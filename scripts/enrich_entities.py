"""
Build enriched entity database by linking all sources.

Uses the linking chain:
- SEC (CIK, Ticker) → name match → GLEIF (LEI)
- GLEIF LEI → ISIN mapping → FactSet (Industry, SIC, NAICS, BusDesc)
- All validated against fresh GLEIF data

Enrichment columns from FactSet:
- PrimarySICCode, PrimarySICName
- EntitySICDivFull, EntitySICMajGrpFull, EntitySICIndGrpFull, EntitySICIndFull
- EntityNAICSIndNatlFull
- FactSetEconSector, FactSetInd
- BusDesc (Business Description)
- DomicileCountryIso2
- EntityType
- Date(FIRST) - listing date
"""
import csv
import json
import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime
from collections import defaultdict

DATA_DIR = Path("B:/github/py-sec-edgar/data")
ENTITYSPINE_DIR = Path("B:/github/py-sec-edgar/entityspine/entityspine_data")


def load_gleif_isin_to_lei():
    """Load GLEIF ISIN → LEI mapping."""
    print("Loading GLEIF ISIN-LEI mappings...")
    isin_to_lei = {}
    
    with open(ENTITYSPINE_DIR / "gleif/lei-isin-20260129T081545.csv", 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            isin = row['ISIN']
            lei = row['LEI']
            isin_to_lei[isin] = lei
    
    print(f"  Loaded {len(isin_to_lei):,} ISIN → LEI mappings")
    return isin_to_lei


def load_factset_enrichment():
    """Load FactSet data for enrichment."""
    print("Loading FactSet Public Companies...")
    
    df = pd.read_excel(DATA_DIR / "FF_PUBLIC_COMPANIES_EXPORT_GLOBAL_IDENTIFIERS_NEW ALL.xlsx")
    print(f"  Loaded {len(df):,} rows")
    
    # Create dict by ISIN
    factset_by_isin = {}
    for _, row in df.iterrows():
        isin = row.get('ISIN') or row.get('ISINSymbol')
        if pd.isna(isin) or not isin:
            continue
        
        factset_by_isin[isin] = {
            'entity_id': row.get('EntityID'),
            'name': row.get('Company Name') or row.get('FECo InfoName'),
            'sic_code': row.get('PrimarySICCode'),
            'sic_name': row.get('PrimarySICName'),
            'sic_division': row.get('EntitySICDivFull'),
            'sic_major_group': row.get('EntitySICMajGrpFull'),
            'sic_industry_group': row.get('EntitySICIndGrpFull'),
            'sic_industry': row.get('EntitySICIndFull'),
            'naics_code': row.get('EntityNAICSIndNatlFull'),
            'factset_sector': row.get('FactSetEconSector'),
            'factset_industry': row.get('FactSetInd'),
            'gics_sector': row.get('MindShareGICSSectors'),
            'gics_industry': row.get('MindShareGICSIndustry'),
            'business_desc': row.get('BusDesc'),
            'country_iso2': row.get('DomicileCountryIso2'),
            'country_iso3': row.get('DomicileCountryIso3'),
            'entity_type': row.get('EntityType'),
            'listing_date': row.get('Date(FIRST)'),
            'listing_exchange': row.get('ListingExchng'),
            'cusip': row.get('CUSIP'),
            'sedol': row.get('SEDOL'),
        }
    
    print(f"  Indexed {len(factset_by_isin):,} by ISIN")
    return factset_by_isin


def load_sec_companies():
    """Load SEC company data."""
    print("Loading SEC companies...")
    
    with open(ENTITYSPINE_DIR / "bulk_reference/sec_company_tickers_exchange.json", 'r') as f:
        data = json.load(f)
    
    sec_companies = {}
    for entry in data['data']:
        cik, name, ticker, exchange = entry
        sec_companies[cik] = {
            'name': name,
            'ticker': ticker,
            'exchange': exchange
        }
    
    print(f"  Loaded {len(sec_companies):,} SEC companies")
    return sec_companies


def enrich_entities():
    """Main enrichment process."""
    print("=" * 70)
    print("ENTITY ENRICHMENT PROCESS")
    print("=" * 70)
    
    # Load reference data
    isin_to_lei = load_gleif_isin_to_lei()
    factset_by_isin = load_factset_enrichment()
    sec_companies = load_sec_companies()
    
    # Connect to authoritative DB
    conn = sqlite3.connect(str(ENTITYSPINE_DIR / "authoritative.db"))
    
    # Add enrichment columns if not exist
    try:
        conn.execute("ALTER TABLE entities ADD COLUMN sic_code TEXT")
        conn.execute("ALTER TABLE entities ADD COLUMN sic_name TEXT")
        conn.execute("ALTER TABLE entities ADD COLUMN naics_code TEXT")
        conn.execute("ALTER TABLE entities ADD COLUMN factset_sector TEXT")
        conn.execute("ALTER TABLE entities ADD COLUMN factset_industry TEXT")
        conn.execute("ALTER TABLE entities ADD COLUMN business_desc TEXT")
        conn.execute("ALTER TABLE entities ADD COLUMN sec_cik INTEGER")
        conn.execute("ALTER TABLE entities ADD COLUMN sec_ticker TEXT")
        conn.execute("ALTER TABLE entities ADD COLUMN factset_entity_id TEXT")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # Columns already exist
    
    # Step 1: Link via ISIN
    print("\n" + "=" * 70)
    print("Step 1: Enriching via ISIN → LEI → FactSet")
    print("=" * 70)
    
    enriched_via_isin = 0
    
    # Get all LEIs with ISINs
    for isin, lei in isin_to_lei.items():
        factset = factset_by_isin.get(isin)
        if not factset:
            continue
        
        # Check if LEI exists in our entities
        cursor = conn.execute("SELECT 1 FROM entities WHERE lei = ?", (lei,))
        if not cursor.fetchone():
            continue
        
        # Update with FactSet data
        conn.execute("""
            UPDATE entities SET
                sic_code = COALESCE(sic_code, ?),
                sic_name = COALESCE(sic_name, ?),
                naics_code = COALESCE(naics_code, ?),
                factset_sector = COALESCE(factset_sector, ?),
                factset_industry = COALESCE(factset_industry, ?),
                business_desc = COALESCE(business_desc, ?),
                factset_entity_id = COALESCE(factset_entity_id, ?)
            WHERE lei = ?
        """, (
            str(factset['sic_code']) if pd.notna(factset['sic_code']) else None,
            factset['sic_name'] if pd.notna(factset['sic_name']) else None,
            factset['naics_code'] if pd.notna(factset['naics_code']) else None,
            factset['factset_sector'] if pd.notna(factset['factset_sector']) else None,
            factset['factset_industry'] if pd.notna(factset['factset_industry']) else None,
            factset['business_desc'] if pd.notna(factset['business_desc']) else None,
            factset['entity_id'] if pd.notna(factset['entity_id']) else None,
            lei
        ))
        
        enriched_via_isin += 1
        if enriched_via_isin % 1000 == 0:
            print(f"  Enriched {enriched_via_isin:,} entities...")
            conn.commit()
    
    conn.commit()
    print(f"  Total enriched via ISIN: {enriched_via_isin:,}")
    
    # Step 2: Link SEC CIK via name matching
    print("\n" + "=" * 70)
    print("Step 2: Linking SEC CIK via name matching")
    print("=" * 70)
    
    import re
    
    def normalize_name(name):
        """Normalize company name for matching."""
        if not name:
            return ''
        name = name.upper()
        name = re.sub(r'[,.]', '', name)
        # Remove common suffixes (run twice to catch nested)
        for _ in range(2):
            name = re.sub(r'\s+(INC|CORP|CORPORATION|LLC|LP|LTD|LIMITED|CO|COMPANY|PLC|NV|SA|AG|SE|/DE/|\\DE\\)\s*$', '', name)
        name = re.sub(r'\s+', ' ', name).strip()
        return name
    
    # Build name index for SEC (both exact and normalized)
    sec_by_name = {}
    sec_by_norm = {}
    for cik, info in sec_companies.items():
        name = info['name']
        name_upper = name.upper().strip()
        sec_by_name[name_upper] = (cik, info['ticker'])
        
        norm = normalize_name(name)
        if norm:
            sec_by_norm[norm] = (cik, info['ticker'])
    
    linked_sec = 0
    
    cursor = conn.execute("SELECT lei, legal_name FROM entities WHERE legal_name IS NOT NULL")
    for lei, gleif_name in cursor:
        name_upper = gleif_name.upper().strip()
        
        # Try exact match first
        if name_upper in sec_by_name:
            cik, ticker = sec_by_name[name_upper]
            conn.execute("UPDATE entities SET sec_cik = ?, sec_ticker = ? WHERE lei = ?", (cik, ticker, lei))
            linked_sec += 1
        else:
            # Try normalized match
            norm = normalize_name(gleif_name)
            if norm in sec_by_norm:
                cik, ticker = sec_by_norm[norm]
                conn.execute("UPDATE entities SET sec_cik = ?, sec_ticker = ? WHERE lei = ?", (cik, ticker, lei))
                linked_sec += 1
    
    conn.commit()
    print(f"  Linked {linked_sec:,} entities to SEC CIK")
    
    # Summary
    print("\n" + "=" * 70)
    print("ENRICHMENT SUMMARY")
    print("=" * 70)
    
    stats = conn.execute("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN sic_code IS NOT NULL THEN 1 ELSE 0 END) as has_sic,
            SUM(CASE WHEN naics_code IS NOT NULL THEN 1 ELSE 0 END) as has_naics,
            SUM(CASE WHEN business_desc IS NOT NULL THEN 1 ELSE 0 END) as has_desc,
            SUM(CASE WHEN sec_cik IS NOT NULL THEN 1 ELSE 0 END) as has_cik,
            SUM(CASE WHEN factset_entity_id IS NOT NULL THEN 1 ELSE 0 END) as has_factset
        FROM entities
    """).fetchone()
    
    print(f"\n  Total entities: {stats[0]:,}")
    print(f"  With SIC code: {stats[1]:,}")
    print(f"  With NAICS code: {stats[2]:,}")
    print(f"  With business description: {stats[3]:,}")
    print(f"  With SEC CIK: {stats[4]:,}")
    print(f"  With FactSet EntityID: {stats[5]:,}")
    
    # Sample enriched entity
    print("\n" + "=" * 70)
    print("SAMPLE ENRICHED ENTITY (NVIDIA)")
    print("=" * 70)
    
    nvidia = conn.execute("""
        SELECT lei, legal_name, jurisdiction, sic_code, sic_name, naics_code,
               factset_sector, factset_industry, business_desc, sec_cik, sec_ticker, factset_entity_id
        FROM entities 
        WHERE legal_name LIKE '%NVIDIA CORP%'
        AND jurisdiction LIKE 'US%'
        LIMIT 1
    """).fetchone()
    
    if nvidia:
        print(f"  LEI: {nvidia[0]}")
        print(f"  Legal Name: {nvidia[1]}")
        print(f"  Jurisdiction: {nvidia[2]}")
        print(f"  SIC Code: {nvidia[3]}")
        print(f"  SIC Name: {nvidia[4]}")
        print(f"  NAICS Code: {nvidia[5]}")
        print(f"  FactSet Sector: {nvidia[6]}")
        print(f"  FactSet Industry: {nvidia[7]}")
        print(f"  Business Desc: {str(nvidia[8])[:80]}..." if nvidia[8] else "  Business Desc: None")
        print(f"  SEC CIK: {nvidia[9]}")
        print(f"  SEC Ticker: {nvidia[10]}")
        print(f"  FactSet EntityID: {nvidia[11]}")
    
    conn.close()


if __name__ == "__main__":
    enrich_entities()
