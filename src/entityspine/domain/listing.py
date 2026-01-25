"""
Listing domain model (stdlib dataclass).

STDLIB ONLY - NO PYDANTIC.

Listings represent where and when a Security trades. Each Listing connects
a Security to an exchange with a specific ticker symbol. This is critical
because:

1. **Tickers are exchange-scoped**: The same company may trade as "AAPL" 
   on NASDAQ but use different symbols on foreign exchanges
2. **Tickers change over time**: META was FB until June 2022
3. **Securities list on multiple exchanges**: Cross-listing is common

Relationship Hierarchy:
    Entity (issuer) → Security (instrument) → Listing (where it trades)
    
    Example: Apple Inc. common stock trading on NASDAQ
    - Entity: Apple Inc. (CIK: 0000320193)
    - Security: AAPL Common Stock (ISIN: US0378331005)
    - Listing: NASDAQ:AAPL (MIC: XNAS, since 1980-12-12)

Why Ticker Lives on Listing (not Entity or Security):
    - An entity might have multiple securities (common, preferred, bonds)
    - Each security can list on multiple exchanges with different tickers
    - Ticker changes (FB→META) are listing-level events, not entity-level
    - Point-in-time resolution requires knowing which ticker was valid when

MIC (Market Identifier Code):
    ISO 10383 MIC provides unambiguous exchange identification:
    - XNYS = New York Stock Exchange
    - XNAS = NASDAQ
    - XLON = London Stock Exchange
    Prefer MIC over exchange name strings for consistency.
"""

from dataclasses import dataclass, field, replace
from datetime import date, datetime

from entityspine.domain.enums import ListingStatus
from entityspine.domain.timestamps import generate_ulid, utc_now
from entityspine.domain.validators import (
    normalize_mic,
    normalize_ticker,
    validate_mic,
    validate_ticker,
)


@dataclass(frozen=True, slots=True)
class Listing:
    """
    Where and when a Security trades - **TICKER LIVES HERE**.
    
    Listing is the leaf of the Entity → Security → Listing hierarchy.
    It connects a tradeable instrument to a specific exchange with
    a ticker symbol, enabling point-in-time resolution of "what was
    the ticker for AAPL on NASDAQ in 2020?"
    
    Design Principles:
        - **Ticker is listing-scoped**: Not entity or security scoped
        - **Immutable**: Frozen dataclass for thread safety
        - **Temporal validity**: start_date/end_date track listing lifecycle
        - **MIC preferred**: Use ISO 10383 MIC for unambiguous exchange ID
        - **Auto-normalization**: Ticker/MIC normalized and validated on creation
    
    Attributes:
        listing_id: ULID primary key (auto-generated if not provided).
        security_id: FK to the Security being listed (required).
        ticker: Exchange-specific ticker symbol (required, auto-normalized).
        exchange: Exchange name (human-readable, e.g., "NASDAQ").
        mic: Market Identifier Code (ISO 10383, e.g., "XNAS").
        start_date: When this listing became active.
        end_date: When this listing ended (None if still active).
        is_primary: Whether this is the primary listing for the security.
        currency: Trading currency (ISO 4217 code).
        status: Lifecycle status (ACTIVE, DELISTED, SUSPENDED).
        source_system: Data source that created this record.
        source_id: Identifier in the source system.
        created_at: Record creation timestamp.
        updated_at: Record last update timestamp.
    
    Examples:
        Create a NASDAQ listing for Apple:
        
        >>> from entityspine.domain import Listing
        >>> aapl_nasdaq = Listing(
        ...     security_id="01HR8X9ABC123",
        ...     ticker="AAPL",
        ...     exchange="NASDAQ",
        ...     mic="XNAS",
        ...     start_date=date(1980, 12, 12),
        ...     is_primary=True,
        ...     currency="USD",
        ...     source_system="sec",
        ... )
        
        Handle ticker change (FB → META):
        
        >>> from datetime import date
        >>> # Old listing ends
        >>> fb_listing = Listing(
        ...     security_id="meta_common",
        ...     ticker="FB",
        ...     mic="XNAS",
        ...     start_date=date(2012, 5, 18),
        ...     end_date=date(2022, 6, 8),  # Last day as FB
        ...     source_system="exchange",
        ... )
        >>> # New listing begins
        >>> meta_listing = Listing(
        ...     security_id="meta_common",  # Same security
        ...     ticker="META",
        ...     mic="XNAS",
        ...     start_date=date(2022, 6, 9),  # First day as META
        ...     source_system="exchange",
        ... )
        
        Check if listing is active:
        
        >>> aapl_nasdaq.is_active
        True
        >>> fb_listing.is_active
        False
        
        Delist a security (e.g., going private):
        
        >>> delisted = aapl_nasdaq.delist(date(2030, 1, 1))
        >>> delisted.status
        <ListingStatus.DELISTED: 'delisted'>
    
    See Also:
        - Security: The instrument being listed
        - Entity: The issuing company
        - IdentifierClaim: For ticker history via scheme=TICKER
    """

    # Required fields
    security_id: str
    ticker: str

    # Primary key (auto-generated if not provided)
    listing_id: str = field(default_factory=generate_ulid)

    # Exchange info
    exchange: str = ""
    mic: str | None = None

    # Validity period
    start_date: date | None = None
    end_date: date | None = None

    # Flags
    is_primary: bool = False
    currency: str | None = None

    # Status
    status: ListingStatus = ListingStatus.ACTIVE

    # Record provenance
    source_system: str = "unknown"
    source_id: str | None = None

    # Timestamps
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def __post_init__(self):
        """Validate and normalize listing fields after creation.
        
        Performs:
        1. Validates required fields (security_id, listing_id, ticker)
        2. Normalizes ticker to uppercase, trimmed
        3. Validates ticker format (alphanumeric, reasonable length)
        4. Normalizes and validates MIC if provided
        
        Raises:
            ValueError: If required fields are empty or validation fails.
        """
        if not self.security_id or not self.security_id.strip():
            raise ValueError("security_id cannot be empty")
        if not self.listing_id or not self.listing_id.strip():
            raise ValueError("listing_id cannot be empty")

        # Normalize and validate ticker
        if not self.ticker:
            raise ValueError("ticker cannot be empty")
        normalized_ticker = normalize_ticker(self.ticker)
        is_valid, error = validate_ticker(normalized_ticker)
        if not is_valid:
            raise ValueError(error)
        # Update to normalized value (frozen dataclass workaround)
        object.__setattr__(self, "ticker", normalized_ticker)

        # Normalize MIC if provided
        if self.mic:
            normalized_mic = normalize_mic(self.mic)
            is_valid, error = validate_mic(normalized_mic)
            if not is_valid:
                raise ValueError(error)
            object.__setattr__(self, "mic", normalized_mic)

    @property
    def is_active(self) -> bool:
        """Check if this listing is currently active.
        
        A listing is active if it has no end_date and status is ACTIVE.
        
        Returns:
            True if the listing is currently tradeable.
            
        Examples:
            >>> active = Listing(security_id="sec", ticker="AAPL")
            >>> active.is_active
            True
            >>> delisted = active.delist()
            >>> delisted.is_active
            False
        """
        if self.end_date is not None:
            return False
        return self.status == ListingStatus.ACTIVE

    def with_update(self, **kwargs) -> "Listing":
        """Create a new Listing with updated fields.
        
        Since Listing is immutable (frozen), this creates a copy with
        the specified fields changed. Automatically updates updated_at.
        
        Args:
            **kwargs: Fields to update (e.g., exchange="NYSE").
            
        Returns:
            New Listing instance with updated fields.
        """
        kwargs.setdefault("updated_at", utc_now())
        return replace(self, **kwargs)

    def delist(self, end_date: date | None = None) -> "Listing":
        """Create a delisted version of this listing.
        
        Marks the listing as DELISTED with an end date. Used when
        a security stops trading on an exchange (going private,
        moving to another exchange, bankruptcy, etc.).
        
        Args:
            end_date: When the listing ended. Defaults to today.
            
        Returns:
            New Listing with DELISTED status and end_date set.
            
        Examples:
            >>> listing = Listing(security_id="sec", ticker="TWTR")
            >>> # Twitter delisted when taken private
            >>> delisted = listing.delist(date(2022, 10, 27))
            >>> delisted.status
            <ListingStatus.DELISTED: 'delisted'>
            >>> delisted.is_active
            False
        """
        from datetime import date as date_type

        return self.with_update(
            end_date=end_date or date_type.today(),
            status=ListingStatus.DELISTED,
        )
