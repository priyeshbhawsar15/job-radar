"""Focused location-remediation contracts; all persistence uses disposable SQLite."""
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from job_radar.adapters.base import ExtractedCandidate, ProviderLocationEvidence
from job_radar.adapters.registry import adapter_registry
from job_radar.db.base import Base
from job_radar.db.models.board import Board
from job_radar.db.models.candidate import CandidateJob
from job_radar.db.models.handoff import HandoffOutbox
from job_radar.db.models.run import BoardRun, PipelineRun
from job_radar.services.engine import PipelineExecutionEngine
from job_radar.services.handoff import HandoffProcessor, JobOpsClient
from job_radar.services.location import LocationDecision, evaluate_location
from job_radar.services.normalization import NormalizationService


@pytest_asyncio.fixture
async def session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    yield factory
    await engine.dispose()


def test_greenhouse_structured_location_evidence_shapes():
    payload = json.dumps({"jobs": [{
        "id": 17, "title": "Engineer", "absolute_url": "https://job-boards.greenhouse.io/acme/jobs/17",
        "location": {"name": "Remote"},
        "offices": [{"name": "Toronto", "location": {"name": "Ontario", "country": "Canada"}}],
        "metadata": [{"name": "Country", "value": ["Canada", "United States"]}],
    }]})
    candidate = adapter_registry.get("greenhouse").parse_raw_payload(payload, "Acme", "https://job-boards.greenhouse.io/acme")[0]
    assert candidate.location == "Remote"
    evidence = candidate.location_provider_evidence
    assert evidence.countries == ["Canada", "United States", "Canada"]
    assert "Toronto" in evidence.display_locations and "Ontario" in evidence.display_locations
    assert evaluate_location(candidate.location, provider_evidence=evidence).decision == LocationDecision.NON_INDIA


def test_ashby_postal_and_nested_secondary_location_evidence():
    payload = json.dumps({"jobs": [{
        "id": "a-1", "title": "Engineer", "jobUrl": "https://jobs.ashbyhq.com/acme/a-1", "location": "Remote",
        "address": {"postalAddress": {"addressCountry": "US", "addressRegion": "California"}},
        "secondaryLocations": [{"name": "Bengaluru", "address": {"postalAddress": {"addressCountry": "India", "addressRegion": "Karnataka"}}}],
    }]})
    candidate = adapter_registry.get("ashby").parse_raw_payload(payload, "Acme", "https://jobs.ashbyhq.com/acme")[0]
    evidence = candidate.location_provider_evidence
    assert evidence.countries == ["US", "India"]
    assert evidence.regions == ["California", "Karnataka"]
    assert evaluate_location(candidate.location, provider_evidence=evidence).decision == LocationDecision.CONFLICT


@pytest.mark.asyncio
async def test_godaddy_country_filter_is_preserved_at_endpoint_translation(monkeypatch):
    engine = PipelineExecutionEngine()
    payload = json.dumps({"jobs": [
        {"id": 1, "title": "India", "absolute_url": "https://job-boards.greenhouse.io/godaddy/jobs/1", "location": {"name": "Remote"}, "metadata": [{"name": "Country", "value": "India"}]},
        {"id": 2, "title": "Foreign", "absolute_url": "https://job-boards.greenhouse.io/godaddy/jobs/2", "location": {"name": "Remote"}, "metadata": [{"name": "Country", "value": "Canada"}]},
        {"id": 3, "title": "Unknown", "absolute_url": "https://job-boards.greenhouse.io/godaddy/jobs/3", "location": {"name": "Remote"}},
    ]})
    class Response:
        status_code = 200
        text = payload
    class Client:
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def get(self, *args, **kwargs): return Response()
    monkeypatch.setattr("job_radar.services.engine.httpx.AsyncClient", lambda **kwargs: Client())
    result = await engine.fetch_greenhouse_candidates("https://careers.godaddy.com/search-jobs?country_codes[]=IN", "GoDaddy")
    assert {candidate.title for candidate in result} == {"India", "Unknown"}
    india = next(candidate for candidate in result if candidate.title == "India")
    assert india.location_provider_evidence.source_scope == "IN"


def test_maximum_structured_evidence_uses_bounded_summary_without_corrupting_provider_json():
    evidence = ProviderLocationEvidence(
        provider_family="greenhouse",
        countries=[f"Canada-{index}" for index in range(12)],
        regions=[f"North America Region {index}" for index in range(12)],
        display_locations=[f"Toronto Office Location {index}" for index in range(12)],
    )
    # Make the country values recognizable by the central classifier while retaining
    # maximum count and long structured values in the persisted provider document.
    evidence.countries[0] = "Canada"
    result = evaluate_location("Remote", provider_evidence=evidence)
    persisted = json.dumps(evidence.model_dump(), separators=(",", ":"))

    assert result.decision == LocationDecision.NON_INDIA
    assert len(result.evidence) <= 255
    assert json.loads(persisted)["countries"] == evidence.countries


@pytest.mark.asyncio
async def test_normalization_round_trip_keeps_valid_bounded_evidence(session_factory):
    async with session_factory() as session:
        session.add_all([Board(board_id="b", name="Acme", family="greenhouse", status="active"), PipelineRun(pipeline_id="p", trigger="test", status="running"), BoardRun(board_run_id="r", pipeline_id="p", board_id="b", stage="x", outcome="x")])
        await session.commit()
    evidence = ProviderLocationEvidence(provider_family="greenhouse", countries=["Canada"] * 12, country_paths=["metadata.Country"] * 12, display_locations=["X" * 200] * 12)
    service = NormalizationService(session_factory=session_factory, detail_extractor=AsyncMock())
    await service.ingest_candidates("b", "r", [ExtractedCandidate(title="Engineer", company="Acme", location="Remote", raw_url="https://example.test/1", fingerprint="1", location_provider_evidence=evidence)])
    async with session_factory() as session:
        candidate = (await session.execute(select(CandidateJob))).scalar_one()
        persisted = json.loads(candidate.location_provider_evidence)
        decision = evaluate_location(candidate.location, provider_evidence=persisted)
        assert persisted["countries"] == ["Canada"] * 12
        assert decision.decision == LocationDecision.NON_INDIA
        assert len(decision.evidence) <= 255
        assert candidate.location_decision == LocationDecision.NON_INDIA
        assert candidate.india_eligible is False


@pytest.mark.asyncio
async def test_disposable_integrated_provider_regression_persists_decisions_and_never_dispatches(session_factory):
    providers = [
        ("GitLab", "greenhouse", "Toronto, Ontario", {"countries": ["Canada"]}),
        ("GoDaddy", "greenhouse", "Remote", {"countries": ["India"], "source_scope": "IN"}),
        ("Twilio", "greenhouse", "London, UK", {"countries": ["United Kingdom"]}),
        ("Camunda", "ashby", "Remote", {"countries": ["US"], "regions": ["California"]}),
        ("Postman", "greenhouse", "Bengaluru, India", {"countries": ["India"]}),
        ("Redis", "ashby", "Remote", {"countries": ["Canada"]}),
        ("Databricks", "greenhouse", "Seattle, Washington", {"countries": ["US"]}),
        ("Okta", "greenhouse", "Remote", {"countries": ["India", "Canada"]}),
        ("Coinbase", "greenhouse", "Bengaluru, India", {"countries": ["India"]}),
    ]
    async with session_factory() as session:
        for number, (name, family, _, _) in enumerate(providers):
            board_id = f"integration-{number}"
            session.add_all([Board(board_id=board_id, name=name, family=family, status="active"), BoardRun(board_run_id=f"run-{number}", pipeline_id="pipeline", board_id=board_id, stage="x", outcome="x")])
        session.add(PipelineRun(pipeline_id="pipeline", trigger="test", status="running"))
        await session.commit()
    service = NormalizationService(session_factory=session_factory, detail_extractor=AsyncMock())
    for number, (name, family, location, evidence) in enumerate(providers):
        extracted = ExtractedCandidate(title="Engineer", company=name, location=location, raw_url=f"https://example.test/{number}", fingerprint=f"provider-{number}", extra_payload={"description": "Responsibilities include designing reliable systems for customers across production environments.\nQualifications require Python, testing, and distributed systems experience.\nRequirements include clear communication, ownership, and engineering judgment."}, location_provider_evidence=ProviderLocationEvidence(provider_family=family, **evidence))
        await service.ingest_candidates(f"integration-{number}", f"run-{number}", [extracted], family=family)
    async with session_factory() as session:
        candidates = (await session.execute(select(CandidateJob))).scalars().all()
        assert len(candidates) == len(providers)
        by_company = {candidate.company: candidate for candidate in candidates}
        assert by_company["GoDaddy"].location_decision == LocationDecision.INDIA
        assert by_company["Okta"].location_decision == LocationDecision.CONFLICT
        assert by_company["GitLab"].location_decision == LocationDecision.NON_INDIA
        assert all(json.loads(candidate.location_provider_evidence) for candidate in candidates)
        queued = (await session.execute(select(HandoffOutbox))).scalars().all()
        assert {row.candidate_id for row in queued} == {by_company["GoDaddy"].candidate_id, by_company["Postman"].candidate_id, by_company["Okta"].candidate_id, by_company["Coinbase"].candidate_id}


class FailOnCallClient(JobOpsClient):
    def __init__(self): self.calls = 0
    async def push_candidate(self, payload):
        self.calls += 1
        raise AssertionError("Job Ops must not be called")


async def _add_candidate(session_factory, candidate_id, location, evidence=None):
    async with session_factory() as session:
        session.add(Board(board_id=f"b-{candidate_id}", name="Acme", family="generic", status="active"))
        session.add(CandidateJob(candidate_id=candidate_id, board_id=f"b-{candidate_id}", identity_key=candidate_id, canonical_url_hash=candidate_id, title="Engineer", company="Acme", location=location, public_apply_url=f"https://example.test/{candidate_id}", location_provider_evidence=json.dumps(evidence) if evidence else None))
        await session.commit()


@pytest.mark.asyncio
async def test_enqueue_and_stale_dispatch_are_blocked_without_http(session_factory):
    client = FailOnCallClient(); processor = HandoffProcessor(session_factory=session_factory, jobops_client=client)
    await _add_candidate(session_factory, "foreign", "London, UK")
    assert await processor.enqueue_candidate_handoff("foreign") is None
    async with session_factory() as session:
        session.add(HandoffOutbox(candidate_id="foreign", idempotency_key="foreign", state="queued", next_retry_at=datetime.now(timezone.utc)))
        await session.commit()
    with patch("job_radar.services.handoff.load_settings", return_value=type("S", (), {"handoff_enabled": True, "jobops_import_batch_size": 10})()):
        assert await processor.process_pending_outbox() == 0
    async with session_factory() as session:
        row = (await session.execute(select(HandoffOutbox))).scalar_one()
        assert row.state == "held"
    assert client.calls == 0


@pytest.mark.asyncio
async def test_reconciliation_dry_run_and_apply_only_quarantines_nonaccepted(session_factory):
    processor = HandoffProcessor(session_factory=session_factory, jobops_client=FailOnCallClient())
    await _add_candidate(session_factory, "queued", "Toronto, Ontario")
    await _add_candidate(session_factory, "accepted", "London, UK")
    async with session_factory() as session:
        session.add_all([HandoffOutbox(candidate_id="queued", idempotency_key="q", state="queued", next_retry_at=datetime.now(timezone.utc)), HandoffOutbox(candidate_id="accepted", idempotency_key="a", state="accepted", next_retry_at=None)])
        await session.commit()
    report = await processor.reconcile_stale_outbox()
    assert {item["proposed_action"] for item in report} == {"quarantine", "report_accepted_for_approval"}
    await processor.reconcile_stale_outbox(apply=True)
    async with session_factory() as session:
        states = {row.candidate_id: row.state for row in (await session.execute(select(HandoffOutbox))).scalars()}
        assert states == {"queued": "held", "accepted": "accepted"}
