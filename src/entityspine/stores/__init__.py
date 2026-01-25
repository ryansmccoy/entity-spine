"""
EntitySpine Stores - Storage backends.

Tier 0-1 stores use ONLY stdlib (zero external dependencies):
- JsonEntityStore: In-memory with JSON file persistence (Tier 0)
- SqliteStore: SQLite using stdlib sqlite3 (Tier 1)

Higher-tier stores require optional dependencies:
- DuckDbStore: Analytics-optimized (Tier 2) - [duckdb] extra
- PostgresStore: Production (Tier 3) - [postgres] extra
- ElasticsearchStore: Full-text search (Tier 4/5) - [search] extra
- Neo4jStore: Graph database (Tier 4/5) - [graph] extra

ORM-based stores (SqlModelStore) are in entityspine.adapters.orm
and require the [orm] extra.

ALL stores return domain dataclasses (entityspine.domain.*).

Repository Protocols:
    The stores.protocols module defines reusable repository interfaces
    that can be implemented by any backend (SQLite, PostgreSQL, JSON, etc.).

v2.3.4: Added audit trail stores:
- ProvenanceStore: Source tracking
- MergeEventStore: Entity merge history
- ExplanationStore: Decision explanations
- ResolutionRunStore: Batch execution tracking
- SourceRecordStore: Raw data preservation
- DataQualityStore: Quality check results
"""

# v2.3.4: Audit trail stores
from entityspine.stores.audit_stores import (
    DataQualityStore,
    ExplanationStore,
    MergeEventStore,
    ProvenanceStore,
    ResolutionRunStore,
    SourceRecordStore,
)
from entityspine.stores.json_store import JsonEntityStore
from entityspine.stores.protocols import (
    AddressRepositoryProtocol,
    AssetRepositoryProtocol,
    BrandRepositoryProtocol,
    CaseRepositoryProtocol,
    ClaimRepositoryProtocol,
    ClusterRepositoryProtocol,
    ContractRepositoryProtocol,
    EntityRepositoryProtocol,
    EventRepositoryProtocol,
    GeoRepositoryProtocol,
    ListingRepositoryProtocol,
    ProductRepositoryProtocol,
    RelationshipRepositoryProtocol,
    RoleRepositoryProtocol,
    SecurityRepositoryProtocol,
)
from entityspine.stores.sqlite import SqliteStore

__all__ = [
    # Stores
    "JsonEntityStore",
    "SqliteStore",
    # v2.3.4: Audit trail stores
    "ProvenanceStore",
    "MergeEventStore",
    "ExplanationStore",
    "ResolutionRunStore",
    "SourceRecordStore",
    "DataQualityStore",
    # Repository Protocols
    "AddressRepositoryProtocol",
    "AssetRepositoryProtocol",
    "BrandRepositoryProtocol",
    "CaseRepositoryProtocol",
    "ClaimRepositoryProtocol",
    "ClusterRepositoryProtocol",
    "ContractRepositoryProtocol",
    "EntityRepositoryProtocol",
    "EventRepositoryProtocol",
    "GeoRepositoryProtocol",
    "ListingRepositoryProtocol",
    "ProductRepositoryProtocol",
    "RelationshipRepositoryProtocol",
    "RoleRepositoryProtocol",
    "SecurityRepositoryProtocol",
]

# Optional: Elasticsearch (requires [search] extra)
try:
    from entityspine.stores.elasticsearch_store import ElasticsearchStore
    __all__.append("ElasticsearchStore")
except ImportError:
    pass

# Optional: Neo4j (requires [graph] extra)
try:
    from entityspine.stores.neo4j_store import Neo4jStore
    __all__.append("Neo4jStore")
except ImportError:
    pass

# Optional: SqlModelStore (requires [orm] extra)
# from entityspine.adapters.orm import SqlModelStore
