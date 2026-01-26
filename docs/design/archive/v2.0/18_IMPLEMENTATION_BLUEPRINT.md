# Entity Master - Implementation Blueprint

**Concrete code structure for the lightweight modular architecture**

---

## Package Layout

```
entity_master/
├── __init__.py                      # Public API
├── py.typed                         # Type hints marker
├── version.py                       # Version string
│
├── core/                            # Zero-dependency core
│   ├── __init__.py
│   ├── types.py                     # Entity, SimpleEntity dataclasses
│   ├── ulid.py                      # ULID generator (stdlib only)
│   ├── normalize.py                 # Name normalization
│   └── exceptions.py                # Custom exceptions
│
├── storage/                         # Storage backends
│   ├── __init__.py                  # Backend factory
│   ├── protocol.py                  # Abstract protocol
│   ├── json_backend.py              # Tier 0: JSON file
│   ├── sqlite_backend.py            # Tier 1: SQLite
│   ├── duckdb_backend.py            # Tier 2: DuckDB (optional)
│   └── postgres_backend.py          # Tier 3: PostgreSQL (optional)
│
├── resolver.py                      # Main EntityResolver class
├── config.py                        # Configuration
└── cli.py                           # CLI interface
```

---

## Core Implementation

### [__init__.py] - Public API

```python
"""
Entity Master - Lightweight Entity Resolution

Tiers:
- Tier 0: JSON file only (zero deps)
- Tier 1: SQLite (stdlib only)
- Tier 2: DuckDB (optional)
- Tier 3: PostgreSQL + FastAPI (optional)

Usage:
    from entity_master import EntityResolver
    
    resolver = EntityResolver()
    entity = resolver.resolve("AAPL")
    print(entity.cik)  # "0000320193"
"""

from .version import __version__
from .core.types import Entity, SimpleEntity
from .resolver import EntityResolver
from .core.exceptions import EntityNotFoundError, ResolutionError

__all__ = [
    "__version__",
    "EntityResolver",
    "Entity",
    "SimpleEntity",
    "EntityNotFoundError",
    "ResolutionError",
]
```

### [core/types.py] - Core Types

```python
"""Core domain types."""

from dataclasses import dataclass, field
from typing import Optional, Dict, List
from datetime import date, datetime
from enum import Enum


class EntityStatus(Enum):
    ACTIVE = "active"
    PROVISIONAL = "provisional"
    MERGED = "merged"
    INACTIVE = "inactive"


class EntityType(Enum):
    ORGANIZATION = "organization"
    PERSON = "person"
    GOVERNMENT = "government"
    FUND = "fund"


@dataclass
class SimpleEntity:
    """
    Minimal entity representation for Tier 0.
    Only contains data from company_tickers.json.
    """
    cik: str
    ticker: str
    name: str
    
    @property
    def primary_name(self) -> str:
        return self.name
    
    @property
    def cik_padded(self) -> str:
        return self.cik.zfill(10)


@dataclass
class Entity:
    """
    Full entity representation for Tier 1+.
    """
    entity_id: str
    primary_name: str
    entity_type: EntityType = EntityType.ORGANIZATION
    status: EntityStatus = EntityStatus.ACTIVE
    
    # Common identifiers (denormalized for convenience)
    cik: Optional[str] = None
    lei: Optional[str] = None
    ein: Optional[str] = None
    ticker: Optional[str] = None
    
    # Additional info
    jurisdiction: Optional[str] = None
    sic_code: Optional[str] = None
    incorporation_date: Optional[date] = None
    
    # All identifiers
    identifiers: Dict[str, str] = field(default_factory=dict)
    
    # All aliases
    aliases: List[str] = field(default_factory=list)
    
    # Timestamps
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    @property
    def cik_padded(self) -> str:
        return self.cik.zfill(10) if self.cik else None
    
    def to_simple(self) -> SimpleEntity:
        """Convert to SimpleEntity for backward compat."""
        return SimpleEntity(
            cik=self.cik or "",
            ticker=self.ticker or "",
            name=self.primary_name,
        )
```

### [core/ulid.py] - ULID Generator (No External Deps)

```python
"""
Minimal ULID generator using only stdlib.
ULIDs are 26 characters, sortable, and don't require coordination.
"""

import time
import random
import string

ENCODING = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"  # Crockford's Base32


def generate_ulid() -> str:
    """
    Generate a ULID (Universally Unique Lexicographically Sortable Identifier).
    
    Format: TTTTTTTTTTRRRRRRRRRRRRRRR (26 chars)
    - T: Timestamp (10 chars, 48 bits)
    - R: Randomness (16 chars, 80 bits)
    """
    # Timestamp component (milliseconds since Unix epoch)
    timestamp_ms = int(time.time() * 1000)
    
    # Encode timestamp (10 characters)
    timestamp_chars = []
    for _ in range(10):
        timestamp_chars.append(ENCODING[timestamp_ms % 32])
        timestamp_ms //= 32
    timestamp_part = "".join(reversed(timestamp_chars))
    
    # Random component (16 characters)
    random_part = "".join(random.choice(ENCODING) for _ in range(16))
    
    return timestamp_part + random_part


def ulid_timestamp(ulid: str) -> float:
    """Extract Unix timestamp from ULID."""
    timestamp_part = ulid[:10]
    timestamp_ms = 0
    for char in timestamp_part:
        timestamp_ms = timestamp_ms * 32 + ENCODING.index(char)
    return timestamp_ms / 1000


def is_valid_ulid(value: str) -> bool:
    """Check if string is a valid ULID."""
    if len(value) != 26:
        return False
    return all(c in ENCODING for c in value.upper())
```

### [core/normalize.py] - Name Normalization

```python
"""Name normalization utilities."""

import re
import unicodedata
from typing import Optional


# Common suffixes to normalize
CORP_SUFFIXES = {
    "inc", "inc.", "incorporated",
    "corp", "corp.", "corporation",
    "co", "co.", "company",
    "ltd", "ltd.", "limited",
    "llc", "l.l.c.", "llp", "l.l.p.",
    "plc", "p.l.c.",
    "sa", "s.a.", "ag", "a.g.",
    "nv", "n.v.", "bv", "b.v.",
    "gmbh", "g.m.b.h.",
}

# Words to remove for matching
NOISE_WORDS = {"the", "a", "an", "of", "and", "&"}


def normalize_name(name: str) -> str:
    """
    Normalize company name for matching.
    
    Transformations:
    - Lowercase
    - Remove accents
    - Remove punctuation except hyphens
    - Remove corporate suffixes
    - Remove noise words
    - Collapse whitespace
    """
    if not name:
        return ""
    
    # Lowercase
    result = name.lower()
    
    # Remove accents (NFD decomposition)
    result = unicodedata.normalize("NFD", result)
    result = "".join(c for c in result if unicodedata.category(c) != "Mn")
    
    # Replace & with "and"
    result = result.replace("&", " and ")
    
    # Remove punctuation except hyphens and spaces
    result = re.sub(r"[^\w\s-]", " ", result)
    
    # Split into words
    words = result.split()
    
    # Remove suffixes and noise words
    words = [w for w in words if w not in CORP_SUFFIXES and w not in NOISE_WORDS]
    
    # Rejoin and collapse whitespace
    result = " ".join(words)
    
    return result.strip()


def normalize_cik(cik: str) -> str:
    """Normalize CIK to 10-digit padded format."""
    # Remove any non-digit characters
    digits = re.sub(r"\D", "", cik)
    # Pad to 10 digits
    return digits.zfill(10)


def normalize_ticker(ticker: str) -> str:
    """Normalize ticker symbol."""
    return ticker.upper().strip()
```

### [storage/protocol.py] - Storage Protocol

```python
"""Abstract storage protocol."""

from typing import Protocol, Optional, List, Dict, Any
from ..core.types import Entity, SimpleEntity


class EntityStore(Protocol):
    """
    Protocol for entity storage backends.
    
    All backends must implement these methods.
    """
    
    def get_by_id(self, entity_id: str) -> Optional[Entity]:
        """Get entity by ID."""
        ...
    
    def get_by_cik(self, cik: str) -> Optional[Entity]:
        """Get entity by CIK."""
        ...
    
    def get_by_ticker(self, ticker: str) -> Optional[Entity]:
        """Get entity by ticker symbol."""
        ...
    
    def get_by_identifier(self, scheme: str, value: str) -> Optional[Entity]:
        """Get entity by any identifier."""
        ...
    
    def search(self, query: str, limit: int = 10) -> List[Entity]:
        """Search entities by name."""
        ...
    
    def create(self, entity: Entity) -> str:
        """Create new entity, return entity_id."""
        ...
    
    def update(self, entity: Entity) -> None:
        """Update existing entity."""
        ...
    
    def add_identifier(
        self, 
        entity_id: str, 
        scheme: str, 
        value: str,
    ) -> None:
        """Add identifier to entity."""
        ...
    
    def add_alias(
        self,
        entity_id: str,
        alias: str,
        alias_type: str = "alternate",
    ) -> None:
        """Add alias to entity."""
        ...
    
    def count(self) -> int:
        """Return total entity count."""
        ...
    
    def close(self) -> None:
        """Close any open connections."""
        ...
```

### [storage/json_backend.py] - Tier 0 Backend

```python
"""
Tier 0: JSON file backend.

Zero external dependencies - uses only Python stdlib.
Read-only, loads SEC company_tickers.json.
"""

import json
import urllib.request
from pathlib import Path
from typing import Optional, List, Dict

from ..core.types import Entity, SimpleEntity
from ..core.normalize import normalize_name, normalize_cik, normalize_ticker


class JSONBackend:
    """
    Read-only backend using SEC company_tickers.json.
    
    This is the simplest possible backend:
    - No database
    - No external dependencies
    - Auto-downloads from SEC if needed
    """
    
    SEC_URL = "https://www.sec.gov/files/company_tickers.json"
    
    def __init__(
        self,
        json_path: Optional[str] = None,
        auto_download: bool = True,
    ):
        self._json_path = self._find_or_download(json_path, auto_download)
        self._entities: Dict[str, SimpleEntity] = {}
        self._by_cik: Dict[str, SimpleEntity] = {}
        self._by_ticker: Dict[str, SimpleEntity] = {}
        self._by_name_normalized: Dict[str, SimpleEntity] = {}
        self._loaded = False
    
    def _find_or_download(
        self,
        json_path: Optional[str],
        auto_download: bool,
    ) -> Path:
        """Find existing file or download from SEC."""
        if json_path:
            p = Path(json_path)
            if p.exists():
                return p
        
        # Search common locations
        candidates = [
            Path.cwd() / "refdata" / "company_tickers.json",
            Path.cwd() / "data" / "company_tickers.json",
            Path.cwd() / "company_tickers.json",
            Path.home() / ".entity_master" / "company_tickers.json",
            Path.home() / ".cache" / "entity_master" / "company_tickers.json",
        ]
        
        for c in candidates:
            if c.exists():
                return c
        
        if auto_download:
            return self._download()
        
        raise FileNotFoundError(
            "company_tickers.json not found. "
            "Set json_path or enable auto_download."
        )
    
    def _download(self) -> Path:
        """Download company_tickers.json from SEC."""
        target = Path.home() / ".entity_master" / "company_tickers.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        
        print(f"Downloading company_tickers.json from SEC...")
        req = urllib.request.Request(
            self.SEC_URL,
            headers={"User-Agent": "entity-master/1.0 (research)"},
        )
        
        with urllib.request.urlopen(req) as resp:
            target.write_bytes(resp.read())
        
        print(f"Saved to {target}")
        return target
    
    def _ensure_loaded(self):
        """Lazy load data on first access."""
        if self._loaded:
            return
        
        with open(self._json_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        
        for _, item in raw.items():
            cik = item["cik_str"]
            ticker = item["ticker"]
            name = item["title"]
            
            entity = SimpleEntity(cik=cik, ticker=ticker, name=name)
            
            # Index by CIK (both padded and unpadded)
            self._by_cik[cik] = entity
            self._by_cik[cik.lstrip("0") or "0"] = entity
            
            # Index by ticker
            self._by_ticker[ticker.upper()] = entity
            
            # Index by normalized name
            norm = normalize_name(name)
            self._by_name_normalized[norm] = entity
        
        self._loaded = True
    
    # =========================================================================
    # Protocol Implementation
    # =========================================================================
    
    def get_by_id(self, entity_id: str) -> Optional[Entity]:
        """JSON backend doesn't have entity IDs."""
        return None
    
    def get_by_cik(self, cik: str) -> Optional[Entity]:
        self._ensure_loaded()
        cik_clean = cik.lstrip("0") or "0"
        simple = self._by_cik.get(cik_clean)
        return self._to_entity(simple) if simple else None
    
    def get_by_ticker(self, ticker: str) -> Optional[Entity]:
        self._ensure_loaded()
        simple = self._by_ticker.get(ticker.upper())
        return self._to_entity(simple) if simple else None
    
    def get_by_identifier(self, scheme: str, value: str) -> Optional[Entity]:
        if scheme == "cik":
            return self.get_by_cik(value)
        elif scheme == "ticker":
            return self.get_by_ticker(value)
        return None
    
    def search(self, query: str, limit: int = 10) -> List[Entity]:
        self._ensure_loaded()
        results = []
        q = query.upper()
        q_norm = normalize_name(query)
        
        # Search tickers first
        for ticker, entity in self._by_ticker.items():
            if q in ticker:
                results.append(self._to_entity(entity))
                if len(results) >= limit:
                    return results
        
        # Then search normalized names
        for norm, entity in self._by_name_normalized.items():
            if q_norm in norm:
                e = self._to_entity(entity)
                if e not in results:
                    results.append(e)
                    if len(results) >= limit:
                        return results
        
        return results
    
    def create(self, entity: Entity) -> str:
        raise NotImplementedError("JSON backend is read-only")
    
    def update(self, entity: Entity) -> None:
        raise NotImplementedError("JSON backend is read-only")
    
    def add_identifier(self, entity_id: str, scheme: str, value: str) -> None:
        raise NotImplementedError("JSON backend is read-only")
    
    def add_alias(self, entity_id: str, alias: str, alias_type: str) -> None:
        raise NotImplementedError("JSON backend is read-only")
    
    def count(self) -> int:
        self._ensure_loaded()
        return len(self._by_ticker)
    
    def close(self) -> None:
        pass
    
    def _to_entity(self, simple: SimpleEntity) -> Entity:
        """Convert SimpleEntity to Entity."""
        return Entity(
            entity_id="",  # No ID in JSON backend
            primary_name=simple.name,
            cik=simple.cik,
            ticker=simple.ticker,
        )
```

### [resolver.py] - Main EntityResolver Class

```python
"""
Main EntityResolver class.

Auto-selects best available backend:
1. Tier 3: PostgreSQL (if configured)
2. Tier 2: DuckDB (if installed and db exists)
3. Tier 1: SQLite (if db_path specified)
4. Tier 0: JSON (always available)
"""

from typing import Optional, List, Union, Literal
from pathlib import Path

from .core.types import Entity, SimpleEntity
from .core.normalize import normalize_cik, normalize_ticker, normalize_name
from .storage.protocol import EntityStore


BackendType = Literal["json", "sqlite", "duckdb", "postgres", "auto"]


class EntityResolver:
    """
    Entity resolution with automatic backend selection.
    
    Usage:
        # Simplest (JSON backend)
        resolver = EntityResolver()
        
        # With SQLite caching
        resolver = EntityResolver(db_path="entities.db")
        
        # Explicit backend
        resolver = EntityResolver(backend="duckdb", db_path="entities.duckdb")
        
        # PostgreSQL
        resolver = EntityResolver(backend="postgres", dsn="postgresql://...")
    """
    
    def __init__(
        self,
        backend: BackendType = "auto",
        db_path: Optional[str] = None,
        json_path: Optional[str] = None,
        dsn: Optional[str] = None,
        auto_download: bool = True,
    ):
        """
        Initialize resolver.
        
        Args:
            backend: Storage backend ("json", "sqlite", "duckdb", "postgres", "auto")
            db_path: Path to database file (for sqlite/duckdb)
            json_path: Path to company_tickers.json
            dsn: Database connection string (for postgres)
            auto_download: Download company_tickers.json if not found
        """
        self._store = self._create_store(
            backend=backend,
            db_path=db_path,
            json_path=json_path,
            dsn=dsn,
            auto_download=auto_download,
        )
    
    def _create_store(
        self,
        backend: BackendType,
        db_path: Optional[str],
        json_path: Optional[str],
        dsn: Optional[str],
        auto_download: bool,
    ) -> EntityStore:
        """Create appropriate storage backend."""
        
        if backend == "auto":
            backend = self._detect_backend(db_path, dsn)
        
        if backend == "postgres":
            return self._create_postgres_store(dsn)
        elif backend == "duckdb":
            return self._create_duckdb_store(db_path, json_path)
        elif backend == "sqlite":
            return self._create_sqlite_store(db_path, json_path)
        else:
            return self._create_json_store(json_path, auto_download)
    
    def _detect_backend(
        self,
        db_path: Optional[str],
        dsn: Optional[str],
    ) -> BackendType:
        """Auto-detect best available backend."""
        
        if dsn:
            return "postgres"
        
        if db_path:
            p = Path(db_path)
            if p.suffix == ".duckdb":
                return "duckdb"
            return "sqlite"
        
        return "json"
    
    def _create_json_store(
        self,
        json_path: Optional[str],
        auto_download: bool,
    ) -> EntityStore:
        """Create JSON backend."""
        from .storage.json_backend import JSONBackend
        return JSONBackend(json_path=json_path, auto_download=auto_download)
    
    def _create_sqlite_store(
        self,
        db_path: Optional[str],
        json_path: Optional[str],
    ) -> EntityStore:
        """Create SQLite backend."""
        from .storage.sqlite_backend import SQLiteBackend
        return SQLiteBackend(
            db_path=db_path or "entity_master.db",
            json_path=json_path,
        )
    
    def _create_duckdb_store(
        self,
        db_path: Optional[str],
        json_path: Optional[str],
    ) -> EntityStore:
        """Create DuckDB backend."""
        try:
            from .storage.duckdb_backend import DuckDBBackend
            return DuckDBBackend(
                db_path=db_path or "entity_master.duckdb",
                json_path=json_path,
            )
        except ImportError:
            raise ImportError(
                "DuckDB backend requires duckdb. "
                "Install with: pip install entity-master[analytics]"
            )
    
    def _create_postgres_store(self, dsn: Optional[str]) -> EntityStore:
        """Create PostgreSQL backend."""
        try:
            from .storage.postgres_backend import PostgresBackend
            return PostgresBackend(dsn=dsn)
        except ImportError:
            raise ImportError(
                "PostgreSQL backend requires asyncpg. "
                "Install with: pip install entity-master[postgres]"
            )
    
    # =========================================================================
    # Resolution Methods
    # =========================================================================
    
    def resolve(self, query: str) -> Optional[Entity]:
        """
        Resolve any identifier (ticker, CIK, name) to entity.
        
        Tries in order:
        1. Ticker lookup
        2. CIK lookup (if numeric)
        3. Name search (exact then fuzzy)
        """
        q = query.strip()
        
        # Try ticker (most common)
        if entity := self._store.get_by_ticker(normalize_ticker(q)):
            return entity
        
        # Try CIK
        if q.isdigit() or (q.startswith("0") and q[1:].isdigit()):
            if entity := self._store.get_by_cik(normalize_cik(q)):
                return entity
        
        # Try any identifier
        if entity := self._store.get_by_identifier("name", q):
            return entity
        
        # Try search
        results = self._store.search(q, limit=1)
        if results:
            return results[0]
        
        return None
    
    def get_by_cik(self, cik: str) -> Optional[Entity]:
        """Get entity by CIK."""
        return self._store.get_by_cik(normalize_cik(cik))
    
    def get_by_ticker(self, ticker: str) -> Optional[Entity]:
        """Get entity by ticker symbol."""
        return self._store.get_by_ticker(normalize_ticker(ticker))
    
    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Get entity by ID."""
        return self._store.get_by_id(entity_id)
    
    def search(self, query: str, limit: int = 10) -> List[Entity]:
        """Search entities by name or ticker."""
        return self._store.search(query, limit=limit)
    
    # =========================================================================
    # Write Methods (Tier 1+)
    # =========================================================================
    
    def add_identifier(
        self,
        entity_id: str,
        scheme: str,
        value: str,
    ) -> None:
        """Add identifier to entity."""
        self._store.add_identifier(entity_id, scheme, value)
    
    def add_alias(
        self,
        entity_id: str,
        alias: str,
        alias_type: str = "alternate",
    ) -> None:
        """Add alias to entity."""
        self._store.add_alias(entity_id, alias, alias_type)
    
    # =========================================================================
    # Utility
    # =========================================================================
    
    @property
    def entity_count(self) -> int:
        """Number of entities in store."""
        return self._store.count()
    
    def close(self) -> None:
        """Close any open connections."""
        self._store.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.close()
```

---

## py-sec-edgar v4 Integration Example

```python
# py_sec_edgar_v4/filings/search.py

from typing import Optional, List
from pathlib import Path

# Try importing entity_master
try:
    from entity_master import EntityResolver
    _HAS_ENTITY_MASTER = True
except ImportError:
    _HAS_ENTITY_MASTER = False


class FilingSearch:
    """Search SEC filings."""
    
    def __init__(self, data_dir: str = "sec_data"):
        self.data_dir = Path(data_dir)
        self._entity_resolver = None
    
    @property
    def entity_resolver(self) -> 'EntityResolver':
        """Lazy-load entity resolver."""
        if self._entity_resolver is None:
            if _HAS_ENTITY_MASTER:
                # Use entity_master if available
                self._entity_resolver = EntityResolver(
                    json_path=str(self.data_dir.parent / "refdata" / "company_tickers.json"),
                )
            else:
                # Inline fallback (copy Tier 0 logic)
                self._entity_resolver = self._create_fallback_resolver()
        return self._entity_resolver
    
    def resolve_ticker(self, ticker: str) -> Optional[str]:
        """Resolve ticker to CIK (10-digit padded)."""
        entity = self.entity_resolver.resolve(ticker)
        if entity and entity.cik:
            return entity.cik.zfill(10)
        return None
    
    def resolve_cik(self, cik: str) -> Optional[dict]:
        """Resolve CIK to entity info."""
        entity = self.entity_resolver.get_by_cik(cik)
        if entity:
            return {
                "cik": entity.cik,
                "ticker": entity.ticker,
                "name": entity.primary_name,
            }
        return None
    
    def search_by_ticker(
        self,
        tickers: List[str],
        forms: Optional[List[str]] = None,
        **kwargs,
    ) -> List['Filing']:
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

## CLI Interface

```python
# entity_master/cli.py

"""Entity Master CLI."""

import argparse
import sys
from typing import Optional


def main(args: Optional[list] = None):
    parser = argparse.ArgumentParser(
        prog="entity-master",
        description="Lightweight entity resolution",
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Resolve command
    resolve_parser = subparsers.add_parser("resolve", help="Resolve identifier")
    resolve_parser.add_argument("query", help="Ticker, CIK, or name")
    resolve_parser.add_argument("--db", help="Database path")
    resolve_parser.add_argument("--format", choices=["text", "json"], default="text")
    
    # Search command
    search_parser = subparsers.add_parser("search", help="Search entities")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("--limit", type=int, default=10)
    search_parser.add_argument("--db", help="Database path")
    
    # Serve command
    serve_parser = subparsers.add_parser("serve", help="Start API server")
    serve_parser.add_argument("--port", type=int, default=8000)
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--db", help="Database path")
    serve_parser.add_argument("--dsn", help="PostgreSQL DSN")
    
    # Migrate command
    migrate_parser = subparsers.add_parser("migrate", help="Migrate data")
    migrate_parser.add_argument("--source", required=True, help="Source path/DSN")
    migrate_parser.add_argument("--target", required=True, help="Target path/DSN")
    
    # Download command
    download_parser = subparsers.add_parser("download", help="Download SEC data")
    download_parser.add_argument("--output", default="company_tickers.json")
    
    parsed = parser.parse_args(args)
    
    if parsed.command == "resolve":
        cmd_resolve(parsed)
    elif parsed.command == "search":
        cmd_search(parsed)
    elif parsed.command == "serve":
        cmd_serve(parsed)
    elif parsed.command == "migrate":
        cmd_migrate(parsed)
    elif parsed.command == "download":
        cmd_download(parsed)
    else:
        parser.print_help()


def cmd_resolve(args):
    """Resolve identifier to entity."""
    from entity_master import EntityResolver
    import json
    
    resolver = EntityResolver(db_path=args.db)
    entity = resolver.resolve(args.query)
    
    if not entity:
        print(f"Not found: {args.query}", file=sys.stderr)
        sys.exit(1)
    
    if args.format == "json":
        print(json.dumps({
            "entity_id": entity.entity_id,
            "primary_name": entity.primary_name,
            "cik": entity.cik,
            "ticker": entity.ticker,
        }, indent=2))
    else:
        print(f"Name:   {entity.primary_name}")
        print(f"CIK:    {entity.cik}")
        print(f"Ticker: {entity.ticker}")


def cmd_search(args):
    """Search entities."""
    from entity_master import EntityResolver
    
    resolver = EntityResolver(db_path=args.db)
    results = resolver.search(args.query, limit=args.limit)
    
    if not results:
        print("No results found")
        return
    
    for entity in results:
        print(f"{entity.ticker or '-':6} {entity.cik or '-':12} {entity.primary_name}")


def cmd_serve(args):
    """Start FastAPI server."""
    try:
        import uvicorn
        from entity_master.api.app import create_app
    except ImportError:
        print("Server requires: pip install entity-master[service]", file=sys.stderr)
        sys.exit(1)
    
    app = create_app(db_path=args.db, dsn=args.dsn)
    uvicorn.run(app, host=args.host, port=args.port)


def cmd_download(args):
    """Download SEC data."""
    from entity_master.storage.json_backend import JSONBackend
    from pathlib import Path
    
    backend = JSONBackend(auto_download=True)
    print(f"Downloaded to: {backend._json_path}")
    print(f"Entities: {backend.count():,}")


if __name__ == "__main__":
    main()
```

---

## Usage Examples

```bash
# CLI usage
entity-master resolve AAPL
entity-master search "apple"
entity-master download

# Start service
entity-master serve --port 8000

# With PostgreSQL
entity-master serve --dsn "postgresql://localhost/entity_master"
```

```python
# Python usage
from entity_master import EntityResolver

# Tier 0: Just JSON
resolver = EntityResolver()
apple = resolver.resolve("AAPL")
print(apple.cik)  # "0000320193"

# Tier 1: With SQLite
resolver = EntityResolver(db_path="entities.db")
resolver.add_alias(apple.entity_id, "Apple Computer", alias_type="former")

# Search
for entity in resolver.search("technology", limit=5):
    print(f"{entity.ticker}: {entity.primary_name}")
```

---

*Document version: 1.0.0*
*Last updated: 2025-01-25*
