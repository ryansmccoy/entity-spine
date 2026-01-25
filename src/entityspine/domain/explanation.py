"""
Explanation and Resolution Run models (stdlib dataclass).

STDLIB ONLY - NO PYDANTIC.

These models provide explainability for entity resolution decisions:
- Explanation: Human-readable notes on WHY a decision was made
- ResolutionRun: Tracks a batch resolution execution

This enables:
- Audit trail: "Why did the system match these entities?"
- Debugging: "What went wrong in yesterday's batch?"
- Monitoring: "How is resolution quality trending?"

v2.3.4 Design:
- Explanation is attached to claims, merges, and other decisions
- ResolutionRun tracks batch execution with full metrics
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from entityspine.domain.enums import DecisionType, RunStatus
from entityspine.domain.timestamps import generate_ulid, utc_now


@dataclass(frozen=True, slots=True)
class Explanation:
    """
    Human-readable explanation of a resolution decision.

    Explanation records capture the reasoning behind entity resolution
    decisions. This is critical for:
    - Auditing: "Why were these two entities matched?"
    - Debugging: "Why did this match fail?"
    - Training: "What patterns lead to good matches?"

    Attributes:
        explanation_id: ULID primary key.
        decision_type: Type of decision (match, merge, reject, etc.).
        summary: One-line summary of the decision.
        details: Detailed explanation text.
        factors: JSON dict of factors that influenced decision.
        confidence: Confidence in the decision (0.0-1.0).
        match_scores: JSON dict of individual match scores.
        rule_hits: Which rules/heuristics fired.
        created_at: Record creation timestamp.

    Examples:
        High-confidence match explanation:

        >>> exp = Explanation(
        ...     decision_type="match",
        ...     summary="Matched on CIK with exact name",
        ...     details="CIK 0000320193 matches exactly. Name 'Apple Inc.' matches with 1.0 score.",
        ...     factors={"cik_match": True, "name_score": 1.0, "jurisdiction_match": True},
        ...     confidence=1.0,
        ... )

        Lower-confidence match:

        >>> exp = Explanation(
        ...     decision_type="match",
        ...     summary="Fuzzy name match only",
        ...     details="No identifier match. Name 'APPLE INC' fuzzy matched 'Apple Inc.' with 0.92 score.",
        ...     factors={"name_score": 0.92, "no_identifiers": True},
        ...     confidence=0.85,
        ... )

        Rejection explanation:

        >>> exp = Explanation(
        ...     decision_type=DecisionType.REJECT,
        ...     summary="Different CIKs",
        ...     details="Candidate has CIK 0000123456, target has CIK 0000320193. Cannot be same entity.",
        ...     factors={"cik_mismatch": True},
        ... )
    """

    # Primary key
    explanation_id: str = field(default_factory=generate_ulid)

    # Decision info
    decision_type: DecisionType | str = DecisionType.MATCH  # Allow str for backward compatibility
    summary: str = ""  # One-line summary
    details: str = ""  # Detailed explanation

    # Factors (stored as frozen dict via field)
    # Note: dict reference is frozen, contents set once at creation
    # This follows existing pattern in ResolutionResult.limits
    factors: dict[str, Any] = field(default_factory=dict)

    # Scores
    confidence: float = 1.0
    match_scores: dict[str, float] = field(default_factory=dict)

    # Rules
    rule_hits: tuple[str, ...] = ()  # Which rules/heuristics fired

    # Timestamps
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self):
        """Convert mutable collections to appropriate types."""
        if isinstance(self.rule_hits, list):
            object.__setattr__(self, "rule_hits", tuple(self.rule_hits))


@dataclass(frozen=True, slots=True)
class ResolutionRun:
    """
    Tracks a batch resolution execution.

    ResolutionRun captures everything about a resolution batch:
    - Input parameters (for reproducibility)
    - Output metrics (for monitoring)
    - Timing information (for performance)
    - Error tracking (for debugging)

    Attributes:
        run_id: ULID primary key.
        input_params: Configuration used for this run.
        source_record_ids: Records processed in this run.
        started_at: When the run started.
        completed_at: When the run completed.
        stage_metrics: Metrics per pipeline stage.
        entities_created: Number of new entities created.
        entities_updated: Number of entities updated.
        entities_merged: Number of entities merged.
        claims_created: Number of new claims created.
        claims_superseded: Number of claims superseded.
        avg_confidence: Average confidence across matches.
        ambiguous_count: Number of ambiguous resolutions.
        error_count: Number of errors encountered.
        status: Run status (RUNNING, COMPLETED, FAILED, CANCELLED).
        error_message: Error message if failed.
        created_at: Record creation timestamp.

    Examples:
        >>> run = ResolutionRun(
        ...     input_params={"blocking_keys": ["cik", "name_prefix"]},
        ...     source_record_ids=("rec1", "rec2", "rec3"),
        ... )
        >>> # After completion:
        >>> completed_run = dataclasses.replace(
        ...     run,
        ...     status="COMPLETED",
        ...     completed_at=utc_now(),
        ...     entities_created=150,
        ...     entities_merged=12,
        ... )
    """

    # Primary key
    run_id: str = field(default_factory=generate_ulid)

    # Inputs (for reproducibility)
    # Note: dict[str, Any] follows existing pattern in ResolutionResult.limits
    # The dict reference is frozen, contents are set once at creation
    input_params: dict[str, Any] = field(default_factory=dict)
    source_record_ids: tuple[str, ...] = ()

    # Timing
    started_at: datetime = field(default_factory=utc_now)
    completed_at: datetime | None = None

    # Stage metrics (dict with field default_factory)
    stage_metrics: dict[str, dict[str, int]] = field(default_factory=dict)
    # Example: {"normalize": {"processed": 1000, "errors": 5}, ...}

    # Output summary
    entities_created: int = 0
    entities_updated: int = 0
    entities_merged: int = 0
    claims_created: int = 0
    claims_superseded: int = 0

    # Quality metrics
    avg_confidence: float = 0.0
    ambiguous_count: int = 0
    error_count: int = 0

    # Status
    status: RunStatus = RunStatus.RUNNING
    error_message: str | None = None

    # Timestamps
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self):
        """Convert mutable collections to appropriate types."""
        if isinstance(self.source_record_ids, list):
            object.__setattr__(self, "source_record_ids", tuple(self.source_record_ids))

    @property
    def is_complete(self) -> bool:
        """Check if run is complete (success or failure)."""
        return self.status in (RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED)

    @property
    def is_successful(self) -> bool:
        """Check if run completed successfully."""
        return self.status == RunStatus.COMPLETED

    @property
    def duration_seconds(self) -> float | None:
        """Get run duration in seconds."""
        if self.completed_at is None:
            return None
        return (self.completed_at - self.started_at).total_seconds()


@dataclass(frozen=True, slots=True)
class ResolutionRunDiff:
    """
    Diff between two resolution runs.

    Used to compare what changed between runs.

    Attributes:
        run_a_id: First run ID.
        run_b_id: Second run ID.
        entities_added: Entity IDs in B but not A.
        entities_removed: Entity IDs in A but not B.
        entities_modified: Entity IDs different in A vs B.
    """

    run_a_id: str
    run_b_id: str

    entities_added: tuple[str, ...] = ()
    entities_removed: tuple[str, ...] = ()
    entities_modified: tuple[str, ...] = ()
