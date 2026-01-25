# EntitySpine Ingestion Architecture

## Overview

EntitySpine's ingestion system is designed as a **first-class feature** that handles:

1. **Multi-vendor data sources** with different schemas and formats
2. **Dynamic field mapping** via LLM-assisted schema generation
3. **Temporal versioning** with date-based priority and history
4. **Corporate actions** (mergers, acquisitions, spin-offs)
5. **Source priority ranking** (Bloomberg > FactSet > Thomson > SEC)
6. **Schema evolution** without data loss

---

## Core Concepts

### 1. Source Priority System

Each data source has a **priority rank** that determines which value wins in conflicts:

```
┌─────────────────────────────────────────────────────────┐
│  Source Priority (Highest to Lowest)                    │
├─────────────────────────────────────────────────────────┤
│  1. Bloomberg    - Gold standard for market data        │
│  2. FactSet      - Strong corporate fundamentals        │
│  3. Refinitiv    - Good for identifiers (PermID)        │
│  4. SEC EDGAR    - Authoritative for US filings         │
│  5. User Input   - Manual corrections                   │
│  6. Derived      - Computed/inferred values             │
└─────────────────────────────────────────────────────────┘
```

### 2. Temporal Versioning

Every piece of data has temporal dimensions:

```
┌─────────────────────────────────────────────────────────┐
│  Time Dimensions                                        │
├─────────────────────────────────────────────────────────┤
│  captured_at   - When we observed/ingested the data     │
│  valid_from    - When the data became true (business)   │
│  valid_to      - When the data stopped being true       │
│  source_date   - Date from the vendor's file            │
│  file_date     - When the vendor generated the file     │
└─────────────────────────────────────────────────────────┘
```

### 3. Entity Lifecycle States

```
                    ┌──────────────┐
                    │   PENDING    │ ← New unverified entity
                    └──────┬───────┘
                           │ verify
                           ▼
                    ┌──────────────┐
         ┌─────────│    ACTIVE    │←────────┐
         │         └──────┬───────┘         │
         │                │                 │
    merge/acquire         │ deactivate    reactivate
         │                │                 │
         ▼                ▼                 │
┌────────────────┐ ┌──────────────┐         │
│   MERGED_INTO  │ │   INACTIVE   │─────────┘
└────────────────┘ └──────┬───────┘
                          │ dissolve
                          ▼
                   ┌──────────────┐
                   │  DISSOLVED   │
                   └──────────────┘
```

---

## Ingestion Pipeline

### Phase 1: Schema Discovery (LLM-Assisted)

Users provide:
1. Sample data (headers + 5-10 rows)
2. Source metadata (vendor, date, format)

The LLM generates:
1. Field mappings to EntitySpine schema
2. Transformation rules
3. Validation constraints

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Raw Data File  │────▶│  LLM Mapper     │────▶│  Mapping Config │
│  + Headers      │     │  (Schema Gen)   │     │  (JSON/YAML)    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

### Phase 2: Data Transformation

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Mapping Config │────▶│  Transformer    │────▶│  Staged Data    │
│  + Raw Data     │     │  Engine         │     │  (Validated)    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

### Phase 3: Conflict Resolution

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Staged Data    │────▶│  Resolver       │────▶│  Merged Entity  │
│  + Existing     │     │  (Priority +    │     │  Graph          │
│                 │     │   Temporal)     │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

### Phase 4: Corporate Actions

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Merger/Acq     │────▶│  Action         │────▶│  Updated Graph  │
│  Events         │     │  Processor      │     │  + History      │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

---

## Dynamic Field Mapping

### The Problem

Different vendors have different column names for the same concept:

| Concept | Bloomberg | FactSet | Thomson | SEC |
|---------|-----------|---------|---------|-----|
| Company Name | NAME | Name | organization-name | conformed-name |
| Ticker | ID_BB_SEC_NUM_DES | Identifier | - | ticker-symbol |
| Country | CNTRY_OF_DOMICILE | Country | isDomiciledIn | state-country |
| Industry | INDUSTRY_SECTOR | FactSet Industry | - | sic-code |
| Website | COMPANY_WEBSITE | Website | - | - |
| Market Cap | CUR_MKT_CAP | Market Capitalization | - | - |

### The Solution: LLM-Assisted Mapping

#### Step 1: Export Schema for LLM

```python
from entityspine.data.schema_export import export_schema_for_llm

schema_prompt = export_schema_for_llm()
# Returns a formatted description of all Entity fields
```

#### Step 2: User Provides Sample Data

```
Headers: NAME|TICKER|FEED_SOURCE|ID_BB_UNIQUE|SECURITY_TYP|MARKET_SECTOR_DES|CNTRY_OF_DOMICILE|COMPANY_WEBSITE
Row 1: Apple Inc|AAPL|US|EQ0010169500001000|Common Stock|Technology|US|https://www.apple.com
Row 2: Microsoft Corp|MSFT|US|EQ0010174300001000|Common Stock|Technology|US|https://www.microsoft.com
```

#### Step 3: LLM Generates Mapping

```yaml
source_type: bloomberg
mapping:
  entity:
    primary_name: NAME
    jurisdiction: CNTRY_OF_DOMICILE
    entity_type:
      column: MARKET_SECTOR_DES
      transform: sector_to_entity_type
  security:
    security_type:
      column: SECURITY_TYP
      transform: bloomberg_security_type
  listing:
    ticker: TICKER
    exchange:
      column: FEED_SOURCE
      transform: feed_source_to_mic
  identifiers:
    - scheme: FIGI
      column: ID_BB_GLOBAL
    - scheme: BBUID
      column: ID_BB_UNIQUE
  extended_attributes:
    - name: website
      column: COMPANY_WEBSITE
      type: url
    - name: market_sector
      column: MARKET_SECTOR_DES
      type: string
```

---

## Version Control & History

### Entity Version Table

```sql
CREATE TABLE entity_versions (
    version_id      TEXT PRIMARY KEY,
    entity_id       TEXT NOT NULL,
    version_number  INTEGER NOT NULL,
    
    -- Snapshot of entity state
    primary_name    TEXT,
    entity_type     TEXT,
    status          TEXT,
    jurisdiction    TEXT,
    -- ... all fields
    
    -- Temporal
    valid_from      DATE,
    valid_to        DATE,
    
    -- Provenance
    source_system   TEXT,
    source_date     DATE,
    ingestion_id    TEXT,
    
    -- Change tracking
    change_type     TEXT,  -- CREATE, UPDATE, MERGE, SPLIT
    change_reason   TEXT,
    changed_fields  JSON,
    previous_version_id TEXT,
    
    created_at      TIMESTAMP
);
```

### Ingestion Log

```sql
CREATE TABLE ingestion_log (
    ingestion_id    TEXT PRIMARY KEY,
    
    -- Source info
    source_type     TEXT,
    source_file     TEXT,
    source_date     DATE,
    file_hash       TEXT,
    
    -- Processing stats
    started_at      TIMESTAMP,
    completed_at    TIMESTAMP,
    status          TEXT,
    
    -- Counts
    rows_processed  INTEGER,
    entities_created INTEGER,
    entities_updated INTEGER,
    entities_merged  INTEGER,
    conflicts_resolved INTEGER,
    errors          INTEGER,
    
    -- Config used
    mapping_config  JSON,
    priority_config JSON
);
```

---

## Corporate Action Handling

### Scenario 1: Merger (A acquires B)

```
Before:
┌─────────────┐     ┌─────────────┐
│  Company A  │     │  Company B  │
│  AAPL       │     │  BEATS      │
└─────────────┘     └─────────────┘

After:
┌─────────────────────────────────────────┐
│  Company A (expanded)                   │
│  AAPL                                   │
│  ├── [historical] Beats Electronics     │
│  │   status: MERGED_INTO                │
│  │   merged_into: AAPL entity_id        │
│  │   merge_date: 2014-08-01             │
│  └── All B's securities → A             │
└─────────────────────────────────────────┘
```

**Process:**
1. Mark Company B as `MERGED_INTO`
2. Set `successor_entity_id` to Company A's ID
3. Transfer all securities/listings to Company A (with history)
4. Keep historical identifiers searchable
5. Create merge event in timeline

### Scenario 2: Spin-off (A creates B)

```
Before:
┌─────────────────────────────────┐
│  Company A                       │
│  Includes: Division X           │
└─────────────────────────────────┘

After:
┌─────────────────┐     ┌─────────────────┐
│  Company A      │     │  Company B      │
│  (reduced)      │     │  (Division X)   │
│                 │◄────│  spun_from: A   │
└─────────────────┘     └─────────────────┘
```

### Scenario 3: Name Change

```
Timeline:
├── 2012: Research In Motion (RIM)
├── 2013: Name change to BlackBerry
└── 2024: Still BlackBerry

Entity:
{
  entity_id: "ent_001",
  primary_name: "BlackBerry Limited",  // Current
  names: [
    {name: "BlackBerry Limited", valid_from: "2013-01-30"},
    {name: "Research In Motion Limited", valid_from: "1999", valid_to: "2013-01-30"}
  ]
}
```

---

## Conflict Resolution Rules

### Priority Matrix

| Conflict Type | Resolution Strategy |
|--------------|---------------------|
| Name differs | Higher priority source wins, keep alternates |
| Identifier conflict | Keep both, flag for review |
| Status differs | Most restrictive wins (INACTIVE > ACTIVE) |
| Date differs | Earlier date wins (with validation) |
| Missing field | Fill from any source |

### Resolution Algorithm

```python
def resolve_conflict(existing, incoming, field):
    # 1. Check source priority
    if source_priority(incoming) > source_priority(existing):
        return incoming[field]
    
    # 2. Check temporal freshness
    if incoming.source_date > existing.source_date:
        return incoming[field]
    
    # 3. Check confidence scores
    if incoming.confidence > existing.confidence:
        return incoming[field]
    
    # 4. Keep existing
    return existing[field]
```

---

## Extended Attributes System

For fields that don't fit the core schema (like `website`, `market_sector_des`):

```python
@dataclass
class ExtendedAttribute:
    """Dynamic attribute storage."""
    entity_id: str
    attribute_name: str
    attribute_value: Any
    value_type: str  # string, number, date, url, json
    source_system: str
    source_date: date
    captured_at: datetime
    confidence: float = 1.0
```

This allows:
- Storing ANY vendor-specific field
- Querying by attribute name
- Preserving full provenance
- No schema migrations needed

---

## Example: Complex Multi-Source Ingestion

### Scenario: Building Apple Inc's Entity

**Sources available:**
1. Bloomberg BBUID (2016-05-30)
2. FactSet Companies (2019-08-01)
3. Thomson PermID (2020-08-30)
4. SEC EDGAR (live)

**Ingestion Order:**
1. Load Bloomberg first (highest priority)
2. Merge FactSet (fill gaps, version updates)
3. Merge Thomson (add PermID identifier)
4. Merge SEC (add CIK, official filings data)

**Result:**

```json
{
  "entity_id": "ent_AAPL_001",
  "primary_name": "Apple Inc",  // From Bloomberg (highest priority)
  "entity_type": "ORGANIZATION",
  
  "jurisdiction": "US",  // Confirmed by all sources
  "sic_code": "3571",    // From SEC (authoritative)
  
  "identifiers": [
    {"scheme": "CIK", "value": "0000320193", "source": "sec_edgar"},
    {"scheme": "FIGI", "value": "BBG000B9XRY4", "source": "bloomberg"},
    {"scheme": "PERMID", "value": "4295905573", "source": "thomson"},
    {"scheme": "TICKER", "value": "AAPL", "listing_id": "lst_001"}
  ],
  
  "securities": [
    {
      "security_id": "sec_AAPL_001",
      "security_type": "COMMON_STOCK",
      "listings": [
        {"mic": "XNAS", "ticker": "AAPL", "is_primary": true}
      ]
    }
  ],
  
  "extended_attributes": {
    "website": {"value": "https://www.apple.com", "source": "bloomberg"},
    "market_sector": {"value": "Technology", "source": "bloomberg"},
    "employees": {"value": 164000, "source": "factset", "as_of": "2019-08-01"}
  },
  
  "provenance": {
    "sources": ["bloomberg", "factset", "thomson", "sec_edgar"],
    "last_updated": "2024-01-15",
    "versions": 4
  }
}
```

---

## API for Ingestion

### 1. Create Mapping from Sample

```python
from entityspine.data.ingestion import IngestPipeline

pipeline = IngestPipeline()

# Option A: Use LLM to generate mapping
mapping = pipeline.generate_mapping_with_llm(
    sample_file="bloomberg_sample.csv",
    source_type="bloomberg",
    llm_provider="openai"  # or "anthropic", "local"
)

# Option B: Load existing mapping
mapping = pipeline.load_mapping("mappings/bloomberg_2016.yaml")
```

### 2. Execute Ingestion

```python
result = pipeline.ingest(
    source_file="G:/BLOOMBERG/Equity_Common_Stock_20160530.txt",
    mapping=mapping,
    options={
        "source_priority": 1,  # Bloomberg = highest
        "source_date": "2016-05-30",
        "batch_size": 10000,
        "on_conflict": "priority",  # or "newer", "manual"
        "create_versions": True,
    }
)

print(f"Created: {result.entities_created}")
print(f"Updated: {result.entities_updated}")
print(f"Conflicts: {result.conflicts_resolved}")
```

### 3. Handle Corporate Actions

```python
from entityspine.data.corporate_actions import CorporateActionProcessor

processor = CorporateActionProcessor(store)

# Record a merger
processor.merge_entities(
    acquired_entity_id="ent_BEATS_001",
    acquirer_entity_id="ent_AAPL_001",
    effective_date=date(2014, 8, 1),
    deal_type="acquisition",
    transfer_securities=True,
    preserve_history=True,
)

# Record a spin-off
processor.spinoff_entity(
    parent_entity_id="ent_EBAY_001",
    new_entity_name="PayPal Holdings Inc",
    effective_date=date(2015, 7, 20),
    transferred_securities=["sec_PYPL_001"],
)
```

---

## LLM Prompt Template for Schema Mapping

See `INGESTION_LLM_PROMPT.md` for the full prompt template that users can send to ChatGPT/Claude to generate field mappings.

---

## Implementation Checklist

- [ ] Extended attributes table/storage
- [ ] Version history tracking
- [ ] Ingestion log
- [ ] Corporate action processor
- [ ] Conflict resolution engine
- [ ] LLM mapping generator
- [ ] Schema export for LLM
- [ ] Mapping config loader (YAML/JSON)
- [ ] Priority-based field resolver
- [ ] Temporal query support
- [ ] Migration tools for mergers
- [ ] Audit trail
- [ ] Rollback capability

---

## Next Steps

1. Review this architecture
2. Implement ExtendedAttribute storage
3. Build the CorporateActionProcessor
4. Create the LLM prompt template
5. Build complex test scenarios
6. Add version history queries
