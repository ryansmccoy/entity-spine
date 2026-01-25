"""
Reference data for EntitySpine domain models.

STDLIB ONLY - NO PYDANTIC.

This package contains curated, human-maintained reference data for market
infrastructure. This is the "Gold" layer - enriched, validated, ready-to-use.

Architecture:
    reference_data/ (this package) = CURATED GOLD LAYER
    - Static, human-maintained data
    - High-quality metadata
    - Ready for UI, analytics, validation
    
    sources/ = BRONZE/SILVER INGESTION
    - Live downloads from ISO 10383, GLEIF
    - Parsing and normalization
    - Change tracking
    
Modules:
    markets.py     - Exchange and clearinghouse reference data (legacy + ExchangeRef)
    venues.py      - VenueRef dataclass and curated venue registries
    vendorcodes.py - Vendor code mappings (Bloomberg, Reuters, FactSet, IBKR)
    assetclasses.py - Asset class metadata registry

For ISO 10383 bulk MIC data and live downloads, use:
    from entityspine.sources.iso10383 import ISO10383Source, MICRegistry, MICRecord
    
For GLEIF LEI data, use:
    from entityspine.sources.gleif import GLEIFSource, LEIRegistry
    from entityspine.sources.gleif_mic_lei import GLEIFMICLEISource

Version History:
    v2.3.1 - Initial reference_data package
    v2.3.2 - Added ExchangeRef, ClearinghouseRef with provenance
    v2.3.2 - Added VenueRef generalization for all venue types
    v2.3.2 - Added VenueKind and MicSource enums
    v2.3.2 - Added vendor code mappings and asset class metadata
    v2.3.2 - Aligned with project conventions (no underscores in filenames)
"""

# -----------------------------------------------------------------------------
# Core market reference data (markets.py)
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# Enums from enums/markets.py (re-exported for convenience)
# -----------------------------------------------------------------------------
from entityspine.domain.enums.markets import (
    MicSource,
    VenueKind,
)

# -----------------------------------------------------------------------------
# Asset class metadata (assetclasses.py)
# -----------------------------------------------------------------------------
from entityspine.domain.reference_data.assetclasses import (
    ASSET_CLASS_INFO,
    AssetClassInfo,
    get_asset_class_description,
    get_asset_class_info,
    get_typical_venues_for_asset_class,
)
from entityspine.domain.reference_data.markets import (
    # Helpers
    ALL_KNOWN_MICS,
    AMERICAS_EXCHANGES,
    APAC_EXCHANGES,
    # Vendor mappings (legacy)
    BLOOMBERG_FEED_SOURCES,
    # Global exchanges
    EUROPEAN_EXCHANGES,
    FACTSET_EXCHANGE_CODES,
    GLOBAL_CLEARINGHOUSES,
    MENA_EXCHANGES,
    THOMSON_EXCHANGE_CODES,
    # Clearinghouses
    US_CLEARINGHOUSES,
    # US exchanges
    US_EQUITY_EXCHANGES,
    US_FUTURES_EXCHANGES,
    US_OPTIONS_EXCHANGES,
    US_OTC_MARKETS,
    ClearinghouseInfo,
    ClearinghouseRef,
    ExchangeInfo,
    # Typed reference classes (v2.3.2)
    ExchangeRef,
    get_all_exchange_refs,
    get_all_exchanges,
    lookup_exchange_by_mic,
    lookup_exchange_ref,
)

# -----------------------------------------------------------------------------
# Vendor code mappings (vendorcodes.py)
# -----------------------------------------------------------------------------
from entityspine.domain.reference_data.vendorcodes import (
    # Vendor-specific mapping tables
    BLOOMBERG_VENUE_CODES,
    FACTSET_VENUE_CODES,
    IBKR_VENUE_CODES,
    REUTERS_VENUE_CODES,
    VendorNamespace,
    VendorVenueCodeRef,
    find_conflicting_mappings,
    get_vendor_code_ref,
    # Lookup helpers
    lookup_mic_by_vendor_code,
    lookup_vendor_codes_for_mic,
)

# -----------------------------------------------------------------------------
# Curated major venues (venues.py)
# -----------------------------------------------------------------------------
from entityspine.domain.reference_data.venues import (
    # Aggregate registry
    ALL_MAJOR_VENUES,
    MAJOR_CLEARINGHOUSES,
    MAJOR_CRYPTO_VENUES,
    MAJOR_DEPOSITORIES_CSDS,
    # Curated venue registries by asset class
    MAJOR_EQUITY_VENUES,
    MAJOR_FUTURES_VENUES,
    MAJOR_FX_VENUES,
    MAJOR_INDEX_PROVIDERS,
    MAJOR_OPTIONS_VENUES,
    MAJOR_RATES_CREDIT_VENUES,
    MAJOR_SWAPS_SEFS,
    MAJOR_TRADE_REPORTING,
    VenueRef,
    get_major_venues,
    get_venues_by_asset_class,
    get_venues_by_kind,
    # Lookup helpers
    lookup_major_venue,
)

# =============================================================================
# Public API
# =============================================================================

__all__ = [
    # -------------------------------------------------------------------------
    # Enums (from enums/markets.py)
    # -------------------------------------------------------------------------
    "VenueKind",
    "MicSource",
    # -------------------------------------------------------------------------
    # Core reference classes (markets.py)
    # -------------------------------------------------------------------------
    "ExchangeRef",
    "ClearinghouseRef",
    "ExchangeInfo",
    "ClearinghouseInfo",
    # US exchanges
    "US_EQUITY_EXCHANGES",
    "US_OPTIONS_EXCHANGES",
    "US_FUTURES_EXCHANGES",
    "US_OTC_MARKETS",
    # Global exchanges
    "EUROPEAN_EXCHANGES",
    "APAC_EXCHANGES",
    "AMERICAS_EXCHANGES",
    "MENA_EXCHANGES",
    # Clearinghouses
    "US_CLEARINGHOUSES",
    "GLOBAL_CLEARINGHOUSES",
    # Vendor mappings (legacy)
    "BLOOMBERG_FEED_SOURCES",
    "THOMSON_EXCHANGE_CODES",
    "FACTSET_EXCHANGE_CODES",
    # Helpers
    "ALL_KNOWN_MICS",
    "lookup_exchange_by_mic",
    "lookup_exchange_ref",
    "get_all_exchanges",
    "get_all_exchange_refs",
    # -------------------------------------------------------------------------
    # Asset class metadata (assetclasses.py)
    # -------------------------------------------------------------------------
    "AssetClassInfo",
    "ASSET_CLASS_INFO",
    "get_asset_class_info",
    "get_asset_class_description",
    "get_typical_venues_for_asset_class",
    # -------------------------------------------------------------------------
    # Curated venues (venues.py)
    # -------------------------------------------------------------------------
    "VenueRef",
    "MAJOR_EQUITY_VENUES",
    "MAJOR_OPTIONS_VENUES",
    "MAJOR_FUTURES_VENUES",
    "MAJOR_FX_VENUES",
    "MAJOR_RATES_CREDIT_VENUES",
    "MAJOR_SWAPS_SEFS",
    "MAJOR_CRYPTO_VENUES",
    "MAJOR_INDEX_PROVIDERS",
    "MAJOR_TRADE_REPORTING",
    "MAJOR_CLEARINGHOUSES",
    "MAJOR_DEPOSITORIES_CSDS",
    "ALL_MAJOR_VENUES",
    "lookup_major_venue",
    "get_major_venues",
    "get_venues_by_kind",
    "get_venues_by_asset_class",
    # -------------------------------------------------------------------------
    # Vendor code mappings (vendorcodes.py)
    # -------------------------------------------------------------------------
    "VendorNamespace",
    "VendorVenueCodeRef",
    "BLOOMBERG_VENUE_CODES",
    "REUTERS_VENUE_CODES",
    "FACTSET_VENUE_CODES",
    "IBKR_VENUE_CODES",
    "lookup_mic_by_vendor_code",
    "lookup_vendor_codes_for_mic",
    "get_vendor_code_ref",
    "find_conflicting_mappings",
]
