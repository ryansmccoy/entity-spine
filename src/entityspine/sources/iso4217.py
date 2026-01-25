"""
ISO 4217 Currency Code Source.

STDLIB ONLY - NO PYDANTIC.

Downloads and manages ISO 4217 currency codes for validation and enrichment.

This implements a Bronze/Silver/Gold data architecture:
- Bronze: Raw XML/JSON snapshots stored immutably
- Silver: Normalized currency records with change tracking
- Gold: Domain-ready registry with lookup APIs

Data Sources:
- Primary: https://www.six-group.com/dam/download/financial-information/data-center/iso-currrency/lists/list-one.xml
  (Official ISO 4217 Maintenance Agency - SIX Group)
- Fallback: GitHub mirrors of currency data

Standards:
- ISO 4217 alpha-3: Three-letter codes (USD, EUR, GBP)
- ISO 4217 numeric: Three-digit codes (840, 978, 826)
- Minor units: Decimal places (USD=2, JPY=0, BHD=3)

Update Cadence:
- ISO updates ~4 times per year (quarterly amendments)
- Changes include new currencies, withdrawals, name changes

Currency Types:
- National currencies (USD, EUR, JPY)
- Supranational currencies (XDR - SDR)
- Precious metals (XAU - Gold, XAG - Silver)
- Testing codes (XTS)
- No currency (XXX)

Example:
    >>> from entityspine.sources import ISO4217Source, CurrencyRegistry
    >>>
    >>> source = ISO4217Source()
    >>> records = await source.fetch()
    >>> print(f"Fetched {len(records)} currencies")
    >>>
    >>> registry = CurrencyRegistry()
    >>> await registry.load_from_source()
    >>> usd = registry.lookup("USD")
    >>> print(f"{usd.name} ({usd.symbol}) - {usd.minor_unit} decimals")

v1.0.0 Initial implementation.
"""

from __future__ import annotations

import hashlib
import logging
import urllib.request
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date, datetime

from entityspine.domain.timestamps import utc_now

logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

# Official SIX Group ISO 4217 XML (Maintenance Agency)
SIX_ISO4217_URL = "https://www.six-group.com/dam/download/financial-information/data-center/iso-currrency/lists/list-one.xml"

# GitHub mirror (fallback) - datahub.io currency codes
GITHUB_ISO4217_URL = "https://raw.githubusercontent.com/datasets/currency-codes/master/data/codes-all.csv"

# Alternative fallback - Open Exchange Rates currencies.json
OER_CURRENCIES_URL = "https://openexchangerates.org/api/currencies.json"

# User agent for requests
USER_AGENT = "EntitySpine/1.0 (ISO 4217 Currency Data)"

# XML namespaces (SIX uses default namespace)
ISO4217_NS = {"ns": "urn:iso:std:iso:4217"}


# =============================================================================
# Common Currency Symbols (not in ISO standard)
# =============================================================================

CURRENCY_SYMBOLS: dict[str, str] = {
    "USD": "$",
    "EUR": "€",
    "GBP": "£",
    "JPY": "¥",
    "CNY": "¥",
    "CHF": "Fr.",
    "CAD": "C$",
    "AUD": "A$",
    "NZD": "NZ$",
    "HKD": "HK$",
    "SGD": "S$",
    "SEK": "kr",
    "NOK": "kr",
    "DKK": "kr",
    "INR": "₹",
    "RUB": "₽",
    "BRL": "R$",
    "ZAR": "R",
    "KRW": "₩",
    "MXN": "Mex$",
    "THB": "฿",
    "TRY": "₺",
    "PLN": "zł",
    "ILS": "₪",
    "AED": "د.إ",
    "SAR": "﷼",
    "PHP": "₱",
    "CZK": "Kč",
    "IDR": "Rp",
    "MYR": "RM",
    "HUF": "Ft",
    "CLP": "$",
    "TWD": "NT$",
    "ARS": "$",
    "COP": "$",
    "PEN": "S/",
    "VND": "₫",
    "UAH": "₴",
    "EGP": "E£",
    "PKR": "₨",
    "NGN": "₦",
    "BDT": "৳",
    "RON": "lei",
    "KES": "KSh",
    "QAR": "﷼",
    "KWD": "د.ك",
    "BHD": ".د.ب",
    "OMR": "﷼",
    # Precious metals
    "XAU": "oz Au",
    "XAG": "oz Ag",
    "XPT": "oz Pt",
    "XPD": "oz Pd",
    # Special
    "XDR": "SDR",
    "BTC": "₿",
    "ETH": "Ξ",
}


# =============================================================================
# Bronze Layer: Raw Snapshot
# =============================================================================


@dataclass(frozen=True, slots=True)
class CurrencySnapshot:
    """
    Bronze layer: Immutable raw snapshot of ISO 4217 data.
    
    Stores the raw downloaded content with metadata for provenance tracking.
    
    Attributes:
        snapshot_id: Unique identifier for this snapshot.
        source_url: URL the data was fetched from.
        format: File format (xml, csv, json).
        content_hash: SHA-256 hash of content for deduplication.
        content_size: Size in bytes.
        record_count: Number of currency records in snapshot.
        published_date: ISO publication date if available.
        captured_at: When snapshot was captured.
        raw_content: The raw content (optional, for Bronze storage).
    """
    snapshot_id: str
    source_url: str
    format: str
    content_hash: str
    content_size: int
    record_count: int
    captured_at: datetime
    published_date: date | None = None
    raw_content: str | None = None

    @classmethod
    def from_response(
        cls,
        content: bytes,
        source_url: str,
        format: str,
        record_count: int,
        published_date: date | None = None,
        store_content: bool = False,
    ) -> CurrencySnapshot:
        """Create snapshot from HTTP response content."""
        content_str = content.decode("utf-8")
        content_hash = hashlib.sha256(content).hexdigest()
        captured_at = utc_now()
        snapshot_id = f"iso4217_{captured_at.strftime('%Y%m%d_%H%M%S')}_{content_hash[:8]}"

        return cls(
            snapshot_id=snapshot_id,
            source_url=source_url,
            format=format,
            content_hash=content_hash,
            content_size=len(content),
            record_count=record_count,
            published_date=published_date,
            captured_at=captured_at,
            raw_content=content_str if store_content else None,
        )


# =============================================================================
# Silver Layer: Normalized Record
# =============================================================================


@dataclass(frozen=True, slots=True)
class CurrencyRecord:
    """
    Silver layer: Normalized ISO 4217 currency record.
    
    Represents a single currency with all standard identifiers and metadata.
    
    Attributes:
        alpha3: ISO 4217 alpha-3 code (e.g., "USD").
        numeric: ISO 4217 numeric code (e.g., "840").
        name: Currency name (e.g., "US Dollar").
        minor_unit: Number of decimal places (e.g., 2 for USD, 0 for JPY).
        country_codes: Countries using this currency (alpha-2 codes).
        symbol: Common symbol (e.g., "$") - not in ISO standard.
        is_fund: Whether this is a fund code (e.g., USN, USS).
        is_precious_metal: Whether this is a precious metal (XAU, XAG, etc.).
        is_supranational: Whether this is supranational (XDR, XBA, etc.).
        is_active: Whether currency is currently active.
        withdrawal_date: Date currency was withdrawn (if inactive).
    """
    # Core identifiers
    alpha3: str
    numeric: str | None = None
    name: str = ""

    # Numeric properties
    minor_unit: int | None = None  # None means "N.A." in ISO

    # Countries using this currency
    country_codes: tuple[str, ...] = ()

    # Display (not from ISO)
    symbol: str | None = None

    # Classification
    is_fund: bool = False
    is_precious_metal: bool = False
    is_supranational: bool = False
    is_active: bool = True

    # Lifecycle
    withdrawal_date: date | None = None

    def __post_init__(self) -> None:
        """Validate required fields."""
        if not self.alpha3 or len(self.alpha3) != 3:
            raise ValueError(f"Invalid alpha3 code: {self.alpha3}")

    @property
    def display_symbol(self) -> str:
        """Get display symbol, falling back to alpha3 code."""
        return self.symbol or self.alpha3


# =============================================================================
# Gold Layer: Currency Registry
# =============================================================================


class CurrencyRegistry:
    """
    Gold layer: Fast lookup registry for currency codes.
    
    Provides O(1) lookup by alpha-3 or numeric code.
    Supports validation, enrichment, and filtering.
    
    Example:
        >>> registry = CurrencyRegistry()
        >>> await registry.load_from_source()
        >>>
        >>> # Lookup by alpha-3
        >>> usd = registry.lookup("USD")
        >>> print(usd.name)  # "US Dollar"
        >>>
        >>> # Lookup by numeric
        >>> eur = registry.lookup_numeric("978")
        >>> print(eur.alpha3)  # "EUR"
        >>>
        >>> # Get all active currencies
        >>> active = registry.get_active_currencies()
    """

    def __init__(self) -> None:
        self._by_alpha3: dict[str, CurrencyRecord] = {}
        self._by_numeric: dict[str, str] = {}  # numeric -> alpha3
        self._by_country: dict[str, list[str]] = {}  # country -> [alpha3]
        self._snapshot: CurrencySnapshot | None = None
        self._loaded_at: datetime | None = None

    @property
    def snapshot(self) -> CurrencySnapshot | None:
        """The Bronze snapshot this registry was loaded from."""
        return self._snapshot

    @property
    def loaded_at(self) -> datetime | None:
        """When this registry was loaded."""
        return self._loaded_at

    def __len__(self) -> int:
        return len(self._by_alpha3)

    def __contains__(self, alpha3: str) -> bool:
        return alpha3.upper() in self._by_alpha3

    def __iter__(self) -> Iterator[CurrencyRecord]:
        return iter(self._by_alpha3.values())

    async def load_from_source(
        self,
        source: ISO4217Source | None = None,
    ) -> CurrencySnapshot:
        """
        Load registry from ISO 4217 source.
        
        Args:
            source: Optional source instance. Creates default if None.
            
        Returns:
            The Bronze snapshot that was loaded.
        """
        if source is None:
            source = ISO4217Source()

        snapshot, records = await source.fetch()
        self._load_records(records)
        self._snapshot = snapshot
        self._loaded_at = utc_now()

        logger.info(
            f"Loaded {len(self)} currencies from {snapshot.source_url}"
        )
        return snapshot

    def load_from_records(self, records: list[CurrencyRecord]) -> None:
        """Load registry from pre-parsed records."""
        self._load_records(records)
        self._loaded_at = utc_now()

    def _load_records(self, records: list[CurrencyRecord]) -> None:
        """Internal method to index records."""
        self._by_alpha3.clear()
        self._by_numeric.clear()
        self._by_country.clear()

        for rec in records:
            alpha3 = rec.alpha3.upper()
            self._by_alpha3[alpha3] = rec

            if rec.numeric:
                self._by_numeric[rec.numeric] = alpha3

            for country in rec.country_codes:
                country_upper = country.upper()
                if country_upper not in self._by_country:
                    self._by_country[country_upper] = []
                self._by_country[country_upper].append(alpha3)

    def lookup(self, alpha3: str) -> CurrencyRecord | None:
        """
        Look up currency by ISO 4217 alpha-3 code.
        
        Args:
            alpha3: Three-letter currency code (case-insensitive).
            
        Returns:
            CurrencyRecord if found, None otherwise.
        """
        return self._by_alpha3.get(alpha3.upper())

    def get(self, alpha3: str) -> CurrencyRecord | None:
        """Alias for lookup() - provides consistent API across registries."""
        return self.lookup(alpha3)

    def lookup_numeric(self, numeric: str) -> CurrencyRecord | None:
        """
        Look up currency by ISO 4217 numeric code.
        
        Args:
            numeric: Three-digit numeric code.
            
        Returns:
            CurrencyRecord if found, None otherwise.
        """
        alpha3 = self._by_numeric.get(numeric)
        if alpha3:
            return self._by_alpha3.get(alpha3)
        return None

    def is_valid(self, code: str) -> bool:
        """
        Check if a currency code is valid.
        
        Accepts alpha-3 or numeric codes.
        
        Args:
            code: Currency code to validate.
            
        Returns:
            True if valid, False otherwise.
        """
        code = code.upper()
        if len(code) == 3:
            if code.isdigit():
                return code in self._by_numeric
            return code in self._by_alpha3
        return False

    def normalize_to_alpha3(self, code: str) -> str | None:
        """
        Normalize any currency code to alpha-3.
        
        Args:
            code: Alpha-3 or numeric code.
            
        Returns:
            Alpha-3 code if valid, None otherwise.
        """
        code = code.upper()
        if len(code) == 3:
            if code.isdigit():
                return self._by_numeric.get(code)
            if code in self._by_alpha3:
                return code
        return None

    def get_currencies_for_country(self, country_code: str) -> list[CurrencyRecord]:
        """
        Get currencies used by a country.
        
        Args:
            country_code: ISO 3166-1 alpha-2 country code.
            
        Returns:
            List of CurrencyRecord objects.
        """
        alpha3s = self._by_country.get(country_code.upper(), [])
        return [self._by_alpha3[a3] for a3 in alpha3s]

    def get_active_currencies(self) -> list[CurrencyRecord]:
        """Get all active (non-withdrawn) currencies."""
        return [rec for rec in self._by_alpha3.values() if rec.is_active]

    def get_precious_metals(self) -> list[CurrencyRecord]:
        """Get precious metal codes (XAU, XAG, XPT, XPD)."""
        return [rec for rec in self._by_alpha3.values() if rec.is_precious_metal]

    def get_fund_codes(self) -> list[CurrencyRecord]:
        """Get fund codes (USN, USS, etc.)."""
        return [rec for rec in self._by_alpha3.values() if rec.is_fund]

    def search_by_name(self, query: str) -> list[CurrencyRecord]:
        """
        Search currencies by name (case-insensitive substring match).
        
        Args:
            query: Search string.
            
        Returns:
            List of matching CurrencyRecord objects.
        """
        query = query.lower()
        return [
            rec for rec in self._by_alpha3.values()
            if query in rec.name.lower()
        ]

    def get_minor_unit(self, alpha3: str) -> int | None:
        """
        Get decimal places for a currency.
        
        Args:
            alpha3: Currency code.
            
        Returns:
            Number of decimal places, or None if not found or N.A.
        """
        rec = self.lookup(alpha3)
        return rec.minor_unit if rec else None

    def get_symbol(self, alpha3: str) -> str:
        """
        Get display symbol for a currency.
        
        Args:
            alpha3: Currency code.
            
        Returns:
            Symbol string, or alpha3 code if no symbol.
        """
        rec = self.lookup(alpha3)
        if rec:
            return rec.display_symbol
        return alpha3.upper()


# =============================================================================
# Source: ISO 4217 Fetcher
# =============================================================================


class ISO4217Source:
    """
    Bronze/Silver layer: Fetches and parses ISO 4217 currency data.
    
    Uses official SIX Group XML as primary source with GitHub CSV fallback.
    
    Example:
        >>> source = ISO4217Source()
        >>> snapshot, records = await source.fetch()
        >>> print(f"Fetched {len(records)} currencies")
    """

    def __init__(
        self,
        primary_url: str = SIX_ISO4217_URL,
        fallback_url: str = GITHUB_ISO4217_URL,
        timeout: int = 30,
    ) -> None:
        self.primary_url = primary_url
        self.fallback_url = fallback_url
        self.timeout = timeout

    async def fetch(
        self,
        store_raw: bool = False,
    ) -> tuple[CurrencySnapshot, list[CurrencyRecord]]:
        """
        Fetch and parse ISO 4217 currency data.
        
        Tries primary SIX XML first, falls back to GitHub CSV on failure.
        
        Args:
            store_raw: Whether to store raw content in snapshot.
            
        Returns:
            Tuple of (CurrencySnapshot, list of CurrencyRecord).
        """
        # Try primary source (SIX XML)
        try:
            content = self._download(self.primary_url)
            records, published_date = self._parse_six_xml(content)
            source_url = self.primary_url
            format_type = "xml"
        except Exception as e:
            logger.warning(f"Primary source failed: {e}, trying fallback")
            try:
                content = self._download(self.fallback_url)
                records = self._parse_github_csv(content)
                published_date = None
                source_url = self.fallback_url
                format_type = "csv"
            except Exception as e2:
                logger.error(f"Fallback also failed: {e2}")
                raise

        snapshot = CurrencySnapshot.from_response(
            content=content,
            source_url=source_url,
            format=format_type,
            record_count=len(records),
            published_date=published_date,
            store_content=store_raw,
        )

        logger.info(f"Fetched {len(records)} currencies from {source_url}")
        return snapshot, records

    def _download(self, url: str) -> bytes:
        """Download content from URL with SSL fallback."""
        import ssl

        request = urllib.request.Request(
            url,
            headers={"User-Agent": USER_AGENT},
        )

        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return response.read()
        except ssl.SSLCertVerificationError:
            # Try with unverified context (for corporate firewalls)
            logger.warning(f"SSL verification failed for {url}, retrying without verification")
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            with urllib.request.urlopen(request, timeout=self.timeout, context=context) as response:
                return response.read()

    def _parse_github_csv(self, content: bytes) -> list[CurrencyRecord]:
        """Parse GitHub datahub.io currency codes CSV format."""
        import csv
        import io

        text = content.decode("utf-8")
        reader = csv.DictReader(io.StringIO(text))
        records = []
        seen: set[str] = set()

        for row in reader:
            try:
                alpha3 = row.get("AlphabeticCode", "").strip()
                if not alpha3 or alpha3 in seen:
                    continue
                seen.add(alpha3)

                # Parse minor units
                minor_str = row.get("MinorUnit", "").strip()
                minor_unit = None
                if minor_str and minor_str.isdigit():
                    minor_unit = int(minor_str)

                # Classify special currencies
                is_precious_metal = alpha3 in ("XAU", "XAG", "XPT", "XPD")
                is_supranational = alpha3.startswith("X") and not is_precious_metal

                record = CurrencyRecord(
                    alpha3=alpha3,
                    numeric=row.get("NumericCode", "").strip() or None,
                    name=row.get("Currency", "").strip(),
                    minor_unit=minor_unit,
                    symbol=CURRENCY_SYMBOLS.get(alpha3),
                    is_precious_metal=is_precious_metal,
                    is_supranational=is_supranational,
                    is_active=True,
                )
                records.append(record)
            except Exception as e:
                logger.warning(f"Failed to parse currency row: {e}")
                continue

        return records

    def _parse_six_xml(self, content: bytes) -> tuple[list[CurrencyRecord], date | None]:
        """Parse SIX Group ISO 4217 XML format."""
        root = ET.fromstring(content)
        records = []
        published_date = None

        # Try to get publication date
        # Format: <Pblshd>2024-06-01</Pblshd>
        pblshd = root.find(".//Pblshd")
        if pblshd is not None and pblshd.text:
            try:
                published_date = date.fromisoformat(pblshd.text)
            except ValueError:
                pass

        # Parse currency entries
        # Structure: <CcyTbl><CcyNtry>...</CcyNtry></CcyTbl>
        for entry in root.findall(".//CcyNtry"):
            try:
                record = self._parse_currency_entry(entry)
                if record:
                    records.append(record)
            except Exception as e:
                logger.warning(f"Failed to parse currency entry: {e}")
                continue

        # Deduplicate by alpha3 (some currencies appear multiple times for different countries)
        # We want to merge country_codes
        merged = self._merge_by_alpha3(records)

        return merged, published_date

    def _parse_currency_entry(self, entry: ET.Element) -> CurrencyRecord | None:
        """Parse a single <CcyNtry> element."""
        # Get required alpha3 code
        ccy = entry.find("Ccy")
        if ccy is None or not ccy.text:
            return None  # Entry without currency code (some have only country)

        alpha3 = ccy.text.strip().upper()

        # Get country (if present)
        ctry = entry.find("CtryNm")
        country_name = ctry.text.strip() if ctry is not None and ctry.text else ""

        # Get currency name
        ccy_nm = entry.find("CcyNm")
        name = ccy_nm.text.strip() if ccy_nm is not None and ccy_nm.text else ""

        # Check for fund attribute: <CcyNm IsFund="true">
        is_fund = False
        if ccy_nm is not None:
            is_fund = ccy_nm.get("IsFund", "false").lower() == "true"

        # Get numeric code
        ccy_nbr = entry.find("CcyNbr")
        numeric = ccy_nbr.text.strip() if ccy_nbr is not None and ccy_nbr.text else None

        # Get minor unit (decimal places)
        ccy_mnr_unts = entry.find("CcyMnrUnts")
        minor_unit = None
        if ccy_mnr_unts is not None and ccy_mnr_unts.text:
            text = ccy_mnr_unts.text.strip()
            if text != "N.A.":
                try:
                    minor_unit = int(text)
                except ValueError:
                    pass

        # Classify special currencies
        is_precious_metal = alpha3 in ("XAU", "XAG", "XPT", "XPD")
        is_supranational = alpha3.startswith("X") and not is_precious_metal

        # Get symbol from our mapping
        symbol = CURRENCY_SYMBOLS.get(alpha3)

        return CurrencyRecord(
            alpha3=alpha3,
            numeric=numeric,
            name=name,
            minor_unit=minor_unit,
            country_codes=(),  # Will be merged later
            symbol=symbol,
            is_fund=is_fund,
            is_precious_metal=is_precious_metal,
            is_supranational=is_supranational,
            is_active=True,  # Active currencies in list-one.xml
        )

    def _merge_by_alpha3(self, records: list[CurrencyRecord]) -> list[CurrencyRecord]:
        """Merge records with same alpha3, combining country_codes."""
        merged: dict[str, CurrencyRecord] = {}
        countries: dict[str, set[str]] = {}

        for rec in records:
            if rec.alpha3 not in merged:
                merged[rec.alpha3] = rec
                countries[rec.alpha3] = set()
            # Note: country_codes will be empty at this point since XML
            # doesn't directly provide country codes, just country names

        return list(merged.values())


# =============================================================================
# Convenience Functions
# =============================================================================

# Module-level registry singleton (lazy-loaded)
_default_registry: CurrencyRegistry | None = None


async def get_currency_registry() -> CurrencyRegistry:
    """
    Get the default currency registry (lazy-loaded singleton).
    
    Returns:
        Loaded CurrencyRegistry instance.
    """
    global _default_registry
    if _default_registry is None:
        _default_registry = CurrencyRegistry()
        await _default_registry.load_from_source()
    return _default_registry


def is_valid_currency_code(code: str, registry: CurrencyRegistry | None = None) -> bool:
    """
    Validate a currency code (requires pre-loaded registry).
    
    Args:
        code: Currency code to validate.
        registry: Optional registry instance.
        
    Returns:
        True if valid, False otherwise.
    """
    if registry is None:
        if _default_registry is None:
            raise RuntimeError("Registry not loaded. Call get_currency_registry() first.")
        registry = _default_registry
    return registry.is_valid(code)


def get_currency_decimals(alpha3: str, registry: CurrencyRegistry | None = None) -> int:
    """
    Get decimal places for a currency (requires pre-loaded registry).
    
    Args:
        alpha3: Currency code.
        registry: Optional registry instance.
        
    Returns:
        Number of decimal places, defaults to 2 if unknown.
    """
    if registry is None:
        if _default_registry is None:
            # Return safe default
            return 2
        registry = _default_registry

    minor_unit = registry.get_minor_unit(alpha3)
    return minor_unit if minor_unit is not None else 2
