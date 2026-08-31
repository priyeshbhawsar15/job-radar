import logging
from typing import Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from job_radar.db.models.board import Board
from job_radar.db.models.candidate import RunCandidate
from job_radar.db.models.handoff import HandoffOutbox
from job_radar.db.models.run import BoardRun, PipelineRun
from job_radar.services.settings_store import load_settings

logger = logging.getLogger(__name__)

COLOR_SUCCESS = 0x10B981
COLOR_ERROR = 0xEF4444


async def send_pipeline_summary_notification(pipeline_id: str, db_session: AsyncSession) -> bool:
    stored = load_settings()
    if not stored.discord_webhook_enabled or not stored.discord_webhook_url:
        return False

    result = await db_session.execute(
        select(PipelineRun)
        .options(selectinload(PipelineRun.board_runs).selectinload(BoardRun.run_candidates))
        .where(PipelineRun.pipeline_id == pipeline_id)
    )
    pipeline_run = result.scalar_one_or_none()
    if pipeline_run is None:
        return False

    board_ids = [board_run.board_id for board_run in pipeline_run.board_runs]
    boards_by_id = {}
    if board_ids:
        board_result = await db_session.execute(select(Board).where(Board.board_id.in_(board_ids)))
        boards_by_id = {board.board_id: board for board in board_result.scalars().all()}

    total_extracted = 0
    new_discovered = 0
    re_observed = 0
    board_breakdown = []
    error_lines = []
    all_candidate_ids = []

    for board_run in pipeline_run.board_runs:
        total_extracted += board_run.extracted_count
        board_name = boards_by_id.get(board_run.board_id).name if board_run.board_id in boards_by_id else board_run.board_id

        run_discovered = 0
        run_re_observed = 0
        for run_candidate in board_run.run_candidates:
            all_candidate_ids.append(run_candidate.candidate_id)
            if run_candidate.observation_outcome == "discovered":
                new_discovered += 1
                run_discovered += 1
            elif run_candidate.observation_outcome == "re_observed":
                re_observed += 1
                run_re_observed += 1

        if run_discovered > 0:
            board_breakdown.append(f"**{board_name}** — {run_discovered} new, {run_re_observed} re-observed")

        if board_run.outcome != "success":
            detail = board_run.error_code or board_run.outcome
            error_lines.append(f"**{board_name}**: {board_run.outcome} ({detail})")

    sent_to_jobops = 0
    if all_candidate_ids:
        handoff_result = await db_session.execute(
            select(HandoffOutbox).where(
                HandoffOutbox.candidate_id.in_(all_candidate_ids),
                HandoffOutbox.state == "accepted",
            )
        )
        sent_to_jobops = len(handoff_result.scalars().all())

    color = COLOR_ERROR if error_lines else COLOR_SUCCESS

    # Discord embed field values are hard-capped at 1024 characters.
    # Format per-board breakdown safely within limits.
    if len(board_breakdown) > 15:
        truncated_items = board_breakdown[:15]
        breakdown_val = "\n".join(truncated_items) + f"\n*...and {len(board_breakdown) - 15} more boards*"
    else:
        breakdown_val = "\n".join(board_breakdown) if board_breakdown else "No new jobs discovered"

    if len(breakdown_val) > 1024:
        breakdown_val = breakdown_val[:1000] + "\n*...truncated*"

    fields = [
        {"name": "Total Jobs Extracted", "value": str(total_extracted), "inline": True},
        {"name": "New Jobs Discovered", "value": str(new_discovered), "inline": True},
        {"name": "Duplicate Jobs Re-observed", "value": str(re_observed), "inline": True},
        {"name": "Sent to Job Ops", "value": str(sent_to_jobops), "inline": True},
        {"name": "Per-Board Breakdown", "value": breakdown_val, "inline": False},
    ]
    if error_lines:
        err_text = "\n".join(error_lines)
        if len(err_text) > 1024:
            err_text = err_text[:1000] + "\n...truncated"
        fields.append({"name": "Errors", "value": err_text, "inline": False})

    embed = {
        "title": "🎯 Job Radar Pipeline Run Summary",
        "color": color,
        "fields": fields,
    }
    payload = {"embeds": [embed]}

    try:
        async with httpx.AsyncClient(timeout=10.0) as http_client:
            response = await http_client.post(stored.discord_webhook_url, json=payload)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        logger.warning("Failed to deliver Discord pipeline summary notification: %s", exc)
        return False

    return True
