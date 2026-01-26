# Migration Notes: v2.1 → v2.2

**Companion to Unified Data Model v2.2**

> This document describes how to migrate from v2.1 schema to v2.2 schema,  
> including breaking changes, data migration scripts, and compatibility notes.

---

## Table of Contents

1. [Breaking Changes Summary](#breaking-changes-summary)
2. [Schema Changes](#schema-changes)
3. [API Changes](#api-changes)
4. [Migration Steps](#migration-steps)
5. [Rollback Plan](#rollback-plan)
6. [Compatibility Matrix](#compatibility-matrix)

---

## Breaking Changes Summary

### High Impact ⚠️

| Change | Impact | Migration Effort |
|--------|--------|------------------|
| `SimpleEntity.ticker` removed | All code using ticker on entity | Medium |
| `entities.ticker` column dropped (Tier 1) | SQLite schema change | Low |
| `entities.exchange` column dropped (Tier 1) | SQLite schema change | Low |
| `identifiers` → `identifier_claims` | Table rename + new columns | Medium |
| `resolve()` returns `list` not `Entity | None` | All resolution call sites | High |

### Medium Impact

| Change | Impact | Migration Effort |
|--------|--------|------------------|
| New `securities` table required (Tier 1) | Schema addition | Low |
| New `listings` table required (Tier 1) | Schema addition | Low |
| `merged_into_id` on entities | New column | Low |
| Claims require `source_system` | Data quality | Low |

### Low Impact

| Change | Impact | Migration Effort |
|--------|--------|------------------|
| New `scheme_registry` table (Tier 3) | Optional enhancement | None |
| New `merge_events` table | Audit trail | None |
| New `vendor_crosswalks` table | Vendor support | None |

---

## Schema Changes

### Tier 0: JSON

**v2.1 (incorrect)**
```python
@dataclass
class SimpleEntity:
    entity_id: str
    cik: str
    ticker: str       # ❌ Scope violation
    name: str
    exchange: str     # ❌ Scope violation
```

**v2.2 (correct)**
```python
@dataclass
class Tier0Entity:
    """Read-only entity from SEC JSON."""
    cik: str
    name: str
    
    # DERIVED from SEC file (not entity property)
    primary_ticker: str | None = None  # Clearly marked as derived
    
    source: str = "sec_company_tickers"
    source_date: date | None = None
```

### Tier 1: SQLite

**v2.1 entities table**
```sql
-- OLD (v2.1)
CREATE TABLE entities (
    entity_id TEXT PRIMARY KEY,
    cik TEXT UNIQUE NOT NULL,
    ticker TEXT,              -- ❌ REMOVE
    name TEXT NOT NULL,
    exchange TEXT,            -- ❌ REMOVE
    sic_code TEXT,
    entity_type TEXT DEFAULT 'COMPANY',
    status TEXT DEFAULT 'active',
    created_at TEXT,
    updated_at TEXT
);
```

**v2.2 entities table**
```sql
-- NEW (v2.2)
CREATE TABLE entities (
    entity_id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL DEFAULT 'COMPANY',
    status TEXT NOT NULL DEFAULT 'active',
    legal_name TEXT,
    primary_name TEXT NOT NULL,
    sic_code TEXT,
    source_system TEXT NOT NULL,
    source_id TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    merged_into_id TEXT REFERENCES entities(entity_id),  -- ✅ NEW
    merged_at TEXT                                        -- ✅ NEW
);
```

**v2.2 NEW tables**
```sql
-- Securities (NEW in v2.2)
CREATE TABLE securities (
    security_id TEXT PRIMARY KEY,
    issuer_entity_id TEXT NOT NULL REFERENCES entities(entity_id),
    security_type TEXT NOT NULL,
    name TEXT NOT NULL,
    currency TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    source_system TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Listings (NEW in v2.2)
CREATE TABLE listings (
    listing_id TEXT PRIMARY KEY,
    security_id TEXT NOT NULL REFERENCES securities(security_id),
    ticker TEXT NOT NULL,
    mic TEXT,
    is_primary INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'active',
    valid_from TEXT NOT NULL,
    valid_to TEXT,
    source_system TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(ticker, mic, valid_from)
);

-- Identifier Claims (replaces identifiers)
CREATE TABLE identifier_claims (
    claim_id TEXT PRIMARY KEY,
    entity_id TEXT REFERENCES entities(entity_id),
    security_id TEXT REFERENCES securities(security_id),
    listing_id TEXT REFERENCES listings(listing_id),
    scheme TEXT NOT NULL,
    value TEXT NOT NULL,
    source_system TEXT NOT NULL,       -- ✅ NEW required
    confidence REAL NOT NULL DEFAULT 1.0,
    captured_at TEXT NOT NULL DEFAULT (datetime('now')),
    valid_from TEXT,
    valid_to TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    CHECK (...)
);
```

### Tier 3: PostgreSQL

Same conceptual changes as Tier 1, plus:
- `scheme_registry` table (new)
- `claim_conflicts` table (new)
- `merge_events` table (new)
- `vendor_crosswalks` table (new)

See [00_UNIFIED_DATA_MODEL_V2_2.md](00_UNIFIED_DATA_MODEL_V2_2.md) for full DDL.

---

## API Changes

### Resolution Return Type

**v2.1 (incorrect)**
```python
def resolve(self, query: str) -> Entity | None:
    """Returns single entity or None."""
    ...

# Usage:
entity = resolver.resolve("AAPL")
if entity:
    print(entity.name)
```

**v2.2 (correct)**
```python
def resolve(
    self, 
    query: str, 
    as_of: date | None = None,
    limit: int = 10
) -> ResolutionResult:
    """Returns ranked candidates with metadata."""
    ...

# Usage:
result = resolver.resolve("AAPL")
if result.best and result.best.score >= 0.9:
    entity = resolver.get(result.best.entity_id)
    print(entity.name)
```

### Migration Helper

```python
# Compatibility shim for v2.1 callers
def resolve_v21_compat(resolver, query: str) -> Entity | None:
    """
    Compatibility wrapper that mimics v2.1 behavior.
    
    ⚠️ DEPRECATED: Migrate to v2.2 API.
    """
    import warnings
    warnings.warn(
        "resolve_v21_compat is deprecated, use resolve() directly",
        DeprecationWarning
    )
    
    result = resolver.resolve(query)
    if result.best and result.best.score >= 0.9:
        return resolver.get(result.best.entity_id)
    return None
```

### Entity Access

**v2.1 (incorrect)**
```python
# Direct attribute access
entity = resolver.resolve("AAPL")
print(entity.ticker)   # ❌ Scope violation
print(entity.exchange) # ❌ Scope violation
```

**v2.2 (correct)**
```python
# Proper hierarchy traversal
result = resolver.resolve_ticker("AAPL")
if result.best:
    # Get the listing that matched
    listing = resolver.get_listing(result.best.listing_id)
    print(listing.ticker)  # ✅ Correct scope
    print(listing.mic)     # ✅ Correct scope
    
    # Get the underlying entity
    entity = resolver.get(result.best.entity_id)
    print(entity.primary_name)  # ✅ Entity attribute
```

---

## Migration Steps

### Step 1: Backup Existing Data

```bash
# SQLite
cp entities.db entities_v21_backup.db

# PostgreSQL
pg_dump entityspine > entityspine_v21_backup.sql
```

### Step 2: Create New Tables (Additive)

```sql
-- Add new tables without modifying existing ones yet
-- SQLite example

CREATE TABLE IF NOT EXISTS securities (
    security_id TEXT PRIMARY KEY,
    issuer_entity_id TEXT NOT NULL,
    security_type TEXT NOT NULL DEFAULT 'common_stock',
    name TEXT NOT NULL,
    currency TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    source_system TEXT NOT NULL DEFAULT 'migration',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS listings (
    listing_id TEXT PRIMARY KEY,
    security_id TEXT NOT NULL,
    ticker TEXT NOT NULL,
    mic TEXT,
    is_primary INTEGER NOT NULL DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'active',
    valid_from TEXT NOT NULL DEFAULT '1900-01-01',
    valid_to TEXT,
    source_system TEXT NOT NULL DEFAULT 'migration',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS identifier_claims (
    claim_id TEXT PRIMARY KEY,
    entity_id TEXT,
    security_id TEXT,
    listing_id TEXT,
    scheme TEXT NOT NULL,
    value TEXT NOT NULL,
    source_system TEXT NOT NULL DEFAULT 'migration',
    confidence REAL NOT NULL DEFAULT 1.0,
    captured_at TEXT NOT NULL DEFAULT (datetime('now')),
    valid_from TEXT,
    valid_to TEXT,
    status TEXT NOT NULL DEFAULT 'active'
);
```

### Step 3: Migrate Existing Data

```sql
-- Migrate entities.ticker → securities + listings

-- 1. Create securities for each entity that had a ticker
INSERT INTO securities (security_id, issuer_entity_id, security_type, name, source_system)
SELECT 
    'S' || substr(entity_id, 2),  -- Derive security_id from entity_id
    entity_id,
    'common_stock',
    name || ' Common Stock',
    'v21_migration'
FROM entities
WHERE ticker IS NOT NULL AND ticker != '';

-- 2. Create listings for each security
INSERT INTO listings (listing_id, security_id, ticker, mic, is_primary, valid_from, source_system)
SELECT 
    'L' || substr(entity_id, 2),
    'S' || substr(entity_id, 2),
    ticker,
    CASE exchange
        WHEN 'NASDAQ' THEN 'XNAS'
        WHEN 'NYSE' THEN 'XNYS'
        WHEN 'AMEX' THEN 'XASE'
        ELSE 'XXXX'
    END,
    1,
    '1900-01-01',  -- Unknown start date
    'v21_migration'
FROM entities
WHERE ticker IS NOT NULL AND ticker != '';

-- 3. Migrate identifiers → identifier_claims
INSERT INTO identifier_claims (claim_id, entity_id, scheme, value, source_system, captured_at)
SELECT 
    'C' || id,
    entity_id,
    scheme,
    value,
    COALESCE(source, 'v21_migration'),
    COALESCE(created_at, datetime('now'))
FROM identifiers;
```

### Step 4: Add New Columns to Entities

```sql
-- Add merge support columns
ALTER TABLE entities ADD COLUMN merged_into_id TEXT REFERENCES entities(entity_id);
ALTER TABLE entities ADD COLUMN merged_at TEXT;

-- Add source_system if missing
ALTER TABLE entities ADD COLUMN source_system TEXT DEFAULT 'v21_migration';
UPDATE entities SET source_system = 'v21_migration' WHERE source_system IS NULL;
```

### Step 5: Update Application Code

```python
# Before (v2.1)
entity = resolver.resolve("AAPL")
if entity:
    process_filing(entity.entity_id, entity.ticker)

# After (v2.2)
result = resolver.resolve("AAPL")
if result.best and result.best.score >= 0.9:
    entity = resolver.get(result.best.entity_id)
    # Get ticker from listing, not entity
    listing = resolver.get_listing(result.best.listing_id)
    process_filing(entity.entity_id, listing.ticker if listing else None)
```

### Step 6: Remove Deprecated Columns

```sql
-- Only after application code is migrated and tested

-- SQLite doesn't support DROP COLUMN easily, so recreate table
CREATE TABLE entities_new (
    entity_id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL DEFAULT 'COMPANY',
    status TEXT NOT NULL DEFAULT 'active',
    legal_name TEXT,
    primary_name TEXT NOT NULL,
    sic_code TEXT,
    source_system TEXT NOT NULL,
    source_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    merged_into_id TEXT,
    merged_at TEXT
);

INSERT INTO entities_new 
SELECT entity_id, entity_type, status, legal_name, name, sic_code, 
       source_system, source_id, created_at, updated_at, merged_into_id, merged_at
FROM entities;

DROP TABLE entities;
ALTER TABLE entities_new RENAME TO entities;

-- Drop old identifiers table
DROP TABLE IF EXISTS identifiers;
```

### Step 7: Create Indexes

```sql
CREATE INDEX IF NOT EXISTS idx_securities_issuer ON securities(issuer_entity_id);
CREATE INDEX IF NOT EXISTS idx_listings_ticker ON listings(ticker);
CREATE INDEX IF NOT EXISTS idx_listings_security ON listings(security_id);
CREATE INDEX IF NOT EXISTS idx_claims_scheme_value ON identifier_claims(scheme, value);
```

---

## Rollback Plan

### If Migration Fails

```bash
# Restore from backup
# SQLite
cp entities_v21_backup.db entities.db

# PostgreSQL
psql -c "DROP DATABASE entityspine"
psql -c "CREATE DATABASE entityspine"
psql entityspine < entityspine_v21_backup.sql
```

### Partial Rollback (Keep New Tables, Restore Old Columns)

```sql
-- If need to support both v2.1 and v2.2 temporarily
-- Add back deprecated columns as computed/virtual

-- SQLite doesn't support computed columns, use a view instead
CREATE VIEW entities_v21_compat AS
SELECT 
    e.*,
    l.ticker,
    CASE l.mic
        WHEN 'XNAS' THEN 'NASDAQ'
        WHEN 'XNYS' THEN 'NYSE'
        WHEN 'XASE' THEN 'AMEX'
        ELSE l.mic
    END AS exchange
FROM entities e
LEFT JOIN securities s ON s.issuer_entity_id = e.entity_id
    AND s.security_type = 'common_stock'
LEFT JOIN listings l ON l.security_id = s.security_id
    AND l.is_primary = 1
    AND (l.valid_to IS NULL OR l.valid_to > date('now'));
```

---

## Compatibility Matrix

### Package Version Compatibility

| py-sec-edgar | entityspine | Notes |
|--------------|-------------|-------|
| 1.x | 1.x (v2.1) | Full compatibility |
| 1.x | 2.x (v2.2) | ❌ Breaking - must upgrade py-sec-edgar |
| 2.x | 1.x (v2.1) | ❌ Breaking - must upgrade entityspine |
| 2.x | 2.x (v2.2) | ✅ Full compatibility |

### Feature Compatibility

| Feature | v2.1 | v2.2 | Migration Path |
|---------|------|------|----------------|
| CIK resolution | ✅ | ✅ | No change |
| Ticker resolution | ✅ (incorrect scope) | ✅ (correct scope) | Use new API |
| Entity.ticker | ✅ | ❌ Removed | Use listings |
| Ambiguous results | ❌ | ✅ | New feature |
| Merge redirects | ❌ | ✅ | New feature |
| Vendor crosswalks | ❌ | ✅ | New feature |
| Provisional entities | ❌ | ✅ | New feature |

### Timeline

```
Recommended migration timeline:

Week 1:  Create backup, add new tables (Step 1-2)
Week 2:  Migrate data (Step 3-4)
Week 3:  Update application code (Step 5)
Week 4:  Test thoroughly
Week 5:  Remove deprecated columns (Step 6)
Week 6:  Monitor and fix issues
```

---

## Validation Queries

### Verify Migration Completeness

```sql
-- Count entities with securities
SELECT 
    (SELECT COUNT(*) FROM entities WHERE status = 'active') AS entities,
    (SELECT COUNT(*) FROM securities) AS securities,
    (SELECT COUNT(*) FROM listings) AS listings;

-- Verify all tickers migrated
SELECT COUNT(*) AS orphaned_tickers
FROM entities e
WHERE e.ticker IS NOT NULL 
  AND NOT EXISTS (
    SELECT 1 FROM securities s 
    JOIN listings l ON l.security_id = s.security_id
    WHERE s.issuer_entity_id = e.entity_id
  );
-- Should return 0

-- Verify CIK claims exist
SELECT COUNT(*) AS entities_without_cik_claim
FROM entities e
WHERE NOT EXISTS (
    SELECT 1 FROM identifier_claims ic
    WHERE ic.entity_id = e.entity_id
      AND ic.scheme = 'cik'
);
-- Should return 0 (or match entities without CIK)
```

---

## Decision Log

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | Migrate data, don't delete | Preserve historical data |
| 2 | Use derived security_id/listing_id | Maintain traceability |
| 3 | Default valid_from to 1900-01-01 | Unknown history, safe default |
| 4 | Keep compatibility view | Gradual migration support |
| 5 | Require source_system on new rows | Provenance from start |

---

*Migration Notes for Unified Data Model v2.2 | January 2026*
