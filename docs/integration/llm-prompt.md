# LLM Schema Mapping Prompt Template

Use this prompt with ChatGPT, Claude, or your preferred LLM to generate field mappings for new data sources.

---

## Instructions

1. Copy the entire prompt below
2. Replace `{SAMPLE_DATA}` with your actual data (headers + 3-5 sample rows)
3. Replace `{SOURCE_NAME}` with your vendor name
4. Send to LLM
5. Review and save the generated YAML

---

## The Prompt

```
You are a data mapping expert for financial entity data. Your task is to map columns from a vendor data file to the EntitySpine canonical schema.

## EntitySpine Schema

### Entity (Core Organization/Company record)
- entity_id: str (auto-generated UUID)
- primary_name: str (official legal name)
- entity_type: enum [ORGANIZATION, FUND, TRUST, GOVERNMENT, INDIVIDUAL, INDEX, CURRENCY, COMMODITY]
- status: enum [ACTIVE, INACTIVE, PENDING, MERGED_INTO, DISSOLVED]
- jurisdiction: str (ISO-3166 country code, e.g., "US", "GB", "JP")
- formation_date: date (when entity was formed/incorporated)
- dissolution_date: date (when entity ceased to exist)
- successor_entity_id: str (if merged/acquired, points to successor)
- sic_code: str (Standard Industry Classification)
- naics_code: str (North American Industry Classification)

### Security (Financial instrument issued by entity)
- security_id: str (auto-generated UUID)
- entity_id: str (FK to Entity)
- security_type: enum [COMMON_STOCK, PREFERRED_STOCK, ADR, ETF, BOND, WARRANT, OPTION, UNIT, REIT, OTHER]
- description: str (security description)
- currency: str (ISO-4217 currency code)
- issue_date: date
- maturity_date: date (for bonds)

### Listing (Trading venue for a security)
- listing_id: str (auto-generated UUID)
- security_id: str (FK to Security)
- mic: str (Market Identifier Code - ISO-10383, e.g., "XNAS", "XNYS", "XLON")
- ticker: str (trading symbol)
- is_primary: bool (primary listing flag)
- listing_date: date
- delisting_date: date

### IdentifierClaim (Cross-reference identifiers)
- claim_id: str (auto-generated UUID)
- entity_id: str (FK to Entity, optional)
- security_id: str (FK to Security, optional)
- listing_id: str (FK to Listing, optional)
- scheme: str (identifier system, e.g., "CIK", "FIGI", "CUSIP", "ISIN", "SEDOL", "LEI", "PERMID", "BBUID")
- value: str (the identifier value)
- source_system: str
- captured_at: datetime
- valid_from: date
- valid_to: date

### ExtendedAttribute (Dynamic fields not in core schema)
- entity_id: str (FK to Entity)
- attribute_name: str (e.g., "website", "employees", "market_sector")
- attribute_value: any
- value_type: str [string, number, date, url, json, boolean]
- source_system: str
- source_date: date

## Common Exchange Mappings
| Feed Code | MIC Code | Exchange Name |
|-----------|----------|---------------|
| US | XNAS | NASDAQ |
| UN | XNYS | NYSE |
| UW | XNAS | NASDAQ |
| UP | XNYS | NYSE ARCA |
| LN | XLON | London Stock Exchange |
| JT | XTKS | Tokyo Stock Exchange |
| HK | XHKG | Hong Kong Stock Exchange |
| GR | XFRA | Frankfurt Stock Exchange |
| FP | XPAR | Euronext Paris |
| CN | XTSE | Toronto Stock Exchange |
| AU | XASX | Australian Securities Exchange |

## Common Identifier Schemes
- CIK: SEC Central Index Key (10 digits, zero-padded)
- CUSIP: 9-character identifier for US/Canada securities
- ISIN: 12-character international identifier
- SEDOL: 7-character UK identifier
- FIGI: Bloomberg Financial Instrument Global Identifier
- LEI: Legal Entity Identifier (20 characters)
- PERMID: Refinitiv PermID
- BBUID: Bloomberg Unique Identifier
- TICKER: Exchange trading symbol

---

## Your Data Source: {SOURCE_NAME}

### Sample Data (headers + rows):
```
{SAMPLE_DATA}
```

---

## Your Task

Generate a YAML mapping configuration that:

1. Maps each relevant column to the EntitySpine schema
2. Identifies which columns map to Entity, Security, Listing, or IdentifierClaim
3. Specifies any transformations needed (e.g., exchange code to MIC)
4. Captures fields that should go to ExtendedAttributes
5. Identifies columns to SKIP (internal IDs, duplicates, etc.)

## Output Format

Provide the mapping in this exact YAML format:

```yaml
source_type: "{source_name_lowercase}"
description: "Description of this data source"
file_format:
  delimiter: "|" or "\t" or ","
  encoding: "utf-8"
  header_row: 0
  skip_rows: 0

column_mappings:
  # Entity fields
  entity:
    primary_name:
      column: "COLUMN_NAME"
      transform: null  # or transformation function name
    entity_type:
      column: "COLUMN_NAME"
      transform: "transform_function_name"  # if needed
      default: "ORGANIZATION"  # if column missing
    jurisdiction:
      column: "COLUMN_NAME"
      transform: null
    # ... other entity fields

  # Security fields
  security:
    security_type:
      column: "COLUMN_NAME"
      transform: "security_type_transform"
    description:
      column: "COLUMN_NAME"
      transform: null
    # ... other security fields

  # Listing fields
  listing:
    ticker:
      column: "COLUMN_NAME"
    mic:
      column: "COLUMN_NAME"
      transform: "exchange_to_mic"
    is_primary:
      default: true

  # Identifiers to extract
  identifiers:
    - scheme: "IDENTIFIER_SCHEME"
      column: "COLUMN_NAME"
      target: "entity"  # or "security" or "listing"
    - scheme: "ANOTHER_SCHEME"
      column: "COLUMN_NAME"
      target: "security"

  # Extended attributes (vendor-specific fields)
  extended_attributes:
    - name: "attribute_name"
      column: "COLUMN_NAME"
      type: "string"  # or number, date, url, json, boolean
    - name: "another_attribute"
      column: "COLUMN_NAME"
      type: "number"

  # Columns to skip
  skip_columns:
    - "INTERNAL_ID"
    - "DUPLICATE_COLUMN"

# Transformation functions needed
transforms:
  exchange_to_mic:
    description: "Convert exchange code to ISO-10383 MIC"
    mapping:
      "US": "XNAS"
      "UN": "XNYS"
      # ... add based on data
  
  security_type_transform:
    description: "Convert vendor security type to EntitySpine enum"
    mapping:
      "Common Stock": "COMMON_STOCK"
      "Pref Stock": "PREFERRED_STOCK"
      # ... add based on data

# Validation rules
validation:
  required_columns:
    - "NAME_COLUMN"
    - "IDENTIFIER_COLUMN"
  unique_key:
    - "IDENTIFIER_COLUMN"
```

## Additional Notes

- If a column could map to multiple schema fields, explain your choice
- If data quality issues are apparent, note them
- If transformations are complex, provide pseudocode
- Flag any columns you're uncertain about
```

---

## Example Output

For Bloomberg BBUID data with these columns:
```
NAME|ID_BB_SEC_NUM_DES|FEED_SOURCE|ID_BB_UNIQUE|SECURITY_TYP|ID_BB_GLOBAL|COMPOSITE_ID_BB_GLOBAL
Apple Inc|AAPL|US|EQ0010169500001000|Common Stock|BBG000B9XRY4|BBG000B9Y5X2
```

The LLM would generate:

```yaml
source_type: "bloomberg_bbuid"
description: "Bloomberg BBUID equity reference data"
file_format:
  delimiter: "|"
  encoding: "utf-8"
  header_row: 0

column_mappings:
  entity:
    primary_name:
      column: "NAME"
    entity_type:
      default: "ORGANIZATION"
    jurisdiction:
      column: null  # Not in this file, may need enrichment

  security:
    security_type:
      column: "SECURITY_TYP"
      transform: "bloomberg_security_type"
    description:
      column: "NAME"
      transform: "append_security_type"  # "Apple Inc Common Stock"

  listing:
    ticker:
      column: "ID_BB_SEC_NUM_DES"
    mic:
      column: "FEED_SOURCE"
      transform: "bloomberg_feed_to_mic"
    is_primary:
      default: true

  identifiers:
    - scheme: "BBUID"
      column: "ID_BB_UNIQUE"
      target: "security"
    - scheme: "FIGI"
      column: "ID_BB_GLOBAL"
      target: "security"
    - scheme: "COMPOSITE_FIGI"
      column: "COMPOSITE_ID_BB_GLOBAL"
      target: "entity"

  extended_attributes: []  # No extra fields in this file

  skip_columns: []

transforms:
  bloomberg_feed_to_mic:
    mapping:
      "US": "XNAS"
      "UN": "XNYS"
      "UW": "XNAS"
      "UP": "XNYS"
      "UA": "XASE"
      "LN": "XLON"
      "JT": "XTKS"
  
  bloomberg_security_type:
    mapping:
      "Common Stock": "COMMON_STOCK"
      "Pref Stock": "PREFERRED_STOCK"
      "ADR": "ADR"
      "ETF": "ETF"
      "REIT": "REIT"
      "default": "OTHER"

validation:
  required_columns:
    - "NAME"
    - "ID_BB_UNIQUE"
  unique_key:
    - "ID_BB_UNIQUE"
```

---

## Using the Generated Mapping

```python
from entityspine.data.ingestion import IngestPipeline
import yaml

# Load the LLM-generated mapping
with open("mappings/bloomberg_bbuid.yaml") as f:
    mapping = yaml.safe_load(f)

# Run ingestion
pipeline = IngestPipeline()
result = pipeline.ingest(
    source_file="G:/BLOOMBERG/bbuid/Equity_Common_Stock.txt",
    mapping=mapping,
    source_priority=1,  # Bloomberg is highest
)
```

---

## Iterating on Mappings

After initial mapping, you may need to:

1. **Add missing transforms**: If certain values don't convert correctly
2. **Handle edge cases**: Null values, malformed data
3. **Add validation**: Check for required fields, format validation
4. **Tune extended attributes**: Add more vendor-specific fields

The LLM can help refine mappings - just provide error messages or sample failures and ask for updates to the YAML.
