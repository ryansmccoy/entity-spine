#!/usr/bin/env python3
"""
EntitySpine Ingestion Patterns Example

This example demonstrates the various ways to ingest data into EntitySpine:

1. MANUAL CREATION - Create entities/securities/listings programmatically
2. SEC JSON LOADING - Bulk load from SEC company_tickers.json format
3. SEC API LOADING - Load directly from SEC EDGAR API
4. CLAIM-BASED INGESTION - Add identifiers via IdentifierClaim (v2.2.3 pattern)
5. MULTI-SOURCE MERGING - Combine data from multiple vendors

USAGE:
    python examples/ingestion_patterns.py
"""

from __future__ import annotations

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


def demo_manual_creation() -> None:
    """
    PATTERN 1: Manual Entity Creation
    
    Best for:
    - Creating entities from custom sources
    - Building test data
    - Interactive data entry
    """
    print_header("Pattern 1: Manual Entity Creation")
    
    store = JsonEntityStore()
    store.initialize()
    
    # Step 1: Create the Entity (legal identity)
    # v2.2.3: Entity has NO identifier fields - use Claims
    entity = Entity(
        entity_id="ent_boeing_001",
        primary_name="The Boeing Company",
        entity_type=EntityType.ORGANIZATION,
        status=EntityStatus.ACTIVE,
        jurisdiction="US-DE",  # Delaware incorporation
        sic_code="3721",  # Aircraft manufacturing
        incorporation_date=date(1916, 7, 15),
        source_system="manual",
        aliases=("Boeing", "Boeing Co"),
    )
    store.save_entity(entity)
    print(f"✓ Created entity: {entity.primary_name}")
    
    # Step 2: Add identifier claims (THE v2.2.3 way)
    claims = [
        # CIK claim
        IdentifierClaim(
            claim_id="clm_ba_cik",
            entity_id=entity.entity_id,
            scheme=IdentifierScheme.CIK,
            value="0000012927",
            namespace=VendorNamespace.SEC,
            valid_from=date(1986, 1, 1),
            confidence=1.0,
            source="SEC EDGAR",
        ),
        # LEI claim
        IdentifierClaim(
            claim_id="clm_ba_lei",
            entity_id=entity.entity_id,
            scheme=IdentifierScheme.LEI,
            value="RVHJWBXLJ1RFUBSY1F30",
            namespace=VendorNamespace.GLEIF,
            valid_from=date(2012, 1, 1),
            confidence=1.0,
            source="GLEIF",
        ),
    ]
    for claim in claims:
        store.save_claim(claim)
    print(f"✓ Added {len(claims)} identifier claims (CIK, LEI)")
    
    # Step 3: Create Security (represents the financial instrument)
    security = Security(
        security_id="sec_ba_common",
        entity_id=entity.entity_id,
        security_type=SecurityType.COMMON_STOCK,
        description="Boeing Company Common Stock",
        currency="USD",
        source_system="manual",
    )
    store.save_security(security)
    print(f"✓ Created security: {security.description}")
    
    # Note: In v2.2.3, to create a Listing you need to use internal methods
    # or the load_sec_json method. The public API for listings is limited.
    # This is by design - tickers are managed through structured loading.
    
    # Verify
    entities = store.get_entities_by_cik("12927")
    if entities:
        print(f"✓ Resolved by CIK: {entities[0].primary_name}")
    
    store.close()
    print("\n  ℹ️  Manual creation is best for custom/test data")


def demo_sec_json_loading() -> None:
    """
    PATTERN 2: SEC JSON Bulk Loading
    
    Best for:
    - Loading all US public companies
    - Initial database population
    - Periodic full refreshes
    """
    print_header("Pattern 2: SEC JSON Bulk Loading")
    
    store = JsonEntityStore()
    store.initialize()
    
    # SEC company_tickers.json format
    # This is the format from: https://www.sec.gov/files/company_tickers.json
    sec_data = {
        "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
        "1": {"cik_str": 789019, "ticker": "MSFT", "title": "Microsoft Corporation"},
        "2": {"cik_str": 1652044, "ticker": "GOOGL", "title": "Alphabet Inc."},
        "3": {"cik_str": 1652044, "ticker": "GOOG", "title": "Alphabet Inc."},  # Same CIK!
        "4": {"cik_str": 1018724, "ticker": "AMZN", "title": "Amazon.com Inc."},
    }
    
    count = store.load_sec_json(sec_data)
    print(f"✓ Loaded {count} unique entities from SEC JSON")
    print(f"  - Total entities: {store.entity_count()}")
    print(f"  - Total listings: {store.listing_count()}")
    
    # Note: Alphabet has 2 tickers (GOOGL, GOOG) but 1 entity
    entities = store.get_entities_by_cik("1652044")
    if entities:
        print(f"\n  Alphabet Inc. resolution:")
        print(f"    Entity: {entities[0].primary_name}")
        
        # Both tickers resolve to same entity
        for ticker in ["GOOGL", "GOOG"]:
            resolved = store.get_entities_by_ticker(ticker)
            if resolved:
                print(f"    {ticker} → {resolved[0].primary_name}")
    
    store.close()
    print("\n  ℹ️  load_sec_json handles deduplication by CIK automatically")


def demo_sec_api_loading() -> None:
    """
    PATTERN 3: SEC API Direct Loading
    
    Best for:
    - Loading fresh data from SEC
    - Automated updates
    - When you don't have a local JSON file
    
    Note: Requires internet access to SEC EDGAR.
    """
    print_header("Pattern 3: SEC API Loading (Optional)")
    
    print("  This pattern loads directly from SEC EDGAR API:")
    print("  https://www.sec.gov/files/company_tickers.json")
    print()
    print("  Example code:")
    print("    store = SqliteStore(db_path='entities.db')")
    print("    store.initialize()")
    print("    count = store.load_sec_data()  # Loads from SEC API")
    print()
    print("  ⚠️  Skipping actual API call in this demo")


def demo_claim_based_ingestion() -> None:
    """
    PATTERN 4: Claim-Based Identifier Ingestion
    
    This is THE v2.2.3 pattern for managing identifiers.
    Identifiers are NOT stored on Entity - they're IdentifierClaims.
    
    Best for:
    - Multi-vendor identifier management
    - Handling conflicting identifiers
    - Temporal identifier tracking
    """
    print_header("Pattern 4: Claim-Based Identifier Ingestion (v2.2.3)")
    
    store = JsonEntityStore()
    store.initialize()
    
    # First, create the entity without any identifiers
    entity = Entity(
        entity_id="ent_tesla_001",
        primary_name="Tesla, Inc.",
        entity_type=EntityType.ORGANIZATION,
        status=EntityStatus.ACTIVE,
        jurisdiction="US-DE",
        sic_code="3711",  # Motor vehicles
        source_system="sec",
    )
    store.save_entity(entity)
    print(f"✓ Created entity: {entity.primary_name}")
    print("  (Entity has NO identifier fields - v2.2.3 design)")
    
    # Now add identifiers as CLAIMS from different sources
    print("\n  Adding identifier claims from multiple vendors:")
    
    # SEC provides CIK
    sec_claim = IdentifierClaim(
        claim_id="clm_tsla_sec_cik",
        entity_id=entity.entity_id,
        scheme=IdentifierScheme.CIK,
        value="0001318605",
        namespace=VendorNamespace.SEC,
        valid_from=date(2010, 1, 1),
        confidence=1.0,
        source="SEC EDGAR filings",
    )
    store.save_claim(sec_claim)
    print(f"    SEC claim: CIK={sec_claim.value}")
    
    # GLEIF provides LEI
    gleif_claim = IdentifierClaim(
        claim_id="clm_tsla_gleif_lei",
        entity_id=entity.entity_id,
        scheme=IdentifierScheme.LEI,
        value="54930043XZGB27CTOV49",
        namespace=VendorNamespace.GLEIF,
        valid_from=date(2014, 6, 1),
        confidence=1.0,
        source="GLEIF database",
    )
    store.save_claim(gleif_claim)
    print(f"    GLEIF claim: LEI={gleif_claim.value}")
    
    # Note: FIGI and ISIN are SECURITY-scoped identifiers (not entity-scoped)
    # They would be attached to a Security, not an Entity.
    # For entity-level identifiers, use: CIK, LEI, EIN, DUNS
    
    # Add another entity-level identifier (EIN)
    ein_claim = IdentifierClaim(
        claim_id="clm_tsla_ein",
        entity_id=entity.entity_id,
        scheme=IdentifierScheme.EIN,
        value="91-2197729",
        namespace=VendorNamespace.SEC,
        valid_from=date(2003, 7, 1),
        confidence=1.0,
        source="SEC Form 10-K",
    )
    store.save_claim(ein_claim)
    print(f"    SEC claim: EIN={ein_claim.value}")
    
    # Resolve from any identifier
    print("\n  Resolution from ANY identifier works:")
    for cik in ["1318605", "0001318605"]:
        entities = store.get_entities_by_cik(cik)
        if entities:
            print(f"    CIK {cik} → {entities[0].primary_name}")
    
    store.close()
    print("\n  ℹ️  Claims enable multi-vendor crosswalks and temporal tracking")


def demo_multi_source_merge() -> None:
    """
    PATTERN 5: Multi-Source Data Merging
    
    Shows how to combine data from multiple sources while
    maintaining data lineage.
    """
    print_header("Pattern 5: Multi-Source Data Merging")
    
    store = SqliteStore(db_path=":memory:")  # In-memory SQLite
    store.initialize()
    
    # Source 1: SEC provides basic company info
    print("  Source 1: SEC (base company data)")
    sec_data = {
        "0": {"cik_str": 1341439, "ticker": "ORCL", "title": "ORACLE CORP"},
    }
    store.load_sec_json(sec_data)
    
    entities = store.get_entities_by_cik("1341439")
    if entities:
        print(f"    → {entities[0].primary_name}")
        entity_id = entities[0].entity_id
        
        # Source 2: GLEIF provides LEI
        print("  Source 2: GLEIF (LEI identifier)")
        lei_claim = IdentifierClaim(
            claim_id="clm_orcl_lei",
            entity_id=entity_id,
            scheme=IdentifierScheme.LEI,
            value="1Z4GXXU7ZHVWFCD8TV52",
            namespace=VendorNamespace.GLEIF,
            valid_from=date(2014, 1, 1),
            confidence=1.0,
            source="GLEIF",
        )
        store.save_claim(lei_claim)
        print(f"    → Added LEI: {lei_claim.value}")
        
        # Source 3: Add a DUNS number
        print("  Source 3: Dun & Bradstreet (DUNS number)")
        duns_claim = IdentifierClaim(
            claim_id="clm_orcl_duns",
            entity_id=entity_id,
            scheme=IdentifierScheme.DUNS,
            value="05-459-7742",
            namespace=VendorNamespace.OTHER,
            valid_from=date(1990, 1, 1),
            confidence=1.0,
            source="D&B",
        )
        store.save_claim(duns_claim)
        print(f"    → Added DUNS: {duns_claim.value}")
    
    # All identifiers resolve to same entity
    print("\n  Cross-vendor resolution:")
    print("    All identifiers map to single Oracle entity")
    
    store.close()
    print("\n  ℹ️  Claims preserve source lineage and enable crosswalks")


def main() -> None:
    """Run all ingestion pattern demonstrations."""
    
    print_header("EntitySpine Ingestion Patterns")
    print("This example demonstrates 5 ways to ingest data into EntitySpine.")
    
    # Run each pattern demo
    demo_manual_creation()
    demo_sec_json_loading()
    demo_sec_api_loading()
    demo_claim_based_ingestion()
    demo_multi_source_merge()
    
    # Summary
    print_header("Ingestion Patterns Summary")
    print("""
PATTERN OVERVIEW:

1. MANUAL CREATION
   - Use save_entity(), save_security(), save_claim()
   - Best for custom/test data
   - Full control over all fields

2. SEC JSON LOADING
   - Use load_sec_json(data)
   - Auto-creates Entity + Security + Listing + CIK claim
   - Handles multi-ticker entities (e.g., GOOGL/GOOG)

3. SEC API LOADING
   - Use load_sec_data()
   - Fetches directly from SEC EDGAR API
   - Good for automated refreshes

4. CLAIM-BASED INGESTION
   - Create Entity, then add IdentifierClaim objects
   - THE v2.2.3 pattern for identifiers
   - Enables multi-vendor crosswalks
   - Preserves temporal history

5. MULTI-SOURCE MERGING
   - Combine patterns 2 + 4
   - Load base data from SEC
   - Enrich with claims from other vendors
   - Maintains full data lineage

KEY v2.2.3 PRINCIPLE:
  Identifiers are CLAIMS, not Entity fields.
  This enables:
  • Multi-vendor identifier management
  • Conflicting identifier resolution
  • Temporal identifier tracking
  • Full data lineage
""")


if __name__ == "__main__":
    main()
