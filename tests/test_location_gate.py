import pytest
from job_radar.services.location import is_india_eligible


@pytest.mark.parametrize(
    "location,expected_eligible",
    [
        (None, True),
        ("", True),
        ("   ", True),
        ("Unknown", True),
        ("N/A", True),
        ("Remote", True),
        ("Global", True),
        ("Flexible", True),
        ("India", True),
        ("INDIA", True),
        ("Bangalore", True),
        ("Bengaluru, India", True),
        ("Hyderabad, Telangana", True),
        ("Gurgaon, Haryana", True),
        ("Gurugram", True),
        ("Noida, UP", True),
        ("Pune, Maharashtra", True),
        ("Chennai, Tamil Nadu", True),
        ("Mumbai", True),
        ("New Delhi", True),
        ("Delhi NCR", True),
        ("Bengaluru, IN", True),
        ("India - Remote", True),
        ("London, UK; Bangalore, India", True),
        ("Remote - India", True),
        ("Hybrid - Bangalore", True),
        ("Remote in Europe", False),
        ("Based in London", False),
        ("San Francisco, CA", False),
        ("London, UK", False),
        ("New York, NY, USA", False),
        ("United States", False),
        ("Seattle, WA", False),
        ("Tokyo, Japan", False),
        ("Berlin, Germany", False),
        ("Remote - US", False),
        ("Austin, TX", False),
    ]
)
def test_is_india_eligible(location, expected_eligible):
    eligible, reason = is_india_eligible(location)
    assert eligible == expected_eligible
    if expected_eligible:
        assert reason is None
    else:
        assert reason is not None
        assert "NON_INDIA_LOCATION" in reason
