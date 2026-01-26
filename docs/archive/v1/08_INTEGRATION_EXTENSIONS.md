# Entity Master - Integration Extensions

Extensions to support py-sec-edgar and other consumer applications.

---

## Gap Analysis

Based on the [py-sec-edgar integration requirements](05_PYSECEDGAR_INTEGRATION_REQUIREMENTS.md), these extensions are needed:

| Feature | Current Status | Priority |
|---------|---------------|----------|
| Fuzzy name matching with confidence | ✅ Basic search exists | Enhancement |
| Entity types: PERSON, PRODUCT, LOCATION | ⚠️ Only COMPANY, SECURITY | HIGH |
| **Relationship storage with evidence** | 🔴 Read-only queries | HIGH |
| **Entity mention tracking** | 🔴 Not implemented | HIGH |
| **Event-entity linking** | 🔴 Not implemented | MEDIUM |
| **Change detection webhooks** | ⚠️ Partially designed | HIGH |
| Multi-source conflict resolution | 🔴 Not implemented | MEDIUM |
| Confidence aggregation | 🔴 Not implemented | LOW |

---

## Extended Entity Types

```python
# entity_master/models/entity_types.py

from enum import Enum


class EntityType(Enum):
    """All supported entity types."""
    
    # Organizations
    COMPANY = "company"              # Corporations, LLCs, partnerships
    FUND = "fund"                    # Investment funds, ETFs
    GOVERNMENT = "government"        # Government agencies
    NONPROFIT = "nonprofit"          # Non-profit organizations
    
    # Financial Instruments
    SECURITY = "security"            # Stocks, bonds, derivatives
    INDEX = "index"                  # Market indices
    
    # People
    PERSON = "person"                # Executives, directors, investors
    
    # Other
    PRODUCT = "product"              # Products, brands, services
    LOCATION = "location"            # Countries, states, cities
    INDUSTRY = "industry"            # Industry classifications
    EXCHANGE = "exchange"            # Stock exchanges
    
    # Catch-all
    UNKNOWN = "unknown"


class PersonRole(Enum):
    """Roles a person can have with an organization."""
    CEO = "ceo"
    CFO = "cfo"
    COO = "coo"
    CTO = "cto"
    CHAIRMAN = "chairman"
    DIRECTOR = "director"
    EXECUTIVE = "executive"
    FOUNDER = "founder"
    INVESTOR = "investor"
    EMPLOYEE = "employee"
```

---

## Relationships API

Full relationship management with evidence tracking:

```python
# entity_master/api/relationships.py

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from enum import Enum


class RelationshipType(Enum):
    """Relationship types between entities."""
    
    # Supply Chain
    SUPPLIES_TO = "SUPPLIES_TO"
    BUYS_FROM = "BUYS_FROM"
    DISTRIBUTES = "DISTRIBUTES"
    
    # Competition
    COMPETES_WITH = "COMPETES_WITH"
    
    # Corporate Structure
    SUBSIDIARY_OF = "SUBSIDIARY_OF"
    PARENT_OF = "PARENT_OF"
    DIVISION_OF = "DIVISION_OF"
    
    # Transactions
    ACQUIRED = "ACQUIRED"
    ACQUIRED_BY = "ACQUIRED_BY"
    MERGED_WITH = "MERGED_WITH"
    INVESTED_IN = "INVESTED_IN"
    
    # Partnerships
    PARTNER_WITH = "PARTNER_WITH"
    JOINT_VENTURE_WITH = "JOINT_VENTURE_WITH"
    LICENSED_FROM = "LICENSED_FROM"
    LICENSED_TO = "LICENSED_TO"
    
    # People
    EXECUTIVE_OF = "EXECUTIVE_OF"
    BOARD_MEMBER_OF = "BOARD_MEMBER_OF"
    FOUNDER_OF = "FOUNDER_OF"
    EMPLOYED_BY = "EMPLOYED_BY"
    
    # Industry
    OPERATES_IN = "OPERATES_IN"
    MEMBER_OF = "MEMBER_OF"


@dataclass
class RelationshipEvidence:
    """Evidence supporting a relationship."""
    source_system: str              # 'py_sec_edgar', 'news', 'manual'
    source_id: str                  # filing_id, article_id, etc.
    source_section: Optional[str]   # 'Item 1', 'Risk Factors', etc.
    evidence_text: str              # Supporting text excerpt
    extracted_at: datetime = field(default_factory=datetime.utcnow)
    confidence: float = 1.0


@dataclass
class RelationshipMetrics:
    """Quantitative metrics for a relationship."""
    revenue_pct: Optional[float] = None      # Customer concentration
    ownership_pct: Optional[float] = None    # Ownership stake
    deal_value: Optional[float] = None       # Transaction value
    is_sole_source: Optional[bool] = None    # Sole supplier flag
    segment: Optional[str] = None            # Business segment
    custom: dict = field(default_factory=dict)  # Flexible metrics


@dataclass
class Relationship:
    """A relationship between two entities."""
    id: str
    source_entity_id: str
    target_entity_id: str
    relationship_type: RelationshipType
    subtype: Optional[str] = None    # 'major_customer', 'key_vendor', etc.
    
    # Evidence (can have multiple sources confirming same relationship)
    evidence: List[RelationshipEvidence] = field(default_factory=list)
    
    # Metrics
    metrics: RelationshipMetrics = field(default_factory=RelationshipMetrics)
    
    # Aggregated confidence (increases with more evidence)
    confidence: float = 1.0
    
    # Lifecycle
    status: str = "active"           # active, ended, unverified
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


class RelationshipsAPI:
    """Manage entity relationships."""
    
    def __init__(self, storage):
        self._storage = storage
    
    # =========================================================================
    # WRITE OPERATIONS
    # =========================================================================
    
    async def add(
        self,
        source_entity_id: str,
        target_entity_id: str,
        relationship_type: RelationshipType | str,
        subtype: str = None,
        evidence: RelationshipEvidence | dict = None,
        metrics: RelationshipMetrics | dict = None,
        confidence: float = 1.0,
        valid_from: datetime = None,
        valid_to: datetime = None,
    ) -> Relationship:
        """Add or update a relationship.
        
        If relationship already exists, evidence is appended and confidence
        is increased based on the new evidence.
        
        Args:
            source_entity_id: Source entity (e.g., supplier)
            target_entity_id: Target entity (e.g., customer)
            relationship_type: Type of relationship
            subtype: Subtype (e.g., 'major_customer')
            evidence: Supporting evidence
            metrics: Quantitative metrics
            confidence: Confidence score 0-1
            valid_from: When relationship started
            valid_to: When relationship ended (None = ongoing)
        
        Returns:
            Created or updated Relationship
        """
        # Normalize inputs
        if isinstance(relationship_type, str):
            relationship_type = RelationshipType(relationship_type)
        
        if isinstance(evidence, dict):
            evidence = RelationshipEvidence(**evidence)
        
        if isinstance(metrics, dict):
            metrics = RelationshipMetrics(**metrics)
        
        # Check for existing relationship
        existing = await self._storage.get_relationship(
            source_entity_id,
            target_entity_id,
            relationship_type.value,
        )
        
        if existing:
            # Append evidence
            if evidence:
                existing.evidence.append(evidence)
            
            # Aggregate confidence (more evidence = higher confidence)
            existing.confidence = self._aggregate_confidence(existing)
            
            # Merge metrics (prefer non-null values)
            if metrics:
                existing.metrics = self._merge_metrics(existing.metrics, metrics)
            
            # Update timestamps
            existing.last_seen = datetime.utcnow()
            existing.updated_at = datetime.utcnow()
            
            await self._storage.update_relationship(existing)
            return existing
        
        # Create new relationship
        rel = Relationship(
            id=f"{source_entity_id}:{target_entity_id}:{relationship_type.value}",
            source_entity_id=source_entity_id,
            target_entity_id=target_entity_id,
            relationship_type=relationship_type,
            subtype=subtype,
            evidence=[evidence] if evidence else [],
            metrics=metrics or RelationshipMetrics(),
            confidence=confidence,
            first_seen=datetime.utcnow(),
            last_seen=datetime.utcnow(),
            valid_from=valid_from,
            valid_to=valid_to,
        )
        
        await self._storage.add_relationship(rel)
        return rel
    
    async def add_batch(
        self,
        relationships: List[dict],
    ) -> List[Relationship]:
        """Add multiple relationships efficiently.
        
        For bulk imports from filing processing.
        """
        results = []
        for rel_data in relationships:
            rel = await self.add(**rel_data)
            results.append(rel)
        return results
    
    async def end(
        self,
        source_entity_id: str,
        target_entity_id: str,
        relationship_type: str,
        ended_at: datetime = None,
    ):
        """Mark a relationship as ended."""
        rel = await self._storage.get_relationship(
            source_entity_id, target_entity_id, relationship_type
        )
        if rel:
            rel.status = "ended"
            rel.valid_to = ended_at or datetime.utcnow()
            await self._storage.update_relationship(rel)
    
    # =========================================================================
    # READ OPERATIONS
    # =========================================================================
    
    async def get(
        self,
        entity_id: str,
        relationship_type: str = None,
        direction: str = "both",  # "outbound", "inbound", "both"
        status: str = "active",
        include_evidence: bool = False,
    ) -> List[Relationship]:
        """Get relationships for an entity."""
        return await self._storage.query_relationships(
            entity_id=entity_id,
            relationship_type=relationship_type,
            direction=direction,
            status=status,
            include_evidence=include_evidence,
        )
    
    async def get_suppliers(
        self,
        entity_id: str,
        include_metrics: bool = True,
    ) -> List[dict]:
        """Get suppliers of an entity.
        
        Returns entities that SUPPLY_TO this entity.
        """
        rels = await self.get(
            entity_id,
            relationship_type="SUPPLIES_TO",
            direction="inbound",
        )
        return [
            {
                "entity": await self._storage.get_entity(r.source_entity_id),
                "metrics": r.metrics if include_metrics else None,
                "confidence": r.confidence,
            }
            for r in rels
        ]
    
    async def get_customers(
        self,
        entity_id: str,
        include_metrics: bool = True,
    ) -> List[dict]:
        """Get customers of an entity.
        
        Returns entities that this entity SUPPLIES_TO.
        """
        rels = await self.get(
            entity_id,
            relationship_type="SUPPLIES_TO",
            direction="outbound",
        )
        return [
            {
                "entity": await self._storage.get_entity(r.target_entity_id),
                "metrics": r.metrics if include_metrics else None,
                "confidence": r.confidence,
            }
            for r in rels
        ]
    
    async def get_competitors(self, entity_id: str) -> List[dict]:
        """Get competitors (bidirectional relationship)."""
        rels = await self.get(
            entity_id,
            relationship_type="COMPETES_WITH",
            direction="both",
        )
        results = []
        seen = set()
        for r in rels:
            other_id = r.target_entity_id if r.source_entity_id == entity_id else r.source_entity_id
            if other_id not in seen:
                seen.add(other_id)
                results.append({
                    "entity": await self._storage.get_entity(other_id),
                    "confidence": r.confidence,
                })
        return results
    
    async def get_executives(
        self,
        entity_id: str,
        include_board: bool = True,
    ) -> List[dict]:
        """Get executives and optionally board members."""
        types = ["EXECUTIVE_OF"]
        if include_board:
            types.append("BOARD_MEMBER_OF")
        
        results = []
        for rel_type in types:
            rels = await self.get(entity_id, relationship_type=rel_type, direction="inbound")
            for r in rels:
                results.append({
                    "person": await self._storage.get_entity(r.source_entity_id),
                    "role": r.subtype,  # CEO, CFO, Director, etc.
                    "metrics": r.metrics,
                })
        return results
    
    async def get_supply_chain(
        self,
        entity_id: str,
        direction: str = "upstream",  # "upstream", "downstream", "both"
        max_depth: int = 3,
    ) -> dict:
        """Get multi-tier supply chain.
        
        Args:
            entity_id: Starting entity
            direction: upstream (suppliers), downstream (customers), or both
            max_depth: How many tiers to traverse
        
        Returns:
            Nested structure of supply chain relationships
        """
        # Requires graph backend for efficient traversal
        return await self._storage.get_supply_chain(
            entity_id, direction, max_depth
        )
    
    # =========================================================================
    # HELPERS
    # =========================================================================
    
    def _aggregate_confidence(self, rel: Relationship) -> float:
        """Calculate aggregated confidence from multiple evidence sources.
        
        More evidence from different sources = higher confidence.
        """
        if not rel.evidence:
            return rel.confidence
        
        # Group evidence by source system
        sources = set(e.source_system for e in rel.evidence)
        
        # Base confidence from strongest single evidence
        base = max(e.confidence for e in rel.evidence)
        
        # Boost for multiple sources (diminishing returns)
        source_boost = min(0.15, 0.05 * (len(sources) - 1))
        
        # Boost for multiple pieces of evidence
        evidence_boost = min(0.1, 0.02 * (len(rel.evidence) - 1))
        
        return min(1.0, base + source_boost + evidence_boost)
    
    def _merge_metrics(
        self,
        existing: RelationshipMetrics,
        new: RelationshipMetrics,
    ) -> RelationshipMetrics:
        """Merge metrics, preferring newer non-null values."""
        return RelationshipMetrics(
            revenue_pct=new.revenue_pct or existing.revenue_pct,
            ownership_pct=new.ownership_pct or existing.ownership_pct,
            deal_value=new.deal_value or existing.deal_value,
            is_sole_source=new.is_sole_source if new.is_sole_source is not None else existing.is_sole_source,
            segment=new.segment or existing.segment,
            custom={**existing.custom, **new.custom},
        )
```

---

## Mentions API

Track entity mentions across documents:

```python
# entity_master/api/mentions.py

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List


@dataclass
class EntityMention:
    """A mention of an entity in a document."""
    id: str
    entity_id: str
    
    # Source document
    source_system: str              # 'py_sec_edgar', 'news_crawler', etc.
    source_id: str                  # filing_id, article_id
    source_subsection: Optional[str] = None  # section_id, paragraph_id
    
    # Mention details
    mention_text: str               # The text that was matched
    canonical_name: Optional[str] = None  # Resolved entity name
    context: Optional[str] = None   # Surrounding text
    char_start: Optional[int] = None
    char_end: Optional[int] = None
    
    # Classification
    mention_type: str = "reference"  # reference, subject, comparison
    sentiment: Optional[float] = None  # -1 to 1 sentiment score
    confidence: float = 1.0
    
    # Timestamps
    mentioned_at: Optional[datetime] = None  # Document date
    created_at: datetime = field(default_factory=datetime.utcnow)


class MentionsAPI:
    """Track entity mentions across sources."""
    
    def __init__(self, storage):
        self._storage = storage
    
    async def add(
        self,
        entity_id: str,
        source_system: str,
        source_id: str,
        mention_text: str,
        source_subsection: str = None,
        context: str = None,
        char_start: int = None,
        char_end: int = None,
        mention_type: str = "reference",
        sentiment: float = None,
        confidence: float = 1.0,
        mentioned_at: datetime = None,
    ) -> EntityMention:
        """Record an entity mention.
        
        Args:
            entity_id: The entity being mentioned
            source_system: System that found the mention
            source_id: Document ID in source system
            mention_text: The actual text that was matched
            source_subsection: Section within document
            context: Surrounding text for context
            char_start: Character offset start
            char_end: Character offset end
            mention_type: Type of mention
            sentiment: Sentiment score (-1 to 1)
            confidence: Confidence in the match
            mentioned_at: Date of the document
        
        Returns:
            Created EntityMention
        """
        # Get entity for canonical name
        entity = await self._storage.get_entity(entity_id)
        
        mention = EntityMention(
            id=f"{source_system}:{source_id}:{entity_id}:{char_start or 0}",
            entity_id=entity_id,
            source_system=source_system,
            source_id=source_id,
            source_subsection=source_subsection,
            mention_text=mention_text,
            canonical_name=entity.primary_name if entity else None,
            context=context,
            char_start=char_start,
            char_end=char_end,
            mention_type=mention_type,
            sentiment=sentiment,
            confidence=confidence,
            mentioned_at=mentioned_at,
        )
        
        await self._storage.add_mention(mention)
        return mention
    
    async def add_batch(
        self,
        mentions: List[dict],
    ) -> List[EntityMention]:
        """Add multiple mentions efficiently."""
        results = []
        for mention_data in mentions:
            mention = await self.add(**mention_data)
            results.append(mention)
        return results
    
    async def get(
        self,
        entity_id: str,
        source_system: str = None,
        since: datetime = None,
        until: datetime = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[EntityMention]:
        """Get mentions of an entity.
        
        Args:
            entity_id: Entity to get mentions for
            source_system: Filter by source system
            since: Mentions after this date
            until: Mentions before this date
            limit: Max results
            offset: Pagination offset
        
        Returns:
            List of mentions sorted by date descending
        """
        return await self._storage.query_mentions(
            entity_id=entity_id,
            source_system=source_system,
            since=since,
            until=until,
            limit=limit,
            offset=offset,
        )
    
    async def cross_mentions(
        self,
        entity_id: str,
        in_entity_id: str,
        source_system: str = None,
    ) -> List[EntityMention]:
        """Find where entity A is mentioned in entity B's documents.
        
        Useful for finding:
        - Apple mentioned in TSMC's filings (supplier relationship evidence)
        - Competitor mentions in risk factors
        
        Args:
            entity_id: Entity being mentioned
            in_entity_id: Entity whose documents to search
            source_system: Filter by source system
        
        Returns:
            Mentions of entity_id in documents about in_entity_id
        """
        # Get documents about in_entity_id
        # This requires source system to support document-entity mapping
        return await self._storage.query_cross_mentions(
            entity_id=entity_id,
            in_entity_id=in_entity_id,
            source_system=source_system,
        )
    
    async def get_co_mentioned(
        self,
        entity_id: str,
        source_system: str = None,
        min_count: int = 2,
        limit: int = 20,
    ) -> List[dict]:
        """Find entities frequently co-mentioned with this entity.
        
        Useful for discovering relationships.
        
        Returns:
            List of {entity, mention_count, sample_documents}
        """
        return await self._storage.query_co_mentions(
            entity_id=entity_id,
            source_system=source_system,
            min_count=min_count,
            limit=limit,
        )
    
    async def get_mention_count(
        self,
        entity_id: str,
        source_system: str = None,
        since: datetime = None,
    ) -> int:
        """Get total mention count for an entity."""
        return await self._storage.count_mentions(
            entity_id=entity_id,
            source_system=source_system,
            since=since,
        )
```

---

## Events API

Link external events to entities:

```python
# entity_master/api/events.py

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from enum import Enum


class EventRole(Enum):
    """Role an entity plays in an event."""
    SUBJECT = "subject"           # Main entity (the filer)
    TARGET = "target"             # Target of action (acquired company)
    COUNTERPARTY = "counterparty" # Other party (customer, supplier, litigant)
    ACQUIRER = "acquirer"         # Entity doing the acquiring
    PERSON = "person"             # Person involved (new CEO)
    INVESTOR = "investor"         # Investor in transaction
    CUSTOMER = "customer"         # Customer in concentration event
    SUPPLIER = "supplier"         # Supplier in concentration event


@dataclass
class EventEntityLink:
    """Link between an external event and an entity."""
    id: str
    
    # Event reference (event is stored in source system)
    source_system: str              # 'py_sec_edgar_sigdev', 'news_events'
    event_id: str                   # ID in source system
    event_type: Optional[str] = None  # 'MA_ACQUISITION', 'MGMT_APPOINTMENT'
    
    # Entity
    entity_id: str
    role: EventRole
    is_primary: bool = False        # Primary entity for this event
    
    # Context
    notes: Optional[str] = None
    confidence: float = 1.0
    
    # Timestamps
    event_date: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


class EventsAPI:
    """Link events to entities."""
    
    def __init__(self, storage):
        self._storage = storage
    
    async def link(
        self,
        source_system: str,
        event_id: str,
        entity_id: str,
        role: EventRole | str,
        event_type: str = None,
        is_primary: bool = False,
        event_date: datetime = None,
        notes: str = None,
        confidence: float = 1.0,
    ) -> EventEntityLink:
        """Link an event to an entity.
        
        Args:
            source_system: System where event is stored
            event_id: Event ID in that system
            entity_id: Entity ID in Entity Master
            role: Role the entity plays
            event_type: Type of event
            is_primary: Whether this is the primary entity
            event_date: When the event occurred
            notes: Additional context
            confidence: Confidence in the link
        
        Returns:
            Created EventEntityLink
        """
        if isinstance(role, str):
            role = EventRole(role)
        
        link = EventEntityLink(
            id=f"{source_system}:{event_id}:{entity_id}",
            source_system=source_system,
            event_id=event_id,
            event_type=event_type,
            entity_id=entity_id,
            role=role,
            is_primary=is_primary,
            event_date=event_date,
            notes=notes,
            confidence=confidence,
        )
        
        await self._storage.add_event_link(link)
        return link
    
    async def link_batch(
        self,
        links: List[dict],
    ) -> List[EventEntityLink]:
        """Link multiple events to entities."""
        return [await self.link(**link_data) for link_data in links]
    
    async def get_entity_events(
        self,
        entity_id: str,
        event_types: List[str] = None,
        roles: List[EventRole] = None,
        since: datetime = None,
        limit: int = 50,
    ) -> List[EventEntityLink]:
        """Get events involving an entity.
        
        Args:
            entity_id: Entity to get events for
            event_types: Filter by event type
            roles: Filter by role in event
            since: Events after this date
            limit: Max results
        
        Returns:
            Event links sorted by date descending
        """
        return await self._storage.query_event_links(
            entity_id=entity_id,
            event_types=event_types,
            roles=[r.value if isinstance(r, EventRole) else r for r in (roles or [])],
            since=since,
            limit=limit,
        )
    
    async def get_event_entities(
        self,
        source_system: str,
        event_id: str,
    ) -> List[EventEntityLink]:
        """Get all entities linked to an event."""
        return await self._storage.query_event_links(
            source_system=source_system,
            event_id=event_id,
        )
    
    async def resolve_event_entities(
        self,
        source_system: str,
        event_id: str,
    ) -> dict:
        """Get resolved entities for an event, organized by role.
        
        Returns:
            {
                'subject': ResolvedEntity,
                'target': ResolvedEntity,
                'person': ResolvedEntity,
                ...
            }
        """
        links = await self.get_event_entities(source_system, event_id)
        
        result = {}
        for link in links:
            entity = await self._storage.get_entity(link.entity_id)
            role_key = link.role.value if isinstance(link.role, EventRole) else link.role
            
            if link.is_primary or role_key not in result:
                result[role_key] = entity
        
        return result
```

---

## Change Tracking API

Enhanced change detection with webhooks:

```python
# entity_master/api/changes.py

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Callable, Awaitable
from enum import Enum
import asyncio


class ChangeType(Enum):
    """Types of entity changes."""
    CREATED = "created"
    UPDATED = "updated"
    MERGED = "merged"
    DEACTIVATED = "deactivated"
    RELATIONSHIP_ADDED = "relationship_added"
    RELATIONSHIP_REMOVED = "relationship_removed"
    IDENTIFIER_ADDED = "identifier_added"
    IDENTIFIER_REMOVED = "identifier_removed"


@dataclass
class EntityChange:
    """A change to an entity."""
    id: str
    entity_id: str
    change_type: ChangeType
    
    # What changed
    changed_fields: List[str] = field(default_factory=list)
    old_values: dict = field(default_factory=dict)
    new_values: dict = field(default_factory=dict)
    
    # Metadata
    changed_by: Optional[str] = None  # Source system that made the change
    reason: Optional[str] = None
    
    # Timestamps
    changed_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class WebhookSubscription:
    """A webhook subscription."""
    id: str
    url: str
    events: List[ChangeType]
    filters: dict = field(default_factory=dict)  # e.g., {"entity_type": "company"}
    secret: Optional[str] = None
    active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)


class ChangesAPI:
    """Track and broadcast entity changes."""
    
    def __init__(self, storage):
        self._storage = storage
        self._webhooks: List[WebhookSubscription] = []
        self._listeners: List[Callable[[EntityChange], Awaitable[None]]] = []
    
    async def record(
        self,
        entity_id: str,
        change_type: ChangeType,
        changed_fields: List[str] = None,
        old_values: dict = None,
        new_values: dict = None,
        changed_by: str = None,
        reason: str = None,
    ) -> EntityChange:
        """Record a change and notify subscribers.
        
        Called internally by Entity Master when entities change.
        """
        change = EntityChange(
            id=f"{entity_id}:{datetime.utcnow().timestamp()}",
            entity_id=entity_id,
            change_type=change_type,
            changed_fields=changed_fields or [],
            old_values=old_values or {},
            new_values=new_values or {},
            changed_by=changed_by,
            reason=reason,
        )
        
        await self._storage.add_change(change)
        
        # Notify listeners asynchronously
        asyncio.create_task(self._notify(change))
        
        return change
    
    async def get_since(
        self,
        since: datetime,
        change_types: List[ChangeType] = None,
        entity_types: List[str] = None,
        entity_ids: List[str] = None,
        limit: int = 1000,
    ) -> List[EntityChange]:
        """Get changes since a timestamp.
        
        Args:
            since: Get changes after this time
            change_types: Filter by change type
            entity_types: Filter by entity type
            entity_ids: Filter by specific entities
            limit: Max results
        
        Returns:
            Changes sorted by timestamp ascending
        """
        return await self._storage.query_changes(
            since=since,
            change_types=[c.value for c in (change_types or [])],
            entity_types=entity_types,
            entity_ids=entity_ids,
            limit=limit,
        )
    
    async def get_entity_history(
        self,
        entity_id: str,
        since: datetime = None,
        limit: int = 100,
    ) -> List[EntityChange]:
        """Get change history for a specific entity."""
        return await self._storage.query_changes(
            entity_ids=[entity_id],
            since=since,
            limit=limit,
        )
    
    # =========================================================================
    # WEBHOOK MANAGEMENT
    # =========================================================================
    
    async def subscribe_webhook(
        self,
        url: str,
        events: List[ChangeType] = None,
        filters: dict = None,
        secret: str = None,
    ) -> WebhookSubscription:
        """Register a webhook for change notifications.
        
        Args:
            url: URL to POST changes to
            events: Event types to subscribe to (None = all)
            filters: Filter criteria (e.g., {"entity_type": "company"})
            secret: HMAC secret for signature verification
        
        Returns:
            Created subscription
        """
        sub = WebhookSubscription(
            id=f"webhook_{len(self._webhooks)}",
            url=url,
            events=events or list(ChangeType),
            filters=filters or {},
            secret=secret,
        )
        
        self._webhooks.append(sub)
        await self._storage.add_webhook(sub)
        return sub
    
    async def unsubscribe_webhook(self, webhook_id: str):
        """Remove a webhook subscription."""
        self._webhooks = [w for w in self._webhooks if w.id != webhook_id]
        await self._storage.remove_webhook(webhook_id)
    
    # =========================================================================
    # IN-PROCESS LISTENERS
    # =========================================================================
    
    def add_listener(
        self,
        callback: Callable[[EntityChange], Awaitable[None]],
    ):
        """Add an in-process change listener.
        
        For applications using Entity Master as a library.
        """
        self._listeners.append(callback)
    
    def remove_listener(
        self,
        callback: Callable[[EntityChange], Awaitable[None]],
    ):
        """Remove an in-process listener."""
        self._listeners = [l for l in self._listeners if l != callback]
    
    # =========================================================================
    # INTERNAL
    # =========================================================================
    
    async def _notify(self, change: EntityChange):
        """Notify all subscribers of a change."""
        # Get entity for filtering
        entity = await self._storage.get_entity(change.entity_id)
        
        # Notify webhooks
        for webhook in self._webhooks:
            if self._matches_subscription(change, entity, webhook):
                asyncio.create_task(self._call_webhook(webhook, change, entity))
        
        # Notify in-process listeners
        for listener in self._listeners:
            try:
                await listener(change)
            except Exception as e:
                # Log but don't fail
                pass
    
    def _matches_subscription(
        self,
        change: EntityChange,
        entity: dict,
        sub: WebhookSubscription,
    ) -> bool:
        """Check if change matches subscription filters."""
        # Check event type
        if change.change_type not in sub.events:
            return False
        
        # Check filters
        for key, value in sub.filters.items():
            if key == "entity_type" and entity.get("entity_type") != value:
                return False
            if key == "entity_id" and change.entity_id != value:
                return False
        
        return True
    
    async def _call_webhook(
        self,
        webhook: WebhookSubscription,
        change: EntityChange,
        entity: dict,
    ):
        """Send change to webhook URL."""
        import httpx
        import hmac
        import hashlib
        import json
        
        payload = {
            "event_type": f"entity.{change.change_type.value}",
            "entity_id": change.entity_id,
            "entity": entity,
            "changes": {
                "fields": change.changed_fields,
                "old": change.old_values,
                "new": change.new_values,
            },
            "timestamp": change.changed_at.isoformat(),
        }
        
        body = json.dumps(payload)
        headers = {"Content-Type": "application/json"}
        
        # Add signature if secret configured
        if webhook.secret:
            signature = hmac.new(
                webhook.secret.encode(),
                body.encode(),
                hashlib.sha256,
            ).hexdigest()
            headers["X-Entity-Master-Signature"] = f"sha256={signature}"
        
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    webhook.url,
                    content=body,
                    headers=headers,
                    timeout=10.0,
                )
        except Exception as e:
            # Log webhook failure
            pass
```

---

## Updated Storage Schema

Additional tables for the new APIs:

```sql
-- Add to 02_STORAGE_BACKENDS.md PostgreSQL schema

-- Relationships with full evidence tracking
CREATE TABLE relationships (
    id VARCHAR(255) PRIMARY KEY,
    source_entity_id VARCHAR(100) NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    target_entity_id VARCHAR(100) NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    relationship_type VARCHAR(50) NOT NULL,
    subtype VARCHAR(50),
    
    -- Aggregated confidence
    confidence DECIMAL(3,2) DEFAULT 1.0,
    
    -- Metrics (flexible)
    metrics JSONB DEFAULT '{}',
    
    -- Lifecycle
    status VARCHAR(20) DEFAULT 'active',
    first_seen TIMESTAMPTZ,
    last_seen TIMESTAMPTZ,
    valid_from DATE,
    valid_to DATE,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(source_entity_id, target_entity_id, relationship_type)
);

-- Evidence for relationships
CREATE TABLE relationship_evidence (
    id SERIAL PRIMARY KEY,
    relationship_id VARCHAR(255) NOT NULL REFERENCES relationships(id) ON DELETE CASCADE,
    source_system VARCHAR(50) NOT NULL,
    source_id VARCHAR(255) NOT NULL,
    source_section VARCHAR(100),
    evidence_text TEXT,
    confidence DECIMAL(3,2) DEFAULT 1.0,
    extracted_at TIMESTAMPTZ DEFAULT NOW()
);

-- Entity mentions
CREATE TABLE entity_mentions (
    id VARCHAR(255) PRIMARY KEY,
    entity_id VARCHAR(100) NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    
    source_system VARCHAR(50) NOT NULL,
    source_id VARCHAR(255) NOT NULL,
    source_subsection VARCHAR(100),
    
    mention_text VARCHAR(500) NOT NULL,
    canonical_name VARCHAR(500),
    context TEXT,
    char_start INT,
    char_end INT,
    
    mention_type VARCHAR(50) DEFAULT 'reference',
    sentiment DECIMAL(3,2),
    confidence DECIMAL(3,2) DEFAULT 1.0,
    
    mentioned_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Event-entity links
CREATE TABLE event_entity_links (
    id VARCHAR(255) PRIMARY KEY,
    source_system VARCHAR(50) NOT NULL,
    event_id VARCHAR(255) NOT NULL,
    event_type VARCHAR(50),
    
    entity_id VARCHAR(100) NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL,
    is_primary BOOLEAN DEFAULT false,
    
    notes TEXT,
    confidence DECIMAL(3,2) DEFAULT 1.0,
    event_date TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Change log
CREATE TABLE entity_changes (
    id VARCHAR(255) PRIMARY KEY,
    entity_id VARCHAR(100) REFERENCES entities(id) ON DELETE SET NULL,
    change_type VARCHAR(50) NOT NULL,
    changed_fields TEXT[],
    old_values JSONB,
    new_values JSONB,
    changed_by VARCHAR(100),
    reason TEXT,
    changed_at TIMESTAMPTZ DEFAULT NOW()
);

-- Webhook subscriptions
CREATE TABLE webhook_subscriptions (
    id VARCHAR(100) PRIMARY KEY,
    url VARCHAR(500) NOT NULL,
    events TEXT[] NOT NULL,
    filters JSONB DEFAULT '{}',
    secret VARCHAR(255),
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_relationships_source ON relationships(source_entity_id);
CREATE INDEX idx_relationships_target ON relationships(target_entity_id);
CREATE INDEX idx_relationships_type ON relationships(relationship_type);
CREATE INDEX idx_mentions_entity ON entity_mentions(entity_id);
CREATE INDEX idx_mentions_source ON entity_mentions(source_system, source_id);
CREATE INDEX idx_event_links_entity ON event_entity_links(entity_id);
CREATE INDEX idx_event_links_event ON event_entity_links(source_system, event_id);
CREATE INDEX idx_changes_entity ON entity_changes(entity_id);
CREATE INDEX idx_changes_timestamp ON entity_changes(changed_at);
```

---

## Updated EntityMaster Class

Integrate new APIs into main class:

```python
# entity_master/__init__.py

from entity_master.api.relationships import RelationshipsAPI
from entity_master.api.mentions import MentionsAPI
from entity_master.api.events import EventsAPI
from entity_master.api.changes import ChangesAPI


class EntityMaster:
    """Main Entity Master interface with all APIs."""
    
    def __init__(self, tier: str = "auto", **config):
        self._storage = create_storage(tier, **config)
        
        # Sub-APIs
        self.relationships = RelationshipsAPI(self._storage)
        self.mentions = MentionsAPI(self._storage)
        self.events = EventsAPI(self._storage)
        self.changes = ChangesAPI(self._storage)
    
    # ... existing resolution methods ...
    
    # Convenience aliases
    @property
    def rels(self) -> RelationshipsAPI:
        """Alias for relationships API."""
        return self.relationships
```

---

## py-sec-edgar Integration Example

Complete integration pattern:

```python
# In py-sec-edgar: filing processing with Entity Master

from entity_master import EntityMaster
from entity_master.api.relationships import RelationshipType, RelationshipEvidence


class FilingEntityExtractor:
    """Extract and store entities from SEC filings."""
    
    def __init__(self, entity_master: EntityMaster):
        self.em = entity_master
    
    async def process_filing(self, filing: dict):
        """Process a filing and update Entity Master."""
        filer_entity = await self.em.resolve(filing["cik"])
        
        # Extract customer relationships from Item 1
        customers = self.extract_customers(filing["sections"]["item_1"])
        for customer_name, metrics in customers:
            # Resolve customer entity (may create new)
            customer = await self.em.resolve(
                customer_name,
                min_confidence=0.7,
            )
            
            if customer:
                await self.em.relationships.add(
                    source_entity_id=filer_entity.id,
                    target_entity_id=customer.id,
                    relationship_type=RelationshipType.SUPPLIES_TO,
                    subtype="major_customer",
                    evidence=RelationshipEvidence(
                        source_system="py_sec_edgar",
                        source_id=filing["accession_number"],
                        source_section="Item 1",
                        evidence_text=metrics.get("evidence_text", ""),
                        confidence=0.9,
                    ),
                    metrics={"revenue_pct": metrics.get("revenue_pct")},
                )
        
        # Record mentions
        for mention in self.extract_mentions(filing):
            entity = await self.em.resolve(mention["text"], min_confidence=0.8)
            if entity:
                await self.em.mentions.add(
                    entity_id=entity.id,
                    source_system="py_sec_edgar",
                    source_id=filing["accession_number"],
                    mention_text=mention["text"],
                    context=mention["context"],
                    char_start=mention["start"],
                    char_end=mention["end"],
                )
```
