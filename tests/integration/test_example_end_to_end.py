"""
Integration test for the end-to-end SEC filing to Knowledge Graph example.

This test validates that:
1. SEC tickers can be loaded into SqliteStore
2. Entity resolution works (ticker, CIK, name search)
3. Filing facts payload can be ingested into KG nodes/edges
4. Tier honesty warnings are generated when as_of cannot be honored
5. KG queries return correct counts

Requirements:
- Only stdlib + entityspine core
- Runtime < 2 seconds

Author: EntitySpine Team
"""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from entityspine.core.timestamps import utc_now
from entityspine.core.ulid import generate_ulid
from entityspine.domain import (
    Address,
    Asset,
    AssetStatus,
    AssetType,
    Brand,
    Contract,
    ContractStatus,
    ContractType,
    Entity,
    EntityStatus,
    EntityType,
    Event,
    EventStatus,
    EventType,
    Geo,
    GeoType,
    NodeRef,
    Product,
    ProductStatus,
    ProductType,
    Relationship,
    RelationshipType,
    ResolutionTier,
    RoleAssignment,
    RoleType,
    compute_address_hash,
    found_result,
)
from entityspine.stores import SqliteStore

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def fixtures_dir() -> Path:
    """Return path to fixtures directory."""
    return Path(__file__).parent.parent.parent / "examples" / "fixtures"


@pytest.fixture
def sec_tickers_data(fixtures_dir: Path) -> dict:
    """Load SEC tickers sample data."""
    path = fixtures_dir / "sec_company_tickers_sample.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def filing_facts_data(fixtures_dir: Path) -> dict:
    """Load mock filing facts payload."""
    path = fixtures_dir / "mock_filing_facts_10k.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def store() -> SqliteStore:
    """Create an in-memory SqliteStore for testing."""
    s = SqliteStore(":memory:")
    s.initialize()
    yield s
    s.close()


@pytest.fixture
def loaded_store(store: SqliteStore, sec_tickers_data: dict) -> SqliteStore:
    """SqliteStore with SEC tickers pre-loaded."""
    store.load_sec_json(sec_tickers_data)
    return store


# ============================================================================
# SECTION A: TIER 1 SETUP TESTS
# ============================================================================


class TestTier1Setup:
    """Test SEC ticker loading and basic resolution."""

    def test_load_sec_tickers(self, store: SqliteStore, sec_tickers_data: dict):
        """Loading SEC tickers creates entities, securities, listings, and claims."""
        count = store.load_sec_json(sec_tickers_data)

        assert count == 10
        assert store.entity_count() == 10
        assert store.security_count() == 10
        assert store.listing_count() == 10
        assert store.claim_count() >= 10  # At least CIK claims

    def test_resolve_by_ticker(self, loaded_store: SqliteStore):
        """Resolution by ticker returns correct entity."""
        results = loaded_store.get_entities_by_ticker("AAPL")

        assert len(results) == 1
        assert results[0].primary_name == "Apple Inc."

    def test_resolve_by_cik(self, loaded_store: SqliteStore):
        """Resolution by CIK returns correct entity."""
        results = loaded_store.get_entities_by_cik("320193")

        assert len(results) == 1
        assert results[0].primary_name == "Apple Inc."

    def test_resolve_by_padded_cik(self, loaded_store: SqliteStore):
        """Resolution works with zero-padded CIK."""
        results = loaded_store.get_entities_by_cik("0000320193")

        assert len(results) == 1
        assert results[0].primary_name == "Apple Inc."

    def test_search_by_name(self, loaded_store: SqliteStore):
        """Search by name returns matching entities."""
        results = loaded_store.search_entities("Apple Inc.", limit=3)

        assert len(results) >= 1
        entity, _score = results[0]
        assert "Apple" in entity.primary_name


# ============================================================================
# SECTION B: FILING FACTS INGESTION TESTS
# ============================================================================


class TestFilingFactsIngestion:
    """Test ingestion of filing facts into KG nodes."""

    def test_create_person_entity(self, loaded_store: SqliteStore):
        """Can create person entities for officers."""
        person_id = generate_ulid()
        person = Entity(
            entity_id=person_id,
            primary_name="Timothy D. Cook",
            entity_type=EntityType.PERSON,
            status=EntityStatus.ACTIVE,
            source_system="sec_edgar",
        )
        loaded_store.save_entity(person)

        retrieved = loaded_store.get_entity(person_id)
        assert retrieved is not None
        assert retrieved.primary_name == "Timothy D. Cook"
        assert retrieved.entity_type == EntityType.PERSON

    def test_create_role_assignment(self, loaded_store: SqliteStore):
        """Can create role assignments linking person to org."""
        # Get Apple entity
        entities = loaded_store.get_entities_by_ticker("AAPL")
        apple = entities[0]

        # Create person
        person_id = generate_ulid()
        person = Entity(
            entity_id=person_id,
            primary_name="Timothy D. Cook",
            entity_type=EntityType.PERSON,
            status=EntityStatus.ACTIVE,
            source_system="sec_edgar",
        )
        loaded_store.save_entity(person)

        # Create role assignment
        role = RoleAssignment(
            role_assignment_id=generate_ulid(),
            person_entity_id=person_id,
            org_entity_id=apple.entity_id,
            role_type=RoleType.CEO,
            title="Chief Executive Officer",
            start_date=date(2011, 8, 24),
            confidence=1.0,
            captured_at=utc_now(),
            source_system="sec_edgar",
        )
        loaded_store.save_role_assignment(role)

        # Verify
        roles = loaded_store.get_role_assignments_by_org(apple.entity_id)
        assert len(roles) == 1
        assert roles[0].role_type == RoleType.CEO
        assert roles[0].person_entity_id == person_id

    def test_create_geo_hierarchy(self, loaded_store: SqliteStore):
        """Can create geographic hierarchy (country → state → city)."""
        # Country
        us = Geo(
            geo_id="geo_us",
            name="United States",
            geo_type=GeoType.COUNTRY,
            iso_code="US",
        )
        loaded_store.save_geo(us)

        # State
        ca = Geo(
            geo_id="geo_ca",
            name="California",
            geo_type=GeoType.STATE,
            parent_geo_id="geo_us",
        )
        loaded_store.save_geo(ca)

        # City
        cupertino = Geo(
            geo_id="geo_cupertino",
            name="Cupertino",
            geo_type=GeoType.CITY,
            parent_geo_id="geo_ca",
        )
        loaded_store.save_geo(cupertino)

        # Verify
        assert loaded_store.geo_count() == 3

        retrieved = loaded_store.get_geo("geo_cupertino")
        assert retrieved is not None
        assert retrieved.name == "Cupertino"
        assert retrieved.parent_geo_id == "geo_ca"

    def test_create_address_with_hash(self, loaded_store: SqliteStore):
        """Can create address with normalized hash for deduplication."""
        addr_hash = compute_address_hash(
            line1="One Apple Park Way",
            line2=None,
            city="Cupertino",
            region="CA",
            postal="95014",
            country="US",
        )

        address = Address(
            address_id=generate_ulid(),
            line1="One Apple Park Way",
            city="Cupertino",
            region="CA",
            postal="95014",
            country="US",
            normalized_hash=addr_hash,
        )
        loaded_store.save_address(address)

        # Verify
        assert loaded_store.address_count() == 1

        retrieved = loaded_store.get_address(address.address_id)
        assert retrieved is not None
        assert retrieved.line1 == "One Apple Park Way"
        assert retrieved.normalized_hash == addr_hash

    def test_create_contract(self, loaded_store: SqliteStore):
        """Can create material contract."""
        contract = Contract(
            contract_id="contract_001",
            title="Semiconductor Supply Agreement",
            contract_type=ContractType("supply"),  # lowercase 'supply'
            effective_date=date(2023, 1, 1),
            value_usd=Decimal("5000000000"),
            status=ContractStatus.ACTIVE,
            source_system="sec_edgar",
        )
        loaded_store.save_contract(contract)

        assert loaded_store.contract_count() == 1

        retrieved = loaded_store.get_contract("contract_001")
        assert retrieved is not None
        assert retrieved.value_usd == Decimal("5000000000")

    def test_create_product(self, loaded_store: SqliteStore):
        """Can create product."""
        entities = loaded_store.get_entities_by_ticker("AAPL")
        apple = entities[0]

        product = Product(
            product_id="product_001",
            name="iPhone",
            product_type=ProductType.CONSUMER_GOOD,
            owner_entity_id=apple.entity_id,
            status=ProductStatus.ACTIVE,
            source_system="sec_edgar",
        )
        loaded_store.save_product(product)

        assert loaded_store.product_count() == 1

        products = loaded_store.get_products_by_owner(apple.entity_id)
        assert len(products) == 1
        assert products[0].name == "iPhone"

    def test_create_brand(self, loaded_store: SqliteStore):
        """Can create brand."""
        entities = loaded_store.get_entities_by_ticker("AAPL")
        apple = entities[0]

        brand = Brand(
            brand_id="brand_001",
            name="Apple",
            owner_entity_id=apple.entity_id,
            source_system="sec_edgar",
        )
        loaded_store.save_brand(brand)

        assert loaded_store.brand_count() == 1

        brands = loaded_store.get_brands_by_owner(apple.entity_id)
        assert len(brands) == 1
        assert brands[0].name == "Apple"

    def test_create_asset(self, loaded_store: SqliteStore):
        """Can create asset with geo/address links."""
        entities = loaded_store.get_entities_by_ticker("AAPL")
        apple = entities[0]

        asset = Asset(
            asset_id="asset_001",
            name="Apple Park Campus",
            asset_type=AssetType.FACILITY,
            owner_entity_id=apple.entity_id,
            status=AssetStatus.ACTIVE,
            source_system="sec_edgar",
        )
        loaded_store.save_asset(asset)

        assert loaded_store.asset_count() == 1

        assets = loaded_store.get_assets_by_owner(apple.entity_id)
        assert len(assets) == 1
        assert assets[0].name == "Apple Park Campus"

    def test_create_event(self, loaded_store: SqliteStore):
        """Can create KG event (acquisition)."""
        event = Event(
            event_id="event_001",
            event_type=EventType.MERGER_ACQUISITION,
            title="Acquisition of XYZ Labs Inc.",
            status=EventStatus.COMPLETED,
            announced_on=date(2023, 6, 15),
            occurred_on=date(2023, 9, 1),
            source_system="sec_edgar",
        )
        loaded_store.save_event(event)

        assert loaded_store.event_count() == 1

    def test_create_relationship(self, loaded_store: SqliteStore):
        """Can create generic relationship between nodes."""
        entities = loaded_store.get_entities_by_ticker("AAPL")
        apple = entities[0]

        # Create geo
        cupertino = Geo(
            geo_id="geo_cupertino",
            name="Cupertino",
            geo_type=GeoType.CITY,
        )
        loaded_store.save_geo(cupertino)

        # Create LOCATED_IN relationship
        rel = Relationship(
            relationship_id=generate_ulid(),
            source_ref=NodeRef.entity(apple.entity_id),
            target_ref=NodeRef.geo("geo_cupertino"),
            relationship_type=RelationshipType.LOCATED_IN,
            confidence=1.0,
            source_system="sec_edgar",
        )
        loaded_store.save_relationship(rel)

        assert loaded_store.relationship_count() == 1

        rels = loaded_store.get_relationships_by_source_id(apple.entity_id)
        assert len(rels) == 1
        assert rels[0].relationship_type == RelationshipType.LOCATED_IN


# ============================================================================
# SECTION C: TIER HONESTY TESTS
# ============================================================================


class TestTierHonesty:
    """Test tier capability warnings."""

    def test_as_of_warning_generated(self, loaded_store: SqliteStore):
        """Tier 1 generates warning when as_of cannot be honored."""
        entities = loaded_store.get_entities_by_ticker("AAPL")
        entity = entities[0]

        # Create result with as_of that can't be honored
        result = found_result(
            entity=entity,
            query="AAPL",
            tier=ResolutionTier.TIER_1,
            as_of=date(2015, 1, 1),
            as_of_honored=False,
        )
        result.add_as_of_ignored_warning()

        assert result.as_of_honored is False
        assert len(result.warnings) == 1
        assert "as_of parameter ignored" in result.warnings[0]

    def test_tier_1_limits_set(self, loaded_store: SqliteStore):
        """Tier 1 result includes capability limits."""
        entities = loaded_store.get_entities_by_ticker("AAPL")
        entity = entities[0]

        result = found_result(
            entity=entity,
            query="AAPL",
            tier=ResolutionTier.TIER_1,
        )
        result.set_tier_1_limits()

        assert "temporal_resolution" in result.limits
        assert result.limits["temporal_resolution"] == "best_effort"


# ============================================================================
# SECTION D: KG QUERY TESTS
# ============================================================================


class TestKGQueries:
    """Test knowledge graph query capabilities."""

    def test_count_all_node_types(self, loaded_store: SqliteStore):
        """All count methods work after loading fixtures."""
        # Base counts from SEC tickers
        assert loaded_store.entity_count() == 10
        assert loaded_store.security_count() == 10
        assert loaded_store.listing_count() == 10
        assert loaded_store.claim_count() >= 10

        # KG counts (start at 0)
        assert loaded_store.geo_count() == 0
        assert loaded_store.address_count() == 0
        assert loaded_store.role_assignment_count() == 0
        assert loaded_store.relationship_count() == 0
        assert loaded_store.asset_count() == 0
        assert loaded_store.contract_count() == 0
        assert loaded_store.product_count() == 0
        assert loaded_store.brand_count() == 0
        assert loaded_store.event_count() == 0

    def test_get_role_assignments_by_org(self, loaded_store: SqliteStore):
        """Can query role assignments by organization."""
        entities = loaded_store.get_entities_by_ticker("AAPL")
        apple = entities[0]

        # Create some roles
        for role_type, name in [(RoleType.CEO, "Tim Cook"), (RoleType.CFO, "Luca Maestri")]:
            person_id = generate_ulid()
            person = Entity(
                entity_id=person_id,
                primary_name=name,
                entity_type=EntityType.PERSON,
                status=EntityStatus.ACTIVE,
                source_system="test",
            )
            loaded_store.save_entity(person)

            role = RoleAssignment(
                role_assignment_id=generate_ulid(),
                person_entity_id=person_id,
                org_entity_id=apple.entity_id,
                role_type=role_type,
                confidence=1.0,
                captured_at=utc_now(),
                source_system="test",
            )
            loaded_store.save_role_assignment(role)

        roles = loaded_store.get_role_assignments_by_org(apple.entity_id)
        assert len(roles) == 2
        role_types = {r.role_type for r in roles}
        assert RoleType.CEO in role_types
        assert RoleType.CFO in role_types

    def test_get_relationships_by_source(self, loaded_store: SqliteStore):
        """Can query relationships by source entity."""
        entities = loaded_store.get_entities_by_ticker("AAPL")
        apple = entities[0]

        # Create SEC entity
        sec_id = generate_ulid()
        sec = Entity(
            entity_id=sec_id,
            primary_name="SEC",
            entity_type=EntityType.GOVERNMENT,
            status=EntityStatus.ACTIVE,
            source_system="test",
        )
        loaded_store.save_entity(sec)

        # Create REGULATED_BY relationship
        rel = Relationship(
            relationship_id=generate_ulid(),
            source_ref=NodeRef.entity(apple.entity_id),
            target_ref=NodeRef.entity(sec_id),
            relationship_type=RelationshipType.REGULATED_BY,
            confidence=1.0,
            source_system="test",
        )
        loaded_store.save_relationship(rel)

        rels = loaded_store.get_relationships_by_source_id(apple.entity_id)
        assert len(rels) == 1
        assert rels[0].relationship_type == RelationshipType.REGULATED_BY


# ============================================================================
# INTEGRATION TEST: FULL PAYLOAD
# ============================================================================


class TestFullPayloadIntegration:
    """Full integration test using actual fixture files."""

    def test_full_payload_ingestion(
        self,
        loaded_store: SqliteStore,
        filing_facts_data: dict,
    ):
        """
        Full integration test: ingest entire mock_filing_facts_10k.json payload.

        This mirrors what the actual example script does.
        """
        # Get issuer
        issuer_cik = filing_facts_data["issuer"]["cik"].lstrip("0")
        entities = loaded_store.get_entities_by_cik(issuer_cik)
        assert len(entities) == 1
        issuer = entities[0]

        # Track what we create
        person_ids: dict[str, str] = {}
        role_count = 0

        # Create officers
        for officer in filing_facts_data.get("officers", []):
            person_id = generate_ulid()
            person = Entity(
                entity_id=person_id,
                primary_name=officer["name"],
                entity_type=EntityType.PERSON,
                status=EntityStatus.ACTIVE,
                source_system="sec_edgar",
            )
            loaded_store.save_entity(person)
            person_ids[officer["person_id"]] = person_id

            # Create role
            role = RoleAssignment(
                role_assignment_id=generate_ulid(),
                person_entity_id=person_id,
                org_entity_id=issuer.entity_id,
                role_type=RoleType(officer["role_type"]),  # enum values are lowercase
                title=officer.get("title"),
                confidence=1.0,
                captured_at=utc_now(),
                source_system="sec_edgar",
            )
            loaded_store.save_role_assignment(role)
            role_count += 1

        # Create directors
        for director in filing_facts_data.get("directors", []):
            person_id = generate_ulid()
            person = Entity(
                entity_id=person_id,
                primary_name=director["name"],
                entity_type=EntityType.PERSON,
                status=EntityStatus.ACTIVE,
                source_system="sec_edgar",
            )
            loaded_store.save_entity(person)
            person_ids[director["person_id"]] = person_id

            role = RoleAssignment(
                role_assignment_id=generate_ulid(),
                person_entity_id=person_id,
                org_entity_id=issuer.entity_id,
                role_type=RoleType.DIRECTOR,
                title=director.get("title"),
                confidence=1.0,
                captured_at=utc_now(),
                source_system="sec_edgar",
            )
            loaded_store.save_role_assignment(role)
            role_count += 1

        # Create geos
        for geo_data in filing_facts_data.get("geo_hierarchy", []):
            geo = Geo(
                geo_id=geo_data["geo_id"],
                name=geo_data["name"],
                geo_type=GeoType(geo_data["geo_type"]),  # enum values are lowercase
                parent_geo_id=geo_data.get("parent_geo_id"),
            )
            loaded_store.save_geo(geo)

        # Create address
        hq = filing_facts_data.get("headquarters", {})
        if hq:
            addr_hash = compute_address_hash(
                line1=hq.get("line1", ""),
                line2=hq.get("line2"),  # required parameter
                city=hq.get("city", ""),
                region=hq.get("region", ""),
                postal=hq.get("postal", ""),
                country=hq.get("country", "US"),
            )
            address = Address(
                address_id=generate_ulid(),
                line1=hq.get("line1"),
                city=hq.get("city"),
                region=hq.get("region"),
                postal=hq.get("postal"),
                country=hq.get("country", "US"),
                normalized_hash=addr_hash,
            )
            loaded_store.save_address(address)

        # Create contracts
        for contract_data in filing_facts_data.get("material_contracts", []):
            contract = Contract(
                contract_id=contract_data["contract_id"],
                title=contract_data["title"],
                contract_type=ContractType(
                    contract_data["contract_type"]
                ),  # enum values are lowercase
                value_usd=Decimal(str(contract_data.get("value_usd", 0))),
                status=ContractStatus.ACTIVE,
                source_system="sec_edgar",
            )
            loaded_store.save_contract(contract)

        # Create products
        for product_data in filing_facts_data.get("products", []):
            product = Product(
                product_id=product_data["product_id"],
                name=product_data["name"],
                product_type=ProductType(product_data["product_type"]),  # enum values are lowercase
                owner_entity_id=issuer.entity_id,
                status=ProductStatus.ACTIVE,
                source_system="sec_edgar",
            )
            loaded_store.save_product(product)

        # Create brands
        for brand_data in filing_facts_data.get("brands", []):
            brand = Brand(
                brand_id=brand_data["brand_id"],
                name=brand_data["name"],
                owner_entity_id=issuer.entity_id,
                source_system="sec_edgar",
            )
            loaded_store.save_brand(brand)

        # Create assets
        for asset_data in filing_facts_data.get("assets", []):
            asset = Asset(
                asset_id=asset_data["asset_id"],
                name=asset_data["name"],
                asset_type=AssetType(asset_data["asset_type"]),  # enum values are lowercase
                owner_entity_id=issuer.entity_id,
                status=AssetStatus.ACTIVE,
                source_system="sec_edgar",
            )
            loaded_store.save_asset(asset)

        # Create events
        for event_data in filing_facts_data.get("events", []):
            event = Event(
                event_id=event_data["event_id"],
                event_type=EventType(event_data["event_type"]),  # enum values are lowercase
                title=event_data["title"],
                status=EventStatus(
                    event_data.get("status", "announced")
                ),  # enum values are lowercase
                source_system="sec_edgar",
            )
            loaded_store.save_event(event)

        # Verify all counts
        assert loaded_store.entity_count() == 10 + len(person_ids)  # SEC tickers + persons
        assert loaded_store.role_assignment_count() == role_count
        assert loaded_store.geo_count() == len(filing_facts_data.get("geo_hierarchy", []))
        assert loaded_store.address_count() == (1 if hq else 0)
        assert loaded_store.contract_count() == len(filing_facts_data.get("material_contracts", []))
        assert loaded_store.product_count() == len(filing_facts_data.get("products", []))
        assert loaded_store.brand_count() == len(filing_facts_data.get("brands", []))
        assert loaded_store.asset_count() == len(filing_facts_data.get("assets", []))
        assert loaded_store.event_count() == len(filing_facts_data.get("events", []))


# ============================================================================
# PERFORMANCE TEST
# ============================================================================


class TestPerformance:
    """Verify integration tests complete in reasonable time."""

    def test_full_integration_under_2_seconds(
        self,
        loaded_store: SqliteStore,
        filing_facts_data: dict,
    ):
        """Full integration should complete in under 2 seconds."""
        import time

        start = time.perf_counter()

        # Run a subset of operations
        entities = loaded_store.get_entities_by_ticker("AAPL")
        _ = loaded_store.get_entities_by_cik("320193")
        _ = loaded_store.search_entities("Apple", limit=5)

        # Create some nodes
        for i in range(10):
            geo = Geo(
                geo_id=f"perf_geo_{i}",
                name=f"Test City {i}",
                geo_type=GeoType.CITY,
            )
            loaded_store.save_geo(geo)

        elapsed = time.perf_counter() - start
        assert elapsed < 2.0, f"Integration test took {elapsed:.2f}s, expected < 2s"
