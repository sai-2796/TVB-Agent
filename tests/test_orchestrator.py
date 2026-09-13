import pytest
import os
import tempfile
from unittest.mock import MagicMock
from models.discovery import DiscoveredCandidate, DiscoveryResult
from models.company import CompanyResearch
from models.evidence import Evidence, VerificationMethod, SourceTier
from models.financial import FinancialsData, FinancialType
from models.us_presence import USPresenceData, USPresenceStatus
from models.executive import ExecutiveProfile, ExecutiveRole
from models.email import ExecutiveEmail, EmailVerificationStatus, TechnicalStatus, FinalEmailStatus
from models.lead import QualificationStatus
from models.orchestrator import OrchestratorState, StopReason, ExecutionBudgets
from tools.search import MockSearchProvider
from tools.web_research import MockWebResearchProvider
from tools.email_verification import MockEmailVerificationProvider
from tools.interfaces import SearchResult
from storage.lead_store import LeadStore
from agents.orchestrator import MasterOrchestrator


def make_test_evidence(field: str, value: str, text: str, url: str) -> Evidence:
    return Evidence(
        field=field,
        value=value,
        raw_claim=text,
        evidence_text=text,
        source_url=url,
        source_title="Company Source",
        source_type="company_website",
        accessed_at="2026-09-13T00:00:00Z",
        source_tier=SourceTier.TIER_1,
        confidence=0.95,
        verification_method=VerificationMethod.DIRECT_EXTRACTION,
    )


def test_orchestrator_end_to_end_mock_success(tmp_path):
    db_file = str(tmp_path / "test_orchestrator.db")
    store = LeadStore(db_path=db_file)

    def mock_search_fn(query: str, limit: int = 10):
        q_lower = query.lower()
        if "alphasaas" in q_lower or "alpha" in q_lower:
            return [
                SearchResult(
                    title="Alpha SaaS - B2B Supply Chain",
                    url="https://alphasaas.io/about",
                    snippet="Alpha SaaS is a leading B2B SaaS platform based in Tallinn, Estonia. Raised $2.5M total funding. CEO John Doe leads the company. Contact John Doe at john.doe@alphasaas.io.",
                    source_domain="alphasaas.io",
                )
            ]
        elif "betaai" in q_lower or "beta" in q_lower:
            return [
                SearchResult(
                    title="Beta AI - Enterprise Machine Learning",
                    url="https://betaai.co/team",
                    snippet="Beta AI is headquartered in Berlin, Germany. CEO is Alex Smith.",
                    source_domain="betaai.co",
                )
            ]
        return [
            SearchResult(
                title="Alpha SaaS - B2B Supply Chain",
                url="https://alphasaas.io/about",
                snippet="Alpha SaaS is a leading B2B SaaS platform based in Tallinn, Estonia. Raised $2.5M total funding. CEO John Doe leads the company. Contact John Doe at john.doe@alphasaas.io.",
                source_domain="alphasaas.io",
            ),
            SearchResult(
                title="Beta AI - Enterprise Machine Learning",
                url="https://betaai.co/team",
                snippet="Beta AI is headquartered in Berlin, Germany. CEO is Alex Smith.",
                source_domain="betaai.co",
            ),
        ]

    mock_search = MockSearchProvider()
    mock_search.search = mock_search_fn

    # 2. Mock web provider returning qualifying page text for alphasaas.io and failing text for betaai.co
    alphasaas_text = (
        "Alpha SaaS is a B2B SaaS platform. Raised $2.5M total funding. "
        "Headquartered in Tallinn, Estonia with zero US office. "
        "CEO John Doe leads the company. Contact John Doe at john.doe@alphasaas.io."
    )
    betaai_text = "Beta AI has US headquarters in San Francisco, CA. Revenue is $100M."

    mock_responses = {
        "https://alphasaas.io/about": {
            "url": "https://alphasaas.io/about",
            "page_title": "Alpha SaaS About",
            "main_text": alphasaas_text,
            "status_code": 200,
            "source_domain": "alphasaas.io",
            "is_accessible": True,
        },
        "https://betaai.co/team": {
            "url": "https://betaai.co/team",
            "page_title": "Beta AI Team",
            "main_text": betaai_text,
            "status_code": 200,
            "source_domain": "betaai.co",
            "is_accessible": True,
        },
    }

    class FlexibleMockWebProvider(MockWebResearchProvider):
        def fetch(self, url: str):
            if "alphasaas.io" in url:
                return mock_responses["https://alphasaas.io/about"]
            elif "betaai.co" in url:
                return mock_responses["https://betaai.co/team"]
            return super().fetch(url)

    mock_web = FlexibleMockWebProvider()

    # 3. Mock email verifier delivering john.doe@alphasaas.io
    mock_email_verifier = MockEmailVerificationProvider(
        mock_status_map={"john.doe@alphasaas.io": "deliverable"}
    )

    budgets = ExecutionBudgets(target_qualified_leads=1, max_discovery_iterations=2)

    orchestrator = MasterOrchestrator(
        lead_store=store,
        search_provider=mock_search,
        web_provider=mock_web,
        email_verifier=mock_email_verifier,
        budgets=budgets,
    )

    res = orchestrator.run(target_qualified_leads=1)

    assert res.qualified_leads_count == 1, f"Expected 1 qualified lead, got {res.qualified_leads_count}. Stop reason: {res.stop_reason}"
    assert res.status == OrchestratorState.COMPLETED
    assert res.stop_reason == StopReason.TARGET_REACHED
    assert res.qualified_leads[0].domain == "alphasaas.io"
    assert res.qualified_leads[0].verified_executive_email == "john.doe@alphasaas.io"
    assert res.qualified_leads[0].qualification_status == QualificationStatus.QUALIFIED


def test_orchestrator_target_not_reached_reports_actual_count(tmp_path):
    db_file = str(tmp_path / "test_target_not_reached.db")
    store = LeadStore(db_path=db_file)

    mock_search = MockSearchProvider(
        mock_results=[
            SearchResult(
                title="Gamma Tech",
                url="https://gammatech.io",
                snippet="Gamma Tech is based in US.",
                source_domain="gammatech.io",
            )
        ]
    )

    mock_web = MockWebResearchProvider(
        mock_responses={
            "https://gammatech.io": {
                "url": "https://gammatech.io",
                "title": "Gamma Tech",
                "main_text": "Gamma Tech has US headquarters in New York.",
                "is_accessible": True,
            }
        }
    )

    budgets = ExecutionBudgets(target_qualified_leads=15, max_discovery_iterations=1)
    orchestrator = MasterOrchestrator(
        lead_store=store,
        search_provider=mock_search,
        web_provider=mock_web,
        budgets=budgets,
    )

    res = orchestrator.run(target_qualified_leads=15)

    # Must NOT claim 15 qualified leads!
    assert res.qualified_leads_count == 0
    assert res.target_qualified_leads == 15
    assert res.status in (OrchestratorState.COMPLETED, OrchestratorState.EXHAUSTED)
    assert res.stop_reason != StopReason.TARGET_REACHED


def test_orchestrator_deduplication(tmp_path):
    db_file = str(tmp_path / "test_dedup.db")
    store = LeadStore(db_path=db_file)

    # Search provider returning same candidate domain across iterations
    mock_search = MockSearchProvider(
        mock_results=[
            SearchResult(
                title="Alpha SaaS",
                url="https://alphasaas.io",
                snippet="Alpha SaaS platform",
                source_domain="alphasaas.io",
            )
        ]
    )

    mock_web = MockWebResearchProvider()
    budgets = ExecutionBudgets(target_qualified_leads=5, max_discovery_iterations=2)

    orchestrator = MasterOrchestrator(
        lead_store=store,
        search_provider=mock_search,
        web_provider=mock_web,
        budgets=budgets,
    )

    res = orchestrator.run(target_qualified_leads=5)

    # The domain alphasaas.io should be researched exactly once
    assert res.total_researched <= 1


def test_orchestrator_cheap_validation_rejection_efficiency(tmp_path):
    db_file = str(tmp_path / "test_cheap_val.db")
    store = LeadStore(db_path=db_file)

    mock_search = MockSearchProvider(
        mock_results=[
            SearchResult(
                title="Delta US Corp",
                url="https://deltaus.com",
                snippet="US Headquarters in San Francisco.",
                source_domain="deltaus.com",
            )
        ]
    )

    mock_web = MockWebResearchProvider(
        mock_responses={
            "https://deltaus.com": {
                "url": "https://deltaus.com",
                "title": "Delta US",
                "main_text": "US Headquarters in San Francisco, CA.",
                "is_accessible": True,
            }
        }
    )

    mock_email_verifier = MockEmailVerificationProvider()

    orchestrator = MasterOrchestrator(
        lead_store=store,
        search_provider=mock_search,
        web_provider=mock_web,
        email_verifier=mock_email_verifier,
        budgets=ExecutionBudgets(target_qualified_leads=5, max_discovery_iterations=1),
    )

    res = orchestrator.run()

    # Email verifier must NOT be called for company failing US presence!
    assert res.total_email_attempts == 0
    assert res.total_rejected == 1


def _discovered_candidate(candidate_id: str, domain: str) -> DiscoveredCandidate:
    return DiscoveredCandidate(
        candidate_id=candidate_id,
        company_name=candidate_id,
        company_domain=domain,
        discovery_source_url=f"https://{domain}",
        discovery_source_title=candidate_id,
        discovery_snippet=f"{candidate_id} platform",
        discovery_timestamp="2026-09-13T00:00:00Z",
        discovery_hypothesis="test",
    )


def _discovery_result(candidates):
    return DiscoveryResult(
        run_id="disc_test",
        candidates=candidates,
        iterations_completed=1,
        queries_executed=["test"],
        unique_domains_discovered=len(candidates),
        stop_reason="maximum_iterations",
        discovery_timestamp="2026-09-13T00:00:00Z",
    )


def test_orchestrator_continues_after_candidate_research_exception(tmp_path):
    store = LeadStore(db_path=str(tmp_path / "candidate_failure.db"))
    first = _discovered_candidate("first", "first.example")
    second = _discovered_candidate("second", "second.example")
    orchestrator = MasterOrchestrator(
        lead_store=store,
        search_provider=MockSearchProvider(),
        web_provider=MockWebResearchProvider(),
        budgets=ExecutionBudgets(target_qualified_leads=1, max_discovery_iterations=1),
    )
    orchestrator.discovery_agent.run_discovery = MagicMock(
        return_value=_discovery_result([first, second])
    )
    orchestrator.research_agent.research_candidate = MagicMock(
        side_effect=[RuntimeError("first candidate failed"), CompanyResearch(domain="second.example")]
    )

    result = orchestrator.run(target_qualified_leads=1, max_iterations=1)
    metadata = store.get_run_metadata(result.run_id)

    assert result.total_researched == 1
    assert result.total_rejected == 2
    assert any("first candidate failed" in error for error in result.errors)
    assert metadata["total_researched_count"] == 1
    assert metadata["total_rejected_count"] == 2


def test_orchestrator_persists_terminal_metadata_on_unexpected_exception(tmp_path):
    store = LeadStore(db_path=str(tmp_path / "interrupt.db"))
    orchestrator = MasterOrchestrator(
        lead_store=store,
        search_provider=MockSearchProvider(),
        web_provider=MockWebResearchProvider(),
        budgets=ExecutionBudgets(target_qualified_leads=1, max_discovery_iterations=1),
    )
    orchestrator.discovery_agent.run_discovery = MagicMock(
        side_effect=KeyboardInterrupt("simulated interruption")
    )

    with pytest.raises(KeyboardInterrupt):
        orchestrator.run(target_qualified_leads=1, max_iterations=1)

    metadata = store.list_all_runs()[0]
    assert metadata["status"] == OrchestratorState.FAILED.value
    assert metadata["stop_reason"] == StopReason.SYSTEM_ERROR.value
    assert "KeyboardInterrupt" in metadata["errors"][0]
    assert metadata["completed_at"] is not None


def test_orchestrator_uses_configured_candidate_page_budget(tmp_path):
    store = LeadStore(db_path=str(tmp_path / "page_budget.db"))
    candidate = _discovered_candidate("budget", "budget.example")
    settings = __import__("config.settings", fromlist=["Settings"]).Settings(
        sqlite_db_path=str(tmp_path / "page_budget.db"),
        max_pages_per_candidate=2,
    )
    orchestrator = MasterOrchestrator(
        settings=settings,
        lead_store=store,
        search_provider=MockSearchProvider(),
        web_provider=MockWebResearchProvider(),
        budgets=ExecutionBudgets(target_qualified_leads=1, max_discovery_iterations=1),
    )
    orchestrator.discovery_agent.run_discovery = MagicMock(
        return_value=_discovery_result([candidate])
    )
    orchestrator.research_agent.research_candidate = MagicMock(
        return_value=CompanyResearch(domain="budget.example")
    )

    orchestrator.run(target_qualified_leads=1, max_iterations=1)

    assert orchestrator.research_agent.research_candidate.call_args.kwargs["max_pages"] == 2
