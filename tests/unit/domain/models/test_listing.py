"""
Tests for v2.2 Listing domain dataclass.

v2.2 CRITICAL: Listing is WHERE ticker lives.
- NOT on Entity
- NOT on Security
- ON Listing (with MIC and validity period)

IMPORTANT: These tests use the CANONICAL domain dataclasses (entityspine.domain),
NOT the optional Pydantic wrappers (entityspine.adapters.pydantic).
"""

import dataclasses
from datetime import date

import pytest

from entityspine.domain import Listing


class TestListingCreation:
    """Test Listing creation."""

    def test_listing_has_ticker(self):
        """v2.2: Listing MUST have ticker attribute."""
        listing = Listing(
            listing_id="01LST3NDEKTSV4RRFFQ69G5FAV",
            security_id="01SEC3NDEKTSV4RRFFQ69G5FAV",
            ticker="AAPL",
            exchange="NASDAQ",
        )
        assert listing.ticker == "AAPL"
        field_names = {f.name for f in dataclasses.fields(Listing)}
        assert "ticker" in field_names

    def test_listing_has_exchange(self):
        """v2.2: Listing MUST have exchange attribute."""
        listing = Listing(
            listing_id="01LST3NDEKTSV4RRFFQ69G5FAV",
            security_id="01SEC3NDEKTSV4RRFFQ69G5FAV",
            ticker="AAPL",
            exchange="NASDAQ",
        )
        assert listing.exchange == "NASDAQ"
        field_names = {f.name for f in dataclasses.fields(Listing)}
        assert "exchange" in field_names

    def test_listing_requires_ticker(self):
        """Listing must have ticker (required field)."""
        with pytest.raises(TypeError):
            Listing(
                listing_id="01LST3NDEKTSV4RRFFQ69G5FAV",
                security_id="01SEC3NDEKTSV4RRFFQ69G5FAV",
                exchange="NASDAQ",
                # Missing ticker - should fail
            )

    def test_listing_requires_security_id(self):
        """Listing must link to a security."""
        with pytest.raises(TypeError):
            Listing(
                listing_id="01LST3NDEKTSV4RRFFQ69G5FAV",
                # Missing security_id
                ticker="AAPL",
                exchange="NASDAQ",
            )

    def test_listing_with_all_fields(self):
        """Listing can be created with all optional fields."""
        listing = Listing(
            listing_id="01LST3NDEKTSV4RRFFQ69G5FAV",
            security_id="01SEC3NDEKTSV4RRFFQ69G5FAV",
            ticker="AAPL",
            exchange="NASDAQ",
            mic="XNAS",
            is_primary=True,
            start_date=date(1980, 12, 12),
            end_date=None,
            currency="USD",
        )
        assert listing.mic == "XNAS"
        assert listing.is_primary is True
        assert listing.currency == "USD"


class TestListingTemporality:
    """v2.2: Listings have validity periods for ticker reuse."""

    def test_listing_has_start_date(self):
        """Listing can have start_date."""
        listing = Listing(
            listing_id="01LST3NDEKTSV4RRFFQ69G5FAV",
            security_id="01SEC3NDEKTSV4RRFFQ69G5FAV",
            ticker="AAPL",
            exchange="NASDAQ",
            start_date=date(1980, 12, 12),
        )
        assert listing.start_date == date(1980, 12, 12)

    def test_listing_has_end_date(self):
        """Listing can have end_date for delisted/renamed tickers."""
        listing = Listing(
            listing_id="01LST3NDEKTSV4RRFFQ69G5FAV",
            security_id="01SEC3NDEKTSV4RRFFQ69G5FAV",
            ticker="FB",
            exchange="NASDAQ",
            start_date=date(2012, 5, 18),
            end_date=date(2022, 6, 9),  # Before META rename
        )
        assert listing.end_date == date(2022, 6, 9)

    def test_listing_is_active_property(self):
        """Listing has is_active property based on end_date."""
        active_listing = Listing(
            listing_id="01LST3NDEKTSV4RRFFQ69G5FAV",
            security_id="01SEC3NDEKTSV4RRFFQ69G5FAV",
            ticker="AAPL",
            exchange="NASDAQ",
            end_date=None,
        )
        assert active_listing.is_active is True

        inactive_listing = Listing(
            listing_id="01LST3NDEKTSV4RRFFQ69G5FAV",
            security_id="01SEC3NDEKTSV4RRFFQ69G5FAV",
            ticker="FB",
            exchange="NASDAQ",
            end_date=date(2022, 6, 9),
        )
        assert inactive_listing.is_active is False


class TestListingMIC:
    """Test Market Identifier Code support."""

    def test_listing_has_mic(self):
        """Listing can have MIC (Market Identifier Code)."""
        listing = Listing(
            listing_id="01LST3NDEKTSV4RRFFQ69G5FAV",
            security_id="01SEC3NDEKTSV4RRFFQ69G5FAV",
            ticker="AAPL",
            exchange="NASDAQ",
            mic="XNAS",
        )
        assert listing.mic == "XNAS"

    def test_mic_is_optional(self):
        """MIC is optional."""
        listing = Listing(
            listing_id="01LST3NDEKTSV4RRFFQ69G5FAV",
            security_id="01SEC3NDEKTSV4RRFFQ69G5FAV",
            ticker="AAPL",
            exchange="NASDAQ",
        )
        assert listing.mic is None


class TestListingTickerFormats:
    """Test various ticker formats."""

    def test_simple_ticker(self):
        """Standard ticker format."""
        listing = Listing(
            listing_id="01LST3NDEKTSV4RRFFQ69G5FAV",
            security_id="01SEC3NDEKTSV4RRFFQ69G5FAV",
            ticker="AAPL",
            exchange="NASDAQ",
        )
        assert listing.ticker == "AAPL"

    def test_dot_notation_ticker(self):
        """Ticker with dot notation (e.g., BRK.B)."""
        listing = Listing(
            listing_id="01LST3NDEKTSV4RRFFQ69G5FAV",
            security_id="01SEC3NDEKTSV4RRFFQ69G5FAV",
            ticker="BRK.B",
            exchange="NYSE",
        )
        assert listing.ticker == "BRK.B"

    def test_dash_notation_ticker(self):
        """Ticker with dash notation gets normalized to dot."""
        listing = Listing(
            listing_id="01LST3NDEKTSV4RRFFQ69G5FAV",
            security_id="01SEC3NDEKTSV4RRFFQ69G5FAV",
            ticker="BRK-B",  # Will be normalized to BRK.B
            exchange="NYSE",
        )
        assert listing.ticker == "BRK.B"  # Normalized


class TestListingPrimary:
    """Test primary listing support."""

    def test_is_primary_default_false(self):
        """is_primary defaults to False."""
        listing = Listing(
            listing_id="01LST3NDEKTSV4RRFFQ69G5FAV",
            security_id="01SEC3NDEKTSV4RRFFQ69G5FAV",
            ticker="AAPL",
            exchange="NASDAQ",
        )
        assert listing.is_primary is False

    def test_can_set_primary(self):
        """Can explicitly set is_primary."""
        listing = Listing(
            listing_id="01LST3NDEKTSV4RRFFQ69G5FAV",
            security_id="01SEC3NDEKTSV4RRFFQ69G5FAV",
            ticker="AAPL",
            exchange="NASDAQ",
            is_primary=True,
        )
        assert listing.is_primary is True
