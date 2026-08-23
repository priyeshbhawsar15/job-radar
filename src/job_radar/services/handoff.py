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
from job_radar.services.detail_extractor import description_is_valid
from job_radar.services.settings_store import load_settings

logger = logging.getLogger(__name__)


class JobOpsClient:
    """Client for forwarding candidate jobs to Job Ops intake API (/api/manual-jobs/import)."""

    def __init__(self, endpoint: Optional[str] = None, username: Optional[str] = None, password: Optional[str] = None):
        stored = load_settings()
        raw_ep = endpoint or stored.jobops_endpoint or settings.JOBOPS_ENDPOINT or "http://192.168.2.201:3005"
        self.base_endpoint = raw_ep.rstrip("/")
        if self.base_endpoint.endswith("/api/manual-jobs/import"):
            self.import_endpoint = self.base_endpoint
            self.base_endpoint = self.base_endpoint[:-23]
        else:
            self.import_endpoint = f"{self.base_endpoint}/api/manual-jobs/import"

        self.username = username or stored.jobops_username or settings.JOBOPS_USERNAME
        self.password = password or stored.jobops_password or settings.JOBOPS_PASSWORD
        self._token: Optional[str] = None

    async def _ensure_token(self, client: httpx.AsyncClient) -> Optional[str]:
        if self._token:
            return self._token
        if not self.username or not self.password:
            return None

        login_url = f"{self.base_endpoint}/api/auth/login"
        try:
            resp = await client.post(login_url, json={"username": self.username, "password": self.password})
            if resp.status_code == 200:
                data = resp.json()
                if data.get("ok") and data.get("data", {}).get("token"):
                    self._token = data["data"]["token"]
                    return self._token
        except Exception as exc:
            logger.warning(f"JobOps authentication failed: {exc}")
        return None

    async def push_candidate(self, candidate_data: Dict[str, Any]) -> bool:
        stored = load_settings()
        is_enabled = stored.handoff_enabled or settings.HANDOFF_ENABLED
        if not is_enabled:
            logger.info("JobOps handoff disabled in settings. Simulating successful handoff outbox dispatch.")
            return True

        async with httpx.AsyncClient(timeout=15.0) as client:
            token = await self._ensure_token(client)
            headers = {}
            if token:
                headers["Authorization"] = f"Bearer {token}"

            response = await client.post(self.import_endpoint, json=candidate_data, headers=headers)
            # If 409 Conflict, job is already present in Job Ops workspace -- count as success
            if response.status_code == 409:
                logger.info(f"Candidate already exists in Job Ops workspace: {candidate_data.get('job', {}).get('sourceJobId')}")
                return True

            response.raise_for_status()
            return True


class HandoffProcessor:
    """Transactional outbox processor for delivering candidate handoffs to Job Ops."""

    def __init__(self, session_factory=AsyncSessionLocal, jobops_client: Optional[JobOpsClient] = None):
        self.session_factory = session_factory
        self.client = jobops_client or JobOpsClient()

    async def enqueue_candidate_handoff(self, candidate_id: str, payload_json: Optional[Dict[str, Any]] = None) -> Optional[HandoffOutbox]:
        async with self.session_factory() as session:
            # Avoid duplicate outbox queueing for the same candidate
            existing_res = await session.execute(
                select(HandoffOutbox).where(HandoffOutbox.candidate_id == candidate_id)
            )
            if existing_res.scalar_one_or_none():
                return None

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

    async def process_pending_outbox(self, max_batch: int = 50, loop_until_empty: bool = True) -> int:
        stored = load_settings()
        is_enabled = stored.handoff_enabled or settings.HANDOFF_ENABLED
        if not is_enabled:
            logger.debug("Handoff feature disabled in settings. Skipping outbox processing.")
            return 0

        total_processed = 0

        while True:
            now = datetime.now(timezone.utc)
            processed_in_batch = 0

            async with self.session_factory() as session:
                res = await session.execute(
                    select(HandoffOutbox)
                    .options(selectinload(HandoffOutbox.attempts))
                    .where(HandoffOutbox.state.in_(["queued", "uncertain"]))
                    .where(HandoffOutbox.next_retry_at <= now)
                    .limit(max_batch)
                )
                pending_records = res.scalars().all()

                if not pending_records:
                    break

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
                        cand_res = await session.execute(select(CandidateJob).where(CandidateJob.candidate_id == record.candidate_id))
                        cand = cand_res.scalar_one_or_none()

                        payload = {
                            "skipTailoring": True,
                            "job": {
                                "source": (cand.board_id if cand else "job_radar")[:120],
                                "sourceJobId": (cand.candidate_id if cand else "unknown")[:500],
                                "title": (cand.title if cand else "Unknown Position")[:500],
                                "employer": (cand.company if cand else "Unknown Company")[:500],
                                "jobUrl": (cand.public_apply_url if cand else "")[:2000],
                                "applicationLink": (cand.public_apply_url if cand else "")[:2000],
                                "location": ((cand.location if (cand and cand.location) else "India") or "India")[:200],
                                "salary": (cand.salary_raw if (cand and cand.salary_raw) else "Competitive / Not specified")[:200],
                                "jobDescription": (cand.description if (cand and cand.description and description_is_valid(cand.description, title=cand.title if cand else "")) else f"Full position details and responsibilities for {cand.title if cand else 'Role'} at {cand.company if cand else 'Company'}.")[:40000],
                                "jobType": (cand.employment_type if (cand and cand.employment_type) else "Full-time")[:200],
                                "jobFunction": (cand.department if (cand and cand.department) else "Engineering")[:200]
                            }
                        }

                        await self.client.push_candidate(payload)
                        record.state = "accepted"
                        attempt.safe_outcome = "accepted"
                        attempt.http_status = 200
                        attempt.finished_at = datetime.now(timezone.utc)
                        processed_in_batch += 1

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

            total_processed += processed_in_batch

            if not loop_until_empty or processed_in_batch == 0:
                break

        return total_processed


handoff_processor = HandoffProcessor()
