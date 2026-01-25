"""
Security domain model (stdlib dataclass).

STDLIB ONLY - NO PYDANTIC.

v2.2.3 DESIGN:
- Security represents a financial instrument issued by an Entity
- NO identifier fields (isin, cusip, sedol, figi) - use IdentifierClaim
- Links to Entity via entity_id
"""

from dataclasses import dataclass, field, replace
from datetime import datetime

from entityspine.domain.enums import SecurityStatus, SecurityType
from entityspine.domain.timestamps import generate_ulid, utc_now


@dataclass(frozen=True, slots=True)
class Security:
    """
    Financial instrument issued by an Entity.

    v2.2.3 DESIGN:
    - NO identifier convenience fields - use IdentifierClaim
    - Immutable (frozen) for thread safety

    Attributes:
        security_id: ULID primary key
        entity_id: FK to issuing Entity
        security_type: Type of security
        description: Human-readable description
        currency: ISO 4217 currency code
        status: Lifecycle status
        source_system: Where this RECORD came from
        source_id: ID in the source system
        created_at: Record creation timestamp
        updated_at: Last update timestamp
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
        """Validate security after creation."""
        if not self.entity_id or not self.entity_id.strip():
            raise ValueError("entity_id cannot be empty")
        if not self.security_id or not self.security_id.strip():
            raise ValueError("security_id cannot be empty")

    def with_update(self, **kwargs) -> "Security":
        """Create a new Security with updated fields."""
        kwargs.setdefault("updated_at", utc_now())
        return replace(self, **kwargs)
