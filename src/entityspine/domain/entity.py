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
    Legal/organizational identity node in the EntitySpine knowledge graph.

    Entity is the central node type representing companies, persons, funds,
    government bodies, and other legal identities. Identifiers (CIK, LEI, etc.)
    are stored separately in IdentifierClaim to support multi-vendor crosswalks
    and temporal validity tracking.

    Design Principles:
        - **Immutable**: Frozen dataclass ensures thread safety and hashability
        - **No Identifiers**: Use IdentifierClaim for CIK, LEI, EIN, etc.
        - **No Tickers**: Tickers belong on Listing (exchange-specific)
        - **Provenance**: source_system tracks record origin, not identifier source

    Attributes:
        entity_id: ULID primary key (auto-generated if not provided).
        primary_name: Current legal or trading name.
        entity_type: Classification (ORGANIZATION, PERSON, FUND, etc.).
        status: Lifecycle status (ACTIVE, INACTIVE, MERGED).
        jurisdiction: Country/state of incorporation (ISO 3166-1 alpha-2).
        sic_code: Standard Industrial Classification code.
        incorporation_date: Date of incorporation/formation.
        source_system: Data source that created this record.
        source_id: Identifier in the source system.
        redirect_to: Target entity_id for merged entities.
        redirect_reason: Why this entity was merged/redirected.
        merged_at: Timestamp when entity was merged.
        aliases: Tuple of alternative names (immutable for hashability).
        created_at: Record creation timestamp.
        updated_at: Record last update timestamp.

    Examples:
        Create a basic company entity:

        >>> from entityspine.domain import Entity, EntityType
        >>> apple = Entity(
        ...     primary_name="Apple Inc.",
        ...     entity_type=EntityType.ORGANIZATION,
        ...     jurisdiction="US-DE",  # Delaware
        ...     sic_code="3571",  # Electronic computers
        ...     source_system="sec",
        ... )
        >>> apple.primary_name
        'Apple Inc.'

        Create a person entity (for executives, directors):

        >>> tim_cook = Entity(
        ...     primary_name="Timothy D. Cook",
        ...     entity_type=EntityType.PERSON,
        ...     source_system="sec",
        ... )

        Create a fund entity:

        >>> fund = Entity(
        ...     primary_name="Vanguard 500 Index Fund",
        ...     entity_type=EntityType.FUND,
        ...     jurisdiction="US-PA",
        ...     source_system="factset",
        ... )

        Add an alias (returns new immutable Entity):

        >>> apple_with_alias = apple.add_alias("Apple Computer, Inc.")
        >>> "Apple Computer, Inc." in apple_with_alias.aliases
        True

        Merge duplicate entities:

        >>> # When entity A is found to be duplicate of entity B
        >>> merged_entity = apple.merge_into(
        ...     target_entity_id="01HQ8X9...",
        ...     reason="duplicate_resolution"
        ... )
        >>> merged_entity.status
        <EntityStatus.MERGED: 'merged'>
        >>> merged_entity.is_redirect
        True

        Update entity fields (returns new immutable Entity):

        >>> updated = apple.with_update(
        ...     sic_code="3570",
        ...     jurisdiction="US-CA",
        ... )

    See Also:
        - IdentifierClaim: For storing CIK, LEI, CUSIP, etc.
        - Security: For financial instruments issued by entities
        - Listing: For exchange-specific ticker symbols
        - EntityRelationship: For corporate hierarchy and business relationships
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
        """
        Check if this entity redirects to another (i.e., was merged).

        Returns:
            True if this entity has been merged into another entity.

        Examples:
            >>> entity = Entity("Test Corp")
            >>> entity.is_redirect
            False
            >>> merged = entity.merge_into("target_id")
            >>> merged.is_redirect
            True
        """
        return self.redirect_to is not None

    def with_update(self, **kwargs) -> "Entity":
        """
        Create a new Entity with updated fields.

        Since Entity is immutable (frozen), this creates a copy with
        the specified fields changed. Automatically updates the
        updated_at timestamp.

        Args:
            **kwargs: Fields to update (e.g., status=EntityStatus.INACTIVE).

        Returns:
            New Entity instance with updated fields.

        Examples:
            >>> entity = Entity("Test Corp", jurisdiction="US-DE")
            >>> updated = entity.with_update(jurisdiction="US-CA")
            >>> updated.jurisdiction
            'US-CA'
        """
        kwargs.setdefault("updated_at", utc_now())
        return replace(self, **kwargs)

    def add_alias(self, alias: str) -> "Entity":
        """
        Create a new Entity with an additional alias.

        Aliases are used for entity resolution - matching different name
        variations to the same entity.

        Args:
            alias: Alternative name to add.

        Returns:
            New Entity with alias added, or self if alias already exists.

        Examples:
            >>> entity = Entity("Microsoft Corporation")
            >>> with_alias = entity.add_alias("Microsoft Corp")
            >>> "Microsoft Corp" in with_alias.aliases
            True
        """
        if alias in self.aliases or alias == self.primary_name:
            return self
        new_aliases = (*self.aliases, alias)
        return self.with_update(aliases=new_aliases)

    def merge_into(self, target_entity_id: str, reason: str = "merged") -> "Entity":
        """
        Create a merged version of this entity pointing to the target.

        Used when duplicate entities are discovered. The merged entity
        becomes a redirect to the canonical entity.

        Args:
            target_entity_id: The entity_id of the canonical entity.
            reason: Reason for the merge (e.g., "duplicate_resolution").

        Returns:
            New Entity with MERGED status and redirect pointer.

        Examples:
            >>> duplicate = Entity("APPLE INC")
            >>> canonical_id = "01HQ8X9ABC123"
            >>> merged = duplicate.merge_into(canonical_id, "same_cik")
            >>> merged.redirect_to
            '01HQ8X9ABC123'
            >>> merged.status
            <EntityStatus.MERGED: 'merged'>
        """
        return self.with_update(
            redirect_to=target_entity_id,
            redirect_reason=reason,
            status=EntityStatus.MERGED,
            merged_at=utc_now(),
        )
