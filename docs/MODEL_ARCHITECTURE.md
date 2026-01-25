# EntitySpine Model Architecture (v2.2.4)

## Single Source of Truth: Domain Dataclasses

**ALL business logic and model definitions live in `entityspine.domain.*`**

These are stdlib `@dataclass` classes with zero external dependencies:

```python
from entityspine.domain import Entity, Security, Listing, IdentifierClaim
from entityspine.domain import Asset, Contract, Product, Brand, Event  # KG nodes
```

## Layer Architecture

### 1. Domain Layer (`entityspine.domain.*`) - CANONICAL
- **Pure stdlib** - no Pydantic, SQLAlchemy, or SQLModel
- All models are `@dataclass(frozen=True, slots=True)`
- Contains all validation logic
- Zero-dependency guarantee: `pip install entityspine` works without extras

### 2. Stores Layer (`entityspine.stores.*`)
- **SqliteStore** - Tier 0/1 store using stdlib `sqlite3` only
- Uses `stores/mappers.py` for domain↔dict conversion
- MUST return domain dataclasses from all methods
- NO Pydantic or ORM dependencies

### 3. Adapters Layer (`entityspine.adapters.*`) - OPTIONAL

#### Pydantic Adapter (`entityspine.adapters.pydantic.*`)
- **Requires**: `pip install entityspine[pydantic]`
- Provides Pydantic models for API serialization/validation
- Each model has `to_domain()` and `from_domain()` methods
- Use for FastAPI endpoints, JSON schemas, etc.

#### ORM Adapter (`entityspine.adapters.orm.*`)
- **Requires**: `pip install entityspine[orm]`
- Provides SQLModel tables and SqlModelStore
- Uses Pydantic adapters internally (dependency cascade)
- Repository pattern with `to_domain()` conversion

## Dependency Graph

```
entityspine (core)     → stdlib only
entityspine.domain     → stdlib only (dataclasses)
entityspine.stores     → stdlib only (sqlite3)
entityspine[pydantic]  → pydantic
entityspine[orm]       → sqlmodel → sqlalchemy → pydantic
```

## Design Rules

1. **Domain is canonical** - All other layers convert to/from domain dataclasses
2. **No competing definitions** - Domain tests import from `entityspine.domain`, not adapters
3. **Tier capability honesty** - Stores must warn when they can't honor `as_of`, `mic`, etc.
4. **Zero dependencies for core** - Tests enforce this via `test_no_optional_imports.py`

## Test Organization

| Test Location | Tests What |
|---------------|------------|
| `tests/unit/domain/models/` | Domain dataclasses (import from `entityspine.domain`) |
| `tests/unit/stores/` | Store implementations |
| `tests/unit/test_pydantic_conversions.py` | Pydantic adapter `to_domain()/from_domain()` |
| `tests/unit/test_no_optional_imports.py` | Zero-dependency guarantee |
| `tests/unit/test_zero_dependencies.py` | Domain model creation without extras |

## Migration Notes (v2.2.4)

Prior to v2.2.4, some tests incorrectly imported from `adapters.pydantic` when testing domain behavior. This has been corrected:

- ✅ `test_entity.py` - Now imports from `entityspine.domain`
- ✅ `test_listing.py` - Now imports from `entityspine.domain`
- ✅ `test_resolution.py` - Now imports from `entityspine.domain`

The ORM adapter (`adapters.orm`) still uses Pydantic models internally for convenience, but this is an implementation detail hidden behind the repository pattern's `to_domain()` conversion.

### Mapper Fixes (v0.3.1)

Critical field drift in `stores/mappers.py` was fixed:
- Entity, Security, Listing, IdentifierClaim core mappers now align with domain models
- Added Case, EntityCluster, EntityClusterMember mappers
- Comprehensive regression tests prevent future drift (39 mapper tests)

The SqliteStore was unaffected because it uses direct field access, not mappers. Other stores (DuckDB, Postgres) that implement the protocol MUST use the corrected mappers.
