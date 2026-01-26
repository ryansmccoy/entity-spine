# EntitySpine Tier Capabilities and Limits (v2.2)

**Status**: Normative  
**Audience**: Implementers, API consumers

---

## Table of Contents

1. [Overview](#overview)
2. [Capability Matrix](#capability-matrix)
3. [Data Source Realities](#data-source-realities)
4. [Resolution Behavior by Tier](#resolution-behavior-by-tier)
5. [ResolutionResult Limits & Warnings](#resolutionresult-limits--warnings)
6. [Upgrading Tiers](#upgrading-tiers)
7. [Decision Log](#decision-log)
8. [Known Limitations / Open Questions](#known-limitations--open-questions)

---

## Overview

EntitySpine supports multiple storage tiers with different capabilities. This document is **the truth** about what each tier can and cannot do. When code or documentation elsewhere conflicts with this document, **this document wins**.

### The Core Principle

> **Be honest about what we don't know.**  
> If historical data isn't available, say so in the result—don't silently return today's data as if it were 1995's.

---

## Capability Matrix

| Capability | Tier 0 (JSON) | Tier 1 (SQLite) | Tier 2 (DuckDB) | Tier 3 (PostgreSQL) |
|------------|---------------|-----------------|-----------------|---------------------|
| **Data Source** | SEC JSON only | SEC JSON + local | SEC + external | Multi-vendor |
| **Dependencies** | None (stdlib) | None (stdlib) | `duckdb` | `asyncpg`/`psycopg` |
| **Entity resolution by CIK** | ✅ Exact | ✅ Exact | ✅ Exact | ✅ Exact |
| **Entity resolution by name** | ✅ Exact only | ✅ + Fuzzy (LIKE) | ✅ + FTS | ✅ + FTS + trigram |
| **Ticker → Entity** | ⚠️ Current only | ⚠️ Current only* | ⚠️ Current only* | ✅ Historical |
| **Point-in-time (`as_of`)** | ❌ Not supported | ⚠️ Best-effort** | ⚠️ Best-effort** | ✅ Full support |
| **MIC (exchange) filtering** | ❌ No MIC data | ❌ No MIC data* | ⚠️ If populated | ✅ Full support |
| **Merge redirects** | ❌ No merge data | ✅ Supported | ✅ Supported | ✅ + audit trail |
| **Claims with provenance** | ⚠️ Implicit*** | ✅ Supported | ✅ Supported | ✅ + conflicts |
| **Multi-vendor crosswalks** | ❌ SEC only | ❌ SEC only | ⚠️ Manual | ✅ Full support |
| **Concurrent writes** | ❌ Read-only | ⚠️ Single writer | ⚠️ Single writer | ✅ Multi-writer |
| **Person entities** | ❌ No schema | ✅ Schema only | ✅ Supported | ✅ Full support |
| **Role assignments** | ❌ No schema | ✅ Schema only | ✅ Supported | ✅ + temporal |
| **Entity relationships** | ❌ No schema | ✅ Schema only | ✅ Supported | ✅ + temporal |
| **Cases/Proceedings** | ❌ No schema | ✅ Schema only | ✅ Supported | ✅ Full support |
| **Address normalization** | ❌ Not available | ✅ Hash-based | ✅ Hash-based | ✅ + fuzzy match |
| **Geographic (Geo) nodes** | ❌ No schema | ✅ Schema only | ✅ Supported | ✅ Full support |

**Legend**:
- ✅ = Fully supported and guaranteed
- ⚠️ = Partial/best-effort (see notes)
- ❌ = Not supported

### Notes

\* **Tier 1 historical resolution**: SQLite schema supports `valid_from`/`valid_to` on listings, but SEC JSON doesn't provide this data. Unless you manually populate validity windows, all listings are treated as "current".

\** **Best-effort as_of**: If `valid_from`/`valid_to` are NULL or unpopulated, the resolver returns current listings with a warning in `ResolutionResult.warnings`.

\*** **Tier 0 implicit claims**: SEC JSON is the only source, so all identifiers implicitly have `source_system='sec'`, `confidence=1.0`. No explicit claims table exists.

---

## Data Source Realities

### SEC company_tickers.json

The SEC provides `https://www.sec.gov/files/company_tickers.json` with this structure:

```json
{
  "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
  "1": {"cik_str": 789019, "ticker": "MSFT", "title": "MICROSOFT CORP"}
}
```

**What SEC JSON provides**:
- CIK (Central Index Key)
- Current ticker (as of today)
- Current company name

**What SEC JSON does NOT provide**:
- MIC (Market Identifier Code) - we don't know if AAPL is XNAS or XNYS
- Validity windows - we don't know when AAPL started trading
- Historical tickers - only current mapping
- LEI, ISIN, CUSIP, FIGI, or any other identifiers
- Merge history - if companies merged, we don't know

### Implications for Resolution

```python
# This is HONEST behavior for Tier 0-1:

result = resolver.resolve_ticker("AAPL", as_of=date(1990, 1, 1))

# Returns candidates but with warnings:
assert result.warnings == [
    "as_of parameter ignored: listing validity data not available in Tier 0-1",
]
assert result.limits == {
    "temporal_resolution": "current_only",
    "mic_filtering": "not_available",
}
```

---

## Resolution Behavior by Tier

### Tier 0: JSON (Zero Dependencies)

```python
# What works
result = resolver.resolve_cik("320193")       # ✅ Exact CIK match
result = resolver.resolve("Apple Inc.")       # ✅ Exact name match (case-insensitive)
result = resolver.resolve("AAPL")             # ⚠️ Returns current mapping only

# What doesn't work (should warn, not silently succeed)
result = resolver.resolve_ticker("AAPL", as_of=date(1990, 1, 1))
# ⚠️ Returns current AAPL with warning: "as_of not supported in Tier 0"

result = resolver.resolve_ticker("AAPL", mic="XNAS")
# ⚠️ Ignores mic, returns current AAPL with warning: "mic filtering not available"
```

### Tier 1: SQLite (Zero Dependencies)

```python
# Schema supports temporal data, but SEC JSON doesn't provide it
# Unless you manually populate valid_from/valid_to, behavior same as Tier 0

# With manually populated temporal data:
result = resolver.resolve_ticker("AAPL", as_of=date(1990, 1, 1))
# If valid_from/valid_to populated: ✅ Returns correct historical entity
# If not populated: ⚠️ Returns current with warning

# Merge redirects work:
entity = resolver.get("old_entity_id")  # ✅ Returns merged-into entity
entity, chain = resolver.get_canonical("old_entity_id")  # ✅ Returns with redirect chain
```

### Tier 3: PostgreSQL (Full Support)

```python
# Full temporal resolution with vendor data
result = resolver.resolve_ticker("AAPL", mic="XNAS", as_of=date(1990, 1, 1))
# ✅ Returns correct historical entity from that exchange at that time

# No warnings, full support:
assert result.warnings == []
assert result.limits == {}
```

---

## ResolutionResult Limits & Warnings

### Updated ResolutionResult Schema

```python
@dataclass
class ResolutionResult:
    """
    Result of entity resolution.
    
    Attributes:
        candidates: Ranked list of matching entities.
        query: The original query string.
        as_of: Point-in-time for the resolution.
        is_ambiguous: True if multiple high-scoring candidates.
        needs_review: True if confidence is low.
        created_provisional: True if a provisional entity was created.
        
        # NEW in v2.2.1: Honesty fields
        warnings: List of warnings about resolution limitations.
        limits: Dict describing capability limits that applied.
        tier: The storage tier that performed this resolution.
    """
    
    candidates: list[ResolutionCandidate]
    query: str
    as_of: date
    is_ambiguous: bool = False
    needs_review: bool = False
    created_provisional: bool = False
    
    # Honesty fields (NEW)
    warnings: list[str] = field(default_factory=list)
    limits: dict[str, str] = field(default_factory=dict)
    tier: int = 0  # 0, 1, 2, or 3
    
    @property
    def has_temporal_limits(self) -> bool:
        """True if temporal resolution was limited."""
        return "temporal_resolution" in self.limits
```

### Standard Warnings

| Warning | When Issued |
|---------|-------------|
| `"as_of parameter ignored: listing validity data not available"` | Tier 0-1 with unpopulated validity |
| `"mic parameter ignored: exchange data not available"` | Tier 0-1 |
| `"fuzzy matching not available in Tier 0"` | Tier 0 with non-exact name match |
| `"redirect chain truncated at depth {n}"` | Max redirect depth reached |
| `"redirect cycle detected: {chain}"` | Circular merge reference |

### Standard Limits

| Limit Key | Possible Values | Meaning |
|-----------|-----------------|---------|
| `temporal_resolution` | `"current_only"`, `"best_effort"`, `"full"` | as_of support level |
| `mic_filtering` | `"not_available"`, `"partial"`, `"full"` | Exchange filtering support |
| `fuzzy_matching` | `"not_available"`, `"like_only"`, `"fts"` | Name search capability |
| `redirect_depth` | `"truncated_at_{n}"` | If chain was cut short |
| `person_entities` | `"schema_only"`, `"supported"`, `"full"` | Person entity support |
| `role_assignments` | `"not_available"`, `"schema_only"`, `"supported"` | Role query support |
| `relationships` | `"not_available"`, `"schema_only"`, `"supported"` | Relationship query support |
| `cases` | `"not_available"`, `"schema_only"`, `"supported"` | Case/proceeding support |
| `address_matching` | `"not_available"`, `"hash_based"`, `"fuzzy"` | Address matching capability |

### Knowledge Graph Warnings

| Warning | When Issued |
|---------|-------------|
| `"role_data_not_available"` | Tier 0, or Tier 1 with no role data loaded |
| `"relationship_data_not_available"` | Tier 0, or Tier 1 with no relationship data |
| `"case_data_not_available"` | Tier 0, or Tier 1 with no case data |
| `"person_matching_conservative"` | Tier 0-1 uses exact name match only |
| `"temporal_role_query_ignored"` | Tier 0-1 ignores as_of for role queries |

---

## Upgrading Tiers

### Tier 0 → Tier 1

Migration is automatic: JSONStore data can be imported into SQLiteStore.

```python
# Tier 0
json_resolver = EntityResolver(backend="json")

# Upgrade to Tier 1 (imports SEC JSON into SQLite)
sqlite_resolver = EntityResolver(
    backend="sqlite",
    db_path="entities.db",
    json_path="company_tickers.json",  # Import from JSON
)
```

**What you gain**:
- Merge redirect support
- Explicit claims with provenance
- Fuzzy name search (LIKE patterns)
- Schema ready for temporal data (if you populate it)

**What doesn't change**:
- Still SEC-only data (no MIC, no historical validity)
- as_of still returns current data with warnings

### Tier 1 → Tier 3

Requires data enrichment from external sources.

---

## Decision Log

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | Add `warnings` to ResolutionResult | Callers need to know when resolution is limited |
| 2 | Add `limits` dict | Machine-readable capability information |
| 3 | Add `tier` field | Callers can check which tier performed resolution |
| 4 | SEC JSON = current only | This is the reality of the data source |
| 5 | Don't fake historical data | Honesty > convenience |
| 6 | Tier 1 schema supports temporal | Ready for enrichment, but not guaranteed |

---

## Known Limitations / Open Questions

### Limitations

1. **SEC JSON update frequency**: We don't track when SEC JSON was downloaded. Stale data possible.
2. **Ticker changes not tracked**: If GOOG→GOOGL happened, SEC JSON only shows current state.
3. **Exchange listing unknown**: We assume US exchanges but don't actually know.

### Open Questions

1. **Should Tier 0-1 refuse as_of entirely, or return current with warning?**
   - Current decision: Return current with warning (less disruptive)
   - Alternative: Raise `TemporalResolutionNotSupported` exception

2. **Should we track SEC JSON download timestamp?**
   - Could add `data_as_of: datetime` to ResolutionResult
   - Would help callers understand data freshness

3. **How to handle partial temporal data?**
   - Some listings have valid_from, others don't
   - Current: Mix supported and best-effort, warn appropriately

---

*EntitySpine Tier Capabilities v2.2.1 | January 2026*
