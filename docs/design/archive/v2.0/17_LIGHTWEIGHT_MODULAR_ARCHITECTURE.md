# Entity Master v2 - Lightweight & Modular Architecture

**Zero-to-Hero: From company_tickers.json to Full Enterprise Platform**

---

## Design Philosophy

### Core Principles

1. **Zero External Dependencies by Default** - Works with just `company_tickers.json` and SQLite/DuckDB
2. **Progressive Enhancement** - Add capabilities as needed, not upfront
3. **Same API, Different Backends** - Swap SQLite → PostgreSQL without code changes
4. **Library First, Service Optional** - Use as import or spin up as FastAPI service
5. **Migration Path** - Data migrates cleanly between tiers
6. **Feedspine Compatible** - Works standalone OR as Feedspine pipeline component

---

## Usage Spectrum

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                           ENTITY MASTER USAGE SPECTRUM                                   │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                          │
│  MINIMAL                                          MAXIMAL                                │
│  ───────                                          ───────                                │
│                                                                                          │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐                  │
│  │   JSON      │   │   SQLite    │   │   DuckDB    │   │   FastAPI   │                  │
│  │   File      │ → │   Local     │ → │   OLAP      │ → │   Service   │                  │
│  │   Only      │   │   Cache     │   │   Analytics │   │   + Postgres│                  │
│  └─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘                  │
│                                                                                          │
│  Dependencies:     Dependencies:     Dependencies:     Dependencies:                    │
│  - json (stdlib)   - sqlite3(stdlib) - duckdb         - fastapi                         │
│  - pathlib         - ulid            - pandas (opt)   - postgres                        │
│                                       - polars (opt)  - elasticsearch (opt)             │
│                                                       - neo4j (opt)                     │
│                                                                                          │
│  Use Case:         Use Case:         Use Case:         Use Case:                        │
│  - Read-only       - py-sec-edgar    - Analytics      - Multi-user                      │
│  - CIK→ticker      - Single user     - Batch joins    - Real-time                       │
│  - Quick scripts   - Offline         - Reporting      - Production                      │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Tier 0: JSON File Only (Zero Dependencies)

**The simplest possible entity resolver - just read company_tickers.json**

### Installation

```bash
# No extra dependencies needed!
pip install py-sec-edgar
```

### Usage

```python
from entity_master import EntityResolver

# Auto-downloads company_tickers.json if not present
resolver = EntityResolver()

# Resolve ticker → entity
entity = resolver.resolve("AAPL")
print(entity.cik)          # "0000320193"
print(entity.primary_name) # "Apple Inc."

# Reverse lookup
entity = resolver.get_by_cik("320193")
print(entity.ticker)       # "AAPL"

# Search
results = resolver.search("apple")
for e in results:
    print(f"{e.ticker}: {e.primary_name}")
```

### Implementation

```python
"""
entity_master/tier0_json.py

Zero-dependency entity resolver using only company_tickers.json.
This is the absolute minimum - no database, no external deps.
"""
import json
import urllib.request
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List, Dict


@dataclass
class SimpleEntity:
    """Minimal entity for Tier 0."""
    cik: str
    ticker: str
    name: str
    
    @property
    def primary_name(self) -> str:
        return self.name


class JSONEntityResolver:
    """
    Tier 0: Read-only resolver using only company_tickers.json.
    
    Zero external dependencies - uses only Python stdlib.
    """
    
    SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
    
    def __init__(
        self, 
        json_path: Optional[str] = None,
        auto_download: bool = True,
    ):
        """
        Initialize resolver.
        
        Args:
            json_path: Path to company_tickers.json (auto-detected if None)
            auto_download: Download from SEC if file not found
        """
        self._json_path = self._find_or_download(json_path, auto_download)
        self._data: Dict[str, SimpleEntity] = {}
        self._by_cik: Dict[str, SimpleEntity] = {}
        self._by_ticker: Dict[str, SimpleEntity] = {}
        self._by_name: Dict[str, SimpleEntity] = {}
        self._loaded = False
    
    def _find_or_download(
        self, 
        json_path: Optional[str],
        auto_download: bool,
    ) -> Path:
        """Find existing file or download from SEC."""
        # Check explicit path
        if json_path:
            p = Path(json_path)
            if p.exists():
                return p
        
        # Check common locations
        candidates = [
            Path.cwd() / "refdata" / "company_tickers.json",
            Path.cwd() / "company_tickers.json",
            Path.home() / ".entity_master" / "company_tickers.json",
        ]
        
        for candidate in candidates:
            if candidate.exists():
                return candidate
        
        # Download if allowed
        if auto_download:
            target = Path.home() / ".entity_master" / "company_tickers.json"
            target.parent.mkdir(parents=True, exist_ok=True)
            
            print(f"Downloading company_tickers.json from SEC...")
            headers = {"User-Agent": "entity-master/1.0 (research)"}
            req = urllib.request.Request(self.SEC_TICKERS_URL, headers=headers)
            
            with urllib.request.urlopen(req) as response:
                data = response.read()
                target.write_bytes(data)
            
            return target
        
        raise FileNotFoundError(
            "company_tickers.json not found. Set json_path or enable auto_download."
        )
    
    def _ensure_loaded(self):
        """Lazy load data on first access."""
        if self._loaded:
            return
        
        with open(self._json_path, 'r') as f:
            raw = json.load(f)
        
        # Parse SEC format: {"0": {"cik_str": "...", "ticker": "...", "title": "..."}, ...}
        for _, item in raw.items():
            cik = item["cik_str"].lstrip("0") or "0"  # Normalize CIK
            entity = SimpleEntity(
                cik=cik,
                ticker=item["ticker"],
                name=item["title"],
            )
            
            self._by_cik[cik] = entity
            self._by_cik[item["cik_str"]] = entity  # Also store padded
            self._by_ticker[item["ticker"].upper()] = entity
            self._by_name[item["title"].upper()] = entity
        
        self._loaded = True
    
    def resolve(self, query: str) -> Optional[SimpleEntity]:
        """
        Resolve any identifier (ticker, CIK, or name) to entity.
        """
        self._ensure_loaded()
        
        q = query.strip()
        
        # Try ticker (most common)
        if q.upper() in self._by_ticker:
            return self._by_ticker[q.upper()]
        
        # Try CIK (with and without leading zeros)
        if q.isdigit():
            cik = q.lstrip("0") or "0"
            if cik in self._by_cik:
                return self._by_cik[cik]
        
        # Try exact name match
        if q.upper() in self._by_name:
            return self._by_name[q.upper()]
        
        return None
    
    def get_by_cik(self, cik: str) -> Optional[SimpleEntity]:
        """Get entity by CIK."""
        self._ensure_loaded()
        cik_clean = cik.lstrip("0") or "0"
        return self._by_cik.get(cik_clean)
    
    def get_by_ticker(self, ticker: str) -> Optional[SimpleEntity]:
        """Get entity by ticker symbol."""
        self._ensure_loaded()
        return self._by_ticker.get(ticker.upper())
    
    def search(self, query: str, limit: int = 10) -> List[SimpleEntity]:
        """
        Search entities by partial name/ticker match.
        """
        self._ensure_loaded()
        
        q = query.upper()
        results = []
        
        # Search tickers
        for ticker, entity in self._by_ticker.items():
            if q in ticker:
                results.append(entity)
                if len(results) >= limit:
                    return results
        
        # Search names
        for name, entity in self._by_name.items():
            if q in name and entity not in results:
                results.append(entity)
                if len(results) >= limit:
                    return results
        
        return results
    
    def all_entities(self) -> List[SimpleEntity]:
        """Get all entities."""
        self._ensure_loaded()
        return list(set(self._by_cik.values()))
    
    @property
    def entity_count(self) -> int:
        """Number of entities loaded."""
        self._ensure_loaded()
        return len(set(self._by_cik.values()))


# =============================================================================
# Public API (same interface for all tiers)
# =============================================================================

# Default resolver - auto-selects best available backend
def EntityResolver(**kwargs) -> 'JSONEntityResolver':
    """
    Create entity resolver with best available backend.
    
    Tier 0 (JSON) is always available.
    Higher tiers activate when their dependencies are installed.
    """
    # For now, always return JSON resolver
    # Higher tiers will be added as optional imports
    return JSONEntityResolver(**kwargs)
```

### py-sec-edgar Integration

```python
# In py_sec_edgar_v2/src/py_sec_edgar/filings/search.py

from entity_master import EntityResolver

class FilingSearch:
    def __init__(self):
        # Entity resolver auto-detects best backend
        self._entity_resolver = EntityResolver()
    
    def resolve_ticker(self, ticker: str) -> Optional[str]:
        """Resolve ticker to CIK."""
        entity = self._entity_resolver.resolve(ticker)
        return entity.cik if entity else None
    
    def search_by_ticker(self, tickers: List[str], **kwargs) -> List[Filing]:
        """Search filings by ticker symbol."""
        ciks = []
        for ticker in tickers:
            entity = self._entity_resolver.resolve(ticker)
            if entity:
                ciks.append(entity.cik.zfill(10))
        
        return self.search(ciks=ciks, **kwargs)
```

---

## Tier 1: SQLite Cache (Zero External Deps Still)

**Add write capability and indexing without external dependencies**

### When to Use
- Need to cache enrichments (LEI, SIC codes, etc.)
- Want faster repeated lookups
- Single user, local development

### Upgrade Path

```python
from entity_master import EntityResolver

# Upgrade from Tier 0 → Tier 1 by specifying db_path
resolver = EntityResolver(db_path="entity_master.db")

# First call migrates company_tickers.json to SQLite
entity = resolver.resolve("AAPL")

# Now you can add enrichments
resolver.add_identifier(entity.entity_id, "lei", "HWUPKR0MPOU8FGXBT394")
resolver.add_alias(entity.entity_id, "Apple Computer, Inc.", alias_type="former")
```

### Implementation

```python
"""
entity_master/tier1_sqlite.py

SQLite-backed entity resolver.
Still zero external dependencies (sqlite3 is stdlib).
"""
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional, List
from contextlib import contextmanager

from .tier0_json import JSONEntityResolver, SimpleEntity
from .core.types import Entity
from .core.ulid import generate_ulid  # Simple ULID generator (no deps)


class SQLiteEntityResolver(JSONEntityResolver):
    """
    Tier 1: SQLite-backed resolver with write capabilities.
    
    Extends Tier 0 JSON resolver:
    - All read operations work immediately
    - Writes go to SQLite
    - Can migrate JSON data to SQLite
    """
    
    SCHEMA = """
    CREATE TABLE IF NOT EXISTS entities (
        entity_id TEXT PRIMARY KEY,
        primary_name TEXT NOT NULL,
        entity_type TEXT DEFAULT 'organization',
        status TEXT DEFAULT 'active',
        cik TEXT,
        lei TEXT,
        ticker TEXT,
        jurisdiction TEXT,
        sic_code TEXT,
        created_at TEXT DEFAULT (datetime('now')),
        updated_at TEXT DEFAULT (datetime('now'))
    );
    
    CREATE TABLE IF NOT EXISTS identifiers (
        identifier_id TEXT PRIMARY KEY,
        entity_id TEXT NOT NULL,
        scheme TEXT NOT NULL,
        value TEXT NOT NULL,
        valid_from TEXT,
        valid_to TEXT,
        created_at TEXT DEFAULT (datetime('now')),
        UNIQUE(scheme, value),
        FOREIGN KEY (entity_id) REFERENCES entities(entity_id)
    );
    
    CREATE TABLE IF NOT EXISTS aliases (
        alias_id TEXT PRIMARY KEY,
        entity_id TEXT NOT NULL,
        alias_name TEXT NOT NULL,
        alias_type TEXT DEFAULT 'alternate',
        created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (entity_id) REFERENCES entities(entity_id)
    );
    
    CREATE INDEX IF NOT EXISTS idx_entities_cik ON entities(cik);
    CREATE INDEX IF NOT EXISTS idx_entities_ticker ON entities(ticker);
    CREATE INDEX IF NOT EXISTS idx_identifiers_scheme_value ON identifiers(scheme, value);
    CREATE INDEX IF NOT EXISTS idx_aliases_name ON aliases(alias_name);
    """
    
    def __init__(
        self,
        db_path: str = "entity_master.db",
        json_path: Optional[str] = None,
        auto_migrate: bool = True,
    ):
        super().__init__(json_path=json_path, auto_download=True)
        self.db_path = Path(db_path)
        self._init_db()
        
        if auto_migrate and self._is_empty():
            self._migrate_from_json()
    
    def _init_db(self):
        """Initialize SQLite database."""
        with self._connection() as conn:
            conn.executescript(self.SCHEMA)
    
    @contextmanager
    def _connection(self):
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()
    
    def _is_empty(self) -> bool:
        """Check if database is empty."""
        with self._connection() as conn:
            count = conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
            return count == 0
    
    def _migrate_from_json(self):
        """Migrate company_tickers.json data to SQLite."""
        self._ensure_loaded()  # Load JSON data
        
        with self._connection() as conn:
            for entity in self.all_entities():
                entity_id = generate_ulid()
                
                conn.execute("""
                    INSERT INTO entities (entity_id, primary_name, cik, ticker)
                    VALUES (?, ?, ?, ?)
                """, (entity_id, entity.name, entity.cik, entity.ticker))
                
                # Add CIK identifier
                conn.execute("""
                    INSERT OR IGNORE INTO identifiers (identifier_id, entity_id, scheme, value)
                    VALUES (?, ?, 'cik', ?)
                """, (generate_ulid(), entity_id, entity.cik.zfill(10)))
                
                # Add ticker identifier
                conn.execute("""
                    INSERT OR IGNORE INTO identifiers (identifier_id, entity_id, scheme, value)
                    VALUES (?, ?, 'ticker', ?)
                """, (generate_ulid(), entity_id, entity.ticker))
    
    def resolve(self, query: str) -> Optional[Entity]:
        """Resolve any identifier to entity."""
        with self._connection() as conn:
            # Try by identifier
            row = conn.execute("""
                SELECT e.* FROM entities e
                JOIN identifiers i ON i.entity_id = e.entity_id
                WHERE UPPER(i.value) = UPPER(?)
            """, (query,)).fetchone()
            
            if row:
                return self._row_to_entity(row)
            
            # Try by alias
            row = conn.execute("""
                SELECT e.* FROM entities e
                JOIN aliases a ON a.entity_id = e.entity_id
                WHERE UPPER(a.alias_name) = UPPER(?)
            """, (query,)).fetchone()
            
            if row:
                return self._row_to_entity(row)
            
            # Try direct CIK/ticker lookup
            row = conn.execute("""
                SELECT * FROM entities
                WHERE UPPER(cik) = UPPER(?) OR UPPER(ticker) = UPPER(?)
            """, (query, query)).fetchone()
            
            return self._row_to_entity(row) if row else None
    
    def add_identifier(
        self, 
        entity_id: str, 
        scheme: str, 
        value: str,
        valid_from: Optional[str] = None,
        valid_to: Optional[str] = None,
    ) -> str:
        """Add identifier to entity."""
        identifier_id = generate_ulid()
        with self._connection() as conn:
            conn.execute("""
                INSERT INTO identifiers (identifier_id, entity_id, scheme, value, valid_from, valid_to)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (identifier_id, entity_id, scheme, value, valid_from, valid_to))
        return identifier_id
    
    def add_alias(
        self,
        entity_id: str,
        alias_name: str,
        alias_type: str = "alternate",
    ) -> str:
        """Add alias to entity."""
        alias_id = generate_ulid()
        with self._connection() as conn:
            conn.execute("""
                INSERT INTO aliases (alias_id, entity_id, alias_name, alias_type)
                VALUES (?, ?, ?, ?)
            """, (alias_id, entity_id, alias_name, alias_type))
        return alias_id
    
    def _row_to_entity(self, row: sqlite3.Row) -> Entity:
        """Convert database row to Entity object."""
        return Entity(
            entity_id=row["entity_id"],
            primary_name=row["primary_name"],
            cik=row["cik"],
            ticker=row["ticker"],
            lei=row.get("lei"),
            status=row.get("status", "active"),
        )
```

---

## Tier 2: DuckDB Analytics

**Add analytical queries without heavyweight RDBMS**

### When to Use
- Need joins with filing data
- Analytical/OLAP queries
- Batch processing of large datasets
- Already using DuckDB for py-sec-edgar filings

### Installation

```bash
pip install entity-master[analytics]
# or
pip install duckdb
```

### Usage

```python
from entity_master import EntityResolver

# Upgrade to DuckDB
resolver = EntityResolver(backend="duckdb", db_path="entities.duckdb")

# All Tier 0/1 methods work
entity = resolver.resolve("AAPL")

# Plus analytical queries
df = resolver.query("""
    SELECT e.ticker, e.primary_name, COUNT(f.filing_id) as filing_count
    FROM entities e
    JOIN filings f ON f.cik = e.cik
    WHERE e.sic_code LIKE '73%'
    GROUP BY e.ticker, e.primary_name
    ORDER BY filing_count DESC
    LIMIT 20
""")

# Join with external parquet
resolver.attach_parquet("filings", "sec_data/filings/*.parquet")
```

---

## Tier 3: FastAPI Service

**Run Entity Master as standalone microservice**

### When to Use
- Multi-user access
- Need REST/GraphQL API
- Production deployment
- Integrate with non-Python systems

### Installation

```bash
pip install entity-master[service]
# Installs: fastapi, uvicorn, pydantic
```

### Start Service

```bash
# Minimal: SQLite backend
entity-master serve --port 8000

# Production: PostgreSQL
entity-master serve --backend postgres --dsn "postgresql://localhost/entity_master"

# Full stack: PostgreSQL + Elasticsearch
entity-master serve --backend postgres --dsn "..." --search elasticsearch --search-url "http://localhost:9200"
```

### API Endpoints

```
GET  /health                          Health check
GET  /entities/{entity_id}            Get entity by ID
GET  /resolve?q={query}               Resolve identifier
GET  /search?q={query}&limit=10       Search entities
POST /entities                        Create entity
PUT  /entities/{entity_id}            Update entity
POST /entities/{entity_id}/identifiers  Add identifier
POST /entities/{entity_id}/aliases    Add alias
GET  /entities/{entity_id}/securities List securities
POST /relationships                   Add relationship
```

### FastAPI Implementation

```python
"""
entity_master/api/app.py

FastAPI application for Entity Master service.
"""
from fastapi import FastAPI, HTTPException, Depends
from typing import Optional, List
from pydantic import BaseModel

from entity_master import EntityResolver
from entity_master.config import settings


app = FastAPI(
    title="Entity Master",
    description="Lightweight entity resolution service",
    version="2.0.0",
)


# =============================================================================
# Dependency Injection
# =============================================================================

def get_resolver() -> EntityResolver:
    """Get entity resolver based on config."""
    return EntityResolver(
        backend=settings.backend,
        db_path=settings.db_path,
        dsn=settings.dsn,
    )


# =============================================================================
# Models
# =============================================================================

class EntityResponse(BaseModel):
    entity_id: str
    primary_name: str
    entity_type: str = "organization"
    status: str = "active"
    cik: Optional[str] = None
    lei: Optional[str] = None
    ticker: Optional[str] = None


class ResolutionResponse(BaseModel):
    success: bool
    entity: Optional[EntityResponse] = None
    candidates: List[EntityResponse] = []
    error: Optional[str] = None


# =============================================================================
# Endpoints
# =============================================================================

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/resolve", response_model=ResolutionResponse)
async def resolve(
    q: str,
    resolver: EntityResolver = Depends(get_resolver),
):
    """Resolve any identifier (CIK, ticker, name) to entity."""
    entity = resolver.resolve(q)
    
    if entity:
        return ResolutionResponse(
            success=True,
            entity=EntityResponse(**entity.__dict__),
        )
    
    # Try fuzzy search for candidates
    candidates = resolver.search(q, limit=5)
    return ResolutionResponse(
        success=False,
        candidates=[EntityResponse(**c.__dict__) for c in candidates],
        error=f"No exact match for '{q}'",
    )


@app.get("/entities/{entity_id}", response_model=EntityResponse)
async def get_entity(
    entity_id: str,
    resolver: EntityResolver = Depends(get_resolver),
):
    """Get entity by ID."""
    entity = resolver.get_entity(entity_id)
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    return EntityResponse(**entity.__dict__)


@app.get("/search")
async def search(
    q: str,
    limit: int = 10,
    resolver: EntityResolver = Depends(get_resolver),
):
    """Search entities by name or ticker."""
    results = resolver.search(q, limit=limit)
    return [EntityResponse(**e.__dict__) for e in results]
```

---

## Module Structure

```
entity_master/
├── __init__.py                  # Public API: EntityResolver, Entity, etc.
├── py.typed                     # PEP 561 marker
│
├── core/                        # Core types (zero deps)
│   ├── __init__.py
│   ├── types.py                 # Entity, Security, Listing dataclasses
│   ├── ulid.py                  # Simple ULID generator (no deps)
│   └── normalization.py         # Name normalization
│
├── storage/                     # Storage backends
│   ├── __init__.py              # Auto-selects best available
│   ├── base.py                  # Abstract interface
│   ├── json_store.py            # Tier 0: JSON only
│   ├── sqlite_store.py          # Tier 1: SQLite
│   ├── duckdb_store.py          # Tier 2: DuckDB (optional)
│   └── postgres_store.py        # Tier 3: PostgreSQL (optional)
│
├── resolution/                  # Resolution logic
│   ├── __init__.py
│   ├── resolver.py              # Main EntityResolver class
│   └── strategies.py            # Resolution strategies
│
├── api/                         # FastAPI service (optional)
│   ├── __init__.py
│   ├── app.py                   # FastAPI app
│   ├── routes/
│   │   ├── entities.py
│   │   ├── resolution.py
│   │   └── search.py
│   └── models.py                # Pydantic models
│
├── migrations/                  # Schema migrations
│   ├── sqlite/
│   │   └── 001_initial.sql
│   ├── duckdb/
│   │   └── 001_initial.sql
│   └── postgres/
│       └── 001_initial.sql
│
├── feedspine/                   # Feedspine integration (optional)
│   ├── __init__.py
│   ├── sec_tickers_feed.py      # company_tickers.json feed
│   └── gleif_feed.py            # LEI feed
│
├── cli.py                       # CLI commands
└── config.py                    # Settings
```

---

## Installation Options

```toml
# pyproject.toml

[project]
name = "entity-master"
version = "2.0.0"
description = "Lightweight entity resolution for SEC EDGAR and beyond"

dependencies = [
    # Zero required deps for Tier 0/1
]

[project.optional-dependencies]
# Tier 2: Analytics
analytics = [
    "duckdb>=0.9.0",
]

# Tier 3: Service
service = [
    "fastapi>=0.100.0",
    "uvicorn>=0.23.0",
    "pydantic>=2.0.0",
]

# Tier 3+: PostgreSQL
postgres = [
    "asyncpg>=0.28.0",
    "psycopg[binary]>=3.1.0",
]

# Tier 4: Search
search = [
    "elasticsearch>=8.0.0",
]

# Tier 5: Graph
graph = [
    "neo4j>=5.0.0",
]

# Full install
full = [
    "entity-master[analytics,service,postgres,search,graph]",
]

# Development
dev = [
    "pytest>=7.0.0",
    "pytest-asyncio>=0.21.0",
    "httpx>=0.24.0",  # For testing FastAPI
]
```

---

## py-sec-edgar v4 Integration

### Backward Compatible Import

```python
# py_sec_edgar_v4/entity_resolver.py
# DEPRECATED: Use entity_master directly

import warnings
from entity_master import EntityResolver as _EntityResolver

warnings.warn(
    "Importing from py_sec_edgar.entity_resolver is deprecated. "
    "Use 'from entity_master import EntityResolver' instead.",
    DeprecationWarning,
    stacklevel=2,
)

EntityResolver = _EntityResolver
```

### Integration in FilingSearch

```python
# py_sec_edgar_v4/filings/search.py

from typing import Optional, List
from datetime import date

# Try entity_master, fall back to inline resolver
try:
    from entity_master import EntityResolver
    ENTITY_MASTER_AVAILABLE = True
except ImportError:
    ENTITY_MASTER_AVAILABLE = False


class FilingSearch:
    def __init__(self, data_dir: str = "sec_data"):
        self.data_dir = Path(data_dir)
        self._entity_resolver = None
    
    @property
    def entity_resolver(self):
        """Lazy-load entity resolver."""
        if self._entity_resolver is None:
            if ENTITY_MASTER_AVAILABLE:
                self._entity_resolver = EntityResolver()
            else:
                # Fallback to inline JSON resolver
                self._entity_resolver = self._create_inline_resolver()
        return self._entity_resolver
    
    def resolve_ticker(self, ticker: str) -> Optional[str]:
        """Resolve ticker to CIK."""
        entity = self.entity_resolver.resolve(ticker)
        return entity.cik.zfill(10) if entity else None
    
    def search_by_ticker(
        self,
        tickers: List[str],
        forms: Optional[List[str]] = None,
        **kwargs,
    ) -> List[Filing]:
        """Search filings by ticker symbols."""
        ciks = []
        for ticker in tickers:
            cik = self.resolve_ticker(ticker)
            if cik:
                ciks.append(cik)
            else:
                self.logger.warning(f"Could not resolve ticker: {ticker}")
        
        if not ciks:
            return []
        
        return self.search(ciks=ciks, forms=forms, **kwargs)
```

---

## Migration Paths

### Tier 0 → Tier 1

```python
# Automatic migration when specifying db_path
resolver = EntityResolver(db_path="entities.db")
# JSON data is auto-migrated to SQLite
```

### Tier 1 → Tier 2

```python
# Export from SQLite
from entity_master.migrations import migrate

migrate(
    source="entities.db",           # SQLite source
    target="entities.duckdb",       # DuckDB target
    backend="duckdb",
)
```

### Tier 1/2 → Tier 3

```python
# Export to PostgreSQL
migrate(
    source="entities.db",
    target="postgresql://localhost/entity_master",
    backend="postgres",
)
```

### CLI Migration

```bash
# Migrate SQLite → DuckDB
entity-master migrate --source entities.db --target entities.duckdb --backend duckdb

# Migrate to PostgreSQL
entity-master migrate --source entities.db --target "postgresql://localhost/entity_master"

# Export to JSON (for backup/sharing)
entity-master export --source entities.db --format json --output entities_export.json
```

---

## Questions to Consider

1. **Feedspine Integration Depth**
   - Should Entity Master BE a Feedspine pipeline?
   - Or should it use Feedspine for data ingestion only?
   - Recommendation: Both - can run standalone OR as Feedspine plugin

2. **Where to Host Entity Master Code?**
   - Option A: Inside py-sec-edgar as submodule
   - Option B: Separate package `entity-master`
   - Option C: Inside feedspine
   - Recommendation: **Option B** - separate package, can be used by both

3. **Async vs Sync API**
   - Tier 0-2: Sync is fine (local files)
   - Tier 3+: Async for FastAPI
   - Recommendation: Dual API with `sync` and `async` variants

4. **Graph Database (Neo4j)**
   - When does relationship tracking warrant Neo4j?
   - Alternative: PostgreSQL recursive CTEs for simple graphs
   - Recommendation: PostgreSQL first, Neo4j as optional Tier 5

5. **Vector Search**
   - For fuzzy name matching: pgvector vs. dedicated vector DB?
   - Recommendation: pgvector for Tier 3, optional Pinecone/Milvus for Tier 5

---

## Next Steps

1. **Create `entity-master` package** with Tier 0 + Tier 1
2. **Update py-sec-edgar v4** to use entity-master for ticker resolution
3. **Add Feedspine feed** for company_tickers.json ingestion
4. **Build FastAPI service** for multi-user deployments
5. **Create migration tools** for tier upgrades

---

*Document version: 1.0.0*
*Last updated: 2025-01-25*
