#!/usr/bin/env python3
"""
EntitySpine End-to-End Integration Proof: SEC Filing to Knowledge Graph

This example demonstrates that EntitySpine is ready to integrate with
FeedSpine / py-sec-edgar by showing the complete data flow:

1. Tier 1 Setup: Load SEC company tickers into SqliteStore
2. Resolution: Query entities by ticker, CIK, and name
3. Filing Facts Ingestion: Parse mock 10-K payload into KG nodes/edges
4. Tier Honesty: Demonstrate as_of warnings when tier can't honor
5. KG Query: Summarize ingested graph (counts, relationships)

REQUIREMENTS:
- Python 3.10+
- Only entityspine core (no pydantic/sqlmodel required)

USAGE:
    python examples/01_end_to_end_sec_filing_to_kg.py

Author: EntitySpine Team
Version: 2.2.4
"""

from __future__ import annotations

import json
import sys
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Optional

# ============================================================================
# STDLIB-ONLY IMPORTS: This script MUST run with zero external dependencies
# ============================================================================

# EntitySpine Core Domain (stdlib dataclasses)
from entityspine.domain import (
    # Core models
    Entity,
    EntityType,
    EntityStatus,
    Security,
    SecurityType,
    Listing,
    IdentifierClaim,
    IdentifierScheme,
    VendorNamespace,
    # Knowledge Graph models
    Address,
    AddressType,
    Geo,
    GeoType,
    RoleAssignment,
    RoleType,
    Relationship,
    RelationshipType,
    NodeRef,
    NodeKind,
    Asset,
    AssetType,
    AssetStatus,
    Contract,
    ContractType,
    ContractStatus,
    Product,
    ProductType,
    ProductStatus,
    Brand,
    Event,
    EventType,
    EventStatus,
    # Resolution
    ResolutionResult,
    ResolutionStatus,
    ResolutionTier,
    found_result,
    not_found_result,
    # Validators
    normalize_cik,
    compute_address_hash,
)

# EntitySpine Core Store (stdlib sqlite3)
from entityspine.stores import SqliteStore

# Core utilities
from entityspine.core.ulid import generate_ulid
from entityspine.core.timestamps import utc_now


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def print_header(title: str) -> None:
    """Print a formatted section header."""
    print()
    print("=" * 70)
    print(f" {title}")
    print("=" * 70)


def print_subheader(title: str) -> None:
    """Print a formatted subsection header."""
    print()
    print(f"--- {title} ---")


def load_json(path: Path) -> dict:
    """Load JSON file."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ============================================================================
# SECTION A: TIER 1 SETUP + BASIC RESOLUTION
# ============================================================================

def demo_tier1_setup(store: SqliteStore, fixtures_dir: Path) -> str:
    """
    Demonstrate Tier 1 setup: load SEC tickers and perform basic resolution.
    
    Returns the issuer entity_id for subsequent operations.
    """
    print_header("A) TIER 1 SETUP: Load SEC Sample Tickers")
    
    # Load SEC company_tickers sample
    tickers_path = fixtures_dir / "sec_company_tickers_sample.json"
    sec_data = load_json(tickers_path)
    
    # Load into store
    count = store.load_sec_json(sec_data)
    print(f"✓ Loaded {count} entities from SEC JSON")
    print(f"  - Entity count: {store.entity_count()}")
    print(f"  - Security count: {store.security_count()}")
    print(f"  - Listing count: {store.listing_count()}")
    print(f"  - Claim count: {store.claim_count()}")
    
    print_subheader("Basic Resolution Examples")
    
    # Resolve by ticker
    results = store.get_entities_by_ticker("AAPL")
    if results:
        apple = results[0]
        print(f"  resolve('AAPL') → {apple.primary_name} (entity_id={apple.entity_id[:12]}...)")
        issuer_entity_id = apple.entity_id
    else:
        # Should not happen with fixtures
        raise RuntimeError("AAPL not found in fixtures")
    
    # Resolve by CIK
    results = store.get_entities_by_cik("320193")
    if results:
        print(f"  resolve('0000320193') → {results[0].primary_name}")
    
    # Resolve by exact name
    search_results = store.search_entities("Apple Inc.", limit=3)
    if search_results:
        entity, score = search_results[0]
        print(f"  search('Apple Inc.') → {entity.primary_name} (score={score})")
    
    return issuer_entity_id


# ============================================================================
# SECTION B: MOCK FILING FACTS INGESTION
# ============================================================================

def demo_filing_facts_ingestion(
    store: SqliteStore,
    fixtures_dir: Path,
    issuer_entity_id: str,
) -> dict:
    """
    Demonstrate ingesting a mock 10-K filing facts payload into the KG.
    
    Returns a dict of created entity IDs for reference.
    """
    print_header("B) FILING FACTS INGESTION: Mock 10-K → Knowledge Graph")
    
    payload_path = fixtures_dir / "mock_filing_facts_10k.json"
    payload = load_json(payload_path)
    
    created_ids: dict = {
        "issuer_entity_id": issuer_entity_id,
        "person_entity_ids": {},
        "geo_ids": {},
        "address_id": None,
        "role_assignment_ids": [],
        "relationship_ids": [],
        "contract_ids": [],
        "product_ids": [],
        "brand_ids": [],
        "asset_ids": [],
        "event_ids": [],
    }
    
    # -------------------------------------------------------------------------
    # B.1: Create Person Entities (CEO, CFO, Directors)
    # -------------------------------------------------------------------------
    print_subheader("B.1: Creating Person Entities")
    
    for officer in payload.get("officers", []):
        person_id = generate_ulid()
        person = Entity(
            entity_id=person_id,
            primary_name=officer["name"],
            entity_type=EntityType.PERSON,
            status=EntityStatus.ACTIVE,
            source_system="sec_edgar",
            source_id=officer.get("person_id"),
        )
        store.save_entity(person)
        created_ids["person_entity_ids"][officer["person_id"]] = person_id
        print(f"  ✓ Created person: {officer['name']} ({officer['role_type'].upper()})")
    
    for director in payload.get("directors", []):
        person_id = generate_ulid()
        person = Entity(
            entity_id=person_id,
            primary_name=director["name"],
            entity_type=EntityType.PERSON,
            status=EntityStatus.ACTIVE,
            source_system="sec_edgar",
            source_id=director.get("person_id"),
        )
        store.save_entity(person)
        created_ids["person_entity_ids"][director["person_id"]] = person_id
        print(f"  ✓ Created person: {director['name']} ({director['role_type'].upper()})")
    
    # -------------------------------------------------------------------------
    # B.2: Create RoleAssignments (with evidence)
    # -------------------------------------------------------------------------
    print_subheader("B.2: Creating Role Assignments")
    
    filing_id = payload["filing_metadata"]["filing_id"]
    
    for officer in payload.get("officers", []):
        person_entity_id = created_ids["person_entity_ids"][officer["person_id"]]
        role_type = _map_role_type(officer["role_type"])
        
        role = RoleAssignment(
            role_assignment_id=generate_ulid(),
            person_entity_id=person_entity_id,
            org_entity_id=issuer_entity_id,
            role_type=role_type,
            title=officer.get("title"),
            start_date=_parse_date(officer.get("start_date")),
            end_date=_parse_date(officer.get("end_date")),
            confidence=1.0,
            captured_at=utc_now(),
            source_system="sec_edgar",
            source_ref=filing_id,
            filing_id=filing_id,
            section_id=officer.get("evidence", {}).get("section_id"),
            snippet_hash=_hash_snippet(officer.get("evidence", {}).get("snippet")),
        )
        store.save_role_assignment(role)
        created_ids["role_assignment_ids"].append(role.role_assignment_id)
        print(f"  ✓ Role: {officer['name']} → {role_type.value} at {payload['issuer']['name']}")
    
    for director in payload.get("directors", []):
        person_entity_id = created_ids["person_entity_ids"][director["person_id"]]
        role_type = _map_role_type(director["role_type"])
        
        role = RoleAssignment(
            role_assignment_id=generate_ulid(),
            person_entity_id=person_entity_id,
            org_entity_id=issuer_entity_id,
            role_type=role_type,
            title=director.get("title"),
            start_date=_parse_date(director.get("start_date")),
            end_date=_parse_date(director.get("end_date")),
            confidence=1.0,
            captured_at=utc_now(),
            source_system="sec_edgar",
            source_ref=filing_id,
            filing_id=filing_id,
            section_id=director.get("evidence", {}).get("section_id"),
        )
        store.save_role_assignment(role)
        created_ids["role_assignment_ids"].append(role.role_assignment_id)
        print(f"  ✓ Role: {director['name']} → {role_type.value} at {payload['issuer']['name']}")
    
    # -------------------------------------------------------------------------
    # B.3: Create Geo Hierarchy (Country → State → City)
    # -------------------------------------------------------------------------
    print_subheader("B.3: Creating Geographic Hierarchy")
    
    for geo_data in payload.get("geo_hierarchy", []):
        geo = Geo(
            geo_id=geo_data["geo_id"],
            name=geo_data["name"],
            geo_type=GeoType(geo_data["geo_type"]),
            iso_code=geo_data.get("iso_code"),
            parent_geo_id=geo_data.get("parent_geo_id"),
        )
        store.save_geo(geo)
        created_ids["geo_ids"][geo_data["geo_id"]] = geo.geo_id
        parent_info = f" (parent: {geo_data['parent_geo_id']})" if geo_data.get("parent_geo_id") else ""
        print(f"  ✓ Geo: {geo.geo_type.value}/{geo.name}{parent_info}")
    
    # -------------------------------------------------------------------------
    # B.4: Create Address with Hash
    # -------------------------------------------------------------------------
    print_subheader("B.4: Creating Address (with normalized hash)")
    
    hq = payload.get("headquarters", {})
    if hq:
        # Compute address hash for deduplication
        addr_hash = compute_address_hash(
            line1=hq.get("line1", ""),
            line2=hq.get("line2"),  # Required parameter
            city=hq.get("city", ""),
            region=hq.get("region", ""),
            postal=hq.get("postal", ""),
            country=hq.get("country", "US"),
        )
        
        address = Address(
            address_id=generate_ulid(),
            line1=hq.get("line1"),
            line2=hq.get("line2"),
            city=hq.get("city"),
            region=hq.get("region"),
            postal=hq.get("postal"),
            country=hq.get("country", "US"),
            normalized_hash=addr_hash,
        )
        store.save_address(address)
        created_ids["address_id"] = address.address_id
        print(f"  ✓ Address: {address.display}")
        print(f"    Hash: {addr_hash[:16]}...")
        
        # Link address to issuer via EntityAddress
        store.save_entity_address(
            entity_id=issuer_entity_id,
            address_id=address.address_id,
            address_type=AddressType.BUSINESS,
        )
        print(f"  ✓ Linked address to {payload['issuer']['name']}")
    
    # -------------------------------------------------------------------------
    # B.5: Create Contract (Material Agreement)
    # -------------------------------------------------------------------------
    print_subheader("B.5: Creating Material Contract")
    
    for contract_data in payload.get("material_contracts", []):
        contract = Contract(
            contract_id=contract_data["contract_id"],
            title=contract_data["title"],
            contract_type=ContractType(contract_data["contract_type"]),
            effective_date=_parse_date(contract_data.get("effective_date")),
            termination_date=_parse_date(contract_data.get("termination_date")),
            value_usd=Decimal(str(contract_data.get("value_usd"))) if contract_data.get("value_usd") else None,
            status=ContractStatus.ACTIVE,
            filing_id=contract_data.get("evidence", {}).get("filing_id"),
            source_system="sec_edgar",
        )
        store.save_contract(contract)
        created_ids["contract_ids"].append(contract.contract_id)
        print(f"  ✓ Contract: {contract.title}")
        print(f"    Value: ${contract.value_usd:,.0f}" if contract.value_usd else "")
    
    # -------------------------------------------------------------------------
    # B.6: Create Product
    # -------------------------------------------------------------------------
    print_subheader("B.6: Creating Products")
    
    for product_data in payload.get("products", []):
        product = Product(
            product_id=product_data["product_id"],
            name=product_data["name"],
            product_type=ProductType(product_data["product_type"]),
            description=product_data.get("description"),
            owner_entity_id=issuer_entity_id,
            status=ProductStatus(product_data.get("status", "active")),
            source_system="sec_edgar",
        )
        store.save_product(product)
        created_ids["product_ids"].append(product.product_id)
        print(f"  ✓ Product: {product.name} ({product.product_type.value})")
    
    # -------------------------------------------------------------------------
    # B.7: Create Brand
    # -------------------------------------------------------------------------
    print_subheader("B.7: Creating Brands")
    
    for brand_data in payload.get("brands", []):
        brand = Brand(
            brand_id=brand_data["brand_id"],
            name=brand_data["name"],
            owner_entity_id=issuer_entity_id,
            description=brand_data.get("description"),
            source_system="sec_edgar",
        )
        store.save_brand(brand)
        created_ids["brand_ids"].append(brand.brand_id)
        print(f"  ✓ Brand: {brand.name}")
    
    # -------------------------------------------------------------------------
    # B.8: Create Asset (Facility with Geo/Address)
    # -------------------------------------------------------------------------
    print_subheader("B.8: Creating Assets")
    
    for asset_data in payload.get("assets", []):
        # Get geo_id for Cupertino if available
        cupertino_geo_id = created_ids["geo_ids"].get("geo_cupertino")
        
        asset = Asset(
            asset_id=asset_data["asset_id"],
            name=asset_data["name"],
            asset_type=AssetType(asset_data["asset_type"]),
            description=asset_data.get("description"),
            owner_entity_id=issuer_entity_id,
            geo_id=cupertino_geo_id,
            address_id=created_ids["address_id"],  # Link to HQ address
            status=AssetStatus(asset_data.get("status", "active")),
            source_system="sec_edgar",
        )
        store.save_asset(asset)
        created_ids["asset_ids"].append(asset.asset_id)
        print(f"  ✓ Asset: {asset.name} ({asset.asset_type.value})")
        if cupertino_geo_id:
            print(f"    Located in: geo_cupertino")
    
    # -------------------------------------------------------------------------
    # B.9: Create KG Event (Acquisition)
    # -------------------------------------------------------------------------
    print_subheader("B.9: Creating KG Events")
    
    for event_data in payload.get("events", []):
        event = Event(
            event_id=event_data["event_id"],
            event_type=EventType(event_data["event_type"]),
            title=event_data["title"],
            description=event_data.get("description"),
            status=EventStatus(event_data.get("status", "announced")),
            announced_on=_parse_date(event_data.get("announced_on")),
            occurred_on=_parse_date(event_data.get("occurred_on")),
            payload={"related_entities": event_data.get("related_entities", [])},
            evidence_filing_id=event_data.get("evidence", {}).get("filing_id"),
            evidence_section_id=event_data.get("evidence", {}).get("section_id"),
            evidence_snippet=event_data.get("evidence", {}).get("snippet"),
            source_system="sec_edgar",
        )
        store.save_event(event)
        created_ids["event_ids"].append(event.event_id)
        print(f"  ✓ Event: {event.title} ({event.event_type.value})")
        print(f"    Status: {event.status.value}")
    
    # -------------------------------------------------------------------------
    # B.10: Create Relationships
    # -------------------------------------------------------------------------
    print_subheader("B.10: Creating Relationships")
    
    # Create any additional entities needed (SEC, XYZ Labs, NVIDIA)
    additional_entities = _create_additional_entities(store, payload, created_ids)
    
    for rel_data in payload.get("relationships", []):
        rel_type = RelationshipType(rel_data["relationship_type"])
        
        # Resolve source and target NodeRefs
        source_ref = _resolve_node_ref(
            rel_data["source_type"],
            rel_data["source_ref"],
            created_ids,
            issuer_entity_id,
            additional_entities,
        )
        target_ref = _resolve_node_ref(
            rel_data["target_type"],
            rel_data["target_ref"],
            created_ids,
            issuer_entity_id,
            additional_entities,
        )
        
        if source_ref and target_ref:
            relationship = Relationship(
                relationship_id=generate_ulid(),
                source_ref=source_ref,
                target_ref=target_ref,
                relationship_type=rel_type,
                valid_from=_parse_date(rel_data.get("start_date")),
                evidence_filing_id=rel_data.get("evidence", {}).get("filing_id"),
                evidence_snippet=rel_data.get("evidence", {}).get("snippet"),
                source_system="sec_edgar",
                confidence=1.0,
            )
            store.save_relationship(relationship)
            created_ids["relationship_ids"].append(relationship.relationship_id)
            print(f"  ✓ {rel_type.value}: {source_ref} → {target_ref}")
    
    print_subheader("Ingestion Summary")
    print(f"  Entities: +{len(created_ids['person_entity_ids'])} persons")
    print(f"  Geos: {len(created_ids['geo_ids'])}")
    print(f"  Addresses: {'1' if created_ids['address_id'] else '0'}")
    print(f"  Role Assignments: {len(created_ids['role_assignment_ids'])}")
    print(f"  Contracts: {len(created_ids['contract_ids'])}")
    print(f"  Products: {len(created_ids['product_ids'])}")
    print(f"  Brands: {len(created_ids['brand_ids'])}")
    print(f"  Assets: {len(created_ids['asset_ids'])}")
    print(f"  Events: {len(created_ids['event_ids'])}")
    print(f"  Relationships: {len(created_ids['relationship_ids'])}")
    
    return created_ids


# ============================================================================
# SECTION C: TIER HONESTY DEMONSTRATION
# ============================================================================

def demo_tier_honesty(store: SqliteStore) -> None:
    """
    Demonstrate Tier 1 capability honesty: as_of warnings.
    
    Tier 1 (SqliteStore) cannot honor temporal queries - it must warn the caller.
    """
    print_header("C) TIER HONESTY: as_of Parameter Warnings")
    
    # Create a mock resolution with as_of parameter
    old_date = date(2015, 1, 1)
    
    print(f"  Requesting resolution with as_of={old_date}...")
    print()
    
    # Get listings with as_of (will be ignored by Tier 1)
    listings = store.get_listings_by_ticker("AAPL", as_of=old_date)
    
    # The store returns current data but we need to communicate tier limitations
    # In a real resolver, we'd wrap this in ResolutionResult with warnings
    
    # Demonstrate what the resolver would return
    if listings:
        # Build result with tier honesty
        entities = store.get_entities_by_ticker("AAPL")
        if entities:
            result = found_result(
                entity=entities[0],
                query="AAPL",
                tier=ResolutionTier.TIER_1,
                as_of=old_date,
                as_of_honored=False,  # Tier 1 cannot honor as_of
            )
            # Add standard warning
            result.add_as_of_ignored_warning()
            # Set tier limits
            result.set_tier_1_limits()
            
            print("  ResolutionResult:")
            print(f"    Entity: {result.entity.primary_name}")
            print(f"    Tier: {result.tier.value}")
            print(f"    as_of requested: {result.as_of}")
            print(f"    as_of_honored: {result.as_of_honored}")
            print()
            print("  Warnings:")
            for warning in result.warnings:
                print(f"    ⚠ {warning}")
            print()
            print("  Limits:")
            for key, value in result.limits.items():
                print(f"    • {key}: {value}")
    else:
        print("  (No listings found)")


# ============================================================================
# SECTION D: KG QUERY + SUMMARIZE
# ============================================================================

def demo_kg_summary(store: SqliteStore, created_ids: dict, payload: dict) -> None:
    """
    Query and summarize the ingested knowledge graph.
    """
    print_header("D) KNOWLEDGE GRAPH SUMMARY")
    
    # -------------------------------------------------------------------------
    # D.1: Counts per Node Type
    # -------------------------------------------------------------------------
    print_subheader("D.1: Node Counts")
    
    counts = {
        "Entities": store.entity_count(),
        "Securities": store.security_count(),
        "Listings": store.listing_count(),
        "Claims": store.claim_count(),
        "Geos": store.geo_count(),
        "Addresses": store.address_count(),
        "Role Assignments": store.role_assignment_count(),
        "Relationships": store.relationship_count(),
        "Assets": store.asset_count(),
        "Contracts": store.contract_count(),
        "Products": store.product_count(),
        "Brands": store.brand_count(),
        "Events": store.event_count(),
    }
    
    for name, count in counts.items():
        print(f"  {name:20s}: {count:4d}")
    
    # -------------------------------------------------------------------------
    # D.2: List CEO and CFO for Issuer
    # -------------------------------------------------------------------------
    print_subheader("D.2: Executive Officers")
    
    issuer_id = created_ids["issuer_entity_id"]
    roles = store.get_role_assignments_by_org(issuer_id)
    
    for role in roles:
        if role.role_type in (RoleType.CEO, RoleType.CFO):
            person = store.get_entity(role.person_entity_id)
            if person:
                print(f"  {role.role_type.value.upper():5s}: {person.primary_name}")
                if role.title:
                    print(f"        Title: {role.title}")
    
    # -------------------------------------------------------------------------
    # D.3: List Contract Titles for Issuer
    # -------------------------------------------------------------------------
    print_subheader("D.3: Material Contracts")
    
    # Find contracts where issuer is a party (via relationship)
    for contract_id in created_ids.get("contract_ids", []):
        contract = store.get_contract(contract_id)
        if contract:
            print(f"  • {contract.title}")
            if contract.value_usd:
                print(f"    Value: ${contract.value_usd:,.0f}")
    
    # -------------------------------------------------------------------------
    # D.4: List Asset Names for Issuer
    # -------------------------------------------------------------------------
    print_subheader("D.4: Assets")
    
    assets = store.get_assets_by_owner(issuer_id)
    for asset in assets:
        print(f"  • {asset.name} ({asset.asset_type.value})")
    
    # -------------------------------------------------------------------------
    # D.5: Show 5 Relationship Edges Involving Issuer
    # -------------------------------------------------------------------------
    print_subheader("D.5: Relationships (first 5)")
    
    all_rels = store.get_relationships_by_source_id(issuer_id, limit=5)
    for i, rel in enumerate(all_rels[:5], 1):
        print(f"  {i}. {rel.relationship_type.value}")
        print(f"     {rel.source_ref} → {rel.target_ref}")


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _parse_date(date_str: Optional[str]) -> Optional[date]:
    """Parse ISO date string to date object."""
    if not date_str:
        return None
    try:
        return date.fromisoformat(date_str)
    except ValueError:
        return None


def _map_role_type(role_str: str) -> RoleType:
    """Map payload role type string to RoleType enum."""
    mapping = {
        "ceo": RoleType.CEO,
        "cfo": RoleType.CFO,
        "coo": RoleType.COO,
        "cto": RoleType.CTO,
        "director": RoleType.DIRECTOR,
        "chair": RoleType.CHAIR,
        "vice_chair": RoleType.VICE_CHAIR,
        "officer": RoleType.OFFICER,
        "president": RoleType.PRESIDENT,
    }
    return mapping.get(role_str.lower(), RoleType.OTHER)


def _hash_snippet(snippet: Optional[str]) -> Optional[str]:
    """Create a hash of evidence snippet for deduplication."""
    if not snippet:
        return None
    import hashlib
    return hashlib.sha256(snippet.encode()).hexdigest()[:16]


def _create_additional_entities(
    store: SqliteStore,
    payload: dict,
    created_ids: dict,
) -> dict:
    """Create additional entities needed for relationships (SEC, XYZ Labs, etc.)."""
    additional = {}
    
    # Create SEC regulator entity
    sec_id = generate_ulid()
    sec = Entity(
        entity_id=sec_id,
        primary_name="U.S. Securities and Exchange Commission",
        entity_type=EntityType.GOVERNMENT,
        status=EntityStatus.ACTIVE,
        source_system="manual",
        jurisdiction="US",
    )
    store.save_entity(sec)
    additional["sec"] = sec_id
    
    # Create XYZ Labs (acquisition target)
    xyz_id = generate_ulid()
    xyz = Entity(
        entity_id=xyz_id,
        primary_name="XYZ Labs Inc.",
        entity_type=EntityType.ORGANIZATION,
        status=EntityStatus.MERGED,  # Acquired
        source_system="sec_edgar",
    )
    store.save_entity(xyz)
    additional["xyz_labs"] = xyz_id
    
    # Get NVIDIA entity_id if it exists from SEC tickers
    nvidia_results = store.get_entities_by_ticker("NVDA")
    if nvidia_results:
        additional["nvidia"] = nvidia_results[0].entity_id
    
    return additional


def _resolve_node_ref(
    node_type: str,
    ref: str,
    created_ids: dict,
    issuer_entity_id: str,
    additional_entities: dict,
) -> Optional[NodeRef]:
    """Resolve a payload reference to a NodeRef."""
    
    if node_type == "entity":
        if ref == "issuer":
            return NodeRef.entity(issuer_entity_id)
        elif ref in created_ids.get("person_entity_ids", {}):
            return NodeRef.entity(created_ids["person_entity_ids"][ref])
        elif ref in additional_entities:
            return NodeRef.entity(additional_entities[ref])
    elif node_type == "geo":
        if ref in created_ids.get("geo_ids", {}):
            return NodeRef.geo(created_ids["geo_ids"][ref])
    elif node_type == "contract":
        if ref in created_ids.get("contract_ids", []):
            return NodeRef.contract(ref)
        # Also check by ID directly
        for cid in created_ids.get("contract_ids", []):
            if cid == ref:
                return NodeRef.contract(cid)
    elif node_type == "asset":
        for aid in created_ids.get("asset_ids", []):
            if aid == ref:
                return NodeRef.asset(aid)
    elif node_type == "event":
        for eid in created_ids.get("event_ids", []):
            if eid == ref:
                return NodeRef.event(eid)
    
    return None


# ============================================================================
# MAIN
# ============================================================================

def main() -> int:
    """Run the end-to-end integration proof."""
    print()
    print("=" * 70)
    print(" EntitySpine v2.2.4 - End-to-End Integration Proof")
    print(" SEC Filing → Knowledge Graph (stdlib-only)")
    print("=" * 70)
    
    # Determine fixtures directory
    script_dir = Path(__file__).parent
    fixtures_dir = script_dir / "fixtures"
    
    if not fixtures_dir.exists():
        print(f"ERROR: Fixtures directory not found: {fixtures_dir}")
        return 1
    
    # Create in-memory SQLite store
    store = SqliteStore(":memory:")
    store.initialize()
    
    try:
        # A) Tier 1 Setup + Basic Resolution
        issuer_entity_id = demo_tier1_setup(store, fixtures_dir)
        
        # B) Mock Filing Facts Ingestion
        payload = load_json(fixtures_dir / "mock_filing_facts_10k.json")
        created_ids = demo_filing_facts_ingestion(store, fixtures_dir, issuer_entity_id)
        
        # C) Tier Honesty Demonstration
        demo_tier_honesty(store)
        
        # D) KG Query + Summary
        demo_kg_summary(store, created_ids, payload)
        
        print_header("✓ END-TO-END INTEGRATION PROOF COMPLETE")
        print()
        print("  EntitySpine is ready to integrate with FeedSpine / py-sec-edgar!")
        print()
        print("  Next steps:")
        print("  1. FeedSpine extraction produces this JSON payload schema")
        print("  2. py-sec-edgar calls EntitySpine to persist KG nodes/edges")
        print("  3. Resolution API provides entity lookup for downstream apps")
        print()
        
        return 0
        
    finally:
        store.close()


if __name__ == "__main__":
    sys.exit(main())
