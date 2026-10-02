"""Direct Ashby detail extraction and API payload fetching."""

import html
import logging
import re
from typing import Mapping, Optional, Tuple
from urllib.parse import urlparse

import httpx

from job_radar.services.detail_contracts import (
    ERR_DESCRIPTION_INVALID,
    ERR_DESCRIPTION_MISSING,
    ERR_HTTP_STATUS,
    ERR_INVALID_DETAIL_URL,
    ERR_INVALID_PAYLOAD,
    ERR_RECORD_NOT_FOUND,
    DetailRequest,
    DetailResult,
)

logger = logging.getLogger(__name__)

_ORG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")
_JOB_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")


def parse_ashby_job_url(
    public_url: str, provider_config: Optional[Mapping[str, object]] = None
) -> Optional[Tuple[str, str]]:
    """Derive (org, job_id) from a canonical Ashby job URL.

    Example:
        https://jobs.ashbyhq.com/supabase/68a397e7-8a1a-4566-ae41-e8c61dd6ed93
        -> ("supabase", "68a397e7-8a1a-4566-ae41-e8c61dd6ed93")
    """
    if not public_url or not isinstance(public_url, str):
        return None

    try:
        parsed = urlparse(public_url)
    except Exception:
        return None

    if parsed.scheme != "https" or parsed.hostname != "jobs.ashbyhq.com" or parsed.username or parsed.password:
        return None
    try:
        if parsed.port is not None:
            return None
    except ValueError:
        return None
    parts = parsed.path.strip("/").split("/")
    if len(parts) == 2 and _ORG_RE.fullmatch(parts[0]) and _JOB_ID_RE.fullmatch(parts[1]):
        return parts[0], parts[1]

    return None


async def fetch_ashby_detail(req: DetailRequest, client: httpx.AsyncClient) -> DetailResult:
    """Fetch job details from Ashby's public posting API."""
    from job_radar.services.detail_extractor import clean_html_to_text, description_is_valid

    parsed = parse_ashby_job_url(req.public_url, req.provider_config)
    if not parsed:
        return DetailResult.empty(ERR_INVALID_DETAIL_URL)

    org, job_id = parsed
    api_url = f"https://api.ashbyhq.com/posting-api/job-board/{org}?includeCompensation=true"
    headers = {
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }

    try:
        resp = await client.get(api_url, headers=headers, follow_redirects=False)
    except httpx.HTTPError as exc:
        logger.info("Ashby detail request failed for %s: %s", org, exc)
        return DetailResult.empty(ERR_HTTP_STATUS)

    if resp.status_code == 404:
        return DetailResult.empty(ERR_RECORD_NOT_FOUND)
    if resp.status_code != 200:
        return DetailResult.empty(ERR_HTTP_STATUS)

    try:
        data = resp.json()
    except Exception:
        return DetailResult.empty(ERR_INVALID_PAYLOAD)

    if not isinstance(data, dict):
        return DetailResult.empty(ERR_INVALID_PAYLOAD)

    jobs = data.get("jobs", [])
    if not isinstance(jobs, list):
        return DetailResult.empty(ERR_INVALID_PAYLOAD)

    target_job = None
    for j in jobs:
        if not isinstance(j, dict):
            continue
        j_id = str(j.get("id") or "")
        j_url = str(j.get("jobUrl") or "")
        if job_id == j_id or parse_ashby_job_url(j_url) == (org, job_id):
            target_job = j
            break

    if not target_job:
        return DetailResult.empty(ERR_RECORD_NOT_FOUND)

    raw_desc = target_job.get("descriptionHtml") or target_job.get("descriptionPlain") or ""
    if not raw_desc or not isinstance(raw_desc, str):
        return DetailResult.empty(ERR_DESCRIPTION_MISSING)

    description = clean_html_to_text(raw_desc)[:40000]
    if not description_is_valid(description, title=req.title):
        return DetailResult.empty(ERR_DESCRIPTION_INVALID)

    title = target_job.get("title").strip() if isinstance(target_job.get("title"), str) else None
    location = target_job.get("location").strip() if isinstance(target_job.get("location"), str) else None
    department = target_job.get("department").strip() if isinstance(target_job.get("department"), str) else None
    employment_type = target_job.get("employmentType").strip() if isinstance(target_job.get("employmentType"), str) else None

    # Extract compensation if present
    salary_raw = None
    comp = target_job.get("compensation")
    if isinstance(comp, dict):
        salary_raw = comp.get("compensationTierSummary")

    return DetailResult(
        description=description,
        location=location,
        department=department,
        employment_type=employment_type,
        title=title,
        salary_raw=salary_raw,
        source="ashby_api",
    )
