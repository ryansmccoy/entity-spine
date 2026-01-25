# EntitySpine Services Reference

> **Version**: 0.4.0  
> **Last Updated**: January 27, 2026

## Overview

EntitySpine provides comprehensive services for entity resolution, relationship management, and data quality:

| Service | Module | Lines | Purpose |
|---------|--------|-------|---------|
| **Graph** | `services/graph_service.py` | 812 | Relationship traversal & network analysis |
| **Timeline** | `services/timeline.py` | 549 | Point-in-time queries & snapshots |
| **Exhibit 21** | `parser/exhibit21.py` | 918 | Corporate hierarchy parsing |
| **Audit** | `services/audit.py` | — | Change tracking & reversion |
| **Conflicts** | `services/conflicts.py` | — | Duplicate detection & resolution |
| **Data Quality** | `services/data_quality.py` | — | Validation & cleansing |
| **Fuzzy** | `services/fuzzy.py` | — | Name matching & normalization |
| **Clustering** | `services/clustering.py` | — | Entity grouping |
| **Resolver** | `services/resolver.py` | — | Multi-identifier resolution |
| **Symbology** | `services/symbology_refresh.py` | — | Identifier refresh |

---

## Graph Service (812 lines)

Relationship traversal and network analysis for the knowledge graph.

### Components

- **GraphService**: Main service class for graph operations
- **RelationshipType**: Types of relationships (SUBSIDIARY, SUPPLIER, CUSTOMER, OFFICER, etc.)
- **PathResult**: Result of path-finding queries
- **NetworkAnalysis**: Graph metrics and centrality analysis

### Key Capabilities

- Find entity relationships (subsidiaries, officers, directors)
- Path finding between entities
- Network analysis (centrality, clustering)
- Relationship queries with filtering

### Usage

```python
from entityspine.services.graph_service import GraphService

# Initialize with a store
graph = GraphService(store)

# Find subsidiaries of a company
subsidiaries = graph.get_subsidiaries("ent_apple")
for sub in subsidiaries:
    print(f"  → {sub.primary_name}")

# Find officers/directors
officers = graph.get_officers("ent_apple")
directors = graph.get_directors("ent_apple")

# Path finding
path = graph.find_path("ent_nvidia", "ent_tsmc")
if path:
    print(" → ".join(e.primary_name for e in path.entities))

# Network analysis
analysis = graph.analyze_network("ent_apple")
print(f"Connections: {analysis.degree_centrality}")
```

---

## Timeline Service (549 lines)

Point-in-time queries and entity history tracking.

### Components

- **TimelineService**: Main service class
- **EntitySnapshot**: Entity state at a specific point in time
- **TimelineDiff**: Changes between two time points

### Key Capabilities

- Get entity state at any historical date
- Track changes over time
- Compare entity between dates
- Reconstruct historical relationships

### Usage

```python
from entityspine.services.timeline import TimelineService
from datetime import date

# Initialize
timeline = TimelineService(store)

# Get entity as of a specific date
snapshot = timeline.get_entity_at("ent_apple", date(2020, 1, 1))
print(f"Name in 2020: {snapshot.primary_name}")
print(f"CIK in 2020: {snapshot.get_identifier('CIK')}")

# Get history of changes
history = timeline.get_entity_history("ent_apple")
for event in history:
    print(f"{event.date}: {event.change_type}")

# Compare between dates
diff = timeline.compare_entity(
    entity_id="ent_apple",
    date_a=date(2020, 1, 1),
    date_b=date(2024, 1, 1),
)
print(f"Changed fields: {diff.changed_fields}")
```

---

## Exhibit 21 Parser (918 lines)

Parses Exhibit 21 (List of Subsidiaries) from SEC 10-K filings to extract corporate hierarchy.

### Key Capabilities

- Parse HTML tables with subsidiaries
- Handle ASCII art / text-based tables
- Extract nested/hierarchical structures
- Parse ownership percentages
- Handle "dba" (doing business as) names
- State/country of incorporation

### Usage

```python
from entityspine.parser.exhibit21 import Exhibit21Parser

parser = Exhibit21Parser()

# Parse HTML content from Exhibit 21
subsidiaries = parser.parse(exhibit_21_html)

for sub in subsidiaries:
    print(f"  → {sub.name}")
    print(f"    Jurisdiction: {sub.jurisdiction}")
    print(f"    Ownership: {sub.ownership_percent}%")
    print(f"    DBA: {sub.dba_names}")
```

### Output Format

```python
@dataclass
class Subsidiary:
    name: str                    # Company name
    jurisdiction: str | None     # State/country of incorporation
    ownership_percent: float     # Ownership percentage (0-100)
    dba_names: list[str]         # "Doing business as" names
    parent_name: str | None      # Parent company if nested
    level: int                   # Hierarchy depth (0 = direct subsidiary)
```

### Example Pipeline

```python
# Full SEC → Knowledge Graph workflow
from entityspine import SqliteStore
from entityspine.parser.exhibit21 import Exhibit21Parser
from entityspine.services.graph_service import GraphService

# 1. Download Exhibit 21 from SEC filing
exhibit_html = download_exhibit(accession, "EX-21")

# 2. Parse subsidiaries
parser = Exhibit21Parser()
subsidiaries = parser.parse(exhibit_html)

# 3. Create entities and relationships
store = SqliteStore("entities.db")
store.initialize()

for sub in subsidiaries:
    # Create subsidiary entity
    entity = store.create_entity(primary_name=sub.name)
    
    # Create SUBSIDIARY relationship
    store.create_relationship(
        source_id=parent_entity_id,
        target_id=entity.entity_id,
        relationship_type="SUBSIDIARY",
        properties={"ownership_percent": sub.ownership_percent}
    )

# 4. Query the graph
graph = GraphService(store)
all_subs = graph.get_subsidiaries(parent_entity_id)
```

---

## Audit Service

Full change tracking with point-in-time reversion support.

### Components

- **ChangeEvent**: Immutable record of a change
- **ChangeType**: CREATE, UPDATE, DELETE, MERGE, REDIRECT, etc.
- **EntityKind**: ENTITY, SECURITY, LISTING, CLAIM, RELATIONSHIP
- **SqliteAuditStore**: SQLite-based audit storage
- **AuditManager**: High-level audit operations

### Usage

```python
from entityspine.services.audit import (
    AuditManager, SqliteAuditStore, ChangeType, EntityKind
)

# Initialize
audit_store = SqliteAuditStore("audit.db")
audit_store.initialize()
manager = AuditManager(audit_store)

# Record a change
event = manager.record(
    entity_kind=EntityKind.ENTITY,
    entity_id="ent_apple",
    change_type=ChangeType.CREATE,
    after={"name": "Apple Inc.", "cik": "320193"},
    user_id="data_pipeline",
)

# Get history
history = manager.get_history(EntityKind.ENTITY, "ent_apple")
for event in history:
    print(f"{event.occurred_at}: {event.change_type.value}")

# Point-in-time state
state = manager.get_state_at(
    EntityKind.ENTITY, 
    "ent_apple", 
    datetime(2024, 1, 1)
)

# Close when done
audit_store.close()
```

---

## Conflicts Service

Duplicate detection and conflict resolution.

### Components

- **DuplicateDetector**: Finds potential duplicate entities
- **ConflictResolver**: Resolves conflicts with strategies
- **DataQualityScorer**: Scores data completeness
- **ResolutionStrategy**: KEEP_FIRST, KEEP_LATEST, KEEP_HIGHEST_CONFIDENCE, MERGE, MANUAL

### Usage

```python
from entityspine.services.conflicts import (
    DuplicateDetector, ConflictResolver, ResolutionStrategy, DataQualityScorer
)

# Detect duplicates
detector = DuplicateDetector(name_threshold=0.85)
duplicates = detector.find_duplicates_for_entity(
    entity=apple_entity,
    entity_claims=apple_claims,
    all_entities=all_entities,
    all_claims=claims_by_entity,
)

for dup in duplicates:
    print(f"Potential duplicate: {dup.entity_id_b}")
    print(f"  Name similarity: {dup.name_similarity:.2f}")
    print(f"  Overall score: {dup.overall_score:.2f}")

# Resolve duplicate claims
resolver = ConflictResolver()
winner, losers = resolver.resolve_duplicate_claims(
    claims=duplicate_claims,
    strategy=ResolutionStrategy.KEEP_HIGHEST_CONFIDENCE,
)

# Score data quality
scorer = DataQualityScorer()
score = scorer.score_entity(entity, claims)
print(f"Quality score: {score.overall_score:.1f}")
print(f"Issues: {score.issues}")
print(f"Recommendations: {score.recommendations}")
```

---

## Data Quality Service

Validation, cleansing, and identifier format checking.

### Components

- **IdentifierValidator**: Validates identifier claims
- **IdentifierPatterns**: Regex patterns for CIK, LEI, CUSIP, ISIN, etc.
- **ValidationResult**: Contains is_valid, issues, errors, warnings
- **ValidationSeverity**: ERROR, WARNING, INFO

### Usage

```python
from entityspine.services.data_quality import (
    IdentifierValidator, IdentifierPatterns, ValidationResult
)

# Direct pattern validation
if IdentifierPatterns.CIK_PATTERN.match("0000320193"):
    print("Valid CIK format")

if IdentifierPatterns.LEI_PATTERN.match("5493001A7V1L0B6QXM78"):
    print("Valid LEI format")

# Full claim validation
validator = IdentifierValidator()
result = validator.validate(claim)

if result.has_errors:
    for issue in result.errors:
        print(f"ERROR: {issue.message}")
else:
    print("Claim is valid")
    for issue in result.warnings:
        print(f"WARNING: {issue.message}")
```

### Supported Identifier Patterns

| Scheme | Format | Example |
|--------|--------|---------|
| CIK | 10 digits, leading zeros OK | `0000320193` |
| LEI | 20 alphanumeric | `5493001A7V1L0B6QXM78` |
| CUSIP | 9 alphanumeric | `037833100` |
| ISIN | 2 letters + 9 chars + 1 digit | `US0378331005` |
| FIGI | 12 chars starting BBG | `BBG000B9XRY4` |
| EIN | 9 digits with optional hyphen | `94-3055941` |
| TICKER | 1-5 uppercase letters | `AAPL` |

---

## Fuzzy Matching Service

Company name normalization and similarity scoring.

### Usage

```python
from entityspine.services.fuzzy import (
    normalize_company_name, compute_name_similarity
)

# Normalize names
normalized = normalize_company_name("  APPLE INC.  ")
# "apple"

# Compare names
score = compute_name_similarity("Apple Inc.", "APPLE INCORPORATED")
# 0.95 (high similarity)
```

---

## Integration Testing

All services are tested in [tests/integration/test_entity_storage_complete.py](../tests/integration/test_entity_storage_complete.py):

```bash
cd entityspine
uv run pytest tests/integration/test_entity_storage_complete.py -v
```

Tests cover:
1. Entity storage with SqliteStore
2. Audit trail tracking
3. Identifier pattern validation
4. Identifier claim validation
5. Name normalization
6. Duplicate detection
7. Conflict resolution
8. Data quality scoring
9. Full workflow integration

---

## Best Practices

1. **Always initialize stores before use**
   ```python
   store = SqliteStore("db.sqlite")
   store.initialize()  # Required!
   ```

2. **Close connections when done**
   ```python
   try:
       # ... use store
   finally:
       store.close()
   ```

3. **Use correct identifier scope**
   - CIK → `entity_id`
   - ISIN → `security_id`
   - TICKER → `listing_id`

4. **Validate before storing**
   ```python
   result = validator.validate(claim)
   if not result.has_errors:
       store.save_claim(claim)
   ```

5. **Audit significant changes**
   ```python
   manager.record(
       entity_kind=EntityKind.ENTITY,
       entity_id=entity.entity_id,
       change_type=ChangeType.UPDATE,
       before=old_state,
       after=new_state,
       user_id="pipeline_name",
   )
   ```
