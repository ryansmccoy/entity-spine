"""
ISO 3166 Country Code Source.

STDLIB ONLY - NO PYDANTIC.

Downloads and manages ISO 3166-1 country codes for validation and enrichment.

This implements a Bronze/Silver/Gold data architecture:
- Bronze: Raw JSON/CSV snapshots stored immutably
- Silver: Normalized country records with change tracking
- Gold: Domain-ready registry with lookup APIs

Data Sources:
- Primary: https://restcountries.com/v3.1/all (REST Countries API - free)
- Fallback: https://raw.githubusercontent.com/lukes/ISO-3166-Countries-with-Regional-Codes/master/all/all.json
- Official: https://www.iso.org/obp/ui/#search/code/ (requires scraping)

Standards:
- ISO 3166-1 alpha-2: Two-letter codes (US, GB, JP)
- ISO 3166-1 alpha-3: Three-letter codes (USA, GBR, JPN)
- ISO 3166-1 numeric: Three-digit codes (840, 826, 392)
- ISO 3166-2: Subdivisions (US-NY, GB-ENG)

Update Cadence:
- ISO updates ~2-4 times per year
- Changes are rare (new countries, name changes)

Example:
    >>> from entityspine.sources import ISO3166Source, CountryRegistry
    >>>
    >>> source = ISO3166Source()
    >>> records = await source.fetch()
    >>> print(f"Fetched {len(records)} countries")
    >>>
    >>> registry = CountryRegistry()
    >>> await registry.load_from_source()
    >>> us = registry.lookup("US")
    >>> print(f"{us.name} ({us.alpha3})")  # United States of America (USA)

v1.0.0 Initial implementation.
"""

from __future__ import annotations

import hashlib
import json
import logging
import urllib.request
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime

from entityspine.domain.timestamps import utc_now

logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

# REST Countries API (free, no auth required) - v3.1 all fields
REST_COUNTRIES_URL = "https://restcountries.com/v3.1/all"

# GitHub mirror of ISO 3166 data (fallback)
GITHUB_ISO3166_URL = "https://raw.githubusercontent.com/lukes/ISO-3166-Countries-with-Regional-Codes/master/all/all.json"

# User agent for requests
USER_AGENT = "EntitySpine/1.0 (ISO 3166 Country Data)"


# =============================================================================
# Bronze Layer: Raw Snapshot
# =============================================================================


@dataclass(frozen=True, slots=True)
class CountrySnapshot:
    """
    Bronze layer: Immutable raw snapshot of ISO 3166 data.
    
    Stores the raw downloaded content with metadata for provenance tracking.
    
    Attributes:
        snapshot_id: Unique identifier for this snapshot.
        source_url: URL the data was fetched from.
        content_hash: SHA-256 hash of content for deduplication.
        content_size: Size in bytes.
        record_count: Number of country records in snapshot.
        captured_at: When snapshot was captured.
        raw_content: The raw JSON content (optional, for Bronze storage).
    """
    snapshot_id: str
    source_url: str
    content_hash: str
    content_size: int
    record_count: int
    captured_at: datetime
    raw_content: str | None = None

    @classmethod
    def from_response(
        cls,
        content: bytes,
        source_url: str,
        record_count: int,
        store_content: bool = False,
    ) -> CountrySnapshot:
        """Create snapshot from HTTP response content."""
        content_str = content.decode("utf-8")
        content_hash = hashlib.sha256(content).hexdigest()
        captured_at = utc_now()
        snapshot_id = f"iso3166_{captured_at.strftime('%Y%m%d_%H%M%S')}_{content_hash[:8]}"

        return cls(
            snapshot_id=snapshot_id,
            source_url=source_url,
            content_hash=content_hash,
            content_size=len(content),
            record_count=record_count,
            captured_at=captured_at,
            raw_content=content_str if store_content else None,
        )


# =============================================================================
# Silver Layer: Normalized Record
# =============================================================================


@dataclass(frozen=True, slots=True)
class CountryRecord:
    """
    Silver layer: Normalized ISO 3166-1 country record.
    
    Represents a single country with all standard identifiers and metadata.
    
    Attributes:
        alpha2: ISO 3166-1 alpha-2 code (e.g., "US").
        alpha3: ISO 3166-1 alpha-3 code (e.g., "USA").
        numeric: ISO 3166-1 numeric code (e.g., "840").
        name: Common name (e.g., "United States").
        official_name: Official name (e.g., "United States of America").
        region: Geographic region (e.g., "Americas").
        subregion: Geographic subregion (e.g., "Northern America").
        capital: Capital city (e.g., "Washington, D.C.").
        currencies: Currency codes used (e.g., ("USD",)).
        languages: Official languages (e.g., ("eng",)).
        timezones: IANA timezone(s) (e.g., ("America/New_York", ...)).
        flag_emoji: Flag emoji (e.g., "🇺🇸").
        independent: Whether country is independent.
        status: ISO status (e.g., "officially-assigned").
    """
    # Core identifiers
    alpha2: str
    alpha3: str | None = None
    numeric: str | None = None

    # Names
    name: str = ""
    official_name: str | None = None

    # Geography
    region: str | None = None
    subregion: str | None = None
    capital: str | None = None

    # Related codes
    currencies: tuple[str, ...] = ()
    languages: tuple[str, ...] = ()
    timezones: tuple[str, ...] = ()

    # Metadata
    flag_emoji: str | None = None
    independent: bool | None = None
    status: str = "officially-assigned"

    def __post_init__(self) -> None:
        """Validate required fields."""
        if not self.alpha2 or len(self.alpha2) != 2:
            raise ValueError(f"Invalid alpha2 code: {self.alpha2}")


# =============================================================================
# Gold Layer: Country Registry
# =============================================================================


class CountryRegistry:
    """
    Gold layer: Fast lookup registry for country codes.
    
    Provides O(1) lookup by alpha-2, alpha-3, or numeric code.
    Supports validation, enrichment, and cross-referencing.
    
    Example:
        >>> registry = CountryRegistry()
        >>> await registry.load_from_source()
        >>>
        >>> # Lookup by alpha-2
        >>> us = registry.lookup("US")
        >>> print(us.name)  # "United States"
        >>>
        >>> # Lookup by alpha-3
        >>> gb = registry.lookup_alpha3("GBR")
        >>> print(gb.alpha2)  # "GB"
        >>>
        >>> # Validate code
        >>> registry.is_valid("XX")  # False
    """

    def __init__(self) -> None:
        self._by_alpha2: dict[str, CountryRecord] = {}
        self._by_alpha3: dict[str, str] = {}  # alpha3 -> alpha2
        self._by_numeric: dict[str, str] = {}  # numeric -> alpha2
        self._by_region: dict[str, list[str]] = {}  # region -> [alpha2]
        self._snapshot: CountrySnapshot | None = None
        self._loaded_at: datetime | None = None

    @property
    def snapshot(self) -> CountrySnapshot | None:
        """The Bronze snapshot this registry was loaded from."""
        return self._snapshot

    @property
    def loaded_at(self) -> datetime | None:
        """When this registry was loaded."""
        return self._loaded_at

    def __len__(self) -> int:
        return len(self._by_alpha2)

    def __contains__(self, alpha2: str) -> bool:
        return alpha2.upper() in self._by_alpha2

    def __iter__(self) -> Iterator[CountryRecord]:
        return iter(self._by_alpha2.values())

    async def load_from_source(
        self,
        source: ISO3166Source | None = None,
    ) -> CountrySnapshot:
        """
        Load registry from ISO 3166 source.
        
        Args:
            source: Optional source instance. Creates default if None.
            
        Returns:
            The Bronze snapshot that was loaded.
        """
        if source is None:
            source = ISO3166Source()

        snapshot, records = await source.fetch()
        self._load_records(records)
        self._snapshot = snapshot
        self._loaded_at = utc_now()

        logger.info(
            f"Loaded {len(self)} countries from {snapshot.source_url}"
        )
        return snapshot

    def load_from_records(self, records: list[CountryRecord]) -> None:
        """Load registry from pre-parsed records."""
        self._load_records(records)
        self._loaded_at = utc_now()

    def _load_records(self, records: list[CountryRecord]) -> None:
        """Internal method to index records."""
        self._by_alpha2.clear()
        self._by_alpha3.clear()
        self._by_numeric.clear()
        self._by_region.clear()

        for rec in records:
            alpha2 = rec.alpha2.upper()
            self._by_alpha2[alpha2] = rec

            if rec.alpha3:
                self._by_alpha3[rec.alpha3.upper()] = alpha2

            if rec.numeric:
                self._by_numeric[rec.numeric] = alpha2

            if rec.region:
                if rec.region not in self._by_region:
                    self._by_region[rec.region] = []
                self._by_region[rec.region].append(alpha2)

    def lookup(self, alpha2: str) -> CountryRecord | None:
        """
        Look up country by ISO 3166-1 alpha-2 code.
        
        Args:
            alpha2: Two-letter country code (case-insensitive).
            
        Returns:
            CountryRecord if found, None otherwise.
        """
        return self._by_alpha2.get(alpha2.upper())

    def get(self, alpha2: str) -> CountryRecord | None:
        """Alias for lookup() - provides consistent API across registries."""
        return self.lookup(alpha2)

    def lookup_alpha3(self, alpha3: str) -> CountryRecord | None:
        """
        Look up country by ISO 3166-1 alpha-3 code.
        
        Args:
            alpha3: Three-letter country code (case-insensitive).
            
        Returns:
            CountryRecord if found, None otherwise.
        """
        alpha2 = self._by_alpha3.get(alpha3.upper())
        if alpha2:
            return self._by_alpha2.get(alpha2)
        return None

    def lookup_numeric(self, numeric: str) -> CountryRecord | None:
        """
        Look up country by ISO 3166-1 numeric code.
        
        Args:
            numeric: Three-digit numeric code.
            
        Returns:
            CountryRecord if found, None otherwise.
        """
        alpha2 = self._by_numeric.get(numeric)
        if alpha2:
            return self._by_alpha2.get(alpha2)
        return None

    def is_valid(self, code: str) -> bool:
        """
        Check if a country code is valid.
        
        Accepts alpha-2, alpha-3, or numeric codes.
        
        Args:
            code: Country code to validate.
            
        Returns:
            True if valid, False otherwise.
        """
        code = code.upper()
        if len(code) == 2:
            return code in self._by_alpha2
        elif len(code) == 3:
            if code.isdigit():
                return code in self._by_numeric
            return code in self._by_alpha3
        return False

    def normalize_to_alpha2(self, code: str) -> str | None:
        """
        Normalize any country code to alpha-2.
        
        Args:
            code: Alpha-2, alpha-3, or numeric code.
            
        Returns:
            Alpha-2 code if valid, None otherwise.
        """
        code = code.upper()
        if len(code) == 2 and code in self._by_alpha2:
            return code
        elif len(code) == 3:
            if code.isdigit():
                return self._by_numeric.get(code)
            return self._by_alpha3.get(code)
        return None

    def get_by_region(self, region: str) -> list[CountryRecord]:
        """
        Get all countries in a geographic region.
        
        Args:
            region: Region name (e.g., "Americas", "Europe", "Asia").
            
        Returns:
            List of CountryRecord objects in the region.
        """
        alpha2s = self._by_region.get(region, [])
        return [self._by_alpha2[a2] for a2 in alpha2s]

    def get_regions(self) -> set[str]:
        """Get set of all region names."""
        return set(self._by_region.keys())

    def search_by_name(self, query: str) -> list[CountryRecord]:
        """
        Search countries by name (case-insensitive substring match).
        
        Args:
            query: Search string.
            
        Returns:
            List of matching CountryRecord objects.
        """
        query = query.lower()
        results = []
        for rec in self._by_alpha2.values():
            if query in rec.name.lower() or (rec.official_name and query in rec.official_name.lower()):
                results.append(rec)
        return results

    def get_timezones_for_country(self, alpha2: str) -> tuple[str, ...]:
        """
        Get IANA timezones for a country.
        
        Args:
            alpha2: Two-letter country code.
            
        Returns:
            Tuple of timezone strings, empty if not found.
        """
        rec = self.lookup(alpha2)
        return rec.timezones if rec else ()

    def get_currencies_for_country(self, alpha2: str) -> tuple[str, ...]:
        """
        Get currency codes for a country.
        
        Args:
            alpha2: Two-letter country code.
            
        Returns:
            Tuple of ISO 4217 currency codes, empty if not found.
        """
        rec = self.lookup(alpha2)
        return rec.currencies if rec else ()


# =============================================================================
# Source: ISO 3166 Fetcher
# =============================================================================


class ISO3166Source:
    """
    Bronze/Silver layer: Fetches and parses ISO 3166 country data.
    
    Uses REST Countries API as primary source with GitHub fallback.
    
    Example:
        >>> source = ISO3166Source()
        >>> snapshot, records = await source.fetch()
        >>> print(f"Fetched {len(records)} countries")
    """

    def __init__(
        self,
        primary_url: str = REST_COUNTRIES_URL,
        fallback_url: str = GITHUB_ISO3166_URL,
        timeout: int = 30,
    ) -> None:
        self.primary_url = primary_url
        self.fallback_url = fallback_url
        self.timeout = timeout

    async def fetch(
        self,
        store_raw: bool = False,
    ) -> tuple[CountrySnapshot, list[CountryRecord]]:
        """
        Fetch and parse ISO 3166 country data.
        
        Tries primary URL first, falls back to GitHub mirror on failure.
        
        Args:
            store_raw: Whether to store raw content in snapshot.
            
        Returns:
            Tuple of (CountrySnapshot, list of CountryRecord).
        """
        # Try primary source
        try:
            content, source_url = self._download(self.primary_url)
            records = self._parse_rest_countries(content)
        except Exception as e:
            logger.warning(f"Primary source failed: {e}, trying fallback")
            content, source_url = self._download(self.fallback_url)
            records = self._parse_github_iso3166(content)

        snapshot = CountrySnapshot.from_response(
            content=content,
            source_url=source_url,
            record_count=len(records),
            store_content=store_raw,
        )

        logger.info(f"Fetched {len(records)} countries from {source_url}")
        return snapshot, records

    def _download(self, url: str) -> tuple[bytes, str]:
        """Download content from URL with SSL fallback."""
        import ssl

        request = urllib.request.Request(
            url,
            headers={"User-Agent": USER_AGENT},
        )

        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return response.read(), url
        except ssl.SSLCertVerificationError:
            # Try with unverified context (for corporate firewalls)
            logger.warning(f"SSL verification failed for {url}, retrying without verification")
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            with urllib.request.urlopen(request, timeout=self.timeout, context=context) as response:
                return response.read(), url

    def _parse_rest_countries(self, content: bytes) -> list[CountryRecord]:
        """Parse REST Countries API response."""
        data = json.loads(content.decode("utf-8"))
        records = []

        for item in data:
            try:
                # Extract currencies
                currencies = tuple(item.get("currencies", {}).keys())

                # Extract languages
                languages = tuple(item.get("languages", {}).keys())

                # Extract timezones
                timezones = tuple(item.get("timezones", []))

                # Extract capital (can be a list)
                capitals = item.get("capital", [])
                capital = capitals[0] if capitals else None

                record = CountryRecord(
                    alpha2=item.get("cca2", ""),
                    alpha3=item.get("cca3"),
                    numeric=item.get("ccn3"),
                    name=item.get("name", {}).get("common", ""),
                    official_name=item.get("name", {}).get("official"),
                    region=item.get("region"),
                    subregion=item.get("subregion"),
                    capital=capital,
                    currencies=currencies,
                    languages=languages,
                    timezones=timezones,
                    flag_emoji=item.get("flag"),
                    independent=item.get("independent"),
                    status=item.get("status", "officially-assigned"),
                )
                records.append(record)
            except Exception as e:
                logger.warning(f"Failed to parse country: {e}")
                continue

        return records

    def _parse_github_iso3166(self, content: bytes) -> list[CountryRecord]:
        """Parse GitHub ISO 3166 JSON format."""
        data = json.loads(content.decode("utf-8"))
        records = []

        for item in data:
            try:
                record = CountryRecord(
                    alpha2=item.get("alpha-2", ""),
                    alpha3=item.get("alpha-3"),
                    numeric=item.get("country-code"),
                    name=item.get("name", ""),
                    region=item.get("region"),
                    subregion=item.get("sub-region"),
                )
                records.append(record)
            except Exception as e:
                logger.warning(f"Failed to parse country: {e}")
                continue

        return records


# =============================================================================
# Convenience Functions
# =============================================================================

# Module-level registry singleton (lazy-loaded)
_default_registry: CountryRegistry | None = None


async def get_country_registry() -> CountryRegistry:
    """
    Get the default country registry (lazy-loaded singleton).
    
    Returns:
        Loaded CountryRegistry instance.
    """
    global _default_registry
    if _default_registry is None:
        _default_registry = CountryRegistry()
        await _default_registry.load_from_source()
    return _default_registry


def is_valid_country_code(code: str, registry: CountryRegistry | None = None) -> bool:
    """
    Validate a country code (requires pre-loaded registry).
    
    Args:
        code: Country code to validate.
        registry: Optional registry instance.
        
    Returns:
        True if valid, False otherwise.
    """
    if registry is None:
        if _default_registry is None:
            raise RuntimeError("Registry not loaded. Call get_country_registry() first.")
        registry = _default_registry
    return registry.is_valid(code)
