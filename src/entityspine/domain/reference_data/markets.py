"""
Market infrastructure reference data.

STDLIB ONLY - NO PYDANTIC.

This module contains well-known exchanges, clearinghouses, and vendor code mappings.
Data sourced from:
- Thomson Reuters OpenPermID (421 exchange codes, 293 MICs)
- Bloomberg BBUID (258 feed sources)
- FactSet (128 exchanges)
- Interactive Brokers (69 exchanges)
- ISO 10383 MIC codes

Use this for:
- Seeding exchange database
- Validating MIC codes
- Mapping vendor codes to MICs

v2.3.1 - Moved from domain/markets.py for cleaner separation of concerns.
v2.3.2 - Added ExchangeRef typed dataclass with provenance fields.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import TypedDict

from entityspine.domain.timestamps import utc_now


# =============================================================================
# Typed Reference Data Classes (v2.3.2)
# =============================================================================


@dataclass(frozen=True, slots=True)
class ExchangeRef:
    """
    Typed reference data for an exchange with provenance tracking.
    
    Use this when you need more than just a dict lookup - when provenance,
    source tracking, or typed access matters.
    
    Attributes:
        mic: Market Identifier Code (ISO 10383).
        name: Full exchange name.
        short_name: Common abbreviated name.
        country_code: ISO 3166-1 alpha-2 country code.
        city: City where headquartered.
        timezone: IANA timezone string.
        
        # Provenance
        source: Where this data came from (e.g., "ISO 10383", "SEC").
        source_url: URL to authoritative source.
        as_of: Date when this data was valid/published.
        captured_at: When we captured/ingested this data.
        last_verified: When we last verified this data was still accurate.
        confidence: Confidence score 0.0-1.0.
    """
    
    mic: str
    name: str
    
    short_name: str | None = None
    country_code: str | None = None
    city: str | None = None
    timezone: str | None = None
    operating_mic: str | None = None  # For segment MICs
    
    # Provenance (v2.3.2)
    source: str = "unknown"
    source_url: str | None = None
    as_of: date | None = None
    captured_at: datetime = field(default_factory=utc_now)
    last_verified: date | None = None
    confidence: float = 1.0
    
    def to_dict(self) -> dict:
        """Convert to dict for backward compatibility."""
        result = {"name": self.name}
        if self.short_name:
            result["short"] = self.short_name
        if self.city:
            result["city"] = self.city
        if self.country_code:
            result["country"] = self.country_code
        return result
    
    @classmethod
    def from_dict(
        cls,
        mic: str,
        data: dict,
        *,
        source: str = "unknown",
        source_url: str | None = None,
        as_of: date | None = None,
    ) -> "ExchangeRef":
        """Create ExchangeRef from legacy dict format."""
        return cls(
            mic=mic,
            name=data.get("name", ""),
            short_name=data.get("short"),
            country_code=data.get("country"),
            city=data.get("city"),
            source=source,
            source_url=source_url,
            as_of=as_of,
        )


@dataclass(frozen=True, slots=True)
class ClearinghouseRef:
    """
    Typed reference data for a clearinghouse with provenance tracking.
    
    Attributes:
        identifier: Unique identifier (often name-based).
        name: Full clearinghouse name.
        short_name: Common abbreviated name.
        clearinghouse_type: Type of clearing organization.
        country_code: ISO 3166-1 alpha-2 country code.
        
        # Provenance
        source: Where this data came from.
        source_url: URL to authoritative source.
        as_of: Date when this data was valid/published.
        captured_at: When we captured/ingested this data.
    """
    
    identifier: str
    name: str
    
    short_name: str | None = None
    clearinghouse_type: str | None = None
    country_code: str | None = None
    
    # Provenance (v2.3.2)
    source: str = "unknown"
    source_url: str | None = None
    as_of: date | None = None
    captured_at: datetime = field(default_factory=utc_now)
    
    def to_dict(self) -> dict:
        """Convert to dict for backward compatibility."""
        result = {"name": self.name}
        if self.short_name:
            result["short"] = self.short_name
        if self.clearinghouse_type:
            result["type"] = self.clearinghouse_type
        if self.country_code:
            result["country"] = self.country_code
        return result


# =============================================================================
# Type definitions for reference data (legacy TypedDict)
# =============================================================================


class ExchangeInfo(TypedDict, total=False):
    """Type for exchange reference data entries."""
    name: str
    short: str
    city: str
    country: str


class ClearinghouseInfo(TypedDict, total=False):
    """Type for clearinghouse reference data entries."""
    name: str
    short: str
    type: str
    country: str


# =============================================================================
# US Exchanges
# =============================================================================

# Major US Equity Exchanges (MIC codes → Full Name)
US_EQUITY_EXCHANGES: dict[str, ExchangeInfo] = {
    "XNYS": {"name": "New York Stock Exchange", "short": "NYSE", "city": "New York"},
    "XNAS": {"name": "NASDAQ Stock Market", "short": "NASDAQ", "city": "New York"},
    "ARCX": {"name": "NYSE Arca", "short": "ARCA", "city": "New York"},
    "XASE": {"name": "NYSE American", "short": "AMEX", "city": "New York"},
    "BATS": {"name": "Cboe BZX Exchange", "short": "BZX", "city": "Chicago"},
    "BATY": {"name": "Cboe BYX Exchange", "short": "BYX", "city": "Chicago"},
    "EDGA": {"name": "Cboe EDGA Exchange", "short": "EDGA", "city": "Chicago"},
    "EDGX": {"name": "Cboe EDGX Exchange", "short": "EDGX", "city": "Chicago"},
    "IEXG": {"name": "Investors Exchange", "short": "IEX", "city": "New York"},
    "XBOS": {"name": "NASDAQ BX", "short": "BX", "city": "Boston"},
    "XPHL": {"name": "NASDAQ PHLX", "short": "PHLX", "city": "Philadelphia"},
    "XCHI": {"name": "NYSE Chicago", "short": "CHX", "city": "Chicago"},
    "MEMX": {"name": "MEMX Exchange", "short": "MEMX", "city": "New York"},
    "LTSE": {"name": "Long-Term Stock Exchange", "short": "LTSE", "city": "San Francisco"},
    "XNCM": {"name": "NASDAQ Capital Market", "short": "NASDAQ-CM", "city": "New York"},
    "XNGS": {"name": "NASDAQ Global Select", "short": "NASDAQ-GS", "city": "New York"},
    "XNMS": {"name": "NASDAQ Global Market", "short": "NASDAQ-GM", "city": "New York"},
}

# US Options Exchanges (MIC → Details)
US_OPTIONS_EXCHANGES: dict[str, ExchangeInfo] = {
    "XCBO": {"name": "Cboe Options Exchange", "short": "CBOE", "city": "Chicago"},
    "ARCO": {"name": "NYSE Arca Options", "short": "ARCA-OPT", "city": "New York"},
    "AMXO": {"name": "NYSE American Options", "short": "AMEX-OPT", "city": "New York"},
    "XISX": {"name": "NASDAQ ISE", "short": "ISE", "city": "New York"},
    "GMNI": {"name": "MIAX Emerald", "short": "EMERALD", "city": "Princeton"},
    "MPRL": {"name": "MIAX Pearl", "short": "PEARL", "city": "Princeton"},
    "XMIO": {"name": "MIAX Options", "short": "MIAX", "city": "Princeton"},
    "XBOX": {"name": "Boston Options Exchange", "short": "BOX", "city": "Boston"},
    "BATO": {"name": "Cboe BZX Options", "short": "BZX-OPT", "city": "Chicago"},
    "C2OX": {"name": "Cboe C2 Options", "short": "C2", "city": "Chicago"},
    "XPHO": {"name": "NASDAQ PHLX Options", "short": "PHLX-OPT", "city": "Philadelphia"},
    "XNDQ": {"name": "NASDAQ Options Market", "short": "NOM", "city": "New York"},
}

# US Futures Exchanges (MIC → Details)
US_FUTURES_EXCHANGES: dict[str, ExchangeInfo] = {
    "XCME": {"name": "Chicago Mercantile Exchange", "short": "CME", "city": "Chicago"},
    "XCBT": {"name": "Chicago Board of Trade", "short": "CBOT", "city": "Chicago"},
    "XNYM": {"name": "New York Mercantile Exchange", "short": "NYMEX", "city": "New York"},
    "XCEC": {"name": "COMEX", "short": "COMEX", "city": "New York"},
    "IFUS": {"name": "ICE Futures US", "short": "ICE-US", "city": "New York"},
    "XCBF": {"name": "Cboe Futures Exchange", "short": "CFE", "city": "Chicago"},
    "XOCH": {"name": "OneChicago", "short": "ONE", "city": "Chicago"},
    "XKBT": {"name": "Kansas City Board of Trade", "short": "KCBT", "city": "Kansas City"},
    "SMFE": {"name": "Small Exchange", "short": "SMFE", "city": "Chicago"},
}

# US OTC Markets
US_OTC_MARKETS: dict[str, ExchangeInfo] = {
    "OTCM": {"name": "OTC Markets", "short": "OTCM", "city": "New York"},
    "OTCQ": {"name": "OTCQX", "short": "OTCQX", "city": "New York"},
    "OTCB": {"name": "OTCQB", "short": "OTCQB", "city": "New York"},
    "PINX": {"name": "OTC Pink", "short": "PINK", "city": "New York"},
}


# =============================================================================
# European Exchanges
# =============================================================================

EUROPEAN_EXCHANGES: dict[str, ExchangeInfo] = {
    # UK
    "XLON": {"name": "London Stock Exchange", "short": "LSE", "country": "GB", "city": "London"},
    "XLME": {"name": "London Metal Exchange", "short": "LME", "country": "GB", "city": "London"},
    "AIMX": {"name": "AIM (Alternative Investment Market)", "short": "AIM", "country": "GB", "city": "London"},
    "TRQX": {"name": "Turquoise", "short": "TQ", "country": "GB", "city": "London"},
    "CHIX": {"name": "Chi-X Europe", "short": "CHI-X", "country": "GB", "city": "London"},
    "BATE": {"name": "Cboe Europe - BXE", "short": "BATE", "country": "GB", "city": "London"},
    "AQEU": {"name": "Aquis Exchange", "short": "AQXE", "country": "GB", "city": "London"},
    # Germany
    "XETR": {"name": "Xetra", "short": "XETRA", "country": "DE", "city": "Frankfurt"},
    "XFRA": {"name": "Frankfurt Stock Exchange", "short": "FRA", "country": "DE", "city": "Frankfurt"},
    "XBER": {"name": "Berlin Stock Exchange", "short": "BER", "country": "DE", "city": "Berlin"},
    "XMUN": {"name": "Munich Stock Exchange", "short": "MUN", "country": "DE", "city": "Munich"},
    "XHAM": {"name": "Hamburg Stock Exchange", "short": "HAM", "country": "DE", "city": "Hamburg"},
    "XHAN": {"name": "Hanover Stock Exchange", "short": "HAN", "country": "DE", "city": "Hanover"},
    "XDUS": {"name": "Dusseldorf Stock Exchange", "short": "DUS", "country": "DE", "city": "Dusseldorf"},
    "XSTU": {"name": "Stuttgart Stock Exchange", "short": "STU", "country": "DE", "city": "Stuttgart"},
    # France
    "XPAR": {"name": "Euronext Paris", "short": "PAR", "country": "FR", "city": "Paris"},
    "ALXP": {"name": "Alternext Paris", "short": "ALXP", "country": "FR", "city": "Paris"},
    "XMLI": {"name": "Euronext Growth Paris", "short": "MLPA", "country": "FR", "city": "Paris"},
    # Netherlands
    "XAMS": {"name": "Euronext Amsterdam", "short": "AMS", "country": "NL", "city": "Amsterdam"},
    "ALXA": {"name": "Alternext Amsterdam", "short": "ALXA", "country": "NL", "city": "Amsterdam"},
    # Belgium
    "XBRU": {"name": "Euronext Brussels", "short": "BRU", "country": "BE", "city": "Brussels"},
    "ALXB": {"name": "Alternext Brussels", "short": "ALXB", "country": "BE", "city": "Brussels"},
    # Portugal
    "XLIS": {"name": "Euronext Lisbon", "short": "LIS", "country": "PT", "city": "Lisbon"},
    # Ireland
    "XDUB": {"name": "Euronext Dublin", "short": "DUB", "country": "IE", "city": "Dublin"},
    # Switzerland
    "XSWX": {"name": "SIX Swiss Exchange", "short": "SIX", "country": "CH", "city": "Zurich"},
    "XVTX": {"name": "SIX Structured Products", "short": "SIX-SP", "country": "CH", "city": "Zurich"},
    "XBRN": {"name": "Bern Stock Exchange", "short": "BRN", "country": "CH", "city": "Bern"},
    # Spain
    "XMAD": {"name": "Bolsa de Madrid", "short": "MAD", "country": "ES", "city": "Madrid"},
    "XMCE": {"name": "BME Spanish Exchanges", "short": "BME", "country": "ES", "city": "Madrid"},
    "XBAR": {"name": "Bolsa de Barcelona", "short": "BAR", "country": "ES", "city": "Barcelona"},
    "XMAB": {"name": "Bolsa de Bilbao", "short": "BIL", "country": "ES", "city": "Bilbao"},
    "XVAL": {"name": "Bolsa de Valencia", "short": "VAL", "country": "ES", "city": "Valencia"},
    # Italy
    "XMIL": {"name": "Borsa Italiana", "short": "MIL", "country": "IT", "city": "Milan"},
    "MTAA": {"name": "Borsa Italiana - MTA", "short": "MTA", "country": "IT", "city": "Milan"},
    "MTAH": {"name": "Borsa Italiana - MTA International", "short": "MTAI", "country": "IT", "city": "Milan"},
    "ETLX": {"name": "Borsa Italiana - ETFplus", "short": "ETF", "country": "IT", "city": "Milan"},
    # Nordic
    "XSTO": {"name": "Nasdaq Stockholm", "short": "STO", "country": "SE", "city": "Stockholm"},
    "XHEL": {"name": "Nasdaq Helsinki", "short": "HEL", "country": "FI", "city": "Helsinki"},
    "XCSE": {"name": "Nasdaq Copenhagen", "short": "CPH", "country": "DK", "city": "Copenhagen"},
    "XICE": {"name": "Nasdaq Iceland", "short": "ICE", "country": "IS", "city": "Reykjavik"},
    "XRIS": {"name": "Nasdaq Riga", "short": "RIS", "country": "LV", "city": "Riga"},
    "XTAL": {"name": "Nasdaq Tallinn", "short": "TAL", "country": "EE", "city": "Tallinn"},
    "XLIT": {"name": "Nasdaq Vilnius", "short": "LIT", "country": "LT", "city": "Vilnius"},
    "XOSL": {"name": "Oslo Bors", "short": "OSL", "country": "NO", "city": "Oslo"},
    "NOTC": {"name": "Norwegian OTC", "short": "NOTC", "country": "NO", "city": "Oslo"},
    # Austria/Central Europe
    "XWBO": {"name": "Wiener Borse", "short": "WBO", "country": "AT", "city": "Vienna"},
    "XWAR": {"name": "Warsaw Stock Exchange", "short": "WAR", "country": "PL", "city": "Warsaw"},
    "XPRA": {"name": "Prague Stock Exchange", "short": "PRA", "country": "CZ", "city": "Prague"},
    "XBUD": {"name": "Budapest Stock Exchange", "short": "BUD", "country": "HU", "city": "Budapest"},
    "XLJU": {"name": "Ljubljana Stock Exchange", "short": "LJU", "country": "SI", "city": "Ljubljana"},
    "XZAG": {"name": "Zagreb Stock Exchange", "short": "ZAG", "country": "HR", "city": "Zagreb"},
    "XBUL": {"name": "Bulgarian Stock Exchange", "short": "BUL", "country": "BG", "city": "Sofia"},
    "XBSE": {"name": "Bucharest Stock Exchange", "short": "BSE", "country": "RO", "city": "Bucharest"},
    # Greece/Cyprus/Turkey
    "XATH": {"name": "Athens Stock Exchange", "short": "ATH", "country": "GR", "city": "Athens"},
    "XCYS": {"name": "Cyprus Stock Exchange", "short": "CYS", "country": "CY", "city": "Nicosia"},
    "XIST": {"name": "Borsa Istanbul", "short": "IST", "country": "TR", "city": "Istanbul"},
    # Russia
    "MISX": {"name": "Moscow Exchange", "short": "MOEX", "country": "RU", "city": "Moscow"},
    "RTSX": {"name": "RTS Stock Exchange", "short": "RTS", "country": "RU", "city": "Moscow"},
}


# =============================================================================
# Asia-Pacific Exchanges
# =============================================================================

APAC_EXCHANGES: dict[str, ExchangeInfo] = {
    # Japan
    "XTKS": {"name": "Tokyo Stock Exchange", "short": "TSE", "country": "JP", "city": "Tokyo"},
    "XOSE": {"name": "Osaka Exchange", "short": "OSE", "country": "JP", "city": "Osaka"},
    "XJAS": {"name": "JASDAQ", "short": "JAS", "country": "JP", "city": "Tokyo"},
    "XNGO": {"name": "Nagoya Stock Exchange", "short": "NGO", "country": "JP", "city": "Nagoya"},
    "XSAP": {"name": "Sapporo Securities Exchange", "short": "SAP", "country": "JP", "city": "Sapporo"},
    "XFKA": {"name": "Fukuoka Stock Exchange", "short": "FKA", "country": "JP", "city": "Fukuoka"},
    "XPOM": {"name": "Tokyo PRO Market", "short": "TPM", "country": "JP", "city": "Tokyo"},
    # China
    "XSHG": {"name": "Shanghai Stock Exchange", "short": "SSE", "country": "CN", "city": "Shanghai"},
    "XSHE": {"name": "Shenzhen Stock Exchange", "short": "SZSE", "country": "CN", "city": "Shenzhen"},
    "SHSC": {"name": "Shanghai-Hong Kong Stock Connect", "short": "SHSC", "country": "CN", "city": "Shanghai"},
    "SZSC": {"name": "Shenzhen-Hong Kong Stock Connect", "short": "SZSC", "country": "CN", "city": "Shenzhen"},
    # Hong Kong
    "XHKG": {"name": "Hong Kong Stock Exchange", "short": "HKEX", "country": "HK", "city": "Hong Kong"},
    "XHKF": {"name": "Hong Kong Futures Exchange", "short": "HKFE", "country": "HK", "city": "Hong Kong"},
    # Taiwan
    "XTAI": {"name": "Taiwan Stock Exchange", "short": "TWSE", "country": "TW", "city": "Taipei"},
    "ROCO": {"name": "Taipei Exchange (GTSM)", "short": "TPEx", "country": "TW", "city": "Taipei"},
    # Korea
    "XKRX": {"name": "Korea Exchange", "short": "KRX", "country": "KR", "city": "Seoul"},
    "XKOS": {"name": "Korea Exchange - KOSDAQ", "short": "KOSDAQ", "country": "KR", "city": "Seoul"},
    # Singapore
    "XSES": {"name": "Singapore Exchange", "short": "SGX", "country": "SG", "city": "Singapore"},
    # Australia
    "XASX": {"name": "Australian Securities Exchange", "short": "ASX", "country": "AU", "city": "Sydney"},
    "CHIA": {"name": "Chi-X Australia", "short": "CXA", "country": "AU", "city": "Sydney"},
    "XNEC": {"name": "NSX Australia", "short": "NSX", "country": "AU", "city": "Sydney"},
    # New Zealand
    "XNZE": {"name": "New Zealand Exchange", "short": "NZX", "country": "NZ", "city": "Wellington"},
    # India
    "XNSE": {"name": "National Stock Exchange of India", "short": "NSE", "country": "IN", "city": "Mumbai"},
    "XBOM": {"name": "BSE India (Bombay)", "short": "BSE", "country": "IN", "city": "Mumbai"},
    # Southeast Asia
    "XKLS": {"name": "Bursa Malaysia", "short": "KLSE", "country": "MY", "city": "Kuala Lumpur"},
    "XBKK": {"name": "Stock Exchange of Thailand", "short": "SET", "country": "TH", "city": "Bangkok"},
    "XIDX": {"name": "Indonesia Stock Exchange", "short": "IDX", "country": "ID", "city": "Jakarta"},
    "XPHS": {"name": "Philippine Stock Exchange", "short": "PSE", "country": "PH", "city": "Manila"},
    "XSTC": {"name": "Ho Chi Minh Stock Exchange", "short": "HOSE", "country": "VN", "city": "Ho Chi Minh City"},
    "HSTC": {"name": "Hanoi Stock Exchange", "short": "HNX", "country": "VN", "city": "Hanoi"},
}


# =============================================================================
# Americas Exchanges (outside US)
# =============================================================================

AMERICAS_EXCHANGES: dict[str, ExchangeInfo] = {
    # Canada
    "XTSE": {"name": "Toronto Stock Exchange", "short": "TSX", "country": "CA", "city": "Toronto"},
    "XTSX": {"name": "TSX Venture Exchange", "short": "TSXV", "country": "CA", "city": "Toronto"},
    "XCNQ": {"name": "Canadian Securities Exchange", "short": "CSE", "country": "CA", "city": "Toronto"},
    "NEOE": {"name": "NEO Exchange", "short": "NEO", "country": "CA", "city": "Toronto"},
    "XMOD": {"name": "Montreal Exchange", "short": "MX", "country": "CA", "city": "Montreal"},
    "PURE": {"name": "Pure Trading", "short": "PURE", "country": "CA", "city": "Toronto"},
    # Brazil
    "BVMF": {"name": "B3 (Brasil Bolsa Balcao)", "short": "B3", "country": "BR", "city": "Sao Paulo"},
    "XBSP": {"name": "BM&FBOVESPA", "short": "BOVESPA", "country": "BR", "city": "Sao Paulo"},
    # Mexico
    "XMEX": {"name": "Bolsa Mexicana de Valores", "short": "BMV", "country": "MX", "city": "Mexico City"},
    "BIVA": {"name": "BIVA (Bolsa Institucional)", "short": "BIVA", "country": "MX", "city": "Mexico City"},
    # Argentina
    "XBUE": {"name": "Buenos Aires Stock Exchange", "short": "BCBA", "country": "AR", "city": "Buenos Aires"},
    # Chile
    "XSGO": {"name": "Santiago Stock Exchange", "short": "BCS", "country": "CL", "city": "Santiago"},
    # Colombia
    "XBOG": {"name": "Colombian Securities Exchange", "short": "BVC", "country": "CO", "city": "Bogota"},
    # Peru
    "XLIM": {"name": "Lima Stock Exchange", "short": "BVL", "country": "PE", "city": "Lima"},
}


# =============================================================================
# Middle East / Africa Exchanges
# =============================================================================

MENA_EXCHANGES: dict[str, ExchangeInfo] = {
    # Middle East
    "XTAE": {"name": "Tel Aviv Stock Exchange", "short": "TASE", "country": "IL", "city": "Tel Aviv"},
    "XSAU": {"name": "Saudi Stock Exchange (Tadawul)", "short": "TADAWUL", "country": "SA", "city": "Riyadh"},
    "XDFM": {"name": "Dubai Financial Market", "short": "DFM", "country": "AE", "city": "Dubai"},
    "XADS": {"name": "Abu Dhabi Securities Exchange", "short": "ADX", "country": "AE", "city": "Abu Dhabi"},
    "DIFX": {"name": "NASDAQ Dubai", "short": "NDX", "country": "AE", "city": "Dubai"},
    "XKUW": {"name": "Kuwait Stock Exchange", "short": "KSE", "country": "KW", "city": "Kuwait City"},
    "XBAH": {"name": "Bahrain Bourse", "short": "BHB", "country": "BH", "city": "Manama"},
    "XMUS": {"name": "Muscat Securities Market", "short": "MSM", "country": "OM", "city": "Muscat"},
    "DSMD": {"name": "Qatar Stock Exchange", "short": "QSE", "country": "QA", "city": "Doha"},
    "XAMM": {"name": "Amman Stock Exchange", "short": "ASE", "country": "JO", "city": "Amman"},
    "XCAI": {"name": "Egyptian Exchange", "short": "EGX", "country": "EG", "city": "Cairo"},
    "XCAS": {"name": "Casablanca Stock Exchange", "short": "CSE", "country": "MA", "city": "Casablanca"},
    # Africa
    "XJSE": {"name": "Johannesburg Stock Exchange", "short": "JSE", "country": "ZA", "city": "Johannesburg"},
    "XNSA": {"name": "Nigerian Stock Exchange", "short": "NSE", "country": "NG", "city": "Lagos"},
    "XNAI": {"name": "Nairobi Securities Exchange", "short": "NSE", "country": "KE", "city": "Nairobi"},
    "XGHA": {"name": "Ghana Stock Exchange", "short": "GSE", "country": "GH", "city": "Accra"},
    "XBOT": {"name": "Botswana Stock Exchange", "short": "BSE", "country": "BW", "city": "Gaborone"},
    "XMAU": {"name": "Stock Exchange of Mauritius", "short": "SEM", "country": "MU", "city": "Port Louis"},
    "XZIM": {"name": "Zimbabwe Stock Exchange", "short": "ZSE", "country": "ZW", "city": "Harare"},
}


# =============================================================================
# Clearinghouses
# =============================================================================

US_CLEARINGHOUSES: dict[str, ClearinghouseInfo] = {
    "DTCC": {"name": "Depository Trust & Clearing Corporation", "short": "DTCC", "type": "holding"},
    "NSCC": {"name": "National Securities Clearing Corporation", "short": "NSCC", "type": "equity_clearing"},
    "DTC": {"name": "Depository Trust Company", "short": "DTC", "type": "depository"},
    "FICC": {"name": "Fixed Income Clearing Corporation", "short": "FICC", "type": "fixed_income"},
    "OCC": {"name": "Options Clearing Corporation", "short": "OCC", "type": "options_clearing"},
    "CME_CLEARING": {"name": "CME Clearing", "short": "CME-CLR", "type": "futures_clearing"},
    "ICE_CLEAR": {"name": "ICE Clear US", "short": "ICE-CLR", "type": "futures_clearing"},
    "ICE_CLEAR_CREDIT": {"name": "ICE Clear Credit", "short": "ICE-CRD", "type": "cds_clearing"},
    "LCH_US": {"name": "LCH.Clearnet US", "short": "LCH-US", "type": "swaps_clearing"},
}

GLOBAL_CLEARINGHOUSES: dict[str, ClearinghouseInfo] = {
    # Europe
    "LCH": {"name": "LCH.Clearnet", "short": "LCH", "country": "GB", "type": "multi_asset"},
    "EUREX_CLR": {"name": "Eurex Clearing", "short": "EUREX-CLR", "country": "DE", "type": "derivatives"},
    "ECC": {"name": "European Commodity Clearing", "short": "ECC", "country": "DE", "type": "commodity"},
    "EUROCLEAR": {"name": "Euroclear", "short": "EUROCLEAR", "country": "BE", "type": "depository"},
    "CLEARSTREAM": {"name": "Clearstream", "short": "CLEARSTREAM", "country": "LU", "type": "depository"},
    "SIX_XCLEAR": {"name": "SIX x-clear", "short": "X-CLEAR", "country": "CH", "type": "equity_clearing"},
    "CC&G": {"name": "Cassa di Compensazione e Garanzia", "short": "CC&G", "country": "IT", "type": "clearing"},
    # Asia
    "JSCC": {"name": "Japan Securities Clearing Corporation", "short": "JSCC", "country": "JP", "type": "clearing"},
    "JASDEC": {"name": "Japan Securities Depository Center", "short": "JASDEC", "country": "JP", "type": "depository"},
    "HKSCC": {"name": "Hong Kong Securities Clearing", "short": "HKSCC", "country": "HK", "type": "clearing"},
    "CCDC": {"name": "China Central Depository & Clearing", "short": "CCDC", "country": "CN", "type": "depository"},
    "SHCH": {"name": "Shanghai Clearing House", "short": "SHCH", "country": "CN", "type": "clearing"},
    "KSD": {"name": "Korea Securities Depository", "short": "KSD", "country": "KR", "type": "depository"},
    "CDSL": {"name": "Central Depository Services (India)", "short": "CDSL", "country": "IN", "type": "depository"},
    "NSDL": {"name": "National Securities Depository (India)", "short": "NSDL", "country": "IN", "type": "depository"},
    "CDP": {"name": "Central Depository (Singapore)", "short": "CDP", "country": "SG", "type": "depository"},
    "ASX_CLR": {"name": "ASX Clear", "short": "ASX-CLR", "country": "AU", "type": "clearing"},
}


# =============================================================================
# Vendor Code Mappings
# =============================================================================

# Bloomberg Feed Source to Exchange Mapping (2-letter codes)
BLOOMBERG_FEED_SOURCES: dict[str, str] = {
    # Americas
    "US": "United States (Composite)",
    "UN": "NYSE",
    "UQ": "NASDAQ",
    "UA": "NYSE Arca",
    "UV": "OTC Markets",
    "UP": "NYSE American",
    "UW": "Cboe",
    "CN": "Canada (Composite)",
    "CT": "Toronto Stock Exchange",
    "CV": "TSX Venture",
    "MM": "Mexico BMV",
    "BZ": "Brazil B3",
    # Europe
    "LN": "London Stock Exchange",
    "GY": "Germany (Xetra)",
    "GR": "Germany (Frankfurt)",
    "FP": "France (Euronext Paris)",
    "NA": "Netherlands (Euronext Amsterdam)",
    "BB": "Belgium (Euronext Brussels)",
    "PL": "Portugal (Euronext Lisbon)",
    "ID": "Ireland (Euronext Dublin)",
    "SW": "Switzerland (SIX)",
    "SM": "Spain (BME)",
    "IM": "Italy (Borsa Italiana)",
    "SS": "Sweden (Nasdaq Stockholm)",
    "FH": "Finland (Nasdaq Helsinki)",
    "DC": "Denmark (Nasdaq Copenhagen)",
    "NO": "Norway (Oslo Bors)",
    "AV": "Austria (Wiener Borse)",
    "PW": "Poland (Warsaw)",
    "CP": "Czech Republic (Prague)",
    "HB": "Hungary (Budapest)",
    "GA": "Greece (Athens)",
    "TI": "Turkey (Istanbul)",
    "RU": "Russia (MOEX)",
    # Asia-Pacific
    "JT": "Japan (Tokyo)",
    "JP": "Japan (Osaka)",
    "HK": "Hong Kong",
    "CH": "China (Shanghai)",
    "CZ": "China (Shenzhen)",
    "TT": "Taiwan",
    "KS": "Korea (KRX)",
    "KQ": "Korea (KOSDAQ)",
    "SP": "Singapore",
    "AU": "Australia (ASX)",
    "NZ": "New Zealand",
    "IN": "India (NSE)",
    "IB": "India (BSE)",
    "MK": "Malaysia",
    "TB": "Thailand",
    "IJ": "Indonesia",
    "PM": "Philippines",
    "VN": "Vietnam",
    # Middle East/Africa
    "IT": "Israel",
    "AB": "Saudi Arabia",
    "DU": "UAE (Dubai)",
    "UH": "UAE (Abu Dhabi)",
    "QD": "Qatar",
    "KC": "Kuwait",
    "SJ": "South Africa",
    "NL": "Nigeria",
}

# Thomson Exchange Codes (3-letter) to MIC mapping
THOMSON_EXCHANGE_CODES: dict[str, str] = {
    # Americas
    "NYS": "XNYS",
    "NAS": "XNAS",
    "ASE": "XASE",
    "ARC": "ARCX",
    "OTC": "OTCM",
    "TSE": "XTSE",
    "TOR": "XTSE",
    "CVE": "XTSX",
    "MEX": "XMEX",
    "SAO": "BVMF",
    "BUE": "XBUE",
    "SGO": "XSGO",
    # Europe
    "LSE": "XLON",
    "AIM": "AIMX",
    "ETR": "XETR",
    "FRA": "XFRA",
    "PAR": "XPAR",
    "AMS": "XAMS",
    "BRU": "XBRU",
    "LIS": "XLIS",
    "SWX": "XSWX",
    "MAD": "XMAD",
    "MIL": "XMIL",
    "STO": "XSTO",
    "HEX": "XHEL",
    "CPH": "XCSE",
    "OSL": "XOSL",
    "VIE": "XWBO",
    "WAR": "XWAR",
    "PRA": "XPRA",
    "BUD": "XBUD",
    "ATH": "XATH",
    "IST": "XIST",
    "MIC": "MISX",  # Moscow
    # Asia-Pacific
    "TYO": "XTKS",
    "OSA": "XOSE",
    "HKG": "XHKG",
    "SHH": "XSHG",
    "SHZ": "XSHE",
    "TAI": "XTAI",
    "KSC": "XKRX",
    "SES": "XSES",
    "ASX": "XASX",
    "NSI": "XNSE",  # India NSE
    "BSE": "XBOM",  # India BSE
    "KLS": "XKLS",
    "SET": "XBKK",
    "JKT": "XIDX",
    "PHS": "XPHS",
    # Middle East/Africa
    "TLV": "XTAE",
    "SAU": "XSAU",
    "DFM": "XDFM",
    "ADS": "XADS",
    "JNB": "XJSE",
    "CAI": "XCAI",
}

# FactSet Exchange Codes
FACTSET_EXCHANGE_CODES: dict[str, str] = {
    "NAS": "NASDAQ",
    "NYS": "NYSE",
    "LON": "London Stock Exchange",
    "SWX": "SIX Swiss Exchange",
    "HKG": "Hong Kong Stock Exchange",
    "KRX": "Korea Exchange",
    "BRU": "Euronext Brussels",
    "PAR": "Euronext Paris",
    "ASX": "Australian Securities Exchange",
    "MCE": "BME Spanish Exchanges",
    "ETR": "Xetra",
    "BSP": "B3 Sao Paulo",
    "TAI": "Taiwan Stock Exchange",
    "MIC": "Moscow Exchange",
    "TSE": "Toronto Stock Exchange",
    "MIL": "Borsa Italiana",
    "OSL": "Oslo Bors",
    "CSE": "Nasdaq Copenhagen",
    "SAU": "Saudi Stock Exchange",
    "TKS": "Tokyo Stock Exchange",
    "BOM": "BSE India",
    "BOG": "Colombia Exchange",
    "DUB": "Euronext Dublin",
    "OME": "Nasdaq Stockholm",
    "SES": "Singapore Exchange",
    "JSE": "Johannesburg Stock Exchange",
    "MEX": "Mexican Stock Exchange",
    "AMS": "Euronext Amsterdam",
    "FRA": "Frankfurt Stock Exchange",
    "DSMD": "Qatar Stock Exchange",
    "SHG": "Shanghai Stock Exchange",
    "HEL": "Nasdaq Helsinki",
    "KLS": "Bursa Malaysia",
    "BKK": "Stock Exchange of Thailand",
    "NSA": "Nigerian Stock Exchange",
    "JKT": "Indonesia Stock Exchange",
    "ADS": "Abu Dhabi Securities Exchange",
    "SGO": "Santiago Stock Exchange",
    "SHE": "Shenzhen Stock Exchange",
    "DFM": "Dubai Financial Market",
    "ASE": "NYSE American",
    "KUW": "Kuwait Stock Exchange",
    "PRA": "Prague Stock Exchange",
    "DIFX": "NASDAQ Dubai",
    "WAR": "Warsaw Stock Exchange",
    "LIS": "Euronext Lisbon",
    "PHS": "Philippine Stock Exchange",
    "WBO": "Wiener Borse",
    "IST": "Borsa Istanbul",
    "LIM": "Lima Stock Exchange",
    "ATH": "Athens Stock Exchange",
    "OTC": "US OTC Markets",
    "CAR": "Caracas Stock Exchange",
    "TAE": "Tel Aviv Stock Exchange",
    "KAR": "Pakistan Stock Exchange",
    "CAS": "Casablanca Stock Exchange",
    "STC": "Ho Chi Minh Stock Exchange",
    "BSE": "Bucharest Stock Exchange",
    "CAI": "Egyptian Exchange",
    "JAS": "JASDAQ",
    "ZAG": "Zagreb Stock Exchange",
    "BDA": "Bermuda Stock Exchange",
    "AMM": "Amman Stock Exchange",
    "NAI": "Nairobi Securities Exchange",
    "BUD": "Budapest Stock Exchange",
    "NZE": "New Zealand Exchange",
    "DHA": "Dhaka Stock Exchange",
    "BAH": "Bahrain Bourse",
    "LUX": "Luxembourg Stock Exchange",
    "BRV": "BRVM (West Africa)",
    "MUS": "Muscat Securities Market",
    "LJU": "Ljubljana Stock Exchange",
    "NSE": "National Stock Exchange of India",
}


# =============================================================================
# Derived Data & Helpers
# =============================================================================

# All MIC codes combined for validation
ALL_KNOWN_MICS: set[str] = (
    set(US_EQUITY_EXCHANGES.keys()) |
    set(US_OPTIONS_EXCHANGES.keys()) |
    set(US_FUTURES_EXCHANGES.keys()) |
    set(US_OTC_MARKETS.keys()) |
    set(EUROPEAN_EXCHANGES.keys()) |
    set(APAC_EXCHANGES.keys()) |
    set(AMERICAS_EXCHANGES.keys()) |
    set(MENA_EXCHANGES.keys())
)


def lookup_exchange_by_mic(mic: str) -> ExchangeInfo | None:
    """
    Look up exchange info by MIC code (returns dict for backward compatibility).
    
    Args:
        mic: Market Identifier Code (ISO 10383), case-insensitive.
        
    Returns:
        ExchangeInfo dict with name, short, city/country, or None if not found.
        
    Example:
        >>> lookup_exchange_by_mic("XNYS")
        {'name': 'New York Stock Exchange', 'short': 'NYSE', 'city': 'New York'}
        
    See Also:
        lookup_exchange_ref: Returns typed ExchangeRef with provenance.
    """
    mic_upper = mic.upper().strip()
    
    # Search through all exchange dicts
    for exchange_dict in [
        US_EQUITY_EXCHANGES,
        US_OPTIONS_EXCHANGES,
        US_FUTURES_EXCHANGES,
        US_OTC_MARKETS,
        EUROPEAN_EXCHANGES,
        APAC_EXCHANGES,
        AMERICAS_EXCHANGES,
        MENA_EXCHANGES,
    ]:
        if mic_upper in exchange_dict:
            return exchange_dict[mic_upper]
    
    return None


def lookup_exchange_ref(
    mic: str,
    *,
    source: str = "entityspine_reference_data",
    as_of: date | None = None,
) -> ExchangeRef | None:
    """
    Look up exchange info by MIC code and return typed ExchangeRef with provenance.
    
    This is the preferred method when you need:
    - Typed access to fields
    - Provenance tracking (source, as_of, captured_at)
    - Conversion to dict via .to_dict()
    
    Args:
        mic: Market Identifier Code (ISO 10383), case-insensitive.
        source: Source name for provenance tracking.
        as_of: Date when this data was valid (defaults to None).
        
    Returns:
        ExchangeRef with name, short_name, city, country, and provenance,
        or None if not found.
        
    Example:
        >>> ref = lookup_exchange_ref("XNYS", source="ISO 10383")
        >>> ref.name
        'New York Stock Exchange'
        >>> ref.to_dict()
        {'name': 'New York Stock Exchange', 'short': 'NYSE', 'city': 'New York'}
    """
    mic_upper = mic.upper().strip()
    info = lookup_exchange_by_mic(mic_upper)
    
    if info is None:
        return None
    
    return ExchangeRef.from_dict(
        mic=mic_upper,
        data=info,
        source=source,
        as_of=as_of,
    )


def get_all_exchanges() -> dict[str, ExchangeInfo]:
    """
    Get all exchanges combined into a single dictionary.
    
    Returns:
        Dict mapping MIC → ExchangeInfo for all known exchanges.
    """
    result: dict[str, ExchangeInfo] = {}
    for exchange_dict in [
        US_EQUITY_EXCHANGES,
        US_OPTIONS_EXCHANGES,
        US_FUTURES_EXCHANGES,
        US_OTC_MARKETS,
        EUROPEAN_EXCHANGES,
        APAC_EXCHANGES,
        AMERICAS_EXCHANGES,
        MENA_EXCHANGES,
    ]:
        result.update(exchange_dict)
    return result


def get_all_exchange_refs(
    *,
    source: str = "entityspine_reference_data",
    as_of: date | None = None,
) -> list[ExchangeRef]:
    """
    Get all exchanges as typed ExchangeRef objects.
    
    Args:
        source: Source name for provenance tracking.
        as_of: Date when this data was valid.
        
    Returns:
        List of ExchangeRef objects for all known exchanges.
    """
    refs = []
    for mic, info in get_all_exchanges().items():
        refs.append(ExchangeRef.from_dict(
            mic=mic,
            data=info,
            source=source,
            as_of=as_of,
        ))
    return refs
