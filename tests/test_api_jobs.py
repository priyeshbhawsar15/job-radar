from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from job_radar.db.models.board import Board
from job_radar.db.models.candidate import CandidateJob
from job_radar.services.detail_contracts import DetailResult


async def _make_board(db_session: AsyncSession, family: str = "generic") -> Board:
    board = Board(name="Acme", family=family, status="enabled")
    db_session.add(board)
    await db_session.commit()
    return board


async def _make_candidate(db_session: AsyncSession, board: Board, **overrides) -> CandidateJob:
    defaults = dict(
        board_id=board.board_id,
        identity_key=f"acme:job:{overrides.get('candidate_id', 'x')}",
        canonical_url_hash="hash-1",
        title="Software Engineer",
        company="Acme",
        public_apply_url="https://acme.example.com/jobs/1",
        detail_enrichment_status="failed",
        detail_enrichment_error_code="description_missing",
    )
    defaults.update(overrides)
    candidate = CandidateJob(**defaults)
    db_session.add(candidate)
    await db_session.commit()
    return candidate


@pytest.mark.asyncio
async def test_retry_enrichment_endpoint_success(client: AsyncClient, db_session: AsyncSession):
    board = await _make_board(db_session)
    candidate = await _make_candidate(db_session, board)

    success_result = DetailResult(
        description=(
            "About the role\n\n"
            + "A" * 200
            + "\n\nResponsibilities\n\nRequirements and qualifications for this role."
        ),
        location="Remote",
        source="generic",
    )
    with patch(
        "job_radar.api.v1.jobs.detail_extractor.fetch_and_enrich",
        new=AsyncMock(return_value=success_result),
    ):
        resp = await client.post(f"/api/v1/jobs/{candidate.candidate_id}/retry-enrichment")

    assert resp.status_code == 200
    data = resp.json()
    assert data["candidate_id"] == candidate.candidate_id
    assert data["detail_enrichment_status"] == "succeeded"
    assert data["detail_enrichment_error_code"] is None
    assert data["description"] == success_result.description


@pytest.mark.asyncio
async def test_retry_enrichment_endpoint_failure(client: AsyncClient, db_session: AsyncSession):
    board = await _make_board(db_session)
    candidate = await _make_candidate(db_session, board)

    failure_result = DetailResult(error_code="http_status")
    with patch(
        "job_radar.api.v1.jobs.detail_extractor.fetch_and_enrich",
        new=AsyncMock(return_value=failure_result),
    ):
        resp = await client.post(f"/api/v1/jobs/{candidate.candidate_id}/retry-enrichment")

    assert resp.status_code == 200
    data = resp.json()
    assert data["detail_enrichment_status"] == "failed"
    assert data["detail_enrichment_error_code"] == "http_status"


@pytest.mark.asyncio
async def test_retry_enrichment_endpoint_not_found(client: AsyncClient, db_session: AsyncSession):
    resp = await client.post("/api/v1/jobs/does-not-exist/retry-enrichment")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_legacy_record_serialization_consistency(client: AsyncClient, db_session: AsyncSession):
    board = await _make_board(db_session)
    candidate = await _make_candidate(
        db_session,
        board,
        location="London, UK",
        india_eligible=None,
        india_exclusion_reason=None,
    )
    resp = await client.get("/api/v1/jobs")
    assert resp.status_code == 200
    jobs = resp.json()
    match = next((j for j in jobs if j["candidate_id"] == candidate.candidate_id), None)
    assert match is not None
    assert match["india_eligible"] is False
    assert match["india_exclusion_reason"] == "NON_INDIA_LOCATION: London, UK"