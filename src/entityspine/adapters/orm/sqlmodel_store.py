"""
SQLModel Store - Modern Tier 1 storage backend.

Replaces raw SQL with SQLModel/SQLAlchemy ORM and repository pattern.

Tier 1 Characteristics:
- SQLite database with proper schema
- Full Entity/Security/Listing hierarchy
- Identifier claims with validity tracking
- LIKE pattern search (not full-text)
- No temporal/historical data (as_of will be IGNORED)

Architecture:
- Uses Pydantic models for domain (models/)
- Uses SQLModel tables for persistence (db/tables.py)
- Uses Repository pattern for data access (db/repositories/)

Example:
    >>> store = SqlModelStore("entities.db")
    >>> store.load_sec_json(data)
    >>> result = store.resolve("AAPL")
"""

import logging
from datetime import date, datetime
from pathlib import Path

from sqlmodel import Session

from entityspine.adapters.orm import create_sqlite_engine, create_tables
from entityspine.adapters.orm.repositories import (
    ClaimRepository,
    EntityRepository,
    ListingRepository,
    SecurityRepository,
)
from entityspine.adapters.orm.tables import ListingTable, SecurityTable
from entityspine.adapters.pydantic import (
    ClaimStatus,
    Entity,
    EntityStatus,
    EntityType,
    IdentifierClaim,
    IdentifierScheme,
    Listing,
    ResolutionResult,
    ResolutionTier,
    ResolutionWarning,
    Security,
    SecurityType,
    found_result,
    not_found_result,
)
from entityspine.core.timestamps import utc_now
from entityspine.core.ulid import generate_ulid

logger = logging.getLogger(__name__)


class SqlModelStore:
    """
    Modern Tier 1 SQLite store using SQLModel.

    Uses repository pattern for clean data access.

    Attributes:
        tier: Storage tier (always 1).
        tier_name: Human-readable tier name.
        supports_temporal: Whether temporal queries work (always False).
    """

    tier: int = 1
    tier_name: str = "SQLite (SQLModel)"
    supports_temporal: bool = False

    def __init__(self, db_path: str | Path):
        """
        Initialize SQLModel store.

        Args:
            db_path: Path to SQLite database file.
        """
        self.db_path = Path(db_path)
        self._engine = None
        self._initialized = False

    def initialize(self) -> None:
        """
        Initialize storage (create tables/indexes).

        Idempotent: safe to call multiple times.
        """
        if self._initialized:
            return

        # Ensure directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Create engine and tables
        self._engine = create_sqlite_engine(str(self.db_path))
        create_tables(self._engine)

        self._initialized = True
        logger.info(f"SqlModelStore initialized at {self.db_path}")

    def close(self) -> None:
        """Close database connection."""
        if self._engine:
            self._engine.dispose()
            self._engine = None
        self._initialized = False

    def _ensure_initialized(self) -> None:
        """Ensure store is initialized."""
        if not self._initialized:
            raise RuntimeError("Store not initialized. Call initialize() first.")

    # =========================================================================
    # Entity Operations (via EntityRepository)
    # =========================================================================

    def get_entity(self, entity_id: str) -> Entity | None:
        """Get entity by ID."""
        self._ensure_initialized()
        with Session(self._engine) as session:
            repo = EntityRepository(session)
            table = repo.get_by_id(entity_id)
            return repo.to_domain(table) if table else None

    def get_entity_by_cik(self, cik: str) -> Entity | None:
        """Get entity by CIK."""
        self._ensure_initialized()
        cik_padded = cik.zfill(10)
        with Session(self._engine) as session:
            repo = EntityRepository(session)
            table = repo.get_by_cik(cik_padded)
            return repo.to_domain(table) if table else None

    def get_entity_with_redirect(self, entity_id: str, max_depth: int = 10) -> Entity | None:
        """Get entity, following redirects."""
        self._ensure_initialized()
        with Session(self._engine) as session:
            repo = EntityRepository(session)
            table = repo.get_with_redirect(entity_id, max_depth)
            return repo.to_domain(table) if table else None

    def search_entities(self, query: str, limit: int = 10) -> list[Entity]:
        """Search entities by name."""
        self._ensure_initialized()
        with Session(self._engine) as session:
            repo = EntityRepository(session)
            tables = repo.search_by_name(query, limit)
            return [repo.to_domain(t) for t in tables]

    def save_entity(self, entity: Entity) -> Entity:
        """Save entity (insert or update)."""
        self._ensure_initialized()
        with Session(self._engine) as session:
            repo = EntityRepository(session)

            # Check if exists
            existing = repo.get_by_id(entity.entity_id)
            if existing:
                # Update
                table = repo.from_domain(entity)
                for key, value in table.model_dump(exclude_unset=True).items():
                    if key != "entity_id":
                        setattr(existing, key, value)
                existing.updated_at = utc_now()
                session.commit()
                session.refresh(existing)
                return repo.to_domain(existing)
            else:
                # Insert
                table = repo.from_domain(entity)
                session.add(table)
                session.commit()
                session.refresh(table)
                return repo.to_domain(table)

    def count_entities(self) -> int:
        """Get total entity count."""
        self._ensure_initialized()
        with Session(self._engine) as session:
            repo = EntityRepository(session)
            return repo.count()

    # =========================================================================
    # Security Operations (via SecurityRepository)
    # =========================================================================

    def get_securities_for_entity(self, entity_id: str) -> list[Security]:
        """Get all securities for an entity."""
        self._ensure_initialized()
        with Session(self._engine) as session:
            repo = SecurityRepository(session)
            tables = repo.get_by_entity(entity_id)
            return [repo.to_domain(t) for t in tables]

    def get_security_by_isin(self, isin: str) -> Security | None:
        """Get security by ISIN."""
        self._ensure_initialized()
        with Session(self._engine) as session:
            repo = SecurityRepository(session)
            table = repo.get_by_isin(isin)
            return repo.to_domain(table) if table else None

    def save_security(self, security: Security) -> Security:
        """Save security."""
        self._ensure_initialized()
        with Session(self._engine) as session:
            repo = SecurityRepository(session)

            existing = repo.get_by_id(security.security_id)
            if existing:
                table = repo.from_domain(security)
                for key, value in table.model_dump(exclude_unset=True).items():
                    if key != "security_id":
                        setattr(existing, key, value)
                existing.updated_at = utc_now()
                session.commit()
                session.refresh(existing)
                return repo.to_domain(existing)
            else:
                table = repo.from_domain(security)
                session.add(table)
                session.commit()
                session.refresh(table)
                return repo.to_domain(table)

    # =========================================================================
    # Listing Operations (via ListingRepository) - TICKER QUERIES HERE!
    # =========================================================================

    def get_listing_by_ticker(
        self,
        ticker: str,
        exchange: str | None = None,
    ) -> Listing | None:
        """
        Get listing by ticker symbol.

        TICKER BELONGS ON LISTING, NOT ENTITY!

        Args:
            ticker: Ticker symbol (e.g., "AAPL").
            exchange: Optional exchange filter.

        Returns:
            Listing if found, None otherwise.
        """
        self._ensure_initialized()
        with Session(self._engine) as session:
            repo = ListingRepository(session)
            tables = repo.get_by_ticker(ticker, exchange)
            if not tables:
                return None
            return repo.to_domain(tables[0])

    def get_listings_for_security(self, security_id: str) -> list[Listing]:
        """Get all listings for a security."""
        self._ensure_initialized()
        with Session(self._engine) as session:
            repo = ListingRepository(session)
            tables = repo.get_by_security(security_id)
            return [repo.to_domain(t) for t in tables]

    def save_listing(self, listing: Listing) -> Listing:
        """Save listing."""
        self._ensure_initialized()
        with Session(self._engine) as session:
            repo = ListingRepository(session)

            existing = repo.get_by_id(listing.listing_id)
            if existing:
                table = repo.from_domain(listing)
                for key, value in table.model_dump(exclude_unset=True).items():
                    if key != "listing_id":
                        setattr(existing, key, value)
                existing.updated_at = utc_now()
                session.commit()
                session.refresh(existing)
                return repo.to_domain(existing)
            else:
                table = repo.from_domain(listing)
                session.add(table)
                session.commit()
                session.refresh(table)
                return repo.to_domain(table)

    # =========================================================================
    # Claim Operations (via ClaimRepository)
    # =========================================================================

    def get_claims_for_entity(self, entity_id: str) -> list[IdentifierClaim]:
        """Get all claims for an entity."""
        self._ensure_initialized()
        with Session(self._engine) as session:
            repo = ClaimRepository(session)
            tables = repo.get_by_entity(entity_id)
            return [repo.to_domain(t) for t in tables]

    def find_entity_by_claim(
        self,
        scheme: str,
        value: str,
    ) -> Entity | None:
        """Find entity by identifier claim."""
        self._ensure_initialized()
        with Session(self._engine) as session:
            claim_repo = ClaimRepository(session)
            claims = claim_repo.get_by_scheme_value(scheme, value)

            if not claims:
                return None

            # Get entity from first matching claim
            entity_repo = EntityRepository(session)
            table = entity_repo.get_by_id(claims[0].entity_id)
            return entity_repo.to_domain(table) if table else None

    def save_claim(self, claim: IdentifierClaim) -> IdentifierClaim:
        """Save claim."""
        self._ensure_initialized()
        with Session(self._engine) as session:
            repo = ClaimRepository(session)

            existing = repo.get_by_id(claim.claim_id)
            if existing:
                table = repo.from_domain(claim)
                for key, value in table.model_dump(exclude_unset=True).items():
                    if key != "claim_id":
                        setattr(existing, key, value)
                existing.updated_at = utc_now()
                session.commit()
                session.refresh(existing)
                return repo.to_domain(existing)
            else:
                table = repo.from_domain(claim)
                session.add(table)
                session.commit()
                session.refresh(table)
                return repo.to_domain(table)

    # =========================================================================
    # Resolution (main use case)
    # =========================================================================

    def resolve(
        self,
        query: str,
        as_of: date | None = None,
    ) -> ResolutionResult:
        """
        Resolve a query to an entity.

        Supports:
        - CIK: 10-digit SEC Central Index Key
        - Ticker: Exchange ticker symbol (via Listing)
        - Name: Partial name match

        Args:
            query: Search query (CIK, ticker, or name).
            as_of: Date for temporal lookup (IGNORED in Tier 1).

        Returns:
            ResolutionResult with entity or not_found status.
        """
        self._ensure_initialized()

        start_time = utc_now()
        warnings = []

        # TIER CAPABILITY HONESTY: Warn if as_of ignored
        if as_of:
            warnings.append(ResolutionWarning.AS_OF_IGNORED)

        query_clean = query.strip()

        # Try CIK lookup (10 digits, possibly padded)
        if query_clean.isdigit():
            entity = self.get_entity_by_cik(query_clean)
            if entity:
                return found_result(
                    entity=entity,
                    query=query,
                    tier=ResolutionTier.TIER_1,
                    elapsed_ms=self._elapsed_ms(start_time),
                    warnings=warnings,
                )

        # Try ticker lookup via Listing
        listing = self.get_listing_by_ticker(query_clean)
        if listing:
            # Get security, then entity
            with Session(self._engine) as session:
                sec_repo = SecurityRepository(session)
                security_table = sec_repo.get_by_id(listing.security_id)
                if security_table:
                    security = sec_repo.to_domain(security_table)
                    entity_repo = EntityRepository(session)
                    entity_table = entity_repo.get_by_id(security_table.entity_id)
                    if entity_table:
                        entity = entity_repo.to_domain(entity_table)
                        return found_result(
                            entity=entity,
                            query=query,
                            tier=ResolutionTier.TIER_1,
                            elapsed_ms=self._elapsed_ms(start_time),
                            warnings=warnings,
                            security=security,
                            listing=listing,
                        )

        # Try name search
        entities = self.search_entities(query_clean, limit=1)
        if entities:
            return found_result(
                entity=entities[0],
                query=query,
                tier=ResolutionTier.TIER_1,
                elapsed_ms=self._elapsed_ms(start_time),
                warnings=warnings,
            )

        # Not found
        return not_found_result(
            query=query,
            tier=ResolutionTier.TIER_1,
            elapsed_ms=self._elapsed_ms(start_time),
            warnings=warnings,
        )

    def _elapsed_ms(self, start: datetime) -> float:
        """Calculate elapsed milliseconds."""
        return (utc_now() - start).total_seconds() * 1000

    # =========================================================================
    # Bulk Loading
    # =========================================================================

    def load_sec_json(self, data: dict) -> int:
        """
        Load entities from SEC company_tickers.json format.

        Creates Entity, Security, Listing, and Claim records.

        Args:
            data: Dict in SEC JSON format.

        Returns:
            Number of entities loaded.
        """
        self._ensure_initialized()
        count = 0

        # Handle both dict and list formats
        items = data.values() if isinstance(data, dict) else data

        with Session(self._engine) as session:
            entity_repo = EntityRepository(session)
            SecurityRepository(session)
            ListingRepository(session)
            claim_repo = ClaimRepository(session)

            for item in items:
                try:
                    cik_str = item.get("cik_str") or item.get("cik")
                    cik = str(cik_str).strip() if cik_str else None
                    ticker = item.get("ticker", "").strip() or None
                    name = item.get("title") or item.get("name", "Unknown")

                    if not cik:
                        continue

                    cik_padded = cik.zfill(10)

                    # Check if entity exists
                    existing = entity_repo.get_by_cik(cik_padded)
                    if existing:
                        # Maybe add listing
                        if ticker:
                            self._ensure_listing_for_entity(
                                session, existing.entity_id, name, ticker
                            )
                        continue

                    # Create entity
                    # v2.2.3: Use source_system/source_id instead of cik field
                    now = utc_now()
                    entity = Entity(
                        entity_id=generate_ulid(),
                        primary_name=name.strip(),
                        entity_type=EntityType.ORGANIZATION,
                        status=EntityStatus.ACTIVE,
                        source_system="sec",
                        source_id=cik_padded,
                        created_at=now,
                        updated_at=now,
                    )
                    entity_table = entity_repo.from_domain(entity)
                    session.add(entity_table)

                    # Create CIK claim
                    # v2.2.3: Use VendorNamespace.SEC
                    from entityspine.adapters.pydantic.validators import VendorNamespace

                    claim = IdentifierClaim(
                        claim_id=generate_ulid(),
                        entity_id=entity.entity_id,
                        scheme=IdentifierScheme.CIK,
                        value=cik_padded,
                        namespace=VendorNamespace.SEC,
                        source="sec_json",
                        confidence=1.0,
                        status=ClaimStatus.ACTIVE,
                    )
                    claim_table = claim_repo.from_domain(claim)
                    session.add(claim_table)

                    # Create security and listing if ticker present
                    if ticker:
                        self._create_security_and_listing(session, entity.entity_id, name, ticker)

                    count += 1

                except Exception as e:
                    logger.warning(f"Error loading entity: {e}")
                    continue

            session.commit()

        logger.info(f"Loaded {count} entities from SEC JSON")
        return count

    def _create_security_and_listing(
        self,
        session: Session,
        entity_id: str,
        name: str,
        ticker: str,
    ) -> tuple[str, str]:
        """Create Security and Listing records."""
        now = utc_now()
        ticker_normalized = ticker.upper().replace("-", ".")

        # Create security
        security_id = generate_ulid()
        security = SecurityTable(
            security_id=security_id,
            entity_id=entity_id,
            security_type=SecurityType.COMMON_STOCK.value,
            description=f"{name} Common Stock",
            metadata={},
            created_at=now,
            updated_at=now,
        )
        session.add(security)

        # Create listing (TICKER LIVES HERE!)
        listing_id = generate_ulid()
        listing = ListingTable(
            listing_id=listing_id,
            security_id=security_id,
            ticker=ticker_normalized,
            exchange="",  # Unknown from SEC data
            is_primary=True,
            metadata={},
            created_at=now,
            updated_at=now,
        )
        session.add(listing)

        return security_id, listing_id

    def _ensure_listing_for_entity(
        self,
        session: Session,
        entity_id: str,
        name: str,
        ticker: str,
    ) -> None:
        """Ensure a listing exists for the entity."""
        ticker_normalized = ticker.upper().replace("-", ".")

        # Check if listing already exists
        listing_repo = ListingRepository(session)
        existing = listing_repo.get_by_ticker(ticker_normalized)
        if existing:
            return

        # Get or create security
        security_repo = SecurityRepository(session)
        securities = security_repo.get_by_entity(entity_id)

        if securities:
            security_id = securities[0].security_id
        else:
            # Create security
            now = utc_now()
            security_id = generate_ulid()
            security = SecurityTable(
                security_id=security_id,
                entity_id=entity_id,
                security_type=SecurityType.COMMON_STOCK.value,
                description=f"{name} Common Stock",
                metadata={},
                created_at=now,
                updated_at=now,
            )
            session.add(security)

        # Create listing
        now = utc_now()
        listing_id = generate_ulid()
        listing = ListingTable(
            listing_id=listing_id,
            security_id=security_id,
            ticker=ticker_normalized,
            exchange="",
            is_primary=True,
            metadata={},
            created_at=now,
            updated_at=now,
        )
        session.add(listing)

    # =========================================================================
    # Context Manager Support
    # =========================================================================

    def __enter__(self) -> "SqlModelStore":
        """Context manager entry."""
        self.initialize()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()
