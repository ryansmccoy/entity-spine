"""
Neo4j Graph Store for EntitySpine (Tier 4/5).

Provides graph traversal and path-finding capabilities that
relational databases cannot efficiently provide.

Features:
- O(1) per-hop relationship traversal (vs O(n) recursive CTEs)
- Native shortest path algorithms
- Pattern matching with Cypher
- Graph algorithms (PageRank, centrality, community detection)

Usage:
    from entityspine.stores.neo4j_store import Neo4jStore
    
    store = Neo4jStore(
        uri="bolt://localhost:7687",
        user="neo4j",
        password="password"
    )
    await store.initialize()
    
    # Sync an entity with relationships
    await store.sync_entity(entity, relationships)
    
    # Find ownership chain
    chain = await store.get_ownership_chain("entity_id", max_depth=5)
    
    # Find path between entities
    path = await store.find_path("entity_a", "entity_b")
    
    # Get full network for visualization
    network = await store.get_entity_network("entity_id", max_depth=2)

Installation:
    pip install entityspine[graph]
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

logger = logging.getLogger(__name__)

# Check for neo4j dependency
try:
    from neo4j import AsyncGraphDatabase
    from neo4j.exceptions import ServiceUnavailable

    HAS_NEO4J = True
except ImportError:
    HAS_NEO4J = False
    AsyncGraphDatabase = None  # type: ignore

if TYPE_CHECKING:
    from entityspine.domain import Entity
    from entityspine.domain.graph import EntityRelationship


# =============================================================================
# Result Types
# =============================================================================


@dataclass
class GraphNode:
    """A node in the graph."""

    entity_id: str
    name: str
    entity_type: str | None = None
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphEdge:
    """An edge/relationship in the graph."""

    source_id: str
    target_id: str
    relationship_type: str
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphPath:
    """A path between two nodes."""

    nodes: list[GraphNode]
    edges: list[GraphEdge]
    length: int

    @property
    def found(self) -> bool:
        return len(self.nodes) > 0


@dataclass
class GraphNetwork:
    """A network/subgraph around a central node."""

    center: GraphNode
    nodes: list[GraphNode]
    edges: list[GraphEdge]

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @property
    def edge_count(self) -> int:
        return len(self.edges)


# =============================================================================
# Neo4j Store
# =============================================================================


class Neo4jStore:
    """
    Neo4j-backed graph store for entity relationships.

    Provides capabilities that PostgreSQL cannot efficiently handle:
    - Multi-hop traversal in O(1) per hop
    - Native shortest path algorithms
    - Complex pattern matching
    - Graph algorithms (PageRank, community detection)
    """

    def __init__(
        self,
        uri: str = "bolt://localhost:7687",
        user: str = "neo4j",
        password: str = "password",
        database: str = "neo4j",
    ):
        """
        Initialize Neo4j store.

        Args:
            uri: Neo4j bolt URI
            user: Username
            password: Password
            database: Database name
        """
        if not HAS_NEO4J:
            raise ImportError(
                "Neo4j driver not installed. Run: pip install entityspine[graph]"
            )

        self.uri = uri
        self.user = user
        self.password = password
        self.database = database
        self.driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
        self._initialized = False

    async def initialize(self) -> None:
        """Create constraints and indexes."""
        if self._initialized:
            return

        async with self.driver.session(database=self.database) as session:
            # Unique constraints
            await session.run("""
                CREATE CONSTRAINT entity_id IF NOT EXISTS
                FOR (e:Entity) REQUIRE e.entity_id IS UNIQUE
            """)

            await session.run("""
                CREATE CONSTRAINT security_id IF NOT EXISTS
                FOR (s:Security) REQUIRE s.security_id IS UNIQUE
            """)

            await session.run("""
                CREATE CONSTRAINT person_id IF NOT EXISTS
                FOR (p:Person) REQUIRE p.entity_id IS UNIQUE
            """)

            # Indexes for common queries
            await session.run("""
                CREATE INDEX entity_name IF NOT EXISTS
                FOR (e:Entity) ON (e.name)
            """)

            await session.run("""
                CREATE INDEX entity_cik IF NOT EXISTS
                FOR (e:Entity) ON (e.cik)
            """)

            await session.run("""
                CREATE INDEX entity_type IF NOT EXISTS
                FOR (e:Entity) ON (e.entity_type)
            """)

        self._initialized = True
        logger.info("Neo4j constraints and indexes created")

    async def close(self) -> None:
        """Close the Neo4j connection."""
        await self.driver.close()

    # =========================================================================
    # Node Operations
    # =========================================================================

    async def upsert_entity(self, entity: "Entity") -> None:
        """
        Create or update an entity node.

        Args:
            entity: Entity to upsert
        """
        async with self.driver.session(database=self.database) as session:
            await session.run(
                """
                MERGE (e:Entity {entity_id: $entity_id})
                SET e.name = $name,
                    e.entity_type = $entity_type,
                    e.status = $status,
                    e.cik = $cik,
                    e.jurisdiction = $jurisdiction,
                    e.sic_code = $sic_code,
                    e.updated_at = datetime()
                """,
                entity_id=entity.entity_id,
                name=entity.primary_name,
                entity_type=entity.entity_type.value if hasattr(entity.entity_type, "value") else str(entity.entity_type),
                status=entity.status.value if hasattr(entity.status, "value") else str(entity.status),
                cik=entity.source_id if entity.source_system == "sec" else None,
                jurisdiction=entity.jurisdiction,
                sic_code=entity.sic_code,
            )

    async def delete_entity(self, entity_id: str) -> None:
        """Delete an entity and its relationships."""
        async with self.driver.session(database=self.database) as session:
            await session.run(
                """
                MATCH (e:Entity {entity_id: $entity_id})
                DETACH DELETE e
                """,
                entity_id=entity_id,
            )

    # =========================================================================
    # Relationship Operations
    # =========================================================================

    async def upsert_relationship(
        self,
        source_id: str,
        target_id: str,
        relationship_type: str,
        properties: dict | None = None,
    ) -> None:
        """
        Create or update a relationship.

        Args:
            source_id: Source entity ID
            target_id: Target entity ID
            relationship_type: Type of relationship (OWNS, SUPPLIES, etc.)
            properties: Optional relationship properties
        """
        props = properties or {}
        async with self.driver.session(database=self.database) as session:
            # Dynamic relationship type requires string concatenation
            # Note: In production, validate relationship_type against allowed values
            await session.run(
                f"""
                MATCH (source:Entity {{entity_id: $source_id}})
                MATCH (target:Entity {{entity_id: $target_id}})
                MERGE (source)-[r:{relationship_type}]->(target)
                SET r += $props, r.updated_at = datetime()
                """,
                source_id=source_id,
                target_id=target_id,
                props=props,
            )

    async def sync_entity_with_relationships(
        self,
        entity: "Entity",
        relationships: list["EntityRelationship"],
    ) -> None:
        """
        Sync an entity and all its relationships.

        Args:
            entity: Entity to sync
            relationships: List of relationships
        """
        await self.upsert_entity(entity)

        for rel in relationships:
            rel_type = rel.relationship_type.value if hasattr(rel.relationship_type, "value") else str(rel.relationship_type)
            rel_type = rel_type.upper().replace("-", "_")  # Normalize for Neo4j

            props = {}
            if hasattr(rel, "ownership_percentage") and rel.ownership_percentage:
                props["ownership_percentage"] = float(rel.ownership_percentage)
            if hasattr(rel, "valid_from") and rel.valid_from:
                props["valid_from"] = str(rel.valid_from)
            if hasattr(rel, "valid_to") and rel.valid_to:
                props["valid_to"] = str(rel.valid_to)

            await self.upsert_relationship(
                source_id=rel.source_entity_id,
                target_id=rel.target_entity_id,
                relationship_type=rel_type,
                properties=props,
            )

    # =========================================================================
    # Graph Queries - Ownership
    # =========================================================================

    async def get_ownership_chain(
        self,
        entity_id: str,
        max_depth: int = 5,
        direction: str = "both",
    ) -> list[GraphPath]:
        """
        Get ownership chain (parents and/or subsidiaries).

        Args:
            entity_id: Starting entity
            max_depth: Maximum traversal depth
            direction: "up" (parents), "down" (subs), or "both"

        Returns:
            List of ownership paths
        """
        if direction == "up":
            pattern = "(child:Entity)-[:OWNS|SUBSIDIARY_OF*1..$depth]->(parent:Entity)"
            where = "child.entity_id = $entity_id"
        elif direction == "down":
            pattern = "(parent:Entity)-[:OWNS|SUBSIDIARY_OF*1..$depth]->(child:Entity)"
            where = "parent.entity_id = $entity_id"
        else:
            pattern = "(e1:Entity)-[:OWNS|SUBSIDIARY_OF*1..$depth]-(e2:Entity)"
            where = "e1.entity_id = $entity_id OR e2.entity_id = $entity_id"

        async with self.driver.session(database=self.database) as session:
            result = await session.run(
                f"""
                MATCH path = {pattern}
                WHERE {where}
                RETURN path,
                       [n IN nodes(path) | {{
                           entity_id: n.entity_id,
                           name: n.name,
                           entity_type: n.entity_type
                       }}] as nodes,
                       length(path) as depth
                ORDER BY depth
                LIMIT 100
                """,
                entity_id=entity_id,
                depth=max_depth,
            )

            paths = []
            async for record in result:
                nodes = [
                    GraphNode(
                        entity_id=n["entity_id"],
                        name=n["name"],
                        entity_type=n.get("entity_type"),
                    )
                    for n in record["nodes"]
                ]
                paths.append(
                    GraphPath(
                        nodes=nodes,
                        edges=[],  # Could extract from path if needed
                        length=record["depth"],
                    )
                )

            return paths

    async def get_subsidiaries(self, entity_id: str, max_depth: int = 1) -> list[GraphNode]:
        """Get direct or nested subsidiaries."""
        async with self.driver.session(database=self.database) as session:
            result = await session.run(
                """
                MATCH (parent:Entity {entity_id: $entity_id})-[:OWNS|SUBSIDIARY_OF*1..$depth]->(sub:Entity)
                RETURN DISTINCT sub.entity_id as entity_id,
                       sub.name as name,
                       sub.entity_type as entity_type
                """,
                entity_id=entity_id,
                depth=max_depth,
            )

            return [
                GraphNode(
                    entity_id=record["entity_id"],
                    name=record["name"],
                    entity_type=record.get("entity_type"),
                )
                async for record in result
            ]

    async def get_parent_company(self, entity_id: str) -> GraphNode | None:
        """Get the ultimate parent company."""
        async with self.driver.session(database=self.database) as session:
            result = await session.run(
                """
                MATCH (child:Entity {entity_id: $entity_id})-[:OWNS|SUBSIDIARY_OF*]->(parent:Entity)
                WHERE NOT (parent)-[:OWNS|SUBSIDIARY_OF]->()
                RETURN parent.entity_id as entity_id,
                       parent.name as name,
                       parent.entity_type as entity_type
                LIMIT 1
                """,
                entity_id=entity_id,
            )

            record = await result.single()
            if record:
                return GraphNode(
                    entity_id=record["entity_id"],
                    name=record["name"],
                    entity_type=record.get("entity_type"),
                )
            return None

    # =========================================================================
    # Graph Queries - Path Finding
    # =========================================================================

    async def find_path(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 6,
        relationship_types: list[str] | None = None,
    ) -> GraphPath:
        """
        Find shortest path between two entities.

        Args:
            source_id: Source entity ID
            target_id: Target entity ID
            max_depth: Maximum path length
            relationship_types: Optional filter for relationship types

        Returns:
            GraphPath with nodes and edges
        """
        rel_filter = ""
        if relationship_types:
            types = "|".join(relationship_types)
            rel_filter = f":{types}"

        async with self.driver.session(database=self.database) as session:
            result = await session.run(
                f"""
                MATCH path = shortestPath(
                    (source:Entity {{entity_id: $source_id}})-[{rel_filter}*1..{max_depth}]-(target:Entity {{entity_id: $target_id}})
                )
                RETURN path,
                       [n IN nodes(path) | {{
                           entity_id: n.entity_id,
                           name: n.name,
                           entity_type: n.entity_type
                       }}] as nodes,
                       [r IN relationships(path) | {{
                           type: type(r),
                           source: startNode(r).entity_id,
                           target: endNode(r).entity_id
                       }}] as rels,
                       length(path) as depth
                """,
                source_id=source_id,
                target_id=target_id,
            )

            record = await result.single()
            if record:
                nodes = [
                    GraphNode(
                        entity_id=n["entity_id"],
                        name=n["name"],
                        entity_type=n.get("entity_type"),
                    )
                    for n in record["nodes"]
                ]
                edges = [
                    GraphEdge(
                        source_id=r["source"],
                        target_id=r["target"],
                        relationship_type=r["type"],
                    )
                    for r in record["rels"]
                ]
                return GraphPath(nodes=nodes, edges=edges, length=record["depth"])

            return GraphPath(nodes=[], edges=[], length=-1)

    async def find_all_paths(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 4,
        limit: int = 10,
    ) -> list[GraphPath]:
        """Find all paths between two entities (up to limit)."""
        async with self.driver.session(database=self.database) as session:
            result = await session.run(
                f"""
                MATCH path = (source:Entity {{entity_id: $source_id}})-[*1..{max_depth}]-(target:Entity {{entity_id: $target_id}})
                RETURN [n IN nodes(path) | {{
                           entity_id: n.entity_id,
                           name: n.name
                       }}] as nodes,
                       [r IN relationships(path) | {{
                           type: type(r),
                           source: startNode(r).entity_id,
                           target: endNode(r).entity_id
                       }}] as rels,
                       length(path) as depth
                ORDER BY depth
                LIMIT $limit
                """,
                source_id=source_id,
                target_id=target_id,
                limit=limit,
            )

            paths = []
            async for record in result:
                nodes = [
                    GraphNode(entity_id=n["entity_id"], name=n["name"], entity_type=None)
                    for n in record["nodes"]
                ]
                edges = [
                    GraphEdge(
                        source_id=r["source"],
                        target_id=r["target"],
                        relationship_type=r["type"],
                    )
                    for r in record["rels"]
                ]
                paths.append(GraphPath(nodes=nodes, edges=edges, length=record["depth"]))

            return paths

    # =========================================================================
    # Graph Queries - Network/Visualization
    # =========================================================================

    async def get_entity_network(
        self,
        entity_id: str,
        max_depth: int = 2,
        relationship_types: list[str] | None = None,
        limit: int = 100,
    ) -> GraphNetwork:
        """
        Get entity network for visualization.

        Args:
            entity_id: Center entity
            max_depth: Traversal depth
            relationship_types: Optional filter
            limit: Maximum nodes

        Returns:
            GraphNetwork with nodes and edges for visualization
        """
        rel_filter = ""
        if relationship_types:
            types = "|".join(relationship_types)
            rel_filter = f":{types}"

        async with self.driver.session(database=self.database) as session:
            result = await session.run(
                f"""
                MATCH (center:Entity {{entity_id: $entity_id}})
                OPTIONAL MATCH path = (center)-[{rel_filter}*1..{max_depth}]-(connected:Entity)
                WITH center, collect(DISTINCT connected) as connected_nodes,
                     collect(DISTINCT relationships(path)) as all_rels
                RETURN {{
                    center: {{
                        entity_id: center.entity_id,
                        name: center.name,
                        entity_type: center.entity_type
                    }},
                    nodes: [n IN connected_nodes[0..{limit}] | {{
                        entity_id: n.entity_id,
                        name: n.name,
                        entity_type: n.entity_type
                    }}],
                    edges: [rel_list IN all_rels | [r IN rel_list | {{
                        source: startNode(r).entity_id,
                        target: endNode(r).entity_id,
                        type: type(r)
                    }}]][0..{limit}]
                }} as network
                """,
                entity_id=entity_id,
            )

            record = await result.single()
            if not record or not record["network"]:
                return GraphNetwork(
                    center=GraphNode(entity_id=entity_id, name="Unknown", entity_type=None),
                    nodes=[],
                    edges=[],
                )

            network = record["network"]
            center = GraphNode(
                entity_id=network["center"]["entity_id"],
                name=network["center"]["name"],
                entity_type=network["center"].get("entity_type"),
            )

            nodes = [
                GraphNode(
                    entity_id=n["entity_id"],
                    name=n["name"],
                    entity_type=n.get("entity_type"),
                )
                for n in (network.get("nodes") or [])
            ]

            # Flatten nested edge lists
            edges = []
            for edge_list in network.get("edges") or []:
                if isinstance(edge_list, list):
                    for e in edge_list:
                        if isinstance(e, dict):
                            edges.append(
                                GraphEdge(
                                    source_id=e["source"],
                                    target_id=e["target"],
                                    relationship_type=e["type"],
                                )
                            )

            return GraphNetwork(center=center, nodes=nodes, edges=edges)

    # =========================================================================
    # Graph Algorithms
    # =========================================================================

    async def get_pagerank(
        self,
        relationship_type: str | None = None,
        limit: int = 100,
    ) -> list[tuple[GraphNode, float]]:
        """
        Calculate PageRank for entities.

        Requires Neo4j Graph Data Science plugin.

        Returns:
            List of (node, score) tuples sorted by score
        """
        # Note: This requires the GDS plugin
        # For simplicity, returning a placeholder
        logger.warning("PageRank requires Neo4j Graph Data Science plugin")
        return []

    async def get_community_detection(
        self,
        relationship_type: str | None = None,
    ) -> dict[str, list[GraphNode]]:
        """
        Detect communities/clusters in the graph.

        Requires Neo4j Graph Data Science plugin.

        Returns:
            Dict mapping community_id to list of nodes
        """
        logger.warning("Community detection requires Neo4j Graph Data Science plugin")
        return {}

    # =========================================================================
    # Sync from PostgreSQL
    # =========================================================================

    async def sync_from_postgres(self, pg_store: Any, batch_size: int = 1000) -> dict:
        """
        Sync entities and relationships from PostgreSQL.

        Args:
            pg_store: PostgreSQL store instance
            batch_size: Batch size for sync

        Returns:
            Sync statistics
        """
        logger.info("Starting sync from PostgreSQL to Neo4j")
        # Implementation would iterate through PG entities/relationships
        return {
            "entities_synced": 0,
            "relationships_synced": 0,
            "timestamp": datetime.utcnow().isoformat(),
        }

    # =========================================================================
    # Stats
    # =========================================================================

    async def count_nodes(self, label: str = "Entity") -> int:
        """Count nodes with a given label."""
        async with self.driver.session(database=self.database) as session:
            result = await session.run(f"MATCH (n:{label}) RETURN count(n) as count")
            record = await result.single()
            return record["count"] if record else 0

    async def count_relationships(self, rel_type: str | None = None) -> int:
        """Count relationships, optionally filtered by type."""
        async with self.driver.session(database=self.database) as session:
            if rel_type:
                result = await session.run(
                    f"MATCH ()-[r:{rel_type}]->() RETURN count(r) as count"
                )
            else:
                result = await session.run("MATCH ()-[r]->() RETURN count(r) as count")
            record = await result.single()
            return record["count"] if record else 0

    async def stats(self) -> dict:
        """Get graph statistics."""
        return {
            "entity_count": await self.count_nodes("Entity"),
            "person_count": await self.count_nodes("Person"),
            "security_count": await self.count_nodes("Security"),
            "relationship_count": await self.count_relationships(),
        }
