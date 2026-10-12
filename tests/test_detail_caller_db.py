"""Isolated engine -> enrichment -> SQLite readback with captured public bodies."""

import json
from pathlib import Path

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from job_radar.adapters.base import ExtractedCandidate
from job_radar.db.models.board import Board, BoardRevision
from job_radar.db.models.candidate import CandidateJob
from job_radar.db.models.handoff import HandoffAttempt
from job_radar.services import engine as engine_module
from job_radar.services.detail_extractor import DetailExtractor
from job_radar.services.normalization import NormalizationService

FIXTURES = Path(__file__).parent / "fixtures" / "detail_failure_20261011"


class NoBrowser:
    async def fetch_board_html(self, target_url, *_args, **_kwargs):
        fixture = "apple_1.html" if "apple.com" in target_url else "mattel_1.html"
        return (FIXTURES / fixture).read_text()


class RecordedAdapter:
    def parse_raw_payload(self, payload, board_name, target_url, selector_config=None):
        return [RECORDED_CANDIDATES[board_name]]


RECORDED_CANDIDATES = {
    "Apple": ExtractedCandidate(
        title="IN-Technical Specialist", company="Apple", location="India",
        raw_url="https://jobs.apple.com/en-in/details/200314122/in-technical-specialist?team=APPST",
        fingerprint="apple-200314122", extra_payload={},
    ),
    "Twilio": ExtractedCandidate(
        title="Senior Solutions Engineer", company="Twilio", location="Remote - US",
        raw_url="https://job-boards.greenhouse.io/twilio/jobs/8249194",
        fingerprint="twilio-8249194", extra_payload={},
    ),
    "Mattel": ExtractedCandidate(
        title="Sr Electronic Engineer Hyderabad, Telangana 10/08/2026", company="Mattel", location="Hyderabad, Telangana, India",
        raw_url="https://jobs.mattel.com/en/job/hyderabad/sr-electronic-engineer/2015/90860268592",
        fingerprint="mattel-90860268592", extra_payload={},
    ),
}


@pytest.mark.asyncio
async def test_engine_terminal_board_outcomes_and_persisted_typed_errors(db_session: AsyncSession, monkeypatch):
    assert engine_module.__file__.startswith("/home/priyesh/projects/job-radar-detail-fixes-20261011/src/")
    assert __import__("job_radar.services.detail_extractor", fromlist=["__file__"]).__file__.startswith(
        "/home/priyesh/projects/job-radar-detail-fixes-20261011/src/"
    )
    session_factory = async_sessionmaker(db_session.bind, expire_on_commit=False)
    fixture_payload = json.loads((FIXTURES / "twilio.json").read_text())
    attempts = []

    def handler(request):
        attempts.append((request.method, request.url.host))
        if request.url.host == "jobs.apple.com":
            return httpx.Response(200, text=(FIXTURES / "apple_1.html").read_text())
        if request.url.host == "boards-api.greenhouse.io":
            return httpx.Response(200, json=fixture_payload)
        if request.url.host == "jobs.mattel.com":
            return httpx.Response(200, text=(FIXTURES / "mattel_1.html").read_text())
        raise AssertionError("unexpected outbound request")

    class FixtureExtractor:
        async def fetch_and_enrich(self, *args, **kwargs):
            async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
                return await DetailExtractor(NoBrowser()).fetch_and_enrich(*args, client=client, **kwargs)

    norm = NormalizationService(session_factory=session_factory, detail_extractor=FixtureExtractor())
    monkeypatch.setattr(engine_module, "normalization_service", norm)
    monkeypatch.setattr(engine_module.adapter_registry, "get", lambda family: RecordedAdapter())
    engine = engine_module.PipelineExecutionEngine(session_factory=session_factory)
    engine.browser_client = NoBrowser()

    async def greenhouse_listing(**_kwargs):
        return [RECORDED_CANDIDATES["Twilio"]]

    monkeypatch.setattr(engine, "fetch_greenhouse_candidates", greenhouse_listing)
    for board_name, family in [("Apple", "apple_jobs"), ("Twilio", "greenhouse"), ("Mattel", "custom")]:
        board = Board(board_id=f"isolated-{board_name.lower()}", name=board_name, family=family, status="reviewed")
        db_session.add(board)
        await db_session.flush()
        revision = BoardRevision(board_id=board.board_id, revision_number=1, status="reviewed", config_json={"target_url": RECORDED_CANDIDATES[board_name].raw_url})
        db_session.add(revision)
        await db_session.flush()
        board.current_revision_id = revision.revision_id
    await db_session.commit()

    outcomes = {}
    for board_name in ("Apple", "Twilio", "Mattel"):
        result = await engine.execute_board_run(f"isolated-{board_name.lower()}")
        outcomes[board_name] = result.outcome
    assert outcomes == {"Apple": "success", "Twilio": "partial", "Mattel": "partial"}

    async with session_factory() as session:
        jobs = {job.company: job for job in (await session.execute(select(CandidateJob))).scalars()}
        assert jobs["Apple"].detail_enrichment_status == "succeeded"
        assert jobs["Apple"].description and "Minimum Qualifications" in jobs["Apple"].description
        assert jobs["Apple"].detail_enrichment_error_code is None
        assert jobs["Twilio"].detail_enrichment_error_code == "description_invalid"
        assert jobs["Twilio"].description is None
        assert jobs["Mattel"].detail_enrichment_error_code == "location_conflict"
        assert jobs["Mattel"].description is None
        evidence = json.loads(jobs["Mattel"].location_provider_evidence)
        assert evidence["detail_location_conflict"] == {"listing": "Hyderabad, Telangana, India", "body": "Belagavi, India (Aequs Facility)"}
        assert (await session.execute(select(HandoffAttempt))).scalars().first() is None
    assert all(method == "GET" and host in {"jobs.apple.com", "boards-api.greenhouse.io", "jobs.mattel.com"} for method, host in attempts)
