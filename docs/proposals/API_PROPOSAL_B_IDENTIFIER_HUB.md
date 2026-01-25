# Proposal B: Identifier Hub API Design

**Focus:** Position API as an "Identifier Resolution Hub" - the single source of truth for mapping between any financial identifiers.

---

## Philosophy

Instead of separate entity/security/listing endpoints, treat the API as a **universal identifier translator**. Users don't care about internal hierarchies - they want to:

1. Input any identifier they have
2. Get back any identifier they need
3. Optionally get metadata

This is how Bloomberg Terminal, Refinitiv, and FactSet APIs work.

---

## Proposed Endpoint Structure

```
/api/v1/
├── resolve/                     # Primary endpoint
│   ├── {identifier}             # Smart resolution
│   └── batch                    # Batch resolution
│
├── lookup/                      # Direct lookups by scheme
│   ├── cik/{value}
│   ├── ticker/{value}
│   ├── cusip/{value}
│   ├── isin/{value}
│   ├── lei/{value}
│   ├── figi/{value}
│   └── sedol/{value}
│
├── convert/                     # Identifier conversion
│   └── ?value=X&from=A&to=B
│
├── search/                      # Unified search
│   └── ?q=apple&type=company
│
└── health/
    └── (health check)
```

---

## Key Features

### 1. Universal Resolution Response

Every resolution returns ALL known identifiers:

```
GET /api/v1/resolve/AAPL

Response:
{
  "query": "AAPL",
  "status": "found",
  "confidence": 1.0,
  
  "identifiers": {
    "cik": "0000320193",
    "lei": "HWUPKR0MPOU8FGXBT394",
    "cusip": "037833100",
    "isin": "US0378331005",
    "figi": "BBG000B9XRY4",
    "sedol": "2046251",
    "ticker": "AAPL",
    "permid": "4295905573"
  },
  
  "metadata": {
    "name": "Apple Inc.",
    "type": "company",
    "country": "US",
    "sector": "Technology",
    "exchange": "NASDAQ"
  },
  
  "links": {
    "sec_filings": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0000320193",
    "openfigi": "https://www.openfigi.com/id/BBG000B9XRY4"
  }
}
```

### 2. Conversion as Primary Use Case

```
GET /api/v1/convert?value=AAPL&from=ticker&to=cusip,isin,cik

Response:
{
  "input": {"scheme": "ticker", "value": "AAPL"},
  "output": {
    "cusip": "037833100",
    "isin": "US0378331005",
    "cik": "0000320193"
  },
  "resolved_name": "Apple Inc."
}
```

### 3. Batch Conversion (Pipeline Friendly)

```
POST /api/v1/convert/batch
{
  "from": "ticker",
  "to": ["cusip", "cik"],
  "values": ["AAPL", "MSFT", "GOOGL", "AMZN"]
}

Response:
{
  "results": {
    "AAPL": {"cusip": "037833100", "cik": "0000320193"},
    "MSFT": {"cusip": "594918104", "cik": "0000789019"},
    "GOOGL": {"cusip": "02079K305", "cik": "0001652044"},
    "AMZN": {"cusip": "023135106", "cik": "0001018724"}
  },
  "resolved": 4,
  "failed": 0
}
```

### 4. Scheme-Aware Lookups

```
GET /api/v1/lookup/cusip/037833100

Response:
{
  "scheme": "cusip",
  "value": "037833100",
  "valid": true,
  "check_digit_valid": true,
  
  "identifiers": {
    "cik": "0000320193",
    "isin": "US0378331005",
    "ticker": "AAPL",
    ...
  },
  
  "metadata": {
    "name": "Apple Inc.",
    "security_type": "common_stock"
  }
}
```

---

## Pros

- ✅ Simple mental model: "give me X, get back Y"
- ✅ Matches how traders/analysts actually think
- ✅ Perfect for data pipeline integration
- ✅ Fewer endpoints to remember
- ✅ Response always includes all identifiers (no follow-up calls)

## Cons

- ❌ Flattens the Entity/Security/Listing distinction
- ❌ May return incomplete data if not all identifiers are known
- ❌ Harder to represent complex cases (same ticker, different exchanges)

---

## Implementation Effort

| Component | Effort | Notes |
|-----------|--------|-------|
| Refactor `/resolve` response | Low | Add identifiers dict |
| `/lookup/{scheme}/{value}` | Low | 7 routes, same underlying logic |
| `/convert` endpoint | Low | Wrapper around resolve |
| Batch conversion | Low | Loop over resolve |
| Identifier aggregation | Medium | Collect all IDs for an entity |

**Total: ~1-2 days**
