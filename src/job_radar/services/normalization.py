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
  """Canonical identity key SHA256 generation."""
  raw = f"{company.strip().lower()}|{title.strip().lower()}|{(location or '').strip().lower()}"
  return hashlib.sha256(raw.encode('utf-8')).hexdigest()

def compute_url_hash(url: str) -> str:
  """Canonical SHA256 of candidate public URL."""
  return hashlib.sha256(url.strip().encode('utf-8')).hexdigest()

class NormalizationService:
  """Service for normalizing extracted candidates, deduplication, and pipeline ingestion."""

  def __init__(self, session_factory=AsyncSessionLocal):
    self.session_factory = session_factory

  async def ingest_candidates(
    self,
    board_id: str,
    board_run_id: str,
    extracted_candidates: List[ExtractedCandidate]
  ) -> Tuple[int, int]:
    """
    Ingest extracted candidates into DB:
    - Normalizes fields (company, title, location).
    - Checks candidate_jobs identity_key index.
    - Inserts new candidate_jobs or updates last_seen_at.
    - Creates run_candidates mapping records.
    Returns (total_ingested, new_jobs_created)
    """
    new_jobs_count = 0
    seen_candidate_ids_in_batch = set()

    async with self.session_factory() as session:
      for item in extracted_candidates:
        identity_key = item.fingerprint or compute_job_identity_key(item.company, item.title, item.location)
        url_hash = compute_url_hash(item.raw_url)

        # Check existing CandidateJob
        res = await session.execute(
          select(CandidateJob).where(CandidateJob.identity_key == identity_key)
        )
        existing_job = res.scalar_one_or_none()

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
            location=item.location.strip() if item.location else None,
            department=item.department.strip() if item.department else None,
            employment_type=item.employment_type.strip() if item.employment_type else None,
            public_apply_url=item.raw_url
          )
          session.add(new_job)
          await session.flush()
          candidate_id = new_job.candidate_id
          new_jobs_count += 1
          outcome = "discovered"

        # Create RunCandidate linkage (avoiding duplicate PK in single run batch)
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

class RetentionPurger:
  """Purger for enforcing 7-day retention limit on execution logs and payload blobs."""

  def __init__(self, retention_days: int = 7, session_factory=AsyncSessionLocal):
    self.retention_days = retention_days
    self.session_factory = session_factory

  async def purge_expired_records(self) -> Dict[str, int]:
    """Purge execution attempts and pipeline runs older than retention threshold."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=self.retention_days)
    purged_counts = {"attempts": 0, "board_runs": 0, "pipeline_runs": 0}

    async with self.session_factory() as session:
      # 1. Delete ExecutionAttempts older than cutoff
      att_res = await session.execute(
        delete(ExecutionAttempt).where(ExecutionAttempt.created_at < cutoff)
      )
      purged_counts["attempts"] = att_res.rowcount or 0

      # 2. Delete BoardRuns older than cutoff
      br_res = await session.execute(
        delete(BoardRun).where(BoardRun.started_at < cutoff)
      )
      purged_counts["board_runs"] = br_res.rowcount or 0

      # 3. Delete PipelineRuns older than cutoff
      pr_res = await session.execute(
        delete(PipelineRun).where(PipelineRun.started_at < cutoff)
      )
      purged_counts["pipeline_runs"] = pr_res.rowcount or 0

      await session.commit()

    logger.info(f"Retention purge complete: {purged_counts}")
    return purged_counts

normalization_service = NormalizationService()
retention_purger = RetentionPurger()
