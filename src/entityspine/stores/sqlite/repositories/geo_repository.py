"""
Geo repository for SQLite store.

Handles all geographic location database operations following the Repository Pattern.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from entityspine.domain import Geo, GeoType

if TYPE_CHECKING:
    from ..connection import SqliteConnectionManager


class GeoRepository:
    """
    Repository for Geo CRUD operations.
    
    Single Responsibility: Geographic location database operations only.
    Represents country → state → city hierarchy.
    """

    def __init__(self, connection: "SqliteConnectionManager"):
        """
        Initialize repository with connection manager.
        
        Args:
            connection: Connection manager for database access.
        """
        self.conn = connection

    def save(self, geo: Geo) -> None:
        """
        Save or update a geographic location.
        
        Args:
            geo: Geo domain object to persist.
        """
        now = datetime.now(UTC).isoformat()
        geo_type = geo.geo_type.value if hasattr(geo.geo_type, "value") else geo.geo_type

        with self.conn.connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO geos (
                    geo_id, geo_type, name, iso_code, parent_geo_id,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    geo.geo_id,
                    geo_type,
                    geo.name,
                    geo.iso_code,
                    geo.parent_geo_id,
                    now,
                    now,
                ),
            )
            conn.commit()

    def get_by_id(self, geo_id: str) -> Geo | None:
        """
        Get geographic location by ID.
        
        Args:
            geo_id: Geo ULID.
            
        Returns:
            Geo or None if not found.
        """
        row = self.conn.fetchone("SELECT * FROM geos WHERE geo_id = ?", (geo_id,))
        if not row:
            return None
        return Geo(
            geo_id=row["geo_id"],
            geo_type=GeoType(row["geo_type"]),
            name=row["name"],
            iso_code=row["iso_code"],
            parent_geo_id=row["parent_geo_id"],
        )

    def count(self) -> int:
        """
        Count total geographic locations.
        
        Returns:
            Number of geos in database.
        """
        row = self.conn.fetchone("SELECT COUNT(*) as cnt FROM geos")
        return row["cnt"] if row else 0
