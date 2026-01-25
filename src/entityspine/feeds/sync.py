"""
Synchronization utilities between FeedSpine and EntitySpine.

This module provides tools to:
1. Sync FeedSpine records (Bronze) to EntitySpine registries (Gold)
2. Detect changes between FeedSpine sightings and current registry state
3. Update EntitySpine stores from FeedSpine collections

The sync flow:
    FeedSpine Storage (Bronze) --> Sync --> EntitySpine Registry (Gold)
                                        --> EntitySpine Store (Entities/Securities)

Example:
    >>> from feedspine import FeedSpine, MemoryStorage
    >>> from entityspine.feeds import MICFeedAdapter
    >>> from entityspine.feeds.sync import FeedSpineEntitySpineSync
    >>>
    >>> async def full_refresh():
    ...     # FeedSpine handles dedup and storage
    ...     fs_storage = MemoryStorage()
    ...     spine = FeedSpine(storage=fs_storage)
    ...     spine.register_feed(MICFeedAdapter())
    ...     result = await spine.collect()
    ...     
    ...     # Sync new records to EntitySpine
    ...     sync = FeedSpineEntitySpineSync(fs_storage)
    ...     await sync.sync_mic_registry()
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from entityspine.sources import CountryRegistry, CurrencyRegistry, LEIRegistry, MICRegistry
    from entityspine.stores import SqliteStore

logger = logging.getLogger(__name__)


# =============================================================================
# Individual Sync Functions
# =============================================================================


async def sync_mic_to_registry(
    feedspine_storage: Any,
    registry: MICRegistry | None = None,
) -> tuple[int, int]:
    """
    Sync MIC records from FeedSpine storage to EntitySpine MICRegistry.
    
    Args:
        feedspine_storage: FeedSpine storage backend with MIC records.
        registry: Existing MICRegistry to update (creates new if None).
        
    Returns:
        Tuple of (new_count, updated_count).
    
    Example:
        >>> from feedspine import MemoryStorage
        >>> from entityspine.feeds.sync import sync_mic_to_registry
        >>> from entityspine.sources import MICRegistry
        >>> # Assuming storage has MIC records from MICFeedAdapter
        >>> # new, updated = await sync_mic_to_registry(storage)
    """
    from entityspine.domain.timestamps import utc_now
    from entityspine.sources import MICRecord, MICRegistry

    if registry is None:
        registry = MICRegistry()

    new_count = 0
    updated_count = 0

    # Query all MIC records from FeedSpine
    async for record in feedspine_storage.query(
        filters={"metadata.source_type": "iso10383.mic"}
    ):
        content = record.content
        mic_code = content.get("mic")

        if not mic_code:
            continue

        # Check if MIC exists in registry
        existing = registry.get(mic_code)

        if existing is None:
            new_count += 1
        # Compare content hashes for change detection
        elif content.get("content_hash") != getattr(existing, "_content_hash", None):
            updated_count += 1
        else:
            continue  # No change

        # Create MICRecord from FeedSpine content
        mic_record = MICRecord(
            mic=mic_code,
            operating_mic=content.get("operating_mic", mic_code),
            mic_type=content.get("mic_type", "OPRT"),
            name=content.get("name", ""),
            legal_entity_name=content.get("legal_entity_name"),
            lei=content.get("lei"),
            market_category_code=content.get("market_category_code"),
            acronym=content.get("acronym"),
            country_code=content.get("country_code"),
            city=content.get("city"),
            website=content.get("website"),
            status=content.get("status", "ACTIVE"),
            snapshot_id=record.metadata.extra.get("snapshot_id"),
            captured_at=utc_now(),
        )

        # Add to registry (updates internal dict)
        registry._mics[mic_code.upper()] = mic_record

    logger.info(f"MIC sync complete: {new_count} new, {updated_count} updated")
    return new_count, updated_count


async def sync_sec_to_store(
    feedspine_storage: Any,
    entity_store: SqliteStore,
    create_entities: bool = True,
    create_securities: bool = True,
    create_listings: bool = True,
) -> dict[str, int]:
    """
    Sync SEC ticker records from FeedSpine to EntitySpine SqliteStore.
    
    Creates/updates:
    - Entities (one per CIK)
    - Securities (one per ticker)
    - Listings (ticker on exchange)
    
    Args:
        feedspine_storage: FeedSpine storage backend with SEC records.
        entity_store: EntitySpine SqliteStore to update.
        create_entities: Whether to create Entity records.
        create_securities: Whether to create Security records.
        create_listings: Whether to create Listing records.
        
    Returns:
        Dict with counts: {"entities": N, "securities": N, "listings": N}
    """
    from entityspine.domain.enums import IdentifierScheme, VendorNamespace
    from entityspine.domain.graph import Entity, Listing, Security
    from entityspine.domain.timestamps import utc_now

    stats = {"entities": 0, "securities": 0, "listings": 0}

    # Track CIKs we've seen to avoid duplicates
    seen_ciks: set[str] = set()

    async for record in feedspine_storage.query(
        filters={"metadata.source_type": "sec.company_tickers"}
    ):
        content = record.content
        cik = content.get("cik")
        ticker = content.get("ticker")
        name = content.get("name")
        exchange = content.get("exchange")
        mic = content.get("mic")

        if not cik or not ticker:
            continue

        # Create entity (one per CIK)
        if create_entities and cik not in seen_ciks:
            seen_ciks.add(cik)

            entity = Entity(
                entity_id=f"sec:{cik}",
                primary_name=name,
                source_system="SEC",
                captured_at=utc_now(),
                jurisdiction="US",
                is_public=True,
            )

            # Add CIK claim
            entity.add_identifier(
                scheme=IdentifierScheme.CIK,
                value=cik,
                namespace=VendorNamespace.SEC,
            )

            entity_store.save_entity(entity)
            stats["entities"] += 1

        # Create security
        if create_securities:
            security = Security(
                security_id=f"sec:{cik}:{ticker}",
                entity_id=f"sec:{cik}",
                primary_ticker=ticker,
                security_type="EQUITY",
                source_system="SEC",
                captured_at=utc_now(),
            )

            entity_store.save_security(security)
            stats["securities"] += 1

        # Create listing
        if create_listings and mic:
            listing = Listing(
                listing_id=f"sec:{ticker}:{mic}",
                security_id=f"sec:{cik}:{ticker}",
                ticker=ticker,
                exchange=mic,
                captured_at=utc_now(),
                is_primary=True,
            )

            entity_store.save_listing(listing)
            stats["listings"] += 1

    logger.info(f"SEC sync complete: {stats}")
    return stats


async def sync_lei_to_registry(
    feedspine_storage: Any,
    registry: LEIRegistry | None = None,
) -> tuple[int, int]:
    """
    Sync LEI records from FeedSpine storage to EntitySpine LEIRegistry.
    
    Args:
        feedspine_storage: FeedSpine storage backend with LEI records.
        registry: Existing LEIRegistry to update (creates new if None).
        
    Returns:
        Tuple of (new_count, updated_count).
    """
    from entityspine.domain.timestamps import utc_now
    from entityspine.sources import LEIRecord, LEIRegistry

    if registry is None:
        from entityspine.sources.gleif import LEIRegistry
        registry = LEIRegistry()

    new_count = 0
    updated_count = 0

    async for record in feedspine_storage.query(
        filters={"metadata.source_type": "gleif.lei"}
    ):
        content = record.content
        lei = content.get("lei")

        if not lei:
            continue

        existing = registry.get(lei)

        if existing is None:
            new_count += 1
        elif content.get("content_hash") != getattr(existing, "_content_hash", None):
            updated_count += 1
        else:
            continue

        lei_record = LEIRecord(
            lei=lei,
            legal_name=content.get("legal_name", ""),
            legal_address_country=content.get("legal_address_country"),
            legal_address_city=content.get("legal_address_city"),
            hq_address_country=content.get("hq_address_country"),
            hq_address_city=content.get("hq_address_city"),
            legal_jurisdiction=content.get("legal_jurisdiction"),
            entity_category=content.get("entity_category"),
            entity_status=content.get("entity_status", "ACTIVE"),
            registration_status=content.get("registration_status"),
            snapshot_id=record.metadata.extra.get("snapshot_id"),
            captured_at=utc_now(),
        )

        registry._leis[lei.upper()] = lei_record

    logger.info(f"LEI sync complete: {new_count} new, {updated_count} updated")
    return new_count, updated_count


# =============================================================================
# Unified Sync Manager
# =============================================================================


class FeedSpineEntitySpineSync:
    """
    Unified synchronization manager between FeedSpine and EntitySpine.
    
    Provides a single interface to:
    - Collect from all reference data feeds
    - Sync to appropriate EntitySpine registries/stores
    - Track sync history and changes
    
    Example:
        >>> from feedspine import FeedSpine, MemoryStorage
        >>> from entityspine.feeds.sync import FeedSpineEntitySpineSync
        >>> from entityspine.stores import SqliteStore
        >>>
        >>> async def refresh_all():
        ...     fs_storage = MemoryStorage()
        ...     entity_store = SqliteStore(":memory:")
        ...     
        ...     sync = FeedSpineEntitySpineSync(
        ...         feedspine_storage=fs_storage,
        ...         entity_store=entity_store,
        ...     )
        ...     
        ...     # Register all feeds and collect
        ...     result = await sync.collect_all()
        ...     
        ...     # Sync to EntitySpine
        ...     sync_result = await sync.sync_all()
        ...     print(f"Synced: {sync_result}")
    """

    def __init__(
        self,
        feedspine_storage: Any,
        entity_store: SqliteStore | None = None,
        mic_registry: MICRegistry | None = None,
        lei_registry: LEIRegistry | None = None,
        country_registry: CountryRegistry | None = None,
        currency_registry: CurrencyRegistry | None = None,
    ) -> None:
        """
        Initialize sync manager.
        
        Args:
            feedspine_storage: FeedSpine storage backend.
            entity_store: EntitySpine SqliteStore for entities/securities.
            mic_registry: MICRegistry to sync to.
            lei_registry: LEIRegistry to sync to.
            country_registry: CountryRegistry to sync to.
            currency_registry: CurrencyRegistry to sync to.
        """
        self._storage = feedspine_storage
        self._entity_store = entity_store
        self._mic_registry = mic_registry
        self._lei_registry = lei_registry
        self._country_registry = country_registry
        self._currency_registry = currency_registry
        self._last_sync: datetime | None = None
        self._sync_history: list[dict[str, Any]] = []

    async def collect_all(self, include: list[str] | None = None) -> dict[str, Any]:
        """
        Collect from all registered reference data feeds.
        
        Args:
            include: List of feed names to include (None = all).
            
        Returns:
            Collection statistics.
        """
        try:
            from feedspine import FeedSpine
        except ImportError:
            raise ImportError("FeedSpine required: pip install feedspine")

        from entityspine.feeds import (
            CountryFeedAdapter,
            CurrencyFeedAdapter,
            LEIFeedAdapter,
            MICFeedAdapter,
            SECTickerFeedAdapter,
        )

        # All available adapters
        adapters = {
            "sec": SECTickerFeedAdapter(),
            "mic": MICFeedAdapter(),
            "lei": LEIFeedAdapter(limit=1000),  # Limit for speed
            "country": CountryFeedAdapter(),
            "currency": CurrencyFeedAdapter(),
        }

        # Filter if include specified
        if include:
            adapters = {k: v for k, v in adapters.items() if k in include}

        # Create FeedSpine and register adapters
        spine = FeedSpine(storage=self._storage)
        for adapter in adapters.values():
            spine.register_feed(adapter)

        # Collect
        async with spine:
            result = await spine.collect()

        return {
            "total_processed": result.total_processed,
            "total_new": result.total_new,
            "total_duplicates": result.total_duplicates,
            "feeds": list(result.feed_stats.keys()),
        }

    async def sync_all(self) -> dict[str, dict[str, int]]:
        """
        Sync all collected records to EntitySpine.
        
        Returns:
            Dict mapping feed type to sync counts.
        """
        from entityspine.domain.timestamps import utc_now

        results: dict[str, dict[str, int]] = {}

        # Sync MIC
        # Always try MIC sync regardless of registry state
        new, updated = await sync_mic_to_registry(
            self._storage, self._mic_registry
        )
        results["mic"] = {"new": new, "updated": updated}

        # Sync SEC to entity store
        if self._entity_store is not None:
            stats = await sync_sec_to_store(self._storage, self._entity_store)
            results["sec"] = stats

        # Sync LEI
        # Always try LEI sync regardless of registry state
        new, updated = await sync_lei_to_registry(
            self._storage, self._lei_registry
        )
        results["lei"] = {"new": new, "updated": updated}

        # Record sync
        self._last_sync = utc_now()
        self._sync_history.append({
            "synced_at": self._last_sync,
            "results": results,
        })

        return results

    @property
    def last_sync(self) -> datetime | None:
        """When the last sync occurred."""
        return self._last_sync

    @property
    def sync_history(self) -> list[dict[str, Any]]:
        """History of sync operations."""
        return self._sync_history
