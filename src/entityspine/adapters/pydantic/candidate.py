"""
Resolution candidate model for ranked resolution results.

v2.2.3 DESIGN:
- ResolutionCandidate is a lightweight match result (IDs only, no full objects)
- Supports ranked resolution with scores and match reasons
- Enables efficient multi-candidate returns without hydrating full objects
- Full Entity/Security/Listing objects are hydrated on demand
"""

from datetime import datetime
from enum import Enum

from pydantic import Field

from entityspine.adapters.pydantic.base import EntitySpineModel
from entityspine.core.timestamps import utc_now


class MatchReason(str, Enum):
    """Why this candidate matched the query."""

    # Exact identifier matches
    EXACT_CIK = "exact_cik"
    EXACT_LEI = "exact_lei"
    EXACT_ISIN = "exact_isin"
    EXACT_CUSIP = "exact_cusip"
    EXACT_FIGI = "exact_figi"
    EXACT_TICKER = "exact_ticker"

    # Fuzzy/partial matches
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


class ResolutionCandidate(EntitySpineModel):
    """
    A lightweight resolution match result.

    This model contains only IDs and match metadata, NOT full objects.
    Use this for efficient multi-candidate returns where you don't need
    to hydrate full Entity/Security/Listing objects for all candidates.

    v2.2.3 DESIGN:
    - IDs only (entity_id, security_id, listing_id) - no full objects
    - Score for ranking (0.0-1.0)
    - Match reason explains WHY this candidate matched
    - Matched scheme/value shows WHAT identifier matched
    - Warnings for any issues with this specific candidate

    Attributes:
        entity_id: Matched entity ID (may be None for security-only matches).
        security_id: Matched security ID (may be None).
        listing_id: Matched listing ID (may be None).
        score: Match confidence score 0.0-1.0.
        match_reason: Why this candidate matched.
        matched_scheme: Which identifier scheme matched (e.g., "cik", "ticker").
        matched_value: The actual value that matched.
        warnings: Any warnings specific to this candidate.

    Example:
        >>> candidate = ResolutionCandidate(
        ...     entity_id="01HABC...",
        ...     security_id="01HDEF...",
        ...     listing_id="01HGHI...",
        ...     score=0.95,
        ...     match_reason=MatchReason.EXACT_TICKER,
        ...     matched_scheme="ticker",
        ...     matched_value="AAPL",
        ... )
    """

    # IDs only - no full objects
    entity_id: str | None = Field(
        default=None,
        description="Matched entity ID",
    )
    security_id: str | None = Field(
        default=None,
        description="Matched security ID",
    )
    listing_id: str | None = Field(
        default=None,
        description="Matched listing ID",
    )

    # Match quality
    score: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Match confidence score (0.0-1.0)",
    )
    match_reason: MatchReason = Field(
        default=MatchReason.UNKNOWN,
        description="Why this candidate matched the query",
    )

    # What matched
    matched_scheme: str | None = Field(
        default=None,
        description="Which identifier scheme matched (e.g., 'cik', 'ticker')",
    )
    matched_value: str | None = Field(
        default=None,
        description="The actual value that matched",
    )

    # Candidate-specific warnings
    warnings: list[str] = Field(
        default_factory=list,
        description="Warnings specific to this candidate",
    )

    # Metadata
    matched_at: datetime = Field(
        default_factory=utc_now,
        description="When this match was found (UTC)",
    )

    @property
    def has_entity(self) -> bool:
        """Check if this candidate has an entity match."""
        return self.entity_id is not None

    @property
    def has_security(self) -> bool:
        """Check if this candidate has a security match."""
        return self.security_id is not None

    @property
    def has_listing(self) -> bool:
        """Check if this candidate has a listing match."""
        return self.listing_id is not None

    @property
    def has_full_chain(self) -> bool:
        """Check if this candidate has entity → security → listing chain."""
        return all([self.entity_id, self.security_id, self.listing_id])

    @property
    def has_warnings(self) -> bool:
        """Check if this candidate has any warnings."""
        return len(self.warnings) > 0

    def add_warning(self, warning: str) -> "ResolutionCandidate":
        """
        Create a new candidate with an additional warning.

        Args:
            warning: Warning message to add

        Returns:
            New ResolutionCandidate with warning added
        """
        new_warnings = [*list(self.warnings), warning]
        data = self.model_dump()
        data["warnings"] = new_warnings
        return ResolutionCandidate(**data)

    # =========================================================================
    # Domain Model Conversion (v2.2.3 - Pydantic as thin wrapper)
    # =========================================================================

    def to_domain(self) -> "entityspine.domain.ResolutionCandidate":
        """
        Convert Pydantic model to domain dataclass.

        Returns:
            Domain ResolutionCandidate dataclass
        """
        from entityspine.domain import (
            MatchReason as DomainMatchReason,
        )
        from entityspine.domain import (
            ResolutionCandidate as DomainCandidate,
        )

        # Handle enum values - Pydantic may store as str or Enum
        match_reason_val = (
            self.match_reason.value if hasattr(self.match_reason, "value") else self.match_reason
        )

        return DomainCandidate(
            entity_id=self.entity_id,
            security_id=self.security_id,
            listing_id=self.listing_id,
            score=self.score,
            match_reason=DomainMatchReason(match_reason_val),
            matched_scheme=self.matched_scheme,
            matched_value=self.matched_value,
            warnings=tuple(self.warnings),
        )

    @classmethod
    def from_domain(
        cls, candidate: "entityspine.domain.ResolutionCandidate"
    ) -> "ResolutionCandidate":
        """
        Create Pydantic model from domain dataclass.

        Args:
            candidate: Domain ResolutionCandidate dataclass

        Returns:
            Pydantic ResolutionCandidate model
        """
        return cls(
            entity_id=candidate.entity_id,
            security_id=candidate.security_id,
            listing_id=candidate.listing_id,
            score=candidate.score,
            match_reason=MatchReason(candidate.match_reason.value),
            matched_scheme=candidate.matched_scheme,
            matched_value=candidate.matched_value,
            warnings=list(candidate.warnings),
        )


def create_candidate(
    entity_id: str | None = None,
    security_id: str | None = None,
    listing_id: str | None = None,
    score: float = 1.0,
    match_reason: MatchReason = MatchReason.UNKNOWN,
    matched_scheme: str | None = None,
    matched_value: str | None = None,
) -> ResolutionCandidate:
    """
    Factory function to create a ResolutionCandidate.

    Args:
        entity_id: Matched entity ID
        security_id: Matched security ID
        listing_id: Matched listing ID
        score: Match confidence score
        match_reason: Why this candidate matched
        matched_scheme: Which identifier scheme matched
        matched_value: The actual value that matched

    Returns:
        New ResolutionCandidate
    """
    return ResolutionCandidate(
        entity_id=entity_id,
        security_id=security_id,
        listing_id=listing_id,
        score=score,
        match_reason=match_reason,
        matched_scheme=matched_scheme,
        matched_value=matched_value,
    )
