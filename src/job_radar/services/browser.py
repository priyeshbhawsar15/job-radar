import logging
from urllib.parse import urlparse
import httpx
from typing import Optional
from job_radar.config import settings

logger = logging.getLogger(__name__)

class TargetBoundaryViolation(Exception):
    """Raised when a target URL violates private boundary rules."""
    pass

def validate_target_url(target_url: str, registered_target_url: Optional[str] = None) -> bool:
    parsed_target = urlparse(target_url)
    if parsed_target.scheme not in ("http", "https"):
        raise TargetBoundaryViolation(f"Invalid URL scheme: {parsed_target.scheme}")
    if not parsed_target.netloc:
        raise TargetBoundaryViolation("Target URL missing network location / domain host.")
    return True

import logging
import json
import re
from urllib.parse import urlparse
import httpx
from typing import Optional, Dict, Any
from job_radar.config import settings

logger = logging.getLogger(__name__)

class TargetBoundaryViolation(Exception):
    """Raised when a target URL violates private boundary rules."""
    pass

def validate_target_url(target_url: str, registered_target_url: Optional[str] = None) -> bool:
    parsed_target = urlparse(target_url)
    if parsed_target.scheme not in ("http", "https"):
        raise TargetBoundaryViolation(f"Invalid URL scheme: {parsed_target.scheme}")
    if not parsed_target.netloc:
        raise TargetBoundaryViolation("Target URL missing network location / domain host.")
    return True

class BrowserServiceClient:
    """Client communicating with Playwright rendering boundary."""

    def __init__(self, service_url: Optional[str] = None):
        self.service_url = (service_url or settings.BROWSER_SERVICE_URL).rstrip("/")
        self._playwright = None
        self._browser = None

    async def _get_browser(self):
        if self._browser is None:
            from playwright.async_api import async_playwright
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(headless=True)
        return self._browser

    async def fetch_board_html(self, target_url: str, registered_target_url: Optional[str] = None) -> str:
        validate_target_url(target_url, registered_target_url)

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/html, */*"
        }

        try:
            browser = await self._get_browser()
            page = await browser.new_page(
                viewport={"width": 1440, "height": 1000},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            await page.goto(target_url, wait_until="domcontentloaded", timeout=18000)
            await page.wait_for_timeout(4500)
            content = await page.content()
            await page.close()
            if content and len(content) > 500:
                return content
        except Exception as e:
            logger.info(f"Playwright fetch fallback ({e}) for {target_url}")

        async with httpx.AsyncClient(timeout=8.0, follow_redirects=True, headers=headers) as client:
            resp = await client.get(target_url)
            resp.raise_for_status()
            return resp.text

    async def fetch_oracle_detail_record(self, target_url: str, registered_target_url: Optional[str] = None) -> Optional[Dict[str, Any]]:
        parsed = urlparse(target_url)
        if parsed.scheme != "https":
            return None

        validate_target_url(target_url, registered_target_url)

        if registered_target_url:
            reg_parsed = urlparse(registered_target_url)
            if reg_parsed.netloc and parsed.netloc != reg_parsed.netloc:
                return None

        # Extract requisition ID from numeric /job/{id} path
        job_match = re.search(r'/job/(\d+)', parsed.path)
        if not job_match:
            return None

        req_id_str = job_match.group(1)

        captured_record: Optional[Dict[str, Any]] = None

        try:
            browser = await self._get_browser()
            page = await browser.new_page(
                viewport={"width": 1440, "height": 1000},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )

            async def handle_response(response):
                nonlocal captured_record
                if captured_record is not None:
                    return

                try:
                    if response.request.resource_type in {"xhr", "fetch"}:
                        resp_url = response.url
                        resp_parsed = urlparse(resp_url)
                        if resp_parsed.netloc != parsed.netloc:
                            return
                        if "recruitingCEJobRequisitions" not in resp_url and "recruitingCEJobRequisitionDetails" not in resp_url:
                            return
                        if response.status != 200:
                            return

                        headers = response.headers
                        content_length = int(headers.get("content-length", 0))
                        if content_length > 5 * 1024 * 1024:
                            return

                        body = await response.body()
                        if len(body) > 5 * 1024 * 1024:
                            return

                        data = json.loads(body.decode("utf-8"))
                        if isinstance(data, dict) and isinstance(data.get("items"), list):
                            for item in data["items"]:
                                if isinstance(item, dict):
                                    item_id = str(item.get("RequisitionId") or item.get("requisitionId") or "").strip()
                                    if item_id == req_id_str:
                                        captured_record = data
                                        break
                except Exception as e:
                    logger.debug(f"Oracle response capture error: {e}")

            page.on("response", handle_response)
            try:
                await page.goto(target_url, wait_until="domcontentloaded", timeout=18000)
                await page.wait_for_timeout(4500)
            finally:
                await page.close()

            return captured_record
        except Exception as e:
            logger.info(f"Playwright Oracle response capture error ({e}) for {target_url}")
            return None

