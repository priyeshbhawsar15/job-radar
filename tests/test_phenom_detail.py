import json
from pathlib import Path
import pytest
import httpx

from job_radar.services.detail_contracts import (
    DetailRequest,
    DetailResult,
    ERR_INVALID_PROVIDER_CONFIG,
    ERR_INVALID_DETAIL_URL,
    ERR_BOUNDARY_VIOLATION,
    ERR_HTTP_STATUS,
    ERR_DESCRIPTION_MISSING,
)
from job_radar.services.phenom_detail import (
    extract_phenom_posting,
    extract_job_posting_json_ld,
    extract_location_from_json_ld,
    extract_phenom_bounded_dom_description,
    fetch_phenom_detail,
)

FIXTURES = Path(__file__).parent / "fixtures" / "descriptions"


def test_extract_phenom_posting_json_ld_success():
    philips_html = (FIXTURES / "philips_detail.html").read_text()
    res = extract_phenom_posting(philips_html, title="Software Systems Engineer")
    assert res.description is not None
    assert "PHILIPS_FULL_DESCRIPTION_TOKEN" in res.description
    assert res.source == "phenom_json_ld"
    assert res.location == "Bangalore, India"


def test_extract_phenom_posting_json_ld_location_variants():
    job_node = {
        "@type": "JobPosting",
        "jobLocation": [
            {
                "@type": "Place",
                "address": {
                    "addressLocality": "Bangalore",
                    "addressRegion": "Karnataka",
                    "addressCountry": "IN",
                },
            }
        ],
    }
    loc = extract_location_from_json_ld(job_node)
    assert loc == "Bangalore, Karnataka, India"


def test_extract_phenom_bounded_dom_fallback():
    dom_html = """
    <html>
    <body>
    <header>Nav link Privacy Policy Cookie Preferences</header>
    <div class="description-block">
        <p>VALID_BOUNDED_DOM_TOKEN</p>
        <p>RESPONSIBILITIES:</p>
        <ul><li>Build medical device UI.</li><li>Ensure test coverage.</li></ul>
        <p>QUALIFICATIONS:</p>
        <ul><li>5+ years experience.</li></ul>
    </div>
    <footer>Footer contact terms</footer>
    </body>
    </html>
    """
    res = extract_phenom_posting(dom_html, title="Dev")
    assert res.description is not None
    assert "VALID_BOUNDED_DOM_TOKEN" in res.description
    assert res.source == "phenom_description_dom"
    assert "Privacy Policy" not in res.description


def test_extract_phenom_posting_unbounded_html_rejected():
    unbounded_html = """
    <html>
    <body>
    <p>Some random body text that is not in a description container window.vanityurlenabled</p>
    </body>
    </html>
    """
    res = extract_phenom_posting(unbounded_html, title="Dev")
    assert res.description is None
    assert res.error_code == ERR_DESCRIPTION_MISSING


@pytest.mark.asyncio
async def test_fetch_phenom_detail_http_success():
    philips_fixture = (FIXTURES / "philips_detail.html").read_bytes()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "www.careers.philips.com"
        return httpx.Response(200, content=philips_fixture, headers={"Content-Type": "text/html"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        req = DetailRequest(
            family="phenom",
            public_url="https://www.careers.philips.com/in/en/job/581004/Senior-Software-Technologist-Rust",
            board_name="Philips",
            title="Senior Software Technologist",
            provider_config={
                "allowed_origins": ["www.careers.philips.com"],
            },
        )
        res = await fetch_phenom_detail(req, client)
        assert res.description is not None
        assert "PHILIPS_FULL_DESCRIPTION_TOKEN" in res.description
        assert res.source == "phenom_json_ld"
        assert res.error_code is None


@pytest.mark.asyncio
async def test_fetch_phenom_detail_boundary_violation():
    async with httpx.AsyncClient() as client:
        req = DetailRequest(
            family="phenom",
            public_url="https://unallowed.example.com/job/581004",
            board_name="Philips",
            title="Dev",
            provider_config={
                "allowed_origins": ["www.careers.philips.com"],
            },
        )
        res = await fetch_phenom_detail(req, client)
        assert res.error_code == ERR_BOUNDARY_VIOLATION
