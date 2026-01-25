# FactSet Integration Guide

This guide explains how to load FactSet Standard Data Feeds into EntitySpine.

## Overview

EntitySpine provides first-class support for FactSet data through:

1. **Schema Detection** - Auto-identify FactSet file types
2. **Specialized Loaders** - Convert each feed to domain models
3. **Identifier Crosswalks** - Link FactSet IDs to other vendors

## Supported FactSet Feeds

| Feed | Description | EntitySpine Model |
|------|-------------|-------------------|
| Symbology | Identifier crosswalks | `IdentifierClaim` |
| Events Calendar | Earnings, dividends, meetings | `Event` |
| People | Executives, board members | `PersonRole` |
| Ownership | Institutional/insider holdings | `OwnershipPosition` |
| M&A | Deal data | `Event`, `EntityRelationship` |
| Supply Chain (Revere) | Supplier/customer relationships | `EntityRelationship` |
| Estimates | Analyst consensus | Financial observations |

## Quick Start

### 1. Load Symbology Data

```python
from entityspine.data.factset import FactSetSymbologyLoader
from entityspine.stores import SqliteStore

# Initialize store
store = SqliteStore("entityspine.db")

# Load identifier crosswalks
loader = FactSetSymbologyLoader()
for claim in loader.iter_claims("sym_coverage.csv"):
    store.save_claim(claim)

# Now you can resolve by any identifier
entity = store.resolve("CUSIP", "037833100")  # Apple
```

### 2. Load Events Calendar

```python
from entityspine.data.factset import FactSetEventsLoader
from datetime import date

loader = FactSetEventsLoader()

# Get upcoming earnings
upcoming_earnings = []
for event in loader.iter_events("earnings_calendar.csv"):
    if (event.event_type.value == "earnings_release" and 
        event.scheduled_on and 
        event.scheduled_on > date.today()):
        upcoming_earnings.append(event)

# Print next 10 earnings
for event in sorted(upcoming_earnings, key=lambda e: e.scheduled_on)[:10]:
    print(f"{event.scheduled_on}: {event.title} ({event.report_time})")
```

### 3. Load M&A Deals

```python
from entityspine.data.factset import FactSetMergersLoader

loader = FactSetMergersLoader()
events, relationships = loader.load_deals("ma_deals.csv")

# Store events
for event in events:
    store.save_event(event)

# Store relationships (for completed deals)
for rel in relationships:
    store.save_relationship(rel)
```

## Schema Detection

EntitySpine can auto-detect FactSet file types:

```python
from entityspine.data.schema_detector import detect_vendor

# Detect file type
result = detect_vendor("sym_coverage.csv")
print(f"Vendor: {result.vendor}")      # DataVendor.FACTSET
print(f"Product: {result.product}")    # DataProduct.FACTSET_EDM
print(f"Type: {result.data_type}")     # DataType.IDENTIFIERS
```

### Detection Patterns

| File Pattern | Detected Product |
|--------------|------------------|
| `sym_*.csv` | FACTSET_EDM (identifiers) |
| `ca_events*.csv` | FACTSET_EDM (corporate actions) |
| `ppl_*.csv` | FACTSET_EDM (people) |
| `ma_deals*.csv` | FACTSET_EDM (M&A) |
| `supply_chain*.csv` | FACTSET_SUPPLY_CHAIN |
| `est_*.csv` | FACTSET_ESTIMATES |

## FactSet Identifier Crosswalks

### Supported Identifiers

FactSet symbology provides crosswalks between:

| Identifier | Scope | EntitySpine Scheme |
|------------|-------|-------------------|
| `fsym_id` | Entity | `FACTSET_ENTITY_ID` |
| `fsym_security_id` | Security | `FACTSET_SECURITY_ID` |
| CUSIP | Security | `CUSIP` |
| ISIN | Security | `ISIN` |
| SEDOL | Security | `SEDOL` |
| LEI | Entity | `LEI` |

### Building Multi-Vendor Crosswalks

```python
# Load FactSet identifiers
factset_loader = FactSetSymbologyLoader()
for claim in factset_loader.iter_claims("sym_xref.csv"):
    store.save_claim(claim)

# Load Bloomberg identifiers (if available)
from entityspine.data.loaders import load_bloomberg_batch
# ...

# Now resolve across vendors
entity = store.resolve("ISIN", "US0378331005")  # Works for any vendor
claims = store.get_claims(entity.entity_id)

for claim in claims:
    print(f"{claim.namespace}: {claim.scheme} = {claim.value}")
# Output:
# factset: factset_entity_id = 000C7F-E
# factset: cusip = 037833100
# factset: isin = US0378331005
# bloomberg: figi = BBG000B9XRY4
```

## Event Model Alignment

FactSet Events Calendar fields map to EntitySpine `Event`:

| FactSet Field | EntitySpine Field |
|---------------|-------------------|
| `event_type` | `event_type` |
| `event_date` | `scheduled_on` |
| `announcement_date` | `announced_on` |
| `fiscal_year` | `fiscal_year` |
| `fiscal_quarter` | `fiscal_quarter` |
| `report_time` | `report_time` (BMO/AMC/DURING) |
| `dividend_amount` | `amount` |
| `currency` | `currency` |

### Example: Dividend Calendar

```python
from entityspine.data.factset import FactSetEventsLoader
from entityspine.domain.enums import EventType

loader = FactSetEventsLoader()

# Find ex-dividend dates this month
import datetime
today = datetime.date.today()
month_end = today.replace(day=28)

for event in loader.iter_events("dividend_calendar.csv"):
    if (event.event_type == EventType.DIVIDEND_EX_DATE and
        event.effective_date and
        today <= event.effective_date <= month_end):
        print(f"{event.effective_date}: {event.title}")
        print(f"  Amount: {event.currency} {event.amount}")
```

## Best Practices

### 1. Use Streaming Iterators

All FactSet loaders use generators to handle large files efficiently:

```python
# Good - streams data
for claim in loader.iter_claims("large_file.csv"):
    process(claim)

# Avoid - loads everything into memory
claims = list(loader.iter_claims("large_file.csv"))
```

### 2. Batch Database Operations

```python
from entityspine.stores import SqliteStore

store = SqliteStore("entityspine.db")

# Batch inserts for performance
batch = []
for claim in loader.iter_claims("sym_coverage.csv"):
    batch.append(claim)
    if len(batch) >= 10000:
        store.save_claims_batch(batch)
        batch = []

if batch:
    store.save_claims_batch(batch)
```

### 3. Handle Missing Data

FactSet files may have missing values. Loaders handle this gracefully:

```python
# Loaders skip invalid rows and continue
for claim in loader.iter_claims("sym_coverage.csv"):
    # claim.value is always valid (normalized)
    # Invalid CUSIPs, ISINs, etc. are skipped
    pass
```

## See Also

- [FACTSET_INTEGRATION.md](../FACTSET_INTEGRATION.md) - Detailed field mappings
- [ENHANCEMENTS.md](../ENHANCEMENTS.md) - v2.3.0 FactSet-informed changes
- [FactSet Loaders API](../api/data/factset.md) - Full API reference
