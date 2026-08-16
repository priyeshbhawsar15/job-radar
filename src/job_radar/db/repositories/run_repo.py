from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from job_radar.db.models.run import PipelineRun, BoardRun, RunRequest


class RunRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_pipeline_run(self, trigger: str, total_boards: int) -> PipelineRun:
        run = PipelineRun(trigger=trigger, total_boards=total_boards, status="running")
        self.session.add(run)
        await self.session.commit()
        await self.session.refresh(run)
        return run

    async def get_pipeline_run(self, pipeline_id: str) -> Optional[PipelineRun]:
        result = await self.session.execute(select(PipelineRun).where(PipelineRun.pipeline_id == pipeline_id))
        return result.scalar_one_or_none()

    async def list_pipeline_runs(self, limit: int = 50) -> List[PipelineRun]:
        result = await self.session.execute(
            select(PipelineRun).order_by(PipelineRun.started_at.desc()).limit(limit)
        )
        return list(result.scalars().all())
