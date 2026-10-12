"""Exact Avature JobDetail identity and narrative duties for Tesco."""

import re
from urllib.parse import urlparse

import httpx

from job_radar.services.detail_contracts import (
    DetailRequest, DetailResult, ERR_DESCRIPTION_INVALID, ERR_DESCRIPTION_MISSING,
    ERR_HTTP_STATUS, ERR_IDENTITY_MISMATCH, ERR_INVALID_DETAIL_URL,
    ERR_RESPONSE_TOO_LARGE,
)

_PATH = re.compile(r"^/en_GB/careers/JobDetail/[^/]+/(\d+)/?$", re.I)


def parse_tesco_detail(raw_html: str, req: DetailRequest) -> DetailResult:
    from job_radar.services.detail_extractor import extract_job_posting, clean_html_to_text, description_is_valid

    url = urlparse(req.public_url)
    match = _PATH.fullmatch(url.path)
    if url.scheme != "https" or url.hostname != "careers.tesco.com" or url.username or url.password or url.port or not match:
        return DetailResult.empty(ERR_INVALID_DETAIL_URL)
    jp = extract_job_posting(raw_html)
    if not jp:
        return DetailResult.empty(ERR_DESCRIPTION_MISSING)
    identifier = jp.get("identifier")
    title = jp.get("title")
    if (not isinstance(identifier, dict) or str(identifier.get("value")) != match.group(1)
            or not isinstance(title, str) or not title.strip()
            or title.casefold().strip() != req.title.casefold().strip()):
        return DetailResult.empty(ERR_IDENTITY_MISMATCH)
    raw = jp.get("description")
    if not isinstance(raw, str) or not raw.strip():
        return DetailResult.empty(ERR_DESCRIPTION_MISSING)
    text = clean_html_to_text(raw)
    # The second observed page names a different senior data-engineering role in
    # its body despite a matching Avature id and listing title. Hold that conflict.
    advertised = re.search(r"(?i)we['’]re looking for an experienced ([^.\n]{8,90}?) with \d", text[:1200])
    if advertised and title.casefold() not in advertised.group(1).casefold():
        return DetailResult.empty(ERR_IDENTITY_MISMATCH)
    lead = re.match(r"(?is)^As a (?:Principal )?Software Development Engineer, you\b", text)
    if not lead or len(re.findall(r"\b(?:you|I)\s+(?:own|guide|build|design|deliver|solve|write|contribute|set|innovate)\b", text[:3500], re.I)) < 3:
        return DetailResult.empty(ERR_DESCRIPTION_INVALID)
    description = "Responsibilities\n" + text
    description = re.sub(r"(?im)^(Experience relevant for this job:)\s*$", r"Qualifications\n\1", description, count=1)
    description = description[:40000]
    if not description_is_valid(description):
        return DetailResult.empty(ERR_DESCRIPTION_INVALID)
    location = None
    job_loc = jp.get("jobLocation")
    if isinstance(job_loc, dict):
        address = job_loc.get("address")
        if isinstance(address, dict) and isinstance(address.get("addressLocality"), str):
            location = address["addressLocality"].strip()[:200]
    return DetailResult(description=description, title=title.strip(), location=location, source="tesco_jobposting")


async def fetch_tesco_detail(req: DetailRequest, client: httpx.AsyncClient) -> DetailResult:
    url = urlparse(req.public_url)
    if url.scheme != "https" or url.hostname != "careers.tesco.com" or url.username or url.password or url.port or not _PATH.fullmatch(url.path):
        return DetailResult.empty(ERR_INVALID_DETAIL_URL)
    try:
        response = await client.get(req.public_url, follow_redirects=False, timeout=15.0)
    except httpx.HTTPError:
        return DetailResult.empty(ERR_HTTP_STATUS)
    if response.status_code != 200:
        return DetailResult.empty(ERR_HTTP_STATUS)
    if len(response.content) > 1_000_000:
        return DetailResult.empty(ERR_RESPONSE_TOO_LARGE)
    return parse_tesco_detail(response.text, req)
