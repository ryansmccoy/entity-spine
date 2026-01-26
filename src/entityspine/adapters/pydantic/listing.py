"""
Listing model - Exchange-specific ticker.

v2.2.3 DESIGN PRINCIPLES:
1. Listing is WHERE/WHEN a Security trades with a specific ticker
2. TICKER BELONGS HERE - not on Entity or Security
3. Listing has validity period (start_date/end_date) for historical tracking
4. source_system tracks where the RECORD came from

CRITICAL: THIS IS WHERE TICKER BELONGS!

A Listing represents a Security trading on a specific exchange with a specific ticker.
Tickers belong here because:
1. Tickers are exchange-specific (AAPL on NASDAQ, different on LSE)
2. Tickers change over time (FB → META)
3. Tickers can be reused (different companies over time)
4. Tickers have validity periods (start_date, end_date)

Entity → Security → Listing hierarchy:
- Apple Inc. (Entity)
  └── Apple Common Stock (Security)
      ├── AAPL on NASDAQ (Listing, active)
      └── APC on Frankfurt (Listing, active)
"""

from datetime import date, datetime
from enum import Enum

from pydantic import Field, field_validator, model_validator

from entityspine.adapters.pydantic.base import EntitySpineModel, generate_id
from entityspine.adapters.pydantic.validators import (
    normalize_mic,
    normalize_ticker,
    validate_mic,
    validate_ticker,
)
from entityspine.core.timestamps import utc_now


class ListingStatus(str, Enum):
    """Lifecycle status of a listing."""

    ACTIVE = "active"  # Currently trading
    INACTIVE = "inactive"  # No longer trading
    SUSPENDED = "suspended"  # Temporarily suspended
    DELISTED = "delisted"  # Permanently delisted


class Listing(EntitySpineModel):
    """
    A listing of a Security on a specific exchange.

    v2.2.3 DESIGN:
    - THIS IS WHERE TICKER LIVES!
    - Links to Security via security_id
    - Has validity period for historical tracking
    - source_system tracks record provenance

    Attributes:
        listing_id: ULID primary key.
        security_id: ULID of the Security being listed.
        ticker: Trading symbol on this exchange (e.g., AAPL, BRK.B).
        exchange: Exchange identifier (e.g., NASDAQ, NYSE).
        mic: Market Identifier Code (ISO 10383).
        start_date: When this listing became active.
        end_date: When this listing ended (None if still active).
        is_primary: Whether this is the primary listing.
        currency: Trading currency (ISO 4217).
        status: Lifecycle status.
        source_system: Where this RECORD came from.
        source_id: ID in the source system.
        created_at: Record creation timestamp (UTC).
        updated_at: Last update timestamp (UTC).

    Example:
        >>> listing = Listing(
        ...     security_id="01HABC...",
        ...     ticker="AAPL",
        ...     exchange="NASDAQ",
        ...     mic="XNAS",
        ...     is_primary=True,
        ... )
    """

    listing_id: str = Field(
        default_factory=generate_id,
        description="ULID primary key",
    )
    security_id: str = Field(
        ...,
        description="ULID of the Security being listed",
    )
    ticker: str = Field(
        ...,
        min_length=1,
        description="Trading symbol (THIS IS WHERE TICKER LIVES!)",
    )
    exchange: str = Field(
        default="",
        description="Exchange identifier (may be empty if unknown)",
    )

    # Standard exchange identifiers
    mic: str | None = Field(
        default=None,
        description="Market Identifier Code (ISO 10383, 4 chars)",
    )

    # Validity period
    start_date: date | None = Field(
        default=None,
        description="When listing became active",
    )
    end_date: date | None = Field(
        default=None,
        description="When listing ended (None if still active)",
    )

    # Listing properties
    is_primary: bool = Field(
        default=False,
        description="Primary listing for this security?",
    )
    currency: str | None = Field(
        default=None,
        description="Trading currency (ISO 4217, 3 chars)",
    )

    # Lifecycle
    status: ListingStatus = Field(
        default=ListingStatus.ACTIVE,
        description="Lifecycle status",
    )

    # Record provenance
    source_system: str = Field(
        default="unknown",
        description="System that created this RECORD",
    )
    source_id: str | None = Field(
        default=None,
        description="ID in the source system",
    )

    # Timestamps
    created_at: datetime = Field(
        default_factory=utc_now,
        description="Record creation time (UTC)",
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        description="Last update time (UTC)",
    )

    # Extensible metadata
    metadata: dict[str, str] = Field(
        default_factory=dict,
        description="Additional metadata (string keys/values only)",
    )

    @field_validator("ticker", mode="before")
    @classmethod
    def normalize_ticker_field(cls, v: str) -> str:
        """Normalize ticker: uppercase, dash to dot, strip."""
        return normalize_ticker(v)

    @field_validator("mic", mode="before")
    @classmethod
    def normalize_mic_field(cls, v: str | None) -> str | None:
        """Normalize and validate MIC format."""
        if v is None:
            return None
        normalized = normalize_mic(v)
        is_valid, error = validate_mic(normalized)
        if not is_valid:
            raise ValueError(error)
        return normalized

    @field_validator("currency", mode="before")
    @classmethod
    def normalize_currency(cls, v: str | None) -> str | None:
        """Normalize and validate currency format (ISO 4217)."""
        if v is None:
            return None
        v = v.strip().upper()
        if len(v) != 3 or not v.isalpha():
            raise ValueError(f"Currency must be 3 letters (ISO 4217), got: {v!r}")
        return v

    @model_validator(mode="after")
    def validate_listing(self) -> "Listing":
        """Validate listing integrity."""
        # Validate ticker format
        is_valid, error = validate_ticker(self.ticker)
        if not is_valid:
            raise ValueError(error)

        # Validate date range
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError(
                f"start_date ({self.start_date}) cannot be after end_date ({self.end_date})"
            )
        return self

    @property
    def is_active(self) -> bool:
        """Check if listing is currently active."""
        if self.status != ListingStatus.ACTIVE:
            return False
        if self.end_date is None:
            return True
        return date.today() <= self.end_date

    def was_active_on(self, check_date: date) -> bool:
        """
        Check if listing was active on a specific date.

        Args:
            check_date: Date to check

        Returns:
            True if listing was active on that date
        """
        if self.start_date and check_date < self.start_date:
            return False
        return not (self.end_date and check_date > self.end_date)

    def with_update(self, **kwargs) -> "Listing":
        """
        Create a new Listing with updated fields.

        Args:
            **kwargs: Fields to update

        Returns:
            New Listing with updated fields and updated_at timestamp
        """
        data = self.model_dump()
        data.update(kwargs)
        data["updated_at"] = utc_now()
        return Listing(**data)

    def delist(self, end_date: date | None = None) -> "Listing":
        """
        Create a delisted version of this listing.

        Args:
            end_date: When the listing ended (defaults to today)

        Returns:
            New Listing with DELISTED status and end_date set
        """
        return self.with_update(
            status=ListingStatus.DELISTED,
            end_date=end_date or date.today(),
        )

    # =========================================================================
    # Domain Model Conversion (v2.2.3 - Pydantic as thin wrapper)
    # =========================================================================

    def to_domain(self) -> "entityspine.domain.Listing":
        """
        Convert Pydantic model to domain dataclass.

        Returns:
            Domain Listing dataclass
        """
        from entityspine.domain import Listing as DomainListing
        from entityspine.domain import ListingStatus as DomainListingStatus

        # Handle enum values - Pydantic may store as str or Enum
        status_val = self.status.value if hasattr(self.status, "value") else self.status

        return DomainListing(
            listing_id=self.listing_id,
            security_id=self.security_id,
            ticker=self.ticker,
            exchange=self.exchange,
            mic=self.mic,
            start_date=self.start_date,
            end_date=self.end_date,
            is_primary=self.is_primary,
            currency=self.currency,
            status=DomainListingStatus(status_val),
            source_system=self.source_system,
            source_id=self.source_id,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_domain(cls, listing: "entityspine.domain.Listing") -> "Listing":
        """
        Create Pydantic model from domain dataclass.

        Args:
            listing: Domain Listing dataclass

        Returns:
            Pydantic Listing model
        """
        return cls(
            listing_id=listing.listing_id,
            security_id=listing.security_id,
            ticker=listing.ticker,
            exchange=listing.exchange,
            mic=listing.mic,
            start_date=listing.start_date,
            end_date=listing.end_date,
            is_primary=listing.is_primary,
            currency=listing.currency,
            status=ListingStatus(listing.status.value),
            source_system=listing.source_system,
            source_id=listing.source_id,
            created_at=listing.created_at,
            updated_at=listing.updated_at,
        )


# Common exchange constants
class Exchange:
    """Standard exchange constants."""

    # US exchanges
    NYSE = "NYSE"  # MIC: XNYS
    NASDAQ = "NASDAQ"  # MIC: XNAS
    NYSE_ARCA = "NYSE_ARCA"  # MIC: ARCX
    AMEX = "AMEX"  # MIC: XASE

    # European exchanges
    LSE = "LSE"  # MIC: XLON
    EURONEXT = "EURONEXT"  # Various MICs
    XETRA = "XETRA"  # MIC: XETR

    # Asian exchanges
    TSE = "TSE"  # MIC: XJPX
    HKEX = "HKEX"  # MIC: XHKG
    SSE = "SSE"  # MIC: XSHG


# MIC to exchange mapping
MIC_TO_EXCHANGE: dict[str, str] = {
    "XNYS": Exchange.NYSE,
    "XNAS": Exchange.NASDAQ,
    "ARCX": Exchange.NYSE_ARCA,
    "XASE": Exchange.AMEX,
    "XLON": Exchange.LSE,
    "XETR": Exchange.XETRA,
    "XJPX": Exchange.TSE,
    "XHKG": Exchange.HKEX,
    "XSHG": Exchange.SSE,
}
