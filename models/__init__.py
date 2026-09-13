"""Pydantic data models for TVB Agent."""
from .evidence import Evidence, FreshnessStatus, SourceTier, VerificationMethod
from .financial import FinancialsData, FinancialType
from .us_presence import USPresenceData, USPresenceStatus
from .executive import ExecutiveProfile, ExecutiveRole
from .email import ExecutiveEmail, EmailVerificationStatus, TechnicalStatus, FinalEmailStatus
from .conflict import ConflictRecord
from .company import CompanyResearch
from .lead import Lead, QualificationStatus
from .discovery import (
    DiscoveryConfig,
    DiscoveredCandidate,
    DiscoveryIterationLog,
    DiscoveryResult,
)

__all__ = [
    "Evidence",
    "SourceTier",
    "FreshnessStatus",
    "VerificationMethod",
    "FinancialsData",
    "FinancialType",
    "USPresenceData",
    "USPresenceStatus",
    "ExecutiveProfile",
    "ExecutiveRole",
    "ExecutiveEmail",
    "EmailVerificationStatus",
    "TechnicalStatus",
    "FinalEmailStatus",
    "ConflictRecord",
    "CompanyResearch",
    "Lead",
    "QualificationStatus",
    "DiscoveryConfig",
    "DiscoveredCandidate",
    "DiscoveryIterationLog",
    "DiscoveryResult",
]
