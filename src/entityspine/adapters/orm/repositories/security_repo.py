"""
Security repository for database operations.
"""

from sqlmodel import Session, select

from entityspine.adapters.orm.repositories.base import BaseRepository
from entityspine.adapters.orm.tables import SecurityTable
from entityspine.adapters.pydantic.security import Security, SecurityType


class SecurityRepository(BaseRepository[SecurityTable]):
    """Repository for Security database operations."""

    def __init__(self, session: Session):
        """Initialize with SecurityTable model."""
        super().__init__(session, SecurityTable)

    def get_by_entity(self, entity_id: str) -> list[SecurityTable]:
        """Get all securities for an entity."""
        statement = select(SecurityTable).where(SecurityTable.entity_id == entity_id)
        return list(self._session.exec(statement).all())

    def get_by_isin(self, isin: str) -> SecurityTable | None:
        """Get security by ISIN."""
        statement = select(SecurityTable).where(SecurityTable.isin == isin.upper())
        return self._session.exec(statement).first()

    def get_by_cusip(self, cusip: str) -> SecurityTable | None:
        """Get security by CUSIP."""
        statement = select(SecurityTable).where(SecurityTable.cusip == cusip.upper())
        return self._session.exec(statement).first()

    def to_domain(self, table: SecurityTable) -> Security:
        """Convert table row to domain model.

        v2.2.3: Security no longer has isin/cusip/sedol/figi fields.
        Identifiers are tracked via IdentifierClaim.
        """
        return Security(
            security_id=table.security_id,
            entity_id=table.entity_id,
            security_type=SecurityType(table.security_type),
            description=table.description,
            # v2.2.3: Use source_system/source_id for record provenance
            source_system=table.source_system or "unknown",
            source_id=table.source_id,
            created_at=table.created_at,
            updated_at=table.updated_at,
            metadata=table.metadata_ or {},
        )

    def from_domain(self, security: Security) -> SecurityTable:
        """Convert domain model to table row.

        v2.2.3: Security no longer has isin/cusip/sedol/figi fields.
        Identifiers are tracked via IdentifierClaim.
        Legacy columns kept for backward compatibility but set to None.
        """
        return SecurityTable(
            security_id=security.security_id,
            entity_id=security.entity_id,
            security_type=security.security_type.value
            if isinstance(security.security_type, SecurityType)
            else security.security_type,
            description=security.description,
            # Legacy identifier columns - set to None
            isin=None,
            cusip=None,
            sedol=None,
            figi=None,
            # v2.2.3: Record provenance
            source_system=getattr(security, "source_system", "unknown"),
            source_id=getattr(security, "source_id", None),
            created_at=security.created_at,
            updated_at=security.updated_at,
            metadata_=security.metadata,
        )
