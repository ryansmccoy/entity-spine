#!/usr/bin/env python3
"""
EntitySpine Tier 1 Example: SQLite Store

TIER 1 CAPABILITIES:
- Zero external dependencies (stdlib only)
- Persistent database - no explicit save needed
- Concurrent read access
- SQL query capabilities
- Better than JSON for > 10k entities
- ACID transactions

USAGE:
    python examples/tier1_sqlite.py
"""

from __future__ import annotations

from datetime import date

# EntitySpine - ZERO external dependencies required for Tier 1
from entityspine.domain import (
    Entity,
    EntityType,
    EntityStatus,
    IdentifierClaim,
    IdentifierScheme,
    VendorNamespace,
)
from entityspine.stores import SqliteStore


def print_header(title: str) -> None:
    """Print a formatted section header."""
    print(f"\n{'=' * 70}")
    print(f" {title}")
    print(f"{'=' * 70}\n")


def main() -> None:
    """Demonstrate Tier 1 SQLite store capabilities."""
    
    print_header("EntitySpine Tier 1: SQLite Store Demo")
    print("Dependencies: NONE (stdlib only - sqlite3 is built-in)")
    print("Best for: Medium datasets, persistent local storage, SQL queries")
    
    # ========================================================================
    # 1. CREATE STORE (SQLite in-memory for demo)
    # ========================================================================
    print_header("1. Create SQLite Store")
    
    # Use in-memory database for demo (no file cleanup issues)
    # In production, use: SqliteStore(db_path=Path("entities.db"))
    store = SqliteStore(db_path=":memory:")
    store.initialize()
    print("✓ Created SQLite database (in-memory)")
    print(f"  - Tables created automatically")
    print(f"  - Entities: {store.entity_count()}")
    
    # ========================================================================
    # 2. LOAD SEC DATA (demonstrates bulk loading)
    # ========================================================================
    print_header("2. Bulk Load SEC Data")
    
    # Sample SEC data (normally from company_tickers.json)
    sec_data = {
        "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
        "1": {"cik_str": 789019, "ticker": "MSFT", "title": "Microsoft Corporation"},
        "2": {"cik_str": 1652044, "ticker": "GOOGL", "title": "Alphabet Inc."},
        "3": {"cik_str": 1018724, "ticker": "AMZN", "title": "Amazon.com Inc."},
        "4": {"cik_str": 1326801, "ticker": "META", "title": "Meta Platforms Inc."},
        "5": {"cik_str": 1045810, "ticker": "NVDA", "title": "NVIDIA Corporation"},
        "6": {"cik_str": 886982, "ticker": "GS", "title": "Goldman Sachs Group Inc."},
        "7": {"cik_str": 70858, "ticker": "BAC", "title": "Bank of America Corp"},
        "8": {"cik_str": 200406, "ticker": "JNJ", "title": "Johnson & Johnson"},
        "9": {"cik_str": 93410, "ticker": "CVX", "title": "Chevron Corporation"},
    }
    
    loaded = store.load_sec_json(sec_data)
    print(f"✓ Loaded {loaded} entities from SEC data")
    print(f"  - Total entities: {store.entity_count()}")
    print(f"  - Total listings: {store.listing_count()}")
    
    # ========================================================================
    # 3. ENTITY RESOLUTION
    # ========================================================================
    print_header("3. Entity Resolution (CIK, Ticker, Name)")
    
    # Resolve by CIK
    entities = store.get_entities_by_cik("320193")
    if entities:
        print(f"  get_entities_by_cik('320193') → {entities[0].primary_name}")
    
    # Resolve by ticker
    entities = store.get_entities_by_ticker("NVDA")
    if entities:
        print(f"  get_entities_by_ticker('NVDA') → {entities[0].primary_name}")
    
    # Resolution with full padding
    for cik, expected in [("0000789019", "Microsoft"), ("0000070858", "Bank of America")]:
        entities = store.get_entities_by_cik(cik)
        if entities:
            print(f"  get_entities_by_cik('{cik}') → {entities[0].primary_name}")
    
    # ========================================================================
    # 4. SQL QUERIES (Tier 1 advantage!)
    # ========================================================================
    print_header("4. SQL Query Capabilities (Tier 1 advantage)")
    
    # Direct SQL access for advanced queries
    conn = store._conn
    cursor = conn.cursor()
    
    # Count entities by type
    cursor.execute("""
        SELECT entity_type, COUNT(*) as cnt 
        FROM entities 
        GROUP BY entity_type
    """)
    print("  Entity counts by type:")
    for row in cursor.fetchall():
        print(f"    - {row[0]}: {row[1]}")
    
    # Find entities with specific patterns
    cursor.execute("""
        SELECT entity_id, primary_name 
        FROM entities 
        WHERE primary_name LIKE '%Inc%'
        LIMIT 5
    """)
    print("\n  Entities with 'Inc' in name (LIKE pattern):")
    for row in cursor.fetchall():
        print(f"    - {row[1]}")
    
    # ========================================================================
    # 5. SEARCH (better than Tier 0)
    # ========================================================================
    print_header("5. Search (LIKE patterns vs Tier 0 exact match)")
    
    results = store.search_entities("Apple", limit=5)
    print(f"  search_entities('Apple'):")
    for entity, score in results:
        print(f"    - {entity.primary_name} (score={score:.2f})")
    
    results = store.search_entities("Corporation", limit=5)
    print(f"\n  search_entities('Corporation'):")
    for entity, score in results:
        print(f"    - {entity.primary_name} (score={score:.2f})")
    
    # ========================================================================
    # 6. ADD ADDITIONAL IDENTIFIERS
    # ========================================================================
    print_header("6. Add Additional Identifiers")
    
    # Enrich with LEI claims
    entities = store.get_entities_by_cik("320193")  # Apple
    if entities:
        claim = IdentifierClaim(
            claim_id="clm_aapl_lei",
            entity_id=entities[0].entity_id,
            scheme=IdentifierScheme.LEI,
            value="HWUPKR0MPOU8FGXBT394",
            namespace=VendorNamespace.GLEIF,
            valid_from=date(2014, 1, 1),
            confidence=1.0,
            source="GLEIF",
        )
        store.save_claim(claim)
        print(f"✓ Added LEI claim for Apple: {claim.value}")
    
    store.close()
    
    # ========================================================================
    # SUMMARY
    # ========================================================================
    print_header("Tier 1 Summary")
    
    print("""
TIER 1 CAPABILITIES DEMONSTRATED:
  ✓ Zero dependencies (stdlib sqlite3)
  ✓ Automatic schema creation
  ✓ SQL query capabilities
  ✓ LIKE pattern search
  ✓ ACID transactions
  ✓ Better performance for medium datasets

TIER 1 vs TIER 0:
  • Tier 0 (JSON): Simple, human-readable files
  • Tier 1 (SQLite): Persistent, queryable, transactional

FILE-BASED USAGE:
  # Persistent storage to file
  from pathlib import Path
  store = SqliteStore(db_path=Path("entities.db"))
  store.initialize()
  # ... use store ...
  store.close()
  
  # Reopen later
  store = SqliteStore(db_path=Path("entities.db"))
  store.initialize()  # Tables already exist

WHEN TO USE TIER 1:
  • Datasets 10k-500k entities
  • Need SQL queries
  • Need persistence without explicit save
  • Single-user applications
  • Embedded applications

UPGRADE TO TIER 2 (DuckDB) WHEN YOU NEED:
  • Complex analytics and aggregations
  • Columnar storage for large datasets
  • Parquet/Arrow integration
  • Data science workflows
""")


if __name__ == "__main__":
    main()
