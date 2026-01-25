"""
Dependency injection for EntitySpine API.

Provides FastAPI dependency functions for:
- EntityResolver instance
- Database connections
- Configuration
"""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

from pydantic_settings import BaseSettings

if TYPE_CHECKING:
    from entityspine.services.resolver import EntityResolver


class Settings(BaseSettings):
    """API configuration settings."""

    # Database
    db_path: str | None = None
    auto_load_sec: bool = True

    # Resolution
    min_fuzzy_score: float = 0.6
    max_candidates: int = 10

    # API
    api_title: str = "EntitySpine API"
    api_version: str = "0.1.0"
    api_description: str = "Entity Resolution REST API"

    class Config:
        env_prefix = "ENTITYSPINE_"
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global resolver instance (lazy initialization)
_resolver: EntityResolver | None = None


def get_resolver() -> EntityResolver:
    """
    Get the EntityResolver instance.

    This creates a single shared resolver instance for the application.
    The resolver is lazily initialized on first use.

    Returns:
        EntityResolver: The configured resolver instance.
    """
    global _resolver

    if _resolver is None:
        from entityspine.services.resolver import EntityResolver, ResolverConfig

        settings = get_settings()

        config = ResolverConfig(
            db_path=settings.db_path,
            auto_load_sec=settings.auto_load_sec,
            min_fuzzy_score=settings.min_fuzzy_score,
            max_candidates=settings.max_candidates,
        )

        _resolver = EntityResolver(config=config)

    return _resolver


def reset_resolver() -> None:
    """Reset the resolver instance (for testing)."""
    global _resolver
    _resolver = None
