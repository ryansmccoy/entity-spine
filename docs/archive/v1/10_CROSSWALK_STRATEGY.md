# Entity Master - Crosswalk Strategy

**How to map vendor identifiers (Bloomberg, FactSet, Refinitiv, S&P, OpenFIGI) into the canonical model.**

---

## The Crosswalk Problem

Every financial data vendor has their own identifier system:

| Vendor | Entity IDs | Security IDs | Listing IDs |
|--------|-----------|--------------|-------------|
| **Bloomberg** | Company ID (internal) | FIGI, BUID, BSID | BBG Ticker, BBID |
| **FactSet** | Entity ID | Security ID | Listing ID |
| **Refinitiv** | PermID (Entity) | PermID (Quote) | RIC |
| **S&P** | GVKEY | IID (Issue ID) | — |
| **LSEG/ICE** | — | SEDOL | — |
| **DTCC** | — | CUSIP | — |
| **ISO** | — | ISIN | — |
| **SEC** | CIK | — | — |
| **GLEIF** | LEI | — | — |

**The challenge:** Map between these systems while:
- Preserving correct scope (entity vs security vs listing)
- Tracking provenance (where did mapping come from?)
- Handling conflicts (vendors disagree)
- Supporting temporal validity (mappings change over time)

---

## Identifier Scope Matrix

### Entity-Scoped Identifiers

These identify the **legal organization**, not its securities.

| Scheme | Source | Format | Notes |
|--------|--------|--------|-------|
| `cik` | SEC | 10-digit padded | SEC filers only |
| `lei` | GLEIF | 20-char alphanumeric | ISO 17442 |
| `duns` | D&B | 9-digit | Any business globally |
| `ein` | IRS | XX-XXXXXXX | US tax ID |
| `permid_entity` | Refinitiv | Numeric | PermID for organizations |
| `factset_entity` | FactSet | Alphanumeric | FactSet entity ID |
| `sp_gvkey` | S&P | 6-digit | S&P company key |
| `bbg_company` | Bloomberg | Alphanumeric | Bloomberg company ID |

### Security-Scoped Identifiers

These identify the **financial instrument**.

| Scheme | Source | Format | Notes |
|--------|--------|--------|-------|
| `isin` | ISO/NNAs | 12-char | CC + NSIN + check digit |
| `cusip` | CUSIP Global | 9-char | US/Canada securities |
| `sedol` | LSE | 7-char | UK/Ireland securities |
| `figi` | Bloomberg | BBG + 8 chars | OpenFIGI security |
| `composite_figi` | Bloomberg | BBG + 8 chars | Country-level FIGI |
| `share_class_figi` | Bloomberg | BBG + 8 chars | Share class FIGI |
| `permid_quote` | Refinitiv | Numeric | PermID for instruments |
| `factset_sec` | FactSet | Alphanumeric | FactSet security ID |
| `sp_iid` | S&P | Numeric | S&P issue ID |

### Listing-Scoped Identifiers

These identify the **traded quote on an exchange**.

| Scheme | Source | Format | Notes |
|--------|--------|--------|-------|
| `ticker` | Exchange | Variable | Exchange-specific |
| `exchange_figi` | Bloomberg | BBG + 8 chars | Exchange-specific FIGI |
| `ric` | Refinitiv | Variable | Reuters Instrument Code |
| `bbg_ticker` | Bloomberg | Symbol + suffix | e.g., AAPL US Equity |
| `factset_listing` | FactSet | Alphanumeric | FactSet listing ID |

---

## Vendor-Specific Mapping Rules

### Bloomberg

Bloomberg has multiple ID types that map to different scopes:

```
Bloomberg ID Hierarchy:
┌─────────────────────────────────────────────────────────────────────────────┐
│  BBG Company ID (internal)                                                   │
│      → Entity scope                                                          │
│      → Not publicly exposed; use FIGI instead                                │
│                                                                              │
│  FIGI (Global Financial Instrument Global Identifier)                        │
│      → Security scope (primary)                                              │
│      → From OpenFIGI API                                                     │
│      → Types: FIGI, Composite FIGI, Share Class FIGI                         │
│                                                                              │
│  BUID (Bloomberg Unique ID)                                                  │
│      → Security/Listing scope                                                │
│      → Internal Bloomberg ID                                                 │
│                                                                              │
│  BSID (Bloomberg Security ID)                                                │
│      → Security scope                                                        │
│      → Older ID format                                                       │
│                                                                              │
│  BBID (Bloomberg ID)                                                         │
│      → Listing scope                                                         │
│      → Exchange-specific                                                     │
│                                                                              │
│  BBG Ticker (e.g., "AAPL US Equity")                                        │
│      → Listing scope                                                         │
│      → Symbol + exchange suffix + security type                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Mapping strategy:**
```python
def map_bloomberg_id(bbg_id: str, id_type: str) -> IdentifierMapping:
    """Map Bloomberg ID to canonical scope."""
    
    scope_map = {
        'FIGI': IdentifierScope.SECURITY,
        'COMPOSITE_FIGI': IdentifierScope.SECURITY,
        'SHARE_CLASS_FIGI': IdentifierScope.SECURITY,
        'BUID': IdentifierScope.SECURITY,  # Usually security, can be listing
        'BSID': IdentifierScope.SECURITY,
        'BBID': IdentifierScope.LISTING,
        'BBG_TICKER': IdentifierScope.LISTING,
    }
    
    return IdentifierMapping(
        scheme=f'bbg_{id_type.lower()}',
        value=bbg_id,
        scope=scope_map.get(id_type, IdentifierScope.UNKNOWN),
        vendor='bloomberg',
        vendor_id_type=id_type,
    )
```

### FactSet

FactSet has a clean hierarchical ID structure:

```
FactSet ID Hierarchy:
┌─────────────────────────────────────────────────────────────────────────────┐
│  Entity ID (e.g., "000C7F-E")                                               │
│      → Entity scope                                                          │
│      → One per company/fund/person                                           │
│                                                                              │
│  Security ID (e.g., "000C7F-S-US")                                          │
│      → Security scope                                                        │
│      → Entity ID + security suffix                                           │
│                                                                              │
│  Regional ID (e.g., "000C7F-R-US")                                          │
│      → Regional security scope                                               │
│      → Composite of listings                                                 │
│                                                                              │
│  Listing ID (e.g., "000C7F-L-NYS-USD")                                      │
│      → Listing scope                                                         │
│      → Entity + exchange + currency                                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Mapping strategy:**
```python
def map_factset_id(fs_id: str) -> IdentifierMapping:
    """Map FactSet ID to canonical scope based on suffix."""
    
    if '-E' in fs_id or fs_id.count('-') == 0:
        scope = IdentifierScope.ENTITY
        scheme = 'factset_entity'
    elif '-S-' in fs_id:
        scope = IdentifierScope.SECURITY
        scheme = 'factset_sec'
    elif '-R-' in fs_id:
        scope = IdentifierScope.SECURITY  # Regional = security composite
        scheme = 'factset_regional'
    elif '-L-' in fs_id:
        scope = IdentifierScope.LISTING
        scheme = 'factset_listing'
    else:
        scope = IdentifierScope.UNKNOWN
        scheme = 'factset_unknown'
    
    return IdentifierMapping(
        scheme=scheme,
        value=fs_id,
        scope=scope,
        vendor='factset',
    )
```

### Refinitiv (LSEG)

Refinitiv uses PermID and RIC:

```
Refinitiv ID Hierarchy:
┌─────────────────────────────────────────────────────────────────────────────┐
│  PermID (Organization) - e.g., "4295903307"                                 │
│      → Entity scope                                                          │
│      → Permanent identifier for legal entities                               │
│      → Available from Open PermID API                                        │
│                                                                              │
│  PermID (Quote) - e.g., "55838587890"                                       │
│      → Security/Listing scope                                                │
│      → Identifies tradeable instruments                                      │
│                                                                              │
│  RIC (Reuters Instrument Code) - e.g., "AAPL.O"                             │
│      → Listing scope                                                         │
│      → Symbol + exchange suffix                                              │
│      → Can change (not permanent)                                            │
│                                                                              │
│  ISIN, CUSIP, SEDOL                                                         │
│      → Refinitiv redistributes standard IDs                                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Mapping strategy:**
```python
def map_refinitiv_id(ref_id: str, id_type: str) -> IdentifierMapping:
    """Map Refinitiv ID to canonical scope."""
    
    if id_type == 'PERMID_ORG':
        return IdentifierMapping(
            scheme='permid_entity',
            value=ref_id,
            scope=IdentifierScope.ENTITY,
            vendor='refinitiv',
        )
    elif id_type == 'PERMID_QUOTE':
        return IdentifierMapping(
            scheme='permid_quote',
            value=ref_id,
            scope=IdentifierScope.SECURITY,  # Or LISTING depending on context
            vendor='refinitiv',
        )
    elif id_type == 'RIC':
        return IdentifierMapping(
            scheme='ric',
            value=ref_id,
            scope=IdentifierScope.LISTING,
            vendor='refinitiv',
        )
```

### S&P Global

S&P uses GVKEY for companies and IID for issues:

```
S&P ID Hierarchy:
┌─────────────────────────────────────────────────────────────────────────────┐
│  GVKEY (Global Company Key) - e.g., "001690"                                │
│      → Entity scope                                                          │
│      → 6-digit identifier                                                    │
│      → Core to Compustat                                                     │
│                                                                              │
│  IID (Issue ID) - e.g., "01"                                                │
│      → Security scope (relative to GVKEY)                                    │
│      → GVKEY + IID uniquely identifies security                              │
│                                                                              │
│  GVKEY-IID combo - e.g., "001690-01"                                        │
│      → Security scope (absolute)                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### OpenFIGI

OpenFIGI specifically returns **security and listing level** identifiers:

```
OpenFIGI Response Structure:
┌─────────────────────────────────────────────────────────────────────────────┐
│  Query: ticker=AAPL, exchCode=US                                            │
│                                                                              │
│  Response:                                                                   │
│  {                                                                           │
│    "figi": "BBG000B9XRY4",               ← Security-level FIGI              │
│    "compositeFIGI": "BBG000B9XRY4",      ← Country-level (same for US)      │
│    "shareClassFIGI": "BBG001S5N8V8",     ← Share class FIGI                 │
│    "securityType": "Common Stock",                                           │
│    "marketSector": "Equity",                                                 │
│    "ticker": "AAPL",                                                         │
│    "name": "APPLE INC",                                                      │
│    "exchCode": "US",                                                         │
│  }                                                                           │
│                                                                              │
│  NOTE: There is NO "issuer FIGI" - FIGI does not identify companies!        │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Correct mapping:**
```python
def map_openfigi_response(response: dict) -> list[IdentifierMapping]:
    """Map OpenFIGI response to canonical identifiers."""
    
    mappings = []
    
    # Security-level FIGI
    if response.get('figi'):
        mappings.append(IdentifierMapping(
            scheme='figi',
            value=response['figi'],
            scope=IdentifierScope.SECURITY,
            vendor='openfigi',
        ))
    
    # Composite FIGI (also security-level, country aggregation)
    if response.get('compositeFIGI'):
        mappings.append(IdentifierMapping(
            scheme='composite_figi',
            value=response['compositeFIGI'],
            scope=IdentifierScope.SECURITY,
            vendor='openfigi',
        ))
    
    # Share class FIGI
    if response.get('shareClassFIGI'):
        mappings.append(IdentifierMapping(
            scheme='share_class_figi',
            value=response['shareClassFIGI'],
            scope=IdentifierScope.SECURITY,
            vendor='openfigi',
        ))
    
    # Note: exchCode + ticker would map to LISTING scope
    # but OpenFIGI doesn't give us a listing-specific ID
    
    return mappings
```

---

## Crosswalk Table Design

```sql
-- =============================================================================
-- CROSSWALKS (Vendor ID mappings with provenance)
-- =============================================================================

CREATE TABLE crosswalks (
    crosswalk_id        CHAR(26) PRIMARY KEY,  -- ULID
    
    -- Our canonical ID (exactly one set)
    entity_id           CHAR(26) REFERENCES entities(entity_id),
    security_id         CHAR(26) REFERENCES securities(security_id),
    listing_id          CHAR(26) REFERENCES listings(listing_id),
    
    -- Vendor identifier
    vendor              VARCHAR(30) NOT NULL,
    vendor_id_type      VARCHAR(50) NOT NULL,  -- Vendor's name for this ID type
    vendor_id_value     VARCHAR(200) NOT NULL,
    
    -- Mapping metadata
    mapping_source      VARCHAR(50) NOT NULL,  -- How we got this mapping
    mapping_method      VARCHAR(30) NOT NULL,
    confidence          DECIMAL(3,2) DEFAULT 1.0,
    
    -- Temporal validity
    valid_from          DATE,
    valid_to            DATE,
    
    -- Capture tracking
    first_seen_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_verified_at    TIMESTAMPTZ,
    
    -- Conflicts
    conflict_count      INT DEFAULT 0,
    conflict_notes      TEXT,
    
    -- Audit
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT chk_crosswalk_scope CHECK (
        (entity_id IS NOT NULL)::int +
        (security_id IS NOT NULL)::int +
        (listing_id IS NOT NULL)::int = 1
    ),
    
    CONSTRAINT chk_mapping_method CHECK (mapping_method IN (
        'exact',           -- Exact ID match
        'derived',         -- Derived from related ID
        'vendor_file',     -- From vendor data file
        'api_lookup',      -- From vendor API
        'manual',          -- Manual mapping
        'inferred'         -- Inferred from context
    ))
);

CREATE INDEX idx_crosswalks_vendor ON crosswalks(vendor, vendor_id_type, vendor_id_value);
CREATE INDEX idx_crosswalks_entity ON crosswalks(entity_id) WHERE entity_id IS NOT NULL;
CREATE INDEX idx_crosswalks_security ON crosswalks(security_id) WHERE security_id IS NOT NULL;
CREATE INDEX idx_crosswalks_listing ON crosswalks(listing_id) WHERE listing_id IS NOT NULL;

-- =============================================================================
-- CROSSWALK CONFLICTS (When vendors disagree)
-- =============================================================================

CREATE TABLE crosswalk_conflicts (
    conflict_id         CHAR(26) PRIMARY KEY,
    
    -- The vendor ID in question
    vendor              VARCHAR(30) NOT NULL,
    vendor_id_type      VARCHAR(50) NOT NULL,
    vendor_id_value     VARCHAR(200) NOT NULL,
    
    -- Conflicting canonical IDs
    canonical_id_1      CHAR(26) NOT NULL,
    canonical_id_2      CHAR(26) NOT NULL,
    canonical_scope     VARCHAR(20) NOT NULL,  -- 'entity', 'security', 'listing'
    
    -- Conflict details
    conflict_type       VARCHAR(30) NOT NULL,
    description         TEXT,
    
    -- Resolution
    status              VARCHAR(20) DEFAULT 'open',
    resolved_to_id      CHAR(26),
    resolution_method   VARCHAR(50),
    resolution_notes    TEXT,
    resolved_at         TIMESTAMPTZ,
    resolved_by         VARCHAR(100),
    
    -- Audit
    detected_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT chk_conflict_type CHECK (conflict_type IN (
        'one_to_many',      -- One vendor ID maps to multiple canonical IDs
        'many_to_one',      -- Multiple vendor IDs map to same canonical ID
        'vendor_disagree',  -- Different vendors give different mappings
        'temporal_overlap', -- Overlapping valid periods
        'scope_mismatch'    -- ID assigned to wrong scope
    )),
    
    CONSTRAINT chk_status CHECK (status IN (
        'open',
        'investigating',
        'resolved',
        'false_positive',
        'accepted'  -- Known conflict, accepted as-is
    ))
);
```

---

## Conflict Handling

### Conflict Types

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  CONFLICT TYPE: ONE-TO-MANY                                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│  Scenario: One vendor ID maps to multiple canonical entities                 │
│                                                                              │
│  Example:                                                                    │
│    Bloomberg FIGI "BBG000XYZ123" →                                          │
│      • Security A (AAPL Class A)                                             │
│      • Security B (AAPL Class B)  ← ERROR: FIGI should be unique!           │
│                                                                              │
│  Cause: Data error in source or misunderstanding of ID scope                 │
│  Resolution: Investigate and pick correct mapping; remove incorrect one      │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│  CONFLICT TYPE: MANY-TO-ONE                                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│  Scenario: Multiple vendor IDs map to same canonical entity                  │
│                                                                              │
│  Example:                                                                    │
│    FactSet "001690-E" → Entity A (Apple)                                    │
│    FactSet "001690-R-US" → Entity A (Apple)  ← OK if different ID types     │
│                                                                              │
│  Cause: Often legitimate (different ID types for same thing)                 │
│  Resolution: Usually OK; verify ID types are different                       │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│  CONFLICT TYPE: VENDOR DISAGREE                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│  Scenario: Different vendors give different canonical mappings               │
│                                                                              │
│  Example:                                                                    │
│    Query: "What is ISIN US0378331005?"                                      │
│    FactSet: Security A (Apple Common Stock)                                  │
│    Refinitiv: Security B (Apple Common Stock) ← Different internal ID!      │
│                                                                              │
│  Cause: Different systems created different canonical records                │
│  Resolution: Merge canonical records; they represent same thing              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│  CONFLICT TYPE: SCOPE MISMATCH                                               │
├─────────────────────────────────────────────────────────────────────────────┤
│  Scenario: Vendor ID attached to wrong scope                                 │
│                                                                              │
│  Example:                                                                    │
│    FIGI "BBG000B9XRY4" attached to Entity (Apple Inc.)                      │
│    WRONG! FIGI is Security-scoped, not Entity-scoped.                        │
│                                                                              │
│  Cause: Misunderstanding of identifier semantics                             │
│  Resolution: Move identifier to correct scope; create security if needed     │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Conflict Resolution Algorithm

```python
class ConflictResolver:
    """Resolve crosswalk conflicts."""
    
    def __init__(self, db: Database):
        self.db = db
    
    async def resolve_one_to_many(
        self,
        vendor: str,
        vendor_id: str,
        candidates: list[str],  # Canonical IDs
    ) -> ResolutionResult:
        """Resolve when one vendor ID maps to multiple canonical IDs."""
        
        # Strategy 1: Check if one is a duplicate/merge target
        for cid in candidates:
            merge = await self.db.get_merge_target(cid)
            if merge:
                # This canonical ID was merged; use the target
                return ResolutionResult(
                    resolved_id=merge.to_entity_id,
                    method='merged_entity',
                    remove_ids=[cid],
                )
        
        # Strategy 2: Check confidence scores
        mappings = await self.db.get_crosswalks(vendor, vendor_id)
        best = max(mappings, key=lambda m: m.confidence)
        if best.confidence > 0.9 and all(
            m.confidence < 0.7 for m in mappings if m != best
        ):
            return ResolutionResult(
                resolved_id=best.canonical_id,
                method='confidence_winner',
                remove_ids=[m.canonical_id for m in mappings if m != best],
            )
        
        # Strategy 3: Defer to manual review
        return ResolutionResult(
            resolved_id=None,
            method='manual_review',
            queue_for_review=True,
        )
    
    async def resolve_scope_mismatch(
        self,
        identifier: Identifier,
        current_scope: str,
        correct_scope: str,
    ) -> ResolutionResult:
        """Fix identifier attached to wrong scope."""
        
        # Example: FIGI attached to entity, should be on security
        if current_scope == 'entity' and correct_scope == 'security':
            # Find or create the security for this entity
            entity = await self.db.get_entity(identifier.entity_id)
            securities = await self.db.get_securities_for_entity(entity.entity_id)
            
            if len(securities) == 1:
                # Easy case: only one security
                return ResolutionResult(
                    action='move_identifier',
                    from_scope='entity',
                    from_id=entity.entity_id,
                    to_scope='security',
                    to_id=securities[0].security_id,
                )
            elif len(securities) > 1:
                # Hard case: need to match to specific security
                return ResolutionResult(
                    action='manual_review',
                    note=f"Entity has {len(securities)} securities; cannot auto-assign FIGI",
                )
            else:
                # No securities exist; create one
                return ResolutionResult(
                    action='create_and_assign',
                    create_type='security',
                    parent_id=entity.entity_id,
                )
```

---

## Partial Mapping Strategy

Not all identifiers are available for all entities. Handle gracefully:

```python
@dataclass
class PartialMapping:
    """Represents a partial crosswalk with missing identifiers."""
    
    entity_id: str
    
    # What we have
    available_ids: dict[str, str]  # scheme -> value
    
    # What we're missing
    missing_ids: list[str]  # schemes we don't have
    
    # Enrichment status
    enrichment_attempted: dict[str, datetime]  # scheme -> last attempt
    enrichment_failed: dict[str, str]  # scheme -> failure reason


async def enrich_missing_identifiers(
    entity: Entity,
    missing: list[str],
) -> EnrichmentResult:
    """Attempt to fill in missing identifiers."""
    
    results = {}
    
    for scheme in missing:
        if scheme == 'lei':
            # Try GLEIF lookup by name
            if entity.legal_name:
                lei = await gleif.search_by_name(entity.legal_name)
                if lei:
                    results['lei'] = lei
        
        elif scheme == 'figi':
            # Try OpenFIGI lookup by ISIN or ticker
            securities = await get_securities(entity.entity_id)
            for sec in securities:
                if sec.isin:
                    figi = await openfigi.lookup(isin=sec.isin)
                    if figi:
                        results['figi'] = figi
                        break
        
        elif scheme == 'permid_entity':
            # Try Refinitiv Open PermID by LEI or name
            if entity.lei:
                permid = await permid.lookup(lei=entity.lei)
            else:
                permid = await permid.search(name=entity.legal_name)
            if permid:
                results['permid_entity'] = permid
    
    return EnrichmentResult(
        entity_id=entity.entity_id,
        added_identifiers=results,
        still_missing=[s for s in missing if s not in results],
    )
```

---

## Crosswalk Queries

### Get All Vendor IDs for an Entity

```sql
-- All vendor IDs for an entity (including its securities and listings)
WITH entity_tree AS (
    -- Entity level
    SELECT 'entity' AS scope, e.entity_id AS canonical_id
    FROM entities e
    WHERE e.entity_id = :entity_id
    
    UNION ALL
    
    -- Security level
    SELECT 'security' AS scope, s.security_id AS canonical_id
    FROM securities s
    WHERE s.issuer_entity_id = :entity_id
    
    UNION ALL
    
    -- Listing level
    SELECT 'listing' AS scope, l.listing_id AS canonical_id
    FROM listings l
    JOIN securities s ON s.security_id = l.security_id
    WHERE s.issuer_entity_id = :entity_id
)
SELECT 
    et.scope,
    c.vendor,
    c.vendor_id_type,
    c.vendor_id_value,
    c.confidence,
    c.valid_from,
    c.valid_to
FROM entity_tree et
JOIN crosswalks c ON (
    (et.scope = 'entity' AND c.entity_id = et.canonical_id) OR
    (et.scope = 'security' AND c.security_id = et.canonical_id) OR
    (et.scope = 'listing' AND c.listing_id = et.canonical_id)
)
ORDER BY et.scope, c.vendor, c.vendor_id_type;
```

### Reverse Lookup: Vendor ID → Canonical

```sql
-- Find canonical entity/security/listing from vendor ID
SELECT 
    COALESCE(c.entity_id, c.security_id, c.listing_id) AS canonical_id,
    CASE 
        WHEN c.entity_id IS NOT NULL THEN 'entity'
        WHEN c.security_id IS NOT NULL THEN 'security'
        ELSE 'listing'
    END AS scope,
    c.confidence,
    c.valid_from,
    c.valid_to,
    -- Get names for context
    COALESCE(e.legal_name, sec.name, l.ticker) AS name
FROM crosswalks c
LEFT JOIN entities e ON e.entity_id = c.entity_id
LEFT JOIN securities sec ON sec.security_id = c.security_id
LEFT JOIN listings l ON l.listing_id = c.listing_id
WHERE c.vendor = :vendor
  AND c.vendor_id_type = :id_type
  AND c.vendor_id_value = :id_value
  AND (c.valid_to IS NULL OR c.valid_to > CURRENT_DATE);
```

### Build Full Crosswalk for Export

```sql
-- Export format: all mappings for integration with other systems
SELECT 
    e.entity_id AS em_entity_id,
    e.legal_name,
    -- Standard IDs (from identifiers table)
    MAX(CASE WHEN i.scheme = 'cik' THEN i.value END) AS cik,
    MAX(CASE WHEN i.scheme = 'lei' THEN i.value END) AS lei,
    -- Vendor IDs (from crosswalks table)
    MAX(CASE WHEN c.vendor = 'factset' AND c.vendor_id_type = 'entity' 
        THEN c.vendor_id_value END) AS factset_entity_id,
    MAX(CASE WHEN c.vendor = 'refinitiv' AND c.vendor_id_type = 'permid_org' 
        THEN c.vendor_id_value END) AS permid_entity,
    MAX(CASE WHEN c.vendor = 's&p' AND c.vendor_id_type = 'gvkey' 
        THEN c.vendor_id_value END) AS sp_gvkey
FROM entities e
LEFT JOIN identifiers i ON i.entity_id = e.entity_id
LEFT JOIN crosswalks c ON c.entity_id = e.entity_id
WHERE e.status = 'active'
GROUP BY e.entity_id, e.legal_name
ORDER BY e.legal_name;
```

---

## Integration Points

### Loading Vendor Data

```python
class VendorDataLoader:
    """Load and map vendor data files."""
    
    async def load_bloomberg_file(self, filepath: str):
        """Load Bloomberg data export."""
        
        for row in read_csv(filepath):
            # Determine scope from Bloomberg ID type
            if row['ID_TYPE'] == 'COMPANY':
                scope = 'entity'
            elif row['ID_TYPE'] in ('FIGI', 'BUID'):
                scope = 'security'
            elif row['ID_TYPE'] in ('BBID', 'TICKER'):
                scope = 'listing'
            else:
                continue
            
            # Find or create canonical record
            canonical_id = await self.resolve_or_create(
                scope=scope,
                hints={
                    'isin': row.get('ISIN'),
                    'ticker': row.get('TICKER'),
                    'name': row.get('NAME'),
                },
            )
            
            # Add crosswalk
            await self.db.upsert_crosswalk(
                canonical_id=canonical_id,
                scope=scope,
                vendor='bloomberg',
                vendor_id_type=row['ID_TYPE'],
                vendor_id_value=row['ID_VALUE'],
                source='vendor_file',
                confidence=0.95,
            )
    
    async def load_factset_symbology(self, filepath: str):
        """Load FactSet symbology file."""
        
        for row in read_csv(filepath):
            fs_id = row['factset_id']
            
            # Parse FactSet ID to determine scope
            mapping = map_factset_id(fs_id)
            
            # Add crosswalk
            await self.db.upsert_crosswalk(
                vendor='factset',
                vendor_id_type=mapping.scheme,
                vendor_id_value=fs_id,
                scope=mapping.scope,
                source='vendor_file',
                confidence=0.95,
            )
```

---

## Next Documents

- [11_RESOLUTION_STRATEGY.md](11_RESOLUTION_STRATEGY.md) - How to resolve identifiers
- [12_STORAGE_TIERS.md](12_STORAGE_TIERS.md) - Tiered schema implementations
- [13_PYSECEDGAR_PORT.md](13_PYSECEDGAR_PORT.md) - py-sec-edgar integration
