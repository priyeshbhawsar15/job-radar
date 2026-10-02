"""Direct Eightfold detail extraction and API payload fetching."""

import html
import logging
import re
from typing import Mapping, Optional, Tuple
from urllib.parse import parse_qs, urlencode, urlparse

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
_ALLOWED_HOSTS = {"apply.careers.microsoft.com", "hp.eightfold.ai", "careers.qualcomm.com"}
_JOB_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")
_DOMAIN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.-]{0,252}[A-Za-z0-9]$")


def parse_eightfold_job_url(
    public_url: str, provider_config: Optional[Mapping[str, object]] = None
) -> Optional[Tuple[str, str, Optional[str]]]:
    """Derive (host, job_id, domain_param) from an Eightfold job URL.

    Examples:
        https://apply.careers.microsoft.com/careers/job/1970393557022260
        -> ("apply.careers.microsoft.com", "1970393557022260", None)
        https://hp.eightfold.ai/careers/job/43778054?domain=hp.com
        -> ("hp.eightfold.ai", "43778054", "hp.com")
    """
    if not public_url or not isinstance(public_url, str):
        return None

    try:
        parsed = urlparse(public_url)
    except Exception:
        return None

    host = parsed.hostname
    if parsed.scheme != "https" or host not in _ALLOWED_HOSTS or parsed.username or parsed.password:
        return None
    try:
        if parsed.port is not None:
            return None
    except ValueError:
        return None

    parts = parsed.path.strip("/").split("/")
    if len(parts) != 3 or parts[:2] != ["careers", "job"]:
        return None
    job_id = parts[2]

    if not _JOB_ID_RE.fullmatch(job_id):
        return None

    qs = parse_qs(parsed.query)
    domain = qs.get("domain", [None])[0]
    if domain is not None and not _DOMAIN_RE.fullmatch(domain):
        return None

    return host, job_id, domain


async def fetch_eightfold_detail(req: DetailRequest, client: httpx.AsyncClient) -> DetailResult:
    """Fetch job details from Eightfold's apply v2 API."""
    from job_radar.services.detail_extractor import clean_html_to_text, description_is_valid

    parsed = parse_eightfold_job_url(req.public_url, req.provider_config)
    if not parsed:
        return DetailResult.empty(ERR_INVALID_DETAIL_URL)

    host, job_id, domain = parsed
    api_url = f"https://{host}/api/apply/v2/jobs/{job_id}"
    if domain:
        api_url = f"{api_url}?{urlencode({'domain': domain})}"

    headers = {
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }

    try:
        resp = await client.get(api_url, headers=headers, follow_redirects=False)
    except httpx.HTTPError as exc:
        logger.info("Eightfold detail request failed for %s: %s", job_id, exc)
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

    raw_desc = data.get("job_description") or data.get("description") or ""
    if not raw_desc or not isinstance(raw_desc, str):
        return DetailResult.empty(ERR_DESCRIPTION_MISSING)

    description = clean_html_to_text(raw_desc)[:40000]
    if not description_is_valid(description, title=req.title):
        return DetailResult.empty(ERR_DESCRIPTION_INVALID)

    title = (data.get("name") or data.get("posting_name") or data.get("title") or "").strip() or None
    location = (data.get("location") or "").strip() or None
    department = (data.get("department") or data.get("business_unit") or "").strip() or None
    employment_type = (data.get("type") or "").strip() or None

    return DetailResult(
        description=description,
        location=location,
        department=department,
        employment_type=employment_type,
        title=title,
        source="eightfold_api",
    )
