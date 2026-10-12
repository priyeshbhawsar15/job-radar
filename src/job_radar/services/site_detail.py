"""Strict public page contracts for Amazon and Novartis detail pages."""

from html import unescape
from html.parser import HTMLParser
import re
from urllib.parse import urlparse

import httpx

from job_radar.services.detail_contracts import (
    DetailRequest, DetailResult, ERR_DESCRIPTION_INVALID, ERR_DESCRIPTION_MISSING,
    ERR_HTTP_STATUS, ERR_IDENTITY_MISMATCH, ERR_INVALID_DETAIL_URL, ERR_INVALID_PAYLOAD, ERR_RESPONSE_TOO_LARGE,
)

_AMAZON_PATH = re.compile(r"^/en/jobs/(\d+)(?:/[^/?]+)?/?$", re.I)
_NOVARTIS_PATH = re.compile(r"^/in-en/careers/career-search/job/details/req-(\d+)-[^/?]+/?$", re.I)


class Node:
    def __init__(self, tag="", attrs=()):
        self.tag = tag
        self.attrs = dict(attrs)
        self.children = []

    def descendants(self):
        for child in self.children:
            if isinstance(child, Node):
                yield child
                yield from child.descendants()

    def text(self):
        parts = []
        for child in self.children:
            if isinstance(child, str):
                parts.append(child)
            elif child.tag in {"script", "style", "svg", "noscript"}:
                continue
            else:
                content = child.text()
                if child.tag == "li":
                    parts.append("\n• " + content + "\n")
                elif child.tag in {"p", "div", "h1", "h2", "h3", "h4", "br", "ul", "ol"}:
                    parts.append("\n" + content + "\n")
                else:
                    parts.append(content)
        raw = unescape("".join(parts)).replace("\xa0", " ")
        return "\n".join(re.sub(r"[ \t]+", " ", line).strip() for line in raw.splitlines() if line.strip())


class Document(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node()
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs)
        self.stack[-1].children.append(node)
        if tag not in {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}:
            self.stack.append(node)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def _class(node, name):
    return name in node.attrs.get("class", "").split()


def parse_amazon_detail(raw_html: str, public_url: str) -> DetailResult:
    from job_radar.services.detail_extractor import description_is_valid

    url = urlparse(public_url)
    match = _AMAZON_PATH.fullmatch(url.path)
    if url.scheme != "https" or url.hostname != "www.amazon.jobs" or url.username or url.password or url.port or not match:
        return DetailResult.empty(ERR_INVALID_DETAIL_URL)
    title_match = re.search(r"<title>(.*?) - Job ID: (\d+) \| Amazon\.jobs</title>", raw_html, re.I | re.S)
    if not title_match or title_match.group(2) != match.group(1):
        return DetailResult.empty(ERR_INVALID_PAYLOAD)
    doc = Document()
    doc.feed(raw_html)
    sections = []
    for node in doc.root.descendants():
        if node.tag != "div" or not _class(node, "section"):
            continue
        headings = [child for child in node.children if isinstance(child, Node) and child.tag == "h2"]
        if not headings:
            continue
        heading = headings[0].text().strip()
        if heading in {"Description", "Basic Qualifications", "Preferred Qualifications"}:
            content = node.text()
            if heading == "Description":
                content = re.sub(r"(?i)\bKey job responsibilities\b", "\nResponsibilities\nKey job responsibilities", content, count=1)
            sections.append((heading, content))
    if not sections:
        return DetailResult.empty(ERR_DESCRIPTION_MISSING)
    if not any(h == "Description" for h, _ in sections):
        return DetailResult.empty(ERR_DESCRIPTION_INVALID)
    description = "\n\n".join(text for _, text in sections)[:40000]
    if not description_is_valid(description):
        return DetailResult.empty(ERR_DESCRIPTION_INVALID)
    return DetailResult(description=description, title=unescape(title_match.group(1)).strip(), source="amazon_sections")


def parse_novartis_detail(raw_html: str, public_url: str) -> DetailResult:
    from job_radar.services.detail_extractor import description_is_valid

    url = urlparse(public_url)
    match = _NOVARTIS_PATH.fullmatch(url.path)
    if url.scheme != "https" or url.hostname != "www.novartis.com" or url.username or url.password or url.port or not match:
        return DetailResult.empty(ERR_INVALID_DETAIL_URL)
    title_match = re.search(r"<title>(.*?) \| Novartis India</title>", raw_html, re.I | re.S)
    if not title_match:
        return DetailResult.empty(ERR_INVALID_PAYLOAD)
    doc = Document()
    doc.feed(raw_html)
    # Bind identity and body to the same observed job article. Navigation,
    # comments, scripts or a footer containing the requested id are not proof.
    articles = [node for node in doc.root.descendants()
                if node.tag == "article" and _class(node, "node--type-jobs")]
    if len(articles) != 1:
        return DetailResult.empty(ERR_IDENTITY_MISMATCH)
    nodes = list(articles[0].descendants())
    id_fields = [node for node in nodes if _class(node, "field_job_id")]
    if not id_fields or any(
            re.findall(r"\bREQ-(\d+)\b", node.text(), re.I) != [match.group(1)]
            for node in id_fields):
        return DetailResult.empty(ERR_IDENTITY_MISMATCH)
    title = unescape(title_match.group(1)).strip()
    article_titles = [node.text().strip() for node in nodes if _class(node, "field_job_title")]
    normalized_title = " ".join(title.split()).casefold()
    if not article_titles or any(" ".join(value.split()).casefold() != normalized_title for value in article_titles):
        return DetailResult.empty(ERR_IDENTITY_MISMATCH)
    bodies = [node for node in nodes if node.tag == "div" and _class(node, "job_description")]
    if not bodies or len(bodies) > 3:
        return DetailResult.empty(ERR_DESCRIPTION_MISSING)
    description = "\n\n".join(body.text() for body in bodies)[:40000]
    if not description_is_valid(description):
        return DetailResult.empty(ERR_DESCRIPTION_INVALID)
    def field_values(class_name):
        values = []
        for node in nodes:
            if not _class(node, class_name):
                continue
            lines = node.text().splitlines()
            if lines and lines[0] in {"Site", "Location", "Country"}:
                lines = lines[1:]
            value = ", ".join(lines).strip()
            if value and value not in values:
                values.append(value)
        return values

    sites = field_values("field_job_work_location")
    countries = field_values("field_job_country")
    location = ", ".join(dict.fromkeys(sites + countries))[:200] or None
    return DetailResult(description=description, title=title, location=location, source="novartis_visible_body")


async def fetch_site_detail(req: DetailRequest, client: httpx.AsyncClient) -> DetailResult:
    url = urlparse(req.public_url)
    amazon = url.hostname == "www.amazon.jobs" and _AMAZON_PATH.fullmatch(url.path)
    novartis = url.hostname == "www.novartis.com" and _NOVARTIS_PATH.fullmatch(url.path)
    if url.scheme != "https" or url.username or url.password or url.port or not (amazon or novartis):
        return DetailResult.empty(ERR_INVALID_DETAIL_URL)
    try:
        response = await client.get(req.public_url, follow_redirects=False, timeout=15.0)
        if amazon and response.status_code in {301, 302}:
            location = response.headers.get("location", "")
            target = urlparse(location)
            target_match = _AMAZON_PATH.fullmatch(target.path)
            if target.scheme != "https" or target.hostname != "www.amazon.jobs" or not target_match or target_match.group(1) != _AMAZON_PATH.fullmatch(url.path).group(1) or target.username or target.password or target.port:
                return DetailResult.empty(ERR_INVALID_DETAIL_URL)
            response = await client.get(location, follow_redirects=False, timeout=15.0)
    except httpx.HTTPError:
        return DetailResult.empty(ERR_HTTP_STATUS)
    if response.status_code != 200:
        return DetailResult.empty(ERR_HTTP_STATUS)
    if len(response.content) > 1_000_000:
        return DetailResult.empty(ERR_RESPONSE_TOO_LARGE)
    return parse_amazon_detail(response.text, req.public_url) if amazon else parse_novartis_detail(response.text, req.public_url)
