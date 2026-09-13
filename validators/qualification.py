from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from models.company import CompanyResearch
from models.lead import Lead, QualificationStatus
from validators.financial import FinancialValidator, ValidationResult, ValidationStatus
from validators.platform import PlatformValidator
from validators.us_presence import USPresenceValidator
from validators.executive import ExecutiveValidator
from validators.email import EmailValidator


class CriterionResult(BaseModel):
    """Structured audit model for an individual hard qualification criterion."""

    criterion: str
    status: ValidationStatus
    reason: str
    evidence_ids: List[str] = Field(default_factory=list)
    source_urls: List[str] = Field(default_factory=list)
    confidence: float = 0.0
    validation_timestamp: str


class QualificationReport(BaseModel):
    """
    Complete deterministic qualification report container including full audit trail.
    """

    company_name: str
    canonical_domain: str
    overall_status: QualificationStatus
    validation_version: str = "1.0"
    is_qualified: bool = False
    financial_result: ValidationResult
    platform_result: ValidationResult
    us_presence_result: ValidationResult
    executive_result: ValidationResult
    email_result: ValidationResult
    criterion_results: List[CriterionResult] = Field(default_factory=list)
    rejection_reasons: List[str] = Field(default_factory=list)
    unresolved_conflicts: List[Dict[str, Any]] = Field(default_factory=list)
    validated_at: str


class QualificationEngine:
    """
    Master programmatic qualification engine enforcing TVB's 5 Hard Criteria.
    Executes purely deterministic Python rules outside the LLM.
    """

    VALIDATION_VERSION: str = "1.0"

    @classmethod
    def evaluate(cls, company_research: CompanyResearch) -> QualificationReport:
        now_ts = datetime.now(timezone.utc).isoformat()

        # Run individual deterministic validators
        financial_res = FinancialValidator.validate(company_research.financials)
        platform_res = PlatformValidator.validate(company_research)
        us_res = USPresenceValidator.validate(company_research.us_presence)
        exec_res = ExecutiveValidator.validate(company_research.executive)
        email_res = EmailValidator.validate(company_research.executive_email)

        # Check for unresolved critical conflicts
        unresolved_conflicts: List[Dict[str, Any]] = []
        for conf in company_research.conflicts:
            if conf.resolution_status == "UNRESOLVED_UNKNOWN":
                unresolved_conflicts.append(conf.model_dump())
                if conf.field_name == "financials":
                    financial_res = ValidationResult(
                        criterion="financial",
                        status=ValidationStatus.UNKNOWN,
                        reason="Financial UNKNOWN: Unresolved data conflict across research sources.",
                    )
                elif conf.field_name == "executive":
                    exec_res = ValidationResult(
                        criterion="executive",
                        status=ValidationStatus.UNKNOWN,
                        reason="Executive UNKNOWN: Unresolved leadership conflict across research sources.",
                    )

        # Build audit trail
        results_map = [
            ("financial", financial_res),
            ("platform", platform_res),
            ("us_presence", us_res),
            ("executive", exec_res),
            ("email", email_res),
        ]

        criterion_results: List[CriterionResult] = []
        rejection_reasons: List[str] = []

        for c_name, res in results_map:
            criterion_results.append(
                CriterionResult(
                    criterion=c_name,
                    status=res.status,
                    reason=res.reason,
                    evidence_ids=res.evidence_ids,
                    source_urls=res.source_urls,
                    confidence=res.confidence,
                    validation_timestamp=now_ts,
                )
            )
            if res.status != ValidationStatus.PASS:
                rejection_reasons.append(f"{c_name.capitalize()} [{res.status.value}]: {res.reason}")

        # Overall Status Determination
        all_pass = all(res.status == ValidationStatus.PASS for _, res in results_map)
        non_email_pass = (
            financial_res.status == ValidationStatus.PASS
            and platform_res.status == ValidationStatus.PASS
            and us_res.status == ValidationStatus.PASS
            and exec_res.status == ValidationStatus.PASS
        )

        if all_pass:
            overall_status = QualificationStatus.QUALIFIED
            is_qualified = True
        elif non_email_pass and email_res.status == ValidationStatus.UNKNOWN:
            overall_status = QualificationStatus.PENDING_CONTACT_VERIFICATION
            is_qualified = False
        else:
            overall_status = QualificationStatus.UNQUALIFIED
            is_qualified = False

        return QualificationReport(
            company_name=company_research.company_name or company_research.domain,
            canonical_domain=company_research.domain,
            overall_status=overall_status,
            validation_version=cls.VALIDATION_VERSION,
            is_qualified=is_qualified,
            financial_result=financial_res,
            platform_result=platform_res,
            us_presence_result=us_res,
            executive_result=exec_res,
            email_result=email_res,
            criterion_results=criterion_results,
            rejection_reasons=rejection_reasons,
            unresolved_conflicts=unresolved_conflicts,
            validated_at=now_ts,
        )

    @classmethod
    def build_lead(cls, lead_id: str, company_research: CompanyResearch, created_at: str) -> Lead:
        report = cls.evaluate(company_research)

        # Verified email is populated ONLY if fully QUALIFIED
        verified_email = (
            company_research.executive_email.email
            if report.is_qualified and company_research.executive_email
            else None
        )

        fin_summary = None
        if company_research.financials and company_research.financials.normalized_usd:
            fin_summary = f"${company_research.financials.normalized_usd:,.2f} USD ({company_research.financials.financial_type.value})"

        return Lead(
            id=lead_id,
            company_name=company_research.company_name or company_research.domain,
            domain=company_research.domain,
            description=company_research.description,
            industry_sector=company_research.industry_sector,
            financial_summary=fin_summary,
            executive_name=company_research.executive.full_name if company_research.executive else None,
            executive_role=company_research.executive.role.value if company_research.executive and company_research.executive.role else None,
            verified_executive_email=verified_email,
            qualification_status=report.overall_status,
            rejection_reasons=report.rejection_reasons,
            research_payload=company_research,
            validation_version=report.validation_version,
            created_at=created_at,
        )
