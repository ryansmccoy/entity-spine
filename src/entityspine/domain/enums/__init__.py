"""
EntitySpine domain enums.

STDLIB ONLY - NO PYDANTIC.

This package provides all domain enumerations for the EntitySpine system.
Enums are organized into logical modules by domain concept.

For backward compatibility, all enums are re-exported from this __init__.py.
Import patterns:
    # Preferred - explicit module import
    from entityspine.domain.enums.core import EntityType, SecurityType
    from entityspine.domain.enums.resolution import ResolutionTier

    # Also supported - package-level import (backward compatible)
    from entityspine.domain.enums import EntityType, SecurityType
"""

# =============================================================================
# Core entity and security enums
# =============================================================================
from entityspine.domain.enums.core import (
    EntityStatus,
    EntityType,
    ListingStatus,
    SecurityStatus,
    SecurityType,
)

# =============================================================================
# Identifier and claim enums
# =============================================================================
from entityspine.domain.enums.identifiers import (
    ClaimStatus,
    IdentifierScheme,
    IdentifierScope,
    SanctionStatus,
)

# =============================================================================
# Resolution and matching enums
# =============================================================================
from entityspine.domain.enums.resolution import (
    MatchReason,
    ResolutionStatus,
    ResolutionTier,
    ResolutionWarning,
)

# =============================================================================
# Graph relationship and role enums
# =============================================================================
from entityspine.domain.enums.graph import (
    ClusterRole,
    ParticipantType,
    PositionType,
    RelationshipType,
    RoleType,
)

# =============================================================================
# Event and case enums
# =============================================================================
from entityspine.domain.enums.events import (
    CaseStatus,
    CaseType,
    EventStatus,
    EventType,
)

# =============================================================================
# Asset, contract, and product enums
# =============================================================================
from entityspine.domain.enums.assets import (
    AssetStatus,
    AssetType,
    ContractStatus,
    ContractType,
    ProductStatus,
    ProductType,
)

# =============================================================================
# Financial observation enums
# =============================================================================
from entityspine.domain.enums.observations import (
    AccountingBasis,
    EstimateScope,
    MetricCategory,
    MetricCode,
    ObservationType,
    PeriodType,
    PerShareType,
    Presentation,
    ProvenanceKind,
    ScopeType,
)

# =============================================================================
# Vendor and data source enums
# =============================================================================
from entityspine.domain.enums.vendors import VendorNamespace

# =============================================================================
# Geographic enums
# =============================================================================
from entityspine.domain.enums.geo import AddressType, GeoType

# =============================================================================
# Transaction enums
# =============================================================================
from entityspine.domain.enums.transactions import TransactionCode

# =============================================================================
# Market infrastructure enums (v2.3.0)
# =============================================================================
from entityspine.domain.enums.markets import (
    AssetClass,
    BrokerDealerStatus,
    BrokerDealerType,
    ClearinghouseType,
    ClearingStatus,
    ExchangeStatus,
    ExchangeType,
    MarketParticipantType,
    MembershipStatus,  # v2.3.1 - split from BrokerDealerStatus
    MembershipType,
    OrderType,
    RegistrationStatus,  # v2.3.1 - split from BrokerDealerStatus
    RegistrationType,
    TradingSessionType,
)

# =============================================================================
# __all__ for explicit exports
# =============================================================================
__all__ = [
    # core
    "EntityType",
    "EntityStatus",
    "SecurityType",
    "SecurityStatus",
    "ListingStatus",
    # identifiers
    "IdentifierScheme",
    "ClaimStatus",
    "SanctionStatus",
    "IdentifierScope",
    # resolution
    "ResolutionTier",
    "ResolutionStatus",
    "ResolutionWarning",
    "MatchReason",
    # graph
    "RoleType",
    "ParticipantType",
    "PositionType",
    "ClusterRole",
    "RelationshipType",
    # events
    "EventType",
    "EventStatus",
    "CaseType",
    "CaseStatus",
    # assets
    "AssetType",
    "AssetStatus",
    "ContractType",
    "ContractStatus",
    "ProductType",
    "ProductStatus",
    # observations
    "MetricCode",
    "MetricCategory",
    "AccountingBasis",
    "Presentation",
    "PerShareType",
    "ScopeType",
    "PeriodType",
    "ObservationType",
    "EstimateScope",
    "ProvenanceKind",
    # vendors
    "VendorNamespace",
    # geo
    "GeoType",
    "AddressType",
    # transactions
    "TransactionCode",
    # markets (v2.3.0)
    "ExchangeType",
    "ExchangeStatus",
    "AssetClass",
    "BrokerDealerType",
    "BrokerDealerStatus",
    "ClearinghouseType",
    "ClearingStatus",
    "MarketParticipantType",
    "MembershipStatus",  # v2.3.1
    "RegistrationStatus",  # v2.3.1
    "RegistrationType",
    "TradingSessionType",
    "OrderType",
    "MembershipType",
]
