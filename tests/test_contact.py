import pytest
from models.company import CompanyResearch
from models.evidence import Evidence, VerificationMethod, SourceTier
from models.financial import FinancialsData, FinancialType
from models.us_presence import USPresenceData, USPresenceStatus
from models.executive import ExecutiveProfile, ExecutiveRole
from models.email import ExecutiveEmail, EmailVerificationStatus, TechnicalStatus, FinalEmailStatus
from models.lead import QualificationStatus
from tools.email_verification import MockEmailVerificationProvider, MXFallbackProvider
from tools.generic_email import is_generic_email
from agents.contact_agent import ContactAgent, generate_candidate_email_patterns
from validators.qualification import QualificationEngine
from validators.email import EmailValidator, ValidationStatus


def make_evidence(field: str, value: str, text: str, url: str = "https://techplatform.io/team") -> Evidence:
    return Evidence(
        field=field,
        value=value,
        raw_claim=text,
        evidence_text=text,
        source_url=url,
        source_title="Company Team",
        source_type="company_team",
        accessed_at="2026-09-13T00:00:00Z",
        source_tier=SourceTier.TIER_1,
        confidence=0.95,
        verification_method=VerificationMethod.DIRECT_EXTRACTION,
    )


def test_generate_candidate_email_patterns():
    patterns = generate_candidate_email_patterns("Alex", "Smith", "techplatform.io")
    assert "alex.smith@techplatform.io" in patterns
    assert "alex@techplatform.io" in patterns
    assert "asmith@techplatform.io" in patterns


def test_contact_agent_verified_email_success():
    company = CompanyResearch(
        domain="techplatform.io",
        company_name="TechPlatform Ltd",
        executive=ExecutiveProfile(
            full_name="Alex Smith",
            role=ExecutiveRole.CEO,
            identity_verified=True,
            is_current_leadership=True,
            evidence=[make_evidence("executive", "Alex Smith", "Alex Smith is CEO")],
        ),
        all_evidence=[
            make_evidence(
                "email",
                "alex.smith@techplatform.io",
                "Contact CEO Alex Smith at alex.smith@techplatform.io for inquiries.",
                url="https://techplatform.io/contact",
            )
        ],
    )

    mock_verifier = MockEmailVerificationProvider(mock_status_map={"alex.smith@techplatform.io": "deliverable"})
    agent = ContactAgent(email_verifier=mock_verifier)

    exec_email = agent.process_contact_verification(company)

    assert exec_email.email == "alex.smith@techplatform.io"
    assert exec_email.association_verified is True
    assert exec_email.technical_status == TechnicalStatus.DELIVERABLE
    assert exec_email.final_status == FinalEmailStatus.VERIFIED
    assert exec_email.verification_status == EmailVerificationStatus.VERIFIED


def test_contact_agent_generic_email_rejection():
    # Test all generic prefixes
    generics = ["info@co.com", "contact@co.com", "hello@co.com", "support@co.com", "admin@co.com", "sales@co.com", "jobs@co.com", "careers@co.com"]
    for addr in generics:
        assert is_generic_email(addr) is True

    company = CompanyResearch(
        domain="techplatform.io",
        executive=ExecutiveProfile(
            full_name="Alex Smith",
            role=ExecutiveRole.CEO,
            identity_verified=True,
            is_current_leadership=True,
            evidence=[make_evidence("executive", "Alex Smith", "Alex Smith is CEO")],
        ),
        all_evidence=[
            make_evidence("email", "info@techplatform.io", "Contact info@techplatform.io for general questions")
        ],
    )

    agent = ContactAgent(email_verifier=MockEmailVerificationProvider())
    exec_email = agent.process_contact_verification(company)

    # Generic email address rejected!
    assert exec_email.final_status in (FinalEmailStatus.REJECTED, FinalEmailStatus.NOT_VERIFIED)


def test_contact_agent_pattern_hypothesis_without_association_fails():
    # Candidate email generated from pattern without direct text proof in evidence
    company = CompanyResearch(
        domain="techplatform.io",
        executive=ExecutiveProfile(
            full_name="Alex Smith",
            role=ExecutiveRole.CEO,
            identity_verified=True,
            is_current_leadership=True,
            evidence=[make_evidence("executive", "Alex Smith", "Alex Smith is CEO")],
        ),
        all_evidence=[],  # No direct email mentioned in evidence text!
    )

    mock_verifier = MockEmailVerificationProvider(mock_status_map={"alex.smith@techplatform.io": "deliverable"})
    agent = ContactAgent(email_verifier=mock_verifier)

    exec_email = agent.process_contact_verification(company)

    # Pattern hypothesis without public evidence association CANNOT become VERIFIED!
    assert exec_email.association_verified is False
    assert exec_email.final_status == FinalEmailStatus.NOT_VERIFIED
    assert exec_email.verification_status == EmailVerificationStatus.UNVERIFIED


def test_mx_fallback_provider_does_not_falsely_report_verified():
    fallback = MXFallbackProvider()
    res = fallback.verify("alex.smith@gmail.com", "gmail.com")

    # MX check valid != VERIFIED!
    assert res["technical_status"] == TechnicalStatus.MX_VALIDATED.value
    assert res["final_status"] == FinalEmailStatus.NOT_VERIFIED.value
    assert res["is_deliverable"] is False


def test_qualification_engine_integration_with_phase7_email():
    # Company with all non-email criteria PASS + Phase 7 verified email -> QUALIFIED
    company_pass = CompanyResearch(
        domain="techplatform.io",
        company_name="TechPlatform Ltd",
        is_tech_platform=True,
        platform_evidence=[make_evidence("platform", "SaaS Platform", "Cloud B2B SaaS")],
        financials=FinancialsData(
            financial_type=FinancialType.FUNDING,
            amount_raw=2500000.0,
            normalized_usd=2500000.0,
            is_total_amount=True,
            evidence=[make_evidence("fin", "2.5M", "Total funding $2.5M")],
        ),
        us_presence=USPresenceData(
            status=USPresenceStatus.VERIFIED_NO_US_PRESENCE,
            headquarters_country="Estonia",
            evidence=[make_evidence("us", "Estonia", "HQ Estonia")],
        ),
        executive=ExecutiveProfile(
            full_name="Alex Smith",
            role=ExecutiveRole.CEO,
            identity_verified=True,
            is_current_leadership=True,
            evidence=[make_evidence("exec", "Alex Smith", "CEO Alex Smith")],
        ),
        executive_email=ExecutiveEmail(
            email="alex.smith@techplatform.io",
            association_verified=True,
            association_evidence=[make_evidence("email", "alex.smith@techplatform.io", "Contact Alex Smith at alex.smith@techplatform.io")],
            technical_status=TechnicalStatus.DELIVERABLE,
            final_status=FinalEmailStatus.VERIFIED,
            verification_status=EmailVerificationStatus.VERIFIED,
            is_generic=False,
        ),
    )

    report_pass = QualificationEngine.evaluate(company_pass)
    assert report_pass.is_qualified is True
    assert report_pass.overall_status == QualificationStatus.QUALIFIED

    # Company with all non-email criteria PASS + unverified pattern-only email -> PENDING_CONTACT_VERIFICATION
    company_unverified_email = company_pass.model_copy(deep=True)
    company_unverified_email.executive_email = ExecutiveEmail(
        email="alex.smith@techplatform.io",
        association_verified=False,  # Unverified association!
        technical_status=TechnicalStatus.MX_VALIDATED,
        final_status=FinalEmailStatus.NOT_VERIFIED,
        verification_status=EmailVerificationStatus.UNVERIFIED,
    )

    report_unverified = QualificationEngine.evaluate(company_unverified_email)
    assert report_unverified.is_qualified is False
    assert report_unverified.overall_status == QualificationStatus.PENDING_CONTACT_VERIFICATION
