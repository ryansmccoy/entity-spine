# EntitySpine - Unified Design Document

**Version: 2.1 | Consolidated from v1 and v2 designs**

---

## Executive Summary

EntitySpine is a **lightweight, modular entity resolution library** for financial data.

### Core Value Proposition

```python
from entityspine import EntityResolver

resolver = EntityResolver()
entity = resolver.resolve("AAPL")  # or "320193" or "Apple Inc"
```

**One function. Any identifier. Canonical entity.**

---

## Design Principles

### 1. Zero Dependencies by Default

Tier 0 and Tier 1 use **only Python stdlib**:
- JSON parsing: `json`
- SQLite: `sqlite3`  
- ULID generation: Custom implementation
- HTTP: `urllib.request`

### 2. Progressive Enhancement

```
Tier 0: JSON only      → Scripts, CLI tools
Tier 1: SQLite         → Local development  
Tier 2: DuckDB         → Analytics workloads
Tier 3: PostgreSQL     → Production services
```

### 3. Same API, Different Backends

```python
# All use identical API
resolver = EntityResolver()                           # JSON
resolver = EntityResolver(db_path="entities.db")      # SQLite
resolver = EntityResolver(backend="duckdb")           # DuckDB
resolver = EntityResolver(backend="postgres", dsn=...) # PostgreSQL
```

### 4. Entity/Security/Listing Hierarchy

**Critical distinction** - these are NOT the same:

| Object | Scope | Identifiers | Example |
|--------|-------|-------------|---------|
| **Entity** | Issuer/Org | CIK, LEI | Apple Inc |
| **Security** | Instrument | ISIN, CUSIP | AAPL common stock |
| **Listing** | Trading venue | Ticker+MIC | AAPL on XNAS |

**Tier 0-2**: Flattened (SimpleEntity with CIK, ticker, name)  
**Tier 3**: Full hierarchy (Entity → Security → Listing)

---

## Data Model

### SimpleEntity (Tier 0-2)

```python
@dataclass
class SimpleEntity:
    """Lightweight entity for JSON/SQLite tiers."""
    cik: str              # "0000320193" (10-digit padded)
    ticker: str           # "AAPL"
    name: str             # "Apple Inc."
    exchange: str = ""    # "NASDAQ" (optional)
```

### Full Entity (Tier 3)

```python
@dataclass
class Entity:
    """Full entity with all metadata."""
    entity_id: str        # ULID "01ARZ3NDEKTSV4RRFFQ69G5FAV"
    entity_type: EntityType
    status: EntityStatus
    legal_name: str
    primary_name: str
    identifiers: dict[str, list[str]]  # {"cik": ["0000320193"], "lei": [...]}
    aliases: list[str]
    jurisdiction_country: str
    sic_code: str
    created_at: datetime
    updated_at: datetime
```

---

## Storage Tiers

### Tier 0: JSON File

**Dependencies**: None (stdlib only)  
**Data Source**: SEC `company_tickers.json`  
**Capabilities**: Read-only lookups

```python
# Auto-downloads and caches SEC data
resolver = EntityResolver()
```

**Storage**: In-memory dict loaded from JSON

### Tier 1: SQLite

**Dependencies**: None (stdlib `sqlite3`)  
**Capabilities**: Read/write, persistence, search

```python
resolver = EntityResolver(db_path="entities.db")
resolver.add_alias("01ARZ3...", "Apple Computer")
```

**Schema**:
```sql
CREATE TABLE entities (
    entity_id TEXT PRIMARY KEY,
    cik TEXT UNIQUE NOT NULL,
    ticker TEXT,
    name TEXT NOT NULL,
    exchange TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_entities_cik ON entities(cik);
CREATE INDEX idx_entities_ticker ON entities(ticker);

CREATE TABLE identifiers (
    id INTEGER PRIMARY KEY,
    entity_id TEXT REFERENCES entities(entity_id),
    scheme TEXT NOT NULL,    -- 'cik', 'lei', 'ticker'
    value TEXT NOT NULL,
    UNIQUE(entity_id, scheme, value)
);

CREATE TABLE aliases (
    id INTEGER PRIMARY KEY,
    entity_id TEXT REFERENCES entities(entity_id),
    alias TEXT NOT NULL,
    alias_type TEXT DEFAULT 'alternate'  -- 'legal', 'trade', 'former'
);
```

### Tier 2: DuckDB

**Dependencies**: `pip install entityspine[duckdb]`  
**Capabilities**: Analytics, Parquet export

```python
resolver = EntityResolver(backend="duckdb", db_path="entities.duckdb")
resolver.export_parquet("entities.parquet")
```

### Tier 3: PostgreSQL

**Dependencies**: `pip install entityspine[postgres]`  
**Capabilities**: Full hierarchy, multi-user, async

```python
resolver = EntityResolver(backend="postgres", dsn="postgresql://...")
```

**Full schema** in `01_CANONICAL_DATA_MODEL.md`.

---

## Resolution Algorithm

```python
def resolve(self, query: str) -> Entity | None:
    """Resolve any identifier to canonical entity."""
    q = query.strip().upper()
    
    # 1. Try ticker (most common)
    if entity := self._store.get_by_ticker(q):
        return entity
    
    # 2. Try CIK (if numeric)
    if q.isdigit():
        if entity := self._store.get_by_cik(normalize_cik(q)):
            return entity
    
    # 3. Try other identifiers (LEI, ISIN, etc.)
    for scheme in ["lei", "isin", "cusip", "figi"]:
        if entity := self._store.get_by_identifier(scheme, q):
            return entity
    
    # 4. Try name search (fuzzy)
    results = self._store.search(q, limit=1)
    return results[0] if results else None
```

---

## Normalization Rules

### CIK
- Strip leading zeros, then pad to 10 digits
- `"320193"` → `"0000320193"`

### Ticker
- Uppercase, strip whitespace
- `" aapl "` → `"AAPL"`

### LEI
- Uppercase, strip whitespace
- Validate: 20 alphanumeric chars

### ISIN
- Uppercase, validate checksum
- Format: 2 letter country + 9 alphanum + check digit

---

## Package Structure

```
entityspine/
├── src/entityspine/
│   ├── __init__.py              # Public API
│   ├── py.typed                 # Type hints marker
│   │
│   ├── core/                    # Zero-dep utilities
│   │   ├── __init__.py
│   │   ├── config.py            # Settings
│   │   ├── exceptions.py        # Custom errors
│   │   ├── normalize.py         # ID normalization
│   │   └── ulid.py              # ULID generator
│   │
│   ├── domain/                  # Domain layer
│   │   ├── __init__.py
│   │   ├── entities/
│   │   │   ├── __init__.py
│   │   │   ├── enums.py         # EntityStatus, EntityType
│   │   │   ├── model.py         # Full Entity
│   │   │   └── simple.py        # SimpleEntity
│   │   └── resolution/
│   │       ├── __init__.py
│   │       └── resolver.py      # EntityResolver
│   │
│   └── adapters/                # Storage backends
│       ├── __init__.py
│       └── storage/
│           ├── __init__.py
│           ├── protocol.py      # EntityStore protocol
│           ├── json_store.py    # Tier 0
│           ├── sqlite_store.py  # Tier 1
│           ├── duckdb_store.py  # Tier 2
│           └── postgres_store.py # Tier 3
│
├── tests/                       # Mirrors src/
├── docs/
│   ├── design/                  # Design docs
│   ├── archive/v1/              # Old designs
│   └── PROMPT_ENTITYSPINE.md    # LLM prompt
│
├── pyproject.toml
├── Makefile
└── README.md
```

---

## Public API

```python
# entityspine/__init__.py
from entityspine.domain.entities import Entity, SimpleEntity, EntityStatus, EntityType
from entityspine.domain.resolution import EntityResolver
from entityspine.core.exceptions import (
    EntitySpineError,
    EntityNotFoundError,
    ResolutionError,
    StorageError,
)

__all__ = [
    "EntityResolver",
    "Entity",
    "SimpleEntity",
    "EntityStatus",
    "EntityType",
    "EntitySpineError",
    "EntityNotFoundError",
    "ResolutionError",
    "StorageError",
]
```

---

## Usage Examples

### Basic (Tier 0)

```python
from entityspine import EntityResolver

resolver = EntityResolver()
entity = resolver.resolve("AAPL")
print(f"{entity.name} (CIK: {entity.cik})")
# Apple Inc. (CIK: 0000320193)
```

### With Persistence (Tier 1)

```python
resolver = EntityResolver(db_path="my_entities.db")

# Add custom alias
resolver.add_alias("0000320193", "Apple Computer Inc", alias_type="former")

# Search finds it
results = resolver.search("Apple Computer")
```

### Analytics (Tier 2)

```python
resolver = EntityResolver(backend="duckdb", db_path="entities.duckdb")

# Export for external tools
resolver.export_parquet("entities.parquet")

# SQL access
df = resolver.query("SELECT * FROM entities WHERE ticker LIKE 'AA%'")
```

---

## Integration with py-sec-edgar

py-sec-edgar uses entityspine via a minimal interface:

```python
# py_sec_edgar/ports/entity_resolver.py
from typing import Protocol, Optional

class EntityResolverPort(Protocol):
    """What py-sec-edgar needs from entityspine."""
    
    def resolve_cik(self, cik: str) -> Optional[str]:
        """CIK → entity_id."""
        ...
    
    def resolve_ticker(self, ticker: str) -> Optional[str]:
        """Ticker → entity_id."""
        ...

# py_sec_edgar/core/identity.py
from entityspine import EntityResolver

_resolver = EntityResolver()

def get_entity_id(cik: str) -> str | None:
    entity = _resolver.get_by_cik(cik)
    return entity.entity_id if entity else None
```

py-sec-edgar stores `entity_id` as a foreign key reference.

---

## Migration from v1 to v2

See `16_QUICK_REFERENCE.md` for migration cheat sheet.

Key changes:
- UUIDs → ULIDs for primary keys
- Single table → Entity/Security/Listing hierarchy (Tier 3)
- Identifiers now have explicit scope enforcement

---

## Next Steps

1. **Phase 1**: Complete JSON and SQLite backends with tests
2. **Phase 2**: Add DuckDB backend
3. **Phase 3**: Full PostgreSQL with Entity/Security/Listing
4. **Phase 4**: FastAPI service (optional)

See `PROMPT_ENTITYSPINE.md` for detailed implementation guide.
