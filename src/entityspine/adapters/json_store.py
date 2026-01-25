"""
JSON Store - Tier 0 storage backend for EntitySpine (REFACTORED).

This is a refactored version of JsonEntityStore using the mixin pattern.
Reduced from 740 lines to ~90 lines by extracting into focused mixins.

Mixins:
- JsonStoreQueryMixin: All read operations (~150 lines)
- JsonStoreWriteMixin: All write operations (~140 lines)
- JsonStoreLifecycleMixin: Init/persistence (~170 lines)

Original: 740 lines in one file
Refactored: 90 lines + 460 lines in mixins = 550 total (26% reduction)

v2.2.3 ARCHITECTURE:
- Uses DOMAIN dataclasses internally (entityspine.domain.*)
- Returns domain dataclasses from all public methods
- Pydantic models are NOT used here (zero-deps for Tier 0)
"""

import logging
from pathlib import Path

from entityspine.adapters.mixins import (
    JsonStoreLifecycleMixin,
    JsonStoreQueryMixin,
    JsonStoreWriteMixin,
)
from entityspine.domain import Entity, IdentifierClaim, Listing, Security

logger = logging.getLogger(__name__)


class JsonEntityStoreRefactored(JsonStoreQueryMixin, JsonStoreWriteMixin, JsonStoreLifecycleMixin):
    """
    Tier 0 JSON-based entity store (refactored with mixins).

    Stores entities in memory with optional JSON file persistence.
    Implements EntityStoreProtocol and StorageLifecycleProtocol.

    Limitations (TIER CAPABILITY HONESTY):
    - as_of parameter IGNORED (no temporal data)
    - Exact match search only
    - Max recommended entities: 50,000

    Attributes:
        tier: Storage tier (always 0).
        tier_name: Human-readable tier name.
        supports_temporal: Whether temporal queries work (always False).

    Example:
        >>> store = JsonEntityStoreRefactored()
        >>> store.initialize()
        >>> store.load_sec_json(data)
        >>> entities = store.get_entities_by_cik("320193")
    """

    tier: int = 0
    tier_name: str = "JSON"
    supports_temporal: bool = False

    def __init__(self, json_path: Path | None = None):
        """
        Initialize JSON store with mixins.

        Args:
            json_path: Optional path to JSON file for persistence.
        """
        self.json_path = json_path

        # In-memory storage
        self._entities: dict[str, Entity] = {}
        self._securities: dict[str, Security] = {}
        self._listings: dict[str, Listing] = {}
        self._claims: dict[str, IdentifierClaim] = {}

        # Indexes
        self._cik_index: dict[str, set[str]] = {}
        self._ticker_index: dict[str, set[str]] = {}
        self._name_index: dict[str, set[str]] = {}
        self._security_by_entity: dict[str, set[str]] = {}
        self._listing_by_security: dict[str, set[str]] = {}

        self._initialized = False

    def _follow_redirects(self, entity: Entity, max_depth: int = 10) -> Entity:
        """Follow redirect chain to get canonical entity."""
        seen = {entity.entity_id}
        current = entity

        for _ in range(max_depth):
            if not current.redirect_to:
                return current

            if current.redirect_to in seen:
                logger.warning(f"Redirect cycle: {entity.entity_id} -> {current.redirect_to}")
                return current

            target = self._entities.get(current.redirect_to)
            if not target:
                logger.warning(f"Broken redirect: {current.entity_id} -> {current.redirect_to}")
                return current

            seen.add(current.redirect_to)
            current = target

        logger.warning(f"Max redirect depth for {entity.entity_id}")
        return current
