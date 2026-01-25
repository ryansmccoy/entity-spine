"""
Audit Trail and Change Tracking for EntitySpine.

This module provides:
1. Change tracking for all entity modifications
2. Point-in-time reversion capabilities  
3. Complete audit history
4. Event sourcing pattern support

Design Principles:
- Every change is logged with before/after state
- Changes are immutable once recorded
- Support for both sync and async listeners
- Efficient storage with configurable retention
"""

from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from entityspine.core.timestamps import from_iso8601, to_iso8601, utc_now
from entityspine.core.ulid import generate_ulid

logger = logging.getLogger(__name__)


# =============================================================================
# CHANGE TYPES
# =============================================================================

class ChangeType(Enum):
    """Types of changes that can be tracked."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    MERGE = "merge"
    REDIRECT = "redirect"
    CLAIM_ADD = "claim_add"
    CLAIM_REVOKE = "claim_revoke"
    RELATIONSHIP_ADD = "relationship_add"
    RELATIONSHIP_REMOVE = "relationship_remove"
    BULK_IMPORT = "bulk_import"
    REVERT = "revert"


class EntityKind(Enum):
    """Kinds of entities that can be tracked."""
    ENTITY = "entity"
    SECURITY = "security"
    LISTING = "listing"
    CLAIM = "claim"
    RELATIONSHIP = "relationship"


# =============================================================================
# CHANGE EVENT MODEL
# =============================================================================

@dataclass(frozen=True, slots=True)
class ChangeEvent:
    """
    Immutable record of a change.
    
    All changes to entities, securities, listings, claims, and relationships
    are recorded as ChangeEvents for full auditability.
    """
    # Primary key
    event_id: str = field(default_factory=generate_ulid)

    # What changed
    entity_kind: EntityKind = EntityKind.ENTITY
    entity_id: str = ""
    change_type: ChangeType = ChangeType.UPDATE

    # Before/after state (JSON serialized)
    before_state: str | None = None  # JSON
    after_state: str | None = None   # JSON

    # Change details
    changed_fields: tuple = field(default_factory=tuple)  # Fields that changed
    change_reason: str | None = None

    # Source tracking
    source_system: str = "unknown"
    source_ref: str | None = None
    user_id: str | None = None

    # Timing
    occurred_at: datetime = field(default_factory=utc_now)

    # Reversion support
    parent_event_id: str | None = None  # For grouped changes
    is_revertible: bool = True
    reverted_by: str | None = None  # Event ID that reverted this

    # Checksum for integrity
    checksum: str | None = None

    def __post_init__(self):
        """Compute checksum if not provided."""
        if self.checksum is None:
            content = f"{self.entity_kind.value}:{self.entity_id}:{self.change_type.value}:{self.before_state}:{self.after_state}"
            object.__setattr__(self, 'checksum', hashlib.sha256(content.encode()).hexdigest()[:16])

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "entity_kind": self.entity_kind.value,
            "entity_id": self.entity_id,
            "change_type": self.change_type.value,
            "before_state": self.before_state,
            "after_state": self.after_state,
            "changed_fields": list(self.changed_fields),
            "change_reason": self.change_reason,
            "source_system": self.source_system,
            "source_ref": self.source_ref,
            "user_id": self.user_id,
            "occurred_at": to_iso8601(self.occurred_at),
            "parent_event_id": self.parent_event_id,
            "is_revertible": self.is_revertible,
            "reverted_by": self.reverted_by,
            "checksum": self.checksum,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ChangeEvent:
        return cls(
            event_id=d["event_id"],
            entity_kind=EntityKind(d["entity_kind"]),
            entity_id=d["entity_id"],
            change_type=ChangeType(d["change_type"]),
            before_state=d.get("before_state"),
            after_state=d.get("after_state"),
            changed_fields=tuple(d.get("changed_fields", [])),
            change_reason=d.get("change_reason"),
            source_system=d.get("source_system", "unknown"),
            source_ref=d.get("source_ref"),
            user_id=d.get("user_id"),
            occurred_at=from_iso8601(d["occurred_at"]) if d.get("occurred_at") else utc_now(),
            parent_event_id=d.get("parent_event_id"),
            is_revertible=d.get("is_revertible", True),
            reverted_by=d.get("reverted_by"),
            checksum=d.get("checksum"),
        )


# =============================================================================
# CHANGE LISTENER PROTOCOL
# =============================================================================

ChangeListener = Callable[[ChangeEvent], None]


@dataclass
class ListenerRegistration:
    """Registration for a change listener."""
    listener_id: str
    listener: ChangeListener
    entity_kinds: list[EntityKind] | None = None  # None = all
    change_types: list[ChangeType] | None = None  # None = all
    priority: int = 0  # Higher = called first


# =============================================================================
# AUDIT STORE PROTOCOL
# =============================================================================

class AuditStoreProtocol(ABC):
    """Protocol for audit trail storage."""

    @abstractmethod
    def record_change(self, event: ChangeEvent) -> None:
        """Record a change event."""
        ...

    @abstractmethod
    def get_event(self, event_id: str) -> ChangeEvent | None:
        """Get a specific event by ID."""
        ...

    @abstractmethod
    def get_entity_history(
        self,
        entity_kind: EntityKind,
        entity_id: str,
        limit: int = 100,
    ) -> list[ChangeEvent]:
        """Get change history for an entity."""
        ...

    @abstractmethod
    def get_state_at(
        self,
        entity_kind: EntityKind,
        entity_id: str,
        at_time: datetime,
    ) -> str | None:
        """Get entity state at a point in time (JSON)."""
        ...

    @abstractmethod
    def get_changes_since(
        self,
        since: datetime,
        entity_kinds: list[EntityKind] | None = None,
        limit: int = 1000,
    ) -> list[ChangeEvent]:
        """Get all changes since a given time."""
        ...

    @abstractmethod
    def mark_reverted(self, event_id: str, reverted_by: str) -> None:
        """Mark an event as reverted."""
        ...


# =============================================================================
# SQLITE AUDIT STORE
# =============================================================================

class SqliteAuditStore(AuditStoreProtocol):
    """SQLite-based audit trail storage."""

    SCHEMA = """
    CREATE TABLE IF NOT EXISTS audit_events (
        event_id TEXT PRIMARY KEY,
        entity_kind TEXT NOT NULL,
        entity_id TEXT NOT NULL,
        change_type TEXT NOT NULL,
        before_state TEXT,
        after_state TEXT,
        changed_fields TEXT,
        change_reason TEXT,
        source_system TEXT,
        source_ref TEXT,
        user_id TEXT,
        occurred_at TEXT NOT NULL,
        parent_event_id TEXT,
        is_revertible INTEGER DEFAULT 1,
        reverted_by TEXT,
        checksum TEXT
    );
    
    CREATE INDEX IF NOT EXISTS idx_audit_entity 
        ON audit_events(entity_kind, entity_id);
    CREATE INDEX IF NOT EXISTS idx_audit_time 
        ON audit_events(occurred_at);
    CREATE INDEX IF NOT EXISTS idx_audit_type 
        ON audit_events(change_type);
    CREATE INDEX IF NOT EXISTS idx_audit_parent 
        ON audit_events(parent_event_id);
    """

    def __init__(self, db_path: str | Path = ":memory:"):
        self.db_path = str(db_path)
        self._conn: sqlite3.Connection | None = None

    def initialize(self) -> None:
        """Initialize the audit store."""
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(self.SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        """Close the connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def record_change(self, event: ChangeEvent) -> None:
        """Record a change event."""
        self._conn.execute(
            """INSERT INTO audit_events 
               (event_id, entity_kind, entity_id, change_type, before_state, after_state,
                changed_fields, change_reason, source_system, source_ref, user_id,
                occurred_at, parent_event_id, is_revertible, reverted_by, checksum)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                event.event_id, event.entity_kind.value, event.entity_id,
                event.change_type.value, event.before_state, event.after_state,
                json.dumps(list(event.changed_fields)), event.change_reason,
                event.source_system, event.source_ref, event.user_id,
                to_iso8601(event.occurred_at), event.parent_event_id,
                1 if event.is_revertible else 0, event.reverted_by, event.checksum
            )
        )
        self._conn.commit()

    def get_event(self, event_id: str) -> ChangeEvent | None:
        """Get a specific event."""
        row = self._conn.execute(
            "SELECT * FROM audit_events WHERE event_id = ?", (event_id,)
        ).fetchone()
        return self._row_to_event(row) if row else None

    def get_entity_history(
        self,
        entity_kind: EntityKind,
        entity_id: str,
        limit: int = 100,
    ) -> list[ChangeEvent]:
        """Get change history for an entity."""
        rows = self._conn.execute(
            """SELECT * FROM audit_events 
               WHERE entity_kind = ? AND entity_id = ?
               ORDER BY occurred_at DESC
               LIMIT ?""",
            (entity_kind.value, entity_id, limit)
        ).fetchall()
        return [self._row_to_event(row) for row in rows]

    def get_state_at(
        self,
        entity_kind: EntityKind,
        entity_id: str,
        at_time: datetime,
    ) -> str | None:
        """Get entity state at a point in time."""
        # Find the most recent event before at_time
        row = self._conn.execute(
            """SELECT after_state FROM audit_events
               WHERE entity_kind = ? AND entity_id = ? AND occurred_at <= ?
               ORDER BY occurred_at DESC
               LIMIT 1""",
            (entity_kind.value, entity_id, to_iso8601(at_time))
        ).fetchone()
        return row["after_state"] if row else None

    def get_changes_since(
        self,
        since: datetime,
        entity_kinds: list[EntityKind] | None = None,
        limit: int = 1000,
    ) -> list[ChangeEvent]:
        """Get all changes since a given time."""
        if entity_kinds:
            placeholders = ",".join("?" * len(entity_kinds))
            rows = self._conn.execute(
                f"""SELECT * FROM audit_events
                   WHERE occurred_at > ? AND entity_kind IN ({placeholders})
                   ORDER BY occurred_at ASC
                   LIMIT ?""",
                [to_iso8601(since)] + [k.value for k in entity_kinds] + [limit]
            ).fetchall()
        else:
            rows = self._conn.execute(
                """SELECT * FROM audit_events
                   WHERE occurred_at > ?
                   ORDER BY occurred_at ASC
                   LIMIT ?""",
                (to_iso8601(since), limit)
            ).fetchall()
        return [self._row_to_event(row) for row in rows]

    def mark_reverted(self, event_id: str, reverted_by: str) -> None:
        """Mark an event as reverted."""
        self._conn.execute(
            "UPDATE audit_events SET reverted_by = ? WHERE event_id = ?",
            (reverted_by, event_id)
        )
        self._conn.commit()

    def _row_to_event(self, row: sqlite3.Row) -> ChangeEvent:
        """Convert a database row to a ChangeEvent."""
        return ChangeEvent(
            event_id=row["event_id"],
            entity_kind=EntityKind(row["entity_kind"]),
            entity_id=row["entity_id"],
            change_type=ChangeType(row["change_type"]),
            before_state=row["before_state"],
            after_state=row["after_state"],
            changed_fields=tuple(json.loads(row["changed_fields"] or "[]")),
            change_reason=row["change_reason"],
            source_system=row["source_system"],
            source_ref=row["source_ref"],
            user_id=row["user_id"],
            occurred_at=from_iso8601(row["occurred_at"]),
            parent_event_id=row["parent_event_id"],
            is_revertible=bool(row["is_revertible"]),
            reverted_by=row["reverted_by"],
            checksum=row["checksum"],
        )


# =============================================================================
# AUDIT MANAGER
# =============================================================================

class AuditManager:
    """
    Manages audit trail and change tracking.
    
    Features:
    - Records all changes with before/after state
    - Supports point-in-time queries
    - Enables reversion to previous states
    - Notifies listeners of changes
    """

    def __init__(self, store: AuditStoreProtocol):
        self.store = store
        self._listeners: list[ListenerRegistration] = []

    def record(
        self,
        entity_kind: EntityKind,
        entity_id: str,
        change_type: ChangeType,
        before: Any = None,
        after: Any = None,
        changed_fields: list[str] | None = None,
        reason: str | None = None,
        source_system: str = "unknown",
        source_ref: str | None = None,
        user_id: str | None = None,
        parent_event_id: str | None = None,
    ) -> ChangeEvent:
        """Record a change and notify listeners."""
        # Serialize states
        before_json = json.dumps(before, default=str) if before else None
        after_json = json.dumps(after, default=str) if after else None

        # Auto-detect changed fields if not provided
        if changed_fields is None and before and after:
            if isinstance(before, dict) and isinstance(after, dict):
                changed_fields = [
                    k for k in set(before.keys()) | set(after.keys())
                    if before.get(k) != after.get(k)
                ]

        event = ChangeEvent(
            entity_kind=entity_kind,
            entity_id=entity_id,
            change_type=change_type,
            before_state=before_json,
            after_state=after_json,
            changed_fields=tuple(changed_fields or []),
            change_reason=reason,
            source_system=source_system,
            source_ref=source_ref,
            user_id=user_id,
            parent_event_id=parent_event_id,
        )

        # Store
        self.store.record_change(event)

        # Notify listeners
        self._notify_listeners(event)

        return event

    def get_history(
        self,
        entity_kind: EntityKind,
        entity_id: str,
        limit: int = 100,
    ) -> list[ChangeEvent]:
        """Get change history for an entity."""
        return self.store.get_entity_history(entity_kind, entity_id, limit)

    def get_state_at(
        self,
        entity_kind: EntityKind,
        entity_id: str,
        at_time: datetime,
    ) -> dict[str, Any] | None:
        """Get entity state at a point in time."""
        state_json = self.store.get_state_at(entity_kind, entity_id, at_time)
        return json.loads(state_json) if state_json else None

    def can_revert(self, event_id: str) -> bool:
        """Check if an event can be reverted."""
        event = self.store.get_event(event_id)
        if not event:
            return False
        return event.is_revertible and event.reverted_by is None

    def create_revert_event(
        self,
        event_id: str,
        reason: str | None = None,
        user_id: str | None = None,
    ) -> ChangeEvent | None:
        """Create a reversion event (caller must apply the actual revert)."""
        original = self.store.get_event(event_id)
        if not original or not self.can_revert(event_id):
            return None

        # Create revert event (swaps before/after)
        revert = self.record(
            entity_kind=original.entity_kind,
            entity_id=original.entity_id,
            change_type=ChangeType.REVERT,
            before=json.loads(original.after_state) if original.after_state else None,
            after=json.loads(original.before_state) if original.before_state else None,
            reason=reason or f"Revert of event {event_id}",
            user_id=user_id,
            parent_event_id=event_id,
        )

        # Mark original as reverted
        self.store.mark_reverted(event_id, revert.event_id)

        return revert

    def add_listener(
        self,
        listener: ChangeListener,
        entity_kinds: list[EntityKind] | None = None,
        change_types: list[ChangeType] | None = None,
        priority: int = 0,
    ) -> str:
        """Add a change listener."""
        registration = ListenerRegistration(
            listener_id=generate_ulid(),
            listener=listener,
            entity_kinds=entity_kinds,
            change_types=change_types,
            priority=priority,
        )
        self._listeners.append(registration)
        self._listeners.sort(key=lambda r: -r.priority)
        return registration.listener_id

    def remove_listener(self, listener_id: str) -> bool:
        """Remove a change listener."""
        for i, reg in enumerate(self._listeners):
            if reg.listener_id == listener_id:
                self._listeners.pop(i)
                return True
        return False

    def _notify_listeners(self, event: ChangeEvent) -> None:
        """Notify relevant listeners of a change."""
        for reg in self._listeners:
            # Check filters
            if reg.entity_kinds and event.entity_kind not in reg.entity_kinds:
                continue
            if reg.change_types and event.change_type not in reg.change_types:
                continue

            try:
                reg.listener(event)
            except Exception as e:
                logger.error(f"Listener {reg.listener_id} error: {e}")


# =============================================================================
# FACTORY
# =============================================================================

def create_audit_manager(db_path: str | Path = ":memory:") -> AuditManager:
    """Create and initialize an audit manager."""
    store = SqliteAuditStore(db_path)
    store.initialize()
    return AuditManager(store)
