"""
Storage protocols for EntitySpine.

These protocols define the contract that all storage backends must implement.
Based on design document 06_PROTOCOLS_AND_INTERFACES.md (authoritative).

Protocol Hierarchy:
- EntityStoreProtocol: Core CRUD (ALL backends)
- StorageLifecycleProtocol: Setup/teardown (ALL backends)
- SecurityStoreProtocol: Security operations (Tier 1+)
- SearchProtocol: Search operations (capabilities vary by tier)
"""

from datetime import date
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from entityspine.adapters.pydantic import Entity, IdentifierClaim, Listing, Security


@runtime_checkable
class EntityStoreProtocol(Protocol):
    """
    Core protocol for entity storage backends.

    ALL storage implementations (JSON, SQLite, DuckDB, PostgreSQL)
    must satisfy this interface.

    Note:
        This protocol includes ONLY methods that ALL backends can implement.
        Tier-specific features are in separate protocols.
    """

    # =========================================================================
    # Entity Operations
    # =========================================================================

    def get_entity(self, entity_id: str) -> "Entity | None":
        """
        Get entity by ID, following merge redirects.

        Args:
            entity_id: Entity ULID.

        Returns:
            Entity (canonical, after following redirects) or None.

        Note:
            If entity A merged into B, get_entity("A") returns B.
            Use get_entity_raw() to get A without following redirects.
        """
        ...

    def get_entity_raw(self, entity_id: str) -> "Entity | None":
        """
        Get entity by ID WITHOUT following merge redirects.

        Args:
            entity_id: Entity ULID.

        Returns:
            Entity exactly as stored (may have redirect_to set).
        """
        ...

    def get_entities_by_cik(self, cik: str) -> "list[Entity]":
        """
        Get entities matching CIK (via claims lookup).

        Args:
            cik: SEC Central Index Key (with or without padding).

        Returns:
            List of matching entities (usually 0 or 1).
        """
        ...

    def save_entity(self, entity: "Entity") -> None:
        """
        Save or update entity.

        Args:
            entity: Entity to save.

        Note:
            Upserts by entity_id.
        """
        ...

    # =========================================================================
    # Listing Operations (ticker resolution)
    # =========================================================================

    def get_listings_by_ticker(
        self,
        ticker: str,
        mic: str | None = None,
        as_of: date | None = None,
    ) -> "list[Listing]":
        """
        Get listings matching ticker.

        Args:
            ticker: Stock ticker symbol (case-insensitive).
            mic: Optional Market Identifier Code filter.
            as_of: Optional point-in-time filter.

        Returns:
            List of matching listings.

        Note:
            If as_of filtering is not supported (Tier 0-1), return current
            listings. The resolver will add appropriate warnings.
        """
        ...

    def get_listings_by_security(self, security_id: str) -> "list[Listing]":
        """
        Get all listings for a security.

        Args:
            security_id: Security ULID.

        Returns:
            All listings (current and historical) for the security.
        """
        ...

    # =========================================================================
    # Claim Operations
    # =========================================================================

    def get_claims(
        self,
        scheme: str,
        value: str,
    ) -> "list[IdentifierClaim]":
        """
        Get claims matching scheme and value.

        Args:
            scheme: Identifier scheme (cik, lei, isin, etc.).
            value: Identifier value.

        Returns:
            List of matching claims.
        """
        ...

    def save_claim(self, claim: "IdentifierClaim") -> None:
        """
        Save identifier claim.

        Args:
            claim: Claim to save.
        """
        ...

    # =========================================================================
    # Statistics
    # =========================================================================

    def entity_count(self) -> int:
        """
        Get total number of entities.

        Returns:
            Count of entities in store.
        """
        ...

    def listing_count(self) -> int:
        """
        Get total number of listings.

        Returns:
            Count of listings in store.
        """
        ...


@runtime_checkable
class StorageLifecycleProtocol(Protocol):
    """
    Protocol for storage lifecycle management.

    Handles initialization, cleanup, and data loading.
    """

    def initialize(self) -> None:
        """
        Initialize storage (create tables/indexes).

        Idempotent: safe to call multiple times.
        """
        ...

    def close(self) -> None:
        """
        Close storage connections and release resources.
        """
        ...

    def load_sec_json(self, data: dict) -> int:
        """
        Load entities from SEC company_tickers.json format.

        Args:
            data: Dict in SEC JSON format:
                {"0": {"cik_str": "320193", "ticker": "AAPL", "title": "..."}}

        Returns:
            Number of entities loaded.

        Note:
            This creates Entity, Security, Listing, and Claim records
            from the flat SEC JSON structure.
        """
        ...


@runtime_checkable
class SecurityStoreProtocol(Protocol):
    """
    Protocol for security-level operations.

    Required for Tier 1+, optional for Tier 0.
    """

    def get_security(self, security_id: str) -> "Security | None":
        """
        Get security by ID.

        Args:
            security_id: Security ULID.

        Returns:
            Security or None.
        """
        ...

    def get_securities_by_entity(self, entity_id: str) -> "list[Security]":
        """
        Get all securities issued by an entity.

        Args:
            entity_id: Entity ULID.

        Returns:
            List of securities.
        """
        ...

    def save_security(self, security: "Security") -> None:
        """
        Save or update security.

        Args:
            security: Security to save.
        """
        ...


@runtime_checkable
class SearchProtocol(Protocol):
    """
    Protocol for search operations.

    Capabilities vary by tier:
    - Tier 0: Exact match only
    - Tier 1: LIKE patterns
    - Tier 2-3: Full-text search
    """

    def search_entities(
        self,
        query: str,
        limit: int = 10,
    ) -> "list[tuple[Entity, float]]":
        """
        Search entities by name.

        Args:
            query: Search query.
            limit: Maximum results.

        Returns:
            List of (entity, similarity_score) tuples.
        """
        ...

    def search_aliases(
        self,
        query: str,
        limit: int = 10,
    ) -> list[tuple[str, str, float]]:
        """
        Search entity aliases.

        Args:
            query: Search query.
            limit: Maximum results.

        Returns:
            List of (entity_id, alias_text, similarity_score) tuples.
        """
        ...


# Tier capabilities for documentation
TIER_CAPABILITIES = {
    0: {
        "name": "JSON",
        "temporal": False,
        "search": "exact",
        "securities": False,
        "redirects": True,
        "max_entities": 50_000,
        "limitations": [
            "as_of_ignored: No temporal data",
            "search_exact_only: No fuzzy search",
            "no_securities: Security/Listing hierarchy not available",
        ],
    },
    1: {
        "name": "SQLite",
        "temporal": False,
        "search": "like",
        "securities": True,
        "redirects": True,
        "max_entities": 1_000_000,
        "limitations": [
            "as_of_ignored: No temporal data",
            "search_like_only: LIKE patterns, no full-text",
        ],
    },
    2: {
        "name": "DuckDB",
        "temporal": True,
        "search": "fulltext",
        "securities": True,
        "redirects": True,
        "max_entities": 10_000_000,
        "limitations": [],
    },
}
