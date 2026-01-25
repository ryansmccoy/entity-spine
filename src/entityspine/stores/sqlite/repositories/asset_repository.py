"""
Asset repository for SQLite store.

Handles all asset-related database operations following the Repository Pattern.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from entityspine.domain import Asset
from entityspine.stores.mappers import asset_to_row, row_to_asset

if TYPE_CHECKING:
    from ..connection import SqliteConnectionManager


class AssetRepository:
    """
    Repository for Asset CRUD operations.
    
    Single Responsibility: Asset database operations only.
    """

    def __init__(self, connection: "SqliteConnectionManager"):
        """
        Initialize repository with connection manager.
        
        Args:
            connection: Connection manager for database access.
        """
        self.conn = connection

    def save(self, asset: Asset) -> None:
        """
        Save or update an asset.
        
        Args:
            asset: Asset domain object to persist.
        """
        row = asset_to_row(asset)
        with self.conn.connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO assets (
                    asset_id, asset_type, name, description, owner_entity_id,
                    operator_entity_id, geo_id, address_id, status,
                    source_system, source_id, captured_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["asset_id"],
                    row["asset_type"],
                    row["name"],
                    row["description"],
                    row["owner_entity_id"],
                    row["operator_entity_id"],
                    row["geo_id"],
                    row["address_id"],
                    row["status"],
                    row["source_system"],
                    row["source_id"],
                    row["captured_at"],
                    row["created_at"],
                    row["updated_at"],
                ),
            )
            conn.commit()

    def get_by_id(self, asset_id: str) -> Asset | None:
        """
        Get asset by ID.
        
        Args:
            asset_id: Asset ULID.
            
        Returns:
            Asset or None if not found.
        """
        row = self.conn.fetchone("SELECT * FROM assets WHERE asset_id = ?", (asset_id,))
        return row_to_asset(dict(row)) if row else None

    def get_by_owner(self, entity_id: str) -> list[Asset]:
        """
        Get all assets owned by an entity.
        
        Args:
            entity_id: Owner entity ULID.
            
        Returns:
            List of assets owned by the entity.
        """
        rows = self.conn.fetchall(
            "SELECT * FROM assets WHERE owner_entity_id = ?",
            (entity_id,),
        )
        return [row_to_asset(dict(row)) for row in rows]

    def count(self) -> int:
        """
        Count total assets.
        
        Returns:
            Number of assets in database.
        """
        row = self.conn.fetchone("SELECT COUNT(*) as cnt FROM assets")
        return row["cnt"] if row else 0
