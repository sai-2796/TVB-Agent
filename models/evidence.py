from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator


class SourceTier(str, Enum):
    TIER_1 = "Tier_1"  # Official company sources, regulatory filings
    TIER_2 = "Tier_2"  # Credible databases, major financial publications
    TIER_3 = "Tier_3"  # Regional startup portals, professional profiles
    TIER_4 = "Tier_4"  # Generic aggregators, secondary blogs


class FreshnessStatus(str, Enum):
    CURRENT = "CURRENT"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"


class VerificationMethod(str, Enum):
    DIRECT_EXTRACTION = "DIRECT_EXTRACTION"
    CROSS_CHECK = "CROSS_CHECK"
    API_CHECK = "API_CHECK"
    MX_CHECK = "MX_CHECK"
    SMTP_CHECK = "SMTP_CHECK"
    UNVERIFIED = "UNVERIFIED"


class Evidence(BaseModel):
    """Structured evidence backing a specific research claim."""

    field: str
    value: Any = None
    raw_claim: str
    evidence_text: Optional[str] = None
    source_url: str
    source_title: str
    source_type: str
    source_published_date: Optional[str] = None
    accessed_at: str
    freshness_status: FreshnessStatus = FreshnessStatus.UNKNOWN
    source_tier: SourceTier = SourceTier.TIER_3
    confidence: float = Field(ge=0.0, le=1.0)
    verification_method: VerificationMethod = VerificationMethod.UNVERIFIED
    evidence_conflict_id: Optional[str] = None

    def model_post_init(self, __context: Any) -> None:
        if not self.evidence_text and self.raw_claim:
            self.evidence_text = self.raw_claim

    @field_validator("confidence")
    @classmethod
    def check_confidence_range(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError("Confidence must be strictly between 0.0 and 1.0")
        return v
