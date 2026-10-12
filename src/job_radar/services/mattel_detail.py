"""Mattel's exact JobPosting contract with a body/listing worksite conflict gate."""

import html
import re
from urllib.parse import urlparse

import httpx

from job_radar.services.detail_contracts import (
    DetailRequest, DetailResult, ERR_DESCRIPTION_INVALID, ERR_DESCRIPTION_MISSING,
    ERR_HTTP_STATUS, ERR_IDENTITY_MISMATCH, ERR_INVALID_DETAIL_URL,
    ERR_LOCATION_CONFLICT, ERR_RESPONSE_TOO_LARGE,
)

_PATH = re.compile(r"^/en/job/[^/]+/[^/]+/\d+/\d+/?$", re.I)


def parse_mattel_detail(raw_html: str, req: DetailRequest) -> DetailResult:
    from job_radar.services.detail_extractor import extract_job_posting, clean_html_to_text, description_is_valid, normalize_detail_sections

    url = urlparse(req.public_url)
    if url.scheme != "https" or url.hostname != "jobs.mattel.com" or url.username or url.password or url.port or not _PATH.fullmatch(url.path):
        return DetailResult.empty(ERR_INVALID_DETAIL_URL)
    jp = extract_job_posting(raw_html)
    if not jp or jp.get("url") != req.public_url:
        return DetailResult.empty(ERR_IDENTITY_MISMATCH)
    title = jp.get("title")
    if not isinstance(title, str) or not title.strip():
        return DetailResult.empty(ERR_IDENTITY_MISMATCH)
    source_title = html.unescape(title).strip()
    if not req.title.casefold().startswith(source_title.casefold()):
        return DetailResult.empty(ERR_IDENTITY_MISMATCH)
    description_raw = jp.get("description")
    if not isinstance(description_raw, str) or not description_raw.strip():
        return DetailResult.empty(ERR_DESCRIPTION_MISSING)
    description = normalize_detail_sections(clean_html_to_text(description_raw), "Mattel")[:40000]
    if not description_is_valid(description):
        return DetailResult.empty(ERR_DESCRIPTION_INVALID)
    location = None
    job_locs = jp.get("jobLocation")
    if isinstance(job_locs, list) and job_locs:
        address = job_locs[0].get("address") if isinstance(job_locs[0], dict) else None
        if isinstance(address, dict) and isinstance(address.get("addressLocality"), str):
            location = address["addressLocality"].strip()
    body_location = re.search(r"(?im)^Location:\s*\n([^\n]+)", description)
    if body_location and location:
        body_value = body_location.group(1).strip()
        if location.casefold() not in body_value.casefold():
            return DetailResult(
                description=description, title=source_title, location=body_value,
                source="mattel_jsonld", error_code=ERR_LOCATION_CONFLICT,
            )
    return DetailResult(description=description, title=source_title, location=location, source="mattel_jsonld")


async def fetch_mattel_detail(req: DetailRequest, client: httpx.AsyncClient) -> DetailResult:
    url = urlparse(req.public_url)
    if url.scheme != "https" or url.hostname != "jobs.mattel.com" or url.username or url.password or url.port or not _PATH.fullmatch(url.path):
        return DetailResult.empty(ERR_INVALID_DETAIL_URL)
    try:
        response = await client.get(req.public_url, follow_redirects=False, timeout=15.0)
    except httpx.HTTPError:
        return DetailResult.empty(ERR_HTTP_STATUS)
    if response.status_code != 200:
        return DetailResult.empty(ERR_HTTP_STATUS)
    if len(response.content) > 1_000_000:
        return DetailResult.empty(ERR_RESPONSE_TOO_LARGE)
    return parse_mattel_detail(response.text, req)
