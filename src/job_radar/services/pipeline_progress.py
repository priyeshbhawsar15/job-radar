from datetime import datetime, timezone

from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from job_radar.db.models.candidate import RunCandidate
from job_radar.db.models.handoff import HandoffOutbox
from job_radar.db.models.run import BoardRun, PipelineRun


SUCCESSFUL_BOARD_OUTCOMES = {"success", "empty_verified"}


async def finalize_pipeline_run(
    pipeline_id: str,
    session: AsyncSession,
) -> PipelineRun | None:
    """Finalize a parent run from board runs associated with the pipeline."""
    pipeline_result = await session.execute(
        select(PipelineRun).where(PipelineRun.pipeline_id == pipeline_id)
    )
    pipeline = pipeline_result.scalar_one_or_none()
    if pipeline is None:
        return None

    board_result = await session.execute(
        select(BoardRun).where(
            BoardRun.pipeline_id == pipeline_id,
            BoardRun.terminal_at.is_not(None),
        )
    )
    terminal_board_runs = list(board_result.scalars().all())

    successful_count = sum(
        board_run.outcome in SUCCESSFUL_BOARD_OUTCOMES
        for board_run in terminal_board_runs
    )
    explicit_failure_count = sum(
        board_run.outcome not in SUCCESSFUL_BOARD_OUTCOMES
        for board_run in terminal_board_runs
    )
    missing_count = max(pipeline.total_boards - len(terminal_board_runs), 0)
    failed_count = explicit_failure_count + missing_count

    accepted_result = await session.execute(
        select(func.count(distinct(HandoffOutbox.candidate_id)))
        .select_from(HandoffOutbox)
        .join(
            RunCandidate,
            RunCandidate.candidate_id == HandoffOutbox.candidate_id,
        )
        .join(BoardRun, BoardRun.board_run_id == RunCandidate.run_id)
        .where(
            BoardRun.pipeline_id == pipeline_id,
            HandoffOutbox.state == "accepted",
        )
    )

    held_result = await session.execute(
        select(func.count(distinct(HandoffOutbox.candidate_id)))
        .select_from(HandoffOutbox)
        .join(
            RunCandidate,
            RunCandidate.candidate_id == HandoffOutbox.candidate_id,
        )
        .join(BoardRun, BoardRun.board_run_id == RunCandidate.run_id)
        .where(
            BoardRun.pipeline_id == pipeline_id,
            HandoffOutbox.state == "held",
        )
    )

    pipeline.extracted_count = sum(
        board_run.extracted_count for board_run in terminal_board_runs
    )
    pipeline.accepted_count = int(accepted_result.scalar_one() or 0)
    pipeline.held_count = int(held_result.scalar_one() or 0)
    pipeline.failed_count = failed_count
    pipeline.terminal_at = datetime.now(timezone.utc)

    if pipeline.total_boards == 0:
        pipeline.status = "completed"
    elif failed_count == 0:
        pipeline.status = "completed"
    elif failed_count >= pipeline.total_boards and successful_count == 0:
        pipeline.status = "failed"
    else:
        pipeline.status = "partial"

    await session.commit()
    await session.refresh(pipeline)
    return pipeline
