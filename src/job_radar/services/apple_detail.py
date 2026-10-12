"""Bounded extraction from Apple's public, server-rendered detail hydration."""

import json
import re
from urllib.parse import urlparse

import httpx

from job_radar.services.detail_contracts import (
    DetailRequest, DetailResult, ERR_DESCRIPTION_INVALID, ERR_DESCRIPTION_MISSING,
    ERR_HTTP_STATUS, ERR_INVALID_DETAIL_URL, ERR_INVALID_PAYLOAD, ERR_RESPONSE_TOO_LARGE,
)

_DETAIL_PATH = re.compile(r"^/[a-z]{2}(?:-[a-z]{2})?/details/(\d{6,12})/[^/]+/?$", re.I)
_HYDRATION = re.compile(r'window\.__staticRouterHydrationData\s*=\s*JSON\.parse\(("(?:\\.|[^"\\])*")\)', re.S)


def parse_apple_detail(html_text: str, public_url: str) -> DetailResult:
    from job_radar.services.detail_extractor import description_is_valid

    url = urlparse(public_url)
    match = _DETAIL_PATH.fullmatch(url.path)
    if url.scheme != "https" or url.hostname != "jobs.apple.com" or url.username or url.password or url.port or not match:
        return DetailResult.empty(ERR_INVALID_DETAIL_URL)
    payload = _HYDRATION.search(html_text)
    if not payload:
        return DetailResult.empty(ERR_INVALID_PAYLOAD)
    try:
        data = json.loads(json.loads(payload.group(1)))
        job = data["loaderData"]["jobDetails"]["jobsData"]
    except (ValueError, TypeError, KeyError):
        return DetailResult.empty(ERR_INVALID_PAYLOAD)
    if not isinstance(job, dict) or str(job.get("jobNumber")) != match.group(1):
        return DetailResult.empty(ERR_INVALID_PAYLOAD)
    title = job.get("postingTitle")
    if not isinstance(title, str) or not title.strip():
        return DetailResult.empty(ERR_INVALID_PAYLOAD)
    fields = (
        ("Summary", "jobSummary"),
        ("Responsibilities", "description"),
        ("Minimum Qualifications", "minimumQualifications"),
        ("Preferred Qualifications", "preferredQualifications"),
    )
    sections = [f"{heading}\n{job[key].strip()}" for heading, key in fields if isinstance(job.get(key), str) and job[key].strip()]
    if not sections:
        return DetailResult.empty(ERR_DESCRIPTION_MISSING)
    description = "\n\n".join(sections)[:40000]
    if not description_is_valid(description, title=title):
        return DetailResult.empty(ERR_DESCRIPTION_INVALID)
    locations = job.get("locations")
    location = None
    if isinstance(locations, list):
        names = [loc.get("name") for loc in locations if isinstance(loc, dict) and isinstance(loc.get("name"), str)]
        location = ", ".join(dict.fromkeys(names))[:200] or None
    return DetailResult(description=description, title=title.strip(), location=location, source="apple_hydration")


async def fetch_apple_detail(req: DetailRequest, client: httpx.AsyncClient) -> DetailResult:
    url = urlparse(req.public_url)
    if url.scheme != "https" or url.hostname != "jobs.apple.com" or url.username or url.password or url.port or not _DETAIL_PATH.fullmatch(url.path):
        return DetailResult.empty(ERR_INVALID_DETAIL_URL)
    try:
        response = await client.get(req.public_url, follow_redirects=False, timeout=15.0)
    except httpx.HTTPError:
        return DetailResult.empty(ERR_HTTP_STATUS)
    if response.status_code != 200:
        return DetailResult.empty(ERR_HTTP_STATUS)
    if len(response.content) > 2_000_000:
        return DetailResult.empty(ERR_RESPONSE_TOO_LARGE)
    return parse_apple_detail(response.text, req.public_url)
