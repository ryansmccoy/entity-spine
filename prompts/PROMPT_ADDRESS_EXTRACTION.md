# Prompt: Address Model Extraction (P4)

> **Feature**: Extract address models from `graph.py` into dedicated `address.py`  
> **Priority**: 🟢 P2 (Low Impact, Low Effort)  
> **Estimated Effort**: 30-45 minutes

---

## Context

Address models (`Address`, `EntityAddress`) are currently in `graph.py` but represent a distinct domain concept that's used broadly beyond just the knowledge graph. Extracting them improves cohesion and reduces `graph.py` size.

## Current State

In `entityspine/domain/graph.py`:

```python
@dataclass(frozen=True, slots=True)
class Address:
    """Physical or mailing address."""
    
    address_id: str = field(default_factory=generate_ulid)
    line1: str = ""
    line2: str | None = None
    city: str = ""
    state_province: str | None = None
    postal_code: str | None = None
    country: str = "US"
    address_hash: str | None = None
    # ... more fields and methods


@dataclass(frozen=True, slots=True)
class EntityAddress:
    """Links an entity to an address with type and validity period."""
    
    entity_address_id: str = field(default_factory=generate_ulid)
    entity_id: str = ""
    address: Address | None = None
    address_type: AddressType = AddressType.BUSINESS
    is_primary: bool = False
    valid_from: date | None = None
    valid_to: date | None = None
    # ... more fields
```

## Target State

```
entityspine/domain/
├── address.py           # NEW - Address, EntityAddress
├── graph.py             # Reduced - imports from address.py
└── __init__.py          # Updated exports
```

### New `address.py`:

```python
"""
Address domain models.

STDLIB ONLY - NO PYDANTIC.
"""

from dataclasses import dataclass, field
from datetime import date

from entityspine.domain.enums import AddressType
from entityspine.domain.timestamps import generate_ulid
from entityspine.domain.validators import compute_address_hash, normalize_address_line


@dataclass(frozen=True, slots=True)
class Address:
    """
    Physical or mailing address.
    
    STDLIB ONLY - NO PYDANTIC.
    
    Attributes:
        address_id: ULID primary key
        line1: Street address line 1
        line2: Street address line 2 (apt, suite, etc.)
        city: City name
        state_province: State/province code
        postal_code: Postal/ZIP code
        country: ISO 3166-1 alpha-2 country code
        address_hash: Computed hash for deduplication
    """
    # ... move implementation from graph.py


@dataclass(frozen=True, slots=True)
class EntityAddress:
    """
    Links an entity to an address with type and validity period.
    
    Attributes:
        entity_address_id: ULID primary key
        entity_id: FK to Entity
        address: The address
        address_type: Type (business, mailing, registered, etc.)
        is_primary: Whether this is the primary address of this type
        valid_from: Start of validity period
        valid_to: End of validity period
    """
    # ... move implementation from graph.py
```

## Requirements

1. **Backward Compatibility**: All existing imports must continue to work:
   ```python
   from entityspine.domain.graph import Address, EntityAddress  # Must work
   from entityspine.domain import Address, EntityAddress  # Must work
   ```

2. **Update graph.py**: Import and re-export from `address.py`:
   ```python
   # In graph.py
   from entityspine.domain.address import Address, EntityAddress
   ```

3. **Follow Conventions**: See `ENTITYSPINE_CONVENTIONS.md`

4. **Tests Must Pass**: All existing tests must continue to pass

## Task

1. Create `entityspine/domain/address.py`
2. Move `Address` and `EntityAddress` classes from `graph.py`
3. In `graph.py`, add import: `from entityspine.domain.address import Address, EntityAddress`
4. Update `__init__.py` to import from `address.py`
5. Run tests

## Files to Modify

| File | Changes |
|------|---------|
| `address.py` | CREATE - Move Address, EntityAddress here |
| `graph.py` | MODIFY - Remove classes, add import |
| `__init__.py` | MODIFY - Update imports |

## Verification

```bash
cd entityspine
python -m pytest tests/unit/ -v --tb=short
# Expected: All tests pass

# Verify imports work
python -c "
from entityspine.domain.address import Address, EntityAddress
from entityspine.domain.graph import Address, EntityAddress  # Backward compat
from entityspine.domain import Address, EntityAddress
print('All address imports successful')
"
```
