"""Focused tests for the evidence-based location decision system."""

import hashlib
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from job_radar.services.location import (
    evaluate_location,
    is_india_eligible,
    LocationDecision,
)
from job_radar.services.normalization import NormalizationService
from job_radar.services.handoff import HandoffProcessor, JobOpsClient
from job_radar.adapters.base import ExtractedCandidate
from job_radar.db.models.candidate import CandidateJob
from job_radar.db.models.handoff import HandoffOutbox
from job_radar.db.models.board import Board, BoardRevision
from job_radar.db.models.run import BoardRun, PipelineRun
from job_radar.api.v1.jobs import push_candidate_to_jobops
from job_radar.db.base import Base


@pytest_asyncio.fixture
async def session_factory():
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)
    yield factory
    await test_engine.dispose()


def test_bengaluru_ka_decision():
    res = evaluate_location("Bengaluru, KA")
    assert res.decision == LocationDecision.INDIA
    assert res.eligible is True
    assert "Bengaluru" in res.evidence or "KA" in res.evidence
    assert res.confidence == "HIGH"


def test_2_locations_no_scope_decision():
    res = evaluate_location("2 Locations")
    assert res.decision == LocationDecision.UNKNOWN
    assert res.eligible is True
    assert res.confidence == "LOW"


def test_2_locations_verified_in_scope_decision():
    res = evaluate_location(
        "2 Locations",
        source_scope="IN",
        source_evidence="workday_location_country_filter"
    )
    assert res.decision == LocationDecision.INDIA
    assert res.eligible is True
    assert "source_scope: IN" in res.evidence
    assert "workday_location_country_filter" in res.evidence


def test_london_uk_decision():
    res = evaluate_location("London, UK")
    assert res.decision == LocationDecision.NON_INDIA
    assert res.eligible is False
    assert res.reason is not None
    assert "NON_INDIA_LOCATION" in res.reason


def test_remote_in_europe_decision():
    # Ordinary preposition 'in' must never count as India
    res = evaluate_location("Remote in Europe")
    assert res.decision == LocationDecision.NON_INDIA
    assert res.eligible is False
    assert "Europe" in res.evidence
    assert "NON_INDIA_LOCATION" in res.reason


def test_india_london_credible_conflict():
    res = evaluate_location("Bengaluru, India and London, UK")
    assert res.decision == LocationDecision.CONFLICT
    assert res.eligible is True
    assert "location_conflict" in res.evidence


def test_in_scope_london_only_detail():
    res = evaluate_location(
        "London, UK",
        source_scope="IN",
        source_evidence="workday_location_country_filter"
    )
    assert res.decision == LocationDecision.CONFLICT
    assert res.eligible is True
    assert "source_scope: IN" in res.evidence
    assert "London" in res.evidence


def compute_url_hash_val(url: str) -> str:
    return hashlib.sha256(url.encode('utf-8')).hexdigest()


@pytest.mark.asyncio
async def test_normalization_persistence_for_each_decision(session_factory):
    async with session_factory() as session:
        pr = PipelineRun(pipeline_id="pipe-1", trigger="manual", status="running", total_boards=1)
        session.add(pr)
        b = Board(board_id="board-test-pers", name="Test Board", family="generic", status="reviewed")
        session.add(b)
        br = BoardRun(board_run_id="run-test-pers", pipeline_id="pipe-1", board_id="board-test-pers", stage="running", outcome="in_progress")
        session.add(br)
        await session.commit()

    norm_svc = NormalizationService(session_factory=session_factory, detail_extractor=MagicMock())

    cands = [
        ExtractedCandidate(title="Job 1", company="Co", location="Bengaluru, KA", department="Eng", employment_type="Full-time", raw_url="https://example.com/1", fingerprint="fp1", extra_payload={"description": "Valid detail description for role 1"}),
        ExtractedCandidate(title="Job 2", company="Co", location="2 Locations", department="Eng", employment_type="Full-time", raw_url="https://example.com/2", fingerprint="fp2", extra_payload={"description": "Valid detail description for role 2"}),
        ExtractedCandidate(title="Job 3", company="Co", location="London, UK", department="Eng", employment_type="Full-time", raw_url="https://example.com/3", fingerprint="fp3", extra_payload={"description": "Valid detail description for role 3"}),
        ExtractedCandidate(title="Job 4", company="Co", location="Bengaluru, India and London, UK", department="Eng", employment_type="Full-time", raw_url="https://example.com/4", fingerprint="fp4", extra_payload={"description": "Valid detail description for role 4"}),
    ]

    with patch("job_radar.services.normalization.HandoffProcessor.enqueue_candidate_handoff", new_callable=AsyncMock):
        await norm_svc.ingest_candidates("board-test-pers", "run-test-pers", cands)

    async with session_factory() as session:
        j1 = (await session.execute(select(CandidateJob).where(CandidateJob.canonical_url_hash == compute_url_hash_val("https://example.com/1")))).scalar_one()
        assert j1.location_decision == LocationDecision.INDIA
        assert j1.india_eligible is True
        assert j1.india_exclusion_reason is None

        j2 = (await session.execute(select(CandidateJob).where(CandidateJob.canonical_url_hash == compute_url_hash_val("https://example.com/2")))).scalar_one()
        assert j2.location_decision == LocationDecision.UNKNOWN
        assert j2.india_eligible is True
        assert j2.india_exclusion_reason is None

        j3 = (await session.execute(select(CandidateJob).where(CandidateJob.canonical_url_hash == compute_url_hash_val("https://example.com/3")))).scalar_one()
        assert j3.location_decision == LocationDecision.NON_INDIA
        assert j3.india_eligible is False
        assert j3.india_exclusion_reason is not None

        j4 = (await session.execute(select(CandidateJob).where(CandidateJob.canonical_url_hash == compute_url_hash_val("https://example.com/4")))).scalar_one()
        assert j4.location_decision == LocationDecision.CONFLICT
        assert j4.india_eligible is True
        assert j4.india_exclusion_reason is None


@pytest.mark.asyncio
async def test_automatic_enqueue_allows_unknown_conflict_blocks_non_india(session_factory):
    processor = HandoffProcessor(session_factory=session_factory)

    async with session_factory() as session:
        b = Board(board_id="b-enq", name="B", family="g", status="reviewed")
        session.add(b)
        c_india = CandidateJob(candidate_id="c-india", board_id="b-enq", identity_key="ik1", canonical_url_hash="h1", title="T1", company="C", location="Bengaluru", public_apply_url="https://a.com/1", location_decision=LocationDecision.INDIA, india_eligible=True)
        c_unknown = CandidateJob(candidate_id="c-unknown", board_id="b-enq", identity_key="ik2", canonical_url_hash="h2", title="T2", company="C", location="2 Locations", public_apply_url="https://a.com/2", location_decision=LocationDecision.UNKNOWN, india_eligible=True)
        c_conflict = CandidateJob(candidate_id="c-conflict", board_id="b-enq", identity_key="ik3", canonical_url_hash="h3", title="T3", company="C", location="India / US", public_apply_url="https://a.com/3", location_decision=LocationDecision.CONFLICT, india_eligible=True)
        c_non_india = CandidateJob(candidate_id="c-non-india", board_id="b-enq", identity_key="ik4", canonical_url_hash="h4", title="T4", company="C", location="London, UK", public_apply_url="https://a.com/4", location_decision=LocationDecision.NON_INDIA, india_eligible=False, india_exclusion_reason="NON_INDIA_LOCATION: London, UK")
        session.add_all([c_india, c_unknown, c_conflict, c_non_india])
        await session.commit()

    # Test enqueueing each candidate
    out_india = await processor.enqueue_candidate_handoff("c-india")
    assert out_india is not None

    out_unknown = await processor.enqueue_candidate_handoff("c-unknown")
    assert out_unknown is not None

    out_conflict = await processor.enqueue_candidate_handoff("c-conflict")
    assert out_conflict is not None

    out_non_india = await processor.enqueue_candidate_handoff("c-non-india")
    assert out_non_india is None  # Blocked!

    # Test outbox processing with fail-on-call double (ensuring no real Job Ops call)
    class FailOnCallClient(JobOpsClient):
        def __init__(self):
            self.pushed_payloads = []
        async def push_candidate(self, payload):
            self.pushed_payloads.append(payload)
            return True

    fail_client = FailOnCallClient()
    processor.client = fail_client

    with patch("job_radar.services.handoff.load_settings") as mock_settings:
        mock_settings.return_value.handoff_enabled = True
        mock_settings.return_value.jobops_import_batch_size = 50
        processed = await processor.process_pending_outbox(loop_until_empty=False)
        assert processed == 3  # India, Unknown, Conflict
        assert len(fail_client.pushed_payloads) == 3


@pytest.mark.asyncio
async def test_manual_push_and_handoff_processor_same_policy(session_factory):
    async with session_factory() as session:
        b = Board(board_id="b-push", name="B", family="g", status="reviewed")
        session.add(b)
        c_unk = CandidateJob(candidate_id="c-push-unk", board_id="b-push", identity_key="ikp1", canonical_url_hash="hp1", title="T1", company="C", location="2 Locations", public_apply_url="https://a.com/p1", location_decision=LocationDecision.UNKNOWN, india_eligible=True, description="Valid detail description for push testing")
        c_ni = CandidateJob(candidate_id="c-push-ni", board_id="b-push", identity_key="ikp2", canonical_url_hash="hp2", title="T2", company="C", location="London, UK", public_apply_url="https://a.com/p2", location_decision=LocationDecision.NON_INDIA, india_eligible=False, india_exclusion_reason="NON_INDIA_LOCATION: London, UK", description="Valid detail description for push testing")
        session.add_all([c_unk, c_ni])
        await session.commit()

    with patch("job_radar.api.v1.jobs.handoff_processor.session_factory", session_factory), \
         patch("job_radar.api.v1.jobs.handoff_processor.client.push_candidate", new_callable=AsyncMock) as mock_push, \
         patch("job_radar.services.handoff.load_settings") as mock_settings:
        mock_settings.return_value.handoff_enabled = True
        mock_settings.return_value.jobops_import_batch_size = 50
        mock_push.return_value = True

        async with session_factory() as db:
            res_unk = await push_candidate_to_jobops("c-push-unk", db=db)
            assert res_unk.status == "imported"

            res_ni = await push_candidate_to_jobops("c-push-ni", db=db)
            assert res_ni.status == "excluded_non_india"


def test_join_us_remotely_decision():
    res = evaluate_location("Join us remotely")
    assert res.decision == LocationDecision.UNKNOWN
    assert res.eligible is True


def test_lowercase_in_vs_uppercase_in():
    res_lower = evaluate_location("in")
    assert res_lower.decision == LocationDecision.UNKNOWN
    assert res_lower.eligible is True

    res_upper = evaluate_location("IN")
    assert res_upper.decision == LocationDecision.INDIA
    assert res_upper.eligible is True


def test_multiword_foreign_cities():
    for loc in ["New York", "San Francisco, CA", "Tel Aviv", "San Jose", "Sao Paulo"]:
        res = evaluate_location(loc)
        assert res.decision == LocationDecision.NON_INDIA, f"Failed for location: {loc}"
        assert res.eligible is False


@pytest.mark.asyncio
async def test_legacy_candidate_handling(session_factory):
    processor = HandoffProcessor(session_factory=session_factory)

    async with session_factory() as session:
        b = Board(board_id="b-legacy", name="B Legacy", family="g", status="reviewed")
        session.add(b)
        # Legacy row: location_decision is None, stale india_eligible=False, location="2 Locations"
        c_legacy_allowed = CandidateJob(
            candidate_id="c-leg-allowed",
            board_id="b-legacy",
            identity_key="ik-leg-1",
            canonical_url_hash="hash-leg-1",
            title="T1",
            company="C",
            location="2 Locations",
            public_apply_url="https://a.com/leg1",
            location_decision=None,
            india_eligible=False,
            india_exclusion_reason="Stale reason",
            description="Valid detail description for legacy candidate",
        )
        # Legacy row: location_decision is None, stale india_eligible=True, location="London, UK"
        c_legacy_blocked = CandidateJob(
            candidate_id="c-leg-blocked",
            board_id="b-legacy",
            identity_key="ik-leg-2",
            canonical_url_hash="hash-leg-2",
            title="T2",
            company="C",
            location="London, UK",
            public_apply_url="https://a.com/leg2",
            location_decision=None,
            india_eligible=True,
            description="Valid detail description for legacy candidate",
        )
        session.add_all([c_legacy_allowed, c_legacy_blocked])
        await session.commit()

    # Automatic enqueue check (without real Job Ops calls)
    out_allowed = await processor.enqueue_candidate_handoff("c-leg-allowed")
    assert out_allowed is not None

    out_blocked = await processor.enqueue_candidate_handoff("c-leg-blocked")
    assert out_blocked is None

    # Manual gate check via push_candidate_to_jobops
    with patch("job_radar.api.v1.jobs.handoff_processor.session_factory", session_factory), \
         patch("job_radar.api.v1.jobs.handoff_processor.client.push_candidate", new_callable=AsyncMock) as mock_push, \
         patch("job_radar.services.handoff.load_settings") as mock_settings:
        mock_settings.return_value.handoff_enabled = True
        mock_settings.return_value.jobops_import_batch_size = 50
        mock_push.return_value = True

        async with session_factory() as db:
            res_allowed = await push_candidate_to_jobops("c-leg-allowed", db=db)
            assert res_allowed.status in ("imported", "queued")

            res_blocked = await push_candidate_to_jobops("c-leg-blocked", db=db)
            assert res_blocked.status == "excluded_non_india"


@pytest.mark.asyncio
async def test_reobservation_updates_raw_location_and_evidence(session_factory):
    async with session_factory() as session:
        pr = PipelineRun(pipeline_id="pipe-reobs", trigger="manual", status="running", total_boards=1)
        session.add(pr)
        b = Board(board_id="board-reobs", name="Reobs Board", family="generic", status="reviewed")
        session.add(b)
        br = BoardRun(board_run_id="run-reobs-1", pipeline_id="pipe-reobs", board_id="board-reobs", stage="running", outcome="in_progress")
        br2 = BoardRun(board_run_id="run-reobs-2", pipeline_id="pipe-reobs", board_id="board-reobs", stage="running", outcome="in_progress")
        session.add_all([br, br2])

        # Pre-existing candidate in DB with location "2 Locations"
        cand = CandidateJob(
            candidate_id="c-reobs-1",
            board_id="board-reobs",
            identity_key="reobs-fp-1",
            canonical_url_hash=compute_url_hash_val("https://example.com/reobs"),
            title="Engineer",
            company="Acme Corp",
            location="2 Locations",
            location_decision=LocationDecision.UNKNOWN,
            location_evidence="unresolved_location: 2 Locations",
            india_eligible=True,
            public_apply_url="https://example.com/reobs",
            description="Valid detail description for reobs candidate",
        )
        session.add(cand)
        await session.commit()

    norm_svc = NormalizationService(session_factory=session_factory, detail_extractor=MagicMock())

    # Re-observe candidate with updated location "London, UK"
    reobs_cand = ExtractedCandidate(
        title="Engineer",
        company="Acme Corp",
        location="London, UK",
        department="Eng",
        employment_type="Full-time",
        raw_url="https://example.com/reobs",
        fingerprint="reobs-fp-1",
        extra_payload={"description": "Valid detail description for reobs candidate"},
    )

    with patch("job_radar.services.normalization.HandoffProcessor.enqueue_candidate_handoff", new_callable=AsyncMock):
        await norm_svc.ingest_candidates("board-reobs", "run-reobs-1", [reobs_cand])

    async with session_factory() as session:
        j = (await session.execute(select(CandidateJob).where(CandidateJob.candidate_id == "c-reobs-1"))).scalar_one()
        assert j.location == "London, UK"
        assert j.location_decision == LocationDecision.NON_INDIA
        assert "London" in j.location_evidence or "UK" in j.location_evidence
        assert j.india_eligible is False

    # Re-observe candidate with blank location: should retain existing "London, UK" and classify it
    reobs_blank_cand = ExtractedCandidate(
        title="Engineer",
        company="Acme Corp",
        location="",
        department="Eng",
        employment_type="Full-time",
        raw_url="https://example.com/reobs",
        fingerprint="reobs-fp-1",
        extra_payload={"description": "Valid detail description for reobs candidate"},
    )

    with patch("job_radar.services.normalization.HandoffProcessor.enqueue_candidate_handoff", new_callable=AsyncMock):
        await norm_svc.ingest_candidates("board-reobs", "run-reobs-2", [reobs_blank_cand])

    async with session_factory() as session:
        j2 = (await session.execute(select(CandidateJob).where(CandidateJob.candidate_id == "c-reobs-1"))).scalar_one()
        assert j2.location == "London, UK"
        assert j2.location_decision == LocationDecision.NON_INDIA
        assert "London" in j2.location_evidence or "UK" in j2.location_evidence
        assert j2.india_eligible is False


@pytest.mark.asyncio
async def test_jll_multilocations_with_config_not_rejected(session_factory):
    async with session_factory() as session:
        pr = PipelineRun(pipeline_id="pipe-jll", trigger="manual", status="running", total_boards=1)
        session.add(pr)
        jll_board = Board(board_id="board-jll", name="JLL", family="workday", status="reviewed")
        session.add(jll_board)
        rev = BoardRevision(
            board_id="board-jll",
            revision_number=1,
            status="reviewed",
            config_json={
                "target_url": "https://jll.wd1.myworkdayjobs.com/en-US/jllcareers?locationCountry=c4f78be1a8f14da0ab49ce1162348a5e",
                "source_country_scope": "IN",
                "source_scope_evidence": "workday_location_country_filter"
            }
        )
        session.add(rev)
        await session.flush()
        jll_board.current_revision_id = rev.revision_id
        br = BoardRun(board_run_id="run-jll-01", pipeline_id="pipe-jll", board_id="board-jll", stage="running", outcome="in_progress")
        session.add(br)
        await session.commit()

    norm_svc = NormalizationService(session_factory=session_factory, detail_extractor=MagicMock())

    valid_desc = (
        "Position Responsibilities and Duties:\n"
        "- We are seeking an experienced candidate for this role to join our team.\n"
        "- Requirements include experience with engineering and operations.\n"
        "- Full time position with competitive compensation and benefits included."
    )

    jll_cands = [
        ExtractedCandidate(title="JLL Role 1", company="JLL", location="2 Locations", department="Real Estate", employment_type="Full-time", raw_url="https://jll.wd1.myworkdayjobs.com/job1", fingerprint="jll-fp-1", extra_payload={"description": valid_desc}),
        ExtractedCandidate(title="JLL Role 2", company="JLL", location="3 Locations", department="Real Estate", employment_type="Full-time", raw_url="https://jll.wd1.myworkdayjobs.com/job2", fingerprint="jll-fp-2", extra_payload={"description": valid_desc}),
    ]

    provider_cfg = {
        "source_country_scope": "IN",
        "source_scope_evidence": "workday_location_country_filter"
    }

    with patch("job_radar.services.normalization.HandoffProcessor.enqueue_candidate_handoff", new_callable=AsyncMock) as mock_enq:
        ingest_res = await norm_svc.ingest_candidates("board-jll", "run-jll-01", jll_cands, provider_config=provider_cfg)
        assert ingest_res.created_count == 2
        assert mock_enq.call_count == 2

    async with session_factory() as session:
        jobs = (await session.execute(select(CandidateJob).where(CandidateJob.board_id == "board-jll"))).scalars().all()
        assert len(jobs) == 2
        for j in jobs:
            assert j.location_decision == LocationDecision.INDIA
            assert j.india_eligible is True
            assert j.india_exclusion_reason is None
            assert "source_scope: IN" in j.location_evidence
            assert "workday_location_country_filter" in j.location_evidence
