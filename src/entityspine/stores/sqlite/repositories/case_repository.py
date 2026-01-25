"""
Case repository for SQLite store.

Handles all legal case database operations following the Repository Pattern.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from entityspine.domain import Case
from entityspine.stores.mappers import case_to_row, row_to_case

if TYPE_CHECKING:
    from ..connection import SqliteConnectionManager


class CaseRepository:
    """
    Repository for Case CRUD operations.
    
    Single Responsibility: Legal case database operations only.
    """

    def __init__(self, connection: "SqliteConnectionManager"):
        """
        Initialize repository with connection manager.
        
        Args:
            connection: Connection manager for database access.
        """
        self.conn = connection

    def save(self, case: Case) -> None:
        """
        Save or update a legal case.
        
        Args:
            case: Case domain object to persist.
        """
        row = case_to_row(case)
        with self.conn.connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO cases (
                    case_id, case_type, case_number, title, status,
                    authority_entity_id, target_entity_id,
                    opened_date, closed_date, description,
                    source_system, source_ref, filing_id, captured_at,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["case_id"],
                    row["case_type"],
                    row["case_number"],
                    row["title"],
                    row["status"],
                    row["authority_entity_id"],
                    row["target_entity_id"],
                    row["opened_date"],
                    row["closed_date"],
                    row["description"],
                    row["source_system"],
                    row["source_ref"],
                    row["filing_id"],
                    row["captured_at"],
                    row["created_at"],
                    row["updated_at"],
                ),
            )
            conn.commit()

    def get_by_id(self, case_id: str) -> Case | None:
        """
        Get case by ID.
        
        Args:
            case_id: Case ULID.
            
        Returns:
            Case or None if not found.
        """
        row = self.conn.fetchone(
            "SELECT * FROM cases WHERE case_id = ?",
            (case_id,),
        )
        return row_to_case(dict(row)) if row else None

    def get_by_target(self, target_entity_id: str) -> list[Case]:
        """
        Get all cases involving a target entity.
        
        Args:
            target_entity_id: Target entity ULID.
            
        Returns:
            List of cases targeting the entity.
        """
        rows = self.conn.fetchall(
            "SELECT * FROM cases WHERE target_entity_id = ?",
            (target_entity_id,),
        )
        return [row_to_case(dict(row)) for row in rows]

    def get_by_authority(self, authority_entity_id: str) -> list[Case]:
        """
        Get all cases from an authority (court/regulator).
        
        Args:
            authority_entity_id: Authority entity ULID.
            
        Returns:
            List of cases from the authority.
        """
        rows = self.conn.fetchall(
            "SELECT * FROM cases WHERE authority_entity_id = ?",
            (authority_entity_id,),
        )
        return [row_to_case(dict(row)) for row in rows]

    def count(self) -> int:
        """
        Count total cases.
        
        Returns:
            Number of cases in database.
        """
        row = self.conn.fetchone("SELECT COUNT(*) as cnt FROM cases")
        return row["cnt"] if row else 0
