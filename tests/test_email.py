from models.email import ExecutiveEmail, EmailVerificationStatus
from models.evidence import Evidence, VerificationMethod
from tools.generic_email import is_generic_email
from validators.email import EmailValidator, ValidationStatus


def make_evidence() -> Evidence:
    return Evidence(
        field="executive_email",
        value="alex.smith@techplatform.io",
        raw_claim="Found contact email on official company press release",
        source_url="https://techplatform.io/press",
        source_title="Press Contact",
        source_type="press_release",
        accessed_at="2026-09-12T23:50:00Z",
        confidence=0.95,
        verification_method=VerificationMethod.API_CHECK,
    )


def test_generic_email_filter():
    generic_addresses = [
        "info@example.com",
        "contact@example.com",
        "hello@example.com",
        "support@example.com",
        "admin@example.com",
        "sales@example.com",
        "jobs@example.com",
        "INFO@EXAMPLE.COM",
        "info-us@example.com",
        "contact.us@example.com",
    ]

    for addr in generic_addresses:
        assert is_generic_email(addr) is True, f"Failed to reject generic address: {addr}"

    personal_addresses = [
        "alex.smith@techplatform.io",
        "john.doe@company.de",
        "founder@mytechstartup.co.uk",  # 'founder' is not in generic denylist
        "ceo@startup.ai",  # 'ceo' local part is personal/role-specific, not generic support
    ]

    for addr in personal_addresses:
        assert is_generic_email(addr) is False, f"Erroneously rejected personal address: {addr}"


def test_email_validator():
    # Fully verified, associated, non-generic email -> PASS
    valid_email = ExecutiveEmail(
        email="alex.smith@techplatform.io",
        verification_status=EmailVerificationStatus.VERIFIED,
        verification_method=VerificationMethod.API_CHECK,
        is_generic=False,
        association_verified=True,
        association_evidence=[make_evidence()],
        technical_validation_evidence=[make_evidence()],
    )
    res_valid = EmailValidator.validate(valid_email)
    assert res_valid.status == ValidationStatus.PASS

    # Generic email -> FAIL
    generic_email = ExecutiveEmail(
        email="info@techplatform.io",
        verification_status=EmailVerificationStatus.VERIFIED,
        is_generic=True,
        association_verified=True,
        association_evidence=[make_evidence()],
    )
    res_generic = EmailValidator.validate(generic_email)
    assert res_generic.status == ValidationStatus.FAIL
    assert "generic" in res_generic.reason

    # Unverified deliverability -> UNKNOWN
    unverified_email = ExecutiveEmail(
        email="alex.smith@techplatform.io",
        verification_status=EmailVerificationStatus.UNVERIFIED,
        association_verified=True,
        association_evidence=[make_evidence()],
    )
    res_unverified = EmailValidator.validate(unverified_email)
    assert res_unverified.status == ValidationStatus.UNKNOWN

    # Verified deliverability but NO identity association -> UNKNOWN
    unassociated_email = ExecutiveEmail(
        email="alex.smith@techplatform.io",
        verification_status=EmailVerificationStatus.VERIFIED,
        association_verified=False,  # e.g. MX lookup passed, pattern guessed, but no association proof
        association_evidence=[],
    )
    res_unassociated = EmailValidator.validate(unassociated_email)
    assert res_unassociated.status == ValidationStatus.UNKNOWN
    assert "lacks public evidence associating it" in res_unassociated.reason


def test_zerobounce_email_verifier_provider():
    from tools.email_verification import ZeroBounceEmailVerifierProvider
    provider = ZeroBounceEmailVerifierProvider(api_key="")
    res = provider.verify("john.doe@alphasaas.io", "alphasaas.io")
    assert res["is_deliverable"] is False
    assert res["final_status"] == "NOT_VERIFIED"

