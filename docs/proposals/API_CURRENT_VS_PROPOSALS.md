# EntitySpine API: Current State vs Proposals

## What's Currently Implemented

The existing API (created earlier today) has these endpoints:

| Endpoint | Method | Status | Notes |
|----------|--------|--------|-------|
| `/health` | GET | ✅ Exists | Basic health check |
| `/info` | GET | ✅ Exists | API info |
| `/resolve/{query}` | GET | ✅ Exists | Basic resolve (returns Entity only) |
| `/resolve/batch` | POST | ✅ Exists | Batch resolution |
| `/entities/cik/{cik}` | GET | ✅ Exists | CIK lookup |
| `/entities/ticker/{ticker}` | GET | ✅ Exists | Ticker lookup (returns Entity) |
| `/entities/{entity_id}` | GET | ✅ Exists | Entity by ID |
| `/search` | GET | ✅ Exists | Basic search |
| `/convert` | GET | ✅ Exists | **Incomplete** - only CIK conversion works |

### Current Limitations

1. **Entity-only responses** - Resolution returns just the Entity, not Security/Listing chain
2. **No CUSIP/ISIN/FIGI lookups** - Only CIK/ticker endpoints exist
3. **No Security endpoints** - `/securities/*` doesn't exist
4. **No Listing endpoints** - `/listings/*` doesn't exist
5. **No identifier aggregation** - Response doesn't include all known identifiers
6. **Conversion is broken** - Only ticker→CIK partially works
7. **No temporal support** - `as_of` parameter exists but ignored in response

---

## Gap Analysis by Proposal

### Proposal A: Security-Centric

| Feature | Current | Proposal A | Gap |
|---------|---------|------------|-----|
| `/securities/*` endpoints | ❌ | ✅ | **New** |
| `/listings/*` endpoints | ❌ | ✅ | **New** |
| `/crosswalk` endpoint | ❌ | ✅ | **New** |
| `?expand=full` on resolve | ❌ | ✅ | **New** |
| Entity→Securities drill-down | ❌ | ✅ | **New** |

### Proposal B: Identifier Hub

| Feature | Current | Proposal B | Gap |
|---------|---------|------------|-----|
| Return ALL identifiers in response | ❌ | ✅ | **Enhance** |
| `/lookup/{scheme}/{value}` | Partial | ✅ | Need CUSIP/ISIN/LEI/FIGI |
| `/convert` with multiple outputs | ❌ | ✅ | **Enhance** |
| Batch conversion | ❌ | ✅ | **New** |

### Proposal C: Hybrid Security Master

| Feature | Current | Proposal C | Gap |
|---------|---------|------------|-----|
| `/instruments/*` endpoints | ❌ | ✅ | **New** |
| Temporal `?as_of` honored | ❌ | ✅ | **Enhance** |
| Entity history | ❌ | ✅ | **New** |
| Corporate actions | ❌ | ✅ | **New** |
| `/mappings` endpoint | ❌ | ✅ | **New** |

---

## Recommendation

**Start with Proposal B (Identifier Hub)** because:

1. ✅ Smallest delta from current implementation
2. ✅ Immediately useful for data pipelines  
3. ✅ Can be built in 1-2 days
4. ✅ Doesn't require new data sources

Then layer on Proposal C features (temporal, history) as a Phase 2.

### Minimal Changes Needed for Proposal B

1. **Enhance `ResolutionResponse`** to include `identifiers` dict with all known IDs
2. **Add `/lookup/{scheme}/{value}`** routes for CUSIP, ISIN, LEI, FIGI, SEDOL
3. **Fix `/convert`** to support multiple output schemes
4. **Add `/convert/batch`** for pipeline use cases

---

## Decision Matrix

| Criteria | Proposal A | Proposal B | Proposal C |
|----------|------------|------------|------------|
| Effort to implement | 2-3 days | **1-2 days** | 1 week |
| Immediate value | Medium | **High** | High |
| Data requirements | Need Security/Listing data | **Existing data works** | Need historical data |
| API complexity | High (many endpoints) | **Low (few endpoints)** | Medium |
| Matches user mental model | Hierarchical | **Flat/simple** | Mixed |

**Winner: Proposal B** for Phase 1, with Proposal C features in Phase 2.
