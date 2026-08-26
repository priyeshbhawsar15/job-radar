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


@pytest.mark.asyncio
async def test_jpmc_detail_title_replaces_exact_oracle_html_placeholder(test_session_factory):
    mock_extractor = AsyncMock()
    mock_extractor.fetch_and_enrich.return_value = DetailResult(
        title="Lead Software Engineer - Sales",
        description="<p>Responsibilities include building backend services for JPMC processing systems.</p>\n<p>Qualifications include 8+ years experience in Java and Python microservices.</p>\n<p>Requirements include strong knowledge of SQL databases.</p>",
        location="Hyderabad, Telangana, India",
        source="oracle_hcm_detail",
        error_code=None,
    )
    norm_svc = NormalizationService(session_factory=test_session_factory, detail_extractor=mock_extractor)

    async with test_session_factory() as session:
        board = Board(board_id="board-jpmc", name="JPMC", family="oracle", status="active")
        p_run = PipelineRun(pipeline_id="p-01", trigger="manual", status="running")
        b_run = BoardRun(board_run_id="br-01", pipeline_id="p-01", board_id="board-jpmc", stage="running", outcome="in_progress")
        session.add_all([board, p_run, b_run])
        await session.commit()

    candidate = ExtractedCandidate(
        title="JPMC Job Requisition 210729984",
        company="JPMC",
        location="Hyderabad, Telangana, India",
        raw_url="https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/job/210729984/",
        fingerprint="fp_jpmc_210729984",
        extra_payload={"public_job_id": "210729984"},
    )

    res = await norm_svc.ingest_candidates("board-jpmc", "br-01", [candidate], family="oracle")
    assert res.enrichment_succeeded == 1

    async with test_session_factory() as session:
        db_res = await session.execute(select(CandidateJob))
        job = db_res.scalar_one()
        assert job.title == "Lead Software Engineer - Sales"
        assert job.detail_enrichment_status == "succeeded"
        assert job.description is not None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "listing_title, company, family, public_id, detail_title",
    [
        ("Software Developer 4", "Oracle", "oracle", "337440", "Software Developer IV - Backend"),
        ("Software Engineer II", "AMEX", "oracle", "210001", "Lead Software Engineer"),
        ("Software Engineer - Java", "JPMC", "oracle", "210729984", "Sr Software Engineer - Java"),
    ],
)
async def test_detail_title_does_not_replace_valid_listing_title(
    test_session_factory, listing_title, company, family, public_id, detail_title
):
    valid_test_description = (
        "<p>Responsibilities include building backend services for software processing systems across multiple domains.</p>\n"
        "<p>Qualifications include 5+ years experience in Java and Python microservices and distributed systems.</p>\n"
        "<p>Requirements include strong knowledge of SQL databases and async performance tuning.</p>"
    )

    mock_extractor = AsyncMock()
    mock_extractor.fetch_and_enrich.return_value = DetailResult(
        title=detail_title,
        description=valid_test_description,
        location="Bengaluru, Karnataka, India",
        source="oracle_hcm_detail",
        error_code=None,
    )
    norm_svc = NormalizationService(session_factory=test_session_factory, detail_extractor=mock_extractor)

    board_id = f"board-{company.lower()}"
    async with test_session_factory() as session:
        board = Board(board_id=board_id, name=company, family=family, status="active")
        p_run = PipelineRun(pipeline_id="p-01", trigger="manual", status="running")
        b_run = BoardRun(board_run_id=f"br-{company.lower()}", pipeline_id="p-01", board_id=board_id, stage="running", outcome="in_progress")
        session.add_all([board, p_run, b_run])
        await session.commit()

    candidate = ExtractedCandidate(
        title=listing_title,
        company=company,
        location="Bengaluru, Karnataka, India",
        raw_url=f"https://{company.lower()}.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/job/{public_id}/",
        fingerprint=f"fp_{company.lower()}_{public_id}",
        extra_payload={"public_job_id": public_id},
    )

    res = await norm_svc.ingest_candidates(board_id, f"br-{company.lower()}", [candidate], family=family)
    assert res.enrichment_succeeded == 1

    async with test_session_factory() as session:
        db_res = await session.execute(select(CandidateJob).where(CandidateJob.board_id == board_id))
        job = db_res.scalar_one()
        assert job.title == listing_title
        assert job.detail_enrichment_status == "succeeded"
        assert job.description is not None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "cand_title, detail_title_arg",
    [
        ("JPMC Job Requisition 210729984", None),
        ("JPMC Job Requisition 210729984", ""),
        ("JPMC Job Requisition 210729984", "   "),
        ("JPMC Job Requisition 210729984", 12345),
        ("JPMC Job Requisition 210729984", ["Lead Engineer"]),
        ("JPMC Job Requisition 210729984", {"t": "Lead Engineer"}),
        ("JPMC Job Requisition 999999999", "Lead Software Engineer - Sales"),
        ("JPMC Job Requisition 210729984 (Updated)", "Lead Software Engineer - Sales"),
        ("JP Morgan Job Requisition 210729984", "Lead Software Engineer - Sales"),
        ("JPMC Job Requisition210729984", "Lead Software Engineer - Sales"),
    ],
)
async def test_detail_title_invalid_and_near_match_safety(test_session_factory, cand_title, detail_title_arg):
    valid_test_description = (
        "<p>Responsibilities include building backend services for software processing systems across multiple domains.</p>\n"
        "<p>Qualifications include 5+ years experience in Java and Python microservices and distributed systems.</p>\n"
        "<p>Requirements include strong knowledge of SQL databases and async performance tuning.</p>"
    )

    mock_extractor = AsyncMock()
    mock_extractor.fetch_and_enrich.return_value = DetailResult(
        title=detail_title_arg,
        description=valid_test_description,
        location="Hyderabad, Telangana, India",
        source="oracle_hcm_detail",
        error_code=None,
    )
    norm_svc = NormalizationService(session_factory=test_session_factory, detail_extractor=mock_extractor)

    async with test_session_factory() as session:
        board = Board(board_id="board-jpmc-safety", name="JPMC", family="oracle", status="active")
        p_run = PipelineRun(pipeline_id="p-safety", trigger="manual", status="running")
        b_run = BoardRun(board_run_id="br-safety", pipeline_id="p-safety", board_id="board-jpmc-safety", stage="running", outcome="in_progress")
        session.add_all([board, p_run, b_run])
        await session.commit()

    candidate = ExtractedCandidate(
        title=cand_title,
        company="JPMC",
        location="Hyderabad, Telangana, India",
        raw_url="https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/job/210729984/",
        fingerprint=f"fp_jpmc_safety_{hash(cand_title)}",
        extra_payload={"public_job_id": "210729984"},
    )

    res = await norm_svc.ingest_candidates("board-jpmc-safety", "br-safety", [candidate], family="oracle")
    assert res.enrichment_succeeded == 1

    async with test_session_factory() as session:
        db_res = await session.execute(select(CandidateJob).where(CandidateJob.board_id == "board-jpmc-safety"))
        job = db_res.scalar_one()
        assert job.title == cand_title
        assert job.detail_enrichment_status == "succeeded"


@pytest.mark.asyncio
async def test_detail_title_failed_enrichment_leaves_title_and_records_failure(test_session_factory):
    mock_extractor = AsyncMock()
    mock_extractor.fetch_and_enrich.return_value = DetailResult.empty(error_code="invalid_payload")
    norm_svc = NormalizationService(session_factory=test_session_factory, detail_extractor=mock_extractor)

    async with test_session_factory() as session:
        board = Board(board_id="board-jpmc-fail", name="JPMC", family="oracle", status="active")
        p_run = PipelineRun(pipeline_id="p-fail", trigger="manual", status="running")
        b_run = BoardRun(board_run_id="br-fail", pipeline_id="p-fail", board_id="board-jpmc-fail", stage="running", outcome="in_progress")
        session.add_all([board, p_run, b_run])
        await session.commit()

    candidate = ExtractedCandidate(
        title="JPMC Job Requisition 210729984",
        company="JPMC",
        location="Hyderabad, Telangana, India",
        raw_url="https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/job/210729984/",
        fingerprint="fp_jpmc_fail_210729984",
    )

    res = await norm_svc.ingest_candidates("board-jpmc-fail", "br-fail", [candidate], family="oracle")
    assert res.enrichment_failed == 1

    async with test_session_factory() as session:
        db_res = await session.execute(select(CandidateJob).where(CandidateJob.board_id == "board-jpmc-fail"))
        job = db_res.scalar_one()
        assert job.title == "JPMC Job Requisition 210729984"
        assert job.detail_enrichment_status == "failed"
        assert job.detail_enrichment_error_code == "invalid_payload"


@pytest.mark.asyncio
async def test_detail_title_replacement_persistence_invariants(test_session_factory):
    valid_test_description = (
        "<p>Responsibilities include building backend services for software processing systems across multiple domains.</p>\n"
        "<p>Qualifications include 5+ years experience in Java and Python microservices and distributed systems.</p>\n"
        "<p>Requirements include strong knowledge of SQL databases and async performance tuning.</p>"
    )

    mock_extractor = AsyncMock()
    mock_extractor.fetch_and_enrich.return_value = DetailResult(
        title="Lead Software Engineer - Sales",
        description=valid_test_description,
        location="Hyderabad, Telangana, India",
        source="oracle_hcm_detail",
        error_code=None,
    )
    norm_svc = NormalizationService(session_factory=test_session_factory, detail_extractor=mock_extractor)

    async with test_session_factory() as session:
        board = Board(board_id="board-jpmc-inv", name="JPMC", family="oracle", status="active")
        p_run = PipelineRun(pipeline_id="p-inv", trigger="manual", status="running")
        b_run = BoardRun(board_run_id="br-inv", pipeline_id="p-inv", board_id="board-jpmc-inv", stage="running", outcome="in_progress")
        b_run2 = BoardRun(board_run_id="br-inv-2", pipeline_id="p-inv", board_id="board-jpmc-inv", stage="running", outcome="in_progress")
        session.add_all([board, p_run, b_run, b_run2])
        await session.commit()

    candidate = ExtractedCandidate(
        title="JPMC Job Requisition 210729984",
        company="JPMC",
        location="Hyderabad, Telangana, India",
        raw_url="https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/job/210729984/",
        fingerprint="fp_jpmc_inv_210729984",
    )

    res = await norm_svc.ingest_candidates("board-jpmc-inv", "br-inv", [candidate], family="oracle")
    assert res.enrichment_succeeded == 1

    async with test_session_factory() as session:
        db_res = await session.execute(select(CandidateJob).where(CandidateJob.board_id == "board-jpmc-inv"))
        job = db_res.scalar_one()
        initial_identity_key = job.identity_key
        initial_url_hash = job.canonical_url_hash
        assert job.title == "Lead Software Engineer - Sales"

    # Re-observe candidate with fallback title when existing row has already corrected title
    re_candidate = ExtractedCandidate(
        title="JPMC Job Requisition 210729984",
        company="JPMC",
        location="Hyderabad, Telangana, India",
        raw_url="https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/job/210729984/",
        fingerprint="fp_jpmc_inv_210729984",
    )

    res2 = await norm_svc.ingest_candidates("board-jpmc-inv", "br-inv-2", [re_candidate], family="oracle")
    assert res2.observed_count == 1

    async with test_session_factory() as session:
        db_res = await session.execute(select(CandidateJob).where(CandidateJob.board_id == "board-jpmc-inv"))
        job2 = db_res.scalar_one()
        assert job2.title == "Lead Software Engineer - Sales"
        assert job2.identity_key == initial_identity_key
        assert job2.canonical_url_hash == initial_url_hash


@pytest.mark.asyncio
async def test_missing_location_preservation_and_outbox_queueing(test_session_factory):
    from job_radar.db.models.handoff import HandoffOutbox
    valid_test_description = (
        "<p>Responsibilities include building backend services for software processing systems across multiple domains.</p>\n"
        "<p>Qualifications include 5+ years experience in Java and Python microservices and distributed systems.</p>\n"
        "<p>Requirements include strong knowledge of SQL databases and async performance tuning.</p>"
    )

    mock_extractor = AsyncMock()
    mock_extractor.fetch_and_enrich.return_value = DetailResult.empty(error_code="description_missing")
    norm_svc = NormalizationService(session_factory=test_session_factory, detail_extractor=mock_extractor)

    async with test_session_factory() as session:
        board = Board(board_id="board-noloc", name="NoLocCorp", family="ashby", status="active")
        p_run = PipelineRun(pipeline_id="p-noloc", trigger="manual", status="running")
        b_run = BoardRun(board_run_id="br-noloc", pipeline_id="p-noloc", board_id="board-noloc", stage="running", outcome="in_progress")
        session.add_all([board, p_run, b_run])
        await session.commit()

    candidate = ExtractedCandidate(
        title="Remote Systems Architect",
        company="NoLocCorp",
        location=None,
        raw_url="https://jobs.ashbyhq.com/noloc/101",
        fingerprint="fp_noloc_101",
        extra_payload={"description": valid_test_description}
    )

    res = await norm_svc.ingest_candidates("board-noloc", "br-noloc", [candidate], family="ashby")
    assert res.created_count == 1

    async with test_session_factory() as session:
        db_res = await session.execute(select(CandidateJob).where(CandidateJob.board_id == "board-noloc"))
        job = db_res.scalar_one()
        assert job.location is None, f"Expected location to be preserved as None, got '{job.location}'"
        assert job.india_eligible is True
        assert job.india_exclusion_reason is None

        outbox_res = await session.execute(select(HandoffOutbox).where(HandoffOutbox.candidate_id == job.candidate_id))
        outbox_entry = outbox_res.scalar_one_or_none()
        assert outbox_entry is not None, "Candidate with missing location must have handoff outbox row queued"
        assert outbox_entry.state == "queued"