"""
EntitySpine Services

This module provides high-level services for common EntitySpine operations:

High-Level APIs (The "killer features"):
- EntityResolver: Resolve any identifier to an entity (ticker, CIK, name)
- FuzzyMatcher: Fuzzy string matching for entity names
- GraphService: Traverse entity relationships (subsidiaries, officers, paths)
- ClusteringService: Detect and manage duplicate entities
- TimelineService: Track entity history over time

Core Services:
- SymbologyRefreshService: Refresh symbology from multiple sources
- RefreshResult: Result of a symbology refresh operation

Example:
    >>> from entityspine import EntityResolver
    >>>
    >>> resolver = EntityResolver()  # Auto-loads SEC data
    >>> result = resolver.resolve("AAPL")
    >>> print(result.entity.primary_name)  # Apple Inc.
    >>>
    >>> # Fuzzy name matching
    >>> result = resolver.resolve("Apple")
    >>> print(result.confidence)  # 0.95
"""

from entityspine.services.symbology_refresh import (
    RefreshResult,
    SymbologyRefreshService,
    SymbologySource,
)

# High-level resolver API
from entityspine.services.resolver import EntityResolver, ResolverConfig

# Fuzzy matching
from entityspine.services.fuzzy import (
    FuzzyMatcher,
    compute_name_similarity,
    normalize_company_name,
)

# Simple lookup utilities
from entityspine.services.lookup import (
    Lookup,
    ticker,
    cik,
    name,
    tickers,
    ciks,
    names,
    fast_ticker,
    fast_cik,
    offline_ticker,
    offline_cik,
    offline_name,
    COMMON_COMPANIES,
    get_db_path,
    use_shared_db,
    reset_resolver,
    lei_from_isin,
    isins_from_lei,
    bic_from_lei,
)

# Graph traversal
from entityspine.services.graph_service import (
    GraphService,
    EntityNetwork,
    EntityPath,
    OfficerInfo,
    PathStep,
    RelatedEntity,
)

# Entity clustering/deduplication (import from domain)
from entityspine.domain.clustering import (
    ClusterStatus,
    DuplicateCandidate,
    ClusterInfo,
    BlockingConfig,
)
from entityspine.services.clustering import ClusteringService

# Timeline/history (import from domain)
from entityspine.domain.timeline import (
    TimelineEventType,
    TimelineEvent,
    EntitySnapshot,
    StateDiff,
)
from entityspine.services.timeline import TimelineService

# Audit trail and change tracking
from entityspine.services.audit import (
    AuditManager,
    ChangeEvent,
    ChangeType,
    EntityKind,
    SqliteAuditStore,
)

# Conflict resolution and duplicate detection
from entityspine.services.conflicts import (
    ConflictType,
    ResolutionStrategy,
    ConflictStatus,
    ConflictRecord,
    DuplicateCandidate as DuplicateCandidateConflict,
    MergeOperation,
    DataQualityScore,
    DuplicateDetector,
    ConflictResolver,
    DataQualityScorer,
    ConflictStore,
)

# Data quality and validation
from entityspine.services.data_quality import (
    ValidationSeverity,
    ValidationCategory,
    ValidationIssue,
    ValidationResult,
    IdentifierValidator,
    EntityValidator,
    DataCleanser,
    BatchValidator,
    BatchValidationResult,
)

# Backward compatibility alias
EventType = TimelineEventType

__all__ = [
    # Core services
    "RefreshResult",
    "SymbologyRefreshService",
    "SymbologySource",
    # Resolver
    "EntityResolver",
    "ResolverConfig",
    # Fuzzy matching
    "FuzzyMatcher",
    "compute_name_similarity",
    "normalize_company_name",
    # Lookup utilities
    "Lookup",
    "ticker",
    "cik",
    "name",
    "tickers",
    "ciks",
    "names",
    "fast_ticker",
    "fast_cik",
    "offline_ticker",
    "offline_cik",
    "offline_name",
    "COMMON_COMPANIES",
    "get_db_path",
    "use_shared_db",
    "reset_resolver",
    # Graph traversal
    "GraphService",
    "EntityNetwork",
    "EntityPath",
    "OfficerInfo",
    "PathStep",
    "RelatedEntity",
    # Clustering
    "ClusteringService",
    "ClusterInfo",
    "ClusterStatus",
    "DuplicateCandidate",
    "BlockingConfig",
    # Timeline
    "TimelineService",
    "TimelineEventType",
    "TimelineEvent",
    "EntitySnapshot",
    "StateDiff",
    "EventType",  # Backward compatibility alias
    # Audit trail
    "AuditManager",
    "ChangeEvent",
    "ChangeType",
    "EntityKind",
    "SqliteAuditStore",
    # Conflict resolution
    "ConflictType",
    "ResolutionStrategy",
    "ConflictStatus",
    "ConflictRecord",
    "DuplicateCandidateConflict",
    "MergeOperation",
    "DataQualityScore",
    "DuplicateDetector",
    "ConflictResolver",
    "DataQualityScorer",
    "ConflictStore",
    # Data quality
    "ValidationSeverity",
    "ValidationCategory",
    "ValidationIssue",
    "ValidationResult",
    "IdentifierValidator",
    "EntityValidator",
    "DataCleanser",
    "BatchValidator",
    "BatchValidationResult",
]