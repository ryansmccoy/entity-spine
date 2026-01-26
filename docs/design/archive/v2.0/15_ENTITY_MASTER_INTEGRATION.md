# py-sec-edgar ↔ Entity Master v2 Integration

**Interface Specification | API Contracts | Data Flow Patterns**

---

## Integration Summary

py-sec-edgar is a **consumer** of Entity Master v2. It does NOT manage entities directly.

| Responsibility | py-sec-edgar | Entity Master v2 |
|---------------|--------------|------------------|
| Filer identification | Uses CIK from SEC filings | Owns canonical entity_id |
| Entity resolution | Calls EntityResolver port | Provides resolution API |
| Name/ticker lookup | Sends query | Returns entity_id |
| Relationship extraction | Extracts from text | Stores in graph |
| Mention tracking | Extracts mentions | May aggregate |
| Provisional entities | Creates mentions | Manages lifecycle |

---

## 1. Identifier Scope Rules

Entity Master v2 enforces strict identifier scoping. py-sec-edgar must respect these:

### 1.1 What py-sec-edgar Encounters in SEC Filings

| Identifier | Scope | Where Found | Resolution Target |
|------------|-------|-------------|-------------------|
| **CIK** | Entity | All filings | `entities.entity_id` |
| **Ticker** | Listing | Text mentions, headers | `listings.listing_id` → `securities.security_id` → `entities.entity_id` |
| **CUSIP** | Security | 13F, prospectuses | `securities.security_id` → `entities.entity_id` |
| **ISIN** | Security | Foreign filings | `securities.security_id` → `entities.entity_id` |
| **FIGI** | Security/Listing | Rare in filings | Varies by prefix |
| **Company Name** | Entity | Text mentions | `entities.entity_id` |
| **Person Name** | Entity | Proxy, 8-K | `entities.entity_id` (PERSON type) |

### 1.2 Resolution Scope Matrix

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    IDENTIFIER → ENTITY RESOLUTION                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  CIK           ─────────────────────────────────────→  entity_id ✓          │
│  (Entity Scope)                                                              │
│                                                                              │
│  Ticker + MIC  ──→ listing_id ──→ security_id ──→ entity_id ✓               │
│  (Listing Scope)                                                             │
│                                                                              │
│  ISIN, CUSIP   ──────────────→ security_id ──────→ entity_id ✓              │
│  (Security Scope)                                                            │
│                                                                              │
│  Company Name  ─────────────────────────────────────→ entity_id ✓           │
│  (Fuzzy Match)                                                               │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. EntityResolverPort Interface

### 2.1 Port Definition

```python
# py_sec_edgar/ports/entity_resolver.py

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from typing import Optional, Literal
from enum import Enum


class IdentifierType(Enum):
    """Identifier types recognized by Entity Master v2."""
    # Entity scope
    CIK = "CIK"
    LEI = "LEI"
    EIN = "EIN"
    DUNS = "DUNS"
    
    # Security scope
    ISIN = "ISIN"
    CUSIP = "CUSIP"
    SEDOL = "SEDOL"
    FIGI = "FIGI"  # Composite FIGI (security)
    
    # Listing scope
    TICKER = "TICKER"
    RIC = "RIC"
    SHARE_CLASS_FIGI = "SHARE_CLASS_FIGI"
    
    # Generic
    NAME = "NAME"


@dataclass(frozen=True)
class ResolvedEntity:
    """Result of entity resolution from Entity Master v2."""
    
    # Entity Master canonical IDs (ULID format)
    entity_id: Optional[str] = None      # e.g., "01HYB7GKPD3MX9VNPBQ2T6XNYW"
    security_id: Optional[str] = None
    listing_id: Optional[str] = None
    
    # Basic information
    primary_name: str = ""
    legal_name: Optional[str] = None
    entity_type: str = "COMPANY"  # COMPANY, FUND, PERSON, GOVERNMENT, SPV
    status: str = "ACTIVE"
    
    # Key identifiers
    cik: Optional[str] = None
    lei: Optional[str] = None
    ticker: Optional[str] = None
    isin: Optional[str] = None
    
    # Resolution metadata
    confidence: float = 1.0
    is_provisional: bool = False
    was_merged: bool = False
    canonical_id: Optional[str] = None  # If merged, the current canonical ID
    
    # Additional identifiers (all returned by Entity Master)
    identifiers: dict = field(default_factory=dict)
    
    def __post_init__(self):
        if self.was_merged and not self.canonical_id:
            object.__setattr__(self, 'canonical_id', self.entity_id)


@dataclass
class ResolutionRequest:
    """Request to resolve an identifier or name."""
    query: str
    identifier_type: Optional[IdentifierType] = None
    min_confidence: float = 0.7
    as_of_date: Optional[date] = None
    mic: Optional[str] = None  # For ticker resolution
    create_provisional: bool = False
    context: Optional[str] = None  # Additional context for fuzzy matching


@dataclass 
class ResolutionResult:
    """Result of resolution attempt."""
    success: bool
    entity: Optional[ResolvedEntity] = None
    candidates: list[ResolvedEntity] = field(default_factory=list)
    error: Optional[str] = None
    resolution_path: Optional[str] = None  # e.g., "TICKER→LISTING→SECURITY→ENTITY"


class EntityResolverPort(ABC):
    """
    Port interface for Entity Master v2 integration.
    
    py-sec-edgar uses this port to:
    1. Resolve identifiers found in SEC filings
    2. Look up entities by CIK, ticker, CUSIP, etc.
    3. Create provisional entities for unresolved mentions
    4. Push extracted relationships back to Entity Master
    
    Implementations:
    - RemoteEntityResolverAdapter: Calls Entity Master HTTP API
    - LocalEntityResolverAdapter: Direct database queries (for co-located deployments)
    - MockEntityResolverAdapter: For testing
    - CachedEntityResolverAdapter: Wraps another adapter with caching
    """
    
    @abstractmethod
    async def resolve(self, request: ResolutionRequest) -> ResolutionResult:
        """
        Resolve any identifier or name to Entity Master canonical record.
        
        Resolution follows Entity Master v2 scope rules:
        - CIK, LEI → Entity directly
        - ISIN, CUSIP → Security → Entity
        - Ticker → Listing → Security → Entity
        - Name → Fuzzy match → Entity
        """
        pass
    
    @abstractmethod
    async def resolve_cik(self, cik: str) -> ResolutionResult:
        """
        Resolve SEC CIK to entity.
        
        CIK is entity-scoped in Entity Master v2.
        This is the most common resolution for py-sec-edgar.
        """
        pass
    
    @abstractmethod
    async def resolve_ticker(
        self,
        ticker: str,
        mic: Optional[str] = None,
        as_of_date: Optional[date] = None,
    ) -> ResolutionResult:
        """
        Resolve ticker to entity via listing → security → entity chain.
        
        Args:
            ticker: Trading symbol (e.g., "AAPL")
            mic: Market identifier code (e.g., "XNAS" for NASDAQ)
            as_of_date: Point-in-time resolution (for historical tickers)
        
        Returns full chain: listing_id, security_id, entity_id
        """
        pass
    
    @abstractmethod
    async def resolve_cusip(
        self,
        cusip: str,
        as_of_date: Optional[date] = None,
    ) -> ResolutionResult:
        """
        Resolve CUSIP to entity via security → entity chain.
        
        Used for 13F filings which report holdings by CUSIP.
        """
        pass
    
    @abstractmethod
    async def resolve_isin(self, isin: str) -> ResolutionResult:
        """Resolve ISIN to entity via security → entity chain."""
        pass
    
    @abstractmethod
    async def resolve_name(
        self,
        name: str,
        context: Optional[str] = None,
        min_confidence: float = 0.7,
    ) -> ResolutionResult:
        """
        Fuzzy name match to entity.
        
        Args:
            name: Company or person name
            context: Additional context (e.g., "technology company", "CEO of X")
            min_confidence: Minimum match confidence threshold
        """
        pass
    
    @abstractmethod
    async def get_entity(self, entity_id: str) -> Optional[ResolvedEntity]:
        """
        Get entity by Entity Master entity_id.
        
        Handles merged entities automatically (returns canonical if merged).
        """
        pass
    
    @abstractmethod
    async def get_entity_by_cik(self, cik: str) -> Optional[ResolvedEntity]:
        """Convenience method for CIK lookup."""
        pass
    
    @abstractmethod
    async def create_provisional(
        self,
        name: str,
        source_system: str,
        source_id: str,
        entity_type: str = "COMPANY",
        context: Optional[str] = None,
    ) -> ResolvedEntity:
        """
        Create a provisional entity for an unresolved mention.
        
        Entity Master will track provisionals separately and
        merge them when a canonical entity is identified.
        """
        pass
    
    @abstractmethod
    async def add_relationship(
        self,
        source_entity_id: str,
        target_entity_id: str,
        relationship_type: str,
        evidence: dict,
        metrics: Optional[dict] = None,
        valid_from: Optional[date] = None,
        valid_to: Optional[date] = None,
        bidirectional: bool = False,
    ) -> str:
        """
        Push extracted relationship to Entity Master.
        
        Args:
            source_entity_id: Entity Master entity_id
            target_entity_id: Entity Master entity_id
            relationship_type: One of RelationshipType enum values
            evidence: Evidence dictionary with source_system, source_id, etc.
            metrics: Optional metrics (revenue_pct, count, etc.)
            valid_from: Start of relationship validity
            valid_to: End of relationship validity
            bidirectional: If True, also creates reverse relationship
        
        Returns:
            relationship_id from Entity Master
        """
        pass
    
    @abstractmethod
    async def record_mention(
        self,
        entity_id: str,
        filing_id: str,
        section_id: Optional[str],
        mention_text: str,
        context: str,
        confidence: float,
        position: Optional[dict] = None,
    ) -> str:
        """
        Record an entity mention in Entity Master.
        
        Entity Master can aggregate mentions for frequency analysis.
        """
        pass
    
    @abstractmethod
    async def batch_resolve(
        self,
        requests: list[ResolutionRequest],
    ) -> list[ResolutionResult]:
        """
        Batch resolution for efficiency.
        
        Used when processing multiple mentions from a single filing.
        """
        pass


class RelationshipType(Enum):
    """
    Relationship types that py-sec-edgar can extract.
    Entity Master v2 accepts these via add_relationship().
    """
    # Customer/supplier
    SUPPLIES_TO = "SUPPLIES_TO"          # A supplies to B
    CUSTOMER_OF = "CUSTOMER_OF"          # A is customer of B
    
    # Competition
    COMPETES_WITH = "COMPETES_WITH"      # Bidirectional
    
    # M&A
    ACQUIRED = "ACQUIRED"                 # A acquired B
    MERGED_WITH = "MERGED_WITH"          # Bidirectional
    SPUN_OFF = "SPUN_OFF"                # A spun off B
    
    # Corporate structure
    SUBSIDIARY_OF = "SUBSIDIARY_OF"       # A is subsidiary of B
    CONTROLS = "CONTROLS"                 # A controls B
    
    # Legal
    LITIGATING_WITH = "LITIGATING_WITH"  # Bidirectional
    SETTLED_WITH = "SETTLED_WITH"
    
    # Personnel
    HIRED_FROM = "HIRED_FROM"            # A hired executive from B
    
    # Business
    PARTNER_OF = "PARTNER_OF"            # Bidirectional
    LICENSED_FROM = "LICENSED_FROM"      # A licensed IP from B
    INVESTED_IN = "INVESTED_IN"          # A invested in B
```

### 2.2 Adapter Implementations

```python
# py_sec_edgar/adapters/entity_resolver/remote.py

import httpx
from typing import Optional
from datetime import date

from py_sec_edgar.ports.entity_resolver import (
    EntityResolverPort,
    ResolutionRequest,
    ResolutionResult,
    ResolvedEntity,
    IdentifierType,
)


class RemoteEntityResolverAdapter(EntityResolverPort):
    """
    HTTP adapter for Entity Master v2 API.
    """
    
    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        timeout: float = 10.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout,
            headers={"Authorization": f"Bearer {api_key}"} if api_key else {},
        )
    
    async def resolve(self, request: ResolutionRequest) -> ResolutionResult:
        resp = await self.client.post(
            "/api/v2/resolve",
            json={
                "query": request.query,
                "identifier_type": request.identifier_type.value if request.identifier_type else None,
                "min_confidence": request.min_confidence,
                "as_of_date": request.as_of_date.isoformat() if request.as_of_date else None,
                "mic": request.mic,
                "create_provisional": request.create_provisional,
                "context": request.context,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        
        return ResolutionResult(
            success=data["success"],
            entity=self._parse_entity(data.get("entity")),
            candidates=[self._parse_entity(c) for c in data.get("candidates", [])],
            error=data.get("error"),
            resolution_path=data.get("resolution_path"),
        )
    
    async def resolve_cik(self, cik: str) -> ResolutionResult:
        return await self.resolve(ResolutionRequest(
            query=cik.zfill(10),
            identifier_type=IdentifierType.CIK,
        ))
    
    async def resolve_ticker(
        self,
        ticker: str,
        mic: Optional[str] = None,
        as_of_date: Optional[date] = None,
    ) -> ResolutionResult:
        return await self.resolve(ResolutionRequest(
            query=ticker.upper(),
            identifier_type=IdentifierType.TICKER,
            mic=mic,
            as_of_date=as_of_date,
        ))
    
    async def resolve_cusip(
        self,
        cusip: str,
        as_of_date: Optional[date] = None,
    ) -> ResolutionResult:
        return await self.resolve(ResolutionRequest(
            query=cusip,
            identifier_type=IdentifierType.CUSIP,
            as_of_date=as_of_date,
        ))
    
    async def resolve_isin(self, isin: str) -> ResolutionResult:
        return await self.resolve(ResolutionRequest(
            query=isin,
            identifier_type=IdentifierType.ISIN,
        ))
    
    async def resolve_name(
        self,
        name: str,
        context: Optional[str] = None,
        min_confidence: float = 0.7,
    ) -> ResolutionResult:
        return await self.resolve(ResolutionRequest(
            query=name,
            identifier_type=IdentifierType.NAME,
            min_confidence=min_confidence,
            context=context,
        ))
    
    async def get_entity(self, entity_id: str) -> Optional[ResolvedEntity]:
        resp = await self.client.get(f"/api/v2/entities/{entity_id}")
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return self._parse_entity(resp.json())
    
    async def get_entity_by_cik(self, cik: str) -> Optional[ResolvedEntity]:
        result = await self.resolve_cik(cik)
        return result.entity if result.success else None
    
    async def create_provisional(
        self,
        name: str,
        source_system: str,
        source_id: str,
        entity_type: str = "COMPANY",
        context: Optional[str] = None,
    ) -> ResolvedEntity:
        resp = await self.client.post(
            "/api/v2/entities/provisional",
            json={
                "name": name,
                "source_system": source_system,
                "source_id": source_id,
                "entity_type": entity_type,
                "context": context,
            },
        )
        resp.raise_for_status()
        return self._parse_entity(resp.json())
    
    async def add_relationship(
        self,
        source_entity_id: str,
        target_entity_id: str,
        relationship_type: str,
        evidence: dict,
        metrics: Optional[dict] = None,
        valid_from: Optional[date] = None,
        valid_to: Optional[date] = None,
        bidirectional: bool = False,
    ) -> str:
        resp = await self.client.post(
            "/api/v2/relationships",
            json={
                "source_entity_id": source_entity_id,
                "target_entity_id": target_entity_id,
                "relationship_type": relationship_type,
                "evidence": evidence,
                "metrics": metrics or {},
                "valid_from": valid_from.isoformat() if valid_from else None,
                "valid_to": valid_to.isoformat() if valid_to else None,
                "bidirectional": bidirectional,
            },
        )
        resp.raise_for_status()
        return resp.json()["relationship_id"]
    
    async def record_mention(
        self,
        entity_id: str,
        filing_id: str,
        section_id: Optional[str],
        mention_text: str,
        context: str,
        confidence: float,
        position: Optional[dict] = None,
    ) -> str:
        resp = await self.client.post(
            "/api/v2/mentions",
            json={
                "entity_id": entity_id,
                "source_system": "py_sec_edgar",
                "source_id": filing_id,
                "source_section": section_id,
                "mention_text": mention_text,
                "context": context,
                "confidence": confidence,
                "position": position,
            },
        )
        resp.raise_for_status()
        return resp.json()["mention_id"]
    
    async def batch_resolve(
        self,
        requests: list[ResolutionRequest],
    ) -> list[ResolutionResult]:
        resp = await self.client.post(
            "/api/v2/resolve/batch",
            json=[
                {
                    "query": r.query,
                    "identifier_type": r.identifier_type.value if r.identifier_type else None,
                    "min_confidence": r.min_confidence,
                    "as_of_date": r.as_of_date.isoformat() if r.as_of_date else None,
                }
                for r in requests
            ],
        )
        resp.raise_for_status()
        return [
            ResolutionResult(
                success=d["success"],
                entity=self._parse_entity(d.get("entity")),
                candidates=[self._parse_entity(c) for c in d.get("candidates", [])],
                error=d.get("error"),
            )
            for d in resp.json()
        ]
    
    def _parse_entity(self, data: Optional[dict]) -> Optional[ResolvedEntity]:
        if not data:
            return None
        return ResolvedEntity(
            entity_id=data.get("entity_id"),
            security_id=data.get("security_id"),
            listing_id=data.get("listing_id"),
            primary_name=data.get("primary_name", ""),
            legal_name=data.get("legal_name"),
            entity_type=data.get("entity_type", "COMPANY"),
            status=data.get("status", "ACTIVE"),
            cik=data.get("cik"),
            lei=data.get("lei"),
            ticker=data.get("ticker"),
            isin=data.get("isin"),
            confidence=data.get("confidence", 1.0),
            is_provisional=data.get("is_provisional", False),
            was_merged=data.get("was_merged", False),
            canonical_id=data.get("canonical_id"),
            identifiers=data.get("identifiers", {}),
        )
```

---

## 3. py-sec-edgar Usage Patterns

### 3.1 Filing Ingestion

```python
# py_sec_edgar/services/filing_ingestor.py

from py_sec_edgar.ports.entity_resolver import EntityResolverPort
from py_sec_edgar.storage.filings import FilingStorage
from datetime import date


class FilingIngestorService:
    def __init__(
        self,
        filing_storage: FilingStorage,
        entity_resolver: EntityResolverPort,
    ):
        self.filing_storage = filing_storage
        self.entity_resolver = entity_resolver
    
    async def ingest_filing(self, raw_filing: dict) -> str:
        """
        Ingest a filing from SEC EDGAR.
        Resolves CIK to Entity Master entity_id.
        """
        cik = raw_filing["cik"]
        
        # Resolve filer to Entity Master
        result = await self.entity_resolver.resolve_cik(cik)
        
        if not result.success:
            # CIK should always resolve (SEC registered entities)
            raise ValueError(f"Could not resolve CIK {cik}: {result.error}")
        
        # Store filing with entity_id
        filing_id = await self.filing_storage.insert_filing(
            filer_entity_id=result.entity.entity_id,
            cik=cik,
            accession_number=raw_filing["accession_number"],
            form_type=raw_filing["form_type"],
            filed_date=raw_filing["filed_date"],
            # ... other fields
        )
        
        return filing_id
```

### 3.2 Entity Mention Extraction

```python
# py_sec_edgar/services/mention_extractor.py

import re
from dataclasses import dataclass
from typing import Optional

from py_sec_edgar.ports.entity_resolver import (
    EntityResolverPort,
    ResolutionRequest,
    IdentifierType,
)


@dataclass
class ExtractedMention:
    text: str
    mention_type: str  # 'company', 'ticker', 'person'
    start: int
    end: int
    context: str


class MentionExtractorService:
    """
    Extract and resolve entity mentions from section text.
    """
    
    TICKER_PATTERN = re.compile(r'\((?:NASDAQ|NYSE|AMEX|OTC):\s*([A-Z]{1,5})\)')
    CUSIP_PATTERN = re.compile(r'\b([0-9A-Z]{9})\b')  # Simplified
    
    def __init__(self, entity_resolver: EntityResolverPort):
        self.entity_resolver = entity_resolver
    
    async def extract_and_resolve(
        self,
        text: str,
        filing_id: str,
        section_id: str,
    ) -> list[dict]:
        """
        Extract mentions and resolve to Entity Master entities.
        """
        mentions = self._extract_mentions(text)
        
        # Batch resolve for efficiency
        requests = [
            ResolutionRequest(
                query=m.text,
                identifier_type=self._get_identifier_type(m),
                min_confidence=0.7,
                create_provisional=True,
                context=m.context,
            )
            for m in mentions
        ]
        
        results = await self.entity_resolver.batch_resolve(requests)
        
        # Build resolved mentions
        resolved = []
        for mention, result in zip(mentions, results):
            resolved.append({
                "filing_id": filing_id,
                "section_id": section_id,
                "mention_text": mention.text,
                "mention_type": mention.mention_type,
                "char_start": mention.start,
                "char_end": mention.end,
                "sentence_context": mention.context,
                "resolution_status": "resolved" if result.success else "unresolved",
                "entity_id": result.entity.entity_id if result.success else None,
                "security_id": result.entity.security_id if result.success else None,
                "listing_id": result.entity.listing_id if result.success else None,
                "resolution_confidence": result.entity.confidence if result.success else None,
                "provisional_entity_id": (
                    result.entity.entity_id
                    if result.success and result.entity.is_provisional
                    else None
                ),
            })
        
        return resolved
    
    def _extract_mentions(self, text: str) -> list[ExtractedMention]:
        """Extract raw mentions from text."""
        mentions = []
        
        # Extract ticker mentions
        for match in self.TICKER_PATTERN.finditer(text):
            ticker = match.group(1)
            context = text[max(0, match.start()-100):match.end()+100]
            mentions.append(ExtractedMention(
                text=ticker,
                mention_type="ticker",
                start=match.start(),
                end=match.end(),
                context=context,
            ))
        
        # ... more extraction patterns
        
        return mentions
    
    def _get_identifier_type(self, mention: ExtractedMention) -> Optional[IdentifierType]:
        if mention.mention_type == "ticker":
            return IdentifierType.TICKER
        elif mention.mention_type == "cusip":
            return IdentifierType.CUSIP
        elif mention.mention_type == "company":
            return IdentifierType.NAME
        return None
```

### 3.3 SIGDEV Event Extraction

```python
# py_sec_edgar/services/sigdev/event_extractor.py

from py_sec_edgar.ports.entity_resolver import (
    EntityResolverPort,
    RelationshipType,
)
from py_sec_edgar.services.sigdev.detectors import CustomerConcentrationDetector


class SigdevEventExtractor:
    """
    Extract SIGDEV events and link to Entity Master.
    """
    
    def __init__(self, entity_resolver: EntityResolverPort):
        self.entity_resolver = entity_resolver
        self.detectors = [
            CustomerConcentrationDetector(),
            # ... more detectors
        ]
    
    async def extract_events(
        self,
        filing_id: str,
        section_id: str,
        filer_entity_id: str,  # From Entity Master
        section_text: str,
    ) -> list[dict]:
        """
        Extract events and resolve involved entities.
        """
        events = []
        
        for detector in self.detectors:
            detected = detector.detect(section_text)
            
            for event in detected:
                # Resolve any mentioned entities
                entity_links = []
                
                for entity_mention in event.get("entities", []):
                    result = await self.entity_resolver.resolve_name(
                        name=entity_mention["name"],
                        context=entity_mention.get("context"),
                        min_confidence=0.7,
                    )
                    
                    if result.success:
                        entity_links.append({
                            "entity_id": result.entity.entity_id,
                            "role": entity_mention["role"],
                            "resolution_confidence": result.entity.confidence,
                        })
                        
                        # Push relationship to Entity Master
                        if entity_mention["role"] == "customer":
                            await self.entity_resolver.add_relationship(
                                source_entity_id=filer_entity_id,
                                target_entity_id=result.entity.entity_id,
                                relationship_type=RelationshipType.SUPPLIES_TO.value,
                                evidence={
                                    "source_system": "py_sec_edgar",
                                    "source_id": filing_id,
                                    "source_section": section_id,
                                    "evidence_text": event["evidence_text"],
                                    "confidence": event["confidence"],
                                },
                                metrics={"revenue_pct": event.get("revenue_pct")},
                            )
                
                events.append({
                    "event_type": event["event_type"],
                    "issuer_entity_id": filer_entity_id,
                    "filing_id": filing_id,
                    "section_id": section_id,
                    "confidence": event["confidence"],
                    "significance": event["significance"],
                    "evidence_text": event["evidence_text"],
                    "payload": event.get("payload", {}),
                    "entity_links": entity_links,
                })
        
        return events
```

---

## 4. Handling Entity Merges

Entity Master v2 may merge entities (e.g., when a provisional is identified). py-sec-edgar must handle redirects.

### 4.1 Webhook Handler

```python
# py_sec_edgar/webhooks/entity_master.py

from fastapi import APIRouter, Request
from py_sec_edgar.storage.database import Database


router = APIRouter()


@router.post("/webhooks/entity-master")
async def handle_entity_master_event(request: Request, db: Database):
    """
    Handle Entity Master v2 change events.
    """
    payload = await request.json()
    event_type = payload.get("event_type")
    
    if event_type == "entity.merged":
        from_id = payload["from_entity_id"]
        to_id = payload["to_entity_id"]
        
        # Update all entity_id references
        await db.execute("""
            UPDATE filings 
            SET filer_entity_id = $1 
            WHERE filer_entity_id = $2
        """, to_id, from_id)
        
        await db.execute("""
            UPDATE sigdev_events 
            SET issuer_entity_id = $1 
            WHERE issuer_entity_id = $2
        """, to_id, from_id)
        
        await db.execute("""
            UPDATE entity_mentions 
            SET entity_id = $1 
            WHERE entity_id = $2
        """, to_id, from_id)
        
        await db.execute("""
            UPDATE event_entity_links 
            SET entity_id = $1 
            WHERE entity_id = $2
        """, to_id, from_id)
        
        # Refresh entity cache
        await refresh_entity_cache(to_id, db)
    
    elif event_type == "entity.updated":
        entity_id = payload["entity_id"]
        await refresh_entity_cache(entity_id, db)
    
    return {"status": "ok"}
```

### 4.2 Resolution with Redirect Following

```python
async def get_canonical_entity(
    entity_resolver: EntityResolverPort,
    entity_id: str,
) -> ResolvedEntity:
    """
    Get entity, following any merge redirects.
    """
    entity = await entity_resolver.get_entity(entity_id)
    
    if entity and entity.was_merged and entity.canonical_id != entity_id:
        # Entity was merged, fetch canonical
        entity = await entity_resolver.get_entity(entity.canonical_id)
    
    return entity
```

---

## 5. Configuration

### 5.1 Settings

```python
# py_sec_edgar/config.py

from pydantic_settings import BaseSettings
from typing import Literal


class EntityMasterSettings(BaseSettings):
    """Entity Master v2 integration settings."""
    
    # Connection
    ENTITY_MASTER_URL: str = "https://entity-master.example.com"
    ENTITY_MASTER_API_KEY: str = ""
    
    # Behavior
    ENTITY_MASTER_TIMEOUT: float = 10.0
    ENTITY_MASTER_CREATE_PROVISIONAL: bool = True
    ENTITY_MASTER_MIN_CONFIDENCE: float = 0.7
    
    # Caching
    ENTITY_CACHE_TTL: int = 3600  # 1 hour
    ENTITY_CACHE_MAX_SIZE: int = 10000
    
    # Adapter selection
    ENTITY_RESOLVER_ADAPTER: Literal["remote", "local", "mock"] = "remote"
    
    class Config:
        env_prefix = "PY_SEC_EDGAR_"
```

### 5.2 Dependency Injection

```python
# py_sec_edgar/dependencies.py

from functools import lru_cache
from py_sec_edgar.config import EntityMasterSettings
from py_sec_edgar.ports.entity_resolver import EntityResolverPort
from py_sec_edgar.adapters.entity_resolver.remote import RemoteEntityResolverAdapter
from py_sec_edgar.adapters.entity_resolver.cached import CachedEntityResolverAdapter


@lru_cache()
def get_settings() -> EntityMasterSettings:
    return EntityMasterSettings()


def get_entity_resolver() -> EntityResolverPort:
    settings = get_settings()
    
    if settings.ENTITY_RESOLVER_ADAPTER == "remote":
        adapter = RemoteEntityResolverAdapter(
            base_url=settings.ENTITY_MASTER_URL,
            api_key=settings.ENTITY_MASTER_API_KEY,
            timeout=settings.ENTITY_MASTER_TIMEOUT,
        )
    elif settings.ENTITY_RESOLVER_ADAPTER == "local":
        from py_sec_edgar.adapters.entity_resolver.local import LocalEntityResolverAdapter
        adapter = LocalEntityResolverAdapter()
    else:
        from py_sec_edgar.adapters.entity_resolver.mock import MockEntityResolverAdapter
        adapter = MockEntityResolverAdapter()
    
    # Wrap with caching
    return CachedEntityResolverAdapter(
        inner=adapter,
        ttl=settings.ENTITY_CACHE_TTL,
        max_size=settings.ENTITY_CACHE_MAX_SIZE,
    )
```

---

## 6. Testing

### 6.1 Mock Adapter

```python
# py_sec_edgar/adapters/entity_resolver/mock.py

from py_sec_edgar.ports.entity_resolver import (
    EntityResolverPort,
    ResolutionRequest,
    ResolutionResult,
    ResolvedEntity,
)


class MockEntityResolverAdapter(EntityResolverPort):
    """
    Mock adapter for testing without Entity Master.
    """
    
    def __init__(self):
        self.entities = {}
        self.relationships = []
        self.mentions = []
        
        # Pre-populate with common test entities
        self._add_test_entity("0000320193", "Apple Inc.", "AAPL")
        self._add_test_entity("0001018724", "Amazon.com, Inc.", "AMZN")
        self._add_test_entity("0001652044", "Alphabet Inc.", "GOOGL")
    
    def _add_test_entity(self, cik: str, name: str, ticker: str):
        entity_id = f"TEST{cik}"
        self.entities[cik] = ResolvedEntity(
            entity_id=entity_id,
            primary_name=name,
            cik=cik,
            ticker=ticker,
            entity_type="COMPANY",
            status="ACTIVE",
            confidence=1.0,
        )
        self.entities[ticker] = self.entities[cik]
        self.entities[name.lower()] = self.entities[cik]
    
    async def resolve_cik(self, cik: str) -> ResolutionResult:
        cik = cik.zfill(10)
        if cik in self.entities:
            return ResolutionResult(success=True, entity=self.entities[cik])
        return ResolutionResult(success=False, error=f"CIK {cik} not found")
    
    # ... implement other methods
```

---

## Related Documents

| Document | Description |
|----------|-------------|
| [14_STORAGE_SCHEMA_V2.md](14_STORAGE_SCHEMA_V2.md) | PostgreSQL schema aligned with Entity Master v2 |
| [entity_master_v2/01_CANONICAL_DATA_MODEL.md](entity_master_v2/01_CANONICAL_DATA_MODEL.md) | Entity Master v2 data model |
| [entity_master_v2/02_RESOLUTION_AND_MERGE_WORKFLOWS.md](entity_master_v2/02_RESOLUTION_AND_MERGE_WORKFLOWS.md) | Resolution workflows |
| [entity_master/13_PYSECEDGAR_PORT.md](entity_master/13_PYSECEDGAR_PORT.md) | Original port design |

---

*Document version: 1.0.0*
*Last updated: 2025-01-25*
*Aligned with: Entity Master v2*
