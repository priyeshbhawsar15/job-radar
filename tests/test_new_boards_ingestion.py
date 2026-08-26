import json
from pathlib import Path
import pytest

from job_radar.adapters.registry import adapter_registry
from job_radar.db.seed import INITIAL_BOARDS, BLOCKED_BOARD_IDS
from job_radar.services.location import is_india_eligible
from job_radar.services.detail_extractor import description_is_valid

FIXTURES_DIR = Path("tests/fixtures")
NEW_BOARDS = INITIAL_BOARDS[37:]

# Map of board names to fixture relative path under tests/fixtures/
BOARD_FIXTURE_MAP = {
    "JLL": "workday/jll.json",
    "Razorpay": "greenhouse/razorpay.json",
    "SOTI": "workday/soti.json",
    "Amgen": "workday/amgen.json",
    "Paytm": "lever/paytm.json",
    "Uber": "custom/uber.json",
    "GoDaddy": "greenhouse/godaddy.json",
    "PhonePe": "greenhouse/phonepe.json",
    "Buffer": "ashby/buffer.json",
    "Sourcegraph": "greenhouse/sourcegraph91.json",
    "Zapier": "ashby/zapier.json",
    "Remote.com": "greenhouse/remote.json",
    "Elastic": "custom/elastic.json",
    "Twilio": "greenhouse/twilio.json",
    "Supabase": "ashby/supabase.json",
    "Bitwarden": "greenhouse/bitwarden.json",
    "Camunda": "ashby/camunda.json",
    "Zoho": "zoho/zoho.json",
    "Postman": "greenhouse/postman.json",
    "BrowserStack": "workday/browserstack.json",
    "Atlan": "ashby/atlan.json",
    "Redis": "ashby/redis.json",
    "Springworks": "custom/springworks.json",
    "Groww": "greenhouse/groww.json",
    "Snowflake": "phenom/snowflake.json",
    "Databricks": "greenhouse/databricks.json",
    "Okta": "greenhouse/okta.json",
    "Coinbase": "greenhouse/coinbase.json",
    "Salesforce": "workday/salesforce.json",
    "SAP": "phenom/sap.json",
    "Workday": "workday/workdaycorp.json",
    "VMware": "smartrecruiters/vmware.json",
    "Intel": "workday/intel.json",
    "Airbnb": "greenhouse/airbnb.json",
    "Meesho": "custom/meesho.json",
    "BlackRock": "phenom/blackrock.json",
    "UiPath": "custom/uipath.json",
    "Druva": "greenhouse/druva.json",
    "EPAM Systems": "custom/epam_systems.json",
}


def test_65_new_boards_inventory_totals():
    assert len(NEW_BOARDS) == 65
    assert len(INITIAL_BOARDS) == 102
    assert len(BOARD_FIXTURE_MAP) == 39
    assert len(BLOCKED_BOARD_IDS) == 26


@pytest.mark.parametrize("board_tuple", [b for b in NEW_BOARDS if b[1] in BOARD_FIXTURE_MAP], ids=lambda b: b[1])
def test_reviewed_board_contract(board_tuple):
    b_id, name, family, target_url = board_tuple[0], board_tuple[1], board_tuple[2], board_tuple[3]
    rel_path = BOARD_FIXTURE_MAP[name]
    fixture_path = FIXTURES_DIR / rel_path

    assert fixture_path.exists(), f"Sanitized live fixture missing for reviewed board {name} at {fixture_path}"

    payload_text = fixture_path.read_text()

    adapter = adapter_registry.get(family)
    assert adapter is not None, f"Adapter for family '{family}' not found in registry"

    extracted = adapter.parse_raw_payload(
        payload=payload_text,
        board_name=name,
        target_url=target_url
    )

    assert isinstance(extracted, list), f"Expected list of ExtractedCandidate for {name}"
    assert len(extracted) > 0, f"Expected at least 1 extracted candidate for {name}"

    for candidate in extracted:
        assert candidate.title and len(candidate.title) > 3, f"Invalid title '{candidate.title}' for {name}"
        assert candidate.company == name, f"Mismatch company for {name}"
        assert candidate.raw_url.startswith("http"), f"Invalid raw_url '{candidate.raw_url}' for {name}"
        assert not candidate.raw_url.endswith(".css"), f"Canonical URL is a CSS asset for {name}"
        assert candidate.fingerprint, f"Candidate missing fingerprint for {name}"

        # Test India Gate classification
        is_eligible, reason = is_india_eligible(candidate.location)
        if is_eligible:
            assert reason is None
        else:
            assert reason is not None
            assert "NON_INDIA_LOCATION" in reason


@pytest.mark.parametrize("board_tuple", [b for b in NEW_BOARDS if b[0] in BLOCKED_BOARD_IDS], ids=lambda b: b[1])
def test_blocked_draft_board_registration(board_tuple):
    b_id, name, family, target_url = board_tuple[0], board_tuple[1], board_tuple[2], board_tuple[3]
    assert b_id in BLOCKED_BOARD_IDS, f"Board {name} ({b_id}) must be registered as draft/blocked"
