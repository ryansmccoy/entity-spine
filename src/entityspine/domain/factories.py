"""
Factory functions for creating domain objects.

STDLIB ONLY - NO PYDANTIC.

These factory functions provide convenient ways to create domain objects
with common configurations and proper validation.
"""

from entityspine.domain.candidate import ResolutionCandidate
from entityspine.domain.claim import IdentifierClaim
from entityspine.domain.entity import Entity
from entityspine.domain.enums import (
    EntityType,
    IdentifierScheme,
    MatchReason,
    ResolutionStatus,
    ResolutionTier,
    SecurityType,
    VendorNamespace,
)
from entityspine.domain.listing import Listing
from entityspine.domain.resolution import ResolutionResult
from entityspine.domain.security import Security

# =============================================================================
# Entity Factories
# =============================================================================


def create_entity(
    primary_name: str,
    entity_id: str | None = None,
    entity_type: EntityType = EntityType.ORGANIZATION,
    source_system: str = "unknown",
    source_id: str | None = None,
    **kwargs,
) -> Entity:
    """
    Create an Entity with common defaults.

    Args:
        primary_name: Legal/trading name
        entity_id: Optional ULID (auto-generated if not provided)
        entity_type: Type of entity
        source_system: Where this record came from
        source_id: ID in the source system
        **kwargs: Additional Entity fields
    """
    params = {
        "primary_name": primary_name,
        "entity_type": entity_type,
        "source_system": source_system,
    }
    if entity_id:
        params["entity_id"] = entity_id
    if source_id:
        params["source_id"] = source_id
    params.update(kwargs)
    return Entity(**params)


# =============================================================================
# Security Factories
# =============================================================================


def create_security(
    entity_id: str,
    security_id: str | None = None,
    security_type: SecurityType = SecurityType.COMMON_STOCK,
    description: str | None = None,
    **kwargs,
) -> Security:
    """
    Create a Security with common defaults.

    Args:
        entity_id: FK to issuing Entity
        security_id: Optional ULID (auto-generated if not provided)
        security_type: Type of security
        description: Human-readable description
        **kwargs: Additional Security fields
    """
    params = {
        "entity_id": entity_id,
        "security_type": security_type,
    }
    if security_id:
        params["security_id"] = security_id
    if description:
        params["description"] = description
    params.update(kwargs)
    return Security(**params)


# =============================================================================
# Listing Factories
# =============================================================================


def create_listing(
    security_id: str,
    ticker: str,
    listing_id: str | None = None,
    exchange: str = "",
    mic: str | None = None,
    is_primary: bool = False,
    **kwargs,
) -> Listing:
    """
    Create a Listing with common defaults.

    Args:
        security_id: FK to Security
        ticker: Ticker symbol
        listing_id: Optional ULID (auto-generated if not provided)
        exchange: Exchange name/code
        mic: Market Identifier Code
        is_primary: Whether this is the primary listing
        **kwargs: Additional Listing fields
    """
    params = {
        "security_id": security_id,
        "ticker": ticker,
        "exchange": exchange,
        "is_primary": is_primary,
    }
    if listing_id:
        params["listing_id"] = listing_id
    if mic:
        params["mic"] = mic
    params.update(kwargs)
    return Listing(**params)


# =============================================================================
# Claim Factories
# =============================================================================


def create_claim(
    scheme: IdentifierScheme,
    value: str,
    entity_id: str | None = None,
    security_id: str | None = None,
    listing_id: str | None = None,
    namespace: VendorNamespace = VendorNamespace.INTERNAL,
    source: str = "unknown",
    confidence: float = 1.0,
    **kwargs,
) -> IdentifierClaim:
    """
    Create an IdentifierClaim with common defaults.

    Args:
        scheme: Identifier scheme
        value: Identifier value (will be normalized)
        entity_id: Entity target (for entity-scoped schemes)
        security_id: Security target (for security-scoped schemes)
        listing_id: Listing target (for listing-scoped schemes)
        namespace: Vendor/source namespace
        source: Human-readable source description
        confidence: Confidence score 0.0-1.0
        **kwargs: Additional IdentifierClaim fields
    """
    params = {
        "scheme": scheme,
        "value": value,
        "namespace": namespace,
        "source": source,
        "confidence": confidence,
    }
    if entity_id:
        params["entity_id"] = entity_id
    if security_id:
        params["security_id"] = security_id
    if listing_id:
        params["listing_id"] = listing_id
    params.update(kwargs)
    return IdentifierClaim(**params)


# =============================================================================
# Candidate Factories
# =============================================================================


def create_candidate(
    score: float,
    match_reason: MatchReason,
    entity_id: str | None = None,
    security_id: str | None = None,
    listing_id: str | None = None,
    matched_scheme: str | None = None,
    matched_value: str | None = None,
    **kwargs,
) -> ResolutionCandidate:
    """
    Create a ResolutionCandidate.

    Args:
        score: Match confidence score 0.0-1.0
        match_reason: Why this candidate matched
        entity_id: Matched entity ID
        security_id: Matched security ID
        listing_id: Matched listing ID
        matched_scheme: Which identifier scheme matched
        matched_value: The actual value that matched
        **kwargs: Additional ResolutionCandidate fields
    """
    params = {
        "score": score,
        "match_reason": match_reason,
    }
    if entity_id:
        params["entity_id"] = entity_id
    if security_id:
        params["security_id"] = security_id
    if listing_id:
        params["listing_id"] = listing_id
    if matched_scheme:
        params["matched_scheme"] = matched_scheme
    if matched_value:
        params["matched_value"] = matched_value
    params.update(kwargs)
    return ResolutionCandidate(**params)


# =============================================================================
# Resolution Result Factories
# =============================================================================


def found_result(
    entity: Entity,
    query: str,
    tier: ResolutionTier,
    elapsed_ms: float = 0.0,
    warnings: list[str] | None = None,
    security: Security | None = None,
    listing: Listing | None = None,
    **kwargs,
) -> ResolutionResult:
    """
    Create a successful resolution result.

    Args:
        entity: The resolved entity
        query: Original query string
        tier: Storage tier that provided the result
        elapsed_ms: Time taken in milliseconds
        warnings: Optional list of warnings
        security: Optional resolved security
        listing: Optional resolved listing
        **kwargs: Additional ResolutionResult fields
    """
    return ResolutionResult(
        entity=entity,
        security=security,
        listing=listing,
        status=ResolutionStatus.FOUND,
        tier=tier,
        query=query,
        elapsed_ms=elapsed_ms,
        warnings=warnings or [],
        confidence=1.0,
        **kwargs,
    )


def not_found_result(
    query: str,
    tier: ResolutionTier,
    elapsed_ms: float = 0.0,
    warnings: list[str] | None = None,
    **kwargs,
) -> ResolutionResult:
    """
    Create a not-found resolution result.

    Args:
        query: Original query string
        tier: Storage tier that performed the resolution
        elapsed_ms: Time taken in milliseconds
        warnings: Optional list of warnings
        **kwargs: Additional ResolutionResult fields
    """
    return ResolutionResult(
        entity=None,
        status=ResolutionStatus.NOT_FOUND,
        tier=tier,
        query=query,
        elapsed_ms=elapsed_ms,
        warnings=warnings or [],
        confidence=0.0,
        **kwargs,
    )


def ambiguous_result(
    query: str,
    tier: ResolutionTier,
    candidates: list[ResolutionCandidate],
    elapsed_ms: float = 0.0,
    warnings: list[str] | None = None,
    **kwargs,
) -> ResolutionResult:
    """
    Create an ambiguous resolution result with multiple candidates.

    Args:
        query: Original query string
        tier: Storage tier that performed the resolution
        candidates: List of potential matches
        elapsed_ms: Time taken in milliseconds
        warnings: Optional list of warnings
        **kwargs: Additional ResolutionResult fields
    """
    warnings_list = warnings or []
    if "ambiguous_match" not in str(warnings_list):
        warnings_list.append("Multiple candidates matched query")

    return ResolutionResult(
        entity=None,
        status=ResolutionStatus.AMBIGUOUS,
        tier=tier,
        query=query,
        candidates=candidates,
        elapsed_ms=elapsed_ms,
        warnings=warnings_list,
        confidence=0.5 if candidates else 0.0,
        **kwargs,
    )
