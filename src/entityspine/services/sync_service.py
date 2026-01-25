"""
Data Sync Service for EntitySpine (Tier 4/5).

Coordinates synchronization from PostgreSQL (source of truth) to:
- Elasticsearch (search index)
- Neo4j (graph replica)

Sync Strategies:
1. Full sync - Initial load or recovery
2. Incremental sync - Based on updated_at timestamps
3. CDC (Change Data Capture) - Real-time via PostgreSQL triggers/NOTIFY

Usage:
    from entityspine.services.sync_service import SyncService
    
    sync = SyncService(
        pg_store=postgres_store,
        es_store=elasticsearch_store,
        neo4j_store=neo4j_store,
    )
    
    # Full sync (initial load)
    await sync.full_sync()
    
    # Incremental sync (periodic)
    await sync.incremental_sync(since=last_sync_time)
    
    # Single entity sync (real-time)
    await sync.sync_entity(entity_id)
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from entityspine.stores.elasticsearch_store import ElasticsearchStore
    from entityspine.stores.neo4j_store import Neo4jStore


@dataclass
class SyncResult:
    """Result of a sync operation."""

    started_at: datetime
    completed_at: datetime | None = None
    entities_synced: int = 0
    relationships_synced: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return len(self.errors) == 0

    @property
    def duration_seconds(self) -> float:
        if not self.completed_at:
            return 0
        return (self.completed_at - self.started_at).total_seconds()

    def to_dict(self) -> dict:
        return {
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "entities_synced": self.entities_synced,
            "relationships_synced": self.relationships_synced,
            "errors": self.errors,
            "warnings": self.warnings,
            "success": self.success,
        }


class SyncService:
    """
    Coordinates data synchronization from PostgreSQL to downstream stores.

    PostgreSQL is the source of truth. Elasticsearch and Neo4j are
    eventually consistent replicas optimized for their specific use cases.

    Conflict Resolution:
    - PostgreSQL always wins
    - Downstream discrepancies trigger re-sync
    - Discrepancies are logged for investigation
    """

    def __init__(
        self,
        pg_store: Any,
        es_store: "ElasticsearchStore | None" = None,
        neo4j_store: "Neo4jStore | None" = None,
        batch_size: int = 1000,
    ):
        """
        Initialize sync service.

        Args:
            pg_store: PostgreSQL store (source of truth)
            es_store: Optional Elasticsearch store
            neo4j_store: Optional Neo4j store
            batch_size: Number of entities per batch
        """
        self.pg_store = pg_store
        self.es_store = es_store
        self.neo4j_store = neo4j_store
        self.batch_size = batch_size
        self._last_sync: datetime | None = None

    # =========================================================================
    # Full Sync
    # =========================================================================

    async def full_sync(self) -> SyncResult:
        """
        Perform full sync from PostgreSQL to all downstream stores.

        Use for:
        - Initial data load
        - Recovery after failures
        - Periodic full reconciliation
        """
        result = SyncResult(started_at=datetime.utcnow())
        logger.info("Starting full sync from PostgreSQL")

        try:
            # Sync to Elasticsearch
            if self.es_store:
                es_result = await self._sync_entities_to_elasticsearch()
                result.entities_synced += es_result["synced"]
                if es_result.get("errors"):
                    result.errors.extend(es_result["errors"])

            # Sync to Neo4j
            if self.neo4j_store:
                neo4j_result = await self._sync_to_neo4j()
                result.entities_synced += neo4j_result.get("entities", 0)
                result.relationships_synced = neo4j_result.get("relationships", 0)
                if neo4j_result.get("errors"):
                    result.errors.extend(neo4j_result["errors"])

            result.completed_at = datetime.utcnow()
            self._last_sync = result.completed_at
            logger.info(
                f"Full sync completed: {result.entities_synced} entities, "
                f"{result.relationships_synced} relationships in {result.duration_seconds:.2f}s"
            )

        except Exception as e:
            result.errors.append(str(e))
            result.completed_at = datetime.utcnow()
            logger.error(f"Full sync failed: {e}")

        return result

    async def _sync_entities_to_elasticsearch(self) -> dict:
        """Sync all entities to Elasticsearch."""
        if not self.es_store:
            return {"synced": 0}

        synced = 0
        errors = []

        try:
            # Get all entities from PostgreSQL
            # This assumes pg_store has an iterator method
            if hasattr(self.pg_store, "iter_entities"):
                batch = []
                async for entity in self.pg_store.iter_entities():
                    # Get identifiers for this entity
                    identifiers = []
                    if hasattr(self.pg_store, "get_identifiers"):
                        identifiers = await self.pg_store.get_identifiers(entity.entity_id)

                    batch.append((entity, identifiers))

                    if len(batch) >= self.batch_size:
                        result = await self.es_store.bulk_index(batch)
                        synced += result["success"]
                        if result["failed"]:
                            errors.append(f"Failed to index {result['failed']} entities")
                        batch = []

                # Index remaining batch
                if batch:
                    result = await self.es_store.bulk_index(batch)
                    synced += result["success"]

            elif hasattr(self.pg_store, "get_all_entities"):
                entities = self.pg_store.get_all_entities()
                batch = [(e, []) for e in entities]
                for i in range(0, len(batch), self.batch_size):
                    chunk = batch[i : i + self.batch_size]
                    result = await self.es_store.bulk_index(chunk)
                    synced += result["success"]

        except Exception as e:
            errors.append(f"Elasticsearch sync error: {e}")
            logger.error(f"Elasticsearch sync error: {e}")

        return {"synced": synced, "errors": errors}

    async def _sync_to_neo4j(self) -> dict:
        """Sync all entities and relationships to Neo4j."""
        if not self.neo4j_store:
            return {"entities": 0, "relationships": 0}

        entities_synced = 0
        relationships_synced = 0
        errors = []

        try:
            # Sync entities
            if hasattr(self.pg_store, "iter_entities"):
                async for entity in self.pg_store.iter_entities():
                    await self.neo4j_store.upsert_entity(entity)
                    entities_synced += 1

            # Sync relationships
            if hasattr(self.pg_store, "iter_relationships"):
                async for rel in self.pg_store.iter_relationships():
                    rel_type = rel.relationship_type.value if hasattr(rel.relationship_type, "value") else str(rel.relationship_type)
                    await self.neo4j_store.upsert_relationship(
                        source_id=rel.source_entity_id,
                        target_id=rel.target_entity_id,
                        relationship_type=rel_type.upper(),
                    )
                    relationships_synced += 1

        except Exception as e:
            errors.append(f"Neo4j sync error: {e}")
            logger.error(f"Neo4j sync error: {e}")

        return {
            "entities": entities_synced,
            "relationships": relationships_synced,
            "errors": errors,
        }

    # =========================================================================
    # Incremental Sync
    # =========================================================================

    async def incremental_sync(
        self,
        since: datetime | None = None,
    ) -> SyncResult:
        """
        Sync only entities/relationships updated since a given time.

        Args:
            since: Sync changes since this time. Defaults to last sync time.

        Use for:
        - Periodic sync jobs (every N minutes)
        - Catching up after downtime
        """
        if since is None:
            since = self._last_sync or (datetime.utcnow() - timedelta(hours=1))

        result = SyncResult(started_at=datetime.utcnow())
        logger.info(f"Starting incremental sync since {since}")

        try:
            # Get updated entities
            if hasattr(self.pg_store, "get_entities_updated_since"):
                entities = await self.pg_store.get_entities_updated_since(since)

                for entity in entities:
                    await self.sync_entity(entity.entity_id)
                    result.entities_synced += 1

            # Get updated relationships
            if hasattr(self.pg_store, "get_relationships_updated_since"):
                relationships = await self.pg_store.get_relationships_updated_since(since)

                for rel in relationships:
                    await self._sync_relationship(rel)
                    result.relationships_synced += 1

            result.completed_at = datetime.utcnow()
            self._last_sync = result.completed_at
            logger.info(
                f"Incremental sync completed: {result.entities_synced} entities, "
                f"{result.relationships_synced} relationships"
            )

        except Exception as e:
            result.errors.append(str(e))
            result.completed_at = datetime.utcnow()
            logger.error(f"Incremental sync failed: {e}")

        return result

    # =========================================================================
    # Single Entity Sync
    # =========================================================================

    async def sync_entity(self, entity_id: str) -> bool:
        """
        Sync a single entity to all downstream stores.

        Use for:
        - Real-time sync after entity creation/update
        - CDC (Change Data Capture) handling
        """
        try:
            # Get entity from PostgreSQL
            entity = None
            if hasattr(self.pg_store, "get_entity"):
                entity = self.pg_store.get_entity(entity_id)
            elif hasattr(self.pg_store, "get_entity_async"):
                entity = await self.pg_store.get_entity_async(entity_id)

            if not entity:
                logger.warning(f"Entity not found in PostgreSQL: {entity_id}")
                return False

            # Get identifiers
            identifiers = []
            if hasattr(self.pg_store, "get_identifiers"):
                identifiers = self.pg_store.get_identifiers(entity_id)

            # Sync to Elasticsearch
            if self.es_store:
                await self.es_store.index_entity(entity, identifiers)

            # Sync to Neo4j
            if self.neo4j_store:
                await self.neo4j_store.upsert_entity(entity)

                # Also sync relationships for this entity
                if hasattr(self.pg_store, "get_relationships_for_entity"):
                    relationships = self.pg_store.get_relationships_for_entity(entity_id)
                    for rel in relationships:
                        await self._sync_relationship(rel)

            logger.debug(f"Synced entity: {entity_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to sync entity {entity_id}: {e}")
            return False

    async def _sync_relationship(self, relationship: Any) -> bool:
        """Sync a single relationship to Neo4j."""
        if not self.neo4j_store:
            return True

        try:
            rel_type = relationship.relationship_type
            if hasattr(rel_type, "value"):
                rel_type = rel_type.value
            rel_type = str(rel_type).upper().replace("-", "_")

            props = {}
            if hasattr(relationship, "ownership_percentage") and relationship.ownership_percentage:
                props["ownership_percentage"] = float(relationship.ownership_percentage)

            await self.neo4j_store.upsert_relationship(
                source_id=relationship.source_entity_id,
                target_id=relationship.target_entity_id,
                relationship_type=rel_type,
                properties=props,
            )
            return True

        except Exception as e:
            logger.error(f"Failed to sync relationship: {e}")
            return False

    # =========================================================================
    # Delete Sync
    # =========================================================================

    async def delete_entity(self, entity_id: str) -> bool:
        """
        Delete an entity from all downstream stores.

        Call this when an entity is deleted from PostgreSQL.
        """
        try:
            if self.es_store:
                await self.es_store.delete_entity(entity_id)

            if self.neo4j_store:
                await self.neo4j_store.delete_entity(entity_id)

            logger.debug(f"Deleted entity from downstream stores: {entity_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete entity {entity_id}: {e}")
            return False

    # =========================================================================
    # Health & Stats
    # =========================================================================

    async def check_health(self) -> dict:
        """Check health of all stores."""
        health = {
            "postgresql": "unknown",
            "elasticsearch": "unknown",
            "neo4j": "unknown",
        }

        # Check PostgreSQL
        try:
            if hasattr(self.pg_store, "count_entities"):
                self.pg_store.count_entities()
            health["postgresql"] = "healthy"
        except Exception as e:
            health["postgresql"] = f"unhealthy: {e}"

        # Check Elasticsearch
        if self.es_store:
            try:
                await self.es_store.count()
                health["elasticsearch"] = "healthy"
            except Exception as e:
                health["elasticsearch"] = f"unhealthy: {e}"
        else:
            health["elasticsearch"] = "not_configured"

        # Check Neo4j
        if self.neo4j_store:
            try:
                await self.neo4j_store.count_nodes()
                health["neo4j"] = "healthy"
            except Exception as e:
                health["neo4j"] = f"unhealthy: {e}"
        else:
            health["neo4j"] = "not_configured"

        return health

    async def get_sync_stats(self) -> dict:
        """Get counts from all stores for comparison."""
        stats = {
            "postgresql": {},
            "elasticsearch": {},
            "neo4j": {},
            "in_sync": True,
            "discrepancies": [],
        }

        # PostgreSQL counts
        pg_entity_count = 0
        if hasattr(self.pg_store, "count_entities"):
            pg_entity_count = self.pg_store.count_entities()
        stats["postgresql"]["entities"] = pg_entity_count

        # Elasticsearch counts
        if self.es_store:
            try:
                es_count = await self.es_store.count()
                stats["elasticsearch"]["entities"] = es_count

                if es_count != pg_entity_count:
                    stats["in_sync"] = False
                    stats["discrepancies"].append(
                        f"ES entity count ({es_count}) != PG count ({pg_entity_count})"
                    )
            except Exception as e:
                stats["elasticsearch"]["error"] = str(e)

        # Neo4j counts
        if self.neo4j_store:
            try:
                neo4j_stats = await self.neo4j_store.stats()
                stats["neo4j"] = neo4j_stats

                neo4j_entity_count = neo4j_stats.get("entity_count", 0)
                if neo4j_entity_count != pg_entity_count:
                    stats["in_sync"] = False
                    stats["discrepancies"].append(
                        f"Neo4j entity count ({neo4j_entity_count}) != PG count ({pg_entity_count})"
                    )
            except Exception as e:
                stats["neo4j"]["error"] = str(e)

        stats["last_sync"] = self._last_sync.isoformat() if self._last_sync else None

        return stats
