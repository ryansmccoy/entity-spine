# EntitySpine + FeedSpine Integration Analysis

**Status**: Analysis & Proposal  
**Date**: January 2026  
**Audience**: Architects

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [The py-sec-edgar Ecosystem](#the-py-sec-edgar-ecosystem)
3. [What FeedSpine Does](#what-feedspine-does)
4. [What EntitySpine Does](#what-entityspine-does)
5. [Overlap Analysis](#overlap-analysis)
6. [Integration Opportunities](#integration-opportunities)
7. [Symbology Refresh System](#symbology-refresh-system)
8. [Recommended Architecture](#recommended-architecture)
9. [Decision: Integrate or Keep Separate?](#decision-integrate-or-keep-separate)
10. [Implementation Roadmap](#implementation-roadmap)

---

## Executive Summary

**FeedSpine** and **EntitySpine** solve complementary problems:

| Aspect | FeedSpine | EntitySpine |
|--------|-----------|-------------|
| **Purpose** | Data ingestion & deduplication | Entity resolution & identity |
| **Core Problem** | "Capture feeds without duplicates" | "Which entity is this?" |
| **Data Flow** | Raw → Bronze → Silver → Gold | Query → Resolve → Canonical |
| **Deduplication** | By `natural_key` (exact match) | By identity (semantic match) |
| **Temporal** | Sightings (first/last seen) | Listings (valid_from/to) |

### Verdict: **Complementary, Not Overlapping**

FeedSpine handles **data ingestion** (getting symbology into the system).  
EntitySpine handles **identity resolution** (what does this symbology mean).

**Recommendation**: Keep them separate but create an **integration layer** for symbology refresh workflows.

---

## The py-sec-edgar Ecosystem

### Three Packages, Three Responsibilities

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           PY-SEC-EDGAR ECOSYSTEM                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                           py-sec-edgar                                   │   │
│  │                     (Main Application Layer)                             │   │
│  │                                                                          │   │
│  │  • CLI interface (sec-edgar fetch, search, download)                    │   │
│  │  • Filing collection workflows                                           │   │
│  │  • User-facing API                                                       │   │
│  │  • Configuration management                                              │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                              │                    │                              │
│                              │ uses               │ uses                         │
│                              ▼                    ▼                              │
│  ┌──────────────────────────────────┐   ┌──────────────────────────────────┐   │
│  │           FeedSpine              │   │          EntitySpine             │   │
│  │       (Data Ingestion)           │   │     (Identity Resolution)        │   │
│  │                                  │   │                                  │   │
│  │  • SEC RSS feed monitoring       │   │  • "Who is CIK 0000320193?"     │   │
│  │  • Bulk file downloads           │   │  • Ticker → Entity resolution    │   │
│  │  • Deduplication (seen before?)  │   │  • LEI/FIGI/CIK crosswalk       │   │
│  │  • Sighting tracking             │   │  • Claims with provenance        │   │
│  │  • Bronze/Silver/Gold layers     │   │  • Merge/rename history          │   │
│  └──────────────────────────────────┘   └──────────────────────────────────┘   │
│                              │                    │                              │
│                              └────────┬───────────┘                              │
│                                       │                                          │
│                                       ▼                                          │
│                          ┌─────────────────────────┐                            │
│                          │    Shared Storage       │                            │
│                          │  (DuckDB / SQLite)      │                            │
│                          └─────────────────────────┘                            │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### How They Work Together

| User Action | py-sec-edgar | FeedSpine | EntitySpine |
|-------------|--------------|-----------|-------------|
| `sec-edgar fetch --ticker AAPL` | CLI routing | — | Resolve AAPL → CIK 0000320193 |
| `sec-edgar monitor` | Start monitor | Track new filings, dedup | — |
| `sec-edgar download --cik 320193` | Download orchestration | Store filing metadata | Lookup entity name |
| `sec-edgar search "Apple"` | Search interface | — | Fuzzy name matching |
| `sec-edgar refresh-symbology` | Trigger refresh | Fetch SEC/GLEIF feeds | Store new identifiers |

### Data Flow Example: Fetch Filings for Apple

```
User: sec-edgar fetch --ticker AAPL --form 10-K

┌─────────────────────────────────────────────────────────────────────────────┐
│ Step 1: py-sec-edgar receives command                                        │
│         "fetch 10-K filings for ticker AAPL"                                │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Step 2: EntitySpine resolves ticker                                          │
│                                                                              │
│   resolver.resolve_ticker("AAPL")                                           │
│   → ResolutionResult(                                                        │
│       best = Candidate(entity_id="01ARZ...", cik="0000320193",              │
│                        name="Apple Inc.", score=1.0)                        │
│     )                                                                        │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Step 3: py-sec-edgar queries SEC EDGAR                                       │
│                                                                              │
│   GET https://data.sec.gov/submissions/CIK0000320193.json                   │
│   → Filing list for Apple Inc.                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Step 4: FeedSpine tracks what we've seen                                     │
│                                                                              │
│   For each filing:                                                           │
│     spine.record(                                                            │
│       natural_key="0000320193-24-000082",  # accession number               │
│       content={"form": "10-K", "filed": "2024-11-01", ...}                  │
│     )                                                                        │
│     → Sighting(is_new=True/False)  # Have we downloaded this before?        │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Step 5: py-sec-edgar downloads new filings only                              │
│                                                                              │
│   if sighting.is_new:                                                        │
│       download_filing(accession_number)                                      │
│       store_locally(filing)                                                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Data Flow Example: Symbology Refresh

```
User: sec-edgar refresh-symbology

┌─────────────────────────────────────────────────────────────────────────────┐
│ Step 1: py-sec-edgar triggers refresh                                        │
│         "Update all symbology from SEC, GLEIF, OpenFIGI"                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Step 2: FeedSpine fetches raw data from sources                              │
│                                                                              │
│   SEC:     GET https://www.sec.gov/files/company_tickers.json               │
│   GLEIF:   Download golden copy (bulk LEI data)                              │
│   OpenFIGI: Query API for new mappings                                       │
│                                                                              │
│   → Deduplicate against previous fetches (sightings)                        │
│   → Store raw data in Bronze layer                                          │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Step 3: EntitySpine processes new identifiers                                │
│                                                                              │
│   For each NEW record from FeedSpine:                                        │
│                                                                              │
│   # Check if identifier exists                                               │
│   existing = store.get_claims(scheme="cik", value="0000320193")             │
│                                                                              │
│   if not existing:                                                           │
│       # New entity!                                                          │
│       entity = Entity(name="Apple Inc.", status="active")                   │
│       claim = IdentifierClaim(scheme="cik", value="0000320193", ...)        │
│       store.save(entity, claim)                                              │
│                                                                              │
│   elif new_identifier_for_existing_entity:                                   │
│       # Same entity, new identifier (e.g., added LEI)                       │
│       claim = IdentifierClaim(scheme="lei", value="HWUPKR...", ...)         │
│       store.save(claim)                                                      │
│                                                                              │
│   else:                                                                       │
│       # Already have this - skip (no duplicates!)                           │
│       pass                                                                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Step 4: Report results                                                       │
│                                                                              │
│   RefreshResult:                                                             │
│     sources_refreshed: 3                                                     │
│     new_entities: 42                                                         │
│     new_claims: 156                                                          │
│     skipped_duplicates: 12,847                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Package Boundaries

```
┌────────────────────────────────────────────────────────────────────────────┐
│                              py-sec-edgar                                   │
│                                                                             │
│  Responsibilities:                                                          │
│  ─────────────────                                                          │
│  • CLI and user interface                                                   │
│  • Workflow orchestration                                                   │
│  • SEC EDGAR API interactions                                               │
│  • Filing download and storage                                              │
│  • Section extraction (10-K/10-Q parsing)                                  │
│  • Configuration and caching                                                │
│                                                                             │
│  Does NOT own:                                                              │
│  ──────────────                                                             │
│  • Entity resolution logic (→ EntitySpine)                                 │
│  • Feed deduplication logic (→ FeedSpine)                                  │
│  • Identifier storage schema (→ EntitySpine)                               │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────┐
│                              FeedSpine                                      │
│                                                                             │
│  Responsibilities:                                                          │
│  ─────────────────                                                          │
│  • Generic feed ingestion (any data source)                                │
│  • Record deduplication by natural_key                                     │
│  • Sighting tracking (first seen, last seen)                               │
│  • Bronze/Silver/Gold layer management                                     │
│  • Storage backends (DuckDB, Postgres, Memory)                             │
│                                                                             │
│  Does NOT own:                                                              │
│  ──────────────                                                             │
│  • SEC-specific logic (→ py-sec-edgar)                                     │
│  • Entity identity/resolution (→ EntitySpine)                              │
│  • What the data "means" (it's storage-agnostic)                           │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────┐
│                              EntitySpine                                    │
│                                                                             │
│  Responsibilities:                                                          │
│  ─────────────────                                                          │
│  • Entity/Security/Listing domain model                                    │
│  • Identifier claims with provenance                                       │
│  • Resolution: ticker → entity, CIK → entity, name → entity               │
│  • Merge/rename tracking (old IDs → current ID)                           │
│  • Crosswalk between identifier schemes                                    │
│  • Point-in-time queries (as_of)                                           │
│                                                                             │
│  Does NOT own:                                                              │
│  ──────────────                                                             │
│  • How data is fetched (→ FeedSpine or direct)                            │
│  • SEC filing content (→ py-sec-edgar)                                     │
│  • UI/CLI (→ py-sec-edgar)                                                 │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘
```

### Why Three Packages?

| Principle | Explanation |
|-----------|-------------|
| **Single Responsibility** | Each package does one thing well |
| **Reusability** | FeedSpine can be used outside SEC context (any feed) |
| **Reusability** | EntitySpine can be used outside SEC context (any entity resolution) |
| **Testing** | Each package tested independently |
| **Versioning** | Can release EntitySpine v2.3 without touching py-sec-edgar |
| **Dependencies** | py-sec-edgar can use EntitySpine without FeedSpine (or vice versa) |

---

## What FeedSpine Does

### Core Capabilities

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          FEEDSPINE CORE                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  1. FEED ADAPTERS         2. DEDUPLICATION        3. SIGHTING TRACKING  │
│  ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐   │
│  │ SecRssFeed      │     │ natural_key     │     │ first_seen_at   │   │
│  │ GLEIFFeed       │────▶│ collision check │────▶│ last_seen_at    │   │
│  │ OpenFIGIFeed    │     │ hash comparison │     │ seen_count      │   │
│  │ CustomFileFeed  │     └─────────────────┘     │ is_new flag     │   │
│  └─────────────────┘                             └─────────────────┘   │
│                                                                          │
│  4. MEDALLION LAYERS      5. STORAGE BACKENDS    6. ENRICHMENT         │
│  ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐   │
│  │ BRONZE (raw)    │     │ DuckDB          │     │ BatchEnricher   │   │
│  │ SILVER (clean)  │     │ PostgreSQL      │     │ Metadata        │   │
│  │ GOLD (curated)  │     │ Memory          │     │ Validation      │   │
│  └─────────────────┘     └─────────────────┘     └─────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Key Data Model

```python
# FeedSpine's core model
@dataclass
class RecordCandidate:
    natural_key: str      # Unique within feed (e.g., "cik:0000320193")
    published_at: datetime
    content: dict         # Arbitrary payload
    metadata: Metadata    # Source, tags, etc.

@dataclass
class Sighting:
    natural_key: str
    source: str
    seen_at: datetime
    is_new: bool         # First time seeing this key?
```

### What FeedSpine Does Well

1. **Exact deduplication** - Same `natural_key` → same record
2. **Sighting tracking** - Know when records appear/disappear
3. **Multi-source ingestion** - Combine SEC, GLEIF, OpenFIGI, etc.
4. **Storage agnostic** - DuckDB, Postgres, Memory backends
5. **Scheduled refresh** - Cron-like feed scheduling

---

## What EntitySpine Does

### Core Capabilities

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          ENTITYSPINE CORE                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  1. ENTITY RESOLUTION     2. CLAIMS MODEL        3. MERGE TRACKING      │
│  ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐   │
│  │ "AAPL" → Entity │     │ CIK claim       │     │ Entity A        │   │
│  │ "320193" → Entity│     │ LEI claim       │────▶│  merged_into    │   │
│  │ "Apple" → Entity│────▶│ Ticker claim    │     │ Entity B        │   │
│  │ Score ranking   │     │ FIGI claim      │     │ (redirect chain)│   │
│  └─────────────────┘     └─────────────────┘     └─────────────────┘   │
│                                                                          │
│  4. E/S/L HIERARCHY       5. TEMPORAL VALIDITY   6. TIER STORAGE       │
│  ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐   │
│  │ Entity          │     │ valid_from      │     │ Tier 0: JSON    │   │
│  │   └─ Security   │     │ valid_to        │     │ Tier 1: SQLite  │   │
│  │       └─ Listing│     │ as_of queries   │     │ Tier 2: DuckDB  │   │
│  └─────────────────┘     └─────────────────┘     │ Tier 3: Postgres│   │
│                                                   └─────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Key Data Model

```python
# EntitySpine's core model
@dataclass
class Entity:
    entity_id: str        # ULID
    primary_name: str
    status: str           # active, merged, provisional
    merged_into_id: str | None

@dataclass
class IdentifierClaim:
    entity_id: str
    scheme: str           # 'cik', 'lei', 'ticker', 'figi'
    value: str
    source_system: str    # 'sec', 'gleif', 'openfigi'
    confidence: float
    captured_at: datetime
```

### What EntitySpine Does Well

1. **Semantic resolution** - "AAPL" and "Apple Inc." → same entity
2. **Claims with provenance** - Track where identifiers came from
3. **Entity ≠ Security ≠ Listing** - Proper financial modeling
4. **Merge history** - Old IDs remain resolvable forever
5. **Point-in-time** - What was AAPL on 2020-01-01?

---

## Overlap Analysis

### Where They Overlap

| Feature | FeedSpine | EntitySpine | Winner |
|---------|-----------|-------------|--------|
| Store CIKs | ✅ `natural_key` | ✅ `IdentifierClaim` | Both |
| Deduplicate | ✅ Exact match | ✅ Semantic match | Different |
| Track changes | ✅ Sightings | ✅ Claims history | Both |
| Query by ticker | ⚠️ Generic query | ✅ `resolve_ticker()` | EntitySpine |
| Multi-source | ✅ Feed adapters | ⚠️ Manual import | FeedSpine |

### Where They're Different

| Capability | FeedSpine | EntitySpine |
|------------|-----------|-------------|
| **Dedup logic** | Hash/key match | Identity resolution |
| **Data model** | Flat records | Entity/Security/Listing |
| **Resolution** | Query filters | Ranked candidates |
| **Merge handling** | Replace/update | Redirect chain |
| **Temporal** | first_seen/last_seen | valid_from/valid_to |

### The Gap

**FeedSpine** can tell you: "I saw CIK 0000320193 on 2024-01-15"  
**EntitySpine** can tell you: "CIK 0000320193 is Apple Inc., ticker AAPL on XNAS"

Neither alone solves: **"Refresh symbology and only insert new identifiers"**

---

## Integration Opportunities

### Opportunity 1: FeedSpine as Data Source for EntitySpine

```
FeedSpine (ingestion)          EntitySpine (resolution)
─────────────────────          ─────────────────────────
                               
SEC Feed ──┐                   
           │                   ┌─────────────────┐
GLEIF Feed─┼─▶ FeedSpine ─────▶│ EntitySpine     │
           │   (dedup)         │ load_from_spine()│
FIGI Feed ─┘                   └─────────────────┘
```

**Use Case**: FeedSpine collects symbology from multiple sources. EntitySpine consumes the deduplicated data.

```python
# entityspine/adapters/feedspine_adapter.py
class FeedSpineAdapter:
    """Load entities from FeedSpine storage."""
    
    def __init__(self, feedspine: FeedSpine, entity_store: EntityStoreProtocol):
        self._spine = feedspine
        self._store = entity_store
    
    async def sync_sec_entities(self) -> int:
        """Sync SEC entities from FeedSpine to EntitySpine."""
        count = 0
        
        async for record in self._spine.query(
            source="sec-tickers",
            layer=Layer.SILVER,  # Use cleaned data
        ):
            cik = record.content["cik"]
            
            # Check if entity exists
            result = self._store.get_claims(scheme="cik", value=cik)
            
            if not result:
                # New entity - create it
                entity = self._create_entity_from_record(record)
                self._store.store_entity(entity)
                count += 1
            else:
                # Existing - update claims if needed
                self._update_claims_from_record(result[0].entity_id, record)
        
        return count
```

### Opportunity 2: EntitySpine as Resolution Service for FeedSpine

```
FeedSpine Record              EntitySpine
─────────────────              ───────────

{ "ticker": "AAPL" }  ───────▶ resolve("AAPL")
                               ◀─────────────
                      { "entity_id": "01ARZ3...", "cik": "0000320193" }
```

**Use Case**: FeedSpine enrichers use EntitySpine for resolution.

```python
# feedspine/enrichers/entity_enricher.py
class EntitySpineEnricher(Enricher):
    """Enrich FeedSpine records with EntitySpine resolution."""
    
    def __init__(self, resolver: EntityResolverProtocol):
        self._resolver = resolver
    
    async def enrich(self, record: Record) -> Record:
        ticker = record.content.get("ticker")
        if not ticker:
            return record
        
        result = self._resolver.resolve_ticker(ticker)
        
        if result.best:
            record.content["entity_id"] = result.best.entity_id
            record.content["resolved_name"] = result.best.matched_value
            record.content["resolution_score"] = result.best.score
        
        return record
```

### Opportunity 3: Shared Sighting/Claim Model

Both track "when did we see this identifier?" - could unify:

```python
# Unified observation model
@dataclass
class IdentifierObservation:
    """When an identifier was observed from a source."""
    
    scheme: str          # 'cik', 'ticker', 'lei', 'figi'
    value: str           # The identifier value
    source: str          # 'sec-feed', 'gleif-bulk', 'manual'
    observed_at: datetime
    is_first: bool       # First time seeing this?
    raw_content: dict    # Original record data
```

---

## Symbology Refresh System

### The User's Request

> "Setup a system for symbology that would refresh various symbology lists and be able to track and deduplicate and only append new identifiers so there are no duplicates and searching could be easier"

### Proposed Solution: SymbologyRefreshService

```python
# entityspine/services/symbology_refresh.py
"""Symbology refresh service using FeedSpine for ingestion."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

from entityspine.protocols import EntityStoreProtocol


@dataclass
class RefreshResult:
    """Result of a symbology refresh operation."""
    
    source: str
    started_at: datetime
    completed_at: datetime
    records_fetched: int
    new_entities: int
    new_claims: int
    updated_claims: int
    skipped_duplicates: int
    errors: list[str]


class SymbologySource(Protocol):
    """Protocol for symbology data sources."""
    
    name: str
    
    async def fetch(self) -> list[dict]:
        """Fetch current symbology data."""
        ...


class SymbologyRefreshService:
    """
    Refresh symbology from multiple sources, deduplicating against EntitySpine.
    
    Key Features:
    - Only appends NEW identifiers (no duplicates)
    - Tracks when identifiers were first/last seen
    - Uses FeedSpine for raw data ingestion (optional)
    - Uses EntitySpine for identity resolution
    
    Example:
        >>> service = SymbologyRefreshService(entity_store)
        >>> service.add_source(SECTickerSource())
        >>> service.add_source(GLEIFSource())
        >>> results = await service.refresh_all()
        >>> print(f"Added {results.total_new_claims} new identifiers")
    """
    
    def __init__(
        self,
        entity_store: EntityStoreProtocol,
        feedspine: FeedSpine | None = None,  # Optional FeedSpine for ingestion
    ):
        self._store = entity_store
        self._spine = feedspine
        self._sources: list[SymbologySource] = []
    
    def add_source(self, source: SymbologySource) -> None:
        """Register a symbology source."""
        self._sources.append(source)
    
    async def refresh_all(self) -> list[RefreshResult]:
        """Refresh all registered sources."""
        results = []
        for source in self._sources:
            result = await self.refresh_source(source)
            results.append(result)
        return results
    
    async def refresh_source(self, source: SymbologySource) -> RefreshResult:
        """
        Refresh symbology from a single source.
        
        Process:
        1. Fetch raw data from source
        2. If FeedSpine configured, store for dedup/audit
        3. For each record, check if identifier exists in EntitySpine
        4. Only insert NEW identifiers (claims)
        5. Track statistics
        """
        started = datetime.now(timezone.utc)
        
        # Fetch raw data
        raw_records = await source.fetch()
        
        # Optional: Store in FeedSpine for audit trail
        if self._spine:
            await self._store_in_feedspine(source.name, raw_records)
        
        # Process each record
        new_entities = 0
        new_claims = 0
        updated_claims = 0
        skipped = 0
        errors = []
        
        for record in raw_records:
            try:
                result = await self._process_record(source.name, record)
                if result == "new_entity":
                    new_entities += 1
                elif result == "new_claim":
                    new_claims += 1
                elif result == "updated":
                    updated_claims += 1
                else:
                    skipped += 1
            except Exception as e:
                errors.append(str(e))
        
        return RefreshResult(
            source=source.name,
            started_at=started,
            completed_at=datetime.now(timezone.utc),
            records_fetched=len(raw_records),
            new_entities=new_entities,
            new_claims=new_claims,
            updated_claims=updated_claims,
            skipped_duplicates=skipped,
            errors=errors,
        )
    
    async def _process_record(
        self, 
        source: str, 
        record: dict
    ) -> str:
        """
        Process a single symbology record.
        
        Returns: 'new_entity', 'new_claim', 'updated', or 'skipped'
        """
        # Extract identifier(s) from record
        identifiers = self._extract_identifiers(record)
        
        for scheme, value in identifiers:
            # Check if this exact claim exists
            existing = self._store.get_claims(scheme=scheme, value=value)
            
            if not existing:
                # New identifier - need to create or link to entity
                entity_id = await self._resolve_or_create_entity(record)
                
                claim = IdentifierClaim(
                    claim_id=generate_ulid(),
                    entity_id=entity_id,
                    scheme=scheme,
                    value=value,
                    source_system=source,
                    confidence=1.0,
                    captured_at=datetime.now(timezone.utc),
                )
                self._store.store_claim(claim)
                return "new_claim"
            
            # Claim exists - check if it's from same source
            if any(c.source_system == source for c in existing):
                return "skipped"  # Duplicate from same source
            
            # New source for existing identifier - add claim
            return "updated"
        
        return "skipped"
    
    def _extract_identifiers(self, record: dict) -> list[tuple[str, str]]:
        """Extract identifier (scheme, value) pairs from record."""
        identifiers = []
        
        if cik := record.get("cik"):
            identifiers.append(("cik", str(cik).zfill(10)))
        
        if lei := record.get("lei"):
            identifiers.append(("lei", lei))
        
        if figi := record.get("figi"):
            identifiers.append(("figi", figi))
        
        if isin := record.get("isin"):
            identifiers.append(("isin", isin))
        
        if cusip := record.get("cusip"):
            identifiers.append(("cusip", cusip))
        
        return identifiers
```

### Example Sources

```python
# entityspine/sources/sec.py
class SECTickerSource(SymbologySource):
    """SEC company_tickers.json source."""
    
    name = "sec-tickers"
    url = "https://www.sec.gov/files/company_tickers.json"
    
    async def fetch(self) -> list[dict]:
        async with httpx.AsyncClient() as client:
            response = await client.get(self.url)
            data = response.json()
            
            return [
                {
                    "cik": str(item["cik_str"]).zfill(10),
                    "ticker": item.get("ticker"),
                    "name": item.get("title"),
                }
                for item in data.values()
            ]


# entityspine/sources/gleif.py  
class GLEIFSource(SymbologySource):
    """GLEIF LEI bulk data source."""
    
    name = "gleif-lei"
    
    async def fetch(self) -> list[dict]:
        # Download and parse GLEIF golden copy
        ...
```

---

## Recommended Architecture

### Option A: FeedSpine as Optional Dependency (RECOMMENDED)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     ENTITYSPINE ARCHITECTURE                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  CORE (zero deps)                                                        │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Entity, Security, Listing, IdentifierClaim                      │   │
│  │  EntityResolver, EntityStore                                      │   │
│  │  SQLite storage (stdlib)                                          │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  SYMBOLOGY REFRESH (optional FeedSpine integration)                      │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  SymbologyRefreshService                                          │   │
│  │    ├─ With FeedSpine: Full audit trail, sightings, scheduling   │   │
│  │    └─ Without: Direct HTTP fetch, simpler                        │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  SOURCES (adapters for data providers)                                   │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  SECTickerSource, GLEIFSource, OpenFIGISource, LocalFileSource  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Package Structure

```
entityspine/
├── src/entityspine/
│   ├── core/                    # Zero deps
│   │   ├── models.py
│   │   └── resolver.py
│   │
│   ├── storage/                 # Tier backends
│   │   ├── sqlite.py
│   │   └── duckdb.py
│   │
│   ├── services/                # Business logic
│   │   └── symbology_refresh.py # NEW
│   │
│   ├── sources/                 # Symbology sources # NEW
│   │   ├── __init__.py
│   │   ├── sec.py
│   │   ├── gleif.py
│   │   └── openfigi.py
│   │
│   └── adapters/                # External integrations
│       └── feedspine.py         # NEW: Optional FeedSpine adapter

# Optional dependency
[project.optional-dependencies]
feedspine = ["feedspine>=0.1.0"]
```

---

## Decision: Integrate or Keep Separate?

### Analysis

| Factor | Integrate | Keep Separate |
|--------|-----------|---------------|
| **Dependency** | EntitySpine requires FeedSpine | EntitySpine standalone |
| **Complexity** | More complex | Simpler core |
| **Flexibility** | FeedSpine's full power | Custom refresh logic |
| **Use case** | Heavy symbology refresh | Light identifier lookup |
| **Testing** | More mocks needed | Easier unit tests |

### Recommendation: **Keep Separate with Optional Integration**

```python
# Install options:
# pip install entityspine                    # Core only (zero deps)
# pip install entityspine[feedspine]         # With FeedSpine integration
# pip install entityspine[all]               # All optional deps
```

### Rationale

1. **EntitySpine's core mission** is resolution, not ingestion
2. **FeedSpine is great for ingestion** but EntitySpine doesn't need it for basic operation
3. **Optional integration** gives users choice without forcing dependencies
4. **SymbologyRefreshService** works with or without FeedSpine

---

## Implementation Roadmap

### Phase 1: Core EntitySpine (No FeedSpine)

- [x] Entity/Security/Listing models
- [x] IdentifierClaim with provenance
- [x] EntityResolver returning ResolutionResult
- [x] SQLite storage (Tier 1)
- [ ] Basic symbology sources (SEC, GLEIF)

### Phase 2: SymbologyRefreshService

- [ ] Create `services/symbology_refresh.py`
- [ ] Create `sources/` module with SEC, GLEIF sources
- [ ] Implement deduplication logic (only append new)
- [ ] Track refresh statistics

### Phase 3: Optional FeedSpine Integration

- [ ] Create `adapters/feedspine.py`
- [ ] FeedSpine storage adapter for EntitySpine
- [ ] EntitySpine enricher for FeedSpine
- [ ] Integration tests

### Phase 4: Advanced Features

- [ ] Scheduled refresh (with or without FeedSpine)
- [ ] Conflict detection (same identifier, different entities)
- [ ] Vendor crosswalk (FIGI ↔ LEI ↔ CIK)

---

## Summary

| Component | Role | Integration Level |
|-----------|------|-------------------|
| **FeedSpine** | Data ingestion, deduplication, sightings | Optional adapter |
| **EntitySpine** | Entity resolution, identity, claims | Core |
| **SymbologyRefreshService** | Bridge between sources and EntitySpine | New service |

**Key Insight**: FeedSpine and EntitySpine solve **different problems**:
- FeedSpine: "Have I seen this record before?"
- EntitySpine: "What entity does this identifier belong to?"

They complement each other perfectly when used together, but EntitySpine should remain usable without FeedSpine for simpler use cases.

---

*EntitySpine + FeedSpine Integration Analysis | January 2026*
