#!/usr/bin/env python
"""
Full multi-source data load with entity linking.

Loads complete datasets from:
1. Thomson OpenPermID (organizations with LEI, instruments, quotes)
2. Bloomberg Equity (BBUID-consolidated entities)
3. FactSet Fundamentals (ff_combined.csv)

Then links entities using:
- LEI (Legal Entity Identifier) - universal standard
- BBUID (Bloomberg Unique ID) - issuer-level
- Ticker + Exchange matching
"""

import logging
import os
import sys
import sqlite3
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from entityspine.stores import SqliteStore
from entityspine.loaders import ThomsonLoader, BloombergLoader, FactSetLoader

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"load_{datetime.now():%Y%m%d_%H%M%S}.log"),
    ],
)

logger = logging.getLogger(__name__)


# Data paths
THOMSON_DIR = Path("G:/THOMSON")
BLOOMBERG_DIR = Path("G:/BLOOMBERG/bbuid/Equity_Common_Stock_20160530")
FACTSET_FILE = Path("G:/FACTSET/ff_combined.csv")

# Output
DB_PATH = Path("entityspine_data/linked_load.db")


def load_thomson(store: SqliteStore, limit: int | None = None) -> None:
    """Load Thomson organizations, instruments, and quotes."""
    logger.info("=" * 60)
    logger.info("LOADING THOMSON OPENPERMID DATA")
    logger.info("=" * 60)
    
    loader = ThomsonLoader(store)
    
    # Load organizations with LEI extraction
    logger.info("Loading organizations...")
    stats = loader.load(
        THOMSON_DIR,
        limit=limit,
        file_types=["organization"]
    )
    logger.info(f"Organizations: {stats}")
    
    # Load instruments (securities)
    logger.info("Loading instruments...")
    loader2 = ThomsonLoader(store)  # Fresh loader for stats
    stats2 = loader2.load(
        THOMSON_DIR,
        limit=limit,
        file_types=["instrument"]
    )
    logger.info(f"Instruments: {stats2}")
    
    # Load quotes (listings)
    logger.info("Loading quotes...")
    loader3 = ThomsonLoader(store)  # Fresh loader for stats
    stats3 = loader3.load(
        THOMSON_DIR,
        limit=limit,
        file_types=["quote"]
    )
    logger.info(f"Quotes: {stats3}")


def load_bloomberg_consolidated(store: SqliteStore, limit: int | None = None) -> None:
    """
    Load Bloomberg data, consolidating by BBUID.
    
    BBUID is the issuer-level ID - multiple FIGIs/securities can map to same issuer.
    We create one entity per unique BBUID, with multiple securities.
    """
    logger.info("=" * 60)
    logger.info("LOADING BLOOMBERG EQUITY DATA (BBUID-CONSOLIDATED)")
    logger.info("=" * 60)
    
    loader = BloombergLoader(store)
    
    # Load the common stock files
    stats = loader.load(
        BLOOMBERG_DIR,
        limit=limit,
        create_securities=True,
        create_listings=True,
    )
    logger.info(f"Bloomberg: {stats}")


def load_factset(store: SqliteStore, limit: int | None = None) -> None:
    """Load FactSet fundamentals data."""
    logger.info("=" * 60)
    logger.info("LOADING FACTSET FUNDAMENTALS")
    logger.info("=" * 60)
    
    loader = FactSetLoader(store)
    
    stats = loader.load(
        FACTSET_FILE,
        limit=limit,
    )
    logger.info(f"FactSet: {stats}")


def analyze_identifiers(conn: sqlite3.Connection) -> dict:
    """Analyze available identifiers for linking."""
    logger.info("=" * 60)
    logger.info("ANALYZING IDENTIFIERS FOR LINKING")
    logger.info("=" * 60)
    
    cursor = conn.cursor()
    
    # First, show all scheme counts
    cursor.execute("""
        SELECT scheme, COUNT(*) as cnt
        FROM claims
        GROUP BY scheme
        ORDER BY cnt DESC
    """)
    logger.info("Claims by scheme:")
    for scheme, cnt in cursor.fetchall():
        logger.info(f"  {scheme}: {cnt:,}")
    
    # Count LEIs (case-insensitive)
    cursor.execute("""
        SELECT COUNT(DISTINCT value), COUNT(DISTINCT entity_id)
        FROM claims
        WHERE LOWER(scheme) = 'lei'
    """)
    lei_count, lei_entities = cursor.fetchone()
    logger.info(f"LEI identifiers: {lei_count} unique values, {lei_entities} entities")
    
    # Count ISINs
    cursor.execute("""
        SELECT COUNT(DISTINCT value), COUNT(DISTINCT security_id)
        FROM claims
        WHERE LOWER(scheme) = 'isin'
    """)
    isin_count, isin_securities = cursor.fetchone()
    logger.info(f"ISIN identifiers: {isin_count} unique values, {isin_securities} securities")
    
    # Count FIGIs
    cursor.execute("""
        SELECT COUNT(DISTINCT value), COUNT(DISTINCT security_id)
        FROM claims
        WHERE LOWER(scheme) = 'figi'
    """)
    figi_count, figi_securities = cursor.fetchone()
    logger.info(f"FIGI identifiers: {figi_count} unique values, {figi_securities} securities")
    
    # Count BBUIDs (stored as INTERNAL with bbuid: prefix or as raw value)
    cursor.execute("""
        SELECT COUNT(DISTINCT value), COUNT(DISTINCT entity_id)
        FROM claims
        WHERE LOWER(scheme) = 'internal'
        AND (LOWER(namespace) = 'bloomberg' OR value LIKE 'EQ%')
    """)
    bbuid_count, bbuid_entities = cursor.fetchone()
    logger.info(f"BBUID identifiers: {bbuid_count} unique values, {bbuid_entities} entities")
    
    # Count entities by source
    cursor.execute("""
        SELECT source_system, COUNT(*) as cnt
        FROM entities
        GROUP BY source_system
        ORDER BY cnt DESC
    """)
    source_counts = cursor.fetchall()
    logger.info("Entities by source:")
    for source, cnt in source_counts:
        logger.info(f"  {source}: {cnt:,}")
    
    return {
        "lei_count": lei_count,
        "lei_entities": lei_entities,
        "isin_count": isin_count,
        "figi_count": figi_count,
        "bbuid_count": bbuid_count,
    }


def link_entities_by_lei(conn: sqlite3.Connection) -> int:
    """
    Link entities that share the same LEI.
    
    Creates entity_relationships records for entities with matching LEI.
    """
    logger.info("=" * 60)
    logger.info("LINKING ENTITIES BY LEI")
    logger.info("=" * 60)
    
    cursor = conn.cursor()
    
    # Find LEIs that appear in multiple entities from different sources
    cursor.execute("""
        SELECT ic.value as lei, 
               GROUP_CONCAT(DISTINCT ic.entity_id) as entity_ids,
               GROUP_CONCAT(DISTINCT e.source_system) as sources,
               COUNT(DISTINCT ic.entity_id) as entity_count,
               COUNT(DISTINCT e.source_system) as source_count
        FROM claims ic
        JOIN entities e ON ic.entity_id = e.entity_id
        WHERE LOWER(ic.scheme) = 'lei'
        AND ic.entity_id IS NOT NULL
        GROUP BY ic.value
        HAVING COUNT(DISTINCT e.source_system) > 1
    """)
    
    multi_source_leis = cursor.fetchall()
    logger.info(f"Found {len(multi_source_leis)} LEIs shared across multiple sources")
    
    # Create links
    links_created = 0
    now = datetime.utcnow().isoformat()
    
    for lei, entity_ids_str, sources, entity_count, source_count in multi_source_leis:
        entity_ids = entity_ids_str.split(",")
        
        # Create links between all pairs
        for i, from_id in enumerate(entity_ids):
            for to_id in entity_ids[i+1:]:
                rel_id = f"lei:{lei}:{from_id}:{to_id}"
                try:
                    cursor.execute("""
                        INSERT OR IGNORE INTO entity_relationships 
                        (relationship_id, from_entity_id, to_entity_id, relationship_type, 
                         captured_at, source_system, created_at, updated_at)
                        VALUES (?, ?, ?, 'same_as', ?, 'lei_match', ?, ?)
                    """, (rel_id, from_id, to_id, now, now, now))
                    if cursor.rowcount > 0:
                        links_created += 1
                except Exception as e:
                    logger.warning(f"Error linking {from_id} -> {to_id}: {e}")
    
    conn.commit()
    logger.info(f"Created {links_created} entity links via LEI")
    
    return links_created


def link_entities_by_ticker(conn: sqlite3.Connection) -> int:
    """
    Link entities that share the same ticker symbol and exchange.
    
    This links different vendor records for the same security.
    """
    logger.info("=" * 60)
    logger.info("LINKING ENTITIES BY TICKER/EXCHANGE")
    logger.info("=" * 60)
    
    cursor = conn.cursor()
    
    # Find tickers that appear in multiple entities from different sources
    # Join through listings -> securities -> entities
    cursor.execute("""
        WITH ticker_entities AS (
            SELECT l.ticker, l.exchange, 
                   s.entity_id,
                   e.source_system,
                   e.primary_name
            FROM listings l
            JOIN securities s ON l.security_id = s.security_id
            JOIN entities e ON s.entity_id = e.entity_id
            WHERE l.ticker IS NOT NULL
            AND l.exchange IS NOT NULL
            AND LENGTH(l.ticker) >= 1
            AND LENGTH(l.ticker) <= 10
        )
        SELECT ticker, exchange,
               GROUP_CONCAT(DISTINCT entity_id) as entity_ids,
               GROUP_CONCAT(DISTINCT source_system) as sources,
               COUNT(DISTINCT entity_id) as entity_count,
               COUNT(DISTINCT source_system) as source_count
        FROM ticker_entities
        GROUP BY ticker, exchange
        HAVING COUNT(DISTINCT source_system) > 1
        ORDER BY entity_count DESC
        LIMIT 10000
    """)
    
    multi_source_tickers = cursor.fetchall()
    logger.info(f"Found {len(multi_source_tickers)} ticker/exchange pairs shared across multiple sources")
    
    # Create links
    links_created = 0
    now = datetime.utcnow().isoformat()
    
    for ticker, exchange, entity_ids_str, sources, entity_count, source_count in multi_source_tickers:
        entity_ids = entity_ids_str.split(",")
        
        # Create links between all pairs
        for i, from_id in enumerate(entity_ids):
            for to_id in entity_ids[i+1:]:
                rel_id = f"ticker:{ticker}:{exchange}:{from_id}:{to_id}"
                try:
                    cursor.execute("""
                        INSERT OR IGNORE INTO entity_relationships 
                        (relationship_id, from_entity_id, to_entity_id, relationship_type,
                         captured_at, source_system, created_at, updated_at)
                        VALUES (?, ?, ?, 'same_as', ?, 'ticker_match', ?, ?)
                    """, (rel_id, from_id, to_id, now, now, now))
                    if cursor.rowcount > 0:
                        links_created += 1
                except Exception as e:
                    pass  # Ignore duplicates
    
    conn.commit()
    logger.info(f"Created {links_created} entity links via ticker/exchange")
    
    return links_created


def analyze_nvda(conn: sqlite3.Connection) -> None:
    """Check if NVIDIA is linked across sources."""
    logger.info("=" * 60)
    logger.info("ANALYZING NVIDIA ENTITY LINKING")
    logger.info("=" * 60)
    
    cursor = conn.cursor()
    
    # Find all NVIDIA entities
    cursor.execute("""
        SELECT entity_id, primary_name, source_system, jurisdiction
        FROM entities
        WHERE LOWER(primary_name) LIKE '%nvidia%'
        ORDER BY source_system
    """)
    
    nvda_entities = cursor.fetchall()
    logger.info(f"Found {len(nvda_entities)} NVIDIA-related entities")
    
    for entity_id, name, source, jurisdiction in nvda_entities:
        logger.info(f"  [{source}] {entity_id}: {name} ({jurisdiction})")
        
        # Check for LEI
        cursor.execute("""
            SELECT scheme, value FROM claims
            WHERE entity_id = ? AND LOWER(scheme) = 'lei'
        """, (entity_id,))
        lei = cursor.fetchone()
        if lei:
            logger.info(f"    LEI: {lei[1]}")
        
        # Check for relationships
        cursor.execute("""
            SELECT relationship_type, to_entity_id, source_system
            FROM entity_relationships
            WHERE from_entity_id = ?
            UNION
            SELECT relationship_type, from_entity_id, source_system
            FROM entity_relationships
            WHERE to_entity_id = ?
        """, (entity_id, entity_id))
        
        rels = cursor.fetchall()
        if rels:
            logger.info(f"    Links: {len(rels)}")
            for rel_type, other_id, rel_source in rels[:5]:
                cursor.execute("SELECT primary_name, source_system FROM entities WHERE entity_id = ?", (other_id,))
                other = cursor.fetchone()
                if other:
                    logger.info(f"      -> {other[0]} ({other[1]}) via {rel_source}")


def print_summary(conn: sqlite3.Connection) -> None:
    """Print database summary."""
    logger.info("=" * 60)
    logger.info("DATABASE SUMMARY")
    logger.info("=" * 60)
    
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM entities")
    logger.info(f"Entities: {cursor.fetchone()[0]:,}")
    
    cursor.execute("SELECT COUNT(*) FROM securities")
    logger.info(f"Securities: {cursor.fetchone()[0]:,}")
    
    cursor.execute("SELECT COUNT(*) FROM listings")
    logger.info(f"Listings: {cursor.fetchone()[0]:,}")
    
    cursor.execute("SELECT COUNT(*) FROM claims")
    logger.info(f"Claims: {cursor.fetchone()[0]:,}")
    
    cursor.execute("SELECT COUNT(*) FROM entity_relationships")
    logger.info(f"Entity Relationships: {cursor.fetchone()[0]:,}")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Load multi-source data with linking")
    parser.add_argument("--limit", type=int, help="Limit records per source (for testing)")
    parser.add_argument("--skip-thomson", action="store_true", help="Skip Thomson loading")
    parser.add_argument("--skip-bloomberg", action="store_true", help="Skip Bloomberg loading")
    parser.add_argument("--skip-factset", action="store_true", help="Skip FactSet loading")
    parser.add_argument("--link-only", action="store_true", help="Only run linking (skip loading)")
    args = parser.parse_args()
    
    logger.info("=" * 60)
    logger.info("MULTI-SOURCE DATA LOAD WITH ENTITY LINKING")
    logger.info("=" * 60)
    logger.info(f"Database: {DB_PATH}")
    logger.info(f"Limit: {args.limit or 'None (full load)'}")
    
    # Create fresh database
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    if not args.link_only:
        # Remove existing database for fresh load
        if DB_PATH.exists():
            logger.info(f"Removing existing database: {DB_PATH}")
            DB_PATH.unlink()
        
        store = SqliteStore(db_path=str(DB_PATH))
        store.initialize()  # Create tables and establish connection
        try:
            # Load each source
            if not args.skip_thomson:
                load_thomson(store, limit=args.limit)
            
            if not args.skip_bloomberg:
                load_bloomberg_consolidated(store, limit=args.limit)
            
            if not args.skip_factset:
                load_factset(store, limit=args.limit)
        finally:
            store.close()
    
    # Connect for analysis and linking
    conn = sqlite3.connect(str(DB_PATH))
    
    try:
        # Analyze identifiers
        id_stats = analyze_identifiers(conn)
        
        # Link entities
        lei_links = link_entities_by_lei(conn)
        ticker_links = link_entities_by_ticker(conn)
        
        # Analyze NVIDIA specifically
        analyze_nvda(conn)
        
        # Final summary
        print_summary(conn)
        
    finally:
        conn.close()
    
    logger.info("=" * 60)
    logger.info("COMPLETED")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
