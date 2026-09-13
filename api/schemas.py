from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from models.lead import QualificationStatus
from models.orchestrator import OrchestratorState, StopReason


class RunCreateRequest(BaseModel):
    target_qualified_leads: Optional[int] = Field(default=None, ge=1, le=100)
    max_discovery_iterations: Optional[int] = Field(default=None, ge=1, le=20)


class RunCreateResponse(BaseModel):
    run_id: str
    status: OrchestratorState
    target_qualified_leads: int
    started_at: str


class RunStatusResponse(BaseModel):
    run_id: str
    status: OrchestratorState
    stop_reason: Optional[StopReason] = None
    target_qualified_leads: int
    qualified_leads_count: int
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
    completed_at: Optional[str] = None


class LeadSummaryResponse(BaseModel):
    id: str
    company_name: str
    domain: str
    description: Optional[str] = None
    industry_sector: Optional[str] = None
    financial_summary: Optional[str] = None
    executive_name: Optional[str] = None
    executive_role: Optional[str] = None
    verified_executive_email: Optional[str] = None
    qualification_status: QualificationStatus
    created_at: str


class EvidenceResponse(BaseModel):
    field: str
    value: Optional[Any] = None
    claim: str
    evidence_text: Optional[str] = None
    source_url: str
    source_type: str
    source_tier: str
    confidence: float
    observed_at: str


class LeadDetailResponse(BaseModel):
    id: str
    company_name: str
    domain: str
    description: Optional[str] = None
    industry_sector: Optional[str] = None
    financial: Dict[str, Any] = Field(default_factory=dict)
    platform: Dict[str, Any] = Field(default_factory=dict)
    us_presence: Dict[str, Any] = Field(default_factory=dict)
    executive: Dict[str, Any] = Field(default_factory=dict)
    email: Dict[str, Any] = Field(default_factory=dict)
    qualification_status: QualificationStatus
    rejection_reasons: List[str] = Field(default_factory=list)
    evidence: List[EvidenceResponse] = Field(default_factory=list)
    created_at: str


class HealthCheckResponse(BaseModel):
    status: str = "ok"
    version: str = "1.0.0"
