"""
Tests for Knowledge Graph domain models.

Tests verify:
1. Enum expansion doesn't break existing behavior
2. Creating a PERSON Entity works
3. RoleAssignment requires person and org
4. Relationship NodeRef validates kind/id
5. New models are stdlib dataclasses (no Pydantic)
"""

import dataclasses
from datetime import date
from decimal import Decimal

import pytest


class TestEntityTypeExpansion:
    """Test that EntityType enum expansion doesn't break existing behavior."""

    def test_organization_type_exists(self):
        """ORGANIZATION type should exist."""
        from entityspine.domain import EntityType

        assert EntityType.ORGANIZATION.value == "organization"

    def test_person_type_exists(self):
        """PERSON type should exist."""
        from entityspine.domain import EntityType

        assert EntityType.PERSON.value == "person"

    def test_new_entity_types_exist(self):
        """All new entity types should exist."""
        from entityspine.domain import EntityType

        expected_types = [
            "organization",
            "person",
            "government",
            "fund",
            "trust",
            "partnership",
            "spv",
            "exchange",
            "geo",
            "unknown",
        ]

        actual_values = [e.value for e in EntityType]

        for expected in expected_types:
            assert expected in actual_values, f"EntityType.{expected.upper()} not found"

    def test_entity_type_is_str_enum(self):
        """EntityType should be a str enum for JSON serialization."""
        from entityspine.domain import EntityType

        # Should be usable as string via .value
        assert EntityType.PERSON.value == "person"
        # String comparison should work
        assert EntityType.PERSON == "person"


class TestPersonEntity:
    """Test creating PERSON type entities."""

    def test_create_person_entity(self):
        """Should be able to create a person entity."""
        from entityspine.domain import Entity, EntityType

        person = Entity(
            primary_name="John Doe",
            entity_type=EntityType.PERSON,
        )

        assert person.primary_name == "John Doe"
        assert person.entity_type == EntityType.PERSON
        assert person.entity_id  # Should have auto-generated ULID

    def test_person_entity_with_source(self):
        """Person entity should track source system."""
        from entityspine.domain import Entity, EntityType

        person = Entity(
            primary_name="Jane Smith",
            entity_type=EntityType.PERSON,
            source_system="sec_form4",
            source_id="0001234567-24-000123",
        )

        assert person.source_system == "sec_form4"
        assert person.source_id == "0001234567-24-000123"


class TestNewEnums:
    """Test new Knowledge Graph enums."""

    def test_role_type_enum(self):
        """RoleType enum should have expected values."""
        from entityspine.domain import RoleType

        # C-Suite
        assert RoleType.CEO.value == "ceo"
        assert RoleType.CFO.value == "cfo"

        # Board
        assert RoleType.DIRECTOR.value == "director"
        assert RoleType.CHAIR.value == "chair"

        # Ownership
        assert RoleType.BENEFICIAL_OWNER_10PCT.value == "beneficial_owner_10pct"

    def test_case_type_enum(self):
        """CaseType enum should have expected values."""
        from entityspine.domain import CaseType

        assert CaseType.LAWSUIT.value == "lawsuit"
        assert CaseType.INVESTIGATION.value == "investigation"
        assert CaseType.ENFORCEMENT.value == "enforcement"
        assert CaseType.BANKRUPTCY.value == "bankruptcy"

    def test_geo_type_enum(self):
        """GeoType enum should have expected values."""
        from entityspine.domain import GeoType

        assert GeoType.COUNTRY.value == "country"
        assert GeoType.STATE.value == "state"
        assert GeoType.CITY.value == "city"

    def test_relationship_type_additions(self):
        """RelationshipType should have KG-specific values."""
        from entityspine.domain import RelationshipType

        # New relationship types
        assert RelationshipType.BENEFICIAL_OWNER_OF.value == "beneficial_owner_of"
        assert RelationshipType.OFFICER_OF.value == "officer_of"
        assert RelationshipType.DIRECTOR_OF.value == "director_of"
        assert RelationshipType.EMPLOYED_BY.value == "employed_by"
        assert RelationshipType.REGULATED_BY.value == "regulated_by"
        assert RelationshipType.LISTED_ON.value == "listed_on"
        assert RelationshipType.LOCATED_IN.value == "located_in"


class TestNodeRef:
    """Test NodeRef polymorphic reference."""

    def test_create_entity_ref(self):
        """NodeRef.entity() should create entity reference."""
        from entityspine.domain import NodeKind, NodeRef

        ref = NodeRef.entity("01ARZ3NDEKTSV4RRFFQ69G5FAV")

        assert ref.kind == NodeKind.ENTITY
        assert ref.id == "01ARZ3NDEKTSV4RRFFQ69G5FAV"

    def test_create_security_ref(self):
        """NodeRef.security() should create security reference."""
        from entityspine.domain import NodeKind, NodeRef

        ref = NodeRef.security("01ARZ3NDEKTSV4RRFFQ69G5FAV")

        assert ref.kind == NodeKind.SECURITY
        assert ref.id == "01ARZ3NDEKTSV4RRFFQ69G5FAV"

    def test_create_case_ref(self):
        """NodeRef.case() should create case reference."""
        from entityspine.domain import NodeKind, NodeRef

        ref = NodeRef.case("01ARZ3NDEKTSV4RRFFQ69G5FAV")

        assert ref.kind == NodeKind.CASE
        assert ref.id == "01ARZ3NDEKTSV4RRFFQ69G5FAV"

    def test_node_ref_validation(self):
        """NodeRef should validate id is not empty."""
        from entityspine.domain import NodeKind, NodeRef

        with pytest.raises(ValueError, match="cannot be empty"):
            NodeRef(kind=NodeKind.ENTITY, id="")

        with pytest.raises(ValueError, match="cannot be empty"):
            NodeRef(kind=NodeKind.ENTITY, id="   ")

    def test_node_ref_str(self):
        """NodeRef __str__ should return kind:id format."""
        from entityspine.domain import NodeRef

        ref = NodeRef.entity("abc123")
        assert str(ref) == "entity:abc123"

    def test_node_ref_is_frozen(self):
        """NodeRef should be immutable."""
        from entityspine.domain import NodeRef

        ref = NodeRef.entity("abc123")

        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            ref.id = "new_id"


class TestRoleAssignment:
    """Test RoleAssignment model."""

    def test_create_role_assignment(self):
        """Should create role assignment with required fields."""
        from entityspine.domain import RoleAssignment, RoleType

        role = RoleAssignment(
            person_entity_id="person_123",
            org_entity_id="org_456",
            role_type=RoleType.CEO,
        )

        assert role.person_entity_id == "person_123"
        assert role.org_entity_id == "org_456"
        assert role.role_type == RoleType.CEO
        assert role.role_assignment_id  # Auto-generated

    def test_role_assignment_with_dates(self):
        """Role assignment should support start/end dates."""
        from entityspine.domain import RoleAssignment, RoleType

        role = RoleAssignment(
            person_entity_id="person_123",
            org_entity_id="org_456",
            role_type=RoleType.CFO,
            start_date=date(2020, 1, 15),
            end_date=date(2023, 6, 30),
        )

        assert role.start_date == date(2020, 1, 15)
        assert role.end_date == date(2023, 6, 30)
        assert not role.is_current  # End date is in the past

    def test_role_assignment_is_current(self):
        """is_current should reflect active roles."""
        from entityspine.domain import RoleAssignment, RoleType

        # No end date = current
        current_role = RoleAssignment(
            person_entity_id="p1",
            org_entity_id="o1",
            role_type=RoleType.DIRECTOR,
        )
        assert current_role.is_current

        # Future end date = current
        future_role = RoleAssignment(
            person_entity_id="p1",
            org_entity_id="o1",
            role_type=RoleType.DIRECTOR,
            end_date=date(2099, 12, 31),
        )
        assert future_role.is_current

    def test_role_assignment_is_dataclass(self):
        """RoleAssignment should be a stdlib dataclass."""
        from entityspine.domain import RoleAssignment

        assert dataclasses.is_dataclass(RoleAssignment)


class TestGeo:
    """Test Geo geographic model."""

    def test_create_country(self):
        """Should create a country Geo node."""
        from entityspine.domain import Geo, GeoType

        usa = Geo(
            name="United States",
            geo_type=GeoType.COUNTRY,
            iso_code="US",
        )

        assert usa.name == "United States"
        assert usa.geo_type == GeoType.COUNTRY
        assert usa.iso_code == "US"

    def test_create_state_with_parent(self):
        """State can reference parent country."""
        from entityspine.domain import Geo, GeoType

        ca = Geo(
            name="California",
            geo_type=GeoType.STATE,
            iso_code="US-CA",
            parent_geo_id="usa_geo_id",
        )

        assert ca.geo_type == GeoType.STATE
        assert ca.parent_geo_id == "usa_geo_id"

    def test_geo_requires_name(self):
        """Geo should require a name."""
        from entityspine.domain import Geo, GeoType

        with pytest.raises(ValueError, match="name cannot be empty"):
            Geo(name="", geo_type=GeoType.COUNTRY)


class TestCase:
    """Test Case (legal proceedings) model."""

    def test_create_lawsuit(self):
        """Should create a lawsuit case."""
        from entityspine.domain import Case, CaseType

        case = Case(
            case_type=CaseType.LAWSUIT,
            title="SEC v. XYZ Corp",
            case_number="24-cv-12345",
        )

        assert case.case_type == CaseType.LAWSUIT
        assert case.title == "SEC v. XYZ Corp"
        assert case.case_number == "24-cv-12345"

    def test_create_investigation(self):
        """Should create an investigation case."""
        from entityspine.domain import Case, CaseStatus, CaseType

        case = Case(
            case_type=CaseType.INVESTIGATION,
            title="SEC Investigation of ABC Inc.",
            status=CaseStatus.OPEN,
            opened_date=date(2024, 3, 15),
        )

        assert case.case_type == CaseType.INVESTIGATION
        assert case.status == CaseStatus.OPEN
        assert case.is_open

    def test_case_with_entities(self):
        """Case can reference authority and target entities."""
        from entityspine.domain import Case, CaseType

        case = Case(
            case_type=CaseType.ENFORCEMENT,
            title="SEC Enforcement Action",
            authority_entity_id="sec_entity_id",
            target_entity_id="company_entity_id",
        )

        assert case.authority_entity_id == "sec_entity_id"
        assert case.target_entity_id == "company_entity_id"

    def test_case_requires_title(self):
        """Case should require a title."""
        from entityspine.domain import Case, CaseType

        with pytest.raises(ValueError, match="title cannot be empty"):
            Case(case_type=CaseType.LAWSUIT, title="")


class TestRelationship:
    """Test generic Relationship model with NodeRef."""

    def test_create_relationship(self):
        """Should create a relationship between nodes."""
        from entityspine.domain import NodeRef, Relationship, RelationshipType

        rel = Relationship(
            source_ref=NodeRef.entity("company_id"),
            target_ref=NodeRef.geo("location_id"),
            relationship_type=RelationshipType.LOCATED_IN,
        )

        assert rel.source_ref.kind.value == "entity"
        assert rel.target_ref.kind.value == "geo"
        assert rel.relationship_type == RelationshipType.LOCATED_IN

    def test_relationship_with_evidence(self):
        """Relationship should support evidence pointers."""
        from entityspine.domain import NodeRef, Relationship, RelationshipType

        rel = Relationship(
            source_ref=NodeRef.entity("child_id"),
            target_ref=NodeRef.entity("parent_id"),
            relationship_type=RelationshipType.SUBSIDIARY,
            evidence_filing_id="filing_123",
            evidence_snippet="XYZ Corp is a wholly-owned subsidiary...",
            confidence=0.95,
        )

        assert rel.evidence_filing_id == "filing_123"
        assert rel.evidence_snippet is not None
        assert rel.confidence == 0.95

    def test_relationship_is_current(self):
        """is_current should check valid_to date."""
        from entityspine.domain import NodeRef, Relationship, RelationshipType

        # No valid_to = current
        current = Relationship(
            source_ref=NodeRef.entity("a"),
            target_ref=NodeRef.entity("b"),
            relationship_type=RelationshipType.PARTNER,
        )
        assert current.is_current


class TestAddress:
    """Test Address model."""

    def test_create_address(self):
        """Should create an address."""
        from entityspine.domain import Address

        addr = Address(
            line1="123 Main St",
            city="San Francisco",
            region="CA",
            postal="94105",
            country="US",
        )

        assert addr.line1 == "123 Main St"
        assert addr.city == "San Francisco"
        assert addr.country == "US"

    def test_address_display(self):
        """Address display property should format nicely."""
        from entityspine.domain import Address

        addr = Address(
            line1="123 Main St",
            city="San Francisco",
            region="CA",
            postal="94105",
            country="US",
        )

        display = addr.display
        assert "123 Main St" in display
        assert "San Francisco" in display
        assert "CA" in display


class TestValidators:
    """Test new person/address validators."""

    def test_normalize_person_name(self):
        """Person name normalization should clean up whitespace."""
        from entityspine.domain import normalize_person_name

        assert normalize_person_name("  john   doe  ") == "John Doe"
        assert normalize_person_name("JANE SMITH") == "Jane Smith"
        assert normalize_person_name(None) is None

    def test_normalize_person_name_for_search(self):
        """Search normalization should lowercase and remove punctuation."""
        from entityspine.domain import normalize_person_name_for_search

        assert normalize_person_name_for_search("John Q. Doe, Jr.") == "john q doe jr"
        assert normalize_person_name_for_search("JANE SMITH") == "jane smith"

    def test_normalize_country_code(self):
        """Country code should be uppercase 2-letter."""
        from entityspine.domain import normalize_country_code

        assert normalize_country_code("us") == "US"
        assert normalize_country_code("  gb  ") == "GB"
        assert normalize_country_code(None) is None

    def test_compute_address_hash(self):
        """Address hash should be consistent for matching."""
        from entityspine.domain import compute_address_hash

        hash1 = compute_address_hash(
            line1="123 Main St",
            line2=None,
            city="San Francisco",
            region="CA",
            postal="94105",
            country="US",
        )

        # Same address should get same hash
        hash2 = compute_address_hash(
            line1="123 Main St",
            line2=None,
            city="San Francisco",
            region="CA",
            postal="94105",
            country="US",
        )

        assert hash1 == hash2
        assert len(hash1) == 32  # Truncated SHA256

    def test_validate_person_name(self):
        """Person name validation should check for letters."""
        from entityspine.domain import validate_person_name

        is_valid, error = validate_person_name("John Doe")
        assert is_valid

        is_valid, error = validate_person_name("")
        assert not is_valid
        assert "empty" in error

        is_valid, error = validate_person_name("12345")
        assert not is_valid
        assert "letter" in error


class TestModelsAreDataclasses:
    """Test that all new models are stdlib dataclasses (no Pydantic)."""

    def test_node_ref_is_dataclass(self):
        from entityspine.domain import NodeRef

        assert dataclasses.is_dataclass(NodeRef)

    def test_geo_is_dataclass(self):
        from entityspine.domain import Geo

        assert dataclasses.is_dataclass(Geo)

    def test_case_is_dataclass(self):
        from entityspine.domain import Case

        assert dataclasses.is_dataclass(Case)

    def test_relationship_is_dataclass(self):
        from entityspine.domain import Relationship

        assert dataclasses.is_dataclass(Relationship)

    def test_role_assignment_is_dataclass(self):
        from entityspine.domain import RoleAssignment

        assert dataclasses.is_dataclass(RoleAssignment)

    def test_address_is_dataclass(self):
        from entityspine.domain import Address

        assert dataclasses.is_dataclass(Address)

    def test_entity_address_is_dataclass(self):
        from entityspine.domain import EntityAddress

        assert dataclasses.is_dataclass(EntityAddress)

    def test_entity_relationship_is_dataclass(self):
        from entityspine.domain import EntityRelationship

        assert dataclasses.is_dataclass(EntityRelationship)

    def test_entity_cluster_is_dataclass(self):
        from entityspine.domain import EntityCluster

        assert dataclasses.is_dataclass(EntityCluster)


class TestSqliteGraphTables:
    """Test that SQLite store creates graph tables."""

    def test_sqlite_store_creates_graph_tables(self):
        """SQLite store should create all graph tables."""
        from entityspine.stores import SqliteStore

        store = SqliteStore(":memory:")
        store.initialize()

        # Query to list all tables using internal method
        with store._get_connection() as conn:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            tables = [row[0] for row in cursor.fetchall()]

        # Check graph tables exist
        expected_tables = [
            "addresses",
            "cases",
            "entity_addresses",
            "entity_cluster_members",
            "entity_clusters",
            "entity_relationships",
            "geos",
            "relationships",
            "role_assignments",
        ]

        for table in expected_tables:
            assert table in tables, f"Table '{table}' not found in SQLite schema"

    def test_sqlite_store_role_assignments_indexes(self):
        """Role assignments table should have proper indexes."""
        from entityspine.stores import SqliteStore

        store = SqliteStore(":memory:")
        store.initialize()

        with store._get_connection() as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE '%role_assignments%'"
            )
            indexes = [row[0] for row in cursor.fetchall()]

        assert len(indexes) >= 3  # At least person, org, role type indexes


# =============================================================================
# v2.2.4 KG High-Confidence Node Tests
# =============================================================================


class TestAssetModel:
    """Test Asset domain model (v2.2.4)."""

    def test_asset_creation(self):
        """Asset can be created with required fields."""
        from entityspine.domain import Asset, AssetType

        asset = Asset(name="San Jose Manufacturing Facility", asset_type=AssetType.FACILITY)

        assert asset.name == "San Jose Manufacturing Facility"
        assert asset.asset_type == AssetType.FACILITY
        assert asset.asset_id  # Auto-generated

    def test_asset_with_owner(self):
        """Asset can have owner_entity_id."""
        from entityspine.domain import Asset, AssetStatus, AssetType

        asset = Asset(
            name="Boeing 737 Fleet",
            asset_type=AssetType.AIRCRAFT,
            owner_entity_id="01ENTITY123",
            status=AssetStatus.ACTIVE,
        )

        assert asset.owner_entity_id == "01ENTITY123"
        assert asset.status == AssetStatus.ACTIVE

    def test_asset_requires_name(self):
        """Asset must have non-empty name."""
        from entityspine.domain import Asset, AssetType

        with pytest.raises(ValueError, match="name cannot be empty"):
            Asset(name="", asset_type=AssetType.FACILITY)

    def test_asset_types_exist(self):
        """All asset types should exist."""
        from entityspine.domain import AssetType

        expected = [
            "facility",
            "data_center",
            "vessel",
            "aircraft",
            "plant",
            "property",
            "equipment",
            "vehicle",
            "inventory",
            "ip",
            "other",
        ]
        actual = [e.value for e in AssetType]

        for exp in expected:
            assert exp in actual, f"AssetType.{exp.upper()} not found"

    def test_asset_is_dataclass(self):
        """Asset should be a stdlib dataclass."""
        from entityspine.domain import Asset

        assert dataclasses.is_dataclass(Asset)


class TestContractModel:
    """Test Contract domain model (v2.2.4)."""

    def test_contract_creation(self):
        """Contract can be created with required fields."""
        from entityspine.domain import Contract, ContractType

        contract = Contract(
            title="Revolving Credit Facility", contract_type=ContractType.CREDIT_FACILITY
        )

        assert contract.title == "Revolving Credit Facility"
        assert contract.contract_type == ContractType.CREDIT_FACILITY
        assert contract.contract_id  # Auto-generated

    def test_contract_with_dates(self):
        """Contract can have effective and termination dates."""
        from entityspine.domain import Contract, ContractStatus, ContractType

        contract = Contract(
            title="Office Lease Agreement",
            contract_type=ContractType.LEASE,
            effective_date=date(2024, 1, 1),
            termination_date=date(2029, 12, 31),
            status=ContractStatus.ACTIVE,
        )

        assert contract.effective_date == date(2024, 1, 1)
        assert contract.termination_date == date(2029, 12, 31)

    def test_contract_with_value(self):
        """Contract can have USD value."""
        from entityspine.domain import Contract, ContractType

        contract = Contract(
            title="Material Agreement",
            contract_type=ContractType.MATERIAL_AGREEMENT,
            value_usd=Decimal("500000000"),  # $500M
        )

        assert contract.value_usd == Decimal("500000000")

    def test_contract_is_active_property(self):
        """Contract.is_active property works correctly."""
        from entityspine.domain import Contract, ContractStatus, ContractType

        # Active contract
        active = Contract(
            title="Active Contract",
            contract_type=ContractType.LICENSE,
            status=ContractStatus.ACTIVE,
            termination_date=date(2030, 1, 1),
        )
        assert active.is_active is True

        # Expired contract
        expired = Contract(
            title="Expired Contract",
            contract_type=ContractType.LICENSE,
            status=ContractStatus.EXPIRED,
        )
        assert expired.is_active is False

    def test_contract_requires_title(self):
        """Contract must have non-empty title."""
        from entityspine.domain import Contract, ContractType

        with pytest.raises(ValueError, match="title cannot be empty"):
            Contract(title="", contract_type=ContractType.OTHER)

    def test_contract_types_exist(self):
        """All contract types should exist."""
        from entityspine.domain import ContractType

        expected = [
            "credit_facility",
            "lease",
            "material_agreement",
            "supply",
            "license",
            "employment",
            "merger",
            "joint_venture",
            "service",
            "distribution",
            "settlement",
            "other",
        ]
        actual = [e.value for e in ContractType]

        for exp in expected:
            assert exp in actual, f"ContractType.{exp} not found"

    def test_contract_is_dataclass(self):
        """Contract should be a stdlib dataclass."""
        from entityspine.domain import Contract

        assert dataclasses.is_dataclass(Contract)


class TestProductModel:
    """Test Product domain model (v2.2.4)."""

    def test_product_creation(self):
        """Product can be created with required fields."""
        from entityspine.domain import Product, ProductType

        product = Product(name="Keytruda", product_type=ProductType.DRUG)

        assert product.name == "Keytruda"
        assert product.product_type == ProductType.DRUG
        assert product.product_id  # Auto-generated

    def test_product_with_owner(self):
        """Product can have owner_entity_id."""
        from entityspine.domain import Product, ProductStatus, ProductType

        product = Product(
            name="iPhone",
            product_type=ProductType.CONSUMER_GOOD,
            owner_entity_id="01ENTITY456",
            status=ProductStatus.ACTIVE,
        )

        assert product.owner_entity_id == "01ENTITY456"
        assert product.status == ProductStatus.ACTIVE

    def test_product_requires_name(self):
        """Product must have non-empty name."""
        from entityspine.domain import Product, ProductType

        with pytest.raises(ValueError, match="name cannot be empty"):
            Product(name="", product_type=ProductType.SOFTWARE)

    def test_product_types_exist(self):
        """All product types should exist."""
        from entityspine.domain import ProductType

        expected = [
            "drug",
            "device",
            "software",
            "service",
            "consumer_good",
            "industrial",
            "financial",
            "food_beverage",
            "vehicle",
            "other",
        ]
        actual = [e.value for e in ProductType]

        for exp in expected:
            assert exp in actual, f"ProductType.{exp} not found"

    def test_product_is_dataclass(self):
        """Product should be a stdlib dataclass."""
        from entityspine.domain import Product

        assert dataclasses.is_dataclass(Product)


class TestBrandModel:
    """Test Brand domain model (v2.2.4)."""

    def test_brand_creation(self):
        """Brand can be created with required fields."""
        from entityspine.domain import Brand

        brand = Brand(name="Nike")

        assert brand.name == "Nike"
        assert brand.brand_id  # Auto-generated

    def test_brand_with_owner(self):
        """Brand can have owner_entity_id."""
        from entityspine.domain import Brand

        brand = Brand(name="Coca-Cola", owner_entity_id="01ENTITY789")

        assert brand.owner_entity_id == "01ENTITY789"

    def test_brand_requires_name(self):
        """Brand must have non-empty name."""
        from entityspine.domain import Brand

        with pytest.raises(ValueError, match="name cannot be empty"):
            Brand(name="")

    def test_brand_is_dataclass(self):
        """Brand should be a stdlib dataclass."""
        from entityspine.domain import Brand

        assert dataclasses.is_dataclass(Brand)


class TestEventModel:
    """Test Event domain model (v2.2.4)."""

    def test_event_creation(self):
        """Event can be created with required fields."""
        from entityspine.domain import Event, EventType

        event = Event(title="Acquisition of XYZ Corp", event_type=EventType.MERGER_ACQUISITION)

        assert event.title == "Acquisition of XYZ Corp"
        assert event.event_type == EventType.MERGER_ACQUISITION
        assert event.event_id  # Auto-generated

    def test_event_with_dates(self):
        """Event can have occurred_on and announced_on dates."""
        from entityspine.domain import Event, EventStatus, EventType

        event = Event(
            title="Data Breach Incident",
            event_type=EventType.DATA_BREACH,
            occurred_on=date(2024, 3, 15),
            announced_on=date(2024, 3, 20),
            status=EventStatus.COMPLETED,
        )

        assert event.occurred_on == date(2024, 3, 15)
        assert event.announced_on == date(2024, 3, 20)
        assert event.status == EventStatus.COMPLETED

    def test_event_with_payload(self):
        """Event can have payload dict."""
        from entityspine.domain import Event, EventType

        event = Event(
            title="Leadership Change",
            event_type=EventType.MANAGEMENT,
            payload={"old_ceo": "John Smith", "new_ceo": "Jane Doe"},
        )

        assert event.payload["old_ceo"] == "John Smith"
        assert event.payload["new_ceo"] == "Jane Doe"

    def test_event_with_evidence(self):
        """Event can have evidence pointers."""
        from entityspine.domain import Event, EventType

        event = Event(
            title="Material Contract",
            event_type=EventType.LEGAL,
            evidence_filing_id="filing-123",
            evidence_section_id="section-456",
            evidence_snippet="On March 15, 2024, the Company entered into...",
            confidence=0.95,
        )

        assert event.evidence_filing_id == "filing-123"
        assert event.confidence == 0.95

    def test_event_is_completed_property(self):
        """Event.is_completed property works correctly."""
        from entityspine.domain import Event, EventStatus, EventType

        completed = Event(
            title="Completed Acquisition",
            event_type=EventType.MERGER_ACQUISITION,
            status=EventStatus.COMPLETED,
        )
        assert completed.is_completed is True

        pending = Event(
            title="Pending Acquisition",
            event_type=EventType.MERGER_ACQUISITION,
            status=EventStatus.PENDING,
        )
        assert pending.is_completed is False

    def test_event_requires_title(self):
        """Event must have non-empty title."""
        from entityspine.domain import Event, EventType

        with pytest.raises(ValueError, match="title cannot be empty"):
            Event(title="", event_type=EventType.OTHER)

    def test_event_types_exist(self):
        """All event types should exist."""
        from entityspine.domain import EventType

        expected = [
            "m&a",
            "divestiture",
            "restructuring",
            "bankruptcy",
            "legal",
            "regulatory",
            "investigation",
            "enforcement",
            "cyber",
            "data_breach",
            "operational",
            "financial",
            "capital",
            "dividend",
            "mgmt",
            "board",
            "product_launch",
            "product_recall",
            "other",
        ]
        actual = [e.value for e in EventType]

        for exp in expected:
            assert exp in actual, f"EventType.{exp} not found"

    def test_event_is_dataclass(self):
        """Event should be a stdlib dataclass."""
        from entityspine.domain import Event

        assert dataclasses.is_dataclass(Event)


class TestNodeKindExpansion:
    """Test NodeKind enum expansion for v2.2.4."""

    def test_core_node_kinds_exist(self):
        """Core node kinds should exist."""
        from entityspine.domain import NodeKind

        core_kinds = ["entity", "security", "listing"]
        actual = [e.value for e in NodeKind]

        for kind in core_kinds:
            assert kind in actual, f"NodeKind.{kind.upper()} not found"

    def test_infrastructure_node_kinds_exist(self):
        """Infrastructure node kinds should exist."""
        from entityspine.domain import NodeKind

        infra_kinds = ["address", "geo", "case"]
        actual = [e.value for e in NodeKind]

        for kind in infra_kinds:
            assert kind in actual, f"NodeKind.{kind.upper()} not found"

    def test_v224_node_kinds_exist(self):
        """v2.2.4 high-confidence node kinds should exist."""
        from entityspine.domain import NodeKind

        new_kinds = ["asset", "contract", "product", "brand", "regulator", "event"]
        actual = [e.value for e in NodeKind]

        for kind in new_kinds:
            assert kind in actual, f"NodeKind.{kind.upper()} not found"


class TestNodeRefNewTypes:
    """Test NodeRef factory methods for new types."""

    def test_noderef_asset(self):
        """NodeRef.asset() works correctly."""
        from entityspine.domain import NodeKind, NodeRef

        ref = NodeRef.asset("asset123")

        assert ref.kind == NodeKind.ASSET
        assert ref.id == "asset123"

    def test_noderef_contract(self):
        """NodeRef.contract() works correctly."""
        from entityspine.domain import NodeKind, NodeRef

        ref = NodeRef.contract("contract456")

        assert ref.kind == NodeKind.CONTRACT
        assert ref.id == "contract456"

    def test_noderef_product(self):
        """NodeRef.product() works correctly."""
        from entityspine.domain import NodeKind, NodeRef

        ref = NodeRef.product("product789")

        assert ref.kind == NodeKind.PRODUCT
        assert ref.id == "product789"

    def test_noderef_brand(self):
        """NodeRef.brand() works correctly."""
        from entityspine.domain import NodeKind, NodeRef

        ref = NodeRef.brand("brand001")

        assert ref.kind == NodeKind.BRAND
        assert ref.id == "brand001"

    def test_noderef_event(self):
        """NodeRef.event() works correctly."""
        from entityspine.domain import NodeKind, NodeRef

        ref = NodeRef.event("event002")

        assert ref.kind == NodeKind.EVENT
        assert ref.id == "event002"

    def test_noderef_regulator(self):
        """NodeRef.regulator() works correctly."""
        from entityspine.domain import NodeKind, NodeRef

        ref = NodeRef.regulator("regulator003")

        assert ref.kind == NodeKind.REGULATOR
        assert ref.id == "regulator003"


class TestRelationshipTypeExpansion:
    """Test RelationshipType enum expansion for v2.2.4."""

    def test_asset_relationships_exist(self):
        """Asset relationship types should exist."""
        from entityspine.domain import RelationshipType

        asset_rels = ["owns_asset", "operates_asset", "leases_asset"]
        actual = [e.value for e in RelationshipType]

        for rel in asset_rels:
            assert rel in actual, f"RelationshipType.{rel.upper()} not found"

    def test_contract_relationships_exist(self):
        """Contract relationship types should exist."""
        from entityspine.domain import RelationshipType

        contract_rels = ["party_to", "counterparty_to", "governs"]
        actual = [e.value for e in RelationshipType]

        for rel in contract_rels:
            assert rel in actual, f"RelationshipType.{rel.upper()} not found"

    def test_product_relationships_exist(self):
        """Product relationship types should exist."""
        from entityspine.domain import RelationshipType

        product_rels = ["manufactures", "sells", "distributes", "licenses_product", "develops"]
        actual = [e.value for e in RelationshipType]

        for rel in product_rels:
            assert rel in actual, f"RelationshipType.{rel.upper()} not found"

    def test_brand_relationships_exist(self):
        """Brand relationship types should exist."""
        from entityspine.domain import RelationshipType

        brand_rels = ["owns_brand", "licenses_brand", "brand_of"]
        actual = [e.value for e in RelationshipType]

        for rel in brand_rels:
            assert rel in actual, f"RelationshipType.{rel.upper()} not found"

    def test_event_relationships_exist(self):
        """Event relationship types should exist."""
        from entityspine.domain import RelationshipType

        event_rels = ["subject_of", "involved_in", "triggered_by", "resulted_in", "announced_by"]
        actual = [e.value for e in RelationshipType]

        for rel in event_rels:
            assert rel in actual, f"RelationshipType.{rel.upper()} not found"


class TestSqliteV224Tables:
    """Test SQLite store creates v2.2.4 tables."""

    def test_sqlite_creates_assets_table(self):
        """SQLite store should create assets table."""
        from entityspine.stores import SqliteStore

        store = SqliteStore(":memory:")
        store.initialize()

        with store._get_connection() as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='assets'"
            )
            result = cursor.fetchone()

        assert result is not None, "assets table not found"

    def test_sqlite_creates_contracts_table(self):
        """SQLite store should create contracts table."""
        from entityspine.stores import SqliteStore

        store = SqliteStore(":memory:")
        store.initialize()

        with store._get_connection() as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='contracts'"
            )
            result = cursor.fetchone()

        assert result is not None, "contracts table not found"

    def test_sqlite_creates_products_table(self):
        """SQLite store should create products table."""
        from entityspine.stores import SqliteStore

        store = SqliteStore(":memory:")
        store.initialize()

        with store._get_connection() as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='products'"
            )
            result = cursor.fetchone()

        assert result is not None, "products table not found"

    def test_sqlite_creates_brands_table(self):
        """SQLite store should create brands table."""
        from entityspine.stores import SqliteStore

        store = SqliteStore(":memory:")
        store.initialize()

        with store._get_connection() as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='brands'"
            )
            result = cursor.fetchone()

        assert result is not None, "brands table not found"

    def test_sqlite_creates_kg_events_table(self):
        """SQLite store should create kg_events table."""
        from entityspine.stores import SqliteStore

        store = SqliteStore(":memory:")
        store.initialize()

        with store._get_connection() as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='kg_events'"
            )
            result = cursor.fetchone()

        assert result is not None, "kg_events table not found"

    def test_sqlite_assets_indexes(self):
        """Assets table should have proper indexes."""
        from entityspine.stores import SqliteStore

        store = SqliteStore(":memory:")
        store.initialize()

        with store._get_connection() as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE '%assets%'"
            )
            indexes = [row[0] for row in cursor.fetchall()]

        assert len(indexes) >= 4, f"Expected at least 4 asset indexes, got {len(indexes)}"
