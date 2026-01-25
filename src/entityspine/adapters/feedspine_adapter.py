"""
FeedSpine Adapter for EntitySpine

Optional adapter to use FeedSpine for symbology refresh audit trail.

FeedSpine Adds:
- Sighting tracking (first_seen, last_seen)
- Deduplication at source level
- Bronze/Silver/Gold layer management
- Scheduled refresh (cron)

Without FeedSpine:
- EntitySpine handles deduplication at entity level
- No source-level sightings (just claims)
- Manual refresh triggers

Example:
    >>> from entityspine import SqliteStore
    >>> from entityspine.adapters.feedspine_adapter import FeedSpineAdapter
    >>> from feedspine import FeedSpine, MemoryStorage
    >>>
    >>> # Setup EntitySpine
    >>> store = SqliteStore("entities.db")
    >>> store.initialize()
    >>>
    >>> # Setup FeedSpine
    >>> spine = FeedSpine(storage=MemoryStorage())
    >>>
    >>> # Create adapter
    >>> adapter = FeedSpineAdapter(spine, store)
    >>>
    >>> # Sync entities from FeedSpine SILVER layer
    >>> count = await adapter.sync_sec_entities()
    >>> print(f"Synced {count} entities")
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from entityspine.stores.sqlite_store import SqliteStore

logger = logging.getLogger(__name__)


@dataclass
class SyncResult:
    """Result of a FeedSpine → EntitySpine sync operation.

    Attributes:
        source: FeedSpine source name
        records_processed: Number of records processed
        entities_created: Number of new entities created
        entities_updated: Number of existing entities updated
        skipped: Number of records skipped (duplicates)
        errors: List of error messages
        duration_seconds: How long the sync took
    """

    source: str
    records_processed: int = 0
    entities_created: int = 0
    entities_updated: int = 0
    skipped: int = 0
    errors: list[str] | None = None
    duration_seconds: float = 0.0

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class FeedSpineAdapter:
    """Adapter for using FeedSpine with EntitySpine.

    This adapter enables:
    1. Using FeedSpine as a data source for EntitySpine entities
    2. Using FeedSpine for audit trail during symbology refresh
    3. Syncing FeedSpine records to EntitySpine entities

    Architecture:
    ```
    FeedSpine (SILVER layer) ──► FeedSpineAdapter ──► EntitySpine (Entities)
                                    │
                                    ├─ Extracts CIK, ticker, name
                                    ├─ Checks for existing entity
                                    └─ Creates/updates entity
    ```

    Example:
        >>> adapter = FeedSpineAdapter(feedspine, entity_store)
        >>>
        >>> # Sync all SEC entities from FeedSpine
        >>> result = await adapter.sync_sec_entities()
        >>> print(f"Created {result.entities_created} entities")
        >>>
        >>> # Query FeedSpine records with entity resolution
        >>> async for record in adapter.iter_enriched_records("sec-tickers"):
        ...     print(f"{record['ticker']} → {record['entity_name']}")
    """

    def __init__(
        self,
        feedspine: Any,  # FeedSpine instance (duck typed to avoid hard dependency)
        entity_store: SqliteStore,
    ):
        """Initialize the FeedSpine adapter.

        Args:
            feedspine: A FeedSpine instance for data ingestion
            entity_store: An EntitySpine store for entity resolution
        """
        self._spine = feedspine
        self._store = entity_store

    async def sync_sec_entities(
        self,
        source: str = "sec-tickers",
        layer: str = "SILVER",
    ) -> SyncResult:
        """Sync SEC entities from FeedSpine to EntitySpine.

        Processes records from FeedSpine's SILVER layer (cleaned data)
        and creates/updates entities in EntitySpine.

        Args:
            source: FeedSpine source name (default: "sec-tickers")
            layer: FeedSpine layer to read from (default: "SILVER")

        Returns:
            SyncResult with statistics
        """
        start_time = datetime.now(UTC)
        logger.info(f"Starting sync from FeedSpine {source}/{layer}")

        result = SyncResult(source=source)

        try:
            async for record in self._query_feedspine(source, layer):
                result.records_processed += 1

                try:
                    outcome = self._process_feedspine_record(record)
                    if outcome == "created":
                        result.entities_created += 1
                    elif outcome == "updated":
                        result.entities_updated += 1
                    else:
                        result.skipped += 1
                except Exception as e:
                    result.errors.append(f"Record error: {e}")
                    logger.warning(f"Error processing record: {e}")

        except Exception as e:
            result.errors.append(f"Sync failed: {e}")
            logger.error(f"FeedSpine sync failed: {e}")

        result.duration_seconds = (
            datetime.now(UTC) - start_time
        ).total_seconds()

        logger.info(
            f"Sync complete: {result.entities_created} created, "
            f"{result.entities_updated} updated, {result.skipped} skipped"
        )

        return result

    async def iter_enriched_records(
        self,
        source: str,
        layer: str = "SILVER",
    ) -> AsyncIterator[dict[str, Any]]:
        """Iterate FeedSpine records enriched with EntitySpine resolution.

        For each FeedSpine record, adds:
        - entity_id: EntitySpine entity ID (if resolved)
        - entity_name: Canonical entity name (if resolved)
        - resolution_score: How confident the resolution is

        Args:
            source: FeedSpine source name
            layer: FeedSpine layer to read from

        Yields:
            Enriched record dictionaries
        """
        async for record in self._query_feedspine(source, layer):
            enriched = dict(record)

            # Try to resolve entity
            cik = record.get("cik")
            if cik:
                cik = str(cik).lstrip("0").zfill(10)
                entities = self._store.get_entities_by_cik(cik)
                if entities:
                    entity = entities[0]
                    enriched["entity_id"] = entity.entity_id
                    enriched["entity_name"] = entity.primary_name
                    enriched["resolution_score"] = 1.0

            # Try name resolution if CIK failed
            if "entity_id" not in enriched:
                name = record.get("name") or record.get("title")
                if name:
                    results = self._store.search_entities(name, limit=1)
                    if results:
                        entity, score = results[0]
                        if score >= 0.8:
                            enriched["entity_id"] = entity.entity_id
                            enriched["entity_name"] = entity.primary_name
                            enriched["resolution_score"] = score

            yield enriched

    async def _query_feedspine(
        self,
        source: str,
        layer: str,
    ) -> AsyncIterator[dict[str, Any]]:
        """Query FeedSpine for records.

        This method adapts to FeedSpine's API. Override for custom queries.

        Args:
            source: Source name
            layer: Layer name (BRONZE, SILVER, GOLD)

        Yields:
            Record content dictionaries
        """
        # Duck-type FeedSpine API
        # FeedSpine may have different query methods depending on version
        try:
            # Try async query
            if hasattr(self._spine, "query"):
                async for record in self._spine.query(source=source, layer=layer):
                    yield record.content if hasattr(record, "content") else record
            elif hasattr(self._spine, "iter_records"):
                async for record in self._spine.iter_records(source=source, layer=layer):
                    yield record.content if hasattr(record, "content") else record
            else:
                logger.warning("FeedSpine instance has no query method")
        except Exception as e:
            logger.error(f"FeedSpine query failed: {e}")
            raise

    def _process_feedspine_record(self, record: dict[str, Any]) -> str:
        """Process a single FeedSpine record.

        Returns:
            'created' - New entity created
            'updated' - Existing entity updated
            'skipped' - No changes needed
        """
        cik = record.get("cik")
        name = record.get("name") or record.get("title")
        ticker = record.get("ticker")
        exchange = record.get("exchange", "UNKNOWN")

        if not cik or not name:
            return "skipped"

        # Normalize CIK
        cik = str(cik).lstrip("0").zfill(10)

        # Check if entity exists
        existing = self._store.get_entities_by_cik(cik)

        if existing:
            entity = existing[0]
            # Check if we need to add ticker
            if ticker:
                listings = self._store.get_listings_by_ticker(ticker)
                if not listings:
                    self._store.add_listing(
                        entity_id=entity.entity_id,
                        ticker=ticker,
                        exchange=exchange,
                    )
                    return "updated"
            return "skipped"

        # Create new entity
        entity_id = self._store.create_entity(
            primary_name=name,
            source_system="feedspine",
            source_id=cik,
        )

        # Add ticker listing if provided
        if ticker:
            self._store.add_listing(
                entity_id=entity_id,
                ticker=ticker,
                exchange=exchange,
            )

        logger.debug(f"Created entity from FeedSpine: {name} (CIK: {cik})")
        return "created"


# =============================================================================
# Helper: Record symbology update in FeedSpine
# =============================================================================


async def record_symbology_in_feedspine(
    feedspine: Any,
    source: str,
    records: list[dict[str, Any]],
) -> int:
    """Record symbology records in FeedSpine for audit trail.

    This is a helper function for the SymbologyRefreshService to use
    when FeedSpine is configured.

    Args:
        feedspine: FeedSpine instance
        source: Source name (e.g., "sec-tickers")
        records: List of symbology records

    Returns:
        Number of records stored
    """
    stored = 0

    try:
        for record in records:
            cik = record.get("cik")
            if not cik:
                continue

            natural_key = f"{source}:{cik}"

            # Store in FeedSpine (adapt to actual API)
            if hasattr(feedspine, "record"):
                await feedspine.record(
                    natural_key=natural_key,
                    content=record,
                    source=source,
                )
                stored += 1

    except Exception as e:
        logger.error(f"Failed to record in FeedSpine: {e}")

    return stored
