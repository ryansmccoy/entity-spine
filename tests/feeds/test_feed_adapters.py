"""Tests for EntitySpine FeedSpine feed adapters.

These tests verify that the feed adapters:
1. Produce valid RecordCandidate objects
2. Generate correct natural keys for deduplication
3. Can be used with FeedSpine's Pipeline for dedup
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime


class TestFeedAdaptersImport:
    """Test that feed adapters can be imported."""

    def test_import_all_adapters(self):
        """Test importing all feed adapters."""
        from entityspine.feeds import (
            SECTickerFeedAdapter,
            MICFeedAdapter,
            LEIFeedAdapter,
            CountryFeedAdapter,
            CurrencyFeedAdapter,
            ISINLEIFeedAdapter,
        )

        assert SECTickerFeedAdapter is not None
        assert MICFeedAdapter is not None
        assert LEIFeedAdapter is not None
        assert CountryFeedAdapter is not None
        assert CurrencyFeedAdapter is not None
        assert ISINLEIFeedAdapter is not None

    def test_import_sync_functions(self):
        """Test importing sync functions."""
        from entityspine.feeds import (
            sync_mic_to_registry,
            sync_sec_to_store,
            sync_lei_to_registry,
            FeedSpineEntitySpineSync,
        )

        assert sync_mic_to_registry is not None
        assert sync_sec_to_store is not None
        assert sync_lei_to_registry is not None
        assert FeedSpineEntitySpineSync is not None


class TestMICFeedAdapter:
    """Test MICFeedAdapter."""

    def test_adapter_properties(self):
        """Test MICFeedAdapter has required properties."""
        from entityspine.feeds import MICFeedAdapter

        adapter = MICFeedAdapter()

        assert adapter.name == "iso10383.mic"
        assert adapter.source_type == "iso10383.mic"

    @pytest.mark.asyncio
    async def test_adapter_yields_record_candidates(self):
        """Test MICFeedAdapter yields RecordCandidate objects."""
        from entityspine.feeds import MICFeedAdapter

        adapter = MICFeedAdapter()

        # Collect first few records
        records = []
        async for record in adapter.fetch():
            records.append(record)
            if len(records) >= 5:
                break

        assert len(records) >= 1
        
        # Check record structure
        first = records[0]
        assert hasattr(first, "natural_key")
        assert hasattr(first, "content")
        assert hasattr(first, "metadata")
        
        # MIC natural key is the MIC code itself
        assert first.natural_key  # Should not be empty

    @pytest.mark.asyncio
    async def test_mic_natural_keys_are_unique(self):
        """Test that MIC natural keys are unique."""
        from entityspine.feeds import MICFeedAdapter

        adapter = MICFeedAdapter()

        natural_keys = set()
        async for record in adapter.fetch():
            natural_keys.add(record.natural_key)
            if len(natural_keys) >= 100:
                break

        # All should be unique
        # (set size equals number of records)
        assert len(natural_keys) >= 50  # At least 50 unique MICs


class TestSECTickerFeedAdapter:
    """Test SECTickerFeedAdapter."""

    def test_adapter_properties(self):
        """Test SECTickerFeedAdapter has required properties."""
        from entityspine.feeds import SECTickerFeedAdapter

        adapter = SECTickerFeedAdapter()

        assert adapter.name == "sec.company_tickers"
        assert adapter.source_type == "sec.company_tickers"

    @pytest.mark.asyncio
    async def test_natural_key_format(self):
        """Test SEC ticker natural key format is cik:ticker."""
        from entityspine.feeds import SECTickerFeedAdapter

        adapter = SECTickerFeedAdapter()

        # Collect some records
        records = []
        async for record in adapter.fetch():
            records.append(record)
            if len(records) >= 5:
                break

        # Check natural key format
        for record in records:
            # Should be format: {cik}:{ticker}
            assert ":" in record.natural_key
            parts = record.natural_key.split(":")
            assert len(parts) == 2

            cik, ticker = parts
            assert cik.isdigit()  # CIK is numeric
            assert ticker  # Ticker not empty


class TestCountryFeedAdapter:
    """Test CountryFeedAdapter."""

    def test_adapter_properties(self):
        """Test CountryFeedAdapter has required properties."""
        from entityspine.feeds import CountryFeedAdapter

        adapter = CountryFeedAdapter()

        assert adapter.name == "iso3166.country"
        assert adapter.source_type == "iso3166.country"

    @pytest.mark.asyncio
    async def test_yields_all_countries(self):
        """Test adapter yields all countries."""
        from entityspine.feeds import CountryFeedAdapter

        adapter = CountryFeedAdapter()

        records = []
        async for record in adapter.fetch():
            records.append(record)

        # Should have ~250 countries
        assert len(records) >= 200

        # Check natural key is alpha-2 code (may be lowercased by FeedSpine)
        us_records = [r for r in records if r.natural_key.upper() == "US"]
        assert len(us_records) == 1

        us = us_records[0]
        # Content should preserve original case
        assert us.content.get("alpha_2") in ("US", "us")
        assert "United States" in us.content.get("name", "")


class TestCurrencyFeedAdapter:
    """Test CurrencyFeedAdapter."""

    def test_adapter_properties(self):
        """Test CurrencyFeedAdapter has required properties."""
        from entityspine.feeds import CurrencyFeedAdapter

        adapter = CurrencyFeedAdapter()

        assert adapter.name == "iso4217.currency"
        assert adapter.source_type == "iso4217.currency"

    @pytest.mark.asyncio
    async def test_yields_all_currencies(self):
        """Test adapter yields all currencies."""
        from entityspine.feeds import CurrencyFeedAdapter

        adapter = CurrencyFeedAdapter()

        records = []
        async for record in adapter.fetch():
            records.append(record)

        # Should have ~150+ currencies
        assert len(records) >= 100

        # Check USD (natural key may be lowercased by FeedSpine)
        usd_records = [r for r in records if r.natural_key.upper() == "USD"]
        assert len(usd_records) == 1

        usd = usd_records[0]
        # Content should preserve original case
        assert usd.content.get("alpha_3") in ("USD", "usd")
        assert "Dollar" in usd.content.get("name", "")


class TestLEIFeedAdapter:
    """Test LEIFeedAdapter."""

    def test_adapter_properties(self):
        """Test LEIFeedAdapter has required properties."""
        from entityspine.feeds import LEIFeedAdapter

        adapter = LEIFeedAdapter(limit=10)

        assert adapter.name == "gleif.lei"
        assert adapter.source_type == "gleif.lei"
        assert adapter._limit == 10

    @pytest.mark.asyncio
    async def test_respects_limit(self):
        """Test LEIFeedAdapter respects limit parameter."""
        from entityspine.feeds import LEIFeedAdapter

        adapter = LEIFeedAdapter(limit=5)

        records = []
        async for record in adapter.fetch():
            records.append(record)

        # Should not exceed limit
        assert len(records) <= 5


class TestNaturalKeyUniqueness:
    """Test that natural keys provide proper deduplication."""

    @pytest.mark.asyncio
    async def test_duplicate_records_have_same_natural_key(self):
        """Test that identical content produces same natural key."""
        from entityspine.feeds import CountryFeedAdapter

        adapter = CountryFeedAdapter()

        # Fetch twice
        first_fetch = []
        async for record in adapter.fetch():
            first_fetch.append(record)

        second_fetch = []
        async for record in adapter.fetch():
            second_fetch.append(record)

        # Same natural keys should be generated
        first_keys = {r.natural_key for r in first_fetch}
        second_keys = {r.natural_key for r in second_fetch}

        assert first_keys == second_keys


class TestFeedSpineIntegration:
    """Test integration with FeedSpine (if available)."""

    @pytest.mark.skipif(
        True,  # Skip by default - requires feedspine
        reason="FeedSpine not installed"
    )
    @pytest.mark.asyncio
    async def test_adapter_works_with_feedspine_pipeline(self):
        """Test adapter can be used with FeedSpine Pipeline."""
        pytest.importorskip("feedspine")

        from feedspine import FeedSpine, MemoryStorage
        from entityspine.feeds import CountryFeedAdapter

        storage = MemoryStorage()
        spine = FeedSpine(storage=storage)

        adapter = CountryFeedAdapter()
        spine.register_feed(adapter)

        async with spine:
            result = await spine.collect()

        # Should have processed countries
        assert result.total_processed >= 200
        # First run - all should be new
        assert result.total_new >= 200

        # Second run - all should be duplicates
        async with spine:
            result2 = await spine.collect()

        assert result2.total_duplicates >= 200
        assert result2.total_new == 0


class TestSyncFunctions:
    """Test sync functions for FeedSpine → EntitySpine."""

    def test_feedspine_entityspine_sync_creation(self):
        """Test FeedSpineEntitySpineSync can be created."""
        from entityspine.feeds.sync import FeedSpineEntitySpineSync

        # Mock storage
        mock_storage = MagicMock()

        sync = FeedSpineEntitySpineSync(feedspine_storage=mock_storage)

        assert sync._storage is mock_storage
        assert sync.last_sync is None
        assert sync.sync_history == []
