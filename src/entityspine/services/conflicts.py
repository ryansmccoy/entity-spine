"""
Conflict Resolution and Duplicate Detection for EntitySpine.

This module provides:
1. Duplicate detection across entities
2. Conflict resolution strategies
3. Merge operations with audit trail
4. Data quality scoring

Design Principles:
- Multiple strategies for different conflict types
- Confidence-based resolution
- Full audit trail of resolutions
- Pluggable matching algorithms
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, TypeVar

from entityspine.core.timestamps import utc_now
from entityspine.core.ulid import generate_ulid
from entityspine.domain import Entity, IdentifierClaim, IdentifierScheme
from entityspine.services.fuzzy import compute_name_similarity

logger = logging.getLogger(__name__)

T = TypeVar('T')


# =============================================================================
# CONFLICT TYPES
# =============================================================================

class ConflictType(Enum):
    """Types of conflicts that can occur."""
    DUPLICATE_ENTITY = "duplicate_entity"
    DUPLICATE_CLAIM = "duplicate_claim"
    CONFLICTING_CLAIM = "conflicting_claim"  # Same identifier, different entities
    NAME_MISMATCH = "name_mismatch"
    TICKER_REUSE = "ticker_reuse"  # Same ticker used by different companies over time
    CIK_COLLISION = "cik_collision"
    DATA_INCONSISTENCY = "data_inconsistency"


class ResolutionStrategy(Enum):
    """Strategies for resolving conflicts."""
    KEEP_FIRST = "keep_first"        # Keep the first/existing record
    KEEP_LATEST = "keep_latest"      # Keep the most recent
    KEEP_HIGHEST_CONFIDENCE = "keep_highest_confidence"
    MERGE = "merge"                  # Merge records together
    MANUAL = "manual"                # Flag for manual review
    TEMPORAL_SPLIT = "temporal_split"  # Split by time period
    CREATE_REDIRECT = "create_redirect"  # Create redirect from old to new


class ConflictStatus(Enum):
    """Status of a detected conflict."""
    DETECTED = "detected"
    IN_REVIEW = "in_review"
    RESOLVED = "resolved"
    IGNORED = "ignored"


# =============================================================================
# CONFLICT MODELS
# =============================================================================

@dataclass
class ConflictRecord:
    """
    Record of a detected conflict.
    """
    conflict_id: str = field(default_factory=generate_ulid)
    conflict_type: ConflictType = ConflictType.DUPLICATE_ENTITY
    status: ConflictStatus = ConflictStatus.DETECTED

    # Entities involved
    entity_ids: tuple[str, ...] = field(default_factory=tuple)
    claim_ids: tuple[str, ...] = field(default_factory=tuple)

    # Conflict details
    description: str = ""
    confidence: float = 0.0  # How confident are we this is a real conflict

    # Evidence
    evidence: dict[str, Any] = field(default_factory=dict)

    # Resolution
    resolution_strategy: ResolutionStrategy | None = None
    resolved_by: str | None = None  # User or system ID
    resolution_notes: str | None = None
    winning_entity_id: str | None = None

    # Timing
    detected_at: datetime = field(default_factory=utc_now)
    resolved_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "conflict_id": self.conflict_id,
            "conflict_type": self.conflict_type.value,
            "status": self.status.value,
            "entity_ids": list(self.entity_ids),
            "claim_ids": list(self.claim_ids),
            "description": self.description,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "resolution_strategy": self.resolution_strategy.value if self.resolution_strategy else None,
            "resolved_by": self.resolved_by,
            "resolution_notes": self.resolution_notes,
            "winning_entity_id": self.winning_entity_id,
            "detected_at": self.detected_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }


@dataclass
class DuplicateCandidate:
    """
    Potential duplicate entity pair.
    """
    entity_id_a: str
    entity_id_b: str

    # Matching scores
    name_similarity: float = 0.0
    identifier_overlap: float = 0.0
    overall_score: float = 0.0

    # Matching details
    matching_identifiers: list[tuple[str, str]] = field(default_factory=list)  # (scheme, value)
    similar_names: list[tuple[str, str, float]] = field(default_factory=list)  # (name_a, name_b, score)

    # Recommendation
    recommended_action: ResolutionStrategy = ResolutionStrategy.MANUAL

    def __hash__(self):
        return hash((min(self.entity_id_a, self.entity_id_b),
                     max(self.entity_id_a, self.entity_id_b)))


@dataclass
class MergeOperation:
    """
    Specification for merging two entities.
    """
    source_entity_id: str  # Entity to merge from (will be redirected)
    target_entity_id: str  # Entity to merge into (will remain)

    # What to transfer
    transfer_claims: bool = True
    transfer_securities: bool = True
    transfer_listings: bool = True

    # Merge behavior
    preserve_source_name: bool = True  # Add source name as alias
    create_redirect: bool = True

    # Audit
    reason: str = ""
    performed_by: str | None = None


# =============================================================================
# DUPLICATE DETECTOR
# =============================================================================

class DuplicateDetector:
    """
    Detects potential duplicate entities.
    
    Detection methods:
    1. Exact identifier match (CIK, LEI, etc.)
    2. Fuzzy name matching
    3. Shared identifier claims
    4. Combined scoring
    """

    def __init__(
        self,
        name_threshold: float = 0.85,
        identifier_weight: float = 0.7,
        name_weight: float = 0.3,
    ):
        self.name_threshold = name_threshold
        self.identifier_weight = identifier_weight
        self.name_weight = name_weight

    def find_duplicates_for_entity(
        self,
        entity: Entity,
        entity_claims: list[IdentifierClaim],
        all_entities: list[Entity],
        all_claims: dict[str, list[IdentifierClaim]],  # entity_id -> claims
    ) -> list[DuplicateCandidate]:
        """Find potential duplicates for a specific entity."""
        candidates = []

        for other in all_entities:
            if other.entity_id == entity.entity_id:
                continue

            other_claims = all_claims.get(other.entity_id, [])
            candidate = self._compare_entities(
                entity, entity_claims,
                other, other_claims
            )

            if candidate and candidate.overall_score > 0.5:
                candidates.append(candidate)

        # Sort by score
        candidates.sort(key=lambda c: -c.overall_score)
        return candidates

    def _compare_entities(
        self,
        entity_a: Entity,
        claims_a: list[IdentifierClaim],
        entity_b: Entity,
        claims_b: list[IdentifierClaim],
    ) -> DuplicateCandidate | None:
        """Compare two entities for potential duplication."""
        # Check identifier overlap
        matching_ids = []
        for claim_a in claims_a:
            for claim_b in claims_b:
                if (claim_a.scheme == claim_b.scheme and
                    claim_a.value.upper() == claim_b.value.upper()):
                    matching_ids.append((claim_a.scheme.value, claim_a.value))

        identifier_score = min(1.0, len(matching_ids) / max(1, min(len(claims_a), len(claims_b))))

        # Check name similarity
        name_score = compute_name_similarity(
            entity_a.primary_name,
            entity_b.primary_name
        )

        similar_names = []
        if name_score >= self.name_threshold:
            similar_names.append((entity_a.primary_name, entity_b.primary_name, name_score))

        # Check aliases
        for alias_a in entity_a.aliases:
            alias_score = compute_name_similarity(alias_a, entity_b.primary_name)
            if alias_score >= self.name_threshold:
                similar_names.append((alias_a, entity_b.primary_name, alias_score))

            for alias_b in entity_b.aliases:
                alias_score = compute_name_similarity(alias_a, alias_b)
                if alias_score >= self.name_threshold:
                    similar_names.append((alias_a, alias_b, alias_score))

        # Calculate overall score
        max_name_score = max([s[2] for s in similar_names]) if similar_names else name_score
        overall_score = (
            self.identifier_weight * identifier_score +
            self.name_weight * max_name_score
        )

        if overall_score < 0.3 and not matching_ids:
            return None

        # Determine recommended action
        if matching_ids and identifier_score >= 0.8:
            action = ResolutionStrategy.MERGE
        elif max_name_score >= 0.95 and not matching_ids:
            action = ResolutionStrategy.MANUAL  # Same name, no shared IDs - needs review
        else:
            action = ResolutionStrategy.MANUAL

        return DuplicateCandidate(
            entity_id_a=entity_a.entity_id,
            entity_id_b=entity_b.entity_id,
            name_similarity=max_name_score,
            identifier_overlap=identifier_score,
            overall_score=overall_score,
            matching_identifiers=matching_ids,
            similar_names=similar_names,
            recommended_action=action,
        )


# =============================================================================
# CONFLICT RESOLVER
# =============================================================================

class ConflictResolver:
    """
    Resolves conflicts between entities and claims.
    
    Strategies:
    - KEEP_FIRST: Keep existing, discard incoming
    - KEEP_LATEST: Replace with newer data
    - KEEP_HIGHEST_CONFIDENCE: Use confidence scores
    - MERGE: Combine records
    - TEMPORAL_SPLIT: Create time-bounded records
    """

    def __init__(self, default_strategy: ResolutionStrategy = ResolutionStrategy.KEEP_HIGHEST_CONFIDENCE):
        self.default_strategy = default_strategy
        self._strategy_handlers: dict[ResolutionStrategy, Callable] = {
            ResolutionStrategy.KEEP_FIRST: self._resolve_keep_first,
            ResolutionStrategy.KEEP_LATEST: self._resolve_keep_latest,
            ResolutionStrategy.KEEP_HIGHEST_CONFIDENCE: self._resolve_keep_highest_confidence,
            ResolutionStrategy.MERGE: self._resolve_merge,
        }

    def resolve_duplicate_claims(
        self,
        claims: list[IdentifierClaim],
        strategy: ResolutionStrategy | None = None,
    ) -> tuple[IdentifierClaim, list[IdentifierClaim]]:
        """
        Resolve duplicate identifier claims.
        
        Returns:
            (winning_claim, losing_claims)
        """
        if not claims:
            raise ValueError("No claims to resolve")
        if len(claims) == 1:
            return (claims[0], [])

        strategy = strategy or self.default_strategy

        if strategy == ResolutionStrategy.KEEP_FIRST:
            sorted_claims = sorted(claims, key=lambda c: c.created_at)
            return (sorted_claims[0], sorted_claims[1:])

        elif strategy == ResolutionStrategy.KEEP_LATEST:
            sorted_claims = sorted(claims, key=lambda c: c.created_at, reverse=True)
            return (sorted_claims[0], sorted_claims[1:])

        elif strategy == ResolutionStrategy.KEEP_HIGHEST_CONFIDENCE:
            sorted_claims = sorted(claims, key=lambda c: (-c.confidence, c.created_at))
            return (sorted_claims[0], sorted_claims[1:])

        else:
            # Default to highest confidence
            sorted_claims = sorted(claims, key=lambda c: (-c.confidence, c.created_at))
            return (sorted_claims[0], sorted_claims[1:])

    def _resolve_keep_first(self, items: list[T]) -> tuple[T, list[T]]:
        """Keep the first item."""
        return (items[0], items[1:])

    def _resolve_keep_latest(self, items: list[T]) -> tuple[T, list[T]]:
        """Keep the latest item."""
        sorted_items = sorted(items, key=lambda x: getattr(x, 'created_at', datetime.min), reverse=True)
        return (sorted_items[0], sorted_items[1:])

    def _resolve_keep_highest_confidence(self, items: list[T]) -> tuple[T, list[T]]:
        """Keep the highest confidence item."""
        sorted_items = sorted(items, key=lambda x: getattr(x, 'confidence', 0), reverse=True)
        return (sorted_items[0], sorted_items[1:])

    def _resolve_merge(self, items: list[T]) -> tuple[T, list[T]]:
        """Merge items (returns first, others need manual merge)."""
        return (items[0], items[1:])


# =============================================================================
# DATA QUALITY SCORER
# =============================================================================

@dataclass
class DataQualityScore:
    """Score representing data quality for an entity."""
    entity_id: str
    overall_score: float = 0.0  # 0-100

    # Component scores
    completeness_score: float = 0.0  # Required fields present
    consistency_score: float = 0.0   # No conflicting data
    freshness_score: float = 0.0     # How recent is the data
    provenance_score: float = 0.0    # Source reliability

    # Issues found
    issues: list[str] = field(default_factory=list)

    # Recommendations
    recommendations: list[str] = field(default_factory=list)


class DataQualityScorer:
    """
    Scores data quality for entities.
    
    Checks:
    - Required fields present
    - Identifier validity
    - Name normalization
    - Temporal consistency
    - Source reliability
    """

    REQUIRED_FIELDS = ['primary_name', 'entity_type']
    RECOMMENDED_FIELDS = ['jurisdiction', 'source_system']
    HIGH_CONFIDENCE_SOURCES = ['sec', 'edgar', 'official']

    def score_entity(
        self,
        entity: Entity,
        claims: list[IdentifierClaim],
    ) -> DataQualityScore:
        """Score data quality for an entity."""
        issues = []
        recommendations = []

        # Completeness
        completeness = self._score_completeness(entity, claims, issues, recommendations)

        # Consistency
        consistency = self._score_consistency(entity, claims, issues, recommendations)

        # Freshness
        freshness = self._score_freshness(entity, claims, issues, recommendations)

        # Provenance
        provenance = self._score_provenance(entity, claims, issues, recommendations)

        # Overall (weighted average)
        overall = (
            completeness * 0.3 +
            consistency * 0.3 +
            freshness * 0.2 +
            provenance * 0.2
        )

        return DataQualityScore(
            entity_id=entity.entity_id,
            overall_score=overall,
            completeness_score=completeness,
            consistency_score=consistency,
            freshness_score=freshness,
            provenance_score=provenance,
            issues=issues,
            recommendations=recommendations,
        )

    def _score_completeness(
        self,
        entity: Entity,
        claims: list[IdentifierClaim],
        issues: list[str],
        recommendations: list[str],
    ) -> float:
        score = 100.0

        # Check required fields
        if not entity.primary_name:
            score -= 50
            issues.append("Missing primary_name")

        # Check for identifiers
        if not claims:
            score -= 30
            recommendations.append("Add identifier claims (CIK, LEI, etc.)")

        # Check for recommended fields
        if not entity.jurisdiction:
            score -= 10
            recommendations.append("Add jurisdiction")

        if not entity.source_system or entity.source_system == "unknown":
            score -= 10
            recommendations.append("Specify source_system")

        return max(0, score)

    def _score_consistency(
        self,
        entity: Entity,
        claims: list[IdentifierClaim],
        issues: list[str],
        recommendations: list[str],
    ) -> float:
        score = 100.0

        # Check for conflicting claims
        claims_by_scheme: dict[IdentifierScheme, list[IdentifierClaim]] = {}
        for claim in claims:
            if claim.scheme not in claims_by_scheme:
                claims_by_scheme[claim.scheme] = []
            claims_by_scheme[claim.scheme].append(claim)

        # Flag multiple active claims of same scheme
        for scheme, scheme_claims in claims_by_scheme.items():
            active_claims = [c for c in scheme_claims if c.status.value == "active"]
            if len(active_claims) > 1:
                # Multiple active claims - check if temporally valid
                score -= 15
                issues.append(f"Multiple active {scheme.value} claims")

        return max(0, score)

    def _score_freshness(
        self,
        entity: Entity,
        claims: list[IdentifierClaim],
        issues: list[str],
        recommendations: list[str],
    ) -> float:
        score = 100.0

        # Check last update time
        now = utc_now()
        days_since_update = (now - entity.updated_at).days

        if days_since_update > 365:
            score -= 30
            recommendations.append("Consider refreshing entity data")
        elif days_since_update > 180:
            score -= 15

        return max(0, score)

    def _score_provenance(
        self,
        entity: Entity,
        claims: list[IdentifierClaim],
        issues: list[str],
        recommendations: list[str],
    ) -> float:
        score = 100.0

        # Check source
        if entity.source_system == "unknown":
            score -= 30
            issues.append("Unknown data source")
        elif entity.source_system.lower() not in self.HIGH_CONFIDENCE_SOURCES:
            score -= 10

        # Check claim sources
        for claim in claims:
            if claim.source == "unknown":
                score -= 5

        return max(0, min(100, score))


# =============================================================================
# CONFLICT STORE
# =============================================================================

class ConflictStore:
    """In-memory conflict store (can be extended for persistence)."""

    def __init__(self):
        self._conflicts: dict[str, ConflictRecord] = {}
        self._by_entity: dict[str, set[str]] = {}  # entity_id -> conflict_ids

    def save(self, conflict: ConflictRecord) -> None:
        self._conflicts[conflict.conflict_id] = conflict
        for eid in conflict.entity_ids:
            if eid not in self._by_entity:
                self._by_entity[eid] = set()
            self._by_entity[eid].add(conflict.conflict_id)

    def get(self, conflict_id: str) -> ConflictRecord | None:
        return self._conflicts.get(conflict_id)

    def get_for_entity(self, entity_id: str) -> list[ConflictRecord]:
        conflict_ids = self._by_entity.get(entity_id, set())
        return [self._conflicts[cid] for cid in conflict_ids if cid in self._conflicts]

    def get_unresolved(self) -> list[ConflictRecord]:
        return [c for c in self._conflicts.values()
                if c.status in (ConflictStatus.DETECTED, ConflictStatus.IN_REVIEW)]


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Types
    "ConflictType",
    "ResolutionStrategy",
    "ConflictStatus",

    # Models
    "ConflictRecord",
    "DuplicateCandidate",
    "MergeOperation",
    "DataQualityScore",

    # Services
    "DuplicateDetector",
    "ConflictResolver",
    "DataQualityScorer",
    "ConflictStore",
]
