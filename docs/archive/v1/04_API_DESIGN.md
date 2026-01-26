# Entity Master - API Design

Service API for entity resolution, search, and integration.

---

## Design Philosophy

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CONSUMERS                                       │
│                                                                              │
│   py-sec-edgar      Data Pipelines      Web Apps       CLI Tools            │
│       │                   │                 │              │                 │
│       └───────────────────┴────────┬────────┴──────────────┘                 │
│                                    │                                         │
│                                    ▼                                         │
│                        ┌───────────────────────┐                             │
│                        │   Entity Master API    │                            │
│                        │                       │                             │
│                        │  • Simple lookups    │                              │
│                        │  • Batch resolution  │                              │
│                        │  • Fuzzy search      │                              │
│                        │  • Graph queries     │                              │
│                        │  • Change webhooks   │                              │
│                        └───────────┬───────────┘                             │
│                                    │                                         │
│                      ┌─────────────┼─────────────┐                           │
│                      │             │             │                           │
│                      ▼             ▼             ▼                           │
│               ┌──────────┐  ┌──────────┐  ┌──────────┐                       │
│               │  Python  │  │   REST   │  │ GraphQL  │                       │
│               │   SDK    │  │   API    │  │   API    │                       │
│               └──────────┘  └──────────┘  └──────────┘                       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Python SDK (Primary Interface)

### Installation

```bash
pip install entity-master

# Or with specific backends
pip install entity-master[postgres]
pip install entity-master[graph]
pip install entity-master[all]
```

### Quick Start

```python
from entity_master import EntityMaster

# Initialize (auto-detects tier from config)
em = EntityMaster()

# Simple resolution
entity = em.resolve("AAPL")
entity = em.resolve("0000320193")  # CIK
entity = em.resolve("549300Q4RLWG85ULYE86")  # LEI

# Get specific identifier
cik = em.get_cik("AAPL")
lei = em.get_lei("Apple Inc")
```

### Core API

```python
# entity_master/api/__init__.py

from typing import Optional, List
from dataclasses import dataclass
from enum import Enum


class IdentifierScheme(Enum):
    """Supported identifier schemes."""
    CIK = "cik"
    LEI = "lei"
    FIGI = "figi"
    ISIN = "isin"
    CUSIP = "cusip"
    SEDOL = "sedol"
    TICKER = "ticker"
    PERMID = "permid"
    DUNS = "duns"
    INTERNAL = "internal"


@dataclass
class Identifier:
    """An identifier with optional context."""
    scheme: IdentifierScheme
    value: str
    exchange: Optional[str] = None  # For tickers
    country: Optional[str] = None   # For ISINs, etc.
    valid_from: Optional[str] = None
    valid_to: Optional[str] = None


@dataclass
class ResolvedEntity:
    """A fully resolved entity."""
    id: str                          # Internal Entity Master ID
    primary_name: str                # Canonical name
    entity_type: str                 # company, person, security
    identifiers: List[Identifier]    # All known identifiers
    aliases: List[str]               # Alternative names
    status: str                      # active, inactive, merged
    metadata: dict                   # Additional attributes
    confidence: float                # Resolution confidence 0-1
    
    # Convenience accessors
    @property
    def cik(self) -> Optional[str]:
        """Get CIK if available."""
        return self._get_identifier(IdentifierScheme.CIK)
    
    @property
    def lei(self) -> Optional[str]:
        """Get LEI if available."""
        return self._get_identifier(IdentifierScheme.LEI)
    
    @property
    def ticker(self) -> Optional[str]:
        """Get primary ticker if available."""
        return self._get_identifier(IdentifierScheme.TICKER)
    
    def _get_identifier(self, scheme: IdentifierScheme) -> Optional[str]:
        for ident in self.identifiers:
            if ident.scheme == scheme:
                return ident.value
        return None


class EntityMaster:
    """Main Entity Master interface."""
    
    def __init__(
        self,
        tier: str = "auto",
        config_path: str = None,
        storage_url: str = None,
    ):
        """Initialize Entity Master.
        
        Args:
            tier: 'basic', 'intermediate', 'advanced', 'full', 'mindblowing', 'auto'
            config_path: Path to config YAML
            storage_url: Direct database URL
        """
        ...
    
    # =========================================================================
    # RESOLUTION
    # =========================================================================
    
    def resolve(
        self,
        query: str,
        schemes: List[IdentifierScheme] = None,
        min_confidence: float = 0.8,
    ) -> Optional[ResolvedEntity]:
        """Resolve any identifier or name to an entity.
        
        Args:
            query: Identifier value or company name
            schemes: Limit to specific identifier schemes
            min_confidence: Minimum confidence threshold
        
        Returns:
            ResolvedEntity or None if not found
        
        Examples:
            em.resolve("AAPL")
            em.resolve("0000320193")  # CIK
            em.resolve("Apple Inc")
            em.resolve("US0378331005", schemes=[IdentifierScheme.ISIN])
        """
        ...
    
    def resolve_batch(
        self,
        queries: List[str],
        schemes: List[IdentifierScheme] = None,
    ) -> dict[str, Optional[ResolvedEntity]]:
        """Resolve multiple identifiers efficiently.
        
        Args:
            queries: List of identifiers or names
            schemes: Limit to specific identifier schemes
        
        Returns:
            Dict mapping query → ResolvedEntity (or None)
        """
        ...
    
    # =========================================================================
    # DIRECT LOOKUPS
    # =========================================================================
    
    def get_by_cik(self, cik: str) -> Optional[ResolvedEntity]:
        """Look up by SEC CIK."""
        ...
    
    def get_by_lei(self, lei: str) -> Optional[ResolvedEntity]:
        """Look up by Legal Entity Identifier."""
        ...
    
    def get_by_ticker(
        self,
        ticker: str,
        exchange: str = None,
    ) -> Optional[ResolvedEntity]:
        """Look up by ticker symbol."""
        ...
    
    def get_by_figi(self, figi: str) -> Optional[ResolvedEntity]:
        """Look up by FIGI."""
        ...
    
    # =========================================================================
    # IDENTIFIER CONVERSION
    # =========================================================================
    
    def get_cik(self, query: str) -> Optional[str]:
        """Get CIK for any identifier or name."""
        entity = self.resolve(query)
        return entity.cik if entity else None
    
    def get_lei(self, query: str) -> Optional[str]:
        """Get LEI for any identifier or name."""
        entity = self.resolve(query)
        return entity.lei if entity else None
    
    def get_ticker(self, query: str) -> Optional[str]:
        """Get primary ticker for any identifier or name."""
        entity = self.resolve(query)
        return entity.ticker if entity else None
    
    def get_figi(self, query: str) -> Optional[str]:
        """Get FIGI for any identifier or name."""
        entity = self.resolve(query)
        return entity.figi if entity else None
    
    def convert(
        self,
        value: str,
        from_scheme: IdentifierScheme,
        to_scheme: IdentifierScheme,
    ) -> Optional[str]:
        """Convert between identifier schemes.
        
        Example:
            lei = em.convert("AAPL", IdentifierScheme.TICKER, IdentifierScheme.LEI)
        """
        ...
    
    # =========================================================================
    # SEARCH
    # =========================================================================
    
    def search(
        self,
        query: str,
        entity_type: str = None,
        limit: int = 10,
    ) -> List[ResolvedEntity]:
        """Fuzzy search for entities by name.
        
        Args:
            query: Search query (supports wildcards)
            entity_type: Filter by type ('company', 'person', 'security')
            limit: Max results
        
        Returns:
            List of matching entities sorted by relevance
        """
        ...
    
    def autocomplete(
        self,
        prefix: str,
        limit: int = 10,
    ) -> List[str]:
        """Autocomplete entity names.
        
        Returns list of matching names for UI autocomplete.
        """
        ...
    
    # =========================================================================
    # RELATIONSHIPS (Tier 4+)
    # =========================================================================
    
    def get_relationships(
        self,
        entity_id: str,
        relationship_types: List[str] = None,
        direction: str = "both",  # "outbound", "inbound", "both"
    ) -> List[dict]:
        """Get entity relationships.
        
        Args:
            entity_id: Entity ID or resolvable identifier
            relationship_types: Filter by type
            direction: Relationship direction
        
        Returns:
            List of relationship dicts with source, target, type, metadata
        """
        ...
    
    def find_path(
        self,
        source: str,
        target: str,
        max_hops: int = 5,
    ) -> List[dict]:
        """Find connection path between two entities."""
        ...
    
    # =========================================================================
    # ENRICHMENT
    # =========================================================================
    
    def enrich(
        self,
        entity_id: str,
        sources: List[str] = None,
        force: bool = False,
    ) -> ResolvedEntity:
        """Enrich entity from external sources.
        
        Args:
            entity_id: Entity to enrich
            sources: Which sources ('gleif', 'openfigi', 'sec')
            force: Re-enrich even if recent data exists
        
        Returns:
            Enriched entity
        """
        ...
    
    # =========================================================================
    # CHANGE TRACKING
    # =========================================================================
    
    def changes_since(
        self,
        since: str | datetime,
        change_types: List[str] = None,
    ) -> List[dict]:
        """Get changes since a timestamp.
        
        Args:
            since: ISO timestamp or datetime
            change_types: 'new', 'updated', 'deleted', 'merged'
        
        Returns:
            List of change records
        """
        ...
```

---

## py-sec-edgar Integration

### Simple Drop-In

```python
# In py_sec_edgar/core/identity/__init__.py

from entity_master import EntityMaster


# Global instance (lazy-loaded)
_em: EntityMaster | None = None


def get_entity_master() -> EntityMaster:
    """Get or create Entity Master instance."""
    global _em
    if _em is None:
        _em = EntityMaster(tier="auto")
    return _em


def resolve_cik(identifier: str) -> str | None:
    """Resolve any identifier to CIK.
    
    Usage:
        from py_sec_edgar.core.identity import resolve_cik
        
        cik = resolve_cik("AAPL")
        cik = resolve_cik("Apple Inc")
    """
    return get_entity_master().get_cik(identifier)


def resolve_ticker(identifier: str) -> str | None:
    """Resolve any identifier to ticker."""
    return get_entity_master().get_ticker(identifier)


def resolve_lei(identifier: str) -> str | None:
    """Resolve any identifier to LEI."""
    return get_entity_master().get_lei(identifier)


def search_companies(query: str, limit: int = 10) -> list[dict]:
    """Search for companies by name."""
    em = get_entity_master()
    entities = em.search(query, entity_type="company", limit=limit)
    return [
        {
            "name": e.primary_name,
            "cik": e.cik,
            "ticker": e.ticker,
            "lei": e.lei,
        }
        for e in entities
    ]
```

### Decorator for Auto-Resolution

```python
# In py_sec_edgar/core/identity/decorators.py

from functools import wraps
from typing import Callable


def resolve_identifier(param_name: str = "cik"):
    """Decorator to auto-resolve identifiers to CIK.
    
    Usage:
        @resolve_identifier("cik")
        def get_filings(cik: str, form_type: str = None):
            # cik is guaranteed to be a valid CIK
            ...
        
        # These all work:
        get_filings("0000320193")  # Already a CIK
        get_filings("AAPL")        # Resolved from ticker
        get_filings("Apple Inc")   # Resolved from name
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get the parameter value
            if param_name in kwargs:
                value = kwargs[param_name]
            else:
                # Assume first positional arg
                value = args[0]
                args = args[1:]
            
            # Resolve to CIK
            cik = resolve_cik(value)
            if cik is None:
                raise ValueError(f"Could not resolve '{value}' to a CIK")
            
            # Call with resolved CIK
            kwargs[param_name] = cik
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


# Example usage in py_sec_edgar
@resolve_identifier("cik")
def download_filings(cik: str, form_type: str = "10-K"):
    """Download filings - accepts CIK, ticker, or name."""
    # cik is guaranteed valid here
    ...
```

### Pipeline Integration

```python
# Example: Enhance filing download with entity resolution

from py_sec_edgar import SECClient
from py_sec_edgar.core.identity import get_entity_master


class EnhancedSECClient(SECClient):
    """SEC client with Entity Master integration."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._em = get_entity_master()
    
    def get_filings(
        self,
        identifier: str,  # Accepts CIK, ticker, name, LEI
        **kwargs,
    ):
        """Get filings for any identifier."""
        entity = self._em.resolve(identifier)
        if entity is None:
            raise ValueError(f"Unknown entity: {identifier}")
        
        if entity.cik is None:
            raise ValueError(f"Entity '{entity.primary_name}' has no CIK")
        
        # Store resolved entity for metadata
        self._current_entity = entity
        
        return super().get_filings(cik=entity.cik, **kwargs)
    
    def download_with_metadata(
        self,
        identifier: str,
        **kwargs,
    ):
        """Download filings with enhanced entity metadata."""
        entity = self._em.resolve(identifier)
        
        filings = self.get_filings(identifier, **kwargs)
        
        # Enhance filings with entity data
        for filing in filings:
            filing.entity = {
                "name": entity.primary_name,
                "cik": entity.cik,
                "ticker": entity.ticker,
                "lei": entity.lei,
                "aliases": entity.aliases,
            }
        
        return filings
```

---

## REST API

For applications needing HTTP interface.

### Endpoints

```yaml
# OpenAPI spec summary

paths:
  # Resolution
  /resolve/{query}:
    get:
      summary: Resolve identifier to entity
      parameters:
        - name: query
          in: path
          required: true
          description: CIK, ticker, name, LEI, FIGI, ISIN, etc.
        - name: schemes
          in: query
          description: Limit to specific schemes (comma-separated)
      responses:
        200:
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ResolvedEntity'
  
  /resolve/batch:
    post:
      summary: Resolve multiple identifiers
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                queries:
                  type: array
                  items:
                    type: string
      responses:
        200:
          content:
            application/json:
              schema:
                type: object
                additionalProperties:
                  $ref: '#/components/schemas/ResolvedEntity'
  
  # Direct lookups
  /entities/cik/{cik}:
    get:
      summary: Get entity by CIK
  
  /entities/lei/{lei}:
    get:
      summary: Get entity by LEI
  
  /entities/ticker/{ticker}:
    get:
      summary: Get entity by ticker
      parameters:
        - name: exchange
          in: query
          description: Filter by exchange
  
  # Search
  /search:
    get:
      summary: Search entities
      parameters:
        - name: q
          in: query
          required: true
        - name: type
          in: query
          description: Entity type filter
        - name: limit
          in: query
          default: 10
  
  # Conversion
  /convert:
    get:
      summary: Convert between identifier schemes
      parameters:
        - name: value
          in: query
          required: true
        - name: from
          in: query
          required: true
          description: Source scheme (cik, lei, ticker, etc.)
        - name: to
          in: query
          required: true
          description: Target scheme
  
  # Relationships (Tier 4+)
  /entities/{id}/relationships:
    get:
      summary: Get entity relationships
      parameters:
        - name: types
          in: query
          description: Relationship type filter
        - name: direction
          in: query
          enum: [inbound, outbound, both]
  
  /path/{source}/{target}:
    get:
      summary: Find path between entities
      parameters:
        - name: max_hops
          in: query
          default: 5
  
  # Changes
  /changes:
    get:
      summary: Get recent changes
      parameters:
        - name: since
          in: query
          description: ISO timestamp
        - name: types
          in: query
          description: Change types filter
```

### FastAPI Implementation

```python
# entity_master/api/rest.py

from fastapi import FastAPI, HTTPException, Query
from entity_master import EntityMaster

app = FastAPI(title="Entity Master API")
em = EntityMaster()


@app.get("/resolve/{query}")
async def resolve(
    query: str,
    schemes: str = None,
):
    """Resolve any identifier to entity."""
    scheme_list = schemes.split(",") if schemes else None
    
    entity = em.resolve(query, schemes=scheme_list)
    if entity is None:
        raise HTTPException(404, f"Entity not found: {query}")
    
    return entity


@app.post("/resolve/batch")
async def resolve_batch(body: dict):
    """Resolve multiple identifiers."""
    queries = body.get("queries", [])
    return em.resolve_batch(queries)


@app.get("/search")
async def search(
    q: str = Query(...),
    type: str = None,
    limit: int = 10,
):
    """Search entities."""
    return em.search(q, entity_type=type, limit=limit)


@app.get("/convert")
async def convert(
    value: str = Query(...),
    from_scheme: str = Query(..., alias="from"),
    to_scheme: str = Query(..., alias="to"),
):
    """Convert between identifier schemes."""
    result = em.convert(value, from_scheme, to_scheme)
    if result is None:
        raise HTTPException(404, f"Cannot convert {value}")
    return {"value": result, "scheme": to_scheme}
```

---

## GraphQL API

For flexible queries and relationship exploration.

```graphql
# entity_master/api/schema.graphql

type Entity {
  id: ID!
  primaryName: String!
  entityType: EntityType!
  status: EntityStatus!
  identifiers: [Identifier!]!
  aliases: [String!]!
  
  # Convenience fields
  cik: String
  lei: String
  ticker: String
  figi: String
  
  # Relationships (lazy-loaded)
  relationships(
    types: [RelationshipType!]
    direction: Direction
  ): [Relationship!]!
  
  # Related entities
  suppliers: [Entity!]!
  customers: [Entity!]!
  competitors: [Entity!]!
  subsidiaries: [Entity!]!
  parentCompany: Entity
  
  # Mentions
  mentions(limit: Int = 10): [Mention!]!
}

type Identifier {
  scheme: IdentifierScheme!
  value: String!
  exchange: String
  country: String
  validFrom: DateTime
  validTo: DateTime
}

type Relationship {
  source: Entity!
  target: Entity!
  type: RelationshipType!
  confidence: Float!
  metadata: JSON
  sources: [String!]!
  firstSeen: DateTime!
  lastSeen: DateTime!
}

type Mention {
  entity: Entity!
  document: Document!
  context: String
  sentiment: Float
  timestamp: DateTime!
}

enum EntityType {
  COMPANY
  PERSON
  SECURITY
  FUND
  INDEX
  EXCHANGE
  GOVERNMENT
}

enum IdentifierScheme {
  CIK
  LEI
  FIGI
  ISIN
  CUSIP
  SEDOL
  TICKER
  PERMID
  DUNS
}

enum RelationshipType {
  SUPPLIER_OF
  CUSTOMER_OF
  COMPETITOR_OF
  SUBSIDIARY_OF
  PARENT_OF
  EXECUTIVE_OF
  BOARD_MEMBER_OF
  INVESTOR_IN
  PARTNER_WITH
}

type Query {
  # Resolution
  resolve(query: String!, schemes: [IdentifierScheme!]): Entity
  
  # Direct lookups
  entityByCik(cik: String!): Entity
  entityByLei(lei: String!): Entity
  entityByTicker(ticker: String!, exchange: String): Entity
  
  # Search
  search(
    query: String!
    entityType: EntityType
    limit: Int = 10
  ): [Entity!]!
  
  # Path finding
  findPath(
    source: ID!
    target: ID!
    maxHops: Int = 5
  ): [[Relationship!]!]!
  
  # Changes
  changes(
    since: DateTime!
    types: [String!]
  ): [Change!]!
}

type Mutation {
  # Manual entity creation
  createEntity(input: EntityInput!): Entity!
  
  # Add relationship
  addRelationship(
    sourceId: ID!
    targetId: ID!
    type: RelationshipType!
    metadata: JSON
  ): Relationship!
  
  # Trigger enrichment
  enrich(entityId: ID!, sources: [String!]): Entity!
}
```

### Example GraphQL Queries

```graphql
# Get entity with all identifiers
query GetEntity {
  resolve(query: "AAPL") {
    primaryName
    cik
    lei
    ticker
    identifiers {
      scheme
      value
    }
  }
}

# Get company with relationships
query GetCompanyRelationships {
  resolve(query: "Apple Inc") {
    primaryName
    suppliers {
      primaryName
      ticker
    }
    customers(limit: 5) {
      primaryName
    }
    competitors {
      primaryName
      ticker
    }
  }
}

# Find connection between companies
query FindConnection {
  findPath(
    source: "apple-inc",
    target: "taiwan-semiconductor"
    maxHops: 3
  ) {
    source { primaryName }
    target { primaryName }
    type
  }
}

# Search with relationships
query SearchWithSupplyChain {
  search(query: "semiconductor", limit: 5) {
    primaryName
    ticker
    suppliers {
      primaryName
    }
    customers {
      primaryName
    }
  }
}
```

---

## Webhooks (Tier 3+)

Get notified of entity changes.

```python
# entity_master/webhooks.py

from datetime import datetime
from pydantic import BaseModel


class WebhookEvent(BaseModel):
    """Webhook event payload."""
    event_type: str  # "entity.created", "entity.updated", etc.
    timestamp: datetime
    entity_id: str
    entity: dict  # ResolvedEntity as dict
    changes: dict | None  # For updates, what changed


class WebhookManager:
    """Manage webhook subscriptions."""
    
    def register(
        self,
        url: str,
        events: list[str] = None,
        filters: dict = None,
        secret: str = None,
    ) -> str:
        """Register a webhook endpoint.
        
        Args:
            url: Webhook URL to POST to
            events: Event types to subscribe to
            filters: Filter criteria (e.g., entity_type=company)
            secret: HMAC secret for signature verification
        
        Returns:
            Webhook ID
        """
        ...
    
    def unregister(self, webhook_id: str):
        """Remove webhook subscription."""
        ...
    
    async def dispatch(self, event: WebhookEvent):
        """Dispatch event to all matching webhooks."""
        ...
```

### Configuration

```yaml
# In entity_master.yaml

webhooks:
  - url: https://myapp.com/webhooks/entity-master
    events:
      - entity.created
      - entity.updated
    filters:
      entity_type: company
    secret: ${WEBHOOK_SECRET}
  
  - url: https://slack.com/api/webhooks/xxx
    events:
      - entity.created
    # Notify Slack of new entities
```

---

## Extended APIs

For additional APIs that support py-sec-edgar integration, see [08_INTEGRATION_EXTENSIONS.md](08_INTEGRATION_EXTENSIONS.md):

| API | Purpose | Key Features |
|-----|---------|--------------|
| **RelationshipsAPI** | Write relationships with evidence | `add()`, `add_batch()`, evidence tracking, confidence |
| **MentionsAPI** | Track entity mentions in documents | `add()`, `get_co_mentioned()`, cross-mentions |
| **EventsAPI** | Link SIGDEV events to entities | `link()`, role assignment, context capture |
| **ChangesAPI** | Enhanced change tracking | Webhooks, in-process listeners, change history |

These extensions build on this core API design.
