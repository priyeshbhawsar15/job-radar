import pytest
from unittest.mock import AsyncMock, patch

from job_radar.services.detail_extractor import DetailExtractor, strip_to_plain_text
from job_radar.services.detail_contracts import ERR_INVALID_DETAIL_URL

RAW_HTML_NO_LOCAL_MATCH = """
<html>
<head><style>.x{color:red}</style><script>var a=1;</script></head>
<body>
<nav>Menu</nav>
<div>Short unrelated text.</div>
<footer>Copyright 2026</footer>
</body>
</html>
"""

INFERRED_PAYLOAD = {
    "title": "Senior Backend Engineer",
    "employer": "Acme Corp",
    "location": "Bangalore, India",
    "salary": "INR 20,00,000 - INR 30,00,000 / yr",
    "jobDescription": (
        "About the role: We are looking for a Senior Backend Engineer to own our platform.\n\n"
        "Responsibilities include designing scalable services, mentoring engineers and driving "
        "architecture decisions.\n\n"
        "Requirements: 5+ years experience, strong skills in distributed "
        "systems, and excellent communication. What you'll do: build, ship, and operate critical "
        "infrastructure. Qualifications: BS in CS or equivalent experience."
    ),
    "jobType": "Full-time",
    "department": "Engineering",
}


@pytest.fixture
def extractor():
    mock_browser = AsyncMock()
    mock_browser.fetch_board_html.return_value = RAW_HTML_NO_LOCAL_MATCH
    return DetailExtractor(browser_client=mock_browser)


def _settings_patch(**overrides):
    defaults = dict(
        JOBOPS_ENDPOINT="https://jobops.example.com",
        JOBOPS_USERNAME="svc_user",
        JOBOPS_PASSWORD="svc_pass",
    )
    defaults.update(overrides)
    return patch.multiple("job_radar.config.settings", **defaults)


@pytest.mark.asyncio
async def test_infer_fallback_success_merges_fields(extractor):
    mock_http_client = AsyncMock()
    mock_http_client.get.side_effect = Exception("network unreachable")

    mock_infer_response = AsyncMock()
    mock_infer_response.status_code = 200
    mock_infer_response.json = lambda: INFERRED_PAYLOAD
    mock_http_client.post.return_value = mock_infer_response

    with _settings_patch():
        res = await extractor.fetch_and_enrich(
            "https://boards.example.com/jobs/123",
            "ExampleBoard",
            "Senior Backend Engineer",
            client=mock_http_client,
        )

    assert res.source == "jobops_infer_fallback"
    assert res.description is not None
    assert "Senior Backend Engineer" in res.description or "Backend Engineer" in res.description
    assert res.location == "Bangalore, India"
    assert res.employment_type == "Full-time"
    assert res.department == "Engineering"

    post_args, post_kwargs = mock_http_client.post.call_args
    assert post_args[0] == "https://jobops.example.com/api/manual-jobs/infer"
    assert "jobDescription" in post_kwargs["json"]
    assert post_kwargs["auth"] == ("svc_user", "svc_pass")


@pytest.mark.asyncio
async def test_infer_fallback_auth_error_returns_empty_result(extractor):
    mock_http_client = AsyncMock()
    mock_http_client.get.side_effect = Exception("network unreachable")

    mock_infer_response = AsyncMock()
    mock_infer_response.status_code = 401
    mock_infer_response.json = lambda: {"error": "unauthorized"}
    mock_http_client.post.return_value = mock_infer_response

    with _settings_patch():
        res = await extractor.fetch_and_enrich(
            "https://boards.example.com/jobs/123",
            "ExampleBoard",
            "Senior Backend Engineer",
            client=mock_http_client,
        )

    assert res.source != "jobops_infer_fallback"
    assert res.error_code == ERR_INVALID_DETAIL_URL


@pytest.mark.asyncio
async def test_infer_fallback_server_error_returns_empty_result(extractor):
    mock_http_client = AsyncMock()
    mock_http_client.get.side_effect = Exception("network unreachable")

    mock_infer_response = AsyncMock()
    mock_infer_response.status_code = 500
    mock_infer_response.json = lambda: {"error": "server error"}
    mock_http_client.post.return_value = mock_infer_response

    with _settings_patch():
        res = await extractor.fetch_and_enrich(
            "https://boards.example.com/jobs/123",
            "ExampleBoard",
            "Senior Backend Engineer",
            client=mock_http_client,
        )

    assert res.source != "jobops_infer_fallback"
    assert res.error_code == ERR_INVALID_DETAIL_URL


@pytest.mark.asyncio
async def test_infer_fallback_skipped_when_endpoint_unconfigured(extractor):
    mock_http_client = AsyncMock()
    mock_http_client.get.side_effect = Exception("network unreachable")

    with _settings_patch(JOBOPS_ENDPOINT=None):
        res = await extractor.fetch_and_enrich(
            "https://boards.example.com/jobs/123",
            "ExampleBoard",
            "Senior Backend Engineer",
            client=mock_http_client,
        )

    mock_http_client.post.assert_not_called()
    assert res.source != "jobops_infer_fallback"


@pytest.mark.asyncio
async def test_infer_fallback_not_invoked_when_local_extraction_succeeds():
    valid_description_html = """
    <html><body><div class="job-description">
    <p>About the role: We are looking for an Engineer to own our platform. Responsibilities
    include designing scalable services. Requirements: 5+ years experience, strong skills in
    distributed systems. What you'll do: build, ship, and operate infrastructure. Qualifications:
    BS in CS.</p>
    </div></body></html>
    """
    mock_browser = AsyncMock()
    mock_browser.fetch_board_html.return_value = valid_description_html
    local_extractor = DetailExtractor(browser_client=mock_browser)

    mock_http_client = AsyncMock()
    mock_http_client.get.side_effect = Exception("network unreachable")

    with _settings_patch():
        res = await local_extractor.fetch_and_enrich(
            "https://boards.example.com/jobs/123",
            "ExampleBoard",
            "Engineer",
            client=mock_http_client,
        )

    mock_http_client.post.assert_not_called()
    assert res.source == "generic_browser_html"


def test_strip_to_plain_text_removes_js_css_and_tags():
    html_input = "<html><head><style>.a{}</style><script>x=1</script></head><body><p>Hello <b>World</b></p></body></html>"
    text = strip_to_plain_text(html_input)
    assert "<" not in text
    assert "script" not in text.lower()
    assert "style" not in text.lower() or ".a{}" not in text
    assert "Hello" in text and "World" in text
