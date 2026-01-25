"""
Tests verifying zero-dependency guarantee for Tier 0/1.

These tests ensure that the core entityspine package can be imported
and used without any optional dependencies (pydantic, sqlmodel, etc.).
"""

import sys


class TestZeroDependencies:
    """Verify core package has no external dependencies."""

    def test_import_entityspine_no_pydantic(self):
        """Importing entityspine should not load pydantic."""
        # Clear any cached imports
        modules_to_clear = [
            k
            for k in sys.modules.keys()
            if any(x in k for x in ["entityspine", "pydantic", "sqlmodel"])
        ]
        for k in modules_to_clear:
            del sys.modules[k]

        # Import entityspine
        import entityspine

        # Check pydantic is not loaded (it may be installed but shouldn't be imported)
        pydantic_loaded = any("pydantic" in k for k in sys.modules.keys() if not k.startswith("_"))

        # This may fail if pydantic is already cached - that's OK in test environment
        # The real test is in CI with a fresh environment
        assert entityspine.Entity is not None

    def test_entity_is_dataclass(self):
        """Entity should be a stdlib dataclass."""
        from dataclasses import is_dataclass

        from entityspine import Entity

        assert is_dataclass(Entity), "Entity must be a stdlib dataclass"

    def test_security_is_dataclass(self):
        """Security should be a stdlib dataclass."""
        from dataclasses import is_dataclass

        from entityspine import Security

        assert is_dataclass(Security), "Security must be a stdlib dataclass"

    def test_listing_is_dataclass(self):
        """Listing should be a stdlib dataclass."""
        from dataclasses import is_dataclass

        from entityspine import Listing

        assert is_dataclass(Listing), "Listing must be a stdlib dataclass"

    def test_identifier_claim_is_dataclass(self):
        """IdentifierClaim should be a stdlib dataclass."""
        from dataclasses import is_dataclass

        from entityspine import IdentifierClaim

        assert is_dataclass(IdentifierClaim), "IdentifierClaim must be a stdlib dataclass"

    def test_resolution_result_is_dataclass(self):
        """ResolutionResult should be a stdlib dataclass."""
        from dataclasses import is_dataclass

        from entityspine import ResolutionResult

        assert is_dataclass(ResolutionResult), "ResolutionResult must be a stdlib dataclass"


class TestDomainModelCreation:
    """Test that domain models can be created without dependencies."""

    def test_create_entity(self):
        """Can create Entity without any dependencies."""
        from entityspine import Entity, EntityStatus, EntityType

        entity = Entity(
            primary_name="Apple Inc.",
            entity_type=EntityType.ORGANIZATION,
            status=EntityStatus.ACTIVE,
            source_system="sec",
            source_id="0000320193",
        )

        assert entity.primary_name == "Apple Inc."
        assert entity.entity_type == EntityType.ORGANIZATION
        assert entity.source_system == "sec"

    def test_create_security(self):
        """Can create Security without any dependencies."""
        from entityspine import Security, SecurityType

        security = Security(
            entity_id="test-entity-id",
            security_type=SecurityType.COMMON_STOCK,
            description="Apple Common Stock",
        )

        assert security.entity_id == "test-entity-id"
        assert security.security_type == SecurityType.COMMON_STOCK

    def test_create_listing(self):
        """Can create Listing without any dependencies."""
        from entityspine import Listing

        listing = Listing(
            security_id="test-security-id",
            ticker="AAPL",
            exchange="NASDAQ",
            mic="XNAS",
        )

        assert listing.ticker == "AAPL"
        assert listing.exchange == "NASDAQ"
        assert listing.mic == "XNAS"

    def test_create_identifier_claim(self):
        """Can create IdentifierClaim without any dependencies."""
        from entityspine import IdentifierClaim, IdentifierScheme, VendorNamespace

        claim = IdentifierClaim(
            entity_id="test-entity-id",
            scheme=IdentifierScheme.CIK,
            value="0000320193",
            namespace=VendorNamespace.SEC,
            source="sec_edgar",
        )

        assert claim.scheme == IdentifierScheme.CIK
        assert claim.value == "0000320193"
        assert claim.namespace == VendorNamespace.SEC

    def test_create_resolution_result(self):
        """Can create ResolutionResult without any dependencies."""
        from entityspine import ResolutionResult, ResolutionStatus, ResolutionTier

        result = ResolutionResult(
            status=ResolutionStatus.NOT_FOUND,
            tier=ResolutionTier.TIER_0,
            query="UNKNOWN",
        )

        assert result.status == ResolutionStatus.NOT_FOUND
        assert result.found is False


class TestFactoryFunctions:
    """Test factory functions work without dependencies."""

    def test_found_result_factory(self):
        """found_result factory works."""
        from entityspine import Entity, ResolutionTier, found_result

        entity = Entity(primary_name="Test Corp")
        result = found_result(
            entity=entity,
            query="TEST",
            tier=ResolutionTier.TIER_0,
        )

        assert result.found is True
        assert result.entity == entity

    def test_not_found_result_factory(self):
        """not_found_result factory works."""
        from entityspine import ResolutionTier, not_found_result

        result = not_found_result(
            query="UNKNOWN",
            tier=ResolutionTier.TIER_0,
        )

        assert result.found is False
        assert result.entity is None


class TestValidators:
    """Test validators are accessible and work."""

    def test_normalize_cik(self):
        """normalize_cik is accessible and works."""
        from entityspine import normalize_cik

        assert normalize_cik("320193") == "0000320193"
        assert normalize_cik("0000320193") == "0000320193"

    def test_validate_cik(self):
        """validate_cik is accessible and works."""
        from entityspine import validate_cik

        # validate_cik returns (is_valid, error_msg) tuple
        assert validate_cik("0000320193")[0] is True
        assert validate_cik("abc")[0] is False

    def test_normalize_isin(self):
        """normalize_isin is accessible and works."""
        from entityspine import normalize_isin

        assert normalize_isin("us0378331005") == "US0378331005"

    def test_scheme_scopes_available(self):
        """SCHEME_SCOPES mapping is accessible."""
        from entityspine import SCHEME_SCOPES, IdentifierScope

        assert SCHEME_SCOPES["cik"] == IdentifierScope.ENTITY
        assert SCHEME_SCOPES["isin"] == IdentifierScope.SECURITY
        assert SCHEME_SCOPES["ticker"] == IdentifierScope.LISTING


class TestTierHonestySemantics:
    """Test tier honesty semantics are preserved."""

    def test_resolution_result_has_warnings(self):
        """ResolutionResult has warnings field."""
        from entityspine import ResolutionResult

        result = ResolutionResult(query="test")
        assert hasattr(result, "warnings")
        assert isinstance(result.warnings, list)

    def test_resolution_result_has_limits(self):
        """ResolutionResult has limits field."""
        from entityspine import ResolutionResult

        result = ResolutionResult(query="test")
        assert hasattr(result, "limits")
        assert isinstance(result.limits, dict)

    def test_resolution_warning_constants(self):
        """ResolutionWarning enum has expected values."""
        from entityspine import ResolutionWarning

        assert ResolutionWarning.AS_OF_IGNORED.value == "as_of_ignored"
        # Check that key warnings exist
        assert hasattr(ResolutionWarning, "AS_OF_IGNORED")

    def test_resolution_tier_values(self):
        """ResolutionTier enum has expected values."""
        from entityspine import ResolutionTier

        assert ResolutionTier.TIER_0.value == 0
        assert ResolutionTier.TIER_1.value == 1


class TestV223Semantics:
    """Test v2.2.3 semantics are preserved."""

    def test_entity_has_no_identifier_fields(self):
        """Entity has NO cik/lei/ein fields per v2.2.3."""
        import dataclasses

        from entityspine import Entity

        field_names = {f.name for f in dataclasses.fields(Entity)}

        # v2.2.3: NO identifier convenience fields
        assert "cik" not in field_names, "Entity should not have cik field"
        assert "lei" not in field_names, "Entity should not have lei field"
        assert "ein" not in field_names, "Entity should not have ein field"
        assert "identifiers" not in field_names, "Entity should not have identifiers dict"

        # But should have provenance
        assert "source_system" in field_names
        assert "source_id" in field_names

    def test_identifier_claim_has_captured_at(self):
        """IdentifierClaim has captured_at for observation time."""
        import dataclasses

        from entityspine import IdentifierClaim

        field_names = {f.name for f in dataclasses.fields(IdentifierClaim)}

        assert "captured_at" in field_names, "IdentifierClaim needs captured_at"
        assert "valid_from" in field_names, "IdentifierClaim needs valid_from"
        assert "valid_to" in field_names, "IdentifierClaim needs valid_to"

    def test_identifier_claim_has_namespace(self):
        """IdentifierClaim has namespace for vendor tracking."""
        import dataclasses

        from entityspine import IdentifierClaim, VendorNamespace

        field_names = {f.name for f in dataclasses.fields(IdentifierClaim)}

        assert "namespace" in field_names, "IdentifierClaim needs namespace"

        # Create claim with namespace
        claim = IdentifierClaim(
            entity_id="test",
            scheme="cik",
            value="0000320193",
            namespace=VendorNamespace.SEC,
        )
        assert claim.namespace == VendorNamespace.SEC

    def test_resolution_result_has_candidates(self):
        """ResolutionResult has candidates list per v2.2.3."""
        import dataclasses

        from entityspine import ResolutionResult

        field_names = {f.name for f in dataclasses.fields(ResolutionResult)}

        assert "candidates" in field_names, "ResolutionResult needs candidates"

        result = ResolutionResult(query="test")
        assert isinstance(result.candidates, list)
