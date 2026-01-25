#!/usr/bin/env python3
"""
EntitySpine Performance & Global Ticker Example

This example demonstrates:
1. MEMORY ESTIMATION - How much memory a security master uses
2. PERFORMANCE OPTIMIZATION - Fast lookups and efficient storage
3. GLOBAL TICKERS - Handling same ticker on different exchanges (MIC codes)

SCENARIO:
- 50,000 entities (companies)
- 15 identifiers per entity (CIK, LEI, DUNS, multiple tickers, etc.)
- Global exchanges (NYSE, NASDAQ, LSE, TSE, XETRA, etc.)

USAGE:
    python examples/performance_and_global_tickers.py
"""

from __future__ import annotations

import gc
import sys
import time
from dataclasses import dataclass
from datetime import date
from typing import Any

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
from entityspine.stores import JsonEntityStore, SqliteStore


def print_header(title: str) -> None:
    """Print a formatted section header."""
    print(f"\n{'=' * 70}")
    print(f" {title}")
    print(f"{'=' * 70}\n")


def get_size_bytes(obj: Any, seen: set | None = None) -> int:
    """Recursively calculate object size in bytes."""
    size = sys.getsizeof(obj)
    if seen is None:
        seen = set()
    obj_id = id(obj)
    if obj_id in seen:
        return 0
    seen.add(obj_id)
    
    if isinstance(obj, dict):
        size += sum(get_size_bytes(k, seen) + get_size_bytes(v, seen) for k, v in obj.items())
    elif hasattr(obj, '__dict__'):
        size += get_size_bytes(obj.__dict__, seen)
    elif hasattr(obj, '__iter__') and not isinstance(obj, (str, bytes, bytearray)):
        size += sum(get_size_bytes(i, seen) for i in obj)
    return size


def format_bytes(size: int) -> str:
    """Format bytes as human-readable string."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


# =============================================================================
# GLOBAL EXCHANGE DEFINITIONS (MIC Codes)
# =============================================================================

# Market Identifier Codes (ISO 10383) for major exchanges
EXCHANGES = {
    # North America
    "XNYS": {"name": "New York Stock Exchange", "country": "US", "currency": "USD"},
    "XNAS": {"name": "NASDAQ", "country": "US", "currency": "USD"},
    "XASE": {"name": "NYSE American (AMEX)", "country": "US", "currency": "USD"},
    "XTSE": {"name": "Toronto Stock Exchange", "country": "CA", "currency": "CAD"},
    "XTSX": {"name": "TSX Venture", "country": "CA", "currency": "CAD"},
    
    # Europe
    "XLON": {"name": "London Stock Exchange", "country": "GB", "currency": "GBP"},
    "XETR": {"name": "Deutsche Börse XETRA", "country": "DE", "currency": "EUR"},
    "XPAR": {"name": "Euronext Paris", "country": "FR", "currency": "EUR"},
    "XAMS": {"name": "Euronext Amsterdam", "country": "NL", "currency": "EUR"},
    "XSWX": {"name": "SIX Swiss Exchange", "country": "CH", "currency": "CHF"},
    
    # Asia-Pacific
    "XTKS": {"name": "Tokyo Stock Exchange", "country": "JP", "currency": "JPY"},
    "XHKG": {"name": "Hong Kong Stock Exchange", "country": "HK", "currency": "HKD"},
    "XSHG": {"name": "Shanghai Stock Exchange", "country": "CN", "currency": "CNY"},
    "XSHE": {"name": "Shenzhen Stock Exchange", "country": "CN", "currency": "CNY"},
    "XASX": {"name": "Australian Securities Exchange", "country": "AU", "currency": "AUD"},
    "XKRX": {"name": "Korea Exchange", "country": "KR", "currency": "KRW"},
    "XBOM": {"name": "BSE India", "country": "IN", "currency": "INR"},
    "XNSE": {"name": "National Stock Exchange India", "country": "IN", "currency": "INR"},
}


def generate_global_security_master(num_entities: int) -> dict:
    """
    Generate a realistic global security master dataset.
    
    Each entity has:
    - 1 Entity record
    - 1-3 Securities (common stock, ADR, etc.)
    - 1-5 Listings (across multiple exchanges)
    - ~15 IdentifierClaims (CIK, LEI, CUSIP, ISIN, etc.)
    """
    import random
    
    # Company name components for generation
    prefixes = ["Global", "International", "National", "United", "First", "Pacific", "Atlantic", "Northern", "Southern", "Eastern", "Western", "Central", "Premier", "Prime", "Alpha", "Omega", "Delta", "Summit", "Apex", "Quantum"]
    industries = ["Tech", "Finance", "Energy", "Health", "Industrial", "Consumer", "Media", "Telecom", "Materials", "Utilities", "Real Estate", "Transportation", "Aerospace", "Pharma", "Biotech", "Software", "Hardware", "Services", "Holdings", "Capital"]
    suffixes = ["Inc.", "Corp.", "Ltd.", "PLC", "AG", "SA", "NV", "AB", "SpA", "Co.", "Group", "Holdings", "Industries", "Enterprises", "Partners", "Systems", "Solutions", "International", "Global", "Worldwide"]
    
    # Generate realistic tickers
    def make_ticker(i: int) -> str:
        letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        if i < 26:
            return letters[i]
        elif i < 26 * 26:
            return letters[i // 26 - 1] + letters[i % 26]
        elif i < 26 * 26 * 26:
            return letters[i // (26*26) - 1] + letters[(i // 26) % 26] + letters[i % 26]
        else:
            return f"T{i:04d}"
    
    data = {
        "entities": [],
        "securities": [],
        "listings": [],
        "claims": [],
    }
    
    exchange_list = list(EXCHANGES.keys())
    
    for i in range(num_entities):
        # Entity
        entity_id = f"ent_{i:06d}"
        name = f"{random.choice(prefixes)} {random.choice(industries)} {random.choice(suffixes)}"
        
        data["entities"].append({
            "entity_id": entity_id,
            "primary_name": name,
            "entity_type": "organization",
            "status": "active",
            "jurisdiction": random.choice(["US-DE", "US-NY", "GB", "DE", "JP", "CN", "CA"]),
            "sic_code": f"{random.randint(1000, 9999)}",
        })
        
        # Generate 15 identifier claims per entity
        cik = f"{1000000 + i:010d}"
        lei = f"{''.join(random.choices('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=20))}"
        
        # CIK claim
        data["claims"].append({
            "claim_id": f"clm_{entity_id}_cik",
            "entity_id": entity_id,
            "scheme": "cik",
            "value": cik,
            "namespace": "sec",
        })
        
        # LEI claim
        data["claims"].append({
            "claim_id": f"clm_{entity_id}_lei",
            "entity_id": entity_id,
            "scheme": "lei",
            "value": lei,
            "namespace": "gleif",
        })
        
        # DUNS claim
        data["claims"].append({
            "claim_id": f"clm_{entity_id}_duns",
            "entity_id": entity_id,
            "scheme": "duns",
            "value": f"{random.randint(100000000, 999999999):09d}",
            "namespace": "other",
        })
        
        # EIN claim
        data["claims"].append({
            "claim_id": f"clm_{entity_id}_ein",
            "entity_id": entity_id,
            "scheme": "ein",
            "value": f"{random.randint(10, 99)}-{random.randint(1000000, 9999999)}",
            "namespace": "sec",
        })
        
        # Securities (1-3 per entity)
        num_securities = random.randint(1, 3)
        base_ticker = make_ticker(i)
        
        for s in range(num_securities):
            security_id = f"sec_{entity_id}_{s}"
            sec_type = ["common_stock", "preferred_stock", "adr"][s] if s < 3 else "common_stock"
            
            data["securities"].append({
                "security_id": security_id,
                "entity_id": entity_id,
                "security_type": sec_type,
                "description": f"{name} {sec_type.replace('_', ' ').title()}",
            })
            
            # Security-level identifiers (ISIN, CUSIP, SEDOL, FIGI)
            isin = f"US{''.join(random.choices('0123456789', k=9))}{random.randint(0, 9)}"
            cusip = f"{''.join(random.choices('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=9))}"
            
            data["claims"].append({
                "claim_id": f"clm_{security_id}_isin",
                "security_id": security_id,
                "scheme": "isin",
                "value": isin,
                "namespace": "other",
            })
            
            data["claims"].append({
                "claim_id": f"clm_{security_id}_cusip",
                "security_id": security_id,
                "scheme": "cusip",
                "value": cusip,
                "namespace": "other",
            })
            
            data["claims"].append({
                "claim_id": f"clm_{security_id}_figi",
                "security_id": security_id,
                "scheme": "figi",
                "value": f"BBG{''.join(random.choices('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=9))}",
                "namespace": "openfigi",
            })
            
            # Listings (1-5 per security, across different exchanges)
            num_listings = random.randint(1, min(5, len(exchange_list)))
            selected_exchanges = random.sample(exchange_list, num_listings)
            
            for l, mic in enumerate(selected_exchanges):
                listing_id = f"lst_{security_id}_{mic}"
                ticker = base_ticker if l == 0 else f"{base_ticker}.{EXCHANGES[mic]['country']}"
                
                data["listings"].append({
                    "listing_id": listing_id,
                    "security_id": security_id,
                    "ticker": ticker,
                    "exchange": EXCHANGES[mic]["name"],
                    "mic": mic,
                    "currency": EXCHANGES[mic]["currency"],
                    "is_primary": l == 0,
                })
                
                # Ticker claim (listing-scoped)
                data["claims"].append({
                    "claim_id": f"clm_{listing_id}_ticker",
                    "listing_id": listing_id,
                    "scheme": "ticker",
                    "value": ticker,
                    "namespace": "exchange",
                })
    
    return data


def demo_memory_estimation() -> None:
    """Estimate memory usage for different dataset sizes."""
    print_header("1. Memory Estimation")
    
    print("Estimating memory for security master datasets:\n")
    
    sizes = [1000, 5000, 10000, 50000]
    
    for num_entities in sizes:
        # Generate sample data
        data = generate_global_security_master(num_entities)
        
        # Calculate sizes
        entity_size = get_size_bytes(data["entities"])
        security_size = get_size_bytes(data["securities"])
        listing_size = get_size_bytes(data["listings"])
        claim_size = get_size_bytes(data["claims"])
        total_size = entity_size + security_size + listing_size + claim_size
        
        print(f"  {num_entities:,} entities:")
        print(f"    Entities:  {len(data['entities']):>8,} records  {format_bytes(entity_size):>10}")
        print(f"    Securities:{len(data['securities']):>8,} records  {format_bytes(security_size):>10}")
        print(f"    Listings:  {len(data['listings']):>8,} records  {format_bytes(listing_size):>10}")
        print(f"    Claims:    {len(data['claims']):>8,} records  {format_bytes(claim_size):>10}")
        print(f"    TOTAL:     {format_bytes(total_size):>30}")
        print(f"    Avg/entity:{format_bytes(total_size // num_entities):>30}")
        print()
        
        # Clean up
        del data
        gc.collect()
    
    print("""
  MEMORY GUIDELINES:
  
  | Entities | Est. Memory | Recommended Tier |
  |----------|-------------|------------------|
  | 1,000    | ~10 MB      | Tier 0 (JSON)    |
  | 10,000   | ~100 MB     | Tier 0/1         |
  | 50,000   | ~500 MB     | Tier 1 (SQLite)  |
  | 500,000  | ~5 GB       | Tier 2 (DuckDB)  |
  | 5,000,000| ~50 GB      | Tier 3 (PG)      |
""")


def demo_performance_optimization() -> None:
    """Demonstrate performance optimization techniques."""
    print_header("2. Performance Optimization")
    
    # Generate test data
    num_entities = 5000
    print(f"  Generating {num_entities:,} entities with ~15 identifiers each...")
    data = generate_global_security_master(num_entities)
    
    # Convert to SEC JSON format for loading
    sec_json = {}
    for i, entity in enumerate(data["entities"]):
        cik = f"{1000000 + i}"
        # Find a ticker for this entity
        ticker = f"T{i:04d}"
        for listing in data["listings"]:
            if listing["security_id"].startswith(f"sec_{entity['entity_id']}"):
                ticker = listing["ticker"]
                break
        sec_json[str(i)] = {
            "cik_str": int(cik),
            "ticker": ticker,
            "title": entity["primary_name"],
        }
    
    print(f"  Generated {len(sec_json):,} SEC records\n")
    
    # Benchmark Tier 0 (JSON)
    print("  --- Tier 0 (JSON/Memory) ---")
    store0 = JsonEntityStore()
    store0.initialize()
    
    start = time.perf_counter()
    store0.load_sec_json(sec_json)
    load_time0 = (time.perf_counter() - start) * 1000
    print(f"    Load time: {load_time0:.0f} ms")
    
    # Benchmark lookups
    test_ciks = [f"{1000000 + i:010d}" for i in range(0, num_entities, num_entities // 100)]
    
    start = time.perf_counter()
    for cik in test_ciks:
        store0.get_entities_by_cik(cik)
    lookup_time0 = (time.perf_counter() - start) * 1000 / len(test_ciks)
    print(f"    CIK lookup: {lookup_time0:.3f} ms avg ({len(test_ciks)} lookups)")
    
    start = time.perf_counter()
    for _ in range(100):
        store0.search_entities("Global", limit=10)
    search_time0 = (time.perf_counter() - start) * 1000 / 100
    print(f"    Search: {search_time0:.2f} ms avg")
    
    store0.close()
    
    # Benchmark Tier 1 (SQLite)
    print("\n  --- Tier 1 (SQLite) ---")
    store1 = SqliteStore(db_path=":memory:")
    store1.initialize()
    
    start = time.perf_counter()
    store1.load_sec_json(sec_json)
    load_time1 = (time.perf_counter() - start) * 1000
    print(f"    Load time: {load_time1:.0f} ms")
    
    start = time.perf_counter()
    for cik in test_ciks:
        store1.get_entities_by_cik(cik)
    lookup_time1 = (time.perf_counter() - start) * 1000 / len(test_ciks)
    print(f"    CIK lookup: {lookup_time1:.3f} ms avg ({len(test_ciks)} lookups)")
    
    start = time.perf_counter()
    for _ in range(100):
        store1.search_entities("Global", limit=10)
    search_time1 = (time.perf_counter() - start) * 1000 / 100
    print(f"    Search: {search_time1:.2f} ms avg")
    
    store1.close()
    
    print(f"""
  PERFORMANCE COMPARISON ({num_entities:,} entities):
  
  | Operation    | Tier 0 (JSON) | Tier 1 (SQLite) | Winner |
  |--------------|---------------|-----------------|--------|
  | Bulk Load    | {load_time0:>8.0f} ms    | {load_time1:>10.0f} ms    | {'Tier 0' if load_time0 < load_time1 else 'Tier 1':<6} |
  | CIK Lookup   | {lookup_time0:>8.3f} ms    | {lookup_time1:>10.3f} ms    | {'Tier 0' if lookup_time0 < lookup_time1 else 'Tier 1':<6} |
  | Name Search  | {search_time0:>8.2f} ms    | {search_time1:>10.2f} ms    | {'Tier 0' if search_time0 < search_time1 else 'Tier 1':<6} |
  
  OPTIMIZATION STRATEGIES:
  
  1. INDEX STRATEGY (Already implemented):
     - CIK index: O(1) dict lookup in Tier 0, B-tree in Tier 1
     - Ticker index: Normalized uppercase for consistent matching
     - Name index: Lowercased for case-insensitive search
  
  2. BATCH LOADING:
     - Use load_sec_json() for bulk operations
     - Avoid individual save_entity() in loops
  
  3. LAZY LOADING:
     - Don't load full entity graph unless needed
     - Use get_entities_by_cik() not full scan
  
  4. CACHING (for web apps):
     - Cache resolved entities by (identifier_type, identifier_value)
     - Invalidate on entity update
  
  5. TIER SELECTION:
     - < 50k entities: Tier 0 is fine (fast, simple)
     - 50k-500k: Tier 1 for persistence + SQL
     - > 500k: Tier 2+ for analytics
""")


def demo_global_ticker_handling() -> None:
    """Demonstrate proper handling of global tickers with MIC codes."""
    print_header("3. Global Ticker Handling (MIC Codes)")
    
    store = SqliteStore(db_path=":memory:")
    store.initialize()
    
    print("""
  PROBLEM: Same ticker can exist on different exchanges
  
  Example: "AAPL" could be:
    - Apple Inc. on NASDAQ (XNAS)
    - A different company on another exchange
    
  SOLUTION: Use MIC (Market Identifier Code) to disambiguate
""")
    
    # Create a company with listings on multiple exchanges
    print("  Creating Royal Dutch Shell with global listings...\n")
    
    # Load base entity
    store.load_sec_json({
        "0": {"cik_str": 1306965, "ticker": "SHEL", "title": "Shell plc"},
    })
    
    # Get the entity we just created
    entities = store.get_entities_by_cik("1306965")
    if not entities:
        print("  ERROR: Entity not created")
        return
    
    entity = entities[0]
    print(f"  Entity: {entity.primary_name}")
    print(f"  Entity ID: {entity.entity_id}")
    
    # The current system creates one listing. Let's explain the model:
    print("""
  ENTITYSPINE DATA MODEL FOR GLOBAL TICKERS:
  
  Entity (Shell plc)
    |
    +-- Security (Shell Common Stock)
          |
          +-- Listing: SHEL on NYSE (MIC: XNYS)     [Primary]
          +-- Listing: SHEL on LSE (MIC: XLON)
          +-- Listing: SHELL on Euronext (MIC: XAMS)
          +-- Listing: SHEL on Frankfurt (MIC: XETR)
          
  Each Listing has:
    - ticker: The symbol (SHEL, SHELL, etc.)
    - exchange: Human-readable name
    - mic: ISO 10383 Market Identifier Code
    - currency: Trading currency
    - is_primary: True for the main listing
""")
    
    # Demonstrate ticker resolution with MIC
    print("  RESOLUTION EXAMPLES:\n")
    
    # Simple ticker lookup (returns all exchanges)
    listings = store.get_listings_by_ticker("SHEL")
    print(f"  get_listings_by_ticker('SHEL'):")
    for listing in listings:
        print(f"    - {listing.ticker} on {listing.exchange} (MIC: {listing.mic})")
    
    # MIC-qualified lookup
    print("\n  get_listings_by_ticker('SHEL', mic='XNYS'):")
    listings = store.get_listings_by_ticker("SHEL", mic="XNYS")
    for listing in listings:
        print(f"    - {listing.ticker} on {listing.exchange} (MIC: {listing.mic})")
    
    store.close()
    
    print("""
  BEST PRACTICES FOR GLOBAL TICKERS:
  
  1. ALWAYS store MIC code with listings
     - MIC is the ISO standard (ISO 10383)
     - Unambiguous, machine-readable
     - Example: XNYS (NYSE), XNAS (NASDAQ), XLON (LSE)
  
  2. Use qualified lookups when possible:
     get_listings_by_ticker("AAPL", mic="XNAS")  # Specific
     get_listings_by_ticker("AAPL")              # All exchanges
  
  3. Handle multi-listed securities:
     - Same company, different tickers (SHEL vs SHELL)
     - Same ticker, different companies (rare but possible)
     - ADRs vs ordinary shares
  
  4. Currency matters:
     - SHEL on NYSE trades in USD
     - SHEL on LSE trades in GBP
     - Store currency on Listing, not Entity
  
  5. Primary listing flag:
     - Set is_primary=True for home exchange
     - Useful for default display/sorting

  COMMON MIC CODES:
  
  | MIC  | Exchange                    | Country |
  |------|-----------------------------|---------|
  | XNYS | New York Stock Exchange     | US      |
  | XNAS | NASDAQ                      | US      |
  | XLON | London Stock Exchange       | GB      |
  | XETR | Deutsche Borse XETRA        | DE      |
  | XTKS | Tokyo Stock Exchange        | JP      |
  | XHKG | Hong Kong Stock Exchange    | HK      |
  | XSHG | Shanghai Stock Exchange     | CN      |
  | XASX | Australian Securities Exch  | AU      |
  | XTSE | Toronto Stock Exchange      | CA      |
  | XPAR | Euronext Paris              | FR      |
""")


def demo_optimized_lookup_patterns() -> None:
    """Show optimized lookup patterns for production use."""
    print_header("4. Optimized Lookup Patterns")
    
    print("""
  PATTERN 1: Identifier Routing
  
  def resolve_identifier(value: str, hint: str = None) -> Entity | None:
      '''Smart resolution based on identifier format.'''
      
      # Auto-detect identifier type
      if value.isdigit() and len(value) <= 10:
          # Looks like CIK
          return store.get_entities_by_cik(value)
      
      elif len(value) == 20 and value.isalnum():
          # Looks like LEI
          return store.get_entities_by_lei(value)
      
      elif len(value) == 12 and value[:2].isalpha():
          # Looks like ISIN
          return store.get_securities_by_isin(value)
      
      elif len(value) <= 5 and value.isalpha():
          # Looks like ticker
          return store.get_entities_by_ticker(value)
      
      # Fall back to search
      return store.search_entities(value, limit=1)
  
  
  PATTERN 2: Batch Resolution
  
  def resolve_batch(identifiers: list[tuple[str, str]]) -> dict:
      '''Resolve multiple identifiers efficiently.'''
      results = {}
      
      # Group by type for batch queries
      by_type = defaultdict(list)
      for id_type, id_value in identifiers:
          by_type[id_type].append(id_value)
      
      # Batch resolve each type
      if "cik" in by_type:
          for cik in by_type["cik"]:
              results[("cik", cik)] = store.get_entities_by_cik(cik)
      
      if "ticker" in by_type:
          for ticker in by_type["ticker"]:
              results[("ticker", ticker)] = store.get_entities_by_ticker(ticker)
      
      return results
  
  
  PATTERN 3: Cached Resolution (for web apps)
  
  from functools import lru_cache
  
  @lru_cache(maxsize=10000)
  def cached_resolve(id_type: str, id_value: str) -> Entity | None:
      '''Cached entity resolution.'''
      if id_type == "cik":
          entities = store.get_entities_by_cik(id_value)
      elif id_type == "ticker":
          entities = store.get_entities_by_ticker(id_value)
      else:
          entities = []
      return entities[0] if entities else None
  
  
  PATTERN 4: Qualified Ticker Resolution
  
  def resolve_ticker(ticker: str, mic: str = None, exchange: str = None) -> Entity | None:
      '''Resolve ticker with optional exchange qualification.'''
      
      listings = store.get_listings_by_ticker(ticker, mic=mic)
      
      if not listings:
          return None
      
      if len(listings) == 1:
          # Unambiguous
          security = store.get_security(listings[0].security_id)
          return store.get_entity(security.entity_id)
      
      # Multiple listings - need disambiguation
      if exchange:
          # Filter by exchange name
          listings = [l for l in listings if exchange.lower() in l.exchange.lower()]
      
      if listings:
          # Return primary listing or first match
          primary = next((l for l in listings if l.is_primary), listings[0])
          security = store.get_security(primary.security_id)
          return store.get_entity(security.entity_id)
      
      return None
""")


def main() -> None:
    """Run all performance and global ticker demonstrations."""
    
    print_header("EntitySpine Performance & Global Tickers")
    print("This example covers memory estimation, optimization, and global ticker handling.")
    
    demo_memory_estimation()
    demo_performance_optimization()
    demo_global_ticker_handling()
    demo_optimized_lookup_patterns()
    
    print_header("Summary")
    print("""
  KEY TAKEAWAYS:
  
  1. MEMORY: ~10KB per entity with full identifiers
     - 50,000 entities = ~500 MB
     - Use Tier 1 (SQLite) for datasets > 10k
  
  2. PERFORMANCE: Dict-based indexes give O(1) lookups
     - CIK lookup: < 0.1 ms
     - Tier 0 is faster for pure in-memory
     - Tier 1 better for persistence + SQL
  
  3. GLOBAL TICKERS: Always use MIC codes
     - Disambiguates same ticker on different exchanges
     - Store: (ticker, mic, exchange, currency)
     - Query: get_listings_by_ticker(ticker, mic=mic)
  
  4. OPTIMIZATION PATTERNS:
     - Batch loading via load_sec_json()
     - Identifier routing by format
     - LRU caching for web apps
     - Qualified ticker resolution
""")


if __name__ == "__main__":
    main()
