from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class ProviderLocationEvidence(BaseModel):
  """Bounded geography facts extracted from a provider, never raw payloads."""
  provider_family: str
  countries: List[str] = Field(default_factory=list, max_length=12)
  country_paths: List[str] = Field(default_factory=list, max_length=12)
  regions: List[str] = Field(default_factory=list, max_length=12)
  region_paths: List[str] = Field(default_factory=list, max_length=12)
  display_locations: List[str] = Field(default_factory=list, max_length=12)
  source_scope: Optional[str] = None
  source_evidence: Optional[str] = None

class ExtractedCandidate(BaseModel):
  """Normalized candidate job extracted by an adapter."""
  title: str
  company: str
  location: Optional[str] = None
  department: Optional[str] = None
  employment_type: Optional[str] = None
  raw_url: str
  fingerprint: str
  extra_payload: Dict[str, Any] = Field(default_factory=dict)
  location_provider_evidence: Optional[ProviderLocationEvidence] = None

class BaseAdapter(ABC):
  """Abstract Base Class for board adapter implementations."""

  @property
  @abstractmethod
  def family(self) -> str:
    """The adapter family slug identifier (e.g. 'greenhouse', 'lever')."""
    pass

  @abstractmethod
  def parse_raw_payload(
    self,
    payload: str | bytes,
    board_name: str,
    target_url: str,
    selector_config: Optional[Dict[str, Any]] = None
  ) -> List[ExtractedCandidate]:
    """Parse raw HTTP/DOM payload into normalized candidate jobs."""
    pass
