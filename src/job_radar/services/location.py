"""Global Location Decision & India Eligibility Classifier for Job Radar candidates."""

import re
from dataclasses import dataclass
from typing import Optional, Tuple, Set, List


class LocationDecision:
    INDIA = "INDIA"
    NON_INDIA = "NON_INDIA"
    UNKNOWN = "UNKNOWN"
    CONFLICT = "CONFLICT"


@dataclass
class LocationDecisionResult:
    decision: str
    eligible: bool
    reason: Optional[str] = None
    evidence: Optional[str] = None
    confidence: Optional[str] = None


INDIAN_CITIES_HUB: Set[str] = {
    "bengaluru", "bangalore", "hyderabad", "gurgaon", "gurugram", "noida",
    "pune", "chennai", "mumbai", "delhi", "new delhi", "ncr", "ahmedabad",
    "kolkata", "jaipur", "indore", "kochi", "cochin", "trivandrum",
    "thiruvananthapuram", "chandigarh", "mohali", "coimbatore", "vadodara",
    "surat", "nagpur", "bhubaneswar", "ghaziabad", "faridabad", "mysore",
    "mysuru", "visakhapatnam", "vizag"
}

INDIAN_STATES: Set[str] = {
    "karnataka", "telangana", "maharashtra", "haryana", "tamil nadu",
    "kerala", "uttar pradesh", "gujarat", "rajasthan", "punjab",
    "west bengal", "odisha", "andhra pradesh", "madhya pradesh"
}

INDIAN_STATE_CODES: Set[str] = {
    "KA", "TS", "TG", "MH", "HR", "TN", "UP", "DL", "GJ", "RJ",
    "PB", "WB", "OR", "OD", "AP", "MP", "KL"
}

FOREIGN_COUNTRIES_REGIONS: Set[str] = {
    "united states", "usa", "us", "united kingdom", "uk", "canada",
    "australia", "germany", "france", "singapore", "japan", "china",
    "brazil", "netherlands", "poland", "ireland", "spain", "italy",
    "switzerland", "sweden", "romania", "mexico", "philippines", "vietnam",
    "europe", "emea", "apac", "latam", "americas", "north america", "south america"
}

FOREIGN_CITIES: Set[str] = {
    "london", "new york", "san francisco", "san jose", "seattle", "austin",
    "chicago", "boston", "toronto", "vancouver", "montreal", "sydney",
    "melbourne", "berlin", "munich", "frankfurt", "paris", "tokyo",
    "shanghai", "beijing", "amsterdam", "dublin", "warsaw",
    "bucharest", "zurich", "geneva", "sao paulo", "buenos aires", "tel aviv",
    "dubai"
}

FOREIGN_COUNTRY_CODES: Set[str] = {
    "US", "USA", "UK", "CA", "DE", "FR", "SG", "JP", "CN", "BR",
    "NL", "PL", "IE", "ES", "IT", "CH", "SE", "RO", "MX", "PH", "VN"
}


def _extract_signals(loc_str: str) -> Tuple[List[str], List[str]]:
    """Extract Indian signals and foreign signals from raw location text."""
    if not loc_str:
        return [], []

    loc_clean = loc_str.strip().lower()
    indian_signals: List[str] = []
    foreign_signals: List[str] = []

    # 1. Multi-word Indian phrases
    for phrase in ["new delhi", "delhi ncr", "tamil nadu", "uttar pradesh", "west bengal", "andhra pradesh", "madhya pradesh"]:
        if phrase in loc_clean:
            indian_signals.append(phrase.title())

    # 2. Check explicit country name "india"
    tokens_lower = set(re.split(r'[^a-zA-Z0-9]+', loc_clean))

    if "india" in tokens_lower:
        indian_signals.append("India")

    # 3. Check exact uppercase or structured country code for India (IN / IND)
    # Must NOT match preposition "in" (e.g. "Remote in Europe")
    loc_raw = loc_str.strip()
    if loc_raw.upper() in ("IN", "IND"):
        indian_signals.append(loc_raw.upper())
    elif re.search(r'(?:,\s*|\(\s*|\[\s*|-\s*|/\s*)\b(IN|IND)\b(?:\s*,|\s*\)|\s*\]|\s*-|\s*/|$)', loc_raw):
        indian_signals.append("IN")
    elif re.search(r',\s*(?:in|ind)\s*$', loc_clean):
        indian_signals.append("IN")

    # 4. Check Indian state codes (e.g. ", KA", "(HR)", "Bengaluru, KA")
    for st_code in INDIAN_STATE_CODES:
        if re.search(r'(?:,\s*|\(\s*|\[\s*|-\s*|/\s*)\b' + st_code + r'\b(?:\s*,|\s*\)|\s*\]|\s*-|\s*/|$)', loc_raw):
            if st_code not in indian_signals:
                indian_signals.append(st_code)

    # 5. Check Indian city and state keywords
    for tok in tokens_lower:
        if tok in INDIAN_CITIES_HUB:
            if tok.title() not in indian_signals:
                indian_signals.append(tok.title())
        elif tok in INDIAN_STATES:
            if tok.title() not in indian_signals:
                indian_signals.append(tok.title())

    # 6. Check Foreign multi-word phrases
    for phrase in ["united states", "united kingdom", "north america", "south america"]:
        if phrase in loc_clean:
            foreign_signals.append(phrase.title())

    # 7. Check Foreign cities, countries, and regions
    for tok in tokens_lower:
        if tok in FOREIGN_CITIES:
            if tok.title() not in foreign_signals:
                foreign_signals.append(tok.title())
        elif tok in FOREIGN_COUNTRIES_REGIONS and tok not in ("us", "uk", "in"):
            if tok.title() not in foreign_signals:
                foreign_signals.append(tok.title())

    # 8. Check Foreign country/state codes in structured format or capital tokens
    for f_code in FOREIGN_COUNTRY_CODES:
        if f_code in ("US", "UK", "USA", "CA"):
            if f_code.lower() in tokens_lower or re.search(r'(?:,\s*|\(\s*|\[\s*|-\s*|/\s*)\b' + f_code + r'\b(?:\s*,|\s*\)|\s*\]|\s*-|\s*/|$)', loc_raw):
                if f_code not in foreign_signals:
                    foreign_signals.append(f_code)
        elif re.search(r'(?:,\s*|\(\s*|\[\s*|-\s*|/\s*)\b' + f_code + r'\b(?:\s*,|\s*\)|\s*\]|\s*-|\s*/|$)', loc_raw):
            if f_code not in foreign_signals:
                foreign_signals.append(f_code)

    return indian_signals, foreign_signals


def evaluate_location(
    location: Optional[str],
    source_scope: Optional[str] = None,
    source_evidence: Optional[str] = None
) -> LocationDecisionResult:
    """
    Evaluates a candidate location and source scope to produce an explicit location decision.

    Decisions:
    - INDIA: Explicit Indian signals OR trusted source scope IN with ambiguous location.
    - NON_INDIA: Foreign signals present without Indian signals and without trusted IN source scope.
    - UNKNOWN: Generic / unresolved location text without explicit signals or source scope.
    - CONFLICT: Simultaneous credible Indian and foreign signals, OR trusted scope IN with explicit foreign-only job location.

    Eligibility:
    - True for INDIA, UNKNOWN, CONFLICT.
    - False for NON_INDIA (the ONLY decision blocked from Job Ops handoff).
    """
    loc_str = (location or "").strip()
    scope_is_in = (source_scope or "").strip().upper() in ("IN", "IND")

    indian_signals, foreign_signals = _extract_signals(loc_str)

    has_india = len(indian_signals) > 0
    has_foreign = len(foreign_signals) > 0

    if has_india and has_foreign:
        ind_str = ", ".join(indian_signals)
        for_str = ", ".join(foreign_signals)
        evidence = f"location_conflict: Indian ({ind_str}) vs Foreign ({for_str})"
        if scope_is_in and source_evidence:
            evidence += f"; source_scope: IN ({source_evidence})"
        return LocationDecisionResult(
            decision=LocationDecision.CONFLICT,
            eligible=True,
            reason=None,
            evidence=evidence,
            confidence="MEDIUM",
        )

    if has_india:
        ind_str = ", ".join(indian_signals)
        evidence = f"indian_location_signal: {ind_str}"
        if scope_is_in and source_evidence:
            evidence += f"; source_scope: IN ({source_evidence})"
        return LocationDecisionResult(
            decision=LocationDecision.INDIA,
            eligible=True,
            reason=None,
            evidence=evidence,
            confidence="HIGH",
        )

    if has_foreign:
        for_str = ", ".join(foreign_signals)
        if scope_is_in:
            # Trusted source scope IN plus explicit foreign-only job-level location -> CONFLICT, eligible per policy
            evidence = f"source_scope: IN ({source_evidence or 'trusted_scope'}); foreign_location: {for_str}"
            return LocationDecisionResult(
                decision=LocationDecision.CONFLICT,
                eligible=True,
                reason=None,
                evidence=evidence,
                confidence="MEDIUM",
            )
        else:
            evidence = f"foreign_location_signal: {for_str}"
            reason = f"NON_INDIA_LOCATION: {loc_str[:100]}"
            return LocationDecisionResult(
                decision=LocationDecision.NON_INDIA,
                eligible=False,
                reason=reason,
                evidence=evidence,
                confidence="HIGH",
            )

    # Ambiguous / generic / unresolved location text (e.g. "2 Locations", "3 Locations", "Remote", "")
    if scope_is_in:
        evidence = f"source_scope: IN ({source_evidence or 'trusted_scope'}); raw_location: {loc_str or 'unspecified'}"
        return LocationDecisionResult(
            decision=LocationDecision.INDIA,
            eligible=True,
            reason=None,
            evidence=evidence,
            confidence="HIGH",
        )

    evidence = f"unresolved_location: {loc_str or 'unspecified'}"
    return LocationDecisionResult(
        decision=LocationDecision.UNKNOWN,
        eligible=True,
        reason=None,
        evidence=evidence,
        confidence="LOW",
    )


def is_india_eligible(
    location: Optional[str],
    source_scope: Optional[str] = None,
    source_evidence: Optional[str] = None
) -> Tuple[bool, Optional[str]]:
    """
    Backward-compatibility wrapper returning (is_eligible: bool, exclusion_reason: Optional[str]).
    """
    res = evaluate_location(location, source_scope=source_scope, source_evidence=source_evidence)
    return res.eligible, res.reason
