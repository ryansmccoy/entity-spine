# Entity Master v2 - Canonical Data Model

**Version 2.0 | Complete ERD with explicit Entity/Security/Listing separation**

---

## Design Principles

### Non-Negotiable Rules

1. **Entity ≠ Security ≠ Listing** - Three distinct object types with explicit relationships
2. **Identifiers have scope** - CIK→Entity, ISIN→Security, Ticker→Listing (never cross-attached)
3. **Vendor IDs in crosswalks** - Not in `identifiers` table; strict scope enforcement
4. **Temporal validity everywhere** - `valid_from`/`valid_to` + `first_seen`/`last_seen`
5. **Provisional entities are first-class** - Created from mentions, mergeable, with redirect history
6. **Merges preserve lineage** - Tombstones point to canonical; follow_redirects is always possible

### ID Strategy

- **Primary Keys**: ULID (26 chars) - sortable, unique, no coordination needed
- **Natural Keys**: Scheme+Value for identifiers; Vendor+Type+Value for crosswalks
- **Foreign Keys**: Reference canonical IDs; follow redirects on read

---

## Entity-Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                          ENTITY MASTER v2 - CANONICAL MODEL                              │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐    │
│  │                              ENTITIES                                            │    │
│  │                       (Issuers/Organizations)                                    │    │
│  ├─────────────────────────────────────────────────────────────────────────────────┤    │
│  │  entity_id (PK)           ULID                                                   │    │
│  │  entity_type              COMPANY|FUND|PERSON|GOVERNMENT|SPV|UNKNOWN             │    │
│  │  status                   active|inactive|merged|provisional                     │    │
│  │  legal_name               Official registered name                               │    │
│  │  primary_name             Trading/common name                                    │    │
│  │  jurisdiction_country     ISO 3166-1 alpha-2                                     │    │
│  │  jurisdiction_subdiv      State/province                                         │    │
│  │  formation_date           When formed/incorporated                               │    │
│  │  dissolution_date         When dissolved (if applicable)                         │    │
│  │  sic_code                 4-digit SIC                                            │    │
│  │  naics_code               6-digit NAICS                                          │    │
│  │  is_public                SEC filer?                                             │    │
│  │  source_system            Where first created                                    │    │
│  │  confidence               1.0 for authoritative, lower for provisional           │    │
│  └──────────┬──────────────────────────────────────────────────────────────────────┘    │
│             │                                                                            │
│             │ 1:N (issues)                                                               │
│             ▼                                                                            │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐    │
│  │                              SECURITIES                                          │    │
│  │                       (Financial Instruments)                                    │    │
│  ├─────────────────────────────────────────────────────────────────────────────────┤    │
│  │  security_id (PK)         ULID                                                   │    │
│  │  issuer_entity_id (FK)    → entities.entity_id                                   │    │
│  │  security_type            common_stock|preferred|bond|warrant|option|fund_share  │    │
│  │  name                     Security name                                          │    │
│  │  currency                 ISO 4217 (denomination currency)                       │    │
│  │  status                   active|inactive|merged|called|converted                │    │
│  │  issue_date               When issued                                            │    │
│  │  maturity_date            For bonds/notes                                        │    │
│  │  shares_outstanding       For equities                                           │    │
│  └──────────┬──────────────────────────────────────────────────────────────────────┘    │
│             │                                                                            │
│             │ 1:N (trades_as)                                                            │
│             ▼                                                                            │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐    │
│  │                              LISTINGS                                            │    │
│  │                       (Trading Identities)                                       │    │
│  ├─────────────────────────────────────────────────────────────────────────────────┤    │
│  │  listing_id (PK)          ULID                                                   │    │
│  │  security_id (FK)         → securities.security_id                               │    │
│  │  ticker                   Exchange symbol                                        │    │
│  │  mic                      Market Identifier Code (ISO 10383)                     │    │
│  │  currency                 Trading currency                                       │    │
│  │  is_primary               Primary listing for this security?                     │    │
│  │  status                   active|suspended|delisted                              │    │
│  │  valid_from               When listing became active                             │    │
│  │  valid_to                 When delisted (NULL = active)                          │    │
│  │  lot_size                 Trading lot size                                       │    │
│  └─────────────────────────────────────────────────────────────────────────────────┘    │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Core Tables - PostgreSQL DDL

### Entities Table

```sql
-- =============================================================================
-- ENTITIES (Issuers/Organizations - the real-world legal identity)
-- =============================================================================
CREATE TABLE entities (
    entity_id               CHAR(26) PRIMARY KEY,  -- ULID
    
    -- Classification
    entity_type             VARCHAR(30) NOT NULL DEFAULT 'UNKNOWN',
    status                  VARCHAR(20) NOT NULL DEFAULT 'active',
    confidence              DECIMAL(3,2) NOT NULL DEFAULT 1.0,
    
    -- Names
    legal_name              VARCHAR(500),           -- Registered legal name
    primary_name            VARCHAR(500) NOT NULL,  -- Common/trading name
    
    -- Jurisdiction
    jurisdiction_country    CHAR(2),               -- ISO 3166-1 alpha-2
    jurisdiction_subdiv     VARCHAR(10),           -- State/province code
    
    -- Lifecycle
    formation_date          DATE,
    dissolution_date        DATE,
    
    -- Classification
    sic_code                CHAR(4),
    naics_code              CHAR(6),
    is_public               BOOLEAN DEFAULT FALSE,
    
    -- Provenance
    source_system           VARCHAR(50) NOT NULL,
    source_id               VARCHAR(200),          -- ID in source system
    
    -- Timestamps
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    first_seen_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT chk_entity_type CHECK (entity_type IN (
        'COMPANY', 'FUND', 'PERSON', 'GOVERNMENT', 'SPV', 
        'TRUST', 'PARTNERSHIP', 'UNKNOWN'
    )),
    CONSTRAINT chk_entity_status CHECK (status IN (
        'active', 'inactive', 'merged', 'provisional', 'disputed'
    ))
);

CREATE INDEX idx_entities_type_status ON entities(entity_type, status);
CREATE INDEX idx_entities_name ON entities(primary_name);
CREATE INDEX idx_entities_jurisdiction ON entities(jurisdiction_country, jurisdiction_subdiv);
CREATE INDEX idx_entities_sic ON entities(sic_code);
CREATE INDEX idx_entities_source ON entities(source_system, source_id);

-- Full-text search index (Tier 2+)
CREATE INDEX idx_entities_fts ON entities 
    USING GIN(to_tsvector('english', COALESCE(legal_name, '') || ' ' || primary_name));
```

### Securities Table

```sql
-- =============================================================================
-- SECURITIES (Financial Instruments issued by entities)
-- =============================================================================
CREATE TABLE securities (
    security_id             CHAR(26) PRIMARY KEY,  -- ULID
    
    -- Issuer relationship
    issuer_entity_id        CHAR(26) NOT NULL REFERENCES entities(entity_id),
    
    -- Security info
    security_type           VARCHAR(30) NOT NULL,
    name                    VARCHAR(500) NOT NULL,
    currency                CHAR(3),               -- ISO 4217 (denomination)
    status                  VARCHAR(20) NOT NULL DEFAULT 'active',
    
    -- Lifecycle
    issue_date              DATE,
    maturity_date           DATE,                  -- For bonds
    call_date               DATE,                  -- If called early
    
    -- For equities
    share_class             VARCHAR(10),           -- A, B, C, etc.
    voting_rights           DECIMAL(5,2),          -- Votes per share
    shares_outstanding      BIGINT,
    
    -- For bonds
    coupon_rate             DECIMAL(6,4),
    face_value              DECIMAL(15,2),
    
    -- Provenance
    source_system           VARCHAR(50) NOT NULL,
    source_id               VARCHAR(200),
    
    -- Timestamps
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT chk_security_type CHECK (security_type IN (
        'common_stock', 'preferred_stock', 'adr', 'gdr',
        'corporate_bond', 'government_bond', 'municipal_bond',
        'warrant', 'option', 'future', 'fund_share', 'etf',
        'convertible', 'unit', 'right', 'other'
    )),
    CONSTRAINT chk_security_status CHECK (status IN (
        'active', 'inactive', 'merged', 'called', 'converted', 'matured'
    ))
);

CREATE INDEX idx_securities_issuer ON securities(issuer_entity_id);
CREATE INDEX idx_securities_type ON securities(security_type, status);
CREATE INDEX idx_securities_name ON securities(name);
```

### Listings Table

```sql
-- =============================================================================
-- LISTINGS (Trading identities - where/how securities trade)
-- =============================================================================
CREATE TABLE listings (
    listing_id              CHAR(26) PRIMARY KEY,  -- ULID
    
    -- Security relationship
    security_id             CHAR(26) NOT NULL REFERENCES securities(security_id),
    
    -- Trading identity
    ticker                  VARCHAR(20) NOT NULL,
    mic                     CHAR(4) NOT NULL,      -- Market Identifier Code
    currency                CHAR(3) NOT NULL,      -- Trading currency (ISO 4217)
    
    -- Status
    is_primary              BOOLEAN NOT NULL DEFAULT FALSE,
    status                  VARCHAR(20) NOT NULL DEFAULT 'active',
    
    -- Temporal validity (critical for ticker reuse)
    valid_from              DATE NOT NULL,
    valid_to                DATE,                  -- NULL = currently active
    
    -- Trading info
    lot_size                INT DEFAULT 1,
    exchange_code           VARCHAR(20),           -- Exchange's internal code
    
    -- Provenance
    source_system           VARCHAR(50) NOT NULL,
    source_id               VARCHAR(200),
    
    -- Timestamps
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    first_seen_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT chk_listing_status CHECK (status IN (
        'active', 'suspended', 'delisted', 'merged'
    )),
    -- Ensure no overlapping ticker+MIC periods
    CONSTRAINT uq_listing_ticker_mic_period EXCLUDE USING GIST (
        ticker WITH =,
        mic WITH =,
        daterange(valid_from, COALESCE(valid_to, '9999-12-31'::date)) WITH &&
    )
);

CREATE INDEX idx_listings_security ON listings(security_id);
CREATE INDEX idx_listings_ticker_mic ON listings(ticker, mic);
CREATE INDEX idx_listings_active ON listings(ticker, mic, status) WHERE status = 'active';
CREATE INDEX idx_listings_temporal ON listings(ticker, mic, valid_from, valid_to);

-- Partial unique index for active primary listings per security
CREATE UNIQUE INDEX idx_listings_primary 
    ON listings(security_id) 
    WHERE is_primary = TRUE AND status = 'active';
```

---

## Identifier and Crosswalk Tables

### Standard Identifiers Table

```sql
-- =============================================================================
-- IDENTIFIERS (Standard/public identifier schemes)
-- Attach to exactly ONE scope (entity OR security OR listing)
-- =============================================================================
CREATE TABLE identifiers (
    identifier_id           CHAR(26) PRIMARY KEY,  -- ULID
    
    -- Scope: exactly one must be set
    entity_id               CHAR(26) REFERENCES entities(entity_id),
    security_id             CHAR(26) REFERENCES securities(security_id),
    listing_id              CHAR(26) REFERENCES listings(listing_id),
    
    -- Identifier
    scheme                  VARCHAR(30) NOT NULL,  -- See enum below
    value                   VARCHAR(100) NOT NULL,
    
    -- Temporal validity
    valid_from              DATE,
    valid_to                DATE,
    
    -- Tracking
    first_seen_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_verified_at        TIMESTAMPTZ,
    
    -- Provenance
    source_system           VARCHAR(50) NOT NULL,
    confidence              DECIMAL(3,2) DEFAULT 1.0,
    
    -- Timestamps
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Exactly one scope must be set
    CONSTRAINT chk_identifier_scope CHECK (
        (entity_id IS NOT NULL)::int +
        (security_id IS NOT NULL)::int +
        (listing_id IS NOT NULL)::int = 1
    ),
    
    -- Unique identifier per scheme (considering validity)
    CONSTRAINT uq_identifier_scheme_value UNIQUE (scheme, value)
);

-- Scheme-specific indexes
CREATE INDEX idx_identifiers_entity ON identifiers(entity_id) WHERE entity_id IS NOT NULL;
CREATE INDEX idx_identifiers_security ON identifiers(security_id) WHERE security_id IS NOT NULL;
CREATE INDEX idx_identifiers_listing ON identifiers(listing_id) WHERE listing_id IS NOT NULL;
CREATE INDEX idx_identifiers_scheme_value ON identifiers(scheme, value);
CREATE INDEX idx_identifiers_value ON identifiers(value);  -- For reverse lookups
```

### Identifier Scope Matrix

```sql
-- =============================================================================
-- Valid identifier schemes and their correct scopes
-- =============================================================================
CREATE TABLE identifier_schemes (
    scheme                  VARCHAR(30) PRIMARY KEY,
    scope                   VARCHAR(20) NOT NULL,  -- 'entity', 'security', 'listing'
    authority               VARCHAR(100),          -- Issuing authority
    format_regex            VARCHAR(200),          -- Validation pattern
    description             TEXT,
    
    CONSTRAINT chk_scheme_scope CHECK (scope IN ('entity', 'security', 'listing'))
);

INSERT INTO identifier_schemes (scheme, scope, authority, format_regex, description) VALUES
-- Entity-scoped
('cik',             'entity',   'SEC',          '^[0-9]{10}$',          'SEC Central Index Key'),
('lei',             'entity',   'GLEIF',        '^[A-Z0-9]{20}$',       'Legal Entity Identifier'),
('ein',             'entity',   'IRS',          '^[0-9]{2}-[0-9]{7}$',  'Employer Identification Number'),
('duns',            'entity',   'D&B',          '^[0-9]{9}$',           'DUNS Number'),
('rssd_id',         'entity',   'Fed Reserve',  '^[0-9]+$',             'Federal Reserve RSSD ID'),

-- Security-scoped (FIGI is security, NOT entity!)
('isin',            'security', 'NNAs',         '^[A-Z]{2}[A-Z0-9]{9}[0-9]$', 'ISIN'),
('cusip',           'security', 'CUSIP Global', '^[A-Z0-9]{9}$',        'CUSIP'),
('sedol',           'security', 'LSE',          '^[A-Z0-9]{7}$',        'SEDOL'),
('figi',            'security', 'OMG/Bloomberg','^BBG[A-Z0-9]{9}$',     'FIGI'),
('composite_figi',  'security', 'OMG/Bloomberg','^BBG[A-Z0-9]{9}$',     'Composite FIGI'),
('share_class_figi','security', 'OMG/Bloomberg','^BBG[A-Z0-9]{9}$',     'Share Class FIGI'),
('valor',           'security', 'SIX',          '^[0-9]+$',             'Swiss Valor'),
('wkn',             'security', 'WM Data',      '^[A-Z0-9]{6}$',        'German WKN'),

-- Listing-scoped
('ric',             'listing',  'Refinitiv',    NULL,                   'Reuters Instrument Code'),
('bbg_ticker',      'listing',  'Bloomberg',    NULL,                   'Bloomberg Ticker'),
('exchange_figi',   'listing',  'OMG/Bloomberg','^BBG[A-Z0-9]{9}$',     'Exchange FIGI');

-- Enforce correct scope on insert/update
CREATE OR REPLACE FUNCTION validate_identifier_scope()
RETURNS TRIGGER AS $$
DECLARE
    expected_scope VARCHAR(20);
    actual_scope VARCHAR(20);
BEGIN
    -- Get expected scope for this scheme
    SELECT scope INTO expected_scope 
    FROM identifier_schemes 
    WHERE scheme = NEW.scheme;
    
    IF expected_scope IS NULL THEN
        RAISE EXCEPTION 'Unknown identifier scheme: %', NEW.scheme;
    END IF;
    
    -- Determine actual scope from which FK is set
    IF NEW.entity_id IS NOT NULL THEN
        actual_scope := 'entity';
    ELSIF NEW.security_id IS NOT NULL THEN
        actual_scope := 'security';
    ELSIF NEW.listing_id IS NOT NULL THEN
        actual_scope := 'listing';
    END IF;
    
    -- Validate match
    IF expected_scope != actual_scope THEN
        RAISE EXCEPTION 'Identifier scheme % must be attached to scope %, not %',
            NEW.scheme, expected_scope, actual_scope;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_validate_identifier_scope
    BEFORE INSERT OR UPDATE ON identifiers
    FOR EACH ROW
    EXECUTE FUNCTION validate_identifier_scope();
```

### Vendor Crosswalks Table

```sql
-- =============================================================================
-- CROSSWALKS (Vendor-specific ID mappings)
-- Separate from identifiers because these are vendor-internal IDs
-- =============================================================================
CREATE TABLE crosswalks (
    crosswalk_id            CHAR(26) PRIMARY KEY,  -- ULID
    
    -- Our canonical ID (exactly one set)
    entity_id               CHAR(26) REFERENCES entities(entity_id),
    security_id             CHAR(26) REFERENCES securities(security_id),
    listing_id              CHAR(26) REFERENCES listings(listing_id),
    
    -- Vendor identifier
    vendor                  VARCHAR(30) NOT NULL,
    vendor_id_type          VARCHAR(50) NOT NULL,
    vendor_id_value         VARCHAR(200) NOT NULL,
    
    -- Mapping provenance
    mapping_source          VARCHAR(50) NOT NULL,  -- 'vendor_file', 'api_lookup', 'manual', etc.
    mapping_method          VARCHAR(30) NOT NULL,  -- 'exact', 'derived', 'inferred'
    confidence              DECIMAL(3,2) DEFAULT 1.0,
    
    -- Temporal validity
    valid_from              DATE,
    valid_to                DATE,
    
    -- Tracking
    first_seen_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_verified_at        TIMESTAMPTZ,
    
    -- Conflict tracking
    conflict_count          INT DEFAULT 0,
    conflict_notes          TEXT,
    
    -- Timestamps
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Exactly one scope must be set
    CONSTRAINT chk_crosswalk_scope CHECK (
        (entity_id IS NOT NULL)::int +
        (security_id IS NOT NULL)::int +
        (listing_id IS NOT NULL)::int = 1
    ),
    
    -- Unique vendor ID mapping
    CONSTRAINT uq_crosswalk_vendor_id UNIQUE (vendor, vendor_id_type, vendor_id_value)
);

CREATE INDEX idx_crosswalks_vendor ON crosswalks(vendor, vendor_id_type, vendor_id_value);
CREATE INDEX idx_crosswalks_entity ON crosswalks(entity_id) WHERE entity_id IS NOT NULL;
CREATE INDEX idx_crosswalks_security ON crosswalks(security_id) WHERE security_id IS NOT NULL;
CREATE INDEX idx_crosswalks_listing ON crosswalks(listing_id) WHERE listing_id IS NOT NULL;

-- Valid vendor ID types and their scopes
CREATE TABLE vendor_id_types (
    vendor                  VARCHAR(30) NOT NULL,
    vendor_id_type          VARCHAR(50) NOT NULL,
    scope                   VARCHAR(20) NOT NULL,
    description             TEXT,
    
    PRIMARY KEY (vendor, vendor_id_type),
    CONSTRAINT chk_vendor_scope CHECK (scope IN ('entity', 'security', 'listing'))
);

INSERT INTO vendor_id_types (vendor, vendor_id_type, scope, description) VALUES
-- FactSet
('factset', 'entity_id',    'entity',   'FactSet Entity ID (e.g., 000C7F-E)'),
('factset', 'security_id',  'security', 'FactSet Security ID (e.g., 000C7F-S-US)'),
('factset', 'regional_id',  'security', 'FactSet Regional ID (e.g., 000C7F-R-US)'),
('factset', 'listing_id',   'listing',  'FactSet Listing ID (e.g., 000C7F-L-NYS-USD)'),

-- Bloomberg
('bloomberg', 'company_id', 'entity',   'Bloomberg Company ID (internal)'),
('bloomberg', 'buid',       'security', 'Bloomberg Unique ID'),
('bloomberg', 'bsid',       'security', 'Bloomberg Security ID'),
('bloomberg', 'bbid',       'listing',  'Bloomberg ID (exchange-specific)'),

-- Refinitiv
('refinitiv', 'permid_org',   'entity',   'PermID Organization'),
('refinitiv', 'permid_quote', 'security', 'PermID Quote/Instrument'),

-- S&P
('sp', 'gvkey',     'entity',   'S&P Global Company Key'),
('sp', 'gvkey_iid', 'security', 'GVKEY + Issue ID');

-- Enforce correct scope on crosswalk insert/update
CREATE OR REPLACE FUNCTION validate_crosswalk_scope()
RETURNS TRIGGER AS $$
DECLARE
    expected_scope VARCHAR(20);
    actual_scope VARCHAR(20);
BEGIN
    SELECT scope INTO expected_scope 
    FROM vendor_id_types 
    WHERE vendor = NEW.vendor AND vendor_id_type = NEW.vendor_id_type;
    
    -- Allow unknown types (with warning logged)
    IF expected_scope IS NULL THEN
        RETURN NEW;  -- Or RAISE WARNING
    END IF;
    
    IF NEW.entity_id IS NOT NULL THEN
        actual_scope := 'entity';
    ELSIF NEW.security_id IS NOT NULL THEN
        actual_scope := 'security';
    ELSIF NEW.listing_id IS NOT NULL THEN
        actual_scope := 'listing';
    END IF;
    
    IF expected_scope != actual_scope THEN
        RAISE EXCEPTION 'Vendor ID % % must be attached to scope %, not %',
            NEW.vendor, NEW.vendor_id_type, expected_scope, actual_scope;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_validate_crosswalk_scope
    BEFORE INSERT OR UPDATE ON crosswalks
    FOR EACH ROW
    EXECUTE FUNCTION validate_crosswalk_scope();
```

---

## Alias and Merge Tables

### Entity Aliases

```sql
-- =============================================================================
-- ENTITY_ALIASES (All known names for entities)
-- =============================================================================
CREATE TABLE entity_aliases (
    alias_id                CHAR(26) PRIMARY KEY,  -- ULID
    entity_id               CHAR(26) NOT NULL REFERENCES entities(entity_id),
    
    -- The alias
    alias_type              VARCHAR(30) NOT NULL,
    name                    VARCHAR(500) NOT NULL,
    name_normalized         VARCHAR(500) NOT NULL,  -- For exact matching
    
    -- Temporal validity (for former names)
    valid_from              DATE,
    valid_to                DATE,
    
    -- Provenance
    source_system           VARCHAR(50) NOT NULL,
    confidence              DECIMAL(3,2) DEFAULT 1.0,
    
    -- Language
    language                CHAR(2) DEFAULT 'en',
    
    -- Timestamps
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT chk_alias_type CHECK (alias_type IN (
        'legal',      -- Legal/registered name
        'trade',      -- Trading name / DBA
        'former',     -- Former name (has valid_to)
        'short',      -- Abbreviated name
        'ticker',     -- Name derived from ticker
        'extracted',  -- Extracted from documents
        'alternate',  -- Other known name
        'misspelling' -- Common misspelling (for fuzzy matching)
    ))
);

CREATE INDEX idx_aliases_entity ON entity_aliases(entity_id);
CREATE INDEX idx_aliases_normalized ON entity_aliases(name_normalized);
CREATE INDEX idx_aliases_name ON entity_aliases(name);
CREATE INDEX idx_aliases_fts ON entity_aliases 
    USING GIN(to_tsvector('english', name));
```

### Entity Merges (Redirects)

```sql
-- =============================================================================
-- ENTITY_MERGES (Track when entities are merged/consolidated)
-- The old entity_id becomes a tombstone pointing to canonical
-- =============================================================================
CREATE TABLE entity_merges (
    merge_id                CHAR(26) PRIMARY KEY,  -- ULID
    
    -- The redirect
    from_entity_id          CHAR(26) NOT NULL REFERENCES entities(entity_id),
    to_entity_id            CHAR(26) NOT NULL REFERENCES entities(entity_id),
    
    -- Merge details
    merge_type              VARCHAR(30) NOT NULL,
    reason                  TEXT,
    evidence_text           TEXT,
    
    -- When
    merged_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    effective_date          DATE,
    
    -- Who/what
    source_system           VARCHAR(50) NOT NULL,
    approved_by             VARCHAR(100),
    
    CONSTRAINT chk_merge_type CHECK (merge_type IN (
        'duplicate',      -- Duplicate records merged
        'corporate',      -- Corporate M&A
        'correction',     -- Data correction
        'provisional',    -- Provisional entity merged to canonical
        'subsidiary'      -- Subsidiary merged into parent
    )),
    CONSTRAINT chk_no_self_merge CHECK (from_entity_id != to_entity_id)
);

CREATE INDEX idx_merges_from ON entity_merges(from_entity_id);
CREATE INDEX idx_merges_to ON entity_merges(to_entity_id);
CREATE INDEX idx_merges_date ON entity_merges(merged_at);

-- Security and listing merges (similar structure)
CREATE TABLE security_merges (
    merge_id                CHAR(26) PRIMARY KEY,
    from_security_id        CHAR(26) NOT NULL REFERENCES securities(security_id),
    to_security_id          CHAR(26) NOT NULL REFERENCES securities(security_id),
    merge_type              VARCHAR(30) NOT NULL,
    reason                  TEXT,
    merged_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source_system           VARCHAR(50) NOT NULL,
    CONSTRAINT chk_no_self_merge CHECK (from_security_id != to_security_id)
);

CREATE TABLE listing_merges (
    merge_id                CHAR(26) PRIMARY KEY,
    from_listing_id         CHAR(26) NOT NULL REFERENCES listings(listing_id),
    to_listing_id           CHAR(26) NOT NULL REFERENCES listings(listing_id),
    merge_type              VARCHAR(30) NOT NULL,
    reason                  TEXT,
    merged_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source_system           VARCHAR(50) NOT NULL,
    CONSTRAINT chk_no_self_merge CHECK (from_listing_id != to_listing_id)
);
```

### Canonical Views (Follow Redirects)

```sql
-- =============================================================================
-- VIEW: Current canonical entity for any entity_id (follows redirect chain)
-- =============================================================================
CREATE VIEW v_entity_canonical AS
WITH RECURSIVE merge_chain AS (
    -- Base: all entities
    SELECT 
        entity_id AS original_id,
        entity_id AS current_id,
        0 AS depth
    FROM entities
    
    UNION ALL
    
    -- Follow redirect chain
    SELECT 
        mc.original_id,
        em.to_entity_id AS current_id,
        mc.depth + 1
    FROM merge_chain mc
    JOIN entity_merges em ON em.from_entity_id = mc.current_id
    WHERE mc.depth < 10  -- Prevent infinite loops
)
SELECT DISTINCT ON (original_id)
    original_id,
    current_id AS canonical_id,
    original_id != current_id AS was_merged,
    depth AS redirect_depth
FROM merge_chain
ORDER BY original_id, depth DESC;

-- Similar views for securities and listings
CREATE VIEW v_security_canonical AS
WITH RECURSIVE merge_chain AS (
    SELECT security_id AS original_id, security_id AS current_id, 0 AS depth
    FROM securities
    UNION ALL
    SELECT mc.original_id, sm.to_security_id, mc.depth + 1
    FROM merge_chain mc
    JOIN security_merges sm ON sm.from_security_id = mc.current_id
    WHERE mc.depth < 10
)
SELECT DISTINCT ON (original_id)
    original_id, current_id AS canonical_id,
    original_id != current_id AS was_merged
FROM merge_chain ORDER BY original_id, depth DESC;

CREATE VIEW v_listing_canonical AS
WITH RECURSIVE merge_chain AS (
    SELECT listing_id AS original_id, listing_id AS current_id, 0 AS depth
    FROM listings
    UNION ALL
    SELECT mc.original_id, lm.to_listing_id, mc.depth + 1
    FROM merge_chain mc
    JOIN listing_merges lm ON lm.from_listing_id = mc.current_id
    WHERE mc.depth < 10
)
SELECT DISTINCT ON (original_id)
    original_id, current_id AS canonical_id,
    original_id != current_id AS was_merged
FROM merge_chain ORDER BY original_id, depth DESC;
```

---

## Relationship Tables

### Corporate Hierarchy

```sql
-- =============================================================================
-- CORPORATE_HIERARCHY (Parent/subsidiary relationships)
-- =============================================================================
CREATE TABLE corporate_hierarchy (
    relationship_id         CHAR(26) PRIMARY KEY,  -- ULID
    
    parent_entity_id        CHAR(26) NOT NULL REFERENCES entities(entity_id),
    child_entity_id         CHAR(26) NOT NULL REFERENCES entities(entity_id),
    
    -- Ownership details
    relationship_type       VARCHAR(30) NOT NULL DEFAULT 'subsidiary',
    ownership_pct           DECIMAL(5,2),          -- NULL if unknown
    ownership_type          VARCHAR(20),           -- direct, indirect
    control_type            VARCHAR(20),           -- voting, economic
    
    -- Temporal validity
    valid_from              DATE NOT NULL,
    valid_to                DATE,
    
    -- Evidence
    source_system           VARCHAR(50) NOT NULL,
    evidence_type           VARCHAR(30),           -- 'exhibit_21', 'filing_text', etc.
    evidence_id             VARCHAR(200),
    confidence              DECIMAL(3,2) DEFAULT 1.0,
    
    -- Timestamps
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT chk_hierarchy_type CHECK (relationship_type IN (
        'subsidiary', 'branch', 'division', 'affiliate', 'joint_venture'
    )),
    CONSTRAINT chk_no_self_parent CHECK (parent_entity_id != child_entity_id)
);

CREATE INDEX idx_hierarchy_parent ON corporate_hierarchy(parent_entity_id);
CREATE INDEX idx_hierarchy_child ON corporate_hierarchy(child_entity_id);
CREATE INDEX idx_hierarchy_temporal ON corporate_hierarchy(valid_from, valid_to);
```

### Entity Relationships (General)

```sql
-- =============================================================================
-- ENTITY_RELATIONSHIPS (Supplier/customer/competitor/etc.)
-- =============================================================================
CREATE TABLE entity_relationships (
    relationship_id         CHAR(26) PRIMARY KEY,  -- ULID
    
    -- The relationship
    source_entity_id        CHAR(26) NOT NULL REFERENCES entities(entity_id),
    target_entity_id        CHAR(26) NOT NULL REFERENCES entities(entity_id),
    relationship_type       VARCHAR(50) NOT NULL,
    relationship_subtype    VARCHAR(50),
    
    -- Directionality
    is_bidirectional        BOOLEAN DEFAULT FALSE,
    
    -- Confidence and metrics
    confidence              DECIMAL(3,2) NOT NULL DEFAULT 0.5,
    metrics                 JSONB DEFAULT '{}',
    
    -- Temporal validity
    first_observed          DATE NOT NULL,
    last_observed           DATE NOT NULL,
    status                  VARCHAR(20) DEFAULT 'active',
    
    -- Timestamps
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT chk_relationship_type CHECK (relationship_type IN (
        'SUPPLIES_TO', 'BUYS_FROM', 'COMPETES_WITH', 'PARTNER_WITH',
        'INVESTED_IN', 'ACQUIRED', 'MERGED_WITH', 'SPUN_OFF_FROM',
        'EXECUTIVE_OF', 'DIRECTOR_OF', 'AUDITOR_OF', 'LEGAL_COUNSEL_OF'
    ))
);

CREATE INDEX idx_relationships_source ON entity_relationships(source_entity_id);
CREATE INDEX idx_relationships_target ON entity_relationships(target_entity_id);
CREATE INDEX idx_relationships_type ON entity_relationships(relationship_type);
```

### Relationship Evidence

```sql
-- =============================================================================
-- RELATIONSHIP_EVIDENCE (Supporting evidence for relationships)
-- Multiple evidence records per relationship (from different sources)
-- =============================================================================
CREATE TABLE relationship_evidence (
    evidence_id             CHAR(26) PRIMARY KEY,  -- ULID
    relationship_id         CHAR(26) NOT NULL REFERENCES entity_relationships(relationship_id),
    
    -- Source
    source_system           VARCHAR(50) NOT NULL,  -- 'py_sec_edgar', 'news_feed', 'manual'
    source_document_id      VARCHAR(200),          -- Filing accession number, article ID, etc.
    source_section_id       VARCHAR(200),          -- Section within document
    
    -- Evidence details
    evidence_text           TEXT,
    evidence_context        TEXT,                  -- Surrounding context
    char_start              INT,
    char_end                INT,
    
    -- Scoring
    confidence              DECIMAL(3,2) NOT NULL,
    extraction_method       VARCHAR(30),           -- 'regex', 'ml', 'llm', 'manual'
    
    -- When observed
    observed_at             TIMESTAMPTZ NOT NULL,
    
    -- Timestamps
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_evidence_relationship ON relationship_evidence(relationship_id);
CREATE INDEX idx_evidence_source ON relationship_evidence(source_system, source_document_id);
```

---

## Mention and Provisional Entity Tables

```sql
-- =============================================================================
-- MENTIONS (Entity references extracted from documents)
-- =============================================================================
CREATE TABLE mentions (
    mention_id              CHAR(26) PRIMARY KEY,  -- ULID
    
    -- Resolved entity (NULL if unresolved)
    resolved_entity_id      CHAR(26) REFERENCES entities(entity_id),
    resolution_status       VARCHAR(20) NOT NULL DEFAULT 'pending',
    
    -- Raw extraction
    mention_text            VARCHAR(1000) NOT NULL,
    mention_text_normalized VARCHAR(500) NOT NULL,
    entity_type_hint        VARCHAR(30),
    
    -- Source document
    source_system           VARCHAR(50) NOT NULL,
    source_document_id      VARCHAR(200) NOT NULL,
    source_section_id       VARCHAR(200),
    
    -- Position in document
    char_start              INT,
    char_end                INT,
    sentence_context        TEXT,
    
    -- Extraction details
    extraction_method       VARCHAR(30) NOT NULL,
    confidence              DECIMAL(3,2) NOT NULL,
    
    -- Additional context (helps resolution)
    context_hints           JSONB DEFAULT '{}',
    
    -- Timestamps
    extracted_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at             TIMESTAMPTZ,
    
    CONSTRAINT chk_resolution_status CHECK (resolution_status IN (
        'pending',          -- Not yet attempted
        'resolved',         -- Successfully resolved
        'provisional',      -- Created provisional entity
        'unresolvable',     -- Tried but couldn't resolve
        'manual_review'     -- Needs human review
    ))
);

CREATE INDEX idx_mentions_resolved ON mentions(resolved_entity_id) WHERE resolved_entity_id IS NOT NULL;
CREATE INDEX idx_mentions_status ON mentions(resolution_status);
CREATE INDEX idx_mentions_text ON mentions(mention_text_normalized);
CREATE INDEX idx_mentions_source ON mentions(source_system, source_document_id);
CREATE INDEX idx_mentions_pending ON mentions(resolution_status) WHERE resolution_status = 'pending';

-- =============================================================================
-- RESOLUTION_QUEUE (Mentions needing review)
-- =============================================================================
CREATE TABLE resolution_queue (
    queue_id                CHAR(26) PRIMARY KEY,  -- ULID
    mention_id              CHAR(26) NOT NULL REFERENCES mentions(mention_id),
    
    -- Why in queue
    queue_reason            VARCHAR(50) NOT NULL,
    
    -- Candidates
    candidate_entity_ids    CHAR(26)[],
    candidate_scores        DECIMAL(3,2)[],
    
    -- Resolution
    status                  VARCHAR(20) DEFAULT 'pending',
    resolved_entity_id      CHAR(26) REFERENCES entities(entity_id),
    resolution_method       VARCHAR(30),
    resolution_notes        TEXT,
    resolved_by             VARCHAR(100),
    resolved_at             TIMESTAMPTZ,
    
    -- Priority and timing
    priority                INT DEFAULT 0,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT chk_queue_reason CHECK (queue_reason IN (
        'low_confidence',
        'multiple_candidates',
        'no_match',
        'new_entity',
        'conflict',
        'manual_request'
    )),
    CONSTRAINT chk_queue_status CHECK (status IN (
        'pending', 'in_progress', 'resolved', 'skipped', 'escalated'
    ))
);

CREATE INDEX idx_queue_status ON resolution_queue(status, priority DESC);
CREATE INDEX idx_queue_mention ON resolution_queue(mention_id);
```

---

## SQLite Simplified Schema

For Tier 1 (local/single-user), use a denormalized schema:

```sql
-- =============================================================================
-- SQLite SIMPLIFIED SCHEMA (Tier 1)
-- Denormalized for simplicity; one entity can have multiple identifiers inline
-- =============================================================================

CREATE TABLE entities (
    entity_id           TEXT PRIMARY KEY,
    entity_type         TEXT DEFAULT 'COMPANY',
    status              TEXT DEFAULT 'active',
    primary_name        TEXT NOT NULL,
    legal_name          TEXT,
    
    -- Denormalized identifiers (most common)
    cik                 TEXT,
    lei                 TEXT,
    ticker              TEXT,
    exchange            TEXT,
    
    -- Classification
    sic_code            TEXT,
    jurisdiction        TEXT,
    is_public           INTEGER DEFAULT 0,
    
    -- Timestamps
    created_at          TEXT DEFAULT (datetime('now')),
    updated_at          TEXT DEFAULT (datetime('now'))
);

CREATE INDEX idx_entities_cik ON entities(cik);
CREATE INDEX idx_entities_lei ON entities(lei);
CREATE INDEX idx_entities_ticker ON entities(ticker, exchange);
CREATE INDEX idx_entities_name ON entities(primary_name);

-- Additional identifiers in separate table
CREATE TABLE identifiers (
    identifier_id       TEXT PRIMARY KEY,
    entity_id           TEXT NOT NULL REFERENCES entities(entity_id),
    scheme              TEXT NOT NULL,
    value               TEXT NOT NULL,
    valid_from          TEXT,
    valid_to            TEXT,
    source              TEXT,
    UNIQUE (scheme, value)
);

CREATE INDEX idx_identifiers_entity ON identifiers(entity_id);
CREATE INDEX idx_identifiers_lookup ON identifiers(scheme, value);

-- Simple aliases table
CREATE TABLE aliases (
    alias_id            TEXT PRIMARY KEY,
    entity_id           TEXT NOT NULL REFERENCES entities(entity_id),
    alias_type          TEXT,
    name                TEXT NOT NULL,
    name_normalized     TEXT NOT NULL
);

CREATE INDEX idx_aliases_entity ON aliases(entity_id);
CREATE INDEX idx_aliases_normalized ON aliases(name_normalized);

-- Simple merges table
CREATE TABLE entity_merges (
    merge_id            TEXT PRIMARY KEY,
    from_entity_id      TEXT NOT NULL,
    to_entity_id        TEXT NOT NULL,
    merged_at           TEXT DEFAULT (datetime('now'))
);

CREATE INDEX idx_merges_from ON entity_merges(from_entity_id);

-- Mentions (for tracking extracted entities)
CREATE TABLE mentions (
    mention_id          TEXT PRIMARY KEY,
    entity_id           TEXT REFERENCES entities(entity_id),
    mention_text        TEXT NOT NULL,
    source_doc_id       TEXT,
    confidence          REAL,
    extracted_at        TEXT DEFAULT (datetime('now'))
);

CREATE INDEX idx_mentions_entity ON mentions(entity_id);
CREATE INDEX idx_mentions_text ON mentions(mention_text);
```

---

## Key Constraints Summary

| Rule | Enforced By |
|------|-------------|
| Entity ≠ Security ≠ Listing | Separate tables with FK relationships |
| Exactly one scope per identifier | CHECK constraint + trigger |
| FIGI is Security-scoped | `identifier_schemes` + trigger |
| No overlapping ticker+MIC periods | EXCLUDE constraint |
| One primary listing per security | Partial unique index |
| Merges form valid chains | Self-referential FK + no self-merge |
| Vendor IDs have correct scope | `vendor_id_types` + trigger |

---

## Next Document

→ [02_RESOLUTION_AND_MERGE_WORKFLOWS.md](02_RESOLUTION_AND_MERGE_WORKFLOWS.md) - Resolution paths and merge handling
