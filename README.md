<p align="center">
  <img src="https://raw.githubusercontent.com/ryansmccoy/entity-spine/main/docs/assets/logo.svg" alt="EntitySpine" width="400">
</p>

<h1 align="center">EntitySpine</h1>

<p align="center">
  <strong>Zero-Dependency Entity Resolution for SEC EDGAR Data</strong>
</p>

<p align="center">
  <em>From <code>company_tickers.json</code> to enterprise-grade Knowledge Graph — without forcing dependencies.</em>
</p>

<p align="center">
  <a href="https://pypi.org/project/entityspine/">
    <img src="https://img.shields.io/pypi/v/entityspine?color=blue&label=PyPI" alt="PyPI">
  </a>
  <a href="https://pypi.org/project/entityspine/">
    <img src="https://img.shields.io/pypi/pyversions/entityspine" alt="Python Versions">
  </a>
  <a href="https://github.com/ryansmccoy/entity-spine/blob/main/LICENSE">
    <img src="https://img.shields.io/github/license/ryansmccoy/entity-spine" alt="License">
  </a>
  <a href="https://github.com/ryansmccoy/entity-spine/actions">
    <img src="https://img.shields.io/github/actions/workflow/status/ryansmccoy/entity-spine/ci.yml?branch=main" alt="CI">
  </a>
  <a href="https://codecov.io/gh/ryansmccoy/entity-spine">
    <img src="https://img.shields.io/codecov/c/github/ryansmccoy/entity-spine" alt="Coverage">
  </a>
</p>

<p align="center">
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-why-entityspine">Why EntitySpine?</a> •
  <a href="#-examples">Examples</a> •
  <a href="#-architecture">Architecture</a> •
  <a href="#-api-reference">API</a> •
  <a href="#-contributing">Contributing</a>
</p>

---

## 🎯 What is EntitySpine?

**EntitySpine** solves the **entity resolution problem** for SEC EDGAR data:

> *"Is CIK 0000320193 the same company as ticker AAPL on NASDAQ?"*

It provides:

- **🔍 Entity Resolution** — Resolve tickers, CIKs, CUSIPs to canonical entities
- **📊 Knowledge Graph** — Model companies, people, relationships, events
- **🗃️ Tiered Storage** — JSON → SQLite → DuckDB → PostgreSQL
- **⚡ Zero Core Dependencies** — stdlib-only for Tier 0-1

---

## ⚡ Quick Start

### Installation

```bash
# Core (zero dependencies)
pip install entityspine

# With optional features
pip install "entityspine[pydantic]"  # Validation wrappers
pip install "entityspine[orm]"       # SQLModel/SQLAlchemy
pip install "entityspine[duckdb]"    # Analytics tier
pip install "entityspine[full]"      # Everything
```

### 30-Second Example

```python
from entityspine import SqliteStore

# Create store and load ~14,000 SEC companies (auto-downloads)
store = SqliteStore(":memory:")
store.initialize()
store.load_sec_data()  # Fetches from SEC automatically

# Resolve by ticker
results = store.search_entities("AAPL")
entity, score = results[0]
print(f"{entity.primary_name} (CIK: {entity.source_id})")
# Apple Inc. (CIK: 0000320193)

# Resolve by CIK  
entities = store.get_entities_by_cik("0000320193")
print(entities[0].primary_name)
# Apple Inc.
```

---

## 🤔 Why EntitySpine?

### The Problem

SEC EDGAR data uses multiple identifiers that don't naturally connect:

| Identifier | Example | What It Identifies |
|------------|---------|-------------------|
| CIK | 0000320193 | Legal filing entity |
| Ticker | AAPL | Exchange listing |
| CUSIP | 037833100 | Security instrument |
| LEI | HWUPKR0MPOU8FGXBT394 | Global legal entity |

**Questions that are hard to answer:**
- Is `AAPL` and `0000320193` the same company? ✅ Yes
- Did `FB` become `META`? How do I track that? 🤔
- Which company is `GOOG` vs `GOOGL`? Same entity, different securities
- What's the LEI for CIK 0001018724? 🤷

### The Solution

EntitySpine provides a **canonical entity model** with **identifier claims**:

```
┌─────────────────────────────────────────────────────────────────┐
│                         Entity                                   │
│                    "Apple Inc."                                  │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │ CIK Claim   │  │ LEI Claim   │  │ EIN Claim   │             │
│  │ 0000320193  │  │ HWUPKR...   │  │ 94-2404110  │             │
│  │ source: SEC │  │ source:GLEIF│  │ source: IRS │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│                          │                                       │
│                          ▼                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                      Security                            │   │
│  │               "Apple Common Stock"                       │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐        │   │
│  │  │CUSIP Claim │  │ISIN Claim  │  │FIGI Claim  │        │   │
│  │  │ 037833100  │  │US037833...  │  │BBG000B9XRY4│        │   │
│  │  └────────────┘  └────────────┘  └────────────┘        │   │
│  │                          │                              │   │
│  │                          ▼                              │   │
│  │  ┌────────────────────────────────────────────────┐   │   │
│  │  │              Listing (NASDAQ)                   │   │   │
│  │  │  Ticker: AAPL | MIC: XNAS | Status: ACTIVE     │   │   │
│  │  └────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📚 Examples

### Example 1: Load SEC Company Tickers

```python
"""Load SEC's company_tickers.json into EntitySpine."""
from entityspine import SqliteStore
import httpx
import json

# Download SEC data
url = "https://www.sec.gov/files/company_tickers.json"
headers = {"User-Agent": "MyApp/1.0 (contact@example.com)"}
response = httpx.get(url, headers=headers)
sec_data = response.json()

# Load into EntitySpine
store = SqliteStore("./sec_entities.db")
store.initialize()
loaded = store.load_sec_json(sec_data)

print(f"Loaded {loaded} entities")
# Loaded 10,847 entities

# Query
results = store.search_entities("Microsoft")
for entity, score in results[:5]:
    print(f"  {score:.2f} | {entity.primary_name}")
# 1.00 | Microsoft Corporation
# 0.70 | Microsoft Payments Inc
```

### Example 2: Build Knowledge Graph from Filing

```python
"""Extract entities and relationships from a 10-K filing."""
from entityspine import (
    Entity, EntityType, EntityStatus,
    IdentifierClaim, IdentifierScheme, VendorNamespace, ClaimStatus,
    Relationship, NodeRef, NodeKind, RelationshipType,
    SqliteStore,
)

store = SqliteStore("./knowledge_graph.db")
store.initialize()

# Create NVIDIA entity
nvidia = Entity(
    primary_name="NVIDIA Corporation",
    entity_type=EntityType.ORGANIZATION,
    status=EntityStatus.ACTIVE,
    jurisdiction="DE",
    sic_code="3674",
    source_system="sec-edgar",
    source_id="0001045810",
)
store.save_entity(nvidia)

# Attach CIK with SEC filing evidence
cik_claim = IdentifierClaim(
    entity_id=nvidia.entity_id,
    scheme=IdentifierScheme.CIK,
    value="0001045810",
    namespace=VendorNamespace.SEC,
    source="sec-edgar",
    source_ref="0001045810-24-000029",  # Accession number
    confidence=1.0,
)
store.save_claim(cik_claim)

# Create supplier entity
tsmc = Entity(
    primary_name="Taiwan Semiconductor Manufacturing Company",
    entity_type=EntityType.ORGANIZATION,
    source_system="sec-edgar",
)
store.save_entity(tsmc)

# Create supplier relationship with evidence
relationship = Relationship(
    source_ref=NodeRef(NodeKind.ENTITY, nvidia.entity_id),
    target_ref=NodeRef(NodeKind.ENTITY, tsmc.entity_id),
    relationship_type=RelationshipType.SUPPLIER,
    confidence=0.95,
    evidence_filing_id="0001045810-24-000029",
    evidence_snippet="TSMC manufactures substantially all of our GPUs...",
    source_system="sec-edgar",
)
store.save_relationship(relationship)

print(f"Entities: {store.entity_count()}")
print(f"Relationships: {store.relationship_count()}")
```

### Example 3: py-sec-edgar Integration

```python
"""Ingest SEC filings using the integration module."""
from datetime import date
from entityspine.integration import (
    FilingFacts,
    FilingEvidence,
    ingest_filing_facts,
)
from entityspine.integration.contracts import (
    ExtractedEntity,
    ExtractedRelationship,
)
from entityspine import SqliteStore

store = SqliteStore("./filings.db")
store.initialize()

# Build facts from a 10-K (this would come from py-sec-edgar)
facts = FilingFacts(
    evidence=FilingEvidence(
        accession_number="0001045810-24-000029",
        form_type="10-K",
        filed_date=date(2024, 2, 21),
        cik="0001045810",
    ),
    registrant_name="NVIDIA Corporation",
    registrant_cik="0001045810",
    registrant_ticker="NVDA",
    registrant_exchange="NASDAQ",
    registrant_sic="3674",
    registrant_state="DE",
    entities=[
        ExtractedEntity(name="Jensen Huang", entity_type="person"),
        ExtractedEntity(name="TSMC", entity_type="organization"),
        ExtractedEntity(name="Microsoft", entity_type="organization"),
    ],
    relationships=[
        ExtractedRelationship(
            source_name="NVIDIA Corporation",
            target_name="TSMC",
            relationship_type="SUPPLIER",
            evidence_snippet="TSMC manufactures our GPUs",
        ),
        ExtractedRelationship(
            source_name="NVIDIA Corporation", 
            target_name="Microsoft",
            relationship_type="CUSTOMER",
            evidence_snippet="Microsoft is a major customer for datacenter",
        ),
    ],
)

# Ingest into knowledge graph
result = ingest_filing_facts(store, facts)

print(f"Created {result.entities_created} entities")
print(f"Created {result.relationships_created} relationships")
print(f"Created {result.claims_created} identifier claims")
# Created 4 entities
# Created 2 relationships  
# Created 2 identifier claims
```

### Example 4: Multi-Identifier Resolution

```python
"""Resolve entities across multiple identifier schemes."""
from entityspine import SqliteStore

store = SqliteStore("./entities.db")
store.initialize()

# Search works across CIK, ticker, and name
queries = ["AAPL", "0000320193", "Apple Inc", "Apple"]

for query in queries:
    results = store.search_entities(query, limit=1)
    if results:
        entity, score = results[0]
        print(f"'{query}' → {entity.primary_name} (score: {score:.2f})")
        
# 'AAPL' → Apple Inc. (score: 1.00)
# '0000320193' → Apple Inc. (score: 1.00)
# 'Apple Inc' → Apple Inc. (score: 1.00)
# 'Apple' → Apple Inc. (score: 0.70)
```

### Example 5: Track Corporate Actions

```python
"""Track mergers, name changes, and ticker changes."""
from entityspine import Entity, EntityStatus, SqliteStore
from entityspine.domain.timestamps import utc_now

store = SqliteStore("./corporate_actions.db")
store.initialize()

# Original entity
facebook = Entity(
    primary_name="Facebook, Inc.",
    entity_type=EntityType.ORGANIZATION,
    source_system="sec-edgar",
    source_id="0001326801",
)
store.save_entity(facebook)

# After rebranding - create redirect
meta = Entity(
    primary_name="Meta Platforms, Inc.",
    entity_type=EntityType.ORGANIZATION,
    source_system="sec-edgar",
    source_id="0001326801",  # Same CIK
)
store.save_entity(meta)

# Mark old entity as merged
facebook_merged = facebook.with_update(
    status=EntityStatus.MERGED,
    redirect_to=meta.entity_id,
    redirect_reason="Rebranded to Meta Platforms, Inc.",
    merged_at=utc_now(),
)
store.save_entity(facebook_merged)

# Lookups automatically follow redirect
results = store.search_entities("Facebook")
entity, _ = results[0]
print(f"Facebook resolved to: {entity.primary_name}")
# Facebook resolved to: Meta Platforms, Inc.
```

---

## 🏗️ Architecture

### Domain is Canonical

```
┌─────────────────────────────────────────────────────────────────┐
│                    entityspine.domain                           │
│                  (stdlib dataclasses only)                      │
│  ┌─────────┐ ┌──────────┐ ┌─────────┐ ┌─────────────────┐      │
│  │ Entity  │ │ Security │ │ Listing │ │IdentifierClaim  │      │
│  └─────────┘ └──────────┘ └─────────┘ └─────────────────┘      │
│  ┌─────────┐ ┌──────────┐ ┌─────────┐ ┌─────────────────┐      │
│  │  Asset  │ │ Contract │ │ Product │ │  Relationship   │      │
│  └─────────┘ └──────────┘ └─────────┘ └─────────────────┘      │
└─────────────────────────────────────────────────────────────────┘
                          ↑ returns domain dataclasses
┌─────────────────────────────────────────────────────────────────┐
│                      entityspine.stores                         │
│  ┌───────────────┐ ┌───────────────┐                           │
│  │  JsonStore    │ │  SqliteStore  │  (Tier 0-1, stdlib)       │
│  └───────────────┘ └───────────────┘                           │
└─────────────────────────────────────────────────────────────────┘
                          ↑ optional extras
┌─────────────────────────────────────────────────────────────────┐
│                    entityspine.adapters                         │
│  ┌─────────────────────┐ ┌─────────────────────┐               │
│  │ pydantic/ wrappers  │ │  orm/ SqlModelStore │               │
│  │ to_domain/from_dom  │ │  returns domain     │               │
│  └─────────────────────┘ └─────────────────────┘               │
│  pip install .[pydantic]  pip install .[orm]                    │
└─────────────────────────────────────────────────────────────────┘
```

### Storage Tiers

| Tier | Backend | Dependencies | Use Case | Temporal? |
|------|---------|--------------|----------|-----------|
| 0 | JSON file | None | Scripts, CLI | ❌ |
| 1 | SQLite | None | Local dev | ❌ |
| 2 | DuckDB | `[duckdb]` | Analytics | ⏳ Planned |
| 3 | PostgreSQL | `[postgres]` | Production | ✅ |

### Tier Honesty

Lower tiers **warn** when they can't fulfill advanced queries:

```python
result = store.resolve("AAPL", as_of="2015-01-01")
if not result.as_of_honored:
    for warning in result.warnings:
        print(f"⚠️ {warning}")
# ⚠️ as_of parameter ignored: temporal resolution requires Tier 2+
```

---

## 📖 Domain Models

### Core Models

| Model | Purpose | Key Fields |
|-------|---------|------------|
| `Entity` | Legal/organizational identity | `primary_name`, `entity_type`, `jurisdiction` |
| `Security` | Tradeable instrument | `security_type`, `entity_id`, `description` |
| `Listing` | Exchange-specific ticker | `ticker`, `exchange`, `mic`, `security_id` |
| `IdentifierClaim` | Identifier with provenance | `scheme`, `value`, `entity_id`, `confidence` |

### Knowledge Graph Nodes

| Model | Purpose |
|-------|---------|
| `Person` | Natural persons (executives, directors) |
| `Asset` | Physical/tangible assets |
| `Contract` | Material agreements |
| `Product` | Products/services |
| `Brand` | Brand identities |
| `Event` | Discrete business events |
| `Case` | Legal proceedings |
| `Geo` | Geographic locations |
| `Address` | Physical addresses |

### Edge Models

| Model | Purpose |
|-------|---------|
| `RoleAssignment` | Person→Org roles (CEO, CFO, Director) |
| `Relationship` | Generic node→node edges with evidence |
| `EntityRelationship` | Entity→Entity relationships |

---

## 🔧 Configuration

### Environment Variables

```bash
# Storage path (default: ./entityspine.db)
ENTITYSPINE_DB_PATH=./data/entities.db

# Log level
ENTITYSPINE_LOG_LEVEL=INFO
```

### Programmatic Configuration

```python
from entityspine import SqliteStore

# In-memory for testing
store = SqliteStore(":memory:")

# File-based
store = SqliteStore("./entities.db")

# With explicit WAL mode (better concurrency)
store = SqliteStore("./entities.db", wal_mode=True)
```

---

## 🧪 Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=entityspine --cov-report=html

# Only unit tests
pytest tests/unit -v

# Only integration tests  
pytest tests/integration -v
```

---

## 📁 Project Structure

```
entityspine/
├── src/entityspine/
│   ├── __init__.py              # Package exports
│   ├── domain/                  # Canonical stdlib dataclasses
│   │   ├── entity.py            # Entity model
│   │   ├── security.py          # Security model
│   │   ├── listing.py           # Listing model
│   │   ├── claim.py             # IdentifierClaim model
│   │   ├── graph.py             # KG nodes (Asset, Contract, etc.)
│   │   ├── enums.py             # All enumerations
│   │   └── validators.py        # Normalization + validation
│   ├── stores/                  # Storage backends
│   │   ├── sqlite_store.py      # Tier 1 (stdlib sqlite3)
│   │   ├── json_store.py        # Tier 0 (JSON file)
│   │   └── mappers.py           # Domain ↔ dict conversion
│   ├── adapters/                # Optional adapters
│   │   ├── pydantic/            # Pydantic validation wrappers
│   │   └── orm/                 # SQLModel/SQLAlchemy layer
│   ├── integration/             # py-sec-edgar integration
│   │   ├── contracts.py         # FilingFacts schema
│   │   ├── ingest.py            # Ingestion functions
│   │   └── normalize.py         # SEC identifier normalizers
│   └── core/                    # Utilities
│       ├── ulid.py              # ULID generation
│       └── timestamps.py        # UTC timestamp utilities
├── tests/                       # 303 tests
├── examples/                    # Usage examples
└── docs/                        # Documentation
```

---

## 🚀 Roadmap

- [x] **v0.3.x** — Core entity resolution, KG nodes, integration module
- [ ] **v0.4.x** — DuckDB Tier 2, temporal queries
- [ ] **v0.5.x** — PostgreSQL Tier 3, full temporal support
- [ ] **v0.6.x** — FastAPI service, graph traversal API
- [ ] **v1.0.0** — Production-ready, comprehensive documentation

---

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

```bash
# Setup development environment
git clone https://github.com/ryansmccoy/entity-spine.git
cd entity-spine
pip install -e ".[dev]"
pre-commit install

# Run tests
pytest

# Run linting
ruff check src tests
mypy src/entityspine
```

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 🔗 Links

- **Repository**: https://github.com/ryansmccoy/entity-spine
- **PyPI**: https://pypi.org/project/entityspine/
- **Documentation**: https://github.com/ryansmccoy/entity-spine/tree/main/docs
- **Issues**: https://github.com/ryansmccoy/entity-spine/issues

---

<p align="center">
  <sub>Built with ❤️ for the SEC EDGAR community</sub>
</p>
