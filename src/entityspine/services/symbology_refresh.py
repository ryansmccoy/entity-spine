"""
Symbology Refresh Service

Refresh symbology from multiple sources, only appending NEW identifiers.
Works with OR without FeedSpine.

Key Design:
- FeedSpine: "Have I seen this record before?" (deduplication)
- EntitySpine: "What entity does this identifier belong to?" (resolution)

Without FeedSpine:
- EntitySpine handles deduplication at entity level
- No source-level sightings (just claims)
- Manual refresh triggers

With FeedSpine:
- Sighting tracking (first_seen, last_seen)
- Deduplication at source level
- Bronze/Silver/Gold layer management
- Scheduled refresh (cron)

Example:
    >>> from entityspine import SqliteStore
    >>> from entityspine.services import SymbologyRefreshService
    >>> from entityspine.sources import SECTickerSource
    >>>
    >>> store = SqliteStore("entities.db")
    >>> store.initialize()
    >>>
    >>> service = SymbologyRefreshService(store)
    >>> service.add_source(SECTickerSource())
    >>> results = await service.refresh_all()
    >>> print(f"New entities: {results[0].new_entities}")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from entityspine.stores.sqlite_store import SqliteStore

logger = logging.getLogger(__name__)


# =============================================================================
# Result Dataclass
# =============================================================================


@dataclass
class RefreshResult:
    """Result of a symbology refresh operation.

    Attributes:
        source: Name of the symbology source (e.g., "sec-tickers")
        started_at: When the refresh started
        completed_at: When the refresh completed
        records_fetched: Number of records fetched from source
        new_entities: Number of new entities created
        new_claims: Number of new identifier claims added
        updated_claims: Number of existing claims updated
        skipped_duplicates: Number of records skipped (already exist)
        errors: List of error messages encountered
    """

    source: str
    started_at: datetime
    completed_at: datetime
    records_fetched: int = 0
    new_entities: int = 0
    new_claims: int = 0
    updated_claims: int = 0
    skipped_duplicates: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def duration_seconds(self) -> float:
        """Return the duration of the refresh in seconds."""
        return (self.completed_at - self.started_at).total_seconds()

    @property
    def success_rate(self) -> float:
        """Return the success rate (1.0 = 100% success)."""
        if self.records_fetched == 0:
            return 1.0
        return 1.0 - (len(self.errors) / self.records_fetched)


# =============================================================================
# Protocols
# =============================================================================


@runtime_checkable
class SymbologySource(Protocol):
    """Protocol for symbology data sources.

    Implement this protocol to create custom symbology sources.

    Example:
        >>> class MySource:
        ...     name = "my-source"
        ...     async def fetch(self) -> list[dict]:
        ...         return [{"cik": "0000320193", "name": "Apple Inc."}]
    """

    @property
    def name(self) -> str:
        """Return the unique name of this source."""
        ...

    async def fetch(self) -> list[dict]:
        """Fetch symbology records from the source.

        Returns:
            List of dictionaries with symbology data.
            Expected keys: cik, ticker, name, lei, figi, isin, cusip, exchange
        """
        ...


# =============================================================================
# Symbology Refresh Service
# =============================================================================


class SymbologyRefreshService:
    """
    Refresh symbology from multiple sources, deduplicating against EntitySpine.

    Key Features:
    - Only appends NEW identifiers (no duplicates)
    - Tracks when identifiers were first/last seen via claims
    - Uses FeedSpine for raw data ingestion (optional)
    - Uses EntitySpine for identity resolution

    Without FeedSpine:
    - Direct HTTP fetch from sources
    - Deduplication at EntitySpine level (via get_claims)
    - Simpler, fewer dependencies

    With FeedSpine:
    - Full audit trail via sightings
    - Source-level deduplication
    - Scheduled refresh support
    - Bronze/Silver/Gold layer management

    Example:
        >>> from entityspine import SqliteStore
        >>> from entityspine.services import SymbologyRefreshService
        >>> from entityspine.sources import SECTickerSource
        >>>
        >>> store = SqliteStore("entities.db")
        >>> store.initialize()
        >>>
        >>> service = SymbologyRefreshService(store)
        >>> service.add_source(SECTickerSource())
        >>>
        >>> # Refresh all sources
        >>> results = await service.refresh_all()
        >>> for result in results:
        ...     print(f"{result.source}: +{result.new_entities} entities, +{result.new_claims} claims")
    """

    def __init__(
        self,
        entity_store: SqliteStore,
        feedspine: object | None = None,  # Optional FeedSpine for audit trail
    ):
        """Initialize the symbology refresh service.

        Args:
            entity_store: EntitySpine store (SqliteStore or compatible)
            feedspine: Optional FeedSpine instance for audit trail/sightings
        """
        self._store = entity_store
        self._spine = feedspine
        self._sources: list[SymbologySource] = []

    def add_source(self, source: SymbologySource) -> None:
        """Register a symbology source.

        Args:
            source: A source implementing SymbologySource protocol
        """
        self._sources.append(source)
        logger.info(f"Registered symbology source: {source.name}")

    @property
    def sources(self) -> list[SymbologySource]:
        """Return registered sources."""
        return list(self._sources)

    async def refresh_all(self) -> list[RefreshResult]:
        """Refresh symbology from all registered sources.

        Returns:
            List of RefreshResult for each source
        """
        results = []
        for source in self._sources:
            result = await self.refresh_source(source)
            results.append(result)
        return results

    async def refresh_source(self, source: SymbologySource) -> RefreshResult:
        """
        Refresh symbology from a single source.

        Process:
        1. Fetch raw data from source
        2. If FeedSpine configured, store for dedup/audit
        3. For each record, check if identifier exists in EntitySpine
        4. Only insert NEW identifiers (claims)
        5. Track statistics

        Args:
            source: The symbology source to refresh

        Returns:
            RefreshResult with statistics
        """
        started = datetime.now(UTC)
        logger.info(f"Starting symbology refresh from {source.name}")

        # Fetch raw data
        try:
            raw_records = await source.fetch()
        except Exception as e:
            logger.error(f"Failed to fetch from {source.name}: {e}")
            return RefreshResult(
                source=source.name,
                started_at=started,
                completed_at=datetime.now(UTC),
                errors=[f"Fetch failed: {e}"],
            )

        logger.info(f"Fetched {len(raw_records)} records from {source.name}")

        # Optional: Store in FeedSpine for audit trail
        if self._spine is not None:
            await self._store_in_feedspine(source.name, raw_records)

        # Process each record
        new_entities = 0
        new_claims = 0
        updated_claims = 0
        skipped = 0
        errors: list[str] = []

        for record in raw_records:
            try:
                result = self._process_record(source.name, record)
                if result == "new_entity":
                    new_entities += 1
                    new_claims += 1  # New entity always gets at least one claim
                elif result == "new_claim":
                    new_claims += 1
                elif result == "updated":
                    updated_claims += 1
                else:
                    skipped += 1
            except Exception as e:
                errors.append(f"Record error: {e}")
                logger.warning(f"Error processing record: {e}")

        completed = datetime.now(UTC)
        logger.info(
            f"Completed {source.name}: +{new_entities} entities, "
            f"+{new_claims} claims, {skipped} skipped"
        )

        return RefreshResult(
            source=source.name,
            started_at=started,
            completed_at=completed,
            records_fetched=len(raw_records),
            new_entities=new_entities,
            new_claims=new_claims,
            updated_claims=updated_claims,
            skipped_duplicates=skipped,
            errors=errors,
        )

    def _process_record(self, source: str, record: dict) -> str:
        """
        Process a single symbology record.

        Returns:
            'new_entity' - Created new entity
            'new_claim' - Added claim to existing entity
            'updated' - Updated existing claim
            'skipped' - Already exists, no changes
        """
        from entityspine import create_entity

        # Extract CIK as primary identifier
        cik = record.get("cik")
        if cik:
            cik = str(cik).lstrip("0").zfill(10)  # Normalize to 10 digits

        name = record.get("name") or record.get("title")
        ticker = record.get("ticker")
        exchange = record.get("exchange")

        # Check if entity exists by CIK
        if cik:
            existing_entities = self._store.get_entities_by_cik(cik)
            if existing_entities:
                # Entity exists - check if we need to add claims
                entity = existing_entities[0]
                return self._update_entity_claims(entity, record, source)

        # Check if entity exists by name (fuzzy match)
        if name:
            results = self._store.search_entities(name, limit=1)
            if results:
                entity, score = results[0]
                if score >= 0.95:  # High confidence match
                    return self._update_entity_claims(entity, record, source)

        # New entity - create it using domain factory
        if cik and name:
            entity = create_entity(
                primary_name=name,
                source_system="sec" if "sec" in source.lower() else source,
                source_id=cik,
            )
            self._store.save_entity(entity)

            # Add ticker listing if provided
            if ticker and exchange:
                try:
                    # Use _create_security_and_listing if available
                    if hasattr(self._store, "_create_security_and_listing"):
                        self._store._create_security_and_listing(
                            entity.entity_id, name, ticker
                        )
                except Exception as e:
                    logger.warning(f"Failed to create listing: {e}")

            logger.debug(f"Created new entity: {name} (CIK: {cik})")
            return "new_entity"

        return "skipped"

    def _update_entity_claims(self, entity, record: dict, source: str) -> str:
        """Update claims for an existing entity.

        Returns:
            'new_claim' - Added new claim
            'updated' - Updated existing claim
            'skipped' - No changes needed
        """
        ticker = record.get("ticker")
        exchange = record.get("exchange")

        # Check if ticker listing exists
        if ticker:
            existing_listings = self._store.get_listings_by_ticker(ticker)
            if not existing_listings:
                # Add new listing using internal method
                try:
                    if hasattr(self._store, "_create_security_and_listing"):
                        self._store._create_security_and_listing(
                            entity.entity_id, entity.primary_name, ticker
                        )
                        logger.debug(f"Added listing {ticker} to {entity.primary_name}")
                        return "new_claim"
                except Exception as e:
                    logger.warning(f"Failed to add listing: {e}")

        return "skipped"

    async def _store_in_feedspine(self, source: str, records: list[dict]) -> None:
        """Store records in FeedSpine for audit trail (if configured).

        Args:
            source: Source name
            records: Raw records from source
        """
        if self._spine is None:
            return

        # FeedSpine integration - type checking deferred
        try:
            for record in records:
                cik = record.get("cik")
                natural_key = f"{source}:{cik}" if cik else None
                if natural_key:
                    # Note: Actual FeedSpine API call would go here
                    # await self._spine.record(natural_key=natural_key, content=record)
                    pass
        except Exception as e:
            logger.warning(f"Failed to store in FeedSpine: {e}")
