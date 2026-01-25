"""
Create entity links using GLEIF ISIN-LEI mappings.

This script links Thomson (via LEI) <-> FactSet/Bloomberg (via ISIN) 
using GLEIF as the bridge.
"""
import sqlite3
import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path

DB_PATH = "entityspine_data/linked_load.db"
GLEIF_PATH = "entityspine_data/gleif/lei-isin-20260129T081545.csv"
BRIDGE_PATH = "entityspine_data/identifier_bridge.csv"


def load_gleif_mappings():
    """Load GLEIF ISIN-LEI bidirectional mappings."""
    lei_to_isins = defaultdict(set)
    isin_to_lei = {}
    
    print("Loading GLEIF ISIN-LEI mappings...")
    with open(GLEIF_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            lei = row['LEI']
            isin = row['ISIN']
            lei_to_isins[lei].add(isin)
            isin_to_lei[isin] = lei
    
    print(f"  Loaded {len(lei_to_isins):,} LEIs -> {len(isin_to_lei):,} ISINs")
    return lei_to_isins, isin_to_lei


def load_identifier_bridge():
    """Load the identifier bridge with FactSet and Bloomberg data."""
    bridge_by_isin = {}
    
    print("Loading identifier bridge...")
    with open(BRIDGE_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            isin = row.get('isin', '')
            if isin:
                bridge_by_isin[isin] = row
    
    print(f"  Loaded {len(bridge_by_isin):,} bridge entries with ISIN")
    return bridge_by_isin


def get_entity_by_lei(conn, lei):
    """Find entity in DB by LEI."""
    cursor = conn.execute("""
        SELECT e.entity_id, e.primary_name, e.source_system
        FROM entities e
        JOIN claims c ON e.entity_id = c.entity_id
        WHERE c.scheme = 'lei' AND c.value = ?
        LIMIT 1
    """, (lei,))
    return cursor.fetchone()


def get_entity_by_figi(conn, figi):
    """Find entity in DB by FIGI."""
    cursor = conn.execute("""
        SELECT e.entity_id, e.primary_name, e.source_system
        FROM entities e
        JOIN claims c ON e.entity_id = c.entity_id
        WHERE c.scheme = 'figi' AND c.value = ?
        LIMIT 1
    """, (figi,))
    return cursor.fetchone()


def create_entity_link(conn, entity_id_1, entity_id_2, link_type, confidence, reason):
    """Create a link between two entities."""
    link_id = f"link:{entity_id_1}:{entity_id_2}:{link_type}"
    
    # Check if link already exists
    cursor = conn.execute(
        "SELECT 1 FROM entity_links WHERE link_id = ?",
        (link_id,)
    )
    if cursor.fetchone():
        return False
    
    now = datetime.utcnow().isoformat()
    conn.execute("""
        INSERT INTO entity_links (link_id, entity_id_1, entity_id_2, link_type, confidence, reason, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (link_id, entity_id_1, entity_id_2, link_type, confidence, reason, now))
    
    return True


def ensure_links_table(conn):
    """Create entity_links table if it doesn't exist."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS entity_links (
            link_id TEXT PRIMARY KEY,
            entity_id_1 TEXT NOT NULL,
            entity_id_2 TEXT NOT NULL,
            link_type TEXT NOT NULL,
            confidence REAL DEFAULT 1.0,
            reason TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (entity_id_1) REFERENCES entities(entity_id),
            FOREIGN KEY (entity_id_2) REFERENCES entities(entity_id)
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_entity_links_1 ON entity_links(entity_id_1)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_entity_links_2 ON entity_links(entity_id_2)
    """)


def main():
    print("=" * 70)
    print("GLEIF-Based Entity Linking")
    print("=" * 70)
    
    # Load reference data
    lei_to_isins, isin_to_lei = load_gleif_mappings()
    bridge_by_isin = load_identifier_bridge()
    
    # Connect to database
    conn = sqlite3.connect(DB_PATH)
    ensure_links_table(conn)
    
    # Get existing link count
    link_count_before = conn.execute("SELECT COUNT(*) FROM entity_links").fetchone()[0]
    print(f"\nExisting links: {link_count_before:,}")
    
    # Statistics
    stats = {
        'isins_checked': 0,
        'lei_found': 0,
        'thomson_entity_found': 0,
        'bloomberg_figi_found': 0,
        'links_created': 0,
        'links_skipped_duplicate': 0,
    }
    
    print("\nCreating links...")
    
    # For each bridge entry with ISIN
    for isin, bridge_row in bridge_by_isin.items():
        stats['isins_checked'] += 1
        
        # Get LEI from GLEIF
        lei = isin_to_lei.get(isin)
        if not lei:
            continue
        stats['lei_found'] += 1
        
        # Find Thomson entity with this LEI
        thomson = get_entity_by_lei(conn, lei)
        if not thomson:
            continue
        stats['thomson_entity_found'] += 1
        
        thomson_id, thomson_name, thomson_source = thomson
        
        # Get Bloomberg FIGI from bridge
        bloomberg_figi = bridge_row.get('bloomberg_figi', '')
        if bloomberg_figi:
            # Find Bloomberg entity
            bloomberg = get_entity_by_figi(conn, bloomberg_figi)
            if bloomberg:
                stats['bloomberg_figi_found'] += 1
                bloomberg_id, bloomberg_name, bloomberg_source = bloomberg
                
                # Create link
                reason = f"GLEIF: LEI {lei} -> ISIN {isin} -> FIGI {bloomberg_figi}"
                if create_entity_link(conn, thomson_id, bloomberg_id, 'same_entity', 0.95, reason):
                    stats['links_created'] += 1
                    if stats['links_created'] <= 10:
                        print(f"  LINK: {thomson_name} ({thomson_source}) <-> {bloomberg_name} ({bloomberg_source})")
                else:
                    stats['links_skipped_duplicate'] += 1
    
    conn.commit()
    
    # Get final link count
    link_count_after = conn.execute("SELECT COUNT(*) FROM entity_links").fetchone()[0]
    
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)
    print(f"ISINs checked: {stats['isins_checked']:,}")
    print(f"LEIs found in GLEIF: {stats['lei_found']:,}")
    print(f"Thomson entities found: {stats['thomson_entity_found']:,}")
    print(f"Bloomberg entities found: {stats['bloomberg_figi_found']:,}")
    print(f"Links created: {stats['links_created']:,}")
    print(f"Links skipped (duplicate): {stats['links_skipped_duplicate']:,}")
    print(f"\nTotal links in DB: {link_count_after:,}")
    
    # Show sample linked entities
    print("\n" + "=" * 70)
    print("SAMPLE LINKED ENTITIES")
    print("=" * 70)
    
    cursor = conn.execute("""
        SELECT 
            el.link_id,
            e1.primary_name as name1, e1.source_system as source1,
            e2.primary_name as name2, e2.source_system as source2,
            el.reason
        FROM entity_links el
        JOIN entities e1 ON el.entity_id_1 = e1.entity_id
        JOIN entities e2 ON el.entity_id_2 = e2.entity_id
        LIMIT 10
    """)
    
    for row in cursor:
        print(f"\n{row[1]} ({row[2]}) <-> {row[3]} ({row[4]})")
        print(f"  Reason: {row[5][:80]}...")
    
    conn.close()


if __name__ == "__main__":
    main()
