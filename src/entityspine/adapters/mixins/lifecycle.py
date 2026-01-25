"""Lifecycle and persistence mixin for JSON entity store.

Handles initialization, file I/O, and cleanup operations.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from entityspine.domain import Entity, IdentifierClaim, Listing, Security

logger = logging.getLogger(__name__)


class JsonStoreLifecycleMixin:
    """Mixin providing lifecycle and persistence for JSON entity store.
    
    Requires:
        - self.json_path: Path | None
        - self._entities: dict[str, Entity]
        - self._securities: dict[str, Security]
        - self._listings: dict[str, Listing]
        - self._claims: dict[str, IdentifierClaim]
        - self._cik_index: dict[str, set[str]]
        - self._ticker_index: dict[str, set[str]]
        - self._name_index: dict[str, set[str]]
        - self._security_by_entity: dict[str, set[str]]
        - self._listing_by_security: dict[str, set[str]]
        - self._save_entity_internal, _save_security_internal, etc. methods
    """

    def initialize(self) -> None:
        """Initialize store and load from file if path provided."""
        if self.json_path and Path(self.json_path).exists():
            self._load_from_file()
        self._initialized = True
        logger.info(f"JsonEntityStore initialized ({self.entity_count()} entities)")

    def close(self) -> None:
        """Save to file if path provided and clear memory."""
        if self.json_path:
            self._save_to_file()

        self._entities.clear()
        self._securities.clear()
        self._listings.clear()
        self._claims.clear()
        self._cik_index.clear()
        self._ticker_index.clear()
        self._name_index.clear()
        self._security_by_entity.clear()
        self._listing_by_security.clear()

        self._initialized = False
        logger.info("JsonEntityStore closed")

    def _load_from_file(self) -> None:
        """Load entities from JSON file."""
        from entityspine.domain import Entity, IdentifierClaim, Listing, Security

        if not self.json_path:
            return

        path = Path(self.json_path)
        if not path.exists():
            logger.warning(f"JSON file not found: {path}")
            return

        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)

            # Load entities
            for entity_dict in data.get("entities", []):
                entity = Entity(**entity_dict)
                self._save_entity_internal(entity)

            # Load securities
            for security_dict in data.get("securities", []):
                security = Security(**security_dict)
                self._save_security_internal(security)

            # Load listings
            for listing_dict in data.get("listings", []):
                listing = Listing(**listing_dict)
                self._save_listing_internal(listing)

            # Load claims
            for claim_dict in data.get("claims", []):
                claim = IdentifierClaim(**claim_dict)
                self._save_claim_internal(claim)

            logger.info(f"Loaded {len(self._entities)} entities from {path}")

        except Exception as e:
            logger.error(f"Failed to load from {path}: {e}")
            raise

    def _save_to_file(self) -> None:
        """Save entities to JSON file."""
        if not self.json_path:
            return

        path = Path(self.json_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        try:
            data = {
                "entities": [e.__dict__ for e in self._entities.values()],
                "securities": [s.__dict__ for s in self._securities.values()],
                "listings": [l.__dict__ for l in self._listings.values()],
                "claims": [c.__dict__ for c in self._claims.values()],
            }

            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)

            logger.info(f"Saved {len(self._entities)} entities to {path}")

        except Exception as e:
            logger.error(f"Failed to save to {path}: {e}")
            raise

    def load_sec_json(self, data: dict) -> int:
        """Load entities from SEC company tickers JSON format.
        
        Args:
            data: Dictionary with structure {cik: {ticker, title, exchange}}
            
        Returns:
            Number of entities loaded.
        """
        from entityspine.core.ulid import generate_ulid
        from entityspine.domain import Entity, EntityStatus, EntityType

        count = 0

        for cik_raw, company_data in data.items():
            # Normalize CIK (remove leading zeros, then pad to 10 digits)
            cik = cik_raw.lstrip("0").zfill(10)

            # Extract fields
            ticker = company_data.get("ticker", "").upper()
            name = company_data.get("title", "")
            exchange = company_data.get("exchange", "UNKNOWN")

            if not name:
                logger.warning(f"Skipping CIK {cik} - missing name")
                continue

            # Create entity
            entity = Entity(
                entity_id=generate_ulid(),
                entity_type=EntityType.COMPANY,
                status=EntityStatus.ACTIVE,
                name=name,
                cik=cik,
            )
            self._save_entity_internal(entity)

            # Create security and listing if ticker exists
            if ticker:
                self._create_security_and_listing(
                    entity_id=entity.entity_id,
                    ticker=ticker,
                    exchange=exchange,
                    name=name,
                )

            count += 1

        logger.info(f"Loaded {count} entities from SEC JSON")
        return count
