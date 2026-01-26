"""
EntitySpine Canonical Domain Models (stdlib-only).

This package contains the canonical domain models using stdlib dataclasses.
NO PYDANTIC OR ORM DEPENDENCIES ALLOWED HERE.

Tier 0/1 Guarantee: This package has zero non-stdlib dependencies.

All business rules and validation logic live here. Pydantic and ORM
wrappers (in entityspine.ext.*) must delegate to these validators.

v2.2.3 Semantics:
- IdentifierClaim is the canonical source of truth for identifiers
- Entity/Security have NO identifier storage fields
- Listing has ticker (ticker is listing-scoped)
- Scheme-scope enforcement (CIK→entity, ISIN→security, TICKER→listing)
- VendorNamespace for multi-vendor crosswalks
- captured_at vs valid_from/valid_to time semantics
- ResolutionResult with tier honesty warnings/limits
"""

from entityspine.domain.enums import (
    EntityType,
    EntityStatus,
    SecurityType,
    SecurityStatus,
    ListingStatus,
    IdentifierScheme,
    ClaimStatus,
    VendorNamespace,
    IdentifierScope,
    ResolutionStatus,
    ResolutionTier,
    ResolutionWarning,
    MatchReason,
    # Knowledge Graph enums
    RoleType,
    ParticipantType,
    PositionType,
    TransactionCode,
    AddressType,
    ClusterRole,
    RelationshipType,
    CaseType,
    CaseStatus,
    GeoType,
    # v2.2.4 KG High-Confidence enums
    AssetType,
    AssetStatus,
    ContractType,
    ContractStatus,
    ProductType,
    ProductStatus,
    EventType,
    EventStatus,
)

from entityspine.domain.entity import Entity
from entityspine.domain.security import Security
from entityspine.domain.listing import Listing
from entityspine.domain.claim import IdentifierClaim
from entityspine.domain.candidate import ResolutionCandidate
from entityspine.domain.resolution import ResolutionResult

from entityspine.domain.validators import (
    # Normalizers
    normalize_cik,
    normalize_lei,
    normalize_isin,
    normalize_cusip,
    normalize_sedol,
    normalize_figi,
    normalize_ein,
    normalize_ticker,
    normalize_mic,
    # Person/Address normalizers
    normalize_person_name,
    normalize_person_name_for_search,
    normalize_country_code,
    normalize_region_code,
    normalize_postal_code,
    normalize_address_line,
    compute_address_hash,
    # Validators
    validate_cik,
    validate_lei,
    validate_isin,
    validate_cusip,
    validate_sedol,
    validate_figi,
    validate_ein,
    validate_ticker,
    validate_mic,
    validate_person_name,
    # Utilities
    normalize_and_validate,
    get_scope_for_scheme,
    validate_scheme_scope,
    SCHEME_SCOPES,
)

from entityspine.domain.factories import (
    found_result,
    not_found_result,
    ambiguous_result,
    create_entity,
    create_security,
    create_listing,
    create_claim,
    create_candidate,
)

from entityspine.domain.protocols import (
    StorageLifecycleProtocol,
    EntityStoreProtocol,
    ListingStoreProtocol,
    SecurityStoreProtocol,
    ClaimStoreProtocol,
    SearchProtocol,
    ResolverProtocol,
    FullStoreProtocol,
)

# Knowledge Graph domain models
from entityspine.domain.graph import (
    NodeKind,
    NodeRef,
    PersonRole,
    FilingParticipant,
    OwnershipPosition,
    InsiderTransaction,
    Address,
    EntityAddress,
    Geo,
    EntityRelationship,
    Case,
    EntityCluster,
    EntityClusterMember,
    Relationship,
    RoleAssignment,
    # v2.2.4 KG High-Confidence node types
    Asset,
    Contract,
    Product,
    Brand,
    Event,
)

__all__ = [
    # Enums
    "EntityType",
    "EntityStatus",
    "SecurityType",
    "SecurityStatus",
    "ListingStatus",
    "IdentifierScheme",
    "ClaimStatus",
    "VendorNamespace",
    "IdentifierScope",
    "ResolutionStatus",
    "ResolutionTier",
    "ResolutionWarning",
    "MatchReason",
    # Knowledge Graph enums
    "RoleType",
    "ParticipantType",
    "PositionType",
    "TransactionCode",
    "AddressType",
    "ClusterRole",
    "RelationshipType",
    "CaseType",
    "CaseStatus",
    "GeoType",
    # v2.2.4 KG High-Confidence enums
    "AssetType",
    "AssetStatus",
    "ContractType",
    "ContractStatus",
    "ProductType",
    "ProductStatus",
    "EventType",
    "EventStatus",
    # Domain models
    "Entity",
    "Security",
    "Listing",
    "IdentifierClaim",
    "ResolutionCandidate",
    "ResolutionResult",
    # Knowledge Graph models
    "NodeKind",
    "NodeRef",
    "PersonRole",
    "FilingParticipant",
    "OwnershipPosition",
    "InsiderTransaction",
    "Address",
    "EntityAddress",
    "Geo",
    "EntityRelationship",
    "Case",
    "EntityCluster",
    "EntityClusterMember",
    "Relationship",
    "RoleAssignment",
    # v2.2.4 KG High-Confidence node types
    "Asset",
    "Contract",
    "Product",
    "Brand",
    "Event",
    # Validators
    "normalize_cik",
    "normalize_lei",
    "normalize_isin",
    "normalize_cusip",
    "normalize_sedol",
    "normalize_figi",
    "normalize_ein",
    "normalize_ticker",
    "normalize_mic",
    "normalize_person_name",
    "normalize_person_name_for_search",
    "normalize_country_code",
    "normalize_region_code",
    "normalize_postal_code",
    "normalize_address_line",
    "compute_address_hash",
    "validate_cik",
    "validate_lei",
    "validate_isin",
    "validate_cusip",
    "validate_sedol",
    "validate_figi",
    "validate_ein",
    "validate_ticker",
    "validate_mic",
    "validate_person_name",
    "normalize_and_validate",
    "get_scope_for_scheme",
    "validate_scheme_scope",
    "SCHEME_SCOPES",
    # Factories
    "found_result",
    "not_found_result",
    "ambiguous_result",
    "create_entity",
    "create_security",
    "create_listing",
    "create_claim",
    "create_candidate",
    # Protocols (stdlib typing.Protocol)
    "StorageLifecycleProtocol",
    "EntityStoreProtocol",
    "ListingStoreProtocol",
    "SecurityStoreProtocol",
    "ClaimStoreProtocol",
    "SearchProtocol",
    "ResolverProtocol",
    "FullStoreProtocol",
]
