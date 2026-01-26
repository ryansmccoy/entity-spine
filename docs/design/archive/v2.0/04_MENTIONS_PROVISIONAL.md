# Entity Master v2 - Mentions, Private Entities, and Provisional Workflow

**Handling unknown/private entity mentions extracted from SEC filings**

---

## The Problem

When parsing SEC filings, we encounter entity mentions that don't exist in our canonical database:

```
From AAPL 10-K filing:
"Our significant suppliers include Taiwan Semiconductor Manufacturing Company,
 Foxconn Technology Group, and various private component suppliers including 
 Advanced Silicon Technologies LLC and MicroPrecision Components Inc."
```

- **Taiwan Semiconductor**, **Foxconn**: Public companies with CIKs → can resolve
- **Advanced Silicon Technologies LLC**, **MicroPrecision Components Inc.**: Likely private → no CIK

**We MUST support these private mentions without:**
1. Polluting the entity database with garbage
2. Creating duplicate entities for each mention variation
3. Losing the extracted relationships

---

## Design Principles

### Rule 1: Mentions ≠ Entities

A **mention** is an occurrence of a name in text. An **entity** is a canonical record in our database.

```
┌────────────────────────────────────────────────────────────────────────────────────────────┐
│  mentions table                          entities table                                     │
│  ──────────────                          ──────────────                                     │
│                                                                                             │
│  "Apple Inc." in 10-K §1.1   ─────────►  Entity: Apple Inc. (CIK 320193)                   │
│  "Apple Computer" in 8-K     ─────────►  [resolved to same entity via alias]               │
│  "Advanced Silicon Tech"     ─────────►  ???                                               │
│                               ▲                                                             │
│                               │                                                             │
│                               RESOLUTION REQUIRED                                           │
│                                                                                             │
└────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Rule 2: Provisional Entities Are Quarantined

Provisional entities live in a separate status, not mixed with confirmed entities:

```python
class EntityStatus(Enum):
    ACTIVE = 'active'          # Confirmed, has authoritative ID
    PROVISIONAL = 'provisional' # Created from mention, needs verification
    MERGED = 'merged'          # Merged into another entity
    INACTIVE = 'inactive'      # Dissolved, delisted, etc.
```

### Rule 3: Resolution Is Multi-Stage

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                        MENTION → ENTITY RESOLUTION PIPELINE                              │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                          │
│  STAGE 1: EXTRACTION                                                                     │
│  ─────────────────────                                                                   │
│  Filing text → NER/regex → Raw mentions with context                                     │
│                                                                                          │
│  STAGE 2: NORMALIZATION                                                                  │
│  ─────────────────────                                                                   │
│  "Apple Inc." → "APPLE", suffix stripped                                                 │
│  "Advanced Silicon Technologies, LLC" → "ADVANCED SILICON TECHNOLOGIES"                  │
│                                                                                          │
│  STAGE 3: CANDIDATE LOOKUP                                                               │
│  ─────────────────────────                                                               │
│  Query entity_aliases table for exact/fuzzy match                                        │
│  Check existing provisional entities for near-duplicates                                 │
│                                                                                          │
│  STAGE 4: RESOLUTION DECISION                                                            │
│  ──────────────────────────                                                              │
│  ┌───────────────────────────────────────────────────────────────────┐                   │
│  │ If exact match → resolve to existing entity                       │                   │
│  │ If fuzzy match (>0.85) → resolve with lower confidence            │                   │
│  │ If no match + has CIK hint → create ACTIVE entity                 │                   │
│  │ If no match + public company → queue for enrichment               │                   │
│  │ If no match + likely private → create PROVISIONAL entity          │                   │
│  └───────────────────────────────────────────────────────────────────┘                   │
│                                                                                          │
│  STAGE 5: ENTITY CREATION (if needed)                                                    │
│  ───────────────────────────────────                                                     │
│  Create provisional entity with all available metadata                                   │
│  Link mention to provisional entity                                                      │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Data Model

### Extended mentions Table

```sql
CREATE TABLE mentions (
    mention_id      TEXT PRIMARY KEY,  -- ULID
    
    -- Source context
    filing_id       TEXT NOT NULL,     -- FK to filings
    section_path    TEXT,              -- e.g., 'Item 1.01/Risk Factors/Para 3'
    sentence_idx    INTEGER,           -- Sentence number in section
    char_offset     INTEGER,           -- Character offset in document
    char_length     INTEGER,           -- Length of mention span
    
    -- Extracted text
    raw_text        TEXT NOT NULL,     -- Exact text: "Apple Inc."
    
    -- Context (for disambiguation)
    context_before  TEXT,              -- 50 chars before
    context_after   TEXT,              -- 50 chars after
    context_sentence TEXT,             -- Full sentence
    
    -- Normalized form
    normalized_name TEXT NOT NULL,     -- "APPLE"
    name_hash       TEXT NOT NULL,     -- SHA256 of normalized name (for dedup)
    
    -- Extraction metadata
    extraction_method TEXT,            -- 'ner_spacy', 'regex_org', 'llm_gpt4'
    extraction_confidence REAL,        -- 0.0-1.0
    entity_type     TEXT,              -- 'organization', 'person', 'location'
    
    -- Resolution status
    resolution_status TEXT DEFAULT 'pending',  -- 'pending', 'resolved', 'unresolvable', 'manual_review'
    resolved_entity_id TEXT,           -- FK to entities (if resolved)
    resolution_confidence REAL,        -- Confidence in the resolution
    resolution_method TEXT,            -- 'exact_alias', 'fuzzy_match', 'manual', 'llm'
    resolved_at     TIMESTAMPTZ,
    resolved_by     TEXT,              -- 'system', user_id
    
    -- Hints from context
    hints           JSONB,             -- {'ticker': 'AAPL', 'cik_hint': '320193', ...}
    
    -- Audit
    created_at      TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (resolved_entity_id) REFERENCES entities(entity_id)
);

CREATE INDEX idx_mentions_normalized ON mentions(normalized_name);
CREATE INDEX idx_mentions_hash ON mentions(name_hash);
CREATE INDEX idx_mentions_status ON mentions(resolution_status);
CREATE INDEX idx_mentions_resolved ON mentions(resolved_entity_id) WHERE resolved_entity_id IS NOT NULL;
CREATE INDEX idx_mentions_filing ON mentions(filing_id);
```

### provisional_entities View

```sql
-- View of entities that are provisional
CREATE VIEW provisional_entities AS
SELECT 
    e.*,
    COUNT(m.mention_id) AS mention_count,
    MIN(m.created_at) AS first_mention_at,
    MAX(m.created_at) AS last_mention_at,
    ARRAY_AGG(DISTINCT m.filing_id) AS source_filings
FROM entities e
LEFT JOIN mentions m ON m.resolved_entity_id = e.entity_id
WHERE e.status = 'provisional'
GROUP BY e.entity_id;
```

### Deduplication Tracking

```sql
CREATE TABLE mention_clusters (
    cluster_id      TEXT PRIMARY KEY,  -- ULID
    canonical_name  TEXT NOT NULL,     -- Best name for this cluster
    normalized_name TEXT NOT NULL,     -- Normalized form
    
    -- Stats
    mention_count   INTEGER DEFAULT 0,
    unique_filings  INTEGER DEFAULT 0,
    first_seen_at   TIMESTAMPTZ,
    last_seen_at    TIMESTAMPTZ,
    
    -- Resolution
    resolved_entity_id TEXT,           -- FK to entities (if cluster resolved)
    resolution_status TEXT DEFAULT 'pending',
    
    created_at      TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Many mentions can belong to one cluster
ALTER TABLE mentions ADD COLUMN cluster_id TEXT REFERENCES mention_clusters(cluster_id);
CREATE INDEX idx_mentions_cluster ON mentions(cluster_id);
```

---

## Implementation

### Stage 1: Mention Extraction

```python
from dataclasses import dataclass
from typing import Optional, List, Dict
from datetime import datetime
import hashlib
import re


@dataclass
class ExtractedMention:
    """A mention extracted from filing text."""
    raw_text: str
    char_offset: int
    char_length: int
    context_before: str
    context_after: str
    context_sentence: str
    extraction_method: str
    extraction_confidence: float
    entity_type: str
    hints: Dict[str, str] = None


class MentionExtractor:
    """Extract entity mentions from SEC filing text."""
    
    def __init__(self, nlp_model=None):
        self.nlp = nlp_model  # spaCy or similar
        
        # Patterns for extracting hints
        self.cik_pattern = re.compile(r'\(CIK[:\s]+(\d{10})\)')
        self.ticker_pattern = re.compile(r'\((?:NYSE|NASDAQ|AMEX)[:\s]+([A-Z]{1,5})\)')
    
    def extract_from_section(
        self,
        text: str,
        filing_id: str,
        section_path: str,
    ) -> List[ExtractedMention]:
        """Extract all entity mentions from a section of text."""
        
        mentions = []
        
        # Method 1: NER extraction
        if self.nlp:
            doc = self.nlp(text)
            for ent in doc.ents:
                if ent.label_ in ('ORG', 'COMPANY', 'GPE'):
                    mention = self._create_mention(
                        text=text,
                        start=ent.start_char,
                        end=ent.end_char,
                        raw_text=ent.text,
                        method='ner_spacy',
                        entity_type='organization' if ent.label_ in ('ORG', 'COMPANY') else 'location',
                        confidence=0.8,
                    )
                    mentions.append(mention)
        
        # Method 2: Pattern-based extraction for company suffixes
        company_pattern = re.compile(
            r'([A-Z][A-Za-z0-9\s&\-\']+\s+'
            r'(?:Inc\.?|Corp\.?|Corporation|LLC|LP|LLP|Ltd\.?|Limited|Company|Co\.?|Group))',
            re.MULTILINE
        )
        
        for match in company_pattern.finditer(text):
            # Avoid duplicates with NER
            if not any(m.char_offset == match.start() for m in mentions):
                mention = self._create_mention(
                    text=text,
                    start=match.start(),
                    end=match.end(),
                    raw_text=match.group(1),
                    method='regex_org',
                    entity_type='organization',
                    confidence=0.6,
                )
                mentions.append(mention)
        
        # Extract hints for each mention
        for mention in mentions:
            mention.hints = self._extract_hints(text, mention)
        
        return mentions
    
    def _create_mention(
        self,
        text: str,
        start: int,
        end: int,
        raw_text: str,
        method: str,
        entity_type: str,
        confidence: float,
    ) -> ExtractedMention:
        """Create a mention with context."""
        
        # Extract context
        context_before = text[max(0, start - 50):start].strip()
        context_after = text[end:min(len(text), end + 50)].strip()
        
        # Find sentence boundaries
        sentence_start = text.rfind('.', 0, start)
        sentence_end = text.find('.', end)
        context_sentence = text[
            sentence_start + 1 if sentence_start != -1 else 0:
            sentence_end + 1 if sentence_end != -1 else len(text)
        ].strip()
        
        return ExtractedMention(
            raw_text=raw_text,
            char_offset=start,
            char_length=end - start,
            context_before=context_before,
            context_after=context_after,
            context_sentence=context_sentence,
            extraction_method=method,
            extraction_confidence=confidence,
            entity_type=entity_type,
        )
    
    def _extract_hints(self, text: str, mention: ExtractedMention) -> Dict:
        """Extract identifying hints from surrounding context."""
        
        hints = {}
        search_range = 200  # chars around mention
        
        start = max(0, mention.char_offset - search_range)
        end = min(len(text), mention.char_offset + mention.char_length + search_range)
        context = text[start:end]
        
        # Look for CIK
        cik_match = self.cik_pattern.search(context)
        if cik_match:
            hints['cik'] = cik_match.group(1)
        
        # Look for ticker
        ticker_match = self.ticker_pattern.search(context)
        if ticker_match:
            hints['ticker'] = ticker_match.group(1)
        
        # Check for common phrases indicating public/private
        if 'publicly traded' in context.lower() or 'SEC' in context:
            hints['likely_public'] = True
        elif 'private' in context.lower() or 'privately held' in context.lower():
            hints['likely_private'] = True
        
        return hints
```

### Stage 2: Normalization

```python
import unicodedata


def normalize_company_name(name: str) -> str:
    """
    Normalize company name for matching.
    
    - Uppercase
    - Remove legal suffixes (Inc, Corp, LLC, etc.)
    - Remove punctuation
    - Collapse whitespace
    - Handle Unicode
    """
    
    if not name:
        return ''
    
    # Normalize Unicode
    name = unicodedata.normalize('NFKD', name)
    name = name.encode('ASCII', 'ignore').decode('ASCII')
    
    # Uppercase
    name = name.upper()
    
    # Remove legal suffixes
    suffixes = [
        r'\s+INCORPORATED$',
        r'\s+INC\.?$',
        r'\s+CORPORATION$',
        r'\s+CORP\.?$',
        r'\s+LIMITED$',
        r'\s+LTD\.?$',
        r'\s+LLC$',
        r'\s+L\.L\.C\.?$',
        r'\s+LP$',
        r'\s+L\.P\.?$',
        r'\s+LLP$',
        r'\s+L\.L\.P\.?$',
        r'\s+PLC$',
        r'\s+P\.L\.C\.?$',
        r'\s+COMPANY$',
        r'\s+CO\.?$',
        r'\s+GROUP$',
        r'\s+HOLDINGS?$',
        r'\s+INTERNATIONAL$',
        r'\s+INT\'?L\.?$',
        r',?\s*THE$',
        r'^THE\s+',
    ]
    
    for pattern in suffixes:
        name = re.sub(pattern, '', name)
    
    # Remove punctuation except &
    name = re.sub(r'[^\w\s&]', '', name)
    
    # Collapse whitespace
    name = ' '.join(name.split())
    
    return name.strip()


def compute_name_hash(normalized_name: str) -> str:
    """Compute hash of normalized name for deduplication."""
    return hashlib.sha256(normalized_name.encode('utf-8')).hexdigest()[:16]


def compute_fuzzy_keys(normalized_name: str) -> List[str]:
    """
    Compute fuzzy keys for blocking.
    
    Returns multiple keys to catch common variations.
    """
    keys = []
    
    # Key 1: First 4 chars
    if len(normalized_name) >= 4:
        keys.append(f"prefix:{normalized_name[:4]}")
    
    # Key 2: Sorted words (order-independent)
    words = sorted(normalized_name.split())
    keys.append(f"sorted:{' '.join(words[:3])}")
    
    # Key 3: Consonant skeleton
    consonants = re.sub(r'[AEIOU\s]', '', normalized_name)
    if len(consonants) >= 4:
        keys.append(f"consonants:{consonants[:8]}")
    
    # Key 4: First word
    first_word = normalized_name.split()[0] if normalized_name.split() else ''
    if len(first_word) >= 3:
        keys.append(f"first:{first_word}")
    
    return keys
```

### Stage 3: Candidate Lookup

```python
from dataclasses import dataclass
from typing import Optional, List, Tuple


@dataclass
class ResolutionCandidate:
    """A potential entity match for a mention."""
    entity_id: str
    entity_name: str
    entity_status: str  # 'active', 'provisional'
    match_type: str     # 'exact', 'alias', 'fuzzy', 'cluster'
    confidence: float
    matched_on: str     # What we matched: 'name', 'alias', 'cik', 'ticker'


class CandidateFinder:
    """Find resolution candidates for mentions."""
    
    def __init__(self, db):
        self.db = db
    
    async def find_candidates(
        self,
        mention: ExtractedMention,
        normalized_name: str,
        name_hash: str,
    ) -> List[ResolutionCandidate]:
        """Find all potential entity matches for a mention."""
        
        candidates = []
        
        # Method 1: Exact match on alias
        exact_matches = await self._find_exact_alias_matches(normalized_name)
        candidates.extend(exact_matches)
        
        # Method 2: CIK hint (highest priority)
        if mention.hints and mention.hints.get('cik'):
            cik_match = await self._find_by_cik(mention.hints['cik'])
            if cik_match:
                candidates.append(cik_match)
        
        # Method 3: Ticker hint
        if mention.hints and mention.hints.get('ticker'):
            ticker_matches = await self._find_by_ticker(mention.hints['ticker'])
            candidates.extend(ticker_matches)
        
        # Method 4: Fuzzy match (if no exact matches)
        if not candidates:
            fuzzy_matches = await self._find_fuzzy_matches(normalized_name)
            candidates.extend(fuzzy_matches)
        
        # Method 5: Cluster match (existing provisional entities)
        cluster_matches = await self._find_cluster_matches(name_hash, normalized_name)
        candidates.extend(cluster_matches)
        
        # Sort by confidence, deduplicate by entity_id
        seen = set()
        unique_candidates = []
        for c in sorted(candidates, key=lambda x: -x.confidence):
            if c.entity_id not in seen:
                seen.add(c.entity_id)
                unique_candidates.append(c)
        
        return unique_candidates
    
    async def _find_exact_alias_matches(
        self,
        normalized_name: str,
    ) -> List[ResolutionCandidate]:
        """Find entities with exact alias match."""
        
        results = await self.db.fetch_all("""
            SELECT 
                a.entity_id,
                e.primary_name,
                e.status,
                a.alias_name,
                a.alias_type
            FROM entity_aliases a
            JOIN entities e ON e.entity_id = a.entity_id
            WHERE a.name_normalized = :name
              AND e.status IN ('active', 'provisional')
        """, {'name': normalized_name})
        
        return [
            ResolutionCandidate(
                entity_id=r['entity_id'],
                entity_name=r['primary_name'],
                entity_status=r['status'],
                match_type='alias' if r['alias_type'] != 'primary' else 'exact',
                confidence=0.95,
                matched_on='alias',
            )
            for r in results
        ]
    
    async def _find_by_cik(self, cik: str) -> Optional[ResolutionCandidate]:
        """Find entity by CIK."""
        
        cik_padded = cik.zfill(10)
        
        result = await self.db.fetch_one("""
            SELECT 
                i.entity_id,
                e.primary_name,
                e.status
            FROM identifiers i
            JOIN entities e ON e.entity_id = i.entity_id
            WHERE i.scheme = 'cik' AND i.value = :cik
              AND e.status IN ('active', 'provisional')
        """, {'cik': cik_padded})
        
        if result:
            return ResolutionCandidate(
                entity_id=result['entity_id'],
                entity_name=result['primary_name'],
                entity_status=result['status'],
                match_type='exact',
                confidence=0.99,
                matched_on='cik',
            )
        
        return None
    
    async def _find_by_ticker(self, ticker: str) -> List[ResolutionCandidate]:
        """Find entity by ticker symbol."""
        
        results = await self.db.fetch_all("""
            SELECT 
                l.listing_id,
                s.security_id,
                s.issuer_entity_id,
                e.primary_name,
                e.status
            FROM listings l
            JOIN securities s ON s.security_id = l.security_id
            JOIN entities e ON e.entity_id = s.issuer_entity_id
            WHERE l.ticker = :ticker
              AND l.status = 'active'
              AND e.status IN ('active', 'provisional')
        """, {'ticker': ticker.upper()})
        
        return [
            ResolutionCandidate(
                entity_id=r['issuer_entity_id'],
                entity_name=r['primary_name'],
                entity_status=r['status'],
                match_type='derived',
                confidence=0.85,
                matched_on='ticker',
            )
            for r in results
        ]
    
    async def _find_fuzzy_matches(
        self,
        normalized_name: str,
        threshold: float = 0.85,
    ) -> List[ResolutionCandidate]:
        """Find fuzzy matches using trigram similarity."""
        
        results = await self.db.fetch_all("""
            SELECT 
                a.entity_id,
                e.primary_name,
                e.status,
                a.alias_name,
                similarity(a.name_normalized, :name) AS sim
            FROM entity_aliases a
            JOIN entities e ON e.entity_id = a.entity_id
            WHERE a.name_normalized % :name
              AND e.status IN ('active', 'provisional')
            ORDER BY sim DESC
            LIMIT 10
        """, {'name': normalized_name})
        
        return [
            ResolutionCandidate(
                entity_id=r['entity_id'],
                entity_name=r['primary_name'],
                entity_status=r['status'],
                match_type='fuzzy',
                confidence=min(r['sim'], 0.90),  # Cap fuzzy at 0.90
                matched_on='fuzzy_name',
            )
            for r in results
            if r['sim'] >= threshold
        ]
    
    async def _find_cluster_matches(
        self,
        name_hash: str,
        normalized_name: str,
    ) -> List[ResolutionCandidate]:
        """Find existing mention clusters that match."""
        
        results = await self.db.fetch_all("""
            SELECT 
                c.cluster_id,
                c.canonical_name,
                c.resolved_entity_id,
                e.primary_name,
                e.status
            FROM mention_clusters c
            LEFT JOIN entities e ON e.entity_id = c.resolved_entity_id
            WHERE c.normalized_name = :name
               OR c.cluster_id IN (
                   SELECT cluster_id FROM mention_fuzzy_keys
                   WHERE fuzzy_key IN (
                       SELECT unnest(:keys::text[])
                   )
               )
        """, {
            'name': normalized_name,
            'keys': compute_fuzzy_keys(normalized_name),
        })
        
        candidates = []
        for r in results:
            if r['resolved_entity_id']:
                candidates.append(ResolutionCandidate(
                    entity_id=r['resolved_entity_id'],
                    entity_name=r['primary_name'],
                    entity_status=r['status'],
                    match_type='cluster',
                    confidence=0.80,
                    matched_on='mention_cluster',
                ))
        
        return candidates
```

### Stage 4: Resolution Decision

```python
@dataclass
class ResolutionDecision:
    """The decision for resolving a mention."""
    action: str  # 'resolve', 'create_provisional', 'queue_enrichment', 'queue_review'
    entity_id: Optional[str] = None
    cluster_id: Optional[str] = None
    confidence: float = 0.0
    reason: str = ''


class MentionResolver:
    """Resolve mentions to entities."""
    
    def __init__(self, db, candidate_finder, entity_creator):
        self.db = db
        self.finder = candidate_finder
        self.creator = entity_creator
        
        # Thresholds
        self.AUTO_RESOLVE_THRESHOLD = 0.90
        self.FUZZY_RESOLVE_THRESHOLD = 0.85
        self.CLUSTER_THRESHOLD = 0.80
    
    async def resolve_mention(
        self,
        mention: ExtractedMention,
        filing_id: str,
        section_path: str,
    ) -> ResolutionDecision:
        """
        Resolve a single mention.
        
        Decision tree:
        1. If CIK hint → resolve with high confidence
        2. If exact alias match → resolve
        3. If fuzzy match > threshold → resolve with lower confidence
        4. If looks like public company → queue for enrichment
        5. Otherwise → create/join provisional cluster
        """
        
        normalized = normalize_company_name(mention.raw_text)
        name_hash = compute_name_hash(normalized)
        
        # Find candidates
        candidates = await self.finder.find_candidates(mention, normalized, name_hash)
        
        # Decision logic
        if not candidates:
            return await self._handle_no_candidates(mention, normalized, name_hash)
        
        best = candidates[0]
        
        # High-confidence match (CIK or exact alias)
        if best.confidence >= self.AUTO_RESOLVE_THRESHOLD:
            return ResolutionDecision(
                action='resolve',
                entity_id=best.entity_id,
                confidence=best.confidence,
                reason=f"High-confidence {best.match_type} match on {best.matched_on}",
            )
        
        # Fuzzy match - resolve but with lower confidence
        if best.match_type == 'fuzzy' and best.confidence >= self.FUZZY_RESOLVE_THRESHOLD:
            return ResolutionDecision(
                action='resolve',
                entity_id=best.entity_id,
                confidence=best.confidence,
                reason=f"Fuzzy match (similarity={best.confidence:.2f})",
            )
        
        # Cluster match - join existing cluster
        if best.match_type == 'cluster' and best.confidence >= self.CLUSTER_THRESHOLD:
            return ResolutionDecision(
                action='resolve',
                entity_id=best.entity_id,
                confidence=best.confidence,
                reason="Matched existing mention cluster",
            )
        
        # Ambiguous - multiple similar candidates
        if len(candidates) > 1 and candidates[1].confidence > 0.70:
            return ResolutionDecision(
                action='queue_review',
                reason=f"Ambiguous: {len(candidates)} candidates with similar confidence",
            )
        
        # No good match
        return await self._handle_no_candidates(mention, normalized, name_hash)
    
    async def _handle_no_candidates(
        self,
        mention: ExtractedMention,
        normalized: str,
        name_hash: str,
    ) -> ResolutionDecision:
        """Handle case with no good resolution candidates."""
        
        # Check if likely public company
        if mention.hints and mention.hints.get('likely_public'):
            return ResolutionDecision(
                action='queue_enrichment',
                reason="Likely public company, needs external lookup",
            )
        
        # Check for existing cluster
        cluster = await self._find_or_create_cluster(normalized, name_hash)
        
        if cluster['resolved_entity_id']:
            # Cluster already resolved
            return ResolutionDecision(
                action='resolve',
                entity_id=cluster['resolved_entity_id'],
                cluster_id=cluster['cluster_id'],
                confidence=0.75,
                reason="Joined existing resolved cluster",
            )
        
        if cluster['mention_count'] >= 3:
            # Cluster has enough mentions - create provisional entity
            entity_id = await self._create_provisional_from_cluster(cluster)
            return ResolutionDecision(
                action='resolve',
                entity_id=entity_id,
                cluster_id=cluster['cluster_id'],
                confidence=0.70,
                reason="Created provisional entity from cluster",
            )
        
        # Just join the cluster, don't create entity yet
        return ResolutionDecision(
            action='create_provisional',
            cluster_id=cluster['cluster_id'],
            confidence=0.50,
            reason="Added to cluster, waiting for more mentions",
        )
    
    async def _find_or_create_cluster(
        self,
        normalized: str,
        name_hash: str,
    ) -> dict:
        """Find existing cluster or create new one."""
        
        # Try exact match
        cluster = await self.db.fetch_one("""
            SELECT * FROM mention_clusters
            WHERE normalized_name = :name
        """, {'name': normalized})
        
        if cluster:
            return dict(cluster)
        
        # Try fuzzy match on existing clusters
        fuzzy_keys = compute_fuzzy_keys(normalized)
        
        cluster = await self.db.fetch_one("""
            SELECT c.* FROM mention_clusters c
            JOIN mention_fuzzy_keys k ON k.cluster_id = c.cluster_id
            WHERE k.fuzzy_key = ANY(:keys)
            ORDER BY similarity(c.normalized_name, :name) DESC
            LIMIT 1
        """, {'keys': fuzzy_keys, 'name': normalized})
        
        if cluster:
            return dict(cluster)
        
        # Create new cluster
        cluster_id = generate_ulid()
        
        await self.db.execute("""
            INSERT INTO mention_clusters (
                cluster_id, canonical_name, normalized_name,
                mention_count, first_seen_at
            ) VALUES (
                :id, :canonical, :normalized, 0, NOW()
            )
        """, {
            'id': cluster_id,
            'canonical': normalized.title(),  # Title case for display
            'normalized': normalized,
        })
        
        # Insert fuzzy keys
        for key in fuzzy_keys:
            await self.db.execute("""
                INSERT INTO mention_fuzzy_keys (cluster_id, fuzzy_key)
                VALUES (:cluster_id, :key)
            """, {'cluster_id': cluster_id, 'key': key})
        
        return {
            'cluster_id': cluster_id,
            'canonical_name': normalized.title(),
            'normalized_name': normalized,
            'mention_count': 0,
            'resolved_entity_id': None,
        }
    
    async def _create_provisional_from_cluster(self, cluster: dict) -> str:
        """Create a provisional entity from a mention cluster."""
        
        entity_id = await self.creator.create_provisional_entity(
            name=cluster['canonical_name'],
            source_type='mention_cluster',
            source_id=cluster['cluster_id'],
        )
        
        # Update cluster
        await self.db.execute("""
            UPDATE mention_clusters SET
                resolved_entity_id = :entity_id,
                resolution_status = 'resolved'
            WHERE cluster_id = :cluster_id
        """, {
            'entity_id': entity_id,
            'cluster_id': cluster['cluster_id'],
        })
        
        # Update all mentions in cluster
        await self.db.execute("""
            UPDATE mentions SET
                resolved_entity_id = :entity_id,
                resolution_status = 'resolved',
                resolution_method = 'cluster_promotion',
                resolution_confidence = 0.70,
                resolved_at = NOW()
            WHERE cluster_id = :cluster_id
        """, {
            'entity_id': entity_id,
            'cluster_id': cluster['cluster_id'],
        })
        
        return entity_id
```

### Stage 5: Provisional Entity Creation

```python
class ProvisionalEntityCreator:
    """Create and manage provisional entities."""
    
    def __init__(self, db):
        self.db = db
    
    async def create_provisional_entity(
        self,
        name: str,
        source_type: str,  # 'mention', 'mention_cluster', 'manual'
        source_id: str,
        hints: dict = None,
    ) -> str:
        """
        Create a provisional entity.
        
        Provisional entities have:
        - status = 'provisional'
        - No CIK or LEI (yet)
        - Source tracking
        - Lower trust level
        """
        
        entity_id = generate_ulid()
        normalized = normalize_company_name(name)
        
        # Check for near-duplicates first
        existing = await self._check_duplicate_provisional(normalized)
        if existing:
            return existing
        
        await self.db.execute("""
            INSERT INTO entities (
                entity_id,
                primary_name,
                entity_type,
                status,
                source_type,
                source_id,
                trust_level,
                created_at,
                updated_at
            ) VALUES (
                :id,
                :name,
                'organization',
                'provisional',
                :source_type,
                :source_id,
                'low',
                NOW(),
                NOW()
            )
        """, {
            'id': entity_id,
            'name': name,
            'source_type': source_type,
            'source_id': source_id,
        })
        
        # Create primary alias
        await self.db.execute("""
            INSERT INTO entity_aliases (
                alias_id, entity_id, alias_name, name_normalized,
                alias_type, source
            ) VALUES (
                :alias_id, :entity_id, :name, :normalized,
                'primary', 'provisional_creation'
            )
        """, {
            'alias_id': generate_ulid(),
            'entity_id': entity_id,
            'name': name,
            'normalized': normalized,
        })
        
        # Store hints for later enrichment
        if hints:
            await self.db.execute("""
                INSERT INTO provisional_entity_hints (
                    entity_id, hints, created_at
                ) VALUES (:entity_id, :hints, NOW())
            """, {
                'entity_id': entity_id,
                'hints': json.dumps(hints),
            })
        
        return entity_id
    
    async def _check_duplicate_provisional(
        self,
        normalized: str,
    ) -> Optional[str]:
        """Check if a similar provisional entity already exists."""
        
        result = await self.db.fetch_one("""
            SELECT e.entity_id 
            FROM entities e
            JOIN entity_aliases a ON a.entity_id = e.entity_id
            WHERE e.status = 'provisional'
              AND a.name_normalized = :name
        """, {'name': normalized})
        
        return result['entity_id'] if result else None
```

---

## Guardrails Against Entity Explosion

### Rule 1: Cluster Before Creating

Never create a provisional entity from a single mention. Wait for:
- 3+ mentions of same normalized name, OR
- 2+ mentions from different filings, OR
- Manual review confirms creation

```python
MIN_MENTIONS_FOR_PROVISIONAL = 3
MIN_FILINGS_FOR_PROVISIONAL = 2

async def should_create_provisional(cluster: dict) -> bool:
    return (
        cluster['mention_count'] >= MIN_MENTIONS_FOR_PROVISIONAL
        or cluster['unique_filings'] >= MIN_FILINGS_FOR_PROVISIONAL
    )
```

### Rule 2: Fuzzy Deduplication on Provisionals

Before creating a new provisional, always check existing provisionals:

```python
async def check_similar_provisionals(normalized: str) -> List[str]:
    """Find existing provisionals that might be duplicates."""
    
    return await db.fetch_all("""
        SELECT entity_id, primary_name, similarity(a.name_normalized, :name) as sim
        FROM entities e
        JOIN entity_aliases a ON a.entity_id = e.entity_id
        WHERE e.status = 'provisional'
          AND a.name_normalized % :name
          AND similarity(a.name_normalized, :name) > 0.7
        ORDER BY sim DESC
        LIMIT 5
    """, {'name': normalized})
```

### Rule 3: Periodic Cleanup

Scheduled job to clean up orphaned provisionals:

```python
async def cleanup_stale_provisionals():
    """
    Remove provisional entities that:
    - Have no mentions for 90 days
    - Have only 1 mention total
    - Were never enriched
    """
    
    await db.execute("""
        DELETE FROM entities
        WHERE status = 'provisional'
          AND entity_id NOT IN (
              SELECT resolved_entity_id FROM mentions
              WHERE resolved_entity_id IS NOT NULL
                AND created_at > NOW() - INTERVAL '90 days'
          )
          AND entity_id NOT IN (
              SELECT entity_id FROM identifiers
          )
          AND created_at < NOW() - INTERVAL '90 days'
    """)
```

### Rule 4: Enrichment Promotion

Provisional → Active when we get authoritative ID:

```python
async def promote_provisional_to_active(
    entity_id: str,
    identifier_scheme: str,
    identifier_value: str,
) -> bool:
    """
    Promote a provisional entity to active status
    when we receive an authoritative identifier.
    """
    
    # Verify entity is provisional
    entity = await db.fetch_one(
        "SELECT status FROM entities WHERE entity_id = :id",
        {'id': entity_id}
    )
    
    if entity['status'] != 'provisional':
        return False
    
    # Check if identifier already exists (would indicate duplicate)
    existing = await db.fetch_one("""
        SELECT entity_id FROM identifiers
        WHERE scheme = :scheme AND value = :value
    """, {'scheme': identifier_scheme, 'value': identifier_value})
    
    if existing:
        # Duplicate! Merge instead
        await merge_entities(
            from_entity_id=entity_id,
            to_entity_id=existing['entity_id'],
            merge_type='duplicate',
            reason=f'Same {identifier_scheme} discovered',
        )
        return False
    
    # Add identifier
    await db.execute("""
        INSERT INTO identifiers (
            identifier_id, entity_id, scheme, value,
            source, created_at
        ) VALUES (
            :id, :entity_id, :scheme, :value,
            'enrichment', NOW()
        )
    """, {
        'id': generate_ulid(),
        'entity_id': entity_id,
        'scheme': identifier_scheme,
        'value': identifier_value,
    })
    
    # Promote to active
    await db.execute("""
        UPDATE entities SET
            status = 'active',
            trust_level = 'medium',
            updated_at = NOW()
        WHERE entity_id = :id
    """, {'id': entity_id})
    
    return True
```

---

## Example: End-to-End Flow

```python
# 1. Extract mention from filing
mention = MentionExtractor().extract_from_section(
    text="... our supplier Advanced Silicon Technologies LLC ...",
    filing_id="0001193125-24-012345",
    section_path="Item 1/Business/Suppliers"
)[0]

# mention.raw_text = "Advanced Silicon Technologies LLC"
# mention.hints = {'likely_private': True}

# 2. Normalize
normalized = normalize_company_name(mention.raw_text)
# normalized = "ADVANCED SILICON TECHNOLOGIES"

name_hash = compute_name_hash(normalized)
# name_hash = "a8b3c4d5e6f71234"

# 3. Find candidates
candidates = await CandidateFinder(db).find_candidates(mention, normalized, name_hash)
# candidates = []  (no matches)

# 4. Resolve
decision = await MentionResolver(db).resolve_mention(mention, filing_id, section_path)
# decision.action = 'create_provisional'
# decision.cluster_id = '01HYX...'
# decision.reason = "Added to cluster, waiting for more mentions"

# 5. Store mention
await store_mention(
    mention=mention,
    filing_id=filing_id,
    section_path=section_path,
    normalized=normalized,
    name_hash=name_hash,
    cluster_id=decision.cluster_id,
    resolution_status='pending',
)

# ... later, after 3 mentions from different filings ...

# 6. Cluster promoted to provisional entity
entity_id = await create_provisional_from_cluster(cluster)
# entity_id = '01HYX...'
# status = 'provisional'

# ... later, someone finds their LEI ...

# 7. Promote to active
await promote_provisional_to_active(
    entity_id=entity_id,
    identifier_scheme='lei',
    identifier_value='5493006ABC123DEF4567',
)
# status = 'active'
```

---

## Next Document

→ [05_STORAGE_TIERS.md](05_STORAGE_TIERS.md) - SQLite → DuckDB → PostgreSQL → ES+Neo4j progression
