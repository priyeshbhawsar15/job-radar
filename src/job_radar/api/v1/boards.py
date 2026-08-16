from typing import List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from job_radar.db.session import get_db_session
from job_radar.db.models.board import Board, BoardRevision

router = APIRouter(prefix="/boards", tags=["Job Boards"])

@router.get("", response_model=List[dict])
async def list_boards(db: AsyncSession = Depends(get_db_session)):
    res = await db.execute(
        select(Board)
        .options(selectinload(Board.current_revision))
        .order_by(Board.created_at.desc())
    )
    boards = res.scalars().all()
    out = []
    for b in boards:
        cfg = b.current_revision.config_json if b.current_revision else {}
        out.append({
            "board_id": b.board_id,
            "name": b.name,
            "family": b.family,
            "status": b.status,
            "consecutive_parser_failures": b.consecutive_parser_failures,
            "target_url": cfg.get("target_url", ""),
            "schedule_cron": cfg.get("schedule_cron", ""),
            "created_at": b.created_at.isoformat() if b.created_at else None
        })
    return out
