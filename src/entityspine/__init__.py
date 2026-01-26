"""
EntitySpine - Lightweight Entity Resolution

Architecture: Entity ≠ Security ≠ Listing
- Entity: Legal/organizational identity (Apple Inc.)
- Security: Tradeable instrument (Apple Common Stock)
- Listing: Exchange-specific ticker (AAPL on NASDAQ)

CRITICAL: TICKER BELONGS ON LISTING, NOT ENTITY

Design Principles:
- Canonical domain models are stdlib dataclasses (entityspine.domain)
- IdentifierClaim is the canonical source of truth for identifiers
- Pydantic wrappers available via entityspine.adapters.pydantic (optional)
- ORM layer available via entityspine.adapters.orm (optional)

Storage Tiers:
- Tier 0: JSON file + dataclasses (stdlib only)
- Tier 1: SQLite with stdlib sqlite3 (stdlib only)
- Tier 2: DuckDB analytics ([duckdb] extra)
- Tier 3: PostgreSQL production ([postgres] extra)

Usage:
    from entityspine import Entity, Security, Listing, IdentifierClaim

    # Create entities using stdlib dataclasses
    entity = Entity(primary_name="Apple Inc.", source_system="sec", source_id="0000320193")

    # For Pydantic validation (optional):
    # from entityspine.adapters.pydantic import Entity as PydanticEntity
"""

from pathlib import Path
from typing import Optional, Union

from entityspine.core.exceptions import (
    EntityNotFoundError,
    EntitySpineError,
    ResolutionError,
    StorageError,
)
from entityspine.core.identifier import IdentifierType, classify_identifier
from entityspine.core.timestamps import from_iso8601, to_iso8601, utc_now

# Core utilities (stdlib only)
from entityspine.core.ulid import generate_ulid

# =============================================================================
# CANONICAL DOMAIN MODELS (stdlib dataclasses - zero dependencies)
# =============================================================================
# These are the canonical domain models. All business logic and validation
# lives here. Pydantic/ORM wrappers delegate to domain validators.
from entityspine.domain import (
    SCHEME_SCOPES,
    ClaimStatus,
    # Domain models
    Entity,
    EntityStatus,
    # Enums
    EntityType,
    IdentifierClaim,
    IdentifierScheme,
    IdentifierScope,
    Listing,
    ListingStatus,
    MatchReason,
    ResolutionCandidate,
    ResolutionResult,
    ResolutionStatus,
    ResolutionTier,
    ResolutionWarning,
    Security,
    SecurityStatus,
    SecurityType,
    VendorNamespace,
    ambiguous_result,
    create_candidate,
    create_claim,
    create_entity,
    create_listing,
    create_security,
    # Factory functions
    found_result,
    get_scope_for_scheme,
    normalize_and_validate,
    # Validators
    normalize_cik,
    normalize_cusip,
    normalize_ein,
    normalize_figi,
    normalize_isin,
    normalize_lei,
    normalize_mic,
    normalize_sedol,
    normalize_ticker,
    not_found_result,
    validate_cik,
    validate_cusip,
    validate_ein,
    validate_figi,
    validate_isin,
    validate_lei,
    validate_mic,
    validate_scheme_scope,
    validate_sedol,
    validate_ticker,
)

# Protocols (stdlib typing.Protocol - zero deps)
from entityspine.domain.protocols import (
    ClaimStoreProtocol,
    EntityStoreProtocol,
    FullStoreProtocol,
    ListingStoreProtocol,
    ResolverProtocol,
    SearchProtocol,
    SecurityStoreProtocol,
    StorageLifecycleProtocol,
)

# =============================================================================
# STORAGE BACKENDS (Tier 0-1, stdlib only)
# =============================================================================
from entityspine.stores import JsonEntityStore, SqliteStore

__version__ = "0.3.3"

__all__ = [
    "__version__",
    # Storage backends (Tier 0-1, stdlib only)
    "SqliteStore",
    "JsonEntityStore",
    # Domain models (canonical - stdlib dataclasses)
    "Entity",
    "Security",
    "Listing",
    "IdentifierClaim",
    "ResolutionResult",
    "ResolutionCandidate",
    # Enums
    "EntityType",
    "EntityStatus",
    "SecurityType",
    "SecurityStatus",
    "ListingStatus",
    "IdentifierScheme",
    "ClaimStatus",
    "VendorNamespace",
    "IdentifierScope",
    "ResolutionStatus",
    "ResolutionTier",
    "ResolutionWarning",
    "MatchReason",
    # Factory functions
    "found_result",
    "not_found_result",
    "ambiguous_result",
    "create_entity",
    "create_security",
    "create_listing",
    "create_claim",
    "create_candidate",
    # Validators
    "normalize_cik",
    "normalize_lei",
    "normalize_isin",
    "normalize_cusip",
    "normalize_sedol",
    "normalize_figi",
    "normalize_ein",
    "normalize_ticker",
    "normalize_mic",
    "validate_cik",
    "validate_lei",
    "validate_isin",
    "validate_cusip",
    "validate_sedol",
    "validate_figi",
    "validate_ein",
    "validate_ticker",
    "validate_mic",
    "normalize_and_validate",
    "get_scope_for_scheme",
    "validate_scheme_scope",
    "SCHEME_SCOPES",
    # Core utilities
    "generate_ulid",
    "utc_now",
    "to_iso8601",
    "from_iso8601",
    "classify_identifier",
    "IdentifierType",
    # Exceptions
    "EntitySpineError",
    "EntityNotFoundError",
    "ResolutionError",
    "StorageError",
    # Protocols (stdlib typing.Protocol - zero deps)
    "StorageLifecycleProtocol",
    "EntityStoreProtocol",
    "ListingStoreProtocol",
    "SecurityStoreProtocol",
    "ClaimStoreProtocol",
    "SearchProtocol",
    "ResolverProtocol",
    "FullStoreProtocol",
    # Factory
    "create_store",
]


def create_store(
    backend: str = "sqlite",
    path: str | Path | None = None,
    **kwargs,
):
    """
    Create a storage backend.

    Factory function for easy store creation.

    Args:
        backend: Storage backend type.
            - "json": JsonEntityStore (Tier 0, stdlib only)
            - "sqlite": SqliteStore (Tier 1, stdlib only)
            - "orm": SqlModelStore (requires entityspine[orm])
        path: Path to database/file. Defaults to in-memory for sqlite.
        **kwargs: Additional backend-specific options.

    Returns:
        Store instance (returns domain dataclasses).

    Example:
        >>> store = create_store("sqlite", path="entities.db")
        >>> store.initialize()
        >>> store.load_sec_json(data)
        >>> entities = store.get_entities_by_cik("320193")
    """
    if backend == "json":
        from entityspine.stores import JsonEntityStore

        json_path = Path(path) if path else None
        store = JsonEntityStore(json_path)
        store.initialize()
        return store
    elif backend == "sqlite":
        from entityspine.stores import SqliteStore

        db_path = Path(path) if path else ":memory:"
        store = SqliteStore(db_path)
        store.initialize()
        return store
    elif backend == "orm":
        try:
            from entityspine.adapters.orm import SqlModelStore
        except ImportError:
            raise ImportError(
                "SqlModelStore requires the 'orm' extra. Install with: pip install entityspine[orm]"
            )
        db_path = Path(path) if path else Path(":memory:")
        store = SqlModelStore(db_path)
        store.initialize()
        return store
    else:
        raise ValueError(f"Unknown backend: {backend}. Use 'json', 'sqlite', or 'orm'.")
