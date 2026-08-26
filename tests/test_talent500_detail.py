import json
from pathlib import Path
import pytest
import httpx

from job_radar.services.detail_contracts import (
    DetailRequest,
    ERR_INVALID_DETAIL_URL,
    ERR_HTTP_STATUS,
    ERR_RECORD_NOT_FOUND,
    ERR_DESCRIPTION_MISSING,
    ERR_DESCRIPTION_INVALID,
)
from job_radar.services.talent500_detail import (
    validate_talent500_url,
    fetch_talent500_detail,
)

FIXTURES_DIR = Path("tests/fixtures/talent500")


def test_validate_talent500_url():
    valid_url_1 = "https://talent500.com/jobs/t-mobile/manager-software-engineering-hyderabad-T500-28653/"
    valid_url_2 = "https://talent500.com/jobs/best-buy-india/senior-product-manager-bengaluru-T500-28622"
    invalid_host = "https://example.com/jobs/t-mobile/manager-software-engineering-hyderabad-T500-28653/"
    invalid_path = "https://talent500.com/joblist/?company=TMUS"

    assert validate_talent500_url(valid_url_1) == "manager-software-engineering-hyderabad-T500-28653"
    assert validate_talent500_url(valid_url_2) == "senior-product-manager-bengaluru-T500-28622"
    assert validate_talent500_url(invalid_host) is None
    assert validate_talent500_url(invalid_path) is None


@pytest.mark.asyncio
async def test_fetch_talent500_detail_success():
    detail_data = json.loads((FIXTURES_DIR / "tmus_detail.json").read_text())
    slug = "manager-software-engineering-hyderabad-T500-28653"
    url = f"https://talent500.com/jobs/t-mobile/{slug}/"

    req = DetailRequest(
        family="talent500",
        public_url=url,
        board_name="TMUS",
        title="Manager, Software Engineering",
        provider_config={},
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert f"/api/jobs/{slug}/" in str(request.url)
        return httpx.Response(200, json=detail_data)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        res = await fetch_talent500_detail(req, client)

    assert res.error_code is None
    assert res.source == "talent500_api"
    assert res.title == "Manager, Software Engineering"
    assert res.location == "Hyderabad, India"
    assert res.employment_type == "Full-Time"
    assert res.description is not None
    assert len(res.description) > 200
    assert "Responsibilities" in res.description or "software engineering" in res.description.lower()


@pytest.mark.asyncio
async def test_fetch_talent500_detail_invalid_url():
    req = DetailRequest(
        family="talent500",
        public_url="https://invalid-domain.com/jobs/foo/bar",
        board_name="TMUS",
        title="Manager, Software Engineering",
        provider_config={},
    )
    async with httpx.AsyncClient() as client:
        res = await fetch_talent500_detail(req, client)

    assert res.error_code == ERR_INVALID_DETAIL_URL


@pytest.mark.asyncio
async def test_fetch_talent500_detail_not_found():
    req = DetailRequest(
        family="talent500",
        public_url="https://talent500.com/jobs/t-mobile/nonexistent-slug/",
        board_name="TMUS",
        title="Manager, Software Engineering",
        provider_config={},
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"detail": "Not found"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        res = await fetch_talent500_detail(req, client)

    assert res.error_code == ERR_RECORD_NOT_FOUND
