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

# Entity clustering/deduplication (import from domain)
from entityspine.domain.clustering import (
    BlockingConfig,
    ClusterInfo,
    ClusterStatus,
    DuplicateCandidate,
)

# Timeline/history (import from domain)
from entityspine.domain.timeline import (
    EntitySnapshot,
    StateDiff,
    TimelineEvent,
    TimelineEventType,
)

# Audit trail and change tracking
from entityspine.services.audit import (
    AuditManager,
    ChangeEvent,
    ChangeType,
    EntityKind,
    SqliteAuditStore,
)
from entityspine.services.clustering import ClusteringService

# Conflict resolution and duplicate detection
from entityspine.services.conflicts import (
    ConflictRecord,
    ConflictResolver,
    ConflictStatus,
    ConflictStore,
    ConflictType,
    DataQualityScore,
    DataQualityScorer,
    DuplicateDetector,
    MergeOperation,
    ResolutionStrategy,
)
from entityspine.services.conflicts import (
    DuplicateCandidate as DuplicateCandidateConflict,
)

# Data quality and validation
from entityspine.services.data_quality import (
    BatchValidationResult,
    BatchValidator,
    DataCleanser,
    EntityValidator,
    IdentifierValidator,
    ValidationCategory,
    ValidationIssue,
    ValidationResult,
    ValidationSeverity,
)

# Fuzzy matching
from entityspine.services.fuzzy import (
    FuzzyMatcher,
    compute_name_similarity,
    normalize_company_name,
)

# Graph traversal
from entityspine.services.graph_service import (
    EntityNetwork,
    EntityPath,
    GraphService,
    OfficerInfo,
    PathStep,
    RelatedEntity,
)

# Simple lookup utilities
from entityspine.services.lookup import (
    COMMON_COMPANIES,
    Lookup,
    bic_from_lei,
    cik,
    ciks,
    fast_cik,
    fast_ticker,
    get_db_path,
    isins_from_lei,
    lei_from_isin,
    name,
    names,
    offline_cik,
    offline_name,
    offline_ticker,
    reset_resolver,
    ticker,
    tickers,
    use_shared_db,
)

# High-level resolver API
from entityspine.services.resolver import EntityResolver, ResolverConfig
from entityspine.services.symbology_refresh import (
    RefreshResult,
    SymbologyRefreshService,
    SymbologySource,
)
from entityspine.services.timeline import TimelineService

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
