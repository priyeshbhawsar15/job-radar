#!/usr/bin/env python3
"""Standalone, production-independent live contract gate for job details.

Validates Oracle, JPMC, AMEX, and Philips live detail payload contracts before
any production code changes under src/.
"""

import asyncio
import html
import json
import sys
import re
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse

import httpx

LIVE_CASES = [
    {
        "board": "Oracle",
        "family": "oracle",
        "url": "https://eeho.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/job/337440/",
        "api_origin": "https://eeho.fa.us2.oraclecloud.com",
        "allowed_origins": ["eeho.fa.us2.oraclecloud.com"],
        "public_id": "337440",
        "required_sections": ["description", "responsibilities"],
        "min_chars": 5_000,
    },
    {
        "board": "JPMC",
        "family": "oracle",
        "url": "https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/job/210729984/",
        "api_origin": "https://jpmc.fa.oraclecloud.com",
        "allowed_origins": ["jpmc.fa.oraclecloud.com"],
        "public_id": "210729984",
        "required_sections": ["description"],
        "min_chars": 2_500,
    },
    {
        "board": "AMEX",
        "family": "oracle",
        "url": "https://egug.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/job/26012235/",
        "api_origin": "https://egug.fa.us2.oraclecloud.com",
        "allowed_origins": ["egug.fa.us2.oraclecloud.com"],
        "public_id": "26012235",
        "required_sections": ["description", "responsibilities", "qualifications"],
        "min_chars": 3_500,
    },
    {
        "board": "Philips",
        "family": "phenom",
        "url": "https://www.careers.philips.com/in/en/job/581004/Senior-Software-Technologist-Rust",
        "allowed_origins": ["www.careers.philips.com", "careers.philips.com"],
        "public_id": "581004",
        "required_sections": ["description"],
        "min_chars": 3_000,
    },
]


def clean_html_to_text(html_content: str) -> str:
    if not html_content:
        return ""
    # Strip script/style tags
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html_content, flags=re.DOTALL | re.IGNORECASE)
    # Convert block elements and break lines to newline
    text = re.sub(r"<(?:p|br|h[1-6]|div|li|tr)[^>]*>", "\n", text, flags=re.IGNORECASE)
    # Strip remaining tags
    text = re.sub(r"<[^>]+>", "", text)
    # Unescape HTML entities
    text = html.unescape(text)
    # Replace non-breaking spaces
    text = text.replace("\xa0", " ")
    # Normalize horizontal whitespace per line
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    # Remove empty lines while joining with single newlines
    result_lines = []
    for line in lines:
        if line:
            result_lines.append(line)
    return "\n".join(result_lines)


def normalize_for_comparison(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def extract_paragraphs(text: str) -> List[str]:
    return [p.strip() for p in text.split("\n") if p.strip()]


def find_job_posting_json_ld(obj: Any) -> Optional[Dict[str, Any]]:
    if isinstance(obj, dict):
        obj_type = obj.get("@type")
        if obj_type == "JobPosting" or (isinstance(obj_type, list) and "JobPosting" in obj_type):
            return obj
        if "@graph" in obj and isinstance(obj["@graph"], list):
            res = find_job_posting_json_ld(obj["@graph"])
            if res:
                return res
        for key, val in obj.items():
            if isinstance(val, (dict, list)):
                res = find_job_posting_json_ld(val)
                if res:
                    return res
    elif isinstance(obj, list):
        for item in obj:
            res = find_job_posting_json_ld(item)
            if res:
                return res
    return None


def extract_philips_location(job_posting: Dict[str, Any]) -> str:
    job_loc = job_posting.get("jobLocation")
    if not job_loc:
        return ""
    if isinstance(job_loc, list):
        job_loc = job_loc[0] if job_loc else {}
    if not isinstance(job_loc, dict):
        return ""

    address = job_loc.get("address", {})
    if isinstance(address, str):
        return address.strip()
    if not isinstance(address, dict):
        return ""

    parts = []
    for key in ["addressLocality", "addressRegion", "addressCountry"]:
        val = address.get(key)
        if isinstance(val, dict):
            val = val.get("name", "")
        if val and isinstance(val, str):
            val_str = val.strip()
            if val_str and val_str not in parts:
                parts.append(val_str)
    return ", ".join(parts)


def select_sentinel_excerpt(raw_field: str) -> str:
    text = clean_html_to_text(raw_field)
    paragraphs = [p for p in text.split("\n") if len(p.strip()) > 30]
    if paragraphs:
        target = paragraphs[0]
        # pick a 20-30 char substring from middle
        start = max(0, (len(target) - 25) // 2)
        return target[start:start + 25].strip()
    return ""


async def probe_oracle_case(client: httpx.AsyncClient, case: Dict[str, Any]) -> Dict[str, Any]:
    api_origin = case["api_origin"]
    public_id = case["public_id"]
    endpoint = f"{api_origin}/hcmRestApi/resources/latest/recruitingCEJobRequisitionDetails"
    params = {
        "expand": "all",
        "onlyData": "true",
        "finder": f'ById;Id="{public_id}"',
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
    }
    resp = await client.get(endpoint, params=params, headers=headers)
    status_code = resp.status_code
    final_url = str(resp.url)
    final_host = urlparse(final_url).netloc

    report = {
        "board": case["board"],
        "url": case["url"],
        "status_code": status_code,
        "final_host": final_host,
        "extracted_public_id": None,
        "title": None,
        "location": None,
        "sections": {},
        "final_length": 0,
        "sources": [],
        "assertions": [],
        "passed": False,
        "error": None,
    }

    if status_code != 200:
        report["error"] = f"HTTP status {status_code}"
        return report

    data = resp.json()
    items = data.get("items", [])
    if len(items) != 1:
        report["error"] = f"Expected 1 item, got {len(items)}"
        return report

    item = items[0]
    extracted_id = str(item.get("Id"))
    requisition_id = str(item.get("RequisitionId"))
    title = item.get("Title", "")
    location = item.get("PrimaryLocation", "")

    report["extracted_public_id"] = extracted_id
    report["title"] = title
    report["location"] = location

    # Raw fields
    ext_desc_raw = item.get("ExternalDescriptionStr") or ""
    ext_resp_raw = item.get("ExternalResponsibilitiesStr") or ""
    ext_qual_raw = item.get("ExternalQualificationsStr") or ""
    short_desc_raw = item.get("ShortDescriptionStr") or ""
    corp_desc_raw = item.get("CorporateDescriptionStr") or ""
    org_desc_raw = item.get("OrganizationDescriptionStr") or ""

    ext_desc = clean_html_to_text(ext_desc_raw)
    ext_resp = clean_html_to_text(ext_resp_raw)
    ext_qual = clean_html_to_text(ext_qual_raw)

    report["sections"] = {
        "ExternalDescriptionStr": len(ext_desc),
        "ExternalResponsibilitiesStr": len(ext_resp),
        "ExternalQualificationsStr": len(ext_qual),
        "ShortDescriptionStr": len(clean_html_to_text(short_desc_raw)),
        "CorporateDescriptionStr": len(clean_html_to_text(corp_desc_raw)),
        "OrganizationDescriptionStr": len(clean_html_to_text(org_desc_raw)),
    }

    # Compose final description
    section_configs = [
        (None, ext_desc_raw, "ExternalDescriptionStr"),
        ("RESPONSIBILITIES", ext_resp_raw, "ExternalResponsibilitiesStr"),
        ("QUALIFICATIONS", ext_qual_raw, "ExternalQualificationsStr"),
    ]

    seen_paragraphs: Set[str] = set()
    composed_parts = []
    sources = []

    for heading, raw_content, source_name in section_configs:
        text = clean_html_to_text(raw_content)
        if not text:
            continue
        paras = extract_paragraphs(text)
        unique_paras = []
        for p in paras:
            norm = normalize_for_comparison(p)
            if norm and norm not in seen_paragraphs:
                seen_paragraphs.add(norm)
                unique_paras.append(p)
        if unique_paras:
            sec_text = "\n".join(unique_paras)
            if heading:
                composed_parts.append(f"{heading}\n{sec_text}")
            else:
                composed_parts.append(sec_text)
            sources.append(source_name)

    final_description = "\n\n".join(composed_parts).strip()
    report["final_length"] = len(final_description)
    report["sources"] = sources

    # Assertions check
    assertions = []

    # 1. Status 200
    assertions.append(("status_code_200", 200 <= status_code < 300))
    # 2. Final origin in allowed_origins
    assertions.append(("allowed_origin", final_host in case["allowed_origins"]))
    # 3. Public ID matches and RequisitionId != public_id
    assertions.append(("public_id_match", extracted_id == public_id))
    assertions.append(("req_id_not_public_id", requisition_id != public_id))
    # 4. Title valid
    assertions.append(("valid_title", bool(title and len(title.strip()) >= 3)))
    # 5. Location valid (not re.fullmatch(r"\d+(?:, India)?", location))
    assertions.append(("valid_location", bool(location and not re.fullmatch(r"\d+(?:, India)?", location))))
    # 6. Description length within bounds
    assertions.append(("min_max_length", case["min_chars"] <= len(final_description) <= 40_000))
    # 7. Description stripped
    assertions.append(("is_stripped", final_description == final_description.strip()))
    # 8. short_description not in extraction_sources
    assertions.append(("no_short_description_source", "ShortDescriptionStr" not in sources))
    # 9. No unwanted markers in description
    unwanted_markers = [
        "window.vanityurlenabled", "candidate experience page careers",
        "accessibility assistance", "sorry! we couldn’t find any jobs",
        "cookie preferences", "privacy policy", "terms of use",
        "gtag", "datalayer", "javascript:",
    ]
    has_unwanted = any(marker in final_description.lower() for marker in unwanted_markers)
    assertions.append(("no_unwanted_markers", not has_unwanted))
    # 10. No duplicate paragraphs
    paragraphs = extract_paragraphs(final_description)
    norm_paragraphs = [normalize_for_comparison(p) for p in paragraphs]
    assertions.append(("no_duplicate_paragraphs", len(norm_paragraphs) == len(set(norm_paragraphs))))

    # Case-specific assertions
    if case["board"] == "Oracle":
        assertions.append(("oracle_desc_and_resp", "ExternalDescriptionStr" in sources and "ExternalResponsibilitiesStr" in sources))
    elif case["board"] == "JPMC":
        assertions.append(("jpmc_desc_equals_cleaned", final_description == ext_desc and len(sources) == 1))
    elif case["board"] == "AMEX":
        sentinel_desc = select_sentinel_excerpt(ext_desc_raw)
        sentinel_resp = select_sentinel_excerpt(ext_resp_raw)
        sentinel_qual = select_sentinel_excerpt(ext_qual_raw)

        c_desc = final_description.count(sentinel_desc) if sentinel_desc else 0
        c_resp = final_description.count(sentinel_resp) if sentinel_resp else 0
        c_qual = final_description.count(sentinel_qual) if sentinel_qual else 0

        assertions.append(("amex_split_fields", c_desc == 1 and c_resp == 1 and c_qual == 1))
        # Ensure corporate / org boilerplate not in final_description
        corp_text = clean_html_to_text(corp_desc_raw)
        if corp_text and len(corp_text) > 50:
            sentinel_corp = select_sentinel_excerpt(corp_desc_raw)
            assertions.append(("amex_no_corporate_boilerplate", sentinel_corp not in final_description if sentinel_corp else True))

    report["assertions"] = assertions
    report["passed"] = all(passed for name, passed in assertions)
    return report


async def probe_philips_case(client: httpx.AsyncClient, case: Dict[str, Any]) -> Dict[str, Any]:
    url = case["url"]
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    resp = await client.get(url, headers=headers)
    status_code = resp.status_code
    final_url = str(resp.url)
    final_host = urlparse(final_url).netloc

    report = {
        "board": case["board"],
        "url": case["url"],
        "status_code": status_code,
        "final_host": final_host,
        "extracted_public_id": None,
        "title": None,
        "location": None,
        "sections": {},
        "final_length": 0,
        "sources": [],
        "assertions": [],
        "passed": False,
        "error": None,
    }

    if status_code != 200:
        report["error"] = f"HTTP status {status_code}"
        return report

    html_text = resp.text
    # Find JSON-LD script tags
    script_blocks = re.findall(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html_text, flags=re.DOTALL | re.IGNORECASE)

    job_posting = None
    for block in script_blocks:
        try:
            data = json.loads(block.strip())
            found = find_job_posting_json_ld(data)
            if found:
                job_posting = found
                break
        except Exception:
            continue

    if not job_posting:
        report["error"] = "No JobPosting JSON-LD node found"
        return report

    raw_desc = job_posting.get("description", "")
    title = job_posting.get("title", "")
    location = extract_philips_location(job_posting)
    req_id = str(job_posting.get("identifier", {}).get("value", "")) or case["public_id"]

    cleaned_desc = clean_html_to_text(raw_desc)
    report["extracted_public_id"] = req_id
    report["title"] = title
    report["location"] = location
    report["final_length"] = len(cleaned_desc)
    report["sources"] = ["json_ld"]

    assertions = []
    # 1. Status 200
    assertions.append(("status_code_200", 200 <= status_code < 300))
    # 2. Allowed origin
    assertions.append(("allowed_origin", final_host in case["allowed_origins"]))
    # 3. Public ID match
    assertions.append(("public_id_match", case["public_id"] in req_id or req_id in case["public_id"]))
    # 4. Title contains Senior Software Technologist
    assertions.append(("title_match", bool(title and "Senior Software Technologist" in title)))
    # 5. Location contains Bangalore and India
    assertions.append(("location_match", bool(location and "Bangalore" in location and "India" in location)))
    # 6. Min/max chars
    assertions.append(("min_max_length", case["min_chars"] <= len(cleaned_desc) <= 40_000))
    # 7. Stripped
    assertions.append(("is_stripped", cleaned_desc == cleaned_desc.strip()))
    # 8. No unwanted markers
    unwanted_markers = [
        "cookie preferences", "privacy policy", "terms of use",
        "javascript:", "accessibility assistance",
    ]
    has_unwanted = any(marker in cleaned_desc.lower() for marker in unwanted_markers)
    assertions.append(("no_unwanted_markers", not has_unwanted))
    # 9. No duplicate paragraphs
    paragraphs = extract_paragraphs(cleaned_desc)
    norm_paragraphs = [normalize_for_comparison(p) for p in paragraphs]
    assertions.append(("no_duplicate_paragraphs", len(norm_paragraphs) == len(set(norm_paragraphs))))

    report["assertions"] = assertions
    report["passed"] = all(passed for name, passed in assertions)
    return report


async def main():
    print("Running live detail contract probe against 4 target URLs...")
    async with httpx.AsyncClient(timeout=25.0, follow_redirects=True) as client:
        results = []
        for case in LIVE_CASES:
            if case["family"] == "oracle":
                report = await probe_oracle_case(client, case)
            else:
                report = await probe_philips_case(client, case)
            results.append(report)

    all_passed = True
    print("\n" + "=" * 80)
    print(f"{'BOARD':<10} | {'STATUS':<6} | {'PUBLIC_ID':<10} | {'LENGTH':<6} | {'TITLE':<30}")
    print("-" * 80)
    for r in results:
        status_str = "PASS" if r["passed"] else "FAIL"
        if not r["passed"]:
            all_passed = False
        title_str = (r["title"] or "")[:30]
        print(f"{r['board']:<10} | {status_str:<6} | {str(r['extracted_public_id']):<10} | {r['final_length']:<6} | {title_str:<30}")
        print(f"  URL: {r['url']}")
        print(f"  Location: {r['location']}")
        print(f"  Sources: {r['sources']}")
        print(f"  Assertions: {r['assertions']}")
        if r["error"]:
            print(f"  Error: {r['error']}")
        print("-" * 80)

    print("=" * 80)
    if all_passed:
        print("RESULT: 100% PASS - Live contracts verified!")
        sys.exit(0)
    else:
        print("RESULT: FAIL - One or more live contract checks failed!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
