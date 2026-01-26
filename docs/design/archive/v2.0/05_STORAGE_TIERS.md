# Entity Master v2 - Storage Tiers

**Progression from single-file SQLite to distributed PostgreSQL + Elasticsearch + Neo4j**

---

## Tier Overview

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              STORAGE TIER PROGRESSION                                    │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                          │
│  TIER 1              TIER 2              TIER 3              TIER 4/5                   │
│  ──────              ──────              ──────              ───────                    │
│                                                                                          │
│  SQLite              DuckDB              PostgreSQL          PostgreSQL (SoT)            │
│  Single file         Analytics           Full canonical      + Elasticsearch            │
│  <100K entities      OLAP queries        + pgvector          + Neo4j (graphs)           │
│                                                                                          │
│  ────────────────────────────────────────────────────────────────────────────────────── │
│       │                  │                    │                    │                    │
│       │    local dev     │   analytics        │   production       │   search/graphs    │
│       │    prototyping   │   batch reports    │   master data      │   traversal        │
│       │                  │                    │                    │                    │
│  ────────────────────────────────────────────────────────────────────────────────────── │
│       ▼                  ▼                    ▼                    ▼                    │
│                                                                                          │
│  Use case:           Use case:            Use case:            Use case:                │
│  - CLI tools         - Filing analytics   - Source of truth    - Full-text search       │
│  - Single user       - Large batch joins  - Multi-user access  - Graph queries          │
│  - Offline work      - Columnar agg       - ACID transactions  - Name similarity        │
│  - Quick start       - Read-heavy         - Conflict handling  - Relationship paths     │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Tier 1: SQLite

### When to Use

- Local development and prototyping
- Single-user CLI tools (`py-sec-edgar`)
- Offline/disconnected operation
- < 100,000 entities
- Read-heavy, occasional writes

### Schema (Simplified)

```sql
-- SQLite version: Simplified schema, no triggers/constraints
-- See 01_CANONICAL_DATA_MODEL.md for full schema

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

-- Core tables
CREATE TABLE entities (
    entity_id       TEXT PRIMARY KEY,
    primary_name    TEXT NOT NULL,
    entity_type     TEXT DEFAULT 'organization',
    status          TEXT DEFAULT 'active',
    jurisdiction    TEXT,
    incorporation_date TEXT,
    first_seen_at   TEXT,
    last_seen_at    TEXT,
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE securities (
    security_id     TEXT PRIMARY KEY,
    issuer_entity_id TEXT NOT NULL,
    name            TEXT NOT NULL,
    security_type   TEXT,
    asset_class     TEXT,
    status          TEXT DEFAULT 'active',
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (issuer_entity_id) REFERENCES entities(entity_id)
);

CREATE TABLE listings (
    listing_id      TEXT PRIMARY KEY,
    security_id     TEXT NOT NULL,
    mic             TEXT NOT NULL,
    ticker          TEXT NOT NULL,
    currency        TEXT,
    status          TEXT DEFAULT 'active',
    valid_from      TEXT,
    valid_to        TEXT,
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (security_id) REFERENCES securities(security_id)
);

CREATE TABLE identifiers (
    identifier_id   TEXT PRIMARY KEY,
    entity_id       TEXT,
    security_id     TEXT,
    listing_id      TEXT,
    scheme          TEXT NOT NULL,
    value           TEXT NOT NULL,
    valid_from      TEXT,
    valid_to        TEXT,
    created_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE crosswalks (
    crosswalk_id    TEXT PRIMARY KEY,
    entity_id       TEXT,
    security_id     TEXT,
    listing_id      TEXT,
    vendor          TEXT NOT NULL,
    vendor_id_type  TEXT NOT NULL,
    vendor_id_value TEXT NOT NULL,
    mapping_source  TEXT,
    confidence      REAL DEFAULT 0.95,
    created_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE entity_aliases (
    alias_id        TEXT PRIMARY KEY,
    entity_id       TEXT NOT NULL,
    alias_name      TEXT NOT NULL,
    name_normalized TEXT NOT NULL,
    alias_type      TEXT DEFAULT 'alternate',
    created_at      TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (entity_id) REFERENCES entities(entity_id)
);

CREATE TABLE entity_merges (
    merge_id        TEXT PRIMARY KEY,
    from_entity_id  TEXT NOT NULL,
    to_entity_id    TEXT NOT NULL,
    merge_type      TEXT,
    reason          TEXT,
    merged_at       TEXT DEFAULT (datetime('now'))
);

CREATE TABLE mentions (
    mention_id      TEXT PRIMARY KEY,
    filing_id       TEXT NOT NULL,
    raw_text        TEXT NOT NULL,
    normalized_name TEXT NOT NULL,
    resolved_entity_id TEXT,
    resolution_status TEXT DEFAULT 'pending',
    created_at      TEXT DEFAULT (datetime('now'))
);

-- Indexes
CREATE INDEX idx_entities_name ON entities(primary_name);
CREATE INDEX idx_entities_status ON entities(status);
CREATE INDEX idx_securities_issuer ON securities(issuer_entity_id);
CREATE INDEX idx_listings_security ON listings(security_id);
CREATE INDEX idx_listings_ticker ON listings(ticker);
CREATE INDEX idx_listings_mic_ticker ON listings(mic, ticker);
CREATE INDEX idx_identifiers_entity ON identifiers(entity_id);
CREATE INDEX idx_identifiers_security ON identifiers(security_id);
CREATE INDEX idx_identifiers_scheme_value ON identifiers(scheme, value);
CREATE INDEX idx_crosswalks_vendor ON crosswalks(vendor, vendor_id_type, vendor_id_value);
CREATE INDEX idx_aliases_normalized ON entity_aliases(name_normalized);
CREATE INDEX idx_merges_from ON entity_merges(from_entity_id);
CREATE INDEX idx_mentions_resolved ON mentions(resolved_entity_id);
```

### Python Adapter

```python
import sqlite3
from pathlib import Path
from typing import Optional, List, Dict
from contextlib import contextmanager


class SQLiteEntityStore:
    """SQLite storage adapter for Entity Master."""
    
    def __init__(self, db_path: str = "entity_master.db"):
        self.db_path = Path(db_path)
        self._init_db()
    
    def _init_db(self):
        """Initialize database with schema if needed."""
        if not self.db_path.exists():
            with self._connection() as conn:
                conn.executescript(SQLITE_SCHEMA)
    
    @contextmanager
    def _connection(self):
        """Get database connection with WAL mode."""
        conn = sqlite3.connect(
            self.db_path,
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    # =========================================================================
    # Entity Operations
    # =========================================================================
    
    def get_entity(self, entity_id: str) -> Optional[Dict]:
        """Get entity by ID."""
        with self._connection() as conn:
            row = conn.execute(
                "SELECT * FROM entities WHERE entity_id = ?",
                (entity_id,)
            ).fetchone()
            return dict(row) if row else None
    
    def get_entity_by_cik(self, cik: str) -> Optional[Dict]:
        """Get entity by CIK identifier."""
        cik_padded = cik.zfill(10)
        with self._connection() as conn:
            row = conn.execute("""
                SELECT e.* FROM entities e
                JOIN identifiers i ON i.entity_id = e.entity_id
                WHERE i.scheme = 'cik' AND i.value = ?
            """, (cik_padded,)).fetchone()
            return dict(row) if row else None
    
    def create_entity(self, entity: Dict) -> str:
        """Create new entity."""
        entity_id = entity.get('entity_id') or generate_ulid()
        
        with self._connection() as conn:
            conn.execute("""
                INSERT INTO entities (
                    entity_id, primary_name, entity_type, status,
                    jurisdiction, incorporation_date
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                entity_id,
                entity['primary_name'],
                entity.get('entity_type', 'organization'),
                entity.get('status', 'active'),
                entity.get('jurisdiction'),
                entity.get('incorporation_date'),
            ))
            
            # Create primary alias
            conn.execute("""
                INSERT INTO entity_aliases (
                    alias_id, entity_id, alias_name, name_normalized, alias_type
                ) VALUES (?, ?, ?, ?, 'primary')
            """, (
                generate_ulid(),
                entity_id,
                entity['primary_name'],
                normalize_company_name(entity['primary_name']),
            ))
        
        return entity_id
    
    def search_entities_by_name(
        self,
        name: str,
        limit: int = 10,
    ) -> List[Dict]:
        """Search entities by name (prefix match)."""
        normalized = normalize_company_name(name)
        
        with self._connection() as conn:
            rows = conn.execute("""
                SELECT DISTINCT e.* FROM entities e
                JOIN entity_aliases a ON a.entity_id = e.entity_id
                WHERE a.name_normalized LIKE ? || '%'
                   OR a.name_normalized LIKE '%' || ? || '%'
                ORDER BY 
                    CASE WHEN a.name_normalized = ? THEN 0 ELSE 1 END,
                    LENGTH(a.name_normalized)
                LIMIT ?
            """, (normalized, normalized, normalized, limit)).fetchall()
            return [dict(r) for r in rows]
    
    # =========================================================================
    # Resolution
    # =========================================================================
    
    def resolve_identifier(
        self,
        scheme: str,
        value: str,
    ) -> Optional[Dict]:
        """Resolve identifier to entity/security/listing."""
        
        with self._connection() as conn:
            row = conn.execute("""
                SELECT entity_id, security_id, listing_id, scheme, value
                FROM identifiers
                WHERE scheme = ? AND value = ?
            """, (scheme.lower(), value.upper())).fetchone()
            
            if not row:
                return None
            
            result = dict(row)
            
            # If we have entity_id, follow merges
            if result['entity_id']:
                canonical = self._follow_entity_merge(conn, result['entity_id'])
                result['canonical_entity_id'] = canonical
            
            return result
    
    def _follow_entity_merge(self, conn, entity_id: str) -> str:
        """Follow merge chain to canonical entity."""
        
        visited = set()
        current = entity_id
        
        while True:
            if current in visited:
                break  # Cycle detected
            visited.add(current)
            
            row = conn.execute("""
                SELECT to_entity_id FROM entity_merges
                WHERE from_entity_id = ?
            """, (current,)).fetchone()
            
            if row:
                current = row['to_entity_id']
            else:
                break
        
        return current
    
    # =========================================================================
    # Merge Operations
    # =========================================================================
    
    def merge_entities(
        self,
        from_entity_id: str,
        to_entity_id: str,
        merge_type: str,
        reason: str,
    ) -> str:
        """Record entity merge."""
        
        merge_id = generate_ulid()
        
        with self._connection() as conn:
            # Record merge
            conn.execute("""
                INSERT INTO entity_merges (
                    merge_id, from_entity_id, to_entity_id, merge_type, reason
                ) VALUES (?, ?, ?, ?, ?)
            """, (merge_id, from_entity_id, to_entity_id, merge_type, reason))
            
            # Update source entity status
            conn.execute("""
                UPDATE entities SET status = 'merged', updated_at = datetime('now')
                WHERE entity_id = ?
            """, (from_entity_id,))
            
            # Transfer aliases
            conn.execute("""
                UPDATE entity_aliases SET entity_id = ?, updated_at = datetime('now')
                WHERE entity_id = ?
            """, (to_entity_id, from_entity_id))
            
            # Transfer identifiers
            conn.execute("""
                UPDATE identifiers SET entity_id = ?
                WHERE entity_id = ?
            """, (to_entity_id, from_entity_id))
        
        return merge_id
    
    # =========================================================================
    # Export for Tier Transition
    # =========================================================================
    
    def export_to_duckdb(self, output_path: str):
        """Export entire database to DuckDB format."""
        import duckdb
        
        duck = duckdb.connect(output_path)
        
        # Attach SQLite as external database
        duck.execute(f"ATTACH '{self.db_path}' AS sqlite_db (TYPE sqlite)")
        
        # Copy each table
        for table in ['entities', 'securities', 'listings', 'identifiers', 
                      'crosswalks', 'entity_aliases', 'entity_merges', 'mentions']:
            duck.execute(f"""
                CREATE TABLE {table} AS 
                SELECT * FROM sqlite_db.{table}
            """)
        
        duck.close()
    
    def export_to_postgres(self, pg_conn_str: str):
        """Export to PostgreSQL using COPY."""
        import csv
        import tempfile
        import psycopg2
        
        with psycopg2.connect(pg_conn_str) as pg_conn:
            with self._connection() as sqlite_conn:
                for table in ['entities', 'securities', 'listings', 'identifiers']:
                    # Export to CSV
                    with tempfile.NamedTemporaryFile(
                        mode='w', suffix='.csv', delete=False
                    ) as f:
                        writer = csv.writer(f)
                        
                        rows = sqlite_conn.execute(f"SELECT * FROM {table}").fetchall()
                        if rows:
                            writer.writerow(rows[0].keys())
                            for row in rows:
                                writer.writerow(row)
                        
                        csv_path = f.name
                    
                    # Import to PostgreSQL
                    with pg_conn.cursor() as cur:
                        with open(csv_path, 'r') as f:
                            cur.copy_expert(
                                f"COPY {table} FROM STDIN WITH CSV HEADER",
                                f
                            )
                    
                    pg_conn.commit()
```

---

## Tier 2: DuckDB

### When to Use

- Analytics and reporting
- Large batch operations
- OLAP-style queries (aggregations, joins)
- Read-heavy, bulk writes
- 100K - 10M entities

### Benefits Over SQLite

- Columnar storage (faster aggregations)
- Parallel query execution
- Better compression
- Arrow integration (zero-copy to pandas/polars)
- Window functions optimized

### Schema Additions

```sql
-- DuckDB-specific optimizations

-- Partitioned tables for time-series data
CREATE TABLE filings_partitioned (
    filing_id       VARCHAR PRIMARY KEY,
    cik             VARCHAR(10),
    form_type       VARCHAR(20),
    filing_date     DATE,
    entity_id       VARCHAR,
    -- ... other fields
) PARTITION BY (YEAR(filing_date));

-- Materialized views for common queries
CREATE TABLE mv_entity_filing_counts AS
SELECT 
    e.entity_id,
    e.primary_name,
    COUNT(DISTINCT f.filing_id) as filing_count,
    COUNT(DISTINCT f.form_type) as form_type_count,
    MIN(f.filing_date) as first_filing,
    MAX(f.filing_date) as last_filing
FROM entities e
LEFT JOIN filings_partitioned f ON f.entity_id = e.entity_id
GROUP BY e.entity_id, e.primary_name;

-- Refresh materialized view
CREATE OR REPLACE MACRO refresh_entity_counts() AS TABLE
SELECT 
    e.entity_id,
    e.primary_name,
    COUNT(DISTINCT f.filing_id) as filing_count,
    COUNT(DISTINCT f.form_type) as form_type_count,
    MIN(f.filing_date) as first_filing,
    MAX(f.filing_date) as last_filing
FROM entities e
LEFT JOIN filings_partitioned f ON f.entity_id = e.entity_id
GROUP BY e.entity_id, e.primary_name;
```

### Python Adapter

```python
import duckdb
from typing import Optional, List, Dict
import polars as pl


class DuckDBEntityStore:
    """DuckDB storage adapter for analytics."""
    
    def __init__(self, db_path: str = "entity_master.duckdb"):
        self.db_path = db_path
        self.conn = duckdb.connect(db_path)
        self._init_extensions()
    
    def _init_extensions(self):
        """Load useful DuckDB extensions."""
        self.conn.execute("INSTALL 'fts'")
        self.conn.execute("LOAD 'fts'")
    
    # =========================================================================
    # Analytics Queries
    # =========================================================================
    
    def get_entity_with_filings(
        self,
        entity_id: str,
    ) -> Dict:
        """Get entity with filing statistics."""
        
        result = self.conn.execute("""
            SELECT 
                e.*,
                COUNT(DISTINCT f.filing_id) as filing_count,
                COUNT(DISTINCT f.form_type) as form_type_count,
                MIN(f.filing_date) as first_filing,
                MAX(f.filing_date) as last_filing,
                LIST(DISTINCT f.form_type) as form_types
            FROM entities e
            LEFT JOIN filings_partitioned f ON f.entity_id = e.entity_id
            WHERE e.entity_id = ?
            GROUP BY ALL
        """, [entity_id]).fetchone()
        
        return dict(result) if result else None
    
    def get_filing_analytics(
        self,
        start_date: str = None,
        end_date: str = None,
        form_types: List[str] = None,
    ) -> pl.DataFrame:
        """Get filing analytics as Polars DataFrame."""
        
        query = """
            SELECT 
                YEAR(filing_date) as year,
                MONTH(filing_date) as month,
                form_type,
                COUNT(*) as filing_count,
                COUNT(DISTINCT cik) as unique_filers
            FROM filings_partitioned
            WHERE 1=1
        """
        params = []
        
        if start_date:
            query += " AND filing_date >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND filing_date <= ?"
            params.append(end_date)
        
        if form_types:
            query += f" AND form_type IN ({','.join('?' * len(form_types))})"
            params.extend(form_types)
        
        query += " GROUP BY year, month, form_type ORDER BY year, month, form_type"
        
        return self.conn.execute(query, params).pl()
    
    def get_entity_relationship_network(
        self,
        entity_id: str,
        max_depth: int = 2,
    ) -> pl.DataFrame:
        """Get entity relationship network as DataFrame."""
        
        return self.conn.execute("""
            WITH RECURSIVE network AS (
                -- Base: starting entity
                SELECT 
                    entity_id as source_id,
                    entity_id as target_id,
                    NULL as relationship_type,
                    0 as depth
                FROM entities
                WHERE entity_id = ?
                
                UNION ALL
                
                -- Recurse: find related entities
                SELECT 
                    n.target_id as source_id,
                    r.related_entity_id as target_id,
                    r.relationship_type,
                    n.depth + 1
                FROM network n
                JOIN entity_relationships r 
                    ON r.entity_id = n.target_id OR r.related_entity_id = n.target_id
                WHERE n.depth < ?
            )
            SELECT DISTINCT * FROM network
            WHERE depth > 0
        """, [entity_id, max_depth]).pl()
    
    # =========================================================================
    # Batch Operations
    # =========================================================================
    
    def bulk_insert_entities(
        self,
        entities_df: pl.DataFrame,
    ) -> int:
        """Bulk insert entities from Polars DataFrame."""
        
        self.conn.execute("""
            INSERT INTO entities 
            SELECT * FROM entities_df
        """)
        
        return len(entities_df)
    
    def bulk_resolve_mentions(
        self,
        mentions_df: pl.DataFrame,
    ) -> pl.DataFrame:
        """Bulk resolve mentions against entity aliases."""
        
        # Register DataFrame
        self.conn.register('mentions_batch', mentions_df)
        
        # Join against aliases
        resolved = self.conn.execute("""
            SELECT 
                m.*,
                a.entity_id as resolved_entity_id,
                CASE 
                    WHEN a.entity_id IS NOT NULL THEN 'resolved'
                    ELSE 'pending'
                END as resolution_status
            FROM mentions_batch m
            LEFT JOIN entity_aliases a ON a.name_normalized = m.normalized_name
        """).pl()
        
        return resolved
    
    # =========================================================================
    # Full-Text Search
    # =========================================================================
    
    def create_fts_index(self):
        """Create full-text search index on entity names."""
        
        self.conn.execute("""
            PRAGMA create_fts_index(
                'entity_aliases', 
                'alias_id', 
                'alias_name', 
                'name_normalized',
                overwrite=1
            )
        """)
    
    def fts_search_entities(
        self,
        query: str,
        limit: int = 10,
    ) -> List[Dict]:
        """Full-text search on entity names."""
        
        results = self.conn.execute("""
            SELECT 
                a.entity_id,
                a.alias_name,
                e.primary_name,
                e.status,
                fts_main_entity_aliases.match_bm25(
                    a.alias_id, ?
                ) as score
            FROM entity_aliases a
            JOIN entities e ON e.entity_id = a.entity_id
            WHERE score IS NOT NULL
            ORDER BY score DESC
            LIMIT ?
        """, [query, limit]).fetchall()
        
        return [dict(r) for r in results]
```

---

## Tier 3: PostgreSQL

### When to Use

- Production source of truth
- Multi-user concurrent access
- Complex constraints and triggers
- Full ACID transactions
- > 1M entities or growing rapidly

### Full Schema

See [01_CANONICAL_DATA_MODEL.md](01_CANONICAL_DATA_MODEL.md) for complete DDL.

Key PostgreSQL-specific features:
- `EXCLUDE` constraints for overlapping date ranges
- Triggers for scope validation
- Recursive CTEs for merge following
- `pg_trgm` for fuzzy matching
- `pgvector` for embedding similarity

### Python Adapter

```python
import asyncpg
from typing import Optional, List, Dict, AsyncGenerator
from contextlib import asynccontextmanager


class PostgresEntityStore:
    """PostgreSQL storage adapter for production use."""
    
    def __init__(self, dsn: str):
        self.dsn = dsn
        self.pool = None
    
    async def connect(self):
        """Create connection pool."""
        self.pool = await asyncpg.create_pool(
            self.dsn,
            min_size=5,
            max_size=20,
        )
    
    async def close(self):
        """Close connection pool."""
        if self.pool:
            await self.pool.close()
    
    @asynccontextmanager
    async def transaction(self):
        """Get connection with transaction."""
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                yield conn
    
    # =========================================================================
    # Entity Operations (Full featured)
    # =========================================================================
    
    async def get_entity(
        self,
        entity_id: str,
        follow_merges: bool = True,
    ) -> Optional[Dict]:
        """Get entity by ID, optionally following merges."""
        
        async with self.pool.acquire() as conn:
            if follow_merges:
                # Use recursive CTE
                row = await conn.fetchrow("""
                    WITH RECURSIVE merge_chain AS (
                        SELECT entity_id, entity_id as original_id
                        FROM entities
                        WHERE entity_id = $1
                        
                        UNION ALL
                        
                        SELECT m.to_entity_id, mc.original_id
                        FROM entity_merges m
                        JOIN merge_chain mc ON m.from_entity_id = mc.entity_id
                    )
                    SELECT e.*, mc.original_id as requested_id
                    FROM entities e
                    JOIN merge_chain mc ON e.entity_id = mc.entity_id
                    WHERE e.status != 'merged'
                    LIMIT 1
                """, entity_id)
            else:
                row = await conn.fetchrow(
                    "SELECT * FROM entities WHERE entity_id = $1",
                    entity_id
                )
            
            return dict(row) if row else None
    
    async def resolve(
        self,
        identifier: str,
        as_of_date: str = None,
        follow_merges: bool = True,
    ) -> Optional[Dict]:
        """
        Resolve any identifier to entity/security/listing.
        
        Uses the unified resolution logic from 02_RESOLUTION_AND_MERGE_WORKFLOWS.md
        """
        
        # Detect identifier type
        id_type = detect_identifier_type(identifier)
        
        async with self.pool.acquire() as conn:
            if id_type['scheme'] == 'cik':
                return await self._resolve_cik(conn, id_type['value'], follow_merges)
            
            elif id_type['scheme'] == 'lei':
                return await self._resolve_lei(conn, id_type['value'], follow_merges)
            
            elif id_type['scheme'] == 'isin':
                return await self._resolve_isin(conn, id_type['value'], follow_merges)
            
            elif id_type['scheme'] == 'ticker':
                return await self._resolve_ticker(
                    conn, id_type['value'], as_of_date, follow_merges
                )
            
            else:
                # Try generic lookup
                return await self._resolve_generic(conn, identifier, follow_merges)
    
    async def _resolve_cik(
        self,
        conn,
        cik: str,
        follow_merges: bool,
    ) -> Optional[Dict]:
        """Resolve CIK to entity."""
        
        row = await conn.fetchrow("""
            SELECT 
                e.entity_id,
                e.primary_name,
                e.status,
                'entity' as resolved_type,
                i.scheme as matched_scheme,
                i.value as matched_value
            FROM identifiers i
            JOIN entities e ON e.entity_id = i.entity_id
            WHERE i.scheme = 'cik' 
              AND i.value = $1
        """, cik.zfill(10))
        
        if row and follow_merges:
            canonical = await self.get_entity(row['entity_id'], follow_merges=True)
            return {**dict(row), 'canonical_entity_id': canonical['entity_id']}
        
        return dict(row) if row else None
    
    async def _resolve_ticker(
        self,
        conn,
        ticker: str,
        as_of_date: str,
        follow_merges: bool,
    ) -> Optional[Dict]:
        """Resolve ticker to listing → security → entity."""
        
        query = """
            SELECT 
                l.listing_id,
                l.ticker,
                l.mic,
                s.security_id,
                s.name as security_name,
                e.entity_id,
                e.primary_name,
                'listing' as resolved_type
            FROM listings l
            JOIN securities s ON s.security_id = l.security_id
            JOIN entities e ON e.entity_id = s.issuer_entity_id
            WHERE l.ticker = $1
              AND l.status = 'active'
        """
        params = [ticker.upper()]
        
        if as_of_date:
            query += """
                AND (l.valid_from IS NULL OR l.valid_from <= $2)
                AND (l.valid_to IS NULL OR l.valid_to > $2)
            """
            params.append(as_of_date)
        
        row = await conn.fetchrow(query, *params)
        return dict(row) if row else None
    
    # =========================================================================
    # Fuzzy Search with pg_trgm
    # =========================================================================
    
    async def fuzzy_search_entities(
        self,
        name: str,
        threshold: float = 0.3,
        limit: int = 10,
    ) -> List[Dict]:
        """Fuzzy search using trigram similarity."""
        
        normalized = normalize_company_name(name)
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT 
                    e.entity_id,
                    e.primary_name,
                    e.status,
                    a.alias_name,
                    similarity(a.name_normalized, $1) as score
                FROM entity_aliases a
                JOIN entities e ON e.entity_id = a.entity_id
                WHERE a.name_normalized % $1
                  AND e.status IN ('active', 'provisional')
                ORDER BY score DESC
                LIMIT $2
            """, normalized, limit)
            
            return [dict(r) for r in rows]
    
    # =========================================================================
    # Vector Search with pgvector
    # =========================================================================
    
    async def vector_search_entities(
        self,
        embedding: List[float],
        limit: int = 10,
    ) -> List[Dict]:
        """Search entities by name embedding similarity."""
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT 
                    e.entity_id,
                    e.primary_name,
                    e.status,
                    1 - (ev.name_embedding <=> $1::vector) as similarity
                FROM entity_vectors ev
                JOIN entities e ON e.entity_id = ev.entity_id
                WHERE e.status IN ('active', 'provisional')
                ORDER BY ev.name_embedding <=> $1::vector
                LIMIT $2
            """, embedding, limit)
            
            return [dict(r) for r in rows]
    
    # =========================================================================
    # Conflict Handling with Row Locking
    # =========================================================================
    
    async def safe_merge_entities(
        self,
        from_entity_id: str,
        to_entity_id: str,
        merge_type: str,
        reason: str,
    ) -> str:
        """Merge entities with proper locking."""
        
        async with self.transaction() as conn:
            # Lock both entities (in sorted order to prevent deadlock)
            entity_ids = sorted([from_entity_id, to_entity_id])
            
            await conn.execute("""
                SELECT * FROM entities 
                WHERE entity_id = ANY($1)
                FOR UPDATE
            """, entity_ids)
            
            # Verify neither is already merged
            status = await conn.fetch("""
                SELECT entity_id, status FROM entities
                WHERE entity_id = ANY($1)
            """, entity_ids)
            
            for s in status:
                if s['status'] == 'merged':
                    raise ValueError(f"Entity {s['entity_id']} is already merged")
            
            # Perform merge
            merge_id = generate_ulid()
            
            await conn.execute("""
                INSERT INTO entity_merges (
                    merge_id, from_entity_id, to_entity_id, merge_type, reason
                ) VALUES ($1, $2, $3, $4, $5)
            """, merge_id, from_entity_id, to_entity_id, merge_type, reason)
            
            await conn.execute("""
                UPDATE entities SET status = 'merged', updated_at = NOW()
                WHERE entity_id = $1
            """, from_entity_id)
            
            # Transfer assets
            await conn.execute("""
                UPDATE entity_aliases SET entity_id = $1 WHERE entity_id = $2
            """, to_entity_id, from_entity_id)
            
            await conn.execute("""
                UPDATE identifiers SET entity_id = $1 WHERE entity_id = $2
            """, to_entity_id, from_entity_id)
            
            return merge_id
```

---

## Tier 4/5: Elasticsearch + Neo4j

### Elasticsearch: Full-Text Search

```python
from elasticsearch import AsyncElasticsearch


class ElasticsearchEntityIndex:
    """Elasticsearch index for entity search."""
    
    INDEX_NAME = "entities"
    
    MAPPING = {
        "mappings": {
            "properties": {
                "entity_id": {"type": "keyword"},
                "primary_name": {
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
                "status": {"type": "keyword"},
                "entity_type": {"type": "keyword"},
                "jurisdiction": {"type": "keyword"},
                "identifiers": {
                    "type": "nested",
                    "properties": {
                        "scheme": {"type": "keyword"},
                        "value": {"type": "keyword"}
                    }
                },
                "created_at": {"type": "date"},
                "updated_at": {"type": "date"}
            }
        },
        "settings": {
            "analysis": {
                "analyzer": {
                    "autocomplete": {
                        "tokenizer": "autocomplete",
                        "filter": ["lowercase"]
                    }
                },
                "tokenizer": {
                    "autocomplete": {
                        "type": "edge_ngram",
                        "min_gram": 2,
                        "max_gram": 20,
                        "token_chars": ["letter", "digit"]
                    }
                }
            }
        }
    }
    
    def __init__(self, hosts: List[str]):
        self.client = AsyncElasticsearch(hosts)
    
    async def create_index(self):
        """Create the entities index."""
        await self.client.indices.create(
            index=self.INDEX_NAME,
            body=self.MAPPING,
            ignore=400,  # Ignore if exists
        )
    
    async def index_entity(self, entity: Dict):
        """Index a single entity."""
        
        doc = {
            "entity_id": entity["entity_id"],
            "primary_name": entity["primary_name"],
            "aliases": entity.get("aliases", []),
            "status": entity["status"],
            "entity_type": entity.get("entity_type"),
            "jurisdiction": entity.get("jurisdiction"),
            "identifiers": entity.get("identifiers", []),
            "created_at": entity.get("created_at"),
            "updated_at": entity.get("updated_at"),
        }
        
        await self.client.index(
            index=self.INDEX_NAME,
            id=entity["entity_id"],
            document=doc,
        )
    
    async def search(
        self,
        query: str,
        filters: Dict = None,
        limit: int = 10,
    ) -> List[Dict]:
        """Search entities."""
        
        must = [
            {
                "multi_match": {
                    "query": query,
                    "fields": [
                        "primary_name^3",
                        "primary_name.autocomplete^2",
                        "aliases"
                    ],
                    "type": "best_fields",
                    "fuzziness": "AUTO"
                }
            }
        ]
        
        filter_clauses = []
        
        if filters:
            if filters.get("status"):
                filter_clauses.append({"term": {"status": filters["status"]}})
            
            if filters.get("entity_type"):
                filter_clauses.append({"term": {"entity_type": filters["entity_type"]}})
        
        body = {
            "query": {
                "bool": {
                    "must": must,
                    "filter": filter_clauses
                }
            },
            "size": limit
        }
        
        response = await self.client.search(
            index=self.INDEX_NAME,
            body=body,
        )
        
        return [
            {**hit["_source"], "_score": hit["_score"]}
            for hit in response["hits"]["hits"]
        ]
```

### Neo4j: Graph Queries

```python
from neo4j import AsyncGraphDatabase


class Neo4jEntityGraph:
    """Neo4j graph for entity relationships."""
    
    def __init__(self, uri: str, user: str, password: str):
        self.driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
    
    async def close(self):
        await self.driver.close()
    
    # =========================================================================
    # Graph Schema
    # =========================================================================
    
    async def create_constraints(self):
        """Create graph constraints and indexes."""
        
        async with self.driver.session() as session:
            # Unique constraints
            await session.run("""
                CREATE CONSTRAINT entity_id IF NOT EXISTS
                FOR (e:Entity) REQUIRE e.entity_id IS UNIQUE
            """)
            
            await session.run("""
                CREATE CONSTRAINT security_id IF NOT EXISTS
                FOR (s:Security) REQUIRE s.security_id IS UNIQUE
            """)
            
            # Indexes
            await session.run("""
                CREATE INDEX entity_name IF NOT EXISTS
                FOR (e:Entity) ON (e.primary_name)
            """)
    
    # =========================================================================
    # Sync from PostgreSQL
    # =========================================================================
    
    async def sync_entity(self, entity: Dict, relationships: List[Dict]):
        """Sync an entity and its relationships to Neo4j."""
        
        async with self.driver.session() as session:
            # Upsert entity node
            await session.run("""
                MERGE (e:Entity {entity_id: $entity_id})
                SET e.primary_name = $primary_name,
                    e.status = $status,
                    e.entity_type = $entity_type,
                    e.updated_at = datetime()
            """, **entity)
            
            # Upsert relationships
            for rel in relationships:
                await session.run("""
                    MATCH (e1:Entity {entity_id: $entity_id})
                    MERGE (e2:Entity {entity_id: $related_entity_id})
                    MERGE (e1)-[r:RELATED_TO {type: $relationship_type}]->(e2)
                    SET r.since = $valid_from,
                        r.source = $source
                """, **rel)
    
    # =========================================================================
    # Graph Queries
    # =========================================================================
    
    async def get_ownership_chain(
        self,
        entity_id: str,
        max_depth: int = 5,
    ) -> List[Dict]:
        """Get ownership chain (parents/subsidiaries)."""
        
        async with self.driver.session() as session:
            result = await session.run("""
                MATCH path = (child:Entity)-[:RELATED_TO*1..$max_depth {type: 'subsidiary'}]->(parent:Entity)
                WHERE child.entity_id = $entity_id OR parent.entity_id = $entity_id
                RETURN [n IN nodes(path) | {
                    entity_id: n.entity_id,
                    name: n.primary_name
                }] as chain,
                length(path) as depth
                ORDER BY depth
            """, entity_id=entity_id, max_depth=max_depth)
            
            return [dict(r) async for r in result]
    
    async def find_connection_paths(
        self,
        entity_id_1: str,
        entity_id_2: str,
        max_depth: int = 4,
    ) -> List[Dict]:
        """Find all paths connecting two entities."""
        
        async with self.driver.session() as session:
            result = await session.run("""
                MATCH path = shortestPath(
                    (e1:Entity {entity_id: $id1})-[*1..$max_depth]-(e2:Entity {entity_id: $id2})
                )
                RETURN [n IN nodes(path) | {
                    entity_id: n.entity_id,
                    name: n.primary_name
                }] as nodes,
                [r IN relationships(path) | {
                    type: r.type
                }] as relationships,
                length(path) as depth
            """, id1=entity_id_1, id2=entity_id_2, max_depth=max_depth)
            
            return [dict(r) async for r in result]
    
    async def get_entity_network(
        self,
        entity_id: str,
        relationship_types: List[str] = None,
        max_depth: int = 2,
    ) -> Dict:
        """Get full network around an entity for visualization."""
        
        type_filter = ""
        if relationship_types:
            types_str = "|".join(relationship_types)
            type_filter = f"[:{types_str}]"
        
        async with self.driver.session() as session:
            result = await session.run(f"""
                MATCH (center:Entity {{entity_id: $entity_id}})
                CALL {{
                    WITH center
                    MATCH path = (center)-{type_filter}*1..{max_depth}-(connected:Entity)
                    RETURN connected, relationships(path) as rels
                }}
                WITH center, collect(DISTINCT connected) as nodes, 
                     collect(DISTINCT rels) as all_rels
                RETURN {{
                    center: {{
                        entity_id: center.entity_id,
                        name: center.primary_name
                    }},
                    nodes: [n IN nodes | {{
                        entity_id: n.entity_id,
                        name: n.primary_name,
                        status: n.status
                    }}],
                    edges: [r IN all_rels | {{
                        source: startNode(r).entity_id,
                        target: endNode(r).entity_id,
                        type: r.type
                    }}]
                }} as network
            """, entity_id=entity_id)
            
            record = await result.single()
            return record["network"] if record else None
```

---

## Source of Truth Rules

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              SOURCE OF TRUTH HIERARCHY                                   │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                          │
│  POSTGRESQL IS SOURCE OF TRUTH                                                           │
│  ─────────────────────────────                                                           │
│                                                                                          │
│  All writes go to PostgreSQL first. Downstream systems (ES, Neo4j, DuckDB) are          │
│  replicas/projections that are eventually consistent.                                    │
│                                                                                          │
│  ┌────────────┐                                                                          │
│  │ PostgreSQL │ ─────────────────────────────────────────────────────────────►          │
│  │ (Primary)  │                                                                          │
│  └────────────┘                                                                          │
│        │                                                                                 │
│        │ CDC / Async Sync                                                                │
│        │                                                                                 │
│        ├──────────────► Elasticsearch (search index)                                     │
│        │                - Eventual consistency OK                                        │
│        │                - Refresh on entity create/update/delete                         │
│        │                                                                                 │
│        ├──────────────► Neo4j (graph replica)                                           │
│        │                - Sync relationships                                             │
│        │                - Refresh on relationship changes                                │
│        │                                                                                 │
│        └──────────────► DuckDB (analytics snapshot)                                     │
│                         - Nightly batch sync                                             │
│                         - Read-only analytics queries                                    │
│                                                                                          │
│  CONFLICT RESOLUTION                                                                     │
│  ───────────────────                                                                     │
│                                                                                          │
│  If PostgreSQL and downstream disagree:                                                  │
│  1. PostgreSQL wins                                                                      │
│  2. Re-sync downstream from PostgreSQL                                                   │
│  3. Log the discrepancy for investigation                                                │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Next Document

→ [06_PYSECEDGAR_PORT.md](06_PYSECEDGAR_PORT.md) - EntityResolver port interface
