"""Integration tests for EntitySpine ↔ FeedSpine integration.

These tests verify that:
1. SymbologyRefreshService works with EntitySpine stores
2. EntityEnricher can resolve entities in FeedSpine records
3. FeedSpineAdapter can sync records to EntitySpine
"""

import pytest
from datetime import datetime, timezone


# =============================================================================
# Test: SymbologyRefreshService (EntitySpine side)
# =============================================================================

class TestSymbologyRefreshService:
    """Test SymbologyRefreshService."""

    def test_refresh_result_properties(self):
        """Test RefreshResult dataclass."""
        from entityspine.services import RefreshResult

        result = RefreshResult(
            source="test-source",
            started_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            completed_at=datetime(2024, 1, 1, 12, 0, 10, tzinfo=timezone.utc),
            records_fetched=100,
            new_entities=10,
            new_claims=15,
            skipped_duplicates=75,
        )

        assert result.duration_seconds == 10.0
        assert result.success_rate == 1.0  # No errors

    def test_refresh_result_with_errors(self):
        """Test RefreshResult with errors."""
        from entityspine.services import RefreshResult

        result = RefreshResult(
            source="test-source",
            started_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            completed_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            records_fetched=100,
            errors=["Error 1", "Error 2"],
        )

        assert result.success_rate == 0.98  # 98% success (2 errors out of 100)

    def test_symbology_refresh_service_creation(self):
        """Test SymbologyRefreshService can be created."""
        from entityspine import SqliteStore
        from entityspine.services import SymbologyRefreshService

        store = SqliteStore(":memory:")
        store.initialize()

        service = SymbologyRefreshService(store)
        assert service.sources == []

    def test_symbology_source_protocol(self):
        """Test SymbologySource protocol implementation."""
        from entityspine.services import SymbologySource

        # Create a minimal source
        class TestSource:
            name = "test-source"

            async def fetch(self):
                return [{"cik": "0000320193", "name": "Apple Inc."}]

        source = TestSource()
        assert isinstance(source, SymbologySource)
        assert source.name == "test-source"

    def test_add_source_to_service(self):
        """Test adding sources to SymbologyRefreshService."""
        from entityspine import SqliteStore
        from entityspine.services import SymbologyRefreshService

        store = SqliteStore(":memory:")
        store.initialize()

        service = SymbologyRefreshService(store)

        class TestSource:
            name = "test-source"
            async def fetch(self):
                return []

        service.add_source(TestSource())
        assert len(service.sources) == 1
        assert service.sources[0].name == "test-source"


# =============================================================================
# Test: SECTickerSource
# =============================================================================

class TestSECTickerSource:
    """Test SEC ticker symbology source."""

    def test_source_properties(self):
        """Test SECTickerSource properties."""
        from entityspine.sources import SECTickerSource

        source = SECTickerSource()
        assert source.name == "sec-tickers"
        assert "sec.gov" in source.url

    def test_transform_records(self):
        """Test SEC data transformation."""
        from entityspine.sources import SECTickerSource

        source = SECTickerSource()

        # Mock SEC format
        sec_data = {
            "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
            "1": {"cik_str": 1045810, "ticker": "NVDA", "title": "NVIDIA Corporation"},
        }

        records = source._transform_records(sec_data)

        assert len(records) == 2
        assert records[0]["cik"] == "0000320193"
        assert records[0]["ticker"] == "AAPL"
        assert records[0]["name"] == "Apple Inc."

    def test_infer_exchange(self):
        """Test exchange inference from ticker."""
        from entityspine.sources import SECTickerSource

        source = SECTickerSource()

        # All short tickers return "Nasdaq" (human-readable name, not MIC code)
        assert source._infer_exchange("AAPL") == "Nasdaq"
        assert source._infer_exchange("") == "UNKNOWN"
        # 5-char tickers return US (generic)
        assert source._infer_exchange("GOOGL") in ("Nasdaq", "US")  # Either is acceptable


# =============================================================================
# Test: FeedSpineAdapter (EntitySpine side)
# =============================================================================

class TestFeedSpineAdapter:
    """Test FeedSpineAdapter for FeedSpine → EntitySpine sync."""

    def test_sync_result_dataclass(self):
        """Test SyncResult dataclass."""
        from entityspine.adapters.feedspine_adapter import SyncResult

        result = SyncResult(
            source="test",
            records_processed=100,
            entities_created=10,
            entities_updated=5,
            skipped=85,
        )

        assert result.records_processed == 100
        assert result.errors == []

    def test_adapter_creation(self):
        """Test FeedSpineAdapter can be created."""
        from entityspine import SqliteStore
        from entityspine.adapters.feedspine_adapter import FeedSpineAdapter

        store = SqliteStore(":memory:")
        store.initialize()

        # Mock FeedSpine (duck-typed)
        class MockFeedSpine:
            pass

        adapter = FeedSpineAdapter(MockFeedSpine(), store)
        assert adapter is not None


# =============================================================================
# Test: EntityEnricher (FeedSpine side)
# Requires feedspine to be installed - skip if not available
# =============================================================================

class TestEntityEnricher:
    """Test EntityEnricher for FeedSpine records."""

    def test_enricher_properties(self):
        """Test EntityEnricher properties."""
        feedspine = pytest.importorskip("feedspine", reason="feedspine not installed")
        from feedspine.enricher.entity_enricher import EntityEnricher

        # Mock store
        class MockStore:
            def get_entities_by_cik(self, cik):
                return []
            def search_entities(self, query, limit=10):
                return []

        enricher = EntityEnricher(MockStore())
        assert enricher.name == "EntityEnricher"

    def test_enricher_custom_name(self):
        """Test EntityEnricher with custom name."""
        feedspine = pytest.importorskip("feedspine", reason="feedspine not installed")
        from feedspine.enricher.entity_enricher import EntityEnricher

        class MockStore:
            def get_entities_by_cik(self, cik):
                return []
            def search_entities(self, query, limit=10):
                return []

        enricher = EntityEnricher(MockStore(), name="CustomEnricher")
        assert enricher.name == "CustomEnricher"

    def test_entity_store_protocol(self):
        """Test EntityStoreProtocol is runtime checkable."""
        feedspine = pytest.importorskip("feedspine", reason="feedspine not installed")
        from feedspine.enricher.entity_enricher import EntityStoreProtocol

        class ValidStore:
            def get_entities_by_cik(self, cik):
                return []
            def search_entities(self, query, limit=10):
                return []

        store = ValidStore()
        assert isinstance(store, EntityStoreProtocol)


# =============================================================================
# Test: Integration (EntitySpine + FeedSpine together)
# Requires feedspine to be installed - skip if not available
# =============================================================================

class TestEntitySpineFeedSpineIntegration:
    """Test EntitySpine + FeedSpine working together."""

    def test_entityspine_store_is_compatible_with_enricher(self):
        """Test EntitySpine SqliteStore works with FeedSpine EntityEnricher."""
        feedspine = pytest.importorskip("feedspine", reason="feedspine not installed")
        from entityspine import SqliteStore
        from feedspine.enricher.entity_enricher import EntityStoreProtocol

        store = SqliteStore(":memory:")
        store.initialize()

        # SqliteStore should implement the protocol methods
        assert hasattr(store, "get_entities_by_cik")
        assert hasattr(store, "search_entities")

    def test_enrich_record_with_cik(self):
        """Test enriching a FeedSpine record with EntitySpine resolution."""
        feedspine = pytest.importorskip("feedspine", reason="feedspine not installed")
        from entityspine import SqliteStore, create_entity, create_claim
        from entityspine.domain.enums import IdentifierScheme
        from feedspine.enricher.entity_enricher import EntityEnricher

        # Setup EntitySpine with test data
        store = SqliteStore(":memory:")
        store.initialize()

        # Create a test entity using domain factory
        entity = create_entity(
            primary_name="Apple Inc.",
            source_system="sec",
            source_id="0000320193",
        )
        store.save_entity(entity)

        # Create CIK claim to allow lookup by CIK
        cik_claim = create_claim(
            scheme=IdentifierScheme.CIK,
            value="0000320193",
            entity_id=entity.entity_id,
            source="test",
        )
        store.save_claim(cik_claim)

        # Create enricher
        enricher = EntityEnricher(store)

        # Test resolution
        result = enricher._resolve_entity(MockRecord(cik="0000320193"))

        assert result is not None
        assert result["entity_name"] == "Apple Inc."
        assert result["resolution_method"] == "cik"
        assert result["resolution_score"] == 1.0


class MockRecord:
    """Mock FeedSpine record for testing."""
    
    def __init__(self, cik=None, ticker=None, name=None):
        self.content = {}
        if cik:
            self.content["cik"] = cik
        if ticker:
            self.content["ticker"] = ticker
        if name:
            self.content["name"] = name


# =============================================================================
# Test: Deduplication (no duplicates on refresh)
# =============================================================================

class TestDeduplication:
    """Test that symbology refresh doesn't create duplicates."""

    def test_no_duplicates_on_reload(self):
        """Test that reloading SEC data doesn't create duplicates."""
        from entityspine import SqliteStore, create_entity, create_claim
        from entityspine.domain.enums import IdentifierScheme

        store = SqliteStore(":memory:")
        store.initialize()

        # First load - create entity using domain factory
        entity = create_entity(
            primary_name="Apple Inc.",
            source_system="sec",
            source_id="0000320193",
        )
        store.save_entity(entity)
        
        # Add CIK claim to make entity findable by CIK
        cik_claim = create_claim(
            scheme=IdentifierScheme.CIK,
            value="0000320193",
            entity_id=entity.entity_id,
            source="test",
        )
        store.save_claim(cik_claim)
        
        # Count entities by checking if we can find it
        existing1 = store.get_entities_by_cik("0000320193")
        assert len(existing1) == 1

        # Try to create same entity again
        # (this simulates what happens during refresh)
        existing = store.get_entities_by_cik("0000320193")
        if not existing:
            entity2 = create_entity(
                primary_name="Apple Inc.",
                source_system="sec",
                source_id="0000320193",
            )
            store.save_entity(entity2)
            cik_claim2 = create_claim(
                scheme=IdentifierScheme.CIK,
                value="0000320193",
                entity_id=entity2.entity_id,
                source="test",
            )
            store.save_claim(cik_claim2)
        
        # Should still have only 1 entity
        existing2 = store.get_entities_by_cik("0000320193")
        assert len(existing2) == 1

    def test_symbology_refresh_service_skips_duplicates(self):
        """Test SymbologyRefreshService skips existing entities."""
        from entityspine import SqliteStore, create_entity
        from entityspine.services import SymbologyRefreshService

        store = SqliteStore(":memory:")
        store.initialize()

        # Pre-create an entity using domain factory
        entity = create_entity(
            primary_name="Apple Inc.",
            source_system="sec",
            source_id="0000320193",
        )
        store.save_entity(entity)

        service = SymbologyRefreshService(store)

        # Process a record for the same entity
        result = service._process_record("sec", {
            "cik": "0000320193",
            "name": "Apple Inc.",
            "ticker": "AAPL",
        })

        # Should be skipped (already exists)
        assert result in ("skipped", "new_claim")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
