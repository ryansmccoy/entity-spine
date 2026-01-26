# Entity Master - Canonical Data Model

**The correct separation of Entity, Security, and Listing identities.**

---

## The Core Problem

Most identity systems conflate three distinct concepts:

| Concept | Example | What Most Systems Do Wrong |
|---------|---------|---------------------------|
| **Entity** | Alphabet Inc. | Mix with securities ("GOOG is a company") |
| **Security** | Alphabet Class A common stock | Confuse with listings ("GOOGL is traded") |
| **Listing** | GOOGL on NASDAQ (XNAS) | Assume ticker = security = company |

This causes silent corruption:
- Ticker reuse breaks historical queries (GM 2009 ≠ GM 2010)
- Multi-class issuers break crosswalks (GOOG vs GOOGL → same company, different securities)
- Multi-listed securities break analytics (AAPL on XNAS vs AAPL on XMEX)

---

## Canonical Concepts

### 1. Entity (Issuer / Organization)

An **Entity** is a real-world legal or organizational identity.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ENTITY                                                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│  Definition:                                                                │
│    A legal person (corporation, partnership, government, fund, individual)  │
│    that has independent existence regardless of securities issued.          │
│                                                                             │
│  Examples:                                                                  │
│    • Alphabet Inc. (Delaware corporation, CIK 1652044)                      │
│    • United States Treasury (government entity)                             │
│    • Vanguard Group Inc (fund sponsor - not the fund itself)                │
│    • Tim Cook (individual - for executive/director tracking)                │
│                                                                             │
│  Key Properties:                                                            │
│    • Has legal jurisdiction (state/country of incorporation)                │
│    • May have corporate hierarchy (parent/subsidiary relationships)          │
│    • Can issue zero or more securities                                      │
│    • Has persistent identity even if all securities delisted                │
│                                                                             │
│  Primary Identifiers:                                                       │
│    • CIK (SEC filers)                                                       │
│    • LEI (GLEIF - legal entities)                                           │
│    • DUNS (D&B - any business)                                              │
│    • PermID Entity (Refinitiv)                                              │
│    • FactSet Entity ID                                                      │
│    • S&P GVKEY                                                              │
│                                                                             │
│  NOT Entity Identifiers:                                                    │
│    • FIGI (identifies securities, not entities)                             │
│    • ISIN (identifies securities)                                           │
│    • Ticker (identifies listings)                                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2. Security (Financial Instrument)

A **Security** is a financial instrument issued by an entity.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  SECURITY                                                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│  Definition:                                                                │
│    A fungible financial instrument that represents a claim on an issuer     │
│    (equity, debt, derivative, fund share class).                            │
│                                                                             │
│  Examples:                                                                  │
│    • Alphabet Class A Common Stock (ISIN US02079K3059)                      │
│    • Alphabet Class C Common Stock (ISIN US02079K1079)                      │
│    • Apple Inc 2.40% Notes due 2050 (a specific bond)                       │
│    • Vanguard 500 Index Fund Admiral Shares (fund share class)              │
│                                                                             │
│  Key Properties:                                                            │
│    • Issued by exactly one entity at a point in time                        │
│    • Has instrument type (common, preferred, bond, option, fund)            │
│    • May have multiple listings on different exchanges                      │
│    • Has lifecycle (issuance → trading → maturity/redemption)               │
│                                                                             │
│  Primary Identifiers:                                                       │
│    • ISIN (international standard)                                          │
│    • CUSIP (US/Canada)                                                      │
│    • SEDOL (UK/Ireland)                                                     │
│    • FIGI (Bloomberg)                                                       │
│    • FactSet Security ID                                                    │
│    • Refinitiv QuoteID                                                      │
│                                                                             │
│  Relationship to Entity:                                                    │
│    One Entity can issue MANY Securities                                     │
│    • Alphabet Inc → Class A, Class C stocks                                 │
│    • Apple Inc → Common stock + many bond issuances                         │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3. Listing (Trading Identity)

A **Listing** is a traded instance of a security on an exchange.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  LISTING                                                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│  Definition:                                                                │
│    A specific tradeable quote of a security on an exchange/venue,           │
│    identified by ticker + MIC (market identifier code) + currency.          │
│                                                                             │
│  Examples:                                                                  │
│    • GOOGL on NASDAQ (MIC: XNAS, USD)                                       │
│    • GOOG on NASDAQ (MIC: XNAS, USD) — different security, same issuer      │
│    • AAPL on NASDAQ (MIC: XNAS, USD)                                        │
│    • AAPL on Mexico Exchange (MIC: XMEX, MXN) — same security, diff listing │
│    • VOD on LSE (MIC: XLON, GBP)                                            │
│    • VOD on NASDAQ (MIC: XNAS, USD) — ADR, actually different security      │
│                                                                             │
│  Key Properties:                                                            │
│    • Ticker can be REUSED over time (requires temporal tracking)            │
│    • Maps to exactly ONE security at a point in time                        │
│    • Has trading status (active, halted, delisted)                          │
│    • Has primary/secondary designation                                      │
│                                                                             │
│  Primary Identifiers:                                                       │
│    • Composite Key: (Ticker, MIC, valid_from, valid_to)                     │
│    • Bloomberg Ticker (includes exchange suffix)                            │
│    • Reuters RIC                                                            │
│    • FactSet Listing ID                                                     │
│    • OpenFIGI (maps to listings, not entities!)                             │
│                                                                             │
│  CRITICAL: Ticker Reuse                                                     │
│    • GM (2009) → General Motors Corp (bankrupt)                             │
│    • GM (2010+) → General Motors Company (new entity)                       │
│    Same ticker, DIFFERENT entities and securities!                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           ENTITY / SECURITY / LISTING MODEL                          │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│                                  ┌───────────────┐                                   │
│                                  │    ENTITY     │                                   │
│                                  │ (Issuer/Org)  │                                   │
│                                  │               │                                   │
│                                  │ • entity_id   │                                   │
│                                  │ • CIK         │                                   │
│                                  │ • LEI         │                                   │
│                                  │ • legal_name  │                                   │
│                                  └───────┬───────┘                                   │
│                                          │                                           │
│                           ┌──────────────┼──────────────┐                            │
│                           │              │              │                            │
│                           │    ISSUES    │    ISSUES    │                            │
│                           │  (1:Many)    │   (1:Many)   │                            │
│                           ▼              ▼              ▼                            │
│                    ┌────────────┐ ┌────────────┐ ┌────────────┐                      │
│                    │  SECURITY  │ │  SECURITY  │ │  SECURITY  │                      │
│                    │ (Class A)  │ │ (Class C)  │ │ (2050 Bond)│                      │
│                    │            │ │            │ │            │                      │
│                    │ • ISIN     │ │ • ISIN     │ │ • ISIN     │                      │
│                    │ • CUSIP    │ │ • CUSIP    │ │ • CUSIP    │                      │
│                    │ • FIGI     │ │ • FIGI     │ │ • FIGI     │                      │
│                    └─────┬──────┘ └─────┬──────┘ └────────────┘                      │
│                          │              │                                            │
│                    ┌─────┴─────┐  ┌─────┴─────┐                                      │
│                    │   TRADES  │  │   TRADES  │                                      │
│                    │  (1:Many) │  │  (1:Many) │                                      │
│                    ▼           ▼  ▼           ▼                                      │
│              ┌──────────┐ ┌──────────┐ ┌──────────┐                                  │
│              │ LISTING  │ │ LISTING  │ │ LISTING  │                                  │
│              │ GOOGL    │ │ GOOG     │ │ GOOGL    │                                  │
│              │ @XNAS    │ │ @XNAS    │ │ @XMEX    │                                  │
│              │          │ │          │ │          │                                  │
│              │ • ticker │ │ • ticker │ │ • ticker │                                  │
│              │ • MIC    │ │ • MIC    │ │ • MIC    │                                  │
│              │ • ccy    │ │ • ccy    │ │ • ccy    │                                  │
│              └──────────┘ └──────────┘ └──────────┘                                  │
│                                                                                      │
│  CARDINALITY:                                                                        │
│  ─────────────                                                                       │
│  Entity (1) ─issues─► Security (Many)                                                │
│  Security (1) ─trades─► Listing (Many)                                               │
│  Listing (Many) ─at_time─► Security (1)  [point-in-time: ticker reuse!]             │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Canonical Schema

### Core Tables

```sql
-- =============================================================================
-- ENTITIES (Issuers / Organizations)
-- =============================================================================

CREATE TABLE entities (
    -- Canonical ID (stable, internal)
    entity_id           CHAR(26) PRIMARY KEY,  -- ULID for sortability + uniqueness
    
    -- Classification
    entity_type         VARCHAR(30) NOT NULL,  -- See EntityType enum below
    entity_subtype      VARCHAR(50),           -- e.g., 'corporation', 'llc', 'lp'
    
    -- Names
    legal_name          VARCHAR(500) NOT NULL, -- Official legal name
    primary_name        VARCHAR(500),          -- Commonly used name
    
    -- Jurisdiction
    jurisdiction_country VARCHAR(2),           -- ISO 3166-1 alpha-2
    jurisdiction_state   VARCHAR(10),          -- State/province code
    
    -- SEC-specific (nullable for non-SEC entities)
    sic_code            VARCHAR(4),
    sic_description     VARCHAR(200),
    fiscal_year_end     VARCHAR(4),            -- MMDD format
    
    -- Lifecycle
    status              VARCHAR(20) NOT NULL DEFAULT 'active',
    -- 'active', 'inactive', 'merged', 'dissolved', 'acquired'
    
    inactive_reason     VARCHAR(100),          -- Why inactive
    successor_entity_id CHAR(26) REFERENCES entities(entity_id),  -- If merged/acquired
    
    -- Audit
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by          VARCHAR(100),
    
    -- Constraints
    CONSTRAINT chk_entity_type CHECK (entity_type IN (
        'COMPANY',           -- Public or private corporation
        'FUND',              -- Investment fund (the fund itself, not sponsor)
        'FUND_SPONSOR',      -- Fund management company
        'PERSON',            -- Individual (executive, director, insider)
        'GOVERNMENT',        -- Government entity
        'EXCHANGE',          -- Trading venue
        'INDEX_PROVIDER',    -- Index sponsor
        'PRIVATE_COMPANY',   -- Non-public company
        'SUBSIDIARY',        -- Subsidiary entity
        'SPECIAL_PURPOSE'    -- SPV, trust, etc.
    ))
);

-- =============================================================================
-- SECURITIES (Financial Instruments)
-- =============================================================================

CREATE TABLE securities (
    -- Canonical ID
    security_id         CHAR(26) PRIMARY KEY,  -- ULID
    
    -- Issuer link (required)
    issuer_entity_id    CHAR(26) NOT NULL REFERENCES entities(entity_id),
    
    -- Classification
    security_type       VARCHAR(30) NOT NULL,  -- See SecurityType enum
    security_subtype    VARCHAR(50),           -- e.g., 'class_a', 'series_b'
    
    -- Descriptors
    name                VARCHAR(500) NOT NULL, -- Security name
    description         TEXT,
    
    -- For equity
    share_class         VARCHAR(50),           -- 'A', 'B', 'C', 'Common', 'Preferred'
    voting_rights       VARCHAR(50),           -- 'full', 'limited', 'none'
    
    -- For debt
    coupon_rate         DECIMAL(8,5),
    maturity_date       DATE,
    par_value           DECIMAL(18,4),
    
    -- For funds
    fund_type           VARCHAR(50),           -- 'mutual', 'etf', 'closed_end'
    share_class_name    VARCHAR(50),           -- 'Admiral', 'Investor', 'Institutional'
    
    -- Currency
    primary_currency    VARCHAR(3),            -- ISO 4217
    
    -- Lifecycle
    status              VARCHAR(20) NOT NULL DEFAULT 'active',
    -- 'active', 'matured', 'redeemed', 'merged', 'delisted'
    
    issue_date          DATE,
    termination_date    DATE,
    
    -- Audit
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT chk_security_type CHECK (security_type IN (
        'COMMON_STOCK',
        'PREFERRED_STOCK',
        'WARRANT',
        'RIGHTS',
        'CONVERTIBLE_BOND',
        'CORPORATE_BOND',
        'GOVERNMENT_BOND',
        'MUNICIPAL_BOND',
        'ETF',
        'MUTUAL_FUND',
        'CLOSED_END_FUND',
        'UNIT',              -- Units (stock + warrant)
        'ADR',               -- American Depositary Receipt
        'GDR',               -- Global Depositary Receipt
        'OPTION',
        'FUTURE',
        'OTHER'
    ))
);

-- =============================================================================
-- LISTINGS (Trading Identities)
-- =============================================================================

CREATE TABLE listings (
    -- Canonical ID
    listing_id          CHAR(26) PRIMARY KEY,  -- ULID
    
    -- Security link (required)
    security_id         CHAR(26) NOT NULL REFERENCES securities(security_id),
    
    -- Trading identity (the unique combination)
    ticker              VARCHAR(20) NOT NULL,
    mic                 VARCHAR(4) NOT NULL,   -- ISO 10383 Market Identifier Code
    currency            VARCHAR(3) NOT NULL,   -- ISO 4217 trading currency
    
    -- Exchange details
    exchange_name       VARCHAR(100),          -- Human-readable
    country             VARCHAR(2),            -- Exchange country
    
    -- Listing type
    listing_type        VARCHAR(30),           -- 'primary', 'secondary', 'adr', 'gdr'
    is_primary          BOOLEAN DEFAULT false,
    
    -- Trading status
    status              VARCHAR(20) NOT NULL DEFAULT 'active',
    -- 'active', 'suspended', 'delisted', 'pending'
    
    -- Temporal validity (CRITICAL for ticker reuse)
    valid_from          DATE NOT NULL,         -- When this listing became valid
    valid_to            DATE,                  -- NULL means current; set on delist
    
    -- Delisting info
    delist_reason       VARCHAR(100),
    successor_listing_id CHAR(26) REFERENCES listings(listing_id),
    
    -- Trading metadata
    lot_size            INT,
    price_currency      VARCHAR(3),
    
    -- Audit
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Unique constraint: ticker+mic+timeframe must be unique
    -- (Same ticker can exist in different time periods)
    CONSTRAINT uq_listing_ticker_mic_period 
        UNIQUE (ticker, mic, valid_from)
);

CREATE INDEX idx_listings_ticker ON listings(ticker);
CREATE INDEX idx_listings_active ON listings(ticker, mic) WHERE status = 'active' AND valid_to IS NULL;
CREATE INDEX idx_listings_security ON listings(security_id);
```

### Identifier Tables

```sql
-- =============================================================================
-- IDENTIFIERS (Scoped by Entity/Security/Listing)
-- =============================================================================

CREATE TABLE identifiers (
    identifier_id       CHAR(26) PRIMARY KEY,  -- ULID
    
    -- Scope: exactly ONE of these must be set
    entity_id           CHAR(26) REFERENCES entities(entity_id),
    security_id         CHAR(26) REFERENCES securities(security_id),
    listing_id          CHAR(26) REFERENCES listings(listing_id),
    
    -- Identifier details
    scheme              VARCHAR(30) NOT NULL,  -- 'cik', 'lei', 'figi', 'isin', etc.
    value               VARCHAR(100) NOT NULL, -- The identifier value
    
    -- For vendor-specific IDs
    vendor              VARCHAR(30),           -- 'bloomberg', 'factset', 'refinitiv', 's&p'
    vendor_id_type      VARCHAR(50),           -- 'BUID', 'BSID', 'entity_id', etc.
    
    -- Source tracking (provenance)
    source              VARCHAR(50) NOT NULL,  -- Where we got this
    source_id           VARCHAR(200),          -- Reference in source system
    
    -- Confidence and quality
    confidence          DECIMAL(3,2) DEFAULT 1.0,  -- 0.00 to 1.00
    is_primary          BOOLEAN DEFAULT false, -- Primary identifier for this scheme
    is_verified         BOOLEAN DEFAULT false, -- Manually verified
    
    -- Temporal validity
    valid_from          DATE,                  -- When identifier became valid
    valid_to            DATE,                  -- NULL = still valid
    
    -- Capture tracking
    first_seen_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    capture_date        DATE NOT NULL DEFAULT CURRENT_DATE,
    
    -- Audit
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT chk_identifier_scope CHECK (
        (entity_id IS NOT NULL)::int +
        (security_id IS NOT NULL)::int +
        (listing_id IS NOT NULL)::int = 1
    ),
    
    CONSTRAINT chk_scheme CHECK (scheme IN (
        -- Entity-scoped
        'cik',           -- SEC Central Index Key
        'lei',           -- Legal Entity Identifier
        'duns',          -- D&B Number
        'ein',           -- Employer Identification Number
        'permid_entity', -- Refinitiv Entity PermID
        'factset_entity',-- FactSet Entity ID
        'sp_gvkey',      -- S&P Global Company Key
        'bbg_company',   -- Bloomberg Company ID
        
        -- Security-scoped
        'isin',          -- International Securities ID
        'cusip',         -- CUSIP
        'sedol',         -- SEDOL
        'figi',          -- Bloomberg FIGI
        'composite_figi',-- Bloomberg Composite FIGI
        'share_class_figi', -- Bloomberg Share Class FIGI
        'permid_quote',  -- Refinitiv Quote PermID
        'factset_sec',   -- FactSet Security ID
        
        -- Listing-scoped
        'ticker',        -- Ticker symbol (legacy, prefer listing table)
        'ric',           -- Reuters Instrument Code
        'bbg_ticker',    -- Bloomberg Ticker
        'factset_listing', -- FactSet Listing ID
        'exchange_figi', -- OpenFIGI Exchange-specific
        
        -- Generic/Other
        'internal',      -- Our internal ID
        'other'
    )),
    
    -- Uniqueness: scheme + value should be unique within scope (with temporal)
    CONSTRAINT uq_identifier UNIQUE (scheme, value, valid_from, entity_id, security_id, listing_id)
);

CREATE INDEX idx_identifiers_scheme_value ON identifiers(scheme, value);
CREATE INDEX idx_identifiers_entity ON identifiers(entity_id) WHERE entity_id IS NOT NULL;
CREATE INDEX idx_identifiers_security ON identifiers(security_id) WHERE security_id IS NOT NULL;
CREATE INDEX idx_identifiers_listing ON identifiers(listing_id) WHERE listing_id IS NOT NULL;
CREATE INDEX idx_identifiers_current ON identifiers(scheme, value) WHERE valid_to IS NULL;
```

### Name/Alias Tables

```sql
-- =============================================================================
-- ENTITY ALIASES (Name normalization)
-- =============================================================================

CREATE TABLE entity_aliases (
    alias_id            CHAR(26) PRIMARY KEY,  -- ULID
    entity_id           CHAR(26) NOT NULL REFERENCES entities(entity_id),
    
    -- Alias details
    name                VARCHAR(500) NOT NULL,
    name_normalized     VARCHAR(500),          -- Lowercased, trimmed, standardized
    alias_type          VARCHAR(30) NOT NULL,
    
    -- Source
    source              VARCHAR(50) NOT NULL,
    source_id           VARCHAR(200),
    
    -- Temporal
    valid_from          DATE,
    valid_to            DATE,
    
    -- Priority
    is_primary          BOOLEAN DEFAULT false,
    priority            INT DEFAULT 0,         -- Higher = preferred
    
    -- Audit
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT chk_alias_type CHECK (alias_type IN (
        'legal',         -- Official legal name
        'trade',         -- Trade name / DBA
        'former',        -- Previous name
        'short',         -- Abbreviated name
        'ticker_derived', -- Name derived from ticker
        'sec_filing',    -- Name from SEC filing
        'extracted',     -- NER extracted name
        'manual'         -- Manually added
    ))
);

CREATE INDEX idx_aliases_name ON entity_aliases(name_normalized);
CREATE INDEX idx_aliases_entity ON entity_aliases(entity_id);

-- Full-text search index (Tier 2+)
CREATE INDEX idx_aliases_fts ON entity_aliases USING gin(to_tsvector('english', name));
```

### Corporate Hierarchy

```sql
-- =============================================================================
-- CORPORATE HIERARCHY (Parent/Subsidiary relationships)
-- =============================================================================

CREATE TABLE corporate_hierarchy (
    hierarchy_id        CHAR(26) PRIMARY KEY,  -- ULID
    
    -- Relationship parties
    parent_entity_id    CHAR(26) NOT NULL REFERENCES entities(entity_id),
    child_entity_id     CHAR(26) NOT NULL REFERENCES entities(entity_id),
    
    -- Relationship type
    relationship_type   VARCHAR(30) NOT NULL,
    
    -- Ownership details (optional)
    ownership_pct       DECIMAL(6,3),          -- e.g., 100.000, 51.500
    ownership_type      VARCHAR(30),           -- 'direct', 'indirect', 'beneficial'
    voting_pct          DECIMAL(6,3),
    
    -- Temporal
    effective_date      DATE,                  -- When relationship started
    end_date            DATE,                  -- NULL = still active
    
    -- Evidence (provenance)
    source              VARCHAR(50) NOT NULL,
    source_id           VARCHAR(200),          -- e.g., filing accession number
    evidence_text       TEXT,
    confidence          DECIMAL(3,2) DEFAULT 1.0,
    
    -- Audit
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT chk_hierarchy_type CHECK (relationship_type IN (
        'parent_of',         -- A is parent of B
        'subsidiary_of',     -- A is subsidiary of B (inverse)
        'ultimate_parent_of',-- A is ultimate parent of B
        'controlled_by',     -- A is controlled by B
        'affiliated_with'    -- A is affiliated with B (no ownership)
    )),
    
    -- Prevent self-reference
    CONSTRAINT chk_no_self_ref CHECK (parent_entity_id != child_entity_id),
    
    -- Unique constraint
    CONSTRAINT uq_hierarchy UNIQUE (parent_entity_id, child_entity_id, relationship_type, effective_date)
);

CREATE INDEX idx_hierarchy_parent ON corporate_hierarchy(parent_entity_id);
CREATE INDEX idx_hierarchy_child ON corporate_hierarchy(child_entity_id);
CREATE INDEX idx_hierarchy_active ON corporate_hierarchy(parent_entity_id, child_entity_id) 
    WHERE end_date IS NULL;
```

### Entity Merges

```sql
-- =============================================================================
-- ENTITY MERGES (Tombstones and redirects)
-- =============================================================================

CREATE TABLE entity_merges (
    merge_id            CHAR(26) PRIMARY KEY,  -- ULID
    
    -- What was merged
    from_entity_id      CHAR(26) NOT NULL,     -- No FK - entity may be soft-deleted
    to_entity_id        CHAR(26) NOT NULL REFERENCES entities(entity_id),
    
    -- Merge details
    merge_type          VARCHAR(30) NOT NULL,
    reason              TEXT,
    
    -- Temporal
    merged_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    effective_date      DATE,                  -- Business effective date
    
    -- Evidence
    source              VARCHAR(50) NOT NULL,
    source_id           VARCHAR(200),
    evidence_text       TEXT,
    
    -- Who approved
    approved_by         VARCHAR(100),
    approved_at         TIMESTAMPTZ,
    
    -- Audit
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT chk_merge_type CHECK (merge_type IN (
        'duplicate',         -- Same entity, duplicate records
        'acquisition',       -- from_entity was acquired by to_entity
        'merger',            -- Both merged into to_entity
        'reorganization',    -- Corporate restructuring
        'name_change',       -- Same entity, name changed (soft merge)
        'data_correction'    -- Data error correction
    ))
);

CREATE INDEX idx_merges_from ON entity_merges(from_entity_id);
CREATE INDEX idx_merges_to ON entity_merges(to_entity_id);

-- View for resolving old IDs to current
CREATE VIEW v_entity_redirects AS
WITH RECURSIVE redirect_chain AS (
    -- Base: direct merges
    SELECT 
        from_entity_id AS original_id,
        to_entity_id AS current_id,
        1 AS depth
    FROM entity_merges
    
    UNION ALL
    
    -- Recursive: follow chain
    SELECT 
        rc.original_id,
        em.to_entity_id AS current_id,
        rc.depth + 1
    FROM redirect_chain rc
    JOIN entity_merges em ON em.from_entity_id = rc.current_id
    WHERE rc.depth < 10  -- Prevent infinite loops
)
SELECT DISTINCT ON (original_id)
    original_id,
    current_id
FROM redirect_chain
ORDER BY original_id, depth DESC;
```

---

## Examples

### Example 1: Alphabet Inc. (Dual Share Classes)

```
ENTITY: Alphabet Inc.
├── entity_id: 01HYX7M1Y0... (ULID)
├── entity_type: COMPANY
├── legal_name: "Alphabet Inc."
├── CIK: 1652044
├── LEI: 5493006MHB84DD0ZWV18
│
├── SECURITY: Alphabet Class A Common Stock
│   ├── security_id: 01HYX7M2A1...
│   ├── security_type: COMMON_STOCK
│   ├── share_class: "A"
│   ├── ISIN: US02079K3059
│   ├── CUSIP: 02079K305
│   ├── FIGI: BBG009S39JX6
│   │
│   └── LISTING: GOOGL on NASDAQ
│       ├── listing_id: 01HYX7M3B2...
│       ├── ticker: GOOGL
│       ├── mic: XNAS
│       ├── currency: USD
│       ├── valid_from: 2014-04-03
│       └── is_primary: true
│
└── SECURITY: Alphabet Class C Common Stock
    ├── security_id: 01HYX7M4C3...
    ├── security_type: COMMON_STOCK
    ├── share_class: "C"
    ├── voting_rights: "none"
    ├── ISIN: US02079K1079
    ├── CUSIP: 02079K107
    ├── FIGI: BBG009S3NB30
    │
    └── LISTING: GOOG on NASDAQ
        ├── listing_id: 01HYX7M5D4...
        ├── ticker: GOOG
        ├── mic: XNAS
        ├── currency: USD
        ├── valid_from: 2014-04-03
        └── is_primary: true
```

### Example 2: Ticker Reuse (GM)

```
ENTITY: General Motors Corporation (OLD - bankrupt)
├── entity_id: 01HYX8A1...
├── status: INACTIVE
├── inactive_reason: "Chapter 11 bankruptcy"
├── CIK: 40730
│
└── SECURITY: GM Corp Common Stock
    ├── security_id: 01HYX8A2...
    ├── status: DELISTED
    │
    └── LISTING: GM on NYSE (historical)
        ├── listing_id: 01HYX8A3...
        ├── ticker: GM
        ├── mic: XNYS
        ├── valid_from: 1916-01-01 (approx)
        ├── valid_to: 2009-06-01     ← CRITICAL: ended!
        └── status: DELISTED

---

ENTITY: General Motors Company (NEW)
├── entity_id: 01HYX8B1... (DIFFERENT entity!)
├── status: ACTIVE
├── CIK: 1467858 (DIFFERENT CIK!)
├── LEI: 54930070NSV60J38I987
│
└── SECURITY: GM Company Common Stock
    ├── security_id: 01HYX8B2...
    ├── ISIN: US37045V1008 (DIFFERENT ISIN!)
    │
    └── LISTING: GM on NYSE (current)
        ├── listing_id: 01HYX8B3...
        ├── ticker: GM
        ├── mic: XNYS
        ├── valid_from: 2010-11-18   ← Starts AFTER old one ended
        ├── valid_to: NULL           ← Still active
        └── status: ACTIVE
```

**Query: "What was GM trading on 2008-01-01?"**
```sql
SELECT e.legal_name, s.name, l.ticker, l.mic
FROM listings l
JOIN securities s ON s.security_id = l.security_id
JOIN entities e ON e.entity_id = s.issuer_entity_id
WHERE l.ticker = 'GM'
  AND l.mic = 'XNYS'
  AND l.valid_from <= '2008-01-01'
  AND (l.valid_to IS NULL OR l.valid_to > '2008-01-01');

-- Returns: General Motors Corporation (the old company)
```

### Example 3: Public Subsidiary

```
ENTITY: Berkshire Hathaway Inc. (Parent)
├── entity_id: 01HYX9P1...
├── CIK: 1067983
├── LEI: 549300Q6TC5EY2FHWR82
│
├── CORPORATE_HIERARCHY (parent_of):
│   └── child: GEICO Corporation (subsidiary, 100% owned)
│
├── CORPORATE_HIERARCHY (parent_of):
│   └── child: See's Candies (subsidiary, 100% owned)
│
└── SECURITIES: BRK.A, BRK.B (multiple share classes)

---

ENTITY: GEICO Corporation
├── entity_id: 01HYX9Q2...
├── entity_type: SUBSIDIARY
├── CIK: 40274
│
├── CORPORATE_HIERARCHY:
│   └── subsidiary_of: Berkshire Hathaway Inc.
│       ├── ownership_pct: 100.0
│       ├── effective_date: 1996-01-02
│       └── source: "10-K filing"
│
└── (No public securities - wholly owned)
```

### Example 4: Multi-Listing Across Exchanges

```
ENTITY: Royal Dutch Shell PLC
├── entity_id: 01HYXAM1...
├── LEI: 21380068P1DRHMJ8KU70
│
└── SECURITY: Shell Ordinary Shares
    ├── security_id: 01HYXAM2...
    ├── ISIN: GB00BP6MXD84
    │
    ├── LISTING: SHEL on LSE
    │   ├── ticker: SHEL
    │   ├── mic: XLON
    │   ├── currency: GBP
    │   └── is_primary: true
    │
    ├── LISTING: SHEL on Euronext Amsterdam
    │   ├── ticker: SHELL
    │   ├── mic: XAMS
    │   ├── currency: EUR
    │   └── is_primary: false
    │
    └── LISTING: SHEL ADR on NYSE
        ├── ticker: SHEL
        ├── mic: XNYS
        ├── currency: USD
        ├── listing_type: ADR
        └── is_primary: false (for US market)
```

---

## Identifier Scope Rules

| Identifier | Scope | Notes |
|------------|-------|-------|
| **CIK** | Entity | SEC filer identifier; one per SEC-registered entity |
| **LEI** | Entity | GLEIF legal entity; one per legal entity globally |
| **DUNS** | Entity | D&B business identifier |
| **EIN** | Entity | US tax identifier |
| **PermID Entity** | Entity | Refinitiv entity identifier |
| **FactSet Entity ID** | Entity | FactSet entity identifier |
| **S&P GVKEY** | Entity | S&P Global company key |
| | | |
| **ISIN** | Security | One per security globally |
| **CUSIP** | Security | US/Canada security identifier |
| **SEDOL** | Security | UK/Ireland security identifier |
| **FIGI** | Security | Bloomberg security identifier |
| **Composite FIGI** | Security | Bloomberg country-level FIGI |
| | | |
| **Ticker** | Listing | Exchange-specific, can be reused |
| **Exchange FIGI** | Listing | Bloomberg exchange-specific FIGI |
| **RIC** | Listing | Reuters listing identifier |
| **Bloomberg Ticker** | Listing | BBG ticker with exchange suffix |

---

## OpenFIGI Clarification

**FIGI is primarily a Security/Listing identifier, NOT an Entity identifier.**

```
OpenFIGI returns:
┌─────────────────────────────────────────────────────────────────┐
│  {                                                              │
│    "figi": "BBG000B9XRY4",        ← Security-level FIGI        │
│    "name": "APPLE INC",                                         │
│    "ticker": "AAPL",                                            │
│    "exchCode": "US",                                            │
│    "compositeFIGI": "BBG000B9XRY4",  ← Composite (country)     │
│    "shareClassFIGI": "BBG001S5N8V8", ← Share class FIGI        │
│    "securityType": "Common Stock"                               │
│  }                                                              │
└─────────────────────────────────────────────────────────────────┘
```

**Correct attachment:**
- `figi` (BBG000B9XRY4) → Security table
- `compositeFIGI` → Security table (different ID type)
- `shareClassFIGI` → Security table (share class level)
- Exchange-specific FIGI → Listing table

**Wrong:**
- Attaching FIGI to Entity table (there is no "issuer FIGI")
- Treating FIGI as company identifier

If you need "all FIGIs for a company," you query:
```sql
SELECT i.value AS figi
FROM identifiers i
JOIN securities s ON s.security_id = i.security_id
WHERE s.issuer_entity_id = :entity_id
  AND i.scheme = 'figi';
```

---

## Next Documents

- [10_CROSSWALK_STRATEGY.md](10_CROSSWALK_STRATEGY.md) - Vendor ID mapping
- [11_RESOLUTION_STRATEGY.md](11_RESOLUTION_STRATEGY.md) - Resolution paths
- [12_STORAGE_TIERS.md](12_STORAGE_TIERS.md) - Tiered schema implementations
- [13_PYSECEDGAR_PORT.md](13_PYSECEDGAR_PORT.md) - py-sec-edgar integration
