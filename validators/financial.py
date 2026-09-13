from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field
from models.financial import FinancialsData, FinancialType


class ValidationStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"


class ValidationResult(BaseModel):
    criterion: str = "financial"
    status: ValidationStatus
    reason: str
    evidence_ids: List[str] = Field(default_factory=list)
    source_urls: List[str] = Field(default_factory=list)
    confidence: float = 0.0


class FinancialValidator:
    """Deterministic validator for TVB financial criterion ($1M–$5M USD revenue or total funding)."""

    MIN_THRESHOLD_USD: float = 1_000_000.0
    MAX_THRESHOLD_USD: float = 5_000_000.0

    @classmethod
    def validate(cls, financial_data: FinancialsData | None) -> ValidationResult:
        if financial_data is None or not financial_data.evidence:
            return ValidationResult(
                criterion="financial",
                status=ValidationStatus.UNKNOWN,
                reason="Financial UNKNOWN: Insufficient evidence — No verified financial evidence provided.",
                confidence=0.0,
            )

        urls = [e.source_url for e in financial_data.evidence if e.source_url]
        ev_ids = [e.source_url for e in financial_data.evidence if e.source_url]
        max_conf = max((e.confidence for e in financial_data.evidence), default=0.0)

        ftype = financial_data.financial_type

        # Disqualify valuation
        if ftype == FinancialType.VALUATION:
            return ValidationResult(
                criterion="financial",
                status=ValidationStatus.FAIL,
                reason="Financial FAIL: Disqualified — Company valuation cannot be used as revenue or total funding.",
                evidence_ids=ev_ids,
                source_urls=urls,
                confidence=max_conf,
            )

        # Disqualify unknown financial type
        if ftype not in (FinancialType.FUNDING, FinancialType.REVENUE, FinancialType.FUNDING_ROUND):
            return ValidationResult(
                criterion="financial",
                status=ValidationStatus.UNKNOWN,
                reason="Financial UNKNOWN: Financial claim type is unverified or unknown.",
                evidence_ids=ev_ids,
                source_urls=urls,
                confidence=max_conf,
            )

        # Evaluate single funding round vs cumulative total funding
        if ftype == FinancialType.FUNDING_ROUND and not financial_data.is_total_amount:
            return ValidationResult(
                criterion="financial",
                status=ValidationStatus.UNKNOWN,
                reason="Financial UNKNOWN: Single funding round amount cannot be assumed to equal cumulative total funding without explicit evidence.",
                evidence_ids=ev_ids,
                source_urls=urls,
                confidence=max_conf,
            )

        val_usd = financial_data.normalized_usd
        if val_usd is None:
            return ValidationResult(
                criterion="financial",
                status=ValidationStatus.UNKNOWN,
                reason="Financial UNKNOWN: Financial value could not be normalized to USD.",
                evidence_ids=ev_ids,
                source_urls=urls,
                confidence=max_conf,
            )

        # Strict boundary evaluation ($1M to $5M USD inclusive)
        if cls.MIN_THRESHOLD_USD <= val_usd <= cls.MAX_THRESHOLD_USD:
            return ValidationResult(
                criterion="financial",
                status=ValidationStatus.PASS,
                reason=f"Financial PASS: Verified cumulative {ftype.value} of ${val_usd:,.2f} USD is within target range [$1,000,000, $5,000,000].",
                evidence_ids=ev_ids,
                source_urls=urls,
                confidence=max_conf,
            )
        elif val_usd < cls.MIN_THRESHOLD_USD:
            return ValidationResult(
                criterion="financial",
                status=ValidationStatus.FAIL,
                reason=f"Financial FAIL: Verified {ftype.value} of ${val_usd:,.2f} USD is below minimum $1,000,000 USD threshold.",
                evidence_ids=ev_ids,
                source_urls=urls,
                confidence=max_conf,
            )
        else:
            return ValidationResult(
                criterion="financial",
                status=ValidationStatus.FAIL,
                reason=f"Financial FAIL: Verified {ftype.value} of ${val_usd:,.2f} USD is above maximum $5,000,000 USD threshold.",
                evidence_ids=ev_ids,
                source_urls=urls,
                confidence=max_conf,
            )
