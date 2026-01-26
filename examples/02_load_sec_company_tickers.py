"""
02_load_sec_company_tickers.py

Load SEC's company_tickers.json into EntitySpine for entity resolution.

This example demonstrates:
- Downloading SEC data with proper User-Agent
- Bulk loading into EntitySpine
- Searching for entities by ticker or name
"""

from __future__ import annotations

import json
from pathlib import Path

# For HTTP requests (optional, can use urllib if httpx not available)
try:
    import httpx

    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False
    import urllib.request

from entityspine import SqliteStore


def download_sec_data(cache_path: Path | None = None) -> dict:
    """Download SEC company_tickers.json with caching.

    Args:
        cache_path: Optional path to cache the downloaded data.

    Returns:
        Dictionary of SEC company data.
    """
    # Check cache first
    if cache_path and cache_path.exists():
        print(f"Loading from cache: {cache_path}")
        return json.loads(cache_path.read_text())

    url = "https://www.sec.gov/files/company_tickers.json"
    headers = {
        "User-Agent": "EntitySpine/0.3.0 (github.com/ryansmccoy/entity-spine)",
        "Accept": "application/json",
    }

    print(f"Downloading: {url}")

    if HAS_HTTPX:
        response = httpx.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
    else:
        # Fallback to urllib
        req = urllib.request.Request(url, headers=headers)  # noqa: S310
        with urllib.request.urlopen(req, timeout=30) as response:  # noqa: S310
            data = json.loads(response.read().decode())

    # Save to cache
    if cache_path:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(data, indent=2))
        print(f"Cached to: {cache_path}")

    return data


def main() -> None:
    """Main example function."""
    # Download SEC data (with caching)
    cache_path = Path("./fixtures/company_tickers.json")
    sec_data = download_sec_data(cache_path)

    print(f"\nLoaded {len(sec_data)} entries from SEC")

    # Create EntitySpine store
    store = SqliteStore(":memory:")
    store.initialize()

    # Load SEC data
    loaded_count = store.load_sec_json(sec_data)
    print(f"Loaded {loaded_count} entities into EntitySpine")

    # Example searches
    print("\n" + "=" * 60)
    print("SEARCH EXAMPLES")
    print("=" * 60)

    queries = ["AAPL", "Microsoft", "GOOGL", "Tesla", "0000320193"]

    for query in queries:
        print(f"\nQuery: '{query}'")
        results = store.search_entities(query, limit=3)
        for entity, score in results:
            cik = entity.source_id or "N/A"
            print(f"  {score:.2f} | {entity.primary_name} (CIK: {cik})")

    # Statistics
    print("\n" + "=" * 60)
    print("STORE STATISTICS")
    print("=" * 60)
    print(f"Total entities: {store.entity_count()}")


if __name__ == "__main__":
    main()
