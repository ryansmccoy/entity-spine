"""
IdentifierClaim model - Provenance-tracked identifier assertions.

v2.2.3 DESIGN PRINCIPLES:
1. IdentifierClaim is THE canonical source of truth for identifiers
2. Entity/Security/Listing may expose computed convenience properties
3. Claims track both observation time (captured_at) and validity time (valid_from/to)
4. Namespace distinguishes vendor sources (Bloomberg vs FactSet vs SEC, etc.)
5. Strict scheme-scope rules prevent invalid identifier assignments

A claim asserts that an identifier (CIK, LEI, ISIN, etc.) belongs to an object
during a specific time period. This enables:
- Tracking identifier changes over time
- Handling identifier reuse (e.g., tickers)
- Auditing identifier provenance
- Multi-vendor crosswalks
"""

from datetime import date, datetime
from enum import Enum

from pydantic import Field, field_validator, model_validator

from entityspine.adapters.pydantic.base import EntitySpineModel, generate_id
from entityspine.adapters.pydantic.validators import (
    IdentifierScope,
    VendorNamespace,
    get_scope_for_scheme,
    normalize_and_validate,
    validate_scheme_scope,
)
from entityspine.core.timestamps import utc_now


class IdentifierScheme(str, Enum):
    """
    Standard identifier schemes.

    Each scheme has an expected scope (entity, security, or listing).
    The IdentifierClaim validator enforces correct scope usage.
    """

    # Entity-scoped (legal identity)
    CIK = "cik"  # SEC Central Index Key → entity_id
    LEI = "lei"  # Legal Entity Identifier → entity_id
    EIN = "ein"  # Employer Identification Number → entity_id
    DUNS = "duns"  # D-U-N-S Number → entity_id

    # Security-scoped (financial instrument)
    ISIN = "isin"  # International Securities ID Number → security_id
    CUSIP = "cusip"  # CUSIP identifier → security_id
    SEDOL = "sedol"  # SEDOL identifier → security_id
    FIGI = "figi"  # Financial Instrument Global ID → security_id

    # Listing-scoped (exchange-specific)
    TICKER = "ticker"  # Stock ticker symbol → listing_id
    RIC = "ric"  # Reuters Instrument Code → listing_id

    # Flexible scope
    INTERNAL = "internal"  # Internal system ID → any
    OTHER = "other"  # Other identifier type → any


class ClaimStatus(str, Enum):
    """Status of an identifier claim."""

    ACTIVE = "active"  # Currently valid claim
    SUPERSEDED = "superseded"  # Replaced by newer claim
    REVOKED = "revoked"  # Explicitly invalidated
    DISPUTED = "disputed"  # Under review


class IdentifierClaim(EntitySpineModel):
    """
    Provenance-tracked identifier assertion.

    v2.2.3 DESIGN:
    - This is the CANONICAL source of truth for identifiers
    - Supports multi-vendor crosswalks via namespace
    - Separates observation time (captured_at) from validity time (valid_from/to)
    - Enforces scheme-scope rules (CIK→entity, ISIN→security, TICKER→listing)

    Time Semantics:
    - captured_at: When we observed/recorded this claim (always set)
    - valid_from/valid_to: When the identifier was/is actually valid (business time)
    - created_at/updated_at: Record timestamps (technical)

    Attributes:
        claim_id: ULID primary key.
        entity_id: Entity this claim is about (if entity-scoped scheme).
        security_id: Security this claim is about (if security-scoped scheme).
        listing_id: Listing this claim is about (if listing-scoped scheme).
        scheme: Type of identifier (cik, lei, isin, etc.).
        value: The identifier value (normalized).
        namespace: Vendor/source namespace (sec, bloomberg, factset, etc.).
        source_ref: Optional reference ID in the source system.
        captured_at: When this claim was observed/captured.
        valid_from: When this identifier became valid (business time).
        valid_to: When this identifier ended (None if still valid).
        source: Human-readable source description.
        confidence: Confidence score 0.0-1.0.
        status: Claim status (active, superseded, etc.).
        notes: Additional notes about this claim.

    Example:
        >>> claim = IdentifierClaim(
        ...     entity_id="01HABC...",
        ...     scheme=IdentifierScheme.CIK,
        ...     value="320193",  # Will be normalized to 0000320193
        ...     namespace=VendorNamespace.SEC,
        ...     source="sec_edgar",
        ... )
        >>> claim.value  # Normalized
        '0000320193'
    """

    claim_id: str = Field(
        default_factory=generate_id,
        description="ULID primary key",
    )

    # Target: exactly one of entity_id, security_id, listing_id must be set
    # Scheme-scope rules determine which one is valid for each scheme
    entity_id: str | None = Field(
        default=None,
        description="Entity this claim is about (for entity-scoped schemes)",
    )
    security_id: str | None = Field(
        default=None,
        description="Security this claim is about (for security-scoped schemes)",
    )
    listing_id: str | None = Field(
        default=None,
        description="Listing this claim is about (for listing-scoped schemes)",
    )

    # The identifier itself
    scheme: IdentifierScheme = Field(
        ...,
        description="Type of identifier (determines valid scope)",
    )
    value: str = Field(
        ...,
        min_length=1,
        description="The identifier value (normalized by validators)",
    )

    # v2.2.3: Vendor namespace for multi-vendor crosswalks
    namespace: VendorNamespace = Field(
        default=VendorNamespace.INTERNAL,
        description="Vendor/source namespace (sec, bloomberg, factset, etc.)",
    )
    source_ref: str | None = Field(
        default=None,
        description="Reference ID in the source system",
    )

    # v2.2.3: Separate observation time from validity time
    captured_at: datetime = Field(
        default_factory=utc_now,
        description="When this claim was observed/captured (UTC)",
    )

    # Business validity period
    valid_from: date | None = Field(
        default=None,
        description="When identifier became valid (business time)",
    )
    valid_to: date | None = Field(
        default=None,
        description="When identifier ended (None if still valid)",
    )

    # Provenance
    source: str = Field(
        default="unknown",
        description="Human-readable source description",
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence score 0.0-1.0",
    )
    status: ClaimStatus = Field(
        default=ClaimStatus.ACTIVE,
        description="Claim status",
    )
    notes: str | None = Field(
        default=None,
        description="Additional notes about this claim",
    )

    # Record timestamps (technical, not business)
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

    @field_validator("value", mode="before")
    @classmethod
    def strip_value(cls, v: str) -> str:
        """Strip whitespace from value before other processing."""
        if isinstance(v, str):
            return v.strip()
        return v

    @model_validator(mode="after")
    def validate_claim(self) -> "IdentifierClaim":
        """
        Validate claim integrity:
        1. Exactly one target ID is set
        2. Scheme matches target type (CIK→entity, ISIN→security, etc.)
        3. Identifier value is valid for the scheme
        4. Date range is valid
        """
        # 1. Exactly one target
        targets = [self.entity_id, self.security_id, self.listing_id]
        non_null = [t for t in targets if t is not None]
        if len(non_null) != 1:
            raise ValueError(
                "Exactly one of entity_id, security_id, or listing_id must be set. "
                f"Got: entity_id={self.entity_id}, security_id={self.security_id}, "
                f"listing_id={self.listing_id}"
            )

        # 2. Validate scheme-scope match
        scheme_str = self.scheme.value if isinstance(self.scheme, Enum) else self.scheme
        is_valid, error = validate_scheme_scope(
            scheme_str,
            self.entity_id,
            self.security_id,
            self.listing_id,
        )
        if not is_valid:
            raise ValueError(error)

        # 3. Normalize and validate identifier value
        normalized, errors = normalize_and_validate(scheme_str, self.value)
        if errors:
            raise ValueError(f"Invalid {scheme_str.upper()} value: {'; '.join(errors)}")

        # Update value if normalization changed it (frozen model workaround)
        if normalized != self.value:
            object.__setattr__(self, "value", normalized)

        # 4. Validate date range
        if self.valid_from and self.valid_to and self.valid_from > self.valid_to:
            raise ValueError(
                f"valid_from ({self.valid_from}) cannot be after valid_to ({self.valid_to})"
            )

        return self

    @property
    def target_type(self) -> str:
        """Return which type of object this claim is about."""
        if self.entity_id:
            return "entity"
        elif self.security_id:
            return "security"
        elif self.listing_id:
            return "listing"
        return "unknown"

    @property
    def target_id(self) -> str | None:
        """Return the target object ID."""
        return self.entity_id or self.security_id or self.listing_id

    @property
    def expected_scope(self) -> IdentifierScope:
        """Return the expected scope for this claim's scheme."""
        scheme_str = self.scheme.value if isinstance(self.scheme, Enum) else self.scheme
        return get_scope_for_scheme(scheme_str)

    @property
    def is_active(self) -> bool:
        """Check if claim is currently active."""
        if self.status != ClaimStatus.ACTIVE:
            return False
        if self.valid_to is None:
            return True
        return date.today() <= self.valid_to

    def was_valid_on(self, check_date: date) -> bool:
        """
        Check if this claim was valid on a specific date.

        Args:
            check_date: Date to check

        Returns:
            True if claim was active and within validity period on that date
        """
        if self.status not in (ClaimStatus.ACTIVE, ClaimStatus.SUPERSEDED):
            return False
        if self.valid_from and check_date < self.valid_from:
            return False
        return not (self.valid_to and check_date > self.valid_to)

    def supersede(self, reason: str | None = None) -> "IdentifierClaim":
        """
        Create a superseded copy of this claim.

        Args:
            reason: Optional reason for superseding

        Returns:
            New IdentifierClaim with SUPERSEDED status
        """
        data = self.model_dump()
        data["status"] = ClaimStatus.SUPERSEDED
        data["updated_at"] = utc_now()
        if reason:
            data["notes"] = f"Superseded: {reason}" + (
                f" (was: {self.notes})" if self.notes else ""
            )
        return IdentifierClaim(**data)

    def with_update(self, **kwargs) -> "IdentifierClaim":
        """
        Create a new claim with updated fields.

        Args:
            **kwargs: Fields to update

        Returns:
            New IdentifierClaim with updated fields
        """
        data = self.model_dump()
        data.update(kwargs)
        data["updated_at"] = utc_now()
        return IdentifierClaim(**data)

    # =========================================================================
    # Domain Model Conversion (v2.2.3 - Pydantic as thin wrapper)
    # =========================================================================

    def to_domain(self) -> "entityspine.domain.IdentifierClaim":
        """
        Convert Pydantic model to domain dataclass.

        Returns:
            Domain IdentifierClaim dataclass
        """
        from entityspine.domain import (
            ClaimStatus as DomainClaimStatus,
        )
        from entityspine.domain import (
            IdentifierClaim as DomainClaim,
        )
        from entityspine.domain import (
            IdentifierScheme as DomainScheme,
        )
        from entityspine.domain import (
            VendorNamespace as DomainVendorNamespace,
        )

        # Handle enum values - Pydantic may store as str or Enum
        scheme_val = self.scheme.value if hasattr(self.scheme, "value") else self.scheme
        namespace_val = self.namespace.value if hasattr(self.namespace, "value") else self.namespace
        status_val = self.status.value if hasattr(self.status, "value") else self.status

        return DomainClaim(
            claim_id=self.claim_id,
            entity_id=self.entity_id,
            security_id=self.security_id,
            listing_id=self.listing_id,
            scheme=DomainScheme(scheme_val),
            value=self.value,
            namespace=DomainVendorNamespace(namespace_val),
            source_ref=self.source_ref,
            captured_at=self.captured_at,
            valid_from=self.valid_from,
            valid_to=self.valid_to,
            source=self.source,
            confidence=self.confidence,
            status=DomainClaimStatus(status_val),
            notes=self.notes,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_domain(cls, claim: "entityspine.domain.IdentifierClaim") -> "IdentifierClaim":
        """
        Create Pydantic model from domain dataclass.

        Args:
            claim: Domain IdentifierClaim dataclass

        Returns:
            Pydantic IdentifierClaim model
        """
        return cls(
            claim_id=claim.claim_id,
            entity_id=claim.entity_id,
            security_id=claim.security_id,
            listing_id=claim.listing_id,
            scheme=IdentifierScheme(claim.scheme.value),
            value=claim.value,
            namespace=VendorNamespace(claim.namespace.value),
            source_ref=claim.source_ref,
            captured_at=claim.captured_at,
            valid_from=claim.valid_from,
            valid_to=claim.valid_to,
            source=claim.source,
            confidence=claim.confidence,
            status=ClaimStatus(claim.status.value),
            notes=claim.notes,
            created_at=claim.created_at,
            updated_at=claim.updated_at,
        )
