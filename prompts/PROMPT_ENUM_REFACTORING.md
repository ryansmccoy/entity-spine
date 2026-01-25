# Prompt: Enum Refactoring (P1)

> **Feature**: Split `enums.py` into logical domain-specific files  
> **Priority**: 🔴 P0 (High Impact, Low Effort)  
> **Estimated Effort**: 1-2 hours

---

## Context

EntitySpine's `entityspine/domain/enums.py` has grown to 857 lines with 42 enum classes. This makes it difficult to navigate and maintain. We need to split it into logical domain-specific files while maintaining backward compatibility.

## Current State

```
entityspine/domain/enums.py (857 lines, 42 enums)
```

Current enums:
- **Core**: EntityType, EntityStatus, SecurityType, SecurityStatus, ListingStatus
- **Identifiers**: IdentifierScheme, IdentifierScope, ClaimStatus, SanctionStatus
- **Resolution**: ResolutionTier, ResolutionStatus, ResolutionWarning, MatchReason
- **Graph**: NodeKind, RelationshipType, RoleType, ParticipantType, PositionType, ClusterRole
- **Events**: EventType, EventStatus, CaseType, CaseStatus
- **Assets**: AssetType, AssetStatus, ContractType, ContractStatus, ProductType, ProductStatus
- **Observations**: MetricCode, MetricCategory, AccountingBasis, Presentation, PerShareType, ScopeType, PeriodType, ObservationType, EstimateScope
- **Vendors**: VendorNamespace, ProvenanceKind
- **Geography**: GeoType, AddressType
- **Transactions**: TransactionCode

## Target State

```
entityspine/domain/enums/
├── __init__.py          # Re-exports ALL enums for backward compatibility
├── core.py              # EntityType, EntityStatus, SecurityType, SecurityStatus, ListingStatus
├── identifiers.py       # IdentifierScheme, IdentifierScope, ClaimStatus, SanctionStatus
├── resolution.py        # ResolutionTier, ResolutionStatus, ResolutionWarning, MatchReason
├── graph.py             # NodeKind, RelationshipType, RoleType, ParticipantType, PositionType, ClusterRole
├── events.py            # EventType, EventStatus, CaseType, CaseStatus
├── assets.py            # AssetType, AssetStatus, ContractType, ContractStatus, ProductType, ProductStatus
├── observations.py      # MetricCode, MetricCategory, AccountingBasis, Presentation, PerShareType, ScopeType, PeriodType, ObservationType, EstimateScope
├── vendors.py           # VendorNamespace, ProvenanceKind
├── geo.py               # GeoType, AddressType
└── transactions.py      # TransactionCode
```

## Requirements

1. **Backward Compatibility**: All existing imports must continue to work:
   ```python
   # These must still work after refactoring:
   from entityspine.domain.enums import EntityType
   from entityspine.domain import EntityType
   ```

2. **Follow EntitySpine Conventions**:
   - Each file must have `"""STDLIB ONLY - NO PYDANTIC."""` header
   - All enums inherit from `(str, Enum)` for JSON serialization
   - Values are lowercase strings
   - Each enum has a docstring with examples

3. **No Circular Imports**: Carefully order imports to avoid cycles

4. **Tests Must Pass**: Run `pytest tests/unit/` - all 298 tests must pass

## Task

1. Create the `enums/` directory structure
2. Move each enum class to its appropriate file
3. Create `enums/__init__.py` that re-exports everything
4. Update `domain/__init__.py` to import from `enums/` package
5. Delete the old `enums.py` file
6. Run tests to verify nothing broke

## Conventions Reference

See `entityspine/docs/ENTITYSPINE_CONVENTIONS.md` for:
- File header format
- Enum docstring format
- Import organization

## Verification

```bash
cd entityspine
python -m pytest tests/unit/ -v --tb=short
# Expected: 298 passed
```

Also verify imports work:
```python
from entityspine.domain.enums import EntityType, SecurityType, MetricCode
from entityspine.domain import EntityType  # Must still work
print("All imports successful")
```
