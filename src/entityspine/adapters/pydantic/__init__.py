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
from entityspine.adapters.pydantic.entity import Entity, EntityType, EntityStatus
from entityspine.adapters.pydantic.security import Security, SecurityType, SecurityStatus
from entityspine.adapters.pydantic.listing import Listing, ListingStatus, Exchange, MIC_TO_EXCHANGE
from entityspine.adapters.pydantic.claim import IdentifierClaim, IdentifierScheme, ClaimStatus
from entityspine.adapters.pydantic.candidate import ResolutionCandidate, MatchReason, create_candidate
from entityspine.adapters.pydantic.resolution import (
    ResolutionResult,
    ResolutionStatus,
    ResolutionTier,
    ResolutionWarning,
    found_result,
    not_found_result,
    ambiguous_result,
    redirected_result,
)
from entityspine.adapters.pydantic.validators import (
    VendorNamespace,
    IdentifierScope,
    SCHEME_SCOPES,
    # Normalization functions
    normalize_cik,
    normalize_lei,
    normalize_isin,
    normalize_cusip,
    normalize_sedol,
    normalize_figi,
    normalize_ein,
    normalize_ticker,
    normalize_mic,
    # Validation functions
    validate_cik,
    validate_lei,
    validate_isin,
    validate_cusip,
    validate_sedol,
    validate_figi,
    validate_ein,
    validate_ticker,
    validate_mic,
    # Combined functions
    normalize_and_validate,
    get_scope_for_scheme,
    validate_scheme_scope,
)

__all__ = [
    # Base
    "EntitySpineModel",
    "MutableEntitySpineModel",
    # Entity
    "Entity",
    "EntityType",
    "EntityStatus",
    # Security
    "Security",
    "SecurityType",
    "SecurityStatus",
    # Listing
    "Listing",
    "ListingStatus",
    "Exchange",
    "MIC_TO_EXCHANGE",
    # Claims (CANONICAL source of identifiers)
    "IdentifierClaim",
    "IdentifierScheme",
    "ClaimStatus",
    # Vendor namespaces
    "VendorNamespace",
    "IdentifierScope",
    "SCHEME_SCOPES",
    # Resolution candidates
    "ResolutionCandidate",
    "MatchReason",
    "create_candidate",
    # Resolution results
    "ResolutionResult",
    "ResolutionStatus",
    "ResolutionTier",
    "ResolutionWarning",
    # Result factories
    "found_result",
    "not_found_result",
    "ambiguous_result",
    "redirected_result",
    # Normalization functions
    "normalize_cik",
    "normalize_lei",
    "normalize_isin",
    "normalize_cusip",
    "normalize_sedol",
    "normalize_figi",
    "normalize_ein",
    "normalize_ticker",
    "normalize_mic",
    # Validation functions
    "validate_cik",
    "validate_lei",
    "validate_isin",
    "validate_cusip",
    "validate_sedol",
    "validate_figi",
    "validate_ein",
    "validate_ticker",
    "validate_mic",
    # Combined functions
    "normalize_and_validate",
    "get_scope_for_scheme",
    "validate_scheme_scope",
]
