"""
Enumerations for EntitySpine domain models.

All enums are str-based for JSON serialization compatibility.
STDLIB ONLY - NO PYDANTIC.
"""

from enum import Enum

# =============================================================================
# Entity Enums
# =============================================================================


class EntityType(str, Enum):
    """
    Type of legal entity.

    Keep types BROAD and stable. Nuance (like "Subsidiary") should be
    modeled via relationships, not more entity types.
    """

    ORGANIZATION = "organization"  # General company/corporation
    PERSON = "person"  # Natural person
    GOVERNMENT = "government"  # Government body/agency
    FUND = "fund"  # Investment fund (mutual, hedge, etc.)
    TRUST = "trust"  # Trust structure
    PARTNERSHIP = "partnership"  # LP, LLP, general partnership
    SPV = "spv"  # Special Purpose Vehicle
    EXCHANGE = "exchange"  # Stock exchange / trading venue
    GEO = "geo"  # Geographic entity (country, state)
    UNKNOWN = "unknown"  # Unknown entity type


class EntityStatus(str, Enum):
    """Lifecycle status of an entity."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    MERGED = "merged"
    PROVISIONAL = "provisional"


# =============================================================================
# Security Enums
# =============================================================================


class SecurityType(str, Enum):
    """Type of financial security."""

    COMMON_STOCK = "common_stock"
    PREFERRED_STOCK = "preferred_stock"
    ADR = "adr"
    ETF = "etf"
    BOND = "bond"
    WARRANT = "warrant"
    OPTION = "option"
    UNIT = "unit"
    REIT = "reit"
    OTHER = "other"


class SecurityStatus(str, Enum):
    """Lifecycle status of a security."""

    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELISTED = "delisted"
    MATURED = "matured"


# =============================================================================
# Listing Enums
# =============================================================================


class ListingStatus(str, Enum):
    """Lifecycle status of a listing."""

    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELISTED = "delisted"


# =============================================================================
# Identifier Claim Enums
# =============================================================================


class IdentifierScheme(str, Enum):
    """
    Standard identifier schemes.

    Each scheme has an expected scope (entity, security, or listing).
    """

    # Entity-scoped (legal identity)
    CIK = "cik"  # SEC Central Index Key → entity_id
    LEI = "lei"  # Legal Entity Identifier → entity_id
    EIN = "ein"  # Employer Identification Number → entity_id
    DUNS = "duns"  # D-U-N-S Number → entity_id

    # Security-scoped (financial instrument)
    ISIN = "isin"  # International Securities ID Number → security_id
    CUSIP = "cusip"  # CUSIP identifier → security_id
    SEDOL = "sedol"  # SEDOL identifier → security_id
    FIGI = "figi"  # Financial Instrument Global ID → security_id

    # Listing-scoped (exchange-specific)
    TICKER = "ticker"  # Stock ticker symbol → listing_id
    RIC = "ric"  # Reuters Instrument Code → listing_id

    # Flexible scope
    INTERNAL = "internal"  # Internal system ID → any
    OTHER = "other"  # Other identifier type → any


class ClaimStatus(str, Enum):
    """Status of an identifier claim."""

    ACTIVE = "active"
    SUPERSEDED = "superseded"
    REVOKED = "revoked"
    DISPUTED = "disputed"


class VendorNamespace(str, Enum):
    """
    Vendor/source namespaces for identifier claims.

    Enables multi-vendor crosswalks (Bloomberg vs FactSet vs Reuters, etc.)
    """

    # Regulatory sources
    SEC = "sec"
    GLEIF = "gleif"

    # Market data vendors
    BLOOMBERG = "bloomberg"
    FACTSET = "factset"
    REUTERS = "reuters"
    OPENFIGI = "openfigi"

    # Exchanges
    EXCHANGE = "exchange"

    # Internal
    USER = "user"
    INTERNAL = "internal"

    # Other
    OTHER = "other"


class IdentifierScope(str, Enum):
    """Which object type an identifier scheme applies to."""

    ENTITY = "entity"
    SECURITY = "security"
    LISTING = "listing"
    ANY = "any"


# =============================================================================
# Resolution Enums
# =============================================================================


class ResolutionTier(int, Enum):
    """Storage tier that provided the resolution."""

    CACHE = -1
    TIER_0 = 0
    TIER_1 = 1
    TIER_2 = 2
    TIER_3 = 3


class ResolutionStatus(str, Enum):
    """Status of the resolution attempt."""

    FOUND = "found"
    NOT_FOUND = "not_found"
    AMBIGUOUS = "ambiguous"
    REDIRECTED = "redirected"
    ERROR = "error"


class ResolutionWarning(str, Enum):
    """Standard warning types for resolution results."""

    AS_OF_IGNORED = "as_of_ignored"
    TEMPORAL_NOT_SUPPORTED = "temporal_not_supported"
    MIC_NOT_SUPPORTED = "mic_not_supported"
    REDIRECT_FOLLOWED = "redirect_followed"
    MAX_REDIRECTS_REACHED = "max_redirects_reached"
    AMBIGUOUS_MATCH = "ambiguous_match"
    LOW_CONFIDENCE = "low_confidence"
    STALE_DATA = "stale_data"
    CACHE_HIT = "cache_hit"
    FUZZY_MATCH_ONLY = "fuzzy_match_only"


class MatchReason(str, Enum):
    """Why a resolution candidate matched the query."""

    # Exact identifier matches
    EXACT_CIK = "exact_cik"
    EXACT_LEI = "exact_lei"
    EXACT_ISIN = "exact_isin"
    EXACT_CUSIP = "exact_cusip"
    EXACT_FIGI = "exact_figi"
    EXACT_TICKER = "exact_ticker"

    # Name matches
    NAME_EXACT = "name_exact"
    NAME_FUZZY = "name_fuzzy"
    ALIAS_MATCH = "alias_match"

    # Derived matches
    REDIRECT_FOLLOWED = "redirect_followed"
    CROSS_REFERENCE = "cross_reference"

    # Ambiguous
    MULTIPLE_MATCHES = "multiple_matches"

    # Unknown
    UNKNOWN = "unknown"


# =============================================================================
# Knowledge Graph Enums (Full Version)
# =============================================================================


class RoleType(str, Enum):
    """
    Type of role a person holds at an organization.

    Used in PersonRole edges to represent person ↔ org relationships.
    """

    # C-Suite
    CEO = "ceo"
    CFO = "cfo"
    COO = "coo"
    CTO = "cto"
    CHRO = "chro"
    CIO = "cio"
    CLO = "clo"
    CMO = "cmo"

    # Board
    DIRECTOR = "director"
    CHAIR = "chair"
    VICE_CHAIR = "vice_chair"
    LEAD_DIRECTOR = "lead_director"

    # Officers
    OFFICER = "officer"
    PRESIDENT = "president"
    EVP = "evp"
    SVP = "svp"
    VP = "vp"
    SECRETARY = "secretary"
    TREASURER = "treasurer"
    CONTROLLER = "controller"

    # Compliance/Governance
    SIGNATORY = "signatory"
    PRINCIPAL_ACCOUNTING_OFFICER = "principal_accounting_officer"
    PRINCIPAL_FINANCIAL_OFFICER = "principal_financial_officer"
    PRINCIPAL_EXECUTIVE_OFFICER = "principal_executive_officer"

    # Ownership
    BENEFICIAL_OWNER_10PCT = "beneficial_owner_10pct"
    REPORTING_OWNER = "reporting_owner"
    INSIDER = "insider"

    # External
    AUDITOR = "auditor"
    AUDITOR_PARTNER = "auditor_partner"
    UNDERWRITER = "underwriter"
    UNDERWRITER_CONTACT = "underwriter_contact"
    COUNSEL = "counsel"

    # Other
    EMPLOYEE = "employee"
    CONSULTANT = "consultant"
    OTHER = "other"


class ParticipantType(str, Enum):
    """
    Type of participation in a filing.

    Used in FilingParticipant to represent who appears in filings and how.
    """

    SIGNER = "signer"
    OFFICER = "officer"
    DIRECTOR = "director"
    REPORTING_OWNER = "reporting_owner"
    BENEFICIAL_OWNER = "beneficial_owner"
    AUDITOR = "auditor"
    COUNSEL = "counsel"
    UNDERWRITER = "underwriter"
    CONTACT = "contact"
    MENTIONED = "mentioned"
    OTHER = "other"


class PositionType(str, Enum):
    """
    Type of ownership position.

    Used in OwnershipPosition to categorize holdings.
    """

    BENEFICIAL_OWNER = "beneficial_owner"
    DIRECT_OWNER = "direct_owner"
    INDIRECT_OWNER = "indirect_owner"
    INSTITUTIONAL_HOLDER = "institutional_holder"
    INSIDER = "insider"
    REPORTING_OWNER = "reporting_owner"
    GROUP_MEMBER = "group_member"
    OTHER = "other"


class TransactionCode(str, Enum):
    """
    SEC Form 4/5 transaction codes.

    Used in InsiderTransaction to categorize insider trades.
    """

    # Open Market
    P = "P"  # Open market purchase
    S = "S"  # Open market sale

    # Exercises/Conversions
    A = "A"  # Grant/award
    M = "M"  # Exercise of derivative
    C = "C"  # Conversion of derivative
    X = "X"  # Exercise of in-the-money option

    # Gifts/Inheritances
    G = "G"  # Gift
    J = "J"  # Other acquisition
    K = "K"  # Equity swap

    # Plan Transactions
    F = "F"  # Tax withholding
    I = "I"  # Discretionary transaction
    W = "W"  # Acquisition/disposition by will

    # Dispositions
    D = "D"  # Disposition to issuer
    L = "L"  # Small acquisition
    U = "U"  # Tender of shares
    Z = "Z"  # Deposit into voting trust

    # Other
    OTHER = "other"


class AddressType(str, Enum):
    """Type of address for an entity."""

    BUSINESS = "business"
    MAILING = "mailing"
    REGISTERED = "registered"
    HEADQUARTERS = "headquarters"
    FILING = "filing"
    RESIDENCE = "residence"
    OTHER = "other"


class ClusterRole(str, Enum):
    """
    Role of an entity within a cluster.

    Used for gradual entity consolidation without destructive merges.
    """

    CANONICAL = "canonical"  # The "winner" entity in the cluster
    MEMBER = "member"  # A potential duplicate
    PROVISIONAL = "provisional"  # Unconfirmed membership


class RelationshipType(str, Enum):
    """
    Type of relationship between two nodes.

    Used in EntityRelationship for entity ↔ entity edges,
    and in Relationship for polymorphic NodeRef edges.

    v2.2.4: Extended to support Asset, Contract, Product, Brand, Event nodes.
    """

    # Corporate structure
    PARENT = "parent"
    SUBSIDIARY = "subsidiary"
    AFFILIATE = "affiliate"
    SUCCESSOR = "successor"
    PREDECESSOR = "predecessor"

    # Business relationships
    CUSTOMER = "customer"
    SUPPLIER = "supplier"
    VENDOR = "vendor"
    PARTNER = "partner"
    COMPETITOR = "competitor"

    # Financial relationships
    INVESTOR = "investor"
    INVESTEE = "investee"
    LENDER = "lender"
    BORROWER = "borrower"
    GUARANTOR = "guarantor"
    BENEFICIAL_OWNER_OF = "beneficial_owner_of"

    # Service relationships
    AUDITOR = "auditor"
    COUNSEL = "counsel"
    UNDERWRITER = "underwriter"
    ADVISOR = "advisor"

    # Employment/Position
    OFFICER_OF = "officer_of"
    DIRECTOR_OF = "director_of"
    EMPLOYED_BY = "employed_by"

    # Regulatory
    REGULATED_BY = "regulated_by"
    REGULATES = "regulates"  # Inverse

    # Listing
    LISTED_ON = "listed_on"

    # Geographic
    LOCATED_IN = "located_in"
    LOCATED_AT = "located_at"  # More precise than located_in
    INCORPORATED_IN = "incorporated_in"
    HEADQUARTERED_IN = "headquartered_in"

    # =========================================================================
    # Asset relationships (v2.2.4)
    # =========================================================================
    OWNS_ASSET = "owns_asset"  # Entity owns Asset
    OPERATES_ASSET = "operates_asset"  # Entity operates Asset
    LEASES_ASSET = "leases_asset"  # Entity leases Asset

    # =========================================================================
    # Contract relationships (v2.2.4)
    # =========================================================================
    PARTY_TO = "party_to"  # Entity is party to Contract
    COUNTERPARTY_TO = "counterparty_to"  # Entity is counterparty in Contract
    GOVERNS = "governs"  # Contract governs (Asset, Product, etc.)

    # =========================================================================
    # Product relationships (v2.2.4)
    # =========================================================================
    MANUFACTURES = "manufactures"  # Entity manufactures Product
    SELLS = "sells"  # Entity sells Product
    DISTRIBUTES = "distributes"  # Entity distributes Product
    LICENSES_PRODUCT = "licenses_product"  # Entity licenses Product
    DEVELOPS = "develops"  # Entity develops Product

    # =========================================================================
    # Brand relationships (v2.2.4)
    # =========================================================================
    OWNS_BRAND = "owns_brand"  # Entity owns Brand
    LICENSES_BRAND = "licenses_brand"  # Entity licenses Brand
    BRAND_OF = "brand_of"  # Brand applies to Product

    # =========================================================================
    # Event relationships (v2.2.4)
    # =========================================================================
    SUBJECT_OF = "subject_of"  # Entity is subject of Event
    INVOLVED_IN = "involved_in"  # Entity involved in Event
    TRIGGERED_BY = "triggered_by"  # Event triggered by (another Event)
    RESULTED_IN = "resulted_in"  # Event resulted in (another Event)
    ANNOUNCED_BY = "announced_by"  # Event announced by Entity

    # Other
    RELATED_PARTY = "related_party"
    ACQUIRED = "acquired"
    OTHER = "other"


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


class GeoType(str, Enum):
    """
    Type of geographic entity.

    Used in Geo for different levels of geographic granularity.
    """

    COUNTRY = "country"  # ISO 3166-1 country
    STATE = "state"  # State/Province (ISO 3166-2)
    CITY = "city"  # City/Municipality
    REGION = "region"  # Other region (county, district)
    CONTINENT = "continent"  # Continent
    OTHER = "other"


# =============================================================================
# KG High-Confidence Node Types (v2.2.4)
# =============================================================================


class AssetType(str, Enum):
    """
    Type of physical/tangible asset.

    Used in Asset nodes for categorizing physical assets.
    """

    FACILITY = "facility"  # Manufacturing facility, office
    DATA_CENTER = "data_center"  # Data center
    VESSEL = "vessel"  # Ship, boat
    AIRCRAFT = "aircraft"  # Airplane, helicopter
    PLANT = "plant"  # Industrial plant
    PROPERTY = "property"  # Real estate property
    EQUIPMENT = "equipment"  # Major equipment
    VEHICLE = "vehicle"  # Land vehicles
    INVENTORY = "inventory"  # Significant inventory
    INTELLECTUAL_PROPERTY = "ip"  # Patents, trademarks (non-physical)
    OTHER = "other"


class AssetStatus(str, Enum):
    """Lifecycle status of an asset."""

    ACTIVE = "active"  # In operation
    INACTIVE = "inactive"  # Idle/mothballed
    UNDER_CONSTRUCTION = "under_construction"
    DISPOSED = "disposed"  # Sold/decommissioned
    LEASED_OUT = "leased_out"  # Leased to another party
    OTHER = "other"


class ContractType(str, Enum):
    """
    Type of legal contract/agreement.

    Used in Contract nodes for categorizing agreements.
    """

    CREDIT_FACILITY = "credit_facility"  # Loan/credit agreement
    LEASE = "lease"  # Property/equipment lease
    MATERIAL_AGREEMENT = "material_agreement"  # 8-K material contract
    SUPPLY_AGREEMENT = "supply"  # Supply/procurement
    LICENSE = "license"  # License agreement
    EMPLOYMENT = "employment"  # Employment contract
    MERGER_AGREEMENT = "merger"  # M&A agreement
    JOINT_VENTURE = "joint_venture"  # JV agreement
    SERVICE_AGREEMENT = "service"  # Service contract
    DISTRIBUTION = "distribution"  # Distribution agreement
    SETTLEMENT = "settlement"  # Legal settlement
    OTHER = "other"


class ContractStatus(str, Enum):
    """Lifecycle status of a contract."""

    ACTIVE = "active"
    EXPIRED = "expired"
    TERMINATED = "terminated"
    PENDING = "pending"
    UNDER_NEGOTIATION = "negotiation"
    AMENDED = "amended"
    OTHER = "other"


class ProductType(str, Enum):
    """
    Type of product or service.

    Used in Product nodes for categorizing products.
    """

    DRUG = "drug"  # Pharmaceutical drug
    DEVICE = "device"  # Medical device
    SOFTWARE = "software"  # Software product
    SERVICE = "service"  # Service offering
    CONSUMER_GOOD = "consumer_good"  # Consumer product
    INDUSTRIAL_GOOD = "industrial"  # Industrial product
    FINANCIAL_PRODUCT = "financial"  # Financial product (not security)
    FOOD_BEVERAGE = "food_beverage"  # Food & beverage
    VEHICLE = "vehicle"  # Vehicle product
    OTHER = "other"


class ProductStatus(str, Enum):
    """Lifecycle status of a product."""

    ACTIVE = "active"  # On market
    DEVELOPMENT = "development"  # In development
    DISCONTINUED = "discontinued"  # No longer sold
    RECALLED = "recalled"  # Product recall
    PENDING_APPROVAL = "pending"  # Awaiting regulatory approval
    OTHER = "other"


class EventType(str, Enum):
    """
    Type of discrete business event.

    Used in Event nodes for graph-native events.
    Maps loosely to SEC 8-K event categories.
    """

    # Corporate events
    MERGER_ACQUISITION = "m&a"  # M&A, tender offer
    DIVESTITURE = "divestiture"  # Spin-off, sale of division
    RESTRUCTURING = "restructuring"  # Reorg, layoffs
    BANKRUPTCY = "bankruptcy"  # Bankruptcy filing

    # Legal/Compliance events
    LEGAL = "legal"  # Lawsuit, settlement
    REGULATORY = "regulatory"  # Regulatory action
    INVESTIGATION = "investigation"  # Government investigation
    ENFORCEMENT = "enforcement"  # Enforcement action

    # Risk events
    CYBER = "cyber"  # Cyber incident
    DATA_BREACH = "data_breach"  # Data breach
    OPERATIONAL = "operational"  # Operational incident

    # Financial events
    FINANCIAL = "financial"  # Earnings, restatement
    CAPITAL = "capital"  # Capital raise, buyback
    DIVIDEND = "dividend"  # Dividend declaration

    # Management events
    MANAGEMENT = "mgmt"  # Leadership change
    BOARD = "board"  # Board change

    # Product events
    PRODUCT_LAUNCH = "product_launch"
    PRODUCT_RECALL = "product_recall"

    # Other
    OTHER = "other"


class EventStatus(str, Enum):
    """Status of a business event."""

    ANNOUNCED = "announced"  # Publicly announced
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    PENDING = "pending"
    UNKNOWN = "unknown"
