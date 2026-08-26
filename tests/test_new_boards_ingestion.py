import json
import re
from pathlib import Path
import pytest

from job_radar.adapters.registry import adapter_registry
from job_radar.db.seed import INITIAL_BOARDS, BLOCKED_BOARD_IDS
from job_radar.services.location import is_india_eligible
from job_radar.services.detail_extractor import description_is_valid

FIXTURES_DIR = Path("tests/fixtures")
NEW_BOARDS = INITIAL_BOARDS[37:]

GENERIC_TITLE_RE = re.compile(
    r'^(.* Role|.* Position|Custom Role|Phenom Role|Zoho Careers Position)$',
    re.IGNORECASE,
)

# Map of 27 reviewed new boards to fixture relative path under tests/fixtures/
BOARD_FIXTURE_MAP = {
    "JLL": "workday/jll.json",
    "Razorpay": "greenhouse/razorpay.json",
    "Amgen": "workday/amgen.json",
    "Paytm": "lever/paytm.json",
    "Gitlab": "greenhouse/gitlab.json",
    "GoDaddy": "greenhouse/godaddy.json",
    "PhonePe": "greenhouse/phonepe.json",
    "Buffer": "ashby/buffer.json",
    "Sourcegraph": "greenhouse/sourcegraph91.json",
    "Twilio": "greenhouse/twilio.json",
    "Supabase": "ashby/supabase.json",
    "Bitwarden": "greenhouse/bitwarden.json",
    "Camunda": "ashby/camunda.json",
    "Postman": "greenhouse/postman.json",
    "BrowserStack": "workday/browserstack.json",
    "Atlan": "ashby/atlan.json",
    "Redis": "ashby/redis.json",
    "Groww": "greenhouse/groww.json",
    "Databricks": "greenhouse/databricks.json",
    "Okta": "greenhouse/okta.json",
    "CrowdStrike": "workday/crowdstrike.json",
    "Coinbase": "greenhouse/coinbase.json",
    "Salesforce": "workday/salesforce.json",
    "VMware": "smartrecruiters/vmware.json",
    "Intel": "workday/intel.json",
    "Airbnb": "greenhouse/airbnb.json",
    "Druva": "greenhouse/druva.json",
    "TMUS": "talent500/tmus.json",
    "Best Buy": "talent500/bestbuy.json",
    "Evernorth": "talent500/evernorth.json",
    "Marriott Tech": "talent500/marriotttech.json",
    "McD": "talent500/mcd.json",
    "Regal Rexnord": "workday/regalrexnord.json",
}


def test_66_new_boards_inventory_totals():
    assert len(NEW_BOARDS) == 66
    assert len(INITIAL_BOARDS) == 103
    assert len(BOARD_FIXTURE_MAP) == 33
    assert len(BLOCKED_BOARD_IDS) == 39


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
        assert not GENERIC_TITLE_RE.match(candidate.title), f"Generic/placeholder title '{candidate.title}' forbidden for {name}"
        assert candidate.company == name or candidate.company.startswith(name) or name in candidate.company, f"Mismatch company for {name}"
        assert candidate.raw_url.startswith("http"), f"Invalid raw_url '{candidate.raw_url}' for {name}"
        assert not candidate.raw_url.endswith(".css"), f"Canonical URL is a CSS asset for {name}"
        assert candidate.fingerprint, f"Candidate missing fingerprint for {name}"

        # Assert substantive detail text exists in extra_payload or description
        desc = candidate.extra_payload.get("description")
        if desc:
            assert len(desc) >= 200, f"Description too short (<200 chars) for candidate in {name}"
            assert description_is_valid(desc, title=candidate.title), f"Invalid description quality for candidate in {name}"

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
