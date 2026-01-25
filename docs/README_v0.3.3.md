# EntitySpine v0.3.3

**Zero-Dependency Entity Resolution for Financial Data**

[![PyPI](https://img.shields.io/pypi/v/entityspine?color=blue)](https://pypi.org/project/entityspine/)
[![Python](https://img.shields.io/pypi/pyversions/entityspine)](https://pypi.org/project/entityspine/)
[![License](https://img.shields.io/github/license/ryansmccoy/entity-spine)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-548%20passed-brightgreen)](tests/)
[![Coverage](https://img.shields.io/badge/coverage-40%25-orange)](tests/)

> From `company_tickers.json` to enterprise Knowledge Graph — **without forcing dependencies**

---

## 🎯 What is EntitySpine?

EntitySpine is a **lightweight entity resolution library** designed for SEC EDGAR data and financial entity management. It solves the fundamental problem: **connecting different identifiers to the same real-world entity**.

### The Entity Resolution Problem

```
❓ Is CIK 0000320193 the same as ticker AAPL?
❓ Did Facebook (ticker: FB) become Meta Platforms (ticker: META)?
❓ What's the LEI for Microsoft's CIK?
❓ Which entities are subsidiaries of Alphabet Inc.?
```

EntitySpine provides the **canonical data model** and **storage infrastructure** to answer these questions reliably.

---

## ⚡ Quick Start

### Installation

```bash
# Core (zero dependencies - stdlib only)
pip install entityspine

# With optional features
pip install entityspine[pydantic]    # Validation wrappers
pip install entityspine[orm]         # SQLModel/SQLAlchemy layer
pip install entityspine[api]         # FastAPI REST endpoints
pip install entityspine[cli]         # Command-line tools
pip install entityspine[dev]         # Development tools
pip install entityspine[all]         # Everything
```

### 30-Second Example

```python
from entityspine import SqliteStore

# Create in-memory store and load SEC data
store = SqliteStore(":memory:")
store.initialize()

# Auto-fetch and load ~14,000 SEC companies
store.load_sec_data()

# Resolve by ticker
entities = store.search_entities("AAPL")
entity, score = entities[0]
print(f"{entity.primary_name} - CIK: {entity.source_id}")
# Output: Apple Inc. - CIK: 0000320193

# Resolve by CIK
entity = store.get_entity_by_cik("0000320193")
print(entity.primary_name)
# Output: Apple Inc.
```

---

## 🏗️ Architecture

### Three-Layer Model: Entity ≠ Security ≠ Listing

EntitySpine distinguishes between three core concepts:

```
┌─────────────────────────────────────────────────────────┐
│                      ENTITY                             │
│                 "Apple Inc."                            │
│  (Legal/organizational identity - one per company)      │
│                                                         │
│  • CIK: 0000320193                                      │
│  • LEI: HWUPKR0MPOU8FGXBT394                            │
│  • EIN: 94-2404110                                      │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│                   SECURITY                              │
│            "Apple Common Stock"                         │
│  (Tradeable instrument - can have multiple per entity)  │
│                                                         │
│  • CUSIP: 037833100                                     │
│  • ISIN: US0378331005                                   │
│  • FIGI: BBG000B9XRY4                                   │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│                    LISTING                              │
│            "AAPL on NASDAQ"                             │
│  (Exchange-specific ticker - security can list on many) │
│                                                         │
│  • Ticker: AAPL                                         │
│  • Exchange: NASDAQ                                     │
│  • MIC: XNAS                                            │
└─────────────────────────────────────────────────────────┘
```

**Critical Design Rule**: `ticker` belongs on **Listing**, NOT on **Entity**.

---

## 📦 Core Features

### ✅ Zero-Dependency Core
- **Tier 0-1**: Pure stdlib (JSON, SQLite)
- **No required dependencies** for basic entity resolution
- Optional extras for advanced features

### ✅ Identifier Claims System
```python
from entityspine import IdentifierClaim, IdentifierScheme

# Track identifiers with provenance and confidence
claim = IdentifierClaim(
    entity_id="01JGXXX...",
    scheme=IdentifierScheme.CIK,
    value="0000320193",
    namespace="sec",
    source="company_tickers.json",
    confidence=1.0,
    verified=True
)
```

### ✅ Knowledge Graph Support
```python
from entityspine.domain import Person, RoleAssignment, NodeRef

# Model executives, relationships, and organizational structure
ceo = Person(
    full_name="Satya Nadella",
    first_name="Satya",
    last_name="Nadella"
)

role = RoleAssignment(
    person_ref=NodeRef("person", ceo.person_id),
    org_ref=NodeRef("entity", microsoft.entity_id),
    role_title="Chief Executive Officer",
    start_date=date(2014, 2, 4)
)
```

### ✅ Multi-Source Resolution
```python
# Search across CIK, ticker, name, LEI, CUSIP
queries = ["MSFT", "0000789019", "Microsoft", "INF4NPJ6J0M6"]

for query in queries:
    results = store.search_entities(query, limit=1)
    entity, score = results[0]
    print(f"'{query}' → {entity.primary_name} (score: {score:.2f})")
```

### ✅ Corporate Action Tracking
```python
# Track mergers, name changes, ticker changes
facebook_merged = facebook.with_update(
    status=EntityStatus.MERGED,
    redirect_to=meta.entity_id,
    redirect_reason="Rebranded to Meta Platforms",
    merged_at=utc_now()
)
```

---

## 📁 Project Structure

```
entityspine/
├── src/entityspine/               # Main package
│   ├── __init__.py                # Public API exports
│   │
│   ├── domain/                    # 🎯 Canonical domain models (stdlib only)
│   │   ├── __init__.py
│   │   ├── entity.py              # Entity (legal identity)
│   │   ├── security.py            # Security (tradeable instrument)
│   │   ├── listing.py             # Listing (exchange ticker)
│   │   ├── claim.py               # IdentifierClaim (with provenance)
│   │   ├── resolution.py          # Resolution results
│   │   ├── graph.py               # KG nodes (Person, Asset, Contract, etc.)
│   │   ├── markets.py             # Exchange, BrokerDealer, Clearinghouse
│   │   ├── observation.py         # Financial observations
│   │   ├── enums/                 # All enumerations
│   │   │   ├── identifiers.py     # IdentifierScheme, VendorNamespace
│   │   │   ├── markets.py         # AssetClass, SecurityType
│   │   │   └── ...
│   │   ├── validators.py          # Normalization & validation
│   │   └── reference_data/        # ISO standards, market data
│   │       ├── markets.py         # MIC codes, exchange mappings
│   │       ├── assetclasses.py    # Asset class definitions
│   │       └── vendorcodes.py     # Vendor identifier mappings
│   │
│   ├── stores/                    # 💾 Storage backends
│   │   ├── __init__.py
│   │   ├── sqlite_store.py        # Tier 1: SQLite (stdlib only)
│   │   ├── json_store.py          # Tier 0: JSON file (stdlib only)
│   │   ├── mappers.py             # Domain ↔ dict conversion
│   │   ├── elasticsearch_store.py # Tier 4: Search engine (optional)
│   │   └── neo4j_store.py         # Tier 5: Graph database (optional)
│   │
│   ├── sources/                   # 📥 Data source loaders
│   │   ├── __init__.py
│   │   ├── base.py                # Bronze/Silver layer base
│   │   ├── sec.py                 # SEC company_tickers.json
│   │   ├── gleif.py               # GLEIF LEI data
│   │   ├── iso3166.py             # Country codes
│   │   ├── iso4217.py             # Currency codes
│   │   └── iso10383.py            # MIC codes (exchanges)
│   │
│   ├── services/                  # 🔧 Business logic
│   │   ├── __init__.py
│   │   ├── resolver.py            # Entity resolution engine
│   │   ├── lookup.py              # Simple ticker/CIK lookup API
│   │   ├── fuzzy.py               # Fuzzy name matching
│   │   ├── conflicts.py           # Identifier conflict detection
│   │   ├── clustering.py          # Entity clustering/deduplication
│   │   ├── audit.py               # Data quality audits
│   │   └── timeline.py            # Temporal event tracking
│   │
│   ├── integration/               # 🔗 External integrations
│   │   ├── __init__.py
│   │   ├── contracts.py           # FilingFacts schema
│   │   ├── ingest.py              # Filing ingestion
│   │   └── normalize.py           # SEC normalization
│   │
│   ├── adapters/                  # 🔌 Optional adapters
│   │   ├── pydantic/              # Pydantic wrappers ([pydantic] extra)
│   │   │   ├── entity.py
│   │   │   ├── security.py
│   │   │   └── ...
│   │   ├── orm/                   # SQLModel/SQLAlchemy ([orm] extra)
│   │   │   ├── engine.py
│   │   │   ├── tables.py
│   │   │   └── repositories/
│   │   └── protocol.py            # Store protocol definition
│   │
│   ├── api/                       # 🌐 REST API ([api] extra)
│   │   ├── __init__.py
│   │   ├── app.py                 # FastAPI application
│   │   ├── deps.py                # Dependency injection
│   │   └── schemas.py             # Request/response models
│   │
│   ├── feeds/                     # 📡 Data feed adapters
│   │   ├── __init__.py
│   │   ├── adapters.py            # FeedSpine integration
│   │   └── sync.py                # Feed synchronization
│   │
│   ├── parser/                    # 📄 Filing parsers
│   │   ├── __init__.py
│   │   └── exhibit21.py           # Exhibit 21 subsidiary parser
│   │
│   ├── data/                      # 📊 Data utilities
│   │   ├── schema_detector.py     # Schema inference
│   │   ├── parquet_store.py       # Parquet backend
│   │   └── ...
│   │
│   ├── core/                      # 🛠️ Core utilities
│   │   ├── __init__.py
│   │   ├── ulid.py                # ULID generation
│   │   ├── timestamps.py          # UTC timestamps
│   │   ├── normalize.py           # Text normalization
│   │   ├── identifier.py          # Identifier classification
│   │   └── exceptions.py          # Custom exceptions
│   │
│   └── cli.py                     # 🖥️ Command-line interface ([cli] extra)
│
├── api/                           # 🐳 Docker deployment
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── main.py                    # Standalone API entry point
│
├── tests/                         # ✅ Test suite (548 tests)
│   ├── unit/                      # Unit tests
│   │   ├── domain/
│   │   ├── stores/
│   │   └── ...
│   ├── integration/               # Integration tests
│   │   ├── test_entity_storage_complete.py
│   │   ├── test_example_end_to_end.py
│   │   └── ...
│   ├── sources/                   # Source loader tests
│   ├── feeds/                     # Feed adapter tests
│   └── api/                       # API tests (requires [api] extra)
│
├── examples/                      # 📚 Usage examples
│   ├── basic_usage.py
│   ├── knowledge_graph.py
│   ├── filing_ingestion.py
│   └── ...
│
├── scripts/                       # 🔧 Utility scripts
│   ├── load_all_reference_data.py
│   ├── verify_reference_data.py
│   └── ...
│
├── docs/                          # 📖 Documentation
│   ├── architecture/
│   │   └── ARCHITECTURE_AND_TIERS.md
│   ├── GUARDRAILS.md
│   └── archive/
│
├── pyproject.toml                 # Package configuration
├── README.md                      # This file
├── CHANGELOG.md                   # Version history
├── CONTRIBUTING.md                # Contribution guidelines
├── LICENSE                        # MIT License
└── RELEASE_AUDIT_REPORT.md        # v0.3.3 release audit
```

---

## 🗂️ Storage Tiers

EntitySpine supports multiple storage backends with progressive capabilities:

| Tier | Backend | Dependencies | Use Case | Temporal Support |
|------|---------|--------------|----------|------------------|
| **0** | JSON file | None (stdlib) | Prototyping, CLI scripts | ❌ |
| **1** | SQLite | None (stdlib) | Local development, testing | ❌ |
| **2** | DuckDB | `duckdb` ([duckdb] extra) | Analytics, data science | ⏳ Planned |
| **3** | PostgreSQL | `psycopg3` ([postgres] extra) | Production apps | ✅ |
| **4** | Elasticsearch | `elasticsearch` ([search] extra) | Full-text search | ✅ |
| **5** | Neo4j | `neo4j` ([graph] extra) | Graph traversal | ✅ |

### Tier Honesty Principle

Lower tiers **warn** when they can't fulfill advanced features:

```python
result = store.resolve("AAPL", as_of="2020-01-01")

if not result.as_of_honored:
    for warning in result.warnings:
        print(f"⚠️ {warning}")
# ⚠️ Temporal resolution requires Tier 2+ (DuckDB/PostgreSQL)
```

---

## 📖 Domain Model Reference

### Core Models

| Model | Description | Key Fields |
|-------|-------------|------------|
| **Entity** | Legal/organizational identity | `primary_name`, `entity_type`, `jurisdiction`, `sic_code` |
| **Security** | Tradeable financial instrument | `security_type`, `entity_id`, `description` |
| **Listing** | Exchange-specific ticker | `ticker`, `exchange`, `mic`, `security_id` |
| **IdentifierClaim** | Identifier with provenance | `scheme`, `value`, `entity_id`, `confidence`, `source` |

### Knowledge Graph Nodes

| Model | Purpose | Example |
|-------|---------|---------|
| **Person** | Natural persons | Executives, directors, beneficial owners |
| **Asset** | Physical/tangible assets | Real estate, equipment, IP |
| **Contract** | Material agreements | Loans, leases, supply contracts |
| **Product** | Products/services | iPhone, Azure, AWS |
| **Brand** | Brand identities | Apple, Microsoft, Google |
| **Event** | Discrete business events | Earnings calls, M&A announcements |
| **Case** | Legal proceedings | Lawsuits, regulatory actions |
| **Geo** | Geographic locations | Countries, states, cities |
| **Address** | Physical addresses | Headquarters, branch offices |

### Market Infrastructure

| Model | Purpose |
|-------|---------|
| **Exchange** | Trading venues (NYSE, NASDAQ) |
| **BrokerDealer** | FINRA registered broker-dealers |
| **Clearinghouse** | Clearing and settlement (DTCC, OCC) |
| **MarketParticipant** | Market makers, specialists |
| **SelfRegulatoryOrg** | FINRA, CBOE, etc. |

### Relationship Models

| Model | Purpose |
|-------|---------|
| **RoleAssignment** | Person → Organization roles (CEO, CFO, Director) |
| **Relationship** | Generic node → node edges with evidence |
| **EntityRelationship** | Entity → Entity relationships (parent, subsidiary) |

---

## 🔌 Optional Dependencies

EntitySpine uses **optional dependency groups** to keep the core lightweight:

```toml
[project.optional-dependencies]
# Validation wrappers
pydantic = ["pydantic>=2.0", "pydantic-settings>=2.0"]

# ORM layer
orm = [
    "sqlalchemy>=2.0",
    "sqlmodel>=0.0.14",
    "psycopg[binary]>=3.1"
]

# Analytics tier
duckdb = ["duckdb>=0.10.0"]

# Production database
postgres = ["psycopg[binary]>=3.1", "psycopg[pool]>=3.1"]

# Search engine
search = ["elasticsearch>=8.0"]

# Graph database
graph = ["neo4j>=5.0"]

# REST API
api = [
    "fastapi>=0.100",
    "uvicorn[standard]>=0.23",
    "python-multipart>=0.0.6"
]

# CLI tools
cli = ["click>=8.1", "rich>=13.0", "tabulate>=0.9"]

# Development tools
dev = [
    "pytest>=7.4",
    "pytest-cov>=4.1",
    "pytest-asyncio>=0.21",
    "ruff>=0.1",
    "mypy>=1.5",
    "pre-commit>=3.5"
]

# Everything
all = [
    "entityspine[pydantic,orm,duckdb,postgres,search,graph,api,cli,dev]"
]
```

### Installation Examples

```bash
# Core only (zero dependencies)
pip install entityspine

# With Pydantic validation
pip install entityspine[pydantic]

# Production setup (PostgreSQL + API)
pip install entityspine[postgres,api]

# Full analytics stack
pip install entityspine[postgres,duckdb,search,graph]

# Development environment
pip install -e ".[dev]"
```

---

## 🧪 Testing

EntitySpine v0.3.3 has **548 passing tests** with **40% code coverage**.

```bash
# Run all tests
pytest

# With coverage report
pytest --cov=src/entityspine --cov-report=html
open htmlcov/index.html

# Run specific test categories
pytest tests/unit           # Unit tests only
pytest tests/integration    # Integration tests only
pytest tests/sources        # Source loader tests

# Run with verbose output
pytest -v

# Run tests matching pattern
pytest -k "test_entity"
```

### Test Organization

```
tests/
├── unit/                   # Fast unit tests (no I/O)
│   ├── domain/             # Domain model tests
│   ├── stores/             # Store tests (in-memory)
│   └── test_*.py
├── integration/            # Integration tests (real I/O)
│   ├── test_entity_storage_complete.py
│   ├── test_example_end_to_end.py
│   └── ...
├── sources/                # Data source tests
└── api/                    # API tests (requires [api] extra)
```

---

## 📚 Usage Examples

### Example 1: Load SEC Data

```python
"""Load SEC's company_tickers.json automatically."""
from entityspine import SqliteStore

store = SqliteStore("./sec_entities.db")
store.initialize()

# Auto-downloads from SEC (respects rate limits)
count = store.load_sec_data()
print(f"Loaded {count} entities")
# Loaded 14,247 entities

# Search works immediately
results = store.search_entities("Tesla", limit=5)
for entity, score in results:
    print(f"  {score:.2f} | {entity.primary_name}")
```

### Example 2: Build Knowledge Graph

```python
"""Model entities, people, and relationships."""
from entityspine import (
    Entity, EntityType, EntityStatus,
    IdentifierClaim, IdentifierScheme,
    SqliteStore
)
from entityspine.domain import Person, RoleAssignment, NodeRef
from datetime import date

store = SqliteStore(":memory:")
store.initialize()

# Create Microsoft entity
microsoft = Entity(
    primary_name="Microsoft Corporation",
    entity_type=EntityType.ORGANIZATION,
    status=EntityStatus.ACTIVE,
    jurisdiction="WA",
    source_system="sec",
    source_id="0000789019"
)
store.save_entity(microsoft)

# Add CIK identifier
cik_claim = IdentifierClaim(
    entity_id=microsoft.entity_id,
    scheme=IdentifierScheme.CIK,
    value="0000789019",
    namespace="sec",
    source="company_tickers.json",
    confidence=1.0
)
store.save_claim(cik_claim)

# Create CEO
satya = Person(
    full_name="Satya Nadella",
    first_name="Satya",
    last_name="Nadella"
)
store.save_person(satya)

# Assign role
role = RoleAssignment(
    person_ref=NodeRef("person", satya.person_id),
    org_ref=NodeRef("entity", microsoft.entity_id),
    role_title="Chief Executive Officer",
    start_date=date(2014, 2, 4)
)
store.save_role_assignment(role)

# Query
ceo_roles = store.get_roles_for_entity(microsoft.entity_id)
print(f"CEO: {ceo_roles[0].person_ref.ref_id}")
```

### Example 3: Track Corporate Actions

```python
"""Track mergers, acquisitions, and name changes."""
from entityspine import Entity, EntityStatus, SqliteStore
from entityspine.core.timestamps import utc_now

store = SqliteStore("./corporate_actions.db")
store.initialize()

# Original entity (Facebook)
fb = Entity(
    primary_name="Facebook, Inc.",
    entity_type=EntityType.ORGANIZATION,
    source_system="sec",
    source_id="0001326801"
)
store.save_entity(fb)

# After rebrand (Meta)
meta = Entity(
    primary_name="Meta Platforms, Inc.",
    entity_type=EntityType.ORGANIZATION,
    source_system="sec",
    source_id="0001326801"  # Same CIK
)
store.save_entity(meta)

# Mark old entity as merged
fb_merged = fb.with_update(
    status=EntityStatus.MERGED,
    redirect_to=meta.entity_id,
    redirect_reason="Rebranded to Meta Platforms, Inc.",
    merged_at=utc_now()
)
store.save_entity(fb_merged)

# Search for "Facebook" now returns Meta
results = store.search_entities("Facebook")
entity, score = results[0]
print(f"Facebook → {entity.primary_name}")
# Facebook → Meta Platforms, Inc.
```

### Example 4: Identifier Resolution

```python
"""Resolve entities across multiple identifier schemes."""
from entityspine import SqliteStore

store = SqliteStore("./entities.db")
store.initialize()
store.load_sec_data()

# Search works across CIK, ticker, name
test_queries = [
    "AAPL",           # Ticker
    "0000320193",     # CIK
    "Apple Inc",      # Exact name
    "Apple",          # Fuzzy name
    "037833100",      # CUSIP (if loaded)
]

for query in test_queries:
    results = store.search_entities(query, limit=1)
    if results:
        entity, score = results[0]
        print(f"'{query}' → {entity.primary_name} (score: {score:.2f})")
        
# Output:
# 'AAPL' → Apple Inc. (score: 1.00)
# '0000320193' → Apple Inc. (score: 1.00)
# 'Apple Inc' → Apple Inc. (score: 1.00)
# 'Apple' → Apple Inc. (score: 0.70)
```

---

## 🔧 Configuration

### Environment Variables

```bash
# Database path
ENTITYSPINE_DB_PATH=./data/entities.db

# Log level (DEBUG, INFO, WARNING, ERROR)
ENTITYSPINE_LOG_LEVEL=INFO

# SEC API rate limit (requests per second)
ENTITYSPINE_SEC_RATE_LIMIT=10

# Cache directory
ENTITYSPINE_CACHE_DIR=~/.cache/entityspine
```

### Programmatic Configuration

```python
from entityspine import SqliteStore
from entityspine.core.config import Config

# Custom configuration
config = Config(
    db_path="./custom.db",
    log_level="DEBUG",
    enable_wal=True
)

# Pass to store
store = SqliteStore(config.db_path, wal_mode=config.enable_wal)
```

---

## 🚀 Roadmap

### Current: v0.3.3 (January 2025)
- ✅ Zero-dependency core (JSON, SQLite)
- ✅ Entity, Security, Listing models
- ✅ IdentifierClaim system
- ✅ Knowledge Graph nodes (Person, Asset, Contract, etc.)
- ✅ SEC data loader
- ✅ ISO reference data (countries, currencies, MICs)
- ✅ 548 passing tests

### Planned: v0.4.0 (Q1 2025)
- [ ] DuckDB Tier 2 backend
- [ ] Temporal queries (as-of, time-travel)
- [ ] Enhanced fuzzy matching
- [ ] GLEIF LEI loader improvements
- [ ] Expanded test coverage (60%+ target)

### Planned: v0.5.0 (Q2 2025)
- [ ] PostgreSQL Tier 3 production backend
- [ ] Full temporal support
- [ ] Graph traversal queries
- [ ] REST API stabilization
- [ ] OpenAPI documentation

### Planned: v1.0.0 (Q3 2025)
- [ ] Production-ready stability
- [ ] Comprehensive documentation
- [ ] Performance benchmarks
- [ ] Migration guides
- [ ] Enterprise support options

---

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

### Development Setup

```bash
# Clone repository
git clone https://github.com/ryansmccoy/entityspine.git
cd entityspine

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Run tests
pytest

# Run linting
ruff check src tests
mypy src/entityspine
```

### Code Quality Standards

- **Test Coverage**: Aim for 60%+ (currently 40%)
- **Type Hints**: All public APIs must be typed
- **Docstrings**: Google-style docstrings for all public functions
- **Linting**: Pass `ruff check` and `mypy`
- **Tests**: All new features must have tests

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

## 🔗 Links

- **Repository**: https://github.com/ryansmccoy/entityspine
- **PyPI**: https://pypi.org/project/entityspine/
- **Issues**: https://github.com/ryansmccoy/entityspine/issues
- **Discussions**: https://github.com/ryansmccoy/entityspine/discussions
- **Changelog**: [CHANGELOG.md](CHANGELOG.md)

---

## 🙏 Acknowledgments

EntitySpine builds on the excellent work of:

- **SEC EDGAR**: For providing public company data
- **GLEIF**: For LEI data and reference implementations
- **ISO**: For standardized identifier schemes (ISO 3166, 4217, 10383)
- **py-sec-edgar community**: For inspiration and integration patterns

---

<p align="center">
  <sub>Built with ❤️ for the financial data community</sub>
  <br>
  <sub>v0.3.3 | Released January 2025</sub>
</p>
