#!/usr/bin/env python3
"""
Corporate Hierarchy and Knowledge Graph Example

This example demonstrates EntitySpine's graph traversal capabilities for
exploring corporate structures:

1. Parent-subsidiary relationships
2. Officer/executive relationships  
3. Cross-company connections (shared board members)
4. Network analysis around a company

Real-world use case: SEC Form 10-K requires disclosure of subsidiaries.
Form DEF 14A discloses executives and directors. This data creates a
corporate knowledge graph that EntitySpine can traverse.

Run: python examples/08_corporate_hierarchy.py
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

# Add entityspine to path for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from entityspine import (
    SqliteStore,
    GraphService,
    create_entity,
    EntityType,
)
from entityspine.domain.enums import RelationshipType, RoleType
from entityspine.domain.graph import EntityRelationship, RoleAssignment
from entityspine.core.ulid import generate_ulid


def print_header(title: str) -> None:
    """Print a formatted section header."""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print('=' * 70)


def setup_corporate_data(store: SqliteStore) -> dict[str, str]:
    """
    Set up a realistic corporate structure based on real SEC disclosures.
    
    Returns mapping of company names to entity IDs for easy reference.
    """
    entities = {}
    
    # ==========================================================================
    # Create Parent Companies (from SEC filings)
    # ==========================================================================
    
    # Alphabet Inc. - Parent of Google (real structure from 10-K)
    alphabet = create_entity(
        primary_name="Alphabet Inc.",
        entity_type=EntityType.ORGANIZATION,
        source_system="sec",
        source_id="0001652044",
    )
    store.save_entity(alphabet)
    entities["Alphabet"] = alphabet.entity_id
    
    # Google LLC - Subsidiary of Alphabet
    google = create_entity(
        primary_name="Google LLC",
        entity_type=EntityType.ORGANIZATION,
        source_system="sec",
        source_id="google_llc",
    )
    store.save_entity(google)
    entities["Google"] = google.entity_id
    
    # YouTube LLC - Subsidiary of Google
    youtube = create_entity(
        primary_name="YouTube LLC",
        entity_type=EntityType.ORGANIZATION,
        source_system="sec",
        source_id="youtube_llc",
    )
    store.save_entity(youtube)
    entities["YouTube"] = youtube.entity_id
    
    # Waymo LLC - Subsidiary of Alphabet
    waymo = create_entity(
        primary_name="Waymo LLC",
        entity_type=EntityType.ORGANIZATION,
        source_system="sec",
        source_id="waymo_llc",
    )
    store.save_entity(waymo)
    entities["Waymo"] = waymo.entity_id
    
    # Verily Life Sciences LLC - Subsidiary of Alphabet
    verily = create_entity(
        primary_name="Verily Life Sciences LLC",
        entity_type=EntityType.ORGANIZATION,
        source_system="sec",
        source_id="verily_llc",
    )
    store.save_entity(verily)
    entities["Verily"] = verily.entity_id
    
    # ==========================================================================
    # Berkshire Hathaway Structure (real from 10-K)
    # ==========================================================================
    
    berkshire = create_entity(
        primary_name="Berkshire Hathaway Inc.",
        entity_type=EntityType.ORGANIZATION,
        source_system="sec",
        source_id="0001067983",
    )
    store.save_entity(berkshire)
    entities["Berkshire"] = berkshire.entity_id
    
    geico = create_entity(
        primary_name="GEICO Corporation",
        entity_type=EntityType.ORGANIZATION,
        source_system="sec",
        source_id="geico_corp",
    )
    store.save_entity(geico)
    entities["GEICO"] = geico.entity_id
    
    bnsf = create_entity(
        primary_name="BNSF Railway Company",
        entity_type=EntityType.ORGANIZATION,
        source_system="sec",
        source_id="bnsf_railway",
    )
    store.save_entity(bnsf)
    entities["BNSF"] = bnsf.entity_id
    
    sees_candies = create_entity(
        primary_name="See's Candies, Inc.",
        entity_type=EntityType.ORGANIZATION,
        source_system="sec",
        source_id="sees_candies",
    )
    store.save_entity(sees_candies)
    entities["Sees"] = sees_candies.entity_id
    
    dairy_queen = create_entity(
        primary_name="Dairy Queen Corporation",
        entity_type=EntityType.ORGANIZATION,
        source_system="sec",
        source_id="dairy_queen",
    )
    store.save_entity(dairy_queen)
    entities["DairyQueen"] = dairy_queen.entity_id
    
    # ==========================================================================
    # Create Executive Persons (from DEF 14A)
    # ==========================================================================
    
    # Alphabet/Google executives
    sundar = create_entity(
        primary_name="Sundar Pichai",
        entity_type=EntityType.PERSON,
        source_system="sec",
        source_id="sundar_pichai",
    )
    store.save_entity(sundar)
    entities["Sundar"] = sundar.entity_id
    
    ruth = create_entity(
        primary_name="Ruth Porat",
        entity_type=EntityType.PERSON,
        source_system="sec",
        source_id="ruth_porat",
    )
    store.save_entity(ruth)
    entities["Ruth"] = ruth.entity_id
    
    # Berkshire executives
    warren = create_entity(
        primary_name="Warren E. Buffett",
        entity_type=EntityType.PERSON,
        source_system="sec",
        source_id="warren_buffett",
    )
    store.save_entity(warren)
    entities["Warren"] = warren.entity_id
    
    charlie = create_entity(
        primary_name="Charles T. Munger",  # Historical - passed Dec 2023
        entity_type=EntityType.PERSON,
        source_system="sec",
        source_id="charlie_munger",
    )
    store.save_entity(charlie)
    entities["Charlie"] = charlie.entity_id
    
    ajit = create_entity(
        primary_name="Ajit Jain",
        entity_type=EntityType.PERSON,
        source_system="sec",
        source_id="ajit_jain",
    )
    store.save_entity(ajit)
    entities["Ajit"] = ajit.entity_id
    
    greg = create_entity(
        primary_name="Greg Abel",
        entity_type=EntityType.PERSON,
        source_system="sec",
        source_id="greg_abel",
    )
    store.save_entity(greg)
    entities["Greg"] = greg.entity_id
    
    # ==========================================================================
    # Create Subsidiary Relationships
    # ==========================================================================
    
    # Alphabet structure
    store.save_entity_relationship(EntityRelationship(
        from_entity_id=alphabet.entity_id,
        to_entity_id=google.entity_id,
        relationship_type=RelationshipType.SUBSIDIARY,
        valid_from=date(2015, 10, 2),  # Alphabet restructuring
        source_system="sec_10k",
    ))
    
    store.save_entity_relationship(EntityRelationship(
        from_entity_id=google.entity_id,
        to_entity_id=youtube.entity_id,
        relationship_type=RelationshipType.SUBSIDIARY,
        valid_from=date(2006, 10, 9),  # YouTube acquisition
        source_system="sec_10k",
    ))
    
    store.save_entity_relationship(EntityRelationship(
        from_entity_id=alphabet.entity_id,
        to_entity_id=waymo.entity_id,
        relationship_type=RelationshipType.SUBSIDIARY,
        valid_from=date(2016, 12, 13),  # Waymo spin-off
        source_system="sec_10k",
    ))
    
    store.save_entity_relationship(EntityRelationship(
        from_entity_id=alphabet.entity_id,
        to_entity_id=verily.entity_id,
        relationship_type=RelationshipType.SUBSIDIARY,
        valid_from=date(2015, 8, 10),
        source_system="sec_10k",
    ))
    
    # Berkshire structure
    store.save_entity_relationship(EntityRelationship(
        from_entity_id=berkshire.entity_id,
        to_entity_id=geico.entity_id,
        relationship_type=RelationshipType.SUBSIDIARY,
        valid_from=date(1996, 1, 1),  # Geico acquisition completed
        source_system="sec_10k",
    ))
    
    store.save_entity_relationship(EntityRelationship(
        from_entity_id=berkshire.entity_id,
        to_entity_id=bnsf.entity_id,
        relationship_type=RelationshipType.SUBSIDIARY,
        valid_from=date(2010, 2, 12),  # BNSF acquisition
        source_system="sec_10k",
    ))
    
    store.save_entity_relationship(EntityRelationship(
        from_entity_id=berkshire.entity_id,
        to_entity_id=sees_candies.entity_id,
        relationship_type=RelationshipType.SUBSIDIARY,
        valid_from=date(1972, 1, 1),  # Classic Buffett acquisition
        source_system="sec_10k",
    ))
    
    store.save_entity_relationship(EntityRelationship(
        from_entity_id=berkshire.entity_id,
        to_entity_id=dairy_queen.entity_id,
        relationship_type=RelationshipType.SUBSIDIARY,
        valid_from=date(1998, 1, 1),
        source_system="sec_10k",
    ))
    
    # ==========================================================================
    # Create Role Assignments (Officer/Director roles from DEF 14A)
    # ==========================================================================
    
    # Sundar Pichai - CEO of Alphabet and Google
    store.save_role_assignment(RoleAssignment(
        person_entity_id=sundar.entity_id,
        org_entity_id=alphabet.entity_id,
        role_type=RoleType.CEO,
        title="Chief Executive Officer",
        start_date=date(2019, 12, 3),  # Took over from Larry Page
        source_system="sec_def14a",
    ))
    
    store.save_role_assignment(RoleAssignment(
        person_entity_id=sundar.entity_id,
        org_entity_id=google.entity_id,
        role_type=RoleType.CEO,
        title="Chief Executive Officer",
        start_date=date(2015, 8, 10),  # Became Google CEO
        source_system="sec_def14a",
    ))
    
    # Ruth Porat - CFO
    store.save_role_assignment(RoleAssignment(
        person_entity_id=ruth.entity_id,
        org_entity_id=alphabet.entity_id,
        role_type=RoleType.CFO,
        title="Chief Financial Officer",
        start_date=date(2015, 5, 26),
        source_system="sec_def14a",
    ))
    
    # Warren Buffett - Chairman and CEO of Berkshire
    store.save_role_assignment(RoleAssignment(
        person_entity_id=warren.entity_id,
        org_entity_id=berkshire.entity_id,
        role_type=RoleType.CEO,
        title="Chairman and Chief Executive Officer",
        start_date=date(1970, 1, 1),
        source_system="sec_def14a",
    ))
    
    store.save_role_assignment(RoleAssignment(
        person_entity_id=warren.entity_id,
        org_entity_id=berkshire.entity_id,
        role_type=RoleType.CHAIR,
        title="Chairman of the Board",
        start_date=date(1970, 1, 1),
        source_system="sec_def14a",
    ))
    
    # Charlie Munger - Vice Chairman (historical)
    store.save_role_assignment(RoleAssignment(
        person_entity_id=charlie.entity_id,
        org_entity_id=berkshire.entity_id,
        role_type=RoleType.VICE_CHAIR,
        title="Vice Chairman",
        start_date=date(1978, 1, 1),
        end_date=date(2023, 11, 28),  # Passed away
        source_system="sec_def14a",
    ))
    
    # Ajit Jain - Insurance Operations
    store.save_role_assignment(RoleAssignment(
        person_entity_id=ajit.entity_id,
        org_entity_id=berkshire.entity_id,
        role_type=RoleType.EVP,
        title="Vice Chairman - Insurance Operations",
        start_date=date(2018, 1, 1),
        source_system="sec_def14a",
    ))
    
    # Greg Abel - Non-Insurance Operations (successor designate)
    store.save_role_assignment(RoleAssignment(
        person_entity_id=greg.entity_id,
        org_entity_id=berkshire.entity_id,
        role_type=RoleType.EVP,
        title="Vice Chairman - Non-Insurance Operations",
        start_date=date(2018, 1, 1),
        source_system="sec_def14a",
    ))
    
    print(f"  Created {len(entities)} entities with relationships and roles")
    return entities


def example_1_subsidiary_traversal(graph: GraphService, entities: dict) -> None:
    """Traverse subsidiary relationships."""
    print_header("Example 1: Subsidiary Traversal")
    
    print("\n  Alphabet Inc. Corporate Structure:\n")
    
    # Get direct subsidiaries
    subs = graph.get_subsidiaries(entities["Alphabet"])
    print(f"  Direct Subsidiaries of Alphabet ({len(subs)}):")
    for sub in subs:
        print(f"    - {sub.entity.primary_name}")
        if sub.relationship and sub.relationship.valid_from:
            print(f"      (since {sub.relationship.valid_from})")
    
    # Get all subsidiaries including indirect
    print("\n  All Subsidiaries (including indirect):")
    all_subs = graph.get_subsidiaries(entities["Alphabet"], include_indirect=True, max_depth=3)
    for sub in all_subs:
        indent = "  " * (sub.depth + 1)
        print(f"  {indent}- {sub.entity.primary_name} (depth: {sub.depth})")


def example_2_berkshire_structure(graph: GraphService, entities: dict) -> None:
    """Explore Berkshire Hathaway's structure."""
    print_header("Example 2: Berkshire Hathaway Conglomerate")
    
    print("\n  Berkshire Hathaway Subsidiaries:\n")
    
    subs = graph.get_subsidiaries(entities["Berkshire"])
    print(f"  Direct Subsidiaries ({len(subs)}):")
    for sub in subs:
        print(f"    - {sub.entity.primary_name}")
        if sub.relationship:
            print(f"      Acquired: {sub.relationship.valid_from}")


def example_3_executive_roles(graph: GraphService, entities: dict) -> None:
    """Explore officer/executive relationships."""
    print_header("Example 3: Executive Roles from DEF 14A")
    
    print("\n  Alphabet Inc. Leadership:\n")
    officers = graph.get_officers(entities["Alphabet"])
    
    for officer in officers:
        status = "[Current]" if officer.is_current else "[Former]"
        print(f"  {status} {officer.person.primary_name}")
        print(f"          Role: {officer.title or officer.role_type.value}")
        if officer.start_date:
            print(f"          Since: {officer.start_date}")
        print()
    
    print("\n  Berkshire Hathaway Leadership:\n")
    officers = graph.get_officers(entities["Berkshire"])
    
    for officer in officers:
        status = "[Current]" if officer.is_current else "[Former]"
        print(f"  {status} {officer.person.primary_name}")
        print(f"          Role: {officer.title or officer.role_type.value}")
        if officer.start_date:
            print(f"          Since: {officer.start_date}")
        if officer.end_date:
            print(f"          Until: {officer.end_date}")
        print()


def example_4_person_roles(graph: GraphService, entities: dict) -> None:
    """Find all roles for a specific person."""
    print_header("Example 4: Person's Roles Across Companies")
    
    print("\n  Sundar Pichai's Roles:\n")
    
    roles = graph.get_person_roles(entities["Sundar"])
    for company, officer_info in roles:
        status = "[Current]" if officer_info.is_current else "[Former]"
        print(f"  {status} {company.primary_name}")
        print(f"          Title: {officer_info.title or officer_info.role_type.value}")
        if officer_info.start_date:
            print(f"          Since: {officer_info.start_date}")
        print()
    
    print("\n  Warren Buffett's Roles:\n")
    roles = graph.get_person_roles(entities["Warren"])
    for company, officer_info in roles:
        status = "[Current]" if officer_info.is_current else "[Former]"
        print(f"  {status} {company.primary_name}")
        print(f"          Title: {officer_info.title or officer_info.role_type.value}")
        if officer_info.start_date:
            duration = date.today().year - officer_info.start_date.year
            print(f"          Since: {officer_info.start_date} ({duration}+ years!)")
        print()


def example_5_network_analysis(graph: GraphService, entities: dict) -> None:
    """Analyze entity networks."""
    print_header("Example 5: Entity Network Analysis")
    
    print("\n  Network around Alphabet Inc. (depth=2):\n")
    
    network = graph.get_entity_network(entities["Alphabet"], max_depth=2)
    
    print(f"  Center: {network.center.primary_name}")
    print(f"  Total Nodes: {network.node_count}")
    print(f"  Total Edges: {network.edge_count}")
    
    print("\n  Entities by depth:")
    for depth in range(3):
        at_depth = network.entities_at_depth(depth)
        if at_depth:
            print(f"    Depth {depth}: {len(at_depth)} entities")
            for entity in at_depth[:5]:  # Show first 5
                print(f"      - {entity.primary_name}")


def example_6_find_path(graph: GraphService, entities: dict) -> None:
    """Find paths between entities."""
    print_header("Example 6: Finding Paths Between Entities")
    
    print("\n  Path from YouTube to Alphabet:\n")
    
    path = graph.find_path(entities["YouTube"], entities["Alphabet"])
    
    if path.found:
        print(f"  Found path with {path.total_distance} step(s):")
        print(f"  Start: {path.source.primary_name}")
        for step in path.steps:
            rel_type = step.relationship_type if step.relationship_type else "?"
            print(f"    --[{rel_type}]-->")
            print(f"  {step.entity.primary_name}")
    else:
        print("  No path found")
    
    print("\n  Path from GEICO to Berkshire:\n")
    
    path = graph.find_path(entities["GEICO"], entities["Berkshire"])
    
    if path.found:
        print(f"  Found path with {path.total_distance} step(s):")
        print(f"  Start: {path.source.primary_name}")
        for step in path.steps:
            rel_type = step.relationship_type if step.relationship_type else "?"
            print(f"    --[{rel_type}]-->")
            print(f"  {step.entity.primary_name}")


def main():
    """Run all corporate hierarchy examples."""
    print("\n" + "=" * 70)
    print("  EntitySpine - Corporate Hierarchy & Knowledge Graph")
    print("  Demonstrating graph traversal with real corporate structures")
    print("=" * 70)
    
    # Create an in-memory SQLite store
    store = SqliteStore(":memory:")
    store.initialize()
    
    print("\nSetting up corporate data...")
    entities = setup_corporate_data(store)
    
    # Create graph service
    graph = GraphService(store)
    
    # Run examples
    example_1_subsidiary_traversal(graph, entities)
    example_2_berkshire_structure(graph, entities)
    example_3_executive_roles(graph, entities)
    example_4_person_roles(graph, entities)
    example_5_network_analysis(graph, entities)
    example_6_find_path(graph, entities)
    
    print_header("Summary")
    print(f"\n  Total entities: {store.entity_count()}")
    print(f"  Relationships traversed successfully!")
    print("\n  The corporate knowledge graph is now queryable.\n")


if __name__ == "__main__":
    main()
