"""
Financial market infrastructure enums.

STDLIB ONLY - NO PYDANTIC.

Enums for modeling exchanges, broker-dealers, clearinghouses,
trading venues, and market participants.

Based on analysis of:
- Thomson Reuters OpenPermID (421 exchange codes, 293 MICs)
- Bloomberg BBUID (258 feed sources)
- FactSet (128 exchanges)
- Interactive Brokers (69 exchanges)
- ISO 10383 MIC codes

v2.3.1 - Initial version
v2.3.2 - Added VenueKind, MicSource, expanded ExchangeType
"""

from enum import Enum


# =============================================================================
# Venue Classification (v2.3.2)
# =============================================================================


class VenueKind(str, Enum):
    """
    High-level classification of market venues and infrastructure.
    
    More granular than ExchangeType; used for cross-asset venue modeling.
    Maps to Bronze/Silver/Gold data layers.
    
    Categories:
    - TRADING: Where securities/instruments trade
    - POST_TRADE: Clearing, settlement, custody
    - REPORTING: Trade/transaction reporting
    - REFERENCE: Index/benchmark providers
    """
    
    # === Trading Venues ===
    STOCK_EXCHANGE = "stock_exchange"           # Traditional stock exchange (NYSE, LSE)
    OPTIONS_EXCHANGE = "options_exchange"       # Options trading (CBOE, ISE)
    FUTURES_EXCHANGE = "futures_exchange"       # Futures/derivatives (CME, ICE)
    COMMODITY_EXCHANGE = "commodity_exchange"   # Physical commodities
    
    # Electronic venues
    ECN = "ecn"                                 # Electronic Communication Network
    ATS = "ats"                                 # Alternative Trading System
    DARK_POOL = "dark_pool"                     # Non-displayed liquidity
    MTF = "mtf"                                 # Multilateral Trading Facility (EU)
    OTF = "otf"                                 # Organized Trading Facility (EU)
    PTS = "pts"                                 # Proprietary Trading System (Japan)
    SI = "si"                                   # Systematic Internaliser (EU)
    
    # FX/Rates venues
    FX_ECN = "fx_ecn"                           # FX ECN (EBS, Reuters Matching)
    FX_PLATFORM = "fx_platform"                 # FX trading platform
    BOND_PLATFORM = "bond_platform"             # Electronic bond trading
    RATES_VENUE = "rates_venue"                 # Interest rate instruments
    
    # Swap execution
    SEF = "sef"                                 # Swap Execution Facility (US)
    SWAP_VENUE = "swap_venue"                   # Non-US swap venue
    
    # OTC markets
    OTC_MARKET = "otc_market"                   # OTC Markets (OTCQX, Pink)
    IDB = "idb"                                 # Inter-Dealer Broker
    
    # Digital assets
    CRYPTO_EXCHANGE = "crypto_exchange"         # Cryptocurrency exchange
    DIGITAL_ASSET_PLATFORM = "digital_asset_platform"
    
    # === Post-Trade Infrastructure ===
    CCP = "ccp"                                 # Central Counterparty
    CLEARING_HOUSE = "clearing_house"           # Clearing organization
    CSD = "csd"                                 # Central Securities Depository
    ICSD = "icsd"                               # International CSD (Euroclear, Clearstream)
    CUSTODIAN = "custodian"                     # Custody services
    
    # === Payment Systems ===
    RTGS = "rtgs"                               # Real-Time Gross Settlement
    PAYMENT_SYSTEM = "payment_system"           # Payment infrastructure
    
    # === Reporting Infrastructure ===
    TRF = "trf"                                 # Trade Reporting Facility
    APA = "apa"                                 # Approved Publication Arrangement (EU)
    ARM = "arm"                                 # Approved Reporting Mechanism (EU)
    TRADE_REPOSITORY = "trade_repository"       # Derivatives trade repository
    SDR = "sdr"                                 # Swap Data Repository
    
    # === Reference Data Providers ===
    INDEX_PROVIDER = "index_provider"           # Index calculation (S&P, MSCI)
    BENCHMARK_ADMIN = "benchmark_admin"         # Benchmark administrator
    PRICING_SERVICE = "pricing_service"         # Valuation/pricing
    
    # === Market Operators ===
    MARKET_OPERATOR = "market_operator"         # Exchange group/operator
    SRO = "sro"                                 # Self-Regulatory Organization
    
    OTHER = "other"


class MicSource(str, Enum):
    """
    Source/provenance of MIC code data.
    
    Used to track where venue reference data originated.
    """
    
    CURATED = "curated"           # Hand-maintained in major_venues.py
    ISO10383_BULK = "iso10383"    # Bulk ISO 10383 download
    VENDOR_INFERRED = "vendor"    # Inferred from vendor code mapping
    REGULATORY = "regulatory"      # From regulatory filings (SEC, ESMA)
    EXCHANGE_DIRECT = "exchange"   # Direct from exchange
    MANUAL = "manual"              # Manual entry
    UNKNOWN = "unknown"


class ExchangeType(str, Enum):
    """
    Type of securities exchange or trading venue.
    
    Based on SEC/FINRA classifications and MiFID II venue categories.
    """
    
    # Primary exchanges (registered with SEC as national securities exchange)
    NATIONAL_SECURITIES_EXCHANGE = "national_securities_exchange"  # NYSE, NASDAQ
    REGIONAL_EXCHANGE = "regional_exchange"  # Historical: Boston, Philadelphia, Chicago
    
    # Alternative trading systems
    ATS = "ats"  # Alternative Trading System (dark pools, ECNs)
    ECN = "ecn"  # Electronic Communication Network
    DARK_POOL = "dark_pool"  # Non-displayed liquidity pool
    
    # Derivatives exchanges
    OPTIONS_EXCHANGE = "options_exchange"  # CBOE, ISE, PHLX
    FUTURES_EXCHANGE = "futures_exchange"  # CME, ICE, NYMEX
    DERIVATIVES_EXCHANGE = "derivatives_exchange"  # Combined derivatives
    
    # Fixed income & money markets
    BOND_EXCHANGE = "bond_exchange"  # Bond trading platforms
    MONEY_MARKET = "money_market"  # Money market instruments
    
    # OTC markets
    OTC_MARKET = "otc_market"  # OTC Markets (OTCQX, OTCQB, Pink)
    INTER_DEALER_BROKER = "inter_dealer_broker"  # IDB for institutional
    
    # European venue types (MiFID II)
    MTF = "mtf"  # Multilateral Trading Facility
    OTF = "otf"  # Organized Trading Facility
    SI = "si"  # Systematic Internaliser
    
    # Asian venue types
    PTS = "pts"  # Proprietary Trading System (Japan)
    
    # Commodities
    COMMODITY_EXCHANGE = "commodity_exchange"  # Physical commodities
    
    # Crypto/Digital
    DIGITAL_ASSET_EXCHANGE = "digital_asset_exchange"
    
    # Trade reporting
    TRADE_REPORTING_FACILITY = "trade_reporting_facility"  # FINRA TRF
    APA = "apa"  # Approved Publication Arrangement (EU)
    
    # Indices
    INDEX_PROVIDER = "index_provider"  # S&P, MSCI, FTSE
    
    OTHER = "other"


class ExchangeStatus(str, Enum):
    """Operational status of an exchange."""
    
    ACTIVE = "active"
    SUSPENDED = "suspended"
    MERGED = "merged"
    DEREGISTERED = "deregistered"
    DEFUNCT = "defunct"


class AssetClass(str, Enum):
    """
    Asset classes traded on an exchange or by a broker-dealer.
    """
    
    EQUITY = "equity"
    FIXED_INCOME = "fixed_income"
    OPTIONS = "options"
    FUTURES = "futures"
    FX = "fx"
    COMMODITIES = "commodities"
    CRYPTO = "crypto"
    STRUCTURED_PRODUCTS = "structured_products"
    MONEY_MARKET = "money_market"
    OTHER = "other"


class BrokerDealerType(str, Enum):
    """
    Type of broker-dealer registration.
    
    Based on FINRA/SEC broker-dealer categories.
    """
    
    # Primary classifications
    FULL_SERVICE = "full_service"  # Full-service broker-dealer
    DISCOUNT = "discount"  # Discount/online broker
    INTRODUCING = "introducing"  # Introduces customers to clearing firm
    CLEARING = "clearing"  # Provides clearing services
    SELF_CLEARING = "self_clearing"  # Clears own trades
    
    # Specialized
    PRIME_BROKER = "prime_broker"  # Prime brokerage services
    INSTITUTIONAL = "institutional"  # Institutional-only
    RETAIL = "retail"  # Retail-focused
    
    # Market making
    MARKET_MAKER = "market_maker"  # OTC/exchange market maker
    SPECIALIST = "specialist"  # Exchange specialist/DMM
    WHOLESALER = "wholesaler"  # Wholesale market maker (PFOF)
    
    # Other
    MUNICIPAL = "municipal"  # Municipal securities dealer
    GOVERNMENT = "government"  # Government securities dealer
    INVESTMENT_BANK = "investment_bank"  # Investment banking
    PROPRIETARY = "proprietary"  # Proprietary trading
    
    OTHER = "other"


class BrokerDealerStatus(str, Enum):
    """
    Registration status of a broker-dealer entity lifecycle.
    
    USE THIS ONLY for the broker-dealer entity itself.
    For memberships, use MembershipStatus.
    For registrations, use RegistrationStatus.
    """
    
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    REVOKED = "revoked"
    WITHDRAWN = "withdrawn"
    EXPELLED = "expelled"  # FINRA expulsion


class MembershipStatus(str, Enum):
    """
    Status of exchange or clearing membership.
    
    Separate from BrokerDealerStatus because a BD can be ACTIVE
    but have a SUSPENDED membership on a particular exchange.
    
    Used by:
    - ExchangeMembership.status
    - ClearingMembership.status
    - MarketParticipant.status
    """
    
    ACTIVE = "active"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"
    PENDING = "pending"
    RESTRICTED = "restricted"  # Active but with limitations


class RegistrationStatus(str, Enum):
    """
    Status of a regulatory registration.
    
    Separate from BrokerDealerStatus because registrations have
    their own lifecycle (can be approved, pending, deficient).
    
    Used by:
    - BrokerDealerRegistration.status
    """
    
    ACTIVE = "active"
    PENDING = "pending"
    APPROVED = "approved"  # Synonym for active in some contexts
    DEFICIENT = "deficient"  # Missing required filings
    SUSPENDED = "suspended"
    REVOKED = "revoked"
    WITHDRAWN = "withdrawn"
    EXPIRED = "expired"


class ClearingStatus(str, Enum):
    """
    Operational status of a clearinghouse entity.
    
    Note: For clearing MEMBERSHIP status, use MembershipStatus.
    This enum is for the clearinghouse entity itself.
    """
    
    ACTIVE = "active"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"


class ClearinghouseType(str, Enum):
    """
    Type of clearing organization.
    """
    
    # US clearing
    CENTRAL_COUNTERPARTY = "central_counterparty"  # CCP
    CLEARING_AGENCY = "clearing_agency"  # SEC-registered
    DERIVATIVES_CLEARING = "derivatives_clearing"  # DCO (CFTC)
    
    # Depository
    SECURITIES_DEPOSITORY = "securities_depository"  # DTC, Euroclear
    
    # Payment systems
    PAYMENT_SYSTEM = "payment_system"  # FedWire, CHIPS
    
    OTHER = "other"


class MarketParticipantType(str, Enum):
    """
    Type of market participant.
    
    Entities that participate in securities markets beyond
    standard broker-dealers.
    """
    
    # Registered entities
    BROKER_DEALER = "broker_dealer"
    INVESTMENT_ADVISER = "investment_adviser"
    TRANSFER_AGENT = "transfer_agent"
    CUSTODIAN = "custodian"
    
    # Specialized participants
    MARKET_MAKER = "market_maker"
    DESIGNATED_MARKET_MAKER = "designated_market_maker"  # NYSE DMM
    LEAD_MARKET_MAKER = "lead_market_maker"  # Options
    SPECIALIST = "specialist"
    FLOOR_BROKER = "floor_broker"
    FLOOR_TRADER = "floor_trader"
    
    # Institutional
    QUALIFIED_INSTITUTIONAL_BUYER = "qib"  # Rule 144A
    ACCREDITED_INVESTOR = "accredited_investor"
    
    # SROs and infrastructure
    EXCHANGE = "exchange"
    CLEARING_MEMBER = "clearing_member"
    SRO = "sro"  # Self-regulatory organization
    
    OTHER = "other"


class RegistrationType(str, Enum):
    """
    Type of regulatory registration.
    """
    
    # SEC registrations
    SEC_BROKER_DEALER = "sec_broker_dealer"
    SEC_INVESTMENT_ADVISER = "sec_investment_adviser"
    SEC_TRANSFER_AGENT = "sec_transfer_agent"
    SEC_EXCHANGE = "sec_exchange"
    SEC_CLEARING_AGENCY = "sec_clearing_agency"
    SEC_ATS = "sec_ats"
    
    # FINRA
    FINRA_MEMBER = "finra_member"
    
    # CFTC
    CFTC_FCM = "cftc_fcm"  # Futures Commission Merchant
    CFTC_IB = "cftc_ib"  # Introducing Broker
    CFTC_CPO = "cftc_cpo"  # Commodity Pool Operator
    CFTC_CTA = "cftc_cta"  # Commodity Trading Advisor
    CFTC_DCM = "cftc_dcm"  # Designated Contract Market
    CFTC_DCO = "cftc_dco"  # Derivatives Clearing Organization
    
    # NFA
    NFA_MEMBER = "nfa_member"
    
    # State
    STATE_BROKER_DEALER = "state_broker_dealer"
    STATE_INVESTMENT_ADVISER = "state_investment_adviser"
    
    # International
    FCA_AUTHORIZED = "fca_authorized"  # UK
    MAS_LICENSED = "mas_licensed"  # Singapore
    SFC_LICENSED = "sfc_licensed"  # Hong Kong
    
    OTHER = "other"


class TradingSessionType(str, Enum):
    """Type of trading session."""
    
    PRE_MARKET = "pre_market"
    REGULAR = "regular"
    AFTER_HOURS = "after_hours"
    CONTINUOUS = "continuous"  # 24/7
    AUCTION = "auction"  # Opening/closing auction


class OrderType(str, Enum):
    """Type of order flow."""
    
    RETAIL = "retail"
    INSTITUTIONAL = "institutional"
    ALGORITHMIC = "algorithmic"
    HIGH_FREQUENCY = "high_frequency"
    MARKET_MAKER = "market_maker"


class MembershipType(str, Enum):
    """Type of exchange or clearing membership."""
    
    # Exchange memberships
    FULL_MEMBER = "full_member"
    ASSOCIATE_MEMBER = "associate_member"
    TRADING_MEMBER = "trading_member"
    CLEARING_MEMBER = "clearing_member"
    
    # Clearing memberships
    GENERAL_CLEARING_MEMBER = "gcm"
    INDIVIDUAL_CLEARING_MEMBER = "icm"
    DIRECT_CLEARING_MEMBER = "dcm"
    
    # Sponsored access
    SPONSORED_ACCESS = "sponsored_access"
    DIRECT_MARKET_ACCESS = "dma"
    
    OTHER = "other"
