# EntitySpine v2.2.2 Pydantic Models - Quick Reference

**Status:** ✅ Implemented  
**Location:** `src/entityspine/models/`

---

## Overview

The v2.2.2 implementation uses **Pydantic v2** instead of dataclasses for:
- Better validation with clear error messages
- Built-in JSON serialization
- IDE support and type checking

---

## Model Hierarchy

```
Entity (Legal organization - NO ticker)
  └── Security (Financial instrument)
        └── Listing (Where it trades - TICKER HERE)

IdentifierClaim (Provenance-tracked identifier on any object)
```

---

## Entity Model

```python
# src/entityspine/models/entity.py
from pydantic import Field
from entityspine.models.base import EntitySpineModel

class Entity(EntitySpineModel):
    """Legal organization. NO TICKER HERE."""
    
    entity_id: str = Field(default_factory=generate_id)
    primary_name: str = Field(..., min_length=1)
    entity_type: EntityType = EntityType.ORGANIZATION
    status: EntityStatus = EntityStatus.ACTIVE
    
    # Identifiers (convenience fields)
    cik: Optional[str] = None      # Zero-padded to 10 digits
    lei: Optional[str] = None      # 20-char LEI
    ein: Optional[str] = None      # 9-char EIN
    
    # Details
    jurisdiction: Optional[str] = None
    sic_code: Optional[str] = None
    incorporation_date: Optional[date] = None
    
    # v2.2 spec fields
    source_system: str = "unknown"
    source_id: Optional[str] = None
    
    # Redirect support (for merges)
    redirect_to: Optional[str] = None
    redirect_reason: Optional[str] = None
    merged_at: Optional[datetime] = None
    
    # Collections
    identifiers: dict[str, str] = Field(default_factory=dict)
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
    """Financial instrument issued by an Entity."""
    
    security_id: str = Field(default_factory=generate_id)
    entity_id: str                  # FK to Entity (issuer)
    security_type: SecurityType = SecurityType.COMMON_STOCK
    description: Optional[str] = None
    
    # Standard identifiers
    isin: Optional[str] = None      # 12-char ISIN
    cusip: Optional[str] = None     # 9-char CUSIP
    sedol: Optional[str] = None     # 7-char SEDOL
    figi: Optional[str] = None      # 12-char FIGI
    
    # v2.2 spec fields
    currency: Optional[str] = None  # ISO 4217
    status: str = "active"
    source_system: str = "unknown"
    
    # Timestamps
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
```

### SecurityType Enum
```python
class SecurityType(str, Enum):
    COMMON_STOCK = "common_stock"
    PREFERRED_STOCK = "preferred_stock"
    ADR = "adr"
    ETF = "etf"
    BOND = "bond"
    WARRANT = "warrant"
    OPTION = "option"
    UNIT = "unit"
    OTHER = "other"
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
    
    # Standard identifiers
    mic: Optional[str] = None       # Market Identifier Code (ISO 10383)
    
    # Validity period
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    
    # Properties
    is_primary: bool = False
    currency: Optional[str] = None  # Trading currency
    
    # v2.2 spec fields
    status: str = "active"
    source_system: str = "unknown"
    
    # Timestamps
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
```

---

## IdentifierClaim Model

```python
# src/entityspine/models/claim.py
class IdentifierClaim(EntitySpineModel):
    """Provenance-tracked identifier claim."""
    
    claim_id: str = Field(default_factory=generate_id)
    
    # v2.2: exactly ONE of these must be set
    entity_id: Optional[str] = None
    security_id: Optional[str] = None
    listing_id: Optional[str] = None
    
    # The identifier
    scheme: IdentifierScheme        # CIK, LEI, ISIN, etc.
    value: str = Field(..., min_length=1)
    
    # Validity
    valid_from: Optional[date] = None
    valid_to: Optional[date] = None
    
    # Provenance
    source: str = "unknown"
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    status: ClaimStatus = ClaimStatus.ACTIVE
    notes: Optional[str] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
```

### IdentifierScheme Enum
```python
class IdentifierScheme(str, Enum):
    CIK = "cik"
    LEI = "lei"
    EIN = "ein"
    ISIN = "isin"
    CUSIP = "cusip"
    SEDOL = "sedol"
    FIGI = "figi"
    TICKER = "ticker"
    INTERNAL = "internal"
    OTHER = "other"
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
    limits: dict[str, str] = Field(default_factory=dict)
    
    # Resolution path
    redirect_chain: list[str] = Field(default_factory=list)
    alternatives: list[Entity] = Field(default_factory=list)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    
    # Timing
    resolved_at: datetime = Field(default_factory=utc_now)
    elapsed_ms: float = 0.0
    
    @property
    def found(self) -> bool:
        return self.entity is not None
    
    @property
    def has_warnings(self) -> bool:
        return len(self.warnings) > 0
```

---

## Usage Example

```python
from entityspine import Entity, Security, Listing, IdentifierClaim
from entityspine import IdentifierScheme, create_store

# Create entities
entity = Entity(
    primary_name="Apple Inc.",
    cik="0000320193",
    source_system="sec",
)

security = Security(
    entity_id=entity.entity_id,
    description="Apple Inc. Common Stock",
    isin="US0378331005",
)

listing = Listing(
    security_id=security.security_id,
    ticker="AAPL",
    mic="XNAS",
    is_primary=True,
)

# Create a claim with provenance
claim = IdentifierClaim(
    entity_id=entity.entity_id,
    scheme=IdentifierScheme.CIK,
    value="0000320193",
    source="sec_edgar",
    confidence=1.0,
)

# Use the store
with create_store(":memory:") as store:
    store.save_entity(entity)
    result = store.resolve("AAPL")
    if result.found:
        print(result.entity.primary_name)
```

---

## Key Differences from v2.2 Spec

| Spec (dataclasses) | Implementation (Pydantic) | Notes |
|--------------------|---------------------------|-------|
| `@dataclass(frozen=True)` | `class Config: frozen = True` | Same immutability |
| `field(default_factory=...)` | `Field(default_factory=...)` | Same pattern |
| Manual validation | `@field_validator` | Declarative |
| `asdict()` | `model_dump()` | Built-in |

---

*Last updated: January 2026*
