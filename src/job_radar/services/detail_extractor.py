from dataclasses import dataclass
import hashlib
import logging
import asyncio
import html
import json
import re
import httpx
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Iterator, List, Mapping

from job_radar.config import settings
from job_radar.services.browser import BrowserServiceClient
from job_radar.services.detail_contracts import (
    DetailRequest, DetailResult, ERR_INVALID_DETAIL_URL, ERR_DESCRIPTION_INVALID,
    ERR_DESCRIPTION_MISSING, ERR_IDENTITY_MISMATCH, ERR_FUTURE_POOL,
)
from job_radar.services.oracle_detail import fetch_oracle_detail
from job_radar.services.phenom_detail import fetch_phenom_detail
from job_radar.services.workday_detail import fetch_workday_detail
from job_radar.services.zoho_detail import fetch_zoho_detail_from_html
from job_radar.services.talent500_detail import fetch_talent500_detail
from job_radar.services.greenhouse_detail import fetch_greenhouse_detail
from job_radar.services.smartrecruiters_detail import fetch_smartrecruiters_detail
from job_radar.services.ashby_detail import fetch_ashby_detail
from job_radar.services.ashby_detail import parse_ashby_job_url
from job_radar.services.eightfold_detail import fetch_eightfold_detail, parse_eightfold_job_url
from job_radar.services.apple_detail import fetch_apple_detail
from job_radar.services.site_detail import fetch_site_detail
from job_radar.services.google_detail import fetch_google_detail
from job_radar.services.celonis_detail import fetch_celonis_detail
from job_radar.services.mattel_detail import fetch_mattel_detail
from job_radar.services.tesco_detail import fetch_tesco_detail

logger = logging.getLogger(__name__)

REJECTION_PATTERNS = [
    re.compile(r'window\.vanityurlenabled', re.IGNORECASE),
    re.compile(r'page not found(?:\.|\s*-)', re.IGNORECASE),
    re.compile(r'candidate experience page careers', re.IGNORECASE),
    re.compile(r'sorry!?\s+we\s+couldn[\'\u2019]t\s+find\s+any\s+jobs', re.IGNORECASE),
    re.compile(r'^(?:full\s+job\s+description\s+for|position\s+for)\b', re.IGNORECASE),
    re.compile(r'^\.job-details-wrapper\b', re.IGNORECASE),
]

CONTENT_INDICATORS = [
    "responsibilities",
    "qualifications",
    "requirements",
    "experience",
    "skills",
    "what you will do",
    "what you'll do",
    "what you’ll do",
    "what you will need",
    "what you'll need",
    "what you’ll need",
    "what you bring",
    "what we're looking for",
    "what we are looking for",
    "who you are",
    "about the role",
    "about the job",
    "job description",
    "job summary",
    "role summary",
    "role overview",
    "overview",
    "duties",
    "key accountabilities",
    "job purpose",
    "education and experience",
    "preferred qualifications",
    "basic qualifications",
    "minimum qualifications",
    "required qualifications",
    "key responsibilities",
    "we are looking for",
    "in this role",
    "about us",
    "the role",
    "job overview",
]

_FUTURE_ONLY = re.compile(
    r"\b(?:talent community|future opportunities|future vacancies|"
    r"upcoming vacancy|no current (?:vacanc(?:y|ies)|openings?|positions?)|"
    r"not tied to a specific (?:role|position)|"
    r"bolsa de (?:trabajo|talento)|futuras oportunidades|sin vacantes actuales)\b",
    re.IGNORECASE,
)
_FUTURE_TITLE = re.compile(r"\b(?:future openings?|future opportunities|talent pool)\b", re.I)
_ROLE_SECTION = re.compile(
    r"^(?:about the role|about the job|job (?:description|summary|overview)|"
    r"role (?:summary|overview)|introduction|(?:core |key |position )?responsibilities(?: and duties)?|"
    r"duties|key accountabilities|your (?:impact|day-to-day)|"
    r"what you(?:'|’)ll (?:do|be responsible for)|how you(?:'|’)ll demonstrate|"
    r"what you will (?:do|accomplish)|"
    r"the impact you will have|in this role|"
    r"responsabilidades|funciones|tareas del puesto|sobre el puesto|"
    r"resumen de posici[oó]n|el impacto que tendr[aá]s|en este puesto)\b\s*:?(?:\s|$)",
    re.IGNORECASE,
)
_OTHER_SECTION = re.compile(
    r"^(?:about (?!the (?:role|job)\b)\S+(?:\s+\S+){0,3}|"
    r"who are we|what .{1,35} is|benefits?|perks?|what we (?:offer|look for)|"
    r"what you (?:will )?bring|about you|qualifications?|(?:minimum|preferred|basic|required|desired) (?:qualifications?|requirements?)|"
    r"education and experience|location|work (?:model|location|mode)|"
    r"equal opportunity|compliance|disclaimer|notification to agencies|"
    r"privacy|accommodations|posting statement|learn more about us|"
    r"lo que buscamos|(?:a snapshot of )?our (?:many )?perks)\b",
    re.IGNORECASE,
)
_DUTY_ACTION = re.compile(
    r"\b(?:build(?:ing)?|develop(?:ing)?|design(?:ing)?|implement(?:ing)?|maintain(?:ing)?|manage|lead|drive|create|"
    r"deliver|support|collaborate|partner|analy[sz]e|review|monitor|improve|"
    r"coordinate|resolv(?:e|ing)|ensure|provide|prepare|perform|own|write|test|"
    r"book(?:ing)?|settle(?:ment)?|reconcil(?:e|iation)|"
    r"construir|desarrollar|diseñar|implementar|mantener|gestionar|"
    r"liderar|crear|colaborar|analizar|revisar|supervisar|mejorar|"
    r"coordinar|resolver|garantizar|preparar|realizar|diseñará|"
    r"desarrollará|gestionará|liderará|colaborará)\b",
    re.IGNORECASE,
)
_BOILERPLATE_LINE = re.compile(
    r"\b(?:benefits?|perks?|about us|our company|privacy|cookie|"
    r"terms of use|equal opportunity|apply now|sign in|navigation|"
    r"explore jobs|search jobs|build your career|create (?:a |your )?profile|"
    r"job alerts?|browse (?:jobs|roles)|salario|beneficios)\b",
    re.IGNORECASE,
)

_DUTY_SUBJECT = re.compile(
    r"^(?:you(?:'|’)ll|you will|this role|the (?:role|position)|"
    r"as an?\s+.{3,55}?\s+you will|our\s+.{3,55}?\s+(?:will|engage|build|own)|"
    r"tendr[aá]s|comunicar[aá]s|asignar[aá]s|te reunir[aá]s|"
    r"superar[aá]s|utilizar[aá]s|desarrollar[aá]s)\b",
    re.IGNORECASE,
)
_BULLET = re.compile(r"^(?:[•*–-]|\d+[.)])\s*")

# Exact observed provider templates. Insert section boundaries while retaining every
# line of source content, including the qualification section for consumers.
_SCOPED_ROLE_HEADINGS = {
    "Marriott Tech": (r"Job Responsibilities", r"Position Summary"),
    "McD": (r"Position Summary", r"Primary Responsibilities"),
    "Redis": (r"What type of work will you be doing",),
    "Supabase": (r"What You['’]ll Own",),
    "GoDaddy": (r"What you['’]ll get to do\.{0,3}",),
    "HighRadius": (r"Job role\s*:\s*.+", r"Key Responsibilities"),
    "BrowserStack": (r"Role in nutshell", r"What will you do\??"),
    "Vanguard": (r"Responsibilites",),
    "Amgen": (r"Roles and Responsibilities",),
    "Salesforce": (r"What You['’]ll Actually Be Building",),
    "JLL": (r"What this job involves",),
    "Walmart": (r"What you['’]ll do\.{0,3}",),
    "JioStar": (r"Key responsibilities",),
    "Regal Rexnord": (r"SCOPE OF ROLE", r"Essential Duties and Responsibilities"),
    "Oracle": (r"Job Responsibilities",),
    "Celonis": (r"The Work You['’]ll Do",),
    "Sourcegraph": (r"Here['’]s what you can expect in your first year",),
    "Razorpay": (r"Roles and responsibilities",),
    "Gitlab": (r"Associate Renewals Manager Responsibilities",),
    "Coinbase": (r"What You['’]ll Be Doing",),
    "Groww": (r"Reimagine Internal Audit with us \| What You['’]ll Do",),
    "Cognite": (r"As an Account Executive, Manufacturing you will.*",),
    "Mattel": (r"What Your Impact Will Be",),
    "Airbnb": (r"The difference you will make", r"A typical day"),
}
_SCOPED_QUALIFICATION_HEADINGS = {
    "Marriott Tech": (r"Skill and Experience",),
    "McD": (r"Skills Required", r"Preferred Skills"),
    "Redis": (r"What You['’]ll Bring to Redis", r"Your experience and strengths"),
    "Supabase": (r"What You['’]ll Bring", r"What We Offer"),
    "GoDaddy": (r"Your experience should include\.{0,3}",),
    "HighRadius": (r"Desired Requirements", r"Skill & Experience Needed"),
    "BrowserStack": (r"What do you bring", r"Requirements", r"Qualifications"),
    "Vanguard": (r"Qualifications and Skills",),
    "Amgen": (r"Basic Qualifications",),
    "Salesforce": (r"You['’]re Our Forward Deployed Engineer If…?",),
    "JLL": (r"Education and experience",),
    "Walmart": (r"What You['’]ll Bring\.{0,4}",),
    "JioStar": (r"Skills and attributes for success",),
    "Regal Rexnord": (r"About Regal Rexnord", r"Education and Experience Requirements"),
    "Oracle": (r"Mandatory Skills", r"Preferred Skills"),
    "Celonis": (r"What You Bring", r"The Qualifications You Need"),
    "Sourcegraph": (r"About you", r"Your Skills and Experience"),
    "Razorpay": (r"Must haves",),
    "Gitlab": (r"Associate Renewals Manager Requirements",),
    "Coinbase": (r"What We Look For",),
    "Groww": (r"What Makes You a Great Fit",),
    "Cognite": (r"you bring to Cognite",),
    "Mattel": (r"What We['’]re Looking For",),
    "Airbnb": (r"Your expertise",),
}


def normalize_detail_sections(description: str, board_name: str) -> str:
    """Expose only observed board-specific duty/qualification headings to the validator."""
    if not isinstance(description, str) or not description:
        return description
    starts = _SCOPED_ROLE_HEADINGS.get(board_name, ())
    stops = _SCOPED_QUALIFICATION_HEADINGS.get(board_name, ())
    if not starts and not stops:
        return description
    if board_name in ("HighRadius", "Razorpay", "Airbnb"):
        # This Greenhouse template double-encodes nonbreaking spaces and uses ●.
        description = html.unescape(description)
    if board_name == "HighRadius":
        description = description.replace("●", "•")
    description = description.replace("\xa0", " ")
    if board_name == "JioStar":
        # CXS places this template on one physical line, including the skills.
        description = re.sub(r"\s*●\s*", "\n• ", description)
        description = re.sub(r"\s+(Key responsibilities|Skills and attributes for success)\s*:?(?=\s|$)", r"\n\1:", description, flags=re.I)
    lines = description.splitlines()
    result = []
    for line in lines:
        candidate = line.strip()
        if any(re.fullmatch(pattern + r"\s*:?(?:\.{0,3})?", candidate, re.I) for pattern in stops):
            result.append("Qualifications")
        elif any(re.fullmatch(pattern + r"\s*:?(?:\.{0,3})?", candidate, re.I) for pattern in starts):
            result.append("Responsibilities")
        elif board_name in ("Vanguard", "Regal Rexnord", "BrowserStack") and any(
            re.match(pattern + r"\b", candidate, re.I) for pattern in starts
        ):
            result.append("Responsibilities")
        result.append(line)
    return "\n".join(result)


def _is_job_posting_type(value: Any) -> bool:
    if isinstance(value, str):
        return value.lower() == "jobposting"
    return isinstance(value, list) and any(_is_job_posting_type(item) for item in value)


def iter_json_ld_nodes(value: Any) -> Iterator[Dict[str, Any]]:
    if isinstance(value, list):
        for item in value:
            yield from iter_json_ld_nodes(item)
    elif isinstance(value, dict):
        yield value
        graph = value.get("@graph")
        if isinstance(graph, (dict, list)):
            yield from iter_json_ld_nodes(graph)


def extract_job_posting(raw_html: str) -> Optional[Dict[str, Any]]:
    if not raw_html:
        return None
    unescaped = html.unescape(raw_html)
    script_blocks = re.findall(
        r'<script\b[^>]*\btype=[\"\']application/ld\+json[\"\'][^>]*>(.*?)</script>',
        unescaped,
        re.DOTALL | re.IGNORECASE,
    )
    for raw in script_blocks:
        try:
            data = json.loads(raw.strip())
            for node in iter_json_ld_nodes(data):
                if _is_job_posting_type(node.get("@type")):
                    if node.get("description"):
                        return node
        except Exception:
            pass
    return None


def description_is_valid(text: Optional[str], *, title: str = "", board_name: str = "") -> bool:
    if not text or not isinstance(text, str):
        return False
    cleaned = text.strip()
    if not cleaned or len(cleaned) < 150:
        return False

    for pat in REJECTION_PATTERNS:
        if pat.search(cleaned):
            if len(cleaned) < 500 or 'window' in pat.pattern or 'sorry' in pat.pattern or 'page not found' in pat.pattern:
                return False

    if _FUTURE_TITLE.search(title) or _FUTURE_ONLY.search(cleaned):
        return False

    if board_name == "Databricks" and "あなたがもたらす影響" in cleaned:
        # Observed Japanese template has full, unbulleted duties and a separate
        # requirements section. Count only action sentences between those bounds.
        before, sep, after = cleaned.partition("あなたがもたらす影響")
        duties, stop, _ = after.partition("必要な条件/経験")
        if not stop or len(before) < 100:
            return False
        action_lines = [line for line in duties.splitlines()
                        if len(line.strip()) >= 18 and re.search(r"(?:定義|設計|構築|推進|連携|指導|確立|促進|貢献|リード)", line)]
        return len(action_lines) >= 3

    plain = re.sub(r"<[^>]+>", "\n", html.unescape(cleaned))
    lines = [line.strip() for line in plain.splitlines() if line.strip()]
    section = "unknown"
    role_duties = 0
    unheaded_bullets = 0
    for raw in lines:
        line = _BULLET.sub("", raw).strip()
        role_match = _ROLE_SECTION.match(line)
        if role_match:
            section = "role"
            line = line[role_match.end():].strip()
            if not line:
                continue
        elif len(line) < 90 and _OTHER_SECTION.match(line):
            section = "other"
            continue
        if section == "other" or len(line.split()) < 4 or _BOILERPLATE_LINE.search(line):
            continue
        # Action words in product narratives are not duties. Require a role section,
        # a candidate-directed sentence, or a run of explicit task bullets before
        # any company/benefits section (some feeds omit a duties heading entirely).
        action = bool(_DUTY_ACTION.search(line) or _DUTY_SUBJECT.match(line))
        if not action:
            continue
        if section == "role":
            role_duties += 1
        elif section == "unknown" and _BULLET.match(raw):
            unheaded_bullets += 1
    return role_duties > 0 or unheaded_bullets >= 2


def clean_html_to_text(raw_html_str: str) -> str:
    if not raw_html_str:
        return ""
    text = html.unescape(raw_html_str)
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


def strip_to_plain_text(raw_html_str: str) -> str:
    """Strip all JS/CSS/HTML tags, returning bare plain text (last-resort before Job Ops inference)."""
    if not raw_html_str:
        return ""
    text = html.unescape(raw_html_str)
    text = re.sub(r'<(script|style)\b[^>]*>[\s\S]*?</\1>', ' ', text, flags=re.IGNORECASE)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'[ \t]+', ' ', text)
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    return "\n".join(lines)


class DetailExtractor:
    """Service to fetch full job detail content and parse description, salary, department & employment type."""

    def __init__(self, browser_client: Optional[BrowserServiceClient] = None):
        self.browser_client = browser_client or BrowserServiceClient()

    async def fetch_and_enrich(
        self,
        public_apply_url: str,
        board_name: str,
        title: str,
        *,
        family: str = "generic",
        provider_config: Optional[Mapping[str, Any]] = None,
        client: Optional[httpx.AsyncClient] = None,
    ) -> DetailResult:
        provider_config = provider_config or {}
        if isinstance(provider_config, dict):
            if family == "oracle" and "oracle_detail" in provider_config and isinstance(provider_config["oracle_detail"], dict):
                provider_config = provider_config["oracle_detail"]
            elif family == "phenom" and "phenom_detail" in provider_config and isinstance(provider_config["phenom_detail"], dict):
                provider_config = provider_config["phenom_detail"]

        req = DetailRequest(
            family=family,
            public_url=public_apply_url,
            board_name=board_name,
            title=title,
            provider_config=provider_config,
        )

        if family == "ashby" and parse_ashby_job_url(public_apply_url, provider_config) is None:
            return DetailResult.empty(ERR_INVALID_DETAIL_URL)
        if family == "eightfold" and parse_eightfold_job_url(public_apply_url, provider_config) is None:
            return DetailResult.empty(ERR_INVALID_DETAIL_URL)

        close_client = False
        if client is None:
            client = httpx.AsyncClient(timeout=15.0, follow_redirects=False)
            close_client = True

        native_failure: Optional[DetailResult] = None
        observed_invalid_content = False
        try:
            if family == "oracle":
                result = await fetch_oracle_detail(req, client)
                if result.error_code is not None:
                    return result
                description = normalize_detail_sections(result.description or "", board_name)
                if not description_is_valid(description, title=title):
                    return DetailResult.empty(ERR_DESCRIPTION_INVALID)
                return DetailResult(**{**result.__dict__, "description": description})
            elif family == "phenom":
                return await fetch_phenom_detail(req, client)
            elif family == "talent500":
                return await fetch_talent500_detail(req, client)
            elif family == "ashby":
                return await fetch_ashby_detail(req, client)
            elif family == "eightfold":
                return await fetch_eightfold_detail(req, client)
            elif family == "apple_jobs":
                return await fetch_apple_detail(req, client)
            elif family == "amazon_jobs" or (family == "custom" and public_apply_url.startswith("https://www.novartis.com/")):
                return await fetch_site_detail(req, client)
            elif family == "google_careers":
                return await fetch_google_detail(req, client)
            elif family == "celonis_dxp":
                return await fetch_celonis_detail(req, client)
            elif family == "custom" and public_apply_url.startswith("https://jobs.mattel.com/"):
                return await fetch_mattel_detail(req, client)
            elif family == "avature" and public_apply_url.startswith("https://careers.tesco.com/"):
                return await fetch_tesco_detail(req, client)
            elif family == "workday":
                result = await fetch_workday_detail(req, client)
                if result.error_code is None:
                    description = normalize_detail_sections(result.description or "", board_name)
                    if not description_is_valid(description, title=title):
                        return DetailResult.empty(ERR_DESCRIPTION_INVALID)
                    return DetailResult(**{**result.__dict__, "description": description})
                if result.error_code in (ERR_DESCRIPTION_MISSING, ERR_DESCRIPTION_INVALID, ERR_INVALID_DETAIL_URL, ERR_IDENTITY_MISMATCH, ERR_FUTURE_POOL):
                    return result
                native_failure = result
                # Fall through to generic HTML fallback below on CXS failure.
            elif family == "zoho":
                raw_html = await self.browser_client.fetch_board_html(
                    public_apply_url, wait_for_selector="div.cw-jobdescription"
                )
                return fetch_zoho_detail_from_html(raw_html, public_apply_url)
            elif family == "greenhouse" or "gh_jid" in public_apply_url:
                result = await fetch_greenhouse_detail(req, client)
                if result.error_code is None:
                    return result
                if result.error_code in (ERR_DESCRIPTION_MISSING, ERR_DESCRIPTION_INVALID, ERR_INVALID_DETAIL_URL, ERR_IDENTITY_MISMATCH, ERR_FUTURE_POOL):
                    return result
                native_failure = result
                # A bounded provider-native failure may still have a usable public page.
            elif family == "smartrecruiters":
                result = await fetch_smartrecruiters_detail(req, client)
                if result.error_code is None:
                    return result
                if result.error_code in (ERR_DESCRIPTION_MISSING, ERR_DESCRIPTION_INVALID, ERR_INVALID_DETAIL_URL):
                    return result
                native_failure = result
                # A bounded provider-native failure may still have a usable public page.

            # Generic fallback logic
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            }
            try:
                resp = await client.get(public_apply_url, headers=headers, follow_redirects=False)
                if resp.status_code == 200 and len(resp.text) > 800:
                    parsed = self.parse_detail_html(resp.text, board_name, title, public_apply_url)
                    if parsed.get("description"):
                        return DetailResult(
                            description=parsed["description"],
                            location=parsed.get("location"),
                            employment_type=parsed.get("employment_type"),
                            department=parsed.get("department"),
                            salary_raw=parsed.get("salary_raw"),
                            salary_min=parsed.get("salary_min"),
                            salary_max=parsed.get("salary_max"),
                            salary_currency=parsed.get("salary_currency"),
                            source="generic_static_html",
                        )
                    observed_invalid_content = bool(extract_job_posting(resp.text))
            except Exception:
                pass

            raw_html = None
            try:
                raw_html = await self.browser_client.fetch_board_html(public_apply_url)
                parsed = self.parse_detail_html(raw_html, board_name, title, public_apply_url)
                if parsed.get("description"):
                    return DetailResult(
                        description=parsed["description"],
                        location=parsed.get("location"),
                        employment_type=parsed.get("employment_type"),
                        department=parsed.get("department"),
                        salary_raw=parsed.get("salary_raw"),
                        salary_min=parsed.get("salary_min"),
                        salary_max=parsed.get("salary_max"),
                        salary_currency=parsed.get("salary_currency"),
                        source="generic_browser_html",
                    )
                observed_invalid_content = observed_invalid_content or bool(extract_job_posting(raw_html))
            except Exception as e:
                logger.info(f"Failed to fetch detail page for {public_apply_url}: {e}")

            if raw_html and not observed_invalid_content:
                infer_result = await self.fetch_jobops_infer_fallback(raw_html, client)
                if infer_result is not None:
                    return infer_result

            if native_failure:
                return native_failure
            if observed_invalid_content:
                return DetailResult.empty(ERR_DESCRIPTION_INVALID)
            return DetailResult.empty(ERR_INVALID_DETAIL_URL)

        finally:
            if close_client:
                await client.aclose()

    async def fetch_jobops_infer_fallback(
        self, raw_html_or_text: str, client: httpx.AsyncClient
    ) -> Optional[DetailResult]:
        """Fall back to Job Ops' /api/manual-jobs/infer when local deterministic parsing fails."""
        if not settings.JOBOPS_ENDPOINT:
            return None

        stripped_text = strip_to_plain_text(raw_html_or_text)[:35000]
        if not stripped_text:
            return None

        infer_url = f"{settings.JOBOPS_ENDPOINT.rstrip('/')}/api/manual-jobs/infer"
        headers = {}

        if settings.JOBOPS_USERNAME and settings.JOBOPS_PASSWORD:
            login_url = f"{settings.JOBOPS_ENDPOINT.rstrip('/')}/api/auth/login"
            try:
                login_resp = await client.post(
                    login_url,
                    json={
                        "username": settings.JOBOPS_USERNAME,
                        "password": settings.JOBOPS_PASSWORD,
                    },
                    timeout=15.0,
                )
                if login_resp.status_code == 200:
                    login_data = login_resp.json()
                    token = (
                        login_data.get("data", {}).get("token")
                        or login_data.get("token")
                    )
                    if token:
                        headers["Authorization"] = f"Bearer {token}"
            except Exception as e:
                logger.info(f"Job Ops auth login failed: {e}")

        try:
            resp = await client.post(
                infer_url,
                json={"jobDescription": stripped_text},
                headers=headers,
                timeout=45.0,
            )
        except Exception as e:
            logger.info(f"Job Ops infer fallback request failed: {e}")
            return None

        if resp.status_code != 200:
            logger.info(f"Job Ops infer fallback returned status {resp.status_code}")
            return None

        try:
            data = resp.json()
        except Exception as e:
            logger.info(f"Job Ops infer fallback returned invalid JSON: {e}")
            return None

        payload_data = data.get("data") if isinstance(data.get("data"), dict) else data
        job_data = payload_data.get("job") if isinstance(payload_data.get("job"), dict) else payload_data

        inferred_description = job_data.get("jobDescription")
        if not description_is_valid(inferred_description):
            return None

        salary_raw = job_data.get("salary")

        return DetailResult(
            description=inferred_description[:40000],
            location=(job_data.get("location") or None),
            employment_type=(job_data.get("jobType") or None),
            department=(job_data.get("department") or None),
            salary_raw=salary_raw,
            title=(job_data.get("title") or None),
            source="jobops_infer_fallback",
        )

    def parse_detail_html(self, raw_html_text: str, board_name: str, title: str, apply_url: str) -> Dict[str, Any]:
        raw_html_text = html.unescape(raw_html_text)
        jp = extract_job_posting(raw_html_text)
        if jp and jp.get("description"):
            desc_clean = clean_html_to_text(jp["description"])[:40000]
            if description_is_valid(desc_clean, title=title):
                loc = None
                job_loc = jp.get("jobLocation")
                if isinstance(job_loc, dict):
                    addr = job_loc.get("address", {})
                    if isinstance(addr, dict):
                        locality = addr.get("addressLocality")
                        region = addr.get("addressRegion")
                        country = addr.get("addressCountry")
                        parts = [p for p in [locality, region, country] if p and isinstance(p, str)]
                        if parts:
                            loc = ", ".join(parts)[:200]
                elif isinstance(job_loc, list) and len(job_loc) > 0:
                    first_loc = job_loc[0]
                    if isinstance(first_loc, dict):
                        addr = first_loc.get("address", {})
                        if isinstance(addr, dict):
                            locality = addr.get("addressLocality")
                            region = addr.get("addressRegion")
                            country = addr.get("addressCountry")
                            parts = [p for p in [locality, region, country] if p and isinstance(p, str)]
                            if parts:
                                loc = ", ".join(parts)[:200]

                emp_type = jp.get("employmentType")
                if isinstance(emp_type, list):
                    emp_type = ", ".join(str(x) for x in emp_type)
                elif not isinstance(emp_type, str):
                    emp_type = None

                sal_raw = None
                sal_min = None
                sal_max = None
                sal_curr = None
                base_sal = jp.get("baseSalary")
                if isinstance(base_sal, dict):
                    val = base_sal.get("value", {})
                    sal_curr = base_sal.get("currency")
                    if isinstance(val, dict):
                        sal_min = val.get("minValue")
                        sal_max = val.get("maxValue")
                        if sal_min and sal_max:
                            sal_raw = f"{sal_min} - {sal_max} {sal_curr or ''}".strip()
                        elif sal_min:
                            sal_raw = f"{sal_min} {sal_curr or ''}".strip()

                return {
                    "description": desc_clean,
                    "location": loc,
                    "employment_type": emp_type,
                    "department": None,
                    "salary_raw": sal_raw,
                    "salary_min": sal_min,
                    "salary_max": sal_max,
                    "salary_currency": sal_curr,
                }

        # Fallback to meta tags
        desc_meta = None
        desc_match = re.search(r'<meta\b[^>]*?\bname=[\"\']description[\"\'][^>]*?\bcontent=[\"\'](.*?)[\"\']', raw_html_text, re.IGNORECASE)
        if not desc_match:
            desc_match = re.search(r'<meta\b[^>]*?\bproperty=[\"\']og:description[\"\'][^>]*?\bcontent=[\"\'](.*?)[\"\']', raw_html_text, re.IGNORECASE)

        if desc_match:
            desc_meta = html.unescape(desc_match.group(1)).strip()
            desc_clean = clean_html_to_text(desc_meta)[:40000]
            if description_is_valid(desc_clean, title=title):
                return {
                    "description": desc_clean,
                    "location": None,
                    "employment_type": None,
                    "department": None,
                    "salary_raw": None,
                    "salary_min": None,
                    "salary_max": None,
                    "salary_currency": None,
                }

        return {}

detail_extractor = DetailExtractor()
