# Working with SEC Data

EntitySpine is built to work with SEC (Securities and Exchange Commission) data from the ground up. This guide shows you how to leverage free, public SEC data to build entity resolution systems.

## Why SEC Data?

- **Free**: No API keys, no subscriptions, no rate limits
- **Authoritative**: Official regulatory filings, legally required to be accurate
- **Comprehensive**: 14,000+ publicly traded US companies
- **Historical**: Data going back decades
- **Structured**: JSON APIs and bulk downloads available

## SEC Data Sources

### 1. Company Tickers (Start Here)

The simplest way to get started - a JSON file with all SEC-registered companies:

```python
from entityspine import load_sec_data

# Download company_tickers.json (14K+ companies)
entities = load_sec_data(download_dir="data/sec")

# Each entity has:
# - CIK (Central Index Key) - SEC's unique identifier
# - Company name
# - Stock ticker (if applicable)
# - Exchange (NYSE, NASDAQ, etc.)

for entity in entities[:5]:
    print(f"{entity.primary_name} (CIK: {entity.source_id})")
```

**URL**: https://www.sec.gov/files/company_tickers.json

**Structure**:
```json
{
  "0": {
    "cik_str": "320193",
    "ticker": "AAPL",
    "title": "Apple Inc."
  },
  "1": {
    "cik_str": "789019",
    "ticker": "MSFT",
    "title": "MICROSOFT CORP"
  }
}
```

### 2. Company Facts (Detailed Financial Data)

For each company, the SEC provides structured financial statement data:

```python
from entityspine import fetch_company_facts

# Get Apple's financial data
facts = fetch_company_facts(cik="0000320193")

# Access financial metrics:
# - Revenue, net income, EPS
# - Balance sheet items
# - Cash flow data
# All with quarterly and annual periods
```

**URL Pattern**: `https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json`

**Example**: https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json

### 3. Submissions (Filing History)

Every filing a company has ever made with the SEC:

```python
from entityspine import fetch_submissions

# Get Microsoft's filing history
submissions = fetch_submissions(cik="0000789019")

# Access:
# - 10-K annual reports
# - 10-Q quarterly reports
# - 8-K current reports
# - Proxy statements
# - S-1 IPO filings
```

**URL Pattern**: `https://data.sec.gov/submissions/CIK{cik}.json`

## Identifier Mapping with SEC Data

EntitySpine's identifier claim model maps perfectly to SEC data:

```python
from entityspine import Entity, IdentifierClaim

# Create entity from SEC data
apple = Entity(
    primary_name="Apple Inc.",
    source_system="SEC",
    source_id="0000320193"  # CIK
)

# Add CIK as identifier claim
cik_claim = IdentifierClaim(
    entity_id=apple.entity_id,
    scheme="CIK",
    identifier="0000320193",
    source_system="SEC",
    source="company_tickers.json",
    confidence=1.0  # Official data, 100% confident
)

# Add ticker claim
ticker_claim = IdentifierClaim(
    entity_id=apple.entity_id,
    scheme="TICKER",
    identifier="AAPL",
    source_system="SEC",
    source="company_tickers.json",
    confidence=1.0
)
```

## Building Corporate Networks from SEC Data

### Parent-Subsidiary Relationships

Extract from 10-K filings (Item 1 - Business section):

```python
from entityspine import Relationship

# Example: Alphabet owns Google
alphabet = Entity(primary_name="Alphabet Inc.", ...)
google = Entity(primary_name="Google LLC", ...)

parent_of = Relationship(
    from_entity_id=alphabet.entity_id,
    relationship_type="PARENT_OF",
    to_entity_id=google.entity_id,
    source_system="SEC",
    source="10-K Filing",
    confidence=1.0
)
```

### Executive Relationships

From proxy statements (DEF 14A filings):

```python
from entityspine import PersonRole

# Example: Tim Cook as CEO of Apple
tim_cook = Entity(primary_name="Timothy Cook", entity_type="PERSON")

ceo_role = PersonRole(
    person_id=tim_cook.entity_id,
    organization_id=apple.entity_id,
    role_type="CEO",
    start_date="2011-08-24",
    source_system="SEC",
    source="DEF 14A - Proxy Statement"
)
```

## SEC Data Best Practices

### 1. CIK Formatting

CIKs can be with or without leading zeros:

```python
# All refer to Apple:
cik_variants = [
    "320193",      # Without leading zeros
    "0000320193",  # With leading zeros (10 digits)
]

# EntitySpine normalizes to without leading zeros:
def normalize_cik(cik: str) -> str:
    return str(int(cik))  # Removes leading zeros
```

### 2. Rate Limiting

While there are no hard rate limits, be respectful:

```python
import time
import requests

def fetch_with_delay(url: str, delay: float = 0.1) -> dict:
    """Fetch SEC data with built-in delay."""
    response = requests.get(url, headers={
        "User-Agent": "YourCompany contact@example.com"  # Required!
    })
    time.sleep(delay)  # 0.1s = max 10 requests/second
    return response.json()
```

**Required**: Always set a proper `User-Agent` header with contact info.

### 3. Data Freshness

- **company_tickers.json**: Updated daily
- **Company Facts**: Updated within 1-2 business days of filing
- **Submissions**: Real-time (filings appear immediately after acceptance)

### 4. Historical Data

Access historical filings:

```python
# Get all 10-K filings for a company
filings_10k = [
    f for f in submissions["filings"]["recent"]
    if f["form"] == "10-K"
]

# Sort by date to build timeline
filings_10k.sort(key=lambda x: x["filingDate"])
```

## Common Patterns

### Pattern 1: Build Company Database

```python
from entityspine import SqliteStore, load_sec_data

# Load all SEC companies
entities = load_sec_data()

# Store in SQLite
store = SqliteStore("companies.db")
for entity in entities:
    store.save(entity)

# Now you have 14K+ companies in a local database
```

### Pattern 2: Enrich with Identifiers

```python
# Start with SEC data (CIK + ticker)
# Then add other identifiers as you find them:

# Add LEI from GLEIF
lei_claim = IdentifierClaim(
    entity_id=apple.entity_id,
    scheme="LEI",
    identifier="HWUPKR0MPOU8FGXBT394",
    source_system="GLEIF",
    confidence=0.95
)

# Add CUSIP from your vendor
cusip_claim = IdentifierClaim(
    entity_id=apple.entity_id,
    scheme="CUSIP",
    identifier="037833100",
    source_system="vendor_data",
    confidence=0.90
)

# EntitySpine tracks provenance for each claim
```

### Pattern 3: Track Changes Over Time

```python
from datetime import datetime

# Company name change
old_name = IdentifierClaim(
    entity_id=entity.entity_id,
    scheme="NAME",
    identifier="Facebook, Inc.",
    source_system="SEC",
    valid_from=datetime(2012, 5, 18),
    valid_to=datetime(2021, 10, 28),
    confidence=1.0
)

new_name = IdentifierClaim(
    entity_id=entity.entity_id,
    scheme="NAME",
    identifier="Meta Platforms, Inc.",
    source_system="SEC",
    valid_from=datetime(2021, 10, 28),
    confidence=1.0
)
```

## Going Beyond SEC Data

Once you have the SEC foundation, you can layer on other data sources:

1. **SEC Data** (free, authoritative)
   ↓
2. **Add LEI from GLEIF** (free, global entity IDs)
   ↓
3. **Add your proprietary data** (customer relationships, etc.)
   ↓
4. **Optionally add vendor data** (Bloomberg, FactSet, etc.)

EntitySpine's identifier claim model tracks the source and confidence for each piece of data, so you always know what came from where.

## Resources

- **SEC EDGAR**: https://www.sec.gov/edgar
- **SEC Data APIs**: https://www.sec.gov/data-research/sec-markets-data/developer-resources
- **Company Tickers**: https://www.sec.gov/files/company_tickers.json
- **SEC Filing Viewer**: https://www.sec.gov/cgi-bin/browse-edgar

## Next Steps

- **[Core Concepts](../architecture/UNIFIED_DATA_MODEL.md)** - Understand EntitySpine's data model
- **[Building Corporate Networks](CORPORATE_NETWORKS.md)** - Map relationships between entities
- **[Identifier Mapping](../api/domain/claim.md)** - Deep dive into identifier claims

