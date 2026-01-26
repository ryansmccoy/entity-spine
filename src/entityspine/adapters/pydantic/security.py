"""
Security model - Tradeable instrument.

v2.2.3 DESIGN PRINCIPLES:
1. Security represents a tradeable financial instrument (NOT where it trades)
2. Security has NO identifier convenience fields (isin, cusip, etc.) - use claims
3. Security links to Entity (issuer) and has Listings (where it trades)
4. source_system tracks where the RECORD came from, not identifier provenance

A Security represents a tradeable financial instrument:
- Apple Common Stock
- Tesla Series A Preferred
- US Treasury 10-Year Note

Security links to Entity (the issuer) and has Listings (where it trades).
"""

from datetime import datetime
from enum import Enum

from pydantic import Field

from entityspine.adapters.pydantic.base import EntitySpineModel, generate_id
from entityspine.core.timestamps import utc_now


class SecurityType(str, Enum):
    """Type of security."""

    COMMON_STOCK = "common_stock"
    PREFERRED_STOCK = "preferred_stock"
    ADR = "adr"  # American Depositary Receipt
    ETF = "etf"
    BOND = "bond"
    WARRANT = "warrant"
    OPTION = "option"
    UNIT = "unit"
    CONVERTIBLE = "convertible"
    RIGHT = "right"
    OTHER = "other"


class SecurityStatus(str, Enum):
    """Lifecycle status of a security."""

    ACTIVE = "active"  # Currently trading
    INACTIVE = "inactive"  # No longer trading
    SUSPENDED = "suspended"  # Temporarily suspended
    DELISTED = "delisted"  # Permanently delisted


class Security(EntitySpineModel):
    """
    Tradeable financial instrument.

    v2.2.3 DESIGN:
    - NO identifier convenience fields (isin, cusip, sedol, figi) - use IdentifierClaim
    - Links to Entity (issuer) via entity_id
    - Has multiple Listings (where/when it trades)
    - source_system tracks record provenance, not identifier sources

    Attributes:
        security_id: ULID primary key.
        entity_id: ULID of the issuing Entity.
        security_type: Type of security (common stock, ETF, etc.).
        description: Human-readable description.
        currency: Primary/issuance currency (ISO 4217).
        status: Lifecycle status.
        source_system: Where this RECORD came from.
        source_id: ID in the source system.
        created_at: Record creation timestamp (UTC).
        updated_at: Last update timestamp (UTC).

    Example:
        >>> security = Security(
        ...     entity_id="01HABC...",  # Apple Inc.
        ...     security_type=SecurityType.COMMON_STOCK,
        ...     description="Apple Inc. Common Stock",
        ...     currency="USD",
        ... )
        >>> # To add identifiers, create IdentifierClaim objects
        >>> claim = IdentifierClaim(
        ...     security_id=security.security_id,
        ...     scheme=IdentifierScheme.ISIN,
        ...     value="US0378331005",
        ...     namespace=VendorNamespace.OPENFIGI,
        ... )
    """

    security_id: str = Field(
        default_factory=generate_id,
        description="ULID primary key",
    )
    entity_id: str = Field(
        ...,
        description="ULID of the issuing Entity",
    )
    security_type: SecurityType = Field(
        default=SecurityType.COMMON_STOCK,
        description="Type of security",
    )
    description: str | None = Field(
        default=None,
        description="Human-readable description",
    )

    # Security details (NOT identifiers - those go in claims)
    currency: str | None = Field(
        default=None,
        description="Primary/issuance currency (ISO 4217)",
    )
    status: SecurityStatus = Field(
        default=SecurityStatus.ACTIVE,
        description="Lifecycle status",
    )

    # Record provenance (NOT identifier provenance - that's in claims)
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

    def with_update(self, **kwargs) -> "Security":
        """
        Create a new Security with updated fields.

        Args:
            **kwargs: Fields to update

        Returns:
            New Security with updated fields and updated_at timestamp
        """
        data = self.model_dump()
        data.update(kwargs)
        data["updated_at"] = utc_now()
        return Security(**data)

    # =========================================================================
    # Domain Model Conversion (v2.2.3 - Pydantic as thin wrapper)
    # =========================================================================

    def to_domain(self) -> "entityspine.domain.Security":
        """
        Convert Pydantic model to domain dataclass.

        Returns:
            Domain Security dataclass
        """
        from entityspine.domain import Security as DomainSecurity
        from entityspine.domain import SecurityStatus as DomainSecurityStatus
        from entityspine.domain import SecurityType as DomainSecurityType

        # Handle enum values - Pydantic may store as str or Enum
        security_type_val = (
            self.security_type.value if hasattr(self.security_type, "value") else self.security_type
        )
        status_val = self.status.value if hasattr(self.status, "value") else self.status

        return DomainSecurity(
            security_id=self.security_id,
            entity_id=self.entity_id,
            security_type=DomainSecurityType(security_type_val),
            description=self.description,
            currency=self.currency,
            status=DomainSecurityStatus(status_val),
            source_system=self.source_system,
            source_id=self.source_id,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_domain(cls, security: "entityspine.domain.Security") -> "Security":
        """
        Create Pydantic model from domain dataclass.

        Args:
            security: Domain Security dataclass

        Returns:
            Pydantic Security model
        """
        return cls(
            security_id=security.security_id,
            entity_id=security.entity_id,
            security_type=SecurityType(security.security_type.value),
            description=security.description,
            currency=security.currency,
            status=SecurityStatus(security.status.value),
            source_system=security.source_system,
            source_id=security.source_id,
            created_at=security.created_at,
            updated_at=security.updated_at,
        )
