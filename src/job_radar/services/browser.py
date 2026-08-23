import asyncio
import logging
import json
import re
from urllib.parse import urlparse
import httpx
from typing import Optional, Dict, Any
from job_radar.config import settings
from job_radar.services.settings_store import load_settings

logger = logging.getLogger(__name__)

_global_browser_semaphore: Optional[asyncio.Semaphore] = None
_global_semaphore_capacity: int = 10


def get_global_browser_semaphore() -> asyncio.Semaphore:
    global _global_browser_semaphore, _global_semaphore_capacity
    stored = load_settings()
    target_cap = stored.global_browser_concurrency or 10

    if _global_browser_semaphore is None or _global_semaphore_capacity != target_cap:
        _global_semaphore_capacity = target_cap
        _global_browser_semaphore = asyncio.Semaphore(target_cap)

    return _global_browser_semaphore


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
    """Client communicating with Playwright/Browserless rendering service."""

    def __init__(self, service_url: Optional[str] = None):
        self.service_url = (service_url or settings.BROWSER_SERVICE_URL).rstrip("/")

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

        # Priority 1: High-performance HTTP rendering via standalone Browserless container
        if self.service_url and (self.service_url.startswith("http://") or self.service_url.startswith("ws://")):
            http_endpoint = self.service_url.replace("ws://", "http://").replace("wss://", "https://")
            content_url = f"{http_endpoint}/content"

            payload = {
                "url": target_url,
                "waitFor": wait_for_selector if wait_for_selector else 4000,
                "userAgent": headers["User-Agent"]
            }

            sem = get_global_browser_semaphore()
            async with sem:
                # Up to 2 attempts with exponential backoff for transient Browserless queues
                for attempt in range(1, 3):
                    try:
                        logger.info(f"Fetching SPA rendered HTML via Browserless service (attempt {attempt}) at {content_url}")
                        async with httpx.AsyncClient(timeout=45.0) as client:
                            res = await client.post(content_url, json=payload)
                            if res.status_code == 200 and len(res.text) > 500:
                                return res.text
                    except Exception as b_err:
                        logger.warning(f"Browserless fetch attempt {attempt} failed ({b_err}) for {target_url}.")
                        if attempt < 2:
                            await asyncio.sleep(2.0)

        # Priority 2: Direct HTTP request fallback
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=True, headers=headers) as client:
            resp = await client.get(target_url)
            resp.raise_for_status()
            return resp.text
