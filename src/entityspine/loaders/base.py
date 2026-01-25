"""
Base classes for EntitySpine data loaders.

Provides:
- DataLoader: Abstract base class for all loaders
- LoadStats: Statistics tracking for load operations
- Bulk insert helpers for performance
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Iterator, TypeVar

if TYPE_CHECKING:
    from entityspine.domain import Entity, IdentifierClaim, Listing, Security
    from entityspine.stores import SqliteStore

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class LoadStats:
    """Statistics for a data load operation."""
    
    source: str = ""
    started_at: datetime = field(default_factory=datetime.now)
    finished_at: datetime | None = None
    
    entities_loaded: int = 0
    securities_loaded: int = 0
    listings_loaded: int = 0
    claims_loaded: int = 0
    
    entities_skipped: int = 0
    errors: int = 0
    
    def finish(self) -> None:
        """Mark load as finished."""
        self.finished_at = datetime.now()
    
    @property
    def elapsed_seconds(self) -> float:
        """Elapsed time in seconds."""
        end = self.finished_at or datetime.now()
        return (end - self.started_at).total_seconds()
    
    @property
    def entities_per_second(self) -> float:
        """Entities loaded per second."""
        elapsed = self.elapsed_seconds
        if elapsed == 0:
            return 0.0
        return self.entities_loaded / elapsed
    
    def __str__(self) -> str:
        return (
            f"LoadStats({self.source}): "
            f"{self.entities_loaded:,} entities, "
            f"{self.securities_loaded:,} securities, "
            f"{self.listings_loaded:,} listings, "
            f"{self.claims_loaded:,} claims "
            f"in {self.elapsed_seconds:.1f}s "
            f"({self.entities_per_second:.0f}/sec)"
        )


class DataLoader(ABC):
    """
    Abstract base class for vendor data loaders.
    
    Implements bulk loading with batched commits for performance.
    """
    
    def __init__(
        self,
        store: "SqliteStore",
        batch_size: int = 5000,
        commit_interval: int = 10000,
    ):
        """
        Initialize loader.
        
        Args:
            store: SQLite store for persistence
            batch_size: Number of records to batch before insert
            commit_interval: Number of records between commits
        """
        self.store = store
        self.batch_size = batch_size
        self.commit_interval = commit_interval
        self.stats = LoadStats()
        
        # Batch buffers
        self._entity_batch: list[Entity] = []
        self._security_batch: list[Security] = []
        self._listing_batch: list[Listing] = []
        self._claim_batch: list[IdentifierClaim] = []
    
    @abstractmethod
    def load(self, source: str | Path, **kwargs) -> LoadStats:
        """
        Load data from a source.
        
        Args:
            source: Path to source file or directory
            **kwargs: Loader-specific options
            
        Returns:
            LoadStats with load results
        """
        ...
    
    def _flush_batches(self) -> None:
        """Flush all pending batches to database."""
        if self._entity_batch:
            self._bulk_insert_entities(self._entity_batch)
            self._entity_batch = []
        
        if self._security_batch:
            self._bulk_insert_securities(self._security_batch)
            self._security_batch = []
        
        if self._listing_batch:
            self._bulk_insert_listings(self._listing_batch)
            self._listing_batch = []
        
        if self._claim_batch:
            self._bulk_insert_claims(self._claim_batch)
            self._claim_batch = []
    
    def _add_entity(self, entity: "Entity") -> None:
        """Add entity to batch, flushing if needed."""
        self._entity_batch.append(entity)
        self.stats.entities_loaded += 1
        
        if len(self._entity_batch) >= self.batch_size:
            self._bulk_insert_entities(self._entity_batch)
            self._entity_batch = []
        
        self._maybe_commit()
    
    def _add_security(self, security: "Security") -> None:
        """Add security to batch."""
        self._security_batch.append(security)
        self.stats.securities_loaded += 1
        
        if len(self._security_batch) >= self.batch_size:
            self._bulk_insert_securities(self._security_batch)
            self._security_batch = []
    
    def _add_listing(self, listing: "Listing") -> None:
        """Add listing to batch."""
        self._listing_batch.append(listing)
        self.stats.listings_loaded += 1
        
        if len(self._listing_batch) >= self.batch_size:
            self._bulk_insert_listings(self._listing_batch)
            self._listing_batch = []
    
    def _add_claim(self, claim: "IdentifierClaim") -> None:
        """Add claim to batch."""
        self._claim_batch.append(claim)
        self.stats.claims_loaded += 1
        
        if len(self._claim_batch) >= self.batch_size:
            self._bulk_insert_claims(self._claim_batch)
            self._claim_batch = []
    
    def _maybe_commit(self) -> None:
        """Commit if we've reached the interval."""
        total = (
            self.stats.entities_loaded +
            self.stats.securities_loaded +
            self.stats.claims_loaded
        )
        if total > 0 and total % self.commit_interval == 0:
            self.store._conn.commit()
            logger.info(f"Committed at {total:,} records")
    
    def _bulk_insert_entities(self, entities: list["Entity"]) -> None:
        """Bulk insert entities using executemany."""
        from entityspine.core.timestamps import to_iso8601
        
        if not entities:
            return
        
        data = []
        for e in entities:
            e = e.with_update()
            data.append((
                e.entity_id,
                e.primary_name,
                e.entity_type.value,
                e.status.value,
                e.source_system,
                e.source_id,
                e.jurisdiction,
                e.sic_code,
                e.redirect_to,
                to_iso8601(e.created_at),
                to_iso8601(e.updated_at),
            ))
        
        self.store._conn.executemany(
            """INSERT OR REPLACE INTO entities
               (entity_id, primary_name, entity_type, status,
                source_system, source_id, jurisdiction, sic_code, redirect_to,
                created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            data,
        )
    
    def _bulk_insert_securities(self, securities: list["Security"]) -> None:
        """Bulk insert securities using executemany."""
        from entityspine.core.timestamps import to_iso8601
        
        if not securities:
            return
        
        data = []
        for s in securities:
            s = s.with_update()
            data.append((
                s.security_id,
                s.entity_id,
                s.security_type.value,
                s.status.value,
                s.description,
                s.source_system,
                to_iso8601(s.created_at),
                to_iso8601(s.updated_at),
            ))
        
        self.store._conn.executemany(
            """INSERT OR REPLACE INTO securities
               (security_id, entity_id, security_type, status,
                description, source_system, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            data,
        )
    
    def _bulk_insert_listings(self, listings: list["Listing"]) -> None:
        """Bulk insert listings using executemany."""
        from entityspine.core.timestamps import to_iso8601
        
        if not listings:
            return
        
        data = []
        for lst in listings:
            lst = lst.with_update()
            data.append((
                lst.listing_id,
                lst.security_id,
                lst.ticker,
                lst.exchange,
                lst.mic,
                lst.status.value,
                1 if lst.is_primary else 0,
                to_iso8601(lst.start_date) if lst.start_date else None,
                to_iso8601(lst.end_date) if lst.end_date else None,
                lst.source_system,
                to_iso8601(lst.created_at),
                to_iso8601(lst.updated_at),
            ))
        
        self.store._conn.executemany(
            """INSERT OR REPLACE INTO listings
               (listing_id, security_id, ticker, exchange, mic, status,
                is_primary, start_date, end_date, source_system,
                created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            data,
        )
    
    def _bulk_insert_claims(self, claims: list["IdentifierClaim"]) -> None:
        """Bulk insert claims using executemany."""
        from entityspine.core.timestamps import to_iso8601
        from entityspine.core.ulid import generate_ulid
        
        if not claims:
            return
        
        data = []
        for c in claims:
            c = c.with_update()
            claim_id = c.claim_id or generate_ulid()
            data.append((
                claim_id,
                c.entity_id,
                c.security_id,
                c.listing_id,
                c.scheme.value,
                c.value,
                c.namespace.value,
                c.status.value,
                c.confidence,
                c.source,
                to_iso8601(c.valid_from) if c.valid_from else None,
                to_iso8601(c.valid_to) if c.valid_to else None,
                to_iso8601(c.captured_at),
                to_iso8601(c.created_at),
                to_iso8601(c.updated_at),
            ))
        
        self.store._conn.executemany(
            """INSERT OR REPLACE INTO claims
               (claim_id, entity_id, security_id, listing_id, scheme, value,
                namespace, status, confidence, source, valid_from, valid_to,
                captured_at, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            data,
        )
    
    def _log_progress(self, message: str = "") -> None:
        """Log progress update."""
        logger.info(
            f"{message} - "
            f"{self.stats.entities_loaded:,} entities, "
            f"{self.stats.claims_loaded:,} claims "
            f"({self.stats.entities_per_second:.0f}/sec)"
        )
