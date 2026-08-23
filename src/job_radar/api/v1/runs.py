from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
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
    out = []
    for r in runs:
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
