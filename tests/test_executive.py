from models.executive import ExecutiveProfile, ExecutiveRole
from models.evidence import Evidence
from validators.executive import ExecutiveValidator, ValidationStatus


def make_evidence() -> Evidence:
    return Evidence(
        field="executive",
        value="Alex Smith",
        raw_claim="Alex Smith is CEO & Co-founder",
        source_url="https://example.com/about",
        source_title="About Us",
        source_type="company_website",
        accessed_at="2026-09-12T23:50:00Z",
        confidence=0.9,
    )


def test_executive_validator():
    # Active CEO -> PASS
    ceo = ExecutiveProfile(
        full_name="Alex Smith",
        role=ExecutiveRole.CEO,
        identity_verified=True,
        is_current_leadership=True,
        evidence=[make_evidence()],
    )
    assert ExecutiveValidator.validate(ceo).status == ValidationStatus.PASS

    # Active Co-founder -> PASS
    cofounder = ExecutiveProfile(
        full_name="Jane Doe",
        role=ExecutiveRole.CO_FOUNDER,
        identity_verified=True,
        is_current_leadership=True,
        evidence=[make_evidence()],
    )
    assert ExecutiveValidator.validate(cofounder).status == ValidationStatus.PASS

    # Active CEO & Co-founder -> PASS
    both = ExecutiveProfile(
        full_name="Alex Smith",
        role=ExecutiveRole.CEO_AND_CO_FOUNDER,
        identity_verified=True,
        is_current_leadership=True,
        evidence=[make_evidence()],
    )
    assert ExecutiveValidator.validate(both).status == ValidationStatus.PASS

    # Former CEO -> FAIL
    former = ExecutiveProfile(
        full_name="Old Leader",
        role=ExecutiveRole.CEO,
        identity_verified=True,
        is_current_leadership=False,  # Resigned / Former leadership
        evidence=[make_evidence()],
    )
    res_former = ExecutiveValidator.validate(former)
    assert res_former.status == ValidationStatus.FAIL
    assert "former leadership" in res_former.reason

    # Missing identity verification -> UNKNOWN
    unverified_id = ExecutiveProfile(
        full_name="Alex Smith",
        role=ExecutiveRole.CEO,
        identity_verified=False,
        is_current_leadership=True,
        evidence=[make_evidence()],
    )
    res_id = ExecutiveValidator.validate(unverified_id)
    assert res_id.status == ValidationStatus.UNKNOWN

    # Unauthorized role (e.g. Other / VP) -> FAIL
    other_role = ExecutiveProfile(
        full_name="Bob VP",
        role=ExecutiveRole.OTHER,
        identity_verified=True,
        is_current_leadership=True,
        evidence=[make_evidence()],
    )
    res_role = ExecutiveValidator.validate(other_role)
    assert res_role.status == ValidationStatus.FAIL
