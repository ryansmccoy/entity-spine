# EntitySpine v0.3.0 Migration Guide

## Overview

v0.3.0 introduces a **zero-dependency core** architecture. The canonical domain models are now stdlib dataclasses, with Pydantic and ORM layers available as optional extras.

## Breaking Changes

### 1. Core Package is Now Zero-Dependency

**Before (v0.2.x):**
```python
# Required pydantic as core dependency
pip install entityspine  # Installed pydantic automatically
```

**After (v0.3.0):**
```python
# Core is stdlib-only
pip install entityspine  # No external dependencies

# For Pydantic models (optional)
pip install entityspine[pydantic]

# For SQLModel store (optional)
pip install entityspine[sqlmodel]
```

### 2. Domain Models are Now Dataclasses

**Before (v0.2.x):**
```python
from entityspine import Entity  # Was a Pydantic model

entity = Entity(primary_name="Apple Inc.", cik="0000320193")
entity.model_dump()  # Pydantic method
```

**After (v0.3.0):**
```python
from entityspine import Entity  # Now a stdlib dataclass

entity = Entity(primary_name="Apple Inc.", source_system="sec", source_id="0000320193")

# Use dataclasses.asdict instead of model_dump
from dataclasses import asdict
asdict(entity)
```

### 3. Entity No Longer Has Identifier Fields

**Before (v0.2.x):**
```python
entity = Entity(
    primary_name="Apple Inc.",
    cik="0000320193",      # Convenience field
    lei="HWUPKR...",       # Convenience field
    identifiers={...},     # Dict field
)
```

**After (v0.3.0):**
```python
# Entity has NO identifier fields - use IdentifierClaim
entity = Entity(
    primary_name="Apple Inc.",
    source_system="sec",      # Record provenance only
    source_id="0000320193",   # Record provenance only
)

# Track identifiers via IdentifierClaim
claim = IdentifierClaim(
    entity_id=entity.entity_id,
    scheme=IdentifierScheme.CIK,
    value="0000320193",
    namespace=VendorNamespace.SEC,
)
```

### 4. Pydantic Models Moved to Optional Path

**Before (v0.2.x):**
```python
from entityspine.models import Entity  # Pydantic model
```

**After (v0.3.0):**
```python
# Pydantic models require the [pydantic] extra
# pip install entityspine[pydantic]
from entityspine.models import Entity  # Pydantic wrapper
```

## Migration Steps

### Step 1: Update Your Dependencies

```toml
# pyproject.toml
[project]
dependencies = [
    "entityspine[pydantic,sqlmodel]",  # If you need Pydantic/ORM
    # OR
    "entityspine",  # For stdlib-only usage
]
```

### Step 2: Update Entity Creation

```python
# Old
entity = Entity(primary_name="Apple", cik="0000320193")

# New
entity = Entity(primary_name="Apple", source_system="sec", source_id="0000320193")
claim = IdentifierClaim(
    entity_id=entity.entity_id,
    scheme=IdentifierScheme.CIK,
    value="0000320193",
    namespace=VendorNamespace.SEC,
)
```

### Step 3: Update Serialization

```python
# Old (Pydantic)
data = entity.model_dump()

# New (stdlib dataclass)
from dataclasses import asdict
data = asdict(entity)
```

### Step 4: Update Import Paths (if using Pydantic)

```python
# If you need Pydantic validation features:
from entityspine.models import Entity as PydanticEntity
from entityspine import Entity as DomainEntity

# Convert between them
domain_entity = pydantic_entity.to_domain()
pydantic_entity = PydanticEntity.from_domain(domain_entity)
```

## New Features

### VendorNamespace for Multi-Vendor Crosswalks

```python
from entityspine import VendorNamespace

claim = IdentifierClaim(
    entity_id="...",
    scheme=IdentifierScheme.FIGI,
    value="BBG000B9XRY4",
    namespace=VendorNamespace.OPENFIGI,  # Track data source
)
```

### Observation Time vs Validity Time

```python
claim = IdentifierClaim(
    entity_id="...",
    scheme=IdentifierScheme.LEI,
    value="HWUPKR...",
    captured_at=datetime.now(),  # When we observed this
    valid_from=date(2012, 6, 1),  # When LEI was assigned
    valid_to=None,                # Still valid
)
```

### Scheme-Scope Enforcement

```python
from entityspine import SCHEME_SCOPES, IdentifierScope

# CIK must be on entity_id
SCHEME_SCOPES["cik"] == IdentifierScope.ENTITY

# ISIN must be on security_id
SCHEME_SCOPES["isin"] == IdentifierScope.SECURITY

# TICKER must be on listing_id
SCHEME_SCOPES["ticker"] == IdentifierScope.LISTING
```

### Resolution Candidates

```python
result = store.resolve("AAPL")
for candidate in result.candidates:
    print(f"{candidate.entity_id}: {candidate.score} ({candidate.match_reason})")
```

## Package Structure

```
entityspine/
├── domain/           # Canonical stdlib dataclasses (ZERO deps)
│   ├── entity.py
│   ├── security.py
│   ├── listing.py
│   ├── claim.py
│   ├── resolution.py
│   ├── validators.py
│   └── enums.py
├── models/           # Pydantic wrappers (optional)
├── stores/           # SQLModel store (optional)
└── db/               # Database layer (optional)
```

## Extras Reference

| Extra | Description | Dependencies |
|-------|-------------|--------------|
| (none) | Core stdlib-only | None |
| `pydantic` | Pydantic models | pydantic>=2.5.0 |
| `sqlmodel` | SQLModel ORM | sqlmodel, pydantic |
| `sqlite` | SQLite store | sqlmodel |
| `dev` | Development tools | pydantic, sqlmodel, pytest, etc. |

## FAQ

**Q: Why remove Pydantic from core?**

A: To honor the Tier 0/1 "zero dependencies" contract. Users who only need basic entity modeling shouldn't be forced to install Pydantic.

**Q: Can I still use Pydantic validation?**

A: Yes! Install `entityspine[pydantic]` and import from `entityspine.models`.

**Q: Why move identifiers to IdentifierClaim?**

A: IdentifierClaim provides:
- Provenance tracking (who said this identifier belongs here?)
- Validity periods (when was this identifier valid?)
- Multi-vendor crosswalks (Bloomberg says X, FactSet says Y)
- Audit trail (captured_at tells when we learned this)

**Q: Is the SQLModel store still available?**

A: Yes, with `entityspine[sqlmodel]`. The store automatically populates legacy CIK columns for backward compatibility.
