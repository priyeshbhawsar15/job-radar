import hashlib
import logging
import asyncio
import httpx
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, or_

from job_radar.db.session import AsyncSessionLocal
from job_radar.db.models.candidate import CandidateJob, RunCandidate
from job_radar.db.models.run import PipelineRun, BoardRun, ExecutionAttempt
from job_radar.adapters.base import ExtractedCandidate
from job_radar.services.detail_extractor import detail_extractor, description_is_valid

logger = logging.getLogger(__name__)

def _description_looks_bad(text: str, title: str = "") -> bool:
    if not text:
        return True
    return not description_is_valid(text, title=title)

def compute_job_identity_key(company: str, title: str, location: str | None = None) -> str:
    raw = f"{company.strip().lower()[:500]}|{title.strip().lower()[:500]}|{(location or '').strip().lower()[:200]}"
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()

def compute_url_hash(url: str) -> str:
    return hashlib.sha256(url.strip()[:2000].encode('utf-8')).hexdigest()

async def bg_enrich_candidates(candidates_to_enrich: List[Tuple[str, str, str, str]]):
    sem = asyncio.Semaphore(10)

    async def do_enrich(cand_tuple):
        cand_id, url, company, title = cand_tuple
        async with sem:
            try:
                enriched = await detail_extractor.fetch_and_enrich(url, company, title)
                async with AsyncSessionLocal() as session:
                    res = await session.execute(select(CandidateJob).where(CandidateJob.candidate_id == cand_id))
                    job = res.scalar_one_or_none()
                    if job:
                        desc = enriched.get("description")
                        if desc and description_is_valid(desc, title=title):
                            job.description = desc[:40000]
                        enr_loc = enriched.get("location")
                        if enr_loc and enr_loc.strip() not in ("India", "in", "pageData", ""):
                            job.location = enr_loc.strip()[:200]
                        if enriched.get("employment_type"):
                            job.employment_type = enriched.get("employment_type")[:200]
                        await session.commit()
            except Exception as e:
                logger.info(f"Enrichment error: {e}")

    await asyncio.gather(*[do_enrich(c) for c in candidates_to_enrich])

class NormalizationService:
    def __init__(self, session_factory=AsyncSessionLocal):
        self.session_factory = session_factory

    async def ingest_candidates(
        self,
        board_id: str,
        board_run_id: str,
        extracted_candidates: List[ExtractedCandidate]
    ) -> Tuple[int, int]:
        new_jobs_count = 0
        seen_candidate_ids_in_batch = set()
        to_enrich: List[Tuple[str, str, str, str]] = []

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
                    outcome = "re_observed"

                    if not existing_job.description or not description_is_valid(existing_job.description, title=existing_job.title):
                        to_enrich.append((candidate_id, url_capped, company_capped, title_capped))
                else:
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
                        salary_raw="Competitive / Not specified"[:200]
                    )
                    session.add(new_job)
                    await session.flush()
                    candidate_id = new_job.candidate_id
                    new_jobs_count += 1
                    outcome = "discovered"

                    if not valid_extra_desc:
                        to_enrich.append((candidate_id, url_capped, company_capped, title_capped))

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

        if to_enrich:
            asyncio.create_task(bg_enrich_candidates(to_enrich))

        return len(extracted_candidates), new_jobs_count

normalization_service = NormalizationService()
