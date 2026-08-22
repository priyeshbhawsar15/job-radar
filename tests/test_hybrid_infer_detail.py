import pytest
import httpx
from unittest.mock import MagicMock, patch
from job_radar.services.detail_extractor import detail_extractor, strip_to_plain_text, DetailResult
from job_radar.config import settings

LONG_VALID_JD = """
About the Role:
We are seeking a Senior Software Engineer to join our team in Bangalore.

Responsibilities:
- Design and build distributed scalable backend services in Python and FastAPI.
- Collaborate with frontend engineers, product managers, and UI designers.
- Maintain high code quality through unit testing, integration tests, and code reviews.

Qualifications & Requirements:
- 5+ years of experience in backend development.
- Strong knowledge of database design, SQL, and async Python frameworks.
- Excellent communication and problem-solving skills.
"""

@pytest.mark.asyncio
async def test_infer_fallback_success_merges_fields(monkeypatch):
    monkeypatch.setattr(settings, "JOBOPS_ENDPOINT", "http://192.168.2.201:3005")
    monkeypatch.setattr(settings, "JOBOPS_USERNAME", "priyesh")
    monkeypatch.setattr(settings, "JOBOPS_PASSWORD", "itwasmeDIO!")

    sample_html = f"<html><body><h1>Senior Developer</h1><p>{LONG_VALID_JD}</p></body></html>"

    async def mock_post(url, **kwargs):
        resp = MagicMock()
        if "/api/auth/login" in url:
            resp.status_code = 200
            resp.json.return_value = {"ok": True, "data": {"token": "fake-jwt-token"}}
        elif "/api/manual-jobs/infer" in url:
            resp.status_code = 200
            resp.json.return_value = {
                "ok": True,
                "data": {
                    "job": {
                        "title": "Senior Developer",
                        "jobDescription": LONG_VALID_JD,
                        "location": "Bangalore, India",
                        "salary": "INR 20,000,000 / yr",
                        "jobType": "Full-time",
                        "department": "Engineering"
                    }
                }
            }
            assert kwargs.get("headers", {}).get("Authorization") == "Bearer fake-jwt-token"
        return resp

    async with httpx.AsyncClient() as client:
        with patch.object(client, "post", side_effect=mock_post):
            res = await detail_extractor.fetch_jobops_infer_fallback(sample_html, client)
            assert res is not None
            assert res.source == "jobops_infer_fallback"
            assert "Responsibilities:" in res.description
            assert res.location == "Bangalore, India"
            assert res.salary_raw == "INR 20,000,000 / yr"
            assert res.employment_type == "Full-time"
            assert res.department == "Engineering"

@pytest.mark.asyncio
async def test_infer_fallback_auth_error_returns_empty_result(monkeypatch):
    monkeypatch.setattr(settings, "JOBOPS_ENDPOINT", "http://192.168.2.201:3005")
    monkeypatch.setattr(settings, "JOBOPS_USERNAME", "priyesh")
    monkeypatch.setattr(settings, "JOBOPS_PASSWORD", "wrongpass")

    sample_html = "<html><body><p>Responsibilities include testing. Requirements: Python expertise.</p></body></html>"

    async def mock_post(url, **kwargs):
        resp = MagicMock()
        if "/api/auth/login" in url:
            resp.status_code = 401
            resp.json.return_value = {"ok": False, "error": {"message": "Unauthorized"}}
        return resp

    async with httpx.AsyncClient() as client:
        with patch.object(client, "post", side_effect=mock_post):
            res = await detail_extractor.fetch_jobops_infer_fallback(sample_html, client)
            assert res is None

def test_strip_to_plain_text_removes_js_css_and_tags():
    html_input = """
    <html>
        <head>
            <style>body { color: red; }</style>
            <script>console.log('secret');</script>
        </head>
        <body>
            <nav>Nav links</nav>
            <h1>Job Title</h1>
            <p>Main content paragraph.</p>
        </body>
    </html>
    """
    text = strip_to_plain_text(html_input)
    assert "console.log" not in text
    assert "body { color" not in text
    assert "Job Title" in text
    assert "Main content paragraph." in text
