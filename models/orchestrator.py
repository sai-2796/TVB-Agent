from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from models.discovery import DiscoveredCandidate
from models.company import CompanyResearch
from models.lead import Lead, QualificationStatus


class OrchestratorState(str, Enum):
    IDLE = "IDLE"
    DISCOVERING = "DISCOVERING"
    RESEARCHING = "RESEARCHING"
    VALIDATING = "VALIDATING"
    CONTACT_RESEARCH = "CONTACT_RESEARCH"
    EMAIL_VERIFICATION = "EMAIL_VERIFICATION"
    QUALIFIED = "QUALIFIED"
    REJECTED = "REJECTED"
    ITERATING = "ITERATING"
    COMPLETED = "COMPLETED"
    EXHAUSTED = "EXHAUSTED"
    FAILED = "FAILED"


class StopReason(str, Enum):
    TARGET_REACHED = "TARGET_REACHED"
    DISCOVERY_EXHAUSTED = "DISCOVERY_EXHAUSTED"
    CANDIDATE_POOL_EXHAUSTED = "CANDIDATE_POOL_EXHAUSTED"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"
    PROVIDER_FAILURE = "PROVIDER_FAILURE"
    SYSTEM_ERROR = "SYSTEM_ERROR"
    MAX_ITERATIONS_REACHED = "MAX_ITERATIONS_REACHED"
    USER_INTERRUPT = "USER_INTERRUPT"


class ExecutionBudgets(BaseModel):
    """Resource execution budgets for the autonomous run."""

    target_qualified_leads: int = 15
    max_discovery_iterations: int = 5
    max_total_candidates: int = 50
    max_candidates_researched: int = 50
    max_search_queries: int = 100
    max_pages_fetched: int = 150
    max_email_verifications: int = 50
    max_runtime_seconds: Optional[int] = None


class RunCheckpoint(BaseModel):
    """Structured, serializable run state for observability and checkpointing."""

    run_id: str
    started_at: str
    current_state: OrchestratorState = OrchestratorState.IDLE
    iteration_number: int = 0
    target_qualified_leads: int = 15
    total_discovered_count: int = 0
    total_researched_count: int = 0
    total_rejected_count: int = 0
    total_pending_count: int = 0
    total_qualified_count: int = 0
    total_email_attempts: int = 0
    total_contact_research_attempts: int = 0
    total_verified_email_count: int = 0
    total_search_queries: int = 0
    total_pages_fetched: int = 0
    current_candidate_domain: Optional[str] = None
    stop_reason: Optional[StopReason] = None
    completed_at: Optional[str] = None
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class AutonomousRunResult(BaseModel):
    """Structured result container produced by the master orchestrator."""

    run_id: str
    status: OrchestratorState
    stop_reason: StopReason
    target_qualified_leads: int
    qualified_leads_count: int
    qualified_leads: List[Lead] = Field(default_factory=list)
    total_discovered: int
    total_researched: int
    total_rejected: int
    total_email_attempts: int
    total_contact_research_attempts: int = 0
    total_verified_email_count: int = 0
    iterations_completed: int
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    started_at: str
    completed_at: str
