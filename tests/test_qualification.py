import pytest
from models.company import CompanyResearch
from models.evidence import Evidence, VerificationMethod
from models.financial import FinancialsData, FinancialType
from models.us_presence import USPresenceData, USPresenceStatus
from models.executive import ExecutiveProfile, ExecutiveRole
from models.email import ExecutiveEmail, EmailVerificationStatus
from models.lead import QualificationStatus
from models.conflict import ConflictRecord
from validators.qualification import QualificationEngine
from validators.financial import FinancialValidator, ValidationStatus
from validators.us_presence import USPresenceValidator
from validators.executive import ExecutiveValidator
from validators.email import EmailValidator


def make_evidence(field: str, value: str, url: str = "https://techplatform.io/press") -> Evidence:
    return Evidence(
        field=field,
        value=value,
        raw_claim=f"Claim for {field}: {value}",
        source_url=url,
        source_title="Source Title",
        source_type="press_release",
        accessed_at="2026-09-13T00:00:00Z",
        confidence=0.95,
        verification_method=VerificationMethod.DIRECT_EXTRACTION,
    )


def create_fully_qualifying_company() -> CompanyResearch:
    return CompanyResearch(
        domain="techplatform.io",
        company_name="TechPlatform Ltd",
        description="B2B SaaS supply chain platform",
        industry_sector="B2B SaaS",
        is_tech_platform=True,
        platform_summary="Cloud B2B SaaS dashboard",
        platform_evidence=[make_evidence("platform", "SaaS Dashboard")],
        financials=FinancialsData(
            financial_type=FinancialType.FUNDING,
            amount_raw=2500000.0,
            normalized_usd=2500000.0,
            is_total_amount=True,
            evidence=[make_evidence("financials", "$2.5M USD")],
        ),
        us_presence=USPresenceData(
            status=USPresenceStatus.VERIFIED_NO_US_PRESENCE,
            headquarters_country="Estonia",
            evidence=[make_evidence("us_presence", "HQ Estonia")],
        ),
        executive=ExecutiveProfile(
            full_name="Alex Smith",
            role=ExecutiveRole.CEO,
            identity_verified=True,
            is_current_leadership=True,
            evidence=[make_evidence("executive", "CEO Alex Smith")],
        ),
        executive_email=ExecutiveEmail(
            email="alex.smith@techplatform.io",
            verification_status=EmailVerificationStatus.VERIFIED,
            verification_method=VerificationMethod.API_CHECK,
            is_generic=False,
            association_verified=True,
            association_evidence=[make_evidence("email", "alex.smith@techplatform.io")],
            technical_validation_evidence=[make_evidence("email_mx", "Deliverable")],
        ),
    )


def test_financial_validator_strict_boundaries_and_rules():
    # 999,999 USD -> FAIL
    f999 = FinancialsData(financial_type=FinancialType.FUNDING, amount_raw=999999.0, normalized_usd=999999.0, is_total_amount=True, evidence=[make_evidence("f", "999k")])
    assert FinancialValidator.validate(f999).status == ValidationStatus.FAIL

    # 1,000,000 USD -> PASS
    f1m = FinancialsData(financial_type=FinancialType.FUNDING, amount_raw=1000000.0, normalized_usd=1000000.0, is_total_amount=True, evidence=[make_evidence("f", "1m")])
    assert FinancialValidator.validate(f1m).status == ValidationStatus.PASS

    # 5,000,000 USD -> PASS
    f5m = FinancialsData(financial_type=FinancialType.REVENUE, amount_raw=5000000.0, normalized_usd=5000000.0, is_total_amount=True, evidence=[make_evidence("f", "5m")])
    assert FinancialValidator.validate(f5m).status == ValidationStatus.PASS

    # 5,000,001 USD -> FAIL
    f5m1 = FinancialsData(financial_type=FinancialType.FUNDING, amount_raw=5000001.0, normalized_usd=5000001.0, is_total_amount=True, evidence=[make_evidence("f", "5m1")])
    assert FinancialValidator.validate(f5m1).status == ValidationStatus.FAIL

    # Valuation -> FAIL
    f_val = FinancialsData(financial_type=FinancialType.VALUATION, amount_raw=3000000.0, normalized_usd=3000000.0, is_total_amount=True, evidence=[make_evidence("f", "3m val")])
    assert FinancialValidator.validate(f_val).status == ValidationStatus.FAIL

    # Single funding round without cumulative evidence -> UNKNOWN
    f_round = FinancialsData(financial_type=FinancialType.FUNDING_ROUND, amount_raw=3000000.0, normalized_usd=3000000.0, is_total_amount=False, evidence=[make_evidence("f", "3m round")])
    assert FinancialValidator.validate(f_round).status == ValidationStatus.UNKNOWN


def test_us_presence_foreign_hq_with_us_office_fails():
    # Foreign HQ (India) but has US office in New York -> FAIL
    us_data = USPresenceData(
        status=USPresenceStatus.MINIMAL_US_PRESENCE,
        headquarters_country="India",
        office_locations=["Mumbai", "New York, NY"],
        evidence=[make_evidence("us", "Offices in Mumbai & New York")],
    )
    res = USPresenceValidator.validate(us_data)
    assert res.status == ValidationStatus.FAIL
    assert "US physical office" in res.reason


def test_us_presence_foreign_hq_no_us_office_passes():
    # Foreign HQ (India) with no US offices -> PASS
    us_data = USPresenceData(
        status=USPresenceStatus.VERIFIED_NO_US_PRESENCE,
        headquarters_country="India",
        office_locations=["Mumbai", "Bangalore"],
        evidence=[make_evidence("us", "Offices in Mumbai & Bangalore")],
    )
    res = USPresenceValidator.validate(us_data)
    assert res.status == ValidationStatus.PASS


def test_qualification_engine_all_five_pass():
    company = create_fully_qualifying_company()
    report = QualificationEngine.evaluate(company)
    assert report.is_qualified is True
    assert report.overall_status == QualificationStatus.QUALIFIED
    assert report.validation_version == "1.0"

    lead = QualificationEngine.build_lead("lead_100", company, "2026-09-13T00:00:00Z")
    assert lead.qualification_status == QualificationStatus.QUALIFIED
    assert lead.verified_executive_email == "alex.smith@techplatform.io"


def test_qualification_engine_email_pending_results_in_pending_status():
    # All 4 criteria PASS, but executive email is UNKNOWN (Phase 6 state) -> PENDING_CONTACT_VERIFICATION
    company = create_fully_qualifying_company()
    company.executive_email = ExecutiveEmail()  # Pending email

    report = QualificationEngine.evaluate(company)
    assert report.is_qualified is False
    assert report.overall_status == QualificationStatus.PENDING_CONTACT_VERIFICATION

    lead = QualificationEngine.build_lead("lead_101", company, "2026-09-13T00:00:00Z")
    assert lead.qualification_status == QualificationStatus.PENDING_CONTACT_VERIFICATION
    assert lead.verified_executive_email is None  # Never reveal unverified email!


def test_qualification_engine_unresolved_conflicts():
    company = create_fully_qualifying_company()
    company.conflicts.append(
        ConflictRecord(
            conflict_id="conf_99",
            field_name="financials",
            competing_claims=[{"val": 2000000}, {"val": 9000000}],
            resolution_status="UNRESOLVED_UNKNOWN",
            created_at="2026-09-13T00:00:00Z",
        )
    )

    report = QualificationEngine.evaluate(company)
    assert report.is_qualified is False
    assert report.overall_status == QualificationStatus.UNQUALIFIED
    assert report.financial_result.status == ValidationStatus.UNKNOWN
