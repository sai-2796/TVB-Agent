"""Agents package."""
from .orchestrator import MasterOrchestrator, MasterOrchestrator as Orchestrator
from .discovery_agent import DiscoveryAgent
from .hypothesis_generator import HypothesisGenerator
from .candidate_extractor import CandidateExtractor
from .research_planner import ResearchPlanner
from .conflict_resolver import ConflictResolver
from .research_agent import ResearchAgent
from .contact_agent import ContactAgent

__all__ = [
    "MasterOrchestrator",
    "Orchestrator",
    "DiscoveryAgent",
    "HypothesisGenerator",
    "CandidateExtractor",
    "ResearchPlanner",
    "ConflictResolver",
    "ResearchAgent",
    "ContactAgent",
]
