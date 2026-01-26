"""Configuration management for EntitySpine."""

from enum import Enum
from functools import lru_cache
from pathlib import Path

try:
    from pydantic import Field
    from pydantic_settings import BaseSettings, SettingsConfigDict

    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False


class Environment(str, Enum):
    """Application environment."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class StorageBackend(str, Enum):
    """Storage backend types."""

    JSON = "json"
    SQLITE = "sqlite"
    DUCKDB = "duckdb"
    POSTGRES = "postgres"


if PYDANTIC_AVAILABLE:

    class Settings(BaseSettings):
        """Application settings with environment variable support."""

        model_config = SettingsConfigDict(
            env_prefix="ENTITYSPINE_",
            env_file=".env",
            env_file_encoding="utf-8",
            extra="ignore",
        )

        # Application
        env: Environment = Environment.DEVELOPMENT
        debug: bool = False
        log_level: str = "INFO"

        # Storage
        backend: StorageBackend = StorageBackend.SQLITE
        db_path: str = "./data/entityspine.db"
        json_path: str | None = None

        # PostgreSQL
        postgres_host: str = "localhost"
        postgres_port: int = 5432
        postgres_user: str = "entityspine"
        postgres_password: str = "entityspine"
        postgres_db: str = "entityspine"
        database_url: str | None = None

        # API
        api_host: str = "0.0.0.0"
        api_port: int = 8000
        api_workers: int = 1
        api_reload: bool = True
        cors_origins: str = "http://localhost:3000,http://localhost:5173"

        # SEC Data
        auto_download: bool = True
        sec_user_agent: str = "EntitySpine/1.0 (research)"

        # Optional: Elasticsearch
        elasticsearch_url: str | None = None
        elasticsearch_index: str = "entities"

        # Optional: Redis
        redis_url: str | None = None

        @property
        def postgres_dsn(self) -> str:
            """Build PostgreSQL DSN from components."""
            if self.database_url:
                return self.database_url
            return (
                f"postgresql://{self.postgres_user}:{self.postgres_password}"
                f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
            )

        @property
        def cors_origin_list(self) -> list[str]:
            """Parse CORS origins as list."""
            return [origin.strip() for origin in self.cors_origins.split(",")]

else:
    # Fallback when pydantic-settings not installed
    import os

    class Settings:  # type: ignore[no-redef]
        """Simple settings without pydantic (for Tier 0-1)."""

        def __init__(self) -> None:
            self.env = os.getenv("ENTITYSPINE_ENV", "development")
            self.debug = os.getenv("ENTITYSPINE_DEBUG", "false").lower() == "true"
            self.log_level = os.getenv("ENTITYSPINE_LOG_LEVEL", "INFO")
            self.backend = os.getenv("ENTITYSPINE_BACKEND", "sqlite")
            self.db_path = os.getenv("ENTITYSPINE_DB_PATH", "./data/entityspine.db")
            self.json_path = os.getenv("ENTITYSPINE_JSON_PATH")
            self.auto_download = os.getenv("ENTITYSPINE_AUTO_DOWNLOAD", "true").lower() == "true"
            self.sec_user_agent = os.getenv(
                "ENTITYSPINE_SEC_USER_AGENT", "EntitySpine/1.0 (research)"
            )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Common paths
def get_data_dir() -> Path:
    """Get data directory path."""
    settings = get_settings()
    if hasattr(settings, "db_path"):
        return Path(settings.db_path).parent
    return Path("./data")


def get_default_json_path() -> Path:
    """Get default path for company_tickers.json."""
    candidates = [
        get_data_dir() / "company_tickers.json",
        Path.cwd() / "refdata" / "company_tickers.json",
        Path.cwd() / "data" / "company_tickers.json",
        Path.home() / ".entityspine" / "company_tickers.json",
        Path.home() / ".cache" / "entityspine" / "company_tickers.json",
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    # Default location for download
    return Path.home() / ".entityspine" / "company_tickers.json"
