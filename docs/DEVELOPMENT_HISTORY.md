# EntitySpine Development History

This document provides a chronological summary of commits, features, and files affected during the v2.3.0 development session.

---

## Table of Contents

1. [Session Overview](#session-overview)
2. [Commit Timeline](#commit-timeline)
3. [Feature Summary by Area](#feature-summary-by-area)
4. [Files Changed by Category](#files-changed-by-category)
5. [Documentation Index](#documentation-index)
6. [Quick Reference](#quick-reference)

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
3. **Calendar Event Support** - 40+ event types aligned with FactSet/SEC
4. **Tier 4/5 Storage** - Elasticsearch + Neo4j stores with sync service
5. **CLI** - Comprehensive command-line interface
6. **React Visualization Apps** - 3D graph visualization dashboards
7. **FactSet Integration** - Entity loading and identifier crosswalk
8. **Documentation Overhaul** - ADRs, features docs, and reorganization

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

**Why:** FactSet Events Calendar integration required scheduling, fiscal period, and monetary value support.

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
Bloomberg (1) > FactSet (2) > Thomson Reuters (3) > SEC (4) > User (5)
```

---

### Commit 10: `b1ee064` - FactSet Integration Guide
**Date:** Wed Jan 28 22:50:19 2026  
**Type:** `docs`  
**Title:** Add FactSet integration guide and API docs

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

*Generated from commit history: `8114acd..e8dabdb`*
