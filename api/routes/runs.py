import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from api.dependencies import get_lead_store, get_orchestrator
from api.schemas import RunCreateRequest, RunCreateResponse, RunStatusResponse, LeadSummaryResponse
from agents.orchestrator import MasterOrchestrator, OrchestratorState
from storage.lead_store import LeadStore

logger = logging.getLogger("tvb_agent.api.runs")
router = APIRouter(prefix="/api/runs", tags=["Runs"])

# In-memory background task status cache for ongoing runs
_active_runs_cache: Dict[str, Dict[str, Any]] = {}


def _execute_background_run(run_id: str, orchestrator: MasterOrchestrator, target_leads: int, max_iters: int):
    """Background task worker executing the orchestrator run."""
    try:
        _active_runs_cache[run_id]["status"] = OrchestratorState.DISCOVERING.value
        result = orchestrator.run(target_qualified_leads=target_leads, max_iterations=max_iters)
        _active_runs_cache[run_id] = result.model_dump()
    except Exception as exc:
        logger.error(f"Background run execution failed for '{run_id}': {str(exc)}")
        if run_id in _active_runs_cache:
            _active_runs_cache[run_id]["status"] = OrchestratorState.FAILED.value
            _active_runs_cache[run_id]["errors"] = [str(exc)]
            _active_runs_cache[run_id]["completed_at"] = datetime.now(timezone.utc).isoformat()


@router.post("", response_model=RunCreateResponse, status_code=status.HTTP_202_ACCEPTED)
def create_run(
    payload: RunCreateRequest,
    background_tasks: BackgroundTasks,
    orchestrator: MasterOrchestrator = Depends(get_orchestrator),
    store: LeadStore = Depends(get_lead_store),
):
    """Start an autonomous lead discovery & qualification run in the background."""
    run_id = f"run_{uuid.uuid4().hex[:8]}"
    start_ts = datetime.now(timezone.utc).isoformat()
    target_count = payload.target_qualified_leads or orchestrator.budgets.target_qualified_leads
    max_iters = payload.max_discovery_iterations or orchestrator.budgets.max_discovery_iterations

    run_meta = {
        "run_id": run_id,
        "status": OrchestratorState.DISCOVERING.value,
        "target_qualified_leads": target_count,
        "qualified_leads_count": 0,
        "total_discovered": 0,
        "total_researched": 0,
        "total_rejected": 0,
        "total_email_attempts": 0,
        "iterations_completed": 0,
        "started_at": start_ts,
        "completed_at": None,
        "errors": [],
        "warnings": [],
    }

    _active_runs_cache[run_id] = run_meta
    store.save_run_metadata(run_id, run_meta, start_ts)

    background_tasks.add_task(_execute_background_run, run_id, orchestrator, target_count, max_iters)

    return RunCreateResponse(
        run_id=run_id,
        status=OrchestratorState.DISCOVERING,
        target_qualified_leads=target_count,
        started_at=start_ts,
    )


@router.get("", response_model=List[RunStatusResponse])
def list_runs(store: LeadStore = Depends(get_lead_store)):
    """List execution history of all autonomous runs."""
    meta_records = store.list_all_runs()
    runs_list: List[RunStatusResponse] = []

    # Merge with active in-memory cache if available
    cache_by_id = {k: v for k, v in _active_runs_cache.items()}
    seen_ids = set()

    for record in meta_records:
        r_id = record.get("run_id")
        if not r_id:
            continue
        seen_ids.add(r_id)

        data = cache_by_id.get(r_id, record)
        runs_list.append(
            RunStatusResponse(
                run_id=r_id,
                status=data.get("status", OrchestratorState.IDLE.value),
                stop_reason=data.get("stop_reason"),
                target_qualified_leads=data.get("target_qualified_leads", 15),
                qualified_leads_count=data.get("qualified_leads_count", data.get("total_qualified_count", 0)),
                total_discovered=data.get("total_discovered", data.get("total_discovered_count", 0)),
                total_researched=data.get("total_researched", data.get("total_researched_count", 0)),
                total_rejected=data.get("total_rejected", data.get("total_rejected_count", 0)),
                total_email_attempts=data.get("total_email_attempts", 0),
                iterations_completed=data.get("iterations_completed", data.get("iteration_number", 0)),
                errors=data.get("errors", []),
                warnings=data.get("warnings", []),
                started_at=data.get("started_at", ""),
                completed_at=data.get("completed_at"),
            )
        )

    for r_id, data in cache_by_id.items():
        if r_id not in seen_ids:
            runs_list.append(
                RunStatusResponse(
                    run_id=r_id,
                    status=data.get("status", OrchestratorState.DISCOVERING.value),
                    stop_reason=data.get("stop_reason"),
                    target_qualified_leads=data.get("target_qualified_leads", 15),
                    qualified_leads_count=data.get("qualified_leads_count", 0),
                    total_discovered=data.get("total_discovered", 0),
                    total_researched=data.get("total_researched", 0),
                    total_rejected=data.get("total_rejected", 0),
                    total_email_attempts=data.get("total_email_attempts", 0),
                    iterations_completed=data.get("iterations_completed", 0),
                    errors=data.get("errors", []),
                    warnings=data.get("warnings", []),
                    started_at=data.get("started_at", ""),
                    completed_at=data.get("completed_at"),
                )
            )

    return runs_list


@router.get("/{run_id}", response_model=RunStatusResponse)
def get_run_status(run_id: str, store: LeadStore = Depends(get_lead_store)):
    """Fetch status and telemetry metrics for a specific run."""
    data = _active_runs_cache.get(run_id)
    if not data:
        data = store.get_run_metadata(run_id)

    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run '{run_id}' not found.",
        )

    return RunStatusResponse(
        run_id=run_id,
        status=data.get("status", OrchestratorState.IDLE.value),
        stop_reason=data.get("stop_reason"),
        target_qualified_leads=data.get("target_qualified_leads", 15),
        qualified_leads_count=data.get("qualified_leads_count", data.get("total_qualified_count", 0)),
        total_discovered=data.get("total_discovered", data.get("total_discovered_count", 0)),
        total_researched=data.get("total_researched", data.get("total_researched_count", 0)),
        total_rejected=data.get("total_rejected", data.get("total_rejected_count", 0)),
        total_email_attempts=data.get("total_email_attempts", 0),
        iterations_completed=data.get("iterations_completed", data.get("iteration_number", 0)),
        errors=data.get("errors", []),
        warnings=data.get("warnings", []),
        started_at=data.get("started_at", ""),
        completed_at=data.get("completed_at"),
    )


@router.get("/{run_id}/leads", response_model=List[LeadSummaryResponse])
def get_run_qualified_leads(run_id: str, store: LeadStore = Depends(get_lead_store)):
    """Fetch qualified leads produced by a specific run."""
    data = _active_runs_cache.get(run_id) or store.get_run_metadata(run_id)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run '{run_id}' not found.",
        )

    # Return qualified leads stored in lead_store
    all_qualified = store.list_qualified_leads()
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
        for l in all_qualified
    ]
