from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from job_radar.db.session import get_db_session
from job_radar.db.models.board import Board, BoardRevision

router = APIRouter(prefix="/boards", tags=["Job Boards"])

class UpdateBoardConfigRequest(BaseModel):
    target_url: Optional[str] = None
    max_pages: Optional[int] = 3
    family: Optional[str] = None
    schedule_cron: Optional[str] = None

@router.get("", response_model=List[dict])
async def list_boards(db: AsyncSession = Depends(get_db_session)):
    res = await db.execute(
        select(Board)
        .options(selectinload(Board.current_revision))
        .order_by(Board.name.asc())
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
            "max_pages": cfg.get("max_pages", 3),
            "schedule_cron": cfg.get("schedule_cron", ""),
            "created_at": b.created_at.isoformat() if b.created_at else None
        })
    return out

@router.get("/{board_id}", response_model=dict)
async def get_board(board_id: str, db: AsyncSession = Depends(get_db_session)):
    res = await db.execute(
        select(Board)
        .options(selectinload(Board.current_revision))
        .where(Board.board_id == board_id)
    )
    b = res.scalar_one_or_none()
    if not b:
        raise HTTPException(status_code=404, detail="Board not found")
    cfg = b.current_revision.config_json if b.current_revision else {}
    return {
        "board_id": b.board_id,
        "name": b.name,
        "family": b.family,
        "status": b.status,
        "consecutive_parser_failures": b.consecutive_parser_failures,
        "target_url": cfg.get("target_url", ""),
        "max_pages": cfg.get("max_pages", 3),
        "schedule_cron": cfg.get("schedule_cron", ""),
        "created_at": b.created_at.isoformat() if b.created_at else None
    }

@router.put("/{board_id}/config", response_model=dict)
async def update_board_config(
    board_id: str,
    req: UpdateBoardConfigRequest,
    db: AsyncSession = Depends(get_db_session)
):
    res = await db.execute(
        select(Board)
        .options(selectinload(Board.current_revision))
        .where(Board.board_id == board_id)
    )
    b = res.scalar_one_or_none()
    if not b:
        raise HTTPException(status_code=404, detail="Board not found")

    cur_rev = b.current_revision
    new_rev_num = (cur_rev.revision_number + 1) if cur_rev else 1
    new_cfg = cur_rev.config_json.copy() if cur_rev and cur_rev.config_json else {}

    if req.target_url is not None:
        new_cfg["target_url"] = req.target_url
    if req.max_pages is not None:
        new_cfg["max_pages"] = req.max_pages
    if req.schedule_cron is not None:
        new_cfg["schedule_cron"] = req.schedule_cron
    if req.family is not None:
        new_cfg["family"] = req.family
        b.family = req.family

    new_rev = BoardRevision(
        board_id=b.board_id,
        revision_number=new_rev_num,
        status="reviewed",
        config_json=new_cfg
    )
    db.add(new_rev)
    await db.flush()
    b.current_revision_id = new_rev.revision_id
    await db.commit()

    return {
        "board_id": b.board_id,
        "name": b.name,
        "family": b.family,
        "status": b.status,
        "revision_number": new_rev_num,
        "config_json": new_cfg
    }
