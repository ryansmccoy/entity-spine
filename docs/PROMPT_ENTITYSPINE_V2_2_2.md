# EntitySpine - Enhancement Prompt (v2.2.2)

**For: Claude Opus 4.5 (Extended Thinking Mode)**

---

## 🚀 DO THIS FIRST (Before Any Changes)

### Step 1: Understand Existing EntitySpine Code (20 min)

```
EXPLORE IN THIS ORDER:
1. entityspine/src/entityspine/__init__.py           → Package exports + create_store()
2. entityspine/src/entityspine/models/               → Pydantic domain models
3. entityspine/src/entityspine/stores/               → SqlModelStore (Tier 1)
4. entityspine/src/entityspine/db/                   → SQLModel tables + repositories
5. entityspine/src/entityspine/core/                 → Utilities (ULID, timestamps)
```

### Step 2: Read Design Documents (15 min)

```
REQUIRED READING ORDER:
1. entityspine/GUARDRAILS.md                              → Non-negotiable standards
2. entityspine/docs/design/current/06_PROTOCOLS_AND_INTERFACES.md → AUTHORITATIVE protocols
3. entityspine/docs/design/current/05_TIER_CAPABILITIES_AND_LIMITS.md → as_of honesty
4. entityspine/docs/design/current/00_UNIFIED_DATA_MODEL_V2_2.md → Schema contract
5. entityspine/docs/MODEL_AUDIT_V2_2.md               → Model compliance audit
```

### Step 3: Run Existing Tests

```bash
cd entityspine
uv run pytest tests/ -v --tb=short
```

**All 66 tests should pass. Understand what works before changing anything.**

### Step 4: Review Implementation Status

The v2.2.2 implementation is COMPLETE for Tier 0-1:

- ✅ Entity/Security/Listing split done
- ✅ Ticker on Listing (NOT Entity)
- ✅ Claims support entity/security/listing targets
- ✅ ResolutionResult with warnings and limits
- ✅ SqlModelStore with repository pattern
- ✅ Pydantic models with validation
- ✅ 66 tests passing

**Next steps** (if enhancing):
- [ ] Add Tier 2 DuckDB support
- [ ] Add Tier 3 PostgreSQL support  
- [ ] Add fuzzy name matching
- [ ] Add external data source integrations

---

## ⚠️ STATUS: v2.2.2 Implementation COMPLETE

EntitySpine v2.2.2 has been fully implemented with:

- ✅ Pydantic v2 domain models (frozen, validated)
- ✅ SQLModel database tables + repository pattern
- ✅ Entity/Security/Listing split (ticker on Listing)
- ✅ Claims with entity/security/listing targets
- ✅ ResolutionResult with tier warnings
- ✅ SqlModelStore (Tier 1)
- ✅ JSON store (Tier 0)
- ✅ 66 tests passing

**Technology decisions:**
- Chose Pydantic over dataclasses for better validation/DX
- Chose SQLModel over raw SQL for cleaner repository pattern
- Chose uv over pip for reproducible builds

---

## ⚠️ CRITICAL: Read These Documents

### Development Standards

| Order | Document | Location | Why |
|-------|----------|----------|-----|
| **1** | GUARDRAILS.md | `entityspine/GUARDRAILS.md` | Non-negotiable code standards |
| **2** | MANIFESTO.md | `entityspine/docs/MANIFESTO.md` | Design philosophy |
| **3** | .cursorrules | `entityspine/.cursorrules` | AI coding patterns |

### v2.2.1 Contract Documents

| Order | Document | Key Focus |
|-------|----------|-----------|
| **4** | `00_UNIFIED_DATA_MODEL_V2_2.md` | **Master schema contract** |
| **5** | `01_RESOLUTION_AND_TEMPORALITY.md` | Resolution algorithms |
| **6** | `02_PYSECEDGAR_INTEGRATION_CONTRACT.md` | Port/adapter interface |
| **7** | `03_MIGRATION_NOTES.md` | v2.1→v2.2 changes |
| **8** | `04_IMPLEMENTATION_BLUEPRINT.md` | **Tech stack, TDD order** |
| **9** | `05_TIER_CAPABILITIES_AND_LIMITS.md` | **as_of honesty, capability matrix** |
| **10** | `06_PROTOCOLS_AND_INTERFACES.md` | **Authoritative protocol definitions** |
| **11** | `07_SQLITE_OPS_BEST_PRACTICES.md` | **PRAGMA, timestamps, lifecycle** |
| **12** | `08_IDENTIFIER_CLASSIFICATION.md` | **BRK.B ticker support, classification** |

All documents are in `entityspine/docs/design/`.

---

## ⚡ CURRENT PACKAGE STRUCTURE (Updated January 2026)

EntitySpine v2.2.2 has been modernized with Pydantic models:

```
entityspine/src/entityspine/
├── __init__.py                  # Package exports + create_store() factory
├── models/                      # Pydantic domain models (v2.2 compliant)
│   ├── __init__.py
│   ├── base.py                  # Base model with frozen=True
│   ├── entity.py                # Entity (NO ticker) ✅
│   ├── security.py              # Security model ✅
│   ├── listing.py               # Listing (TICKER HERE) ✅
│   ├── claim.py                 # IdentifierClaim with provenance ✅
│   └── resolution.py            # ResolutionResult with warnings ✅
├── db/                          # SQLModel database layer
│   ├── __init__.py
│   ├── engine.py                # Engine creation helpers
│   ├── tables.py                # SQLModel table definitions
│   └── repositories/            # Repository pattern
│       ├── __init__.py
│       ├── base.py              # Generic CRUD
│       ├── entity_repository.py
│       ├── security_repository.py
│       ├── listing_repository.py
│       └── claim_repository.py
├── stores/                      # Store implementations
│   └── sqlmodel_store.py        # Tier 1 SQLModel store ✅
├── adapters/                    # Legacy adapters (kept for compatibility)
│   ├── __init__.py
│   ├── json_store.py            # Tier 0 JSON store
│   └── protocol.py              # Storage protocols
└── core/                        # Utilities
    ├── __init__.py
    ├── config.py
    ├── exceptions.py
    ├── normalize.py
    ├── timestamps.py            # UTC helpers
    └── ulid.py                  # ULID generation
```

**v2.2.2 Status:**
- ✅ Entity/Security/Listing split complete
- ✅ Ticker correctly on Listing (NOT Entity)
- ✅ Claims-based identifiers with provenance
- ✅ ResolutionResult with tier warnings
- ✅ SQLModel store with repository pattern
- ✅ 66 tests passing

---

## ⚡ INLINE: Domain Model Definitions (Pydantic v2)

**These are the EXACT Pydantic model definitions (implemented):**

```python
# entityspine/models/entity.py
from pydantic import Field
from entityspine.models.base import EntitySpineModel, generate_id

class Entity(EntitySpineModel):
    """Legal organization (company, trust, fund). NO TICKER HERE."""
    
    entity_id: str = Field(default_factory=generate_id)
    primary_name: str = Field(..., min_length=1)
    cik: Optional[str] = None      # Zero-padded to 10 digits
    lei: Optional[str] = None      # 20-char LEI
    ein: Optional[str] = None      # 9-char EIN
    
    # v2.2 spec fields
    source_system: str = "unknown"
    redirect_to: Optional[str] = None   # Merged into this entity
    merged_at: Optional[datetime] = None
    
    # ❌ NO ticker field - ticker belongs to Listing

# entityspine/models/security.py
class Security(EntitySpineModel):
    """Financial instrument issued by an Entity."""
    
    security_id: str = Field(default_factory=generate_id)
    entity_id: str              # Links to Entity (issuer)
    security_type: SecurityType = SecurityType.COMMON_STOCK
    isin: Optional[str] = None  # 12-char ISIN
    cusip: Optional[str] = None # 9-char CUSIP
    figi: Optional[str] = None  # 12-char FIGI
    
    # v2.2 spec fields
    currency: Optional[str] = None  # ISO 4217
    status: str = "active"
    source_system: str = "unknown"

# entityspine/models/listing.py
class Listing(EntitySpineModel):
    """Where/when a Security trades. TICKER LIVES HERE."""
    
    listing_id: str = Field(default_factory=generate_id)
    security_id: str            # Links to Security
    ticker: str = Field(..., min_length=1)  # ← TICKER HERE
    mic: Optional[str] = None   # "XNAS", "XNYS" (ISO 10383)
    start_date: Optional[date] = None   # When listing started
    end_date: Optional[date] = None     # When delisted (None = current)
    is_primary: bool = False
    
    # v2.2 spec fields
    status: str = "active"
    source_system: str = "unknown"

# entityspine/models/claim.py
class IdentifierClaim(EntitySpineModel):
    """An identifier claim with provenance (NOT a fact)."""
    
    claim_id: str = Field(default_factory=generate_id)
    
    # v2.2: exactly one of these must be set
    entity_id: Optional[str] = None
    security_id: Optional[str] = None
    listing_id: Optional[str] = None
    
    scheme: IdentifierScheme   # CIK, LEI, ISIN, etc.
    value: str = Field(..., min_length=1)
    source: str = "unknown"
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    valid_from: Optional[date] = None
    valid_to: Optional[date] = None
```

---

## ⚡ v2.2.2 Implementation Status

| Area | v2.2 Spec | v2.2.2 Implementation |
|------|-----------|----------------------|
| **Domain models** | dataclasses | ✅ Pydantic v2 (frozen=True) |
| **Database** | Raw SQL | ✅ SQLModel + repositories |
| **Tier honesty** | warnings + limits | ✅ ResolutionResult.warnings |
| **E/S/L split** | Required | ✅ Complete |
| **Ticker location** | On Listing | ✅ Listing.ticker |
| **Claims** | Multi-target | ✅ entity_id/security_id/listing_id |
| **Package manager** | pip | ✅ uv with lock file |
| **Tests** | 66 passing | ✅ All green |

---

## ⚡ CRITICAL: Tier Capability Honesty

**SEC JSON has NO temporal data.** Be honest about what Tier 0-1 cannot do:

| Capability | Tier 0-1 Reality | Tier 3+ |
|------------|------------------|---------|
| `as_of` queries | ❌ Returns CURRENT with WARNING | ✅ True historical |
| MIC (exchange) | ❌ Not in SEC JSON | ✅ From market data |
| Listing validity | ❌ Not available | ✅ Full history |
| Multiple tickers | ❌ Current only | ✅ All historical |

### ResolutionResult Implementation

```python
# entityspine/models/resolution.py
from pydantic import Field
from entityspine.models.base import MutableEntitySpineModel

class ResolutionResult(MutableEntitySpineModel):
    """Result with tier capability honesty."""
    
    entity: Optional[Entity] = None
    security: Optional[Security] = None
    listing: Optional[Listing] = None
    status: ResolutionStatus = ResolutionStatus.NOT_FOUND
    tier: ResolutionTier = ResolutionTier.TIER_0
    
    # Query context
    query: str = ""
    as_of: Optional[date] = None
    as_of_honored: bool = True
    
    # v2.2 tier honesty
    warnings: list[str] = Field(default_factory=list)
    limits: dict[str, str] = Field(default_factory=dict)
    
    # Resolution path
    redirect_chain: list[str] = Field(default_factory=list)
    alternatives: list[Entity] = Field(default_factory=list)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    
    @property
    def found(self) -> bool:
        return self.entity is not None
    
    @property
    def has_warnings(self) -> bool:
        return len(self.warnings) > 0
```
    
    # v2.2.1: Tier capability honesty
    warnings: list[str] = field(default_factory=list)
    limits: dict[str, str] = field(default_factory=dict)
    tier: int = 0  # Which tier performed resolution
    
    @property
    def best(self) -> ResolutionCandidate | None:
        return self.candidates[0] if self.candidates else None
```

### Standard Warnings

| Warning | When Issued |
|---------|-------------|
| `"as_of_ignored"` | Tier 0-1 when `as_of` provided |
| `"mic_unavailable"` | Tier 0-1 when MIC requested |
| `"listing_history_unavailable"` | Tier 0-1 for ticker queries |
| `"redirect_chain_truncated"` | Chain exceeded MAX_REDIRECT_DEPTH |
| `"redirect_cycle_detected"` | Circular merge reference found |

---

## ⚡ PROTOCOL DEFINITIONS (AUTHORITATIVE)

**CRITICAL**: Use ONLY the protocol definitions from `06_PROTOCOLS_AND_INTERFACES.md`. That document is authoritative.

### Protocol Hierarchy

```
StorageLifecycleProtocol (initialize, close, introspection)
       │
       ├── EntityStoreProtocol (core CRUD, Tier 0+)
       │        │
       │        └── SecurityStoreProtocol (securities, Tier 1+)
       │
       └── SearchProtocol (search capabilities, varies by tier)

EntityResolverProtocol (main service interface, wraps store)
```

### EntityStoreProtocol (Core - All Tiers)

```python
class EntityStoreProtocol(Protocol):
    """Core entity storage operations - ALL tiers must implement."""
    
    def get_entity(self, entity_id: str) -> Entity | None: ...
    def get_entity_raw(self, entity_id: str) -> Entity | None: ...
    def store_entity(self, entity: Entity) -> None: ...
    def entity_count(self) -> int: ...
    def list_entities(self, limit: int = 100, offset: int = 0) -> list[Entity]: ...
    def get_claims(self, scheme: str, value: str) -> list[IdentifierClaim]: ...
    def store_claim(self, claim: IdentifierClaim) -> None: ...
    def listing_count(self) -> int: ...
```

### StorageLifecycleProtocol (Required for all stores)

```python
class StorageLifecycleProtocol(Protocol):
    """Lifecycle management for storage backends."""
    
    def initialize(self) -> None: ...
    def close(self) -> None: ...
    def load_sec_json(self, data: dict) -> int: ...
```

### EntityResolverProtocol (Service Interface)

```python
class EntityResolverProtocol(Protocol):
    """Main resolution service interface."""
    
    def resolve(self, query: str, as_of: date | None = None, limit: int = 10) -> ResolutionResult: ...
    def resolve_cik(self, cik: str) -> ResolutionResult: ...
    def resolve_ticker(self, ticker: str, mic: str | None = None, as_of: date | None = None) -> ResolutionResult: ...
    def get(self, entity_id: str) -> Entity | None: ...
    def get_canonical(self, entity_id: str) -> tuple[Entity | None, list[str], bool, bool]: ...
```

**Note**: `get_canonical()` returns 4-tuple: `(entity, chain, cycle_detected, truncated)`

---

## ⚡ IDENTIFIER CLASSIFICATION

**CRITICAL**: Support class share tickers like BRK.B, BRK-B. See `08_IDENTIFIER_CLASSIFICATION.md`.

### Improved Ticker Detection

```python
import re

# Supports: AAPL, BRK.B, BRK-B, BF.A, etc.
TICKER_PATTERN = re.compile(
    r"^[A-Z]{1,5}(?:[.-][A-Z])?$",
    re.IGNORECASE
)

def looks_like_ticker(s: str) -> tuple[bool, str]:
    """
    Detect ticker, normalizing hyphen to dot.
    
    Examples:
        looks_like_ticker("BRK-B") → (True, "BRK.B")
        looks_like_ticker("0000320193") → (False, "0000320193")
    """
    upper = s.upper().strip()
    normalized = upper.replace("-", ".")  # Normalize separator
    
    if len(normalized) > 7:
        return False, s
    if normalized.replace(".", "").isdigit():
        return False, s  # Numeric = CIK
    if TICKER_PATTERN.match(normalized):
        return True, normalized
    return False, s
```

### Identifier Types

| Type | Pattern | Example |
|------|---------|---------|
| CIK | 1-10 digits | `320193`, `0000320193` |
| Ticker | 1-5 letters + optional class | `AAPL`, `BRK.B` |
| Entity ID | 26 char ULID | `01ARZ3NDEKTSV4RRFFQ69G5FAV` |
| Scheme:Value | `scheme:value` | `isin:US0378331005` |
| Name | Default | `Apple Inc.` |

---

## ⚡ TIMESTAMP CONVENTIONS

**CRITICAL**: Always use timezone-aware UTC. See `07_SQLITE_OPS_BEST_PRACTICES.md`.

```python
from datetime import datetime, timezone

def utc_now() -> datetime:
    """Get current UTC timestamp (timezone-aware)."""
    return datetime.now(timezone.utc)

def to_iso8601(dt: datetime) -> str:
    """Convert to ISO-8601 string with Z suffix."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
```

**NEVER use**: `datetime.now()`, `datetime.utcnow()` (both return naive datetimes)

---

## ⚡ REDIRECT CHAIN SAFETY

**CRITICAL**: Implement cycle detection and max depth. See `07_SQLITE_OPS_BEST_PRACTICES.md`.

### Constants

```python
MAX_REDIRECT_DEPTH = 10
```

### Safe Implementation

```python
def get_canonical(self, entity_id: str) -> tuple[Entity | None, list[str], bool, bool]:
    """
    Returns: (entity, chain, cycle_detected, truncated)
    """
    chain: list[str] = []
    seen: set[str] = set()
    current_id = entity_id
    
    for depth in range(MAX_REDIRECT_DEPTH + 1):
        if current_id in seen:
            return None, chain, True, False  # Cycle!
        
        seen.add(current_id)
        chain.append(current_id)
        
        entity = self.get_entity_raw(current_id)
        if entity is None:
            return None, chain, False, False
        if entity.merged_into_id is None:
            return entity, chain, False, False  # Found canonical
        
        current_id = entity.merged_into_id
        
        if depth == MAX_REDIRECT_DEPTH:
            return entity, chain, False, True  # Truncated
    
    return None, chain, False, True
```

---

## ⚡ SQLITE BEST PRACTICES

**CRITICAL**: Apply PRAGMAs on every connection. See `07_SQLITE_OPS_BEST_PRACTICES.md`.

```python
PRAGMAS = [
    "PRAGMA foreign_keys = ON",       # REQUIRED
    "PRAGMA journal_mode = WAL",      # Recommended
    "PRAGMA synchronous = NORMAL",    # Safe with WAL
]

def _configure_connection(self, conn: sqlite3.Connection) -> None:
    for pragma in PRAGMAS:
        conn.execute(pragma)
```

---

## Mission

You are the lead architect and implementer for **entityspine**, a production-quality Python package for entity resolution in financial data.

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

## Storage Tiers (v2.2)

| Tier | Backend | Dependencies | Capabilities |
|------|---------|--------------|--------------|
| 0 | JSON | None (stdlib) | Entity lookup (current only) |
| 1 | SQLite | None (stdlib) | Full E/S/L schema (current only) |
| 2 | DuckDB | Optional | Analytics views |
| 3 | PostgreSQL | Optional | **Full temporal, multi-vendor** |

### Tier Capability Matrix (Complete)

| Capability | Tier 0 | Tier 1 | Tier 2 | Tier 3 |
|------------|--------|--------|--------|--------|
| CIK → Entity | ✅ | ✅ | ✅ | ✅ |
| Ticker → Entity (current) | ✅ | ✅ | ✅ | ✅ |
| Ticker → Entity (historical) | ⚠️ Warning | ⚠️ Warning | ⚠️ Warning | ✅ |
| as_of honored | ❌ Returns current | ❌ Returns current | ❌ Returns current | ✅ |
| MIC filtering | ❌ | ❌ | ❌ | ✅ |
| Listing history | ❌ | ❌ | ⚠️ Limited | ✅ |
| Merge redirect chains | ❌ | ✅ | ✅ | ✅ |
| Cross-vendor conflicts | ❌ | ❌ | ❌ | ✅ |

---

## Implementation Phases (v2.2.2 - Enhancement Path)

### Phase 1: Audit Existing Code

**Tasks**:
1. Review `domain/entities/model.py` - Understand current Entity
2. Review `domain/resolution/resolver.py` - Current resolution logic
3. Review `core/` - What utilities exist?
4. Run existing tests - What's the coverage?

```bash
cd entityspine
pytest tests/ --cov=entityspine --cov-report=term-missing
```

**🔴 CHECKPOINT 1: Document what exists vs what's needed**:
```
EXISTS:
- Entity model (with ticker - needs refactoring)
- SimpleEntity
- Basic resolver
- ULID generation

NEEDS ADDING:
- Security model
- Listing model  
- IdentifierClaim model
- ResolutionResult with warnings
- Storage protocols
- JSON/SQLite stores
```

---

### Phase 2: Add Security & Listing Models (E/S/L Split)

**Files to Create**:
1. `domain/security.py` - NEW
2. `domain/listing.py` - NEW (ticker HERE)
3. `domain/claims.py` - NEW

**Files to Modify**:
1. `domain/entities/model.py` - Remove ticker field

**🔴 CHECKPOINT 2: Tests pass, no ticker on Entity**:
```bash
pytest tests/unit/domain/ -v
# Entity should NOT have ticker attribute
```

---

### Phase 3: Add ResolutionResult with Warnings

**Files to Create**:
1. `resolution/result.py` - ResolutionResult with warnings/limits

**Files to Modify**:
1. `resolution/resolver.py` - Return ResolutionResult, add tier warnings

**🔴 CHECKPOINT 3: as_of generates warning**:
```bash
pytest tests/unit/resolution/ -v
# as_of in Tier 0-1 should add "as_of_ignored" to warnings
```

---

### Phase 4: Add Storage Protocols & Tier 0 Store

**Files to Create**:
1. `adapters/protocol.py` - From doc 06
2. `adapters/json_store.py` - Tier 0 (SEC JSON)

**🔴 CHECKPOINT 4: Tier 0 works**:
```bash
pytest tests/adapters/test_json_store.py -v
```

---

### Phase 5: Add Tier 1 SQLite Store

**Files to Create**:
1. `adapters/sqlite_store.py` - Full E/S/L schema
2. `adapters/migrations/001_initial.sql`

**🔴 CHECKPOINT 5: SQLite with proper PRAGMAs**:
```bash
pytest tests/adapters/test_sqlite_store.py -v
pytest tests/adapters/test_sqlite_pragmas.py -v
```

---

### Phase 6: Integration Port

**Files to Create**:
1. `ports/py_sec_edgar.py` - EntityResolverPort

**🔴 FINAL CHECKPOINT: Full test suite**:
```bash
pytest tests/ --cov=entityspine --cov-fail-under=80
mypy entityspine/src/entityspine/ --strict
ruff check entityspine/src/
```

---

## Technology Stack (Updated January 2026)

### Implementation Decision

After evaluating trade-offs, the v2.2.2 implementation uses:

| Component | Technology | Why |
|-----------|------------|-----|
| Domain Models | **Pydantic v2** | Better validation, JSON serialization, IDE support |
| Database Tables | **SQLModel** | Pydantic + SQLAlchemy hybrid, clean repository pattern |
| Package Manager | **uv** | Fast, reproducible builds with lock file |
| IDs | Custom ULID | No external package, compatible with Pydantic |
| Interfaces | `typing.Protocol` | Structural subtyping |
| Timestamps | `datetime.timezone.utc` | Timezone-aware |

### Original Spec vs Implementation

The original spec said "NEVER use Pydantic at Tier 0-1" to maintain zero dependencies.
We chose to accept Pydantic as a dependency for:
1. **Better validation**: Declarative field validation with clear error messages
2. **JSON serialization**: Built-in with proper datetime handling
3. **Developer experience**: Familiar to modern Python developers
4. **IDE support**: Better autocomplete and type checking
5. **Ecosystem**: Works seamlessly with FastAPI when needed

**Trade-off**: Adds ~11MB installed dependency. Accepted for improved DX.

---

## Core Design Principles (v2.2)

### 1. Claims, Not Facts

Every identifier is a **claim** with provenance:

```python
# ❌ WRONG: Treating identifier as fact
entity.lei = "HWUPKR0MPOU8FGXBT394"

# ✅ CORRECT: Treating identifier as claim (Pydantic model)
from entityspine import IdentifierClaim, IdentifierScheme

claim = IdentifierClaim(
    entity_id="01ARZ3...",
    scheme=IdentifierScheme.LEI,
    value="HWUPKR0MPOU8FGXBT394",
    source="gleif",
    confidence=1.0,
)
```

### 2. Return Ambiguity, Never Guess

Resolution returns **ranked candidates** with **warnings**:

```python
# ❌ WRONG: Single result
def resolve(query: str) -> Entity | None: ...

# ✅ CORRECT: Ranked candidates + warnings
def resolve(query: str, as_of: date | None = None) -> ResolutionResult:
    result = ResolutionResult(...)
    if as_of and self._tier < 3:
        result.warnings.append("as_of_ignored")
    return result
```

### 3. Merges Create Redirects, Never Delete

Old IDs stay resolvable forever with **safe chain following**:

```python
# Returns 4-tuple with safety flags
entity, chain, cycle_detected, truncated = resolver.get_canonical("A")

if cycle_detected:
    logger.error(f"Cycle in merge chain: {chain}")
if truncated:
    logger.warning(f"Chain truncated at depth {MAX_REDIRECT_DEPTH}")
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

---

## Quality Gates

- **Coverage**: 90%+ for core, 80%+ overall
- **Type Checking**: `mypy --strict` passes
- **Linting**: `ruff check` clean
- **Formatting**: `ruff format` applied
- **Documentation**: All public APIs have Google-style docstrings

---

## Common Mistakes to Avoid (v2.2.1)

### ❌ Using Methods Not in Protocol

```python
# WRONG: search_aliases not in EntityStoreProtocol
matches = store.search_aliases(query)  

# ✅ CORRECT: Use SearchProtocol or resolver
result = resolver.resolve(query)  # SearchProtocol handles it
```

### ❌ Silent as_of Failure

```python
# WRONG: Silently ignores as_of in Tier 0-1
def resolve_ticker(self, ticker, as_of=None):
    listings = self._get_current_listings(ticker)  # Ignores as_of!

# ✅ CORRECT: Add warning
def resolve_ticker(self, ticker, as_of=None):
    result = ResolutionResult(...)
    if as_of and self._tier < 3:
        result.warnings.append("as_of_ignored")
        result.limits["temporal"] = "current_only"
    return result
```

### ❌ Naive Ticker Detection

```python
# WRONG: Misses BRK.B
def _is_ticker(s):
    return len(s) <= 5 and s.isalpha()

# ✅ CORRECT: Use TICKER_PATTERN
def _is_ticker(s):
    return TICKER_PATTERN.match(s.upper().replace("-", "."))
```

### ❌ Naive Datetime

```python
# WRONG: Timezone-naive
created_at = datetime.now()
created_at = datetime.utcnow()  # Also wrong!

# ✅ CORRECT: Timezone-aware UTC
from entityspine.core.timestamps import utc_now
created_at = utc_now()
```

### ❌ No Redirect Safety

```python
# WRONG: Infinite loop possible
def get(self, entity_id):
    entity = self._load(entity_id)
    if entity.merged_into_id:
        return self.get(entity.merged_into_id)  # No depth limit!

# ✅ CORRECT: Use get_canonical with safety
def get(self, entity_id):
    entity, chain, cycle, truncated = self.get_canonical(entity_id)
    return entity
```

### ❌ Missing PRAGMA

```python
# WRONG: Foreign keys not enforced
conn = sqlite3.connect("db.sqlite")

# ✅ CORRECT: Apply PRAGMAs
conn = sqlite3.connect("db.sqlite")
conn.execute("PRAGMA foreign_keys = ON")
conn.execute("PRAGMA journal_mode = WAL")
```

### ❌ Putting Ticker on Entity

```python
# WRONG
@dataclass
class Entity:
    ticker: str  # NO! Ticker belongs to Listing
```

---

## Testing Strategy

### Test Directory Structure

```
tests/
├── conftest.py                  # Shared fixtures
├── unit/
│   ├── core/
│   │   ├── test_ulid.py
│   │   ├── test_timestamps.py   # NEW: UTC tests
│   │   └── test_identifier_classification.py  # NEW
│   ├── domain/
│   │   ├── test_entity.py
│   │   ├── test_security.py
│   │   ├── test_listing.py
│   │   └── test_claims.py
│   └── resolution/
│       ├── test_resolver.py
│       ├── test_ranking.py
│       └── test_redirect_safety.py  # NEW
├── adapters/
│   └── storage/
│       ├── test_json_store.py
│       ├── test_sqlite_store.py
│       ├── test_sqlite_pragmas.py   # NEW
│       └── test_protocol_compliance.py
└── integration/
    ├── test_resolution_flow.py
    ├── test_merge_redirect.py
    ├── test_tier_warnings.py        # NEW
    └── test_pysecedgar_port.py
```

---

## Document Reference

| Document | Purpose |
|----------|---------|
| `00_UNIFIED_DATA_MODEL_V2_2.md` | Master schema, E/S/L definitions |
| `01_RESOLUTION_AND_TEMPORALITY.md` | Resolution algorithms, as_of semantics |
| `02_PYSECEDGAR_INTEGRATION_CONTRACT.md` | Port interface for py-sec-edgar |
| `03_MIGRATION_NOTES.md` | Breaking changes from v2.1 |
| `04_IMPLEMENTATION_BLUEPRINT.md` | Tech stack, TDD phases |
| `05_TIER_CAPABILITIES_AND_LIMITS.md` | **Capability matrix, as_of honesty** |
| `06_PROTOCOLS_AND_INTERFACES.md` | **Authoritative protocol definitions** |
| `07_SQLITE_OPS_BEST_PRACTICES.md` | **PRAGMA, timestamps, redirect safety** |
| `08_IDENTIFIER_CLASSIFICATION.md` | **BRK.B support, classification logic** |
| `09_FEEDSPINE_INTEGRATION_ANALYSIS.md` | **Ecosystem integration, FeedSpine/py-sec-edgar** |

---

## ⚡ ECOSYSTEM CONTEXT: Where EntitySpine Fits

EntitySpine is part of a **three-package ecosystem**:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           PY-SEC-EDGAR ECOSYSTEM                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                           py-sec-edgar                               │   │
│  │                     (Main Application Layer)                         │   │
│  │  • CLI interface, filing workflows, SEC EDGAR API                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                              │                    │                          │
│                              ▼                    ▼                          │
│  ┌──────────────────────────────────┐   ┌──────────────────────────────┐   │
│  │           FeedSpine              │   │        EntitySpine ◀── YOU   │   │
│  │       (Data Ingestion)           │   │     (Identity Resolution)    │   │
│  │  • Feed deduplication            │   │  • Ticker/CIK → Entity       │   │
│  │  • Sighting tracking             │   │  • Claims with provenance    │   │
│  │  • Bronze/Silver/Gold layers     │   │  • Merge/rename history      │   │
│  └──────────────────────────────────┘   └──────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### EntitySpine's Role

| Responsibility | EntitySpine Owns | EntitySpine Does NOT Own |
|----------------|------------------|--------------------------|
| **Identity** | "Who is CIK 0000320193?" | How data is fetched |
| **Resolution** | Ticker → Entity mapping | Filing content |
| **Claims** | Identifier provenance | Feed scheduling |
| **Crosswalk** | CIK ↔ LEI ↔ FIGI | UI/CLI |

### Key Integration Points

1. **py-sec-edgar** calls EntitySpine to resolve tickers before fetching:
   ```python
   # py-sec-edgar uses EntitySpine
   result = resolver.resolve_ticker("AAPL")
   cik = result.best.cik  # "0000320193"
   ```

2. **FeedSpine** (optional) can provide symbology data to EntitySpine:
   ```python
   # FeedSpine feeds → EntitySpine stores
   for record in feedspine.query(source="sec-tickers"):
       entityspine.store_claim(record_to_claim(record))
   ```

3. **EntitySpine remains zero-deps** - works without FeedSpine for simple use cases.

See `09_FEEDSPINE_INTEGRATION_ANALYSIS.md` for full ecosystem documentation.

---

## Your First Tasks (v2.2.1)

1. **Read v2.2.1 design docs** (45 min): 
   - `05_TIER_CAPABILITIES_AND_LIMITS.md` (NEW)
   - `06_PROTOCOLS_AND_INTERFACES.md` (NEW)
   - `07_SQLITE_OPS_BEST_PRACTICES.md` (NEW)
   - `08_IDENTIFIER_CLASSIFICATION.md` (NEW)

2. **Verify protocol compliance**: Ensure your implementations match `06_PROTOCOLS_AND_INTERFACES.md` EXACTLY

3. **Add tier warnings**: Implement `warnings` and `limits` in `ResolutionResult`

4. **Fix ticker detection**: Use improved pattern from `08_IDENTIFIER_CLASSIFICATION.md`

5. **Apply SQLite best practices**: PRAGMA configuration, UTC timestamps

6. **Add redirect safety**: Cycle detection, max depth, 4-tuple return

---

*EntitySpine Development Prompt v2.2.2 | January 2026*
