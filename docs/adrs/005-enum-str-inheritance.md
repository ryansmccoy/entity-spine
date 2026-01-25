# ADR-005: Enum str Inheritance

**Status**: Accepted  
**Date**: 2025-12  
**Deciders**: Project maintainers

## Context

Enums need to serialize to JSON and be compared with string values from external sources (APIs, databases, CSV files).

Options:
1. Regular `Enum` with explicit `.value` access
2. `StrEnum` (Python 3.11+)
3. `(str, Enum)` multiple inheritance

## Decision

**All enums inherit from `(str, Enum)` for automatic JSON serialization.**

```python
class EntityType(str, Enum):
    """Type of legal entity."""
    CORPORATION = "corporation"
    PARTNERSHIP = "partnership"
    TRUST = "trust"
    ...
```

## Consequences

### Positive
- **JSON serialization**: `json.dumps(entity_type)` just works
- **String comparison**: `entity_type == "corporation"` works
- **API compatibility**: FastAPI/Pydantic serialize automatically
- **Database storage**: Store as string without conversion

### Negative
- Slightly non-standard pattern
- Python 3.11 has `StrEnum` which is cleaner
- Must remember to use lowercase values for consistency

### Usage Examples
```python
# String comparison works
if entity.entity_type == "corporation":
    ...

# JSON serialization works
import json
json.dumps({"type": EntityType.CORPORATION})
# '{"type": "corporation"}'

# Can construct from string
EntityType("corporation")  # EntityType.CORPORATION
```

### Why Not StrEnum?
`StrEnum` was added in Python 3.11. We support Python 3.10+, so `(str, Enum)` provides compatibility.

When we drop 3.10 support:
```python
# Future - Python 3.11+
from enum import StrEnum

class EntityType(StrEnum):
    CORPORATION = "corporation"
```
