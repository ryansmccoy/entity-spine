# EntitySpine API Access Points Design

## Executive Summary

This document analyzes all access points for entity resolution functionality and proposes a unified design inspired by popular financial data APIs like yfinance, OpenBB, alpha_vantage, pandas-datareader, and professional terminals (Bloomberg, FactSet, Refinitiv).

---

## 1. Current Access Points Inventory

### 1.1 What We Have Now

| Access Point | Location | Status |
|--------------|----------|--------|
| **Python SDK** | `entityspine/__init__.py` | ✅ Exists (domain models, `EntityResolver`) |
| **REST API** | `entityspine/api/app.py` | ✅ Exists (9 endpoints) |
| **CLI** | N/A | ❌ Missing |
| **py-sec-edgar Integration** | Port pattern | 📋 Designed |

### 1.2 What py-sec-edgar Has

| Access Point | Location | Status |
|--------------|----------|--------|
| **Python Client** | `py_sec_edgar/client.py` | ✅ `SecClient` class |
| **CLI** | `py_sec_edgar/cli.py` | ✅ Click-based, 500+ lines |
| **REST API** | `py_sec_edgar/api/` | ✅ FastAPI |
| **Ticker Service** | `py_sec_edgar/ticker_service.py` | ✅ Separate module |

---

## 2. Patterns from Popular Financial APIs

### 2.1 yfinance (21K+ stars) - Object-Oriented Ticker

```python
import yfinance as yf

# Core pattern: Ticker object is the entry point
ticker = yf.Ticker("AAPL")

# All data hangs off the ticker
ticker.info           # Company info (dict)
ticker.history()      # Price history
ticker.financials     # Financial statements
ticker.dividends      # Dividend history
ticker.options        # Options chain

# Multi-ticker support
tickers = yf.Tickers("AAPL MSFT GOOGL")
tickers.tickers["AAPL"].info

# Download function for bulk
data = yf.download(["AAPL", "MSFT"], start="2020-01-01")
```

**Key Patterns:**
- **Ticker as primary object** - everything hangs off it
- **Lazy loading** - data fetched on demand
- **Batch support** - `Tickers` for multiple, `download` for bulk
- **Caching** - session-based caching

### 2.2 OpenBB (SEC Provider) - Command-Style API

```python
from openbb import obb

# Command-style API with dot notation
obb.regulators.sec.cik_map(symbol="AAPL")           # Ticker → CIK
obb.regulators.sec.symbol_map(query="0000320193")   # CIK → Ticker
obb.regulators.sec.institutions_search("Berkshire")  # Search by name
obb.regulators.sec.company_filings(symbol="AAPL")   # Get filings

obb.equity.search("Apple", provider="sec")           # Find companies

# Returns OBBject with .results, .to_df(), .to_dict()
result = obb.regulators.sec.cik_map(symbol="AAPL")
result.results.cik  # Access data
result.to_df()      # As DataFrame
```

**Key Patterns:**
- **Namespace hierarchy** - `obb.regulators.sec.*`
- **Provider abstraction** - same interface, multiple data sources
- **Consistent response objects** - `OBBject` wrapper
- **DataFrame-first** - `.to_df()` everywhere

### 2.3 alpha_vantage - Client Per Domain

```python
from alpha_vantage.timeseries import TimeSeries
from alpha_vantage.fundamentaldata import FundamentalData

# Separate clients per domain
ts = TimeSeries(key='YOUR_KEY', output_format='pandas')
fd = FundamentalData(key='YOUR_KEY', output_format='pandas')

# Domain-specific methods
data, meta = ts.get_intraday('GOOGL')
data, meta = fd.get_company_overview('AAPL')

# Async support
from alpha_vantage.async_support.timeseries import TimeSeries
ts = TimeSeries(key='YOUR_KEY')
data, _ = await ts.get_quote_endpoint('AAPL')
await ts.close()
```

**Key Patterns:**
- **Domain-specific clients** - TimeSeries, FundamentalData, etc.
- **Output format option** - JSON, pandas, CSV
- **Tuple returns** - `(data, metadata)`
- **Async support** - parallel fetching

### 2.4 pandas-datareader - Unified Reader

```python
import pandas_datareader.data as web

# Universal DataReader interface
df = web.DataReader('AAPL', 'yahoo', start, end)
df = web.DataReader('GDP', 'fred', start, end)
df = web.DataReader('ticker=RGDPUS', 'econdb')

# Also specific functions
from pandas_datareader.nasdaq_trader import get_nasdaq_symbols
symbols = get_nasdaq_symbols()
```

**Key Patterns:**
- **Unified interface** - same function, source as parameter
- **Source abstraction** - 'yahoo', 'fred', 'iex', etc.
- **DataFrame output** - always returns DataFrame
- **Start/end dates** - temporal range is core

### 2.5 Bloomberg (blp) - Session-Based

```python
from blp import blp

# Session management
bq = blp.BlpQuery()

# Reference data (like entity info)
bq.bdp(['AAPL US Equity'], ['PX_LAST', 'CIK_NUMBER'])

# Historical data
bq.bdh(['AAPL US Equity'], ['PX_LAST'], start_date, end_date)

# Bulk download
bq.bds('SPX Index', 'INDX_MWEIGHT')
```

**Key Patterns:**
- **Security identifier syntax** - `AAPL US Equity` (ticker + market + type)
- **Field-based requests** - specify exactly what data you want
- **bdp/bdh/bds** - point/history/bulk naming convention

---

## 3. Proposed Unified EntitySpine Design

### 3.1 Core Principle: "Resolve First, Query Later"

Unlike price data APIs (where you know the ticker), entity resolution has **ambiguity** as a core problem. Our API needs to handle:
- Input: "AAPL" or "Apple" or "0000320193"
- Output: Unambiguous entity with all identifiers

### 3.2 Three-Layer Architecture

```
┌────────────────────────────────────────────────────────────┐
│  Layer 1: Python SDK (Primary)                             │
│  ──────────────────────────────────────────────────────────│
│  from entityspine import EntityResolver, Entity            │
│  resolver.resolve("AAPL")                                  │
└────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌────────────────────────────────────────────────────────────┐
│  Layer 2: CLI (Click-based)                                │
│  ──────────────────────────────────────────────────────────│
│  entityspine resolve AAPL                                  │
│  entityspine lookup --cik 0000320193                       │
│  entityspine convert --from ticker --to cik AAPL           │
└────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌────────────────────────────────────────────────────────────┐
│  Layer 3: REST API (FastAPI)                               │
│  ──────────────────────────────────────────────────────────│
│  GET /resolve/{query}                                      │
│  GET /entities/cik/{cik}                                   │
│  POST /batch/resolve                                       │
└────────────────────────────────────────────────────────────┘
```

### 3.3 Python SDK Design (Primary Interface)

#### Option A: yfinance-Style (Entity as Object)

```python
from entityspine import es

# Entity object is the entry point (like yf.Ticker)
entity = es.Entity("AAPL")  # Resolves automatically

# All identifiers accessible
entity.cik           # "0000320193"
entity.ticker        # "AAPL"  
entity.lei           # "549300Q4RLWG85ULYE86"
entity.cusip         # "037833100"
entity.isin          # "US0378331005"
entity.figi          # "BBG000B9XRY4"

# Entity info
entity.name          # "Apple Inc."
entity.type          # "COMPANY"
entity.sic_code      # "3571"
entity.exchange      # "XNAS"

# Historical (point-in-time)
entity.as_of("2020-01-01").ticker  # Ticker at that time

# Multi-entity
entities = es.Entities(["AAPL", "MSFT", "GOOGL"])
entities["AAPL"].cik

# Bulk resolve
results = es.resolve_batch(["AAPL", "MSFT", "Apple Inc"])
```

#### Option B: OpenBB-Style (Namespace Commands)

```python
from entityspine import es

# Command-style with namespaces
es.resolve("AAPL")              # Smart resolve
es.resolve.cik("0000320193")    # By CIK
es.resolve.ticker("AAPL")       # By ticker
es.resolve.name("Apple Inc")    # By name (fuzzy)
es.resolve.isin("US0378331005") # By ISIN

# Identifier conversion
es.convert("AAPL", from_scheme="ticker", to_scheme="cik")
es.convert.ticker_to_cik("AAPL")
es.convert.cik_to_ticker("0000320193")

# Batch operations
es.batch.resolve(["AAPL", "MSFT", "0000320193"])
es.batch.convert(["AAPL", "MSFT"], to_scheme="cik")

# Search
es.search("Apple", limit=10)
es.search.companies("tech", sic_code="35*")
```

#### Option C: pandas-datareader-Style (Unified Reader)

```python
from entityspine import EntityReader

# Unified interface like DataReader
entity = EntityReader("AAPL", source="ticker")
entity = EntityReader("0000320193", source="cik")
entity = EntityReader("Apple Inc", source="name")

# With date range for historical
entity = EntityReader("AAPL", source="ticker", as_of="2020-01-01")

# DataFrame output
from entityspine import entity_lookup
df = entity_lookup(["AAPL", "MSFT"], output="dataframe")
```

### 3.4 Recommended: Hybrid Design

Combining best patterns from all:

```python
from entityspine import EntitySpine

# Initialize (like yfinance's implicit session)
es = EntitySpine()  # Uses default config
es = EntitySpine(cache_dir="./cache")  # Custom config

# ════════════════════════════════════════════════════════════
# PRIMARY: Entity object (yfinance pattern)
# ════════════════════════════════════════════════════════════
entity = es.get("AAPL")  # Smart resolve
entity = es.get("0000320193", scheme="cik")

# All identifiers on the entity object
entity.cik            # "0000320193"
entity.ticker         # "AAPL"
entity.lei            # Optional, may be None
entity.identifiers    # Dict of all: {"cik": "...", "ticker": "...", ...}

# Entity metadata
entity.name           # "Apple Inc."
entity.type           # EntityType.COMPANY
entity.source_system  # "sec"

# ════════════════════════════════════════════════════════════
# RESOLUTION: When you need match confidence (OpenBB pattern)
# ════════════════════════════════════════════════════════════
result = es.resolve("Apple Inc")
result.best           # Best match entity
result.candidates     # List of candidates with scores
result.confidence     # 0.0-1.0
result.is_ambiguous   # True if multiple good matches

# Resolve by specific scheme
result = es.resolve.cik("0000320193")
result = es.resolve.ticker("AAPL", exchange="XNAS")
result = es.resolve.lei("549300Q4RLWG85ULYE86")

# ════════════════════════════════════════════════════════════
# CONVERSION: Identifier translation (Bloomberg pattern)
# ════════════════════════════════════════════════════════════
cik = es.to_cik("AAPL")
ticker = es.to_ticker("0000320193")
lei = es.to_lei("AAPL")

# Bulk conversion
ciks = es.to_cik(["AAPL", "MSFT", "GOOGL"])  # Returns dict

# Full conversion
ids = es.all_identifiers("AAPL")
# Returns: {"cik": "0000320193", "ticker": "AAPL", "lei": "...", ...}

# ════════════════════════════════════════════════════════════
# BATCH: Pipeline operations (pandas-datareader pattern)
# ════════════════════════════════════════════════════════════
entities = es.get_many(["AAPL", "MSFT", "GOOGL"])
# Returns dict: {"AAPL": Entity, "MSFT": Entity, ...}

results = es.resolve_many(["Apple Inc", "Microsoft", "Google"])
# Returns dict with ResolutionResult

df = es.to_dataframe(["AAPL", "MSFT"], columns=["cik", "name", "lei"])
# Returns pandas DataFrame

# ════════════════════════════════════════════════════════════
# SEARCH: Discovery (OpenBB pattern)
# ════════════════════════════════════════════════════════════
results = es.search("tech", limit=20)
results = es.search.by_name("Apple", exact=False)
results = es.search.by_sic("3571")  # Computer equipment

# ════════════════════════════════════════════════════════════
# TEMPORAL: Point-in-time (unique to security master)
# ════════════════════════════════════════════════════════════
entity = es.get("AAPL", as_of="2020-01-01")
ticker = es.to_ticker("0000320193", as_of="2015-06-01")
```

### 3.5 CLI Design (Click-based)

```bash
# ════════════════════════════════════════════════════════════
# RESOLVE: Primary command
# ════════════════════════════════════════════════════════════
entityspine resolve AAPL
# Output:
# Entity: Apple Inc. (0000320193)
# CIK:    0000320193
# Ticker: AAPL (XNAS)
# LEI:    549300Q4RLWG85ULYE86 (not available)

entityspine resolve "Apple Inc" --fuzzy
# Shows multiple candidates with confidence

entityspine resolve 0000320193 --scheme cik

# ════════════════════════════════════════════════════════════
# LOOKUP: Direct by identifier
# ════════════════════════════════════════════════════════════
entityspine lookup --cik 0000320193
entityspine lookup --ticker AAPL
entityspine lookup --lei 549300Q4RLWG85ULYE86

# ════════════════════════════════════════════════════════════
# CONVERT: Identifier translation
# ════════════════════════════════════════════════════════════
entityspine convert AAPL --from ticker --to cik
# Output: 0000320193

entityspine convert AAPL --to all
# Output (JSON):
# {"cik": "0000320193", "ticker": "AAPL", "lei": null, ...}

# Batch convert from file
entityspine convert --file tickers.txt --from ticker --to cik --output ciks.csv

# ════════════════════════════════════════════════════════════
# SEARCH: Discovery
# ════════════════════════════════════════════════════════════
entityspine search "Apple"
entityspine search --sic 3571 --limit 50
entityspine search --name "tech" --type COMPANY

# ════════════════════════════════════════════════════════════
# BATCH: Bulk operations
# ════════════════════════════════════════════════════════════
entityspine batch resolve input.txt --output results.json
entityspine batch convert input.csv --from ticker --to cik --output output.csv

# ════════════════════════════════════════════════════════════
# CACHE: Management
# ════════════════════════════════════════════════════════════
entityspine cache status
entityspine cache refresh
entityspine cache clear

# ════════════════════════════════════════════════════════════
# INFO: System info
# ════════════════════════════════════════════════════════════
entityspine info
entityspine version
entityspine stats  # Entity counts, coverage
```

### 3.6 REST API Design (FastAPI)

```
# ════════════════════════════════════════════════════════════
# RESOLUTION ENDPOINTS
# ════════════════════════════════════════════════════════════

GET /v1/resolve/{query}
    ?scheme=auto|cik|ticker|lei|isin|cusip
    ?as_of=2020-01-01
    
POST /v1/resolve/batch
    Body: {"queries": ["AAPL", "MSFT"], "scheme": "ticker"}

# ════════════════════════════════════════════════════════════
# ENTITY ENDPOINTS (Direct lookup)
# ════════════════════════════════════════════════════════════

GET /v1/entities/{entity_id}
GET /v1/entities/cik/{cik}
GET /v1/entities/ticker/{ticker}?exchange={mic}
GET /v1/entities/lei/{lei}
GET /v1/entities/isin/{isin}
GET /v1/entities/cusip/{cusip}
GET /v1/entities/figi/{figi}

# ════════════════════════════════════════════════════════════
# IDENTIFIER CONVERSION
# ════════════════════════════════════════════════════════════

GET /v1/convert/{value}
    ?from=ticker
    ?to=cik
    ?as_of=2020-01-01

GET /v1/identifiers/{entity_id}
    # Returns all identifiers for an entity

POST /v1/convert/batch
    Body: {"values": [...], "from": "ticker", "to": "cik"}

# ════════════════════════════════════════════════════════════
# SEARCH ENDPOINTS
# ════════════════════════════════════════════════════════════

GET /v1/search?q=Apple&limit=20
GET /v1/search/companies?name=tech&sic=35*

# ════════════════════════════════════════════════════════════
# SYSTEM ENDPOINTS
# ════════════════════════════════════════════════════════════

GET /v1/health
GET /v1/info
GET /v1/stats
```

### 3.7 Response Format (Consistent Across All)

```python
# Python SDK returns Entity objects
entity = es.get("AAPL")
# Entity(entity_id="01ABC...", primary_name="Apple Inc.", ...)

# CLI outputs formatted text or JSON
entityspine resolve AAPL --format json
# {"entity_id": "01ABC...", "name": "Apple Inc.", "identifiers": {...}}

# REST API returns JSON
# GET /v1/resolve/AAPL
{
    "entity_id": "01ABC...",
    "primary_name": "Apple Inc.",
    "entity_type": "COMPANY",
    "identifiers": {
        "cik": "0000320193",
        "ticker": "AAPL",
        "lei": "549300Q4RLWG85ULYE86",
        "isin": null,
        "cusip": null
    },
    "resolution": {
        "query": "AAPL",
        "confidence": 1.0,
        "match_reason": "EXACT_TICKER"
    }
}
```

---

## 4. Sync Strategy: Keep All Access Points Consistent

### 4.1 Single Source of Truth

```
┌─────────────────────────────────────────┐
│     entityspine/core/resolver.py        │  ← Single implementation
│     EntityResolver.resolve()            │
│     EntityResolver.get_by_cik()         │
│     EntityResolver.convert()            │
└─────────────────────────────────────────┘
          │           │           │
          ▼           ▼           ▼
    ┌─────────┐ ┌─────────┐ ┌─────────┐
    │ Python  │ │   CLI   │ │  REST   │
    │   SDK   │ │(wrapper)│ │(wrapper)│
    └─────────┘ └─────────┘ └─────────┘
```

### 4.2 Naming Convention Alignment

| Operation | Python SDK | CLI | REST API |
|-----------|------------|-----|----------|
| Smart resolve | `es.get("AAPL")` | `resolve AAPL` | `GET /resolve/AAPL` |
| By CIK | `es.get("...", scheme="cik")` | `lookup --cik ...` | `GET /entities/cik/...` |
| Convert | `es.to_cik("AAPL")` | `convert AAPL --to cik` | `GET /convert/AAPL?to=cik` |
| Batch | `es.get_many([...])` | `batch resolve ...` | `POST /resolve/batch` |
| Search | `es.search("Apple")` | `search "Apple"` | `GET /search?q=Apple` |

### 4.3 Implementation Priority

1. **Phase 1**: Python SDK (primary, fully featured)
2. **Phase 2**: CLI (wraps SDK, Click-based)
3. **Phase 3**: REST API (wraps SDK, FastAPI)

All three share:
- Same resolver core
- Same response models
- Same validation logic
- Same error handling

---

## 5. Comparison: Current vs Proposed

| Feature | Current | Proposed |
|---------|---------|----------|
| Python entry point | `EntityResolver()` | `EntitySpine()` with shortcuts |
| Get entity | `resolver.resolve("AAPL")` | `es.get("AAPL")` |
| Get by CIK | `resolver.resolve_cik(...)` | `es.get(..., scheme="cik")` |
| Convert identifiers | `resolver.convert(...)` (broken) | `es.to_cik(...)`, `es.all_identifiers(...)` |
| Batch | `resolver.resolve_batch(...)` | `es.get_many(...)`, `es.resolve_many(...)` |
| CLI | ❌ None | `entityspine resolve/lookup/convert/search` |
| REST Response | Entity-only | Entity + all identifiers + resolution metadata |

---

## 6. Next Steps

1. **Review and approve design** - Choose between Options A/B/C or the hybrid
2. **Implement Python SDK** - Primary interface first
3. **Implement CLI** - Click-based, wraps SDK
4. **Update REST API** - Align with SDK patterns
5. **Document all interfaces** - OpenAPI spec, CLI help, SDK docstrings

---

## Appendix: py-sec-edgar Integration

### How py-sec-edgar Uses EntitySpine

```python
# In py_sec_edgar/core/identity.py

from entityspine import EntitySpine

_es: EntitySpine | None = None

def get_entity_spine() -> EntitySpine:
    global _es
    if _es is None:
        _es = EntitySpine()
    return _es

def resolve_cik(identifier: str) -> str | None:
    """Resolve any identifier to CIK (for SEC API calls)."""
    return get_entity_spine().to_cik(identifier)

def resolve_ticker(identifier: str) -> str | None:
    """Resolve any identifier to ticker."""
    entity = get_entity_spine().get(identifier)
    return entity.ticker if entity else None
```

### CLI Integration

```bash
# py-sec-edgar CLI could delegate to entityspine CLI
py-sec-edgar company lookup AAPL
# → internally calls: entityspine resolve AAPL
```

This keeps py-sec-edgar focused on SEC filings while delegating entity resolution to EntitySpine.
