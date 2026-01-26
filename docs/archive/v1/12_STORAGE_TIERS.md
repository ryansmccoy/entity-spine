# Entity Master - Storage Tiers

**Staged storage implementations from minimal SQLite to full PostgreSQL + Graph.**

---

## Tier Overview

Each tier adds capabilities while maintaining backward compatibility:

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              STORAGE TIER PROGRESSION                                │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  TIER 1: BASIC              TIER 2: INTERMEDIATE         TIER 3: ADVANCED           │
│  ─────────────              ──────────────────           ───────────────            │
│  SQLite                     DuckDB                       PostgreSQL                  │
│                                                                                      │
│  • Single file              • Analytics engine           • Full ACID                 │
│  • Exact lookups            • Full-text search           • Point-in-time queries    │
│  • No history               • Alias matching             • Complete history          │
│  • Manual updates           • Scheduled updates          • Real-time feeds           │
│  • ~10K entities            • ~100K entities             • Millions of entities      │
│                                                                                      │
│  Use: Personal              Use: Small team              Use: Production             │
│                                                                                      │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  TIER 4: FULL               TIER 5: MIND-BLOWING                                     │
│  ───────────                ─────────────────                                        │
│  + Elasticsearch            + LLM Enrichment                                         │
│  + Neo4j                    + Vector Search                                          │
│                             + Real-time Streaming                                    │
│  • Fuzzy search             • Semantic resolution                                    │
│  • Graph traversal          • AI entity extraction                                   │
│  • Supply chain queries     • Knowledge graph                                        │
│                                                                                      │
│  Use: Enterprise            Use: Research                                            │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Tier 1: Basic (SQLite)

**Storage:** Single SQLite file
**Best for:** Personal projects, offline use, prototyping
**Scale:** ~10,000 entities

### Schema

```sql
-- =============================================================================
-- TIER 1: MINIMAL SCHEMA (SQLite)
-- =============================================================================
-- Single-file database with exact-match lookups only.
-- No history, no full-text search, no relationships.

-- Core entity table (simplified)
CREATE TABLE entities (
    entity_id       TEXT PRIMARY KEY,    -- ULID
    entity_type     TEXT NOT NULL,       -- 'COMPANY', 'FUND', etc.
    legal_name      TEXT NOT NULL,
    primary_name    TEXT,
    status          TEXT DEFAULT 'active',
    cik             TEXT,                -- Denormalized for fast lookup
    lei             TEXT,
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now'))
);

CREATE INDEX idx_entities_cik ON entities(cik) WHERE cik IS NOT NULL;
CREATE INDEX idx_entities_lei ON entities(lei) WHERE lei IS NOT NULL;
CREATE INDEX idx_entities_name ON entities(legal_name);

-- Securities (simplified)
CREATE TABLE securities (
    security_id         TEXT PRIMARY KEY,
    issuer_entity_id    TEXT NOT NULL REFERENCES entities(entity_id),
    security_type       TEXT NOT NULL,
    name                TEXT NOT NULL,
    share_class         TEXT,
    isin                TEXT,           -- Denormalized
    cusip               TEXT,           -- Denormalized
    figi                TEXT,           -- Denormalized
    status              TEXT DEFAULT 'active',
    created_at          TEXT DEFAULT (datetime('now'))
);

CREATE INDEX idx_securities_isin ON securities(isin) WHERE isin IS NOT NULL;
CREATE INDEX idx_securities_cusip ON securities(cusip) WHERE cusip IS NOT NULL;
CREATE INDEX idx_securities_figi ON securities(figi) WHERE figi IS NOT NULL;
CREATE INDEX idx_securities_issuer ON securities(issuer_entity_id);

-- Listings (simplified, no temporal)
CREATE TABLE listings (
    listing_id      TEXT PRIMARY KEY,
    security_id     TEXT NOT NULL REFERENCES securities(security_id),
    ticker          TEXT NOT NULL,
    mic             TEXT NOT NULL,      -- Market Identifier Code
    currency        TEXT,
    is_primary      INTEGER DEFAULT 0,
    status          TEXT DEFAULT 'active',
    created_at      TEXT DEFAULT (datetime('now')),
    UNIQUE(ticker, mic)
);

CREATE INDEX idx_listings_ticker ON listings(ticker);
CREATE INDEX idx_listings_ticker_mic ON listings(ticker, mic);
CREATE INDEX idx_listings_security ON listings(security_id);

-- Identifiers (all scopes in one table, simplified)
CREATE TABLE identifiers (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id       TEXT REFERENCES entities(entity_id),
    security_id     TEXT REFERENCES securities(security_id),
    listing_id      TEXT REFERENCES listings(listing_id),
    scheme          TEXT NOT NULL,
    value           TEXT NOT NULL,
    source          TEXT,
    created_at      TEXT DEFAULT (datetime('now')),
    UNIQUE(scheme, value)
);

CREATE INDEX idx_identifiers_lookup ON identifiers(scheme, value);

-- Simple aliases (no FTS)
CREATE TABLE aliases (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id       TEXT NOT NULL REFERENCES entities(entity_id),
    name            TEXT NOT NULL,
    alias_type      TEXT,
    source          TEXT
);

CREATE INDEX idx_aliases_name ON aliases(name);
CREATE INDEX idx_aliases_entity ON aliases(entity_id);
```

### Usage

```python
from entity_master import EntityMaster

# Initialize Tier 1
em = EntityMaster(
    tier='basic',
    db_path='~/.entity_master/entities.db',
)

# Load SEC data
await em.load_sec_tickers()  # Downloads company_tickers_exchange.json

# Exact lookups only
entity = em.resolve('AAPL')      # Ticker lookup
entity = em.resolve('320193')    # CIK lookup

# No fuzzy search in Tier 1
results = em.search('Apple')  # Uses LIKE '%Apple%' (slow, exact substring)
```

### Limitations

- ❌ No temporal tracking (can't query "GM as of 2008")
- ❌ No full-text search (substring matching only)
- ❌ No relationship graph
- ❌ No automatic enrichment
- ❌ Single-user (no concurrent writes)

---

## Tier 2: Intermediate (DuckDB)

**Storage:** DuckDB database
**Best for:** Small teams, analytics, data exploration
**Scale:** ~100,000 entities

### Schema Additions

```sql
-- =============================================================================
-- TIER 2: ADDITIONS (DuckDB)
-- =============================================================================
-- Adds: Full-text search, sightings tracking, basic history, analytics.

-- Add temporal columns to listings
ALTER TABLE listings ADD COLUMN valid_from DATE;
ALTER TABLE listings ADD COLUMN valid_to DATE;

-- Add confidence to identifiers
ALTER TABLE identifiers ADD COLUMN confidence DECIMAL(3,2) DEFAULT 1.0;
ALTER TABLE identifiers ADD COLUMN first_seen_at TIMESTAMP;
ALTER TABLE identifiers ADD COLUMN last_seen_at TIMESTAMP;

-- Sightings table (track when records were seen)
CREATE TABLE sightings (
    id              INTEGER PRIMARY KEY,
    entity_id       TEXT REFERENCES entities(entity_id),
    security_id     TEXT REFERENCES securities(security_id),
    listing_id      TEXT REFERENCES listings(listing_id),
    feed_id         TEXT NOT NULL,       -- 'sec-tickers', 'gleif', etc.
    capture_date    DATE NOT NULL,
    record_hash     TEXT,                -- For change detection
    UNIQUE(entity_id, feed_id, capture_date),
    UNIQUE(security_id, feed_id, capture_date),
    UNIQUE(listing_id, feed_id, capture_date)
);

-- Entity history (track changes)
CREATE TABLE entity_history (
    id              INTEGER PRIMARY KEY,
    entity_id       TEXT NOT NULL,
    field_name      TEXT NOT NULL,
    old_value       TEXT,
    new_value       TEXT,
    changed_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    change_source   TEXT
);

CREATE INDEX idx_history_entity ON entity_history(entity_id);

-- Full-text search index (DuckDB FTS extension)
INSTALL fts;
LOAD fts;

-- Create FTS index on aliases
PRAGMA create_fts_index('aliases', 'name', stemmer='porter', lower=true);
```

### Full-Text Search

```python
# DuckDB FTS queries
async def search_fts(query: str, limit: int = 10) -> list[Entity]:
    """Full-text search on entity names."""
    
    results = await db.fetch_all(
        """
        SELECT a.entity_id, a.name, fts_main_aliases.match_bm25(a.id, ?) AS score
        FROM aliases a
        WHERE score IS NOT NULL
        ORDER BY score DESC
        LIMIT ?
        """,
        (query, limit),
    )
    
    entities = []
    for row in results:
        entity = await get_entity(row['entity_id'])
        entities.append(entity)
    
    return entities
```

### Analytics Queries

```python
# DuckDB enables fast analytics
em = EntityMaster(tier='intermediate')

# Companies by exchange
df = em.analytics.query("""
    SELECT l.mic AS exchange, COUNT(DISTINCT e.entity_id) AS companies
    FROM listings l
    JOIN securities s ON s.security_id = l.security_id
    JOIN entities e ON e.entity_id = s.issuer_entity_id
    WHERE l.status = 'active'
    GROUP BY l.mic
    ORDER BY companies DESC
""")

# New entities this week
new = em.analytics.query("""
    SELECT e.entity_id, e.legal_name, MIN(s.capture_date) AS first_seen
    FROM entities e
    JOIN sightings s ON s.entity_id = e.entity_id
    GROUP BY e.entity_id, e.legal_name
    HAVING MIN(s.capture_date) >= CURRENT_DATE - INTERVAL 7 DAY
""")

# Export to Parquet for external analysis
em.export_parquet('entities.parquet', table='entities')
```

### Change Detection

```python
# Track what's new/changed using sightings
async def detect_changes(feed_id: str, since: date) -> ChangeReport:
    """Detect entities that appeared/disappeared in a feed."""
    
    # New entities (first seen after date)
    new = await db.fetch_all(
        """
        SELECT entity_id, MIN(capture_date) AS first_seen
        FROM sightings
        WHERE feed_id = :feed_id
        GROUP BY entity_id
        HAVING MIN(capture_date) > :since
        """,
        {'feed_id': feed_id, 'since': since},
    )
    
    # Missing entities (last seen before date, not seen since)
    missing = await db.fetch_all(
        """
        WITH latest AS (
            SELECT entity_id, MAX(capture_date) AS last_seen
            FROM sightings
            WHERE feed_id = :feed_id
            GROUP BY entity_id
        )
        SELECT entity_id, last_seen
        FROM latest
        WHERE last_seen < :since
          AND entity_id NOT IN (
              SELECT entity_id FROM sightings 
              WHERE feed_id = :feed_id AND capture_date >= :since
          )
        """,
        {'feed_id': feed_id, 'since': since},
    )
    
    return ChangeReport(new_entities=new, missing_entities=missing)
```

---

## Tier 3: Advanced (PostgreSQL)

**Storage:** PostgreSQL
**Best for:** Production deployments, multi-user, full history
**Scale:** Millions of entities

### Full Schema

```sql
-- =============================================================================
-- TIER 3: FULL POSTGRESQL SCHEMA
-- =============================================================================
-- Complete Entity/Security/Listing model with temporal tracking.

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- Fuzzy matching
CREATE EXTENSION IF NOT EXISTS "btree_gin"; -- Combined indexes

-- =============================================================================
-- ENTITIES
-- =============================================================================

CREATE TABLE entities (
    entity_id           CHAR(26) PRIMARY KEY,  -- ULID
    entity_type         VARCHAR(30) NOT NULL,
    entity_subtype      VARCHAR(50),
    legal_name          VARCHAR(500) NOT NULL,
    primary_name        VARCHAR(500),
    jurisdiction_country VARCHAR(2),
    jurisdiction_state   VARCHAR(10),
    sic_code            VARCHAR(4),
    sic_description     VARCHAR(200),
    fiscal_year_end     VARCHAR(4),
    status              VARCHAR(20) NOT NULL DEFAULT 'active',
    inactive_reason     VARCHAR(100),
    successor_entity_id CHAR(26) REFERENCES entities(entity_id),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by          VARCHAR(100),
    
    CONSTRAINT chk_entity_type CHECK (entity_type IN (
        'COMPANY', 'FUND', 'FUND_SPONSOR', 'PERSON', 'GOVERNMENT',
        'EXCHANGE', 'INDEX_PROVIDER', 'PRIVATE_COMPANY', 'SUBSIDIARY', 'SPECIAL_PURPOSE'
    ))
);

CREATE INDEX idx_entities_type ON entities(entity_type);
CREATE INDEX idx_entities_status ON entities(status);
CREATE INDEX idx_entities_name_trgm ON entities USING gin(legal_name gin_trgm_ops);

-- =============================================================================
-- SECURITIES
-- =============================================================================

CREATE TABLE securities (
    security_id         CHAR(26) PRIMARY KEY,
    issuer_entity_id    CHAR(26) NOT NULL REFERENCES entities(entity_id),
    security_type       VARCHAR(30) NOT NULL,
    security_subtype    VARCHAR(50),
    name                VARCHAR(500) NOT NULL,
    description         TEXT,
    share_class         VARCHAR(50),
    voting_rights       VARCHAR(50),
    coupon_rate         DECIMAL(8,5),
    maturity_date       DATE,
    par_value           DECIMAL(18,4),
    fund_type           VARCHAR(50),
    share_class_name    VARCHAR(50),
    primary_currency    VARCHAR(3),
    status              VARCHAR(20) NOT NULL DEFAULT 'active',
    issue_date          DATE,
    termination_date    DATE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT chk_security_type CHECK (security_type IN (
        'COMMON_STOCK', 'PREFERRED_STOCK', 'WARRANT', 'RIGHTS',
        'CONVERTIBLE_BOND', 'CORPORATE_BOND', 'GOVERNMENT_BOND', 'MUNICIPAL_BOND',
        'ETF', 'MUTUAL_FUND', 'CLOSED_END_FUND', 'UNIT', 'ADR', 'GDR', 'OPTION', 'FUTURE', 'OTHER'
    ))
);

CREATE INDEX idx_securities_issuer ON securities(issuer_entity_id);
CREATE INDEX idx_securities_type ON securities(security_type);

-- =============================================================================
-- LISTINGS (with temporal validity)
-- =============================================================================

CREATE TABLE listings (
    listing_id          CHAR(26) PRIMARY KEY,
    security_id         CHAR(26) NOT NULL REFERENCES securities(security_id),
    ticker              VARCHAR(20) NOT NULL,
    mic                 VARCHAR(4) NOT NULL,
    currency            VARCHAR(3) NOT NULL,
    exchange_name       VARCHAR(100),
    country             VARCHAR(2),
    listing_type        VARCHAR(30),
    is_primary          BOOLEAN DEFAULT false,
    status              VARCHAR(20) NOT NULL DEFAULT 'active',
    valid_from          DATE NOT NULL,
    valid_to            DATE,
    delist_reason       VARCHAR(100),
    successor_listing_id CHAR(26) REFERENCES listings(listing_id),
    lot_size            INT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Unique: same ticker+MIC can exist in different time periods
    CONSTRAINT uq_listing_ticker_mic_period UNIQUE (ticker, mic, valid_from)
);

CREATE INDEX idx_listings_ticker ON listings(ticker);
CREATE INDEX idx_listings_ticker_mic ON listings(ticker, mic);
CREATE INDEX idx_listings_security ON listings(security_id);
CREATE INDEX idx_listings_active ON listings(ticker, mic) 
    WHERE status = 'active' AND valid_to IS NULL;

-- Point-in-time lookup function
CREATE OR REPLACE FUNCTION get_listing_at(
    p_ticker VARCHAR,
    p_mic VARCHAR,
    p_date DATE DEFAULT CURRENT_DATE
) RETURNS TABLE (
    listing_id CHAR(26),
    security_id CHAR(26),
    ticker VARCHAR(20),
    mic VARCHAR(4)
) AS $$
BEGIN
    RETURN QUERY
    SELECT l.listing_id, l.security_id, l.ticker, l.mic
    FROM listings l
    WHERE l.ticker = p_ticker
      AND l.mic = p_mic
      AND l.valid_from <= p_date
      AND (l.valid_to IS NULL OR l.valid_to > p_date);
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- IDENTIFIERS (scoped)
-- =============================================================================

CREATE TABLE identifiers (
    identifier_id       CHAR(26) PRIMARY KEY,
    entity_id           CHAR(26) REFERENCES entities(entity_id),
    security_id         CHAR(26) REFERENCES securities(security_id),
    listing_id          CHAR(26) REFERENCES listings(listing_id),
    scheme              VARCHAR(30) NOT NULL,
    value               VARCHAR(100) NOT NULL,
    vendor              VARCHAR(30),
    vendor_id_type      VARCHAR(50),
    source              VARCHAR(50) NOT NULL,
    source_id           VARCHAR(200),
    confidence          DECIMAL(3,2) DEFAULT 1.0,
    is_primary          BOOLEAN DEFAULT false,
    is_verified         BOOLEAN DEFAULT false,
    valid_from          DATE,
    valid_to            DATE,
    first_seen_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    capture_date        DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Exactly one scope must be set
    CONSTRAINT chk_identifier_scope CHECK (
        (entity_id IS NOT NULL)::int +
        (security_id IS NOT NULL)::int +
        (listing_id IS NOT NULL)::int = 1
    )
);

CREATE INDEX idx_identifiers_scheme_value ON identifiers(scheme, value);
CREATE INDEX idx_identifiers_entity ON identifiers(entity_id) WHERE entity_id IS NOT NULL;
CREATE INDEX idx_identifiers_security ON identifiers(security_id) WHERE security_id IS NOT NULL;
CREATE INDEX idx_identifiers_listing ON identifiers(listing_id) WHERE listing_id IS NOT NULL;
CREATE INDEX idx_identifiers_current ON identifiers(scheme, value) WHERE valid_to IS NULL;

-- =============================================================================
-- ALIASES (with FTS)
-- =============================================================================

CREATE TABLE entity_aliases (
    alias_id            CHAR(26) PRIMARY KEY,
    entity_id           CHAR(26) NOT NULL REFERENCES entities(entity_id),
    name                VARCHAR(500) NOT NULL,
    name_normalized     VARCHAR(500),
    alias_type          VARCHAR(30) NOT NULL,
    source              VARCHAR(50) NOT NULL,
    source_id           VARCHAR(200),
    valid_from          DATE,
    valid_to            DATE,
    is_primary          BOOLEAN DEFAULT false,
    priority            INT DEFAULT 0,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_aliases_name ON entity_aliases(name_normalized);
CREATE INDEX idx_aliases_name_trgm ON entity_aliases USING gin(name gin_trgm_ops);
CREATE INDEX idx_aliases_entity ON entity_aliases(entity_id);

-- Full-text search
CREATE INDEX idx_aliases_fts ON entity_aliases 
    USING gin(to_tsvector('english', name));

-- =============================================================================
-- CORPORATE HIERARCHY
-- =============================================================================

CREATE TABLE corporate_hierarchy (
    hierarchy_id        CHAR(26) PRIMARY KEY,
    parent_entity_id    CHAR(26) NOT NULL REFERENCES entities(entity_id),
    child_entity_id     CHAR(26) NOT NULL REFERENCES entities(entity_id),
    relationship_type   VARCHAR(30) NOT NULL,
    ownership_pct       DECIMAL(6,3),
    ownership_type      VARCHAR(30),
    voting_pct          DECIMAL(6,3),
    effective_date      DATE,
    end_date            DATE,
    source              VARCHAR(50) NOT NULL,
    source_id           VARCHAR(200),
    evidence_text       TEXT,
    confidence          DECIMAL(3,2) DEFAULT 1.0,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT chk_no_self_ref CHECK (parent_entity_id != child_entity_id)
);

CREATE INDEX idx_hierarchy_parent ON corporate_hierarchy(parent_entity_id);
CREATE INDEX idx_hierarchy_child ON corporate_hierarchy(child_entity_id);
CREATE INDEX idx_hierarchy_active ON corporate_hierarchy(parent_entity_id, child_entity_id) 
    WHERE end_date IS NULL;

-- =============================================================================
-- ENTITY MERGES
-- =============================================================================

CREATE TABLE entity_merges (
    merge_id            CHAR(26) PRIMARY KEY,
    from_entity_id      CHAR(26) NOT NULL,
    to_entity_id        CHAR(26) NOT NULL REFERENCES entities(entity_id),
    merge_type          VARCHAR(30) NOT NULL,
    reason              TEXT,
    merged_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    effective_date      DATE,
    source              VARCHAR(50) NOT NULL,
    source_id           VARCHAR(200),
    evidence_text       TEXT,
    approved_by         VARCHAR(100),
    approved_at         TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_merges_from ON entity_merges(from_entity_id);
CREATE INDEX idx_merges_to ON entity_merges(to_entity_id);

-- =============================================================================
-- AUDIT / HISTORY
-- =============================================================================

CREATE TABLE entity_changes (
    change_id           CHAR(26) PRIMARY KEY,
    entity_id           CHAR(26) NOT NULL,
    table_name          VARCHAR(50) NOT NULL,
    operation           VARCHAR(10) NOT NULL,  -- INSERT, UPDATE, DELETE
    old_values          JSONB,
    new_values          JSONB,
    changed_fields      TEXT[],
    changed_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    changed_by          VARCHAR(100),
    source              VARCHAR(50)
);

CREATE INDEX idx_changes_entity ON entity_changes(entity_id);
CREATE INDEX idx_changes_time ON entity_changes(changed_at);

-- Trigger for automatic history
CREATE OR REPLACE FUNCTION track_entity_changes()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'UPDATE' THEN
        INSERT INTO entity_changes (
            change_id, entity_id, table_name, operation,
            old_values, new_values, changed_fields
        ) VALUES (
            gen_random_uuid()::text,
            COALESCE(NEW.entity_id, OLD.entity_id),
            TG_TABLE_NAME,
            TG_OP,
            to_jsonb(OLD),
            to_jsonb(NEW),
            ARRAY(
                SELECT key 
                FROM jsonb_each(to_jsonb(NEW)) n
                FULL OUTER JOIN jsonb_each(to_jsonb(OLD)) o USING (key)
                WHERE n.value IS DISTINCT FROM o.value
            )
        );
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO entity_changes (
            change_id, entity_id, table_name, operation, old_values
        ) VALUES (
            gen_random_uuid()::text,
            OLD.entity_id,
            TG_TABLE_NAME,
            TG_OP,
            to_jsonb(OLD)
        );
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER entities_audit
    AFTER UPDATE OR DELETE ON entities
    FOR EACH ROW EXECUTE FUNCTION track_entity_changes();

-- =============================================================================
-- CROSSWALKS (Vendor ID mappings)
-- =============================================================================

CREATE TABLE crosswalks (
    crosswalk_id        CHAR(26) PRIMARY KEY,
    entity_id           CHAR(26) REFERENCES entities(entity_id),
    security_id         CHAR(26) REFERENCES securities(security_id),
    listing_id          CHAR(26) REFERENCES listings(listing_id),
    vendor              VARCHAR(30) NOT NULL,
    vendor_id_type      VARCHAR(50) NOT NULL,
    vendor_id_value     VARCHAR(200) NOT NULL,
    mapping_source      VARCHAR(50) NOT NULL,
    mapping_method      VARCHAR(30) NOT NULL,
    confidence          DECIMAL(3,2) DEFAULT 1.0,
    valid_from          DATE,
    valid_to            DATE,
    first_seen_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_verified_at    TIMESTAMPTZ,
    conflict_count      INT DEFAULT 0,
    conflict_notes      TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT chk_crosswalk_scope CHECK (
        (entity_id IS NOT NULL)::int +
        (security_id IS NOT NULL)::int +
        (listing_id IS NOT NULL)::int = 1
    )
);

CREATE INDEX idx_crosswalks_vendor ON crosswalks(vendor, vendor_id_type, vendor_id_value);
CREATE INDEX idx_crosswalks_entity ON crosswalks(entity_id) WHERE entity_id IS NOT NULL;

-- =============================================================================
-- RESOLUTION QUEUE (for manual review)
-- =============================================================================

CREATE TABLE resolution_queue (
    queue_id            CHAR(26) PRIMARY KEY,
    input_identifier    VARCHAR(500) NOT NULL,
    input_type          VARCHAR(30),
    context             JSONB,
    candidate_ids       CHAR(26)[],
    candidate_scores    DECIMAL(3,2)[],
    status              VARCHAR(20) DEFAULT 'pending',
    resolved_id         CHAR(26),
    resolution_method   VARCHAR(30),
    resolution_notes    TEXT,
    resolved_by         VARCHAR(100),
    resolved_at         TIMESTAMPTZ,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    source_system       VARCHAR(50),
    priority            INT DEFAULT 0
);

CREATE INDEX idx_queue_pending ON resolution_queue(priority DESC, created_at)
    WHERE status = 'pending';
```

### Connection Pooling

```python
# Use asyncpg with connection pooling
import asyncpg

class PostgresBackend:
    def __init__(self, dsn: str):
        self.dsn = dsn
        self.pool: asyncpg.Pool = None
    
    async def connect(self):
        self.pool = await asyncpg.create_pool(
            self.dsn,
            min_size=5,
            max_size=20,
            command_timeout=60,
        )
    
    async def resolve(self, identifier: str) -> Entity | None:
        async with self.pool.acquire() as conn:
            # Use prepared statements for performance
            row = await conn.fetchrow(
                """
                SELECT e.*, i.scheme, i.value
                FROM entities e
                JOIN identifiers i ON i.entity_id = e.entity_id
                WHERE i.scheme = $1 AND i.value = $2
                """,
                detect_scheme(identifier),
                identifier,
            )
            return Entity(**row) if row else None
```

---

## Tier 4: Full (+ Elasticsearch + Neo4j)

**Storage:** PostgreSQL + Elasticsearch + Neo4j
**Best for:** Enterprise, supply chain analysis, complex queries
**Scale:** Tens of millions of entities

### Elasticsearch for Search

```python
# Elasticsearch index mapping
ENTITY_INDEX_MAPPING = {
    "mappings": {
        "properties": {
            "entity_id": {"type": "keyword"},
            "entity_type": {"type": "keyword"},
            "legal_name": {
                "type": "text",
                "analyzer": "english",
                "fields": {
                    "keyword": {"type": "keyword"},
                    "autocomplete": {
                        "type": "text",
                        "analyzer": "autocomplete"
                    }
                }
            },
            "aliases": {
                "type": "text",
                "analyzer": "english"
            },
            "identifiers": {
                "type": "nested",
                "properties": {
                    "scheme": {"type": "keyword"},
                    "value": {"type": "keyword"}
                }
            },
            "cik": {"type": "keyword"},
            "lei": {"type": "keyword"},
            "ticker": {"type": "keyword"},
            "status": {"type": "keyword"},
            "sic_code": {"type": "keyword"},
            "jurisdiction_country": {"type": "keyword"},
            "created_at": {"type": "date"}
        }
    },
    "settings": {
        "analysis": {
            "analyzer": {
                "autocomplete": {
                    "type": "custom",
                    "tokenizer": "autocomplete_tokenizer",
                    "filter": ["lowercase"]
                }
            },
            "tokenizer": {
                "autocomplete_tokenizer": {
                    "type": "edge_ngram",
                    "min_gram": 2,
                    "max_gram": 20,
                    "token_chars": ["letter", "digit"]
                }
            }
        }
    }
}


class ElasticsearchBackend:
    async def search(
        self,
        query: str,
        entity_type: str = None,
        limit: int = 10,
    ) -> list[Entity]:
        """Fuzzy search with Elasticsearch."""
        
        must = [
            {
                "multi_match": {
                    "query": query,
                    "fields": ["legal_name^3", "aliases^2", "ticker^2"],
                    "type": "best_fields",
                    "fuzziness": "AUTO"
                }
            }
        ]
        
        if entity_type:
            must.append({"term": {"entity_type": entity_type}})
        
        result = await self.es.search(
            index="entities",
            body={
                "query": {"bool": {"must": must}},
                "size": limit
            }
        )
        
        return [Entity(**hit["_source"]) for hit in result["hits"]["hits"]]
```

### Neo4j for Graphs

```cypher
-- Neo4j schema for relationship queries

// Entity nodes
CREATE CONSTRAINT entity_id IF NOT EXISTS
FOR (e:Entity) REQUIRE e.entity_id IS UNIQUE;

CREATE (e:Entity {
    entity_id: $entity_id,
    legal_name: $legal_name,
    entity_type: $entity_type,
    cik: $cik,
    lei: $lei,
    status: $status
})

// Security nodes
CREATE (s:Security {
    security_id: $security_id,
    name: $name,
    security_type: $security_type,
    isin: $isin,
    figi: $figi
})

// Relationships
CREATE (e:Entity)-[:ISSUES]->(s:Security)

// Corporate hierarchy
CREATE (parent:Entity)-[:PARENT_OF {
    ownership_pct: $ownership_pct,
    effective_date: date($effective_date),
    source: $source
}]->(child:Entity)

// Example: Get full corporate hierarchy
MATCH path = (ultimate:Entity)-[:PARENT_OF*0..5]->(subsidiary:Entity)
WHERE ultimate.entity_id = $entity_id
RETURN path

// Example: Supply chain traversal
MATCH path = (company:Entity)-[:SUPPLIES_TO|BUYS_FROM*1..3]-(related:Entity)
WHERE company.entity_id = $entity_id
RETURN path
```

### Sync Between Stores

```python
class MultiBackendEntityMaster:
    """Entity Master with PostgreSQL + Elasticsearch + Neo4j."""
    
    def __init__(self):
        self.pg = PostgresBackend()
        self.es = ElasticsearchBackend()
        self.neo4j = Neo4jBackend()
    
    async def add_entity(self, entity: Entity):
        """Add entity to all stores."""
        
        # PostgreSQL is source of truth
        await self.pg.insert_entity(entity)
        
        # Sync to Elasticsearch for search
        await self.es.index_entity(entity)
        
        # Sync to Neo4j for graph queries
        await self.neo4j.create_entity_node(entity)
    
    async def resolve(self, identifier: str) -> Entity | None:
        """Resolve from PostgreSQL (source of truth)."""
        return await self.pg.resolve(identifier)
    
    async def search(self, query: str, **kwargs) -> list[Entity]:
        """Search via Elasticsearch."""
        return await self.es.search(query, **kwargs)
    
    async def get_corporate_tree(self, entity_id: str) -> dict:
        """Get corporate hierarchy from Neo4j."""
        return await self.neo4j.get_hierarchy(entity_id)
    
    async def sync_all(self):
        """Full sync from PostgreSQL to secondary stores."""
        
        async for entity in self.pg.stream_all_entities():
            await self.es.index_entity(entity)
            await self.neo4j.create_entity_node(entity)
        
        async for hierarchy in self.pg.stream_all_hierarchies():
            await self.neo4j.create_hierarchy_edge(hierarchy)
```

---

## Tier Selection Guide

| Factor | Tier 1 | Tier 2 | Tier 3 | Tier 4 |
|--------|--------|--------|--------|--------|
| **Entity count** | <10K | <100K | <10M | Unlimited |
| **Users** | 1 | <10 | <100 | Unlimited |
| **Search type** | Exact | FTS | FTS + fuzzy | Semantic |
| **History** | None | Basic | Full audit | Full + graph |
| **Deployment** | Local file | Local file | Server | Cluster |
| **Cost** | Free | Free | $50-500/mo | $500+/mo |
| **Setup time** | 5 min | 10 min | 1 hour | 1 day |

### Upgrade Path

```python
# Tier upgrades are non-breaking
em = EntityMaster(tier='basic')

# Later, upgrade to intermediate
em.upgrade_to('intermediate')  # Adds FTS, sightings

# Later, upgrade to advanced
em.upgrade_to('advanced', pg_dsn='postgresql://...')  # Migrates data

# Each upgrade preserves existing data and adds new capabilities
```

---

## Next Document

- [13_PYSECEDGAR_PORT.md](13_PYSECEDGAR_PORT.md) - py-sec-edgar integration
