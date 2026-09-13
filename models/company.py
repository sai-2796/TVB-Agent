from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from .evidence import Evidence
from .financial import FinancialsData
from .us_presence import USPresenceData
from .executive import ExecutiveProfile
from .email import ExecutiveEmail
from .conflict import ConflictRecord


class CompanyResearch(BaseModel):
    """Aggregated research payload for a single candidate company."""

    domain: str
    company_name: Optional[str] = None
    website_url: Optional[str] = None
    description: Optional[str] = None
    industry_sector: Optional[str] = None
    headquarters_country: Optional[str] = None
    founded_year: Optional[int] = None
    is_tech_platform: bool = False
    platform_summary: Optional[str] = None
    platform_evidence: List[Evidence] = Field(default_factory=list)
    financials: FinancialsData = Field(default_factory=FinancialsData)
    us_presence: USPresenceData = Field(default_factory=USPresenceData)
    executive: ExecutiveProfile = Field(default_factory=ExecutiveProfile)
    executive_email: ExecutiveEmail = Field(default_factory=ExecutiveEmail)
    all_evidence: List[Evidence] = Field(default_factory=list)
    conflicts: List[ConflictRecord] = Field(default_factory=list)
    research_completeness: str = "partial"  # "complete", "partial", "failed"
    research_depth: str = "standard"        # "quick", "standard", "deep"
    sources_consulted: List[str] = Field(default_factory=list)
    source_failures: List[Dict[str, Any]] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    research_timestamp: Optional[str] = None
