"""Tests for SqliteStore (stdlib sqlite3-based store, Tier 1)."""

from datetime import date
from pathlib import Path

from entityspine import (
    Entity,
    EntityStatus,
    EntityType,
)
from entityspine.stores import SqliteStore


class TestSqliteStoreBasics:
    """Test basic store operations."""

    def test_store_initializes(self, tmp_path: Path):
        """Test store can be initialized."""
        db_path = tmp_path / "test.db"
        store = SqliteStore(db_path)
        store.initialize()

        assert store._initialized
        assert db_path.exists()

        store.close()
        assert not store._initialized

    def test_store_in_memory(self):
        """Test in-memory store."""
        store = SqliteStore(":memory:")
        store.initialize()
        assert store._initialized
        store.close()

    def test_store_tier_attributes(self):
        """Test tier capability attributes."""
        store = SqliteStore(":memory:")

        assert store.tier == 1
        assert store.tier_name == "SQLite (stdlib)"
        assert store.supports_temporal is False


class TestSqliteStoreEntityOperations:
    """Test entity CRUD operations."""

    def test_save_and_get_entity(self, tmp_path: Path):
        """Test saving and retrieving an entity."""
        store = SqliteStore(tmp_path / "test.db")
        store.initialize()

        try:
            entity = Entity(
                primary_name="Apple Inc.",
                entity_type=EntityType.ORGANIZATION,
                status=EntityStatus.ACTIVE,
                source_system="sec",
                source_id="0000320193",
            )

            store.save_entity(entity)

            retrieved = store.get_entity(entity.entity_id)
            assert retrieved is not None
            assert retrieved.primary_name == "Apple Inc."
            assert retrieved.entity_type == EntityType.ORGANIZATION
            assert retrieved.source_system == "sec"
        finally:
            store.close()

    def test_entity_count(self, tmp_path: Path):
        """Test counting entities."""
        store = SqliteStore(tmp_path / "test.db")
        store.initialize()

        try:
            assert store.entity_count() == 0

            entity = Entity(
                primary_name="Test Corp",
                source_system="test",
            )
            store.save_entity(entity)

            assert store.entity_count() == 1
        finally:
            store.close()


class TestSqliteStoreSecJson:
    """Test loading SEC JSON data."""

    def test_load_sec_json(self, tmp_path: Path):
        """Test loading entities from SEC JSON format."""
        store = SqliteStore(tmp_path / "test.db")
        store.initialize()

        try:
            sec_data = {
                "0": {"cik_str": "320193", "ticker": "AAPL", "title": "Apple Inc."},
                "1": {"cik_str": "789019", "ticker": "MSFT", "title": "Microsoft Corporation"},
            }

            count = store.load_sec_json(sec_data)

            assert count == 2
            assert store.entity_count() == 2

            # Test CIK lookup
            entities = store.get_entities_by_cik("320193")
            assert len(entities) == 1
            assert entities[0].primary_name == "Apple Inc."

            # Test ticker lookup
            entities = store.get_entities_by_ticker("MSFT")
            assert len(entities) == 1
            assert entities[0].primary_name == "Microsoft Corporation"
        finally:
            store.close()


class TestSqliteStoreListingOperations:
    """Test listing operations."""

    def test_get_listings_by_ticker(self, tmp_path: Path):
        """Test retrieving listings by ticker."""
        store = SqliteStore(tmp_path / "test.db")
        store.initialize()

        try:
            sec_data = {
                "0": {"cik_str": "320193", "ticker": "AAPL", "title": "Apple Inc."},
            }
            store.load_sec_json(sec_data)

            listings = store.get_listings_by_ticker("AAPL")
            assert len(listings) == 1
            assert listings[0].ticker == "AAPL"
        finally:
            store.close()


class TestSqliteStoreSearch:
    """Test search operations."""

    def test_search_by_cik(self, tmp_path: Path):
        """Test searching by CIK."""
        store = SqliteStore(tmp_path / "test.db")
        store.initialize()

        try:
            sec_data = {
                "0": {"cik_str": "320193", "ticker": "AAPL", "title": "Apple Inc."},
            }
            store.load_sec_json(sec_data)

            results = store.search_entities("320193")
            assert len(results) == 1
            assert results[0][0].primary_name == "Apple Inc."
            assert results[0][1] == 1.0  # Exact match score
        finally:
            store.close()

    def test_search_by_name_like(self, tmp_path: Path):
        """Test LIKE-based name search."""
        store = SqliteStore(tmp_path / "test.db")
        store.initialize()

        try:
            sec_data = {
                "0": {"cik_str": "320193", "ticker": "AAPL", "title": "Apple Inc."},
                "1": {"cik_str": "789019", "ticker": "MSFT", "title": "Microsoft Corporation"},
            }
            store.load_sec_json(sec_data)

            # Exact match
            results = store.search_entities("apple inc.")
            assert len(results) >= 1
            assert results[0][0].primary_name == "Apple Inc."

            # Partial match
            results = store.search_entities("apple")
            assert len(results) >= 1
        finally:
            store.close()


class TestSqliteStoreTierHonesty:
    """Test tier capability honesty."""

    def test_as_of_parameter_ignored(self, tmp_path: Path):
        """Test that as_of parameter is accepted but ignored."""
        store = SqliteStore(tmp_path / "test.db")
        store.initialize()

        try:
            sec_data = {
                "0": {"cik_str": "320193", "ticker": "AAPL", "title": "Apple Inc."},
            }
            store.load_sec_json(sec_data)

            # as_of should be accepted but ignored
            listings = store.get_listings_by_ticker(
                "AAPL",
                as_of=date(2020, 1, 1),  # Historical date
            )

            # Should still return current listings
            assert len(listings) == 1
        finally:
            store.close()


class TestSqliteStoreKGAssets:
    """Test Knowledge Graph Asset CRUD operations."""

    def test_save_and_get_asset(self, tmp_path: Path):
        """Test saving and retrieving an asset."""
        from entityspine.domain import Asset, AssetStatus, AssetType

        store = SqliteStore(tmp_path / "test.db")
        store.initialize()

        try:
            asset = Asset(
                name="San Jose Manufacturing Facility",
                asset_type=AssetType.FACILITY,
                owner_entity_id="entity123",
                status=AssetStatus.ACTIVE,
            )
            store.save_asset(asset)

            retrieved = store.get_asset(asset.asset_id)
            assert retrieved is not None
            assert retrieved.name == "San Jose Manufacturing Facility"
            assert retrieved.asset_type == AssetType.FACILITY
            assert retrieved.owner_entity_id == "entity123"
        finally:
            store.close()

    def test_get_assets_by_owner(self, tmp_path: Path):
        """Test getting assets by owner entity."""
        from entityspine.domain import Asset, AssetType

        store = SqliteStore(tmp_path / "test.db")
        store.initialize()

        try:
            owner_id = "entity456"
            asset1 = Asset(
                name="Facility A", asset_type=AssetType.FACILITY, owner_entity_id=owner_id
            )
            asset2 = Asset(
                name="Data Center B", asset_type=AssetType.DATA_CENTER, owner_entity_id=owner_id
            )
            asset3 = Asset(name="Other Owner", asset_type=AssetType.PLANT, owner_entity_id="other")

            store.save_asset(asset1)
            store.save_asset(asset2)
            store.save_asset(asset3)

            assets = store.get_assets_by_owner(owner_id)
            assert len(assets) == 2
            assert all(a.owner_entity_id == owner_id for a in assets)
        finally:
            store.close()

    def test_asset_count(self, tmp_path: Path):
        """Test asset count."""
        from entityspine.domain import Asset, AssetType

        store = SqliteStore(tmp_path / "test.db")
        store.initialize()

        try:
            assert store.asset_count() == 0
            store.save_asset(Asset(name="Test", asset_type=AssetType.FACILITY))
            assert store.asset_count() == 1
        finally:
            store.close()


class TestSqliteStoreKGContracts:
    """Test Knowledge Graph Contract CRUD operations."""

    def test_save_and_get_contract(self, tmp_path: Path):
        """Test saving and retrieving a contract."""
        from decimal import Decimal

        from entityspine.domain import Contract, ContractStatus, ContractType

        store = SqliteStore(tmp_path / "test.db")
        store.initialize()

        try:
            contract = Contract(
                title="Revolving Credit Facility",
                contract_type=ContractType.CREDIT_FACILITY,
                effective_date=date(2024, 1, 1),
                termination_date=date(2029, 12, 31),
                value_usd=Decimal("500000000"),
                status=ContractStatus.ACTIVE,
            )
            store.save_contract(contract)

            retrieved = store.get_contract(contract.contract_id)
            assert retrieved is not None
            assert retrieved.title == "Revolving Credit Facility"
            assert retrieved.contract_type == ContractType.CREDIT_FACILITY
            assert retrieved.value_usd == Decimal("500000000")
            assert retrieved.effective_date == date(2024, 1, 1)
        finally:
            store.close()

    def test_contract_count(self, tmp_path: Path):
        """Test contract count."""
        from entityspine.domain import Contract, ContractType

        store = SqliteStore(tmp_path / "test.db")
        store.initialize()

        try:
            assert store.contract_count() == 0
            store.save_contract(Contract(title="Test", contract_type=ContractType.OTHER))
            assert store.contract_count() == 1
        finally:
            store.close()


class TestSqliteStoreKGProducts:
    """Test Knowledge Graph Product CRUD operations."""

    def test_save_and_get_product(self, tmp_path: Path):
        """Test saving and retrieving a product."""
        from entityspine.domain import Product, ProductStatus, ProductType

        store = SqliteStore(tmp_path / "test.db")
        store.initialize()

        try:
            product = Product(
                name="Keytruda",
                product_type=ProductType.DRUG,
                owner_entity_id="entity789",
                status=ProductStatus.ACTIVE,
            )
            store.save_product(product)

            retrieved = store.get_product(product.product_id)
            assert retrieved is not None
            assert retrieved.name == "Keytruda"
            assert retrieved.product_type == ProductType.DRUG
        finally:
            store.close()

    def test_get_products_by_owner(self, tmp_path: Path):
        """Test getting products by owner entity."""
        from entityspine.domain import Product, ProductType

        store = SqliteStore(tmp_path / "test.db")
        store.initialize()

        try:
            owner_id = "pharma_co"
            product1 = Product(
                name="Drug A", product_type=ProductType.DRUG, owner_entity_id=owner_id
            )
            product2 = Product(
                name="Drug B", product_type=ProductType.DRUG, owner_entity_id=owner_id
            )

            store.save_product(product1)
            store.save_product(product2)

            products = store.get_products_by_owner(owner_id)
            assert len(products) == 2
        finally:
            store.close()


class TestSqliteStoreKGBrands:
    """Test Knowledge Graph Brand CRUD operations."""

    def test_save_and_get_brand(self, tmp_path: Path):
        """Test saving and retrieving a brand."""
        from entityspine.domain import Brand

        store = SqliteStore(tmp_path / "test.db")
        store.initialize()

        try:
            brand = Brand(
                name="Coca-Cola",
                owner_entity_id="coke_entity",
            )
            store.save_brand(brand)

            retrieved = store.get_brand(brand.brand_id)
            assert retrieved is not None
            assert retrieved.name == "Coca-Cola"
            assert retrieved.owner_entity_id == "coke_entity"
        finally:
            store.close()

    def test_get_brands_by_owner(self, tmp_path: Path):
        """Test getting brands by owner entity."""
        from entityspine.domain import Brand

        store = SqliteStore(tmp_path / "test.db")
        store.initialize()

        try:
            owner_id = "nike_entity"
            brand1 = Brand(name="Nike", owner_entity_id=owner_id)
            brand2 = Brand(name="Jordan", owner_entity_id=owner_id)
            brand3 = Brand(name="Adidas", owner_entity_id="other")

            store.save_brand(brand1)
            store.save_brand(brand2)
            store.save_brand(brand3)

            brands = store.get_brands_by_owner(owner_id)
            assert len(brands) == 2
        finally:
            store.close()


class TestSqliteStoreKGEvents:
    """Test Knowledge Graph Event CRUD operations."""

    def test_save_and_get_event(self, tmp_path: Path):
        """Test saving and retrieving an event."""
        from entityspine.domain import Event, EventStatus, EventType

        store = SqliteStore(tmp_path / "test.db")
        store.initialize()

        try:
            event = Event(
                title="Acquisition of XYZ Corp",
                event_type=EventType.MERGER_ACQUISITION,
                occurred_on=date(2024, 3, 15),
                announced_on=date(2024, 3, 10),
                status=EventStatus.COMPLETED,
                payload={"target": "XYZ Corp", "value": 1000000000},
                confidence=0.95,
            )
            store.save_event(event)

            retrieved = store.get_event(event.event_id)
            assert retrieved is not None
            assert retrieved.title == "Acquisition of XYZ Corp"
            assert retrieved.event_type == EventType.MERGER_ACQUISITION
            assert retrieved.payload["target"] == "XYZ Corp"
            assert retrieved.confidence == 0.95
        finally:
            store.close()

    def test_get_events_by_type(self, tmp_path: Path):
        """Test getting events by type."""
        from entityspine.domain import Event, EventType

        store = SqliteStore(tmp_path / "test.db")
        store.initialize()

        try:
            event1 = Event(title="M&A 1", event_type=EventType.MERGER_ACQUISITION)
            event2 = Event(title="M&A 2", event_type=EventType.MERGER_ACQUISITION)
            event3 = Event(title="Data Breach", event_type=EventType.DATA_BREACH)

            store.save_event(event1)
            store.save_event(event2)
            store.save_event(event3)

            ma_events = store.get_events_by_type(EventType.MERGER_ACQUISITION)
            assert len(ma_events) == 2

            breach_events = store.get_events_by_type(EventType.DATA_BREACH)
            assert len(breach_events) == 1
        finally:
            store.close()

    def test_event_count(self, tmp_path: Path):
        """Test event count."""
        from entityspine.domain import Event, EventType

        store = SqliteStore(tmp_path / "test.db")
        store.initialize()

        try:
            assert store.event_count() == 0
            store.save_event(Event(title="Test", event_type=EventType.OTHER))
            assert store.event_count() == 1
        finally:
            store.close()
