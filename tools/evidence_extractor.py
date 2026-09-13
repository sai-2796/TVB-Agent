import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from models.evidence import Evidence, FreshnessStatus, VerificationMethod
from tools.source_classifier import classify_source_type, get_source_tier

logger = logging.getLogger("tvb_agent.evidence_extractor")


class EvidenceExtractor:
    """
    Evidence Extraction component converting research page findings into structured,
    non-hallucinated Evidence objects backed by empirical text snippets.
    """

    @classmethod
    def create_evidence(
        cls,
        field: str,
        page_data: Dict[str, Any],
        raw_claim: str,
        evidence_text: str,
        value: Any = None,
        confidence: float = 0.8,
        verification_method: VerificationMethod = VerificationMethod.DIRECT_EXTRACTION,
        evidence_conflict_id: Optional[str] = None,
    ) -> Optional[Evidence]:
        """
        Creates a structured Evidence object from fetched page data.
        Returns None if page is inaccessible, content is empty, or snippet is missing/invalid.
        """

        if not page_data or not page_data.get("is_accessible", True):
            logger.info(f"EvidenceExtractor: Suppressed evidence creation for field '{field}' - page inaccessible or failed fetch.")
            return None

        source_url = page_data.get("url", "")
        if not source_url:
            logger.info(f"EvidenceExtractor: Suppressed evidence creation for field '{field}' - missing source URL.")
            return None

        # Verify evidence text snippet actually exists and is non-empty
        if not evidence_text or not evidence_text.strip():
            logger.info(f"EvidenceExtractor: Suppressed evidence creation for field '{field}' - no supporting evidence text provided.")
            return None

        page_title = page_data.get("page_title", "") or "Web Source"
        published_date = page_data.get("published_date")
        accessed_at = page_data.get("accessed_at") or datetime.now(timezone.utc).isoformat()

        # Classify source type & source tier
        source_type = classify_source_type(source_url, title=page_title, snippet=evidence_text)
        source_tier = get_source_tier(source_type)

        # Freshness determination
        freshness = FreshnessStatus.UNKNOWN
        if published_date:
            freshness = FreshnessStatus.CURRENT

        # Ensure confidence is clamped between 0.0 and 1.0
        clamped_confidence = max(0.0, min(1.0, float(confidence)))

        return Evidence(
            field=field,
            value=value,
            raw_claim=raw_claim,
            evidence_text=evidence_text,
            source_url=source_url,
            source_title=page_title,
            source_type=source_type.value,
            source_published_date=published_date,
            accessed_at=accessed_at,
            freshness_status=freshness,
            source_tier=source_tier,
            confidence=clamped_confidence,
            verification_method=verification_method,
            evidence_conflict_id=evidence_conflict_id,
        )
