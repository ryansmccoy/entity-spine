# EntitySpine Manifesto

**A Lightweight Entity Resolution Library for Financial Data**

*Version: 2.0 (v2.2.2 Implementation)*  
*Updated: January 2026*

---

## Implementation Status

**EntitySpine v2.2.2 is COMPLETE for Tier 0-1:**

| Component | Status | Technology |
|-----------|--------|------------|
| Domain Models | ✅ Complete | Pydantic v2 (frozen) |
| E/S/L Split | ✅ Complete | Ticker on Listing |
| Claims | ✅ Complete | Entity/Security/Listing targets |
| JSON Store | ✅ Complete | Tier 0 |
| SQLite Store | ✅ Complete | SQLModel + Repository pattern |
| Resolution | ✅ Complete | With tier warnings |
| Tests | ✅ 66 passing | Full coverage |

---

## The Problem

You want to:
1. Look up **any financial identifier** (CIK, ticker, ISIN, LEI, CUSIP)
2. Get back a **canonical entity** (the real-world company)
3. Handle **ticker reuse** (META was Facebook, now it's not MTFA)
4. Work **locally first** (no server required)
5. **Scale up** when needed (PostgreSQL for production)

Existing solutions are either:
- Too heavy (requires database server, complex setup)
- Too simple (no identifier hierarchy, no temporal validity)
- Locked to one data source (SEC only, or Bloomberg only)
- Expensive (commercial data services)

---

## The Solution: EntitySpine

A **zero-to-hero** Python package that starts simple and grows with you:

```bash
# Zero dependencies - just works
pip install entityspine
```

```python
from entityspine import EntityResolver

resolver = EntityResolver()

# All of these refer to Apple Inc
resolver.resolve("AAPL")           # Ticker
resolver.resolve("320193")         # CIK (any format)
resolver.resolve("0000320193")     # Padded CIK
resolver.resolve("Apple Inc")      # Name search
```

---

## Core Principles

### 1. Entity ≠ Security ≠ Listing

**Critical Distinction** - These are NOT the same thing:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      THE HIERARCHY                                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   ENTITY (Apple Inc)                                                    │
│   └── The legal organization that files with the SEC                    │
│       Identifiers: CIK, LEI, EIN, DUNS                                  │
│                                                                         │
│       └── SECURITY (AAPL Common Stock)                                  │
│           └── A financial instrument issued by the entity               │
│               Identifiers: ISIN, CUSIP, FIGI                            │
│                                                                         │
│               └── LISTING (AAPL on NASDAQ)                              │
│                   └── Where/how the security trades                     │
│                       Identifiers: Ticker + MIC (exchange code)         │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**Why this matters:**
- **Tickers reuse**: `META` was Metamark, now Meta Platforms. Same ticker, different entity.
- **Cross-listing**: Apple trades as AAPL on NASDAQ and 0R2V on LSE. Same entity, different listings.
- **Multiple securities**: A company can have Class A, Class B shares. Same entity, different securities.

### 2. Progressive Enhancement (Tier System)

```
┌──────────────────────────────────────────────────────────────────────────┐
│                       STORAGE TIERS                                      │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   TIER 0: JSON (Zero Dependencies)                                       │
│   ════════════════════════════════                                       │
│   • SEC company_tickers.json (auto-downloaded)                           │
│   • In-memory dict, read-only                                            │
│   • Perfect for: scripts, CLI tools, quick lookups                       │
│   • Dependencies: NONE (stdlib only)                                     │
│                                                                          │
│   TIER 1: SQLite (Zero Dependencies)                                     │
│   ══════════════════════════════════                                     │
│   • Local database file, read/write                                      │
│   • Add aliases, custom entities                                         │
│   • Perfect for: local development, personal projects                    │
│   • Dependencies: NONE (stdlib sqlite3)                                  │
│                                                                          │
│   TIER 2: DuckDB (Optional)                                              │
│   ══════════════════════════                                             │
│   • Analytical queries, Parquet export                                   │
│   • Perfect for: data science, bulk analysis                             │
│   • Dependencies: pip install entityspine[duckdb]                        │
│                                                                          │
│   TIER 3: PostgreSQL (Optional)                                          │
│   ══════════════════════════════                                         │
│   • Full Entity/Security/Listing hierarchy                               │
│   • Multi-user, production-ready                                         │
│   • Perfect for: services, APIs, team environments                       │
│   • Dependencies: pip install entityspine[postgres]                      │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

**Same API at every tier:**

```python
# Tier 0: JSON
resolver = EntityResolver()

# Tier 1: SQLite  
resolver = EntityResolver(db_path="entities.db")

# Tier 2: DuckDB
resolver = EntityResolver(backend="duckdb", db_path="entities.duckdb")

# Tier 3: PostgreSQL
resolver = EntityResolver(backend="postgres", dsn="postgresql://...")

# API is IDENTICAL - swap backends without code changes
entity = resolver.resolve("AAPL")
```

### 3. Identifier Scope Enforcement

Identifiers are NOT interchangeable. Each has a specific scope:

| Identifier | Scope | Attached To | Example |
|------------|-------|-------------|---------|
| CIK | Entity | The filer | `0000320193` |
| LEI | Entity | Legal entity globally | `HWUPKR0MPOU8FGXBT394` |
| EIN | Entity | US tax ID | `942404110` |
| ISIN | Security | Specific instrument | `US0378331005` |
| CUSIP | Security | US/Canada instrument | `037833100` |
| FIGI | Security | Bloomberg ID | `BBG000B9XRY4` |
| Ticker | Listing | Exchange symbol | `AAPL` on `XNAS` |

**Tier 0-2**: Simplified (everything maps to entity)
**Tier 3**: Full scope enforcement (identifiers attach to correct object)

### 4. Temporal Validity

Tickers change owners. Corporate actions happen. EntitySpine tracks time:

```python
# Who was AAPL on 2023-01-15?
resolver.resolve("AAPL", as_of="2023-01-15")

# Historical ticker lookup
resolver.resolve("FB", as_of="2021-06-01")  # → Meta Platforms
resolver.resolve("FB", as_of="2022-06-01")  # → None (renamed to META)
```

### 5. Protocol-Based Design

All storage backends implement the same protocol:

```python
class EntityStore(Protocol):
    """What every backend must implement."""
    
    def get(self, entity_id: str) -> Entity | None: ...
    def get_by_cik(self, cik: str) -> Entity | None: ...
    def get_by_ticker(self, ticker: str) -> Entity | None: ...
    def search(self, query: str, limit: int = 10) -> list[Entity]: ...
    def save(self, entity: Entity) -> None: ...
```

**Benefits:**
- Swap backends without API changes
- Test with in-memory, deploy with PostgreSQL
- New backends can be added by anyone

---

## What EntitySpine Is NOT

### Not a Data Provider

EntitySpine is a **resolution engine**, not a data source:

- ✅ "Given AAPL, what's the canonical entity?"
- ❌ "Download all company fundamental data"

Data comes from:
- SEC (company_tickers.json, EDGAR filings)
- OpenFIGI (FIGI mappings)
- GLEIF (LEI data)
- Your own sources

### Not a Full MDM System

EntitySpine is focused on **entity resolution**:

- ✅ CIK → Entity → Canonical name
- ❌ Master Data Management workflows
- ❌ Data stewardship UI
- ❌ Complex matching rules engine

For full MDM, use Tamr, Informatica, or build on top of EntitySpine.

### Not py-sec-edgar

EntitySpine is a **separate package** that py-sec-edgar depends on:

- `entityspine`: Entity resolution (any domain)
- `py-sec-edgar`: SEC filing collection (SEC specific)

```python
# py-sec-edgar uses entityspine internally
from py_sec_edgar import FilingCollector
from entityspine import EntityResolver  # Separate import

# Or they work together
collector = FilingCollector()
resolver = EntityResolver()

filing = collector.get_filing("0000320193-24-000081")
entity = resolver.resolve(filing.filer_cik)
```

---

## Design Decisions

### Why ULID for Primary Keys?

- **Sortable**: ULIDs sort chronologically
- **No coordination**: Generate anywhere, no DB sequence needed
- **URL-safe**: No special characters
- **Compact**: 26 characters vs UUID's 36

```python
# ULID: 01ARZ3NDEKTSV4RRFFQ69G5FAV
# UUID: 550e8400-e29b-41d4-a716-446655440000
```

### Why Pydantic Instead of Dataclasses?

The original design called for stdlib-only (dataclasses) at Tier 0-1.  
We chose Pydantic v2 for:

- **Better validation**: Declarative field validation with clear errors
- **JSON serialization**: Built-in datetime/enum handling
- **Developer experience**: Familiar to modern Python developers
- **IDE support**: Better autocomplete and type checking

**Trade-off**: Adds `pydantic` dependency (~11MB). Accepted for improved DX.

### Why Protocol Pattern?

- **Testability**: Mock any backend
- **Flexibility**: Add new backends without touching core
- **Type safety**: Protocols work with mypy
- **Documentation**: Interface is explicit

---

## Success Criteria

EntitySpine is successful when:

1. **Any identifier resolves in <10ms** (Tier 0-1)
2. **Zero dependencies** for basic usage
3. **Same API** works across all tiers
4. **90%+ test coverage** maintained
5. **Clear documentation** with runnable examples

---

## Ecosystem Integration

EntitySpine is part of a **three-package ecosystem**:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           PY-SEC-EDGAR ECOSYSTEM                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                           py-sec-edgar                               │   │
│  │                     (Main Application Layer)                         │   │
│  │  • CLI, filing workflows, SEC EDGAR API                             │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                              │                    │                          │
│                              ▼                    ▼                          │
│  ┌──────────────────────────────────┐   ┌──────────────────────────────┐   │
│  │           FeedSpine              │   │      EntitySpine ◀── HERE    │   │
│  │       (Data Ingestion)           │   │     (Identity Resolution)    │   │
│  │  • Feed deduplication            │   │  • Ticker/CIK → Entity       │   │
│  │  • Sighting tracking             │   │  • Claims with provenance    │   │
│  └──────────────────────────────────┘   └──────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Cross-Package Improvements Welcome

**You are encouraged to modify ANY package to improve the overall system.**

- If EntitySpine's API is awkward for py-sec-edgar → **fix EntitySpine**
- If FeedSpine needs entity context → **add EntitySpine adapter to FeedSpine**
- If py-sec-edgar's integration is clunky → **improve the port interface**

See `design/09_FEEDSPINE_INTEGRATION_ANALYSIS.md` for ecosystem details.

---

## Related Documents

| Document | Purpose |
|----------|--------|
| [GUARDRAILS.md](../GUARDRAILS.md) | Development standards (MUST READ) |
| [MODEL_AUDIT_V2_2.md](MODEL_AUDIT_V2_2.md) | Model compliance audit |
| [design/current/00_UNIFIED_DATA_MODEL_V2_2.md](design/current/00_UNIFIED_DATA_MODEL_V2_2.md) | Canonical data model (v2.2) |
| [design/current/06_PROTOCOLS_AND_INTERFACES.md](design/current/06_PROTOCOLS_AND_INTERFACES.md) | Protocol definitions |
| [PROMPT_ENTITYSPINE_V2_2_2.md](PROMPT_ENTITYSPINE_V2_2_2.md) | LLM implementation guide |

---

*"Simple things should be simple, complex things should be possible."* — Alan Kay

---

*Version 1.0 | January 2026*
