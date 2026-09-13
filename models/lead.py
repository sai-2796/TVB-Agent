from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field
from .company import CompanyResearch


class QualificationStatus(str, Enum):
    QUALIFIED = "QUALIFIED"
    UNQUALIFIED = "UNQUALIFIED"
    PENDING_CONTACT_VERIFICATION = "PENDING_CONTACT_VERIFICATION"


class Lead(BaseModel):
    """Final output lead model representing a candidate evaluation result."""

    id: str
    company_name: str
    domain: str
    description: Optional[str] = None
    industry_sector: Optional[str] = None
    financial_summary: Optional[str] = None
    executive_name: Optional[str] = None
    executive_role: Optional[str] = None
    verified_executive_email: Optional[str] = None  # Populated ONLY if QUALIFIED
    qualification_status: QualificationStatus = QualificationStatus.UNQUALIFIED
    rejection_reasons: List[str] = Field(default_factory=list)
    research_payload: Optional[CompanyResearch] = None
    validation_version: str = "1.0"
    created_at: str
