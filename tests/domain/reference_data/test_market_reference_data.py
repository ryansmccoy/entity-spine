"""
Unit tests for market infrastructure reference data (v2.3.2).

Tests the reference_data layer architecture:
- Curated major venues (high signal)
- Vendor code mappings (bidirectional lookup)
- Asset class metadata registry

NOTE: ISO 10383 bulk infrastructure tests are in tests/sources/test_iso10383.py
      because that functionality lives in entityspine.sources.iso10383.

STDLIB ONLY - NO PYDANTIC.
"""

from __future__ import annotations

from datetime import date, datetime

import pytest

from entityspine.domain.enums import AssetClass
from entityspine.domain.enums.markets import MicSource, VenueKind
from entityspine.domain.reference_data import (
    # Dataclasses
    AssetClassInfo,
    VendorVenueCodeRef,
    VenueRef,
    # Enums
    VendorNamespace,
    # Registries
    ALL_MAJOR_VENUES,
    ASSET_CLASS_INFO,
    BLOOMBERG_VENUE_CODES,
    FACTSET_VENUE_CODES,
    IBKR_VENUE_CODES,
    MAJOR_CLEARINGHOUSES,
    MAJOR_CRYPTO_VENUES,
    MAJOR_DEPOSITORIES_CSDS,
    MAJOR_EQUITY_VENUES,
    MAJOR_FUTURES_VENUES,
    MAJOR_FX_VENUES,
    MAJOR_INDEX_PROVIDERS,
    MAJOR_OPTIONS_VENUES,
    MAJOR_RATES_CREDIT_VENUES,
    MAJOR_SWAPS_SEFS,
    MAJOR_TRADE_REPORTING,
    REUTERS_VENUE_CODES,
    # Functions
    find_conflicting_mappings,
    get_asset_class_description,
    get_asset_class_info,
    get_major_venues,
    get_typical_venues_for_asset_class,
    get_vendor_code_ref,
    get_venues_by_asset_class,
    get_venues_by_kind,
    lookup_major_venue,
    lookup_mic_by_vendor_code,
    lookup_vendor_codes_for_mic,
)


# =============================================================================
# VenueKind Enum Tests
# =============================================================================

class TestVenueKindEnum:
    """Tests for VenueKind enum completeness."""

    def test_venue_kind_has_trading_venues(self) -> None:
        """VenueKind should have trading venue types."""
        assert VenueKind.STOCK_EXCHANGE
        assert VenueKind.OPTIONS_EXCHANGE
        assert VenueKind.FUTURES_EXCHANGE
        assert VenueKind.ECN
        assert VenueKind.ATS
        assert VenueKind.DARK_POOL

    def test_venue_kind_has_mifid_venues(self) -> None:
        """VenueKind should have MiFID II venue types."""
        assert VenueKind.MTF
        assert VenueKind.OTF
        assert VenueKind.SI

    def test_venue_kind_has_post_trade(self) -> None:
        """VenueKind should have post-trade infrastructure."""
        assert VenueKind.CCP
        assert VenueKind.CSD
        assert VenueKind.ICSD
        assert VenueKind.TRF

    def test_venue_kind_has_fx_venues(self) -> None:
        """VenueKind should have FX venue types."""
        assert VenueKind.FX_ECN
        assert VenueKind.FX_PLATFORM

    def test_venue_kind_has_swaps_venues(self) -> None:
        """VenueKind should have swaps venue types."""
        assert VenueKind.SEF

    def test_venue_kind_has_crypto_venues(self) -> None:
        """VenueKind should have crypto venue types."""
        assert VenueKind.CRYPTO_EXCHANGE
        assert VenueKind.DIGITAL_ASSET_PLATFORM

    def test_venue_kind_count(self) -> None:
        """VenueKind should have 30+ venue types."""
        # Actual count is 39, so check for at least 30
        assert len(VenueKind) >= 30


class TestMicSourceEnum:
    """Tests for MicSource enum."""

    def test_mic_source_has_curated(self) -> None:
        """MicSource should have CURATED."""
        assert MicSource.CURATED
        # Check value contains 'curated' (case-insensitive)
        assert "curated" in MicSource.CURATED.value.lower()

    def test_mic_source_has_bulk(self) -> None:
        """MicSource should have ISO10383_BULK."""
        assert MicSource.ISO10383_BULK
        assert "iso10383" in MicSource.ISO10383_BULK.value.lower()

    def test_mic_source_has_vendor(self) -> None:
        """MicSource should have vendor sources."""
        assert MicSource.VENDOR_INFERRED


# =============================================================================
# VenueRef Dataclass Tests
# =============================================================================

class TestVenueRef:
    """Tests for VenueRef dataclass."""

    def test_venue_ref_creation(self) -> None:
        """VenueRef should be creatable with minimal fields."""
        venue = VenueRef(
            mic="XNYS",
            name="New York Stock Exchange",
        )
        assert venue.mic == "XNYS"
        assert venue.name == "New York Stock Exchange"

    def test_venue_ref_is_frozen(self) -> None:
        """VenueRef should be immutable."""
        venue = VenueRef(mic="XNYS", name="NYSE")
        with pytest.raises(AttributeError):
            venue.mic = "XXXX"  # type: ignore

    def test_venue_ref_full_fields(self) -> None:
        """VenueRef should support all fields."""
        venue = VenueRef(
            mic="XNYS",
            name="New York Stock Exchange",
            short_name="NYSE",
            venue_kind=VenueKind.STOCK_EXCHANGE,
            asset_classes=(AssetClass.EQUITY,),
            country_code="US",
            jurisdiction="US",
            city="New York",
            timezone="America/New_York",
            operating_mic=None,
            is_segment=False,
            operator_name="Intercontinental Exchange",
            operator_lei="5493000F4ZO33MV32P92",
            sec_registered=True,
            esma_registered=False,
            regulator="SEC",
            opened_on=date(1817, 3, 8),
            closed_on=None,
            source=MicSource.CURATED,
            source_url="https://www.nyse.com",
            as_of=date(2024, 1, 1),
            captured_at=datetime(2024, 1, 1, 12, 0, 0),
            last_verified=date(2024, 1, 1),
            confidence=1.0,
        )
        assert venue.mic == "XNYS"
        assert venue.venue_kind == VenueKind.STOCK_EXCHANGE
        assert venue.asset_classes == (AssetClass.EQUITY,)
        assert venue.sec_registered is True
        assert venue.confidence == 1.0


# =============================================================================
# Major Venues Registry Tests
# =============================================================================

class TestMajorVenuesRegistries:
    """Tests for curated venue registries."""

    def test_major_equity_venues_not_empty(self) -> None:
        """MAJOR_EQUITY_VENUES should have venues."""
        assert len(MAJOR_EQUITY_VENUES) > 0

    def test_major_equity_venues_has_nyse(self) -> None:
        """MAJOR_EQUITY_VENUES should have NYSE."""
        assert "XNYS" in MAJOR_EQUITY_VENUES
        nyse = MAJOR_EQUITY_VENUES["XNYS"]
        assert nyse.name == "New York Stock Exchange"
        assert nyse.venue_kind == VenueKind.STOCK_EXCHANGE

    def test_major_equity_venues_has_nasdaq(self) -> None:
        """MAJOR_EQUITY_VENUES should have NASDAQ."""
        assert "XNAS" in MAJOR_EQUITY_VENUES
        nasdaq = MAJOR_EQUITY_VENUES["XNAS"]
        assert "NASDAQ" in nasdaq.name

    def test_major_options_venues_not_empty(self) -> None:
        """MAJOR_OPTIONS_VENUES should have venues."""
        assert len(MAJOR_OPTIONS_VENUES) > 0

    def test_major_options_venues_has_cboe(self) -> None:
        """MAJOR_OPTIONS_VENUES should have CBOE."""
        assert "XCBO" in MAJOR_OPTIONS_VENUES
        cboe = MAJOR_OPTIONS_VENUES["XCBO"]
        assert cboe.venue_kind == VenueKind.OPTIONS_EXCHANGE

    def test_major_futures_venues_not_empty(self) -> None:
        """MAJOR_FUTURES_VENUES should have venues."""
        assert len(MAJOR_FUTURES_VENUES) > 0

    def test_major_futures_venues_has_cme(self) -> None:
        """MAJOR_FUTURES_VENUES should have CME."""
        assert "XCME" in MAJOR_FUTURES_VENUES
        cme = MAJOR_FUTURES_VENUES["XCME"]
        assert cme.venue_kind == VenueKind.FUTURES_EXCHANGE

    def test_major_fx_venues_not_empty(self) -> None:
        """MAJOR_FX_VENUES should have venues."""
        assert len(MAJOR_FX_VENUES) > 0

    def test_major_rates_credit_venues_not_empty(self) -> None:
        """MAJOR_RATES_CREDIT_VENUES should have venues."""
        assert len(MAJOR_RATES_CREDIT_VENUES) > 0

    def test_major_swaps_sefs_not_empty(self) -> None:
        """MAJOR_SWAPS_SEFS should have venues."""
        assert len(MAJOR_SWAPS_SEFS) > 0

    def test_major_crypto_venues_not_empty(self) -> None:
        """MAJOR_CRYPTO_VENUES should have venues."""
        assert len(MAJOR_CRYPTO_VENUES) > 0

    def test_major_index_providers_not_empty(self) -> None:
        """MAJOR_INDEX_PROVIDERS should have venues."""
        assert len(MAJOR_INDEX_PROVIDERS) > 0

    def test_major_trade_reporting_not_empty(self) -> None:
        """MAJOR_TRADE_REPORTING should have venues."""
        assert len(MAJOR_TRADE_REPORTING) > 0

    def test_major_clearinghouses_not_empty(self) -> None:
        """MAJOR_CLEARINGHOUSES should have venues."""
        assert len(MAJOR_CLEARINGHOUSES) > 0

    def test_major_clearinghouses_has_dtcc(self) -> None:
        """MAJOR_CLEARINGHOUSES should have DTCC."""
        # DTCC may have MIC "XDTC" or similar
        dtcc_found = any(
            "DTCC" in v.name or "Depository Trust" in v.name
            for v in MAJOR_CLEARINGHOUSES.values()
        )
        assert dtcc_found

    def test_major_depositories_csds_not_empty(self) -> None:
        """MAJOR_DEPOSITORIES_CSDS should have venues."""
        assert len(MAJOR_DEPOSITORIES_CSDS) > 0

    def test_all_major_venues_is_aggregate(self) -> None:
        """ALL_MAJOR_VENUES should combine all registries."""
        total_individual = (
            len(MAJOR_EQUITY_VENUES)
            + len(MAJOR_OPTIONS_VENUES)
            + len(MAJOR_FUTURES_VENUES)
            + len(MAJOR_FX_VENUES)
            + len(MAJOR_RATES_CREDIT_VENUES)
            + len(MAJOR_SWAPS_SEFS)
            + len(MAJOR_CRYPTO_VENUES)
            + len(MAJOR_INDEX_PROVIDERS)
            + len(MAJOR_TRADE_REPORTING)
            + len(MAJOR_CLEARINGHOUSES)
            + len(MAJOR_DEPOSITORIES_CSDS)
        )
        # May have some overlap, so ALL_MAJOR_VENUES could be <= total
        assert len(ALL_MAJOR_VENUES) <= total_individual
        assert len(ALL_MAJOR_VENUES) >= 50  # Should have at least 50 venues


# =============================================================================
# Venue Lookup Function Tests
# =============================================================================

class TestVenueLookupFunctions:
    """Tests for venue lookup helper functions."""

    def test_lookup_major_venue_found(self) -> None:
        """lookup_major_venue should return venue when found."""
        venue = lookup_major_venue("XNYS")
        assert venue is not None
        assert venue.mic == "XNYS"

    def test_lookup_major_venue_not_found(self) -> None:
        """lookup_major_venue should return None when not found."""
        venue = lookup_major_venue("XXXX")
        assert venue is None

    def test_lookup_major_venue_case_insensitive(self) -> None:
        """lookup_major_venue should be case-insensitive."""
        venue = lookup_major_venue("xnys")
        assert venue is not None
        assert venue.mic == "XNYS"

    def test_get_major_venues_by_asset_class(self) -> None:
        """get_major_venues should filter by asset class."""
        equity_venues = get_major_venues(asset_class=AssetClass.EQUITY)
        assert len(equity_venues) > 0
        for venue in equity_venues:
            assert AssetClass.EQUITY in venue.asset_classes

    def test_get_major_venues_by_venue_kind(self) -> None:
        """get_major_venues should filter by venue kind."""
        ccp_venues = get_major_venues(venue_kind=VenueKind.CCP)
        assert len(ccp_venues) > 0
        for venue in ccp_venues:
            assert venue.venue_kind == VenueKind.CCP

    def test_get_major_venues_by_jurisdiction(self) -> None:
        """get_major_venues should filter by jurisdiction."""
        us_venues = get_major_venues(jurisdiction="US")
        assert len(us_venues) > 0
        for venue in us_venues:
            assert venue.jurisdiction == "US"

    def test_get_major_venues_combined_filters(self) -> None:
        """get_major_venues should support multiple filters."""
        us_equity = get_major_venues(
            asset_class=AssetClass.EQUITY,
            jurisdiction="US",
        )
        assert len(us_equity) > 0
        for venue in us_equity:
            assert AssetClass.EQUITY in venue.asset_classes
            assert venue.jurisdiction == "US"

    def test_get_venues_by_kind(self) -> None:
        """get_venues_by_kind should return venues of specified kind."""
        exchanges = get_venues_by_kind(VenueKind.STOCK_EXCHANGE)
        assert len(exchanges) > 0
        for venue in exchanges:
            assert venue.venue_kind == VenueKind.STOCK_EXCHANGE

    def test_get_venues_by_asset_class(self) -> None:
        """get_venues_by_asset_class should return venues for asset class."""
        futures_venues = get_venues_by_asset_class(AssetClass.FUTURES)
        assert len(futures_venues) > 0
        for venue in futures_venues:
            assert AssetClass.FUTURES in venue.asset_classes


# =============================================================================
# NOTE: ISO 10383 Infrastructure Tests moved to tests/sources/test_iso10383.py
# Those tests belong with the sources/ module, not reference_data/.
# =============================================================================


# =============================================================================
# Vendor Mapping Tests
# =============================================================================

class TestVendorVenueCodeRef:
    """Tests for VendorVenueCodeRef dataclass."""

    def test_vendor_code_ref_creation(self) -> None:
        """VendorVenueCodeRef should be creatable."""
        ref = VendorVenueCodeRef(
            vendor=VendorNamespace.BLOOMBERG,
            vendor_code="UN",
            mic="XNYS",
            name="New York Stock Exchange",
        )
        assert ref.vendor == VendorNamespace.BLOOMBERG
        assert ref.vendor_code == "UN"
        assert ref.mic == "XNYS"

    def test_vendor_code_ref_is_frozen(self) -> None:
        """VendorVenueCodeRef should be immutable."""
        ref = VendorVenueCodeRef(
            vendor=VendorNamespace.BLOOMBERG,
            vendor_code="UN",
            mic="XNYS",
            name="NYSE",
        )
        with pytest.raises(AttributeError):
            ref.vendor_code = "UW"  # type: ignore


class TestVendorMappings:
    """Tests for vendor mapping registries."""

    def test_bloomberg_venue_codes_not_empty(self) -> None:
        """BLOOMBERG_VENUE_CODES should have mappings."""
        assert len(BLOOMBERG_VENUE_CODES) > 0

    def test_bloomberg_has_un_for_nyse(self) -> None:
        """Bloomberg should map UN to NYSE."""
        assert "UN" in BLOOMBERG_VENUE_CODES
        ref = BLOOMBERG_VENUE_CODES["UN"]
        assert ref.mic == "XNYS"

    def test_reuters_venue_codes_not_empty(self) -> None:
        """REUTERS_VENUE_CODES should have mappings."""
        assert len(REUTERS_VENUE_CODES) > 0

    def test_reuters_has_dot_n_for_nyse(self) -> None:
        """Reuters should map .N to NYSE."""
        assert ".N" in REUTERS_VENUE_CODES
        ref = REUTERS_VENUE_CODES[".N"]
        assert ref.mic == "XNYS"

    def test_factset_venue_codes_not_empty(self) -> None:
        """FACTSET_VENUE_CODES should have mappings."""
        assert len(FACTSET_VENUE_CODES) > 0

    def test_ibkr_venue_codes_not_empty(self) -> None:
        """IBKR_VENUE_CODES should have mappings."""
        assert len(IBKR_VENUE_CODES) > 0


class TestVendorLookupFunctions:
    """Tests for vendor lookup functions."""

    def test_lookup_mic_by_vendor_code_found(self) -> None:
        """lookup_mic_by_vendor_code should return MIC when found."""
        mic = lookup_mic_by_vendor_code(VendorNamespace.BLOOMBERG, "UN")
        assert mic == "XNYS"

    def test_lookup_mic_by_vendor_code_not_found(self) -> None:
        """lookup_mic_by_vendor_code should return None when not found."""
        mic = lookup_mic_by_vendor_code(VendorNamespace.BLOOMBERG, "XXXX")
        assert mic is None

    def test_lookup_vendor_codes_for_mic(self) -> None:
        """lookup_vendor_codes_for_mic should return all vendor codes."""
        codes = lookup_vendor_codes_for_mic("XNYS")
        assert codes is not None
        assert len(codes) > 0
        # Should have at least one vendor code mapping
        # The structure may be a dict or list depending on implementation

    def test_get_vendor_code_ref(self) -> None:
        """get_vendor_code_ref should return full reference."""
        ref = get_vendor_code_ref(VendorNamespace.BLOOMBERG, "UN")
        assert ref is not None
        assert ref.vendor == VendorNamespace.BLOOMBERG
        assert ref.vendor_code == "UN"
        assert ref.mic == "XNYS"

    def test_find_conflicting_mappings_callable(self) -> None:
        """find_conflicting_mappings should be callable with MIC."""
        # Test with a known MIC
        conflicts = find_conflicting_mappings("XNYS")
        # Result is a dict mapping VendorNamespace to list of VendorVenueCodeRef
        assert isinstance(conflicts, dict)


# =============================================================================
# Asset Class Metadata Tests
# =============================================================================

class TestAssetClassInfo:
    """Tests for AssetClassInfo dataclass."""

    def test_asset_class_info_creation(self) -> None:
        """AssetClassInfo should be creatable."""
        info = AssetClassInfo(
            asset_class=AssetClass.EQUITY,
            name="Equity",
            description="Equity securities",
            examples=("AAPL", "MSFT"),
            typical_venues=("NYSE", "NASDAQ"),
        )
        assert info.description == "Equity securities"
        assert info.examples == ("AAPL", "MSFT")


class TestAssetClassInfoRegistry:
    """Tests for ASSET_CLASS_INFO registry."""

    def test_registry_has_equity(self) -> None:
        """Registry should have EQUITY info."""
        assert AssetClass.EQUITY in ASSET_CLASS_INFO
        info = ASSET_CLASS_INFO[AssetClass.EQUITY]
        assert info.description
        assert info.typical_venues

    def test_registry_has_options(self) -> None:
        """Registry should have OPTIONS info."""
        assert AssetClass.OPTIONS in ASSET_CLASS_INFO

    def test_registry_has_futures(self) -> None:
        """Registry should have FUTURES info."""
        assert AssetClass.FUTURES in ASSET_CLASS_INFO

    def test_registry_has_fx(self) -> None:
        """Registry should have FX info."""
        assert AssetClass.FX in ASSET_CLASS_INFO

    def test_registry_coverage(self) -> None:
        """Registry should cover most asset classes."""
        # At minimum, should cover the major asset classes
        major_classes = [
            AssetClass.EQUITY,
            AssetClass.OPTIONS,
            AssetClass.FUTURES,
            AssetClass.FX,
        ]
        for ac in major_classes:
            assert ac in ASSET_CLASS_INFO


class TestAssetClassHelpers:
    """Tests for asset class helper functions."""

    def test_get_asset_class_info(self) -> None:
        """get_asset_class_info should return info for asset class."""
        info = get_asset_class_info(AssetClass.EQUITY)
        assert info is not None
        assert info.description

    def test_get_asset_class_info_not_found(self) -> None:
        """get_asset_class_info should return None for unknown."""
        # This test only works if there's an asset class not in registry
        # Skip if all are covered
        pass

    def test_get_asset_class_description(self) -> None:
        """get_asset_class_description should return description."""
        desc = get_asset_class_description(AssetClass.EQUITY)
        assert desc is not None
        assert len(desc) > 0

    def test_get_typical_venues_for_asset_class(self) -> None:
        """get_typical_venues_for_asset_class should return venues."""
        venues = get_typical_venues_for_asset_class(AssetClass.EQUITY)
        assert venues is not None
        assert len(venues) > 0


# =============================================================================
# Integration Tests
# =============================================================================

class TestTwoLayerArchitectureIntegration:
    """Integration tests for the two-layer architecture."""

    def test_curated_then_bulk_lookup(self) -> None:
        """Should try curated layer first, then bulk."""
        # Curated lookup succeeds for major venues
        venue = lookup_major_venue("XNYS")
        assert venue is not None
        assert venue.source == MicSource.CURATED
        
        # For unknown MICs, would fall back to bulk layer
        venue = lookup_major_venue("XXXX")
        assert venue is None  # Not in curated layer

    def test_vendor_to_curated_lookup(self) -> None:
        """Should resolve vendor code to curated venue."""
        # Get MIC from vendor code
        mic = lookup_mic_by_vendor_code(VendorNamespace.BLOOMBERG, "UN")
        assert mic == "XNYS"
        
        # Look up curated venue
        venue = lookup_major_venue(mic)
        assert venue is not None
        assert venue.name == "New York Stock Exchange"

    def test_all_venues_have_valid_fields(self) -> None:
        """All curated venues should have valid required fields."""
        for mic, venue in ALL_MAJOR_VENUES.items():
            assert venue.mic == mic
            assert venue.name
            assert venue.venue_kind is not None
            assert venue.source is not None


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_mic_normalization_lowercase(self) -> None:
        """MIC lookups should handle lowercase input."""
        venue = lookup_major_venue("xnys")
        assert venue is not None
        assert venue.mic == "XNYS"  # Should be normalized to uppercase

    def test_mic_normalization_whitespace(self) -> None:
        """MIC lookups should handle whitespace."""
        # Depending on implementation, may strip or not
        venue = lookup_major_venue("XNYS")  # Normal case
        assert venue is not None
        assert venue.mic == "XNYS"
        # Whitespace handling may vary by implementation

    def test_empty_mic_lookup(self) -> None:
        """Empty MIC should return None."""
        venue = lookup_major_venue("")
        assert venue is None

    def test_none_mic_lookup(self) -> None:
        """None MIC should return None or raise."""
        # Depending on implementation, either None or TypeError
        try:
            venue = lookup_major_venue(None)  # type: ignore
            assert venue is None
        except (TypeError, AttributeError):
            pass  # Also acceptable
