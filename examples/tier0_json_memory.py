#!/usr/bin/env python3
"""
EntitySpine Tier 0 Example: JSON/Memory Store

TIER 0 CAPABILITIES:
- Zero external dependencies (stdlib only)
- In-memory storage with optional JSON persistence
- Fast local development and prototyping
- Perfect for scripts, notebooks, small datasets
- No database setup required

USAGE:
    python examples/tier0_json_memory.py
"""

from __future__ import annotations

import json
import tempfile
from datetime import date
from pathlib import Path

# EntitySpine - ZERO external dependencies required
from entityspine.domain import (
    Entity,
    EntityType,
    EntityStatus,
    IdentifierClaim,
    IdentifierScheme,
    VendorNamespace,
)
from entityspine.stores import JsonEntityStore


def print_header(title: str) -> None:
    """Print a formatted section header."""
    print(f"\n{'=' * 70}")
    print(f" {title}")
    print(f"{'=' * 70}\n")


def main() -> None:
    """Demonstrate Tier 0 JSON/Memory store capabilities."""
    
    print_header("EntitySpine Tier 0: JSON/Memory Store Demo")
    print("Dependencies: NONE (stdlib only)")
    print("Best for: Scripts, notebooks, prototyping, small datasets")
    
    # ========================================================================
    # 1. CREATE STORE (in-memory)
    # ========================================================================
    print_header("1. Create In-Memory Store")
    
    store = JsonEntityStore()
    store.initialize()
    print("✓ Created empty in-memory store")
    print(f"  - Entities: {store.entity_count()}")
    print(f"  - Listings: {store.listing_count()}")
    
    # ========================================================================
    # 2. ADD ENTITIES MANUALLY
    # ========================================================================
    print_header("2. Add Entities Programmatically")
    
    # Create an entity using actual domain model
    apple = Entity(
        entity_id="ent_apple_001",
        primary_name="Apple Inc.",
        entity_type=EntityType.ORGANIZATION,
        status=EntityStatus.ACTIVE,
        jurisdiction="US-CA",
        sic_code="3571",
        incorporation_date=date(1977, 4, 1),
        source_system="sec_edgar",
        aliases=("Apple Computer, Inc.",),  # Historical name
    )
    
    store.save_entity(apple)
    print(f"✓ Saved: {apple.primary_name}")
    print(f"  - Entity ID: {apple.entity_id}")
    print(f"  - Type: {apple.entity_type.value}")
    print(f"  - Jurisdiction: {apple.jurisdiction}")
    print(f"  - Aliases: {apple.aliases}")
    
    # Add identifier claims (v2.2.3 design - identifiers are claims, not fields)
    claims = [
        IdentifierClaim(
            claim_id="clm_001",
            entity_id=apple.entity_id,
            scheme=IdentifierScheme.CIK,
            value="0000320193",
            namespace=VendorNamespace.SEC,
            valid_from=date(1994, 1, 1),
            confidence=1.0,
            source="SEC EDGAR",
        ),
        IdentifierClaim(
            claim_id="clm_002",
            entity_id=apple.entity_id,
            scheme=IdentifierScheme.LEI,
            value="HWUPKR0MPOU8FGXBT394",
            namespace=VendorNamespace.GLEIF,
            valid_from=date(2014, 1, 1),
            confidence=1.0,
            source="GLEIF database",
        ),
    ]
    
    for claim in claims:
        store.save_claim(claim)
    print(f"✓ Saved {len(claims)} identifier claims")
    
    # ========================================================================
    # 3. BULK LOAD SEC DATA
    # ========================================================================
    print_header("3. Bulk Load SEC Data")
    
    # Load sample SEC tickers using built-in method
    fixtures_path = Path(__file__).parent / "fixtures" / "sec_company_tickers_sample.json"
    
    if fixtures_path.exists():
        with open(fixtures_path) as f:
            sec_data = json.load(f)
        
        store2 = JsonEntityStore()
        store2.initialize()
        loaded = store2.load_sec_json(sec_data)
        
        print(f"✓ Loaded from SEC JSON:")
        print(f"  - Entities: {store2.entity_count()}")
        print(f"  - Listings: {store2.listing_count()}")
    else:
        # Use inline sample data
        sec_data = {
            "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
            "1": {"cik_str": 789019, "ticker": "MSFT", "title": "Microsoft Corporation"},
            "2": {"cik_str": 1652044, "ticker": "GOOGL", "title": "Alphabet Inc."},
            "3": {"cik_str": 1018724, "ticker": "AMZN", "title": "Amazon.com Inc."},
            "4": {"cik_str": 1326801, "ticker": "META", "title": "Meta Platforms Inc."},
        }
        
        store2 = JsonEntityStore()
        store2.initialize()
        loaded = store2.load_sec_json(sec_data)
        
        print(f"✓ Loaded from inline SEC data:")
        print(f"  - Entities: {store2.entity_count()}")
        print(f"  - Listings: {store2.listing_count()}")
    
    # ========================================================================
    # 4. RESOLUTION: Find entities by various identifiers
    # ========================================================================
    print_header("4. Entity Resolution")
    
    # Resolve by CIK
    entities = store2.get_entities_by_cik("320193")
    if entities:
        print(f"  get_entities_by_cik('320193') → {entities[0].primary_name}")
    
    # Resolve by ticker
    entities = store2.get_entities_by_ticker("AAPL")
    if entities:
        print(f"  get_entities_by_ticker('AAPL') → {entities[0].primary_name}")
    
    # More resolution tests
    for test_id, method_name in [
        ("MSFT", "get_entities_by_ticker"),
        ("789019", "get_entities_by_cik"),
        ("GOOGL", "get_entities_by_ticker"),
    ]:
        method = getattr(store2, method_name)
        entities = method(test_id)
        if entities:
            print(f"  {method_name}('{test_id}') → {entities[0].primary_name}")
    
    # ========================================================================
    # 5. SEARCH
    # ========================================================================
    print_header("5. Search (Tier 0: exact match)")
    
    # Search by name
    results = store2.search_entities("Apple Inc.", limit=5)
    print(f"  search_entities('Apple Inc.'):")
    for entity, score in results:
        print(f"    - {entity.primary_name} (score={score:.2f})")
    
    # Search by CIK
    results = store2.search_entities("320193", limit=5)
    print(f"\n  search_entities('320193'):")
    for entity, score in results:
        print(f"    - {entity.primary_name} (score={score:.2f})")
    
    # ========================================================================
    # 6. PERSISTENCE: Save to JSON file
    # ========================================================================
    print_header("6. JSON Persistence")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        json_path = Path(tmpdir) / "entities.json"
        
        # Create store with persistence
        store3 = JsonEntityStore(json_path=json_path)
        store3.initialize()
        store3.load_sec_json(sec_data)
        
        # Save by closing
        store3.close()
        print(f"✓ Persisted to: {json_path.name}")
        
        # Check file size
        size_kb = json_path.stat().st_size / 1024
        print(f"  File size: {size_kb:.2f} KB")
        
        # Reload and verify
        store4 = JsonEntityStore(json_path=json_path)
        store4.initialize()
        print(f"✓ Reloaded: {store4.entity_count()} entities")
    
    # ========================================================================
    # SUMMARY
    # ========================================================================
    print_header("Tier 0 Summary")
    
    print("""
TIER 0 CAPABILITIES DEMONSTRATED:
  ✓ Zero dependencies (stdlib only)
  ✓ In-memory entity storage
  ✓ Entity/Security/Listing/Claim management
  ✓ v2.2.3 design: Identifiers via Claims (not on entities)
  ✓ SEC JSON bulk loading
  ✓ Resolution by CIK, Ticker, Name
  ✓ Basic search (exact match)
  ✓ JSON file persistence

v2.2.3 KEY DESIGN:
  • Entity: primary_name, jurisdiction, sic_code
  • IdentifierClaim: THE source of truth for CIK, LEI, Ticker, etc.
  • Listing: Where TICKER lives (exchange-specific)

WHEN TO USE TIER 0:
  • Quick prototyping and exploration
  • Jupyter notebooks
  • Small datasets (< 50k entities)
  • Offline scripts
  • Testing and CI/CD

UPGRADE TO TIER 1 (SQLite) WHEN YOU NEED:
  • Concurrent read access
  • SQL query capabilities
  • Better search (LIKE patterns)
  • Persistent without explicit save
""")


if __name__ == "__main__":
    main()
