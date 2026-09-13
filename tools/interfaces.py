from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel


class SearchResult(BaseModel):
    title: str
    url: str
    snippet: str
    source_domain: str
    published_date: Optional[str] = None


class SearchProvider(ABC):
    """Abstract interface for dynamic search engine providers."""

    @abstractmethod
    def search(self, query: str, limit: int = 10) -> List[SearchResult]:
        """Execute web search query and return structured search results."""
        pass


class LLMProvider(ABC):
    """Abstract interface for LLM extraction and interpretation providers."""

    @abstractmethod
    def complete(self, prompt: str, schema: Optional[Type[BaseModel]] = None) -> Any:
        """Generate response or structured Pydantic object from prompt."""
        pass


class EmailVerificationProvider(ABC):
    """Abstract interface for email deliverability and MX validation services."""

    @abstractmethod
    def verify(self, email: str, domain: str) -> Dict[str, Any]:
        """Verify deliverability status of an email address."""
        pass


class WebResearchProvider(ABC):
    """Abstract interface for fetching web content / landing pages."""

    @abstractmethod
    def fetch(self, url: str) -> Dict[str, Any]:
        """Fetch raw HTML or extracted markdown from a target URL."""
        pass
