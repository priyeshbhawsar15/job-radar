import json

import httpx
import pytest

from job_radar.services.oracle_listing import (
    OracleListingError,
    fetch_oracle_listing_payload,
)

ORACLE_CONFIG = {
    "api_origin": "https://eeho.fa.us2.oraclecloud.com",
    "allowed_origins": [
        "https://eeho.fa.us2.oraclecloud.com",
        "https://careers.oracle.com",
    ],
    "site_number": "CX_45001",
}

LISTING_CONFIG = {
    "keyword": "Software Engineer",
    "location": "India",
    "limit": 10,
}


def _client_with_handler(handler) -> httpx.AsyncClient:
    transport = httpx.MockTransport(handler)
    return httpx.AsyncClient(transport=transport, follow_redirects=True)


@pytest.mark.asyncio
async def test_fetch_oracle_listing_payload_builds_verified_finder_without_double_encoding():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith(
            "/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
        )
        assert request.url.params["onlyData"] == "true"
        assert request.url.params["expand"] == "requisitionList.secondaryLocations"
        assert request.url.params["finder"] == (
            "findReqs;siteNumber=CX_45001,limit=10,"
            "keyword=Software Engineer,location=India"
        )
        assert "%2520" not in str(request.url)
        return httpx.Response(200, json={"items": [{"requisitionList": []}]})

    async with _client_with_handler(handler) as client:
        text = await fetch_oracle_listing_payload(LISTING_CONFIG, ORACLE_CONFIG, client)

    assert json.loads(text) == {"items": [{"requisitionList": []}]}


@pytest.mark.asyncio
async def test_fetch_oracle_listing_payload_rejects_invalid_or_pathful_provider_config():
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("transport must not be called for invalid config")

    invalid_oracle_config = {
        "api_origin": "https://eeho.fa.us2.oraclecloud.com/path",
        "allowed_origins": ["https://eeho.fa.us2.oraclecloud.com/path"],
        "site_number": "CX_45001",
    }

    async with _client_with_handler(handler) as client:
        with pytest.raises(OracleListingError) as error:
            await fetch_oracle_listing_payload(LISTING_CONFIG, invalid_oracle_config, client)

    assert error.value.code == "invalid_provider_config"


@pytest.mark.asyncio
async def test_fetch_oracle_listing_payload_rejects_missing_site_number():
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("transport must not be called for invalid config")

    missing_site_config = {
        "api_origin": "https://eeho.fa.us2.oraclecloud.com",
        "allowed_origins": ["https://eeho.fa.us2.oraclecloud.com"],
    }

    async with _client_with_handler(handler) as client:
        with pytest.raises(OracleListingError) as error:
            await fetch_oracle_listing_payload(LISTING_CONFIG, missing_site_config, client)

    assert error.value.code == "invalid_provider_config"


@pytest.mark.asyncio
async def test_fetch_oracle_listing_payload_rejects_final_host_outside_allowlist():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "eeho.fa.us2.oraclecloud.com":
            return httpx.Response(
                302, headers={"Location": "https://outside.example/jobs"}
            )
        return httpx.Response(200, json={"items": [{"requisitionList": []}]})

    async with _client_with_handler(handler) as client:
        with pytest.raises(OracleListingError) as error:
            await fetch_oracle_listing_payload(LISTING_CONFIG, ORACLE_CONFIG, client)

    assert error.value.code == "boundary_violation"


@pytest.mark.asyncio
async def test_fetch_oracle_listing_payload_maps_connect_error_to_http_status():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom", request=request)

    async with _client_with_handler(handler) as client:
        with pytest.raises(OracleListingError) as error:
            await fetch_oracle_listing_payload(LISTING_CONFIG, ORACLE_CONFIG, client)

    assert error.value.code == "http_status"


@pytest.mark.asyncio
async def test_fetch_oracle_listing_payload_maps_non_200_to_http_status():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="service unavailable")

    async with _client_with_handler(handler) as client:
        with pytest.raises(OracleListingError) as error:
            await fetch_oracle_listing_payload(LISTING_CONFIG, ORACLE_CONFIG, client)

    assert error.value.code == "http_status"


@pytest.mark.asyncio
async def test_fetch_oracle_listing_payload_rejects_response_over_five_mib():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=b"x" * (5 * 1024 * 1024 + 1),
            headers={"Content-Type": "application/json"},
        )

    async with _client_with_handler(handler) as client:
        with pytest.raises(OracleListingError) as error:
            await fetch_oracle_listing_payload(LISTING_CONFIG, ORACLE_CONFIG, client)

    assert error.value.code == "response_too_large"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "body",
    [
        b"not json",
        b'{"no_items": true}',
        b'{"items": []}',
        b'{"items": [{"requisitionList": "not-a-list"}]}',
    ],
)
async def test_fetch_oracle_listing_payload_rejects_invalid_json_or_schema(body):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=body)

    async with _client_with_handler(handler) as client:
        with pytest.raises(OracleListingError) as error:
            await fetch_oracle_listing_payload(LISTING_CONFIG, ORACLE_CONFIG, client)

    assert error.value.code == "invalid_payload"
