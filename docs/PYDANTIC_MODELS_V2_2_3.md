# EntitySpine v2.2.3 Pydantic Models - Quick Reference

**Status:** Implemented (Updated v2.2.3)  
**Location:** `src/entityspine/models/`

---

## Overview

The v2.2.3 implementation uses **Pydantic v2** instead of dataclasses for:
- Better validation with clear error messages
- Built-in JSON serialization
- IDE support and type checking

**v2.2.3 Changes:**
- Entity/Security no longer have identifier fields (use IdentifierClaim)
- VendorNamespace for multi-vendor crosswalks
- Scheme-scope enforcement on IdentifierClaim
- ResolutionCandidate for lightweight match results

---

## Model Hierarchy

```
Entity (Legal organization - NO ticker, NO cik/lei fields)
  |-- Security (Financial instrument - NO isin/cusip fields)
        |-- Listing (Where it trades - TICKER HERE)

IdentifierClaim (Canonical source of truth for ALL identifiers)
```

---

## Entity Model

```python
# src/entityspine/models/entity.py
from pydantic import Field
from entityspine.models.base import EntitySpineModel

class Entity(EntitySpineModel):
    """
    Legal organization. 
    
    v2.2.3 CRITICAL:
    - NO TICKER (belongs on Listing)
    - NO cik/lei/ein fields (use IdentifierClaim)
    """
    
    entity_id: str = Field(default_factory=generate_id)
    primary_name: str = Field(..., min_length=1)
    entity_type: EntityType = EntityType.ORGANIZATION
    status: EntityStatus = EntityStatus.ACTIVE
    
    # Details
    jurisdiction: Optional[str] = None
    sic_code: Optional[str] = None
    incorporation_date: Optional[date] = None
    
    # Record provenance (NOT identifier storage)
    source_system: str = "unknown"  # e.g., "sec", "bloomberg"
    source_id: Optional[str] = None  # ID in source system
    
    # Redirect support (for merges)
    redirect_to: Optional[str] = None
    redirect_reason: Optional[str] = None
    merged_at: Optional[datetime] = None
    
    # Collections
    aliases: list[str] = Field(default_factory=list)
    
    # Timestamps
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
```

### EntityType Enum
```python
class EntityType(str, Enum):
    ORGANIZATION = "organization"
    PERSON = "person"
    GOVERNMENT = "government"
    FUND = "fund"
    TRUST = "trust"
    SPV = "spv"
```

### EntityStatus Enum
```python
class EntityStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    MERGED = "merged"
    PROVISIONAL = "provisional"
```

---

## Security Model

```python
# src/entityspine/models/security.py
class Security(EntitySpineModel):
    """
    Financial instrument issued by an Entity.
    
    v2.2.3 CRITICAL: NO isin/cusip/sedol/figi fields (use IdentifierClaim)
    """
    
    security_id: str = Field(default_factory=generate_id)
    entity_id: str                  # FK to Entity (issuer)
    security_type: SecurityType = SecurityType.COMMON_STOCK
    description: Optional[str] = None
    currency: Optional[str] = None  # ISO 4217
    
    # Record provenance (NOT identifier storage)
    source_system: str = "unknown"
    source_id: Optional[str] = None
    
    # Status
    status: SecurityStatus = SecurityStatus.ACTIVE
    
    # Timestamps
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
```

---

## Listing Model

```python
# src/entityspine/models/listing.py
class Listing(EntitySpineModel):
    """Where/when a Security trades. TICKER LIVES HERE!"""
    
    listing_id: str = Field(default_factory=generate_id)
    security_id: str                # FK to Security
    ticker: str = Field(..., min_length=1)  # TICKER HERE!
    exchange: str = ""
    mic: Optional[str] = None       # Market Identifier Code (ISO 10383)
    
    # Validity period
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    
    # Properties
    is_primary: bool = False
    currency: Optional[str] = None  # Trading currency
    status: ListingStatus = ListingStatus.ACTIVE
    source_system: str = "unknown"
    
    # Timestamps
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
```

---

## IdentifierClaim Model (v2.2.3 CANONICAL SOURCE)

```python
# src/entityspine/models/claim.py
class IdentifierClaim(EntitySpineModel):
    """
    Provenance-tracked identifier - THE canonical source of truth.
    
    v2.2.3 Features:
    - namespace: VendorNamespace for multi-vendor crosswalks
    - captured_at: Observation time (vs valid_from/to validity time)
    - Scheme-scope validation (CIK->entity, ISIN->security, TICKER->listing)
    - Auto-normalization of identifier values
    """
    
    claim_id: str = Field(default_factory=generate_id)
    
    # Target: exactly ONE must be set, must match scheme scope
    entity_id: Optional[str] = None     # For CIK, LEI, EIN, DUNS
    security_id: Optional[str] = None   # For ISIN, CUSIP, SEDOL, FIGI
    listing_id: Optional[str] = None    # For TICKER, RIC
    
    # The identifier
    scheme: IdentifierScheme        # CIK, LEI, ISIN, TICKER, etc.
    value: str                      # Auto-normalized by validators
    
    # v2.2.3: Vendor namespace
    namespace: VendorNamespace = VendorNamespace.INTERNAL
    source_ref: Optional[str] = None  # Reference ID in source
    
    # v2.2.3: Observation time (when captured) vs validity time
    captured_at: datetime = Field(default_factory=utc_now)
    valid_from: Optional[date] = None  # When identifier became valid
    valid_to: Optional[date] = None    # When identifier ended
    
    # Provenance
    source: str = "unknown"
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    status: ClaimStatus = ClaimStatus.ACTIVE
    notes: Optional[str] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
```

### VendorNamespace Enum (v2.2.3 NEW)
```python
class VendorNamespace(str, Enum):
    SEC = "sec"           # SEC EDGAR
    GLEIF = "gleif"       # Global LEI Foundation
    BLOOMBERG = "bloomberg"
    FACTSET = "factset"
    REUTERS = "reuters"
    OPENFIGI = "openfigi"
    INTERNAL = "internal"
    USER = "user"
```

### IdentifierScheme Enum
```python
class IdentifierScheme(str, Enum):
    # Entity-scoped
    CIK = "cik"       # -> entity_id
    LEI = "lei"       # -> entity_id
    EIN = "ein"       # -> entity_id
    DUNS = "duns"     # -> entity_id
    
    # Security-scoped
    ISIN = "isin"     # -> security_id
    CUSIP = "cusip"   # -> security_id
    SEDOL = "sedol"   # -> security_id
    FIGI = "figi"     # -> security_id
    
    # Listing-scoped
    TICKER = "ticker" # -> listing_id
    RIC = "ric"       # -> listing_id
    
    # Flexible
    INTERNAL = "internal"
    OTHER = "other"
```

---

## ResolutionCandidate Model (v2.2.3 NEW)

```python
# src/entityspine/models/candidate.py
class ResolutionCandidate(EntitySpineModel):
    """Lightweight match result - IDs only, no hydration."""
    
    entity_id: Optional[str] = None
    security_id: Optional[str] = None
    listing_id: Optional[str] = None
    score: float = 0.0
    match_reason: MatchReason
    matched_scheme: Optional[str] = None
    matched_value: Optional[str] = None
```

### MatchReason Enum
```python
class MatchReason(str, Enum):
    EXACT_CIK = "exact_cik"
    EXACT_LEI = "exact_lei"
    EXACT_TICKER = "exact_ticker"
    EXACT_ISIN = "exact_isin"
    NAME_FUZZY = "name_fuzzy"
    NAME_EXACT = "name_exact"
    ALIAS_MATCH = "alias_match"
```

---

## ResolutionResult Model

```python
# src/entityspine/models/resolution.py
class ResolutionResult(MutableEntitySpineModel):
    """Result with tier capability honesty."""
    
    # Core result
    entity: Optional[Entity] = None
    security: Optional[Security] = None
    listing: Optional[Listing] = None
    status: ResolutionStatus = ResolutionStatus.NOT_FOUND
    tier: ResolutionTier = ResolutionTier.TIER_0
    
    # Query context
    query: str = ""
    as_of: Optional[date] = None
    as_of_honored: bool = True
    
    # v2.2 tier honesty
    warnings: list[str] = Field(default_factory=list)
    
    # v2.2.3: Lightweight candidates
    candidates: list[ResolutionCandidate] = Field(default_factory=list)
    
    # Timing
    resolved_at: datetime = Field(default_factory=utc_now)
    elapsed_ms: float = 0.0
    
    @property
    def found(self) -> bool:
        return self.entity is not None
    
    @property
    def best(self) -> Optional[ResolutionCandidate]:
        """Highest-scoring candidate."""
        return self.candidates[0] if self.candidates else None
```

---

## Usage Example

```python
from entityspine import Entity, Security, Listing, IdentifierClaim
from entityspine import IdentifierScheme, VendorNamespace

# Create entity (NO cik field!)
entity = Entity(
    primary_name="Apple Inc.",
    source_system="sec",
    source_id="0000320193",  # Provenance only
)

# Track CIK via IdentifierClaim (canonical source)
cik_claim = IdentifierClaim(
    entity_id=entity.entity_id,
    scheme=IdentifierScheme.CIK,
    value="320193",  # Auto-normalized to 0000320193
    namespace=VendorNamespace.SEC,
    source="sec_edgar",
)

security = Security(
    entity_id=entity.entity_id,
    description="Apple Inc. Common Stock",
)

# Track ISIN via IdentifierClaim
isin_claim = IdentifierClaim(
    security_id=security.security_id,
    scheme=IdentifierScheme.ISIN,
    value="US0378331005",
    namespace=VendorNamespace.OPENFIGI,
    source="openfigi_api",
)

listing = Listing(
    security_id=security.security_id,
    ticker="AAPL",
    mic="XNAS",
    is_primary=True,
)
```

---

## Key v2.2.3 Design Decisions

| Decision | Rationale |
|----------|-----------|
| No identifier fields on Entity/Security | IdentifierClaim is single source of truth |
| VendorNamespace enum | Multi-vendor crosswalk support |
| captured_at vs valid_from | Observation time != validity time |
| Scheme-scope rules | CIK->entity, ISIN->security, TICKER->listing |
| ResolutionCandidate (IDs only) | Lightweight results, lazy hydration |

---

*Last updated: v2.2.3*
