# ADR-007: Enum Package Split

**Status**: Accepted  
**Date**: 2026-01-28  
**Deciders**: Project maintainers

## Context

The `enums.py` file grew to 1099 lines with 42 enum classes covering:
- Core types (Entity, Security, Listing)
- Identifiers and claims
- Resolution logic
- Knowledge graph relationships
- Events and cases
- Financial observations
- Assets, contracts, products

This violated the single-responsibility principle and made navigation difficult.

## Decision

**Split `enums.py` into an `enums/` package with 10 focused modules.**

```
entityspine/domain/enums/
├── __init__.py      # Re-exports all (backward compatibility)
├── core.py          # EntityType, SecurityType, ListingStatus
├── identifiers.py   # IdentifierScheme, ClaimStatus, SanctionStatus
├── resolution.py    # ResolutionTier, ResolutionStatus, MatchReason
├── graph.py         # RoleType, RelationshipType, ClusterRole
├── events.py        # EventType, EventStatus, CaseType, CaseStatus
├── assets.py        # AssetType, ContractType, ProductType
├── observations.py  # MetricCode, MetricCategory, Presentation
├── vendors.py       # VendorNamespace
├── geo.py           # GeoType, AddressType
└── transactions.py  # TransactionCode (SEC Form 4)
```

## Consequences

### Positive
- **Single responsibility**: Each file ~50-150 lines
- **Easier navigation**: Find enums by domain concept
- **Better imports**: `from entityspine.domain.enums.events import EventType`
- **Reduced merge conflicts**: Changes isolated to specific files

### Negative
- More files to manage
- Import paths longer (mitigated by `__init__.py` re-exports)
- Migration effort for existing code (none - backward compatible)

### Backward Compatibility

The `__init__.py` re-exports everything:
```python
# Still works (backward compatible)
from entityspine.domain.enums import EntityType, EventType

# Also works (explicit module)
from entityspine.domain.enums.events import EventType
```

### Grouping Rationale

| Module | Enums | Rationale |
|--------|-------|-----------|
| `core.py` | EntityType, SecurityType, etc. | Fundamental entity model |
| `identifiers.py` | IdentifierScheme, ClaimStatus | Identifier claim system |
| `resolution.py` | ResolutionTier, MatchReason | Entity resolution |
| `graph.py` | RoleType, RelationshipType | Knowledge graph edges |
| `events.py` | EventType, CaseType | Discrete events |
| `assets.py` | AssetType, ContractType | KG node types |
| `observations.py` | MetricCode, Presentation | Financial observations |
| `vendors.py` | VendorNamespace | Data sources |
| `geo.py` | GeoType, AddressType | Geographic |
| `transactions.py` | TransactionCode | SEC Form 4 |
