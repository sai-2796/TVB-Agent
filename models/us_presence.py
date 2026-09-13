from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field
from .evidence import Evidence


class USPresenceStatus(str, Enum):
    VERIFIED_NO_US_PRESENCE = "VERIFIED_NO_US_PRESENCE"
    MINIMAL_US_PRESENCE = "MINIMAL_US_PRESENCE"
    SIGNIFICANT_US_PRESENCE = "SIGNIFICANT_US_PRESENCE"
    UNKNOWN = "UNKNOWN"


class USPresenceData(BaseModel):
    """Model evaluating company US operational footprint."""

    status: USPresenceStatus = USPresenceStatus.UNKNOWN
    headquarters_country: Optional[str] = None
    office_locations: List[str] = Field(default_factory=list)
    subsidiary_information: Optional[str] = None
    serves_us_customers_only: bool = False  # True if US activity is purely customer base
    uses_us_cloud_hosting_only: bool = False  # True if US activity is cloud infra (AWS/GCP/Azure)
    evidence: List[Evidence] = Field(default_factory=list)
