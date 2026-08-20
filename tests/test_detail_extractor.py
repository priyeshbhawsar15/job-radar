from pathlib import Path

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
