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
    A lightweight resolution match result containing IDs and match metadata.

    Manifesto
    ---------
    ResolutionCandidate embodies EntitySpine's "lazy hydration" principle: return
    IDs first, objects later. When resolving ambiguous queries like "MS" or "AA",
    we may find multiple potential matches. Rather than hydrating full Entity,
    Security, and Listing objects for each candidate (expensive), we return
    lightweight candidates with just IDs and match metadata. The caller decides
    which candidate to hydrate based on scores and context.

    This supports the Result[T] pattern (Principle #3): callers get transparent
    information about why matches occurred and can make informed decisions about
    which candidate to accept.

    Architecture
    ------------
    ::

        ┌────────────────────────────────────────────────────────────────┐
        │                    Resolution Process                          │
        │                                                                │
        │   Query("MS")                                                  │
        │       │                                                        │
        │       ▼                                                        │
        │   ┌─────────────────────────────────────────────────────────┐  │
        │   │               ResolutionCandidate[]                     │  │
        │   │  ┌──────────────────┐   ┌──────────────────┐            │  │
        │   │  │ score: 0.85     │   │ score: 0.80     │            │  │
        │   │  │ entity_id: E1   │   │ entity_id: E2   │            │  │
        │   │  │ match: "ticker" │   │ match: "alias"  │            │  │
        │   │  │ Morgan Stanley  │   │ Microsoft Corp  │            │  │
        │   │  └──────────────────┘   └──────────────────┘            │  │
        │   └─────────────────────────────────────────────────────────┘  │
        │       │                                                        │
        │       ▼  (caller decides)                                      │
        │   resolve.entity ← hydrate(best_candidate.entity_id)           │
        └────────────────────────────────────────────────────────────────┘

    Features
    --------
    - **Lightweight**: IDs only, ~50 bytes vs ~2KB for full object graph
    - **Ranked**: Score field enables confidence-based selection
    - **Transparent**: match_reason explains WHY the match occurred
    - **Traceable**: matched_scheme/value show WHAT matched
    - **Warning-aware**: Per-candidate warnings (e.g., "ticker expired")

    Examples
    --------
    Creating a candidate from a ticker match:

    >>> candidate = ResolutionCandidate(
    ...     score=0.95,
    ...     match_reason=MatchReason.EXACT_TICKER,
    ...     entity_id="01HQ8KQXYZ...",
    ...     security_id="01HQ8KQABC...",
    ...     listing_id="01HQ8KQ123...",
    ...     matched_scheme="ticker",
    ...     matched_value="AAPL",
    ... )
    >>> candidate.has_entity
    True
    >>> candidate.score
    0.95

    Candidate with warnings (expired ticker):

    >>> candidate = ResolutionCandidate(
    ...     score=0.70,
    ...     match_reason=MatchReason.HISTORICAL_TICKER,
    ...     entity_id="01HQ8...",
    ...     warnings=("ticker_expired_2020-01-15",),
    ... )
    >>> len(candidate.warnings)
    1

    Performance
    -----------
    - Memory: ~50 bytes per candidate (IDs + score + reason)
    - Serialization: JSON-serializable for API responses
    - Hydration: O(1) lookup when caller needs full objects

    Guardrails
    ----------
    - score must be in [0.0, 1.0] range (validated in __post_init__)
    - warnings automatically converted from list to tuple (immutability)
    - Frozen dataclass prevents accidental modification

    Context
    -------
    Used by EntityResolver to return multiple potential matches. The
    ResolutionResult.candidates list contains ResolutionCandidate objects
    ranked by score. Higher scores indicate better matches.

    Tags
    ----
    :tag domain-model: Core domain concept
    :tag resolution: Part of entity resolution subsystem
    :tag lightweight: Optimized for memory efficiency
    :tag principle-3: Implements Result[T] transparency

    Doc-Types
    ---------
    :api-ref: entityspine.domain.candidate.ResolutionCandidate
    :related: ResolutionResult, EntityResolver, MatchReason

    Attributes
    ----------
    score : float
        Match confidence score 0.0-1.0 (higher is better).
    match_reason : MatchReason
        Why this candidate matched (EXACT_TICKER, FUZZY_NAME, etc.).
    entity_id : str | None
        Matched entity ID (ULID).
    security_id : str | None
        Matched security ID (ULID).
    listing_id : str | None
        Matched listing ID (ULID).
    matched_scheme : str | None
        Which identifier scheme matched (e.g., "cik", "ticker", "isin").
    matched_value : str | None
        The actual value that matched (e.g., "AAPL", "0000320193").
    warnings : tuple
        Any warnings specific to this candidate.
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
