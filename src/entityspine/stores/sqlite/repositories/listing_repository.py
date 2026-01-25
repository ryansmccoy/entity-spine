"""
Listing repository for SQLite store.

Handles all listing-related database operations following the Repository Pattern.
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from entityspine.core.timestamps import to_iso8601
from entityspine.domain import Listing

from ..converters import row_to_listing

if TYPE_CHECKING:
    from ..connection import SqliteConnectionManager


class ListingRepository:
    """
    Repository for Listing CRUD operations.
    
    Single Responsibility: Listing database operations only.
    Note: TICKER lives on Listing, not on Entity or Security.
    """

    def __init__(self, connection: SqliteConnectionManager):
        """
        Initialize repository with connection manager.
        
        Args:
            connection: Connection manager for database access.
        """
        self.conn = connection

    def save(self, listing: Listing) -> None:
        """
        Save or update a listing.
        
        Args:
            listing: Listing domain object to persist.
        """
        listing = listing.with_update()
        now_str = to_iso8601(listing.updated_at)

        self.conn.execute(
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

    def get_by_ticker(
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
            rows = self.conn.fetchall(
                "SELECT * FROM listings WHERE ticker = ? AND mic = ?",
                (ticker_normalized, mic),
            )
        else:
            rows = self.conn.fetchall(
                "SELECT * FROM listings WHERE ticker = ?",
                (ticker_normalized,),
            )

        return [row_to_listing(row) for row in rows]

    def get_by_security(self, security_id: str) -> list[Listing]:
        """
        Get all listings for a security.
        
        Args:
            security_id: Security ULID.
            
        Returns:
            All listings for the security.
        """
        rows = self.conn.fetchall(
            "SELECT * FROM listings WHERE security_id = ?",
            (security_id,),
        )
        return [row_to_listing(row) for row in rows]

    def count(self) -> int:
        """
        Count total listings.
        
        Returns:
            Number of listings in database.
        """
        row = self.conn.fetchone("SELECT COUNT(*) as cnt FROM listings")
        return row["cnt"] if row else 0
