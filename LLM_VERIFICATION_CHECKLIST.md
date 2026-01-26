# LLM Verification Checklist

> A systematic checklist for LLMs to verify that code changes follow EntitySpine project standards.

**Purpose**: Point an LLM to this document after making changes. The LLM should review all referenced documents and verify compliance with project guardrails.

---

## How to Use This Document

When you've completed implementing a feature, tell the LLM:

```
Review the LLM_VERIFICATION_CHECKLIST.md and verify that all my recent changes 
follow the project guardrails. Run any verification commands, check the referenced 
documents, and report any issues.
```

The LLM should then:
1. Read this checklist
2. Read referenced documents for full context
3. Run verification commands
4. Report compliance status

---

## Quick Reference: Key Documents

| Document | Location | Purpose |
|----------|----------|---------|
| **GUARDRAILS.md** | `./GUARDRAILS.md` | Primary enforcement rules (MUST READ) |
| **MANIFESTO.md** | `./docs/MANIFESTO.md` | Design philosophy principles |
| **UNIFIED_DATA_MODEL.md** | `./docs/UNIFIED_DATA_MODEL.md` | Schema contract |
| **Unified Design** | `./docs/design/00_UNIFIED_DESIGN.md` | Core architecture reference |
| **.cursorrules** | `./.cursorrules` | AI assistant coding rules |

---

## Verification Checklist

### 1. ✅ Tests Pass

**Priority: CRITICAL**

Run the test suite and confirm all tests pass:

```bash
# Run all tests
uv run pytest tests/ --tb=short -q

# Expected: All tests pass (0 failures)
```

**If tests fail:**
- Fix the failing tests before proceeding
- Do NOT skip tests or mark them as xfail without explicit approval

---

### 2. ✅ Test-Driven Development (TDD) Compliance

**Priority: HIGH**

Reference: `GUARDRAILS.md` → Testing Standards

Verify TDD was followed:

- [ ] Tests were written BEFORE implementation (or comprehensive tests exist)
- [ ] Test file mirrors source structure: `src/entityspine/x/y.py` → `tests/unit/x/test_y.py`
- [ ] Test naming follows pattern: `test_<what>_<condition>`
- [ ] Test classes follow pattern: `Test<Class><Aspect>`
- [ ] Tests cover: happy path, edge cases, error conditions

**Check test structure:**
```bash
# List test files to verify they mirror source
ls -la tests/unit/
```

---

### 3. ✅ Type Annotations

**Priority: HIGH**

Reference: `GUARDRAILS.md` → Code Standards → Type Annotations

Run type checking:

```bash
uv run mypy src/
```

**Requirements:**
- [ ] All functions have complete type annotations
- [ ] Return types are specified (even `-> None`)
- [ ] Use modern Python syntax: `list[str]` not `List[str]`
- [ ] Use `X | None` not `Optional[X]`

---

### 4. ✅ Tier Dependency Compliance

**Priority: CRITICAL**

Reference: `GUARDRAILS.md` → Code Standards → Zero Dependencies for Tier 0-1

**Tier 0-1 (JSON, SQLite) MUST use ONLY stdlib:**

```bash
# Check for forbidden imports in core and tier 0-1 files
grep -r "^import requests\|^import httpx\|^import aiohttp" src/entityspine/core/
grep -r "^import requests\|^import httpx\|^import aiohttp" src/entityspine/adapters/storage/json_store.py
grep -r "^import requests\|^import httpx\|^import aiohttp" src/entityspine/adapters/storage/sqlite_store.py

# Should return nothing
```

**Allowed stdlib imports for Tier 0-1:**
- `json`, `sqlite3`, `datetime`, `urllib.request`, `dataclasses`
- `typing`, `collections.abc`, `pathlib`, `os`, `re`

---

### 5. ✅ Docstring Coverage

**Priority: HIGH**

Reference: `GUARDRAILS.md` → Documentation Standards

Run docstring coverage check:

```bash
uv run interrogate --fail-under=80 src/entityspine/
```

**Requirements:**
- [ ] All public modules have docstrings
- [ ] All public classes have docstrings
- [ ] All public functions have docstrings
- [ ] Docstrings follow Google style format

---

### 6. ✅ Doctest Examples

**Priority: MEDIUM**

Reference: `GUARDRAILS.md` → Doctest Examples

Run doctests:

```bash
uv run pytest --doctest-modules src/entityspine/
```

**Requirements:**
- [ ] All public API functions have `Example:` sections
- [ ] Examples are runnable (include imports)
- [ ] Examples produce deterministic output

---

### 7. ✅ Code Style (Lint & Format)

**Priority: MEDIUM**

Run linting:

```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
```

**Requirements:**
- [ ] No lint errors
- [ ] Code is properly formatted
- [ ] Imports are organized (stdlib → third-party → local)

---

### 8. ✅ Protocol Compliance

**Priority: HIGH**

Reference: `.cursorrules` → Protocol file template

If implementing a storage backend, verify:

- [ ] Class implements `EntityStore` protocol methods
- [ ] All protocol methods are implemented
- [ ] Method signatures match protocol exactly
- [ ] Uses `initialize()` / `close()` lifecycle methods

**Check protocol:**
```python
# The implementation should satisfy the protocol
from entityspine.adapters.storage.protocol import EntityStore

def check(store: EntityStore) -> None:
    """Type checker verifies protocol compliance."""
    pass

check(YourStorageClass())  # Must not raise type error
```

---

### 9. ✅ Exception Handling

**Priority: MEDIUM**

Reference: `GUARDRAILS.md` → Never use bare `except:`

Verify exception handling:

- [ ] All exceptions are from `entityspine.core.exceptions`
- [ ] No bare `except:` clauses
- [ ] Specific exception types are caught
- [ ] Error messages are descriptive

**Check for bare excepts:**
```bash
grep -r "except:" src/entityspine/ | grep -v "except.*:"
# Should return nothing
```

---

### 10. ✅ Test Coverage

**Priority: HIGH**

Reference: `GUARDRAILS.md` → Coverage Requirements

Run coverage:

```bash
uv run pytest --cov=entityspine --cov-report=term-missing --cov-fail-under=90
```

**Requirements:**
- [ ] Overall coverage ≥ 90%
- [ ] No critical paths without tests
- [ ] Edge cases are covered

---

## Post-Verification Summary Template

After running all checks, provide a summary:

```markdown
## Verification Summary

| Check | Status | Notes |
|-------|--------|-------|
| Tests Pass | ✅/❌ | |
| TDD Compliance | ✅/❌ | |
| Type Annotations | ✅/❌ | |
| Tier Dependencies | ✅/❌ | |
| Docstring Coverage | ✅/❌ | X% |
| Doctest Examples | ✅/❌ | |
| Code Style | ✅/❌ | |
| Protocol Compliance | ✅/❌ | |
| Exception Handling | ✅/❌ | |
| Test Coverage | ✅/❌ | X% |

### Issues Found
1. [Issue description]
2. [Issue description]

### Recommendations
1. [Recommendation]
2. [Recommendation]
```

---

## Common Issues & Fixes

### Issue: Missing type annotation

```python
# ❌ Wrong
def resolve(self, query):
    ...

# ✅ Fix
def resolve(self, query: str) -> Entity | None:
    ...
```

### Issue: Legacy typing syntax

```python
# ❌ Wrong
from typing import Optional, List
def search(self, q: str) -> Optional[List[Entity]]:
    ...

# ✅ Fix
def search(self, q: str) -> list[Entity] | None:
    ...
```

### Issue: External import in Tier 0-1

```python
# ❌ Wrong (in sqlite_store.py)
import requests

# ✅ Fix
from urllib.request import urlopen
```

### Issue: Bare except clause

```python
# ❌ Wrong
try:
    ...
except:
    pass

# ✅ Fix
try:
    ...
except EntityNotFoundError:
    return None
except Exception as e:
    raise StorageError(f"Unexpected error: {e}") from e
```

---

*Version 1.0 | January 2026*
