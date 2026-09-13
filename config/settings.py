import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()


def _default_sqlite_db_path() -> str:
    configured_path = os.getenv("SQLITE_DB_PATH")
    if configured_path:
        return configured_path
    if os.getenv("VERCEL"):
        return "/tmp/tvb_leads.db"
    return str(Path.cwd() / "tvb_leads.db")



class Settings(BaseModel):
    """Application settings loaded from environment variables or defaults."""

    search_provider: str = Field(
        default_factory=lambda: os.getenv("SEARCH_PROVIDER", "mock").lower()
    )
    search_api_key: str = Field(
        default_factory=lambda: os.getenv("SEARCH_API_KEY", "")
    )
    gemini_api_key: str = Field(
        default_factory=lambda: os.getenv("GEMINI_API_KEY", "")
    )
    email_verification_api_key: str = Field(
        default_factory=lambda: os.getenv("EMAIL_VERIFICATION_API_KEY", "")
    )
    log_level: str = Field(
        default_factory=lambda: os.getenv("LOG_LEVEL", "INFO")
    )
    target_qualified_leads: int = Field(
        default_factory=lambda: int(os.getenv("TARGET_QUALIFIED_LEADS", "15"))
    )
    max_candidate_pool_size: int = Field(
        default_factory=lambda: int(os.getenv("MAX_CANDIDATE_POOL_SIZE", "100"))
    )
    request_timeout_seconds: int = Field(
        default_factory=lambda: int(os.getenv("REQUEST_TIMEOUT_SECONDS", "10"))
    )
    max_pages_per_candidate: int = Field(
        default_factory=lambda: int(os.getenv("MAX_PAGES_PER_CANDIDATE", "4"))
    )
    sqlite_db_path: str = Field(
        default_factory=_default_sqlite_db_path
    )


_settings_instance: Settings | None = None


def get_settings() -> Settings:
    """Get singleton instance of application settings."""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()
    return _settings_instance
