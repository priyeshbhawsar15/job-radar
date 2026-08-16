import logging
import asyncio
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from job_radar.config import settings
from job_radar.db.session import AsyncSessionLocal
from job_radar.db.models.handoff import HandoffOutbox, HandoffAttempt
from job_radar.db.models.candidate import CandidateJob

logger = logging.getLogger(__name__)

class JobOpsClient:
  """Client for forwarding candidate jobs to Job Ops endpoint."""

  def __init__(self, endpoint: Optional[str] = None, username: Optional[str] = None, password: Optional[str] = None):
    self.endpoint = endpoint or settings.JOBOPS_ENDPOINT
    self.username = username or settings.JOBOPS_USERNAME
    self.password = password or settings.JOBOPS_PASSWORD

  async def push_candidate(self, candidate_data: Dict[str, Any]) -> bool:
    """Push candidate payload to external Job Ops endpoint."""
    if not self.endpoint:
      logger.info("JobOps endpoint not configured. Simulating successful handoff.")
      return True

    auth = None
    if self.username and self.password:
      auth = (self.username, self.password)

    async with httpx.AsyncClient(timeout=15.0) as client:
      response = await client.post(self.endpoint, json=candidate_data, auth=auth)
      response.raise_for_status()
      return True

class HandoffProcessor:
  """Transactional outbox processor for delivering candidate handoffs to Job Ops."""

  def __init__(self, session_factory=AsyncSessionLocal, jobops_client: Optional[JobOpsClient] = None):
    self.session_factory = session_factory
    self.client = jobops_client or JobOpsClient()

  async def enqueue_candidate_handoff(self, candidate_id: str, payload_json: Dict[str, Any]) -> HandoffOutbox:
    """Enqueue a candidate handoff into transactional outbox."""
    async with self.session_factory() as session:
      idempotency_key = f"idem_{candidate_id}_{uuid.uuid4().hex[:8]}"
      outbox = HandoffOutbox(
        candidate_id=candidate_id,
        idempotency_key=idempotency_key,
        state="queued",
        next_retry_at=datetime.now(timezone.utc)
      )
      session.add(outbox)
      await session.commit()
      await session.refresh(outbox)
      return outbox

  async def process_pending_outbox(self, max_batch: int = 10) -> int:
    """Process pending outbox records with exponential backoff retries."""
    if not settings.HANDOFF_ENABLED and not settings.JOBOPS_ENDPOINT:
      logger.debug("Handoff feature disabled or endpoint unconfigured. Skipping outbox processing.")
      return 0

    now = datetime.now(timezone.utc)
    processed_count = 0

    async with self.session_factory() as session:
      res = await session.execute(
        select(HandoffOutbox)
        .options(selectinload(HandoffOutbox.attempts))
        .where(HandoffOutbox.state.in_(["queued", "uncertain"]))
        .where(HandoffOutbox.next_retry_at <= now)
        .limit(max_batch)
      )
      pending_records = res.scalars().all()

      for record in pending_records:
        record.state = "dispatching"
        attempt_seq = len(record.attempts) + 1 if record.attempts else 1

        attempt = HandoffAttempt(
          outbox_id=record.outbox_id,
          attempt_seq=attempt_seq,
          safe_outcome="in_progress"
        )
        session.add(attempt)
        await session.flush()

        try:
          # Fetch candidate details
          cand_res = await session.execute(select(CandidateJob).where(CandidateJob.candidate_id == record.candidate_id))
          cand = cand_res.scalar_one_or_none()

          payload = {
            "title": cand.title if cand else "Unknown",
            "company": cand.company if cand else "Unknown",
            "url": cand.public_apply_url if cand else ""
          }

          # Attempt delivery to Job Ops
          await self.client.push_candidate(payload)
          record.state = "accepted"
          attempt.safe_outcome = "accepted"
          attempt.http_status = 200
          attempt.finished_at = datetime.now(timezone.utc)
          processed_count += 1

        except Exception as e:
          error_str = str(e)
          attempt.safe_outcome = "rejected"
          attempt.error_message = error_str
          attempt.finished_at = datetime.now(timezone.utc)

          if attempt_seq >= 5:
            record.state = "rejected"
            logger.error(f"Handoff record {record.outbox_id} failed 5 attempts. State set to REJECTED.")
          else:
            record.state = "uncertain"
            backoff_seconds = (2 ** attempt_seq) * 5
            record.next_retry_at = now + timedelta(seconds=backoff_seconds)
            logger.warning(f"Handoff attempt failed for {record.outbox_id}. Retrying in {backoff_seconds}s.")

        await session.commit()

    return processed_count

handoff_processor = HandoffProcessor()
