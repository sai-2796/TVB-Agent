from enum import Enum
from typing import Any, List, Optional
from pydantic import BaseModel, Field
from .evidence import Evidence, VerificationMethod


class EmailVerificationStatus(str, Enum):
    VERIFIED = "VERIFIED"
    UNVERIFIED = "UNVERIFIED"
    INVALID = "INVALID"
    UNKNOWN = "UNKNOWN"


class TechnicalStatus(str, Enum):
    UNKNOWN = "UNKNOWN"
    INVALID = "INVALID"
    RISKY = "RISKY"
    MX_VALIDATED = "MX_VALIDATED"
    DELIVERABLE = "DELIVERABLE"
    VERIFIED = "VERIFIED"


class FinalEmailStatus(str, Enum):
    UNKNOWN = "UNKNOWN"
    NOT_VERIFIED = "NOT_VERIFIED"
    REJECTED = "REJECTED"
    VERIFIED = "VERIFIED"


class ExecutiveEmail(BaseModel):
    """Model representing an executive email candidate, technical validation, and identity association state."""

    email: Optional[str] = None
    normalized_email: Optional[str] = None
    executive_name: Optional[str] = None
    association_verified: bool = False  # True ONLY if public evidence connects exact email to executive
    association_evidence: List[Evidence] = Field(default_factory=list)
    association_evidence_ids: List[str] = Field(default_factory=list)

    technical_status: TechnicalStatus = TechnicalStatus.UNKNOWN
    syntax_valid: bool = False
    domain_valid: bool = False
    mx_valid: bool = False
    provider_status: Optional[str] = None
    verification_provider: Optional[str] = None
    verification_timestamp: Optional[str] = None
    verification_method: VerificationMethod = VerificationMethod.UNVERIFIED
    source_url: Optional[str] = None
    evidence_ids: List[str] = Field(default_factory=list)
    technical_validation_evidence: List[Evidence] = Field(default_factory=list)

    is_generic: bool = False
    is_pattern_candidate: bool = False  # True if generated via pattern hypothesis without direct text proof

    verification_status: EmailVerificationStatus = EmailVerificationStatus.UNKNOWN
    final_status: FinalEmailStatus = FinalEmailStatus.UNKNOWN
