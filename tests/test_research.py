import pytest
from unittest.mock import MagicMock
from models.discovery import DiscoveredCandidate
from models.financial import FinancialType
from models.us_presence import USPresenceStatus
from models.executive import ExecutiveRole
from models.evidence import Evidence, SourceTier
from tools.interfaces import SearchResult
from tools.search import MockSearchProvider
from tools.web_research import MockWebResearchProvider
from tools.currency_normalizer import normalize_currency_to_usd
from agents.research_agent import ResearchAgent, parse_financial_claim, parse_us_presence_text, parse_executive_text
from agents.conflict_resolver import ConflictResolver


def test_currency_normalizer():
    assert normalize_currency_to_usd(100.0, "USD") == 100.0
    assert normalize_currency_to_usd(100.0, "EUR") == 108.0
    assert normalize_currency_to_usd(100.0, "GBP") == 127.0
    assert normalize_currency_to_usd(100.0, "XYZ_UNSUPPORTED") is None


def test_parse_financial_claim_distinctions():
    # Total funding
    ftype1, amt1, curr1, is_tot1 = parse_financial_claim("TechPlatform raised $2.5M total funding")
    assert ftype1 == FinancialType.FUNDING
    assert amt1 == 2500000.0
    assert is_tot1 is True

    # Single funding round (NOT assumed to equal total funding)
    ftype2, amt2, curr2, is_tot2 = parse_financial_claim("TechPlatform announced a $2.5M Seed round")
    assert ftype2 == FinancialType.FUNDING_ROUND
    assert amt2 == 2500000.0
    assert is_tot2 is False

    # Valuation (rejected as funding/revenue)
    ftype3, amt3, curr3, is_tot3 = parse_financial_claim("TechPlatform valued at $10M in recent round")
    assert ftype3 == FinancialType.VALUATION

    # Revenue
    ftype4, amt4, curr4, is_tot4 = parse_financial_claim("TechPlatform reached €3M annual revenue")
    assert ftype4 == FinancialType.REVENUE
    assert curr4 == "EUR"
    assert amt4 == 3000000.0
    assert is_tot4 is True


def test_parse_us_presence_distinctions():
    # Foreign HQ in Estonia -> VERIFIED_NO_US_PRESENCE
    status1, hq1, _ = parse_us_presence_text("Headquartered in Tallinn, Estonia. Global B2B SaaS", "techplatform.io")
    assert status1 == USPresenceStatus.VERIFIED_NO_US_PRESENCE
    assert hq1 == "Estonia"

    # Physical US HQ -> SIGNIFICANT_US_PRESENCE
    status2, hq2, _ = parse_us_presence_text("Headquartered in San Francisco, CA", "techplatform.io")
    assert status2 == USPresenceStatus.SIGNIFICANT_US_PRESENCE
    assert hq2 == "United States"


def test_parse_executive_distinctions():
    # Active CEO
    name1, role1, is_act1 = parse_executive_text("Alex Smith is CEO & Co-founder of TechPlatform")
    assert name1 == "Alex Smith"
    assert role1 == ExecutiveRole.CEO
    assert is_act1 is True

    # Former CEO (must NOT pass as active CEO)
    name2, role2, is_act2 = parse_executive_text("Former CEO John Doe stepped down in 2023")
    assert is_act2 is False


def test_conflict_resolver_financials():
    ev_tier1 = Evidence(
        field="financials",
        value=2500000.0,
        raw_claim="Official filing: Total cumulative funding $2.5M",
        source_url="https://techplatform.io/press",
        source_title="Press Release",
        source_type="company_news",
        accessed_at="2026-09-13T00:00:00Z",
        source_tier=SourceTier.TIER_1,
        confidence=0.95,
    )
    ev_tier3 = Evidence(
        field="financials",
        value=7000000.0,
        raw_claim="Aggregator report: Raised $7M total funding",
        source_url="https://genericblog.com/post",
        source_title="Blog Post",
        source_type="other",
        accessed_at="2026-09-13T00:00:00Z",
        source_tier=SourceTier.TIER_4,
        confidence=0.4,
    )

    winner, conflict = ConflictResolver.resolve_financial_evidence([ev_tier1, ev_tier3])
    assert winner is not None
    assert winner.value == 2500000.0  # Tier 1 source wins over Tier 4
    assert conflict is not None
    assert conflict.resolution_status == "RESOLVED_BY_TIER"


def test_research_agent_end_to_end_mock():
    candidate = DiscoveredCandidate(
        candidate_id="cand_123",
        company_name="TechPlatform",
        company_domain="techplatform.io",
        discovery_source_url="https://techplatform.io",
        discovery_source_title="TechPlatform - B2B SaaS",
        discovery_snippet="TechPlatform operates a B2B SaaS supply chain dashboard.",
        discovery_timestamp="2026-09-13T00:00:00Z",
        discovery_hypothesis="Hypothesis 1",
    )

    mock_search = MockSearchProvider(
        mock_results=[
            SearchResult(
                title="TechPlatform Press - Funding",
                url="https://techplatform.io/press",
                snippet="TechPlatform announced a $2.5M total funding round in Tallinn, Estonia. Alex Smith is CEO.",
                source_domain="techplatform.io",
            )
        ]
    )

    mock_web = MockWebResearchProvider(
        mock_responses={
            "https://techplatform.io/press": {
                "url": "https://techplatform.io/press",
                "page_title": "TechPlatform Press Release",
                "main_text": "TechPlatform Ltd announced a $2.5M total funding round. Headquartered in Tallinn, Estonia. Alex Smith is CEO. The SaaS platform provides supply chain tracking.",
                "status_code": 200,
                "source_domain": "techplatform.io",
                "accessed_at": "2026-09-13T00:00:00Z",
                "published_date": "2024-05-10",
                "is_accessible": True,
            }
        }
    )

    agent = ResearchAgent(search_provider=mock_search, web_provider=mock_web)
    research = agent.research_candidate(candidate, depth="quick", max_pages=4)

    assert research.domain == "techplatform.io"
    assert research.company_name == "TechPlatform"
    assert len(research.all_evidence) > 0
    assert research.is_tech_platform is True
    assert research.headquarters_country == "Estonia"
    assert research.us_presence.status == USPresenceStatus.VERIFIED_NO_US_PRESENCE
    assert research.executive.full_name == "Alex Smith"
    assert research.executive.identity_verified is True
    assert research.research_completeness in ("complete", "partial")


def test_research_agent_continues_after_source_exception():
    candidate = DiscoveredCandidate(
        candidate_id="cand_source_failure",
        company_name="SourceResilient",
        company_domain="source-resilient.io",
        discovery_source_url="https://source-resilient.io",
        discovery_source_title="SourceResilient",
        discovery_snippet="SourceResilient B2B SaaS platform",
        discovery_timestamp="2026-09-13T00:00:00Z",
        discovery_hypothesis="Test",
    )
    search = MockSearchProvider(
        mock_results=[
            SearchResult(
                title="Broken source",
                url="https://broken.example/source",
                snippet="broken",
                source_domain="broken.example",
            ),
            SearchResult(
                title="Working source",
                url="https://source-resilient.io/about",
                snippet="SourceResilient is a B2B SaaS platform headquartered in Tallinn, Estonia. CEO Alex Smith.",
                source_domain="source-resilient.io",
            ),
        ]
    )

    class FailingFirstWebProvider(MockWebResearchProvider):
        def fetch(self, url: str):
            if "broken.example" in url:
                raise TimeoutError("source timeout")
            return {
                "url": url,
                "page_title": "About",
                "main_text": "SourceResilient is a B2B SaaS platform headquartered in Tallinn, Estonia. CEO Alex Smith.",
                "status_code": 200,
                "is_accessible": True,
            }

    research = ResearchAgent(search_provider=search, web_provider=FailingFirstWebProvider())
    result = research.research_candidate(candidate, depth="quick", max_pages=2)

    assert result.research_completeness != "failed"
    assert result.executive.full_name == "Alex Smith"
    assert result.source_failures[0]["url"] == "https://broken.example/source"


def test_research_agent_deduplicates_sources_across_queries():
    candidate = DiscoveredCandidate(
        candidate_id="cand_duplicate_source",
        company_name="DuplicateSource",
        company_domain="duplicate-source.io",
        discovery_source_url="https://duplicate-source.io",
        discovery_source_title="DuplicateSource",
        discovery_snippet="DuplicateSource platform",
        discovery_timestamp="2026-09-13T00:00:00Z",
        discovery_hypothesis="Test",
    )
    search = MockSearchProvider(
        mock_results=[
            SearchResult(
                title="Same source",
                url="https://duplicate-source.io/about",
                snippet="DuplicateSource platform",
                source_domain="duplicate-source.io",
            )
        ]
    )
    web = MagicMock()
    web.fetch.return_value = {
        "url": "https://duplicate-source.io/about",
        "page_title": "About",
        "main_text": "DuplicateSource is a B2B SaaS platform headquartered in Tallinn, Estonia. CEO Alex Smith.",
        "status_code": 200,
        "is_accessible": True,
    }

    ResearchAgent(search_provider=search, web_provider=web).research_candidate(
        candidate, depth="deep", max_pages=4
    )

    assert web.fetch.call_count == 1


def test_financial_conflict_distinction_revenue_vs_round():
    ev_revenue = Evidence(
        field="financials",
        value=3000000.0,
        raw_claim="Annual revenue reached €3M ($3.24M USD)",
        source_url="https://techplatform.io/financials",
        source_title="Financial Report",
        source_type="company_website",
        accessed_at="2026-09-13T00:00:00Z",
        source_tier=SourceTier.TIER_1,
        confidence=0.9,
    )
    ev_round = Evidence(
        field="financials",
        value=500000.0,
        raw_claim="Raised $500k Pre-Seed round in 2022",
        source_url="https://techplatform.io/press",
        source_title="Press Release",
        source_type="press_release",
        accessed_at="2026-09-13T00:00:00Z",
        source_tier=SourceTier.TIER_1,
        confidence=0.9,
    )

    winner, conflict = ConflictResolver.resolve_financial_evidence([ev_revenue, ev_round])
    assert winner is not None
    assert winner.value == 3000000.0

