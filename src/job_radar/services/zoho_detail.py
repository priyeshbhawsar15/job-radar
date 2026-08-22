"""Zoho Recruit ("cw-*" career site widget) detail extraction.

Zoho Recruit career sites (e.g. Wynploy) render job detail pages via a
client-side widget. Once hydrated, the DOM contains:

    div.cw-summary        - key/value job metadata (Date Opened, City, ...)
    div.cw-jobdescription - full job description HTML

This module extracts both from already-rendered HTML (fetched via a
Playwright browser client that waited for `div.cw-jobdescription` to
appear) and validates the resulting description via `validate_detail_content`.
"""

import html
import re
from typing import Dict, Optional

from job_radar.services.detail_contracts import DetailResult
from job_radar.services.workday_detail import validate_detail_content

_SCRIPT_STYLE_RE = re.compile(r"<(script|style)\b[^>]*>.*?</\1>", re.DOTALL | re.IGNORECASE)
_CDN_PATH_VAR_RE = re.compile(r"var\s+cdnPathForStaticFiles\s*=.*?;", re.IGNORECASE)
_BLOCK_TAG_RE = re.compile(r"</?(?:p|div|h[1-6])\b[^>]*>", re.IGNORECASE)
_LIST_ITEM_RE = re.compile(r"<li\b[^>]*>", re.IGNORECASE)
_TAG_RE = re.compile(r"<[^>]+>")


def _strip_script_and_style(raw_html_str: str) -> str:
    """Remove inline <script>/<style> blocks and any stray cdnPathForStaticFiles JS."""
    text = _SCRIPT_STYLE_RE.sub(" ", raw_html_str)
    text = _CDN_PATH_VAR_RE.sub(" ", text)
    return text


def _find_balanced_div(raw_html_str: str, class_name: str) -> Optional[str]:
    """Return the full outer HTML of the first `<div class="{class_name}...">` block,
    matching nested divs by depth so unrelated trailing markup isn't captured."""
    open_re = re.compile(
        r'<div\b[^>]*\bclass=["\'][^"\']*\b' + re.escape(class_name) + r'\b[^"\']*["\'][^>]*>',
        re.IGNORECASE,
    )
    match = open_re.search(raw_html_str)
    if not match:
        return None

    tag_re = re.compile(r"<div\b|</div>", re.IGNORECASE)
    pos = match.end()
    depth = 1
    while depth > 0:
        tag_match = tag_re.search(raw_html_str, pos)
        if not tag_match:
            return None
        if tag_match.group(0).lower().startswith("<div"):
            depth += 1
        else:
            depth -= 1
        pos = tag_match.end()

    return raw_html_str[match.start():pos]


def clean_zoho_description_html(raw_html_str: Optional[str]) -> str:
    """Convert cw-jobdescription inner HTML into clean, boundary-preserving text."""
    if not raw_html_str or not isinstance(raw_html_str, str):
        return ""

    text = _strip_script_and_style(raw_html_str)
    text = html.unescape(text)

    # Zoho often wraps <li> content in a nested <p>; strip that wrapper so the
    # bullet marker stays attached to its text instead of becoming its own paragraph.
    text = re.sub(r"(<li\b[^>]*>)\s*<p\b[^>]*>", r"\1", text, flags=re.IGNORECASE)
    text = re.sub(r"</p>\s*(</li>)", r"\1", text, flags=re.IGNORECASE)

    def _bulletize(m: re.Match) -> str:
        return "\n• " + m.group(0)

    text = _LIST_ITEM_RE.sub(_bulletize, text)
    text = re.sub(r"</li>", "", text, flags=re.IGNORECASE)
    text = _LIST_ITEM_RE.sub("", text)

    text = re.sub(r"</p>|<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<p\b[^>]*>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</?(?:ul|ol)\b[^>]*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</?div\b[^>]*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</?h[1-6]\b[^>]*>", "\n\n", text, flags=re.IGNORECASE)

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


def extract_zoho_summary_fields(raw_html_str: str) -> Dict[str, str]:
    """Extract key/value pairs from div.cw-summary (e.g. City, Date Opened)."""
    summary_html = _find_balanced_div(raw_html_str, "cw-summary")
    if not summary_html:
        return {}

    summary_html = _strip_script_and_style(summary_html)

    fields: Dict[str, str] = {}
    for li_match in re.finditer(r"<li\b[^>]*>(.*?)</li>", summary_html, re.DOTALL | re.IGNORECASE):
        li_inner = li_match.group(1)
        spans = re.findall(r"<span\b[^>]*>(.*?)</span>", li_inner, re.DOTALL | re.IGNORECASE)
        if len(spans) < 2:
            continue
        key = html.unescape(_TAG_RE.sub("", spans[0])).strip()
        value = html.unescape(_TAG_RE.sub("", spans[1])).strip()
        if key and value:
            fields[key] = value

    return fields


def extract_zoho_city(summary_fields: Dict[str, str]) -> Optional[str]:
    for key in ("City", "Location", "Job Location"):
        if key in summary_fields and summary_fields[key].strip():
            return summary_fields[key].strip()
    return None


def extract_zoho_date_opened(summary_fields: Dict[str, str]) -> Optional[str]:
    for key in ("Date Opened", "Posted Date", "Job Opening Date"):
        if key in summary_fields and summary_fields[key].strip():
            return summary_fields[key].strip()
    return None


def fetch_zoho_detail_from_html(raw_html: str, url: str) -> DetailResult:
    """Parse already browser-rendered Zoho Recruit detail HTML into a DetailResult.

    Requires `div.cw-jobdescription` to be present (i.e. hydration completed
    before this HTML was captured) and the resulting description to pass
    `validate_detail_content`.
    """
    if not raw_html or not isinstance(raw_html, str):
        return DetailResult.empty("description_missing")

    description_html = _find_balanced_div(raw_html, "cw-jobdescription")
    if description_html is None:
        return DetailResult.empty("description_missing")

    description = clean_zoho_description_html(description_html)
    if len(description) > 40_000:
        description = description[:40_000].strip()

    error_code = validate_detail_content(description)
    if error_code:
        return DetailResult.empty(error_code)

    summary_fields = extract_zoho_summary_fields(raw_html)
    city = extract_zoho_city(summary_fields)

    return DetailResult(
        description=description,
        location=city,
        source="zoho_rendered_detail",
    )
