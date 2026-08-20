import asyncio
import logging
import json
import re
import html
import urllib.parse
import httpx
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from job_radar.db.session import AsyncSessionLocal
from job_radar.db.models.board import Board, BoardRevision
from job_radar.db.models.run import PipelineRun, BoardRun, RunRequest, ExecutionAttempt
from job_radar.adapters.registry import adapter_registry
from job_radar.adapters.base import ExtractedCandidate
from job_radar.adapters.families import generate_fingerprint, canonicalize_job_url
from job_radar.services.browser import BrowserServiceClient, TargetBoundaryViolation
from job_radar.services.normalization import normalization_service

logger = logging.getLogger(__name__)

def oracle_clean_description(text: str) -> str:
    if not text:
        return ""
    t = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.I)
    t = re.sub(r'@keyframes[^{]+\{[^}]+\}', '', t)
    t = html.unescape(t)
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    bad_markers = [
        "page not found. - oracle careers",
        "hashbang_regex",
        "candidate experience page",
    ]
    if any(m in t.lower() for m in bad_markers):
        return ""
    return t[:40000]

def oracle_meta_fallback(html_text: str) -> str:
    if not html_text:
        return ""
    m = re.search(r'<meta\s+property="og:description"\s+content="([^"]*)"', html_text, re.I)
    if m:
        return html.unescape(m.group(1)).strip()[:40000]
    return ""

def clean_amazon_html(raw_html: str) -> str:
    if not raw_html:
        return ''
    text = html.unescape(raw_html)
    text = re.sub(r'</?(p|div|li|h[1-6]|br|tr|td)[^>]*>', '\n', text, flags=re.I)
    text = re.sub(r'<[^>]+>', '', text)
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    filtered = []
    for l in lines:
        l_lower = l.lower()
        if any(x in l_lower for x in ['equal opportunity employer', 'disability/veteran', 'pay transparency', 'affirmative action']):
            continue
        filtered.append(l)
    return '\n\n'.join(filtered)

class PipelineExecutionEngine:
    """Stateful engine for executing board parsing runs with multi-page pagination & threshold rules."""

    def __init__(self, session_factory=AsyncSessionLocal):
        self.session_factory = session_factory
        self.browser_client = BrowserServiceClient()

    async def fetch_rbctech_candidates(
        self,
        target_url: str,
        board_name: str
    ) -> List[ExtractedCandidate]:
        """Fetch RBCTech job postings directly from Stratsy public API."""
        api_url = "https://aligncrm.stratsy.us/api/public/opportunities"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        all_candidates: List[ExtractedCandidate] = []
        seen_urls = set()

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(api_url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                items = data.get("data", [])
                for item in items:
                    title = str(item.get("title") or "").strip()
                    job_id = str(item.get("id") or "")
                    loc = str(item.get("location") or "India").strip()
                    emp = str(item.get("opportunityType") or "Full-time").replace("_", "-").title()
                    desc = str(item.get("description") or "").strip()

                    full_u = f"https://aligncrm.stratsy.us/public/opportunities?board=RBC%20Technologies&id={job_id}"
                    clean_u = canonicalize_job_url(full_u, board_name, target_url)
                    if not clean_u or clean_u in seen_urls:
                        continue
                    seen_urls.add(clean_u)

                    fp = generate_fingerprint(board_name, f"{title} {job_id}", loc)
                    all_candidates.append(
                        ExtractedCandidate(
                            title=title,
                            company=board_name,
                            location=loc,
                            department="Engineering",
                            employment_type=emp,
                            raw_url=clean_u,
                            fingerprint=fp,
                            extra_payload={"description": desc[:40000]}
                        )
                    )

        return all_candidates

    async def fetch_lever_candidates(
        self,
        target_url: str,
        board_name: str
    ) -> List[ExtractedCandidate]:
        """Fetch Lever job postings directly from Lever's JSON API."""
        parsed = urllib.parse.urlparse(target_url)
        slug = parsed.path.strip("/").split("/")[0]
        if not slug or slug == "v0":
            slug = parsed.path.split("/postings/")[-1].split("?")[0]

        api_url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        all_candidates: List[ExtractedCandidate] = []
        seen_urls = set()

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(api_url, headers=headers)
            if resp.status_code == 200:
                jobs = resp.json()
                for j in jobs:
                    cats = j.get("categories", {})
                    loc_str = str(cats.get("location", ""))
                    country_str = str(cats.get("country", ""))
                    text_str = str(j.get("text", ""))
                    
                    full_loc = f"{loc_str} {country_str} {text_str}"
                    if "india" not in full_loc.lower():
                        continue

                    raw_u = j.get("hostedUrl") or j.get("applyUrl")
                    clean_u = canonicalize_job_url(raw_u, board_name, target_url)
                    if not clean_u or clean_u in seen_urls:
                        continue
                    seen_urls.add(clean_u)

                    title = j.get("text", "").strip()
                    job_id = j.get("id", "")
                    dept = cats.get("department", "Technology").strip()
                    emp = cats.get("commitment", "Full-time").strip()
                    desc_p = html.unescape(j.get("descriptionPlain", "") or j.get("description", ""))
                    add_p = html.unescape(j.get("additionalPlain", "") or j.get("additional", ""))
                    lists = j.get("lists", [])
                    list_parts = []
                    if isinstance(lists, list):
                        for lst in lists:
                            if isinstance(lst, dict):
                                h_t = lst.get("text", "")
                                c_h = lst.get("content", "")
                                c_t = re.sub(r'</?(p|li|ul|br|div)[^>]*>', '\n', c_h, flags=re.I)
                                c_t = re.sub(r'<[^>]+>', '', c_t)
                                c_c = '\n'.join([l.strip() for l in html.unescape(c_t).splitlines() if l.strip()])
                                if h_t or c_c:
                                    list_parts.append(f"=== {h_t.upper()} ===\n{c_c}")
                    full_lever_desc = f"{desc_p}\n\n" + "\n\n".join(list_parts) + f"\n\n{add_p}"
                    desc = full_lever_desc.strip()
                    fp = generate_fingerprint(board_name, f"{title} {job_id}", loc_str or "India")

                    all_candidates.append(
                        ExtractedCandidate(
                            title=title,
                            company=board_name,
                            location=loc_str or "India",
                            department=dept,
                            employment_type=emp,
                            raw_url=clean_u,
                            fingerprint=fp,
                            extra_payload={"description": desc[:40000]}
                        )
                    )

        return all_candidates

    async def fetch_celonis_candidates(
        self,
        target_url: str,
        board_name: str
    ) -> List[ExtractedCandidate]:
        """Fetch Celonis job postings directly from Celonis DXP API."""
        api_url = "https://dxp-api.celonis.com/v1/jobs?limit=100"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        all_candidates: List[ExtractedCandidate] = []
        seen_urls = set()

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(api_url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                jobs = data.get("jobs", []) or data.get("data", []) or []
                for j in jobs:
                    loc = str(j.get("location", "") or j.get("groupedLocation", ""))
                    team = str(j.get("team", "") or j.get("department", ""))
                    if "bangalore" not in loc.lower() and "india" not in loc.lower():
                        continue

                    job_id = j.get("jobId", "") or j.get("id", "")
                    raw_u = f"https://careers.celonis.com/join-us/open-positions/job-detail?jobId={job_id}"
                    clean_u = canonicalize_job_url(raw_u, board_name, target_url)
                    if clean_u in seen_urls:
                        continue
                    seen_urls.add(clean_u)

                    title = j.get("title", "").strip()
                    desc = j.get("description", "") or j.get("content", "")
                    fp = generate_fingerprint(board_name, f"{title} {job_id}", "Bangalore, India")

                    all_candidates.append(
                        ExtractedCandidate(
                            title=title,
                            company=board_name,
                            location="Bangalore, India",
                            department=team or "Engineering",
                            employment_type="Full-time",
                            raw_url=clean_u,
                            fingerprint=fp,
                            extra_payload={"description": str(desc)[:40000]}
                        )
                    )

        return all_candidates

    async def fetch_ashby_candidates(
        self,
        target_url: str,
        board_name: str
    ) -> List[ExtractedCandidate]:
        """Fetch Ashby job postings directly from Ashby's public API."""
        parsed = urllib.parse.urlparse(target_url)
        org_slug = parsed.path.strip('/').split('/')[0]
        api_url = f"https://api.ashbyhq.com/posting-api/job-board/{org_slug}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

        all_candidates: List[ExtractedCandidate] = []
        seen_urls = set()

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(api_url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                jobs = data.get("jobs", [])
                for j in jobs:
                    raw_u = j.get("jobUrl") or f"https://jobs.ashbyhq.com/{org_slug}/{j.get('id')}"
                    clean_u = canonicalize_job_url(raw_u, board_name, target_url)
                    if clean_u in seen_urls:
                        continue
                    seen_urls.add(clean_u)

                    title = j.get("title", "").strip()
                    loc = j.get("location", "India").strip()
                    dept = j.get("department", "Technology").strip()
                    emp = j.get("employmentType", "Full-time").strip()
                    desc = j.get("descriptionPlain", "") or j.get("descriptionHtml", "")
                    fp = generate_fingerprint(board_name, f"{title} {j.get('id')}", loc)

                    all_candidates.append(
                        ExtractedCandidate(
                            title=title,
                            company=board_name,
                            location=loc,
                            department=dept,
                            employment_type=emp,
                            raw_url=clean_u,
                            fingerprint=fp,
                            extra_payload={"description": desc[:40000]}
                        )
                    )

        return all_candidates

    async def fetch_amazon_candidates_multipage(
        self,
        target_url: str,
        board_name: str,
        max_pages: int = 3,
        selector_config: Optional[Dict[str, Any]] = None
    ) -> List[ExtractedCandidate]:
        """Fetch Amazon job postings across multiple pages using Amazon Search JSON API."""
        base_api = "https://www.amazon.jobs/en/search.json?result_limit=10&sort=recent&category[]=software-development&distanceType=Mi&radius=24km&latitude=&longitude=&loc_group_id=&loc_query=India&base_query=software&city=&country=IND&region=&county=&query_options=|"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        all_candidates: List[ExtractedCandidate] = []
        seen_urls = set()

        async with httpx.AsyncClient(timeout=10.0) as client:
            for page in range(max_pages):
                offset = page * 10
                api_url = f"{base_api}&offset={offset}"
                try:
                    resp = await client.get(api_url, headers=headers)
                    if resp.status_code == 200:
                        data = resp.json()
                        jobs = data.get("jobs", [])
                        if not jobs:
                            break
                        for item in jobs:
                            title = item.get("title", "").strip()
                            job_id = item.get("id_icims", "") or item.get("id", "")
                            raw_url = f"https://www.amazon.jobs{item.get('job_path', '')}"
                            clean_url = canonicalize_job_url(raw_url, board_name, target_url)
                            if clean_url in seen_urls:
                                continue
                            seen_urls.add(clean_url)

                            desc_text = clean_amazon_html(item.get('description', ''))
                            basic_text = clean_amazon_html(item.get('basic_qualifications', ''))
                            pref_text = clean_amazon_html(item.get('preferred_qualifications', ''))

                            detail_desc = ""
                            try:
                                dr = await client.get(clean_url, headers=headers)
                                if dr.status_code == 200:
                                    m_og = re.search(r'<meta\s+property=["\x27]og:description["\x27]\s+content=["\x27]([^"\x27]*)["\x27]', dr.text, re.I)
                                    og_d = html.unescape(m_og.group(1)).strip() if m_og else ""
                                    m_b = re.search(r'<h2>Basic Qualifications</h2>\s*<p>(.*?)</p>', dr.text, re.DOTALL | re.I)
                                    b_q = ""
                                    if m_b:
                                        b_t = re.sub(r'</?(p|div|li|br)[^>]*>', '\n', m_b.group(1), flags=re.I)
                                        b_q = '\n'.join([l.strip() for l in html.unescape(re.sub(r'<[^>]+>', '', b_t)).splitlines() if l.strip()])
                                    m_p = re.search(r'<h2>Preferred Qualifications</h2>\s*<p>(.*?)</p>', dr.text, re.DOTALL | re.I)
                                    p_q = ""
                                    if m_p:
                                        p_t = re.sub(r'</?(p|div|li|br)[^>]*>', '\n', m_p.group(1), flags=re.I)
                                        p_q = '\n'.join([l.strip() for l in html.unescape(re.sub(r'<[^>]+>', '', p_t)).splitlines() if l.strip()])
                                    
                                    if og_d:
                                        detail_desc = f"{og_d}\n\n=== BASIC QUALIFICATIONS ===\n{b_q}\n\n=== PREFERRED QUALIFICATIONS ===\n{p_q}".strip()
                            except Exception:
                                pass

                            full_desc = detail_desc if detail_desc else (desc_text + chr(10) + chr(10) + "=== BASIC QUALIFICATIONS ===" + chr(10) + basic_text + chr(10) + chr(10) + "=== PREFERRED QUALIFICATIONS ===" + chr(10) + pref_text).strip()
                            loc_raw = item.get("location", "India")
                            if "BANGALORE" in loc_raw.upper() or "BENGALURU" in loc_raw.upper() or "KA" in loc_raw.upper():
                                loc = "Bangalore, India"
                            elif "HYDERABAD" in loc_raw.upper() or "TS" in loc_raw.upper():
                                loc = "Hyderabad, India"
                            elif "NOIDA" in loc_raw.upper() or "UP" in loc_raw.upper():
                                loc = "Noida, India"
                            elif "GURGAON" in loc_raw.upper() or "GURUGRAM" in loc_raw.upper() or "HR" in loc_raw.upper():
                                loc = "Gurgaon, India"
                            else:
                                loc = "India"

                            fp = generate_fingerprint(board_name, f"{title} {job_id}", loc)
                            all_candidates.append(
                                ExtractedCandidate(
                                    title=title,
                                    company=board_name,
                                    location=loc,
                                    department="Software Development",
                                    employment_type="Full-time",
                                    raw_url=clean_url,
                                    fingerprint=fp,
                                    extra_payload={"description": full_desc[:40000]}
                                )
                            )
                        total = data.get("hits", 0)
                        if offset + 10 >= total:
                            break
                    else:
                        break
                except Exception as e:
                    logger.info(f"Amazon pagination error page {page+1} for {board_name}: {e}")
                    break

        return all_candidates

    async def fetch_workday_candidates_multipage(
        self,
        target_url: str,
        board_name: str,
        max_pages: int = 3,
        selector_config: Optional[Dict[str, Any]] = None
    ) -> List[ExtractedCandidate]:
        """Fetch Workday job postings across multiple pages using Workday CXS API."""
        parsed_target = target_url.replace("https://", "").replace("http://", "")
        parts = parsed_target.split('/')
        domain = parts[0]
        tenant = domain.split('.')[0]
        site = "external_experienced"

        for idx, p in enumerate(parts[1:], 1):
            if p in ("en-US", "en_US") and idx + 1 < len(parts):
                site = parts[idx + 1].split('?')[0]
                break
            elif any(x in p.lower() for x in ["external", "career", "apply", "jobs"]):
                site = p.split('?')[0]
                break

        parsed_url = urllib.parse.urlparse(target_url)
        qs = urllib.parse.parse_qs(parsed_url.query)

        valid_facet_keys = {"workerSubType", "jobFamilyGroup", "timeType", "locationCountry", "locationHierarchy1", "locationRegion", "jobFamily"}
        facets = {k: v for k, v in qs.items() if k in valid_facet_keys}

        cxs_url = f"https://{domain}/wday/cxs/{tenant}/{site}/jobs"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        all_candidates: List[ExtractedCandidate] = []
        seen_urls = set()
        adapter = adapter_registry.get("workday")
        total_known: Optional[int] = None

        async with httpx.AsyncClient(timeout=10.0) as client:
            for page in range(max_pages):
                offset = page * 20
                payload = {"appliedFacets": facets, "limit": 20, "offset": offset, "searchText": ""}
                try:
                    resp = await client.post(cxs_url, json=payload, headers=headers)
                    if resp.status_code != 200 and "locationCountry" in facets:
                        fallback_facets = {k: v for k, v in facets.items() if k != "locationCountry"}
                        payload["appliedFacets"] = fallback_facets
                        resp = await client.post(cxs_url, json=payload, headers=headers)

                    if resp.status_code == 200:
                        page_payload = resp.text
                        page_cands = adapter.parse_raw_payload(
                            payload=page_payload,
                            board_name=board_name,
                            target_url=target_url,
                            selector_config=selector_config
                        )
                        if not page_cands:
                            break
                        for c in page_cands:
                            if c.raw_url not in seen_urls:
                                seen_urls.add(c.raw_url)
                                try:
                                    parsed_c = urllib.parse.urlparse(c.raw_url)
                                    path_segment = parsed_c.path
                                    if "/job/" in path_segment:
                                        rel_path = path_segment[path_segment.find("/job/"):]
                                        detail_endpoint = f"https://{domain}/wday/cxs/{tenant}/{site}{rel_path}"
                                        dr = await client.get(detail_endpoint, headers=headers)
                                        if dr.status_code == 200:
                                            d_info = dr.json().get("jobPostingInfo", {})
                                            raw_desc = d_info.get("jobDescription", "")
                                            if raw_desc:
                                                clean_desc = html.unescape(re.sub(r"<[^>]+>", " ", raw_desc)).strip()
                                                c.extra_payload = {"description": clean_desc[:40000]}
                                except Exception as de_err:
                                    logger.info(f"CXS detail fetch exception for {c.raw_url}: {de_err}")
                                all_candidates.append(c)

                        data = resp.json()
                        if data.get("total", 0) > 0:
                            total_known = data["total"]
                        if total_known is not None and total_known > 0 and offset + 20 >= total_known:
                            break
                    else:
                        break
                except Exception as e:
                    logger.info(f"Workday pagination error page {page+1} for {board_name}: {e}")
                    break

        if not all_candidates:
            raw_payload = await self.browser_client.fetch_board_html(target_url, target_url)
            all_candidates = adapter.parse_raw_payload(raw_payload, board_name, target_url, selector_config)

        return all_candidates

    async def execute_board_run(
        self,
        board_id: str,
        pipeline_id: Optional[str] = None
    ) -> BoardRun:
        """Execute a single board parsing run with state transition rules."""
        async with self.session_factory() as session:
            result = await session.execute(
                select(Board).where(Board.board_id == board_id)
            )
            board = result.scalar_one_or_none()
            if not board:
                raise ValueError(f"Board not found: {board_id}")

            if not pipeline_id:
                pipeline = PipelineRun(
                    trigger="manual",
                    status="running",
                    total_boards=1
                )
                session.add(pipeline)
                await session.commit()
                await session.refresh(pipeline)
                pipeline_id = pipeline.pipeline_id

            if board.status == "held":
                logger.warning(f"Board {board_id} is HELD due to consecutive failures. Skipping run.")
                board_run = BoardRun(
                    board_id=board_id,
                    pipeline_id=pipeline_id,
                    stage="completed",
                    outcome="held",
                    error_code="BOARD_HELD",
                    terminal_at=datetime.now(timezone.utc)
                )
                session.add(board_run)
                await session.commit()
                return board_run

            revision = None
            if board.current_revision_id:
                rev_res = await session.execute(
                    select(BoardRevision).where(BoardRevision.revision_id == board.current_revision_id)
                )
                revision = rev_res.scalar_one_or_none()

            target_url = "https://localhost"
            selector_config = None
            max_pages = 3
            family = board.family

            if revision and isinstance(revision.config_json, dict):
                target_url = revision.config_json.get("target_url", target_url)
                selector_config = revision.config_json.get("selector_config")
                max_pages = int(revision.config_json.get("max_pages", 3))
                family = revision.config_json.get("family", family)

            board_run = BoardRun(
                board_id=board_id,
                pipeline_id=pipeline_id,
                revision_id=revision.revision_id if revision else None,
                stage="running",
                outcome="in_progress"
            )
            session.add(board_run)
            await session.commit()
            await session.refresh(board_run)

            run_req = RunRequest(
                board_id=board_id,
                origin="manual",
                status="admitted"
            )
            session.add(run_req)
            await session.commit()
            await session.refresh(run_req)

            adapter = adapter_registry.get(family)
            if not adapter:
                board_run.stage = "completed"
                board_run.outcome = "parser_contract"
                board_run.error_code = f"UNSUPPORTED_ADAPTER_{family}"
                board_run.terminal_at = datetime.now(timezone.utc)
                board.consecutive_parser_failures += 1
                if board.consecutive_parser_failures >= 3:
                    board.status = "held"
                await session.commit()
                return board_run

            max_attempts = 2
            run_success = False
            run_partial = False
            error_msg: Optional[str] = None
            extracted_candidates = []

            for attempt_num in range(1, max_attempts + 1):
                attempt_rec = ExecutionAttempt(
                    request_id=run_req.request_id,
                    stage="running"
                )
                session.add(attempt_rec)
                await session.commit()

                try:
                    if family == "workday":
                        extracted_candidates = await self.fetch_workday_candidates_multipage(
                            target_url=target_url,
                            board_name=board.name,
                            max_pages=max_pages,
                            selector_config=selector_config
                        )
                    elif family == "amazon_jobs":
                        extracted_candidates = await self.fetch_amazon_candidates_multipage(
                            target_url=target_url,
                            board_name=board.name,
                            max_pages=max_pages,
                            selector_config=selector_config
                        )
                    elif family in ("ashby", "ashbyhq"):
                        extracted_candidates = await self.fetch_ashby_candidates(
                            target_url=target_url,
                            board_name=board.name
                        )
                    elif family in ("celonis", "celonis_dxp"):
                        extracted_candidates = await self.fetch_celonis_candidates(
                            target_url=target_url,
                            board_name=board.name
                        )
                    elif family == "lever":
                        extracted_candidates = await self.fetch_lever_candidates(
                            target_url=target_url,
                            board_name=board.name
                        )
                    elif family in ("stratsy", "stratsy_api"):
                        extracted_candidates = await self.fetch_rbctech_candidates(
                            target_url=target_url,
                            board_name=board.name
                        )
                    elif family == "apple_jobs":
                        raw_payload = await self.browser_client.fetch_board_html(
                            target_url=target_url,
                            registered_target_url=target_url
                        )
                        extracted_candidates = adapter.parse_raw_payload(
                            payload=raw_payload,
                            board_name=board.name,
                            target_url=target_url,
                            selector_config=selector_config
                        )
                        extracted_candidates = [c for c in extracted_candidates if "locationPicker" not in c.raw_url]
                        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True, verify=False, headers={"User-Agent": "Mozilla/5.0"}) as client:
                            for c in extracted_candidates:
                                try:
                                    dr = await client.get(c.raw_url)
                                    if dr.status_code == 200:
                                        m = re.search(r'window\.__staticRouterHydrationData\s*=\s*JSON\.parse\(("(?:[^"\\]|\\.)*")\)', dr.text)
                                        if m:
                                            raw_str = json.loads(m.group(1))
                                            data = json.loads(raw_str)
                                            loader = data.get("loaderData", {})
                                            jd_block = loader.get("jobDetails", {})
                                            jd = jd_block.get("jobsData", {})
                                            if jd:
                                                summary = html.unescape(re.sub(r'<[^>]+>', ' ', jd.get("jobSummary", ""))).strip()
                                                desc = html.unescape(re.sub(r'<[^>]+>', ' ', jd.get("description", ""))).strip()
                                                min_q = html.unescape(re.sub(r'<[^>]+>', ' ', jd.get("minimumQualifications", ""))).strip()
                                                pref_q = html.unescape(re.sub(r'<[^>]+>', ' ', jd.get("preferredQualifications", ""))).strip()
                                                full_text = f"{summary}\n\n=== MINIMUM QUALIFICATIONS ===\n{min_q}\n\n=== PREFERRED QUALIFICATIONS ===\n{pref_q}\n\n=== DESCRIPTION & RESPONSIBILITIES ===\n{desc}".strip()
                                                if full_text and len(full_text) > 100:
                                                    c.extra_payload = {"description": full_text[:40000]}
                                except Exception as apple_err:
                                    logger.info(f"Apple detail fetch failed for {c.raw_url}: {apple_err}")
                    elif family == "eightfold":
                        raw_payload = await self.browser_client.fetch_board_html(
                            target_url=target_url,
                            registered_target_url=target_url
                        )
                        extracted_candidates = adapter.parse_raw_payload(
                            payload=raw_payload,
                            board_name=board.name,
                            target_url=target_url,
                            selector_config=selector_config
                        )
                        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True, verify=False, headers={"User-Agent": "Mozilla/5.0"}) as client:
                            for c in extracted_candidates:
                                try:
                                    dr = await client.get(c.raw_url)
                                    if dr.status_code == 200:
                                        matches = re.findall(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', dr.text, re.DOTALL | re.I)
                                        for m in matches:
                                            try:
                                                ld_data = json.loads(m.strip())
                                                if isinstance(ld_data, dict) and ld_data.get("@type") == "JobPosting" and ld_data.get("description"):
                                                    clean_desc = html.unescape(re.sub(r'<[^>]+>', ' ', ld_data.get("description"))).strip()
                                                    if clean_desc and len(clean_desc) > 100:
                                                        c.extra_payload = {"description": clean_desc[:40000]}
                                                        break
                                            except Exception:
                                                pass
                                except Exception as ef_err:
                                    logger.info(f"Eightfold detail fetch failed for {c.raw_url}: {ef_err}")
                    elif family == "google_careers":
                        raw_payload = await self.browser_client.fetch_board_html(
                            target_url=target_url,
                            registered_target_url=target_url
                        )
                        extracted_candidates = adapter.parse_raw_payload(
                            payload=raw_payload,
                            board_name=board.name,
                            target_url=target_url,
                            selector_config=selector_config
                        )
                        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True, verify=False, headers={"User-Agent": "Mozilla/5.0"}) as client:
                            for c in extracted_candidates:
                                try:
                                    dr = await client.get(c.raw_url)
                                    if dr.status_code == 200:
                                        m_meta = re.search(r'meta\s+name=["\']description["\']\s+content=["\'](.*?)["\']', dr.text, re.IGNORECASE)
                                        if m_meta:
                                            g_desc = html.unescape(m_meta.group(1)).strip()
                                            if g_desc and len(g_desc) > 50:
                                                c.extra_payload = {"description": g_desc[:40000]}
                                except Exception as g_err:
                                    logger.info(f"Google detail fetch failed for {c.raw_url}: {g_err}")
                    elif family == "oracle":
                        raw_payload = await self.browser_client.fetch_board_html(
                            target_url=target_url,
                            registered_target_url=target_url
                        )
                        extracted_candidates = adapter.parse_raw_payload(
                            payload=raw_payload,
                            board_name=board.name,
                            target_url=target_url,
                            selector_config=selector_config
                        )
                    else:
                        raw_payload = await self.browser_client.fetch_board_html(
                            target_url=target_url,
                            registered_target_url=target_url
                        )
                        extracted_candidates = adapter.parse_raw_payload(
                            payload=raw_payload,
                            board_name=board.name,
                            target_url=target_url,
                            selector_config=selector_config
                        )

                    provider_cfg = revision.config_json if revision and isinstance(revision.config_json, dict) else None
                    ingest_res = await normalization_service.ingest_candidates(
                        board_id=board_id,
                        board_run_id=board_run.board_run_id,
                        extracted_candidates=extracted_candidates,
                        family=family,
                        provider_config=provider_cfg,
                    )

                    attempt_rec.stage = "completed"
                    attempt_rec.outcome = "partial" if ingest_res.enrichment_failed else "success"
                    attempt_rec.terminal_at = datetime.now(timezone.utc)
                    board_run.extracted_count = len(extracted_candidates)
                    run_success = True
                    run_partial = bool(ingest_res.enrichment_failed)
                    await session.commit()
                    break

                except TargetBoundaryViolation as tbv:
                    attempt_rec.stage = "completed"
                    attempt_rec.outcome = "boundary_violation"
                    attempt_rec.terminal_at = datetime.now(timezone.utc)
                    error_msg = str(tbv)
                    await session.commit()
                    break

                except Exception as e:
                    attempt_rec.stage = "completed"
                    attempt_rec.outcome = "error"
                    attempt_rec.terminal_at = datetime.now(timezone.utc)
                    error_msg = str(e)
                    await session.commit()
                    if attempt_num < max_attempts:
                        await asyncio.sleep(1.0)

            board_run.terminal_at = datetime.now(timezone.utc)
            board_run.stage = "completed"
            if run_success:
                board_run.outcome = "partial" if run_partial else "success"
                board.consecutive_parser_failures = 0
            else:
                board_run.outcome = "provider_failure"
                board_run.error_code = error_msg
                board.consecutive_parser_failures += 1
                if board.consecutive_parser_failures >= 3:
                    board.status = "held"
                    logger.warning(f"Board {board_id} exceeded failure threshold (3). Status set to HELD.")

            await session.commit()
            return board_run

execution_engine = PipelineExecutionEngine()