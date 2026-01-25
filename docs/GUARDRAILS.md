# EntitySpine Development Guardrails

> Enforced standards for code, documentation, and testing.

This document defines the **must-follow** rules for all EntitySpine development.
These are enforced via CI checks and pre-commit hooks.

---

## Table of Contents

1. [Ecosystem Collaboration](#ecosystem-collaboration)
2. [Code Standards](#code-standards)
3. [Documentation Standards](#documentation-standards)
4. [Testing Standards](#testing-standards)
5. [Package Standards](#package-standards)
6. [CI Enforcement](#ci-enforcement)

---

## Ecosystem Collaboration

### Three-Package Ecosystem (IMPORTANT)

EntitySpine is part of a **three-package ecosystem**:

```
py-sec-edgar (main app)  →  uses  →  EntitySpine (identity)
                         →  uses  →  FeedSpine (ingestion)
```

**Cross-package changes are ENCOURAGED when they improve the overall system.**

### When to Modify Other Packages

| Scenario | Action |
|----------|--------|
| EntitySpine needs a FeedSpine adapter | ✅ Create adapter in BOTH packages |
| py-sec-edgar integration is awkward | ✅ Improve EntitySpine's port interface |
| FeedSpine record model needs EntitySpine fields | ✅ Coordinate schema changes |
| Bug in FeedSpine affects EntitySpine | ✅ Fix in FeedSpine directly |

### Cross-Package Guidelines

```python
# ✅ ENCOURAGED - Improve integration
# If EntitySpine's API is awkward for py-sec-edgar, fix EntitySpine

# ✅ ENCOURAGED - Shared concerns
# If FeedSpine and EntitySpine both need timestamp utils, consider shared module

# ✅ ENCOURAGED - End-to-end thinking
# When adding a feature, consider the full flow: FeedSpine → EntitySpine → py-sec-edgar
```

### Package Locations

| Package | Path | Purpose |
|---------|------|--------|
| EntitySpine | `entityspine/` | Identity resolution |
| FeedSpine | `feedspine/` | Feed ingestion |
| py-sec-edgar | `py_sec_edgar/` | Main application |

### Integration Documentation

| Document | Location |
|----------|----------|
| Ecosystem Overview | `entityspine/docs/design/09_FEEDSPINE_INTEGRATION_ANALYSIS.md` |
| py-sec-edgar Integration | `py_sec_edgar/docs/PROMPT_INTEGRATION_V1.md` |
| FeedSpine Prompt | `feedspine/docs/PROMPT_FEEDSPINE_V1.md` |

---

## Code Standards

### Type Annotations (REQUIRED)

Every function and method MUST have complete type annotations.

```python
# ✅ CORRECT
def resolve(self, query: str) -> Entity | None:
    """Resolve any identifier to canonical entity."""
    ...

def get_by_cik(self, cik: str) -> Entity | None:
    """Get entity by CIK."""
    ...

# ❌ WRONG - Missing types
def resolve(self, query):
    ...
```

**Enforcement:** `mypy --strict`

### Import Style (REQUIRED)

```python
# ✅ CORRECT - Future annotations at top
from __future__ import annotations

import sqlite3                          # stdlib
from datetime import datetime
from typing import TYPE_CHECKING, Protocol, Optional

from pydantic import Field              # Pydantic v2
from entityspine.core.exceptions import EntityNotFoundError  # local

if TYPE_CHECKING:                       # type-only imports
    from entityspine.models import Entity
```

**Enforcement:** `ruff check --select I`

### Modern Python Syntax (REQUIRED)

```python
# ✅ CORRECT - Python 3.11+ syntax
def search(self, query: str, limit: int = 10) -> list[Entity]:
    ...

def get(self, entity_id: str) -> Entity | None:
    ...

# ❌ WRONG - Legacy typing
from typing import List, Optional
def search(self, query: str, limit: int = 10) -> List[Entity]:
    ...
```

**Enforcement:** `ruff check --select UP`

### Zero Dependencies for Tier 0-1 (CRITICAL)

Tier 0 and Tier 1 MUST use ONLY Python stdlib:

```python
# ✅ CORRECT - Stdlib only for Tier 0-1
import json
import sqlite3
from datetime import datetime
from urllib.request import urlopen

# ❌ WRONG - External deps in Tier 0-1
import requests  # Use urllib.request instead
import pendulum  # Use datetime instead
```

**Exception:** DuckDB (Tier 2) and PostgreSQL (Tier 3) use optional dependencies.

### Protocol Pattern (REQUIRED)

All storage backends MUST implement the `EntityStore` protocol:

```python
from typing import Protocol

class EntityStore(Protocol):
    """Storage backend interface."""
    
    def get(self, entity_id: str) -> Entity | None:
        """Get entity by ID."""
        ...
    
    def get_by_cik(self, cik: str) -> Entity | None:
        """Get entity by CIK."""
        ...
    
    def get_by_ticker(self, ticker: str) -> Entity | None:
        """Get entity by ticker symbol."""
        ...
    
    def search(self, query: str, limit: int = 10) -> list[Entity]:
        """Search entities by name."""
        ...
    
    def save(self, entity: Entity) -> None:
        """Save or update entity."""
        ...
```

---

## Documentation Standards

### Docstring Coverage (REQUIRED: 80% minimum)

Every public module, class, and function MUST have a docstring.

**Enforcement:** `interrogate --fail-under 80`

### Docstring Format (REQUIRED: Google Style)

```python
def resolve(self, query: str) -> Entity | None:
    """Resolve any identifier to a canonical entity.

    Attempts resolution in order: ticker, CIK, other identifiers, name search.
    Returns the first match found.

    Args:
        query: The identifier to resolve. Can be ticker, CIK, LEI, ISIN,
            or company name.

    Returns:
        The resolved Entity, or None if not found.

    Raises:
        ValidationError: If the query format is invalid.

    Example:
        >>> from entityspine import EntityResolver
        >>> resolver = EntityResolver()
        >>> entity = resolver.resolve("AAPL")
        >>> entity.name
        'Apple Inc.'

    See Also:
        get_by_cik: Direct CIK lookup.
        get_by_ticker: Direct ticker lookup.
    """
```

### Docstring Sections Reference

| Section | When Required | Purpose |
|---------|---------------|---------|
| **Summary** | ALWAYS | One-line description (first line) |
| **Extended** | Complex functions | Multi-line explanation |
| **Args** | Has parameters | Document each parameter |
| **Returns** | Non-None return | Document return value |
| **Raises** | Can raise | Document exceptions |
| **Example** | Public API | Runnable doctest |
| **See Also** | Related items | Cross-references |

### Doctest Examples (REQUIRED for Public API)

All public functions MUST include runnable `Example:` sections.

```python
# ✅ CORRECT - Runnable example
"""
Example:
    >>> from entityspine import EntityResolver
    >>> resolver = EntityResolver()
    >>> entity = resolver.resolve("AAPL")
    >>> entity is not None
    True
"""

# ❌ WRONG - Not runnable (missing imports)
"""
Example:
    >>> resolver.resolve("AAPL")
    <Entity ...>
"""
```

**Enforcement:** `pytest --doctest-modules src/`

---

## Testing Standards

### Directory Structure (REQUIRED)

Tests MUST mirror the source structure exactly:

```
src/entityspine/models/entity.py       →  tests/unit/domain/models/test_entity.py
src/entityspine/models/listing.py      →  tests/unit/domain/models/test_listing.py
src/entityspine/stores/sqlmodel_store.py →  tests/unit/stores/test_sqlmodel_store.py
```

### Test File Template (REQUIRED)

```python
"""Tests for entityspine.<module>.<submodule>."""

from __future__ import annotations

import pytest

from entityspine.<module>.<submodule> import ClassUnderTest


@pytest.fixture
def instance() -> ClassUnderTest:
    """Fresh instance for each test."""
    return ClassUnderTest()


class TestClassUnderTestBasicOperations:
    """Tests for basic operations."""

    def test_operation_succeeds(self, instance: ClassUnderTest) -> None:
        """Operation works under normal conditions."""
        result = instance.operation()
        assert result is not None

    def test_operation_with_invalid_input(
        self, instance: ClassUnderTest
    ) -> None:
        """Operation raises on invalid input."""
        with pytest.raises(ValueError):
            instance.operation(invalid="data")
```

### Naming Conventions (REQUIRED)

| Element | Pattern | Example |
|---------|---------|---------|
| Test file | `test_<module>.py` | `test_normalize.py` |
| Test class | `Test<Class><Aspect>` | `TestEntityResolverBasic` |
| Test method | `test_<what>_<condition>` | `test_resolve_ticker_returns_entity` |
| Fixture | `<descriptive_name>` | `resolver`, `sample_entity` |

### Coverage Requirements (REQUIRED: 90% minimum)

```bash
# Run with coverage
uv run pytest --cov=entityspine --cov-report=term-missing

# Must achieve 90%+ coverage
```

**Enforcement:** `pytest --cov-fail-under=90`

### Test Categories

| Category | Location | Purpose | Runs In CI |
|----------|----------|---------|------------|
| Unit | `tests/unit/` | Test single components | Every commit |
| Integration | `tests/integration/` | Test storage backends | Every commit |
| Doctest | `src/` | Verify documentation | Every commit |

---

## Package Standards

### Tier Progression (REQUIRED)

EntitySpine follows a strict tier progression:

| Tier | Backend | Dependencies | Install |
|------|---------|--------------|---------|
| 0 | JSON | None (stdlib) | `pip install entityspine` |
| 1 | SQLite | None (stdlib) | `pip install entityspine` |
| 2 | DuckDB | `duckdb` | `pip install entityspine[duckdb]` |
| 3 | PostgreSQL | `asyncpg` | `pip install entityspine[postgres]` |

### pyproject.toml Extras (REQUIRED)

```toml
[project.optional-dependencies]
duckdb = ["duckdb>=0.10"]
postgres = ["asyncpg>=0.29"]
all = ["entityspine[duckdb,postgres]"]
dev = ["pytest", "mypy", "ruff", "interrogate"]
```

### Package Exports (REQUIRED)

Public API in `__init__.py`:

```python
# entityspine/__init__.py
from entityspine.domain.entities import Entity, SimpleEntity
from entityspine.domain.resolution import EntityResolver
from entityspine.core.exceptions import (
    EntitySpineError,
    EntityNotFoundError,
    ResolutionError,
)

__all__ = [
    "EntityResolver",
    "Entity",
    "SimpleEntity",
    "EntitySpineError",
    "EntityNotFoundError",
    "ResolutionError",
]
```

---

## CI Enforcement

### Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.9.0
    hooks:
      - id: mypy
        additional_dependencies: [pydantic]
```

### CI Pipeline

```yaml
# .github/workflows/ci.yml
jobs:
  test:
    steps:
      - name: Type check
        run: uv run mypy src/
      
      - name: Lint
        run: uv run ruff check src/ tests/
      
      - name: Test
        run: uv run pytest --cov=entityspine --cov-fail-under=90
      
      - name: Docstring coverage
        run: uv run interrogate --fail-under=80 src/
      
      - name: Doctest
        run: uv run pytest --doctest-modules src/
```

### Required CI Checks

| Check | Command | Threshold |
|-------|---------|-----------|
| Type check | `mypy --strict` | 0 errors |
| Lint | `ruff check` | 0 errors |
| Format | `ruff format --check` | 0 diffs |
| Tests | `pytest` | 100% pass |
| Coverage | `pytest --cov` | ≥90% |
| Docstrings | `interrogate` | ≥80% |
| Doctests | `pytest --doctest-modules` | 100% pass |

---

## Quick Reference Card

### ✅ Always Do

- Use `from __future__ import annotations`
- Add complete type annotations
- Write Google-style docstrings with Examples
- Mirror test structure to source
- Use Tier-appropriate dependencies only
- Raise specific exceptions from `core.exceptions`

### ❌ Never Do

- Don't use `Optional[T]`, use `T | None`
- Don't use `List[T]`, use `list[T]`
- Don't import external packages in Tier 0-1
- Don't skip type annotations
- Don't use bare `except:` clauses
- Don't test implementation details

---

*Version 1.0 | January 2026*
