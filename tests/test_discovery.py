import pytest
from unittest.mock import MagicMock, patch
from models.discovery import DiscoveryConfig, DiscoveryResult
from tools.interfaces import SearchProvider, SearchResult
from tools.search import MockSearchProvider
from agents.discovery_agent import DiscoveryAgent
from agents.candidate_extractor import CandidateExtractor, sanitize_company_name, extract_domain_from_text
from agents.hypothesis_generator import HypothesisGenerator


def test_sanitize_company_name():
    assert sanitize_company_name("TechPlatform | Crunchbase") == "TechPlatform"
    assert sanitize_company_name("Alpha SaaS - Product Hunt") == "Alpha SaaS"
    assert sanitize_company_name("Beta AI raises $3M Seed funding") == "Beta AI"
    assert sanitize_company_name("Gamma Corp: Overview and Team") == "Gamma Corp"


def test_extract_domain_from_text():
    assert extract_domain_from_text("Visit us at https://techplatform.io for more info") == "techplatform.io"
    # Third party directory domains should return None as canonical company domain
    assert extract_domain_from_text("Read about us on crunchbase.com") is None


def test_candidate_extractor_canonical_domain_and_directory_filtering():
    # Direct company website search result
    res_direct = SearchResult(
        title="TechPlatform - B2B SaaS Supply Chain",
        url="https://techplatform.io/about",
        snippet="Leading B2B SaaS platform for logistics",
        source_domain="techplatform.io",
    )
    cand_direct = CandidateExtractor.extract_candidate(res_direct, hypothesis="Hypothesis 1")
    assert cand_direct is not None
    assert cand_direct.company_domain == "techplatform.io"
    assert cand_direct.company_name == "TechPlatform"
    assert cand_direct.discovery_score > 0.5

    # Directory search result (Crunchbase) -> domain set to None unless mentioned in text
    res_dir = SearchResult(
        title="Delta Robotics | Crunchbase",
        url="https://www.crunchbase.com/organization/delta-robotics",
        snippet="Delta Robotics is an AI platform based in Tallinn.",
        source_domain="crunchbase.com",
    )
    cand_dir = CandidateExtractor.extract_candidate(res_dir, hypothesis="Hypothesis 1")
    assert cand_dir is not None
    assert cand_dir.company_domain is None  # Never claim crunchbase.com as candidate domain!
    assert cand_dir.company_name == "Delta Robotics"


def test_hypothesis_generator():
    config = DiscoveryConfig(
        geographic_focus=["Europe", "LATAM"],
        technology_focus=["B2B SaaS", "AI"],
        maximum_queries_per_iteration=2,
    )
    generator = HypothesisGenerator(config)

    hyp1 = generator.generate_hypothesis(1, discovery_gaps=[])
    assert "Strategy Iteration 1" in hyp1["hypothesis"]
    assert len(hyp1["queries"]) <= 2

    # Verify query tracking avoids duplicate query generation
    hyp2 = generator.generate_hypothesis(2, discovery_gaps=["tech_sector"])
    for q in hyp2["queries"]:
        assert q.lower() not in [old_q.lower() for old_q in hyp1["queries"]]


def test_discovery_agent_basic_run():
    mock_search_results = [
        SearchResult(
            title="Epsilon Tech - B2B Platform",
            url="https://epsilontech.de/about",
            snippet="Epsilon Tech raised $2.5M Seed funding for B2B SaaS",
            source_domain="epsilontech.de",
        ),
        SearchResult(
            title="Zeta Health | Crunchbase",
            url="https://www.crunchbase.com/organization/zeta-health",
            snippet="Zeta Health operates a digital health platform in Germany",
            source_domain="crunchbase.com",
        ),
    ]

    provider = MockSearchProvider(mock_results=mock_search_results)
    config = DiscoveryConfig(maximum_iterations=2, maximum_candidates=10)
    agent = DiscoveryAgent(search_provider=provider, config=config)

    result = agent.run_discovery()

    assert isinstance(result, DiscoveryResult)
    assert len(result.candidates) > 0
    assert result.iterations_completed >= 1
    assert result.stop_reason in ("maximum_iterations", "no_new_candidates", "maximum_candidates")

    # Check provenance
    first_cand = result.candidates[0]
    assert first_cand.discovery_source_url != ""
    assert first_cand.discovery_hypothesis != ""
    assert first_cand.discovery_timestamp != ""


def test_discovery_agent_deduplication():
    # Two search results pointing to the same company domain
    mock_results = [
        SearchResult(
            title="TechPlatform Page 1",
            url="https://techplatform.io/page1",
            snippet="Snippet 1",
            source_domain="techplatform.io",
        ),
        SearchResult(
            title="TechPlatform Page 2",
            url="https://techplatform.io/page2",
            snippet="Snippet 2",
            source_domain="techplatform.io",
        ),
    ]
    provider = MockSearchProvider(mock_results=mock_results)
    config = DiscoveryConfig(maximum_iterations=1, maximum_candidates=10)
    agent = DiscoveryAgent(search_provider=provider, config=config)

    result = agent.run_discovery()
    # Should deduplicate to exactly 1 candidate for techplatform.io
    assert len(result.candidates) == 1
    assert result.unique_domains_discovered == 1


def test_discovery_agent_similar_names_not_merged():
    # Two distinct companies with similar names: ABC Technologies vs ABC Labs
    mock_results = [
        SearchResult(
            title="ABC Technologies - B2B SaaS",
            url="https://abctechnologies.com/about",
            snippet="Snippet 1",
            source_domain="abctechnologies.com",
        ),
        SearchResult(
            title="ABC Labs - Health Platform",
            url="https://abclabs.io/about",
            snippet="Snippet 2",
            source_domain="abclabs.io",
        ),
    ]
    provider = MockSearchProvider(mock_results=mock_results)
    config = DiscoveryConfig(maximum_iterations=1, maximum_candidates=10)
    agent = DiscoveryAgent(search_provider=provider, config=config)

    result = agent.run_discovery()
    assert len(result.candidates) == 2
    domains = {c.company_domain for c in result.candidates}
    assert "abctechnologies.com" in domains
    assert "abclabs.io" in domains


def test_discovery_agent_stop_conditions():
    # Test maximum_candidates stop condition
    mock_results = [
        SearchResult(
            title=f"Company {i}",
            url=f"https://company{i}.io/about",
            snippet=f"Platform {i}",
            source_domain=f"company{i}.io",
        )
        for i in range(20)
    ]
    provider = MockSearchProvider(mock_results=mock_results)
    config = DiscoveryConfig(
        maximum_iterations=5,
        maximum_candidates=3,
        maximum_results_per_query=10,
    )
    agent = DiscoveryAgent(search_provider=provider, config=config)

    result = agent.run_discovery()
    assert len(result.candidates) == 3
    assert result.stop_reason == "maximum_candidates"


def test_discovery_agent_stagnation_stop_condition():
    # Empty search results -> 0 new candidates -> stops after 2 zero-yield iterations
    provider = MockSearchProvider(mock_results=[])
    config = DiscoveryConfig(maximum_iterations=5, maximum_candidates=10)
    agent = DiscoveryAgent(search_provider=provider, config=config)

    result = agent.run_discovery()
    assert len(result.candidates) == 0
    assert result.stop_reason == "no_new_candidates"
    assert result.iterations_completed == 2  # Stopped after 2 zero-yield iterations


def test_discovery_agent_iteration_offset_and_result_limit():
    provider = MagicMock()
    provider.search.return_value = []
    config = DiscoveryConfig(
        maximum_iterations=1,
        maximum_queries_per_iteration=1,
        maximum_results_per_query=2,
        iteration_offset=2,
    )

    DiscoveryAgent(search_provider=provider).run_discovery(config)

    query = provider.search.call_args.args[0]
    assert "HealthTech" in query
    assert provider.search.call_args.kwargs["limit"] == 2
