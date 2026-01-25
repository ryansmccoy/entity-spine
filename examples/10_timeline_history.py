#!/usr/bin/env python3
"""
EntitySpine - Historical Timeline Example

Demonstrates tracking entity changes over time using real corporate history.

This example shows:
1. Building corporate timelines from SEC filings
2. Officer appointment/departure tracking
3. Corporate structure changes (mergers, spin-offs)
4. Point-in-time queries
5. Comparing entity states across time

Run: python examples/10_timeline_history.py
"""

from __future__ import annotations

import sys
import tempfile
from datetime import date
from pathlib import Path

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from entityspine import (
    EntityType,
    create_entity,
    SqliteStore,
)
from entityspine.core.ulid import generate_ulid
from entityspine.domain.enums import RelationshipType, RoleType
from entityspine.domain.graph import EntityRelationship, RoleAssignment
from entityspine.services.timeline import TimelineService, TimelineEventType


def print_header(title: str) -> None:
    """Print a formatted section header."""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}")


def print_subheader(title: str) -> None:
    """Print a subsection header."""
    print(f"\n  --- {title} ---\n")


def setup_historical_data(store: SqliteStore) -> dict[str, str]:
    """
    Create historical corporate data for demonstration.
    
    This simulates the kind of data extracted from SEC filings
    over many years, showing:
    - Corporate name changes
    - Leadership transitions  
    - Mergers and acquisitions
    - Spin-offs
    
    Returns:
        Dict mapping friendly names to entity IDs.
    """
    print("  Setting up historical corporate data...\n")
    
    entities = {}
    
    # Meta/Facebook - shows a major rebrand
    meta = create_entity(
        primary_name="Meta Platforms, Inc.",
        entity_type=EntityType.ORGANIZATION,
        source_system="sec_edgar",
        source_id="0001326801",
    )
    store.save_entity(meta)
    entities["meta"] = meta.entity_id
    
    # Create person entities for executives
    zuckerberg = create_entity(
        primary_name="Mark Zuckerberg",
        entity_type=EntityType.PERSON,
        source_system="sec_def14a",
    )
    store.save_entity(zuckerberg)
    entities["zuckerberg"] = zuckerberg.entity_id
    
    sandberg = create_entity(
        primary_name="Sheryl Sandberg",
        entity_type=EntityType.PERSON,
        source_system="sec_def14a",
    )
    store.save_entity(sandberg)
    entities["sandberg"] = sandberg.entity_id
    
    olivan = create_entity(
        primary_name="Javier Olivan",
        entity_type=EntityType.PERSON,
        source_system="sec_def14a",
    )
    store.save_entity(olivan)
    entities["olivan"] = olivan.entity_id
    
    # Add role assignments with dates
    # Zuckerberg - CEO since founding
    zuck_ceo = RoleAssignment(
        
        org_entity_id=meta.entity_id,
        person_entity_id=zuckerberg.entity_id,
        role_type=RoleType.CEO,
        title="Chief Executive Officer",
        start_date=date(2004, 2, 4),  # Facebook founding
        source_system="sec_def14a",
        source_ref="DEF 14A 2024",
        confidence=1.0,
    )
    store.save_role_assignment(zuck_ceo)
    
    # Sandberg - COO from 2008 to 2022
    sandberg_coo = RoleAssignment(
        
        org_entity_id=meta.entity_id,
        person_entity_id=sandberg.entity_id,
        role_type=RoleType.COO,
        title="Chief Operating Officer",
        start_date=date(2008, 3, 24),
        end_date=date(2022, 8, 1),  # Departed
        source_system="sec_def14a",
        source_ref="DEF 14A 2022",
        confidence=1.0,
    )
    store.save_role_assignment(sandberg_coo)
    
    # Olivan - COO from 2022
    olivan_coo = RoleAssignment(
        
        org_entity_id=meta.entity_id,
        person_entity_id=olivan.entity_id,
        role_type=RoleType.COO,
        title="Chief Operating Officer",
        start_date=date(2022, 8, 1),
        source_system="sec_def14a",
        source_ref="DEF 14A 2023",
        confidence=1.0,
    )
    store.save_role_assignment(olivan_coo)
    
    # -------------------------------------------------------------------
    # AT&T - shows a major spin-off (Warner Bros Discovery)
    # -------------------------------------------------------------------
    att = create_entity(
        primary_name="AT&T Inc.",
        entity_type=EntityType.ORGANIZATION,
        source_system="sec_edgar",
        source_id="0000732717",
    )
    store.save_entity(att)
    entities["att"] = att.entity_id
    
    warner = create_entity(
        primary_name="Warner Bros. Discovery, Inc.",
        entity_type=EntityType.ORGANIZATION,
        source_system="sec_edgar",
        source_id="0001437107",
    )
    store.save_entity(warner)
    entities["warner"] = warner.entity_id
    
    time_warner = create_entity(
        primary_name="Time Warner Inc.",
        entity_type=EntityType.ORGANIZATION,
        source_system="sec_edgar",
    )
    store.save_entity(time_warner)
    entities["time_warner"] = time_warner.entity_id
    
    # AT&T acquired Time Warner in 2018 (AT&T ACQUIRED Time Warner)
    acquisition = EntityRelationship(
        
        from_entity_id=att.entity_id,
        to_entity_id=time_warner.entity_id,
        relationship_type=RelationshipType.ACQUIRED,
        valid_from=date(2018, 6, 15),
        valid_to=date(2022, 4, 8),  # Until spin-off
        source_system="sec_8k",
        source_ref="Form 8-K 2018-06-15",
        confidence=1.0,
    )
    store.save_entity_relationship(acquisition)
    
    # Warner spun off from AT&T in 2022 (Warner is SUCCESSOR to Time Warner)
    spinoff = EntityRelationship(
        
        from_entity_id=warner.entity_id,
        to_entity_id=time_warner.entity_id,
        relationship_type=RelationshipType.SUCCESSOR,
        valid_from=date(2022, 4, 8),
        source_system="sec_8k",
        source_ref="Form 8-K 2022-04-08",
        confidence=1.0,
    )
    store.save_entity_relationship(spinoff)
    
    # -------------------------------------------------------------------
    # Apple - shows CEO transition
    # -------------------------------------------------------------------
    apple = create_entity(
        primary_name="Apple Inc.",
        entity_type=EntityType.ORGANIZATION,
        source_system="sec_edgar",
        source_id="0000320193",
    )
    store.save_entity(apple)
    entities["apple"] = apple.entity_id
    
    jobs = create_entity(
        primary_name="Steve Jobs",
        entity_type=EntityType.PERSON,
        source_system="sec_def14a",
    )
    store.save_entity(jobs)
    entities["jobs"] = jobs.entity_id
    
    cook = create_entity(
        primary_name="Tim Cook",
        entity_type=EntityType.PERSON,
        source_system="sec_def14a",
    )
    store.save_entity(cook)
    entities["cook"] = cook.entity_id
    
    # Jobs - CEO until 2011
    jobs_ceo = RoleAssignment(
        
        org_entity_id=apple.entity_id,
        person_entity_id=jobs.entity_id,
        role_type=RoleType.CEO,
        title="Chief Executive Officer",
        start_date=date(1997, 9, 16),  # Return to Apple
        end_date=date(2011, 8, 24),  # Resigned
        source_system="sec_def14a",
        confidence=1.0,
    )
    store.save_role_assignment(jobs_ceo)
    
    # Cook - CEO from 2011
    cook_ceo = RoleAssignment(
        
        org_entity_id=apple.entity_id,
        person_entity_id=cook.entity_id,
        role_type=RoleType.CEO,
        title="Chief Executive Officer",
        start_date=date(2011, 8, 24),
        source_system="sec_def14a",
        source_ref="DEF 14A 2024",
        confidence=1.0,
    )
    store.save_role_assignment(cook_ceo)
    
    # Cook was also COO before becoming CEO
    cook_coo = RoleAssignment(
        
        org_entity_id=apple.entity_id,
        person_entity_id=cook.entity_id,
        role_type=RoleType.COO,
        title="Chief Operating Officer",
        start_date=date(2007, 1, 1),
        end_date=date(2011, 8, 24),
        source_system="sec_def14a",
        confidence=1.0,
    )
    store.save_role_assignment(cook_coo)
    
    print(f"  Created {len(entities)} entities with historical data\n")
    return entities


def example_1_entity_timeline(timeline: TimelineService, entities: dict) -> None:
    """Show complete timeline for an entity."""
    print_header("Example 1: Complete Entity Timeline")
    
    print_subheader("Meta Platforms (Facebook) Timeline")
    
    events = timeline.get_entity_timeline(entities["meta"])
    
    print("  Date        Event")
    print("  " + "-" * 60)
    
    for event in events:
        event_icon = {
            TimelineEventType.ENTITY_CREATED: "[+]",
            TimelineEventType.OFFICER_APPOINTED: "[*]",
            TimelineEventType.OFFICER_DEPARTED: "[-]",
            TimelineEventType.RELATIONSHIP_ADDED: "[>]",
            TimelineEventType.RELATIONSHIP_ENDED: "[<]",
        }.get(event.event_type, "[ ]")
        
        print(f"  {event.event_date}  {event_icon} {event.description}")
    
    print_subheader("Apple Inc. Timeline")
    
    events = timeline.get_entity_timeline(entities["apple"])
    
    print("  Date        Event")
    print("  " + "-" * 60)
    
    for event in events:
        event_icon = {
            TimelineEventType.ENTITY_CREATED: "[+]",
            TimelineEventType.OFFICER_APPOINTED: "[*]",
            TimelineEventType.OFFICER_DEPARTED: "[-]",
        }.get(event.event_type, "[ ]")
        
        print(f"  {event.event_date}  {event_icon} {event.description}")


def example_2_officer_changes(timeline: TimelineService, entities: dict) -> None:
    """Track officer appointments and departures."""
    print_header("Example 2: Officer Changes Over Time")
    
    print_subheader("Meta Leadership Changes")
    
    # Filter for officer events only
    events = timeline.get_entity_timeline(
        entities["meta"],
        event_types=[TimelineEventType.OFFICER_APPOINTED, TimelineEventType.OFFICER_DEPARTED],
    )
    
    print("  The Meta/Facebook COO transition:\n")
    
    for event in events:
        if event.event_type == TimelineEventType.OFFICER_APPOINTED:
            marker = "APPOINTED"
        else:
            marker = "DEPARTED"
        
        print(f"  {event.event_date}: {marker}")
        print(f"    {event.description}")
        print()
    
    print_subheader("Apple CEO Succession")
    
    events = timeline.get_entity_timeline(
        entities["apple"],
        event_types=[TimelineEventType.OFFICER_APPOINTED, TimelineEventType.OFFICER_DEPARTED],
    )
    
    # Filter for CEO roles
    ceo_events = [e for e in events if "CEO" in e.description or "Chief Executive" in e.description]
    
    print("  Historic CEO transition:\n")
    
    for event in ceo_events:
        if event.event_type == TimelineEventType.OFFICER_APPOINTED:
            marker = "APPOINTED"
        else:
            marker = "DEPARTED"
        
        print(f"  {event.event_date}: {marker}")
        print(f"    {event.description}")
        print()


def example_3_corporate_actions(timeline: TimelineService, entities: dict) -> None:
    """Track mergers, acquisitions, and spin-offs."""
    print_header("Example 3: Corporate Actions")
    
    print_subheader("AT&T / Time Warner / Warner Bros Discovery")
    
    # Get AT&T timeline
    att_events = timeline.get_entity_timeline(
        entities["att"],
        event_types=[TimelineEventType.RELATIONSHIP_ADDED, TimelineEventType.RELATIONSHIP_ENDED],
    )
    
    # Get Time Warner timeline  
    tw_events = timeline.get_entity_timeline(
        entities["time_warner"],
        event_types=[TimelineEventType.RELATIONSHIP_ADDED, TimelineEventType.RELATIONSHIP_ENDED],
    )
    
    # Get Warner Bros Discovery timeline
    wbd_events = timeline.get_entity_timeline(
        entities["warner"],
        event_types=[TimelineEventType.RELATIONSHIP_ADDED, TimelineEventType.RELATIONSHIP_ENDED],
    )
    
    all_events = att_events + tw_events + wbd_events
    all_events.sort(key=lambda e: e.event_date)
    
    print("  Corporate restructuring timeline:\n")
    
    for event in all_events:
        print(f"  {event.event_date}: {event.description}")
        if event.source_ref:
            print(f"    Source: {event.source_ref}")
        print()


def example_4_point_in_time(timeline: TimelineService, entities: dict, store: SqliteStore) -> None:
    """Query entity state at specific points in time."""
    print_header("Example 4: Point-in-Time Queries")
    
    print_subheader("Who was Apple's CEO?")
    
    dates_to_check = [
        date(2000, 1, 1),  # Jobs era
        date(2010, 1, 1),  # Jobs era
        date(2012, 1, 1),  # Cook era
        date(2024, 1, 1),  # Cook era
    ]
    
    print("  Checking CEO at different points in time:\n")
    
    for check_date in dates_to_check:
        # Get all roles for Apple at this date
        roles = store.get_role_assignments(
            org_entity_id=entities["apple"],
            current_only=False,
        )
        
        # Filter to CEO roles active on this date
        ceo_on_date = None
        for role in roles:
            if role.role_type != RoleType.CEO:
                continue
            
            start_ok = role.start_date is None or role.start_date <= check_date
            end_ok = role.end_date is None or role.end_date > check_date
            
            if start_ok and end_ok:
                person = store.get_entity(role.person_entity_id)
                ceo_on_date = person.primary_name if person else "Unknown"
                break
        
        print(f"  {check_date}: {ceo_on_date or 'No CEO found'}")
    
    print_subheader("Meta COO History")
    
    dates_to_check = [
        date(2010, 1, 1),  # Sandberg era
        date(2020, 1, 1),  # Sandberg era
        date(2023, 1, 1),  # Olivan era
    ]
    
    print("  Checking COO at different points in time:\n")
    
    for check_date in dates_to_check:
        roles = store.get_role_assignments(
            org_entity_id=entities["meta"],
            current_only=False,
        )
        
        coo_on_date = None
        for role in roles:
            if role.role_type != RoleType.COO:
                continue
            
            start_ok = role.start_date is None or role.start_date <= check_date
            end_ok = role.end_date is None or role.end_date > check_date
            
            if start_ok and end_ok:
                person = store.get_entity(role.person_entity_id)
                coo_on_date = person.primary_name if person else "Unknown"
                break
        
        print(f"  {check_date}: {coo_on_date or 'No COO found'}")


def example_5_timeline_filtering(timeline: TimelineService, entities: dict) -> None:
    """Filter timeline by date range and event type."""
    print_header("Example 5: Timeline Filtering")
    
    print_subheader("Apple Events Since 2010")
    
    events = timeline.get_entity_timeline(
        entities["apple"],
        start_date=date(2010, 1, 1),
    )
    
    print("  Events from 2010 onwards:\n")
    
    for event in events:
        print(f"  {event.event_date}: {event.description}")
    
    print_subheader("Meta Appointments Only")
    
    events = timeline.get_entity_timeline(
        entities["meta"],
        event_types=[TimelineEventType.OFFICER_APPOINTED],
    )
    
    print("  Officer appointments only:\n")
    
    for event in events:
        print(f"  {event.event_date}: {event.description}")
    
    print_subheader("Events in a Specific Year (2022)")
    
    events = timeline.get_entity_timeline(
        entities["meta"],
        start_date=date(2022, 1, 1),
        end_date=date(2022, 12, 31),
    )
    
    print("  2022 events for Meta:\n")
    
    for event in events:
        print(f"  {event.event_date}: {event.description}")


def main() -> None:
    """Run all timeline examples."""
    print("\n" + "=" * 70)
    print("  EntitySpine - Historical Timeline Tracking")
    print("  Demonstrating temporal queries on entity history")
    print("=" * 70)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "timeline_demo.db"
        store = SqliteStore(db_path)
        store.initialize()
        
        timeline = TimelineService(store)
        
        print_header("Setup: Creating Historical Data")
        entities = setup_historical_data(store)
        
        # Run examples
        example_1_entity_timeline(timeline, entities)
        example_2_officer_changes(timeline, entities)
        example_3_corporate_actions(timeline, entities)
        example_4_point_in_time(timeline, entities, store)
        example_5_timeline_filtering(timeline, entities)
        
        store.close()
    
    print_header("Summary")
    print("""
  Key Takeaways:

  1. EVENT-SOURCED: Entity history is tracked as a series of events,
     enabling complete audit trails and temporal queries.

  2. POINT-IN-TIME: Query entity state at any historical date to
     answer "who was CEO in 2010?" type questions.

  3. CORPORATE ACTIONS: Track complex corporate events like mergers,
     acquisitions, and spin-offs with date precision.

  4. FLEXIBLE FILTERING: Filter timelines by date range and event
     type to focus on specific aspects of history.

  5. SOURCE TRACKING: Every event can reference its source document
     (8-K, DEF 14A, etc.) for provenance tracking.
""")


if __name__ == "__main__":
    main()
