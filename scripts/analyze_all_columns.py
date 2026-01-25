"""
Summary of useful columns across all data sources for entity enrichment.

This analyzes what columns can be used to enrich entities once linked.
"""
import pandas as pd
import json
from pathlib import Path

DATA_DIR = Path("B:/github/py-sec-edgar/data")

def analyze_factset_public():
    """Analyze FactSet Public Companies Excel (65k rows)."""
    print("=" * 70)
    print("FACTSET PUBLIC COMPANIES EXCEL (65k public companies)")
    print("=" * 70)
    
    df = pd.read_excel(DATA_DIR / "FF_PUBLIC_COMPANIES_EXPORT_GLOBAL_IDENTIFIERS_NEW ALL.xlsx", nrows=100)
    
    # Categorize columns
    identifiers = []
    geography = []
    industry = []
    financials = []
    descriptive = []
    dates = []
    other = []
    
    for col in df.columns:
        col_lower = col.lower()
        sample = df[col].iloc[0] if pd.notna(df[col].iloc[0]) else None
        
        if any(x in col_lower for x in ['isin', 'cusip', 'sedol', 'ticker', 'symbol', 'entityid', 'permid', 'perm.sec']):
            identifiers.append((col, sample))
        elif any(x in col_lower for x in ['country', 'region', 'nation', 'domicile', 'iso']):
            geography.append((col, sample))
        elif any(x in col_lower for x in ['sic', 'naics', 'gics', 'sector', 'industry', 'icb']):
            industry.append((col, sample))
        elif any(x in col_lower for x in ['mktval', 'sales', 'shares', 'revenue', 'value', 'currency', 'curr']):
            financials.append((col, sample))
        elif any(x in col_lower for x in ['name', 'desc', 'type', 'exchange', 'listing', 'exch']):
            descriptive.append((col, sample))
        elif any(x in col_lower for x in ['date', 'first']):
            dates.append((col, sample))
        else:
            other.append((col, sample))
    
    print("\n📌 IDENTIFIERS (for linking):")
    for col, sample in identifiers:
        print(f"  • {col}: {str(sample)[:40]}")
    
    print("\n🌍 GEOGRAPHY:")
    for col, sample in geography:
        print(f"  • {col}: {str(sample)[:40]}")
    
    print("\n🏭 INDUSTRY CLASSIFICATION:")
    for col, sample in industry:
        print(f"  • {col}: {str(sample)[:40]}")
    
    print("\n💰 FINANCIALS (historical):")
    for col, sample in financials[:10]:
        print(f"  • {col}: {str(sample)[:40]}")
    
    print("\n📝 DESCRIPTIVE:")
    for col, sample in descriptive[:10]:
        print(f"  • {col}: {str(sample)[:40]}")
    
    print("\n📅 DATES:")
    for col, sample in dates:
        print(f"  • {col}: {str(sample)[:40]}")
    
    return df


def analyze_factset_global():
    """Analyze FactSet Global Identifiers CSV (303k rows)."""
    print("\n" + "=" * 70)
    print("FACTSET GLOBAL IDENTIFIERS CSV (303k entities)")
    print("=" * 70)
    
    df = pd.read_csv(DATA_DIR / "ff_global_identifiers.csv", nrows=100, encoding='latin-1')
    
    print(f"\nColumns ({len(df.columns)}):")
    for col in df.columns:
        sample = df[col].iloc[0] if pd.notna(df[col].iloc[0]) else "(null)"
        print(f"  • {col.strip()}: {str(sample)[:50]}")
    
    return df


def analyze_bloomberg():
    """Analyze Bloomberg pub/priv CSV."""
    print("\n" + "=" * 70)
    print("BLOOMBERG PUB/PRIV CSV")
    print("=" * 70)
    
    df = pd.read_csv(DATA_DIR / "bb_pubpriv_20150101.csv", nrows=100, encoding='latin-1')
    
    print(f"\nColumns ({len(df.columns)}):")
    for col in df.columns:
        sample = df[col].iloc[0] if pd.notna(df[col].iloc[0]) else "(null)"
        print(f"  • {col}: {str(sample)[:50]}")
    
    # Count non-null ISINs
    full_df = pd.read_csv(DATA_DIR / "bb_pubpriv_20150101.csv", encoding='latin-1')
    has_isin = full_df['ISIN'].notna() & (full_df['ISIN'] != '--')
    print(f"\nRows with ISIN: {has_isin.sum():,} / {len(full_df):,}")
    
    return df


def analyze_sec_bulk():
    """Analyze SEC bulk data we downloaded."""
    print("\n" + "=" * 70)
    print("SEC BULK DATA (downloaded today)")
    print("=" * 70)
    
    sec_path = Path("B:/github/py-sec-edgar/entityspine/entityspine_data/bulk_reference/sec_company_tickers_exchange.json")
    if sec_path.exists():
        with open(sec_path, 'r') as f:
            data = json.load(f)
        
        print(f"\nFields: {data.get('fields', [])}")
        print(f"Total companies: {len(data.get('data', []))}")
        print("\nSample:")
        for entry in data['data'][:5]:
            print(f"  {entry}")
    
    # Also check GLEIF
    print("\n" + "=" * 70)
    print("GLEIF FULL LEI (downloaded today)")
    print("=" * 70)
    
    gleif_path = Path("B:/github/py-sec-edgar/entityspine/entityspine_data/gleif/gleif_lei_full.csv")
    if gleif_path.exists():
        # Just read headers
        with open(gleif_path, 'r', encoding='utf-8') as f:
            header = f.readline().strip().split(',')
        
        # Key columns
        key_cols = [h for h in header if any(x in h for x in ['LEI', 'LegalName', 'Jurisdiction', 'Country', 'City', 'Status', 'Category', 'SIC'])]
        print(f"\nKey columns for enrichment:")
        for col in key_cols[:20]:
            print(f"  • {col}")


def summarize_useful_columns():
    """Create a summary of the most useful columns for entity enrichment."""
    print("\n" + "=" * 70)
    print("SUMMARY: RECOMMENDED COLUMNS FOR ENTITY ENRICHMENT")
    print("=" * 70)
    
    print("""
┌─────────────────────────────────────────────────────────────────────┐
│                    COLUMNS BY PURPOSE                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  🔗 LINKING IDENTIFIERS (use these to connect sources):            │
│  ─────────────────────────────────────────────────────────          │
│  • ISIN (12-char) - FactSet Excel has full ISINs                   │
│  • CUSIP (9-char with check digit)                                 │
│  • SEDOL (7-char with check digit)                                 │
│  • LEI (20-char) - From GLEIF, Thomson                             │
│  • CIK - From SEC (10,317 companies)                               │
│  • FIGI - From Bloomberg                                           │
│  • FactSet EntityID (e.g., 072RVT-E)                               │
│  • FactSet Perm.Sec.ID (e.g., SRCT6H-S-US)                         │
│                                                                     │
│  🏢 ENTITY ATTRIBUTES (enrich after linking):                      │
│  ─────────────────────────────────────────────────────────          │
│  • Company Name / Legal Name                                        │
│  • Business Description (BusDesc)                                   │
│  • Entity Type (C=Corporation, etc.)                                │
│  • Entity Status (Active/Inactive)                                  │
│                                                                     │
│  🌍 GEOGRAPHY:                                                      │
│  ─────────────────────────────────────────────────────────          │
│  • DomicileCountryIso2 / DomicileCountryIso3                       │
│  • LegalJurisdiction (e.g., US-DE)                                 │
│  • Legal Address (City, Country)                                    │
│  • Headquarters Address                                             │
│                                                                     │
│  🏭 INDUSTRY CLASSIFICATION:                                        │
│  ─────────────────────────────────────────────────────────          │
│  • PrimarySICCode / PrimarySICName                                 │
│  • EntitySICDivFull / EntitySICMajGrpFull / EntitySICIndFull       │
│  • EntityNAICSIndNatlFull (6-digit NAICS)                          │
│  • GICS Sector/Industry                                            │
│  • FactSetEconSector / FactSetInd                                  │
│                                                                     │
│  📈 MARKET DATA (historical - use with caution):                   │
│  ─────────────────────────────────────────────────────────          │
│  • ListingExchange / TradingExchange                               │
│  • Ticker Symbol (changes over time!)                              │
│  • Security Type (SHARE, etc.)                                     │
│  • Date(FIRST) - IPO/listing date                                  │
│                                                                     │
│  ⚠️  DO NOT USE (stale/historical):                                │
│  ─────────────────────────────────────────────────────────          │
│  • Market Value (MktValCo) - very outdated                         │
│  • Revenue/Sales - point-in-time historical                        │
│  • EPS - point-in-time historical                                  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

LINKING CHAIN:
─────────────────

  SEC (CIK + Name)
       ↓ (name match)
  GLEIF (LEI + Legal Name + Jurisdiction + SIC)
       ↓ (LEI)
  Thomson OpenPermID (LEI + PermID + Name)
       ↓ (ISIN via GLEIF ISIN-LEI mapping)
  FactSet (ISIN + EntityID + CUSIP + SEDOL + Industry)
       ↓ (CUSIP/ISIN)
  Bloomberg (FIGI + ISIN + Name)

RECOMMENDED ENTITY ATTRIBUTES TO STORE:
────────────────────────────────────────

1. PRIMARY (always populate):
   - Legal Name (from GLEIF - authoritative)
   - LEI (if available)
   - CIK (for US public companies)
   - Jurisdiction (from GLEIF)

2. SECONDARY (populate if available):
   - SIC Code + Name
   - NAICS Code + Name
   - Business Description
   - Headquarters Country/City

3. IDENTIFIERS (for cross-referencing):
   - ISIN (primary security)
   - CUSIP
   - SEDOL
   - FIGI
   - FactSet EntityID
   - Thomson PermID
""")


def main():
    pd.set_option('display.max_colwidth', 50)
    
    analyze_factset_public()
    analyze_factset_global()
    analyze_bloomberg()
    analyze_sec_bulk()
    summarize_useful_columns()


if __name__ == "__main__":
    main()
