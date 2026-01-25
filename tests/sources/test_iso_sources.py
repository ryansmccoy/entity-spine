"""
Unit tests for ISO 3166 and ISO 4217 sources.

Tests the Bronze/Silver/Gold architecture for country and currency codes.
"""

from __future__ import annotations

from datetime import date

import pytest

from entityspine.sources.iso3166 import (
    ISO3166Source,
    CountryRegistry,
    CountryRecord,
    CountrySnapshot,
)
from entityspine.sources.iso4217 import (
    ISO4217Source,
    CurrencyRegistry,
    CurrencyRecord,
    CurrencySnapshot,
    CURRENCY_SYMBOLS,
)


# =============================================================================
# ISO 3166 Country Tests
# =============================================================================


class TestCountryRecord:
    """Tests for CountryRecord dataclass."""
    
    def test_country_record_creation(self) -> None:
        """CountryRecord should be creatable with minimal fields."""
        record = CountryRecord(
            alpha2="US",
            alpha3="USA",
            numeric="840",
            name="United States",
        )
        assert record.alpha2 == "US"
        assert record.alpha3 == "USA"
        assert record.numeric == "840"
        assert record.name == "United States"
    
    def test_country_record_is_frozen(self) -> None:
        """CountryRecord should be immutable."""
        record = CountryRecord(alpha2="US", name="United States")
        with pytest.raises(AttributeError):
            record.alpha2 = "XX"  # type: ignore
    
    def test_country_record_validation(self) -> None:
        """CountryRecord should validate alpha2 code."""
        with pytest.raises(ValueError):
            CountryRecord(alpha2="", name="Invalid")
        
        with pytest.raises(ValueError):
            CountryRecord(alpha2="USA", name="Invalid")  # Too long
    
    def test_country_record_full_fields(self) -> None:
        """CountryRecord should support all fields."""
        record = CountryRecord(
            alpha2="US",
            alpha3="USA",
            numeric="840",
            name="United States",
            official_name="United States of America",
            region="Americas",
            subregion="Northern America",
            capital="Washington, D.C.",
            currencies=("USD",),
            languages=("eng",),
            timezones=("America/New_York", "America/Chicago", "America/Los_Angeles"),
            flag_emoji="🇺🇸",
            independent=True,
            status="officially-assigned",
        )
        assert record.region == "Americas"
        assert record.currencies == ("USD",)
        assert len(record.timezones) == 3


class TestCountryRegistry:
    """Tests for CountryRegistry."""
    
    @pytest.fixture
    def sample_countries(self) -> list[CountryRecord]:
        """Create sample country records for testing."""
        return [
            CountryRecord(
                alpha2="US",
                alpha3="USA",
                numeric="840",
                name="United States",
                region="Americas",
            ),
            CountryRecord(
                alpha2="GB",
                alpha3="GBR",
                numeric="826",
                name="United Kingdom",
                region="Europe",
            ),
            CountryRecord(
                alpha2="JP",
                alpha3="JPN",
                numeric="392",
                name="Japan",
                region="Asia",
            ),
        ]
    
    def test_registry_lookup_alpha2(self, sample_countries: list[CountryRecord]) -> None:
        """Registry should look up by alpha-2 code."""
        registry = CountryRegistry()
        registry.load_from_records(sample_countries)
        
        us = registry.lookup("US")
        assert us is not None
        assert us.name == "United States"
        
        # Case insensitive
        us_lower = registry.lookup("us")
        assert us_lower is not None
        assert us_lower.name == "United States"
    
    def test_registry_lookup_alpha3(self, sample_countries: list[CountryRecord]) -> None:
        """Registry should look up by alpha-3 code."""
        registry = CountryRegistry()
        registry.load_from_records(sample_countries)
        
        gb = registry.lookup_alpha3("GBR")
        assert gb is not None
        assert gb.alpha2 == "GB"
    
    def test_registry_lookup_numeric(self, sample_countries: list[CountryRecord]) -> None:
        """Registry should look up by numeric code."""
        registry = CountryRegistry()
        registry.load_from_records(sample_countries)
        
        jp = registry.lookup_numeric("392")
        assert jp is not None
        assert jp.alpha2 == "JP"
    
    def test_registry_is_valid(self, sample_countries: list[CountryRecord]) -> None:
        """Registry should validate codes."""
        registry = CountryRegistry()
        registry.load_from_records(sample_countries)
        
        assert registry.is_valid("US") is True
        assert registry.is_valid("USA") is True
        assert registry.is_valid("840") is True
        assert registry.is_valid("XX") is False
        assert registry.is_valid("XXX") is False
    
    def test_registry_normalize_to_alpha2(self, sample_countries: list[CountryRecord]) -> None:
        """Registry should normalize codes to alpha-2."""
        registry = CountryRegistry()
        registry.load_from_records(sample_countries)
        
        assert registry.normalize_to_alpha2("US") == "US"
        assert registry.normalize_to_alpha2("USA") == "US"
        assert registry.normalize_to_alpha2("840") == "US"
        assert registry.normalize_to_alpha2("XX") is None
    
    def test_registry_get_by_region(self, sample_countries: list[CountryRecord]) -> None:
        """Registry should filter by region."""
        registry = CountryRegistry()
        registry.load_from_records(sample_countries)
        
        americas = registry.get_by_region("Americas")
        assert len(americas) == 1
        assert americas[0].alpha2 == "US"
    
    def test_registry_search_by_name(self, sample_countries: list[CountryRecord]) -> None:
        """Registry should search by name."""
        registry = CountryRegistry()
        registry.load_from_records(sample_countries)
        
        results = registry.search_by_name("United")
        assert len(results) == 2  # US and GB
    
    def test_registry_contains(self, sample_countries: list[CountryRecord]) -> None:
        """Registry should support 'in' operator."""
        registry = CountryRegistry()
        registry.load_from_records(sample_countries)
        
        assert "US" in registry
        assert "XX" not in registry
    
    def test_registry_len(self, sample_countries: list[CountryRecord]) -> None:
        """Registry should support len()."""
        registry = CountryRegistry()
        registry.load_from_records(sample_countries)
        
        assert len(registry) == 3


# =============================================================================
# ISO 4217 Currency Tests
# =============================================================================


class TestCurrencyRecord:
    """Tests for CurrencyRecord dataclass."""
    
    def test_currency_record_creation(self) -> None:
        """CurrencyRecord should be creatable with minimal fields."""
        record = CurrencyRecord(
            alpha3="USD",
            numeric="840",
            name="US Dollar",
        )
        assert record.alpha3 == "USD"
        assert record.numeric == "840"
        assert record.name == "US Dollar"
    
    def test_currency_record_is_frozen(self) -> None:
        """CurrencyRecord should be immutable."""
        record = CurrencyRecord(alpha3="USD", name="US Dollar")
        with pytest.raises(AttributeError):
            record.alpha3 = "EUR"  # type: ignore
    
    def test_currency_record_validation(self) -> None:
        """CurrencyRecord should validate alpha3 code."""
        with pytest.raises(ValueError):
            CurrencyRecord(alpha3="", name="Invalid")
        
        with pytest.raises(ValueError):
            CurrencyRecord(alpha3="US", name="Invalid")  # Too short
    
    def test_currency_record_display_symbol(self) -> None:
        """CurrencyRecord should return display symbol."""
        usd = CurrencyRecord(alpha3="USD", name="US Dollar", symbol="$")
        assert usd.display_symbol == "$"
        
        zzz = CurrencyRecord(alpha3="ZZZ", name="Unknown")
        assert zzz.display_symbol == "ZZZ"
    
    def test_currency_record_full_fields(self) -> None:
        """CurrencyRecord should support all fields."""
        record = CurrencyRecord(
            alpha3="USD",
            numeric="840",
            name="US Dollar",
            minor_unit=2,
            country_codes=("US",),
            symbol="$",
            is_fund=False,
            is_precious_metal=False,
            is_supranational=False,
            is_active=True,
        )
        assert record.minor_unit == 2
        assert record.symbol == "$"


class TestCurrencyRegistry:
    """Tests for CurrencyRegistry."""
    
    @pytest.fixture
    def sample_currencies(self) -> list[CurrencyRecord]:
        """Create sample currency records for testing."""
        return [
            CurrencyRecord(
                alpha3="USD",
                numeric="840",
                name="US Dollar",
                minor_unit=2,
                symbol="$",
            ),
            CurrencyRecord(
                alpha3="EUR",
                numeric="978",
                name="Euro",
                minor_unit=2,
                symbol="€",
            ),
            CurrencyRecord(
                alpha3="JPY",
                numeric="392",
                name="Yen",
                minor_unit=0,
                symbol="¥",
            ),
            CurrencyRecord(
                alpha3="XAU",
                numeric="959",
                name="Gold",
                is_precious_metal=True,
            ),
        ]
    
    def test_registry_lookup(self, sample_currencies: list[CurrencyRecord]) -> None:
        """Registry should look up by alpha-3 code."""
        registry = CurrencyRegistry()
        registry.load_from_records(sample_currencies)
        
        usd = registry.lookup("USD")
        assert usd is not None
        assert usd.name == "US Dollar"
        
        # Case insensitive
        usd_lower = registry.lookup("usd")
        assert usd_lower is not None
    
    def test_registry_lookup_numeric(self, sample_currencies: list[CurrencyRecord]) -> None:
        """Registry should look up by numeric code."""
        registry = CurrencyRegistry()
        registry.load_from_records(sample_currencies)
        
        eur = registry.lookup_numeric("978")
        assert eur is not None
        assert eur.alpha3 == "EUR"
    
    def test_registry_is_valid(self, sample_currencies: list[CurrencyRecord]) -> None:
        """Registry should validate codes."""
        registry = CurrencyRegistry()
        registry.load_from_records(sample_currencies)
        
        assert registry.is_valid("USD") is True
        assert registry.is_valid("840") is True
        assert registry.is_valid("ZZZ") is False
    
    def test_registry_normalize_to_alpha3(self, sample_currencies: list[CurrencyRecord]) -> None:
        """Registry should normalize codes to alpha-3."""
        registry = CurrencyRegistry()
        registry.load_from_records(sample_currencies)
        
        assert registry.normalize_to_alpha3("USD") == "USD"
        assert registry.normalize_to_alpha3("840") == "USD"
        assert registry.normalize_to_alpha3("ZZZ") is None
    
    def test_registry_get_minor_unit(self, sample_currencies: list[CurrencyRecord]) -> None:
        """Registry should return minor units."""
        registry = CurrencyRegistry()
        registry.load_from_records(sample_currencies)
        
        assert registry.get_minor_unit("USD") == 2
        assert registry.get_minor_unit("JPY") == 0
        assert registry.get_minor_unit("ZZZ") is None
    
    def test_registry_get_symbol(self, sample_currencies: list[CurrencyRecord]) -> None:
        """Registry should return symbols."""
        registry = CurrencyRegistry()
        registry.load_from_records(sample_currencies)
        
        assert registry.get_symbol("USD") == "$"
        assert registry.get_symbol("EUR") == "€"
        assert registry.get_symbol("ZZZ") == "ZZZ"
    
    def test_registry_get_active_currencies(self, sample_currencies: list[CurrencyRecord]) -> None:
        """Registry should filter active currencies."""
        registry = CurrencyRegistry()
        registry.load_from_records(sample_currencies)
        
        active = registry.get_active_currencies()
        assert len(active) == 4
    
    def test_registry_get_precious_metals(self, sample_currencies: list[CurrencyRecord]) -> None:
        """Registry should filter precious metals."""
        registry = CurrencyRegistry()
        registry.load_from_records(sample_currencies)
        
        metals = registry.get_precious_metals()
        assert len(metals) == 1
        assert metals[0].alpha3 == "XAU"
    
    def test_registry_search_by_name(self, sample_currencies: list[CurrencyRecord]) -> None:
        """Registry should search by name."""
        registry = CurrencyRegistry()
        registry.load_from_records(sample_currencies)
        
        results = registry.search_by_name("Dollar")
        assert len(results) == 1
        assert results[0].alpha3 == "USD"


class TestCurrencySymbols:
    """Tests for currency symbol mapping."""
    
    def test_major_currencies_have_symbols(self) -> None:
        """Major currencies should have symbols defined."""
        major = ["USD", "EUR", "GBP", "JPY", "CNY", "CHF", "CAD", "AUD"]
        for code in major:
            assert code in CURRENCY_SYMBOLS
            assert len(CURRENCY_SYMBOLS[code]) >= 1
    
    def test_precious_metals_have_symbols(self) -> None:
        """Precious metal codes should have symbols."""
        metals = ["XAU", "XAG", "XPT", "XPD"]
        for code in metals:
            assert code in CURRENCY_SYMBOLS


# =============================================================================
# Integration Tests (require network)
# =============================================================================


@pytest.mark.asyncio
class TestISO3166SourceIntegration:
    """Integration tests for ISO 3166 source (requires network)."""
    
    @pytest.mark.skip(reason="Requires network access")
    async def test_fetch_countries(self) -> None:
        """Should fetch country data from source."""
        source = ISO3166Source()
        snapshot, records = await source.fetch()
        
        assert len(records) > 200  # Should have 200+ countries
        assert snapshot.record_count == len(records)
        
        # Should have major countries
        alpha2_codes = {r.alpha2 for r in records}
        assert "US" in alpha2_codes
        assert "GB" in alpha2_codes
        assert "JP" in alpha2_codes


@pytest.mark.asyncio
class TestISO4217SourceIntegration:
    """Integration tests for ISO 4217 source (requires network)."""
    
    @pytest.mark.skip(reason="Requires network access")
    async def test_fetch_currencies(self) -> None:
        """Should fetch currency data from source."""
        source = ISO4217Source()
        snapshot, records = await source.fetch()
        
        assert len(records) > 150  # Should have 150+ currencies
        assert snapshot.record_count == len(records)
        
        # Should have major currencies
        alpha3_codes = {r.alpha3 for r in records}
        assert "USD" in alpha3_codes
        assert "EUR" in alpha3_codes
        assert "JPY" in alpha3_codes
