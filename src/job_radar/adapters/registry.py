from typing import Dict, Type, List, Optional
from job_radar.adapters.base import BaseAdapter
from job_radar.adapters.families import (
  GreenhouseAdapter,
  LeverAdapter,
  AshbyAdapter,
  WorkdayAdapter,
)

class AdapterRegistry:
  """Central registry for board parser adapters."""

  def __init__(self):
    self._adapters: Dict[str, BaseAdapter] = {}
    # Register default families
    self.register(GreenhouseAdapter())
    self.register(LeverAdapter())
    self.register(AshbyAdapter())
    self.register(WorkdayAdapter())

  def register(self, adapter: BaseAdapter) -> None:
    self._adapters[adapter.family.lower()] = adapter

  def get(self, family: str) -> Optional[BaseAdapter]:
    return self._adapters.get(family.lower())

  def list_families(self) -> List[str]:
    return sorted(list(self._adapters.keys()))

adapter_registry = AdapterRegistry()
