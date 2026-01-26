# py-sec-edgar Integration Contract

**Companion to Unified Data Model v2.2**

> This document defines exactly what py-sec-edgar stores, what entityspine owns,  
> and the port/adapter interface between them.

---

## Table of Contents

1. [Package Responsibilities](#package-responsibilities)
2. [What py-sec-edgar Stores](#what-py-sec-edgar-stores)
3. [What entityspine Owns](#what-entityspine-owns)
4. [Port Interface](#port-interface)
5. [Adapter Implementation](#adapter-implementation)
6. [Mention-to-Entity Workflow](#mention-to-entity-workflow)
7. [Provisional Entity Lifecycle](#provisional-entity-lifecycle)
8. [Error Handling Contract](#error-handling-contract)
9. [Testing Contract](#testing-contract)

---

## Package Responsibilities

### Clear Boundary

```
┌───────────────────────────────────────────────────────────────────────────────┐
│                             RESPONSIBILITY MATRIX                              │
├───────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  py-sec-edgar OWNS:                    entityspine OWNS:                      │
│  ══════════════════                    ═════════════════                      │
│                                                                               │
│  • SEC filings (content, dates)        • Entity lifecycle (create, merge)    │
│  • Extracted sections (text)           • Entity/Security/Listing hierarchy   │
│  • SIGDEV events (M&A, mgmt)           • All identifier claims               │
│  • Entity mentions (text spans)        • Aliases and name variants           │
│  • Company relationships               • Vendor crosswalks                   │
│  • Filing metadata                     • Merge events and redirects          │
│  • Processing status                   • Conflict resolution                 │
│                                                                               │
│  py-sec-edgar STORES:                  entityspine PROVIDES:                  │
│  ═══════════════════                   ═════════════════════                  │
│                                                                               │
│  • entity_id references                • resolve() → ranked candidates       │
│  • Evidence pointers back              • get() → full entity data            │
│  • Resolution metadata                 • create_provisional() → new entity   │
│  • Confidence scores                   • propose_merge() → merge proposal    │
│                                                                               │
│  py-sec-edgar NEVER:                   entityspine NEVER:                     │
│  ═══════════════════                   ═════════════════════                  │
│                                                                               │
│  • Creates entities directly           • Parses SEC filings                  │
│  • Modifies entity attributes          • Stores filing content               │
│  • Manages identifier claims           • Extracts sections or events         │
│  • Decides merges                      • Owns mention text storage           │
│                                                                               │
└───────────────────────────────────────────────────────────────────────────────┘
```

---

## What py-sec-edgar Stores

### Filings Table

```sql
CREATE TABLE filings (
    filing_id               UUID PRIMARY KEY,
    
    -- Reference to entityspine (the ONLY entity data stored)
    filer_entity_id         CHAR(26) NOT NULL,  -- entityspine entity_id
    
    -- Filing metadata (owned by py-sec-edgar)
    accession_number        VARCHAR(25) UNIQUE NOT NULL,
    form_type               VARCHAR(20) NOT NULL,
    filed_date              DATE NOT NULL,
    accepted_at             TIMESTAMPTZ,
    period_of_report        DATE,
    primary_document        VARCHAR(255),
    file_number             VARCHAR(25),
    items_reported          VARCHAR(100)[],
    is_amendment            BOOLEAN DEFAULT FALSE,
    
    -- Storage and processing
    raw_content_path        VARCHAR(500),
    processing_status       VARCHAR(20) DEFAULT 'pending',
    
    created_at              TIMESTAMPTZ DEFAULT NOW()
);

-- Note: filer_entity_id REFERENCES entityspine, enforced at application level
-- (cross-database foreign keys not possible in standard SQL)
```

### Entity Mentions Table

```sql
CREATE TABLE entity_mentions (
    mention_id              UUID PRIMARY KEY,
    section_id              UUID REFERENCES extracted_sections(section_id),
    
    -- What was mentioned (owned by py-sec-edgar)
    mention_text            VARCHAR(500) NOT NULL,
    entity_type             VARCHAR(20) NOT NULL,
    char_start              INT,
    char_end                INT,
    sentence_context        TEXT,
    
    -- Resolution result (references entityspine)
    resolved_entity_id      CHAR(26),              -- entityspine.entities.entity_id
    
    -- Resolution metadata (owned by py-sec-edgar)
    resolution_status       VARCHAR(20) NOT NULL DEFAULT 'pending',
    resolution_method       VARCHAR(30),           -- 'exact', 'fuzzy', 'provisional', 'manual'
    resolution_confidence   DECIMAL(3,2),
    resolution_candidates   JSONB,                 -- Top N candidates from resolve()
    resolved_at             TIMESTAMPTZ,
    
    -- Extraction metadata
    extraction_method       VARCHAR(20),           -- 'spacy', 'regex', 'llm'
    extraction_confidence   DECIMAL(3,2),
    created_at              TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT chk_resolution_status CHECK (resolution_status IN (
        'pending', 'resolved', 'provisional', 'ambiguous', 'unresolvable', 'manual_review'
    ))
);
```

### Company Relationships Table

```sql
CREATE TABLE company_relationships (
    relationship_id         UUID PRIMARY KEY,
    
    -- Source (always resolved)
    source_entity_id        CHAR(26) NOT NULL,     -- entityspine entity_id
    
    -- Target (may be unresolved)
    target_entity_id        CHAR(26),              -- entityspine entity_id (if resolved)
    target_mention_id       UUID REFERENCES entity_mentions(mention_id),  -- Link to mention
    target_mention_text     VARCHAR(500),          -- Original text if unresolved
    
    -- Relationship (owned by py-sec-edgar)
    relationship_type       VARCHAR(50) NOT NULL,
    relationship_subtype    VARCHAR(50),
    
    -- Evidence pointers (owned by py-sec-edgar)
    evidence_filing_id      UUID REFERENCES filings(filing_id),
    evidence_section_id     UUID REFERENCES extracted_sections(section_id),
    evidence_text           TEXT,
    evidence_char_start     INT,
    evidence_char_end       INT,
    
    -- Metrics
    metrics                 JSONB DEFAULT '{}',
    
    -- Lifecycle
    first_disclosed         DATE,
    last_disclosed          DATE,
    status                  VARCHAR(20) DEFAULT 'ACTIVE',
    confidence              DECIMAL(3,2),
    
    created_at              TIMESTAMPTZ DEFAULT NOW()
);
```

### What py-sec-edgar Does NOT Store

```python
# ❌ NEVER store these in py-sec-edgar:

# Entity attributes (owned by entityspine)
company_name = "Apple Inc."          # Use entityspine.get(entity_id).primary_name
cik = "0000320193"                   # Query entityspine claims
ticker = "AAPL"                      # Query entityspine listings

# Denormalized caches (leads to stale data)
filings.company_name                 # Just store entity_id
filings.ticker                       # Query when needed

# Entity lifecycle
entity.created_at                    # Owned by entityspine
entity.merged_into_id                # Owned by entityspine
```

---

## What entityspine Owns

### Entity Master Data

| Table | Columns | py-sec-edgar Access |
|-------|---------|---------------------|
| `entities` | entity_id, names, status, type, merged_into_id | Read via get() |
| `securities` | security_id, issuer_entity_id, type | Read via get_securities() |
| `listings` | listing_id, ticker, mic, valid_from/to | Read via resolve_ticker() |
| `identifier_claims` | All identifier mappings | Read via resolve() |
| `aliases` | Name variants | Used by resolve() fuzzy |
| `merge_events` | Merge history | Read via get_merge_history() |
| `vendor_crosswalks` | Bloomberg, FactSet IDs | Read via get_vendor_id() |

### Entity Lifecycle (Exclusive to entityspine)

```
                    entityspine controls ALL lifecycle
                    
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│  CREATE                                                                 │
│  ────────                                                               │
│  • From SEC bulk data (company_tickers.json)                           │
│  • From py-sec-edgar provisional request                               │
│  • From vendor data loads                                              │
│                                                                         │
│  UPDATE                                                                 │
│  ────────                                                               │
│  • Name changes (from SEC filings)                                     │
│  • New identifiers (from vendor crosswalks)                            │
│  • Status changes (active → inactive)                                  │
│                                                                         │
│  MERGE                                                                  │
│  ────────                                                               │
│  • Corporate M&A (AT&T acquires Time Warner)                          │
│  • Duplicate detection (same entity, different sources)                │
│  • py-sec-edgar can PROPOSE merges, entityspine EXECUTES              │
│                                                                         │
│  NEVER auto-merge without:                                             │
│  • Evidence claims                                                     │
│  • Merge event record                                                  │
│  • Redirect from old ID                                                │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Port Interface

### EntityResolverPort (py-sec-edgar side)

```python
# py_sec_edgar/ports/entity_resolver.py
"""
Port interface that py-sec-edgar uses to interact with entity resolution.
This is what py-sec-edgar codes against (dependency inversion).
"""

from typing import Protocol
from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class ResolutionCandidate:
    """A potential entity match."""
    entity_id: str
    score: float              # 0.0 to 1.0
    match_type: str           # 'exact', 'alias', 'fuzzy', 'ticker'
    matched_value: str        # What actually matched the query
    matched_scheme: str | None = None
    redirect_chain: list[str] | None = None


@dataclass
class ResolutionResult:
    """Full resolution response."""
    candidates: list[ResolutionCandidate]
    query: str
    as_of: date
    resolved_at: datetime
    is_ambiguous: bool = False
    needs_review: bool = False
    created_provisional: bool = False
    provisional_entity_id: str | None = None
    
    @property
    def best(self) -> ResolutionCandidate | None:
        return self.candidates[0] if self.candidates else None
    
    @property
    def is_confident(self) -> bool:
        return len(self.candidates) == 1 and self.candidates[0].score >= 0.9


@dataclass(frozen=True)
class EntityData:
    """Read-only entity data returned by entityspine."""
    entity_id: str
    entity_type: str
    status: str
    primary_name: str
    legal_name: str | None
    cik: str | None
    lei: str | None
    sic_code: str | None
    is_public: bool


class EntityResolverPort(Protocol):
    """
    Interface py-sec-edgar uses to talk to entityspine.
    
    py-sec-edgar codes against this protocol.
    entityspine provides implementation.
    """
    
    def resolve(
        self, 
        query: str, 
        as_of: date | None = None,
        limit: int = 10
    ) -> ResolutionResult:
        """
        Resolve any identifier/name to ranked entity candidates.
        
        Args:
            query: CIK, ticker, name, or other identifier
            as_of: Point-in-time for resolution (default: today)
            limit: Max candidates to return
            
        Returns:
            ResolutionResult with ranked candidates and metadata
        """
        ...
    
    def resolve_cik(self, cik: str) -> ResolutionResult:
        """Resolve SEC CIK to entity. CIK should resolve to exactly one."""
        ...
    
    def resolve_ticker(
        self, 
        ticker: str, 
        mic: str | None = None,
        as_of: date | None = None
    ) -> ResolutionResult:
        """Resolve ticker symbol, optionally with exchange."""
        ...
    
    def get(self, entity_id: str) -> EntityData | None:
        """
        Get entity by ID. Follows merge redirects automatically.
        
        Returns None if entity_id not found.
        """
        ...
    
    def get_canonical(self, entity_id: str) -> tuple[EntityData | None, list[str]]:
        """
        Get entity and redirect chain.
        
        Returns:
            (entity, redirect_chain) where redirect_chain shows merge path
        """
        ...
    
    def create_provisional(
        self,
        name: str,
        entity_type: str = "COMPANY",
        evidence_uri: str | None = None,
        evidence_text: str | None = None,
        source_system: str = "py-sec-edgar",
    ) -> str:
        """
        Create provisional entity for unmatched mention.
        
        Returns:
            New entity_id
        """
        ...
    
    def propose_merge(
        self,
        source_entity_id: str,
        target_entity_id: str,
        evidence_uri: str,
        reason: str,
    ) -> str:
        """
        Propose merging source into target.
        
        Does NOT execute merge - creates proposal for review.
        
        Returns:
            Merge proposal ID
        """
        ...
```

---

## Adapter Implementation

### EntitySpineAdapter (implements port)

```python
# py_sec_edgar/adapters/entityspine_adapter.py
"""
Adapter that implements EntityResolverPort using entityspine package.
"""

from datetime import date, datetime
from entityspine import EntityResolver, EntityStore
from py_sec_edgar.ports.entity_resolver import (
    EntityResolverPort, ResolutionResult, ResolutionCandidate, EntityData
)


class EntitySpineAdapter:
    """
    Adapts entityspine to py-sec-edgar's port interface.
    
    Usage:
        adapter = EntitySpineAdapter(backend="sqlite", db_path="entities.db")
        result = adapter.resolve("AAPL")
    """
    
    def __init__(
        self, 
        backend: str = "sqlite", 
        db_path: str | None = None,
        **kwargs
    ):
        """
        Initialize adapter with entityspine backend.
        
        Args:
            backend: "json", "sqlite", "duckdb", "postgres"
            db_path: Path to database (for file-based backends)
            **kwargs: Additional backend-specific options
        """
        self._resolver = EntityResolver(backend=backend, db_path=db_path, **kwargs)
        self._store = EntityStore(backend=backend, db_path=db_path, **kwargs)
    
    def resolve(
        self, 
        query: str, 
        as_of: date | None = None,
        limit: int = 10
    ) -> ResolutionResult:
        """Resolve any identifier to ranked candidates."""
        result = self._resolver.resolve(query, as_of=as_of, limit=limit)
        
        return ResolutionResult(
            candidates=[
                ResolutionCandidate(
                    entity_id=c.entity_id,
                    score=c.score,
                    match_type=c.match_type,
                    matched_value=c.matched_value,
                    matched_scheme=c.matched_scheme,
                    redirect_chain=c.redirect_chain,
                )
                for c in result.candidates
            ],
            query=query,
            as_of=as_of or date.today(),
            resolved_at=datetime.now(),
            is_ambiguous=result.is_ambiguous,
            needs_review=result.needs_review,
            created_provisional=result.created_provisional,
            provisional_entity_id=result.provisional_entity_id,
        )
    
    def resolve_cik(self, cik: str) -> ResolutionResult:
        """Resolve CIK to entity."""
        return self.resolve(cik)  # Resolver auto-detects CIK format
    
    def resolve_ticker(
        self, 
        ticker: str, 
        mic: str | None = None,
        as_of: date | None = None
    ) -> ResolutionResult:
        """Resolve ticker symbol."""
        result = self._resolver.resolve_ticker(ticker, mic=mic, as_of=as_of)
        return self._convert_result(result, ticker, as_of)
    
    def get(self, entity_id: str) -> EntityData | None:
        """Get entity by ID, following redirects."""
        entity = self._store.get(entity_id)
        if entity is None:
            return None
        
        return EntityData(
            entity_id=entity.entity_id,
            entity_type=entity.entity_type,
            status=entity.status,
            primary_name=entity.primary_name,
            legal_name=entity.legal_name,
            cik=entity.cik,
            lei=entity.lei,
            sic_code=entity.sic_code,
            is_public=entity.is_public,
        )
    
    def get_canonical(self, entity_id: str) -> tuple[EntityData | None, list[str]]:
        """Get entity and redirect chain."""
        entity, chain = self._store.get_canonical(entity_id)
        if entity is None:
            return None, []
        
        return self._to_entity_data(entity), chain
    
    def create_provisional(
        self,
        name: str,
        entity_type: str = "COMPANY",
        evidence_uri: str | None = None,
        evidence_text: str | None = None,
        source_system: str = "py-sec-edgar",
    ) -> str:
        """Create provisional entity."""
        entity_id = self._store.create_provisional(
            name=name,
            entity_type=entity_type,
            evidence_uri=evidence_uri,
            evidence_text=evidence_text,
            source_system=source_system,
        )
        return entity_id
    
    def propose_merge(
        self,
        source_entity_id: str,
        target_entity_id: str,
        evidence_uri: str,
        reason: str,
    ) -> str:
        """Propose merge (does not execute)."""
        proposal_id = self._store.propose_merge(
            source_id=source_entity_id,
            target_id=target_entity_id,
            evidence_uri=evidence_uri,
            reason=reason,
            proposed_by="py-sec-edgar",
        )
        return proposal_id
    
    def _to_entity_data(self, entity) -> EntityData:
        return EntityData(
            entity_id=entity.entity_id,
            entity_type=entity.entity_type,
            status=entity.status,
            primary_name=entity.primary_name,
            legal_name=entity.legal_name,
            cik=entity.cik,
            lei=entity.lei,
            sic_code=entity.sic_code,
            is_public=entity.is_public,
        )
```

### Null Adapter (For Testing)

```python
# py_sec_edgar/adapters/null_entity_adapter.py
"""
Null adapter for testing without entityspine dependency.
"""

from datetime import date, datetime
from py_sec_edgar.ports.entity_resolver import (
    EntityResolverPort, ResolutionResult, ResolutionCandidate, EntityData
)


class NullEntityAdapter:
    """
    Adapter that returns empty results.
    
    Use for testing py-sec-edgar in isolation.
    """
    
    def resolve(
        self, 
        query: str, 
        as_of: date | None = None,
        limit: int = 10
    ) -> ResolutionResult:
        return ResolutionResult(
            candidates=[],
            query=query,
            as_of=as_of or date.today(),
            resolved_at=datetime.now(),
        )
    
    def resolve_cik(self, cik: str) -> ResolutionResult:
        return self.resolve(cik)
    
    def resolve_ticker(
        self, 
        ticker: str, 
        mic: str | None = None,
        as_of: date | None = None
    ) -> ResolutionResult:
        return self.resolve(ticker, as_of=as_of)
    
    def get(self, entity_id: str) -> EntityData | None:
        return None
    
    def get_canonical(self, entity_id: str) -> tuple[EntityData | None, list[str]]:
        return None, []
    
    def create_provisional(self, **kwargs) -> str:
        import ulid
        return str(ulid.new())
    
    def propose_merge(self, **kwargs) -> str:
        import ulid
        return str(ulid.new())
```

---

## Mention-to-Entity Workflow

### Complete Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                     MENTION-TO-ENTITY RESOLUTION WORKFLOW                        │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  py-sec-edgar                                    entityspine                    │
│  ═══════════                                     ══════════                     │
│                                                                                 │
│  1. Extract mention from filing                                                 │
│     ┌──────────────────────────────┐                                           │
│     │ "...our customer Microsoft   │                                           │
│     │  Corporation purchased..."   │                                           │
│     └──────────────────────────────┘                                           │
│                │                                                                │
│                ▼                                                                │
│  2. Create entity_mentions record                                               │
│     • mention_text = "Microsoft Corporation"                                    │
│     • resolution_status = 'pending'                                            │
│                │                                                                │
│                ▼                                                                │
│  3. Call resolver.resolve("Microsoft Corporation")                              │
│                │                                                                │
│                └────────────────────────────►  4. Search aliases, names         │
│                                                   • Query aliases table        │
│                                                   • Query entity names          │
│                                                   • Score candidates           │
│                                                                                 │
│                ◄────────────────────────────  5. Return ResolutionResult        │
│                │                                  candidates=[                  │
│                │                                    {id: "01X..", score: 0.98}, │
│                │                                    {id: "01Y..", score: 0.45}, │
│                │                                  ]                             │
│                ▼                                                                │
│  6. Evaluate result                                                             │
│     ┌─────────────────────────────┐                                            │
│     │ if best.score >= 0.9:       │                                            │
│     │   → RESOLVED                │                                            │
│     │ elif best.score >= 0.7:     │                                            │
│     │   → RESOLVED (lower conf)   │                                            │
│     │ elif best.score >= 0.5:     │                                            │
│     │   → AMBIGUOUS (review)      │                                            │
│     │ else:                       │                                            │
│     │   → CREATE PROVISIONAL      │                                            │
│     └─────────────────────────────┘                                            │
│                │                                                                │
│                ▼                                                                │
│  7. Update entity_mentions                                                      │
│     • resolved_entity_id = "01X..."                                            │
│     • resolution_status = 'resolved'                                           │
│     • resolution_method = 'alias_exact'                                        │
│     • resolution_confidence = 0.98                                             │
│     • resolution_candidates = [{...}, {...}]                                   │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Code Implementation

```python
# py_sec_edgar/services/mention_resolver.py
"""
Service for resolving entity mentions to entityspine entities.
"""

from dataclasses import dataclass
from datetime import date
from py_sec_edgar.ports.entity_resolver import EntityResolverPort, ResolutionResult


@dataclass
class MentionResolution:
    """Result of attempting to resolve a mention."""
    entity_id: str | None
    status: str
    method: str | None
    confidence: float | None
    candidates_json: str | None


class MentionResolver:
    """Resolves entity mentions to entityspine entities."""
    
    # Confidence thresholds
    CONFIDENT_THRESHOLD = 0.9
    ACCEPTABLE_THRESHOLD = 0.7
    AMBIGUOUS_THRESHOLD = 0.5
    
    def __init__(self, entity_resolver: EntityResolverPort):
        self._resolver = entity_resolver
    
    def resolve_mention(
        self,
        mention_text: str,
        filing_date: date | None = None,
        create_provisional: bool = False,
        evidence_uri: str | None = None,
    ) -> MentionResolution:
        """
        Resolve a mention to an entity.
        
        Args:
            mention_text: The text span mentioning an entity
            filing_date: Date for temporal resolution
            create_provisional: If True, create provisional entity when unresolved
            evidence_uri: Evidence pointer for provisional creation
            
        Returns:
            MentionResolution with entity_id, status, and metadata
        """
        # Resolve against entityspine
        result = self._resolver.resolve(mention_text, as_of=filing_date)
        
        # Evaluate candidates
        if not result.candidates:
            return self._handle_no_match(
                mention_text, create_provisional, evidence_uri
            )
        
        best = result.best
        
        if best.score >= self.CONFIDENT_THRESHOLD:
            return MentionResolution(
                entity_id=best.entity_id,
                status='resolved',
                method=best.match_type,
                confidence=best.score,
                candidates_json=self._candidates_to_json(result.candidates[:3]),
            )
        
        if best.score >= self.ACCEPTABLE_THRESHOLD:
            return MentionResolution(
                entity_id=best.entity_id,
                status='resolved',
                method=best.match_type,
                confidence=best.score,
                candidates_json=self._candidates_to_json(result.candidates[:3]),
            )
        
        if best.score >= self.AMBIGUOUS_THRESHOLD:
            # Multiple plausible candidates - needs review
            return MentionResolution(
                entity_id=best.entity_id,  # Store best guess
                status='ambiguous',
                method=best.match_type,
                confidence=best.score,
                candidates_json=self._candidates_to_json(result.candidates[:5]),
            )
        
        # Low confidence - create provisional or mark unresolvable
        return self._handle_no_match(
            mention_text, create_provisional, evidence_uri
        )
    
    def _handle_no_match(
        self,
        mention_text: str,
        create_provisional: bool,
        evidence_uri: str | None,
    ) -> MentionResolution:
        """Handle case where no good match found."""
        if create_provisional:
            entity_id = self._resolver.create_provisional(
                name=mention_text,
                evidence_uri=evidence_uri,
            )
            return MentionResolution(
                entity_id=entity_id,
                status='provisional',
                method='provisional_created',
                confidence=0.5,
                candidates_json=None,
            )
        
        return MentionResolution(
            entity_id=None,
            status='unresolvable',
            method=None,
            confidence=None,
            candidates_json=None,
        )
    
    def _candidates_to_json(self, candidates) -> str:
        import json
        return json.dumps([
            {
                'entity_id': c.entity_id,
                'score': c.score,
                'match_type': c.match_type,
                'matched_value': c.matched_value,
            }
            for c in candidates
        ])
```

---

## Provisional Entity Lifecycle

### States and Transitions

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      PROVISIONAL ENTITY LIFECYCLE                                │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│                           ┌─────────────────┐                                   │
│                           │   PROVISIONAL   │                                   │
│                           │  (status=prov)  │                                   │
│                           └────────┬────────┘                                   │
│                                    │                                            │
│              ┌─────────────────────┼─────────────────────┐                     │
│              │                     │                     │                     │
│              ▼                     ▼                     ▼                     │
│     ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐           │
│     │    ENRICHED     │   │     MERGED      │   │    REJECTED     │           │
│     │ (status=active) │   │ (status=merged) │   │ (status=reject) │           │
│     └─────────────────┘   └─────────────────┘   └─────────────────┘           │
│                                                                                 │
│  Transitions:                                                                   │
│  ───────────                                                                    │
│                                                                                 │
│  1. PROVISIONAL → ENRICHED                                                      │
│     • Vendor crosswalk matches existing entity → wait, that's merge            │
│     • Vendor provides new identifiers → enrich and activate                    │
│     • Analyst confirms entity is real and unique                               │
│                                                                                 │
│  2. PROVISIONAL → MERGED                                                        │
│     • Later enrichment finds it matches existing entity                        │
│     • Analyst identifies as duplicate                                          │
│     • Creates merge proposal → approve → execute                               │
│                                                                                 │
│  3. PROVISIONAL → REJECTED                                                      │
│     • Analyst determines mention was not an entity                             │
│     • False positive from NLP extraction                                       │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Provisional Creation Evidence

```python
# When py-sec-edgar creates provisional:
result = resolver.create_provisional(
    name="Acme Private Holdings LLC",
    entity_type="COMPANY",
    evidence_uri="sec://0000320193-24-000081/10-K#item1:char=15432-15458",
    evidence_text="...our supplier Acme Private Holdings LLC provides...",
    source_system="py-sec-edgar",
)

# entityspine creates:
# 1. Entity record with status='provisional'
# 2. Alias record linking name to entity
# 3. Claim record with evidence_uri pointing to filing
```

### Merge Proposal (Not Auto-Merge)

```python
# Later, enrichment process discovers Acme matches known entity
# py-sec-edgar or enrichment service proposes merge:

proposal_id = resolver.propose_merge(
    source_entity_id=provisional_entity_id,  # Acme provisional
    target_entity_id=known_entity_id,        # Known entity from vendor
    evidence_uri="file:///crosswalks/factset_2024.csv:row=5432",
    reason="FactSet crosswalk shows same LEI",
)

# entityspine creates:
# 1. Merge proposal record (not executed)
# 2. Status = 'pending_review'

# Analyst reviews and approves:
# 3. entityspine executes merge
# 4. provisional.merged_into_id = known_entity_id
# 5. provisional.status = 'merged'
# 6. Redirect chain preserved
```

---

## Error Handling Contract

### Expected Errors

```python
from py_sec_edgar.ports.entity_resolver import EntityResolverPort

class EntityNotFoundError(Exception):
    """Entity ID does not exist."""
    pass

class EntityMergedError(Exception):
    """Entity was merged, use redirect."""
    def __init__(self, original_id: str, canonical_id: str, chain: list[str]):
        self.original_id = original_id
        self.canonical_id = canonical_id
        self.chain = chain

class ResolutionError(Exception):
    """Resolution failed."""
    pass

class ProvisionalCreationError(Exception):
    """Failed to create provisional entity."""
    pass
```

### Error Handling in py-sec-edgar

```python
def process_mention(mention: EntityMention, resolver: EntityResolverPort):
    """Process a mention with proper error handling."""
    try:
        result = resolver.resolve(mention.mention_text)
        
        if result.best and result.best.score >= 0.7:
            mention.resolved_entity_id = result.best.entity_id
            mention.resolution_status = 'resolved'
        else:
            # Try to create provisional
            try:
                entity_id = resolver.create_provisional(
                    name=mention.mention_text,
                    evidence_uri=f"sec://{mention.filing_accession}",
                )
                mention.resolved_entity_id = entity_id
                mention.resolution_status = 'provisional'
            except ProvisionalCreationError as e:
                logger.warning(f"Could not create provisional: {e}")
                mention.resolution_status = 'unresolvable'
                
    except ResolutionError as e:
        logger.error(f"Resolution failed: {e}")
        mention.resolution_status = 'error'
        mention.resolution_notes = str(e)
```

---

## Testing Contract

### What py-sec-edgar Tests

```python
# tests/unit/adapters/test_entity_adapter.py
"""
py-sec-edgar tests its adapter against the port interface.
Uses mocks or null adapter - does NOT require entityspine.
"""

import pytest
from unittest.mock import Mock
from py_sec_edgar.adapters.entityspine_adapter import EntitySpineAdapter
from py_sec_edgar.ports.entity_resolver import ResolutionResult, ResolutionCandidate


def test_resolve_returns_resolution_result():
    """Adapter returns proper ResolutionResult type."""
    # Arrange
    mock_resolver = Mock()
    mock_resolver.resolve.return_value = MockResult(...)
    adapter = EntitySpineAdapter(resolver=mock_resolver)
    
    # Act
    result = adapter.resolve("AAPL")
    
    # Assert
    assert isinstance(result, ResolutionResult)
    assert result.query == "AAPL"


def test_resolve_empty_returns_empty_candidates():
    """Empty resolution returns empty list, not None."""
    adapter = create_adapter_with_empty_results()
    
    result = adapter.resolve("nonexistent")
    
    assert result.candidates == []
    assert result.best is None


def test_get_follows_redirects():
    """Get follows merge redirects transparently."""
    # Entity A merged into B
    adapter = create_adapter_with_merged_entity("A", "B")
    
    entity = adapter.get("A")
    
    # Should return B, not A
    assert entity.entity_id == "B"
```

### What entityspine Tests

```python
# entityspine/tests/integration/test_resolver.py
"""
entityspine tests its resolver implementation.
"""

def test_resolve_cik_returns_single_candidate():
    """CIK resolution should return single high-confidence match."""
    store = create_test_store()
    store.add_entity_with_cik("01ABC...", "0000320193")
    resolver = EntityResolver(store)
    
    result = resolver.resolve("0000320193")
    
    assert len(result.candidates) == 1
    assert result.candidates[0].score == 1.0
    assert result.candidates[0].matched_scheme == "cik"


def test_resolve_ticker_respects_as_of():
    """Ticker resolution respects point-in-time."""
    store = create_test_store()
    # AAPL was Company A until 1995, Company B after
    store.add_listing("AAPL", entity_id="A", valid_from="1985-01-01", valid_to="1995-12-31")
    store.add_listing("AAPL", entity_id="B", valid_from="1996-01-01", valid_to=None)
    resolver = EntityResolver(store)
    
    result_1990 = resolver.resolve("AAPL", as_of=date(1990, 1, 1))
    result_2024 = resolver.resolve("AAPL", as_of=date(2024, 1, 1))
    
    assert result_1990.best.entity_id == "A"
    assert result_2024.best.entity_id == "B"
```

---

## Summary: Integration Rules

### py-sec-edgar MUST:

1. **Store only entity_id references** - never cache entity attributes
2. **Store evidence pointers** - link mentions to filings/sections
3. **Handle ambiguity** - store resolution_candidates for review
4. **Use port interface** - never import entityspine directly in core
5. **Request provisional creation** - don't create entities directly

### entityspine MUST:

1. **Return ranked candidates** - never single result from resolve()
2. **Follow redirects on get()** - merged entities return canonical
3. **Provide evidence on claims** - every identifier has provenance
4. **Never auto-merge** - merges require proposal → approval → execute
5. **Preserve old IDs forever** - redirects, never delete

---

*Companion to Unified Data Model v2.2 | January 2026*
