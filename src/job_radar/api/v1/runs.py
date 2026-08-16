from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from job_radar.db.session import get_db_session
from job_radar.db.models.board import Board
from job_radar.db.models.run import PipelineRun, BoardRun
from job_radar.services.engine import execution_engine

router = APIRouter(prefix="/runs", tags=["Pipeline Runs"])

class TriggerRunRequest(BaseModel):
    board_id: Optional[str] = None  # If None, triggers all active boards

class TriggerRunResponse(BaseModel):
    message: str
    pipeline_id: str
    triggered_boards: List[str]

class BoardRunSchema(BaseModel):
    run_id: str
    board_id: str
    pipeline_id: str
    stage: str
    outcome: str
    extracted_count: int
    normalized_count: int
    error_code: Optional[str] = None
    created_at: str

    class Config:
        from_attributes = True

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
