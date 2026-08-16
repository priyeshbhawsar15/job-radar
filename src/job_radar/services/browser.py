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
    """Client communicating with private local Playwright microservice boundary."""

    def __init__(self, service_url: Optional[str] = None):
        self.service_url = (service_url or settings.BROWSER_SERVICE_URL).rstrip("/")

    async def fetch_board_html(self, target_url: str, registered_target_url: Optional[str] = None) -> str:
        """Fetch raw HTML/JSON content via browser boundary with URL validation."""
        validate_target_url(target_url, registered_target_url)

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/html, */*"
        }

        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True, headers=headers) as client:
            try:
                response = await client.post(
                    f"{self.service_url}/render",
                    json={"url": target_url}
                )
                response.raise_for_status()
                data = response.json()
                return data.get("content", "")
            except Exception as e:
                logger.info(f"Browser service unavailable ({e}), using direct HTTP fetch for {target_url}")
                resp = await client.get(target_url)
                resp.raise_for_status()
                return resp.text
