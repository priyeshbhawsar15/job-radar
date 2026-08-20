from unittest.mock import AsyncMock
import pytest
import pytest_asyncio
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select

from job_radar.db.base import Base
from job_radar.db.models.board import Board
from job_radar.db.models.candidate import CandidateJob
from job_radar.db.models.run import PipelineRun, BoardRun
from job_radar.adapters.base import ExtractedCandidate
from job_radar.services.normalization import NormalizationService, IngestionResult
from job_radar.services.detail_contracts import DetailResult

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
async def test_deduplication_and_normalization(test_session_factory):
    mock_extractor = AsyncMock()
    mock_extractor.fetch_and_enrich.return_value = DetailResult(
        description="<p>Responsibilities include building backend services for Stripe processing systems.</p>\n<p>Qualifications include 5+ years experience in Python and Rust microservices.</p>\n<p>Requirements include strong knowledge of SQL databases and async performance tuning.</p>",
        location="San Francisco, CA",
        employment_type="Full-time",
        department="Engineering",
        salary_raw=None, salary_min=None, salary_max=None, salary_currency=None,
        source="greenhouse", error_code=None
    )
    norm_svc = NormalizationService(session_factory=test_session_factory, detail_extractor=mock_extractor)

    async with test_session_factory() as session:
        board = Board(board_id="board-01", name="Stripe", family="greenhouse", status="active")
        p_run = PipelineRun(pipeline_id="p-01", trigger="manual", status="running")
        b_run = BoardRun(board_run_id="br-01", pipeline_id="p-01", board_id="board-01", stage="running", outcome="in_progress")
        session.add(board)
        session.add(p_run)
        session.add(b_run)
        await session.commit()

    candidates = [
        ExtractedCandidate(
            title="Backend Engineer",
            company="Stripe",
            location="San Francisco, CA",
            raw_url="https://boards.greenhouse.io/stripe/jobs/1",
            fingerprint="fp_test_1"
        ),
        ExtractedCandidate(
            title="Backend Engineer",
            company="Stripe",
            location="San Francisco, CA",
            raw_url="https://boards.greenhouse.io/stripe/jobs/1",
            fingerprint="fp_test_1"
        )
    ]

    res = await norm_svc.ingest_candidates("board-01", "br-01", candidates)
    assert res.observed_count == 2
    assert res.created_count == 1
    assert res.enrichment_succeeded == 1
    assert res.enrichment_failed == 0

@pytest.mark.asyncio
async def test_normalization_persists_none_for_missing_or_invalid_description(test_session_factory):
    mock_extractor = AsyncMock()
    mock_extractor.fetch_and_enrich.return_value = DetailResult.empty(error_code="description_missing")
    norm_svc = NormalizationService(session_factory=test_session_factory, detail_extractor=mock_extractor)

    async with test_session_factory() as session:
        board = Board(board_id="board-01", name="Oracle", family="oracle", status="active")
        p_run = PipelineRun(pipeline_id="p-01", trigger="manual", status="running")
        b_run = BoardRun(board_run_id="br-01", pipeline_id="p-01", board_id="board-01", stage="running", outcome="in_progress")
        session.add(board)
        session.add(p_run)
        session.add(b_run)
        await session.commit()

    oracle_shell = "<html>window.VanityUrlEnabled = true; Accessibility Assistance</html>"
    candidates = [
        ExtractedCandidate(
            title="Senior Developer",
            company="Oracle",
            location="Bangalore",
            raw_url="https://oracle.com/job/123",
            fingerprint="fp_oracle_1",
            extra_payload={"description": oracle_shell}
        ),
        ExtractedCandidate(
            title="Principal Engineer",
            company="Oracle",
            location="Bangalore",
            raw_url="https://oracle.com/job/456",
            fingerprint="fp_oracle_2",
            extra_payload={}
        )
    ]

    res = await norm_svc.ingest_candidates("board-01", "br-01", candidates)
    assert res.observed_count == 2
    assert res.created_count == 2
    assert res.enrichment_succeeded == 0
    assert res.enrichment_failed == 2

    async with test_session_factory() as session:
        db_res = await session.execute(select(CandidateJob))
        jobs = db_res.scalars().all()
        for job in jobs:
            assert job.description is None
            assert job.detail_enrichment_status == "failed"
            assert job.detail_enrichment_error_code == "description_missing"
            assert job.detail_enrichment_attempts == 1

@pytest.mark.asyncio
async def test_normalization_valid_extra_desc_does_not_fetch(test_session_factory):
    mock_extractor = AsyncMock()
    norm_svc = NormalizationService(session_factory=test_session_factory, detail_extractor=mock_extractor)

    async with test_session_factory() as session:
        board = Board(board_id="board-01", name="Philips", family="phenom", status="active")
        p_run = PipelineRun(pipeline_id="p-01", trigger="manual", status="running")
        b_run = BoardRun(board_run_id="br-01", pipeline_id="p-01", board_id="board-01", stage="running", outcome="in_progress")
        session.add(board)
        session.add(p_run)
        session.add(b_run)
        await session.commit()

    valid_desc = "<p>Responsibilities include building high performance distributed systems for Philips devices.</p>\n<p>Qualifications include 5+ years of experience with Rust and C++ software engineering.</p>\n<p>Requirements include familiarity with Linux, async execution, and hardware integration.</p>"
    candidates = [
        ExtractedCandidate(
            title="Senior Rust Engineer",
            company="Philips",
            location="Bangalore, Karnataka, India",
            raw_url="https://www.careers.philips.com/in/en/job/581004/Senior-Rust-Engineer",
            fingerprint="fp_philips_1",
            extra_payload={"description": valid_desc}
        )
    ]

    res = await norm_svc.ingest_candidates("board-01", "br-01", candidates, family="phenom")
    assert res.observed_count == 1
    assert res.created_count == 1
    assert res.enrichment_succeeded == 1
    assert res.enrichment_failed == 0
    mock_extractor.fetch_and_enrich.assert_not_called()

    async with test_session_factory() as session:
        db_res = await session.execute(select(CandidateJob))
        job = db_res.scalar_one()
        assert job.description == valid_desc
        assert job.detail_enrichment_status == "succeeded"
        assert job.detail_enriched_at is not None
