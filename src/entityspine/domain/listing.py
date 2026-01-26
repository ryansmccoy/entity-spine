"""
Listing domain model (stdlib dataclass).

STDLIB ONLY - NO PYDANTIC.

v2.2.3 DESIGN:
- Listing represents where/when a Security trades
- TICKER BELONGS HERE (ticker is listing-scoped)
- Links to Security via security_id
"""

from dataclasses import dataclass, field, replace
from datetime import date, datetime
from typing import Optional

from entityspine.domain.enums import ListingStatus
from entityspine.domain.timestamps import utc_now, generate_ulid
from entityspine.domain.validators import normalize_ticker, normalize_mic, validate_ticker, validate_mic


@dataclass(frozen=True, slots=True)
class Listing:
    """
    Where/when a Security trades. TICKER LIVES HERE!
    
    v2.2.3 DESIGN:
    - ticker is listing-scoped (not entity-scoped)
    - Immutable (frozen) for thread safety
    
    Attributes:
        listing_id: ULID primary key
        security_id: FK to Security
        ticker: Ticker symbol (exchange-specific)
        exchange: Exchange name/code
        mic: Market Identifier Code (ISO 10383)
        start_date: When listing became active
        end_date: When listing ended (None if active)
        is_primary: Whether this is the primary listing
        currency: Trading currency
        status: Lifecycle status
        source_system: Where this RECORD came from
        source_id: ID in the source system
        created_at: Record creation timestamp
        updated_at: Last update timestamp
    """
    
    # Required fields
    security_id: str
    ticker: str
    
    # Primary key (auto-generated if not provided)
    listing_id: str = field(default_factory=generate_ulid)
    
    # Exchange info
    exchange: str = ""
    mic: Optional[str] = None
    
    # Validity period
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    
    # Flags
    is_primary: bool = False
    currency: Optional[str] = None
    
    # Status
    status: ListingStatus = ListingStatus.ACTIVE
    
    # Record provenance
    source_system: str = "unknown"
    source_id: Optional[str] = None
    
    # Timestamps
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    
    def __post_init__(self):
        """Validate and normalize listing after creation."""
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
        object.__setattr__(self, 'ticker', normalized_ticker)
        
        # Normalize MIC if provided
        if self.mic:
            normalized_mic = normalize_mic(self.mic)
            is_valid, error = validate_mic(normalized_mic)
            if not is_valid:
                raise ValueError(error)
            object.__setattr__(self, 'mic', normalized_mic)
    
    @property
    def is_active(self) -> bool:
        """Check if listing is currently active."""
        if self.end_date is not None:
            return False
        if self.status != ListingStatus.ACTIVE:
            return False
        return True
    
    def with_update(self, **kwargs) -> "Listing":
        """Create a new Listing with updated fields."""
        kwargs.setdefault("updated_at", utc_now())
        return replace(self, **kwargs)
    
    def delist(self, end_date: Optional[date] = None) -> "Listing":
        """Create a delisted version of this listing."""
        from datetime import date as date_type
        return self.with_update(
            end_date=end_date or date_type.today(),
            status=ListingStatus.DELISTED,
        )
