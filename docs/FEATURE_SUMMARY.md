# EntitySpine v2.3.0 - Feature Summary

This document consolidates all recent features added to EntitySpine, organized by feature area.

---

## 📊 Overview

EntitySpine has evolved into a comprehensive multi-source entity resolution system for financial data, with the following major feature areas recently added:

| Feature Area | Components | Status |
|-------------|-----------|--------|
| Modular Enums | 10 enum files | ✅ Complete |
| Financial Observation Model | 8 dataclasses | ✅ Complete |
| Calendar Events | Event model enhancements | ✅ Complete |
| Tier 4/5 Stores | Elasticsearch + Neo4j | ✅ Complete |
| CLI | 15+ commands | ✅ Complete |
| React Visualization | 2 apps | ✅ Complete |
| FactSet Integration | Loader + examples | ✅ Complete |
| FastAPI Endpoints | Enhanced routes | ✅ Complete |

---

## 1. 🏷️ Modular Enum System

**Commit:** `8114acd` - refactor(domain): split enums.py into modular package

### What Changed
The monolithic 857-line `enums.py` was split into 10 focused modules:

| File | Purpose | Key Enums |
|------|---------|-----------|
| `core.py` | Fundamental types | `Confidence`, `ProcessingState`, `ValidationStatus` |
| `identifiers.py` | ID schemes | `IdentifierScheme` (LEI, CUSIP, ISIN, FIGI, etc.) |
| `resolution.py` | Entity resolution | `ResolutionStrategy`, `ResolutionSource`, `MatchType` |
| `graph.py` | Graph relationships | `RelationshipType`, `EdgeDirection`, `NodeType` |
| `events.py` | Corporate events | `EventType` (40+ types), `EventStatus`, `EventSeverity` |
| `assets.py` | Asset classes | `AssetClass`, `InstrumentType`, `SecurityStatus` |
| `observations.py` | Financial metrics | `MetricCode`, `MetricCategory`, `ReportTime` |
| `vendors.py` | Data providers | `DataVendor`, `FeedType`, `DeliveryMethod` |
| `geo.py` | Geography | `CountryCode`, `RegionType`, `ExchangeCode` |
| `transactions.py` | Corporate actions | `TransactionType`, `CorporateActionType` |

### Key Design Pattern
```python
# All enums follow (str, Enum) pattern for JSON serialization
class MetricCode(str, Enum):
    REVENUE = "revenue"
    NET_INCOME = "net_income"
    # ...
```

---

## 2. 📈 Financial Observation Model v2.2.5

**Commit:** `eac71d7` - feat(domain): add Financial Observation Model v2.2.5

### Purpose
A comprehensive model for financial metrics with provenance tracking, vendor attribution, and estimate handling.

### Core Classes

```
src/entityspine/domain/observation.py (823 lines)
├── MetricSpec      - What metric + frequency + fiscal info
├── FiscalPeriod    - Fiscal year/quarter representation
├── ProvenanceRef   - Source/revision tracking
├── SourceKey       - Vendor + feed + as-of-date
├── EstimateInfo    - Analyst estimate details
├── ValueWithUnits  - Numeric value + units + currency
├── Observation     - Complete observation record
└── ObservationSet  - Collection with metadata
```

### Example Usage
```python
from entityspine.domain.observation import (
    Observation, MetricSpec, SourceKey, ValueWithUnits
)
from entityspine.domain.enums import MetricCode, DataVendor

obs = Observation(
    id=generate_ulid(),
    entity_id="01HXYZ...",
    metric=MetricSpec(
        code=MetricCode.REVENUE,
        fiscal_year=2024,
        fiscal_quarter=1
    ),
    value=ValueWithUnits(
        numeric=125_000_000_000.0,
        units="USD",
        currency="USD"
    ),
    source=SourceKey(
        vendor=DataVendor.FACTSET,
        feed_id="factset-fundamentals"
    )
)
```

### Test Coverage
- 35 tests in `tests/test_observation.py`
- All edge cases covered

---

## 3. 📅 Calendar Event Support

**Commit:** `58da798` - feat(domain): enhance Event model with calendar event support

### New Event Fields

| Field | Type | Purpose |
|-------|------|---------|
| `scheduled_on` | `date \| None` | Original scheduled date |
| `effective_date` | `date \| None` | When event takes effect |
| `fiscal_year` | `int \| None` | Related fiscal year |
| `fiscal_quarter` | `int \| None` | Related fiscal quarter (1-4) |
| `report_time` | `ReportTime \| None` | Before/After market |
| `currency` | `str \| None` | For monetary events |
| `amount` | `Decimal \| None` | Dividend, split ratio, etc. |
| `entity_id` | `str \| None` | Primary entity reference |
| `related_entity_ids` | `list[str]` | Related entities (M&A, etc.) |

### New Properties

```python
@property
def is_calendar_event(self) -> bool:
    """Events investors track on calendars"""
    return self.event_type in {
        EventType.EARNINGS_RELEASE,
        EventType.DIVIDEND_DECLARATION,
        EventType.STOCK_SPLIT,
        ...
    }

@property
def fiscal_period_str(self) -> str | None:
    """Format: 'FY2024' or 'Q1 FY2024'"""
```

### Event Categories (40+ Types)
- **Financial:** `EARNINGS_RELEASE`, `REVENUE_ANNOUNCEMENT`, `GUIDANCE_UPDATE`
- **Corporate Actions:** `DIVIDEND_DECLARATION`, `STOCK_SPLIT`, `MERGER_ACQUISITION`
- **Compliance:** `SEC_FILING`, `REGULATORY_ACTION`, `SANCTION_EVENT`
- **Governance:** `BOARD_CHANGE`, `CEO_CHANGE`, `SHAREHOLDER_MEETING`

---

## 4. 🗄️ Tier 4/5 Storage System

**Commit:** `d05e8d0` - feat(stores): add Tier 4/5 Elasticsearch and Neo4j stores

### Architecture

```
Tier 0/1: JSON/SQLite (lightweight)
    ↓
Tier 2: DuckDB (analytics)
    ↓
Tier 3: PostgreSQL (operational)
    ↓
Tier 4/5: PostgreSQL + Elasticsearch + Neo4j (enterprise)
```

### ElasticsearchStore (582 lines)

```python
from entityspine.stores import ElasticsearchStore

es_store = ElasticsearchStore(
    hosts=["localhost:9200"],
    index_prefix="entityspine"
)

# Fuzzy search with typo tolerance
results = await es_store.fuzzy_search(
    query="Microsft",  # Note typo
    fuzziness="AUTO"
)

# Autocomplete
suggestions = await es_store.autocomplete(
    prefix="Appl",
    field="name"
)
```

**Features:**
- Fuzzy matching with configurable fuzziness
- Autocomplete/suggest functionality
- BM25 relevance scoring
- Index lifecycle management

### Neo4jStore (744 lines)

```python
from entityspine.stores import Neo4jStore

neo4j_store = Neo4jStore(
    uri="bolt://localhost:7687",
    user="neo4j",
    password="password"
)

# Find shortest path between entities
path = await neo4j_store.find_path(
    source_id="entity_1",
    target_id="entity_2",
    max_hops=5
)

# Graph traversal
related = await neo4j_store.traverse(
    entity_id="entity_1",
    relationship_types=["SUBSIDIARY_OF", "OWNS"],
    depth=3
)
```

**Features:**
- O(1) hop traversal via Cypher
- Dijkstra shortest path
- Relationship pattern matching
- Graph statistics/metrics

### SyncService (492 lines)

```python
from entityspine.services import SyncService

sync = SyncService(
    pg_store=postgres_store,
    es_store=es_store,
    neo4j_store=neo4j_store
)

# Full sync
await sync.full_sync()

# Incremental sync (CDC-based)
await sync.incremental_sync(since=last_sync_time)
```

---

## 5. 🖥️ Command Line Interface

**Commit:** `2b07f46` - feat(cli): add comprehensive EntitySpine CLI

### Commands Overview

```bash
# Entity Resolution
entityspine resolve "Apple Inc" --strategy=fuzzy
entityspine search --query="tech companies" --limit=20

# Graph Operations
entityspine graph network <entity_id> --depth=2
entityspine graph path <source_id> <target_id>

# SEC Filings
entityspine filings list <entity_id>
entityspine filings download <accession_number>

# Database
entityspine db init --tier=3
entityspine db migrate
entityspine db stats

# Server
entityspine serve --host=0.0.0.0 --port=8000
```

### Tech Stack
- **typer:** CLI framework
- **rich:** Formatted output, tables, progress bars
- **httpx:** Async HTTP client

---

## 6. 🌐 React Visualization Apps

**Commit:** `c9c921f` - feat(examples): add React knowledge graph visualization apps

### entity-graph-app
3D force-directed graph visualization for entity relationships.

```bash
cd examples/entity-graph-app
npm install
npm run dev
```

**Tech Stack:**
- React + TypeScript + Vite
- react-force-graph-3d
- three.js
- Tailwind CSS

### entity-relationships-dashboard
Interactive dashboard for exploring entity relationships and events.

```bash
cd examples/entity-relationships-dashboard
npm install
npm run dev
```

**Features:**
- Real-time entity search
- Timeline view for events
- Relationship type filtering
- Entity detail panels

---

## 7. 📊 FactSet Integration

**Commit:** `b1ee064` - docs: add FactSet integration guide and API docs

### Supported Data Types

| FactSet Feed | EntitySpine Mapping |
|-------------|---------------------|
| Entity Master | `Entity` + identifiers |
| Fundamentals | `Observation` records |
| Ownership | `Claim` relationships |
| Corporate Events | `Event` records |

### Example: Loading FactSet Entities

```python
from entityspine.examples import load_factset_entities

# Load from FactSet export
entities = load_factset_entities(
    "path/to/factset_export.csv",
    vendor=DataVendor.FACTSET
)

# Store in database
for entity in entities:
    await store.upsert_entity(entity)
```

---

## 8. 🔌 FastAPI Endpoints

**Commit:** `859366b` - feat(api): enhance FastAPI endpoints

### New/Enhanced Endpoints

```
GET  /api/v1/entities/{id}           - Get entity by ID
GET  /api/v1/entities/search         - Search entities
POST /api/v1/entities/resolve        - Resolve entity from name

GET  /api/v1/graph/neighbors/{id}    - Get entity neighbors
GET  /api/v1/graph/path              - Find path between entities

GET  /api/v1/observations/{entity}   - Get entity observations
POST /api/v1/observations            - Create observation

GET  /api/v1/events/{entity}         - Get entity events
GET  /api/v1/events/calendar         - Get calendar events
```

---

## 📁 Project Structure After Changes

```
entityspine/
├── src/entityspine/
│   ├── domain/
│   │   ├── enums/              # NEW: Modular enums
│   │   │   ├── __init__.py
│   │   │   ├── core.py
│   │   │   ├── identifiers.py
│   │   │   ├── resolution.py
│   │   │   ├── graph.py
│   │   │   ├── events.py
│   │   │   ├── assets.py
│   │   │   ├── observations.py
│   │   │   ├── vendors.py
│   │   │   ├── geo.py
│   │   │   └── transactions.py
│   │   ├── observation.py      # NEW: Financial Observation Model
│   │   ├── graph.py            # ENHANCED: Event model
│   │   └── ...
│   ├── stores/
│   │   ├── elasticsearch_store.py  # NEW: Tier 4/5
│   │   └── neo4j_store.py          # NEW: Tier 4/5
│   ├── services/
│   │   └── sync_service.py     # NEW: PG→ES/Neo4j sync
│   └── cli.py                  # NEW: CLI
├── examples/
│   ├── entity-graph-app/       # NEW: 3D graph viz
│   ├── entity-relationships-dashboard/  # NEW: Dashboard
│   └── ...
├── prompts/                    # NEW: LLM prompts
└── docs/
    ├── ENHANCEMENTS.md
    ├── FACTSET_GUIDE.md
    └── ...
```

---

## 🔧 Development Guidelines

### Domain Layer Rules (CRITICAL)
1. **STDLIB ONLY** - No external dependencies (no pydantic, no attrs)
2. Use `@dataclass(frozen=True, slots=True)` for all models
3. All enums inherit from `(str, Enum)` for JSON compatibility
4. IDs use ULID via `generate_ulid()` from timestamps.py
5. No ORM methods in domain classes

### Import Conventions
```python
# Good - from package
from entityspine.domain.enums import MetricCode, EventType

# Bad - from individual file
from entityspine.domain.enums.observations import MetricCode
```

---

## 📋 Commits Reference

| Hash | Type | Description |
|------|------|-------------|
| `8114acd` | refactor | Split enums.py into modular package |
| `eac71d7` | feat | Add Financial Observation Model v2.2.5 |
| `58da798` | feat | Enhance Event model with calendar support |
| `d05e8d0` | feat | Add Tier 4/5 ES and Neo4j stores |
| `2b07f46` | feat | Add comprehensive CLI |
| `f7ac7bf` | feat | Enhance Entity and Claim models |
| `6f63f6d` | feat | Add tier and ingestion examples |
| `55c29db` | docs | Add code conventions and architecture proposals |
| `8f84c66` | docs | Add multi-vendor ingestion architecture |
| `b1ee064` | docs | Add FactSet integration guide |
| `6a315c8` | build | Add mkdocs configuration |
| `859366b` | feat | Enhance FastAPI endpoints |
| `c9c921f` | feat | Add React knowledge graph visualization apps |

---

*Last updated: Session completing documentation consolidation*
