"""
Clustering Domain Models for EntitySpine.

STDLIB ONLY - NO PYDANTIC.

These models represent entity clustering and deduplication concepts:
- ClusterStatus: Status of a deduplication cluster
- DuplicateCandidate: A candidate duplicate entity pair
- ClusterInfo: Rich information about a cluster
- BlockingConfig: Configuration for blocking/candidate generation
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from entityspine.domain.graph import EntityCluster, EntityClusterMember
from entityspine.domain.timestamps import utc_now

if TYPE_CHECKING:
    from entityspine.domain.entity import Entity


class ClusterStatus(str, Enum):
    """Status of a deduplication cluster."""

    PENDING = "pending"  # Awaiting review
    APPROVED = "approved"  # Approved for merge
    REJECTED = "rejected"  # False positive, not duplicates
    MERGED = "merged"  # Already merged


@dataclass
class DuplicateCandidate:
    """
    A candidate duplicate entity pair.
    
    Represents two entities that may be duplicates based on
    similarity scoring and matching criteria.
    """

    entity_a: "Entity"
    entity_b: "Entity"
    similarity_score: float
    match_reasons: list[str]
    blocking_key: str | None = None  # What caused them to be compared

    @property
    def confidence(self) -> str:
        """Human-readable confidence level."""
        if self.similarity_score >= 0.95:
            return "very_high"
        elif self.similarity_score >= 0.85:
            return "high"
        elif self.similarity_score >= 0.70:
            return "medium"
        else:
            return "low"


@dataclass
class ClusterInfo:
    """
    Rich information about a deduplication cluster.
    
    Wraps an EntityCluster with member entities and status.
    """

    cluster: EntityCluster
    members: list[EntityClusterMember]
    entities: list["Entity"]
    canonical_entity: "Entity | None"
    status: ClusterStatus = ClusterStatus.PENDING

    @property
    def member_count(self) -> int:
        return len(self.members)

    @property
    def entity_names(self) -> list[str]:
        return [e.primary_name for e in self.entities]


@dataclass
class BlockingConfig:
    """
    Configuration for blocking (candidate pair generation).
    
    Blocking reduces the O(n²) comparison problem by grouping
    entities that share "blocking keys" (e.g., same name prefix).
    """

    # Blocking keys to use
    use_name_prefix: bool = True  # First N chars of name
    name_prefix_length: int = 4
    use_soundex: bool = True  # Phonetic blocking
    use_cik_prefix: bool = True  # First 4 digits of CIK
    use_industry: bool = False  # Same SIC code (requires industry data)

    # Fuzzy matching settings
    min_similarity: float = 0.7  # Minimum similarity to be a candidate
    max_candidates_per_entity: int = 50  # Limit candidates per entity

    # Performance settings
    batch_size: int = 1000  # Entities to process at once
