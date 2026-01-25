"""
SQLite Store - Tier 1 storage backend for EntitySpine.

Tier 1 Characteristics:
- SQLite database using stdlib sqlite3 (ZERO external dependencies)
- Full Entity/Security/Listing hierarchy
- Identifier claims with validity tracking
- LIKE pattern search
- No temporal/historical data (as_of will be IGNORED)

TIER CAPABILITY HONESTY:
When as_of is provided, the store MUST:
1. Return current entity (best effort)
2. The resolver adds warning: "as_of_ignored: Tier 1 store lacks temporal data"

v2.2.3 ARCHITECTURE:
- Uses DOMAIN dataclasses internally (entityspine.domain.*)
- Returns domain dataclasses from all public methods
- Pydantic/SQLModel NOT used here (zero-deps for Tier 1)
"""

import json
import logging
import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Optional

from entityspine.core.identifier import looks_like_cik, looks_like_ticker
from entityspine.core.timestamps import from_iso8601, to_iso8601, utc_now
from entityspine.core.ulid import generate_ulid

# v2.2.3: Use DOMAIN dataclasses (stdlib-only, zero deps)
from entityspine.domain import (
    ClaimStatus,
    Entity,
    EntityStatus,
    EntityType,
    IdentifierClaim,
    IdentifierScheme,
    Listing,
    ListingStatus,
    Security,
    SecurityStatus,
    SecurityType,
    VendorNamespace,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Schema Definitions
# =============================================================================

_SCHEMA_SQL = """
-- Entities table
CREATE TABLE IF NOT EXISTS entities (
    entity_id TEXT PRIMARY KEY,
    primary_name TEXT NOT NULL,
    entity_type TEXT NOT NULL DEFAULT 'organization',
    status TEXT NOT NULL DEFAULT 'active',
    source_system TEXT,
    source_id TEXT,
    jurisdiction TEXT,
    sic_code TEXT,
    redirect_to TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(primary_name);
CREATE INDEX IF NOT EXISTS idx_entities_source ON entities(source_system, source_id);
CREATE INDEX IF NOT EXISTS idx_entities_status ON entities(status);

-- Securities table
CREATE TABLE IF NOT EXISTS securities (
    security_id TEXT PRIMARY KEY,
    entity_id TEXT NOT NULL,
    security_type TEXT NOT NULL DEFAULT 'common_stock',
    status TEXT NOT NULL DEFAULT 'active',
    description TEXT,
    source_system TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (entity_id) REFERENCES entities(entity_id)
);

CREATE INDEX IF NOT EXISTS idx_securities_entity ON securities(entity_id);
CREATE INDEX IF NOT EXISTS idx_securities_type ON securities(security_type);

-- Listings table (TICKER LIVES HERE!)
CREATE TABLE IF NOT EXISTS listings (
    listing_id TEXT PRIMARY KEY,
    security_id TEXT NOT NULL,
    ticker TEXT NOT NULL,
    exchange TEXT NOT NULL,
    mic TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    is_primary INTEGER NOT NULL DEFAULT 0,
    start_date TEXT,
    end_date TEXT,
    source_system TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (security_id) REFERENCES securities(security_id)
);

CREATE INDEX IF NOT EXISTS idx_listings_security ON listings(security_id);
CREATE INDEX IF NOT EXISTS idx_listings_ticker ON listings(ticker);
CREATE INDEX IF NOT EXISTS idx_listings_exchange ON listings(exchange);

-- Identifier Claims table (canonical identifier storage)
CREATE TABLE IF NOT EXISTS claims (
    claim_id TEXT PRIMARY KEY,
    entity_id TEXT,
    security_id TEXT,
    listing_id TEXT,
    scheme TEXT NOT NULL,
    value TEXT NOT NULL,
    namespace TEXT NOT NULL DEFAULT 'UNKNOWN',
    status TEXT NOT NULL DEFAULT 'active',
    confidence REAL NOT NULL DEFAULT 1.0,
    source TEXT,
    valid_from TEXT,
    valid_to TEXT,
    captured_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (entity_id) REFERENCES entities(entity_id),
    FOREIGN KEY (security_id) REFERENCES securities(security_id),
    FOREIGN KEY (listing_id) REFERENCES listings(listing_id)
);

CREATE INDEX IF NOT EXISTS idx_claims_scheme_value ON claims(scheme, value);
CREATE INDEX IF NOT EXISTS idx_claims_entity ON claims(entity_id);
CREATE INDEX IF NOT EXISTS idx_claims_security ON claims(security_id);
CREATE INDEX IF NOT EXISTS idx_claims_listing ON claims(listing_id);

-- =============================================================================
-- Knowledge Graph Tables (v2.2.3)
-- =============================================================================

-- Addresses table (normalized addresses)
CREATE TABLE IF NOT EXISTS addresses (
    address_id TEXT PRIMARY KEY,
    line1 TEXT,
    line2 TEXT,
    city TEXT,
    region TEXT,
    postal TEXT,
    country TEXT NOT NULL DEFAULT 'US',
    normalized_hash TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_addresses_hash ON addresses(normalized_hash);
CREATE INDEX IF NOT EXISTS idx_addresses_city ON addresses(city);

-- Entity-Address link table
CREATE TABLE IF NOT EXISTS entity_addresses (
    entity_id TEXT NOT NULL,
    address_id TEXT NOT NULL,
    address_type TEXT NOT NULL DEFAULT 'business',
    valid_from TEXT,
    valid_to TEXT,
    captured_at TEXT NOT NULL,
    source_system TEXT,
    source_ref TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (entity_id, address_id, address_type),
    FOREIGN KEY (entity_id) REFERENCES entities(entity_id),
    FOREIGN KEY (address_id) REFERENCES addresses(address_id)
);

CREATE INDEX IF NOT EXISTS idx_entity_addresses_entity ON entity_addresses(entity_id);
CREATE INDEX IF NOT EXISTS idx_entity_addresses_address ON entity_addresses(address_id);

-- Geographic locations (Geo nodes)
CREATE TABLE IF NOT EXISTS geos (
    geo_id TEXT PRIMARY KEY,
    geo_type TEXT NOT NULL,
    name TEXT NOT NULL,
    iso_code TEXT,
    parent_geo_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (parent_geo_id) REFERENCES geos(geo_id)
);

CREATE INDEX IF NOT EXISTS idx_geos_iso ON geos(iso_code);
CREATE INDEX IF NOT EXISTS idx_geos_type ON geos(geo_type);
CREATE INDEX IF NOT EXISTS idx_geos_name ON geos(name);

-- Role assignments (person -> org roles)
CREATE TABLE IF NOT EXISTS role_assignments (
    role_assignment_id TEXT PRIMARY KEY,
    person_entity_id TEXT NOT NULL,
    org_entity_id TEXT NOT NULL,
    role_type TEXT NOT NULL,
    title TEXT,
    start_date TEXT,
    end_date TEXT,
    confidence REAL NOT NULL DEFAULT 1.0,
    captured_at TEXT NOT NULL,
    source_system TEXT,
    source_ref TEXT,
    filing_id TEXT,
    section_id TEXT,
    snippet_hash TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (person_entity_id) REFERENCES entities(entity_id),
    FOREIGN KEY (org_entity_id) REFERENCES entities(entity_id)
);

CREATE INDEX IF NOT EXISTS idx_role_assignments_person ON role_assignments(person_entity_id);
CREATE INDEX IF NOT EXISTS idx_role_assignments_org ON role_assignments(org_entity_id);
CREATE INDEX IF NOT EXISTS idx_role_assignments_role ON role_assignments(role_type);
CREATE INDEX IF NOT EXISTS idx_role_assignments_dates ON role_assignments(start_date, end_date);

-- Entity relationships (entity <-> entity edges)
CREATE TABLE IF NOT EXISTS entity_relationships (
    relationship_id TEXT PRIMARY KEY,
    from_entity_id TEXT NOT NULL,
    to_entity_id TEXT NOT NULL,
    relationship_type TEXT NOT NULL,
    valid_from TEXT,
    valid_to TEXT,
    captured_at TEXT NOT NULL,
    source_system TEXT,
    source_ref TEXT,
    confidence REAL NOT NULL DEFAULT 1.0,
    status TEXT NOT NULL DEFAULT 'active',
    evidence_text TEXT,
    filing_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (from_entity_id) REFERENCES entities(entity_id),
    FOREIGN KEY (to_entity_id) REFERENCES entities(entity_id)
);

CREATE INDEX IF NOT EXISTS idx_relationships_from ON entity_relationships(from_entity_id);
CREATE INDEX IF NOT EXISTS idx_relationships_to ON entity_relationships(to_entity_id);
CREATE INDEX IF NOT EXISTS idx_relationships_type ON entity_relationships(relationship_type);

-- Generic relationships (using NodeRef pattern - serialized as kind:id)
CREATE TABLE IF NOT EXISTS relationships (
    relationship_id TEXT PRIMARY KEY,
    source_kind TEXT NOT NULL,
    source_id TEXT NOT NULL,
    target_kind TEXT NOT NULL,
    target_id TEXT NOT NULL,
    relationship_type TEXT NOT NULL,
    subtype TEXT,
    valid_from TEXT,
    valid_to TEXT,
    captured_at TEXT NOT NULL,
    source_system TEXT,
    source_ref TEXT,
    confidence REAL NOT NULL DEFAULT 1.0,
    evidence_filing_id TEXT,
    evidence_section_id TEXT,
    evidence_excerpt_hash TEXT,
    evidence_snippet TEXT,
    metrics TEXT,  -- JSON serialized
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_generic_rel_source ON relationships(source_kind, source_id);
CREATE INDEX IF NOT EXISTS idx_generic_rel_target ON relationships(target_kind, target_id);
CREATE INDEX IF NOT EXISTS idx_generic_rel_type ON relationships(relationship_type);

-- Legal cases/proceedings
CREATE TABLE IF NOT EXISTS cases (
    case_id TEXT PRIMARY KEY,
    case_type TEXT NOT NULL,
    case_number TEXT,
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'unknown',
    authority_entity_id TEXT,
    target_entity_id TEXT,
    opened_date TEXT,
    closed_date TEXT,
    description TEXT,
    source_system TEXT,
    source_ref TEXT,
    filing_id TEXT,
    captured_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (authority_entity_id) REFERENCES entities(entity_id),
    FOREIGN KEY (target_entity_id) REFERENCES entities(entity_id)
);

CREATE INDEX IF NOT EXISTS idx_cases_type ON cases(case_type);
CREATE INDEX IF NOT EXISTS idx_cases_status ON cases(status);
CREATE INDEX IF NOT EXISTS idx_cases_authority ON cases(authority_entity_id);
CREATE INDEX IF NOT EXISTS idx_cases_target ON cases(target_entity_id);
CREATE INDEX IF NOT EXISTS idx_cases_number ON cases(case_number);

-- Entity clusters (for deduplication)
CREATE TABLE IF NOT EXISTS entity_clusters (
    cluster_id TEXT PRIMARY KEY,
    reason TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Cluster membership
CREATE TABLE IF NOT EXISTS entity_cluster_members (
    cluster_id TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'member',
    confidence REAL NOT NULL DEFAULT 1.0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (cluster_id, entity_id),
    FOREIGN KEY (cluster_id) REFERENCES entity_clusters(cluster_id),
    FOREIGN KEY (entity_id) REFERENCES entities(entity_id)
);

CREATE INDEX IF NOT EXISTS idx_cluster_members_entity ON entity_cluster_members(entity_id);
CREATE INDEX IF NOT EXISTS idx_cluster_members_role ON entity_cluster_members(role);

-- =============================================================================
-- KG High-Confidence Node Tables (v2.2.4)
-- =============================================================================

-- Assets table (physical/tangible assets)
CREATE TABLE IF NOT EXISTS assets (
    asset_id TEXT PRIMARY KEY,
    asset_type TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    owner_entity_id TEXT,
    operator_entity_id TEXT,
    geo_id TEXT,
    address_id TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    source_system TEXT,
    source_id TEXT,
    captured_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (owner_entity_id) REFERENCES entities(entity_id),
    FOREIGN KEY (operator_entity_id) REFERENCES entities(entity_id),
    FOREIGN KEY (geo_id) REFERENCES geos(geo_id),
    FOREIGN KEY (address_id) REFERENCES addresses(address_id)
);

CREATE INDEX IF NOT EXISTS idx_assets_type ON assets(asset_type);
CREATE INDEX IF NOT EXISTS idx_assets_name ON assets(name);
CREATE INDEX IF NOT EXISTS idx_assets_owner ON assets(owner_entity_id);
CREATE INDEX IF NOT EXISTS idx_assets_status ON assets(status);
CREATE INDEX IF NOT EXISTS idx_assets_source ON assets(source_system, source_id);

-- Contracts table (legal agreements)
CREATE TABLE IF NOT EXISTS contracts (
    contract_id TEXT PRIMARY KEY,
    contract_type TEXT NOT NULL,
    title TEXT NOT NULL,
    effective_date TEXT,
    termination_date TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    value_usd REAL,
    source_system TEXT,
    source_id TEXT,
    filing_id TEXT,
    content_hash TEXT,
    summary TEXT,
    captured_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_contracts_type ON contracts(contract_type);
CREATE INDEX IF NOT EXISTS idx_contracts_status ON contracts(status);
CREATE INDEX IF NOT EXISTS idx_contracts_effective ON contracts(effective_date);
CREATE INDEX IF NOT EXISTS idx_contracts_source ON contracts(source_system, source_id);
CREATE INDEX IF NOT EXISTS idx_contracts_filing ON contracts(filing_id);

-- Products table (products/services)
CREATE TABLE IF NOT EXISTS products (
    product_id TEXT PRIMARY KEY,
    product_type TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    owner_entity_id TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    source_system TEXT,
    source_id TEXT,
    captured_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (owner_entity_id) REFERENCES entities(entity_id)
);

CREATE INDEX IF NOT EXISTS idx_products_type ON products(product_type);
CREATE INDEX IF NOT EXISTS idx_products_name ON products(name);
CREATE INDEX IF NOT EXISTS idx_products_owner ON products(owner_entity_id);
CREATE INDEX IF NOT EXISTS idx_products_status ON products(status);
CREATE INDEX IF NOT EXISTS idx_products_source ON products(source_system, source_id);

-- Brands table
CREATE TABLE IF NOT EXISTS brands (
    brand_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    owner_entity_id TEXT,
    description TEXT,
    source_system TEXT,
    source_id TEXT,
    captured_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (owner_entity_id) REFERENCES entities(entity_id)
);

CREATE INDEX IF NOT EXISTS idx_brands_name ON brands(name);
CREATE INDEX IF NOT EXISTS idx_brands_owner ON brands(owner_entity_id);
CREATE INDEX IF NOT EXISTS idx_brands_source ON brands(source_system, source_id);

-- KG Events table (graph-native events, not py-sec-edgar events)
CREATE TABLE IF NOT EXISTS kg_events (
    event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'announced',
    occurred_on TEXT,
    announced_on TEXT,
    payload TEXT,  -- JSON serialized
    evidence_filing_id TEXT,
    evidence_section_id TEXT,
    evidence_snippet TEXT,
    confidence REAL NOT NULL DEFAULT 1.0,
    source_system TEXT,
    source_id TEXT,
    captured_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_kg_events_type ON kg_events(event_type);
CREATE INDEX IF NOT EXISTS idx_kg_events_status ON kg_events(status);
CREATE INDEX IF NOT EXISTS idx_kg_events_occurred ON kg_events(occurred_on);
CREATE INDEX IF NOT EXISTS idx_kg_events_announced ON kg_events(announced_on);
CREATE INDEX IF NOT EXISTS idx_kg_events_source ON kg_events(source_system, source_id);
CREATE INDEX IF NOT EXISTS idx_kg_events_filing ON kg_events(evidence_filing_id);
"""


class SqliteStore:
    """
    Tier 1 SQLite-based entity store using stdlib sqlite3.

    Implements the same interface as JsonEntityStore but with SQLite persistence.
    Uses ONLY stdlib sqlite3 - no SQLModel, no SQLAlchemy, no Pydantic.

    v2.2.3: Returns DOMAIN dataclasses (not Pydantic/ORM models).

    Limitations (TIER CAPABILITY HONESTY):
    - as_of parameter IGNORED (no temporal data)
    - LIKE-based search (not full-text)
    - Max recommended entities: 500,000

    Attributes:
        tier: Storage tier (always 1).
        tier_name: Human-readable tier name.
        supports_temporal: Whether temporal queries work (always False).

    Example:
        >>> store = SqliteStore("entities.db")
        >>> store.initialize()
        >>> store.load_sec_json(data)
        >>> entities = store.get_entities_by_cik("320193")
    """

    tier: int = 1
    tier_name: str = "SQLite (stdlib)"
    supports_temporal: bool = False

    def __init__(self, db_path: str | Path = ":memory:"):
        """
        Initialize SQLite store.

        Args:
            db_path: Path to SQLite database file.
                    Use ":memory:" for in-memory database.
        """
        self.db_path = str(db_path)
        self._conn: sqlite3.Connection | None = None
        self._initialized = False

    @contextmanager
    def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Get a database connection with row factory."""
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row
        yield self._conn

    def _execute(self, sql: str, params: tuple = (), many: bool = False) -> sqlite3.Cursor:
        """Execute SQL and return cursor."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if many:
                cursor.executemany(sql, params)  # type: ignore
            else:
                cursor.execute(sql, params)
            conn.commit()
            return cursor

    def _fetchone(self, sql: str, params: tuple = ()) -> sqlite3.Row | None:
        """Execute SQL and fetch one row."""
        cursor = self._execute(sql, params)
        return cursor.fetchone()

    def _fetchall(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        """Execute SQL and fetch all rows."""
        cursor = self._execute(sql, params)
        return cursor.fetchall()

    # =========================================================================
    # Row to Domain Conversion (stdlib only)
    # =========================================================================

    def _row_to_entity(self, row: sqlite3.Row) -> Entity:
        """Convert database row to Entity domain dataclass."""
        return Entity(
            entity_id=row["entity_id"],
            primary_name=row["primary_name"],
            entity_type=EntityType(row["entity_type"]),
            status=EntityStatus(row["status"]),
            source_system=row["source_system"],
            source_id=row["source_id"],
            jurisdiction=row["jurisdiction"],
            sic_code=row["sic_code"],
            redirect_to=row["redirect_to"],
            created_at=from_iso8601(row["created_at"]) if row["created_at"] else utc_now(),
            updated_at=from_iso8601(row["updated_at"]) if row["updated_at"] else utc_now(),
        )

    def _row_to_security(self, row: sqlite3.Row) -> Security:
        """Convert database row to Security domain dataclass."""
        return Security(
            security_id=row["security_id"],
            entity_id=row["entity_id"],
            security_type=SecurityType(row["security_type"]),
            status=SecurityStatus(row["status"]),
            description=row["description"],
            source_system=row["source_system"],
            created_at=from_iso8601(row["created_at"]) if row["created_at"] else utc_now(),
            updated_at=from_iso8601(row["updated_at"]) if row["updated_at"] else utc_now(),
        )

    def _row_to_listing(self, row: sqlite3.Row) -> Listing:
        """Convert database row to Listing domain dataclass."""
        return Listing(
            listing_id=row["listing_id"],
            security_id=row["security_id"],
            ticker=row["ticker"],
            exchange=row["exchange"],
            mic=row["mic"],
            status=ListingStatus(row["status"]),
            is_primary=bool(row["is_primary"]),
            start_date=date.fromisoformat(row["start_date"]) if row["start_date"] else None,
            end_date=date.fromisoformat(row["end_date"]) if row["end_date"] else None,
            source_system=row["source_system"],
            created_at=from_iso8601(row["created_at"]) if row["created_at"] else utc_now(),
            updated_at=from_iso8601(row["updated_at"]) if row["updated_at"] else utc_now(),
        )

    def _row_to_claim(self, row: sqlite3.Row) -> IdentifierClaim:
        """Convert database row to IdentifierClaim domain dataclass."""
        return IdentifierClaim(
            claim_id=row["claim_id"],
            entity_id=row["entity_id"],
            security_id=row["security_id"],
            listing_id=row["listing_id"],
            scheme=IdentifierScheme(row["scheme"]),
            value=row["value"],
            namespace=VendorNamespace(row["namespace"])
            if row["namespace"]
            else VendorNamespace.UNKNOWN,
            status=ClaimStatus(row["status"]),
            confidence=row["confidence"],
            source=row["source"],
            valid_from=date.fromisoformat(row["valid_from"]) if row["valid_from"] else None,
            valid_to=date.fromisoformat(row["valid_to"]) if row["valid_to"] else None,
            captured_at=from_iso8601(row["captured_at"]) if row["captured_at"] else utc_now(),
            created_at=from_iso8601(row["created_at"]) if row["created_at"] else utc_now(),
            updated_at=from_iso8601(row["updated_at"]) if row["updated_at"] else utc_now(),
        )

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

        with self._get_connection() as conn:
            conn.executescript(_SCHEMA_SQL)
            conn.commit()

        self._initialized = True
        logger.info(f"SqliteStore initialized at {self.db_path}")

    def close(self) -> None:
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
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
                existing = self._fetchone(
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

                self._execute(
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
                self._execute(
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
        import gzip
        import json
        import urllib.request

        SEC_COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
        target_url = url or SEC_COMPANY_TICKERS_URL

        # SEC requires a proper User-Agent header with contact info
        # See: https://www.sec.gov/os/webmaster-faq#developers
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
        self._execute(
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
        self._execute(
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
        self._execute(
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
        existing = self._fetchone(
            """SELECT l.listing_id FROM listings l
               JOIN securities s ON l.security_id = s.security_id
               WHERE s.entity_id = ? AND l.ticker = ?""",
            (entity_id, ticker_normalized),
        )

        if not existing:
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
        row = self._fetchone(
            "SELECT * FROM entities WHERE entity_id = ?",
            (entity_id,),
        )
        if not row:
            return None

        entity = self._row_to_entity(row)
        return self._follow_redirects(entity)

    def get_entity_raw(self, entity_id: str) -> Entity | None:
        """
        Get entity by ID WITHOUT following redirects.

        Args:
            entity_id: Entity ULID.

        Returns:
            Entity exactly as stored.
        """
        row = self._fetchone(
            "SELECT * FROM entities WHERE entity_id = ?",
            (entity_id,),
        )
        return self._row_to_entity(row) if row else None

    def get_entities_by_cik(self, cik: str) -> list[Entity]:
        """
        Get entities matching CIK.

        Args:
            cik: SEC Central Index Key (with or without padding).

        Returns:
            List of matching entities.
        """
        cik_normalized = cik.strip().zfill(10)

        rows = self._fetchall(
            """SELECT DISTINCT e.* FROM entities e
               JOIN claims c ON e.entity_id = c.entity_id
               WHERE c.scheme = 'cik' AND c.value = ?""",
            (cik_normalized,),
        )

        entities = []
        seen_ids: set[str] = set()

        for row in rows:
            entity = self._row_to_entity(row)
            entity = self._follow_redirects(entity)
            if entity.entity_id not in seen_ids:
                entities.append(entity)
                seen_ids.add(entity.entity_id)

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

        rows = self._fetchall(
            """SELECT DISTINCT e.* FROM entities e
               JOIN securities s ON e.entity_id = s.entity_id
               JOIN listings l ON s.security_id = l.security_id
               WHERE l.ticker = ?""",
            (ticker_normalized,),
        )

        entities = []
        seen_ids: set[str] = set()

        for row in rows:
            entity = self._row_to_entity(row)
            entity = self._follow_redirects(entity)
            if entity.entity_id not in seen_ids:
                entities.append(entity)
                seen_ids.add(entity.entity_id)

        return entities

    def save_entity(self, entity: Entity) -> None:
        """
        Save or update entity.

        Args:
            entity: Entity (domain dataclass) to save.
        """
        entity = entity.with_update()
        now_str = to_iso8601(entity.updated_at)

        # Upsert
        self._execute(
            """INSERT INTO entities
               (entity_id, primary_name, entity_type, status,
                source_system, source_id, jurisdiction, sic_code, redirect_to,
                created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(entity_id) DO UPDATE SET
                 primary_name = excluded.primary_name,
                 entity_type = excluded.entity_type,
                 status = excluded.status,
                 source_system = excluded.source_system,
                 source_id = excluded.source_id,
                 jurisdiction = excluded.jurisdiction,
                 sic_code = excluded.sic_code,
                 redirect_to = excluded.redirect_to,
                 updated_at = excluded.updated_at""",
            (
                entity.entity_id,
                entity.primary_name,
                entity.entity_type.value,
                entity.status.value,
                entity.source_system,
                entity.source_id,
                entity.jurisdiction,
                entity.sic_code,
                entity.redirect_to,
                to_iso8601(entity.created_at),
                now_str,
            ),
        )

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

        NOTE: as_of is IGNORED (Tier 1 has no temporal data).
        The resolver will add a warning.

        Args:
            ticker: Stock ticker symbol.
            mic: Optional MIC filter.
            as_of: Optional date filter (IGNORED - Tier 1 limitation).

        Returns:
            List of matching Listing objects.
        """
        ticker_normalized = ticker.upper().strip().replace("-", ".")

        if mic:
            rows = self._fetchall(
                "SELECT * FROM listings WHERE ticker = ? AND mic = ?",
                (ticker_normalized, mic),
            )
        else:
            rows = self._fetchall(
                "SELECT * FROM listings WHERE ticker = ?",
                (ticker_normalized,),
            )

        return [self._row_to_listing(row) for row in rows]

    def get_listings_by_security(self, security_id: str) -> list[Listing]:
        """
        Get all listings for a security.

        Args:
            security_id: Security ULID.

        Returns:
            All listings for the security.
        """
        rows = self._fetchall(
            "SELECT * FROM listings WHERE security_id = ?",
            (security_id,),
        )
        return [self._row_to_listing(row) for row in rows]

    def save_listing(self, listing: Listing) -> None:
        """Save or update listing."""
        listing = listing.with_update()
        now_str = to_iso8601(listing.updated_at)

        self._execute(
            """INSERT INTO listings
               (listing_id, security_id, ticker, exchange, mic, status, is_primary,
                start_date, end_date, source_system, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(listing_id) DO UPDATE SET
                 security_id = excluded.security_id,
                 ticker = excluded.ticker,
                 exchange = excluded.exchange,
                 mic = excluded.mic,
                 status = excluded.status,
                 is_primary = excluded.is_primary,
                 start_date = excluded.start_date,
                 end_date = excluded.end_date,
                 source_system = excluded.source_system,
                 updated_at = excluded.updated_at""",
            (
                listing.listing_id,
                listing.security_id,
                listing.ticker,
                listing.exchange,
                listing.mic,
                listing.status.value,
                1 if listing.is_primary else 0,
                listing.start_date.isoformat() if listing.start_date else None,
                listing.end_date.isoformat() if listing.end_date else None,
                listing.source_system,
                to_iso8601(listing.created_at),
                now_str,
            ),
        )

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
        rows = self._fetchall(
            "SELECT * FROM claims WHERE scheme = ? AND value = ?",
            (scheme.lower(), value),
        )
        return [self._row_to_claim(row) for row in rows]

    def save_claim(self, claim: IdentifierClaim) -> None:
        """Save identifier claim."""
        claim = claim.with_update()
        now_str = to_iso8601(claim.updated_at)

        scheme_val = (
            claim.scheme.value if isinstance(claim.scheme, IdentifierScheme) else str(claim.scheme)
        )
        namespace_val = (
            claim.namespace.value
            if isinstance(claim.namespace, VendorNamespace)
            else str(claim.namespace)
        )
        status_val = (
            claim.status.value if isinstance(claim.status, ClaimStatus) else str(claim.status)
        )

        self._execute(
            """INSERT INTO claims
               (claim_id, entity_id, security_id, listing_id, scheme, value,
                namespace, status, confidence, source, valid_from, valid_to,
                captured_at, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(claim_id) DO UPDATE SET
                 entity_id = excluded.entity_id,
                 security_id = excluded.security_id,
                 listing_id = excluded.listing_id,
                 scheme = excluded.scheme,
                 value = excluded.value,
                 namespace = excluded.namespace,
                 status = excluded.status,
                 confidence = excluded.confidence,
                 source = excluded.source,
                 valid_from = excluded.valid_from,
                 valid_to = excluded.valid_to,
                 captured_at = excluded.captured_at,
                 updated_at = excluded.updated_at""",
            (
                claim.claim_id,
                claim.entity_id,
                claim.security_id,
                claim.listing_id,
                scheme_val,
                claim.value,
                namespace_val,
                status_val,
                claim.confidence,
                claim.source,
                claim.valid_from.isoformat() if claim.valid_from else None,
                claim.valid_to.isoformat() if claim.valid_to else None,
                to_iso8601(claim.captured_at),
                to_iso8601(claim.created_at),
                now_str,
            ),
        )

    # =========================================================================
    # SecurityStoreProtocol
    # =========================================================================

    def get_security(self, security_id: str) -> Security | None:
        """Get security by ID."""
        row = self._fetchone(
            "SELECT * FROM securities WHERE security_id = ?",
            (security_id,),
        )
        return self._row_to_security(row) if row else None

    def get_securities_by_entity(self, entity_id: str) -> list[Security]:
        """Get all securities issued by an entity."""
        rows = self._fetchall(
            "SELECT * FROM securities WHERE entity_id = ?",
            (entity_id,),
        )
        return [self._row_to_security(row) for row in rows]

    def save_security(self, security: Security) -> None:
        """Save or update security."""
        security = security.with_update()
        now_str = to_iso8601(security.updated_at)

        self._execute(
            """INSERT INTO securities
               (security_id, entity_id, security_type, status, description,
                source_system, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(security_id) DO UPDATE SET
                 entity_id = excluded.entity_id,
                 security_type = excluded.security_type,
                 status = excluded.status,
                 description = excluded.description,
                 source_system = excluded.source_system,
                 updated_at = excluded.updated_at""",
            (
                security.security_id,
                security.entity_id,
                security.security_type.value,
                security.status.value,
                security.description,
                security.source_system,
                to_iso8601(security.created_at),
                now_str,
            ),
        )

    # =========================================================================
    # EntityStoreProtocol - Statistics
    # =========================================================================

    def entity_count(self) -> int:
        """Get total number of entities."""
        row = self._fetchone("SELECT COUNT(*) as cnt FROM entities")
        return row["cnt"] if row else 0

    def listing_count(self) -> int:
        """Get total number of listings."""
        row = self._fetchone("SELECT COUNT(*) as cnt FROM listings")
        return row["cnt"] if row else 0

    def security_count(self) -> int:
        """Get total number of securities."""
        row = self._fetchone("SELECT COUNT(*) as cnt FROM securities")
        return row["cnt"] if row else 0

    def claim_count(self) -> int:
        """Get total number of claims."""
        row = self._fetchone("SELECT COUNT(*) as cnt FROM claims")
        return row["cnt"] if row else 0

    # =========================================================================
    # Search (Tier 1: LIKE-based)
    # =========================================================================

    def search_entities(
        self,
        query: str,
        limit: int = 10,
    ) -> list[tuple[Entity, float]]:
        """
        Search entities by name or identifier.

        Args:
            query: Search query.
            limit: Maximum results.

        Returns:
            List of (entity, similarity_score) tuples.
            Score is 1.0 for exact match, lower for LIKE matches.
        """
        query_lower = query.lower().strip()
        results: list[tuple[Entity, float]] = []
        seen_ids: set[str] = set()

        # Check CIK first
        is_cik, cik_normalized = looks_like_cik(query)
        if is_cik:
            for entity in self.get_entities_by_cik(cik_normalized):
                if entity.entity_id not in seen_ids:
                    results.append((entity, 1.0))
                    seen_ids.add(entity.entity_id)
                    if len(results) >= limit:
                        return results

        # Check ticker
        is_ticker, ticker_normalized = looks_like_ticker(query)
        if is_ticker:
            for entity in self.get_entities_by_ticker(ticker_normalized):
                if entity.entity_id not in seen_ids:
                    results.append((entity, 1.0))
                    seen_ids.add(entity.entity_id)
                    if len(results) >= limit:
                        return results

        # Check exact name match
        rows = self._fetchall(
            "SELECT * FROM entities WHERE LOWER(primary_name) = ? LIMIT ?",
            (query_lower, limit - len(results)),
        )
        for row in rows:
            entity = self._row_to_entity(row)
            entity = self._follow_redirects(entity)
            if entity.entity_id not in seen_ids:
                results.append((entity, 1.0))
                seen_ids.add(entity.entity_id)

        if len(results) >= limit:
            return results

        # LIKE search for partial matches
        rows = self._fetchall(
            "SELECT * FROM entities WHERE LOWER(primary_name) LIKE ? LIMIT ?",
            (f"%{query_lower}%", limit - len(results)),
        )
        for row in rows:
            entity = self._row_to_entity(row)
            entity = self._follow_redirects(entity)
            if entity.entity_id not in seen_ids:
                # Lower score for LIKE matches
                results.append((entity, 0.7))
                seen_ids.add(entity.entity_id)

        return results

    # =========================================================================
    # Internal Methods
    # =========================================================================

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
                logger.warning(
                    f"Redirect cycle detected: {entity.entity_id} -> {current.redirect_to}"
                )
                return current

            target = self.get_entity_raw(current.redirect_to)
            if not target:
                logger.warning(f"Broken redirect: {current.entity_id} -> {current.redirect_to}")
                return current

            seen.add(current.redirect_to)
            current = target

        logger.warning(f"Max redirect depth reached for {entity.entity_id}")
        return current

    # =========================================================================
    # Knowledge Graph: Asset Operations (v2.2.4)
    # Uses mappers module for database-agnostic domain conversion
    # =========================================================================

    def save_asset(self, asset: "Asset") -> None:
        """Save or update an asset."""
        from entityspine.stores.mappers import asset_to_row

        row = asset_to_row(asset)
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO assets (
                    asset_id, asset_type, name, description, owner_entity_id,
                    operator_entity_id, geo_id, address_id, status,
                    source_system, source_id, captured_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["asset_id"],
                    row["asset_type"],
                    row["name"],
                    row["description"],
                    row["owner_entity_id"],
                    row["operator_entity_id"],
                    row["geo_id"],
                    row["address_id"],
                    row["status"],
                    row["source_system"],
                    row["source_id"],
                    row["captured_at"],
                    row["created_at"],
                    row["updated_at"],
                ),
            )
            conn.commit()

    def get_asset(self, asset_id: str) -> Optional["Asset"]:
        """Get asset by ID."""
        from entityspine.stores.mappers import row_to_asset

        row = self._fetchone("SELECT * FROM assets WHERE asset_id = ?", (asset_id,))
        return row_to_asset(dict(row)) if row else None

    def get_assets_by_owner(self, entity_id: str) -> list["Asset"]:
        """Get all assets owned by an entity."""
        from entityspine.stores.mappers import row_to_asset

        rows = self._fetchall(
            "SELECT * FROM assets WHERE owner_entity_id = ?",
            (entity_id,),
        )
        return [row_to_asset(dict(row)) for row in rows]

    def asset_count(self) -> int:
        """Get total number of assets."""
        row = self._fetchone("SELECT COUNT(*) as cnt FROM assets")
        return row["cnt"] if row else 0

    # =========================================================================
    # Knowledge Graph: Contract Operations (v2.2.4)
    # Uses mappers module for database-agnostic domain conversion
    # =========================================================================

    def save_contract(self, contract: "Contract") -> None:
        """Save or update a contract."""
        from entityspine.stores.mappers import contract_to_row

        row = contract_to_row(contract)
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO contracts (
                    contract_id, contract_type, title, effective_date,
                    termination_date, status, value_usd, source_system,
                    source_id, filing_id, captured_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["contract_id"],
                    row["contract_type"],
                    row["title"],
                    row["effective_date"],
                    row["termination_date"],
                    row["status"],
                    row["value_usd"],
                    row["source_system"],
                    row["source_id"],
                    row["filing_id"],
                    row["captured_at"],
                    row["created_at"],
                    row["updated_at"],
                ),
            )
            conn.commit()

    def get_contract(self, contract_id: str) -> Optional["Contract"]:
        """Get contract by ID."""
        from entityspine.stores.mappers import row_to_contract

        row = self._fetchone("SELECT * FROM contracts WHERE contract_id = ?", (contract_id,))
        return row_to_contract(dict(row)) if row else None

    def contract_count(self) -> int:
        """Get total number of contracts."""
        row = self._fetchone("SELECT COUNT(*) as cnt FROM contracts")
        return row["cnt"] if row else 0

    # =========================================================================
    # Knowledge Graph: Product Operations (v2.2.4)
    # Uses mappers module for database-agnostic domain conversion
    # =========================================================================

    def save_product(self, product: "Product") -> None:
        """Save or update a product."""
        from entityspine.stores.mappers import product_to_row

        row = product_to_row(product)
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO products (
                    product_id, product_type, name, description, owner_entity_id,
                    status, source_system, source_id, captured_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["product_id"],
                    row["product_type"],
                    row["name"],
                    row["description"],
                    row["owner_entity_id"],
                    row["status"],
                    row["source_system"],
                    row["source_id"],
                    row["captured_at"],
                    row["created_at"],
                    row["updated_at"],
                ),
            )
            conn.commit()

    def get_product(self, product_id: str) -> Optional["Product"]:
        """Get product by ID."""
        from entityspine.stores.mappers import row_to_product

        row = self._fetchone("SELECT * FROM products WHERE product_id = ?", (product_id,))
        return row_to_product(dict(row)) if row else None

    def get_products_by_owner(self, entity_id: str) -> list["Product"]:
        """Get all products owned by an entity."""
        from entityspine.stores.mappers import row_to_product

        rows = self._fetchall(
            "SELECT * FROM products WHERE owner_entity_id = ?",
            (entity_id,),
        )
        return [row_to_product(dict(row)) for row in rows]

    def product_count(self) -> int:
        """Get total number of products."""
        row = self._fetchone("SELECT COUNT(*) as cnt FROM products")
        return row["cnt"] if row else 0

    # =========================================================================
    # Knowledge Graph: Brand Operations (v2.2.4)
    # Uses mappers module for database-agnostic domain conversion
    # =========================================================================

    def save_brand(self, brand: "Brand") -> None:
        """Save or update a brand."""
        from entityspine.stores.mappers import brand_to_row

        row = brand_to_row(brand)
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO brands (
                    brand_id, name, owner_entity_id, description,
                    source_system, source_id, captured_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["brand_id"],
                    row["name"],
                    row["owner_entity_id"],
                    row["description"],
                    row["source_system"],
                    row["source_id"],
                    row["captured_at"],
                    row["created_at"],
                    row["updated_at"],
                ),
            )
            conn.commit()

    def get_brand(self, brand_id: str) -> Optional["Brand"]:
        """Get brand by ID."""
        from entityspine.stores.mappers import row_to_brand

        row = self._fetchone("SELECT * FROM brands WHERE brand_id = ?", (brand_id,))
        return row_to_brand(dict(row)) if row else None

    def get_brands_by_owner(self, entity_id: str) -> list["Brand"]:
        """Get all brands owned by an entity."""
        from entityspine.stores.mappers import row_to_brand

        rows = self._fetchall(
            "SELECT * FROM brands WHERE owner_entity_id = ?",
            (entity_id,),
        )
        return [row_to_brand(dict(row)) for row in rows]

    def brand_count(self) -> int:
        """Get total number of brands."""
        row = self._fetchone("SELECT COUNT(*) as cnt FROM brands")
        return row["cnt"] if row else 0

    # =========================================================================
    # Knowledge Graph: Event Operations (v2.2.4)
    # Uses mappers module for database-agnostic domain conversion
    # =========================================================================

    def save_event(self, event: "Event") -> None:
        """Save or update an event."""
        from entityspine.stores.mappers import event_to_row

        row = event_to_row(event)
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO kg_events (
                    event_id, event_type, title, description, status,
                    occurred_on, announced_on, payload, evidence_filing_id,
                    evidence_section_id, evidence_snippet, confidence,
                    source_system, source_id, captured_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["event_id"],
                    row["event_type"],
                    row["title"],
                    row["description"],
                    row["status"],
                    row["occurred_on"],
                    row["announced_on"],
                    row["payload"],
                    row["evidence_filing_id"],
                    row["evidence_section_id"],
                    row["evidence_snippet"],
                    row["confidence"],
                    row["source_system"],
                    row["source_id"],
                    row["captured_at"],
                    row["created_at"],
                    row["updated_at"],
                ),
            )
            conn.commit()

    def get_event(self, event_id: str) -> Optional["Event"]:
        """Get event by ID."""
        from entityspine.stores.mappers import row_to_event

        row = self._fetchone("SELECT * FROM kg_events WHERE event_id = ?", (event_id,))
        return row_to_event(dict(row)) if row else None

    def get_events_by_type(self, event_type: "EventType") -> list["Event"]:
        """Get all events of a specific type."""
        from entityspine.stores.mappers import row_to_event

        type_value = event_type.value if hasattr(event_type, "value") else event_type
        rows = self._fetchall(
            "SELECT * FROM kg_events WHERE event_type = ?",
            (type_value,),
        )
        return [row_to_event(dict(row)) for row in rows]

    def event_count(self) -> int:
        """Get total number of events."""
        row = self._fetchone("SELECT COUNT(*) as cnt FROM kg_events")
        return row["cnt"] if row else 0

    # =========================================================================
    # Knowledge Graph: Geo Operations (v2.2.4)
    # Geographic hierarchy (country → state → city)
    # =========================================================================

    def save_geo(self, geo: "Geo") -> None:
        """Save or update a geographic location."""

        now = datetime.now(UTC).isoformat()
        geo_type = geo.geo_type.value if hasattr(geo.geo_type, "value") else geo.geo_type

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO geos (
                    geo_id, geo_type, name, iso_code, parent_geo_id,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    geo.geo_id,
                    geo_type,
                    geo.name,
                    geo.iso_code,
                    geo.parent_geo_id,
                    now,
                    now,
                ),
            )
            conn.commit()

    def get_geo(self, geo_id: str) -> Optional["Geo"]:
        """Get geographic location by ID."""
        from entityspine.domain import Geo, GeoType

        row = self._fetchone("SELECT * FROM geos WHERE geo_id = ?", (geo_id,))
        if not row:
            return None
        return Geo(
            geo_id=row["geo_id"],
            geo_type=GeoType(row["geo_type"]),
            name=row["name"],
            iso_code=row["iso_code"],
            parent_geo_id=row["parent_geo_id"],
        )

    def geo_count(self) -> int:
        """Get total number of geographic locations."""
        row = self._fetchone("SELECT COUNT(*) as cnt FROM geos")
        return row["cnt"] if row else 0

    # =========================================================================
    # Knowledge Graph: Address Operations (v2.2.4)
    # Normalized addresses with hash for deduplication
    # =========================================================================

    def save_address(self, address: "Address") -> None:
        """Save or update an address."""

        now = datetime.now(UTC).isoformat()

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO addresses (
                    address_id, line1, line2, city, region, postal,
                    country, normalized_hash, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    address.address_id,
                    address.line1,
                    address.line2,
                    address.city,
                    address.region,
                    address.postal,
                    address.country,
                    address.normalized_hash,
                    now,
                    now,
                ),
            )
            conn.commit()

    def get_address(self, address_id: str) -> Optional["Address"]:
        """Get address by ID."""
        from entityspine.domain import Address

        row = self._fetchone("SELECT * FROM addresses WHERE address_id = ?", (address_id,))
        if not row:
            return None
        return Address(
            address_id=row["address_id"],
            line1=row["line1"],
            line2=row["line2"],
            city=row["city"],
            region=row["region"],
            postal=row["postal"],
            country=row["country"],
            normalized_hash=row["normalized_hash"],
        )

    def get_address_by_hash(self, normalized_hash: str) -> Optional["Address"]:
        """Get address by normalized hash for deduplication."""
        from entityspine.domain import Address

        row = self._fetchone(
            "SELECT * FROM addresses WHERE normalized_hash = ?",
            (normalized_hash,),
        )
        if not row:
            return None
        return Address(
            address_id=row["address_id"],
            line1=row["line1"],
            line2=row["line2"],
            city=row["city"],
            region=row["region"],
            postal=row["postal"],
            country=row["country"],
            normalized_hash=row["normalized_hash"],
        )

    def address_count(self) -> int:
        """Get total number of addresses."""
        row = self._fetchone("SELECT COUNT(*) as cnt FROM addresses")
        return row["cnt"] if row else 0

    def save_entity_address(
        self,
        entity_id: str,
        address_id: str,
        address_type: "AddressType",
    ) -> None:
        """Link an entity to an address."""

        now = datetime.now(UTC).isoformat()
        type_value = address_type.value if hasattr(address_type, "value") else address_type

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO entity_addresses (
                    entity_id, address_id, address_type,
                    captured_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (entity_id, address_id, type_value, now, now, now),
            )
            conn.commit()

    # =========================================================================
    # Knowledge Graph: RoleAssignment Operations (v2.2.4)
    # Person → Org role assignments with evidence
    # =========================================================================

    def save_role_assignment(self, role: "RoleAssignment") -> None:
        """Save or update a role assignment."""

        now = datetime.now(UTC).isoformat()
        role_type = role.role_type.value if hasattr(role.role_type, "value") else role.role_type

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO role_assignments (
                    role_assignment_id, person_entity_id, org_entity_id,
                    role_type, title, start_date, end_date, confidence,
                    captured_at, source_system, source_ref, filing_id,
                    section_id, snippet_hash, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    role.role_assignment_id,
                    role.person_entity_id,
                    role.org_entity_id,
                    role_type,
                    role.title,
                    role.start_date.isoformat() if role.start_date else None,
                    role.end_date.isoformat() if role.end_date else None,
                    role.confidence,
                    role.captured_at.isoformat() if hasattr(role.captured_at, "isoformat") else now,
                    role.source_system,
                    role.source_ref,
                    role.filing_id,
                    role.section_id,
                    role.snippet_hash,
                    now,
                    now,
                ),
            )
            conn.commit()

    def get_role_assignment(self, role_assignment_id: str) -> Optional["RoleAssignment"]:
        """Get role assignment by ID."""
        from datetime import date

        from entityspine.domain import RoleAssignment, RoleType

        row = self._fetchone(
            "SELECT * FROM role_assignments WHERE role_assignment_id = ?",
            (role_assignment_id,),
        )
        if not row:
            return None

        return RoleAssignment(
            role_assignment_id=row["role_assignment_id"],
            person_entity_id=row["person_entity_id"],
            org_entity_id=row["org_entity_id"],
            role_type=RoleType(row["role_type"]),
            title=row["title"],
            start_date=date.fromisoformat(row["start_date"]) if row["start_date"] else None,
            end_date=date.fromisoformat(row["end_date"]) if row["end_date"] else None,
            confidence=row["confidence"],
            captured_at=datetime.fromisoformat(row["captured_at"])
            if row["captured_at"]
            else datetime.now(UTC),
            source_system=row["source_system"] or "unknown",
            source_ref=row["source_ref"],
            filing_id=row["filing_id"],
            section_id=row["section_id"],
            snippet_hash=row["snippet_hash"],
        )

    def get_role_assignments_by_org(self, org_entity_id: str) -> list["RoleAssignment"]:
        """Get all role assignments for an organization."""
        from datetime import date

        from entityspine.domain import RoleAssignment, RoleType

        rows = self._fetchall(
            "SELECT * FROM role_assignments WHERE org_entity_id = ?",
            (org_entity_id,),
        )

        results = []
        for row in rows:
            results.append(
                RoleAssignment(
                    role_assignment_id=row["role_assignment_id"],
                    person_entity_id=row["person_entity_id"],
                    org_entity_id=row["org_entity_id"],
                    role_type=RoleType(row["role_type"]),
                    title=row["title"],
                    start_date=date.fromisoformat(row["start_date"]) if row["start_date"] else None,
                    end_date=date.fromisoformat(row["end_date"]) if row["end_date"] else None,
                    confidence=row["confidence"],
                    captured_at=datetime.fromisoformat(row["captured_at"])
                    if row["captured_at"]
                    else datetime.now(UTC),
                    source_system=row["source_system"] or "unknown",
                    source_ref=row["source_ref"],
                    filing_id=row["filing_id"],
                    section_id=row["section_id"],
                    snippet_hash=row["snippet_hash"],
                )
            )
        return results

    def get_role_assignments_by_person(self, person_entity_id: str) -> list["RoleAssignment"]:
        """Get all role assignments for a person."""
        from datetime import date

        from entityspine.domain import RoleAssignment, RoleType

        rows = self._fetchall(
            "SELECT * FROM role_assignments WHERE person_entity_id = ?",
            (person_entity_id,),
        )

        results = []
        for row in rows:
            results.append(
                RoleAssignment(
                    role_assignment_id=row["role_assignment_id"],
                    person_entity_id=row["person_entity_id"],
                    org_entity_id=row["org_entity_id"],
                    role_type=RoleType(row["role_type"]),
                    title=row["title"],
                    start_date=date.fromisoformat(row["start_date"]) if row["start_date"] else None,
                    end_date=date.fromisoformat(row["end_date"]) if row["end_date"] else None,
                    confidence=row["confidence"],
                    captured_at=datetime.fromisoformat(row["captured_at"])
                    if row["captured_at"]
                    else datetime.now(UTC),
                    source_system=row["source_system"] or "unknown",
                    source_ref=row["source_ref"],
                    filing_id=row["filing_id"],
                    section_id=row["section_id"],
                    snippet_hash=row["snippet_hash"],
                )
            )
        return results

    def role_assignment_count(self) -> int:
        """Get total number of role assignments."""
        row = self._fetchone("SELECT COUNT(*) as cnt FROM role_assignments")
        return row["cnt"] if row else 0

    # =========================================================================
    # Knowledge Graph: Relationship Operations (v2.2.4)
    # Generic NodeRef → NodeRef relationships
    # =========================================================================

    def save_relationship(self, rel: "Relationship") -> None:
        """Save or update a generic relationship."""

        now = datetime.now(UTC).isoformat()
        rel_type = (
            rel.relationship_type.value
            if hasattr(rel.relationship_type, "value")
            else rel.relationship_type
        )

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO relationships (
                    relationship_id, source_kind, source_id, target_kind, target_id,
                    relationship_type, subtype, valid_from, valid_to, captured_at,
                    source_system, source_ref, confidence, evidence_filing_id,
                    evidence_section_id, evidence_excerpt_hash, evidence_snippet,
                    metrics, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    rel.relationship_id,
                    rel.source_ref.kind.value
                    if hasattr(rel.source_ref.kind, "value")
                    else rel.source_ref.kind,
                    rel.source_ref.id,
                    rel.target_ref.kind.value
                    if hasattr(rel.target_ref.kind, "value")
                    else rel.target_ref.kind,
                    rel.target_ref.id,
                    rel_type,
                    rel.subtype,
                    rel.valid_from.isoformat() if rel.valid_from else None,
                    rel.valid_to.isoformat() if rel.valid_to else None,
                    rel.captured_at.isoformat() if hasattr(rel.captured_at, "isoformat") else now,
                    rel.source_system,
                    rel.source_id,
                    rel.confidence,
                    rel.evidence_filing_id,
                    rel.evidence_section_id,
                    rel.evidence_excerpt_hash,
                    rel.evidence_snippet,
                    json.dumps(dict(rel.metrics)) if rel.metrics else None,
                    now,
                    now,
                ),
            )
            conn.commit()

    def get_relationship(self, relationship_id: str) -> Optional["Relationship"]:
        """Get relationship by ID."""
        from datetime import date

        from entityspine.domain import NodeKind, NodeRef, Relationship, RelationshipType

        row = self._fetchone(
            "SELECT * FROM relationships WHERE relationship_id = ?",
            (relationship_id,),
        )
        if not row:
            return None

        return Relationship(
            relationship_id=row["relationship_id"],
            source_ref=NodeRef(
                kind=NodeKind(row["source_kind"]),
                id=row["source_id"],
            ),
            target_ref=NodeRef(
                kind=NodeKind(row["target_kind"]),
                id=row["target_id"],
            ),
            relationship_type=RelationshipType(row["relationship_type"]),
            subtype=row["subtype"],
            valid_from=date.fromisoformat(row["valid_from"]) if row["valid_from"] else None,
            valid_to=date.fromisoformat(row["valid_to"]) if row["valid_to"] else None,
            captured_at=datetime.fromisoformat(row["captured_at"])
            if row["captured_at"]
            else datetime.now(UTC),
            source_system=row["source_system"] or "unknown",
            source_id=row["source_ref"],
            confidence=row["confidence"],
            evidence_filing_id=row["evidence_filing_id"],
            evidence_section_id=row["evidence_section_id"],
            evidence_excerpt_hash=row["evidence_excerpt_hash"],
            evidence_snippet=row["evidence_snippet"],
            metrics=json.loads(row["metrics"]) if row["metrics"] else None,
        )

    def get_relationships_by_source_id(
        self,
        source_id: str,
        limit: int = 100,
    ) -> list["Relationship"]:
        """Get all relationships from a source node (by its ID)."""
        from datetime import date

        from entityspine.domain import NodeKind, NodeRef, Relationship, RelationshipType

        rows = self._fetchall(
            "SELECT * FROM relationships WHERE source_id = ? LIMIT ?",
            (source_id, limit),
        )

        results = []
        for row in rows:
            results.append(
                Relationship(
                    relationship_id=row["relationship_id"],
                    source_ref=NodeRef(
                        kind=NodeKind(row["source_kind"]),
                        id=row["source_id"],
                    ),
                    target_ref=NodeRef(
                        kind=NodeKind(row["target_kind"]),
                        id=row["target_id"],
                    ),
                    relationship_type=RelationshipType(row["relationship_type"]),
                    subtype=row["subtype"],
                    valid_from=date.fromisoformat(row["valid_from"]) if row["valid_from"] else None,
                    valid_to=date.fromisoformat(row["valid_to"]) if row["valid_to"] else None,
                    captured_at=datetime.fromisoformat(row["captured_at"])
                    if row["captured_at"]
                    else datetime.now(UTC),
                    source_system=row["source_system"] or "unknown",
                    source_id=row["source_ref"],
                    confidence=row["confidence"],
                    evidence_filing_id=row["evidence_filing_id"],
                    evidence_section_id=row["evidence_section_id"],
                    evidence_excerpt_hash=row["evidence_excerpt_hash"],
                    evidence_snippet=row["evidence_snippet"],
                    metrics=json.loads(row["metrics"]) if row["metrics"] else None,
                )
            )
        return results

    def relationship_count(self) -> int:
        """Get total number of generic relationships."""
        row = self._fetchone("SELECT COUNT(*) as cnt FROM relationships")
        return row["cnt"] if row else 0

    def get_contract(self, contract_id: str) -> Optional["Contract"]:
        """Get contract by ID."""
        from entityspine.stores.mappers import row_to_contract

        row = self._fetchone(
            "SELECT * FROM contracts WHERE contract_id = ?",
            (contract_id,),
        )
        return row_to_contract(dict(row)) if row else None

    # =========================================================================
    # Case Operations (v2.2.4)
    # =========================================================================

    def save_case(self, case: "Case") -> None:
        """Save or update a legal case."""
        from entityspine.stores.mappers import case_to_row

        row = case_to_row(case)
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO cases (
                    case_id, case_type, case_number, title, status,
                    authority_entity_id, target_entity_id,
                    opened_date, closed_date, description,
                    source_system, source_ref, filing_id, captured_at,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["case_id"],
                    row["case_type"],
                    row["case_number"],
                    row["title"],
                    row["status"],
                    row["authority_entity_id"],
                    row["target_entity_id"],
                    row["opened_date"],
                    row["closed_date"],
                    row["description"],
                    row["source_system"],
                    row["source_ref"],
                    row["filing_id"],
                    row["captured_at"],
                    row["created_at"],
                    row["updated_at"],
                ),
            )
            conn.commit()

    def get_case(self, case_id: str) -> Optional["Case"]:
        """Get case by ID."""
        from entityspine.stores.mappers import row_to_case

        row = self._fetchone(
            "SELECT * FROM cases WHERE case_id = ?",
            (case_id,),
        )
        return row_to_case(dict(row)) if row else None

    def get_cases_by_target(self, target_entity_id: str) -> list["Case"]:
        """Get all cases involving a target entity."""
        from entityspine.stores.mappers import row_to_case

        rows = self._fetchall(
            "SELECT * FROM cases WHERE target_entity_id = ?",
            (target_entity_id,),
        )
        return [row_to_case(dict(row)) for row in rows]

    def get_cases_by_authority(self, authority_entity_id: str) -> list["Case"]:
        """Get all cases from an authority (court/regulator)."""
        from entityspine.stores.mappers import row_to_case

        rows = self._fetchall(
            "SELECT * FROM cases WHERE authority_entity_id = ?",
            (authority_entity_id,),
        )
        return [row_to_case(dict(row)) for row in rows]

    def case_count(self) -> int:
        """Get total number of cases."""
        row = self._fetchone("SELECT COUNT(*) as cnt FROM cases")
        return row["cnt"] if row else 0

    # =========================================================================
    # EntityCluster Operations (v2.2.4) - Anti-Duplication
    # =========================================================================

    def save_cluster(self, cluster: "EntityCluster") -> None:
        """Save or update an entity cluster."""
        from entityspine.stores.mappers import cluster_to_row

        row = cluster_to_row(cluster)
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO entity_clusters (
                    cluster_id, reason, created_at, updated_at
                ) VALUES (?, ?, ?, ?)
                """,
                (row["cluster_id"], row["reason"], row["created_at"], row["updated_at"]),
            )
            conn.commit()

    def get_cluster(self, cluster_id: str) -> Optional["EntityCluster"]:
        """Get cluster by ID."""
        from entityspine.stores.mappers import row_to_cluster

        row = self._fetchone(
            "SELECT * FROM entity_clusters WHERE cluster_id = ?",
            (cluster_id,),
        )
        return row_to_cluster(dict(row)) if row else None

    def cluster_count(self) -> int:
        """Get total number of entity clusters."""
        row = self._fetchone("SELECT COUNT(*) as cnt FROM entity_clusters")
        return row["cnt"] if row else 0

    # =========================================================================
    # EntityClusterMember Operations (v2.2.4)
    # =========================================================================

    def save_cluster_member(self, member: "EntityClusterMember") -> None:
        """Save or update a cluster membership."""
        from entityspine.stores.mappers import cluster_member_to_row

        row = cluster_member_to_row(member)
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO entity_cluster_members (
                    cluster_id, entity_id, role, confidence, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    row["cluster_id"],
                    row["entity_id"],
                    row["role"],
                    row["confidence"],
                    row["created_at"],
                    row["updated_at"],
                ),
            )
            conn.commit()

    def get_cluster_members(self, cluster_id: str) -> list["EntityClusterMember"]:
        """Get all members of a cluster."""
        from entityspine.stores.mappers import row_to_cluster_member

        rows = self._fetchall(
            "SELECT * FROM entity_cluster_members WHERE cluster_id = ?",
            (cluster_id,),
        )
        return [row_to_cluster_member(dict(row)) for row in rows]

    def get_clusters_for_entity(self, entity_id: str) -> list["EntityClusterMember"]:
        """Get all cluster memberships for an entity."""
        from entityspine.stores.mappers import row_to_cluster_member

        rows = self._fetchall(
            "SELECT * FROM entity_cluster_members WHERE entity_id = ?",
            (entity_id,),
        )
        return [row_to_cluster_member(dict(row)) for row in rows]

    def cluster_member_count(self) -> int:
        """Get total number of cluster memberships."""
        row = self._fetchone("SELECT COUNT(*) as cnt FROM entity_cluster_members")
        return row["cnt"] if row else 0
