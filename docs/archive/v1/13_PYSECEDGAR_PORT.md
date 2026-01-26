# Entity Master - py-sec-edgar Integration

**EntityResolver Port interface and integration patterns for py-sec-edgar v4.**

---

## Architecture Overview

py-sec-edgar v4 uses a **ports and adapters** (hexagonal) architecture. Entity Master is accessed through a **port** (interface), with adapters providing different implementations:

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                         py-sec-edgar v4 ARCHITECTURE                                 │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────┐    │
│  │                           py-sec-edgar CORE                                  │    │
│  │                                                                              │    │
│  │   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │    │
│  │   │   Filings    │  │   Sections   │  │    SIGDEV    │  │ Relationships │   │    │
│  │   │   Service    │  │   Extractor  │  │   Detector   │  │   Extractor   │   │    │
│  │   └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘   │    │
│  │          │                 │                 │                 │            │    │
│  │          └─────────────────┴────────┬────────┴─────────────────┘            │    │
│  │                                     │                                        │    │
│  │                                     ▼                                        │    │
│  │                         ┌───────────────────────┐                            │    │
│  │                         │   EntityResolver      │  ← PORT (interface)        │    │
│  │                         │   (Port Interface)    │                            │    │
│  │                         └───────────┬───────────┘                            │    │
│  │                                     │                                        │    │
│  └─────────────────────────────────────┼────────────────────────────────────────┘    │
│                                        │                                             │
│                           ┌────────────┼────────────┐                                │
│                           │            │            │                                │
│                           ▼            ▼            ▼                                │
│                    ┌───────────┐ ┌───────────┐ ┌───────────┐                         │
│                    │  Local    │ │  Remote   │ │   Mock    │  ← ADAPTERS            │
│                    │  Adapter  │ │  Adapter  │ │  Adapter  │                         │
│                    └─────┬─────┘ └─────┬─────┘ └───────────┘                         │
│                          │             │                                             │
│                          ▼             ▼                                             │
│                   ┌────────────┐ ┌────────────┐                                      │
│                   │  Entity    │ │  Entity    │                                      │
│                   │  Master    │ │  Master    │                                      │
│                   │  (Library) │ │  (Service) │                                      │
│                   └────────────┘ └────────────┘                                      │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## EntityResolver Port (Interface)

The **port** defines what py-sec-edgar needs from an entity resolution system:

```python
# py_sec_edgar/ports/entity_resolver.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from typing import Optional


class EntityType(Enum):
    """Types of entities that can be resolved."""
    COMPANY = 'COMPANY'
    FUND = 'FUND'
    PERSON = 'PERSON'
    SECURITY = 'SECURITY'
    GOVERNMENT = 'GOVERNMENT'
    UNKNOWN = 'UNKNOWN'


class ResolutionScope(Enum):
    """What level to resolve to."""
    ENTITY = 'entity'      # Issuer/organization
    SECURITY = 'security'  # Financial instrument
    LISTING = 'listing'    # Trading venue


@dataclass(frozen=True)
class ResolvedEntity:
    """A resolved entity with all available identifiers."""
    
    # Canonical IDs
    entity_id: str
    security_id: Optional[str] = None
    listing_id: Optional[str] = None
    
    # Entity details
    name: str
    entity_type: EntityType
    status: str = 'active'
    
    # Standard identifiers
    cik: Optional[str] = None
    lei: Optional[str] = None
    ticker: Optional[str] = None
    isin: Optional[str] = None
    figi: Optional[str] = None
    cusip: Optional[str] = None
    
    # Jurisdiction
    jurisdiction_country: Optional[str] = None
    sic_code: Optional[str] = None
    
    # Resolution metadata
    resolution_confidence: float = 1.0
    resolution_path: Optional[str] = None
    was_merged: bool = False


@dataclass
class ResolutionResult:
    """Full result of a resolution attempt."""
    
    success: bool
    entity: Optional[ResolvedEntity] = None
    
    # If multiple candidates
    candidates: Optional[list[ResolvedEntity]] = None
    
    # Error information
    error: Optional[str] = None
    error_code: Optional[str] = None
    
    # Metadata
    resolution_time_ms: Optional[float] = None
    cache_hit: bool = False


class EntityResolverPort(ABC):
    """
    Port interface for entity resolution.
    
    py-sec-edgar depends on this interface, not on Entity Master directly.
    This allows swapping implementations (local, remote, mock).
    """
    
    # =========================================================================
    # RESOLUTION
    # =========================================================================
    
    @abstractmethod
    async def resolve(
        self,
        identifier: str,
        *,
        scope: ResolutionScope = ResolutionScope.ENTITY,
        as_of_date: Optional[date] = None,
        min_confidence: float = 0.7,
        hints: Optional[dict] = None,
    ) -> ResolutionResult:
        """
        Resolve any identifier to a canonical entity.
        
        Args:
            identifier: CIK, ticker, LEI, ISIN, FIGI, name, etc.
            scope: What level to resolve to
            as_of_date: Point-in-time for historical resolution
            min_confidence: Minimum confidence threshold
            hints: Additional context (entity_type, sic_code, etc.)
        
        Returns:
            ResolutionResult with entity or candidates
        """
        ...
    
    @abstractmethod
    async def resolve_batch(
        self,
        identifiers: list[str],
        **kwargs,
    ) -> dict[str, ResolutionResult]:
        """
        Resolve multiple identifiers efficiently.
        
        Returns:
            Dict mapping input identifier → ResolutionResult
        """
        ...
    
    @abstractmethod
    async def resolve_name(
        self,
        name: str,
        *,
        entity_type: Optional[EntityType] = None,
        context: Optional[dict] = None,
    ) -> ResolutionResult:
        """
        Resolve by name with fuzzy matching.
        
        Args:
            name: Company/entity name
            entity_type: Filter by type
            context: Filing context (filer_cik, co_mentioned, etc.)
        """
        ...
    
    # =========================================================================
    # LOOKUPS
    # =========================================================================
    
    @abstractmethod
    async def get_by_cik(self, cik: str) -> Optional[ResolvedEntity]:
        """Get entity by SEC CIK."""
        ...
    
    @abstractmethod
    async def get_by_ticker(
        self,
        ticker: str,
        mic: Optional[str] = None,
        as_of: Optional[date] = None,
    ) -> Optional[ResolvedEntity]:
        """Get entity by ticker symbol."""
        ...
    
    @abstractmethod
    async def get_identifiers(
        self,
        entity_id: str,
        schemes: Optional[list[str]] = None,
    ) -> dict[str, str]:
        """Get all identifiers for an entity."""
        ...
    
    # =========================================================================
    # RELATIONSHIPS
    # =========================================================================
    
    @abstractmethod
    async def get_parent(self, entity_id: str) -> Optional[ResolvedEntity]:
        """Get parent company in corporate hierarchy."""
        ...
    
    @abstractmethod
    async def get_subsidiaries(
        self,
        entity_id: str,
        include_indirect: bool = False,
    ) -> list[ResolvedEntity]:
        """Get subsidiary companies."""
        ...
    
    @abstractmethod
    async def get_securities(self, entity_id: str) -> list[dict]:
        """Get all securities issued by entity."""
        ...
    
    @abstractmethod
    async def get_listings(
        self,
        security_id: str,
        active_only: bool = True,
    ) -> list[dict]:
        """Get all listings for a security."""
        ...
    
    # =========================================================================
    # STORAGE (for writing extracted data back)
    # =========================================================================
    
    @abstractmethod
    async def store_relationship(
        self,
        source_entity_id: str,
        target_entity_id: str,
        relationship_type: str,
        *,
        evidence: dict,
        metrics: Optional[dict] = None,
        confidence: float = 1.0,
    ) -> str:
        """
        Store a relationship extracted from filings.
        
        Returns:
            Relationship ID
        """
        ...
    
    @abstractmethod
    async def store_mention(
        self,
        entity_id: str,
        *,
        filing_id: str,
        section_id: Optional[str] = None,
        mention_text: str,
        context: Optional[str] = None,
        confidence: float = 1.0,
    ) -> str:
        """
        Store an entity mention from a filing.
        
        Returns:
            Mention ID
        """
        ...
    
    # =========================================================================
    # CHANGES
    # =========================================================================
    
    @abstractmethod
    async def get_changes_since(
        self,
        since: datetime,
        entity_types: Optional[list[EntityType]] = None,
    ) -> list[dict]:
        """Get entity changes since a timestamp."""
        ...
    
    # =========================================================================
    # HEALTH
    # =========================================================================
    
    @abstractmethod
    async def health_check(self) -> dict:
        """Check if the resolver is healthy."""
        ...
```

---

## Adapters

### Local Adapter (Direct Library)

Uses Entity Master as an embedded library:

```python
# py_sec_edgar/adapters/entity_resolver/local.py

from entity_master import EntityMaster
from py_sec_edgar.ports.entity_resolver import (
    EntityResolverPort,
    ResolvedEntity,
    ResolutionResult,
    ResolutionScope,
    EntityType,
)


class LocalEntityResolverAdapter(EntityResolverPort):
    """
    Entity resolver using Entity Master as a local library.
    
    Direct database access, no network overhead.
    Best for: Single-process applications, development.
    """
    
    def __init__(
        self,
        tier: str = 'basic',
        db_path: Optional[str] = None,
        storage_url: Optional[str] = None,
    ):
        self.em = EntityMaster(
            tier=tier,
            db_path=db_path,
            storage_url=storage_url,
        )
    
    async def resolve(
        self,
        identifier: str,
        *,
        scope: ResolutionScope = ResolutionScope.ENTITY,
        as_of_date: Optional[date] = None,
        min_confidence: float = 0.7,
        hints: Optional[dict] = None,
    ) -> ResolutionResult:
        """Resolve using local Entity Master."""
        
        import time
        start = time.monotonic()
        
        try:
            # Call Entity Master's resolve
            result = await self.em.resolve(
                identifier,
                scope=scope.value,
                as_of_date=as_of_date,
                min_confidence=min_confidence,
            )
            
            if result is None:
                return ResolutionResult(
                    success=False,
                    error='Entity not found',
                    error_code='NOT_FOUND',
                    resolution_time_ms=(time.monotonic() - start) * 1000,
                )
            
            # Convert to port's ResolvedEntity
            entity = self._convert_entity(result)
            
            return ResolutionResult(
                success=True,
                entity=entity,
                resolution_time_ms=(time.monotonic() - start) * 1000,
            )
        
        except Exception as e:
            return ResolutionResult(
                success=False,
                error=str(e),
                error_code='RESOLUTION_ERROR',
                resolution_time_ms=(time.monotonic() - start) * 1000,
            )
    
    async def resolve_batch(
        self,
        identifiers: list[str],
        **kwargs,
    ) -> dict[str, ResolutionResult]:
        """Batch resolve using Entity Master."""
        
        results = await self.em.resolve_batch(identifiers, **kwargs)
        
        return {
            ident: self._wrap_result(result)
            for ident, result in results.items()
        }
    
    async def resolve_name(
        self,
        name: str,
        *,
        entity_type: Optional[EntityType] = None,
        context: Optional[dict] = None,
    ) -> ResolutionResult:
        """Fuzzy name resolution."""
        
        results = await self.em.search(
            name,
            entity_type=entity_type.value if entity_type else None,
            limit=5,
        )
        
        if not results:
            return ResolutionResult(success=False, error='No matches found')
        
        if len(results) == 1 or results[0].confidence > 0.9:
            return ResolutionResult(
                success=True,
                entity=self._convert_entity(results[0]),
            )
        
        return ResolutionResult(
            success=False,
            error='Multiple candidates found',
            error_code='AMBIGUOUS',
            candidates=[self._convert_entity(r) for r in results],
        )
    
    async def get_by_cik(self, cik: str) -> Optional[ResolvedEntity]:
        """Direct CIK lookup."""
        result = await self.em.get_by_cik(cik)
        return self._convert_entity(result) if result else None
    
    async def get_by_ticker(
        self,
        ticker: str,
        mic: Optional[str] = None,
        as_of: Optional[date] = None,
    ) -> Optional[ResolvedEntity]:
        """Ticker lookup with optional exchange and date."""
        result = await self.em.get_by_ticker(ticker, mic=mic, as_of_date=as_of)
        return self._convert_entity(result) if result else None
    
    async def get_identifiers(
        self,
        entity_id: str,
        schemes: Optional[list[str]] = None,
    ) -> dict[str, str]:
        """Get all identifiers for an entity."""
        return await self.em.get_identifiers(entity_id, schemes=schemes)
    
    async def get_parent(self, entity_id: str) -> Optional[ResolvedEntity]:
        """Get parent company."""
        result = await self.em.hierarchy.get_parent(entity_id)
        return self._convert_entity(result) if result else None
    
    async def get_subsidiaries(
        self,
        entity_id: str,
        include_indirect: bool = False,
    ) -> list[ResolvedEntity]:
        """Get subsidiaries."""
        results = await self.em.hierarchy.get_subsidiaries(
            entity_id,
            recursive=include_indirect,
        )
        return [self._convert_entity(r) for r in results]
    
    async def get_securities(self, entity_id: str) -> list[dict]:
        """Get securities for entity."""
        return await self.em.get_securities(entity_id)
    
    async def get_listings(
        self,
        security_id: str,
        active_only: bool = True,
    ) -> list[dict]:
        """Get listings for security."""
        return await self.em.get_listings(security_id, active_only=active_only)
    
    async def store_relationship(
        self,
        source_entity_id: str,
        target_entity_id: str,
        relationship_type: str,
        *,
        evidence: dict,
        metrics: Optional[dict] = None,
        confidence: float = 1.0,
    ) -> str:
        """Store extracted relationship."""
        return await self.em.relationships.add(
            source_entity_id=source_entity_id,
            target_entity_id=target_entity_id,
            relationship_type=relationship_type,
            evidence=evidence,
            metrics=metrics or {},
            confidence=confidence,
        )
    
    async def store_mention(
        self,
        entity_id: str,
        *,
        filing_id: str,
        section_id: Optional[str] = None,
        mention_text: str,
        context: Optional[str] = None,
        confidence: float = 1.0,
    ) -> str:
        """Store entity mention."""
        return await self.em.mentions.add(
            entity_id=entity_id,
            source_system='py_sec_edgar',
            source_id=filing_id,
            source_subsection=section_id,
            mention_text=mention_text,
            context=context,
            confidence=confidence,
        )
    
    async def get_changes_since(
        self,
        since: datetime,
        entity_types: Optional[list[EntityType]] = None,
    ) -> list[dict]:
        """Get changes since timestamp."""
        return await self.em.changes.since(
            since,
            entity_types=[t.value for t in entity_types] if entity_types else None,
        )
    
    async def health_check(self) -> dict:
        """Health check."""
        return await self.em.health_check()
    
    def _convert_entity(self, em_entity) -> ResolvedEntity:
        """Convert Entity Master entity to port's ResolvedEntity."""
        return ResolvedEntity(
            entity_id=em_entity.entity_id,
            security_id=getattr(em_entity, 'security_id', None),
            listing_id=getattr(em_entity, 'listing_id', None),
            name=em_entity.primary_name or em_entity.legal_name,
            entity_type=EntityType(em_entity.entity_type),
            status=em_entity.status,
            cik=em_entity.cik,
            lei=em_entity.lei,
            ticker=em_entity.ticker,
            isin=getattr(em_entity, 'isin', None),
            figi=getattr(em_entity, 'figi', None),
            cusip=getattr(em_entity, 'cusip', None),
            jurisdiction_country=em_entity.jurisdiction_country,
            sic_code=em_entity.sic_code,
            resolution_confidence=em_entity.confidence,
            resolution_path=em_entity.resolution_path,
            was_merged=em_entity.was_merged,
        )
```

### Remote Adapter (HTTP Client)

Uses Entity Master as a remote service:

```python
# py_sec_edgar/adapters/entity_resolver/remote.py

import httpx
from py_sec_edgar.ports.entity_resolver import (
    EntityResolverPort,
    ResolvedEntity,
    ResolutionResult,
    ResolutionScope,
    EntityType,
)


class RemoteEntityResolverAdapter(EntityResolverPort):
    """
    Entity resolver using Entity Master as a remote HTTP service.
    
    Best for: Multi-process applications, microservices architecture.
    """
    
    def __init__(
        self,
        base_url: str = 'http://localhost:8080',
        api_key: Optional[str] = None,
        timeout: float = 30.0,
    ):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout,
            headers={'Authorization': f'Bearer {api_key}'} if api_key else {},
        )
    
    async def resolve(
        self,
        identifier: str,
        *,
        scope: ResolutionScope = ResolutionScope.ENTITY,
        as_of_date: Optional[date] = None,
        min_confidence: float = 0.7,
        hints: Optional[dict] = None,
    ) -> ResolutionResult:
        """Resolve via HTTP API."""
        
        params = {
            'identifier': identifier,
            'scope': scope.value,
            'min_confidence': min_confidence,
        }
        
        if as_of_date:
            params['as_of_date'] = as_of_date.isoformat()
        
        if hints:
            params['hints'] = hints
        
        response = await self.client.post('/v1/resolve', json=params)
        
        if response.status_code == 404:
            return ResolutionResult(success=False, error='Not found')
        
        response.raise_for_status()
        data = response.json()
        
        return ResolutionResult(
            success=data['success'],
            entity=ResolvedEntity(**data['entity']) if data.get('entity') else None,
            candidates=[ResolvedEntity(**c) for c in data.get('candidates', [])],
            error=data.get('error'),
            resolution_time_ms=data.get('resolution_time_ms'),
        )
    
    async def resolve_batch(
        self,
        identifiers: list[str],
        **kwargs,
    ) -> dict[str, ResolutionResult]:
        """Batch resolve via HTTP."""
        
        response = await self.client.post(
            '/v1/resolve/batch',
            json={
                'identifiers': identifiers,
                **kwargs,
            },
        )
        response.raise_for_status()
        
        results = {}
        for ident, data in response.json().items():
            results[ident] = ResolutionResult(
                success=data['success'],
                entity=ResolvedEntity(**data['entity']) if data.get('entity') else None,
            )
        
        return results
    
    # ... other methods follow same pattern ...
    
    async def health_check(self) -> dict:
        """Check service health."""
        response = await self.client.get('/health')
        return response.json()
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()
```

### Mock Adapter (Testing)

For unit tests:

```python
# py_sec_edgar/adapters/entity_resolver/mock.py

class MockEntityResolverAdapter(EntityResolverPort):
    """
    Mock resolver for testing.
    
    Pre-loaded with test entities, no external dependencies.
    """
    
    def __init__(self):
        self.entities: dict[str, ResolvedEntity] = {}
        self.relationships: list[dict] = []
        self.mentions: list[dict] = []
        self._load_test_data()
    
    def _load_test_data(self):
        """Load common test entities."""
        
        self.entities['AAPL'] = ResolvedEntity(
            entity_id='test_apple_inc',
            name='Apple Inc',
            entity_type=EntityType.COMPANY,
            cik='0000320193',
            ticker='AAPL',
            lei='HWUPKR0MPOU8FGXBT394',
            isin='US0378331005',
            figi='BBG000B9XRY4',
        )
        
        self.entities['320193'] = self.entities['AAPL']
        self.entities['0000320193'] = self.entities['AAPL']
        
        self.entities['GOOGL'] = ResolvedEntity(
            entity_id='test_alphabet_inc',
            name='Alphabet Inc',
            entity_type=EntityType.COMPANY,
            cik='0001652044',
            ticker='GOOGL',
        )
    
    async def resolve(
        self,
        identifier: str,
        **kwargs,
    ) -> ResolutionResult:
        """Mock resolve."""
        
        entity = self.entities.get(identifier.upper())
        
        if entity:
            return ResolutionResult(success=True, entity=entity)
        
        return ResolutionResult(
            success=False,
            error='Not found (mock)',
            error_code='NOT_FOUND',
        )
    
    # ... simple implementations for testing ...
```

---

## Integration in py-sec-edgar Pipeline

### Configuration

```python
# py_sec_edgar/config.py

from pydantic import BaseSettings


class EntityResolverConfig(BaseSettings):
    """Entity resolver configuration."""
    
    # Which adapter to use
    adapter: str = 'local'  # 'local', 'remote', 'mock'
    
    # Local adapter settings
    tier: str = 'basic'
    db_path: str = '~/.entity_master/entities.db'
    storage_url: str | None = None
    
    # Remote adapter settings
    service_url: str = 'http://localhost:8080'
    api_key: str | None = None
    
    class Config:
        env_prefix = 'ENTITY_RESOLVER_'


def get_entity_resolver(config: EntityResolverConfig) -> EntityResolverPort:
    """Factory function to create resolver adapter."""
    
    if config.adapter == 'local':
        from py_sec_edgar.adapters.entity_resolver.local import LocalEntityResolverAdapter
        return LocalEntityResolverAdapter(
            tier=config.tier,
            db_path=config.db_path,
            storage_url=config.storage_url,
        )
    
    elif config.adapter == 'remote':
        from py_sec_edgar.adapters.entity_resolver.remote import RemoteEntityResolverAdapter
        return RemoteEntityResolverAdapter(
            base_url=config.service_url,
            api_key=config.api_key,
        )
    
    elif config.adapter == 'mock':
        from py_sec_edgar.adapters.entity_resolver.mock import MockEntityResolverAdapter
        return MockEntityResolverAdapter()
    
    else:
        raise ValueError(f"Unknown adapter: {config.adapter}")
```

### Using in Filing Pipeline

```python
# py_sec_edgar/pipelines/filing_processor.py

from py_sec_edgar.ports.entity_resolver import EntityResolverPort, EntityType


class FilingProcessor:
    """Process SEC filings with entity resolution."""
    
    def __init__(self, entity_resolver: EntityResolverPort):
        self.resolver = entity_resolver
    
    async def process_filing(self, filing: Filing) -> ProcessedFiling:
        """Process a single filing."""
        
        # Resolve the filer
        filer_result = await self.resolver.resolve(filing.cik)
        
        if not filer_result.success:
            raise FilingProcessingError(f"Could not resolve filer CIK: {filing.cik}")
        
        filer = filer_result.entity
        
        # Extract sections
        sections = await self.extract_sections(filing)
        
        # Extract entities from sections
        for section in sections:
            entities = await self.extract_entities_from_text(section.content)
            
            for extracted in entities:
                # Resolve extracted entity
                result = await self.resolver.resolve_name(
                    extracted.name,
                    entity_type=EntityType(extracted.type),
                    context={
                        'filer_cik': filer.cik,
                        'filer_sic': filer.sic_code,
                        'section_type': section.type,
                    },
                )
                
                if result.success:
                    # Store mention
                    await self.resolver.store_mention(
                        entity_id=result.entity.entity_id,
                        filing_id=filing.accession_number,
                        section_id=section.section_id,
                        mention_text=extracted.text,
                        context=extracted.context,
                        confidence=result.entity.resolution_confidence,
                    )
                    
                    # If this is a relationship, store it
                    if extracted.relationship_type:
                        await self.resolver.store_relationship(
                            source_entity_id=filer.entity_id,
                            target_entity_id=result.entity.entity_id,
                            relationship_type=extracted.relationship_type,
                            evidence={
                                'filing_id': filing.accession_number,
                                'section_id': section.section_id,
                                'text': extracted.context,
                            },
                            confidence=extracted.confidence,
                        )
        
        return ProcessedFiling(
            filing=filing,
            filer=filer,
            sections=sections,
        )
```

### Using in SIGDEV Event Detection

```python
# py_sec_edgar/pipelines/sigdev_detector.py

class SIGDEVDetector:
    """Detect significant developments from filings."""
    
    def __init__(self, entity_resolver: EntityResolverPort):
        self.resolver = entity_resolver
    
    async def detect_ma_event(
        self,
        filing: Filing,
        section: Section,
    ) -> Optional[SIGDEVEvent]:
        """Detect M&A events."""
        
        # Extract target company name from text
        target_name = self.extract_target_name(section.content)
        
        if not target_name:
            return None
        
        # Resolve target entity
        result = await self.resolver.resolve_name(
            target_name,
            entity_type=EntityType.COMPANY,
            context={
                'filer_cik': filing.cik,
                'event_type': 'MA_ACQUISITION',
            },
        )
        
        target_entity = result.entity if result.success else None
        
        return SIGDEVEvent(
            event_type='MA_ACQUISITION',
            issuer_entity_id=filing.filer_entity_id,
            target_entity_id=target_entity.entity_id if target_entity else None,
            target_name_raw=target_name,
            target_resolved=result.success,
            payload={
                'purchase_price': self.extract_purchase_price(section.content),
                'consideration_type': self.extract_consideration_type(section.content),
            },
        )
```

### Dependency Injection

```python
# py_sec_edgar/app.py

from dependency_injector import containers, providers


class Container(containers.DeclarativeContainer):
    """Dependency injection container."""
    
    config = providers.Configuration()
    
    # Entity resolver (from config)
    entity_resolver = providers.Singleton(
        get_entity_resolver,
        config=config.entity_resolver,
    )
    
    # Filing processor (uses entity resolver)
    filing_processor = providers.Factory(
        FilingProcessor,
        entity_resolver=entity_resolver,
    )
    
    # SIGDEV detector (uses entity resolver)
    sigdev_detector = providers.Factory(
        SIGDEVDetector,
        entity_resolver=entity_resolver,
    )


# Usage
container = Container()
container.config.from_yaml('config.yaml')

async with container.filing_processor() as processor:
    result = await processor.process_filing(filing)
```

---

## API Summary

### Resolution Methods

| Method | Input | Output | Use Case |
|--------|-------|--------|----------|
| `resolve()` | Any identifier | Single entity or candidates | General resolution |
| `resolve_batch()` | List of identifiers | Dict of results | Bulk processing |
| `resolve_name()` | Company name | Single or candidates | Fuzzy matching |
| `get_by_cik()` | CIK | Entity | Direct SEC lookup |
| `get_by_ticker()` | Ticker (+MIC, date) | Entity | Trading lookup |

### Lookup Methods

| Method | Input | Output | Use Case |
|--------|-------|--------|----------|
| `get_identifiers()` | Entity ID | Dict of scheme→value | Get all IDs |
| `get_parent()` | Entity ID | Parent entity | Corporate hierarchy |
| `get_subsidiaries()` | Entity ID | List of entities | Corporate hierarchy |
| `get_securities()` | Entity ID | List of securities | Issuer analysis |
| `get_listings()` | Security ID | List of listings | Trading venues |

### Write Methods

| Method | Input | Output | Use Case |
|--------|-------|--------|----------|
| `store_relationship()` | Source, target, type, evidence | Relationship ID | Store extracted relationships |
| `store_mention()` | Entity, filing, text | Mention ID | Track entity mentions |

---

## Configuration Examples

### Development (Local, Basic)

```yaml
# config.yaml
entity_resolver:
  adapter: local
  tier: basic
  db_path: ~/.entity_master/dev.db
```

### Production (Local, Advanced)

```yaml
# config.yaml
entity_resolver:
  adapter: local
  tier: advanced
  storage_url: postgresql://user:pass@localhost:5432/entity_master
```

### Production (Remote Service)

```yaml
# config.yaml
entity_resolver:
  adapter: remote
  service_url: https://entity-master.internal.company.com
  api_key: ${ENTITY_MASTER_API_KEY}
```

### Testing

```yaml
# config.yaml
entity_resolver:
  adapter: mock
```

---

## Migration from v3

If py-sec-edgar v3 had direct Entity Master calls, wrap them:

```python
# Before (v3): Direct Entity Master calls
from entity_master import EntityMaster
em = EntityMaster()
entity = em.resolve("AAPL")

# After (v4): Through port interface
from py_sec_edgar.ports.entity_resolver import EntityResolverPort

async def process(resolver: EntityResolverPort):
    result = await resolver.resolve("AAPL")
    if result.success:
        entity = result.entity
```

Benefits:
- Swappable implementations (local, remote, mock)
- Easier testing (inject mock adapter)
- Clear contract between py-sec-edgar and Entity Master
