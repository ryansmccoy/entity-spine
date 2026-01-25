"""
Product repository for SQLite store.

Handles all product-related database operations following the Repository Pattern.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from entityspine.domain import Product
from entityspine.stores.mappers import product_to_row, row_to_product

if TYPE_CHECKING:
    from ..connection import SqliteConnectionManager


class ProductRepository:
    """
    Repository for Product CRUD operations.
    
    Single Responsibility: Product database operations only.
    """

    def __init__(self, connection: SqliteConnectionManager):
        """
        Initialize repository with connection manager.
        
        Args:
            connection: Connection manager for database access.
        """
        self.conn = connection

    def save(self, product: Product) -> None:
        """
        Save or update a product.
        
        Args:
            product: Product domain object to persist.
        """
        row = product_to_row(product)
        with self.conn.connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO products (
                    product_id, product_type, name, description, owner_entity_id,
                    status, source_system, source_id, captured_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["product_id"],
                    row["product_type"],
                    row["name"],
                    row["description"],
                    row["owner_entity_id"],
                    row["status"],
                    row["source_system"],
                    row["source_id"],
                    row["captured_at"],
                    row["created_at"],
                    row["updated_at"],
                ),
            )
            conn.commit()

    def get_by_id(self, product_id: str) -> Product | None:
        """
        Get product by ID.
        
        Args:
            product_id: Product ULID.
            
        Returns:
            Product or None if not found.
        """
        row = self.conn.fetchone("SELECT * FROM products WHERE product_id = ?", (product_id,))
        return row_to_product(dict(row)) if row else None

    def get_by_owner(self, entity_id: str) -> list[Product]:
        """
        Get all products owned by an entity.
        
        Args:
            entity_id: Owner entity ULID.
            
        Returns:
            List of products owned by the entity.
        """
        rows = self.conn.fetchall(
            "SELECT * FROM products WHERE owner_entity_id = ?",
            (entity_id,),
        )
        return [row_to_product(dict(row)) for row in rows]

    def count(self) -> int:
        """
        Count total products.
        
        Returns:
            Number of products in database.
        """
        row = self.conn.fetchone("SELECT COUNT(*) as cnt FROM products")
        return row["cnt"] if row else 0
