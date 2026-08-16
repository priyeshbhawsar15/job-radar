import hashlib
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from job_radar.db.session import AsyncSessionLocal
from job_radar.db.models.candidate import CandidateJob, RunCandidate
from job_radar.db.models.run import PipelineRun, BoardRun, ExecutionAttempt
from job_radar.adapters.base import ExtractedCandidate

logger = logging.getLogger(__name__)

def compute_job_identity_key(company: str, title: str, location: str | None = None) -> str:
    raw = f"{company.strip().lower()}|{title.strip().lower()}|{(location or '').strip().lower()}"
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()

def compute_url_hash(url: str) -> str:
    return hashlib.sha256(url.strip().encode('utf-8')).hexdigest()

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

        async with self.session_factory() as session:
            for item in extracted_candidates:
                identity_key = item.fingerprint or compute_job_identity_key(item.company, item.title, item.location)
                url_hash = compute_url_hash(item.raw_url)

                res = await session.execute(
                    select(CandidateJob).where(CandidateJob.identity_key == identity_key)
                )
                existing_job = res.scalar_one_or_none()

                extra = item.extra_payload or {}
                desc = extra.get("description") or f"Full position requirements and responsibilities for {item.title} at {item.company}. Apply directly at original job listing link."
                salary_raw = extra.get("salary_raw")
                salary_min = extra.get("salary_min")
                salary_max = extra.get("salary_max")
                salary_currency = extra.get("salary_currency")

                if existing_job:
                    candidate_id = existing_job.candidate_id
                    existing_job.last_seen_at = datetime.now(timezone.utc)
                    if not existing_job.description:
                        existing_job.description = desc
                    outcome = "re_observed"
                else:
                    new_job = CandidateJob(
                        board_id=board_id,
                        identity_key=identity_key,
                        canonical_url_hash=url_hash,
                        company=item.company.strip(),
                        title=item.title.strip(),
                        location=item.location.strip() if item.location else None,
                        department=item.department.strip() if item.department else None,
                        employment_type=item.employment_type.strip() if item.employment_type else None,
                        public_apply_url=item.raw_url,
                        description=desc,
                        salary_raw=salary_raw,
                        salary_min=salary_min,
                        salary_max=salary_max,
                        salary_currency=salary_currency
                    )
                    session.add(new_job)
                    await session.flush()
                    candidate_id = new_job.candidate_id
                    new_jobs_count += 1
                    outcome = "discovered"

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

        return len(extracted_candidates), new_jobs_count

normalization_service = NormalizationService()
