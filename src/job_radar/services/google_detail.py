"""Deterministic extraction of the rendered Google Careers detail panel."""

from html import unescape
import re
from urllib.parse import urlparse

import httpx

from job_radar.services.detail_contracts import (
    DetailRequest, DetailResult, ERR_DESCRIPTION_INVALID, ERR_DESCRIPTION_MISSING,
    ERR_HTTP_STATUS, ERR_INVALID_DETAIL_URL, ERR_INVALID_PAYLOAD, ERR_RESPONSE_TOO_LARGE,
)
from job_radar.services.site_detail import Document, Node, _class

_PATH = re.compile(r"^/about/careers/applications/jobs/results/(\d{12,20})-[^/?]+/?$")


def parse_google_detail(raw_html: str, public_url: str) -> DetailResult:
    from job_radar.services.detail_extractor import description_is_valid

    url = urlparse(public_url)
    match = _PATH.fullmatch(url.path)
    if url.scheme != "https" or url.hostname != "www.google.com" or url.username or url.password or url.port or not match:
        return DetailResult.empty(ERR_INVALID_DETAIL_URL)
    canonical = re.search(r'<link\s+rel="canonical"\s+href="([^"]+)"', raw_html, re.I)
    if not canonical or urlparse(unescape(canonical.group(1))).path != url.path:
        return DetailResult.empty(ERR_INVALID_PAYLOAD)
    title_match = re.search(r"<title>(.*?) — Google Careers</title>", raw_html, re.I | re.S)
    if not title_match:
        return DetailResult.empty(ERR_INVALID_PAYLOAD)
    doc = Document()
    doc.feed(raw_html)
    panels = {}
    for node in doc.root.descendants():
        if node.tag != "div":
            continue
        for cls in ("KwJkGe", "aG5W3", "BDNOWe"):
            if _class(node, cls):
                panels.setdefault(cls, []).append(node)
    if any(len(panels.get(cls, [])) != 1 for cls in ("KwJkGe", "aG5W3", "BDNOWe")):
        return DetailResult.empty(ERR_DESCRIPTION_MISSING)
    sections = []
    for cls in ("KwJkGe", "aG5W3", "BDNOWe"):
        panel = panels[cls][0]
        for child in panel.children:
            if isinstance(child, Node) and child.tag == "h3":
                heading = child.text().strip().rstrip(":")
                if heading in {"Minimum qualifications", "Preferred qualifications", "About the job", "Responsibilities"}:
                    sections.append(heading)
            elif isinstance(child, Node) and child.tag in {"ul", "p", "div"} and not (cls == "KwJkGe" and child.tag == "div"):
                text = child.text().strip()
                if text:
                    sections.append(text)
    description = "\n\n".join(sections)[:40000]
    if not all(heading in description for heading in ("Minimum qualifications", "Preferred qualifications", "About the job", "Responsibilities")):
        return DetailResult.empty(ERR_DESCRIPTION_INVALID)
    if not description_is_valid(description):
        return DetailResult.empty(ERR_DESCRIPTION_INVALID)
    headers = [node for node in doc.root.descendants() if node.tag == "div" and _class(node, "op1BBf")]
    location = None
    if len(headers) == 1:
        locations = [node.text().strip(" ;") for node in headers[0].descendants() if node.tag == "span" and _class(node, "r0wTof")]
        location = "; ".join(loc for loc in locations if loc)[:200] or None
    return DetailResult(description=description, title=unescape(title_match.group(1)).strip(), location=location, source="google_detail_panel")


async def fetch_google_detail(req: DetailRequest, client: httpx.AsyncClient) -> DetailResult:
    url = urlparse(req.public_url)
    if url.scheme != "https" or url.hostname != "www.google.com" or url.username or url.password or url.port or not _PATH.fullmatch(url.path):
        return DetailResult.empty(ERR_INVALID_DETAIL_URL)
    try:
        response = await client.get(req.public_url, follow_redirects=False, timeout=15.0)
    except httpx.HTTPError:
        return DetailResult.empty(ERR_HTTP_STATUS)
    if response.status_code != 200:
        return DetailResult.empty(ERR_HTTP_STATUS)
    if len(response.content) > 2_000_000:
        return DetailResult.empty(ERR_RESPONSE_TOO_LARGE)
    return parse_google_detail(response.text, req.public_url)
