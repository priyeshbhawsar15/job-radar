from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from job_radar.db.session import get_db_session
from job_radar.db.models.board import Board
from job_radar.db.models.candidate import CandidateJob
from job_radar.db.models.handoff import HandoffOutbox
from job_radar.services.detail_extractor import detail_extractor, description_is_valid
from job_radar.services.handoff import handoff_processor
from job_radar.services.location import is_india_eligible

router = APIRouter(prefix="/jobs", tags=["Normalized Jobs"])


def _serialize_job(j: CandidateJob, job_ops_status: Optional[str] = None) -> dict:
    state = job_ops_status
    if not state:
        try:
            if hasattr(j, "handoff_outbox") and j.handoff_outbox:
                state = j.handoff_outbox.state
        except Exception:
            state = "untracked"
    return {
        "candidate_id": j.candidate_id,
        "board_id": j.board_id,
        "title": j.title,
        "company": j.company,
        "company_name": j.company,
        "location": j.location,
        "department": j.department,
        "employment_type": j.employment_type,
        "public_apply_url": j.public_apply_url,
        "description": j.description,
        "salary_raw": j.salary_raw,
        "salary_min": j.salary_min,
        "salary_max": j.salary_max,
        "salary_currency": j.salary_currency,
        "first_seen_at": j.discovered_at.isoformat() if j.discovered_at else None,
        "last_seen_at": j.last_seen_at.isoformat() if j.last_seen_at else None,
        "observation_outcome": getattr(j, "observation_outcome", "discovered"),
        "detail_enrichment_status": j.detail_enrichment_status,
        "detail_enrichment_error_code": j.detail_enrichment_error_code,
        "india_eligible": j.india_eligible if hasattr(j, "india_eligible") and j.india_eligible is not None else is_india_eligible(j.location)[0],
        "india_exclusion_reason": j.india_exclusion_reason if hasattr(j, "india_exclusion_reason") else is_india_eligible(j.location)[1],
        "job_ops_status": state or "untracked",
    }

@router.get("", response_model=List[dict])
async def list_jobs(
    board_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session)
):
    query = select(CandidateJob).options(selectinload(CandidateJob.handoff_outbox)).order_by(CandidateJob.discovered_at.desc())
    if board_id:
        query = query.where(CandidateJob.board_id == board_id)

    res = await db.execute(query)
    jobs = res.scalars().all()
    return [_serialize_job(j) for j in jobs]


@router.post("/{candidate_id}/retry-enrichment", response_model=dict)
async def retry_enrichment(
    candidate_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    res = await db.execute(select(CandidateJob).where(CandidateJob.candidate_id == candidate_id))
    candidate = res.scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate job not found")

    board_res = await db.execute(
        select(Board)
        .options(selectinload(Board.current_revision))
        .where(Board.board_id == candidate.board_id)
    )
    board = board_res.scalar_one_or_none()
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")

    family = board.family
    provider_config = board.current_revision.config_json if board.current_revision else {}
    if isinstance(provider_config, dict):
        family = provider_config.get("family", family)

    err_code = "description_missing"
    result = None
    try:
        result = await detail_extractor.fetch_and_enrich(
            public_apply_url=candidate.public_apply_url,
            board_name=candidate.company,
            title=candidate.title,
            family=family,
            provider_config=provider_config,
        )
    except Exception:
        err_code = "enrichment_exception"

    candidate.detail_enrichment_attempts = (candidate.detail_enrichment_attempts or 0) + 1

    if result and result.description and description_is_valid(result.description, title=candidate.title):
        candidate.description = result.description[:40000]
        if result.location and result.location.strip() not in ("India", "in", "pageData", ""):
            candidate.location = result.location.strip()[:200]
        if result.employment_type:
            candidate.employment_type = result.employment_type[:200]
        if result.department:
            candidate.department = result.department[:200]
        candidate.detail_enrichment_status = "succeeded"
        candidate.detail_enriched_at = datetime.now(timezone.utc)
        candidate.detail_enrichment_error_code = None
    else:
        raw_err = getattr(result, "error_code", None)
        candidate.detail_enrichment_status = "failed"
        candidate.detail_enrichment_error_code = raw_err if isinstance(raw_err, str) else err_code

    await db.commit()
    await db.refresh(candidate)

    return _serialize_job(candidate)


class PushJobOpsResponse(BaseModel):
    status: str
    detail: Optional[str] = None


@router.post("/{candidate_id}/push-jobops", response_model=PushJobOpsResponse)
async def push_candidate_to_jobops(
    candidate_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    res = await db.execute(select(CandidateJob).where(CandidateJob.candidate_id == candidate_id))
    candidate = res.scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate job not found")

    is_eligible, reason = is_india_eligible(candidate.location)
    if not is_eligible:
        return PushJobOpsResponse(status="excluded_non_india", detail=f"Job excluded by India gate: {reason}")

    outbox = await handoff_processor.enqueue_candidate_handoff(candidate_id)
    if not outbox:
        outbox_res = await db.execute(select(HandoffOutbox).where(HandoffOutbox.candidate_id == candidate_id))
        outbox = outbox_res.scalar_one_or_none()

    if outbox:
        outbox.state = "queued"
        outbox.next_retry_at = datetime.now(timezone.utc)
        await db.commit()

    processed = await handoff_processor.process_pending_outbox(max_batch=1, loop_until_empty=False)

    outbox_res = await db.execute(select(HandoffOutbox).where(HandoffOutbox.candidate_id == candidate_id))
    updated_outbox = outbox_res.scalar_one_or_none()

    final_state = updated_outbox.state if updated_outbox else "failed"
    if final_state == "accepted":
        return PushJobOpsResponse(status="imported", detail="Job successfully imported to Job Ops")
    return PushJobOpsResponse(status=final_state, detail=f"Handoff status: {final_state}")

