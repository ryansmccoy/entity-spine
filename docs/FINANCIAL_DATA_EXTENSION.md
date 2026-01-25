# Financial Data Extension: FinancialSpine

This document describes how the EntitySpine patterns extend to financial data via a companion `financialspine` package.

## Architecture Layering

```
┌─────────────────────────────────────────────────────────────────┐
│                    Consumer Applications                         │
│  (Analytics, Reporting, Investment Models, LLM Agents)          │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                   FinancialSpine                                 │
│  - Financial statements (income, balance sheet, cash flow)       │
│  - Key metrics (EPS, P/E, ROE, etc.)                            │
│  - Time series (prices, volumes, rates)                          │
│  - Event data (earnings, dividends, splits)                      │
│  - Links TO EntitySpine via entity_id / security_id             │
└──────────────────────────┬──────────────────────────────────────┘
                           │ entity_id / security_id
┌──────────────────────────▼──────────────────────────────────────┐
│                    EntitySpine (core identity)                   │
│  - Entities (companies, funds, governments)                      │
│  - Securities (stocks, bonds, derivatives)                       │
│  - Listings (exchange-specific)                                  │
│  - Identifier claims (CUSIP, ISIN, FIGI, LEI, etc.)             │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                    Data Sources                                  │
│  FactSet | Bloomberg | Thomson | Compustat | CRSP | etc.         │
└─────────────────────────────────────────────────────────────────┘
```

## Why Separate Packages?

**EntitySpine** handles **identity resolution**:
- Who is this company?
- What identifiers does it have?
- What securities has it issued?
- Where do they trade?

**FinancialSpine** handles **financial content**:
- What are its revenues?
- What's the stock price history?
- When did it pay dividends?
- What were last quarter's earnings?

Both use the same patterns:
- Multi-source ingestion with LLM-assisted mapping
- Source priority hierarchies
- Temporal versioning
- Parquet storage

## FinancialSpine Conceptual Schema

```python
# financialspine/domain/statement.py

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum

class PeriodType(str, Enum):
    ANNUAL = "annual"        # FY / 10-K
    QUARTERLY = "quarterly"  # Q1-Q4 / 10-Q
    TTM = "ttm"             # Trailing Twelve Months
    YTD = "ytd"             # Year to Date
    MONTHLY = "monthly"

class SeriesType(str, Enum):
    PRICE = "price"
    ADJUSTED_PRICE = "adjusted_price"
    VOLUME = "volume"
    DIVIDEND = "dividend"
    SPLIT_FACTOR = "split_factor"

class Frequency(str, Enum):
    TICK = "tick"
    MINUTE = "minute"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"

@dataclass(frozen=True)
class FinancialStatement:
    """Periodic financial report (10-K, 10-Q)."""
    statement_id: str
    entity_id: str  # FK to EntitySpine
    
    period_type: PeriodType
    fiscal_period: str  # "2024Q1", "2024FY"
    filing_date: date
    period_end_date: date
    
    # Provenance
    source_system: str
    source_priority: int
    captured_at: datetime

@dataclass(frozen=True)
class FinancialMetric:
    """Single financial data point with versioning."""
    metric_id: str
    statement_id: str | None  # Optional FK to statement
    entity_id: str  # FK to EntitySpine
    security_id: str | None  # Optional FK for per-share metrics
    
    metric_name: str  # "revenue", "eps_diluted", "total_assets"
    value: Decimal
    currency: str
    unit: str | None  # "millions", "thousands", etc.
    
    period_type: PeriodType
    fiscal_period: str
    
    # Versioning & Priority (same as EntitySpine)
    source_system: str  # "compustat", "bloomberg", "factset"
    source_priority: int  # 1=highest
    captured_at: datetime
    valid_from: datetime
    valid_to: datetime | None  # None = current

@dataclass(frozen=True)
class TimeSeries:
    """Price/volume time series."""
    series_id: str
    listing_id: str  # FK to EntitySpine Listing
    
    series_type: SeriesType
    frequency: Frequency
    currency: str
    
    # Data stored in Parquet with columns:
    # date, value, source_system, source_priority
    data_path: str  # Path to Parquet file
```

## Example: Compustat Quarterly Ingestion

Using the **same LLM mapping approach** for Compustat quarterly data:

### Sample Data

```csv
gvkey,datadate,fyearq,fqtr,tic,cusip,revtq,niq,epspxq,atq,ltq
001690,2024-03-31,2024,1,AAPL,037833100,90753.0,23636.0,1.53,352583.0,279414.0
```

### LLM-Generated Mapping

```yaml
source_type: "compustat_fundq"
description: "Compustat North America Fundamentals Quarterly"
file_format:
  delimiter: ","
  encoding: "utf-8"

# EntitySpine resolution keys
entity_resolution:
  lookup_by:
    - scheme: "CUSIP"
      column: "cusip"
    - scheme: "TICKER"
      column: "tic"
  fallback_create: false  # Don't create entities, require resolution

column_mappings:
  statement:
    period_type:
      default: "QUARTERLY"
    fiscal_period:
      columns: ["fyearq", "fqtr"]
      transform: "format_fiscal_period"  # -> "2024Q1"
    period_end_date:
      column: "datadate"

  metrics:
    - name: "revenue"
      column: "revtq"
      type: "decimal"
      unit: "millions"
    - name: "net_income"
      column: "niq"
      type: "decimal"
      unit: "millions"
    - name: "eps_diluted"
      column: "epspxq"
      type: "decimal"
    - name: "total_assets"
      column: "atq"
      type: "decimal"
      unit: "millions"
    - name: "total_liabilities"
      column: "ltq"
      type: "decimal"
      unit: "millions"
    # ... 100s more metrics

  skip_columns:
    - "gvkey"  # Compustat internal ID

transforms:
  format_fiscal_period:
    code: |
      def transform(row):
          return f"{row['fyearq']}Q{row['fqtr']}"
```

### Ingestion Code

```python
from financialspine.data.ingest import FinancialIngestPipeline
from entityspine.data.parquet_store import ParquetEntityStore
import yaml

# Load entity index for resolution
entity_store = ParquetEntityStore("entityspine_data/")

# Load mapping
with open("mappings/compustat_fundq.yaml") as f:
    mapping = yaml.safe_load(f)

# Run ingestion
pipeline = FinancialIngestPipeline(entity_store=entity_store)
result = pipeline.ingest(
    source_file="/data/compustat/fundq_2024.csv",
    mapping=mapping,
    source_priority=2,  # Compustat is priority 2
)

print(f"Loaded {result.statements} statements, {result.metrics} metrics")
print(f"Unresolved: {len(result.unresolved_entities)} entities not in EntitySpine")
```

## Source Priority Hierarchy

Same pattern as EntitySpine:

| Priority | Source | Use Case |
|----------|--------|----------|
| 1 | Bloomberg | Primary for listed companies |
| 2 | Compustat | Primary for fundamentals |
| 3 | FactSet | Backup / broader coverage |
| 4 | SEC EDGAR | Official filings |
| 5 | Manual | User overrides |

## Migration When Entities Merge

When an entity is acquired (EntitySpine tracks via `successor_entity_id`):

```python
from entityspine.domain import Entity
from financialspine.services import FinancialMigrationService

def handle_acquisition(acquired: Entity, acquirer: Entity, merge_date: date):
    """
    When entity A is acquired by entity B:
    
    1. EntitySpine: 
       - A.successor_entity_id = B.entity_id
       - A.status = MERGED_INTO
       - A.dissolution_date = merge_date
    
    2. FinancialSpine:
       - Keep A's historical data with A's entity_id (accurate backtesting)
       - New data after merge_date links to B
       - Queries can optionally follow the chain
    """
    # EntitySpine handles entity transition
    acquired_updated = acquired.with_updates(
        successor_entity_id=acquirer.entity_id,
        status=EntityStatus.MERGED_INTO,
        dissolution_date=merge_date,
    )
    entity_store.update(acquired_updated)
    
    # FinancialSpine: No migration needed!
    # Historical data stays with acquired's entity_id
    # This preserves accurate backtesting
    
    # For reporting that needs combined view:
    migration_svc = FinancialMigrationService(financial_store)
    combined_metrics = migration_svc.get_combined_history(
        entity_ids=[acquired.entity_id, acquirer.entity_id],
        follow_successor_chain=True,
    )
```

## Key Design Principles

1. **Entity Resolution First**: Financial data links to EntitySpine entities via resolved identifiers
2. **Same Versioning Pattern**: Multiple sources, priority hierarchy, temporal validity
3. **Same LLM Mapping Pattern**: Generate field mappings from sample data
4. **Columnar Storage**: Parquet for time series, efficient analytical queries
5. **Metric Registry**: Define standard metric names with validation rules
6. **Historical Preservation**: Keep data with original entity_id for backtesting accuracy

## Metric Registry Example

```python
# financialspine/registry/metrics.py

METRIC_REGISTRY = {
    # Income Statement
    "revenue": {
        "aliases": ["revtq", "sale", "total_revenue", "net_sales"],
        "unit": "currency",
        "period_types": ["quarterly", "annual", "ttm"],
        "description": "Total revenue/net sales",
    },
    "net_income": {
        "aliases": ["niq", "ni", "netincome"],
        "unit": "currency",
        "period_types": ["quarterly", "annual", "ttm"],
        "description": "Net income attributable to common",
    },
    "eps_diluted": {
        "aliases": ["epspxq", "epsdil", "eps_dil"],
        "unit": "per_share",
        "period_types": ["quarterly", "annual", "ttm"],
        "description": "Diluted earnings per share",
    },
    
    # Balance Sheet
    "total_assets": {
        "aliases": ["atq", "at", "assets"],
        "unit": "currency",
        "period_types": ["quarterly", "annual"],
        "description": "Total assets",
    },
    
    # Ratios (computed)
    "pe_ratio": {
        "formula": "price / eps_diluted",
        "unit": "ratio",
        "description": "Price to earnings ratio",
    },
}
```

This registry enables:
- Mapping vendor column names to standard metrics
- Computing derived metrics
- Validation of metric values
- Schema export for LLM consumption

## Directory Structure

```
financialspine/
├── src/
│   └── financialspine/
│       ├── domain/
│       │   ├── __init__.py
│       │   ├── statement.py
│       │   ├── metric.py
│       │   ├── timeseries.py
│       │   └── enums.py
│       ├── data/
│       │   ├── __init__.py
│       │   ├── loaders/
│       │   │   ├── compustat.py
│       │   │   ├── bloomberg.py
│       │   │   └── crsp.py
│       │   ├── parquet_store.py
│       │   └── ingest.py
│       ├── registry/
│       │   ├── metrics.py
│       │   └── transforms.py
│       └── services/
│           ├── resolution.py
│           └── migration.py
├── tests/
├── mappings/          # LLM-generated YAML mappings
├── pyproject.toml
└── README.md
```

## Next Steps

1. ✅ Finalize EntitySpine core entity maps (current focus)
2. Create FinancialSpine package skeleton
3. Implement metric registry with validation
4. Build Compustat loader as reference implementation
5. Add time series storage with Parquet partitioning
6. Create LLM prompt template for financial data mapping
