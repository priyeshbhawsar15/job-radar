from pathlib import Path
import json
import pytest

from job_radar.services.detail_extractor import (
    iter_json_ld_nodes,
    extract_job_posting,
    description_is_valid,
    extract_oracle_description,
)

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

    oracle_desc = extract_oracle_description(oracle_json, "123456")
    assert oracle_desc is not None
    assert "ORACLE_FULL_DESCRIPTION_TOKEN" in oracle_desc
    assert "SHORT_DESCRIPTION_TOKEN" not in oracle_desc
    assert description_is_valid(oracle_desc)

    jpmc_desc = extract_oracle_description(jpmc_json, "234567")
    assert jpmc_desc is not None
    assert "JPMC_FULL_DESCRIPTION_TOKEN" in jpmc_desc
    assert "SHORT_DESCRIPTION_TOKEN" not in jpmc_desc
    assert description_is_valid(jpmc_desc)

    amex_desc = extract_oracle_description(amex_json, "345678")
    assert amex_desc is not None
    assert "AMEX_FULL_DESCRIPTION_TOKEN" in amex_desc
    assert "SHORT_DESCRIPTION_TOKEN" not in amex_desc
    assert description_is_valid(amex_desc)

    # Mismatched Requisition ID
    assert extract_oracle_description(oracle_json, "999999") is None

    # Invalid wrapper shape
    assert extract_oracle_description({"items": []}, "123456") is None
    assert extract_oracle_description({}, "123456") is None

    # Short description only
    short_json = {"items": [{"RequisitionId": 123456, "ShortDescription": "SHORT_DESCRIPTION_TOKEN"}]}
    assert extract_oracle_description(short_json, "123456") is None


def test_python_sources_contain_no_backspace_characters():
    source_root = Path(__file__).parents[1] / "src"
    offenders = [path for path in source_root.rglob("*.py") if "\x08" in path.read_text()]
    assert offenders == []
