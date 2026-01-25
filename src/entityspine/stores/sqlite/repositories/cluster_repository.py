"""
Cluster repository for SQLite store.

Handles all entity cluster database operations following the Repository Pattern.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from entityspine.domain import EntityCluster, EntityClusterMember
from entityspine.stores.mappers import (
    cluster_member_to_row,
    cluster_to_row,
    row_to_cluster,
    row_to_cluster_member,
)

if TYPE_CHECKING:
    from ..connection import SqliteConnectionManager


class ClusterRepository:
    """
    Repository for EntityCluster and EntityClusterMember CRUD operations.
    
    Single Responsibility: Entity clustering database operations only.
    Used for entity deduplication workflows.
    """

    def __init__(self, connection: SqliteConnectionManager):
        """
        Initialize repository with connection manager.
        
        Args:
            connection: Connection manager for database access.
        """
        self.conn = connection

    def save(self, cluster: EntityCluster) -> None:
        """
        Save or update an entity cluster.
        
        Args:
            cluster: EntityCluster domain object to persist.
        """
        row = cluster_to_row(cluster)
        with self.conn.connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO entity_clusters (
                    cluster_id, reason, created_at, updated_at
                ) VALUES (?, ?, ?, ?)
                """,
                (row["cluster_id"], row["reason"], row["created_at"], row["updated_at"]),
            )
            conn.commit()

    def get_by_id(self, cluster_id: str) -> EntityCluster | None:
        """
        Get cluster by ID.
        
        Args:
            cluster_id: Cluster ULID.
            
        Returns:
            EntityCluster or None if not found.
        """
        row = self.conn.fetchone(
            "SELECT * FROM entity_clusters WHERE cluster_id = ?",
            (cluster_id,),
        )
        return row_to_cluster(dict(row)) if row else None

    def get_by_status(self, status: str) -> list[EntityCluster]:
        """
        Get clusters by status (pending, approved, rejected, merged).
        
        Note: Would need status column added to clusters table.
        Currently returns all clusters.
        
        Args:
            status: Cluster status to filter by.
            
        Returns:
            List of clusters (currently all clusters).
        """
        # Note: Would need to add status column to clusters table
        # For now, return all clusters
        rows = self.conn.fetchall("SELECT * FROM entity_clusters", ())
        return [row_to_cluster(dict(row)) for row in rows]

    def count(self) -> int:
        """
        Count total entity clusters.
        
        Returns:
            Number of clusters in database.
        """
        row = self.conn.fetchone("SELECT COUNT(*) as cnt FROM entity_clusters")
        return row["cnt"] if row else 0

    # =========================================================================
    # Cluster Member Operations
    # =========================================================================

    def save_member(self, member: EntityClusterMember) -> None:
        """
        Save or update a cluster membership.
        
        Args:
            member: EntityClusterMember domain object to persist.
        """
        row = cluster_member_to_row(member)
        with self.conn.connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO entity_cluster_members (
                    cluster_id, entity_id, role, confidence, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    row["cluster_id"],
                    row["entity_id"],
                    row["role"],
                    row["confidence"],
                    row["created_at"],
                    row["updated_at"],
                ),
            )
            conn.commit()

    def get_members(self, cluster_id: str) -> list[EntityClusterMember]:
        """
        Get all members of a cluster.
        
        Args:
            cluster_id: Cluster ULID.
            
        Returns:
            List of cluster members.
        """
        rows = self.conn.fetchall(
            "SELECT * FROM entity_cluster_members WHERE cluster_id = ?",
            (cluster_id,),
        )
        return [row_to_cluster_member(dict(row)) for row in rows]

    def get_clusters_for_entity(self, entity_id: str) -> list[EntityClusterMember]:
        """
        Get all cluster memberships for an entity.
        
        Args:
            entity_id: Entity ULID.
            
        Returns:
            List of cluster memberships for the entity.
        """
        rows = self.conn.fetchall(
            "SELECT * FROM entity_cluster_members WHERE entity_id = ?",
            (entity_id,),
        )
        return [row_to_cluster_member(dict(row)) for row in rows]

    def member_count(self) -> int:
        """
        Count total cluster memberships.
        
        Returns:
            Number of cluster members in database.
        """
        row = self.conn.fetchone("SELECT COUNT(*) as cnt FROM entity_cluster_members")
        return row["cnt"] if row else 0
