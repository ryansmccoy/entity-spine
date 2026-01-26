# EntitySpine Examples

This directory contains integration examples demonstrating how EntitySpine works with SEC EDGAR data and produces a Knowledge Graph.

## Overview

EntitySpine is the **entity resolution and knowledge graph** layer designed to integrate with:
- **FeedSpine** - SEC filing extraction pipeline
- **py-sec-edgar** - SEC EDGAR filing collection

## Examples

### 01_end_to_end_sec_filing_to_kg.py

**The canonical integration proof** showing the complete data flow:

```
SEC EDGAR JSON → SqliteStore → Entity Resolution → KG Nodes/Edges
```

#### What It Demonstrates

| Section | Description |
|---------|-------------|
| **A) Tier 1 Setup** | Load SEC company_tickers JSON into SqliteStore |
| **B) Filing Facts Ingestion** | Parse mock 10-K payload into KG nodes |
| **C) Tier Honesty** | Show `as_of` warnings when tier can't honor |
| **D) KG Summary** | Query counts, relationships, and assets |

#### Running the Example

```bash
# From repository root
cd entityspine
python examples/01_end_to_end_sec_filing_to_kg.py
```

#### Expected Output

```
======================================================================
 EntitySpine v2.2.4 - End-to-End Integration Proof
 SEC Filing → Knowledge Graph (stdlib-only)
======================================================================

======================================================================
 A) TIER 1 SETUP: Load SEC Sample Tickers
======================================================================
✓ Loaded 10 entities from SEC JSON
  - Entity count: 10
  - Security count: 10
  - Listing count: 10
  - Claim count: 20

--- Basic Resolution Examples ---
  resolve('AAPL') → Apple Inc. (entity_id=01HYZ...)
  resolve('0000320193') → Apple Inc.
  search('Apple Inc.') → Apple Inc. (score=1.0)

...

======================================================================
 ✓ END-TO-END INTEGRATION PROOF COMPLETE
======================================================================

  EntitySpine is ready to integrate with FeedSpine / py-sec-edgar!
```

---

## Fixtures

### `fixtures/sec_company_tickers_sample.json`

Sample SEC company tickers in the official SEC JSON format.

**Schema:**
```json
{
  "0": {
    "cik_str": 320193,
    "ticker": "AAPL",
    "title": "Apple Inc."
  }
}
```

**Contains:** 10 companies (AAPL, MSFT, AMZN, GOOGL, META, NVDA, IBM, GS, BRK.B, CVX)

### `fixtures/mock_filing_facts_10k.json`

Mock 10-K filing facts payload representing what FeedSpine would extract.

**Schema:**

```json
{
  "filing_metadata": {
    "filing_id": "0000320193-24-000123",
    "form_type": "10-K",
    "filing_date": "2024-01-15",
    "period_end": "2023-12-31"
  },
  
  "issuer": {
    "cik": "0000320193",
    "name": "Apple Inc."
  },
  
  "officers": [
    {
      "person_id": "person_tim_cook",
      "name": "Timothy D. Cook",
      "role_type": "ceo",
      "title": "Chief Executive Officer",
      "start_date": "2011-08-24",
      "evidence": {
        "section_id": "10K_PART_I_ITEM_1",
        "snippet": "Timothy D. Cook has served as Chief Executive Officer..."
      }
    }
  ],
  
  "directors": [...],
  
  "headquarters": {
    "line1": "One Apple Park Way",
    "city": "Cupertino",
    "region": "CA",
    "postal": "95014",
    "country": "US"
  },
  
  "geo_hierarchy": [
    {"geo_id": "geo_us", "name": "United States", "geo_type": "country"},
    {"geo_id": "geo_ca", "name": "California", "geo_type": "state", "parent_geo_id": "geo_us"},
    {"geo_id": "geo_cupertino", "name": "Cupertino", "geo_type": "city", "parent_geo_id": "geo_ca"}
  ],
  
  "material_contracts": [...],
  "products": [...],
  "brands": [...],
  "assets": [...],
  "events": [...],
  "relationships": [...]
}
```

---

## Integration Contract

### FeedSpine → EntitySpine Payload

FeedSpine extracts SEC filings and produces JSON payloads following the schema above.

**Key Points:**
1. **filing_id** follows SEC format: `{CIK}-{YY}-{ACCESSION}`
2. **person_id** is a temporary key for linking roles within the payload
3. **geo_id** follows pattern: `geo_{name_lowercase}`
4. **relationships** use `source_ref` / `target_ref` to link entities

### EntitySpine → py-sec-edgar API

```python
from entityspine.stores import SqliteStore
from entityspine.domain import Entity, RoleAssignment, Relationship

# Initialize store
store = SqliteStore("path/to/entityspine.db")
store.initialize()

# Load SEC tickers (run once)
store.load_sec_json(sec_tickers_data)

# Resolve entity by CIK
entities = store.get_entities_by_cik("320193")
apple = entities[0] if entities else None

# Ingest filing facts
store.save_role_assignment(role)
store.save_relationship(relationship)
store.save_event(event)

# Query KG
assets = store.get_assets_by_owner(apple.entity_id)
roles = store.get_role_assignments_by_org(apple.entity_id)
```

---

## Requirements

- Python 3.10+
- EntitySpine core only (no external dependencies)

The example script uses **only stdlib + entityspine core**:
- `json`, `datetime`, `decimal`, `pathlib` (stdlib)
- `entityspine.domain` (stdlib dataclasses)
- `entityspine.stores.SqliteStore` (stdlib sqlite3)

---

## Node Types

| Type | Description | Store Method |
|------|-------------|--------------|
| Entity | Companies, people, government agencies | `save_entity()` |
| Security | Stock, bond, option | `save_security()` |
| Listing | Ticker on exchange | `save_listing()` |
| Claim | Identifier (CIK, LEI, CUSIP) | `save_claim()` |
| Geo | Country, state, city | `save_geo()` |
| Address | Physical location | `save_address()` |
| RoleAssignment | Person→Org role (CEO, Director) | `save_role_assignment()` |
| Asset | Real estate, equipment | `save_asset()` |
| Contract | Material agreements | `save_contract()` |
| Product | Goods sold | `save_product()` |
| Brand | Trademarked names | `save_brand()` |
| Event | M&A, legal, regulatory | `save_event()` |
| Relationship | Generic NodeRef→NodeRef edge | `save_relationship()` |

---

## Tier Honesty

EntitySpine implements a tiered resolution architecture:

| Tier | Store | Capabilities | Limitations |
|------|-------|--------------|-------------|
| **Tier 1** | SqliteStore | Basic lookup, KG CRUD | No temporal queries |
| **Tier 2** | PostgresStore | Full temporal, versioning | Requires Postgres |
| **Tier 3** | ResolutionService | Fuzzy matching, ML | Requires ML models |

When Tier 1 is asked for capabilities it can't provide (e.g., `as_of` queries), it returns data with warnings:

```python
result = found_result(entity, query="AAPL", tier=ResolutionTier.TIER_1, as_of=date(2015,1,1))
result.as_of_honored = False
result.add_as_of_ignored_warning()
# warnings = ["as_of parameter ignored: Tier 1 store does not support temporal queries"]
```

---

## Next Steps

1. **Run the example** to verify EntitySpine works correctly
2. **Integrate with FeedSpine** to produce real filing payloads
3. **Connect to py-sec-edgar** for bulk filing collection
4. **Upgrade to Tier 2** for temporal queries (optional)
