from config.settings import Settings, get_settings
from storage.lead_store import LeadStore
from agents.orchestrator import MasterOrchestrator


def get_lead_store() -> LeadStore:
    """Dependency provider for LeadStore instance."""
    settings = get_settings()
    return LeadStore(settings.sqlite_db_path)


def get_orchestrator() -> MasterOrchestrator:
    """Dependency provider for MasterOrchestrator instance."""
    settings = get_settings()
    store = LeadStore(settings.sqlite_db_path)
    return MasterOrchestrator(settings=settings, lead_store=store)
