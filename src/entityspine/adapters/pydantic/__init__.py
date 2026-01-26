"""
Pydantic wrappers for EntitySpine domain models.

This module provides Pydantic v2 wrappers around the canonical domain dataclasses.
These wrappers are OPTIONAL - the domain dataclasses are the single source of truth.

Use cases:
- JSON serialization/deserialization
- Request/response validation in APIs
- JSON Schema generation for OpenAPI

CRITICAL DESIGN PRINCIPLE:
Pydantic wrappers MUST use to_domain() / from_domain() to convert.
Wrappers may have derived/computed fields for convenience, but these
are EXCLUDED from to_domain() and never used for business logic.

Installation:
    pip install entityspine[pydantic]

Example:
    from entityspine.adapters.pydantic import Entity as PydanticEntity
    from entityspine import Entity as DomainEntity

    # Convert Pydantic to domain
    domain_entity = pydantic_entity.to_domain()

    # Convert domain to Pydantic
    pydantic_entity = PydanticEntity.from_domain(domain_entity)
"""

from entityspine.adapters.pydantic.base import EntitySpineModel, MutableEntitySpineModel
from entityspine.adapters.pydantic.candidate import (
    MatchReason,
    ResolutionCandidate,
    create_candidate,
)
from entityspine.adapters.pydantic.claim import ClaimStatus, IdentifierClaim, IdentifierScheme
from entityspine.adapters.pydantic.entity import Entity, EntityStatus, EntityType
from entityspine.adapters.pydantic.listing import MIC_TO_EXCHANGE, Exchange, Listing, ListingStatus
from entityspine.adapters.pydantic.resolution import (
    ResolutionResult,
    ResolutionStatus,
    ResolutionTier,
    ResolutionWarning,
    ambiguous_result,
    found_result,
    not_found_result,
    redirected_result,
)
from entityspine.adapters.pydantic.security import Security, SecurityStatus, SecurityType
from entityspine.adapters.pydantic.validators import (
    SCHEME_SCOPES,
    IdentifierScope,
    VendorNamespace,
    get_scope_for_scheme,
    # Combined functions
    normalize_and_validate,
    # Normalization functions
    normalize_cik,
    normalize_cusip,
    normalize_ein,
    normalize_figi,
    normalize_isin,
    normalize_lei,
    normalize_mic,
    normalize_sedol,
    normalize_ticker,
    # Validation functions
    validate_cik,
    validate_cusip,
    validate_ein,
    validate_figi,
    validate_isin,
    validate_lei,
    validate_mic,
    validate_scheme_scope,
    validate_sedol,
    validate_ticker,
)

__all__ = [
    "MIC_TO_EXCHANGE",
    "SCHEME_SCOPES",
    "ClaimStatus",
    # Entity
    "Entity",
    # Base
    "EntitySpineModel",
    "EntityStatus",
    "EntityType",
    "Exchange",
    # Claims (CANONICAL source of identifiers)
    "IdentifierClaim",
    "IdentifierScheme",
    "IdentifierScope",
    # Listing
    "Listing",
    "ListingStatus",
    "MatchReason",
    "MutableEntitySpineModel",
    # Resolution candidates
    "ResolutionCandidate",
    # Resolution results
    "ResolutionResult",
    "ResolutionStatus",
    "ResolutionTier",
    "ResolutionWarning",
    # Security
    "Security",
    "SecurityStatus",
    "SecurityType",
    # Vendor namespaces
    "VendorNamespace",
    "ambiguous_result",
    "create_candidate",
    # Result factories
    "found_result",
    "get_scope_for_scheme",
    # Combined functions
    "normalize_and_validate",
    # Normalization functions
    "normalize_cik",
    "normalize_cusip",
    "normalize_ein",
    "normalize_figi",
    "normalize_isin",
    "normalize_lei",
    "normalize_mic",
    "normalize_sedol",
    "normalize_ticker",
    "not_found_result",
    "redirected_result",
    # Validation functions
    "validate_cik",
    "validate_cusip",
    "validate_ein",
    "validate_figi",
    "validate_isin",
    "validate_lei",
    "validate_mic",
    "validate_scheme_scope",
    "validate_sedol",
    "validate_ticker",
]
