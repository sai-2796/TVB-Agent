from typing import List
from models.us_presence import USPresenceData, USPresenceStatus
from validators.financial import ValidationResult, ValidationStatus

US_LOCATION_KEYWORDS = {
    "united states",
    "usa",
    "us office",
    "san francisco",
    "new york",
    "austin",
    "boston",
    "silicon valley",
    "california",
    "seattle",
}


def contains_us_location(locations: List[str]) -> bool:
    """Checks if any office location in the list matches physical US presence keywords."""
    for loc in locations:
        loc_lower = loc.lower()
        if any(kw in loc_lower for kw in US_LOCATION_KEYWORDS):
            return True
    return False


class USPresenceValidator:
    """Deterministic validator for TVB US presence criteria (minimal to no US presence)."""

    @classmethod
    def validate(cls, us_data: USPresenceData | None) -> ValidationResult:
        if us_data is None or not us_data.evidence:
            return ValidationResult(
                criterion="us_presence",
                status=ValidationStatus.UNKNOWN,
                reason="US Presence UNKNOWN: Insufficient evidence — US operational footprint is unverified.",
            )

        urls = [e.source_url for e in us_data.evidence if e.source_url]
        ev_ids = [e.source_url for e in us_data.evidence if e.source_url]
        max_conf = max((e.confidence for e in us_data.evidence), default=0.0)

        hq = us_data.headquarters_country or ""
        is_us_hq = hq.lower() in ("united states", "usa", "us")
        has_us_office = contains_us_location(us_data.office_locations)

        # Disqualify if US HQ, US physical office, or SIGNIFICANT_US_PRESENCE
        if is_us_hq or has_us_office or us_data.status == USPresenceStatus.SIGNIFICANT_US_PRESENCE:
            reason_detail = "US Headquarters" if is_us_hq else ("US physical office" if has_us_office else "Significant US operational footprint")
            return ValidationResult(
                criterion="us_presence",
                status=ValidationStatus.FAIL,
                reason=f"US Presence FAIL: Disqualified due to {reason_detail}.",
                evidence_ids=ev_ids,
                source_urls=urls,
                confidence=max_conf,
            )

        # Pass if verified foreign HQ or minimal non-US presence
        if us_data.status in (USPresenceStatus.VERIFIED_NO_US_PRESENCE, USPresenceStatus.MINIMAL_US_PRESENCE):
            return ValidationResult(
                criterion="us_presence",
                status=ValidationStatus.PASS,
                reason=f"US Presence PASS: Verified minimal to no US footprint (HQ: {hq or 'Non-US'}).",
                evidence_ids=ev_ids,
                source_urls=urls,
                confidence=max_conf,
            )

        return ValidationResult(
            criterion="us_presence",
            status=ValidationStatus.UNKNOWN,
            reason="US Presence UNKNOWN: Unable to verify non-US status with high-confidence evidence.",
            evidence_ids=ev_ids,
            source_urls=urls,
            confidence=max_conf,
        )
