"""Provider-aware detail request and result types and structured failure codes."""

from dataclasses import dataclass
from typing import Any, Mapping, Optional

# Stable detail extraction error codes
ERR_INVALID_PROVIDER_CONFIG = "invalid_provider_config"
ERR_INVALID_DETAIL_URL = "invalid_detail_url"
ERR_BOUNDARY_VIOLATION = "boundary_violation"
ERR_HTTP_STATUS = "http_status"
ERR_RESPONSE_TOO_LARGE = "response_too_large"
ERR_INVALID_PAYLOAD = "invalid_payload"
ERR_RECORD_NOT_FOUND = "record_not_found"
ERR_DESCRIPTION_MISSING = "description_missing"
ERR_DESCRIPTION_INVALID = "description_invalid"


@dataclass(frozen=True)
class DetailRequest:
    family: str
    public_url: str
    board_name: str
    title: str
    provider_config: Mapping[str, Any]


@dataclass(frozen=True)
class DetailResult:
    description: Optional[str] = None
    location: Optional[str] = None
    employment_type: Optional[str] = None
    department: Optional[str] = None
    salary_raw: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_currency: Optional[str] = None
    source: Optional[str] = None
    error_code: Optional[str] = None
    title: Optional[str] = None

    @classmethod
    def empty(cls, error_code: Optional[str] = None) -> "DetailResult":
        return cls(error_code=error_code)

    def as_update_dict(self) -> dict[str, Any]:
        return {
            "description": self.description,
            "location": self.location,
            "employment_type": self.employment_type,
            "department": self.department,
            "salary_raw": self.salary_raw,
            "salary_min": self.salary_min,
            "salary_max": self.salary_max,
            "salary_currency": self.salary_currency,
            "detail_enrichment_source": self.source,
            "detail_enrichment_error_code": self.error_code,
        }
