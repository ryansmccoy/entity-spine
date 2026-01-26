"""
Entity repository for database operations.

Provides entity-specific queries:
- get_by_cik
- get_by_name
- search by name
- follow redirects
"""

from sqlmodel import Session, col, select

from entityspine.adapters.orm.repositories.base import BaseRepository
from entityspine.adapters.orm.tables import EntityTable
from entityspine.adapters.pydantic.entity import Entity, EntityStatus, EntityType


class EntityRepository(BaseRepository[EntityTable]):
    """
    Repository for Entity database operations.

    Provides specialized queries for entities including:
    - CIK lookup
    - Name search
    - Redirect following
    """

    def __init__(self, session: Session):
        """Initialize with EntityTable model."""
        super().__init__(session, EntityTable)

    def get_by_cik(self, cik: str) -> EntityTable | None:
        """
        Get entity by CIK.

        Args:
            cik: SEC Central Index Key (will be normalized).

        Returns:
            Entity or None.
        """
        # Normalize CIK to 10-digit
        cik_normalized = cik.strip().lstrip("0").zfill(10) if cik else None
        if not cik_normalized:
            return None

        statement = select(EntityTable).where(EntityTable.cik == cik_normalized)
        return self._session.exec(statement).first()

    def get_by_cik_list(self, ciks: list[str]) -> list[EntityTable]:
        """
        Get entities by multiple CIKs.

        Args:
            ciks: List of CIKs.

        Returns:
            List of matching entities.
        """
        # Normalize all CIKs
        normalized = [c.strip().lstrip("0").zfill(10) for c in ciks if c]
        if not normalized:
            return []

        statement = select(EntityTable).where(col(EntityTable.cik).in_(normalized))
        return list(self._session.exec(statement).all())

    def get_with_redirect(self, entity_id: str, max_depth: int = 10) -> EntityTable | None:
        """
        Get entity, following redirects.

        Args:
            entity_id: Entity ID to look up.
            max_depth: Maximum redirect depth.

        Returns:
            Final entity after following redirects, or None.
        """
        visited: set[str] = set()
        current_id = entity_id

        for _ in range(max_depth):
            if current_id in visited:
                # Cycle detected
                break
            visited.add(current_id)

            entity = self.get_by_id(current_id)
            if not entity:
                return None

            if not entity.redirect_to:
                return entity

            current_id = entity.redirect_to

        return None  # Max depth exceeded

    def search_by_name(
        self,
        query: str,
        limit: int = 10,
        status: str | None = None,
    ) -> list[EntityTable]:
        """
        Search entities by name using LIKE.

        Args:
            query: Search query.
            limit: Maximum results.
            status: Filter by status.

        Returns:
            Matching entities.
        """
        # Build search pattern
        pattern = f"%{query}%"

        statement = select(EntityTable).where(col(EntityTable.primary_name).ilike(pattern))

        if status:
            statement = statement.where(EntityTable.status == status)

        statement = statement.limit(limit)
        return list(self._session.exec(statement).all())

    def get_by_status(self, status: str, limit: int = 100) -> list[EntityTable]:
        """
        Get entities by status.

        Args:
            status: Status filter.
            limit: Maximum results.

        Returns:
            Matching entities.
        """
        statement = select(EntityTable).where(EntityTable.status == status).limit(limit)
        return list(self._session.exec(statement).all())

    def to_domain(self, table: EntityTable) -> Entity:
        """
        Convert table row to domain model.

        Args:
            table: Database row.

        Returns:
            Pydantic Entity model.

        Note:
            v2.2.3: Entity no longer has cik/lei/ein/identifiers fields.
            Those are stored in IdentifierClaim. The table still has the
            columns for storage, but they're not exposed on the domain model.
        """
        return Entity(
            entity_id=table.entity_id,
            primary_name=table.primary_name,
            entity_type=EntityType(table.entity_type),
            status=EntityStatus(table.status),
            jurisdiction=table.jurisdiction,
            sic_code=table.sic_code,
            incorporation_date=table.incorporation_date,
            source_system=table.source_system or "unknown",
            source_id=table.source_id,
            redirect_to=table.redirect_to,
            redirect_reason=table.redirect_reason,
            merged_at=table.merged_at,
            aliases=table.aliases or [],
            created_at=table.created_at,
            updated_at=table.updated_at,
            metadata=table.metadata_ or {},
        )

    def from_domain(self, entity: Entity) -> EntityTable:
        """
        Convert domain model to table row.

        Args:
            entity: Pydantic Entity model.

        Returns:
            Database row.

        Note:
            v2.2.3: Entity no longer has cik/lei/ein/identifiers fields.
            Those are stored in IdentifierClaim. The table still has the
            columns for backward compatibility. We populate the cik column
            when source_system='sec' for backward-compatible CIK lookups.
        """
        # For backward compatibility, populate legacy cik column when source_system='sec'
        legacy_cik = None
        if entity.source_system == "sec" and entity.source_id:
            legacy_cik = entity.source_id.strip().zfill(10)

        return EntityTable(
            entity_id=entity.entity_id,
            primary_name=entity.primary_name,
            entity_type=entity.entity_type.value
            if isinstance(entity.entity_type, EntityType)
            else entity.entity_type,
            status=entity.status.value
            if isinstance(entity.status, EntityStatus)
            else entity.status,
            cik=legacy_cik,  # v2.2.3: Populated from source_id when source_system='sec'
            lei=None,  # v2.2.3: Use IdentifierClaim instead
            ein=None,  # v2.2.3: Use IdentifierClaim instead
            jurisdiction=entity.jurisdiction,
            sic_code=entity.sic_code,
            incorporation_date=entity.incorporation_date,
            source_system=entity.source_system,
            source_id=entity.source_id,
            redirect_to=entity.redirect_to,
            redirect_reason=entity.redirect_reason,
            merged_at=entity.merged_at,
            identifiers={},  # v2.2.3: Use IdentifierClaim instead
            aliases=entity.aliases,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            metadata_=entity.metadata,
        )
