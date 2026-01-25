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
    A securities exchange or trading venue.
    
    Represents venues where securities trade, including national exchanges,
    ATSs, dark pools, and foreign exchanges.
    
    Key identifiers:
    - MIC: Market Identifier Code (ISO 10383) - primary identifier
    - Operating MIC: For market segments (see ExchangeSegment for structured)
    - SEC File Number: For SEC-registered exchanges
    
    Time Semantics:
        valid_from: When exchange started operating (business time)
        valid_to: When exchange ceased operating (None if still active)
        captured_at: When we ingested this record
        created_at/updated_at: Record metadata
    
    Attributes:
        exchange_id: ULID primary key.
        name: Full legal name of the exchange.
        short_name: Common abbreviated name (e.g., "NYSE", "NASDAQ").
        mic: Market Identifier Code (ISO 10383).
        operating_mic: Operating MIC for market segments.
        exchange_type: Type of exchange/venue.
        country_code: ISO 3166-1 alpha-2 country code.
        city: City where headquartered.
        website: Exchange website URL.
        status: Operational status.
        
        # Regulatory
        sec_file_number: SEC registration file number.
        is_sec_registered: Whether registered with SEC as exchange.
        is_sip_participant: Whether participates in SIP (CTA/CQS/UTP).
        
        # Trading info
        asset_classes: Asset classes traded.
        trading_currency: Primary trading currency.
        timezone: Timezone for trading hours.
        
        # Parent/subsidiary
        parent_entity_id: FK to parent Entity (for ownership).
        operator_entity_id: FK to operating entity.
        
        # Validity (business time)
        valid_from: When exchange started operating.
        valid_to: When exchange ceased operating.
        
        # Provenance
        source_system: Where this record came from.
        source_ref: Reference in source system.
        captured_at: When we captured this record.
        created_at: Record creation timestamp.
        updated_at: Record update timestamp.
        
        # Claims compatibility
        claim_target_id: Optional ID for linking to IdentifierClaims.
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
    
    Models broker-dealer firms including their regulatory status,
    business lines, and organizational relationships.
    
    Key identifiers:
    - CRD Number: Central Registration Depository number (primary)
    - SEC File Number: SEC registration number
    
    Time Semantics:
        valid_from: When BD registration became effective
        valid_to: When BD registration terminated
        captured_at: When we ingested this record
    
    Note on status:
        BrokerDealerStatus is used ONLY for the BD entity lifecycle.
        For membership status on exchanges, use ExchangeMembership.status (MembershipStatus).
        For registration status in jurisdictions, use BrokerDealerRegistration.status (RegistrationStatus).
    
    Attributes:
        broker_dealer_id: ULID primary key.
        name: Legal name of the broker-dealer.
        dba_name: Doing business as name.
        crd_number: FINRA CRD number (primary identifier).
        sec_file_number: SEC broker-dealer file number.
        
        # Classification
        bd_type: Type of broker-dealer.
        status: Entity lifecycle status (NOT membership or registration status).
        
        # Business info
        clearing_arrangement: How trades are cleared.
        clears_for_self: Whether self-clearing.
        clears_for_others: Whether clears for other firms.
        
        # Relationships
        entity_id: FK to Entity (the legal entity).
        clearing_firm_id: FK to clearing firm BrokerDealer.
        parent_bd_id: FK to parent broker-dealer.
        
        # Validity (business time)
        valid_from: When registration became effective.
        valid_to: When registration terminated.
        
        # Provenance
        source_system: Where this record came from.
        captured_at: When captured.
        
        # Claims compatibility
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
    A clearing organization or central counterparty.
    
    Models clearing agencies, CCPs, and securities depositories.
    
    Examples:
    - DTCC (Depository Trust & Clearing Corporation)
    - NSCC (National Securities Clearing Corporation)
    - OCC (Options Clearing Corporation)
    - CME Clearing
    
    Time Semantics:
        valid_from: When clearinghouse began operations
        valid_to: When clearinghouse ceased operations
        captured_at: When we ingested this record
    
    Note on status:
        ClearingStatus is for the clearinghouse entity itself.
        For clearing MEMBERSHIP status, see ClearingMembership.status (MembershipStatus).
    
    Attributes:
        clearinghouse_id: ULID primary key.
        name: Full legal name.
        short_name: Common abbreviated name.
        clearinghouse_type: Type of clearing organization.
        
        # Regulatory
        sec_file_number: SEC registration number.
        is_sec_registered: Whether registered with SEC.
        is_systemically_important: Whether designated as SIFMU.
        
        # Operations
        asset_classes: Asset classes cleared.
        settlement_currency: Primary settlement currency.
        
        # Relationships
        entity_id: FK to Entity (the legal entity).
        parent_clearinghouse_id: FK to parent clearinghouse.
        
        # Validity (business time)
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
    A clearing membership relationship.
    
    Links a broker-dealer or other entity to a clearinghouse.
    
    Note on status:
        Uses MembershipStatus (not ClearingStatus or BrokerDealerStatus)
        because membership status is distinct from entity lifecycle status.
    
    Time Semantics:
        valid_from: When membership became effective
        valid_to: When membership terminated
        captured_at: When we learned about this membership
    
    Attributes:
        membership_id: ULID primary key.
        clearinghouse_id: FK to Clearinghouse.
        member_entity_id: FK to Entity (the member).
        member_bd_id: FK to BrokerDealer (if applicable).
        
        # Membership details
        membership_type: Type of clearing membership.
        status: Membership status (MembershipStatus).
        
        # Validity (business time)
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
    An exchange membership relationship.
    
    Links a broker-dealer to an exchange with specific trading rights.
    
    Note on status:
        Uses MembershipStatus (not BrokerDealerStatus) because a BD can be
        ACTIVE but have a SUSPENDED membership on a particular exchange.
    
    Time Semantics:
        valid_from: When membership became effective
        valid_to: When membership terminated
        captured_at: When we learned about this membership
    
    Attributes:
        membership_id: ULID primary key.
        exchange_id: FK to Exchange.
        broker_dealer_id: FK to BrokerDealer.
        
        # Membership details
        membership_type: Type of exchange membership.
        member_code: Member code/MPID on the exchange.
        status: Membership status (MembershipStatus).
        
        # Trading rights
        can_trade_equity: Whether can trade equities.
        can_trade_options: Whether can trade options.
        is_market_maker: Whether registered as market maker.
        
        # Validity (business time)
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

from entityspine.domain.reference_data.markets import (
    ALL_KNOWN_MICS,
    AMERICAS_EXCHANGES,
    APAC_EXCHANGES,
    BLOOMBERG_FEED_SOURCES,
    EUROPEAN_EXCHANGES,
    FACTSET_EXCHANGE_CODES,
    GLOBAL_CLEARINGHOUSES,
    MENA_EXCHANGES,
    THOMSON_EXCHANGE_CODES,
    US_CLEARINGHOUSES,
    US_EQUITY_EXCHANGES,
    US_FUTURES_EXCHANGES,
    US_OPTIONS_EXCHANGES,
    US_OTC_MARKETS,
    lookup_exchange_by_mic,
)
