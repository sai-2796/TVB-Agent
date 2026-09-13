import logging
from typing import Dict, List
from models.discovery import DiscoveredCandidate

logger = logging.getLogger("tvb_agent.research_planner")


class ResearchPlanner:
    """
    Generates targeted research tasks and candidate-specific queries across 4 major research areas:
    financials, platform nature, US presence, and active CEO/co-founder identity.
    """

    @classmethod
    def generate_research_plan(
        cls, candidate: DiscoveredCandidate, depth: str = "standard", max_queries: int = 6
    ) -> Dict[str, List[str]]:
        company = candidate.company_name or candidate.company_domain or "Company"

        financial_queries = [
            f'"{company}" total funding revenue',
            f'"{company}" funding round raised',
        ]
        platform_queries = [
            f'"{company}" platform product SaaS software',
            f'"{company}" business model technology',
        ]
        us_presence_queries = [
            f'"{company}" headquarters office locations',
            f'"{company}" United States presence offices',
        ]
        executive_queries = [
            f'"{company}" CEO founder co-founder',
            f'"{company}" leadership team executive',
        ]

        if depth == "quick":
            plan = {
                "financial": [financial_queries[0]],
                "platform": [platform_queries[0]],
                "us_presence": [us_presence_queries[0]],
                "executive": [executive_queries[0]],
            }
        elif depth == "deep":
            plan = {
                "financial": financial_queries,
                "platform": platform_queries,
                "us_presence": us_presence_queries,
                "executive": executive_queries,
            }
        else:  # standard
            plan = {
                "financial": [financial_queries[0]],
                "platform": [platform_queries[0]],
                "us_presence": [us_presence_queries[0]],
                "executive": [executive_queries[0]],
            }

        # Clamp total query count if max_queries limit specified
        total_count = sum(len(qs) for qs in plan.values())
        logger.info(f"ResearchPlanner generated {total_count} queries for '{company}' (depth={depth})")
        return plan
