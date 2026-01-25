"""
SQLite store facade orchestrating repositories.

This is the main entry point for the refactored SqliteStore.
It maintains backward compatibility with the original 92-method API
while delegating to specialized repositories internally.

Tier 1 Characteristics:
- SQLite database using stdlib sqlite3 (ZERO external dependencies)
- Full Entity/Security/Listing hierarchy
- Identifier claims with validity tracking
- LIKE pattern search
- No temporal/historical data (as_of will be IGNORED)
"""

from __future__ import annotations

import gzip
import json
import logging
import urllib.request
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

from entityspine.core.timestamps import to_iso8601, utc_now
from entityspine.core.ulid import generate_ulid
from entityspine.domain import (
    Address,
    AddressType,
    Asset,
    Brand,
    Case,
    Contract,
    Entity,
    EntityCluster,
    EntityClusterMember,
    Event,
    EventType,
    Geo,
    IdentifierClaim,
    IdentifierScheme,
    Listing,
    Product,
    Relationship,
    RoleAssignment,
    Security,
)
from entityspine.domain.graph import EntityRelationship

from .connection import SqliteConnectionManager
from .repositories import (
    AddressRepository,
    AssetRepository,
    BrandRepository,
    CaseRepository,
    ClaimRepository,
    ClusterRepository,
    ContractRepository,
    EntityRepository,
    EventRepository,
    GeoRepository,
    ListingRepository,
    ProductRepository,
    RelationshipRepository,
    RoleRepository,
    SecurityRepository,
)
from .schema import SCHEMA_SQL

if TYPE_CHECKING:
    from entityspine.loaders.sec_loader import SecDataLoader

logger = logging.getLogger(__name__)


class SqliteStore:
    """
    Tier 1 SQLite-based entity store (Facade Pattern).
    
    SqliteStore is the recommended storage backend for production EntitySpine
    deployments up to ~500K entities. It provides indexed queries, LIKE pattern
    search, and proper relational integrity while maintaining ZERO external
    dependencies (stdlib sqlite3 only).
    
    Manifesto:
        EntitySpine's tiered storage architecture (Principle #5) provides SQLite
        as the T1 backend: more capable than T0 (JSON) but still zero-dependency.
        This is the sweet spot for most use cases:
        - Indexed lookups by CIK, ticker, entity_id
        - LIKE pattern search for partial name matching
        - Proper foreign key constraints
        - Concurrent read access
        - Scales to ~500K entities with good performance
        
        The Facade Pattern orchestrates specialized repositories (EntityRepository,
        SecurityRepository, etc.) for clean separation of concerns while presenting
        a unified 92+ method API for backward compatibility.
        
        **TIER CAPABILITY HONESTY**: Like T0, SQLite does NOT support true temporal
        queries (as_of returns current data with warning). For temporal queries,
        use T2 (DuckDB) or T3 (PostgreSQL with temporal tables).
    
    Architecture:
        ```
        ┌──────────────────────────────────────────────────────────┐
        │                  SqliteStore (Tier 1)                     │
        │                   Facade Pattern                          │
        └──────────────────────────────────────────────────────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    │              │              │
                    ▼              ▼              ▼
        ┌───────────────┐ ┌───────────────┐ ┌───────────────┐
        │EntityRepository│ │SecurityRepo   │ │ListingRepo    │
        │ - save()      │ │ - save()      │ │ - save()      │
        │ - get()       │ │ - get()       │ │ - get()       │
        │ - search()    │ │ - by_entity() │ │ - by_ticker() │
        └───────────────┘ └───────────────┘ └───────────────┘
                │              │              │
                └──────────────┼──────────────┘
                               │
                               ▼
                ┌─────────────────────────────┐
                │   SqliteConnectionManager   │
                │   - connection pool         │
                │   - thread safety           │
                └─────────────────────────────┘
                               │
                               ▼
                ┌─────────────────────────────┐
                │        SQLite DB            │
                │   entities.db               │
                │   - entities table          │
                │   - securities table        │
                │   - listings table          │
                │   - identifier_claims table │
                │   - relationships table     │
                │   - ... (20+ tables)        │
                └─────────────────────────────┘
        
        Repository Structure:
        stores/sqlite/
        ├── __init__.py
        ├── connection.py      # SqliteConnectionManager
        ├── schema.py          # SCHEMA_SQL DDL
        ├── converters.py      # row_to_entity(), etc.
        ├── storage.py         # SqliteStore (this class)
        └── repositories/
            ├── entity.py      # EntityRepository
            ├── security.py    # SecurityRepository
            ├── listing.py     # ListingRepository
            ├── claim.py       # ClaimRepository
            └── ... (10+ repos)
        ```
        Dependencies: None - stdlib sqlite3 only
        Storage Tier: T1 (SQLite)
    
    Features:
        - Zero external dependencies (stdlib sqlite3)
        - Repository pattern for clean separation of concerns
        - Facade pattern for unified API
        - Full Entity → Security → Listing hierarchy
        - 20+ domain tables with proper foreign keys
        - Indexed lookups (CIK, ticker, entity_id, etc.)
        - LIKE pattern search for names
        - SEC data auto-loader (downloads + caches)
        - Thread-safe read access
        - Returns DOMAIN dataclasses (not ORM models)
    
    Limitations (Tier 1 Honesty):
        - as_of parameter IGNORED (no temporal data)
        - LIKE-based search (not full-text search)
        - Single-writer (SQLite limitation)
        - Max recommended: 500,000 entities
    
    Examples:
        >>> # Basic usage
        >>> store = SqliteStore("entities.db")
        >>> store.initialize()
        >>> store.load_sec_data()  # Downloads and loads SEC data
        
        >>> # With auto-loading
        >>> store = SqliteStore("entities.db", auto_load_sec=True)
        >>> store.initialize()
        >>> entities = store.search("APPLE")  # Auto-loads SEC data first
        
        >>> # In-memory database (for testing)
        >>> store = SqliteStore(":memory:")
        >>> store.initialize()
        
        >>> # Lookup by CIK
        >>> entities = store.get_entities_by_cik("0000320193")
        >>> print(entities[0].primary_name)
        Apple Inc.
        
        >>> # Lookup by ticker
        >>> listings = store.get_listings_by_ticker("AAPL")
        >>> for listing in listings:
        ...     print(f"{listing.mic}:{listing.ticker}")
        
        >>> # Save new entity
        >>> entity = Entity(primary_name="Test Corp")
        >>> store.save_entity(entity)
        
        >>> # Get entity with related securities
        >>> entity = store.get_entity(entity_id)
        >>> securities = store.get_securities_by_entity(entity_id)
    
    Performance:
        - Initialization: O(1), ~50ms (schema creation)
        - CIK lookup: O(log n), ~1ms with index
        - Ticker lookup: O(log n), ~1ms with index
        - Name search (LIKE): O(n), ~10ms for 14K entities
        - Load SEC JSON: O(n), ~5 seconds for 14K companies
        - Memory: ~20MB for 14K companies (SQLite handles paging)
        - File size: ~100MB for 500K entities
    
    Guardrails:
        - Do NOT use SqliteStore for >500K entities
          ✅ Instead: Use DuckDB (T2) or PostgreSQL (T3)
        - Do NOT expect as_of queries to work
          ✅ Instead: Use T2/T3 for temporal queries
        - Do NOT use for concurrent writes
          ✅ Instead: SQLite is single-writer; use connection pooling
        - Do NOT import from old path
          ✅ Instead: from entityspine.stores.sqlite import SqliteStore
    
    Context:
        Problem: JsonEntityStore lacks indexing and scales poorly beyond 50K
                 entities; full SQL databases require external dependencies.
        Solution: SqliteStore uses stdlib sqlite3 for indexed queries and
                  proper relational storage with zero external dependencies.
    
    Tags:
        - storage_backend
        - tier_1
        - sqlite
        - repository_pattern
        - facade_pattern
        - stdlib_only
    
    Doc-Types:
        - MANIFESTO (section: "Tiered Storage", priority: 9)
        - FEATURES (section: "Storage Backends", priority: 9)
        - API_REFERENCE (section: "Stores", priority: 9)
    """

    tier: int = 1
    tier_name: str = "SQLite (stdlib)"
    supports_temporal: bool = False

    def __init__(
        self,
        db_path: str | Path = ":memory:",
        *,
        auto_load_sec: bool = False,
        cache_dir: str | Path | None = None,
    ):
        """
        Initialize SQLite store.
        
        Args:
            db_path: Path to SQLite database file.
                    Use ":memory:" for in-memory database.
            auto_load_sec: If True, automatically load SEC data on first query.
                          Data is cached locally to avoid repeated downloads.
            cache_dir: Directory for cached SEC data. Defaults to ~/.entityspine/cache.
        
        Example:
            >>> # Basic usage
            >>> store = SqliteStore("entities.db")
            >>> store.initialize()
            >>> store.load_sec_data()  # Manual load
            >>>
            >>> # With auto-loading (recommended)
            >>> store = SqliteStore("entities.db", auto_load_sec=True)
            >>> store.initialize()
            >>> entities = store.search("APPLE")  # Auto-loads SEC data
        """
        self.db_path = str(db_path)
        self._initialized = False

        # Connection manager
        self.connection = SqliteConnectionManager(db_path)

        # Auto-load configuration
        self._auto_load_sec = auto_load_sec
        self._cache_dir = cache_dir
        self._sec_loader: SecDataLoader | None = None
        self._auto_loaded = False

        # Repositories (initialized lazily after initialize() called)
        self._entities: EntityRepository | None = None
        self._securities: SecurityRepository | None = None
        self._listings: ListingRepository | None = None
        self._claims: ClaimRepository | None = None
        self._assets: AssetRepository | None = None
        self._contracts: ContractRepository | None = None
        self._products: ProductRepository | None = None
        self._brands: BrandRepository | None = None
        self._events: EventRepository | None = None
        self._geos: GeoRepository | None = None
        self._addresses: AddressRepository | None = None
        self._roles: RoleRepository | None = None
        self._relationships: RelationshipRepository | None = None
        self._cases: CaseRepository | None = None
        self._clusters: ClusterRepository | None = None

    # =========================================================================
    # StorageLifecycleProtocol
    # =========================================================================

    def initialize(self) -> None:
        """
        Initialize storage and create tables.
        
        Idempotent: safe to call multiple times.
        """
        if self._initialized:
            return

        # Create schema
        with self.connection.connection() as conn:
            conn.executescript(SCHEMA_SQL)
            conn.commit()

        # Initialize all repositories
        self._entities = EntityRepository(self.connection)
        self._securities = SecurityRepository(self.connection)
        self._listings = ListingRepository(self.connection)
        self._claims = ClaimRepository(self.connection)
        self._assets = AssetRepository(self.connection)
        self._contracts = ContractRepository(self.connection)
        self._products = ProductRepository(self.connection)
        self._brands = BrandRepository(self.connection)
        self._events = EventRepository(self.connection)
        self._geos = GeoRepository(self.connection)
        self._addresses = AddressRepository(self.connection)
        self._roles = RoleRepository(self.connection)
        self._relationships = RelationshipRepository(self.connection)
        self._cases = CaseRepository(self.connection)
        self._clusters = ClusterRepository(self.connection)

        self._initialized = True
        logger.info(f"SqliteStore initialized at {self.db_path}")

    def close(self) -> None:
        """Close database connection."""
        self.connection.close()
        self._initialized = False

    # =========================================================================
    # SEC Data Loading
    # =========================================================================

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
        items = list(data.values()) if isinstance(data, dict) else list(data)

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
                existing = self.connection.fetchone(
                    "SELECT e.entity_id FROM entities e "
                    "JOIN claims c ON e.entity_id = c.entity_id "
                    "WHERE c.scheme = 'cik' AND c.value = ?",
                    (cik_normalized,),
                )

                if existing:
                    # Entity exists, maybe add listing
                    if ticker:
                        self._ensure_listing_for_entity(existing["entity_id"], ticker, name)
                    continue

                # Create new entity
                now = utc_now()
                now_str = to_iso8601(now)
                entity_id = generate_ulid()

                self.connection.execute(
                    """INSERT INTO entities
                       (entity_id, primary_name, entity_type, status,
                        source_system, source_id, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        entity_id,
                        name.strip(),
                        "organization",
                        "active",
                        "sec",
                        cik_normalized,
                        now_str,
                        now_str,
                    ),
                )

                # Create CIK claim
                claim_id = generate_ulid()
                self.connection.execute(
                    """INSERT INTO claims
                       (claim_id, entity_id, scheme, value, namespace,
                        status, confidence, source, captured_at, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        claim_id,
                        entity_id,
                        "cik",
                        cik_normalized,
                        "SEC",
                        "active",
                        1.0,
                        "sec_json",
                        now_str,
                        now_str,
                        now_str,
                    ),
                )

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
            >>> store = SqliteStore(":memory:")
            >>> store.initialize()
            >>> count = store.load_sec_data()  # Downloads ~14,000 companies
            >>> print(f"Loaded {count} companies")
        """
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
        now_str = to_iso8601(utc_now())
        ticker_normalized = ticker.upper().replace("-", ".")

        # Create security
        security_id = generate_ulid()
        self.connection.execute(
            """INSERT INTO securities
               (security_id, entity_id, security_type, status, description,
                source_system, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                security_id,
                entity_id,
                "common_stock",
                "active",
                f"{name} Common Stock",
                "sec",
                now_str,
                now_str,
            ),
        )

        # Create listing (TICKER LIVES HERE!)
        listing_id = generate_ulid()
        self.connection.execute(
            """INSERT INTO listings
               (listing_id, security_id, ticker, exchange, status, is_primary,
                source_system, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                listing_id,
                security_id,
                ticker_normalized,
                "UNKNOWN",
                "active",
                1,
                "sec",
                now_str,
                now_str,
            ),
        )

        # Create ticker claim on LISTING (TICKER→listing scope)
        claim_id = generate_ulid()
        self.connection.execute(
            """INSERT INTO claims
               (claim_id, listing_id, scheme, value, namespace,
                status, confidence, source, captured_at, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                claim_id,
                listing_id,
                "ticker",
                ticker_normalized,
                "SEC",
                "active",
                1.0,
                "sec_json",
                now_str,
                now_str,
                now_str,
            ),
        )

        return security_id, listing_id

    def _ensure_listing_for_entity(self, entity_id: str, ticker: str, name: str) -> None:
        """Ensure a listing exists for an entity/ticker combination."""
        ticker_normalized = ticker.upper().replace("-", ".")

        # Check if listing already exists for this entity+ticker
        existing = self.connection.fetchone(
            """SELECT l.listing_id FROM listings l
               JOIN securities s ON l.security_id = s.security_id
               WHERE s.entity_id = ? AND l.ticker = ?""",
            (entity_id, ticker_normalized),
        )

        if not existing:
            self._create_security_and_listing(entity_id, name, ticker)

    def _ensure_auto_loaded(self) -> None:
        """Ensure SEC data is loaded if auto_load_sec is enabled."""
        if self._auto_load_sec and not self._auto_loaded:
            # Lazy import to avoid circular dependency
            from entityspine.loaders.sec_loader import SecDataLoader

            if self._sec_loader is None:
                self._sec_loader = SecDataLoader(
                    self,
                    cache_dir=self._cache_dir,
                )
            self._sec_loader.ensure_loaded()
            self._auto_loaded = True

    # =========================================================================
    # Entity Operations (delegates to EntityRepository)
    # =========================================================================

    def save_entity(self, entity: Entity) -> None:
        """Save or update entity."""
        self._entities.save(entity)

    def get_entity(self, entity_id: str) -> Entity | None:
        """Get entity by ID, following redirects."""
        self._ensure_auto_loaded()
        return self._entities.get_by_id(entity_id)

    def get_entity_raw(self, entity_id: str) -> Entity | None:
        """Get entity by ID WITHOUT following redirects."""
        return self._entities.get_raw(entity_id)

    def get_entities_by_cik(self, cik: str) -> list[Entity]:
        """Get entities matching CIK."""
        self._ensure_auto_loaded()
        return self._entities.get_by_cik(cik)

    def get_entities_by_ticker(self, ticker: str) -> list[Entity]:
        """Get entities matching ticker (via Listing lookup)."""
        self._ensure_auto_loaded()
        return self._entities.get_by_ticker(ticker)

    def search_entities(self, query: str, limit: int = 10) -> list[tuple[Entity, float]]:
        """Search entities by name or identifier."""
        self._ensure_auto_loaded()
        return self._entities.search(query, limit)

    def count_entities(self) -> int:
        """Return the count of entities in the store."""
        return self._entities.count()

    def entity_count(self) -> int:
        """Get total number of entities."""
        return self._entities.count()

    # =========================================================================
    # Security Operations (delegates to SecurityRepository)
    # =========================================================================

    def save_security(self, security: Security) -> None:
        """Save or update security."""
        self._securities.save(security)

    def get_security(self, security_id: str) -> Security | None:
        """Get security by ID."""
        return self._securities.get_by_id(security_id)

    def get_securities_by_entity(self, entity_id: str) -> list[Security]:
        """Get all securities issued by an entity."""
        return self._securities.get_by_entity(entity_id)

    def security_count(self) -> int:
        """Get total number of securities."""
        return self._securities.count()

    # =========================================================================
    # Listing Operations (delegates to ListingRepository)
    # =========================================================================

    def save_listing(self, listing: Listing) -> None:
        """Save or update listing."""
        self._listings.save(listing)

    def get_listings_by_ticker(
        self,
        ticker: str,
        mic: str | None = None,
        as_of: date | None = None,
    ) -> list[Listing]:
        """Get listings matching ticker."""
        return self._listings.get_by_ticker(ticker, mic, as_of)

    def get_listings_by_security(self, security_id: str) -> list[Listing]:
        """Get all listings for a security."""
        return self._listings.get_by_security(security_id)

    def listing_count(self) -> int:
        """Get total number of listings."""
        return self._listings.count()

    # =========================================================================
    # Claim Operations (delegates to ClaimRepository)
    # =========================================================================

    def save_claim(self, claim: IdentifierClaim) -> None:
        """Save identifier claim."""
        self._claims.save(claim)

    def get_claims(self, scheme: str, value: str) -> list[IdentifierClaim]:
        """Get claims matching scheme and value."""
        return self._claims.get(scheme, value)

    def get_claims_for_entity(self, entity_id: str) -> list[IdentifierClaim]:
        """Get all identifier claims for an entity."""
        return self._claims.get_for_entity(entity_id)

    def get_claims_by_value(
        self,
        scheme: IdentifierScheme,
        value: str,
    ) -> list[IdentifierClaim]:
        """Get claims by scheme and value."""
        return self._claims.get_by_value(scheme, value)

    def claim_count(self) -> int:
        """Get total number of claims."""
        return self._claims.count()

    # =========================================================================
    # Asset Operations (delegates to AssetRepository)
    # =========================================================================

    def save_asset(self, asset: Asset) -> None:
        """Save or update an asset."""
        self._assets.save(asset)

    def get_asset(self, asset_id: str) -> Asset | None:
        """Get asset by ID."""
        return self._assets.get_by_id(asset_id)

    def get_assets_by_owner(self, entity_id: str) -> list[Asset]:
        """Get all assets owned by an entity."""
        return self._assets.get_by_owner(entity_id)

    def asset_count(self) -> int:
        """Get total number of assets."""
        return self._assets.count()

    # =========================================================================
    # Contract Operations (delegates to ContractRepository)
    # =========================================================================

    def save_contract(self, contract: Contract) -> None:
        """Save or update a contract."""
        self._contracts.save(contract)

    def get_contract(self, contract_id: str) -> Contract | None:
        """Get contract by ID."""
        return self._contracts.get_by_id(contract_id)

    def contract_count(self) -> int:
        """Get total number of contracts."""
        return self._contracts.count()

    # =========================================================================
    # Product Operations (delegates to ProductRepository)
    # =========================================================================

    def save_product(self, product: Product) -> None:
        """Save or update a product."""
        self._products.save(product)

    def get_product(self, product_id: str) -> Product | None:
        """Get product by ID."""
        return self._products.get_by_id(product_id)

    def get_products_by_owner(self, entity_id: str) -> list[Product]:
        """Get all products owned by an entity."""
        return self._products.get_by_owner(entity_id)

    def product_count(self) -> int:
        """Get total number of products."""
        return self._products.count()

    # =========================================================================
    # Brand Operations (delegates to BrandRepository)
    # =========================================================================

    def save_brand(self, brand: Brand) -> None:
        """Save or update a brand."""
        self._brands.save(brand)

    def get_brand(self, brand_id: str) -> Brand | None:
        """Get brand by ID."""
        return self._brands.get_by_id(brand_id)

    def get_brands_by_owner(self, entity_id: str) -> list[Brand]:
        """Get all brands owned by an entity."""
        return self._brands.get_by_owner(entity_id)

    def brand_count(self) -> int:
        """Get total number of brands."""
        return self._brands.count()

    # =========================================================================
    # Event Operations (delegates to EventRepository)
    # =========================================================================

    def save_event(self, event: Event) -> None:
        """Save or update an event."""
        self._events.save(event)

    def get_event(self, event_id: str) -> Event | None:
        """Get event by ID."""
        return self._events.get_by_id(event_id)

    def get_events_by_type(self, event_type: EventType) -> list[Event]:
        """Get all events of a specific type."""
        return self._events.get_by_type(event_type)

    def event_count(self) -> int:
        """Get total number of events."""
        return self._events.count()

    # =========================================================================
    # Geo Operations (delegates to GeoRepository)
    # =========================================================================

    def save_geo(self, geo: Geo) -> None:
        """Save or update a geographic location."""
        self._geos.save(geo)

    def get_geo(self, geo_id: str) -> Geo | None:
        """Get geographic location by ID."""
        return self._geos.get_by_id(geo_id)

    def geo_count(self) -> int:
        """Get total number of geographic locations."""
        return self._geos.count()

    # =========================================================================
    # Address Operations (delegates to AddressRepository)
    # =========================================================================

    def save_address(self, address: Address) -> None:
        """Save or update an address."""
        self._addresses.save(address)

    def get_address(self, address_id: str) -> Address | None:
        """Get address by ID."""
        return self._addresses.get_by_id(address_id)

    def get_address_by_hash(self, normalized_hash: str) -> Address | None:
        """Get address by normalized hash for deduplication."""
        return self._addresses.get_by_hash(normalized_hash)

    def save_entity_address(
        self,
        entity_id: str,
        address_id: str,
        address_type: AddressType,
    ) -> None:
        """Link an entity to an address."""
        self._addresses.save_entity_address(entity_id, address_id, address_type)

    def address_count(self) -> int:
        """Get total number of addresses."""
        return self._addresses.count()

    # =========================================================================
    # Role Operations (delegates to RoleRepository)
    # =========================================================================

    def save_role_assignment(self, role: RoleAssignment) -> None:
        """Save or update a role assignment."""
        self._roles.save(role)

    def get_role_assignment(self, role_assignment_id: str) -> RoleAssignment | None:
        """Get role assignment by ID."""
        return self._roles.get_by_id(role_assignment_id)

    def get_role_assignments_by_org(self, org_entity_id: str) -> list[RoleAssignment]:
        """Get all role assignments for an organization."""
        return self._roles.get_by_org(org_entity_id)

    def get_role_assignments_by_person(self, person_entity_id: str) -> list[RoleAssignment]:
        """Get all role assignments for a person."""
        return self._roles.get_by_person(person_entity_id)

    def get_role_assignments(
        self,
        person_entity_id: str | None = None,
        org_entity_id: str | None = None,
        role_types: list | None = None,
        current_only: bool = False,
    ) -> list[RoleAssignment]:
        """Get role assignments with optional filters."""
        return self._roles.get_with_filters(
            person_entity_id, org_entity_id, role_types, current_only
        )

    def role_assignment_count(self) -> int:
        """Get total number of role assignments."""
        return self._roles.count()

    # =========================================================================
    # Relationship Operations (delegates to RelationshipRepository)
    # =========================================================================

    def save_relationship(self, rel: Relationship) -> None:
        """Save or update a generic relationship."""
        self._relationships.save(rel)

    def get_relationship(self, relationship_id: str) -> Relationship | None:
        """Get relationship by ID."""
        return self._relationships.get_by_id(relationship_id)

    def get_relationships_by_source_id(
        self,
        source_id: str,
        limit: int = 100,
    ) -> list[Relationship]:
        """Get all relationships from a source node (by its ID)."""
        return self._relationships.get_by_source_id(source_id, limit)

    def relationship_count(self) -> int:
        """Get total number of generic relationships."""
        return self._relationships.count()

    def save_entity_relationship(self, rel: EntityRelationship) -> None:
        """Save or update an entity relationship."""
        self._relationships.save_entity_relationship(rel)

    def get_entity_relationships(
        self,
        from_entity_id: str | None = None,
        to_entity_id: str | None = None,
        relationship_types: list | None = None,
    ) -> list[EntityRelationship]:
        """Get entity relationships with optional filters."""
        return self._relationships.get_entity_relationships(
            from_entity_id, to_entity_id, relationship_types
        )

    # =========================================================================
    # Case Operations (delegates to CaseRepository)
    # =========================================================================

    def save_case(self, case: Case) -> None:
        """Save or update a legal case."""
        self._cases.save(case)

    def get_case(self, case_id: str) -> Case | None:
        """Get case by ID."""
        return self._cases.get_by_id(case_id)

    def get_cases_by_target(self, target_entity_id: str) -> list[Case]:
        """Get all cases involving a target entity."""
        return self._cases.get_by_target(target_entity_id)

    def get_cases_by_authority(self, authority_entity_id: str) -> list[Case]:
        """Get all cases from an authority (court/regulator)."""
        return self._cases.get_by_authority(authority_entity_id)

    def case_count(self) -> int:
        """Get total number of cases."""
        return self._cases.count()

    # =========================================================================
    # Cluster Operations (delegates to ClusterRepository)
    # =========================================================================

    def save_cluster(self, cluster: EntityCluster) -> None:
        """Save or update an entity cluster."""
        self._clusters.save(cluster)

    def get_cluster(self, cluster_id: str) -> EntityCluster | None:
        """Get cluster by ID."""
        return self._clusters.get_by_id(cluster_id)

    def get_clusters_by_status(self, status: str) -> list[EntityCluster]:
        """Get clusters by status (pending, approved, rejected, merged)."""
        return self._clusters.get_by_status(status)

    def cluster_count(self) -> int:
        """Get total number of entity clusters."""
        return self._clusters.count()

    def save_cluster_member(self, member: EntityClusterMember) -> None:
        """Save or update a cluster membership."""
        self._clusters.save_member(member)

    def get_cluster_members(self, cluster_id: str) -> list[EntityClusterMember]:
        """Get all members of a cluster."""
        return self._clusters.get_members(cluster_id)

    def get_clusters_for_entity(self, entity_id: str) -> list[EntityClusterMember]:
        """Get all cluster memberships for an entity."""
        return self._clusters.get_clusters_for_entity(entity_id)

    def cluster_member_count(self) -> int:
        """Get total number of cluster memberships."""
        return self._clusters.member_count()

    # =========================================================================
    # Legacy compatibility: Direct connection access (for backward compatibility)
    # =========================================================================

    @property
    def _conn(self):
        """Legacy property for backward compatibility."""
        with self.connection.connection() as conn:
            return conn

    def _get_connection(self):
        """
        Legacy method for backward compatibility.
        
        Returns a context manager for database connection.
        New code should use self.connection.connection() instead.
        """
        return self.connection.connection()
