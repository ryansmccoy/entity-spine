"""
Entity model - Legal/organizational identity.

v2.2.3 DESIGN PRINCIPLES:
1. Entity represents a legal/organizational identity (NOT a security or listing)
2. Entity does NOT have ticker - tickers belong on Listing
3. Identifiers are tracked via IdentifierClaim (canonical source of truth)
4. Entity has NO convenience identifier fields (cik, lei, ein) - use claims
5. source_system tracks where the RECORD came from, not identifier provenance

An Entity represents a legal or organizational identity:
- Apple Inc. (corporation)
- Warren Buffett (person)
- State of California (government)

CRITICAL: Entity does NOT have ticker!
Tickers belong on Listing because:
1. Tickers are exchange-specific
2. Tickers change over time (FB → META)
3. Tickers can be reused by different entities
4. Same entity can have different tickers on different exchanges
"""

from datetime import date, datetime
from enum import Enum

from pydantic import Field, model_validator

from entityspine.adapters.pydantic.base import EntitySpineModel, generate_id
from entityspine.core.timestamps import utc_now


class EntityType(str, Enum):
    """Type of legal entity."""

    ORGANIZATION = "organization"  # Corporation, LLC, etc.
    PERSON = "person"  # Individual
    GOVERNMENT = "government"  # Government entity
    FUND = "fund"  # Investment fund
    TRUST = "trust"  # Trust
    SPV = "spv"  # Special Purpose Vehicle


class EntityStatus(str, Enum):
    """Lifecycle status of an entity."""

    ACTIVE = "active"  # Currently operating
    INACTIVE = "inactive"  # No longer operating
    MERGED = "merged"  # Merged into another entity
    PROVISIONAL = "provisional"  # Pending verification


class Entity(EntitySpineModel):
    """
    Legal/organizational identity.

    v2.2.3 DESIGN:
    - NO identifier convenience fields (cik, lei, ein) - use IdentifierClaim
    - NO identifiers dict - use IdentifierClaim for all identifier tracking
    - Tickers DO NOT belong here - they are on Listing
    - source_system tracks record provenance, not identifier sources

    Attributes:
        entity_id: ULID primary key.
        primary_name: Current legal/trading name.
        entity_type: Type of entity (organization, person, etc.).
        status: Lifecycle status (active, merged, etc.).
        jurisdiction: Country/state of incorporation.
        sic_code: Standard Industrial Classification.
        incorporation_date: Date of incorporation.
        source_system: Where this RECORD came from (not identifier provenance).
        source_id: ID in the source system.
        redirect_to: Entity ID to redirect to (for merged entities).
        redirect_reason: Why this entity redirects.
        merged_at: When entity was merged.
        aliases: All known names.
        created_at: Record creation timestamp (UTC).
        updated_at: Last update timestamp (UTC).

    Example:
        >>> entity = Entity(
        ...     primary_name="Apple Inc.",
        ...     source_system="sec",
        ... )
        >>> # To add identifiers, create IdentifierClaim objects
        >>> claim = IdentifierClaim(
        ...     entity_id=entity.entity_id,
        ...     scheme=IdentifierScheme.CIK,
        ...     value="320193",  # Auto-normalized to 0000320193
        ...     namespace=VendorNamespace.SEC,
        ... )
    """

    entity_id: str = Field(
        default_factory=generate_id,
        min_length=1,
        description="ULID primary key",
    )
    primary_name: str = Field(
        ...,
        min_length=1,
        description="Current legal/trading name",
    )
    entity_type: EntityType = Field(
        default=EntityType.ORGANIZATION,
        description="Type of entity",
    )
    status: EntityStatus = Field(
        default=EntityStatus.ACTIVE,
        description="Lifecycle status",
    )

    # Entity details (NOT identifiers - those go in claims)
    jurisdiction: str | None = Field(
        default=None,
        description="Country/state of incorporation (e.g., US-DE)",
    )
    sic_code: str | None = Field(
        default=None,
        description="Standard Industrial Classification code",
    )
    incorporation_date: date | None = Field(
        default=None,
        description="Date of incorporation/formation",
    )

    # Record provenance (NOT identifier provenance - that's in claims)
    source_system: str = Field(
        default="unknown",
        description="System that created this RECORD (not identifier source)",
    )
    source_id: str | None = Field(
        default=None,
        description="ID in the source system",
    )

    # Redirect support (for merged/renamed entities)
    redirect_to: str | None = Field(
        default=None,
        description="Target entity_id for redirects",
    )
    redirect_reason: str | None = Field(
        default=None,
        description="Reason for redirect (merged, renamed, etc.)",
    )
    merged_at: datetime | None = Field(
        default=None,
        description="When entity was merged (UTC)",
    )

    # All known names (denormalized for search convenience)
    aliases: list[str] = Field(
        default_factory=list,
        description="All known names/aliases for search",
    )

    # Timestamps
    created_at: datetime = Field(
        default_factory=utc_now,
        description="Record creation time (UTC)",
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        description="Last update time (UTC)",
    )

    # Extensible metadata
    metadata: dict[str, str] = Field(
        default_factory=dict,
        description="Additional metadata (string keys/values only)",
    )

    @model_validator(mode="after")
    def validate_redirect(self) -> "Entity":
        """Validate redirect configuration."""
        if self.redirect_to and self.status != EntityStatus.MERGED:
            # Auto-set status to merged if redirect is set
            object.__setattr__(self, "status", EntityStatus.MERGED)
        return self

    @property
    def is_redirect(self) -> bool:
        """Check if this entity redirects to another."""
        return self.redirect_to is not None

    def with_update(self, **kwargs) -> "Entity":
        """
        Create a new Entity with updated fields.

        Args:
            **kwargs: Fields to update

        Returns:
            New Entity with updated fields and updated_at timestamp
        """
        # Use model_copy (Pydantic v2) to preserve types and create a modified copy
        kwargs["updated_at"] = utc_now()
        return self.model_copy(update=kwargs)

    def add_alias(self, alias: str) -> "Entity":
        """
        Create a new Entity with an additional alias.

        Args:
            alias: New alias to add

        Returns:
            New Entity with alias added (if not already present)
        """
        if alias in self.aliases or alias == self.primary_name:
            return self
        new_aliases = [*list(self.aliases), alias]
        return self.with_update(aliases=new_aliases)

    def merge_into(self, target_entity_id: str, reason: str = "merged") -> "Entity":
        """
        Create a merged version of this entity pointing to the target.

        Args:
            target_entity_id: Entity ID to redirect to
            reason: Reason for the merge

        Returns:
            New Entity with redirect set and status=MERGED
        """
        return self.with_update(
            redirect_to=target_entity_id,
            redirect_reason=reason,
            status=EntityStatus.MERGED,
            merged_at=utc_now(),
        )

    # =========================================================================
    # Domain Model Conversion (v2.2.3 - Pydantic as thin wrapper)
    # =========================================================================

    def to_domain(self) -> "entityspine.domain.Entity":
        """
        Convert Pydantic model to domain dataclass.

        The domain dataclass is the canonical representation.
        Pydantic models are thin wrappers for validation/serialization.

        Returns:
            Domain Entity dataclass
        """
        from entityspine.domain import Entity as DomainEntity
        from entityspine.domain import EntityStatus as DomainEntityStatus
        from entityspine.domain import EntityType as DomainEntityType

        # Handle enum values - Pydantic may store as str or Enum
        entity_type_val = (
            self.entity_type.value if hasattr(self.entity_type, "value") else self.entity_type
        )
        status_val = self.status.value if hasattr(self.status, "value") else self.status

        return DomainEntity(
            entity_id=self.entity_id,
            primary_name=self.primary_name,
            entity_type=DomainEntityType(entity_type_val),
            status=DomainEntityStatus(status_val),
            jurisdiction=self.jurisdiction,
            sic_code=self.sic_code,
            incorporation_date=self.incorporation_date,
            source_system=self.source_system,
            source_id=self.source_id,
            redirect_to=self.redirect_to,
            redirect_reason=self.redirect_reason,
            merged_at=self.merged_at,
            aliases=tuple(self.aliases),
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_domain(cls, entity: "entityspine.domain.Entity") -> "Entity":
        """
        Create Pydantic model from domain dataclass.

        Args:
            entity: Domain Entity dataclass

        Returns:
            Pydantic Entity model
        """
        return cls(
            entity_id=entity.entity_id,
            primary_name=entity.primary_name,
            entity_type=EntityType(entity.entity_type.value),
            status=EntityStatus(entity.status.value),
            jurisdiction=entity.jurisdiction,
            sic_code=entity.sic_code,
            incorporation_date=entity.incorporation_date,
            source_system=entity.source_system,
            source_id=entity.source_id,
            redirect_to=entity.redirect_to,
            redirect_reason=entity.redirect_reason,
            merged_at=entity.merged_at,
            aliases=list(entity.aliases),
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
