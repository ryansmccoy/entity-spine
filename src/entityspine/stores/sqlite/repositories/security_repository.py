"""
Security repository for SQLite store.

Handles all security-related database operations following the Repository Pattern.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from entityspine.core.timestamps import to_iso8601
from entityspine.domain import Security

from ..converters import row_to_security

if TYPE_CHECKING:
    from ..connection import SqliteConnectionManager


class SecurityRepository:
    """
    Repository for Security CRUD operations.
    
    Single Responsibility: Security database operations only.
    """

    def __init__(self, connection: SqliteConnectionManager):
        """
        Initialize repository with connection manager.
        
        Args:
            connection: Connection manager for database access.
        """
        self.conn = connection

    def save(self, security: Security) -> None:
        """
        Save or update a security.
        
        Args:
            security: Security domain object to persist.
        """
        security = security.with_update()
        now_str = to_iso8601(security.updated_at)

        self.conn.execute(
            """INSERT INTO securities
               (security_id, entity_id, security_type, status, description,
                source_system, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(security_id) DO UPDATE SET
                 entity_id = excluded.entity_id,
                 security_type = excluded.security_type,
                 status = excluded.status,
                 description = excluded.description,
                 source_system = excluded.source_system,
                 updated_at = excluded.updated_at""",
            (
                security.security_id,
                security.entity_id,
                security.security_type.value,
                security.status.value,
                security.description,
                security.source_system,
                to_iso8601(security.created_at),
                now_str,
            ),
        )

    def get_by_id(self, security_id: str) -> Security | None:
        """
        Get security by ID.
        
        Args:
            security_id: Security ULID.
            
        Returns:
            Security or None if not found.
        """
        row = self.conn.fetchone(
            "SELECT * FROM securities WHERE security_id = ?",
            (security_id,),
        )
        return row_to_security(row) if row else None

    def get_by_entity(self, entity_id: str) -> list[Security]:
        """
        Get all securities issued by an entity.
        
        Args:
            entity_id: Entity ULID.
            
        Returns:
            List of securities for the entity.
        """
        rows = self.conn.fetchall(
            "SELECT * FROM securities WHERE entity_id = ?",
            (entity_id,),
        )
        return [row_to_security(row) for row in rows]

    def count(self) -> int:
        """
        Count total securities.
        
        Returns:
            Number of securities in database.
        """
        row = self.conn.fetchone("SELECT COUNT(*) as cnt FROM securities")
        return row["cnt"] if row else 0
