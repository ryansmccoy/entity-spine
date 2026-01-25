#!/usr/bin/env python3
"""
EntitySpine Tier Comparison Example

This example compares all available tiers side-by-side, showing:
- Which features each tier supports
- Performance characteristics
- When to use each tier

TIERS:
- Tier 0: JSON/Memory (stdlib only)
- Tier 1: SQLite (stdlib only)
- Tier 2: DuckDB (optional, analytics)
- Tier 3: PostgreSQL (optional, production)
- Tier 4/5: PostgreSQL + Elasticsearch + Neo4j (optional, enterprise)

USAGE:
    python examples/tier_comparison.py
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import date
from typing import Any

from entityspine.domain import (
    Entity,
    EntityType,
    EntityStatus,
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


@dataclass
class BenchmarkResult:
    """Results from a benchmark run."""
    tier: str
    load_time_ms: float
    search_time_ms: float
    resolve_time_ms: float
    entity_count: int
    features: list[str]


def generate_test_data(count: int) -> dict[str, dict]:
    """Generate test SEC-format data."""
    return {
        str(i): {
            "cik_str": 1000000 + i,
            "ticker": f"TST{i:04d}",
            "title": f"Test Corporation {i:04d}",
        }
        for i in range(count)
    }


def benchmark_tier0(data: dict) -> BenchmarkResult:
    """Benchmark Tier 0 (JSON/Memory) store."""
    store = JsonEntityStore()
    store.initialize()
    
    # Benchmark load
    start = time.perf_counter()
    count = store.load_sec_json(data)
    load_time = (time.perf_counter() - start) * 1000
    
    # Benchmark search
    start = time.perf_counter()
    for _ in range(100):
        store.search_entities("Test", limit=10)
    search_time = (time.perf_counter() - start) * 1000 / 100
    
    # Benchmark resolve
    start = time.perf_counter()
    for _ in range(100):
        store.get_entities_by_cik("1000050")
    resolve_time = (time.perf_counter() - start) * 1000 / 100
    
    store.close()
    
    return BenchmarkResult(
        tier="Tier 0 (JSON/Memory)",
        load_time_ms=load_time,
        search_time_ms=search_time,
        resolve_time_ms=resolve_time,
        entity_count=count,
        features=[
            "Zero dependencies",
            "In-memory storage",
            "JSON file persistence",
            "Basic substring search",
            "Dict-based indexes",
        ],
    )


def benchmark_tier1(data: dict) -> BenchmarkResult:
    """Benchmark Tier 1 (SQLite) store."""
    store = SqliteStore(db_path=":memory:")
    store.initialize()
    
    # Benchmark load
    start = time.perf_counter()
    count = store.load_sec_json(data)
    load_time = (time.perf_counter() - start) * 1000
    
    # Benchmark search
    start = time.perf_counter()
    for _ in range(100):
        store.search_entities("Test", limit=10)
    search_time = (time.perf_counter() - start) * 1000 / 100
    
    # Benchmark resolve
    start = time.perf_counter()
    for _ in range(100):
        store.get_entities_by_cik("1000050")
    resolve_time = (time.perf_counter() - start) * 1000 / 100
    
    store.close()
    
    return BenchmarkResult(
        tier="Tier 1 (SQLite)",
        load_time_ms=load_time,
        search_time_ms=search_time,
        resolve_time_ms=resolve_time,
        entity_count=count,
        features=[
            "Zero dependencies",
            "Persistent storage",
            "SQL query support",
            "LIKE pattern search",
            "ACID transactions",
            "FTS5 optional",
        ],
    )


def check_optional_stores() -> dict[str, bool]:
    """Check which optional stores are available."""
    available = {}
    
    # DuckDB
    try:
        import duckdb
        available["duckdb"] = True
    except ImportError:
        available["duckdb"] = False
    
    # Elasticsearch
    try:
        from entityspine.stores import ElasticsearchStore
        available["elasticsearch"] = True
    except ImportError:
        available["elasticsearch"] = False
    
    # Neo4j
    try:
        from entityspine.stores import Neo4jStore
        available["neo4j"] = True
    except ImportError:
        available["neo4j"] = False
    
    return available


def main() -> None:
    """Run tier comparison benchmarks."""
    
    print_header("EntitySpine Tier Comparison")
    print("Comparing available storage tiers...")
    
    # Check optional stores
    available = check_optional_stores()
    print("\nOptional Dependencies:")
    print(f"  DuckDB (Tier 2):        {'✓ Available' if available['duckdb'] else '✗ Not installed (pip install duckdb)'}")
    print(f"  Elasticsearch (Tier 4): {'✓ Available' if available['elasticsearch'] else '✗ Not installed (pip install elasticsearch)'}")
    print(f"  Neo4j (Tier 4):         {'✓ Available' if available['neo4j'] else '✗ Not installed (pip install neo4j)'}")
    
    # Generate test data
    print_header("Benchmark Setup")
    test_sizes = [100, 500]
    
    for size in test_sizes:
        print(f"\n--- {size} Entities ---")
        data = generate_test_data(size)
        
        # Benchmark each available tier
        results = []
        
        # Tier 0
        result0 = benchmark_tier0(data)
        results.append(result0)
        print(f"  Tier 0 (JSON):   load={result0.load_time_ms:.1f}ms, search={result0.search_time_ms:.2f}ms, resolve={result0.resolve_time_ms:.2f}ms")
        
        # Tier 1
        result1 = benchmark_tier1(data)
        results.append(result1)
        print(f"  Tier 1 (SQLite): load={result1.load_time_ms:.1f}ms, search={result1.search_time_ms:.2f}ms, resolve={result1.resolve_time_ms:.2f}ms")
    
    # Feature comparison
    print_header("Feature Comparison by Tier")
    
    comparison = """
╔══════════════════════════╦════════╦════════╦════════╦════════╦════════╗
║ Feature                  ║ Tier 0 ║ Tier 1 ║ Tier 2 ║ Tier 3 ║ Tier 4 ║
║                          ║  JSON  ║ SQLite ║ DuckDB ║ Postgres║ +ES+Neo║
╠══════════════════════════╬════════╬════════╬════════╬════════╬════════╣
║ Zero dependencies        ║   ✓    ║   ✓    ║   ✗    ║   ✗    ║   ✗    ║
║ Persistent storage       ║   ✓*   ║   ✓    ║   ✓    ║   ✓    ║   ✓    ║
║ SQL queries              ║   ✗    ║   ✓    ║   ✓    ║   ✓    ║   ✓    ║
║ LIKE pattern search      ║   ✗    ║   ✓    ║   ✓    ║   ✓    ║   ✓    ║
║ Full-text search         ║   ✗    ║   ✓**  ║   ✓**  ║   ✓    ║   ✓    ║
║ Analytics queries        ║   ✗    ║   ✗    ║   ✓    ║   ✓    ║   ✓    ║
║ Concurrent write         ║   ✗    ║   ✗    ║   ✗    ║   ✓    ║   ✓    ║
║ Horizontal scale         ║   ✗    ║   ✗    ║   ✗    ║   ✓    ║   ✓    ║
║ Fuzzy search             ║   ✗    ║   ✗    ║   ✗    ║   ✗    ║   ✓    ║
║ Graph traversal          ║   ✗    ║   ✗    ║   ✗    ║   ✗    ║   ✓    ║
║ Semantic search          ║   ✗    ║   ✗    ║   ✗    ║   ✗    ║   ✓    ║
╚══════════════════════════╩════════╩════════╩════════╩════════╩════════╝

* JSON persistence requires explicit save/close
** FTS5 (SQLite) / FTS (DuckDB) are optional extensions
"""
    print(comparison)
    
    # Use case recommendations
    print_header("Tier Selection Guide")
    
    guide = """
TIER 0: JSON/Memory (Zero Dependencies)
├── Best for: Prototyping, scripts, notebooks, testing
├── Dataset: < 50,000 entities
├── Requires: Nothing (stdlib only)
└── Install: pip install entityspine

TIER 1: SQLite (Zero Dependencies)
├── Best for: Single-user apps, embedded systems, medium datasets
├── Dataset: 50,000 - 500,000 entities
├── Requires: Nothing (stdlib sqlite3)
└── Install: pip install entityspine

TIER 2: DuckDB (Analytics)
├── Best for: Data science, analytics, Parquet integration
├── Dataset: 100,000 - 10,000,000 entities
├── Requires: pip install duckdb
└── Install: pip install entityspine[duckdb]

TIER 3: PostgreSQL (Production)
├── Best for: Production apps, concurrent users, web services
├── Dataset: 1,000,000+ entities
├── Requires: PostgreSQL server, psycopg/asyncpg
└── Install: pip install entityspine[postgres]

TIER 4/5: PostgreSQL + Elasticsearch + Neo4j (Enterprise)
├── Best for: Enterprise apps, fuzzy search, graph analytics
├── Dataset: 10,000,000+ entities
├── Requires: PG + ES + Neo4j infrastructure
└── Install: pip install entityspine[search,graph]

DECISION TREE:
  Need zero deps?
    ├── Yes → Need SQL? → Yes → Tier 1 (SQLite)
    │                   → No  → Tier 0 (JSON)
    └── No  → Need analytics? → Yes → Tier 2 (DuckDB)
            → Need production scale? → Yes → Tier 3 (PostgreSQL)
            → Need fuzzy/graph? → Yes → Tier 4/5 (Full Stack)
"""
    print(guide)


if __name__ == "__main__":
    main()
