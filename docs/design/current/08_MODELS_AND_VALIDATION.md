# EntitySpine v2.2.3 Models and Validation Design

## Overview

This document describes the design decisions for EntitySpine's Pydantic model layer,
addressing identifier management, provenance tracking, and multi-vendor crosswalks.

## Core Design Principles

### 1. Single Source of Truth: IdentifierClaim

**Problem (v2.2.2):** Entity had multiple ways to track identifiers:
- Direct fields: `cik`, `lei`, `ein`
- Dict field: `identifiers: dict[str, str]`
- Claims: `IdentifierClaim` objects

This created confusion about which was authoritative.

**Solution (v2.2.3):** `IdentifierClaim` is THE canonical source of truth.
- Entity no longer has `cik`, `lei`, `ein`, or `identifiers` fields
- Security no longer has `isin`, `cusip`, `sedol`, `figi` fields
- All identifiers are tracked via `IdentifierClaim` with full provenance

```python
# v2.2.3: Entity has NO identifier fields
entity = Entity(
    entity_id="01HABC...",
    primary_name="Apple Inc.",
    source_system="sec",  # Provenance only
    source_id="0000320193",
)

# Identifiers tracked via claims
claim = IdentifierClaim(
    entity_id="01HABC...",
    scheme=IdentifierScheme.CIK,
    value="320193",  # Auto-normalized to 0000320193
    namespace=VendorNamespace.SEC,
    source="sec_edgar",
)
```

### 2. Scheme-Scope Enforcement

Identifiers have a natural scope where they apply:
- **Entity-scoped:** CIK, LEI, EIN, DUNS (legal identity)
- **Security-scoped:** ISIN, CUSIP, SEDOL, FIGI (financial instrument)
- **Listing-scoped:** TICKER, RIC (exchange-specific)

The `IdentifierClaim` model validator enforces these rules:

```python
# Valid: CIK is entity-scoped
IdentifierClaim(entity_id="...", scheme=IdentifierScheme.CIK, value="320193")

# Invalid: CIK on a listing (ValidationError)
IdentifierClaim(listing_id="...", scheme=IdentifierScheme.CIK, value="320193")
```

### 3. Vendor Namespace Support

Multi-vendor data environments need to track where data came from:

```python
class VendorNamespace(str, Enum):
    SEC = "sec"
    GLEIF = "gleif"
    BLOOMBERG = "bloomberg"
    FACTSET = "factset"
    REUTERS = "reuters"
    OPENFIGI = "openfigi"
    INTERNAL = "internal"
    USER = "user"
```

Claims track their source namespace:

```python
# Bloomberg-sourced FIGI
IdentifierClaim(
    security_id="...",
    scheme=IdentifierScheme.FIGI,
    value="BBG000B9XRY4",
    namespace=VendorNamespace.OPENFIGI,
)

# SEC-sourced CIK
IdentifierClaim(
    entity_id="...",
    scheme=IdentifierScheme.CIK,
    value="0000320193",
    namespace=VendorNamespace.SEC,
)
```

### 4. Observation Time vs Validity Time

**Problem:** When was this data captured vs when was the identifier actually valid?

**Solution:** Separate timestamps:
- `captured_at`: When we observed/recorded this claim (always set)
- `valid_from`/`valid_to`: When the identifier was actually valid (business time)
- `created_at`/`updated_at`: Record timestamps (technical)

```python
claim = IdentifierClaim(
    entity_id="01HABC...",
    scheme=IdentifierScheme.LEI,
    value="HWUPKR0MPOU8FGXBT394",
    namespace=VendorNamespace.GLEIF,
    captured_at=datetime(2024, 1, 15, 10, 30),  # When we downloaded GLEIF data
    valid_from=date(2012, 6, 1),  # When LEI was assigned
    valid_to=None,  # Still valid
)
```

### 5. ResolutionCandidate for Lightweight Matches

**Problem:** `ResolutionResult.alternatives` required hydrated Entity objects.

**Solution:** `ResolutionCandidate` provides lightweight match info:

```python
class ResolutionCandidate(EntitySpineModel):
    entity_id: Optional[str] = None
    security_id: Optional[str] = None
    listing_id: Optional[str] = None
    score: float
    match_reason: MatchReason
    matched_value: Optional[str] = None

# ResolutionResult now has candidates
result = resolve("AAPL")
for candidate in result.candidates:
    print(f"{candidate.entity_id}: {candidate.score} ({candidate.match_reason})")
```

## Module Structure

```
src/entityspine/models/
├── __init__.py        # Public exports
├── base.py            # EntitySpineModel base class
├── entity.py          # Entity model (NO identifier fields)
├── security.py        # Security model (NO identifier fields)
├── listing.py         # Listing model (has ticker/exchange)
├── claim.py           # IdentifierClaim with validation
├── candidate.py       # ResolutionCandidate (NEW)
├── resolution.py      # ResolutionResult with candidates
└── validators.py      # VendorNamespace, IdentifierScope, normalizers (NEW)
```

## Validators Module

The `validators.py` module provides:

### Enums
- `VendorNamespace`: Data source namespaces
- `IdentifierScope`: ENTITY, SECURITY, LISTING, ANY

### Normalizers
- `normalize_cik(value)` → 10-digit padded
- `normalize_lei(value)` → uppercase 20 chars
- `normalize_isin(value)` → uppercase 12 chars
- `normalize_cusip(value)` → uppercase 9 chars
- `normalize_sedol(value)` → uppercase 7 chars
- `normalize_figi(value)` → uppercase 12 chars
- `normalize_ticker(value)` → uppercase, dash→dot

### Validators
- `validate_cik(value)` → True if 10 digits
- `validate_lei(value)` → True if 20 alphanumeric
- `validate_isin(value)` → True if 12 alphanumeric
- etc.

### Scheme-Scope Rules
```python
SCHEME_SCOPES = {
    "cik": IdentifierScope.ENTITY,
    "lei": IdentifierScope.ENTITY,
    "isin": IdentifierScope.SECURITY,
    "ticker": IdentifierScope.LISTING,
    # ...
}
```

## Migration Notes

### Breaking Changes from v2.2.2

1. **Entity no longer has `cik`, `lei`, `ein`, `identifiers` fields**
   - Use `source_system`/`source_id` for record provenance
   - Use `IdentifierClaim` for identifier tracking

2. **Security no longer has `isin`, `cusip`, `sedol`, `figi` fields**
   - Use `IdentifierClaim` for identifier tracking

3. **IdentifierClaim requires namespace**
   - New `namespace` field (defaults to `VendorNamespace.INTERNAL`)
   - New `captured_at` field (defaults to now)

4. **ResolutionResult has `candidates` instead of hydrated `alternatives`**
   - Use `result.candidates` for lightweight match info
   - Use `result.best` for highest-scoring candidate

### Migration Example

```python
# v2.2.2 (OLD)
entity = Entity(
    entity_id="01HABC...",
    primary_name="Apple Inc.",
    cik="0000320193",  # NO LONGER VALID
)

# v2.2.3 (NEW)
entity = Entity(
    entity_id="01HABC...",
    primary_name="Apple Inc.",
    source_system="sec",
    source_id="0000320193",
)

claim = IdentifierClaim(
    entity_id="01HABC...",
    scheme=IdentifierScheme.CIK,
    value="320193",  # Auto-normalized
    namespace=VendorNamespace.SEC,
    source="sec_edgar",
)
```

## Dependency Strategy

**Pydantic is a REQUIRED dependency.**

The models module requires Pydantic v2.x (currently tested with 2.12.5).
This is intentional - domain models are core to the library and benefit
from Pydantic's validation, serialization, and type safety.

Optional dependencies:
- `sqlmodel` - For SQLite/database storage (Tier 1+)
- `aiohttp` - For async SEC API access

## Testing

Run model tests:
```bash
pytest tests/unit/domain/models/ -v
```

Key test files:
- `test_entity.py` - Entity creation, no-ticker enforcement
- `test_listing.py` - Ticker belongs on Listing
- `test_resolution.py` - ResolutionResult with candidates
- `test_claim.py` - Scheme-scope validation (to be added)

## Design Decisions Summary

| Decision | Rationale |
|----------|-----------|
| Remove identifier fields from Entity | Single source of truth (IdentifierClaim) |
| VendorNamespace enum | Multi-vendor crosswalk support |
| captured_at vs valid_from | Observation time != validity time |
| ResolutionCandidate (IDs only) | Lightweight results, lazy hydration |
| Scheme-scope rules | Prevent invalid assignments |
| Pydantic required | Core domain modeling needs validation |
