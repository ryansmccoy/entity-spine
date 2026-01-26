# Entity Master - Relationship Graph

Knowledge graph for entity relationships, supply chains, and network analysis.

---

## Overview

Entity Master's relationship graph captures business relationships between entities:

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           RELATIONSHIP GRAPH                                  │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│                        ┌──────────────┐                                       │
│                        │    APPLE     │                                       │
│                        │   (Company)  │                                       │
│                        └──────┬───────┘                                       │
│                               │                                               │
│         ┌─────────────────────┼─────────────────────┐                         │
│         │                     │                     │                         │
│         ▼                     ▼                     ▼                         │
│   ┌──────────┐         ┌──────────┐         ┌──────────┐                      │
│   │   TSMC   │         │  NVIDIA  │         │  GOOGLE  │                      │
│   │ SUPPLIER │         │COMPETITOR│         │ CUSTOMER │                      │
│   └────┬─────┘         └────┬─────┘         └────┬─────┘                      │
│        │                    │                    │                            │
│        ▼                    ▼                    ▼                            │
│   ┌──────────┐         ┌──────────┐         ┌──────────┐                      │
│   │  ASML    │         │   AMD    │         │MICROSOFT │                      │
│   │ SUPPLIER │         │COMPETITOR│         │COMPETITOR│                      │
│   └──────────┘         └──────────┘         └──────────┘                      │
│                                                                               │
│   Relationship Types:                                                         │
│   ─────────────────                                                           │
│   • SUPPLIER_OF          • CUSTOMER_OF         • COMPETITOR_OF                │
│   • SUBSIDIARY_OF        • PARENT_OF           • INVESTOR_IN                  │
│   • EXECUTIVE_OF         • BOARD_MEMBER_OF     • PARTNER_WITH                 │
│   • JOINT_VENTURE_WITH   • ACQUIRED_BY         • MERGED_WITH                  │
│                                                                               │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Graph Data Model

### Nodes (Entities)

```python
# entity_master/graph/models.py

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class EntityType(Enum):
    """Types of entities in the graph."""
    COMPANY = "company"
    PERSON = "person"
    SECURITY = "security"
    FUND = "fund"
    INDEX = "index"
    EXCHANGE = "exchange"
    GOVERNMENT = "government"
    INDUSTRY = "industry"


@dataclass
class GraphEntity:
    """An entity node in the graph."""
    
    id: str                          # Internal Entity Master ID
    entity_type: EntityType
    primary_name: str
    
    # Key identifiers (denormalized for fast queries)
    cik: Optional[str] = None
    lei: Optional[str] = None
    ticker: Optional[str] = None
    
    # Attributes
    status: str = "active"           # active, inactive, merged
    country: Optional[str] = None
    industry: Optional[str] = None
    sic_code: Optional[str] = None
    
    # Graph metrics (computed)
    degree: int = 0                  # Number of relationships
    pagerank: float = 0.0            # Importance score
    community_id: Optional[str] = None
    
    # Timestamps
    created_at: datetime = None
    updated_at: datetime = None
```

### Edges (Relationships)

```python
class RelationshipType(Enum):
    """Types of relationships between entities."""
    
    # Supply Chain
    SUPPLIER_OF = "SUPPLIER_OF"           # A supplies to B
    CUSTOMER_OF = "CUSTOMER_OF"           # A buys from B
    DISTRIBUTOR_OF = "DISTRIBUTOR_OF"     # A distributes B's products
    
    # Competition
    COMPETITOR_OF = "COMPETITOR_OF"       # A competes with B
    
    # Corporate Structure
    SUBSIDIARY_OF = "SUBSIDIARY_OF"       # A is subsidiary of B
    PARENT_OF = "PARENT_OF"               # A is parent of B
    DIVISION_OF = "DIVISION_OF"           # A is division of B
    
    # Transactions
    ACQUIRED_BY = "ACQUIRED_BY"           # A was acquired by B
    MERGED_WITH = "MERGED_WITH"           # A merged with B
    INVESTOR_IN = "INVESTOR_IN"           # A invested in B
    
    # Partnerships
    PARTNER_WITH = "PARTNER_WITH"         # A partners with B
    JOINT_VENTURE_WITH = "JOINT_VENTURE_WITH"
    LICENSING_AGREEMENT_WITH = "LICENSING_AGREEMENT_WITH"
    
    # People
    EXECUTIVE_OF = "EXECUTIVE_OF"         # Person A is executive of Company B
    BOARD_MEMBER_OF = "BOARD_MEMBER_OF"   # Person A on board of Company B
    FOUNDER_OF = "FOUNDER_OF"             # Person A founded Company B
    EMPLOYED_BY = "EMPLOYED_BY"           # Person A works at Company B
    
    # Industry
    MEMBER_OF = "MEMBER_OF"               # A is member of Industry B
    OPERATES_IN = "OPERATES_IN"           # A operates in Industry B


@dataclass
class GraphRelationship:
    """A relationship edge in the graph."""
    
    id: str                           # Unique relationship ID
    source_id: str                    # Source entity ID
    target_id: str                    # Target entity ID
    relationship_type: RelationshipType
    
    # Relationship attributes
    confidence: float = 1.0           # Confidence score 0-1
    strength: float = 1.0             # Relationship strength
    
    # Source tracking
    sources: list[str] = None         # Where this came from
    evidence: list[str] = None        # Supporting text excerpts
    
    # Temporal
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    first_seen: datetime = None
    last_seen: datetime = None
    
    # Metadata
    metadata: dict = None
```

---

## Neo4j Schema (Tier 4)

### Node Labels and Properties

```cypher
// Company node
CREATE (c:Company {
  id: 'em_apple_inc',
  name: 'Apple Inc',
  cik: '0000320193',
  lei: '549300Q4RLWG85ULYE86',
  ticker: 'AAPL',
  exchange: 'NASDAQ',
  country: 'US',
  state: 'CA',
  industry: 'Technology Hardware',
  sic_code: '3571',
  market_cap: 3000000000000,
  employees: 164000,
  status: 'active',
  created_at: datetime(),
  updated_at: datetime()
})

// Person node
CREATE (p:Person {
  id: 'em_tim_cook',
  name: 'Timothy D. Cook',
  title: 'Chief Executive Officer',
  status: 'active'
})

// Security node (for detailed security-level tracking)
CREATE (s:Security {
  id: 'em_aapl_equity',
  name: 'Apple Inc Common Stock',
  figi: 'BBG000B9XRY4',
  isin: 'US0378331005',
  cusip: '037833100',
  security_type: 'Common Stock'
})

// Industry node
CREATE (i:Industry {
  id: 'em_tech_hardware',
  name: 'Technology Hardware',
  sic_code: '3571',
  sector: 'Technology'
})
```

### Relationship Types

```cypher
// Supply chain relationships
MATCH (apple:Company {name: 'Apple Inc'})
MATCH (tsmc:Company {name: 'Taiwan Semiconductor'})
CREATE (tsmc)-[r:SUPPLIER_OF {
  confidence: 0.95,
  strength: 0.9,
  sources: ['10-K filing', 'news'],
  product_category: 'semiconductors',
  valid_from: date('2010-01-01'),
  first_seen: datetime(),
  last_seen: datetime()
}]->(apple)

// Competition
MATCH (apple:Company {name: 'Apple Inc'})
MATCH (samsung:Company {name: 'Samsung Electronics'})
CREATE (apple)-[r:COMPETITOR_OF {
  confidence: 0.98,
  segments: ['smartphones', 'tablets', 'wearables'],
  sources: ['10-K filing']
}]->(samsung)

// Corporate structure
MATCH (beats:Company {name: 'Beats Electronics'})
MATCH (apple:Company {name: 'Apple Inc'})
CREATE (beats)-[r:SUBSIDIARY_OF {
  acquired_date: date('2014-08-01'),
  acquisition_price: 3000000000,
  status: 'completed'
}]->(apple)

// Executive relationship
MATCH (tim:Person {name: 'Timothy D. Cook'})
MATCH (apple:Company {name: 'Apple Inc'})
CREATE (tim)-[r:EXECUTIVE_OF {
  title: 'Chief Executive Officer',
  start_date: date('2011-08-24'),
  compensation: 99400000,
  sources: ['DEF 14A proxy']
}]->(apple)
```

### Indexes and Constraints

```cypher
// Uniqueness constraints
CREATE CONSTRAINT company_id FOR (c:Company) REQUIRE c.id IS UNIQUE;
CREATE CONSTRAINT company_cik FOR (c:Company) REQUIRE c.cik IS UNIQUE;
CREATE CONSTRAINT company_lei FOR (c:Company) REQUIRE c.lei IS UNIQUE;
CREATE CONSTRAINT person_id FOR (p:Person) REQUIRE p.id IS UNIQUE;
CREATE CONSTRAINT security_figi FOR (s:Security) REQUIRE s.figi IS UNIQUE;

// Indexes for common queries
CREATE INDEX company_name FOR (c:Company) ON (c.name);
CREATE INDEX company_ticker FOR (c:Company) ON (c.ticker);
CREATE INDEX company_industry FOR (c:Company) ON (c.industry);
CREATE INDEX person_name FOR (p:Person) ON (p.name);
```

---

## Graph Queries

### Common Query Patterns

```python
# entity_master/graph/queries.py

from neo4j import AsyncGraphDatabase


class GraphQueries:
    """Common graph query patterns."""
    
    def __init__(self, neo4j_uri: str, auth: tuple):
        self.driver = AsyncGraphDatabase.driver(neo4j_uri, auth=auth)
    
    # =========================================================================
    # SUPPLY CHAIN QUERIES
    # =========================================================================
    
    async def get_suppliers(
        self,
        entity_id: str,
        max_depth: int = 1,
        min_confidence: float = 0.5,
    ) -> list[dict]:
        """Get suppliers of an entity.
        
        Args:
            entity_id: Entity to find suppliers for
            max_depth: How many hops (1 = direct, 2 = include tier-2)
            min_confidence: Minimum relationship confidence
        """
        query = """
        MATCH (e:Company {id: $entity_id})
        MATCH (supplier)-[r:SUPPLIER_OF*1..$max_depth]->(e)
        WHERE all(rel IN r WHERE rel.confidence >= $min_confidence)
        RETURN supplier, r, length(r) as depth
        ORDER BY depth, supplier.name
        """
        
        async with self.driver.session() as session:
            result = await session.run(
                query,
                entity_id=entity_id,
                max_depth=max_depth,
                min_confidence=min_confidence,
            )
            return [dict(record) async for record in result]
    
    async def get_supply_chain(
        self,
        entity_id: str,
        direction: str = "both",  # "upstream", "downstream", "both"
        max_depth: int = 3,
    ) -> dict:
        """Get full supply chain network.
        
        Returns:
            {
                "entity": {...},
                "upstream": [suppliers, their suppliers, ...],
                "downstream": [customers, their customers, ...],
            }
        """
        upstream_query = """
        MATCH (e:Company {id: $entity_id})
        MATCH path = (supplier)-[:SUPPLIER_OF*1..$max_depth]->(e)
        WITH supplier, length(path) as tier
        RETURN COLLECT({entity: supplier, tier: tier}) as upstream
        """
        
        downstream_query = """
        MATCH (e:Company {id: $entity_id})
        MATCH path = (e)-[:SUPPLIER_OF*1..$max_depth]->(customer)
        WITH customer, length(path) as tier
        RETURN COLLECT({entity: customer, tier: tier}) as downstream
        """
        
        async with self.driver.session() as session:
            upstream = []
            downstream = []
            
            if direction in ("upstream", "both"):
                result = await session.run(upstream_query, entity_id=entity_id, max_depth=max_depth)
                record = await result.single()
                upstream = record["upstream"] if record else []
            
            if direction in ("downstream", "both"):
                result = await session.run(downstream_query, entity_id=entity_id, max_depth=max_depth)
                record = await result.single()
                downstream = record["downstream"] if record else []
            
            return {
                "entity_id": entity_id,
                "upstream": upstream,
                "downstream": downstream,
            }
    
    # =========================================================================
    # COMPETITOR ANALYSIS
    # =========================================================================
    
    async def get_competitors(
        self,
        entity_id: str,
        include_indirect: bool = False,
    ) -> list[dict]:
        """Get competitors of an entity.
        
        Args:
            entity_id: Entity to find competitors for
            include_indirect: Include companies that compete with competitors
        """
        if include_indirect:
            query = """
            MATCH (e:Company {id: $entity_id})
            MATCH (e)-[:COMPETITOR_OF*1..2]-(competitor:Company)
            WHERE competitor.id <> e.id
            RETURN DISTINCT competitor
            ORDER BY competitor.market_cap DESC
            """
        else:
            query = """
            MATCH (e:Company {id: $entity_id})
            MATCH (e)-[:COMPETITOR_OF]-(competitor:Company)
            RETURN competitor
            ORDER BY competitor.market_cap DESC
            """
        
        async with self.driver.session() as session:
            result = await session.run(query, entity_id=entity_id)
            return [dict(record["competitor"]) async for record in result]
    
    async def competitive_landscape(
        self,
        entity_id: str,
    ) -> dict:
        """Get competitive landscape analysis.
        
        Returns competitors grouped by:
        - Direct competitors
        - Indirect competitors (compete in overlapping segments)
        - Potential disruptors (different industry but similar products)
        """
        query = """
        MATCH (e:Company {id: $entity_id})
        
        // Direct competitors
        OPTIONAL MATCH (e)-[r1:COMPETITOR_OF]-(direct:Company)
        
        // Shared suppliers (potential indirect competitors)
        OPTIONAL MATCH (e)<-[:SUPPLIER_OF]-(supplier)-[:SUPPLIER_OF]->(indirect:Company)
        WHERE indirect.id <> e.id AND NOT (e)-[:COMPETITOR_OF]-(indirect)
        
        // Same industry
        OPTIONAL MATCH (e)-[:OPERATES_IN]->(industry)<-[:OPERATES_IN]-(industry_peer:Company)
        WHERE industry_peer.id <> e.id
        
        RETURN 
          e as entity,
          COLLECT(DISTINCT direct) as direct_competitors,
          COLLECT(DISTINCT indirect) as indirect_competitors,
          COLLECT(DISTINCT industry_peer) as industry_peers
        """
        
        async with self.driver.session() as session:
            result = await session.run(query, entity_id=entity_id)
            record = await result.single()
            return dict(record) if record else {}
    
    # =========================================================================
    # PATH FINDING
    # =========================================================================
    
    async def find_connection(
        self,
        source_id: str,
        target_id: str,
        max_hops: int = 5,
    ) -> list[dict]:
        """Find shortest path between two entities.
        
        Returns path as list of nodes and relationships.
        """
        query = """
        MATCH (source {id: $source_id})
        MATCH (target {id: $target_id})
        MATCH path = shortestPath((source)-[*1..$max_hops]-(target))
        RETURN path
        """
        
        async with self.driver.session() as session:
            result = await session.run(
                query,
                source_id=source_id,
                target_id=target_id,
                max_hops=max_hops,
            )
            record = await result.single()
            
            if not record:
                return []
            
            path = record["path"]
            return self._path_to_dict(path)
    
    async def find_all_paths(
        self,
        source_id: str,
        target_id: str,
        max_hops: int = 4,
        limit: int = 10,
    ) -> list[list[dict]]:
        """Find all paths between two entities."""
        query = """
        MATCH (source {id: $source_id})
        MATCH (target {id: $target_id})
        MATCH path = (source)-[*1..$max_hops]-(target)
        RETURN path
        ORDER BY length(path)
        LIMIT $limit
        """
        
        async with self.driver.session() as session:
            result = await session.run(
                query,
                source_id=source_id,
                target_id=target_id,
                max_hops=max_hops,
                limit=limit,
            )
            
            paths = []
            async for record in result:
                paths.append(self._path_to_dict(record["path"]))
            return paths
    
    # =========================================================================
    # NETWORK ANALYSIS
    # =========================================================================
    
    async def get_entity_network(
        self,
        entity_id: str,
        max_hops: int = 2,
        relationship_types: list[str] = None,
    ) -> dict:
        """Get the network around an entity.
        
        Returns nodes and edges for visualization.
        """
        rel_filter = ""
        if relationship_types:
            rel_filter = "WHERE type(r) IN $rel_types"
        
        query = f"""
        MATCH (center {{id: $entity_id}})
        CALL apoc.path.subgraphAll(center, {{
          maxLevel: $max_hops,
          relationshipFilter: $rel_filter
        }})
        YIELD nodes, relationships
        RETURN nodes, relationships
        """
        
        async with self.driver.session() as session:
            result = await session.run(
                query,
                entity_id=entity_id,
                max_hops=max_hops,
                rel_types=relationship_types or [],
            )
            record = await result.single()
            
            return {
                "nodes": [dict(n) for n in record["nodes"]],
                "edges": [self._rel_to_dict(r) for r in record["relationships"]],
            }
    
    async def calculate_centrality(
        self,
        entity_ids: list[str] = None,
    ) -> list[dict]:
        """Calculate centrality metrics for entities.
        
        Returns:
            List of entities with degree, pagerank, betweenness centrality
        """
        # Using Neo4j Graph Data Science library
        query = """
        CALL gds.pageRank.stream('company-graph')
        YIELD nodeId, score
        WITH gds.util.asNode(nodeId) AS entity, score as pagerank
        
        CALL gds.degree.stream('company-graph')
        YIELD nodeId, score as degree
        WHERE gds.util.asNode(nodeId) = entity
        
        CALL gds.betweenness.stream('company-graph')
        YIELD nodeId, score as betweenness
        WHERE gds.util.asNode(nodeId) = entity
        
        RETURN entity.id, entity.name, pagerank, degree, betweenness
        ORDER BY pagerank DESC
        """
        
        async with self.driver.session() as session:
            result = await session.run(query)
            return [dict(record) async for record in result]
    
    async def detect_communities(self) -> list[dict]:
        """Detect communities in the entity graph.
        
        Uses Louvain algorithm to find clusters.
        """
        query = """
        CALL gds.louvain.stream('company-graph')
        YIELD nodeId, communityId
        WITH gds.util.asNode(nodeId) AS entity, communityId
        RETURN communityId, COLLECT(entity.name) as members, COUNT(*) as size
        ORDER BY size DESC
        """
        
        async with self.driver.session() as session:
            result = await session.run(query)
            return [dict(record) async for record in result]
    
    # =========================================================================
    # EXECUTIVE/PEOPLE QUERIES
    # =========================================================================
    
    async def get_executives(
        self,
        entity_id: str,
        include_board: bool = True,
    ) -> list[dict]:
        """Get executives and board members."""
        rel_types = ["EXECUTIVE_OF"]
        if include_board:
            rel_types.append("BOARD_MEMBER_OF")
        
        query = """
        MATCH (e:Company {id: $entity_id})
        MATCH (p:Person)-[r]->(e)
        WHERE type(r) IN $rel_types
        RETURN p as person, type(r) as role, r.title as title
        ORDER BY r.compensation DESC NULLS LAST
        """
        
        async with self.driver.session() as session:
            result = await session.run(
                query,
                entity_id=entity_id,
                rel_types=rel_types,
            )
            return [dict(record) async for record in result]
    
    async def get_interlocking_boards(
        self,
        entity_id: str,
    ) -> list[dict]:
        """Find companies with shared board members."""
        query = """
        MATCH (e:Company {id: $entity_id})
        MATCH (e)<-[:BOARD_MEMBER_OF]-(p:Person)-[:BOARD_MEMBER_OF]->(other:Company)
        WHERE other.id <> e.id
        RETURN other as company, COLLECT(p.name) as shared_directors, COUNT(p) as overlap
        ORDER BY overlap DESC
        """
        
        async with self.driver.session() as session:
            result = await session.run(query, entity_id=entity_id)
            return [dict(record) async for record in result]
    
    # =========================================================================
    # HELPERS
    # =========================================================================
    
    def _path_to_dict(self, path) -> list[dict]:
        """Convert Neo4j path to list of dicts."""
        result = []
        nodes = list(path.nodes)
        rels = list(path.relationships)
        
        for i, node in enumerate(nodes):
            result.append({
                "type": "node",
                "data": dict(node),
            })
            
            if i < len(rels):
                result.append({
                    "type": "relationship",
                    "data": self._rel_to_dict(rels[i]),
                })
        
        return result
    
    def _rel_to_dict(self, rel) -> dict:
        """Convert Neo4j relationship to dict."""
        return {
            "type": rel.type,
            "source": rel.start_node["id"],
            "target": rel.end_node["id"],
            "properties": dict(rel),
        }
```

---

## Graph Building Pipeline

### Relationship Extraction

```python
# entity_master/graph/builder.py

from datetime import datetime
from entity_master.graph.models import GraphRelationship, RelationshipType


class GraphBuilder:
    """Build and maintain the relationship graph."""
    
    def __init__(self, entity_master, graph_storage):
        self.em = entity_master
        self.storage = graph_storage
    
    async def build_from_sec_filings(self, cik: str):
        """Extract relationships from SEC filings."""
        # Get 10-K and proxy filings
        # Parse for supplier/customer mentions
        # Use LLM for relationship extraction
        pass
    
    async def build_from_gleif_relationships(self):
        """Load GLEIF relationship data.
        
        GLEIF provides:
        - Parent-child relationships
        - Ultimate parent relationships
        - Merger/acquisition history
        """
        from entity_master.feeds import GLEIFRelationshipsFeed
        
        feed = GLEIFRelationshipsFeed()
        records = await feed.fetch()
        
        for record in records:
            if record.content["relationship_type"] == "IS_ULTIMATELY_CONSOLIDATED_BY":
                await self.add_relationship(
                    source_id=await self._resolve_lei(record.content["child_lei"]),
                    target_id=await self._resolve_lei(record.content["parent_lei"]),
                    relationship_type=RelationshipType.SUBSIDIARY_OF,
                    confidence=1.0,
                    sources=["gleif_rr"],
                    valid_from=record.content.get("valid_from"),
                )
    
    async def add_relationship(
        self,
        source_id: str,
        target_id: str,
        relationship_type: RelationshipType,
        confidence: float = 1.0,
        sources: list[str] = None,
        evidence: list[str] = None,
        metadata: dict = None,
        valid_from: datetime = None,
        valid_to: datetime = None,
    ) -> GraphRelationship:
        """Add or update a relationship."""
        
        # Check for existing relationship
        existing = await self.storage.get_relationship(
            source_id,
            target_id,
            relationship_type,
        )
        
        if existing:
            # Update confidence (take max)
            existing.confidence = max(existing.confidence, confidence)
            
            # Append sources
            existing.sources = list(set(existing.sources or []) | set(sources or []))
            
            # Update timestamps
            existing.last_seen = datetime.utcnow()
            
            await self.storage.update_relationship(existing)
            return existing
        
        # Create new relationship
        rel = GraphRelationship(
            id=f"{source_id}:{target_id}:{relationship_type.value}",
            source_id=source_id,
            target_id=target_id,
            relationship_type=relationship_type,
            confidence=confidence,
            sources=sources,
            evidence=evidence,
            metadata=metadata,
            valid_from=valid_from,
            valid_to=valid_to,
            first_seen=datetime.utcnow(),
            last_seen=datetime.utcnow(),
        )
        
        await self.storage.add_relationship(rel)
        return rel
```

---

## Visualization

### D3.js Network Graph

```python
# entity_master/graph/visualization.py


def generate_d3_graph(network: dict) -> dict:
    """Convert network data to D3.js force graph format.
    
    Args:
        network: {"nodes": [...], "edges": [...]}
    
    Returns:
        D3.js compatible format
    """
    # Node formatting
    d3_nodes = []
    for node in network["nodes"]:
        d3_nodes.append({
            "id": node["id"],
            "name": node.get("name", node["id"]),
            "group": node.get("entity_type", "unknown"),
            "size": _calculate_node_size(node),
            "color": _get_entity_color(node.get("entity_type")),
        })
    
    # Edge formatting
    d3_links = []
    for edge in network["edges"]:
        d3_links.append({
            "source": edge["source"],
            "target": edge["target"],
            "type": edge["type"],
            "value": edge.get("confidence", 1.0),
        })
    
    return {
        "nodes": d3_nodes,
        "links": d3_links,
    }


def _calculate_node_size(node: dict) -> int:
    """Calculate node size based on importance."""
    if node.get("market_cap"):
        # Scale by market cap
        return max(5, min(50, int(node["market_cap"] / 10**11)))
    return 10


def _get_entity_color(entity_type: str) -> str:
    """Get color for entity type."""
    colors = {
        "company": "#4285F4",      # Blue
        "person": "#0F9D58",        # Green
        "security": "#F4B400",      # Yellow
        "fund": "#DB4437",          # Red
        "industry": "#9E9E9E",      # Gray
    }
    return colors.get(entity_type, "#9E9E9E")
```

### CLI Commands

```bash
# Get supply chain
entity-master graph supply-chain AAPL --depth 3

# Find connection between companies
entity-master graph path AAPL TSMC

# Get competitors
entity-master graph competitors AAPL --include-indirect

# Export for visualization
entity-master graph export AAPL --format d3 --output apple_network.json
entity-master graph export AAPL --format graphml --output apple.graphml

# Network analysis
entity-master graph centrality --top 20
entity-master graph communities
```

---

## Configuration

```yaml
# entity_master.yaml

graph:
  # Backend selection
  backend: neo4j  # neo4j, networkx (in-memory), memgraph
  
  # Neo4j configuration
  neo4j:
    uri: bolt://localhost:7687
    username: neo4j
    password: ${NEO4J_PASSWORD}
    database: entitymaster
  
  # Graph Data Science plugin
  gds:
    enabled: true
    project_name: company-graph
  
  # Visualization
  visualization:
    default_format: d3
    max_nodes: 500
    
  # Relationship sources
  sources:
    # GLEIF relationship records
    gleif_rr:
      enabled: true
      schedule: "0 0 1 * *"  # Monthly
    
    # SEC filing extraction
    sec_filings:
      enabled: true
      use_llm: true
      forms: ["10-K", "10-Q", "8-K"]
    
    # News analysis
    news:
      enabled: false  # Tier 5
      providers: ["newsapi", "alpha_vantage"]
```
