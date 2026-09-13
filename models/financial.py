from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field
from .evidence import Evidence


class FinancialType(str, Enum):
    FUNDING = "funding"
    REVENUE = "revenue"
    VALUATION = "valuation"
    FUNDING_ROUND = "funding_round"
    UNKNOWN = "unknown"


class FinancialsData(BaseModel):
    """Financial research model distinguishing funding, revenue, valuation, and rounds."""

    financial_type: FinancialType = FinancialType.UNKNOWN
    amount_raw: float = 0.0
    currency: str = "USD"
    original_amount: float = 0.0
    original_currency: str = "USD"
    normalized_usd: Optional[float] = None
    financial_period: Optional[str] = None
    financial_source: Optional[str] = None
    is_total_amount: bool = False  # True ONLY if confirmed cumulative total funding or annual revenue
    is_in_range: bool = False  # True if 1M USD <= normalized_usd <= 5M USD
    evidence: List[Evidence] = Field(default_factory=list)
