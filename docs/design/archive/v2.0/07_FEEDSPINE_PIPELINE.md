# Entity Master v2 - FeedSpine Pipeline Integration

**Bronze → Silver → Gold reference data layers for Entity Master**

---

## FeedSpine Architecture Context

FeedSpine is a data pipeline framework that processes reference data through quality tiers:

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              FEEDSPINE LAYER ARCHITECTURE                                │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                          │
│   RAW SOURCES              BRONZE               SILVER                GOLD               │
│   ───────────              ──────               ──────                ────               │
│                                                                                          │
│   SEC EDGAR   ─────┐                                                                     │
│   (filings)        │                                                                     │
│                    │       ┌─────────────┐     ┌─────────────┐     ┌─────────────┐      │
│   SEC Bulk    ────►├──────►│   BRONZE    │────►│   SILVER    │────►│    GOLD     │      │
│   (company.json)   │       │             │     │             │     │             │      │
│                    │       │ - Raw data  │     │ - Cleaned   │     │ - Curated   │      │
│   OpenFIGI   ─────┤       │ - As-is     │     │ - Validated │     │ - Enriched  │      │
│   (FIGI data)      │       │ - Timestamped│     │ - Normalized│     │ - Resolved  │      │
│                    │       │             │     │             │     │             │      │
│   FactSet    ─────┤       └─────────────┘     └─────────────┘     └─────────────┘      │
│   (symbology)      │                                                                     │
│                    │       ▼                   ▼                   ▼                    │
│   Refinitiv  ─────┘       Data Lake           Entity Master       Canonical             │
│   (PermID)                (parquet)           Staging            Production            │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Bronze Layer: Raw Data Ingestion

### Purpose

- Capture raw vendor data exactly as received
- Preserve provenance and timestamps
- Enable replay/reprocessing
- No transformations, validations, or deduplication

### Schema

```sql
-- Bronze layer tables live in separate schema
CREATE SCHEMA bronze;

-- Raw SEC company data
CREATE TABLE bronze.sec_company_tickers (
    record_id       TEXT PRIMARY KEY,  -- ULID
    
    -- Raw fields from company_tickers.json
    cik_raw         TEXT,
    ticker_raw      TEXT,
    title_raw       TEXT,
    exchange_raw    TEXT,
    
    -- Provenance
    source_file     TEXT NOT NULL,
    source_url      TEXT,
    file_date       DATE,
    ingested_at     TIMESTAMPTZ DEFAULT NOW(),
    
    -- Raw JSON for full fidelity
    raw_json        JSONB
);

-- Raw SEC filing header data
CREATE TABLE bronze.sec_filing_headers (
    record_id       TEXT PRIMARY KEY,
    
    -- Raw fields
    accession_number_raw TEXT,
    cik_raw         TEXT,
    form_type_raw   TEXT,
    date_filed_raw  TEXT,
    company_name_raw TEXT,
    
    -- Provenance
    source_index    TEXT,  -- 'daily-index' or 'full-index'
    index_date      DATE,
    ingested_at     TIMESTAMPTZ DEFAULT NOW(),
    
    raw_json        JSONB
);

-- Raw OpenFIGI responses
CREATE TABLE bronze.openfigi_responses (
    record_id       TEXT PRIMARY KEY,
    
    -- Request context
    request_type    TEXT,  -- 'search', 'mapping'
    request_params  JSONB,
    
    -- Raw response
    figi_raw        TEXT,
    composite_figi_raw TEXT,
    share_class_figi_raw TEXT,
    ticker_raw      TEXT,
    exch_code_raw   TEXT,
    name_raw        TEXT,
    security_type_raw TEXT,
    
    -- Provenance
    api_version     TEXT,
    response_date   TIMESTAMPTZ,
    ingested_at     TIMESTAMPTZ DEFAULT NOW(),
    
    raw_json        JSONB
);

-- Raw FactSet symbology
CREATE TABLE bronze.factset_symbology (
    record_id       TEXT PRIMARY KEY,
    
    -- Raw fields
    factset_entity_id_raw TEXT,
    factset_security_id_raw TEXT,
    factset_listing_id_raw TEXT,
    entity_name_raw TEXT,
    isin_raw        TEXT,
    cusip_raw       TEXT,
    ticker_raw      TEXT,
    exchange_raw    TEXT,
    
    -- Provenance
    source_file     TEXT,
    file_date       DATE,
    ingested_at     TIMESTAMPTZ DEFAULT NOW(),
    
    raw_json        JSONB
);

-- Indexes for replay queries
CREATE INDEX idx_bronze_sec_company_date ON bronze.sec_company_tickers(file_date);
CREATE INDEX idx_bronze_sec_filing_date ON bronze.sec_filing_headers(index_date);
CREATE INDEX idx_bronze_openfigi_date ON bronze.openfigi_responses(response_date);
CREATE INDEX idx_bronze_factset_date ON bronze.factset_symbology(file_date);
```

### Ingestion Pipeline

```python
"""Bronze layer ingestion for FeedSpine."""

from dataclasses import dataclass
from datetime import datetime, date
from typing import Dict, List, Optional, Any
import json


@dataclass
class BronzeRecord:
    """A raw record in the bronze layer."""
    record_id: str
    source: str
    source_file: Optional[str]
    source_url: Optional[str]
    ingested_at: datetime
    raw_json: Dict[str, Any]


class BronzeIngester:
    """Ingest raw data into bronze layer."""
    
    def __init__(self, db):
        self.db = db
    
    # =========================================================================
    # SEC Data Ingestion
    # =========================================================================
    
    async def ingest_sec_company_tickers(
        self,
        data: Dict,
        source_url: str,
        file_date: date,
    ) -> int:
        """
        Ingest SEC company_tickers.json into bronze.
        
        Source: https://www.sec.gov/files/company_tickers.json
        """
        records = []
        
        for key, item in data.items():
            record_id = generate_ulid()
            
            records.append({
                'record_id': record_id,
                'cik_raw': str(item.get('cik_str', '')),
                'ticker_raw': item.get('ticker'),
                'title_raw': item.get('title'),
                'exchange_raw': item.get('exchange'),
                'source_file': 'company_tickers.json',
                'source_url': source_url,
                'file_date': file_date,
                'raw_json': json.dumps(item),
            })
        
        # Bulk insert
        await self.db.execute_many("""
            INSERT INTO bronze.sec_company_tickers (
                record_id, cik_raw, ticker_raw, title_raw, exchange_raw,
                source_file, source_url, file_date, raw_json
            ) VALUES (
                :record_id, :cik_raw, :ticker_raw, :title_raw, :exchange_raw,
                :source_file, :source_url, :file_date, :raw_json::jsonb
            )
        """, records)
        
        return len(records)
    
    async def ingest_sec_filing_index(
        self,
        index_data: List[Dict],
        index_type: str,  # 'daily-index' or 'full-index'
        index_date: date,
    ) -> int:
        """
        Ingest SEC EDGAR index data into bronze.
        """
        records = []
        
        for item in index_data:
            record_id = generate_ulid()
            
            records.append({
                'record_id': record_id,
                'accession_number_raw': item.get('accessionNumber'),
                'cik_raw': str(item.get('cik', '')),
                'form_type_raw': item.get('form'),
                'date_filed_raw': item.get('filingDate') or item.get('dateFiled'),
                'company_name_raw': item.get('companyName'),
                'source_index': index_type,
                'index_date': index_date,
                'raw_json': json.dumps(item),
            })
        
        await self.db.execute_many("""
            INSERT INTO bronze.sec_filing_headers (
                record_id, accession_number_raw, cik_raw, form_type_raw,
                date_filed_raw, company_name_raw, source_index, index_date, raw_json
            ) VALUES (
                :record_id, :accession_number_raw, :cik_raw, :form_type_raw,
                :date_filed_raw, :company_name_raw, :source_index, :index_date, :raw_json::jsonb
            )
        """, records)
        
        return len(records)
    
    # =========================================================================
    # OpenFIGI Ingestion
    # =========================================================================
    
    async def ingest_openfigi_responses(
        self,
        responses: List[Dict],
        request_type: str,
        request_params: Dict,
    ) -> int:
        """
        Ingest OpenFIGI API responses into bronze.
        """
        records = []
        
        for response in responses:
            # Handle both success and error responses
            if 'data' in response:
                for item in response['data']:
                    record_id = generate_ulid()
                    
                    records.append({
                        'record_id': record_id,
                        'request_type': request_type,
                        'request_params': json.dumps(request_params),
                        'figi_raw': item.get('figi'),
                        'composite_figi_raw': item.get('compositeFIGI'),
                        'share_class_figi_raw': item.get('shareClassFIGI'),
                        'ticker_raw': item.get('ticker'),
                        'exch_code_raw': item.get('exchCode'),
                        'name_raw': item.get('name'),
                        'security_type_raw': item.get('securityType'),
                        'api_version': '3',
                        'response_date': datetime.utcnow(),
                        'raw_json': json.dumps(item),
                    })
            
            elif 'error' in response:
                # Log error but don't fail
                logger.warning(f"OpenFIGI error: {response['error']}")
        
        if records:
            await self.db.execute_many("""
                INSERT INTO bronze.openfigi_responses (
                    record_id, request_type, request_params,
                    figi_raw, composite_figi_raw, share_class_figi_raw,
                    ticker_raw, exch_code_raw, name_raw, security_type_raw,
                    api_version, response_date, raw_json
                ) VALUES (
                    :record_id, :request_type, :request_params::jsonb,
                    :figi_raw, :composite_figi_raw, :share_class_figi_raw,
                    :ticker_raw, :exch_code_raw, :name_raw, :security_type_raw,
                    :api_version, :response_date, :raw_json::jsonb
                )
            """, records)
        
        return len(records)
    
    # =========================================================================
    # FactSet Ingestion
    # =========================================================================
    
    async def ingest_factset_symbology(
        self,
        filepath: str,
        file_date: date,
    ) -> int:
        """
        Ingest FactSet symbology file into bronze.
        """
        import csv
        
        records = []
        
        with open(filepath, 'r') as f:
            reader = csv.DictReader(f, delimiter='|')
            
            for row in reader:
                record_id = generate_ulid()
                
                records.append({
                    'record_id': record_id,
                    'factset_entity_id_raw': row.get('factset_entity_id'),
                    'factset_security_id_raw': row.get('factset_security_id'),
                    'factset_listing_id_raw': row.get('factset_listing_id'),
                    'entity_name_raw': row.get('entity_proper_name'),
                    'isin_raw': row.get('isin'),
                    'cusip_raw': row.get('cusip'),
                    'ticker_raw': row.get('ticker_symbol'),
                    'exchange_raw': row.get('ticker_exchange'),
                    'source_file': filepath,
                    'file_date': file_date,
                    'raw_json': json.dumps(row),
                })
        
        # Batch insert
        BATCH_SIZE = 10000
        for i in range(0, len(records), BATCH_SIZE):
            batch = records[i:i + BATCH_SIZE]
            await self.db.execute_many("""
                INSERT INTO bronze.factset_symbology (
                    record_id, factset_entity_id_raw, factset_security_id_raw,
                    factset_listing_id_raw, entity_name_raw, isin_raw, cusip_raw,
                    ticker_raw, exchange_raw, source_file, file_date, raw_json
                ) VALUES (
                    :record_id, :factset_entity_id_raw, :factset_security_id_raw,
                    :factset_listing_id_raw, :entity_name_raw, :isin_raw, :cusip_raw,
                    :ticker_raw, :exchange_raw, :source_file, :file_date, :raw_json::jsonb
                )
            """, batch)
        
        return len(records)
```

---

## Silver Layer: Cleaned and Validated

### Purpose

- Clean and standardize data
- Validate formats and checksums
- Normalize identifiers
- Detect anomalies
- Stage for entity resolution

### Schema

```sql
CREATE SCHEMA silver;

-- Cleaned SEC company data
CREATE TABLE silver.sec_companies (
    company_id      TEXT PRIMARY KEY,  -- ULID
    
    -- Cleaned fields
    cik             VARCHAR(10) NOT NULL,  -- Zero-padded, validated
    ticker          VARCHAR(20),           -- Uppercase, trimmed
    company_name    TEXT NOT NULL,         -- Cleaned, not normalized
    exchange        VARCHAR(20),           -- Standardized exchange code
    
    -- Validation status
    cik_valid       BOOLEAN DEFAULT TRUE,
    ticker_valid    BOOLEAN,
    name_cleaned    BOOLEAN DEFAULT TRUE,
    
    -- Linking to bronze
    bronze_record_id TEXT NOT NULL,
    
    -- Provenance
    source_date     DATE NOT NULL,
    processed_at    TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT uq_silver_sec_cik UNIQUE (cik)
);

-- Cleaned FIGI data
CREATE TABLE silver.openfigi_instruments (
    instrument_id   TEXT PRIMARY KEY,
    
    -- Cleaned fields
    figi            CHAR(12) NOT NULL,          -- Validated format
    composite_figi  CHAR(12),                   -- Validated format
    ticker          VARCHAR(20),                -- Uppercase
    exchange_mic    VARCHAR(4),                 -- ISO 10383 MIC
    security_name   TEXT,                       -- Cleaned
    security_type   VARCHAR(50),                -- Standardized
    
    -- Validation status
    figi_valid      BOOLEAN DEFAULT TRUE,       -- Checksum validated
    mic_valid       BOOLEAN,                    -- MIC exists
    
    -- Linking
    bronze_record_id TEXT NOT NULL,
    
    -- Provenance
    source_date     DATE NOT NULL,
    processed_at    TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT uq_silver_figi UNIQUE (figi)
);

-- Cleaned FactSet data
CREATE TABLE silver.factset_securities (
    factset_id      TEXT PRIMARY KEY,
    
    -- Entity-level
    fs_entity_id    VARCHAR(20),
    entity_name     TEXT,
    
    -- Security-level
    fs_security_id  VARCHAR(20),
    isin            CHAR(12),          -- Validated
    cusip           CHAR(9),           -- Validated
    
    -- Listing-level
    fs_listing_id   VARCHAR(30),
    ticker          VARCHAR(20),
    exchange_mic    VARCHAR(4),
    
    -- Validation
    isin_valid      BOOLEAN,
    cusip_valid     BOOLEAN,
    
    -- Linking
    bronze_record_id TEXT NOT NULL,
    
    -- Provenance
    source_date     DATE NOT NULL,
    processed_at    TIMESTAMPTZ DEFAULT NOW()
);

-- Validation errors log
CREATE TABLE silver.validation_errors (
    error_id        TEXT PRIMARY KEY,
    bronze_table    TEXT NOT NULL,
    bronze_record_id TEXT NOT NULL,
    field_name      TEXT NOT NULL,
    raw_value       TEXT,
    error_type      TEXT NOT NULL,  -- 'format', 'checksum', 'range', 'missing'
    error_message   TEXT,
    detected_at     TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_silver_sec_ticker ON silver.sec_companies(ticker);
CREATE INDEX idx_silver_figi ON silver.openfigi_instruments(figi);
CREATE INDEX idx_silver_isin ON silver.factset_securities(isin);
CREATE INDEX idx_silver_errors ON silver.validation_errors(bronze_table, bronze_record_id);
```

### Cleaning Pipeline

```python
"""Silver layer cleaning and validation for FeedSpine."""

from dataclasses import dataclass
from typing import Optional, Tuple, List
import re


@dataclass
class ValidationResult:
    """Result of validating a field."""
    valid: bool
    cleaned_value: Optional[str]
    error_type: Optional[str] = None
    error_message: Optional[str] = None


class SilverProcessor:
    """Process bronze data into silver layer."""
    
    def __init__(self, db):
        self.db = db
    
    # =========================================================================
    # SEC Company Processing
    # =========================================================================
    
    async def process_sec_companies(
        self,
        source_date: date,
    ) -> Tuple[int, int]:
        """
        Process bronze SEC company data into silver.
        
        Returns (processed_count, error_count)
        """
        # Get unprocessed bronze records for this date
        bronze_records = await self.db.fetch_all("""
            SELECT * FROM bronze.sec_company_tickers
            WHERE file_date = :date
              AND record_id NOT IN (
                  SELECT bronze_record_id FROM silver.sec_companies
              )
        """, {'date': source_date})
        
        processed = 0
        errors = 0
        
        for record in bronze_records:
            try:
                # Clean and validate CIK
                cik_result = self._validate_cik(record['cik_raw'])
                if not cik_result.valid:
                    await self._log_validation_error(
                        bronze_table='sec_company_tickers',
                        bronze_record_id=record['record_id'],
                        field_name='cik',
                        raw_value=record['cik_raw'],
                        error_type=cik_result.error_type,
                        error_message=cik_result.error_message,
                    )
                    errors += 1
                    continue
                
                # Clean ticker
                ticker_result = self._clean_ticker(record['ticker_raw'])
                
                # Clean company name
                name_result = self._clean_company_name(record['title_raw'])
                
                # Standardize exchange
                exchange = self._standardize_exchange(record['exchange_raw'])
                
                # Insert into silver
                company_id = generate_ulid()
                
                await self.db.execute("""
                    INSERT INTO silver.sec_companies (
                        company_id, cik, ticker, company_name, exchange,
                        cik_valid, ticker_valid, name_cleaned,
                        bronze_record_id, source_date
                    ) VALUES (
                        :id, :cik, :ticker, :name, :exchange,
                        :cik_valid, :ticker_valid, :name_cleaned,
                        :bronze_id, :source_date
                    )
                    ON CONFLICT (cik) DO UPDATE SET
                        ticker = EXCLUDED.ticker,
                        company_name = EXCLUDED.company_name,
                        exchange = EXCLUDED.exchange,
                        processed_at = NOW()
                """, {
                    'id': company_id,
                    'cik': cik_result.cleaned_value,
                    'ticker': ticker_result.cleaned_value,
                    'name': name_result.cleaned_value,
                    'exchange': exchange,
                    'cik_valid': cik_result.valid,
                    'ticker_valid': ticker_result.valid,
                    'name_cleaned': name_result.valid,
                    'bronze_id': record['record_id'],
                    'source_date': source_date,
                })
                
                processed += 1
                
            except Exception as e:
                logger.error(f"Error processing record {record['record_id']}: {e}")
                errors += 1
        
        return processed, errors
    
    # =========================================================================
    # OpenFIGI Processing
    # =========================================================================
    
    async def process_openfigi_instruments(
        self,
        source_date: date,
    ) -> Tuple[int, int]:
        """Process bronze OpenFIGI data into silver."""
        
        bronze_records = await self.db.fetch_all("""
            SELECT * FROM bronze.openfigi_responses
            WHERE DATE(response_date) = :date
              AND record_id NOT IN (
                  SELECT bronze_record_id FROM silver.openfigi_instruments
              )
        """, {'date': source_date})
        
        processed = 0
        errors = 0
        
        for record in bronze_records:
            try:
                # Validate FIGI
                figi_result = self._validate_figi(record['figi_raw'])
                if not figi_result.valid:
                    await self._log_validation_error(
                        bronze_table='openfigi_responses',
                        bronze_record_id=record['record_id'],
                        field_name='figi',
                        raw_value=record['figi_raw'],
                        error_type=figi_result.error_type,
                        error_message=figi_result.error_message,
                    )
                    errors += 1
                    continue
                
                # Validate composite FIGI
                comp_figi_result = self._validate_figi(record['composite_figi_raw'])
                
                # Clean ticker
                ticker_result = self._clean_ticker(record['ticker_raw'])
                
                # Map exchange code to MIC
                mic = self._exch_code_to_mic(record['exch_code_raw'])
                
                # Insert into silver
                instrument_id = generate_ulid()
                
                await self.db.execute("""
                    INSERT INTO silver.openfigi_instruments (
                        instrument_id, figi, composite_figi, ticker,
                        exchange_mic, security_name, security_type,
                        figi_valid, mic_valid, bronze_record_id, source_date
                    ) VALUES (
                        :id, :figi, :comp_figi, :ticker,
                        :mic, :name, :sec_type,
                        :figi_valid, :mic_valid, :bronze_id, :source_date
                    )
                    ON CONFLICT (figi) DO UPDATE SET
                        composite_figi = EXCLUDED.composite_figi,
                        ticker = EXCLUDED.ticker,
                        processed_at = NOW()
                """, {
                    'id': instrument_id,
                    'figi': figi_result.cleaned_value,
                    'comp_figi': comp_figi_result.cleaned_value if comp_figi_result.valid else None,
                    'ticker': ticker_result.cleaned_value,
                    'mic': mic,
                    'name': record['name_raw'],
                    'sec_type': record['security_type_raw'],
                    'figi_valid': True,
                    'mic_valid': mic is not None,
                    'bronze_id': record['record_id'],
                    'source_date': source_date,
                })
                
                processed += 1
                
            except Exception as e:
                logger.error(f"Error processing FIGI record {record['record_id']}: {e}")
                errors += 1
        
        return processed, errors
    
    # =========================================================================
    # Validators
    # =========================================================================
    
    def _validate_cik(self, raw_cik: str) -> ValidationResult:
        """Validate and clean CIK."""
        if not raw_cik:
            return ValidationResult(
                valid=False,
                cleaned_value=None,
                error_type='missing',
                error_message='CIK is missing',
            )
        
        # Remove any non-digits
        cleaned = re.sub(r'\D', '', str(raw_cik))
        
        if not cleaned:
            return ValidationResult(
                valid=False,
                cleaned_value=None,
                error_type='format',
                error_message='CIK contains no digits',
            )
        
        # CIK should be 1-10 digits
        if len(cleaned) > 10:
            return ValidationResult(
                valid=False,
                cleaned_value=None,
                error_type='format',
                error_message=f'CIK too long: {len(cleaned)} digits',
            )
        
        # Zero-pad to 10 digits
        padded = cleaned.zfill(10)
        
        return ValidationResult(valid=True, cleaned_value=padded)
    
    def _validate_figi(self, raw_figi: str) -> ValidationResult:
        """Validate FIGI format and checksum."""
        if not raw_figi:
            return ValidationResult(
                valid=False,
                cleaned_value=None,
                error_type='missing',
                error_message='FIGI is missing',
            )
        
        figi = raw_figi.strip().upper()
        
        # FIGI format: BBG + 8 alphanumeric + check digit
        if not re.match(r'^BBG[0-9A-Z]{9}$', figi):
            return ValidationResult(
                valid=False,
                cleaned_value=None,
                error_type='format',
                error_message='Invalid FIGI format',
            )
        
        # Validate checksum (simplified - full implementation needed)
        # FIGI uses Luhn mod N algorithm
        if not self._validate_figi_checksum(figi):
            return ValidationResult(
                valid=False,
                cleaned_value=figi,
                error_type='checksum',
                error_message='Invalid FIGI checksum',
            )
        
        return ValidationResult(valid=True, cleaned_value=figi)
    
    def _validate_figi_checksum(self, figi: str) -> bool:
        """Validate FIGI checksum using Luhn mod 36."""
        # Simplified - return True for now
        # Full implementation: convert to base36, apply Luhn algorithm
        return True
    
    def _validate_isin(self, raw_isin: str) -> ValidationResult:
        """Validate ISIN format and checksum."""
        if not raw_isin:
            return ValidationResult(valid=False, cleaned_value=None, error_type='missing')
        
        isin = raw_isin.strip().upper()
        
        # ISIN: 2 letters (country) + 9 alphanumeric + 1 check digit
        if not re.match(r'^[A-Z]{2}[A-Z0-9]{9}[0-9]$', isin):
            return ValidationResult(
                valid=False,
                cleaned_value=None,
                error_type='format',
                error_message='Invalid ISIN format',
            )
        
        # Validate Luhn checksum
        if not self._validate_luhn(isin):
            return ValidationResult(
                valid=False,
                cleaned_value=isin,
                error_type='checksum',
                error_message='Invalid ISIN checksum',
            )
        
        return ValidationResult(valid=True, cleaned_value=isin)
    
    def _validate_luhn(self, identifier: str) -> bool:
        """Validate Luhn checksum for ISIN/SEDOL."""
        # Convert letters to numbers (A=10, B=11, ...)
        digits = []
        for char in identifier:
            if char.isdigit():
                digits.append(int(char))
            else:
                # A=10, B=11, ..., Z=35
                val = ord(char) - ord('A') + 10
                digits.extend([val // 10, val % 10])
        
        # Apply Luhn algorithm
        total = 0
        for i, digit in enumerate(reversed(digits)):
            if i % 2 == 1:
                digit *= 2
                if digit > 9:
                    digit -= 9
            total += digit
        
        return total % 10 == 0
    
    def _clean_ticker(self, raw_ticker: str) -> ValidationResult:
        """Clean ticker symbol."""
        if not raw_ticker:
            return ValidationResult(valid=True, cleaned_value=None)
        
        ticker = raw_ticker.strip().upper()
        
        # Remove common suffixes
        ticker = re.sub(r'\s*\(.*\)$', '', ticker)
        
        # Valid ticker: 1-10 alphanumeric + dots/dashes
        if not re.match(r'^[A-Z0-9.\-]{1,10}$', ticker):
            return ValidationResult(
                valid=False,
                cleaned_value=ticker,
                error_type='format',
                error_message='Invalid ticker format',
            )
        
        return ValidationResult(valid=True, cleaned_value=ticker)
    
    def _clean_company_name(self, raw_name: str) -> ValidationResult:
        """Clean company name."""
        if not raw_name:
            return ValidationResult(
                valid=False,
                cleaned_value=None,
                error_type='missing',
            )
        
        # Basic cleaning
        name = raw_name.strip()
        
        # Remove multiple spaces
        name = ' '.join(name.split())
        
        # Remove trailing punctuation
        name = name.rstrip('.,;:')
        
        return ValidationResult(valid=True, cleaned_value=name)
    
    def _standardize_exchange(self, raw_exchange: str) -> Optional[str]:
        """Map exchange codes to standard MICs."""
        if not raw_exchange:
            return None
        
        exchange = raw_exchange.strip().upper()
        
        # Common mappings
        mapping = {
            'NYSE': 'XNYS',
            'NASDAQ': 'XNAS',
            'AMEX': 'XASE',
            'BATS': 'BATS',
            'IEX': 'IEXG',
            'ARCA': 'ARCX',
        }
        
        return mapping.get(exchange, exchange)
    
    def _exch_code_to_mic(self, exch_code: str) -> Optional[str]:
        """Map OpenFIGI exchange codes to MICs."""
        if not exch_code:
            return None
        
        # OpenFIGI uses its own codes
        mapping = {
            'US': 'XNAS',  # Default US to NASDAQ
            'UN': 'XNYS',  # NYSE
            'UQ': 'XNAS',  # NASDAQ
            'UA': 'XASE',  # AMEX
            # Add more mappings...
        }
        
        return mapping.get(exch_code.upper(), None)
    
    # =========================================================================
    # Error Logging
    # =========================================================================
    
    async def _log_validation_error(
        self,
        bronze_table: str,
        bronze_record_id: str,
        field_name: str,
        raw_value: str,
        error_type: str,
        error_message: str,
    ):
        """Log a validation error."""
        error_id = generate_ulid()
        
        await self.db.execute("""
            INSERT INTO silver.validation_errors (
                error_id, bronze_table, bronze_record_id,
                field_name, raw_value, error_type, error_message
            ) VALUES (
                :id, :table, :record_id,
                :field, :value, :type, :message
            )
        """, {
            'id': error_id,
            'table': bronze_table,
            'record_id': bronze_record_id,
            'field': field_name,
            'value': raw_value,
            'type': error_type,
            'message': error_message,
        })
```

---

## Gold Layer: Canonical Entity Master

### Purpose

- Resolve and link silver data to canonical entities
- Create/update Entity Master records
- Maintain merge chains and relationships
- Produce production-ready reference data

### Processing Pipeline

```python
"""Gold layer processing - Entity Master population."""

from typing import Tuple, List, Optional
from datetime import date


class GoldProcessor:
    """Process silver data into gold (Entity Master)."""
    
    def __init__(self, db, resolver):
        self.db = db
        self.resolver = resolver
    
    # =========================================================================
    # SEC Company → Entity
    # =========================================================================
    
    async def process_sec_to_entities(
        self,
        source_date: date,
    ) -> Tuple[int, int, int]:
        """
        Process silver SEC companies into Entity Master.
        
        Returns (created, updated, errors)
        """
        silver_records = await self.db.fetch_all("""
            SELECT * FROM silver.sec_companies
            WHERE source_date = :date
              AND cik_valid = TRUE
        """, {'date': source_date})
        
        created = 0
        updated = 0
        errors = 0
        
        for record in silver_records:
            try:
                # Check if entity already exists by CIK
                existing = await self.resolver.store.get_by_identifier(
                    scheme='cik',
                    value=record['cik'],
                )
                
                if existing and existing.entity:
                    # Update existing entity
                    await self._update_entity_from_sec(existing.entity, record)
                    updated += 1
                else:
                    # Create new entity
                    await self._create_entity_from_sec(record)
                    created += 1
                
            except Exception as e:
                logger.error(f"Error processing SEC company {record['cik']}: {e}")
                errors += 1
        
        return created, updated, errors
    
    async def _create_entity_from_sec(self, record: dict) -> str:
        """Create new entity from SEC company data."""
        
        from ..core.types import Entity, EntityType, EntityStatus
        
        entity_id = generate_ulid()
        
        entity = Entity(
            entity_id=entity_id,
            primary_name=record['company_name'],
            entity_type=EntityType.ORGANIZATION,
            status=EntityStatus.ACTIVE,
            cik=record['cik'],
        )
        
        # Create entity
        await self.resolver.store.create_entity(entity)
        
        # Add CIK identifier
        await self.resolver.store.add_identifier(Identifier(
            identifier_id=generate_ulid(),
            scheme='cik',
            value=record['cik'],
            entity_id=entity_id,
            source='sec',
        ))
        
        # Add alias
        await self.resolver.store.add_alias(
            entity_id=entity_id,
            alias=record['company_name'],
            alias_type='primary',
        )
        
        # If ticker present, create security and listing
        if record['ticker'] and record['exchange']:
            await self._create_security_listing(entity_id, record)
        
        return entity_id
    
    async def _update_entity_from_sec(self, entity: Entity, record: dict):
        """Update existing entity with SEC data."""
        
        # Update name if changed
        if entity.primary_name != record['company_name']:
            # Add old name as alias
            await self.resolver.store.add_alias(
                entity_id=entity.entity_id,
                alias=entity.primary_name,
                alias_type='former',
            )
            
            # Update primary name
            entity.primary_name = record['company_name']
            await self.resolver.store.update_entity(entity)
        
        # Update ticker/listing if changed
        if record['ticker'] and record['exchange']:
            await self._update_security_listing(entity.entity_id, record)
    
    async def _create_security_listing(self, entity_id: str, record: dict):
        """Create security and listing for an entity."""
        
        from ..core.types import Security, Listing, SecurityType
        
        # Create security
        security_id = generate_ulid()
        
        security = Security(
            security_id=security_id,
            issuer_entity_id=entity_id,
            name=f"{record['company_name']} Common Stock",
            security_type=SecurityType.COMMON_STOCK,
        )
        
        await self.db.execute("""
            INSERT INTO securities (
                security_id, issuer_entity_id, name, security_type, status
            ) VALUES (
                :id, :entity_id, :name, :type, 'active'
            )
        """, {
            'id': security_id,
            'entity_id': entity_id,
            'name': security.name,
            'type': security.security_type.value,
        })
        
        # Create listing
        listing_id = generate_ulid()
        mic = record['exchange']  # Already standardized in silver
        
        listing = Listing(
            listing_id=listing_id,
            security_id=security_id,
            mic=mic,
            ticker=record['ticker'],
        )
        
        await self.db.execute("""
            INSERT INTO listings (
                listing_id, security_id, mic, ticker, status, valid_from
            ) VALUES (
                :id, :security_id, :mic, :ticker, 'active', :valid_from
            )
        """, {
            'id': listing_id,
            'security_id': security_id,
            'mic': mic,
            'ticker': record['ticker'],
            'valid_from': record['source_date'],
        })
    
    # =========================================================================
    # OpenFIGI → Security/Crosswalk
    # =========================================================================
    
    async def process_figi_to_securities(
        self,
        source_date: date,
    ) -> Tuple[int, int, int]:
        """
        Process silver FIGI data into Entity Master.
        
        FIGI maps to Security (not Entity!).
        """
        silver_records = await self.db.fetch_all("""
            SELECT * FROM silver.openfigi_instruments
            WHERE source_date = :date
              AND figi_valid = TRUE
        """, {'date': source_date})
        
        matched = 0
        unmatched = 0
        errors = 0
        
        for record in silver_records:
            try:
                # Try to match to existing security
                security_id = await self._match_figi_to_security(record)
                
                if security_id:
                    # Add FIGI as identifier
                    await self._add_figi_identifier(security_id, record)
                    matched += 1
                else:
                    # Store as partial mapping for later
                    await self._store_partial_figi(record)
                    unmatched += 1
                
            except Exception as e:
                logger.error(f"Error processing FIGI {record['figi']}: {e}")
                errors += 1
        
        return matched, unmatched, errors
    
    async def _match_figi_to_security(self, record: dict) -> Optional[str]:
        """Try to match FIGI record to existing security."""
        
        # Strategy 1: Match by ticker + exchange
        if record['ticker'] and record['exchange_mic']:
            result = await self.db.fetch_one("""
                SELECT security_id FROM listings
                WHERE ticker = :ticker AND mic = :mic AND status = 'active'
            """, {'ticker': record['ticker'], 'mic': record['exchange_mic']})
            
            if result:
                return result['security_id']
        
        # Strategy 2: Match by security name (fuzzy)
        if record['security_name']:
            # Use resolver's fuzzy search
            results = await self.resolver.store.search_by_name(
                record['security_name'],
                limit=3,
                fuzzy=True,
            )
            
            if results and len(results) == 1:
                # Unambiguous match - get primary security
                securities = await self.db.fetch_all("""
                    SELECT security_id FROM securities
                    WHERE issuer_entity_id = :entity_id AND status = 'active'
                """, {'entity_id': results[0].entity_id})
                
                if len(securities) == 1:
                    return securities[0]['security_id']
        
        return None
    
    async def _add_figi_identifier(self, security_id: str, record: dict):
        """Add FIGI identifier to security."""
        
        # Add primary FIGI
        await self.resolver.store.add_identifier(Identifier(
            identifier_id=generate_ulid(),
            scheme='figi',
            value=record['figi'],
            security_id=security_id,
            source='openfigi',
        ))
        
        # Add composite FIGI if present
        if record['composite_figi']:
            await self.resolver.store.add_identifier(Identifier(
                identifier_id=generate_ulid(),
                scheme='composite_figi',
                value=record['composite_figi'],
                security_id=security_id,
                source='openfigi',
            ))
    
    async def _store_partial_figi(self, record: dict):
        """Store unmatched FIGI for later resolution."""
        
        await self.db.execute("""
            INSERT INTO partial_mappings (
                partial_id, vendor, vendor_id_type, vendor_id_value,
                scope, hints, first_seen_at
            ) VALUES (
                :id, 'openfigi', 'figi', :figi,
                'security', :hints, NOW()
            )
            ON CONFLICT DO NOTHING
        """, {
            'id': generate_ulid(),
            'figi': record['figi'],
            'hints': json.dumps({
                'ticker': record['ticker'],
                'exchange': record['exchange_mic'],
                'name': record['security_name'],
            }),
        })
    
    # =========================================================================
    # FactSet → Crosswalk
    # =========================================================================
    
    async def process_factset_crosswalks(
        self,
        source_date: date,
    ) -> Tuple[int, int, int]:
        """
        Process silver FactSet data into crosswalks.
        """
        silver_records = await self.db.fetch_all("""
            SELECT * FROM silver.factset_securities
            WHERE source_date = :date
        """, {'date': source_date})
        
        matched = 0
        unmatched = 0
        errors = 0
        
        for record in silver_records:
            try:
                # Entity-level crosswalk
                if record['fs_entity_id']:
                    entity_id = await self._match_factset_entity(record)
                    if entity_id:
                        await self.resolver.store.add_crosswalk(Crosswalk(
                            crosswalk_id=generate_ulid(),
                            vendor='factset',
                            vendor_id_type='entity_id',
                            vendor_id_value=record['fs_entity_id'],
                            entity_id=entity_id,
                        ))
                        matched += 1
                    else:
                        unmatched += 1
                
                # Security-level crosswalk
                if record['fs_security_id']:
                    security_id = await self._match_factset_security(record)
                    if security_id:
                        await self.resolver.store.add_crosswalk(Crosswalk(
                            crosswalk_id=generate_ulid(),
                            vendor='factset',
                            vendor_id_type='security_id',
                            vendor_id_value=record['fs_security_id'],
                            security_id=security_id,
                        ))
                        matched += 1
                    else:
                        unmatched += 1
                
            except Exception as e:
                logger.error(f"Error processing FactSet {record['factset_id']}: {e}")
                errors += 1
        
        return matched, unmatched, errors
    
    async def _match_factset_entity(self, record: dict) -> Optional[str]:
        """Match FactSet record to entity."""
        
        # Try ISIN → Security → Entity
        if record['isin'] and record['isin_valid']:
            result = await self.resolver.store.get_by_identifier(
                scheme='isin',
                value=record['isin'],
            )
            if result and result.security:
                # Get entity from security
                security = await self.db.fetch_one("""
                    SELECT issuer_entity_id FROM securities
                    WHERE security_id = :id
                """, {'id': result.security.security_id})
                
                if security:
                    return security['issuer_entity_id']
        
        # Try name match
        if record['entity_name']:
            results = await self.resolver.store.search_by_name(
                record['entity_name'],
                limit=1,
                fuzzy=False,  # Exact match only
            )
            if results:
                return results[0].entity_id
        
        return None
    
    async def _match_factset_security(self, record: dict) -> Optional[str]:
        """Match FactSet record to security."""
        
        # Try ISIN
        if record['isin'] and record['isin_valid']:
            result = await self.resolver.store.get_by_identifier(
                scheme='isin',
                value=record['isin'],
            )
            if result and result.security:
                return result.security.security_id
        
        # Try CUSIP
        if record['cusip'] and record['cusip_valid']:
            result = await self.resolver.store.get_by_identifier(
                scheme='cusip',
                value=record['cusip'],
            )
            if result and result.security:
                return result.security.security_id
        
        # Try ticker + exchange
        if record['ticker'] and record['exchange_mic']:
            listing = await self.db.fetch_one("""
                SELECT security_id FROM listings
                WHERE ticker = :ticker AND mic = :mic AND status = 'active'
            """, {'ticker': record['ticker'], 'mic': record['exchange_mic']})
            
            if listing:
                return listing['security_id']
        
        return None
```

---

## Pipeline Orchestration

```python
"""FeedSpine pipeline orchestration."""

from datetime import date, timedelta
import asyncio


class FeedSpinePipeline:
    """Orchestrate Bronze → Silver → Gold processing."""
    
    def __init__(self, db, resolver):
        self.db = db
        self.resolver = resolver
        
        self.bronze = BronzeIngester(db)
        self.silver = SilverProcessor(db)
        self.gold = GoldProcessor(db, resolver)
    
    async def run_daily_pipeline(self, process_date: date = None):
        """Run full daily pipeline."""
        
        if process_date is None:
            process_date = date.today()
        
        logger.info(f"Starting FeedSpine pipeline for {process_date}")
        
        # =====================================================================
        # Bronze: Ingest raw data
        # =====================================================================
        
        logger.info("BRONZE: Ingesting raw data...")
        
        # SEC company tickers
        sec_data = await self._fetch_sec_company_tickers()
        sec_count = await self.bronze.ingest_sec_company_tickers(
            data=sec_data,
            source_url="https://www.sec.gov/files/company_tickers.json",
            file_date=process_date,
        )
        logger.info(f"  SEC company tickers: {sec_count} records")
        
        # SEC filing index
        index_data = await self._fetch_sec_daily_index(process_date)
        index_count = await self.bronze.ingest_sec_filing_index(
            index_data=index_data,
            index_type='daily-index',
            index_date=process_date,
        )
        logger.info(f"  SEC daily index: {index_count} records")
        
        # =====================================================================
        # Silver: Clean and validate
        # =====================================================================
        
        logger.info("SILVER: Cleaning and validating...")
        
        sec_proc, sec_err = await self.silver.process_sec_companies(process_date)
        logger.info(f"  SEC companies: {sec_proc} processed, {sec_err} errors")
        
        figi_proc, figi_err = await self.silver.process_openfigi_instruments(process_date)
        logger.info(f"  OpenFIGI instruments: {figi_proc} processed, {figi_err} errors")
        
        # =====================================================================
        # Gold: Entity resolution
        # =====================================================================
        
        logger.info("GOLD: Entity Master population...")
        
        ent_created, ent_updated, ent_err = await self.gold.process_sec_to_entities(process_date)
        logger.info(f"  SEC → Entities: {ent_created} created, {ent_updated} updated, {ent_err} errors")
        
        figi_matched, figi_unmatched, figi_err = await self.gold.process_figi_to_securities(process_date)
        logger.info(f"  FIGI → Securities: {figi_matched} matched, {figi_unmatched} unmatched, {figi_err} errors")
        
        # =====================================================================
        # Summary
        # =====================================================================
        
        logger.info(f"Pipeline complete for {process_date}")
        
        return {
            'date': process_date,
            'bronze': {
                'sec_company_tickers': sec_count,
                'sec_daily_index': index_count,
            },
            'silver': {
                'sec_companies': {'processed': sec_proc, 'errors': sec_err},
                'openfigi': {'processed': figi_proc, 'errors': figi_err},
            },
            'gold': {
                'entities': {'created': ent_created, 'updated': ent_updated, 'errors': ent_err},
                'figi_securities': {'matched': figi_matched, 'unmatched': figi_unmatched, 'errors': figi_err},
            },
        }
    
    async def backfill(self, start_date: date, end_date: date):
        """Backfill historical data."""
        
        current = start_date
        while current <= end_date:
            try:
                await self.run_daily_pipeline(current)
            except Exception as e:
                logger.error(f"Error processing {current}: {e}")
            
            current += timedelta(days=1)
```

---

## Next Document

→ [08_GOVERNANCE_AUDIT.md](08_GOVERNANCE_AUDIT.md) - ID types, audit trails, testing strategy
