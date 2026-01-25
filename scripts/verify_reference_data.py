#!/usr/bin/env python3
"""
Quick EntitySpine Reference Data Verification

Run this to verify your EntitySpine database is set up correctly.
"""

from entityspine import (
    ticker, cik, name, tickers, ciks, names,
    lei_from_isin, isins_from_lei, bic_from_lei,
    get_db_path,
)


def main():
    print("=" * 60)
    print("EntitySpine Reference Data Verification")
    print("=" * 60)
    print(f"\nDatabase: {get_db_path()}\n")
    
    # Test SEC lookups
    tests_passed = 0
    tests_failed = 0
    
    print("--- SEC Ticker/CIK Lookups ---")
    
    # Test 1: CIK -> Ticker
    result = ticker("0000320193")
    if result == "AAPL":
        print(f"  ✓ ticker('0000320193') = {result}")
        tests_passed += 1
    else:
        print(f"  ✗ ticker('0000320193') = {result} (expected AAPL)")
        tests_failed += 1
    
    # Test 2: Ticker -> CIK
    result = cik("NVDA")
    if result == "0001045810":
        print(f"  ✓ cik('NVDA') = {result}")
        tests_passed += 1
    else:
        print(f"  ✗ cik('NVDA') = {result} (expected 0001045810)")
        tests_failed += 1
    
    # Test 3: Ticker -> Name
    result = name("MSFT")
    if result and "MICROSOFT" in result.upper():
        print(f"  ✓ name('MSFT') = {result}")
        tests_passed += 1
    else:
        print(f"  ✗ name('MSFT') = {result}")
        tests_failed += 1
    
    # Test 4: Batch lookup
    results = tickers(["0000320193", "0001018724", "0001652044"])
    expected = ["AAPL", "AMZN", "GOOGL"]
    if results == expected:
        print(f"  ✓ tickers([AAPL CIK, AMZN CIK, GOOGL CIK]) = {results}")
        tests_passed += 1
    else:
        print(f"  ✗ tickers([...]) = {results} (expected {expected})")
        tests_failed += 1
    
    print("\n--- ISIN/LEI Lookups ---")
    
    # Test 5: ISIN -> LEI (Apple)
    apple_isin = "US0378331005"
    result = lei_from_isin(apple_isin)
    if result == "HWUPKR0MPOU8FGXBT394":
        print(f"  ✓ lei_from_isin('{apple_isin}') = {result}")
        tests_passed += 1
    else:
        print(f"  ✗ lei_from_isin('{apple_isin}') = {result} (expected HWUPKR0MPOU8FGXBT394)")
        tests_failed += 1
    
    # Test 6: LEI -> ISINs
    apple_lei = "HWUPKR0MPOU8FGXBT394"
    results = isins_from_lei(apple_lei)
    if len(results) > 0 and apple_isin in results:
        print(f"  ✓ isins_from_lei('{apple_lei}') returned {len(results)} ISINs")
        tests_passed += 1
    else:
        print(f"  ✗ isins_from_lei returned unexpected results")
        tests_failed += 1
    
    print(f"\n--- Results ---")
    print(f"  Passed: {tests_passed}")
    print(f"  Failed: {tests_failed}")
    
    if tests_failed == 0:
        print("\n✓ All tests passed! Your EntitySpine database is ready.")
    else:
        print("\n✗ Some tests failed. Check your database.")
    
    print()
    print("=" * 60)
    print("Usage Examples")
    print("=" * 60)
    print("""
    from entityspine import ticker, cik, name, lei_from_isin
    
    # Basic lookups
    ticker("0000320193")   # -> "AAPL"
    cik("NVDA")            # -> "0001045810"
    name("GOOGL")          # -> "Alphabet Inc."
    
    # ISIN lookups
    lei_from_isin("US0378331005")  # -> "HWUPKR0MPOU8FGXBT394"
    
    # Batch lookups (great for DataFrames)
    df['ticker'] = tickers(df['cik'])
    df['company'] = names(df['ticker'])
""")


if __name__ == "__main__":
    main()
