"""Global India Eligibility Classifier for Job Radar candidates."""

import re
from typing import Optional, Tuple, Set

INDIAN_LOCATION_KEYWORDS: Set[str] = {
    "india", "ind", "bengaluru", "bangalore", "hyderabad", "gurgaon", 
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

    # Check for word boundary tokens or direct substring matches for multi-word regions
    # First check multi-word Indian keywords
    if "new delhi" in loc_clean or "tamil nadu" in loc_clean or "uttar pradesh" in loc_clean or "west bengal" in loc_clean:
        return True, None

    tokens = set(re.split(r'[^a-zA-Z0-9]+', loc_clean))
    
    # Check single word Indian keywords
    if any(tok in INDIAN_LOCATION_KEYWORDS for tok in tokens):
        return True, None

    # Check standalone uppercase/lowercase "in" token as country code (e.g. "IN", "Bengaluru, IN")
    if "in" in tokens:
        return True, None

    # If all tokens are generic (e.g. "remote", "flexible", "work from home") without explicit non-India country
    if tokens.issubset(GENERIC_LOCATION_KEYWORDS | {"work", "from", "home", "office", "hybrid"}):
        return True, None

    # Non-empty location with no Indian keywords -> Excluded
    return False, f"NON_INDIA_LOCATION: {loc_str[:100]}"
