# EntitySpine SQLite Operational Best Practices

**Status**: Normative  
**Audience**: Implementers

---

## Table of Contents

1. [Overview](#overview)
2. [PRAGMA Configuration](#pragma-configuration)
3. [Timestamp Conventions](#timestamp-conventions)
4. [Connection Lifecycle](#connection-lifecycle)
5. [Redirect Chain Safety](#redirect-chain-safety)
6. [Schema Conventions](#schema-conventions)
7. [Testing Considerations](#testing-considerations)
8. [Performance Guidelines](#performance-guidelines)
9. [Decision Log](#decision-log)
10. [Known Limitations / Open Questions](#known-limitations--open-questions)

---

## Overview

This document defines operational best practices for SQLite-based EntitySpine storage. These practices ensure data integrity, performance, and testability.

### Why SQLite?

SQLite is the default Tier 1 backend because:
- Zero external dependencies (stdlib `sqlite3`)
- Single-file database (portable)
- ACID compliant
- Fast for read-heavy workloads
- Supports full-text search (FTS5)

---

## PRAGMA Configuration

### Required PRAGMAs

```python
# src/entityspine/infrastructure/storage/sqlite_store.py

class SQLiteStore:
    """SQLite storage with proper PRAGMA configuration."""
    
    # PRAGMA settings applied on every connection
    PRAGMAS = [
        # REQUIRED: Enforce foreign key constraints
        "PRAGMA foreign_keys = ON",
        
        # RECOMMENDED: Write-Ahead Logging for better concurrency
        "PRAGMA journal_mode = WAL",
        
        # RECOMMENDED: Synchronous mode (NORMAL is safe with WAL)
        "PRAGMA synchronous = NORMAL",
        
        # RECOMMENDED: Store temp tables in memory
        "PRAGMA temp_store = MEMORY",
        
        # RECOMMENDED: Increase cache size (negative = KB)
        "PRAGMA cache_size = -64000",  # 64MB
        
        # RECOMMENDED: Memory-mapped I/O size
        "PRAGMA mmap_size = 268435456",  # 256MB
    ]
    
    def _configure_connection(self, conn: sqlite3.Connection) -> None:
        """Apply PRAGMA settings to connection."""
        for pragma in self.PRAGMAS:
            conn.execute(pragma)
```

### PRAGMA Explanations

| PRAGMA | Value | Why |
|--------|-------|-----|
| `foreign_keys` | `ON` | **REQUIRED**: Enforce referential integrity |
| `journal_mode` | `WAL` | Better concurrency, safer than default |
| `synchronous` | `NORMAL` | Safe with WAL, better performance |
| `temp_store` | `MEMORY` | Faster temp table operations |
| `cache_size` | `-64000` | 64MB cache (negative = KB) |
| `mmap_size` | `268435456` | 256MB memory-mapped I/O |

### Testing PRAGMA Application

```python
def test_foreign_keys_enabled(self, temp_db):
    """Foreign key constraints must be enabled."""
    store = SQLiteStore(temp_db)
    store.initialize()
    
    result = store._conn.execute("PRAGMA foreign_keys").fetchone()
    assert result[0] == 1, "PRAGMA foreign_keys must be ON"

def test_wal_mode_enabled(self, temp_db):
    """WAL mode should be enabled for better concurrency."""
    store = SQLiteStore(temp_db)
    store.initialize()
    
    result = store._conn.execute("PRAGMA journal_mode").fetchone()
    assert result[0].upper() == "WAL"
```

---

## Timestamp Conventions

### Timezone-Aware UTC

All timestamps must be:
1. **Timezone-aware** (not naive)
2. **UTC** (not local time)
3. **Stored as ISO-8601 strings** in SQLite

### Timestamp Helper Functions

```python
# src/entityspine/core/timestamps.py
"""Timestamp utilities for consistent timezone handling."""

from datetime import datetime, timezone


def utc_now() -> datetime:
    """
    Get current UTC timestamp (timezone-aware).
    
    Returns:
        datetime with tzinfo=timezone.utc
    
    Example:
        >>> ts = utc_now()
        >>> ts.tzinfo
        datetime.timezone.utc
    """
    return datetime.now(timezone.utc)


def to_iso8601(dt: datetime) -> str:
    """
    Convert datetime to ISO-8601 string for SQLite storage.
    
    Args:
        dt: Datetime (naive or aware).
    
    Returns:
        ISO-8601 string with 'Z' suffix for UTC.
    
    Example:
        >>> to_iso8601(datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc))
        '2024-01-15T10:30:00Z'
    """
    if dt.tzinfo is None:
        # Treat naive datetime as UTC
        dt = dt.replace(tzinfo=timezone.utc)
    
    # Convert to UTC if not already
    utc_dt = dt.astimezone(timezone.utc)
    
    # Format with Z suffix
    return utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def from_iso8601(s: str) -> datetime:
    """
    Parse ISO-8601 string from SQLite to timezone-aware datetime.
    
    Args:
        s: ISO-8601 string (with or without Z suffix).
    
    Returns:
        Timezone-aware datetime (UTC).
    
    Example:
        >>> from_iso8601('2024-01-15T10:30:00Z')
        datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
    """
    if s is None:
        return None
    
    # Handle Z suffix
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    
    # Parse with timezone
    dt = datetime.fromisoformat(s)
    
    # Ensure UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    
    return dt.astimezone(timezone.utc)
```

### Updated Dataclass Defaults

```python
# src/entityspine/domain/models/entity.py
from entityspine.core.timestamps import utc_now

@dataclass(frozen=True, slots=True)
class Entity:
    """Entity with proper UTC timestamps."""
    
    # ... other fields ...
    
    # Use utc_now() instead of datetime.now()
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
```

### SQLite Storage

```python
# Storing timestamps
def _insert_entity(self, entity: Entity) -> None:
    self._conn.execute(
        """
        INSERT INTO entities (entity_id, primary_name, created_at, updated_at)
        VALUES (?, ?, ?, ?)
        """,
        (
            entity.entity_id,
            entity.primary_name,
            to_iso8601(entity.created_at),
            to_iso8601(entity.updated_at),
        )
    )

# Retrieving timestamps
def _row_to_entity(self, row: sqlite3.Row) -> Entity:
    return Entity(
        entity_id=row["entity_id"],
        primary_name=row["primary_name"],
        created_at=from_iso8601(row["created_at"]),
        updated_at=from_iso8601(row["updated_at"]),
    )
```

---

## Connection Lifecycle

### Connection Management

```python
class SQLiteStore:
    """SQLite store with proper connection lifecycle."""
    
    def __init__(self, db_path: Path | str):
        self._db_path = Path(db_path)
        self._conn: sqlite3.Connection | None = None
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get or create connection."""
        if self._conn is None:
            self._conn = sqlite3.connect(
                self._db_path,
                check_same_thread=False,  # Allow multi-thread access
            )
            self._conn.row_factory = sqlite3.Row
            self._configure_connection(self._conn)
        return self._conn
    
    def close(self) -> None:
        """Close connection and release resources."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None
    
    def __enter__(self) -> "SQLiteStore":
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - always close."""
        self.close()
    
    def __del__(self) -> None:
        """Destructor - close if still open."""
        self.close()
```

### Usage Patterns

```python
# Pattern 1: Context manager (preferred for short-lived)
with SQLiteStore("entities.db") as store:
    store.initialize()
    entity = store.get_entity("...")

# Pattern 2: Long-lived (for applications)
store = SQLiteStore("entities.db")
store.initialize()
# ... use store ...
store.close()  # Explicit cleanup

# Pattern 3: EntityResolver manages store lifecycle
resolver = EntityResolver(db_path="entities.db")
# Store is created internally
# Resolver.close() closes store
```

---

## Redirect Chain Safety

### Constants

```python
# src/entityspine/core/constants.py
"""EntitySpine constants."""

# Maximum redirect chain depth (prevent infinite loops)
MAX_REDIRECT_DEPTH = 10

# Maximum cycle detection depth
MAX_CYCLE_DETECTION = MAX_REDIRECT_DEPTH * 2
```

### Safe Redirect Following

```python
def get_entity(self, entity_id: str) -> Entity | None:
    """
    Get entity by ID, following merge redirects safely.
    
    Implements:
    - Cycle detection
    - Max depth limit
    - Returns canonical entity
    """
    entity, chain, cycle_detected, truncated = self.get_canonical(entity_id)
    return entity


def get_canonical(
    self,
    entity_id: str,
) -> tuple[Entity | None, list[str], bool, bool]:
    """
    Get entity with full redirect chain information.
    
    Args:
        entity_id: Starting entity ID.
    
    Returns:
        Tuple of:
        - Entity (canonical) or None if not found
        - chain: List of entity_ids traversed
        - cycle_detected: True if circular reference found
        - truncated: True if MAX_REDIRECT_DEPTH reached
    """
    from entityspine.core.constants import MAX_REDIRECT_DEPTH
    
    chain: list[str] = []
    seen: set[str] = set()
    current_id = entity_id
    cycle_detected = False
    truncated = False
    
    for depth in range(MAX_REDIRECT_DEPTH + 1):
        # Check for cycle
        if current_id in seen:
            cycle_detected = True
            break
        
        seen.add(current_id)
        chain.append(current_id)
        
        # Get entity without following redirects
        entity = self.get_entity_raw(current_id)
        
        if entity is None:
            # Entity not found
            return None, chain, cycle_detected, truncated
        
        if entity.merged_into_id is None:
            # Found canonical entity
            return entity, chain, cycle_detected, truncated
        
        # Follow redirect
        current_id = entity.merged_into_id
        
        if depth == MAX_REDIRECT_DEPTH:
            truncated = True
    
    # Max depth reached without finding canonical
    # Return last entity found
    return self.get_entity_raw(chain[-1]), chain, cycle_detected, truncated
```

### Testing Redirect Safety

```python
class TestRedirectChainSafety:
    """Tests for redirect chain safety features."""
    
    def test_cycle_detection(self, storage_with_cycle):
        """Should detect circular merge references."""
        # Setup: A → B → C → A (cycle)
        entity, chain, cycle_detected, truncated = storage_with_cycle.get_canonical("A")
        
        assert cycle_detected is True
        assert "A" in chain
    
    def test_max_depth_truncation(self, storage_with_long_chain):
        """Should truncate at MAX_REDIRECT_DEPTH."""
        from entityspine.core.constants import MAX_REDIRECT_DEPTH
        
        # Setup: chain of MAX_REDIRECT_DEPTH + 5 merges
        entity, chain, cycle_detected, truncated = storage_with_long_chain.get_canonical("start")
        
        assert truncated is True
        assert len(chain) <= MAX_REDIRECT_DEPTH + 1
    
    def test_normal_redirect_chain(self, storage):
        """Normal redirect chain works correctly."""
        # Setup: A → B → C (C is canonical)
        entity, chain, cycle_detected, truncated = storage.get_canonical("A")
        
        assert entity.entity_id == "C"
        assert chain == ["A", "B", "C"]
        assert cycle_detected is False
        assert truncated is False
```

---

## Schema Conventions

### Table Naming

- Lowercase with underscores: `entities`, `identifier_claims`
- Plural for collections: `entities`, not `entity`
- Foreign key columns end with `_id`: `entity_id`, `security_id`

### Column Naming

- Lowercase with underscores
- Boolean columns: `is_primary`, `is_active`
- Timestamps: `created_at`, `updated_at`, `merged_at`
- Foreign keys: `{table_singular}_id`

### Index Naming

```sql
-- Pattern: idx_{table}_{column(s)}
CREATE INDEX idx_entities_status ON entities(status);
CREATE INDEX idx_claims_scheme_value ON identifier_claims(scheme, value);
CREATE INDEX idx_listings_ticker_valid ON listings(ticker, valid_from, valid_to);
```

### Constraints

```sql
-- Primary keys
entity_id TEXT PRIMARY KEY

-- Foreign keys (enforced by PRAGMA foreign_keys=ON)
REFERENCES entities(entity_id)

-- Unique constraints
UNIQUE(ticker, mic, valid_from)

-- Check constraints
CHECK(confidence >= 0.0 AND confidence <= 1.0)
CHECK(status IN ('active', 'merged', 'provisional', 'inactive'))
```

---

## Testing Considerations

### Avoid Testing Private Methods

```python
# ❌ BAD: Testing private helper methods
def test_get_tables(self, store):
    tables = store._get_tables()  # Don't test private methods
    assert "entities" in tables

# ✅ GOOD: Test via public interface
def test_initialize_creates_tables(self, temp_db):
    store = SQLiteStore(temp_db)
    store.initialize()
    
    # Verify by attempting operations that require tables
    count = store.entity_count()
    assert count == 0  # Empty but table exists
```

### Public Introspection API (If Needed)

If tests need to verify schema state, add public methods:

```python
class SQLiteStore:
    """SQLite store with optional introspection API."""
    
    def get_table_names(self) -> list[str]:
        """
        Get list of table names in database.
        
        Intended for testing and debugging.
        """
        rows = self._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        return [row[0] for row in rows]
    
    def get_column_names(self, table: str) -> list[str]:
        """
        Get list of column names for a table.
        
        Intended for testing and debugging.
        """
        rows = self._conn.execute(f"PRAGMA table_info({table})").fetchall()
        return [row[1] for row in rows]
```

### Fixture Guidelines

```python
@pytest.fixture
def temp_db(tmp_path) -> Path:
    """
    Temporary database path.
    
    Creates a unique path for each test.
    File is automatically cleaned up after test.
    """
    return tmp_path / "test.db"


@pytest.fixture
def initialized_store(temp_db) -> SQLiteStore:
    """
    Initialized SQLite store.
    
    Properly closes after test.
    """
    store = SQLiteStore(temp_db)
    store.initialize()
    yield store
    store.close()
```

---

## Performance Guidelines

### Batch Operations

```python
def store_entities(self, entities: list[Entity]) -> None:
    """
    Store multiple entities efficiently.
    
    Uses executemany for batch insert.
    """
    conn = self._get_connection()
    
    data = [
        (e.entity_id, e.primary_name, to_iso8601(e.created_at))
        for e in entities
    ]
    
    conn.executemany(
        "INSERT OR REPLACE INTO entities (entity_id, primary_name, created_at) VALUES (?, ?, ?)",
        data
    )
    conn.commit()
```

### Transaction Boundaries

```python
def load_sec_json(self, data: dict) -> int:
    """Load SEC JSON with transaction."""
    conn = self._get_connection()
    
    try:
        # Start transaction
        conn.execute("BEGIN TRANSACTION")
        
        count = 0
        for entry in data.values():
            self._create_entity_from_sec(entry)
            count += 1
        
        # Commit
        conn.commit()
        return count
        
    except Exception:
        # Rollback on error
        conn.rollback()
        raise
```

---

## Decision Log

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | `PRAGMA foreign_keys=ON` required | Data integrity is non-negotiable |
| 2 | WAL mode recommended | Better concurrency, safer |
| 3 | UTC timestamps always | Consistency across systems |
| 4 | ISO-8601 string storage | Human-readable, sortable |
| 5 | MAX_REDIRECT_DEPTH = 10 | Reasonable limit, catches most issues |
| 6 | Return 4-tuple from get_canonical | Need cycle_detected and truncated flags |
| 7 | Avoid testing private methods | Tests should verify behavior, not implementation |
| 8 | Public introspection API if needed | Better than testing privates |

---

## Known Limitations / Open Questions

### Limitations

1. **Single-writer limitation**: SQLite doesn't handle concurrent writes well.
2. **No advisory locks**: Can't prevent multiple processes writing.
3. **WAL file cleanup**: WAL files may grow; need periodic checkpointing.

### Open Questions

1. **Should we add connection pooling for SQLite?**
   - Probably overkill for single-file DB
   - But could help with read concurrency

2. **Should we support read-only mode?**
   - Would allow multiple readers without locking
   - `sqlite3.connect(..., mode='ro')`

3. **Should we auto-checkpoint WAL?**
   - `PRAGMA wal_checkpoint(TRUNCATE)` periodically
   - Or let SQLite handle it automatically

---

*EntitySpine SQLite Best Practices v2.2.1 | January 2026*
