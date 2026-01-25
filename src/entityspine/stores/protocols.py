"""
Repository protocols for EntitySpine storage backends.

STDLIB ONLY - NO PYDANTIC, NO SQLALCHEMY.

These protocols define the contract for individual repositories, allowing
the same repository interfaces to be implemented across different backends
(SQLite, PostgreSQL, JSON, etc.).

The Facade (SqliteStore, JsonEntityStore, etc.) composes these repositories
to provide a unified store interface.

Design Principle:
    Repositories are single-responsibility classes that handle CRUD
    for a specific domain type. They return DOMAIN dataclasses.
"""

from __future__ import annotations

from abc import abstractmethod
from datetime import date
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from entityspine.domain import (
        Address,
        AddressType,
        Asset,
        Brand,
        Case,
        Contract,
        Entity,
        EntityCluster,
        EntityClusterMember,
        Event,
        EventType,
        Geo,
        IdentifierClaim,
        IdentifierScheme,
        Listing,
        Product,
        Relationship,
        RoleAssignment,
        Security,
    )
    from entityspine.domain.graph import EntityRelationship


# =============================================================================
# Core Repositories (Entity/Security/Listing hierarchy)
# =============================================================================


@runtime_checkable
class EntityRepositoryProtocol(Protocol):
    """
    Protocol for entity repository operations.
    
    Implements Single Responsibility: Entity CRUD only.
    """

    @abstractmethod
    def save(self, entity: Entity) -> None:
        """Save or update an entity."""
        ...

    @abstractmethod
    def get_by_id(self, entity_id: str, follow_redirects: bool = True) -> Entity | None:
        """Get entity by ID, optionally following redirects."""
        ...

    @abstractmethod
    def get_raw(self, entity_id: str) -> Entity | None:
        """Get entity by ID WITHOUT following redirects."""
        ...

    @abstractmethod
    def get_by_cik(self, cik: str) -> list[Entity]:
        """Get entities matching CIK."""
        ...

    @abstractmethod
    def get_by_ticker(self, ticker: str) -> list[Entity]:
        """Get entities matching ticker (via listing lookup)."""
        ...

    @abstractmethod
    def search(self, query: str, limit: int = 10) -> list[tuple[Entity, float]]:
        """Search entities by name or identifier, returning (entity, score) pairs."""
        ...

    @abstractmethod
    def count(self) -> int:
        """Count total entities."""
        ...


@runtime_checkable
class SecurityRepositoryProtocol(Protocol):
    """Protocol for security repository operations."""

    @abstractmethod
    def save(self, security: Security) -> None:
        """Save or update a security."""
        ...

    @abstractmethod
    def get_by_id(self, security_id: str) -> Security | None:
        """Get security by ID."""
        ...

    @abstractmethod
    def get_by_entity(self, entity_id: str) -> list[Security]:
        """Get all securities for an entity."""
        ...

    @abstractmethod
    def count(self) -> int:
        """Count total securities."""
        ...


@runtime_checkable
class ListingRepositoryProtocol(Protocol):
    """Protocol for listing repository operations."""

    @abstractmethod
    def save(self, listing: Listing) -> None:
        """Save or update a listing."""
        ...

    @abstractmethod
    def get_by_ticker(
        self,
        ticker: str,
        mic: str | None = None,
        as_of: date | None = None,
    ) -> list[Listing]:
        """Get listings by ticker, optionally filtered by MIC and as_of."""
        ...

    @abstractmethod
    def get_by_security(self, security_id: str) -> list[Listing]:
        """Get all listings for a security."""
        ...

    @abstractmethod
    def count(self) -> int:
        """Count total listings."""
        ...


@runtime_checkable
class ClaimRepositoryProtocol(Protocol):
    """Protocol for identifier claim repository operations."""

    @abstractmethod
    def save(self, claim: IdentifierClaim) -> None:
        """Save or update an identifier claim."""
        ...

    @abstractmethod
    def get(self, scheme: str, value: str) -> list[IdentifierClaim]:
        """Get claims by scheme and value."""
        ...

    @abstractmethod
    def get_for_entity(self, entity_id: str) -> list[IdentifierClaim]:
        """Get all claims for an entity."""
        ...

    @abstractmethod
    def get_by_value(
        self,
        scheme: IdentifierScheme,
        value: str,
    ) -> list[IdentifierClaim]:
        """Get claims by scheme enum and value."""
        ...

    @abstractmethod
    def count(self) -> int:
        """Count total claims."""
        ...


# =============================================================================
# Knowledge Graph Repositories (KG Nodes)
# =============================================================================


@runtime_checkable
class AssetRepositoryProtocol(Protocol):
    """Protocol for asset repository operations."""

    @abstractmethod
    def save(self, asset: Asset) -> None:
        """Save or update an asset."""
        ...

    @abstractmethod
    def get_by_id(self, asset_id: str) -> Asset | None:
        """Get asset by ID."""
        ...

    @abstractmethod
    def get_by_owner(self, entity_id: str) -> list[Asset]:
        """Get all assets owned by an entity."""
        ...

    @abstractmethod
    def count(self) -> int:
        """Count total assets."""
        ...


@runtime_checkable
class ContractRepositoryProtocol(Protocol):
    """Protocol for contract repository operations."""

    @abstractmethod
    def save(self, contract: Contract) -> None:
        """Save or update a contract."""
        ...

    @abstractmethod
    def get_by_id(self, contract_id: str) -> Contract | None:
        """Get contract by ID."""
        ...

    @abstractmethod
    def count(self) -> int:
        """Count total contracts."""
        ...


@runtime_checkable
class ProductRepositoryProtocol(Protocol):
    """Protocol for product repository operations."""

    @abstractmethod
    def save(self, product: Product) -> None:
        """Save or update a product."""
        ...

    @abstractmethod
    def get_by_id(self, product_id: str) -> Product | None:
        """Get product by ID."""
        ...

    @abstractmethod
    def get_by_owner(self, entity_id: str) -> list[Product]:
        """Get all products owned by an entity."""
        ...

    @abstractmethod
    def count(self) -> int:
        """Count total products."""
        ...


@runtime_checkable
class BrandRepositoryProtocol(Protocol):
    """Protocol for brand repository operations."""

    @abstractmethod
    def save(self, brand: Brand) -> None:
        """Save or update a brand."""
        ...

    @abstractmethod
    def get_by_id(self, brand_id: str) -> Brand | None:
        """Get brand by ID."""
        ...

    @abstractmethod
    def get_by_owner(self, entity_id: str) -> list[Brand]:
        """Get all brands owned by an entity."""
        ...

    @abstractmethod
    def count(self) -> int:
        """Count total brands."""
        ...


@runtime_checkable
class EventRepositoryProtocol(Protocol):
    """Protocol for event repository operations."""

    @abstractmethod
    def save(self, event: Event) -> None:
        """Save or update an event."""
        ...

    @abstractmethod
    def get_by_id(self, event_id: str) -> Event | None:
        """Get event by ID."""
        ...

    @abstractmethod
    def get_by_type(self, event_type: EventType) -> list[Event]:
        """Get all events of a specific type."""
        ...

    @abstractmethod
    def count(self) -> int:
        """Count total events."""
        ...


# =============================================================================
# Location Repositories
# =============================================================================


@runtime_checkable
class GeoRepositoryProtocol(Protocol):
    """Protocol for geographic location repository operations."""

    @abstractmethod
    def save(self, geo: Geo) -> None:
        """Save or update a geographic location."""
        ...

    @abstractmethod
    def get_by_id(self, geo_id: str) -> Geo | None:
        """Get geographic location by ID."""
        ...

    @abstractmethod
    def count(self) -> int:
        """Count total geographic locations."""
        ...


@runtime_checkable
class AddressRepositoryProtocol(Protocol):
    """Protocol for address repository operations."""

    @abstractmethod
    def save(self, address: Address) -> None:
        """Save or update an address."""
        ...

    @abstractmethod
    def get_by_id(self, address_id: str) -> Address | None:
        """Get address by ID."""
        ...

    @abstractmethod
    def get_by_hash(self, normalized_hash: str) -> Address | None:
        """Get address by normalized hash for deduplication."""
        ...

    @abstractmethod
    def save_entity_address(
        self,
        entity_id: str,
        address_id: str,
        address_type: AddressType,
    ) -> None:
        """Link an entity to an address."""
        ...

    @abstractmethod
    def count(self) -> int:
        """Count total addresses."""
        ...


# =============================================================================
# Graph Repositories (Relationships)
# =============================================================================


@runtime_checkable
class RoleRepositoryProtocol(Protocol):
    """Protocol for role assignment repository operations."""

    @abstractmethod
    def save(self, role: RoleAssignment) -> None:
        """Save or update a role assignment."""
        ...

    @abstractmethod
    def get_by_id(self, role_assignment_id: str) -> RoleAssignment | None:
        """Get role assignment by ID."""
        ...

    @abstractmethod
    def get_by_org(self, org_entity_id: str) -> list[RoleAssignment]:
        """Get all role assignments for an organization."""
        ...

    @abstractmethod
    def get_by_person(self, person_entity_id: str) -> list[RoleAssignment]:
        """Get all role assignments for a person."""
        ...

    @abstractmethod
    def count(self) -> int:
        """Count total role assignments."""
        ...


@runtime_checkable
class RelationshipRepositoryProtocol(Protocol):
    """Protocol for relationship repository operations."""

    @abstractmethod
    def save(self, rel: Relationship) -> None:
        """Save or update a generic relationship."""
        ...

    @abstractmethod
    def get_by_id(self, relationship_id: str) -> Relationship | None:
        """Get relationship by ID."""
        ...

    @abstractmethod
    def get_by_source_id(self, source_id: str, limit: int = 100) -> list[Relationship]:
        """Get all relationships from a source node."""
        ...

    @abstractmethod
    def count(self) -> int:
        """Count total relationships."""
        ...

    @abstractmethod
    def save_entity_relationship(self, rel: EntityRelationship) -> None:
        """Save or update an entity-to-entity relationship."""
        ...

    @abstractmethod
    def get_entity_relationships(
        self,
        from_entity_id: str | None = None,
        to_entity_id: str | None = None,
        relationship_types: list | None = None,
    ) -> list[EntityRelationship]:
        """Get entity relationships with optional filters."""
        ...


@runtime_checkable
class CaseRepositoryProtocol(Protocol):
    """Protocol for legal case repository operations."""

    @abstractmethod
    def save(self, case: Case) -> None:
        """Save or update a legal case."""
        ...

    @abstractmethod
    def get_by_id(self, case_id: str) -> Case | None:
        """Get case by ID."""
        ...

    @abstractmethod
    def get_by_target(self, target_entity_id: str) -> list[Case]:
        """Get all cases involving a target entity."""
        ...

    @abstractmethod
    def get_by_authority(self, authority_entity_id: str) -> list[Case]:
        """Get all cases from an authority (court/regulator)."""
        ...

    @abstractmethod
    def count(self) -> int:
        """Count total cases."""
        ...


@runtime_checkable
class ClusterRepositoryProtocol(Protocol):
    """Protocol for entity cluster repository operations (deduplication)."""

    @abstractmethod
    def save(self, cluster: EntityCluster) -> None:
        """Save or update an entity cluster."""
        ...

    @abstractmethod
    def get_by_id(self, cluster_id: str) -> EntityCluster | None:
        """Get cluster by ID."""
        ...

    @abstractmethod
    def get_by_status(self, status: str) -> list[EntityCluster]:
        """Get clusters by status (pending, approved, rejected, merged)."""
        ...

    @abstractmethod
    def count(self) -> int:
        """Count total clusters."""
        ...

    @abstractmethod
    def save_member(self, member: EntityClusterMember) -> None:
        """Save or update a cluster membership."""
        ...

    @abstractmethod
    def get_members(self, cluster_id: str) -> list[EntityClusterMember]:
        """Get all members of a cluster."""
        ...

    @abstractmethod
    def get_clusters_for_entity(self, entity_id: str) -> list[EntityClusterMember]:
        """Get all cluster memberships for an entity."""
        ...

    @abstractmethod
    def member_count(self) -> int:
        """Count total cluster memberships."""
        ...
