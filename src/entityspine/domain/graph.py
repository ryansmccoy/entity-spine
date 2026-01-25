"""
Knowledge Graph domain models for EntitySpine Full version.

These models represent the "nodes" and "edges" in the knowledge graph:

Node types:
- NodeRef: Polymorphic reference to any graph node
- Geo: Geographic location node
- Case: Legal proceedings/investigations
- Asset: Physical/tangible assets (v2.2.4)
- Contract: Legal agreements (v2.2.4)
- Product: Products/services (v2.2.4)
- Brand: Brand identities (v2.2.4)
- Event: Discrete business events (v2.2.4)

Edge types:
- PersonRole: Person ↔ Org relationships (temporal)
- FilingParticipant: Person ↔ Filing ↔ Org context
- OwnershipPosition: Owner ↔ Issuer holdings
- InsiderTransaction: Insider trading records
- EntityAddress: Entity ↔ Address links
- EntityRelationship: Generic entity ↔ entity edges
- Relationship: Generic NodeRef ↔ NodeRef edges

Infrastructure:
- Address: Normalized address records
- EntityCluster: Anti-duplication clustering
- EntityClusterMember: Cluster membership

STDLIB ONLY - NO PYDANTIC.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from entityspine.domain.enums import (
    AddressType,
    AssetStatus,
    # v2.2.4 KG High-Confidence additions
    AssetType,
    CaseStatus,
    CaseType,
    ClaimStatus,
    ClusterRole,
    ContractStatus,
    ContractType,
    EventStatus,
    EventType,
    GeoType,
    ParticipantType,
    PositionType,
    ProductStatus,
    ProductType,
    RelationshipType,
    RoleType,
    TransactionCode,
)
from entityspine.domain.timestamps import generate_ulid, utc_now

# =============================================================================
# Node Reference Types
# =============================================================================


class NodeKind(str, Enum):
    """
    Kind of node in the knowledge graph.

    Core nodes:
    - ENTITY: Legal entities (orgs, persons)
    - SECURITY: Financial instruments
    - LISTING: Exchange-specific tickers

    Infrastructure nodes:
    - ADDRESS: Physical addresses
    - GEO: Geographic locations
    - CASE: Legal proceedings

    High-confidence additions (v2.2.4):
    - ASSET: Physical/tangible assets
    - CONTRACT: Legal agreements
    - PRODUCT: Products/services
    - BRAND: Brand identities
    - REGULATOR: Regulatory bodies (also entities)
    - EVENT: Discrete business events
    """

    # Core
    ENTITY = "entity"
    SECURITY = "security"
    LISTING = "listing"

    # Infrastructure
    ADDRESS = "address"
    GEO = "geo"
    CASE = "case"

    # High-confidence additions (v2.2.4)
    ASSET = "asset"
    CONTRACT = "contract"
    PRODUCT = "product"
    BRAND = "brand"
    REGULATOR = "regulator"
    EVENT = "event"


@dataclass(frozen=True, slots=True)
class NodeRef:
    """
    Polymorphic reference to any graph node.

    Used inside Relationship and other edge models to avoid
    separate nullable columns for each target type.

    Attributes:
        kind: Type of node being referenced.
        id: ULID of the referenced node.
    """

    kind: NodeKind
    id: str

    def __post_init__(self):
        """Validate NodeRef."""
        if not self.id or not self.id.strip():
            raise ValueError("NodeRef id cannot be empty")

    def __str__(self) -> str:
        return f"{self.kind.value}:{self.id}"

    @classmethod
    def entity(cls, entity_id: str) -> "NodeRef":
        """Create entity reference."""
        return cls(kind=NodeKind.ENTITY, id=entity_id)

    @classmethod
    def security(cls, security_id: str) -> "NodeRef":
        """Create security reference."""
        return cls(kind=NodeKind.SECURITY, id=security_id)

    @classmethod
    def listing(cls, listing_id: str) -> "NodeRef":
        """Create listing reference."""
        return cls(kind=NodeKind.LISTING, id=listing_id)

    @classmethod
    def address(cls, address_id: str) -> "NodeRef":
        """Create address reference."""
        return cls(kind=NodeKind.ADDRESS, id=address_id)

    @classmethod
    def geo(cls, geo_id: str) -> "NodeRef":
        """Create geo reference."""
        return cls(kind=NodeKind.GEO, id=geo_id)

    @classmethod
    def case(cls, case_id: str) -> "NodeRef":
        """Create case reference."""
        return cls(kind=NodeKind.CASE, id=case_id)

    # v2.2.4 High-confidence additions
    @classmethod
    def asset(cls, asset_id: str) -> "NodeRef":
        """Create asset reference."""
        return cls(kind=NodeKind.ASSET, id=asset_id)

    @classmethod
    def contract(cls, contract_id: str) -> "NodeRef":
        """Create contract reference."""
        return cls(kind=NodeKind.CONTRACT, id=contract_id)

    @classmethod
    def product(cls, product_id: str) -> "NodeRef":
        """Create product reference."""
        return cls(kind=NodeKind.PRODUCT, id=product_id)

    @classmethod
    def brand(cls, brand_id: str) -> "NodeRef":
        """Create brand reference."""
        return cls(kind=NodeKind.BRAND, id=brand_id)

    @classmethod
    def regulator(cls, regulator_id: str) -> "NodeRef":
        """Create regulator reference."""
        return cls(kind=NodeKind.REGULATOR, id=regulator_id)

    @classmethod
    def event(cls, event_id: str) -> "NodeRef":
        """Create event reference."""
        return cls(kind=NodeKind.EVENT, id=event_id)


# =============================================================================
# Person Role (Person ↔ Org Relationship)
# =============================================================================


@dataclass(frozen=True, slots=True)
class PersonRole:
    """
    A role/affiliation edge: Person → Organization.

    Represents "person X served as CFO of org Y from A→B".
    This is essential for person identity - people are often identified
    by their roles rather than stable identifiers.

    Attributes:
        role_id: ULID primary key.
        person_entity_id: FK to person Entity.
        org_entity_id: FK to organization Entity.
        role_type: Type of role (CEO, CFO, Director, etc.).
        role_title_raw: Original extracted title string (optional).
        valid_from: When the role started (truth time).
        valid_to: When the role ended (truth time).
        captured_at: When we observed this (observation time).
        source_system: Where the record came from.
        source_ref: Reference in source (accession number, vendor ID).
        confidence: Confidence score (0.0-1.0).
        status: Active/ended/disputed status.
        filing_id: Evidence: related filing ID.
        section_id: Evidence: related section ID.
        char_start: Evidence: character offset start.
        char_end: Evidence: character offset end.
        created_at: Record creation timestamp.
        updated_at: Record update timestamp.
    """

    person_entity_id: str
    org_entity_id: str
    role_type: RoleType

    role_id: str = field(default_factory=generate_ulid)
    role_title_raw: str | None = None

    # Temporal truth
    valid_from: date | None = None
    valid_to: date | None = None

    # Provenance
    captured_at: datetime = field(default_factory=utc_now)
    source_system: str = "unknown"
    source_ref: str | None = None
    confidence: float = 1.0
    status: ClaimStatus = ClaimStatus.ACTIVE

    # Evidence pointers
    filing_id: str | None = None  # UUID as string
    section_id: str | None = None
    char_start: int | None = None
    char_end: int | None = None

    # Timestamps
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    @property
    def is_current(self) -> bool:
        """Check if the role is currently active."""
        if self.valid_to is not None:
            return self.valid_to >= date.today()
        return self.status == ClaimStatus.ACTIVE

    def with_update(self) -> "PersonRole":
        """Create a copy with updated timestamp."""
        return PersonRole(
            role_id=self.role_id,
            person_entity_id=self.person_entity_id,
            org_entity_id=self.org_entity_id,
            role_type=self.role_type,
            role_title_raw=self.role_title_raw,
            valid_from=self.valid_from,
            valid_to=self.valid_to,
            captured_at=self.captured_at,
            source_system=self.source_system,
            source_ref=self.source_ref,
            confidence=self.confidence,
            status=self.status,
            filing_id=self.filing_id,
            section_id=self.section_id,
            char_start=self.char_start,
            char_end=self.char_end,
            created_at=self.created_at,
            updated_at=utc_now(),
        )


# =============================================================================
# Filing Participant
# =============================================================================


@dataclass(frozen=True, slots=True)
class FilingParticipant:
    """
    Structured participation in a filing: Person ↔ Filing ↔ Org.

    Represents who signed, who is mentioned, in what capacity.
    Enables queries like "Show all filings signed by this person."

    Attributes:
        participant_id: ULID primary key.
        filing_id: FK to py-sec-edgar filing.
        person_entity_id: FK to person Entity.
        org_entity_id: FK to organization Entity (context).
        participant_type: Type of participation (signer, officer, etc.).
        evidence_text: Extracted text evidence.
        char_start: Character offset start.
        char_end: Character offset end.
        confidence: Confidence score (0.0-1.0).
        captured_at: When we observed this.
        source_system: Where the record came from.
        source_ref: Reference in source system.
        created_at: Record creation timestamp.
        updated_at: Record update timestamp.
    """

    filing_id: str  # UUID as string
    person_entity_id: str
    participant_type: ParticipantType

    participant_id: str = field(default_factory=generate_ulid)
    org_entity_id: str | None = None

    # Evidence
    evidence_text: str | None = None
    char_start: int | None = None
    char_end: int | None = None

    # Provenance
    confidence: float = 1.0
    captured_at: datetime = field(default_factory=utc_now)
    source_system: str = "unknown"
    source_ref: str | None = None

    # Timestamps
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def with_update(self) -> "FilingParticipant":
        """Create a copy with updated timestamp."""
        return FilingParticipant(
            participant_id=self.participant_id,
            filing_id=self.filing_id,
            person_entity_id=self.person_entity_id,
            org_entity_id=self.org_entity_id,
            participant_type=self.participant_type,
            evidence_text=self.evidence_text,
            char_start=self.char_start,
            char_end=self.char_end,
            confidence=self.confidence,
            captured_at=self.captured_at,
            source_system=self.source_system,
            source_ref=self.source_ref,
            created_at=self.created_at,
            updated_at=utc_now(),
        )


# =============================================================================
# Ownership Position
# =============================================================================


@dataclass(frozen=True, slots=True)
class OwnershipPosition:
    """
    Ownership/holdings edge: Owner ↔ Issuer.

    Represents beneficial ownership, institutional holdings, insider positions.
    Supports 13F filings, 13D/13G, and vendor ownership data.

    Attributes:
        position_id: ULID primary key.
        owner_entity_id: FK to owner Entity (person or org).
        issuer_entity_id: FK to issuer Entity (org).
        security_id: Optional FK to specific Security.
        position_type: Type of position (beneficial owner, institutional, etc.).
        shares: Number of shares held.
        pct_outstanding: Percentage of outstanding shares.
        value_usd: Dollar value of position.
        as_of_date: Point-in-time snapshot date.
        captured_at: When we observed this.
        source_system: Where the record came from.
        source_ref: Reference in source system (13F filing, vendor).
        confidence: Confidence score (0.0-1.0).
        status: Active/superseded/disputed status.
        created_at: Record creation timestamp.
        updated_at: Record update timestamp.
    """

    owner_entity_id: str
    issuer_entity_id: str
    position_type: PositionType

    position_id: str = field(default_factory=generate_ulid)
    security_id: str | None = None

    # Position details
    shares: int | None = None
    pct_outstanding: float | None = None
    value_usd: Decimal | None = None

    # Temporal
    as_of_date: date | None = None

    # Provenance
    captured_at: datetime = field(default_factory=utc_now)
    source_system: str = "unknown"
    source_ref: str | None = None
    confidence: float = 1.0
    status: ClaimStatus = ClaimStatus.ACTIVE

    # Timestamps
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    @property
    def is_significant(self) -> bool:
        """Check if position is >= 5% (SEC reporting threshold)."""
        if self.pct_outstanding is not None:
            return self.pct_outstanding >= 5.0
        return False

    def with_update(self) -> "OwnershipPosition":
        """Create a copy with updated timestamp."""
        return OwnershipPosition(
            position_id=self.position_id,
            owner_entity_id=self.owner_entity_id,
            issuer_entity_id=self.issuer_entity_id,
            security_id=self.security_id,
            position_type=self.position_type,
            shares=self.shares,
            pct_outstanding=self.pct_outstanding,
            value_usd=self.value_usd,
            as_of_date=self.as_of_date,
            captured_at=self.captured_at,
            source_system=self.source_system,
            source_ref=self.source_ref,
            confidence=self.confidence,
            status=self.status,
            created_at=self.created_at,
            updated_at=utc_now(),
        )


# =============================================================================
# Insider Transaction
# =============================================================================


@dataclass(frozen=True, slots=True)
class InsiderTransaction:
    """
    Insider transaction from Forms 3/4/5.

    Represents stock purchases, sales, exercises, gifts by insiders.

    Attributes:
        tx_id: ULID primary key.
        insider_entity_id: FK to insider person Entity.
        issuer_entity_id: FK to issuer organization Entity.
        security_id: Optional FK to specific Security.
        transaction_date: Date of the transaction.
        transaction_code: SEC transaction code (P, S, A, M, etc.).
        shares: Number of shares transacted.
        price: Price per share.
        post_shares: Shares held after transaction.
        direct_indirect: 'D' for direct, 'I' for indirect.
        filing_id: FK to Form 3/4/5 filing.
        captured_at: When we observed this.
        source_system: Where the record came from.
        source_ref: Reference in source system.
        confidence: Confidence score.
        created_at: Record creation timestamp.
        updated_at: Record update timestamp.
    """

    insider_entity_id: str
    issuer_entity_id: str
    transaction_date: date
    transaction_code: TransactionCode

    tx_id: str = field(default_factory=generate_ulid)
    security_id: str | None = None

    # Transaction details
    shares: int | None = None
    price: Decimal | None = None
    post_shares: int | None = None
    direct_indirect: str = "D"  # 'D' or 'I'

    # Evidence
    filing_id: str | None = None

    # Provenance
    captured_at: datetime = field(default_factory=utc_now)
    source_system: str = "sec"
    source_ref: str | None = None
    confidence: float = 1.0

    # Timestamps
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    @property
    def is_purchase(self) -> bool:
        """Check if this is a purchase transaction."""
        return self.transaction_code == TransactionCode.P

    @property
    def is_sale(self) -> bool:
        """Check if this is a sale transaction."""
        return self.transaction_code == TransactionCode.S

    @property
    def total_value(self) -> Decimal | None:
        """Calculate total transaction value."""
        if self.shares is not None and self.price is not None:
            return Decimal(self.shares) * self.price
        return None

    def with_update(self) -> "InsiderTransaction":
        """Create a copy with updated timestamp."""
        return InsiderTransaction(
            tx_id=self.tx_id,
            insider_entity_id=self.insider_entity_id,
            issuer_entity_id=self.issuer_entity_id,
            security_id=self.security_id,
            transaction_date=self.transaction_date,
            transaction_code=self.transaction_code,
            shares=self.shares,
            price=self.price,
            post_shares=self.post_shares,
            direct_indirect=self.direct_indirect,
            filing_id=self.filing_id,
            captured_at=self.captured_at,
            source_system=self.source_system,
            source_ref=self.source_ref,
            confidence=self.confidence,
            created_at=self.created_at,
            updated_at=utc_now(),
        )


# =============================================================================
# Address
# =============================================================================


@dataclass(frozen=True, slots=True)
class Address:
    """
    Normalized address record.

    Addresses are high-signal for person/entity disambiguation.
    Store a normalized hash for matching + raw fields for display.

    Attributes:
        address_id: ULID primary key.
        line1: Street address line 1.
        line2: Street address line 2.
        city: City name.
        region: State/province/region.
        postal: Postal/ZIP code.
        country: Country code (ISO 3166-1 alpha-2).
        normalized_hash: Hash of normalized address for matching.
        created_at: Record creation timestamp.
        updated_at: Record update timestamp.
    """

    address_id: str = field(default_factory=generate_ulid)
    line1: str | None = None
    line2: str | None = None
    city: str | None = None
    region: str | None = None
    postal: str | None = None
    country: str = "US"
    normalized_hash: str | None = None

    # Timestamps
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    @property
    def display(self) -> str:
        """Format address for display."""
        parts = []
        if self.line1:
            parts.append(self.line1)
        if self.line2:
            parts.append(self.line2)
        city_region = []
        if self.city:
            city_region.append(self.city)
        if self.region:
            city_region.append(self.region)
        if city_region:
            parts.append(", ".join(city_region))
        if self.postal:
            parts.append(self.postal)
        if self.country and self.country != "US":
            parts.append(self.country)
        return ", ".join(parts)

    def with_update(self) -> "Address":
        """Create a copy with updated timestamp."""
        return Address(
            address_id=self.address_id,
            line1=self.line1,
            line2=self.line2,
            city=self.city,
            region=self.region,
            postal=self.postal,
            country=self.country,
            normalized_hash=self.normalized_hash,
            created_at=self.created_at,
            updated_at=utc_now(),
        )


# =============================================================================
# Entity Address (link table)
# =============================================================================


@dataclass(frozen=True, slots=True)
class EntityAddress:
    """
    Link between Entity and Address with temporal validity.

    Attributes:
        entity_id: FK to Entity.
        address_id: FK to Address.
        address_type: Type of address (business, mailing, etc.).
        valid_from: When the association started.
        valid_to: When the association ended.
        captured_at: When we observed this.
        source_system: Where the record came from.
        source_ref: Reference in source system.
        created_at: Record creation timestamp.
        updated_at: Record update timestamp.
    """

    entity_id: str
    address_id: str
    address_type: AddressType = AddressType.BUSINESS

    # Temporal
    valid_from: date | None = None
    valid_to: date | None = None

    # Provenance
    captured_at: datetime = field(default_factory=utc_now)
    source_system: str = "unknown"
    source_ref: str | None = None

    # Timestamps
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    @property
    def is_current(self) -> bool:
        """Check if the address is currently valid."""
        if self.valid_to is not None:
            return self.valid_to >= date.today()
        return True

    def with_update(self) -> "EntityAddress":
        """Create a copy with updated timestamp."""
        return EntityAddress(
            entity_id=self.entity_id,
            address_id=self.address_id,
            address_type=self.address_type,
            valid_from=self.valid_from,
            valid_to=self.valid_to,
            captured_at=self.captured_at,
            source_system=self.source_system,
            source_ref=self.source_ref,
            created_at=self.created_at,
            updated_at=utc_now(),
        )


# =============================================================================
# Entity Relationship (Generic Entity ↔ Entity)
# =============================================================================


@dataclass(frozen=True, slots=True)
class EntityRelationship:
    """
    Generic relationship edge: Entity ↔ Entity.

    Used for corporate structure, business relationships, etc.

    Attributes:
        relationship_id: ULID primary key.
        from_entity_id: FK to source Entity.
        to_entity_id: FK to target Entity.
        relationship_type: Type of relationship.
        valid_from: When the relationship started.
        valid_to: When the relationship ended.
        captured_at: When we observed this.
        source_system: Where the record came from.
        source_ref: Reference in source system.
        confidence: Confidence score.
        status: Active/disputed/retracted status.
        evidence_text: Extracted text evidence.
        filing_id: Evidence: related filing ID.
        created_at: Record creation timestamp.
        updated_at: Record update timestamp.
    """

    from_entity_id: str
    to_entity_id: str
    relationship_type: RelationshipType

    relationship_id: str = field(default_factory=generate_ulid)

    # Temporal
    valid_from: date | None = None
    valid_to: date | None = None

    # Provenance
    captured_at: datetime = field(default_factory=utc_now)
    source_system: str = "unknown"
    source_ref: str | None = None
    confidence: float = 1.0
    status: ClaimStatus = ClaimStatus.ACTIVE

    # Evidence
    evidence_text: str | None = None
    filing_id: str | None = None

    # Timestamps
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    @property
    def is_current(self) -> bool:
        """Check if the relationship is currently active."""
        if self.valid_to is not None:
            return self.valid_to >= date.today()
        return self.status == ClaimStatus.ACTIVE

    def with_update(self) -> "EntityRelationship":
        """Create a copy with updated timestamp."""
        return EntityRelationship(
            relationship_id=self.relationship_id,
            from_entity_id=self.from_entity_id,
            to_entity_id=self.to_entity_id,
            relationship_type=self.relationship_type,
            valid_from=self.valid_from,
            valid_to=self.valid_to,
            captured_at=self.captured_at,
            source_system=self.source_system,
            source_ref=self.source_ref,
            confidence=self.confidence,
            status=self.status,
            evidence_text=self.evidence_text,
            filing_id=self.filing_id,
            created_at=self.created_at,
            updated_at=utc_now(),
        )


# =============================================================================
# Entity Cluster (Anti-Duplication)
# =============================================================================


@dataclass(frozen=True, slots=True)
class EntityCluster:
    """
    Cluster for potential duplicate entities.

    Supports gradual consolidation without destructive merges.
    Use cluster-first, merge-later pattern for safety.

    Attributes:
        cluster_id: ULID primary key.
        reason: Why entities were clustered (name similarity, etc.).
        created_at: Cluster creation timestamp.
        updated_at: Cluster update timestamp.
    """

    cluster_id: str = field(default_factory=generate_ulid)
    reason: str | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def with_update(self) -> "EntityCluster":
        """Create a copy with updated timestamp."""
        return EntityCluster(
            cluster_id=self.cluster_id,
            reason=self.reason,
            created_at=self.created_at,
            updated_at=utc_now(),
        )


@dataclass(frozen=True, slots=True)
class EntityClusterMember:
    """
    Membership of an entity in a cluster.

    Attributes:
        cluster_id: FK to EntityCluster.
        entity_id: FK to Entity.
        role: Role in cluster (canonical, member, provisional).
        confidence: Confidence that entity belongs in cluster.
        created_at: Membership creation timestamp.
        updated_at: Membership update timestamp.
    """

    cluster_id: str
    entity_id: str
    role: ClusterRole = ClusterRole.MEMBER
    confidence: float = 1.0
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    @property
    def is_canonical(self) -> bool:
        """Check if this is the canonical entity in the cluster."""
        return self.role == ClusterRole.CANONICAL

    def with_update(self) -> "EntityClusterMember":
        """Create a copy with updated timestamp."""
        return EntityClusterMember(
            cluster_id=self.cluster_id,
            entity_id=self.entity_id,
            role=self.role,
            confidence=self.confidence,
            created_at=self.created_at,
            updated_at=utc_now(),
        )


# =============================================================================
# Geo (Geographic Location Node)
# =============================================================================


@dataclass(frozen=True, slots=True)
class Geo:
    """
    Geographic location node.

    Represents countries, states, cities for location-based relationships.
    Uses ISO codes where available for standardization.

    Attributes:
        geo_id: ULID primary key.
        geo_type: Level of geography (country, state, city, etc.).
        name: Display name of the location.
        iso_code: ISO 3166-1 (country) or ISO 3166-2 (subdivision) code.
        parent_geo_id: FK to parent Geo (e.g., state's country).
        created_at: Record creation timestamp.
        updated_at: Record update timestamp.
    """

    name: str
    geo_type: GeoType

    geo_id: str = field(default_factory=generate_ulid)
    iso_code: str | None = None
    parent_geo_id: str | None = None

    # Timestamps
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def __post_init__(self):
        """Validate Geo."""
        if not self.name or not self.name.strip():
            raise ValueError("Geo name cannot be empty")

    def with_update(self) -> "Geo":
        """Create a copy with updated timestamp."""
        return Geo(
            geo_id=self.geo_id,
            name=self.name,
            geo_type=self.geo_type,
            iso_code=self.iso_code,
            parent_geo_id=self.parent_geo_id,
            created_at=self.created_at,
            updated_at=utc_now(),
        )


# =============================================================================
# Case (Legal Proceedings/Investigations)
# =============================================================================


@dataclass(frozen=True, slots=True)
class Case:
    """
    Legal proceeding, investigation, or enforcement action.

    Represents lawsuits, SEC investigations, regulatory actions.
    Cases involve entities and may reference filings as evidence.

    Attributes:
        case_id: ULID primary key.
        case_type: Type of case (lawsuit, investigation, etc.).
        case_number: Official case/docket number.
        title: Case title/caption.
        status: Current status (open, closed, etc.).
        authority_entity_id: FK to authority Entity (court, regulator).
        target_entity_id: FK to primary target Entity.
        opened_date: When the case was filed/opened.
        closed_date: When the case was closed/resolved.
        description: Brief description of the case.
        source_system: Where the record came from.
        source_ref: Reference in source system.
        filing_id: Related SEC filing (if applicable).
        captured_at: When we observed this.
        created_at: Record creation timestamp.
        updated_at: Record update timestamp.
    """

    case_type: CaseType
    title: str

    case_id: str = field(default_factory=generate_ulid)
    case_number: str | None = None
    status: CaseStatus = CaseStatus.UNKNOWN

    # Related entities
    authority_entity_id: str | None = None  # Court/regulator
    target_entity_id: str | None = None  # Primary defendant/target

    # Temporal
    opened_date: date | None = None
    closed_date: date | None = None

    # Details
    description: str | None = None

    # Provenance
    source_system: str = "unknown"
    source_ref: str | None = None
    filing_id: str | None = None
    captured_at: datetime = field(default_factory=utc_now)

    # Timestamps
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def __post_init__(self):
        """Validate Case."""
        if not self.title or not self.title.strip():
            raise ValueError("Case title cannot be empty")

    @property
    def is_open(self) -> bool:
        """Check if the case is still open."""
        return self.status in (CaseStatus.OPEN, CaseStatus.PENDING)

    def with_update(self) -> "Case":
        """Create a copy with updated timestamp."""
        return Case(
            case_id=self.case_id,
            case_type=self.case_type,
            case_number=self.case_number,
            title=self.title,
            status=self.status,
            authority_entity_id=self.authority_entity_id,
            target_entity_id=self.target_entity_id,
            opened_date=self.opened_date,
            closed_date=self.closed_date,
            description=self.description,
            source_system=self.source_system,
            source_ref=self.source_ref,
            filing_id=self.filing_id,
            captured_at=self.captured_at,
            created_at=self.created_at,
            updated_at=utc_now(),
        )


# =============================================================================
# Generic Relationship (with NodeRef for polymorphic source/target)
# =============================================================================


@dataclass(frozen=True, slots=True)
class Relationship:
    """
    Evidence-backed, time-bounded relationship between two nodes.

    This is a more generic relationship model that uses NodeRef for
    polymorphic source/target references (can link any node types).

    Use EntityRelationship for entity-to-entity relationships.
    Use Relationship for cross-type relationships (entity→geo, entity→case).

    Attributes:
        relationship_id: ULID primary key.
        source_ref: Reference to source node.
        target_ref: Reference to target node.
        relationship_type: Type of relationship.
        subtype: Optional subtype for finer classification.
        valid_from: When the relationship started (business validity).
        valid_to: When the relationship ended (business validity).
        captured_at: When we observed this.
        source_system: Where the record came from.
        source_id: Reference in source system.
        confidence: Confidence score (0.0-1.0).
        evidence_filing_id: FK to filing that evidences this.
        evidence_section_id: FK to section within filing.
        evidence_excerpt_hash: Hash of the evidence text.
        evidence_snippet: Short snippet of evidence (display only).
        metrics: Small dict of additional metrics.
        created_at: Record creation timestamp.
        updated_at: Record update timestamp.
    """

    source_ref: NodeRef
    target_ref: NodeRef
    relationship_type: RelationshipType

    relationship_id: str = field(default_factory=generate_ulid)
    subtype: str | None = None

    # Temporal (business validity)
    valid_from: date | None = None
    valid_to: date | None = None

    # Provenance
    captured_at: datetime = field(default_factory=utc_now)
    source_system: str = "unknown"
    source_id: str | None = None
    confidence: float = 1.0

    # Evidence pointers
    evidence_filing_id: str | None = None
    evidence_section_id: str | None = None
    evidence_excerpt_hash: str | None = None
    evidence_snippet: str | None = None  # Short excerpt for display

    # Additional metrics (stdlib dict)
    metrics: Mapping[str, Any] | None = None

    # Timestamps
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    @property
    def is_current(self) -> bool:
        """Check if the relationship is currently active."""
        if self.valid_to is not None:
            return self.valid_to >= date.today()
        return True

    def with_update(self) -> "Relationship":
        """Create a copy with updated timestamp."""
        return Relationship(
            relationship_id=self.relationship_id,
            source_ref=self.source_ref,
            target_ref=self.target_ref,
            relationship_type=self.relationship_type,
            subtype=self.subtype,
            valid_from=self.valid_from,
            valid_to=self.valid_to,
            captured_at=self.captured_at,
            source_system=self.source_system,
            source_id=self.source_id,
            confidence=self.confidence,
            evidence_filing_id=self.evidence_filing_id,
            evidence_section_id=self.evidence_section_id,
            evidence_excerpt_hash=self.evidence_excerpt_hash,
            evidence_snippet=self.evidence_snippet,
            metrics=self.metrics,
            created_at=self.created_at,
            updated_at=utc_now(),
        )


# =============================================================================
# Role Assignment (Alternative to PersonRole using NodeRef pattern)
# =============================================================================


@dataclass(frozen=True, slots=True)
class RoleAssignment:
    """
    Time-bounded role for a person within an org.

    Alternative to PersonRole that follows the same pattern as other
    domain models. Can be used interchangeably or as a complement.

    Attributes:
        role_assignment_id: ULID primary key.
        person_entity_id: FK to person Entity (EntityType=PERSON).
        org_entity_id: FK to org Entity (EntityType=ORGANIZATION/FUND/etc.).
        role_type: Type of role (CEO, CFO, etc.).
        title: Exact title string (optional).
        start_date: When the role started.
        end_date: When the role ended.
        confidence: Confidence score (0.0-1.0).
        captured_at: When we observed this.
        source_system: Where the record came from.
        source_ref: Reference in source system.
        filing_id: Evidence: related filing ID.
        section_id: Evidence: section within filing.
        snippet_hash: Hash of evidence snippet.
        created_at: Record creation timestamp.
        updated_at: Record update timestamp.
    """

    person_entity_id: str
    org_entity_id: str
    role_type: RoleType

    role_assignment_id: str = field(default_factory=generate_ulid)
    title: str | None = None

    # Temporal
    start_date: date | None = None
    end_date: date | None = None

    # Confidence
    confidence: float = 1.0

    # Provenance
    captured_at: datetime = field(default_factory=utc_now)
    source_system: str = "unknown"
    source_ref: str | None = None

    # Evidence
    filing_id: str | None = None
    section_id: str | None = None
    snippet_hash: str | None = None

    # Timestamps
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    @property
    def is_current(self) -> bool:
        """Check if the role is currently active."""
        if self.end_date is not None:
            return self.end_date >= date.today()
        return True

    def with_update(self) -> "RoleAssignment":
        """Create a copy with updated timestamp."""
        return RoleAssignment(
            role_assignment_id=self.role_assignment_id,
            person_entity_id=self.person_entity_id,
            org_entity_id=self.org_entity_id,
            role_type=self.role_type,
            title=self.title,
            start_date=self.start_date,
            end_date=self.end_date,
            confidence=self.confidence,
            captured_at=self.captured_at,
            source_system=self.source_system,
            source_ref=self.source_ref,
            filing_id=self.filing_id,
            section_id=self.section_id,
            snippet_hash=self.snippet_hash,
            created_at=self.created_at,
            updated_at=utc_now(),
        )


# =============================================================================
# Asset (v2.2.4 High-Confidence Addition)
# =============================================================================


@dataclass(frozen=True, slots=True)
class Asset:
    """
    Physical or tangible asset node.

    Represents facilities, data centers, vessels, aircraft, plants, property.
    Assets are typically owned or operated by entities.

    Attributes:
        asset_id: ULID primary key.
        asset_type: Type of asset (facility, vessel, etc.).
        name: Display name of the asset.
        description: Optional description.
        owner_entity_id: FK to owning Entity (if known).
        operator_entity_id: FK to operating Entity (if different from owner).
        geo_id: FK to Geo (location).
        address_id: FK to Address (physical address).
        status: Lifecycle status.
        source_system: Where the record came from.
        source_id: ID in the source system.
        captured_at: When we observed this.
        created_at: Record creation timestamp.
        updated_at: Record update timestamp.
    """

    name: str
    asset_type: AssetType

    asset_id: str = field(default_factory=generate_ulid)
    description: str | None = None

    # Ownership (prefer relationships, but convenience fields are OK)
    owner_entity_id: str | None = None
    operator_entity_id: str | None = None

    # Location
    geo_id: str | None = None
    address_id: str | None = None

    # Status
    status: AssetStatus = AssetStatus.ACTIVE

    # Provenance
    source_system: str = "unknown"
    source_id: str | None = None
    captured_at: datetime = field(default_factory=utc_now)

    # Timestamps
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def __post_init__(self):
        """Validate Asset."""
        if not self.name or not self.name.strip():
            raise ValueError("Asset name cannot be empty")

    def with_update(self, **kwargs) -> "Asset":
        """Create a copy with updated fields."""
        from dataclasses import replace

        kwargs.setdefault("updated_at", utc_now())
        return replace(self, **kwargs)


# =============================================================================
# Contract (v2.2.4 High-Confidence Addition)
# =============================================================================


@dataclass(frozen=True, slots=True)
class Contract:
    """
    Legal contract/agreement node.

    Represents credit facilities, leases, material agreements, licenses.
    Parties are tracked via relationships (PARTY_TO, COUNTERPARTY_TO).

    Attributes:
        contract_id: ULID primary key.
        contract_type: Type of contract.
        title: Contract title or description.
        effective_date: When the contract takes effect.
        termination_date: When the contract ends.
        status: Lifecycle status.
        value_usd: Contract value in USD (if known).
        source_system: Where the record came from.
        source_id: ID in the source system.
        filing_id: Related SEC filing (8-K material contract).
        content_hash: Hash of contract document (for dedup).
        summary: Brief summary text.
        captured_at: When we observed this.
        created_at: Record creation timestamp.
        updated_at: Record update timestamp.
    """

    title: str
    contract_type: ContractType

    contract_id: str = field(default_factory=generate_ulid)

    # Temporal
    effective_date: date | None = None
    termination_date: date | None = None

    # Status
    status: ContractStatus = ContractStatus.ACTIVE

    # Value
    value_usd: Decimal | None = None

    # Provenance
    source_system: str = "unknown"
    source_id: str | None = None
    filing_id: str | None = None
    captured_at: datetime = field(default_factory=utc_now)

    # Content placeholders (not required in core)
    content_hash: str | None = None
    summary: str | None = None

    # Timestamps
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def __post_init__(self):
        """Validate Contract."""
        if not self.title or not self.title.strip():
            raise ValueError("Contract title cannot be empty")

    @property
    def is_active(self) -> bool:
        """Check if contract is currently active."""
        if self.status != ContractStatus.ACTIVE:
            return False
        return not (self.termination_date and self.termination_date < date.today())

    def with_update(self, **kwargs) -> "Contract":
        """Create a copy with updated fields."""
        from dataclasses import replace

        kwargs.setdefault("updated_at", utc_now())
        return replace(self, **kwargs)


# =============================================================================
# Product (v2.2.4 High-Confidence Addition)
# =============================================================================


@dataclass(frozen=True, slots=True)
class Product:
    """
    Product or service node.

    Represents drugs, devices, software, services, consumer goods.
    Ownership is tracked via owner_entity_id or MANUFACTURES relationship.

    Attributes:
        product_id: ULID primary key.
        product_type: Type of product.
        name: Product name.
        description: Optional description.
        owner_entity_id: FK to owning/manufacturing Entity.
        status: Lifecycle status.
        source_system: Where the record came from.
        source_id: ID in the source system.
        captured_at: When we observed this.
        created_at: Record creation timestamp.
        updated_at: Record update timestamp.
    """

    name: str
    product_type: ProductType

    product_id: str = field(default_factory=generate_ulid)
    description: str | None = None

    # Ownership
    owner_entity_id: str | None = None

    # Status
    status: ProductStatus = ProductStatus.ACTIVE

    # Provenance
    source_system: str = "unknown"
    source_id: str | None = None
    captured_at: datetime = field(default_factory=utc_now)

    # Timestamps
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def __post_init__(self):
        """Validate Product."""
        if not self.name or not self.name.strip():
            raise ValueError("Product name cannot be empty")

    def with_update(self, **kwargs) -> "Product":
        """Create a copy with updated fields."""
        from dataclasses import replace

        kwargs.setdefault("updated_at", utc_now())
        return replace(self, **kwargs)


# =============================================================================
# Brand (v2.2.4 High-Confidence Addition)
# =============================================================================


@dataclass(frozen=True, slots=True)
class Brand:
    """
    Brand identity node.

    Represents brand names owned by entities and applied to products.

    Attributes:
        brand_id: ULID primary key.
        name: Brand name.
        owner_entity_id: FK to owning Entity.
        description: Optional description.
        source_system: Where the record came from.
        source_id: ID in the source system.
        captured_at: When we observed this.
        created_at: Record creation timestamp.
        updated_at: Record update timestamp.
    """

    name: str

    brand_id: str = field(default_factory=generate_ulid)
    owner_entity_id: str | None = None
    description: str | None = None

    # Provenance
    source_system: str = "unknown"
    source_id: str | None = None
    captured_at: datetime = field(default_factory=utc_now)

    # Timestamps
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def __post_init__(self):
        """Validate Brand."""
        if not self.name or not self.name.strip():
            raise ValueError("Brand name cannot be empty")

    def with_update(self, **kwargs) -> "Brand":
        """Create a copy with updated fields."""
        from dataclasses import replace

        kwargs.setdefault("updated_at", utc_now())
        return replace(self, **kwargs)


# =============================================================================
# Event (v2.2.4 High-Confidence Addition - Graph Native)
# =============================================================================


@dataclass(frozen=True, slots=True)
class Event:
    """
    Discrete business event node.

    Represents M&A, legal events, cyber incidents, management changes, etc.
    Graph-native design for KG completeness.

    Note: py-sec-edgar has its own event system. Event nodes here are for
    KG traversal and can be projected from py-sec-edgar events.

    Attributes:
        event_id: ULID primary key.
        event_type: Type of event.
        title: Event title/headline.
        description: Optional longer description.
        status: Event status.
        occurred_on: When the event happened (if known).
        announced_on: When the event was announced.
        payload: Additional structured data (stdlib dict).
        source_system: Where the record came from.
        source_id: ID in the source system.
        evidence_filing_id: FK to filing that evidences this.
        evidence_section_id: Section within filing.
        evidence_snippet: Short evidence text.
        confidence: Confidence score (0.0-1.0).
        captured_at: When we observed this.
        created_at: Record creation timestamp.
        updated_at: Record update timestamp.
    """

    event_type: EventType
    title: str

    event_id: str = field(default_factory=generate_ulid)
    description: str | None = None
    status: EventStatus = EventStatus.ANNOUNCED

    # Temporal
    occurred_on: date | None = None
    announced_on: date | None = None

    # Payload (stdlib dict, not Mapping for mutability during construction)
    payload: dict | None = None

    # Evidence pointers
    evidence_filing_id: str | None = None
    evidence_section_id: str | None = None
    evidence_snippet: str | None = None
    confidence: float = 1.0

    # Provenance
    source_system: str = "unknown"
    source_id: str | None = None
    captured_at: datetime = field(default_factory=utc_now)

    # Timestamps
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def __post_init__(self):
        """Validate Event."""
        if not self.title or not self.title.strip():
            raise ValueError("Event title cannot be empty")

    @property
    def is_completed(self) -> bool:
        """Check if event is completed."""
        return self.status == EventStatus.COMPLETED

    def with_update(self, **kwargs) -> "Event":
        """Create a copy with updated fields."""
        from dataclasses import replace

        kwargs.setdefault("updated_at", utc_now())
        return replace(self, **kwargs)
