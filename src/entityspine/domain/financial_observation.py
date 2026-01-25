"""
Financial Observation domain models (LEGACY/COMPATIBILITY).

This module provides backward-compatible imports for the v1 observation API.
New code should use entityspine.domain.observation instead.

STDLIB ONLY - NO PYDANTIC.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum

from entityspine.domain.enums import (
    MetricCategory,
    MetricCode,
    VendorNamespace,
)
from entityspine.domain.timestamps import generate_ulid, utc_now

# =============================================================================
# Legacy enums (for backward compatibility)
# =============================================================================

class MetricVariant(Enum):
    """Metric variant for legacy API."""
    REPORTED = "reported"
    ADJUSTED = "adjusted"
    NORMALIZED = "normalized"
    PRO_FORMA = "pro_forma"
    NON_GAAP = "non_gaap"
    GAAP = "gaap"
    BASIC = "basic"
    DILUTED = "diluted"


class DataSourceType(Enum):
    """Data source type."""
    SEC_FILING = "sec_filing"
    PRESS_RELEASE = "press_release"
    VENDOR_FEED = "vendor_feed"
    ANALYST_ESTIMATE = "analyst_estimate"
    COMPANY_GUIDANCE = "company_guidance"
    CALCULATED = "calculated"


class FiscalPeriodType(Enum):
    """Fiscal period type."""
    ANNUAL = "annual"
    QUARTERLY = "quarterly"
    SEMI_ANNUAL = "semi_annual"
    YTD = "ytd"
    LTM = "ltm"  # Last twelve months


# =============================================================================
# Legacy dataclasses
# =============================================================================

@dataclass(frozen=True, slots=True)
class FiscalPeriod:
    """
    Fiscal period specification (legacy).
    
    Attributes:
        year: Fiscal year
        period_type: Annual, quarterly, etc.
        quarter: Quarter number (1-4) if quarterly
    """
    year: int
    period_type: FiscalPeriodType = FiscalPeriodType.ANNUAL
    quarter: int | None = None

    def __str__(self) -> str:
        if self.period_type == FiscalPeriodType.ANNUAL:
            return f"FY{self.year}"
        elif self.period_type == FiscalPeriodType.QUARTERLY and self.quarter:
            return f"Q{self.quarter} {self.year}"
        return f"{self.period_type.value} {self.year}"


@dataclass(frozen=True, slots=True)
class DataSource:
    """
    Data source specification.
    
    Attributes:
        source_type: Type of source
        vendor: Vendor namespace
        dataset: Specific dataset name
        source_id: Unique ID within source
    """
    source_type: DataSourceType
    vendor: VendorNamespace = VendorNamespace.OTHER
    dataset: str | None = None
    source_id: str | None = None

    def __str__(self) -> str:
        parts = [self.source_type.value]
        if self.vendor != VendorNamespace.OTHER:
            parts.append(self.vendor.value)
        if self.dataset:
            parts.append(self.dataset)
        return ":".join(parts)


@dataclass(frozen=True, slots=True)
class MetricDefinition:
    """
    Definition of a financial metric.
    
    Attributes:
        code: Metric code
        category: Metric category
        variant: Metric variant
        name: Human-readable name
        unit: Unit of measurement
    """
    code: MetricCode
    category: MetricCategory = MetricCategory.OTHER
    variant: MetricVariant = MetricVariant.REPORTED
    name: str | None = None
    unit: str | None = None

    def __str__(self) -> str:
        name = self.name or self.code.value
        if self.variant != MetricVariant.REPORTED:
            return f"{name} ({self.variant.value})"
        return name


@dataclass(slots=True)
class FinancialObservation:
    """
    A single financial observation/data point.
    
    Attributes:
        observation_id: Unique identifier
        entity_id: Entity this observation is for
        metric: Metric definition
        period: Fiscal period
        value: Numeric value
        currency: Currency code
        source: Data source
        as_of: When the value was known
        captured_at: When we captured this
    """
    observation_id: str = field(default_factory=generate_ulid)
    entity_id: str | None = None
    security_id: str | None = None

    metric: MetricDefinition | None = None
    period: FiscalPeriod | None = None

    value: Decimal | None = None
    currency: str = "USD"

    source: DataSource | None = None
    as_of: datetime | None = None
    captured_at: datetime = field(default_factory=utc_now)

    confidence: float = 1.0

    def __str__(self) -> str:
        metric_str = str(self.metric) if self.metric else "unknown"
        period_str = str(self.period) if self.period else "unknown"
        return f"{metric_str} {period_str}: {self.value} {self.currency}"


@dataclass(slots=True)
class ObservationSet:
    """
    Collection of observations for an entity.
    
    Attributes:
        entity_id: Entity ID
        observations: List of observations
    """
    entity_id: str
    observations: list[FinancialObservation] = field(default_factory=list)

    def add(self, obs: FinancialObservation) -> None:
        """Add an observation."""
        self.observations.append(obs)

    def __len__(self) -> int:
        return len(self.observations)

    def __iter__(self):
        return iter(self.observations)


# =============================================================================
# Factory functions
# =============================================================================

def create_factset_observation(
    entity_id: str,
    metric_code: MetricCode,
    period_year: int,
    value: Decimal,
    currency: str = "USD",
    quarter: int | None = None,
    dataset: str = "factset_fundamentals",
) -> FinancialObservation:
    """Create a FactSet observation."""
    period_type = FiscalPeriodType.QUARTERLY if quarter else FiscalPeriodType.ANNUAL

    return FinancialObservation(
        entity_id=entity_id,
        metric=MetricDefinition(
            code=metric_code,
            category=MetricCategory.INCOME_STATEMENT,
            variant=MetricVariant.NORMALIZED,
        ),
        period=FiscalPeriod(year=period_year, period_type=period_type, quarter=quarter),
        value=value,
        currency=currency,
        source=DataSource(
            source_type=DataSourceType.VENDOR_FEED,
            vendor=VendorNamespace.FACTSET,
            dataset=dataset,
        ),
    )


def create_bloomberg_observation(
    entity_id: str,
    metric_code: MetricCode,
    period_year: int,
    value: Decimal,
    currency: str = "USD",
    quarter: int | None = None,
    dataset: str = "bloomberg_fundamentals",
) -> FinancialObservation:
    """Create a Bloomberg observation."""
    period_type = FiscalPeriodType.QUARTERLY if quarter else FiscalPeriodType.ANNUAL

    return FinancialObservation(
        entity_id=entity_id,
        metric=MetricDefinition(
            code=metric_code,
            category=MetricCategory.INCOME_STATEMENT,
            variant=MetricVariant.NORMALIZED,
        ),
        period=FiscalPeriod(year=period_year, period_type=period_type, quarter=quarter),
        value=value,
        currency=currency,
        source=DataSource(
            source_type=DataSourceType.VENDOR_FEED,
            vendor=VendorNamespace.BLOOMBERG,
            dataset=dataset,
        ),
    )


def create_sec_observation(
    entity_id: str,
    metric_code: MetricCode,
    period_year: int,
    value: Decimal,
    currency: str = "USD",
    quarter: int | None = None,
    accession_number: str | None = None,
) -> FinancialObservation:
    """Create an SEC filing observation."""
    period_type = FiscalPeriodType.QUARTERLY if quarter else FiscalPeriodType.ANNUAL

    return FinancialObservation(
        entity_id=entity_id,
        metric=MetricDefinition(
            code=metric_code,
            category=MetricCategory.INCOME_STATEMENT,
            variant=MetricVariant.GAAP,
        ),
        period=FiscalPeriod(year=period_year, period_type=period_type, quarter=quarter),
        value=value,
        currency=currency,
        source=DataSource(
            source_type=DataSourceType.SEC_FILING,
            vendor=VendorNamespace.SEC,
            source_id=accession_number,
        ),
    )


def create_analyst_estimate(
    entity_id: str,
    metric_code: MetricCode,
    period_year: int,
    value: Decimal,
    currency: str = "USD",
    quarter: int | None = None,
    broker: str | None = None,
) -> FinancialObservation:
    """Create an analyst estimate observation."""
    period_type = FiscalPeriodType.QUARTERLY if quarter else FiscalPeriodType.ANNUAL

    return FinancialObservation(
        entity_id=entity_id,
        metric=MetricDefinition(
            code=metric_code,
            category=MetricCategory.PER_SHARE,
            variant=MetricVariant.ADJUSTED,
        ),
        period=FiscalPeriod(year=period_year, period_type=period_type, quarter=quarter),
        value=value,
        currency=currency,
        source=DataSource(
            source_type=DataSourceType.ANALYST_ESTIMATE,
            dataset=broker,
        ),
    )


def create_press_release_observation(
    entity_id: str,
    metric_code: MetricCode,
    period_year: int,
    value: Decimal,
    currency: str = "USD",
    quarter: int | None = None,
) -> FinancialObservation:
    """Create a press release observation."""
    period_type = FiscalPeriodType.QUARTERLY if quarter else FiscalPeriodType.ANNUAL

    return FinancialObservation(
        entity_id=entity_id,
        metric=MetricDefinition(
            code=metric_code,
            category=MetricCategory.INCOME_STATEMENT,
            variant=MetricVariant.REPORTED,
        ),
        period=FiscalPeriod(year=period_year, period_type=period_type, quarter=quarter),
        value=value,
        currency=currency,
        source=DataSource(
            source_type=DataSourceType.PRESS_RELEASE,
        ),
    )
