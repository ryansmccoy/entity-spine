# Entity Master - Resolution Strategy

**How to resolve identifiers to canonical entities, with proper scope handling and merge support.**

---

## Resolution Overview

Resolution is the process of taking an input identifier and finding the canonical record it refers to.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           RESOLUTION FLOW                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  INPUT                     RESOLUTION                    OUTPUT              │
│  ─────                     ──────────                    ──────              │
│                                                                              │
│  "AAPL"          →   Detect: looks like ticker                              │
│                  →   Scope: LISTING (ticker → listing)                       │
│                  →   Lookup: listings WHERE ticker='AAPL' AND active         │
│                  →   Found: listing_id = "01HYX..."                          │
│                  →   Traverse: listing → security → entity                   │
│                  →   Return: ResolvedEntity(Apple Inc.)                      │
│                                                                              │
│  "0000320193"    →   Detect: 10-digit, CIK pattern                          │
│                  →   Scope: ENTITY (CIK → entity)                            │
│                  →   Lookup: identifiers WHERE scheme='cik'                  │
│                  →   Return: ResolvedEntity(Apple Inc.)                      │
│                                                                              │
│  "US0378331005"  →   Detect: 12-char, ISIN pattern                          │
│                  →   Scope: SECURITY (ISIN → security)                       │
│                  →   Lookup: identifiers WHERE scheme='isin'                 │
│                  →   Traverse: security → entity                             │
│                  →   Return: ResolvedEntity(Apple Inc.) with security_id     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Identifier Strength Ranking

Not all identifiers are equally reliable. Rank them:

### Tier 1: Authoritative (Confidence: 1.0)

These are globally unique, assigned by official registries:

| Identifier | Scope | Authority | Notes |
|------------|-------|-----------|-------|
| **CIK** | Entity | SEC | Unique within SEC universe |
| **LEI** | Entity | GLEIF | Globally unique, ISO 17442 |
| **ISIN** | Security | National Numbering Agencies | Globally unique |
| **CUSIP** | Security | CUSIP Global Services | US/Canada |
| **SEDOL** | Security | London Stock Exchange | UK/Ireland |
| **FIGI** | Security | Bloomberg/OMG | Globally unique |

### Tier 2: Strong (Confidence: 0.95)

These are reliable but may have edge cases:

| Identifier | Scope | Notes |
|------------|-------|-------|
| **EIN** | Entity | US tax ID; can change |
| **DUNS** | Entity | D&B; may have duplicates |
| **PermID** | Entity/Security | Refinitiv; reliable |
| **FactSet ID** | Entity/Security | FactSet; reliable |
| **S&P GVKEY** | Entity | S&P; reliable for public companies |

### Tier 3: Contextual (Confidence: 0.7-0.9)

These require additional context to resolve unambiguously:

| Identifier | Scope | Context Needed |
|------------|-------|----------------|
| **Ticker** | Listing | Exchange (MIC) + date |
| **RIC** | Listing | Exchange + date |
| **Bloomberg Ticker** | Listing | Includes exchange suffix |
| **Company Name** | Entity | Fuzzy match required |

### Tier 4: Weak (Confidence: 0.5-0.7)

These are ambiguous without significant context:

| Identifier | Issue |
|------------|-------|
| Partial ticker (no exchange) | Could match multiple |
| Abbreviated name | Too many matches |
| Former name | Need temporal context |

---

## Resolution Paths

### Path 1: Ticker → Listing → Security → Entity

Most common for trading-oriented queries.

```python
async def resolve_ticker(
    ticker: str,
    mic: str | None = None,
    as_of_date: date | None = None,
) -> ResolvedEntity | None:
    """Resolve a ticker symbol to an entity.
    
    Args:
        ticker: The ticker symbol (e.g., "AAPL", "GM")
        mic: Market Identifier Code (e.g., "XNAS", "XNYS")
        as_of_date: Point-in-time date for historical resolution
    """
    
    as_of = as_of_date or date.today()
    
    # Step 1: Find listing(s)
    query = """
        SELECT l.listing_id, l.security_id, l.mic, l.valid_from, l.valid_to
        FROM listings l
        WHERE l.ticker = :ticker
          AND l.valid_from <= :as_of
          AND (l.valid_to IS NULL OR l.valid_to > :as_of)
    """
    
    params = {'ticker': ticker, 'as_of': as_of}
    
    if mic:
        query += " AND l.mic = :mic"
        params['mic'] = mic
    
    listings = await db.fetch_all(query, params)
    
    if not listings:
        return None
    
    if len(listings) > 1 and not mic:
        # Ambiguous: ticker exists on multiple exchanges
        # Try to pick primary listing
        primary = [l for l in listings if l['is_primary']]
        if len(primary) == 1:
            listings = primary
        else:
            raise AmbiguousTickerError(
                ticker=ticker,
                candidates=[f"{l['mic']}:{ticker}" for l in listings],
            )
    
    listing = listings[0]
    
    # Step 2: Get security
    security = await db.fetch_one(
        "SELECT * FROM securities WHERE security_id = :id",
        {'id': listing['security_id']},
    )
    
    # Step 3: Get entity
    entity = await db.fetch_one(
        "SELECT * FROM entities WHERE entity_id = :id",
        {'id': security['issuer_entity_id']},
    )
    
    # Step 4: Check for merges/redirects
    entity = await follow_redirects(entity)
    
    return build_resolved_entity(
        entity=entity,
        security=security,
        listing=listing,
        resolution_path='ticker -> listing -> security -> entity',
        confidence=0.85 if not mic else 0.95,
    )
```

### Path 2: CIK → Entity (Direct)

Most reliable for SEC data.

```python
async def resolve_cik(cik: str) -> ResolvedEntity | None:
    """Resolve SEC CIK to entity.
    
    CIK is entity-scoped and authoritative.
    """
    
    # Normalize CIK (10-digit, zero-padded)
    cik_normalized = cik.zfill(10)
    
    # Direct lookup
    identifier = await db.fetch_one(
        """
        SELECT i.entity_id
        FROM identifiers i
        WHERE i.scheme = 'cik'
          AND i.value = :cik
          AND i.entity_id IS NOT NULL
        """,
        {'cik': cik_normalized},
    )
    
    if not identifier:
        return None
    
    entity = await db.fetch_one(
        "SELECT * FROM entities WHERE entity_id = :id",
        {'id': identifier['entity_id']},
    )
    
    # Follow redirects (entity may have been merged)
    entity = await follow_redirects(entity)
    
    return build_resolved_entity(
        entity=entity,
        resolution_path='cik -> entity',
        confidence=1.0,  # CIK is authoritative
    )
```

### Path 3: ISIN → Security → Entity

Standard for cross-border securities.

```python
async def resolve_isin(isin: str) -> ResolvedEntity | None:
    """Resolve ISIN to entity via security.
    
    ISIN is security-scoped.
    """
    
    # Validate ISIN format
    if not is_valid_isin(isin):
        raise InvalidIdentifierError(f"Invalid ISIN format: {isin}")
    
    # Find security
    identifier = await db.fetch_one(
        """
        SELECT i.security_id
        FROM identifiers i
        WHERE i.scheme = 'isin'
          AND i.value = :isin
          AND i.security_id IS NOT NULL
          AND (i.valid_to IS NULL OR i.valid_to > CURRENT_DATE)
        """,
        {'isin': isin},
    )
    
    if not identifier:
        return None
    
    security = await db.fetch_one(
        "SELECT * FROM securities WHERE security_id = :id",
        {'id': identifier['security_id']},
    )
    
    # Get issuer entity
    entity = await db.fetch_one(
        "SELECT * FROM entities WHERE entity_id = :id",
        {'id': security['issuer_entity_id']},
    )
    
    entity = await follow_redirects(entity)
    
    return build_resolved_entity(
        entity=entity,
        security=security,
        resolution_path='isin -> security -> entity',
        confidence=1.0,
    )
```

### Path 4: LEI → Entity (Direct)

Global entity identifier.

```python
async def resolve_lei(lei: str) -> ResolvedEntity | None:
    """Resolve GLEIF LEI to entity.
    
    LEI is entity-scoped and globally unique.
    """
    
    # Validate LEI format (20 alphanumeric)
    if not is_valid_lei(lei):
        raise InvalidIdentifierError(f"Invalid LEI format: {lei}")
    
    identifier = await db.fetch_one(
        """
        SELECT i.entity_id
        FROM identifiers i
        WHERE i.scheme = 'lei'
          AND i.value = :lei
          AND i.entity_id IS NOT NULL
        """,
        {'lei': lei.upper()},
    )
    
    if not identifier:
        return None
    
    entity = await db.fetch_one(
        "SELECT * FROM entities WHERE entity_id = :id",
        {'id': identifier['entity_id']},
    )
    
    entity = await follow_redirects(entity)
    
    return build_resolved_entity(
        entity=entity,
        resolution_path='lei -> entity',
        confidence=1.0,
    )
```

### Path 5: FIGI → Security → Entity

Bloomberg identifier (security-scoped).

```python
async def resolve_figi(figi: str) -> ResolvedEntity | None:
    """Resolve Bloomberg FIGI to entity via security.
    
    FIGI is security-scoped (NOT entity-scoped!).
    """
    
    # Validate FIGI format (BBG + 8 chars)
    if not figi.startswith('BBG') or len(figi) != 12:
        raise InvalidIdentifierError(f"Invalid FIGI format: {figi}")
    
    # FIGI maps to security
    identifier = await db.fetch_one(
        """
        SELECT i.security_id
        FROM identifiers i
        WHERE i.scheme IN ('figi', 'composite_figi', 'share_class_figi')
          AND i.value = :figi
          AND i.security_id IS NOT NULL
        """,
        {'figi': figi},
    )
    
    if not identifier:
        return None
    
    security = await db.fetch_one(
        "SELECT * FROM securities WHERE security_id = :id",
        {'id': identifier['security_id']},
    )
    
    entity = await db.fetch_one(
        "SELECT * FROM entities WHERE entity_id = :id",
        {'id': security['issuer_entity_id']},
    )
    
    entity = await follow_redirects(entity)
    
    return build_resolved_entity(
        entity=entity,
        security=security,
        resolution_path='figi -> security -> entity',
        confidence=1.0,
    )
```

### Path 6: Name → Entity (Fuzzy)

Least reliable; requires fuzzy matching.

```python
async def resolve_name(
    name: str,
    entity_type: str | None = None,
    hints: dict | None = None,
) -> ResolvedEntity | list[ResolvedEntity] | None:
    """Resolve entity by name with fuzzy matching.
    
    Args:
        name: Company/entity name
        entity_type: Filter by type (COMPANY, FUND, etc.)
        hints: Additional context (sic_code, state, etc.)
    """
    
    # Normalize name
    normalized = normalize_company_name(name)
    
    # Step 1: Try exact match on aliases
    exact = await db.fetch_all(
        """
        SELECT a.entity_id, a.name, a.alias_type
        FROM entity_aliases a
        WHERE a.name_normalized = :normalized
        """,
        {'normalized': normalized},
    )
    
    if len(exact) == 1:
        entity = await get_entity(exact[0]['entity_id'])
        return build_resolved_entity(
            entity=entity,
            resolution_path='name (exact) -> entity',
            confidence=0.95,
        )
    
    # Step 2: Full-text search (Tier 2+)
    fts_results = await db.fetch_all(
        """
        SELECT a.entity_id, a.name, 
               ts_rank(to_tsvector('english', a.name), plainto_tsquery(:name)) AS rank
        FROM entity_aliases a
        WHERE to_tsvector('english', a.name) @@ plainto_tsquery(:name)
        ORDER BY rank DESC
        LIMIT 10
        """,
        {'name': name},
    )
    
    if not fts_results:
        return None
    
    # Step 3: Apply fuzzy scoring
    scored = []
    for result in fts_results:
        score = calculate_fuzzy_score(name, result['name'], hints)
        scored.append((result, score))
    
    scored.sort(key=lambda x: x[1], reverse=True)
    
    # Step 4: Decide based on scores
    best_score = scored[0][1]
    
    if best_score >= 0.95:
        # High confidence single match
        entity = await get_entity(scored[0][0]['entity_id'])
        return build_resolved_entity(
            entity=entity,
            resolution_path='name (fuzzy) -> entity',
            confidence=best_score,
        )
    
    elif best_score >= 0.7:
        # Multiple possible matches
        close_matches = [(r, s) for r, s in scored if s >= best_score - 0.1]
        
        if len(close_matches) == 1:
            entity = await get_entity(close_matches[0][0]['entity_id'])
            return build_resolved_entity(
                entity=entity,
                resolution_path='name (fuzzy) -> entity',
                confidence=close_matches[0][1],
            )
        else:
            # Return candidates for manual review
            candidates = []
            for result, score in close_matches[:5]:
                entity = await get_entity(result['entity_id'])
                candidates.append(build_resolved_entity(
                    entity=entity,
                    resolution_path='name (fuzzy) -> entity',
                    confidence=score,
                ))
            return candidates  # Caller decides
    
    else:
        # No good match
        return None
```

---

## Identifier Detection

Auto-detect identifier type from input string:

```python
import re
from enum import Enum


class IdentifierType(Enum):
    CIK = 'cik'
    LEI = 'lei'
    ISIN = 'isin'
    CUSIP = 'cusip'
    SEDOL = 'sedol'
    FIGI = 'figi'
    TICKER = 'ticker'
    NAME = 'name'
    UNKNOWN = 'unknown'


# Detection patterns
PATTERNS = {
    # CIK: 1-10 digits
    IdentifierType.CIK: re.compile(r'^0*\d{1,10}$'),
    
    # LEI: 20 alphanumeric (specific checksum)
    IdentifierType.LEI: re.compile(r'^[A-Z0-9]{20}$'),
    
    # ISIN: 2 letters + 9 alphanumeric + 1 check digit
    IdentifierType.ISIN: re.compile(r'^[A-Z]{2}[A-Z0-9]{9}\d$'),
    
    # CUSIP: 9 alphanumeric
    IdentifierType.CUSIP: re.compile(r'^[A-Z0-9]{9}$'),
    
    # SEDOL: 7 alphanumeric
    IdentifierType.SEDOL: re.compile(r'^[A-Z0-9]{7}$'),
    
    # FIGI: BBG + 8 alphanumeric
    IdentifierType.FIGI: re.compile(r'^BBG[A-Z0-9]{9}$'),
    
    # Ticker: 1-5 letters (possibly with suffix like .A)
    IdentifierType.TICKER: re.compile(r'^[A-Z]{1,5}(\.[A-Z])?$'),
}


def detect_identifier_type(value: str) -> tuple[IdentifierType, float]:
    """Detect the type of an identifier.
    
    Returns:
        (IdentifierType, confidence)
    """
    
    value = value.strip().upper()
    
    # Check explicit patterns
    if PATTERNS[IdentifierType.FIGI].match(value):
        return (IdentifierType.FIGI, 1.0)
    
    if PATTERNS[IdentifierType.LEI].match(value) and validate_lei_checksum(value):
        return (IdentifierType.LEI, 1.0)
    
    if PATTERNS[IdentifierType.ISIN].match(value) and validate_isin_checksum(value):
        return (IdentifierType.ISIN, 1.0)
    
    if PATTERNS[IdentifierType.CIK].match(value):
        # Could be CIK or numeric CUSIP; check length
        if len(value.lstrip('0')) <= 7:
            return (IdentifierType.CIK, 0.9)
    
    if PATTERNS[IdentifierType.CUSIP].match(value):
        return (IdentifierType.CUSIP, 0.8)  # Could be other 9-char IDs
    
    if PATTERNS[IdentifierType.SEDOL].match(value):
        return (IdentifierType.SEDOL, 0.8)
    
    if PATTERNS[IdentifierType.TICKER].match(value):
        return (IdentifierType.TICKER, 0.7)  # Tickers are ambiguous
    
    # Default: assume it's a name
    if len(value) > 5 and ' ' in value:
        return (IdentifierType.NAME, 0.6)
    
    return (IdentifierType.UNKNOWN, 0.0)


def validate_lei_checksum(lei: str) -> bool:
    """Validate LEI using ISO 7064 Mod 97-10."""
    # Convert letters to numbers (A=10, B=11, etc.)
    converted = ''
    for char in lei:
        if char.isalpha():
            converted += str(ord(char) - ord('A') + 10)
        else:
            converted += char
    
    return int(converted) % 97 == 1


def validate_isin_checksum(isin: str) -> bool:
    """Validate ISIN using Luhn algorithm."""
    # Convert letters to numbers
    converted = ''
    for char in isin:
        if char.isalpha():
            converted += str(ord(char) - ord('A') + 10)
        else:
            converted += char
    
    # Luhn check
    total = 0
    for i, digit in enumerate(reversed(converted)):
        d = int(digit)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    
    return total % 10 == 0
```

---

## Merge Handling

When entities are merged, old IDs must still resolve.

### Merge Table

```sql
-- From 02_DATA_MODEL.md
CREATE TABLE entity_merges (
    merge_id            CHAR(26) PRIMARY KEY,
    from_entity_id      CHAR(26) NOT NULL,     -- The merged (old) entity
    to_entity_id        CHAR(26) NOT NULL,     -- The surviving entity
    merge_type          VARCHAR(30) NOT NULL,
    reason              TEXT,
    merged_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    effective_date      DATE,
    source              VARCHAR(50) NOT NULL,
    evidence_text       TEXT,
    approved_by         VARCHAR(100),
    ...
);
```

### Follow Redirects

```python
async def follow_redirects(entity: Entity, max_depth: int = 10) -> Entity:
    """Follow merge chain to find current canonical entity.
    
    Handles chains: A → B → C (returns C)
    """
    
    seen = {entity.entity_id}
    current = entity
    
    for _ in range(max_depth):
        # Check if this entity was merged into another
        merge = await db.fetch_one(
            """
            SELECT to_entity_id
            FROM entity_merges
            WHERE from_entity_id = :entity_id
            ORDER BY merged_at DESC
            LIMIT 1
            """,
            {'entity_id': current.entity_id},
        )
        
        if not merge:
            # No merge; this is the current entity
            return current
        
        target_id = merge['to_entity_id']
        
        if target_id in seen:
            # Cycle detected (shouldn't happen)
            raise DataIntegrityError(f"Merge cycle detected: {seen}")
        
        seen.add(target_id)
        
        # Fetch target entity
        current = await db.fetch_one(
            "SELECT * FROM entities WHERE entity_id = :id",
            {'id': target_id},
        )
        
        if not current:
            raise DataIntegrityError(f"Merge target not found: {target_id}")
    
    raise DataIntegrityError(f"Merge chain too deep: {seen}")


# Precomputed view for fast lookups
CREATE VIEW v_entity_canonical AS
WITH RECURSIVE merge_chain AS (
    -- Base: all entities (may or may not be merged)
    SELECT 
        entity_id AS original_id,
        entity_id AS current_id,
        0 AS depth
    FROM entities
    
    UNION
    
    -- Follow merge chain
    SELECT 
        mc.original_id,
        em.to_entity_id AS current_id,
        mc.depth + 1
    FROM merge_chain mc
    JOIN entity_merges em ON em.from_entity_id = mc.current_id
    WHERE mc.depth < 10
)
SELECT DISTINCT ON (original_id)
    original_id,
    current_id,
    original_id != current_id AS was_merged
FROM merge_chain
ORDER BY original_id, depth DESC;
```

### Resolve with Redirect

```python
async def resolve(
    identifier: str,
    follow_merges: bool = True,
) -> ResolvedEntity | None:
    """Main resolution entry point.
    
    Args:
        identifier: Any identifier (auto-detected)
        follow_merges: Whether to follow merge redirects
    """
    
    # Detect identifier type
    id_type, confidence = detect_identifier_type(identifier)
    
    # Route to appropriate resolver
    entity = None
    
    if id_type == IdentifierType.CIK:
        entity = await resolve_cik(identifier)
    elif id_type == IdentifierType.LEI:
        entity = await resolve_lei(identifier)
    elif id_type == IdentifierType.ISIN:
        entity = await resolve_isin(identifier)
    elif id_type == IdentifierType.FIGI:
        entity = await resolve_figi(identifier)
    elif id_type == IdentifierType.TICKER:
        entity = await resolve_ticker(identifier)
    elif id_type == IdentifierType.NAME:
        entity = await resolve_name(identifier)
    else:
        # Try all resolvers
        entity = await try_all_resolvers(identifier)
    
    if entity and follow_merges:
        entity = await follow_redirects(entity)
    
    return entity
```

---

## Match Rules

### Deterministic Rules (High Confidence)

These produce definitive matches:

| Rule | Input | Match Logic | Confidence |
|------|-------|-------------|------------|
| CIK-exact | CIK value | `identifiers.value = :cik AND scheme = 'cik'` | 1.0 |
| LEI-exact | LEI value | `identifiers.value = :lei AND scheme = 'lei'` | 1.0 |
| ISIN-exact | ISIN value | `identifiers.value = :isin AND scheme = 'isin'` | 1.0 |
| FIGI-exact | FIGI value | `identifiers.value = :figi AND scheme = 'figi'` | 1.0 |
| Ticker+MIC+Date | ticker, MIC, date | `listings.ticker = :t AND mic = :m AND valid_from <= :d AND (valid_to IS NULL OR valid_to > :d)` | 0.95 |

### Fuzzy Rules (Lower Confidence)

These require scoring:

| Rule | Input | Match Logic | Confidence |
|------|-------|-------------|------------|
| Ticker-only | ticker (no exchange) | Find all listings with ticker; rank by is_primary | 0.7-0.85 |
| Name-exact | exact name | `aliases.name_normalized = normalize(:name)` | 0.9 |
| Name-FTS | partial name | Full-text search on aliases | 0.6-0.8 |
| Name-fuzzy | similar name | Levenshtein/Jaro-Winkler distance | 0.5-0.7 |

### Manual Review Queue

When confidence is low or multiple matches exist:

```sql
CREATE TABLE resolution_queue (
    queue_id            CHAR(26) PRIMARY KEY,
    
    -- What needs resolution
    input_identifier    VARCHAR(500) NOT NULL,
    input_type          VARCHAR(30),
    context             JSONB,  -- Any hints provided
    
    -- Candidates
    candidate_ids       CHAR(26)[],  -- Entity/Security/Listing IDs
    candidate_scores    DECIMAL(3,2)[],
    
    -- Resolution
    status              VARCHAR(20) DEFAULT 'pending',
    resolved_id         CHAR(26),
    resolution_method   VARCHAR(30),
    resolution_notes    TEXT,
    resolved_by         VARCHAR(100),
    resolved_at         TIMESTAMPTZ,
    
    -- Audit
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    source_system       VARCHAR(50),
    priority            INT DEFAULT 0,
    
    CONSTRAINT chk_status CHECK (status IN (
        'pending',
        'in_progress',
        'resolved',
        'no_match',
        'ambiguous'
    ))
);

-- Index for processing queue
CREATE INDEX idx_queue_pending ON resolution_queue(priority DESC, created_at)
    WHERE status = 'pending';
```

---

## Resolution API

```python
from dataclasses import dataclass
from typing import Optional
from enum import Enum


class ResolutionScope(Enum):
    ENTITY = 'entity'
    SECURITY = 'security'
    LISTING = 'listing'
    AUTO = 'auto'  # Let system decide


@dataclass
class ResolvedEntity:
    """Result of entity resolution."""
    
    # Canonical IDs
    entity_id: str
    security_id: Optional[str] = None
    listing_id: Optional[str] = None
    
    # Entity details
    legal_name: str
    entity_type: str
    status: str
    
    # Key identifiers (convenience)
    cik: Optional[str] = None
    lei: Optional[str] = None
    ticker: Optional[str] = None
    isin: Optional[str] = None
    figi: Optional[str] = None
    
    # Resolution metadata
    resolution_path: str  # How we got here
    confidence: float
    was_merged: bool = False  # Did we follow a redirect?
    original_entity_id: Optional[str] = None  # If merged, what was queried
    
    # Full data access
    all_identifiers: list['Identifier'] = None
    all_securities: list['Security'] = None
    all_listings: list['Listing'] = None


class EntityResolver:
    """Main resolution interface."""
    
    async def resolve(
        self,
        identifier: str,
        scope: ResolutionScope = ResolutionScope.AUTO,
        as_of_date: date | None = None,
        min_confidence: float = 0.7,
        include_securities: bool = True,
        include_listings: bool = True,
    ) -> ResolvedEntity | None:
        """Resolve any identifier to a canonical entity.
        
        Args:
            identifier: The identifier to resolve
            scope: Hint about what kind of identifier this is
            as_of_date: Point-in-time for historical resolution
            min_confidence: Minimum confidence threshold
            include_securities: Include security details in result
            include_listings: Include listing details in result
        """
        ...
    
    async def resolve_batch(
        self,
        identifiers: list[str],
        **kwargs,
    ) -> dict[str, ResolvedEntity | None]:
        """Resolve multiple identifiers efficiently.
        
        Returns dict mapping input → result.
        """
        ...
    
    async def resolve_to_security(
        self,
        identifier: str,
        as_of_date: date | None = None,
    ) -> 'Security' | None:
        """Resolve to security level (not entity).
        
        Use when you specifically need the security, not just the issuer.
        """
        ...
    
    async def resolve_to_listing(
        self,
        identifier: str,
        mic: str | None = None,
        as_of_date: date | None = None,
    ) -> 'Listing' | None:
        """Resolve to listing level.
        
        Use when you need the specific trading venue.
        """
        ...
    
    async def get_resolution_candidates(
        self,
        identifier: str,
        limit: int = 10,
    ) -> list[tuple[ResolvedEntity, float]]:
        """Get all candidates for manual disambiguation.
        
        Returns list of (entity, confidence) tuples.
        """
        ...
    
    async def suggest_identifier(
        self,
        entity_id: str,
        scheme: str,
    ) -> str | None:
        """Suggest an identifier value if we don't have it.
        
        Uses enrichment sources to find missing identifiers.
        """
        ...
```

---

## Resolution Examples

### Example 1: Simple Ticker Resolution

```python
# Input: "AAPL"
result = await resolver.resolve("AAPL")

# Resolution path:
# 1. Detect: TICKER pattern
# 2. Query listings: WHERE ticker='AAPL' AND active
# 3. Found: listing_id=01HYX..., mic=XNAS
# 4. Get security: security_id=01HYX..., ISIN=US0378331005
# 5. Get entity: entity_id=01HYX..., Apple Inc
# 6. Check merges: none
# 7. Return

print(result.legal_name)  # "Apple Inc"
print(result.cik)         # "0000320193"
print(result.confidence)  # 0.85 (ticker without exchange)
```

### Example 2: Ambiguous Ticker (Ticker Reuse)

```python
# Input: "GM" with date 2008-06-01
result = await resolver.resolve("GM", as_of_date=date(2008, 6, 1))

# Resolution path:
# 1. Detect: TICKER pattern
# 2. Query listings: WHERE ticker='GM' AND valid_from <= 2008-06-01 AND (valid_to IS NULL OR valid_to > 2008-06-01)
# 3. Found: listing_id=01HYX8A3 (old GM), valid_from=1916-01-01, valid_to=2009-06-01
# 4. Get security → entity: General Motors Corporation (CIK 40730)
# 5. Return

print(result.legal_name)  # "General Motors Corporation" (OLD company)
print(result.cik)         # "0000040730"

# Now try after bankruptcy
result2 = await resolver.resolve("GM", as_of_date=date(2011, 1, 1))
print(result2.legal_name)  # "General Motors Company" (NEW company)
print(result2.cik)         # "0001467858"  (DIFFERENT!)
```

### Example 3: Merged Entity

```python
# Facebook → Meta merge
# Old CIK still resolves to current entity

result = await resolver.resolve("0001326801")  # Facebook's CIK

# Resolution path:
# 1. Detect: CIK pattern
# 2. Query identifiers: WHERE scheme='cik' AND value='0001326801'
# 3. Found: entity_id=01FACEBOOK...
# 4. Check merges: found merge to entity_id=01META...
# 5. Follow redirect: get Meta Platforms Inc
# 6. Return with was_merged=True

print(result.legal_name)  # "Meta Platforms, Inc."
print(result.was_merged)  # True
print(result.original_entity_id)  # The old Facebook entity ID
```

### Example 4: FIGI → Entity (via Security)

```python
# FIGI is security-scoped, not entity-scoped
result = await resolver.resolve("BBG000B9XRY4")  # Apple FIGI

# Resolution path:
# 1. Detect: FIGI pattern
# 2. Query identifiers: WHERE scheme='figi' AND security_id IS NOT NULL
# 3. Found: security_id=01APPLESTOCK...
# 4. Get security: "Apple Inc Common Stock"
# 5. Get entity via security.issuer_entity_id
# 6. Return with security details

print(result.legal_name)      # "Apple Inc"
print(result.security_id)     # The security ID
print(result.isin)            # "US0378331005"
```

---

## Batch Resolution

For high-volume processing:

```python
async def resolve_batch(
    identifiers: list[str],
    parallel: int = 10,
) -> dict[str, ResolvedEntity | None]:
    """Resolve many identifiers efficiently."""
    
    # Group by detected type for batch queries
    by_type: dict[IdentifierType, list[str]] = defaultdict(list)
    
    for ident in identifiers:
        id_type, _ = detect_identifier_type(ident)
        by_type[id_type].append(ident)
    
    results = {}
    
    # Batch query each type
    if by_type[IdentifierType.CIK]:
        ciks = [cik.zfill(10) for cik in by_type[IdentifierType.CIK]]
        rows = await db.fetch_all(
            """
            SELECT i.value AS cik, e.*
            FROM identifiers i
            JOIN entities e ON e.entity_id = i.entity_id
            WHERE i.scheme = 'cik'
              AND i.value = ANY(:ciks)
            """,
            {'ciks': ciks},
        )
        for row in rows:
            original = next(c for c in by_type[IdentifierType.CIK] 
                          if c.zfill(10) == row['cik'])
            results[original] = build_resolved_entity(row)
    
    # Similarly for ISIN, LEI, etc.
    ...
    
    # Tickers need individual handling (point-in-time)
    for ticker in by_type[IdentifierType.TICKER]:
        results[ticker] = await resolve_ticker(ticker)
    
    # Names need fuzzy matching
    for name in by_type[IdentifierType.NAME]:
        results[name] = await resolve_name(name)
    
    return results
```

---

## Next Documents

- [12_STORAGE_TIERS.md](12_STORAGE_TIERS.md) - Tiered schema implementations
- [13_PYSECEDGAR_PORT.md](13_PYSECEDGAR_PORT.md) - py-sec-edgar integration
