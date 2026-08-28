import logging
import json
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
from job_radar.services.location import evaluate_location

logger = logging.getLogger(__name__)


def current_location_decision(candidate: CandidateJob, source_scope: Optional[str] = None, source_evidence: Optional[str] = None):
    """Single durable admission decision used by enrichment, enqueue, and dispatch.

    Durable provider scope wins; callers may supply the board's reviewed scope for
    legacy records that predate durable scope persistence.
    """
    try:
        evidence = json.loads(candidate.location_provider_evidence) if candidate.location_provider_evidence else None
    except (TypeError, json.JSONDecodeError):
        evidence = None
    if isinstance(evidence, dict):
        source_scope = evidence.get("source_scope") or source_scope
        source_evidence = evidence.get("source_evidence") or source_evidence
    result = evaluate_location(candidate.location, source_scope, source_evidence, evidence)
    candidate.location_decision = result.decision
    candidate.location_evidence = result.evidence
    candidate.location_confidence = result.confidence
    candidate.india_eligible = result.eligible
    candidate.india_exclusion_reason = result.reason
    return result


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
        is_enabled = stored.handoff_enabled
        if not is_enabled:
            logger.warning("JobOps handoff disabled in settings. Refusing outbound dispatch call.")
            raise RuntimeError("JobOps handoff is disabled in settings.")

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
            cand_res = await session.execute(select(CandidateJob).where(CandidateJob.candidate_id == candidate_id))
            cand = cand_res.scalar_one_or_none()
            if not cand:
                return None
            eval_res = current_location_decision(cand)
            if not eval_res.eligible:
                await session.commit()
                logger.info(f"Refusing to enqueue candidate {candidate_id} for handoff: {eval_res.decision} ({eval_res.reason})")
                return None

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

    async def reconcile_stale_outbox(self, apply: bool = False) -> List[Dict[str, Any]]:
        """Dry-run-first audit/quarantine of stale foreign outbox rows.

        Accepted rows are reported but deliberately never mutated automatically.
        """
        report: List[Dict[str, Any]] = []
        async with self.session_factory() as session:
            rows = (await session.execute(select(HandoffOutbox).options(selectinload(HandoffOutbox.candidate)))).scalars().all()
            for row in rows:
                candidate = row.candidate
                if not candidate:
                    continue
                old_decision, old_eligible = candidate.location_decision, candidate.india_eligible
                decision = current_location_decision(candidate)
                item = {"candidate_id": candidate.candidate_id, "board": candidate.board_id, "url": candidate.public_apply_url, "raw_location": candidate.location, "old_decision": old_decision, "new_decision": decision.decision, "old_eligible": old_eligible, "outbox_state": row.state, "proposed_action": None}
                if decision.decision == "NON_INDIA":
                    if row.state == "accepted":
                        item["proposed_action"] = "report_accepted_for_approval"
                    elif row.state in {"queued", "uncertain", "dispatching"}:
                        item["proposed_action"] = "quarantine"
                        if apply:
                            row.state = "held"
                            row.next_retry_at = None
                report.append(item)
            if apply:
                await session.commit()
        return report

    async def process_pending_outbox(self, max_batch: Optional[int] = None, loop_until_empty: bool = True) -> int:
        stored = load_settings()
        is_enabled = stored.handoff_enabled
        if not is_enabled:
            logger.debug("Handoff feature disabled in settings. Skipping outbox processing.")
            return 0

        actual_batch = max_batch or stored.jobops_import_batch_size or 50
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
                    .limit(actual_batch)
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
                        if not cand:
                            raise RuntimeError("candidate_missing")
                        eval_res = current_location_decision(cand)
                        if not eval_res.eligible:
                            record.state = "held"
                            attempt.safe_outcome = "rejected"
                            attempt.error_message = eval_res.reason or "NON_INDIA_LOCATION"
                            attempt.finished_at = datetime.now(timezone.utc)
                            await session.commit()
                            continue

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
