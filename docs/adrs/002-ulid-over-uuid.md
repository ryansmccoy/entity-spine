# ADR-002: ULID over UUID4

**Status**: Accepted  
**Date**: 2025-12  
**Deciders**: Project maintainers

## Context

Every domain object needs a unique identifier. Options considered:
1. **UUID4** - Random, no ordering
2. **UUID7** - Time-ordered (draft spec)
3. **ULID** - Time-ordered, lexicographically sortable
4. **Snowflake IDs** - Twitter-style, requires coordinator

## Decision

**Use ULIDs for all entity/claim/observation IDs.**

```python
# timestamps.py
import ulid

def generate_ulid() -> str:
    """Generate a ULID string for use as entity ID."""
    return str(ulid.new())

# Usage
entity = Entity(
    id=generate_ulid(),  # "01HQXK5J8RYFV3KWJZ4S9NBNMV"
    name="Apple Inc.",
    ...
)
```

## Consequences

### Positive
- **Time-ordered**: IDs sort chronologically
- **Lexicographic**: String sorting = time sorting (great for indexes)
- **Compact**: 26 chars vs 36 for UUID
- **URL-safe**: No special characters
- **Monotonic**: Can generate many per millisecond

### Negative
- External dependency (`python-ulid`)
- Less universally recognized than UUID
- Timestamp extraction possible (minor privacy concern)

### Why Not UUID4?
```python
# UUIDs don't sort by creation time
ids = [uuid4() for _ in range(3)]
sorted(ids)  # Random order, not creation order

# ULIDs do
ids = [ulid.new() for _ in range(3)]
sorted(ids)  # Creation order preserved
```

### Why Not UUID7?
UUID7 provides similar benefits but:
- Still in draft spec (RFC 9562)
- Longer string representation (36 chars)
- Less Python library support
