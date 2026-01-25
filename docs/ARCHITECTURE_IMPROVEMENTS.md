# EntitySpine Architecture Improvement Proposals

> **Version**: 2.2.5  
> **Last Updated**: January 2026  
> **Status**: RFC (Request for Comments)

This document analyzes the current EntitySpine architecture and proposes improvements for maintainability, scalability, and developer experience.

---

## Table of Contents

1. [Current State Analysis](#current-state-analysis)
2. [Proposed Improvements](#proposed-improvements)
   - [P1: Split enums.py](#p1-split-enumspy)
   - [P2: Split graph.py](#p2-split-graphpy)
   - [P3: Consolidate Observation Models](#p3-consolidate-observation-models)
   - [P4: Extract Address Models](#p4-extract-address-models)
   - [P5: Create Type Aliases Module](#p5-create-type-aliases-module)
3. [Migration Strategy](#migration-strategy)
4. [Decision Matrix](#decision-matrix)

---

## Current State Analysis

### File Size Distribution

| File | Lines | Classes | Status |
|------|-------|---------|--------|
| `graph.py` | 1,502 | 25 | 🔴 Too large |
| `enums.py` | 857 | 42 | 🔴 Too large |
| `observation.py` | 786 | 8 | 🟡 At limit |
| `financial_observation.py` | 606 | 8 | 🟡 Duplicate? |
| `validators.py` | 404 | 0 | 🟢 OK |
| `__init__.py` | 348 | 0 | 🟡 Large exports |
| `factories.py` | 311 | 0 | 🟢 OK |
| `protocols.py` | 292 | 8 | 🟢 OK |
| `claim.py` | 228 | 1 | 🟢 OK |
| `entity.py` | 201 | 1 | 🟢 OK |
| Other files | <200 | - | 🟢 OK |

### Pain Points Identified

1. **`enums.py` has 42 enum classes** - Hard to navigate, unclear groupings
2. **`graph.py` has 25 classes** - Mixed concerns (nodes, relationships, traversal results)
3. **Two observation files** - `observation.py` (v2.2.5) and `financial_observation.py` (legacy)
4. **`__init__.py` is 348 lines** - Maintenance burden when adding exports
5. **Address models scattered** - `Address`, `EntityAddress` in `graph.py` but used broadly

---

## Proposed Improvements

### P1: Split `enums.py`

**Problem**: 42 enums in one 857-line file is unwieldy.

**Proposal**: Split into logical domain-specific enum files.

```
entityspine/domain/enums/
├── __init__.py          # Re-exports all enums
├── core.py              # EntityType, EntityStatus, SecurityType, etc.
├── identifiers.py       # IdentifierScheme, IdentifierScope, ClaimStatus
├── resolution.py        # ResolutionTier, ResolutionStatus, MatchReason
├── graph.py             # NodeKind, RelationshipType, RoleType
├── events.py            # EventType, EventStatus
├── observations.py      # MetricCode, ObservationType, PeriodType, etc.
└── vendors.py           # VendorNamespace, ProvenanceKind
```

**Grouping Logic**:

| File | Enums | Purpose |
|------|-------|---------|
| `core.py` | EntityType, EntityStatus, SecurityType, SecurityStatus, ListingStatus | Core domain entities |
| `identifiers.py` | IdentifierScheme, IdentifierScope, ClaimStatus, SanctionStatus | Identifier management |
| `resolution.py` | ResolutionTier, ResolutionStatus, ResolutionWarning, MatchReason | Resolution engine |
| `graph.py` | NodeKind, RelationshipType, RoleType, ParticipantType, PositionType, ClusterRole | Knowledge graph |
| `events.py` | EventType, EventStatus, CaseType, CaseStatus | Events and legal |
| `assets.py` | AssetType, AssetStatus, ContractType, ContractStatus, ProductType, ProductStatus | Assets and contracts |
| `observations.py` | MetricCode, MetricCategory, AccountingBasis, Presentation, PerShareType, ScopeType, PeriodType, ObservationType, EstimateScope | Financial observations |
| `vendors.py` | VendorNamespace, ProvenanceKind | Data sources |
| `geo.py` | GeoType, AddressType | Geography |
| `transactions.py` | TransactionCode | SEC transactions |

**Benefits**:
- ✅ Each file ~50-100 lines (manageable)
- ✅ Clear domain boundaries
- ✅ Easier to find relevant enums
- ✅ Can add new enums to appropriate file

**Drawbacks**:
- ❌ More files to manage
- ❌ Must update imports in `__init__.py`
- ❌ Potential circular import risks

**Recommendation**: ✅ **DO THIS** - The benefits outweigh the costs.

---

### P2: Split `graph.py`

**Problem**: 1,502 lines with 25 classes mixing different concerns.

**Current Structure**:
```python
# graph.py contains:
# 1. Reference types (NodeKind, NodeRef)
# 2. Person/role models (PersonRole, FilingParticipant, RoleAssignment)
# 3. Ownership models (OwnershipPosition, InsiderTransaction)
# 4. Address models (Address, EntityAddress)
# 5. Relationship models (EntityRelationship, Relationship)
# 6. Cluster models (EntityCluster, EntityClusterMember)
# 7. Entity types (Geo, Case, Asset, Contract, Product, Brand, Event)
# 8. Traversal results (RelatedEntity, OfficerInfo, PathStep, EntityPath, EntityNetwork)
```

**Proposal**: Split into focused modules.

```
entityspine/domain/graph/
├── __init__.py          # Re-exports all
├── refs.py              # NodeKind, NodeRef (50 lines)
├── roles.py             # PersonRole, FilingParticipant, RoleAssignment (200 lines)
├── ownership.py         # OwnershipPosition, InsiderTransaction (200 lines)
├── addresses.py         # Address, EntityAddress (150 lines)
├── relationships.py     # EntityRelationship, Relationship (200 lines)
├── clusters.py          # EntityCluster, EntityClusterMember (100 lines)
├── nodes.py             # Geo, Case, Asset, Contract, Product, Brand, Event (400 lines)
└── traversal.py         # RelatedEntity, OfficerInfo, PathStep, etc. (200 lines)
```

**Benefits**:
- ✅ Each file has single responsibility
- ✅ Easier to understand each component
- ✅ Can import only what's needed
- ✅ Better for documentation generation

**Drawbacks**:
- ❌ Many files
- ❌ Cross-references between files
- ❌ Larger `__init__.py` for re-exports

**Recommendation**: ✅ **DO THIS** - 1500 lines is too much for one file.

---

### P3: Consolidate Observation Models

**Problem**: Two observation files exist:
- `observation.py` (786 lines) - New v2.2.5 architecture
- `financial_observation.py` (606 lines) - Legacy v2.2.4 architecture

**Current State**:
```python
# observation.py (NEW - v2.2.5)
- MetricSpec, FiscalPeriod, ProvenanceRef, SourceKey
- EstimateInfo, ValueWithUnits, Observation, ObservationSet

# financial_observation.py (OLD - v2.2.4)
- MetricCode, MetricVariant, ObservationType (now in enums.py)
- FiscalPeriod (old version), DataSource, MetricDefinition
- FinancialObservation (old version), ObservationSet (old version)
```

**Proposal**: 

**Option A**: Delete `financial_observation.py`, keep only `observation.py`
- ✅ Clean slate, no confusion
- ❌ Breaking change for any code using old models

**Option B**: Keep both, deprecate `financial_observation.py`
- ✅ Backward compatible
- ❌ Confusion about which to use
- ❌ Maintenance of two models

**Option C**: Merge best of both into `observation.py`
- ✅ Single source of truth
- ✅ Can keep useful factory functions
- ❌ Requires careful migration

**Recommendation**: **Option A** - Delete legacy file after migration period.

**Migration Plan**:
1. Add deprecation warnings to `financial_observation.py` imports
2. Update all usages to new `observation.py` models
3. Remove `financial_observation.py` in v2.3.0

---

### P4: Extract Address Models

**Problem**: Address models in `graph.py` but used broadly.

**Current Location**: `graph.py` contains `Address` and `EntityAddress`.

**Proposal**: Create `entityspine/domain/address.py`

```python
# address.py
"""
Address domain models.

STDLIB ONLY - NO PYDANTIC.
"""

@dataclass(frozen=True, slots=True)
class Address:
    """Physical or mailing address."""
    line1: str
    city: str
    # ...

@dataclass(frozen=True, slots=True)  
class EntityAddress:
    """Links Entity to Address with type and validity."""
    entity_id: str
    address: Address
    address_type: AddressType
    # ...
```

**Benefits**:
- ✅ Addresses are their own domain concept
- ✅ Reduces `graph.py` size
- ✅ Can add address-specific utilities

**Recommendation**: 🟡 **CONSIDER** - Lower priority than P1/P2.

---

### P5: Create Type Aliases Module

**Problem**: Common type patterns repeated across files.

**Examples**:
```python
# Repeated in many files
entity_id: str
security_id: str | None
claim_ids: list[str]
```

**Proposal**: Create `entityspine/domain/types.py`

```python
# types.py
"""
Common type aliases for EntitySpine domain.

STDLIB ONLY - NO PYDANTIC.
"""
from typing import TypeAlias

# ID types (for documentation/type checking)
EntityId: TypeAlias = str
SecurityId: TypeAlias = str
ListingId: TypeAlias = str
ClaimId: TypeAlias = str
ObservationId: TypeAlias = str

# Collection types
EntityIds: TypeAlias = list[str]
ClaimIds: TypeAlias = list[str]

# Optional patterns
OptionalEntityId: TypeAlias = str | None
OptionalSecurityId: TypeAlias = str | None
```

**Usage**:
```python
from entityspine.domain.types import EntityId, OptionalSecurityId

@dataclass(frozen=True, slots=True)
class Observation:
    entity_id: EntityId  # More semantic than just 'str'
    security_id: OptionalSecurityId = None
```

**Benefits**:
- ✅ Self-documenting code
- ✅ IDE autocompletion shows meaning
- ✅ Easy to change ID type later (e.g., to NewType)

**Drawbacks**:
- ❌ Extra import
- ❌ Marginal benefit for simple types
- ❌ TypeAlias may confuse some developers

**Recommendation**: 🟡 **CONSIDER** - Nice to have, not essential.

---

## Migration Strategy

### Phase 1: Enum Split (1-2 days)

```bash
# Step 1: Create enum subpackage
mkdir entityspine/domain/enums/
touch entityspine/domain/enums/__init__.py

# Step 2: Split enums into logical files
# (Move classes, update imports)

# Step 3: Update enums/__init__.py to re-export all
# Step 4: Update domain/__init__.py imports
# Step 5: Run tests, fix any import errors
```

**Backward Compatibility**:
```python
# domain/__init__.py - keep existing imports working
from entityspine.domain.enums import (
    EntityType,
    EntityStatus,
    # ... all enums still exported from domain
)
```

### Phase 2: Graph Split (2-3 days)

```bash
# Step 1: Create graph subpackage
mkdir entityspine/domain/graph/
touch entityspine/domain/graph/__init__.py

# Step 2: Extract classes into logical files
# Step 3: Handle cross-references with careful import ordering
# Step 4: Update graph/__init__.py to re-export all
# Step 5: Run tests
```

### Phase 3: Observation Consolidation (1 day)

```bash
# Step 1: Add deprecation warnings to financial_observation.py
# Step 2: Migrate factory functions to observation.py if needed
# Step 3: Update all imports to use observation.py
# Step 4: Delete financial_observation.py
```

### Phase 4: Optional Improvements (as needed)

- Extract address models
- Add type aliases
- Other refinements

---

## Decision Matrix

| Proposal | Impact | Effort | Risk | Priority |
|----------|--------|--------|------|----------|
| P1: Split enums | High | Low | Low | 🔴 P0 |
| P2: Split graph | High | Medium | Medium | 🔴 P0 |
| P3: Consolidate observation | Medium | Low | Low | 🟡 P1 |
| P4: Extract address | Low | Low | Low | 🟢 P2 |
| P5: Type aliases | Low | Low | Low | 🟢 P2 |

---

## Proposed Final Structure

After all improvements:

```
entityspine/domain/
├── __init__.py              # Main exports
├── entity.py                # Entity model
├── security.py              # Security model
├── listing.py               # Listing model
├── claim.py                 # IdentifierClaim model
├── candidate.py             # ResolutionCandidate
├── resolution.py            # ResolutionResult
├── observation.py           # Financial observations (v2.2.5)
├── timeline.py              # Timeline models
├── clustering.py            # Clustering models
├── address.py               # Address, EntityAddress
├── timestamps.py            # ULID, UTC utilities
├── validators.py            # Validation functions
├── factories.py             # Factory functions
├── protocols.py             # Protocol interfaces
├── types.py                 # Type aliases (optional)
│
├── enums/                   # Enum subpackage
│   ├── __init__.py
│   ├── core.py              # Entity/Security/Listing enums
│   ├── identifiers.py       # Identifier enums
│   ├── resolution.py        # Resolution enums
│   ├── graph.py             # Graph/relationship enums
│   ├── events.py            # Event enums
│   ├── assets.py            # Asset/contract enums
│   ├── observations.py      # Observation enums
│   ├── vendors.py           # Vendor enums
│   ├── geo.py               # Geography enums
│   └── transactions.py      # Transaction enums
│
└── graph/                   # Graph subpackage
    ├── __init__.py
    ├── refs.py              # NodeKind, NodeRef
    ├── roles.py             # Person roles, participants
    ├── ownership.py         # Ownership, transactions
    ├── relationships.py     # Entity relationships
    ├── clusters.py          # Entity clusters
    ├── nodes.py             # Geo, Case, Asset, etc.
    └── traversal.py         # Path finding results
```

**File Count**: ~30 files (up from ~17)
**Average File Size**: ~150 lines (down from ~300)
**Maintainability**: ⬆️ Significantly improved

---

## Open Questions

1. **Should we use `__all__` in subpackages?**
   - Pro: Explicit exports
   - Con: More maintenance

2. **Should enum files be `_enums.py` (private) or `enums.py` (public)?**
   - Current: Public, re-exported
   - Alternative: Private, only accessed via `enums/__init__.py`

3. **Should we add `py.typed` marker?**
   - Yes if we want to be a typed package for downstream type checkers

4. **Should graph models use composition over inheritance?**
   - Current: Flat dataclasses
   - Alternative: Base `GraphNode` class with subtypes

---

## Appendix: Current vs Proposed Line Counts

| Module | Current | Proposed | Change |
|--------|---------|----------|--------|
| `enums.py` | 857 | ~80 (index) | -90% |
| `enums/*.py` | 0 | ~800 total | Split |
| `graph.py` | 1,502 | ~80 (index) | -95% |
| `graph/*.py` | 0 | ~1,400 total | Split |
| `financial_observation.py` | 606 | 0 | Deleted |
| `observation.py` | 786 | ~800 | Merge |
| **Total domain/** | ~5,600 | ~5,200 | -7% |

Net effect: Same code, better organization.

---

## Conclusion

The highest-impact improvements are:

1. **Split `enums.py`** - 42 enums is too many for one file
2. **Split `graph.py`** - 1,500 lines with mixed concerns
3. **Delete legacy `financial_observation.py`** - Consolidate to single model

These changes maintain backward compatibility while significantly improving code organization and maintainability.

**Next Steps**:
1. Review and approve this RFC
2. Create tracking issues for each proposal
3. Execute Phase 1 (enum split) as proof of concept
4. Evaluate and proceed with remaining phases
