"""
Resolution result models.

v2.2.3 DESIGN PRINCIPLES:
1. Tier Capability Honesty - results include warnings when tier can't honor as_of
2. Candidate-based resolution - lightweight candidates for efficient multi-match
3. Full object hydration on demand - candidates contain IDs, not full objects

CRITICAL: Tier Capability Honesty

When a Tier 0-1 store receives an `as_of` parameter it cannot honor,
the result MUST include a warning. This allows callers to:
- Get the best available answer
- Know the answer might not be historically accurate
- Decide whether to try a higher-tier store
"""

from datetime import date, datetime
from enum import Enum

from pydantic import Field

from entityspine.adapters.pydantic.base import MutableEntitySpineModel
from entityspine.adapters.pydantic.candidate import ResolutionCandidate
from entityspine.adapters.pydantic.entity import Entity
from entityspine.adapters.pydantic.listing import Listing
from entityspine.adapters.pydantic.security import Security
from entityspine.core.timestamps import utc_now


class ResolutionTier(int, Enum):
    """Storage tier that provided the resolution."""

    CACHE = -1  # From cache (tier unknown)
    TIER_0 = 0  # Simple lookup, no history
    TIER_1 = 1  # SQLite, limited history
    TIER_2 = 2  # Full temporal graph


class ResolutionStatus(str, Enum):
    """Status of the resolution attempt."""

    FOUND = "found"  # Entity found
    NOT_FOUND = "not_found"  # No matching entity
    AMBIGUOUS = "ambiguous"  # Multiple matches
    REDIRECTED = "redirected"  # Followed redirect chain
    ERROR = "error"  # Resolution failed


class ResolutionWarning(str, Enum):
    """Standard warning types for resolution results."""

    AS_OF_IGNORED = "as_of_ignored"
    TEMPORAL_NOT_SUPPORTED = "temporal_not_supported"
    REDIRECT_FOLLOWED = "redirect_followed"
    MAX_REDIRECTS_REACHED = "max_redirects_reached"
    AMBIGUOUS_MATCH = "ambiguous_match"
    LOW_CONFIDENCE = "low_confidence"
    STALE_DATA = "stale_data"
    CACHE_HIT = "cache_hit"


class ResolutionResult(MutableEntitySpineModel):
    """
    Result of an entity resolution attempt.

    v2.2.3 DESIGN:
    - Supports both full object hydration AND lightweight candidates
    - entity/security/listing fields for backward compatibility and convenience
    - candidates field for efficient multi-match scenarios
    - best property returns top candidate

    TIER CAPABILITY HONESTY:
    - If `as_of` was requested but the tier can't honor it,
      `warnings` will include the as_of_ignored warning
    - The `tier` field indicates which storage tier provided the result
    - The `limits` dict describes what the tier cannot do

    Attributes:
        entity: The resolved Entity, or None if not found (hydrated).
        security: Resolved security (hydrated).
        listing: Resolved listing (hydrated).
        candidates: Lightweight match candidates (IDs only).
        status: Resolution status (found, not_found, ambiguous, etc.).
        tier: Storage tier that provided this result.
        query: Original query that was resolved.
        as_of: Requested as_of date (may have been ignored).
        as_of_honored: Whether as_of was actually used.
        warnings: List of warning messages.
        limits: Dict of tier limitations.
        redirect_chain: Entity IDs followed during redirect resolution.
        alternatives: Other potential matches (for ambiguous results).
        confidence: Confidence score 0.0-1.0.
        resolved_at: When resolution was performed.
        elapsed_ms: Time taken in milliseconds.

    Example:
        >>> result = resolver.resolve("AAPL")
        >>> if result.found:
        ...     print(result.entity.primary_name)
        >>> if result.has_warnings:
        ...     for warning in result.warnings:
        ...         print(f"Warning: {warning}")
        >>> # Multi-candidate access
        >>> for candidate in result.candidates:
        ...     print(f"{candidate.entity_id}: {candidate.score}")
    """

    # Core result - hydrated objects (for backward compat and convenience)
    entity: Entity | None = Field(
        default=None,
        description="Resolved entity (hydrated)",
    )
    security: Security | None = Field(
        default=None,
        description="Resolved security (hydrated)",
    )
    listing: Listing | None = Field(
        default=None,
        description="Resolved listing (hydrated)",
    )

    # v2.2.3: Lightweight candidates for efficient multi-match
    candidates: list[ResolutionCandidate] = Field(
        default_factory=list,
        description="Lightweight match candidates (IDs only, no full objects)",
    )

    status: ResolutionStatus = Field(
        default=ResolutionStatus.NOT_FOUND,
        description="Resolution status",
    )
    tier: ResolutionTier = Field(
        default=ResolutionTier.TIER_0,
        description="Storage tier that provided this result",
    )

    # Query info
    query: str = Field(
        default="",
        description="Original query",
    )
    as_of: date | None = Field(
        default=None,
        description="Requested point-in-time",
    )
    as_of_honored: bool = Field(
        default=True,
        description="Whether as_of was actually used",
    )

    # Warnings and limitations (tier honesty)
    warnings: list[str] = Field(
        default_factory=list,
        description="Warning messages",
    )
    limits: dict[str, str] = Field(
        default_factory=dict,
        description="Tier limitations",
    )

    # Resolution path
    redirect_chain: list[str] = Field(
        default_factory=list,
        description="Redirect chain followed",
    )
    alternatives: list[Entity] = Field(
        default_factory=list,
        description="Alternative matches (for ambiguous, hydrated)",
    )

    # Quality metrics
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Overall confidence score",
    )

    # Timing
    resolved_at: datetime = Field(
        default_factory=utc_now,
        description="When resolved (UTC)",
    )
    elapsed_ms: float = Field(
        default=0.0,
        ge=0.0,
        description="Time taken (ms)",
    )

    # Extensible metadata
    metadata: dict[str, str] = Field(
        default_factory=dict,
        description="Additional metadata",
    )

    @property
    def found(self) -> bool:
        """Check if entity was found."""
        return self.entity is not None and self.status in (
            ResolutionStatus.FOUND,
            ResolutionStatus.REDIRECTED,
        )

    @property
    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return len(self.warnings) > 0

    @property
    def is_ambiguous(self) -> bool:
        """Check if result is ambiguous."""
        return self.status == ResolutionStatus.AMBIGUOUS

    @property
    def has_candidates(self) -> bool:
        """Check if there are any candidates."""
        return len(self.candidates) > 0

    @property
    def best(self) -> ResolutionCandidate | None:
        """
        Get the best (highest-scoring) candidate.

        Returns:
            Top-ranked candidate or None if no candidates
        """
        if not self.candidates:
            return None
        return max(self.candidates, key=lambda c: c.score)

    @property
    def candidate_count(self) -> int:
        """Get number of candidates."""
        return len(self.candidates)

    def add_warning(self, warning_type: ResolutionWarning | str, detail: str = "") -> None:
        """Add a warning to the result."""
        warning_key = (
            warning_type.value if isinstance(warning_type, ResolutionWarning) else warning_type
        )
        if detail:
            self.warnings.append(f"{warning_key}: {detail}")
        else:
            self.warnings.append(warning_key)

    def add_candidate(self, candidate: ResolutionCandidate) -> None:
        """
        Add a candidate to the result.

        Args:
            candidate: Resolution candidate to add
        """
        self.candidates.append(candidate)

    def add_candidates(self, candidates: list[ResolutionCandidate]) -> None:
        """
        Add multiple candidates to the result.

        Args:
            candidates: List of resolution candidates to add
        """
        self.candidates.extend(candidates)

    def sort_candidates(self, descending: bool = True) -> None:
        """
        Sort candidates by score.

        Args:
            descending: Sort high-to-low (default) or low-to-high
        """
        self.candidates.sort(key=lambda c: c.score, reverse=descending)

    def top_candidates(self, n: int = 5) -> list[ResolutionCandidate]:
        """
        Get top N candidates by score.

        Args:
            n: Number of candidates to return

        Returns:
            Top N candidates sorted by score
        """
        sorted_candidates = sorted(self.candidates, key=lambda c: c.score, reverse=True)
        return sorted_candidates[:n]

    # =========================================================================
    # Domain Model Conversion (v2.2.3 - Pydantic as thin wrapper)
    # =========================================================================

    def to_domain(self) -> "entityspine.domain.ResolutionResult":
        """
        Convert Pydantic model to domain dataclass.

        Returns:
            Domain ResolutionResult dataclass
        """
        from entityspine.domain import (
            ResolutionResult as DomainResult,
        )
        from entityspine.domain import (
            ResolutionStatus as DomainStatus,
        )
        from entityspine.domain import (
            ResolutionTier as DomainTier,
        )

        # Convert nested objects
        domain_entity = self.entity.to_domain() if self.entity else None
        domain_security = self.security.to_domain() if self.security else None
        domain_listing = self.listing.to_domain() if self.listing else None
        domain_candidates = [c.to_domain() for c in self.candidates]

        # Handle enum values - Pydantic may store as str or Enum
        status_val = self.status.value if hasattr(self.status, "value") else self.status
        tier_val = self.tier.value if hasattr(self.tier, "value") else self.tier

        return DomainResult(
            query=self.query,
            status=DomainStatus(status_val),
            tier=DomainTier(tier_val),
            entity=domain_entity,
            security=domain_security,
            listing=domain_listing,
            candidates=domain_candidates,
            as_of=self.as_of,
            as_of_honored=self.as_of_honored,
            warnings=list(self.warnings),
            limits=dict(self.limits),
            redirect_chain=list(self.redirect_chain),
            confidence=self.confidence,
            resolved_at=self.resolved_at,
            elapsed_ms=self.elapsed_ms,
        )

    @classmethod
    def from_domain(cls, result: "entityspine.domain.ResolutionResult") -> "ResolutionResult":
        """
        Create Pydantic model from domain dataclass.

        Args:
            result: Domain ResolutionResult dataclass

        Returns:
            Pydantic ResolutionResult model
        """
        # Convert nested objects
        pydantic_entity = Entity.from_domain(result.entity) if result.entity else None
        pydantic_security = Security.from_domain(result.security) if result.security else None
        pydantic_listing = Listing.from_domain(result.listing) if result.listing else None
        pydantic_candidates = [ResolutionCandidate.from_domain(c) for c in result.candidates]

        return cls(
            query=result.query,
            status=ResolutionStatus(result.status.value),
            tier=ResolutionTier(result.tier.value),
            entity=pydantic_entity,
            security=pydantic_security,
            listing=pydantic_listing,
            candidates=pydantic_candidates,
            as_of=result.as_of,
            as_of_honored=result.as_of_honored,
            warnings=list(result.warnings),
            limits=dict(result.limits),
            redirect_chain=list(result.redirect_chain),
            confidence=result.confidence,
            resolved_at=result.resolved_at,
            elapsed_ms=result.elapsed_ms,
        )


# Factory functions for creating results
def found_result(
    entity: Entity,
    query: str,
    tier: ResolutionTier,
    as_of: date | None = None,
    as_of_honored: bool = True,
    elapsed_ms: float = 0.0,
    confidence: float = 1.0,
    warnings: list[str] | None = None,
    security: Security | None = None,
    listing: Listing | None = None,
) -> ResolutionResult:
    """Create a successful resolution result."""
    result = ResolutionResult(
        entity=entity,
        security=security,
        listing=listing,
        status=ResolutionStatus.FOUND,
        tier=tier,
        query=query,
        as_of=as_of,
        as_of_honored=as_of_honored,
        elapsed_ms=elapsed_ms,
        confidence=confidence,
        warnings=warnings or [],
    )
    if as_of and not as_of_honored:
        result.add_warning(
            ResolutionWarning.AS_OF_IGNORED,
            f"Tier {tier.value} store lacks temporal data",
        )
    return result


def not_found_result(
    query: str,
    tier: ResolutionTier,
    as_of: date | None = None,
    elapsed_ms: float = 0.0,
    warnings: list[str] | None = None,
) -> ResolutionResult:
    """Create a not-found resolution result."""
    return ResolutionResult(
        entity=None,
        status=ResolutionStatus.NOT_FOUND,
        tier=tier,
        query=query,
        as_of=as_of,
        elapsed_ms=elapsed_ms,
        warnings=warnings or [],
    )


def ambiguous_result(
    query: str,
    alternatives: list[Entity],
    tier: ResolutionTier,
    elapsed_ms: float = 0.0,
) -> ResolutionResult:
    """Create an ambiguous resolution result."""
    result = ResolutionResult(
        entity=None,
        status=ResolutionStatus.AMBIGUOUS,
        tier=tier,
        query=query,
        alternatives=alternatives,
        elapsed_ms=elapsed_ms,
    )
    result.add_warning(ResolutionWarning.AMBIGUOUS_MATCH, f"{len(alternatives)} matches found")
    return result


def redirected_result(
    entity: Entity,
    query: str,
    redirect_chain: list[str],
    tier: ResolutionTier,
    elapsed_ms: float = 0.0,
) -> ResolutionResult:
    """Create a redirected resolution result."""
    result = ResolutionResult(
        entity=entity,
        status=ResolutionStatus.REDIRECTED,
        tier=tier,
        query=query,
        redirect_chain=redirect_chain,
        elapsed_ms=elapsed_ms,
    )
    result.add_warning(ResolutionWarning.REDIRECT_FOLLOWED, f"Chain: {' -> '.join(redirect_chain)}")
    return result
