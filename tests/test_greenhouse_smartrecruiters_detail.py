import pytest
import httpx

from job_radar.adapters.smartrecruiters import SmartRecruitersAdapter
from job_radar.services.detail_contracts import DetailRequest
from job_radar.services.greenhouse_detail import build_greenhouse_detail_url, fetch_greenhouse_detail, parse_greenhouse_detail_url
from job_radar.services.smartrecruiters_detail import build_smartrecruiters_detail_url, fetch_smartrecruiters_detail, parse_smartrecruiters_detail_url


@pytest.mark.parametrize("url, expected", [
    ("https://job-boards.greenhouse.io/razorpaysoftwareprivatelimited/jobs/4718628005", ("razorpaysoftwareprivatelimited", "4718628005")),
    ("https://job-boards.greenhouse.io/sourcegraph91/jobs/6103567004", ("sourcegraph91", "6103567004")),
    ("https://job-boards.eu.greenhouse.io/cognite/jobs/123", ("cognite", "123")),
    ("https://boards-api.greenhouse.io/v1/boards/sourcegraph91/jobs/6103567004", ("sourcegraph91", "6103567004")),
])
def test_parse_greenhouse_exact_canonical_tokens(url, expected):
    assert parse_greenhouse_detail_url(url) == expected


def test_greenhouse_rejects_unapproved_hosts_and_unconfigured_gh_jid():
    assert parse_greenhouse_detail_url("https://evil.example/razorpay/jobs/1") is None
    assert parse_greenhouse_detail_url("https://job-boards.greenhouse.io/razorpay/jobs/not-a-number") is None
    assert parse_greenhouse_detail_url("https://job-boards.greenhouse.io/razorpay?gh_jid=1") is None
    assert parse_greenhouse_detail_url("https://job-boards.greenhouse.io/razorpay?gh_jid=1", {"greenhouse_token": "razorpaysoftwareprivatelimited"}) == ("razorpaysoftwareprivatelimited", "1")


@pytest.mark.asyncio
async def test_greenhouse_detail_preserves_provider_title_and_location():
    req = DetailRequest("greenhouse", "https://job-boards.greenhouse.io/sourcegraph91/jobs/6103567004", "Sourcegraph", "old", {})
    payload = {"title": "Agent Engineer [IC4]", "location": {"name": "Remote"}, "content": "<h2>Responsibilities</h2><p>Build reliable systems with a thoughtful engineering team.</p><h2>Qualifications</h2><p>Experience building distributed systems and strong communication skills.</p><h2>Skills</h2><p>Python, Go, and cloud infrastructure.</p>"}
    def handler(request):
        assert str(request.url) == build_greenhouse_detail_url("sourcegraph91", "6103567004")
        return httpx.Response(200, json=payload)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await fetch_greenhouse_detail(req, client)
    assert result.error_code is None
    assert result.title == "Agent Engineer [IC4]"
    assert result.location == "Remote"
    assert result.employment_type is None and result.department is None


def test_smartrecruiters_adapter_uses_company_identifier_not_display_name():
    payload = '{"content":[{"id":"83557431","name":"Support Engineer","company":{"identifier":"Vmware2"},"location":{"city":"Bengaluru","country":"in"}}]}'
    candidate = SmartRecruitersAdapter().parse_raw_payload(payload, "VMware", "https://careers.smartrecruiters.com/Vmware2")[0]
    assert candidate.raw_url == "https://jobs.smartrecruiters.com/Vmware2/83557431"
    assert candidate.extra_payload["smartrecruiters_company_identifier"] == "Vmware2"


@pytest.mark.asyncio
async def test_smartrecruiters_detail_sections_and_safe_api_url():
    assert parse_smartrecruiters_detail_url("https://evil.example/Vmware2/83557431") is None
    assert parse_smartrecruiters_detail_url("https://jobs.smartrecruiters.com/Vmware2/83557431") == ("Vmware2", "83557431")
    req = DetailRequest("smartrecruiters", "https://jobs.smartrecruiters.com/Vmware2/83557431", "VMware", "old", {})
    payload = {"name": "Technical Support Engineer", "location": {"fullLocation": "Bengaluru, KA, India"}, "typeOfEmployment": {"label": "Full-time"}, "function": {"label": "Engineering"}, "jobAd": {"sections": {"jobDescription": {"title": "Job Description", "text": "<p>Responsibilities include resolving complex customer issues and building reliable technical solutions.</p><p>Requirements include strong communication, Linux, networking, and cloud experience.</p>"}, "qualifications": {"title": "Qualifications", "text": ""}, "additionalInformation": {"title": "Additional Information", "text": "<p>All information is confidential according to EEO guidelines.</p>"}}}}
    def handler(request):
        assert str(request.url) == build_smartrecruiters_detail_url("Vmware2", "83557431")
        return httpx.Response(200, json=payload)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await fetch_smartrecruiters_detail(req, client)
    assert result.error_code is None
    assert result.title == "Technical Support Engineer"
    assert result.location == "Bengaluru, KA, India"
    assert result.employment_type == "Full-time" and result.department == "Engineering"
    assert "EEO" not in result.description
