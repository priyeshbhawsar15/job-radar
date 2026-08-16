from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, HttpUrl

class ExtractedCandidate(BaseModel):
  """Normalized candidate job extracted by an adapter."""
  title: str
  company: str
  location: Optional[str] = None
  department: Optional[str] = None
  employment_type: Optional[str] = None
  raw_url: str
  fingerprint: str
  extra_payload: Dict[str, Any] = {}

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
