# Entity Master v2 - py-sec-edgar Integration Port

**How to integrate Entity Master v2 into the existing py-sec-edgar codebase**

---

## Current State Analysis

### Existing EntityResolver Location

```
py_sec_edgar/
├── entity_resolver.py          # Existing resolver (to be replaced)
├── models/
│   └── company.py              # Company dataclass
├── data/
│   └── company_tickers.json    # SEC ticker mapping
└── ...
```

### Current Interface (Simplified)

```python
# Existing interface (simplified)
class EntityResolver:
    def resolve(self, query: str) -> Optional[Company]:
        """Resolve query to company."""
        ...
    
    def get_by_cik(self, cik: str) -> Optional[Company]:
        """Get company by CIK."""
        ...
```

---

## New Module Structure

```
py_sec_edgar/
├── entity_master/                    # NEW: Entity Master v2 module
│   ├── __init__.py                   # Public API exports
│   ├── core/
│   │   ├── __init__.py
│   │   ├── types.py                  # Entity, Security, Listing dataclasses
│   │   ├── identifiers.py            # Identifier detection and validation
│   │   └── normalization.py          # Name normalization utilities
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── base.py                   # Abstract storage interface
│   │   ├── sqlite_store.py           # SQLite adapter (Tier 1)
│   │   ├── duckdb_store.py           # DuckDB adapter (Tier 2)
│   │   └── postgres_store.py         # PostgreSQL adapter (Tier 3)
│   ├── resolution/
│   │   ├── __init__.py
│   │   ├── resolver.py               # Main EntityResolver class
│   │   ├── strategies.py             # Resolution strategies
│   │   └── merge_handler.py          # Merge chain following
│   ├── mentions/
│   │   ├── __init__.py
│   │   ├── extractor.py              # Mention extraction from text
│   │   ├── normalizer.py             # Mention normalization
│   │   └── provisional.py            # Provisional entity handling
│   ├── crosswalks/
│   │   ├── __init__.py
│   │   ├── loader.py                 # Vendor data loading
│   │   └── conflict.py               # Conflict handling
│   ├── migrations/
│   │   ├── 001_initial_schema.sql
│   │   ├── 002_add_crosswalks.sql
│   │   └── ...
│   └── cli.py                        # CLI commands
├── entity_resolver.py                # DEPRECATED: Thin wrapper for backward compat
└── ...
```

---

## Core Types

### [entity_master/core/types.py](entity_master/core/types.py)

```python
"""Core domain types for Entity Master v2."""

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Optional, List, Dict


class EntityStatus(Enum):
    ACTIVE = 'active'
    PROVISIONAL = 'provisional'
    MERGED = 'merged'
    INACTIVE = 'inactive'


class EntityType(Enum):
    ORGANIZATION = 'organization'
    PERSON = 'person'
    GOVERNMENT = 'government'
    FUND = 'fund'


class SecurityType(Enum):
    COMMON_STOCK = 'common_stock'
    PREFERRED_STOCK = 'preferred_stock'
    BOND = 'bond'
    ETF = 'etf'
    MUTUAL_FUND = 'mutual_fund'
    OPTION = 'option'
    WARRANT = 'warrant'
    ADR = 'adr'
    OTHER = 'other'


class ListingStatus(Enum):
    ACTIVE = 'active'
    DELISTED = 'delisted'
    SUSPENDED = 'suspended'


# =============================================================================
# Core Domain Objects
# =============================================================================

@dataclass
class Entity:
    """
    A legal entity that can issue securities and/or file with the SEC.
    
    Rule 1: Entity ≠ Security ≠ Listing
    - Entity is the issuer (company, fund, person)
    - Entity can issue multiple Securities
    - Entity can have multiple Identifiers (CIK, LEI, EIN, DUNS)
    """
    entity_id: str
    primary_name: str
    entity_type: EntityType = EntityType.ORGANIZATION
    status: EntityStatus = EntityStatus.ACTIVE
    
    # Legal details
    jurisdiction: Optional[str] = None
    incorporation_date: Optional[date] = None
    sic_code: Optional[str] = None
    
    # Identifiers (inline for convenience)
    cik: Optional[str] = None
    lei: Optional[str] = None
    ein: Optional[str] = None
    
    # Aliases
    aliases: List[str] = field(default_factory=list)
    
    # Metadata
    first_seen_at: Optional[datetime] = None
    last_seen_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # Resolution metadata
    canonical_entity_id: Optional[str] = None  # If this was resolved via merge
    
    def __post_init__(self):
        if self.canonical_entity_id is None:
            self.canonical_entity_id = self.entity_id


@dataclass
class Security:
    """
    A financial instrument issued by an Entity.
    
    - Security is what you're investing in (the claim/instrument)
    - Security can trade on multiple Listings
    - Security has ISIN, CUSIP, FIGI identifiers
    """
    security_id: str
    issuer_entity_id: str
    name: str
    security_type: SecurityType = SecurityType.COMMON_STOCK
    asset_class: str = 'equity'
    status: str = 'active'
    
    # Identifiers
    isin: Optional[str] = None
    cusip: Optional[str] = None
    figi: Optional[str] = None
    composite_figi: Optional[str] = None
    
    # Metadata
    issued_date: Optional[date] = None
    maturity_date: Optional[date] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class Listing:
    """
    A venue-specific trading identity for a Security.
    
    - Listing is where you trade (exchange + ticker)
    - Ticker can be reused over time (temporal validity)
    - Listing has ticker, MIC, RIC identifiers
    """
    listing_id: str
    security_id: str
    mic: str  # Market Identifier Code (e.g., XNYS, XNAS)
    ticker: str
    currency: str = 'USD'
    status: ListingStatus = ListingStatus.ACTIVE
    
    # Temporal validity
    valid_from: Optional[date] = None
    valid_to: Optional[date] = None
    
    # Identifiers
    exchange_figi: Optional[str] = None
    ric: Optional[str] = None  # Reuters Instrument Code
    
    # Metadata
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class Identifier:
    """A standard identifier attached to Entity/Security/Listing."""
    identifier_id: str
    scheme: str  # 'cik', 'lei', 'isin', 'cusip', 'figi', 'ticker'
    value: str
    
    # Scope (only one will be set)
    entity_id: Optional[str] = None
    security_id: Optional[str] = None
    listing_id: Optional[str] = None
    
    # Validity
    valid_from: Optional[date] = None
    valid_to: Optional[date] = None
    
    # Provenance
    source: Optional[str] = None
    first_seen_at: Optional[datetime] = None


@dataclass
class Crosswalk:
    """A vendor-internal ID mapping."""
    crosswalk_id: str
    vendor: str  # 'factset', 'bloomberg', 'refinitiv', 'sp'
    vendor_id_type: str  # 'entity_id', 'security_id', 'gvkey', 'permid'
    vendor_id_value: str
    
    # Scope (only one will be set)
    entity_id: Optional[str] = None
    security_id: Optional[str] = None
    listing_id: Optional[str] = None
    
    # Provenance
    mapping_source: str = 'vendor_file'
    mapping_method: str = 'exact'
    confidence: float = 0.95


# =============================================================================
# Resolution Results
# =============================================================================

@dataclass
class ResolutionResult:
    """Result of resolving an identifier or query."""
    success: bool
    
    # Resolved objects (only relevant ones populated)
    entity: Optional[Entity] = None
    security: Optional[Security] = None
    listing: Optional[Listing] = None
    
    # Resolution metadata
    resolved_via: Optional[str] = None  # 'cik', 'isin', 'ticker', 'name', etc.
    confidence: float = 1.0
    followed_merge: bool = False
    
    # Multiple candidates (if ambiguous)
    candidates: List[Entity] = field(default_factory=list)
    
    # Error info
    error: Optional[str] = None
    
    @property
    def is_ambiguous(self) -> bool:
        return len(self.candidates) > 1


@dataclass 
class BatchResolutionResult:
    """Result of batch resolution."""
    total: int
    resolved: int
    failed: int
    results: Dict[str, ResolutionResult] = field(default_factory=dict)
```

---

## Storage Interface

### [entity_master/storage/base.py](entity_master/storage/base.py)

```python
"""Abstract storage interface for Entity Master."""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, AsyncGenerator
from datetime import date

from ..core.types import (
    Entity, Security, Listing, Identifier, Crosswalk,
    ResolutionResult
)


class EntityStore(ABC):
    """
    Abstract interface for entity storage.
    
    Implementations:
    - SQLiteEntityStore (Tier 1)
    - DuckDBEntityStore (Tier 2)
    - PostgresEntityStore (Tier 3)
    """
    
    # =========================================================================
    # Lifecycle
    # =========================================================================
    
    @abstractmethod
    async def connect(self) -> None:
        """Establish connection."""
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close connection."""
        pass
    
    @abstractmethod
    async def initialize_schema(self) -> None:
        """Create/update schema."""
        pass
    
    # =========================================================================
    # Entity CRUD
    # =========================================================================
    
    @abstractmethod
    async def get_entity(
        self,
        entity_id: str,
        follow_merges: bool = True,
    ) -> Optional[Entity]:
        """Get entity by ID, optionally following merge chains."""
        pass
    
    @abstractmethod
    async def create_entity(self, entity: Entity) -> str:
        """Create new entity, returns entity_id."""
        pass
    
    @abstractmethod
    async def update_entity(self, entity: Entity) -> None:
        """Update existing entity."""
        pass
    
    # =========================================================================
    # Identifier Operations
    # =========================================================================
    
    @abstractmethod
    async def get_by_identifier(
        self,
        scheme: str,
        value: str,
        as_of_date: Optional[date] = None,
    ) -> Optional[ResolutionResult]:
        """Resolve an identifier to entity/security/listing."""
        pass
    
    @abstractmethod
    async def add_identifier(self, identifier: Identifier) -> str:
        """Add identifier to entity/security/listing."""
        pass
    
    # =========================================================================
    # Alias Operations
    # =========================================================================
    
    @abstractmethod
    async def search_by_name(
        self,
        name: str,
        limit: int = 10,
        fuzzy: bool = True,
    ) -> List[Entity]:
        """Search entities by name."""
        pass
    
    @abstractmethod
    async def add_alias(
        self,
        entity_id: str,
        alias: str,
        alias_type: str = 'alternate',
    ) -> None:
        """Add alias to entity."""
        pass
    
    # =========================================================================
    # Merge Operations
    # =========================================================================
    
    @abstractmethod
    async def merge_entities(
        self,
        from_entity_id: str,
        to_entity_id: str,
        merge_type: str,
        reason: str,
    ) -> str:
        """Merge two entities, returns merge_id."""
        pass
    
    @abstractmethod
    async def get_canonical_entity_id(self, entity_id: str) -> str:
        """Follow merge chain to canonical entity."""
        pass
    
    # =========================================================================
    # Crosswalk Operations
    # =========================================================================
    
    @abstractmethod
    async def get_by_vendor_id(
        self,
        vendor: str,
        vendor_id_type: str,
        vendor_id_value: str,
    ) -> Optional[ResolutionResult]:
        """Resolve vendor ID to canonical record."""
        pass
    
    @abstractmethod
    async def add_crosswalk(self, crosswalk: Crosswalk) -> str:
        """Add vendor ID mapping."""
        pass
    
    # =========================================================================
    # Bulk Operations
    # =========================================================================
    
    @abstractmethod
    async def bulk_get_entities(
        self,
        entity_ids: List[str],
    ) -> Dict[str, Entity]:
        """Get multiple entities by ID."""
        pass
    
    @abstractmethod
    async def stream_all_entities(
        self,
        status: Optional[str] = None,
    ) -> AsyncGenerator[Entity, None]:
        """Stream all entities for export/sync."""
        pass


class SyncEntityStore(ABC):
    """
    Synchronous version of EntityStore for simpler usage.
    
    Use this for CLI tools and synchronous codebases.
    """
    
    @abstractmethod
    def get_entity(
        self,
        entity_id: str,
        follow_merges: bool = True,
    ) -> Optional[Entity]:
        pass
    
    @abstractmethod
    def create_entity(self, entity: Entity) -> str:
        pass
    
    @abstractmethod
    def get_by_identifier(
        self,
        scheme: str,
        value: str,
        as_of_date: Optional[date] = None,
    ) -> Optional[ResolutionResult]:
        pass
    
    @abstractmethod
    def search_by_name(
        self,
        name: str,
        limit: int = 10,
        fuzzy: bool = True,
    ) -> List[Entity]:
        pass
    
    @abstractmethod
    def merge_entities(
        self,
        from_entity_id: str,
        to_entity_id: str,
        merge_type: str,
        reason: str,
    ) -> str:
        pass
```

---

## Main Resolver Class

### [entity_master/resolution/resolver.py](entity_master/resolution/resolver.py)

```python
"""
Main EntityResolver class - the public API for py-sec-edgar.

This replaces the old entity_resolver.py with a unified interface
that supports all identifier types and resolution strategies.
"""

from typing import Optional, List, Union, Dict
from datetime import date
import logging

from ..core.types import (
    Entity, Security, Listing,
    ResolutionResult, BatchResolutionResult
)
from ..core.identifiers import detect_identifier_type, normalize_identifier
from ..core.normalization import normalize_company_name
from ..storage.base import EntityStore, SyncEntityStore


logger = logging.getLogger(__name__)


class EntityResolver:
    """
    Unified entity resolution for py-sec-edgar.
    
    Usage:
        resolver = EntityResolver.from_sqlite("entity_master.db")
        
        # Resolve by identifier
        result = resolver.resolve("320193")  # CIK
        result = resolver.resolve("US0378331005")  # ISIN
        result = resolver.resolve("AAPL")  # Ticker
        
        # Resolve by name
        result = resolver.resolve("Apple Inc")  # Name search
        
        # Get entity directly
        entity = resolver.get_entity_by_cik("320193")
        entity = resolver.get_entity_by_lei("HWUPKR0MPOU8FGXBT394")
        
        # Search
        entities = resolver.search("Apple", limit=10)
    
    Options:
        as_of_date: Resolve identifiers as of a specific date
        follow_merges: Follow merge chains to canonical entity
        include_provisional: Include provisional entities in results
    """
    
    def __init__(
        self,
        store: Union[EntityStore, SyncEntityStore],
        async_mode: bool = False,
    ):
        self.store = store
        self.async_mode = async_mode
        
        # Default options
        self.default_follow_merges = True
        self.default_include_provisional = True
    
    # =========================================================================
    # Factory Methods
    # =========================================================================
    
    @classmethod
    def from_sqlite(
        cls,
        db_path: str = "entity_master.db",
    ) -> 'EntityResolver':
        """Create resolver with SQLite backend."""
        from ..storage.sqlite_store import SQLiteEntityStore
        
        store = SQLiteEntityStore(db_path)
        return cls(store, async_mode=False)
    
    @classmethod
    def from_duckdb(
        cls,
        db_path: str = "entity_master.duckdb",
    ) -> 'EntityResolver':
        """Create resolver with DuckDB backend."""
        from ..storage.duckdb_store import DuckDBEntityStore
        
        store = DuckDBEntityStore(db_path)
        return cls(store, async_mode=False)
    
    @classmethod
    async def from_postgres(
        cls,
        dsn: str,
    ) -> 'EntityResolver':
        """Create resolver with PostgreSQL backend."""
        from ..storage.postgres_store import PostgresEntityStore
        
        store = PostgresEntityStore(dsn)
        await store.connect()
        return cls(store, async_mode=True)
    
    # =========================================================================
    # Main Resolution API
    # =========================================================================
    
    def resolve(
        self,
        query: str,
        as_of_date: Optional[date] = None,
        follow_merges: Optional[bool] = None,
    ) -> ResolutionResult:
        """
        Resolve any query to entity/security/listing.
        
        Automatically detects query type:
        - CIK: 10-digit number or "320193"
        - LEI: 20-char alphanumeric
        - ISIN: 12-char starting with country code
        - CUSIP: 9-char alphanumeric
        - FIGI: 12-char starting with "BBG"
        - Ticker: Short uppercase string
        - Name: Everything else (fuzzy search)
        
        Args:
            query: The identifier or name to resolve
            as_of_date: Resolve as of this date (for tickers)
            follow_merges: Follow merge chains (default True)
        
        Returns:
            ResolutionResult with entity/security/listing
        """
        if follow_merges is None:
            follow_merges = self.default_follow_merges
        
        # Detect identifier type
        id_info = detect_identifier_type(query)
        
        if id_info['type'] != 'unknown':
            # Known identifier type - resolve by scheme
            return self._resolve_identifier(
                scheme=id_info['type'],
                value=id_info['normalized'],
                as_of_date=as_of_date,
                follow_merges=follow_merges,
            )
        else:
            # Unknown type - try name search
            return self._resolve_by_name(query, follow_merges)
    
    def _resolve_identifier(
        self,
        scheme: str,
        value: str,
        as_of_date: Optional[date],
        follow_merges: bool,
    ) -> ResolutionResult:
        """Resolve known identifier type."""
        
        result = self.store.get_by_identifier(
            scheme=scheme,
            value=value,
            as_of_date=as_of_date,
        )
        
        if not result:
            return ResolutionResult(
                success=False,
                error=f"No match for {scheme}={value}",
            )
        
        # Follow merges if requested
        if follow_merges and result.entity:
            canonical_id = self.store.get_canonical_entity_id(result.entity.entity_id)
            if canonical_id != result.entity.entity_id:
                result.entity = self.store.get_entity(canonical_id, follow_merges=False)
                result.followed_merge = True
        
        return result
    
    def _resolve_by_name(
        self,
        name: str,
        follow_merges: bool,
    ) -> ResolutionResult:
        """Resolve by company name (fuzzy search)."""
        
        entities = self.store.search_by_name(name, limit=5, fuzzy=True)
        
        if not entities:
            return ResolutionResult(
                success=False,
                error=f"No match for name '{name}'",
            )
        
        if len(entities) == 1:
            return ResolutionResult(
                success=True,
                entity=entities[0],
                resolved_via='name',
                confidence=0.85,  # Name matches have lower confidence
            )
        
        # Multiple candidates - return ambiguous result
        return ResolutionResult(
            success=True,  # Technically successful but ambiguous
            entity=entities[0],  # Return best match
            candidates=entities,
            resolved_via='name',
            confidence=0.70,
        )
    
    # =========================================================================
    # Direct Accessors
    # =========================================================================
    
    def get_entity(
        self,
        entity_id: str,
        follow_merges: bool = True,
    ) -> Optional[Entity]:
        """Get entity by ID."""
        return self.store.get_entity(entity_id, follow_merges=follow_merges)
    
    def get_entity_by_cik(
        self,
        cik: str,
        follow_merges: bool = True,
    ) -> Optional[Entity]:
        """Get entity by CIK."""
        cik_normalized = cik.zfill(10)
        result = self.store.get_by_identifier('cik', cik_normalized)
        
        if result and result.entity:
            if follow_merges:
                canonical_id = self.store.get_canonical_entity_id(result.entity.entity_id)
                return self.store.get_entity(canonical_id, follow_merges=False)
            return result.entity
        
        return None
    
    def get_entity_by_lei(
        self,
        lei: str,
        follow_merges: bool = True,
    ) -> Optional[Entity]:
        """Get entity by LEI."""
        result = self.store.get_by_identifier('lei', lei.upper())
        
        if result and result.entity:
            if follow_merges:
                canonical_id = self.store.get_canonical_entity_id(result.entity.entity_id)
                return self.store.get_entity(canonical_id, follow_merges=False)
            return result.entity
        
        return None
    
    def get_security_by_isin(
        self,
        isin: str,
    ) -> Optional[Security]:
        """Get security by ISIN."""
        result = self.store.get_by_identifier('isin', isin.upper())
        return result.security if result else None
    
    def get_listing_by_ticker(
        self,
        ticker: str,
        mic: Optional[str] = None,
        as_of_date: Optional[date] = None,
    ) -> Optional[Listing]:
        """
        Get listing by ticker symbol.
        
        Args:
            ticker: Ticker symbol (e.g., "AAPL")
            mic: Market Identifier Code (e.g., "XNAS" for NASDAQ)
            as_of_date: Get listing as of date (for historical lookups)
        """
        # TODO: Implement MIC filtering
        result = self.store.get_by_identifier(
            'ticker',
            ticker.upper(),
            as_of_date=as_of_date,
        )
        return result.listing if result else None
    
    # =========================================================================
    # Search
    # =========================================================================
    
    def search(
        self,
        query: str,
        limit: int = 10,
        fuzzy: bool = True,
        status: Optional[str] = None,
    ) -> List[Entity]:
        """
        Search entities by name.
        
        Args:
            query: Search query
            limit: Max results
            fuzzy: Enable fuzzy matching
            status: Filter by status ('active', 'provisional', etc.)
        """
        entities = self.store.search_by_name(query, limit=limit, fuzzy=fuzzy)
        
        if status:
            entities = [e for e in entities if e.status.value == status]
        
        return entities
    
    # =========================================================================
    # Batch Operations
    # =========================================================================
    
    def resolve_batch(
        self,
        queries: List[str],
        as_of_date: Optional[date] = None,
    ) -> BatchResolutionResult:
        """
        Resolve multiple queries in batch.
        
        More efficient than calling resolve() in a loop.
        """
        results = {}
        resolved = 0
        failed = 0
        
        for query in queries:
            result = self.resolve(query, as_of_date=as_of_date)
            results[query] = result
            
            if result.success:
                resolved += 1
            else:
                failed += 1
        
        return BatchResolutionResult(
            total=len(queries),
            resolved=resolved,
            failed=failed,
            results=results,
        )
    
    def get_entities_batch(
        self,
        entity_ids: List[str],
    ) -> Dict[str, Entity]:
        """Get multiple entities by ID."""
        return self.store.bulk_get_entities(entity_ids)
    
    # =========================================================================
    # Vendor Crosswalk Resolution
    # =========================================================================
    
    def resolve_vendor_id(
        self,
        vendor: str,
        vendor_id_type: str,
        vendor_id_value: str,
    ) -> Optional[Entity]:
        """
        Resolve a vendor ID to entity.
        
        Args:
            vendor: 'factset', 'bloomberg', 'refinitiv', 'sp'
            vendor_id_type: 'entity_id', 'gvkey', 'permid', etc.
            vendor_id_value: The vendor's ID value
        """
        result = self.store.get_by_vendor_id(vendor, vendor_id_type, vendor_id_value)
        return result.entity if result else None
    
    # =========================================================================
    # Merge Operations
    # =========================================================================
    
    def merge_entities(
        self,
        from_entity_id: str,
        to_entity_id: str,
        merge_type: str = 'duplicate',
        reason: str = 'Manual merge',
    ) -> str:
        """
        Merge two entities.
        
        Args:
            from_entity_id: Entity to merge (will be marked 'merged')
            to_entity_id: Entity to merge into (canonical)
            merge_type: 'duplicate', 'acquisition', 'rename'
            reason: Description of why merged
        
        Returns:
            merge_id
        """
        return self.store.merge_entities(
            from_entity_id=from_entity_id,
            to_entity_id=to_entity_id,
            merge_type=merge_type,
            reason=reason,
        )
```

---

## Backward Compatibility Wrapper

### [entity_resolver.py](entity_resolver.py) (Updated)

```python
"""
DEPRECATED: Use py_sec_edgar.entity_master instead.

This module provides backward compatibility with the old EntityResolver API.
New code should import from py_sec_edgar.entity_master directly.
"""

import warnings
from typing import Optional, List

from py_sec_edgar.entity_master import EntityResolver as NewEntityResolver
from py_sec_edgar.entity_master.core.types import Entity


# Emit deprecation warning on import
warnings.warn(
    "py_sec_edgar.entity_resolver is deprecated. "
    "Use py_sec_edgar.entity_master.EntityResolver instead.",
    DeprecationWarning,
    stacklevel=2
)


class EntityResolver:
    """
    DEPRECATED: Backward-compatible wrapper for old API.
    
    Use py_sec_edgar.entity_master.EntityResolver instead.
    """
    
    def __init__(self, db_path: str = "entity_master.db"):
        warnings.warn(
            "EntityResolver is deprecated. Use entity_master.EntityResolver.from_sqlite() instead.",
            DeprecationWarning,
            stacklevel=2
        )
        self._resolver = NewEntityResolver.from_sqlite(db_path)
    
    def resolve(self, query: str) -> Optional['Company']:
        """
        DEPRECATED: Resolve query to Company.
        
        Returns old Company dataclass for compatibility.
        """
        result = self._resolver.resolve(query)
        
        if result.success and result.entity:
            return _entity_to_company(result.entity)
        
        return None
    
    def get_by_cik(self, cik: str) -> Optional['Company']:
        """DEPRECATED: Get company by CIK."""
        entity = self._resolver.get_entity_by_cik(cik)
        return _entity_to_company(entity) if entity else None
    
    def search(self, query: str, limit: int = 10) -> List['Company']:
        """DEPRECATED: Search companies by name."""
        entities = self._resolver.search(query, limit=limit)
        return [_entity_to_company(e) for e in entities]


# Old Company dataclass for compatibility
from dataclasses import dataclass

@dataclass
class Company:
    """DEPRECATED: Use Entity from entity_master.core.types instead."""
    cik: str
    name: str
    ticker: Optional[str] = None
    exchange: Optional[str] = None
    sic: Optional[str] = None


def _entity_to_company(entity: Entity) -> Company:
    """Convert new Entity to old Company for backward compatibility."""
    return Company(
        cik=entity.cik or '',
        name=entity.primary_name,
        ticker=None,  # Would need to resolve through listing
        exchange=None,
        sic=entity.sic_code,
    )
```

---

## CLI Integration

### [entity_master/cli.py](entity_master/cli.py)

```python
"""CLI commands for Entity Master."""

import click
from typing import Optional


@click.group()
def entity_master():
    """Entity Master v2 commands."""
    pass


@entity_master.command()
@click.argument('query')
@click.option('--as-of', help='Resolve as of date (YYYY-MM-DD)')
@click.option('--db', default='entity_master.db', help='Database path')
@click.option('--format', type=click.Choice(['json', 'table']), default='table')
def resolve(query: str, as_of: Optional[str], db: str, format: str):
    """Resolve an identifier or name to entity."""
    from .resolution.resolver import EntityResolver
    from datetime import datetime
    
    resolver = EntityResolver.from_sqlite(db)
    
    as_of_date = None
    if as_of:
        as_of_date = datetime.strptime(as_of, '%Y-%m-%d').date()
    
    result = resolver.resolve(query, as_of_date=as_of_date)
    
    if format == 'json':
        import json
        click.echo(json.dumps(_result_to_dict(result), indent=2))
    else:
        _print_result_table(result)


@entity_master.command()
@click.argument('query')
@click.option('--limit', default=10, help='Max results')
@click.option('--db', default='entity_master.db', help='Database path')
def search(query: str, limit: int, db: str):
    """Search entities by name."""
    from .resolution.resolver import EntityResolver
    
    resolver = EntityResolver.from_sqlite(db)
    entities = resolver.search(query, limit=limit)
    
    click.echo(f"Found {len(entities)} results:\n")
    
    for e in entities:
        click.echo(f"  {e.entity_id[:8]}  {e.primary_name}")
        if e.cik:
            click.echo(f"            CIK: {e.cik}")
        click.echo()


@entity_master.command()
@click.argument('from_entity_id')
@click.argument('to_entity_id')
@click.option('--reason', required=True, help='Merge reason')
@click.option('--db', default='entity_master.db', help='Database path')
def merge(from_entity_id: str, to_entity_id: str, reason: str, db: str):
    """Merge two entities."""
    from .resolution.resolver import EntityResolver
    
    resolver = EntityResolver.from_sqlite(db)
    
    # Confirm merge
    from_entity = resolver.get_entity(from_entity_id)
    to_entity = resolver.get_entity(to_entity_id)
    
    if not from_entity or not to_entity:
        click.echo("Error: One or both entities not found", err=True)
        return
    
    click.echo(f"Merging:")
    click.echo(f"  FROM: {from_entity.primary_name} ({from_entity_id})")
    click.echo(f"  INTO: {to_entity.primary_name} ({to_entity_id})")
    click.echo(f"  Reason: {reason}")
    
    if not click.confirm("Proceed?"):
        return
    
    merge_id = resolver.merge_entities(
        from_entity_id=from_entity_id,
        to_entity_id=to_entity_id,
        reason=reason,
    )
    
    click.echo(f"✓ Merged successfully. Merge ID: {merge_id}")


@entity_master.command()
@click.option('--db', default='entity_master.db', help='Database path')
def stats(db: str):
    """Show database statistics."""
    from .resolution.resolver import EntityResolver
    
    resolver = EntityResolver.from_sqlite(db)
    
    # Get counts
    click.echo("Entity Master Statistics:")
    click.echo("=" * 40)
    # TODO: Implement stats queries
    click.echo("  Entities:      ???")
    click.echo("  Securities:    ???")
    click.echo("  Listings:      ???")
    click.echo("  Identifiers:   ???")
    click.echo("  Crosswalks:    ???")


def _result_to_dict(result) -> dict:
    """Convert ResolutionResult to dict for JSON output."""
    d = {
        'success': result.success,
        'resolved_via': result.resolved_via,
        'confidence': result.confidence,
        'followed_merge': result.followed_merge,
    }
    
    if result.entity:
        d['entity'] = {
            'entity_id': result.entity.entity_id,
            'primary_name': result.entity.primary_name,
            'cik': result.entity.cik,
            'lei': result.entity.lei,
            'status': result.entity.status.value,
        }
    
    if result.error:
        d['error'] = result.error
    
    return d


def _print_result_table(result):
    """Print ResolutionResult as table."""
    if not result.success:
        click.echo(f"❌ Resolution failed: {result.error}")
        return
    
    click.echo("✓ Resolution successful")
    click.echo()
    
    if result.entity:
        click.echo("Entity:")
        click.echo(f"  ID:     {result.entity.entity_id}")
        click.echo(f"  Name:   {result.entity.primary_name}")
        click.echo(f"  Status: {result.entity.status.value}")
        if result.entity.cik:
            click.echo(f"  CIK:    {result.entity.cik}")
        if result.entity.lei:
            click.echo(f"  LEI:    {result.entity.lei}")
    
    click.echo()
    click.echo(f"Resolved via: {result.resolved_via}")
    click.echo(f"Confidence:   {result.confidence:.2f}")
    
    if result.followed_merge:
        click.echo("(Followed merge chain)")
```

---

## Integration with Existing Codebase

### Step 1: Add to pyproject.toml

```toml
[project.optional-dependencies]
entity-master = [
    "ulid-py>=1.1.0",
]

[project.scripts]
pse-entity = "py_sec_edgar.entity_master.cli:entity_master"
```

### Step 2: Update imports in existing code

```python
# Before (deprecated)
from py_sec_edgar.entity_resolver import EntityResolver

# After
from py_sec_edgar.entity_master import EntityResolver

# Or use the factory method
resolver = EntityResolver.from_sqlite("entity_master.db")
```

### Step 3: Migration script for existing data

```python
# scripts/migrate_to_entity_master_v2.py

import sqlite3
from py_sec_edgar.entity_master import EntityResolver
from py_sec_edgar.entity_master.core.types import Entity


def migrate_old_companies(old_db: str, new_db: str):
    """Migrate old company data to new Entity Master schema."""
    
    old_conn = sqlite3.connect(old_db)
    old_conn.row_factory = sqlite3.Row
    
    resolver = EntityResolver.from_sqlite(new_db)
    
    # Read old companies
    rows = old_conn.execute("SELECT * FROM companies").fetchall()
    
    for row in rows:
        entity = Entity(
            entity_id=generate_ulid(),
            primary_name=row['name'],
            cik=row['cik'],
            # Map other fields...
        )
        
        resolver.store.create_entity(entity)
        
        # Add CIK identifier
        if row['cik']:
            resolver.store.add_identifier(Identifier(
                identifier_id=generate_ulid(),
                scheme='cik',
                value=row['cik'].zfill(10),
                entity_id=entity.entity_id,
            ))
    
    print(f"Migrated {len(rows)} companies")
```

---

## Next Document

→ [07_FEEDSPINE_PIPELINE.md](07_FEEDSPINE_PIPELINE.md) - Bronze/silver/gold reference data layers
