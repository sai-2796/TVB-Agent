from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field
from .evidence import Evidence, FreshnessStatus


class ExecutiveRole(str, Enum):
    CEO = "CEO"
    CO_FOUNDER = "Co-founder"
    CEO_AND_CO_FOUNDER = "CEO & Co-founder"
    OTHER = "Other"


class ExecutiveProfile(BaseModel):
    """Model representing an identified decision maker (CEO / Co-founder)."""

    full_name: Optional[str] = None
    role: Optional[ExecutiveRole] = None
    identity_verified: bool = False
    is_current_leadership: bool = True  # Must be True for active leadership
    source_freshness: FreshnessStatus = FreshnessStatus.UNKNOWN
    evidence: List[Evidence] = Field(default_factory=list)
