#!/usr/bin/env python3
"""
Load ALL EntitySpine reference data into the shared database.

This script loads:
1. SEC company_tickers.json (10,000+ US companies with CIK, ticker, name)
2. SEC company_tickers_exchange.json (with exchange info)
3. GLEIF LEI-ISIN mappings (266MB - links LEI to ISIN)
4. GLEIF LEI-BIC mappings (bank identifiers)

Run once to populate your shared database, then all apps can use it.

Usage:
    python scripts/load_all_reference_data.py
    
Environment:
    ENTITYSPINE_DB_PATH - Database location (default: ~/.entityspine/entityspine.db)
"""

import csv
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from entityspine import use_shared_db, get_db_path
from entityspine.stores.sqlite_store import SqliteStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Data directories
DATA_DIR = Path(__file__).parent.parent / "entityspine_data"
BULK_DIR = DATA_DIR / "bulk_reference"
GLEIF_DIR = DATA_DIR / "gleif"


def load_sec_tickers(store: SqliteStore) -> int:
    """Load SEC company tickers from local file."""
    sec_file = BULK_DIR / "sec_company_tickers.json"
    
    if not sec_file.exists():
        logger.warning(f"SEC tickers file not found: {sec_file}")
        return 0
    
    logger.info(f"Loading SEC tickers from {sec_file}")
    with open(sec_file) as f:
        data = json.load(f)
    
    count = store.load_sec_json(data)
    logger.info(f"✓ Loaded {count:,} SEC companies")
    return count


def load_sec_tickers_exchange(store: SqliteStore) -> int:
    """Load SEC company tickers with exchange info."""
    sec_file = BULK_DIR / "sec_company_tickers_exchange.json"
    
    if not sec_file.exists():
        logger.warning(f"SEC exchange file not found: {sec_file}")
        return 0
    
    logger.info(f"Loading SEC tickers with exchange from {sec_file}")
    with open(sec_file) as f:
        data = json.load(f)
    
    # This file has different format - update listings with exchange
    updated = 0
    with store._get_connection() as conn:
        cursor = conn.cursor()
        
        for entry in data.get("data", data.values()) if isinstance(data, dict) else data:
            if isinstance(entry, dict):
                cik = str(entry.get("cik", "")).zfill(10)
                exchange = entry.get("exchange", "")
                
                if exchange:
                    cursor.execute("""
                        UPDATE listings SET exchange = ?
                        WHERE listing_id IN (
                            SELECT l.listing_id FROM listings l
                            JOIN securities s ON l.security_id = s.security_id
                            JOIN entities e ON s.entity_id = e.entity_id
                            WHERE e.source_system = 'sec' AND e.source_id = ?
                        )
                    """, (exchange, cik))
                    updated += cursor.rowcount
        
        conn.commit()
    
    logger.info(f"✓ Updated {updated:,} listings with exchange info")
    return updated


def ensure_identifier_tables(store: SqliteStore):
    """Ensure we have tables for ISIN, LEI, BIC mappings."""
    with store._get_connection() as conn:
        cursor = conn.cursor()
        
        # Create ISIN mapping table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS isin_mappings (
                isin TEXT PRIMARY KEY,
                lei TEXT,
                entity_id TEXT,
                created_at TEXT NOT NULL
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_isin_lei ON isin_mappings(lei)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_isin_entity ON isin_mappings(entity_id)")
        
        # Create LEI mapping table  
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lei_mappings (
                lei TEXT PRIMARY KEY,
                entity_name TEXT,
                entity_id TEXT,
                jurisdiction TEXT,
                status TEXT,
                created_at TEXT NOT NULL
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_lei_entity ON lei_mappings(entity_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_lei_name ON lei_mappings(entity_name)")
        
        # Create BIC mapping table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bic_mappings (
                lei TEXT,
                bic TEXT,
                created_at TEXT NOT NULL,
                PRIMARY KEY (lei, bic)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_bic_lei ON bic_mappings(lei)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_bic_code ON bic_mappings(bic)")
        
        conn.commit()
    
    logger.info("✓ Identifier mapping tables ready")


def load_lei_isin_mappings(store: SqliteStore) -> int:
    """Load GLEIF LEI-ISIN mappings."""
    isin_file = GLEIF_DIR / "lei-isin-20260129T081545.csv"
    
    if not isin_file.exists():
        logger.warning(f"LEI-ISIN file not found: {isin_file}")
        return 0
    
    logger.info(f"Loading LEI-ISIN mappings from {isin_file} (this may take a minute...)")
    
    now = datetime.utcnow().isoformat()
    count = 0
    batch = []
    batch_size = 10000
    
    with store._get_connection() as conn:
        cursor = conn.cursor()
        
        with open(isin_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                lei = row.get('LEI', '').strip()
                isin = row.get('ISIN', '').strip()
                
                if lei and isin:
                    batch.append((isin, lei, None, now))
                    count += 1
                    
                    if len(batch) >= batch_size:
                        cursor.executemany(
                            "INSERT OR REPLACE INTO isin_mappings (isin, lei, entity_id, created_at) VALUES (?, ?, ?, ?)",
                            batch
                        )
                        batch = []
                        if count % 100000 == 0:
                            logger.info(f"  ... loaded {count:,} ISIN mappings")
        
        # Final batch
        if batch:
            cursor.executemany(
                "INSERT OR REPLACE INTO isin_mappings (isin, lei, entity_id, created_at) VALUES (?, ?, ?, ?)",
                batch
            )
        
        conn.commit()
    
    logger.info(f"✓ Loaded {count:,} LEI-ISIN mappings")
    return count


def load_lei_bic_mappings(store: SqliteStore) -> int:
    """Load GLEIF LEI-BIC mappings."""
    bic_file = GLEIF_DIR / "lei-bic-20251226T000000.csv"
    
    if not bic_file.exists():
        logger.warning(f"LEI-BIC file not found: {bic_file}")
        return 0
    
    logger.info(f"Loading LEI-BIC mappings from {bic_file}")
    
    now = datetime.utcnow().isoformat()
    count = 0
    
    with store._get_connection() as conn:
        cursor = conn.cursor()
        
        with open(bic_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            batch = []
            for row in reader:
                lei = row.get('LEI', '').strip()
                bic = row.get('BIC', '').strip()
                
                if lei and bic:
                    batch.append((lei, bic, now))
                    count += 1
                    
                    if len(batch) >= 5000:
                        cursor.executemany(
                            "INSERT OR REPLACE INTO bic_mappings (lei, bic, created_at) VALUES (?, ?, ?)",
                            batch
                        )
                        batch = []
            
            if batch:
                cursor.executemany(
                    "INSERT OR REPLACE INTO bic_mappings (lei, bic, created_at) VALUES (?, ?, ?)",
                    batch
                )
        
        conn.commit()
    
    logger.info(f"✓ Loaded {count:,} LEI-BIC mappings")
    return count


def get_stats(store: SqliteStore) -> dict:
    """Get database statistics."""
    stats = {}
    
    with store._get_connection() as conn:
        cursor = conn.cursor()
        
        # Core tables
        cursor.execute("SELECT COUNT(*) FROM entities")
        stats['entities'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM securities")
        stats['securities'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM listings")
        stats['listings'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM claims")
        stats['claims'] = cursor.fetchone()[0]
        
        # Mapping tables
        try:
            cursor.execute("SELECT COUNT(*) FROM isin_mappings")
            stats['isin_mappings'] = cursor.fetchone()[0]
        except:
            stats['isin_mappings'] = 0
        
        try:
            cursor.execute("SELECT COUNT(*) FROM lei_mappings")
            stats['lei_mappings'] = cursor.fetchone()[0]
        except:
            stats['lei_mappings'] = 0
        
        try:
            cursor.execute("SELECT COUNT(*) FROM bic_mappings")
            stats['bic_mappings'] = cursor.fetchone()[0]
        except:
            stats['bic_mappings'] = 0
    
    return stats


def main():
    """Load all reference data into EntitySpine."""
    print("=" * 60)
    print("EntitySpine Reference Data Loader")
    print("=" * 60)
    
    # Set up shared database
    db_path = use_shared_db()
    print(f"\nDatabase: {db_path}")
    print()
    
    # Initialize store
    store = SqliteStore(str(db_path))
    store.initialize()
    
    # Ensure mapping tables exist
    ensure_identifier_tables(store)
    
    # Load data
    totals = {}
    
    print("\n--- Loading SEC Data ---")
    totals['sec_companies'] = load_sec_tickers(store)
    totals['exchange_updates'] = load_sec_tickers_exchange(store)
    
    print("\n--- Loading GLEIF Data ---")
    totals['lei_isin'] = load_lei_isin_mappings(store)
    totals['lei_bic'] = load_lei_bic_mappings(store)
    
    # Summary
    print("\n" + "=" * 60)
    print("LOAD COMPLETE")
    print("=" * 60)
    
    stats = get_stats(store)
    
    print(f"""
Database Statistics:
  Entities:          {stats['entities']:>10,}
  Securities:        {stats['securities']:>10,}
  Listings:          {stats['listings']:>10,}
  Claims:            {stats['claims']:>10,}
  ISIN Mappings:     {stats['isin_mappings']:>10,}
  BIC Mappings:      {stats['bic_mappings']:>10,}

Database Location: {db_path}
Database Size: {db_path.stat().st_size / 1024 / 1024:.1f} MB

You can now use EntitySpine in any app:

    from entityspine import ticker, cik, name
    
    ticker("0000320193")  # AAPL
    cik("NVDA")           # 0001045810
    name("AMZN")          # AMAZON COM INC
""")


if __name__ == "__main__":
    main()
