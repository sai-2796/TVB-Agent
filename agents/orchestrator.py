import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set
from config.settings import Settings, get_settings
from storage.lead_store import LeadStore
from models.discovery import DiscoveryConfig, DiscoveredCandidate
from models.company import CompanyResearch
from models.lead import Lead, QualificationStatus
from models.orchestrator import (
    OrchestratorState,
    StopReason,
    ExecutionBudgets,
    RunCheckpoint,
    AutonomousRunResult,
)
from tools.interfaces import SearchProvider, WebResearchProvider, EmailVerificationProvider
from tools.search import get_search_provider
from tools.web_research import get_web_research_provider
from tools.email_verification import get_email_verification_provider
from tools.domain_utils import normalize_domain
from agents.discovery_agent import DiscoveryAgent, normalize_company_name_key
from agents.research_agent import ResearchAgent
from agents.contact_agent import ContactAgent
from validators.qualification import QualificationEngine, QualificationReport
from validators.financial import ValidationStatus

logger = logging.getLogger("tvb_agent.orchestrator")


class MasterOrchestrator:
    """
    Bounded Master Autonomous Orchestrator integrating Discovery, Research, Contact,
    and Deterministic Qualification into a closed-loop lead discovery engine.
    """

    def __init__(
        self,
        settings: Optional[Settings] = None,
        lead_store: Optional[LeadStore] = None,
        search_provider: Optional[SearchProvider] = None,
        web_provider: Optional[WebResearchProvider] = None,
        email_verifier: Optional[EmailVerificationProvider] = None,
        budgets: Optional[ExecutionBudgets] = None,
    ):
        self.settings = settings or get_settings()
        self.lead_store = lead_store or LeadStore(self.settings.sqlite_db_path)
        self.search_provider = search_provider or get_search_provider()
        self.web_provider = web_provider or get_web_research_provider()
        self.email_verifier = email_verifier or get_email_verification_provider()

        self.budgets = budgets or ExecutionBudgets(
            target_qualified_leads=self.settings.target_qualified_leads,
            max_total_candidates=self.settings.max_candidate_pool_size,
        )

        self.discovery_agent = DiscoveryAgent(search_provider=self.search_provider)
        self.research_agent = ResearchAgent(
            search_provider=self.search_provider, web_provider=self.web_provider
        )
        self.contact_agent = ContactAgent(
            email_verifier=self.email_verifier,
            search_provider=self.search_provider,
            web_provider=self.web_provider,
        )

    def run(
        self,
        target_qualified_leads: Optional[int] = None,
        max_iterations: Optional[int] = None,
    ) -> AutonomousRunResult:
        try:
            return self._run(target_qualified_leads, max_iterations)
        except BaseException as exc:
            context = getattr(self, "_active_run_context", None)
            if context:
                checkpoint, errors, warnings = context
                error_message = f"Run interrupted or failed: {type(exc).__name__}: {exc}"
                errors.append(error_message)
                checkpoint.errors = errors
                checkpoint.warnings = warnings
                checkpoint.current_state = OrchestratorState.FAILED
                checkpoint.stop_reason = StopReason.SYSTEM_ERROR
                checkpoint.completed_at = datetime.now(timezone.utc).isoformat()
                failed_metadata = checkpoint.model_dump()
                failed_metadata["status"] = OrchestratorState.FAILED.value
                self.lead_store.save_run_metadata(
                    checkpoint.run_id,
                    failed_metadata,
                    checkpoint.completed_at,
                )
                logger.exception("MasterOrchestrator run '%s' failed", checkpoint.run_id)
            raise
        finally:
            self._active_run_context = None

    def _run(
        self,
        target_qualified_leads: Optional[int] = None,
        max_iterations: Optional[int] = None,
    ) -> AutonomousRunResult:
        """
        Executes the autonomous end-to-end lead discovery, research, contact, and qualification pipeline.
        """
        run_id = f"run_{uuid.uuid4().hex[:8]}"
        start_ts = datetime.now(timezone.utc).isoformat()
        target_count = target_qualified_leads or self.budgets.target_qualified_leads
        max_iters = max_iterations or self.budgets.max_discovery_iterations

        checkpoint = RunCheckpoint(
            run_id=run_id,
            started_at=start_ts,
            current_state=OrchestratorState.IDLE,
            target_qualified_leads=target_count,
        )

        logger.info(f"MasterOrchestrator run '{run_id}' started. Target qualified leads: {target_count}, max iterations: {max_iters}")

        # Global candidate tracking & idempotency pools
        seen_domains: Set[str] = set()
        seen_names: Set[str] = set()
        researched_domains: Set[str] = set()

        # Load existing qualified domains from store to prevent duplicate insertion across runs
        existing_leads = self.lead_store.list_all_leads()
        for l in existing_leads:
            if l.domain:
                seen_domains.add(normalize_domain(l.domain))

        candidate_queue: List[DiscoveredCandidate] = []
        qualified_leads: List[Lead] = []
        errors: List[str] = []
        warnings: List[str] = []
        self._active_run_context = (checkpoint, errors, warnings)

        stop_reason: Optional[StopReason] = None
        for iteration in range(1, max_iters + 1):
            checkpoint.iteration_number = iteration
            if len(qualified_leads) >= target_count:
                stop_reason = StopReason.TARGET_REACHED
                logger.info(f"Run '{run_id}': Target qualified lead count ({target_count}) reached.")
                break

            if checkpoint.total_discovered_count >= self.budgets.max_total_candidates:
                stop_reason = StopReason.BUDGET_EXHAUSTED
                warnings.append(f"Reached max total candidates budget limit ({self.budgets.max_total_candidates}).")
                logger.info(f"Run '{run_id}': Max total candidates budget limit reached.")
                break

            remaining_queries = self.budgets.max_search_queries - checkpoint.total_search_queries
            if remaining_queries <= 0:
                stop_reason = StopReason.BUDGET_EXHAUSTED
                warnings.append(f"Reached max search queries budget limit ({self.budgets.max_search_queries}).")
                break

            # 1. DISCOVERY STAGE
            checkpoint.current_state = OrchestratorState.DISCOVERING
            logger.info(f"Run '{run_id}' Iteration {iteration}: Entering DISCOVERING state.")

            disc_config = DiscoveryConfig(
                maximum_iterations=1,  # Single iteration per outer orchestrator step
                maximum_queries_per_iteration=min(3, remaining_queries),
                maximum_results_per_query=2,
                iteration_offset=iteration - 1,
                maximum_candidates=min(20, self.budgets.max_total_candidates - checkpoint.total_discovered_count),
            )

            try:
                disc_res = self.discovery_agent.run_discovery(disc_config)
                checkpoint.total_search_queries += len(disc_res.queries_executed)
                warnings.extend(disc_res.warnings)

                new_disc_count = 0
                for cand in disc_res.candidates:
                    # Deduplicate globally
                    if cand.company_domain:
                        norm_dom = normalize_domain(cand.company_domain)
                        if norm_dom in seen_domains:
                            continue
                        seen_domains.add(norm_dom)
                        if cand.company_name:
                            seen_names.add(normalize_company_name_key(cand.company_name))
                    else:
                        name_key = normalize_company_name_key(cand.company_name)
                        if not name_key or name_key in seen_names:
                            continue
                        seen_names.add(name_key)

                    candidate_queue.append(cand)
                    new_disc_count += 1
                    checkpoint.total_discovered_count += 1

                logger.info(f"Run '{run_id}' Iteration {iteration}: Discovered {new_disc_count} new candidates.")

            except Exception as exc:
                err_msg = f"Discovery Agent failure in iteration {iteration}: {str(exc)}"
                logger.error(err_msg)
                errors.append(err_msg)
                if not candidate_queue:
                    stop_reason = StopReason.PROVIDER_FAILURE
                    break

            # 2. CANDIDATE PROCESSING LOOP
            while candidate_queue and len(qualified_leads) < target_count:
                cand = candidate_queue.pop(0)
                domain = cand.company_domain or normalize_domain(cand.discovery_source_url) or f"cand_{cand.candidate_id}.com"
                checkpoint.current_candidate_domain = domain

                if domain in researched_domains:
                    continue
                researched_domains.add(domain)

                # Check research budget
                if checkpoint.total_researched_count >= self.budgets.max_candidates_researched:
                    stop_reason = StopReason.BUDGET_EXHAUSTED
                    warnings.append(f"Reached max candidates researched budget limit ({self.budgets.max_candidates_researched}).")
                    break

                remaining_pages = self.budgets.max_pages_fetched - checkpoint.total_pages_fetched
                if remaining_pages <= 0:
                    stop_reason = StopReason.BUDGET_EXHAUSTED
                    warnings.append(f"Reached max pages budget limit ({self.budgets.max_pages_fetched}).")
                    break

                # STEP 1: RESEARCH
                checkpoint.current_state = OrchestratorState.RESEARCHING
                logger.info(f"Processing candidate '{cand.company_name}' ({domain}) - RESEARCHING")

                try:
                    research_payload = self.research_agent.research_candidate(
                        cand,
                        depth="standard",
                        max_pages=min(self.settings.max_pages_per_candidate, remaining_pages),
                    )
                    checkpoint.total_researched_count += 1
                    checkpoint.total_pages_fetched += len(research_payload.sources_consulted)
                    warnings.extend(research_payload.warnings)
                except Exception as exc:
                    err_msg = f"Research failed for '{domain}': {str(exc)}"
                    logger.error(err_msg)
                    errors.append(err_msg)
                    checkpoint.total_rejected_count += 1
                    continue

                # STEP 2 & 3: DETERMINISTIC CHEAP VALIDATION
                checkpoint.current_state = OrchestratorState.VALIDATING
                try:
                    report = QualificationEngine.evaluate(research_payload)
                except Exception as exc:
                    err_msg = f"Validation failed for '{domain}': {str(exc)}"
                    logger.exception(err_msg)
                    errors.append(err_msg)
                    checkpoint.total_rejected_count += 1
                    continue

                non_email_pass = (
                    report.financial_result.status == ValidationStatus.PASS
                    and report.platform_result.status == ValidationStatus.PASS
                    and report.us_presence_result.status == ValidationStatus.PASS
                    and report.executive_result.status == ValidationStatus.PASS
                )

                if not non_email_pass:
                    # REJECT immediately! Resource efficiency: Do NOT execute expensive contact research for non-qualifying companies.
                    checkpoint.current_state = OrchestratorState.REJECTED
                    checkpoint.total_rejected_count += 1
                    lead_rejected = QualificationEngine.build_lead(
                        lead_id=f"lead_{uuid.uuid4().hex[:8]}",
                        company_research=research_payload,
                        created_at=datetime.now(timezone.utc).isoformat(),
                    )
                    self.lead_store.save_lead(lead_rejected)
                    logger.info(f"Candidate '{domain}' REJECTED during cheap non-email validation.")
                    continue

                # STEP 4, 5, 6, 7: CONTACT RESEARCH & EMAIL VERIFICATION
                checkpoint.current_state = OrchestratorState.CONTACT_RESEARCH
                if checkpoint.total_email_attempts >= self.budgets.max_email_verifications:
                    stop_reason = StopReason.BUDGET_EXHAUSTED
                    warnings.append(f"Reached max email verifications budget limit ({self.budgets.max_email_verifications}).")
                    break
                checkpoint.total_contact_research_attempts += 1
                logger.info(f"Candidate '{domain}' PASSED non-email criteria. Proceeding to CONTACT_RESEARCH & EMAIL_VERIFICATION.")

                checkpoint.current_state = OrchestratorState.EMAIL_VERIFICATION
                checkpoint.total_email_attempts += 1

                try:
                    verified_exec_email = self.contact_agent.process_contact_verification(research_payload)
                    research_payload.executive_email = verified_exec_email
                    if getattr(verified_exec_email.final_status, "value", None) == "VERIFIED":
                        checkpoint.total_verified_email_count += 1
                except Exception as exc:
                    err_msg = f"Contact agent failure for '{domain}': {str(exc)}"
                    logger.error(err_msg)
                    errors.append(err_msg)

                # STEP 8: FINAL QUALIFICATION ENGINE EVALUATION
                try:
                    final_report = QualificationEngine.evaluate(research_payload)
                except Exception as exc:
                    err_msg = f"Final validation failed for '{domain}': {str(exc)}"
                    logger.exception(err_msg)
                    errors.append(err_msg)
                    checkpoint.total_rejected_count += 1
                    continue
                now_ts = datetime.now(timezone.utc).isoformat()
                lead_final = QualificationEngine.build_lead(
                    lead_id=f"lead_{uuid.uuid4().hex[:8]}",
                    company_research=research_payload,
                    created_at=now_ts,
                )

                if final_report.is_qualified and final_report.overall_status == QualificationStatus.QUALIFIED:
                    checkpoint.current_state = OrchestratorState.QUALIFIED
                    checkpoint.total_qualified_count += 1

                    # Check duplicate store before saving qualified lead
                    self.lead_store.save_lead(lead_final)
                    qualified_leads.append(lead_final)
                    logger.info(f"Candidate '{domain}' QUALIFIED! Total qualified: {len(qualified_leads)}/{target_count}")
                else:
                    checkpoint.current_state = OrchestratorState.REJECTED
                    checkpoint.total_rejected_count += 1
                    self.lead_store.save_lead(lead_final)
                    logger.info(f"Candidate '{domain}' failed final qualification (status={final_report.overall_status.value}). REJECTED.")

                if len(qualified_leads) >= target_count:
                    stop_reason = StopReason.TARGET_REACHED
                    break

            # Iteration transition check
            if len(qualified_leads) >= target_count:
                stop_reason = StopReason.TARGET_REACHED
                break
            elif stop_reason:
                break

            checkpoint.current_state = OrchestratorState.ITERATING

        # Final Stop Reason Assessment
        if len(qualified_leads) >= target_count:
            stop_reason = StopReason.TARGET_REACHED
        elif not stop_reason:
            if not candidate_queue:
                stop_reason = StopReason.CANDIDATE_POOL_EXHAUSTED
            else:
                stop_reason = StopReason.MAX_ITERATIONS_REACHED

        if stop_reason == StopReason.TARGET_REACHED:
            final_state = OrchestratorState.COMPLETED
        elif stop_reason in (StopReason.DISCOVERY_EXHAUSTED, StopReason.CANDIDATE_POOL_EXHAUSTED):
            final_state = OrchestratorState.EXHAUSTED if len(qualified_leads) < target_count else OrchestratorState.COMPLETED
        elif stop_reason in (StopReason.SYSTEM_ERROR, StopReason.PROVIDER_FAILURE):
            final_state = OrchestratorState.FAILED
        else:
            final_state = OrchestratorState.COMPLETED

        end_ts = datetime.now(timezone.utc).isoformat()
        checkpoint.current_state = final_state
        checkpoint.stop_reason = stop_reason
        checkpoint.completed_at = end_ts

        # Save run telemetry metadata to LeadStore
        run_meta = checkpoint.model_dump()
        run_meta["status"] = final_state.value
        self.lead_store.save_run_metadata(run_id, run_meta, end_ts)

        logger.info(
            f"MasterOrchestrator run '{run_id}' finished. Status: {final_state.value}, Stop Reason: {stop_reason.value}, Qualified Leads: {len(qualified_leads)}/{target_count}"
        )

        return AutonomousRunResult(
            run_id=run_id,
            status=final_state,
            stop_reason=stop_reason,
            target_qualified_leads=target_count,
            qualified_leads_count=len(qualified_leads),
            qualified_leads=qualified_leads,
            total_discovered=checkpoint.total_discovered_count,
            total_researched=checkpoint.total_researched_count,
            total_rejected=checkpoint.total_rejected_count,
            total_email_attempts=checkpoint.total_email_attempts,
            total_contact_research_attempts=checkpoint.total_contact_research_attempts,
            total_verified_email_count=checkpoint.total_verified_email_count,
            iterations_completed=checkpoint.iteration_number,
            errors=errors,
            warnings=warnings,
            started_at=start_ts,
            completed_at=end_ts,
        )
