# ADR-001: Stdlib-only Domain Layer

**Status**: Accepted  
**Date**: 2025-12  
**Deciders**: Project maintainers

## Context

The domain layer contains core business logic: Entity, Security, Listing, IdentifierClaim, and all enums. We needed to decide whether to use Pydantic, SQLAlchemy, or stdlib-only constructs.

Dependencies in the domain layer create coupling problems:
- Pydantic models can't be used without pydantic installed
- ORM models tie domain logic to database schema
- Third-party validation libraries evolve independently

## Decision

**The domain layer uses only Python stdlib** - dataclasses, typing, enum, datetime, decimal.

```python
# YES - stdlib only
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum

@dataclass(frozen=True, slots=True)
class Entity:
    id: str
    name: str
    ...

# NO - external dependencies
from pydantic import BaseModel  # Not in domain
from sqlalchemy import Column   # Not in domain
```

Pydantic and ORM wrappers live in `entityspine.ext.*` packages.

## Consequences

### Positive
- Zero external dependencies for core logic
- Domain models work in any context (CLI, API, tests)
- Validation logic is explicit and testable
- No version conflicts with Pydantic/SQLAlchemy

### Negative
- Manual validation code (no Pydantic `@validator`)
- Duplicate model definitions in ext layers
- No automatic JSON schema generation

### Mitigations
- `validators.py` contains all validation functions
- Factory functions ensure valid object creation
- Pydantic wrappers delegate to stdlib validators
