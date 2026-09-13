import os
import tempfile
import pytest
from models.lead import Lead, QualificationStatus
from storage.lead_store import LeadStore


@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    store = LeadStore(db_path=path)
    yield store
    if os.path.exists(path):
        os.remove(path)


def test_lead_store_crud(temp_db):
    store = temp_db

    lead_qual = Lead(
        id="lead_qual_1",
        company_name="TechPlatform Ltd",
        domain="techplatform.io",
        verified_executive_email="alex@techplatform.io",
        qualification_status=QualificationStatus.QUALIFIED,
        created_at="2026-09-12T23:50:00Z",
    )

    lead_unqual = Lead(
        id="lead_unqual_2",
        company_name="Local Store Inc",
        domain="localstore.com",
        qualification_status=QualificationStatus.UNQUALIFIED,
        rejection_reasons=["Platform [FAIL]: Non-tech business"],
        created_at="2026-09-12T23:50:00Z",
    )

    store.save_lead(lead_qual)
    store.save_lead(lead_unqual)

    # Get single lead
    retrieved = store.get_lead("lead_qual_1")
    assert retrieved is not None
    assert retrieved.company_name == "TechPlatform Ltd"
    assert retrieved.qualification_status == QualificationStatus.QUALIFIED

    # List qualified
    qual_list = store.list_qualified_leads()
    assert len(qual_list) == 1
    assert qual_list[0].id == "lead_qual_1"

    # List rejected
    rej_list = store.list_rejected_leads()
    assert len(rej_list) == 1
    assert rej_list[0].id == "lead_unqual_2"

    # List all
    all_list = store.list_all_leads()
    assert len(all_list) == 2
