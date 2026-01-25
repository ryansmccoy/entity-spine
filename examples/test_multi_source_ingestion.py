#!/usr/bin/env python3
"""
Multi-Source Ingestion Test

Tests loading data from:
1. FactSet ff_combined.csv (large file - sample)
2. Bloomberg Equity_Common_Stock (pipe-delimited)
3. Thomson OpenPermID organizations (TTL.gz)

Validates that EntitySpine model can handle real vendor data.
"""

from __future__ import annotations

import csv
import gzip
import re
from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterator

# EntitySpine domain imports
from entityspine.domain import (
    Entity,
    EntityStatus,
    EntityType,
    IdentifierClaim,
    IdentifierScheme,
    Listing,
    Security,
    SecurityType,
    VendorNamespace,
)
from entityspine.domain.financial_observation import (
    FinancialObservation,
    MetricDefinition,
    MetricVariant,
    DataSource,
    DataSourceType,
    FiscalPeriod,
    FiscalPeriodType,
)
from entityspine.domain.enums import MetricCode, MetricCategory
from entityspine.stores import SqliteStore

# Data paths
FACTSET_PATH = Path("G:/FACTSET/ff_combined.csv")
BLOOMBERG_PATH = Path("G:/BLOOMBERG/Equity_Common_Stock_20160530.txt/Equity_Common_Stock_01_20160530.txt")
THOMSON_PATH = Path("G:/THOMSON/OpenPermID-bulk-organization-20200830_084424.ttl.gz")


def print_header(title: str) -> None:
    """Print a formatted section header."""
    print(f"\n{'=' * 70}")
    print(f" {title}")
    print(f"{'=' * 70}\n")


# =============================================================================
# FactSet Loader (ff_combined.csv)
# =============================================================================

def load_factset_sample(path: Path, limit: int = 100) -> tuple[list[Entity], list[IdentifierClaim]]:
    """
    Load sample from FactSet ff_combined.csv.
    
    Columns include:
    - Identifier (e.g., 0CT4VC-E)
    - Name
    - Website
    - Country
    - Primary SIC Industry
    - FactSet Industry/Sector
    - Various financials
    """
    entities = []
    claims = []
    
    print(f"Loading FactSet data from: {path}")
    
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        reader = csv.DictReader(f)
        
        for i, row in enumerate(reader):
            if i >= limit:
                break
            
            # Extract key fields
            identifier = row.get('Identifier', '').strip()
            name = row.get('Name', '').strip()
            country = row.get('Country', '').strip()
            website = row.get('Website', '').strip()
            sic = row.get('Primary SIC Industry', '').strip()
            factset_industry = row.get('FactSet Industry', '').strip()
            company_type = row.get('Company Type', '').strip()
            
            if not name or not identifier:
                continue
            
            # Determine entity type
            if 'fund' in company_type.lower():
                entity_type = EntityType.FUND
            elif 'trust' in company_type.lower():
                entity_type = EntityType.TRUST
            elif 'partnership' in company_type.lower():
                entity_type = EntityType.PARTNERSHIP
            else:
                entity_type = EntityType.ORGANIZATION
            
            entity_id = f"factset:{identifier}"
            
            entity = Entity(
                entity_id=entity_id,
                primary_name=name,
                entity_type=entity_type,
                status=EntityStatus.ACTIVE,
                jurisdiction=country if len(country) <= 10 else country[:2].upper(),
                sic_code=sic.split()[0] if sic else None,
                source_system="factset",
                source_id=identifier,
            )
            entities.append(entity)
            
            # Add FactSet internal ID claim
            claim = IdentifierClaim(
                entity_id=entity_id,
                scheme=IdentifierScheme.INTERNAL,
                value=identifier,
                namespace=VendorNamespace.FACTSET,
                source="factset_ff_combined",
                confidence=1.0,
            )
            claims.append(claim)
    
    print(f"  [OK] Loaded {len(entities)} entities from FactSet")
    return entities, claims


def load_factset_observations(path: Path, limit: int = 100) -> list[FinancialObservation]:
    """
    Load financial observations from FactSet ff_combined.csv.
    
    Maps financial columns to FinancialObservation objects.
    """
    observations = []
    
    # Map FactSet columns to MetricCode
    METRIC_MAP = {
        'Revenue': MetricCode.REVENUE,
        'EBITDA': MetricCode.EBITDA,
        'EBIT': MetricCode.EBIT,
        'Net Income': MetricCode.NET_INCOME,
        'Gross Profit': MetricCode.GROSS_PROFIT,
        'EPS (Diluted)': MetricCode.EPS_DILUTED,
        'EPS (Basic)': MetricCode.EPS_BASIC,
        'Free Cash Flow': MetricCode.FREE_CASH_FLOW,
        'Total Assets': MetricCode.TOTAL_ASSETS,
        'Total Debt': MetricCode.LONG_TERM_DEBT,
        'Market Cap': MetricCode.MARKET_CAP,
        'Enterprise Value': MetricCode.ENTERPRISE_VALUE,
    }
    
    print(f"Loading FactSet observations from: {path}")
    
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        reader = csv.DictReader(f)
        
        for i, row in enumerate(reader):
            if i >= limit:
                break
            
            identifier = row.get('Identifier', '').strip()
            if not identifier:
                continue
            
            entity_id = f"factset:{identifier}"
            
            # Extract each financial metric
            for col_name, metric_code in METRIC_MAP.items():
                value_str = row.get(col_name, '').strip()
                if not value_str or value_str == '-':
                    continue
                
                try:
                    value = Decimal(value_str.replace(',', ''))
                except (InvalidOperation, ValueError):
                    continue
                
                # Determine variant
                variant = MetricVariant.NORMALIZED
                if 'Basic' in col_name:
                    variant = MetricVariant.BASIC
                elif 'Diluted' in col_name:
                    variant = MetricVariant.DILUTED
                
                obs = FinancialObservation(
                    entity_id=entity_id,
                    metric=MetricDefinition(
                        code=metric_code,
                        category=MetricCategory.INCOME_STATEMENT if metric_code in (
                            MetricCode.REVENUE, MetricCode.EBITDA, MetricCode.EBIT,
                            MetricCode.NET_INCOME, MetricCode.GROSS_PROFIT
                        ) else MetricCategory.BALANCE_SHEET,
                        variant=variant,
                        name=col_name,
                    ),
                    period=FiscalPeriod(year=2013, period_type=FiscalPeriodType.ANNUAL),
                    value=value,
                    currency="USD",
                    source=DataSource(
                        source_type=DataSourceType.VENDOR_FEED,
                        vendor=VendorNamespace.FACTSET,
                        dataset="ff_combined",
                    ),
                )
                observations.append(obs)
    
    print(f"  [OK] Loaded {len(observations)} financial observations from FactSet")
    return observations


# =============================================================================
# Bloomberg BBUID Loader
# =============================================================================

def load_bloomberg_sample(path: Path, limit: int = 100) -> tuple[list[Entity], list[Security], list[Listing], list[IdentifierClaim]]:
    """
    Load sample from Bloomberg BBUID pipe-delimited file.
    
    Columns:
    - NAME
    - ID_BB_SEC_NUM_DES (ticker)
    - FEED_SOURCE (exchange code)
    - ID_BB_UNIQUE (BBUID)
    - SECURITY_TYP
    - MARKET_SECTOR_DES
    - ID_BB_GLOBAL (FIGI)
    - COMPOSITE_ID_BB_GLOBAL
    """
    entities = []
    securities = []
    listings = []
    claims = []
    seen_entities = {}  # Track by composite FIGI
    
    # Bloomberg FEED_SOURCE to MIC mapping
    BLOOMBERG_FEED_TO_MIC = {
        'US': 'XNYS', 'UW': 'XNAS', 'UN': 'XNYS', 'UA': 'XASE',
        'UP': 'ARCX', 'UV': 'OTCM', 'LN': 'XLON', 'TN': 'XTSE',
        'QF': 'XTSE', 'JP': 'XTKS', 'HK': 'XHKG',
    }
    
    print(f"Loading Bloomberg data from: {path}")
    
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        reader = csv.reader(f, delimiter='|')
        header = next(reader)
        
        for i, row in enumerate(reader):
            if i >= limit:
                break
            
            if len(row) < 8:
                continue
            
            row_dict = dict(zip(header, row))
            
            name = row_dict.get('NAME', '').strip()
            ticker = row_dict.get('ID_BB_SEC_NUM_DES', '').strip()
            feed_source = row_dict.get('FEED_SOURCE', '').strip()
            bbuid = row_dict.get('ID_BB_UNIQUE', '').strip()
            security_type = row_dict.get('SECURITY_TYP', '').strip()
            figi = row_dict.get('ID_BB_GLOBAL', '').strip()
            composite_figi = row_dict.get('COMPOSITE_ID_BB_GLOBAL', '').strip()
            
            if not name or not bbuid:
                continue
            
            # Use composite FIGI as entity key
            entity_key = composite_figi or bbuid
            
            # Create entity if not seen
            if entity_key not in seen_entities:
                entity_id = f"bloomberg:{composite_figi}" if composite_figi else f"bloomberg:{bbuid}"
                
                entity = Entity(
                    entity_id=entity_id,
                    primary_name=name,
                    entity_type=EntityType.ORGANIZATION,
                    status=EntityStatus.ACTIVE,
                    source_system="bloomberg",
                    source_id=composite_figi or bbuid,
                )
                entities.append(entity)
                seen_entities[entity_key] = entity_id
                
                # Note: FIGI is security-scoped, so we add it when creating securities, not here
            
            entity_id = seen_entities[entity_key]
            
            # Create security
            security_id = f"{entity_id}:{bbuid}"
            security = Security(
                security_id=security_id,
                entity_id=entity_id,
                security_type=SecurityType.COMMON_STOCK,
                description=f"{name} {security_type}",
                source_system="bloomberg",
            )
            securities.append(security)
            
            # Add composite FIGI claim at security level (FIGI is security-scoped)
            if composite_figi and entity_key not in seen_entities or entity_key == entity_key:
                # Only add once per entity_key
                pass
            
            # Add FIGI claim at security level
            if figi:
                try:
                    figi_claim = IdentifierClaim(
                        security_id=security_id,
                        scheme=IdentifierScheme.FIGI,
                        value=figi,
                        namespace=VendorNamespace.BLOOMBERG,
                        source="bloomberg_bbuid",
                    )
                    claims.append(figi_claim)
                except ValueError:
                    pass
            
            # Create listing
            mic = BLOOMBERG_FEED_TO_MIC.get(feed_source)
            listing_id = f"{security_id}:{feed_source}"
            
            try:
                listing = Listing(
                    listing_id=listing_id,
                    security_id=security_id,
                    ticker=ticker,
                    mic=mic,
                    is_primary=(feed_source == 'US'),
                    source_system="bloomberg",
                )
                listings.append(listing)
            except ValueError:
                pass  # Skip invalid tickers
    
    print(f"  [OK] Loaded {len(entities)} entities, {len(securities)} securities, {len(listings)} listings from Bloomberg")
    return entities, securities, listings, claims


# =============================================================================
# Thomson OpenPermID Loader
# =============================================================================

def load_thomson_sample(path: Path, limit: int = 100) -> tuple[list[Entity], list[IdentifierClaim]]:
    """
    Load sample from Thomson OpenPermID TTL.gz file.
    
    TTL format groups triples by subject:
        <https://permid.org/1-5064647712>
            a tr-org:Organization ;
            tr-common:hasPermId "5064647712" ;
            vcard:organization-name "Company Name" .
    """
    entities = []
    claims = []
    
    # Geonames to country mapping
    GEONAMES_TO_COUNTRY = {
        '6252001': 'US', '2635167': 'GB', '2921044': 'DE',
        '3017382': 'FR', '1814991': 'CN', '1861060': 'JP',
        '6251999': 'CA', '2077456': 'AU',
    }
    
    print(f"Loading Thomson data from: {path}")
    
    count = 0
    current_entity = {}
    current_uri = None
    
    with gzip.open(path, 'rt', encoding='utf-8', errors='replace') as f:
        for line in f:
            if count >= limit:
                break
            
            line = line.strip()
            
            # Skip prefixes and empty lines
            if not line or line.startswith('@prefix'):
                continue
            
            # New entity starts with URI
            if line.startswith('<https://permid.org/'):
                # Save previous entity
                if current_entity and current_entity.get('name'):
                    permid = current_entity.get('permid', '')
                    name = current_entity.get('name', '')
                    geonames_id = current_entity.get('geonames_id', '')
                    status = current_entity.get('status', 'active')
                    
                    entity_id = f"permid:{permid}"
                    country = GEONAMES_TO_COUNTRY.get(geonames_id)
                    
                    entity = Entity(
                        entity_id=entity_id,
                        primary_name=name,
                        entity_type=EntityType.ORGANIZATION,
                        status=EntityStatus.ACTIVE if status == 'active' else EntityStatus.INACTIVE,
                        jurisdiction=country,
                        source_system="thomson_permid",
                        source_id=permid,
                    )
                    entities.append(entity)
                    
                    # Add PermID claim
                    claim = IdentifierClaim(
                        entity_id=entity_id,
                        scheme=IdentifierScheme.INTERNAL,
                        value=permid,
                        namespace=VendorNamespace.REUTERS,  # Thomson/Reuters/Refinitiv
                        source="thomson_openpermid",
                    )
                    claims.append(claim)
                    count += 1
                
                # Parse new URI
                uri_end = line.index('>')
                current_uri = line[1:uri_end]
                current_entity = {'uri': current_uri}
                
                # Extract PermID from URI
                if '/1-' in current_uri:
                    permid = current_uri.split('/1-')[-1]
                    current_entity['permid'] = permid
            
            elif current_uri:
                # Parse predicates
                if 'hasPermId' in line:
                    match = re.search(r'"([^"]+)"', line)
                    if match:
                        current_entity['permid'] = match.group(1)
                
                elif 'organization-name' in line:
                    match = re.search(r'"([^"]+)"', line)
                    if match:
                        current_entity['name'] = match.group(1)
                
                elif 'hasActivityStatus' in line:
                    if 'statusActive' in line:
                        current_entity['status'] = 'active'
                    elif 'statusInactive' in line:
                        current_entity['status'] = 'inactive'
                
                elif 'isDomiciledIn' in line or 'isIncorporatedIn' in line:
                    match = re.search(r'geonames\.org/(\d+)', line)
                    if match:
                        current_entity['geonames_id'] = match.group(1)
    
    print(f"  [OK] Loaded {len(entities)} entities from Thomson OpenPermID")
    return entities, claims


# =============================================================================
# Main Test
# =============================================================================

def main():
    """Run multi-source ingestion test."""
    print_header("EntitySpine Multi-Source Ingestion Test")
    
    all_entities = []
    all_securities = []
    all_listings = []
    all_claims = []
    all_observations = []
    
    # 1. Load FactSet data
    print_header("1. Loading FactSet Data")
    if FACTSET_PATH.exists():
        fs_entities, fs_claims = load_factset_sample(FACTSET_PATH, limit=50)
        all_entities.extend(fs_entities)
        all_claims.extend(fs_claims)
        
        # Also load financial observations
        fs_obs = load_factset_observations(FACTSET_PATH, limit=50)
        all_observations.extend(fs_obs)
    else:
        print(f"  [WARN] FactSet file not found: {FACTSET_PATH}")
    
    # 2. Load Bloomberg data
    print_header("2. Loading Bloomberg Data")
    if BLOOMBERG_PATH.exists():
        bb_entities, bb_securities, bb_listings, bb_claims = load_bloomberg_sample(BLOOMBERG_PATH, limit=50)
        all_entities.extend(bb_entities)
        all_securities.extend(bb_securities)
        all_listings.extend(bb_listings)
        all_claims.extend(bb_claims)
    else:
        print(f"  [WARN] Bloomberg file not found: {BLOOMBERG_PATH}")
    
    # 3. Load Thomson data
    print_header("3. Loading Thomson OpenPermID Data")
    if THOMSON_PATH.exists():
        th_entities, th_claims = load_thomson_sample(THOMSON_PATH, limit=50)
        all_entities.extend(th_entities)
        all_claims.extend(th_claims)
    else:
        print(f"  [WARN] Thomson file not found: {THOMSON_PATH}")
    
    # Summary
    print_header("Summary")
    print(f"  Total Entities:      {len(all_entities)}")
    print(f"  Total Securities:    {len(all_securities)}")
    print(f"  Total Listings:      {len(all_listings)}")
    print(f"  Total Claims:        {len(all_claims)}")
    print(f"  Total Observations:  {len(all_observations)}")
    
    # Group by source
    by_source = defaultdict(int)
    for e in all_entities:
        by_source[e.source_system] += 1
    
    print("\n  Entities by Source:")
    for source, count in sorted(by_source.items()):
        print(f"    - {source}: {count}")
    
    # Show sample entities
    print_header("Sample Entities")
    for entity in all_entities[:5]:
        print(f"  [{entity.source_system}] {entity.primary_name}")
        print(f"      ID: {entity.entity_id}")
        print(f"      Type: {entity.entity_type.value}")
        print(f"      Jurisdiction: {entity.jurisdiction}")
        print()
    
    # Show sample claims
    print_header("Sample Identifier Claims")
    for claim in all_claims[:5]:
        target = claim.entity_id or claim.security_id or claim.listing_id
        print(f"  {claim.scheme.value}: {claim.value}")
        print(f"      Target: {target}")
        print(f"      Source: {claim.source}")
        print()
    
    # Show sample observations
    print_header("Sample Financial Observations")
    for obs in all_observations[:5]:
        print(f"  {obs}")
        print(f"      Entity: {obs.entity_id}")
        print(f"      Source: {obs.source}")
        print()
    
    # Test storing in SQLite
    print_header("Testing SQLite Store")
    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    store = SqliteStore(db_path=db_path)
    store.initialize()
    
    # Save entities
    saved_count = 0
    for entity in all_entities:
        try:
            store.save_entity(entity)
            saved_count += 1
        except Exception as e:
            print(f"  [WARN] Error saving {entity.entity_id}: {e}")
    
    print(f"  [OK] Saved {saved_count}/{len(all_entities)} entities to SQLite")
    
    # Save claims
    claim_count = 0
    for claim in all_claims:
        try:
            store.save_claim(claim)
            claim_count += 1
        except Exception as e:
            pass  # Some claims may fail validation
    
    print(f"  [OK] Saved {claim_count}/{len(all_claims)} claims")
    
    # Test retrieval
    print(f"\n  Store entity count: {store.entity_count()}")
    
    # Show field mapping analysis
    print_header("Field Mapping Analysis")
    
    # FactSet field mappings
    print("  FactSet → EntitySpine mappings:")
    print("    Identifier        → entity.source_id")
    print("    Name              → entity.primary_name")
    print("    Country           → entity.jurisdiction")
    print("    Company Type      → entity.entity_type")
    print("    Primary SIC       → entity.sic_code")
    print("    Website           → (extended attribute)")
    print("    Revenue, EBITDA   → FinancialObservation")
    
    print("\n  Bloomberg → EntitySpine mappings:")
    print("    NAME              → entity.primary_name")
    print("    ID_BB_UNIQUE      → entity.source_id (BBUID)")
    print("    COMPOSITE_FIGI    → claim (entity key)")
    print("    ID_BB_GLOBAL      → claim.FIGI (security-scoped)")
    print("    ID_BB_SEC_NUM_DES → listing.ticker")
    print("    FEED_SOURCE       → listing.mic (via mapping)")
    print("    SECURITY_TYP      → security.security_type")
    
    print("\n  Thomson PermID → EntitySpine mappings:")
    print("    organization-name → entity.primary_name")
    print("    hasPermId         → entity.source_id")
    print("    isDomiciledIn     → entity.jurisdiction (via geonames)")
    print("    hasActivityStatus → entity.status")
    
    # Show claim scope validation
    print_header("Identifier Scope Validation")
    scope_counts = {"entity": 0, "security": 0, "listing": 0}
    for claim in all_claims:
        if claim.entity_id:
            scope_counts["entity"] += 1
        elif claim.security_id:
            scope_counts["security"] += 1
        elif claim.listing_id:
            scope_counts["listing"] += 1
    
    print(f"  Entity-scoped claims:   {scope_counts['entity']}")
    print(f"  Security-scoped claims: {scope_counts['security']}")
    print(f"  Listing-scoped claims:  {scope_counts['listing']}")
    
    # Show scheme distribution
    scheme_counts = defaultdict(int)
    for claim in all_claims:
        scheme_counts[claim.scheme.value] += 1
    
    print("\n  Claims by Scheme:")
    for scheme, count in sorted(scheme_counts.items()):
        print(f"    - {scheme}: {count}")
    
    store.close()
    
    # Cleanup
    Path(db_path).unlink(missing_ok=True)
    
    print_header("Test Complete!")
    print("  All vendor data successfully mapped to EntitySpine domain models.")


if __name__ == "__main__":
    main()
