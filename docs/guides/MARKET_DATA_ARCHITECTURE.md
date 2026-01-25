# Market Infrastructure Data Architecture

## Overview

EntitySpine implements a Bronze/Silver/Gold data architecture for managing market infrastructure reference data from authoritative sources:

| Source | Bronze Snapshot | Silver Records | Gold Registry | Records |
|--------|----------------|----------------|---------------|---------|
| **ISO 10383 MIC** | `MICSnapshot` | `MICRecord` | `MICRegistry` | ~2,800 |
| **ISO 3166 Countries** | `CountrySnapshot` | `CountryRecord` | `CountryRegistry` | ~250 |
| **ISO 4217 Currencies** | `CurrencySnapshot` | `CurrencyRecord` | `CurrencyRegistry` | ~180 |
| **GLEIF LEI** | `LEISnapshot` | `LEIRecord` | `LEIRegistry` | ~2.5M |
| **SEC Tickers** | `SECTickerSnapshot` | dict records | Direct list | ~10,300 |
| **GLEIF ISIN-LEI** | `ISINLEISnapshot` | `ISINLEIMapping` | - | ~8M |
| **GLEIF BIC-LEI** | `BICLEISnapshot` | `BICLEIMapping` | - | ~40K |

### Registry API Consistency

All registries provide both `get()` and `lookup()` methods for consistency:

```python
# All of these work identically:
registry.get("XNYS")    # MIC, LEI, Country, Currency
registry.lookup("XNYS") # Same result
```

## Architecture Layers

### Bronze Layer: Raw Snapshots
- **What**: Immutable raw downloads from authoritative sources
- **Purpose**: Audit trail, historical comparison, replay capability
- **Storage**: Files with metadata (hash, timestamp, etag)

```python
@dataclass(frozen=True, slots=True)
class MICSnapshot:
    snapshot_id: str
    source_url: str
    content_hash: str  # SHA-256
    content_size: int
    record_count: int
    etag: str | None
    last_modified: str | None
    captured_at: datetime
    raw_path: str | None
```

### Silver Layer: Normalized Records
- **What**: Parsed and standardized records with consistent field names
- **Purpose**: Query-ready data with provenance links
- **Storage**: Database tables or in-memory

```python
@dataclass(frozen=True, slots=True)
class MICRecord:
    mic: str                        # Primary identifier (4 chars)
    operating_mic: str              # Parent MIC for segments
    mic_type: str                   # OPRT (operating) or SGMT (segment)
    name: str                       # Full market name
    legal_entity_name: str | None   # Operator legal name
    lei: str | None                 # LEI of operator (links to entities!)
    market_category_code: str | None
    country_code: str | None
    city: str | None
    website: str | None
    status: str                     # ACTIVE, EXPIRED, DELETED
    # ... timestamps and provenance
```

### Gold Layer: Registry API
- **What**: Fast, ergonomic lookups for application use
- **Purpose**: O(1) lookups, hierarchical navigation, search
- **Storage**: In-memory indices

```python
class MICRegistry:
    def get(self, mic: str) -> MICRecord | None
    def get_segments(self, operating_mic: str) -> list[MICRecord]
    def get_by_country(self, country_code: str) -> list[MICRecord]
    def search(self, query: str) -> list[MICRecord]
```

## Data Sources

### ISO 10383 MIC List
- **URL**: https://www.iso20022.org/sites/default/files/ISO10383_MIC/ISO10383_MIC.csv
- **Update Cadence**: Quarterly (sometimes monthly)
- **Records**: ~2,800 MIC codes
- **Includes**: LEI for most operating MICs (huge win for entity linking!)

### GLEIF MIC-to-LEI Mapping
- **URL**: GLEIF provides relationship files
- **Purpose**: Connects exchange MICs to legal entity LEIs
- **Use Case**: Build "exchange operator" entities in Entity Spine

## Usage Examples

### Basic Lookup
```python
from entityspine.sources import MICRegistry

registry = MICRegistry()
await registry.load_from_source()

# Lookup NYSE
nyse = registry.get("XNYS")
print(f"NYSE: {nyse.name}")
print(f"NYSE LEI: {nyse.lei}")  # 5493000F4ZO33MV32P92
```

### Get Exchange Segments
```python
# NASDAQ has 19 segments
nasdaq_segments = registry.get_segments("XNAS")
for seg in nasdaq_segments:
    print(f"  {seg.mic}: {seg.name}")
# XNMS: NASDAQ/NMS (GLOBAL MARKET)
# XNGS: NASDAQ/NGS (GLOBAL SELECT MARKET)
# XNCM: NASDAQ/CAPITAL MARKET
# ... etc
```

### Search Markets
```python
# Find all Tokyo exchanges
tokyo = registry.search("Tokyo")
for t in tokyo:
    print(f"{t.mic}: {t.name}")
```

### Change Detection (Diff)
```python
from entityspine.sources import diff_mic_records

# Compare two snapshots
changes = diff_mic_records(old_records, new_records)
for change in changes:
    print(f"{change.mic}.{change.field_name}: {change.old_value} -> {change.new_value}")
```

## Relationship to Entity Spine

The MIC data integrates with Entity Spine in several ways:

1. **Exchange Entities**: Each operating MIC can be an Entity with claims
2. **LEI Linking**: The ISO data includes LEI, enabling direct links to GLEIF entities
3. **Listing Resolution**: When resolving tickers, MIC identifies the exchange
4. **Multi-venue**: Track same security across multiple MIC-identified venues

### Claim Pattern
```python
# Exchange as entity with multiple identifier claims
entity = Entity(primary_name="New York Stock Exchange")

claims = [
    IdentifierClaim(scheme=IdentifierScheme.MIC, value="XNYS"),
    IdentifierClaim(scheme=IdentifierScheme.LEI, value="5493000F4ZO33MV32P92"),
]
```

## Curated Major Venues vs Full MIC List

We maintain **two layers**:

### Full MIC List (from ISO)
- Complete, authoritative
- Covers ~2,800 venues including obscure ones
- Includes reporting facilities, systematic internalizers
- Updated automatically from ISO 20022

### Curated Major Venues (in reference_data/markets.py)
- Hand-maintained subset of important venues
- Adds context not in ISO: asset classes, venue types
- Groups by region (US, Europe, APAC, etc.)
- Includes vendor code mappings (Bloomberg, Thomson, FactSet)

## File Structure

```
entityspine/src/entityspine/
├── sources/
│   ├── __init__.py              # Exports all sources
│   ├── iso10383.py              # ISO 10383 MIC source + registry
│   ├── gleif_mic_lei.py         # GLEIF MIC-to-LEI mappings
│   └── sec.py                   # SEC tickers (existing)
├── domain/
│   ├── markets.py               # Exchange, ExchangeSegment models
│   └── reference_data/
│       └── markets.py           # Curated major venues
```

## Recommended Sync Schedule

| Source | Frequency | Rationale |
|--------|-----------|-----------|
| ISO 10383 MIC | Weekly | Updates quarterly, weekly catches changes fast |
| GLEIF MIC-LEI | Weekly | Synced with GLEIF update cadence |
| SEC Tickers | Daily | Changes with new listings/delistings |

## Next Steps

1. **CLI Commands**: Add `entityspine mic download`, `entityspine mic lookup`
2. **Database Storage**: Store Bronze/Silver in SQLite for persistence
3. **Auto-sync**: Background task to check for MIC updates
4. **Exchange Entity Builder**: Auto-create Entity records from MIC data with LEI claims
