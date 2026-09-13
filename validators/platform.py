from models.company import CompanyResearch
from validators.financial import ValidationResult, ValidationStatus


class PlatformValidator:
    """Deterministic validator evaluating technology-related platform/product status."""

    @classmethod
    def validate(cls, company_research: CompanyResearch | None) -> ValidationResult:
        if company_research is None or not company_research.platform_evidence:
            return ValidationResult(
                criterion="platform",
                status=ValidationStatus.UNKNOWN,
                reason="Platform UNKNOWN: Insufficient evidence — No technology platform evidence provided.",
            )

        urls = [e.source_url for e in company_research.platform_evidence if e.source_url]
        ev_ids = [e.source_url for e in company_research.platform_evidence if e.source_url]
        max_conf = max((e.confidence for e in company_research.platform_evidence), default=0.0)

        if not company_research.is_tech_platform:
            return ValidationResult(
                criterion="platform",
                status=ValidationStatus.FAIL,
                reason="Platform FAIL: Company is evaluated as a traditional non-tech business.",
                evidence_ids=ev_ids,
                source_urls=urls,
                confidence=max_conf,
            )

        summary = company_research.platform_summary or "Tech Platform"
        return ValidationResult(
            criterion="platform",
            status=ValidationStatus.PASS,
            reason=f"Platform PASS: Company operates a verified technology-related platform ({summary}).",
            evidence_ids=ev_ids,
            source_urls=urls,
            confidence=max_conf,
        )
