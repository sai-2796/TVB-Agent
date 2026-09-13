import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from api.dependencies import get_lead_store
from api.schemas import EvidenceResponse, LeadDetailResponse, LeadSummaryResponse
from models.lead import QualificationStatus
from storage.lead_store import LeadStore

logger = logging.getLogger("tvb_agent.api.leads")
router = APIRouter(prefix="/api/leads", tags=["Leads"])


@router.get("", response_model=List[LeadSummaryResponse])
def list_leads(
    status_filter: Optional[QualificationStatus] = None,
    store: LeadStore = Depends(get_lead_store),
):
    """List stored leads with optional qualification status filter."""
    if status_filter == QualificationStatus.QUALIFIED:
        leads = store.list_qualified_leads()
    elif status_filter == QualificationStatus.UNQUALIFIED:
        leads = store.list_rejected_leads()
    else:
        leads = store.list_all_leads()

    return [
        LeadSummaryResponse(
            id=l.id,
            company_name=l.company_name,
            domain=l.domain,
            description=l.description,
            industry_sector=l.industry_sector,
            financial_summary=l.financial_summary,
            executive_name=l.executive_name,
            executive_role=l.executive_role,
            verified_executive_email=l.verified_executive_email,
            qualification_status=l.qualification_status,
            created_at=l.created_at,
        )
        for l in leads
    ]


@router.get("/{lead_id}", response_model=LeadDetailResponse)
def get_lead_detail(lead_id: str, store: LeadStore = Depends(get_lead_store)):
    """Fetch complete lead details including structured research payloads and evidence audit trails."""
    lead = store.get_lead(lead_id)
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lead '{lead_id}' not found.",
        )

    res = lead.research_payload
    fin_dict: Dict[str, Any] = {}
    plat_dict: Dict[str, Any] = {}
    us_dict: Dict[str, Any] = {}
    exec_dict: Dict[str, Any] = {}
    email_dict: Dict[str, Any] = {}
    evidence_list: List[EvidenceResponse] = []

    if res:
        if res.financials:
            fin_dict = res.financials.model_dump()
        if res.us_presence:
            us_dict = res.us_presence.model_dump()
        if res.executive:
            exec_dict = res.executive.model_dump()
        if res.executive_email:
            email_dict = res.executive_email.model_dump()

        plat_dict = {
            "platform_evidence_count": len(res.all_evidence),
            "domain": res.domain,
            "industry_sector": res.industry_sector,
        }

        for ev in res.all_evidence:
            evidence_list.append(
                EvidenceResponse(
                    field=ev.field,
                    value=ev.value,
                    claim=ev.raw_claim,
                    evidence_text=ev.evidence_text,
                    source_url=ev.source_url,
                    source_type=ev.source_type,
                    source_tier=ev.source_tier.value,
                    confidence=ev.confidence,
                    observed_at=ev.accessed_at,
                )
            )

    return LeadDetailResponse(
        id=lead.id,
        company_name=lead.company_name,
        domain=lead.domain,
        description=lead.description,
        industry_sector=lead.industry_sector,
        financial=fin_dict,
        platform=plat_dict,
        us_presence=us_dict,
        executive=exec_dict,
        email=email_dict,
        qualification_status=lead.qualification_status,
        rejection_reasons=lead.rejection_reasons,
        evidence=evidence_list,
        created_at=lead.created_at,
    )
