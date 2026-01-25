"""Query operations mixin for JSON entity store.

Provides all read operations for entities, securities, listings, and claims.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from entityspine.domain import Entity, IdentifierClaim, Listing, Security

logger = logging.getLogger(__name__)


class JsonStoreQueryMixin:
    """Mixin providing query operations for JSON entity store.
    
    Requires:
        - self._entities: dict[str, Entity]
        - self._securities: dict[str, Security]
        - self._listings: dict[str, Listing]
        - self._claims: dict[str, IdentifierClaim]
        - self._cik_index: dict[str, set[str]]
        - self._ticker_index: dict[str, set[str]]
        - self._name_index: dict[str, set[str]]
        - self._security_by_entity: dict[str, set[str]]
        - self._listing_by_security: dict[str, set[str]]
        - self._follow_redirects(entity, max_depth) method
    """

    def get_entity(self, entity_id: str) -> Entity | None:
        """Get entity by ID, following redirects."""
        entity = self._entities.get(entity_id)
        if entity and entity.redirect_to:
            return self._follow_redirects(entity)
        return entity

    def get_entity_raw(self, entity_id: str) -> Entity | None:
        """Get entity by ID WITHOUT following redirects."""
        return self._entities.get(entity_id)

    def get_entities_by_cik(self, cik: str) -> list[Entity]:
        """Get all entities with matching CIK."""
        entity_ids = self._cik_index.get(cik, set())
        entities = []
        for eid in entity_ids:
            entity = self.get_entity(eid)
            if entity:
                entities.append(entity)
        return entities

    def get_entities_by_ticker(self, ticker: str) -> list[Entity]:
        """Get entities by ticker symbol."""
        listing_ids = self._ticker_index.get(ticker.upper(), set())
        entity_ids = set()

        for lid in listing_ids:
            listing = self._listings.get(lid)
            if listing and listing.security_id:
                security = self._securities.get(listing.security_id)
                if security and security.entity_id:
                    entity_ids.add(security.entity_id)

        entities = []
        for eid in entity_ids:
            entity = self.get_entity(eid)
            if entity:
                entities.append(entity)
        return entities

    def get_security(self, security_id: str) -> Security | None:
        """Get security by ID."""
        return self._securities.get(security_id)

    def get_securities_by_entity(self, entity_id: str) -> list[Security]:
        """Get all securities for an entity."""
        security_ids = self._security_by_entity.get(entity_id, set())
        return [self._securities[sid] for sid in security_ids if sid in self._securities]

    def get_listings_by_ticker(
        self,
        ticker: str,
        *,
        exchange: str | None = None,
    ) -> list[Listing]:
        """Get listings by ticker symbol."""
        listing_ids = self._ticker_index.get(ticker.upper(), set())
        listings = []

        for lid in listing_ids:
            listing = self._listings.get(lid)
            if listing:
                if exchange is None or listing.exchange == exchange:
                    listings.append(listing)

        return listings

    def get_listings_by_security(self, security_id: str) -> list[Listing]:
        """Get all listings for a security."""
        listing_ids = self._listing_by_security.get(security_id, set())
        return [self._listings[lid] for lid in listing_ids if lid in self._listings]

    def get_claims(self, scheme: str, value: str) -> list[IdentifierClaim]:
        """Get identifier claims by scheme and value."""
        claims = []
        for claim in self._claims.values():
            if claim.scheme == scheme and claim.value == value:
                claims.append(claim)
        return claims

    def search_entities(
        self,
        query: str,
        *,
        limit: int = 100,
        entity_type: str | None = None,
    ) -> list[Entity]:
        """Search entities by name or identifier (exact match only)."""
        from entityspine.core.identifier import looks_like_cik, looks_like_ticker

        query_lower = query.strip().lower()
        results: list[Entity] = []

        # Try CIK lookup
        if looks_like_cik(query):
            cik_normalized = query.lstrip("0").zfill(10)
            results.extend(self.get_entities_by_cik(cik_normalized))

        # Try ticker lookup
        elif looks_like_ticker(query):
            results.extend(self.get_entities_by_ticker(query))

        # Try name lookup
        else:
            entity_ids = self._name_index.get(query_lower, set())
            for eid in entity_ids:
                entity = self.get_entity(eid)
                if entity:
                    results.append(entity)

        # Apply entity_type filter
        if entity_type:
            results = [e for e in results if e.entity_type == entity_type]

        return results[:limit]

    def entity_count(self) -> int:
        """Count total entities."""
        return len(self._entities)

    def listing_count(self) -> int:
        """Count total listings."""
        return len(self._listings)
