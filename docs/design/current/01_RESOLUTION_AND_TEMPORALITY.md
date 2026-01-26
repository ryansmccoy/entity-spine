# Resolution & Temporality

**Companion to Unified Data Model v2.2**

> This document defines how entityspine resolves identifiers to entities,  
> handles ticker reuse, temporal queries, and returns ranked candidates.

---

## Table of Contents

1. [Resolution Philosophy](#resolution-philosophy)
2. [Resolution Paths](#resolution-paths)
3. [Ticker Reuse & Temporality](#ticker-reuse--temporality)
4. [Scoring & Ranking](#scoring--ranking)
5. [Ambiguity Handling](#ambiguity-handling)
6. [Resolution API](#resolution-api)
7. [Example Flows](#example-flows)

---

## Resolution Philosophy

### Core Principles

```
┌────────────────────────────────────────────────────────────────────────────┐
│                         RESOLUTION PRINCIPLES                               │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  1. NEVER GUESS SILENTLY                                                   │
│     • If ambiguous, return multiple candidates with scores                 │
│     • Caller decides threshold for "good enough"                           │
│                                                                            │
│  2. TEMPORAL CONTEXT MATTERS                                               │
│     • "AAPL" means different things in 1985 vs 2025                        │
│     • Always accept `as_of` parameter                                      │
│     • Default to NOW, but support historical queries                       │
│                                                                            │
│  3. FOLLOW REDIRECTS TRANSPARENTLY                                         │
│     • Merged entities return canonical target                              │
│     • Include redirect_chain in response                                   │
│     • Caller knows if resolution followed merges                           │
│                                                                            │
│  4. PRESERVE EVIDENCE                                                      │
│     • Response includes claim IDs that support match                       │
│     • Enables audit and dispute resolution                                 │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
```

### Resolution vs Lookup

| Operation | Input | Output | Handles Ambiguity |
|-----------|-------|--------|-------------------|
| **resolve()** | Any identifier string | Ranked candidates | Yes |
| **get()** | Known entity_id | Single entity | No (exact lookup) |
| **get_by_cik()** | CIK string | Single entity or None | No (scheme-specific) |

---

## Resolution Paths

### Path Diagram

```
                              ┌─────────────────┐
                              │  resolve(query) │
                              └────────┬────────┘
                                       │
                          ┌────────────┼────────────┐
                          │            │            │
                          ▼            ▼            ▼
                    ┌──────────┐ ┌──────────┐ ┌──────────┐
                    │  Detect  │ │  Detect  │ │  Detect  │
                    │  Scheme  │ │  Ticker  │ │   Name   │
                    │  (CIK,   │ │ Pattern  │ │  Fuzzy   │
                    │   LEI)   │ │          │ │  Match   │
                    └────┬─────┘ └────┬─────┘ └────┬─────┘
                         │            │            │
                         ▼            ▼            ▼
                    ┌──────────┐ ┌──────────┐ ┌──────────┐
                    │  Claims  │ │ Listings │ │  Aliases │
                    │   Table  │ │  Table   │ │  Table   │
                    └────┬─────┘ └────┬─────┘ └────┬─────┘
                         │            │            │
                         │            │   ┌────────┘
                         │            │   │
                         │            ▼   ▼
                         │      ┌──────────────┐
                         │      │  Securities  │
                         │      │    Table     │
                         │      └──────┬───────┘
                         │             │
                         ▼             ▼
                    ┌────────────────────────┐
                    │     Entities Table     │
                    └────────────┬───────────┘
                                 │
                                 ▼
                    ┌────────────────────────┐
                    │   Follow Redirects     │
                    │   (if merged)          │
                    └────────────┬───────────┘
                                 │
                                 ▼
                    ┌────────────────────────┐
                    │   Rank Candidates      │
                    │   Return Top N         │
                    └────────────────────────┘
```

### Path: CIK → Entity (Direct)

```python
def resolve_cik(cik: str, as_of: date | None = None) -> list[ResolutionCandidate]:
    """
    CIK → Entity (direct path, no Security/Listing involved)
    
    CIK is an entity-scoped identifier, so:
    identifier_claims WHERE scheme='cik' → entity_id directly
    """
    cik_normalized = cik.zfill(10)
    
    # Find active claims for this CIK
    claims = query("""
        SELECT ic.entity_id, ic.confidence, ic.claim_id, e.primary_name, e.status,
               e.merged_into_id
        FROM identifier_claims ic
        JOIN entities e ON e.entity_id = ic.entity_id
        WHERE ic.scheme = 'cik'
          AND ic.value = :cik
          AND ic.status = 'active'
          AND (ic.valid_to IS NULL OR ic.valid_to > :as_of)
    """, cik=cik_normalized, as_of=as_of or date.today())
    
    candidates = []
    for row in claims:
        entity_id, redirect_chain = follow_redirects(row.entity_id)
        candidates.append(ResolutionCandidate(
            entity_id=entity_id,
            score=row.confidence,
            match_type='exact',
            matched_value=cik_normalized,
            matched_scheme='cik',
            evidence=[row.claim_id],
            redirect_chain=redirect_chain if len(redirect_chain) > 1 else None
        ))
    
    return sorted(candidates, key=lambda c: c.score, reverse=True)
```

### Path: Ticker → Listing → Security → Entity

```python
def resolve_ticker(
    ticker: str, 
    mic: str | None = None,
    as_of: date | None = None
) -> list[ResolutionCandidate]:
    """
    Ticker → Listing → Security → Entity (full chain)
    
    Ticker is listing-scoped, must traverse the hierarchy.
    """
    as_of = as_of or date.today()
    ticker_upper = ticker.strip().upper()
    
    # Find listings valid at as_of date
    listings = query("""
        SELECT 
            l.listing_id, l.ticker, l.mic, l.is_primary, l.valid_from, l.valid_to,
            s.security_id, s.security_type, s.name AS security_name,
            e.entity_id, e.primary_name, e.status, e.merged_into_id
        FROM listings l
        JOIN securities s ON s.security_id = l.security_id
        JOIN entities e ON e.entity_id = s.issuer_entity_id
        WHERE l.ticker = :ticker
          AND (:mic IS NULL OR l.mic = :mic)
          AND l.valid_from <= :as_of
          AND (l.valid_to IS NULL OR l.valid_to > :as_of)
          AND l.status = 'active'
          AND s.status = 'active'
          AND e.status IN ('active', 'provisional')
        ORDER BY l.is_primary DESC, l.valid_from DESC
    """, ticker=ticker_upper, mic=mic, as_of=as_of)
    
    candidates = []
    for row in listings:
        entity_id, redirect_chain = follow_redirects(row.entity_id)
        
        # Score based on listing attributes
        score = 0.8  # Base score for ticker match
        if row.is_primary:
            score += 0.15  # Primary listing bonus
        if row.mic and mic and row.mic == mic:
            score += 0.05  # Exact exchange match
        
        candidates.append(ResolutionCandidate(
            entity_id=entity_id,
            score=min(score, 1.0),
            match_type='ticker',
            matched_value=f"{row.ticker}:{row.mic or 'ANY'}",
            matched_scheme='ticker',
            evidence=[],  # Could add listing_id as evidence
            redirect_chain=redirect_chain if len(redirect_chain) > 1 else None,
            listing_id=row.listing_id,
            security_id=row.security_id,
        ))
    
    return sorted(candidates, key=lambda c: c.score, reverse=True)
```

### Path: Name → Alias/Entity (Fuzzy)

```python
def resolve_name(
    name: str,
    as_of: date | None = None,
    min_score: float = 0.6
) -> list[ResolutionCandidate]:
    """
    Name → Fuzzy match on aliases and entity names
    
    Uses trigram similarity for fuzzy matching.
    """
    name_normalized = normalize_name(name)
    
    # Search aliases (includes extracted mentions from filings)
    alias_matches = query("""
        SELECT 
            a.entity_id, a.alias_text, a.alias_type,
            similarity(a.alias_text, :name) AS sim_score,
            e.primary_name, e.status, e.merged_into_id
        FROM aliases a
        JOIN entities e ON e.entity_id = a.entity_id
        WHERE similarity(a.alias_text, :name) > :min_score
          AND e.status IN ('active', 'provisional')
        ORDER BY sim_score DESC
        LIMIT 20
    """, name=name_normalized, min_score=min_score)
    
    # Also search primary_name directly
    name_matches = query("""
        SELECT 
            e.entity_id, e.primary_name,
            similarity(e.primary_name, :name) AS sim_score,
            e.status, e.merged_into_id
        FROM entities e
        WHERE similarity(e.primary_name, :name) > :min_score
          AND e.status IN ('active', 'provisional')
        ORDER BY sim_score DESC
        LIMIT 20
    """, name=name_normalized, min_score=min_score)
    
    # Combine and deduplicate
    seen = set()
    candidates = []
    
    for row in alias_matches:
        entity_id, redirect_chain = follow_redirects(row.entity_id)
        if entity_id not in seen:
            seen.add(entity_id)
            candidates.append(ResolutionCandidate(
                entity_id=entity_id,
                score=row.sim_score,
                match_type='alias_fuzzy',
                matched_value=row.alias_text,
                redirect_chain=redirect_chain if len(redirect_chain) > 1 else None,
            ))
    
    for row in name_matches:
        entity_id, redirect_chain = follow_redirects(row.entity_id)
        if entity_id not in seen:
            seen.add(entity_id)
            candidates.append(ResolutionCandidate(
                entity_id=entity_id,
                score=row.sim_score * 0.95,  # Slight penalty vs alias match
                match_type='name_fuzzy',
                matched_value=row.primary_name,
                redirect_chain=redirect_chain if len(redirect_chain) > 1 else None,
            ))
    
    return sorted(candidates, key=lambda c: c.score, reverse=True)[:10]
```

---

## Ticker Reuse & Temporality

### The Problem

Tickers are reused over time:

```
Timeline:
─────────────────────────────────────────────────────────────►
                                                            time
    1985-1995              1996-2023              2024-present
    ┌─────────┐            ┌─────────┐            ┌─────────┐
    │  AAPL   │            │  AAPL   │            │  AAPL   │
    │ (Apple  │            │ (Apple  │            │ (Apple  │
    │ Records)│            │  Inc.)  │            │  Inc.)  │
    └─────────┘            └─────────┘            └─────────┘
        │                       │                      │
        ▼                       ▼                      ▼
    Entity A               Entity B                Entity B
    (Music Label)          (Tech Company)          (Tech Company)
```

### The Solution: Temporal Listings

```sql
-- Listings table has valid_from/valid_to
CREATE TABLE listings (
    listing_id      CHAR(26) PRIMARY KEY,
    security_id     CHAR(26) NOT NULL,
    ticker          VARCHAR(20) NOT NULL,
    mic             CHAR(4) NOT NULL,
    
    valid_from      DATE NOT NULL,  -- When this ticker became active
    valid_to        DATE,           -- When it stopped (NULL = still active)
    
    UNIQUE(ticker, mic, valid_from)
);

-- Example data:
-- | listing_id | ticker | mic  | valid_from | valid_to   | security_id |
-- |------------|--------|------|------------|------------|-------------|
-- | L001...    | AAPL   | XNAS | 1985-01-01 | 1995-12-31 | S001 (Apple Records) |
-- | L002...    | AAPL   | XNAS | 1996-01-01 | NULL       | S002 (Apple Inc.)    |
```

### as_of Query Semantics

```python
def resolve(query: str, as_of: date | None = None) -> list[ResolutionCandidate]:
    """
    as_of semantics:
    
    - None (default): Use current date, return only currently active
    - Specific date: Return entities that matched the query on that date
    
    Examples:
        resolve("AAPL", as_of=date(1990, 1, 1))  → Apple Records
        resolve("AAPL", as_of=date(2024, 1, 1))  → Apple Inc.
        resolve("AAPL")                          → Apple Inc. (today)
    """
    as_of = as_of or date.today()
    
    # Ticker resolution uses temporal bounds
    if looks_like_ticker(query):
        return resolve_ticker(query, as_of=as_of)
    
    # Other schemes may also have validity periods
    ...
```

### Historical Resolution Example

```python
# User wants to analyze a 1992 filing that mentions "AAPL"
filing_date = date(1992, 3, 15)
candidates = resolver.resolve("AAPL", as_of=filing_date)

# Result:
# [
#     ResolutionCandidate(
#         entity_id="01ARZ...",  # Apple Records entity ID
#         score=0.95,
#         match_type="ticker",
#         matched_value="AAPL:XNAS",
#         temporal_note="Valid 1985-01-01 to 1995-12-31"
#     )
# ]
```

---

## Scoring & Ranking

### Score Components

| Factor | Weight | Description |
|--------|--------|-------------|
| **Match Type** | Base | exact=1.0, alias=0.9, fuzzy=0.6-0.9 |
| **Claim Confidence** | Multiplier | Source reliability (SEC=1.0, web=0.7) |
| **Primary Status** | Bonus +0.1 | Primary listing, primary identifier |
| **Temporal Exact** | Bonus +0.05 | Query date falls within validity |
| **Exchange Match** | Bonus +0.05 | Exact MIC match when provided |

### Scoring Formula

```python
def calculate_score(
    match_type: str,
    claim_confidence: float,
    is_primary: bool,
    temporal_match: bool,
    exchange_match: bool
) -> float:
    """Calculate resolution score for a candidate."""
    
    # Base scores by match type
    base_scores = {
        'exact': 1.0,
        'alias_exact': 0.95,
        'ticker': 0.85,
        'alias_fuzzy': 0.7,
        'name_fuzzy': 0.65,
    }
    
    score = base_scores.get(match_type, 0.5)
    score *= claim_confidence
    
    if is_primary:
        score += 0.10
    if temporal_match:
        score += 0.05
    if exchange_match:
        score += 0.05
    
    return min(score, 1.0)  # Cap at 1.0
```

### Ranking Output

```python
@dataclass
class ResolutionCandidate:
    """A potential match for a resolution query."""
    
    entity_id: str              # Canonical entity (after redirect follow)
    score: float                # 0.0 to 1.0
    match_type: str             # How we matched
    matched_value: str          # What actually matched
    matched_scheme: str | None  # 'cik', 'ticker', etc.
    
    # Evidence
    evidence: list[str]         # Claim IDs supporting this match
    
    # If merged
    redirect_chain: list[str] | None  # [original_id, ..., canonical_id]
    
    # For ticker matches, include full chain
    listing_id: str | None = None
    security_id: str | None = None
    
    # Debugging
    temporal_note: str | None = None

# Usage:
candidates = resolver.resolve("AAPL")
# Returns:
# [
#     ResolutionCandidate(entity_id="01ARZ...", score=0.98, ...),
#     ResolutionCandidate(entity_id="01BSY...", score=0.45, ...),  # Less likely
# ]

# Caller decides threshold:
best = candidates[0] if candidates and candidates[0].score > 0.8 else None
```

---

## Ambiguity Handling

### When Ambiguity Occurs

| Scenario | Example | Handling |
|----------|---------|----------|
| Same ticker, different time | "AAPL" in 1990 vs 2024 | Use `as_of` parameter |
| Same name, different entities | "Bank of America" (multiple) | Return all, let caller choose |
| Typo/variation | "Microsft" | Fuzzy match, lower score |
| Private company mention | "Acme Corp" (no CIK) | Create provisional or return candidates |

### Ambiguity Response

```python
@dataclass
class ResolutionResult:
    """Full resolution response with metadata."""
    
    candidates: list[ResolutionCandidate]
    
    # Resolution metadata
    query: str
    as_of: date
    resolved_at: datetime
    
    # Flags
    is_ambiguous: bool          # Multiple high-scoring candidates
    needs_review: bool          # Low confidence, recommend human review
    created_provisional: bool   # Created new provisional entity
    
    @property
    def best(self) -> ResolutionCandidate | None:
        """Highest scoring candidate, or None if empty."""
        return self.candidates[0] if self.candidates else None
    
    @property
    def is_confident(self) -> bool:
        """True if single high-confidence match."""
        return (
            len(self.candidates) == 1 and 
            self.candidates[0].score >= 0.9
        )

# Example: Ambiguous result
result = resolver.resolve("Bank of America")
# result.candidates = [
#     {entity_id: "01A...", score: 0.92, name: "Bank of America Corporation"},
#     {entity_id: "01B...", score: 0.88, name: "Bank of America, National Association"},
#     {entity_id: "01C...", score: 0.72, name: "Bank of America Illinois"},
# ]
# result.is_ambiguous = True
# result.needs_review = False (top score > 0.9)
```

### Caller Strategies

```python
# Strategy 1: Strict (only confident matches)
def resolve_strict(query: str) -> Entity | None:
    result = resolver.resolve(query)
    if result.is_confident:
        return resolver.get(result.best.entity_id)
    return None

# Strategy 2: Best effort (take top candidate if decent)
def resolve_best_effort(query: str, threshold: float = 0.7) -> Entity | None:
    result = resolver.resolve(query)
    if result.best and result.best.score >= threshold:
        return resolver.get(result.best.entity_id)
    return None

# Strategy 3: Interactive (return options for user selection)
def resolve_interactive(query: str) -> list[Entity]:
    result = resolver.resolve(query)
    return [resolver.get(c.entity_id) for c in result.candidates[:5]]
```

---

## Resolution API

### Protocol Definition

```python
from typing import Protocol
from dataclasses import dataclass
from datetime import date, datetime

@dataclass
class ResolutionCandidate:
    entity_id: str
    score: float
    match_type: str
    matched_value: str
    matched_scheme: str | None = None
    evidence: list[str] = field(default_factory=list)
    redirect_chain: list[str] | None = None
    listing_id: str | None = None
    security_id: str | None = None

@dataclass
class ResolutionResult:
    candidates: list[ResolutionCandidate]
    query: str
    as_of: date
    resolved_at: datetime
    is_ambiguous: bool = False
    needs_review: bool = False
    created_provisional: bool = False

class EntityResolverProtocol(Protocol):
    """Entity resolution interface."""
    
    def resolve(
        self, 
        query: str, 
        as_of: date | None = None,
        limit: int = 10
    ) -> ResolutionResult:
        """Resolve any identifier to ranked entity candidates."""
        ...
    
    def resolve_cik(
        self, 
        cik: str, 
        as_of: date | None = None
    ) -> ResolutionResult:
        """Resolve SEC CIK to entity candidates."""
        ...
    
    def resolve_ticker(
        self, 
        ticker: str, 
        mic: str | None = None,
        as_of: date | None = None
    ) -> ResolutionResult:
        """Resolve ticker symbol to entity candidates."""
        ...
    
    def resolve_isin(
        self, 
        isin: str,
        as_of: date | None = None
    ) -> ResolutionResult:
        """Resolve ISIN to entity candidates (via security→entity)."""
        ...
    
    def get(self, entity_id: str) -> Entity | None:
        """Get entity by exact ID (follows redirects)."""
        ...
    
    def get_canonical(self, entity_id: str) -> tuple[Entity | None, list[str]]:
        """Get entity and redirect chain if merged."""
        ...
```

### Usage Examples

```python
# Initialize resolver
from entityspine import create_resolver

resolver = create_resolver(backend="sqlite", db_path="entities.db")

# Basic resolution
result = resolver.resolve("AAPL")
print(f"Top match: {result.best.entity_id} (score: {result.best.score})")

# Historical resolution
result = resolver.resolve("AAPL", as_of=date(1992, 1, 1))

# CIK resolution (direct)
result = resolver.resolve_cik("0000320193")
assert result.best.matched_scheme == "cik"

# Ticker with exchange hint
result = resolver.resolve_ticker("AAPL", mic="XNAS")

# Handle ambiguity
result = resolver.resolve("Bank of America")
if result.is_ambiguous:
    print(f"Ambiguous: {len(result.candidates)} candidates")
    for c in result.candidates:
        entity = resolver.get(c.entity_id)
        print(f"  - {entity.primary_name} (score: {c.score})")
```

---

## Example Flows

### Flow 1: Filing Processor Resolves CIK

```
py-sec-edgar extracts CIK from filing → resolves to entity

┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│  1. Parser extracts: "Central Index Key: 0000320193"                    │
│                                                                         │
│  2. Adapter calls:                                                      │
│     result = resolver.resolve_cik("0000320193")                         │
│                                                                         │
│  3. entityspine:                                                        │
│     • Query identifier_claims WHERE scheme='cik' AND value='0000320193' │
│     • Find entity_id = "01ARZ3NDEKTSV4RRFFQ69G5FAV"                     │
│     • Check entity.merged_into_id → NULL (not merged)                  │
│     • Return ResolutionResult with single candidate, score=1.0          │
│                                                                         │
│  4. py-sec-edgar stores:                                                │
│     filing.filer_entity_id = "01ARZ3NDEKTSV4RRFFQ69G5FAV"              │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Flow 2: NLP Extracts Company Mention

```
Filing text mentions "our customer, Microsoft Corporation" → resolve

┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│  1. NLP extracts: "Microsoft Corporation"                               │
│                                                                         │
│  2. Adapter calls:                                                      │
│     result = resolver.resolve("Microsoft Corporation")                  │
│                                                                         │
│  3. entityspine:                                                        │
│     • Not a known scheme format, try name resolution                   │
│     • Query aliases: similarity("Microsoft Corporation", alias) > 0.8  │
│     • Query entities.primary_name similarity                           │
│     • Found: entity_id="01BSY..." with alias "Microsoft Corporation"   │
│     • Score: 0.97 (exact alias match)                                  │
│                                                                         │
│  4. py-sec-edgar stores:                                                │
│     entity_mention.resolved_entity_id = "01BSY..."                     │
│     entity_mention.resolution_confidence = 0.97                        │
│     entity_mention.resolution_method = "alias_exact"                   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Flow 3: Unknown Company Creates Provisional

```
Filing mentions "Acme Private Holdings LLC" (not in entityspine)

┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│  1. NLP extracts: "Acme Private Holdings LLC"                           │
│                                                                         │
│  2. Adapter calls:                                                      │
│     result = resolver.resolve(                                          │
│         "Acme Private Holdings LLC",                                    │
│         create_provisional=True,                                        │
│         evidence_uri="sec://0000320193-24-000081/10-K#item1"           │
│     )                                                                   │
│                                                                         │
│  3. entityspine:                                                        │
│     • No high-confidence matches found                                 │
│     • create_provisional=True → create new entity:                     │
│       {                                                                 │
│         entity_id: "01CTZ...",                                         │
│         primary_name: "Acme Private Holdings LLC",                     │
│         status: "provisional",                                         │
│         source_system: "py-sec-edgar",                                 │
│         confidence: 0.5                                                │
│       }                                                                 │
│     • Create alias claim with evidence pointer                         │
│     • Return result with created_provisional=True                      │
│                                                                         │
│  4. py-sec-edgar stores:                                                │
│     entity_mention.resolved_entity_id = "01CTZ..."                     │
│     entity_mention.resolution_method = "provisional_created"           │
│                                                                         │
│  5. Later enrichment:                                                   │
│     • Data vendor provides match to known entity                       │
│     • Merge proposal created (not auto-merged)                         │
│     • Analyst reviews and approves merge                               │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Flow 4: Merged Entity Lookup

```
Old entity ID from historical data → follows redirect

┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│  1. Historical data has entity_id = "01AAA..." (Time Warner)            │
│     (Time Warner merged into AT&T in 2018)                             │
│                                                                         │
│  2. Application calls:                                                  │
│     entity, chain = resolver.get_canonical("01AAA...")                  │
│                                                                         │
│  3. entityspine:                                                        │
│     • Lookup entity "01AAA..."                                         │
│     • entity.status = "merged"                                         │
│     • entity.merged_into_id = "01BBB..." (AT&T)                        │
│     • Follow chain: "01BBB..." has merged_into_id = "01CCC..." (?)     │
│     • Continue until merged_into_id IS NULL                            │
│     • Return (canonical_entity, ["01AAA...", "01BBB...", "01CCC..."])  │
│                                                                         │
│  4. Application knows:                                                  │
│     • Canonical entity is "01CCC..."                                   │
│     • Original "01AAA..." followed 2 merges                            │
│     • Can log/display "Time Warner → AT&T → ..." if needed            │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Decision Log

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | Return list not single result | Real data is messy, ambiguity is normal |
| 2 | Include `as_of` on all resolve methods | Ticker reuse requires temporal context |
| 3 | Scores are 0.0-1.0 not percentages | Standard ML convention, easy thresholding |
| 4 | Redirect chain in response | Transparency for audit and debugging |
| 5 | Provisional entities have `status='provisional'` | Distinguish from confirmed entities |

---

## Known Open Questions

| # | Question | Status |
|---|----------|--------|
| 1 | Should `as_of=None` mean "now" or "all time"? | Decided: "now" (current date) |
| 2 | Maximum redirect chain length before error? | Suggest: 10 hops |
| 3 | Should resolver auto-create provisional or require flag? | Suggest: require `create_provisional=True` |
| 4 | Fuzzy threshold configurable per-query? | Open |

---

*Companion to Unified Data Model v2.2 | January 2026*
