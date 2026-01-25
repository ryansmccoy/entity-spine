# Prompt: Type Aliases Module (P5)

> **Feature**: Create type aliases for semantic clarity  
> **Priority**: 🟢 P2 (Low Impact, Low Effort)  
> **Estimated Effort**: 30 minutes

---

## Context

EntitySpine uses `str` for all ID fields (entity_id, security_id, claim_id, etc.). While this works, it provides no semantic information to developers or type checkers. Type aliases can improve code readability and enable future type safety improvements.

## Current State

IDs are plain `str` throughout the codebase:

```python
# In entity.py
@dataclass(frozen=True, slots=True)
class Entity:
    entity_id: str  # What kind of ID? Not obvious.
    primary_name: str
    # ...

# In observation.py
@dataclass(frozen=True, slots=True)
class Observation:
    entity_id: str  # FK to Entity, but just shows as str
    security_id: str | None = None  # FK to Security
    observation_id: str = field(default_factory=generate_ulid)
```

## Target State

Create `entityspine/domain/types.py`:

```python
"""
Common type aliases for EntitySpine domain.

STDLIB ONLY - NO PYDANTIC.

These aliases provide semantic meaning to ID and collection types,
making code more self-documenting and enabling future type safety.

Usage:
    from entityspine.domain.types import EntityId, SecurityId

    def find_securities(entity_id: EntityId) -> list[Security]:
        ...
"""

from typing import TypeAlias

# =============================================================================
# ID Types
# =============================================================================

# Core entity IDs
EntityId: TypeAlias = str
SecurityId: TypeAlias = str
ListingId: TypeAlias = str

# Identifier claim IDs
ClaimId: TypeAlias = str

# Graph node IDs
NodeId: TypeAlias = str
RelationshipId: TypeAlias = str

# Observation IDs
ObservationId: TypeAlias = str
ProvenanceId: TypeAlias = str

# Address IDs
AddressId: TypeAlias = str

# ULID type (all IDs are ULIDs)
ULID: TypeAlias = str

# =============================================================================
# Optional ID Types
# =============================================================================

OptionalEntityId: TypeAlias = str | None
OptionalSecurityId: TypeAlias = str | None
OptionalListingId: TypeAlias = str | None

# =============================================================================
# Collection Types
# =============================================================================

EntityIds: TypeAlias = list[str]
SecurityIds: TypeAlias = list[str]
ClaimIds: TypeAlias = list[str]

# =============================================================================
# Hash Types
# =============================================================================

# Deterministic hashes for deduplication
ObservationKey: TypeAlias = str  # SHA256 hash
AddressHash: TypeAlias = str  # Address fingerprint

# =============================================================================
# External Identifier Types
# =============================================================================

CIK: TypeAlias = str  # 10-digit SEC CIK
LEI: TypeAlias = str  # 20-char Legal Entity Identifier
CUSIP: TypeAlias = str  # 9-char CUSIP
ISIN: TypeAlias = str  # 12-char ISIN
SEDOL: TypeAlias = str  # 7-char SEDOL
FIGI: TypeAlias = str  # 12-char OpenFIGI
Ticker: TypeAlias = str  # Exchange ticker symbol
MIC: TypeAlias = str  # 4-char Market Identifier Code
```

## Usage Examples

### Before (current)

```python
@dataclass(frozen=True, slots=True)
class Observation:
    entity_id: str
    security_id: str | None = None
    observation_id: str = field(default_factory=generate_ulid)
```

### After (with type aliases)

```python
from entityspine.domain.types import EntityId, OptionalSecurityId, ObservationId

@dataclass(frozen=True, slots=True)
class Observation:
    entity_id: EntityId  # Clearly an entity reference
    security_id: OptionalSecurityId = None  # Clearly optional security
    observation_id: ObservationId = field(default_factory=generate_ulid)
```

### Function Signatures

```python
from entityspine.domain.types import EntityId, SecurityIds

def find_securities_for_entity(entity_id: EntityId) -> SecurityIds:
    """Find all security IDs for an entity."""
    ...
```

## Requirements

1. **Optional Adoption**: Type aliases should be available but not required
2. **Backward Compatible**: Plain `str` must still work everywhere
3. **No Runtime Impact**: TypeAlias is purely for static analysis
4. **Follow Conventions**: Standard file header, docstrings

## Task

1. Create `entityspine/domain/types.py` with type aliases
2. Add exports to `__init__.py`
3. (Optional) Update a few key models to use aliases as examples
4. Run tests to ensure no breakage

## Considerations

### Pros
- ✅ Self-documenting code
- ✅ IDE shows semantic meaning in tooltips
- ✅ Foundation for future `NewType` enforcement
- ✅ Easier refactoring if ID type changes

### Cons
- ❌ Extra import needed
- ❌ Marginal benefit for simple strings
- ❌ May confuse developers unfamiliar with TypeAlias

### Future Enhancement

Could upgrade to `NewType` for stricter type checking:

```python
from typing import NewType

# NewType creates distinct types that can't be mixed
EntityId = NewType("EntityId", str)
SecurityId = NewType("SecurityId", str)

# This would catch bugs at type-check time:
def get_entity(entity_id: EntityId) -> Entity: ...

security_id: SecurityId = "01H..."
get_entity(security_id)  # Type error! Can't pass SecurityId as EntityId
```

## Verification

```bash
cd entityspine
python -m pytest tests/unit/ -v --tb=short
# Expected: All tests pass

# Verify imports work
python -c "
from entityspine.domain.types import EntityId, SecurityId, ObservationId, ULID
print(f'EntityId is {EntityId}')
print('Type alias imports successful')
"
```
