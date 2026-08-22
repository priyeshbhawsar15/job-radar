import httpx
import pytest
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from job_radar.db.models.board import Board
from job_radar.db.models.candidate import CandidateJob, RunCandidate
from job_radar.db.models.handoff import HandoffOutbox
from job_radar.db.models.run import BoardRun, PipelineRun
from job_radar.services import discord_notifier, settings_store


@pytest.fixture(autouse=True)
def isolated_settings_file(tmp_path, monkeypatch):
    path = tmp_path / "app_settings.json"
    monkeypatch.setattr(settings_store, "DEFAULT_CONFIG_PATH", path)
    return path


async def _make_board(db_session: AsyncSession, name="Acme") -> Board:
    board = Board(name=name, family="generic", status="enabled")
    db_session.add(board)
    await db_session.commit()
    return board


async def _make_pipeline_run(db_session: AsyncSession, **overrides) -> PipelineRun:
    defaults = dict(trigger="manual", status="completed")
    defaults.update(overrides)
    pipeline_run = PipelineRun(**defaults)
    db_session.add(pipeline_run)
    await db_session.commit()
    return pipeline_run


async def _make_board_run(db_session: AsyncSession, board: Board, pipeline_run: PipelineRun, **overrides) -> BoardRun:
    defaults = dict(
        pipeline_id=pipeline_run.pipeline_id,
        board_id=board.board_id,
        outcome="success",
        extracted_count=0,
    )
    defaults.update(overrides)
    board_run = BoardRun(**defaults)
    db_session.add(board_run)
    await db_session.commit()
    return board_run


async def _make_candidate(db_session: AsyncSession, board: Board, **overrides) -> CandidateJob:
    defaults = dict(
        board_id=board.board_id,
        identity_key=f"acme:job:{overrides.get('canonical_url_hash', 'x')}",
        canonical_url_hash=overrides.get("canonical_url_hash", "hash-1"),
        title="Software Engineer",
        company="Acme",
        public_apply_url="https://acme.example.com/jobs/1",
    )
    defaults.update(overrides)
    candidate = CandidateJob(**defaults)
    db_session.add(candidate)
    await db_session.commit()
    return candidate


def _enable_webhook(url="https://discord.com/api/webhooks/123/abc"):
    stored = settings_store.load_settings()
    updated = stored.model_copy(update={"discord_webhook_enabled": True, "discord_webhook_url": url})
    settings_store.save_settings(updated)


@pytest.mark.asyncio
async def test_skips_when_webhook_disabled(db_session: AsyncSession):
    stored = settings_store.load_settings()
    updated = stored.model_copy(update={"discord_webhook_enabled": False, "discord_webhook_url": ""})
    settings_store.save_settings(updated)

    pipeline_run = await _make_pipeline_run(db_session)

    with patch("job_radar.services.discord_notifier.httpx.AsyncClient.post", new=AsyncMock()) as mock_post:
        result = await discord_notifier.send_pipeline_summary_notification(pipeline_run.pipeline_id, db_session)

    assert result is False
    mock_post.assert_not_called()


@pytest.mark.asyncio
async def test_skips_when_webhook_url_missing(db_session: AsyncSession):
    stored = settings_store.load_settings()
    updated = stored.model_copy(update={"discord_webhook_enabled": True, "discord_webhook_url": ""})
    settings_store.save_settings(updated)

    pipeline_run = await _make_pipeline_run(db_session)

    with patch("job_radar.services.discord_notifier.httpx.AsyncClient.post", new=AsyncMock()) as mock_post:
        result = await discord_notifier.send_pipeline_summary_notification(pipeline_run.pipeline_id, db_session)

    assert result is False
    mock_post.assert_not_called()


@pytest.mark.asyncio
async def test_returns_false_when_pipeline_not_found(db_session: AsyncSession):
    _enable_webhook()

    with patch("job_radar.services.discord_notifier.httpx.AsyncClient.post", new=AsyncMock()) as mock_post:
        result = await discord_notifier.send_pipeline_summary_notification("nonexistent-id", db_session)

    assert result is False
    mock_post.assert_not_called()


@pytest.mark.asyncio
async def test_builds_correct_summary_metrics_and_posts(db_session: AsyncSession):
    _enable_webhook()

    board = await _make_board(db_session, name="Acme")
    pipeline_run = await _make_pipeline_run(db_session)
    board_run = await _make_board_run(db_session, board, pipeline_run, extracted_count=3)

    discovered = await _make_candidate(db_session, board, canonical_url_hash="hash-discovered")
    re_observed = await _make_candidate(db_session, board, canonical_url_hash="hash-reobserved")
    sent_to_jobops = await _make_candidate(db_session, board, canonical_url_hash="hash-sent")

    db_session.add_all([
        RunCandidate(run_id=board_run.board_run_id, candidate_id=discovered.candidate_id, board_id=board.board_id, observation_outcome="discovered"),
        RunCandidate(run_id=board_run.board_run_id, candidate_id=re_observed.candidate_id, board_id=board.board_id, observation_outcome="re_observed"),
        RunCandidate(run_id=board_run.board_run_id, candidate_id=sent_to_jobops.candidate_id, board_id=board.board_id, observation_outcome="discovered"),
    ])
    db_session.add(HandoffOutbox(
        candidate_id=sent_to_jobops.candidate_id,
        idempotency_key="idem-1",
        state="accepted",
    ))
    await db_session.commit()

    mock_response = httpx.Response(status_code=204, request=httpx.Request("POST", "https://discord.com/api/webhooks/123/abc"))
    with patch("job_radar.services.discord_notifier.httpx.AsyncClient.post", new=AsyncMock(return_value=mock_response)) as mock_post:
        result = await discord_notifier.send_pipeline_summary_notification(pipeline_run.pipeline_id, db_session)

    assert result is True
    mock_post.assert_called_once()
    _, kwargs = mock_post.call_args
    payload = kwargs["json"]
    embed = payload["embeds"][0]

    fields = {f["name"]: f["value"] for f in embed["fields"]}
    assert "3" in fields["Total Jobs Extracted"]
    assert "2" in fields["New Jobs Discovered"]
    assert "1" in fields["Duplicate Jobs Re-observed"]
    assert "1" in fields["Sent to Job Ops"]
    assert "Acme" in fields["Per-Board Breakdown"]


@pytest.mark.asyncio
async def test_embed_color_green_when_all_boards_succeed(db_session: AsyncSession):
    _enable_webhook()

    board = await _make_board(db_session)
    pipeline_run = await _make_pipeline_run(db_session)
    await _make_board_run(db_session, board, pipeline_run, outcome="success")

    mock_response = httpx.Response(status_code=204, request=httpx.Request("POST", "https://discord.com/api/webhooks/123/abc"))
    with patch("job_radar.services.discord_notifier.httpx.AsyncClient.post", new=AsyncMock(return_value=mock_response)) as mock_post:
        await discord_notifier.send_pipeline_summary_notification(pipeline_run.pipeline_id, db_session)

    payload = mock_post.call_args.kwargs["json"]
    assert payload["embeds"][0]["color"] == 0x10B981


@pytest.mark.asyncio
async def test_embed_color_red_and_lists_errors_when_board_run_fails(db_session: AsyncSession):
    _enable_webhook()

    board = await _make_board(db_session, name="Failing Board")
    pipeline_run = await _make_pipeline_run(db_session)
    await _make_board_run(db_session, board, pipeline_run, outcome="timeout", error_code="TIMEOUT")

    mock_response = httpx.Response(status_code=204, request=httpx.Request("POST", "https://discord.com/api/webhooks/123/abc"))
    with patch("job_radar.services.discord_notifier.httpx.AsyncClient.post", new=AsyncMock(return_value=mock_response)) as mock_post:
        await discord_notifier.send_pipeline_summary_notification(pipeline_run.pipeline_id, db_session)

    payload = mock_post.call_args.kwargs["json"]
    embed = payload["embeds"][0]
    assert embed["color"] == 0xEF4444
    fields = {f["name"]: f["value"] for f in embed["fields"]}
    assert "Failing Board" in fields["Errors"]
    assert "TIMEOUT" in fields["Errors"]


@pytest.mark.asyncio
async def test_returns_false_on_delivery_failure(db_session: AsyncSession):
    _enable_webhook()

    pipeline_run = await _make_pipeline_run(db_session)

    with patch(
        "job_radar.services.discord_notifier.httpx.AsyncClient.post",
        new=AsyncMock(side_effect=httpx.ConnectError("connection refused")),
    ):
        result = await discord_notifier.send_pipeline_summary_notification(pipeline_run.pipeline_id, db_session)

    assert result is False
