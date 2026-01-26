# EntitySpine - Comprehensive Development Prompt (v2.2)

**For: Claude Opus 4.5 (Extended Thinking Mode)**

---

## ⚠️ CRITICAL: Read These First

Before implementing ANYTHING, read these documents in order:

### Development Standards

| Order | Document | Location | Why |
|-------|----------|----------|-----|
| **1** | GUARDRAILS.md | `entityspine/GUARDRAILS.md` | Non-negotiable code standards |
| **2** | MANIFESTO.md | `entityspine/docs/MANIFESTO.md` | Design philosophy |
| **3** | .cursorrules | `entityspine/.cursorrules` | AI coding patterns |

### v2.2 Contract Documents (START HERE)

| Order | Document | Location | Why |
|-------|----------|----------|-----|
| **4** | UNIFIED_DATA_MODEL_V2_2.md | `docs/design/00_UNIFIED_DATA_MODEL_V2_2.md` | **Master schema contract** |
| **5** | RESOLUTION_AND_TEMPORALITY.md | `docs/design/01_RESOLUTION_AND_TEMPORALITY.md` | Resolution algorithms |
| **6** | PYSECEDGAR_INTEGRATION_CONTRACT.md | `docs/design/02_PYSECEDGAR_INTEGRATION_CONTRACT.md` | Port/adapter interface |
| **7** | MIGRATION_NOTES.md | `docs/design/03_MIGRATION_NOTES.md` | v2.1→v2.2 changes |
| **8** | IMPLEMENTATION_BLUEPRINT.md | `docs/design/04_IMPLEMENTATION_BLUEPRINT.md` | **Tech stack, TDD order, code structure** |

**After implementing**, verify with:

| Document | Location | Why |
|----------|----------|-----|
| **LLM_VERIFICATION_CHECKLIST.md** | `entityspine/LLM_VERIFICATION_CHECKLIST.md` | Verify compliance |

---

## ⚡ IMPLEMENTATION ORDER (TDD-First)

**The Golden Rule**: Test → Implement → Refactor → Repeat

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         IMPLEMENTATION PHASES                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Phase 0: Project Setup                                                     │
│     └── pyproject.toml (ZERO core deps), directory structure               │
│                                                                             │
│  Phase 1: Domain Models (dataclasses, no Pydantic)                          │
│     └── Entity, Security, Listing, Claim dataclasses                       │
│     └── Tests: test_entity.py, test_security.py, etc.                      │
│                                                                             │
│  Phase 2: Protocols & Interfaces                                            │
│     └── EntityStoreProtocol, EntityResolverProtocol                        │
│     └── ResolutionResult, ResolutionCandidate                              │
│                                                                             │
│  Phase 3: Storage Layer (sqlite3 stdlib, no SQLAlchemy)                     │
│     └── SQLiteStore implements EntityStoreProtocol                         │
│     └── JSONStore (read-only SEC JSON)                                     │
│                                                                             │
│  Phase 4: Resolution Service                                                │
│     └── EntityResolver (returns ResolutionResult)                          │
│                                                                             │
│  Phase 5: Simple Facade API                                                 │
│     └── `resolver = EntityResolver()` just works                           │
│     └── Auto-downloads SEC data, creates SQLite cache                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Technology Stack (Tier 0-1)

| Component | Use | Why |
|-----------|-----|-----|
| `dataclasses` | Domain models | Zero deps, stdlib |
| `sqlite3` | Storage | Zero deps, stdlib |
| Custom ULID | IDs | No external package |
| `typing.Protocol` | Interfaces | Structural subtyping |

**See `04_IMPLEMENTATION_BLUEPRINT.md` for full details.**

---

## Mission

You are the lead architect and implementer for **entityspine**, a production-quality Python package for entity resolution in financial data.

### v2.2 Key Changes (from v2.1)

| Change | v2.1 (Wrong) | v2.2 (Correct) |
|--------|--------------|----------------|
| **Ticker scope** | On Entity | On Listing |
| **Resolution return** | `Entity \| None` | `ResolutionResult` with candidates |
| **Identifiers** | Facts | Claims with provenance |
| **Merges** | Delete old | Redirect chain (never delete) |
| **Ambiguity** | Pick best guess | Return ranked candidates |
| **Tier 1 schema** | Flat entity table | Entity/Security/Listing tables |

---

## The Inviolable Rule

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    ENTITY ≠ SECURITY ≠ LISTING                              │
│                                                                             │
│  This applies to ALL tiers, including Tier 0 and Tier 1.                    │
│  Convenience views may flatten, but canonical truth never conflates them.   │
└─────────────────────────────────────────────────────────────────────────────┘
```

| Object | What It Represents | Example Identifiers | Example |
|--------|-------------------|---------------------|---------|
| **Entity** | Legal organization | CIK, LEI, EIN, DUNS | Apple Inc. |
| **Security** | Financial instrument | ISIN, CUSIP, FIGI, SEDOL | AAPL Common Stock |
| **Listing** | Where/when security trades | Ticker+MIC+ValidFrom | AAPL on XNAS since 1980 |

---

## Document Reading Order

### Phase 0: Standards (MUST READ FIRST)

| Order | Document | Key Points |
|-------|----------|------------|
| 0a | `GUARDRAILS.md` | Type hints, docstrings, testing |
| 0b | `MANIFESTO.md` | Entity≠Security≠Listing, tier philosophy |
| 0c | `.cursorrules` | File templates, naming patterns |

### Phase 1: v2.2 Contract Documents

| Order | Document | Key Points |
|-------|----------|------------|
| 1a | `00_UNIFIED_DATA_MODEL_V2_2.md` | **Master schema** - corrected tier strategy, claims model |
| 1b | `01_RESOLUTION_AND_TEMPORALITY.md` | Ticker reuse, `as_of` semantics, ranking |
| 1c | `02_PYSECEDGAR_INTEGRATION_CONTRACT.md` | Port interface, what py-sec-edgar stores |
| 1d | `03_MIGRATION_NOTES.md` | Breaking changes from v2.1 |

### Phase 2: v2 Design Documents (Additional Context)

Read `docs/design/` for additional context:

| Document | Key Points |
|----------|------------|
| `17_LIGHTWEIGHT_MODULAR_ARCHITECTURE.md` | Zero-to-hero tier progression |
| `18_IMPLEMENTATION_BLUEPRINT.md` | Code structure |
| `02_RESOLUTION_AND_MERGE_WORKFLOWS.md` | Merge workflow details |
| `03_VENDOR_CROSSWALK_AND_CONFLICTS.md` | Multi-vendor handling |
| `04_MENTIONS_PROVISIONAL.md` | Provisional entity workflow |

### Phase 3: Historical Context (Optional)

Optionally read `docs/archive/v1/` for historical context, but **v2.2 supersedes all v1 documents**.

---

## Core Design Principles (v2.2)

### 1. Claims, Not Facts

Every identifier is a **claim** with provenance:

```python
# ❌ WRONG (v2.1): Treating identifier as fact
entity.lei = "HWUPKR0MPOU8FGXBT394"

# ✅ CORRECT (v2.2): Treating identifier as claim
claim = IdentifierClaim(
    entity_id="01ARZ3...",
    scheme="lei",
    value="HWUPKR0MPOU8FGXBT394",
    source_system="gleif",
    confidence=1.0,
    captured_at=datetime.now(),
)
```

### 2. Return Ambiguity, Never Guess

Resolution returns **ranked candidates**:

```python
# ❌ WRONG (v2.1): Single result
def resolve(query: str) -> Entity | None: ...

# ✅ CORRECT (v2.2): Ranked candidates
def resolve(query: str, as_of: date | None = None) -> ResolutionResult: ...

@dataclass
class ResolutionResult:
    candidates: list[ResolutionCandidate]  # Ranked by score
    is_ambiguous: bool
    needs_review: bool
```

### 3. Merges Create Redirects, Never Delete

Old IDs stay resolvable forever:

```python
# Entity A merged into Entity B
entity, chain = resolver.get_canonical("A")
# Returns: (Entity B, ["A", "B"])  -- redirect chain included
```

### 4. Scope-Correct Tier 1 Schema

Even Tier 1 (SQLite) must have proper Entity/Security/Listing tables:

```sql
-- Tier 1 SQLite schema (v2.2 correct)
CREATE TABLE entities (...);           -- NO ticker column
CREATE TABLE securities (...);         -- NEW in v2.2
CREATE TABLE listings (...);           -- ticker lives HERE
CREATE TABLE identifier_claims (...);  -- replaces "identifiers"
```

### 5. Derived Views ≠ Canonical Truth

Convenience views are explicitly marked as derived:

```python
@dataclass
class EntityWithPrimaryListing:
    """DERIVED VIEW: Entity + its primary listing for convenience."""
    entity_id: str
    primary_name: str
    primary_ticker: str | None  # From listing, NOT entity
    as_of: date  # When this view was computed
```

---

## Storage Tiers (v2.2)

| Tier | Backend | Dependencies | Schema |
|------|---------|--------------|--------|
| 0 | JSON | None (stdlib) | SEC JSON → interpreted as E/S/L |
| 1 | SQLite | None (stdlib) | **Full E/S/L/Claims tables** |
| 2 | DuckDB | Optional | Full schema + analytics views |
| 3 | PostgreSQL | Optional | Full schema + conflicts + crosswalks |

### Tier 0: JSON (Zero Dependencies)

SEC provides flat `company_tickers.json`. We **interpret** it correctly:

```python
# SEC provides:
{"0": {"cik_str": "320193", "ticker": "AAPL", "title": "Apple Inc."}}

# We interpret as:
# - Entity: CIK 0000320193, name "Apple Inc."
# - Listing: ticker "AAPL" (derived, not stored on entity)

@dataclass
class Tier0Entity:
    """Read-only entity from SEC JSON."""
    cik: str              # Entity identifier
    name: str             # Entity name
    
    # DERIVED convenience (clearly marked)
    primary_ticker: str | None = None  # From implied listing
    
    source: str = "sec_company_tickers"
```

### Tier 1: SQLite (Zero Dependencies, Proper Schema)

```sql
-- v2.2 REQUIRED schema for Tier 1
CREATE TABLE entities (
    entity_id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL DEFAULT 'COMPANY',
    status TEXT NOT NULL DEFAULT 'active',
    primary_name TEXT NOT NULL,
    -- NO ticker column
    -- NO exchange column
    merged_into_id TEXT,
    merged_at TEXT,
    source_system TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE securities (
    security_id TEXT PRIMARY KEY,
    issuer_entity_id TEXT NOT NULL REFERENCES entities(entity_id),
    security_type TEXT NOT NULL,
    name TEXT NOT NULL,
    source_system TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE listings (
    listing_id TEXT PRIMARY KEY,
    security_id TEXT NOT NULL REFERENCES securities(security_id),
    ticker TEXT NOT NULL,
    mic TEXT,
    is_primary INTEGER NOT NULL DEFAULT 1,
    valid_from TEXT NOT NULL,
    valid_to TEXT,
    source_system TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(ticker, mic, valid_from)
);

CREATE TABLE identifier_claims (
    claim_id TEXT PRIMARY KEY,
    entity_id TEXT,
    security_id TEXT,
    listing_id TEXT,
    scheme TEXT NOT NULL,
    value TEXT NOT NULL,
    source_system TEXT NOT NULL,
    confidence REAL NOT NULL DEFAULT 1.0,
    captured_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active'
);
```

---

## Resolution API (v2.2)

### Protocol Definition

```python
from typing import Protocol
from dataclasses import dataclass
from datetime import date

@dataclass(frozen=True)
class ResolutionCandidate:
    entity_id: str
    score: float              # 0.0 to 1.0
    match_type: str           # 'exact', 'alias', 'fuzzy', 'ticker'
    matched_value: str
    matched_scheme: str | None = None
    redirect_chain: list[str] | None = None
    listing_id: str | None = None
    security_id: str | None = None

@dataclass
class ResolutionResult:
    candidates: list[ResolutionCandidate]
    query: str
    as_of: date
    is_ambiguous: bool = False
    needs_review: bool = False
    created_provisional: bool = False
    
    @property
    def best(self) -> ResolutionCandidate | None:
        return self.candidates[0] if self.candidates else None

class EntityResolverProtocol(Protocol):
    def resolve(
        self, 
        query: str, 
        as_of: date | None = None,
        limit: int = 10
    ) -> ResolutionResult:
        """Resolve any identifier to ranked entity candidates."""
        ...
    
    def resolve_cik(self, cik: str) -> ResolutionResult:
        """Resolve SEC CIK to entity candidates."""
        ...
    
    def resolve_ticker(
        self, 
        ticker: str, 
        mic: str | None = None,
        as_of: date | None = None
    ) -> ResolutionResult:
        """Resolve ticker (listing-scoped) to entity."""
        ...
    
    def get(self, entity_id: str) -> Entity | None:
        """Get entity by ID, follows merge redirects."""
        ...
    
    def get_canonical(self, entity_id: str) -> tuple[Entity | None, list[str]]:
        """Get entity and redirect chain."""
        ...
```

### Resolution Paths

```
CIK Resolution (direct to entity):
  CIK → identifier_claims → entity_id

Ticker Resolution (traverses full hierarchy):
  Ticker → listings → security_id → securities → issuer_entity_id
  
Name Resolution (fuzzy match):
  Name → aliases (similarity) → entity_id
```

---

## Implementation Phases (v2.2)

### Phase 1: Foundation (Scope-Correct Tier 0 + Tier 1)

**Goal**: Scope-correct resolution with JSON and SQLite.

**Tasks**:
1. Implement `Tier0Entity` (interprets SEC JSON correctly)
2. Implement `EntityStoreProtocol`
3. Implement `JSONStore` (read-only, from SEC JSON)
4. Implement `SQLiteStore` with **v2.2 schema** (E/S/L/Claims tables)
5. Implement `EntityResolver` returning `ResolutionResult`
6. Tests for all resolution paths

**Success Criteria**:
```python
# Tier 0: JSON
resolver = EntityResolver()
result = resolver.resolve("AAPL")
assert isinstance(result, ResolutionResult)
assert result.best.score >= 0.9
entity = resolver.get(result.best.entity_id)
assert entity.primary_name == "Apple Inc."
assert not hasattr(entity, 'ticker')  # NO ticker on entity

# Tier 1: SQLite with proper schema
resolver = EntityResolver(db_path="entities.db")
result = resolver.resolve_ticker("AAPL", as_of=date(2024, 1, 1))
assert result.best.listing_id is not None  # Ticker resolved via listing
```

### Phase 2: Claims & Provenance

**Goal**: Identifier claims with source tracking.

**Tasks**:
1. Implement `IdentifierClaim` dataclass
2. Implement claims table operations
3. Add `source_system`, `confidence`, `captured_at` to all claims
4. Implement conflict detection
5. Tests for claim lifecycle

### Phase 3: Merge & Redirect

**Goal**: Merges that preserve old IDs.

**Tasks**:
1. Add `merged_into_id`, `merged_at` to entities
2. Implement `follow_redirects()` in resolver
3. Implement `get_canonical()` returning redirect chain
4. Add `merge_events` table for audit
5. Tests for merge scenarios

### Phase 4: Provisional Entities

**Goal**: Create entities from unresolved mentions.

**Tasks**:
1. Implement `create_provisional()` method
2. Add `status='provisional'` support
3. Implement `propose_merge()` (doesn't auto-execute)
4. Evidence pointers (evidence_uri, evidence_text)
5. Tests for provisional workflow

### Phase 5: Vendor Crosswalks (Tier 3)

**Goal**: Multi-vendor ID mapping.

**Tasks**:
1. Add `scheme_registry` table
2. Add `vendor_crosswalks` table
3. Support Bloomberg BBGID, FactSet, Reuters RIC
4. Implement conflict handling
5. PostgreSQL implementation

### Phase 6: Integration

**Goal**: py-sec-edgar integration.

**Tasks**:
1. Implement `EntityResolverPort` (py-sec-edgar interface)
2. Implement `EntitySpineAdapter` 
3. Document integration contract
4. Integration tests

---

## Key Requirements (v2.2 Specific)

### 1. Scope Enforcement

```python
# Entity NEVER has ticker
@dataclass
class Entity:
    entity_id: str
    primary_name: str
    # NO ticker
    # NO exchange

# Listing has ticker
@dataclass
class Listing:
    listing_id: str
    security_id: str
    ticker: str
    mic: str
    valid_from: date
    valid_to: date | None
```

### 2. Claims Required for All Identifiers

```python
# Every identifier lookup goes through claims
def resolve_cik(cik: str) -> ResolutionResult:
    claims = self._store.get_claims(scheme='cik', value=cik)
    # NOT: SELECT * FROM entities WHERE cik = ?
```

### 3. Resolution Returns Candidates

```python
# NEVER return single result
def resolve(query: str) -> ResolutionResult:
    # Find candidates
    # Score candidates  
    # Return ranked list (even if only one)
```

### 4. Follow Redirects on Get

```python
def get(entity_id: str) -> Entity | None:
    entity = self._load(entity_id)
    if entity and entity.merged_into_id:
        return self.get(entity.merged_into_id)  # Follow redirect
    return entity
```

### 5. Point-in-Time Resolution

```python
def resolve_ticker(ticker: str, as_of: date | None = None) -> ResolutionResult:
    as_of = as_of or date.today()
    listings = self._store.get_listings(
        ticker=ticker,
        valid_at=as_of  # Only active listings at as_of
    )
```

---

## Quality Gates

- **Coverage**: 90%+ for core, 80%+ overall
- **Type Checking**: `mypy --strict` passes
- **Linting**: `ruff check` clean
- **Formatting**: `ruff format` applied
- **Documentation**: All public APIs have Google-style docstrings

---

## Testing Strategy

### Test Structure

```
tests/
├── conftest.py
├── unit/
│   ├── core/
│   │   ├── test_ulid.py
│   │   └── test_normalize.py
│   ├── domain/
│   │   ├── test_entity.py
│   │   ├── test_security.py
│   │   ├── test_listing.py
│   │   └── test_claims.py
│   └── resolution/
│       ├── test_resolver.py
│       └── test_ranking.py
├── adapters/
│   └── storage/
│       ├── test_json_store.py
│       ├── test_sqlite_store.py
│       └── test_protocol_compliance.py
└── integration/
    ├── test_resolution_flow.py
    ├── test_merge_redirect.py
    └── test_pysecedgar_port.py
```

### Critical Test Cases (v2.2)

```python
def test_entity_has_no_ticker_attribute():
    """Entity must NOT have ticker attribute (scope violation)."""
    entity = Entity(entity_id="01...", primary_name="Apple Inc.")
    assert not hasattr(entity, 'ticker')

def test_resolve_returns_candidates_list():
    """resolve() must return ResolutionResult with candidates list."""
    result = resolver.resolve("AAPL")
    assert isinstance(result, ResolutionResult)
    assert isinstance(result.candidates, list)

def test_ticker_resolves_via_listing():
    """Ticker resolution must traverse listing→security→entity."""
    result = resolver.resolve_ticker("AAPL")
    assert result.best.listing_id is not None
    assert result.best.security_id is not None
    assert result.best.entity_id is not None

def test_merged_entity_returns_canonical():
    """get() on merged entity returns canonical target."""
    # Entity A merged into B
    entity = resolver.get("A")
    assert entity.entity_id == "B"

def test_get_canonical_returns_chain():
    """get_canonical() includes redirect chain."""
    entity, chain = resolver.get_canonical("A")
    assert chain == ["A", "B"]

def test_ticker_reuse_respects_as_of():
    """Ticker resolution respects point-in-time."""
    # AAPL was Company X until 1995, Company Y after
    result_1990 = resolver.resolve_ticker("AAPL", as_of=date(1990, 1, 1))
    result_2024 = resolver.resolve_ticker("AAPL", as_of=date(2024, 1, 1))
    assert result_1990.best.entity_id != result_2024.best.entity_id

def test_identifier_stored_as_claim():
    """Identifiers must be stored as claims with provenance."""
    claim = store.get_claim(scheme='cik', value='0000320193')
    assert claim.source_system is not None
    assert claim.confidence is not None
    assert claim.captured_at is not None
```

---

## Common Mistakes to Avoid

### ❌ Putting Ticker on Entity

```python
# WRONG
@dataclass
class Entity:
    ticker: str  # NO! Ticker belongs to Listing
```

### ❌ Returning Single Result

```python
# WRONG
def resolve(query: str) -> Entity | None:
    ...  # Must return ResolutionResult
```

### ❌ Silently Overwriting on Merge

```python
# WRONG
def merge(source, target):
    delete(source)  # NO! Must set merged_into_id
```

### ❌ Ignoring as_of Parameter

```python
# WRONG
def resolve_ticker(ticker: str) -> ResolutionResult:
    # Uses "current" listings only - breaks historical queries
```

### ❌ Storing Identifiers as Facts

```python
# WRONG
entity.cik = "0000320193"  # No provenance! Use claims table
```

### ❌ Auto-Merging Without Review

```python
# WRONG
def merge(source, target):
    execute_merge(source, target)  # Must create proposal first
```

---

## Your First Tasks (v2.2)

1. **Read v2.2 contract docs** (30 min): 
   - `00_UNIFIED_DATA_MODEL_V2_2.md`
   - `01_RESOLUTION_AND_TEMPORALITY.md`
   - `02_PYSECEDGAR_INTEGRATION_CONTRACT.md`

2. **Read GUARDRAILS + MANIFESTO** (15 min): Code standards

3. **Review scope changes from v2.1** (15 min): What's removed/changed

4. **Write Phase 1 tests** (1 hr): TDD start with v2.2 requirements

5. **Implement Phase 1** (2 hr): Make tests pass with correct schema

---

## Reference Links

- SEC company_tickers.json: https://www.sec.gov/files/company_tickers.json
- ULID spec: https://github.com/ulid/spec
- OpenFIGI: https://www.openfigi.com/
- GLEIF: https://www.gleif.org/
- Python packaging: https://packaging.python.org/

---

## Summary: v2.2 Non-Negotiables

| Requirement | v2.1 (Wrong) | v2.2 (Correct) |
|-------------|--------------|----------------|
| Entity has ticker | ✅ Yes | ❌ Never |
| Resolution returns | `Entity \| None` | `ResolutionResult` |
| Identifiers stored as | Facts | Claims with provenance |
| Merge behavior | Not specified | Redirect chain, never delete |
| Tier 1 schema | Flat entity | Entity/Security/Listing tables |
| Ambiguity handling | Pick one | Return ranked candidates |
| Point-in-time | Optional | Required (`as_of` parameter) |

---

*EntitySpine Development Prompt v2.2 | January 2026*
