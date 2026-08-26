from typing import Dict, Type, List, Optional
from job_radar.adapters.base import BaseAdapter
from job_radar.adapters.smartrecruiters import SmartRecruitersAdapter
from job_radar.adapters.talent500 import Talent500Adapter
from job_radar.adapters.families import (
    GreenhouseAdapter,
    LeverAdapter,
    AshbyAdapter,
    WorkdayAdapter,
    MetaCareersAdapter,
    GoogleCareersAdapter,
    AvatureAdapter,
    OracleAdapter,
    AmeripriseAdapter,
    PhenomAdapter,
    GenericAdapter,
)

class AdapterRegistry:
    """Central registry for board parser adapters."""

    def __init__(self):
        self._adapters: Dict[str, BaseAdapter] = {}
        self.register(GreenhouseAdapter())
        self.register(LeverAdapter())
        self.register(AshbyAdapter())
        self.register(WorkdayAdapter())
        self.register(MetaCareersAdapter())
        self.register(GoogleCareersAdapter())
        self.register(AvatureAdapter())
        self.register(OracleAdapter())
        self.register(AmeripriseAdapter())
        self.register(PhenomAdapter())
        self.register(SmartRecruitersAdapter())
        self.register(Talent500Adapter())

    def register(self, adapter: BaseAdapter) -> None:
        self._adapters[adapter.family.lower()] = adapter

    def get(self, family: str) -> Optional[BaseAdapter]:
        fam_key = family.lower()
        if fam_key not in self._adapters:
            self._adapters[fam_key] = GenericAdapter(fam_key)
        return self._adapters.get(fam_key)

    def list_families(self) -> List[str]:
        return sorted(list(self._adapters.keys()))

adapter_registry = AdapterRegistry()
