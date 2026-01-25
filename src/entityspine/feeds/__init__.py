"""
EntitySpine Feed Adapters for FeedSpine Integration.

This module provides FeedSpine-compatible adapters for EntitySpine's
reference data sources, enabling:

- Automatic incremental updates (only fetch new/changed data)
- Deduplication via natural keys (content hash, LEI, MIC, etc.)
- Bronze/Silver/Gold layer progression
- Checkpointing for resumable long-running fetches
- Sighting tracking for change detection

Available Adapters:
- SECTickerFeedAdapter: SEC company tickers with exchange mapping
- MICFeedAdapter: ISO 10383 Market Identifier Codes  
- LEIFeedAdapter: GLEIF Legal Entity Identifiers
- CountryFeedAdapter: ISO 3166 Country Codes
- CurrencyFeedAdapter: ISO 4217 Currency Codes
- ISINLEIFeedAdapter: GLEIF ISIN-to-LEI mappings

Example:
    >>> from feedspine import FeedSpine, MemoryStorage
    >>> from entityspine.feeds import MICFeedAdapter, SECTickerFeedAdapter
    >>>
    >>> async def refresh_reference_data():
    ...     storage = MemoryStorage()
    ...     spine = FeedSpine(storage=storage)
    ...     
    ...     # Register reference data feeds
    ...     spine.register_feed(MICFeedAdapter())
    ...     spine.register_feed(SECTickerFeedAdapter())
    ...     
    ...     # Collect - only new/changed records stored
    ...     result = await spine.collect()
    ...     print(f"New: {result.total_new}, Duplicates: {result.total_duplicates}")

Integration with EntitySpine:
    The adapters produce RecordCandidates that can be:
    1. Stored in FeedSpine storage (Bronze layer)
    2. Promoted to Silver after validation
    3. Used to update EntitySpine registries (Gold layer)
    
    See entityspine.feeds.sync for syncing FeedSpine records to EntitySpine.
"""

from entityspine.feeds.adapters import (
    CountryFeedAdapter,
    CurrencyFeedAdapter,
    ISINLEIFeedAdapter,
    LEIFeedAdapter,
    MICFeedAdapter,
    SECTickerFeedAdapter,
)
from entityspine.feeds.sync import (
    FeedSpineEntitySpineSync,
    sync_lei_to_registry,
    sync_mic_to_registry,
    sync_sec_to_store,
)

__all__ = [
    # Adapters
    "SECTickerFeedAdapter",
    "MICFeedAdapter",
    "LEIFeedAdapter",
    "CountryFeedAdapter",
    "CurrencyFeedAdapter",
    "ISINLEIFeedAdapter",

    # Sync utilities
    "sync_mic_to_registry",
    "sync_sec_to_store",
    "sync_lei_to_registry",
    "FeedSpineEntitySpineSync",
]
