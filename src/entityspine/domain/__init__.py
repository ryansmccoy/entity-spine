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

from entityspine.domain.candidate import ResolutionCandidate
from entityspine.domain.claim import IdentifierClaim
from entityspine.domain.entity import Entity
from entityspine.domain.enums import (
    # Observation enums (v2.2.5)
    AccountingBasis,
    AddressType,
    AssetStatus,
    # v2.2.4 KG High-Confidence enums
    AssetType,
    CaseStatus,
    CaseType,
    ClaimStatus,
    ClusterRole,
    ContractStatus,
    ContractType,
    EntityStatus,
    EntityType,
    EstimateScope,
    EventStatus,
    EventType,
    GeoType,
    IdentifierScheme,
    IdentifierScope,
    ListingStatus,
    MatchReason,
    MetricCategory,
    MetricCode,
    ObservationType,
    ParticipantType,
    PeriodType,
    PerShareType,
    PositionType,
    Presentation,
    ProductStatus,
    ProductType,
    ProvenanceKind,
    RelationshipType,
    ResolutionStatus,
    ResolutionTier,
    ResolutionWarning,
    # Knowledge Graph enums
    RoleType,
    # v2.3.0 Compliance/Sanctions enum
    SanctionStatus,
    ScopeType,
    SecurityStatus,
    SecurityType,
    TransactionCode,
    VendorNamespace,
)
from entityspine.domain.factories import (
    ambiguous_result,
    create_candidate,
    create_claim,
    create_entity,
    create_listing,
    create_security,
    found_result,
    not_found_result,
)

# Knowledge Graph domain models
from entityspine.domain.graph import (
    Address,
    # v2.2.4 KG High-Confidence node types
    Asset,
    Brand,
    Case,
    Contract,
    EntityAddress,
    EntityCluster,
    EntityClusterMember,
    EntityRelationship,
    Event,
    FilingParticipant,
    Geo,
    InsiderTransaction,
    NodeKind,
    NodeRef,
    OwnershipPosition,
    PersonRole,
    Product,
    Relationship,
    RoleAssignment,
    # Graph traversal result types
    RelatedEntity,
    OfficerInfo,
    PathStep,
    EntityPath,
    EntityNetwork,
)
from entityspine.domain.listing import Listing
from entityspine.domain.protocols import (
    ClaimStoreProtocol,
    EntityStoreProtocol,
    FullStoreProtocol,
    ListingStoreProtocol,
    ResolverProtocol,
    SearchProtocol,
    SecurityStoreProtocol,
    StorageLifecycleProtocol,
)
from entityspine.domain.resolution import ResolutionResult
from entityspine.domain.security import Security

# Timeline models
from entityspine.domain.timeline import (
    TimelineEventType,
    TimelineEvent,
    EntitySnapshot,
    StateDiff,
)

# Clustering models
from entityspine.domain.clustering import (
    ClusterStatus,
    DuplicateCandidate,
    ClusterInfo,
    BlockingConfig,
)

# Financial observation models
from entityspine.domain.financial_observation import (
    MetricCategory as OldMetricCategory,
    MetricCode as OldMetricCode,
    MetricVariant,
    ObservationType as OldObservationType,
    DataSourceType,
    FiscalPeriodType,
    FiscalPeriod as OldFiscalPeriod,
    DataSource,
    MetricDefinition,
    FinancialObservation,
    ObservationSet as OldObservationSet,
    # Factory functions
    create_factset_observation,
    create_bloomberg_observation,
    create_sec_observation,
    create_analyst_estimate,
    create_press_release_observation,
)

# v2.2.5 Observation models (new architecture)
from entityspine.domain.observation import (
    MetricSpec,
    FiscalPeriod,
    ProvenanceRef,
    SourceKey,
    EstimateInfo,
    ValueWithUnits,
    Observation,
    ObservationSet,
)

from entityspine.domain.validators import (
    SCHEME_SCOPES,
    compute_address_hash,
    get_scope_for_scheme,
    normalize_address_line,
    # Utilities
    normalize_and_validate,
    # Normalizers
    normalize_cik,
    normalize_country_code,
    normalize_cusip,
    normalize_ein,
    normalize_figi,
    normalize_isin,
    normalize_lei,
    normalize_mic,
    # Person/Address normalizers
    normalize_person_name,
    normalize_person_name_for_search,
    normalize_postal_code,
    normalize_region_code,
    normalize_sedol,
    normalize_ticker,
    # Validators
    validate_cik,
    validate_cusip,
    validate_ein,
    validate_figi,
    validate_isin,
    validate_lei,
    validate_mic,
    validate_person_name,
    validate_scheme_scope,
    validate_sedol,
    validate_ticker,
)

__all__ = [
    "SCHEME_SCOPES",
    # Observation enums (v2.2.5)
    "AccountingBasis",
    "Address",
    "AddressType",
    # v2.2.4 KG High-Confidence node types
    "Asset",
    "AssetStatus",
    # v2.2.4 KG High-Confidence enums
    "AssetType",
    "Brand",
    "Case",
    "CaseStatus",
    "CaseType",
    "ClaimStatus",
    "ClaimStoreProtocol",
    "ClusterRole",
    "Contract",
    "ContractStatus",
    "ContractType",
    # Domain models
    "Entity",
    "EntityAddress",
    "EntityCluster",
    "EntityClusterMember",
    "EntityRelationship",
    "EntityStatus",
    "EntityStoreProtocol",
    # Enums
    "EntityType",
    "EstimateInfo",
    "EstimateScope",
    "Event",
    "EventStatus",
    "EventType",
    "FilingParticipant",
    "FiscalPeriod",
    "FullStoreProtocol",
    "Geo",
    "GeoType",
    "IdentifierClaim",
    "IdentifierScheme",
    "IdentifierScope",
    "InsiderTransaction",
    "Listing",
    "ListingStatus",
    "ListingStoreProtocol",
    "MatchReason",
    "MetricCategory",
    "MetricCode",
    "MetricSpec",
    # Knowledge Graph models
    "NodeKind",
    "NodeRef",
    "Observation",
    "ObservationSet",
    "ObservationType",
    "OwnershipPosition",
    "ParticipantType",
    "PeriodType",
    "PerShareType",
    "PersonRole",
    "PositionType",
    "Presentation",
    "Product",
    "ProductStatus",
    "ProductType",
    "ProvenanceKind",
    "ProvenanceRef",
    "Relationship",
    "RelationshipType",
    "ResolutionCandidate",
    "ResolutionResult",
    "ResolutionStatus",
    "ResolutionTier",
    "ResolutionWarning",
    "ResolverProtocol",
    "RoleAssignment",
    # Knowledge Graph enums
    "RoleType",
    # v2.3.0 Compliance/Sanctions enum
    "SanctionStatus",
    "ScopeType",
    "SearchProtocol",
    "Security",
    "SecurityStatus",
    "SecurityStoreProtocol",
    "SecurityType",
    "SourceKey",
    # Protocols (stdlib typing.Protocol)
    "StorageLifecycleProtocol",
    "TransactionCode",
    "ValueWithUnits",
    "VendorNamespace",
    "ambiguous_result",
    "compute_address_hash",
    "create_candidate",
    "create_claim",
    "create_entity",
    "create_listing",
    "create_security",
    # Factories
    "found_result",
    "get_scope_for_scheme",
    "normalize_address_line",
    "normalize_and_validate",
    # Validators
    "normalize_cik",
    "normalize_country_code",
    "normalize_cusip",
    "normalize_ein",
    "normalize_figi",
    "normalize_isin",
    "normalize_lei",
    "normalize_mic",
    "normalize_person_name",
    "normalize_person_name_for_search",
    "normalize_postal_code",
    "normalize_region_code",
    "normalize_sedol",
    "normalize_ticker",
    "not_found_result",
    "validate_cik",
    "validate_cusip",
    "validate_ein",
    "validate_figi",
    "validate_isin",
    "validate_lei",
    "validate_mic",
    "validate_person_name",
    "validate_scheme_scope",
    "validate_sedol",
    "validate_ticker",
    # Graph traversal result types
    "RelatedEntity",
    "OfficerInfo",
    "PathStep",
    "EntityPath",
    "EntityNetwork",
    # Timeline models
    "TimelineEventType",
    "TimelineEvent",
    "EntitySnapshot",
    "StateDiff",
    # Clustering models
    "ClusterStatus",
    "DuplicateCandidate",
    "ClusterInfo",
    "BlockingConfig",
]
