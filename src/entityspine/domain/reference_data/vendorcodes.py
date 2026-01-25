"""
Vendor Code Mappings for Market Infrastructure.

STDLIB ONLY - NO PYDANTIC.

Provides systematic mapping between vendor-specific codes and ISO MIC codes.

Vendors covered:
- Bloomberg (BBUID, feed sources)
- Thomson Reuters / Refinitiv (RIC exchange codes)
- FactSet (exchange codes)
- Interactive Brokers (exchange codes)

Architecture:
------------
This module provides:
1. VendorNamespace enum for vendor identification
2. VendorVenueCodeRef typed record for mappings
3. Curated mapping tables
4. Lookup helpers (bidirectional: vendor→MIC, MIC→vendor)
5. Disagreement handling for conflicting mappings

v2.3.2 - Initial version
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from entityspine.domain.timestamps import utc_now

# =============================================================================
# Vendor Namespace Enum
# =============================================================================


class VendorNamespace(str, Enum):
    """
    Vendor namespaces for market data codes.
    
    Each vendor has their own exchange/venue identification scheme.
    This enum provides a controlled vocabulary for vendor identification.
    """

    # Primary market data vendors
    BLOOMBERG = "bloomberg"           # Bloomberg BBUID/feed sources
    REUTERS = "reuters"               # Thomson Reuters / Refinitiv RIC codes
    REFINITIV = "refinitiv"           # Refinitiv (same as Reuters for most cases)
    FACTSET = "factset"               # FactSet entity/security exchange codes

    # Broker platforms
    INTERACTIVE_BROKERS = "ibkr"      # Interactive Brokers exchange codes
    SCHWAB = "schwab"                 # Charles Schwab
    FIDELITY = "fidelity"             # Fidelity

    # Other data vendors
    MORNINGSTAR = "morningstar"       # Morningstar
    SP_CAPITAL_IQ = "spglobal"        # S&P Global / Capital IQ
    QUANDL = "quandl"                 # Quandl (Nasdaq Data Link)

    # Regulatory / Standard
    ISO10383 = "iso10383"             # ISO MIC standard
    SEC = "sec"                       # SEC EDGAR codes
    FINRA = "finra"                   # FINRA codes

    # Internal
    INTERNAL = "internal"             # Internal/proprietary codes
    UNKNOWN = "unknown"


# =============================================================================
# Vendor Code Reference
# =============================================================================


@dataclass(frozen=True, slots=True)
class VendorVenueCodeRef:
    """
    A vendor-specific venue/exchange code mapping.
    
    Links vendor codes to ISO MIC codes with provenance and confidence.
    
    Attributes:
        vendor: VendorNamespace enum value.
        vendor_code: Vendor-specific code (e.g., "UN" for Bloomberg US).
        mic: ISO 10383 MIC code (if known).
        name: Venue name in vendor's nomenclature.
        
        # Mapping quality
        confidence: Confidence in mapping (0.0-1.0).
        is_exact_match: True if mapping is authoritative.
        notes: Additional context about mapping.
        
        # Provenance
        source: Where this mapping came from.
        source_url: Reference URL.
        captured_at: When captured.
        verified_at: When last verified.
    """

    vendor: VendorNamespace
    vendor_code: str

    mic: str | None = None
    name: str | None = None

    # Mapping quality
    confidence: float = 1.0
    is_exact_match: bool = True
    notes: str | None = None

    # Provenance
    source: str = "curated"
    source_url: str | None = None
    captured_at: datetime = field(default_factory=utc_now)
    verified_at: datetime | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "vendor": self.vendor.value,
            "vendor_code": self.vendor_code,
            "mic": self.mic,
            "name": self.name,
            "confidence": self.confidence,
            "is_exact_match": self.is_exact_match,
            "notes": self.notes,
            "source": self.source,
        }


# =============================================================================
# Bloomberg Mappings
# =============================================================================

BLOOMBERG_VENUE_CODES: dict[str, VendorVenueCodeRef] = {
    # US Equity
    "UN": VendorVenueCodeRef(
        vendor=VendorNamespace.BLOOMBERG, vendor_code="UN",
        mic="XNYS", name="NYSE Composite",
    ),
    "UA": VendorVenueCodeRef(
        vendor=VendorNamespace.BLOOMBERG, vendor_code="UA",
        mic="XASE", name="NYSE American (AMEX)",
    ),
    "UQ": VendorVenueCodeRef(
        vendor=VendorNamespace.BLOOMBERG, vendor_code="UQ",
        mic="XNAS", name="NASDAQ",
    ),
    "US": VendorVenueCodeRef(
        vendor=VendorNamespace.BLOOMBERG, vendor_code="US",
        mic="XNYS", name="NYSE Consolidated",
    ),
    "UP": VendorVenueCodeRef(
        vendor=VendorNamespace.BLOOMBERG, vendor_code="UP",
        mic="ARCX", name="NYSE Arca",
    ),
    "UF": VendorVenueCodeRef(
        vendor=VendorNamespace.BLOOMBERG, vendor_code="UF",
        mic="BATS", name="BATS/Cboe BZX",
    ),
    "UV": VendorVenueCodeRef(
        vendor=VendorNamespace.BLOOMBERG, vendor_code="UV",
        mic="IEXG", name="IEX",
    ),

    # US OTC
    "UU": VendorVenueCodeRef(
        vendor=VendorNamespace.BLOOMBERG, vendor_code="UU",
        mic="OTCM", name="OTC Markets",
    ),

    # Europe
    "LN": VendorVenueCodeRef(
        vendor=VendorNamespace.BLOOMBERG, vendor_code="LN",
        mic="XLON", name="London Stock Exchange",
    ),
    "FP": VendorVenueCodeRef(
        vendor=VendorNamespace.BLOOMBERG, vendor_code="FP",
        mic="XPAR", name="Euronext Paris",
    ),
    "NA": VendorVenueCodeRef(
        vendor=VendorNamespace.BLOOMBERG, vendor_code="NA",
        mic="XAMS", name="Euronext Amsterdam",
    ),
    "GY": VendorVenueCodeRef(
        vendor=VendorNamespace.BLOOMBERG, vendor_code="GY",
        mic="XETR", name="Xetra",
    ),
    "GR": VendorVenueCodeRef(
        vendor=VendorNamespace.BLOOMBERG, vendor_code="GR",
        mic="XFRA", name="Frankfurt Stock Exchange",
    ),
    "SW": VendorVenueCodeRef(
        vendor=VendorNamespace.BLOOMBERG, vendor_code="SW",
        mic="XSWX", name="SIX Swiss Exchange",
    ),
    "SM": VendorVenueCodeRef(
        vendor=VendorNamespace.BLOOMBERG, vendor_code="SM",
        mic="XMAD", name="Bolsa de Madrid",
    ),
    "IM": VendorVenueCodeRef(
        vendor=VendorNamespace.BLOOMBERG, vendor_code="IM",
        mic="XMIL", name="Borsa Italiana",
    ),

    # Asia-Pacific
    "JP": VendorVenueCodeRef(
        vendor=VendorNamespace.BLOOMBERG, vendor_code="JP",
        mic="XJPX", name="Tokyo Stock Exchange",
    ),
    "HK": VendorVenueCodeRef(
        vendor=VendorNamespace.BLOOMBERG, vendor_code="HK",
        mic="XHKG", name="Hong Kong Stock Exchange",
    ),
    "CH": VendorVenueCodeRef(
        vendor=VendorNamespace.BLOOMBERG, vendor_code="CH",
        mic="XSHG", name="Shanghai Stock Exchange",
    ),
    "CZ": VendorVenueCodeRef(
        vendor=VendorNamespace.BLOOMBERG, vendor_code="CZ",
        mic="XSHE", name="Shenzhen Stock Exchange",
    ),
    "AU": VendorVenueCodeRef(
        vendor=VendorNamespace.BLOOMBERG, vendor_code="AU",
        mic="XASX", name="Australian Securities Exchange",
    ),
    "KS": VendorVenueCodeRef(
        vendor=VendorNamespace.BLOOMBERG, vendor_code="KS",
        mic="XKRX", name="Korea Exchange",
    ),
    "SP": VendorVenueCodeRef(
        vendor=VendorNamespace.BLOOMBERG, vendor_code="SP",
        mic="XSES", name="Singapore Exchange",
    ),
    "IN": VendorVenueCodeRef(
        vendor=VendorNamespace.BLOOMBERG, vendor_code="IN",
        mic="XBOM", name="BSE India",
    ),

    # Canada
    "CN": VendorVenueCodeRef(
        vendor=VendorNamespace.BLOOMBERG, vendor_code="CN",
        mic="XTSE", name="Toronto Stock Exchange",
    ),
    "CV": VendorVenueCodeRef(
        vendor=VendorNamespace.BLOOMBERG, vendor_code="CV",
        mic="XTSX", name="TSX Venture Exchange",
    ),
}


# =============================================================================
# Thomson Reuters / Refinitiv Mappings
# =============================================================================

REUTERS_VENUE_CODES: dict[str, VendorVenueCodeRef] = {
    # US Equity
    ".N": VendorVenueCodeRef(
        vendor=VendorNamespace.REUTERS, vendor_code=".N",
        mic="XNYS", name="NYSE",
    ),
    ".A": VendorVenueCodeRef(
        vendor=VendorNamespace.REUTERS, vendor_code=".A",
        mic="XASE", name="NYSE American",
    ),
    ".O": VendorVenueCodeRef(
        vendor=VendorNamespace.REUTERS, vendor_code=".O",
        mic="XNAS", name="NASDAQ",
    ),
    ".OQ": VendorVenueCodeRef(
        vendor=VendorNamespace.REUTERS, vendor_code=".OQ",
        mic="XNGS", name="NASDAQ Global Select",
    ),
    ".PK": VendorVenueCodeRef(
        vendor=VendorNamespace.REUTERS, vendor_code=".PK",
        mic="OTCM", name="OTC Pink",
    ),
    ".Z": VendorVenueCodeRef(
        vendor=VendorNamespace.REUTERS, vendor_code=".Z",
        mic="BATS", name="BATS",
    ),

    # Europe
    ".L": VendorVenueCodeRef(
        vendor=VendorNamespace.REUTERS, vendor_code=".L",
        mic="XLON", name="London Stock Exchange",
    ),
    ".PA": VendorVenueCodeRef(
        vendor=VendorNamespace.REUTERS, vendor_code=".PA",
        mic="XPAR", name="Euronext Paris",
    ),
    ".AS": VendorVenueCodeRef(
        vendor=VendorNamespace.REUTERS, vendor_code=".AS",
        mic="XAMS", name="Euronext Amsterdam",
    ),
    ".DE": VendorVenueCodeRef(
        vendor=VendorNamespace.REUTERS, vendor_code=".DE",
        mic="XETR", name="Xetra",
    ),
    ".F": VendorVenueCodeRef(
        vendor=VendorNamespace.REUTERS, vendor_code=".F",
        mic="XFRA", name="Frankfurt",
    ),
    ".S": VendorVenueCodeRef(
        vendor=VendorNamespace.REUTERS, vendor_code=".S",
        mic="XSWX", name="SIX Swiss Exchange",
    ),
    ".MI": VendorVenueCodeRef(
        vendor=VendorNamespace.REUTERS, vendor_code=".MI",
        mic="XMIL", name="Borsa Italiana",
    ),

    # Asia-Pacific
    ".T": VendorVenueCodeRef(
        vendor=VendorNamespace.REUTERS, vendor_code=".T",
        mic="XJPX", name="Tokyo Stock Exchange",
    ),
    ".HK": VendorVenueCodeRef(
        vendor=VendorNamespace.REUTERS, vendor_code=".HK",
        mic="XHKG", name="Hong Kong Stock Exchange",
    ),
    ".SS": VendorVenueCodeRef(
        vendor=VendorNamespace.REUTERS, vendor_code=".SS",
        mic="XSHG", name="Shanghai Stock Exchange",
    ),
    ".SZ": VendorVenueCodeRef(
        vendor=VendorNamespace.REUTERS, vendor_code=".SZ",
        mic="XSHE", name="Shenzhen Stock Exchange",
    ),
    ".AX": VendorVenueCodeRef(
        vendor=VendorNamespace.REUTERS, vendor_code=".AX",
        mic="XASX", name="Australian Securities Exchange",
    ),
    ".KS": VendorVenueCodeRef(
        vendor=VendorNamespace.REUTERS, vendor_code=".KS",
        mic="XKRX", name="Korea Exchange",
    ),
    ".SI": VendorVenueCodeRef(
        vendor=VendorNamespace.REUTERS, vendor_code=".SI",
        mic="XSES", name="Singapore Exchange",
    ),

    # Canada
    ".TO": VendorVenueCodeRef(
        vendor=VendorNamespace.REUTERS, vendor_code=".TO",
        mic="XTSE", name="Toronto Stock Exchange",
    ),
    ".V": VendorVenueCodeRef(
        vendor=VendorNamespace.REUTERS, vendor_code=".V",
        mic="XTSX", name="TSX Venture",
    ),
}


# =============================================================================
# FactSet Mappings
# =============================================================================

FACTSET_VENUE_CODES: dict[str, VendorVenueCodeRef] = {
    # US
    "US": VendorVenueCodeRef(
        vendor=VendorNamespace.FACTSET, vendor_code="US",
        mic="XNYS", name="NYSE",
        notes="FactSet uses 'US' for consolidated US equities",
    ),
    "UQ": VendorVenueCodeRef(
        vendor=VendorNamespace.FACTSET, vendor_code="UQ",
        mic="XNAS", name="NASDAQ",
    ),
    "UA": VendorVenueCodeRef(
        vendor=VendorNamespace.FACTSET, vendor_code="UA",
        mic="XASE", name="NYSE American",
    ),
    "UP": VendorVenueCodeRef(
        vendor=VendorNamespace.FACTSET, vendor_code="UP",
        mic="ARCX", name="NYSE Arca",
    ),

    # Europe
    "LN": VendorVenueCodeRef(
        vendor=VendorNamespace.FACTSET, vendor_code="LN",
        mic="XLON", name="London Stock Exchange",
    ),
    "FP": VendorVenueCodeRef(
        vendor=VendorNamespace.FACTSET, vendor_code="FP",
        mic="XPAR", name="Euronext Paris",
    ),
    "NA": VendorVenueCodeRef(
        vendor=VendorNamespace.FACTSET, vendor_code="NA",
        mic="XAMS", name="Euronext Amsterdam",
    ),
    "GF": VendorVenueCodeRef(
        vendor=VendorNamespace.FACTSET, vendor_code="GF",
        mic="XFRA", name="Frankfurt",
    ),
    "GR": VendorVenueCodeRef(
        vendor=VendorNamespace.FACTSET, vendor_code="GR",
        mic="XETR", name="Xetra",
    ),
    "SW": VendorVenueCodeRef(
        vendor=VendorNamespace.FACTSET, vendor_code="SW",
        mic="XSWX", name="SIX Swiss",
    ),

    # Asia-Pacific
    "JP": VendorVenueCodeRef(
        vendor=VendorNamespace.FACTSET, vendor_code="JP",
        mic="XJPX", name="Tokyo",
    ),
    "HK": VendorVenueCodeRef(
        vendor=VendorNamespace.FACTSET, vendor_code="HK",
        mic="XHKG", name="Hong Kong",
    ),
    "CH": VendorVenueCodeRef(
        vendor=VendorNamespace.FACTSET, vendor_code="CH",
        mic="XSHG", name="Shanghai",
    ),
    "CZ": VendorVenueCodeRef(
        vendor=VendorNamespace.FACTSET, vendor_code="CZ",
        mic="XSHE", name="Shenzhen",
    ),
    "AU": VendorVenueCodeRef(
        vendor=VendorNamespace.FACTSET, vendor_code="AU",
        mic="XASX", name="ASX",
    ),

    # Canada
    "CN": VendorVenueCodeRef(
        vendor=VendorNamespace.FACTSET, vendor_code="CN",
        mic="XTSE", name="Toronto",
    ),
}


# =============================================================================
# Interactive Brokers Mappings
# =============================================================================

IBKR_VENUE_CODES: dict[str, VendorVenueCodeRef] = {
    # US
    "NYSE": VendorVenueCodeRef(
        vendor=VendorNamespace.INTERACTIVE_BROKERS, vendor_code="NYSE",
        mic="XNYS", name="New York Stock Exchange",
    ),
    "NASDAQ": VendorVenueCodeRef(
        vendor=VendorNamespace.INTERACTIVE_BROKERS, vendor_code="NASDAQ",
        mic="XNAS", name="NASDAQ",
    ),
    "AMEX": VendorVenueCodeRef(
        vendor=VendorNamespace.INTERACTIVE_BROKERS, vendor_code="AMEX",
        mic="XASE", name="NYSE American",
    ),
    "ARCA": VendorVenueCodeRef(
        vendor=VendorNamespace.INTERACTIVE_BROKERS, vendor_code="ARCA",
        mic="ARCX", name="NYSE Arca",
    ),
    "BATS": VendorVenueCodeRef(
        vendor=VendorNamespace.INTERACTIVE_BROKERS, vendor_code="BATS",
        mic="BATS", name="BATS/Cboe BZX",
    ),
    "IEX": VendorVenueCodeRef(
        vendor=VendorNamespace.INTERACTIVE_BROKERS, vendor_code="IEX",
        mic="IEXG", name="IEX",
    ),
    "PINK": VendorVenueCodeRef(
        vendor=VendorNamespace.INTERACTIVE_BROKERS, vendor_code="PINK",
        mic="OTCM", name="OTC Markets",
    ),

    # Options
    "CBOE": VendorVenueCodeRef(
        vendor=VendorNamespace.INTERACTIVE_BROKERS, vendor_code="CBOE",
        mic="XCBO", name="Cboe Options Exchange",
    ),
    "ISE": VendorVenueCodeRef(
        vendor=VendorNamespace.INTERACTIVE_BROKERS, vendor_code="ISE",
        mic="XISX", name="Nasdaq ISE",
    ),
    "PHLX": VendorVenueCodeRef(
        vendor=VendorNamespace.INTERACTIVE_BROKERS, vendor_code="PHLX",
        mic="XPHL", name="Nasdaq PHLX",
    ),

    # Futures
    "CME": VendorVenueCodeRef(
        vendor=VendorNamespace.INTERACTIVE_BROKERS, vendor_code="CME",
        mic="XCME", name="CME",
    ),
    "CBOT": VendorVenueCodeRef(
        vendor=VendorNamespace.INTERACTIVE_BROKERS, vendor_code="CBOT",
        mic="XCBT", name="CBOT",
    ),
    "NYMEX": VendorVenueCodeRef(
        vendor=VendorNamespace.INTERACTIVE_BROKERS, vendor_code="NYMEX",
        mic="XNYM", name="NYMEX",
    ),
    "COMEX": VendorVenueCodeRef(
        vendor=VendorNamespace.INTERACTIVE_BROKERS, vendor_code="COMEX",
        mic="XCEC", name="COMEX",
    ),

    # Europe
    "LSE": VendorVenueCodeRef(
        vendor=VendorNamespace.INTERACTIVE_BROKERS, vendor_code="LSE",
        mic="XLON", name="London Stock Exchange",
    ),
    "IBIS": VendorVenueCodeRef(
        vendor=VendorNamespace.INTERACTIVE_BROKERS, vendor_code="IBIS",
        mic="XETR", name="Xetra",
    ),
    "SBF": VendorVenueCodeRef(
        vendor=VendorNamespace.INTERACTIVE_BROKERS, vendor_code="SBF",
        mic="XPAR", name="Euronext Paris",
    ),
    "AEB": VendorVenueCodeRef(
        vendor=VendorNamespace.INTERACTIVE_BROKERS, vendor_code="AEB",
        mic="XAMS", name="Euronext Amsterdam",
    ),
    "SWX": VendorVenueCodeRef(
        vendor=VendorNamespace.INTERACTIVE_BROKERS, vendor_code="SWX",
        mic="XSWX", name="SIX Swiss Exchange",
    ),
    "EUREX": VendorVenueCodeRef(
        vendor=VendorNamespace.INTERACTIVE_BROKERS, vendor_code="EUREX",
        mic="XEUR", name="Eurex",
    ),

    # Asia-Pacific
    "TSE": VendorVenueCodeRef(
        vendor=VendorNamespace.INTERACTIVE_BROKERS, vendor_code="TSE",
        mic="XJPX", name="Tokyo Stock Exchange",
    ),
    "SEHK": VendorVenueCodeRef(
        vendor=VendorNamespace.INTERACTIVE_BROKERS, vendor_code="SEHK",
        mic="XHKG", name="Hong Kong Stock Exchange",
    ),
    "ASX": VendorVenueCodeRef(
        vendor=VendorNamespace.INTERACTIVE_BROKERS, vendor_code="ASX",
        mic="XASX", name="Australian Securities Exchange",
    ),
    "KSE": VendorVenueCodeRef(
        vendor=VendorNamespace.INTERACTIVE_BROKERS, vendor_code="KSE",
        mic="XKRX", name="Korea Exchange",
    ),
    "SGX": VendorVenueCodeRef(
        vendor=VendorNamespace.INTERACTIVE_BROKERS, vendor_code="SGX",
        mic="XSES", name="Singapore Exchange",
    ),

    # Canada
    "TSX": VendorVenueCodeRef(
        vendor=VendorNamespace.INTERACTIVE_BROKERS, vendor_code="TSX",
        mic="XTSE", name="Toronto Stock Exchange",
    ),
    "VENTURE": VendorVenueCodeRef(
        vendor=VendorNamespace.INTERACTIVE_BROKERS, vendor_code="VENTURE",
        mic="XTSX", name="TSX Venture",
    ),
}


# =============================================================================
# Aggregate Mappings by Vendor
# =============================================================================

VENDOR_CODE_MAPPINGS: dict[VendorNamespace, dict[str, VendorVenueCodeRef]] = {
    VendorNamespace.BLOOMBERG: BLOOMBERG_VENUE_CODES,
    VendorNamespace.REUTERS: REUTERS_VENUE_CODES,
    VendorNamespace.REFINITIV: REUTERS_VENUE_CODES,  # Alias
    VendorNamespace.FACTSET: FACTSET_VENUE_CODES,
    VendorNamespace.INTERACTIVE_BROKERS: IBKR_VENUE_CODES,
}


# =============================================================================
# Reverse Index: MIC → Vendor Codes
# =============================================================================

def _build_mic_to_vendor_index() -> dict[str, list[VendorVenueCodeRef]]:
    """Build reverse index from MIC to vendor codes."""
    index: dict[str, list[VendorVenueCodeRef]] = {}

    for vendor_codes in VENDOR_CODE_MAPPINGS.values():
        for ref in vendor_codes.values():
            if ref.mic:
                mic = ref.mic.upper()
                if mic not in index:
                    index[mic] = []
                index[mic].append(ref)

    return index


_MIC_TO_VENDOR_INDEX: dict[str, list[VendorVenueCodeRef]] = _build_mic_to_vendor_index()


# =============================================================================
# Lookup Functions
# =============================================================================


def lookup_mic_by_vendor_code(
    vendor: VendorNamespace | str,
    vendor_code: str,
) -> str | None:
    """
    Look up MIC code from vendor-specific code.
    
    Args:
        vendor: VendorNamespace enum or string.
        vendor_code: Vendor-specific exchange/venue code.
        
    Returns:
        ISO 10383 MIC code if found, None otherwise.
        
    Example:
        >>> lookup_mic_by_vendor_code(VendorNamespace.BLOOMBERG, "UN")
        'XNYS'
        >>> lookup_mic_by_vendor_code("reuters", ".L")
        'XLON'
    """
    if isinstance(vendor, str):
        try:
            vendor = VendorNamespace(vendor.lower())
        except ValueError:
            return None

    vendor_codes = VENDOR_CODE_MAPPINGS.get(vendor)
    if not vendor_codes:
        return None

    ref = vendor_codes.get(vendor_code)
    return ref.mic if ref else None


def lookup_vendor_codes_for_mic(
    mic: str,
    *,
    vendor: VendorNamespace | None = None,
) -> list[VendorVenueCodeRef]:
    """
    Look up vendor codes for a given MIC.
    
    Args:
        mic: ISO 10383 MIC code.
        vendor: Optional filter by specific vendor.
        
    Returns:
        List of VendorVenueCodeRef matching the MIC.
        
    Example:
        >>> refs = lookup_vendor_codes_for_mic("XNYS")
        >>> [(r.vendor.value, r.vendor_code) for r in refs]
        [('bloomberg', 'UN'), ('bloomberg', 'US'), ('reuters', '.N'), ...]
    """
    refs = _MIC_TO_VENDOR_INDEX.get(mic.upper(), [])

    if vendor:
        refs = [r for r in refs if r.vendor == vendor]

    return refs


def get_vendor_code_ref(
    vendor: VendorNamespace | str,
    vendor_code: str,
) -> VendorVenueCodeRef | None:
    """
    Get full vendor code reference with metadata.
    
    Args:
        vendor: VendorNamespace enum or string.
        vendor_code: Vendor-specific code.
        
    Returns:
        VendorVenueCodeRef if found, None otherwise.
    """
    if isinstance(vendor, str):
        try:
            vendor = VendorNamespace(vendor.lower())
        except ValueError:
            return None

    vendor_codes = VENDOR_CODE_MAPPINGS.get(vendor)
    if not vendor_codes:
        return None

    return vendor_codes.get(vendor_code)


def find_conflicting_mappings(mic: str) -> dict[VendorNamespace, list[VendorVenueCodeRef]]:
    """
    Find potential conflicts where multiple vendor codes map to same MIC.
    
    Useful for data quality checks and reconciliation.
    
    Args:
        mic: ISO 10383 MIC code.
        
    Returns:
        Dict of vendor → list of codes mapping to this MIC.
    """
    refs = lookup_vendor_codes_for_mic(mic)

    by_vendor: dict[VendorNamespace, list[VendorVenueCodeRef]] = {}
    for ref in refs:
        if ref.vendor not in by_vendor:
            by_vendor[ref.vendor] = []
        by_vendor[ref.vendor].append(ref)

    return by_vendor


def get_all_vendor_codes_for_vendor(vendor: VendorNamespace) -> dict[str, VendorVenueCodeRef]:
    """Get all venue codes for a specific vendor."""
    return VENDOR_CODE_MAPPINGS.get(vendor, {})


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Enums
    "VendorNamespace",
    # Typed ref
    "VendorVenueCodeRef",
    # Mapping tables
    "BLOOMBERG_VENUE_CODES",
    "REUTERS_VENUE_CODES",
    "FACTSET_VENUE_CODES",
    "IBKR_VENUE_CODES",
    "VENDOR_CODE_MAPPINGS",
    # Lookup functions
    "lookup_mic_by_vendor_code",
    "lookup_vendor_codes_for_mic",
    "get_vendor_code_ref",
    "find_conflicting_mappings",
    "get_all_vendor_codes_for_vendor",
]
