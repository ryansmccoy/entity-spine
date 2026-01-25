"""
EntitySpine Symbology Sources.

STDLIB ONLY - NO PYDANTIC.

Bronze/Silver/Gold data architecture for authoritative reference data.

Sources:
- SECTickerSource: SEC company_tickers.json (US public companies)
- ISO10383Source: ISO 10383 MIC (Market Identifier Codes) - 2800+ exchanges
- ISO3166Source: ISO 3166 Country Codes - 250 countries
- ISO4217Source: ISO 4217 Currency Codes - 180 currencies
- MICRegistry: Gold-layer MIC lookup registry
- CountryRegistry: Gold-layer country lookup registry
- CurrencyRegistry: Gold-layer currency lookup registry
- GLEIFSource: GLEIF LEI Golden Copy (~2.5M legal entities)
- GLEIFISINLEISource: GLEIF ISIN-to-LEI mappings (~8M)
- GLEIFBICLEISource: GLEIF BIC-to-LEI mappings (~40K)
- GLEIFMICLEISource: GLEIF MIC-to-LEI mappings

Data Architecture:
- Bronze: Raw immutable snapshots with provenance
- Silver: Normalized records with change tracking
- Gold: Fast lookup registries for application use

Example:
    >>> from entityspine.sources import (
    ...     SECTickerSource,
    ...     ISO10383Source, MICRegistry,
    ...     ISO3166Source, CountryRegistry,
    ...     ISO4217Source, CurrencyRegistry,
    ...     GLEIFSource, LEIRegistry,
    ... )
    >>>
    >>> # SEC tickers
    >>> sec = SECTickerSource()
    >>> companies = await sec.fetch()
    >>>
    >>> # MIC registry (exchanges)
    >>> mic_registry = MICRegistry()
    >>> await mic_registry.load_from_source()
    >>> nyse = mic_registry.lookup("XNYS")
    >>> print(f"NYSE: {nyse.name}")
    >>>
    >>> # Country registry
    >>> country_registry = CountryRegistry()
    >>> await country_registry.load_from_source()
    >>> us = country_registry.lookup("US")
    >>> print(f"{us.name} ({us.alpha3})")  # United States (USA)
    >>>
    >>> # Currency registry
    >>> currency_registry = CurrencyRegistry()
    >>> await currency_registry.load_from_source()
    >>> usd = currency_registry.lookup("USD")
    >>> print(f"{usd.name} ({usd.symbol})")  # US Dollar ($)
    >>>
    >>> # LEI registry (legal entities)
    >>> lei_registry = LEIRegistry()
    >>> await lei_registry.load_from_source(limit=10000)
    >>> nvidia = lei_registry.search("NVIDIA")[0]
    >>> print(f"NVIDIA: {nvidia.legal_name}")
"""

from entityspine.sources.sec import (
    SECTickerSource,
    SECTickerSnapshot,
    SEC_EXCHANGE_TO_MIC,
    get_mic_for_exchange,
)

# Base utilities (for creating new sources)
from entityspine.sources.base import (
    BaseSnapshot,
    compute_content_hash,
    decode_content,
    download_url,
    generate_snapshot_id,
    parse_date_flexible,
    parse_datetime_flexible,
    get_csv_field,
    normalize_csv_headers,
)

# ISO 10383 MIC (Market Identifier Codes)
from entityspine.sources.iso10383 import (
    ISO10383Source,
    MICRegistry,
    MICRecord,
    MICSnapshot,
    MICChange,
    diff_mic_records,
    fetch_mic_list,
    lookup_mic,
)

# ISO 3166 Country Codes
from entityspine.sources.iso3166 import (
    ISO3166Source,
    CountryRegistry,
    CountryRecord,
    CountrySnapshot,
    get_country_registry,
    is_valid_country_code,
)

# ISO 4217 Currency Codes
from entityspine.sources.iso4217 import (
    ISO4217Source,
    CurrencyRegistry,
    CurrencyRecord,
    CurrencySnapshot,
    get_currency_registry,
    is_valid_currency_code,
    get_currency_decimals,
    CURRENCY_SYMBOLS,
)

# GLEIF MIC-to-LEI relationship
from entityspine.sources.gleif_mic_lei import (
    GLEIFMICLEISource,
    MICLEIMapping,
    MICLEISnapshot,
    fetch_mic_lei_mappings,
    get_lei_for_mic,
)

# GLEIF LEI (Legal Entity Identifiers)
from entityspine.sources.gleif import (
    GLEIFSource,
    GLEIFISINLEISource,
    GLEIFBICLEISource,
    LEIRegistry,
    LEIRecord,
    LEISnapshot,
    LEIChange,
    ISINLEIMapping,
    ISINLEISnapshot,
    BICLEIMapping,
    BICLEISnapshot,
    lookup_lei,
    validate_lei,
)

__all__ = [
    # Base utilities
    "BaseSnapshot",
    "compute_content_hash",
    "decode_content",
    "download_url",
    "generate_snapshot_id",
    "parse_date_flexible",
    "parse_datetime_flexible",
    "get_csv_field",
    "normalize_csv_headers",
    
    # SEC
    "SECTickerSource",
    "SECTickerSnapshot",
    "SEC_EXCHANGE_TO_MIC",
    "get_mic_for_exchange",
    
    # ISO 10383 MIC
    "ISO10383Source",
    "MICRegistry",
    "MICRecord",
    "MICSnapshot",
    "MICChange",
    "diff_mic_records",
    "fetch_mic_list",
    "lookup_mic",
    
    # ISO 3166 Countries
    "ISO3166Source",
    "CountryRegistry",
    "CountryRecord",
    "CountrySnapshot",
    "get_country_registry",
    "is_valid_country_code",
    
    # ISO 4217 Currencies
    "ISO4217Source",
    "CurrencyRegistry",
    "CurrencyRecord",
    "CurrencySnapshot",
    "get_currency_registry",
    "is_valid_currency_code",
    "get_currency_decimals",
    "CURRENCY_SYMBOLS",
    
    # GLEIF MIC-LEI
    "GLEIFMICLEISource",
    "MICLEIMapping",
    "MICLEISnapshot",
    "fetch_mic_lei_mappings",
    "get_lei_for_mic",
    
    # GLEIF LEI
    "GLEIFSource",
    "GLEIFISINLEISource",
    "GLEIFBICLEISource",
    "LEIRegistry",
    "LEIRecord",
    "LEISnapshot",
    "LEIChange",
    "ISINLEIMapping",
    "ISINLEISnapshot",
    "BICLEIMapping",
    "BICLEISnapshot",
    "lookup_lei",
    "validate_lei",
]
