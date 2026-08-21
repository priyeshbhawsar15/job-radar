"""Bounded direct Oracle Fusion listing transport and response validation."""

from typing import Any, Mapping
from urllib.parse import urlparse

import httpx

from job_radar.services.detail_contracts import (
    ERR_INVALID_PROVIDER_CONFIG,
    ERR_BOUNDARY_VIOLATION,
    ERR_HTTP_STATUS,
    ERR_RESPONSE_TOO_LARGE,
    ERR_INVALID_PAYLOAD,
)
from job_radar.services.oracle_detail import validate_oracle_config

MAX_RESPONSE_BYTES = 5 * 1024 * 1024


class OracleListingError(RuntimeError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _validate_listing_config(listing_config: Mapping[str, Any]) -> bool:
    if not isinstance(listing_config, dict):
        return False
    keyword = listing_config.get("keyword")
    location = listing_config.get("location")
    limit = listing_config.get("limit")
    if not keyword or not isinstance(keyword, str):
        return False
    if not location or not isinstance(location, str):
        return False
    if not isinstance(limit, int) or isinstance(limit, bool) or not (1 <= limit <= 100):
        return False
    return True


async def fetch_oracle_listing_payload(
    listing_config: Mapping[str, Any],
    oracle_config: Mapping[str, Any],
    client: httpx.AsyncClient,
) -> str:
    """Return a validated Oracle Fusion listing response as JSON text."""
    if not validate_oracle_config(oracle_config):
        raise OracleListingError(ERR_INVALID_PROVIDER_CONFIG)

    site_number = oracle_config.get("site_number")
    if not site_number or not isinstance(site_number, str):
        raise OracleListingError(ERR_INVALID_PROVIDER_CONFIG)

    if not _validate_listing_config(listing_config):
        raise OracleListingError(ERR_INVALID_PROVIDER_CONFIG)

    api_origin = oracle_config["api_origin"]
    allowed_origins = oracle_config["allowed_origins"]
    allowed_hosts = {urlparse(o).netloc for o in allowed_origins}

    keyword = listing_config["keyword"]
    location = listing_config["location"]
    limit = listing_config["limit"]

    finder = (
        f"findReqs;siteNumber={site_number},limit={limit},"
        f"keyword={keyword},location={location}"
    )
    params = {
        "onlyData": "true",
        "expand": "requisitionList.secondaryLocations",
        "finder": finder,
    }
    endpoint = f"{api_origin}/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
    }

    try:
        response = await client.get(endpoint, params=params, headers=headers)
    except httpx.HTTPError:
        raise OracleListingError(ERR_HTTP_STATUS)

    final_host = urlparse(str(response.url)).netloc
    if final_host not in allowed_hosts:
        raise OracleListingError(ERR_BOUNDARY_VIOLATION)

    if response.status_code != 200:
        raise OracleListingError(ERR_HTTP_STATUS)

    if len(response.content) > MAX_RESPONSE_BYTES:
        raise OracleListingError(ERR_RESPONSE_TOO_LARGE)

    try:
        data = response.json()
    except Exception:
        raise OracleListingError(ERR_INVALID_PAYLOAD)

    if not isinstance(data, dict):
        raise OracleListingError(ERR_INVALID_PAYLOAD)
    items = data.get("items")
    if not isinstance(items, list) or not items:
        raise OracleListingError(ERR_INVALID_PAYLOAD)
    first_item = items[0]
    if not isinstance(first_item, dict) or not isinstance(
        first_item.get("requisitionList"), list
    ):
        raise OracleListingError(ERR_INVALID_PAYLOAD)

    return response.text
