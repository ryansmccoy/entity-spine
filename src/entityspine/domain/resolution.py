"""
ResolutionResult domain model (stdlib dataclass).

STDLIB ONLY - NO PYDANTIC.

Entity resolution transforms messy real-world identifiers ("AAPL", "Apple Inc.",
"CIK 320193") into canonical Entity/Security/Listing objects. ResolutionResult
captures the outcome of this resolution with full transparency about what the
resolver could and couldn't do.

Key Design Concepts:

1. **Tier Capability Honesty**
   Different storage tiers have different capabilities. ResolutionResult
   transparently communicates what the tier could/couldn't honor:
   
   - Tier 0 (JSON): Current data only, no temporal resolution
   - Tier 1 (SQLite): Some temporal data, limited fuzzy matching
   - Tier 2+ (DuckDB/PostgreSQL): Full temporal, fuzzy, MIC filtering
   
   When a feature is requested but unavailable, warnings are added
   (not silent failures).

2. **Candidate-Based Resolution**
   Instead of returning just one match, resolution produces ranked candidates:
   
   - Multiple potential matches (e.g., "MS" → Morgan Stanley vs Microsoft)
   - Confidence scores for each candidate
   - Let the caller decide threshold for "confident" match

3. **Temporal Awareness**
   Point-in-time queries via as_of parameter, but honest about limitations:
   
   - as_of_honored: Was the date parameter actually used?
   - warnings: Explain if/why temporal filtering wasn't applied

Example:
    >>> from entityspine.domain import ResolutionResult, ResolutionStatus
    >>> result = resolve("AAPL", as_of=date(2020, 1, 1))
    >>> if result.found:
    ...     print(result.entity.primary_name)
    >>> if result.has_warnings:
    ...     for w in result.warnings:
    ...         print(f"Warning: {w}")
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
    
    ResolutionResult encapsulates everything about a resolution attempt:
    the query, what was found, confidence scores, warnings about
    limitations, and timing information.
    
    Note:
        This is NOT frozen (mutable) because resolution builds results
        incrementally via add_candidate(), add_warning(), etc.
    
    Design Principles:
        - **Transparent**: Never silently ignore parameters - add warnings
        - **Candidate-based**: Return ranked options, not just best guess
        - **Tier-honest**: Document what the storage tier couldn't do
        - **Measurable**: Track timing and confidence for monitoring
    
    Attributes:
        query: The original search string (ticker, name, identifier).
        status: Resolution outcome (FOUND, NOT_FOUND, AMBIGUOUS, ERROR).
        tier: Which storage tier provided this result.
        entity: The resolved Entity object (if found).
        security: The resolved Security object (if applicable).
        listing: The resolved Listing object (if applicable).
        candidates: All resolution candidates with scores.
        as_of: Requested point-in-time date (for temporal queries).
        as_of_honored: Whether as_of was actually applied.
        warnings: Transparency warnings about limitations.
        limits: Dict describing tier capability limitations.
        redirect_chain: Entity IDs followed during redirect resolution.
        confidence: Overall confidence score (0.0 to 1.0).
        resolved_at: Timestamp when resolution was performed.
        elapsed_ms: Time taken for resolution in milliseconds.
    
    Examples:
        Simple successful resolution:
        
        >>> result = resolver.resolve("AAPL")
        >>> result.found
        True
        >>> result.entity.primary_name
        'Apple Inc.'
        >>> result.confidence
        1.0
        
        Resolution with ambiguity:
        
        >>> result = resolver.resolve("MS")
        >>> result.status
        <ResolutionStatus.AMBIGUOUS: 'ambiguous'>
        >>> result.candidate_count
        2
        >>> for c in result.candidates:
        ...     print(f"{c.entity_name}: {c.score:.2f}")
        Morgan Stanley: 0.85
        Microsoft Corporation: 0.80
        
        Temporal query with tier limitation:
        
        >>> result = resolver.resolve("META", as_of=date(2020, 1, 1))
        >>> result.as_of_honored
        False  # Tier 0 can't do temporal
        >>> result.warnings
        ['as_of parameter ignored: listing validity data not available']
        >>> result.limits
        {'temporal_resolution': 'current_only', 'fuzzy_matching': 'not_available'}
    
    See Also:
        - ResolutionCandidate: Individual match candidates with scores
        - Entity, Security, Listing: The resolved domain objects
        - EntityResolver: The service that produces these results
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
