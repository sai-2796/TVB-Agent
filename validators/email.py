from models.email import ExecutiveEmail, EmailVerificationStatus, FinalEmailStatus, TechnicalStatus
from tools.generic_email import is_generic_email
from validators.financial import ValidationResult, ValidationStatus


class EmailValidator:
    """Deterministic validator enforcing TVB's Phase 7 Executive Email criterion."""

    @classmethod
    def validate(cls, exec_email: ExecutiveEmail | None) -> ValidationResult:
        if exec_email is None or not exec_email.email:
            return ValidationResult(
                criterion="email",
                status=ValidationStatus.UNKNOWN,
                reason="Email UNKNOWN: Insufficient evidence — Executive email verification pending or missing.",
            )

        email_str = exec_email.email.strip()
        urls = [e.source_url for e in exec_email.association_evidence + exec_email.technical_validation_evidence if e.source_url]
        ev_ids = [e.source_url for e in exec_email.association_evidence + exec_email.technical_validation_evidence if e.source_url]
        max_conf = max((e.confidence for e in exec_email.association_evidence), default=0.0)

        # Generic email check
        if exec_email.is_generic or is_generic_email(email_str) or exec_email.final_status == FinalEmailStatus.REJECTED:
            return ValidationResult(
                criterion="email",
                status=ValidationStatus.FAIL,
                reason=f"Email FAIL: Address '{email_str}' is a generic company mailbox.",
                evidence_ids=ev_ids,
                source_urls=urls,
                confidence=max_conf,
            )

        # Person-Email Association check
        if not exec_email.association_verified or not exec_email.association_evidence:
            return ValidationResult(
                criterion="email",
                status=ValidationStatus.UNKNOWN,
                reason=f"Email UNKNOWN: Candidate address '{email_str}' lacks public evidence associating it directly with the executive.",
                evidence_ids=ev_ids,
                source_urls=urls,
                confidence=max_conf,
            )

        # Technical deliverability verification check
        if exec_email.final_status != FinalEmailStatus.VERIFIED and exec_email.verification_status != EmailVerificationStatus.VERIFIED:
            return ValidationResult(
                criterion="email",
                status=ValidationStatus.UNKNOWN,
                reason=f"Email UNKNOWN: Address '{email_str}' deliverability status is '{exec_email.technical_status.value}' (must be DELIVERABLE/VERIFIED).",
                evidence_ids=ev_ids,
                source_urls=urls,
                confidence=max_conf,
            )

        return ValidationResult(
            criterion="email",
            status=ValidationStatus.PASS,
            reason=f"Email PASS: Verified direct executive email '{email_str}'.",
            evidence_ids=ev_ids,
            source_urls=urls,
            confidence=max_conf,
        )
