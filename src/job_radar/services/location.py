"""Global India Eligibility Classifier for Job Radar candidates."""

import re
from typing import Optional, Tuple, Set

INDIAN_LOCATION_KEYWORDS: Set[str] = {
    "india", "bengaluru", "bangalore", "hyderabad", "gurgaon",
    "gurugram", "noida", "pune", "chennai", "mumbai", "delhi", "new delhi",
    "ncr", "ahmedabad", "kolkata", "jaipur", "indore", "kochi", "cochin",
    "trivandrum", "thiruvananthapuram", "chandigarh", "mohali", "coimbatore",
    "vadodara", "surat", "nagpur", "bhubaneswar", "karnataka", "telangana",
    "maharashtra", "haryana", "tamil nadu", "kerala", "uttar pradesh",
    "gujarat", "rajasthan", "punjab", "west bengal", "odisha"
}

GENERIC_LOCATION_KEYWORDS: Set[str] = {
    "", "unknown", "n/a", "na", "remote", "anywhere", "worldwide", "global", "flexible"
}


def is_india_eligible(location: Optional[str]) -> Tuple[bool, Optional[str]]:
    """
    Evaluates whether a candidate location is eligible for India processing.

    Returns:
        (is_eligible: bool, exclusion_reason: Optional[str])
    """
    if location is None:
        return True, None

    loc_str = location.strip()
    loc_clean = loc_str.lower()

    if not loc_clean or loc_clean in GENERIC_LOCATION_KEYWORDS:
        return True, None

    # Check multi-word Indian region/city keywords
    if any(kw in loc_clean for kw in ["new delhi", "delhi ncr", "tamil nadu", "uttar pradesh", "west bengal"]):
        return True, None

    tokens = set(re.split(r'[^a-zA-Z0-9]+', loc_clean))

    # If location is purely generic tokens (e.g. "remote", "work from home", "hybrid") without specific country
    if tokens.issubset(GENERIC_LOCATION_KEYWORDS | {"work", "from", "home", "office", "hybrid"}):
        return True, None

    # Check single-word Indian keywords
    if any(tok in INDIAN_LOCATION_KEYWORDS for tok in tokens):
        return True, None

    # Exact country code match for "IN" or "IND"
    if loc_str.upper() in ("IN", "IND"):
        return True, None

    # Structured country code pattern: e.g. ", IN", "(IN)", "[IN]", " - IN", ", IN," or terminal ", in" / ", ind"
    if re.search(r'(?:,\s*|\(\s*|\[\s*|-\s*|/\s*)\b(IN|IND)\b(?:\s*,|\s*\)|\s*\]|\s*-|\s*/|$)', loc_str):
        return True, None

    if re.search(r',\s*(?:in|ind)\s*$', loc_clean):
        return True, None

    # Non-empty location without India match -> Excluded
    return False, f"NON_INDIA_LOCATION: {loc_str[:100]}"
