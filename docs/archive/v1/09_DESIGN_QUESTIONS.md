# Entity Master - Design Questions & Decisions

Questions to clarify before implementation.

---

## 1. Deployment Architecture

### Question: Library vs Service vs Both?

**Option A: Library Only**
```python
# Embedded in each application
from entity_master import EntityMaster
em = EntityMaster(storage_url="postgresql://...")
```

**Option B: Standalone Service**
```
┌─────────────┐     ┌─────────────────┐     ┌──────────────┐
│ py-sec-edgar├────▶│ Entity Master   ├────▶│ PostgreSQL   │
└─────────────┘     │ REST API        │     └──────────────┘
                    │ :8080           │
┌─────────────┐     │                 │
│ Other App   ├────▶│                 │
└─────────────┘     └─────────────────┘
```

**Option C: Library with Optional Service**
```python
# Library mode (direct DB access)
em = EntityMaster(storage_url="postgresql://...")

# Service mode (HTTP client)
em = EntityMaster(service_url="http://entity-master:8080")
```

**Considerations:**
- Library: Simpler, no network latency, but each app needs DB credentials
- Service: Centralized, better for multiple consumers, but adds network hop
- Both: Flexible, but more code to maintain

**My Recommendation:** Option C - Library with optional service mode
- Default to library for simplicity
- Service mode for multi-app deployments
- Same API regardless of mode

---

## 2. Multi-Tenancy

### Question: Single tenant or multi-tenant?

**Single Tenant:**
- One Entity Master instance per deployment
- Simpler, no tenant isolation concerns

**Multi-Tenant:**
- Shared service with tenant isolation
- `em = EntityMaster(tenant_id="py_sec_edgar")`
- Data isolated by tenant_id

**Considerations:**
- py-sec-edgar: Single tenant sufficient
- Enterprise deployment: May need multi-tenant
- Data isolation: Do different apps see the same entities?

**My Recommendation:** 
- Start single-tenant for py-sec-edgar
- Design schema to support multi-tenant later (optional tenant_id column)

---

## 3. Source System Namespacing

### Question: How should we namespace data from different sources?

When py-sec-edgar adds a relationship vs another system:

**Option A: Source System Tag**
```python
await em.relationships.add(
    source_entity_id="...",
    target_entity_id="...",
    relationship_type="SUPPLIES_TO",
    evidence=RelationshipEvidence(
        source_system="py_sec_edgar",  # Tagged
        source_id="000032...",
    ),
)
```

**Option B: Separate Relationship Records**
- Each source creates its own relationship record
- Aggregated view merges them

**Option C: Single Relationship with Multiple Evidence**
- One relationship per source-target-type
- Multiple evidence records from different sources

**My Recommendation:** Option C
- Relationship is the "fact" (Apple supplies to Walmart)
- Evidence is the "proof" (multiple filings, news articles)
- More evidence from different sources = higher confidence

---

## 4. Conflict Resolution

### Question: When sources disagree, what happens?

**Scenario:** 
- py-sec-edgar says: "A supplies to B" (from 10-K)
- News feed says: "A competes with B" (from article)

**Option A: Store Both**
- Both relationships exist
- Let consumer decide which to trust

**Option B: Source Priority**
```yaml
source_priority:
  - py_sec_edgar  # Authoritative (SEC filings)
  - manual        # Human-curated
  - news          # Less authoritative
```

**Option C: Confidence-Based**
- Higher confidence wins
- Multiple confirmations increase confidence

**Option D: Temporal (Latest Wins)**
- Most recent source overwrites

**My Recommendation:** Option A + C hybrid
- Store all relationships (they may both be true - A supplies AND competes)
- Use confidence to rank within same relationship type
- Let consumer filter by confidence threshold

---

## 5. Historical Data

### Question: How much history to keep?

**For Relationships:**
- Option A: Only current state (active relationships)
- Option B: First/last seen timestamps
- Option C: Full history (every change)

**For Mentions:**
- Option A: Aggregate counts only
- Option B: Keep all mentions (can be large)
- Option C: Keep recent + aggregate old

**My Recommendation:**
- Relationships: Option B (first/last seen + evidence history)
- Mentions: Option C (configurable retention, default 1 year detail + aggregates)
- Changes: Option B (retention policy, default 90 days)

---

## 6. Resolution Behavior

### Question: Auto-create entities or strict mode?

When py-sec-edgar extracts "WidgetCo" but it's not in Entity Master:

**Option A: Strict (Fail)**
```python
entity = await em.resolve("WidgetCo")
# Returns None - caller must handle
```

**Option B: Auto-Create**
```python
entity = await em.resolve("WidgetCo", auto_create=True)
# Creates new entity with status="unverified"
```

**Option C: Configurable**
```python
em = EntityMaster(auto_create_entities=False)  # Global setting
entity = await em.resolve("WidgetCo", auto_create=True)  # Per-call override
```

**My Recommendation:** Option C
- Default to strict (don't pollute with bad data)
- Allow auto-create for specific use cases
- Unverified entities get enriched/merged later

---

## 7. Batch Processing

### Question: Expected throughput requirements?

**Scenarios:**
1. **Interactive:** Single lookups, <100ms latency needed
2. **Batch filing processing:** 10K filings/day, each with ~50 entities
3. **Bulk import:** GLEIF 3M entities, one-time load
4. **Streaming:** Real-time news with entity extraction

**Questions:**
- What's the expected filing processing rate?
- How many relationships per filing on average?
- Do we need real-time indexing or can it be eventual?

**Performance Targets (Proposed):**
- Single resolve: <50ms (cached), <200ms (uncached)
- Batch resolve: 1000 entities in <1s
- Relationship add: <10ms
- Mention add: <5ms (can be async/batched)

---

## 8. Caching Strategy

### Question: What caching layers?

**Layer 1: Application Cache**
```python
@lru_cache(maxsize=10000)
def cached_resolve(identifier: str):
    return em.resolve(identifier)
```

**Layer 2: Service Cache (Redis)**
```
py-sec-edgar → Entity Master API → Redis → PostgreSQL
```

**Layer 3: Database Materialized Views**
- Pre-computed identifier index
- Denormalized entity views

**Questions:**
- How often do entities change?
- Is eventual consistency acceptable?
- Cache invalidation strategy?

**My Recommendation:**
- Tier 1-2: Application-level LRU cache only
- Tier 3+: Optional Redis for shared cache
- Change events invalidate caches

---

## 9. API Versioning

### Question: How to handle API evolution?

**Option A: URL Versioning**
```
/v1/resolve/AAPL
/v2/resolve/AAPL
```

**Option B: Header Versioning**
```
X-API-Version: 2024-01-01
```

**Option C: No Versioning (Additive Only)**
- Only add new fields, never remove
- Deprecation warnings in response

**My Recommendation:** Option C for library, Option A for REST API
- Library: Use semantic versioning for breaking changes
- REST: URL versioning for major changes

---

## 10. Security & Access Control

### Question: Authentication/authorization model?

**For Library Mode:**
- Inherits database credentials
- No additional auth needed

**For Service Mode:**
- API key per consumer?
- OAuth2?
- Role-based access (read-only vs write)?

**Questions:**
- Who should be able to write relationships vs only read?
- Should some entities/relationships be private?
- Audit logging requirements?

---

## 11. Error Handling

### Question: How to handle resolution failures?

**Scenarios:**
1. Entity not found
2. Ambiguous match (multiple candidates)
3. Low confidence match
4. External enrichment timeout

**Proposed Exceptions:**
```python
class EntityNotFound(Exception):
    """Entity could not be resolved."""
    pass

class AmbiguousMatch(Exception):
    """Multiple entities match with similar confidence."""
    candidates: List[ResolvedEntity]

class LowConfidenceMatch(Exception):
    """Best match below minimum confidence threshold."""
    best_match: ResolvedEntity
    confidence: float

class EnrichmentError(Exception):
    """External enrichment source failed."""
    source: str
    original_error: Exception
```

---

## 12. Relationship Directionality

### Question: How to model bidirectional relationships?

**Scenario:** "Apple competes with Samsung"

**Option A: Explicit Direction**
```python
# Two relationships
await em.relationships.add("AAPL", "Samsung", "COMPETES_WITH")
await em.relationships.add("Samsung", "AAPL", "COMPETES_WITH")
```

**Option B: Bidirectional Flag**
```python
await em.relationships.add(
    "AAPL", "Samsung", "COMPETES_WITH",
    bidirectional=True,  # Stored once, queried both ways
)
```

**Option C: Symmetric Relationship Types**
- COMPETES_WITH is inherently bidirectional
- SUPPLIES_TO is directional

**My Recommendation:** Option C
- Define which relationship types are symmetric
- Query engine handles both directions automatically

---

## Decision Matrix

| # | Question | Options | Recommendation | Priority |
|---|----------|---------|----------------|----------|
| 1 | Library vs Service | A/B/C | C (Both) | HIGH |
| 2 | Multi-tenancy | Single/Multi | Single (extensible) | MEDIUM |
| 3 | Source Namespacing | A/B/C | C (Multi-evidence) | HIGH |
| 4 | Conflict Resolution | A/B/C/D | A+C (Store all, confidence) | HIGH |
| 5 | History Retention | A/B/C | B (First/last seen) | MEDIUM |
| 6 | Auto-create | A/B/C | C (Configurable) | HIGH |
| 7 | Batch Throughput | - | Define targets | HIGH |
| 8 | Caching | Layers | Tier-dependent | MEDIUM |
| 9 | API Versioning | A/B/C | C (library), A (REST) | LOW |
| 10 | Security | - | Define requirements | MEDIUM |
| 11 | Error Handling | - | Define exceptions | HIGH |
| 12 | Bidirectionality | A/B/C | C (Symmetric types) | HIGH |

---

## Questions for You

1. **Primary use case:** Is py-sec-edgar the main consumer, or do you envision other apps using this immediately?

2. **Deployment environment:** Local development only? Docker? Kubernetes? Cloud-managed services?

3. **Scale expectations:** Roughly how many filings/day will be processed? How many concurrent users?

4. **Data ownership:** Should Entity Master own the "canonical" entity data, or just be a crosswalk/cache of authoritative sources (SEC, GLEIF)?

5. **Real-time requirements:** Do relationships need to be queryable immediately, or is a few minutes delay acceptable?

6. **Manual curation:** Will there be a UI for humans to verify/correct entity matches and relationships?

7. **Export requirements:** Do consumers need to export entity/relationship data for offline analysis?

8. **Compliance:** Any data retention or audit requirements?

9. **Budget for external APIs:** OpenFIGI, GLEIF (free), LLM enrichment (paid)?

10. **Timeline:** MVP timeline? Which tier to implement first?
