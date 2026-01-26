# Contributing to EntitySpine

Thank you for your interest in contributing to EntitySpine! This document provides guidelines and instructions for contributing.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Style Guide](#style-guide)
- [Architecture Principles](#architecture-principles)

## Code of Conduct

This project follows a standard Code of Conduct. Please be respectful and constructive in all interactions.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/entity-spine.git
   cd entity-spine
   ```
3. **Add the upstream remote**:
   ```bash
   git remote add upstream https://github.com/ryansmccoy/entity-spine.git
   ```

## Development Setup

### Prerequisites

- Python 3.11 or higher
- Git

### Setup Steps

```bash
# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Activate (Unix/macOS)
source .venv/bin/activate

# Install in development mode with all extras
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

### Verify Setup

```bash
# Run tests
pytest

# Run linting
ruff check src tests

# Run type checking
mypy src/entityspine
```

## Making Changes

### Branch Naming

Use descriptive branch names:

- `feature/add-duckdb-store` — New features
- `fix/sqlite-connection-leak` — Bug fixes
- `docs/update-readme` — Documentation changes
- `refactor/simplify-mappers` — Code refactoring

### Creating a Branch

```bash
# Sync with upstream
git fetch upstream
git checkout main
git merge upstream/main

# Create feature branch
git checkout -b feature/your-feature-name
```

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_sqlite_store.py

# Run specific test
pytest tests/test_sqlite_store.py::test_save_entity

# Run with coverage
pytest --cov=entityspine --cov-report=html

# View coverage report
open htmlcov/index.html  # macOS
start htmlcov/index.html  # Windows
```

### Writing Tests

- Place tests in the `tests/` directory
- Name test files `test_*.py`
- Name test functions `test_*`
- Use `pytest` fixtures for setup/teardown
- Aim for 80%+ coverage on new code

Example test:

```python
"""Tests for entity operations."""
import pytest
from entityspine import Entity, EntityType, SqliteStore


@pytest.fixture
def store():
    """Create an in-memory store for testing."""
    s = SqliteStore(":memory:")
    s.initialize()
    yield s


def test_save_and_retrieve_entity(store):
    """Test basic entity CRUD."""
    entity = Entity(
        primary_name="Test Corp",
        entity_type=EntityType.ORGANIZATION,
    )
    store.save_entity(entity)
    
    retrieved = store.get_entity(entity.entity_id)
    
    assert retrieved is not None
    assert retrieved.primary_name == "Test Corp"
```

## Submitting Changes

### Commit Messages

Follow conventional commit format:

```
type(scope): short description

Longer description if needed.

Closes #123
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting (no code change)
- `refactor`: Code restructuring
- `test`: Adding tests
- `chore`: Maintenance tasks

Examples:
```
feat(stores): add DuckDB storage backend
fix(sqlite): prevent connection leak on error
docs(readme): add architecture diagram
```

### Pull Request Process

1. **Update your branch**:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Run all checks**:
   ```bash
   pytest
   ruff check src tests
   mypy src/entityspine
   ```

3. **Push your branch**:
   ```bash
   git push origin feature/your-feature-name
   ```

4. **Create Pull Request** on GitHub with:
   - Clear title following commit message format
   - Description of what changed and why
   - Link to any related issues

5. **Address review feedback** by pushing additional commits

## Style Guide

### Code Style

EntitySpine uses **Ruff** for linting and formatting.

```bash
# Check style
ruff check src tests

# Auto-fix issues
ruff check src tests --fix

# Format code
ruff format src tests
```

### Type Hints

All public APIs must have type hints:

```python
# Good
def get_entity(self, entity_id: str) -> Entity | None:
    """Get entity by ID."""
    ...

# Bad (missing types)
def get_entity(self, entity_id):
    ...
```

### Docstrings

Use Google-style docstrings:

```python
def save_entity(self, entity: Entity) -> None:
    """Save an entity to the store.
    
    Args:
        entity: The entity to save. If an entity with the same
            entity_id exists, it will be updated.
    
    Raises:
        ValidationError: If the entity fails validation.
    
    Example:
        >>> store = SqliteStore(":memory:")
        >>> store.initialize()
        >>> entity = Entity(primary_name="Test")
        >>> store.save_entity(entity)
    """
```

## Architecture Principles

When contributing, please follow these core principles:

### 1. Domain is Canonical

The `entityspine.domain` package uses only stdlib dataclasses. All other layers adapt to domain models.

```python
# Domain models are the source of truth
from entityspine.domain import Entity  # stdlib dataclass

# Adapters convert to/from domain
from entityspine.adapters.pydantic import EntityModel  # Optional wrapper
```

### 2. Zero Core Dependencies

Tier 0-1 storage backends must work with Python stdlib only. Optional features go in extras.

```toml
# Core has no dependencies
[project]
dependencies = []

# Optional features are extras
[project.optional-dependencies]
pydantic = ["pydantic>=2.0"]
duckdb = ["duckdb>=0.10"]
```

### 3. Tier Honesty

Storage backends must not silently ignore features they don't support. Use warnings.

```python
def resolve(self, query: str, as_of: date | None = None) -> ResolveResult:
    """Resolve entity."""
    if as_of is not None:
        return ResolveResult(
            entity=self._basic_resolve(query),
            as_of_honored=False,
            warnings=["as_of requires Tier 2+"],
        )
```

### 4. Evidence Trail

All data must have provenance through source tracking:

```python
entity = Entity(
    primary_name="Apple Inc.",
    source_system="sec-edgar",     # Where it came from
    source_id="0000320193",        # External identifier
    source_timestamp=utc_now(),    # When extracted
)
```

---

## Questions?

- Open an [issue](https://github.com/ryansmccoy/entity-spine/issues) for bugs or features
- Start a [discussion](https://github.com/ryansmccoy/entity-spine/discussions) for questions

Thank you for contributing! 🎉
