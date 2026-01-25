"""
Financial Observation domain models (stdlib dataclass).

STDLIB ONLY - NO PYDANTIC.

v2.2.5 DESIGN:
- Observation is a single data point with full provenance
- MetricSpec replaces ambiguous (code, variant) with orthogonal axes
- Time semantics: period (what measured), as_of (when known), captured_at (when ingested)
- ProvenanceRef + SourceKey split for document vs field lineage
- EstimateInfo for broker/consensus/guidance metadata
- Supersession chain instead of is_primary flag
- ValueWithUnits stores both raw and normalized values
- observation_key for deduplication/idempotency
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from hashlib import sha256

from entityspine.domain.enums import (
    # New enums added for observations
    AccountingBasis,
    EstimateScope,
    MetricCategory,
    MetricCode,
    ObservationType,
    PeriodType,
    PerShareType,
    Presentation,
    ProvenanceKind,
    ScopeType,
    # Existing enums we reuse
    VendorNamespace,
)
from entityspine.domain.timestamps import generate_ulid, utc_now

# =============================================================================
# MetricSpec - Structured metric specification
# =============================================================================


@dataclass(frozen=True, slots=True)
class MetricSpec:
    """
    Structured metric specification with orthogonal axes.
    
    Replaces ambiguous (MetricCode, variant) with explicit dimensions
    that don't conflate different concepts (basis vs presentation vs 
    share type vs scope).
    
    Example:
        EPS (diluted, vendor-normalized, GAAP, continuing ops):
        
        MetricSpec(
            code=MetricCode.EPS,
            category=MetricCategory.PER_SHARE,
            basis=AccountingBasis.GAAP,
            presentation=Presentation.VENDOR_NORMALIZED,
            per_share=PerShareType.DILUTED,
            scope=ScopeType.CONTINUING,
        )
    
    Attributes:
        code: Core metric identifier (REVENUE, EPS, etc.)
        category: Financial statement category
        basis: Accounting standard (GAAP, IFRS)
        presentation: How adjusted (reported, company_adj, vendor_norm)
        per_share: Share count basis for EPS-like (basic, diluted)
        scope: Operations scope (total, continuing, discontinued)
        custom_code: For unmapped metrics
        custom_name: Human-readable name for custom metrics
    """

    code: MetricCode
    category: MetricCategory = MetricCategory.OTHER
    basis: AccountingBasis = AccountingBasis.GAAP
    presentation: Presentation = Presentation.REPORTED
    per_share: PerShareType | None = None
    scope: ScopeType | None = None
    custom_code: str | None = None
    custom_name: str | None = None

    def __post_init__(self):
        """Validate MetricSpec."""
        # EPS-like metrics should have per_share specified
        if self.code in (MetricCode.EPS, MetricCode.DPS, MetricCode.BPS, MetricCode.CFPS):
            if self.per_share is None:
                # Default to diluted for EPS if not specified
                object.__setattr__(self, "per_share", PerShareType.DILUTED)

    def __str__(self) -> str:
        """Human-readable representation."""
        parts = [self.code.value.upper()]

        if self.per_share:
            parts.append(f"({self.per_share.value})")

        qualifiers = []
        if self.basis != AccountingBasis.GAAP:
            qualifiers.append(self.basis.value)
        if self.presentation != Presentation.REPORTED:
            qualifiers.append(self.presentation.value)
        if self.scope and self.scope != ScopeType.TOTAL:
            qualifiers.append(self.scope.value)

        if qualifiers:
            parts.append(f"[{', '.join(qualifiers)}]")

        return " ".join(parts)

    @property
    def canonical_key(self) -> str:
        """Stable key for grouping/matching."""
        parts = [
            self.code.value,
            self.category.value,
            self.basis.value,
            self.presentation.value,
            self.per_share.value if self.per_share else "na",
            self.scope.value if self.scope else "total",
        ]
        return ":".join(parts)

    # --- Factory methods for common metrics ---

    @classmethod
    def revenue(cls, presentation: Presentation = Presentation.REPORTED) -> "MetricSpec":
        return cls(
            code=MetricCode.REVENUE,
            category=MetricCategory.INCOME_STATEMENT,
            presentation=presentation,
        )

    @classmethod
    def eps_gaap_diluted(cls) -> "MetricSpec":
        return cls(
            code=MetricCode.EPS,
            category=MetricCategory.PER_SHARE,
            basis=AccountingBasis.GAAP,
            presentation=Presentation.REPORTED,
            per_share=PerShareType.DILUTED,
            scope=ScopeType.TOTAL,
        )

    @classmethod
    def eps_gaap_basic(cls) -> "MetricSpec":
        return cls(
            code=MetricCode.EPS,
            category=MetricCategory.PER_SHARE,
            basis=AccountingBasis.GAAP,
            presentation=Presentation.REPORTED,
            per_share=PerShareType.BASIC,
            scope=ScopeType.TOTAL,
        )

    @classmethod
    def eps_company_adjusted(cls, per_share: PerShareType = PerShareType.DILUTED) -> "MetricSpec":
        """Company-adjusted EPS (excludes stock comp, etc.)"""
        return cls(
            code=MetricCode.EPS,
            category=MetricCategory.PER_SHARE,
            basis=AccountingBasis.GAAP,
            presentation=Presentation.COMPANY_ADJUSTED,
            per_share=per_share,
            scope=ScopeType.TOTAL,
        )

    @classmethod
    def eps_vendor_normalized(cls, per_share: PerShareType = PerShareType.DILUTED) -> "MetricSpec":
        """Vendor-normalized EPS (FactSet, Bloomberg, etc.)"""
        return cls(
            code=MetricCode.EPS,
            category=MetricCategory.PER_SHARE,
            basis=AccountingBasis.GAAP,
            presentation=Presentation.VENDOR_NORMALIZED,
            per_share=per_share,
            scope=ScopeType.TOTAL,
        )

    @classmethod
    def net_income(cls, presentation: Presentation = Presentation.REPORTED) -> "MetricSpec":
        return cls(
            code=MetricCode.NET_INCOME,
            category=MetricCategory.INCOME_STATEMENT,
            presentation=presentation,
        )

    @classmethod
    def ebitda(cls, presentation: Presentation = Presentation.REPORTED) -> "MetricSpec":
        return cls(
            code=MetricCode.EBITDA,
            category=MetricCategory.INCOME_STATEMENT,
            presentation=presentation,
        )

    @classmethod
    def fcf(cls) -> "MetricSpec":
        return cls(
            code=MetricCode.FCF,
            category=MetricCategory.CASH_FLOW,
        )


# =============================================================================
# FiscalPeriod - What timeframe the number measures
# =============================================================================


@dataclass(frozen=True, slots=True)
class FiscalPeriod:
    """
    Fiscal period - WHAT timeframe the number measures.
    
    This is the measurement period, not when reported or captured.
    
    Examples:
        FY2025: full fiscal year 2025
        Q4 FY2025: fourth fiscal quarter 2025
        H1 2025: first half 2025
        TTM Q3 2025: trailing 12 months ending Q3 2025
    
    Attributes:
        fiscal_year: Year (e.g., 2025)
        period_type: Type of period (ANNUAL, QUARTERLY, etc.)
        quarter: 1-4 for quarterly
        half: 1-2 for semi-annual
        fye_month: Fiscal year end month (1-12, default 12)
        period_start: Start date if known
        period_end: End date if known
    """

    fiscal_year: int
    period_type: PeriodType
    quarter: int | None = None
    half: int | None = None
    fye_month: int = 12
    period_start: date | None = None
    period_end: date | None = None

    def __post_init__(self):
        """Validate FiscalPeriod."""
        if self.period_type == PeriodType.QUARTERLY:
            if self.quarter is None or not (1 <= self.quarter <= 4):
                raise ValueError(f"Quarterly period requires quarter 1-4, got {self.quarter}")
        if self.period_type == PeriodType.SEMI_ANNUAL:
            if self.half is None or not (1 <= self.half <= 2):
                raise ValueError(f"Semi-annual period requires half 1-2, got {self.half}")

    def __str__(self) -> str:
        if self.period_type == PeriodType.ANNUAL:
            return f"FY{self.fiscal_year}"
        elif self.period_type == PeriodType.QUARTERLY:
            return f"Q{self.quarter} FY{self.fiscal_year}"
        elif self.period_type == PeriodType.SEMI_ANNUAL:
            return f"H{self.half} {self.fiscal_year}"
        elif self.period_type == PeriodType.TTM:
            if self.quarter:
                return f"TTM Q{self.quarter} {self.fiscal_year}"
            return f"TTM {self.fiscal_year}"
        else:
            return f"{self.period_type.value} {self.fiscal_year}"

    @property
    def canonical_key(self) -> str:
        """Stable string for hashing/grouping."""
        return f"{self.fiscal_year}:{self.period_type.value}:{self.quarter or 0}:{self.half or 0}"

    @classmethod
    def annual(cls, year: int, fye_month: int = 12) -> "FiscalPeriod":
        return cls(fiscal_year=year, period_type=PeriodType.ANNUAL, fye_month=fye_month)

    @classmethod
    def quarterly(cls, year: int, quarter: int, fye_month: int = 12) -> "FiscalPeriod":
        return cls(fiscal_year=year, period_type=PeriodType.QUARTERLY, quarter=quarter, fye_month=fye_month)

    @classmethod
    def semi_annual(cls, year: int, half: int, fye_month: int = 12) -> "FiscalPeriod":
        return cls(fiscal_year=year, period_type=PeriodType.SEMI_ANNUAL, half=half, fye_month=fye_month)

    @classmethod
    def ttm(cls, year: int, ending_quarter: int | None = None) -> "FiscalPeriod":
        return cls(fiscal_year=year, period_type=PeriodType.TTM, quarter=ending_quarter)


# =============================================================================
# ProvenanceRef - Which document/snapshot produced this
# =============================================================================


@dataclass(frozen=True, slots=True)
class ProvenanceRef:
    """
    Document/snapshot that produced this observation.
    
    Answers: "Where did this value come from?"
    
    Separate from SourceKey (which dataset/field) because:
    - Same dataset can have multiple snapshots
    - Same document can produce multiple metrics
    - Lineage tracking needs document-level identity
    
    Attributes:
        provenance_id: ULID primary key
        kind: Type of provenance (sec_filing, vendor_snapshot, etc.)
        external_id: External identifier (accession number, URL hash, etc.)
        published_at: When source published this
        document_url: URL to source document
        document_title: Title of source document
        accession_number: SEC accession number (for filings)
        form_type: SEC form type (10-K, 10-Q, 8-K)
        filing_date: SEC filing date
        snapshot_date: Vendor snapshot date
        snapshot_version: Vendor snapshot version
    """

    kind: ProvenanceKind
    external_id: str

    provenance_id: str = field(default_factory=generate_ulid)
    published_at: datetime | None = None
    document_url: str | None = None
    document_title: str | None = None

    # SEC filing specific
    accession_number: str | None = None
    form_type: str | None = None
    filing_date: date | None = None

    # Vendor snapshot specific
    snapshot_date: date | None = None
    snapshot_version: str | None = None

    def __post_init__(self):
        """Validate ProvenanceRef."""
        if not self.external_id or not self.external_id.strip():
            raise ValueError("external_id cannot be empty")

    def __str__(self) -> str:
        return f"{self.kind.value}:{self.external_id}"

    @classmethod
    def sec_filing(
        cls,
        accession_number: str,
        form_type: str,
        filing_date: date,
    ) -> "ProvenanceRef":
        """Create SEC filing provenance."""
        return cls(
            kind=ProvenanceKind.SEC_FILING,
            external_id=accession_number,
            accession_number=accession_number,
            form_type=form_type,
            filing_date=filing_date,
            published_at=datetime.combine(filing_date, datetime.min.time()),
        )

    @classmethod
    def vendor_snapshot(
        cls,
        vendor: VendorNamespace,
        snapshot_date: date,
        snapshot_id: str | None = None,
    ) -> "ProvenanceRef":
        """Create vendor snapshot provenance."""
        ext_id = snapshot_id or f"{vendor.value}:{snapshot_date.isoformat()}"
        return cls(
            kind=ProvenanceKind.VENDOR_SNAPSHOT,
            external_id=ext_id,
            snapshot_date=snapshot_date,
        )

    @classmethod
    def press_release(
        cls,
        release_date: date,
        url: str | None = None,
        title: str | None = None,
    ) -> "ProvenanceRef":
        """Create press release provenance."""
        ext_id = url or f"pr:{release_date.isoformat()}"
        return cls(
            kind=ProvenanceKind.PRESS_RELEASE,
            external_id=ext_id,
            published_at=datetime.combine(release_date, datetime.min.time()),
            document_url=url,
            document_title=title,
        )

    @classmethod
    def broker_note(
        cls,
        firm: str,
        publication_date: date,
        note_id: str | None = None,
    ) -> "ProvenanceRef":
        """Create broker note provenance."""
        ext_id = note_id or f"{firm}:{publication_date.isoformat()}"
        return cls(
            kind=ProvenanceKind.BROKER_NOTE,
            external_id=ext_id,
            published_at=datetime.combine(publication_date, datetime.min.time()),
        )


# =============================================================================
# SourceKey - Which dataset/field produced this
# =============================================================================


@dataclass(frozen=True, slots=True)
class SourceKey:
    """
    Dataset/field that produced this observation.
    
    Answers: "What was the source field code?"
    
    Separate from ProvenanceRef because:
    - Multiple documents can reference same field
    - Field mapping is vendor-specific
    - Needed for crosswalk/reconciliation
    
    Attributes:
        vendor: Vendor namespace
        dataset: Dataset name (ff_fundamentals, bloomberg_estimates)
        field_name: Original field name (FF_SALES, IS_EPS)
        xbrl_namespace: XBRL namespace (us-gaap, ifrs-full)
        xbrl_tag: XBRL tag name (Revenues, NetIncomeLoss)
    """

    vendor: VendorNamespace | None = None
    dataset: str | None = None
    field_name: str | None = None
    xbrl_namespace: str | None = None
    xbrl_tag: str | None = None

    def __str__(self) -> str:
        if self.xbrl_tag:
            return f"{self.xbrl_namespace or 'xbrl'}:{self.xbrl_tag}"
        if self.vendor and self.field_name:
            return f"{self.vendor.value}:{self.field_name}"
        return self.field_name or self.dataset or "unknown"

    @classmethod
    def factset(cls, field_name: str, dataset: str = "ff_fundamentals") -> "SourceKey":
        return cls(vendor=VendorNamespace.FACTSET, dataset=dataset, field_name=field_name)

    @classmethod
    def bloomberg(cls, field_name: str, dataset: str = "bloomberg") -> "SourceKey":
        return cls(vendor=VendorNamespace.BLOOMBERG, dataset=dataset, field_name=field_name)

    @classmethod
    def sec_xbrl(cls, tag: str, namespace: str = "us-gaap") -> "SourceKey":
        return cls(vendor=VendorNamespace.SEC, xbrl_namespace=namespace, xbrl_tag=tag)


# =============================================================================
# EstimateInfo - Metadata for estimates
# =============================================================================


@dataclass(frozen=True, slots=True)
class EstimateInfo:
    """
    Metadata for estimate observations.
    
    Separate from actuals because estimates have additional dimensions:
    - Who produced it (broker, consensus provider)
    - What scope (individual, consensus)
    - Consensus statistics
    
    Attributes:
        scope: Estimate scope (broker, consensus, guidance)
        estimator: Firm name or provider (Cantor, Bloomberg consensus)
        analyst_id: Individual analyst ID if known
        analyst_name: Individual analyst name if known
        num_estimates: Number of estimates in consensus
        high_estimate: High estimate in consensus
        low_estimate: Low estimate in consensus
        guidance_type: Type of guidance (range, point)
        guidance_low: Low end of guidance range
        guidance_high: High end of guidance range
    """

    scope: EstimateScope
    estimator: str

    analyst_id: str | None = None
    analyst_name: str | None = None

    # Consensus statistics
    num_estimates: int | None = None
    high_estimate: Decimal | None = None
    low_estimate: Decimal | None = None

    # Company guidance
    guidance_type: str | None = None
    guidance_low: Decimal | None = None
    guidance_high: Decimal | None = None

    def __post_init__(self):
        """Validate EstimateInfo."""
        if not self.estimator or not self.estimator.strip():
            raise ValueError("estimator cannot be empty")

    def __str__(self) -> str:
        return f"{self.scope.value}:{self.estimator}"


# =============================================================================
# ValueWithUnits - Raw + normalized value storage
# =============================================================================


@dataclass(frozen=True, slots=True)
class ValueWithUnits:
    """
    Numeric value with explicit units and scale.
    
    Stores BOTH raw and normalized values to prevent:
    - "$119.2B" vs "119,200 (millions)" confusion
    - Currency conversion ambiguity
    - Scale mismatches in aggregation
    
    value_normalized is ALWAYS in base units (e.g., USD, not USD millions).
    
    Attributes:
        value_normalized: Value in base units (always use this for math)
        value_raw: Value as received from source
        unit: Unit type (USD, EUR, USD/share, %, shares)
        scale: Multiplier from raw to normalized (1, 1000, 1000000)
        currency: ISO 4217 currency code
    """

    value_normalized: Decimal
    value_raw: Decimal
    unit: str
    scale: int = 1
    currency: str | None = None

    def __post_init__(self):
        """Validate ValueWithUnits."""
        if self.scale <= 0:
            raise ValueError(f"scale must be positive, got {self.scale}")

    @classmethod
    def from_raw(
        cls,
        value_raw: Decimal,
        unit: str,
        scale: int = 1,
        currency: str | None = None,
    ) -> "ValueWithUnits":
        """Create from raw value, auto-normalizing."""
        return cls(
            value_normalized=value_raw * scale,
            value_raw=value_raw,
            unit=unit,
            scale=scale,
            currency=currency,
        )

    @classmethod
    def from_normalized(
        cls,
        value_normalized: Decimal,
        unit: str,
        scale: int = 1,
        currency: str | None = None,
    ) -> "ValueWithUnits":
        """Create from normalized value, computing raw."""
        return cls(
            value_normalized=value_normalized,
            value_raw=value_normalized / scale if scale != 0 else value_normalized,
            unit=unit,
            scale=scale,
            currency=currency,
        )

    def in_millions(self) -> Decimal:
        """Get value in millions."""
        return self.value_normalized / Decimal("1000000")

    def in_billions(self) -> Decimal:
        """Get value in billions."""
        return self.value_normalized / Decimal("1000000000")

    def __str__(self) -> str:
        if self.currency:
            return f"{self.currency} {self.value_normalized:,.2f}"
        return f"{self.value_normalized:,.2f} {self.unit}"


# =============================================================================
# Observation - Core observation model
# =============================================================================


@dataclass(frozen=True, slots=True)
class Observation:
    """
    A single financial data point with full provenance.
    
    Time semantics:
    - period: what timeframe the number measures (FY2025, Q4 FY2025)
    - as_of: when it was known (publication/acceptance time)
    - captured_at: when our system ingested it
    
    Provenance:
    - provenance_ref: which document/snapshot produced this
    - source_key: which dataset/field within that document
    - estimate_info: additional context for estimates
    
    Value:
    - value: normalized Decimal with units
    - stores both raw and normalized for auditability
    
    Identity:
    - observation_id: ULID primary key
    - observation_key: deterministic key for deduplication
    
    Supersession:
    - supersedes_id: observation this supersedes
    - superseded_by_id: observation that superseded this
    
    Attributes:
        observation_id: ULID primary key
        entity_id: FK to Entity
        security_id: FK to Security (if security-specific)
        metric: MetricSpec (what we're measuring)
        period: FiscalPeriod (what timeframe)
        observation_type: Type (actual, estimate, guidance, consensus)
        value: ValueWithUnits (the number)
        value_string: For non-numeric values
        as_of: When it was known
        captured_at: When we ingested it
        provenance_ref: Document/snapshot provenance
        source_key: Dataset/field key
        estimate_info: Estimate metadata
        supersedes_id: What this supersedes
        superseded_by_id: What superseded this
        confidence: Confidence score 0-1
        raw_value: Original raw value string
        notes: Additional notes
        created_at: Record creation timestamp
        updated_at: Last update timestamp
    """

    # Required fields
    entity_id: str
    metric: MetricSpec
    period: FiscalPeriod
    value: ValueWithUnits

    # Primary key
    observation_id: str = field(default_factory=generate_ulid)

    # Optional target
    security_id: str | None = None

    # Observation type
    observation_type: ObservationType = ObservationType.ACTUAL

    # For non-numeric values
    value_string: str | None = None

    # Time semantics
    as_of: datetime | None = None
    captured_at: datetime = field(default_factory=utc_now)

    # Provenance
    provenance_ref: ProvenanceRef | None = None
    source_key: SourceKey | None = None

    # Estimate metadata
    estimate_info: EstimateInfo | None = None

    # Supersession chain
    supersedes_id: str | None = None
    superseded_by_id: str | None = None

    # Quality
    confidence: float = 1.0

    # Raw data
    raw_value: str | None = None
    notes: str | None = None

    # Timestamps
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def __post_init__(self):
        """Validate Observation."""
        if not self.entity_id or not self.entity_id.strip():
            raise ValueError("entity_id cannot be empty")

        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"confidence must be between 0.0 and 1.0, got {self.confidence}")

        # Estimates should have estimate_info
        if self.observation_type in (ObservationType.ESTIMATE, ObservationType.CONSENSUS, ObservationType.GUIDANCE):
            if self.estimate_info is None:
                # Don't raise, just note - some workflows may set it later
                pass

    @property
    def observation_key(self) -> str:
        """
        Deterministic key for deduplication/idempotency.
        
        Same key = same logical observation (for upsert semantics).
        
        For actuals:
            entity_id + metric.canonical_key + period.canonical_key + as_of + provenance_ref.external_id
        
        For estimates:
            Above + estimator + estimate_scope
        """
        parts = [
            self.entity_id,
            self.metric.canonical_key,
            self.period.canonical_key,
            self.as_of.isoformat() if self.as_of else "na",
        ]

        if self.provenance_ref:
            parts.append(self.provenance_ref.external_id)

        if self.estimate_info:
            parts.append(self.estimate_info.estimator)
            parts.append(self.estimate_info.scope.value)

        key_string = "|".join(parts)
        return sha256(key_string.encode()).hexdigest()[:32]

    def __repr__(self) -> str:
        return (
            f"Observation("
            f"entity={self.entity_id}, "
            f"metric={self.metric}, "
            f"period={self.period}, "
            f"type={self.observation_type.value}, "
            f"value={self.value.value_normalized:,.2f})"
        )


# =============================================================================
# ObservationSet - Collection for comparison
# =============================================================================


@dataclass
class ObservationSet:
    """
    Collection of observations for comparison/analysis.
    
    Useful for:
    - Comparing estimates to actuals
    - Cross-source validation
    - Consensus calculation
    
    Attributes:
        entity_id: Entity being tracked
        metric: Metric being tracked
        period: Period being tracked
        observations: List of observations
    """

    entity_id: str
    metric: MetricSpec
    period: FiscalPeriod
    observations: list["Observation"] = field(default_factory=list)

    def get_by_type(self, obs_type: ObservationType) -> list["Observation"]:
        """Filter by observation type."""
        return [o for o in self.observations if o.observation_type == obs_type]

    def get_estimates(self) -> list["Observation"]:
        return self.get_by_type(ObservationType.ESTIMATE)

    def get_actuals(self) -> list["Observation"]:
        return self.get_by_type(ObservationType.ACTUAL)

    def get_consensus(self) -> "Observation | None":
        consensus = self.get_by_type(ObservationType.CONSENSUS)
        return consensus[0] if consensus else None

    def get_latest_actual(self) -> "Observation | None":
        """Get most recent actual (by as_of timestamp)."""
        actuals = self.get_actuals()
        if not actuals:
            return None
        return max(actuals, key=lambda o: o.as_of or datetime.min)

    def get_authoritative_actual(self) -> "Observation | None":
        """
        Get authoritative actual (not superseded, prefer SEC).
        
        Priority:
        1. Most recent SEC filing (not superseded)
        2. Most recent vendor actual
        3. Any actual
        """
        actuals = [o for o in self.get_actuals() if o.superseded_by_id is None]

        # SEC filings first
        sec = [
            o for o in actuals
            if o.provenance_ref and o.provenance_ref.kind == ProvenanceKind.SEC_FILING
        ]
        if sec:
            return max(sec, key=lambda o: o.as_of or datetime.min)

        # Any non-superseded actual
        if actuals:
            return max(actuals, key=lambda o: o.as_of or datetime.min)

        return None
