"""
ResolutionCandidate domain model (stdlib dataclass).

STDLIB ONLY - NO PYDANTIC.

v2.2.3 DESIGN:
- Lightweight match result (IDs only, no full objects)
- Supports ranked resolution with scores and match reasons
- Full Entity/Security/Listing objects hydrated on demand
"""

from dataclasses import dataclass, field

from entityspine.domain.enums import MatchReason


@dataclass(frozen=True, slots=True)
class ResolutionCandidate:
    """
    A lightweight resolution match result.

    Contains only IDs and match metadata, NOT full objects.
    Use for efficient multi-candidate returns.

    Attributes:
        entity_id: Matched entity ID
        security_id: Matched security ID
        listing_id: Matched listing ID
        score: Match confidence score 0.0-1.0
        match_reason: Why this candidate matched
        matched_scheme: Which identifier scheme matched
        matched_value: The actual value that matched
        warnings: Any warnings specific to this candidate
    """

    score: float = 0.0
    match_reason: MatchReason = MatchReason.UNKNOWN

    # IDs only - no full objects
    entity_id: str | None = None
    security_id: str | None = None
    listing_id: str | None = None

    # What matched
    matched_scheme: str | None = None
    matched_value: str | None = None

    # Warnings for this candidate
    warnings: tuple = field(default_factory=tuple)

    def __post_init__(self):
        """Validate candidate after creation."""
        if not (0.0 <= self.score <= 1.0):
            raise ValueError(f"score must be between 0.0 and 1.0, got {self.score}")
        # Convert warnings list to tuple if needed
        if isinstance(self.warnings, list):
            object.__setattr__(self, "warnings", tuple(self.warnings))

    @property
    def has_entity(self) -> bool:
        """Check if candidate has an entity match."""
        return self.entity_id is not None

    @property
    def has_security(self) -> bool:
        """Check if candidate has a security match."""
        return self.security_id is not None

    @property
    def has_listing(self) -> bool:
        """Check if candidate has a listing match."""
        return self.listing_id is not None
