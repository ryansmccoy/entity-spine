# EntitySpine Protocols and Interfaces (v2.2)

**Status**: Normative  
**Audience**: Implementers

---

## Table of Contents

1. [Overview](#overview)
2. [Protocol Hierarchy](#protocol-hierarchy)
3. [Core Protocols](#core-protocols)
4. [Protocol Definitions](#protocol-definitions)
5. [Implementation Requirements](#implementation-requirements)
6. [Testing Protocol Compliance](#testing-protocol-compliance)
7. [Decision Log](#decision-log)
8. [Known Limitations / Open Questions](#known-limitations--open-questions)

---

## Overview

This document defines the **authoritative** protocol interfaces for EntitySpine. All implementations must satisfy these protocols exactly. Example code and documentation must use only methods defined here.

### Design Principles

1. **Protocols are minimal**: Only include methods that ALL implementations must provide.
2. **Extend via composition**: Additional capabilities via optional protocols.
3. **Runtime checkable**: Use `@runtime_checkable` for duck typing support.
4. **Examples must compile**: Every code example must use only defined protocol methods.

---

## Protocol Hierarchy

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PROTOCOL HIERARCHY                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  EntityStoreProtocol (CORE - all backends must implement)                   │
│  ├── Entity CRUD                                                            │
│  ├── Listing queries                                                        │
│  ├── Claim queries                                                          │
│  └── Statistics                                                             │
│                                                                             │
│  StorageLifecycleProtocol (initialization, cleanup)                         │
│  ├── initialize()                                                           │
│  ├── close()                                                                │
│  └── load_sec_json()   # Bootstrap from SEC data                           │
│                                                                             │
│  SecurityStoreProtocol (security-level operations)                          │
│  ├── get_security()                                                         │
│  └── get_securities_by_entity()                                             │
│                                                                             │
│  SearchProtocol (full-text and fuzzy search)                                │
│  ├── search_entities()                                                      │
│  └── search_aliases()                                                       │
│                                                                             │
│  EntityResolverProtocol (resolution service interface)                      │
│  ├── resolve()                                                              │
│  ├── resolve_cik()                                                          │
│  ├── resolve_ticker()                                                       │
│  ├── get()                                                                  │
│  └── get_canonical()                                                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Core Protocols

### What ALL Backends Must Implement

Every storage backend (JSON, SQLite, DuckDB, PostgreSQL) must implement:

1. **EntityStoreProtocol** - Core CRUD and queries
2. **StorageLifecycleProtocol** - Setup and teardown

### What's Optional

- **SecurityStoreProtocol** - Required for Tier 1+, optional for Tier 0
- **SearchProtocol** - Capabilities vary by tier

---

## Protocol Definitions

### EntityStoreProtocol

```python
# src/entityspine/domain/protocols/store.py
"""
Core storage protocol - ALL backends must implement this.
"""

from datetime import date
from typing import Protocol, runtime_checkable

from entityspine.domain.models.entity import Entity
from entityspine.domain.models.listing import Listing
from entityspine.domain.models.claim import IdentifierClaim


@runtime_checkable
class EntityStoreProtocol(Protocol):
    """
    Core protocol for entity storage backends.
    
    ALL storage implementations (JSON, SQLite, DuckDB, PostgreSQL)
    must satisfy this interface.
    
    Note:
        This protocol includes ONLY methods that ALL backends can implement.
        Tier-specific features are in separate protocols.
    """
    
    # =========================================================================
    # Entity Operations
    # =========================================================================
    
    def get_entity(self, entity_id: str) -> Entity | None:
        """
        Get entity by ID, following merge redirects.
        
        Args:
            entity_id: Entity ULID.
        
        Returns:
            Entity (canonical, after following redirects) or None.
        
        Note:
            If entity A merged into B, get_entity("A") returns B.
            Use get_entity_raw() to get A without following redirects.
        """
        ...
    
    def get_entity_raw(self, entity_id: str) -> Entity | None:
        """
        Get entity by ID WITHOUT following merge redirects.
        
        Args:
            entity_id: Entity ULID.
        
        Returns:
            Entity exactly as stored (may have merged_into_id set).
        """
        ...
    
    def get_entities_by_cik(self, cik: str) -> list[Entity]:
        """
        Get entities matching CIK (via claims lookup).
        
        Args:
            cik: SEC Central Index Key (with or without padding).
        
        Returns:
            List of matching entities (usually 0 or 1).
        """
        ...
    
    def save_entity(self, entity: Entity) -> None:
        """
        Save or update entity.
        
        Args:
            entity: Entity to save.
        
        Note:
            Upserts by entity_id.
        """
        ...
    
    # =========================================================================
    # Listing Operations (ticker resolution)
    # =========================================================================
    
    def get_listings_by_ticker(
        self,
        ticker: str,
        mic: str | None = None,
        as_of: date | None = None,
    ) -> list[Listing]:
        """
        Get listings matching ticker.
        
        Args:
            ticker: Stock ticker symbol (case-insensitive).
            mic: Optional Market Identifier Code filter.
            as_of: Optional point-in-time filter.
        
        Returns:
            List of matching listings.
        
        Note:
            Implementations should return ALL matching listings.
            If as_of filtering is not supported, return current listings
            and let the resolver add appropriate warnings.
        """
        ...
    
    def get_listings_by_security(self, security_id: str) -> list[Listing]:
        """
        Get all listings for a security.
        
        Args:
            security_id: Security ULID.
        
        Returns:
            All listings (current and historical) for the security.
        """
        ...
    
    # =========================================================================
    # Claim Operations
    # =========================================================================
    
    def get_claims(
        self,
        scheme: str,
        value: str,
    ) -> list[IdentifierClaim]:
        """
        Get claims matching scheme and value.
        
        Args:
            scheme: Identifier scheme (cik, lei, isin, etc.).
            value: Identifier value.
        
        Returns:
            List of matching claims.
        """
        ...
    
    def save_claim(self, claim: IdentifierClaim) -> None:
        """
        Save identifier claim.
        
        Args:
            claim: Claim to save.
        """
        ...
    
    # =========================================================================
    # Statistics
    # =========================================================================
    
    def entity_count(self) -> int:
        """
        Get total number of entities.
        
        Returns:
            Count of entities in store.
        """
        ...
    
    def listing_count(self) -> int:
        """
        Get total number of listings.
        
        Returns:
            Count of listings in store.
        """
        ...


@runtime_checkable
class StorageLifecycleProtocol(Protocol):
    """
    Protocol for storage lifecycle management.
    
    Handles initialization, cleanup, and data loading.
    """
    
    def initialize(self) -> None:
        """
        Initialize storage (create tables/indexes).
        
        Idempotent: safe to call multiple times.
        """
        ...
    
    def close(self) -> None:
        """
        Close storage connections and release resources.
        """
        ...
    
    def load_sec_json(self, data: dict) -> int:
        """
        Load entities from SEC company_tickers.json format.
        
        Args:
            data: Dict in SEC JSON format:
                {"0": {"cik_str": 320193, "ticker": "AAPL", "title": "..."}}
        
        Returns:
            Number of entities loaded.
        
        Note:
            This creates Entity, Security, Listing, and Claim records
            from the flat SEC JSON structure.
        """
        ...


@runtime_checkable
class SecurityStoreProtocol(Protocol):
    """
    Protocol for security-level operations.
    
    Required for Tier 1+, optional for Tier 0.
    """
    
    def get_security(self, security_id: str) -> "Security | None":
        """
        Get security by ID.
        
        Args:
            security_id: Security ULID.
        
        Returns:
            Security or None.
        """
        ...
    
    def get_securities_by_entity(self, entity_id: str) -> list["Security"]:
        """
        Get all securities issued by an entity.
        
        Args:
            entity_id: Entity ULID.
        
        Returns:
            List of securities.
        """
        ...
    
    def save_security(self, security: "Security") -> None:
        """
        Save or update security.
        
        Args:
            security: Security to save.
        """
        ...


@runtime_checkable  
class SearchProtocol(Protocol):
    """
    Protocol for search operations.
    
    Capabilities vary by tier:
    - Tier 0: Exact match only
    - Tier 1: LIKE patterns
    - Tier 2-3: Full-text search
    """
    
    def search_entities(
        self,
        query: str,
        limit: int = 10,
    ) -> list[tuple[Entity, float]]:
        """
        Search entities by name.
        
        Args:
            query: Search query.
            limit: Maximum results.
        
        Returns:
            List of (entity, similarity_score) tuples.
        """
        ...
    
    def search_aliases(
        self,
        query: str,
        limit: int = 10,
    ) -> list[tuple[str, str, float]]:
        """
        Search entity aliases.
        
        Args:
            query: Search query.
            limit: Maximum results.
        
        Returns:
            List of (entity_id, alias_text, similarity_score) tuples.
        """
        ...
```

### EntityResolverProtocol

```python
# src/entityspine/domain/protocols/resolver.py
"""
Resolution protocol - the main service interface.
"""

from datetime import date
from typing import Protocol

from entityspine.domain.models.entity import Entity
from entityspine.domain.models.resolution import ResolutionResult


class EntityResolverProtocol(Protocol):
    """
    Protocol for entity resolution.
    
    This is the primary interface for consumers.
    
    CRITICAL v2.2 Requirements:
    - resolve() returns ResolutionResult, NEVER Entity
    - get() follows merge redirects
    - All methods return honest warnings when limited
    """
    
    def resolve(
        self,
        query: str,
        as_of: date | None = None,
        limit: int = 10,
    ) -> ResolutionResult:
        """
        Resolve any identifier to ranked entity candidates.
        
        Automatically detects identifier type (CIK, ticker, name).
        
        Args:
            query: CIK, ticker, name, or other identifier.
            as_of: Point-in-time for resolution (may be ignored with warning).
            limit: Maximum candidates to return.
        
        Returns:
            ResolutionResult with ranked candidates and any warnings.
        """
        ...
    
    def resolve_cik(self, cik: str) -> ResolutionResult:
        """
        Resolve SEC CIK to entity candidates.
        
        Args:
            cik: SEC Central Index Key (with or without padding).
        
        Returns:
            ResolutionResult with candidates.
        """
        ...
    
    def resolve_ticker(
        self,
        ticker: str,
        mic: str | None = None,
        as_of: date | None = None,
    ) -> ResolutionResult:
        """
        Resolve ticker via Listing → Security → Entity.
        
        Args:
            ticker: Stock ticker symbol.
            mic: Optional Market Identifier Code.
            as_of: Optional point-in-time.
        
        Returns:
            ResolutionResult with candidates (and warnings if limited).
        """
        ...
    
    def get(self, entity_id: str) -> Entity | None:
        """
        Get entity by ID, following merge redirects.
        
        Args:
            entity_id: Entity ULID.
        
        Returns:
            Canonical entity or None.
        """
        ...
    
    def get_canonical(
        self,
        entity_id: str,
    ) -> tuple[Entity | None, list[str], bool, bool]:
        """
        Get entity with full redirect information.
        
        Args:
            entity_id: Entity ULID.
        
        Returns:
            Tuple of:
            - Entity (canonical) or None
            - Redirect chain (list of entity_ids traversed)
            - cycle_detected (bool): True if circular reference found
            - truncated (bool): True if max depth reached
        """
        ...
    
    @property
    def tier(self) -> int:
        """
        The storage tier (0, 1, 2, or 3).
        
        Used to determine capability limits.
        """
        ...
    
    @property
    def entity_count(self) -> int:
        """Number of entities in the store."""
        ...
```

---

## Implementation Requirements

### Tier 0: JSON Store

Must implement:
- `EntityStoreProtocol` (all methods)
- `StorageLifecycleProtocol` (`initialize`, `close`, `load_sec_json`)

May omit:
- `SecurityStoreProtocol` (flat structure, no separate securities)
- `SearchProtocol` (exact match only via get_entities_by_cik)

### Tier 1: SQLite Store

Must implement:
- `EntityStoreProtocol`
- `StorageLifecycleProtocol`
- `SecurityStoreProtocol`
- `SearchProtocol` (LIKE-based)

### Tier 3: PostgreSQL Store

Must implement:
- All protocols
- Full temporal resolution
- Conflict handling

---

## Testing Protocol Compliance

### Protocol Compliance Test

```python
# tests/unit/domain/protocols/test_protocol_compliance.py
"""Tests that implementations satisfy protocols."""

import pytest
from entityspine.domain.protocols.store import (
    EntityStoreProtocol,
    StorageLifecycleProtocol,
    SecurityStoreProtocol,
)


class TestJSONStoreCompliance:
    """JSON store must implement required protocols."""
    
    def test_implements_entity_store_protocol(self):
        from entityspine.infrastructure.storage.json_store import JSONStore
        
        store = JSONStore()
        assert isinstance(store, EntityStoreProtocol)
    
    def test_implements_lifecycle_protocol(self):
        from entityspine.infrastructure.storage.json_store import JSONStore
        
        store = JSONStore()
        assert isinstance(store, StorageLifecycleProtocol)


class TestSQLiteStoreCompliance:
    """SQLite store must implement all protocols."""
    
    def test_implements_entity_store_protocol(self, temp_db):
        from entityspine.infrastructure.storage.sqlite_store import SQLiteStore
        
        store = SQLiteStore(temp_db)
        assert isinstance(store, EntityStoreProtocol)
    
    def test_implements_security_store_protocol(self, temp_db):
        from entityspine.infrastructure.storage.sqlite_store import SQLiteStore
        
        store = SQLiteStore(temp_db)
        assert isinstance(store, SecurityStoreProtocol)
```

### Method Existence Test

```python
def test_protocol_methods_exist():
    """All protocol methods must exist on implementations."""
    from entityspine.infrastructure.storage.sqlite_store import SQLiteStore
    
    required_methods = [
        "get_entity",
        "get_entity_raw",
        "get_entities_by_cik",
        "save_entity",
        "get_listings_by_ticker",
        "get_listings_by_security",
        "get_claims",
        "save_claim",
        "entity_count",
        "listing_count",
        "initialize",
        "close",
        "load_sec_json",
    ]
    
    for method in required_methods:
        assert hasattr(SQLiteStore, method), f"Missing method: {method}"
```

---

## Decision Log

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | Split protocols (core, lifecycle, security, search) | Not all backends need all features |
| 2 | `get_entity_raw()` in core protocol | Needed for debugging and redirect chain building |
| 3 | `listing_count()` added | Symmetry with entity_count, useful for stats |
| 4 | `load_sec_json()` in lifecycle | SEC JSON is primary bootstrap source |
| 5 | Search is separate protocol | Capabilities vary dramatically by tier |
| 6 | `get_canonical` returns 4-tuple | Need cycle_detected and truncated flags |
| 7 | Resolver has `tier` property | Consumers can check capability limits |

---

## Known Limitations / Open Questions

### Limitations

1. **Protocol methods are synchronous**: No async variants yet.
2. **No batch operations in core protocol**: `save_entities()` would help performance.
3. **No transaction support**: Protocol doesn't define transaction boundaries.

### Open Questions

1. **Should we add async protocol variants?**
   - `AsyncEntityStoreProtocol` with async/await methods
   - Tier 3 PostgreSQL would benefit

2. **Should SearchProtocol return ResolutionCandidate instead of tuples?**
   - More type-safe
   - But adds coupling to resolution module

3. **How to handle protocol versioning?**
   - If we add methods later, old implementations break
   - Could version protocols: `EntityStoreProtocolV2`

---

*EntitySpine Protocols v2.2.1 | January 2026*
