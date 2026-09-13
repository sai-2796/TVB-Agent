import logging
import random
from typing import Any, Dict, List, Set
from models.discovery import DiscoveryConfig

logger = logging.getLogger("tvb_agent.hypothesis_generator")


class HypothesisGenerator:
    """
    Generates dynamic search hypotheses and query formulations for the autonomous discovery engine.
    Ensures query diversification and adapts based on identified discovery gaps.
    """

    def __init__(self, config: DiscoveryConfig):
        self.config = config
        self.executed_queries: Set[str] = set()
        self.executed_hypotheses: Set[str] = set()

    def generate_hypothesis(self, iteration: int, discovery_gaps: List[str]) -> Dict[str, Any]:
        """
        Generates a new search hypothesis strategy and associated search query formulations.
        """
        geos = self.config.geographic_focus
        sectors = self.config.technology_focus

        target_geo = geos[(iteration - 1) % len(geos)] if geos else "Non-US"
        target_sector = sectors[(iteration - 1) % len(sectors)] if sectors else "B2B SaaS"

        # Adapt hypothesis based on discovery gaps if provided
        if "geography" in discovery_gaps and len(geos) > 1:
            target_geo = random.choice(geos)
        if "tech_sector" in discovery_gaps and len(sectors) > 1:
            target_sector = random.choice(sectors)

        hypothesis_name = f"Strategy Iteration {iteration}: {target_sector} platforms in {target_geo} with $1M-$5M funding signals"

        # Generate query variants
        query_templates = [
            f'"{target_sector}" startup raised 1M..5M funding {target_geo}',
            f'{target_sector} platform seed round {target_geo} startup',
            f'top {target_sector} companies {target_geo} 2024 2025',
            f'{target_geo} {target_sector} tech platform Series Seed',
        ]

        # Filter out previously executed queries
        fresh_queries = []
        for q in query_templates:
            normalized_q = q.strip().lower()
            if normalized_q not in self.executed_queries:
                self.executed_queries.add(normalized_q)
                fresh_queries.append(q)
                if len(fresh_queries) >= self.config.maximum_queries_per_iteration:
                    break

        # Fallback if all standard templates were executed
        if not fresh_queries:
            fallback_q = f"{target_sector} technology platform {target_geo} startup {random.randint(100, 999)}"
            self.executed_queries.add(fallback_q.lower())
            fresh_queries.append(fallback_q)

        self.executed_hypotheses.add(hypothesis_name)
        logger.info(f"HypothesisGenerator generated hypothesis: '{hypothesis_name}' with {len(fresh_queries)} queries.")

        return {
            "hypothesis": hypothesis_name,
            "queries": fresh_queries,
            "target_geo": target_geo,
            "target_sector": target_sector,
        }
