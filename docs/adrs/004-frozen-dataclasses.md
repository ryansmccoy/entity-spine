# ADR-004: Frozen Dataclasses

**Status**: Accepted  
**Date**: 2025-12  
**Deciders**: Project maintainers

## Context

Domain objects need to be immutable to:
- Ensure thread safety
- Enable caching/memoization
- Prevent accidental mutation
- Support hashability (for sets/dict keys)

Options:
1. Regular dataclasses with discipline
2. `frozen=True` dataclasses
3. Named tuples
4. attrs with `frozen=True`

## Decision

**All domain dataclasses use `frozen=True` and `slots=True`.**

```python
@dataclass(frozen=True, slots=True)
class Entity:
    id: str
    name: str
    entity_type: EntityType
    ...
```

## Consequences

### Positive
- **Immutable**: Cannot accidentally modify
- **Hashable**: Can use in sets, as dict keys
- **Memory efficient**: `slots=True` reduces memory ~40%
- **Thread safe**: No locks needed for reads
- **Cache friendly**: Safe to cache without copying

### Negative
- Cannot modify after creation (use `dataclasses.replace()`)
- `__post_init__` can't set computed fields normally
- Slightly more verbose for updates

### Mutation Pattern
```python
# WRONG - raises FrozenInstanceError
entity.name = "New Name"

# CORRECT - create new instance
from dataclasses import replace
updated = replace(entity, name="New Name")
```

### Computed Fields in `__post_init__`
```python
@dataclass(frozen=True, slots=True)
class Observation:
    metric: MetricSpec
    _cache_key: str = field(init=False)
    
    def __post_init__(self):
        # Use object.__setattr__ for frozen dataclasses
        object.__setattr__(self, "_cache_key", self._compute_key())
```
