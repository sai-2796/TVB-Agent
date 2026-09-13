import pytest
from unittest.mock import MagicMock, patch
from config.settings import Settings
from tools.interfaces import SearchResult
from tools.search import (
    MockSearchProvider,
    TavilySearchProvider,
    SerpAPISearchProvider,
    SearchService,
    get_search_provider,
)


def test_mock_search_provider():
    mock_results = [
        SearchResult(
            title="TechPlatform - B2B SaaS",
            url="https://techplatform.io/about",
            snippet="Supply chain software platform",
            source_domain="techplatform.io",
        )
    ]
    provider = MockSearchProvider(mock_results=mock_results)
    results = provider.search("B2B SaaS supply chain", limit=5)
    assert len(results) == 1
    assert results[0].title == "TechPlatform - B2B SaaS"
    assert results[0].source_domain == "techplatform.io"
    assert results[0].published_date is None


def test_tavily_search_provider_success():
    provider = TavilySearchProvider(api_key="test_key")
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "results": [
            {
                "title": "Alpha Tech",
                "url": "https://alphatech.de/press",
                "content": "Alpha Tech raises $2M Seed",
                "published_date": "2024-06-01",
            }
        ]
    }

    with patch("requests.post", return_value=mock_response):
        results = provider.search("Alpha Tech funding", limit=5)
        assert len(results) == 1
        assert results[0].title == "Alpha Tech"
        assert results[0].url == "https://alphatech.de/press"
        assert results[0].source_domain == "alphatech.de"
        assert results[0].published_date == "2024-06-01"


def test_tavily_search_provider_unauthorized_and_error_handling():
    # Missing API key -> empty list
    p_no_key = TavilySearchProvider(api_key="")
    assert p_no_key.search("test") == []

    # 401 Unauthorized -> empty list cleanly
    p_bad_key = TavilySearchProvider(api_key="invalid_key")
    mock_401 = MagicMock()
    mock_401.status_code = 401
    with patch("requests.post", return_value=mock_401):
        assert p_bad_key.search("test") == []


def test_serpapi_search_provider_success():
    provider = SerpAPISearchProvider(api_key="test_key")
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "organic_results": [
            {
                "title": "Beta SaaS Platform",
                "link": "https://www.betasaas.com/home",
                "snippet": "Enterprise B2B platform",
                "date": "2024-01-15",
            }
        ]
    }

    with patch("requests.get", return_value=mock_response):
        results = provider.search("Beta SaaS", limit=5)
        assert len(results) == 1
        assert results[0].source_domain == "betasaas.com"
        assert results[0].published_date == "2024-01-15"


def test_search_service_batch_and_deduplication():
    mock_results = [
        SearchResult(
            title="Candidate 1",
            url="https://example.com/p1",
            snippet="Snippet 1",
            source_domain="example.com",
        ),
        SearchResult(
            title="Candidate 1 Dup",
            url="https://example.com/p1",  # Duplicate URL
            snippet="Snippet 1 Dup",
            source_domain="example.com",
        ),
    ]
    provider = MockSearchProvider(mock_results=mock_results)
    service = SearchService(provider=provider)

    # Single search with deduplication
    single = service.search_single("query", limit=10)
    assert len(single) == 1

    # Batch search
    batch = service.search_batch(["query1", "query2"], limit_per_query=5)
    assert "query1" in batch and "query2" in batch


def test_get_search_provider_factory():
    settings = Settings(search_provider="mock", search_api_key="123")
    prov = get_search_provider(settings=settings)
    assert isinstance(prov, MockSearchProvider)
