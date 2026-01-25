"""
Entity extraction and NLP artifact models.

These models support content intelligence features like:
- Named Entity Recognition (NER)
- Story clustering and tracking
- Article relationship detection
- Significance scoring

STDLIB ONLY - NO PYDANTIC.

These models are designed to be used by:
- feedspine: For deduplication and content analysis
- capture-spine: For storage and API responses (via Pydantic adapters)

Example:
    >>> from entityspine.domain.extraction import ExtractedEntity, ExtractionType
    >>> entity = ExtractedEntity(
    ...     extraction_type=ExtractionType.COMPANY,
    ...     text="Apple Inc.",
    ...     normalized="AAPL",
    ...     confidence=0.95,
    ... )
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

# =============================================================================
# Extraction Type Enums
# =============================================================================


class ExtractionType(str, Enum):
    """
    Types of entities that can be extracted from text.
    
    Broader than EntityType - includes non-entity concepts
    like filings, events, and metrics that appear in text.
    """

    # Entity types (map to EntityType where applicable)
    COMPANY = "COMPANY"  # Public/private companies → EntityType.ORGANIZATION
    PERSON = "PERSON"  # Executives, officials → EntityType.PERSON
    LOCATION = "LOCATION"  # Countries, cities, regions → EntityType.GEO
    ORG = "ORG"  # Government, NGO, institution → EntityType.ORGANIZATION

    # Financial types
    INSTRUMENT = "INSTRUMENT"  # Tickers, indices, commodities
    METRIC = "METRIC"  # Revenue, EPS, guidance numbers

    # Content types
    FILING = "FILING"  # SEC form types (10-K, 8-K)
    EVENT = "EVENT"  # Earnings, M&A, IPO events


class StoryStatus(str, Enum):
    """Lifecycle status of a story cluster."""

    EMERGING = "emerging"  # New story, < 5 articles
    ACTIVE = "active"  # Active story, growing
    DECLINING = "declining"  # Story slowing down
    ARCHIVED = "archived"  # Story concluded


class LinkType(str, Enum):
    """Types of relationships between articles/content."""

    SAME_EVENT = "same_event"  # Different sources, same event
    FOLLOW_UP = "follow_up"  # Later article references earlier
    ANGLE_SHIFT = "angle_shift"  # Same entities, different perspective
    ENTITY_CROSSOVER = "entity_crossover"  # Shared entity in new context
    DUPLICATE = "duplicate"  # Same article, different source


class LinkDirection(str, Enum):
    """Directionality of content link."""

    REFERENCES = "references"  # Source → Target
    REFERENCED_BY = "referenced_by"  # Target → Source
    MUTUAL = "mutual"  # Bidirectional


# =============================================================================
# Extraction Models (stdlib dataclasses)
# =============================================================================


@dataclass
class TextSpan:
    """Location of extracted text within source content."""

    start: int
    end: int

    @property
    def length(self) -> int:
        return self.end - self.start


@dataclass
class ExtractedEntity:
    """
    A single entity mention extracted from text.
    
    This is the stdlib equivalent of capture-spine's EntityMention.
    Can be converted to Pydantic for API responses.
    
    Attributes:
        extraction_type: Classification of the extraction
        text: Raw text as found in source
        normalized: Canonical form for matching (ticker, standard name)
        confidence: Extraction confidence score (0-1)
        span: Optional location in source text
        source: Where in the content this was found (title, body, etc.)
        metadata: Additional extraction-specific data
        
    Example:
        >>> entity = ExtractedEntity(
        ...     extraction_type=ExtractionType.COMPANY,
        ...     text="Apple Inc.",
        ...     normalized="AAPL",
        ...     confidence=0.95,
        ...     source="title",
        ...     metadata={"exchange": "NASDAQ", "cik": "0000320193"}
        ... )
    """

    extraction_type: ExtractionType
    text: str
    normalized: str
    confidence: float = 1.0
    span: TextSpan | None = None
    source: str = "body"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractionStats:
    """Statistics about an extraction run."""

    duration_ms: int = 0
    source_length: int = 0
    entity_count: int = 0

    @property
    def entity_density(self) -> float:
        """Entities per 100 characters."""
        if self.source_length == 0:
            return 0.0
        return (self.entity_count / self.source_length) * 100


@dataclass
class StoryEntity:
    """Entity reference within a story cluster."""

    extraction_type: ExtractionType
    normalized: str


@dataclass
class StoryTimeline:
    """Temporal information for a story cluster."""

    first_article_at: datetime
    last_article_at: datetime
    peak_velocity_at: datetime | None = None


@dataclass
class StoryMetrics:
    """Computed metrics for a story cluster."""

    article_count: int = 0
    unique_sources: int = 0
    velocity_current: float = 0.0  # articles/hour
    velocity_peak: float = 0.0
    source_diversity: float = 0.0  # 0-1
    sentiment_avg: float | None = None  # -1 to 1


@dataclass
class StoryCluster:
    """
    A cluster of related articles about the same story/topic.
    
    Stories evolve through lifecycle stages (emerging → active → archived)
    and track metrics about coverage velocity and source diversity.
    
    Attributes:
        cluster_id: Unique identifier
        status: Current lifecycle status
        headline: Representative headline
        summary: Optional LLM-generated summary
        primary_entities: Key entities in this story
        timeline: Temporal boundaries
        metrics: Computed coverage metrics
        member_record_ids: IDs of articles in this cluster
        
    Example:
        >>> cluster = StoryCluster(
        ...     cluster_id="story_abc123",
        ...     status=StoryStatus.ACTIVE,
        ...     headline="Apple Reports Q4 Earnings",
        ...     primary_entities=[StoryEntity(ExtractionType.COMPANY, "AAPL")],
        ...     timeline=StoryTimeline(first_article_at=now, last_article_at=now),
        ...     metrics=StoryMetrics(article_count=15, unique_sources=8),
        ... )
    """

    cluster_id: str
    status: StoryStatus
    headline: str
    primary_entities: list[StoryEntity]
    timeline: StoryTimeline
    metrics: StoryMetrics
    summary: str | None = None
    member_record_ids: list[str] = field(default_factory=list)


@dataclass
class LinkEvidence:
    """Evidence supporting a content link."""

    shared_entities: list[StoryEntity] = field(default_factory=list)
    temporal_distance_hours: float = 0.0
    title_similarity: float = 0.0
    entity_overlap_ratio: float = 0.0


@dataclass
class ContentLink:
    """
    A relationship between two pieces of content.
    
    Used to track how articles relate to each other:
    - Same event from different sources
    - Follow-up/update articles
    - Topic drift and angle shifts
    
    Attributes:
        source_id: ID of the source content
        target_id: ID of the target content
        link_type: Type of relationship
        direction: Directionality
        confidence: Link confidence (0-1)
        explanation: Human-readable reason
        evidence: Supporting data for the link
    """

    source_id: str
    target_id: str
    link_type: LinkType
    direction: LinkDirection = LinkDirection.REFERENCES
    confidence: float = 1.0
    explanation: str = ""
    evidence: LinkEvidence = field(default_factory=LinkEvidence)


# =============================================================================
# Significance Scoring
# =============================================================================


@dataclass
class SignificanceComponent:
    """A single component of a significance score."""

    score: float  # 0-1
    weight: float  # 0-1
    reason: str

    @property
    def weighted(self) -> float:
        return self.score * self.weight


@dataclass
class SignificanceScore:
    """
    Composite significance score for content prioritization.
    
    Components:
    - novelty: How new/unique is this content?
    - velocity: How fast is this story spreading?
    - source_diversity: How many different sources?
    - entity_importance: How important are the entities?
    - temporal_decay: How recent is this?
    
    Example:
        >>> score = SignificanceScore(
        ...     novelty=SignificanceComponent(0.9, 0.3, "First report"),
        ...     velocity=SignificanceComponent(0.7, 0.2, "Spreading fast"),
        ...     source_diversity=SignificanceComponent(0.8, 0.15, "12 sources"),
        ...     entity_importance=SignificanceComponent(0.85, 0.2, "AAPL tier-1"),
        ...     temporal_decay=SignificanceComponent(0.95, 0.15, "2 hours ago"),
        ... )
        >>> score.composite_score
        0.834
    """

    novelty: SignificanceComponent
    velocity: SignificanceComponent
    source_diversity: SignificanceComponent
    entity_importance: SignificanceComponent
    temporal_decay: SignificanceComponent
    computed_at: datetime = field(default_factory=datetime.now)
    valid_until: datetime | None = None

    @property
    def composite_score(self) -> float:
        """Weighted sum of all components."""
        return (
            self.novelty.weighted +
            self.velocity.weighted +
            self.source_diversity.weighted +
            self.entity_importance.weighted +
            self.temporal_decay.weighted
        )

    @property
    def explanation(self) -> str:
        """Generate explanation from highest-weighted components."""
        components = [
            ("novelty", self.novelty),
            ("velocity", self.velocity),
            ("source_diversity", self.source_diversity),
            ("entity_importance", self.entity_importance),
            ("temporal_decay", self.temporal_decay),
        ]
        sorted_components = sorted(components, key=lambda x: x[1].weighted, reverse=True)
        top_two = sorted_components[:2]
        return f"High significance due to {top_two[0][0]} and {top_two[1][0]}"
