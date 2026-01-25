# Unified Data Model v2.2

**Version 2.2 | Master Contract Document**

> This document defines the canonical data model shared between `py-sec-edgar` and `entityspine`.  
> It supersedes v2.1 with corrections for scope leakage, claims-based evidence, and vendor mapping.

---

## Table of Contents

1. [Overview](#overview)
2. [Core Principles](#core-principles)
3. [Tier Strategy (Corrected)](#tier-strategy-corrected)
4. [Canonical Schema](#canonical-schema)
5. [Claims & Evidence Model](#claims--evidence-model)
6. [Scheme Registry](#scheme-registry)
7. [Merge & Redirect System](#merge--redirect-system)
8. [Derived Views](#derived-views)
9. [Decision Log](#decision-log)
10. [Known Open Questions](#known-open-questions)

---

## Overview

### Package Responsibilities

| Package | Owns | Does NOT Own |
|---------|------|--------------|
| **entityspine** | Entities, Securities, Listings, Identifiers, Claims, Merges, Crosswalks | Filing content, extraction, events |
| **py-sec-edgar** | Filings, Sections, Events, Relationships, Mentions (as claims) | Entity lifecycle, identity resolution |

### The Inviolable Rule

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    ENTITY ≠ SECURITY ≠ LISTING                              │
│                                                                             │
│  This applies to ALL tiers, including Tier 0.                               │
│  Convenience views may flatten, but canonical truth never conflates them.   │
└─────────────────────────────────────────────────────────────────────────────┘
```

| Object | What It Represents | Example Identifiers | Example |
|--------|-------------------|---------------------|---------|
| **Entity** | Legal organization that files/issues | CIK, LEI, EIN, DUNS | Apple Inc. |
| **Security** | Financial instrument issued | ISIN, CUSIP, FIGI, SEDOL | AAPL Common Stock |
| **Listing** | Where/when security trades | Ticker+MIC+ValidFrom | AAPL on XNAS since 1980 |

---

## Core Principles

### 1. Claims, Not Facts

Every piece of data is a **claim** with provenance:
- Who said it (source_system)
- When we captured it (captured_at)
- How confident we are (confidence)
- What evidence supports it (evidence_uri)

```python
# ❌ WRONG: Treating identifier as fact
entity.lei = "HWUPKR0MPOU8FGXBT394"

# ✅ CORRECT: Treating identifier as claim
claim = IdentifierClaim(
    entity_id="01ARZ3...",
    scheme="lei",
    value="HWUPKR0MPOU8FGXBT394",
    source_system="gleif",
    confidence=1.0,
    captured_at=datetime.now(),
)
```

### 2. Ambiguity is Normal

Resolution returns **ranked candidates**, not a single guess:

```python
# ❌ WRONG: Single result
def resolve(query: str) -> Entity | None: ...

# ✅ CORRECT: Ranked candidates
def resolve(query: str, as_of: date | None = None) -> list[ResolutionCandidate]: ...

@dataclass
class ResolutionCandidate:
    entity_id: str
    score: float           # 0.0 to 1.0
    match_type: str        # 'exact', 'fuzzy', 'alias'
    matched_value: str     # What actually matched
    evidence: list[str]    # Claim IDs that support this
```

### 3. Merges Create Redirects, Never Delete

When entities merge, old IDs remain resolvable forever:

```
Entity A (acquired) ──[MERGED_INTO]──► Entity B (acquirer)
         │
         └── All lookups for A return B with redirect flag
```

### 4. Derived Views ≠ Canonical Truth

Flat convenience views (like "entity with primary ticker") are:
- Clearly marked as derived
- Computed from canonical tables
- Include `as_of` semantics
- Never written to directly

---

## Tier Strategy (Corrected)

### Overview

| Tier | Backend | Dependencies | Entity/Security/Listing |
|------|---------|--------------|------------------------|
| 0 | JSON | None (stdlib) | **Conceptual** - SEC JSON is pre-flattened, but we model it correctly |
| 1 | SQLite | None (stdlib) | **Explicit tables** - entities, securities, listings |
| 2 | DuckDB | Optional | **Explicit tables** + analytics views |
| 3 | PostgreSQL | Optional | **Full schema** + claims + conflicts + crosswalks |

### Tier 0: JSON (Zero Dependencies)

**Source**: SEC `company_tickers.json` (pre-flattened by SEC)

The SEC provides a flat structure, but we **interpret** it correctly:

```python
# SEC provides:
{"0": {"cik_str": "320193", "ticker": "AAPL", "title": "Apple Inc."}}

# We interpret as:
# - Entity: CIK 0000320193, name "Apple Inc."
# - Listing: ticker "AAPL" (we don't know exchange from this file)
# - Security: implied common stock (assumed)

# Resolution returns:
@dataclass
class Tier0Entity:
    """Read-only entity from SEC JSON. Conceptually: Entity + implied Listing."""
    cik: str              # Entity identifier
    name: str             # Entity name
    
    # These are LISTING attributes, exposed for convenience
    # They represent "current primary listing as of SEC file date"
    primary_ticker: str | None = None
    
    # Provenance
    source: str = "sec_company_tickers"
    source_date: date | None = None  # When SEC published this file
```

**Key Point**: `primary_ticker` is a derived convenience, not a property of the entity.

### Tier 1: SQLite (Zero Dependencies, Proper Schema)

```sql
-- =============================================================================
-- ENTITIES (The legal organization)
-- =============================================================================
CREATE TABLE entities (
    entity_id       TEXT PRIMARY KEY,       -- ULID
    entity_type     TEXT NOT NULL DEFAULT 'COMPANY',
    status          TEXT NOT NULL DEFAULT 'active',  -- active, inactive, merged, provisional
    
    -- Names (these ARE entity attributes)
    legal_name      TEXT,
    primary_name    TEXT NOT NULL,
    
    -- Classification
    sic_code        TEXT,
    
    -- Provenance
    source_system   TEXT NOT NULL,
    source_id       TEXT,
    
    -- Timestamps
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
    
    -- Merge support
    merged_into_id  TEXT REFERENCES entities(entity_id),
    merged_at       TEXT
);

-- =============================================================================
-- SECURITIES (Financial instruments issued by entities)
-- =============================================================================
CREATE TABLE securities (
    security_id         TEXT PRIMARY KEY,   -- ULID
    issuer_entity_id    TEXT NOT NULL REFERENCES entities(entity_id),
    
    security_type       TEXT NOT NULL,      -- common_stock, preferred_stock, bond, etc.
    name                TEXT NOT NULL,
    currency            TEXT,               -- ISO 4217 (denomination)
    status              TEXT NOT NULL DEFAULT 'active',
    
    -- Provenance
    source_system       TEXT NOT NULL,
    created_at          TEXT NOT NULL DEFAULT (datetime('now'))
);

-- =============================================================================
-- LISTINGS (Where/when securities trade)
-- =============================================================================
CREATE TABLE listings (
    listing_id      TEXT PRIMARY KEY,       -- ULID
    security_id     TEXT NOT NULL REFERENCES securities(security_id),
    
    ticker          TEXT NOT NULL,
    mic             TEXT,                   -- Market Identifier Code (NULL if unknown)
    
    is_primary      INTEGER NOT NULL DEFAULT 0,
    status          TEXT NOT NULL DEFAULT 'active',
    
    -- CRITICAL: Temporal validity for ticker reuse
    valid_from      TEXT NOT NULL,          -- ISO date
    valid_to        TEXT,                   -- NULL = currently active
    
    -- Provenance
    source_system   TEXT NOT NULL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    
    UNIQUE(ticker, mic, valid_from)
);

-- =============================================================================
-- IDENTIFIER CLAIMS (All identifiers as claims with provenance)
-- =============================================================================
CREATE TABLE identifier_claims (
    claim_id        TEXT PRIMARY KEY,       -- ULID
    
    -- What object this identifies (exactly one non-null)
    entity_id       TEXT REFERENCES entities(entity_id),
    security_id     TEXT REFERENCES securities(security_id),
    listing_id      TEXT REFERENCES listings(listing_id),
    
    -- The identifier
    scheme          TEXT NOT NULL,          -- 'cik', 'lei', 'isin', etc.
    value           TEXT NOT NULL,
    
    -- Claim metadata
    source_system   TEXT NOT NULL,          -- Who made this claim
    confidence      REAL NOT NULL DEFAULT 1.0,
    captured_at     TEXT NOT NULL DEFAULT (datetime('now')),
    
    -- Validity period
    valid_from      TEXT,
    valid_to        TEXT,
    
    -- Status
    status          TEXT NOT NULL DEFAULT 'active',  -- active, superseded, disputed
    
    CHECK (
        (entity_id IS NOT NULL AND security_id IS NULL AND listing_id IS NULL) OR
        (entity_id IS NULL AND security_id IS NOT NULL AND listing_id IS NULL) OR
        (entity_id IS NULL AND security_id IS NULL AND listing_id IS NOT NULL)
    )
);

-- =============================================================================
-- ALIASES (Name variants)
-- =============================================================================
CREATE TABLE aliases (
    alias_id        TEXT PRIMARY KEY,
    entity_id       TEXT NOT NULL REFERENCES entities(entity_id),
    
    alias_text      TEXT NOT NULL,
    alias_type      TEXT NOT NULL DEFAULT 'alternate',  -- legal, trade, former, extracted
    
    source_system   TEXT NOT NULL,
    captured_at     TEXT NOT NULL DEFAULT (datetime('now'))
);

-- =============================================================================
-- INDEXES
-- =============================================================================
CREATE INDEX idx_entities_status ON entities(status);
CREATE INDEX idx_entities_merged ON entities(merged_into_id) WHERE merged_into_id IS NOT NULL;

CREATE INDEX idx_securities_issuer ON securities(issuer_entity_id);

CREATE INDEX idx_listings_ticker ON listings(ticker);
CREATE INDEX idx_listings_security ON listings(security_id);
CREATE INDEX idx_listings_valid ON listings(valid_from, valid_to);

CREATE INDEX idx_claims_scheme_value ON identifier_claims(scheme, value);
CREATE INDEX idx_claims_entity ON identifier_claims(entity_id) WHERE entity_id IS NOT NULL;
CREATE INDEX idx_claims_security ON identifier_claims(security_id) WHERE security_id IS NOT NULL;
CREATE INDEX idx_claims_listing ON identifier_claims(listing_id) WHERE listing_id IS NOT NULL;

CREATE INDEX idx_aliases_text ON aliases(alias_text);
```

### Tier 2: DuckDB

Same schema as Tier 1, plus:
- Parquet export capability
- Analytical views
- Optional full-text search

### Tier 3: PostgreSQL (Full Production Schema)

See [Canonical Schema](#canonical-schema) below.

---

## Canonical Schema

### Full PostgreSQL DDL (Tier 3)

```sql
-- =============================================================================
-- EXTENSION SETUP
-- =============================================================================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For fuzzy matching

-- =============================================================================
-- SCHEME REGISTRY (What identifier types exist)
-- =============================================================================
CREATE TABLE scheme_registry (
    scheme_code         VARCHAR(20) PRIMARY KEY,
    display_name        VARCHAR(100) NOT NULL,
    scope               VARCHAR(20) NOT NULL,  -- 'entity', 'security', 'listing'
    issuing_authority   VARCHAR(100),
    validation_regex    VARCHAR(200),
    is_standard         BOOLEAN NOT NULL DEFAULT FALSE,  -- ISO/official vs vendor
    
    CONSTRAINT chk_scope CHECK (scope IN ('entity', 'security', 'listing'))
);

-- Seed standard schemes
INSERT INTO scheme_registry (scheme_code, display_name, scope, issuing_authority, validation_regex, is_standard) VALUES
    ('cik',     'SEC Central Index Key',    'entity',   'SEC',          '^\d{10}$',                 TRUE),
    ('lei',     'Legal Entity Identifier',  'entity',   'GLEIF',        '^[A-Z0-9]{20}$',           TRUE),
    ('ein',     'Employer ID Number',       'entity',   'IRS',          '^\d{9}$',                  TRUE),
    ('duns',    'DUNS Number',              'entity',   'D&B',          '^\d{9}$',                  TRUE),
    ('isin',    'International Securities ID', 'security', 'ISO 6166',  '^[A-Z]{2}[A-Z0-9]{9}\d$',  TRUE),
    ('cusip',   'CUSIP',                    'security', 'CUSIP Global', '^[A-Z0-9]{9}$',            TRUE),
    ('figi',    'Financial Instrument GID', 'security', 'OMG',          '^BBG[A-Z0-9]{9}$',         TRUE),
    ('sedol',   'SEDOL',                    'security', 'LSE',          '^[A-Z0-9]{7}$',            TRUE),
    ('ticker',  'Exchange Ticker Symbol',   'listing',  NULL,           NULL,                       TRUE),
    -- Vendor schemes (not standard, but first-class)
    ('bbgid',       'Bloomberg Global ID',      'entity',   'Bloomberg',    NULL, FALSE),
    ('bbuid',       'Bloomberg Unique ID',      'security', 'Bloomberg',    NULL, FALSE),
    ('factset_entity', 'FactSet Entity ID',     'entity',   'FactSet',      NULL, FALSE),
    ('factset_security', 'FactSet Security ID', 'security', 'FactSet',      NULL, FALSE),
    ('refinitiv_orgid', 'Refinitiv OrgID',      'entity',   'Refinitiv',    NULL, FALSE),
    ('ric',         'Reuters Instrument Code',  'listing',  'Refinitiv',    NULL, FALSE),
    ('spiq_company', 'S&P Capital IQ Company ID', 'entity', 'S&P',          NULL, FALSE),
    ('spiq_security', 'S&P Capital IQ Security ID', 'security', 'S&P',      NULL, FALSE);

-- =============================================================================
-- ENTITIES
-- =============================================================================
CREATE TABLE entities (
    entity_id               CHAR(26) PRIMARY KEY,  -- ULID
    
    entity_type             VARCHAR(30) NOT NULL DEFAULT 'COMPANY',
    status                  VARCHAR(20) NOT NULL DEFAULT 'active',
    confidence              DECIMAL(3,2) NOT NULL DEFAULT 1.0,
    
    legal_name              VARCHAR(500),
    primary_name            VARCHAR(500) NOT NULL,
    
    jurisdiction_country    CHAR(2),
    jurisdiction_subdiv     VARCHAR(10),
    formation_date          DATE,
    dissolution_date        DATE,
    
    sic_code                CHAR(4),
    naics_code              CHAR(6),
    is_public               BOOLEAN DEFAULT FALSE,
    
    source_system           VARCHAR(50) NOT NULL,
    source_id               VARCHAR(200),
    
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Merge support
    merged_into_id          CHAR(26) REFERENCES entities(entity_id),
    merged_at               TIMESTAMPTZ,
    merge_reason            TEXT,
    
    CONSTRAINT chk_entity_type CHECK (entity_type IN (
        'COMPANY', 'FUND', 'PERSON', 'GOVERNMENT', 'SPV', 
        'TRUST', 'PARTNERSHIP', 'UNKNOWN'
    )),
    CONSTRAINT chk_entity_status CHECK (status IN (
        'active', 'inactive', 'merged', 'provisional', 'disputed'
    ))
);

-- =============================================================================
-- SECURITIES
-- =============================================================================
CREATE TABLE securities (
    security_id             CHAR(26) PRIMARY KEY,
    issuer_entity_id        CHAR(26) NOT NULL REFERENCES entities(entity_id),
    
    security_type           VARCHAR(30) NOT NULL,
    name                    VARCHAR(500) NOT NULL,
    currency                CHAR(3),
    status                  VARCHAR(20) NOT NULL DEFAULT 'active',
    
    issue_date              DATE,
    maturity_date           DATE,
    share_class             VARCHAR(10),
    shares_outstanding      BIGINT,
    
    source_system           VARCHAR(50) NOT NULL,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Merge support
    merged_into_id          CHAR(26) REFERENCES securities(security_id),
    merged_at               TIMESTAMPTZ,
    
    CONSTRAINT chk_security_type CHECK (security_type IN (
        'common_stock', 'preferred_stock', 'adr', 'gdr',
        'corporate_bond', 'government_bond', 'municipal_bond',
        'warrant', 'option', 'fund_share', 'etf', 'convertible', 'other'
    ))
);

-- =============================================================================
-- LISTINGS
-- =============================================================================
CREATE TABLE listings (
    listing_id              CHAR(26) PRIMARY KEY,
    security_id             CHAR(26) NOT NULL REFERENCES securities(security_id),
    
    ticker                  VARCHAR(20) NOT NULL,
    mic                     CHAR(4) NOT NULL,
    currency                CHAR(3) NOT NULL,
    
    is_primary              BOOLEAN NOT NULL DEFAULT FALSE,
    status                  VARCHAR(20) NOT NULL DEFAULT 'active',
    
    valid_from              DATE NOT NULL,
    valid_to                DATE,
    
    lot_size                INT DEFAULT 1,
    
    source_system           VARCHAR(50) NOT NULL,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(ticker, mic, valid_from)
);

-- =============================================================================
-- IDENTIFIER CLAIMS (The heart of evidence-based identity)
-- =============================================================================
CREATE TABLE identifier_claims (
    claim_id                CHAR(26) PRIMARY KEY,  -- ULID
    
    -- Target (exactly one non-null via constraint)
    entity_id               CHAR(26) REFERENCES entities(entity_id),
    security_id             CHAR(26) REFERENCES securities(security_id),
    listing_id              CHAR(26) REFERENCES listings(listing_id),
    
    -- The identifier
    scheme                  VARCHAR(20) NOT NULL REFERENCES scheme_registry(scheme_code),
    value                   VARCHAR(100) NOT NULL,
    
    -- Claim provenance
    source_system           VARCHAR(50) NOT NULL,
    source_record_id        VARCHAR(200),          -- ID in source system
    confidence              DECIMAL(3,2) NOT NULL DEFAULT 1.0,
    captured_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Optional evidence pointer
    evidence_uri            VARCHAR(500),          -- file:///..., https://..., sec://...
    evidence_text           TEXT,
    
    -- Validity period of the claim
    valid_from              DATE,
    valid_to                DATE,
    
    -- Status
    status                  VARCHAR(20) NOT NULL DEFAULT 'active',
    superseded_by           CHAR(26) REFERENCES identifier_claims(claim_id),
    
    CONSTRAINT chk_single_target CHECK (
        (entity_id IS NOT NULL)::int +
        (security_id IS NOT NULL)::int +
        (listing_id IS NOT NULL)::int = 1
    ),
    CONSTRAINT chk_claim_status CHECK (status IN (
        'active', 'superseded', 'disputed', 'rejected'
    ))
);

-- Partial unique index: only one active claim per scheme+value at a time
CREATE UNIQUE INDEX idx_claims_active_unique 
    ON identifier_claims(scheme, value) 
    WHERE status = 'active' AND valid_to IS NULL;

-- =============================================================================
-- CLAIM CONFLICTS (When two claims disagree)
-- =============================================================================
CREATE TABLE claim_conflicts (
    conflict_id             CHAR(26) PRIMARY KEY,
    
    claim_a_id              CHAR(26) NOT NULL REFERENCES identifier_claims(claim_id),
    claim_b_id              CHAR(26) NOT NULL REFERENCES identifier_claims(claim_id),
    
    conflict_type           VARCHAR(30) NOT NULL,  -- 'same_id_diff_entity', 'same_entity_diff_id', etc.
    
    status                  VARCHAR(20) NOT NULL DEFAULT 'open',
    resolution              VARCHAR(30),           -- 'claim_a_wins', 'claim_b_wins', 'both_valid', 'merge'
    resolved_by             VARCHAR(100),
    resolved_at             TIMESTAMPTZ,
    resolution_notes        TEXT,
    
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT chk_conflict_status CHECK (status IN ('open', 'resolved', 'deferred'))
);

-- =============================================================================
-- MERGE EVENTS (Audit trail for merges)
-- =============================================================================
CREATE TABLE merge_events (
    merge_id                CHAR(26) PRIMARY KEY,
    
    -- What was merged
    source_type             VARCHAR(20) NOT NULL,  -- 'entity', 'security', 'listing'
    source_id               CHAR(26) NOT NULL,
    target_id               CHAR(26) NOT NULL,
    
    -- Why
    merge_reason            VARCHAR(100) NOT NULL,
    evidence_claims         CHAR(26)[],            -- Claim IDs that justified merge
    
    -- Who/when
    merged_by               VARCHAR(100),
    merged_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Reversibility
    is_reversible           BOOLEAN NOT NULL DEFAULT TRUE,
    reversed_at             TIMESTAMPTZ
);

-- =============================================================================
-- VENDOR CROSSWALKS (Explicit vendor ID mappings)
-- =============================================================================
CREATE TABLE vendor_crosswalks (
    crosswalk_id            CHAR(26) PRIMARY KEY,
    
    -- Our ID
    entity_id               CHAR(26) REFERENCES entities(entity_id),
    security_id             CHAR(26) REFERENCES securities(security_id),
    
    -- Vendor ID
    vendor                  VARCHAR(30) NOT NULL,  -- 'bloomberg', 'factset', 'refinitiv', 'spiq'
    vendor_id_type          VARCHAR(30) NOT NULL,  -- 'bbgid', 'factset_entity', etc.
    vendor_id_value         VARCHAR(100) NOT NULL,
    
    -- Provenance
    source_file             VARCHAR(500),
    captured_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    confidence              DECIMAL(3,2) NOT NULL DEFAULT 1.0,
    
    -- Validity
    valid_from              DATE,
    valid_to                DATE,
    
    UNIQUE(vendor, vendor_id_type, vendor_id_value, valid_from),
    
    CONSTRAINT chk_single_ref CHECK (
        (entity_id IS NOT NULL AND security_id IS NULL) OR
        (entity_id IS NULL AND security_id IS NOT NULL)
    )
);

-- =============================================================================
-- INDEXES
-- =============================================================================
CREATE INDEX idx_entities_status ON entities(status);
CREATE INDEX idx_entities_name_trgm ON entities USING GIN(primary_name gin_trgm_ops);
CREATE INDEX idx_entities_merged ON entities(merged_into_id) WHERE merged_into_id IS NOT NULL;

CREATE INDEX idx_securities_issuer ON securities(issuer_entity_id);
CREATE INDEX idx_securities_type ON securities(security_type);

CREATE INDEX idx_listings_ticker ON listings(ticker);
CREATE INDEX idx_listings_security ON listings(security_id);
CREATE INDEX idx_listings_valid ON listings(valid_from, valid_to);

CREATE INDEX idx_claims_scheme_value ON identifier_claims(scheme, value);
CREATE INDEX idx_claims_entity ON identifier_claims(entity_id) WHERE entity_id IS NOT NULL;
CREATE INDEX idx_claims_status ON identifier_claims(status);

CREATE INDEX idx_crosswalks_vendor ON vendor_crosswalks(vendor, vendor_id_value);
CREATE INDEX idx_crosswalks_entity ON vendor_crosswalks(entity_id) WHERE entity_id IS NOT NULL;
```

---

## Claims & Evidence Model

### Claim Lifecycle

```
                    ┌─────────────┐
                    │   Captured  │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
        ┌──────────│   active    │──────────┐
        │          └──────┬──────┘          │
        │                 │                 │
        ▼                 ▼                 ▼
┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│  superseded │   │  disputed   │   │  rejected   │
└─────────────┘   └──────┬──────┘   └─────────────┘
                         │
                         ▼
                  ┌─────────────┐
                  │  resolved   │
                  └─────────────┘
```

### Conflict Detection

```python
def detect_conflicts(new_claim: IdentifierClaim) -> list[ClaimConflict]:
    """Find existing claims that conflict with new claim."""
    conflicts = []
    
    # Type 1: Same identifier claimed by different entities
    existing = get_active_claims(scheme=new_claim.scheme, value=new_claim.value)
    for e in existing:
        if e.target_id != new_claim.target_id:
            conflicts.append(ClaimConflict(
                claim_a=new_claim,
                claim_b=e,
                conflict_type='same_id_different_target'
            ))
    
    # Type 2: Same entity has conflicting identifiers (e.g., two CIKs)
    if new_claim.scheme in UNIQUE_PER_ENTITY_SCHEMES:
        existing = get_active_claims(
            target_id=new_claim.target_id, 
            scheme=new_claim.scheme
        )
        for e in existing:
            if e.value != new_claim.value:
                conflicts.append(ClaimConflict(
                    claim_a=new_claim,
                    claim_b=e,
                    conflict_type='multiple_ids_same_scheme'
                ))
    
    return conflicts
```

### Evidence Pointers

Claims can point to evidence via URI:

| URI Scheme | Example | Meaning |
|------------|---------|---------|
| `sec://` | `sec://0000320193-24-000081/10-K` | SEC filing |
| `gleif://` | `gleif://HWUPKR0MPOU8FGXBT394` | GLEIF LEI record |
| `file://` | `file:///data/crosswalks/bloomberg_2024.csv:row=1234` | Local file |
| `https://` | `https://openfigi.com/api/v3/mapping/...` | External API |

---

## Scheme Registry

### Standard vs Vendor Schemes

```
┌────────────────────────────────────────────────────────────────────────┐
│                        SCHEME CATEGORIES                                │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  STANDARD (ISO, Official Bodies)           VENDOR (Commercial)         │
│  ════════════════════════════════          ════════════════════════    │
│                                                                        │
│  Entity:                                   Entity:                     │
│    • CIK (SEC)                               • BBGID (Bloomberg)       │
│    • LEI (GLEIF)                             • FactSet Entity ID       │
│    • EIN (IRS)                               • Refinitiv OrgID         │
│    • DUNS (D&B)                              • S&P Capital IQ ID       │
│                                                                        │
│  Security:                                 Security:                   │
│    • ISIN (ISO 6166)                         • BBUID (Bloomberg)       │
│    • CUSIP (CUSIP Global)                    • FactSet Security ID     │
│    • FIGI (OMG/Bloomberg)                    • S&P Security ID         │
│    • SEDOL (LSE)                                                       │
│                                                                        │
│  Listing:                                  Listing:                    │
│    • Ticker + MIC                            • RIC (Reuters)           │
│                                              • BBG Ticker              │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

### Scheme Scope Enforcement

```python
SCHEME_SCOPES = {
    # Entity-scoped (attach to entities table)
    'cik': 'entity', 'lei': 'entity', 'ein': 'entity', 'duns': 'entity',
    'bbgid': 'entity', 'factset_entity': 'entity', 'refinitiv_orgid': 'entity',
    
    # Security-scoped (attach to securities table)
    'isin': 'security', 'cusip': 'security', 'figi': 'security', 'sedol': 'security',
    'bbuid': 'security', 'factset_security': 'security',
    
    # Listing-scoped (attach to listings table)
    'ticker': 'listing', 'ric': 'listing',
}

def validate_claim_scope(claim: IdentifierClaim) -> bool:
    """Ensure claim attaches identifier to correct object type."""
    expected_scope = SCHEME_SCOPES.get(claim.scheme)
    if expected_scope == 'entity':
        return claim.entity_id is not None
    elif expected_scope == 'security':
        return claim.security_id is not None
    elif expected_scope == 'listing':
        return claim.listing_id is not None
    return True  # Unknown scheme, allow flexibility
```

---

## Merge & Redirect System

### Merge Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           MERGE WORKFLOW                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  1. Merge Proposal                                                      │
│     ─────────────────                                                   │
│     • Source entity: E1 (to be merged away)                            │
│     • Target entity: E2 (canonical survivor)                           │
│     • Evidence: claims that justify merge                              │
│                                                                         │
│  2. Validation                                                          │
│     ────────────────                                                    │
│     • Check E1 and E2 are same entity_type                             │
│     • Check no circular merges                                         │
│     • Check evidence is sufficient                                     │
│                                                                         │
│  3. Execute Merge                                                       │
│     ─────────────────                                                   │
│     • E1.status = 'merged'                                             │
│     • E1.merged_into_id = E2.entity_id                                 │
│     • E1.merged_at = NOW()                                             │
│     • Transfer securities: UPDATE securities SET issuer_entity_id = E2 │
│       WHERE issuer_entity_id = E1                                      │
│     • Transfer claims: Keep pointing to E1 (for audit)                 │
│     • Create merge_event record                                        │
│                                                                         │
│  4. Resolution Follows Redirects                                        │
│     ──────────────────────────────                                      │
│     • resolve(CIK of E1) → follows merged_into_id → returns E2         │
│     • Response includes redirect_chain for transparency                │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Redirect Resolution

```python
def follow_redirects(entity_id: str, max_depth: int = 10) -> tuple[str, list[str]]:
    """Follow merge chain to canonical entity.
    
    Returns:
        (canonical_id, redirect_chain)
    """
    chain = [entity_id]
    current = entity_id
    
    for _ in range(max_depth):
        entity = get_entity(current)
        if entity.merged_into_id is None:
            break
        current = entity.merged_into_id
        chain.append(current)
    
    return current, chain
```

---

## Derived Views

### Entity With Primary Listing (Convenience View)

```sql
-- This is a DERIVED VIEW, not canonical truth
-- It flattens Entity → Security → Listing for convenience

CREATE VIEW entity_primary_listing AS
SELECT 
    e.entity_id,
    e.entity_type,
    e.status AS entity_status,
    e.primary_name,
    e.legal_name,
    e.sic_code,
    
    -- Primary security (if any)
    s.security_id,
    s.security_type,
    s.name AS security_name,
    
    -- Primary listing (if any)
    l.listing_id,
    l.ticker AS primary_ticker,
    l.mic AS primary_exchange,
    l.valid_from AS ticker_valid_from,
    l.valid_to AS ticker_valid_to,
    
    -- CIK from claims (if any)
    cik_claim.value AS cik,
    
    -- Derivation metadata
    CURRENT_DATE AS as_of_date,
    'derived' AS view_type
    
FROM entities e

-- Join to primary security
LEFT JOIN securities s ON s.issuer_entity_id = e.entity_id
    AND s.security_type = 'common_stock'
    AND s.status = 'active'

-- Join to primary listing
LEFT JOIN listings l ON l.security_id = s.security_id
    AND l.is_primary = TRUE
    AND l.status = 'active'
    AND (l.valid_to IS NULL OR l.valid_to > CURRENT_DATE)

-- Join to CIK claim
LEFT JOIN identifier_claims cik_claim ON cik_claim.entity_id = e.entity_id
    AND cik_claim.scheme = 'cik'
    AND cik_claim.status = 'active'

WHERE e.status IN ('active', 'provisional')
  AND e.merged_into_id IS NULL;
```

### Point-in-Time Resolution View

```sql
-- Resolve ticker as of specific date
CREATE FUNCTION resolve_ticker_as_of(
    p_ticker VARCHAR(20),
    p_mic VARCHAR(4),
    p_as_of DATE DEFAULT CURRENT_DATE
) RETURNS TABLE (
    entity_id CHAR(26),
    security_id CHAR(26),
    listing_id CHAR(26),
    entity_name VARCHAR(500),
    confidence DECIMAL(3,2)
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        e.entity_id,
        s.security_id,
        l.listing_id,
        e.primary_name,
        1.0::DECIMAL(3,2) AS confidence
    FROM listings l
    JOIN securities s ON s.security_id = l.security_id
    JOIN entities e ON e.entity_id = s.issuer_entity_id
    WHERE l.ticker = p_ticker
      AND (p_mic IS NULL OR l.mic = p_mic)
      AND l.valid_from <= p_as_of
      AND (l.valid_to IS NULL OR l.valid_to > p_as_of)
      AND l.status = 'active'
      AND s.status = 'active'
      AND e.status IN ('active', 'provisional')
    ORDER BY l.is_primary DESC, l.valid_from DESC
    LIMIT 5;  -- Return top candidates
END;
$$ LANGUAGE plpgsql;
```

---

## Decision Log

| # | Decision | Rationale | Alternative Considered |
|---|----------|-----------|----------------------|
| 1 | Ticker on Listing, never Entity | Entity ≠ Security ≠ Listing rule | Flat model (rejected: violates scope) |
| 2 | All identifiers as claims | Auditability, conflict handling | Direct columns (rejected: no provenance) |
| 3 | Return ranked candidates | Ambiguity is normal in real data | Single result (rejected: hides uncertainty) |
| 4 | Merges create redirects | Old IDs must stay resolvable | Delete merged (rejected: breaks references) |
| 5 | Vendor IDs first-class | Real integrations need Bloomberg, FactSet | Ignore vendors (rejected: impractical) |
| 6 | Tier 1 has full E/S/L schema | Consistency across tiers | SimpleEntity (rejected: scope leakage) |
| 7 | Derived views clearly marked | Prevent canonical confusion | Denormalize core (rejected: data integrity) |
| 8 | Scheme registry table | Extensible, validates scope | Hardcoded enum (rejected: inflexible) |
| 9 | EntityType broad, relationships for nuance | Avoid type explosion | Subsidiary entity type (rejected: use edge) |
| 10 | Person = Entity with type PERSON | Consistent identity model | Separate person table (rejected: duplication) |

---

## People and Knowledge Graph Extensions (v2.2.3)

### People as Entities

People are modeled as `Entity` with `entity_type = PERSON`:

```python
person = Entity(
    primary_name="John Smith",
    entity_type=EntityType.PERSON,
    source_system="sec_form4",
)
```

**Key Points:**
- CIK can be claimed against PERSON entities (for insiders/filers)
- People are identified by roles + context, not stable IDs
- Person matching is conservative in Tier 0-1 (exact name only)

### Role Assignments

Represents time-bounded roles: Person → Organization

```python
@dataclass
class RoleAssignment:
    person_entity_id: str     # FK to Person Entity
    org_entity_id: str        # FK to Org Entity
    role_type: RoleType       # CEO, CFO, DIRECTOR, etc.
    title: Optional[str]      # Exact title string
    start_date: Optional[date]
    end_date: Optional[date]
    confidence: float
    filing_id: Optional[str]  # Evidence pointer
```

### Entity Relationships

Typed edges between entities:

```python
@dataclass
class EntityRelationship:
    from_entity_id: str
    to_entity_id: str
    relationship_type: RelationshipType  # SUBSIDIARY, AFFILIATE, etc.
    valid_from: Optional[date]
    valid_to: Optional[date]
    confidence: float
    evidence_text: Optional[str]
```

### Addresses

Normalized addresses with hash-based matching:

```python
@dataclass
class Address:
    line1: Optional[str]
    city: Optional[str]
    region: Optional[str]
    postal: Optional[str]
    country: str = "US"
    normalized_hash: Optional[str]  # For dedup matching
```

### Geographic Nodes (Geo)

```python
@dataclass
class Geo:
    name: str
    geo_type: GeoType  # COUNTRY, STATE, CITY
    iso_code: Optional[str]  # ISO 3166-1/2
    parent_geo_id: Optional[str]
```

### Cases/Proceedings

Legal proceedings, investigations, enforcement actions:

```python
@dataclass
class Case:
    case_type: CaseType  # LAWSUIT, INVESTIGATION, ENFORCEMENT
    title: str
    status: CaseStatus
    authority_entity_id: Optional[str]  # Court/regulator
    target_entity_id: Optional[str]
    opened_date: Optional[date]
    closed_date: Optional[date]
```

### Expanded EntityType Enum

```python
class EntityType(str, Enum):
    ORGANIZATION = "organization"
    PERSON = "person"
    GOVERNMENT = "government"
    FUND = "fund"
    TRUST = "trust"
    PARTNERSHIP = "partnership"
    SPV = "spv"
    EXCHANGE = "exchange"
    GEO = "geo"
    UNKNOWN = "unknown"
```

**Important**: "Subsidiary" is NOT an entity type. Use `RelationshipType.SUBSIDIARY` edge.

### SQLite Schema (Tier 1)

```sql
-- Role assignments
CREATE TABLE role_assignments (
    role_assignment_id TEXT PRIMARY KEY,
    person_entity_id TEXT NOT NULL REFERENCES entities(entity_id),
    org_entity_id TEXT NOT NULL REFERENCES entities(entity_id),
    role_type TEXT NOT NULL,
    title TEXT,
    start_date TEXT,
    end_date TEXT,
    confidence REAL DEFAULT 1.0,
    filing_id TEXT,
    ...
);

-- Entity relationships
CREATE TABLE entity_relationships (
    relationship_id TEXT PRIMARY KEY,
    from_entity_id TEXT NOT NULL REFERENCES entities(entity_id),
    to_entity_id TEXT NOT NULL REFERENCES entities(entity_id),
    relationship_type TEXT NOT NULL,
    valid_from TEXT,
    valid_to TEXT,
    confidence REAL DEFAULT 1.0,
    evidence_text TEXT,
    ...
);

-- Cases
CREATE TABLE cases (
    case_id TEXT PRIMARY KEY,
    case_type TEXT NOT NULL,
    title TEXT NOT NULL,
    status TEXT DEFAULT 'unknown',
    authority_entity_id TEXT REFERENCES entities(entity_id),
    target_entity_id TEXT REFERENCES entities(entity_id),
    ...
);
```

See `KG_FULL_CONCEPTS.md` for complete documentation.

---

## High-Confidence Knowledge Graph Nodes (v2.2.4)

v2.2.4 adds six additional KG node types that have high extraction confidence from SEC filings:

### Node Types Summary

| NodeKind | Purpose | Key Identifiers | Source Filings |
|----------|---------|-----------------|----------------|
| **ASSET** | Physical/tangible assets | asset_id | 10-K, 10-Q |
| **CONTRACT** | Legal agreements | contract_id | 8-K, 10-K |
| **PRODUCT** | Products/services | product_id | 10-K, 10-Q |
| **BRAND** | Brand identities | brand_id | 10-K |
| **REGULATOR** | Regulatory bodies | entity_id | 8-K, 10-K |
| **EVENT** | Material events | event_id | 8-K, 10-K |

### Asset Model

Represents physical assets, facilities, equipment owned/operated by entities:

```python
@dataclass
class Asset:
    asset_id: str = field(default_factory=ulid_now)
    asset_type: AssetType = AssetType.OTHER
    name: str = ""
    owner_entity_id: Optional[str] = None
    geo_id: Optional[str] = None
    address_id: Optional[str] = None
    status: AssetStatus = AssetStatus.ACTIVE
    
class AssetType(str, Enum):
    FACILITY = "facility"       # Manufacturing, offices
    DATA_CENTER = "data_center"
    VESSEL = "vessel"           # Ships
    AIRCRAFT = "aircraft"       # Planes
    PLANT = "plant"             # Industrial plant
    PROPERTY = "property"       # Real estate
    EQUIPMENT = "equipment"
    VEHICLE = "vehicle"
    INVENTORY = "inventory"
    IP = "ip"                   # Intellectual property
    OTHER = "other"
```

**Relationship Types:**
- `OWNS_ASSET` - Entity owns asset
- `OPERATES_ASSET` - Entity operates asset
- `LEASES_ASSET` - Entity leases asset

### Contract Model

Represents material agreements disclosed in filings:

```python
@dataclass
class Contract:
    contract_id: str = field(default_factory=ulid_now)
    contract_type: ContractType = ContractType.OTHER
    title: str = ""
    effective_date: Optional[date] = None
    termination_date: Optional[date] = None
    value_usd: Optional[Decimal] = None
    status: ContractStatus = ContractStatus.ACTIVE
    
class ContractType(str, Enum):
    CREDIT_FACILITY = "credit_facility"
    LEASE = "lease"
    MATERIAL_AGREEMENT = "material_agreement"
    SUPPLY = "supply"
    LICENSE = "license"
    EMPLOYMENT = "employment"
    MERGER = "merger"
    JOINT_VENTURE = "joint_venture"
    SERVICE = "service"
    DISTRIBUTION = "distribution"
    SETTLEMENT = "settlement"
    OTHER = "other"
```

**Relationship Types:**
- `PARTY_TO` - Entity is party to contract
- `COUNTERPARTY_TO` - Entity is counterparty to contract
- `GOVERNS` - Contract governs relationship

### Product Model

Products and services disclosed in filings:

```python
@dataclass
class Product:
    product_id: str = field(default_factory=ulid_now)
    product_type: ProductType = ProductType.OTHER
    name: str = ""
    owner_entity_id: Optional[str] = None
    status: ProductStatus = ProductStatus.ACTIVE
    
class ProductType(str, Enum):
    DRUG = "drug"
    DEVICE = "device"
    SOFTWARE = "software"
    SERVICE = "service"
    CONSUMER_GOOD = "consumer_good"
    INDUSTRIAL = "industrial"
    FINANCIAL = "financial"
    FOOD_BEVERAGE = "food_beverage"
    VEHICLE = "vehicle"
    OTHER = "other"
```

**Relationship Types:**
- `MANUFACTURES` - Entity manufactures product
- `SELLS` - Entity sells product
- `DISTRIBUTES` - Entity distributes product
- `LICENSES_PRODUCT` - Entity licenses product
- `DEVELOPS` - Entity develops product

### Brand Model

Brand identities (distinct from products):

```python
@dataclass
class Brand:
    brand_id: str = field(default_factory=ulid_now)
    name: str = ""
    owner_entity_id: Optional[str] = None
```

**Relationship Types:**
- `OWNS_BRAND` - Entity owns brand
- `LICENSES_BRAND` - Entity licenses brand
- `BRAND_OF` - Brand belongs to product

### Event Model

Material events disclosed in filings (M&A, legal, cyber, etc.):

```python
@dataclass
class Event:
    event_id: str = field(default_factory=ulid_now)
    event_type: EventType = EventType.OTHER
    title: str = ""
    occurred_on: Optional[date] = None
    announced_on: Optional[date] = None
    status: EventStatus = EventStatus.ANNOUNCED
    payload: Optional[dict] = None
    evidence_filing_id: Optional[str] = None
    evidence_snippet: Optional[str] = None
    confidence: float = 1.0
    
class EventType(str, Enum):
    # M&A/Strategic
    MERGER_ACQUISITION = "m&a"
    DIVESTITURE = "divestiture"
    RESTRUCTURING = "restructuring"
    BANKRUPTCY = "bankruptcy"
    # Legal/Regulatory
    LEGAL = "legal"
    REGULATORY = "regulatory"
    INVESTIGATION = "investigation"
    ENFORCEMENT = "enforcement"
    # Cyber/Security
    DATA_BREACH = "data_breach"
    CYBER = "cyber"
    OPERATIONAL = "operational"
    # Financial
    FINANCIAL = "financial"
    CAPITAL = "capital"
    DIVIDEND = "dividend"
    # Leadership
    MANAGEMENT = "mgmt"
    BOARD = "board"
    # Product
    PRODUCT_LAUNCH = "product_launch"
    PRODUCT_RECALL = "product_recall"
    OTHER = "other"
```

**Relationship Types:**
- `SUBJECT_OF` - Entity is subject of event
- `INVOLVED_IN` - Entity is involved in event
- `TRIGGERED_BY` - Event triggered by other event
- `RESULTED_IN` - Event resulted in other event
- `ANNOUNCED_BY` - Event announced by entity

### SQLite Schema (Tier 1)

```sql
-- Assets
CREATE TABLE assets (
    asset_id TEXT PRIMARY KEY,
    asset_type TEXT NOT NULL,
    name TEXT NOT NULL,
    owner_entity_id TEXT REFERENCES entities(entity_id),
    geo_id TEXT,
    address_id TEXT,
    status TEXT DEFAULT 'active',
    source_filing_id TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_assets_type ON assets(asset_type);
CREATE INDEX idx_assets_owner ON assets(owner_entity_id);

-- Contracts
CREATE TABLE contracts (
    contract_id TEXT PRIMARY KEY,
    contract_type TEXT NOT NULL,
    title TEXT NOT NULL,
    effective_date TEXT,
    termination_date TEXT,
    value_usd TEXT,
    status TEXT DEFAULT 'active',
    source_filing_id TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_contracts_type ON contracts(contract_type);
CREATE INDEX idx_contracts_status ON contracts(status);

-- Products
CREATE TABLE products (
    product_id TEXT PRIMARY KEY,
    product_type TEXT NOT NULL,
    name TEXT NOT NULL,
    owner_entity_id TEXT REFERENCES entities(entity_id),
    status TEXT DEFAULT 'active',
    source_filing_id TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_products_type ON products(product_type);
CREATE INDEX idx_products_owner ON products(owner_entity_id);

-- Brands
CREATE TABLE brands (
    brand_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    owner_entity_id TEXT REFERENCES entities(entity_id),
    source_filing_id TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_brands_name ON brands(name);
CREATE INDEX idx_brands_owner ON brands(owner_entity_id);

-- Events (kg_events to avoid collision with py-sec-edgar events)
CREATE TABLE kg_events (
    event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    title TEXT NOT NULL,
    occurred_on TEXT,
    announced_on TEXT,
    status TEXT DEFAULT 'announced',
    payload TEXT,  -- JSON
    evidence_filing_id TEXT,
    evidence_section_id TEXT,
    evidence_snippet TEXT,
    confidence REAL DEFAULT 1.0,
    source_filing_id TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_kg_events_type ON kg_events(event_type);
CREATE INDEX idx_kg_events_status ON kg_events(status);
```

### Architecture Guardrails

**INVIOLABLE RULES (v2.2.4):**

1. **ONE canonical definition per model**: All domain models live in `entityspine.domain.*` as stdlib dataclasses.
2. **NO competing implementations**: Pydantic/SQLModel wrappers in `adapters/` must delegate to domain, never duplicate.
3. **Zero-dependency core**: `pip install entityspine` requires nothing. Optional deps via extras.
4. **Stores return domain**: All store methods return `entityspine.domain.*` dataclasses, never ORM/Pydantic models.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    ARCHITECTURE RULE: NO COMPETING MODELS                   │
│                                                                             │
│  ✓ entityspine.domain.Entity (stdlib dataclass) - THE ONE TRUE DEFINITION   │
│  ✓ entityspine.adapters.pydantic.Entity (wrapper) - calls domain            │
│  ✓ entityspine.adapters.orm.EntityModel (table) - converts to/from domain   │
│                                                                             │
│  ✗ entityspine.models.Entity - DELETED (was duplicate)                      │
│  ✗ entityspine.db.EntityTable - DELETED (was duplicate)                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Known Open Questions

| # | Question | Impact | Notes |
|---|----------|--------|-------|
| 1 | How to handle securities without known issuer? | Orphan securities | May need "unknown issuer" entity |
| 2 | Should confidence scores be calibrated across sources? | Scoring consistency | 1.0 from SEC vs 0.9 from scrape |
| 3 | How to handle ticker without MIC (unknown exchange)? | Listing creation | Allow NULL MIC? Use "XXXX" placeholder? |
| 4 | Retention policy for superseded claims? | Storage growth | Keep forever? Archive after N years? |
| 5 | Cross-tier sync strategy? | Multi-tier deployments | If Tier 3 exists, how does Tier 1 sync? |

---

## Appendix: Migration from v2.1

See `03_MIGRATION_NOTES.md` for detailed migration steps.

**Breaking Changes Summary**:
1. `SimpleEntity.ticker` removed - use `primary_listing` view
2. SQLite `entities.ticker` column removed
3. `identifiers` table replaced by `identifier_claims`
4. `resolve()` returns `list[ResolutionCandidate]` not `Entity | None`

---

*Version 2.2 | January 2026*
