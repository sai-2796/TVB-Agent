import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set
from models.discovery import (
    DiscoveredCandidate,
    DiscoveryConfig,
    DiscoveryIterationLog,
    DiscoveryResult,
)
from tools.domain_utils import normalize_domain
from tools.interfaces import SearchProvider
from agents.hypothesis_generator import HypothesisGenerator
from agents.candidate_extractor import CandidateExtractor

logger = logging.getLogger("tvb_agent.discovery_agent")


def normalize_company_name_key(name: str) -> str:
    """Normalizes company name for conservative deduplication fallback when domain is missing."""
    if not name:
        return ""
    cleaned = re.sub(r"[^a-zA-Z0-9]", "", name.lower())
    return cleaned


class DiscoveryAgent:
    """
    Autonomous, hypothesis-driven discovery engine that iteratively discovers new candidate companies.
    Enforces bounded loops, query diversification, candidate deduplication, and gap analysis.
    """

    def __init__(self, search_provider: SearchProvider, config: Optional[DiscoveryConfig] = None):
        self.search_provider = search_provider
        self.config = config or DiscoveryConfig()

    def _analyze_discovery_gaps(self, candidates: List[DiscoveredCandidate]) -> List[str]:
        """
        Analyzes the current candidate pool to identify composition gaps
        (e.g., sector imbalance, geographic imbalance, missing financial signals).
        """
        gaps: List[str] = []
        if not candidates:
            return ["empty_pool"]

        sector_counts: Dict[str, int] = {}
        domain_count = 0

        for cand in candidates:
            if cand.company_domain:
                domain_count += 1
            sec = cand.sector_hint or "unknown"
            sector_counts[sec] = sector_counts.get(sec, 0) + 1

        # Check if canonical domain coverage is low
        if domain_count / len(candidates) < 0.5:
            gaps.append("domain_coverage")

        # Check sector diversity
        if len(sector_counts) < 3:
            gaps.append("tech_sector")

        return gaps

    def run_discovery(self, config: Optional[DiscoveryConfig] = None) -> DiscoveryResult:
        """
        Executes the bounded autonomous discovery loop until a stopping condition is satisfied.
        """
        active_config = config or self.config
        run_id = f"disc_run_{uuid.uuid4().hex[:8]}"
        start_timestamp = datetime.now(timezone.utc).isoformat()

        logger.info(
            f"Starting Discovery Agent run '{run_id}' (max_iterations={active_config.maximum_iterations}, max_candidates={active_config.maximum_candidates})"
        )

        hypothesis_gen = HypothesisGenerator(active_config)

        candidates: List[DiscoveredCandidate] = []
        seen_domains: Set[str] = set()
        seen_names: Set[str] = set()
        executed_queries: List[str] = []
        iteration_logs: List[DiscoveryIterationLog] = []
        warnings: List[str] = []

        stop_reason = "maximum_iterations"
        consecutive_zero_yield_iterations = 0

        first_iteration = active_config.iteration_offset + 1
        last_iteration = active_config.iteration_offset + active_config.maximum_iterations
        for iteration in range(first_iteration, last_iteration + 1):
            # Check stopping condition: Max candidates reached
            if len(candidates) >= active_config.maximum_candidates:
                stop_reason = "maximum_candidates"
                logger.info(f"Discovery run '{run_id}' reached maximum_candidates target ({active_config.maximum_candidates}). Stopping.")
                break

            # Discovery Gap Analysis
            gaps = self._analyze_discovery_gaps(candidates)

            # Generate Search Hypothesis & Queries
            hypothesis_data = hypothesis_gen.generate_hypothesis(iteration, gaps)
            hypothesis_name = hypothesis_data["hypothesis"]
            queries = hypothesis_data["queries"]

            if not queries:
                logger.warning(f"No new queries generated for iteration {iteration}. Exhausted strategy pool.")
                stop_reason = "budget_exhausted"
                break

            iteration_new_candidates = 0
            iteration_results_count = 0

            # Execute Queries
            for query in queries:
                executed_queries.append(query)
                try:
                    logger.info(f"Iteration {iteration}: Executing query '{query}'")
                    search_results = self.search_provider.search(
                        query, limit=active_config.maximum_results_per_query
                    )
                    iteration_results_count += len(search_results)

                    for res in search_results:
                        cand = CandidateExtractor.extract_candidate(
                            res,
                            hypothesis=hypothesis_name,
                            sector_hint=hypothesis_data.get("target_sector"),
                            geo_hint=hypothesis_data.get("target_geo"),
                        )

                        if not cand:
                            continue

                        # Deduplication Logic
                        # 1. Deduplicate by canonical domain if available
                        if cand.company_domain:
                            norm_dom = normalize_domain(cand.company_domain)
                            if norm_dom in seen_domains:
                                continue
                            seen_domains.add(norm_dom)
                            if cand.company_name:
                                seen_names.add(normalize_company_name_key(cand.company_name))
                        else:
                            # 2. Deduplicate conservatively by company name if domain is missing
                            name_key = normalize_company_name_key(cand.company_name)
                            if not name_key or name_key in seen_names:
                                continue
                            seen_names.add(name_key)

                        candidates.append(cand)
                        iteration_new_candidates += 1

                        if len(candidates) >= active_config.maximum_candidates:
                            break

                except Exception as exc:
                    warn_msg = f"Query '{query}' failed during iteration {iteration}: {str(exc)}"
                    logger.error(warn_msg)
                    warnings.append(warn_msg)

                if len(candidates) >= active_config.maximum_candidates:
                    break

            # Record Iteration Telemetry
            log_entry = DiscoveryIterationLog(
                iteration_number=iteration,
                hypothesis=hypothesis_name,
                queries_executed=queries,
                results_retrieved=iteration_results_count,
                new_candidates_found=iteration_new_candidates,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
            iteration_logs.append(log_entry)

            # Track yield stagnation
            if iteration_new_candidates == 0:
                consecutive_zero_yield_iterations += 1
            else:
                consecutive_zero_yield_iterations = 0

            # Check stopping condition: 2 consecutive iterations with no new candidates
            if consecutive_zero_yield_iterations >= 2:
                stop_reason = "no_new_candidates"
                logger.info(f"Discovery run '{run_id}' produced 0 new candidates for 2 consecutive iterations. Stopping.")
                break

        logger.info(
            f"Discovery run '{run_id}' completed. Total candidates: {len(candidates)}, Unique domains: {len(seen_domains)}, Stop reason: '{stop_reason}'"
        )

        return DiscoveryResult(
            run_id=run_id,
            candidates=candidates,
            iterations_completed=len(iteration_logs),
            queries_executed=executed_queries,
            unique_domains_discovered=len(seen_domains),
            stop_reason=stop_reason,
            warnings=warnings,
            discovery_timestamp=start_timestamp,
            iteration_logs=iteration_logs,
        )
