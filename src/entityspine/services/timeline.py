"""
Timeline Service for Entity History.

Track and query entity changes over time:

    from entityspine import TimelineService
    
    timeline = TimelineService(store)
    
    # Get complete entity timeline
    events = timeline.get_entity_timeline("entity_id")
    
    # Get entity state at a point in time
    snapshot = timeline.get_entity_at(entity_id, date(2020, 1, 1))
    
    # Track specific changes
    name_changes = timeline.get_name_changes(entity_id)
    role_changes = timeline.get_officer_changes(entity_id)
    
    # Compare two points in time
    diff = timeline.compare_states(entity_id, date1, date2)

Design Principles:
1. Event-sourced view of entity history
2. Point-in-time queries (as_of semantics)
3. Diff/comparison capabilities
4. Source provenance tracking
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import TYPE_CHECKING

from entityspine.domain.timeline import (
    EntitySnapshot,
    StateDiff,
    TimelineEvent,
    TimelineEventType,
)

if TYPE_CHECKING:
    from entityspine.stores.sqlite_store import SqliteStore

logger = logging.getLogger(__name__)

# Alias for backward compatibility
EventType = TimelineEventType


# =============================================================================
# Timeline Service
# =============================================================================


class TimelineService:
    """
    Service for tracking entity history and temporal queries.

    Examples:
        >>> timeline = TimelineService(store)
        >>>
        >>> # Get full timeline
        >>> events = timeline.get_entity_timeline(entity_id)
        >>> for event in events:
        ...     print(f"{event.event_date}: {event.description}")
        >>>
        >>> # Get state at point in time
        >>> snapshot = timeline.get_entity_at(entity_id, date(2020, 1, 1))
        >>>
        >>> # Compare two dates
        >>> diff = timeline.compare_states(entity_id, date(2019, 1, 1), date(2024, 1, 1))
        >>> print(f"Changes detected: {diff.has_changes}")
    """

    def __init__(self, store: SqliteStore):
        """
        Initialize the timeline service.

        Args:
            store: The underlying storage backend.
        """
        self.store = store

    # =========================================================================
    # Timeline Retrieval
    # =========================================================================

    def get_entity_timeline(
        self,
        entity_id: str,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        event_types: list[TimelineEventType] | None = None,
    ) -> list[TimelineEvent]:
        """
        Get the complete timeline for an entity.

        Args:
            entity_id: Entity to get timeline for.
            start_date: Filter events after this date.
            end_date: Filter events before this date.
            event_types: Filter by event types.

        Returns:
            List of timeline events, sorted by date.
        """
        events: list[TimelineEvent] = []

        # Get entity creation
        entity = self.store.get_entity(entity_id)
        if entity:
            events.append(
                TimelineEvent(
                    event_type=TimelineEventType.ENTITY_CREATED,
                    event_date=entity.created_at.date() if isinstance(entity.created_at, datetime) else entity.created_at,  # type: ignore
                    description=f"Entity created: {entity.primary_name}",
                    entity_id=entity_id,
                    new_value=entity.primary_name,
                    source_system=entity.source_system,
                )
            )

        # Get role changes
        events.extend(self._get_role_events(entity_id))

        # Get relationship events
        events.extend(self._get_relationship_events(entity_id))

        # Get listing events
        events.extend(self._get_listing_events(entity_id))

        # Get identifier events
        events.extend(self._get_identifier_events(entity_id))

        # Filter by date range
        if start_date:
            events = [e for e in events if e.event_date >= start_date]
        if end_date:
            events = [e for e in events if e.event_date <= end_date]

        # Filter by event type
        if event_types:
            events = [e for e in events if e.event_type in event_types]

        # Sort by date
        events.sort(key=lambda e: e.event_date)

        return events

    def _get_role_events(self, entity_id: str) -> list[TimelineEvent]:
        """Get role-related timeline events."""
        events = []

        # Get all role assignments for this organization
        roles = self.store.get_role_assignments(org_entity_id=entity_id, current_only=False)

        for role in roles:
            person = self.store.get_entity(role.person_entity_id)
            person_name = person.primary_name if person else "Unknown"

            # Appointment event
            if role.start_date:
                events.append(
                    TimelineEvent(
                        event_type=TimelineEventType.OFFICER_APPOINTED,
                        event_date=role.start_date,
                        description=f"{person_name} appointed as {role.role_type.value}",
                        entity_id=entity_id,
                        related_entity_id=role.person_entity_id,
                        new_value=role.role_type.value,
                        source_system=role.source_system,
                        source_ref=role.source_ref,
                        confidence=role.confidence,
                    )
                )

            # Departure event
            if role.end_date:
                events.append(
                    TimelineEvent(
                        event_type=EventType.OFFICER_DEPARTED,
                        event_date=role.end_date,
                        description=f"{person_name} departed as {role.role_type.value}",
                        entity_id=entity_id,
                        related_entity_id=role.person_entity_id,
                        old_value=role.role_type.value,
                        source_system=role.source_system,
                        source_ref=role.source_ref,
                    )
                )

        return events

    def _get_relationship_events(self, entity_id: str) -> list[TimelineEvent]:
        """Get relationship-related timeline events."""
        events = []

        # Outgoing relationships
        rels = self.store.get_entity_relationships(from_entity_id=entity_id)
        for rel in rels:
            target = self.store.get_entity(rel.to_entity_id)
            target_name = target.primary_name if target else "Unknown"

            if rel.valid_from:
                events.append(
                    TimelineEvent(
                        event_type=EventType.RELATIONSHIP_ADDED,
                        event_date=rel.valid_from,
                        description=f"Relationship added: {rel.relationship_type.value} to {target_name}",
                        entity_id=entity_id,
                        related_entity_id=rel.to_entity_id,
                        new_value=rel.relationship_type.value,
                        source_system=rel.source_system,
                        confidence=rel.confidence,
                    )
                )

            if rel.valid_to:
                events.append(
                    TimelineEvent(
                        event_type=EventType.RELATIONSHIP_ENDED,
                        event_date=rel.valid_to,
                        description=f"Relationship ended: {rel.relationship_type.value} to {target_name}",
                        entity_id=entity_id,
                        related_entity_id=rel.to_entity_id,
                        old_value=rel.relationship_type.value,
                    )
                )

        return events

    def _get_listing_events(self, entity_id: str) -> list[TimelineEvent]:
        """Get listing-related timeline events."""
        events = []

        # Get securities for this entity
        securities = self.store.get_securities_by_entity(entity_id)

        for security in securities:
            # Get listings for this security
            listings = self.store.get_listings_by_security(security.security_id)

            for listing in listings:
                if listing.start_date:
                    events.append(
                        TimelineEvent(
                            event_type=EventType.LISTING_ADDED,
                            event_date=listing.start_date,
                            description=f"Listed as {listing.ticker} on {listing.exchange}",
                            entity_id=entity_id,
                            new_value=f"{listing.ticker}:{listing.exchange}",
                            source_system=listing.source_system,
                        )
                    )

                if listing.end_date:
                    events.append(
                        TimelineEvent(
                            event_type=EventType.LISTING_REMOVED,
                            event_date=listing.end_date,
                            description=f"Delisted {listing.ticker} from {listing.exchange}",
                            entity_id=entity_id,
                            old_value=f"{listing.ticker}:{listing.exchange}",
                        )
                    )

        return events

    def _get_identifier_events(self, entity_id: str) -> list[TimelineEvent]:
        """Get identifier-related timeline events."""
        events = []

        claims = self.store.get_claims_for_entity(entity_id)

        for claim in claims:
            if claim.valid_from:
                events.append(
                    TimelineEvent(
                        event_type=EventType.IDENTIFIER_ADDED,
                        event_date=claim.valid_from,
                        description=f"Identifier added: {claim.scheme.value} = {claim.value}",
                        entity_id=entity_id,
                        new_value=f"{claim.scheme.value}:{claim.value}",
                        source_system=claim.source,
                        confidence=claim.confidence,
                    )
                )

            if claim.valid_to:
                events.append(
                    TimelineEvent(
                        event_type=EventType.IDENTIFIER_REMOVED,
                        event_date=claim.valid_to,
                        description=f"Identifier expired: {claim.scheme.value} = {claim.value}",
                        entity_id=entity_id,
                        old_value=f"{claim.scheme.value}:{claim.value}",
                    )
                )

        return events

    # =========================================================================
    # Point-in-Time Queries
    # =========================================================================

    def get_entity_at(
        self,
        entity_id: str,
        as_of: date,
    ) -> EntitySnapshot | None:
        """
        Get entity state at a specific point in time.

        Args:
            entity_id: Entity to query.
            as_of: Point in time.

        Returns:
            EntitySnapshot with state at that date.
        """
        entity = self.store.get_entity(entity_id)
        if not entity:
            return None

        snapshot = EntitySnapshot(
            entity=entity,
            as_of=as_of,
        )

        # Get identifiers valid at that date
        claims = self.store.get_claims_for_entity(entity_id)
        for claim in claims:
            if claim.valid_from and claim.valid_from > as_of:
                continue
            if claim.valid_to and claim.valid_to < as_of:
                continue
            snapshot.identifiers[claim.scheme.value] = claim.value

        # Get listings valid at that date
        securities = self.store.get_securities_by_entity(entity_id)
        for security in securities:
            listings = self.store.get_listings_by_security(security.security_id)
            for listing in listings:
                if listing.start_date and listing.start_date > as_of:
                    continue
                if listing.end_date and listing.end_date < as_of:
                    continue
                snapshot.listings.append(listing)

        # Get officers at that date
        roles = self.store.get_role_assignments(org_entity_id=entity_id, current_only=False)
        for role in roles:
            if role.start_date and role.start_date > as_of:
                continue
            if role.end_date and role.end_date < as_of:
                continue
            person = self.store.get_entity(role.person_entity_id)
            if person:
                snapshot.officers.append((person, role.role_type, role.title))

        # Get relationships at that date
        rels = self.store.get_entity_relationships(from_entity_id=entity_id)
        for rel in rels:
            if rel.valid_from and rel.valid_from > as_of:
                continue
            if rel.valid_to and rel.valid_to < as_of:
                continue
            snapshot.relationships.append(rel)

        return snapshot

    # =========================================================================
    # Comparison
    # =========================================================================

    def compare_states(
        self,
        entity_id: str,
        from_date: date,
        to_date: date,
    ) -> StateDiff:
        """
        Compare entity state between two dates.

        Args:
            entity_id: Entity to compare.
            from_date: Earlier date.
            to_date: Later date.

        Returns:
            StateDiff showing changes.
        """
        snapshot_from = self.get_entity_at(entity_id, from_date)
        snapshot_to = self.get_entity_at(entity_id, to_date)

        diff = StateDiff(
            entity_id=entity_id,
            from_date=from_date,
            to_date=to_date,
        )

        if not snapshot_from or not snapshot_to:
            return diff

        # Compare names
        if snapshot_from.entity.primary_name != snapshot_to.entity.primary_name:
            diff.name_changes.append(
                (snapshot_from.entity.primary_name, snapshot_to.entity.primary_name)
            )

        # Compare identifiers
        from_ids = set(snapshot_from.identifiers.items())
        to_ids = set(snapshot_to.identifiers.items())

        for scheme, value in to_ids - from_ids:
            diff.identifier_added.append((scheme, value))
        for scheme, value in from_ids - to_ids:
            diff.identifier_removed.append((scheme, value))

        # Compare officers
        from_officers = {(o[0].entity_id, o[1]) for o in snapshot_from.officers}
        to_officers = {(o[0].entity_id, o[1]) for o in snapshot_to.officers}

        for person_id, role in to_officers - from_officers:
            person = self.store.get_entity(person_id)
            if person:
                diff.officers_added.append((person, role))

        for person_id, role in from_officers - to_officers:
            person = self.store.get_entity(person_id)
            if person:
                diff.officers_removed.append((person, role))

        # Compare listings
        from_listings = {l.listing_id for l in snapshot_from.listings}
        to_listings = {l.listing_id for l in snapshot_to.listings}

        for listing in snapshot_to.listings:
            if listing.listing_id not in from_listings:
                diff.listings_added.append(listing)

        for listing in snapshot_from.listings:
            if listing.listing_id not in to_listings:
                diff.listings_removed.append(listing)

        return diff

    # =========================================================================
    # Specific Change Queries
    # =========================================================================

    def get_name_changes(
        self,
        entity_id: str,
    ) -> list[TimelineEvent]:
        """Get all name changes for an entity."""
        return self.get_entity_timeline(
            entity_id,
            event_types=[EventType.NAME_CHANGED],
        )

    def get_officer_changes(
        self,
        entity_id: str,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[TimelineEvent]:
        """Get all officer appointment/departure events."""
        return self.get_entity_timeline(
            entity_id,
            start_date=start_date,
            end_date=end_date,
            event_types=[EventType.OFFICER_APPOINTED, EventType.OFFICER_DEPARTED],
        )

    def get_listing_changes(
        self,
        entity_id: str,
    ) -> list[TimelineEvent]:
        """Get all listing changes."""
        return self.get_entity_timeline(
            entity_id,
            event_types=[
                EventType.LISTING_ADDED,
                EventType.LISTING_REMOVED,
                EventType.TICKER_CHANGED,
            ],
        )

    # =========================================================================
    # Analysis
    # =========================================================================

    def get_entity_age(self, entity_id: str) -> int | None:
        """Get entity age in days since creation."""
        entity = self.store.get_entity(entity_id)
        if not entity:
            return None

        created = (
            entity.created_at.date()
            if isinstance(entity.created_at, datetime)
            else entity.created_at
        )
        return (date.today() - created).days  # type: ignore

    def get_activity_summary(
        self,
        entity_id: str,
        *,
        period_days: int = 365,
    ) -> dict[str, int]:
        """
        Get summary of entity activity over a period.

        Returns:
            Dict mapping event_type to count.
        """
        end_date = date.today()
        from datetime import timedelta

        start_date = end_date - timedelta(days=period_days)

        events = self.get_entity_timeline(
            entity_id,
            start_date=start_date,
            end_date=end_date,
        )

        summary: dict[str, int] = {}
        for event in events:
            key = event.event_type.value
            summary[key] = summary.get(key, 0) + 1

        return summary
