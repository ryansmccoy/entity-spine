"""
Timeline Domain Models for EntitySpine.

STDLIB ONLY - NO PYDANTIC.

These models represent temporal events and snapshots for tracking entity history:
- TimelineEventType: Types of timeline events (not to be confused with business EventType)
- TimelineEvent: A single event in an entity's timeline
- EntitySnapshot: Point-in-time state capture
- StateDiff: Difference between two entity states
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any

from entityspine.domain.timestamps import utc_now


class TimelineEventType(str, Enum):
    """
    Types of timeline events for entity history tracking.
    
    Note: This is different from domain.enums.EventType which represents
    business events (M&A, legal, etc.). This enum tracks EntitySpine
    internal state changes.
    """

    # Entity lifecycle
    ENTITY_CREATED = "entity_created"
    ENTITY_UPDATED = "entity_updated"
    ENTITY_MERGED = "entity_merged"

    # Name changes
    NAME_CHANGED = "name_changed"
    ALIAS_ADDED = "alias_added"

    # Identifier changes
    IDENTIFIER_ADDED = "identifier_added"
    IDENTIFIER_REMOVED = "identifier_removed"

    # Role changes
    OFFICER_APPOINTED = "officer_appointed"
    OFFICER_DEPARTED = "officer_departed"
    ROLE_CHANGED = "role_changed"

    # Relationship changes
    RELATIONSHIP_ADDED = "relationship_added"
    RELATIONSHIP_ENDED = "relationship_ended"

    # Listing changes
    LISTING_ADDED = "listing_added"
    LISTING_REMOVED = "listing_removed"
    TICKER_CHANGED = "ticker_changed"

    # Security changes
    SECURITY_ISSUED = "security_issued"
    SECURITY_RETIRED = "security_retired"


@dataclass(frozen=True)
class TimelineEvent:
    """
    A single event in an entity's timeline.

    Represents something that happened to an entity at a point in time.
    """

    event_type: TimelineEventType
    event_date: date
    description: str

    # What changed
    old_value: str | None = None
    new_value: str | None = None

    # Related entities
    entity_id: str | None = None
    related_entity_id: str | None = None

    # Provenance
    source_system: str = "unknown"
    source_ref: str | None = None
    confidence: float = 1.0

    # Timestamps
    captured_at: datetime = field(default_factory=utc_now)


@dataclass
class EntitySnapshot:
    """
    Point-in-time snapshot of an entity.

    Captures entity state at a specific date for temporal queries.
    """

    entity_id: str
    snapshot_date: date

    # Entity state
    primary_name: str
    aliases: list[str] = field(default_factory=list)
    entity_type: str | None = None
    status: str | None = None

    # Identifiers at this time
    identifiers: dict[str, str] = field(default_factory=dict)  # scheme -> value

    # Listings at this time
    tickers: list[str] = field(default_factory=list)

    # Officers at this time
    officers: list[dict[str, Any]] = field(default_factory=list)

    # Relationships at this time
    relationships: list[dict[str, Any]] = field(default_factory=list)

    # Source information
    source_system: str = "entityspine"
    captured_at: datetime = field(default_factory=utc_now)


@dataclass
class StateDiff:
    """
    Difference between two entity states.

    Shows what changed between two points in time.
    """

    entity_id: str
    from_date: date
    to_date: date

    # Name changes
    name_changed: bool = False
    old_name: str | None = None
    new_name: str | None = None

    # Identifier changes
    identifiers_added: dict[str, str] = field(default_factory=dict)
    identifiers_removed: dict[str, str] = field(default_factory=dict)

    # Listing changes
    tickers_added: list[str] = field(default_factory=list)
    tickers_removed: list[str] = field(default_factory=list)

    # Officer changes
    officers_added: list[dict[str, Any]] = field(default_factory=list)
    officers_removed: list[dict[str, Any]] = field(default_factory=list)

    # Relationship changes
    relationships_added: list[dict[str, Any]] = field(default_factory=list)
    relationships_removed: list[dict[str, Any]] = field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        """Check if there are any differences."""
        return (
            self.name_changed
            or bool(self.identifiers_added)
            or bool(self.identifiers_removed)
            or bool(self.tickers_added)
            or bool(self.tickers_removed)
            or bool(self.officers_added)
            or bool(self.officers_removed)
            or bool(self.relationships_added)
            or bool(self.relationships_removed)
        )

    @property
    def change_summary(self) -> str:
        """Get a human-readable summary of changes."""
        changes = []
        if self.name_changed:
            changes.append(f"Name: {self.old_name} → {self.new_name}")
        if self.identifiers_added:
            for scheme, value in self.identifiers_added.items():
                changes.append(f"Added {scheme}: {value}")
        if self.identifiers_removed:
            for scheme, value in self.identifiers_removed.items():
                changes.append(f"Removed {scheme}: {value}")
        if self.tickers_added:
            changes.append(f"Added tickers: {', '.join(self.tickers_added)}")
        if self.tickers_removed:
            changes.append(f"Removed tickers: {', '.join(self.tickers_removed)}")
        if self.officers_added:
            changes.append(f"Officers added: {len(self.officers_added)}")
        if self.officers_removed:
            changes.append(f"Officers departed: {len(self.officers_removed)}")
        return "; ".join(changes) if changes else "No changes"
