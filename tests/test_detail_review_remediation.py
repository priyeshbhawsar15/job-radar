"""Recorded-body regressions for the independent review's consumer/identity gaps."""

from dataclasses import replace
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from job_radar.api.v1 import jobs as jobs_api
from job_radar.db.models.board import Board
from job_radar.db.models.candidate import CandidateJob
from job_radar.db.models.handoff import HandoffAttempt, HandoffOutbox
from job_radar.services.detail_contracts import DetailRequest, DetailResult
from job_radar.services.detail_extractor import clean_html_to_text, description_is_valid
from job_radar.services.handoff import HandoffProcessor
from job_radar.services.mattel_detail import parse_mattel_detail
from job_radar.services.settings_store import AppSettingsModel
from job_radar.services.site_detail import parse_novartis_detail

FIXTURES = Path(__file__).parent / "fixtures" / "detail_failure_20261011"
MATTEL_REQUEST = DetailRequest(
    "custom", "https://jobs.mattel.com/en/job/hyderabad/sr-electronic-engineer/2015/90860268592",
    "Mattel", "Sr Electronic Engineer Hyderabad, Telangana 10/08/2026", {},
)


def mattel_result():
    result = parse_mattel_detail((FIXTURES / "mattel_1.html").read_text(), MATTEL_REQUEST)
    assert result.error_code == "location_conflict"
    assert description_is_valid(result.description)
    return result


def databricks_body():
    data = json.loads((FIXTURES / "databricks.json").read_text())
    return data["title"], clean_html_to_text(data["content"])


async def make_candidate(db, *, company, title, url, description=None, error=None):
    board = Board(name=company, family="custom", status="reviewed")
    db.add(board)
    await db.flush()
    job = CandidateJob(
        board_id=board.board_id, identity_key=f"review:{company}", canonical_url_hash=f"review:{company}",
        company=company, title=title, public_apply_url=url, location="Hyderabad, Telangana, India",
        description=description, detail_enrichment_status="failed" if error else "succeeded",
        detail_enrichment_error_code=error,
    )
    db.add(job)
    await db.commit()
    return job


@pytest.mark.asyncio
@pytest.mark.parametrize("error", ["location_conflict", "identity_mismatch", "future_pool"])
async def test_retry_does_not_store_content_from_typed_failure(client, db_session, error):
    job = await make_candidate(
        db_session, company="Mattel", title=MATTEL_REQUEST.title,
        url=MATTEL_REQUEST.public_url, error=error,
    )
    job.location_provider_evidence = '{"provider_family":"custom","countries":["India"]}'
    await db_session.commit()
    result = replace(mattel_result(), error_code=error)
    with patch.object(jobs_api.detail_extractor, "fetch_and_enrich", new=AsyncMock(return_value=result)):
        response = await client.post(f"/api/v1/jobs/{job.candidate_id}/retry-enrichment")
    assert response.status_code == 200
    await db_session.refresh(job)
    assert job.detail_enrichment_status == "failed"
    assert job.detail_enrichment_error_code == error
    assert job.description is None
    assert job.location == "Hyderabad, Telangana, India"
    assert job.detail_enrichment_attempts == 1
    evidence = json.loads(job.location_provider_evidence)
    assert evidence["countries"] == ["India"]
    if error == "location_conflict":
        assert evidence["detail_location_conflict"] == {
            "listing": "Hyderabad, Telangana, India", "body": "Belagavi, India (Aequs Facility)",
        }


@pytest.mark.asyncio
async def test_retry_labels_present_but_invalid_native_content(client, db_session):
    job = await make_candidate(db_session, company="Levi Strauss", title="Manager", url="https://example.com/jobs/review")
    result = DetailResult(description=(FIXTURES / "levi_strauss_description_missing.clean.txt").read_text())
    with patch.object(jobs_api.detail_extractor, "fetch_and_enrich", new=AsyncMock(return_value=result)):
        response = await client.post(f"/api/v1/jobs/{job.candidate_id}/retry-enrichment")
    assert response.status_code == 200
    await db_session.refresh(job)
    assert job.detail_enrichment_error_code == "description_invalid"
    assert job.description is None


@pytest.mark.asyncio
async def test_databricks_retry_accepts_scoped_real_body(client, db_session):
    title, body = databricks_body()
    assert not description_is_valid(body, title=title)
    assert description_is_valid(body, title=title, board_name="Databricks")
    job = await make_candidate(db_session, company="Databricks", title=title, url="https://databricks.com/company/careers/open-positions/job?gh_jid=8805655002")
    with patch.object(jobs_api.detail_extractor, "fetch_and_enrich", new=AsyncMock(return_value=DetailResult(description=body))):
        response = await client.post(f"/api/v1/jobs/{job.candidate_id}/retry-enrichment")
    assert response.status_code == 200
    await db_session.refresh(job)
    assert job.detail_enrichment_status == "succeeded"
    assert job.detail_enrichment_error_code is None
    assert job.description == body


@pytest.mark.asyncio
@pytest.mark.parametrize("status,error,content,valid", [
    ("succeeded", None, "full", True),
    ("failed", "identity_mismatch", "empty", False),
    ("succeeded", "location_conflict", "full", False),
    ("pending", None, "full", False),
    ("succeeded", None, "empty", False),
    ("succeeded", None, "thin", False),
])
async def test_handoff_preserves_scoped_content_or_holds_failure(db_session, status, error, content, valid):
    title, body = databricks_body()
    job = await make_candidate(
        db_session, company="Databricks", title=title, url="https://databricks.com/company/careers/open-positions/job?gh_jid=8805655002",
        description=body if content == "full" else (
            (FIXTURES / "levi_strauss_description_missing.clean.txt").read_text() if content == "thin" else None
        ), error=error,
    )
    job.detail_enrichment_status = status
    await db_session.commit()
    factory = async_sessionmaker(db_session.bind, expire_on_commit=False)
    outbound = AsyncMock()
    client = type("RecordingClient", (), {"push_candidate": outbound})()
    processor = HandoffProcessor(session_factory=factory, jobops_client=client)
    record = await processor.enqueue_candidate_handoff(job.candidate_id)
    assert record is not None
    with patch("job_radar.services.handoff.load_settings", return_value=AppSettingsModel(handoff_enabled=True)):
        count = await processor.process_pending_outbox(loop_until_empty=False)
    async with factory() as session:
        stored = await session.get(HandoffOutbox, record.outbox_id)
        attempts = (await session.execute(select(HandoffAttempt))).scalars().all()
        assert len(attempts) == 1
        if valid:
            assert count == 1 and stored.state == "accepted"
            assert outbound.call_args.args[0]["job"]["jobDescription"] == body
        else:
            assert count == 0 and stored.state == "held"
            assert attempts[0].error_message == (error or "description_invalid")
            outbound.assert_not_called()


@pytest.mark.parametrize("index,number", [(1, "10087247"), (2, "10088115")])
def test_novartis_scoped_requisition_and_location(index, number):
    html = (FIXTURES / f"novartis_{index}.html").read_text()
    url = f"https://www.novartis.com/in-en/careers/career-search/job/details/req-{number}-captured-role"
    result = parse_novartis_detail(html, url)
    assert result.error_code is None
    assert result.location == "Hyderabad (Office), India"
    assert "About the Role" in result.description
    assert "Key Responsibilities" in result.description
    wrong = url.replace(number, "99999999")
    assert parse_novartis_detail(html + "<footer>REQ-99999999</footer>", wrong).error_code == "identity_mismatch"
    assert parse_novartis_detail(html + "<!-- REQ-99999999 -->", wrong).error_code == "identity_mismatch"
    assert parse_novartis_detail(html.replace('node--type-jobs', 'not-a-job'), url).error_code == "identity_mismatch"
    assert parse_novartis_detail(html + html, url).error_code == "identity_mismatch"


def test_novartis_rejects_article_title_conflict():
    html = (FIXTURES / "novartis_2.html").read_text()
    original = "Director, Technology &amp; Engineering for Software and Workflows"
    modified = html.replace(original, "Unrelated role", 1)
    url = "https://www.novartis.com/in-en/careers/career-search/job/details/req-10088115-captured-role"
    assert parse_novartis_detail(modified, url).error_code == "identity_mismatch"
