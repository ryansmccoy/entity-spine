"""
Claim repository for database operations.
"""

from datetime import date

from sqlmodel import Session, or_, select

from entityspine.adapters.orm.repositories.base import BaseRepository
from entityspine.adapters.orm.tables import ClaimTable
from entityspine.adapters.pydantic.claim import ClaimStatus, IdentifierClaim, IdentifierScheme


class ClaimRepository(BaseRepository[ClaimTable]):
    """Repository for IdentifierClaim database operations."""

    def __init__(self, session: Session):
        """Initialize with ClaimTable model."""
        super().__init__(session, ClaimTable)

    def get_by_scheme_value(
        self,
        scheme: str,
        value: str,
        active_only: bool = True,
    ) -> list[ClaimTable]:
        """Get claims by scheme and value."""
        statement = select(ClaimTable).where(
            ClaimTable.scheme == scheme.lower(),
            ClaimTable.value == value,
        )

        if active_only:
            statement = statement.where(ClaimTable.status == "active")

        return list(self._session.exec(statement).all())

    def get_by_entity(self, entity_id: str) -> list[ClaimTable]:
        """Get all claims for an entity."""
        statement = select(ClaimTable).where(ClaimTable.entity_id == entity_id)
        return list(self._session.exec(statement).all())

    def get_valid_on_date(
        self,
        scheme: str,
        value: str,
        check_date: date,
    ) -> list[ClaimTable]:
        """Get claims valid on a specific date."""
        statement = select(ClaimTable).where(
            ClaimTable.scheme == scheme.lower(),
            ClaimTable.value == value,
            or_(ClaimTable.valid_from.is_(None), ClaimTable.valid_from <= check_date),
            or_(ClaimTable.valid_to.is_(None), ClaimTable.valid_to >= check_date),
        )
        return list(self._session.exec(statement).all())

    def to_domain(self, table: ClaimTable) -> IdentifierClaim:
        """Convert table row to domain model."""
        return IdentifierClaim(
            claim_id=table.claim_id,
            entity_id=table.entity_id,
            scheme=IdentifierScheme(table.scheme),
            value=table.value,
            valid_from=table.valid_from,
            valid_to=table.valid_to,
            source=table.source,
            confidence=table.confidence,
            status=ClaimStatus(table.status),
            notes=table.notes,
            created_at=table.created_at,
            updated_at=table.updated_at,
            metadata=table.metadata_ or {},
        )

    def from_domain(self, claim: IdentifierClaim) -> ClaimTable:
        """Convert domain model to table row."""
        return ClaimTable(
            claim_id=claim.claim_id,
            entity_id=claim.entity_id,
            scheme=claim.scheme.value
            if isinstance(claim.scheme, IdentifierScheme)
            else claim.scheme,
            value=claim.value,
            valid_from=claim.valid_from,
            valid_to=claim.valid_to,
            source=claim.source,
            confidence=claim.confidence,
            status=claim.status.value if isinstance(claim.status, ClaimStatus) else claim.status,
            notes=claim.notes,
            created_at=claim.created_at,
            updated_at=claim.updated_at,
            metadata_=claim.metadata,
        )
