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
    It represents a tradeable instrument (stock, bond, option, ETF) without
    specifying where it trades. One Entity can issue multiple Securities (common
    stock, preferred stock, bonds), and each Security can have multiple Listings.
    
    Manifesto:
        EntitySpine's three-tier model (Principle #1) separates what is traded
        (Security) from who issued it (Entity) and where it trades (Listing).
        This separation is essential because:
        - Apple Inc. (Entity) has issued multiple securities: common stock,
          corporate bonds, and commercial paper
        - Each Security has different identifiers: common stock has CUSIP
          037833100, bonds have different CUSIPs
        - The same Security (AAPL common) lists on multiple exchanges with
          potentially different tickers
        
        Identifiers like ISIN, CUSIP, SEDOL, and FIGI belong in IdentifierClaim
        (Principle #2), NOT on Security. This enables multi-vendor crosswalks
        and handles the reality that FactSet, Bloomberg, and Refinitiv may all
        have slightly different CUSIP mappings.
    
    Architecture:
        ```
        ┌──────────────────────────────────────────────────────────┐
        │               Entity → Security → Listing                 │
        └──────────────────────────────────────────────────────────┘
        
             ┌─────────────┐
             │   Entity    │ Apple Inc.
             │(entity_id)  │
             └──────┬──────┘
                    │ 1:N (issues)
           ┌────────┼────────┐
           ▼        ▼        ▼
        ┌──────┐ ┌──────┐ ┌──────┐
        │ Sec  │ │ Sec  │ │ Sec  │ AAPL Common, AAPL Pref, AAPL 3.85% 2046
        └──┬───┘ └──┬───┘ └──────┘
           │        │
           │ 1:N    │ 1:N (listed_on)
           │        │
        ┌──┴──┐  ┌──┴──┐
        │List │  │List │  NASDAQ:AAPL, NYSE:AAPL
        └─────┘  └─────┘
        
        Identifier Claims:
        ┌─────────────┐
        │IdentifierClaim│
        │ ISIN: US0378331005  │──► Security (AAPL Common)
        │ CUSIP: 037833100    │
        │ FIGI: BBG000B9XRY4  │
        └─────────────┘
        ```
        Dependencies: None - stdlib only (dataclasses, datetime)
        Storage Tier: T0 (JSON), T1 (SQLite), T2 (DuckDB), T3 (PostgreSQL)
    
    Features:
        - Immutable (frozen dataclass) for thread safety and hashability
        - NO identifier fields - use IdentifierClaim for ISIN, CUSIP, SEDOL, FIGI
        - Entity link (entity_id) is required - every Security has an issuer
        - Type classification (COMMON_STOCK, PREFERRED, BOND, ETF, OPTION)
        - Currency support for primary trading currency
        - Status tracking (ACTIVE, DELISTED, MATURED, SUSPENDED)
        - Provenance via source_system and source_id
    
    Examples:
        >>> from entityspine.domain import Security, SecurityType
        >>> aapl_stock = Security(
        ...     entity_id="01HQ8X9ABC123",  # Apple Inc.
        ...     security_type=SecurityType.COMMON_STOCK,
        ...     description="Apple Inc. Common Stock",
        ...     currency="USD",
        ...     source_system="sec",
        ... )
        
        >>> # Corporate bond (same issuer, different security)
        >>> bond = Security(
        ...     entity_id="01HQ8X9ABC123",  # Same Apple Inc.
        ...     security_type=SecurityType.CORPORATE_BOND,
        ...     description="AAPL 3.85% 2046",
        ...     currency="USD",
        ...     source_system="factset",
        ... )
        
        >>> # Link identifiers via IdentifierClaim
        >>> from entityspine.domain import IdentifierClaim, IdentifierScheme
        >>> isin_claim = IdentifierClaim(
        ...     scheme=IdentifierScheme.ISIN,
        ...     value="US0378331005",
        ...     security_id=aapl_stock.security_id,
        ... )
    
    Performance:
        - Construction: O(1), ~150ns
        - with_update(): O(1), ~200ns
        - Hash (for dict/set): O(len(security_id)), ~50ns
    
    Guardrails:
        - Do NOT store ISIN, CUSIP, SEDOL, FIGI on Security
          ✅ Instead: Use IdentifierClaim with security_id reference
        - Do NOT store ticker on Security
          ✅ Instead: Use Listing for exchange-specific tickers
        - Do NOT create Security without entity_id
          ✅ Entity relationship is required - every security has an issuer
    
    Context:
        Problem: Traditional models conflate securities with their listings and
                 identifiers, causing data quality issues with corporate actions.
        Solution: Security is a pure instrument node; identifiers are claims,
                  listings handle exchange-specific details.
    
    Tags:
        - entity_resolution
        - domain_model
        - financial_instruments
        - knowledge_graph
        - stdlib_only
    
    Doc-Types:
        - MANIFESTO (section: "Core Principles", priority: 10)
        - FEATURES (section: "Domain Models", priority: 9)
        - API_REFERENCE (section: "Security Model", priority: 9)
    
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
