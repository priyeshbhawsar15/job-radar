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
    """Enforce strict boundary validation."""
    parsed_target = urlparse(target_url)
    if parsed_target.scheme not in ("http", "https"):
        raise TargetBoundaryViolation(f"Invalid URL scheme: {parsed_target.scheme}")

    if not parsed_target.netloc:
        raise TargetBoundaryViolation("Target URL missing network location / domain host.")

    if registered_target_url:
        parsed_registered = urlparse(registered_target_url)
        if parsed_target.netloc != parsed_registered.netloc:
            raise TargetBoundaryViolation(
                f"Domain boundary mismatch! Requested host '{parsed_target.netloc}' "
                f"does not match registered board target host '{parsed_registered.netloc}'."
            )

    return True

class BrowserServiceClient:
    """Client communicating with private Playwright rendering boundary."""

    def __init__(self, service_url: Optional[str] = None):
        self.service_url = (service_url or settings.BROWSER_SERVICE_URL).rstrip("/")

    async def fetch_board_html(self, target_url: str, registered_target_url: Optional[str] = None) -> str:
        """Fetch raw HTML/JSON content via browser boundary with URL validation."""
        validate_target_url(target_url, registered_target_url)

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/html, */*"
        }

        # 1. Try Playwright container microservice
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=True, headers=headers) as client:
            try:
                response = await client.post(
                    f"{self.service_url}/render",
                    json={"url": target_url}
                )
                response.raise_for_status()
                data = response.json()
                content = data.get("content", "")
                if content and len(content) > 500:
                    return content
            except Exception:
                pass

        # 2. Option B Fix for Type 1 Workday & SPA Boards: Local Headless Playwright Chromium
        try:
            from playwright.async_api import async_playwright
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page(
                    viewport={"width": 1440, "height": 1000},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
                await page.goto(target_url, wait_until="networkidle", timeout=25000)
                await page.wait_for_timeout(2000)
                content = await page.content()
                await browser.close()
                if content and len(content) > 500:
                    return content
        except Exception as e:
            logger.info(f"Local Playwright fetch error ({e}), falling back to direct HTTP fetch for {target_url}")

        # 3. Fallback: Direct HTTP GET
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True, headers=headers) as client:
            resp = await client.get(target_url)
            resp.raise_for_status()
            return resp.text
