import json
from pathlib import Path

import httpx
import pytest

from job_radar.services.detail_contracts import (
    DetailRequest,
    ERR_INVALID_DETAIL_URL,
    ERR_HTTP_STATUS,
    ERR_DESCRIPTION_MISSING,
    ERR_DESCRIPTION_INVALID,
)
from job_radar.services.workday_detail import (
    parse_workday_cxs_url,
    build_cxs_detail_url,
    clean_workday_html,
    validate_detail_content,
    fetch_workday_detail,
)

FIXTURES = Path(__file__).parent / "fixtures" / "descriptions"


def test_parse_workday_cxs_url_jiostar():
    url = "https://jiostar.wd102.myworkdayjobs.com/en-US/JioStar/job/Bengaluru/Software-Development-Engineer-II--Web----VX_JR10213"
    tenant, site, path = parse_workday_cxs_url(url)
    assert tenant == "jiostar"
    assert site == "JioStar"
    assert path == "Bengaluru/Software-Development-Engineer-II--Web----VX_JR10213"


@pytest.mark.parametrize(
    "url,expected",
    [
        (
            "https://adobe.wd5.myworkdayjobs.com/en-US/external_experienced/job/San-Jose/Senior-Engineer_R12345",
            ("adobe", "external_experienced", "San-Jose/Senior-Engineer_R12345"),
        ),
        (
            "https://cisco.wd5.myworkdayjobs.com/en-US/Cisco_Careers/job/Bangalore/Software-Engineer_R99999-1",
            ("cisco", "Cisco_Careers", "Bangalore/Software-Engineer_R99999-1"),
        ),
        (
            "https://onetp.wd1.myworkdayjobs.com/en-US/Teleperformance/job/Remote/Analyst_R1",
            ("onetp", "Teleperformance", "Remote/Analyst_R1"),
        ),
    ],
)
def test_parse_workday_cxs_url_various_tenants(url, expected):
    assert parse_workday_cxs_url(url) == expected


def test_parse_workday_cxs_url_rejects_non_workday_and_listing_urls():
    assert parse_workday_cxs_url("https://example.com/job/123") is None
    assert parse_workday_cxs_url("https://jiostar.wd102.myworkdayjobs.com/en-US/JioStar") is None
    assert parse_workday_cxs_url("") is None
    assert parse_workday_cxs_url(None) is None


def test_build_cxs_detail_url():
    url = "https://jiostar.wd102.myworkdayjobs.com/en-US/JioStar/job/Bengaluru/Software-Development-Engineer-II--Web----VX_JR10213"
    cxs_url = build_cxs_detail_url(url)
    assert cxs_url == (
        "https://jiostar.wd102.myworkdayjobs.com/wday/cxs/jiostar/JioStar/job/"
        "Bengaluru/Software-Development-Engineer-II--Web----VX_JR10213"
    )


def test_build_cxs_detail_url_invalid_returns_none():
    assert build_cxs_detail_url("https://example.com/careers") is None


def test_clean_workday_html_preserves_paragraphs_and_bullets():
    raw = (
        "<p>WORKDAY_JIOSTAR_FULL_DESCRIPTION_TOKEN</p>"
        "<p>Intro paragraph about the role.</p>"
        "<p><b>Responsibilities</b></p>"
        "<ul><li>Build things.</li><li>Ship things.</li></ul>"
    )
    cleaned = clean_workday_html(raw)
    assert "WORKDAY_JIOSTAR_FULL_DESCRIPTION_TOKEN" in cleaned
    assert "<p>" not in cleaned and "<li>" not in cleaned and "<b>" not in cleaned
    assert "Intro paragraph about the roleResponsibilities" not in cleaned  # not smashed together
    assert "• Build things." in cleaned
    assert "• Ship things." in cleaned
    # Paragraph boundary preserved (blank line between paragraphs)
    assert "\n\n" in cleaned


def test_clean_workday_html_br_converts_to_line_boundary():
    raw = "<p>Line one.<br>Line two.</p>"
    cleaned = clean_workday_html(raw)
    assert "Line one." in cleaned
    assert "Line two." in cleaned
    assert "Line one.Line two." not in cleaned


def test_clean_workday_html_empty_input():
    assert clean_workday_html("") == ""
    assert clean_workday_html(None) == ""


def test_validate_detail_content_accepts_complete_description():
    fixture = json.loads((FIXTURES / "workday_jiostar_cxs.json").read_text())
    good = clean_workday_html(fixture["jobPostingInfo"]["jobDescription"])
    assert validate_detail_content(good) is None


def test_validate_detail_content_rejects_missing_or_empty():
    assert validate_detail_content(None) == ERR_DESCRIPTION_MISSING
    assert validate_detail_content("") == ERR_DESCRIPTION_MISSING
    assert validate_detail_content("   ") == ERR_DESCRIPTION_MISSING
    assert validate_detail_content("too short") == ERR_DESCRIPTION_INVALID


@pytest.mark.asyncio
async def test_fetch_workday_detail_http_mock_success():
    fixture = json.loads((FIXTURES / "workday_jiostar_cxs.json").read_text())

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "jiostar.wd102.myworkdayjobs.com"
        assert str(request.url.path) == (
            "/wday/cxs/jiostar/JioStar/job/Bengaluru/"
            "Software-Development-Engineer-II--Web----VX_JR10213"
        )
        return httpx.Response(200, json=fixture)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        req = DetailRequest(
            family="workday",
            public_url=(
                "https://jiostar.wd102.myworkdayjobs.com/en-US/JioStar/job/Bengaluru/"
                "Software-Development-Engineer-II--Web----VX_JR10213"
            ),
            board_name="JioStar",
            title="Software Development Engineer II - Web",
            provider_config={},
        )
        res = await fetch_workday_detail(req, client)

    assert res.error_code is None
    assert res.source == "workday_cxs_detail"
    assert "WORKDAY_JIOSTAR_FULL_DESCRIPTION_TOKEN" in res.description
    assert "<p>" not in res.description and "<li>" not in res.description
    assert "• Design and build responsive web applications" in res.description
    assert res.title == "Software Development Engineer II - Web"
    assert res.location == "Bengaluru, Karnataka, India"


@pytest.mark.asyncio
async def test_fetch_workday_detail_invalid_url():
    async with httpx.AsyncClient() as client:
        req = DetailRequest(
            family="workday",
            public_url="https://example.com/not-workday",
            board_name="Example",
            title="Dev",
            provider_config={},
        )
        res = await fetch_workday_detail(req, client)
    assert res.error_code == ERR_INVALID_DETAIL_URL


@pytest.mark.asyncio
async def test_fetch_workday_detail_missing_description_rejected():
    payload = {"jobPostingInfo": {"title": "Empty Role", "jobDescription": ""}}
    transport = httpx.MockTransport(lambda req: httpx.Response(200, json=payload))
    async with httpx.AsyncClient(transport=transport) as client:
        req = DetailRequest(
            family="workday",
            public_url=(
                "https://jiostar.wd102.myworkdayjobs.com/en-US/JioStar/job/Bengaluru/"
                "Empty-Role_JR1"
            ),
            board_name="JioStar",
            title="Empty Role",
            provider_config={},
        )
        res = await fetch_workday_detail(req, client)
    assert res.error_code == ERR_DESCRIPTION_MISSING
    assert res.description is None


@pytest.mark.asyncio
async def test_fetch_workday_detail_http_error_status():
    transport = httpx.MockTransport(lambda req: httpx.Response(404, text="not found"))
    async with httpx.AsyncClient(transport=transport) as client:
        req = DetailRequest(
            family="workday",
            public_url=(
                "https://jiostar.wd102.myworkdayjobs.com/en-US/JioStar/job/Bengaluru/"
                "Missing_JR2"
            ),
            board_name="JioStar",
            title="Missing",
            provider_config={},
        )
        res = await fetch_workday_detail(req, client)
    assert res.error_code == ERR_HTTP_STATUS
