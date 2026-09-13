import logging
import requests
from typing import Any, Dict, List, Optional
from config.settings import Settings, get_settings
from tools.domain_utils import normalize_domain
from tools.interfaces import SearchProvider, SearchResult

logger = logging.getLogger("tvb_agent.search")


class MockSearchProvider(SearchProvider):
    """Mock / fallback implementation of SearchProvider for offline testing."""

    def __init__(self, mock_results: Optional[List[SearchResult]] = None):
        self.mock_results = mock_results or []

    def search(self, query: str, limit: int = 10) -> List[SearchResult]:
        logger.info(f"MockSearchProvider executing query: '{query}'")
        return self.mock_results[:limit]


class TavilySearchProvider(SearchProvider):
    """Concrete SearchProvider implementation utilizing Tavily API."""

    API_URL = "https://api.tavily.com/search"

    def __init__(self, api_key: str, timeout: int = 10):
        self.api_key = api_key
        self.timeout = timeout

    def search(self, query: str, limit: int = 10) -> List[SearchResult]:
        if not self.api_key:
            logger.error("TavilySearchProvider error: SEARCH_API_KEY is not configured.")
            return []

        payload = {
            "api_key": self.api_key,
            "query": query,
            "max_results": limit,
            "search_depth": "basic",
            "include_domains": [],
            "exclude_domains": [],
        }

        try:
            logger.info(f"TavilySearchProvider searching: '{query}' (limit={limit})")
            response = requests.post(self.API_URL, json=payload, timeout=self.timeout)

            if response.status_code == 401:
                logger.error("TavilySearchProvider error: Invalid API key (401 Unauthorized).")
                return []
            elif response.status_code == 429:
                logger.warning("TavilySearchProvider warning: Rate limit reached (429 Too Many Requests).")
                return []

            response.raise_for_status()
            data = response.json()

            results: List[SearchResult] = []
            for item in data.get("results", []):
                raw_url = item.get("url", "")
                domain = normalize_domain(raw_url)
                results.append(
                    SearchResult(
                        title=item.get("title", ""),
                        url=raw_url,
                        snippet=item.get("content", "") or item.get("snippet", ""),
                        source_domain=domain,
                        published_date=item.get("published_date"),
                    )
                )
            return results[:limit]

        except requests.exceptions.Timeout:
            logger.error(f"TavilySearchProvider timeout searching query: '{query}'")
            return []
        except requests.exceptions.RequestException as exc:
            logger.error(f"TavilySearchProvider request failed: {exc}")
            return []
        except Exception as exc:
            logger.error(f"TavilySearchProvider unexpected error: {exc}")
            return []


class SerpAPISearchProvider(SearchProvider):
    """Concrete SearchProvider implementation utilizing SerpAPI (Google Engine)."""

    API_URL = "https://serpapi.com/search"

    def __init__(self, api_key: str, timeout: int = 10):
        self.api_key = api_key
        self.timeout = timeout

    def search(self, query: str, limit: int = 10) -> List[SearchResult]:
        if not self.api_key:
            logger.error("SerpAPISearchProvider error: SEARCH_API_KEY is not configured.")
            return []

        params = {
            "api_key": self.api_key,
            "q": query,
            "engine": "google",
            "num": limit,
        }

        try:
            logger.info(f"SerpAPISearchProvider searching: '{query}' (limit={limit})")
            response = requests.get(self.API_URL, params=params, timeout=self.timeout)

            if response.status_code == 401 or response.status_code == 403:
                logger.error("SerpAPISearchProvider error: Invalid API key or unauthorized.")
                return []

            response.raise_for_status()
            data = response.json()

            results: List[SearchResult] = []
            for item in data.get("organic_results", []):
                raw_url = item.get("link", "")
                domain = normalize_domain(raw_url)
                results.append(
                    SearchResult(
                        title=item.get("title", ""),
                        url=raw_url,
                        snippet=item.get("snippet", ""),
                        source_domain=domain,
                        published_date=item.get("date"),
                    )
                )
            return results[:limit]

        except requests.exceptions.Timeout:
            logger.error(f"SerpAPISearchProvider timeout searching query: '{query}'")
            return []
        except requests.exceptions.RequestException as exc:
            logger.error(f"SerpAPISearchProvider request failed: {exc}")
            return []
        except Exception as exc:
            logger.error(f"SerpAPISearchProvider unexpected error: {exc}")
            return []


def get_search_provider(
    provider_name: Optional[str] = None,
    api_key: Optional[str] = None,
    settings: Optional[Settings] = None,
) -> SearchProvider:
    """Factory function instantiating the requested or configured SearchProvider."""
    app_settings = settings or get_settings()
    p_name = (provider_name or app_settings.search_provider).lower()
    key = api_key or app_settings.search_api_key
    timeout = app_settings.request_timeout_seconds

    if p_name == "tavily":
        return TavilySearchProvider(api_key=key, timeout=timeout)
    elif p_name == "serpapi":
        return SerpAPISearchProvider(api_key=key, timeout=timeout)
    else:
        return MockSearchProvider()


class SearchService:
    """Reusable high-level search service managing multi-query execution & result normalization."""

    def __init__(self, provider: Optional[SearchProvider] = None):
        self.provider = provider or get_search_provider()

    def search_single(
        self, query: str, limit: int = 10, domain_filter: Optional[str] = None
    ) -> List[SearchResult]:
        """Execute a single query with optional domain filtering."""
        logger.info(f"SearchService.search_single started for: '{query}'")
        full_query = query
        if domain_filter:
            full_query = f"site:{domain_filter} {query}"

        results = self.provider.search(full_query, limit=limit)

        # Deduplicate and ensure source_domain normalization
        deduped: List[SearchResult] = []
        seen_urls = set()
        for res in results:
            if not res.url or res.url in seen_urls:
                continue
            seen_urls.add(res.url)
            if not res.source_domain:
                res.source_domain = normalize_domain(res.url)
            deduped.append(res)

        logger.info(f"SearchService.search_single completed: {len(deduped)} results found.")
        return deduped

    def search_batch(
        self, queries: List[str], limit_per_query: int = 5
    ) -> Dict[str, List[SearchResult]]:
        """Execute multiple search queries and return aggregated results by query."""
        logger.info(f"SearchService.search_batch starting for {len(queries)} queries.")
        batch_results: Dict[str, List[SearchResult]] = {}
        for q in queries:
            batch_results[q] = self.search_single(q, limit=limit_per_query)
        logger.info("SearchService.search_batch completed.")
        return batch_results
