from models.executive import ExecutiveProfile, ExecutiveRole
from validators.financial import ValidationResult, ValidationStatus


class ExecutiveValidator:
    """Deterministic validator for executive identification (CEO / Co-founder)."""

    ALLOWED_ROLES = {
        ExecutiveRole.CEO,
        ExecutiveRole.CO_FOUNDER,
        ExecutiveRole.CEO_AND_CO_FOUNDER,
    }

    @classmethod
    def validate(cls, executive: ExecutiveProfile | None) -> ValidationResult:
        if executive is None or not executive.evidence:
            return ValidationResult(
                criterion="executive",
                status=ValidationStatus.UNKNOWN,
                reason="Executive UNKNOWN: Insufficient evidence — No executive leadership evidence provided.",
            )

        urls = [e.source_url for e in executive.evidence if e.source_url]
        ev_ids = [e.source_url for e in executive.evidence if e.source_url]
        max_conf = max((e.confidence for e in executive.evidence), default=0.0)

        if not executive.full_name or not executive.full_name.strip():
            return ValidationResult(
                criterion="executive",
                status=ValidationStatus.FAIL,
                reason="Executive FAIL: Executive full name is missing.",
                evidence_ids=ev_ids,
                source_urls=urls,
                confidence=max_conf,
            )

        if executive.role not in cls.ALLOWED_ROLES:
            return ValidationResult(
                criterion="executive",
                status=ValidationStatus.FAIL,
                reason=f"Executive FAIL: Role '{executive.role}' is not an authorized decision-maker (must be CEO or Co-founder).",
                evidence_ids=ev_ids,
                source_urls=urls,
                confidence=max_conf,
            )

        if not executive.is_current_leadership:
            return ValidationResult(
                criterion="executive",
                status=ValidationStatus.FAIL,
                reason="Executive FAIL: Identified executive is former leadership, not currently active.",
                evidence_ids=ev_ids,
                source_urls=urls,
                confidence=max_conf,
            )

        if not executive.identity_verified:
            return ValidationResult(
                criterion="executive",
                status=ValidationStatus.UNKNOWN,
                reason="Executive UNKNOWN: Executive identity could not be verified with high-confidence evidence.",
                evidence_ids=ev_ids,
                source_urls=urls,
                confidence=max_conf,
            )

        return ValidationResult(
            criterion="executive",
            status=ValidationStatus.PASS,
            reason=f"Executive PASS: Active decision maker '{executive.full_name}' ({executive.role.value}) verified.",
            evidence_ids=ev_ids,
            source_urls=urls,
            confidence=max_conf,
        )
