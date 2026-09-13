"""Tools and provider abstractions package."""
from .interfaces import (
    SearchProvider,
    LLMProvider,
    EmailVerificationProvider,
    WebResearchProvider,
    SearchResult,
)
from .generic_email import is_generic_email, GENERIC_LOCAL_PARTS
from .domain_utils import normalize_domain
from .source_classifier import SourceType, classify_source_type, get_source_tier
from .search import (
    MockSearchProvider,
    TavilySearchProvider,
    SerpAPISearchProvider,
    SearchService,
    get_search_provider,
)
from .web_research import (
    MockWebResearchProvider,
    HTTPWebResearchProvider,
    clean_html_text,
    get_web_research_provider,
)
from .evidence_extractor import EvidenceExtractor

__all__ = [
    "SearchProvider",
    "LLMProvider",
    "EmailVerificationProvider",
    "WebResearchProvider",
    "SearchResult",
    "is_generic_email",
    "GENERIC_LOCAL_PARTS",
    "normalize_domain",
    "SourceType",
    "classify_source_type",
    "get_source_tier",
    "MockSearchProvider",
    "TavilySearchProvider",
    "SerpAPISearchProvider",
    "SearchService",
    "get_search_provider",
    "MockWebResearchProvider",
    "HTTPWebResearchProvider",
    "clean_html_text",
    "get_web_research_provider",
    "EvidenceExtractor",
]
