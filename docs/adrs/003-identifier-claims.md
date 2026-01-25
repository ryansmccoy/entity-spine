# ADR-003: Identifier Claims Pattern

**Status**: Accepted  
**Date**: 2025-12  
**Deciders**: Project maintainers

## Context

Financial entities have many identifiers from many sources:
- CIK (SEC), LEI (GLEIF), FIGI (OpenFIGI)
- CUSIP, ISIN, SEDOL (securities)
- Tickers (exchange-specific)
- Vendor IDs (Bloomberg, FactSet, Reuters)

Early designs stored identifiers directly on Entity:
```python
# WRONG - identifiers on entity
@dataclass
class Entity:
    cik: str | None
    lei: str | None
    figi: str | None  # Doesn't belong here!
```

Problems:
- Schema changes when adding new identifier types
- No provenance tracking
- No handling of conflicting values
- Securities identifiers mixed with entity identifiers

## Decision

**Identifiers are stored as separate IdentifierClaim objects**, not on entities.

```python
@dataclass(frozen=True, slots=True)
class IdentifierClaim:
    """A claim that an identifier belongs to an entity/security/listing."""
    id: str
    scheme: IdentifierScheme      # CIK, LEI, CUSIP, ISIN, TICKER
    value: str                    # The actual identifier value
    scope: IdentifierScope        # ENTITY, SECURITY, LISTING
    target_id: str                # What this identifies
    namespace: VendorNamespace    # Who provided this claim
    status: ClaimStatus           # ACTIVE, SUPERSEDED, DISPUTED
    captured_at: datetime         # When we captured this
    valid_from: datetime | None   # When identifier became valid
    valid_to: datetime | None     # When identifier expired
```

Scheme-scope rules are enforced:
```python
SCHEME_SCOPES = {
    IdentifierScheme.CIK: IdentifierScope.ENTITY,
    IdentifierScheme.LEI: IdentifierScope.ENTITY,
    IdentifierScheme.CUSIP: IdentifierScope.SECURITY,
    IdentifierScheme.ISIN: IdentifierScope.SECURITY,
    IdentifierScheme.TICKER: IdentifierScope.LISTING,
}
```

## Consequences

### Positive
- **Multi-source**: Same entity can have CIK from SEC, LEI from GLEIF
- **Historical**: Track when identifiers changed
- **Conflict resolution**: Multiple claims can exist, status tracks resolution
- **Extensible**: Add new schemes without schema changes
- **Audit trail**: Know who claimed what, when

### Negative
- More complex queries (JOIN to get identifiers)
- No single "canonical" identifier on entity
- Requires claim store in addition to entity store

### Query Pattern
```python
# Find entity by CIK
claims = store.find_claims(scheme=IdentifierScheme.CIK, value="0000320193")
entity = store.get_entity(claims[0].target_id)

# Get all identifiers for entity
claims = store.get_claims_for_target(entity.id)
```
