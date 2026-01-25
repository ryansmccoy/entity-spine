# Proposal A: Security-Centric API Design

**Focus:** Elevate Securities and Listings as first-class API citizens alongside Entities.

---

## Philosophy

A true Security Master needs to answer questions like:
- "What securities does Apple have?" (Common stock, bonds, preferred shares)
- "Where is AAPL traded?" (NASDAQ, various exchanges)
- "What entity owns CUSIP 037833100?"
- "What was the ticker for Facebook before the Meta rebrand?"

The current API is Entity-centric (resolve → Entity). This proposal adds parallel paths for Securities and Listings.

---

## Proposed Endpoint Structure

```
/api/v1/
├── entities/                    # Entity Master (existing)
│   ├── {id}
│   ├── cik/{cik}
│   ├── lei/{lei}
│   └── search
│
├── securities/                  # NEW: Security Master
│   ├── {id}                     # Get security by ID
│   ├── cusip/{cusip}            # Lookup by CUSIP
│   ├── isin/{isin}              # Lookup by ISIN
│   ├── figi/{figi}              # Lookup by FIGI
│   ├── sedol/{sedol}            # Lookup by SEDOL
│   ├── entity/{entity_id}       # All securities for an entity
│   └── search                   # Search securities
│
├── listings/                    # NEW: Exchange Listings
│   ├── {id}                     # Get listing by ID
│   ├── ticker/{ticker}          # Lookup by ticker
│   ├── ticker/{ticker}?mic={mic} # Ticker + exchange
│   ├── security/{security_id}   # All listings for a security
│   └── search                   # Search listings
│
├── resolve/                     # Smart Resolution (enhanced)
│   ├── {query}                  # Auto-detect and resolve
│   ├── {query}?target=entity    # Force entity resolution
│   ├── {query}?target=security  # Force security resolution
│   ├── {query}?target=listing   # Force listing resolution
│   └── batch                    # Batch resolution
│
└── crosswalk/                   # NEW: Identifier Crosswalk
    ├── ?from=ticker&to=cusip&value=AAPL
    └── batch                    # Batch conversion
```

---

## Key Features

### 1. Full Security Resolution Chain

```
GET /api/v1/resolve/AAPL?expand=full

Response:
{
  "query": "AAPL",
  "resolution_path": "ticker → listing → security → entity",
  "listing": {
    "listing_id": "...",
    "ticker": "AAPL",
    "mic": "XNAS",
    "exchange_name": "NASDAQ"
  },
  "security": {
    "security_id": "...",
    "security_type": "common_stock",
    "cusip": "037833100",
    "isin": "US0378331005",
    "figi": "BBG000B9XRY4"
  },
  "entity": {
    "entity_id": "...",
    "primary_name": "Apple Inc.",
    "cik": "0000320193",
    "lei": "HWUPKR0MPOU8FGXBT394"
  }
}
```

### 2. Entity → Securities → Listings Drill-Down

```
GET /api/v1/entities/cik/320193/securities

Response:
{
  "entity": {"entity_id": "...", "primary_name": "Apple Inc."},
  "securities": [
    {
      "security_id": "...",
      "security_type": "common_stock",
      "name": "Apple Inc. Common Stock",
      "cusip": "037833100",
      "listings": [
        {"ticker": "AAPL", "mic": "XNAS", "status": "active"},
        {"ticker": "AAPL", "mic": "XNYS", "status": "active"}
      ]
    },
    {
      "security_id": "...",
      "security_type": "corporate_bond",
      "name": "Apple Inc. 3.25% Notes 2026",
      "cusip": "037833CU5"
    }
  ]
}
```

### 3. Identifier Crosswalk

```
GET /api/v1/crosswalk?from=ticker&to=cusip&value=AAPL

Response:
{
  "from": {"scheme": "ticker", "value": "AAPL"},
  "to": {"scheme": "cusip", "value": "037833100"},
  "confidence": 1.0,
  "via": ["listing", "security"]
}
```

---

## Pros

- ✅ Complete security master functionality
- ✅ Supports multiple security types (stocks, bonds, etc.)
- ✅ Clear separation: Entity vs Security vs Listing
- ✅ Identifier crosswalk is a killer feature for data pipelines

## Cons

- ❌ More complex API surface (more endpoints to maintain)
- ❌ Requires full Security/Listing data population
- ❌ May be overkill if primary use is just CIK/ticker resolution

---

## Implementation Effort

| Component | Effort | Notes |
|-----------|--------|-------|
| `/securities/*` endpoints | Medium | New routes, uses existing domain models |
| `/listings/*` endpoints | Medium | New routes, uses existing domain models |
| `/crosswalk` endpoint | Low | Leverages existing resolution logic |
| Expand `?expand=full` | Low | Add to existing resolve endpoint |
| Data population | High | Need SEC data for securities/listings |

**Total: ~2-3 days**
