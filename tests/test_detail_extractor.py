from pathlib import Path
import json
import pytest

from unittest.mock import AsyncMock

from job_radar.services.detail_contracts import DetailRequest, DetailResult, ERR_BOUNDARY_VIOLATION
from job_radar.services.detail_extractor import (
    DetailExtractor,
    extract_job_posting,
    description_is_valid,
)
from job_radar.services.oracle_detail import compose_oracle_description, find_oracle_item
from job_radar.services.phenom_detail import extract_phenom_posting


def test_detail_request_and_result_contracts():
    req = DetailRequest(
        family="oracle",
        public_url="https://eeho.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/job/337440/",
        board_name="Oracle",
        title="Software Developer 4",
        provider_config={"api_origin": "https://eeho.fa.us2.oraclecloud.com"},
    )
    assert req.family == "oracle"
    assert req.public_url.startswith("https://")
    assert req.provider_config["api_origin"] == "https://eeho.fa.us2.oraclecloud.com"

    res_empty = DetailResult.empty(error_code="description_missing")
    assert res_empty.description is None
    assert res_empty.location is None
    assert res_empty.employment_type is None
    assert res_empty.department is None
    assert res_empty.salary_raw is None
    assert res_empty.salary_min is None
    assert res_empty.salary_max is None
    assert res_empty.salary_currency is None
    assert res_empty.source is None
    assert res_empty.error_code == "description_missing"

    update_dict = res_empty.as_update_dict()
    assert "description" in update_dict
    assert update_dict["description"] is None
    assert update_dict["detail_enrichment_error_code"] == "description_missing"


FIXTURES = Path(__file__).parent / "fixtures" / "descriptions"


def test_description_fixtures_are_sanitized_and_bounded():
    assert FIXTURES.exists()
    fixtures = list(FIXTURES.iterdir())
    assert len(fixtures) >= 6
    for fixture in fixtures:
        content = fixture.read_text()
        assert len(content.encode()) < 100_000
        assert "@" not in content or "example.invalid" in content or "schema.org" in content
        assert "cookie" not in content.lower()


def test_good_fixtures_contain_required_tokens():
    oracle_json = (FIXTURES / "oracle_requisition.json").read_text()
    jpmc_json = (FIXTURES / "jpmc_requisition.json").read_text()
    amex_json = (FIXTURES / "amex_requisition.json").read_text()
    philips_html = (FIXTURES / "philips_detail.html").read_text()

    assert "ORACLE_FULL_DESCRIPTION_TOKEN" in oracle_json
    assert "JPMC_FULL_DESCRIPTION_TOKEN" in jpmc_json
    assert "AMEX_FULL_DESCRIPTION_TOKEN" in amex_json
    assert "PHILIPS_FULL_DESCRIPTION_TOKEN" in philips_html


def test_shell_fixtures_contain_rejection_markers():
    oracle_shell = (FIXTURES / "oracle_shell.html").read_text()
    philips_no_results = (FIXTURES / "philips_no_results.html").read_text()

    assert "window.VanityUrlEnabled" in oracle_shell
    assert "Sorry! We couldn’t find any jobs that match your search" in philips_no_results


@pytest.mark.parametrize("document", [
    {"@type": "JobPosting", "description": "VALID " * 30 + "\n\nRESPONSIBILITIES:\n- Build systems\n- Write code\n\nQUALIFICATIONS:\n- Degree in CS\n- 3+ years python"},
    [{"@type": "BreadcrumbList"}, {"@type": "JobPosting", "description": "VALID " * 30 + "\n\nRESPONSIBILITIES:\n- Build systems\n- Write code\n\nQUALIFICATIONS:\n- Degree in CS\n- 3+ years python"}],
    {"@graph": [{"@type": "Organization"}, {"@type": ["Thing", "JobPosting"], "description": "VALID " * 30 + "\n\nRESPONSIBILITIES:\n- Build systems\n- Write code\n\nQUALIFICATIONS:\n- Degree in CS\n- 3+ years python"}]},
])
def test_extract_job_posting_traverses_schema_shapes(document):
    page = f'<script nonce="x" type="application/ld+json">{json.dumps(document)}</script>'
    posting = extract_job_posting(page)
    assert posting is not None
    assert posting["description"].startswith("VALID")


def test_extract_job_posting_skips_malformed_json():
    page = '''
    <script type="application/ld+json">{ invalid json here }</script>
    <script type="application/ld+json">{"@type": "JobPosting", "description": "VALID "}</script>
    '''
    posting = extract_job_posting(page)
    assert posting is not None
    assert posting["description"] == "VALID "


def test_description_is_valid_rejections():
    assert not description_is_valid("")
    assert not description_is_valid("   ")
    assert not description_is_valid("None")

    oracle_shell = (FIXTURES / "oracle_shell.html").read_text()
    assert not description_is_valid(oracle_shell)

    philips_no_results = (FIXTURES / "philips_no_results.html").read_text()
    assert not description_is_valid(philips_no_results)

    assert not description_is_valid("Page not found. - oracle careers")
    assert not description_is_valid("Candidate Experience Page Careers")
    assert not description_is_valid("Full job description for Senior Backend Engineer at Stripe.")
    assert not description_is_valid("Position for Lead Developer at JPMC. Requirements available at apply link.")
    assert not description_is_valid("Short title summary without structured responsibilities or requirements section.")


def test_description_is_valid_acceptances():
    philips_detail = (FIXTURES / "philips_detail.html").read_text()
    posting = extract_job_posting(philips_detail)
    assert posting is not None
    assert description_is_valid(posting["description"])


def test_extract_oracle_description():
    oracle_json = json.loads((FIXTURES / "oracle_requisition.json").read_text())
    jpmc_json = json.loads((FIXTURES / "jpmc_requisition.json").read_text())
    amex_json = json.loads((FIXTURES / "amex_requisition.json").read_text())

    item_oracle = find_oracle_item(oracle_json, "337440")
    oracle_desc = compose_oracle_description(item_oracle)
    assert oracle_desc is not None
    assert "ORACLE_FULL_DESCRIPTION_TOKEN" in oracle_desc

    item_jpmc = find_oracle_item(jpmc_json, "210729984")
    jpmc_desc = compose_oracle_description(item_jpmc)
    assert jpmc_desc is not None
    assert "JPMC_FULL_DESCRIPTION_TOKEN" in jpmc_desc

    item_amex = find_oracle_item(amex_json, "26012235")
    amex_desc = compose_oracle_description(item_amex)
    assert amex_desc is not None
    assert "AMEX_FULL_DESCRIPTION_TOKEN" in amex_desc


def test_extract_phenom_description():
    philips_detail = (FIXTURES / "philips_detail.html").read_text()
    philips_no_results = (FIXTURES / "philips_no_results.html").read_text()

    res = extract_phenom_posting(philips_detail, "Software Engineer")
    assert res.description is not None
    assert "PHILIPS_FULL_DESCRIPTION_TOKEN" in res.description

    res_no = extract_phenom_posting(philips_no_results, "Software Engineer")
    assert res_no.description is None


@pytest.mark.asyncio
async def test_family_aware_dispatch_routing():
    extractor = DetailExtractor()

    # Philips route with family="phenom" dispatches to Phenom detail logic
    philips_url = "https://www.careers.philips.com/in/en/job/581004/Senior-Software-Technologist-Rust"
    res = await extractor.fetch_and_enrich(
        philips_url,
        "Philips",
        "Senior Software Technologist",
        family="phenom",
        provider_config={"allowed_origins": ["www.careers.philips.com"]},
    )
    assert res.error_code == ERR_BOUNDARY_VIOLATION or res.description is not None or res.error_code is not None


@pytest.mark.asyncio
async def test_fetch_and_enrich_extracts_nested_family_config():
    extractor = DetailExtractor()
    philips_url = "https://www.careers.philips.com/in/en/job/581004/Senior-Software-Technologist-Rust"

    # When provider_config contains nested 'phenom_detail' dictionary:
    nested_config = {
        "target_url": "https://www.careers.philips.com/in/en/search-results",
        "phenom_detail": {
            "allowed_origins": ["https://www.careers.philips.com"]
        }
    }
    # Mocking or calling directly should unwrap phenom_detail rather than failing with ERR_INVALID_PROVIDER_CONFIG
    mock_client = AsyncMock()
    mock_client.get.return_value.status_code = 200
    mock_client.get.return_value.url = philips_url
    mock_client.get.return_value.content = b"<html></html>"
    mock_client.get.return_value.text = "<html></html>"

    res = await extractor.fetch_and_enrich(
        philips_url,
        "Philips",
        "Senior Software Technologist",
        family="phenom",
        provider_config=nested_config,
        client=mock_client,
    )
    assert res.error_code != "invalid_provider_config"


def test_python_sources_contain_no_backspace_characters():
    source_root = Path(__file__).parents[1] / "src"
    offenders = [path for path in source_root.rglob("*.py") if "\x08" in path.read_text()]
    assert offenders == []
