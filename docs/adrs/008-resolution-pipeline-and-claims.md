# ADR-008: Resolution Pipeline and Claims Architecture

**Status**: Proposed  
**Date**: January 2026  
**Deciders**: Project maintainers  
**Supersedes**: None (complements ADR-003)

---

## Context

EntitySpine provides entity resolution for SEC EDGAR issuers (~14K companies), resolving identifiers like ticker, CIK, CUSIP to canonical entities. The current implementation:

1. ✅ Has a claims-based identifier model (ADR-003)
2. ✅ Separates Entity/Security/Listing (ADR-001)
3. ✅ Uses temporal semantics (ADR-006)
4. ❌ Lacks a **staged resolution pipeline** architecture
5. ❌ Lacks **resolution run artifacts** for reproducibility
6. ❌ Lacks **structured explainability** for audit
7. ❌ Lacks **merge/split event logging** for compliance

### Problem Statement

Modern entity resolution systems (Splink, Dedupe, Zingg, enterprise MDM) follow a staged pipeline pattern that provides:

- **Reproducibility**: Same inputs + parameters = same outputs
- **Explainability**: Every decision can be audited
- **Observability**: Metrics, diffs, quality gates
- **Scalability**: Each stage can be optimized independently

EntitySpine performs resolution ad-hoc without these properties, making it unsuitable for:

- Regulatory audit requirements (SEC/FINRA)
- Production monitoring and alerting
- Debugging resolution issues
- A/B testing resolution strategies

### Requirements

| Requirement | Priority | Notes |
|-------------|----------|-------|
| Stdlib-only core | MUST | No pydantic, numpy in domain layer |
| Staged pipeline | MUST | Normalize → Block → Compare → Cluster → Merge |
| Run artifacts | MUST | Persist inputs, params, outputs |
| Explainability | MUST | Every resolution can answer "why?" |
| Merge/split events | MUST | Structured audit log |
| Data quality gates | SHOULD | Pre/post resolution invariants |
| Diff between runs | SHOULD | What changed from run N to N+1? |
| Plugin architecture | MAY | Advanced matchers as optional extras |

---

## Decision

### 1. Adopt Staged Resolution Pipeline

We will implement a **5-stage resolution pipeline** that processes source records through well-defined stages:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        ENTITYSPINE RESOLUTION PIPELINE                          │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│   ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐ │
│   │  STAGE 1 │───▶│  STAGE 2 │───▶│  STAGE 3 │───▶│  STAGE 4 │───▶│  STAGE 5 │ │
│   │ NORMALIZE│    │  BLOCK   │    │  COMPARE │    │  CLUSTER │    │  PERSIST │ │
│   └──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘ │
│        │               │               │               │               │        │
│        ▼               ▼               ▼               ▼               ▼        │
│   ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐ │
│   │  Clean   │    │  Block   │    │ Candidate│    │  Cluster │    │ Entity   │ │
│   │  Records │    │  Keys    │    │  Pairs   │    │ Decisions│    │ + Claims │ │
│   └──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘ │
│                                                                                 │
│   ◀─────────────────── ResolutionRun artifact ──────────────────────────────▶  │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

#### Stage 1: Normalize

**Input**: Raw `SourceRecord` objects  
**Output**: Cleaned, normalized records with extracted identifiers

**Operations**:
- Standardize company names (remove Inc., Corp., etc. for matching)
- Normalize CIK (10-digit zero-padded)
- Normalize ticker (uppercase, dash→dot)
- Extract identifiers from free text
- Flag data quality issues

**Stdlib implementation**:
```python
@dataclass(frozen=True, slots=True)
class NormalizedRecord:
    source_record_id: str
    normalized_name: str
    extracted_identifiers: tuple[tuple[str, str], ...]  # (scheme, value) pairs
    quality_flags: tuple[str, ...] = ()
```

#### Stage 2: Block

**Input**: Normalized records  
**Output**: Block keys that group potentially matching records

**Operations**:
- Generate blocking keys (first 3 chars of name, CIK prefix, etc.)
- Apply blocking rules to reduce comparison space
- Records with same block key are compared

**Blocking strategies** (stdlib core):
- `cik_exact`: Block on exact CIK
- `name_prefix`: Block on first N chars of normalized name
- `ticker_exact`: Block on exact ticker

**Optional plugins** (extras):
- Phonetic blocking (Soundex, Metaphone)
- Token blocking (sorted tokens)
- LSH blocking (locality-sensitive hashing)

```python
@dataclass(frozen=True, slots=True)
class BlockingConfig:
    strategies: tuple[str, ...] = ("cik_exact", "name_prefix")
    name_prefix_length: int = 3
```

#### Stage 3: Compare

**Input**: Candidate pairs from same block  
**Output**: Comparison scores with evidence

**Operations**:
- Compare identifier values (exact, normalized)
- Compare names (exact, normalized, similarity)
- Aggregate scores with weights

**Comparison functions** (stdlib core):
- Exact match (0 or 1)
- Normalized match
- Levenshtein distance (stdlib implementation)

**Optional plugins** (extras):
- Jaro-Winkler similarity
- TF-IDF cosine similarity
- Learned matchers

```python
@dataclass(frozen=True, slots=True)
class ComparisonResult:
    record_a_id: str
    record_b_id: str
    total_score: float
    component_scores: dict[str, float]
    evidence: tuple[str, ...]  # Contributing claim IDs
```

#### Stage 4: Cluster

**Input**: Comparison scores  
**Output**: Cluster decisions (match, no-match, review)

**Operations**:
- Apply threshold to scores
- Transitive closure for multi-way matches
- Generate merge decisions

**Thresholds**:
```python
@dataclass(frozen=True, slots=True)
class ClusteringConfig:
    match_threshold: float = 0.85      # >= this is a match
    review_threshold: float = 0.65     # Between review and match needs human review
    # < review_threshold is no-match
```

```python
@dataclass(frozen=True, slots=True)
class ClusterDecision:
    cluster_id: str
    member_ids: tuple[str, ...]
    decision: Literal["MATCH", "NO_MATCH", "REVIEW"]
    confidence: float
    canonical_id: str | None = None  # Selected representative
```

#### Stage 5: Persist

**Input**: Cluster decisions  
**Output**: Created/updated entities, claims, merge events

**Operations**:
- Create new entities for unmatched records
- Merge matched records into canonical entity
- Create identifier claims with provenance
- Log merge events
- Update statistics

---

### 2. Claims Model with Provenance

Extend ADR-003 claims model with:

#### Provenance Record

```python
@dataclass(frozen=True, slots=True)
class Provenance:
    """Full audit trail for any data assertion."""
    provenance_id: str
    source_system: str          # "sec", "factset", "manual"
    source_uri: str | None      # URL or file path
    source_version: str | None  # "2026-01-28" for dated files
    retrieved_at: datetime      # When we fetched
    as_of_date: date | None     # Business date
    content_hash: str | None    # SHA-256 for verification
    record_locator: str | None  # Row/path in source
    source_reliability: float = 1.0
```

#### Enhanced IdentifierClaim

```python
# Additions to existing IdentifierClaim:
provenance_id: str | None = None  # Link to Provenance record
explanation_id: str | None = None  # Link to Explanation (if from resolution)
```

---

### 3. Resolution Run Artifacts

Every batch resolution creates a **ResolutionRun** artifact:

```python
@dataclass(frozen=True, slots=True)
class ResolutionRun:
    """Reproducible resolution batch execution."""
    run_id: str = field(default_factory=generate_ulid)
    
    # Inputs (for reproducibility)
    # Note: dict[str, Any] follows existing pattern in ResolutionResult.limits
    # The dict reference is frozen, contents are set once at creation
    input_params: dict[str, Any] = field(default_factory=dict)
    source_record_ids: tuple[str, ...] = ()
    
    # Timing
    started_at: datetime = field(default_factory=utc_now)
    completed_at: datetime | None = None
    
    # Stage metrics (dict with field default_factory)
    stage_metrics: dict[str, dict[str, int]] = field(default_factory=dict)
    # Example: {"normalize": {"processed": 1000, "errors": 5}, ...}
    
    # Output summary
    entities_created: int = 0
    entities_updated: int = 0
    entities_merged: int = 0
    claims_created: int = 0
    claims_superseded: int = 0
    
    # Quality
    avg_confidence: float = 0.0
    ambiguous_count: int = 0
    error_count: int = 0
    
    # Status
    status: Literal["RUNNING", "COMPLETED", "FAILED", "CANCELLED"] = "RUNNING"
    error_message: str | None = None
    
    # Timestamps
    created_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True, slots=True)
class ResolutionRunDiff:
    """Diff between two resolution runs."""
    run_a_id: str
    run_b_id: str
    
    entities_added: tuple[str, ...]      # In B but not A
    entities_removed: tuple[str, ...]    # In A but not B
    entities_modified: tuple[str, ...]   # Different in A vs B
    merges_added: tuple[str, ...]        # New merges in B
    merges_reversed: tuple[str, ...]     # Merges in A undone in B
    
    summary: str  # Human-readable summary
```

---

### 4. Explainability Output

Every resolution decision can produce an **Explanation**:

```python
@dataclass(frozen=True, slots=True)
class Explanation:
    """Structured explanation of resolution decision."""
    explanation_id: str
    
    # What was resolved
    query: str
    query_type: Literal["cik", "ticker", "name", "mixed"]
    resolved_entity_id: str | None
    
    # Score breakdown
    total_score: float
    score_components: dict[str, float]
    # Example: {
    #     "exact_cik_match": 0.50,
    #     "name_similarity": 0.30,
    #     "ticker_confirmed": 0.15,
    #     "recency_bonus": 0.05
    # }
    
    # Evidence trail
    contributing_claims: tuple[str, ...]
    matched_values: dict[str, str]
    normalization_applied: dict[str, str]  # Before → after
    
    # Decision factors
    decisive_factor: str | None  # What tipped the balance
    alternatives_considered: int
    rejected_candidates: tuple[str, ...]
    rejection_reasons: dict[str, str]  # entity_id → reason
    
    # Pipeline context
    blocking_keys_used: tuple[str, ...]
    comparison_pairs_evaluated: int
    
    # Metadata
    resolution_run_id: str | None
    created_at: datetime
```

#### Explanation API

```python
def explain_resolution(
    query: str,
    resolved_entity_id: str | None,
    store: EntityStoreProtocol,
) -> Explanation:
    """Generate explanation for a resolution outcome."""
    ...

def format_explanation_text(explanation: Explanation) -> str:
    """Format explanation as human-readable text."""
    ...

def format_explanation_json(explanation: Explanation) -> dict:
    """Format explanation as JSON-serializable dict."""
    ...
```

#### Example Explanation Output

```
Resolution Explanation for query "AAPL"
=======================================

Resolved to: Apple Inc. (entity_id: 01HQZ...)
Confidence: 0.95

Score Breakdown:
  • exact_ticker_match:  0.40  (AAPL on XNAS listing)
  • cik_confirmed:       0.35  (CIK 0000320193 matches)
  • name_similarity:     0.15  (100% match "Apple Inc.")
  • recency_bonus:       0.05  (listing active as of query date)

Evidence:
  • Ticker claim: AAPL → listing_id 01HRL... (source: SEC, captured: 2026-01-28)
  • CIK claim: 0000320193 → entity_id 01HQZ... (source: SEC, confidence: 1.0)

Decision:
  Decisive factor: exact_ticker_match on active listing
  Alternatives considered: 0
  No rejected candidates (unambiguous match)

Pipeline Context:
  Blocking keys: ["ticker:AAPL", "cik:0000320193"]
  Comparison pairs: 1
  Run ID: 01HRD...
```

---

### 5. Merge/Split Event Model

#### MergeEvent

```python
@dataclass(frozen=True, slots=True)
class MergeEvent:
    """Immutable record of entity merge."""
    event_id: str
    
    # What merged
    source_entity_ids: tuple[str, ...]  # One or more source entities
    target_entity_id: str               # Surviving canonical entity
    
    # Why
    reason: str
    evidence_claim_ids: tuple[str, ...] = ()
    confidence: float = 1.0
    
    # Who/when
    performed_by: str = "system"
    performed_at: datetime = field(default_factory=utc_now)
    resolution_run_id: str | None = None
    
    # Reversibility
    reversible: bool = True
    reversed_at: datetime | None = None
    reversed_by: str | None = None
    reversal_reason: str | None = None
```

#### SplitEvent

```python
@dataclass(frozen=True, slots=True)
class SplitEvent:
    """Immutable record of entity split (spin-off, demerger)."""
    event_id: str
    
    # What split
    source_entity_id: str
    target_entity_ids: tuple[str, ...]
    
    # Reassignments
    claim_reassignments: dict[str, str]  # claim_id → new_entity_id
    security_reassignments: dict[str, str]  # security_id → new_entity_id
    
    # Why
    reason: str
    corporate_action_date: date | None = None
    
    # Who/when
    performed_by: str = "system"
    performed_at: datetime = field(default_factory=utc_now)
    resolution_run_id: str | None = None
```

#### Event Query API

```python
def get_merge_history(
    entity_id: str,
    store: EntityStoreProtocol,
) -> list[MergeEvent]:
    """Get all merges that affected this entity (as source or target)."""
    ...

def get_entity_lineage(
    entity_id: str,
    store: EntityStoreProtocol,
) -> dict:
    """Get full entity history including merges, splits, and redirects."""
    ...
```

---

### 6. Stdlib Core vs Optional Plugins

#### Stdlib Core (Zero Dependencies)

Everything in `entityspine.domain` and `entityspine.core`:

| Component | Stdlib Implementation |
|-----------|----------------------|
| Data classes | `dataclasses` |
| Validation | Custom validators in `validators.py` |
| Timestamps | `datetime`, `date` |
| IDs | ULID (custom implementation) |
| Enums | `enum.Enum` |
| Serialization | `json`, `dataclasses.asdict()` |
| Blocking | Exact match, prefix |
| Comparison | Exact, normalized, Levenshtein |
| Storage | JSON files, SQLite (stdlib `sqlite3`) |

#### Optional Plugins (Extras)

Installable via `pip install entityspine[matching]` or similar:

```python
# entityspine.ext.matching (requires jellyfish)
def jaro_winkler_similarity(a: str, b: str) -> float: ...
def soundex_blocking(name: str) -> str: ...

# entityspine.ext.ml (requires scikit-learn)
class LearnedMatcher:
    def train(self, labeled_pairs: list[LabeledPair]) -> None: ...
    def predict(self, pair: tuple[str, str]) -> float: ...

# entityspine.ext.vector (requires sentence-transformers)
class SemanticMatcher:
    def embed(self, text: str) -> list[float]: ...
    def similarity(self, a: str, b: str) -> float: ...
```

#### Plugin Interface

```python
# Core defines protocols that plugins implement

class BlockingStrategy(Protocol):
    """Protocol for blocking key generators."""
    def generate_keys(self, record: NormalizedRecord) -> tuple[str, ...]: ...

class ComparisonFunction(Protocol):
    """Protocol for comparison functions."""
    def compare(self, a: str, b: str) -> float: ...
    
class MatcherPlugin(Protocol):
    """Protocol for ML-based matchers."""
    def score(self, record_a: NormalizedRecord, record_b: NormalizedRecord) -> float: ...
```

#### Plugin Registration

```python
from entityspine.pipeline import ResolutionPipeline

pipeline = ResolutionPipeline()

# Register stdlib strategies (built-in)
pipeline.register_blocking_strategy("cik_exact", CikExactBlocking())
pipeline.register_blocking_strategy("name_prefix", NamePrefixBlocking(length=3))

# Register plugin strategies (optional)
try:
    from entityspine.ext.matching import SoundexBlocking
    pipeline.register_blocking_strategy("soundex", SoundexBlocking())
except ImportError:
    pass  # Plugin not installed
```

---

### 7. Data Quality Gates

```python
@dataclass(frozen=True, slots=True)
class DataQualityRule:
    """Definition of a data quality check."""
    rule_id: str
    name: str
    description: str
    severity: Literal["ERROR", "WARNING", "INFO"] = "ERROR"
    check_expression: str  # SQL or Python expression
    run_stage: Literal["pre_resolution", "post_resolution", "always"] = "always"


@dataclass(frozen=True, slots=True)
class DataQualityResult:
    """Result of running a quality check."""
    rule_id: str
    passed: bool
    violation_count: int = 0
    sample_violations: tuple[str, ...] = ()
    checked_at: datetime = field(default_factory=utc_now)
    resolution_run_id: str | None = None
```

#### Built-in Rules

| Rule ID | Name | Severity | Stage |
|---------|------|----------|-------|
| `cik_uniqueness` | CIK maps to one entity at a time | ERROR | post |
| `claim_validity_no_overlap` | Same claim has no overlapping validity | WARNING | post |
| `entity_has_identifier` | Every entity has ≥1 active claim | WARNING | post |
| `merge_has_evidence` | System merges have evidence claims | ERROR | post |
| `no_circular_redirects` | Redirect chains don't loop | ERROR | post |

---

## Consequences

### Positive

1. **Reproducibility**: ResolutionRun artifacts capture everything needed to reproduce results
2. **Auditability**: Explanation model answers "why?" for any resolution
3. **Observability**: Stage metrics enable monitoring and alerting
4. **Extensibility**: Plugin architecture allows advanced matching without breaking stdlib core
5. **Compliance**: Event logs satisfy regulatory audit requirements
6. **Debugging**: Run diffs identify exactly what changed

### Negative

1. **Complexity**: More types and stages to understand
2. **Storage overhead**: Explanations and events consume space
3. **Performance**: Generating full explanations adds latency
4. **Migration effort**: Existing code needs updates

### Mitigations

- Explanations are optional (generated on demand, not always)
- Event logging can be configured per-deployment
- Stage metrics are lightweight aggregates
- Migration can be incremental (new types are additions, not breaking changes)

---

## Alternatives Considered

### Alternative 1: Use Existing ER Library (Splink, Dedupe)

**Rejected because**:
- Adds heavy dependencies (pandas, numpy)
- Designed for millions of records, overkill for ~14K
- Doesn't integrate with our claims model
- Loses stdlib-only guarantee

### Alternative 2: No Pipeline, Keep Ad-Hoc Resolution

**Rejected because**:
- Can't reproduce results
- No audit trail
- No observability
- Fails regulatory requirements

### Alternative 3: Full Graph Database (Neo4j, DGraph)

**Rejected because**:
- Massive dependency
- Operational overhead
- Overkill for ~14K entities
- Loses tiered storage flexibility

### Alternative 4: Event Sourcing Everything

**Rejected because**:
- Excessive complexity for this scale
- Storage overhead
- Query complexity
- We only need events for merges/splits, not all changes

---

## Implementation Plan

### Phase 1: Foundation (Sprint 1)

1. Add `Provenance` dataclass
2. Add `provenance_id` FK to `IdentifierClaim` (optional, backward compatible)
3. Add `MergeEvent` dataclass
4. Add `Explanation` dataclass (minimal)
5. Add `Entity.merge_into_with_event()` method (keeps `merge_into()` unchanged for backward compatibility)
6. Add storage protocols for new types

### Phase 2: Pipeline (Sprint 2)

1. Add `SourceRecord` dataclass
2. Add `ResolutionRun` dataclass
3. Implement Stage 1: Normalize
4. Implement Stage 2: Block (stdlib strategies)
5. Implement Stage 3: Compare (stdlib functions)
6. Implement Stage 4: Cluster
7. Implement Stage 5: Persist

### Phase 3: Quality & Polish (Sprint 3)

1. Add `DataQualityRule/Result` types
2. Implement built-in rules
3. Add `SplitEvent` dataclass
4. Add `ResolutionRunDiff` type
5. Implement run diff logic
6. Plugin interface and registration
7. Documentation and examples

---

## References

- ADR-001: Stdlib-only Domain Layer
- ADR-003: Identifier Claims Pattern
- ADR-006: Time Semantics
- [Splink: Probabilistic record linkage at scale](https://github.com/moj-analytical-services/splink)
- [Dedupe: A python library for fuzzy matching](https://github.com/dedupeio/dedupe)
- [Zingg: ML based entity resolution](https://github.com/zinggAI/zingg)

---

## Appendix: Example Workflow

```python
from entityspine.pipeline import ResolutionPipeline
from entityspine.domain import SourceRecord, Provenance
from entityspine.stores import JsonEntityStore

# 1. Create store and pipeline
store = JsonEntityStore(Path("./data"))
store.initialize()

pipeline = ResolutionPipeline(
    store=store,
    blocking_config=BlockingConfig(strategies=("cik_exact", "name_prefix")),
    clustering_config=ClusteringConfig(match_threshold=0.85),
)

# 2. Create provenance for this batch
provenance = Provenance(
    provenance_id=generate_ulid(),
    source_system="sec",
    source_uri="https://www.sec.gov/files/company_tickers.json",
    retrieved_at=datetime.now(timezone.utc),
    as_of_date=date.today(),
)
store.save_provenance(provenance)

# 3. Create source records
source_records = [
    SourceRecord(
        record_id=generate_ulid(),
        raw_data={"cik": 320193, "title": "Apple Inc.", "ticker": "AAPL"},
        provenance=provenance,
    )
    for row in sec_data
]

# 4. Run resolution pipeline
run = pipeline.run(source_records)

# 5. Inspect results
print(f"Created: {run.entities_created}, Merged: {run.entities_merged}")
print(f"Avg confidence: {run.avg_confidence:.2f}")

# 6. Get explanation for specific resolution
entity = store.get_entities_by_cik("0000320193")[0]
explanation = pipeline.explain(query="AAPL", resolved_entity_id=entity.entity_id)
print(format_explanation_text(explanation))

# 7. Compare to previous run
if previous_run_id:
    diff = pipeline.diff_runs(previous_run_id, run.run_id)
    print(f"Entities added: {len(diff.entities_added)}")
    print(f"New merges: {len(diff.merges_added)}")
```

---

**Decision**: Adopt staged resolution pipeline with claims provenance, run artifacts, and explainability while maintaining stdlib-only core and plugin extensibility.
