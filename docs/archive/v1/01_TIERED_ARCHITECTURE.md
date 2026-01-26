# Entity Master - Tiered Architecture

Each tier builds on the previous, adding capabilities without breaking changes.

---

## Tier Comparison Matrix

| Feature | Tier 1 | Tier 2 | Tier 3 | Tier 4 | Tier 5 |
|---------|--------|--------|--------|--------|--------|
| **Name** | Basic | Intermediate | Advanced | Full | Mind-blowing |
| **Storage** | SQLite | DuckDB | PostgreSQL | + Neo4j | + Vector DB |
| **Search** | LIKE queries | DuckDB FTS | Elasticsearch | Graph queries | Semantic search |
| **Updates** | Manual | Scheduled | Real-time feeds | + Webhooks | + Streaming |
| **API** | Python only | REST API | + GraphQL | + WebSocket | + gRPC |
| **Enrichment** | None | SEC only | + GLEIF/FIGI | + News/Social | + LLM |
| **Relationships** | None | Foreign keys | + Elasticsearch | Neo4j graph | + Knowledge graph |
| **Concurrency** | Single user | SQLite WAL | Connection pool | Distributed | Clustered |
| **Use Case** | Personal | Small team | Production | Enterprise | Research |

---

## Tier 1: Basic

**Storage**: SQLite
**Best for**: Personal projects, prototyping, offline use

### Features
- ✅ Local SQLite database
- ✅ CIK, ticker, name lookups
- ✅ Basic identifier resolution
- ✅ Manual data loading
- ✅ Python API only
- ❌ No search
- ❌ No enrichment
- ❌ No relationships

### Schema

```sql
-- Single-file SQLite database
CREATE TABLE entities (
    entity_id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    primary_name TEXT NOT NULL,
    status TEXT DEFAULT 'active',
    jurisdiction TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE identifiers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id TEXT NOT NULL REFERENCES entities(entity_id),
    scheme TEXT NOT NULL,  -- 'cik', 'ticker', 'lei', 'figi'
    value TEXT NOT NULL,
    exchange TEXT,  -- For tickers: 'NYSE', 'NASDAQ'
    source TEXT,
    confidence REAL DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(scheme, value)
);

CREATE TABLE aliases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id TEXT NOT NULL REFERENCES entities(entity_id),
    name TEXT NOT NULL,
    alias_type TEXT,  -- 'legal', 'trade', 'former', 'short'
    is_primary BOOLEAN DEFAULT FALSE,
    source TEXT
);

-- Indexes for fast lookups
CREATE INDEX idx_identifiers_scheme_value ON identifiers(scheme, value);
CREATE INDEX idx_identifiers_entity ON identifiers(entity_id);
CREATE INDEX idx_aliases_name ON aliases(name);
```

### Usage

```python
from entity_master import EntityMaster

# Initialize Tier 1
em = EntityMaster(tier="basic", db_path="entities.db")

# Load SEC data manually
await em.load_sec_tickers()  # Downloads company_tickers.json

# Resolve
entity = em.resolve("AAPL")
print(entity.primary_name)  # "APPLE INC"
print(entity.cik)           # "0000320193"

# Search (basic LIKE)
results = em.search("apple")  # Simple substring match
```

### File Structure

```
~/.entity_master/
├── entities.db          # SQLite database
└── config.yaml          # Configuration
```

---

## Tier 2: Intermediate

**Storage**: DuckDB
**Best for**: Analytics, small teams, data exploration

### Additional Features
- ✅ DuckDB analytics engine
- ✅ Full-text search (DuckDB FTS)
- ✅ Scheduled updates via FeedSpine
- ✅ Change detection (new/deleted tickers)
- ✅ Basic REST API
- ✅ Parquet export
- ✅ SQL analytics queries
- ❌ No external enrichment
- ❌ No relationship graph

### Schema Additions

```sql
-- DuckDB with additional analytics tables
CREATE TABLE entity_history (
    id INTEGER PRIMARY KEY,
    entity_id TEXT NOT NULL,
    field_name TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    change_source TEXT
);

CREATE TABLE sightings (
    id INTEGER PRIMARY KEY,
    entity_id TEXT NOT NULL,
    feed_id TEXT NOT NULL,
    capture_date DATE NOT NULL,
    record_hash TEXT,
    UNIQUE(entity_id, feed_id, capture_date)
);

-- FTS index
CREATE TABLE entities_fts AS (
    SELECT entity_id, primary_name, 
           (SELECT GROUP_CONCAT(name, ' ') FROM aliases WHERE aliases.entity_id = entities.entity_id) as all_names
    FROM entities
);
```

### FeedSpine Integration

```python
from feedspine import FeedSpine
from entity_master import EntityMaster
from entity_master.feeds import SECTickerFeed

# FeedSpine manages data ingestion
async with FeedSpine(storage=DuckDBStorage("feeds.duckdb")) as fs:
    fs.register_feed(SECTickerFeed())
    
    # Scheduled collection
    result = await fs.collect()
    print(f"New tickers: {result.new_count}")
    print(f"Updated: {result.updated_count}")

# Entity Master consumes the feeds
em = EntityMaster(tier="intermediate", feedspine=fs)

# Query changes
new_tickers = em.changes.since(days=7)
for entity in new_tickers:
    print(f"New: {entity.ticker} - {entity.primary_name}")
```

### Analytics Queries

```python
# DuckDB enables powerful analytics
em = EntityMaster(tier="intermediate")

# Companies by exchange
df = em.analytics.query("""
    SELECT i.exchange, COUNT(*) as count
    FROM identifiers i
    WHERE i.scheme = 'ticker'
    GROUP BY i.exchange
    ORDER BY count DESC
""")

# Export to Parquet
em.export_parquet("entities.parquet")
```

---

## Tier 3: Advanced

**Storage**: PostgreSQL + Elasticsearch
**Best for**: Production deployments, teams, API services

### Additional Features
- ✅ PostgreSQL for ACID compliance
- ✅ Elasticsearch for full-text search
- ✅ External enrichment (GLEIF, OpenFIGI)
- ✅ REST API with authentication
- ✅ GraphQL API
- ✅ Webhook notifications
- ✅ Connection pooling
- ✅ Basic relationship storage
- ❌ No graph database

### Schema Additions

```sql
-- PostgreSQL with proper constraints and indexes
CREATE TABLE entities (
    entity_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_type entity_type_enum NOT NULL,
    primary_name TEXT NOT NULL,
    status entity_status_enum DEFAULT 'active',
    jurisdiction VARCHAR(2),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    version INTEGER DEFAULT 1
);

-- Enrichment tracking
CREATE TABLE enrichments (
    id SERIAL PRIMARY KEY,
    entity_id UUID NOT NULL REFERENCES entities(entity_id),
    source TEXT NOT NULL,  -- 'gleif', 'openfigi', 'sec'
    enriched_at TIMESTAMPTZ DEFAULT NOW(),
    raw_response JSONB,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT
);

-- Basic relationships (foreign key based)
CREATE TABLE relationships (
    id SERIAL PRIMARY KEY,
    source_entity_id UUID NOT NULL REFERENCES entities(entity_id),
    target_entity_id UUID NOT NULL REFERENCES entities(entity_id),
    relationship_type relationship_type_enum NOT NULL,
    confidence REAL DEFAULT 1.0,
    evidence_accession TEXT,  -- Filing where relationship was found
    evidence_text TEXT,
    first_seen TIMESTAMPTZ DEFAULT NOW(),
    last_seen TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(source_entity_id, target_entity_id, relationship_type)
);

CREATE INDEX idx_relationships_source ON relationships(source_entity_id);
CREATE INDEX idx_relationships_target ON relationships(target_entity_id);
CREATE INDEX idx_relationships_type ON relationships(relationship_type);
```

### Elasticsearch Index

```json
{
  "mappings": {
    "properties": {
      "entity_id": { "type": "keyword" },
      "primary_name": { 
        "type": "text",
        "fields": {
          "keyword": { "type": "keyword" },
          "autocomplete": { 
            "type": "text",
            "analyzer": "autocomplete"
          }
        }
      },
      "aliases": { "type": "text" },
      "identifiers": {
        "type": "nested",
        "properties": {
          "scheme": { "type": "keyword" },
          "value": { "type": "keyword" }
        }
      },
      "entity_type": { "type": "keyword" },
      "jurisdiction": { "type": "keyword" },
      "exchange": { "type": "keyword" }
    }
  }
}
```

### Enrichment Pipeline

```python
em = EntityMaster(
    tier="advanced",
    postgres_url="postgresql://...",
    elasticsearch_url="http://localhost:9200",
)

# Auto-enrichment on resolve
entity = await em.resolve("AAPL", enrich=True)
print(entity.lei)   # Fetched from GLEIF
print(entity.figi)  # Fetched from OpenFIGI

# Bulk enrichment
await em.enrich_all(source="gleif", batch_size=100)
```

### REST API

```python
from fastapi import FastAPI
from entity_master.api import create_router

app = FastAPI()
app.include_router(create_router(em), prefix="/api/v1/entities")

# Endpoints:
# GET  /api/v1/entities/{identifier}     - Resolve entity
# GET  /api/v1/entities/search?q=apple   - Search entities
# POST /api/v1/entities                   - Create entity
# PUT  /api/v1/entities/{id}             - Update entity
# GET  /api/v1/entities/{id}/relationships - Get relationships
```

---

## Tier 4: Full

**Storage**: PostgreSQL + Elasticsearch + Neo4j
**Best for**: Enterprise, complex relationship queries

### Additional Features
- ✅ Neo4j graph database
- ✅ Cypher graph queries
- ✅ Supply chain analysis
- ✅ Path finding (degrees of separation)
- ✅ Community detection
- ✅ Entity extraction from filings
- ✅ WebSocket real-time updates
- ✅ Multi-hop relationship queries

### Neo4j Schema

```cypher
// Node types
CREATE CONSTRAINT entity_id IF NOT EXISTS
FOR (e:Entity) REQUIRE e.entity_id IS UNIQUE;

// Entity nodes
(:Entity {
    entity_id: "uuid",
    primary_name: "Apple Inc",
    entity_type: "company",
    cik: "0000320193",
    ticker: "AAPL",
    lei: "HWUPKR0MPOU8FGXBT394"
})

// Relationship types
(:Entity)-[:SUPPLIER_OF {
    confidence: 0.95,
    evidence: "10-K 2024",
    first_seen: date,
    last_seen: date
}]->(:Entity)

(:Entity)-[:COMPETITOR_OF {
    confidence: 0.90,
    bidirectional: true
}]->(:Entity)

(:Entity)-[:SUBSIDIARY_OF {
    ownership_pct: 100.0
}]->(:Entity)

// Person relationships
(:Person)-[:EXECUTIVE_OF {
    title: "CEO",
    start_date: date
}]->(:Entity)
```

### Graph Queries

```python
em = EntityMaster(
    tier="full",
    neo4j_uri="bolt://localhost:7687",
)

# Find supply chain
supply_chain = await em.graph.get_supply_chain("NVDA", depth=3)
# Returns: NVDA -> TSMC -> ASML -> Zeiss

# Find all paths between two companies
paths = await em.graph.find_paths("AAPL", "TSMC", max_depth=4)

# Get competitors (with confidence)
competitors = await em.graph.query("""
    MATCH (a:Entity {ticker: 'AAPL'})-[r:COMPETITOR_OF]-(b:Entity)
    WHERE r.confidence > 0.8
    RETURN b.primary_name, r.confidence
    ORDER BY r.confidence DESC
""")

# Community detection
communities = await em.graph.detect_communities(algorithm="louvain")
```

### Entity Extraction

```python
from entity_master.extractors import LLMEntityExtractor

extractor = LLMEntityExtractor(model="gpt-4o")

# Extract entities from filing text
text = "We rely on Taiwan Semiconductor Manufacturing Company (TSMC) for chip fabrication..."
entities, relationships = await extractor.extract(text, context_entity="AAPL")

# Returns:
# entities: [Entity(name="TSMC", type="company")]
# relationships: [Relationship(source="AAPL", target="TSMC", type="SUPPLIER_OF")]

# Auto-resolve and store
for entity in entities:
    resolved = await em.resolve_or_create(entity)
for rel in relationships:
    await em.graph.add_relationship(rel)
```

---

## Tier 5: Mind-blowing

**Storage**: Full stack + Vector DB + LLM
**Best for**: Research, AI applications, knowledge graphs

### Additional Features
- ✅ Vector embeddings (OpenAI, sentence-transformers)
- ✅ Semantic search ("companies similar to Apple")
- ✅ LLM-powered enrichment
- ✅ Knowledge graph reasoning
- ✅ Real-time streaming updates
- ✅ gRPC for high-performance
- ✅ Distributed deployment
- ✅ Auto-learning from filings

### Vector Database Integration

```python
em = EntityMaster(
    tier="mind-blowing",
    vector_db="chromadb",  # or "pinecone", "weaviate", "qdrant"
    embedding_model="text-embedding-3-small",
)

# Semantic search
similar = await em.semantic_search(
    "semiconductor chip manufacturers",
    top_k=10
)
# Returns: TSMC, Intel, Samsung, GlobalFoundries, ...

# Find companies similar to Apple
similar_to_apple = await em.find_similar("AAPL", top_k=20)
# Uses entity embeddings based on filings, news, relationships

# Embed entity descriptions
await em.generate_embeddings()
```

### LLM Integration

```python
from entity_master.llm import EntityMasterLLM

llm = EntityMasterLLM(em, model="gpt-4o")

# Natural language queries
result = await llm.query(
    "Who are Apple's main chip suppliers and what is their relationship with ASML?"
)

# Auto-extraction from any text
entities = await llm.extract_entities(news_article_text)

# Relationship inference
inferred = await llm.infer_relationships("NVDA", "AMD")
# Returns: Likely competitors based on filings, news, market data
```

### Real-time Streaming

```python
import asyncio
from entity_master.streaming import EntityStream

async with EntityStream(em) as stream:
    # Subscribe to entity changes
    async for event in stream.subscribe(entity_types=["company"]):
        if event.type == "new_ticker":
            print(f"New listing: {event.entity.ticker}")
        elif event.type == "relationship_added":
            print(f"New relationship: {event.relationship}")
        elif event.type == "delisting":
            print(f"Delisted: {event.entity.ticker}")
```

### Knowledge Graph Reasoning

```python
# Complex inference queries
result = await em.knowledge_graph.query("""
    Find all companies that:
    1. Supply to Apple
    2. Are headquartered in Taiwan
    3. Have been mentioned in NVIDIA's filings
    4. Have a market cap > $100B
""")

# Causal analysis
impact = await em.knowledge_graph.analyze_impact(
    event="TSMC capacity expansion",
    affected_entity="AAPL"
)
```

---

## Migration Between Tiers

```python
from entity_master import EntityMaster
from entity_master.migration import migrate

# Upgrade from Tier 1 to Tier 2
em_basic = EntityMaster(tier="basic", db_path="entities.db")
em_intermediate = EntityMaster(tier="intermediate", db_path="entities.duckdb")

await migrate(source=em_basic, target=em_intermediate)

# Upgrade from Tier 2 to Tier 3
em_advanced = EntityMaster(
    tier="advanced",
    postgres_url="postgresql://...",
    elasticsearch_url="http://localhost:9200",
)

await migrate(source=em_intermediate, target=em_advanced)
```

---

## Configuration

```yaml
# entity_master.yaml
tier: intermediate

# Storage (tier-dependent)
storage:
  sqlite:
    path: ~/.entity_master/entities.db
  duckdb:
    path: ~/.entity_master/entities.duckdb
  postgres:
    url: postgresql://user:pass@localhost/entity_master
  neo4j:
    uri: bolt://localhost:7687
    user: neo4j
    password: secret

# Search
search:
  elasticsearch:
    url: http://localhost:9200
    index: entities

# Enrichment
enrichment:
  gleif:
    enabled: true
    rate_limit: 60  # requests per minute
  openfigi:
    enabled: true
    api_key: ${OPENFIGI_API_KEY}

# FeedSpine
feedspine:
  feeds:
    - sec_tickers
    - gleif_lei
  schedule:
    sec_tickers: "0 6 * * *"  # Daily
    gleif_lei: "0 0 1 * *"    # Monthly

# LLM (Tier 5)
llm:
  provider: openai
  model: gpt-4o
  embedding_model: text-embedding-3-small
```
