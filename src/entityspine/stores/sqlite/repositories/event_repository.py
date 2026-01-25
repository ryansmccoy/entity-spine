"""
Event repository for SQLite store.

Handles all event-related database operations following the Repository Pattern.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from entityspine.domain import Event, EventType
from entityspine.stores.mappers import event_to_row, row_to_event

if TYPE_CHECKING:
    from ..connection import SqliteConnectionManager


class EventRepository:
    """
    Repository for Event CRUD operations.
    
    Single Responsibility: Event database operations only.
    Note: Uses kg_events table (graph-native events, not py-sec-edgar events).
    """

    def __init__(self, connection: SqliteConnectionManager):
        """
        Initialize repository with connection manager.
        
        Args:
            connection: Connection manager for database access.
        """
        self.conn = connection

    def save(self, event: Event) -> None:
        """
        Save or update an event.
        
        Args:
            event: Event domain object to persist.
        """
        row = event_to_row(event)
        with self.conn.connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO kg_events (
                    event_id, event_type, title, description, status,
                    occurred_on, announced_on, payload, evidence_filing_id,
                    evidence_section_id, evidence_snippet, confidence,
                    source_system, source_id, captured_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["event_id"],
                    row["event_type"],
                    row["title"],
                    row["description"],
                    row["status"],
                    row["occurred_on"],
                    row["announced_on"],
                    row["payload"],
                    row["evidence_filing_id"],
                    row["evidence_section_id"],
                    row["evidence_snippet"],
                    row["confidence"],
                    row["source_system"],
                    row["source_id"],
                    row["captured_at"],
                    row["created_at"],
                    row["updated_at"],
                ),
            )
            conn.commit()

    def get_by_id(self, event_id: str) -> Event | None:
        """
        Get event by ID.
        
        Args:
            event_id: Event ULID.
            
        Returns:
            Event or None if not found.
        """
        row = self.conn.fetchone("SELECT * FROM kg_events WHERE event_id = ?", (event_id,))
        return row_to_event(dict(row)) if row else None

    def get_by_type(self, event_type: EventType) -> list[Event]:
        """
        Get all events of a specific type.
        
        Args:
            event_type: Event type to filter by.
            
        Returns:
            List of events matching the type.
        """
        type_value = event_type.value if hasattr(event_type, "value") else event_type
        rows = self.conn.fetchall(
            "SELECT * FROM kg_events WHERE event_type = ?",
            (type_value,),
        )
        return [row_to_event(dict(row)) for row in rows]

    def count(self) -> int:
        """
        Count total events.
        
        Returns:
            Number of events in database.
        """
        row = self.conn.fetchone("SELECT COUNT(*) as cnt FROM kg_events")
        return row["cnt"] if row else 0
