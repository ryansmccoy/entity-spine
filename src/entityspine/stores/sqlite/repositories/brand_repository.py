"""
Brand repository for SQLite store.

Handles all brand-related database operations following the Repository Pattern.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from entityspine.domain import Brand
from entityspine.stores.mappers import brand_to_row, row_to_brand

if TYPE_CHECKING:
    from ..connection import SqliteConnectionManager


class BrandRepository:
    """
    Repository for Brand CRUD operations.
    
    Single Responsibility: Brand database operations only.
    """

    def __init__(self, connection: SqliteConnectionManager):
        """
        Initialize repository with connection manager.
        
        Args:
            connection: Connection manager for database access.
        """
        self.conn = connection

    def save(self, brand: Brand) -> None:
        """
        Save or update a brand.
        
        Args:
            brand: Brand domain object to persist.
        """
        row = brand_to_row(brand)
        with self.conn.connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO brands (
                    brand_id, name, owner_entity_id, description,
                    source_system, source_id, captured_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["brand_id"],
                    row["name"],
                    row["owner_entity_id"],
                    row["description"],
                    row["source_system"],
                    row["source_id"],
                    row["captured_at"],
                    row["created_at"],
                    row["updated_at"],
                ),
            )
            conn.commit()

    def get_by_id(self, brand_id: str) -> Brand | None:
        """
        Get brand by ID.
        
        Args:
            brand_id: Brand ULID.
            
        Returns:
            Brand or None if not found.
        """
        row = self.conn.fetchone("SELECT * FROM brands WHERE brand_id = ?", (brand_id,))
        return row_to_brand(dict(row)) if row else None

    def get_by_owner(self, entity_id: str) -> list[Brand]:
        """
        Get all brands owned by an entity.
        
        Args:
            entity_id: Owner entity ULID.
            
        Returns:
            List of brands owned by the entity.
        """
        rows = self.conn.fetchall(
            "SELECT * FROM brands WHERE owner_entity_id = ?",
            (entity_id,),
        )
        return [row_to_brand(dict(row)) for row in rows]

    def count(self) -> int:
        """
        Count total brands.
        
        Returns:
            Number of brands in database.
        """
        row = self.conn.fetchone("SELECT COUNT(*) as cnt FROM brands")
        return row["cnt"] if row else 0
