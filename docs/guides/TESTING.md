# EntitySpine Testing Guide

**Testing standards and practices for EntitySpine**

---

## Test Structure

```
entityspine/tests/
├── __init__.py
├── conftest.py              # Shared fixtures
├── unit/                    # Unit tests
│   ├── domain/              # Domain model tests
│   ├── core/                # Core utility tests
│   ├── stores/              # Storage backend tests
│   └── services/            # Service layer tests
├── integration/             # Integration tests
│   ├── test_feedspine_*.py  # FeedSpine integration
│   └── test_sec_*.py        # SEC data integration
├── api/                     # API endpoint tests
└── e2e/                     # End-to-end tests
```

---

## Running Tests

```bash
# Run all tests (excluding API tests requiring server)
pytest tests/ --ignore=tests/api -q

# Run with coverage
pytest tests/ --cov=entityspine --cov-report=html

# Run specific test file
pytest tests/unit/domain/test_entity.py -v

# Run tests matching pattern
pytest tests/ -k "test_resolve" -v

# Run doctests
pytest --doctest-modules src/entityspine/
```

---

## Fixtures (conftest.py)

### Common Fixtures

```python
import pytest
from entityspine import EntityManager, Entity

@pytest.fixture
def memory_manager():
    """In-memory EntityManager for fast tests."""
    return EntityManager(storage="memory")

@pytest.fixture
def sample_entity():
    """Standard test entity."""
    return Entity(
        id="ent_test123",
        primary_name="Test Corp",
        entity_type=EntityType.CORPORATION,
        source_system="test",
        source_id="TEST001"
    )

@pytest.fixture
def populated_manager(memory_manager, sample_entity):
    """Manager with sample data."""
    memory_manager.save(sample_entity)
    return memory_manager
```

### Database Fixtures

```python
@pytest.fixture
def sqlite_manager(tmp_path):
    """SQLite manager for persistence tests."""
    db_path = tmp_path / "test.db"
    manager = EntityManager(storage=f"sqlite:///{db_path}")
    yield manager
    manager.close()
```

---

## Test Patterns

### Domain Model Tests

```python
class TestEntity:
    """Tests for Entity domain model."""

    def test_create_entity_with_valid_data(self):
        """Entity creation with valid data succeeds."""
        entity = Entity(
            primary_name="Apple Inc.",
            source_system="sec",
            source_id="0000320193"
        )
        assert entity.primary_name == "Apple Inc."
        assert entity.id is not None

    def test_create_entity_without_name_raises(self):
        """Entity creation without name raises ValueError."""
        with pytest.raises(ValueError, match="primary_name"):
            Entity(primary_name="", source_system="sec", source_id="123")
```

### Resolution Tests

```python
class TestResolution:
    """Tests for entity resolution."""

    def test_resolve_by_ticker_exact_match(self, populated_manager):
        """Exact ticker match returns correct entity."""
        result = populated_manager.resolve("AAPL")
        
        assert result.status == ResolutionStatus.FOUND
        assert result.entity.primary_name == "Apple Inc."
        assert result.confidence > 0.9

    def test_resolve_unknown_returns_not_found(self, populated_manager):
        """Unknown identifier returns NOT_FOUND status."""
        result = populated_manager.resolve("UNKNOWN123")
        
        assert result.status == ResolutionStatus.NOT_FOUND
        assert result.entity is None
```

### Storage Tests

```python
class TestSQLiteStore:
    """Tests for SQLite storage backend."""

    def test_save_and_retrieve_entity(self, sqlite_manager, sample_entity):
        """Saved entity can be retrieved by ID."""
        sqlite_manager.save(sample_entity)
        
        retrieved = sqlite_manager.get(sample_entity.id)
        
        assert retrieved == sample_entity

    def test_persistence_across_sessions(self, tmp_path, sample_entity):
        """Data persists across manager instances."""
        db_path = tmp_path / "persist.db"
        
        # Session 1: Save
        manager1 = EntityManager(storage=f"sqlite:///{db_path}")
        manager1.save(sample_entity)
        manager1.close()
        
        # Session 2: Retrieve
        manager2 = EntityManager(storage=f"sqlite:///{db_path}")
        retrieved = manager2.get(sample_entity.id)
        
        assert retrieved.primary_name == sample_entity.primary_name
```

---

## Parametrized Tests

```python
@pytest.mark.parametrize("identifier,expected_scheme", [
    ("0000320193", IdentifierScheme.CIK),
    ("AAPL", IdentifierScheme.TICKER),
    ("037833100", IdentifierScheme.CUSIP),
    ("US0378331005", IdentifierScheme.ISIN),
])
def test_identify_scheme(identifier, expected_scheme):
    """Identifier scheme detection."""
    result = classify_identifier(identifier)
    assert result == expected_scheme
```

---

## Markers

```python
# In pytest.ini or pyproject.toml
[tool.pytest.ini_options]
markers = [
    "slow: marks tests as slow",
    "integration: integration tests",
    "api: tests requiring API server",
    "database: tests requiring database",
]
```

Usage:
```bash
# Skip slow tests
pytest -m "not slow"

# Only integration tests
pytest -m integration
```

---

## Coverage Requirements

- **Minimum**: 80% overall
- **Domain models**: 95%+
- **Storage backends**: 90%+
- **API endpoints**: 85%+

```bash
# Check coverage
pytest --cov=entityspine --cov-fail-under=80
```

---

## Test Checklist

For each new feature:

- [ ] Unit tests for core logic
- [ ] Edge cases (empty input, None, invalid types)
- [ ] Error conditions (all exceptions documented)
- [ ] Integration tests if cross-component
- [ ] Doctest examples in docstrings
- [ ] Performance test if latency-critical

---

## Continuous Integration

Tests run on every push:

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -e ".[dev]"
      - run: pytest tests/ --ignore=tests/api --cov=entityspine
```
