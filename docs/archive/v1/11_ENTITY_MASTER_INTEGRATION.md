# Entity Master Integration Guide

This document provides a comprehensive overview of the Entity Master system and how it integrates with the py-sec-edgar filing pipeline.

---

## Executive Summary

The **Entity Master** is a modular identity resolution and symbology management system that:
- Resolves any identifier (ticker, CIK, LEI, FIGI, ISIN, CUSIP) to a canonical entity
- Provides fuzzy name matching for entity mentions in filings
- Enriches entities with external data (GLEIF, OpenFIGI)
- Persists entity data with full audit trail
- Functions as a **Security Master** for linking filings to market data

**Key Insight**: The Entity Master is designed to be **completely modular** - it can be used standalone or deeply integrated with the filing extraction pipeline.

---

## Architecture Overview

```
+============================================================================+
|                     PY-SEC-EDGAR ENTITY MASTER ARCHITECTURE                |
+============================================================================+
|                                                                            |
|  +---------------------------------------------------------------------+   |
|  |                        SEC CLASS (sec.py)                           |   |
|  |                                                                     |   |
|  |  sec.resolve_entity("AAPL")    # Ticker -> Entity                   |   |
|  |  sec.resolve_entity("320193")  # CIK -> Entity                      |   |
|  |  sec.search_entities("apple")  # Fuzzy search                       |   |
|  |  await sec.load_entities()     # Load registry                      |   |
|  +---------------------------------------------------------------------+   |
|                                    |                                       |
|                                    v                                       |
|  +---------------------------------------------------------------------+   |
|  |                     ENTITY REGISTRY (singleton)                     |   |
|  |                   core/identity/registry.py                         |   |
|  |                                                                     |   |
|  |  - Auto-loads SEC company_tickers.json (~10,000 companies)          |   |
|  |  - In-memory index for fast lookups by any identifier               |   |
|  |  - Fuzzy name matching with configurable thresholds                 |   |
|  |  - User entity registration (private companies)                     |   |
|  +---------------------------------------------------------------------+   |
|                                    |                                       |
|       +----------------------------+----------------------------+          |
|       |                            |                            |          |
|       v                            v                            v          |
|  +-----------+             +--------------+            +--------------+    |
|  |  ENTITY   |             |  IDENTIFIER  |            |    ALIAS     |    |
|  |  MODEL    |             |   SCHEMES    |            |   MATCHING   |    |
|  |           |             |              |            |              |    |
|  | - type    |             | - CIK        |            | - legal      |    |
|  | - status  |             | - LEI        |            | - trade      |    |
|  | - name    |             | - FIGI       |            | - former     |    |
|  | - ids[]   |             | - ISIN       |            | - short      |    |
|  | - aliases |             | - CUSIP      |            | - extracted  |    |
|  +-----------+             | - TICKER     |            +--------------+    |
|       |                    | - DUNS       |                                |
|       |                    +--------------+                                |
|       v                                                                    |
|  +---------------------------------------------------------------------+   |
|  |                        ENRICHMENT LAYER                             |   |
|  |                   core/identity/enricher.py                         |   |
|  |                                                                     |   |
|  |   +-----------------+        +------------------+                   |   |
|  |   | GLEIF Client    |        | OpenFIGI Client  |                   |   |
|  |   | (LEI lookup)    |        | (FIGI/ISIN/CUSIP)|                   |   |
|  |   +-----------------+        +------------------+                   |   |
|  +---------------------------------------------------------------------+   |
|                                    |                                       |
|                                    v                                       |
|  +---------------------------------------------------------------------+   |
|  |                      PERSISTENCE LAYER                              |   |
|  |                                                                     |   |
|  |  +-------------------+     +-------------------+                    |   |
|  |  | EntityStore       |     | Entity Cache      |                    |   |
|  |  | (DuckDB)          |     | (JSON)            |                    |   |
|  |  |                   |     |                   |                    |   |
|  |  | - entities        |     | - entities.json   |                    |   |
|  |  | - identifiers     |     | - user additions  |                    |   |
|  |  | - aliases         |     |                   |                    |   |
|  |  | - history         |     |                   |                    |   |
|  |  +-------------------+     +-------------------+                    |   |
|  +---------------------------------------------------------------------+   |
|                                                                            |
+============================================================================+
```

---

## Module Structure

```
py_sec_edgar/src/py_sec_edgar/core/identity/
|
+-- __init__.py          # Public exports
+-- accession.py         # AccessionNumber parsing
+-- cik.py               # CIK normalization
+-- filing.py            # Filing, Company models
|
+-- entity.py            # Entity, EntityType, EntityStatus, Alias
+-- identifiers.py       # Identifier, IdentifierScheme
+-- registry.py          # EntityRegistry, EntityIndex (singleton)
+-- matching.py          # NameMatcher, fuzzy matching
+-- store.py             # EntityStore (DuckDB persistence)
+-- enricher.py          # EntityEnricher (GLEIF, OpenFIGI orchestration)
|
+-- sources/
    +-- gleif.py         # GLEIF API client (LEI lookups)
    +-- openfigi.py      # OpenFIGI API client (FIGI/ISIN/CUSIP)
```

---

## Core Data Models

### Entity

```python
@dataclass
class Entity:
    entity_id: str                    # Internal UUID
    entity_type: EntityType           # COMPANY, FUND, PERSON, etc.
    status: EntityStatus              # ACTIVE, INACTIVE, MERGED
    primary_name: str                 # "Apple Inc"
    jurisdiction: str                 # "US", "GB", "KY"
    identifiers: list[Identifier]     # All known identifiers
    aliases: list[Alias]              # Name variants
    metadata: dict                    # Flexible key-value
    
    # Convenience properties
    @property
    def cik(self) -> str | None: ...
    @property
    def ticker(self) -> str | None: ...  # "AAPL:NASDAQ"
    @property
    def lei(self) -> str | None: ...
    @property
    def figi(self) -> str | None: ...
    @property
    def isin(self) -> str | None: ...
    @property
    def cusip(self) -> str | None: ...
```

### Identifier Schemes

| Scheme | Description | Format | Source |
|--------|-------------|--------|--------|
| `CIK` | SEC Central Index Key | 10 digits | SEC |
| `TICKER` | Stock symbol | AAPL:NASDAQ | SEC |
| `LEI` | Legal Entity Identifier | 20 chars | GLEIF |
| `FIGI` | Financial Instrument Global ID | BBG... 12 chars | OpenFIGI |
| `ISIN` | International Securities ID | 12 chars | OpenFIGI |
| `CUSIP` | US/Canada ID | 9 chars | OpenFIGI |
| `SEDOL` | UK ID | 7 chars | - |
| `DUNS` | D&B Number | 9 digits | Manual |

---

## Integration Points with Filing Pipeline

### Current State

The Entity Master is already integrated at these points:

```python
# 1. SEC class methods (sec.py)
sec.resolve_entity(identifier)     # Lookup any identifier
sec.search_entities(query)         # Fuzzy search
await sec.load_entities()          # Load from SEC

# 2. Download ticker resolution (sec.py line 350)
async def download(self, tickers=None, ...):
    for ticker in tickers:
        entity = self.resolve_entity(ticker)
        if entity:
            ciks.add(entity.cik)
```

### Missing Integration Points

The Entity Master should be integrated into:

| Component | Location | Integration Need |
|-----------|----------|------------------|
| **Filing Metadata** | `filing_metadata` table | Link to entity_id |
| **Entity Extraction** | `intelligence/extractors.py` | Resolve extracted mentions |
| **Graph Storage** | `graph/storage.py` | Normalize entities |
| **Section Extraction** | `extractor/section_extractor.py` | Entity context |
| **Enrichment Pipeline** | Cross-tier sync | Entity enrichment step |

---

## Integration with Tiered Storage

### How Entity Master Fits Each Tier

```
+----------------------------------------------------------------------------+
|                    ENTITY MASTER IN TIERED ARCHITECTURE                    |
+----------------------------------------------------------------------------+
|                                                                            |
|  TIER 1: LOCAL (DuckDB)                                                    |
|  +----------------------------------------------------------------------+  |
|  |  entities.duckdb                                                     |  |
|  |  - entities table (entity_id, name, type, status)                    |  |
|  |  - identifiers table (scheme, value, entity_id)                      |  |
|  |  - aliases table (name, entity_id)                                   |  |
|  |  - entity_history table (audit trail)                                |  |
|  |                                                                      |  |
|  |  Filing -> Entity JOIN:                                              |  |
|  |    SELECT f.*, e.primary_name, e.ticker                              |  |
|  |    FROM filing_metadata f                                            |  |
|  |    JOIN identifiers i ON f.cik = i.value AND i.scheme = 'cik'        |  |
|  |    JOIN entities e ON i.entity_id = e.entity_id                      |  |
|  +----------------------------------------------------------------------+  |
|                                                                            |
|  TIER 2: POSTGRES                                                          |
|  +----------------------------------------------------------------------+  |
|  |  Same schema, but:                                                   |  |
|  |  - Concurrent access                                                 |  |
|  |  - Foreign key constraints                                           |  |
|  |  - GIN indexes on identifiers for fast lookup                        |  |
|  |  - Materialized views for company profiles                           |  |
|  +----------------------------------------------------------------------+  |
|                                                                            |
|  TIER 3: ELASTICSEARCH                                                     |
|  +----------------------------------------------------------------------+  |
|  |  sec_entities index:                                                 |  |
|  |  - Searchable entity names/aliases                                   |  |
|  |  - Autocomplete on ticker/name                                       |  |
|  |  - Entity-scoped filing search                                       |  |
|  +----------------------------------------------------------------------+  |
|                                                                            |
|  TIER 4: NEO4J + LLM                                                       |
|  +----------------------------------------------------------------------+  |
|  |  Entity Master IS the company node source:                           |  |
|  |                                                                      |  |
|  |  (:Company {cik, ticker, lei, name}) <-- FROM Entity Master          |  |
|  |       |                                                              |  |
|  |       +-[:COMPETES_WITH]->(:Company)                                 |  |
|  |       +-[:SUPPLIES_TO]->(:Company)                                   |  |
|  |       +-[:IS_CUSTOMER_OF]->(:Company)                                |  |
|  |                                                                      |  |
|  |  LLM extraction -> Entity Master resolution -> Graph storage         |  |
|  +----------------------------------------------------------------------+  |
|                                                                            |
+----------------------------------------------------------------------------+
```

---

## Proposed Schema Additions

### 1. Add `entity_id` to `filing_metadata`

```sql
-- Add entity reference to filing_metadata
ALTER TABLE filing_metadata 
ADD COLUMN entity_id VARCHAR REFERENCES entities(entity_id);

-- Create index for entity-based queries
CREATE INDEX idx_filing_entity ON filing_metadata(entity_id);

-- Populate from CIK
UPDATE filing_metadata f
SET entity_id = (
    SELECT e.entity_id 
    FROM identifiers i 
    JOIN entities e ON i.entity_id = e.entity_id
    WHERE i.scheme = 'cik' AND i.value = LPAD(f.cik, 10, '0')
);
```

### 2. Add `extracted_entities` Table

```sql
-- Store entity mentions extracted from filings
CREATE TABLE extracted_entities (
    extraction_id VARCHAR PRIMARY KEY,
    
    -- Source
    accession_number VARCHAR NOT NULL,
    section_id VARCHAR,
    
    -- Extracted mention
    mention_text VARCHAR NOT NULL,           -- "TSMC"
    mention_type VARCHAR NOT NULL,           -- "supplier", "competitor", "customer"
    confidence REAL,
    
    -- Resolution (NULL if unresolved)
    resolved_entity_id VARCHAR REFERENCES entities(entity_id),
    resolution_method VARCHAR,               -- "exact", "fuzzy", "manual"
    resolution_confidence REAL,
    
    -- Context
    context_snippet TEXT,                    -- Surrounding text
    start_offset INTEGER,
    end_offset INTEGER,
    
    -- Audit
    extracted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    extracted_by VARCHAR,                    -- "llm:gpt-4o", "pattern:v1"
    
    UNIQUE(accession_number, mention_text, start_offset)
);

CREATE INDEX idx_extracted_entity ON extracted_entities(resolved_entity_id);
CREATE INDEX idx_extracted_accession ON extracted_entities(accession_number);
```

### 3. Add `entity_relationships` Table (Alternative to Graph)

```sql
-- Store entity relationships (can supplement or replace Neo4j)
CREATE TABLE entity_relationships (
    relationship_id VARCHAR PRIMARY KEY,
    
    -- Entities
    source_entity_id VARCHAR NOT NULL REFERENCES entities(entity_id),
    target_entity_id VARCHAR NOT NULL REFERENCES entities(entity_id),
    
    -- Relationship
    relationship_type VARCHAR NOT NULL,      -- SUPPLIER, CUSTOMER, COMPETITOR
    direction VARCHAR DEFAULT 'directed',    -- directed, bidirectional
    
    -- Evidence
    accession_number VARCHAR NOT NULL,
    section_id VARCHAR,
    evidence_text TEXT,
    confidence REAL,
    
    -- Metadata
    first_seen DATE,
    last_seen DATE,
    occurrence_count INTEGER DEFAULT 1,
    
    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(source_entity_id, target_entity_id, relationship_type, accession_number)
);

CREATE INDEX idx_rel_source ON entity_relationships(source_entity_id);
CREATE INDEX idx_rel_target ON entity_relationships(target_entity_id);
CREATE INDEX idx_rel_type ON entity_relationships(relationship_type);
```

---

## Integration Implementation

### Phase 1: Core Integration (Minimal)

```python
# py_sec_edgar/core/identity/__init__.py - Already done!
# Exports: Entity, EntityRegistry, get_entity_registry, etc.

# py_sec_edgar/sec.py - Already done!
# Methods: resolve_entity, search_entities, load_entities
```

### Phase 2: Filing Metadata Linkage

```python
# Add to filing_metadata enrichment step

async def enrich_filing_metadata(filing: FilingMetadata) -> FilingMetadata:
    """Enrich filing with entity reference."""
    from py_sec_edgar.core.identity import get_entity_registry
    
    registry = get_entity_registry()
    
    # Try to resolve by CIK
    entity = registry.resolve(filing.cik)
    
    if entity:
        filing.entity_id = entity.entity_id
        # Copy commonly needed fields
        filing.ticker = entity.ticker.split(":")[0] if entity.ticker else None
    
    return filing
```

### Phase 3: Entity Extraction Resolution

```python
# Modify intelligence/extractors.py

async def extract_and_resolve_entities(
    section_text: str,
    company_name: str,
) -> list[ResolvedEntity]:
    """Extract entities and resolve to canonical form."""
    from py_sec_edgar.core.identity import get_entity_registry
    
    # 1. Extract raw mentions (LLM or pattern)
    extractor = EntityExtractor()
    entities, relationships = await extractor.extract(section_text, company_name)
    
    # 2. Resolve each mention to canonical entity
    registry = get_entity_registry()
    resolved = []
    
    for entity in entities:
        # Try exact match first
        canonical = registry.resolve(entity.name)
        
        if canonical is None and entity.ticker:
            canonical = registry.resolve(entity.ticker)
        
        if canonical is None:
            # Try fuzzy match
            matches = registry.search(entity.name, limit=1)
            if matches and matches[0]:  # Check confidence threshold
                canonical = matches[0]
        
        resolved.append(ResolvedEntity(
            mention=entity,
            canonical=canonical,
            resolution_method="exact" if canonical else "unresolved",
        ))
    
    return resolved
```

### Phase 4: Graph Storage Integration

```python
# Modify graph/storage.py

async def store_entity_from_master(self, entity: Entity) -> GraphEntity:
    """Store entity from Entity Master into graph."""
    graph_entity = GraphEntity(
        entity_id=entity.entity_id,
        canonical_name=entity.primary_name,
        entity_type=EntityType(entity.entity_type.value),
        ticker=entity.ticker.split(":")[0] if entity.ticker else None,
        cik=entity.cik,
        lei=entity.lei,
    )
    
    await self.store_entity(graph_entity)
    return graph_entity
```

---

## API Design

### Unified Entity Access

```python
async with SEC() as sec:
    # =========================================
    # ENTITY LOOKUP (already implemented)
    # =========================================
    
    # Resolve any identifier
    apple = sec.resolve_entity("AAPL")
    apple = sec.resolve_entity("320193")
    apple = sec.resolve_entity("HWUPKR0MPOU8FGXBT394")  # LEI
    
    # Search by name
    results = sec.search_entities("apple computer")
    
    # Load registry (async)
    await sec.load_entities(refresh=True)
    
    
    # =========================================
    # PROPOSED: ENTITY-CENTRIC FILING QUERIES
    # =========================================
    
    # Get entity with all filings
    entity = await sec.get_entity("AAPL", include_filings=True)
    print(entity.recent_filings)  # Last 10 filings
    
    # Query filings by entity (not just ticker)
    filings = await sec.filings.for_entity(entity.entity_id)
    
    # Get entity profile (enriched)
    profile = await sec.get_entity_profile("AAPL")
    print(profile.lei)      # From GLEIF
    print(profile.figi)     # From OpenFIGI
    print(profile.sector)   # From SEC
    
    
    # =========================================
    # PROPOSED: ENTITY EXTRACTION
    # =========================================
    
    # Extract and resolve entities from filing
    filing = await sec.get_filing("0001045810-24-000123")
    mentions = await sec.extract_entities(filing)
    
    for mention in mentions:
        print(f"{mention.text} -> {mention.canonical.primary_name if mention.canonical else 'UNRESOLVED'}")
        print(f"  Relationship: {mention.relationship_type}")
        print(f"  Confidence: {mention.confidence}")
    
    
    # =========================================
    # PROPOSED: GRAPH QUERIES (via Entity Master)
    # =========================================
    
    # Find relationships (entities resolved via Entity Master)
    suppliers = await sec.graph.find_suppliers("NVDA")
    for s in suppliers:
        print(f"{s.entity.primary_name} (CIK: {s.entity.cik})")
        print(f"  LEI: {s.entity.lei}")  # Enriched!
        print(f"  Evidence: {s.evidence[:100]}...")
```

---

## Data Flow: Filing to Knowledge Graph

```
+----------------------------------------------------------------------------+
|                    FILING TO KNOWLEDGE GRAPH DATA FLOW                     |
+----------------------------------------------------------------------------+
|                                                                            |
|  1. FILING INGESTION                                                       |
|     +------------------------------------------------------------------+   |
|     | SEC EDGAR -> records table (FeedSpine)                           |   |
|     | accession_number, form_type, cik, filed_date                     |   |
|     +------------------------------------------------------------------+   |
|                                    |                                       |
|                                    v                                       |
|  2. ENTITY LINKAGE                                                         |
|     +------------------------------------------------------------------+   |
|     | EntityRegistry.resolve(cik) -> entity_id                         |   |
|     | filing_metadata.entity_id = entity_id                            |   |
|     +------------------------------------------------------------------+   |
|                                    |                                       |
|                                    v                                       |
|  3. SECTION EXTRACTION                                                     |
|     +------------------------------------------------------------------+   |
|     | Extract Item 1A, Item 1, Item 7, etc.                            |   |
|     | Store in extracted_sections table                                |   |
|     +------------------------------------------------------------------+   |
|                                    |                                       |
|                                    v                                       |
|  4. ENTITY EXTRACTION (LLM or Pattern)                                     |
|     +------------------------------------------------------------------+   |
|     | "We rely on TSMC for manufacturing..."                           |   |
|     | -> mention: "TSMC", type: "supplier"                             |   |
|     +------------------------------------------------------------------+   |
|                                    |                                       |
|                                    v                                       |
|  5. ENTITY RESOLUTION                                                      |
|     +------------------------------------------------------------------+   |
|     | EntityRegistry.resolve("TSMC")                                   |   |
|     | -> Entity(cik="1046179", ticker="TSM", lei="549300...")           |   |
|     +------------------------------------------------------------------+   |
|                                    |                                       |
|                                    v                                       |
|  6. ENTITY ENRICHMENT (Optional)                                           |
|     +------------------------------------------------------------------+   |
|     | EntityEnricher.enrich(entity)                                    |   |
|     | -> Add LEI from GLEIF                                            |   |
|     | -> Add FIGI from OpenFIGI                                        |   |
|     +------------------------------------------------------------------+   |
|                                    |                                       |
|                                    v                                       |
|  7. GRAPH STORAGE                                                          |
|     +------------------------------------------------------------------+   |
|     | Store entity node (if new)                                       |   |
|     | Store relationship edge with evidence                            |   |
|     | (:Company {cik:"1045810"})-[:SUPPLIER_OF]->(:Company {cik:"1046179"}) |
|     +------------------------------------------------------------------+   |
|                                    |                                       |
|                                    v                                       |
|  8. QUERYABLE KNOWLEDGE                                                    |
|     +------------------------------------------------------------------+   |
|     | sec.graph.find_suppliers("NVDA")                                 |   |
|     | -> Returns canonical entities with all identifiers               |   |
|     +------------------------------------------------------------------+   |
|                                                                            |
+----------------------------------------------------------------------------+
```

---

## Configuration

### Entity Master Settings

```python
# Add to EdgarSettings or StorageConfig

class EntityConfig(BaseSettings):
    """Entity Master configuration."""
    
    # Registry
    auto_load: bool = True              # Auto-load on first access
    refresh_interval_days: int = 7      # Refresh SEC data frequency
    
    # Storage
    entity_db_path: str = "sec_data/entities.duckdb"
    entity_cache_path: str = "sec_data/ref/entities.json"
    
    # Enrichment
    gleif_enabled: bool = True
    openfigi_enabled: bool = True
    openfigi_api_key: str | None = None
    enrichment_min_confidence: float = 0.80
    
    # Matching
    fuzzy_threshold: float = 0.70
    fuzzy_algorithm: str = "token_set"
    
    # External sources cache
    sec_companies_url: str = "https://www.sec.gov/files/company_tickers.json"
    sec_cache_max_age_days: int = 7
```

---

## Summary

### What We Have

| Component | Status | Notes |
|-----------|--------|-------|
| Entity Model | DONE | Entity, Identifier, Alias classes |
| Identifier Schemes | DONE | CIK, LEI, FIGI, ISIN, CUSIP, TICKER, DUNS |
| Entity Registry | DONE | In-memory with SEC data |
| Fuzzy Matching | DONE | rapidfuzz integration |
| GLEIF Client | DONE | LEI lookups |
| OpenFIGI Client | DONE | FIGI/ISIN/CUSIP lookups |
| Entity Store | DONE | DuckDB persistence |
| SEC Class Integration | DONE | resolve_entity, search_entities |

### What We Need

| Component | Priority | Effort |
|-----------|----------|--------|
| Link filing_metadata to entity_id | HIGH | Low |
| Resolve extracted entities | HIGH | Medium |
| Graph storage uses Entity Master | MEDIUM | Medium |
| Entity-centric filing queries | MEDIUM | Low |
| Auto-enrichment in pipeline | LOW | Medium |
| Elasticsearch entity index | LOW | Medium |

---

## Bulk Data Sources for Security Master

The Entity Master can be populated from multiple **free bulk download sources**:

### 1. SEC EDGAR (Already Integrated)

| File | URL | Contents | Records |
|------|-----|----------|---------|
| `company_tickers.json` | `sec.gov/files/company_tickers.json` | CIK, ticker, company name | ~10,000 |
| `company_tickers_exchange.json` | `sec.gov/files/company_tickers_exchange.json` | CIK, ticker, name, **exchange** | ~10,000 |
| `company.idx` | Full-index files | CIK, company name, form type, date | All filers |

**Fields**: CIK, ticker, company name, exchange (NYSE, Nasdaq, OTC)

### 2. GLEIF Golden Copy (LEI Data) - FREE BULK DOWNLOAD

| File | URL | Contents | Records |
|------|-----|----------|---------|
| LEI-CDF v3.1 | `gleif.org/lei-data/gleif-golden-copy` | Full LEI database | **3.19M entities** |
| RR-CDF v2.1 | Same | Ownership relationships | 463K relationships |
| ISIN-to-LEI | `gleif.org/lei-data/lei-mapping` | ISIN ↔ LEI mapping | ~2M |
| BIC-to-LEI | Same | SWIFT BIC ↔ LEI | Financial institutions |

**Fields**: LEI, legal name, jurisdiction, registration authority, status, parent LEI

```
Download: https://goldencopy.gleif.org/api/v2/golden-copies/publishes/latest
Format: XML, JSON, CSV (compressed)
Update: 3x daily
License: CC0 (public domain)
```

### 3. OpenFIGI (Already Integrated via API)

| Endpoint | Contents |
|----------|----------|
| `/v3/mapping` | Ticker/ISIN/CUSIP → FIGI |
| `/v3/search` | Name search → FIGI |

**Fields**: FIGI, ticker, exchange, market sector, security type, share class

### 4. Thomson Reuters / Refinitiv PermID

You mentioned having Thomson data at `G:\THOMSON`. Common files include:

| File Pattern | Contents |
|--------------|----------|
| `*.csv` / `*.txt` | PermID, company name, ticker, ISIN, CUSIP |
| Entity files | PermID (organization ID), legal name, LEI, country |
| Quote files | RIC (Reuters Instrument Code), exchange, ticker |

**To import**: Need to map PermID → our Entity Master format

### 5. Bloomberg Open Symbology (BSYM)

You mentioned having Bloomberg data at `G:\BLOOMBERG`. Common files include:

| File Pattern | Contents |
|--------------|----------|
| `bsym_*.csv` | FIGI, ticker, exchange, market sector |
| `bbgid_*.csv` | Bloomberg Global ID mappings |

**Note**: Bloomberg Open FIGI is now the primary free source (same as OpenFIGI above)

### 6. Additional Free Sources

| Source | URL | Contents |
|--------|-----|----------|
| **SEC SIC Codes** | `sec.gov/cgi-bin/browse-edgar?action=getcompany&SIC=*` | Industry classification |
| **SEC Company Search** | `efts.sec.gov/LATEST/search-index` | Full-text entity search |
| **EDGAR Full Index** | `sec.gov/Archives/edgar/full-index/` | All filings by CIK |
| **SEC Submissions** | `data.sec.gov/submissions/CIK*.json` | Company metadata, recent filings |
| **OpenCorporates** | `opencorporates.com` | Company registry data (API) |
| **Wikidata** | `wikidata.org` | Company identifiers (SPARQL) |

---

## Proposed Entity Master Fields to Add

Based on available bulk data, consider adding these fields:

```python
@dataclass
class Entity:
    # ... existing fields ...
    
    # NEW: Industry Classification
    sic_code: str | None = None           # SEC SIC code (4 digits)
    sic_description: str | None = None    # "Computer & Office Equipment"
    naics_code: str | None = None         # NAICS code (6 digits)
    gics_sector: str | None = None        # GICS sector
    gics_industry: str | None = None      # GICS industry group
    
    # NEW: Company Details
    state_of_incorporation: str | None = None  # "DE", "NV", etc.
    fiscal_year_end: str | None = None         # "1231" (MMDD)
    irs_number: str | None = None              # IRS employer ID
    
    # NEW: Market Data
    market_cap_category: str | None = None     # "large", "mid", "small", "micro"
    primary_exchange: str | None = None        # "NYSE", "NASDAQ", "OTC"
    listing_status: str | None = None          # "listed", "delisted", "otc"
    
    # NEW: Ownership
    parent_entity_id: str | None = None        # Ultimate parent
    ownership_percentage: float | None = None  # If subsidiary
```

---

## Bulk Import Scripts (Proposed)

### Import GLEIF Golden Copy

```python
async def import_gleif_golden_copy(file_path: str) -> int:
    """Import GLEIF LEI data into Entity Master.
    
    Download from: https://goldencopy.gleif.org/api/v2/golden-copies/publishes/latest
    
    Returns:
        Number of entities imported/updated
    """
    import json
    from py_sec_edgar.core.identity import (
        Entity, EntityType, EntityStatus, Identifier, Alias, get_entity_registry
    )
    
    registry = get_entity_registry()
    count = 0
    
    with open(file_path, 'r') as f:
        for line in f:
            record = json.loads(line)
            lei = record.get('LEI', {})
            
            entity = Entity(
                entity_type=EntityType.COMPANY,
                status=EntityStatus.ACTIVE if lei.get('EntityStatus') == 'ACTIVE' else EntityStatus.INACTIVE,
                primary_name=lei.get('LegalName', {}).get('$'),
                jurisdiction=lei.get('LegalJurisdiction'),
                identifiers=[
                    Identifier.lei(lei.get('LEI'), source='gleif_golden_copy'),
                ],
                aliases=[
                    Alias(
                        name=lei.get('LegalName', {}).get('$'),
                        alias_type='legal',
                        source='gleif_golden_copy',
                        is_primary=True
                    )
                ],
                metadata={
                    'gleif_registration_authority': lei.get('RegistrationAuthority', {}).get('RegistrationAuthorityID'),
                    'gleif_entity_category': lei.get('EntityCategory'),
                }
            )
            
            registry.register(entity)
            count += 1
    
    return count
```

### Import Thomson/Refinitiv PermID

```python
async def import_thomson_permid(file_path: str) -> int:
    """Import Thomson Reuters PermID data.
    
    Expected CSV columns: PermID, LegalName, Ticker, Exchange, ISIN, LEI, Country
    """
    import csv
    from py_sec_edgar.core.identity import Entity, Identifier, get_entity_registry
    
    registry = get_entity_registry()
    count = 0
    
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            identifiers = [
                Identifier(scheme='permid', value=row['PermID'], source='thomson')
            ]
            if row.get('ISIN'):
                identifiers.append(Identifier.isin(row['ISIN'], source='thomson'))
            if row.get('LEI'):
                identifiers.append(Identifier.lei(row['LEI'], source='thomson'))
            if row.get('Ticker') and row.get('Exchange'):
                identifiers.append(Identifier.ticker(row['Ticker'], row['Exchange'], source='thomson'))
            
            entity = Entity(
                primary_name=row['LegalName'],
                jurisdiction=row.get('Country'),
                identifiers=identifiers,
            )
            registry.register(entity)
            count += 1
    
    return count
```

### Import SEC company_tickers_exchange.json

```python
async def import_sec_tickers_exchange() -> int:
    """Import SEC company tickers with exchange info.
    
    Source: https://www.sec.gov/files/company_tickers_exchange.json
    """
    import httpx
    from py_sec_edgar.core.identity import Entity, Identifier, get_entity_registry
    
    url = "https://www.sec.gov/files/company_tickers_exchange.json"
    
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers={"User-Agent": "py-sec-edgar/1.0"})
        data = resp.json()
    
    registry = get_entity_registry()
    count = 0
    
    # Format: {"fields": ["cik","name","ticker","exchange"], "data": [[cik, name, ticker, exchange], ...]}
    for row in data['data']:
        cik, name, ticker, exchange = row
        
        identifiers = [
            Identifier.cik(str(cik).zfill(10), source='sec_exchange_json'),
        ]
        if ticker:
            identifiers.append(Identifier.ticker(ticker, exchange or 'UNKNOWN', source='sec_exchange_json'))
        
        entity = Entity(
            primary_name=name,
            jurisdiction='US',
            identifiers=identifiers,
            metadata={'exchange': exchange} if exchange else {},
        )
        registry.register(entity)
        count += 1
    
    return count
```

---

## Data Refresh Strategy

| Source | Frequency | Method |
|--------|-----------|--------|
| SEC company_tickers | Weekly | HTTP download |
| GLEIF Golden Copy | Monthly | Bulk download (3GB compressed) |
| OpenFIGI | On-demand | API call per entity |
| Thomson/Bloomberg | Manual | Import from local files |

---

### Key Design Principles

1. **Modular**: Entity Master works standalone or integrated
2. **Source of Truth**: All entities flow through Entity Master
3. **Universal Resolution**: Any identifier -> canonical entity
4. **Enrichment Ready**: LEI/FIGI added on demand
5. **Audit Trail**: Full history of entity changes
6. **Multi-Tier Compatible**: Works with DuckDB, Postgres, Neo4j
