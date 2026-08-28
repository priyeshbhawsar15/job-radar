"""Deterministic, offline India admission decisions for job locations."""
import re
from dataclasses import dataclass
from typing import Optional, Tuple, Set, List, Iterable


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


# Country names and codes intentionally use exact token matching.  Short ISO codes are
# accepted only as standalone, separator-delimited location components.
INDIA_ALIASES = {"india", "republic of india", "bharat", "in", "ind"}
FOREIGN_COUNTRIES = {
    # ISO-3166 names/codes (minus India) plus reviewed common aliases. Codes are
    # still structurally matched below, so ordinary prose never collides with them.
    "afghanistan": {"afghanistan", "af"}, "albania": {"albania", "al"}, "algeria": {"algeria", "dz"}, "andorra": {"andorra", "ad"}, "angola": {"angola", "ao"}, "argentina": {"argentina", "ar"}, "armenia": {"armenia", "am"}, "australia": {"australia", "au"}, "austria": {"austria", "at"}, "azerbaijan": {"azerbaijan", "az"}, "bahamas": {"bahamas", "bs"}, "bahrain": {"bahrain", "bh"}, "bangladesh": {"bangladesh", "bd"}, "barbados": {"barbados", "bb"}, "belarus": {"belarus", "by"}, "belgium": {"belgium", "be"}, "belize": {"belize", "bz"}, "benin": {"benin", "bj"}, "bermuda": {"bermuda", "bm"}, "bhutan": {"bhutan", "bt"}, "bolivia": {"bolivia", "bo"}, "bosnia and herzegovina": {"bosnia and herzegovina", "ba"}, "botswana": {"botswana", "bw"}, "brazil": {"brazil", "br"}, "brunei": {"brunei", "bn"}, "bulgaria": {"bulgaria", "bg"}, "cambodia": {"cambodia", "kh"}, "cameroon": {"cameroon", "cm"}, "canada": {"canada", "ca"}, "chile": {"chile", "cl"}, "china": {"china", "cn"}, "colombia": {"colombia", "co"}, "costa rica": {"costa rica", "cr"}, "croatia": {"croatia", "hr"}, "cyprus": {"cyprus", "cy"}, "czechia": {"czechia", "czech republic", "cz"}, "denmark": {"denmark", "dk"}, "dominican republic": {"dominican republic", "do"}, "ecuador": {"ecuador", "ec"}, "egypt": {"egypt", "eg"}, "estonia": {"estonia", "ee"}, "finland": {"finland", "fi"}, "france": {"france", "fr"}, "georgia": {"georgia", "ge"}, "germany": {"germany", "de"}, "ghana": {"ghana", "gh"}, "greece": {"greece", "gr"}, "guatemala": {"guatemala", "gt"}, "hong kong": {"hong kong", "hk"}, "hungary": {"hungary", "hu"}, "iceland": {"iceland", "is"}, "indonesia": {"indonesia", "id"}, "iraq": {"iraq", "iq"}, "ireland": {"ireland", "ie"}, "israel": {"israel", "il"}, "italy": {"italy", "it"}, "jamaica": {"jamaica", "jm"}, "japan": {"japan", "jp"}, "jordan": {"jordan", "jo"}, "kazakhstan": {"kazakhstan", "kz"}, "kenya": {"kenya", "ke"}, "kuwait": {"kuwait", "kw"}, "latvia": {"latvia", "lv"}, "lebanon": {"lebanon", "lb"}, "lithuania": {"lithuania", "lt"}, "luxembourg": {"luxembourg", "lu"}, "malaysia": {"malaysia", "my"}, "malta": {"malta", "mt"}, "mauritius": {"mauritius", "mu"}, "mexico": {"mexico", "mx"}, "moldova": {"moldova", "md"}, "monaco": {"monaco", "mc"}, "mongolia": {"mongolia", "mn"}, "montenegro": {"montenegro", "me"}, "morocco": {"morocco", "ma"}, "mozambique": {"mozambique", "mz"}, "myanmar": {"myanmar", "mm"}, "namibia": {"namibia", "na"}, "nepal": {"nepal", "np"}, "netherlands": {"netherlands", "nl"}, "new zealand": {"new zealand", "nz"}, "nigeria": {"nigeria", "ng"}, "norway": {"norway", "no"}, "oman": {"oman", "om"}, "pakistan": {"pakistan", "pk"}, "panama": {"panama", "pa"}, "peru": {"peru", "pe"}, "philippines": {"philippines", "ph"}, "poland": {"poland", "pl"}, "portugal": {"portugal", "pt"}, "qatar": {"qatar", "qa"}, "romania": {"romania", "ro"}, "rwanda": {"rwanda", "rw"}, "saudi arabia": {"saudi arabia", "sa", "ksa"}, "senegal": {"senegal", "sn"}, "serbia": {"serbia", "rs"}, "singapore": {"singapore", "sg"}, "slovakia": {"slovakia", "sk"}, "slovenia": {"slovenia", "si"}, "south africa": {"south africa", "za"}, "south korea": {"south korea", "republic of korea", "kr"}, "spain": {"spain", "es"}, "sri lanka": {"sri lanka", "lk"}, "sweden": {"sweden", "se"}, "switzerland": {"switzerland", "ch"}, "taiwan": {"taiwan", "tw"}, "tanzania": {"tanzania", "tz"}, "thailand": {"thailand", "th"}, "tunisia": {"tunisia", "tn"}, "turkey": {"turkey", "türkiye", "tr"}, "ukraine": {"ukraine", "ua"}, "united arab emirates": {"united arab emirates", "uae", "ae"}, "united kingdom": {"united kingdom", "uk", "great britain"}, "united states": {"united states", "united states of america", "usa", "us"}, "uruguay": {"uruguay", "uy"}, "uzbekistan": {"uzbekistan", "uz"}, "venezuela": {"venezuela", "ve"}, "vietnam": {"vietnam", "vn"}, "zambia": {"zambia", "zm"}, "zimbabwe": {"zimbabwe", "zw"},
}
INDIAN_CITIES_HUB: Set[str] = {"bengaluru", "bangalore", "hyderabad", "gurgaon", "gurugram", "noida", "pune", "chennai", "mumbai", "delhi", "new delhi", "ncr", "ahmedabad", "kolkata", "jaipur", "indore", "kochi", "cochin", "trivandrum", "thiruvananthapuram", "chandigarh", "mohali", "coimbatore", "vadodara", "surat", "nagpur", "bhubaneswar", "ghaziabad", "faridabad", "mysore", "mysuru", "visakhapatnam", "vizag"}
INDIAN_STATES: Set[str] = {"karnataka", "telangana", "maharashtra", "haryana", "tamil nadu", "kerala", "uttar pradesh", "gujarat", "rajasthan", "punjab", "west bengal", "odisha", "andhra pradesh", "madhya pradesh"}
INDIAN_STATE_CODES = {"KA", "TS", "TG", "MH", "HR", "TN", "UP", "DL", "GJ", "RJ", "PB", "WB", "OR", "OD", "AP", "MP", "KL"}
US_STATES = {"california", "washington", "delaware", "north carolina", "district of columbia", "washington dc", "new york", "texas", "new jersey", "massachusetts", "illinois", "colorado", "virginia", "florida", "georgia", "oregon", "arizona", "michigan", "pennsylvania", "maryland", "minnesota", "ohio", "utah"}
US_CODES = {"CA", "WA", "DE", "NC", "DC", "NY", "TX", "NJ", "MA", "IL", "CO", "VA", "FL", "GA", "OR", "AZ", "MI", "PA", "MD", "MN", "OH", "UT"}
CANADA_PROVINCES = {"ontario", "quebec", "british columbia", "alberta", "manitoba", "saskatchewan", "nova scotia", "new brunswick", "newfoundland and labrador", "prince edward island"}
CANADA_CODES = {"ON", "QC", "BC", "AB", "MB", "SK", "NS", "NB", "NL", "PE"}
FOREIGN_CITIES = {"london", "new york", "san francisco", "san jose", "seattle", "austin", "chicago", "boston", "toronto", "vancouver", "montreal", "sydney", "melbourne", "berlin", "munich", "frankfurt", "paris", "tokyo", "shanghai", "beijing", "amsterdam", "dublin", "warsaw", "bucharest", "zurich", "geneva", "madrid", "sao paulo", "buenos aires", "tel aviv", "dubai", "bellevue", "mountain view", "charlotte", "wilmington", "belgrade", "seoul"}
CONTEXTUAL_CITIES = {"bellevue", "mountain view", "charlotte", "wilmington", "belgrade", "seoul"}
REGIONS = {"europe", "emea", "apac", "latam", "americas", "north america", "south america"}


def _add(signals: List[str], value: str) -> None:
    if value not in signals:
        signals.append(value)


def _phrase_present(text: str, phrase: str) -> bool:
    return bool(re.search(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", text, re.I))


def _structural_code(text: str, code: str) -> bool:
    return text.strip() == code or bool(re.search(r"(?:^|[\s,(\[/-])" + re.escape(code) + r"(?:$|[\s,)\]/-])", text))


def _country_signal(value: str) -> Tuple[bool, bool, str]:
    raw = value.strip()
    lower = raw.lower()
    if lower in INDIA_ALIASES:
        return True, False, "India"
    for canonical, aliases in FOREIGN_COUNTRIES.items():
        if lower in aliases:
            return False, True, canonical.title()
    return False, False, ""


def _extract_signals(loc_str: str) -> Tuple[List[str], List[str]]:
    if not loc_str:
        return [], []
    raw, text = loc_str.strip(), loc_str.strip().lower()
    india, foreign = [], []
    for phrase in sorted(INDIAN_CITIES_HUB | INDIAN_STATES | {"india", "republic of india", "bharat"}, key=len, reverse=True):
        if _phrase_present(text, phrase): _add(india, "India" if phrase in INDIA_ALIASES else phrase.title())
    for code in INDIAN_STATE_CODES | {"IN", "IND"}:
        if _structural_code(raw, code): _add(india, code)
    for phrase in sorted(US_STATES | CANADA_PROVINCES | (FOREIGN_CITIES - CONTEXTUAL_CITIES) | REGIONS, key=len, reverse=True):
        if _phrase_present(text, phrase): _add(foreign, phrase.title())
    for canonical, aliases in FOREIGN_COUNTRIES.items():
        for alias in aliases:
            if len(alias) <= 3:
                found = _structural_code(raw, alias.upper())
            else:
                found = _phrase_present(text, alias)
            if found:
                _add(foreign, canonical.title()); break
    for code in US_CODES | CANADA_CODES:
        if _structural_code(raw, code): _add(foreign, code)
    # These names collide globally; classify them only when a country/subdivision
    # signal in the same provider location structurally disambiguates them.
    if foreign:
        for city in CONTEXTUAL_CITIES:
            if _phrase_present(text, city): _add(foreign, city.title())
    return india, foreign


def _signal_summary(signals: List[str], max_items: int = 3, item_width: int = 24) -> str:
    """Produce a deterministic, column-safe summary of potentially many signals."""
    values = [" ".join(value.split())[:item_width] for value in signals[:max_items]]
    if len(signals) > max_items:
        values.append(f"+{len(signals) - max_items} more")
    return ", ".join(values)


def _raw_summary(raw: str, width: int = 96) -> str:
    return " ".join(raw.split())[:width] or "unspecified"


def _scope_summary(source_evidence: Optional[str]) -> str:
    return " ".join((source_evidence or "trusted_scope").split())[:48]


def _evidence_values(evidence: object, key: str) -> Iterable[str]:
    if evidence is None: return []
    if hasattr(evidence, key): value = getattr(evidence, key)
    elif isinstance(evidence, dict): value = evidence.get(key, [])
    else: return []
    return [str(v) for v in value if isinstance(v, (str, int))]


def evaluate_location(location: Optional[str], source_scope: Optional[str] = None, source_evidence: Optional[str] = None, provider_evidence: object = None) -> LocationDecisionResult:
    """Classify raw display location plus bounded provider geography, offline.

    Structured country facts are preferred, while display/office locations add genuine
    alternatives. A source scope is informative only; it never defeats foreign evidence.
    """
    raw = (location or "").strip()
    indian, foreign = _extract_signals(raw)
    structured_seen = False
    for country in _evidence_values(provider_evidence, "countries"):
        i, f, label = _country_signal(country)
        if i: _add(indian, f"Country={label}"); structured_seen = True
        if f: _add(foreign, f"Country={label}"); structured_seen = True
    for region in _evidence_values(provider_evidence, "regions"):
        i, f = _extract_signals(region)
        for signal in i: _add(indian, f"Region={signal}")
        for signal in f: _add(foreign, f"Region={signal}")
    for display in _evidence_values(provider_evidence, "display_locations"):
        i, f = _extract_signals(display)
        for signal in i: _add(indian, f"Alternative={signal}")
        for signal in f: _add(foreign, f"Alternative={signal}")
    scope_is_in = (source_scope or "").strip().upper() in {"IN", "IND"}
    # CandidateJob.location_evidence is VARCHAR(255) in PostgreSQL. These compact,
    # deterministic summaries retain the decisive signal types without serializing or
    # truncating structured provider JSON (which remains in its Text column).
    if indian and foreign:
        evidence = f"location_conflict: Indian ({_signal_summary(indian)}) vs Foreign ({_signal_summary(foreign)})"
        return LocationDecisionResult(LocationDecision.CONFLICT, True, evidence=evidence, confidence="HIGH" if structured_seen else "MEDIUM")
    if indian:
        evidence = f"indian_location_signal: {_signal_summary(indian)}"
        if scope_is_in:
            evidence += f"; source_scope: IN ({_scope_summary(source_evidence)})"
        return LocationDecisionResult(LocationDecision.INDIA, True, evidence=evidence, confidence="HIGH")
    if foreign:
        return LocationDecisionResult(LocationDecision.NON_INDIA, False, reason=f"NON_INDIA_LOCATION: {_raw_summary(raw, 100)}", evidence=f"foreign_location_signal: {_signal_summary(foreign)}", confidence="HIGH")
    if scope_is_in:
        return LocationDecisionResult(LocationDecision.INDIA, True, evidence=f"source_scope: IN ({_scope_summary(source_evidence)}); raw_location: {_raw_summary(raw)}", confidence="HIGH")
    return LocationDecisionResult(LocationDecision.UNKNOWN, True, evidence=f"unresolved_location: {_raw_summary(raw)}", confidence="LOW")


def is_india_eligible(location: Optional[str], source_scope: Optional[str] = None, source_evidence: Optional[str] = None, provider_evidence: object = None) -> Tuple[bool, Optional[str]]:
    res = evaluate_location(location, source_scope, source_evidence, provider_evidence)
    return res.eligible, res.reason
