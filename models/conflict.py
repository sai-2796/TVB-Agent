from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ConflictRecord(BaseModel):
    """Model tracking data discrepancies across research sources."""

    conflict_id: str
    field_name: str  # e.g., "financials", "executive", "us_presence", "headquarters"
    competing_claims: List[Dict[str, Any]] = Field(default_factory=list)
    resolution_status: str  # "RESOLVED_BY_TIER", "RESOLVED_BY_RECENCY", "UNRESOLVED_UNKNOWN"
    winning_value: Any = None
    winning_evidence_id: Optional[str] = None
    created_at: str
