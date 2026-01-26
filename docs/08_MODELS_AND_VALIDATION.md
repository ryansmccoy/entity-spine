# EntitySpine Model Layers

This document explains the model layer architecture for EntitySpine. The design follows a "canonical domain + optional wrappers" pattern.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                    CANONICAL DOMAIN (stdlib)                        │
│                                                                     │
│  entityspine.domain.*                                               │
│  - @dataclass(frozen=True, slots=True)                              │
│  - ZERO dependencies                                                │
│  - All business rules and validation                                │
│  - Single source of truth                                           │
└─────────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┴─────────────────────┐
        │                                           │
        │ to_domain() / from_domain()               │ row_to_domain()
        ▼                                           ▼
┌───────────────────────────┐       ┌───────────────────────────────┐
│   OPTIONAL PYDANTIC       │       │     OPTIONAL ORM LAYER        │
│                           │       │                               │
│  entityspine.adapters.    │       │  entityspine.adapters.orm.*   │
│  pydantic.*               │       │  - SQLModel/SQLAlchemy tables │
│  - Pydantic v2 models     │       │  - Repository pattern         │
│  - JSON serialization     │       │  - Returns domain dataclasses │
│  - Delegates validation   │       │  - [orm] extra                │
│  - [pydantic] extra       │       └───────────────────────────────┘
└───────────────────────────┘
                                    ┌───────────────────────────────┐
                                    │     STORAGE BACKENDS          │
                                    │                               │
                                    │  entityspine.stores.*         │
                                    │  - json_store (stdlib)        │
                                    │  - sqlite_store (stdlib)      │
                                    │  - duckdb_store ([duckdb])    │
                                    │  - postgres_store ([postgres])│
                                    │  All return domain dataclasses│
                                    └───────────────────────────────┘
```

## Storage Tier Reality

| Tier | Store | Dependencies | as_of Support |
|------|-------|--------------|---------------|
| 0 | `JsonEntityStore` | **stdlib only** | ❌ ignored |
| 1 | `SqliteStore` | **stdlib sqlite3** | ❌ ignored |
| 2 | `DuckDbStore` | duckdb | ✅ temporal |
| 3 | `PostgresStore` | asyncpg/psycopg | ✅ temporal |

**Critical**: Tier 0–1 stores use ONLY stdlib. No SQLModel, no Pydantic.
ORM layers (SQLModel/SQLAlchemy) are optional adapters for advanced use cases.

## Design Principles

### 1. Single Source of Truth

**The domain dataclasses ARE the canonical representation.**

There is exactly one definition for each model:
- `entityspine.domain.Entity`
- `entityspine.domain.Security`
- `entityspine.domain.Listing`
- `entityspine.domain.IdentifierClaim`
- `entityspine.domain.ResolutionResult`
- `entityspine.domain.ResolutionCandidate`

All other representations (Pydantic, ORM) are derived views.

### 2. Zero Dependencies for Core

The domain package (`entityspine.domain`) has ZERO external dependencies:

```python
# Works with just: pip install entityspine
from entityspine import Entity, Security, Listing, IdentifierClaim

entity = Entity(primary_name="Apple Inc.", source_system="sec", source_id="0000320193")
```

### 3. Optional Wrappers Never Compete

Pydantic and ORM models:
- Convert TO/FROM domain (never bypass)
- May have derived/computed fields, but these are **excluded from `to_domain()`**
- Cannot have business logic that domain lacks
- Never used for internal business decisions

```python
# Correct: Pydantic delegates to domain
pydantic_entity.to_domain()  # → Domain dataclass
PydanticEntity.from_domain(domain_entity)  # → Pydantic model

# GUARDRAIL: Wrapper-only fields must NOT leak into domain
class PydanticEntity(BaseModel):
    # Domain fields
    entity_id: str
    primary_name: str
    
    # Wrapper-only derived field (for convenience serialization)
    display_name: str = ""  # ⚠️ EXCLUDED from to_domain()
    
    def to_domain(self) -> DomainEntity:
        # display_name is NOT passed to domain
        return DomainEntity(
            entity_id=self.entity_id,
            primary_name=self.primary_name,
            ...
        )
```

## Package Structure

```
entityspine/
├── domain/                    # CANONICAL (stdlib only)
│   ├── entity.py              # Entity dataclass
│   ├── security.py            # Security dataclass
│   ├── listing.py             # Listing dataclass
│   ├── claim.py               # IdentifierClaim dataclass
│   ├── resolution.py          # ResolutionResult dataclass
│   ├── candidate.py           # ResolutionCandidate dataclass
│   ├── enums.py               # All enums (EntityType, etc.)
│   ├── validators.py          # Normalization/validation (stdlib)
│   ├── protocols.py           # typing.Protocol interfaces
│   └── factories.py           # create_entity(), found_result(), etc.
│
├── stores/                    # STORAGE BACKENDS
│   ├── json_store.py          # Tier 0: stdlib JSON (zero deps)
│   ├── sqlite_store.py        # Tier 1: stdlib sqlite3 (zero deps)
│   ├── duckdb_store.py        # Tier 2: [duckdb] extra
│   └── postgres_store.py      # Tier 3: [postgres] extra
│
├── adapters/                  # OPTIONAL WRAPPERS
│   ├── pydantic/              # [pydantic] extra
│   │   ├── entity.py          # Pydantic Entity with to_domain()
│   │   ├── security.py
│   │   ├── listing.py
│   │   ├── claim.py
│   │   └── ...
│   └── orm/                   # [orm] extra (SQLModel/SQLAlchemy)
│       ├── tables.py          # ORM table definitions
│       ├── repositories.py    # Repository pattern
│       └── engine.py          # Connection management
│
├── core/                      # INTERNAL UTILITIES (stdlib)
│   ├── ulid.py                # ULID generation
│   ├── timestamps.py          # UTC datetime helpers
│   └── exceptions.py          # Custom exceptions
│
└── __init__.py                # Exports domain only (no optional imports)
```

### Entity

Legal/organizational identity (Apple Inc., Warren Buffett).

```python
@dataclass(frozen=True, slots=True)
class Entity:
    entity_id: str  # ULID primary key
    primary_name: str  # Current legal/trading name
    entity_type: EntityType  # organization, person, etc.
    status: EntityStatus  # active, merged, etc.
    
    # Record provenance (NOT identifier provenance)
    source_system: str  # Where this RECORD came from
    source_id: Optional[str]  # ID in source system
    
    # NO identifier fields (cik, lei, ein)
    # Use IdentifierClaim instead
```

### Security

Financial instrument issued by an Entity.

```python
@dataclass(frozen=True, slots=True)
class Security:
    security_id: str  # ULID primary key
    entity_id: str  # FK to issuing Entity
    security_type: SecurityType  # common_stock, etf, bond
    
    # NO identifier fields (isin, cusip, sedol, figi)
    # Use IdentifierClaim instead
```

### Listing

Where/when a Security trades. **TICKER LIVES HERE!**

```python
@dataclass(frozen=True, slots=True)
class Listing:
    listing_id: str  # ULID primary key
    security_id: str  # FK to Security
    ticker: str  # THIS IS WHERE TICKER BELONGS
    exchange: str  # Exchange name
    mic: Optional[str]  # Market Identifier Code
    start_date: Optional[date]  # Validity start
    end_date: Optional[date]  # Validity end
```

### IdentifierClaim

**THE canonical source of truth for all identifiers.**

```python
@dataclass(frozen=True, slots=True)
class IdentifierClaim:
    claim_id: str
    
    # Exactly one target (scheme-scope enforced)
    entity_id: Optional[str]  # For CIK, LEI, EIN, DUNS
    security_id: Optional[str]  # For ISIN, CUSIP, SEDOL, FIGI
    listing_id: Optional[str]  # For TICKER
    
    scheme: IdentifierScheme  # cik, lei, isin, etc.
    value: str  # Normalized identifier value
    namespace: VendorNamespace  # SEC, BLOOMBERG, GLEIF, etc.
    
    # Observation time vs validity time
    captured_at: datetime  # When we observed this
    valid_from: Optional[date]  # When identifier became valid
    valid_to: Optional[date]  # When identifier ended
```

### ResolutionResult

Result of entity resolution with tier honesty.

```python
@dataclass(slots=True)  # NOT frozen - mutable
class ResolutionResult:
    query: str
    status: ResolutionStatus
    tier: ResolutionTier
    
    entity: Optional[Entity]
    security: Optional[Security]
    listing: Optional[Listing]
    candidates: List[ResolutionCandidate]
    
    # Tier capability honesty
    warnings: List[str]  # e.g., "as_of_ignored"
    limits: Dict[str, str]  # e.g., {"temporal_resolution": "current_only"}
    as_of_honored: bool
    
    @property
    def best(self) -> Optional[ResolutionCandidate]:
        """Get highest-scoring candidate."""
```

## Protocols (stdlib typing.Protocol)

All protocols are defined in `entityspine.domain.protocols` using stdlib `typing.Protocol`:

```python
from entityspine import (
    EntityStoreProtocol,
    ResolverProtocol,
    FullStoreProtocol,
)

# Implement your own store
class MyStore(EntityStoreProtocol):
    def get_entity(self, entity_id: str) -> Optional[Entity]:
        ...
    def save_entity(self, entity: Entity) -> None:
        ...
```

## Pydantic Wrappers (Optional)

Pydantic models are thin wrappers for validation/serialization.
Located at `entityspine.adapters.pydantic` (requires `[pydantic]` extra):

```python
from entityspine.adapters.pydantic import Entity as PydanticEntity
from entityspine import Entity as DomainEntity

# Create Pydantic model
pydantic = PydanticEntity(primary_name="Apple Inc.")

# Convert to domain
domain = pydantic.to_domain()

# Convert from domain
pydantic2 = PydanticEntity.from_domain(domain)

# JSON serialization
json_data = pydantic.model_dump_json()
```

**Guardrail**: Wrappers may have derived/computed fields for serialization convenience,
but these fields are **excluded from `to_domain()`** and never used for business logic.

## Validators

All validators live in `entityspine.domain.validators` (stdlib):

```python
from entityspine import (
    normalize_cik,  # "320193" → "0000320193"
    validate_cik,   # Returns (bool, error_msg)
    normalize_and_validate,  # Combined
    SCHEME_SCOPES,  # {"cik": IdentifierScope.ENTITY, ...}
)
```

## Migration Notes

If upgrading from an earlier version where Pydantic was required:

```python
# Earlier approach (Pydantic required)
from entityspine import Entity  # Was Pydantic
entity.model_dump()

# Current approach (stdlib dataclasses)
from entityspine import Entity  # Now dataclass
from dataclasses import asdict
asdict(entity)

# If you need Pydantic wrappers
from entityspine.adapters.pydantic import Entity as PydanticEntity
```

### Identifier Fields Removed

```python
# Earlier approach
entity = Entity(primary_name="Apple", cik="320193")

# Current approach
entity = Entity(primary_name="Apple", source_system="sec", source_id="0000320193")
claim = IdentifierClaim(
    entity_id=entity.entity_id,
    scheme=IdentifierScheme.CIK,
    value="0000320193",
    namespace=VendorNamespace.SEC,
)
```

## Quick Reference

| Layer | Package | Dependencies | Purpose |
|-------|---------|--------------|---------|
| Domain | `entityspine.domain` | **None** (stdlib) | Canonical truth |
| Stores | `entityspine.stores` | **None** (Tier 0-1) | JSON, SQLite storage |
| Pydantic | `entityspine.adapters.pydantic` | `[pydantic]` | Validation/serialization |
| ORM | `entityspine.adapters.orm` | `[orm]` | SQLModel/SQLAlchemy tables |
| DuckDB | `entityspine.stores.duckdb_store` | `[duckdb]` | Analytics (Tier 2) |
| Postgres | `entityspine.stores.postgres_store` | `[postgres]` | Production (Tier 3) |

## Installation Options

```bash
# Core only (zero deps) - includes Tier 0-1 stores
pip install entityspine

# With Pydantic validation/serialization wrappers
pip install entityspine[pydantic]

# With DuckDB for analytics (Tier 2)
pip install entityspine[duckdb]

# With ORM layer (SQLModel/SQLAlchemy for advanced use cases)
pip install entityspine[orm]

# With PostgreSQL for production (Tier 3)
pip install entityspine[postgres]

# Development (includes pydantic, orm, testing tools)
pip install entityspine[dev]
```

## Tier Capabilities Summary

| Capability | Tier 0 (JSON) | Tier 1 (SQLite) | Tier 2 (DuckDB) | Tier 3 (Postgres) |
|------------|---------------|-----------------|-----------------|-------------------|
| Dependencies | stdlib | stdlib sqlite3 | duckdb | asyncpg/psycopg |
| `as_of` honored | ❌ | ❌ | ✅ | ✅ |
| Full-text search | ❌ | LIKE only | ✅ | ✅ |
| Max entities | ~50K | ~500K | ~10M | Unlimited |
| Temporal history | ❌ | ❌ | ✅ | ✅ |

When a lower-tier store cannot honor a capability (like `as_of`), it:
1. Returns the current/best-effort result
2. Sets `ResolutionResult.as_of_honored = False`
3. Adds a warning: `"as_of_ignored: Tier N store lacks temporal data"`

