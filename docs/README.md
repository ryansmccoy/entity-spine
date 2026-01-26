# EntitySpine Documentation

## ⭐ Start Here (v2.2)

| Order | Document | Purpose |
|-------|----------|---------|
| 1 | **[../GUARDRAILS.md](../GUARDRAILS.md)** | Development standards (MUST READ FIRST) |
| 2 | **[MANIFESTO.md](MANIFESTO.md)** | Design philosophy (Entity≠Security≠Listing) |
| 3 | **[UNIFIED_DATA_MODEL.md](UNIFIED_DATA_MODEL.md)** | **v2.2 Schema contract** (master) |
| 4 | **[PROMPT_ENTITYSPINE.md](PROMPT_ENTITYSPINE.md)** | Complete LLM implementation guide (v2.2) |

### v2.2 Contract Documents (NEW)

| Document | Purpose |
|----------|---------|
| [design/00_UNIFIED_DATA_MODEL_V2_2.md](design/00_UNIFIED_DATA_MODEL_V2_2.md) | Master schema, claims model, tiers |
| [design/01_RESOLUTION_AND_TEMPORALITY.md](design/01_RESOLUTION_AND_TEMPORALITY.md) | Resolution algorithms, ticker reuse |
| [design/02_PYSECEDGAR_INTEGRATION_CONTRACT.md](design/02_PYSECEDGAR_INTEGRATION_CONTRACT.md) | Port/adapter interface |
| [design/03_MIGRATION_NOTES.md](design/03_MIGRATION_NOTES.md) | v2.1→v2.2 migration |
| [design/04_IMPLEMENTATION_BLUEPRINT.md](design/04_IMPLEMENTATION_BLUEPRINT.md) | **Tech stack, TDD order, code structure** |

---

## Quick Start

**For LLM Implementers**: 
1. Read `../GUARDRAILS.md` first (development standards)
2. Read `MANIFESTO.md` (design philosophy)
3. Read `design/00_UNIFIED_DATA_MODEL_V2_2.md` (v2.2 schema contract)
4. Read `PROMPT_ENTITYSPINE.md` (implementation guide)
5. After implementing, use `../LLM_VERIFICATION_CHECKLIST.md` to verify

---

## Document Structure

```
entityspine/
├── GUARDRAILS.md              ← DEVELOPMENT STANDARDS (read first)
├── LLM_VERIFICATION_CHECKLIST.md  ← POST-IMPLEMENTATION CHECKS
├── .cursorrules               ← AI ASSISTANT RULES
│
└── docs/
    ├── MANIFESTO.md           ← DESIGN PHILOSOPHY
    ├── PROMPT_ENTITYSPINE.md  ← LLM IMPLEMENTATION GUIDE
    ├── UNIFIED_DATA_MODEL.md  ← SCHEMA CONTRACT
    ├── README.md              ← You are here
    │
    ├── design/                # Current v2 design (PRIMARY REFERENCE)
    │   ├── 00_UNIFIED_DESIGN.md   # Consolidated v1+v2
    │   ├── 00_UNIFIED_DATA_MODEL_V2_2.md   # v2.2 Master schema (START HERE)
    │   ├── 01_RESOLUTION_AND_TEMPORALITY.md # Resolution algorithms
    │   ├── 02_PYSECEDGAR_INTEGRATION_CONTRACT.md # Port/adapter
    │   ├── 03_MIGRATION_NOTES.md          # v2.1→v2.2 changes
    │   ├── 01-08_*.md                     # Additional design documents
    │   └── 14-18_*.md                     # Specifications
    │
    └── archive/v1/            # Historical v1 design (CONTEXT ONLY)
        └── 00-99_*.md         # Original vision (superseded by v2.2)
```

---

## Reading Order

### If you're implementing (v2.2):

1. `../GUARDRAILS.md` - Development standards (MUST READ)
2. `MANIFESTO.md` - Design philosophy
3. `design/00_UNIFIED_DATA_MODEL_V2_2.md` - **v2.2 Master schema**
4. `design/01_RESOLUTION_AND_TEMPORALITY.md` - Resolution algorithms
5. `design/02_PYSECEDGAR_INTEGRATION_CONTRACT.md` - Integration
6. `design/03_MIGRATION_NOTES.md` - v2.1→v2.2 changes
7. `design/04_IMPLEMENTATION_BLUEPRINT.md` - **Tech stack, TDD, code structure**
8. `PROMPT_ENTITYSPINE.md` - Complete implementation guide
9. After implementation: `../LLM_VERIFICATION_CHECKLIST.md`

### If you want historical context:

1. `archive/v1/00_OVERVIEW.md` - Original vision
2. `archive/v1/09_DESIGN_QUESTIONS.md` - Unresolved questions
3. Then read v2.2 design docs (which supersede v1)

---

## Key Concepts (v2.2)

### The Inviolable Rule

```
Entity ≠ Security ≠ Listing

Ticker belongs to Listing, NEVER Entity (even in Tier 0).
```

### Resolution Returns Candidates

```python
from entityspine import EntityResolver

resolver = EntityResolver()

# v2.2: Returns ranked candidates, not single result
result = resolver.resolve("AAPL")
if result.best and result.best.score >= 0.9:
    entity = resolver.get(result.best.entity_id)
```

### Entity/Security/Listing Hierarchy

```
ENTITY (Apple Inc)           ← CIK, LEI identify this
    └── SECURITY (Common Stock)  ← ISIN, CUSIP identify this
            └── LISTING (AAPL on NASDAQ)  ← Ticker identifies this
```

### Storage Tiers

| Tier | Backend | Dependencies | Schema |
|------|---------|--------------|--------|
| 0 | JSON | None (stdlib) | SEC JSON interpreted as E/S/L |
| 1 | SQLite | None (stdlib) | **Full E/S/L/Claims tables** |
| 2 | DuckDB | Optional | Full schema + analytics |
| 3 | PostgreSQL | Optional | Full schema + conflicts + crosswalks |

---

## Existing Implementation

Partial code exists in `src/entityspine/`:

- ✅ `core/` - ULID, normalization, exceptions
- ⚠️ `domain/entities/` - Entity models (needs v2.2 update)
- ⚠️ `domain/resolution/` - Resolver (needs v2.2 return type)
- ❌ `adapters/storage/` - **NEEDS IMPLEMENTATION**

### Test Structure

Tests mirror source structure:

```
tests/
├── conftest.py                    # Shared fixtures
├── unit/
│   └── domain/models/
│       ├── test_entity.py         # v2.2 scope tests
│       ├── test_listing.py        # Ticker lives here
│       └── test_resolution.py     # ResolutionResult tests
└── integration/
    └── test_simple_api.py         # Facade tests
```

Run tests:
```bash
pytest tests/ -v
```

---

## Getting Started

```bash
cd entityspine
python -m venv .venv
.venv\Scripts\Activate.ps1  # Windows
pip install -e ".[dev]"
pytest tests/ -v
```
