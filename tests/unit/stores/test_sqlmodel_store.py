"""Tests for SqlModelStore (ORM-based store, requires [orm] extra)."""

import pytest

# Skip entire module if sqlmodel not available
sqlmodel = pytest.importorskip("sqlmodel")

from pathlib import Path

from entityspine.adapters.orm import SqlModelStore
from entityspine.adapters.pydantic import (
    Entity,
    EntityStatus,
    EntityType,
    Listing,
    Security,
    SecurityType,
)


class TestSqlModelStoreBasics:
    """Test basic store operations."""

    def test_store_initializes(self, tmp_path: Path):
        """Test store can be initialized."""
        db_path = tmp_path / "test.db"
        store = SqlModelStore(db_path)
        store.initialize()

        assert store._initialized
        assert db_path.exists()

        store.close()
        assert not store._initialized

    def test_store_context_manager(self, tmp_path: Path):
        """Test store works as context manager."""
        db_path = tmp_path / "test.db"

        with SqlModelStore(db_path) as store:
            assert store._initialized

        # After context, should be closed
        assert not store._initialized


class TestSqlModelStoreEntityOperations:
    """Test entity CRUD operations."""

    def test_save_and_get_entity(self, tmp_path: Path):
        """Test saving and retrieving an entity.

        v2.2.3: Entity no longer has cik field - identifiers tracked via IdentifierClaim.
        Use source_system/source_id for provenance instead.
        """
        with SqlModelStore(tmp_path / "test.db") as store:
            entity = Entity(
                entity_id="01TEST",
                primary_name="Apple Inc.",
                entity_type=EntityType.ORGANIZATION,
                status=EntityStatus.ACTIVE,
                source_system="sec",
                source_id="0000320193",
            )

            saved = store.save_entity(entity)
            assert saved.entity_id == "01TEST"

            retrieved = store.get_entity("01TEST")
            assert retrieved is not None
            assert retrieved.primary_name == "Apple Inc."
            assert retrieved.source_system == "sec"
            assert retrieved.source_id == "0000320193"

    def test_get_entity_by_cik(self, tmp_path: Path):
        """Test looking up entity by CIK via source_id.

        v2.2.3: CIK is stored as source_id when source_system="sec".
        """
        with SqlModelStore(tmp_path / "test.db") as store:
            entity = Entity(
                entity_id="01TEST",
                primary_name="Apple Inc.",
                source_system="sec",
                source_id="0000320193",
            )
            store.save_entity(entity)

            # Test with padded CIK
            retrieved = store.get_entity_by_cik("0000320193")
            assert retrieved is not None
            assert retrieved.entity_id == "01TEST"

            # Test with unpadded CIK (should still find it)
            retrieved2 = store.get_entity_by_cik("320193")
            assert retrieved2 is not None
            assert retrieved2.entity_id == "01TEST"

    def test_search_entities(self, tmp_path: Path):
        """Test searching entities by name."""
        with SqlModelStore(tmp_path / "test.db") as store:
            store.save_entity(
                Entity(
                    entity_id="01APPLE",
                    primary_name="Apple Inc.",
                )
            )
            store.save_entity(
                Entity(
                    entity_id="02MICROSOFT",
                    primary_name="Microsoft Corporation",
                )
            )

            results = store.search_entities("Apple")
            assert len(results) == 1
            assert results[0].primary_name == "Apple Inc."

    def test_count_entities(self, tmp_path: Path):
        """Test counting entities."""
        with SqlModelStore(tmp_path / "test.db") as store:
            assert store.count_entities() == 0

            store.save_entity(Entity(entity_id="01", primary_name="A"))
            store.save_entity(Entity(entity_id="02", primary_name="B"))

            assert store.count_entities() == 2


class TestSqlModelStoreResolution:
    """Test resolution operations."""

    def test_resolve_by_cik(self, tmp_path: Path):
        """Test resolving entity by CIK.

        v2.2.3: CIK stored as source_id with source_system="sec".
        """
        with SqlModelStore(tmp_path / "test.db") as store:
            store.save_entity(
                Entity(
                    entity_id="01APPLE",
                    primary_name="Apple Inc.",
                    source_system="sec",
                    source_id="0000320193",
                )
            )

            result = store.resolve("320193")
            assert result.found
            assert result.entity.primary_name == "Apple Inc."

    def test_resolve_by_ticker(self, tmp_path: Path):
        """Test resolving entity by ticker."""
        with SqlModelStore(tmp_path / "test.db") as store:
            # Create entity
            entity = Entity(
                entity_id="01APPLE",
                primary_name="Apple Inc.",
            )
            store.save_entity(entity)

            # Create security
            security = Security(
                security_id="02SEC",
                entity_id="01APPLE",
                security_type=SecurityType.COMMON_STOCK,
                description="Apple Common Stock",
            )
            store.save_security(security)

            # Create listing (TICKER BELONGS HERE!)
            listing = Listing(
                listing_id="03LIST",
                security_id="02SEC",
                ticker="AAPL",
                exchange="NASDAQ",
            )
            store.save_listing(listing)

            # Resolve by ticker
            result = store.resolve("AAPL")
            assert result.found
            assert result.entity.primary_name == "Apple Inc."
            assert result.security is not None
            assert result.listing is not None
            assert result.listing.ticker == "AAPL"

    def test_resolve_not_found(self, tmp_path: Path):
        """Test resolution when entity not found."""
        with SqlModelStore(tmp_path / "test.db") as store:
            result = store.resolve("NONEXISTENT")
            assert not result.found
            assert result.entity is None

    def test_resolve_as_of_warning(self, tmp_path: Path):
        """Test that as_of generates warning in Tier 1."""
        from datetime import date

        with SqlModelStore(tmp_path / "test.db") as store:
            result = store.resolve("ANYTHING", as_of=date(2020, 1, 1))

            # Should have as_of_ignored warning
            assert result.has_warnings
            assert any("as_of_ignored" in w for w in result.warnings)


class TestSqlModelStoreSecJson:
    """Test SEC JSON loading."""

    def test_load_sec_json(self, tmp_path: Path):
        """Test loading entities from SEC JSON format.

        v2.2.3: CIK is stored as source_id with source_system="sec".
        """
        sec_data = {
            "0": {"cik_str": "320193", "ticker": "AAPL", "title": "Apple Inc."},
            "1": {"cik_str": "789019", "ticker": "MSFT", "title": "MICROSOFT CORP"},
        }

        with SqlModelStore(tmp_path / "test.db") as store:
            count = store.load_sec_json(sec_data)
            assert count == 2

            # Check Apple was loaded
            result = store.resolve("AAPL")
            assert result.found
            # CIK stored as source_id
            assert result.entity.source_system == "sec"
            assert result.entity.source_id == "0000320193"

            # Check Microsoft was loaded
            result = store.resolve("789019")
            assert result.found
            assert "MICROSOFT" in result.entity.primary_name.upper()


class TestSqlModelStoreTierCapabilities:
    """Test tier capability attributes."""

    def test_tier_attributes(self, tmp_path: Path):
        """Test store has correct tier attributes."""
        store = SqlModelStore(tmp_path / "test.db")

        assert store.tier == 1
        assert store.tier_name == "SQLite (SQLModel)"
        assert store.supports_temporal is False
