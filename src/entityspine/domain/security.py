"""
Security domain model (stdlib dataclass).

STDLIB ONLY - NO PYDANTIC.

Securities represent financial instruments issued by legal entities (companies,
governments, funds). Each Security belongs to exactly one Entity and can have
multiple Listings across different exchanges.

Design Principles:
    - **No identifier fields**: ISIN, CUSIP, SEDOL, FIGI stored via IdentifierClaim
    - **Entity ownership**: Every Security must have an issuing entity_id
    - **Immutable**: Frozen dataclass for thread safety and hashability
    - **Type flexibility**: Supports stocks, bonds, options, funds, etc.

Relationship Hierarchy:
    Entity (issuer) → Security (instrument) → Listing (where it trades)
    
    Example: Apple Inc. issues AAPL common stock which lists on NASDAQ and NYSE
    - Entity: Apple Inc. (entity_id: "01HQ...")
    - Security: AAPL Common Stock (security_id: "01HR...")  
    - Listings: NASDAQ:AAPL, NYSE:AAPL

Identifier Management:
    Identifiers like ISIN, CUSIP, SEDOL belong on IdentifierClaim with
    security_id as target. This enables:
    - Multi-vendor crosswalks (FactSet vs Bloomberg CUSIP)
    - Temporal validity (old CUSIP → new CUSIP on corporate actions)
    - Provenance tracking (where did this ISIN come from?)
"""

from dataclasses import dataclass, field, replace
from datetime import datetime

from entityspine.domain.enums import SecurityStatus, SecurityType
from entityspine.domain.timestamps import generate_ulid, utc_now


@dataclass(frozen=True, slots=True)
class Security:
    """
    Financial instrument issued by an Entity.
    
    Security is the middle tier of the Entity → Security → Listing hierarchy.
    It represents a tradeable instrument (stock, bond, option, etc.) without
    specifying where it trades.
    
    Design Principles:
        - **Immutable**: Frozen dataclass ensures thread safety
        - **No Identifiers**: Use IdentifierClaim for ISIN, CUSIP, SEDOL, FIGI
        - **Entity Link**: Every security has exactly one issuing entity
        - **Type Agnostic**: Supports equities, fixed income, derivatives, funds
    
    Attributes:
        security_id: ULID primary key (auto-generated if not provided).
        entity_id: FK to the issuing Entity (required).
        security_type: Classification (COMMON_STOCK, PREFERRED, BOND, etc.).
        description: Human-readable description of the security.
        currency: Primary currency (ISO 4217 code like 'USD', 'EUR').
        status: Lifecycle status (ACTIVE, DELISTED, MATURED).
        source_system: Data source that created this record.
        source_id: Identifier in the source system.
        created_at: Record creation timestamp.
        updated_at: Record last update timestamp.
    
    Examples:
        Create a common stock security:
        
        >>> from entityspine.domain import Security, SecurityType
        >>> aapl_stock = Security(
        ...     entity_id="01HQ8X9ABC123",  # Apple Inc.
        ...     security_type=SecurityType.COMMON_STOCK,
        ...     description="Apple Inc. Common Stock",
        ...     currency="USD",
        ...     source_system="sec",
        ... )
        
        Create a corporate bond:
        
        >>> bond = Security(
        ...     entity_id="01HQ8X9ABC123",
        ...     security_type=SecurityType.CORPORATE_BOND,
        ...     description="AAPL 3.85% 2046",
        ...     currency="USD",
        ...     source_system="factset",
        ... )
        
        Create an ETF security:
        
        >>> spy = Security(
        ...     entity_id="01HQ8X9DEF456",  # State Street
        ...     security_type=SecurityType.ETF,
        ...     description="SPDR S&P 500 ETF Trust",
        ...     currency="USD",
        ... )
        
        Link identifiers via IdentifierClaim:
        
        >>> from entityspine.domain import IdentifierClaim, IdentifierScheme
        >>> isin_claim = IdentifierClaim(
        ...     scheme=IdentifierScheme.ISIN,
        ...     value="US0378331005",
        ...     security_id=aapl_stock.security_id,
        ... )
    
    See Also:
        - Entity: The issuing company/organization
        - Listing: Where the security trades (exchange, ticker)
        - IdentifierClaim: For storing ISIN, CUSIP, SEDOL, FIGI
    """

    # Required fields
    entity_id: str

    # Primary key (auto-generated if not provided)
    security_id: str = field(default_factory=generate_ulid)

    # Security classification
    security_type: SecurityType = SecurityType.COMMON_STOCK
    description: str | None = None
    currency: str | None = None

    # Status
    status: SecurityStatus = SecurityStatus.ACTIVE

    # Record provenance
    source_system: str = "unknown"
    source_id: str | None = None

    # Timestamps
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def __post_init__(self):
        """Validate security fields after creation.
        
        Ensures required fields are present and non-empty.
        
        Raises:
            ValueError: If entity_id or security_id is empty.
        """
        if not self.entity_id or not self.entity_id.strip():
            raise ValueError("entity_id cannot be empty")
        if not self.security_id or not self.security_id.strip():
            raise ValueError("security_id cannot be empty")

    def with_update(self, **kwargs) -> "Security":
        """Create a new Security with updated fields.
        
        Since Security is immutable (frozen), this creates a copy with
        the specified fields changed. Automatically updates updated_at.
        
        Args:
            **kwargs: Fields to update (e.g., status=SecurityStatus.DELISTED).
            
        Returns:
            New Security instance with updated fields.
            
        Examples:
            >>> security = Security(entity_id="ent_123", description="Old")
            >>> updated = security.with_update(description="New description")
            >>> updated.description
            'New description'
        """
        kwargs.setdefault("updated_at", utc_now())
        return replace(self, **kwargs)
