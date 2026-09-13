import pytest
import os
import tempfile
from fastapi.testclient import TestClient
from api.main import create_app
from api.dependencies import get_lead_store, get_orchestrator
from storage.lead_store import LeadStore
from agents.orchestrator import MasterOrchestrator, ExecutionBudgets
from tools.search import MockSearchProvider
from tools.web_research import MockWebResearchProvider
from tools.email_verification import MockEmailVerificationProvider
from tools.interfaces import SearchResult
from models.lead import Lead, QualificationStatus


@pytest.fixture
def api_client(tmp_path):
    db_file = str(tmp_path / "test_api.db")
    store = LeadStore(db_path=db_file)

    def mock_search_fn(query: str, limit: int = 10):
        return [
            SearchResult(
                title="Alpha SaaS - B2B Supply Chain",
                url="https://alphasaas.io/about",
                snippet="Alpha SaaS is a leading B2B SaaS platform based in Tallinn, Estonia. Raised $2.5M total funding. CEO John Doe leads the company. Contact John Doe at john.doe@alphasaas.io.",
                source_domain="alphasaas.io",
            )
        ]

    mock_search = MockSearchProvider()
    mock_search.search = mock_search_fn

    mock_web = MockWebResearchProvider()
    mock_email_verifier = MockEmailVerificationProvider(
        mock_status_map={"john.doe@alphasaas.io": "deliverable"}
    )

    budgets = ExecutionBudgets(target_qualified_leads=1, max_discovery_iterations=1)

    orchestrator = MasterOrchestrator(
        lead_store=store,
        search_provider=mock_search,
        web_provider=mock_web,
        email_verifier=mock_email_verifier,
        budgets=budgets,
    )

    app = create_app()

    app.dependency_overrides[get_lead_store] = lambda: store
    app.dependency_overrides[get_orchestrator] = lambda: orchestrator

    with TestClient(app) as client:
        yield client, store, orchestrator


def test_api_health(api_client):
    client, _, _ = api_client
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == "1.0.0"


def test_api_create_run(api_client):
    client, _, _ = api_client
    response = client.post("/api/runs", json={"target_qualified_leads": 1})
    assert response.status_code == 202
    data = response.json()
    assert "run_id" in data
    assert data["status"] == "DISCOVERING"
    assert data["target_qualified_leads"] == 1


def test_api_get_run_status(api_client):
    client, _, _ = api_client
    create_res = client.post("/api/runs", json={"target_qualified_leads": 1})
    run_id = create_res.json()["run_id"]

    status_res = client.get(f"/api/runs/{run_id}")
    assert status_res.status_code == 200
    data = status_res.json()
    assert data["run_id"] == run_id


def test_api_get_run_unknown(api_client):
    client, _, _ = api_client
    response = client.get("/api/runs/nonexistent_run_999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Run 'nonexistent_run_999' not found."


def test_api_get_qualified_leads_for_run(api_client):
    client, store, _ = api_client
    create_res = client.post("/api/runs", json={"target_qualified_leads": 1})
    run_id = create_res.json()["run_id"]

    # Save mock qualified lead
    mock_lead = Lead(
        id="lead_test123",
        company_name="Alpha SaaS",
        domain="alphasaas.io",
        description="B2B SaaS Platform",
        verified_executive_email="john.doe@alphasaas.io",
        qualification_status=QualificationStatus.QUALIFIED,
        created_at="2026-09-13T00:00:00Z",
    )
    store.save_lead(mock_lead)

    leads_res = client.get(f"/api/runs/{run_id}/leads")
    assert leads_res.status_code == 200
    leads = leads_res.json()
    assert len(leads) == 1
    assert leads[0]["domain"] == "alphasaas.io"
    assert leads[0]["verified_executive_email"] == "john.doe@alphasaas.io"


def test_api_get_lead_detail(api_client):
    client, store, _ = api_client
    mock_lead = Lead(
        id="lead_detail_999",
        company_name="Beta AI",
        domain="betaai.co",
        description="Enterprise AI Platform",
        qualification_status=QualificationStatus.QUALIFIED,
        created_at="2026-09-13T00:00:00Z",
    )
    store.save_lead(mock_lead)

    detail_res = client.get("/api/leads/lead_detail_999")
    assert detail_res.status_code == 200
    data = detail_res.json()
    assert data["id"] == "lead_detail_999"
    assert data["company_name"] == "Beta AI"


def test_api_get_lead_unknown(api_client):
    client, _, _ = api_client
    response = client.get("/api/leads/nonexistent_lead_000")
    assert response.status_code == 404
    assert response.json()["detail"] == "Lead 'nonexistent_lead_000' not found."


def test_api_invalid_payload(api_client):
    client, _, _ = api_client
    response = client.post("/api/runs", json={"target_qualified_leads": -5})
    assert response.status_code == 422
