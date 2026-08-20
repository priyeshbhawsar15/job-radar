import pytest
import pytest_asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from job_radar.db.base import Base
from job_radar.db.models.board import Board, BoardRevision
from job_radar.services.engine import PipelineExecutionEngine

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture
async def test_session_factory():
  engine = create_async_engine(TEST_DB_URL, echo=False)
  async with engine.begin() as conn:
    await conn.run_sync(Base.metadata.create_all)

  session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
  yield session_factory
  await engine.dispose()

@pytest.mark.asyncio
async def test_execution_engine_consecutive_failure_hold(test_session_factory):
  # 1. Setup board in DB
  async with test_session_factory() as session:
    board = Board(
      board_id="board-test-01",
      name="Test Board",
      family="greenhouse",
      status="active",
      consecutive_parser_failures=2
    )
    rev = BoardRevision(
      revision_id="rev-test-01",
      board_id="board-test-01",
      revision_number=1,
      status="reviewed",
      config_json={
        "target_url": "https://boards.greenhouse.io/test",
        "schedule_cron": "0 */6 * * *"
      }
    )
    board.current_revision_id = rev.revision_id
    session.add(board)
    session.add(rev)
    await session.commit()

  engine = PipelineExecutionEngine(session_factory=test_session_factory)

  # Mock browser client to raise error
  with patch.object(engine.browser_client, "fetch_board_html", new_callable=AsyncMock) as mock_fetch:
    mock_fetch.side_effect = RuntimeError("Mocked browser service crash")

    board_run = await engine.execute_board_run("board-test-01")
    assert board_run.outcome == "provider_failure"

  # Verify board is now HELD after reaching 3 consecutive failures
  async with test_session_factory() as session:
    res = await session.execute(
      Board.__table__.select().where(Board.board_id == "board-test-01")
    )
    row = res.fetchone()
    assert row.status == "held"
    assert row.consecutive_parser_failures == 3


@pytest.mark.asyncio
async def test_execution_engine_partial_outcome_on_enrichment_failure(test_session_factory):
    async with test_session_factory() as session:
        board = Board(
            board_id="board-philips-test",
            name="Philips Test",
            family="phenom",
            status="active",
            consecutive_parser_failures=0
        )
        rev = BoardRevision(
            revision_id="rev-philips-test",
            board_id="board-philips-test",
            revision_number=1,
            status="reviewed",
            config_json={
                "target_url": "https://www.careers.philips.com/in/en/search-results",
                "schedule_cron": "0 */6 * * *"
            }
        )
        board.current_revision_id = rev.revision_id
        session.add(board)
        session.add(rev)
        await session.commit()

    engine = PipelineExecutionEngine(session_factory=test_session_factory)

    from job_radar.adapters.base import ExtractedCandidate
    mock_candidate = ExtractedCandidate(
        title="Test Engineer",
        company="Philips Test",
        location="India",
        raw_url="https://www.careers.philips.com/in/en/job/123/Test-Engineer",
        fingerprint="fp_test_123"
    )

    with patch.object(engine.browser_client, "fetch_board_html", new_callable=AsyncMock) as mock_fetch, \
         patch("job_radar.services.engine.adapter_registry.get") as mock_adapter_get, \
         patch("job_radar.services.engine.normalization_service.ingest_candidates", new_callable=AsyncMock) as mock_ingest:

        mock_fetch.return_value = "<html></html>"
        mock_adapter = MagicMock()
        mock_adapter.parse_raw_payload.return_value = [mock_candidate]
        mock_adapter_get.return_value = mock_adapter

        from job_radar.services.normalization import IngestionResult
        mock_ingest.return_value = IngestionResult(
            observed_count=1,
            created_count=1,
            enrichment_succeeded=0,
            enrichment_failed=1
        )

        board_run = await engine.execute_board_run("board-philips-test")
        assert board_run.outcome == "partial"

        async with test_session_factory() as session:
            from job_radar.db.models.run import ExecutionAttempt
            res = await session.execute(
                select(ExecutionAttempt).where(ExecutionAttempt.request_id != None)
            )
            attempts = res.scalars().all()
            assert len(attempts) > 0
            assert attempts[0].outcome == "partial"
