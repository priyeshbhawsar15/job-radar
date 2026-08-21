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


ORACLE_CONFIG_FIXTURE = {
    "api_origin": "https://eeho.fa.us2.oraclecloud.com",
    "allowed_origins": [
        "https://eeho.fa.us2.oraclecloud.com",
        "https://careers.oracle.com",
    ],
    "site_number": "CX_45001",
}

LISTING_CONFIG_FIXTURE = {
    "keyword": "Software Engineer",
    "location": "India",
    "limit": 10,
}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "board_id,board_name,target_url",
    [
        ("board-jpmc-test", "JPMC Test", "https://careers.jpmorgan.com/in/en/search-results"),
        ("board-amex-test", "AMEX Test", "https://jobs.americanexpress.com/in/search-results"),
    ],
)
async def test_oracle_family_without_listing_capability_keeps_browser_path(
    test_session_factory, board_id, board_name, target_url
):
    async with test_session_factory() as session:
        board = Board(
            board_id=board_id,
            name=board_name,
            family="oracle",
            status="active",
            consecutive_parser_failures=0,
        )
        rev = BoardRevision(
            revision_id=f"rev-{board_id}",
            board_id=board_id,
            revision_number=1,
            status="reviewed",
            config_json={
                "target_url": target_url,
                "schedule_cron": "0 */6 * * *",
            },
        )
        board.current_revision_id = rev.revision_id
        session.add(board)
        session.add(rev)
        await session.commit()

    engine = PipelineExecutionEngine(session_factory=test_session_factory)

    from job_radar.adapters.base import ExtractedCandidate
    mock_candidate = ExtractedCandidate(
        title="Test Engineer",
        company=board_name,
        location="India",
        raw_url=f"{target_url}/job/123",
        fingerprint="fp_test_oracle_browser",
    )

    with patch.object(engine.browser_client, "fetch_board_html", new_callable=AsyncMock) as mock_fetch, \
         patch("job_radar.services.oracle_listing.fetch_oracle_listing_payload", new_callable=AsyncMock) as mock_listing, \
         patch("job_radar.services.engine.adapter_registry.get") as mock_adapter_get, \
         patch("job_radar.services.engine.normalization_service.ingest_candidates", new_callable=AsyncMock) as mock_ingest:

        mock_fetch.return_value = "<html>browser-html</html>"
        mock_adapter = MagicMock()
        mock_adapter.parse_raw_payload.return_value = [mock_candidate]
        mock_adapter_get.return_value = mock_adapter

        from job_radar.services.normalization import IngestionResult
        mock_ingest.return_value = IngestionResult(
            observed_count=1,
            created_count=1,
            enrichment_succeeded=1,
            enrichment_failed=0,
        )

        board_run = await engine.execute_board_run(board_id)

        assert board_run.outcome == "success"
        mock_fetch.assert_called_once()
        mock_listing.assert_not_called()
        mock_adapter.parse_raw_payload.assert_called_once()
        _, adapter_kwargs = mock_adapter.parse_raw_payload.call_args
        assert adapter_kwargs["payload"] == "<html>browser-html</html>"

        mock_ingest.assert_called_once()
        _, ingest_kwargs = mock_ingest.call_args
        assert ingest_kwargs["provider_config"] == {
            "target_url": target_url,
            "schedule_cron": "0 */6 * * *",
        }


@pytest.mark.asyncio
async def test_oracle_board_with_listing_capability_uses_direct_json_and_skips_browser(
    test_session_factory,
):
    board_id = "board-oracle-direct-test"
    target_url = "https://careers.oracle.com/jobs/#en/sites/jobsearch/requisitions"
    revision_config = {
        "target_url": target_url,
        "schedule_cron": "0 */6 * * *",
        "oracle_detail": dict(ORACLE_CONFIG_FIXTURE),
        "oracle_listing": dict(LISTING_CONFIG_FIXTURE),
    }

    async with test_session_factory() as session:
        board = Board(
            board_id=board_id,
            name="Oracle Direct Test",
            family="oracle",
            status="active",
            consecutive_parser_failures=0,
        )
        rev = BoardRevision(
            revision_id=f"rev-{board_id}",
            board_id=board_id,
            revision_number=1,
            status="reviewed",
            config_json=revision_config,
        )
        board.current_revision_id = rev.revision_id
        session.add(board)
        session.add(rev)
        await session.commit()

    engine = PipelineExecutionEngine(session_factory=test_session_factory)

    from job_radar.adapters.base import ExtractedCandidate
    mock_candidate = ExtractedCandidate(
        title="Test Engineer",
        company="Oracle Direct Test",
        location="India",
        raw_url=f"{target_url}/job/123",
        fingerprint="fp_test_oracle_direct",
    )
    fixture_json = json.dumps({"items": [{"requisitionList": []}]})

    with patch.object(engine.browser_client, "fetch_board_html", new_callable=AsyncMock) as mock_fetch, \
         patch("job_radar.services.oracle_listing.fetch_oracle_listing_payload", new_callable=AsyncMock) as mock_listing, \
         patch("job_radar.services.engine.adapter_registry.get") as mock_adapter_get, \
         patch("job_radar.services.engine.normalization_service.ingest_candidates", new_callable=AsyncMock) as mock_ingest:

        mock_fetch.side_effect = AssertionError("browser path unexpectedly called")
        mock_listing.return_value = fixture_json
        mock_adapter = MagicMock()
        mock_adapter.parse_raw_payload.return_value = [mock_candidate]
        mock_adapter_get.return_value = mock_adapter

        from job_radar.services.normalization import IngestionResult
        mock_ingest.return_value = IngestionResult(
            observed_count=1,
            created_count=1,
            enrichment_succeeded=1,
            enrichment_failed=0,
        )

        board_run = await engine.execute_board_run(board_id)

        mock_fetch.assert_not_called()
        mock_listing.assert_awaited_once()
        call_args, _ = mock_listing.call_args
        assert call_args[0] == LISTING_CONFIG_FIXTURE
        assert call_args[1] == ORACLE_CONFIG_FIXTURE
        import httpx
        assert isinstance(call_args[2], httpx.AsyncClient)

        mock_adapter.parse_raw_payload.assert_called_once()
        _, adapter_kwargs = mock_adapter.parse_raw_payload.call_args
        assert adapter_kwargs["payload"] == fixture_json
        assert adapter_kwargs["target_url"] == target_url

        mock_ingest.assert_called_once()
        _, ingest_kwargs = mock_ingest.call_args
        assert ingest_kwargs["extracted_candidates"] == [mock_candidate]
        assert ingest_kwargs["provider_config"] == revision_config

        assert board_run.extracted_count == 1
        assert board_run.outcome == "success"


@pytest.mark.asyncio
async def test_oracle_listing_error_becomes_provider_failure_without_ingestion(
    test_session_factory,
):
    board_id = "board-oracle-listing-error-test"
    target_url = "https://careers.oracle.com/jobs/#en/sites/jobsearch/requisitions"
    revision_config = {
        "target_url": target_url,
        "schedule_cron": "0 */6 * * *",
        "oracle_detail": dict(ORACLE_CONFIG_FIXTURE),
        "oracle_listing": dict(LISTING_CONFIG_FIXTURE),
    }

    async with test_session_factory() as session:
        board = Board(
            board_id=board_id,
            name="Oracle Listing Error Test",
            family="oracle",
            status="active",
            consecutive_parser_failures=0,
        )
        rev = BoardRevision(
            revision_id=f"rev-{board_id}",
            board_id=board_id,
            revision_number=1,
            status="reviewed",
            config_json=revision_config,
        )
        board.current_revision_id = rev.revision_id
        session.add(board)
        session.add(rev)
        await session.commit()

    engine = PipelineExecutionEngine(session_factory=test_session_factory)

    from job_radar.services.oracle_listing import OracleListingError

    with patch.object(engine.browser_client, "fetch_board_html", new_callable=AsyncMock) as mock_fetch, \
         patch("job_radar.services.oracle_listing.fetch_oracle_listing_payload", new_callable=AsyncMock) as mock_listing, \
         patch("job_radar.services.engine.normalization_service.ingest_candidates", new_callable=AsyncMock) as mock_ingest, \
         patch("asyncio.sleep", new_callable=AsyncMock):

        mock_fetch.side_effect = AssertionError("browser path unexpectedly called")
        mock_listing.side_effect = OracleListingError("invalid_payload")

        board_run = await engine.execute_board_run(board_id)

        assert mock_listing.await_count == 2
        mock_fetch.assert_not_called()
        mock_ingest.assert_not_called()
        assert board_run.outcome == "provider_failure"

    async with test_session_factory() as session:
        from job_radar.db.models.run import BoardRun
        res = await session.execute(
            select(BoardRun).where(BoardRun.board_id == board_id)
        )
        row = res.scalar_one()
        assert row.error_code == "invalid_payload"
