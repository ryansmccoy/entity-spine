# Prompt: Graph Module Refactoring (P2)

> **Feature**: Split `graph.py` into focused domain modules  
> **Priority**: 🔴 P0 (High Impact, Medium Effort)  
> **Estimated Effort**: 2-3 hours

---

## Context

EntitySpine's `entityspine/domain/graph.py` has grown to 1,502 lines with 25 classes mixing different concerns (nodes, relationships, traversal results, addresses, ownership). This violates single responsibility principle and makes the file difficult to maintain.

## Current State

```
entityspine/domain/graph.py (1,502 lines, 25 classes)
```

Current classes grouped by concern:
- **Reference types**: NodeKind (enum), NodeRef
- **Person/Roles**: PersonRole, FilingParticipant, RoleAssignment
- **Ownership**: OwnershipPosition, InsiderTransaction
- **Addresses**: Address, EntityAddress
- **Relationships**: EntityRelationship, Relationship
- **Clusters**: EntityCluster, EntityClusterMember
- **Entity Nodes**: Geo, Case, Asset, Contract, Product, Brand, Event
- **Traversal Results**: RelatedEntity, OfficerInfo, PathStep, EntityPath, EntityNetwork

## Target State

```
entityspine/domain/graph/
├── __init__.py          # Re-exports ALL classes for backward compatibility
├── refs.py              # NodeKind (move to enums/), NodeRef (~50 lines)
├── roles.py             # PersonRole, FilingParticipant, RoleAssignment (~200 lines)
├── ownership.py         # OwnershipPosition, InsiderTransaction (~200 lines)
├── addresses.py         # Address, EntityAddress (~150 lines)
├── relationships.py     # EntityRelationship, Relationship (~200 lines)
├── clusters.py          # EntityCluster, EntityClusterMember (~100 lines)
├── nodes.py             # Geo, Case, Asset, Contract, Product, Brand, Event (~400 lines)
└── traversal.py         # RelatedEntity, OfficerInfo, PathStep, EntityPath, EntityNetwork (~200 lines)
```

## Requirements

1. **Backward Compatibility**: All existing imports must continue to work:
   ```python
   # These must still work after refactoring:
   from entityspine.domain.graph import Address, NodeRef, EntityRelationship
   from entityspine.domain import Address, NodeRef
   ```

2. **Follow EntitySpine Conventions**:
   - Each file must have `"""STDLIB ONLY - NO PYDANTIC."""` header
   - Use `@dataclass(frozen=True, slots=True)` for all dataclasses
   - Use `generate_ulid()` for IDs, `utc_now()` for timestamps
   - Use `str | None` not `Optional[str]`
   - Validation in `__post_init__`

3. **Handle Cross-References**: Some classes reference others:
   - `EntityAddress` references `Address`
   - `EntityPath` references `PathStep`
   - Use careful import ordering or string forward references

4. **Move NodeKind Enum**: `NodeKind` is an enum and should ideally be in `enums/graph.py`, but can stay in `graph/refs.py` for now to minimize changes.

5. **Tests Must Pass**: Run `pytest tests/unit/` - all 298 tests must pass

## Task

1. Create the `graph/` directory structure
2. Move each class to its appropriate file based on concern
3. Handle cross-file imports carefully
4. Create `graph/__init__.py` that re-exports everything
5. Update `domain/__init__.py` to import from `graph/` package
6. Delete the old `graph.py` file
7. Run tests to verify nothing broke

## File Groupings

### `refs.py`
```python
# NodeKind enum (could move to enums/ later)
# NodeRef dataclass
```

### `roles.py`
```python
# PersonRole - Officer/director role
# FilingParticipant - SEC filing participant
# RoleAssignment - Role assignment record
```

### `ownership.py`
```python
# OwnershipPosition - Shareholding position
# InsiderTransaction - Form 4 transaction
```

### `addresses.py`
```python
# Address - Physical address
# EntityAddress - Links entity to address
```

### `relationships.py`
```python
# EntityRelationship - Between two entities
# Relationship - Generic relationship edge
```

### `clusters.py`
```python
# EntityCluster - Group of related entities
# EntityClusterMember - Membership in cluster
```

### `nodes.py`
```python
# Geo - Geographic location
# Case - Legal case
# Asset - Physical asset
# Contract - Legal contract
# Product - Product/service
# Brand - Brand/trademark
# Event - Business event
```

### `traversal.py`
```python
# RelatedEntity - Related entity result
# OfficerInfo - Officer information
# PathStep - Single step in path
# EntityPath - Full path between entities
# EntityNetwork - Network of relationships
```

## Conventions Reference

See `entityspine/docs/ENTITYSPINE_CONVENTIONS.md` for full conventions.

## Verification

```bash
cd entityspine
python -m pytest tests/unit/ -v --tb=short
# Expected: 298 passed
```

Also verify imports work:
```python
from entityspine.domain.graph import Address, NodeRef, EntityRelationship, Asset
from entityspine.domain import Address, NodeRef  # Must still work
print("All imports successful")
```
