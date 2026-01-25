"""
Tests for the database-agnostic mappers module.

These mappers are used by all RDBMS providers (SQLite, PostgreSQL, MySQL, etc.)
to convert between domain dataclasses and row dictionaries.
"""

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

# =============================================================================
# Core Model Mappers (v2.2.4)
# =============================================================================


class TestEntityMappers:
    """Test Entity to/from row conversion (v2.2.4)."""

    def test_entity_to_row(self):
        """Test converting Entity dataclass to row dict."""
        from entityspine.domain import Entity, EntityStatus, EntityType
        from entityspine.stores.mappers import entity_to_row

        entity = Entity(
            entity_id="ent_001",
            primary_name="Acme Corporation",
            entity_type=EntityType.ORGANIZATION,
            status=EntityStatus.ACTIVE,
            jurisdiction="US-DE",
            sic_code="7370",
            incorporation_date=date(2020, 1, 15),
            source_system="sec-edgar",
            source_id="0001234567",
            aliases=("Acme Corp", "ACME"),
        )

        row = entity_to_row(entity)

        assert row["entity_id"] == "ent_001"
        assert row["primary_name"] == "Acme Corporation"
        assert row["entity_type"] == "organization"
        assert row["status"] == "active"
        assert row["jurisdiction"] == "US-DE"
        assert row["sic_code"] == "7370"
        assert row["incorporation_date"] == "2020-01-15"
        assert row["source_system"] == "sec-edgar"
        assert row["source_id"] == "0001234567"
        assert "Acme Corp" in row["aliases"]
        assert "created_at" in row
        assert "updated_at" in row

    def test_entity_to_row_minimal(self):
        """Test converting Entity with minimal fields."""
        from entityspine.domain import Entity, EntityStatus, EntityType
        from entityspine.stores.mappers import entity_to_row

        entity = Entity(
            entity_id="ent_002",
            primary_name="Simple Inc",
            entity_type=EntityType.ORGANIZATION,
            status=EntityStatus.ACTIVE,
        )

        row = entity_to_row(entity)

        assert row["entity_id"] == "ent_002"
        assert row["primary_name"] == "Simple Inc"
        assert row["jurisdiction"] is None
        assert row["sic_code"] is None
        assert row["incorporation_date"] is None

    def test_row_to_entity(self):
        """Test converting row dict to Entity dataclass."""
        import json

        from entityspine.domain import EntityStatus, EntityType
        from entityspine.stores.mappers import row_to_entity

        row = {
            "entity_id": "ent_003",
            "primary_name": "Test Company",
            "entity_type": "organization",
            "status": "active",
            "jurisdiction": "US-CA",
            "sic_code": "1234",
            "incorporation_date": "2021-06-01",
            "source_system": "manual",
            "source_id": "test_001",
            "redirect_to": None,
            "redirect_reason": None,
            "merged_at": None,
            "aliases": json.dumps(["TC", "TestCo"]),
        }

        entity = row_to_entity(row)

        assert entity.entity_id == "ent_003"
        assert entity.primary_name == "Test Company"
        assert entity.entity_type == EntityType.ORGANIZATION
        assert entity.status == EntityStatus.ACTIVE
        assert entity.jurisdiction == "US-CA"
        assert entity.sic_code == "1234"
        assert entity.incorporation_date == date(2021, 6, 1)
        assert entity.source_system == "manual"
        assert "TC" in entity.aliases
        assert "TestCo" in entity.aliases

    def test_entity_round_trip(self):
        """Entity should survive round-trip conversion."""
        from entityspine.domain import Entity, EntityStatus, EntityType
        from entityspine.stores.mappers import entity_to_row, row_to_entity

        original = Entity(
            entity_id="ent_rt",
            primary_name="Round Trip Inc",
            entity_type=EntityType.ORGANIZATION,
            status=EntityStatus.ACTIVE,
            jurisdiction="US-NY",
            sic_code="9999",
            incorporation_date=date(2023, 3, 15),
            source_system="test",
            source_id="rt_001",
            aliases=("RTI", "RoundTrip"),
        )

        row = entity_to_row(original)
        restored = row_to_entity(row)

        assert restored.entity_id == original.entity_id
        assert restored.primary_name == original.primary_name
        assert restored.entity_type == original.entity_type
        assert restored.status == original.status
        assert restored.jurisdiction == original.jurisdiction
        assert restored.sic_code == original.sic_code
        assert restored.incorporation_date == original.incorporation_date
        assert restored.source_system == original.source_system
        assert set(restored.aliases) == set(original.aliases)


class TestSecurityMappers:
    """Test Security to/from row conversion (v2.2.4)."""

    def test_security_to_row(self):
        """Test converting Security dataclass to row dict."""
        from entityspine.domain import Security, SecurityStatus, SecurityType
        from entityspine.stores.mappers import security_to_row

        security = Security(
            security_id="sec_001",
            entity_id="ent_001",
            security_type=SecurityType.COMMON_STOCK,
            description="Common Stock, par value $0.001",
            currency="USD",
            status=SecurityStatus.ACTIVE,
            source_system="sec-edgar",
            source_id="sec_source_001",
        )

        row = security_to_row(security)

        assert row["security_id"] == "sec_001"
        assert row["entity_id"] == "ent_001"
        assert row["security_type"] == "common_stock"
        assert row["description"] == "Common Stock, par value $0.001"
        assert row["currency"] == "USD"
        assert row["status"] == "active"
        assert row["source_system"] == "sec-edgar"
        assert "created_at" in row

    def test_security_to_row_minimal(self):
        """Test converting Security with minimal fields."""
        from entityspine.domain import Security, SecurityType
        from entityspine.stores.mappers import security_to_row

        security = Security(
            security_id="sec_002",
            entity_id="ent_002",
            security_type=SecurityType.COMMON_STOCK,
        )

        row = security_to_row(security)

        assert row["security_id"] == "sec_002"
        assert row["entity_id"] == "ent_002"
        assert row["description"] is None
        assert row["currency"] is None

    def test_row_to_security(self):
        """Test converting row dict to Security dataclass."""
        from entityspine.domain import SecurityStatus, SecurityType
        from entityspine.stores.mappers import row_to_security

        row = {
            "security_id": "sec_003",
            "entity_id": "ent_003",
            "security_type": "preferred_stock",
            "description": "Series A Preferred",
            "currency": "USD",
            "status": "active",
            "source_system": "manual",
            "source_id": None,
        }

        security = row_to_security(row)

        assert security.security_id == "sec_003"
        assert security.entity_id == "ent_003"
        assert security.security_type == SecurityType.PREFERRED_STOCK
        assert security.description == "Series A Preferred"
        assert security.currency == "USD"
        assert security.status == SecurityStatus.ACTIVE

    def test_security_round_trip(self):
        """Security should survive round-trip conversion."""
        from entityspine.domain import Security, SecurityStatus, SecurityType
        from entityspine.stores.mappers import row_to_security, security_to_row

        original = Security(
            security_id="sec_rt",
            entity_id="ent_rt",
            security_type=SecurityType.BOND,
            description="5% Senior Notes due 2030",
            currency="USD",
            status=SecurityStatus.ACTIVE,
            source_system="test",
            source_id="sec_rt_001",
        )

        row = security_to_row(original)
        restored = row_to_security(row)

        assert restored.security_id == original.security_id
        assert restored.entity_id == original.entity_id
        assert restored.security_type == original.security_type
        assert restored.description == original.description
        assert restored.currency == original.currency
        assert restored.status == original.status


class TestListingMappers:
    """Test Listing to/from row conversion (v2.2.4)."""

    def test_listing_to_row(self):
        """Test converting Listing dataclass to row dict."""
        from entityspine.domain import Listing, ListingStatus
        from entityspine.stores.mappers import listing_to_row

        listing = Listing(
            listing_id="lst_001",
            security_id="sec_001",
            ticker="AAPL",
            exchange="NASDAQ",
            mic="XNAS",
            start_date=date(1980, 12, 12),
            is_primary=True,
            currency="USD",
            status=ListingStatus.ACTIVE,
            source_system="exchange-feed",
            source_id="lst_source_001",
        )

        row = listing_to_row(listing)

        assert row["listing_id"] == "lst_001"
        assert row["security_id"] == "sec_001"
        assert row["ticker"] == "AAPL"
        assert row["exchange"] == "NASDAQ"
        assert row["mic"] == "XNAS"
        assert row["start_date"] == "1980-12-12"
        assert row["is_primary"] == 1
        assert row["currency"] == "USD"
        assert row["status"] == "active"
        assert "created_at" in row

    def test_listing_to_row_minimal(self):
        """Test converting Listing with minimal fields."""
        from entityspine.domain import Listing
        from entityspine.stores.mappers import listing_to_row

        listing = Listing(
            listing_id="lst_002",
            security_id="sec_002",
            ticker="TEST",
            exchange="NYSE",
        )

        row = listing_to_row(listing)

        assert row["listing_id"] == "lst_002"
        assert row["ticker"] == "TEST"
        assert row["end_date"] is None
        assert row["mic"] is None

    def test_row_to_listing(self):
        """Test converting row dict to Listing dataclass."""
        from entityspine.domain import ListingStatus
        from entityspine.stores.mappers import row_to_listing

        row = {
            "listing_id": "lst_003",
            "security_id": "sec_003",
            "ticker": "MSFT",
            "exchange": "NASDAQ",
            "mic": "XNAS",
            "start_date": "1986-03-13",
            "end_date": None,
            "is_primary": 1,
            "currency": "USD",
            "status": "active",
            "source_system": "manual",
            "source_id": None,
        }

        listing = row_to_listing(row)

        assert listing.listing_id == "lst_003"
        assert listing.security_id == "sec_003"
        assert listing.ticker == "MSFT"
        assert listing.exchange == "NASDAQ"
        assert listing.mic == "XNAS"
        assert listing.start_date == date(1986, 3, 13)
        assert listing.is_primary is True
        assert listing.currency == "USD"
        assert listing.status == ListingStatus.ACTIVE

    def test_listing_round_trip(self):
        """Listing should survive round-trip conversion."""
        from entityspine.domain import Listing, ListingStatus
        from entityspine.stores.mappers import listing_to_row, row_to_listing

        original = Listing(
            listing_id="lst_rt",
            security_id="sec_rt",
            ticker="GOOG",
            exchange="NASDAQ",
            mic="XNAS",
            start_date=date(2004, 8, 19),
            is_primary=True,
            currency="USD",
            status=ListingStatus.ACTIVE,
            source_system="test",
            source_id="lst_rt_001",
        )

        row = listing_to_row(original)
        restored = row_to_listing(row)

        assert restored.listing_id == original.listing_id
        assert restored.security_id == original.security_id
        assert restored.ticker == original.ticker
        assert restored.exchange == original.exchange
        assert restored.mic == original.mic
        assert restored.start_date == original.start_date
        assert restored.is_primary == original.is_primary
        assert restored.currency == original.currency
        assert restored.status == original.status


class TestIdentifierClaimMappers:
    """Test IdentifierClaim to/from row conversion (v2.2.4)."""

    def test_claim_to_row(self):
        """Test converting IdentifierClaim dataclass to row dict."""
        from entityspine.domain import (
            ClaimStatus,
            IdentifierClaim,
            IdentifierScheme,
            VendorNamespace,
        )
        from entityspine.stores.mappers import claim_to_row

        claim = IdentifierClaim(
            claim_id="clm_001",
            entity_id="ent_001",
            scheme=IdentifierScheme.CIK,
            value="0001234567",
            namespace=VendorNamespace.SEC,
            source_ref="10-K filing",
            captured_at=datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC),
            valid_from=date(2020, 1, 1),
            source="sec-edgar",
            confidence=1.0,
            status=ClaimStatus.ACTIVE,
        )

        row = claim_to_row(claim)

        assert row["claim_id"] == "clm_001"
        assert row["entity_id"] == "ent_001"
        assert row["security_id"] is None
        assert row["listing_id"] is None
        assert row["scheme"] == "cik"
        assert row["value"] == "0001234567"
        assert row["namespace"] == "sec"
        assert row["source_ref"] == "10-K filing"
        assert row["confidence"] == 1.0
        assert row["status"] == "active"
        assert "created_at" in row

    def test_claim_to_row_for_security(self):
        """Test IdentifierClaim attached to a security."""
        from entityspine.domain import (
            ClaimStatus,
            IdentifierClaim,
            IdentifierScheme,
            VendorNamespace,
        )
        from entityspine.stores.mappers import claim_to_row

        claim = IdentifierClaim(
            claim_id="clm_002",
            security_id="sec_001",
            scheme=IdentifierScheme.CUSIP,
            value="037833100",
            namespace=VendorNamespace.REUTERS,
            source="market-data",
            confidence=0.95,
            status=ClaimStatus.ACTIVE,
        )

        row = claim_to_row(claim)

        assert row["claim_id"] == "clm_002"
        assert row["entity_id"] is None
        assert row["security_id"] == "sec_001"
        assert row["scheme"] == "cusip"
        assert row["value"] == "037833100"
        assert row["namespace"] == "reuters"

    def test_row_to_claim(self):
        """Test converting row dict to IdentifierClaim dataclass."""
        from entityspine.domain import ClaimStatus, IdentifierScheme, VendorNamespace
        from entityspine.stores.mappers import row_to_claim

        row = {
            "claim_id": "clm_003",
            "entity_id": "ent_003",
            "security_id": None,
            "listing_id": None,
            "scheme": "lei",
            "value": "5493006MHFPIRP9REF08",
            "namespace": "gleif",
            "source_ref": "GLEIF API",
            "captured_at": "2024-02-01T10:30:00+00:00",
            "valid_from": "2020-01-01",
            "valid_to": None,
            "source": "gleif",
            "confidence": 1.0,
            "status": "active",
            "notes": None,
        }

        claim = row_to_claim(row)

        assert claim.claim_id == "clm_003"
        assert claim.entity_id == "ent_003"
        assert claim.scheme == IdentifierScheme.LEI
        assert claim.value == "5493006MHFPIRP9REF08"
        assert claim.namespace == VendorNamespace.GLEIF
        assert claim.source == "gleif"
        assert claim.confidence == 1.0
        assert claim.status == ClaimStatus.ACTIVE

    def test_claim_round_trip(self):
        """IdentifierClaim should survive round-trip conversion."""
        from entityspine.domain import (
            ClaimStatus,
            IdentifierClaim,
            IdentifierScheme,
            VendorNamespace,
        )
        from entityspine.stores.mappers import claim_to_row, row_to_claim

        # Use CIK scheme which is valid for entity_id
        original = IdentifierClaim(
            claim_id="clm_rt",
            entity_id="ent_rt",
            scheme=IdentifierScheme.CIK,
            value="0001234567",
            namespace=VendorNamespace.SEC,
            source="test",
            confidence=0.99,
            status=ClaimStatus.ACTIVE,
            notes="Test claim",
        )

        row = claim_to_row(original)
        restored = row_to_claim(row)

        assert restored.claim_id == original.claim_id
        assert restored.entity_id == original.entity_id
        assert restored.scheme == original.scheme
        assert restored.value == original.value
        assert restored.namespace == original.namespace
        assert restored.source == original.source
        assert restored.confidence == original.confidence
        assert restored.status == original.status
        assert restored.notes == original.notes

    def test_legacy_aliases(self):
        """Test that legacy identifier_to_row/row_to_identifier aliases work."""
        from entityspine.stores.mappers import (
            claim_to_row,
            identifier_to_row,
            row_to_claim,
            row_to_identifier,
        )

        # Verify the aliases point to the same functions
        assert identifier_to_row is claim_to_row
        assert row_to_identifier is row_to_claim


class TestCaseMappers:
    """Test Case to/from row conversion (v2.2.4)."""

    def test_case_to_row(self):
        """Test converting Case dataclass to row dict."""
        from entityspine.domain import Case, CaseStatus, CaseType
        from entityspine.stores.mappers import case_to_row

        case = Case(
            case_id="case_001",
            case_type=CaseType.INVESTIGATION,
            title="SEC vs Acme Corp",
            case_number="SEC-2024-001",
            status=CaseStatus.OPEN,
            authority_entity_id="ent_sec",
            target_entity_id="ent_acme",
            opened_date=date(2024, 1, 15),
            description="Investigation into accounting irregularities",
            source_system="sec-enforcement",
        )

        row = case_to_row(case)

        assert row["case_id"] == "case_001"
        assert row["case_type"] == "investigation"
        assert row["title"] == "SEC vs Acme Corp"
        assert row["case_number"] == "SEC-2024-001"
        assert row["status"] == "open"
        assert row["authority_entity_id"] == "ent_sec"
        assert row["target_entity_id"] == "ent_acme"
        assert row["opened_date"] == "2024-01-15"
        assert row["description"] == "Investigation into accounting irregularities"
        assert "created_at" in row

    def test_row_to_case(self):
        """Test converting row dict to Case dataclass."""
        from entityspine.domain import CaseStatus, CaseType
        from entityspine.stores.mappers import row_to_case

        row = {
            "case_id": "case_002",
            "case_type": "lawsuit",
            "case_number": "DOCKET-2024-ABC",
            "title": "Class Action vs BigCorp",
            "status": "closed",
            "authority_entity_id": "court_001",
            "target_entity_id": "bigcorp_ent",
            "opened_date": "2023-06-01",
            "closed_date": "2024-03-15",
            "description": "Securities fraud class action",
            "source_system": "pacer",
            "source_ref": "PACER-001",
            "filing_id": None,
            "captured_at": "2024-01-15T12:00:00+00:00",
        }

        case = row_to_case(row)

        assert case.case_id == "case_002"
        assert case.case_type == CaseType.LAWSUIT
        assert case.case_number == "DOCKET-2024-ABC"
        assert case.title == "Class Action vs BigCorp"
        assert case.status == CaseStatus.CLOSED
        assert case.authority_entity_id == "court_001"
        assert case.target_entity_id == "bigcorp_ent"
        assert case.opened_date == date(2023, 6, 1)
        assert case.closed_date == date(2024, 3, 15)
        assert case.description == "Securities fraud class action"

    def test_case_round_trip(self):
        """Case should survive round-trip conversion."""
        from entityspine.domain import Case, CaseStatus, CaseType
        from entityspine.stores.mappers import case_to_row, row_to_case

        original = Case(
            case_id="case_rt",
            case_type=CaseType.BANKRUPTCY,
            title="Chapter 11 Filing",
            case_number="BK-2024-999",
            status=CaseStatus.PENDING,
            authority_entity_id="court_bk",
            target_entity_id="debtor_ent",
            opened_date=date(2024, 5, 1),
            description="Voluntary Chapter 11 filing",
            source_system="test",
        )

        row = case_to_row(original)
        restored = row_to_case(row)

        assert restored.case_id == original.case_id
        assert restored.case_type == original.case_type
        assert restored.title == original.title
        assert restored.case_number == original.case_number
        assert restored.status == original.status
        assert restored.authority_entity_id == original.authority_entity_id
        assert restored.target_entity_id == original.target_entity_id
        assert restored.opened_date == original.opened_date


class TestClusterMappers:
    """Test EntityCluster to/from row conversion (v2.2.4)."""

    def test_cluster_to_row(self):
        """Test converting EntityCluster dataclass to row dict."""
        from entityspine.domain import EntityCluster
        from entityspine.stores.mappers import cluster_to_row

        cluster = EntityCluster(
            cluster_id="clus_001",
            reason="Similar names: 'Apple Inc' and 'APPLE INC.'",
        )

        row = cluster_to_row(cluster)

        assert row["cluster_id"] == "clus_001"
        assert row["reason"] == "Similar names: 'Apple Inc' and 'APPLE INC.'"
        assert "created_at" in row
        assert "updated_at" in row

    def test_row_to_cluster(self):
        """Test converting row dict to EntityCluster dataclass."""
        from entityspine.stores.mappers import row_to_cluster

        row = {
            "cluster_id": "clus_002",
            "reason": "Shared CIK identifier",
            "created_at": "2024-01-15T12:00:00+00:00",
            "updated_at": "2024-01-15T12:00:00+00:00",
        }

        cluster = row_to_cluster(row)

        assert cluster.cluster_id == "clus_002"
        assert cluster.reason == "Shared CIK identifier"

    def test_cluster_round_trip(self):
        """EntityCluster should survive round-trip conversion."""
        from entityspine.domain import EntityCluster
        from entityspine.stores.mappers import cluster_to_row, row_to_cluster

        original = EntityCluster(
            cluster_id="clus_rt",
            reason="Fuzzy name match: 0.95 similarity",
        )

        row = cluster_to_row(original)
        restored = row_to_cluster(row)

        assert restored.cluster_id == original.cluster_id
        assert restored.reason == original.reason


class TestClusterMemberMappers:
    """Test EntityClusterMember to/from row conversion (v2.2.4)."""

    def test_cluster_member_to_row(self):
        """Test converting EntityClusterMember dataclass to row dict."""
        from entityspine.domain import ClusterRole, EntityClusterMember
        from entityspine.stores.mappers import cluster_member_to_row

        member = EntityClusterMember(
            cluster_id="clus_001",
            entity_id="ent_001",
            role=ClusterRole.CANONICAL,
            confidence=1.0,
        )

        row = cluster_member_to_row(member)

        assert row["cluster_id"] == "clus_001"
        assert row["entity_id"] == "ent_001"
        assert row["role"] == "canonical"
        assert row["confidence"] == 1.0
        assert "created_at" in row

    def test_row_to_cluster_member(self):
        """Test converting row dict to EntityClusterMember dataclass."""
        from entityspine.domain import ClusterRole
        from entityspine.stores.mappers import row_to_cluster_member

        row = {
            "cluster_id": "clus_002",
            "entity_id": "ent_002",
            "role": "provisional",
            "confidence": 0.85,
            "created_at": "2024-01-15T12:00:00+00:00",
            "updated_at": "2024-01-15T12:00:00+00:00",
        }

        member = row_to_cluster_member(row)

        assert member.cluster_id == "clus_002"
        assert member.entity_id == "ent_002"
        assert member.role == ClusterRole.PROVISIONAL
        assert member.confidence == 0.85

    def test_cluster_member_round_trip(self):
        """EntityClusterMember should survive round-trip conversion."""
        from entityspine.domain import ClusterRole, EntityClusterMember
        from entityspine.stores.mappers import cluster_member_to_row, row_to_cluster_member

        original = EntityClusterMember(
            cluster_id="clus_rt",
            entity_id="ent_rt",
            role=ClusterRole.MEMBER,
            confidence=0.92,
        )

        row = cluster_member_to_row(original)
        restored = row_to_cluster_member(row)

        assert restored.cluster_id == original.cluster_id
        assert restored.entity_id == original.entity_id
        assert restored.role == original.role
        assert restored.confidence == original.confidence


# =============================================================================
# Knowledge Graph Node Mappers
# =============================================================================


class TestAssetMappers:
    """Test Asset to/from row conversion."""

    def test_asset_to_row(self):
        """Test converting Asset dataclass to row dict."""
        from entityspine.domain import Asset, AssetStatus, AssetType
        from entityspine.stores.mappers import asset_to_row

        asset = Asset(
            asset_id="ast_001",
            asset_type=AssetType.PROPERTY,
            name="HQ Building",
            owner_entity_id="ent_001",
            geo_id="geo_us",
            address_id="addr_001",
            status=AssetStatus.ACTIVE,
        )

        row = asset_to_row(asset)

        assert row["asset_id"] == "ast_001"
        assert row["asset_type"] == "property"
        assert row["name"] == "HQ Building"
        assert row["owner_entity_id"] == "ent_001"
        assert row["status"] == "active"
        assert "created_at" in row
        assert "updated_at" in row

    def test_row_to_asset(self):
        """Test converting row dict to Asset dataclass."""
        from entityspine.domain import AssetStatus, AssetType
        from entityspine.stores.mappers import row_to_asset

        row = {
            "asset_id": "ast_002",
            "asset_type": "equipment",
            "name": "Server Rack",
            "owner_entity_id": "ent_002",
            "geo_id": None,
            "address_id": None,
            "status": "active",
        }

        asset = row_to_asset(row)

        assert asset.asset_id == "ast_002"
        assert asset.asset_type == AssetType.EQUIPMENT
        assert asset.name == "Server Rack"
        assert asset.owner_entity_id == "ent_002"
        assert asset.status == AssetStatus.ACTIVE


class TestContractMappers:
    """Test Contract to/from row conversion."""

    def test_contract_to_row(self):
        """Test converting Contract dataclass to row dict."""
        from entityspine.domain import Contract, ContractStatus, ContractType
        from entityspine.stores.mappers import contract_to_row

        contract = Contract(
            contract_id="con_001",
            contract_type=ContractType.SUPPLY_AGREEMENT,
            title="Supply Agreement",
            effective_date=date(2024, 1, 1),
            termination_date=date(2025, 12, 31),
            value_usd=Decimal("1000000.00"),
            status=ContractStatus.ACTIVE,
        )

        row = contract_to_row(contract)

        assert row["contract_id"] == "con_001"
        assert row["contract_type"] == "supply"
        assert row["title"] == "Supply Agreement"
        assert row["effective_date"] == "2024-01-01"
        assert row["value_usd"] == 1000000.00
        assert row["status"] == "active"

    def test_row_to_contract(self):
        """Test converting row dict to Contract dataclass."""
        from entityspine.domain import ContractStatus, ContractType
        from entityspine.stores.mappers import row_to_contract

        row = {
            "contract_id": "con_002",
            "contract_type": "license",
            "title": "Software License",
            "effective_date": "2024-06-01",
            "termination_date": None,
            "value_usd": 50000.0,
            "status": "active",
        }

        contract = row_to_contract(row)

        assert contract.contract_id == "con_002"
        assert contract.contract_type == ContractType.LICENSE
        assert contract.title == "Software License"
        assert contract.effective_date == date(2024, 6, 1)
        assert contract.value_usd == Decimal("50000.0")
        assert contract.status == ContractStatus.ACTIVE


class TestProductMappers:
    """Test Product to/from row conversion."""

    def test_product_to_row(self):
        """Test converting Product dataclass to row dict."""
        from entityspine.domain import Product, ProductStatus, ProductType
        from entityspine.stores.mappers import product_to_row

        product = Product(
            product_id="prod_001",
            product_type=ProductType.SOFTWARE,
            name="EntitySpine Pro",
            owner_entity_id="ent_001",
            status=ProductStatus.ACTIVE,
        )

        row = product_to_row(product)

        assert row["product_id"] == "prod_001"
        assert row["product_type"] == "software"
        assert row["name"] == "EntitySpine Pro"
        assert row["owner_entity_id"] == "ent_001"
        assert row["status"] == "active"

    def test_row_to_product(self):
        """Test converting row dict to Product dataclass."""
        from entityspine.domain import ProductStatus, ProductType
        from entityspine.stores.mappers import row_to_product

        row = {
            "product_id": "prod_002",
            "product_type": "service",
            "name": "Cloud Hosting",
            "owner_entity_id": "ent_002",
            "status": "active",
        }

        product = row_to_product(row)

        assert product.product_id == "prod_002"
        assert product.product_type == ProductType.SERVICE
        assert product.name == "Cloud Hosting"
        assert product.status == ProductStatus.ACTIVE


class TestBrandMappers:
    """Test Brand to/from row conversion."""

    def test_brand_to_row(self):
        """Test converting Brand dataclass to row dict."""
        from entityspine.domain import Brand
        from entityspine.stores.mappers import brand_to_row

        brand = Brand(
            brand_id="brand_001",
            name="TechCorp",
            owner_entity_id="ent_001",
        )

        row = brand_to_row(brand)

        assert row["brand_id"] == "brand_001"
        assert row["name"] == "TechCorp"
        assert row["owner_entity_id"] == "ent_001"

    def test_row_to_brand(self):
        """Test converting row dict to Brand dataclass."""
        from entityspine.stores.mappers import row_to_brand

        row = {
            "brand_id": "brand_002",
            "name": "AcmeCo",
            "owner_entity_id": "ent_002",
        }

        brand = row_to_brand(row)

        assert brand.brand_id == "brand_002"
        assert brand.name == "AcmeCo"
        assert brand.owner_entity_id == "ent_002"


class TestEventMappers:
    """Test Event to/from row conversion."""

    def test_event_to_row(self):
        """Test converting Event dataclass to row dict."""
        from entityspine.domain import Event, EventStatus, EventType
        from entityspine.stores.mappers import event_to_row

        event = Event(
            event_id="evt_001",
            event_type=EventType.MERGER_ACQUISITION,
            title="TechCorp Acquires StartupXYZ",
            occurred_on=date(2024, 3, 15),
            announced_on=date(2024, 3, 14),
            status=EventStatus.COMPLETED,
            payload={"deal_value": 100000000},
            evidence_filing_id="filing_001",
            confidence=0.95,
        )

        row = event_to_row(event)

        assert row["event_id"] == "evt_001"
        assert row["event_type"] == "m&a"
        assert row["title"] == "TechCorp Acquires StartupXYZ"
        assert row["occurred_on"] == "2024-03-15"
        assert row["status"] == "completed"
        assert '"deal_value": 100000000' in row["payload"]
        assert row["confidence"] == 0.95

    def test_row_to_event(self):
        """Test converting row dict to Event dataclass."""
        from entityspine.domain import EventStatus, EventType
        from entityspine.stores.mappers import row_to_event

        row = {
            "event_id": "evt_002",
            "event_type": "m&a",
            "title": "Merger Announced",
            "occurred_on": "2024-04-01",
            "announced_on": "2024-03-28",
            "status": "announced",
            "payload": '{"parties": 2}',
            "evidence_filing_id": "filing_002",
            "evidence_section_id": None,
            "evidence_snippet": None,
            "confidence": 0.85,
        }

        event = row_to_event(row)

        assert event.event_id == "evt_002"
        assert event.event_type == EventType.MERGER_ACQUISITION
        assert event.title == "Merger Announced"
        assert event.occurred_on == date(2024, 4, 1)
        assert event.status == EventStatus.ANNOUNCED
        assert event.payload == {"parties": 2}
        assert event.confidence == 0.85


class TestMapperRoundTrip:
    """Test that to_row -> from_row preserves data (round-trip)."""

    def test_asset_round_trip(self):
        """Asset should survive round-trip conversion."""
        from entityspine.domain import Asset, AssetStatus, AssetType
        from entityspine.stores.mappers import asset_to_row, row_to_asset

        original = Asset(
            asset_id="ast_rt",
            asset_type=AssetType.EQUIPMENT,
            name="Test Asset",
            owner_entity_id="ent_rt",
            status=AssetStatus.ACTIVE,
        )

        row = asset_to_row(original)
        restored = row_to_asset(row)

        assert restored.asset_id == original.asset_id
        assert restored.asset_type == original.asset_type
        assert restored.name == original.name
        assert restored.owner_entity_id == original.owner_entity_id
        assert restored.status == original.status

    def test_contract_round_trip(self):
        """Contract should survive round-trip conversion."""
        from entityspine.domain import Contract, ContractStatus, ContractType
        from entityspine.stores.mappers import contract_to_row, row_to_contract

        original = Contract(
            contract_id="con_rt",
            contract_type=ContractType.SERVICE_AGREEMENT,
            title="Test Contract",
            effective_date=date(2024, 1, 1),
            value_usd=Decimal("12345.67"),
            status=ContractStatus.ACTIVE,
        )

        row = contract_to_row(original)
        restored = row_to_contract(row)

        assert restored.contract_id == original.contract_id
        assert restored.contract_type == original.contract_type
        assert restored.title == original.title
        assert restored.effective_date == original.effective_date
        # Note: Decimal precision may vary slightly due to float conversion
        assert float(restored.value_usd) == pytest.approx(float(original.value_usd))
        assert restored.status == original.status

    def test_event_round_trip(self):
        """Event should survive round-trip conversion."""
        from entityspine.domain import Event, EventStatus, EventType
        from entityspine.stores.mappers import event_to_row, row_to_event

        original = Event(
            event_id="evt_rt",
            event_type=EventType.CAPITAL,
            title="Test IPO",
            occurred_on=date(2024, 6, 15),
            status=EventStatus.COMPLETED,
            payload={"price": 25.00},
            evidence_filing_id="filing_rt",
            confidence=0.99,
        )

        row = event_to_row(original)
        restored = row_to_event(row)

        assert restored.event_id == original.event_id
        assert restored.event_type == original.event_type
        assert restored.title == original.title
        assert restored.occurred_on == original.occurred_on
        assert restored.status == original.status
        assert restored.payload == original.payload
        assert restored.confidence == original.confidence
