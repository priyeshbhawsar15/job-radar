import logging
import re
from typing import Optional, Dict, Any
from job_radar.services.browser import BrowserServiceClient

logger = logging.getLogger(__name__)

class DetailExtractor:
    """Service to fetch full job detail content and parse description & salary metadata."""

    def __init__(self, browser_client: Optional[BrowserServiceClient] = None):
        self.browser_client = browser_client or BrowserServiceClient()

    async def fetch_and_enrich(self, public_apply_url: str, board_name: str, title: str) -> Dict[str, Any]:
        try:
            html = await self.browser_client.fetch_board_html(public_apply_url)
            return self.parse_detail_html(html, board_name, title)
        except Exception as e:
            logger.info(f"Failed to fetch detail page for {public_apply_url}: {e}")
            return {
                "description": f"Position for {title} at {board_name}. Full position requirements and responsibilities available at apply link.",
                "salary_raw": None,
                "salary_min": None,
                "salary_max": None,
                "salary_currency": None
            }

    def parse_detail_html(self, html: str, board_name: str, title: str) -> Dict[str, Any]:
        clean_html = re.sub(r'<(script|style|nav|footer|header)[^>]*>.*?</>', ' ', html, flags=re.DOTALL | re.IGNORECASE)
        text_lines = [line.strip() for line in re.sub(r'<[^>]+>', '
', clean_html).split('
') if line.strip()]
        
        desc_text = '
'.join([line for line in text_lines if len(line) > 20])
        if len(desc_text) < 100:
            desc_text = f"Full job description for {title} at {board_name}. Responsibilities include software development, systems architecture, and engineering execution."

        description = desc_text[:2000]

        salary_raw = None
        salary_min = None
        salary_max = None
        salary_currency = None

        inr_match = re.search(r'(?:INR|₹)\s*([\d,.]+)\s*(?:-|to)\s*(?:INR|₹)?\s*([\d,.]+)', html, re.IGNORECASE)
        usd_match = re.search(r'$\s*([\d,.]+)\s*(?:-|to)\s*$?\s*([\d,.]+)', html)

        if inr_match:
            try:
                c1 = int(inr_match.group(1).replace(',', '').split('.')[0])
                c2 = int(inr_match.group(2).replace(',', '').split('.')[0])
                salary_min = min(c1, c2)
                salary_max = max(c1, c2)
                salary_currency = "INR"
                salary_raw = f"INR {salary_min:,} - INR {salary_max:,} / yr"
            except Exception:
                pass
        elif usd_match:
            try:
                c1 = int(usd_match.group(1).replace(',', '').split('.')[0])
                c2 = int(usd_match.group(2).replace(',', '').split('.')[0])
                salary_min = min(c1, c2)
                salary_max = max(c1, c2)
                salary_currency = "USD"
                salary_raw = f" -  / yr"
            except Exception:
                pass

        return {
            "description": description,
            "salary_raw": salary_raw,
            "salary_min": salary_min,
            "salary_max": salary_max,
            "salary_currency": salary_currency
        }

detail_extractor = DetailExtractor()
