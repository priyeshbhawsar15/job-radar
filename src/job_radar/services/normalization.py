import hashlib
import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from job_radar.db.session import AsyncSessionLocal
from job_radar.db.models.candidate import CandidateJob, RunCandidate
from job_radar.db.models.run import PipelineRun, BoardRun, ExecutionAttempt
from job_radar.adapters.base import ExtractedCandidate
from job_radar.services.detail_extractor import detail_extractor

logger = logging.getLogger(__name__)

def compute_job_identity_key(company: str, title: str, location: str | None = None) -> str:
    raw = f"{company.strip().lower()}|{title.strip().lower()}|{(location or '').strip().lower()}"
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()

def compute_url_hash(url: str) -> str:
    return hashlib.sha256(url.strip().encode('utf-8')).hexdigest()

async def bg_enrich_candidates(candidates_to_enrich: List[Tuple[str, str, str, str]]):
    for cand_id, url, company, title in candidates_to_enrich[:5]:
        try:
            enriched = await detail_extractor.fetch_and_enrich(url, company, title)
            async with AsyncSessionLocal() as session:
                res = await session.execute(select(CandidateJob).where(CandidateJob.candidate_id == cand_id))
                job = res.scalar_one_or_none()
                if job:
                    job.description = enriched.get("description")
                    job.location = enriched.get("location") or job.location
                    job.employment_type = enriched.get("employment_type") or job.employment_type
                    job.department = enriched.get("department") or job.department
                    job.salary_raw = enriched.get("salary_raw") or job.salary_raw
                    job.salary_min = enriched.get("salary_min")
                    job.salary_max = enriched.get("salary_max")
                    job.salary_currency = enriched.get("salary_currency")
                    await session.commit()
        except Exception:
            pass

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
                identity_key = item.fingerprint or compute_job_identity_key(item.company, item.title, item.location)
                url_hash = compute_url_hash(item.raw_url)

                res = await session.execute(
                    select(CandidateJob).where(CandidateJob.identity_key == identity_key)
                )
                existing_job = res.scalar_one_or_none()

                loc = item.location.strip() if item.location else "India"
                emp_type = item.employment_type.strip() if item.employment_type else "Full-time"
                dept = item.department.strip() if item.department else "Engineering"

                if existing_job:
                    candidate_id = existing_job.candidate_id
                    existing_job.last_seen_at = datetime.now(timezone.utc)
                    outcome = "re_observed"
                else:
                    new_job = CandidateJob(
                        board_id=board_id,
                        identity_key=identity_key,
                        canonical_url_hash=url_hash,
                        company=item.company.strip(),
                        title=item.title.strip(),
                        location=loc,
                        department=dept,
                        employment_type=emp_type,
                        public_apply_url=item.raw_url,
                        description=f"Full job description for {item.title} at {item.company}. Position requirements and responsibilities available at apply link.",
                        salary_raw="Competitive / Not specified"
                    )
                    session.add(new_job)
                    await session.flush()
                    candidate_id = new_job.candidate_id
                    new_jobs_count += 1
                    outcome = "discovered"

                to_enrich.append((candidate_id, item.raw_url, item.company, item.title))

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
