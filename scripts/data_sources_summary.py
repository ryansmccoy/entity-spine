"""
Summary of available bulk data for entity mapping.

This creates a unified view of all available data sources and their linking potential.
"""
import csv
import json
import sqlite3
from pathlib import Path
from collections import Counter

DATA_DIR = Path(__file__).parent.parent / "entityspine_data"


def analyze_data_sources():
    """Summarize all available data sources."""
    
    print("=" * 70)
    print("BULK DATA SOURCES INVENTORY")
    print("=" * 70)
    
    sources = {}
    
    # 1. GLEIF ISIN-LEI (fresh, authoritative)
    isin_lei_path = DATA_DIR / "gleif" / "lei-isin-20260129T081545.csv"
    if isin_lei_path.exists():
        with open(isin_lei_path, 'r') as f:
            lines = sum(1 for _ in f) - 1
        sources['gleif_isin_lei'] = {
            'file': str(isin_lei_path),
            'records': lines,
            'date': '2026-01-29',
            'freshness': 'TODAY',
            'identifiers': ['LEI', 'ISIN'],
            'trust': 'HIGH - Official GLEIF mapping'
        }
    
    # 2. GLEIF BIC-LEI (fresh, authoritative)
    bic_lei_files = list((DATA_DIR / "gleif").glob("lei-bic*.csv"))
    if bic_lei_files:
        f = bic_lei_files[0]
        with open(f, 'r') as fh:
            lines = sum(1 for _ in fh) - 1
        sources['gleif_bic_lei'] = {
            'file': str(f),
            'records': lines,
            'date': '2025-12-26',
            'freshness': '~1 month old',
            'identifiers': ['LEI', 'BIC'],
            'trust': 'HIGH - Official GLEIF mapping'
        }
    
    # 3. GLEIF Full LEI (fresh, authoritative)
    lei_full_path = DATA_DIR / "gleif" / "gleif_lei_full.csv"
    if lei_full_path.exists():
        # Don't count all 3M lines, just estimate from file size
        size_mb = lei_full_path.stat().st_size / 1024 / 1024
        sources['gleif_lei_full'] = {
            'file': str(lei_full_path),
            'records': 3_194_327,
            'size_mb': round(size_mb),
            'date': '2026-01-29',
            'freshness': 'TODAY',
            'identifiers': ['LEI', 'Legal Name', 'Addresses', 'Jurisdiction', 'Registration Authority ID'],
            'trust': 'HIGH - Official GLEIF golden copy'
        }
    
    # 4. SEC Company Tickers (fresh, authoritative for US public)
    sec_path = DATA_DIR / "bulk_reference" / "sec_company_tickers.json"
    if sec_path.exists():
        with open(sec_path, 'r') as f:
            data = json.load(f)
        sources['sec_company_tickers'] = {
            'file': str(sec_path),
            'records': len(data),
            'date': '2026-01-29',
            'freshness': 'TODAY',
            'identifiers': ['CIK', 'Ticker', 'Company Name'],
            'trust': 'HIGH - Official SEC data'
        }
    
    # 5. SEC Company Tickers with Exchange
    sec_exchange_path = DATA_DIR / "bulk_reference" / "sec_company_tickers_exchange.json"
    if sec_exchange_path.exists():
        with open(sec_exchange_path, 'r') as f:
            data = json.load(f)
        sources['sec_company_tickers_exchange'] = {
            'file': str(sec_exchange_path),
            'records': len(data.get('data', [])),
            'date': '2026-01-29',
            'freshness': 'TODAY',
            'identifiers': ['CIK', 'Ticker', 'Company Name', 'Exchange'],
            'trust': 'HIGH - Official SEC data'
        }
    
    # 6. Your Thomson OpenPermID (older vendor data)
    db_path = DATA_DIR / "linked_load.db"
    if db_path.exists():
        conn = sqlite3.connect(str(db_path))
        
        thomson_count = conn.execute(
            "SELECT COUNT(*) FROM entities WHERE source_system = 'openpermid'"
        ).fetchone()[0]
        
        thomson_lei_count = conn.execute(
            "SELECT COUNT(DISTINCT value) FROM claims WHERE scheme = 'lei'"
        ).fetchone()[0]
        
        sources['thomson_openpermid'] = {
            'file': str(db_path),
            'records': thomson_count,
            'unique_leis': thomson_lei_count,
            'date': '~2023-2024',
            'freshness': '2-3 years old',
            'identifiers': ['PermID', 'LEI', 'Company Name'],
            'trust': 'MEDIUM - Comprehensive but older'
        }
        
        # 7. Your Bloomberg data
        bloomberg_count = conn.execute(
            "SELECT COUNT(*) FROM entities WHERE source_system = 'bloomberg'"
        ).fetchone()[0]
        
        bloomberg_figi_count = conn.execute(
            "SELECT COUNT(DISTINCT value) FROM claims WHERE scheme = 'figi'"
        ).fetchone()[0]
        
        sources['bloomberg'] = {
            'file': str(db_path),
            'records': bloomberg_count,
            'unique_figis': bloomberg_figi_count,
            'date': '~2016',
            'freshness': '~10 years old',
            'identifiers': ['FIGI', 'Company ID', 'Name'],
            'trust': 'LOW for current data - Good for historical'
        }
        
        conn.close()
    
    # 8. Identifier Bridge (derived)
    bridge_path = DATA_DIR / "identifier_bridge.csv"
    if bridge_path.exists():
        with open(bridge_path, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        has_isin = sum(1 for r in rows if r.get('isin'))
        has_cusip = sum(1 for r in rows if r.get('cusip'))
        has_figi = sum(1 for r in rows if r.get('bloomberg_figi'))
        
        sources['identifier_bridge'] = {
            'file': str(bridge_path),
            'records': len(rows),
            'has_isin': has_isin,
            'has_cusip': has_cusip,
            'has_bloomberg_figi': has_figi,
            'date': 'Mixed (FactSet ~2015-2016, Bloomberg ~2016)',
            'freshness': '~10 years old',
            'identifiers': ['ISIN', 'CUSIP', 'SEDOL', 'FactSet IDs', 'Bloomberg FIGI'],
            'trust': 'LOW for current - Good for historical cross-reference'
        }
    
    # Print summary
    for name, info in sources.items():
        print(f"\n{'─' * 70}")
        print(f"📁 {name.upper()}")
        print(f"   File: {info['file']}")
        print(f"   Records: {info['records']:,}")
        print(f"   Date: {info.get('date', 'Unknown')}")
        print(f"   Freshness: {info.get('freshness', 'Unknown')}")
        print(f"   Identifiers: {', '.join(info.get('identifiers', []))}")
        print(f"   Trust Level: {info.get('trust', 'Unknown')}")
    
    return sources


def recommend_linking_strategy():
    """Recommend how to use the data."""
    
    print("\n" + "=" * 70)
    print("RECOMMENDED LINKING STRATEGY")
    print("=" * 70)
    
    print("""
┌─────────────────────────────────────────────────────────────────────┐
│                    DATA TRUST HIERARCHY                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  TIER 1 (Ground Truth - Use these as authoritative):               │
│  ─────────────────────────────────────────────────────              │
│  • SEC CIK/Ticker → Official US public company identifiers         │
│  • GLEIF LEI → Official global entity identifiers                  │
│  • GLEIF ISIN-LEI → Official mapping (7.8M records)                │
│                                                                     │
│  TIER 2 (Cross-Reference - Use for enrichment):                    │
│  ─────────────────────────────────────────────────────              │
│  • GLEIF BIC-LEI → Bank identifiers                                │
│  • Thomson OpenPermID → Historical data, many entities             │
│                                                                     │
│  TIER 3 (Historical Reference - Use with caution):                 │
│  ─────────────────────────────────────────────────────              │
│  • Bloomberg FIGI data (~2016)                                     │
│  • FactSet data (~2015-2016)                                       │
│  • Your identifier bridge (derived from above)                     │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

RECOMMENDED APPROACH:
─────────────────────

1. START WITH FRESH GLEIF DATA (Today's data):
   • Load 3.2M LEI records as entity foundation
   • Use ISIN-LEI mapping (7.8M) for securities linking
   • Use BIC-LEI mapping (39K) for bank identification

2. ENRICH WITH SEC DATA (Today's data):
   • Add CIK/Ticker for 10K+ US public companies
   • Use SEC as ground truth for ticker symbols

3. CROSS-REFERENCE WITH YOUR DATA (With validation):
   • Thomson has 1.5M unique LEIs - match to GLEIF for validation
   • Only use Thomson data where LEI matches GLEIF
   • Flag any Thomson data that conflicts with GLEIF

4. USE HISTORICAL DATA FOR CONTEXT:
   • Bloomberg/FactSet data is useful for:
     - Historical ISIN/CUSIP/FIGI mappings
     - Identifying entities that may have changed names
     - Cross-checking identifier consistency
   • DO NOT use for current entity status/names

VALIDATION RULES:
─────────────────

✓ TRUST if: LEI matches across GLEIF + Thomson
✓ TRUST if: CIK matches SEC data
✓ TRUST if: ISIN verified via GLEIF ISIN-LEI

⚠ WARN if: Thomson data conflicts with GLEIF
⚠ WARN if: Bloomberg/FactSet has different name for same identifier
⚠ WARN if: Entity appears inactive in GLEIF but active in old data

✗ REJECT if: LEI not found in GLEIF (may be invalid/expired)
✗ REJECT if: Multiple conflicting identifiers from old sources
""")


def main():
    sources = analyze_data_sources()
    recommend_linking_strategy()
    
    # Quick stats
    print("\n" + "=" * 70)
    print("QUICK STATS")
    print("=" * 70)
    
    total_fresh = 0
    total_historical = 0
    
    for name, info in sources.items():
        if 'TODAY' in info.get('freshness', '') or '2026' in info.get('date', ''):
            total_fresh += info.get('records', 0)
        else:
            total_historical += info.get('records', 0)
    
    print(f"\n  Fresh data (today): {total_fresh:,} records")
    print(f"  Historical data: {total_historical:,} records")
    print(f"\n  Recommendation: Build entity graph from GLEIF/SEC first,")
    print(f"                  then augment with validated historical data.")


if __name__ == "__main__":
    main()
