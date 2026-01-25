"""
Entity repository for SQLite store.

Handles all entity-related database operations following the Repository Pattern.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from entityspine.core.identifier import looks_like_cik, looks_like_ticker
from entityspine.core.timestamps import to_iso8601
from entityspine.domain import Entity

from ..converters import row_to_entity

if TYPE_CHECKING:
    from ..connection import SqliteConnectionManager

logger = logging.getLogger(__name__)


class EntityRepository:
    """
    Repository for Entity CRUD operations.
    
    Single Responsibility: Entity database operations only.
    
    Attributes:
        conn: SqliteConnectionManager for database access.
    """

    def __init__(self, connection: SqliteConnectionManager):
        """
        Initialize repository with connection manager.
        
        Args:
            connection: Connection manager for database access.
        """
        self.conn = connection

    def save(self, entity: Entity) -> None:
        """
        Save or update an entity.
        
        Args:
            entity: Entity domain object to persist.
        """
        entity = entity.with_update()
        now_str = to_iso8601(entity.updated_at)

        self.conn.execute(
            """INSERT INTO entities
               (entity_id, primary_name, entity_type, status,
                source_system, source_id, jurisdiction, sic_code, redirect_to,
                created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(entity_id) DO UPDATE SET
                 primary_name = excluded.primary_name,
                 entity_type = excluded.entity_type,
                 status = excluded.status,
                 source_system = excluded.source_system,
                 source_id = excluded.source_id,
                 jurisdiction = excluded.jurisdiction,
                 sic_code = excluded.sic_code,
                 redirect_to = excluded.redirect_to,
                 updated_at = excluded.updated_at""",
            (
                entity.entity_id,
                entity.primary_name,
                entity.entity_type.value,
                entity.status.value,
                entity.source_system,
                entity.source_id,
                entity.jurisdiction,
                entity.sic_code,
                entity.redirect_to,
                to_iso8601(entity.created_at),
                now_str,
            ),
        )

    def get_by_id(self, entity_id: str, follow_redirects: bool = True) -> Entity | None:
        """
        Get entity by ID.
        
        Args:
            entity_id: Entity ULID.
            follow_redirects: If True, follow redirect chain to canonical entity.
            
        Returns:
            Entity or None if not found.
        """
        row = self.conn.fetchone(
            "SELECT * FROM entities WHERE entity_id = ?",
            (entity_id,),
        )
        if not row:
            return None

        entity = row_to_entity(row)
        return self._follow_redirects(entity) if follow_redirects else entity

    def get_raw(self, entity_id: str) -> Entity | None:
        """
        Get entity by ID WITHOUT following redirects.
        
        Args:
            entity_id: Entity ULID.
            
        Returns:
            Entity exactly as stored, or None.
        """
        return self.get_by_id(entity_id, follow_redirects=False)

    def get_by_cik(self, cik: str) -> list[Entity]:
        """
        Get entities matching CIK.
        
        Args:
            cik: SEC Central Index Key (with or without padding).
            
        Returns:
            List of matching entities.
        """
        cik_normalized = cik.strip().zfill(10)

        rows = self.conn.fetchall(
            """SELECT DISTINCT e.* FROM entities e
               JOIN claims c ON e.entity_id = c.entity_id
               WHERE c.scheme = 'cik' AND c.value = ?""",
            (cik_normalized,),
        )

        entities = []
        seen_ids: set[str] = set()

        for row in rows:
            entity = row_to_entity(row)
            entity = self._follow_redirects(entity)
            if entity.entity_id not in seen_ids:
                entities.append(entity)
                seen_ids.add(entity.entity_id)

        return entities

    def get_by_ticker(self, ticker: str) -> list[Entity]:
        """
        Get entities matching ticker (via Listing lookup).
        
        Args:
            ticker: Stock ticker symbol.
            
        Returns:
            List of matching entities.
        """
        ticker_normalized = ticker.upper().strip().replace("-", ".")

        rows = self.conn.fetchall(
            """SELECT DISTINCT e.* FROM entities e
               JOIN securities s ON e.entity_id = s.entity_id
               JOIN listings l ON s.security_id = l.security_id
               WHERE l.ticker = ?""",
            (ticker_normalized,),
        )

        entities = []
        seen_ids: set[str] = set()

        for row in rows:
            entity = row_to_entity(row)
            entity = self._follow_redirects(entity)
            if entity.entity_id not in seen_ids:
                entities.append(entity)
                seen_ids.add(entity.entity_id)

        return entities

    def search(self, query: str, limit: int = 10) -> list[tuple[Entity, float]]:
        """
        Search entities by name or identifier.
        
        Args:
            query: Search query.
            limit: Maximum results.
            
        Returns:
            List of (entity, similarity_score) tuples.
            Score is 1.0 for exact match, lower for LIKE matches.
        """
        query_lower = query.lower().strip()
        results: list[tuple[Entity, float]] = []
        seen_ids: set[str] = set()

        # Check CIK first
        is_cik, cik_normalized = looks_like_cik(query)
        if is_cik:
            for entity in self.get_by_cik(cik_normalized):
                if entity.entity_id not in seen_ids:
                    results.append((entity, 1.0))
                    seen_ids.add(entity.entity_id)
                    if len(results) >= limit:
                        return results

        # Check ticker
        is_ticker, ticker_normalized = looks_like_ticker(query)
        if is_ticker:
            for entity in self.get_by_ticker(ticker_normalized):
                if entity.entity_id not in seen_ids:
                    results.append((entity, 1.0))
                    seen_ids.add(entity.entity_id)
                    if len(results) >= limit:
                        return results

        # Check exact name match
        rows = self.conn.fetchall(
            "SELECT * FROM entities WHERE LOWER(primary_name) = ? LIMIT ?",
            (query_lower, limit - len(results)),
        )
        for row in rows:
            entity = row_to_entity(row)
            entity = self._follow_redirects(entity)
            if entity.entity_id not in seen_ids:
                results.append((entity, 1.0))
                seen_ids.add(entity.entity_id)

        if len(results) >= limit:
            return results

        # LIKE search for partial matches
        rows = self.conn.fetchall(
            "SELECT * FROM entities WHERE LOWER(primary_name) LIKE ? LIMIT ?",
            (f"%{query_lower}%", limit - len(results)),
        )
        for row in rows:
            entity = row_to_entity(row)
            entity = self._follow_redirects(entity)
            if entity.entity_id not in seen_ids:
                # Lower score for LIKE matches
                results.append((entity, 0.7))
                seen_ids.add(entity.entity_id)

        return results

    def count(self) -> int:
        """
        Count total entities.
        
        Returns:
            Number of entities in database.
        """
        row = self.conn.fetchone("SELECT COUNT(*) as cnt FROM entities")
        return row["cnt"] if row else 0

    def _follow_redirects(self, entity: Entity, max_depth: int = 10) -> Entity:
        """
        Follow redirect chain to get canonical entity.
        
        Args:
            entity: Starting entity.
            max_depth: Maximum redirects to follow (cycle prevention).
            
        Returns:
            Canonical entity.
        """
        seen = {entity.entity_id}
        current = entity

        for _ in range(max_depth):
            if not current.redirect_to:
                return current

            if current.redirect_to in seen:
                logger.warning(
                    f"Redirect cycle detected: {entity.entity_id} -> {current.redirect_to}"
                )
                return current

            target = self.get_raw(current.redirect_to)
            if not target:
                logger.warning(f"Broken redirect: {current.entity_id} -> {current.redirect_to}")
                return current

            seen.add(current.redirect_to)
            current = target

        logger.warning(f"Max redirect depth reached for {entity.entity_id}")
        return current
