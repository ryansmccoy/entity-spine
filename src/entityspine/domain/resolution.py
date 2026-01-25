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
    Complete result of an entity resolution attempt with full transparency.

    Manifesto
    ---------
    ResolutionResult is the flagship implementation of EntitySpine's Result[T]
    pattern (Principle #3). It never silently fails or ignores parameters.
    Instead, it transparently communicates:

    - **What was found**: Entity, Security, Listing objects
    - **How confident we are**: Numerical scores from 0.0-1.0
    - **What we couldn't do**: Warnings about tier limitations
    - **Why we matched**: Full match reason audit trail

    This is critical for financial applications where understanding WHY a
    match occurred is as important as the match itself. Regulators and auditors
    need to trace resolution decisions back to their sources.

    Architecture
    ------------
    ::

        ┌─────────────────────────────────────────────────────────────────────┐
        │                     ResolutionResult Structure                       │
        │                                                                      │
        │   ┌─────────────────────────────────────────────────────────────┐   │
        │   │  Query: "AAPL"          Status: FOUND          Tier: T1    │   │
        │   └─────────────────────────────────────────────────────────────┘   │
        │                                │                                     │
        │          ┌────────────────────┴────────────────────┐                │
        │          ▼                                          ▼                │
        │   ┌─────────────────┐                    ┌─────────────────────┐    │
        │   │  Hydrated       │                    │  Candidates[]       │    │
        │   │  ┌───────────┐  │                    │  ┌───────────────┐  │    │
        │   │  │ Entity    │  │                    │  │ id, score,    │  │    │
        │   │  │ Apple Inc.│  │                    │  │ match_reason  │  │    │
        │   │  └───────────┘  │                    │  └───────────────┘  │    │
        │   │  ┌───────────┐  │                    └─────────────────────┘    │
        │   │  │ Security  │  │                                               │
        │   │  │ AAPL Comm │  │                    ┌─────────────────────┐    │
        │   │  └───────────┘  │                    │  Warnings[]         │    │
        │   │  ┌───────────┐  │                    │  - as_of ignored    │    │
        │   │  │ Listing   │  │                    │  - fuzzy unavail    │    │
        │   │  │ XNAS:AAPL │  │                    └─────────────────────┘    │
        │   │  └───────────┘  │                                               │
        │   └─────────────────┘                    ┌─────────────────────┐    │
        │                                          │  Limits{}           │    │
        │   confidence: 1.0                        │  temporal: current  │    │
        │   elapsed_ms: 15                         │  fuzzy: unavailable │    │
        │                                          └─────────────────────┘    │
        └─────────────────────────────────────────────────────────────────────┘

    Features
    --------
    - **Tier-Honest**: limits dict documents what storage tier couldn't do
    - **Temporal-Aware**: as_of queries with as_of_honored flag
    - **Candidate-Based**: Multiple matches with scores for ambiguous queries
    - **Redirect-Tracking**: redirect_chain shows entity ID traversal
    - **Measurable**: elapsed_ms enables performance monitoring

    Examples
    --------
    Simple successful resolution:

    >>> result = resolver.resolve("AAPL")
    >>> result.found
    True
    >>> result.entity.primary_name
    'Apple Inc.'
    >>> result.confidence
    1.0

    Checking for ambiguous results:

    >>> result = resolver.resolve("MS")
    >>> result.status
    <ResolutionStatus.AMBIGUOUS: 'ambiguous'>
    >>> for c in result.candidates:
    ...     print(f"{c.score:.2f}")
    0.85
    0.80

    Temporal query with tier limitations:

    >>> result = resolver.resolve("META", as_of=date(2020, 1, 1))
    >>> result.as_of_honored
    False
    >>> result.warnings
    ['as_of parameter ignored: tier 0 has current data only']
    >>> result.limits
    {'temporal_resolution': 'current_only'}

    Performance
    -----------
    - Memory: ~2-5KB per result (depending on hydrated objects)
    - Serialization: All fields JSON-serializable
    - Timing: elapsed_ms tracks resolution time for SLA monitoring

    Guardrails
    ----------
    - Mutable (not frozen) because resolution builds incrementally
    - status defaults to NOT_FOUND until resolution succeeds
    - warnings list is append-only during resolution
    - candidates sorted by score descending

    Context
    -------
    ResolutionResult is the primary return type from EntityResolver.resolve().
    The Tiered Storage design (Principle #5) means different tiers provide
    different capabilities, all documented in the limits dict.

    Tags
    ----
    :tag domain-model: Core domain concept
    :tag resolution: Primary resolution output
    :tag principle-3: Result[T] pattern implementation
    :tag principle-5: Tier capability documentation
    :tag transparency: Full audit trail

    Doc-Types
    ---------
    :api-ref: entityspine.domain.resolution.ResolutionResult
    :related: EntityResolver, ResolutionCandidate, ResolutionStatus

    Attributes
    ----------
    query : str
        The original search string (ticker, name, identifier).
    status : ResolutionStatus
        Resolution outcome (FOUND, NOT_FOUND, AMBIGUOUS, ERROR).
    tier : ResolutionTier
        Which storage tier provided this result (T0-T3).
    entity : Entity | None
        The resolved Entity object (if found).
    security : Security | None
        The resolved Security object (if applicable).
    listing : Listing | None
        The resolved Listing object (if applicable).
    candidates : list[ResolutionCandidate]
        All resolution candidates with scores (for ambiguous queries).
    as_of : date | None
        Requested point-in-time date (for temporal queries).
    as_of_honored : bool
        Whether as_of was actually applied by the storage tier.
    warnings : list[str]
        Transparency warnings about limitations.
    limits : dict
        Dict describing tier capability limitations.
    redirect_chain : list[str]
        Entity IDs followed during redirect resolution.
    confidence : float
        Overall confidence score (0.0 to 1.0).
    resolved_at : datetime
        Timestamp when resolution was performed.
    elapsed_ms : float
        Time taken for resolution in milliseconds.
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
