import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select
from job_radar.db.session import AsyncSessionLocal
from job_radar.db.models.board import Board
from job_radar.services.engine import execution_engine

logger = logging.getLogger(__name__)

class SchedulerService:
  """In-process APScheduler orchestrator managing per-board recurring jobs."""

  def __init__(self):
    self.scheduler = AsyncIOScheduler()
    self._is_started = False

  def start(self):
    if not self._is_started:
      self.scheduler.start()
      self._is_started = True
      logger.info("In-process APScheduler service started.")

  def shutdown(self):
    if self._is_started:
      self.scheduler.shutdown(wait=False)
      self._is_started = False
      logger.info("In-process APScheduler service shutdown.")

  async def sync_board_jobs(self):
    """Scan active boards in database and sync cron schedule jobs."""
    async with AsyncSessionLocal() as session:
      res = await session.execute(select(Board).where(Board.status == "active"))
      boards = res.scalars().all()

      for board in boards:
        job_id = f"board_job_{board.board_id}"
        # Check if already scheduled
        if not self.scheduler.get_job(job_id):
          try:
            trigger = CronTrigger.from_crontab(board.schedule_cron)
            self.scheduler.add_job(
              execution_engine.execute_board_run,
              trigger=trigger,
              id=job_id,
              args=[board.board_id],
              replace_existing=True
            )
            logger.info(f"Scheduled cron job for board '{board.name}' ({board.board_id}) with cron '{board.schedule_cron}'")
          except Exception as e:
            logger.error(f"Failed to schedule job for board {board.board_id}: {str(e)}")

scheduler_service = SchedulerService()
