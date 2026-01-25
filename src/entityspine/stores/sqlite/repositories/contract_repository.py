"""
Contract repository for SQLite store.

Handles all contract-related database operations following the Repository Pattern.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from entityspine.domain import Contract
from entityspine.stores.mappers import contract_to_row, row_to_contract

if TYPE_CHECKING:
    from ..connection import SqliteConnectionManager


class ContractRepository:
    """
    Repository for Contract CRUD operations.
    
    Single Responsibility: Contract database operations only.
    """

    def __init__(self, connection: SqliteConnectionManager):
        """
        Initialize repository with connection manager.
        
        Args:
            connection: Connection manager for database access.
        """
        self.conn = connection

    def save(self, contract: Contract) -> None:
        """
        Save or update a contract.
        
        Args:
            contract: Contract domain object to persist.
        """
        row = contract_to_row(contract)
        with self.conn.connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO contracts (
                    contract_id, contract_type, title, effective_date,
                    termination_date, status, value_usd, source_system,
                    source_id, filing_id, captured_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["contract_id"],
                    row["contract_type"],
                    row["title"],
                    row["effective_date"],
                    row["termination_date"],
                    row["status"],
                    row["value_usd"],
                    row["source_system"],
                    row["source_id"],
                    row["filing_id"],
                    row["captured_at"],
                    row["created_at"],
                    row["updated_at"],
                ),
            )
            conn.commit()

    def get_by_id(self, contract_id: str) -> Contract | None:
        """
        Get contract by ID.
        
        Args:
            contract_id: Contract ULID.
            
        Returns:
            Contract or None if not found.
        """
        row = self.conn.fetchone("SELECT * FROM contracts WHERE contract_id = ?", (contract_id,))
        return row_to_contract(dict(row)) if row else None

    def count(self) -> int:
        """
        Count total contracts.
        
        Returns:
            Number of contracts in database.
        """
        row = self.conn.fetchone("SELECT COUNT(*) as cnt FROM contracts")
        return row["cnt"] if row else 0
