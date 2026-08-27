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

    loc_raw = loc_str.strip()
    loc_clean = loc_raw.lower()
    indian_signals: List[str] = []
    foreign_signals: List[str] = []

    def _add_signal(target_list: List[str], sig: str):
        if sig not in target_list:
            target_list.append(sig)

    # 1. Indian Cities & States (multi-word and single-word phrases)
    all_indian_phrases = sorted(
        list(INDIAN_CITIES_HUB | INDIAN_STATES | {"india"}),
        key=lambda x: len(x),
        reverse=True
    )
    for phrase in all_indian_phrases:
        if re.search(r'\b' + re.escape(phrase) + r'\b', loc_clean):
            _add_signal(indian_signals, "India" if phrase == "india" else phrase.title())

    # 2. Indian country codes & state codes (case-sensitive structured or exact uppercase)
    all_indian_codes = INDIAN_STATE_CODES | {"IN", "IND"}
    for code in all_indian_codes:
        if loc_raw == code:
            _add_signal(indian_signals, code)
        elif re.search(r'(?:^|[\s,(\[/-])' + re.escape(code) + r'(?:[\s,)\]/-]|$)', loc_raw):
            _add_signal(indian_signals, code)

    # 3. Foreign Cities & Countries/Regions (multi-word and single-word phrases)
    # Exclude short codes/ambiguous tokens ("us", "uk", "usa", "ca", "in") from case-insensitive phrase matching
    all_foreign_phrases = sorted(
        list(FOREIGN_CITIES | (FOREIGN_COUNTRIES_REGIONS - {"us", "uk", "usa", "ca", "in"})),
        key=lambda x: len(x),
        reverse=True
    )
    for phrase in all_foreign_phrases:
        if re.search(r'\b' + re.escape(phrase) + r'\b', loc_clean):
            _add_signal(foreign_signals, phrase.title())

    # 4. Foreign Country Codes (case-sensitive structured or exact uppercase)
    for f_code in FOREIGN_COUNTRY_CODES:
        if loc_raw == f_code:
            _add_signal(foreign_signals, f_code)
        elif re.search(r'(?:^|[\s,(\[/-])' + re.escape(f_code) + r'(?:[\s,)\]/-]|$)', loc_raw):
            _add_signal(foreign_signals, f_code)

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
