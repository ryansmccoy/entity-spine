"""
JSON Store - Tier 0 storage backend for EntitySpine.

Tier 0 Characteristics:
- Simple in-memory storage with JSON file persistence
- No temporal/historical data (as_of will be IGNORED)
- Exact match search only
- Supports full Entity/Security/Listing hierarchy
- Fast startup, low memory for <50K entities

TIER CAPABILITY HONESTY:
When as_of is provided, the store MUST:
1. Return current entity (best effort)
2. The resolver adds warning: "as_of_ignored: Tier 0 store lacks temporal data"

v2.2.3 ARCHITECTURE:
- Uses DOMAIN dataclasses internally (entityspine.domain.*)
- Returns domain dataclasses from all public methods
- Pydantic models are NOT used here (zero-deps for Tier 0)
"""

import json
import logging
from datetime import date
from pathlib import Path

from entityspine.core.identifier import looks_like_cik, looks_like_ticker
from entityspine.core.ulid import generate_ulid

# v2.2.3: Use DOMAIN dataclasses (stdlib-only, zero deps)
from entityspine.domain import (
    Entity,
    EntityStatus,
    EntityType,
    IdentifierClaim,
    IdentifierScheme,
    Listing,
    Security,
    SecurityType,
    VendorNamespace,
)

logger = logging.getLogger(__name__)


class JsonEntityStore:
    """
    Tier 0 JSON-based entity store.

    Stores entities in memory with optional JSON file persistence.
    Implements EntityStoreProtocol and StorageLifecycleProtocol.

    v2.2.3: Returns DOMAIN dataclasses (not Pydantic models).

    Limitations (TIER CAPABILITY HONESTY):
    - as_of parameter IGNORED (no temporal data)
    - Exact match search only
    - Max recommended entities: 50,000

    Attributes:
        tier: Storage tier (always 0).
        tier_name: Human-readable tier name.
        supports_temporal: Whether temporal queries work (always False).

    Example:
        >>> store = JsonEntityStore()
        >>> store.initialize()
        >>> store.load_sec_json(data)
        >>> entities = store.get_entities_by_cik("320193")
    """

    tier: int = 0
    tier_name: str = "JSON"
    supports_temporal: bool = False

    def __init__(self, json_path: Path | None = None):
        """
        Initialize JSON store.

        Args:
            json_path: Optional path to JSON file for persistence.
                      If None, data is only stored in memory.
        """
        self.json_path = json_path

        # In-memory storage
        self._entities: dict[str, Entity] = {}  # entity_id -> Entity
        self._securities: dict[str, Security] = {}  # security_id -> Security
        self._listings: dict[str, Listing] = {}  # listing_id -> Listing
        self._claims: dict[str, IdentifierClaim] = {}  # claim_id -> Claim

        # Indexes
        self._cik_index: dict[str, set[str]] = {}  # cik -> {entity_id, ...}
        self._ticker_index: dict[str, set[str]] = {}  # ticker -> {listing_id, ...}
        self._name_index: dict[str, set[str]] = {}  # lowercase_name -> {entity_id, ...}
        self._security_by_entity: dict[str, set[str]] = {}  # entity_id -> {security_id, ...}
        self._listing_by_security: dict[str, set[str]] = {}  # security_id -> {listing_id, ...}

        self._initialized = False

    # =========================================================================
    # StorageLifecycleProtocol
    # =========================================================================

    def initialize(self) -> None:
        """
        Initialize storage.

        Loads data from JSON file if path was provided and file exists.
        Idempotent: safe to call multiple times.
        """
        if self._initialized:
            return

        if self.json_path and self.json_path.exists():
            self._load_from_file()

        self._initialized = True
        logger.info(f"JsonEntityStore initialized with {len(self._entities)} entities")

    def close(self) -> None:
        """
        Close storage and optionally persist to file.
        """
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

    def load_sec_json(self, data: dict) -> int:
        """
        Load entities from SEC company_tickers.json format.

        Creates Entity, Security, Listing, and Claim records from SEC data.

        Args:
            data: Dict in SEC JSON format:
                {"0": {"cik_str": "320193", "ticker": "AAPL", "title": "Apple Inc."}}
                OR list format:
                [{"cik_str": "320193", "ticker": "AAPL", "title": "Apple Inc."}]

        Returns:
            Number of entities loaded.
        """
        count = 0

        # Handle both dict and list formats
        items = data.values() if isinstance(data, dict) else data

        for item in items:
            try:
                # Extract fields from SEC format
                cik_str = item.get("cik_str") or item.get("cik")
                cik = str(cik_str).strip() if cik_str else None
                ticker = item.get("ticker", "").strip() or None
                name = item.get("title") or item.get("name", "Unknown")

                if not cik:
                    continue

                # Normalize CIK (zero-pad to 10 digits)
                cik_normalized = cik.zfill(10)

                # Check if entity with this CIK already exists
                existing_ids = self._cik_index.get(cik_normalized, set())
                if existing_ids:
                    # Entity exists, maybe add listing
                    entity_id = next(iter(existing_ids))
                    if ticker:
                        self._ensure_listing_for_entity(entity_id, ticker, name)
                    continue

                # Create new entity (v2.2.3: NO identifier fields on Entity)
                entity_id = generate_ulid()
                entity = Entity(
                    entity_id=entity_id,
                    primary_name=name.strip(),
                    entity_type=EntityType.ORGANIZATION,
                    status=EntityStatus.ACTIVE,
                    source_system="sec",
                    source_id=cik_normalized,
                )

                self._save_entity_internal(entity)

                # Create CIK claim (v2.2.3: IdentifierClaim is canonical)
                claim = IdentifierClaim(
                    claim_id=generate_ulid(),
                    entity_id=entity_id,
                    scheme=IdentifierScheme.CIK,
                    value=cik_normalized,
                    namespace=VendorNamespace.SEC,
                    source="sec_json",
                )
                self._save_claim_internal(claim)

                # Create security and listing if ticker present
                if ticker:
                    self._create_security_and_listing(entity_id, name, ticker)

                count += 1

            except Exception as e:
                logger.warning(f"Error loading entity: {e}")
                continue

        logger.info(f"Loaded {count} entities from SEC JSON")
        return count

    def load_sec_data(self, url: str | None = None) -> int:
        """
        Download and load SEC company data directly from the SEC website.

        This is a convenience method that fetches company_tickers.json from the SEC
        and loads it into the store. Uses only stdlib (urllib) - no external dependencies.

        Args:
            url: Optional URL to fetch data from. Defaults to SEC's company_tickers.json

        Returns:
            Number of entities loaded.

        Raises:
            urllib.error.URLError: If download fails
            json.JSONDecodeError: If response is not valid JSON

        Example:
            >>> store = JsonEntityStore()
            >>> store.initialize()
            >>> count = store.load_sec_data()  # Downloads ~14,000 companies
            >>> print(f"Loaded {count} companies")
        """
        import gzip
        import json
        import urllib.request

        SEC_COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
        target_url = url or SEC_COMPANY_TICKERS_URL

        # SEC requires a proper User-Agent header with contact info
        headers = {
            "User-Agent": "EntitySpine/0.3.3 (entityspine@example.com)",
            "Accept-Encoding": "gzip, deflate",
            "Host": "www.sec.gov",
        }

        logger.info(f"Downloading SEC data from {target_url}")
        request = urllib.request.Request(target_url, headers=headers)

        with urllib.request.urlopen(request, timeout=30) as response:
            raw_data = response.read()
            # Handle gzip compression
            if response.headers.get("Content-Encoding") == "gzip" or raw_data[:2] == b"\x1f\x8b":
                raw_data = gzip.decompress(raw_data)
            data = json.loads(raw_data.decode("utf-8"))

        return self.load_sec_json(data)

    def _create_security_and_listing(
        self, entity_id: str, name: str, ticker: str
    ) -> tuple[str, str]:
        """Create Security and Listing records for an entity."""
        ticker_normalized = ticker.upper().replace("-", ".")

        # Create security (v2.2.3: use domain dataclass)
        security_id = generate_ulid()
        security = Security(
            security_id=security_id,
            entity_id=entity_id,
            security_type=SecurityType.COMMON_STOCK,
            description=f"{name} Common Stock",
            source_system="sec",
        )
        self._save_security_internal(security)

        # Create listing (TICKER LIVES HERE!)
        listing_id = generate_ulid()
        listing = Listing(
            listing_id=listing_id,
            security_id=security_id,
            ticker=ticker_normalized,
            exchange="UNKNOWN",  # SEC data doesn't include exchange
            is_primary=True,
            source_system="sec",
        )
        self._save_listing_internal(listing)

        # Create ticker claim on LISTING (v2.2.3: TICKER→listing scope)
        claim = IdentifierClaim(
            claim_id=generate_ulid(),
            listing_id=listing_id,  # Ticker claim on listing, not entity
            scheme=IdentifierScheme.TICKER,
            value=ticker_normalized,
            namespace=VendorNamespace.SEC,
            source="sec_json",
        )
        self._save_claim_internal(claim)

        return security_id, listing_id

    def _ensure_listing_for_entity(self, entity_id: str, ticker: str, name: str) -> None:
        """Ensure a listing exists for an entity/ticker combination."""
        ticker_normalized = ticker.upper().replace("-", ".")

        # Check if listing already exists
        existing_listings = self._ticker_index.get(ticker_normalized, set())
        for listing_id in existing_listings:
            listing = self._listings.get(listing_id)
            if listing:
                security = self._securities.get(listing.security_id)
                if security and security.entity_id == entity_id:
                    return  # Listing exists

        # Create new security and listing
        self._create_security_and_listing(entity_id, name, ticker)

    # =========================================================================
    # EntityStoreProtocol - Entity Operations
    # =========================================================================

    def get_entity(self, entity_id: str) -> Entity | None:
        """
        Get entity by ID, following redirects.

        Args:
            entity_id: Entity ULID.

        Returns:
            Entity (canonical, after following redirects) or None.
        """
        entity = self._entities.get(entity_id)
        if not entity:
            return None

        # Follow redirect chain (max 10 to prevent infinite loops)
        return self._follow_redirects(entity)

    def get_entity_raw(self, entity_id: str) -> Entity | None:
        """
        Get entity by ID WITHOUT following redirects.

        Args:
            entity_id: Entity ULID.

        Returns:
            Entity exactly as stored.
        """
        return self._entities.get(entity_id)

    def get_entities_by_cik(self, cik: str) -> list[Entity]:
        """
        Get entities matching CIK.

        Args:
            cik: SEC Central Index Key (with or without padding).

        Returns:
            List of matching entities.
        """
        # Normalize CIK
        cik_normalized = cik.strip().zfill(10)

        entity_ids = self._cik_index.get(cik_normalized, set())
        entities = []

        for entity_id in entity_ids:
            entity = self.get_entity(entity_id)  # Follow redirects
            if entity and entity not in entities:
                entities.append(entity)

        return entities

    def get_entities_by_ticker(self, ticker: str) -> list[Entity]:
        """
        Get entities matching ticker (via Listing lookup).

        Args:
            ticker: Stock ticker symbol.

        Returns:
            List of matching entities.
        """
        ticker_normalized = ticker.upper().strip().replace("-", ".")
        listing_ids = self._ticker_index.get(ticker_normalized, set())

        entities = []
        seen_ids: set[str] = set()

        for listing_id in listing_ids:
            listing = self._listings.get(listing_id)
            if not listing:
                continue

            security = self._securities.get(listing.security_id)
            if not security:
                continue

            entity = self.get_entity(security.entity_id)
            if entity and entity.entity_id not in seen_ids:
                entities.append(entity)
                seen_ids.add(entity.entity_id)

        return entities

    def save_entity(self, entity: Entity) -> None:
        """
        Save or update entity.

        Args:
            entity: Entity (domain dataclass) to save.
        """
        # v2.2.3: Domain dataclasses are frozen, use with_update
        entity = entity.with_update()  # Updates updated_at timestamp
        self._save_entity_internal(entity)

    # =========================================================================
    # EntityStoreProtocol - Listing Operations
    # =========================================================================

    def get_listings_by_ticker(
        self,
        ticker: str,
        mic: str | None = None,
        as_of: date | None = None,
    ) -> list[Listing]:
        """
        Get listings matching ticker.

        NOTE: as_of is IGNORED (Tier 0 has no temporal data).
        The resolver will add a warning.

        Args:
            ticker: Stock ticker symbol.
            mic: Optional MIC filter.
            as_of: Optional date filter (IGNORED - Tier 0 limitation).

        Returns:
            List of matching Listing objects.
        """
        ticker_normalized = ticker.upper().strip().replace("-", ".")
        listing_ids = self._ticker_index.get(ticker_normalized, set())

        listings = []
        for listing_id in listing_ids:
            listing = self._listings.get(listing_id)
            if listing:
                if mic and listing.mic != mic:
                    continue
                listings.append(listing)

        return listings

    def get_listings_by_security(self, security_id: str) -> list[Listing]:
        """
        Get all listings for a security.

        Args:
            security_id: Security ULID.

        Returns:
            All listings for the security.
        """
        listing_ids = self._listing_by_security.get(security_id, set())
        return [self._listings[lid] for lid in listing_ids if lid in self._listings]

    # =========================================================================
    # EntityStoreProtocol - Claim Operations
    # =========================================================================

    def get_claims(self, scheme: str, value: str) -> list[IdentifierClaim]:
        """
        Get claims matching scheme and value.

        Args:
            scheme: Identifier scheme (cik, ticker, etc.).
            value: Identifier value.

        Returns:
            List of matching IdentifierClaim objects.
        """
        scheme_lower = scheme.lower()
        claims = []

        for claim in self._claims.values():
            claim_scheme = (
                claim.scheme.value
                if isinstance(claim.scheme, IdentifierScheme)
                else str(claim.scheme)
            )
            if claim_scheme == scheme_lower and claim.value == value:
                claims.append(claim)

        return claims

    def save_claim(self, claim: IdentifierClaim) -> None:
        """
        Save identifier claim.

        Args:
            claim: Claim to save.
        """
        self._save_claim_internal(claim)

    # =========================================================================
    # SecurityStoreProtocol
    # =========================================================================

    def get_security(self, security_id: str) -> Security | None:
        """Get security by ID."""
        return self._securities.get(security_id)

    def get_securities_by_entity(self, entity_id: str) -> list[Security]:
        """Get all securities issued by an entity."""
        security_ids = self._security_by_entity.get(entity_id, set())
        return [self._securities[sid] for sid in security_ids if sid in self._securities]

    def save_security(self, security: Security) -> None:
        """Save or update security."""
        # v2.2.3: Domain dataclasses are frozen, use with_update
        security = security.with_update()
        self._save_security_internal(security)

    # =========================================================================
    # EntityStoreProtocol - Statistics
    # =========================================================================

    def entity_count(self) -> int:
        """Get total number of entities."""
        return len(self._entities)

    def listing_count(self) -> int:
        """Get total number of listings."""
        return len(self._listings)

    # =========================================================================
    # Search (Tier 0: exact match only)
    # =========================================================================

    def search_entities(
        self,
        query: str,
        limit: int = 10,
    ) -> list[tuple[Entity, float]]:
        """
        Search entities by name (exact match only).

        Args:
            query: Search query.
            limit: Maximum results.

        Returns:
            List of (entity, similarity_score) tuples.
            Score is 1.0 for exact match, 0.0 otherwise.
        """
        query_lower = query.lower().strip()
        results = []

        # Check CIK first
        is_cik, cik_normalized = looks_like_cik(query)
        if is_cik:
            for entity in self.get_entities_by_cik(cik_normalized):
                results.append((entity, 1.0))
                if len(results) >= limit:
                    return results

        # Check ticker
        is_ticker, ticker_normalized = looks_like_ticker(query)
        if is_ticker:
            for entity in self.get_entities_by_ticker(ticker_normalized):
                if entity not in [r[0] for r in results]:
                    results.append((entity, 1.0))
                    if len(results) >= limit:
                        return results

        # Check name (exact match on lowercase)
        entity_ids = self._name_index.get(query_lower, set())
        for entity_id in entity_ids:
            entity = self.get_entity(entity_id)
            if entity and entity not in [r[0] for r in results]:
                results.append((entity, 1.0))
                if len(results) >= limit:
                    return results

        return results

    # =========================================================================
    # Internal Methods
    # =========================================================================

    def _save_entity_internal(self, entity: Entity) -> None:
        """Save entity and update indexes."""
        self._entities[entity.entity_id] = entity

        # Update CIK index
        if entity.cik:
            cik_normalized = entity.cik.zfill(10)
            if cik_normalized not in self._cik_index:
                self._cik_index[cik_normalized] = set()
            self._cik_index[cik_normalized].add(entity.entity_id)

        # Update name index
        name_lower = entity.primary_name.lower().strip()
        if name_lower not in self._name_index:
            self._name_index[name_lower] = set()
        self._name_index[name_lower].add(entity.entity_id)

    def _save_security_internal(self, security: Security) -> None:
        """Save security and update indexes."""
        self._securities[security.security_id] = security

        # Update entity -> security index
        if security.entity_id not in self._security_by_entity:
            self._security_by_entity[security.entity_id] = set()
        self._security_by_entity[security.entity_id].add(security.security_id)

    def _save_listing_internal(self, listing: Listing) -> None:
        """Save listing and update indexes."""
        self._listings[listing.listing_id] = listing

        # Update ticker index
        ticker_normalized = listing.ticker.upper().replace("-", ".")
        if ticker_normalized not in self._ticker_index:
            self._ticker_index[ticker_normalized] = set()
        self._ticker_index[ticker_normalized].add(listing.listing_id)

        # Update security -> listing index
        if listing.security_id not in self._listing_by_security:
            self._listing_by_security[listing.security_id] = set()
        self._listing_by_security[listing.security_id].add(listing.listing_id)

    def _save_claim_internal(self, claim: IdentifierClaim) -> None:
        """Save claim."""
        self._claims[claim.claim_id] = claim

    def _follow_redirects(self, entity: Entity, max_depth: int = 10) -> Entity:
        """
        Follow redirect chain to get canonical entity.

        Args:
            entity: Starting entity.
            max_depth: Maximum redirects to follow (cycle prevention).

        Returns:
            Canonical entity.
        """
        seen = {entity.entity_id}
        current = entity

        for _ in range(max_depth):
            if not current.redirect_to:
                return current

            if current.redirect_to in seen:
                # Cycle detected
                logger.warning(
                    f"Redirect cycle detected: {entity.entity_id} -> {current.redirect_to}"
                )
                return current

            target = self._entities.get(current.redirect_to)
            if not target:
                # Broken redirect
                logger.warning(f"Broken redirect: {current.entity_id} -> {current.redirect_to}")
                return current

            seen.add(current.redirect_to)
            current = target

        # Max depth reached
        logger.warning(f"Max redirect depth reached for {entity.entity_id}")
        return current

    def _load_from_file(self) -> None:
        """Load data from JSON file."""
        if not self.json_path or not self.json_path.exists():
            return

        try:
            with open(self.json_path, encoding="utf-8") as f:
                data = json.load(f)

            # Load entities
            for entity_data in data.get("entities", []):
                entity = Entity(
                    entity_id=entity_data["entity_id"],
                    primary_name=entity_data["primary_name"],
                    cik=entity_data.get("cik"),
                    identifiers=entity_data.get("identifiers", {}),
                    aliases=entity_data.get("aliases", []),
                    redirect_to=entity_data.get("redirect_to"),
                )
                self._save_entity_internal(entity)

            # Load securities
            for sec_data in data.get("securities", []):
                security = Security(
                    security_id=sec_data["security_id"],
                    entity_id=sec_data["entity_id"],
                    security_type=sec_data["security_type"],
                    description=sec_data.get("description"),
                )
                self._save_security_internal(security)

            # Load listings
            for listing_data in data.get("listings", []):
                listing = Listing(
                    listing_id=listing_data["listing_id"],
                    security_id=listing_data["security_id"],
                    ticker=listing_data["ticker"],
                    exchange=listing_data["exchange"],
                    is_primary=listing_data.get("is_primary", False),
                )
                self._save_listing_internal(listing)

            logger.info(f"Loaded {len(self._entities)} entities from {self.json_path}")

        except Exception as e:
            logger.error(f"Error loading from file: {e}")

    def _save_to_file(self) -> None:
        """Save data to JSON file."""
        if not self.json_path:
            return

        try:
            entities_data = []
            for entity in self._entities.values():
                entities_data.append(
                    {
                        "entity_id": entity.entity_id,
                        "primary_name": entity.primary_name,
                        "cik": entity.cik,
                        "identifiers": entity.identifiers,
                        "aliases": entity.aliases,
                        "redirect_to": entity.redirect_to,
                    }
                )

            securities_data = []
            for security in self._securities.values():
                securities_data.append(
                    {
                        "security_id": security.security_id,
                        "entity_id": security.entity_id,
                        "security_type": security.security_type,
                        "description": security.description,
                    }
                )

            listings_data = []
            for listing in self._listings.values():
                listings_data.append(
                    {
                        "listing_id": listing.listing_id,
                        "security_id": listing.security_id,
                        "ticker": listing.ticker,
                        "exchange": listing.exchange,
                        "is_primary": listing.is_primary,
                    }
                )

            data = {
                "version": "2.0",
                "tier": 0,
                "entities": entities_data,
                "securities": securities_data,
                "listings": listings_data,
            }

            # Ensure directory exists
            self.json_path.parent.mkdir(parents=True, exist_ok=True)

            with open(self.json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            logger.info(f"Saved {len(self._entities)} entities to {self.json_path}")

        except Exception as e:
            logger.error(f"Error saving to file: {e}")
