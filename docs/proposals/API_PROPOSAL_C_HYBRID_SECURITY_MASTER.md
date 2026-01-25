# Proposal C: Hybrid Security Master API

**Focus:** Keep Entity-centric core but add Security Master "views" and temporal capabilities.

---

## Philosophy

Combine the best of both worlds:
1. **Entity Master Core** - Companies/organizations as the anchor
2. **Security Master Views** - Security-focused projections of the data
3. **Temporal Queries** - Historical lookups ("what was X on date Y?")
4. **Corporate Actions** - Track splits, mergers, ticker changes

This mirrors how institutional data vendors work: entity as the "golden record" with securities as attributes.

---

## Proposed Endpoint Structure

```
/api/v1/
├── resolve/                     # Smart resolution (keep existing)
│   ├── {query}
│   ├── {query}?as_of=2020-01-01 # Temporal
│   └── batch
│
├── entities/                    # Entity Master (enhanced)
│   ├── {id}
│   ├── {id}/identifiers         # All identifiers for entity
│   ├── {id}/securities          # Securities issued by entity
│   ├── {id}/history             # Name changes, mergers
│   ├── cik/{cik}
│   ├── lei/{lei}
│   └── search
│
├── instruments/                 # Security Master View
│   ├── {query}                  # Resolve to instrument
│   ├── cusip/{cusip}
│   ├── isin/{isin}
│   ├── figi/{figi}
│   ├── ticker/{ticker}
│   ├── ticker/{ticker}?mic={mic}
│   └── search
│
├── corporate-actions/           # Track changes over time
│   ├── entity/{entity_id}
│   ├── ticker/{ticker}
│   └── recent?days=30
│
└── mappings/                    # Identifier mappings
    ├── ?input=AAPL&output=cusip,cik
    └── batch
```

---

## Key Features

### 1. Instrument View (Security Master Projection)

```
GET /api/v1/instruments/AAPL

Response:
{
  "instrument_type": "equity",
  "name": "Apple Inc. Common Stock",
  
  "identifiers": {
    "cusip": "037833100",
    "isin": "US0378331005",
    "figi": "BBG000B9XRY4",
    "sedol": "2046251"
  },
  
  "listings": [
    {"ticker": "AAPL", "exchange": "NASDAQ", "mic": "XNAS", "primary": true},
    {"ticker": "AAPL", "exchange": "NYSE", "mic": "XNYS", "primary": false}
  ],
  
  "issuer": {
    "entity_id": "...",
    "name": "Apple Inc.",
    "cik": "0000320193",
    "country": "US"
  },
  
  "metadata": {
    "currency": "USD",
    "lot_size": 1,
    "status": "active"
  }
}
```

### 2. Temporal Resolution

```
GET /api/v1/resolve/FB?as_of=2021-01-01

Response:
{
  "query": "FB",
  "as_of": "2021-01-01",
  "as_of_honored": true,
  
  "entity": {
    "name": "Facebook, Inc.",  # Before Meta rebrand
    "cik": "0001326801"
  },
  
  "note": "Entity renamed to 'Meta Platforms, Inc.' on 2021-10-28"
}
```

### 3. Corporate Actions Feed

```
GET /api/v1/corporate-actions/recent?days=30

Response:
{
  "period": {"start": "2025-12-27", "end": "2026-01-26"},
  "actions": [
    {
      "type": "ticker_change",
      "entity": "Meta Platforms, Inc.",
      "old_ticker": "FB",
      "new_ticker": "META",
      "effective_date": "2022-06-09"
    },
    {
      "type": "stock_split",
      "entity": "Amazon.com, Inc.",
      "ticker": "AMZN",
      "ratio": "20:1",
      "effective_date": "2022-06-06"
    },
    {
      "type": "name_change",
      "entity_id": "...",
      "old_name": "Facebook, Inc.",
      "new_name": "Meta Platforms, Inc.",
      "effective_date": "2021-10-28"
    }
  ]
}
```

### 4. Entity History

```
GET /api/v1/entities/{id}/history

Response:
{
  "entity_id": "...",
  "current_name": "Meta Platforms, Inc.",
  
  "timeline": [
    {"date": "2004-02-04", "event": "founded", "name": "TheFacebook, Inc."},
    {"date": "2005-09-20", "event": "name_change", "name": "Facebook, Inc."},
    {"date": "2012-05-18", "event": "ipo", "ticker": "FB", "exchange": "NASDAQ"},
    {"date": "2021-10-28", "event": "name_change", "name": "Meta Platforms, Inc."},
    {"date": "2022-06-09", "event": "ticker_change", "old": "FB", "new": "META"}
  ]
}
```

### 5. Identifier Mappings (Crosswalk)

```
GET /api/v1/mappings?input=AAPL&output=cusip,isin,cik

Response:
{
  "input": {"type": "ticker", "value": "AAPL"},
  "mappings": {
    "cusip": {"value": "037833100", "confidence": 1.0},
    "isin": {"value": "US0378331005", "confidence": 1.0},
    "cik": {"value": "0000320193", "confidence": 1.0}
  },
  "entity_name": "Apple Inc."
}
```

---

## Pros

- ✅ Preserves Entity/Security/Listing model integrity
- ✅ Adds Security Master "view" without restructuring
- ✅ Temporal queries for historical research
- ✅ Corporate actions tracking is high-value feature
- ✅ Gradual enhancement path (can add features incrementally)

## Cons

- ❌ More complex than Proposal B
- ❌ Corporate actions requires additional data sources
- ❌ Temporal data requires significant storage/indexing
- ❌ Two ways to access similar data (entities vs instruments)

---

## Implementation Phases

### Phase 1: Core (2 days)
- `/instruments/{query}` endpoint
- `/instruments/cusip/{cusip}`, etc.
- `/mappings` endpoint

### Phase 2: Temporal (2 days)
- `?as_of` parameter on resolve
- Entity history endpoint
- Ticker change tracking

### Phase 3: Corporate Actions (3 days)
- Corporate actions data model
- `/corporate-actions/*` endpoints
- Recent changes feed

**Total: ~1 week for full implementation**

---

## Recommended Starting Point

Start with Phase 1 only:
```
/api/v1/instruments/     # Security Master view
/api/v1/mappings/        # Identifier crosswalk
```

This gives immediate Security Master value without the complexity of temporal/corporate actions.
