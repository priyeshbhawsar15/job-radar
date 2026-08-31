from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from job_radar.api.v1 import runs
from job_radar.db.models.board import Board
from job_radar.db.models.candidate import CandidateJob, RunCandidate
from job_radar.db.models.handoff import HandoffOutbox
from job_radar.db.models.run import BoardRun, PipelineRun
from conftest import TestingSessionLocal


pytestmark = pytest.mark.asyncio


async def _pipeline(db_session: AsyncSession, **overrides) -> PipelineRun:
    values = {
        "trigger": "manual",
        "status": "running",
        "total_boards": 3,
        "started_at": datetime.now(timezone.utc),
    }
    values.update(overrides)
    pipeline = PipelineRun(**values)
    db_session.add(pipeline)
    await db_session.commit()
    return pipeline


async def _board(db_session: AsyncSession, name: str) -> Board:
    board = Board(name=name, family="generic", status="enabled")
    db_session.add(board)
    await db_session.commit()
    return board


async def test_active_run_returns_newest_pipeline_aggregate(
    client: AsyncClient, db_session: AsyncSession
):
    pipeline = await _pipeline(db_session, total_boards=3)
    completed_board = await _board(db_session, "Completed Co")
    current_board = await _board(db_session, "Current Co")
    db_session.add_all(
        [
            BoardRun(
                pipeline_id=pipeline.pipeline_id,
                board_id=completed_board.board_id,
                stage="completed",
                outcome="success",
                terminal_at=datetime.now(timezone.utc),
            ),
            BoardRun(
                pipeline_id=pipeline.pipeline_id,
                board_id=current_board.board_id,
                stage="normalizing",
                outcome="in_progress",
                terminal_at=None,
            ),
        ]
    )
    await db_session.commit()

    response = await client.get("/api/v1/runs/active")

    assert response.status_code == 200
    data = response.json()
    serialized_started_at = datetime.fromisoformat(data.pop("started_at").replace("Z", "+00:00"))
    assert serialized_started_at == pipeline.started_at
    assert data == {
        "pipeline_id": pipeline.pipeline_id,
        "status": "running",
        "total_boards": 3,
        "completed_boards": 1,
        "remaining_boards": 2,
        "progress_percentage": 33,
        "current_board_name": "Current Co",
        "current_stage": "normalizing",
    }


async def test_active_run_hides_stale_running_pipeline_when_newest_is_terminal(
    client: AsyncClient, db_session: AsyncSession
):
    now = datetime.now(timezone.utc)
    await _pipeline(db_session, started_at=now - timedelta(hours=1), status="running")
    await _pipeline(
        db_session,
        started_at=now,
        status="completed",
        terminal_at=now,
    )

    response = await client.get("/api/v1/runs/active")

    assert response.status_code == 200
    assert response.json() is None


async def test_run_pipeline_task_finalizes_parent_after_board_failure(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    pipeline = await _pipeline(db_session, total_boards=2)
    successful_board = await _board(db_session, "Healthy Co")
    failing_board = await _board(db_session, "Broken Co")

    async def execute_board_run(*, board_id: str, pipeline_id: str):
        if board_id == failing_board.board_id:
            raise RuntimeError("adapter exploded")
        async with TestingSessionLocal() as session:
            board_run = BoardRun(
                pipeline_id=pipeline_id,
                board_id=board_id,
                stage="completed",
                outcome="success",
                extracted_count=7,
                terminal_at=datetime.now(timezone.utc),
            )
            session.add(board_run)
            await session.commit()

            cand = CandidateJob(
                candidate_id="cand-1",
                board_id=board_id,
                identity_key="id-cand-1",
                canonical_url_hash="hash-cand-1",
                company="Healthy Co",
                title="Software Engineer",
                location="Bengaluru",
                public_apply_url="https://example.com/apply/1",
                description="Valid description string long enough to satisfy check",
            )
            session.add(cand)
            await session.flush()

            session.add(
                RunCandidate(
                    run_id=board_run.board_run_id,
                    candidate_id=cand.candidate_id,
                    board_id=board_id,
                    observation_outcome="discovered",
                )
            )
            session.add(
                HandoffOutbox(
                    candidate_id=cand.candidate_id,
                    idempotency_key="cand-1",
                    state="held",
                )
            )
            await session.commit()
            return board_run

    monkeypatch.setattr(runs, "AsyncSessionLocal", TestingSessionLocal)
    monkeypatch.setattr(runs.execution_engine, "execute_board_run", execute_board_run)
    monkeypatch.setattr(runs.handoff_processor, "process_pending_outbox", AsyncMock())
    monkeypatch.setattr(runs, "send_pipeline_summary_notification", AsyncMock())

    await runs.run_pipeline_task(
        [successful_board.board_id, failing_board.board_id],
        pipeline.pipeline_id,
    )

    await db_session.refresh(pipeline)
    assert pipeline.status == "partial"
    assert pipeline.terminal_at is not None
    assert pipeline.extracted_count == 7
    assert pipeline.accepted_count == 0
    assert pipeline.held_count == 1
    assert pipeline.failed_count == 1
