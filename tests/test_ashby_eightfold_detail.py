import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock

from job_radar.services.detail_contracts import DetailRequest, DetailResult
from job_radar.services.ashby_detail import parse_ashby_job_url, fetch_ashby_detail
from job_radar.services.eightfold_detail import parse_eightfold_job_url, fetch_eightfold_detail
from job_radar.services.detail_extractor import DetailExtractor, description_is_valid


def test_parse_ashby_job_url():
    url = "https://jobs.ashbyhq.com/supabase/68a397e7-8a1a-4566-ae41-e8c61dd6ed93"
    parsed = parse_ashby_job_url(url)
    assert parsed == ("supabase", "68a397e7-8a1a-4566-ae41-e8c61dd6ed93")

    url2 = "https://jobs.ashbyhq.com/camunda/313123ea-02e9-40c6-897e-dbffb2b230f1"
    parsed2 = parse_ashby_job_url(url2)
    assert parsed2 == ("camunda", "313123ea-02e9-40c6-897e-dbffb2b230f1")

    assert parse_ashby_job_url("https://example.com/invalid") is None


def test_parse_eightfold_job_url():
    url = "https://apply.careers.microsoft.com/careers/job/1970393557022260"
    parsed = parse_eightfold_job_url(url)
    assert parsed == ("apply.careers.microsoft.com", "1970393557022260", None)

    url2 = "https://hp.eightfold.ai/careers/job/43778054?domain=hp.com"
    parsed2 = parse_eightfold_job_url(url2)
    assert parsed2 == ("hp.eightfold.ai", "43778054", "hp.com")

    assert parse_eightfold_job_url("https://example.com/invalid") is None


@pytest.mark.parametrize("url", [
    "http://jobs.ashbyhq.com/acme/abc123",
    "https://jobs.ashbyhq.com.evil.test/acme/abc123",
    "https://evil-jobs.ashbyhq.com/acme/abc123",
    "https://user@jobs.ashbyhq.com/acme/abc123",
    "https://jobs.ashbyhq.com:443/acme/abc123",
    "https://jobs.ashbyhq.com/acme/abc123/extra",
    "https://jobs.ashbyhq.com/acme/abc123%2Fextra",
])
def test_ashby_rejects_hostile_urls(url):
    assert parse_ashby_job_url(url, {"ashby_org": "acme"}) is None


@pytest.mark.parametrize("url", [
    "http://hp.eightfold.ai/careers/job/123",
    "https://hp.eightfold.ai.evil.test/careers/job/123",
    "https://localhost/careers/job/123",
    "https://127.0.0.1/careers/job/123",
    "https://morganstanley.eightfold.ai/careers/job/123",
    "https://user@hp.eightfold.ai/careers/job/123",
    "https://hp.eightfold.ai:443/careers/job/123",
    "https://hp.eightfold.ai/careers/job/123/extra",
    "https://hp.eightfold.ai/careers/job/123%2Fextra",
])
def test_eightfold_rejects_hostile_urls(url):
    assert parse_eightfold_job_url(url) is None


def test_description_requires_role_duties():
    nav = ("Search jobs\nExplore careers\nAbout us\nBenefits and perks\n"
           "View responsibilities\nSee qualifications\nApply now\n") * 30
    pool = ("Join our talent pool for future opportunities. We have no current vacancies. "
            "About the role: share your profile and we will contact you later.\n") * 10
    browserstack = ("About BrowserStack\nWe build a platform for testing. Our company provides "
                    "tools to customers around the world.\nBenefits and perks\n"
                    "You will receive health coverage and flexible leave.\n") * 10
    spanish = ("Sobre el puesto\nDiseñar servicios y desarrollar soluciones para clientes.\n"
               "Coordinar con ingeniería para mejorar el rendimiento de la plataforma.\n") * 2
    for invalid in (nav, pool, browserstack):
        assert not description_is_valid(invalid)
    assert description_is_valid(spanish)


@pytest.mark.asyncio
@pytest.mark.parametrize("family,url", [
    ("ashby", "https://jobs.ashbyhq.com.evil.test/acme/abc123"),
    ("eightfold", "https://127.0.0.1/careers/job/123"),
])
async def test_dispatch_rejects_invalid_native_url_without_outbound(family, url):
    client = AsyncMock()
    browser = AsyncMock()
    result = await DetailExtractor(browser_client=browser).fetch_and_enrich(
        url, "Example", "Engineer", family=family, client=client,
    )
    assert result.error_code == "invalid_detail_url"
    client.get.assert_not_called()
    client.post.assert_not_called()
    browser.fetch_board_html.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("family,url", [
    ("ashby", "https://jobs.ashbyhq.com/acme/abc123"),
    ("eightfold", "https://hp.eightfold.ai/careers/job/123"),
])
async def test_native_redirect_cannot_escape_or_fallback(family, url):
    requests = []

    def handler(request):
        requests.append(str(request.url))
        return httpx.Response(302, headers={"Location": "http://127.0.0.1/private"})

    browser = AsyncMock()
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=True) as client:
        result = await DetailExtractor(browser_client=browser).fetch_and_enrich(
            url, "Example", "Engineer", family=family, client=client,
        )
    assert result.error_code == "http_status"
    assert len(requests) == 1
    assert "127.0.0.1" not in requests[0]
    browser.fetch_board_html.assert_not_called()


def test_description_is_valid_with_proposition_and_real_formats():
    # Value proposition for customers must NOT trigger false positive rejection
    salesforce_text = """
    About the Role
    Join our Enterprise Sales team as an Account Executive.
    Responsibilities:
    - Share Salesforce value proposition for existing and new enterprise customers.
    - Drive revenue growth and customer satisfaction across cloud offerings.
    Qualifications:
    - 5+ years of software sales experience in enterprise software.
    - Strong communication, negotiation, and presentation skills.
    """ * 3
    assert description_is_valid(salesforce_text)

    # Bulleted job description without explicit 'responsibilities' header
    bullet_text = """
    • Booking of Import and Local invoices.
    • Settlement of open vendor advances.
    • Monitor GR / IR report for invoice booking.
    • Ensuring weekly Reimbursement of Expenses claims.
    • Timely payment of Third-Party/inter-company Invoices.
    • Bank Reconciliation and audit support across teams.
    About Us
    We are a leading industrial technology manufacturer delivering high quality products.
    Education and Experience:
    Bachelor's degree with 3+ years relevant experience in accounting and finance operations.
    """ * 2
    assert description_is_valid(bullet_text)


@pytest.mark.asyncio
async def test_fetch_ashby_detail_mock():
    mock_client = AsyncMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "jobs": [
            {
                "id": "68a397e7-8a1a-4566-ae41-e8c61dd6ed93",
                "title": "Product Manager",
                "location": "Remote",
                "department": "Product",
                "employmentType": "Full-time",
                "descriptionHtml": """
                <p>About the role: We are looking for a Product Manager to join our fast-growing engineering organization.</p>
                <p>Responsibilities: Lead product roadmap and integrations across multiple core platform services.</p>
                <p>Qualifications: 4+ years experience in technical product management and modern cloud infrastructure.</p>
                """,
            }
        ]
    }
    mock_client.get.return_value = mock_resp

    req = DetailRequest(
        family="ashby",
        public_url="https://jobs.ashbyhq.com/supabase/68a397e7-8a1a-4566-ae41-e8c61dd6ed93",
        board_name="Supabase",
        title="Product Manager",
        provider_config={},
    )
    res = await fetch_ashby_detail(req, mock_client)
    assert res.error_code is None
    assert res.title == "Product Manager"
    assert res.location == "Remote"
    assert res.department == "Product"
    assert res.source == "ashby_api"
    assert "Responsibilities" in res.description


@pytest.mark.asyncio
async def test_ashby_requires_exact_job_identity():
    client = AsyncMock()
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {"jobs": [{
        "id": "other-abc123-extra",
        "jobUrl": "https://jobs.ashbyhq.com/acme/other-abc123-extra",
        "descriptionPlain": "Responsibilities: Build reliable services and manage production deployments.",
    }]}
    client.get.return_value = response
    req = DetailRequest("ashby", "https://jobs.ashbyhq.com/acme/abc123", "Acme", "Engineer", {})
    result = await fetch_ashby_detail(req, client)
    assert result.error_code == "record_not_found"


@pytest.mark.asyncio
async def test_fetch_eightfold_detail_mock():
    mock_client = AsyncMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "name": "Software Engineer 2",
        "location": "Bengaluru, India",
        "department": "Azure",
        "type": "Full-time",
        "job_description": """
        <div>
            <p>Overview: Microsoft Azure is hiring skilled engineers to build next-generation distributed storage systems.</p>
            <p>Responsibilities: Build scalable cloud services, design resilient APIs, and collaborate across teams.</p>
            <p>Qualifications: BS in CS or equivalent experience, 3+ years experience with C++, Java, or Go.</p>
        </div>
        """,
    }
    mock_client.get.return_value = mock_resp

    req = DetailRequest(
        family="eightfold",
        public_url="https://apply.careers.microsoft.com/careers/job/1970393557022260",
        board_name="Microsoft",
        title="Software Engineer 2",
        provider_config={},
    )
    res = await fetch_eightfold_detail(req, mock_client)
    assert res.error_code is None
    assert res.title == "Software Engineer 2"
    assert res.location == "Bengaluru, India"
    assert res.department == "Azure"
    assert res.source == "eightfold_api"
    assert "Overview" in res.description
