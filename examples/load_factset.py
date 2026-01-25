#!/usr/bin/env python3
"""
FactSet Data Loader for EntitySpine

Load large FactSet company datasets into EntitySpine efficiently.
Handles 500MB+ files with 600K+ entities.

USAGE:
    python examples/load_factset.py
"""

from __future__ import annotations

import csv
import gc
import sys
import time
from datetime import date
from pathlib import Path
from typing import Iterator

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
from entityspine.domain.timestamps import generate_ulid
from entityspine.stores import SqliteStore


# ============================================================================
# FactSet field mappings
# ============================================================================

FACTSET_COMPANY_TYPE_MAP = {
    "Public Company": EntityType.ORGANIZATION,
    "Subsidiary": EntityType.ORGANIZATION,
    "Holding Company": EntityType.ORGANIZATION,
    "Private Company": EntityType.ORGANIZATION,
    "Government": EntityType.GOVERNMENT,
    "Non-Profit": EntityType.ORGANIZATION,
    "Joint Venture": EntityType.ORGANIZATION,
    "": EntityType.ORGANIZATION,
}

# Map FactSet exchange names to MIC codes
FACTSET_EXCHANGE_TO_MIC = {
    "NYSE": "XNYS",
    "NASDAQ": "XNAS",
    "AMEX": "XASE",
    "NYSE ARCA": "ARCX",
    "NYSE MKT": "XASE",
    "OTC": "OTCM",
    "PINK": "OTCM",
    "London Stock Exchange": "XLON",
    "LSE": "XLON",
    "Toronto Stock Exchange": "XTSE",
    "TSX": "XTSE",
    "Tokyo Stock Exchange": "XTKS",
    "Hong Kong Stock Exchange": "XHKG",
    "Shanghai Stock Exchange": "XSHG",
    "Shenzhen Stock Exchange": "XSHE",
    "Deutsche Boerse": "XETR",
    "Euronext Paris": "XPAR",
    "SIX Swiss Exchange": "XSWX",
    "Australian Securities Exchange": "XASX",
    "": "UNKNOWN",
}


def parse_factset_identifier(identifier: str) -> tuple[str, str, str]:
    """
    Parse FactSet identifier format: TICKER.EXCHANGE-REGION
    
    Examples:
        AAPL.O-US -> (AAPL, O, US) -> (ticker, NASDAQ, United States)
        MSFT.OQ-US -> (MSFT, OQ, US)
        BA.N-US -> (BA, N, US) -> (ticker, NYSE, United States)
    
    FactSet exchange codes:
        O, OQ = NASDAQ
        N = NYSE
        A = AMEX
        P = NYSE ARCA
        XX = Private/Unlisted
    """
    if not identifier:
        return "", "", ""
    
    # Split on dots and dashes
    parts = identifier.replace("-", ".").split(".")
    
    ticker = parts[0] if len(parts) > 0 else ""
    exchange_code = parts[1] if len(parts) > 1 else ""
    region = parts[2] if len(parts) > 2 else ""
    
    return ticker, exchange_code, region


def factset_exchange_to_mic(exchange_code: str) -> tuple[str, str]:
    """
    Convert FactSet exchange code to exchange name and MIC.
    
    Returns:
        (exchange_name, mic_code)
    """
    exchange_map = {
        "O": ("NASDAQ", "XNAS"),
        "OQ": ("NASDAQ", "XNAS"),
        "N": ("NYSE", "XNYS"),
        "A": ("AMEX", "XASE"),
        "P": ("NYSE ARCA", "ARCX"),
        "XX": ("UNLISTED", "XXXX"),
        "XX1": ("UNLISTED", "XXXX"),
        "XX2": ("UNLISTED", "XXXX"),
        "L": ("LSE", "XLON"),
        "T": ("TSE", "XTSE"),
        "HK": ("HKEX", "XHKG"),
        "SS": ("SSE", "XSHG"),
        "SZ": ("SZSE", "XSHE"),
    }
    
    return exchange_map.get(exchange_code, ("UNKNOWN", "XXXX"))


def iter_factset_csv(
    filepath: Path,
    batch_size: int = 10000,
) -> Iterator[list[dict]]:
    """
    Stream FactSet CSV in batches for memory efficiency.
    
    Yields batches of rows as dictionaries.
    """
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f, delimiter="\t")
        
        batch = []
        for row in reader:
            batch.append(row)
            
            if len(batch) >= batch_size:
                yield batch
                batch = []
        
        # Yield remaining
        if batch:
            yield batch


def load_factset_batch(
    store: SqliteStore,
    rows: list[dict],
    seen_ciks: set[str],
) -> tuple[int, int, int]:
    """
    Load a batch of FactSet rows into the store.
    
    Returns:
        (entities_created, securities_created, listings_created)
    """
    entities = 0
    securities = 0
    listings = 0
    
    for row in rows:
        try:
            # Extract key fields
            identifier = row.get("Identifier", "").strip()
            name = row.get("Name", "").strip()
            company_type = row.get("Company Type", "").strip()
            country = row.get("Country", "").strip()
            exchange_name = row.get("Stock Exchange", "").strip()
            sic_industry = row.get("Primary SIC Industry", "").strip()
            
            if not identifier or not name:
                continue
            
            # Parse FactSet identifier
            ticker, exchange_code, region = parse_factset_identifier(identifier)
            
            # Generate unique entity ID from identifier
            entity_id = f"fs_{identifier.replace('.', '_').replace('-', '_')}"
            
            # Skip if we've seen this entity
            if entity_id in seen_ciks:
                continue
            seen_ciks.add(entity_id)
            
            # Determine entity type
            entity_type = FACTSET_COMPANY_TYPE_MAP.get(
                company_type, EntityType.ORGANIZATION
            )
            
            # Extract SIC code (first 4 digits if present)
            sic_code = None
            if sic_industry:
                # Try to extract numeric SIC from industry name
                pass  # FactSet uses industry names, not codes
            
            # Create entity
            entity = Entity(
                entity_id=entity_id,
                primary_name=name.strip('"'),  # Remove quotes
                entity_type=entity_type,
                status=EntityStatus.ACTIVE,
                jurisdiction=country,
                sic_code=sic_code,
                source_system="factset",
                source_id=identifier,
            )
            store.save_entity(entity)
            entities += 1
            
            # Create FactSet ID claim
            fs_claim = IdentifierClaim(
                claim_id=f"clm_fs_{entity_id}",
                entity_id=entity_id,
                scheme=IdentifierScheme.INTERNAL,
                value=identifier,
                namespace=VendorNamespace.FACTSET,
                confidence=1.0,
                source="factset_pubpriv",
            )
            store.save_claim(fs_claim)
            
            # Create security if it's a public company with exchange
            if exchange_name or exchange_code not in ("XX", "XX1", "XX2", ""):
                security_id = f"sec_{entity_id}"
                security = Security(
                    security_id=security_id,
                    entity_id=entity_id,
                    security_type=SecurityType.COMMON_STOCK,
                    description=f"{name} Common Stock",
                    currency="USD" if region == "US" else None,
                    source_system="factset",
                )
                store.save_security(security)
                securities += 1
                
                # Create listing if we have ticker
                if ticker:
                    exchange, mic = factset_exchange_to_mic(exchange_code)
                    if exchange_name:
                        # Use the explicit exchange name from data
                        exchange = exchange_name
                        mic = FACTSET_EXCHANGE_TO_MIC.get(exchange_name, "XXXX")
                    
                    listing_id = f"lst_{entity_id}_{mic}"
                    listing = Listing(
                        listing_id=listing_id,
                        security_id=security_id,
                        ticker=ticker,
                        exchange=exchange,
                        mic=mic,
                        is_primary=True,
                        source_system="factset",
                    )
                    store._save_listing_internal(listing)
                    listings += 1
                    
                    # Create ticker claim
                    ticker_claim = IdentifierClaim(
                        claim_id=f"clm_tkr_{listing_id}",
                        listing_id=listing_id,
                        scheme=IdentifierScheme.TICKER,
                        value=ticker,
                        namespace=VendorNamespace.FACTSET,
                        confidence=1.0,
                        source="factset_pubpriv",
                    )
                    store.save_claim(ticker_claim)
        
        except Exception as e:
            # Log but continue
            continue
    
    return entities, securities, listings


def load_factset_file(
    filepath: Path,
    db_path: Path | str = ":memory:",
    batch_size: int = 10000,
    max_rows: int | None = None,
) -> SqliteStore:
    """
    Load FactSet CSV into EntitySpine SQLite store.
    
    Args:
        filepath: Path to FactSet CSV file
        db_path: SQLite database path (":memory:" for in-memory)
        batch_size: Rows to process per batch
        max_rows: Maximum rows to load (None for all)
    
    Returns:
        Populated SqliteStore
    """
    print(f"Loading FactSet data from: {filepath}")
    print(f"Database: {db_path}")
    print(f"Batch size: {batch_size:,}")
    if max_rows:
        print(f"Max rows: {max_rows:,}")
    print()
    
    # Create store
    store = SqliteStore(db_path=db_path)
    store.initialize()
    
    # Track progress
    start_time = time.time()
    total_rows = 0
    total_entities = 0
    total_securities = 0
    total_listings = 0
    seen_ids: set[str] = set()
    
    # Process batches
    for batch_num, batch in enumerate(iter_factset_csv(filepath, batch_size)):
        if max_rows and total_rows >= max_rows:
            break
        
        # Limit batch if needed
        if max_rows:
            remaining = max_rows - total_rows
            if remaining < len(batch):
                batch = batch[:remaining]
        
        # Load batch
        e, s, l = load_factset_batch(store, batch, seen_ids)
        total_rows += len(batch)
        total_entities += e
        total_securities += s
        total_listings += l
        
        # Progress report
        elapsed = time.time() - start_time
        rate = total_rows / elapsed if elapsed > 0 else 0
        print(
            f"  Batch {batch_num + 1}: {total_rows:,} rows, "
            f"{total_entities:,} entities, "
            f"{rate:.0f} rows/sec"
        )
        
        # Commit periodically
        if batch_num % 10 == 0:
            store._conn.commit()
            gc.collect()  # Help with memory
    
    # Final commit
    store._conn.commit()
    
    elapsed = time.time() - start_time
    print()
    print(f"=" * 60)
    print(f"LOAD COMPLETE")
    print(f"=" * 60)
    print(f"  Time: {elapsed:.1f} seconds")
    print(f"  Rows processed: {total_rows:,}")
    print(f"  Entities created: {total_entities:,}")
    print(f"  Securities created: {total_securities:,}")
    print(f"  Listings created: {total_listings:,}")
    print(f"  Rate: {total_rows / elapsed:.0f} rows/sec")
    print()
    
    return store


def main():
    """Load FactSet data and demonstrate queries."""
    
    # FactSet file path
    factset_path = Path(r"G:\FACTSET\public_private\ff_pubpriv_companies_all.csv")
    
    if not factset_path.exists():
        print(f"ERROR: File not found: {factset_path}")
        sys.exit(1)
    
    # File info
    file_size_mb = factset_path.stat().st_size / (1024 * 1024)
    print(f"File: {factset_path.name}")
    print(f"Size: {file_size_mb:.1f} MB")
    print()
    
    # Load data - use file-based SQLite for large dataset
    db_path = Path("factset_entities.db")
    
    # For testing, limit to first 50k rows
    # Set max_rows=None to load everything
    store = load_factset_file(
        factset_path,
        db_path=db_path,
        batch_size=10000,
        max_rows=50000,  # Limit for testing - set to None for full load
    )
    
    # Test queries
    print("=" * 60)
    print("QUERY TESTS")
    print("=" * 60)
    
    # Search by name
    print("\nSearch 'Apple':")
    results = store.search_entities("Apple", limit=5)
    for entity, score in results:
        print(f"  - {entity.primary_name} ({entity.jurisdiction})")
    
    print("\nSearch 'Microsoft':")
    results = store.search_entities("Microsoft", limit=5)
    for entity, score in results:
        print(f"  - {entity.primary_name} ({entity.jurisdiction})")
    
    # Stats by country
    print("\nTop countries:")
    cursor = store._conn.cursor()
    cursor.execute("""
        SELECT jurisdiction, COUNT(*) as cnt 
        FROM entities 
        WHERE jurisdiction IS NOT NULL AND jurisdiction != ''
        GROUP BY jurisdiction 
        ORDER BY cnt DESC 
        LIMIT 10
    """)
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]:,}")
    
    # Memory usage
    import os
    try:
        import psutil
        process = psutil.Process(os.getpid())
        mem_mb = process.memory_info().rss / (1024 * 1024)
        print(f"\nMemory usage: {mem_mb:.1f} MB")
    except ImportError:
        pass
    
    # Database size
    if db_path != ":memory:":
        db_size_mb = db_path.stat().st_size / (1024 * 1024)
        print(f"Database size: {db_size_mb:.1f} MB")
    
    store.close()
    print("\nDone!")


if __name__ == "__main__":
    main()
