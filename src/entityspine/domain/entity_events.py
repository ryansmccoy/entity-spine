"""
Entity lifecycle event models (stdlib dataclass).

STDLIB ONLY - NO PYDANTIC.

These models track significant changes to entities over time:
- MergeEvent: When two entities are combined into one
- SplitEvent: When one entity becomes multiple (spin-offs, etc.)

This enables:
- Audit trail: "When and why was this entity merged?"
- Undo capability: "Can we reverse this merge?"
- Analytics: "How often do we have duplicate entities?"

v2.3.4 Design:
- Events are immutable facts about what happened
- Each event links to explanation for "why"
- Events can be linked to resolution runs for batch auditing
"""

from dataclasses import dataclass, field
from datetime import datetime

from entityspine.domain.timestamps import generate_ulid, utc_now


@dataclass(frozen=True, slots=True)
class MergeEvent:
    """
    Records when two entities were merged into one with full audit trail.

    Manifesto
    ---------
    MergeEvent is the cornerstone of EntitySpine's "cluster-first, merge-later"
    philosophy. Entity resolution often discovers duplicates - two database
    records representing the same real-world company. Rather than silently
    merging them (and potentially losing data), we:

    1. Create explicit MergeEvent records documenting the decision
    2. Preserve a snapshot of the source entity before merge
    3. Create a redirect from source → target (the source entity becomes
       a redirect pointer, not deleted)
    4. Track who/what made the decision and why

    This supports auditability: regulators and analysts can trace back every
    entity merge to understand how the canonical entity graph was constructed.

    Architecture
    ------------
    ::

        ┌─────────────────────────────────────────────────────────────────────┐
        │                     Entity Merge Process                             │
        │                                                                      │
        │   Before Merge                        After Merge                    │
        │   ┌──────────────────┐                ┌──────────────────┐          │
        │   │ Entity E1        │                │ Entity E1        │          │
        │   │ "APPLE INC"      │                │ status: REDIRECT │          │
        │   │ CIK: 320193      │                │ redirect_to: E2  │          │
        │   └──────────────────┘                └────────┬─────────┘          │
        │                                                │                     │
        │   ┌──────────────────┐                        │ redirect            │
        │   │ Entity E2        │                        ▼                     │
        │   │ "Apple Inc."     │                ┌──────────────────┐          │
        │   │ CIK: 320193      │                │ Entity E2        │          │
        │   └──────────────────┘                │ "Apple Inc."     │ canonical│
        │                                       │ CIK: 320193      │          │
        │   MergeEvent created:                 │ (merged claims)  │          │
        │   ┌───────────────────────────────────┴──────────────────┘          │
        │   │ source_entity_id: E1                                            │
        │   │ target_entity_id: E2                                            │
        │   │ reason: same_cik                                                │
        │   │ confidence: 1.0                                                 │
        │   │ source_snapshot: {JSON of E1}                                   │
        │   │ reversible: true                                                │
        │   └─────────────────────────────────────────────────────────────────┘
        └─────────────────────────────────────────────────────────────────────┘

    Features
    --------
    - **Non-Destructive**: Source entity becomes redirect, not deleted
    - **Snapshot Preservation**: Full JSON of source entity before merge
    - **Reversibility**: Merges can be undone if mistakes are discovered
    - **Attribution**: merged_by tracks human or system responsible
    - **Explanation Link**: explanation_id links to detailed reasoning
    - **Batch Context**: run_id links to ResolutionRun for bulk operations

    Examples
    --------
    Recording a merge due to matching CIK:

    >>> event = MergeEvent(
    ...     source_entity_id="01HQ8...",  # APPLE INC (duplicate)
    ...     target_entity_id="01HQ9...",  # Apple Inc. (canonical)
    ...     reason="same_cik",
    ...     confidence=1.0,
    ...     merged_by="resolution_pipeline",
    ...     source_snapshot='{"entity_id": "01HQ8...", "primary_name": "APPLE INC"}',
    ... )
    >>> event.reversible
    True

    Recording a manual merge decision:

    >>> event = MergeEvent(
    ...     source_entity_id="01HQA...",
    ...     target_entity_id="01HQB...",
    ...     reason="manual_review",
    ...     confidence=0.95,
    ...     merged_by="analyst@company.com",
    ...     explanation_id="01HQC...",  # Links to detailed Explanation
    ...     notes="Confirmed via SEC filing cross-reference",
    ... )

    Checking if a merge was reversed:

    >>> event.reversed
    False
    >>> # Later, if reversed:
    >>> event.reversed
    True
    >>> event.reversed_by
    'data_quality_team'

    Performance
    -----------
    - Storage: ~1-2KB per event (snapshot can be large)
    - Indexing: source/target entity IDs indexed for lookup
    - Query: "Show all merges involving entity X" is O(1)

    Guardrails
    ----------
    - source_entity_id required (validated in __post_init__)
    - target_entity_id required (validated in __post_init__)
    - Cannot merge entity into itself (validated)
    - Frozen dataclass ensures immutability

    Context
    -------
    MergeEvent works with ClusteringService (finds duplicates),
    ConflictResolver (decides which entity is canonical), and
    Explanation (documents why the merge was appropriate).

    Tags
    ----
    :tag domain-model: Core domain concept
    :tag audit: Complete merge audit trail
    :tag deduplication: Entity deduplication process
    :tag reversible: Supports undo operations

    Doc-Types
    ---------
    :api-ref: entityspine.domain.entity_events.MergeEvent
    :related: SplitEvent, ClusteringService, ConflictResolver, Explanation

    Attributes
    ----------
    event_id : str
        ULID primary key (auto-generated).
    source_entity_id : str
        Entity that was merged away (becomes redirect).
    target_entity_id : str
        Canonical entity that remains.
    reason : str
        Why the merge happened (same_cik, name_match, manual_review, etc.).
    explanation_id : str | None
        Link to detailed Explanation record.
    run_id : str | None
        Link to ResolutionRun if part of batch operation.
    confidence : float
        Confidence in the merge decision (0.0-1.0).
    merged_by : str | None
        User/system that performed the merge.
    merged_at : datetime
        When the merge occurred.
    source_snapshot : str | None
        JSON snapshot of source entity before merge (for reversal).
    reversible : bool
        Whether this merge can be undone.
    reversed : bool
        Whether this merge was reversed.
    reversed_at : datetime | None
        When the merge was reversed.
    reversed_by : str | None
        Who reversed the merge.
    notes : str | None
        Additional notes about the merge.
    created_at : datetime
        Record creation timestamp.
    """

    # Primary key
    event_id: str = field(default_factory=generate_ulid)

    # Merge details
    source_entity_id: str = ""  # Entity being merged away
    target_entity_id: str = ""  # Canonical entity

    # Reason
    reason: str = "duplicate_resolution"
    explanation_id: str | None = None
    run_id: str | None = None

    # Confidence
    confidence: float = 1.0

    # Merge metadata
    merged_by: str | None = None
    merged_at: datetime = field(default_factory=utc_now)

    # Snapshot for potential reversal
    source_snapshot: str | None = None  # JSON of source entity

    # Reversal tracking
    reversible: bool = True
    reversed: bool = False
    reversed_at: datetime | None = None
    reversed_by: str | None = None

    # Notes
    notes: str | None = None

    # Timestamps
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self):
        """Validate merge event."""
        if not self.source_entity_id:
            raise ValueError("source_entity_id is required")
        if not self.target_entity_id:
            raise ValueError("target_entity_id is required")
        if self.source_entity_id == self.target_entity_id:
            raise ValueError("Cannot merge entity into itself")


@dataclass(frozen=True, slots=True)
class SplitEvent:
    """
    Records when one entity was split into multiple for corporate actions.

    Manifesto
    ---------
    SplitEvent captures the inverse of MergeEvent: when a single entity
    becomes multiple distinct entities. This happens during:

    - **Spin-offs**: Parent company spins off a division (e.g., PayPal from eBay)
    - **Divestitures**: Selling a business unit that becomes independent
    - **Corporate Restructuring**: Breaking a conglomerate into parts
    - **Data Correction**: Realizing two different companies were incorrectly
      merged and need to be separated

    Like MergeEvent, SplitEvent maintains full audit trail: who made the
    decision, why, and what the original entity looked like before split.

    Architecture
    ------------
    ::

        ┌─────────────────────────────────────────────────────────────────────┐
        │                     Entity Split Process                             │
        │                                                                      │
        │   Before Split                        After Split                    │
        │   ┌──────────────────┐                                              │
        │   │ Entity E1        │                ┌──────────────────┐          │
        │   │ "eBay Inc."      │        ┌──────▶│ Entity E1        │          │
        │   │ (incl. PayPal)   │        │       │ "eBay Inc."      │          │
        │   │                  │        │       │ (marketplace)    │          │
        │   └──────────────────┘        │       └──────────────────┘          │
        │           │                   │                                      │
        │           │ split             │       ┌──────────────────┐          │
        │           │ 2015-07-18        └──────▶│ Entity E2        │          │
        │           │                           │ "PayPal Holdings"│          │
        │           │                           │ (new entity)     │          │
        │           ▼                           └──────────────────┘          │
        │   SplitEvent created:                                               │
        │   ┌─────────────────────────────────────────────────────────────┐   │
        │   │ source_entity_id: E1                                        │   │
        │   │ target_entity_ids: (E1, E2)   # Original + new entities    │   │
        │   │ reason: spinoff                                             │   │
        │   │ effective_date: 2015-07-18                                  │   │
        │   │ source_snapshot: {JSON of E1 before split}                  │   │
        │   └─────────────────────────────────────────────────────────────┘   │
        └─────────────────────────────────────────────────────────────────────┘

    Features
    --------
    - **Multiple Targets**: Supports 1→N splits (not just 1→2)
    - **Effective Dating**: Business date when split took effect
    - **Snapshot Preservation**: Original entity state before split
    - **Attribution**: split_by tracks responsible party
    - **Explanation Link**: explanation_id for detailed reasoning

    Examples
    --------
    Recording a spin-off:

    >>> event = SplitEvent(
    ...     source_entity_id="01HQ8...",  # Original company
    ...     target_entity_ids=("01HQ8...", "01HQA..."),  # eBay, PayPal
    ...     reason="spinoff",
    ...     effective_date=datetime(2015, 7, 18),
    ...     split_by="corporate_actions_feed",
    ...     notes="PayPal spin-off from eBay",
    ... )
    >>> len(event.target_entity_ids)
    2

    Recording a data correction split:

    >>> event = SplitEvent(
    ...     source_entity_id="01HQB...",
    ...     target_entity_ids=("01HQC...", "01HQD..."),
    ...     reason="data_correction",
    ...     split_by="data_quality_team",
    ...     notes="Incorrectly merged companies separated per JIRA-456",
    ... )

    Three-way split (rare but possible):

    >>> event = SplitEvent(
    ...     source_entity_id="01HQE...",
    ...     target_entity_ids=("01HQF...", "01HQG...", "01HQH..."),
    ...     reason="restructuring",
    ... )

    Performance
    -----------
    - Storage: ~1-2KB per event (snapshot size varies)
    - Query: Find splits by source or target entity
    - Timeline: effective_date enables temporal queries

    Guardrails
    ----------
    - source_entity_id required (validated)
    - At least one target_entity_id required (validated)
    - target_entity_ids automatically converted from list to tuple
    - Frozen dataclass ensures immutability

    Context
    -------
    SplitEvent is less common than MergeEvent but equally important for
    maintaining accurate entity history. Used by TimelineService to
    reconstruct entity state at any point in time.

    Tags
    ----
    :tag domain-model: Core domain concept
    :tag audit: Complete split audit trail
    :tag corporate-actions: Spin-offs, divestitures
    :tag timeline: Temporal entity tracking

    Doc-Types
    ---------
    :api-ref: entityspine.domain.entity_events.SplitEvent
    :related: MergeEvent, TimelineService, Explanation

    Attributes
    ----------
    event_id : str
        ULID primary key (auto-generated).
    source_entity_id : str
        Original entity that was split.
    target_entity_ids : tuple[str, ...]
        New entities created from the split.
    reason : str
        Why the split happened (spinoff, divestiture, data_correction, etc.).
    explanation_id : str | None
        Link to detailed Explanation record.
    run_id : str | None
        Link to ResolutionRun if part of batch operation.
    split_by : str | None
        User/system that performed the split.
    split_at : datetime
        When the split was recorded in the system.
    effective_date : datetime | None
        Business date when split took effect in the real world.
    source_snapshot : str | None
        JSON snapshot of source entity before split.
    notes : str | None
        Additional notes about the split.
    created_at : datetime
        Record creation timestamp.
    """

    # Primary key
    event_id: str = field(default_factory=generate_ulid)

    # Split details
    source_entity_id: str = ""  # Original entity
    target_entity_ids: tuple[str, ...] = ()  # New entities

    # Reason
    reason: str = "spinoff"
    explanation_id: str | None = None
    run_id: str | None = None

    # Split metadata
    split_by: str | None = None
    split_at: datetime = field(default_factory=utc_now)
    effective_date: datetime | None = None  # Business date

    # Snapshot
    source_snapshot: str | None = None  # JSON of source entity

    # Notes
    notes: str | None = None

    # Timestamps
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self):
        """Validate split event."""
        if not self.source_entity_id:
            raise ValueError("source_entity_id is required")
        if not self.target_entity_ids or len(self.target_entity_ids) < 1:
            raise ValueError("At least one target_entity_id is required")
        # Convert list to tuple if needed
        if isinstance(self.target_entity_ids, list):
            object.__setattr__(self, "target_entity_ids", tuple(self.target_entity_ids))
