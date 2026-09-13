from models.company import CompanyResearch
from models.evidence import Evidence
from validators.platform import PlatformValidator, ValidationStatus


def make_evidence() -> Evidence:
    return Evidence(
        field="is_tech_platform",
        value="SaaS Platform",
        raw_claim="Cloud-based inventory dashboard and API",
        source_url="https://example.com/product",
        source_title="Product Overview",
        source_type="company_website",
        accessed_at="2026-09-12T23:50:00Z",
        confidence=0.9,
    )


def test_platform_validator():
    # Tech platform with evidence -> PASS
    c_tech = CompanyResearch(
        domain="techplatform.io",
        is_tech_platform=True,
        platform_evidence=[make_evidence()],
    )
    assert PlatformValidator.validate(c_tech).status == ValidationStatus.PASS

    # Non-tech business -> FAIL
    c_non_tech = CompanyResearch(
        domain="localstore.com",
        is_tech_platform=False,
        platform_evidence=[make_evidence()],
    )
    assert PlatformValidator.validate(c_non_tech).status == ValidationStatus.FAIL

    # No evidence -> UNKNOWN
    c_no_ev = CompanyResearch(
        domain="unknown.com",
        is_tech_platform=True,
        platform_evidence=[],
    )
    assert PlatformValidator.validate(c_no_ev).status == ValidationStatus.UNKNOWN
