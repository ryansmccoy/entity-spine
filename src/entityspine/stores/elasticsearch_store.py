"""
Elasticsearch Store for EntitySpine (Tier 4/5).

Provides full-text search, fuzzy matching, and autocomplete capabilities
that PostgreSQL cannot efficiently provide at scale.

Features:
- Fuzzy name matching ("Appel" → "Apple Inc.")
- Autocomplete with edge-ngrams
- Multi-field search with relevance scoring
- Typo tolerance
- Synonym expansion

Usage:
    from entityspine.stores.elasticsearch_store import ElasticsearchStore
    
    store = ElasticsearchStore(hosts=["http://localhost:9200"])
    await store.initialize()
    
    # Index an entity
    await store.index_entity(entity)
    
    # Search with fuzzy matching
    results = await store.search("Appel Inc", limit=10)
    
    # Autocomplete
    results = await store.autocomplete("micro", limit=5)

Installation:
    pip install entityspine[search]
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any

logger = logging.getLogger(__name__)

# Check for elasticsearch dependency
try:
    from elasticsearch import AsyncElasticsearch
    from elasticsearch.helpers import async_bulk

    HAS_ELASTICSEARCH = True
except ImportError:
    HAS_ELASTICSEARCH = False
    AsyncElasticsearch = None  # type: ignore
    async_bulk = None  # type: ignore

if TYPE_CHECKING:
    from entityspine.domain import Entity


@dataclass
class SearchResult:
    """A search result with relevance score."""

    entity_id: str
    primary_name: str
    entity_type: str
    score: float
    highlights: dict[str, list[str]] | None = None
    source: dict[str, Any] | None = None


# =============================================================================
# Index Configuration
# =============================================================================

ENTITY_INDEX_NAME = "entityspine_entities"

ENTITY_INDEX_MAPPING = {
    "mappings": {
        "properties": {
            # Core fields
            "entity_id": {"type": "keyword"},
            "primary_name": {
                "type": "text",
                "analyzer": "entity_name_analyzer",
                "fields": {
                    "keyword": {"type": "keyword"},
                    "autocomplete": {
                        "type": "text",
                        "analyzer": "autocomplete_analyzer",
                        "search_analyzer": "standard",
                    },
                    "fuzzy": {
                        "type": "text",
                        "analyzer": "fuzzy_analyzer",
                    },
                },
            },
            "aliases": {
                "type": "text",
                "analyzer": "entity_name_analyzer",
                "fields": {
                    "keyword": {"type": "keyword"},
                },
            },
            # Classification
            "entity_type": {"type": "keyword"},
            "status": {"type": "keyword"},
            "jurisdiction": {"type": "keyword"},
            "sic_code": {"type": "keyword"},
            # Identifiers (nested for precise matching)
            "identifiers": {
                "type": "nested",
                "properties": {
                    "scheme": {"type": "keyword"},
                    "value": {"type": "keyword"},
                },
            },
            # Convenience identifier fields (for direct queries)
            "cik": {"type": "keyword"},
            "lei": {"type": "keyword"},
            "ticker": {"type": "keyword"},
            # Metadata
            "source_system": {"type": "keyword"},
            "created_at": {"type": "date"},
            "updated_at": {"type": "date"},
        },
    },
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0,
        "analysis": {
            "analyzer": {
                # Main entity name analyzer
                "entity_name_analyzer": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": [
                        "lowercase",
                        "entity_synonyms",
                        "english_stemmer",
                    ],
                },
                # Autocomplete analyzer (edge n-grams)
                "autocomplete_analyzer": {
                    "type": "custom",
                    "tokenizer": "autocomplete_tokenizer",
                    "filter": ["lowercase"],
                },
                # Fuzzy analyzer (for typo tolerance)
                "fuzzy_analyzer": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": ["lowercase", "asciifolding"],
                },
            },
            "tokenizer": {
                "autocomplete_tokenizer": {
                    "type": "edge_ngram",
                    "min_gram": 2,
                    "max_gram": 20,
                    "token_chars": ["letter", "digit"],
                },
            },
            "filter": {
                "english_stemmer": {
                    "type": "stemmer",
                    "language": "english",
                },
                "entity_synonyms": {
                    "type": "synonym",
                    "synonyms": [
                        "inc, incorporated, corporation, corp",
                        "llc, limited liability company",
                        "ltd, limited",
                        "plc, public limited company",
                        "intl, international",
                        "tech, technology",
                        "pharma, pharmaceutical",
                    ],
                },
            },
        },
    },
}


# =============================================================================
# Elasticsearch Store
# =============================================================================


class ElasticsearchStore:
    """
    Elasticsearch-backed entity search store.

    Provides capabilities that PostgreSQL cannot efficiently handle:
    - Fuzzy text matching with typo tolerance
    - Autocomplete with edge-ngrams
    - Multi-field relevance scoring
    - Synonym expansion
    """

    def __init__(
        self,
        hosts: list[str] | None = None,
        index_name: str = ENTITY_INDEX_NAME,
        **kwargs,
    ):
        """
        Initialize Elasticsearch store.

        Args:
            hosts: Elasticsearch hosts. Defaults to ["http://localhost:9200"]
            index_name: Name of the entity index
            **kwargs: Additional AsyncElasticsearch options
        """
        if not HAS_ELASTICSEARCH:
            raise ImportError(
                "Elasticsearch not installed. Run: pip install entityspine[search]"
            )

        self.hosts = hosts or ["http://localhost:9200"]
        self.index_name = index_name
        self.client = AsyncElasticsearch(hosts=self.hosts, **kwargs)
        self._initialized = False

    async def initialize(self) -> None:
        """Create index with mappings if it doesn't exist."""
        if self._initialized:
            return

        try:
            exists = await self.client.indices.exists(index=self.index_name)
            if not exists:
                await self.client.indices.create(
                    index=self.index_name,
                    body=ENTITY_INDEX_MAPPING,
                )
                logger.info(f"Created Elasticsearch index: {self.index_name}")
            self._initialized = True
        except Exception as e:
            logger.error(f"Failed to initialize Elasticsearch: {e}")
            raise

    async def close(self) -> None:
        """Close the Elasticsearch connection."""
        await self.client.close()

    # =========================================================================
    # Indexing
    # =========================================================================

    async def index_entity(self, entity: Entity, identifiers: list[dict] | None = None) -> None:
        """
        Index a single entity.

        Args:
            entity: Entity to index
            identifiers: Optional list of identifier claims
        """
        doc = self._entity_to_doc(entity, identifiers)
        await self.client.index(
            index=self.index_name,
            id=entity.entity_id,
            document=doc,
        )

    async def bulk_index(self, entities: list[tuple[Entity, list[dict] | None]]) -> dict:
        """
        Bulk index multiple entities.

        Args:
            entities: List of (entity, identifiers) tuples

        Returns:
            Bulk operation results
        """

        def generate_actions():
            for entity, identifiers in entities:
                doc = self._entity_to_doc(entity, identifiers)
                yield {
                    "_index": self.index_name,
                    "_id": entity.entity_id,
                    "_source": doc,
                }

        success, failed = await async_bulk(self.client, generate_actions())
        return {"success": success, "failed": failed}

    async def delete_entity(self, entity_id: str) -> None:
        """Delete an entity from the index."""
        await self.client.delete(
            index=self.index_name,
            id=entity_id,
            ignore=[404],
        )

    def _entity_to_doc(self, entity: Entity, identifiers: list[dict] | None = None) -> dict:
        """Convert entity to Elasticsearch document."""
        doc = {
            "entity_id": entity.entity_id,
            "primary_name": entity.primary_name,
            "aliases": list(entity.aliases) if entity.aliases else [],
            "entity_type": entity.entity_type.value if hasattr(entity.entity_type, "value") else str(entity.entity_type),
            "status": entity.status.value if hasattr(entity.status, "value") else str(entity.status),
            "jurisdiction": entity.jurisdiction,
            "sic_code": entity.sic_code,
            "source_system": entity.source_system,
            "created_at": entity.created_at.isoformat() if entity.created_at else None,
            "updated_at": entity.updated_at.isoformat() if entity.updated_at else None,
        }

        # Add identifiers
        if identifiers:
            doc["identifiers"] = [
                {"scheme": i.get("scheme"), "value": i.get("value")}
                for i in identifiers
            ]
            # Also add convenience fields
            for i in identifiers:
                scheme = i.get("scheme", "").lower()
                if scheme == "cik":
                    doc["cik"] = i.get("value")
                elif scheme == "lei":
                    doc["lei"] = i.get("value")
                elif scheme == "ticker":
                    doc["ticker"] = i.get("value")

        # CIK from source_id if SEC
        if entity.source_system == "sec" and entity.source_id:
            doc["cik"] = entity.source_id

        return doc

    # =========================================================================
    # Search
    # =========================================================================

    async def search(
        self,
        query: str,
        limit: int = 10,
        offset: int = 0,
        filters: dict | None = None,
        highlight: bool = True,
    ) -> list[SearchResult]:
        """
        Full-text search with fuzzy matching.

        Args:
            query: Search query (name, ticker, etc.)
            limit: Maximum results
            offset: Pagination offset
            filters: Optional filters (entity_type, status, etc.)
            highlight: Whether to include highlights

        Returns:
            List of SearchResult with relevance scores
        """
        # Build multi-match query with boosting
        must = [
            {
                "multi_match": {
                    "query": query,
                    "fields": [
                        "primary_name^5",
                        "primary_name.fuzzy^3",
                        "aliases^2",
                        "ticker^4",
                        "cik^4",
                    ],
                    "type": "best_fields",
                    "fuzziness": "AUTO",
                    "prefix_length": 1,
                },
            }
        ]

        # Build filter clauses
        filter_clauses = []
        if filters:
            if filters.get("entity_type"):
                filter_clauses.append({"term": {"entity_type": filters["entity_type"]}})
            if filters.get("status"):
                filter_clauses.append({"term": {"status": filters["status"]}})
            if filters.get("jurisdiction"):
                filter_clauses.append({"term": {"jurisdiction": filters["jurisdiction"]}})

        body = {
            "query": {
                "bool": {
                    "must": must,
                    "filter": filter_clauses,
                },
            },
            "from": offset,
            "size": limit,
        }

        if highlight:
            body["highlight"] = {
                "fields": {
                    "primary_name": {},
                    "aliases": {},
                },
                "pre_tags": ["<mark>"],
                "post_tags": ["</mark>"],
            }

        response = await self.client.search(index=self.index_name, body=body)

        results = []
        for hit in response["hits"]["hits"]:
            source = hit["_source"]
            results.append(
                SearchResult(
                    entity_id=source["entity_id"],
                    primary_name=source["primary_name"],
                    entity_type=source.get("entity_type", "unknown"),
                    score=hit["_score"],
                    highlights=hit.get("highlight"),
                    source=source,
                )
            )

        return results

    async def autocomplete(
        self,
        prefix: str,
        limit: int = 10,
        filters: dict | None = None,
    ) -> list[SearchResult]:
        """
        Autocomplete search using edge-ngrams.

        Args:
            prefix: Prefix to autocomplete (e.g., "micro")
            limit: Maximum suggestions
            filters: Optional filters

        Returns:
            List of autocomplete suggestions
        """
        must = [
            {
                "match": {
                    "primary_name.autocomplete": {
                        "query": prefix,
                        "operator": "and",
                    },
                },
            }
        ]

        filter_clauses = []
        if filters:
            if filters.get("entity_type"):
                filter_clauses.append({"term": {"entity_type": filters["entity_type"]}})

        body = {
            "query": {
                "bool": {
                    "must": must,
                    "filter": filter_clauses,
                },
            },
            "size": limit,
            "_source": ["entity_id", "primary_name", "entity_type", "ticker"],
        }

        response = await self.client.search(index=self.index_name, body=body)

        return [
            SearchResult(
                entity_id=hit["_source"]["entity_id"],
                primary_name=hit["_source"]["primary_name"],
                entity_type=hit["_source"].get("entity_type", "unknown"),
                score=hit["_score"],
            )
            for hit in response["hits"]["hits"]
        ]

    async def search_by_identifier(
        self,
        scheme: str,
        value: str,
    ) -> SearchResult | None:
        """
        Exact match search by identifier.

        Args:
            scheme: Identifier scheme (cik, lei, ticker, etc.)
            value: Identifier value

        Returns:
            Matching entity or None
        """
        # Try convenience field first
        field = scheme.lower()
        if field in ("cik", "lei", "ticker"):
            body = {
                "query": {"term": {field: value}},
                "size": 1,
            }
        else:
            # Use nested query for other identifiers
            body = {
                "query": {
                    "nested": {
                        "path": "identifiers",
                        "query": {
                            "bool": {
                                "must": [
                                    {"term": {"identifiers.scheme": scheme}},
                                    {"term": {"identifiers.value": value}},
                                ],
                            },
                        },
                    },
                },
                "size": 1,
            }

        response = await self.client.search(index=self.index_name, body=body)

        if response["hits"]["hits"]:
            hit = response["hits"]["hits"][0]
            source = hit["_source"]
            return SearchResult(
                entity_id=source["entity_id"],
                primary_name=source["primary_name"],
                entity_type=source.get("entity_type", "unknown"),
                score=hit["_score"],
                source=source,
            )
        return None

    # =========================================================================
    # Sync from PostgreSQL
    # =========================================================================

    async def sync_from_postgres(self, pg_store: Any, batch_size: int = 1000) -> dict:
        """
        Sync entities from PostgreSQL to Elasticsearch.

        Args:
            pg_store: PostgreSQL store instance
            batch_size: Number of entities per batch

        Returns:
            Sync statistics
        """
        logger.info("Starting sync from PostgreSQL to Elasticsearch")
        total_synced = 0
        total_failed = 0

        # This would iterate through PostgreSQL entities
        # Implementation depends on pg_store interface
        # For now, return placeholder
        return {
            "synced": total_synced,
            "failed": total_failed,
            "timestamp": datetime.utcnow().isoformat(),
        }

    # =========================================================================
    # Stats
    # =========================================================================

    async def count(self) -> int:
        """Get total document count."""
        response = await self.client.count(index=self.index_name)
        return response["count"]

    async def stats(self) -> dict:
        """Get index statistics."""
        stats = await self.client.indices.stats(index=self.index_name)
        return {
            "docs_count": stats["indices"][self.index_name]["total"]["docs"]["count"],
            "size_bytes": stats["indices"][self.index_name]["total"]["store"]["size_in_bytes"],
        }
