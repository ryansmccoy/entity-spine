# Entity Master Service: Integration Requirements from py-sec-edgar

## Context

This document provides requirements and integration specifications for the **Entity Master** service based on the unified data model designed for **py-sec-edgar**. The Entity Master will be a **standalone service/package** that py-sec-edgar and other consumers will use for entity resolution, relationship management, and identity crosswalks.

---

## Your Current Entity Master Design (Summary)

Based on review of your documentation, you have designed:

| Document | Content |
|----------|---------|
| `00_OVERVIEW.md` | Service purpose, separation rationale, core capabilities |
| `01_TIERED_ARCHITECTURE.md` | 5-tier deployment model (Basic → Mind-blowing) |
| `03_FEEDSPINE_INTEGRATION.md` | Data ingestion via FeedSpine (SEC, GLEIF, OpenFIGI) |
| `04_API_DESIGN.md` | Python SDK and REST/GraphQL API design |

**Key design decisions already made:**
- Entity Master is a **standalone service** separate from py-sec-edgar
- **5-tier architecture** from SQLite → Neo4j + LLM
- **FeedSpine** handles data ingestion pipeline
- Python SDK is the **primary interface**
- Identifier schemes: CIK, LEI, FIGI, ISIN, CUSIP, TICKER, PERMID, DUNS

---

## py-sec-edgar's Requirements for Entity Master

Based on the unified data model designed in py-sec-edgar, here are the specific requirements:

### 1. Core Entity Resolution

py-sec-edgar needs to resolve entities extracted from SEC filings:

```python
# py-sec-edgar extracts these from filings:
# - Company names (customers, suppliers, competitors)
# - Person names (executives, directors)
# - Product names
# - Locations

# Entity Master must resolve these to canonical entities
entity = em.resolve("Walmart Inc.")  # Fuzzy match → canonical entity
entity = em.resolve("Tim Cook")       # Person resolution
```

**Requirements:**
- [ ] Fuzzy name matching with configurable threshold
- [ ] Support for entity types: `COMPANY`, `PERSON`, `PRODUCT`, `LOCATION`, `SECURITY`
- [ ] Confidence score on resolutions
- [ ] Multiple alias support per entity

### 2. Relationship Storage

py-sec-edgar extracts relationships from filings that should be stored in Entity Master:

```python
# Relationships extracted from SEC filings:
relationships = [
    ("AAPL", "SUPPLIES_TO", "Walmart", {"revenue_pct": 15}),
    ("AAPL", "BUYS_FROM", "TSMC", {"is_sole_source": True}),
    ("AAPL", "COMPETES_WITH", "Samsung", {"segment": "mobile"}),
    ("AAPL", "SUBSIDIARY_OF", None, {"ownership_pct": 100}),  # Ex-21
    ("Tim Cook", "EXECUTIVE_OF", "AAPL", {"title": "CEO"}),
]

# Entity Master should store these
await em.relationships.add(
    source="AAPL",
    relationship_type="SUPPLIES_TO",
    target="Walmart",
    evidence={"filing_id": "...", "section": "Item 1", "text": "..."},
    metrics={"revenue_pct": 15.0},
)
```

**Relationship Types Required:**

| Type | Subtype Examples | Extracted From | Metrics |
|------|------------------|----------------|---------|
| `SUPPLIES_TO` | major_customer, distributor | Item 1, Item 7 | revenue_pct |
| `BUYS_FROM` | sole_supplier, key_vendor | Item 1, Item 1A | is_sole_source |
| `COMPETES_WITH` | direct, indirect | Item 1 | segment |
| `SUBSIDIARY_OF` | wholly_owned, majority | Exhibit 21 | ownership_pct |
| `PARTNER_WITH` | joint_venture, alliance | 8-K, Item 1 | deal_value |
| `EXECUTIVE_OF` | ceo, cfo, director | 8-K 5.02, DEF 14A | title, start_date |
| `ACQUIRED` | completed, pending | 8-K 2.01 | price, date |
| `INVESTED_IN` | strategic, portfolio | 13F | shares, value |

### 3. Entity Mention Tracking

py-sec-edgar tracks where entities are mentioned in filings:

```python
# When extracting sections, we find entity mentions
mention = EntityMention(
    entity_id=resolved_entity.id,
    filing_id="...",
    section_id="...",
    mention_text="Walmart Inc.",
    context="...accounted for 15% of revenue...",
    char_start=1234,
    char_end=1246,
    confidence=0.95,
)

# Entity Master should track this
await em.mentions.add(mention)

# And allow querying
mentions = await em.mentions.get("AAPL", source="sec_filings", limit=100)
cross_mentions = await em.mentions.get("AAPL", in_entity="TSMC")  # Apple mentioned in TSMC's filings
```

### 4. Event Entity Links

SIGDEV events reference entities. Entity Master should support linking events to entities:

```python
# SIGDEV event extracted from 8-K
event = {
    "event_type": "MA_ACQUISITION",
    "issuer_entity": "AAPL",     # The filer
    "target_entity": "WidgetCo", # Acquired company (needs resolution)
    "payload": {"purchase_price": 5000000000},
}

# Resolution flow:
issuer = await em.resolve("AAPL")
target = await em.resolve("WidgetCo", min_confidence=0.7)

# Store the event-entity link
await em.events.link(
    event_id="...",
    entity_id=target.id,
    role="target",  # subject, target, acquirer, customer, supplier
)
```

**Entity Roles in Events:**

| Event Type | Entity Roles |
|------------|--------------|
| `MGMT_APPOINTMENT` | subject (company), person (executive) |
| `MA_ACQUISITION` | acquirer (filer), target (acquired company) |
| `CUSTOMER_CONCENTRATION` | subject (filer), customer (major customer) |
| `SUPPLIER_CONCENTRATION` | subject (filer), supplier (key vendor) |
| `CYBER_INCIDENT` | subject (affected company) |
| `LEGAL_PROCEEDING` | subject, counterparty |

### 5. Change Detection

py-sec-edgar needs to know when entity data changes:

```python
# What changed since last sync?
changes = await em.changes_since("2024-01-01")

# Types of changes:
# - new: New entity added
# - updated: Entity attributes changed
# - merged: Two entities merged
# - deactivated: Entity delisted/dissolved
# - relationship_added: New relationship
# - relationship_removed: Relationship ended

for change in changes:
    if change.type == "new" and change.entity_type == "company":
        # New company to track
        await py_sec_edgar.add_to_watchlist(change.entity_id)
```

---

## Integration Interface

### py-sec-edgar → Entity Master

py-sec-edgar will be a **consumer** of Entity Master:

```python
# py_sec_edgar/core/entity_service.py

from entity_master import EntityMaster, ResolvedEntity

class EntityService:
    """Wrapper around Entity Master for py-sec-edgar."""
    
    def __init__(self, entity_master: EntityMaster):
        self.em = entity_master
    
    async def resolve_extracted_entity(
        self,
        name: str,
        entity_type: str,
        filing_context: dict,
    ) -> ResolvedEntity | None:
        """Resolve an entity extracted from a filing.
        
        Uses filing context to improve resolution accuracy.
        """
        # First try exact match
        entity = await self.em.resolve(name, min_confidence=0.9)
        
        if not entity:
            # Try fuzzy match with context hints
            entity = await self.em.search(
                name,
                entity_type=entity_type,
                hints={
                    "sic_code": filing_context.get("filer_sic"),
                    "mentioned_with": filing_context.get("co_mentioned_entities"),
                },
                limit=1,
            )
        
        return entity[0] if entity else None
    
    async def store_relationship(
        self,
        source: str,
        target: str,
        rel_type: str,
        evidence: dict,
        metrics: dict = None,
    ):
        """Store a relationship extracted from a filing."""
        # Resolve both entities
        source_entity = await self.em.resolve(source)
        target_entity = await self.em.resolve(target)
        
        if not source_entity or not target_entity:
            raise EntityResolutionError(f"Could not resolve: {source} or {target}")
        
        await self.em.relationships.add(
            source_entity_id=source_entity.id,
            target_entity_id=target_entity.id,
            relationship_type=rel_type,
            evidence=evidence,
            metrics=metrics or {},
        )
```

### Entity Master → py-sec-edgar

Entity Master should emit events/webhooks that py-sec-edgar can consume:

```python
# Entity Master webhook payload
{
    "event_type": "entity.updated",
    "entity_id": "...",
    "changes": {
        "ticker": {"old": "FB", "new": "META"},
        "primary_name": {"old": "Facebook, Inc.", "new": "Meta Platforms, Inc."}
    },
    "timestamp": "2024-01-01T00:00:00Z"
}

# py-sec-edgar webhook handler
@app.post("/webhooks/entity-master")
async def handle_entity_change(payload: dict):
    if payload["event_type"] == "entity.updated":
        # Update local caches
        await refresh_entity_cache(payload["entity_id"])
        # Re-link any filings that reference this entity
        await reprocess_entity_mentions(payload["entity_id"])
```

---

## Data Model Alignment

### Entity Master Tables (Your Design)

```sql
-- These exist in your design
CREATE TABLE entities (...);
CREATE TABLE identifiers (...);
CREATE TABLE aliases (...);
CREATE TABLE enrichments (...);
```

### Additional Tables Needed

Based on py-sec-edgar's unified data model, Entity Master should also have:

```sql
-- Relationships with evidence tracking
CREATE TABLE relationships (
    relationship_id UUID PRIMARY KEY,
    source_entity_id UUID NOT NULL REFERENCES entities(entity_id),
    target_entity_id UUID NOT NULL REFERENCES entities(entity_id),
    relationship_type VARCHAR(50) NOT NULL,
    relationship_subtype VARCHAR(50),
    
    -- Evidence from source system (e.g., py-sec-edgar filing)
    evidence_source VARCHAR(50),         -- 'sec_filing', 'news', 'manual'
    evidence_source_id VARCHAR(100),     -- filing_id, article_id, etc.
    evidence_text TEXT,
    
    -- Metrics (flexible JSONB)
    metrics JSONB DEFAULT '{}',
    
    -- Lifecycle
    confidence DECIMAL(3,2),
    first_seen DATE,
    last_seen DATE,
    status VARCHAR(20) DEFAULT 'ACTIVE',
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Entity mentions across sources
CREATE TABLE entity_mentions (
    mention_id UUID PRIMARY KEY,
    entity_id UUID NOT NULL REFERENCES entities(entity_id),
    
    -- Source tracking
    source_system VARCHAR(50) NOT NULL,  -- 'py_sec_edgar', 'news_crawler', etc.
    source_id VARCHAR(100),              -- filing_id, article_id
    source_subsection VARCHAR(100),      -- section_id
    
    -- Mention details
    mention_text VARCHAR(500) NOT NULL,
    context TEXT,
    char_start INT,
    char_end INT,
    confidence DECIMAL(3,2),
    
    mentioned_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Event-entity links (for SIGDEV integration)
CREATE TABLE event_entity_links (
    link_id UUID PRIMARY KEY,
    
    -- Event reference (stored in source system)
    source_system VARCHAR(50) NOT NULL,  -- 'py_sec_edgar_sigdev'
    event_id VARCHAR(100) NOT NULL,
    
    -- Entity
    entity_id UUID NOT NULL REFERENCES entities(entity_id),
    role VARCHAR(50) NOT NULL,  -- subject, target, acquirer, customer
    is_primary BOOLEAN DEFAULT false,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Change log for webhooks/sync
CREATE TABLE entity_changes (
    change_id UUID PRIMARY KEY,
    entity_id UUID REFERENCES entities(entity_id),
    change_type VARCHAR(50) NOT NULL,  -- new, updated, merged, deactivated
    changed_fields JSONB,
    old_values JSONB,
    new_values JSONB,
    changed_by VARCHAR(100),
    changed_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## Neo4j Graph Model Extension

For Tier 4+, the graph should support py-sec-edgar's relationship queries:

```cypher
// Additional relationship types for py-sec-edgar
(:Company)-[:SUPPLIES_TO {
    revenue_pct: 15.0,
    evidence_filing: "0000320193-24-000123",
    first_seen: date("2020-01-01"),
    status: "ACTIVE"
}]->(:Company)

(:Company)-[:BUYS_FROM {
    is_sole_source: true,
    component: "A15 chips"
}]->(:Company)

(:Company)-[:COMPETES_WITH {
    segment: "smartphones",
    bidirectional: true
}]->(:Company)

(:Person)-[:EXECUTIVE_OF {
    title: "CEO",
    start_date: date("2011-08-24"),
    compensation: 99000000
}]->(:Company)

// Event linkage
(:Event {
    event_id: "...",
    event_type: "MA_ACQUISITION",
    significance: 0.95
})-[:INVOLVES {role: "target"}]->(:Company)
```

---

## API Extensions Needed

### Relationship API

```python
class RelationshipsAPI:
    """Manage entity relationships."""
    
    async def add(
        self,
        source_entity_id: str,
        target_entity_id: str,
        relationship_type: str,
        subtype: str = None,
        evidence: dict = None,
        metrics: dict = None,
        confidence: float = 1.0,
    ) -> str:
        """Add a relationship. Returns relationship_id."""
        ...
    
    async def get(
        self,
        entity_id: str,
        relationship_type: str = None,
        direction: str = "both",
    ) -> list[dict]:
        """Get relationships for an entity."""
        ...
    
    async def get_suppliers(self, entity_id: str) -> list[ResolvedEntity]:
        """Convenience: Get all suppliers."""
        ...
    
    async def get_customers(self, entity_id: str) -> list[ResolvedEntity]:
        """Convenience: Get all customers."""
        ...
    
    async def get_competitors(self, entity_id: str) -> list[ResolvedEntity]:
        """Convenience: Get all competitors."""
        ...
    
    async def get_supply_chain(
        self,
        entity_id: str,
        depth: int = 3,
        direction: str = "upstream",
    ) -> dict:
        """Get supply chain graph."""
        ...
```

### Mentions API

```python
class MentionsAPI:
    """Track entity mentions across sources."""
    
    async def add(
        self,
        entity_id: str,
        source_system: str,
        source_id: str,
        mention_text: str,
        context: str = None,
        confidence: float = 1.0,
    ) -> str:
        """Record an entity mention."""
        ...
    
    async def get(
        self,
        entity_id: str,
        source_system: str = None,
        since: datetime = None,
        limit: int = 100,
    ) -> list[dict]:
        """Get mentions of an entity."""
        ...
    
    async def cross_mentions(
        self,
        entity_id: str,
        in_entity: str,
        relationship_type: str = None,
    ) -> list[dict]:
        """Find where entity A is mentioned in entity B's documents."""
        ...
```

### Events API

```python
class EventsAPI:
    """Link events to entities."""
    
    async def link(
        self,
        source_system: str,
        event_id: str,
        entity_id: str,
        role: str,
        is_primary: bool = False,
    ) -> str:
        """Link an event to an entity."""
        ...
    
    async def get_entity_events(
        self,
        entity_id: str,
        event_types: list[str] = None,
        since: datetime = None,
    ) -> list[dict]:
        """Get events involving an entity."""
        ...
```

---

## Tier Mapping for py-sec-edgar Features

| py-sec-edgar Feature | Required Entity Master Tier |
|---------------------|----------------------------|
| Basic ticker/CIK resolution | Tier 1 (Basic) |
| Entity extraction from filings | Tier 2 (Intermediate) |
| Customer/supplier tracking | Tier 3 (Advanced) |
| Supply chain graph queries | Tier 4 (Full) |
| AI-powered entity extraction | Tier 5 (Mind-blowing) |

---

## Migration Path

### Phase 1: Extract Existing Code
Move existing entity resolution code from py-sec-edgar to Entity Master:
- `py_sec_edgar/core/identity/registry.py`
- `py_sec_edgar/core/identity/matching.py`
- `py_sec_edgar/core/identity/store.py`

### Phase 2: Add Relationship Support
Implement relationship storage and querying.

### Phase 3: Add Mention Tracking
Implement mention recording and cross-reference queries.

### Phase 4: Add Event Linking
Implement event-entity linking for SIGDEV integration.

### Phase 5: Graph Database
Add Neo4j for complex relationship queries (Tier 4).

---

## Questions for Entity Master Team

1. **Namespace**: Should relationships extracted by py-sec-edgar be stored with a `source_system` tag to distinguish from other sources?

2. **Conflict Resolution**: If py-sec-edgar says "A supplies to B" and another source says "A competes with B", how should Entity Master handle this?

3. **Historical Tracking**: Should relationships have full history (every mention) or just first/last seen?

4. **Confidence Aggregation**: If multiple filings confirm a relationship, should confidence increase?

5. **Webhook Scope**: Should py-sec-edgar receive webhooks for all entity changes, or only entities it has interacted with?

6. **Batch Operations**: What's the expected throughput for bulk relationship inserts (e.g., processing 10K filings)?

---

## Summary

Entity Master needs these extensions to support py-sec-edgar:

| Component | Status | Priority |
|-----------|--------|----------|
| Basic entity resolution | ✅ Designed | - |
| Identifier crosswalk | ✅ Designed | - |
| **Relationship storage** | 🔴 Needs extension | HIGH |
| **Mention tracking** | 🔴 Needs extension | HIGH |
| **Event-entity linking** | 🔴 Needs extension | MEDIUM |
| **Change webhooks** | 🟡 Partially designed | MEDIUM |
| **Relationship graph queries** | ✅ Designed (Tier 4) | - |

The unified data model documents ([12_SIGDEV_EVENT_STORAGE.md](../12_SIGDEV_EVENT_STORAGE.md) and [13_UNIFIED_DATA_MODEL.md](../13_UNIFIED_DATA_MODEL.md)) provide the detailed schema that py-sec-edgar will use, and Entity Master should align with these for seamless integration.
