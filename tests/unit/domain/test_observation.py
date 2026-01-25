"""
Tests for v2.2.5 Financial Observation models.

STDLIB ONLY - NO PYDANTIC.

Tests verify:
- MetricSpec orthogonal axes
- FiscalPeriod time semantics
- ProvenanceRef + SourceKey split
- ValueWithUnits normalization
- Observation deduplication key
- EntitySpine conventions (ULID, utc_now, str|None)
"""

import pytest
from dataclasses import fields
from datetime import date, datetime, timezone
from decimal import Decimal

from entityspine.domain.observation import (
    MetricSpec,
    FiscalPeriod,
    ProvenanceRef,
    SourceKey,
    EstimateInfo,
    ValueWithUnits,
    Observation,
    ObservationSet,
)
from entityspine.domain.enums import (
    MetricCode,
    MetricCategory,
    AccountingBasis,
    Presentation,
    PerShareType,
    ScopeType,
    PeriodType,
    ObservationType,
    EstimateScope,
    ProvenanceKind,
    VendorNamespace,
)


class TestEntitySpineConventions:
    """Verify observation models follow EntitySpine conventions."""

    def test_observation_uses_ulid_for_id(self):
        """observation_id should be a 26-char ULID."""
        obs = Observation(
            entity_id="01HTEST",
            metric=MetricSpec.revenue(),
            period=FiscalPeriod.annual(2025),
            value=ValueWithUnits.from_raw(Decimal("100"), "USD"),
        )
        assert len(obs.observation_id) == 26
        assert obs.observation_id.isalnum()
        # ULIDs start with timestamp prefix (0-7 for current era)
        assert obs.observation_id[0] in "01234567"

    def test_provenance_uses_ulid_for_id(self):
        """provenance_id should be a 26-char ULID."""
        prov = ProvenanceRef.sec_filing(
            accession_number="0001193125-25-000123",
            form_type="10-K",
            filing_date=date(2025, 2, 15),
        )
        assert len(prov.provenance_id) == 26
        assert prov.provenance_id.isalnum()

    def test_captured_at_is_utc_aware(self):
        """captured_at should be UTC-aware datetime."""
        obs = Observation(
            entity_id="01HTEST",
            metric=MetricSpec.revenue(),
            period=FiscalPeriod.annual(2025),
            value=ValueWithUnits.from_raw(Decimal("100"), "USD"),
        )
        assert obs.captured_at.tzinfo is not None
        assert obs.captured_at.tzinfo == timezone.utc

    def test_created_at_is_utc_aware(self):
        """created_at should be UTC-aware datetime."""
        obs = Observation(
            entity_id="01HTEST",
            metric=MetricSpec.revenue(),
            period=FiscalPeriod.annual(2025),
            value=ValueWithUnits.from_raw(Decimal("100"), "USD"),
        )
        assert obs.created_at.tzinfo is not None
        assert obs.created_at.tzinfo == timezone.utc

    def test_optional_fields_use_pipe_none_not_optional(self):
        """Optional fields should use str | None style."""
        # Check Observation fields
        obs_fields = {f.name: f for f in fields(Observation)}
        # security_id is optional
        assert obs_fields["security_id"].default is None

    def test_observation_is_frozen_dataclass(self):
        """Observation should be immutable (frozen=True)."""
        obs = Observation(
            entity_id="01HTEST",
            metric=MetricSpec.revenue(),
            period=FiscalPeriod.annual(2025),
            value=ValueWithUnits.from_raw(Decimal("100"), "USD"),
        )
        with pytest.raises(Exception):  # FrozenInstanceError
            obs.entity_id = "different"


class TestMetricSpec:
    """Test MetricSpec structured specification."""

    def test_metric_spec_factory_eps_gaap_diluted(self):
        """EPS GAAP diluted factory."""
        eps = MetricSpec.eps_gaap_diluted()
        assert eps.code == MetricCode.EPS
        assert eps.category == MetricCategory.PER_SHARE
        assert eps.basis == AccountingBasis.GAAP
        assert eps.presentation == Presentation.REPORTED
        assert eps.per_share == PerShareType.DILUTED
        assert eps.scope == ScopeType.TOTAL

    def test_metric_spec_factory_eps_vendor_normalized(self):
        """Vendor-normalized EPS factory."""
        eps = MetricSpec.eps_vendor_normalized()
        assert eps.presentation == Presentation.VENDOR_NORMALIZED
        assert eps.per_share == PerShareType.DILUTED

    def test_metric_spec_canonical_key_is_stable(self):
        """Same metric spec should produce same canonical key."""
        eps1 = MetricSpec.eps_gaap_diluted()
        eps2 = MetricSpec.eps_gaap_diluted()
        assert eps1.canonical_key == eps2.canonical_key

    def test_metric_spec_different_axes_different_keys(self):
        """Different axes should produce different keys."""
        eps_diluted = MetricSpec.eps_gaap_diluted()
        eps_basic = MetricSpec.eps_gaap_basic()
        assert eps_diluted.canonical_key != eps_basic.canonical_key

    def test_metric_spec_str_representation(self):
        """String representation should be readable."""
        eps = MetricSpec.eps_gaap_diluted()
        assert "EPS" in str(eps)
        assert "diluted" in str(eps)

    def test_metric_spec_per_share_defaults_for_eps(self):
        """EPS-like metrics should default per_share if not specified."""
        eps = MetricSpec(code=MetricCode.EPS, category=MetricCategory.PER_SHARE)
        assert eps.per_share == PerShareType.DILUTED


class TestFiscalPeriod:
    """Test FiscalPeriod time semantics."""

    def test_annual_period(self):
        """Annual fiscal period."""
        fy = FiscalPeriod.annual(2025)
        assert fy.fiscal_year == 2025
        assert fy.period_type == PeriodType.ANNUAL
        assert str(fy) == "FY2025"

    def test_quarterly_period(self):
        """Quarterly fiscal period."""
        q4 = FiscalPeriod.quarterly(2025, 4)
        assert q4.fiscal_year == 2025
        assert q4.quarter == 4
        assert q4.period_type == PeriodType.QUARTERLY
        assert str(q4) == "Q4 FY2025"

    def test_quarterly_requires_valid_quarter(self):
        """Quarterly period requires quarter 1-4."""
        with pytest.raises(ValueError, match="quarter 1-4"):
            FiscalPeriod.quarterly(2025, 5)

    def test_semi_annual_period(self):
        """Semi-annual fiscal period."""
        h1 = FiscalPeriod.semi_annual(2025, 1)
        assert h1.half == 1
        assert h1.period_type == PeriodType.SEMI_ANNUAL
        assert str(h1) == "H1 2025"

    def test_ttm_period(self):
        """Trailing twelve months period."""
        ttm = FiscalPeriod.ttm(2025, ending_quarter=3)
        assert ttm.period_type == PeriodType.TTM
        assert str(ttm) == "TTM Q3 2025"

    def test_fiscal_period_canonical_key(self):
        """Canonical key for grouping."""
        q4 = FiscalPeriod.quarterly(2025, 4)
        assert "2025" in q4.canonical_key
        assert "quarterly" in q4.canonical_key


class TestProvenanceRef:
    """Test ProvenanceRef document lineage."""

    def test_sec_filing_provenance(self):
        """SEC filing provenance factory."""
        prov = ProvenanceRef.sec_filing(
            accession_number="0001193125-25-000123",
            form_type="10-K",
            filing_date=date(2025, 2, 15),
        )
        assert prov.kind == ProvenanceKind.SEC_FILING
        assert prov.accession_number == "0001193125-25-000123"
        assert prov.form_type == "10-K"
        assert prov.filing_date == date(2025, 2, 15)

    def test_vendor_snapshot_provenance(self):
        """Vendor snapshot provenance factory."""
        prov = ProvenanceRef.vendor_snapshot(
            vendor=VendorNamespace.FACTSET,
            snapshot_date=date(2025, 1, 28),
        )
        assert prov.kind == ProvenanceKind.VENDOR_SNAPSHOT
        assert prov.snapshot_date == date(2025, 1, 28)

    def test_provenance_external_id_required(self):
        """external_id cannot be empty."""
        with pytest.raises(ValueError, match="external_id cannot be empty"):
            ProvenanceRef(kind=ProvenanceKind.SEC_FILING, external_id="")


class TestSourceKey:
    """Test SourceKey field lineage."""

    def test_factset_source(self):
        """FactSet source key."""
        src = SourceKey.factset("FF_SALES")
        assert src.vendor == VendorNamespace.FACTSET
        assert src.field_name == "FF_SALES"

    def test_sec_xbrl_source(self):
        """SEC XBRL source key."""
        src = SourceKey.sec_xbrl("Revenues", namespace="us-gaap")
        assert src.vendor == VendorNamespace.SEC
        assert src.xbrl_tag == "Revenues"
        assert src.xbrl_namespace == "us-gaap"


class TestValueWithUnits:
    """Test ValueWithUnits normalization."""

    def test_from_raw_normalizes(self):
        """from_raw should normalize value."""
        val = ValueWithUnits.from_raw(
            value_raw=Decimal("119.2"),
            unit="USD",
            scale=1_000_000_000,
        )
        assert val.value_raw == Decimal("119.2")
        assert val.value_normalized == Decimal("119200000000")

    def test_in_millions(self):
        """Get value in millions."""
        val = ValueWithUnits.from_raw(
            value_raw=Decimal("119.2"),
            unit="USD",
            scale=1_000_000_000,
        )
        assert val.in_millions() == Decimal("119200")

    def test_in_billions(self):
        """Get value in billions."""
        val = ValueWithUnits.from_raw(
            value_raw=Decimal("119.2"),
            unit="USD",
            scale=1_000_000_000,
        )
        assert val.in_billions() == Decimal("119.2")

    def test_scale_must_be_positive(self):
        """Scale must be positive."""
        with pytest.raises(ValueError, match="scale must be positive"):
            ValueWithUnits.from_raw(Decimal("100"), "USD", scale=0)


class TestObservation:
    """Test Observation model."""

    def test_observation_creation(self):
        """Create observation with required fields."""
        obs = Observation(
            entity_id="01HTEST",
            metric=MetricSpec.revenue(),
            period=FiscalPeriod.annual(2025),
            value=ValueWithUnits.from_raw(Decimal("119.2"), "USD", scale=1_000_000_000),
        )
        assert obs.entity_id == "01HTEST"
        assert obs.observation_type == ObservationType.ACTUAL

    def test_observation_key_is_deterministic(self):
        """Same inputs should produce same observation_key."""
        obs1 = Observation(
            entity_id="01HTEST",
            metric=MetricSpec.revenue(),
            period=FiscalPeriod.annual(2025),
            value=ValueWithUnits.from_raw(Decimal("119.2"), "USD", scale=1_000_000_000),
            as_of=datetime(2025, 2, 15, 12, 0, 0, tzinfo=timezone.utc),
        )
        obs2 = Observation(
            entity_id="01HTEST",
            metric=MetricSpec.revenue(),
            period=FiscalPeriod.annual(2025),
            value=ValueWithUnits.from_raw(Decimal("999"), "USD"),  # Different value
            as_of=datetime(2025, 2, 15, 12, 0, 0, tzinfo=timezone.utc),
        )
        # Same key because same entity/metric/period/as_of
        assert obs1.observation_key == obs2.observation_key

    def test_observation_requires_entity_id(self):
        """entity_id cannot be empty."""
        with pytest.raises(ValueError, match="entity_id cannot be empty"):
            Observation(
                entity_id="",
                metric=MetricSpec.revenue(),
                period=FiscalPeriod.annual(2025),
                value=ValueWithUnits.from_raw(Decimal("100"), "USD"),
            )

    def test_observation_confidence_range(self):
        """confidence must be 0-1."""
        with pytest.raises(ValueError, match="confidence must be between"):
            Observation(
                entity_id="01HTEST",
                metric=MetricSpec.revenue(),
                period=FiscalPeriod.annual(2025),
                value=ValueWithUnits.from_raw(Decimal("100"), "USD"),
                confidence=1.5,
            )


class TestEstimateInfo:
    """Test EstimateInfo metadata."""

    def test_estimate_info_creation(self):
        """Create estimate info."""
        info = EstimateInfo(
            scope=EstimateScope.BROKER,
            estimator="Goldman Sachs",
            analyst_name="John Smith",
        )
        assert info.scope == EstimateScope.BROKER
        assert info.estimator == "Goldman Sachs"

    def test_consensus_estimate_info(self):
        """Consensus estimate with statistics."""
        info = EstimateInfo(
            scope=EstimateScope.CONSENSUS,
            estimator="Bloomberg Consensus",
            num_estimates=25,
            high_estimate=Decimal("2.50"),
            low_estimate=Decimal("2.20"),
        )
        assert info.num_estimates == 25

    def test_estimator_required(self):
        """estimator cannot be empty."""
        with pytest.raises(ValueError, match="estimator cannot be empty"):
            EstimateInfo(scope=EstimateScope.BROKER, estimator="")


class TestObservationSet:
    """Test ObservationSet collection."""

    def test_observation_set_filter_by_type(self):
        """Filter observations by type."""
        actual = Observation(
            entity_id="01HTEST",
            metric=MetricSpec.revenue(),
            period=FiscalPeriod.annual(2025),
            value=ValueWithUnits.from_raw(Decimal("119.2"), "USD", scale=1_000_000_000),
            observation_type=ObservationType.ACTUAL,
        )
        estimate = Observation(
            entity_id="01HTEST",
            metric=MetricSpec.revenue(),
            period=FiscalPeriod.annual(2025),
            value=ValueWithUnits.from_raw(Decimal("120"), "USD", scale=1_000_000_000),
            observation_type=ObservationType.ESTIMATE,
        )

        obs_set = ObservationSet(
            entity_id="01HTEST",
            metric=MetricSpec.revenue(),
            period=FiscalPeriod.annual(2025),
            observations=[actual, estimate],
        )

        assert len(obs_set.get_actuals()) == 1
        assert len(obs_set.get_estimates()) == 1
        assert obs_set.get_actuals()[0] == actual
