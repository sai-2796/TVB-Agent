import pytest
from pydantic import ValidationError
from models.evidence import Evidence, SourceTier, FreshnessStatus, VerificationMethod


def test_evidence_confidence_validation():
    # Valid confidence 0.0 to 1.0 -> Success
    ev_valid = Evidence(
        field="test",
        raw_claim="claim",
        source_url="https://example.com",
        source_title="Title",
        source_type="press",
        accessed_at="2026-09-12T23:50:00Z",
        confidence=0.85,
    )
    assert ev_valid.confidence == 0.85

    # Invalid confidence > 1.0 -> ValidationError
    with pytest.raises(ValidationError):
        Evidence(
            field="test",
            raw_claim="claim",
            source_url="https://example.com",
            source_title="Title",
            source_type="press",
            accessed_at="2026-09-12T23:50:00Z",
            confidence=1.5,
        )

    # Invalid confidence < 0.0 -> ValidationError
    with pytest.raises(ValidationError):
        Evidence(
            field="test",
            raw_claim="claim",
            source_url="https://example.com",
            source_title="Title",
            source_type="press",
            accessed_at="2026-09-12T23:50:00Z",
            confidence=-0.1,
        )
