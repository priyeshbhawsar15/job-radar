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

    if registered_target_url:
        parsed_reg = urlparse(registered_target_url)
        if parsed_reg.netloc and parsed_target.netloc != parsed_reg.netloc:
            raise TargetBoundaryViolation(
                f"Target URL netloc '{parsed_target.netloc}' does not match registered target '{parsed_reg.netloc}'"
            )
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

    async def fetch_board_html(
        self,
        target_url: str,
        registered_target_url: Optional[str] = None,
        wait_for_selector: Optional[str] = None,
    ) -> str:
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
            if wait_for_selector:
                await page.wait_for_selector(wait_for_selector, timeout=15000)
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


