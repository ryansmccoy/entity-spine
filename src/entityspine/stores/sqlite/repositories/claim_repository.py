"""
Claim repository for SQLite store.

Handles all identifier claim-related database operations following the Repository Pattern.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from entityspine.core.timestamps import to_iso8601
from entityspine.domain import ClaimStatus, IdentifierClaim, IdentifierScheme, VendorNamespace

from ..converters import row_to_claim

if TYPE_CHECKING:
    from ..connection import SqliteConnectionManager


class ClaimRepository:
    """
    Repository for IdentifierClaim CRUD operations.
    
    Single Responsibility: Identifier claim database operations only.
    Claims are the source of truth for identifiers (CIK, CUSIP, ISIN, etc.).
    """

    def __init__(self, connection: "SqliteConnectionManager"):
        """
        Initialize repository with connection manager.
        
        Args:
            connection: Connection manager for database access.
        """
        self.conn = connection

    def save(self, claim: IdentifierClaim) -> None:
        """
        Save or update an identifier claim.
        
        Args:
            claim: IdentifierClaim domain object to persist.
        """
        claim = claim.with_update()
        now_str = to_iso8601(claim.updated_at)

        scheme_val = (
            claim.scheme.value if isinstance(claim.scheme, IdentifierScheme) else str(claim.scheme)
        )
        namespace_val = (
            claim.namespace.value
            if isinstance(claim.namespace, VendorNamespace)
            else str(claim.namespace)
        )
        status_val = (
            claim.status.value if isinstance(claim.status, ClaimStatus) else str(claim.status)
        )

        self.conn.execute(
            """INSERT INTO claims
               (claim_id, entity_id, security_id, listing_id, scheme, value,
                namespace, status, confidence, source, valid_from, valid_to,
                captured_at, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(claim_id) DO UPDATE SET
                 entity_id = excluded.entity_id,
                 security_id = excluded.security_id,
                 listing_id = excluded.listing_id,
                 scheme = excluded.scheme,
                 value = excluded.value,
                 namespace = excluded.namespace,
                 status = excluded.status,
                 confidence = excluded.confidence,
                 source = excluded.source,
                 valid_from = excluded.valid_from,
                 valid_to = excluded.valid_to,
                 captured_at = excluded.captured_at,
                 updated_at = excluded.updated_at""",
            (
                claim.claim_id,
                claim.entity_id,
                claim.security_id,
                claim.listing_id,
                scheme_val,
                claim.value,
                namespace_val,
                status_val,
                claim.confidence,
                claim.source,
                claim.valid_from.isoformat() if claim.valid_from else None,
                claim.valid_to.isoformat() if claim.valid_to else None,
                to_iso8601(claim.captured_at),
                to_iso8601(claim.created_at),
                now_str,
            ),
        )

    def get(self, scheme: str, value: str) -> list[IdentifierClaim]:
        """
        Get claims matching scheme and value.
        
        Args:
            scheme: Identifier scheme (cik, ticker, etc.).
            value: Identifier value.
            
        Returns:
            List of matching IdentifierClaim objects.
        """
        rows = self.conn.fetchall(
            "SELECT * FROM claims WHERE scheme = ? AND value = ?",
            (scheme.lower(), value),
        )
        return [row_to_claim(row) for row in rows]

    def get_for_entity(self, entity_id: str) -> list[IdentifierClaim]:
        """
        Get all identifier claims for an entity.
        
        Args:
            entity_id: Entity ULID.
            
        Returns:
            List of claims associated with the entity.
        """
        rows = self.conn.fetchall(
            "SELECT * FROM claims WHERE entity_id = ?",
            (entity_id,),
        )
        return [row_to_claim(row) for row in rows]

    def get_by_value(
        self,
        scheme: IdentifierScheme,
        value: str,
    ) -> list[IdentifierClaim]:
        """
        Get claims by scheme and value.
        
        Args:
            scheme: Identifier scheme enum.
            value: Identifier value.
            
        Returns:
            List of matching claims.
        """
        scheme_str = scheme.value if hasattr(scheme, "value") else scheme
        rows = self.conn.fetchall(
            "SELECT * FROM claims WHERE scheme = ? AND value = ?",
            (scheme_str, value),
        )
        return [row_to_claim(row) for row in rows]

    def count(self) -> int:
        """
        Count total claims.
        
        Returns:
            Number of claims in database.
        """
        row = self.conn.fetchone("SELECT COUNT(*) as cnt FROM claims")
        return row["cnt"] if row else 0
