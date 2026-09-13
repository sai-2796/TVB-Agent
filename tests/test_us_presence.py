from models.us_presence import USPresenceData, USPresenceStatus
from models.evidence import Evidence
from validators.us_presence import USPresenceValidator, ValidationStatus


def make_evidence() -> Evidence:
    return Evidence(
        field="us_presence",
        value="Tallinn, Estonia",
        raw_claim="Headquarters in Tallinn, Estonia. No US offices.",
        source_url="https://example.com/about",
        source_title="Company Locations",
        source_type="company_website",
        accessed_at="2026-09-12T23:50:00Z",
        confidence=0.95,
    )


def test_us_presence_validator():
    # Verified No US Presence -> PASS
    u_none = USPresenceData(
        status=USPresenceStatus.VERIFIED_NO_US_PRESENCE,
        headquarters_country="Estonia",
        evidence=[make_evidence()],
    )
    assert USPresenceValidator.validate(u_none).status == ValidationStatus.PASS

    # Minimal US Presence -> PASS
    u_minimal = USPresenceData(
        status=USPresenceStatus.MINIMAL_US_PRESENCE,
        headquarters_country="Germany",
        evidence=[make_evidence()],
    )
    assert USPresenceValidator.validate(u_minimal).status == ValidationStatus.PASS

    # Significant US Presence -> FAIL
    u_significant = USPresenceData(
        status=USPresenceStatus.SIGNIFICANT_US_PRESENCE,
        headquarters_country="United States",
        office_locations=["San Francisco, CA"],
        evidence=[make_evidence()],
    )
    assert USPresenceValidator.validate(u_significant).status == ValidationStatus.FAIL

    # Unknown -> UNKNOWN
    u_unknown = USPresenceData(
        status=USPresenceStatus.UNKNOWN,
        evidence=[],
    )
    assert USPresenceValidator.validate(u_unknown).status == ValidationStatus.UNKNOWN
