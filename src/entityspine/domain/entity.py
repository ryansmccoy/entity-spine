"""
Entity domain model (stdlib dataclass).

STDLIB ONLY - NO PYDANTIC.

v2.2.3 DESIGN:
- Entity represents a legal/organizational identity
- NO identifier fields (cik, lei, ein) - use IdentifierClaim
- NO ticker - tickers belong on Listing
- source_system tracks record provenance, not identifier sources
"""

from dataclasses import dataclass, field, replace
from datetime import date, datetime

from entityspine.domain.enums import EntityStatus, EntityType
from entityspine.domain.timestamps import generate_ulid, utc_now


@dataclass(frozen=True, slots=True)
class Entity:
    """
    Legal/organizational identity.

    v2.2.3 DESIGN:
    - NO identifier convenience fields - use IdentifierClaim
    - NO ticker - tickers belong on Listing
    - Immutable (frozen) for thread safety

    Attributes:
        entity_id: ULID primary key
        primary_name: Current legal/trading name
        entity_type: Type of entity
        status: Lifecycle status
        jurisdiction: Country/state of incorporation
        sic_code: Standard Industrial Classification
        incorporation_date: Date of incorporation
        source_system: Where this RECORD came from
        source_id: ID in the source system
        redirect_to: Entity ID to redirect to (for merged entities)
        redirect_reason: Why this entity redirects
        merged_at: When entity was merged
        aliases: All known names
        created_at: Record creation timestamp
        updated_at: Last update timestamp
    """

    # Required fields
    primary_name: str

    # Primary key (auto-generated if not provided)
    entity_id: str = field(default_factory=generate_ulid)

    # Entity classification
    entity_type: EntityType = EntityType.ORGANIZATION
    status: EntityStatus = EntityStatus.ACTIVE

    # Entity details
    jurisdiction: str | None = None
    sic_code: str | None = None
    incorporation_date: date | None = None

    # Record provenance (NOT identifier provenance)
    source_system: str = "unknown"
    source_id: str | None = None

    # Redirect support (for merges)
    redirect_to: str | None = None
    redirect_reason: str | None = None
    merged_at: datetime | None = None

    # Aliases
    aliases: tuple = field(default_factory=tuple)  # Use tuple for frozen dataclass

    # Timestamps
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def __post_init__(self):
        """Validate entity after creation."""
        if not self.primary_name or not self.primary_name.strip():
            raise ValueError("primary_name cannot be empty")
        if not self.entity_id or not self.entity_id.strip():
            raise ValueError("entity_id cannot be empty")
        # Convert aliases list to tuple if needed (for hashability)
        if isinstance(self.aliases, list):
            object.__setattr__(self, "aliases", tuple(self.aliases))

    @property
    def is_redirect(self) -> bool:
        """Check if this entity redirects to another."""
        return self.redirect_to is not None

    def with_update(self, **kwargs) -> "Entity":
        """Create a new Entity with updated fields."""
        kwargs.setdefault("updated_at", utc_now())
        return replace(self, **kwargs)

    def add_alias(self, alias: str) -> "Entity":
        """Create a new Entity with an additional alias."""
        if alias in self.aliases or alias == self.primary_name:
            return self
        new_aliases = (*self.aliases, alias)
        return self.with_update(aliases=new_aliases)

    def merge_into(self, target_entity_id: str, reason: str = "merged") -> "Entity":
        """Create a merged version pointing to the target."""
        return self.with_update(
            redirect_to=target_entity_id,
            redirect_reason=reason,
            status=EntityStatus.MERGED,
            merged_at=utc_now(),
        )
