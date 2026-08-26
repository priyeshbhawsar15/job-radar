"""Direct Talent500 API detail extraction and HTTP payload fetching."""

import html
import logging
import re
from typing import Optional
from urllib.parse import urlparse
import httpx

from job_radar.services.detail_contracts import (
    DetailRequest,
    DetailResult,
    ERR_INVALID_DETAIL_URL,
    ERR_HTTP_STATUS,
    ERR_INVALID_PAYLOAD,
    ERR_RECORD_NOT_FOUND,
    ERR_DESCRIPTION_MISSING,
    ERR_DESCRIPTION_INVALID,
)

logger = logging.getLogger(__name__)


def validate_talent500_url(public_url: str) -> Optional[str]:
    """Validate Talent500 canonical URL host and path, returning job slug if valid."""
    if not public_url or not isinstance(public_url, str):
        return None

    try:
        parsed = urlparse(public_url)
    except Exception:
        return None

    if parsed.scheme not in ("http", "https"):
        return None

    netloc = parsed.netloc.lower()
    if netloc not in ("talent500.com", "www.talent500.com", "prod-warmachine.talent500.co"):
        return None

    path_parts = [p for p in parsed.path.split("/") if p]
    if len(path_parts) >= 3 and path_parts[0] == "jobs":
        return path_parts[2]

    return None


def clean_html_to_text(html_str: str) -> str:
    """Clean HTML string into plain text lines."""
    if not html_str:
        return ""
    text = html.unescape(html_str)
    clean = re.sub(
        r'<(script|style|svg|iframe|noscript|nav|footer|header)\b[^>]*>[\s\S]*?</\1>',
        ' ',
        text,
        flags=re.IGNORECASE,
    )
    plain = re.sub(r'<[^>]+>', '\n', clean)
    lines = [l.strip() for l in plain.splitlines() if len(l.strip()) > 8]
    filtered = [
        l for l in lines
        if not any(x in l.lower() for x in [
            'cookie', 'gtag', 'datalayer', 'window.', 'self.', 'scrollrestoration',
            '--bprogress', 'privacy policy', 'terms of use', 'sign in', 'apply now',
            'all rights reserved', 'javascript:'
        ])
    ]
    return "\n\n".join(filtered)


async def fetch_talent500_detail(req: DetailRequest, client: httpx.AsyncClient) -> DetailResult:
    """Fetch job details directly from Talent500 public API endpoint."""
    from job_radar.services.detail_extractor import description_is_valid

    slug = validate_talent500_url(req.public_url)
    if not slug:
        return DetailResult.empty(ERR_INVALID_DETAIL_URL)

    api_url = f"https://prod-warmachine.talent500.co/api/jobs/{slug}/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
    }

    try:
        resp = await client.get(api_url, headers=headers)
    except Exception as e:
        logger.warning(f"Talent500 detail fetch network error for {slug}: {e}")
        return DetailResult.empty(ERR_HTTP_STATUS)

    if resp.status_code == 404:
        return DetailResult.empty(ERR_RECORD_NOT_FOUND)
    elif resp.status_code != 200:
        return DetailResult.empty(ERR_HTTP_STATUS)

    try:
        data = resp.json()
    except Exception as e:
        logger.warning(f"Talent500 detail JSON decode error for {slug}: {e}")
        return DetailResult.empty(ERR_INVALID_PAYLOAD)

    if not isinstance(data, dict):
        return DetailResult.empty(ERR_INVALID_PAYLOAD)

    raw_description = data.get("description")
    if not raw_description or not isinstance(raw_description, str):
        return DetailResult.empty(ERR_DESCRIPTION_MISSING)

    cleaned_desc = clean_html_to_text(raw_description)
    if not description_is_valid(cleaned_desc, title=req.title):
        return DetailResult.empty(ERR_DESCRIPTION_INVALID)

    title = (data.get("title") or data.get("title_alias_1") or "").strip() or None

    city = data.get("location")
    if isinstance(city, str) and city.strip():
        city = city.strip()
    else:
        city = None

    country_obj = data.get("country")
    if isinstance(country_obj, dict):
        country = (country_obj.get("name") or "").strip() or None
    elif isinstance(country_obj, str) and country_obj.strip():
        country = country_obj.strip()
    else:
        country = None

    if city and country:
        if country.lower() in city.lower():
            location_str: Optional[str] = city
        else:
            location_str = f"{city}, {country}"
    elif city:
        location_str = city
    elif country:
        location_str = country
    else:
        location_str = None

    emp_type = data.get("employment_type")
    if emp_type and str(emp_type).strip():
        emp_type = str(emp_type).strip()
    else:
        emp_type = None

    dept = data.get("category") or data.get("role_category") or data.get("job_function") or data.get("job_sub_category")
    if isinstance(dept, dict):
        dept = dept.get("name")
    if dept and str(dept).strip():
        dept = str(dept).strip()
    else:
        dept = None

    return DetailResult(
        description=cleaned_desc,
        location=location_str,
        employment_type=emp_type,
        department=dept,
        source="talent500_api",
        title=title,
    )
