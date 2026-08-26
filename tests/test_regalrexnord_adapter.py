import json
from pathlib import Path
import pytest
import httpx

from job_radar.adapters.registry import adapter_registry
from job_radar.services.engine import PipelineExecutionEngine
from job_radar.services.detail_extractor import DetailExtractor, description_is_valid
from job_radar.services.location import is_india_eligible

FIXTURE_PATH = Path("tests/fixtures/workday/regalrexnord.json")


def test_regalrexnord_fixture_and_adapter_contract():
    assert FIXTURE_PATH.exists(), f"Regal Rexnord fixture missing at {FIXTURE_PATH}"
    payload_text = FIXTURE_PATH.read_text()

    adapter = adapter_registry.get("workday")
    assert adapter is not None

    target_url = "https://regalrexnord.wd1.myworkdayjobs.com/en-US/Careers?locationCountry=c4f78be1a8f14da0ab49ce1162348a5e"
    board_name = "Regal Rexnord"

    extracted = adapter.parse_raw_payload(payload_text, board_name, target_url)
    assert len(extracted) == 20

    first = extracted[0]
    assert first.title == ".Net Backend Engineer"
    assert first.company == "Regal Rexnord"
    assert first.location == "Hyderabad, Telangana, India"
    assert first.raw_url == "https://regalrexnord.wd1.myworkdayjobs.com/en-US/Careers/job/Hyderabad-Telangana-India/XMLNAME-Net-Backend-Engineer_R26_04268"

    is_eligible, reason = is_india_eligible(first.location)
    assert is_eligible is True


@pytest.mark.asyncio
async def test_regalrexnord_detail_extraction_contract():
    raw_url = "https://regalrexnord.wd1.myworkdayjobs.com/en-US/Careers/job/Hyderabad-Telangana-India/XMLNAME-Net-Backend-Engineer_R26_04268"
    cxs_detail_url = "https://regalrexnord.wd1.myworkdayjobs.com/wday/cxs/regalrexnord/Careers/job/Hyderabad-Telangana-India/XMLNAME-Net-Backend-Engineer_R26_04268"

    mock_cxs_detail_response = {
        "jobPostingInfo": {
            "title": ".Net Backend Engineer",
            "jobDescription": "<p>Work Model: You will work in a hybrid model onsite at your designated Regal Rexnord location with flexibility to work remotely. Responsibilities include building microservices, developing backend solutions using .NET Core, C#, Azure, SQL Server, and Industrial IoT frameworks. Requirements: 5 to 8 years of relevant software engineering experience in enterprise application development.</p><ul><li>Design and build microservices</li><li>Develop backend solutions using Azure</li></ul>",
            "location": "Hyderabad, Telangana, India",
            "postedOn": "Posted Today"
        }
    }

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == cxs_detail_url:
            return httpx.Response(200, json=mock_cxs_detail_response)
        return httpx.Response(404, json={})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        resp = await client.get(cxs_detail_url)
        assert resp.status_code == 200
        raw_desc = resp.json()["jobPostingInfo"]["jobDescription"]
        from job_radar.services.engine import clean_workday_html
        clean_desc = clean_workday_html(raw_desc)
        assert len(clean_desc) > 200
        assert description_is_valid(clean_desc, title=".Net Backend Engineer")
