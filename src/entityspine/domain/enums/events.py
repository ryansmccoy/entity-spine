"""
Event and case tracking enums.

STDLIB ONLY - NO PYDANTIC.
"""

from enum import Enum


class EventType(str, Enum):
    """
    Type of discrete business event.

    Used in Event nodes for graph-native events.
    Maps loosely to SEC 8-K event categories and FactSet Events Calendar.

    Examples:
        >>> event_type = EventType.EARNINGS_RELEASE
        >>> event_type.value
        'earnings_release'

        >>> EventType.FUNDING_ROUND in [EventType.FUNDING_ROUND, EventType.IPO]
        True

        >>> # Calendar events (from FactSet Events feed)
        >>> calendar_events = [
        ...     EventType.EARNINGS_RELEASE,
        ...     EventType.DIVIDEND_EX_DATE,
        ...     EventType.ANALYST_DAY,
        ... ]
    """

    # =========================================================================
    # Corporate Action Events (M&A, restructuring)
    # =========================================================================
    MERGER_ACQUISITION = "m&a"  # M&A, tender offer
    DIVESTITURE = "divestiture"  # Spin-off, sale of division
    RESTRUCTURING = "restructuring"  # Reorg, layoffs
    BANKRUPTCY = "bankruptcy"  # Bankruptcy filing
    DELISTING = "delisting"  # Exchange delisting
    SPINOFF = "spinoff"  # Corporate spin-off
    TENDER_OFFER = "tender_offer"  # Tender offer (hostile or friendly)

    # =========================================================================
    # Calendar Events (FactSet Events feed aligned)
    # =========================================================================
    # Earnings calendar
    EARNINGS_RELEASE = "earnings_release"  # Quarterly/annual earnings
    EARNINGS_CALL = "earnings_call"  # Earnings conference call
    EARNINGS_GUIDANCE = "earnings_guidance"  # Forward guidance update
    EARNINGS_REVISION = "earnings_revision"  # Analyst estimate revision

    # Dividend calendar
    DIVIDEND_DECLARED = "dividend_declared"  # Dividend announcement
    DIVIDEND_EX_DATE = "dividend_ex_date"  # Ex-dividend date
    DIVIDEND_RECORD = "dividend_record"  # Record date
    DIVIDEND_PAYMENT = "dividend_payment"  # Payment date
    SPECIAL_DIVIDEND = "special_dividend"  # Special/one-time dividend

    # Corporate calendar
    ANNUAL_MEETING = "annual_meeting"  # Shareholder annual meeting
    ANALYST_DAY = "analyst_day"  # Investor/analyst day
    INVESTOR_CONFERENCE = "investor_conference"  # Conference presentation
    GUIDANCE_UPDATE = "guidance_update"  # Financial guidance update

    # Stock events
    STOCK_SPLIT = "stock_split"  # Forward stock split
    REVERSE_SPLIT = "reverse_split"  # Reverse stock split
    SHARE_BUYBACK = "share_buyback"  # Share repurchase program

    # =========================================================================
    # Legal/Compliance Events
    # =========================================================================
    LEGAL = "legal"  # Lawsuit, settlement
    REGULATORY = "regulatory"  # Regulatory action
    INVESTIGATION = "investigation"  # Government investigation
    ENFORCEMENT = "enforcement"  # Enforcement action

    # Sanctions & Compliance (OFAC, UN, EU aligned)
    SANCTION_DESIGNATION = "sanction_designation"  # Added to sanctions list
    SANCTION_REMOVAL = "sanction_removal"  # Removed from sanctions list
    SANCTION_UPDATE = "sanction_update"  # Sanction details changed
    COMPLIANCE_VIOLATION = "compliance_violation"  # Compliance breach
    AUDIT_FINDING = "audit_finding"  # Audit/inspection finding

    # =========================================================================
    # Risk Events
    # =========================================================================
    CYBER = "cyber"  # Cyber incident
    DATA_BREACH = "data_breach"  # Data breach
    OPERATIONAL = "operational"  # Operational incident
    ESG_INCIDENT = "esg_incident"  # ESG-related incident
    SUPPLY_CHAIN = "supply_chain"  # Supply chain disruption

    # =========================================================================
    # Financial Events
    # =========================================================================
    FINANCIAL = "financial"  # Generic financial event
    CAPITAL = "capital"  # Capital raise, buyback
    DIVIDEND = "dividend"  # Legacy dividend (use specific types above)
    RESTATEMENT = "restatement"  # Financial restatement
    CREDIT_RATING = "credit_rating"  # Credit rating change

    # =========================================================================
    # Private Equity / Venture Events
    # =========================================================================
    FUNDING_ROUND = "funding_round"  # Venture funding (Series A, B, etc.)
    IPO = "ipo"  # Initial Public Offering
    IPO_FILING = "ipo_filing"  # IPO registration (S-1 filing)
    DIRECT_LISTING = "direct_listing"  # Direct listing
    SPAC_MERGER = "spac_merger"  # SPAC de-SPAC transaction
    PRIVATE_PLACEMENT = "private_placement"  # PIPE, private placement
    SECONDARY_OFFERING = "secondary_offering"  # Secondary stock offering
    LBO = "lbo"  # Leveraged buyout
    EXIT = "exit"  # PE exit event

    # =========================================================================
    # Management Events
    # =========================================================================
    MANAGEMENT = "mgmt"  # Generic leadership change
    CEO_CHANGE = "ceo_change"  # CEO appointment/departure
    CFO_CHANGE = "cfo_change"  # CFO appointment/departure
    BOARD = "board"  # Board change
    EXECUTIVE_COMP = "executive_comp"  # Executive compensation event

    # =========================================================================
    # Product Events
    # =========================================================================
    PRODUCT_LAUNCH = "product_launch"
    PRODUCT_RECALL = "product_recall"
    FDA_APPROVAL = "fda_approval"  # FDA drug/device approval
    FDA_REJECTION = "fda_rejection"  # FDA rejection/CRL
    PATENT = "patent"  # Patent grant/expiry

    # =========================================================================
    # Other
    # =========================================================================
    OTHER = "other"


class EventStatus(str, Enum):
    """Status of a business event."""

    ANNOUNCED = "announced"  # Publicly announced
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    PENDING = "pending"
    UNKNOWN = "unknown"


class CaseType(str, Enum):
    """
    Type of legal case/proceeding.

    Used in Case for proceedings, investigations, enforcement actions.
    """

    LAWSUIT = "lawsuit"  # Civil litigation
    INVESTIGATION = "investigation"  # Regulatory investigation
    ENFORCEMENT = "enforcement"  # SEC/DOJ enforcement action
    ARBITRATION = "arbitration"  # FINRA/other arbitration
    BANKRUPTCY = "bankruptcy"  # Bankruptcy proceedings
    ADMINISTRATIVE = "administrative"  # Administrative proceeding
    CRIMINAL = "criminal"  # Criminal charges
    OTHER = "other"


class CaseStatus(str, Enum):
    """Status of a legal case."""

    OPEN = "open"
    PENDING = "pending"
    CLOSED = "closed"
    SETTLED = "settled"
    DISMISSED = "dismissed"
    APPEALED = "appealed"
    UNKNOWN = "unknown"


class DataQualitySeverity(str, Enum):
    """
    Severity level for data quality rules and results.

    Used in DataQualityRule and DataQualityResult.

    Examples:
        >>> DataQualitySeverity.WARNING.value
        'warning'
    """

    INFO = "info"  # Informational, no action required
    WARNING = "warning"  # May need attention
    ERROR = "error"  # Requires action
    CRITICAL = "critical"  # Blocks processing


class RunStatus(str, Enum):
    """
    Status of a resolution or processing run.

    Used in ResolutionRun to track batch execution state.

    Examples:
        >>> RunStatus.COMPLETED.value
        'completed'
    """

    PENDING = "pending"  # Queued, not started
    RUNNING = "running"  # Currently executing
    COMPLETED = "completed"  # Finished successfully
    FAILED = "failed"  # Finished with error
    CANCELLED = "cancelled"  # Manually stopped


class DecisionType(str, Enum):
    """
    Type of resolution decision for audit explanations.

    Used in Explanation to categorize what kind of decision was made.

    Examples:
        >>> DecisionType.MATCH.value
        'match'
    """

    MATCH = "match"  # Identifiers matched to entity
    REJECT = "reject"  # Candidate rejected
    MERGE = "merge"  # Entities merged
    SPLIT = "split"  # Entity split
    CREATE = "create"  # New entity created
    UPDATE = "update"  # Entity updated
    MANUAL = "manual"  # Manual intervention
