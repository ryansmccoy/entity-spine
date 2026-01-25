#!/usr/bin/env python3
"""
SEC Data Pipeline Example

This example demonstrates a complete SEC EDGAR data pipeline:

1. LOAD: Fetch company data from SEC EDGAR
2. ENRICH: Add additional identifiers (LEI, DUNS, etc.)
3. RESOLVE: Query entities by various identifiers
4. EXPORT: Output resolved entities

This is the primary use case for EntitySpine with py-sec-edgar.

USAGE:
    python examples/sec_data_pipeline.py
"""

from __future__ import annotations

import json
import tempfile
from datetime import date
from pathlib import Path

from entityspine.domain import (
    Entity,
    EntityType,
    EntityStatus,
    Security,
    SecurityType,
    Listing,
    IdentifierClaim,
    IdentifierScheme,
    VendorNamespace,
)
from entityspine.stores import JsonEntityStore, SqliteStore


def print_header(title: str) -> None:
    """Print a formatted section header."""
    print(f"\n{'=' * 70}")
    print(f" {title}")
    print(f"{'=' * 70}\n")


# Sample SEC data (normally from company_tickers.json)
SEC_COMPANY_TICKERS = {
    "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
    "1": {"cik_str": 789019, "ticker": "MSFT", "title": "Microsoft Corporation"},
    "2": {"cik_str": 1652044, "ticker": "GOOGL", "title": "Alphabet Inc."},
    "3": {"cik_str": 1652044, "ticker": "GOOG", "title": "Alphabet Inc."},  # Class C shares
    "4": {"cik_str": 1018724, "ticker": "AMZN", "title": "Amazon.com Inc."},
    "5": {"cik_str": 1326801, "ticker": "META", "title": "Meta Platforms Inc."},
    "6": {"cik_str": 1045810, "ticker": "NVDA", "title": "NVIDIA Corporation"},
    "7": {"cik_str": 12927, "ticker": "BA", "title": "BOEING CO"},
    "8": {"cik_str": 886982, "ticker": "GS", "title": "Goldman Sachs Group Inc."},
    "9": {"cik_str": 200406, "ticker": "JNJ", "title": "Johnson & Johnson"},
    "10": {"cik_str": 51143, "ticker": "IBM", "title": "International Business Machines Corp"},
    "11": {"cik_str": 93410, "ticker": "CVX", "title": "Chevron Corporation"},
    "12": {"cik_str": 1318605, "ticker": "TSLA", "title": "Tesla Inc"},
}

# Additional LEI data (normally from GLEIF)
GLEIF_LEI_DATA = {
    "0000320193": "HWUPKR0MPOU8FGXBT394",  # Apple
    "0000789019": "INR2EJN1ERAN0W5ZP974",  # Microsoft
    "0001652044": "5493006MHB84DD0ZWV18",  # Alphabet
    "0001018724": "ZBER1F8J0YMQLDYHTD55",  # Amazon
    "0001326801": "BQ4BKCS1HXDV9HN80Z08",  # Meta
    "0001045810": "5493006M3DO0IG0I9H71",  # NVIDIA
    "0000012927": "RVHJWBXLJ1RFUBSY1F30",  # Boeing
    "0000886982": "784F5XWPLTWKTBV3E584",  # Goldman Sachs
    "0000200406": "549300G5B5SDHFZV3859",  # J&J
    "0000051143": "VGRQXHF3J8VDLUA7XE92",  # IBM
    "0000093410": "549300EYY9HN1J7R8P63",  # Chevron
    "0001318605": "54930043XZGB27CTOV49",  # Tesla
}


def stage1_load_sec_data(store: SqliteStore) -> int:
    """
    STAGE 1: Load SEC company tickers data
    
    This creates:
    - Entity (one per CIK)
    - Security (one per entity) 
    - Listing (one per ticker - multiple tickers can map to one entity)
    - IdentifierClaim for CIK
    """
    print_header("Stage 1: Load SEC Data")
    
    count = store.load_sec_json(SEC_COMPANY_TICKERS)
    
    print(f"✓ Loaded {count} unique entities from SEC")
    print(f"  - Entities: {store.entity_count()}")
    print(f"  - Listings: {store.listing_count()}")
    
    # Show multi-ticker entity example
    print("\n  Example: Alphabet has multiple tickers")
    for ticker in ["GOOGL", "GOOG"]:
        entities = store.get_entities_by_ticker(ticker)
        if entities:
            print(f"    {ticker} → {entities[0].primary_name}")
    
    return count


def stage2_enrich_with_lei(store: SqliteStore) -> int:
    """
    STAGE 2: Enrich with LEI identifiers
    
    This adds IdentifierClaim records from GLEIF data.
    """
    print_header("Stage 2: Enrich with LEI Identifiers")
    
    enriched = 0
    for cik, lei in GLEIF_LEI_DATA.items():
        entities = store.get_entities_by_cik(cik)
        if entities:
            entity = entities[0]
            
            # Create LEI claim
            claim = IdentifierClaim(
                claim_id=f"clm_lei_{cik}",
                entity_id=entity.entity_id,
                scheme=IdentifierScheme.LEI,
                value=lei,
                namespace=VendorNamespace.GLEIF,
                valid_from=date(2014, 1, 1),
                confidence=1.0,
                source="GLEIF database",
            )
            store.save_claim(claim)
            enriched += 1
    
    print(f"✓ Added {enriched} LEI identifiers from GLEIF")
    return enriched


def stage3_resolve_entities(store: SqliteStore) -> None:
    """
    STAGE 3: Demonstrate entity resolution
    
    Shows how the same entity can be found via multiple identifiers.
    """
    print_header("Stage 3: Entity Resolution")
    
    # Test cases: (identifier_type, identifier_value, description)
    test_cases = [
        ("CIK", "320193", "Apple via SEC CIK (short)"),
        ("CIK", "0000320193", "Apple via SEC CIK (padded)"),
        ("Ticker", "AAPL", "Apple via Ticker"),
        ("Ticker", "GOOGL", "Alphabet via Class A ticker"),
        ("Ticker", "GOOG", "Alphabet via Class C ticker"),
        ("CIK", "12927", "Boeing via short CIK"),
    ]
    
    print("Resolution tests:")
    for id_type, id_value, description in test_cases:
        if id_type == "CIK":
            entities = store.get_entities_by_cik(id_value)
        else:
            entities = store.get_entities_by_ticker(id_value)
        
        if entities:
            entity = entities[0]
            print(f"  {description}")
            print(f"    → {entity.primary_name}")
        else:
            print(f"  {description} → NOT FOUND")


def stage4_search_entities(store: SqliteStore) -> None:
    """
    STAGE 4: Demonstrate search capabilities
    """
    print_header("Stage 4: Search")
    
    search_terms = ["Apple", "Inc", "Corporation", "Goldman"]
    
    for term in search_terms:
        results = store.search_entities(term, limit=3)
        print(f"  search('{term}'):")
        if results:
            for entity, score in results:
                print(f"    - {entity.primary_name} (score={score:.2f})")
        else:
            print("    No results")
        print()


def stage5_export_crosswalk(store: SqliteStore) -> dict:
    """
    STAGE 5: Export identifier crosswalk
    
    Creates a mapping: Ticker → CIK → LEI
    """
    print_header("Stage 5: Export Crosswalk")
    
    crosswalk = []
    
    # For each ticker in our data
    for item in SEC_COMPANY_TICKERS.values():
        ticker = item["ticker"]
        cik_short = str(item["cik_str"])
        cik_padded = cik_short.zfill(10)
        name = item["title"]
        lei = GLEIF_LEI_DATA.get(cik_padded, "")
        
        crosswalk.append({
            "ticker": ticker,
            "cik": cik_padded,
            "lei": lei,
            "name": name,
        })
    
    print(f"✓ Generated crosswalk for {len(crosswalk)} securities")
    print("\nSample crosswalk entries:")
    for entry in crosswalk[:5]:
        print(f"  {entry['ticker']:6} → CIK:{entry['cik']} → LEI:{entry['lei'][:20]}...")
    
    return {"crosswalk": crosswalk, "generated_at": date.today().isoformat()}


def main() -> None:
    """Run the complete SEC data pipeline."""
    
    print_header("SEC Data Pipeline Example")
    print("This demonstrates a complete SEC EDGAR data pipeline:")
    print("  1. Load company tickers from SEC")
    print("  2. Enrich with LEI from GLEIF")
    print("  3. Resolve entities by various IDs")
    print("  4. Search by company name")
    print("  5. Export identifier crosswalk")
    
    # Use SQLite for this demo (Tier 1)
    store = SqliteStore(db_path=":memory:")
    store.initialize()
    
    # Run pipeline stages
    stage1_load_sec_data(store)
    stage2_enrich_with_lei(store)
    stage3_resolve_entities(store)
    stage4_search_entities(store)
    crosswalk = stage5_export_crosswalk(store)
    
    # Summary statistics
    print_header("Pipeline Summary")
    
    print(f"""
PIPELINE COMPLETED SUCCESSFULLY:

  Data Loaded:
    - Entities: {store.entity_count()}
    - Listings: {store.listing_count()}
    - LEI enrichments: {len(GLEIF_LEI_DATA)}

  Storage: SQLite (in-memory, Tier 1)
  
  Crosswalk Output:
    - {len(crosswalk['crosswalk'])} securities mapped
    - Fields: ticker, cik, lei, name

REAL-WORLD USAGE:

  # Load from actual SEC API
  store = SqliteStore(db_path="entities.db")
  store.initialize()
  store.load_sec_data()  # Fetches from SEC EDGAR

  # Or load from file
  with open("company_tickers.json") as f:
      store.load_sec_json(json.load(f))

  # Resolve any company
  entities = store.get_entities_by_ticker("AAPL")
  if entities:
      entity = entities[0]
      print(f"Found: {{entity.primary_name}}")
""")
    
    store.close()


if __name__ == "__main__":
    main()
