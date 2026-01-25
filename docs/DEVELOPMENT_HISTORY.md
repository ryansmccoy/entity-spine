# EntitySpine Development History

This document provides a chronological summary of commits, features, and files affected during the v2.3.0 development session.

---

## Table of Contents

1. [Session Overview](#session-overview)
2. [Conversations & Key Decisions](#conversations--key-decisions)
3. [Commit Timeline](#commit-timeline)
4. [Feature Summary by Area](#feature-summary-by-area)
5. [Files Changed by Category](#files-changed-by-category)
6. [Documentation Index](#documentation-index)
7. [Quick Reference](#quick-reference)
8. [Example Code Patterns](#example-code-patterns)

---

## Session Overview

| Metric | Value |
|--------|-------|
| **Date** | January 28, 2026 |
| **Commits** | 15 commits |
| **New Files** | ~100+ files (excluding node_modules) |
| **Lines Changed** | ~15,000+ lines (src + docs + examples) |
| **Primary Focus** | Financial observation model, multi-vendor ingestion, enterprise storage |

### Major Deliverables

1. **Modular Enum System** - Split 857-line enums.py into 10 focused modules
2. **Financial Observation Model v2.2.5** - 8 dataclasses for financial metrics with provenance
3. **Calendar Event Support** - 40+ event types aligned with SEC filings
4. **Tier 4/5 Storage** - Elasticsearch + Neo4j stores with sync service
5. **CLI** - Comprehensive command-line interface
6. **React Visualization Apps** - 3D graph visualization dashboards
7. **SEC Data Integration** - Entity loading from public SEC data
8. **Documentation Overhaul** - ADRs, features docs, and reorganization

---

## Conversations & Key Decisions

This section captures the discussions and reasoning behind major design decisions during the session.

### "Why Not Pydantic in the Domain Layer?"

**The Problem:** Initial implementation used Pydantic for validation, but this created coupling:

```python
# ❌ Initial approach - creates external dependency
from pydantic import BaseModel

class Entity(BaseModel):
    entity_id: str
    primary_name: str
```

**The Discussion:**
> User: "The domain layer should be stdlib-only. Pydantic belongs in the API layer."
> 
> Response: Refactored to frozen dataclasses with manual validation. This keeps the domain pure and serializable.

**The Solution:**
```python
# ✅ EntitySpine convention - stdlib only
from dataclasses import dataclass
from entityspine.domain.identifiers import generate_ulid

@dataclass(frozen=True, slots=True)
class Entity:
    entity_id: str
    primary_name: str
    
    @classmethod
    def create(cls, primary_name: str) -> "Entity":
        return cls(entity_id=generate_ulid(), primary_name=primary_name)
```

---

### "How Do We Handle Multi-Vendor Data Conflicts?"

**The Problem:** Same entity exists in multiple sources with different data:
- Vendor A says Apple HQ is "One Apple Park Way"
- Vendor B says "1 Apple Park Way" 
- SEC filing says "Apple Park, Cupertino"

**The Discussion:**
> User: "FactSet should be authoritative for entity names, Bloomberg for pricing, SEC for legal filings."
>
> Response: Implemented source priority system with claim-based identifier linking.

**The Solution:**
```python
# Source priority (lower = higher priority)
SOURCE_PRIORITY = {
    "bloomberg": 1,   # Highest priority for financial data
    "factset": 2,     # Primary for entity metadata
    "thomson": 3,     # Permid crosswalk
    "sec": 4,         # Legal filings
    "user": 5,        # User-contributed
}

# Claims preserve all sources while resolution picks winner
class IdentifierClaim:
    scheme: IdentifierScheme   # e.g., CUSIP, ISIN, LEI
    value: str                 # The identifier value
    source_system: str         # Who provided this claim
    confidence: float          # 0.0 to 1.0
```

---

### "The 857-Line enums.py Was Unmanageable"

**The Problem:** All 42 enums in one file made navigation painful:

```python
# enums.py had:
# - EntityType, EntityStatus (core)
# - IdentifierScheme, ClaimStatus (identifiers)  
# - EventType (40+ values!), EventStatus (events)
# - MetricCode, PeriodType (observations)
# - ... 30+ more enums
```

**The Discussion:**
> User: "Split enums by domain concept but maintain backward compatibility."
>
> Response: Created `enums/` package with `__init__.py` re-exporting everything.

**The Solution:**
```
enums/
├── __init__.py      # from .core import *; from .events import *; ...
├── core.py          # EntityType, SecurityType
├── events.py        # EventType (40+ values)
├── observations.py  # MetricCode, PeriodType
└── ... 7 more modules
```

Usage unchanged:
```python
# Still works! __init__.py re-exports all
from entityspine.domain.enums import EntityType, EventType, MetricCode
```

---

### "What About Financial Observation Provenance?"

**The Problem:** Financial data needs full lineage - who said what, when, from which document?

**The Discussion:**
> User: "I need to trace every number back to its source document, table, and row."
>
> Response: Designed Observation model with nested provenance and dedup keys.

**Example Use Case:**
```python
from entityspine.domain.observation import (
    Observation, MetricSpec, FiscalPeriod, 
    ProvenanceRef, SourceKey, ValueWithUnits
)
from entityspine.domain.enums import MetricCode, PeriodType, ProvenanceKind
from decimal import Decimal

# Recording EPS from a 10-K filing
obs = Observation.create(
    entity_id="01HQ9XYZABC123",
    metric=MetricSpec(code=MetricCode.EPS_BASIC),
    period=FiscalPeriod(fiscal_year=2024, period_type=PeriodType.ANNUAL),
    value=ValueWithUnits(raw_value=Decimal("6.42"), currency="USD"),
    provenance=ProvenanceRef(
        kind=ProvenanceKind.FILING,
        namespace=VendorNamespace.SEC,
        document_id="0000320193-24-000081"  # Apple's 10-K
    ),
    source_key=SourceKey(
        dataset="sec_filings",
        table="xbrl_facts", 
        column="us-gaap:EarningsPerShareBasic"
    )
)

# Built-in dedup key prevents duplicates
print(obs.dedup_key)  
# "01HQ9XYZABC123|EPS_BASIC|2024|ANNUAL|FILING|SEC|0000320193-24-000081"
```

---

### "How Do Calendar Events Differ From Historical Events?"

**The Problem:** Event calendars have future events (earnings calls, dividends) while historical events have outcomes.

**The Discussion:**
> User: "I need to track scheduled earnings dates AND completed M&A with amounts."
>
> Response: Enhanced Event model with scheduling fields and computed properties.

**Example - Upcoming Earnings:**
```python
from entityspine.domain.graph import Event
from entityspine.domain.enums import EventType
from datetime import date

event = Event(
    event_type=EventType.EARNINGS_RELEASE,
    title="Apple Q1 2025 Earnings",
    entity_id="01HQ9APPLE",
    scheduled_on=date(2025, 1, 30),
    fiscal_year=2025,
    fiscal_quarter=1,
    report_time="AMC"  # After Market Close
)

print(event.is_calendar_event)  # True
print(event.is_financial_event)  # False (no amount yet)
print(event.fiscal_period_str)   # "Q1 2025"
```

**Example - Completed Dividend:**
```python
event = Event(
    event_type=EventType.DIVIDEND_CASH,
    title="Microsoft Quarterly Dividend",
    entity_id="01HQ9MSFT",
    effective_date=date(2024, 12, 12),  # Ex-date
    amount=Decimal("0.83"),
    currency="USD"
)

print(event.is_financial_event)  # True (has amount)
```

---

### "Why Elasticsearch + Neo4j? Isn't PostgreSQL Enough?"

**The Problem:** Different queries need different database strengths:
- "Find companies matching 'Microsft'" → Fuzzy text search
- "What's 3 hops from AAPL?" → Graph traversal
- "All Apple financials for 2024" → Relational queries

**The Discussion:**
> User: "At enterprise scale, I need specialized databases for each workload."
>
> Response: Implemented tiered architecture with sync service.

**The Architecture:**
```
PostgreSQL (Source of Truth)
    │
    ├──► Elasticsearch (Text Search)
    │    - Fuzzy matching: "Microsft" → "Microsoft"
    │    - Autocomplete with edge-ngrams
    │    - BM25 relevance scoring
    │
    └──► Neo4j (Graph Traversal)
         - O(1) per-hop traversal
         - "Find all subsidiaries of Berkshire"
         - "Shortest path from AAPL to GOOGL"
```

**Usage Example:**
```python
from entityspine.stores.elasticsearch_store import ElasticsearchStore
from entityspine.stores.neo4j_store import Neo4jStore

# Fuzzy name search
es_store = ElasticsearchStore(hosts=["localhost:9200"])
results = es_store.search_entities("Microsft")  # Finds Microsoft

# Graph traversal
neo_store = Neo4jStore(uri="bolt://localhost:7687")
network = neo_store.get_entity_network("01HQ9AAPL", max_depth=3)
```

---

## Commit Timeline

### Commit 1: `8114acd` - Enum Package Refactoring
**Date:** Wed Jan 28 22:48:50 2026  
**Type:** `refactor(domain)`  
**Title:** Split enums.py into modular package

**Why:** The monolithic `enums.py` (857 lines, 42 enums) was difficult to navigate and had poor separation of concerns.

**What Changed:**
```
src/entityspine/domain/enums.py         → DELETED
src/entityspine/domain/enums/
├── __init__.py      # Re-exports all enums for backward compatibility
├── core.py          # EntityType, EntityStatus, SecurityType, ListingStatus
├── identifiers.py   # IdentifierScheme, ClaimStatus, SanctionStatus
├── resolution.py    # ResolutionTier, ResolutionStatus, MatchReason
├── graph.py         # NodeKind, RelationshipType, RoleType, ClusterRole
├── events.py        # EventType (40+ types), EventStatus, CaseType
├── assets.py        # AssetType, ContractType, ProductType
├── observations.py  # MetricCode, PeriodType, AccountingBasis
├── vendors.py       # VendorNamespace, ProvenanceKind
├── geo.py           # GeoType, AddressType
└── transactions.py  # TransactionCode
```

**Impact:** Backward compatible - all imports still work via `from entityspine.domain.enums import ...`

---

### Commit 2: `eac71d7` - Financial Observation Model
**Date:** Wed Jan 28 22:49:01 2026  
**Type:** `feat(domain)`  
**Title:** Add Financial Observation Model v2.2.5

**Why:** Financial data requires complex provenance tracking, temporal versioning, and multi-vendor conflict resolution.

**What Changed:**
```
src/entityspine/domain/observation.py   # NEW - 823 lines
tests/unit/domain/test_observation.py   # NEW - 35 tests
```

**New Classes (8 dataclasses):**
| Class | Purpose |
|-------|---------|
| `MetricSpec` | What metric (code, category, basis, per_share, scope) |
| `FiscalPeriod` | What timeframe (fiscal_year, quarter, period_type) |
| `ProvenanceRef` | Source document (kind, namespace, doc_id, snapshot) |
| `SourceKey` | Field lineage (dataset, table, column, row_key) |
| `EstimateInfo` | Analyst estimates (scope, estimator, num_analysts) |
| `ValueWithUnits` | Values with normalization (raw_value, currency, scale) |
| `Observation` | Complete observation record with dedup key |
| `ObservationSet` | Collection with metadata |

---

### Commit 3: `58da798` - Calendar Event Enhancement
**Date:** Wed Jan 28 22:49:18 2026  
**Type:** `feat(domain)`  
**Title:** Enhance Event model with calendar event support

**Why:** Calendar event support required scheduling, fiscal period, and monetary value support for earnings, dividends, and corporate actions.

**What Changed:**
```
src/entityspine/domain/graph.py         # MODIFIED - Event model enhanced
src/entityspine/domain/__init__.py      # MODIFIED - exports
```

**New Event Fields:**
| Field | Type | Purpose |
|-------|------|---------|
| `scheduled_on` | `date \| None` | Future event date |
| `effective_date` | `date \| None` | Ex-date for dividends |
| `fiscal_year` | `int \| None` | FY reference |
| `fiscal_quarter` | `int \| None` | Q1-Q4 reference |
| `report_time` | `str \| None` | 'BMO', 'AMC', 'DURING' |
| `currency` | `str \| None` | For monetary events |
| `amount` | `Decimal \| None` | Dividend, deal value |
| `entity_id` | `str \| None` | Primary entity |
| `related_entity_ids` | `list[str]` | M&A counterparties |

**New Computed Properties:**
- `is_calendar_event` → True if earnings, dividends, meetings
- `is_financial_event` → True if monetary value
- `is_compliance_event` → True if sanctions/regulatory
- `fiscal_period_str` → "Q4 2024" format

---

### Commit 4: `d05e8d0` - Tier 4/5 Enterprise Storage
**Date:** Wed Jan 28 22:49:28 2026  
**Type:** `feat(stores)`  
**Title:** Add Tier 4/5 Elasticsearch and Neo4j stores

**Why:** Enterprise scale requires specialized databases: ES for text search, Neo4j for graph traversal.

**What Changed:**
```
src/entityspine/stores/elasticsearch_store.py  # NEW - 582 lines
src/entityspine/stores/neo4j_store.py          # NEW - 744 lines
src/entityspine/services/sync_service.py       # NEW - 492 lines
ARCHITECTURE_AND_TIERS.md                      # NEW - tier documentation
```

**Tier Architecture:**
```
Tier 0/1: JSON/SQLite (development)
    ↓
Tier 2: DuckDB (analytics)
    ↓
Tier 3: PostgreSQL (production OLTP)
    ↓
Tier 4/5: PostgreSQL + Elasticsearch + Neo4j (enterprise)
```

**Elasticsearch Features:**
- Fuzzy matching ("Microsft" → "Microsoft")
- Autocomplete with edge-ngrams
- BM25 relevance scoring
- Multi-field search

**Neo4j Features:**
- O(1) per-hop traversal
- Dijkstra shortest path
- Cypher pattern matching
- Graph algorithms (PageRank, centrality)

---

### Commit 5: `2b07f46` - Command Line Interface
**Date:** Wed Jan 28 22:49:35 2026  
**Type:** `feat(cli)`  
**Title:** Add comprehensive EntitySpine CLI

**Why:** Users need command-line access for scripting, debugging, and quick entity lookups.

**What Changed:**
```
src/entityspine/cli.py    # NEW - 644 lines
```

**Commands:**
```bash
entityspine resolve AAPL           # Resolve by identifier
entityspine search 'Apple'         # Fuzzy name search
entityspine graph network AAPL     # Visualize entity network
entityspine filings list 0000320193  # SEC filings
entityspine db init                # Initialize database
entityspine serve --port 8000      # Run REST API
```

**Dependencies:** `pip install entityspine[cli]` (typer + rich)

---

### Commit 6: `f7ac7bf` - Entity & Claim Model Enhancements
**Date:** Wed Jan 28 22:49:42 2026  
**Type:** `feat(domain)`  
**Title:** Enhance Entity and Claim models

**What Changed:**
```
src/entityspine/domain/entity.py       # MODIFIED
src/entityspine/domain/claim.py        # MODIFIED
src/entityspine/domain/validators.py   # MODIFIED
src/entityspine/stores/json_store.py   # MODIFIED
src/entityspine/stores/__init__.py     # MODIFIED
```

**Entity Improvements:**
- `source_priority` field for multi-vendor resolution
- `aliases` tuple for alternate names
- Enhanced jurisdiction validation (ISO-3166)

**Claim Improvements:**
- `SanctionStatus` enum support
- Improved scheme-scope validation
- Better confidence scoring

---

### Commit 7: `6f63f6d` - Tier Examples
**Date:** Wed Jan 28 22:49:49 2026  
**Type:** `feat(examples)`  
**Title:** Add tier and ingestion examples

**What Changed:**
```
examples/
├── README.md                         # Example index
├── __init__.py
├── tier0_json_memory.py              # Zero-dependency in-memory
├── tier1_sqlite.py                   # SQLite local development
├── tier_comparison.py                # Performance comparison
├── load_factset.py                   # FactSet 600K+ entities
├── ingestion_patterns.py             # Multi-vendor ingestion
├── sec_data_pipeline.py              # SEC workflow
└── performance_and_global_tickers.py # Global exchange coverage
```

---

### Commit 8: `55c29db` - Code Conventions & Architecture Proposals
**Date:** Wed Jan 28 22:49:58 2026  
**Type:** `docs`  
**Title:** Add code conventions and architecture improvement proposals

**What Changed:**
```
docs/ENTITYSPINE_CONVENTIONS.md       # NEW - 684 lines
docs/ARCHITECTURE_IMPROVEMENTS.md     # NEW - 469 lines
docs/ENHANCEMENTS.md                  # NEW
docs/SESSION_SUMMARY_2026_01_28.md    # NEW
```

**Key Conventions:**
- STDLIB ONLY - NO PYDANTIC in domain layer
- `@dataclass(frozen=True, slots=True)` for all models
- `(str, Enum)` pattern for JSON serialization
- `generate_ulid()` for ID generation
- `utc_now()` for timestamps

---

### Commit 9: `8f84c66` - Ingestion Architecture Documentation
**Date:** Wed Jan 28 22:50:08 2026  
**Type:** `docs`  
**Title:** Add multi-vendor ingestion architecture

**What Changed:**
```
docs/INGESTION_ARCHITECTURE.md        # NEW
docs/INGESTION_LLM_PROMPT.md          # NEW
docs/INGESTION_TEST_SCENARIOS.md      # NEW
docs/FINANCIAL_OBSERVATION_MODEL.md   # NEW
docs/FINANCIAL_DATA_EXTENSION.md      # NEW
```

**Source Priority System:**
```
Vendor_A (1) > Vendor_B (2) > Vendor_C (3) > SEC (4) > User (5)
```

---

### Commit 10: `b1ee064` - Data Integration Guide
**Date:** Wed Jan 28 22:50:19 2026
**Type:** `docs`
**Title:** Add data integration guide and API docs

**What Changed:**
```
docs/FACTSET_INTEGRATION.md           # NEW
docs/api/domain/entity.md             # NEW
docs/api/domain/claim.md              # NEW
docs/api/domain/enums.md              # NEW
docs/api/domain/event.md              # NEW
docs/api/domain/index.md              # NEW
docs/index.md                         # NEW
docs/integration/factset.md           # NEW
```

---

### Commit 11: `6a315c8` - Build Configuration
**Date:** Wed Jan 28 22:50:24 2026  
**Type:** `build`  
**Title:** Add mkdocs configuration and update dependencies

**What Changed:**
```
mkdocs.yml                            # NEW
pyproject.toml                        # MODIFIED
```

**New Dependency Groups:**
```toml
[project.optional-dependencies]
cli = ["typer", "rich"]
search = ["elasticsearch"]
graph = ["neo4j"]
docs = ["mkdocs", "mkdocs-material", "mkdocstrings"]
```

---

### Commit 12: `859366b` - FastAPI Enhancement
**Date:** Wed Jan 28 22:50:30 2026  
**Type:** `feat(api)`  
**Title:** Enhance FastAPI endpoints

**What Changed:**
```
src/entityspine/api/app.py            # MODIFIED
src/entityspine/api/schemas.py        # MODIFIED
```

**New Endpoints:**
| Method | Path | Description |
|--------|------|-------------|
| GET | `/resolve/{identifier}` | Resolve entity by any ID |
| GET | `/entities/{entity_id}` | Get entity with claims |
| GET | `/search` | Fuzzy name search |
| GET | `/graph/network/{entity_id}` | Entity network |
| POST | `/entities` | Create entity |
| POST | `/claims` | Add identifier claim |

---

### Commit 13: `c9c921f` - React Visualization Apps
**Date:** Wed Jan 28 22:57:59 2026  
**Type:** `feat(examples)`  
**Title:** Add React knowledge graph visualization apps

**What Changed:**
```
examples/entity-graph-app/            # NEW - 3D force graph
├── src/App.tsx
├── src/EntityGraph.tsx
├── package.json
└── ...

examples/entity-relationships-dashboard/  # NEW - Relationship dashboard
├── src/App.tsx
├── src/api.ts
├── src/data.ts
├── src/hooks.ts
└── ...

prompts/                              # NEW - LLM prompt templates
├── PROMPT_ADDRESS_EXTRACTION.md
├── PROMPT_ENUM_REFACTORING.md
├── PROMPT_GRAPH_REFACTORING.md
├── PROMPT_OBSERVATION_CONSOLIDATION.md
├── PROMPT_OBSERVATION_EXTENSIONS.md
├── PROMPT_TYPE_ALIASES.md
└── docstring_enhancement.md
```

---

### Commit 14: `214564d` - Feature Summary
**Date:** Wed Jan 28 22:59:09 2026  
**Type:** `docs`  
**Title:** Add consolidated feature summary for v2.3.0

**What Changed:**
```
docs/FEATURE_SUMMARY.md               # NEW - 455 lines
```

---

### Commit 15: `e8dabdb` - Documentation Reorganization
**Date:** Wed Jan 28 23:09:14 2026  
**Type:** `docs`  
**Title:** Reorganize documentation and backfill ADRs

**What Changed:**
```
docs/
├── adrs/                             # NEW - Architecture Decision Records
│   ├── 001-stdlib-only-domain.md
│   ├── 002-ulid-over-uuid.md
│   ├── 003-identifier-claims.md
│   ├── 004-frozen-dataclasses.md
│   ├── 005-enum-str-inheritance.md
│   ├── 006-time-semantics.md
│   └── 007-enum-package-split.md
├── architecture/                     # Moved core docs
│   ├── CONVENTIONS.md
│   ├── MANIFESTO.md
│   └── MODEL_ARCHITECTURE.md
├── features/                         # Feature documentation
│   ├── factset-integration.md
│   ├── ingestion.md
│   └── observation-model.md
├── rfcs/                             # Proposals
│   ├── 001-architecture-improvements.md
│   └── ROADMAP.md
├── changelog/                        # Version history
│   ├── CHANGELOG.md
│   └── v2.3.0-summary.md
└── sessions/                         # Session summaries
    └── 2026-01-28.md
```

---

## Feature Summary by Area

### 1. Domain Layer (`src/entityspine/domain/`)

| File | Purpose | Lines | Status |
|------|---------|-------|--------|
| `enums/` | Modular enum package (10 files) | ~900 | NEW |
| `observation.py` | Financial Observation Model | 823 | NEW |
| `graph.py` | Event model with calendar support | 1829 | ENHANCED |
| `entity.py` | Entity with source_priority | ~400 | ENHANCED |
| `claim.py` | IdentifierClaim with sanctions | ~300 | ENHANCED |
| `validators.py` | Jurisdiction, MIC, SIC validation | ~200 | ENHANCED |

### 2. Storage Layer (`src/entityspine/stores/`)

| File | Purpose | Lines | Status |
|------|---------|-------|--------|
| `elasticsearch_store.py` | Full-text search | 582 | NEW |
| `neo4j_store.py` | Graph traversal | 744 | NEW |
| `json_store.py` | JSON/memory store | ~400 | ENHANCED |

### 3. Services Layer (`src/entityspine/services/`)

| File | Purpose | Lines | Status |
|------|---------|-------|--------|
| `sync_service.py` | PostgreSQL → ES/Neo4j sync | 492 | NEW |

### 4. API Layer (`src/entityspine/api/`)

| File | Purpose | Lines | Status |
|------|---------|-------|--------|
| `app.py` | FastAPI application | ~500 | ENHANCED |
| `schemas.py` | Pydantic request/response | ~300 | ENHANCED |

### 5. CLI (`src/entityspine/cli.py`)

| Feature | Command |
|---------|---------|
| Resolve entity | `entityspine resolve AAPL` |
| Search entities | `entityspine search 'Apple'` |
| Graph network | `entityspine graph network AAPL` |
| SEC filings | `entityspine filings list CIK` |
| Init database | `entityspine db init` |
| Run server | `entityspine serve` |

---

## Files Changed by Category

### Source Code (57 files)

**Domain Layer (16 files):**
```
src/entityspine/domain/
├── __init__.py
├── enums/
│   ├── __init__.py
│   ├── assets.py
│   ├── core.py
│   ├── events.py
│   ├── geo.py
│   ├── graph.py
│   ├── identifiers.py
│   ├── observations.py
│   ├── resolution.py
│   ├── transactions.py
│   └── vendors.py
├── observation.py          # NEW
├── graph.py                # ENHANCED
├── entity.py               # ENHANCED
├── claim.py                # ENHANCED
└── validators.py           # ENHANCED
```

**Storage Layer (4 files):**
```
src/entityspine/stores/
├── __init__.py
├── elasticsearch_store.py  # NEW
├── neo4j_store.py          # NEW
└── json_store.py           # ENHANCED
```

**Services Layer (1 file):**
```
src/entityspine/services/
└── sync_service.py         # NEW
```

**API Layer (2 files):**
```
src/entityspine/api/
├── app.py                  # ENHANCED
└── schemas.py              # ENHANCED
```

**CLI (1 file):**
```
src/entityspine/cli.py      # NEW
```

### Examples (19 files)

```
examples/
├── README.md
├── __init__.py
├── tier0_json_memory.py
├── tier1_sqlite.py
├── tier_comparison.py
├── load_factset.py
├── ingestion_patterns.py
├── sec_data_pipeline.py
├── performance_and_global_tickers.py
├── entity-graph-app/       # React 3D graph (12 files)
└── entity-relationships-dashboard/  # React dashboard (11 files)
```

### Tests (1 file)

```
tests/unit/domain/test_observation.py  # 35 tests
```

### Documentation (60+ files)

See [Documentation Index](#documentation-index) below.

---

## Documentation Index

The `docs/` folder is now organized into logical categories:

### `/docs/adrs/` - Architecture Decision Records

Historical decisions with context and rationale:

| ADR | Title | Summary |
|-----|-------|---------|
| [001](adrs/001-stdlib-only-domain.md) | stdlib-only domain | No pydantic in domain layer |
| [002](adrs/002-ulid-over-uuid.md) | ULID over UUID | Time-sortable IDs |
| [003](adrs/003-identifier-claims.md) | Identifier Claims | Claim pattern for multi-source IDs |
| [004](adrs/004-frozen-dataclasses.md) | Frozen Dataclasses | Immutability by default |
| [005](adrs/005-enum-str-inheritance.md) | Enum str Inheritance | JSON serialization pattern |
| [006](adrs/006-time-semantics.md) | Time Semantics | observed_at vs effective_at |
| [007](adrs/007-enum-package-split.md) | Enum Package Split | Why we split enums.py |

### `/docs/architecture/` - Core Design Documents

| File | Purpose |
|------|---------|
| [CONVENTIONS.md](architecture/CONVENTIONS.md) | Coding standards and patterns |
| [MANIFESTO.md](architecture/MANIFESTO.md) | Design philosophy |
| [MODEL_ARCHITECTURE.md](architecture/MODEL_ARCHITECTURE.md) | Data model design |
| [UNIFIED_DATA_MODEL.md](architecture/UNIFIED_DATA_MODEL.md) | Complete schema reference |

### `/docs/features/` - Feature Documentation

| File | Feature |
|------|---------|
| [factset-integration.md](features/factset-integration.md) | FactSet data loading |
| [ingestion.md](features/ingestion.md) | Multi-vendor ingestion |
| [observation-model.md](features/observation-model.md) | Financial Observation Model |
| [financial-data-extension.md](features/financial-data-extension.md) | FinancialSpine design |
| [social-feed.md](features/social-feed.md) | Social feed integration |

### `/docs/rfcs/` - Proposals & Roadmap

| File | Topic |
|------|-------|
| [001-architecture-improvements.md](rfcs/001-architecture-improvements.md) | Split proposals |
| [ROADMAP.md](rfcs/ROADMAP.md) | Future development |
| [enhancements.md](rfcs/enhancements.md) | v2.3.0 enhancements |
| [API_PROPOSAL_*.md](rfcs/) | API design proposals |

### `/docs/integration/` - External Integration

| File | Integration |
|------|-------------|
| [factset.md](integration/factset.md) | FactSet quick start |
| [llm-prompt.md](integration/llm-prompt.md) | LLM schema mapping |
| [test-scenarios.md](integration/test-scenarios.md) | Ingestion test cases |
| [filing-facts-schema.md](integration/filing-facts-schema.md) | SEC filing schema |

### `/docs/api/` - API Reference

| File | Scope |
|------|-------|
| [domain/entity.md](api/domain/entity.md) | Entity model |
| [domain/claim.md](api/domain/claim.md) | IdentifierClaim |
| [domain/enums.md](api/domain/enums.md) | All enums |
| [domain/event.md](api/domain/event.md) | Event model |
| [services-reference.md](api/services-reference.md) | Service APIs |

### `/docs/changelog/` - Version History

| File | Purpose |
|------|---------|
| [CHANGELOG.md](changelog/CHANGELOG.md) | Full changelog |
| [v2.3.0-summary.md](changelog/v2.3.0-summary.md) | This release |
| [migration-v0.3.0.md](changelog/migration-v0.3.0.md) | Migration guide |

### `/docs/sessions/` - Development Sessions

| File | Date |
|------|------|
| [2026-01-28.md](sessions/2026-01-28.md) | This session |

### `/docs/design/` - Historical Design Docs

Archived design documents from previous versions (v1, v2.0, v2.1).

---

## Quick Reference

### Import Patterns

```python
# Enums (backward compatible)
from entityspine.domain.enums import EntityType, EventType, MetricCode

# Observation Model
from entityspine.domain.observation import (
    Observation, MetricSpec, FiscalPeriod, ValueWithUnits
)

# Event Model
from entityspine.domain.graph import Event

# Stores
from entityspine.stores import JsonEntityStore
from entityspine.stores.elasticsearch_store import ElasticsearchStore
from entityspine.stores.neo4j_store import Neo4jStore
```

### CLI Quick Start

```bash
# Install with CLI support
pip install entityspine[cli]

# Resolve entity
entityspine resolve AAPL

# Search by name
entityspine search "Microsoft" --limit 10

# Initialize database
entityspine db init --tier 1
```

### Run Examples

```bash
cd examples

# Tier examples
python tier0_json_memory.py
python tier1_sqlite.py

# FactSet loading
python load_factset.py /path/to/factset.csv
```

### Run Tests

```bash
pytest tests/unit/domain/test_observation.py -v
```

---

## Example Code Patterns

These patterns emerged from the development discussions and are now best practices.

### Pattern 1: Creating Entities with Claims

```python
from entityspine.domain.entity import Entity
from entityspine.domain.claim import IdentifierClaim
from entityspine.domain.enums import EntityType, IdentifierScheme

# Create entity
apple = Entity.create(
    primary_name="Apple Inc.",
    entity_type=EntityType.CORPORATION,
    domicile_country="US",
    domicile_jurisdiction="US-CA"
)

# Add identifier claims from multiple sources
claims = [
    IdentifierClaim.create(
        entity_id=apple.entity_id,
        scheme=IdentifierScheme.LEI,
        value="HWUPKR0MPOU8FGXBT394",
        source_system="gleif"
    ),
    IdentifierClaim.create(
        entity_id=apple.entity_id,
        scheme=IdentifierScheme.CUSIP,
        value="037833100",
        source_system="factset"
    ),
    IdentifierClaim.create(
        entity_id=apple.entity_id,
        scheme=IdentifierScheme.CIK,
        value="0000320193",
        source_system="sec"
    ),
]

print(f"Apple ({apple.entity_id}) has {len(claims)} identifiers")
```

### Pattern 2: Recording Financial Observations

```python
from entityspine.domain.observation import Observation, MetricSpec, FiscalPeriod
from entityspine.domain.observation import ProvenanceRef, SourceKey, ValueWithUnits
from entityspine.domain.enums import MetricCode, PeriodType, ProvenanceKind, VendorNamespace
from decimal import Decimal

# Annual revenue from SEC filing
revenue_obs = Observation.create(
    entity_id=apple.entity_id,
    metric=MetricSpec(code=MetricCode.REVENUE),
    period=FiscalPeriod(fiscal_year=2024, period_type=PeriodType.ANNUAL),
    value=ValueWithUnits(raw_value=Decimal("383285000000"), currency="USD"),
    provenance=ProvenanceRef(
        kind=ProvenanceKind.FILING,
        namespace=VendorNamespace.SEC,
        document_id="0000320193-24-000081"
    )
)

# Quarterly EPS from vendor data
eps_obs = Observation.create(
    entity_id=apple.entity_id,
    metric=MetricSpec(code=MetricCode.EPS_DILUTED, per_share=True),
    period=FiscalPeriod(fiscal_year=2024, fiscal_quarter=4, period_type=PeriodType.QUARTERLY),
    value=ValueWithUnits(raw_value=Decimal("1.64"), currency="USD"),
    provenance=ProvenanceRef(
        kind=ProvenanceKind.VENDOR,
        namespace=VendorNamespace.FACTSET
    )
)

print(f"Revenue dedup key: {revenue_obs.dedup_key}")
print(f"EPS dedup key: {eps_obs.dedup_key}")
```

### Pattern 3: Calendar Events and M&A

```python
from entityspine.domain.graph import Event
from entityspine.domain.enums import EventType, EventStatus
from datetime import date
from decimal import Decimal

# Upcoming earnings call
earnings = Event(
    event_type=EventType.EARNINGS_RELEASE,
    title="Apple Q1 2025 Earnings Call",
    entity_id=apple.entity_id,
    scheduled_on=date(2025, 1, 30),
    fiscal_year=2025,
    fiscal_quarter=1,
    report_time="AMC",  # After Market Close
    status=EventStatus.SCHEDULED
)

# Completed M&A
acquisition = Event(
    event_type=EventType.ACQUISITION,
    title="Apple acquires AI startup",
    entity_id=apple.entity_id,
    related_entity_ids=["01HQ9TARGET"],
    occurred_on=date(2024, 12, 1),
    amount=Decimal("1000000000"),  # $1B
    currency="USD",
    status=EventStatus.COMPLETED
)

# Properties for filtering
print(f"Earnings is calendar event: {earnings.is_calendar_event}")
print(f"Acquisition has amount: {acquisition.is_financial_event}")
print(f"Earnings fiscal period: {earnings.fiscal_period_str}")
```

### Pattern 4: Multi-Tier Storage

```python
from entityspine.stores import JsonEntityStore
from entityspine.stores.sqlite_store import SqliteStore
from pathlib import Path

# Tier 0: In-memory for testing
memory_store = JsonEntityStore()
memory_store.save_entity(apple)

# Tier 1: SQLite for local development  
sqlite_store = SqliteStore(db_path="entityspine.db")
sqlite_store.initialize()
sqlite_store.save_entity(apple)
sqlite_store.save_claims(claims)

# Query example
found = sqlite_store.resolve_identifier(
    scheme=IdentifierScheme.CUSIP,
    value="037833100"
)
print(f"Resolved CUSIP to: {found.primary_name}")
```

### Pattern 5: CLI Usage Examples

```bash
# Resolve any identifier to entity
entityspine resolve AAPL
entityspine resolve 037833100       # CUSIP
entityspine resolve US0378331005    # ISIN
entityspine resolve HWUPKR0MPOU8FGXBT394  # LEI

# Search by name (fuzzy)
entityspine search "Microsft"        # Finds "Microsoft"
entityspine search "Apple" --limit 5

# View entity network graph
entityspine graph network AAPL --depth 2

# Load FactSet data
entityspine load factset /path/to/ff_combined.csv --limit 10000

# Initialize fresh database
entityspine db init --tier 1

# Run API server
entityspine serve --port 8000
```

---

*Generated from commit history: `8114acd..e8dabdb`*
