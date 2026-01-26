"""
Listing repository for database operations.

CRITICAL: Listings are WHERE TICKER LIVES!
"""

from datetime import date

from sqlmodel import Session, or_, select

from entityspine.adapters.orm.repositories.base import BaseRepository
from entityspine.adapters.orm.tables import ListingTable
from entityspine.adapters.pydantic.listing import Listing


class ListingRepository(BaseRepository[ListingTable]):
    """
    Repository for Listing database operations.

    IMPORTANT: This is where ticker queries happen!
    """

    def __init__(self, session: Session):
        """Initialize with ListingTable model."""
        super().__init__(session, ListingTable)

    def get_by_ticker(
        self,
        ticker: str,
        exchange: str | None = None,
        mic: str | None = None,
        active_only: bool = True,
    ) -> list[ListingTable]:
        """
        Get listings by ticker symbol.

        THIS IS THE PRIMARY TICKER LOOKUP!

        Args:
            ticker: Ticker symbol (will be normalized).
            exchange: Filter by exchange.
            mic: Filter by MIC.
            active_only: Only return active listings.

        Returns:
            Matching listings.
        """
        # Normalize ticker: uppercase, dash to dot
        ticker_normalized = ticker.upper().strip().replace("-", ".")

        statement = select(ListingTable).where(ListingTable.ticker == ticker_normalized)

        if exchange:
            statement = statement.where(ListingTable.exchange == exchange.upper())

        if mic:
            statement = statement.where(ListingTable.mic == mic.upper())

        if active_only:
            # Active = no end_date or end_date >= today
            today = date.today()
            statement = statement.where(
                or_(
                    ListingTable.end_date.is_(None),
                    ListingTable.end_date >= today,
                )
            )

        return list(self._session.exec(statement).all())

    def get_by_security(self, security_id: str) -> list[ListingTable]:
        """Get all listings for a security."""
        statement = select(ListingTable).where(ListingTable.security_id == security_id)
        return list(self._session.exec(statement).all())

    def get_primary_listing(self, security_id: str) -> ListingTable | None:
        """Get the primary listing for a security."""
        statement = (
            select(ListingTable)
            .where(ListingTable.security_id == security_id)
            .where(ListingTable.is_primary)
        )
        return self._session.exec(statement).first()

    def get_active_on_date(self, ticker: str, check_date: date) -> list[ListingTable]:
        """Get listings that were active on a specific date."""
        ticker_normalized = ticker.upper().strip().replace("-", ".")

        statement = select(ListingTable).where(
            ListingTable.ticker == ticker_normalized,
            or_(ListingTable.start_date.is_(None), ListingTable.start_date <= check_date),
            or_(ListingTable.end_date.is_(None), ListingTable.end_date >= check_date),
        )
        return list(self._session.exec(statement).all())

    def to_domain(self, table: ListingTable) -> Listing:
        """Convert table row to domain model."""
        return Listing(
            listing_id=table.listing_id,
            security_id=table.security_id,
            ticker=table.ticker,
            exchange=table.exchange,
            mic=table.mic,
            start_date=table.start_date,
            end_date=table.end_date,
            is_primary=table.is_primary,
            currency=table.currency,
            created_at=table.created_at,
            updated_at=table.updated_at,
            metadata=table.metadata_ or {},
        )

    def from_domain(self, listing: Listing) -> ListingTable:
        """Convert domain model to table row."""
        return ListingTable(
            listing_id=listing.listing_id,
            security_id=listing.security_id,
            ticker=listing.ticker,
            exchange=listing.exchange,
            mic=listing.mic,
            start_date=listing.start_date,
            end_date=listing.end_date,
            is_primary=listing.is_primary,
            currency=listing.currency,
            created_at=listing.created_at,
            updated_at=listing.updated_at,
            metadata_=listing.metadata,
        )
