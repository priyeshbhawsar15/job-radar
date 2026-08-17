import asyncio
import logging
import json
import re
import html
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

def clean_amazon_html(raw_html: str) -> str:
    if not raw_html: return ''
    text = html.unescape(raw_html)
    clean = re.sub(r'<[^>]+>', ' ', text)
    lines = [l.strip() for l in clean.splitlines() if len(l.strip()) > 5]
    filtered = [l for l in lines if not any(x in l.lower() for x in ['equal opportunity', 'disability', 'accommodation', 'privacy', 'cookie', 'affirmative action', 'recruiting partner', 'pay transparency'])]
    return (chr(10) + chr(10)).join(filtered)

class PipelineExecutionEngine:
    """Stateful engine for executing board parsing runs with multi-page pagination & threshold rules."""

    def __init__(self, session_factory=AsyncSessionLocal):
        self.session_factory = session_factory
        self.browser_client = BrowserServiceClient()

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
                            raw_url = f"https://www.amazon.jobs{item.get('job_path', '')}"
                            clean_url = canonicalize_job_url(raw_url, board_name, target_url)
                            if clean_url in seen_urls:
                                continue
                            seen_urls.add(clean_url)

                            desc_text = clean_amazon_html(item.get('description', ''))
                            basic_text = clean_amazon_html(item.get('basic_qualifications', ''))
                            pref_text = clean_amazon_html(item.get('preferred_qualifications', ''))

                            full_desc = (desc_text + chr(10) + chr(10) + "=== BASIC QUALIFICATIONS ===" + chr(10) + basic_text + chr(10) + chr(10) + "=== PREFERRED QUALIFICATIONS ===" + chr(10) + pref_text).strip()
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

                            fp = generate_fingerprint(board_name, title, loc)
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

        for idx, p in enumerate(parts):
            if p in ("en-US", "en_US") and idx + 1 < len(parts):
                site = parts[idx + 1].split('?')[0]
                break
            elif any(x in p.lower() for x in ["external", "career", "apply", "jobs"]):
                site = p.split('?')[0]
                break

        facets = {}
        if 'locationCountry=' in target_url:
            country_code = target_url.split('locationCountry=')[-1].split('&')[0]
            facets['locationCountry'] = [country_code]
        if 'jobFamilyGroup=' in target_url:
            groups = re.findall(r'jobFamilyGroup=([^&]+)', target_url)
            if groups:
                facets['jobFamilyGroup'] = groups
        if 'timeType=' in target_url:
            tt = target_url.split('timeType=')[-1].split('&')[0]
            facets['timeType'] = [tt]

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

                    await normalization_service.ingest_candidates(
                        board_id=board_id,
                        board_run_id=board_run.board_run_id,
                        extracted_candidates=extracted_candidates
                    )

                    attempt_rec.stage = "completed"
                    attempt_rec.outcome = "success"
                    attempt_rec.terminal_at = datetime.now(timezone.utc)
                    board_run.extracted_count = len(extracted_candidates)
                    run_success = True
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
                board_run.outcome = "success"
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
