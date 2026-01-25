# ADR-006: Time Semantics (captured_at vs valid_from)

**Status**: Accepted  
**Date**: 2026-01  
**Deciders**: Project maintainers

## Context

Financial data has complex temporal semantics:
- When was the data captured into our system?
- When was the data valid in the real world?
- When did a fact become true vs when did we learn it?

Early designs conflated these:
```python
# WRONG - ambiguous timestamp
class Claim:
    timestamp: datetime  # Is this capture time or validity time?
```

## Decision

**Use explicit `captured_at` + `valid_from`/`valid_to` on all temporal data.**

```python
@dataclass(frozen=True, slots=True)
class IdentifierClaim:
    captured_at: datetime      # When WE captured this (system time)
    valid_from: datetime | None  # When identifier became valid (business time)
    valid_to: datetime | None    # When identifier expired (business time)
```

### Semantics

| Field | Meaning | Example |
|-------|---------|---------|
| `captured_at` | When we ingested this data | "2026-01-28T10:30:00Z" |
| `valid_from` | When fact became true in reality | "2024-01-15" (IPO date) |
| `valid_to` | When fact stopped being true | "2025-03-01" (ticker changed) |

## Consequences

### Positive
- **Bitemporal queries**: "What did we know on date X about date Y?"
- **Audit trail**: Know exactly when data entered system
- **Historical accuracy**: Track when facts were true, not just when captured
- **Correction handling**: New captures don't overwrite validity windows

### Negative
- More fields to populate
- More complex queries
- Requires discipline to set correctly

### Example: Ticker Change

Apple changed from NASDAQ:AAPL to ... (hypothetical):

```python
# Old ticker claim
IdentifierClaim(
    scheme=IdentifierScheme.TICKER,
    value="AAPL",
    captured_at=datetime(2024, 1, 1),  # When we first captured
    valid_from=datetime(1980, 12, 12),  # IPO date
    valid_to=datetime(2025, 6, 1),      # When ticker changed
    status=ClaimStatus.SUPERSEDED,
)

# New ticker claim
IdentifierClaim(
    scheme=IdentifierScheme.TICKER,
    value="APPL",  # Hypothetical new ticker
    captured_at=datetime(2025, 6, 1),   # When we captured the change
    valid_from=datetime(2025, 6, 1),    # When new ticker became valid
    valid_to=None,                       # Still valid
    status=ClaimStatus.ACTIVE,
)
```

### Query Patterns

```python
# What identifiers were valid on 2024-06-15?
claims = store.find_claims(
    target_id=entity.id,
    valid_on=date(2024, 6, 15)
)

# What did we know as of 2024-01-01?
claims = store.find_claims(
    target_id=entity.id,
    captured_before=datetime(2024, 1, 1)
)
```
