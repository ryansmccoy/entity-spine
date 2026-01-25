"""
Relationship repository for SQLite store.

Handles all relationship database operations following the Repository Pattern.
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from typing import TYPE_CHECKING

from entityspine.core.timestamps import from_iso8601, to_iso8601, utc_now
from entityspine.domain import (
    NodeKind,
    NodeRef,
    Relationship,
    RelationshipType,
)
from entityspine.domain.enums import ClaimStatus
from entityspine.domain.graph import EntityRelationship

if TYPE_CHECKING:
    from ..connection import SqliteConnectionManager


class RelationshipRepository:
    """
    Repository for Relationship CRUD operations.
    
    Single Responsibility: Relationship database operations only.
    Handles both generic NodeRef relationships and entity-specific relationships.
    """

    def __init__(self, connection: SqliteConnectionManager):
        """
        Initialize repository with connection manager.
        
        Args:
            connection: Connection manager for database access.
        """
        self.conn = connection

    def save(self, rel: Relationship) -> None:
        """
        Save or update a generic relationship.
        
        Args:
            rel: Relationship domain object to persist.
        """
        now = datetime.now(UTC).isoformat()
        rel_type = (
            rel.relationship_type.value
            if hasattr(rel.relationship_type, "value")
            else rel.relationship_type
        )

        with self.conn.connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO relationships (
                    relationship_id, source_kind, source_id, target_kind, target_id,
                    relationship_type, subtype, valid_from, valid_to, captured_at,
                    source_system, source_ref, confidence, evidence_filing_id,
                    evidence_section_id, evidence_excerpt_hash, evidence_snippet,
                    metrics, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    rel.relationship_id,
                    rel.source_ref.kind.value
                    if hasattr(rel.source_ref.kind, "value")
                    else rel.source_ref.kind,
                    rel.source_ref.id,
                    rel.target_ref.kind.value
                    if hasattr(rel.target_ref.kind, "value")
                    else rel.target_ref.kind,
                    rel.target_ref.id,
                    rel_type,
                    rel.subtype,
                    rel.valid_from.isoformat() if rel.valid_from else None,
                    rel.valid_to.isoformat() if rel.valid_to else None,
                    rel.captured_at.isoformat() if hasattr(rel.captured_at, "isoformat") else now,
                    rel.source_system,
                    rel.source_id,
                    rel.confidence,
                    rel.evidence_filing_id,
                    rel.evidence_section_id,
                    rel.evidence_excerpt_hash,
                    rel.evidence_snippet,
                    json.dumps(dict(rel.metrics)) if rel.metrics else None,
                    now,
                    now,
                ),
            )
            conn.commit()

    def get_by_id(self, relationship_id: str) -> Relationship | None:
        """
        Get relationship by ID.
        
        Args:
            relationship_id: Relationship ULID.
            
        Returns:
            Relationship or None if not found.
        """
        row = self.conn.fetchone(
            "SELECT * FROM relationships WHERE relationship_id = ?",
            (relationship_id,),
        )
        if not row:
            return None

        return Relationship(
            relationship_id=row["relationship_id"],
            source_ref=NodeRef(
                kind=NodeKind(row["source_kind"]),
                id=row["source_id"],
            ),
            target_ref=NodeRef(
                kind=NodeKind(row["target_kind"]),
                id=row["target_id"],
            ),
            relationship_type=RelationshipType(row["relationship_type"]),
            subtype=row["subtype"],
            valid_from=date.fromisoformat(row["valid_from"]) if row["valid_from"] else None,
            valid_to=date.fromisoformat(row["valid_to"]) if row["valid_to"] else None,
            captured_at=datetime.fromisoformat(row["captured_at"])
            if row["captured_at"]
            else datetime.now(UTC),
            source_system=row["source_system"] or "unknown",
            source_id=row["source_ref"],
            confidence=row["confidence"],
            evidence_filing_id=row["evidence_filing_id"],
            evidence_section_id=row["evidence_section_id"],
            evidence_excerpt_hash=row["evidence_excerpt_hash"],
            evidence_snippet=row["evidence_snippet"],
            metrics=json.loads(row["metrics"]) if row["metrics"] else None,
        )

    def get_by_source_id(self, source_id: str, limit: int = 100) -> list[Relationship]:
        """
        Get all relationships from a source node (by its ID).
        
        Args:
            source_id: Source node ID.
            limit: Maximum results.
            
        Returns:
            List of relationships from the source.
        """
        rows = self.conn.fetchall(
            "SELECT * FROM relationships WHERE source_id = ? LIMIT ?",
            (source_id, limit),
        )
        return [self._row_to_relationship(row) for row in rows]

    def count(self) -> int:
        """
        Count total generic relationships.
        
        Returns:
            Number of relationships in database.
        """
        row = self.conn.fetchone("SELECT COUNT(*) as cnt FROM relationships")
        return row["cnt"] if row else 0

    # =========================================================================
    # Entity-to-Entity Relationship Operations
    # =========================================================================

    def save_entity_relationship(self, rel: EntityRelationship) -> None:
        """
        Save or update an entity relationship.
        
        Args:
            rel: EntityRelationship domain object to persist.
        """
        now_str = to_iso8601(utc_now())
        rel_type = rel.relationship_type.value if hasattr(rel.relationship_type, "value") else rel.relationship_type
        status = rel.status.value if hasattr(rel.status, "value") else rel.status

        with self.conn.connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO entity_relationships (
                    relationship_id, from_entity_id, to_entity_id, relationship_type,
                    valid_from, valid_to, captured_at, source_system, source_ref,
                    confidence, status, evidence_text, filing_id, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    rel.relationship_id,
                    rel.from_entity_id,
                    rel.to_entity_id,
                    rel_type,
                    rel.valid_from.isoformat() if rel.valid_from else None,
                    rel.valid_to.isoformat() if rel.valid_to else None,
                    to_iso8601(rel.captured_at),
                    rel.source_system,
                    rel.source_ref,
                    rel.confidence,
                    status,
                    rel.evidence_text,
                    rel.filing_id,
                    to_iso8601(rel.created_at),
                    now_str,
                ),
            )
            conn.commit()

    def get_entity_relationships(
        self,
        from_entity_id: str | None = None,
        to_entity_id: str | None = None,
        relationship_types: list | None = None,
    ) -> list[EntityRelationship]:
        """
        Get entity relationships with optional filters.
        
        Args:
            from_entity_id: Filter by source entity.
            to_entity_id: Filter by target entity.
            relationship_types: Filter by relationship types.
            
        Returns:
            List of EntityRelationship objects.
        """
        query_parts = ["SELECT * FROM entity_relationships WHERE 1=1"]
        params: list = []

        if from_entity_id:
            query_parts.append("AND from_entity_id = ?")
            params.append(from_entity_id)

        if to_entity_id:
            query_parts.append("AND to_entity_id = ?")
            params.append(to_entity_id)

        if relationship_types:
            placeholders = ",".join("?" * len(relationship_types))
            query_parts.append(f"AND relationship_type IN ({placeholders})")
            for rt in relationship_types:
                params.append(rt.value if hasattr(rt, "value") else rt)

        query = " ".join(query_parts)
        rows = self.conn.fetchall(query, tuple(params))

        results = []
        for row in rows:
            rel = EntityRelationship(
                relationship_id=row["relationship_id"],
                from_entity_id=row["from_entity_id"],
                to_entity_id=row["to_entity_id"],
                relationship_type=RelationshipType(row["relationship_type"]),
                valid_from=date.fromisoformat(row["valid_from"]) if row["valid_from"] else None,
                valid_to=date.fromisoformat(row["valid_to"]) if row["valid_to"] else None,
                captured_at=from_iso8601(row["captured_at"]) if row["captured_at"] else utc_now(),
                source_system=row["source_system"] or "unknown",
                source_ref=row["source_ref"],
                confidence=row["confidence"],
                status=ClaimStatus(row["status"]) if row["status"] else ClaimStatus.ACTIVE,
                evidence_text=row["evidence_text"],
                filing_id=row["filing_id"],
                created_at=from_iso8601(row["created_at"]) if row["created_at"] else utc_now(),
                updated_at=from_iso8601(row["updated_at"]) if row["updated_at"] else utc_now(),
            )
            results.append(rel)

        return results

    def _row_to_relationship(self, row) -> Relationship:
        """Convert database row to Relationship."""
        return Relationship(
            relationship_id=row["relationship_id"],
            source_ref=NodeRef(
                kind=NodeKind(row["source_kind"]),
                id=row["source_id"],
            ),
            target_ref=NodeRef(
                kind=NodeKind(row["target_kind"]),
                id=row["target_id"],
            ),
            relationship_type=RelationshipType(row["relationship_type"]),
            subtype=row["subtype"],
            valid_from=date.fromisoformat(row["valid_from"]) if row["valid_from"] else None,
            valid_to=date.fromisoformat(row["valid_to"]) if row["valid_to"] else None,
            captured_at=datetime.fromisoformat(row["captured_at"])
            if row["captured_at"]
            else datetime.now(UTC),
            source_system=row["source_system"] or "unknown",
            source_id=row["source_ref"],
            confidence=row["confidence"],
            evidence_filing_id=row["evidence_filing_id"],
            evidence_section_id=row["evidence_section_id"],
            evidence_excerpt_hash=row["evidence_excerpt_hash"],
            evidence_snippet=row["evidence_snippet"],
            metrics=json.loads(row["metrics"]) if row["metrics"] else None,
        )
