export type QualificationStatus =
  | 'QUALIFIED'
  | 'REJECTED'
  | 'PENDING'
  | 'EMAIL_UNVERIFIED'
  | 'ERROR';

export type OrchestratorState =
  | 'IDLE'
  | 'DISCOVERING'
  | 'RESEARCHING'
  | 'VALIDATING'
  | 'CONTACT_RESEARCH'
  | 'EMAIL_VERIFICATION'
  | 'QUALIFIED'
  | 'REJECTED'
  | 'ITERATING'
  | 'COMPLETED'
  | 'EXHAUSTED'
  | 'FAILED';

export type StopReason =
  | 'TARGET_REACHED'
  | 'DISCOVERY_EXHAUSTED'
  | 'CANDIDATE_POOL_EXHAUSTED'
  | 'BUDGET_EXHAUSTED'
  | 'PROVIDER_FAILURE'
  | 'SYSTEM_ERROR'
  | 'MAX_ITERATIONS_REACHED'
  | 'USER_INTERRUPT';

export interface HealthResponse {
  status: string;
  version: string;
}

export interface RunCreateRequest {
  target_qualified_leads?: number;
  max_discovery_iterations?: number;
}

export interface RunCreateResponse {
  run_id: string;
  status: OrchestratorState;
  target_qualified_leads: number;
  started_at: string;
}

export interface RunStatusResponse {
  run_id: string;
  status: OrchestratorState;
  stop_reason?: StopReason | null;
  target_qualified_leads: number;
  qualified_leads_count: number;
  total_discovered: number;
  total_researched: number;
  total_rejected: number;
  total_email_attempts: number;
  iterations_completed: number;
  errors: string[];
  warnings: string[];
  started_at: string;
  completed_at?: string | null;
}

export interface LeadSummary {
  id: string;
  company_name: string;
  domain: string;
  description?: string | null;
  industry_sector?: string | null;
  financial_summary?: string | null;
  executive_name?: string | null;
  executive_role?: string | null;
  verified_executive_email?: string | null;
  qualification_status: QualificationStatus;
  created_at: string;
}

export interface Evidence {
  field: string;
  value?: any;
  claim: string;
  evidence_text?: string | null;
  source_url: string;
  source_type: string;
  source_tier: string;
  confidence: number;
  observed_at: string;
}

export interface LeadDetail {
  id: string;
  company_name: string;
  domain: string;
  description?: string | null;
  industry_sector?: string | null;
  financial: Record<string, any>;
  platform: Record<string, any>;
  us_presence: Record<string, any>;
  executive: Record<string, any>;
  email: Record<string, any>;
  qualification_status: QualificationStatus;
  rejection_reasons: string[];
  evidence: Evidence[];
  created_at: string;
}
