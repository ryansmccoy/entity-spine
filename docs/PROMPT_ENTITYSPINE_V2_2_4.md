# EntitySpine - Implementation Reference (v2.2.4)

**For: Claude Opus 4.5 (Extended Thinking Mode)**  
**Version**: 2.2.4  
**Date**: January 2026

---

## 🚀 DO THIS FIRST (Before Any Changes)

### Step 1: Understand EntitySpine Architecture (20 min)

```
EXPLORE IN THIS ORDER:
1. entityspine/src/entityspine/__init__.py           → Package exports + create_store()
2. entityspine/src/entityspine/domain/              → Canonical stdlib dataclasses (THE ONE TRUE SOURCE)
3. entityspine/src/entityspine/stores/              → SqliteStore (Tier 1, stdlib sqlite3)
4. entityspine/src/entityspine/adapters/pydantic/   → OPTIONAL Pydantic wrappers (requires [pydantic])
5. entityspine/src/entityspine/adapters/orm/        → OPTIONAL SQLModel layer (requires [orm])
```

### Step 2: Read Design Documents (15 min)

```
REQUIRED READING ORDER:
1. entityspine/GUARDRAILS.md                              → Non-negotiable standards
2. entityspine/docs/UNIFIED_DATA_MODEL.md                 → Master schema contract (v2.2.4)
3. entityspine/docs/design/current/06_PROTOCOLS_AND_INTERFACES.md → AUTHORITATIVE protocols
4. entityspine/docs/design/current/05_TIER_CAPABILITIES_AND_LIMITS.md → as_of honesty
```

### Step 3: Run Existing Tests

```bash
cd entityspine
uv run pytest tests/ -v --tb=short
```

**All 224 tests should pass. Understand what works before changing anything.**

---

## ⚠️ STATUS: v2.2.4 Implementation COMPLETE

EntitySpine v2.2.4 has been fully implemented with:

### Core Architecture (INVIOLABLE)

| Rule | Implementation |
|------|----------------|
| ONE canonical definition per model | `entityspine.domain.*` (stdlib dataclasses) |
| Zero-dependency core | `pip install entityspine` requires nothing |
| Optional adapters | `[pydantic]` and `[orm]` extras |
| Stores return domain | All store methods return domain dataclasses |

### Components

- ✅ **Domain models** (stdlib dataclasses): Entity, Security, Listing, IdentifierClaim
- ✅ **Knowledge Graph models**: Asset, Contract, Product, Brand, Event
- ✅ **Enums**: NodeKind, RelationshipType, AssetType, ContractType, ProductType, EventType
- ✅ **SqliteStore** (Tier 1): stdlib sqlite3, no ORM dependency
- ✅ **Pydantic adapters** (optional): wrappers with `to_domain()`/`from_domain()`
- ✅ **ORM adapters** (optional): SQLModel tables + repositories
- ✅ **224 tests passing**

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ENTITYSPINE v2.2.4 ARCHITECTURE                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  TIER 0: Zero Dependencies                                                  │
│  ═════════════════════════                                                  │
│      pip install entityspine                                                │
│      │                                                                      │
│      ├── entityspine.domain.*        ← Canonical stdlib dataclasses         │
│      │   ├── Entity, Security, Listing, IdentifierClaim                    │
│      │   ├── Asset, Contract, Product, Brand, Event  (KG nodes)            │
│      │   ├── NodeKind, RelationshipType (enums)                            │
│      │   └── Validators (normalize_cik, validate_isin, etc.)               │
│      │                                                                      │
│      └── entityspine.stores.SqliteStore  ← stdlib sqlite3                   │
│                                                                             │
│  TIER 1: Optional Pydantic                                                  │
│  ═════════════════════════                                                  │
│      pip install entityspine[pydantic]                                      │
│      │                                                                      │
│      └── entityspine.adapters.pydantic.*  ← Pydantic wrappers              │
│          └── to_domain() / from_domain() converters                         │
│                                                                             │
│  TIER 2: Optional ORM (SQLModel)                                            │
│  ═══════════════════════════════                                            │
│      pip install entityspine[orm]                                           │
│      │                                                                      │
│      └── entityspine.adapters.orm.*  ← SQLModel tables + repos             │
│          └── SqlModelStore with repository pattern                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📦 Domain Models

### Core Models (entityspine.domain)

```python
from entityspine.domain import (
    # Core models
    Entity, Security, Listing, IdentifierClaim,
    ResolutionCandidate, ResolutionResult,
    
    # Knowledge Graph models (v2.2.4)
    Asset, Contract, Product, Brand, Event,
    NodeRef, Relationship, RoleAssignment,
    Address, Geo, Case,
    
    # Enums
    EntityType, SecurityType, ListingStatus,
    NodeKind, RelationshipType,
    AssetType, AssetStatus,
    ContractType, ContractStatus,
    ProductType, ProductStatus,
    EventType, EventStatus,
    
    # Validators
    normalize_cik, validate_isin, normalize_ticker,
)
```

### Entity (NO identifier storage)

```python
@dataclass
class Entity:
    entity_id: str = field(default_factory=ulid_now)
    primary_name: str = ""
    entity_type: EntityType = EntityType.UNKNOWN
    status: EntityStatus = EntityStatus.ACTIVE
    aliases: list[str] = field(default_factory=list)
    # NO cik, lei, ein fields - use IdentifierClaim
```

### Security (linked to Entity)

```python
@dataclass
class Security:
    security_id: str = field(default_factory=ulid_now)
    issuer_entity_id: Optional[str] = None
    security_type: SecurityType = SecurityType.UNKNOWN
    security_name: Optional[str] = None
    # NO isin, cusip fields - use IdentifierClaim
```

### Listing (ticker lives HERE)

```python
@dataclass
class Listing:
    listing_id: str = field(default_factory=ulid_now)
    security_id: str = ""
    ticker: str = ""  # TICKER IS HERE
    mic: str = ""     # Exchange MIC code
    status: ListingStatus = ListingStatus.ACTIVE
```

### Knowledge Graph Models (v2.2.4)

```python
@dataclass
class Asset:
    asset_id: str = field(default_factory=ulid_now)
    asset_type: AssetType = AssetType.OTHER
    name: str = ""
    owner_entity_id: Optional[str] = None
    status: AssetStatus = AssetStatus.ACTIVE

@dataclass
class Contract:
    contract_id: str = field(default_factory=ulid_now)
    contract_type: ContractType = ContractType.OTHER
    title: str = ""
    effective_date: Optional[date] = None
    termination_date: Optional[date] = None
    value_usd: Optional[Decimal] = None
    status: ContractStatus = ContractStatus.ACTIVE

@dataclass
class Product:
    product_id: str = field(default_factory=ulid_now)
    product_type: ProductType = ProductType.OTHER
    name: str = ""
    owner_entity_id: Optional[str] = None
    status: ProductStatus = ProductStatus.ACTIVE

@dataclass
class Brand:
    brand_id: str = field(default_factory=ulid_now)
    name: str = ""
    owner_entity_id: Optional[str] = None

@dataclass
class Event:
    event_id: str = field(default_factory=ulid_now)
    event_type: EventType = EventType.OTHER
    title: str = ""
    occurred_on: Optional[date] = None
    announced_on: Optional[date] = None
    status: EventStatus = EventStatus.ANNOUNCED
    payload: Optional[dict] = None
    evidence_filing_id: Optional[str] = None
    confidence: float = 1.0
```

---

## 🗄️ Storage Tiers

### Tier 1: SqliteStore (stdlib, zero deps)

```python
from entityspine.stores import SqliteStore

store = SqliteStore("entities.db")
store.initialize()

# CRUD operations
entity = Entity(primary_name="Apple Inc", entity_type=EntityType.ORGANIZATION)
store.save_entity(entity)

retrieved = store.get_entity(entity.entity_id)  # Returns domain.Entity
assert type(retrieved).__module__ == "entityspine.domain.entity"
```

### Tier 2: SqlModelStore (optional, requires [orm])

```python
from entityspine.adapters.orm import SqlModelStore

store = SqlModelStore("sqlite:///entities.db")
with store:
    store.initialize()
    # Same API, but uses SQLModel under the hood
```

---

## 🔌 Guardrails (INVIOLABLE)

### 1. ONE Definition Per Model

```python
# ✅ CORRECT: Use domain dataclasses
from entityspine.domain import Entity

# ❌ WRONG: Don't import from adapters for core logic
from entityspine.adapters.pydantic import Entity  # Only for API serialization
```

### 2. Stores Return Domain

```python
# ✅ CORRECT: Store methods return domain dataclasses
entity = store.get_entity("...")
assert dataclasses.is_dataclass(entity)
assert entity.__class__.__module__.startswith("entityspine.domain")

# ❌ WRONG: Never return ORM/Pydantic models from stores
```

### 3. Zero-Dep Core Imports

```python
# ✅ CORRECT: Core imports don't require pydantic/sqlalchemy
import entityspine
from entityspine.domain import Entity, Asset, Contract

# These should NOT trigger pydantic/sqlalchemy imports
import sys
assert "pydantic" not in sys.modules
assert "sqlalchemy" not in sys.modules
```

---

## 🧪 Test Summary

```bash
$ uv run pytest tests/ -v --tb=short
# Expected: 224 passed, 1 skipped

# Key test files:
tests/unit/domain/test_graph_models.py    # KG model tests
tests/unit/test_no_optional_imports.py    # Zero-dep guardrails
tests/unit/test_zero_dependencies.py      # Core import tests
tests/unit/stores/test_sqlite_store.py    # Tier 1 store tests
```

---

## 📋 What's Complete

| Component | Status | Notes |
|-----------|--------|-------|
| Domain models | ✅ | stdlib dataclasses |
| KG models (v2.2.4) | ✅ | Asset, Contract, Product, Brand, Event |
| NodeKind enum | ✅ | ENTITY, SECURITY, ASSET, CONTRACT, PRODUCT, BRAND, REGULATOR, EVENT |
| RelationshipType | ✅ | ~50 relationship types |
| SqliteStore (Tier 1) | ✅ | stdlib sqlite3 |
| Pydantic adapters | ✅ | Optional wrappers |
| ORM adapters | ✅ | Optional SQLModel |
| Guardrail tests | ✅ | Zero-dep enforcement |
| Documentation | ✅ | UNIFIED_DATA_MODEL.md updated |

---

## 📋 What's Next (Optional)

| Component | Priority | Notes |
|-----------|----------|-------|
| DuckDB store (Tier 2) | Low | Analytics queries |
| PostgreSQL store (Tier 3) | Low | Full temporal, production |
| Fuzzy name matching | Medium | Levenshtein, phonetic |
| External integrations | Medium | GLEIF, OpenFIGI |

---

## 📁 File Structure

```
src/entityspine/
├── __init__.py                  # Package exports
├── domain/                      # CANONICAL domain models (stdlib)
│   ├── __init__.py              # All exports
│   ├── entity.py                # Entity dataclass
│   ├── security.py              # Security dataclass
│   ├── listing.py               # Listing dataclass
│   ├── claim.py                 # IdentifierClaim dataclass
│   ├── graph.py                 # KG models (NodeKind, Asset, Contract, etc.)
│   ├── enums.py                 # All enumerations
│   └── validators.py            # normalize_*, validate_*
├── stores/                      # Tier 1 storage (stdlib)
│   ├── __init__.py
│   ├── protocol.py              # EntityStoreProtocol
│   └── sqlite_store.py          # SqliteStore (sqlite3)
└── adapters/                    # Optional adapters
    ├── pydantic/                # [pydantic] extra
    │   ├── __init__.py
    │   ├── entity.py            # Pydantic Entity wrapper
    │   └── ...
    └── orm/                     # [orm] extra
        ├── __init__.py
        ├── tables.py            # SQLModel tables
        ├── sqlmodel_store.py    # SqlModelStore
        └── repositories/        # Repository pattern
```

---

*EntitySpine v2.2.4 | January 2026 | 224 tests passing*
