"""
Storage protocols for EntitySpine domain layer.

STDLIB ONLY - NO PYDANTIC, NO SQLALCHEMY.

These protocols define the contract that all storage backends must implement.
All methods return DOMAIN dataclasses, not Pydantic models or ORM objects.

Protocol Hierarchy:
- EntityStoreProtocol: Core CRUD (ALL backends)
- StorageLifecycleProtocol: Setup/teardown (ALL backends)
- SecurityStoreProtocol: Security operations (Tier 1+)
- SearchProtocol: Search operations (capabilities vary by tier)
- ResolverProtocol: Full resolution interface

Design Principle:
    Stores return domain dataclasses (Entity, Security, Listing, etc.)
    Pydantic/ORM conversions happen at the adapter edges only.
"""

from abc import abstractmethod
from datetime import date
from typing import Any, Protocol, runtime_checkable

from entityspine.domain.claim import IdentifierClaim

# Import domain types (stdlib dataclasses)
from entityspine.domain.entity import Entity
from entityspine.domain.listing import Listing
from entityspine.domain.resolution import ResolutionResult
from entityspine.domain.security import Security


@runtime_checkable
class StorageLifecycleProtocol(Protocol):
    """
    Lifecycle management for storage backends.

    ALL storage implementations must satisfy this interface.
    """

    @abstractmethod
    def initialize(self) -> None:
        """
        Initialize storage (create tables/indexes, load data).

        Idempotent: safe to call multiple times.
        """
        ...

    @abstractmethod
    def close(self) -> None:
        """
        Close storage and release resources.

        May persist pending changes before closing.
        """
        ...


@runtime_checkable
class EntityStoreProtocol(Protocol):
    """
    Core protocol for entity storage backends.

    ALL storage implementations (JSON, SQLite, DuckDB, PostgreSQL)
    must satisfy this interface.

    CRITICAL: All methods return DOMAIN dataclasses, not Pydantic/ORM objects.
    """

    # =========================================================================
    # Entity Operations
    # =========================================================================

    @abstractmethod
    def get_entity(self, entity_id: str) -> Entity | None:
        """
        Get entity by ID, following merge redirects.

        Args:
            entity_id: Entity ULID.

        Returns:
            Entity (domain dataclass) or None.

        Note:
            If entity A merged into B, get_entity("A") returns B.
            Use get_entity_raw() to get A without following redirects.
        """
        ...

    @abstractmethod
    def get_entity_raw(self, entity_id: str) -> Entity | None:
        """
        Get entity by ID WITHOUT following merge redirects.

        Args:
            entity_id: Entity ULID.

        Returns:
            Entity exactly as stored (may have redirect_to set).
        """
        ...

    @abstractmethod
    def get_entities_by_cik(self, cik: str) -> list[Entity]:
        """
        Get entities matching CIK (via claims lookup).

        Args:
            cik: SEC Central Index Key (with or without padding).

        Returns:
            List of matching entities (domain dataclasses).
        """
        ...

    @abstractmethod
    def save_entity(self, entity: Entity) -> None:
        """
        Save or update entity.

        Args:
            entity: Entity (domain dataclass) to save.

        Note:
            Upserts by entity_id.
        """
        ...


@runtime_checkable
class ListingStoreProtocol(Protocol):
    """
    Protocol for listing/ticker operations.

    CRITICAL: All methods return DOMAIN dataclasses.
    """

    @abstractmethod
    def get_listings_by_ticker(
        self,
        ticker: str,
        mic: str | None = None,
        as_of: date | None = None,
    ) -> list[Listing]:
        """
        Get listings matching ticker symbol.

        Args:
            ticker: Stock ticker symbol.
            mic: Market Identifier Code (exchange filter).
            as_of: Point-in-time query (may be ignored by lower tiers).

        Returns:
            List of matching listings (domain dataclasses).

        Note:
            - Tier 0/1: mic and as_of may be ignored
            - Use ResolutionResult.warnings to detect ignored parameters
        """
        ...

    @abstractmethod
    def save_listing(self, listing: Listing) -> None:
        """
        Save or update listing.

        Args:
            listing: Listing (domain dataclass) to save.
        """
        ...


@runtime_checkable
class SecurityStoreProtocol(Protocol):
    """
    Protocol for security operations.

    CRITICAL: All methods return DOMAIN dataclasses.
    """

    @abstractmethod
    def get_security(self, security_id: str) -> Security | None:
        """
        Get security by ID.

        Args:
            security_id: Security ULID.

        Returns:
            Security (domain dataclass) or None.
        """
        ...

    @abstractmethod
    def get_securities_by_entity(self, entity_id: str) -> list[Security]:
        """
        Get all securities for an entity.

        Args:
            entity_id: Entity ULID.

        Returns:
            List of securities (domain dataclasses).
        """
        ...

    @abstractmethod
    def save_security(self, security: Security) -> None:
        """
        Save or update security.

        Args:
            security: Security (domain dataclass) to save.
        """
        ...


@runtime_checkable
class ClaimStoreProtocol(Protocol):
    """
    Protocol for identifier claim operations.

    CRITICAL: All methods return DOMAIN dataclasses.
    """

    @abstractmethod
    def get_claims_by_entity(self, entity_id: str) -> list[IdentifierClaim]:
        """
        Get all claims for an entity.

        Args:
            entity_id: Entity ULID.

        Returns:
            List of claims (domain dataclasses).
        """
        ...

    @abstractmethod
    def get_claims_by_scheme_value(
        self,
        scheme: str,
        value: str,
    ) -> list[IdentifierClaim]:
        """
        Get claims by identifier scheme and value.

        Args:
            scheme: Identifier scheme (cik, lei, isin, etc.).
            value: Identifier value (normalized).

        Returns:
            List of matching claims (domain dataclasses).
        """
        ...

    @abstractmethod
    def save_claim(self, claim: IdentifierClaim) -> None:
        """
        Save or update identifier claim.

        Args:
            claim: IdentifierClaim (domain dataclass) to save.
        """
        ...


@runtime_checkable
class SearchProtocol(Protocol):
    """
    Protocol for search operations.

    Capabilities vary by tier:
    - Tier 0: Exact match only
    - Tier 1: LIKE pattern matching
    - Tier 2+: Full-text search
    """

    @abstractmethod
    def search_entities(
        self,
        query: str,
        limit: int = 10,
    ) -> list[Entity]:
        """
        Search entities by name.

        Args:
            query: Search query (interpretation varies by tier).
            limit: Maximum results to return.

        Returns:
            List of matching entities (domain dataclasses).
        """
        ...


@runtime_checkable
class ResolverProtocol(Protocol):
    """
    Full resolution protocol.

    The main interface for entity resolution.
    Returns ResolutionResult with tier honesty (warnings/limits).
    """

    @abstractmethod
    def resolve(
        self,
        query: str,
        as_of: date | None = None,
        mic: str | None = None,
    ) -> ResolutionResult:
        """
        Resolve any identifier to entity/security/listing.

        Args:
            query: Any identifier (CIK, ticker, name, ISIN, etc.).
            as_of: Point-in-time query (may be ignored by lower tiers).
            mic: Market Identifier Code filter (may be ignored by lower tiers).

        Returns:
            ResolutionResult (domain dataclass) with:
            - entity/security/listing (if found)
            - candidates (for ambiguous matches)
            - warnings (if parameters were ignored)
            - limits (tier capability limits)

        Example:
            >>> result = resolver.resolve("AAPL")
            >>> if result.found:
            ...     print(result.entity.primary_name)
            >>> if result.has_warnings:
            ...     print(result.warnings)
        """
        ...


@runtime_checkable
class FullStoreProtocol(
    StorageLifecycleProtocol,
    EntityStoreProtocol,
    ListingStoreProtocol,
    SecurityStoreProtocol,
    ClaimStoreProtocol,
    SearchProtocol,
    ResolverProtocol,
    Protocol,
):
    """
    Combined protocol for full-featured stores.

    Tier 1+ stores should implement this complete interface.
    """

    # Tier metadata
    tier: int
    tier_name: str
    supports_temporal: bool

    @abstractmethod
    def load_sec_json(self, data: dict[str, Any]) -> int:
        """
        Load entities from SEC company_tickers.json format.

        Args:
            data: Dict in SEC JSON format.

        Returns:
            Number of entities loaded.
        """
        ...
