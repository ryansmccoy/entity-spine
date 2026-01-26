# Entity Master - Storage Backends

Detailed implementation guide for each storage tier.

---

## Storage Abstraction

All storage backends implement a common interface:

```python
# entity_master/storage/base.py

from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional
from datetime import datetime


class BaseStorage(ABC):
    """Abstract base for all storage backends."""
    
    # =========================================================================
    # ENTITY OPERATIONS
    # =========================================================================
    
    @abstractmethod
    async def get_entity(self, entity_id: str) -> Optional[dict]:
        """Get entity by internal ID."""
        ...
    
    @abstractmethod
    async def get_by_identifier(
        self,
        scheme: str,
        value: str,
    ) -> Optional[dict]:
        """Get entity by any identifier."""
        ...
    
    @abstractmethod
    async def upsert_entity(self, entity: dict) -> str:
        """Insert or update entity, return ID."""
        ...
    
    @abstractmethod
    async def delete_entity(self, entity_id: str) -> bool:
        """Delete entity."""
        ...
    
    @abstractmethod
    async def list_entities(
        self,
        entity_type: str = None,
        status: str = None,
        limit: int = 100,
        offset: int = 0,
    ) -> AsyncIterator[dict]:
        """List entities with optional filters."""
        ...
    
    # =========================================================================
    # SEARCH
    # =========================================================================
    
    @abstractmethod
    async def search(
        self,
        query: str,
        entity_type: str = None,
        limit: int = 10,
    ) -> list[dict]:
        """Search entities by name."""
        ...
    
    # =========================================================================
    # IDENTIFIER INDEX
    # =========================================================================
    
    @abstractmethod
    async def add_identifier(
        self,
        entity_id: str,
        scheme: str,
        value: str,
        metadata: dict = None,
    ) -> bool:
        """Add identifier to entity."""
        ...
    
    @abstractmethod
    async def remove_identifier(
        self,
        entity_id: str,
        scheme: str,
        value: str,
    ) -> bool:
        """Remove identifier from entity."""
        ...
    
    # =========================================================================
    # RELATIONSHIPS (Optional - Tier 4+)
    # =========================================================================
    
    async def add_relationship(
        self,
        source_id: str,
        target_id: str,
        relationship_type: str,
        metadata: dict = None,
    ) -> str:
        """Add relationship between entities."""
        raise NotImplementedError("Relationships not supported in this tier")
    
    async def get_relationships(
        self,
        entity_id: str,
        relationship_type: str = None,
        direction: str = "both",
    ) -> list[dict]:
        """Get entity relationships."""
        raise NotImplementedError("Relationships not supported in this tier")
    
    # =========================================================================
    # LIFECYCLE
    # =========================================================================
    
    @abstractmethod
    async def initialize(self):
        """Initialize storage (create tables, indexes, etc.)."""
        ...
    
    @abstractmethod
    async def close(self):
        """Clean up resources."""
        ...
    
    async def __aenter__(self):
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
```

---

## Tier 1: SQLite Storage

Simple, file-based storage. No external dependencies.

```python
# entity_master/storage/sqlite.py

import aiosqlite
import json
from pathlib import Path
from typing import Optional, AsyncIterator
from entity_master.storage.base import BaseStorage


class SQLiteStorage(BaseStorage):
    """SQLite-based storage for Tier 1 (Basic)."""
    
    def __init__(self, db_path: str = "~/.entity_master/entities.db"):
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: aiosqlite.Connection = None
    
    async def initialize(self):
        """Create database and tables."""
        self._conn = await aiosqlite.connect(self.db_path)
        
        # Enable WAL mode for better concurrency
        await self._conn.execute("PRAGMA journal_mode=WAL")
        
        # Create tables
        await self._conn.executescript("""
            -- Entities table
            CREATE TABLE IF NOT EXISTS entities (
                id TEXT PRIMARY KEY,
                entity_type TEXT NOT NULL,
                primary_name TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                metadata TEXT,  -- JSON
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            
            -- Identifiers table (separate for efficient lookups)
            CREATE TABLE IF NOT EXISTS identifiers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_id TEXT NOT NULL,
                scheme TEXT NOT NULL,
                value TEXT NOT NULL,
                exchange TEXT,      -- For tickers
                valid_from TEXT,
                valid_to TEXT,
                metadata TEXT,      -- JSON
                FOREIGN KEY (entity_id) REFERENCES entities(id) ON DELETE CASCADE,
                UNIQUE(scheme, value)
            );
            
            -- Aliases table
            CREATE TABLE IF NOT EXISTS aliases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_id TEXT NOT NULL,
                alias TEXT NOT NULL,
                source TEXT,
                FOREIGN KEY (entity_id) REFERENCES entities(id) ON DELETE CASCADE
            );
            
            -- Indexes
            CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(primary_name);
            CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type);
            CREATE INDEX IF NOT EXISTS idx_entities_status ON entities(status);
            CREATE INDEX IF NOT EXISTS idx_identifiers_scheme_value ON identifiers(scheme, value);
            CREATE INDEX IF NOT EXISTS idx_identifiers_entity ON identifiers(entity_id);
            CREATE INDEX IF NOT EXISTS idx_aliases_entity ON aliases(entity_id);
            
            -- Full-text search (SQLite FTS5)
            CREATE VIRTUAL TABLE IF NOT EXISTS entities_fts USING fts5(
                primary_name,
                content='entities',
                content_rowid='rowid'
            );
            
            -- Triggers to keep FTS in sync
            CREATE TRIGGER IF NOT EXISTS entities_ai AFTER INSERT ON entities BEGIN
                INSERT INTO entities_fts(rowid, primary_name) VALUES (new.rowid, new.primary_name);
            END;
            
            CREATE TRIGGER IF NOT EXISTS entities_ad AFTER DELETE ON entities BEGIN
                INSERT INTO entities_fts(entities_fts, rowid, primary_name) 
                VALUES('delete', old.rowid, old.primary_name);
            END;
            
            CREATE TRIGGER IF NOT EXISTS entities_au AFTER UPDATE ON entities BEGIN
                INSERT INTO entities_fts(entities_fts, rowid, primary_name) 
                VALUES('delete', old.rowid, old.primary_name);
                INSERT INTO entities_fts(rowid, primary_name) VALUES (new.rowid, new.primary_name);
            END;
        """)
        
        await self._conn.commit()
    
    async def close(self):
        """Close database connection."""
        if self._conn:
            await self._conn.close()
            self._conn = None
    
    async def get_entity(self, entity_id: str) -> Optional[dict]:
        """Get entity by ID with all identifiers."""
        # Get base entity
        async with self._conn.execute(
            "SELECT * FROM entities WHERE id = ?",
            (entity_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            
            entity = {
                "id": row[0],
                "entity_type": row[1],
                "primary_name": row[2],
                "status": row[3],
                "metadata": json.loads(row[4]) if row[4] else {},
                "created_at": row[5],
                "updated_at": row[6],
            }
        
        # Get identifiers
        async with self._conn.execute(
            "SELECT scheme, value, exchange, valid_from, valid_to FROM identifiers WHERE entity_id = ?",
            (entity_id,)
        ) as cursor:
            identifiers = []
            async for row in cursor:
                ident = {"scheme": row[0], "value": row[1]}
                if row[2]:
                    ident["exchange"] = row[2]
                if row[3]:
                    ident["valid_from"] = row[3]
                if row[4]:
                    ident["valid_to"] = row[4]
                identifiers.append(ident)
            entity["identifiers"] = identifiers
        
        # Get aliases
        async with self._conn.execute(
            "SELECT alias FROM aliases WHERE entity_id = ?",
            (entity_id,)
        ) as cursor:
            entity["aliases"] = [row[0] async for row in cursor]
        
        return entity
    
    async def get_by_identifier(
        self,
        scheme: str,
        value: str,
    ) -> Optional[dict]:
        """Get entity by identifier."""
        async with self._conn.execute(
            "SELECT entity_id FROM identifiers WHERE scheme = ? AND value = ?",
            (scheme, value.upper())
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            return await self.get_entity(row[0])
    
    async def upsert_entity(self, entity: dict) -> str:
        """Insert or update entity."""
        entity_id = entity.get("id") or self._generate_id(entity)
        
        # Upsert entity
        await self._conn.execute("""
            INSERT INTO entities (id, entity_type, primary_name, status, metadata, updated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(id) DO UPDATE SET
                primary_name = excluded.primary_name,
                status = excluded.status,
                metadata = excluded.metadata,
                updated_at = CURRENT_TIMESTAMP
        """, (
            entity_id,
            entity.get("entity_type", "company"),
            entity["primary_name"],
            entity.get("status", "active"),
            json.dumps(entity.get("metadata", {})),
        ))
        
        # Update identifiers
        for ident in entity.get("identifiers", []):
            await self._conn.execute("""
                INSERT OR REPLACE INTO identifiers (entity_id, scheme, value, exchange, valid_from, valid_to)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                entity_id,
                ident["scheme"],
                ident["value"].upper(),
                ident.get("exchange"),
                ident.get("valid_from"),
                ident.get("valid_to"),
            ))
        
        # Update aliases
        await self._conn.execute(
            "DELETE FROM aliases WHERE entity_id = ?",
            (entity_id,)
        )
        for alias in entity.get("aliases", []):
            await self._conn.execute(
                "INSERT INTO aliases (entity_id, alias) VALUES (?, ?)",
                (entity_id, alias)
            )
        
        await self._conn.commit()
        return entity_id
    
    async def search(
        self,
        query: str,
        entity_type: str = None,
        limit: int = 10,
    ) -> list[dict]:
        """Full-text search on entity names."""
        # Use FTS5 for better search
        sql = """
            SELECT e.id FROM entities e
            JOIN entities_fts fts ON e.rowid = fts.rowid
            WHERE entities_fts MATCH ?
        """
        params = [f'"{query}"*']  # Prefix search
        
        if entity_type:
            sql += " AND e.entity_type = ?"
            params.append(entity_type)
        
        sql += " LIMIT ?"
        params.append(limit)
        
        entities = []
        async with self._conn.execute(sql, params) as cursor:
            async for row in cursor:
                entity = await self.get_entity(row[0])
                if entity:
                    entities.append(entity)
        
        return entities
    
    def _generate_id(self, entity: dict) -> str:
        """Generate entity ID from name."""
        import re
        name = entity["primary_name"].lower()
        name = re.sub(r'[^a-z0-9]+', '_', name)
        return f"em_{name[:50]}"
```

---

## Tier 2: DuckDB Storage

Analytical workloads, better performance for large datasets.

```python
# entity_master/storage/duckdb.py

import duckdb
from typing import Optional, AsyncIterator
from entity_master.storage.base import BaseStorage


class DuckDBStorage(BaseStorage):
    """DuckDB-based storage for Tier 2 (Intermediate).
    
    Benefits over SQLite:
    - Columnar storage (faster analytics)
    - Better parallel query execution
    - Native JSON support
    - Parquet export/import
    """
    
    def __init__(self, db_path: str = "~/.entity_master/entities.duckdb"):
        self.db_path = str(Path(db_path).expanduser())
        self._conn: duckdb.DuckDBPyConnection = None
    
    async def initialize(self):
        """Create database and tables."""
        self._conn = duckdb.connect(self.db_path)
        
        # Create tables with DuckDB-specific optimizations
        self._conn.execute("""
            -- Entities table
            CREATE TABLE IF NOT EXISTS entities (
                id VARCHAR PRIMARY KEY,
                entity_type VARCHAR NOT NULL,
                primary_name VARCHAR NOT NULL,
                status VARCHAR DEFAULT 'active',
                metadata JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            -- Identifiers table with struct column for flexibility
            CREATE TABLE IF NOT EXISTS identifiers (
                entity_id VARCHAR NOT NULL,
                scheme VARCHAR NOT NULL,
                value VARCHAR NOT NULL,
                metadata JSON,
                PRIMARY KEY (scheme, value),
                FOREIGN KEY (entity_id) REFERENCES entities(id)
            );
            
            -- Aliases
            CREATE TABLE IF NOT EXISTS aliases (
                entity_id VARCHAR NOT NULL,
                alias VARCHAR NOT NULL,
                source VARCHAR,
                FOREIGN KEY (entity_id) REFERENCES entities(id)
            );
            
            -- Sightings (for change tracking)
            CREATE TABLE IF NOT EXISTS sightings (
                entity_id VARCHAR NOT NULL,
                source VARCHAR NOT NULL,
                captured_at TIMESTAMP NOT NULL,
                content JSON,
                FOREIGN KEY (entity_id) REFERENCES entities(id)
            );
        """)
        
        # Create indexes
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(primary_name);
            CREATE INDEX IF NOT EXISTS idx_identifiers_entity ON identifiers(entity_id);
        """)
    
    async def get_by_identifier(
        self,
        scheme: str,
        value: str,
    ) -> Optional[dict]:
        """Get entity by identifier using DuckDB's JSON features."""
        result = self._conn.execute("""
            SELECT 
                e.*,
                (
                    SELECT list(struct_pack(
                        scheme := i.scheme,
                        value := i.value,
                        metadata := i.metadata
                    ))
                    FROM identifiers i
                    WHERE i.entity_id = e.id
                ) as identifiers,
                (
                    SELECT list(alias)
                    FROM aliases a
                    WHERE a.entity_id = e.id
                ) as aliases
            FROM entities e
            JOIN identifiers i ON e.id = i.entity_id
            WHERE i.scheme = ? AND i.value = ?
        """, [scheme, value.upper()]).fetchone()
        
        if not result:
            return None
        
        return self._row_to_entity(result)
    
    async def search(
        self,
        query: str,
        entity_type: str = None,
        limit: int = 10,
    ) -> list[dict]:
        """Search using DuckDB's SIMILAR TO or FTS extension."""
        # DuckDB has a full-text search extension
        sql = """
            SELECT 
                e.*,
                list(struct_pack(scheme := i.scheme, value := i.value)) as identifiers
            FROM entities e
            LEFT JOIN identifiers i ON e.id = i.entity_id
            WHERE e.primary_name ILIKE ?
        """
        params = [f"%{query}%"]
        
        if entity_type:
            sql += " AND e.entity_type = ?"
            params.append(entity_type)
        
        sql += " GROUP BY e.id LIMIT ?"
        params.append(limit)
        
        results = self._conn.execute(sql, params).fetchall()
        return [self._row_to_entity(r) for r in results]
    
    async def export_parquet(self, output_path: str):
        """Export entities to Parquet for analytics."""
        self._conn.execute(f"""
            COPY (
                SELECT 
                    e.*,
                    i.identifiers
                FROM entities e
                LEFT JOIN (
                    SELECT 
                        entity_id,
                        list(struct_pack(scheme, value)) as identifiers
                    FROM identifiers
                    GROUP BY entity_id
                ) i ON e.id = i.entity_id
            ) TO '{output_path}' (FORMAT PARQUET)
        """)
    
    async def import_parquet(self, input_path: str):
        """Import entities from Parquet."""
        self._conn.execute(f"""
            INSERT INTO entities
            SELECT * FROM read_parquet('{input_path}')
            ON CONFLICT (id) DO UPDATE SET
                primary_name = excluded.primary_name,
                metadata = excluded.metadata,
                updated_at = CURRENT_TIMESTAMP
        """)
```

---

## Tier 3: PostgreSQL Storage

Production-grade with advanced features.

```python
# entity_master/storage/postgres.py

import asyncpg
from typing import Optional, AsyncIterator
from entity_master.storage.base import BaseStorage


class PostgresStorage(BaseStorage):
    """PostgreSQL-based storage for Tier 3 (Advanced).
    
    Benefits:
    - Production-grade reliability
    - Advanced indexing (GIN, GiST)
    - Full-text search with ranking
    - JSONB for flexible metadata
    - Listen/Notify for real-time updates
    """
    
    def __init__(
        self,
        dsn: str = "postgresql://localhost/entity_master",
        pool_size: int = 10,
    ):
        self.dsn = dsn
        self.pool_size = pool_size
        self._pool: asyncpg.Pool = None
    
    async def initialize(self):
        """Create connection pool and schema."""
        self._pool = await asyncpg.create_pool(
            self.dsn,
            min_size=2,
            max_size=self.pool_size,
        )
        
        async with self._pool.acquire() as conn:
            # Create schema
            await conn.execute("""
                -- Extensions
                CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- Fuzzy matching
                CREATE EXTENSION IF NOT EXISTS btree_gin;  -- Composite indexes
                
                -- Entities table
                CREATE TABLE IF NOT EXISTS entities (
                    id TEXT PRIMARY KEY,
                    entity_type TEXT NOT NULL,
                    primary_name TEXT NOT NULL,
                    status TEXT DEFAULT 'active',
                    metadata JSONB DEFAULT '{}',
                    search_vector TSVECTOR,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                );
                
                -- Identifiers with JSONB metadata
                CREATE TABLE IF NOT EXISTS identifiers (
                    id SERIAL PRIMARY KEY,
                    entity_id TEXT NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
                    scheme TEXT NOT NULL,
                    value TEXT NOT NULL,
                    metadata JSONB DEFAULT '{}',
                    valid_from DATE,
                    valid_to DATE,
                    UNIQUE(scheme, value)
                );
                
                -- Aliases
                CREATE TABLE IF NOT EXISTS aliases (
                    id SERIAL PRIMARY KEY,
                    entity_id TEXT NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
                    alias TEXT NOT NULL,
                    source TEXT
                );
                
                -- Relationships (for Tier 3 basic graph queries)
                CREATE TABLE IF NOT EXISTS relationships (
                    id SERIAL PRIMARY KEY,
                    source_id TEXT NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
                    target_id TEXT NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
                    relationship_type TEXT NOT NULL,
                    confidence FLOAT DEFAULT 1.0,
                    sources TEXT[],
                    metadata JSONB DEFAULT '{}',
                    valid_from DATE,
                    valid_to DATE,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    UNIQUE(source_id, target_id, relationship_type)
                );
                
                -- Indexes
                CREATE INDEX IF NOT EXISTS idx_entities_search 
                    ON entities USING GIN(search_vector);
                CREATE INDEX IF NOT EXISTS idx_entities_name_trgm 
                    ON entities USING GIN(primary_name gin_trgm_ops);
                CREATE INDEX IF NOT EXISTS idx_entities_metadata 
                    ON entities USING GIN(metadata);
                CREATE INDEX IF NOT EXISTS idx_identifiers_scheme_value 
                    ON identifiers(scheme, value);
                CREATE INDEX IF NOT EXISTS idx_identifiers_entity 
                    ON identifiers(entity_id);
                CREATE INDEX IF NOT EXISTS idx_relationships_source 
                    ON relationships(source_id);
                CREATE INDEX IF NOT EXISTS idx_relationships_target 
                    ON relationships(target_id);
                
                -- Update search vector trigger
                CREATE OR REPLACE FUNCTION update_search_vector()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.search_vector := to_tsvector('english', NEW.primary_name);
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;
                
                DROP TRIGGER IF EXISTS update_entities_search_vector ON entities;
                CREATE TRIGGER update_entities_search_vector
                    BEFORE INSERT OR UPDATE ON entities
                    FOR EACH ROW EXECUTE FUNCTION update_search_vector();
                
                -- Notify on changes (for webhooks)
                CREATE OR REPLACE FUNCTION notify_entity_change()
                RETURNS TRIGGER AS $$
                BEGIN
                    PERFORM pg_notify('entity_changes', json_build_object(
                        'operation', TG_OP,
                        'entity_id', COALESCE(NEW.id, OLD.id)
                    )::text);
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;
                
                DROP TRIGGER IF EXISTS entity_change_notify ON entities;
                CREATE TRIGGER entity_change_notify
                    AFTER INSERT OR UPDATE OR DELETE ON entities
                    FOR EACH ROW EXECUTE FUNCTION notify_entity_change();
            """)
    
    async def close(self):
        """Close connection pool."""
        if self._pool:
            await self._pool.close()
    
    async def search(
        self,
        query: str,
        entity_type: str = None,
        limit: int = 10,
    ) -> list[dict]:
        """Full-text search with ranking."""
        async with self._pool.acquire() as conn:
            # Combine FTS with trigram similarity for best results
            sql = """
                SELECT 
                    e.*,
                    array_agg(json_build_object(
                        'scheme', i.scheme,
                        'value', i.value
                    )) FILTER (WHERE i.id IS NOT NULL) as identifiers,
                    ts_rank(e.search_vector, plainto_tsquery('english', $1)) as rank,
                    similarity(e.primary_name, $1) as sim
                FROM entities e
                LEFT JOIN identifiers i ON e.id = i.entity_id
                WHERE 
                    e.search_vector @@ plainto_tsquery('english', $1)
                    OR e.primary_name % $1  -- Trigram similarity
            """
            params = [query]
            
            if entity_type:
                sql += " AND e.entity_type = $2"
                params.append(entity_type)
            
            sql += """
                GROUP BY e.id
                ORDER BY rank DESC, sim DESC
                LIMIT $%d
            """ % (len(params) + 1)
            params.append(limit)
            
            rows = await conn.fetch(sql, *params)
            return [dict(row) for row in rows]
    
    async def add_relationship(
        self,
        source_id: str,
        target_id: str,
        relationship_type: str,
        metadata: dict = None,
    ) -> str:
        """Add relationship (Tier 3 supports basic relationships)."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow("""
                INSERT INTO relationships (source_id, target_id, relationship_type, metadata)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (source_id, target_id, relationship_type) 
                DO UPDATE SET metadata = relationships.metadata || $4
                RETURNING id
            """, source_id, target_id, relationship_type, metadata or {})
            return str(row["id"])
    
    async def get_relationships(
        self,
        entity_id: str,
        relationship_type: str = None,
        direction: str = "both",
    ) -> list[dict]:
        """Get relationships for entity."""
        async with self._pool.acquire() as conn:
            conditions = []
            params = [entity_id]
            
            if direction in ("outbound", "both"):
                conditions.append("source_id = $1")
            if direction in ("inbound", "both"):
                conditions.append("target_id = $1")
            
            where = " OR ".join(conditions)
            
            if relationship_type:
                where = f"({where}) AND relationship_type = ${len(params) + 1}"
                params.append(relationship_type)
            
            rows = await conn.fetch(f"""
                SELECT 
                    r.*,
                    se.primary_name as source_name,
                    te.primary_name as target_name
                FROM relationships r
                JOIN entities se ON r.source_id = se.id
                JOIN entities te ON r.target_id = te.id
                WHERE {where}
            """, *params)
            
            return [dict(row) for row in rows]
    
    async def listen_changes(self, callback):
        """Listen for entity changes (for webhooks)."""
        async with self._pool.acquire() as conn:
            await conn.add_listener("entity_changes", callback)
```

---

## Tier 3+: Elasticsearch Integration

Full-text search and analytics.

```python
# entity_master/storage/elasticsearch.py

from elasticsearch import AsyncElasticsearch
from typing import Optional
from entity_master.storage.base import BaseStorage


class ElasticsearchStorage(BaseStorage):
    """Elasticsearch for advanced search (complements SQL storage).
    
    Use alongside PostgreSQL:
    - Postgres: Source of truth, ACID compliance
    - Elasticsearch: Search, autocomplete, analytics
    """
    
    def __init__(
        self,
        hosts: list[str] = ["http://localhost:9200"],
        index_name: str = "entity_master",
    ):
        self.client = AsyncElasticsearch(hosts=hosts)
        self.index_name = index_name
    
    async def initialize(self):
        """Create index with mappings."""
        if not await self.client.indices.exists(index=self.index_name):
            await self.client.indices.create(
                index=self.index_name,
                body={
                    "settings": {
                        "number_of_shards": 1,
                        "analysis": {
                            "analyzer": {
                                "entity_analyzer": {
                                    "type": "custom",
                                    "tokenizer": "standard",
                                    "filter": ["lowercase", "asciifolding", "edge_ngram_filter"]
                                }
                            },
                            "filter": {
                                "edge_ngram_filter": {
                                    "type": "edge_ngram",
                                    "min_gram": 2,
                                    "max_gram": 20
                                }
                            }
                        }
                    },
                    "mappings": {
                        "properties": {
                            "id": {"type": "keyword"},
                            "entity_type": {"type": "keyword"},
                            "primary_name": {
                                "type": "text",
                                "analyzer": "entity_analyzer",
                                "fields": {
                                    "keyword": {"type": "keyword"},
                                    "suggest": {
                                        "type": "completion",
                                        "analyzer": "simple"
                                    }
                                }
                            },
                            "status": {"type": "keyword"},
                            "identifiers": {
                                "type": "nested",
                                "properties": {
                                    "scheme": {"type": "keyword"},
                                    "value": {"type": "keyword"}
                                }
                            },
                            "aliases": {"type": "text", "analyzer": "entity_analyzer"},
                            "metadata": {"type": "object", "enabled": True},
                            "created_at": {"type": "date"},
                            "updated_at": {"type": "date"}
                        }
                    }
                }
            )
    
    async def search(
        self,
        query: str,
        entity_type: str = None,
        limit: int = 10,
    ) -> list[dict]:
        """Advanced multi-field search."""
        must = [
            {
                "multi_match": {
                    "query": query,
                    "fields": ["primary_name^3", "aliases^2", "identifiers.value"],
                    "type": "best_fields",
                    "fuzziness": "AUTO"
                }
            }
        ]
        
        if entity_type:
            must.append({"term": {"entity_type": entity_type}})
        
        response = await self.client.search(
            index=self.index_name,
            body={
                "query": {"bool": {"must": must}},
                "size": limit,
                "highlight": {
                    "fields": {
                        "primary_name": {},
                        "aliases": {}
                    }
                }
            }
        )
        
        return [
            {**hit["_source"], "_score": hit["_score"], "_highlight": hit.get("highlight")}
            for hit in response["hits"]["hits"]
        ]
    
    async def autocomplete(
        self,
        prefix: str,
        limit: int = 10,
    ) -> list[str]:
        """Fast autocomplete using completion suggester."""
        response = await self.client.search(
            index=self.index_name,
            body={
                "suggest": {
                    "entity_suggest": {
                        "prefix": prefix,
                        "completion": {
                            "field": "primary_name.suggest",
                            "size": limit,
                            "skip_duplicates": True
                        }
                    }
                }
            }
        )
        
        suggestions = response["suggest"]["entity_suggest"][0]["options"]
        return [s["text"] for s in suggestions]
    
    async def sync_from_postgres(self, postgres_storage):
        """Sync entities from PostgreSQL to Elasticsearch."""
        async for entity in postgres_storage.list_entities():
            await self.client.index(
                index=self.index_name,
                id=entity["id"],
                body=entity,
            )
```

---

## Storage Factory

```python
# entity_master/storage/__init__.py

from typing import Literal
from entity_master.storage.base import BaseStorage
from entity_master.storage.sqlite import SQLiteStorage
from entity_master.storage.duckdb import DuckDBStorage
from entity_master.storage.postgres import PostgresStorage
from entity_master.storage.elasticsearch import ElasticsearchStorage


def create_storage(
    tier: Literal["basic", "intermediate", "advanced", "full", "mindblowing"],
    **config,
) -> BaseStorage:
    """Factory function to create appropriate storage backend."""
    
    if tier == "basic":
        return SQLiteStorage(
            db_path=config.get("db_path", "~/.entity_master/entities.db")
        )
    
    elif tier == "intermediate":
        return DuckDBStorage(
            db_path=config.get("db_path", "~/.entity_master/entities.duckdb")
        )
    
    elif tier in ("advanced", "full", "mindblowing"):
        storage = PostgresStorage(
            dsn=config.get("postgres_dsn", "postgresql://localhost/entity_master")
        )
        
        # Advanced tier adds Elasticsearch
        if tier in ("advanced", "full", "mindblowing") and config.get("elasticsearch_hosts"):
            es_storage = ElasticsearchStorage(
                hosts=config.get("elasticsearch_hosts", ["http://localhost:9200"])
            )
            # Return composite storage that writes to both
            return CompositeStorage(primary=storage, search=es_storage)
        
        return storage
    
    else:
        raise ValueError(f"Unknown tier: {tier}")


class CompositeStorage(BaseStorage):
    """Combines SQL storage with Elasticsearch."""
    
    def __init__(self, primary: BaseStorage, search: ElasticsearchStorage):
        self.primary = primary
        self.search = search
    
    async def upsert_entity(self, entity: dict) -> str:
        """Write to both storages."""
        entity_id = await self.primary.upsert_entity(entity)
        await self.search.client.index(
            index=self.search.index_name,
            id=entity_id,
            body=entity,
        )
        return entity_id
    
    async def search(self, query: str, **kwargs) -> list[dict]:
        """Use Elasticsearch for search."""
        return await self.search.search(query, **kwargs)
```
