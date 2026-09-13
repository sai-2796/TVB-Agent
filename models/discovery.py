from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DiscoveryConfig(BaseModel):
    """Configuration parameters governing the autonomous discovery loop."""

    target_min_financial_usd: float = 1_000_000.0
    target_max_financial_usd: float = 5_000_000.0
    maximum_iterations: int = 5
    maximum_queries_per_iteration: int = 3
    maximum_results_per_query: int = 2
    iteration_offset: int = 0
    maximum_candidates: int = 50
    geographic_focus: List[str] = Field(
        default_factory=lambda: ["Europe", "LATAM", "SEA", "MENA", "Global Non-US"]
    )
    technology_focus: List[str] = Field(
        default_factory=lambda: [
            "B2B SaaS",
            "AI",
            "HealthTech",
            "EdTech",
            "Cybersecurity",
            "Fintech",
            "TravelTech",
            "Digital Twin",
        ]
    )


class DiscoveredCandidate(BaseModel):
    """Data model representing a discovered candidate company and its discovery provenance."""

    candidate_id: str
    company_name: str
    company_domain: Optional[str] = None
    discovery_source_url: str
    discovery_source_title: str
    discovery_snippet: str
    discovery_timestamp: str
    discovery_hypothesis: str
    discovery_score: float = Field(default=0.5, ge=0.0, le=1.0)
    sector_hint: Optional[str] = None
    geo_hint: Optional[str] = None


class DiscoveryIterationLog(BaseModel):
    """Log entry recording an iteration of the discovery loop."""

    iteration_number: int
    hypothesis: str
    queries_executed: List[str]
    results_retrieved: int
    new_candidates_found: int
    timestamp: str


class DiscoveryResult(BaseModel):
    """Final result container produced by the autonomous discovery engine."""

    run_id: str
    candidates: List[DiscoveredCandidate]
    iterations_completed: int
    queries_executed: List[str]
    unique_domains_discovered: int
    stop_reason: str
    warnings: List[str] = Field(default_factory=list)
    discovery_timestamp: str
    iteration_logs: List[DiscoveryIterationLog] = Field(default_factory=list)
