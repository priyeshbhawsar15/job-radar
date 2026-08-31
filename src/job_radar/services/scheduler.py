import logging
from typing import List
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from job_radar.db.session import AsyncSessionLocal
from job_radar.db.models.board import Board
from job_radar.services.settings_store import load_settings
from job_radar.services.scheduler_alignment import build_pipeline_trigger, next_aligned_run_after
from job_radar.services.engine import execution_engine
from job_radar.services.handoff import handoff_processor
from job_radar.services.discord_notifier import send_pipeline_summary_notification
from job_radar.services.pipeline_progress import finalize_pipeline_run

logger = logging.getLogger(__name__)

class SchedulerService:
    """In-process APScheduler orchestrator managing automated pipeline interval runs."""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self._is_started = False

    def start(self):
        if not self._is_started:
            self.scheduler.start()
            self._is_started = True
            logger.info("In-process APScheduler service started.")
            self.sync_pipeline_job()

    def shutdown(self):
        if self._is_started:
            self.scheduler.shutdown(wait=False)
            self._is_started = False
            logger.info("In-process APScheduler service shutdown.")

    def sync_pipeline_job(self):
        """Sync recurring pipeline execution job according to AppSettings."""
        stored = load_settings()
        job_id = "automated_pipeline_job"

        if not stored.scheduler_enabled or not stored.scheduler_interval_hours:
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
                logger.info("Automated pipeline scheduler disabled. Removed scheduled job.")
            return

        interval_hours = stored.scheduler_interval_hours
        trigger = build_pipeline_trigger(stored.scheduler_anchor_time, interval_hours)
        next_run_time = next_aligned_run_after(stored.scheduler_anchor_time, interval_hours)

        # next_run_time is computed as the first aligned fire strictly after
        # now (never the current instant, even if now sits exactly on a
        # boundary); the CronTrigger itself remains phase-aligned for all
        # subsequent fires, so cadence is never shifted.
        self.scheduler.add_job(
            self.run_scheduled_pipeline,
            trigger=trigger,
            id=job_id,
            replace_existing=True,
            next_run_time=next_run_time,
        )
        logger.info(
            f"Scheduled automated pipeline job every {interval_hours} hours, "
            f"anchored at {stored.scheduler_anchor_time} IST."
        )

    async def run_scheduled_pipeline(self):
        """Execute automated pipeline for selected active boards."""
        stored = load_settings()
        if not stored.scheduler_enabled:
            logger.info("Scheduled pipeline triggered but scheduler is disabled in settings. Skipping.")
            return

        async with AsyncSessionLocal() as session:
            query = select(Board).where(Board.status.in_(["active", "reviewed", "enabled"]))
            if stored.selected_board_ids:
                query = query.where(Board.board_id.in_(stored.selected_board_ids))

            res = await session.execute(query)
            boards = res.scalars().all()
            board_ids = [b.board_id for b in boards]

            if not board_ids:
                logger.info("Scheduled pipeline triggered but no target boards selected/active. Skipping.")
                return

            from job_radar.db.models.run import PipelineRun
            pipeline = PipelineRun(
                trigger="scheduled",
                status="running",
                total_boards=len(board_ids),
            )
            session.add(pipeline)
            await session.commit()
            pipeline_id = pipeline.pipeline_id

        logger.info(f"Starting scheduled pipeline run {pipeline_id} for {len(board_ids)} boards.")

        for b_id in board_ids:
            try:
                await execution_engine.execute_board_run(board_id=b_id, pipeline_id=pipeline_id)
            except Exception as e:
                logger.error(f"Scheduled run error for board {b_id}: {e}")

        try:
            await handoff_processor.process_pending_outbox()
        except Exception as e:
            logger.error(f"Scheduled run outbox error for pipeline {pipeline_id}: {e}")

        async with AsyncSessionLocal() as session:
            try:
                await finalize_pipeline_run(pipeline_id, session)
            except Exception as e:
                logger.error(f"Scheduled pipeline finalization error for {pipeline_id}: {e}")

            try:
                await send_pipeline_summary_notification(pipeline_id, session)
            except Exception as e:
                logger.error(f"Scheduled run notification error for pipeline {pipeline_id}: {e}")

scheduler_service = SchedulerService()
