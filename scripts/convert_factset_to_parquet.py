#!/usr/bin/env python3
"""
Convert FactSet ff_combined.csv to logical Parquet files.

Splits the large CSV into logical groupings:
1. entities.parquet - Core entity information
2. financials.parquet - Income statement, balance sheet metrics
3. ratios.parquet - Financial ratios and margins
4. identifiers.parquet - IDs, tickers, SIC codes
5. metadata.parquet - Descriptions, URLs, dates

Also loads entities into SQLite store for querying.
"""

from __future__ import annotations

import time
from pathlib import Path

import pandas as pd

# Paths
FACTSET_CSV = Path("G:/FACTSET/ff_combined.csv")
OUTPUT_DIR = Path("b:/github/py-sec-edgar/entityspine/entityspine_data/factset")

# Column groupings
ENTITY_COLS = [
    'Identifier', 'Name', 'Country', 'City', 'State/Province',
    'Company Type', 'Year Founded', 'Number of Employees',
    'Ultimate Parent Name', 'Ultimate Parent Type',
]

IDENTIFIER_COLS = [
    'Identifier', 'Name', 'Stock Exchange', 
    'Primary SIC Industry', 'Primary SIC Industry Group', 'Primary SIC Major Group',
    'Primary NAICS Industry', 'Primary NAICS Industry Group', 'Primary NAICS Sector',
    'FactSet Industry', 'FactSet Sector',
]

FINANCIAL_COLS = [
    'Identifier', 'Name', 'Revenue', 'COGS', 'Gross Profit', 
    'EBIT', 'EBITDA', 'Net Income', 'Pretax Income',
    'Total Assets', 'Total Current Assets', 'Total Current Liabilities',
    'Total Debt', 'Long Term Debt', 'Short Term Debt',
    'Cash & ST Investments', 'Market Cap', 'Enterprise Value',
    'Common Shares Outstanding', 'Diluted Shares Outstanding',
    'Capital Expenditures', 'Free Cash Flow', 'Net Operating Cash Flow',
    'Interest Expense', 'Research & Development Expenses',
]

PER_SHARE_COLS = [
    'Identifier', 'Name',
    'EPS (Basic)', 'EPS (Diluted)', 'Book Value per Share',
    'Dividend Amount', 'Dividend Yield', 'Dividend Date',
]

RATIO_COLS = [
    'Identifier', 'Name',
    'Gross Income Margin', 'EBIT Margin', 'EBITDA Margin', 'Net Income Margin', 'Pretax Margin',
    'Return on Assets', 'Return on Equity', 'Return on Average Invested Capital',
    'Price to Earnings', 'Price to Book Value', 'Price to Sales', 'Price to Cash Flow',
    'Enterprise Value to EBIT', 'Enterprise Value to EBITDA', 'Enterprise Value to Sales',
    'Total Debt/EBITDA', 'Net Debt/EBITDA', 'EBITDA/Interest Expense',
    'Sales CAGR', 'EBIT CAGR', 'EBITDA CAGR', 'EPS CAGR', 'Net Income CAGR', 'Gross Profit CAGR',
]

METADATA_COLS = [
    'Identifier', 'Name', 'Website', 'Business Description',
    'Product Line', 'Web Description URL', 'Telephone Number',
    'Fiscal Year End', 'Reports Financials Publicly', 'In Registration',
]


def convert_to_parquet():
    """Convert ff_combined.csv to logical Parquet files."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    print(f"Reading CSV: {FACTSET_CSV}")
    print(f"File size: {FACTSET_CSV.stat().st_size / 1024 / 1024:.1f} MB")
    
    start = time.time()
    
    # Read CSV in chunks for memory efficiency
    chunk_size = 50000
    chunks = []
    
    print(f"Loading CSV in chunks of {chunk_size}...")
    for i, chunk in enumerate(pd.read_csv(
        FACTSET_CSV, 
        encoding='utf-8', 
        encoding_errors='replace',
        chunksize=chunk_size,
        low_memory=False,
    )):
        chunks.append(chunk)
        print(f"  Chunk {i+1}: {len(chunk)} rows")
    
    df = pd.concat(chunks, ignore_index=True)
    load_time = time.time() - start
    
    print(f"\nLoaded {len(df):,} rows x {len(df.columns)} columns in {load_time:.1f}s")
    print(f"Memory usage: {df.memory_usage(deep=True).sum() / 1024 / 1024:.1f} MB")
    
    # Clean column names (some have trailing spaces or duplicates)
    df.columns = df.columns.str.strip()
    
    # Get available columns (some may not exist)
    available_cols = set(df.columns)
    
    def filter_cols(cols):
        return [c for c in cols if c in available_cols]
    
    # Save each logical grouping
    groupings = [
        ('entities', ENTITY_COLS),
        ('identifiers', IDENTIFIER_COLS),
        ('financials', FINANCIAL_COLS),
        ('per_share', PER_SHARE_COLS),
        ('ratios', RATIO_COLS),
        ('metadata', METADATA_COLS),
    ]
    
    print("\nSaving Parquet files:")
    for name, cols in groupings:
        valid_cols = filter_cols(cols)
        if not valid_cols:
            print(f"  {name}: No valid columns found, skipping")
            continue
        
        subset = df[valid_cols].copy()
        output_path = OUTPUT_DIR / f"{name}.parquet"
        
        # Convert to appropriate types
        for col in subset.columns:
            if subset[col].dtype == 'object':
                # Keep as string
                subset[col] = subset[col].astype(str).replace('nan', '')
        
        subset.to_parquet(output_path, index=False, compression='snappy')
        file_size = output_path.stat().st_size / 1024 / 1024
        print(f"  {name}.parquet: {len(valid_cols)} cols, {file_size:.2f} MB")
    
    # Save full dataset too (for reference) - convert all columns to string to avoid type issues
    full_path = OUTPUT_DIR / "ff_combined_full.parquet"
    df_str = df.astype(str).replace('nan', '')
    df_str.to_parquet(full_path, index=False, compression='snappy')
    print(f"\n  ff_combined_full.parquet: {full_path.stat().st_size / 1024 / 1024:.1f} MB")
    
    total_time = time.time() - start
    print(f"\nTotal conversion time: {total_time:.1f}s")
    
    return df


def show_nvidia_entity(df: pd.DataFrame):
    """Show what NVIDIA looks like in the data."""
    print("\n" + "=" * 70)
    print(" NVIDIA Entity Analysis")
    print("=" * 70)
    
    nvidia = df[df['Name'].str.upper().str.contains('NVIDIA', na=False)]
    
    if nvidia.empty:
        print("NVIDIA not found in dataset")
        return
    
    row = nvidia.iloc[0]
    
    # Count filled vs empty
    filled = sum(1 for v in row if pd.notna(v) and str(v).strip() and str(v).strip() != '-')
    total = len(row)
    
    print(f"\nEntity: {row.get('Name', 'N/A')}")
    print(f"Identifier: {row.get('Identifier', 'N/A')}")
    print(f"Data completeness: {filled}/{total} fields ({100*filled/total:.1f}%)")
    
    print("\n--- Core Entity Fields ---")
    for col in ENTITY_COLS:
        if col in row.index:
            val = row[col]
            status = "[OK]" if pd.notna(val) and str(val).strip() and str(val).strip() != '-' else "[EMPTY]"
            print(f"  {status} {col}: {val}")
    
    print("\n--- Key Financials ---")
    key_fin = ['Revenue', 'EBITDA', 'Net Income', 'Market Cap', 'Enterprise Value', 'Total Assets']
    for col in key_fin:
        if col in row.index:
            val = row[col]
            status = "[OK]" if pd.notna(val) and str(val).strip() and str(val).strip() != '-' else "[EMPTY]"
            print(f"  {status} {col}: {val}")
    
    print("\n--- Identifiers ---")
    id_fields = ['Stock Exchange', 'Primary SIC Industry', 'FactSet Industry', 'FactSet Sector']
    for col in id_fields:
        if col in row.index:
            val = row[col]
            status = "[OK]" if pd.notna(val) and str(val).strip() and str(val).strip() != '-' else "[EMPTY]"
            print(f"  {status} {col}: {val}")
    
    # What would be mapped to EntitySpine
    print("\n--- EntitySpine Mapping ---")
    print("  Entity fields:")
    print(f"    primary_name     <- Name: {row.get('Name')}")
    print(f"    entity_id        <- 'factset:' + Identifier: factset:{row.get('Identifier')}")
    print(f"    jurisdiction     <- Country: {row.get('Country')}")
    print(f"    sic_code         <- Primary SIC Industry: {str(row.get('Primary SIC Industry', ''))[:10]}")
    print(f"    source_system    <- 'factset'")
    
    print("\n  Would create FinancialObservations for:")
    obs_fields = ['Revenue', 'EBITDA', 'EBIT', 'Net Income', 'Gross Profit', 'Market Cap', 'Enterprise Value']
    for col in obs_fields:
        if col in row.index:
            val = row[col]
            if pd.notna(val) and str(val).strip() and str(val).strip() != '-':
                print(f"    - {col}: {val}")
    
    print("\n  Missing from FactSet (would need other sources):")
    print("    - CIK (need SEC)")
    print("    - LEI (need GLEIF)")
    print("    - CUSIP/ISIN (need security master)")
    print("    - FIGI (need Bloomberg/OpenFIGI)")


def load_to_sqlite(df: pd.DataFrame):
    """Load entities into SQLite store."""
    import sys
    sys.path.insert(0, str(Path("b:/github/py-sec-edgar/entityspine/src")))
    
    from entityspine.domain import Entity, EntityType, EntityStatus, IdentifierClaim, IdentifierScheme, VendorNamespace
    from entityspine.stores import SqliteStore
    
    db_path = OUTPUT_DIR / "factset_entities.db"
    
    print("\n" + "=" * 70)
    print(f" Loading to SQLite: {db_path}")
    print("=" * 70)
    
    store = SqliteStore(db_path=str(db_path))
    store.initialize()
    
    start = time.time()
    saved = 0
    errors = 0
    
    for idx, row in df.iterrows():
        identifier = str(row.get('Identifier', '')).strip()
        name = str(row.get('Name', '')).strip()
        
        if not identifier or not name or identifier == 'nan' or name == 'nan':
            continue
        
        try:
            entity_id = f"factset:{identifier}"
            country = str(row.get('Country', '')).strip()
            if country == 'nan':
                country = None
            elif len(country) > 10:
                country = country[:2].upper()
            
            company_type = str(row.get('Company Type', '')).lower()
            if 'fund' in company_type:
                entity_type = EntityType.FUND
            elif 'trust' in company_type:
                entity_type = EntityType.TRUST
            elif 'partnership' in company_type:
                entity_type = EntityType.PARTNERSHIP
            else:
                entity_type = EntityType.ORGANIZATION
            
            sic = str(row.get('Primary SIC Industry', '')).strip()
            sic_code = sic.split()[0] if sic and sic != 'nan' else None
            
            entity = Entity(
                entity_id=entity_id,
                primary_name=name,
                entity_type=entity_type,
                status=EntityStatus.ACTIVE,
                jurisdiction=country,
                sic_code=sic_code,
                source_system="factset",
                source_id=identifier,
            )
            store.save_entity(entity)
            
            # Add identifier claim
            claim = IdentifierClaim(
                entity_id=entity_id,
                scheme=IdentifierScheme.INTERNAL,
                value=identifier,
                namespace=VendorNamespace.FACTSET,
                source="factset_ff_combined",
            )
            store.save_claim(claim)
            
            saved += 1
            
            if saved % 10000 == 0:
                print(f"  Saved {saved:,} entities...")
                
        except Exception as e:
            errors += 1
            if errors < 5:
                print(f"  Error: {e}")
    
    elapsed = time.time() - start
    
    print(f"\n  Saved {saved:,} entities in {elapsed:.1f}s ({saved/elapsed:.0f} entities/sec)")
    print(f"  Errors: {errors}")
    print(f"  Database size: {db_path.stat().st_size / 1024 / 1024:.1f} MB")
    
    # Test query
    print("\n  Testing query for 'NVIDIA'...")
    entities = store.search_entities("NVIDIA", limit=5)
    for e in entities:
        print(f"    Found: {e.primary_name} ({e.entity_id})")
    
    store.close()


if __name__ == "__main__":
    df = convert_to_parquet()
    show_nvidia_entity(df)
    
    print("\n" + "=" * 70)
    proceed = input(" Load all entities to SQLite? (y/n): ").strip().lower()
    if proceed == 'y':
        load_to_sqlite(df)
    else:
        print("Skipped SQLite loading.")
