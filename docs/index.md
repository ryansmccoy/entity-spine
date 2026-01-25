# EntitySpine

**Entity resolution for the real world** - Map companies, people, and organizations across data sources. Zero dependencies. Built on SEC data. Scales to enterprise.

---

<div class="grid cards" markdown>

- :material-atom:{ .lg .middle } **Zero Dependencies**

    ---

    Pure Python dataclasses. No required dependencies.
    Works anywhere Python runs.

- :material-office-building:{ .lg .middle } **Built for SEC Data**

    ---

    Load 14,000+ companies from SEC company_tickers.json.
    Track CIK identifiers, filings, and relationships.

- :material-graph-outline:{ .lg .middle } **Entity Networks**

    ---

    Map corporate hierarchies, competitors, supply chains.
    Model ownership and business relationships.

- :material-database-arrow-up:{ .lg .middle } **Scale as You Grow**

    ---

    JSON → SQLite → PostgreSQL. Same domain model,
    different storage tiers.

</div>

---

## What is EntitySpine?

**EntitySpine** helps you answer questions like:

- "Which companies are competitors in the same market?"
- "What's the corporate hierarchy for this subsidiary?"
- "Who are the suppliers in this company's supply chain?"
- "How do I track entities across different identifier schemes?"

It provides:

1. **Entity Resolution**: Match and link entities across data sources
2. **Relationship Modeling**: Corporate hierarchies, ownership, supply chains
3. **Identifier Mapping**: CIK, LEI, TICKER, CUSIP, ISIN (support for major schemes)
4. **Provenance Tracking**: Know where each piece of data came from

## The EntitySpine Journey

### 1️⃣ Start Simple: Entity Basics

Map a single company with zero dependencies:

```python
from entityspine import Entity, SqliteStore

# Create an entity - no external dependencies needed
apple = Entity(
    primary_name="Apple Inc.",
    source_system="SEC",
    source_id="0000320193"  # SEC CIK
)

# Store it (in-memory SQLite, still zero deps)
store = SqliteStore(":memory:")
store.save(apple)
```

**Zero dependencies. Just Python.**

### 2️⃣ Add SEC Data: Real Companies

Load real companies from SEC's public data:

```python
from entityspine import load_sec_data

# Download SEC company_tickers.json (14K+ companies)
entities = load_sec_data(download_dir="data/sec")

# Now you have: Apple, Microsoft, Tesla, etc.
# All with CIK identifiers automatically mapped
```

**Built on official SEC data. No API keys needed.**

### 3️⃣ Map Identifiers: Connect Data Sources

Track the same company across different identifier schemes:

```python
from entityspine import IdentifierClaim

# Add a stock ticker
ticker_claim = IdentifierClaim(
    entity_id=apple.entity_id,
    scheme="TICKER",
    identifier="AAPL",
    source_system="SEC",
    confidence=1.0
)

# Add LEI (Legal Entity Identifier)
lei_claim = IdentifierClaim(
    entity_id=apple.entity_id,
    scheme="LEI",
    identifier="HWUPKR0MPOU8FGXBT394",
    source_system="GLEIF",
    confidence=1.0
)

# Now you can find Apple by CIK, TICKER, or LEI
```

**Support for**: CIK, LEI, TICKER, CUSIP, ISIN, FIGI, PermID, and more.

### 4️⃣ Build Relationships: Corporate Networks

Model how companies connect to each other:

```python
from entityspine import Relationship

# Map corporate hierarchy
alphabet = Entity(primary_name="Alphabet Inc.", ...)
google = Entity(primary_name="Google LLC.", ...)

parent_of = Relationship(
    from_entity_id=alphabet.entity_id,
    relationship_type="PARENT_OF",
    to_entity_id=google.entity_id,
    source_system="SEC",
    confidence=1.0
)

# Map competitors
apple_vs_samsung = Relationship(
    from_entity_id=apple.entity_id,
    relationship_type="COMPETES_WITH",
    to_entity_id=samsung.entity_id,
    source_system="analyst_research",
    confidence=0.85
)

# Map supply chain
supplier = Relationship(
    from_entity_id=apple.entity_id,
    relationship_type="SUPPLIER",
    to_entity_id=foxconn.entity_id,
    source_system="annual_report",
    confidence=0.90
)
```

**Build knowledge graphs** of corporate ecosystems.

### 5️⃣ Financial Markets: Securities & Exchanges

Extend to financial instruments:

```python
from entityspine import Security, Listing

# Create a security (stock)
aapl_stock = Security(
    security_id="...",
    entity_id=apple.entity_id,
    security_type="COMMON_STOCK",
    primary_ticker="AAPL"
)

# Track where it trades
nasdaq_listing = Listing(
    security_id=aapl_stock.security_id,
    exchange_code="XNAS",  # NASDAQ
    ticker="AAPL",
    listing_status="ACTIVE"
)
```

**Track securities, exchanges, and market infrastructure.**

## Installation

```bash
# Core only - zero dependencies
pip install entityspine

# With optional dependencies
pip install entityspine[api]      # REST API
pip install entityspine[cli]      # Command-line tools
pip install entityspine[pydantic] # Pydantic wrappers
pip install entityspine[orm]      # SQLModel ORM
pip install entityspine[full]     # Everything
```

## Storage Tiers: Scale as You Grow

| Tier | Storage | Use Case | Dependencies |
|------|---------|----------|--------------|
| 0 | JSON files | Prototyping, <100 entities | **Zero** |
| 1 | SQLite | Development, <100K entities | **Zero** (stdlib) |
| 2 | DuckDB | Analytics, <1M entities | `duckdb` |
| 3 | PostgreSQL | Production, unlimited | `psycopg2` |
| 4 | Elasticsearch | Search, text queries | `elasticsearch` |
| 5 | Neo4j | Graph queries, complex paths | `neo4j` |

**Start with Tier 0 or 1 (zero dependencies), scale up when needed.**

## Architecture Philosophy

EntitySpine follows a simple progression:

1. **Entities First**: Companies, organizations, people
2. **Identifiers Next**: CIK, LEI, TICKER, CUSIP, etc.
3. **Relationships Then**: Parent/child, competitors, suppliers
4. **Securities Last**: Stocks, bonds, instruments

Each layer builds on the previous one. Use what you need, ignore the rest.

## Next Steps

**Getting Started**:
- [Quick Start Guide](README.md) - Installation and first steps
- [Core Concepts](guides/CORE_CONCEPTS.md) - Entities, identifiers, relationships
- [SEC Data Loading](guides/SEC_DATA_GUIDE.md) - Load real company data

**Building Networks**:
- [Corporate Hierarchies](guides/CORPORATE_NETWORKS.md) - Parent/child relationships
- [Supply Chains](guides/SUPPLY_CHAINS.md) - Supplier/customer mapping
- [Competitor Analysis](guides/COMPETITORS.md) - Market positioning

**Financial Markets**:
- [Securities & Listings](guides/SECURITIES_GUIDE.md) - Stocks, bonds, instruments
- [Market Infrastructure](guides/MARKET_DATA_ARCHITECTURE.md) - Exchanges, venues

**Advanced**:
- [Tier Architecture](architecture/ARCHITECTURE_AND_TIERS.md) - Storage tiers
- [API Reference](api/domain/index.md) - Complete API docs
- [v0.3.3 Release](DOCUMENTATION_REVIEW.md) - Latest release notes

## License

MIT License - see [LICENSE](https://github.com/ryansmccoy/entity-spine/blob/main/LICENSE) for details.
