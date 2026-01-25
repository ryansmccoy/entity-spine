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

    IdentifierClaim is THE canonical mechanism for storing and managing
    identifiers (CIK, LEI, CUSIP, ISIN, TICKER, FIGI) in EntitySpine. Each
    claim represents a single assertion: "source X says identifier Y identifies
    entity/security/listing Z" with full provenance and temporal tracking.
    
    Manifesto:
        EntitySpine's claims-based identity model (Principle #2) recognizes that
        identifiers are NOT facts - they are assertions with provenance, confidence,
        and temporal validity. Consider:
        - SEC says Apple's CIK is 0000320193 (confidence: 1.0)
        - FactSet says Apple's entity ID is 000C7F-E (confidence: 0.95)
        - Bloomberg says AAPL's FIGI is BBG000B9XRY4 (confidence: 0.98)
        
        These are all CLAIMS about the same entity from different sources. When
        sources conflict (rare but it happens), confidence scores help resolve.
        Temporal validity (valid_from/valid_to) handles identifier changes:
        - FB ticker valid_to=2022-06-08
        - META ticker valid_from=2022-06-09
        
        Multi-vendor crosswalks are enabled by namespace: the same entity can have
        SEC claims, FactSet claims, and Bloomberg claims, enabling reconciliation.
    
    Architecture:
        ```
        ┌──────────────────────────────────────────────────────────┐
        │            Claims-Based Identity Resolution              │
        └──────────────────────────────────────────────────────────┘
        
        Query: "Who is CIK 0000320193?"
        
        ┌─────────────────────────┐
        │    IdentifierClaim      │
        │  scheme: CIK            │
        │  value: "0000320193"    │
        │  entity_id: "01HQ..."   │──► Entity: Apple Inc.
        │  namespace: SEC         │
        │  confidence: 1.0        │
        │  valid_from: 1980       │
        │  valid_to: null         │
        └─────────────────────────┘
        
        Multi-Vendor Crosswalk (same entity, different sources):
        ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
        │ Claim (SEC)  │  │Claim(FactSet)│  │Claim(Bloom.) │
        │ CIK: 320193  │  │ENTITY:000C7F │  │FIGI:BBG...   │
        │ conf: 1.0    │  │ conf: 0.95   │  │ conf: 0.98   │
        └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
               │                 │                 │
               └────────────┬────┴─────────────────┘
                            ▼
                    ┌─────────────┐
                    │   Entity    │ Apple Inc.
                    └─────────────┘
        
        Scheme-Scope Enforcement:
        ┌─────────────────────────────────────────────┐
        │ CIK, LEI, EIN        → entity_id (required) │
        │ CUSIP, ISIN, SEDOL   → security_id          │
        │ TICKER               → listing_id           │
        └─────────────────────────────────────────────┘
        ```
        Dependencies: None - stdlib only (dataclasses, datetime)
        Storage Tier: T0 (JSON), T1 (SQLite), T2 (DuckDB), T3 (PostgreSQL)
    
    Features:
        - Multi-vendor crosswalks via namespace (SEC, FACTSET, BLOOMBERG)
        - Temporal validity (valid_from/valid_to) separate from capture time
        - Scheme-scope enforcement (CIK→entity, ISIN→security, TICKER→listing)
        - Confidence scoring for conflict resolution
        - Auto-normalization of identifier values
        - Supersession support for identifier changes
        - Sanctions list support (OFAC_SDN, UN_SANCTIONS)
    
    Examples:
        >>> from entityspine.domain import IdentifierClaim, IdentifierScheme
        >>> from entityspine.domain.enums import VendorNamespace
        >>> # CIK claim (SEC identifier for entity)
        >>> cik_claim = IdentifierClaim(
        ...     scheme=IdentifierScheme.CIK,
        ...     value="0000320193",
        ...     entity_id="01HQ8X9ABC123",
        ...     namespace=VendorNamespace.SEC,
        ...     source="company_tickers.json",
        ... )
        >>> cik_claim.is_current
        True
        
        >>> # CUSIP claim (security identifier)
        >>> cusip_claim = IdentifierClaim(
        ...     scheme=IdentifierScheme.CUSIP,
        ...     value="037833100",
        ...     security_id="sec_apple_common",
        ...     namespace=VendorNamespace.FACTSET,
        ... )
        
        >>> # Temporal ticker claim (FB → META change)
        >>> from datetime import date
        >>> fb_claim = IdentifierClaim(
        ...     scheme=IdentifierScheme.TICKER,
        ...     value="FB",
        ...     listing_id="lst_meta_nasdaq",
        ...     valid_from=date(2012, 5, 18),
        ...     valid_to=date(2022, 6, 8),
        ... )
        >>> meta_claim = IdentifierClaim(
        ...     scheme=IdentifierScheme.TICKER,
        ...     value="META",
        ...     listing_id="lst_meta_nasdaq",
        ...     valid_from=date(2022, 6, 9),
        ... )
    
    Performance:
        - Construction: O(1), ~300ns (includes validation)
        - is_current: O(1), ~20ns
        - supersede(): O(1), ~300ns
        - Lookup by scheme+value: O(1) with index, O(n) without
    
    Guardrails:
        - Do NOT put identifiers directly on Entity/Security/Listing
          ✅ Instead: Use IdentifierClaim with appropriate target_id
        - Do NOT use entity_id for security-scoped schemes (CUSIP, ISIN)
          ✅ Instead: Use security_id for security identifiers
        - Do NOT ignore temporal validity for ticker lookups
          ✅ Instead: Check valid_from/valid_to for point-in-time resolution
        - Do NOT assume confidence=1.0 for all sources
          ✅ Instead: Assign appropriate confidence by source reliability
    
    Context:
        Problem: Identifiers change, conflict, and have different reliability
                 across vendors, making entity resolution error-prone.
        Solution: Claims-based model with provenance, confidence, and temporal
                  validity enables accurate cross-vendor reconciliation.
    
    Tags:
        - entity_resolution
        - claims_based_identity
        - multi_vendor_crosswalk
        - domain_model
        - temporal_validity
        - stdlib_only
    
    Doc-Types:
        - MANIFESTO (section: "Core Principles", priority: 10)
        - FEATURES (section: "Identifier Management", priority: 10)
        - API_REFERENCE (section: "Claim Model", priority: 10)

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

    # v2.3.4: Extended provenance and explainability
    provenance_id: str | None = None  # Link to Provenance record
    explanation_id: str | None = None  # Link to Explanation record

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
