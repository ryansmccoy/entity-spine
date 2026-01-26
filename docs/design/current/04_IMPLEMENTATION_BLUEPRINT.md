# EntitySpine Implementation Blueprint (v2.2)

**For: Claude Opus 4.5 (Extended Thinking Mode)**

> This document defines HOW to implement entityspine in phases,  
> the technology choices, and the order of operations (TDD-first).

---

## Table of Contents

1. [Technology Stack](#technology-stack)
2. [Implementation Order](#implementation-order)
3. [Phase 0: Project Setup](#phase-0-project-setup)
4. [Phase 1: Domain Models](#phase-1-domain-models)
5. [Phase 2: Protocols & Interfaces](#phase-2-protocols--interfaces)
6. [Phase 3: Storage Layer](#phase-3-storage-layer)
7. [Phase 4: Resolution Service](#phase-4-resolution-service)
8. [Phase 5: Simple Facade API](#phase-5-simple-facade-api)
9. [Test Structure](#test-structure)
10. [Simple Interface Design](#simple-interface-design)

---

## Technology Stack

### Core Dependencies (Tier 0-1: Zero External Deps)

| Component | Technology | Why |
|-----------|------------|-----|
| **Domain Models** | `dataclasses` (stdlib) | Zero deps, simple, immutable |
| **Validation** | Custom validators | No Pydantic in core (zero deps) |
| **Storage** | `sqlite3` (stdlib) | Zero deps, sufficient for Tier 1 |
| **IDs** | Custom ULID (stdlib) | No external ulid package |
| **Config** | `dataclasses` + env | No Pydantic settings |

### Optional Dependencies (Tier 2-3)

| Component | Technology | Extra Install |
|-----------|------------|---------------|
| **Validation** | Pydantic v2 | `pip install entityspine[pydantic]` |
| **Analytics DB** | DuckDB | `pip install entityspine[duckdb]` |
| **Production DB** | PostgreSQL + asyncpg | `pip install entityspine[postgres]` |
| **Full install** | All above | `pip install entityspine[all]` |

### Why This Stack?

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DEPENDENCY PHILOSOPHY                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Tier 0-1 MUST work with ZERO pip installs:                                │
│                                                                             │
│    from entityspine import EntityResolver                                   │
│    resolver = EntityResolver()  # Just works, no setup                      │
│    result = resolver.resolve("AAPL")                                        │
│                                                                             │
│  This means:                                                                │
│    • No Pydantic in core (use dataclasses)                                 │
│    • No SQLAlchemy (use raw sqlite3)                                       │
│    • No external ULID (implement with stdlib)                              │
│    • No httpx/requests (use urllib.request)                                │
│                                                                             │
│  Optional deps unlock features, but core always works.                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Implementation Order

### The Golden Rule: TDD

```
For EVERY component:
  1. Write failing test
  2. Implement minimum to pass
  3. Refactor
  4. Repeat
```

### Phase Order (Dependencies Flow Down)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         IMPLEMENTATION PHASES                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Phase 0: Project Setup                                                     │
│     └── pyproject.toml, directory structure, conftest.py                   │
│                                                                             │
│  Phase 1: Domain Models (no deps)                                           │
│     └── Entity, Security, Listing, Claim dataclasses                       │
│     └── Tests: test_entity.py, test_security.py, etc.                      │
│                                                                             │
│  Phase 2: Protocols & Interfaces                                            │
│     └── EntityStoreProtocol, EntityResolverProtocol                        │
│     └── ResolutionResult, ResolutionCandidate                              │
│     └── Tests: test_protocols.py (structural subtyping)                    │
│                                                                             │
│  Phase 3: Storage Layer                                                     │
│     └── SQLiteStore (implements EntityStoreProtocol)                       │
│     └── JSONStore (read-only, for SEC JSON)                                │
│     └── Tests: test_sqlite_store.py, test_json_store.py                    │
│                                                                             │
│  Phase 4: Resolution Service                                                │
│     └── EntityResolver (uses store, returns ResolutionResult)              │
│     └── Tests: test_resolver.py, test_resolution_flow.py                   │
│                                                                             │
│  Phase 5: Simple Facade API                                                 │
│     └── Public API: EntityResolver() with auto-setup                       │
│     └── SEC JSON download and SQLite caching                               │
│     └── Tests: test_simple_api.py, test_integration.py                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Phase 0: Project Setup

### Directory Structure

```
entityspine/
├── src/entityspine/
│   ├── __init__.py              # Public API exports
│   ├── py.typed                 # PEP 561 marker
│   │
│   ├── domain/                  # Domain layer (Phase 1)
│   │   ├── __init__.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── entity.py        # Entity dataclass
│   │   │   ├── security.py      # Security dataclass
│   │   │   ├── listing.py       # Listing dataclass
│   │   │   ├── claim.py         # IdentifierClaim dataclass
│   │   │   └── resolution.py    # ResolutionResult, Candidate
│   │   └── protocols/
│   │       ├── __init__.py
│   │       ├── store.py         # EntityStoreProtocol
│   │       └── resolver.py      # EntityResolverProtocol
│   │
│   ├── infrastructure/          # Infrastructure layer (Phase 3)
│   │   ├── __init__.py
│   │   ├── storage/
│   │   │   ├── __init__.py
│   │   │   ├── sqlite_store.py
│   │   │   ├── json_store.py
│   │   │   ├── duckdb_store.py  # Optional
│   │   │   └── postgres_store.py # Optional
│   │   └── http/
│   │       ├── __init__.py
│   │       └── sec_fetcher.py   # Downloads SEC JSON
│   │
│   ├── application/             # Application layer (Phase 4)
│   │   ├── __init__.py
│   │   └── resolver.py          # EntityResolver service
│   │
│   └── core/                    # Utilities (shared)
│       ├── __init__.py
│       ├── ulid.py              # ULID generation (stdlib)
│       ├── normalize.py         # ID normalization
│       └── exceptions.py        # Exception hierarchy
│
├── tests/                       # Mirrors src/ structure
│   ├── conftest.py              # Shared fixtures
│   ├── unit/
│   │   ├── domain/
│   │   │   ├── models/
│   │   │   │   ├── test_entity.py
│   │   │   │   ├── test_security.py
│   │   │   │   ├── test_listing.py
│   │   │   │   ├── test_claim.py
│   │   │   │   └── test_resolution.py
│   │   │   └── protocols/
│   │   │       └── test_protocols.py
│   │   ├── infrastructure/
│   │   │   └── storage/
│   │   │       ├── test_sqlite_store.py
│   │   │       └── test_json_store.py
│   │   └── application/
│   │       └── test_resolver.py
│   └── integration/
│       ├── test_resolution_flow.py
│       ├── test_simple_api.py
│       └── test_pysecedgar_port.py
│
├── pyproject.toml
├── Makefile
└── README.md
```

### pyproject.toml

```toml
[project]
name = "entityspine"
version = "0.1.0"
description = "Entity resolution for financial data"
requires-python = ">=3.11"
dependencies = []  # ZERO core dependencies

[project.optional-dependencies]
pydantic = ["pydantic>=2.0"]
duckdb = ["duckdb>=0.9"]
postgres = ["asyncpg>=0.29", "psycopg[binary]>=3.1"]
all = ["entityspine[pydantic,duckdb,postgres]"]
dev = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
    "mypy>=1.8",
    "ruff>=0.1",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-v --tb=short"

[tool.mypy]
strict = true
python_version = "3.11"

[tool.ruff]
target-version = "py311"
select = ["E", "F", "I", "UP", "B", "SIM"]
```

### conftest.py (Shared Fixtures)

```python
# tests/conftest.py
"""Shared test fixtures for entityspine."""

import sqlite3
import tempfile
from pathlib import Path
from typing import Generator

import pytest


@pytest.fixture
def temp_db() -> Generator[Path, None, None]:
    """Create temporary SQLite database."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    yield db_path
    db_path.unlink(missing_ok=True)


@pytest.fixture
def sample_sec_json() -> dict:
    """Sample SEC company_tickers.json data."""
    return {
        "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
        "1": {"cik_str": 789019, "ticker": "MSFT", "title": "MICROSOFT CORP"},
        "2": {"cik_str": 1318605, "ticker": "TSLA", "title": "Tesla, Inc."},
    }


@pytest.fixture
def populated_db(temp_db: Path, sample_sec_json: dict) -> Path:
    """SQLite database populated with sample data."""
    from entityspine.infrastructure.storage.sqlite_store import SQLiteStore
    
    store = SQLiteStore(temp_db)
    store.initialize()
    store.load_sec_json(sample_sec_json)
    return temp_db
```

---

## Phase 1: Domain Models

### Order of Implementation

```
1. core/ulid.py          # No deps, needed by all models
2. core/normalize.py     # ID normalization
3. core/exceptions.py    # Exception hierarchy
4. domain/models/entity.py
5. domain/models/security.py
6. domain/models/listing.py
7. domain/models/claim.py
8. domain/models/resolution.py
```

### TDD: Entity Model

**Step 1: Write test first**

```python
# tests/unit/domain/models/test_entity.py
"""Tests for Entity domain model."""

from datetime import datetime

import pytest

from entityspine.domain.models.entity import Entity, EntityType, EntityStatus


class TestEntity:
    """Tests for Entity dataclass."""

    def test_entity_creation_minimal(self):
        """Entity can be created with minimal required fields."""
        entity = Entity(
            entity_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            primary_name="Apple Inc.",
            source_system="sec",
        )
        
        assert entity.entity_id == "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        assert entity.primary_name == "Apple Inc."
        assert entity.entity_type == EntityType.COMPANY  # Default
        assert entity.status == EntityStatus.ACTIVE  # Default

    def test_entity_has_no_ticker_attribute(self):
        """Entity must NOT have ticker attribute (scope violation)."""
        entity = Entity(
            entity_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            primary_name="Apple Inc.",
            source_system="sec",
        )
        
        assert not hasattr(entity, "ticker")
        assert not hasattr(entity, "exchange")

    def test_entity_immutable(self):
        """Entity should be frozen (immutable)."""
        entity = Entity(
            entity_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            primary_name="Apple Inc.",
            source_system="sec",
        )
        
        with pytest.raises(AttributeError):
            entity.primary_name = "Changed"  # type: ignore

    def test_entity_merged_into(self):
        """Entity can track merge target."""
        entity = Entity(
            entity_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            primary_name="Time Warner",
            source_system="sec",
            status=EntityStatus.MERGED,
            merged_into_id="01BSY4NDEKTSV4RRFFQ69G5FAV",
        )
        
        assert entity.status == EntityStatus.MERGED
        assert entity.merged_into_id == "01BSY4NDEKTSV4RRFFQ69G5FAV"

    def test_entity_type_enum(self):
        """EntityType enum has expected values."""
        assert EntityType.COMPANY.value == "COMPANY"
        assert EntityType.FUND.value == "FUND"
        assert EntityType.PERSON.value == "PERSON"

    def test_entity_status_enum(self):
        """EntityStatus enum has expected values."""
        assert EntityStatus.ACTIVE.value == "active"
        assert EntityStatus.MERGED.value == "merged"
        assert EntityStatus.PROVISIONAL.value == "provisional"
```

**Step 2: Implement to pass tests**

```python
# src/entityspine/domain/models/entity.py
"""Entity domain model.

An Entity represents a legal organization (company, fund, person) that files
with the SEC or issues securities. Entities are identified by CIK, LEI, etc.

IMPORTANT: Entity does NOT have ticker or exchange attributes.
Those belong to Listing (Entity → Security → Listing).
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class EntityType(Enum):
    """Classification of entity."""
    COMPANY = "COMPANY"
    FUND = "FUND"
    PERSON = "PERSON"
    GOVERNMENT = "GOVERNMENT"
    SPV = "SPV"
    TRUST = "TRUST"
    PARTNERSHIP = "PARTNERSHIP"
    UNKNOWN = "UNKNOWN"


class EntityStatus(Enum):
    """Lifecycle status of entity."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    MERGED = "merged"
    PROVISIONAL = "provisional"
    DISPUTED = "disputed"


@dataclass(frozen=True, slots=True)
class Entity:
    """
    A legal organization that files with SEC or issues securities.
    
    This is the top of the hierarchy: Entity → Security → Listing.
    
    Attributes:
        entity_id: ULID primary key.
        primary_name: Current canonical name.
        source_system: Where this entity came from.
        entity_type: Classification (COMPANY, FUND, etc.).
        status: Lifecycle status (active, merged, etc.).
        legal_name: Official legal name if different.
        sic_code: Standard Industrial Classification.
        merged_into_id: If merged, the target entity ID.
        created_at: When record was created.
    
    Note:
        Entity does NOT have ticker or exchange. Those are Listing attributes.
    
    Example:
        >>> entity = Entity(
        ...     entity_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
        ...     primary_name="Apple Inc.",
        ...     source_system="sec",
        ... )
        >>> entity.primary_name
        'Apple Inc.'
    """
    
    # Required fields
    entity_id: str
    primary_name: str
    source_system: str
    
    # Optional fields with defaults
    entity_type: EntityType = EntityType.COMPANY
    status: EntityStatus = EntityStatus.ACTIVE
    legal_name: str | None = None
    sic_code: str | None = None
    
    # Merge tracking
    merged_into_id: str | None = None
    merged_at: datetime | None = None
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
```

### Similar TDD Pattern for Other Models

Apply same pattern to:
- `Security` (has `issuer_entity_id`, security type, NO ticker)
- `Listing` (HAS ticker, mic, valid_from/to)
- `IdentifierClaim` (scheme, value, source_system, confidence)
- `ResolutionResult`, `ResolutionCandidate`

---

## Phase 2: Protocols & Interfaces

### TDD: EntityStoreProtocol

**Step 1: Write test**

```python
# tests/unit/domain/protocols/test_protocols.py
"""Tests for protocol definitions."""

from typing import Protocol, runtime_checkable

import pytest

from entityspine.domain.protocols.store import EntityStoreProtocol
from entityspine.domain.models.entity import Entity


class TestEntityStoreProtocol:
    """Tests for EntityStoreProtocol interface."""

    def test_protocol_is_runtime_checkable(self):
        """Protocol should be runtime checkable."""
        assert hasattr(EntityStoreProtocol, "__protocol_attrs__")

    def test_dummy_implementation_satisfies_protocol(self):
        """A class implementing all methods satisfies the protocol."""
        
        class DummyStore:
            def get_entity(self, entity_id: str) -> Entity | None:
                return None
            
            def get_entities_by_cik(self, cik: str) -> list[Entity]:
                return []
            
            def get_listings_by_ticker(
                self, ticker: str, as_of=None
            ) -> list:
                return []
            
            def save_entity(self, entity: Entity) -> None:
                pass
            
            # ... other required methods
        
        store = DummyStore()
        assert isinstance(store, EntityStoreProtocol)
```

**Step 2: Implement protocol**

```python
# src/entityspine/domain/protocols/store.py
"""Storage protocol definitions."""

from datetime import date
from typing import Protocol, runtime_checkable

from entityspine.domain.models.entity import Entity
from entityspine.domain.models.security import Security
from entityspine.domain.models.listing import Listing
from entityspine.domain.models.claim import IdentifierClaim


@runtime_checkable
class EntityStoreProtocol(Protocol):
    """
    Protocol for entity storage backends.
    
    All storage implementations (JSON, SQLite, DuckDB, PostgreSQL)
    must satisfy this interface.
    
    Example:
        >>> class SQLiteStore:
        ...     def get_entity(self, entity_id: str) -> Entity | None:
        ...         ...
        >>> store: EntityStoreProtocol = SQLiteStore("db.sqlite")
    """
    
    # Entity operations
    def get_entity(self, entity_id: str) -> Entity | None:
        """Get entity by ID, following merge redirects."""
        ...
    
    def get_entities_by_cik(self, cik: str) -> list[Entity]:
        """Get entities matching CIK (via claims)."""
        ...
    
    def save_entity(self, entity: Entity) -> None:
        """Save or update entity."""
        ...
    
    # Listing operations (for ticker resolution)
    def get_listings_by_ticker(
        self,
        ticker: str,
        mic: str | None = None,
        as_of: date | None = None,
    ) -> list[Listing]:
        """Get listings matching ticker, optionally at point-in-time."""
        ...
    
    # Claim operations
    def get_claims(
        self,
        scheme: str,
        value: str,
    ) -> list[IdentifierClaim]:
        """Get claims matching scheme and value."""
        ...
    
    def save_claim(self, claim: IdentifierClaim) -> None:
        """Save identifier claim."""
        ...
```

---

## Phase 3: Storage Layer

### TDD: SQLiteStore

**Step 1: Write tests**

```python
# tests/unit/infrastructure/storage/test_sqlite_store.py
"""Tests for SQLite storage backend."""

from datetime import date
from pathlib import Path

import pytest

from entityspine.infrastructure.storage.sqlite_store import SQLiteStore
from entityspine.domain.models.entity import Entity, EntityStatus


class TestSQLiteStoreSchema:
    """Tests for SQLite schema creation."""

    def test_initialize_creates_tables(self, temp_db: Path):
        """Initialize creates all required tables."""
        store = SQLiteStore(temp_db)
        store.initialize()
        
        # Check tables exist
        tables = store._get_tables()
        assert "entities" in tables
        assert "securities" in tables
        assert "listings" in tables
        assert "identifier_claims" in tables
        assert "aliases" in tables

    def test_entities_table_has_no_ticker_column(self, temp_db: Path):
        """Entities table must NOT have ticker column (scope violation)."""
        store = SQLiteStore(temp_db)
        store.initialize()
        
        columns = store._get_columns("entities")
        assert "ticker" not in columns
        assert "exchange" not in columns

    def test_listings_table_has_ticker_column(self, temp_db: Path):
        """Listings table must have ticker column."""
        store = SQLiteStore(temp_db)
        store.initialize()
        
        columns = store._get_columns("listings")
        assert "ticker" in columns
        assert "mic" in columns
        assert "valid_from" in columns


class TestSQLiteStoreOperations:
    """Tests for SQLite CRUD operations."""

    def test_save_and_get_entity(self, temp_db: Path):
        """Can save and retrieve entity."""
        store = SQLiteStore(temp_db)
        store.initialize()
        
        entity = Entity(
            entity_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            primary_name="Apple Inc.",
            source_system="test",
        )
        store.save_entity(entity)
        
        retrieved = store.get_entity("01ARZ3NDEKTSV4RRFFQ69G5FAV")
        assert retrieved is not None
        assert retrieved.primary_name == "Apple Inc."

    def test_get_entity_follows_merge_redirect(self, temp_db: Path):
        """get_entity follows merged_into_id chain."""
        store = SQLiteStore(temp_db)
        store.initialize()
        
        # Entity A merged into B
        entity_a = Entity(
            entity_id="01AAA",
            primary_name="Old Company",
            source_system="test",
            status=EntityStatus.MERGED,
            merged_into_id="01BBB",
        )
        entity_b = Entity(
            entity_id="01BBB",
            primary_name="New Company",
            source_system="test",
        )
        store.save_entity(entity_a)
        store.save_entity(entity_b)
        
        # Getting A should return B
        retrieved = store.get_entity("01AAA")
        assert retrieved.entity_id == "01BBB"

    def test_get_listings_by_ticker_respects_as_of(self, temp_db: Path):
        """Ticker lookup respects point-in-time."""
        store = SQLiteStore(temp_db)
        store.initialize()
        
        # Create listings with different validity periods
        # ... (test temporal validity)
```

**Step 2: Implement SQLiteStore**

```python
# src/entityspine/infrastructure/storage/sqlite_store.py
"""SQLite storage backend for entityspine.

This is the default Tier 1 backend - zero external dependencies,
uses only Python stdlib sqlite3.
"""

import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Any

from entityspine.domain.models.entity import Entity, EntityType, EntityStatus
from entityspine.domain.models.security import Security
from entityspine.domain.models.listing import Listing
from entityspine.domain.models.claim import IdentifierClaim


class SQLiteStore:
    """
    SQLite storage backend implementing EntityStoreProtocol.
    
    Uses v2.2 schema with proper Entity/Security/Listing separation.
    Ticker is on Listing, never on Entity.
    
    Example:
        >>> store = SQLiteStore(Path("entities.db"))
        >>> store.initialize()
        >>> store.save_entity(entity)
    """
    
    SCHEMA = '''
    -- Entities (legal organizations) - NO ticker column
    CREATE TABLE IF NOT EXISTS entities (
        entity_id TEXT PRIMARY KEY,
        entity_type TEXT NOT NULL DEFAULT 'COMPANY',
        status TEXT NOT NULL DEFAULT 'active',
        primary_name TEXT NOT NULL,
        legal_name TEXT,
        sic_code TEXT,
        merged_into_id TEXT REFERENCES entities(entity_id),
        merged_at TEXT,
        source_system TEXT NOT NULL,
        source_id TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
    
    -- Securities (financial instruments)
    CREATE TABLE IF NOT EXISTS securities (
        security_id TEXT PRIMARY KEY,
        issuer_entity_id TEXT NOT NULL REFERENCES entities(entity_id),
        security_type TEXT NOT NULL DEFAULT 'common_stock',
        name TEXT NOT NULL,
        currency TEXT,
        status TEXT NOT NULL DEFAULT 'active',
        source_system TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
    
    -- Listings (where securities trade) - ticker IS here
    CREATE TABLE IF NOT EXISTS listings (
        listing_id TEXT PRIMARY KEY,
        security_id TEXT NOT NULL REFERENCES securities(security_id),
        ticker TEXT NOT NULL,
        mic TEXT,
        is_primary INTEGER NOT NULL DEFAULT 1,
        status TEXT NOT NULL DEFAULT 'active',
        valid_from TEXT NOT NULL,
        valid_to TEXT,
        source_system TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        UNIQUE(ticker, mic, valid_from)
    );
    
    -- Identifier claims (all identifiers with provenance)
    CREATE TABLE IF NOT EXISTS identifier_claims (
        claim_id TEXT PRIMARY KEY,
        entity_id TEXT REFERENCES entities(entity_id),
        security_id TEXT REFERENCES securities(security_id),
        listing_id TEXT REFERENCES listings(listing_id),
        scheme TEXT NOT NULL,
        value TEXT NOT NULL,
        source_system TEXT NOT NULL,
        confidence REAL NOT NULL DEFAULT 1.0,
        captured_at TEXT NOT NULL DEFAULT (datetime('now')),
        valid_from TEXT,
        valid_to TEXT,
        status TEXT NOT NULL DEFAULT 'active'
    );
    
    -- Aliases (name variants)
    CREATE TABLE IF NOT EXISTS aliases (
        alias_id TEXT PRIMARY KEY,
        entity_id TEXT NOT NULL REFERENCES entities(entity_id),
        alias_text TEXT NOT NULL,
        alias_type TEXT NOT NULL DEFAULT 'alternate',
        source_system TEXT NOT NULL,
        captured_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
    
    -- Indexes
    CREATE INDEX IF NOT EXISTS idx_entities_status ON entities(status);
    CREATE INDEX IF NOT EXISTS idx_entities_merged ON entities(merged_into_id);
    CREATE INDEX IF NOT EXISTS idx_securities_issuer ON securities(issuer_entity_id);
    CREATE INDEX IF NOT EXISTS idx_listings_ticker ON listings(ticker);
    CREATE INDEX IF NOT EXISTS idx_listings_valid ON listings(valid_from, valid_to);
    CREATE INDEX IF NOT EXISTS idx_claims_scheme_value ON identifier_claims(scheme, value);
    CREATE INDEX IF NOT EXISTS idx_aliases_text ON aliases(alias_text);
    '''
    
    def __init__(self, db_path: Path | str):
        self.db_path = Path(db_path)
        self._conn: sqlite3.Connection | None = None
    
    def initialize(self) -> None:
        """Create database schema."""
        conn = self._get_connection()
        conn.executescript(self.SCHEMA)
        conn.commit()
    
    def _get_connection(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row
        return self._conn
    
    def get_entity(self, entity_id: str) -> Entity | None:
        """Get entity by ID, following merge redirects."""
        conn = self._get_connection()
        row = conn.execute(
            "SELECT * FROM entities WHERE entity_id = ?",
            (entity_id,)
        ).fetchone()
        
        if row is None:
            return None
        
        entity = self._row_to_entity(row)
        
        # Follow merge redirect
        if entity.merged_into_id:
            return self.get_entity(entity.merged_into_id)
        
        return entity
    
    # ... additional methods
```

---

## Phase 4: Resolution Service

### TDD: EntityResolver

```python
# tests/unit/application/test_resolver.py
"""Tests for EntityResolver service."""

import pytest

from entityspine.application.resolver import EntityResolver
from entityspine.domain.models.resolution import ResolutionResult


class TestEntityResolver:
    """Tests for entity resolution."""

    def test_resolve_returns_resolution_result(self, populated_db):
        """resolve() must return ResolutionResult, not Entity."""
        resolver = EntityResolver(db_path=populated_db)
        
        result = resolver.resolve("AAPL")
        
        assert isinstance(result, ResolutionResult)
        assert isinstance(result.candidates, list)

    def test_resolve_cik_returns_candidates(self, populated_db):
        """CIK resolution returns candidates list."""
        resolver = EntityResolver(db_path=populated_db)
        
        result = resolver.resolve_cik("0000320193")
        
        assert len(result.candidates) >= 1
        assert result.best.score == 1.0
        assert result.best.matched_scheme == "cik"

    def test_resolve_ticker_via_listing(self, populated_db):
        """Ticker resolution goes through listing."""
        resolver = EntityResolver(db_path=populated_db)
        
        result = resolver.resolve_ticker("AAPL")
        
        assert result.best.listing_id is not None
        assert result.best.security_id is not None
        assert result.best.entity_id is not None
```

---

## Phase 5: Simple Facade API

### The Goal: Maximum Simplicity

```python
# This MUST work with zero configuration
from entityspine import EntityResolver

resolver = EntityResolver()  # Auto-downloads SEC JSON, creates SQLite cache
result = resolver.resolve("AAPL")
print(result.best.entity_id)  # Works!
```

### TDD: Simple API

```python
# tests/integration/test_simple_api.py
"""Tests for simple public API."""

import pytest

from entityspine import EntityResolver


class TestSimpleAPI:
    """Tests for the simple public API."""

    def test_resolver_works_with_no_config(self, tmp_path, monkeypatch):
        """EntityResolver() works with zero configuration."""
        # Mock SEC download to avoid network
        monkeypatch.setenv("ENTITYSPINE_CACHE_DIR", str(tmp_path))
        
        resolver = EntityResolver()
        
        # Should have downloaded and cached SEC data
        assert resolver.entity_count > 0

    def test_resolve_aapl(self, resolver_with_sec_data):
        """Can resolve AAPL to Apple Inc."""
        result = resolver_with_sec_data.resolve("AAPL")
        
        assert result.best is not None
        entity = resolver_with_sec_data.get(result.best.entity_id)
        assert "apple" in entity.primary_name.lower()

    def test_resolve_by_cik(self, resolver_with_sec_data):
        """Can resolve by CIK."""
        result = resolver_with_sec_data.resolve("320193")
        
        assert result.best is not None

    def test_resolve_returns_candidates_not_entity(self, resolver_with_sec_data):
        """resolve() returns ResolutionResult, not Entity."""
        result = resolver_with_sec_data.resolve("AAPL")
        
        # NOT: assert isinstance(result, Entity)
        from entityspine.domain.models.resolution import ResolutionResult
        assert isinstance(result, ResolutionResult)
```

### Implementation: Simple Facade

```python
# src/entityspine/__init__.py
"""
EntitySpine - Entity resolution for financial data.

Simple usage:
    >>> from entityspine import EntityResolver
    >>> resolver = EntityResolver()
    >>> result = resolver.resolve("AAPL")
    >>> print(result.best.entity_id)

The resolver automatically:
1. Downloads SEC company_tickers.json (if not cached)
2. Creates SQLite database (in cache directory)
3. Provides resolution via simple API
"""

from entityspine.application.resolver import EntityResolver
from entityspine.domain.models.entity import Entity, EntityType, EntityStatus
from entityspine.domain.models.resolution import ResolutionResult, ResolutionCandidate

__all__ = [
    "EntityResolver",
    "Entity",
    "EntityType",
    "EntityStatus",
    "ResolutionResult",
    "ResolutionCandidate",
]

__version__ = "0.1.0"
```

```python
# src/entityspine/application/resolver.py
"""
EntityResolver - Main entry point for entity resolution.

This module provides the simple facade API that hides backend complexity.
"""

from datetime import date
from pathlib import Path
from typing import Optional

from entityspine.domain.models.resolution import ResolutionResult, ResolutionCandidate
from entityspine.domain.models.entity import Entity
from entityspine.domain.protocols.store import EntityStoreProtocol
from entityspine.infrastructure.storage.sqlite_store import SQLiteStore
from entityspine.infrastructure.http.sec_fetcher import SECFetcher


def _get_default_cache_dir() -> Path:
    """Get default cache directory."""
    import os
    cache_dir = os.environ.get("ENTITYSPINE_CACHE_DIR")
    if cache_dir:
        return Path(cache_dir)
    return Path.home() / ".cache" / "entityspine"


class EntityResolver:
    """
    Entity resolution service with simple API.
    
    Automatically handles:
    - SEC data download and caching
    - SQLite database management
    - Ticker → Listing → Security → Entity traversal
    - Merge redirect following
    
    Example:
        >>> resolver = EntityResolver()
        >>> result = resolver.resolve("AAPL")
        >>> if result.best and result.best.score >= 0.9:
        ...     entity = resolver.get(result.best.entity_id)
        ...     print(entity.primary_name)
        Apple Inc.
    
    Args:
        db_path: Path to SQLite database. If None, uses default cache.
        backend: Storage backend ("sqlite", "duckdb", "postgres").
        auto_download: If True, download SEC data if not cached.
    """
    
    def __init__(
        self,
        db_path: Path | str | None = None,
        backend: str = "sqlite",
        auto_download: bool = True,
    ):
        # Determine database path
        if db_path is None:
            cache_dir = _get_default_cache_dir()
            cache_dir.mkdir(parents=True, exist_ok=True)
            db_path = cache_dir / "entities.db"
        
        self._db_path = Path(db_path)
        
        # Initialize storage
        if backend == "sqlite":
            self._store: EntityStoreProtocol = SQLiteStore(self._db_path)
        else:
            raise ValueError(f"Unsupported backend: {backend}")
        
        # Initialize schema
        self._store.initialize()
        
        # Auto-download SEC data if needed
        if auto_download and self._is_empty():
            self._download_sec_data()
    
    def _is_empty(self) -> bool:
        """Check if database is empty."""
        return self._store.entity_count() == 0
    
    def _download_sec_data(self) -> None:
        """Download and load SEC company_tickers.json."""
        fetcher = SECFetcher()
        data = fetcher.fetch_company_tickers()
        self._store.load_sec_json(data)
    
    def resolve(
        self,
        query: str,
        as_of: date | None = None,
        limit: int = 10,
    ) -> ResolutionResult:
        """
        Resolve any identifier to ranked entity candidates.
        
        Args:
            query: CIK, ticker, name, or other identifier.
            as_of: Point-in-time for resolution (default: today).
            limit: Maximum candidates to return.
        
        Returns:
            ResolutionResult with ranked candidates.
        
        Example:
            >>> result = resolver.resolve("AAPL")
            >>> result.best.entity_id
            '01ARZ3NDEKTSV4RRFFQ69G5FAV'
        """
        as_of = as_of or date.today()
        
        # Detect identifier type and resolve
        if self._looks_like_cik(query):
            return self.resolve_cik(query)
        elif self._looks_like_ticker(query):
            return self.resolve_ticker(query, as_of=as_of)
        else:
            return self._resolve_name(query, limit=limit)
    
    def resolve_cik(self, cik: str) -> ResolutionResult:
        """Resolve SEC CIK to entity candidates."""
        from entityspine.core.normalize import normalize_cik
        
        cik_normalized = normalize_cik(cik)
        claims = self._store.get_claims(scheme="cik", value=cik_normalized)
        
        candidates = []
        for claim in claims:
            if claim.entity_id:
                candidates.append(ResolutionCandidate(
                    entity_id=claim.entity_id,
                    score=claim.confidence,
                    match_type="exact",
                    matched_value=cik_normalized,
                    matched_scheme="cik",
                ))
        
        return ResolutionResult(
            candidates=sorted(candidates, key=lambda c: c.score, reverse=True),
            query=cik,
            as_of=date.today(),
        )
    
    def resolve_ticker(
        self,
        ticker: str,
        mic: str | None = None,
        as_of: date | None = None,
    ) -> ResolutionResult:
        """
        Resolve ticker to entity via Listing → Security → Entity.
        
        Args:
            ticker: Stock ticker symbol.
            mic: Market Identifier Code (optional).
            as_of: Point-in-time (default: today).
        
        Returns:
            ResolutionResult with entity candidates.
        """
        as_of = as_of or date.today()
        ticker_upper = ticker.strip().upper()
        
        listings = self._store.get_listings_by_ticker(
            ticker=ticker_upper,
            mic=mic,
            as_of=as_of,
        )
        
        candidates = []
        for listing in listings:
            # Get security and entity
            security = self._store.get_security(listing.security_id)
            if security:
                entity = self._store.get_entity(security.issuer_entity_id)
                if entity:
                    score = 0.8
                    if listing.is_primary:
                        score += 0.15
                    
                    candidates.append(ResolutionCandidate(
                        entity_id=entity.entity_id,
                        score=min(score, 1.0),
                        match_type="ticker",
                        matched_value=f"{ticker_upper}:{listing.mic or 'ANY'}",
                        matched_scheme="ticker",
                        listing_id=listing.listing_id,
                        security_id=listing.security_id,
                    ))
        
        return ResolutionResult(
            candidates=sorted(candidates, key=lambda c: c.score, reverse=True),
            query=ticker,
            as_of=as_of,
        )
    
    def get(self, entity_id: str) -> Entity | None:
        """
        Get entity by ID, following merge redirects.
        
        Args:
            entity_id: Entity ULID.
        
        Returns:
            Entity or None if not found.
        """
        return self._store.get_entity(entity_id)
    
    def get_canonical(self, entity_id: str) -> tuple[Entity | None, list[str]]:
        """
        Get entity and redirect chain.
        
        Returns:
            (entity, chain) where chain shows merge path.
        """
        chain = [entity_id]
        current = entity_id
        
        for _ in range(10):  # Max redirect depth
            entity = self._store.get_entity_raw(current)
            if entity is None:
                return None, chain
            if entity.merged_into_id is None:
                return entity, chain
            current = entity.merged_into_id
            chain.append(current)
        
        # Too many redirects
        return None, chain
    
    @property
    def entity_count(self) -> int:
        """Number of entities in database."""
        return self._store.entity_count()
    
    def _looks_like_cik(self, query: str) -> bool:
        """Check if query looks like a CIK."""
        digits = "".join(c for c in query if c.isdigit())
        return len(digits) >= 6 and len(digits) <= 10
    
    def _looks_like_ticker(self, query: str) -> bool:
        """Check if query looks like a ticker."""
        return len(query) <= 5 and query.isalpha()
    
    def _resolve_name(self, query: str, limit: int) -> ResolutionResult:
        """Resolve by name fuzzy match."""
        aliases = self._store.search_aliases(query, limit=limit)
        
        candidates = []
        for alias in aliases:
            candidates.append(ResolutionCandidate(
                entity_id=alias.entity_id,
                score=alias.similarity,
                match_type="name_fuzzy",
                matched_value=alias.alias_text,
            ))
        
        return ResolutionResult(
            candidates=candidates,
            query=query,
            as_of=date.today(),
        )
```

---

## Test Structure

### Directory Layout (Mirrors Source)

```
tests/
├── conftest.py                          # Shared fixtures
│
├── unit/                                # Unit tests (no external deps)
│   ├── core/
│   │   ├── test_ulid.py                 # ULID generation
│   │   ├── test_normalize.py            # ID normalization
│   │   └── test_exceptions.py           # Exception hierarchy
│   │
│   ├── domain/
│   │   ├── models/
│   │   │   ├── test_entity.py           # Entity model
│   │   │   ├── test_security.py         # Security model
│   │   │   ├── test_listing.py          # Listing model
│   │   │   ├── test_claim.py            # IdentifierClaim model
│   │   │   └── test_resolution.py       # ResolutionResult
│   │   └── protocols/
│   │       └── test_protocols.py        # Protocol compliance
│   │
│   ├── infrastructure/
│   │   └── storage/
│   │       ├── test_sqlite_store.py     # SQLite backend
│   │       ├── test_json_store.py       # JSON backend
│   │       └── test_protocol_compliance.py
│   │
│   └── application/
│       └── test_resolver.py             # Resolver service
│
├── integration/                         # Integration tests
│   ├── test_resolution_flow.py          # End-to-end resolution
│   ├── test_merge_redirect.py           # Merge chain following
│   ├── test_simple_api.py               # Public API
│   └── test_pysecedgar_port.py          # py-sec-edgar integration
│
└── fixtures/                            # Test data
    ├── sample_sec_json.json
    └── sample_entities.sql
```

---

## Simple Interface Design

### For py-sec-edgar Integration

```python
# In py-sec-edgar codebase:

from entityspine import EntityResolver

# One-time setup (lazy initialization)
_resolver = None

def get_resolver() -> EntityResolver:
    """Get singleton resolver instance."""
    global _resolver
    if _resolver is None:
        _resolver = EntityResolver()  # Auto-downloads SEC data
    return _resolver


# Usage in filing processor
def process_filing(filing_data: dict) -> None:
    resolver = get_resolver()
    
    # Resolve filer CIK
    cik = filing_data["cik"]
    result = resolver.resolve_cik(cik)
    
    if result.best:
        # Store reference to entityspine entity
        filing_data["filer_entity_id"] = result.best.entity_id
```

### Hiding Complexity

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          COMPLEXITY HIDING                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  User sees:                          Under the hood:                        │
│  ──────────                          ──────────────                         │
│                                                                             │
│  resolver = EntityResolver()         • Check for cached SEC JSON            │
│                                      • Download if needed                   │
│                                      • Parse and validate                   │
│                                      • Create SQLite database               │
│                                      • Load entities/securities/listings   │
│                                      • Create identifier claims             │
│                                      • Build indexes                        │
│                                                                             │
│  result = resolver.resolve("AAPL")   • Detect identifier type (ticker)     │
│                                      • Query listings table                 │
│                                      • Filter by valid_from/valid_to       │
│                                      • Join to securities                   │
│                                      • Join to entities                     │
│                                      • Follow merge redirects               │
│                                      • Score candidates                     │
│                                      • Return ranked results                │
│                                                                             │
│  entity = resolver.get(entity_id)    • Query entities table                 │
│                                      • Follow merged_into_id chain         │
│                                      • Return canonical entity              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Reference Documents

Read these in order when implementing:

| Phase | Document | Purpose |
|-------|----------|---------|
| 0 | `GUARDRAILS.md` | Code standards |
| 0 | `MANIFESTO.md` | Design philosophy |
| 1-5 | `00_UNIFIED_DATA_MODEL_V2_2.md` | Schema reference |
| 4 | `01_RESOLUTION_AND_TEMPORALITY.md` | Resolution algorithms |
| 5 | `02_PYSECEDGAR_INTEGRATION_CONTRACT.md` | Integration patterns |

---

## Decision Log

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | dataclasses over Pydantic for core | Zero deps in Tier 0-1 |
| 2 | Raw sqlite3 over SQLAlchemy | Zero deps in Tier 0-1 |
| 3 | TDD for every component | Catch issues early, document behavior |
| 4 | Models before storage | Define contract before implementation |
| 5 | Simple facade last | Build on solid foundation |
| 6 | Auto-download SEC data | Maximum simplicity for users |

---

*EntitySpine Implementation Blueprint v2.2 | January 2026*
