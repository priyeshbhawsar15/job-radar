"""Direct Workday CXS detail extraction and HTTP payload fetching.

Standardizes every Workday-family board onto the first-party CXS detail REST
endpoint shape:

    GET https://{tenant}.{domain}/wday/cxs/{tenant}/{site}/job/{path}

Extracts jobPostingInfo.jobDescription / title / location / jobReqId.
"""

import html
import re
from typing import Any, Mapping, Optional, Tuple
from urllib.parse import urlparse

import httpx

from job_radar.services.detail_contracts import (
    DetailRequest,
    DetailResult,
    ERR_INVALID_DETAIL_URL,
    ERR_HTTP_STATUS,
    ERR_RESPONSE_TOO_LARGE,
    ERR_INVALID_PAYLOAD,
    ERR_DESCRIPTION_MISSING,
    ERR_DESCRIPTION_INVALID,
)


def parse_workday_cxs_url(url: str) -> Optional[Tuple[str, str, str]]:
    """Derive (tenant, site, path) from a canonical Workday job URL.

    Example:
        https://jiostar.wd102.myworkdayjobs.com/en-US/JioStar/job/Bengaluru/Software-Development-Engineer-II--Web----VX_JR10213
        -> ("jiostar", "JioStar", "Bengaluru/Software-Development-Engineer-II--Web----VX_JR10213")
    """
    if not url or not isinstance(url, str):
        return None

    parsed = urlparse(url)
    host = parsed.netloc
    if not host or "myworkdayjobs.com" not in host.lower():
        return None

    tenant = host.split(".")[0]
    if not tenant:
        return None

    path_parts = [p for p in parsed.path.split("/") if p]
    job_idx = None
    for idx, part in enumerate(path_parts):
        if part.lower() == "job":
            job_idx = idx
            break
    if job_idx is None or job_idx == 0:
        return None

    site = path_parts[job_idx - 1]
    job_path_parts = path_parts[job_idx + 1:]
    if not site or not job_path_parts:
        return None

    return tenant, site, "/".join(job_path_parts)


def build_cxs_detail_url(url: str) -> Optional[str]:
    """Build the exact CXS detail endpoint URL for a canonical Workday job URL."""
    parsed_input = urlparse(url)
    host = parsed_input.netloc
    parsed = parse_workday_cxs_url(url)
    if not parsed or not host:
        return None
    tenant, site, path = parsed
    return f"{parsed_input.scheme}://{host}/wday/cxs/{tenant}/{site}/job/{path}"


_BLOCK_TAG_RE = re.compile(r"</?(?:p|div|li|br|h[1-6])\b[^>]*>", re.IGNORECASE)
_LIST_ITEM_RE = re.compile(r"<li\b[^>]*>", re.IGNORECASE)
_TAG_RE = re.compile(r"<[^>]+>")


def clean_workday_html(raw_html_str: Optional[str]) -> str:
    """Convert Workday CXS jobDescription HTML into cleanly formatted text.

    <p>, <br> become paragraph/line boundaries; <li> becomes a bullet prefix;
    all other tags are stripped while preserving paragraph/bullet structure.
    """
    if not raw_html_str or not isinstance(raw_html_str, str):
        return ""

    text = html.unescape(raw_html_str)
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", text, flags=re.DOTALL | re.IGNORECASE)

    # Workday often wraps <li> content in a nested <p>; strip that wrapper so the
    # bullet marker stays attached to its text instead of becoming its own paragraph.
    text = re.sub(r"(<li\b[^>]*>)\s*<p\b[^>]*>", r"\1", text, flags=re.IGNORECASE)
    text = re.sub(r"</p>\s*(</li>)", r"\1", text, flags=re.IGNORECASE)

    # Turn each <li>...</li> into a single bulleted line before generic tag stripping.
    def _bulletize(match: re.Match) -> str:
        return "\n• " + match.group(0)

    text = _LIST_ITEM_RE.sub(_bulletize, text)
    text = re.sub(r"</li>", "", text, flags=re.IGNORECASE)
    text = _LIST_ITEM_RE.sub("", text)

    # Paragraph/line-break boundaries.
    text = re.sub(r"</p>|<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<p\b[^>]*>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</?(?:ul|ol)\b[^>]*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</?div\b[^>]*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</?h[1-6]\b[^>]*>", "\n\n", text, flags=re.IGNORECASE)

    # Strip any remaining tags (b/strong/em/span/a/etc.) without adding boundaries.
    text = _TAG_RE.sub("", text)
    text = html.unescape(text)
    text = text.replace("\xa0", " ")

    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    paragraphs = []
    current = []
    for line in lines:
        if not line:
            if current:
                paragraphs.append(" ".join(current))
                current = []
            continue
        if line.startswith("•"):
            if current:
                paragraphs.append(" ".join(current))
                current = []
            paragraphs.append(line)
        else:
            current.append(line)
    if current:
        paragraphs.append(" ".join(current))

    return "\n\n".join(p for p in paragraphs if p)


def validate_detail_content(description: Optional[str]) -> Optional[str]:
    """Return a typed error code if description is missing/invalid, else None."""
    if description is None:
        return ERR_DESCRIPTION_MISSING
    cleaned = description.strip()
    if not cleaned:
        return ERR_DESCRIPTION_MISSING
    if len(cleaned) < 50:
        return ERR_DESCRIPTION_INVALID
    return None


def extract_workday_location(job_posting_info: Mapping[str, Any]) -> Optional[str]:
    location = job_posting_info.get("location")
    if isinstance(location, str) and location.strip():
        return location.strip()

    req_location = job_posting_info.get("jobRequisitionLocation")
    if isinstance(req_location, dict):
        descriptor = req_location.get("descriptor")
        if isinstance(descriptor, str) and descriptor.strip():
            return descriptor.strip()

    locations = job_posting_info.get("locationsText") or job_posting_info.get("additionalLocationsText")
    if isinstance(locations, str) and locations.strip():
        return locations.strip()

    return None


async def fetch_workday_detail(request: DetailRequest, client: httpx.AsyncClient) -> DetailResult:
    cxs_url = build_cxs_detail_url(request.public_url)
    if not cxs_url:
        return DetailResult.empty(ERR_INVALID_DETAIL_URL)

    headers = {
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }

    try:
        resp = await client.get(cxs_url, headers=headers)
    except httpx.HTTPError:
        return DetailResult.empty(ERR_HTTP_STATUS)

    if resp.status_code != 200:
        return DetailResult.empty(ERR_HTTP_STATUS)

    if len(resp.content) > 5 * 1024 * 1024:
        return DetailResult.empty(ERR_RESPONSE_TOO_LARGE)

    try:
        data = resp.json()
    except Exception:
        return DetailResult.empty(ERR_INVALID_PAYLOAD)

    if not isinstance(data, dict):
        return DetailResult.empty(ERR_INVALID_PAYLOAD)

    job_posting_info = data.get("jobPostingInfo")
    if not isinstance(job_posting_info, dict):
        return DetailResult.empty(ERR_INVALID_PAYLOAD)

    raw_description = job_posting_info.get("jobDescription")
    description = clean_workday_html(raw_description)
    if len(description) > 40_000:
        description = description[:40_000].strip()

    error_code = validate_detail_content(description)
    if error_code:
        return DetailResult.empty(error_code)

    raw_title = job_posting_info.get("title")
    detail_title = raw_title.strip() if isinstance(raw_title, str) and raw_title.strip() else None

    location = extract_workday_location(job_posting_info)

    return DetailResult(
        description=description,
        location=location,
        title=detail_title,
        source="workday_cxs_detail",
    )
