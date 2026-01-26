"""
04_knowledge_graph_relationships.py

Build a knowledge graph from SEC filings with relationships.

This example demonstrates:
- Creating organization and person entities
- Linking entities with typed relationships
- Using evidence from SEC filings
"""

from __future__ import annotations

from entityspine import (
    Entity,
    EntityStatus,
    EntityType,
    SqliteStore,
)
from entityspine.domain.graph import (
    NodeKind,
    NodeRef,
    Person,
    Relationship,
    RelationshipType,
    RoleAssignment,
    RoleType,
)


def main() -> None:
    """Build a knowledge graph from NVIDIA's 10-K."""
    store = SqliteStore(":memory:")
    store.initialize()

    print("=" * 60)
    print("KNOWLEDGE GRAPH EXAMPLE: NVIDIA 10-K")
    print("=" * 60)

    # ========================================
    # CREATE ENTITIES
    # ========================================

    # NVIDIA (primary filer)
    nvidia = Entity(
        primary_name="NVIDIA Corporation",
        entity_type=EntityType.ORGANIZATION,
        status=EntityStatus.ACTIVE,
        jurisdiction="DE",
        sic_code="3674",  # Semiconductors
        source_system="sec-edgar",
        source_id="0001045810",
    )
    store.save_entity(nvidia)
    print(f"\nCreated: {nvidia.primary_name}")

    # CEO
    jensen = Person(
        person_id=None,  # Auto-generated
        full_name="Jensen Huang",
        entity_id=nvidia.entity_id,
        source_system="sec-edgar",
    )
    store.save_person(jensen)
    print(f"Created person: {jensen.full_name}")

    # CFO
    colette = Person(
        person_id=None,
        full_name="Colette Kress",
        entity_id=nvidia.entity_id,
        source_system="sec-edgar",
    )
    store.save_person(colette)
    print(f"Created person: {colette.full_name}")

    # Supplier
    tsmc = Entity(
        primary_name="Taiwan Semiconductor Manufacturing Company",
        entity_type=EntityType.ORGANIZATION,
        source_system="sec-edgar",
    )
    store.save_entity(tsmc)
    print(f"Created: {tsmc.primary_name}")

    # Customer
    microsoft = Entity(
        primary_name="Microsoft Corporation",
        entity_type=EntityType.ORGANIZATION,
        source_system="sec-edgar",
        source_id="0000789019",
    )
    store.save_entity(microsoft)
    print(f"Created: {microsoft.primary_name}")

    # Competitor
    amd = Entity(
        primary_name="Advanced Micro Devices, Inc.",
        entity_type=EntityType.ORGANIZATION,
        source_system="sec-edgar",
        source_id="0000002488",
    )
    store.save_entity(amd)
    print(f"Created: {amd.primary_name}")

    # ========================================
    # CREATE ROLE ASSIGNMENTS
    # ========================================
    print("\n" + "-" * 40)
    print("ROLE ASSIGNMENTS")
    print("-" * 40)

    # Jensen as CEO
    ceo_role = RoleAssignment(
        person_id=jensen.person_id,
        entity_id=nvidia.entity_id,
        role=RoleType.EXECUTIVE,
        title="President and Chief Executive Officer",
        is_primary=True,
        source_system="sec-edgar",
        evidence_filing_id="0001045810-24-000029",
        evidence_snippet="Jensen Huang has served as President and CEO since 1993",
    )
    store.save_role_assignment(ceo_role)
    print(f"  {jensen.full_name} → {ceo_role.title}")

    # Colette as CFO
    cfo_role = RoleAssignment(
        person_id=colette.person_id,
        entity_id=nvidia.entity_id,
        role=RoleType.EXECUTIVE,
        title="Executive Vice President and Chief Financial Officer",
        is_primary=True,
        source_system="sec-edgar",
        evidence_filing_id="0001045810-24-000029",
    )
    store.save_role_assignment(cfo_role)
    print(f"  {colette.full_name} → CFO")

    # ========================================
    # CREATE RELATIONSHIPS
    # ========================================
    print("\n" + "-" * 40)
    print("BUSINESS RELATIONSHIPS")
    print("-" * 40)

    # NVIDIA → TSMC (supplier)
    supplier_rel = Relationship(
        source_ref=NodeRef(NodeKind.ENTITY, nvidia.entity_id),
        target_ref=NodeRef(NodeKind.ENTITY, tsmc.entity_id),
        relationship_type=RelationshipType.SUPPLIER,
        confidence=0.95,
        evidence_filing_id="0001045810-24-000029",
        evidence_snippet="TSMC manufactures substantially all of our GPUs and other chips",
        source_system="sec-edgar",
    )
    store.save_relationship(supplier_rel)
    print(f"  {nvidia.primary_name} → SUPPLIER → {tsmc.primary_name}")

    # NVIDIA → Microsoft (customer)
    customer_rel = Relationship(
        source_ref=NodeRef(NodeKind.ENTITY, nvidia.entity_id),
        target_ref=NodeRef(NodeKind.ENTITY, microsoft.entity_id),
        relationship_type=RelationshipType.CUSTOMER,
        confidence=0.90,
        evidence_filing_id="0001045810-24-000029",
        evidence_snippet="Microsoft Azure is a significant customer for our datacenter products",
        source_system="sec-edgar",
    )
    store.save_relationship(customer_rel)
    print(f"  {nvidia.primary_name} → CUSTOMER → {microsoft.primary_name}")

    # NVIDIA → AMD (competitor)
    competitor_rel = Relationship(
        source_ref=NodeRef(NodeKind.ENTITY, nvidia.entity_id),
        target_ref=NodeRef(NodeKind.ENTITY, amd.entity_id),
        relationship_type=RelationshipType.COMPETITOR,
        confidence=0.95,
        evidence_filing_id="0001045810-24-000029",
        evidence_snippet="We compete with AMD in the GPU and datacenter accelerator markets",
        source_system="sec-edgar",
    )
    store.save_relationship(competitor_rel)
    print(f"  {nvidia.primary_name} → COMPETITOR → {amd.primary_name}")

    # ========================================
    # QUERY THE GRAPH
    # ========================================
    print("\n" + "=" * 60)
    print("GRAPH QUERIES")
    print("=" * 60)

    # Get all relationships for NVIDIA
    print(f"\nAll relationships for {nvidia.primary_name}:")
    relationships = store.get_relationships_for_entity(nvidia.entity_id)
    for rel in relationships:
        # Get target entity
        target_id = rel.target_ref.id
        target = store.get_entity(target_id)
        target_name = target.primary_name if target else "Unknown"
        print(f"  {rel.relationship_type.value} → {target_name}")
        if rel.evidence_snippet:
            print(f"    Evidence: \"{rel.evidence_snippet[:60]}...\"")

    # Get all people for NVIDIA
    print(f"\nExecutives at {nvidia.primary_name}:")
    roles = store.get_roles_for_entity(nvidia.entity_id)
    for role in roles:
        person = store.get_person(role.person_id)
        if person:
            print(f"  {person.full_name}: {role.title}")

    # ========================================
    # STATISTICS
    # ========================================
    print("\n" + "=" * 60)
    print("FINAL STATISTICS")
    print("=" * 60)
    print(f"Entities: {store.entity_count()}")
    print(f"People: {store.person_count()}")
    print(f"Relationships: {store.relationship_count()}")
    print(f"Role Assignments: {store.role_assignment_count()}")


if __name__ == "__main__":
    main()
