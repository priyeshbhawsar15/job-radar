from dataclasses import dataclass
import hashlib
import logging
import asyncio
import httpx
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Tuple, Optional, Mapping
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, or_

from job_radar.db.session import AsyncSessionLocal
from job_radar.db.models.candidate import CandidateJob, RunCandidate
from job_radar.db.models.run import PipelineRun, BoardRun, ExecutionAttempt
from job_radar.adapters.base import ExtractedCandidate
from job_radar.services.detail_extractor import detail_extractor, description_is_valid
from job_radar.services.detail_contracts import DetailResult
from job_radar.services.location import is_india_eligible
from job_radar.services.oracle_detail import extract_oracle_public_id
from job_radar.services.handoff import handoff_processor

logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class IngestionResult:
    observed_count: int
    created_count: int
    enrichment_succeeded: int
    enrichment_failed: int


def oracle_detail_title_replacement(
    *,
    current_title: str,
    company: str,
    public_url: str,
    detail_title: object,
) -> Optional[str]:
    """Return a capped detail title only for this URL's exact Oracle fallback title."""
    if not isinstance(current_title, str) or not isinstance(company, str) or not isinstance(public_url, str):
        return None
    if not isinstance(detail_title, str):
        return None
    stripped_detail = detail_title.strip()
    if not stripped_detail:
        return None
    public_id = extract_oracle_public_id(public_url)
    if not public_id:
        return None
    expected_fallback = f"{company} Job Requisition {public_id}"
    if current_title == expected_fallback:
        return stripped_detail[:255]
    return None


def _description_looks_bad(text: str, title: str = "") -> bool:
    if not text:
        return True
    return not description_is_valid(text, title=title)

def compute_job_identity_key(company: str, title: str, location: str | None = None) -> str:
    raw = f"{company.strip().lower()[:500]}|{title.strip().lower()[:500]}|{(location or '').strip().lower()[:200]}"
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()

def compute_url_hash(url: str) -> str:
    return hashlib.sha256(url.strip()[:2000].encode('utf-8')).hexdigest()

class NormalizationService:
    def __init__(self, session_factory=AsyncSessionLocal, detail_extractor=detail_extractor):
        self.session_factory = session_factory
        self.detail_extractor = detail_extractor

    async def ingest_candidates(
        self,
        board_id: str,
        board_run_id: str,
        extracted_candidates: List[ExtractedCandidate],
        *,
        family: str = "generic",
        provider_config: Optional[Mapping[str, Any]] = None,
    ) -> IngestionResult:
        new_jobs_count = 0
        seen_candidate_ids_in_batch = set()
        to_enrich: Dict[str, Tuple[str, str, str, str]] = {}  # cand_id -> (cand_id, url, company, title)
        already_valid_candidate_ids: List[str] = []
        enrichment_succeeded_count = 0
        enrichment_failed_count = 0

        async with self.session_factory() as session:
            for item in extracted_candidates:
                title_capped = item.title.strip()[:500]
                company_capped = item.company.strip()[:500]
                url_capped = item.raw_url.strip()[:2000]

                identity_key = item.fingerprint or compute_job_identity_key(company_capped, title_capped, item.location)
                url_hash = compute_url_hash(url_capped)

                res = await session.execute(
                    select(CandidateJob).where(
                        (CandidateJob.board_id == board_id) &
                        or_(CandidateJob.canonical_url_hash == url_hash, CandidateJob.identity_key == identity_key)
                    )
                )
                existing_job = res.scalars().first()

                loc = (item.location.strip() if item.location else "India")[:200]
                emp_type = (item.employment_type.strip() if item.employment_type else "Full-time")[:200]
                dept = (item.department.strip() if item.department else "Engineering")[:200]
                raw_desc = item.extra_payload.get("description")
                valid_extra_desc = raw_desc[:40000] if raw_desc and description_is_valid(raw_desc, title=title_capped) else None

                if existing_job:
                    candidate_id = existing_job.candidate_id
                    existing_job.last_seen_at = datetime.now(timezone.utc)
                    if valid_extra_desc:
                        if not existing_job.description or not description_is_valid(existing_job.description, title=existing_job.title) or len(valid_extra_desc) > len(existing_job.description or ""):
                            existing_job.description = valid_extra_desc
                            existing_job.detail_enrichment_status = "succeeded"
                            existing_job.detail_enriched_at = datetime.now(timezone.utc)
                            existing_job.detail_enrichment_error_code = None
                    outcome = "re_observed"

                    if not existing_job.description or not description_is_valid(existing_job.description, title=existing_job.title):
                        existing_job.detail_enrichment_status = "pending"
                        to_enrich[candidate_id] = (candidate_id, url_capped, company_capped, title_capped)
                    else:
                        enrichment_succeeded_count += 1
                else:
                    initial_status = "succeeded" if valid_extra_desc else "pending"
                    initial_enriched_at = datetime.now(timezone.utc) if valid_extra_desc else None

                    new_job = CandidateJob(
                        board_id=board_id,
                        identity_key=identity_key,
                        canonical_url_hash=url_hash,
                        company=company_capped,
                        title=title_capped,
                        location=loc,
                        department=dept,
                        employment_type=emp_type,
                        public_apply_url=url_capped,
                        description=valid_extra_desc,
                        salary_raw="Competitive / Not specified"[:200],
                        detail_enrichment_status=initial_status,
                        detail_enriched_at=initial_enriched_at,
                    )
                    session.add(new_job)
                    await session.flush()
                    candidate_id = new_job.candidate_id
                    new_jobs_count += 1
                    outcome = "discovered"

                    if not valid_extra_desc:
                        to_enrich[candidate_id] = (candidate_id, url_capped, company_capped, title_capped)
                    else:
                        enrichment_succeeded_count += 1
                        already_valid_candidate_ids.append(candidate_id)

                if candidate_id not in seen_candidate_ids_in_batch:
                    run_cand = RunCandidate(
                        run_id=board_run_id,
                        candidate_id=candidate_id,
                        board_id=board_id,
                        observation_outcome=outcome
                    )
                    session.add(run_cand)
                    seen_candidate_ids_in_batch.add(candidate_id)

            await session.commit()

        for c_id in already_valid_candidate_ids:
            try:
                async with self.session_factory() as session:
                    res = await session.execute(select(CandidateJob).where(CandidateJob.candidate_id == c_id))
                    cand = res.scalar_one_or_none()
                    cand_loc = cand.location if cand else None
                is_eligible, reason = is_india_eligible(cand_loc)
                if is_eligible:
                    await handoff_processor.enqueue_candidate_handoff(c_id)
                else:
                    logger.info(f"Skipping handoff for candidate {c_id}: excluded by India gate ({reason})")
            except Exception as h_err:
                logger.warning(f"Failed to enqueue handoff for valid candidate {c_id}: {h_err}")

        if to_enrich:
            board_concurrency = 5
            if provider_config and isinstance(provider_config, dict):
                if "max_enrichment_concurrency" in provider_config and isinstance(provider_config["max_enrichment_concurrency"], int):
                    board_concurrency = max(1, provider_config["max_enrichment_concurrency"])

            sem = asyncio.Semaphore(board_concurrency)

            async def do_enrich(cand_tuple: Tuple[str, str, str, str]) -> bool:
                cand_id, url, company, title = cand_tuple
                async with sem:
                    err_code = "description_missing"
                    result = None
                    try:
                        result = await self.detail_extractor.fetch_and_enrich(
                            public_apply_url=url,
                            board_name=company,
                            title=title,
                            family=family,
                            provider_config=provider_config,
                        )
                    except Exception as e:
                        logger.info(f"Enrichment exception for {cand_id}: {e}")
                        err_code = "enrichment_exception"

                    async with self.session_factory() as session:
                        res = await session.execute(select(CandidateJob).where(CandidateJob.candidate_id == cand_id))
                        job = res.scalar_one_or_none()
                        if job:
                            job.detail_enrichment_attempts = (job.detail_enrichment_attempts or 0) + 1
                            if result and hasattr(result, "description") and result.description and description_is_valid(result.description, title=title):
                                job.description = result.description[:40000]
                                if result.location and result.location.strip() not in ("India", "in", "pageData", ""):
                                    job.location = result.location.strip()[:200]
                                if result.employment_type:
                                    job.employment_type = result.employment_type[:200]
                                if result.department:
                                    job.department = result.department[:200]
                                if family == "oracle":
                                    new_title = oracle_detail_title_replacement(
                                        current_title=job.title,
                                        company=job.company,
                                        public_url=job.public_apply_url,
                                        detail_title=getattr(result, "title", None),
                                    )
                                    if new_title:
                                        job.title = new_title
                                job.detail_enrichment_status = "succeeded"
                                job.detail_enriched_at = datetime.now(timezone.utc)
                                job.detail_enrichment_error_code = None
                                logger.info(
                                    f"Detail enrichment succeeded for candidate {cand_id}: "
                                    f"board={board_id}, family={family}, source={getattr(result, 'source', None)}"
                                )
                                try:
                                    is_eligible, reason = is_india_eligible(job.location)
                                    if is_eligible:
                                        await handoff_processor.enqueue_candidate_handoff(cand_id)
                                    else:
                                        logger.info(f"Skipping handoff for candidate {cand_id} post-enrichment: excluded by India gate ({reason})")
                                except Exception as h_err:
                                    logger.warning(f"Failed to enqueue handoff for {cand_id}: {h_err}")
                                await session.commit()
                                return True
                            else:
                                raw_err = getattr(result, "error_code", None)
                                final_err_code = raw_err if isinstance(raw_err, str) else err_code
                                job.detail_enrichment_status = "failed"
                                job.detail_enrichment_error_code = final_err_code
                                logger.info(
                                    f"Detail enrichment failed for candidate {cand_id}: "
                                    f"board={board_id}, family={family}, error_code={final_err_code}"
                                )
                                await session.commit()
                                return False
                        return False

            results = await asyncio.gather(*[do_enrich(c) for c in to_enrich.values()])
            enrichment_succeeded_count += sum(1 for r in results if r)
            enrichment_failed_count += sum(1 for r in results if not r)

        return IngestionResult(
            observed_count=len(extracted_candidates),
            created_count=new_jobs_count,
            enrichment_succeeded=enrichment_succeeded_count,
            enrichment_failed=enrichment_failed_count,
        )

normalization_service = NormalizationService()
