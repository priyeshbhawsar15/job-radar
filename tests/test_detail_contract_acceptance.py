import json
from pathlib import Path

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from job_radar.db.models.board import Board
from job_radar.db.models.candidate import CandidateJob
from job_radar.services.detail_contracts import DetailRequest
from job_radar.services.workday_detail import fetch_workday_detail

FIXTURES = Path(__file__).parent / "fixtures" / "descriptions"


@pytest.mark.asyncio
async def test_workday_jiostar_detail_persists_clean_description(db_session: AsyncSession):
    """Isolated persistence test: fetch a Workday CXS detail payload and
    persist the enriched fields onto an in-memory CandidateJob row, using
    only the test session's sqlite:///:memory: database (never canonical)."""
    fixture = json.loads((FIXTURES / "workday_jiostar_cxs.json").read_text())

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=fixture)

    transport = httpx.MockTransport(handler)
    public_url = (
        "https://jiostar.wd102.myworkdayjobs.com/en-US/JioStar/job/Bengaluru/"
        "Software-Development-Engineer-II--Web----VX_JR10213"
    )

    async with httpx.AsyncClient(transport=transport) as client:
        req = DetailRequest(
            family="workday",
            public_url=public_url,
            board_name="JioStar",
            title="Software Development Engineer II - Web",
            provider_config={},
        )
        result = await fetch_workday_detail(req, client)

    assert result.error_code is None

    board = Board(name="JioStar", family="workday", status="enabled")
    db_session.add(board)
    await db_session.flush()

    candidate = CandidateJob(
        board_id=board.board_id,
        identity_key="jiostar|VX_JR10213",
        canonical_url_hash="testhash-jiostar-jr10213",
        title=result.title or "Software Development Engineer II - Web",
        company="JioStar",
        location=result.location,
        public_apply_url=public_url,
        description=result.description,
        detail_enrichment_status="enriched",
    )
    db_session.add(candidate)
    await db_session.commit()

    persisted = await db_session.get(CandidateJob, candidate.candidate_id)
    assert persisted is not None
    assert persisted.detail_enrichment_status == "enriched"
    assert persisted.location == "Bengaluru, Karnataka, India"
    assert persisted.title == "Software Development Engineer II - Web"
    assert "WORKDAY_JIOSTAR_FULL_DESCRIPTION_TOKEN" in persisted.description
    assert "<p>" not in persisted.description
    assert "<li>" not in persisted.description
    assert "• Design and build responsive web applications" in persisted.description
