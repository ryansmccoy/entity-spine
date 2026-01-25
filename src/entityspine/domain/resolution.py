"""
ResolutionResult domain model (stdlib dataclass).

STDLIB ONLY - NO PYDANTIC.

v2.2.3 DESIGN:
- Tier Capability Honesty - results include warnings when tier can't honor as_of/mic
- Candidate-based resolution - lightweight candidates for efficient multi-match
- Full object hydration on demand

Per 05_TIER_CAPABILITIES_AND_LIMITS.md:
- Tier 0/1 must emit warnings when as_of or mic cannot be honored
- Must include limits dict describing what tier cannot do
"""

from dataclasses import dataclass, field
from datetime import date, datetime

from entityspine.domain.candidate import ResolutionCandidate
from entityspine.domain.entity import Entity
from entityspine.domain.enums import ResolutionStatus, ResolutionTier
from entityspine.domain.listing import Listing
from entityspine.domain.security import Security
from entityspine.domain.timestamps import utc_now


@dataclass(slots=True)
class ResolutionResult:
    """
    Result of an entity resolution attempt.

    NOTE: This is NOT frozen because it's mutable (add_candidate, etc.)

    v2.2.3 DESIGN:
    - Supports both full object hydration AND lightweight candidates
    - entity/security/listing fields for backward compat
    - candidates field for efficient multi-match

    TIER CAPABILITY HONESTY:
    - If as_of requested but tier can't honor it, warnings includes AS_OF_IGNORED
    - tier field indicates which storage tier provided the result
    - limits dict describes what the tier cannot do

    Standard Warnings (per 05_TIER_CAPABILITIES_AND_LIMITS.md):
    - "as_of parameter ignored: listing validity data not available"
    - "mic parameter ignored: exchange data not available"
    - "fuzzy matching not available in Tier 0"

    Standard Limits:
    - temporal_resolution: "current_only" | "best_effort" | "full"
    - mic_filtering: "not_available" | "partial" | "full"
    - fuzzy_matching: "not_available" | "like_only" | "fts"

    Attributes:
        entity: Resolved entity (hydrated)
        security: Resolved security (hydrated)
        listing: Resolved listing (hydrated)
        candidates: Lightweight match candidates
        status: Resolution status
        tier: Storage tier that provided this result
        query: Original query
        as_of: Requested point-in-time
        as_of_honored: Whether as_of was actually used
        warnings: List of warning messages
        limits: Dict of tier limitations
        redirect_chain: Entity IDs followed during redirect resolution
        confidence: Confidence score 0.0-1.0
        resolved_at: When resolution was performed
        elapsed_ms: Time taken in milliseconds
    """

    # Query info
    query: str = ""

    # Resolution status
    status: ResolutionStatus = ResolutionStatus.NOT_FOUND
    tier: ResolutionTier = ResolutionTier.TIER_0

    # Core result - hydrated objects
    entity: Entity | None = None
    security: Security | None = None
    listing: Listing | None = None

    # Lightweight candidates (v2.2.3)
    candidates: list[ResolutionCandidate] = field(default_factory=list)

    # Temporal query
    as_of: date | None = None
    as_of_honored: bool = True

    # Tier capability honesty (per 05_TIER_CAPABILITIES_AND_LIMITS.md)
    warnings: list[str] = field(default_factory=list)
    limits: dict[str, str] = field(default_factory=dict)

    # Resolution path
    redirect_chain: list[str] = field(default_factory=list)

    # Confidence
    confidence: float = 1.0

    # Timing
    resolved_at: datetime = field(default_factory=utc_now)
    elapsed_ms: float = 0.0

    # ==========================================================================
    # Properties
    # ==========================================================================

    @property
    def found(self) -> bool:
        """Check if entity was found."""
        return self.entity is not None

    @property
    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return len(self.warnings) > 0

    @property
    def has_candidates(self) -> bool:
        """Check if there are any candidates."""
        return len(self.candidates) > 0

    @property
    def candidate_count(self) -> int:
        """Get number of candidates."""
        return len(self.candidates)

    @property
    def best(self) -> ResolutionCandidate | None:
        """Get the highest-scoring candidate."""
        if not self.candidates:
            return None
        return self.candidates[0]

    @property
    def has_temporal_limits(self) -> bool:
        """Check if temporal resolution was limited."""
        return "temporal_resolution" in self.limits

    @property
    def has_mic_limits(self) -> bool:
        """Check if MIC filtering was limited."""
        return "mic_filtering" in self.limits

    # ==========================================================================
    # Candidate Management
    # ==========================================================================

    def add_candidate(self, candidate: ResolutionCandidate) -> None:
        """Add a candidate to the list."""
        self.candidates.append(candidate)

    def add_candidates(self, candidates: list[ResolutionCandidate]) -> None:
        """Add multiple candidates."""
        self.candidates.extend(candidates)

    def sort_candidates(self, reverse: bool = True) -> None:
        """Sort candidates by score (highest first by default)."""
        self.candidates.sort(key=lambda c: c.score, reverse=reverse)

    def top_candidates(self, n: int = 5) -> list[ResolutionCandidate]:
        """Get top N candidates by score."""
        return sorted(self.candidates, key=lambda c: c.score, reverse=True)[:n]

    # ==========================================================================
    # Warning Management
    # ==========================================================================

    def add_warning(self, warning: str) -> None:
        """Add a warning message."""
        if warning not in self.warnings:
            self.warnings.append(warning)

    def add_as_of_ignored_warning(self) -> None:
        """Add standard as_of ignored warning."""
        self.add_warning("as_of parameter ignored: listing validity data not available")
        self.as_of_honored = False

    def add_mic_ignored_warning(self) -> None:
        """Add standard mic ignored warning."""
        self.add_warning("mic parameter ignored: exchange data not available")

    # ==========================================================================
    # Limit Management
    # ==========================================================================

    def set_limit(self, key: str, value: str) -> None:
        """Set a tier limitation."""
        self.limits[key] = value

    def set_tier_0_limits(self) -> None:
        """Set standard Tier 0 limits."""
        self.limits["temporal_resolution"] = "current_only"
        self.limits["mic_filtering"] = "not_available"
        self.limits["fuzzy_matching"] = "not_available"

    def set_tier_1_limits(self) -> None:
        """Set standard Tier 1 limits."""
        self.limits["temporal_resolution"] = "best_effort"
        self.limits["mic_filtering"] = "not_available"
        self.limits["fuzzy_matching"] = "like_only"
