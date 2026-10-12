"""Celonis DXP detail API observed from one ordinary public page navigation."""

import re
from urllib.parse import parse_qs, urlparse

import httpx

from job_radar.services.detail_contracts import (
    DetailRequest, DetailResult, ERR_DESCRIPTION_INVALID, ERR_DESCRIPTION_MISSING,
    ERR_HTTP_STATUS, ERR_IDENTITY_MISMATCH, ERR_INVALID_DETAIL_URL,
    ERR_INVALID_PAYLOAD, ERR_RESPONSE_TOO_LARGE,
)

_PATH = "/join-us/open-positions/job-detail"


def _job_id(public_url: str) -> str | None:
    url = urlparse(public_url)
    values = parse_qs(url.query).get("jobId", [])
    if (url.scheme != "https" or url.hostname != "careers.celonis.com" or url.path != _PATH
            or url.username or url.password or url.port or len(values) != 1 or not re.fullmatch(r"\d{8,12}", values[0])):
        return None
    return values[0]


def _compatible_title(listing_title: str, source_title: str) -> bool:
    def words(value):
        return [word for word in re.findall(r"[\w]+", value.casefold()) if word not in {"senior", "sr", "junior", "jr"}]
    return words(listing_title) == words(source_title)


def parse_celonis_detail(data: object, req: DetailRequest) -> DetailResult:
    from job_radar.services.detail_extractor import clean_html_to_text, description_is_valid, normalize_detail_sections

    requested_id = _job_id(req.public_url)
    if not requested_id:
        return DetailResult.empty(ERR_INVALID_DETAIL_URL)
    if not isinstance(data, dict) or str(data.get("id")) != requested_id:
        return DetailResult.empty(ERR_IDENTITY_MISMATCH)
    title = data.get("title")
    if not isinstance(title, str) or not title.strip() or not _compatible_title(req.title, title):
        return DetailResult.empty(ERR_IDENTITY_MISMATCH)
    raw = data.get("description")
    if not isinstance(raw, str) or not raw.strip():
        return DetailResult.empty(ERR_DESCRIPTION_MISSING)
    description = normalize_detail_sections(clean_html_to_text(raw), "Celonis")[:40000]
    if not description_is_valid(description, title=title):
        return DetailResult.empty(ERR_DESCRIPTION_INVALID)
    location = data.get("groupedLocation")
    return DetailResult(
        description=description, title=title.strip(),
        location=location.strip()[:200] if isinstance(location, str) and location.strip() else None,
        source="celonis_dxp_api",
    )


async def fetch_celonis_detail(req: DetailRequest, client: httpx.AsyncClient) -> DetailResult:
    job_id = _job_id(req.public_url)
    if not job_id:
        return DetailResult.empty(ERR_INVALID_DETAIL_URL)
    # This endpoint was observed in the page's own network responses, not inferred
    # from an ATS token or guessed from a different job-board contract.
    url = f"https://dxp-api.celonis.com/v1/jobs/{job_id}"
    try:
        response = await client.get(url, follow_redirects=False, timeout=15.0, headers={"Accept": "application/json"})
    except httpx.HTTPError:
        return DetailResult.empty(ERR_HTTP_STATUS)
    if response.status_code != 200:
        return DetailResult.empty(ERR_HTTP_STATUS)
    if len(response.content) > 250_000:
        return DetailResult.empty(ERR_RESPONSE_TOO_LARGE)
    try:
        data = response.json()
    except ValueError:
        return DetailResult.empty(ERR_INVALID_PAYLOAD)
    return parse_celonis_detail(data, req)
