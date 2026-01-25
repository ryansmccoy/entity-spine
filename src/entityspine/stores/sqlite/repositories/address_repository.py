"""
Address repository for SQLite store.

Handles all address-related database operations following the Repository Pattern.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from entityspine.domain import Address, AddressType

if TYPE_CHECKING:
    from ..connection import SqliteConnectionManager


class AddressRepository:
    """
    Repository for Address CRUD operations.
    
    Single Responsibility: Address database operations only.
    Uses normalized hash for deduplication.
    """

    def __init__(self, connection: "SqliteConnectionManager"):
        """
        Initialize repository with connection manager.
        
        Args:
            connection: Connection manager for database access.
        """
        self.conn = connection

    def save(self, address: Address) -> None:
        """
        Save or update an address.
        
        Args:
            address: Address domain object to persist.
        """
        now = datetime.now(UTC).isoformat()

        with self.conn.connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO addresses (
                    address_id, line1, line2, city, region, postal,
                    country, normalized_hash, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    address.address_id,
                    address.line1,
                    address.line2,
                    address.city,
                    address.region,
                    address.postal,
                    address.country,
                    address.normalized_hash,
                    now,
                    now,
                ),
            )
            conn.commit()

    def get_by_id(self, address_id: str) -> Address | None:
        """
        Get address by ID.
        
        Args:
            address_id: Address ULID.
            
        Returns:
            Address or None if not found.
        """
        row = self.conn.fetchone("SELECT * FROM addresses WHERE address_id = ?", (address_id,))
        if not row:
            return None
        return Address(
            address_id=row["address_id"],
            line1=row["line1"],
            line2=row["line2"],
            city=row["city"],
            region=row["region"],
            postal=row["postal"],
            country=row["country"],
            normalized_hash=row["normalized_hash"],
        )

    def get_by_hash(self, normalized_hash: str) -> Address | None:
        """
        Get address by normalized hash for deduplication.
        
        Args:
            normalized_hash: Hash of normalized address.
            
        Returns:
            Address or None if not found.
        """
        row = self.conn.fetchone(
            "SELECT * FROM addresses WHERE normalized_hash = ?",
            (normalized_hash,),
        )
        if not row:
            return None
        return Address(
            address_id=row["address_id"],
            line1=row["line1"],
            line2=row["line2"],
            city=row["city"],
            region=row["region"],
            postal=row["postal"],
            country=row["country"],
            normalized_hash=row["normalized_hash"],
        )

    def save_entity_address(
        self,
        entity_id: str,
        address_id: str,
        address_type: AddressType,
    ) -> None:
        """
        Link an entity to an address.
        
        Args:
            entity_id: Entity ULID.
            address_id: Address ULID.
            address_type: Type of address (business, mailing, etc.).
        """
        now = datetime.now(UTC).isoformat()
        type_value = address_type.value if hasattr(address_type, "value") else address_type

        with self.conn.connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO entity_addresses (
                    entity_id, address_id, address_type,
                    captured_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (entity_id, address_id, type_value, now, now, now),
            )
            conn.commit()

    def count(self) -> int:
        """
        Count total addresses.
        
        Returns:
            Number of addresses in database.
        """
        row = self.conn.fetchone("SELECT COUNT(*) as cnt FROM addresses")
        return row["cnt"] if row else 0
