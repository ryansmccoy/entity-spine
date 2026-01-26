# Entity Master v2 - Resolution and Merge Workflows

**Deterministic + fuzzy resolution, identifier detection, merge/redirect handling**

---

## Resolution Overview

Resolution is the process of taking an input identifier and returning the canonical record.

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              RESOLUTION PIPELINE                                         │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                          │
│  INPUT                DETECT              ROUTE               RESOLVE         OUTPUT     │
│  ─────                ──────              ─────               ───────         ──────     │
│                                                                                          │
│  "AAPL"          →   Ticker (0.7)    →   Listing path   →   [Listings]   →   Entity     │
│  "0000320193"    →   CIK (1.0)       →   Entity direct  →   [Entity]     →   Entity     │
│  "US0378331005"  →   ISIN (1.0)      →   Security path  →   [Security]   →   Entity     │
│  "Apple Inc"     →   Name (0.6)      →   Fuzzy match    →   [Candidates] →   Entity?    │
│                                                                                          │
│  All resolution follows merges to return CANONICAL entity                                │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Identifier Detection

### Detection Patterns

```python
import re
from enum import Enum
from dataclasses import dataclass
from typing import Tuple, Optional


class IdentifierType(Enum):
    CIK = 'cik'
    LEI = 'lei'
    ISIN = 'isin'
    CUSIP = 'cusip'
    SEDOL = 'sedol'
    FIGI = 'figi'
    TICKER = 'ticker'
    RIC = 'ric'
    NAME = 'name'
    UNKNOWN = 'unknown'


class IdentifierScope(Enum):
    ENTITY = 'entity'
    SECURITY = 'security'
    LISTING = 'listing'


@dataclass
class DetectionResult:
    identifier_type: IdentifierType
    confidence: float
    scope: IdentifierScope
    normalized_value: str
    hints: dict


# Pattern definitions with validation functions
IDENTIFIER_PATTERNS = {
    # FIGI: BBG + 8 alphanumeric (globally unique per security)
    IdentifierType.FIGI: {
        'pattern': re.compile(r'^BBG[A-Z0-9]{8}[A-Z0-9]$'),
        'scope': IdentifierScope.SECURITY,
        'confidence': 1.0,
        'normalize': lambda x: x.upper(),
    },
    
    # LEI: 20 alphanumeric with checksum
    IdentifierType.LEI: {
        'pattern': re.compile(r'^[A-Z0-9]{18}[0-9]{2}$'),
        'scope': IdentifierScope.ENTITY,
        'confidence': 1.0,  # After checksum validation
        'validate': 'validate_lei_checksum',
        'normalize': lambda x: x.upper(),
    },
    
    # ISIN: 2 letters (country) + 9 alphanumeric + 1 check digit
    IdentifierType.ISIN: {
        'pattern': re.compile(r'^[A-Z]{2}[A-Z0-9]{9}[0-9]$'),
        'scope': IdentifierScope.SECURITY,
        'confidence': 1.0,  # After checksum validation
        'validate': 'validate_isin_checksum',
        'normalize': lambda x: x.upper(),
    },
    
    # CIK: 1-10 digits
    IdentifierType.CIK: {
        'pattern': re.compile(r'^0*[1-9][0-9]{0,9}$'),
        'scope': IdentifierScope.ENTITY,
        'confidence': 0.9,  # Could be confused with other numeric IDs
        'normalize': lambda x: x.zfill(10),
    },
    
    # CUSIP: 9 alphanumeric (US/Canada)
    IdentifierType.CUSIP: {
        'pattern': re.compile(r'^[A-Z0-9]{9}$'),
        'scope': IdentifierScope.SECURITY,
        'confidence': 0.8,  # Similar format to other 9-char IDs
        'normalize': lambda x: x.upper(),
    },
    
    # SEDOL: 7 alphanumeric
    IdentifierType.SEDOL: {
        'pattern': re.compile(r'^[A-Z0-9]{7}$'),
        'scope': IdentifierScope.SECURITY,
        'confidence': 0.8,
        'validate': 'validate_sedol_checksum',
        'normalize': lambda x: x.upper(),
    },
    
    # Ticker: 1-5 letters, optionally with suffix (.A, .B)
    IdentifierType.TICKER: {
        'pattern': re.compile(r'^[A-Z]{1,5}(\.[A-Z])?$'),
        'scope': IdentifierScope.LISTING,
        'confidence': 0.7,  # Ambiguous without exchange
        'normalize': lambda x: x.upper(),
    },
    
    # RIC: Symbol with exchange suffix (e.g., AAPL.O, 7203.T)
    IdentifierType.RIC: {
        'pattern': re.compile(r'^[A-Z0-9]{1,10}\.[A-Z]{1,2}$'),
        'scope': IdentifierScope.LISTING,
        'confidence': 0.85,
        'normalize': lambda x: x.upper(),
    },
}


def detect_identifier_type(value: str) -> DetectionResult:
    """
    Detect the type of identifier from a string value.
    
    Returns DetectionResult with type, confidence, scope, and normalized value.
    """
    value = value.strip()
    value_upper = value.upper()
    
    # Try patterns in order of specificity
    checks = [
        IdentifierType.FIGI,      # Most specific (BBG prefix)
        IdentifierType.LEI,       # Specific format + checksum
        IdentifierType.ISIN,      # Specific format + checksum
        IdentifierType.RIC,       # Has exchange suffix
        IdentifierType.CIK,       # Numeric
        IdentifierType.CUSIP,     # 9 alphanumeric
        IdentifierType.SEDOL,     # 7 alphanumeric
        IdentifierType.TICKER,    # Short alphabetic
    ]
    
    for id_type in checks:
        spec = IDENTIFIER_PATTERNS[id_type]
        
        if spec['pattern'].match(value_upper):
            confidence = spec['confidence']
            
            # Run validation if specified
            if 'validate' in spec:
                validator = globals().get(spec['validate'])
                if validator and not validator(value_upper):
                    continue  # Checksum failed, try next type
                confidence = 1.0  # Checksum passed, high confidence
            
            normalized = spec['normalize'](value)
            
            return DetectionResult(
                identifier_type=id_type,
                confidence=confidence,
                scope=spec['scope'],
                normalized_value=normalized,
                hints={},
            )
    
    # Default: assume it's a name
    if len(value) > 5:
        return DetectionResult(
            identifier_type=IdentifierType.NAME,
            confidence=0.5,
            scope=IdentifierScope.ENTITY,
            normalized_value=normalize_company_name(value),
            hints={},
        )
    
    return DetectionResult(
        identifier_type=IdentifierType.UNKNOWN,
        confidence=0.0,
        scope=IdentifierScope.ENTITY,
        normalized_value=value,
        hints={},
    )


def validate_lei_checksum(lei: str) -> bool:
    """Validate LEI using ISO 7064 Mod 97-10."""
    if len(lei) != 20:
        return False
    
    # Convert letters to numbers (A=10, B=11, etc.)
    converted = ''
    for char in lei:
        if char.isalpha():
            converted += str(ord(char) - ord('A') + 10)
        else:
            converted += char
    
    try:
        return int(converted) % 97 == 1
    except ValueError:
        return False


def validate_isin_checksum(isin: str) -> bool:
    """Validate ISIN using Luhn algorithm."""
    if len(isin) != 12:
        return False
    
    # Convert letters to numbers
    converted = ''
    for char in isin:
        if char.isalpha():
            converted += str(ord(char) - ord('A') + 10)
        else:
            converted += char
    
    # Luhn algorithm
    total = 0
    for i, digit in enumerate(reversed(converted)):
        d = int(digit)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    
    return total % 10 == 0


def validate_sedol_checksum(sedol: str) -> bool:
    """Validate SEDOL checksum."""
    if len(sedol) != 7:
        return False
    
    weights = [1, 3, 1, 7, 3, 9, 1]
    total = 0
    
    for i, char in enumerate(sedol):
        if char.isdigit():
            val = int(char)
        elif char.isalpha():
            val = ord(char) - ord('A') + 10
        else:
            return False
        total += val * weights[i]
    
    return total % 10 == 0


def normalize_company_name(name: str) -> str:
    """Normalize company name for matching."""
    import unicodedata
    
    # Lowercase
    name = name.lower()
    
    # Remove accents
    name = unicodedata.normalize('NFKD', name)
    name = ''.join(c for c in name if not unicodedata.combining(c))
    
    # Remove common suffixes
    suffixes = [
        ' inc', ' inc.', ' incorporated', ' corp', ' corp.', ' corporation',
        ' llc', ' l.l.c.', ' ltd', ' ltd.', ' limited', ' plc', ' p.l.c.',
        ' co', ' co.', ' company', ' & co', ' and company',
        ' sa', ' s.a.', ' ag', ' gmbh', ' bv', ' nv',
    ]
    for suffix in suffixes:
        if name.endswith(suffix):
            name = name[:-len(suffix)]
            break
    
    # Remove punctuation and extra whitespace
    name = re.sub(r'[^\w\s]', ' ', name)
    name = re.sub(r'\s+', ' ', name).strip()
    
    return name
```

---

## Resolution Paths

### Identifier Strength Ranking

| Tier | Identifiers | Confidence | Scope | Notes |
|------|-------------|------------|-------|-------|
| **1** | CIK, LEI | 1.0 | Entity | Authoritative, unique |
| **1** | ISIN, FIGI | 1.0 | Security | Authoritative, unique |
| **2** | CUSIP, SEDOL | 0.95 | Security | Reliable with checksum |
| **2** | PermID (Org) | 0.95 | Entity | Reliable vendor ID |
| **3** | Ticker + MIC + Date | 0.9 | Listing | Needs all three |
| **3** | RIC | 0.85 | Listing | Includes exchange |
| **4** | Ticker only | 0.7 | Listing | Ambiguous |
| **5** | Name (exact) | 0.8 | Entity | Exact alias match |
| **5** | Name (fuzzy) | 0.5-0.7 | Entity | Scoring needed |

### Path 1: CIK → Entity (Direct)

```python
async def resolve_cik(cik: str, follow_merges: bool = True) -> Optional[ResolvedEntity]:
    """
    Resolve SEC CIK directly to entity.
    
    CIK is entity-scoped and authoritative for SEC filers.
    """
    # Normalize to 10-digit zero-padded
    cik_normalized = cik.zfill(10)
    
    # Lookup in identifiers table (entity-scoped)
    result = await db.fetch_one("""
        SELECT i.entity_id
        FROM identifiers i
        WHERE i.scheme = 'cik'
          AND i.value = :cik
          AND i.entity_id IS NOT NULL
    """, {'cik': cik_normalized})
    
    if not result:
        return None
    
    entity_id = result['entity_id']
    
    # Follow merges if requested
    if follow_merges:
        entity_id = await get_canonical_entity_id(entity_id)
    
    # Load full entity
    entity = await load_entity(entity_id)
    
    return ResolvedEntity(
        entity=entity,
        resolution_path='cik -> entity',
        confidence=1.0,
        was_merged=entity_id != result['entity_id'],
    )
```

### Path 2: Ticker → Listing → Security → Entity

```python
async def resolve_ticker(
    ticker: str,
    mic: Optional[str] = None,
    as_of_date: Optional[date] = None,
    follow_merges: bool = True,
) -> Union[ResolvedEntity, List[ResolvedEntity], None]:
    """
    Resolve ticker to entity via listing → security → entity chain.
    
    Args:
        ticker: Stock symbol (e.g., "AAPL")
        mic: Market Identifier Code (e.g., "XNAS" for NASDAQ)
        as_of_date: Point-in-time date (for ticker reuse scenarios)
        follow_merges: Whether to follow merge redirects
    
    Returns:
        Single ResolvedEntity if unambiguous,
        List of candidates if ambiguous (no MIC provided),
        None if not found.
    """
    ticker = ticker.upper()
    as_of = as_of_date or date.today()
    
    # Build query with temporal awareness
    query = """
        SELECT l.listing_id, l.security_id, l.mic, l.is_primary,
               l.valid_from, l.valid_to
        FROM listings l
        WHERE l.ticker = :ticker
          AND l.status = 'active'
          AND l.valid_from <= :as_of
          AND (l.valid_to IS NULL OR l.valid_to > :as_of)
    """
    params = {'ticker': ticker, 'as_of': as_of}
    
    if mic:
        query += " AND l.mic = :mic"
        params['mic'] = mic.upper()
    
    listings = await db.fetch_all(query, params)
    
    if not listings:
        return None
    
    # Single match - resolve fully
    if len(listings) == 1:
        return await _resolve_from_listing(
            listings[0], 
            confidence=0.9 if mic else 0.8,
            follow_merges=follow_merges,
        )
    
    # Multiple matches without MIC - ambiguous
    if not mic:
        # Try to find primary listing
        primary = [l for l in listings if l['is_primary']]
        if len(primary) == 1:
            return await _resolve_from_listing(
                primary[0],
                confidence=0.85,  # Slightly lower - assumed primary
                follow_merges=follow_merges,
            )
        
        # Return all candidates
        candidates = []
        for listing in listings[:5]:  # Limit to 5
            resolved = await _resolve_from_listing(
                listing,
                confidence=0.7,
                follow_merges=follow_merges,
            )
            candidates.append(resolved)
        
        return candidates
    
    # Multiple matches WITH MIC - data quality issue
    # Take the one marked as primary, or most recent
    primary = [l for l in listings if l['is_primary']]
    if primary:
        return await _resolve_from_listing(primary[0], 0.85, follow_merges)
    
    # Fallback: most recent valid_from
    latest = max(listings, key=lambda x: x['valid_from'])
    return await _resolve_from_listing(latest, 0.75, follow_merges)


async def _resolve_from_listing(
    listing: dict,
    confidence: float,
    follow_merges: bool,
) -> ResolvedEntity:
    """Complete resolution from listing record."""
    
    listing_id = listing['listing_id']
    security_id = listing['security_id']
    
    # Follow listing merges
    if follow_merges:
        listing_id = await get_canonical_listing_id(listing_id)
        # Re-fetch if changed
        if listing_id != listing['listing_id']:
            listing = await db.fetch_one(
                "SELECT * FROM listings WHERE listing_id = :id",
                {'id': listing_id}
            )
            security_id = listing['security_id']
    
    # Get security
    security = await db.fetch_one(
        "SELECT * FROM securities WHERE security_id = :id",
        {'id': security_id}
    )
    
    # Follow security merges
    if follow_merges:
        canonical_sec_id = await get_canonical_security_id(security_id)
        if canonical_sec_id != security_id:
            security = await db.fetch_one(
                "SELECT * FROM securities WHERE security_id = :id",
                {'id': canonical_sec_id}
            )
    
    # Get entity
    entity_id = security['issuer_entity_id']
    
    # Follow entity merges
    if follow_merges:
        entity_id = await get_canonical_entity_id(entity_id)
    
    entity = await load_entity(entity_id)
    
    return ResolvedEntity(
        entity=entity,
        security=security,
        listing=listing,
        resolution_path='ticker -> listing -> security -> entity',
        confidence=confidence,
    )
```

### Path 3: ISIN → Security → Entity

```python
async def resolve_isin(isin: str, follow_merges: bool = True) -> Optional[ResolvedEntity]:
    """
    Resolve ISIN to entity via security.
    
    ISIN is security-scoped and globally unique.
    """
    isin = isin.upper()
    
    # Validate checksum
    if not validate_isin_checksum(isin):
        raise InvalidIdentifierError(f"Invalid ISIN checksum: {isin}")
    
    # Lookup in identifiers (security-scoped)
    result = await db.fetch_one("""
        SELECT i.security_id
        FROM identifiers i
        WHERE i.scheme = 'isin'
          AND i.value = :isin
          AND i.security_id IS NOT NULL
          AND (i.valid_to IS NULL OR i.valid_to > CURRENT_DATE)
    """, {'isin': isin})
    
    if not result:
        return None
    
    security_id = result['security_id']
    
    if follow_merges:
        security_id = await get_canonical_security_id(security_id)
    
    security = await db.fetch_one(
        "SELECT * FROM securities WHERE security_id = :id",
        {'id': security_id}
    )
    
    entity_id = security['issuer_entity_id']
    if follow_merges:
        entity_id = await get_canonical_entity_id(entity_id)
    
    entity = await load_entity(entity_id)
    
    return ResolvedEntity(
        entity=entity,
        security=security,
        resolution_path='isin -> security -> entity',
        confidence=1.0,
    )
```

### Path 4: FIGI → Security → Entity

```python
async def resolve_figi(figi: str, follow_merges: bool = True) -> Optional[ResolvedEntity]:
    """
    Resolve Bloomberg FIGI to entity via security.
    
    CRITICAL: FIGI is SECURITY-scoped, NOT entity-scoped!
    """
    figi = figi.upper()
    
    # Validate format
    if not figi.startswith('BBG') or len(figi) != 12:
        raise InvalidIdentifierError(f"Invalid FIGI format: {figi}")
    
    # Check all FIGI types (standard, composite, share class)
    result = await db.fetch_one("""
        SELECT i.security_id
        FROM identifiers i
        WHERE i.scheme IN ('figi', 'composite_figi', 'share_class_figi')
          AND i.value = :figi
          AND i.security_id IS NOT NULL
    """, {'figi': figi})
    
    if not result:
        return None
    
    security_id = result['security_id']
    
    if follow_merges:
        security_id = await get_canonical_security_id(security_id)
    
    security = await db.fetch_one(
        "SELECT * FROM securities WHERE security_id = :id",
        {'id': security_id}
    )
    
    entity_id = security['issuer_entity_id']
    if follow_merges:
        entity_id = await get_canonical_entity_id(entity_id)
    
    entity = await load_entity(entity_id)
    
    return ResolvedEntity(
        entity=entity,
        security=security,
        resolution_path='figi -> security -> entity',
        confidence=1.0,
    )
```

### Path 5: Name → Entity (Fuzzy)

```python
async def resolve_name(
    name: str,
    entity_type: Optional[str] = None,
    context_hints: Optional[dict] = None,
    min_confidence: float = 0.7,
) -> Union[ResolvedEntity, List[ResolvedEntity], None]:
    """
    Resolve entity by name with fuzzy matching.
    
    Args:
        name: Company/entity name
        entity_type: Filter by type (COMPANY, FUND, etc.)
        context_hints: Additional context for disambiguation
            - sic_code: Industry code
            - jurisdiction: Country/state
            - mentioned_with: Other entities mentioned together
        min_confidence: Minimum confidence threshold
    
    Returns:
        Single ResolvedEntity if high confidence match,
        List of candidates if ambiguous,
        None if no good matches.
    """
    hints = context_hints or {}
    
    # Normalize the input name
    normalized = normalize_company_name(name)
    
    # Step 1: Try exact alias match
    exact_matches = await db.fetch_all("""
        SELECT a.entity_id, a.name, a.alias_type, e.status
        FROM entity_aliases a
        JOIN entities e ON e.entity_id = a.entity_id
        WHERE a.name_normalized = :normalized
          AND e.status IN ('active', 'provisional')
    """, {'normalized': normalized})
    
    if len(exact_matches) == 1:
        entity = await load_entity(exact_matches[0]['entity_id'])
        return ResolvedEntity(
            entity=entity,
            resolution_path='name (exact) -> alias -> entity',
            confidence=0.95,
        )
    
    if len(exact_matches) > 1:
        # Multiple exact matches - use hints to disambiguate
        scored = await _score_candidates_with_hints(exact_matches, hints)
        if scored[0][1] >= 0.9 and scored[0][1] - scored[1][1] > 0.1:
            entity = await load_entity(scored[0][0]['entity_id'])
            return ResolvedEntity(
                entity=entity,
                resolution_path='name (exact + hints) -> entity',
                confidence=scored[0][1],
            )
    
    # Step 2: Full-text search
    fts_results = await db.fetch_all("""
        SELECT a.entity_id, a.name,
               ts_rank(to_tsvector('english', a.name), 
                       plainto_tsquery('english', :name)) AS rank
        FROM entity_aliases a
        JOIN entities e ON e.entity_id = a.entity_id
        WHERE to_tsvector('english', a.name) @@ plainto_tsquery('english', :name)
          AND e.status IN ('active', 'provisional')
        ORDER BY rank DESC
        LIMIT 20
    """, {'name': name})
    
    if not fts_results:
        return None
    
    # Step 3: Score with fuzzy matching
    scored_candidates = []
    
    for result in fts_results:
        score = calculate_name_similarity(name, result['name'])
        
        # Apply hint bonuses/penalties
        if hints:
            score = await _apply_hints_to_score(
                result['entity_id'], score, hints
            )
        
        if score >= min_confidence:
            scored_candidates.append((result, score))
    
    if not scored_candidates:
        return None
    
    # Sort by score
    scored_candidates.sort(key=lambda x: x[1], reverse=True)
    
    best = scored_candidates[0]
    
    # High confidence single match
    if best[1] >= 0.9:
        entity = await load_entity(best[0]['entity_id'])
        return ResolvedEntity(
            entity=entity,
            resolution_path='name (fuzzy) -> entity',
            confidence=best[1],
        )
    
    # Check if clear winner
    if len(scored_candidates) >= 2:
        second = scored_candidates[1]
        if best[1] - second[1] >= 0.15:  # Clear separation
            entity = await load_entity(best[0]['entity_id'])
            return ResolvedEntity(
                entity=entity,
                resolution_path='name (fuzzy) -> entity',
                confidence=best[1],
            )
    
    # Return candidates for manual review
    candidates = []
    for result, score in scored_candidates[:5]:
        entity = await load_entity(result['entity_id'])
        candidates.append(ResolvedEntity(
            entity=entity,
            resolution_path='name (fuzzy) -> entity',
            confidence=score,
        ))
    
    return candidates


def calculate_name_similarity(query: str, candidate: str) -> float:
    """Calculate similarity score between two names."""
    from difflib import SequenceMatcher
    
    # Normalize both
    q_norm = normalize_company_name(query)
    c_norm = normalize_company_name(candidate)
    
    # Direct ratio
    ratio = SequenceMatcher(None, q_norm, c_norm).ratio()
    
    # Token overlap bonus
    q_tokens = set(q_norm.split())
    c_tokens = set(c_norm.split())
    
    if q_tokens and c_tokens:
        overlap = len(q_tokens & c_tokens) / len(q_tokens | c_tokens)
        ratio = 0.7 * ratio + 0.3 * overlap
    
    return ratio


async def _apply_hints_to_score(
    entity_id: str,
    base_score: float,
    hints: dict,
) -> float:
    """Apply context hints to adjust match score."""
    
    score = base_score
    entity = await load_entity(entity_id)
    
    # SIC code match
    if hints.get('sic_code') and entity.sic_code:
        if hints['sic_code'] == entity.sic_code:
            score += 0.1  # Exact SIC match
        elif hints['sic_code'][:2] == entity.sic_code[:2]:
            score += 0.05  # Same industry group
    
    # Jurisdiction match
    if hints.get('jurisdiction'):
        if hints['jurisdiction'] == entity.jurisdiction_country:
            score += 0.05
    
    # Is public (if looking for SEC filer)
    if hints.get('is_public') and entity.is_public:
        score += 0.05
    
    return min(score, 1.0)  # Cap at 1.0
```

---

## Merge/Redirect Handling

### Following Redirect Chains

```python
async def get_canonical_entity_id(entity_id: str, max_depth: int = 10) -> str:
    """
    Follow entity merge chain to find current canonical entity.
    
    Uses the precomputed v_entity_canonical view for efficiency.
    Falls back to recursive lookup if view is stale.
    """
    # Fast path: use materialized view
    result = await db.fetch_one("""
        SELECT canonical_id
        FROM v_entity_canonical
        WHERE original_id = :id
    """, {'id': entity_id})
    
    if result:
        return result['canonical_id']
    
    # Fallback: recursive lookup
    return await _follow_entity_merges_recursive(entity_id, max_depth)


async def _follow_entity_merges_recursive(
    entity_id: str, 
    max_depth: int,
    seen: Optional[set] = None,
) -> str:
    """Recursively follow merge chain."""
    
    if seen is None:
        seen = set()
    
    if entity_id in seen:
        raise DataIntegrityError(f"Merge cycle detected: {seen}")
    
    seen.add(entity_id)
    
    if len(seen) > max_depth:
        raise DataIntegrityError(f"Merge chain too deep: {seen}")
    
    # Check for merge
    merge = await db.fetch_one("""
        SELECT to_entity_id
        FROM entity_merges
        WHERE from_entity_id = :id
        ORDER BY merged_at DESC
        LIMIT 1
    """, {'id': entity_id})
    
    if not merge:
        return entity_id  # This is the canonical ID
    
    # Recurse
    return await _follow_entity_merges_recursive(
        merge['to_entity_id'], 
        max_depth, 
        seen
    )


# Similar functions for securities and listings
async def get_canonical_security_id(security_id: str) -> str:
    result = await db.fetch_one("""
        SELECT canonical_id FROM v_security_canonical WHERE original_id = :id
    """, {'id': security_id})
    return result['canonical_id'] if result else security_id


async def get_canonical_listing_id(listing_id: str) -> str:
    result = await db.fetch_one("""
        SELECT canonical_id FROM v_listing_canonical WHERE original_id = :id
    """, {'id': listing_id})
    return result['canonical_id'] if result else listing_id
```

### Creating Merges

```python
@dataclass
class MergeRequest:
    from_entity_id: str
    to_entity_id: str
    merge_type: str
    reason: str
    evidence_text: Optional[str] = None
    effective_date: Optional[date] = None


async def merge_entities(
    request: MergeRequest,
    source_system: str,
    approved_by: Optional[str] = None,
) -> str:
    """
    Merge one entity into another.
    
    - Creates merge record
    - Updates entity status to 'merged'
    - Transfers identifiers, aliases, relationships to target
    - Returns merge_id
    """
    
    # Validate: both entities exist
    from_entity = await load_entity(request.from_entity_id)
    to_entity = await load_entity(request.to_entity_id)
    
    if not from_entity or not to_entity:
        raise EntityNotFoundError("Both entities must exist")
    
    # Validate: source not already merged
    if from_entity.status == 'merged':
        # Get current canonical
        canonical_id = await get_canonical_entity_id(request.from_entity_id)
        if canonical_id == request.to_entity_id:
            return None  # Already merged to this target
        raise InvalidMergeError(f"Entity already merged to {canonical_id}")
    
    # Validate: no circular merge
    to_canonical = await get_canonical_entity_id(request.to_entity_id)
    if to_canonical == request.from_entity_id:
        raise InvalidMergeError("Circular merge detected")
    
    merge_id = generate_ulid()
    
    async with db.transaction():
        # Create merge record
        await db.execute("""
            INSERT INTO entity_merges (
                merge_id, from_entity_id, to_entity_id,
                merge_type, reason, evidence_text,
                effective_date, source_system, approved_by
            ) VALUES (
                :merge_id, :from_id, :to_id,
                :merge_type, :reason, :evidence,
                :effective_date, :source, :approved_by
            )
        """, {
            'merge_id': merge_id,
            'from_id': request.from_entity_id,
            'to_id': request.to_entity_id,
            'merge_type': request.merge_type,
            'reason': request.reason,
            'evidence': request.evidence_text,
            'effective_date': request.effective_date,
            'source': source_system,
            'approved_by': approved_by,
        })
        
        # Update source entity status
        await db.execute("""
            UPDATE entities
            SET status = 'merged', updated_at = NOW()
            WHERE entity_id = :id
        """, {'id': request.from_entity_id})
        
        # Transfer identifiers (keep on source but add to target)
        # Note: We keep identifiers on source for historical resolution
        
        # Transfer aliases
        await db.execute("""
            INSERT INTO entity_aliases (
                alias_id, entity_id, alias_type, name, name_normalized,
                source_system, confidence, created_at
            )
            SELECT 
                :new_prefix || substr(alias_id, 1, 20),
                :to_id, alias_type, name, name_normalized,
                'merge_transfer', confidence, NOW()
            FROM entity_aliases
            WHERE entity_id = :from_id
              AND name_normalized NOT IN (
                  SELECT name_normalized FROM entity_aliases WHERE entity_id = :to_id
              )
        """, {
            'new_prefix': generate_ulid()[:6],
            'to_id': request.to_entity_id,
            'from_id': request.from_entity_id,
        })
        
        # Update relationships (point to new entity)
        await db.execute("""
            UPDATE entity_relationships
            SET source_entity_id = :to_id, updated_at = NOW()
            WHERE source_entity_id = :from_id
        """, {'to_id': request.to_entity_id, 'from_id': request.from_entity_id})
        
        await db.execute("""
            UPDATE entity_relationships
            SET target_entity_id = :to_id, updated_at = NOW()
            WHERE target_entity_id = :from_id
        """, {'to_id': request.to_entity_id, 'from_id': request.from_entity_id})
        
        # Refresh canonical view
        await db.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY v_entity_canonical")
    
    return merge_id
```

---

## Unified Resolution Entry Point

```python
async def resolve(
    identifier: str,
    *,
    scope: Optional[IdentifierScope] = None,
    as_of_date: Optional[date] = None,
    follow_merges: bool = True,
    min_confidence: float = 0.7,
    context_hints: Optional[dict] = None,
) -> Union[ResolvedEntity, List[ResolvedEntity], None]:
    """
    Main resolution entry point - detects identifier type and routes appropriately.
    
    Args:
        identifier: Any identifier string (CIK, ticker, ISIN, name, etc.)
        scope: Optional scope hint (entity, security, listing)
        as_of_date: Point-in-time for historical resolution
        follow_merges: Whether to follow merge redirects
        min_confidence: Minimum confidence threshold
        context_hints: Additional context for disambiguation
    
    Returns:
        ResolvedEntity if single match found,
        List[ResolvedEntity] if ambiguous,
        None if not found.
    """
    
    # Detect identifier type
    detection = detect_identifier_type(identifier)
    
    # Route based on detected type
    if detection.identifier_type == IdentifierType.CIK:
        return await resolve_cik(
            detection.normalized_value, 
            follow_merges=follow_merges
        )
    
    elif detection.identifier_type == IdentifierType.LEI:
        return await resolve_lei(
            detection.normalized_value,
            follow_merges=follow_merges
        )
    
    elif detection.identifier_type == IdentifierType.ISIN:
        return await resolve_isin(
            detection.normalized_value,
            follow_merges=follow_merges
        )
    
    elif detection.identifier_type == IdentifierType.FIGI:
        return await resolve_figi(
            detection.normalized_value,
            follow_merges=follow_merges
        )
    
    elif detection.identifier_type == IdentifierType.TICKER:
        # Extract MIC from hints if provided
        mic = None
        if context_hints:
            mic = context_hints.get('mic') or context_hints.get('exchange')
        
        return await resolve_ticker(
            detection.normalized_value,
            mic=mic,
            as_of_date=as_of_date,
            follow_merges=follow_merges
        )
    
    elif detection.identifier_type == IdentifierType.RIC:
        return await resolve_ric(
            detection.normalized_value,
            as_of_date=as_of_date,
            follow_merges=follow_merges
        )
    
    elif detection.identifier_type == IdentifierType.NAME:
        return await resolve_name(
            detection.normalized_value,
            context_hints=context_hints,
            min_confidence=min_confidence
        )
    
    else:
        # Unknown type - try all resolvers
        return await resolve_unknown(
            identifier,
            follow_merges=follow_merges,
            min_confidence=min_confidence
        )


async def resolve_batch(
    identifiers: List[str],
    **kwargs,
) -> Dict[str, Union[ResolvedEntity, List[ResolvedEntity], None]]:
    """
    Batch resolution for efficiency.
    
    Groups identifiers by type and resolves in bulk where possible.
    """
    results = {}
    
    # Group by detected type
    by_type: Dict[IdentifierType, List[Tuple[str, str]]] = {}
    
    for ident in identifiers:
        detection = detect_identifier_type(ident)
        if detection.identifier_type not in by_type:
            by_type[detection.identifier_type] = []
        by_type[detection.identifier_type].append(
            (ident, detection.normalized_value)
        )
    
    # Resolve each group
    for id_type, group in by_type.items():
        if id_type == IdentifierType.CIK:
            batch_results = await resolve_ciks_batch(
                [norm for _, norm in group],
                **kwargs
            )
            for (orig, norm), result in zip(group, batch_results):
                results[orig] = result
        
        # ... similar for other types
        
        else:
            # Fall back to individual resolution
            for orig, norm in group:
                results[orig] = await resolve(orig, **kwargs)
    
    return results
```

---

## Resolution Queue (Manual Review)

```python
async def queue_for_review(
    mention_id: str,
    reason: str,
    candidates: List[Tuple[str, float]],  # (entity_id, score)
) -> str:
    """Add a mention to the manual review queue."""
    
    queue_id = generate_ulid()
    
    await db.execute("""
        INSERT INTO resolution_queue (
            queue_id, mention_id, queue_reason,
            candidate_entity_ids, candidate_scores,
            status, priority, created_at
        ) VALUES (
            :queue_id, :mention_id, :reason,
            :candidates, :scores,
            'pending', :priority, NOW()
        )
    """, {
        'queue_id': queue_id,
        'mention_id': mention_id,
        'reason': reason,
        'candidates': [c[0] for c in candidates],
        'scores': [c[1] for c in candidates],
        'priority': calculate_priority(reason, len(candidates)),
    })
    
    return queue_id


async def resolve_from_queue(
    queue_id: str,
    resolved_entity_id: str,
    resolution_method: str,
    resolved_by: str,
    notes: Optional[str] = None,
) -> None:
    """Manually resolve an item from the queue."""
    
    async with db.transaction():
        # Update queue record
        await db.execute("""
            UPDATE resolution_queue
            SET status = 'resolved',
                resolved_entity_id = :entity_id,
                resolution_method = :method,
                resolved_by = :by,
                resolution_notes = :notes,
                resolved_at = NOW()
            WHERE queue_id = :queue_id
        """, {
            'queue_id': queue_id,
            'entity_id': resolved_entity_id,
            'method': resolution_method,
            'by': resolved_by,
            'notes': notes,
        })
        
        # Get mention_id
        queue = await db.fetch_one(
            "SELECT mention_id FROM resolution_queue WHERE queue_id = :id",
            {'id': queue_id}
        )
        
        # Update mention
        await db.execute("""
            UPDATE mentions
            SET resolved_entity_id = :entity_id,
                resolution_status = 'resolved',
                resolved_at = NOW()
            WHERE mention_id = :mention_id
        """, {
            'entity_id': resolved_entity_id,
            'mention_id': queue['mention_id'],
        })
```

---

## Next Document

→ [03_VENDOR_CROSSWALK_AND_CONFLICTS.md](03_VENDOR_CROSSWALK_AND_CONFLICTS.md) - Vendor ID mapping and conflict handling
