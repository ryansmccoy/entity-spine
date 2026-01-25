"""
Role repository for SQLite store.

Handles all role assignment database operations following the Repository Pattern.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import TYPE_CHECKING

from entityspine.core.timestamps import to_iso8601, utc_now
from entityspine.domain import RoleAssignment, RoleType

if TYPE_CHECKING:
    from ..connection import SqliteConnectionManager


class RoleRepository:
    """
    Repository for RoleAssignment CRUD operations.
    
    Single Responsibility: Role assignment database operations only.
    Handles person → org role assignments with evidence.
    """

    def __init__(self, connection: SqliteConnectionManager):
        """
        Initialize repository with connection manager.
        
        Args:
            connection: Connection manager for database access.
        """
        self.conn = connection

    def save(self, role: RoleAssignment) -> None:
        """
        Save or update a role assignment.
        
        Args:
            role: RoleAssignment domain object to persist.
        """
        now_str = to_iso8601(utc_now())
        role_type = role.role_type.value if hasattr(role.role_type, "value") else role.role_type

        with self.conn.connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO role_assignments (
                    role_assignment_id, person_entity_id, org_entity_id,
                    role_type, title, start_date, end_date, confidence,
                    captured_at, source_system, source_ref, filing_id,
                    section_id, snippet_hash, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    role.role_assignment_id,
                    role.person_entity_id,
                    role.org_entity_id,
                    role_type,
                    role.title,
                    role.start_date.isoformat() if role.start_date else None,
                    role.end_date.isoformat() if role.end_date else None,
                    role.confidence,
                    to_iso8601(role.captured_at),
                    role.source_system,
                    role.source_ref,
                    role.filing_id,
                    role.section_id,
                    role.snippet_hash,
                    to_iso8601(role.created_at),
                    now_str,
                ),
            )
            conn.commit()

    def get_by_id(self, role_assignment_id: str) -> RoleAssignment | None:
        """
        Get role assignment by ID.
        
        Args:
            role_assignment_id: Role assignment ULID.
            
        Returns:
            RoleAssignment or None if not found.
        """
        row = self.conn.fetchone(
            "SELECT * FROM role_assignments WHERE role_assignment_id = ?",
            (role_assignment_id,),
        )
        if not row:
            return None

        return RoleAssignment(
            role_assignment_id=row["role_assignment_id"],
            person_entity_id=row["person_entity_id"],
            org_entity_id=row["org_entity_id"],
            role_type=RoleType(row["role_type"]),
            title=row["title"],
            start_date=date.fromisoformat(row["start_date"]) if row["start_date"] else None,
            end_date=date.fromisoformat(row["end_date"]) if row["end_date"] else None,
            confidence=row["confidence"],
            captured_at=datetime.fromisoformat(row["captured_at"])
            if row["captured_at"]
            else datetime.now(UTC),
            source_system=row["source_system"] or "unknown",
            source_ref=row["source_ref"],
            filing_id=row["filing_id"],
            section_id=row["section_id"],
            snippet_hash=row["snippet_hash"],
        )

    def get_by_org(self, org_entity_id: str) -> list[RoleAssignment]:
        """
        Get all role assignments for an organization.
        
        Args:
            org_entity_id: Organization entity ULID.
            
        Returns:
            List of role assignments for the org.
        """
        rows = self.conn.fetchall(
            "SELECT * FROM role_assignments WHERE org_entity_id = ?",
            (org_entity_id,),
        )
        return [self._row_to_role(row) for row in rows]

    def get_by_person(self, person_entity_id: str) -> list[RoleAssignment]:
        """
        Get all role assignments for a person.
        
        Args:
            person_entity_id: Person entity ULID.
            
        Returns:
            List of role assignments for the person.
        """
        rows = self.conn.fetchall(
            "SELECT * FROM role_assignments WHERE person_entity_id = ?",
            (person_entity_id,),
        )
        return [self._row_to_role(row) for row in rows]

    def get_with_filters(
        self,
        person_entity_id: str | None = None,
        org_entity_id: str | None = None,
        role_types: list | None = None,
        current_only: bool = False,
    ) -> list[RoleAssignment]:
        """
        Get role assignments with optional filters.
        
        Args:
            person_entity_id: Filter by person.
            org_entity_id: Filter by organization.
            role_types: Filter by role types.
            current_only: Only return current (no end_date) roles.
            
        Returns:
            List of RoleAssignment objects matching filters.
        """
        query_parts = ["SELECT * FROM role_assignments WHERE 1=1"]
        params: list = []

        if person_entity_id:
            query_parts.append("AND person_entity_id = ?")
            params.append(person_entity_id)

        if org_entity_id:
            query_parts.append("AND org_entity_id = ?")
            params.append(org_entity_id)

        if role_types:
            placeholders = ",".join("?" * len(role_types))
            query_parts.append(f"AND role_type IN ({placeholders})")
            for rt in role_types:
                params.append(rt.value if hasattr(rt, "value") else rt)

        if current_only:
            query_parts.append("AND (end_date IS NULL OR end_date >= ?)")
            params.append(date.today().isoformat())

        query = " ".join(query_parts)
        rows = self.conn.fetchall(query, tuple(params))
        return [self._row_to_role(row) for row in rows]

    def count(self) -> int:
        """
        Count total role assignments.
        
        Returns:
            Number of role assignments in database.
        """
        row = self.conn.fetchone("SELECT COUNT(*) as cnt FROM role_assignments")
        return row["cnt"] if row else 0

    def _row_to_role(self, row) -> RoleAssignment:
        """Convert database row to RoleAssignment."""
        return RoleAssignment(
            role_assignment_id=row["role_assignment_id"],
            person_entity_id=row["person_entity_id"],
            org_entity_id=row["org_entity_id"],
            role_type=RoleType(row["role_type"]),
            title=row["title"],
            start_date=date.fromisoformat(row["start_date"]) if row["start_date"] else None,
            end_date=date.fromisoformat(row["end_date"]) if row["end_date"] else None,
            confidence=row["confidence"],
            captured_at=datetime.fromisoformat(row["captured_at"])
            if row["captured_at"]
            else datetime.now(UTC),
            source_system=row["source_system"] or "unknown",
            source_ref=row["source_ref"],
            filing_id=row["filing_id"],
            section_id=row["section_id"],
            snippet_hash=row["snippet_hash"],
        )
