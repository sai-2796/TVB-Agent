import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from models.evidence import Evidence, SourceTier
from models.conflict import ConflictRecord

logger = logging.getLogger("tvb_agent.conflict_resolver")


class ConflictResolver:
    """
    Detects and conservatively resolves data discrepancies across research sources
    based on SourceTier hierarchy and evidence freshness.
    """

    @classmethod
    def resolve_financial_evidence(
        cls, evidence_list: List[Evidence]
    ) -> Tuple[Optional[Evidence], Optional[ConflictRecord]]:
        """
        Evaluates competing financial evidence claims.
        Returns the winning Evidence and an optional ConflictRecord if discrepancies were detected.
        """
        if not evidence_list:
            return None, None

        if len(evidence_list) == 1:
            return evidence_list[0], None

        # Filter out evidence items where value is None or non-numeric
        valid_ev = [e for e in evidence_list if e.value is not None and isinstance(e.value, (int, float))]
        if not valid_ev:
            return evidence_list[0], None

        # Group evidence by raw claim text snippet to avoid comparing different financial metrics (e.g. revenue vs funding round vs valuation)
        values = [e.value for e in valid_ev]

        # Only declare a conflict if values vary by > 20%
        if len(values) >= 2 and (max(values) - min(values)) / max(values) > 0.2:
            logger.warning(f"Financial conflict detected between values {min(values)} and {max(values)}")

            # Sort by SourceTier priority (Tier 1 first) then by published date/confidence
            sorted_evidence = sorted(
                valid_ev,
                key=lambda e: (
                    e.source_tier == SourceTier.TIER_1,
                    e.source_tier == SourceTier.TIER_2,
                    e.confidence,
                ),
                reverse=True,
            )

            winner = sorted_evidence[0]
            conflict_rec = ConflictRecord(
                conflict_id=f"conf_{uuid.uuid4().hex[:8]}",
                field_name="financials",
                competing_claims=[
                    {
                        "source_url": e.source_url,
                        "value": e.value,
                        "tier": e.source_tier.value,
                        "raw_claim": e.raw_claim,
                    }
                    for e in valid_ev
                ],
                resolution_status="RESOLVED_BY_TIER",
                winning_value=winner.value,
                winning_evidence_id=winner.source_url,
                created_at=datetime.now(timezone.utc).isoformat(),
            )
            return winner, conflict_rec

        return valid_ev[0], None

    @classmethod
    def resolve_executive_evidence(
        cls, evidence_list: List[Evidence]
    ) -> Tuple[Optional[Evidence], Optional[ConflictRecord]]:
        """
        Evaluates competing executive leadership claims.
        Returns winning Evidence and optional ConflictRecord.
        """
        if not evidence_list:
            return None, None

        if len(evidence_list) == 1:
            return evidence_list[0], None

        names = {str(e.value).lower().strip() for e in evidence_list if e.value}

        if len(names) >= 2:
            logger.warning(f"Executive leadership conflict detected between names: {names}")

            # Sort by SourceTier priority
            sorted_evidence = sorted(
                evidence_list,
                key=lambda e: (
                    e.source_tier == SourceTier.TIER_1,
                    e.source_tier == SourceTier.TIER_2,
                    e.confidence,
                ),
                reverse=True,
            )

            # If top source is Tier 1 (e.g. official website / team page), resolve to Tier 1 winner
            if sorted_evidence[0].source_tier == SourceTier.TIER_1:
                winner = sorted_evidence[0]
                conflict_rec = ConflictRecord(
                    conflict_id=f"conf_{uuid.uuid4().hex[:8]}",
                    field_name="executive",
                    competing_claims=[
                        {
                            "source_url": e.source_url,
                            "value": e.value,
                            "tier": e.source_tier.value,
                            "raw_claim": e.raw_claim,
                        }
                        for e in evidence_list
                    ],
                    resolution_status="RESOLVED_BY_TIER",
                    winning_value=winner.value,
                    winning_evidence_id=winner.source_url,
                    created_at=datetime.now(timezone.utc).isoformat(),
                )
                return winner, conflict_rec
            else:
                # Unresolved conflict between low-confidence sources -> Return None (UNKNOWN)
                conflict_rec = ConflictRecord(
                    conflict_id=f"conf_{uuid.uuid4().hex[:8]}",
                    field_name="executive",
                    competing_claims=[
                        {
                            "source_url": e.source_url,
                            "value": e.value,
                            "tier": e.source_tier.value,
                            "raw_claim": e.raw_claim,
                        }
                        for e in evidence_list
                    ],
                    resolution_status="UNRESOLVED_UNKNOWN",
                    winning_value=None,
                    winning_evidence_id=None,
                    created_at=datetime.now(timezone.utc).isoformat(),
                )
                return None, conflict_rec

        return evidence_list[0], None
