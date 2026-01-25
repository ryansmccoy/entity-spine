"""
Build a fresh authoritative entity database from GLEIF and SEC data.

This creates a clean entity graph using today's official data,
then validates historical vendor data against it.
"""
import csv
import json
import sqlite3
from pathlib import Path
from datetime import datetime
from collections import defaultdict

DATA_DIR = Path(__file__).parent.parent / "entityspine_data"
DB_PATH = DATA_DIR / "authoritative.db"


def create_database():
    """Create fresh SQLite database."""
    if DB_PATH.exists():
        print(f"Removing existing database: {DB_PATH}")
        DB_PATH.unlink()
    
    conn = sqlite3.connect(str(DB_PATH))
    
    # Entities table
    conn.execute("""
        CREATE TABLE entities (
            lei TEXT PRIMARY KEY,
            legal_name TEXT NOT NULL,
            jurisdiction TEXT,
            entity_status TEXT,
            entity_category TEXT,
            legal_address_city TEXT,
            legal_address_country TEXT,
            registration_authority_id TEXT,
            registration_authority_entity_id TEXT,
            created_at TEXT NOT NULL,
            source TEXT NOT NULL
        )
    """)
    
    # Identifiers table (LEI -> other IDs)
    conn.execute("""
        CREATE TABLE identifiers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lei TEXT NOT NULL,
            scheme TEXT NOT NULL,
            value TEXT NOT NULL,
            source TEXT NOT NULL,
            confidence REAL DEFAULT 1.0,
            created_at TEXT NOT NULL,
            FOREIGN KEY (lei) REFERENCES entities(lei),
            UNIQUE(lei, scheme, value)
        )
    """)
    
    # SEC data table
    conn.execute("""
        CREATE TABLE sec_companies (
            cik INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            ticker TEXT,
            exchange TEXT,
            created_at TEXT NOT NULL
        )
    """)
    
    # Validation results
    conn.execute("""
        CREATE TABLE validation_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lei TEXT,
            source TEXT NOT NULL,
            check_type TEXT NOT NULL,
            status TEXT NOT NULL,
            message TEXT,
            created_at TEXT NOT NULL
        )
    """)
    
    # Indexes
    conn.execute("CREATE INDEX idx_identifiers_lei ON identifiers(lei)")
    conn.execute("CREATE INDEX idx_identifiers_scheme_value ON identifiers(scheme, value)")
    conn.execute("CREATE INDEX idx_sec_ticker ON sec_companies(ticker)")
    
    conn.commit()
    return conn


def load_gleif_entities(conn):
    """Load entities from GLEIF full LEI file."""
    print("\n" + "=" * 60)
    print("Loading GLEIF LEI entities...")
    print("=" * 60)
    
    gleif_path = DATA_DIR / "gleif" / "gleif_lei_full.csv"
    if not gleif_path.exists():
        print(f"  File not found: {gleif_path}")
        return
    
    now = datetime.utcnow().isoformat()
    count = 0
    batch = []
    batch_size = 10000
    
    with open(gleif_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            lei = row.get('LEI', '').strip()
            if not lei:
                continue
            
            entity = (
                lei,
                row.get('Entity.LegalName', '').strip(),
                row.get('Entity.LegalJurisdiction', '').strip(),
                row.get('Entity.EntityStatus', '').strip(),
                row.get('Entity.EntityCategory', '').strip(),
                row.get('Entity.LegalAddress.City', '').strip(),
                row.get('Entity.LegalAddress.Country', '').strip(),
                row.get('Entity.RegistrationAuthority.RegistrationAuthorityID', '').strip(),
                row.get('Entity.RegistrationAuthority.RegistrationAuthorityEntityID', '').strip(),
                now,
                'gleif'
            )
            
            batch.append(entity)
            count += 1
            
            if len(batch) >= batch_size:
                conn.executemany("""
                    INSERT OR REPLACE INTO entities 
                    (lei, legal_name, jurisdiction, entity_status, entity_category,
                     legal_address_city, legal_address_country, 
                     registration_authority_id, registration_authority_entity_id,
                     created_at, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, batch)
                conn.commit()
                batch = []
                
                if count % 100000 == 0:
                    print(f"  Loaded {count:,} entities...")
    
    # Final batch
    if batch:
        conn.executemany("""
            INSERT OR REPLACE INTO entities 
            (lei, legal_name, jurisdiction, entity_status, entity_category,
             legal_address_city, legal_address_country, 
             registration_authority_id, registration_authority_entity_id,
             created_at, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, batch)
        conn.commit()
    
    print(f"  Loaded {count:,} GLEIF entities")


def load_gleif_isin_mappings(conn):
    """Load ISIN-LEI mappings from GLEIF."""
    print("\n" + "=" * 60)
    print("Loading GLEIF ISIN-LEI mappings...")
    print("=" * 60)
    
    isin_path = DATA_DIR / "gleif" / "lei-isin-20260129T081545.csv"
    if not isin_path.exists():
        print(f"  File not found: {isin_path}")
        return
    
    now = datetime.utcnow().isoformat()
    count = 0
    batch = []
    batch_size = 50000
    
    with open(isin_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            lei = row.get('LEI', '').strip()
            isin = row.get('ISIN', '').strip()
            
            if not lei or not isin:
                continue
            
            batch.append((lei, 'isin', isin, 'gleif', 1.0, now))
            count += 1
            
            if len(batch) >= batch_size:
                conn.executemany("""
                    INSERT OR IGNORE INTO identifiers 
                    (lei, scheme, value, source, confidence, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, batch)
                conn.commit()
                batch = []
                
                if count % 500000 == 0:
                    print(f"  Loaded {count:,} ISIN mappings...")
    
    if batch:
        conn.executemany("""
            INSERT OR IGNORE INTO identifiers 
            (lei, scheme, value, source, confidence, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, batch)
        conn.commit()
    
    print(f"  Loaded {count:,} ISIN-LEI mappings")


def load_gleif_bic_mappings(conn):
    """Load BIC-LEI mappings from GLEIF."""
    print("\n" + "=" * 60)
    print("Loading GLEIF BIC-LEI mappings...")
    print("=" * 60)
    
    bic_files = list((DATA_DIR / "gleif").glob("lei-bic*.csv"))
    if not bic_files:
        print("  No BIC-LEI files found")
        return
    
    now = datetime.utcnow().isoformat()
    count = 0
    
    for bic_path in bic_files:
        with open(bic_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            batch = []
            for row in reader:
                lei = row.get('LEI', '').strip()
                bic = row.get('BIC', '').strip()
                
                if not lei or not bic:
                    continue
                
                batch.append((lei, 'bic', bic, 'gleif', 1.0, now))
                count += 1
            
            if batch:
                conn.executemany("""
                    INSERT OR IGNORE INTO identifiers 
                    (lei, scheme, value, source, confidence, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, batch)
                conn.commit()
    
    print(f"  Loaded {count:,} BIC-LEI mappings")


def load_sec_companies(conn):
    """Load SEC company data."""
    print("\n" + "=" * 60)
    print("Loading SEC company data...")
    print("=" * 60)
    
    sec_path = DATA_DIR / "bulk_reference" / "sec_company_tickers_exchange.json"
    if not sec_path.exists():
        print(f"  File not found: {sec_path}")
        return
    
    with open(sec_path, 'r') as f:
        data = json.load(f)
    
    now = datetime.utcnow().isoformat()
    
    # Format: {"fields": ["cik", "name", "ticker", "exchange"], "data": [[cik, name, ticker, exchange], ...]}
    entries = data.get('data', [])
    
    batch = []
    for entry in entries:
        if len(entry) >= 4:
            cik, name, ticker, exchange = entry[:4]
            batch.append((cik, name, ticker, exchange, now))
    
    conn.executemany("""
        INSERT OR REPLACE INTO sec_companies 
        (cik, name, ticker, exchange, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, batch)
    conn.commit()
    
    print(f"  Loaded {len(batch):,} SEC companies")


def validate_thomson_data(conn):
    """Validate Thomson data against GLEIF."""
    print("\n" + "=" * 60)
    print("Validating Thomson data against GLEIF...")
    print("=" * 60)
    
    # Connect to the old database
    old_db_path = DATA_DIR / "linked_load.db"
    if not old_db_path.exists():
        print(f"  Old database not found: {old_db_path}")
        return
    
    old_conn = sqlite3.connect(str(old_db_path))
    
    # Get Thomson LEIs
    cursor = old_conn.execute("""
        SELECT DISTINCT c.value as lei, e.primary_name
        FROM claims c
        JOIN entities e ON c.entity_id = e.entity_id
        WHERE c.scheme = 'lei' AND e.source_system = 'openpermid'
    """)
    
    thomson_data = list(cursor)
    print(f"  Thomson entities with LEI: {len(thomson_data):,}")
    
    # Check against GLEIF
    now = datetime.utcnow().isoformat()
    valid = 0
    invalid = 0
    name_mismatch = 0
    
    for lei, thomson_name in thomson_data:
        # Check if LEI exists in GLEIF
        gleif_row = conn.execute(
            "SELECT legal_name, entity_status FROM entities WHERE lei = ?",
            (lei,)
        ).fetchone()
        
        if gleif_row:
            valid += 1
            gleif_name, status = gleif_row
            
            # Check for name similarity
            if thomson_name and gleif_name:
                # Simple name check - first word match
                thomson_first = thomson_name.split()[0].upper() if thomson_name else ''
                gleif_first = gleif_name.split()[0].upper() if gleif_name else ''
                
                if thomson_first != gleif_first and len(thomson_first) > 2:
                    name_mismatch += 1
                    if name_mismatch <= 5:
                        print(f"    Name mismatch: Thomson='{thomson_name}' vs GLEIF='{gleif_name}'")
        else:
            invalid += 1
            if invalid <= 5:
                print(f"    Invalid LEI (not in GLEIF): {lei} - {thomson_name}")
    
    # Record validation results
    conn.execute("""
        INSERT INTO validation_results (lei, source, check_type, status, message, created_at)
        VALUES (NULL, 'thomson', 'lei_validation', 'complete', ?, ?)
    """, (f"Valid: {valid}, Invalid: {invalid}, Name mismatches: {name_mismatch}", now))
    conn.commit()
    
    print(f"\n  Results:")
    print(f"    Valid LEIs (in GLEIF): {valid:,} ({valid*100/len(thomson_data):.1f}%)")
    print(f"    Invalid LEIs (not in GLEIF): {invalid:,}")
    print(f"    Name mismatches: {name_mismatch:,}")
    
    old_conn.close()


def print_summary(conn):
    """Print database summary."""
    print("\n" + "=" * 60)
    print("AUTHORITATIVE DATABASE SUMMARY")
    print("=" * 60)
    
    entity_count = conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
    isin_count = conn.execute("SELECT COUNT(*) FROM identifiers WHERE scheme = 'isin'").fetchone()[0]
    bic_count = conn.execute("SELECT COUNT(*) FROM identifiers WHERE scheme = 'bic'").fetchone()[0]
    sec_count = conn.execute("SELECT COUNT(*) FROM sec_companies").fetchone()[0]
    
    print(f"\n  Entities (from GLEIF): {entity_count:,}")
    print(f"  ISIN mappings: {isin_count:,}")
    print(f"  BIC mappings: {bic_count:,}")
    print(f"  SEC companies: {sec_count:,}")
    
    # Check NVIDIA
    print("\n  NVIDIA check:")
    nvidia = conn.execute(
        "SELECT lei, legal_name, jurisdiction FROM entities WHERE legal_name LIKE '%NVIDIA%' LIMIT 3"
    ).fetchall()
    for row in nvidia:
        print(f"    LEI: {row[0]}")
        print(f"    Name: {row[1]}")
        print(f"    Jurisdiction: {row[2]}")
        
        # Get ISINs
        isins = conn.execute(
            "SELECT value FROM identifiers WHERE lei = ? AND scheme = 'isin'",
            (row[0],)
        ).fetchall()
        if isins:
            print(f"    ISINs: {[i[0] for i in isins[:5]]}")
    
    # Check SEC ticker
    sec_nvidia = conn.execute(
        "SELECT * FROM sec_companies WHERE ticker = 'NVDA'"
    ).fetchone()
    if sec_nvidia:
        print(f"\n  SEC NVIDIA:")
        print(f"    CIK: {sec_nvidia[0]}")
        print(f"    Name: {sec_nvidia[1]}")
        print(f"    Ticker: {sec_nvidia[2]}")
        print(f"    Exchange: {sec_nvidia[3]}")
    
    print(f"\n  Database saved to: {DB_PATH}")


def main():
    print("=" * 60)
    print("Building Authoritative Entity Database")
    print("=" * 60)
    
    conn = create_database()
    
    load_gleif_entities(conn)
    load_gleif_isin_mappings(conn)
    load_gleif_bic_mappings(conn)
    load_sec_companies(conn)
    
    validate_thomson_data(conn)
    
    print_summary(conn)
    
    conn.close()


if __name__ == "__main__":
    main()
