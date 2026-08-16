import json
import pytest
from job_radar.adapters.registry import adapter_registry
from job_radar.services.browser import validate_target_url, TargetBoundaryViolation

def test_registry_has_default_adapters():
  families = adapter_registry.list_families()
  assert "greenhouse" in families
  assert "lever" in families
  assert "ashby" in families
  assert "workday" in families

def test_greenhouse_adapter_parsing():
  adapter = adapter_registry.get("greenhouse")
  assert adapter is not None

  payload = json.dumps({
    "jobs": [
      {
        "id": 12345,
        "title": "Senior Backend Engineer",
        "absolute_url": "https://boards.greenhouse.io/stripe/jobs/12345",
        "location": {"name": "San Francisco, CA"},
        "departments": [{"name": "Engineering"}]
      }
    ]
  })

  candidates = adapter.parse_raw_payload(payload, "Stripe", "https://boards.greenhouse.io/stripe")
  assert len(candidates) == 1
  c = candidates[0]
  assert c.title == "Senior Backend Engineer"
  assert c.company == "Stripe"
  assert c.location == "San Francisco, CA"
  assert c.department == "Engineering"
  assert c.fingerprint is not None

def test_target_boundary_validation():
  # Valid host match
  assert validate_target_url(
    "https://boards.greenhouse.io/stripe/jobs/123",
    "https://boards.greenhouse.io/stripe"
  ) is True

  # Mismatched host violation
  with pytest.raises(TargetBoundaryViolation):
    validate_target_url(
      "https://malicious-site.com/jobs",
      "https://boards.greenhouse.io/stripe"
    )

  # Invalid scheme violation
  with pytest.raises(TargetBoundaryViolation):
    validate_target_url("file:///etc/passwd")
