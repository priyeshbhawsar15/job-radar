from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from job_radar.db.session import get_db_session
from job_radar.db.models.board import Board
from job_radar.db.models.run import PipelineRun, BoardRun
from job_radar.db.models.candidate import CandidateJob, RunCandidate
from job_radar.services.engine import execution_engine

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
        boards_res = await db.execute(select(Board).where(Board.status != "retired"))
        boards = boards_res.scalars().all()
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
        message="Pipeline run triggered successfully",
        pipeline_id=pipeline.pipeline_id,
        triggered_boards=board_ids
    )

@router.get("", response_model=List[dict])
async def list_runs(db: AsyncSession = Depends(get_db_session)):
    res = await db.execute(
        select(BoardRun)
        .options(selectinload(BoardRun.board))
        .order_by(BoardRun.started_at.desc())
        .limit(50)
    )
    runs = res.scalars().all()
    out = []
    for r in runs:
        out.append({
            "run_id": r.board_run_id,
            "board_id": r.board_id,
            "board_name": r.board.name if r.board else r.board_id,
            "family": r.board.family if r.board else "unknown",
            "pipeline_id": r.pipeline_id,
            "stage": r.stage,
            "outcome": r.outcome,
            "extracted_count": r.extracted_count,
            "normalized_count": 0,
            "error_code": r.error_code,
            "created_at": r.started_at.isoformat() if r.started_at else None,
            "terminal_at": r.terminal_at.isoformat() if r.terminal_at else None
        })
    return out

@router.get("/board-runs/{run_id}", response_model=dict)
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
        select(CandidateJob)
        .join(RunCandidate, CandidateJob.candidate_id == RunCandidate.candidate_id)
        .where(RunCandidate.run_id == br.board_run_id)
    )
    linked_jobs = cj_res.scalars().all()

    if not linked_jobs:
        cj_res2 = await db.execute(
            select(CandidateJob)
            .where(CandidateJob.board_id == br.board_id)
        )
        linked_jobs = cj_res2.scalars().all()

    jobs_out = []
    for j in linked_jobs:
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
            "created_at": j.discovered_at.isoformat() if j.discovered_at else None
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
            "created_at": br.started_at.isoformat() if br.started_at else None,
            "terminal_at": br.terminal_at.isoformat() if br.terminal_at else None
        },
        "extracted_jobs": jobs_out
    }
