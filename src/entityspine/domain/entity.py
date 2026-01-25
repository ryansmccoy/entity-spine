"""
Entity domain model (stdlib dataclass).

STDLIB ONLY - NO PYDANTIC.

v2.2.3 DESIGN:
- Entity represents a legal/organizational identity
- NO identifier fields (cik, lei, ein) - use IdentifierClaim
- NO ticker - tickers belong on Listing
- source_system tracks record provenance, not identifier sources
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date, datetime
from typing import TYPE_CHECKING

from entityspine.domain.enums import EntityStatus, EntityType
from entityspine.domain.timestamps import generate_ulid, utc_now

if TYPE_CHECKING:
    from entityspine.domain.entity_events import MergeEvent


@dataclass(frozen=True, slots=True)
class Entity:
    """
    Legal/organizational identity node in the EntitySpine knowledge graph.

    Entity is the central node type representing companies, persons, funds,
    government bodies, and other legal identities. It is the anchor point for
    all other relationships: Securities are issued by Entities, Listings trade
    Securities, and IdentifierClaims point to Entities.
    
    Manifesto:
        EntitySpine's core insight (Principle #1) is that Entity ≠ Security ≠ Listing.
        Apple Inc. (entity) issues AAPL Common Stock (security) which trades on NASDAQ
        with ticker AAPL (listing). This separation is why identifiers like CIK, LEI,
        and EIN are stored in IdentifierClaim (Principle #2), NOT on Entity. This
        design enables multi-vendor crosswalks: FactSet, Bloomberg, and SEC may all
        have different identifiers for Apple, but they all claim to identify the same
        Entity. Confidence scores track which claims are most reliable.
    
    Architecture:
        ```
        ┌──────────────────────────────────────────────────────────┐
        │                  Entity Relationship Model                │
        └──────────────────────────────────────────────────────────┘
        
                           ┌─────────────┐
                           │   Entity    │◄──── IdentifierClaim (CIK, LEI, EIN)
                           │  (Apple)    │
                           └──────┬──────┘
                                  │ issues
                                  ▼
                           ┌─────────────┐
                           │  Security   │◄──── IdentifierClaim (CUSIP, ISIN)
                           │(AAPL Stock) │
                           └──────┬──────┘
                                  │ listed_on
                                  ▼
                           ┌─────────────┐
                           │   Listing   │◄──── IdentifierClaim (TICKER)
                           │(NASDAQ:AAPL)│
                           └─────────────┘
        
        Merged Entity Flow:
        ┌─────────┐        ┌─────────┐
        │Entity A │──────► │Entity B │  (A.redirect_to = B.entity_id)
        │(merged) │        │(active) │
        └─────────┘        └─────────┘
        ```
        Dependencies: None - stdlib only (dataclasses, datetime)
        Storage Tier: T0 (JSON), T1 (SQLite), T2 (DuckDB), T3 (PostgreSQL)
    
    Features:
        - Immutable (frozen dataclass) for thread safety and hashability
        - NO identifier fields - use IdentifierClaim for CIK, LEI, EIN
        - NO ticker field - tickers belong on Listing (exchange-specific)
        - Redirect support for entity merges (non-destructive resolution)
        - Alias tuple for alternative names (also immutable)
        - Provenance tracking via source_system and source_id
        - Type classification (ORGANIZATION, PERSON, FUND, GOVERNMENT)
    
    Examples:
        >>> from entityspine.domain import Entity, EntityType
        >>> apple = Entity(
        ...     primary_name="Apple Inc.",
        ...     entity_type=EntityType.ORGANIZATION,
        ...     jurisdiction="US-DE",
        ...     sic_code="3571",
        ...     source_system="sec",
        ... )
        >>> apple.primary_name
        'Apple Inc.'
        
        >>> # Add an alias (returns new immutable Entity)
        >>> apple_with_alias = apple.add_alias("Apple Computer, Inc.")
        >>> "Apple Computer, Inc." in apple_with_alias.aliases
        True
        
        >>> # Merge duplicate entities
        >>> merged = apple.merge_into("target_entity_id", reason="duplicate")
        >>> merged.status
        <EntityStatus.MERGED: 'merged'>
        >>> merged.is_redirect
        True
    
    Performance:
        - Construction: O(1), ~200ns
        - with_update(): O(n) where n = len(aliases), ~300ns
        - is_redirect: O(1), ~10ns
        - Hash (for dict/set): O(len(entity_id)), ~50ns
    
    Guardrails:
        - Do NOT store CIK, LEI, or EIN on Entity
          ✅ Instead: Use IdentifierClaim with entity_id reference
        - Do NOT store ticker symbols on Entity
          ✅ Instead: Use Listing for exchange-specific tickers
        - Do NOT delete merged entities
          ✅ Instead: Set redirect_to and status=MERGED
    
    Context:
        Problem: Traditional data models conflate entity identity with identifiers,
                 leading to data quality issues when identifiers change or conflict.
        Solution: Entity is a pure identity node; identifiers are claims with
                  provenance, confidence, and temporal validity.
    
    Tags:
        - entity_resolution
        - domain_model
        - knowledge_graph
        - stdlib_only
        - immutable
    
    Doc-Types:
        - MANIFESTO (section: "Core Principles", priority: 10)
        - FEATURES (section: "Domain Models", priority: 10)
        - API_REFERENCE (section: "Entity Model", priority: 10)

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

    def with_update(self, **kwargs) -> Entity:
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

    def add_alias(self, alias: str) -> Entity:
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

    def merge_into(self, target_entity_id: str, reason: str = "merged") -> Entity:
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

    def merge_into_with_event(
        self,
        target_entity_id: str,
        reason: str = "merged",
        *,
        explanation_id: str | None = None,
        run_id: str | None = None,
        confidence: float = 1.0,
        merged_by: str | None = None,
    ) -> tuple[Entity, MergeEvent]:
        """
        Create a merged entity AND a MergeEvent for audit trail.

        This is the preferred method when you need to track merge history.
        Use plain merge_into() for simple merges without event tracking.

        Args:
            target_entity_id: The entity_id of the canonical entity.
            reason: Reason for the merge (e.g., "duplicate_resolution").
            explanation_id: Link to Explanation record.
            run_id: Link to ResolutionRun if part of batch.
            confidence: Confidence in the merge decision (0.0-1.0).
            merged_by: User/system that performed the merge.

        Returns:
            Tuple of (merged_entity, merge_event).

        Examples:
            >>> duplicate = Entity("APPLE INC")
            >>> canonical_id = "01HQ8X9ABC123"
            >>> merged, event = duplicate.merge_into_with_event(
            ...     canonical_id,
            ...     "same_cik",
            ...     confidence=1.0,
            ...     merged_by="resolution_pipeline",
            ... )
            >>> event.source_entity_id == duplicate.entity_id
            True
        """
        import json

        from entityspine.domain.entity_events import MergeEvent

        # Create the merged entity
        merged = self.merge_into(target_entity_id, reason)

        # Create snapshot of original entity for potential reversal
        snapshot = json.dumps({
            "entity_id": self.entity_id,
            "primary_name": self.primary_name,
            "entity_type": self.entity_type.value if hasattr(self.entity_type, "value") else str(self.entity_type),
            "status": self.status.value if hasattr(self.status, "value") else str(self.status),
            "jurisdiction": self.jurisdiction,
            "sic_code": self.sic_code,
            "aliases": list(self.aliases),
            "source_system": self.source_system,
            "source_id": self.source_id,
        })

        # Create the event
        event = MergeEvent(
            source_entity_id=self.entity_id,
            target_entity_id=target_entity_id,
            reason=reason,
            explanation_id=explanation_id,
            run_id=run_id,
            confidence=confidence,
            merged_by=merged_by,
            source_snapshot=snapshot,
        )

        return merged, event
