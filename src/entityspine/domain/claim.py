"""
IdentifierClaim domain model (stdlib dataclass).

STDLIB ONLY - NO PYDANTIC.

v2.2.3 DESIGN:
- IdentifierClaim is THE canonical source of truth for identifiers
- Supports multi-vendor crosswalks via namespace
- Separates observation time (captured_at) from validity time (valid_from/to)
- Enforces scheme-scope rules (CIK→entity, ISIN→security, TICKER→listing)
"""

from dataclasses import dataclass, field, replace
from datetime import date, datetime

from entityspine.domain.enums import ClaimStatus, IdentifierScheme, VendorNamespace
from entityspine.domain.timestamps import generate_ulid, utc_now
from entityspine.domain.validators import (
    normalize_and_validate,
    validate_exactly_one_target,
    validate_scheme_scope,
)


@dataclass(frozen=True, slots=True)
class IdentifierClaim:
    """
    Provenance-tracked identifier assertion.

    v2.2.3 DESIGN:
    - This is the CANONICAL source of truth for identifiers
    - Supports multi-vendor crosswalks via namespace
    - Separates observation time (captured_at) from validity time (valid_from/to)
    - Enforces scheme-scope rules

    Time Semantics:
    - captured_at: When we observed/recorded this claim (always set)
    - valid_from/valid_to: When the identifier was/is actually valid (business time)
    - created_at/updated_at: Record timestamps (technical)

    Attributes:
        claim_id: ULID primary key
        entity_id: Entity this claim is about (if entity-scoped scheme)
        security_id: Security this claim is about (if security-scoped scheme)
        listing_id: Listing this claim is about (if listing-scoped scheme)
        scheme: Type of identifier
        value: The identifier value (normalized)
        namespace: Vendor/source namespace
        source_ref: Reference ID in the source system
        captured_at: When this claim was observed/captured
        valid_from: When identifier became valid (business time)
        valid_to: When identifier ended (None if still valid)
        source: Human-readable source description
        confidence: Confidence score 0.0-1.0
        status: Claim status
        notes: Additional notes
        created_at: Record creation timestamp
        updated_at: Last update timestamp
    """

    # Required fields
    scheme: IdentifierScheme
    value: str

    # Primary key (auto-generated if not provided)
    claim_id: str = field(default_factory=generate_ulid)

    # Target: exactly one must be set
    entity_id: str | None = None
    security_id: str | None = None
    listing_id: str | None = None

    # Vendor namespace for multi-vendor crosswalks
    namespace: VendorNamespace = VendorNamespace.INTERNAL
    source_ref: str | None = None

    # Observation time (when captured) vs validity time (when valid)
    captured_at: datetime = field(default_factory=utc_now)
    valid_from: date | None = None
    valid_to: date | None = None

    # Provenance
    source: str = "unknown"
    confidence: float = 1.0
    status: ClaimStatus = ClaimStatus.ACTIVE
    notes: str | None = None

    # Timestamps
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def __post_init__(self):
        """Validate claim after creation."""
        # 1. Exactly one target
        is_valid, error = validate_exactly_one_target(
            self.entity_id,
            self.security_id,
            self.listing_id,
        )
        if not is_valid:
            raise ValueError(error)

        # 2. Validate scheme-scope match
        scheme_str = self.scheme.value if isinstance(self.scheme, IdentifierScheme) else self.scheme
        is_valid, error = validate_scheme_scope(
            scheme_str,
            self.entity_id,
            self.security_id,
            self.listing_id,
        )
        if not is_valid:
            raise ValueError(error)

        # 3. Normalize and validate identifier value
        if not self.value or not self.value.strip():
            raise ValueError("value cannot be empty")

        normalized, errors = normalize_and_validate(scheme_str, self.value)
        if errors:
            raise ValueError(f"Invalid {scheme_str} value: {'; '.join(errors)}")

        # Update to normalized value (frozen dataclass workaround)
        object.__setattr__(self, "value", normalized)

        # 4. Validate confidence
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"confidence must be between 0.0 and 1.0, got {self.confidence}")

        # 5. Validate date range
        if self.valid_from and self.valid_to and self.valid_from > self.valid_to:
            raise ValueError(
                f"valid_from ({self.valid_from}) cannot be after valid_to ({self.valid_to})"
            )

    @property
    def target_id(self) -> str | None:
        """Get the target ID (whichever one is set)."""
        return self.entity_id or self.security_id or self.listing_id

    @property
    def target_type(self) -> str:
        """Get the target type as a string."""
        if self.entity_id:
            return "entity"
        if self.security_id:
            return "security"
        if self.listing_id:
            return "listing"
        return "unknown"

    @property
    def is_current(self) -> bool:
        """Check if claim is currently valid (no end date)."""
        return self.valid_to is None and self.status == ClaimStatus.ACTIVE

    def with_update(self, **kwargs) -> "IdentifierClaim":
        """Create a new IdentifierClaim with updated fields."""
        kwargs.setdefault("updated_at", utc_now())
        return replace(self, **kwargs)

    def supersede(self, reason: str | None = None) -> "IdentifierClaim":
        """Create a superseded version of this claim."""
        return self.with_update(
            status=ClaimStatus.SUPERSEDED,
            notes=reason or self.notes,
        )
