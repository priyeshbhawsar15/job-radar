from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from job_radar.db.models.board import Board, BoardRevision


class BoardRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_board(self, name: str, family: str, status: str = "draft") -> Board:
        board = Board(name=name, family=family, status=status)
        self.session.add(board)
        await self.session.commit()
        await self.session.refresh(board)
        return board

    async def get_board_by_id(self, board_id: str) -> Optional[Board]:
        result = await self.session.execute(select(Board).where(Board.board_id == board_id))
        return result.scalar_one_or_none()

    async def list_boards(self, status: Optional[str] = None) -> List[Board]:
        query = select(Board)
        if status:
            query = query.where(Board.status == status)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create_revision(self, board_id: str, revision_number: int, config_json: dict, approved_by: Optional[str] = None) -> BoardRevision:
        rev = BoardRevision(
            board_id=board_id,
            revision_number=revision_number,
            config_json=config_json,
            approved_by=approved_by,
            status="reviewed" if approved_by else "draft"
        )
        self.session.add(rev)
        await self.session.commit()
        await self.session.refresh(rev)
        return rev
