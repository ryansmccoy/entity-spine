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
    Provenance-tracked identifier assertion linking identifiers to entities.

    IdentifierClaim is the canonical mechanism for storing and managing
    identifiers (CIK, LEI, CUSIP, ISIN, TICKER, FIGI, etc.) in EntitySpine.
    Each claim represents a single assertion that "identifier X identifies
    entity/security/listing Y" with full provenance tracking.

    Key Design Features:
        - **Multi-vendor crosswalks**: namespace field distinguishes Bloomberg
          vs FactSet vs SEC vs internal identifiers for the same entity
        - **Temporal validity**: valid_from/valid_to track when identifier
          was actually valid (business time), separate from captured_at
        - **Scheme-scope enforcement**: CIK must point to entity_id, ISIN
          to security_id, TICKER to listing_id
        - **Confidence scoring**: Track reliability of identifier mappings
        - **Sanctions support**: Can store OFAC_SDN, UN_SANCTIONS identifiers

    Time Semantics:
        - captured_at: When we observed/recorded this claim (always set)
        - valid_from/valid_to: When the identifier was/is actually valid
        - created_at/updated_at: Record timestamps (technical metadata)

    Attributes:
        claim_id: ULID primary key.
        scheme: Type of identifier (CIK, LEI, CUSIP, ISIN, TICKER, etc.).
        value: The normalized identifier value.
        entity_id: Entity this claim is about (for entity-scoped schemes).
        security_id: Security this claim is about (for security-scoped schemes).
        listing_id: Listing this claim is about (for listing-scoped schemes).
        namespace: Vendor/source namespace (SEC, FACTSET, BLOOMBERG, etc.).
        source_ref: Reference ID in the source system.
        captured_at: When this claim was observed/captured.
        valid_from: When identifier became valid (business time).
        valid_to: When identifier ended (None if still valid).
        source: Human-readable source description.
        confidence: Confidence score 0.0-1.0.
        status: Claim status (ACTIVE, SUPERSEDED, REVOKED).
        notes: Additional notes.
        created_at: Record creation timestamp.
        updated_at: Last update timestamp.

    Examples:
        Create a CIK claim (SEC identifier for entity):

        >>> from entityspine.domain import IdentifierClaim, IdentifierScheme
        >>> from entityspine.domain.enums import VendorNamespace
        >>> cik_claim = IdentifierClaim(
        ...     scheme=IdentifierScheme.CIK,
        ...     value="0000320193",  # Will be normalized to 10 digits
        ...     entity_id="01HQ8X9ABC123",
        ...     namespace=VendorNamespace.SEC,
        ...     source="company_tickers.json",
        ... )
        >>> cik_claim.value
        '0000320193'
        >>> cik_claim.is_current
        True

        Create a LEI claim (Legal Entity Identifier):

        >>> lei_claim = IdentifierClaim(
        ...     scheme=IdentifierScheme.LEI,
        ...     value="HWUPKR0MPOU8FGXBT394",
        ...     entity_id="01HQ8X9ABC123",
        ...     namespace=VendorNamespace.GLEIF,
        ...     source="GLEIF Golden Copy",
        ...     confidence=1.0,
        ... )

        Create a CUSIP claim (security identifier):

        >>> cusip_claim = IdentifierClaim(
        ...     scheme=IdentifierScheme.CUSIP,
        ...     value="037833100",
        ...     security_id="sec_apple_common",
        ...     namespace=VendorNamespace.FACTSET,
        ...     source="FactSet Symbology",
        ... )

        Create a ticker claim with temporal validity:

        >>> from datetime import date
        >>> ticker_claim = IdentifierClaim(
        ...     scheme=IdentifierScheme.TICKER,
        ...     value="META",
        ...     listing_id="lst_meta_nasdaq",
        ...     namespace=VendorNamespace.EXCHANGE,
        ...     valid_from=date(2022, 6, 9),  # When FB became META
        ...     source="NASDAQ",
        ... )

        Create a multi-vendor crosswalk (same entity, different vendors):

        >>> # FactSet's identifier for Apple
        >>> factset_claim = IdentifierClaim(
        ...     scheme=IdentifierScheme.FACTSET_ENTITY_ID,
        ...     value="000C7F-E",
        ...     entity_id="01HQ8X9ABC123",
        ...     namespace=VendorNamespace.FACTSET,
        ... )
        >>>
        >>> # Bloomberg's identifier for same entity
        >>> bbg_claim = IdentifierClaim(
        ...     scheme=IdentifierScheme.FIGI,
        ...     value="BBG000B9XRY4",
        ...     security_id="sec_apple_common",
        ...     namespace=VendorNamespace.BLOOMBERG,
        ... )

        Create a sanctions list identifier (compliance):

        >>> sanction_claim = IdentifierClaim(
        ...     scheme=IdentifierScheme.OFAC_SDN,
        ...     value="SDN-12345",
        ...     entity_id="ent_sanctioned",
        ...     namespace=VendorNamespace.INTERNAL,
        ...     source="OFAC SDN List 2024-03-01",
        ...     valid_from=date(2024, 3, 1),
        ... )

        Supersede an old claim when identifier changes:

        >>> old_claim = IdentifierClaim(
        ...     scheme=IdentifierScheme.TICKER,
        ...     value="FB",
        ...     listing_id="lst_meta_nasdaq",
        ... )
        >>> superseded = old_claim.supersede("Ticker changed to META")
        >>> superseded.status
        <ClaimStatus.SUPERSEDED: 'superseded'>

    See Also:
        - Entity: The legal identity that identifiers point to
        - Security: Financial instruments with CUSIP, ISIN, SEDOL
        - Listing: Exchange listings with TICKER symbols
        - IdentifierScheme: All supported identifier types
        - VendorNamespace: Vendor sources for crosswalks
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
