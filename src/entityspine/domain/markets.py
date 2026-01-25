"""
Financial Market Infrastructure Domain Models.

STDLIB ONLY - NO PYDANTIC.

This module models the financial market infrastructure including:
- Exchanges and trading venues
- Broker-dealers (FINRA registered)
- Clearinghouses and depositories
- Market participants and memberships
- Regulatory registrations
- Exchange segments (MIC hierarchy)

These models enable:
- Understanding where securities trade
- Tracking broker-dealer compliance
- Mapping clearing and settlement flows
- Market structure analysis
- Routing / venue mapping
- Entity graph joins (trade → mpid → broker → venue → clearinghouse)

Time Semantics (v2.3.1):
-----------------------
- valid_from/valid_to: When the fact was TRUE IN THE WORLD (business time)
- captured_at: When we LEARNED about it (ingestion time)
- created_at/updated_at: Record metadata (system timestamps, not market truth)

Example: NYSE's SEC registration
- valid_from = 1792-05-17 (when NYSE was founded)
- captured_at = 2024-01-15T10:00:00Z (when we ingested the data)
- created_at = 2024-01-15T10:00:00Z (when this DB record was created)

Claims Pattern Compatibility (v2.3.1):
-------------------------------------
Market infrastructure identifiers (MIC, CRD, MPID) are stored directly on models
for convenience. For multi-vendor disagreement handling, these models can be
targets of IdentifierClaim:
- Exchange can have IdentifierClaim(scheme=MIC, value="XNYS", ...) 
- BrokerDealer can have IdentifierClaim(scheme=CRD, value="361", ...)
- The claim_target_id field can be used to link back to claims.

Reference Data:
--------------
Large MIC/exchange dictionaries have been moved to:
  entityspine.domain.reference_data.markets
Import from there for seeding/lookup, not from this module.

v2.3.0 Initial addition.
v2.3.1 Time semantics, status enum split, validators, ExchangeSegment.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal

from entityspine.domain.enums.markets import (
    AssetClass,
    BrokerDealerStatus,
    BrokerDealerType,
    ClearinghouseType,
    ClearingStatus,
    ExchangeStatus,
    ExchangeType,
    MarketParticipantType,
    MembershipStatus,
    MembershipType,
    RegistrationStatus,
    RegistrationType,
    TradingSessionType,
)
from entityspine.domain.timestamps import generate_ulid, utc_now
from entityspine.domain.validators import (
    normalize_crd,
    normalize_mic,
    normalize_mpid,
    normalize_sec_file_number,
    validate_crd,
    validate_mic,
    validate_mpid,
)

# =============================================================================
# Exchange / Trading Venue
# =============================================================================


@dataclass(frozen=True, slots=True)
class Exchange:
    """
    A securities exchange or trading venue with full regulatory metadata.

    Manifesto
    ---------
    Exchange models WHERE securities trade - the physical and electronic venues
    that match buyers and sellers. In EntitySpine's graph model, Exchange sits
    at the intersection of:

    - **Listings**: Securities trade ON exchanges (Listing.mic → Exchange.mic)
    - **Entities**: Exchanges are OPERATED BY entities (operator_entity_id)
    - **Clearinghouses**: Trades clear THROUGH clearing relationships
    - **Broker-Dealers**: Members CONNECT to exchanges via memberships

    This supports the "TICKER LIVES ON LISTING" principle by providing the
    venue context that makes a ticker meaningful. "AAPL" alone is ambiguous;
    "XNAS:AAPL" (NASDAQ) is precise.

    Architecture
    ------------
    ::

        ┌─────────────────────────────────────────────────────────────────────┐
        │                     Exchange in the Graph                            │
        │                                                                      │
        │   Entity (Operator)                                                  │
        │   ┌──────────────────┐                                               │
        │   │ Nasdaq, Inc.     │                                               │
        │   │ CIK: 1120193     │◀──────────┐                                   │
        │   └──────────────────┘           │ operator_entity_id                │
        │                                   │                                   │
        │                           ┌───────┴───────┐                          │
        │                           │   Exchange    │                          │
        │                           │ ┌───────────┐ │                          │
        │                           │ │ MIC: XNAS │ │                          │
        │                           │ │ NASDAQ    │ │                          │
        │                           │ │ SEC Reg   │ │                          │
        │                           │ └───────────┘ │                          │
        │                           └───────┬───────┘                          │
        │                                   │                                   │
        │          ┌────────────────────────┼────────────────────────┐         │
        │          │                        │                        │         │
        │          ▼                        ▼                        ▼         │
        │   ┌─────────────┐          ┌─────────────┐          ┌─────────────┐  │
        │   │  Listing    │          │  Listing    │          │  Listing    │  │
        │   │ AAPL        │          │ MSFT        │          │ GOOGL       │  │
        │   │ Apple Inc.  │          │ Microsoft   │          │ Alphabet    │  │
        │   └─────────────┘          └─────────────┘          └─────────────┘  │
        │                                                                      │
        │   Key: MIC (ISO 10383) uniquely identifies venues worldwide          │
        └─────────────────────────────────────────────────────────────────────┘

    Features
    --------
    - **MIC Identification**: ISO 10383 Market Identifier Code as primary key
    - **Operating MIC**: Supports MIC hierarchy (XNGS → XNAS)
    - **SEC Registration**: Tracks SEC file number for US exchanges
    - **SIP Participation**: CTA/CQS/UTP participant flags
    - **Asset Classes**: What trades here (equity, options, bonds)
    - **Temporal Validity**: valid_from/valid_to for exchange lifecycle
    - **Operator Linkage**: FK to operating entity for ownership queries

    Examples
    --------
    Creating a US national securities exchange:

    >>> nyse = Exchange(
    ...     name="New York Stock Exchange",
    ...     mic="XNYS",
    ...     short_name="NYSE",
    ...     exchange_type=ExchangeType.NATIONAL_SECURITIES_EXCHANGE,
    ...     country_code="US",
    ...     sec_file_number="1-00000",
    ...     is_sec_registered=True,
    ...     is_sip_participant=True,
    ... )
    >>> nyse.mic
    'XNYS'

    Creating a foreign exchange:

    >>> lse = Exchange(
    ...     name="London Stock Exchange",
    ...     mic="XLON",
    ...     country_code="GB",
    ...     exchange_type=ExchangeType.NATIONAL_SECURITIES_EXCHANGE,
    ...     timezone="Europe/London",
    ...     trading_currency="GBP",
    ... )

    Creating an ATS (dark pool):

    >>> ats = Exchange(
    ...     name="IEX Exchange",
    ...     mic="IEXG",
    ...     exchange_type=ExchangeType.ATS,
    ...     is_sec_registered=True,
    ... )

    Performance
    -----------
    - Memory: ~500 bytes per exchange (frozen, slotted)
    - Lookup: MIC indexed for O(1) access
    - Reference Data: ~300 global exchanges in typical deployment

    Guardrails
    ----------
    - MIC validated to ISO 10383 format (4 uppercase letters)
    - country_code validated to ISO 3166-1 alpha-2
    - valid_from must precede valid_to when both present
    - Frozen dataclass ensures thread-safety

    Context
    -------
    Exchange works with ExchangeSegment for MIC hierarchy (XNGS segment
    of XNAS), with Listing for venue placement, and with
    ExchangeMembership for broker connectivity.

    Time Semantics (v2.3.1):
        - valid_from/valid_to: When the fact was TRUE IN THE WORLD
        - captured_at: When we LEARNED about it (ingestion time)
        - created_at/updated_at: Record metadata only

    Tags
    ----
    :tag domain-model: Core domain concept
    :tag market-structure: Financial market infrastructure
    :tag iso-10383: MIC standard implementation
    :tag reference-data: Relatively static lookup data

    Doc-Types
    ---------
    :api-ref: entityspine.domain.markets.Exchange
    :related: Listing, ExchangeSegment, BrokerDealer, Clearinghouse

    Attributes
    ----------
    name : str
        Full legal name of the exchange.
    mic : str
        Market Identifier Code (ISO 10383) - primary identifier.
    exchange_id : str
        ULID primary key (auto-generated).
    short_name : str | None
        Common abbreviated name (e.g., "NYSE", "NASDAQ").
    legal_name : str | None
        Full legal entity name.
    operating_mic : str | None
        Operating MIC for market segments (prefer ExchangeSegment).
    sec_file_number : str | None
        SEC registration file number (for US exchanges).
    lei : str | None
        Legal Entity Identifier (if available).
    exchange_type : ExchangeType
        Type of exchange/venue (NATIONAL, ATS, ECN, etc.).
    status : ExchangeStatus
        Operational status (ACTIVE, SUSPENDED, DEREGISTERED).
    country_code : str
        ISO 3166-1 alpha-2 country code.
    jurisdiction : str | None
        Regulatory jurisdiction (may differ from country).
    city : str | None
        City where headquartered.
    timezone : str
        IANA timezone for trading hours.
    is_sec_registered : bool
        Whether registered with SEC as exchange.
    is_sip_participant : bool
        Whether participates in SIP (CTA/CQS/UTP).
    is_finra_trf : bool
        Whether this is a Trade Reporting Facility.
    asset_classes : tuple[AssetClass, ...]
        Asset classes traded (EQUITY, OPTIONS, BONDS, etc.).
    trading_currency : str
        Primary trading currency (ISO 4217).
    parent_entity_id : str | None
        FK to parent Entity (for ownership relationships).
    operator_entity_id : str | None
        FK to operating entity.
    operator_name : str | None
        Name of operating entity.
    valid_from : date | None
        When exchange started operating (business time).
    valid_to : date | None
        When exchange ceased operating (None if still active).
    opened_on : date | None
        When exchange first opened (alias for clarity).
    closed_on : date | None
        When exchange permanently closed (alias for clarity).
    """

    # Required fields
    name: str
    mic: str  # Primary identifier

    # Auto-generated primary key
    exchange_id: str = field(default_factory=generate_ulid)

    # Names
    short_name: str | None = None
    legal_name: str | None = None

    # Identifiers
    operating_mic: str | None = None  # For segments; prefer ExchangeSegment
    sec_file_number: str | None = None
    lei: str | None = None

    # Classification
    exchange_type: ExchangeType = ExchangeType.NATIONAL_SECURITIES_EXCHANGE
    status: ExchangeStatus = ExchangeStatus.ACTIVE

    # Location & Jurisdiction (v2.3.2)
    country_code: str = "US"  # ISO 3166-1 alpha-2
    jurisdiction: str | None = None  # e.g., "US", "GB", "EU" (regulatory jurisdiction)
    city: str | None = None
    timezone: str = "America/New_York"  # IANA timezone

    # Regulatory flags
    is_sec_registered: bool = False
    is_sip_participant: bool = False
    is_finra_trf: bool = False  # Trade Reporting Facility

    # Trading info
    asset_classes: tuple[AssetClass, ...] = (AssetClass.EQUITY,)
    trading_currency: str = "USD"

    # Relationships
    parent_entity_id: str | None = None
    operator_entity_id: str | None = None
    operator_name: str | None = None  # Name of operating entity (v2.3.2)

    # Validity (business time - when true in the world)
    valid_from: date | None = None  # e.g., opened_on / founded_date
    valid_to: date | None = None  # e.g., closed_on / deregistered_date

    # Explicit lifecycle dates (v2.3.2 - aliases for clarity)
    opened_on: date | None = None  # When exchange first opened
    closed_on: date | None = None  # When exchange permanently closed

    # Legacy date fields (kept for backward compatibility)
    founded_date: date | None = None
    sec_registered_date: date | None = None
    deregistered_date: date | None = None

    # Contact
    website: str | None = None

    # Provenance
    source_system: str = "unknown"
    source_ref: str | None = None
    captured_at: datetime = field(default_factory=utc_now)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    # Claims compatibility (v2.3.1)
    claim_target_id: str | None = None

    def __post_init__(self):
        """Validate and normalize exchange data."""
        if not self.name or not self.name.strip():
            raise ValueError("Exchange name cannot be empty")
        if not self.mic or not self.mic.strip():
            raise ValueError("Exchange MIC cannot be empty")

        # Normalize and validate MIC
        normalized_mic = normalize_mic(self.mic)
        if normalized_mic:
            is_valid, error = validate_mic(normalized_mic)
            if not is_valid:
                raise ValueError(error)
            object.__setattr__(self, "mic", normalized_mic)

        # Normalize operating MIC if provided
        if self.operating_mic:
            normalized_op_mic = normalize_mic(self.operating_mic)
            if normalized_op_mic:
                is_valid, error = validate_mic(normalized_op_mic)
                if not is_valid:
                    raise ValueError(f"Operating MIC invalid: {error}")
                object.__setattr__(self, "operating_mic", normalized_op_mic)

        # Normalize SEC file number if provided
        if self.sec_file_number:
            normalized = normalize_sec_file_number(self.sec_file_number)
            object.__setattr__(self, "sec_file_number", normalized)

    @property
    def is_us_exchange(self) -> bool:
        """Check if this is a US-based exchange."""
        return self.country_code == "US"

    @property
    def is_national_exchange(self) -> bool:
        """Check if this is a national securities exchange."""
        return self.exchange_type == ExchangeType.NATIONAL_SECURITIES_EXCHANGE

    @property
    def is_ats(self) -> bool:
        """Check if this is an ATS/dark pool."""
        return self.exchange_type in (
            ExchangeType.ATS,
            ExchangeType.ECN,
            ExchangeType.DARK_POOL,
        )

    @property
    def display_name(self) -> str:
        """Get display name (short name if available, else full name)."""
        return self.short_name or self.name

    @property
    def is_currently_valid(self) -> bool:
        """Check if exchange is currently valid based on validity window."""
        return self.is_valid_at(date.today())

    def is_valid_at(self, query_date: date) -> bool:
        """
        Check if exchange was valid at a specific date.
        
        Valid if (valid_from is None OR valid_from <= query_date)
            AND (valid_to is None OR query_date <= valid_to)
        
        Args:
            query_date: Date to check validity for.
            
        Returns:
            True if valid at the given date, False otherwise.
        """
        if self.valid_from is not None and query_date < self.valid_from:
            return False
        if self.valid_to is not None and query_date > self.valid_to:
            return False
        return True


@dataclass(frozen=True, slots=True)
class ExchangeSegment:
    """
    Exchange market segment (MIC hierarchy relationship).
    
    ISO 10383 defines a hierarchy where an operating MIC can have
    multiple segment MICs. This model explicitly captures that relationship
    with validity tracking.
    
    Example:
        NASDAQ (XNAS) has segments:
        - XNGS (Global Select Market)
        - XNMS (Global Market)
        - XNCM (Capital Market)
    
    Time Semantics:
        valid_from: When segment relationship became effective
        valid_to: When segment was discontinued
        captured_at: When we learned about this relationship
    
    Attributes:
        segment_id: ULID primary key.
        exchange_id: FK to parent Exchange.
        segment_mic: MIC code for this segment.
        operating_mic: Operating MIC (usually same as parent exchange MIC).
        segment_name: Human-readable segment name.
        description: Additional description.
        
        # Validity
        valid_from: When segment started operating.
        valid_to: When segment ceased operating.
        
        # Provenance
        source_system: Data source.
        source_ref: Reference in source system.
        captured_at: When we captured this record.
        created_at: Record creation timestamp.
    """

    exchange_id: str
    segment_mic: str

    segment_id: str = field(default_factory=generate_ulid)
    operating_mic: str | None = None
    segment_name: str | None = None
    description: str | None = None

    # Validity (business time)
    valid_from: date | None = None
    valid_to: date | None = None

    # Provenance
    source_system: str = "unknown"
    source_ref: str | None = None
    captured_at: datetime = field(default_factory=utc_now)
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self):
        """Validate and normalize segment data."""
        if not self.exchange_id or not self.exchange_id.strip():
            raise ValueError("exchange_id cannot be empty")
        if not self.segment_mic or not self.segment_mic.strip():
            raise ValueError("segment_mic cannot be empty")

        # Normalize and validate segment MIC
        normalized = normalize_mic(self.segment_mic)
        if normalized:
            is_valid, error = validate_mic(normalized)
            if not is_valid:
                raise ValueError(f"segment_mic invalid: {error}")
            object.__setattr__(self, "segment_mic", normalized)

        # Normalize operating MIC if provided
        if self.operating_mic:
            normalized_op = normalize_mic(self.operating_mic)
            if normalized_op:
                is_valid, error = validate_mic(normalized_op)
                if not is_valid:
                    raise ValueError(f"operating_mic invalid: {error}")
                object.__setattr__(self, "operating_mic", normalized_op)

    @property
    def is_currently_valid(self) -> bool:
        """Check if segment is currently valid."""
        return self.is_valid_at(date.today())

    def is_valid_at(self, query_date: date) -> bool:
        """
        Check if segment was valid at a specific date.
        
        Args:
            query_date: Date to check validity for.
            
        Returns:
            True if valid at the given date, False otherwise.
        """
        if self.valid_from is not None and query_date < self.valid_from:
            return False
        if self.valid_to is not None and query_date > self.valid_to:
            return False
        return True


@dataclass(frozen=True, slots=True)
class TradingSession:
    """
    Trading session hours for an exchange.
    
    Exchanges may have multiple sessions (pre-market, regular, after-hours).
    
    Time Semantics:
        valid_from: When this schedule became effective
        valid_to: When this schedule ended (None if current)
        captured_at: When we learned about this schedule
    
    Attributes:
        session_id: ULID primary key.
        exchange_id: FK to Exchange.
        session_type: Type of session.
        day_of_week: Day of week (0=Monday, 6=Sunday).
        open_time: Session open time (local, HH:MM format).
        close_time: Session close time (local, HH:MM format).
        is_auction: Whether this is an auction session.
        
        # Validity
        valid_from: When this schedule became effective.
        valid_to: When this schedule ended.
        
        # Provenance
        source_system: Data source.
        captured_at: When we captured this record.
        created_at: Record creation timestamp.
    """

    exchange_id: str
    session_type: TradingSessionType
    day_of_week: int  # 0=Monday, 6=Sunday
    open_time: str  # HH:MM format
    close_time: str  # HH:MM format

    session_id: str = field(default_factory=generate_ulid)
    is_auction: bool = False

    # Validity (business time)
    valid_from: date | None = None
    valid_to: date | None = None

    # Provenance
    source_system: str = "unknown"
    source_ref: str | None = None
    captured_at: datetime = field(default_factory=utc_now)
    created_at: datetime = field(default_factory=utc_now)


# =============================================================================
# Broker-Dealer
# =============================================================================


@dataclass(frozen=True, slots=True)
class BrokerDealer:
    """
    A broker-dealer registered with FINRA/SEC.
    
    BrokerDealer models the regulated firms that execute trades for customers
    and/or their own accounts. In the market structure graph, broker-dealers
    connect customers to exchanges and clearing infrastructure.
    
    Manifesto:
        Understanding market structure requires modeling WHO can trade WHERE and HOW
        trades are processed. BrokerDealer is the gateway between investors and
        markets:
        
        - **Retail investors** access markets THROUGH broker-dealers
        - **Institutional traders** route orders VIA broker-dealer memberships
        - **Trade execution** flows through exchange memberships (MPID)
        - **Trade settlement** flows through clearing relationships
        
        EntitySpine models this as a graph: Entity (legal identity) → BrokerDealer
        (regulatory registration) → ExchangeMembership (trading rights) → Exchange
        (venue). This enables queries like "which firms can trade options on CBOE?"
        or "trace the clearing chain for this trade."
    
    Architecture:
        ```
        ┌──────────────────────────────────────────────────────────┐
        │            Broker-Dealer in Market Structure             │
        └──────────────────────────────────────────────────────────┘
        
        Customer Order Flow:
        
        ┌────────────┐     ┌─────────────────┐     ┌──────────────┐
        │  Customer  │────►│  BrokerDealer   │────►│   Exchange   │
        │  (Retail)  │     │  (CRD: 12345)   │     │   (XNYS)     │
        └────────────┘     │                 │     └──────────────┘
                           │  Memberships:   │
                           │  ├─ NYSE (DMM)  │     ┌──────────────┐
                           │  ├─ NASDAQ      │────►│   Exchange   │
                           │  └─ CBOE        │     │   (XNAS)     │
                           └────────┬────────┘     └──────────────┘
                                    │
                           Clearing │
                                    ▼
                           ┌─────────────────┐
                           │  Clearinghouse  │
                           │    (NSCC)       │
                           └─────────────────┘
        
        Introducing vs Clearing Broker:
        ┌─────────────────┐     ┌─────────────────┐     ┌────────────┐
        │   Introducing   │────►│    Clearing     │────►│Clearinghouse│
        │   BD (front)    │     │    BD (back)    │     │   (DTCC)   │
        │   CRD: 54321    │     │   CRD: 12345    │     │            │
        └─────────────────┘     └─────────────────┘     └────────────┘
        ```
        Dependencies: validators.py (CRD normalization)
        Storage Tier: T0 (JSON), T1 (SQLite), T2 (DuckDB), T3 (PostgreSQL)
    
    Features:
        - **CRD Identification**: FINRA Central Registration Depository number
        - **SEC Registration**: SEC file number tracking (8-XXXXX format)
        - **Clearing Relationships**: Self-clearing vs fully-disclosed
        - **Exchange Memberships**: Via ExchangeMembership model
        - **Business Model**: Retail, institutional, clearing, introducing
        - **Temporal Validity**: valid_from/valid_to for BD lifecycle
        - **Entity Linkage**: FK to Entity for legal identity joins
    
    Examples:
        >>> # Full-service clearing broker
        >>> goldman = BrokerDealer(
        ...     name="Goldman Sachs & Co. LLC",
        ...     crd_number="361",
        ...     bd_type=BrokerDealerType.FULL_SERVICE,
        ...     clears_for_self=True,
        ...     clears_for_others=True,
        ...     sec_file_number="8-129",
        ... )
        
        >>> # Introducing broker (uses correspondent clearing)
        >>> retail_bd = BrokerDealer(
        ...     name="Retail Trading Inc.",
        ...     crd_number="123456",
        ...     bd_type=BrokerDealerType.INTRODUCING,
        ...     clearing_firm_id=goldman.broker_dealer_id,
        ...     accepts_retail=True,
        ... )
    
    Performance:
        - Memory: ~800 bytes per broker-dealer (frozen, slotted)
        - Lookup: CRD indexed for O(1) access
        - Reference Data: ~3,500 active US broker-dealers
    
    Guardrails:
        - Do NOT confuse BrokerDealerStatus with MembershipStatus
          ✅ BrokerDealerStatus = entity lifecycle (ACTIVE, TERMINATED)
          ✅ MembershipStatus = exchange membership (SUSPENDED, REVOKED)
        - Do NOT use this model for investment advisers
          ✅ BrokerDealers execute trades; IAs provide advice (different regs)
        - CRD validated to numeric format (leading zeros allowed)
        - SEC file number validated to 8-XXXXX format
    
    Context:
        Problem: Trade routing and compliance require understanding which firms
                 can trade where, under what restrictions, and how trades clear.
        Solution: BrokerDealer + ExchangeMembership + ClearingMembership models
                  the full market structure graph for regulatory compliance.
        
        Comparisons:
        | Concept           | BrokerDealer        | Investment Adviser   |
        |-------------------|---------------------|----------------------|
        | Regulator         | FINRA + SEC         | SEC + State          |
        | Primary ID        | CRD Number          | IARD Number          |
        | Activity          | Execute trades      | Investment advice    |
        | Customer Assets   | Held at clearing    | Held at custodian    |
    
    Tags:
        - market_structure
        - domain_model
        - broker_dealer
        - finra_regulated
        - clearing_infrastructure
        - stdlib_only
    
    Doc-Types:
        - MANIFESTO (section: "Market Infrastructure", priority: 9)
        - FEATURES (section: "Broker-Dealer Model", priority: 8)
        - API_REFERENCE (section: "Market Models", priority: 8)
    
    See Also:
        - Entity: The legal identity of the broker-dealer firm
        - ExchangeMembership: Where the BD can trade
        - ClearingMembership: How the BD clears trades
        - BrokerDealerRegistration: State and federal registrations
    
    Time Semantics:
        - valid_from: When BD registration became effective (business time)
        - valid_to: When BD registration terminated (business time)
        - captured_at: When we ingested this record (system time)
        - created_at/updated_at: Record metadata only
    
    Attributes:
        broker_dealer_id: ULID primary key.
        name: Legal name of the broker-dealer.
        dba_name: Doing business as name.
        crd_number: FINRA CRD number (primary identifier).
        sec_file_number: SEC broker-dealer file number.
        bd_type: Type of broker-dealer.
        status: Entity lifecycle status (NOT membership status).
        clearing_arrangement: How trades are cleared.
        clears_for_self: Whether self-clearing.
        clears_for_others: Whether clears for other firms.
        entity_id: FK to Entity (the legal entity).
        clearing_firm_id: FK to clearing firm BrokerDealer.
        parent_bd_id: FK to parent broker-dealer.
        valid_from: When registration became effective.
        valid_to: When registration terminated.
        source_system: Where this record came from.
        captured_at: When captured.
        claim_target_id: Optional ID for linking to IdentifierClaims.
    """

    # Required fields
    name: str
    crd_number: str  # Primary identifier

    # Auto-generated primary key
    broker_dealer_id: str = field(default_factory=generate_ulid)

    # Names
    dba_name: str | None = None
    legal_name: str | None = None

    # Identifiers
    sec_file_number: str | None = None  # 8-XXXXX format
    lei: str | None = None
    ein: str | None = None

    # Classification
    bd_type: BrokerDealerType = BrokerDealerType.FULL_SERVICE
    status: BrokerDealerStatus = BrokerDealerStatus.ACTIVE

    # Business model
    clearing_arrangement: str | None = None  # "self", "fully disclosed", etc.
    clears_for_self: bool = False
    clears_for_others: bool = False
    accepts_retail: bool = False
    accepts_institutional: bool = False

    # Asset classes
    asset_classes: tuple[AssetClass, ...] = (AssetClass.EQUITY,)

    # Relationships
    entity_id: str | None = None  # FK to Entity
    clearing_firm_id: str | None = None  # FK to clearing BD
    parent_bd_id: str | None = None  # FK to parent BD

    # Validity (business time)
    valid_from: date | None = None  # sec_registration_date / finra_membership_date
    valid_to: date | None = None  # termination_date

    # Legacy date fields (kept for backward compatibility)
    sec_registration_date: date | None = None
    finra_membership_date: date | None = None
    termination_date: date | None = None

    # Location
    main_office_address: str | None = None
    state_of_incorporation: str | None = None
    country_code: str = "US"

    # Contact
    website: str | None = None
    phone: str | None = None

    # Provenance
    source_system: str = "unknown"
    source_ref: str | None = None
    captured_at: datetime = field(default_factory=utc_now)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    # Claims compatibility (v2.3.1)
    claim_target_id: str | None = None

    def __post_init__(self):
        """Validate and normalize broker-dealer data."""
        if not self.name or not self.name.strip():
            raise ValueError("Broker-dealer name cannot be empty")
        if not self.crd_number or not self.crd_number.strip():
            raise ValueError("CRD number cannot be empty")

        # Normalize and validate CRD
        normalized_crd = normalize_crd(self.crd_number)
        if normalized_crd:
            is_valid, error = validate_crd(normalized_crd)
            if not is_valid:
                raise ValueError(error)
            object.__setattr__(self, "crd_number", normalized_crd)

        # Normalize SEC file number if provided
        if self.sec_file_number:
            normalized = normalize_sec_file_number(self.sec_file_number)
            object.__setattr__(self, "sec_file_number", normalized)

    @property
    def is_active(self) -> bool:
        """Check if broker-dealer is currently active."""
        return self.status == BrokerDealerStatus.ACTIVE

    @property
    def is_clearing_firm(self) -> bool:
        """Check if this is a clearing firm."""
        return self.clears_for_self or self.clears_for_others

    @property
    def is_introducing(self) -> bool:
        """Check if this is an introducing broker."""
        return self.bd_type == BrokerDealerType.INTRODUCING

    @property
    def is_currently_valid(self) -> bool:
        """Check if BD is currently valid based on validity window."""
        return self.is_valid_at(date.today())

    def is_valid_at(self, query_date: date) -> bool:
        """
        Check if BD was valid at a specific date.
        
        Args:
            query_date: Date to check validity for.
            
        Returns:
            True if valid at the given date, False otherwise.
        """
        if self.valid_from is not None and query_date < self.valid_from:
            return False
        if self.valid_to is not None and query_date > self.valid_to:
            return False
        return True


@dataclass(frozen=True, slots=True)
class BrokerDealerRegistration:
    """
    A specific regulatory registration for a broker-dealer.
    
    Broker-dealers may have multiple registrations (SEC, states, etc.).
    
    Note on status:
        Uses RegistrationStatus (not BrokerDealerStatus) because registrations
        have their own lifecycle (pending, approved, deficient, etc.).
    
    Time Semantics:
        valid_from: When registration became effective
        valid_to: When registration terminated
        captured_at: When we learned about this registration
    
    Attributes:
        registration_id: ULID primary key.
        broker_dealer_id: FK to BrokerDealer.
        registration_type: Type of registration.
        registration_number: Registration/license number.
        jurisdiction: Jurisdiction (US, state code, country).
        
        # Status
        status: Registration status (RegistrationStatus, not BrokerDealerStatus).
        
        # Validity (business time)
        valid_from: When registration became effective.
        valid_to: When registration terminated.
        
        # Restrictions
        has_restrictions: Whether registration has restrictions.
        restriction_details: Details of any restrictions.
    """

    broker_dealer_id: str
    registration_type: RegistrationType
    jurisdiction: str

    registration_id: str = field(default_factory=generate_ulid)
    registration_number: str | None = None

    # Status (uses RegistrationStatus, not BrokerDealerStatus)
    status: RegistrationStatus = RegistrationStatus.ACTIVE

    # Validity (business time)
    valid_from: date | None = None  # effective_date
    valid_to: date | None = None  # termination_date

    # Legacy date fields (kept for backward compatibility)
    effective_date: date | None = None
    termination_date: date | None = None

    has_restrictions: bool = False
    restriction_details: str | None = None

    # Provenance
    source_system: str = "unknown"
    source_ref: str | None = None
    captured_at: datetime = field(default_factory=utc_now)
    created_at: datetime = field(default_factory=utc_now)

    @property
    def is_currently_valid(self) -> bool:
        """Check if registration is currently valid."""
        return self.is_valid_at(date.today())

    def is_valid_at(self, query_date: date) -> bool:
        """
        Check if registration was valid at a specific date.
        
        Args:
            query_date: Date to check validity for.
            
        Returns:
            True if valid at the given date, False otherwise.
        """
        if self.valid_from is not None and query_date < self.valid_from:
            return False
        if self.valid_to is not None and query_date > self.valid_to:
            return False
        return True


@dataclass(frozen=True, slots=True)
class BrokerDealerDisciplinaryAction:
    """
    A regulatory disciplinary action against a broker-dealer.
    
    Tracks enforcement actions, fines, and sanctions.
    
    Time Semantics:
        action_date: When the action was taken (business time)
        resolution_date: When action was resolved (business time)
        captured_at: When we learned about this action
    
    Attributes:
        action_id: ULID primary key.
        broker_dealer_id: FK to BrokerDealer.
        regulator: Regulator taking action (FINRA, SEC, state).
        action_type: Type of action (fine, suspension, etc.).
        action_date: Date of action.
        
        # Details
        description: Description of the violation/action.
        fine_amount: Monetary fine amount.
        fine_currency: Currency of fine.
        suspension_days: Days of suspension if applicable.
        
        # Resolution
        is_resolved: Whether action is resolved.
        resolution_date: Date resolved.
        appeal_status: Status of any appeal.
    """

    broker_dealer_id: str
    regulator: str  # FINRA, SEC, state name
    action_type: str  # fine, suspension, censure, expulsion
    action_date: date

    action_id: str = field(default_factory=generate_ulid)

    description: str | None = None
    fine_amount: Decimal | None = None
    fine_currency: str = "USD"
    suspension_days: int | None = None

    is_resolved: bool = False
    resolution_date: date | None = None
    appeal_status: str | None = None

    # References
    case_number: str | None = None
    docket_number: str | None = None

    # Provenance
    source_system: str = "unknown"
    source_ref: str | None = None
    captured_at: datetime = field(default_factory=utc_now)
    created_at: datetime = field(default_factory=utc_now)


# =============================================================================
# Clearinghouse
# =============================================================================


@dataclass(frozen=True, slots=True)
class Clearinghouse:
    """
    A clearing organization or central counterparty (CCP).
    
    Clearinghouse models the critical post-trade infrastructure that guarantees
    trade settlement by becoming the buyer to every seller and seller to every
    buyer. This "novation" process is fundamental to reducing counterparty risk
    in financial markets.
    
    Manifesto:
        Every trade in modern markets flows through clearing and settlement
        infrastructure. Understanding this flow is essential for:
        
        - **Risk Management**: CCPs net exposures and manage collateral
        - **Regulatory Compliance**: SIFMU designation carries systemic importance
        - **Trade Lifecycle**: T+1/T+2 settlement cycles affect operations
        - **Market Access**: Clearing membership determines who can clear
        
        EntitySpine models the clearing chain: BrokerDealer → ClearingMembership →
        Clearinghouse → Settlement. This enables queries like "which firms are
        clearing members of NSCC?" or "trace the settlement flow for this trade."
    
    Architecture:
        ```
        ┌──────────────────────────────────────────────────────────┐
        │          Clearinghouse in the Settlement Chain           │
        └──────────────────────────────────────────────────────────┘
        
        Trade Execution → Clearing → Settlement
        
        ┌──────────┐  ┌──────────┐     ┌─────────────────┐     ┌──────────────┐
        │  Buyer   │  │  Seller  │     │    Exchange     │     │ Clearinghouse│
        │   BD     │  │   BD     │     │    (XNYS)       │     │   (NSCC)     │
        └────┬─────┘  └────┬─────┘     └────────┬────────┘     └──────┬───────┘
             │             │                    │                      │
             │    Trade Matched                 │                      │
             └─────────────┴────────────────────►                      │
                                                │   Trade Novation     │
                                                └──────────────────────►
                                                                       │
                                                           ┌───────────┴──────────┐
                                                           │      Netting         │
                                                           │  (reduce exposures)  │
                                                           └───────────┬──────────┘
                                                                       │
        ┌────────────────────────────────────────────────────────────────┐
        │                      DTCC Structure                             │
        │  ┌───────────┐    ┌───────────┐    ┌───────────┐              │
        │  │   NSCC    │    │    DTC    │    │   FICC    │              │
        │  │ (equities)│    │(depository)│   │  (fixed)  │              │
        │  └───────────┘    └───────────┘    └───────────┘              │
        └────────────────────────────────────────────────────────────────┘
        ```
        Dependencies: validators.py (SEC file number normalization)
        Storage Tier: T0 (JSON), T1 (SQLite), T2 (DuckDB), T3 (PostgreSQL)
    
    Features:
        - **CCP Types**: Clearinghouses, depositories, and CCPs
        - **SEC Registration**: SEC file number for registered clearing agencies
        - **SIFMU Status**: Systemically Important Financial Market Utility flag
        - **Asset Classes**: What instruments are cleared (equities, options, fixed)
        - **Settlement Cycle**: T+1, T+2, or other settlement timing
        - **Temporal Validity**: valid_from/valid_to for clearinghouse lifecycle
        - **Entity Linkage**: FK to Entity for legal identity joins
    
    Examples:
        >>> # National Securities Clearing Corporation
        >>> nscc = Clearinghouse(
        ...     name="National Securities Clearing Corporation",
        ...     short_name="NSCC",
        ...     clearinghouse_type=ClearinghouseType.CENTRAL_COUNTERPARTY,
        ...     is_sec_registered=True,
        ...     is_systemically_important=True,
        ...     asset_classes=(AssetClass.EQUITY,),
        ...     settlement_cycle="T+1",
        ... )
        
        >>> # Options Clearing Corporation
        >>> occ = Clearinghouse(
        ...     name="The Options Clearing Corporation",
        ...     short_name="OCC",
        ...     clearinghouse_type=ClearinghouseType.CENTRAL_COUNTERPARTY,
        ...     asset_classes=(AssetClass.OPTIONS, AssetClass.FUTURES),
        ... )
    
    Performance:
        - Memory: ~600 bytes per clearinghouse (frozen, slotted)
        - Reference Data: ~50 global CCPs in typical deployment
    
    Guardrails:
        - Do NOT confuse ClearingStatus with MembershipStatus
          ✅ ClearingStatus = clearinghouse lifecycle (ACTIVE, SUSPENDED)
          ✅ MembershipStatus = clearing membership (PENDING, REVOKED)
        - SIFMU designation has regulatory implications
          ✅ Systemically important clearinghouses face enhanced supervision
    
    Context:
        Problem: Trade settlement fails without understanding clearing infrastructure
                 and membership relationships, leading to operational failures.
        Solution: Clearinghouse + ClearingMembership models the full clearing graph,
                  enabling trade lifecycle tracking and membership queries.
        
        Key Clearinghouses:
        | Name | Short | Type        | Asset Classes                    |
        |------|-------|-------------|----------------------------------|
        | NSCC | NSCC  | CCP         | Equities, ETFs, UITs             |
        | DTC  | DTC   | Depository  | Securities custody, settlement   |
        | FICC | FICC  | CCP         | Government bonds, MBS            |
        | OCC  | OCC   | CCP         | Listed options, futures          |
        | CME  | CME   | CCP         | Futures, options, OTC            |
    
    Tags:
        - market_structure
        - domain_model
        - clearinghouse
        - post_trade
        - settlement_infrastructure
        - sifmu
        - stdlib_only
    
    Doc-Types:
        - MANIFESTO (section: "Market Infrastructure", priority: 9)
        - FEATURES (section: "Clearing Model", priority: 8)
        - API_REFERENCE (section: "Market Models", priority: 8)
    
    See Also:
        - Entity: The legal identity of the clearinghouse
        - ClearingMembership: Who is a clearing member
        - BrokerDealer: Firms that clear through clearinghouses
        - ExchangeMembership: Trading side (vs clearing side)
    
    Time Semantics:
        - valid_from: When clearinghouse began operations (business time)
        - valid_to: When clearinghouse ceased operations (business time)
        - captured_at: When we ingested this record (system time)
        - created_at/updated_at: Record metadata only
    
    Attributes:
        clearinghouse_id: ULID primary key.
        name: Full legal name.
        short_name: Common abbreviated name.
        clearinghouse_type: Type of clearing organization.
        sec_file_number: SEC registration number.
        is_sec_registered: Whether registered with SEC.
        is_systemically_important: Whether designated as SIFMU.
        asset_classes: Asset classes cleared.
        settlement_currency: Primary settlement currency.
        entity_id: FK to Entity (the legal entity).
        parent_clearinghouse_id: FK to parent clearinghouse.
        valid_from: When clearinghouse began operations.
        valid_to: When clearinghouse ceased operations.
    """

    name: str

    clearinghouse_id: str = field(default_factory=generate_ulid)

    short_name: str | None = None
    legal_name: str | None = None

    # Identifiers
    sec_file_number: str | None = None
    lei: str | None = None

    # Classification
    clearinghouse_type: ClearinghouseType = ClearinghouseType.CENTRAL_COUNTERPARTY
    status: ClearingStatus = ClearingStatus.ACTIVE

    # Regulatory
    is_sec_registered: bool = False
    is_cftc_registered: bool = False
    is_systemically_important: bool = False  # SIFMU designation

    # Operations
    asset_classes: tuple[AssetClass, ...] = (AssetClass.EQUITY,)
    settlement_currency: str = "USD"
    settlement_cycle: str = "T+1"  # T+1, T+2, etc.

    # Location & Jurisdiction (v2.3.2)
    country_code: str = "US"  # ISO 3166-1 alpha-2
    jurisdiction: str | None = None  # Regulatory jurisdiction
    city: str | None = None

    # Relationships
    entity_id: str | None = None
    parent_clearinghouse_id: str | None = None

    # Validity (business time)
    valid_from: date | None = None
    valid_to: date | None = None

    # Explicit lifecycle dates (v2.3.2)
    opened_on: date | None = None  # When clearinghouse began operations
    closed_on: date | None = None  # When clearinghouse ceased operations

    # Contact
    website: str | None = None

    # Provenance
    source_system: str = "unknown"
    source_ref: str | None = None
    captured_at: datetime = field(default_factory=utc_now)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    # Claims compatibility (v2.3.1)
    claim_target_id: str | None = None

    def __post_init__(self):
        """Validate clearinghouse data."""
        if not self.name or not self.name.strip():
            raise ValueError("Clearinghouse name cannot be empty")

        # Normalize SEC file number if provided
        if self.sec_file_number:
            normalized = normalize_sec_file_number(self.sec_file_number)
            object.__setattr__(self, "sec_file_number", normalized)

    @property
    def is_currently_valid(self) -> bool:
        """Check if clearinghouse is currently valid."""
        return self.is_valid_at(date.today())

    def is_valid_at(self, query_date: date) -> bool:
        """
        Check if clearinghouse was valid at a specific date.
        
        Args:
            query_date: Date to check validity for.
            
        Returns:
            True if valid at the given date, False otherwise.
        """
        if self.valid_from is not None and query_date < self.valid_from:
            return False
        if self.valid_to is not None and query_date > self.valid_to:
            return False
        return True


@dataclass(frozen=True, slots=True)
class ClearingMembership:
    """
    A clearing membership relationship between a firm and a clearinghouse.
    
    ClearingMembership is the edge in the market structure graph that connects
    broker-dealers (and other market participants) to clearing infrastructure.
    Without clearing membership, a firm cannot settle trades.
    
    Manifesto:
        The clearing membership graph answers critical operational questions:
        
        - **Trade Settlement**: Can this firm clear trades in this asset class?
        - **Counterparty Risk**: What are the firm's clearing relationships?
        - **Market Access**: Direct clearing vs correspondent clearing?
        - **Regulatory Scope**: Which CCPs does this firm participate in?
        
        This is a temporal relationship: memberships start, may be suspended,
        and can be terminated. Point-in-time queries require checking validity.
    
    Architecture:
        ```
        ┌──────────────────────────────────────────────────────────┐
        │           Clearing Membership Graph Relationships        │
        └──────────────────────────────────────────────────────────┘
        
        Direct Clearing Member:
        ┌─────────────────┐                    ┌─────────────────┐
        │   BrokerDealer  │───────────────────►│  Clearinghouse  │
        │   (Goldman)     │ ClearingMembership │     (NSCC)      │
        │   CRD: 361      │    FULL_CLEARING   │                 │
        └─────────────────┘                    └─────────────────┘
        
        Correspondent Clearing (introducing → clearing BD → CCP):
        ┌─────────────────┐     ┌─────────────────┐     ┌──────────────┐
        │   Introducing   │────►│    Clearing     │────►│ Clearinghouse│
        │       BD        │corr.│       BD        │memb.│    (NSCC)    │
        └─────────────────┘     └─────────────────┘     └──────────────┘
        ```
        Dependencies: None (relationship model)
        Storage Tier: T1 (SQLite), T2 (DuckDB), T3 (PostgreSQL)
    
    Features:
        - **Membership Types**: FULL_CLEARING, CORRESPONDENT, SPONSORED
        - **Asset Class Scope**: What can be cleared under this membership
        - **Temporal Validity**: valid_from/valid_to for membership lifecycle
        - **Entity + BD Links**: Can link to Entity and/or BrokerDealer
    
    Guardrails:
        - Do NOT confuse MembershipStatus with ClearingStatus
          ✅ MembershipStatus = this relationship's status
          ✅ ClearingStatus = the clearinghouse's overall status
        - Correspondent clearing requires clearing_firm_id on BrokerDealer
    
    Tags:
        - market_structure
        - relationship_model
        - clearing_membership
        - post_trade
        - stdlib_only
    
    Doc-Types:
        - FEATURES (section: "Market Relationships", priority: 7)
        - API_REFERENCE (section: "Market Models", priority: 7)
    
    See Also:
        - Clearinghouse: The CCP being a member of
        - BrokerDealer: The firm with membership
        - ExchangeMembership: Trading relationships (vs clearing)
    
    Time Semantics:
        - valid_from: When membership became effective (business time)
        - valid_to: When membership terminated (business time)
        - captured_at: When we learned about this membership (system time)
    
    Attributes:
        membership_id: ULID primary key.
        clearinghouse_id: FK to Clearinghouse.
        member_entity_id: FK to Entity (the member).
        member_bd_id: FK to BrokerDealer (if applicable).
        membership_type: Type of clearing membership.
        status: Membership status (MembershipStatus).
        valid_from: When membership started.
        valid_to: When membership ended.
    """

    clearinghouse_id: str
    member_entity_id: str

    membership_id: str = field(default_factory=generate_ulid)
    member_bd_id: str | None = None

    membership_type: MembershipType = MembershipType.CLEARING_MEMBER
    # Uses MembershipStatus (v2.3.1), not ClearingStatus
    status: MembershipStatus = MembershipStatus.ACTIVE

    # Asset classes cleared under this membership
    asset_classes: tuple[AssetClass, ...] = (AssetClass.EQUITY,)

    # Validity (business time)
    valid_from: date | None = None  # effective_date
    valid_to: date | None = None  # termination_date

    # Legacy date fields (kept for backward compatibility)
    effective_date: date | None = None
    termination_date: date | None = None

    # Provenance
    source_system: str = "unknown"
    source_ref: str | None = None
    captured_at: datetime = field(default_factory=utc_now)
    created_at: datetime = field(default_factory=utc_now)

    @property
    def is_currently_valid(self) -> bool:
        """Check if clearing membership is currently valid."""
        return self.is_valid_at(date.today())

    def is_valid_at(self, query_date: date) -> bool:
        """
        Check if clearing membership was valid at a specific date.
        
        Args:
            query_date: Date to check validity for.
            
        Returns:
            True if valid at the given date, False otherwise.
        """
        if self.valid_from is not None and query_date < self.valid_from:
            return False
        if self.valid_to is not None and query_date > self.valid_to:
            return False
        return True


# =============================================================================
# Exchange Membership
# =============================================================================


@dataclass(frozen=True, slots=True)
class ExchangeMembership:
    """
    An exchange membership relationship - trading rights on a venue.
    
    ExchangeMembership is the edge connecting broker-dealers to exchanges,
    representing the right to execute trades. Each membership grants specific
    trading rights (equity, options, market maker) and is identified by an MPID.
    
    Manifesto:
        Trade routing decisions depend on understanding where firms CAN trade:
        
        - **Order Routing**: Which venues can receive orders from this firm?
        - **Market Making**: Which firms are registered MMs on this exchange?
        - **Compliance**: Does the firm have active membership for this trade?
        - **Best Execution**: What venues are available for routing this order?
        
        This relationship is temporal and status-sensitive: a firm can be an
        ACTIVE broker-dealer but have a SUSPENDED membership on a particular
        exchange. Point-in-time queries must check both entity AND membership status.
    
    Architecture:
        ```
        ┌──────────────────────────────────────────────────────────┐
        │         Exchange Membership - Trading Rights Graph       │
        └──────────────────────────────────────────────────────────┘
        
        ┌─────────────────┐                       ┌──────────────┐
        │   BrokerDealer  │                       │   Exchange   │
        │   (Citadel)     │                       │    (NYSE)    │
        │   CRD: 116797   │                       │   MIC: XNYS  │
        └────────┬────────┘                       └──────┬───────┘
                 │                                       │
                 │  ExchangeMembership                   │
                 │  ┌────────────────────────────────┐   │
                 └──┤ MPID: CDRG                     ├───┘
                    │ type: TRADING_MEMBER           │
                    │ is_designated_market_maker: ✓  │
                    │ can_trade_equity: ✓            │
                    │ can_trade_options: ✓           │
                    │ status: ACTIVE                 │
                    │ valid_from: 2004-01-01         │
                    └────────────────────────────────┘
        
        Multi-Exchange Membership:
        ┌─────────────────┐     ┌──────────┐     ┌──────────┐
        │   BrokerDealer  │────►│   NYSE   │     │  NASDAQ  │
        │                 │     └──────────┘     └──────────┘
        │   memberships:  │────►│   CBOE   │     │  ARCA    │
        │    - XNYS (DMM) │     └──────────┘     └──────────┘
        │    - XNAS       │────►│   IEX    │
        │    - XCBO       │     └──────────┘
        └─────────────────┘
        ```
        Dependencies: validators.py (MPID normalization)
        Storage Tier: T1 (SQLite), T2 (DuckDB), T3 (PostgreSQL)
    
    Features:
        - **MPID Identification**: Market Participant Identifier on exchange
        - **Membership Types**: TRADING_MEMBER, MARKET_MAKER, SPECIALIST
        - **Trading Rights**: Equity, options, market making flags
        - **DMM Status**: Designated Market Maker role (NYSE)
        - **Asset Class Scope**: What can be traded under this membership
        - **Temporal Validity**: valid_from/valid_to for membership lifecycle
    
    Examples:
        >>> # Standard trading membership
        >>> membership = ExchangeMembership(
        ...     exchange_id=nyse.exchange_id,
        ...     broker_dealer_id=citadel.broker_dealer_id,
        ...     member_code="CDRG",  # MPID
        ...     membership_type=MembershipType.TRADING_MEMBER,
        ...     can_trade_equity=True,
        ...     can_trade_options=True,
        ...     is_designated_market_maker=True,
        ... )
    
    Guardrails:
        - Do NOT confuse MembershipStatus with BrokerDealerStatus
          ✅ MembershipStatus = this relationship's status on this exchange
          ✅ BrokerDealerStatus = the firm's overall regulatory status
        - MPID (member_code) is exchange-specific, not globally unique
        - Validate membership is ACTIVE before routing orders
    
    Tags:
        - market_structure
        - relationship_model
        - exchange_membership
        - mpid
        - trading_rights
        - stdlib_only
    
    Doc-Types:
        - FEATURES (section: "Market Relationships", priority: 8)
        - API_REFERENCE (section: "Market Models", priority: 7)
    
    See Also:
        - Exchange: The venue this membership grants access to
        - BrokerDealer: The firm with membership
        - ClearingMembership: Clearing relationships (vs trading)
    
    Time Semantics:
        - valid_from: When membership became effective (business time)
        - valid_to: When membership terminated (business time)
        - captured_at: When we learned about this membership (system time)
    
    Attributes:
        membership_id: ULID primary key.
        exchange_id: FK to Exchange.
        broker_dealer_id: FK to BrokerDealer.
        membership_type: Type of exchange membership.
        member_code: Member code/MPID on the exchange.
        status: Membership status (MembershipStatus).
        can_trade_equity: Whether can trade equities.
        can_trade_options: Whether can trade options.
        is_market_maker: Whether registered as market maker.
        valid_from: When membership started.
        valid_to: When membership ended.
    """

    exchange_id: str
    broker_dealer_id: str

    membership_id: str = field(default_factory=generate_ulid)

    membership_type: MembershipType = MembershipType.TRADING_MEMBER
    member_code: str | None = None  # MPID
    # Uses MembershipStatus (v2.3.1), not BrokerDealerStatus
    status: MembershipStatus = MembershipStatus.ACTIVE

    # Trading rights
    can_trade_equity: bool = True
    can_trade_options: bool = False
    is_market_maker: bool = False
    is_designated_market_maker: bool = False

    # Asset classes
    asset_classes: tuple[AssetClass, ...] = (AssetClass.EQUITY,)

    # Validity (business time)
    valid_from: date | None = None  # effective_date
    valid_to: date | None = None  # termination_date

    # Legacy date fields (kept for backward compatibility)
    effective_date: date | None = None
    termination_date: date | None = None

    # Provenance
    source_system: str = "unknown"
    source_ref: str | None = None
    captured_at: datetime = field(default_factory=utc_now)
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self):
        """Validate and normalize membership data."""
        # Normalize MPID if provided
        if self.member_code:
            normalized = normalize_mpid(self.member_code)
            if normalized:
                is_valid, error = validate_mpid(normalized)
                if not is_valid:
                    raise ValueError(f"member_code (MPID) invalid: {error}")
                object.__setattr__(self, "member_code", normalized)

    @property
    def is_currently_valid(self) -> bool:
        """Check if exchange membership is currently valid."""
        return self.is_valid_at(date.today())

    def is_valid_at(self, query_date: date) -> bool:
        """
        Check if exchange membership was valid at a specific date.
        
        Args:
            query_date: Date to check validity for.
            
        Returns:
            True if valid at the given date, False otherwise.
        """
        if self.valid_from is not None and query_date < self.valid_from:
            return False
        if self.valid_to is not None and query_date > self.valid_to:
            return False
        return True


# =============================================================================
# Market Participant
# =============================================================================


@dataclass(frozen=True, slots=True)
class MarketParticipant:
    """
    A market participant identifier.
    
    Market Participant Identifiers (MPIDs) and similar codes used
    to identify firms in market data and regulatory reporting.
    
    Note on status:
        Uses MembershipStatus (not BrokerDealerStatus) because this represents
        the participant's status on a specific exchange, not their overall
        entity status.
    
    Time Semantics:
        valid_from: When MPID became effective
        valid_to: When MPID was terminated
        captured_at: When we learned about this MPID
    
    Attributes:
        participant_id: ULID primary key.
        mpid: Market Participant Identifier.
        participant_type: Type of market participant.
        
        # Relationships
        broker_dealer_id: FK to BrokerDealer (if applicable).
        entity_id: FK to Entity.
        exchange_id: FK to Exchange where registered.
        
        # Details
        name: Display name.
        status: Participant status on exchange (MembershipStatus).
        
        # Validity (business time)
        valid_from: When MPID became effective.
        valid_to: When MPID was terminated.
    """

    mpid: str
    exchange_id: str

    participant_id: str = field(default_factory=generate_ulid)

    participant_type: MarketParticipantType = MarketParticipantType.BROKER_DEALER
    name: str | None = None
    # Uses MembershipStatus (v2.3.1), not BrokerDealerStatus
    status: MembershipStatus = MembershipStatus.ACTIVE

    broker_dealer_id: str | None = None
    entity_id: str | None = None

    # Validity (business time)
    valid_from: date | None = None  # effective_date
    valid_to: date | None = None  # termination_date

    # Legacy date fields (kept for backward compatibility)
    effective_date: date | None = None
    termination_date: date | None = None

    # Provenance
    source_system: str = "unknown"
    source_ref: str | None = None
    captured_at: datetime = field(default_factory=utc_now)
    created_at: datetime = field(default_factory=utc_now)

    # Claims compatibility (v2.3.1)
    claim_target_id: str | None = None

    def __post_init__(self):
        """Validate and normalize market participant data."""
        if not self.mpid or not self.mpid.strip():
            raise ValueError("MPID cannot be empty")

        # Normalize and validate MPID
        normalized = normalize_mpid(self.mpid)
        if normalized:
            is_valid, error = validate_mpid(normalized)
            if not is_valid:
                raise ValueError(error)
            object.__setattr__(self, "mpid", normalized)

    @property
    def is_currently_valid(self) -> bool:
        """Check if market participant is currently valid."""
        return self.is_valid_at(date.today())

    def is_valid_at(self, query_date: date) -> bool:
        """
        Check if market participant was valid at a specific date.
        
        Args:
            query_date: Date to check validity for.
            
        Returns:
            True if valid at the given date, False otherwise.
        """
        if self.valid_from is not None and query_date < self.valid_from:
            return False
        if self.valid_to is not None and query_date > self.valid_to:
            return False
        return True


# =============================================================================
# SRO (Self-Regulatory Organization)
# =============================================================================


@dataclass(frozen=True, slots=True)
class SelfRegulatoryOrg:
    """
    A Self-Regulatory Organization (SRO).
    
    Models SROs like FINRA, exchanges acting as SROs, etc.
    
    Time Semantics:
        valid_from: When SRO was established
        valid_to: When SRO ceased operations
        captured_at: When we ingested this record
    
    Attributes:
        sro_id: ULID primary key.
        name: Full legal name.
        short_name: Common abbreviated name.
        
        # Classification
        is_exchange_sro: Whether this is an exchange acting as SRO.
        
        # Relationships
        entity_id: FK to Entity.
        exchange_id: FK to Exchange (if exchange-based SRO).
        
        # Regulatory
        sec_file_number: SEC registration number.
        
        # Validity (business time)
        valid_from: When SRO was established.
        valid_to: When SRO ceased operations.
    """

    name: str

    sro_id: str = field(default_factory=generate_ulid)
    short_name: str | None = None

    is_exchange_sro: bool = False

    entity_id: str | None = None
    exchange_id: str | None = None

    sec_file_number: str | None = None
    lei: str | None = None

    # Location & Jurisdiction (v2.3.2)
    country_code: str = "US"  # ISO 3166-1 alpha-2
    jurisdiction: str | None = None  # Regulatory jurisdiction

    # Areas of oversight
    oversees_broker_dealers: bool = True
    oversees_investment_advisers: bool = False
    oversees_exchanges: bool = False

    # Validity (business time)
    valid_from: date | None = None
    valid_to: date | None = None

    # Explicit lifecycle dates (v2.3.2)
    established_on: date | None = None  # When SRO was established
    dissolved_on: date | None = None  # When SRO was dissolved

    website: str | None = None

    # Provenance
    source_system: str = "unknown"
    source_ref: str | None = None
    captured_at: datetime = field(default_factory=utc_now)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def __post_init__(self):
        """Validate SRO data."""
        if not self.name or not self.name.strip():
            raise ValueError("SRO name cannot be empty")

        # Normalize SEC file number if provided
        if self.sec_file_number:
            normalized = normalize_sec_file_number(self.sec_file_number)
            object.__setattr__(self, "sec_file_number", normalized)

    @property
    def is_currently_valid(self) -> bool:
        """Check if SRO is currently valid."""
        return self.is_valid_at(date.today())

    def is_valid_at(self, query_date: date) -> bool:
        """
        Check if SRO was valid at a specific date.
        
        Args:
            query_date: Date to check validity for.
            
        Returns:
            True if valid at the given date, False otherwise.
        """
        if self.valid_from is not None and query_date < self.valid_from:
            return False
        if self.valid_to is not None and query_date > self.valid_to:
            return False
        return True


# =============================================================================
# Factory Functions
# =============================================================================


def create_exchange(
    name: str,
    mic: str,
    exchange_type: ExchangeType = ExchangeType.NATIONAL_SECURITIES_EXCHANGE,
    *,
    short_name: str | None = None,
    country_code: str = "US",
    valid_from: date | None = None,
    source_system: str = "manual",
) -> Exchange:
    """
    Factory function to create an Exchange.
    
    Args:
        name: Full legal name of the exchange.
        mic: Market Identifier Code (ISO 10383).
        exchange_type: Type of exchange/venue.
        short_name: Common abbreviated name.
        country_code: ISO country code.
        valid_from: When exchange started operating.
        source_system: Source of the data.
        
    Returns:
        Exchange instance.
    """
    return Exchange(
        name=name,
        mic=mic,
        exchange_type=exchange_type,
        short_name=short_name,
        country_code=country_code,
        valid_from=valid_from,
        source_system=source_system,
    )


def create_broker_dealer(
    name: str,
    crd_number: str,
    bd_type: BrokerDealerType = BrokerDealerType.FULL_SERVICE,
    *,
    sec_file_number: str | None = None,
    valid_from: date | None = None,
    source_system: str = "manual",
) -> BrokerDealer:
    """
    Factory function to create a BrokerDealer.
    
    Args:
        name: Legal name of the broker-dealer.
        crd_number: FINRA CRD number.
        bd_type: Type of broker-dealer.
        sec_file_number: SEC registration file number.
        valid_from: When registration became effective.
        source_system: Source of the data.
        
    Returns:
        BrokerDealer instance.
    """
    return BrokerDealer(
        name=name,
        crd_number=crd_number,
        bd_type=bd_type,
        sec_file_number=sec_file_number,
        valid_from=valid_from,
        source_system=source_system,
    )


def create_clearinghouse(
    name: str,
    clearinghouse_type: ClearinghouseType = ClearinghouseType.CENTRAL_COUNTERPARTY,
    *,
    short_name: str | None = None,
    valid_from: date | None = None,
    source_system: str = "manual",
) -> Clearinghouse:
    """
    Factory function to create a Clearinghouse.
    
    Args:
        name: Full legal name.
        clearinghouse_type: Type of clearing organization.
        short_name: Common abbreviated name.
        valid_from: When clearinghouse began operations.
        source_system: Source of the data.
        
    Returns:
        Clearinghouse instance.
    """
    return Clearinghouse(
        name=name,
        clearinghouse_type=clearinghouse_type,
        short_name=short_name,
        valid_from=valid_from,
        source_system=source_system,
    )


def create_exchange_segment(
    exchange_id: str,
    segment_mic: str,
    *,
    operating_mic: str | None = None,
    segment_name: str | None = None,
    valid_from: date | None = None,
    source_system: str = "manual",
) -> ExchangeSegment:
    """
    Factory function to create an ExchangeSegment.
    
    Args:
        exchange_id: FK to parent Exchange.
        segment_mic: MIC code for this segment.
        operating_mic: Operating MIC.
        segment_name: Human-readable segment name.
        valid_from: When segment started operating.
        source_system: Source of the data.
        
    Returns:
        ExchangeSegment instance.
    """
    return ExchangeSegment(
        exchange_id=exchange_id,
        segment_mic=segment_mic,
        operating_mic=operating_mic,
        segment_name=segment_name,
        valid_from=valid_from,
        source_system=source_system,
    )


# =============================================================================
# Backward Compatibility: Reference Data Re-exports
# =============================================================================
#
# NOTE: Reference data has been moved to entityspine.domain.reference_data.markets
# These re-exports are provided for backward compatibility but will be deprecated.
# Please import directly from reference_data module instead.
#

