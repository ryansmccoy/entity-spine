# EntitySpine Architecture & Tier System

## Overview

EntitySpine is a comprehensive entity resolution and knowledge graph system for financial data. This document defines the architecture across all layers and the tier-based capability system.

---

## Architecture Layers

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           FRONTEND APPS                                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────┐  │
│  │ Entity Dashboard │  │ Graph Explorer  │  │ Trading/Admin Desktop   │  │
│  │ (React + 3D)     │  │ (Force Graph)   │  │ (Full Bloomberg-style)  │  │
│  └────────┬────────┘  └────────┬────────┘  └───────────┬─────────────┘  │
└───────────┼────────────────────┼───────────────────────┼────────────────┘
            │                    │                       │
            ▼                    ▼                       ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           REST API (FastAPI)                             │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────┐  ┌───────────────┐  │
│  │ /resolve     │  │ /entities    │  │ /graph     │  │ /filings      │  │
│  │ /search      │  │ /securities  │  │ /network   │  │ /financials   │  │
│  └──────────────┘  └──────────────┘  └────────────┘  └───────────────┘  │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
            ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       PYTHON SDK (entityspine)                           │
│  ┌──────────────────┐  ┌──────────────────┐  ┌───────────────────────┐  │
│  │ EntityResolver   │  │ GraphService     │  │ FilingParser          │  │
│  │ .resolve()       │  │ .get_network()   │  │ .parse_10k()          │  │
│  │ .search()        │  │ .find_path()     │  │ .extract_exhibits()   │  │
│  │ .batch_resolve() │  │ .get_officers()  │  │ .build_graph()        │  │
│  └──────────────────┘  └──────────────────┘  └───────────────────────┘  │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
            ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        CLI (entityspine)                                 │
│  entityspine resolve AAPL                                                │
│  entityspine search "Apple"                                              │
│  entityspine graph network --entity=AAPL --depth=2                       │
│  entityspine ingest --filing=0000320193-24-000081                        │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
            ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         DOMAIN MODELS                                    │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌──────────────────┐   │
│  │ Entity     │  │ Security   │  │ Filing     │  │ EntityRelation-  │   │
│  │ Listing    │  │ Identifier │  │ Section    │  │ ship/PersonRole  │   │
│  │ Claim      │  │ Claim      │  │ Financials │  │ Network/Path     │   │
│  └────────────┘  └────────────┘  └────────────┘  └──────────────────┘   │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
            ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          STORAGE LAYER                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐ │
│  │ Tier 0      │  │ Tier 1      │  │ Tier 2      │  │ Tier 3          │ │
│  │ JSON/Memory │  │ SQLite      │  │ DuckDB      │  │ PostgreSQL      │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Tier System

### Tier Progression

| Feature | Tier 0 (Free) | Tier 1 (Basic) | Tier 2 (Pro) | Tier 3 (Enterprise) | Tier 4/5 (Platform) |
|---------|---------------|----------------|--------------|---------------------|---------------------|
| **Price** | Free | $29/mo | $99/mo | Custom | Custom |
| **Storage** | JSON/Memory | SQLite | DuckDB | PostgreSQL | PG + ES + Neo4j |
| **Dependencies** | Zero (stdlib) | Zero (stdlib) | duckdb | asyncpg, sqlmodel | + elasticsearch, neo4j |

### Storage Tier Details

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              STORAGE TIER PROGRESSION                                    │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                          │
│  TIER 0/1            TIER 2              TIER 3              TIER 4/5                   │
│  ───────             ──────              ──────              ───────                    │
│                                                                                          │
│  JSON/SQLite         DuckDB              PostgreSQL          PostgreSQL (SoT)            │
│  Single file         Analytics           Full canonical      + Elasticsearch            │
│  <100K entities      OLAP queries        + pgvector          + Neo4j (graphs)           │
│                                                                                          │
│  Use case:           Use case:           Use case:           Use case:                  │
│  - CLI tools         - Filing analytics  - Source of truth   - Full-text search         │
│  - Single user       - Large batch joins - Multi-user access - Graph traversal          │
│  - Offline work      - Columnar agg      - ACID transactions - Path finding             │
│  - Quick start       - Read-heavy        - Conflict handling - Network analysis         │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### Why Elasticsearch + Neo4j? (Tier 4/5)

| Capability | PostgreSQL | Elasticsearch | Neo4j |
|------------|------------|---------------|-------|
| **Fuzzy text search** | `pg_trgm` (slow) | **Native, blazing fast** | ❌ |
| **Autocomplete** | Manual trigrams | **Edge-ngram built-in** | ❌ |
| **Typo tolerance** | Limited | **"Appel" → "Apple"** | ❌ |
| **Relevance scoring** | Basic | **TF-IDF, BM25** | ❌ |
| **Multi-hop traversal** | Recursive CTEs (slow) | ❌ | **Native, O(1) per hop** |
| **Path finding** | Very slow | ❌ | **Dijkstra built-in** |
| **Pattern matching** | Complex SQL | ❌ | **Cypher: `(a)-[:OWNS*1..5]->(b)`** |
| **Graph algorithms** | Manual | ❌ | **PageRank, centrality, community** |

**Source of Truth Architecture:**
```
PostgreSQL (Primary) ──────┬──────► Elasticsearch (search index)
                           │         - Eventual consistency
                           │         - Refresh on entity changes
                           │
                           ├──────► Neo4j (graph replica)
                           │         - Sync relationships
                           │         - Refresh on edge changes
                           │
                           └──────► DuckDB (analytics snapshot)
                                     - Nightly batch sync
                                     - Read-only analytics
```

### Tier 4/5 Store Implementations

**Elasticsearch Store** (`entityspine.stores.elasticsearch_store`):
```python
from entityspine.stores.elasticsearch_store import ElasticsearchStore

es_store = ElasticsearchStore(hosts=["http://localhost:9200"])
await es_store.initialize()

# Fuzzy search (typo tolerance)
results = await es_store.search("Appel Inc")  # Finds "Apple Inc."

# Autocomplete
suggestions = await es_store.autocomplete("micro")  # Microsoft, Micron, Microchip...

# Search by identifier
entity = await es_store.search_by_identifier("cik", "0000320193")
```

**Neo4j Store** (`entityspine.stores.neo4j_store`):
```python
from entityspine.stores.neo4j_store import Neo4jStore

neo4j_store = Neo4jStore(
    uri="bolt://localhost:7687",
    user="neo4j",
    password="password"
)
await neo4j_store.initialize()

# Get ownership chain
chain = await neo4j_store.get_ownership_chain("entity_id", max_depth=5)

# Find path between entities (six degrees)
path = await neo4j_store.find_path("boeing_id", "lockheed_id")

# Get network for visualization
network = await neo4j_store.get_entity_network("entity_id", max_depth=2)
```

**Sync Service** (`entityspine.services.sync_service`):
```python
from entityspine.services.sync_service import SyncService

sync = SyncService(
    pg_store=postgres_store,
    es_store=elasticsearch_store,
    neo4j_store=neo4j_store,
)

# Full sync (initial load)
result = await sync.full_sync()

# Incremental sync (periodic)
result = await sync.incremental_sync(since=last_sync_time)

# Real-time single entity sync
await sync.sync_entity(entity_id)

# Check sync health
stats = await sync.get_sync_stats()
```

### Data Capabilities by Tier

| Capability | Tier 0 | Tier 1 | Tier 2 | Tier 3 |
|------------|--------|--------|--------|--------|
| **Entity Resolution** | ✅ | ✅ | ✅ | ✅ |
| SEC company_tickers.json | ✅ | ✅ | ✅ | ✅ |
| Ticker → CIK lookup | ✅ | ✅ | ✅ | ✅ |
| CIK → Entity lookup | ✅ | ✅ | ✅ | ✅ |
| Basic name search | ✅ | ✅ | ✅ | ✅ |
| **Identifier Claims** | ❌ | ✅ | ✅ | ✅ |
| LEI resolution | ❌ | ✅ | ✅ | ✅ |
| ISIN/CUSIP resolution | ❌ | ✅ | ✅ | ✅ |
| FIGI resolution | ❌ | ❌ | ✅ | ✅ |
| Temporal queries (as_of) | ❌ | ✅ | ✅ | ✅ |
| **Fuzzy Matching** | Basic | ✅ | ✅ | ✅ |
| Alias matching | ❌ | ✅ | ✅ | ✅ |
| Name normalization | ❌ | ✅ | ✅ | ✅ |
| Confidence scores | ❌ | ✅ | ✅ | ✅ |
| **Knowledge Graph** | ❌ | Basic | ✅ | ✅ |
| Corporate structure | ❌ | ✅ | ✅ | ✅ |
| Officers/Directors | ❌ | ❌ | ✅ | ✅ |
| Ownership positions | ❌ | ❌ | ✅ | ✅ |
| Network traversal | ❌ | ❌ | ✅ | ✅ |
| Path finding | ❌ | ❌ | ✅ | ✅ |
| **SEC Filing Data** | ❌ | ❌ | ✅ | ✅ |
| Filing metadata | ❌ | ❌ | ✅ | ✅ |
| XBRL financial data | ❌ | ❌ | ✅ | ✅ |
| Section extraction | ❌ | ❌ | ✅ | ✅ |
| Change detection | ❌ | ❌ | ❌ | ✅ |
| **Analytics** | ❌ | ❌ | ✅ | ✅ |
| Aggregations | ❌ | ❌ | ✅ | ✅ |
| Time series | ❌ | ❌ | ✅ | ✅ |
| OLAP queries | ❌ | ❌ | ✅ | ✅ |
| **Scale** | 10K entities | 50K entities | 500K entities | Unlimited |
| Batch operations | 100/call | 1,000/call | 10,000/call | Unlimited |
| API rate limit | 100/day | 10K/day | 100K/day | Unlimited |

### API Access by Tier

| Endpoint | Tier 0 | Tier 1 | Tier 2 | Tier 3 |
|----------|--------|--------|--------|--------|
| `GET /resolve/{query}` | ✅ | ✅ | ✅ | ✅ |
| `POST /resolve/batch` | ❌ | ✅ | ✅ | ✅ |
| `GET /entities/{id}` | ✅ | ✅ | ✅ | ✅ |
| `GET /entities/cik/{cik}` | ✅ | ✅ | ✅ | ✅ |
| `GET /entities/ticker/{ticker}` | ✅ | ✅ | ✅ | ✅ |
| `GET /search` | ✅ (basic) | ✅ | ✅ | ✅ |
| `GET /graph/network/{id}` | ❌ | ✅ (depth=1) | ✅ | ✅ |
| `GET /graph/path` | ❌ | ❌ | ✅ | ✅ |
| `GET /graph/officers/{id}` | ❌ | ❌ | ✅ | ✅ |
| `GET /filings/{accession}` | ❌ | ❌ | ✅ | ✅ |
| `GET /filings/company/{cik}` | ❌ | ❌ | ✅ | ✅ |
| `GET /financials/{cik}` | ❌ | ❌ | ✅ | ✅ |
| `POST /ingest/filing` | ❌ | ❌ | ❌ | ✅ |
| `WebSocket /stream` | ❌ | ❌ | ❌ | ✅ |

---

## Component Details

### 1. Python SDK (`entityspine`)

```python
# Tier 0 - Zero dependencies
from entityspine import EntityResolver
resolver = EntityResolver()  # Uses JSON store
result = resolver.resolve("AAPL")

# Tier 1 - SQLite (still zero dependencies)
from entityspine import EntityResolver
resolver = EntityResolver(db_path="entities.db")
result = resolver.resolve("AAPL", as_of=date(2020, 1, 1))

# Tier 2 - DuckDB (pip install entityspine[duckdb])
from entityspine import EntityResolver, GraphService
resolver = EntityResolver(tier=2)
graph = GraphService(resolver.store)
network = graph.get_entity_network("entity_id", max_depth=3)

# Tier 3 - PostgreSQL (pip install entityspine[postgres])
from entityspine import EntityResolver
resolver = EntityResolver(
    connection_string="postgresql://...",
    tier=3
)
```

### 2. REST API (FastAPI)

```bash
# Run locally
uvicorn entityspine.api.app:app --reload

# Docker
docker run -p 8000:8000 entityspine/api

# With tier configuration
ENTITYSPINE_TIER=2 uvicorn entityspine.api.app:app
```

**Endpoints:**
- `/resolve/{query}` - Resolve any identifier
- `/resolve/batch` - Batch resolution
- `/entities/{id}` - Get entity by ID
- `/entities/cik/{cik}` - Get by CIK
- `/entities/ticker/{ticker}` - Get by ticker
- `/search` - Full-text search
- `/graph/network/{id}` - Get entity network
- `/graph/path` - Find path between entities
- `/graph/subsidiaries/{id}` - Get subsidiaries
- `/graph/officers/{id}` - Get officers/directors
- `/filings/{accession}` - Get filing details
- `/filings/company/{cik}` - Get company filings
- `/financials/{cik}` - Get financial data

### 3. CLI

```bash
# Install
pip install entityspine[cli]

# Resolution
entityspine resolve AAPL
entityspine resolve 0000320193 --as-of 2020-01-01
entityspine resolve "Apple Inc" --fuzzy

# Search
entityspine search "technology" --sector
entityspine search "Tim Cook" --type person

# Graph
entityspine graph network AAPL --depth 2 --output json
entityspine graph path AAPL MSFT
entityspine graph officers AAPL --current-only

# Filings
entityspine filings list 0000320193 --form-type 10-K
entityspine filings parse 0000320193-24-000081 --extract-sections

# Database
entityspine db init --tier 1
entityspine db load-sec
entityspine db stats
entityspine db migrate --from tier1 --to tier2

# Server
entityspine serve --port 8000 --tier 2
```

### 4. Database Schema

**Tier 1 (SQLite):**
- `entities` - Core entity records
- `identifier_claims` - All identifier mappings
- `listings` - Ticker/exchange listings
- `entity_relationships` - Basic relationships

**Tier 2 (DuckDB) - adds:**
- `filings` - SEC filing metadata
- `filing_sections` - Parsed sections
- `financial_statements` - XBRL data
- `person_roles` - Officers/directors

**Tier 3 (PostgreSQL) - adds:**
- Full-text search indexes
- Materialized views
- Audit logging
- Multi-tenancy support

---

## Implementation Roadmap

### Phase 1: Core SDK (Current)
- [x] Domain models (Entity, Security, Listing, Claims)
- [x] EntityResolver with Tier 0/1 stores
- [x] Basic FastAPI endpoints
- [ ] **CLI implementation**
- [ ] **GraphService integration in API**

### Phase 2: Knowledge Graph
- [x] Graph domain models
- [x] GraphService for traversal
- [ ] **Graph API endpoints**
- [ ] **Network visualization data**
- [ ] **Path finding API**

### Phase 3: Filing Integration
- [ ] Filing parser integration
- [ ] XBRL extraction
- [ ] Section extraction
- [ ] Change detection

### Phase 4: Enterprise Features
- [ ] PostgreSQL store
- [ ] Multi-tenancy
- [ ] Audit logging
- [ ] Streaming updates

---

## Data Sources

### Included (All Tiers)
- SEC company_tickers.json (auto-downloaded)
- SEC EDGAR filing index

### Tier 2+ Data Sources
- OpenFIGI API
- LEI-GLEIF database
- SEC XBRL filings
- SEC form 4 (insider transactions)

### Tier 3+ Data Sources
- Real-time SEC feed
- Custom data ingestion
- Third-party integrations

---

## Frontend Apps

### 1. Entity Relationships Dashboard
Location: `entityspine/examples/entity-relationships-dashboard/`
- Boeing ecosystem demo
- 3D force-directed graph
- Corporate hierarchy tree
- Company profile view

### 2. Entity Graph App
Location: `entityspine/examples/entity-graph-app/`
- Standalone 3D graph explorer
- Custom node rendering
- Interactive controls

### 3. Trading Desktop (market-spine)
Location: `market-spine/trading-desktop/`
- Full admin interface
- Entity profile pages
- Relationship exploration

---

## Configuration

### Environment Variables
```bash
# Storage
ENTITYSPINE_DB_PATH=/path/to/db
ENTITYSPINE_TIER=2

# API
ENTITYSPINE_API_HOST=0.0.0.0
ENTITYSPINE_API_PORT=8000
ENTITYSPINE_API_KEY=your-api-key

# Tier 3 (PostgreSQL)
ENTITYSPINE_PG_HOST=localhost
ENTITYSPINE_PG_PORT=5432
ENTITYSPINE_PG_DATABASE=entityspine
ENTITYSPINE_PG_USER=entityspine
ENTITYSPINE_PG_PASSWORD=secret

# Tier 4/5 (Elasticsearch)
ENTITYSPINE_ES_HOSTS=http://localhost:9200
ENTITYSPINE_ES_INDEX=entityspine_entities

# Tier 4/5 (Neo4j)
ENTITYSPINE_NEO4J_URI=bolt://localhost:7687
ENTITYSPINE_NEO4J_USER=neo4j
ENTITYSPINE_NEO4J_PASSWORD=password

# Features
ENTITYSPINE_AUTO_LOAD_SEC=true
ENTITYSPINE_CACHE_ENABLED=true
ENTITYSPINE_CACHE_TTL=3600
```

### pyproject.toml Extras
```toml
[project.optional-dependencies]
# Tier 0/1 - Zero dependencies (default)

# Tier 2 - DuckDB analytics
duckdb = ["duckdb>=1.0.0"]

# Tier 3 - PostgreSQL production
postgres = ["asyncpg>=0.29.0", "psycopg[binary]>=3.1.0"]

# Tier 4/5 - Search & Graph
search = ["elasticsearch>=8.12.0"]
graph = ["neo4j>=5.15.0"]
platform = ["entityspine[postgres,search,graph]"]

# API service
api = ["fastapi>=0.115.0", "uvicorn[standard]>=0.32.0"]

# CLI
cli = ["typer>=0.9.0", "rich>=13.0.0"]

# Full installation
full = ["entityspine[duckdb,postgres,api,cli,search,graph]"]
```

---

## Next Steps

1. ~~**Implement CLI**~~ ✅ - Added typer-based CLI with all commands
2. ~~**Graph API endpoints**~~ ✅ - Exposed GraphService through REST
3. ~~**Frontend API client**~~ ✅ - Created api.ts and hooks.ts for dashboard
4. **Database migration** - Add tier migration support
5. **API authentication** - Add API key/tier validation
6. **Frontend API integration** - Connect dashboards to live API
7. **Tier enforcement** - Rate limiting and feature gating

---

## Implementation Status

### Completed
- [x] Domain models (Entity, Security, Listing, Claims)
- [x] EntityResolver with Tier 0/1 stores
- [x] Basic FastAPI endpoints (/resolve, /entities, /search)
- [x] GraphService for relationship traversal
- [x] CLI implementation (`entityspine` command)
- [x] Graph API endpoints (/graph/network, /graph/subsidiaries, /graph/officers, /graph/path)
- [x] Frontend API client (api.ts, hooks.ts)
- [x] Entity Relationships Dashboard (React + 3D)
- [x] PostgreSQL schema (db/schema.sql)
- [x] **Elasticsearch Store** (`stores/elasticsearch_store.py`)
- [x] **Neo4j Store** (`stores/neo4j_store.py`)
- [x] **Sync Service** (`services/sync_service.py`)

### In Progress
- [ ] Tier enforcement middleware
- [ ] API key authentication
- [ ] Rate limiting
- [ ] CDC (Change Data Capture) from PostgreSQL

### Planned
- [ ] DuckDB store (Tier 2)
- [ ] PostgreSQL store (Tier 3)
- [ ] Filing integration
- [ ] XBRL parsing
- [ ] Real-time streaming
- [ ] Neo4j Graph Data Science algorithms (PageRank, community detection)
