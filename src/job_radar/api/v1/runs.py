from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case
from sqlalchemy.orm import selectinload

from job_radar.db.session import get_db_session, AsyncSessionLocal
from job_radar.db.models.board import Board
from job_radar.db.models.run import PipelineRun, BoardRun
from job_radar.db.models.candidate import CandidateJob, RunCandidate
from job_radar.db.models.handoff import HandoffOutbox
from job_radar.services.engine import execution_engine
from job_radar.services.discord_notifier import send_pipeline_summary_notification
from job_radar.services.handoff import handoff_processor

router = APIRouter(prefix="/runs", tags=["Pipeline Runs"])

class TriggerRunRequest(BaseModel):
    board_id: Optional[str] = None

class TriggerRunResponse(BaseModel):
    message: str
    pipeline_id: str
    triggered_boards: List[str]

async def run_pipeline_task(board_ids: List[str], pipeline_id: str):
    for b_id in board_ids:
        try:
            await execution_engine.execute_board_run(board_id=b_id, pipeline_id=pipeline_id)
        except Exception as e:
            print(f"Error executing board run for {b_id}: {e}")

    try:
        await handoff_processor.process_pending_outbox()
    except Exception as e:
        print(f"Error processing pending handoff outbox for pipeline {pipeline_id}: {e}")

    async with AsyncSessionLocal() as session:
        try:
            await send_pipeline_summary_notification(pipeline_id, session)
        except Exception as e:
            print(f"Error sending Discord pipeline summary notification for {pipeline_id}: {e}")

@router.post("/trigger", response_model=TriggerRunResponse)
async def trigger_run(
    req: TriggerRunRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_session)
):
    if req.board_id:
        board_res = await db.execute(select(Board).where(Board.board_id == req.board_id))
        board = board_res.scalar_one_or_none()
        if not board:
            raise HTTPException(status_code=404, detail="Board not found")
        board_ids = [req.board_id]
    else:
        board_res = await db.execute(select(Board).where(Board.status.in_(["active", "reviewed", "enabled"])))
        boards = board_res.scalars().all()
        board_ids = [b.board_id for b in boards]

    pipeline = PipelineRun(
        trigger="manual",
        status="running",
        total_boards=len(board_ids)
    )
    db.add(pipeline)
    await db.commit()
    await db.refresh(pipeline)

    background_tasks.add_task(run_pipeline_task, board_ids, pipeline.pipeline_id)

    return TriggerRunResponse(
        message=f"Pipeline execution started for {len(board_ids)} board(s)",
        pipeline_id=pipeline.pipeline_id,
        triggered_boards=board_ids
    )

@router.get("", response_model=List[dict])
async def list_runs(db: AsyncSession = Depends(get_db_session)):
    res = await db.execute(
        select(BoardRun)
        .options(selectinload(BoardRun.board))
        .order_by(BoardRun.started_at.desc())
        .limit(100)
    )
    runs = res.scalars().all()
    if not runs:
        return []

    run_ids = [r.board_run_id for r in runs]

    is_not_false = (CandidateJob.india_eligible != False) | CandidateJob.india_eligible.is_(None)
    is_false = CandidateJob.india_eligible.is_(False)

    enrichment_res = await db.execute(
        select(
            RunCandidate.run_id,
            func.sum(
                case((CandidateJob.detail_enrichment_status == "succeeded", 1), else_=0)
            ).label("enrichment_succeeded"),
            func.sum(
                case((CandidateJob.detail_enrichment_status == "failed", 1), else_=0)
            ).label("enrichment_failed"),
            func.sum(
                case(
                    (CandidateJob.detail_enrichment_status.in_(["succeeded", "failed"]), 1),
                    else_=0,
                )
            ).label("enrichment_total"),
            func.sum(
                case((is_not_false & (CandidateJob.detail_enrichment_status == "succeeded"), 1), else_=0)
            ).label("accepted_count"),
            func.sum(
                case((is_false, 1), else_=0)
            ).label("rejected_non_india_count"),
            func.sum(
                case((is_not_false & (CandidateJob.detail_enrichment_status == "failed"), 1), else_=0)
            ).label("rejected_enrichment_count"),
            func.sum(
                case((is_not_false & ~CandidateJob.detail_enrichment_status.in_(["succeeded", "failed"]), 1), else_=0)
            ).label("pending_count"),
            func.count(RunCandidate.candidate_id).label("acceptance_total"),
        )
        .join(CandidateJob, RunCandidate.candidate_id == CandidateJob.candidate_id)
        .where(RunCandidate.run_id.in_(run_ids))
        .group_by(RunCandidate.run_id)
    )

    enrichment_map = {}
    for row in enrichment_res.all():
        acc = int(row.accepted_count or 0)
        rej_ni = int(row.rejected_non_india_count or 0)
        rej_en = int(row.rejected_enrichment_count or 0)
        pend = int(row.pending_count or 0)
        total = int(row.acceptance_total or 0)
        pct = round((acc / total) * 100) if total > 0 else 0
        enrichment_map[row.run_id] = {
            "enrichment_succeeded": int(row.enrichment_succeeded or 0),
            "enrichment_failed": int(row.enrichment_failed or 0),
            "enrichment_total": int(row.enrichment_total or 0),
            "accepted_count": acc,
            "rejected_non_india_count": rej_ni,
            "rejected_enrichment_count": rej_en,
            "pending_count": pend,
            "acceptance_total": total,
            "acceptance_percentage": pct,
        }

    out = []
    default_metrics = {
        "enrichment_succeeded": 0,
        "enrichment_failed": 0,
        "enrichment_total": 0,
        "accepted_count": 0,
        "rejected_non_india_count": 0,
        "rejected_enrichment_count": 0,
        "pending_count": 0,
        "acceptance_total": 0,
        "acceptance_percentage": 0,
    }
    for r in runs:
        metrics = enrichment_map.get(r.board_run_id, default_metrics)
        out.append({
            "run_id": r.board_run_id,
            "pipeline_id": r.pipeline_id,
            "board_id": r.board_id,
            "board_name": r.board.name if r.board else r.board_id,
            "family": r.board.family if r.board else "unknown",
            "stage": r.stage,
            "outcome": r.outcome,
            "extracted_count": r.extracted_count,
            "created_at": r.started_at.isoformat() if r.started_at else None,
            "enrichment_succeeded": metrics["enrichment_succeeded"],
            "enrichment_failed": metrics["enrichment_failed"],
            "enrichment_total": metrics["enrichment_total"],
            "accepted_count": metrics["accepted_count"],
            "rejected_non_india_count": metrics["rejected_non_india_count"],
            "rejected_enrichment_count": metrics["rejected_enrichment_count"],
            "pending_count": metrics["pending_count"],
            "acceptance_total": metrics["acceptance_total"],
            "acceptance_percentage": metrics["acceptance_percentage"],
        })
    return out

@router.get("/board-runs/{run_id}")
async def get_board_run_detail(run_id: str, db: AsyncSession = Depends(get_db_session)):
    res = await db.execute(
        select(BoardRun)
        .options(selectinload(BoardRun.board))
        .where((BoardRun.board_run_id == run_id) | (BoardRun.pipeline_id == run_id))
        .order_by(BoardRun.started_at.desc())
    )
    br = res.scalars().first()
    if not br:
        raise HTTPException(status_code=404, detail="Board run log not found")

    cj_res = await db.execute(
        select(CandidateJob, RunCandidate.observation_outcome, HandoffOutbox.state)
        .join(RunCandidate, CandidateJob.candidate_id == RunCandidate.candidate_id)
        .outerjoin(HandoffOutbox, CandidateJob.candidate_id == HandoffOutbox.candidate_id)
        .where(RunCandidate.run_id == br.board_run_id)
    )
    linked_rows = cj_res.all()

    if not linked_rows:
        cj_res2 = await db.execute(
            select(CandidateJob, HandoffOutbox.state)
            .outerjoin(HandoffOutbox, CandidateJob.candidate_id == HandoffOutbox.candidate_id)
            .where(CandidateJob.board_id == br.board_id)
        )
        linked_rows = [(j, None, state) for j, state in cj_res2.all()]

    jobs_out = []
    new_discovered_count = 0
    re_observed_count = 0
    for j, observation_outcome, handoff_state in linked_rows:
        if observation_outcome == "discovered":
            new_discovered_count += 1
        elif observation_outcome == "re_observed":
            re_observed_count += 1
        
        ops_status = handoff_state if handoff_state else "untracked"

        jobs_out.append({
            "candidate_id": j.candidate_id,
            "board_id": j.board_id,
            "company": j.company,
            "title": j.title,
            "location": j.location,
            "department": j.department,
            "employment_type": j.employment_type,
            "public_apply_url": j.public_apply_url,
            "description": j.description,
            "salary_raw": j.salary_raw,
            "detail_enrichment_status": j.detail_enrichment_status,
            "detail_enrichment_error_code": j.detail_enrichment_error_code,
            "location_decision": getattr(j, "location_decision", None),
            "location_evidence": getattr(j, "location_evidence", None),
            "location_confidence": getattr(j, "location_confidence", None),
            "india_eligible": j.india_eligible,
            "india_exclusion_reason": j.india_exclusion_reason,
            "job_ops_status": ops_status,
            "created_at": j.discovered_at.isoformat() if j.discovered_at else None,
            "observation_outcome": observation_outcome
        })

    return {
        "board_run": {
            "run_id": br.board_run_id,
            "pipeline_id": br.pipeline_id,
            "board_id": br.board_id,
            "board_name": br.board.name if br.board else br.board_id,
            "family": br.board.family if br.board else "unknown",
            "stage": br.stage,
            "outcome": br.outcome,
            "extracted_count": br.extracted_count,
            "new_discovered_count": new_discovered_count,
            "re_observed_count": re_observed_count,
            "created_at": br.started_at.isoformat() if br.started_at else None,
        },
        "jobs": jobs_out,
        "extracted_jobs": jobs_out
    }
