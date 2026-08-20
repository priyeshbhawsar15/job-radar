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
    ERR_RECORD_NOT_FOUND,
)
from job_radar.services.oracle_detail import (
    extract_oracle_public_id,
    find_oracle_item,
    compose_oracle_description,
    fetch_oracle_detail,
)

FIXTURES = Path(__file__).parent / "fixtures" / "descriptions"


def test_extract_oracle_public_id():
    url = "https://eeho.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/job/337440/"
    assert extract_oracle_public_id(url) == "337440"

    url_jpmc = "https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/job/210729984"
    assert extract_oracle_public_id(url_jpmc) == "210729984"

    url_invalid = "https://eeho.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/search/"
    assert extract_oracle_public_id(url_invalid) is None


def test_find_oracle_item_matches_id_never_requisition_id():
    oracle_json = json.loads((FIXTURES / "oracle_requisition.json").read_text())
    item = find_oracle_item(oracle_json, "337440")
    assert item is not None
    assert str(item["Id"]) == "337440"
    assert str(item["RequisitionId"]) != "337440"

    # Must NOT match on internal RequisitionId 900000000000001
    assert find_oracle_item(oracle_json, "900000000000001") is None


def test_find_oracle_item_malformed_returns_none():
    assert find_oracle_item({}, "337440") is None
    assert find_oracle_item({"items": []}, "337440") is None
    assert find_oracle_item({"items": [{"Id": "999"}]}, "337440") is None


def test_compose_oracle_description_and_sections():
    oracle_json = json.loads((FIXTURES / "oracle_requisition.json").read_text())
    item = find_oracle_item(oracle_json, "337440")
    desc = compose_oracle_description(item)
    assert desc is not None
    assert "ORACLE_FULL_DESCRIPTION_TOKEN" in desc
    assert "ORACLE_RESPONSIBILITIES_TOKEN" in desc
    assert "ORACLE_SHORT_TOKEN" not in desc
    assert "ORACLE_CORPORATE_TOKEN" not in desc


def test_compose_oracle_description_jpmc_empty_optional_sections():
    jpmc_json = json.loads((FIXTURES / "jpmc_requisition.json").read_text())
    item = find_oracle_item(jpmc_json, "210729984")
    desc = compose_oracle_description(item)
    assert desc is not None
    assert "JPMC_FULL_DESCRIPTION_TOKEN" in desc
    assert "RESPONSIBILITIES\n" not in desc  # no empty section header added
    assert "QUALIFICATIONS\n" not in desc


def test_compose_oracle_description_amex_split_fields():
    amex_json = json.loads((FIXTURES / "amex_requisition.json").read_text())
    item = find_oracle_item(amex_json, "26012235")
    desc = compose_oracle_description(item)
    assert desc is not None
    assert "AMEX_FULL_DESCRIPTION_TOKEN" in desc
    assert "AMEX_RESPONSIBILITIES_TOKEN" in desc
    assert "AMEX_QUALIFICATIONS_TOKEN" in desc
    assert "AMEX_CORPORATE_BOILERPLATE_TOKEN" not in desc
    assert "AMEX_ORGANIZATION_BOILERPLATE_TOKEN" not in desc


@pytest.mark.asyncio
async def test_fetch_oracle_detail_http_mock_success():
    oracle_fixture = (FIXTURES / "oracle_requisition.json").read_bytes()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "eeho.fa.us2.oraclecloud.com"
        assert "finder=ById%3BId%3D%22337440%22" in str(request.url) or 'finder=ById;Id="337440"' in str(request.url)
        return httpx.Response(200, content=oracle_fixture, headers={"Content-Type": "application/json"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        req = DetailRequest(
            family="oracle",
            public_url="https://eeho.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/job/337440/",
            board_name="Oracle",
            title="Software Developer 4",
            provider_config={
                "api_origin": "https://eeho.fa.us2.oraclecloud.com",
                "allowed_origins": ["eeho.fa.us2.oraclecloud.com"],
            },
        )
        res = await fetch_oracle_detail(req, client)
        assert res.description is not None
        assert "ORACLE_FULL_DESCRIPTION_TOKEN" in res.description
        assert res.source == "oracle_hcm_detail"
        assert res.error_code is None
        assert res.location == "BENGALURU, KARNATAKA, India"


@pytest.mark.asyncio
async def test_fetch_oracle_detail_with_site_number():
    oracle_fixture = (FIXTURES / "oracle_requisition.json").read_bytes()

    def handler(request: httpx.Request) -> httpx.Response:
        assert "siteNumber=CX_45001" in str(request.url) or "siteNumber%3DCX_45001" in str(request.url)
        return httpx.Response(200, content=oracle_fixture)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        req = DetailRequest(
            family="oracle",
            public_url="https://eeho.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/job/337440/",
            board_name="Oracle",
            title="Software Developer 4",
            provider_config={
                "api_origin": "https://eeho.fa.us2.oraclecloud.com",
                "site_number": "CX_45001",
                "allowed_origins": ["eeho.fa.us2.oraclecloud.com"],
            },
        )
        res = await fetch_oracle_detail(req, client)
        assert res.description is not None


@pytest.mark.asyncio
async def test_fetch_oracle_detail_boundary_violation():
    async with httpx.AsyncClient() as client:
        req = DetailRequest(
            family="oracle",
            public_url="https://unallowed.example.com/job/337440/",
            board_name="Oracle",
            title="Dev",
            provider_config={
                "api_origin": "https://eeho.fa.us2.oraclecloud.com",
                "allowed_origins": ["eeho.fa.us2.oraclecloud.com"],
            },
        )
        res = await fetch_oracle_detail(req, client)
        assert res.error_code == ERR_BOUNDARY_VIOLATION
