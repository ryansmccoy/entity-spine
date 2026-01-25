"""
Curated Major Venues Registry.

STDLIB ONLY - NO PYDANTIC.

Human-maintained registry of major trading venues, infrastructure,
and reference data providers across all asset classes.

This is the "signal" layer - high-quality, curated data for:
- Routing decisions
- Analytics graphs
- Display/reporting
- Regulatory lookups

For complete MIC coverage, use iso10383.py bulk data layer.

Categories:
----------
- Equity exchanges (NYSE, NASDAQ, LSE, etc.)
- Options exchanges (CBOE, ISE, etc.)
- Futures exchanges (CME, ICE, Eurex, etc.)
- FX venues (EBS, Reuters Matching, etc.)
- Bond/rates platforms (Tradeweb, MarketAxess, etc.)
- SEFs (swap execution facilities)
- Crypto venues
- Index providers (S&P, MSCI, FTSE, etc.)
- Trade reporting facilities
- Clearinghouses
- CSDs/Depositories

v2.3.2 - Initial version
"""

from dataclasses import dataclass, field
from datetime import date, datetime

from entityspine.domain.enums.markets import AssetClass, MicSource, VenueKind
from entityspine.domain.timestamps import utc_now

# =============================================================================
# VenueRef - Typed Reference for All Venue Types
# =============================================================================


@dataclass(frozen=True, slots=True)
class VenueRef:
    """
    Reference data for a trading venue or market infrastructure.
    
    Generalization of ExchangeRef that covers all venue types:
    exchanges, ECNs, SEFs, clearinghouses, depositories, etc.
    
    Fields:
        mic: ISO 10383 MIC code (primary identifier).
        name: Full legal/official name.
        short_name: Common abbreviation (NYSE, CME, etc.).
        venue_kind: VenueKind classification.
        asset_classes: Asset classes traded/cleared.
        
        # Location
        country_code: ISO 3166-1 alpha-2.
        jurisdiction: Regulatory jurisdiction (may differ from country).
        city: Primary city location.
        timezone: IANA timezone.
        
        # MIC hierarchy
        operating_mic: Parent operating MIC (for segments).
        is_segment: True if this is a segment MIC.
        
        # Operator
        operator_name: Operating company name.
        operator_lei: Operating company LEI.
        
        # Regulatory
        sec_registered: Whether SEC-registered (US venues).
        esma_registered: Whether ESMA-registered (EU venues).
        regulator: Primary regulator.
        
        # Lifecycle
        opened_on: When venue began operations.
        closed_on: When venue ceased operations.
        
        # Provenance
        source: MicSource enum.
        source_url: URL for reference.
        as_of: Data vintage date.
        captured_at: When captured.
        last_verified: When last verified.
        confidence: Confidence score (0.0-1.0).
    """

    mic: str
    name: str

    short_name: str | None = None
    venue_kind: VenueKind = VenueKind.STOCK_EXCHANGE
    asset_classes: tuple[AssetClass, ...] = (AssetClass.EQUITY,)

    # Location
    country_code: str | None = None
    jurisdiction: str | None = None
    city: str | None = None
    timezone: str | None = None

    # MIC hierarchy
    operating_mic: str | None = None
    is_segment: bool = False

    # Operator
    operator_name: str | None = None
    operator_lei: str | None = None

    # Regulatory
    sec_registered: bool = False
    esma_registered: bool = False
    regulator: str | None = None

    # Lifecycle
    opened_on: date | None = None
    closed_on: date | None = None

    # Provenance
    source: MicSource = MicSource.CURATED
    source_url: str | None = None
    as_of: date | None = None
    captured_at: datetime = field(default_factory=utc_now)
    last_verified: date | None = None
    confidence: float = 1.0

    @property
    def is_active(self) -> bool:
        """Check if venue is currently active."""
        return self.closed_on is None

    @property
    def display_name(self) -> str:
        """Get display name (short name if available)."""
        return self.short_name or self.name

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "mic": self.mic,
            "name": self.name,
            "short_name": self.short_name,
            "venue_kind": self.venue_kind.value if self.venue_kind else None,
            "asset_classes": [ac.value for ac in self.asset_classes],
            "country_code": self.country_code,
            "jurisdiction": self.jurisdiction,
            "city": self.city,
            "timezone": self.timezone,
            "operating_mic": self.operating_mic,
            "is_segment": self.is_segment,
            "operator_name": self.operator_name,
            "sec_registered": self.sec_registered,
            "source": self.source.value if self.source else None,
        }


# =============================================================================
# MAJOR EQUITY VENUES
# =============================================================================

MAJOR_EQUITY_VENUES: dict[str, VenueRef] = {
    # === US National Exchanges ===
    "XNYS": VenueRef(
        mic="XNYS", name="New York Stock Exchange", short_name="NYSE",
        venue_kind=VenueKind.STOCK_EXCHANGE, asset_classes=(AssetClass.EQUITY,),
        country_code="US", jurisdiction="US", city="New York", timezone="America/New_York",
        operator_name="Intercontinental Exchange", operator_lei="5493000F4ZO33MV32P92",
        sec_registered=True, regulator="SEC", opened_on=date(1792, 5, 17),
    ),
    "XNAS": VenueRef(
        mic="XNAS", name="NASDAQ Stock Market", short_name="NASDAQ",
        venue_kind=VenueKind.STOCK_EXCHANGE, asset_classes=(AssetClass.EQUITY,),
        country_code="US", jurisdiction="US", city="New York", timezone="America/New_York",
        operator_name="Nasdaq Inc.", operator_lei="549300L8X1Q78HN7L497",
        sec_registered=True, regulator="SEC", opened_on=date(1971, 2, 8),
    ),
    "ARCX": VenueRef(
        mic="ARCX", name="NYSE Arca", short_name="NYSE Arca",
        venue_kind=VenueKind.STOCK_EXCHANGE, asset_classes=(AssetClass.EQUITY, AssetClass.OPTIONS),
        country_code="US", jurisdiction="US", city="New York", timezone="America/New_York",
        operating_mic="XNYS", operator_name="Intercontinental Exchange",
        sec_registered=True, regulator="SEC",
    ),
    "BATS": VenueRef(
        mic="BATS", name="Cboe BZX Exchange", short_name="BZX",
        venue_kind=VenueKind.STOCK_EXCHANGE, asset_classes=(AssetClass.EQUITY,),
        country_code="US", jurisdiction="US", city="Chicago", timezone="America/Chicago",
        operator_name="Cboe Global Markets",
        sec_registered=True, regulator="SEC",
    ),
    "IEXG": VenueRef(
        mic="IEXG", name="Investors Exchange", short_name="IEX",
        venue_kind=VenueKind.STOCK_EXCHANGE, asset_classes=(AssetClass.EQUITY,),
        country_code="US", jurisdiction="US", city="New York", timezone="America/New_York",
        sec_registered=True, regulator="SEC", opened_on=date(2016, 9, 2),
    ),

    # === NASDAQ Segments ===
    "XNGS": VenueRef(
        mic="XNGS", name="Nasdaq Global Select Market", short_name="NGS",
        venue_kind=VenueKind.STOCK_EXCHANGE, asset_classes=(AssetClass.EQUITY,),
        country_code="US", jurisdiction="US", city="New York", timezone="America/New_York",
        operating_mic="XNAS", is_segment=True, operator_name="Nasdaq Inc.",
    ),
    "XNMS": VenueRef(
        mic="XNMS", name="Nasdaq Global Market", short_name="NGM",
        venue_kind=VenueKind.STOCK_EXCHANGE, asset_classes=(AssetClass.EQUITY,),
        country_code="US", jurisdiction="US", city="New York", timezone="America/New_York",
        operating_mic="XNAS", is_segment=True, operator_name="Nasdaq Inc.",
    ),
    "XNCM": VenueRef(
        mic="XNCM", name="Nasdaq Capital Market", short_name="NCM",
        venue_kind=VenueKind.STOCK_EXCHANGE, asset_classes=(AssetClass.EQUITY,),
        country_code="US", jurisdiction="US", city="New York", timezone="America/New_York",
        operating_mic="XNAS", is_segment=True, operator_name="Nasdaq Inc.",
    ),

    # === US OTC Markets ===
    "OTCM": VenueRef(
        mic="OTCM", name="OTC Markets Group", short_name="OTCM",
        venue_kind=VenueKind.OTC_MARKET, asset_classes=(AssetClass.EQUITY,),
        country_code="US", jurisdiction="US", city="New York", timezone="America/New_York",
        regulator="FINRA",
    ),

    # === European Exchanges ===
    "XLON": VenueRef(
        mic="XLON", name="London Stock Exchange", short_name="LSE",
        venue_kind=VenueKind.STOCK_EXCHANGE, asset_classes=(AssetClass.EQUITY, AssetClass.FIXED_INCOME),
        country_code="GB", jurisdiction="UK", city="London", timezone="Europe/London",
        operator_name="London Stock Exchange Group", operator_lei="213800D1EI4B9WTWWD28",
        esma_registered=True, regulator="FCA",
    ),
    "XPAR": VenueRef(
        mic="XPAR", name="Euronext Paris", short_name="Paris",
        venue_kind=VenueKind.STOCK_EXCHANGE, asset_classes=(AssetClass.EQUITY,),
        country_code="FR", jurisdiction="EU", city="Paris", timezone="Europe/Paris",
        operator_name="Euronext N.V.", esma_registered=True, regulator="AMF",
    ),
    "XAMS": VenueRef(
        mic="XAMS", name="Euronext Amsterdam", short_name="Amsterdam",
        venue_kind=VenueKind.STOCK_EXCHANGE, asset_classes=(AssetClass.EQUITY,),
        country_code="NL", jurisdiction="EU", city="Amsterdam", timezone="Europe/Amsterdam",
        operator_name="Euronext N.V.", esma_registered=True, regulator="AFM",
    ),
    "XETR": VenueRef(
        mic="XETR", name="Xetra", short_name="Xetra",
        venue_kind=VenueKind.STOCK_EXCHANGE, asset_classes=(AssetClass.EQUITY,),
        country_code="DE", jurisdiction="EU", city="Frankfurt", timezone="Europe/Berlin",
        operator_name="Deutsche Börse AG", esma_registered=True, regulator="BaFin",
    ),
    "XSWX": VenueRef(
        mic="XSWX", name="SIX Swiss Exchange", short_name="SIX",
        venue_kind=VenueKind.STOCK_EXCHANGE, asset_classes=(AssetClass.EQUITY,),
        country_code="CH", jurisdiction="CH", city="Zurich", timezone="Europe/Zurich",
        regulator="FINMA",
    ),

    # === Asia-Pacific Exchanges ===
    "XJPX": VenueRef(
        mic="XJPX", name="Japan Exchange Group", short_name="JPX",
        venue_kind=VenueKind.STOCK_EXCHANGE, asset_classes=(AssetClass.EQUITY,),
        country_code="JP", jurisdiction="JP", city="Tokyo", timezone="Asia/Tokyo",
        operator_name="Japan Exchange Group", regulator="FSA Japan",
    ),
    "XHKG": VenueRef(
        mic="XHKG", name="Hong Kong Stock Exchange", short_name="HKEX",
        venue_kind=VenueKind.STOCK_EXCHANGE, asset_classes=(AssetClass.EQUITY,),
        country_code="HK", jurisdiction="HK", city="Hong Kong", timezone="Asia/Hong_Kong",
        operator_name="Hong Kong Exchanges and Clearing", regulator="SFC",
    ),
    "XSHG": VenueRef(
        mic="XSHG", name="Shanghai Stock Exchange", short_name="SSE",
        venue_kind=VenueKind.STOCK_EXCHANGE, asset_classes=(AssetClass.EQUITY,),
        country_code="CN", jurisdiction="CN", city="Shanghai", timezone="Asia/Shanghai",
        regulator="CSRC",
    ),
    "XSHE": VenueRef(
        mic="XSHE", name="Shenzhen Stock Exchange", short_name="SZSE",
        venue_kind=VenueKind.STOCK_EXCHANGE, asset_classes=(AssetClass.EQUITY,),
        country_code="CN", jurisdiction="CN", city="Shenzhen", timezone="Asia/Shanghai",
        regulator="CSRC",
    ),
    "XASX": VenueRef(
        mic="XASX", name="Australian Securities Exchange", short_name="ASX",
        venue_kind=VenueKind.STOCK_EXCHANGE, asset_classes=(AssetClass.EQUITY,),
        country_code="AU", jurisdiction="AU", city="Sydney", timezone="Australia/Sydney",
        regulator="ASIC",
    ),
    "XKRX": VenueRef(
        mic="XKRX", name="Korea Exchange", short_name="KRX",
        venue_kind=VenueKind.STOCK_EXCHANGE, asset_classes=(AssetClass.EQUITY,),
        country_code="KR", jurisdiction="KR", city="Seoul", timezone="Asia/Seoul",
        regulator="FSC Korea",
    ),
}


# =============================================================================
# MAJOR OPTIONS VENUES
# =============================================================================

MAJOR_OPTIONS_VENUES: dict[str, VenueRef] = {
    "XCBO": VenueRef(
        mic="XCBO", name="Cboe Options Exchange", short_name="CBOE",
        venue_kind=VenueKind.OPTIONS_EXCHANGE, asset_classes=(AssetClass.OPTIONS,),
        country_code="US", jurisdiction="US", city="Chicago", timezone="America/Chicago",
        operator_name="Cboe Global Markets", sec_registered=True, regulator="SEC",
    ),
    "XISX": VenueRef(
        mic="XISX", name="Nasdaq ISE", short_name="ISE",
        venue_kind=VenueKind.OPTIONS_EXCHANGE, asset_classes=(AssetClass.OPTIONS,),
        country_code="US", jurisdiction="US", city="New York", timezone="America/New_York",
        operator_name="Nasdaq Inc.", sec_registered=True, regulator="SEC",
    ),
    "XPHL": VenueRef(
        mic="XPHL", name="Nasdaq PHLX", short_name="PHLX",
        venue_kind=VenueKind.OPTIONS_EXCHANGE, asset_classes=(AssetClass.OPTIONS,),
        country_code="US", jurisdiction="US", city="Philadelphia", timezone="America/New_York",
        operator_name="Nasdaq Inc.", sec_registered=True, regulator="SEC",
    ),
    "AMXO": VenueRef(
        mic="AMXO", name="NYSE American Options", short_name="AMEX Options",
        venue_kind=VenueKind.OPTIONS_EXCHANGE, asset_classes=(AssetClass.OPTIONS,),
        country_code="US", jurisdiction="US", city="New York", timezone="America/New_York",
        operator_name="Intercontinental Exchange", sec_registered=True,
    ),
    "XEUR": VenueRef(
        mic="XEUR", name="Eurex Exchange", short_name="Eurex",
        venue_kind=VenueKind.OPTIONS_EXCHANGE, asset_classes=(AssetClass.OPTIONS, AssetClass.FUTURES),
        country_code="DE", jurisdiction="EU", city="Frankfurt", timezone="Europe/Berlin",
        operator_name="Deutsche Börse AG", esma_registered=True,
    ),
}


# =============================================================================
# MAJOR FUTURES VENUES
# =============================================================================

MAJOR_FUTURES_VENUES: dict[str, VenueRef] = {
    "XCME": VenueRef(
        mic="XCME", name="Chicago Mercantile Exchange", short_name="CME",
        venue_kind=VenueKind.FUTURES_EXCHANGE, asset_classes=(AssetClass.FUTURES, AssetClass.OPTIONS),
        country_code="US", jurisdiction="US", city="Chicago", timezone="America/Chicago",
        operator_name="CME Group", operator_lei="LCZ7 VOICES175MTEE171",
        regulator="CFTC", opened_on=date(1898, 1, 1),
    ),
    "XCBT": VenueRef(
        mic="XCBT", name="Chicago Board of Trade", short_name="CBOT",
        venue_kind=VenueKind.FUTURES_EXCHANGE, asset_classes=(AssetClass.FUTURES,),
        country_code="US", jurisdiction="US", city="Chicago", timezone="America/Chicago",
        operating_mic="XCME", operator_name="CME Group", regulator="CFTC",
    ),
    "XNYM": VenueRef(
        mic="XNYM", name="New York Mercantile Exchange", short_name="NYMEX",
        venue_kind=VenueKind.FUTURES_EXCHANGE, asset_classes=(AssetClass.FUTURES, AssetClass.COMMODITIES),
        country_code="US", jurisdiction="US", city="New York", timezone="America/New_York",
        operating_mic="XCME", operator_name="CME Group", regulator="CFTC",
    ),
    "XCEC": VenueRef(
        mic="XCEC", name="Commodity Exchange Inc", short_name="COMEX",
        venue_kind=VenueKind.COMMODITY_EXCHANGE, asset_classes=(AssetClass.COMMODITIES,),
        country_code="US", jurisdiction="US", city="New York", timezone="America/New_York",
        operating_mic="XCME", operator_name="CME Group", regulator="CFTC",
    ),
    "IFEU": VenueRef(
        mic="IFEU", name="ICE Futures Europe", short_name="ICE Europe",
        venue_kind=VenueKind.FUTURES_EXCHANGE, asset_classes=(AssetClass.FUTURES, AssetClass.COMMODITIES),
        country_code="GB", jurisdiction="UK", city="London", timezone="Europe/London",
        operator_name="Intercontinental Exchange", regulator="FCA",
    ),
    "IFUS": VenueRef(
        mic="IFUS", name="ICE Futures U.S.", short_name="ICE US",
        venue_kind=VenueKind.FUTURES_EXCHANGE, asset_classes=(AssetClass.FUTURES,),
        country_code="US", jurisdiction="US", city="New York", timezone="America/New_York",
        operator_name="Intercontinental Exchange", regulator="CFTC",
    ),
    "XEUR": VenueRef(  # Also listed in options
        mic="XEUR", name="Eurex Exchange", short_name="Eurex",
        venue_kind=VenueKind.FUTURES_EXCHANGE, asset_classes=(AssetClass.FUTURES, AssetClass.OPTIONS),
        country_code="DE", jurisdiction="EU", city="Frankfurt", timezone="Europe/Berlin",
        operator_name="Deutsche Börse AG", esma_registered=True,
    ),
    "XSGE": VenueRef(
        mic="XSGE", name="Shanghai Futures Exchange", short_name="SHFE",
        venue_kind=VenueKind.FUTURES_EXCHANGE, asset_classes=(AssetClass.FUTURES, AssetClass.COMMODITIES),
        country_code="CN", jurisdiction="CN", city="Shanghai", timezone="Asia/Shanghai",
        regulator="CSRC",
    ),
}


# =============================================================================
# MAJOR FX VENUES
# =============================================================================

MAJOR_FX_VENUES: dict[str, VenueRef] = {
    "EBSP": VenueRef(
        mic="EBSP", name="EBS Market", short_name="EBS",
        venue_kind=VenueKind.FX_ECN, asset_classes=(AssetClass.FX,),
        country_code="GB", jurisdiction="UK", city="London", timezone="Europe/London",
        operator_name="CME Group",
    ),
    "RTSL": VenueRef(
        mic="RTSL", name="Refinitiv Matching", short_name="Reuters Matching",
        venue_kind=VenueKind.FX_ECN, asset_classes=(AssetClass.FX,),
        country_code="GB", jurisdiction="UK", city="London", timezone="Europe/London",
        operator_name="London Stock Exchange Group",
    ),
    "CRNX": VenueRef(
        mic="CRNX", name="Currenex", short_name="Currenex",
        venue_kind=VenueKind.FX_PLATFORM, asset_classes=(AssetClass.FX,),
        country_code="US", jurisdiction="US", city="New York", timezone="America/New_York",
        operator_name="State Street",
    ),
    "FXAL": VenueRef(
        mic="FXAL", name="FXall", short_name="FXall",
        venue_kind=VenueKind.FX_PLATFORM, asset_classes=(AssetClass.FX,),
        country_code="US", jurisdiction="US", city="New York", timezone="America/New_York",
        operator_name="Refinitiv",
    ),
    "HSFX": VenueRef(
        mic="HSFX", name="Hotspot FX", short_name="Hotspot",
        venue_kind=VenueKind.FX_ECN, asset_classes=(AssetClass.FX,),
        country_code="US", jurisdiction="US", city="New York", timezone="America/New_York",
        operator_name="Cboe Global Markets",
    ),
}


# =============================================================================
# MAJOR BOND/RATES VENUES
# =============================================================================

MAJOR_RATES_CREDIT_VENUES: dict[str, VenueRef] = {
    "TRWB": VenueRef(
        mic="TRWB", name="Tradeweb", short_name="Tradeweb",
        venue_kind=VenueKind.BOND_PLATFORM, asset_classes=(AssetClass.FIXED_INCOME,),
        country_code="US", jurisdiction="US", city="New York", timezone="America/New_York",
        operator_name="Tradeweb Markets", sec_registered=True,
    ),
    "MKTX": VenueRef(
        mic="MKTX", name="MarketAxess", short_name="MarketAxess",
        venue_kind=VenueKind.BOND_PLATFORM, asset_classes=(AssetClass.FIXED_INCOME,),
        country_code="US", jurisdiction="US", city="New York", timezone="America/New_York",
        operator_name="MarketAxess Holdings", sec_registered=True,
    ),
    "BTEC": VenueRef(
        mic="BTEC", name="BrokerTec", short_name="BrokerTec",
        venue_kind=VenueKind.RATES_VENUE, asset_classes=(AssetClass.FIXED_INCOME,),
        country_code="US", jurisdiction="US", city="New York", timezone="America/New_York",
        operator_name="CME Group",
    ),
    "BGCI": VenueRef(
        mic="BGCI", name="BGC Partners", short_name="BGC",
        venue_kind=VenueKind.IDB, asset_classes=(AssetClass.FIXED_INCOME, AssetClass.FX),
        country_code="US", jurisdiction="US", city="New York", timezone="America/New_York",
        operator_name="BGC Partners",
    ),
    "ICAP": VenueRef(
        mic="ICAP", name="TP ICAP", short_name="TP ICAP",
        venue_kind=VenueKind.IDB, asset_classes=(AssetClass.FIXED_INCOME, AssetClass.FX),
        country_code="GB", jurisdiction="UK", city="London", timezone="Europe/London",
        operator_name="TP ICAP Group",
    ),
}


# =============================================================================
# MAJOR SEFS (Swap Execution Facilities)
# =============================================================================

MAJOR_SWAPS_SEFS: dict[str, VenueRef] = {
    "TWSF": VenueRef(
        mic="TWSF", name="Tradeweb SEF", short_name="Tradeweb SEF",
        venue_kind=VenueKind.SEF, asset_classes=(AssetClass.FX, AssetClass.FIXED_INCOME),
        country_code="US", jurisdiction="US", city="New York", timezone="America/New_York",
        operator_name="Tradeweb Markets", regulator="CFTC",
    ),
    "BGSF": VenueRef(
        mic="BGSF", name="BGC SEF", short_name="BGC SEF",
        venue_kind=VenueKind.SEF, asset_classes=(AssetClass.FX, AssetClass.FIXED_INCOME),
        country_code="US", jurisdiction="US", city="New York", timezone="America/New_York",
        operator_name="BGC Partners", regulator="CFTC",
    ),
    "BLMX": VenueRef(
        mic="BLMX", name="Bloomberg SEF", short_name="BSEF",
        venue_kind=VenueKind.SEF, asset_classes=(AssetClass.FX, AssetClass.FIXED_INCOME),
        country_code="US", jurisdiction="US", city="New York", timezone="America/New_York",
        operator_name="Bloomberg LP", regulator="CFTC",
    ),
    "ICSF": VenueRef(
        mic="ICSF", name="ICE Swap Trade", short_name="ICE SEF",
        venue_kind=VenueKind.SEF, asset_classes=(AssetClass.FX,),
        country_code="US", jurisdiction="US", city="New York", timezone="America/New_York",
        operator_name="Intercontinental Exchange", regulator="CFTC",
    ),
}


# =============================================================================
# MAJOR CRYPTO VENUES
# =============================================================================

MAJOR_CRYPTO_VENUES: dict[str, VenueRef] = {
    # Note: Many crypto venues don't have official MICs
    # Using internal codes or applying for MICs
    "COIN": VenueRef(
        mic="COIN", name="Coinbase Exchange", short_name="Coinbase",
        venue_kind=VenueKind.CRYPTO_EXCHANGE, asset_classes=(AssetClass.CRYPTO,),
        country_code="US", jurisdiction="US", city="San Francisco", timezone="America/Los_Angeles",
        operator_name="Coinbase Global",
    ),
    "KRKN": VenueRef(
        mic="KRKN", name="Kraken", short_name="Kraken",
        venue_kind=VenueKind.CRYPTO_EXCHANGE, asset_classes=(AssetClass.CRYPTO,),
        country_code="US", jurisdiction="US", city="San Francisco", timezone="America/Los_Angeles",
        operator_name="Payward Inc.",
    ),
    "GMNI": VenueRef(
        mic="GMNI", name="Gemini Exchange", short_name="Gemini",
        venue_kind=VenueKind.CRYPTO_EXCHANGE, asset_classes=(AssetClass.CRYPTO,),
        country_code="US", jurisdiction="US", city="New York", timezone="America/New_York",
        operator_name="Gemini Trust Company",
    ),
}


# =============================================================================
# MAJOR INDEX PROVIDERS
# =============================================================================

MAJOR_INDEX_PROVIDERS: dict[str, VenueRef] = {
    "XSPD": VenueRef(
        mic="XSPD", name="S&P Dow Jones Indices", short_name="S&P DJI",
        venue_kind=VenueKind.INDEX_PROVIDER, asset_classes=(AssetClass.EQUITY,),
        country_code="US", jurisdiction="US", city="New York", timezone="America/New_York",
        operator_name="S&P Global",
    ),
    "MSCI": VenueRef(
        mic="MSCI", name="MSCI Inc", short_name="MSCI",
        venue_kind=VenueKind.INDEX_PROVIDER, asset_classes=(AssetClass.EQUITY,),
        country_code="US", jurisdiction="US", city="New York", timezone="America/New_York",
        operator_name="MSCI Inc.",
    ),
    "FTSE": VenueRef(
        mic="FTSE", name="FTSE Russell", short_name="FTSE Russell",
        venue_kind=VenueKind.INDEX_PROVIDER, asset_classes=(AssetClass.EQUITY,),
        country_code="GB", jurisdiction="UK", city="London", timezone="Europe/London",
        operator_name="London Stock Exchange Group",
    ),
    "NASD": VenueRef(
        mic="NASD", name="Nasdaq Global Indexes", short_name="Nasdaq Indexes",
        venue_kind=VenueKind.INDEX_PROVIDER, asset_classes=(AssetClass.EQUITY,),
        country_code="US", jurisdiction="US", city="New York", timezone="America/New_York",
        operator_name="Nasdaq Inc.",
    ),
}


# =============================================================================
# MAJOR TRADE REPORTING FACILITIES
# =============================================================================

MAJOR_TRADE_REPORTING: dict[str, VenueRef] = {
    "FINR": VenueRef(
        mic="FINR", name="FINRA", short_name="FINRA",
        venue_kind=VenueKind.TRF, asset_classes=(AssetClass.EQUITY,),
        country_code="US", jurisdiction="US", city="Washington DC", timezone="America/New_York",
        operator_name="FINRA",
    ),
    "TRFI": VenueRef(
        mic="TRFI", name="NYSE TRF", short_name="NYSE TRF",
        venue_kind=VenueKind.TRF, asset_classes=(AssetClass.EQUITY,),
        country_code="US", jurisdiction="US", city="New York", timezone="America/New_York",
        operator_name="Intercontinental Exchange",
    ),
    "NQTF": VenueRef(
        mic="NQTF", name="NASDAQ TRF", short_name="NASDAQ TRF",
        venue_kind=VenueKind.TRF, asset_classes=(AssetClass.EQUITY,),
        country_code="US", jurisdiction="US", city="New York", timezone="America/New_York",
        operator_name="Nasdaq Inc.",
    ),
}


# =============================================================================
# MAJOR CLEARINGHOUSES
# =============================================================================

MAJOR_CLEARINGHOUSES: dict[str, VenueRef] = {
    # US Clearinghouses
    "XDTC": VenueRef(
        mic="XDTC", name="Depository Trust Company", short_name="DTC",
        venue_kind=VenueKind.CSD, asset_classes=(AssetClass.EQUITY, AssetClass.FIXED_INCOME),
        country_code="US", jurisdiction="US", city="New York", timezone="America/New_York",
        operator_name="DTCC",
    ),
    "XNSCC": VenueRef(
        mic="XNSCC", name="National Securities Clearing Corporation", short_name="NSCC",
        venue_kind=VenueKind.CCP, asset_classes=(AssetClass.EQUITY,),
        country_code="US", jurisdiction="US", city="New York", timezone="America/New_York",
        operator_name="DTCC",
    ),
    "XOCC": VenueRef(
        mic="XOCC", name="Options Clearing Corporation", short_name="OCC",
        venue_kind=VenueKind.CCP, asset_classes=(AssetClass.OPTIONS,),
        country_code="US", jurisdiction="US", city="Chicago", timezone="America/Chicago",
        operator_name="OCC",
    ),
    "XCCC": VenueRef(
        mic="XCCC", name="CME Clearing", short_name="CME Clearing",
        venue_kind=VenueKind.CCP, asset_classes=(AssetClass.FUTURES,),
        country_code="US", jurisdiction="US", city="Chicago", timezone="America/Chicago",
        operator_name="CME Group",
    ),
    "XICC": VenueRef(
        mic="XICC", name="ICE Clear Credit", short_name="ICE Clear Credit",
        venue_kind=VenueKind.CCP, asset_classes=(AssetClass.FIXED_INCOME,),
        country_code="US", jurisdiction="US", city="Chicago", timezone="America/Chicago",
        operator_name="Intercontinental Exchange",
    ),

    # European Clearinghouses
    "LCHL": VenueRef(
        mic="LCHL", name="LCH Ltd", short_name="LCH",
        venue_kind=VenueKind.CCP, asset_classes=(AssetClass.FX, AssetClass.FIXED_INCOME),
        country_code="GB", jurisdiction="UK", city="London", timezone="Europe/London",
        operator_name="London Stock Exchange Group",
    ),
    "ECAG": VenueRef(
        mic="ECAG", name="Eurex Clearing AG", short_name="Eurex Clearing",
        venue_kind=VenueKind.CCP, asset_classes=(AssetClass.FUTURES, AssetClass.OPTIONS),
        country_code="DE", jurisdiction="EU", city="Frankfurt", timezone="Europe/Berlin",
        operator_name="Deutsche Börse AG",
    ),
}


# =============================================================================
# MAJOR CSDs / DEPOSITORIES
# =============================================================================

MAJOR_DEPOSITORIES_CSDS: dict[str, VenueRef] = {
    "XDTC": VenueRef(  # Also in clearinghouses
        mic="XDTC", name="Depository Trust Company", short_name="DTC",
        venue_kind=VenueKind.CSD, asset_classes=(AssetClass.EQUITY, AssetClass.FIXED_INCOME),
        country_code="US", jurisdiction="US", city="New York", timezone="America/New_York",
        operator_name="DTCC",
    ),
    "ECLE": VenueRef(
        mic="ECLE", name="Euroclear", short_name="Euroclear",
        venue_kind=VenueKind.ICSD, asset_classes=(AssetClass.EQUITY, AssetClass.FIXED_INCOME),
        country_code="BE", jurisdiction="EU", city="Brussels", timezone="Europe/Brussels",
        operator_name="Euroclear Group",
    ),
    "CLST": VenueRef(
        mic="CLST", name="Clearstream", short_name="Clearstream",
        venue_kind=VenueKind.ICSD, asset_classes=(AssetClass.EQUITY, AssetClass.FIXED_INCOME),
        country_code="LU", jurisdiction="EU", city="Luxembourg", timezone="Europe/Luxembourg",
        operator_name="Deutsche Börse AG",
    ),
    "CRES": VenueRef(
        mic="CRES", name="CREST", short_name="CREST",
        venue_kind=VenueKind.CSD, asset_classes=(AssetClass.EQUITY,),
        country_code="GB", jurisdiction="UK", city="London", timezone="Europe/London",
        operator_name="Euroclear UK & International",
    ),
}


# =============================================================================
# Aggregate All Major Venues
# =============================================================================

ALL_MAJOR_VENUES: dict[str, VenueRef] = {
    **MAJOR_EQUITY_VENUES,
    **MAJOR_OPTIONS_VENUES,
    **MAJOR_FUTURES_VENUES,
    **MAJOR_FX_VENUES,
    **MAJOR_RATES_CREDIT_VENUES,
    **MAJOR_SWAPS_SEFS,
    **MAJOR_CRYPTO_VENUES,
    **MAJOR_INDEX_PROVIDERS,
    **MAJOR_TRADE_REPORTING,
    **MAJOR_CLEARINGHOUSES,
    **MAJOR_DEPOSITORIES_CSDS,
}


# =============================================================================
# Lookup Helpers
# =============================================================================


def lookup_major_venue(mic: str) -> VenueRef | None:
    """
    Lookup a major venue by MIC code.
    
    Args:
        mic: ISO 10383 MIC code.
        
    Returns:
        VenueRef if found in curated list, None otherwise.
    """
    return ALL_MAJOR_VENUES.get(mic.upper())


def get_major_venues(
    *,
    asset_class: AssetClass | None = None,
    venue_kind: VenueKind | None = None,
    jurisdiction: str | None = None,
    country_code: str | None = None,
) -> list[VenueRef]:
    """
    Get major venues filtered by criteria.
    
    Args:
        asset_class: Filter by asset class.
        venue_kind: Filter by venue kind.
        jurisdiction: Filter by regulatory jurisdiction (US, EU, UK, etc.).
        country_code: Filter by ISO country code.
        
    Returns:
        List of matching VenueRef instances.
    """
    results = []

    for venue in ALL_MAJOR_VENUES.values():
        if asset_class and asset_class not in venue.asset_classes:
            continue
        if venue_kind and venue.venue_kind != venue_kind:
            continue
        if jurisdiction and venue.jurisdiction != jurisdiction:
            continue
        if country_code and venue.country_code != country_code:
            continue
        results.append(venue)

    return results


def get_venues_by_kind(venue_kind: VenueKind) -> list[VenueRef]:
    """Get all major venues of a specific kind."""
    return [v for v in ALL_MAJOR_VENUES.values() if v.venue_kind == venue_kind]


def get_venues_by_asset_class(asset_class: AssetClass) -> list[VenueRef]:
    """Get all major venues that trade a specific asset class."""
    return [v for v in ALL_MAJOR_VENUES.values() if asset_class in v.asset_classes]


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Typed ref
    "VenueRef",
    # Curated registries
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
    # Helpers
    "lookup_major_venue",
    "get_major_venues",
    "get_venues_by_kind",
    "get_venues_by_asset_class",
]
