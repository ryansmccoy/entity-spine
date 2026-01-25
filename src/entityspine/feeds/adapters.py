"""
FeedSpine Adapters for EntitySpine Reference Data Sources.

These adapters wrap EntitySpine sources to produce FeedSpine RecordCandidates,
enabling automatic deduplication, incremental updates, and change tracking.

Each adapter:
1. Fetches from the authoritative source (SEC, GLEIF, ISO)
2. Yields RecordCandidate objects with natural keys
3. FeedSpine handles deduplication via natural_key
4. New records go to Bronze layer, duplicates tracked as sightings

Natural Key Strategy:
- MIC: The MIC code itself (e.g., "XNYS")
- LEI: The LEI code (e.g., "549300S4KLFTLO7GSQ80")
- SEC Ticker: "{cik}:{ticker}" (e.g., "0000320193:AAPL")
- Country: ISO alpha-2 code (e.g., "US")
- Currency: ISO alpha-3 code (e.g., "USD")
- ISIN-LEI: The ISIN (e.g., "US0378331005")
"""

from __future__ import annotations

import hashlib
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

# Check if feedspine is available
try:
    from feedspine.models.base import Metadata
    from feedspine.models.record import RecordCandidate
    FEEDSPINE_AVAILABLE = True
except ImportError:
    FEEDSPINE_AVAILABLE = False
    # Stub classes for when FeedSpine not installed
    class Metadata:  # type: ignore
        def __init__(self, **kwargs: Any) -> None:
            for k, v in kwargs.items():
                setattr(self, k, v)
    class RecordCandidate:  # type: ignore
        def __init__(self, **kwargs: Any) -> None:
            for k, v in kwargs.items():
                setattr(self, k, v)


class EntitySpineFeedAdapter:
    """
    Base class for EntitySpine feed adapters.
    
    This provides a standalone implementation that works with or without
    FeedSpine installed. When FeedSpine is available, these adapters
    implement the FeedAdapter protocol for seamless integration.
    
    Subclasses implement:
    - _fetch_candidates(): AsyncIterator yielding RecordCandidate
    """
    
    def __init__(self, name: str, source_type: str | None = None) -> None:
        """Initialize adapter.
        
        Args:
            name: Adapter identifier.
            source_type: Type of source for metadata.
        """
        self._name = name
        self._source_type = source_type or name
        self._initialized = False
    
    @property
    def name(self) -> str:
        """Adapter name."""
        return self._name
    
    @property
    def source_type(self) -> str:
        """Source type for metadata."""
        return self._source_type
    
    async def initialize(self) -> None:
        """Initialize the adapter."""
        self._initialized = True
    
    async def close(self) -> None:
        """Clean up resources."""
        self._initialized = False
    
    async def __aenter__(self) -> "EntitySpineFeedAdapter":
        """Async context manager entry."""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()
    
    async def fetch(self) -> AsyncIterator[RecordCandidate]:
        """Fetch records from the source.
        
        Yields:
            RecordCandidate for each item.
        """
        # Subclasses override this
        raise NotImplementedError("Subclass must implement fetch()")


def _content_hash(content: dict[str, Any]) -> str:
    """Generate a stable content hash for change detection."""
    import json
    serialized = json.dumps(content, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode()).hexdigest()[:16]


# =============================================================================
# SEC Ticker Feed Adapter
# =============================================================================


class SECTickerFeedAdapter(EntitySpineFeedAdapter):
    """
    FeedSpine adapter for SEC company tickers.
    
    Natural Key: "{cik}:{ticker}" (e.g., "0000320193:AAPL")
    
    This enables:
    - Detecting new public company listings
    - Tracking ticker changes over time
    - Detecting exchange transfers
    
    Example:
        >>> from entityspine.feeds import SECTickerFeedAdapter
        >>> adapter = SECTickerFeedAdapter()
        >>> # Use with FeedSpine
        >>> # async for candidate in adapter.fetch():
        >>> #     print(candidate.natural_key)
    """
    
    def __init__(self) -> None:
        super().__init__(name="sec.company_tickers", source_type="sec.company_tickers")
        self._source = None
    
    async def initialize(self) -> None:
        """Initialize the SEC source."""
        from entityspine.sources import SECTickerSource
        self._source = SECTickerSource()
    
    async def close(self) -> None:
        """Clean up resources."""
        self._source = None
    
    async def fetch(self) -> AsyncIterator[RecordCandidate]:
        """Fetch SEC tickers and yield RecordCandidates."""
        if self._source is None:
            await self.initialize()
        
        records = await self._source.fetch()
        snapshot = self._source.last_snapshot
        
        for record in records:
            cik = record["cik"]
            ticker = record["ticker"]
            natural_key = f"{cik}:{ticker}"
            
            content = {
                "cik": cik,
                "ticker": ticker,
                "name": record["name"],
                "exchange": record["exchange"],
                "mic": record["mic"],
                "content_hash": _content_hash(record),
            }
            
            yield RecordCandidate(
                natural_key=natural_key,
                published_at=snapshot.captured_at if snapshot else datetime.now(UTC),
                content=content,
                metadata=Metadata(
                    source=self.name,
                    source_type="sec.company_tickers",
                    extra={
                        "snapshot_id": snapshot.snapshot_id if snapshot else None,
                        "source_url": snapshot.source_url if snapshot else None,
                    },
                ),
            )


# =============================================================================
# ISO 10383 MIC Feed Adapter
# =============================================================================


class MICFeedAdapter(EntitySpineFeedAdapter):
    """
    FeedSpine adapter for ISO 10383 MIC codes.
    
    Natural Key: MIC code (e.g., "XNYS")
    
    Change detection via content hash enables tracking:
    - New exchanges/venues
    - Name changes
    - Status changes (ACTIVE -> EXPIRED)
    - LEI updates
    
    Example:
        >>> from entityspine.feeds import MICFeedAdapter
        >>> adapter = MICFeedAdapter()
        >>> adapter.name
        'iso10383.mic'
    """
    
    def __init__(self) -> None:
        super().__init__(name="iso10383.mic", source_type="iso10383.mic")
        self._source = None
    
    async def initialize(self) -> None:
        """Initialize the ISO 10383 source."""
        from entityspine.sources import ISO10383Source
        self._source = ISO10383Source()
    
    async def close(self) -> None:
        """Clean up resources."""
        self._source = None
    
    async def fetch(self) -> AsyncIterator[RecordCandidate]:
        """Fetch MIC codes and yield RecordCandidates."""
        if self._source is None:
            await self.initialize()
        
        records = await self._source.fetch_as_records()
        snapshot = self._source.last_snapshot
        
        for record in records:
            content = {
                "mic": record.mic,
                "operating_mic": record.operating_mic,
                "mic_type": record.mic_type,
                "name": record.name,
                "legal_entity_name": record.legal_entity_name,
                "lei": record.lei,
                "market_category_code": record.market_category_code,
                "acronym": record.acronym,
                "country_code": record.country_code,
                "city": record.city,
                "website": record.website,
                "status": record.status,
            }
            content["content_hash"] = _content_hash(content)
            
            yield RecordCandidate(
                natural_key=record.mic,
                published_at=snapshot.captured_at if snapshot else datetime.now(UTC),
                content=content,
                metadata=Metadata(
                    source=self.name,
                    source_type="iso10383.mic",
                    extra={
                        "snapshot_id": snapshot.snapshot_id if snapshot else None,
                        "country_code": record.country_code,
                        "mic_type": record.mic_type,
                    },
                ),
            )


# =============================================================================
# GLEIF LEI Feed Adapter
# =============================================================================


class LEIFeedAdapter(EntitySpineFeedAdapter):
    """
    FeedSpine adapter for GLEIF LEI data.
    
    Natural Key: LEI code (e.g., "549300S4KLFTLO7GSQ80")
    
    Supports:
    - Single LEI lookups (API-based)
    - Bulk fetch (Golden Copy download)
    - Search by name
    
    Example:
        >>> from entityspine.feeds import LEIFeedAdapter
        >>> adapter = LEIFeedAdapter(mode="search", query="NVIDIA")
        >>> adapter.name
        'gleif.lei'
    """
    
    def __init__(
        self,
        mode: str = "bulk",  # "bulk", "single", or "search"
        query: str | None = None,  # For search mode
        lei: str | None = None,  # For single mode
        limit: int | None = None,  # For bulk mode
    ) -> None:
        super().__init__(name="gleif.lei", source_type="gleif.lei")
        self._source = None
        self._mode = mode
        self._query = query
        self._lei = lei
        self._limit = limit
    
    async def initialize(self) -> None:
        """Initialize the GLEIF source."""
        from entityspine.sources import GLEIFSource
        self._source = GLEIFSource()
    
    async def close(self) -> None:
        """Clean up resources."""
        self._source = None
    
    async def fetch(self) -> AsyncIterator[RecordCandidate]:
        """Fetch LEI records and yield RecordCandidates."""
        if self._source is None:
            await self.initialize()
        
        if self._mode == "single" and self._lei:
            # Single LEI lookup
            record = await self._source.lookup_lei(self._lei)
            if record:
                yield self._record_to_candidate(record)
        else:
            # Bulk fetch
            records = await self._source.fetch_as_records(limit=self._limit)
            for record in records:
                yield self._record_to_candidate(record)
    
    def _record_to_candidate(self, record: Any) -> RecordCandidate:
        """Convert LEIRecord to RecordCandidate."""
        content = {
            "lei": record.lei,
            "legal_name": record.legal_name,
            "legal_address_country": record.legal_address_country,
            "legal_address_city": record.legal_address_city,
            "hq_address_country": record.hq_address_country,
            "hq_address_city": record.hq_address_city,
            "legal_jurisdiction": record.legal_jurisdiction,
            "entity_category": record.entity_category,
            "entity_status": record.entity_status,
            "registration_status": record.registration_status,
        }
        content["content_hash"] = _content_hash(content)
        
        return RecordCandidate(
            natural_key=record.lei,
            published_at=record.captured_at or datetime.now(UTC),
            content=content,
            metadata=Metadata(
                source=self.name,
                source_type="gleif.lei",
                extra={
                    "snapshot_id": record.snapshot_id,
                    "jurisdiction": record.legal_jurisdiction,
                    "entity_status": record.entity_status,
                },
            ),
        )


# =============================================================================
# ISO 3166 Country Feed Adapter
# =============================================================================


class CountryFeedAdapter(EntitySpineFeedAdapter):
    """
    FeedSpine adapter for ISO 3166 country codes.
    
    Natural Key: ISO alpha-2 code (e.g., "US")
    
    Example:
        >>> from entityspine.feeds import CountryFeedAdapter
        >>> adapter = CountryFeedAdapter()
        >>> adapter.name
        'iso3166.country'
    """
    
    def __init__(self) -> None:
        super().__init__(name="iso3166.country", source_type="iso3166.country")
        self._source = None
    
    async def initialize(self) -> None:
        """Initialize the ISO 3166 source."""
        from entityspine.sources import ISO3166Source
        self._source = ISO3166Source()
    
    async def close(self) -> None:
        """Clean up resources."""
        self._source = None
    
    async def fetch(self) -> AsyncIterator[RecordCandidate]:
        """Fetch country records and yield RecordCandidates."""
        if self._source is None:
            await self.initialize()
        
        snapshot, records = await self._source.fetch()
        
        for record in records:
            # Normalize to uppercase for consistency
            alpha2 = record.alpha2.upper() if record.alpha2 else ""
            alpha3 = record.alpha3.upper() if record.alpha3 else None
            
            content = {
                "alpha_2": alpha2,
                "alpha_3": alpha3,
                "numeric": record.numeric,
                "name": record.name,
                "official_name": record.official_name,
                "region": record.region,
                "subregion": record.subregion,
            }
            content["content_hash"] = _content_hash(content)
            
            yield RecordCandidate(
                natural_key=alpha2,  # Normalized to uppercase
                published_at=snapshot.captured_at if snapshot else datetime.now(UTC),
                content=content,
                metadata=Metadata(
                    source=self.name,
                    source_type="iso3166.country",
                    extra={
                        "snapshot_id": snapshot.snapshot_id if snapshot else None,
                        "region": record.region,
                    },
                ),
            )


# =============================================================================
# ISO 4217 Currency Feed Adapter
# =============================================================================


class CurrencyFeedAdapter(EntitySpineFeedAdapter):
    """
    FeedSpine adapter for ISO 4217 currency codes.
    
    Natural Key: ISO alpha-3 code (e.g., "USD")
    
    Example:
        >>> from entityspine.feeds import CurrencyFeedAdapter
        >>> adapter = CurrencyFeedAdapter()
        >>> adapter.name
        'iso4217.currency'
    """
    
    def __init__(self) -> None:
        super().__init__(name="iso4217.currency", source_type="iso4217.currency")
        self._source = None
    
    async def initialize(self) -> None:
        """Initialize the ISO 4217 source."""
        from entityspine.sources import ISO4217Source
        self._source = ISO4217Source()
    
    async def close(self) -> None:
        """Clean up resources."""
        self._source = None
    
    async def fetch(self) -> AsyncIterator[RecordCandidate]:
        """Fetch currency records and yield RecordCandidates."""
        if self._source is None:
            await self.initialize()
        
        snapshot, records = await self._source.fetch()
        
        for record in records:
            content = {
                "alpha_3": record.alpha3,
                "numeric": record.numeric,
                "name": record.name,
                "minor_unit": record.minor_unit,
                "countries": record.countries if hasattr(record, 'countries') else [],
                "is_fund": record.is_fund if hasattr(record, 'is_fund') else False,
            }
            content["content_hash"] = _content_hash(content)
            
            yield RecordCandidate(
                natural_key=record.alpha3,
                published_at=snapshot.captured_at if snapshot else datetime.now(UTC),
                content=content,
                metadata=Metadata(
                    source=self.name,
                    source_type="iso4217.currency",
                    extra={
                        "snapshot_id": snapshot.snapshot_id if snapshot else None,
                        "minor_unit": record.minor_unit,
                    },
                ),
            )


# =============================================================================
# GLEIF ISIN-LEI Mapping Feed Adapter
# =============================================================================


class ISINLEIFeedAdapter(EntitySpineFeedAdapter):
    """
    FeedSpine adapter for GLEIF ISIN-to-LEI mappings.
    
    Natural Key: ISIN (e.g., "US0378331005")
    
    This mapping file connects securities (via ISIN) to their issuers (via LEI).
    ~8 million mappings.
    
    Example:
        >>> from entityspine.feeds import ISINLEIFeedAdapter
        >>> adapter = ISINLEIFeedAdapter()
        >>> adapter.name
        'gleif.isin_lei'
    """
    
    def __init__(self, limit: int | None = None) -> None:
        super().__init__(name="gleif.isin_lei", source_type="gleif.isin_lei")
        self._source = None
        self._limit = limit
    
    async def initialize(self) -> None:
        """Initialize the GLEIF ISIN-LEI source."""
        from entityspine.sources import GLEIFISINLEISource
        self._source = GLEIFISINLEISource()
    
    async def close(self) -> None:
        """Clean up resources."""
        self._source = None
    
    async def fetch(self) -> AsyncIterator[RecordCandidate]:
        """Fetch ISIN-LEI mappings and yield RecordCandidates."""
        if self._source is None:
            await self.initialize()
        
        records = await self._source.fetch()
        snapshot = self._source.last_snapshot
        
        for record in records:
            content = {
                "isin": record["isin"],
                "lei": record["lei"],
                "isin_status": record.get("isin_status"),
                "lei_status": record.get("lei_status"),
            }
            content["content_hash"] = _content_hash(content)
            
            yield RecordCandidate(
                natural_key=record["isin"],
                published_at=snapshot.captured_at if snapshot else datetime.now(UTC),
                content=content,
                metadata=Metadata(
                    source=self.name,
                    source_type="gleif.isin_lei",
                    extra={
                        "snapshot_id": snapshot.snapshot_id if snapshot else None,
                        "lei": record["lei"],
                    },
                ),
            )
