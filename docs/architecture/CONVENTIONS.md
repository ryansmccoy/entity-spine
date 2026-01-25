# EntitySpine Code Conventions Manifesto

> **Version**: 2.2.5  
> **Last Updated**: January 2026  
> **Status**: Canonical Reference

This document defines the authoritative conventions for all code in the EntitySpine domain layer. Following these conventions ensures consistency, maintainability, and the stdlib-only guarantee.

---

## Table of Contents

1. [Core Principles](#core-principles)
2. [File Organization](#file-organization)
3. [Dataclass Patterns](#dataclass-patterns)
4. [Type Hint Conventions](#type-hint-conventions)
5. [Enum Conventions](#enum-conventions)
6. [ID Generation](#id-generation)
7. [Timestamp Conventions](#timestamp-conventions)
8. [Validation Patterns](#validation-patterns)
9. [Factory Functions](#factory-functions)
10. [Import Organization](#import-organization)
11. [Documentation Standards](#documentation-standards)

---

## Core Principles

### 1. STDLIB ONLY - NO PYDANTIC

The domain layer has **zero non-stdlib dependencies**. This is a Tier 0/1 guarantee.

```python
"""
Module description here.

STDLIB ONLY - NO PYDANTIC.
"""
```

Every file in `entityspine.domain` MUST include this header comment. No exceptions.

**Why?**
- Domain models can be used in any context (CLI, API, workers)
- No version conflicts with downstream consumers
- Faster imports, smaller footprint
- Forces clean separation between domain logic and framework concerns

### 2. Single Source of Truth

- **Enums**: ALL enums live in `enums.py` (never inline)
- **Validators**: ALL validation functions live in `validators.py`
- **Timestamps**: ALL time utilities live in `timestamps.py`
- **Factories**: ALL factory functions live in `factories.py`

**Why?**
- Prevents duplication (DRY)
- Easy to find and maintain
- Clear dependency graph

### 3. Immutability by Default

Domain models are frozen dataclasses. Mutation happens through explicit factory methods that return new instances.

---

## File Organization

### Standard File Header

```python
"""
Brief description of module purpose.

STDLIB ONLY - NO PYDANTIC.

v2.2.X DESIGN:
- Key design decision 1
- Key design decision 2
- Key design decision 3
"""

from dataclasses import dataclass, field
from datetime import datetime
# ... stdlib imports ...

from entityspine.domain.enums import (
    # Explicit enum imports
)
from entityspine.domain.timestamps import generate_ulid, utc_now
```

### Import Order

1. **Stdlib imports** (alphabetical)
2. **Blank line**
3. **EntitySpine domain imports** (alphabetical)
4. **Blank line**
5. **Type checking imports** (if needed)

```python
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from entityspine.domain.enums import EntityType, EntityStatus
from entityspine.domain.timestamps import generate_ulid, utc_now
from entityspine.domain.validators import normalize_cik

if TYPE_CHECKING:
    from entityspine.domain.claim import IdentifierClaim
```

---

## Dataclass Patterns

### Standard Dataclass Declaration

```python
@dataclass(frozen=True, slots=True)
class MyModel:
    """
    Brief description.
    
    Longer description with usage examples.
    
    Attributes:
        field_name: Description of field.
        another_field: Description with units/format.
    """
    
    # Required fields first (no defaults)
    required_field: str
    another_required: int
    
    # Primary key with ULID default
    model_id: str = field(default_factory=generate_ulid)
    
    # Optional fields use str | None (NOT Optional[str])
    optional_field: str | None = None
    
    # Timestamps with utc_now default
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    
    def __post_init__(self):
        """Validate after creation."""
        if not self.required_field or not self.required_field.strip():
            raise ValueError("required_field cannot be empty")
```

### Key Rules

| Rule | Correct | Incorrect |
|------|---------|-----------|
| Frozen | `@dataclass(frozen=True, slots=True)` | `@dataclass` |
| Optional types | `str \| None` | `Optional[str]` |
| IDs | `field(default_factory=generate_ulid)` | `field(default_factory=lambda: str(uuid.uuid4()))` |
| Timestamps | `field(default_factory=utc_now)` | `field(default_factory=datetime.utcnow)` |
| Validation | `__post_init__` method | External validation |

### Mutable Collections in Frozen Dataclasses

For collections that need post-init mutation, use mutable defaults carefully:

```python
@dataclass(frozen=True, slots=True)
class Entity:
    entity_id: str
    aliases: list[str] = field(default_factory=list)
    
    def add_alias(self, alias: str) -> None:
        """Add alias (mutates internal list, not the reference)."""
        if alias not in self.aliases:
            self.aliases.append(alias)
```

Or prefer returning new instances:

```python
def with_alias(self, alias: str) -> "Entity":
    """Return new Entity with added alias."""
    new_aliases = self.aliases + [alias] if alias not in self.aliases else self.aliases
    return dataclasses.replace(self, aliases=new_aliases)
```

---

## Type Hint Conventions

### Modern Python Style (3.10+)

```python
# CORRECT - Modern union syntax
optional_field: str | None = None
union_field: int | float = 0

# INCORRECT - Legacy typing module
from typing import Optional, Union
optional_field: Optional[str] = None  # DON'T USE
union_field: Union[int, float] = 0    # DON'T USE
```

### Generic Collections

```python
# CORRECT - Builtin generics (3.9+)
items: list[str]
mapping: dict[str, int]
coordinates: tuple[float, float]

# INCORRECT - typing module generics
from typing import List, Dict, Tuple
items: List[str]       # DON'T USE
mapping: Dict[str, int] # DON'T USE
```

### Forward References

```python
# CORRECT - String literal for forward reference
def process(self) -> "MyModel":
    ...

# Also acceptable in dataclass fields
parent: "Entity | None" = None
```

---

## Enum Conventions

### Location

**ALL enums MUST be defined in `enums.py`**. Never define enums inline in model files.

### Standard Enum Pattern

```python
class MyStatus(str, Enum):
    """
    Brief description of what this enum represents.
    
    Used in XyzModel for categorizing ABC.
    
    Examples:
        >>> MyStatus.ACTIVE.value
        'active'
    """
    
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
```

### Key Rules

| Rule | Correct | Incorrect |
|------|---------|-----------|
| Base class | `class X(str, Enum)` | `class X(Enum)` |
| Values | Lowercase strings | `ACTIVE = "ACTIVE"` |
| Naming | SCREAMING_SNAKE for members | `Active = "active"` |
| Docstrings | Required with examples | No docstring |

### Why `(str, Enum)`?

```python
class Status(str, Enum):
    ACTIVE = "active"

# JSON serialization works automatically
import json
json.dumps({"status": Status.ACTIVE})  # '{"status": "active"}'

# String comparison works
Status.ACTIVE == "active"  # True
```

---

## ID Generation

### ULID Format

EntitySpine uses ULIDs (Universally Unique Lexicographically Sortable Identifiers):

```python
from entityspine.domain.timestamps import generate_ulid

entity_id = generate_ulid()
# Example: "01HGW2SBSX6VY0XJHK5Z3QKPW8"
```

**Properties:**
- 26 characters, base32 encoded
- Time-sortable (first 10 chars = timestamp)
- Globally unique (16 chars random)
- URL-safe, case-insensitive

### Usage in Dataclasses

```python
@dataclass(frozen=True, slots=True)
class Entity:
    primary_name: str
    entity_id: str = field(default_factory=generate_ulid)
```

### NEVER Use

```python
# DON'T USE uuid
import uuid
entity_id: str = field(default_factory=lambda: str(uuid.uuid4()))

# DON'T USE custom ID generation
entity_id: str = field(default_factory=lambda: f"ENT-{random.randint(0, 999999)}")
```

---

## Timestamp Conventions

### UTC Only

All timestamps MUST be UTC-aware:

```python
from entityspine.domain.timestamps import utc_now

@dataclass(frozen=True, slots=True)
class Observation:
    captured_at: datetime = field(default_factory=utc_now)
```

### NEVER Use

```python
# DON'T USE - naive datetime
from datetime import datetime
created_at: datetime = field(default_factory=datetime.utcnow)  # Naive!

# DON'T USE - local time
created_at: datetime = field(default_factory=datetime.now)  # Local!
```

### Time Semantics

EntitySpine distinguishes three time concepts:

| Field | Meaning | Example |
|-------|---------|---------|
| `captured_at` | When our system ingested | `2025-01-28T12:00:00Z` |
| `valid_from` / `valid_to` | When the fact was true | `2024-01-01` to `2024-12-31` |
| `as_of` | When it was known/published | `2025-01-15T09:30:00Z` |

---

## Validation Patterns

### In `__post_init__`

Validation happens in `__post_init__` for frozen dataclasses:

```python
@dataclass(frozen=True, slots=True)
class Entity:
    entity_id: str
    primary_name: str
    
    def __post_init__(self):
        """Validate after creation."""
        if not self.entity_id or not self.entity_id.strip():
            raise ValueError("entity_id cannot be empty")
        if not self.primary_name or not self.primary_name.strip():
            raise ValueError("primary_name cannot be empty")
```

### Setting Computed Fields

For frozen dataclasses, use `object.__setattr__`:

```python
def __post_init__(self):
    """Validate and normalize."""
    # Normalize the value
    normalized = self.cik.lstrip("0").zfill(10)
    object.__setattr__(self, "cik", normalized)
```

### Reusable Validators

Complex validation logic goes in `validators.py`:

```python
# In validators.py
def normalize_cik(value: str) -> str:
    """Normalize CIK to 10-digit zero-padded string."""
    if not value:
        raise ValueError("CIK cannot be empty")
    digits = "".join(c for c in value if c.isdigit())
    if not digits:
        raise ValueError(f"CIK contains no digits: {value}")
    return digits.zfill(10)

# In claim.py
def __post_init__(self):
    if self.scheme == IdentifierScheme.CIK:
        normalized = normalize_cik(self.value)
        object.__setattr__(self, "value", normalized)
```

---

## Factory Functions

### Location

Factory functions live in `factories.py`, not in the model files.

### Standard Pattern

```python
# In factories.py
def create_entity(
    primary_name: str,
    entity_type: EntityType = EntityType.ORGANIZATION,
    *,
    entity_id: str | None = None,
    source_system: str | None = None,
    aliases: list[str] | None = None,
) -> Entity:
    """
    Create an Entity with proper defaults.
    
    Args:
        primary_name: Legal/canonical name
        entity_type: Type classification
        entity_id: Optional specific ID (generates ULID if None)
        source_system: Source system identifier
        aliases: Alternative names
    
    Returns:
        New Entity instance
        
    Examples:
        >>> entity = create_entity("Apple Inc.")
        >>> entity.primary_name
        'Apple Inc.'
    """
    return Entity(
        entity_id=entity_id or generate_ulid(),
        primary_name=primary_name,
        entity_type=entity_type,
        source_system=source_system,
        aliases=aliases or [],
    )
```

### Specialized Factories

```python
def create_security(
    entity_id: str,
    security_name: str,
    security_type: SecurityType = SecurityType.COMMON_STOCK,
    **kwargs,
) -> Security:
    """Create Security linked to Entity."""
    ...

def found_result(
    entity: Entity,
    tier: ResolutionTier,
    query: str,
    **kwargs,
) -> ResolutionResult:
    """Create successful resolution result."""
    ...
```

---

## Import Organization

### In `__init__.py`

Explicit imports with logical grouping:

```python
"""
EntitySpine Canonical Domain Models (stdlib-only).

STDLIB ONLY - NO PYDANTIC.
"""

# Core models
from entityspine.domain.entity import Entity
from entityspine.domain.security import Security
from entityspine.domain.listing import Listing
from entityspine.domain.claim import IdentifierClaim

# Enums (alphabetical within group)
from entityspine.domain.enums import (
    ClaimStatus,
    EntityStatus,
    EntityType,
    IdentifierScheme,
    # ... etc
)

# Factories
from entityspine.domain.factories import (
    create_entity,
    create_security,
    # ... etc
)

__all__ = [
    # Explicit, alphabetical
    "ClaimStatus",
    "Entity",
    "EntityStatus",
    # ... etc
]
```

---

## Documentation Standards

### Module Docstrings

```python
"""
Brief one-line description.

STDLIB ONLY - NO PYDANTIC.

v2.2.X DESIGN:
- Key design point 1
- Key design point 2

Longer description if needed, explaining the module's
purpose and how it fits into the overall architecture.
"""
```

### Class Docstrings

```python
@dataclass(frozen=True, slots=True)
class Entity:
    """
    Canonical entity (company, person, fund, etc.).
    
    The Entity is the root of the ownership graph. Securities,
    listings, and claims are all linked to entities.
    
    v2.2.3: Entity has NO identifier storage. All identifiers
    are stored as IdentifierClaims with proper scheme-scope
    enforcement.
    
    Attributes:
        entity_id: ULID primary key
        primary_name: Legal/canonical name
        entity_type: Classification (ORGANIZATION, PERSON, etc.)
        status: Lifecycle status
        
    Examples:
        >>> entity = Entity(
        ...     entity_id="01HTEST",
        ...     primary_name="Apple Inc.",
        ... )
        >>> entity.primary_name
        'Apple Inc.'
    """
```

### Enum Docstrings

```python
class SecurityType(str, Enum):
    """
    Type classification for securities.
    
    Used in Security nodes to categorize the instrument type.
    Maps to standard financial instrument taxonomies.
    
    Examples:
        >>> SecurityType.COMMON_STOCK.value
        'common_stock'
        
        >>> SecurityType.COMMON_STOCK in [SecurityType.COMMON_STOCK, SecurityType.PREFERRED]
        True
    """
    
    COMMON_STOCK = "common_stock"  # Ordinary shares
    PREFERRED = "preferred"  # Preferred shares
    # ... etc
```

---

## Quick Reference Card

```
┌─────────────────────────────────────────────────────────────┐
│                  ENTITYSPINE CONVENTIONS                     │
├─────────────────────────────────────────────────────────────┤
│ File Header:     """STDLIB ONLY - NO PYDANTIC."""           │
│ Dataclass:       @dataclass(frozen=True, slots=True)        │
│ Optional:        str | None   (NOT Optional[str])           │
│ IDs:             field(default_factory=generate_ulid)       │
│ Timestamps:      field(default_factory=utc_now)             │
│ Enums:           class X(str, Enum) in enums.py             │
│ Validation:      __post_init__ method                       │
│ Factories:       In factories.py, not model files           │
│ Validators:      In validators.py, reusable functions       │
└─────────────────────────────────────────────────────────────┘
```

---

## Anti-Patterns to Avoid

### ❌ Don't Do This

```python
# Inline enum (should be in enums.py)
class MyModel:
    class Status(Enum):
        ACTIVE = "ACTIVE"

# Optional from typing
from typing import Optional
field: Optional[str] = None

# UUID instead of ULID
import uuid
id: str = str(uuid.uuid4())

# Naive datetime
created: datetime = datetime.utcnow()

# Validation outside __post_init__
def validate(model: MyModel) -> bool:
    ...
```

### ✅ Do This Instead

```python
# Enum in enums.py
from entityspine.domain.enums import MyStatus

# Modern union syntax
field: str | None = None

# ULID generation
from entityspine.domain.timestamps import generate_ulid
id: str = field(default_factory=generate_ulid)

# UTC-aware datetime
from entityspine.domain.timestamps import utc_now
created: datetime = field(default_factory=utc_now)

# Validation in __post_init__
def __post_init__(self):
    if not self.field:
        raise ValueError("field required")
```

---

## Changelog

- **v2.2.5** (Jan 2026): Added observation model conventions, MetricSpec patterns
- **v2.2.4** (Jan 2026): Added knowledge graph model conventions
- **v2.2.3** (Dec 2025): Established IdentifierClaim as single source of truth
- **v2.2.0** (Nov 2025): Initial conventions document
