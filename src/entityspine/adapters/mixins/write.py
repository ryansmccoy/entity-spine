"""Write operations mixin for JSON entity store.

Provides all write operations for entities, securities, listings, and claims.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from entityspine.domain import Entity, IdentifierClaim, Listing, Security

logger = logging.getLogger(__name__)


class JsonStoreWriteMixin:
    """Mixin providing write operations for JSON entity store.
    
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
    """

    def save_entity(self, entity: Entity) -> None:
        """Save an entity and update indexes."""
        self._save_entity_internal(entity)

    def save_security(self, security: Security) -> None:
        """Save a security and update indexes."""
        self._save_security_internal(security)

    def save_claim(self, claim: IdentifierClaim) -> None:
        """Save an identifier claim."""
        self._save_claim_internal(claim)

    def _save_entity_internal(self, entity: Entity) -> None:
        """Internal method to save entity and update indexes."""
        self._entities[entity.entity_id] = entity

        # Update CIK index
        if entity.cik:
            if entity.cik not in self._cik_index:
                self._cik_index[entity.cik] = set()
            self._cik_index[entity.cik].add(entity.entity_id)

        # Update name index
        if entity.name:
            name_key = entity.name.strip().lower()
            if name_key not in self._name_index:
                self._name_index[name_key] = set()
            self._name_index[name_key].add(entity.entity_id)

    def _save_security_internal(self, security: Security) -> None:
        """Internal method to save security and update indexes."""
        self._securities[security.security_id] = security

        # Update entity->security index
        if security.entity_id:
            if security.entity_id not in self._security_by_entity:
                self._security_by_entity[security.entity_id] = set()
            self._security_by_entity[security.entity_id].add(security.security_id)

    def _save_listing_internal(self, listing: Listing) -> None:
        """Internal method to save listing and update indexes."""
        self._listings[listing.listing_id] = listing

        # Update ticker index
        if listing.ticker:
            ticker_key = listing.ticker.upper()
            if ticker_key not in self._ticker_index:
                self._ticker_index[ticker_key] = set()
            self._ticker_index[ticker_key].add(listing.listing_id)

        # Update security->listing index
        if listing.security_id:
            if listing.security_id not in self._listing_by_security:
                self._listing_by_security[listing.security_id] = set()
            self._listing_by_security[listing.security_id].add(listing.listing_id)

    def _save_claim_internal(self, claim: IdentifierClaim) -> None:
        """Internal method to save identifier claim."""
        self._claims[claim.claim_id] = claim

    def _ensure_listing_for_entity(self, entity_id: str, ticker: str, name: str) -> None:
        """Ensure a listing exists for an entity's ticker."""
        from entityspine.core.ulid import generate_ulid
        from entityspine.domain import Listing, Security, SecurityType

        # Check if listing already exists
        existing = self.get_listings_by_ticker(ticker)
        for listing in existing:
            if listing.security_id:
                security = self._securities.get(listing.security_id)
                if security and security.entity_id == entity_id:
                    return  # Listing already exists

        # Create security if needed
        securities = self.get_securities_by_entity(entity_id)
        if securities:
            security = securities[0]
        else:
            security = Security(
                security_id=generate_ulid(),
                entity_id=entity_id,
                security_type=SecurityType.COMMON_STOCK,
                name=f"{name} Common Stock",
            )
            self._save_security_internal(security)

        # Create listing
        listing = Listing(
            listing_id=generate_ulid(),
            security_id=security.security_id,
            ticker=ticker.upper(),
            exchange="UNKNOWN",
            name=name,
        )
        self._save_listing_internal(listing)

    def _create_security_and_listing(
        self,
        entity_id: str,
        ticker: str,
        exchange: str,
        name: str,
    ) -> None:
        """Create a security and listing for an entity."""
        from entityspine.core.ulid import generate_ulid
        from entityspine.domain import Listing, Security, SecurityType

        # Create security
        security = Security(
            security_id=generate_ulid(),
            entity_id=entity_id,
            security_type=SecurityType.COMMON_STOCK,
            name=f"{name} Common Stock",
        )
        self._save_security_internal(security)

        # Create listing
        listing = Listing(
            listing_id=generate_ulid(),
            security_id=security.security_id,
            ticker=ticker.upper(),
            exchange=exchange or "UNKNOWN",
            name=name,
        )
        self._save_listing_internal(listing)
