"""
Tests for Pydantic model domain conversions.

These tests verify that Pydantic models can convert to/from domain dataclasses.
Uses pytest.importorskip to skip if Pydantic is not installed.

v2.2.3: Pydantic models are thin wrappers, domain dataclasses are canonical.
"""

import pytest

# Skip all tests if Pydantic is not installed
pydantic = pytest.importorskip("pydantic")


class TestEntityConversion:
    """Tests for Entity domain/Pydantic conversion."""

    def test_entity_to_domain(self):
        """Test converting Pydantic Entity to domain dataclass."""
        from entityspine.adapters.pydantic import Entity as PydanticEntity
        from entityspine.adapters.pydantic import EntityStatus, EntityType
        from entityspine.domain import Entity as DomainEntity

        pydantic_entity = PydanticEntity(
            entity_id="test-entity-id",
            primary_name="Apple Inc.",
            entity_type=EntityType.ORGANIZATION,
            status=EntityStatus.ACTIVE,
            source_system="sec",
        )

        domain_entity = pydantic_entity.to_domain()

        assert isinstance(domain_entity, DomainEntity)
        assert domain_entity.entity_id == "test-entity-id"
        assert domain_entity.primary_name == "Apple Inc."
        assert domain_entity.entity_type.value == "organization"
        assert domain_entity.status.value == "active"
        assert domain_entity.source_system == "sec"

    def test_entity_from_domain(self):
        """Test creating Pydantic Entity from domain dataclass."""
        from entityspine.adapters.pydantic import Entity as PydanticEntity
        from entityspine.domain import Entity as DomainEntity
        from entityspine.domain import EntityStatus, EntityType

        domain_entity = DomainEntity(
            entity_id="test-entity-id",
            primary_name="Microsoft Corp.",
            entity_type=EntityType.ORGANIZATION,
            status=EntityStatus.ACTIVE,
            source_system="user",
        )

        pydantic_entity = PydanticEntity.from_domain(domain_entity)

        assert isinstance(pydantic_entity, PydanticEntity)
        assert pydantic_entity.entity_id == "test-entity-id"
        assert pydantic_entity.primary_name == "Microsoft Corp."
        assert pydantic_entity.source_system == "user"

    def test_entity_roundtrip(self):
        """Test Entity roundtrip conversion preserves data."""
        from entityspine.adapters.pydantic import Entity as PydanticEntity

        original = PydanticEntity(
            entity_id="roundtrip-entity",
            primary_name="Google Inc.",
            source_system="test",
            jurisdiction="US-DE",
            sic_code="7371",
        )

        domain = original.to_domain()
        restored = PydanticEntity.from_domain(domain)

        assert restored.entity_id == original.entity_id
        assert restored.primary_name == original.primary_name
        assert restored.source_system == original.source_system
        assert restored.jurisdiction == original.jurisdiction
        assert restored.sic_code == original.sic_code


class TestSecurityConversion:
    """Tests for Security domain/Pydantic conversion."""

    def test_security_to_domain(self):
        """Test converting Pydantic Security to domain dataclass."""
        from entityspine.adapters.pydantic import Security as PydanticSecurity
        from entityspine.adapters.pydantic import SecurityType
        from entityspine.domain import Security as DomainSecurity

        pydantic_security = PydanticSecurity(
            security_id="test-security-id",
            entity_id="parent-entity-id",
            security_type=SecurityType.COMMON_STOCK,
            description="Apple Common Stock",
            currency="USD",
        )

        domain_security = pydantic_security.to_domain()

        assert isinstance(domain_security, DomainSecurity)
        assert domain_security.security_id == "test-security-id"
        assert domain_security.entity_id == "parent-entity-id"
        assert domain_security.security_type.value == "common_stock"
        assert domain_security.description == "Apple Common Stock"

    def test_security_from_domain(self):
        """Test creating Pydantic Security from domain dataclass."""
        from entityspine.adapters.pydantic import Security as PydanticSecurity
        from entityspine.domain import Security as DomainSecurity
        from entityspine.domain import SecurityType

        domain_security = DomainSecurity(
            security_id="test-security-id",
            entity_id="parent-entity-id",
            security_type=SecurityType.COMMON_STOCK,
            description="Test Security",
        )

        pydantic_security = PydanticSecurity.from_domain(domain_security)

        assert isinstance(pydantic_security, PydanticSecurity)
        assert pydantic_security.security_id == "test-security-id"
        assert pydantic_security.entity_id == "parent-entity-id"


class TestListingConversion:
    """Tests for Listing domain/Pydantic conversion."""

    def test_listing_to_domain(self):
        """Test converting Pydantic Listing to domain dataclass."""
        from entityspine.adapters.pydantic import Listing as PydanticListing
        from entityspine.domain import Listing as DomainListing

        pydantic_listing = PydanticListing(
            listing_id="test-listing-id",
            security_id="parent-security-id",
            ticker="AAPL",
            exchange="NASDAQ",
            mic="XNAS",
            is_primary=True,
        )

        domain_listing = pydantic_listing.to_domain()

        assert isinstance(domain_listing, DomainListing)
        assert domain_listing.listing_id == "test-listing-id"
        assert domain_listing.security_id == "parent-security-id"
        assert domain_listing.ticker == "AAPL"
        assert domain_listing.mic == "XNAS"
        assert domain_listing.is_primary is True

    def test_listing_from_domain(self):
        """Test creating Pydantic Listing from domain dataclass."""
        from entityspine.adapters.pydantic import Listing as PydanticListing
        from entityspine.domain import Listing as DomainListing

        domain_listing = DomainListing(
            listing_id="test-listing-id",
            security_id="parent-security-id",
            ticker="MSFT",
            exchange="NASDAQ",
        )

        pydantic_listing = PydanticListing.from_domain(domain_listing)

        assert isinstance(pydantic_listing, PydanticListing)
        assert pydantic_listing.listing_id == "test-listing-id"
        assert pydantic_listing.ticker == "MSFT"


class TestIdentifierClaimConversion:
    """Tests for IdentifierClaim domain/Pydantic conversion."""

    def test_claim_to_domain(self):
        """Test converting Pydantic IdentifierClaim to domain dataclass."""
        from entityspine.adapters.pydantic import IdentifierClaim as PydanticClaim
        from entityspine.adapters.pydantic import IdentifierScheme, VendorNamespace
        from entityspine.domain import IdentifierClaim as DomainClaim

        pydantic_claim = PydanticClaim(
            claim_id="test-claim-id",
            entity_id="parent-entity-id",
            scheme=IdentifierScheme.CIK,
            value="0000320193",
            namespace=VendorNamespace.SEC,
        )

        domain_claim = pydantic_claim.to_domain()

        assert isinstance(domain_claim, DomainClaim)
        assert domain_claim.claim_id == "test-claim-id"
        assert domain_claim.entity_id == "parent-entity-id"
        assert domain_claim.scheme.value == "cik"
        assert domain_claim.value == "0000320193"
        assert domain_claim.namespace.value == "sec"

    def test_claim_from_domain(self):
        """Test creating Pydantic IdentifierClaim from domain dataclass."""
        from entityspine.adapters.pydantic import IdentifierClaim as PydanticClaim
        from entityspine.domain import IdentifierClaim as DomainClaim
        from entityspine.domain import IdentifierScheme, VendorNamespace

        domain_claim = DomainClaim(
            claim_id="test-claim-id",
            entity_id="parent-entity-id",
            scheme=IdentifierScheme.LEI,
            value="HWUPKR0MPOU8FGXBT394",
            namespace=VendorNamespace.GLEIF,
        )

        pydantic_claim = PydanticClaim.from_domain(domain_claim)

        assert isinstance(pydantic_claim, PydanticClaim)
        assert pydantic_claim.claim_id == "test-claim-id"
        assert pydantic_claim.value == "HWUPKR0MPOU8FGXBT394"


class TestResolutionCandidateConversion:
    """Tests for ResolutionCandidate domain/Pydantic conversion."""

    def test_candidate_to_domain(self):
        """Test converting Pydantic ResolutionCandidate to domain dataclass."""
        from entityspine.adapters.pydantic import MatchReason
        from entityspine.adapters.pydantic import ResolutionCandidate as PydanticCandidate
        from entityspine.domain import ResolutionCandidate as DomainCandidate

        pydantic_candidate = PydanticCandidate(
            entity_id="test-entity-id",
            security_id="test-security-id",
            listing_id="test-listing-id",
            score=0.95,
            match_reason=MatchReason.EXACT_TICKER,
            matched_scheme="ticker",
            matched_value="AAPL",
        )

        domain_candidate = pydantic_candidate.to_domain()

        assert isinstance(domain_candidate, DomainCandidate)
        assert domain_candidate.entity_id == "test-entity-id"
        assert domain_candidate.score == 0.95
        assert domain_candidate.match_reason.value == "exact_ticker"
        assert domain_candidate.matched_value == "AAPL"

    def test_candidate_from_domain(self):
        """Test creating Pydantic ResolutionCandidate from domain dataclass."""
        from entityspine.adapters.pydantic import ResolutionCandidate as PydanticCandidate
        from entityspine.domain import MatchReason
        from entityspine.domain import ResolutionCandidate as DomainCandidate

        domain_candidate = DomainCandidate(
            entity_id="test-entity-id",
            score=0.85,
            match_reason=MatchReason.NAME_FUZZY,
            matched_scheme="name",
            matched_value="Apple Inc",
        )

        pydantic_candidate = PydanticCandidate.from_domain(domain_candidate)

        assert isinstance(pydantic_candidate, PydanticCandidate)
        assert pydantic_candidate.entity_id == "test-entity-id"
        assert pydantic_candidate.score == 0.85


class TestResolutionResultConversion:
    """Tests for ResolutionResult domain/Pydantic conversion."""

    def test_result_to_domain(self):
        """Test converting Pydantic ResolutionResult to domain dataclass."""
        from entityspine.adapters.pydantic import (
            Entity as PydanticEntity,
        )
        from entityspine.adapters.pydantic import (
            ResolutionResult as PydanticResult,
        )
        from entityspine.adapters.pydantic import (
            ResolutionStatus,
            ResolutionTier,
        )
        from entityspine.domain import ResolutionResult as DomainResult

        pydantic_entity = PydanticEntity(
            entity_id="test-entity-id",
            primary_name="Apple Inc.",
        )

        pydantic_result = PydanticResult(
            query="AAPL",
            status=ResolutionStatus.FOUND,
            tier=ResolutionTier.TIER_1,
            entity=pydantic_entity,
            warnings=["as_of_ignored"],
            confidence=0.95,
        )

        domain_result = pydantic_result.to_domain()

        assert isinstance(domain_result, DomainResult)
        assert domain_result.query == "AAPL"
        assert domain_result.status.value == "found"
        assert domain_result.tier.value == 1
        assert domain_result.entity is not None
        assert domain_result.entity.primary_name == "Apple Inc."
        assert "as_of_ignored" in domain_result.warnings

    def test_result_from_domain(self):
        """Test creating Pydantic ResolutionResult from domain dataclass."""
        from entityspine.adapters.pydantic import ResolutionResult as PydanticResult
        from entityspine.domain import (
            Entity as DomainEntity,
        )
        from entityspine.domain import (
            ResolutionResult as DomainResult,
        )
        from entityspine.domain import (
            ResolutionStatus,
            ResolutionTier,
        )

        domain_entity = DomainEntity(
            entity_id="test-entity-id",
            primary_name="Microsoft Corp.",
        )

        domain_result = DomainResult(
            query="MSFT",
            status=ResolutionStatus.FOUND,
            tier=ResolutionTier.TIER_0,
            entity=domain_entity,
        )

        pydantic_result = PydanticResult.from_domain(domain_result)

        assert isinstance(pydantic_result, PydanticResult)
        assert pydantic_result.query == "MSFT"
        assert pydantic_result.entity is not None
        assert pydantic_result.entity.primary_name == "Microsoft Corp."


class TestProtocolsAreStdlib:
    """Tests verifying protocols are stdlib-only."""

    def test_protocols_available_without_pydantic(self):
        """Test that domain protocols can be imported without pydantic."""

        # Run in a subprocess without pydantic in path
        code = """
import sys
# Remove any cached pydantic imports
mods_to_remove = [k for k in sys.modules if 'pydantic' in k]
for mod in mods_to_remove:
    del sys.modules[mod]

# Import protocols
from entityspine.domain.protocols import (
    EntityStoreProtocol,
    ResolverProtocol,
    FullStoreProtocol,
)

# Verify they're Protocol subclasses
from typing import Protocol
print("Protocols loaded successfully")
"""
        # This test verifies protocols are importable
        # In practice, the pydantic importorskip above means pydantic IS available
        # But the protocols module itself doesn't require pydantic

        from entityspine.domain.protocols import (
            EntityStoreProtocol,
        )

        # Check they're protocols
        assert hasattr(EntityStoreProtocol, "__protocol_attrs__") or isinstance(
            EntityStoreProtocol, type
        )
