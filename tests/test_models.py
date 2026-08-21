import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from job_radar.db.models.board import Board, BoardRevision
from job_radar.db.models.run import PipelineRun, BoardRun, RunRequest, ExecutionAttempt
from job_radar.db.models.candidate import CandidateJob, RunCandidate
from job_radar.db.models.handoff import HandoffOutbox, HandoffAttempt
from job_radar.db.models.audit import AuditEvent
from job_radar.db.repositories.board_repo import BoardRepository
from job_radar.db.repositories.run_repo import RunRepository


@pytest.mark.asyncio
async def test_board_and_revision_creation(db_session: AsyncSession):
    repo = BoardRepository(db_session)
    board = await repo.create_board(name="Coupa Careers", family="lever", status="draft")
    assert board.board_id is not None
    assert board.name == "Coupa Careers"
    assert board.status == "draft"

    revision = await repo.create_revision(
        board_id=board.board_id,
        revision_number=1,
        config_json={"url": "https://api.lever.co/v0/postings/coupa"},
        approved_by="admin@jobradar"
    )
    assert revision.revision_id is not None
    assert revision.revision_number == 1
    assert revision.status == "reviewed"


@pytest.mark.asyncio
async def test_pipeline_and_board_run(db_session: AsyncSession):
    run_repo = RunRepository(db_session)
    pipeline = await run_repo.create_pipeline_run(trigger="scheduled", total_boards=5)
    assert pipeline.pipeline_id is not None
    assert pipeline.status == "running"

    board_repo = BoardRepository(db_session)
    board = await board_repo.create_board(name="Amazon", family="amazon_jobs", status="enabled")

    board_run = BoardRun(
        pipeline_id=pipeline.pipeline_id,
        board_id=board.board_id,
        stage="completed",
        outcome="success",
        duration_ms=450,
        extracted_count=12
    )
    db_session.add(board_run)
    await db_session.commit()
    await db_session.refresh(board_run)

    assert board_run.board_run_id is not None
    assert board_run.extracted_count == 12


@pytest.mark.asyncio
async def test_candidate_job_and_outbox(db_session: AsyncSession):
    board_repo = BoardRepository(db_session)
    board = await board_repo.create_board(name="Qualcomm", family="eightfold", status="enabled")

    candidate = CandidateJob(
        board_id=board.board_id,
        identity_key="eightfold_qc_1001",
        canonical_url_hash="abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        title="Staff Engineer",
        company="Qualcomm",
        location="San Diego, CA",
        public_apply_url="https://qualcomm.eightfold.ai/careers/job/1001",
        employment_type="Full-time",
        department="Hardware"
    )
    db_session.add(candidate)
    await db_session.commit()
    await db_session.refresh(candidate)

    assert candidate.candidate_id is not None
    assert candidate.detail_enrichment_status == "pending"
    assert candidate.detail_enrichment_attempts == 0
    assert candidate.detail_enrichment_error_code is None
    assert candidate.detail_enriched_at is None

    outbox = HandoffOutbox(
        candidate_id=candidate.candidate_id,
        idempotency_key=f"job_radar_cand_{candidate.candidate_id}_v1",
        state="not_eligible"
    )
    db_session.add(outbox)
    await db_session.commit()
    await db_session.refresh(outbox)

    assert outbox.outbox_id is not None
    assert outbox.state == "not_eligible"


@pytest.mark.asyncio
async def test_audit_event_logging(db_session: AsyncSession):
    event = AuditEvent(
        actor="operator",
        role="admin",
        action="board_enable",
        entity_type="Board",
        entity_id="test-board-uuid",
        reason="Manual enablement for initial tick"
    )
    db_session.add(event)
    await db_session.commit()
    await db_session.refresh(event)

    assert event.event_id is not None
    assert event.role == "admin"


@pytest.mark.asyncio
async def test_philips_seed_configuration(db_session: AsyncSession):
    from job_radar.db.seed import INITIAL_BOARDS
    philips_items = [b for b in INITIAL_BOARDS if b[0] == "board-philips"]
    assert len(philips_items) == 1
    philips_item = philips_items[0]
    assert len(philips_item) == 5
    b_id, name, family, target_url, phenom_cfg = philips_item
    assert family == "phenom"
    assert "allowed_origins" in phenom_cfg
    assert phenom_cfg["allowed_origins"] == ["https://www.careers.philips.com"]


def test_jpmc_seed_oracle_detail_config_contains_only_strict_origins():
    from urllib.parse import urlparse
    from job_radar.db.seed import INITIAL_BOARDS
    from job_radar.services.oracle_detail import validate_oracle_config

    jpmc_items = [b for b in INITIAL_BOARDS if b[0] == "board-jpmc"]
    assert len(jpmc_items) == 1
    jpmc_item = jpmc_items[0]
    assert len(jpmc_item) == 5
    b_id, name, family, target_url, jpmc_cfg = jpmc_item
    assert family == "oracle"

    assert jpmc_cfg["api_origin"] in jpmc_cfg["allowed_origins"]
    assert validate_oracle_config(jpmc_cfg) is True

    for origin in jpmc_cfg["allowed_origins"]:
        parsed = urlparse(origin)
        assert parsed.scheme == "https"
        assert not parsed.username
        assert not parsed.password
        assert not parsed.query
        assert not parsed.fragment
        assert parsed.path in ("", "/")
