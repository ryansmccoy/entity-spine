#!/usr/bin/env python3
"""
Real SEC Filing Entity Resolution Example

This example demonstrates EntitySpine's entity resolution capabilities using
actual SEC EDGAR data. It shows how to:

1. Resolve companies by ticker, CIK, and name
2. Handle ambiguous queries (common names, ticker changes)
3. Work with historical ticker lookups
4. Batch-process multiple identifiers

Real-world use case: You're processing SEC filings and need to normalize
all company identifiers to canonical entities with consistent IDs.

Run: python examples/07_real_sec_resolution.py
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

# Add entityspine to path for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from entityspine import (
    EntityResolver,
    ResolverConfig,
    SqliteStore,
    create_entity,
    create_listing,
    create_security,
    create_claim,
    IdentifierScheme,
)


def print_header(title: str) -> None:
    """Print a formatted section header."""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print('=' * 70)


def print_result(result: Any, query: str) -> None:
    """Print resolution result details."""
    print(f"\n  Query: '{query}'")
    print(f"  Status: {result.status.value}")
    
    if result.found:
        entity = result.entity
        print(f"  [FOUND] {entity.primary_name}")
        print(f"     Entity ID: {entity.entity_id}")
        print(f"     CIK: {entity.source_id}")
        print(f"     Confidence: {result.confidence:.2%}")
    else:
        print(f"  [NOT FOUND]")
        if result.candidates:
            print(f"     Candidates: {len(result.candidates)}")
            for cand in result.candidates[:3]:
                print(f"       - {cand.entity.primary_name} (score: {cand.score:.2f})")
    
    if result.warnings:
        for warning in result.warnings:
            print(f"  [WARNING] {warning}")


def setup_real_sec_data(store: SqliteStore) -> None:
    """
    Load real SEC company data structure.
    
    This simulates the data structure from SEC's company_tickers.json
    which contains ~10,000 companies.
    """
    # Real SEC companies (actual CIKs from SEC EDGAR)
    companies = [
        # Tech Giants
        {"cik_str": "320193", "ticker": "AAPL", "title": "Apple Inc."},
        {"cik_str": "789019", "ticker": "MSFT", "title": "MICROSOFT CORP"},
        {"cik_str": "1652044", "ticker": "GOOGL", "title": "Alphabet Inc."},
        {"cik_str": "1652044", "ticker": "GOOG", "title": "Alphabet Inc."},  # Dual class shares
        {"cik_str": "1318605", "ticker": "TSLA", "title": "Tesla, Inc."},
        {"cik_str": "1018724", "ticker": "AMZN", "title": "AMAZON COM INC"},
        {"cik_str": "1326801", "ticker": "META", "title": "Meta Platforms, Inc."},
        {"cik_str": "1045810", "ticker": "NVDA", "title": "NVIDIA CORP"},
        
        # Finance
        {"cik_str": "70858", "ticker": "BAC", "title": "BANK OF AMERICA CORP"},
        {"cik_str": "19617", "ticker": "JPM", "title": "JPMORGAN CHASE & CO"},
        {"cik_str": "831001", "ticker": "C", "title": "CITIGROUP INC"},
        {"cik_str": "1364742", "ticker": "GS", "title": "Goldman Sachs Group Inc"},
        {"cik_str": "72971", "ticker": "WFC", "title": "WELLS FARGO & COMPANY"},
        {"cik_str": "1067983", "ticker": "BRK-A", "title": "BERKSHIRE HATHAWAY INC"},
        {"cik_str": "1067983", "ticker": "BRK-B", "title": "BERKSHIRE HATHAWAY INC"},
        
        # Healthcare/Pharma
        {"cik_str": "200406", "ticker": "JNJ", "title": "JOHNSON & JOHNSON"},
        {"cik_str": "78003", "ticker": "PFE", "title": "PFIZER INC"},
        {"cik_str": "1551152", "ticker": "ABBV", "title": "AbbVie Inc."},
        {"cik_str": "310158", "ticker": "MRK", "title": "Merck & Co., Inc."},
        {"cik_str": "14272", "ticker": "BMY", "title": "BRISTOL MYERS SQUIBB CO"},
        
        # Consumer
        {"cik_str": "21344", "ticker": "KO", "title": "COCA COLA CO"},
        {"cik_str": "77476", "ticker": "PEP", "title": "PEPSICO INC"},
        {"cik_str": "80424", "ticker": "PG", "title": "PROCTER & GAMBLE Co"},
        {"cik_str": "104169", "ticker": "WMT", "title": "Walmart Inc."},
        {"cik_str": "1800", "ticker": "ABT", "title": "ABBOTT LABORATORIES"},
        
        # Energy
        {"cik_str": "34088", "ticker": "XOM", "title": "EXXON MOBIL CORP"},
        {"cik_str": "93410", "ticker": "CVX", "title": "CHEVRON CORP"},
        {"cik_str": "1163165", "ticker": "COP", "title": "ConocoPhillips"},
        
        # Industrials
        {"cik_str": "40545", "ticker": "GE", "title": "GENERAL ELECTRIC CO"},
        {"cik_str": "12927", "ticker": "BA", "title": "BOEING CO"},
        {"cik_str": "63908", "ticker": "MMM", "title": "3M CO"},
        {"cik_str": "50104", "ticker": "HON", "title": "HONEYWELL INTERNATIONAL INC"},
        {"cik_str": "18230", "ticker": "CAT", "title": "CATERPILLAR INC"},
        
        # Telecom/Media
        {"cik_str": "732717", "ticker": "T", "title": "AT&T INC."},
        {"cik_str": "732712", "ticker": "VZ", "title": "VERIZON COMMUNICATIONS INC"},
        {"cik_str": "1001039", "ticker": "CMCSA", "title": "COMCAST CORP"},
        {"cik_str": "1001082", "ticker": "NFLX", "title": "NETFLIX INC"},
        {"cik_str": "1418091", "ticker": "DIS", "title": "Walt Disney Co"},
        
        # Semiconductors
        {"cik_str": "2488", "ticker": "AMD", "title": "ADVANCED MICRO DEVICES INC"},
        {"cik_str": "50863", "ticker": "INTC", "title": "INTEL CORP"},
        {"cik_str": "1341439", "ticker": "AVGO", "title": "Broadcom Inc."},
        {"cik_str": "97476", "ticker": "TXN", "title": "TEXAS INSTRUMENTS INC"},
        
        # Companies with name changes (for historical examples)
        # Facebook became Meta
        # {"cik_str": "1326801", "ticker": "FB", "title": "Facebook, Inc."},  # Old ticker
    ]
    
    # Convert to SEC JSON format
    sec_data = {str(i): c for i, c in enumerate(companies)}
    
    # Load into store
    count = store.load_sec_json(sec_data)
    print(f"  Loaded {count} entities from SEC data")


def example_1_ticker_resolution(resolver: EntityResolver) -> None:
    """Resolve companies by ticker symbol."""
    print_header("Example 1: Ticker Resolution")
    
    # Common tickers
    tickers = ["AAPL", "MSFT", "TSLA", "NVDA", "JPM", "META"]
    
    for ticker in tickers:
        result = resolver.resolve(ticker)
        print_result(result, ticker)


def example_2_cik_resolution(resolver: EntityResolver) -> None:
    """Resolve companies by SEC CIK number."""
    print_header("Example 2: CIK Resolution")
    
    # Various CIK formats (SEC accepts with/without leading zeros)
    ciks = [
        "0000320193",  # Apple - full padded
        "320193",      # Apple - without padding
        "789019",      # Microsoft
        "1318605",     # Tesla
        "1067983",     # Berkshire Hathaway
    ]
    
    for cik in ciks:
        result = resolver.resolve(cik)
        print_result(result, cik)


def example_3_fuzzy_name_resolution(resolver: EntityResolver) -> None:
    """Resolve companies by name (fuzzy matching)."""
    print_header("Example 3: Fuzzy Name Resolution")
    
    # Try various name formats/misspellings
    names = [
        "Apple Inc",          # Exact
        "apple",              # Lowercase
        "APPLE INC.",         # Uppercase with period
        "MICROSOFT CORP",     # All caps (SEC style)
        "Microsoft",          # Natural casing
        "Tesla Motors",       # Old name
        "facebook",           # Old brand name → should find Meta
        "JP Morgan",          # Common abbreviation
        "JPMorgan Chase",     # Variant spacing
        "Alphabet",           # Parent company
        "Google",             # Brand name → should find Alphabet
        "Amazon",             # Shortened
        "Amazon.com",         # Domain-style
        "Berkshire",          # Partial name
    ]
    
    for name in names:
        result = resolver.resolve(name)
        print_result(result, name)


def example_4_batch_resolution(resolver: EntityResolver) -> None:
    """Batch process multiple identifiers."""
    print_header("Example 4: Batch Resolution")
    
    # Mixed identifier types
    identifiers = [
        "AAPL",
        "789019",
        "Tesla Inc",
        "NVDA",
        "0000070858",
        "Goldman Sachs",
        "WMT",
        "Procter Gamble",
    ]
    
    print("\n  Processing batch of", len(identifiers), "identifiers...")
    
    results = resolver.resolve_many(identifiers)
    
    resolved = sum(1 for r in results if r.found)
    print(f"\n  Results: {resolved}/{len(identifiers)} resolved successfully")
    
    for identifier, result in zip(identifiers, results):
        status = "[OK]" if result.found else "[--]"
        name = result.entity.primary_name if result.found else "Not found"
        print(f"  {status} {identifier:20} -> {name}")


def example_5_ambiguous_queries(resolver: EntityResolver) -> None:
    """Handle ambiguous queries with multiple matches."""
    print_header("Example 5: Handling Ambiguous Queries")
    
    # These queries might match multiple entities
    ambiguous = [
        "Bank",               # Many banks
        "Inc",                # Part of many names
        "General",            # Multiple "General" companies
        "American",           # Multiple "American" companies
        "BRK",                # Two share classes (A and B)
        "GOOG",               # Alphabet has GOOG and GOOGL
    ]
    
    for query in ambiguous:
        result = resolver.resolve(query)
        print(f"\n  Query: '{query}'")
        print(f"  Status: {result.status.value}")
        
        if result.found:
            print(f"  Primary Match: {result.entity.primary_name}")
            
        if result.candidates and len(result.candidates) > 1:
            print(f"  Additional Candidates ({len(result.candidates) - 1} more):")
            for cand in result.candidates[1:4]:  # Show top 3 alternatives
                print(f"    - {cand.entity.primary_name} (score: {cand.score:.2f})")


def example_6_sec_filing_workflow(resolver: EntityResolver) -> None:
    """
    Real-world workflow: Processing SEC filing data.
    
    When processing SEC filings, you encounter company identifiers in
    various formats. EntitySpine normalizes them all to canonical entities.
    """
    print_header("Example 6: SEC Filing Processing Workflow")
    
    # Simulated filing data (as it appears in SEC EDGAR)
    filings = [
        {"accession": "0000320193-24-000081", "filer_cik": "320193", "filer_name": "Apple Inc."},
        {"accession": "0000789019-24-000012", "filer_cik": "789019", "filer_name": "MICROSOFT CORP"},
        {"accession": "0001318605-24-000005", "filer_cik": "1318605", "filer_name": "Tesla, Inc."},
        {"accession": "0001326801-24-000019", "filer_cik": "1326801", "filer_name": "Meta Platforms, Inc."},
        {"accession": "0000070858-24-000033", "filer_cik": "70858", "filer_name": "BANK OF AMERICA CORP /DE/"},
    ]
    
    print("\n  Processing SEC filings...\n")
    
    for filing in filings:
        # Resolve by CIK (most reliable)
        result = resolver.resolve(filing["filer_cik"])
        
        if result.found:
            entity = result.entity
            
            # Check if SEC name matches our canonical name
            name_match = filing["filer_name"].upper() == entity.primary_name.upper()
            
            print(f"  Filing: {filing['accession']}")
            print(f"    SEC CIK: {filing['filer_cik']} -> Entity ID: {entity.entity_id}")
            print(f"    SEC Name: {filing['filer_name']}")
            print(f"    Canonical: {entity.primary_name}")
            print(f"    Name Match: {'[OK]' if name_match else '[DIFFERS]'}")
            print()


def example_7_identifier_scope_awareness(resolver: EntityResolver) -> None:
    """
    Demonstrate identifier scope awareness.
    
    EntitySpine understands that:
    - CIK belongs to ENTITY (the legal filer)
    - Ticker belongs to LISTING (exchange-specific)
    - ISIN belongs to SECURITY (the financial instrument)
    """
    print_header("Example 7: Identifier Scope Awareness")
    
    # Berkshire Hathaway has two share classes (same entity, different securities)
    print("\n  Berkshire Hathaway - Two Share Classes:\n")
    
    result_a = resolver.resolve("BRK-A")
    result_b = resolver.resolve("BRK-B")
    
    if result_a.found and result_b.found:
        print(f"  BRK-A -> Entity: {result_a.entity.primary_name}")
        print(f"  BRK-B -> Entity: {result_b.entity.primary_name}")
        
        # Same entity?
        same_entity = result_a.entity.entity_id == result_b.entity.entity_id
        print(f"\n  Same Entity? {same_entity}")
        print("  (Different TICKERS point to same ENTITY via different SECURITIES)")
    
    # Alphabet has two share classes
    print("\n\n  Alphabet Inc - Dual Class Structure:\n")
    
    result_googl = resolver.resolve("GOOGL")
    result_goog = resolver.resolve("GOOG")
    
    if result_googl.found and result_goog.found:
        print(f"  GOOGL (Class A) -> Entity: {result_googl.entity.primary_name}")
        print(f"  GOOG (Class C) -> Entity: {result_goog.entity.primary_name}")
        
        same_entity = result_googl.entity.entity_id == result_goog.entity.entity_id
        print(f"\n  Same Entity? {same_entity}")


def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print("  EntitySpine - Real SEC Filing Entity Resolution")
    print("  Demonstrating resolution with actual SEC EDGAR data structures")
    print("=" * 70)
    
    # Create an in-memory SQLite store
    store = SqliteStore(":memory:")
    store.initialize()
    
    print("\nSetting up SEC data...")
    setup_real_sec_data(store)
    
    # Create resolver with the pre-loaded store
    config = ResolverConfig(
        auto_load_sec=False,  # We've already loaded data
        min_fuzzy_score=0.6,
    )
    resolver = EntityResolver(config=config, store=store)
    
    # Run examples
    example_1_ticker_resolution(resolver)
    example_2_cik_resolution(resolver)
    example_3_fuzzy_name_resolution(resolver)
    example_4_batch_resolution(resolver)
    example_5_ambiguous_queries(resolver)
    example_6_sec_filing_workflow(resolver)
    example_7_identifier_scope_awareness(resolver)
    
    print_header("Summary")
    print(f"\n  Total entities in store: {store.entity_count()}")
    print(f"  Total listings in store: {store.listing_count()}")
    print("\n  EntitySpine makes SEC data useful!\n")


if __name__ == "__main__":
    main()
