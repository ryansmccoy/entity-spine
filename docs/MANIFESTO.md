# EntitySpine Manifesto

**Zero-Dependency Entity Resolution for SEC EDGAR Data**

*Version: 0.4*  
*Updated: February 2026*

---

## The Problem

Financial data is fragmented across identifiers:

```
CIK: 0000320193      ← SEC's identifier
Ticker: AAPL         ← Exchange identifier  
CUSIP: 037833100     ← Settlement identifier
LEI: HWUPKR0MPOU8FGXBT394  ← Global legal entity identifier
```

**Is this all the same company?** That's entity resolution.

Current solutions require:
- Heavy ORM dependencies (SQLAlchemy, Django)
- Complex graph databases (Neo4j)
- Vendor lock-in (Bloomberg, Refinitiv)

We need something that starts simple and scales.

---

## The Solution: EntitySpine

EntitySpine provides **progressive entity resolution**:

```
Tier 0: JSON + dataclasses    → Zero dependencies
Tier 1: SQLite               → stdlib only
Tier 2: DuckDB               → Analytics scale
Tier 3: PostgreSQL           → Production scale
```

### Core Architecture

```
              Entity
               │
    ┌──────────┼──────────┐
    │          │          │
Security   Security   Security
    │          │          │
 Listing   Listing   Listing
    │          │          │
  AAPL       AAPL      037833
  NASDAQ     NYSE      CUSIP
```

**Entity ≠ Security ≠ Listing** — This separation is fundamental.

---

## Core Principles

### 1. Zero Core Dependencies

The core library uses only Python stdlib:

```python
# ✅ Core uses stdlib only
from dataclasses import dataclass
from typing import Optional
import sqlite3

# ❌ Never in core
import pydantic  # Optional adapter
import sqlalchemy  # Optional adapter
```

**Why?** Easy auditing, fast startup, minimal attack surface.

### 2. Canonical Domain Models

All business logic lives in `entityspine.domain`:

```python
from entityspine.domain import Entity, Security, Listing, IdentifierClaim

# These are stdlib dataclasses with validation
entity = Entity(
    primary_name="Apple Inc.",
    source_system="sec",
    source_id="0000320193"
)
```

Pydantic/ORM wrappers are optional adapters.

### 3. IdentifierClaim as Source of Truth

Every identifier is a **claim**, not a fact:

```python
claim = IdentifierClaim(
    entity_id="ent_abc123",
    scheme=IdentifierScheme.CIK,
    value="0000320193",
    status=ClaimStatus.VERIFIED,
    source="sec_company_tickers",
    confidence=0.99
)
```

**Why claims?** Real-world data has conflicts, errors, and changes.

### 4. Tiered Storage

Start simple, scale when needed:

| Tier | Storage | Dependencies | Use Case |
|------|---------|--------------|----------|
| 0 | JSON file | None | Development, testing |
| 1 | SQLite | stdlib | Single-user, local |
| 2 | DuckDB | `[duckdb]` | Analytics workloads |
| 3 | PostgreSQL | `[postgres]` | Multi-user production |

```python
# Same API, different scale
from entityspine import EntityManager

# Tier 0
manager = EntityManager(storage="json://./data/entities.json")

# Tier 1
manager = EntityManager(storage="sqlite://./data/entities.db")

# Tier 3
manager = EntityManager(storage="postgresql://localhost/entities")
```

### 5. Resolution, Not Matching

Entity resolution isn't fuzzy matching—it's **confident identification**:

```python
result = resolver.resolve("AAPL")

# Returns resolution with confidence
ResolutionResult(
    status=ResolutionStatus.FOUND,
    entity_id="ent_abc123",
    confidence=0.95,
    match_reason=MatchReason.TICKER_EXACT,
    candidates=[...]  # Other potential matches
)
```

---

## What We're NOT Building

1. **A general-purpose graph database** — Use Neo4j for that
2. **A trading system** — We resolve identities, not execute trades
3. **A data vendor** — We organize YOUR data
4. **A monolith** — Each tier can run independently

---

## The Knowledge Graph

EntitySpine models the financial world:

```
┌─────────────────────────────────────────────────────────────┐
│                      KNOWLEDGE GRAPH                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   ┌────────┐    employs    ┌────────┐    files    ┌──────┐  │
│   │ Person ├──────────────→│ Entity │────────────→│ Form │  │
│   └────────┘               └───┬────┘             └──────┘  │
│                                │                             │
│                           issues                             │
│                                │                             │
│                                ▼                             │
│                          ┌──────────┐                        │
│                          │ Security │                        │
│                          └────┬─────┘                        │
│                               │                              │
│                          listed as                           │
│                               │                              │
│                               ▼                              │
│                          ┌─────────┐                         │
│                          │ Listing │                         │
│                          └─────────┘                         │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Success Metrics

1. **Resolution accuracy**: >99% on SEC company_tickers.json
2. **Startup time**: <100ms for Tier 0-1
3. **Query latency**: <10ms for single entity lookup
4. **Zero core dependencies**: Verified by CI

---

## Getting Started

```python
from entityspine import EntityManager, Entity

# Initialize (Tier 1 SQLite)
manager = EntityManager(storage="sqlite://./entities.db")

# Load SEC data
manager.load_sec_company_tickers()

# Resolve
result = manager.resolve("AAPL")
print(f"Found: {result.entity.primary_name}")  # Apple Inc.
```

---

*EntitySpine: From company_tickers.json to enterprise-grade Knowledge Graph.*
