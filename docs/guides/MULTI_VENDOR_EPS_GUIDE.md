# Multi-Vendor EPS Management Guide

## The Problem: "Which EPS is the Right EPS?"

You're building a financial model and need Apple's Q4 2024 EPS. Sounds simple, right? 

Then you discover:

```
Source                  | EPS Value | What They Call It
------------------------|-----------|-------------------
SEC 10-K (GAAP)         | $1.46     | "Diluted EPS"
SEC 10-K (GAAP)         | $1.48     | "Basic EPS"
Apple Press Release     | $2.18     | "Non-GAAP diluted EPS"
FactSet Fundamentals    | $2.20     | "EPS (Normalized)"
Bloomberg               | $2.19     | "Adjusted EPS"
Refinitiv/LSEG          | $2.18     | "EPS excl. Extra Items"
Consensus Estimate      | $2.15     | "Mean EPS Estimate"
JP Morgan (Analyst)     | $2.22     | "JPM EPS Estimate"
Goldman Sachs (Analyst) | $2.12     | "GS EPS Estimate"
```

**Nine different EPS values for the same company, same quarter.**

Which one should your model use? They're all "correct" but measuring different things.

---

## Why These Values Differ

### 1. GAAP vs Non-GAAP (Accounting Basis)

| Type | What It Includes | Who Uses It |
|------|------------------|-------------|
| **GAAP EPS** | Everything required by accounting rules | SEC filings, auditors |
| **Non-GAAP EPS** | Excludes "unusual" items company chooses | Press releases, management |

Apple Q4 2024 Example:
- GAAP EPS: $1.46 (includes $8B one-time EU tax ruling)
- Non-GAAP EPS: $2.18 (excludes that charge)

### 2. Basic vs Diluted (Share Count Basis)

| Type | Share Count | When Higher |
|------|-------------|-------------|
| **Basic** | Actual shares outstanding | Always higher than diluted |
| **Diluted** | Basic + options, warrants, convertibles | Industry standard |

The difference can be 1-5% depending on stock option activity.

### 3. Vendor Normalization (Whose Adjustments?)

Each vendor applies their own "normalization" methodology:

```
┌─────────────────────────────────────────────────────────────────┐
│  Raw GAAP Net Income: $25,000,000,000                          │
├─────────────────────────────────────────────────────────────────┤
│  FactSet adds back:     │  Bloomberg adds back:                │
│  - Stock comp: $3B      │  - Stock comp: $3B                   │
│  - Restructuring: $1B   │  - Restructuring: $1B                │
│  - Amortization: $2B    │  - Intangible amort only: $1.5B      │
│  = "Normalized": $31B   │  = "Adjusted": $30.5B                │
└─────────────────────────────────────────────────────────────────┘
```

**Same raw data, different adjustments, different EPS.**

### 4. Actual vs Estimate (Observation Type)

| Type | Source | Use Case |
|------|--------|----------|
| **Actual** | After earnings released | Historical analysis |
| **Estimate** | Analyst prediction | Expectations, surprises |
| **Consensus** | Average of estimates | Benchmark for "beat/miss" |
| **Guidance** | Company projection | Forward expectations |

---

## How EntitySpine Models This

EntitySpine uses **orthogonal dimensions** instead of a single "variant" field:

```python
from entityspine.domain.observation import MetricSpec
from entityspine.domain.enums import (
    AccountingBasis,   # GAAP, IFRS, NON_GAAP
    Presentation,      # REPORTED, COMPANY_ADJUSTED, VENDOR_NORMALIZED
    PerShareType,      # BASIC, DILUTED
    ScopeType,         # TOTAL, CONTINUING, DISCONTINUED
)
```

### The MetricSpec: Structured Metric Definition

Instead of ambiguous strings like `"eps_adjusted"`, use explicit dimensions:

```python
# Apple's SEC-filed GAAP diluted EPS
eps_gaap = MetricSpec(
    code=MetricCode.EPS,
    category=MetricCategory.PER_SHARE,
    basis=AccountingBasis.GAAP,
    presentation=Presentation.REPORTED,
    per_share=PerShareType.DILUTED,
    scope=ScopeType.TOTAL,
)
# canonical_key: "eps:per_share:gaap:reported:diluted:total"

# Apple's press release Non-GAAP EPS
eps_non_gaap = MetricSpec(
    code=MetricCode.EPS,
    category=MetricCategory.PER_SHARE,
    basis=AccountingBasis.NON_GAAP,
    presentation=Presentation.COMPANY_ADJUSTED,
    per_share=PerShareType.DILUTED,
    scope=ScopeType.TOTAL,
)
# canonical_key: "eps:per_share:non_gaap:company_adjusted:diluted:total"

# FactSet normalized EPS
eps_factset = MetricSpec(
    code=MetricCode.EPS,
    category=MetricCategory.PER_SHARE,
    basis=AccountingBasis.GAAP,
    presentation=Presentation.VENDOR_NORMALIZED,
    per_share=PerShareType.DILUTED,
    scope=ScopeType.TOTAL,
)
# canonical_key: "eps:per_share:gaap:vendor_normalized:diluted:total"
```

### Factory Methods for Common Cases

```python
# Use factory methods for common metrics
eps_gaap_diluted = MetricSpec.eps_gaap_diluted()
eps_gaap_basic = MetricSpec.eps_gaap_basic()
eps_company_adj = MetricSpec.eps_company_adjusted()
eps_vendor_norm = MetricSpec.eps_vendor_normalized()
```

---

## Tracking Source/Vendor: The SourceKey

Every observation has a `SourceKey` that identifies where the data came from:

```python
from entityspine.domain.observation import SourceKey
from entityspine.domain.enums import VendorNamespace

# FactSet fundamentals
factset_source = SourceKey(
    vendor=VendorNamespace.FACTSET,
    dataset="fundamentals_daily",
    field_name="eps_normalized_diluted",
)

# Bloomberg
bloomberg_source = SourceKey(
    vendor=VendorNamespace.BLOOMBERG,
    dataset="equity_fundamentals",
    field_name="IS_EPS_ADJUSTED",
)

# SEC XBRL
sec_source = SourceKey(
    vendor=VendorNamespace.SEC,
    dataset="xbrl_filings",
    field_name="us-gaap:EarningsPerShareDiluted",
)

# Analyst estimate
analyst_source = SourceKey(
    vendor=VendorNamespace.IBES,
    dataset="detail_estimates",
    field_name="eps_mean",
)
# Note: broker info goes in EstimateInfo, not SourceKey
```

---

## The Full Observation: Putting It Together

```python
from entityspine.domain.observation import (
    Observation,
    MetricSpec,
    FiscalPeriod,
    SourceKey,
    ProvenanceRef,
    ValueWithUnits,
)
from entityspine.domain.enums import (
    ObservationType,
    ProvenanceKind,
    VendorNamespace,
)
from decimal import Decimal
from datetime import datetime, timezone

# Apple's Q4 2024 EPS from SEC 10-K
aapl_eps_sec = Observation(
    entity_id="aapl",
    
    # WHAT metric
    metric=MetricSpec.eps_gaap_diluted(),
    
    # WHAT period
    period=FiscalPeriod.quarterly(2024, 4, fye_month=9),  # Apple FYE September
    
    # WHAT value
    value=ValueWithUnits(
        value_raw=Decimal("1.46"),
        value_normalized=Decimal("1.46"),
        unit="USD/share",
        scale=1,
        currency="USD",
    ),
    
    # Actual vs Estimate
    observation_type=ObservationType.ACTUAL,
    
    # WHERE it came from
    source_key=SourceKey(
        vendor=VendorNamespace.SEC,
        dataset="xbrl_filings",
        field_name="us-gaap:EarningsPerShareDiluted",
    ),
    
    # WHICH document
    provenance_ref=ProvenanceRef(
        kind=ProvenanceKind.SEC_FILING,
        external_id="0000320193-24-000081",  # Accession number
        feed_run_id="sec-xbrl-2024-01-30",
    ),
    
    # WHEN known
    as_of=datetime(2024, 1, 30, 21, 30, tzinfo=timezone.utc),
)

# Same quarter, FactSet normalized
aapl_eps_factset = Observation(
    entity_id="aapl",
    metric=MetricSpec.eps_vendor_normalized(),
    period=FiscalPeriod.quarterly(2024, 4, fye_month=9),
    value=ValueWithUnits(
        value_raw=Decimal("2.20"),
        value_normalized=Decimal("2.20"),
        unit="USD/share",
    ),
    observation_type=ObservationType.ACTUAL,
    source_key=SourceKey(
        vendor=VendorNamespace.FACTSET,
        dataset="fundamentals_daily",
        field_name="eps_normalized_diluted",
    ),
    as_of=datetime(2024, 1, 31, 6, 0, tzinfo=timezone.utc),
)

# JP Morgan analyst estimate (made BEFORE earnings)
aapl_eps_jpm_estimate = Observation(
    entity_id="aapl",
    metric=MetricSpec.eps_vendor_normalized(),  # Analysts estimate adjusted
    period=FiscalPeriod.quarterly(2024, 4, fye_month=9),
    value=ValueWithUnits(
        value_raw=Decimal("2.22"),
        value_normalized=Decimal("2.22"),
        unit="USD/share",
    ),
    observation_type=ObservationType.ESTIMATE,
    estimate_info=EstimateInfo(
        scope=EstimateScope.BROKER,
        estimator="JP Morgan",
        analyst_id="JPMORGAN",
        analyst_name="Samik Chatterjee",
    ),
    source_key=SourceKey(
        vendor=VendorNamespace.IBES,
        dataset="detail_estimates",
    ),
    as_of=datetime(2024, 1, 15, tzinfo=timezone.utc),
)
```

---

## Querying: "Give Me the Right EPS"

### Authority Hierarchy

When you query for "the" EPS, EntitySpine follows an authority hierarchy:

```
1. SEC Filing (GAAP, reported) - Audited, legal source of truth
2. Press Release (Non-GAAP)    - Company's preferred view
3. Vendor Actual               - FactSet/Bloomberg/Refinitiv
4. Consensus Estimate          - IBES/FactSet consensus
5. Individual Estimate         - Specific analyst
```

### Query Patterns

```python
from entityspine.services.observation_service import ObservationService

service = ObservationService(storage)

# 1. "What's Apple's official Q4 2024 EPS?" (GAAP from SEC)
eps = await service.get_authoritative(
    entity_id="aapl",
    metric=MetricSpec.eps_gaap_diluted(),
    period=FiscalPeriod.quarterly(2024, 4),
)

# 2. "What's Apple's adjusted EPS?" (Non-GAAP from press release)
eps_adj = await service.get_authoritative(
    entity_id="aapl",
    metric=MetricSpec.eps_company_adjusted(),
    period=FiscalPeriod.quarterly(2024, 4),
)

# 3. "Give me ALL EPS values for Q4 (compare vendors)"
all_eps = await service.query(
    entity_id="aapl",
    metric_code=MetricCode.EPS,  # Any EPS variant
    period=FiscalPeriod.quarterly(2024, 4),
)

for obs in all_eps:
    print(f"{obs.source_key.vendor.value}: {obs.metric} = ${obs.value.value_normalized}")
    # SEC: EPS (diluted) = $1.46
    # SEC: EPS (basic) = $1.48
    # FACTSET: EPS (diluted) [vendor_normalized] = $2.20
    # BLOOMBERG: EPS (diluted) [vendor_normalized] = $2.19
    # IBES: EPS (diluted) [estimate] = $2.15 (consensus)

# 4. "Did Apple beat estimates?"
surprise = await service.calculate_surprise(
    entity_id="aapl",
    metric=MetricSpec.eps_vendor_normalized(),  # Compare apples to apples
    period=FiscalPeriod.quarterly(2024, 4),
)
# surprise.actual = 2.20 (FactSet normalized)
# surprise.consensus = 2.15 (IBES consensus)
# surprise.surprise = 0.05
# surprise.surprise_pct = 2.3%
```

---

## Supersession: When Values Get Revised

The same metric can be revised over time:

```
Timeline for AAPL Q4 2024 EPS (GAAP):
─────────────────────────────────────────────────────────────────►

Jan 30 (8-K)          Feb 28 (10-K)        Mar 15 (10-K/A)
     │                     │                     │
     ▼                     ▼                     ▼
  $1.45                 $1.46                 $1.47
  (preliminary)         (audited)            (amended)
```

EntitySpine tracks the **supersession chain**:

```python
# Each observation links to what it supersedes
preliminary = Observation(
    observation_id="obs_001",
    ...
)

audited = Observation(
    observation_id="obs_002",
    supersedes_id="obs_001",  # Points to preliminary
    ...
)

amended = Observation(
    observation_id="obs_003",
    supersedes_id="obs_002",  # Points to audited
    ...
)

# Query gets the latest non-superseded value
latest = await service.get_authoritative(...)
assert latest.observation_id == "obs_003"

# But you can get the full history
chain = await service.get_supersession_chain("obs_003")
# [preliminary, audited, amended]
```

---

## Deduplication: observation_key

To prevent duplicate storage, each observation has a unique key:

```python
@property
def observation_key(self) -> str:
    """Unique key for deduplication."""
    parts = [
        self.entity_id,
        self.metric.canonical_key,
        self.period.canonical_key,
        self.source_key.canonical_key if self.source_key else "na",
        self.as_of.isoformat() if self.as_of else "na",
    ]
    return sha256("|".join(parts).encode()).hexdigest()[:32]
```

Same entity + metric + period + source + as_of = same observation (update, don't duplicate).

---

## Estimate Tracking: EstimateInfo

For analyst estimates, track rich metadata:

```python
from entityspine.domain.observation import EstimateInfo
from entityspine.domain.enums import EstimateScope

# Individual analyst estimate
jpm_estimate = EstimateInfo(
    scope=EstimateScope.BROKER,
    estimator="JP Morgan",
    analyst_id="JPMORGAN",
    analyst_name="Samik Chatterjee",
)

# Consensus (mean of all estimates)
consensus = EstimateInfo(
    scope=EstimateScope.CONSENSUS,
    estimator="IBES Consensus",
    num_estimates=45,
    high_estimate=Decimal("2.35"),
    low_estimate=Decimal("1.95"),
)

# Company guidance
guidance = EstimateInfo(
    scope=EstimateScope.COMPANY_GUIDANCE,
    estimator="Apple Inc",
    guidance_type="range",
    guidance_low=Decimal("2.10"),
    guidance_high=Decimal("2.20"),
)
```

---

## Example: Full Multi-Vendor Ingestion

```python
"""Load EPS from multiple vendors, reconcile, query."""

from entityspine.domain.observation import Observation, MetricSpec, FiscalPeriod
from entityspine.services.observation_service import ObservationService

async def load_q4_eps():
    service = ObservationService()
    
    # 1. Load from SEC XBRL
    async for filing in sec_xbrl_client.get_financials("AAPL"):
        for fact in filing.facts:
            if fact.concept == "us-gaap:EarningsPerShareDiluted":
                obs = Observation(
                    entity_id="aapl",
                    metric=MetricSpec.eps_gaap_diluted(),
                    period=fact.fiscal_period,
                    value=fact.value,
                    source_key=SourceKey(vendor=VendorNamespace.SEC, ...),
                    provenance_ref=ProvenanceRef(external_id=filing.accession),
                    observation_type=ObservationType.ACTUAL,
                )
                await service.store(obs)
    
    # 2. Load from FactSet
    async for record in factset_client.get_fundamentals("AAPL"):
        obs = Observation(
            entity_id="aapl",
            metric=MetricSpec.eps_vendor_normalized(),
            period=record.fiscal_period,
            value=record.eps_normalized,
            source_key=SourceKey(vendor=VendorNamespace.FACTSET, ...),
            observation_type=ObservationType.ACTUAL,
        )
        await service.store(obs)
    
    # 3. Load analyst estimates from IBES
    async for estimate in ibes_client.get_estimates("AAPL"):
        obs = Observation(
            entity_id="aapl",
            metric=MetricSpec.eps_vendor_normalized(),
            period=estimate.fiscal_period,
            value=estimate.eps_mean,
            source_key=SourceKey(vendor=VendorNamespace.IBES, ...),
            observation_type=ObservationType.ESTIMATE,
            estimate_info=EstimateInfo(
                scope=EstimateScope.CONSENSUS,
                num_estimates=estimate.num_est,
            ),
        )
        await service.store(obs)
    
    # 4. Now query with confidence
    print("\n=== AAPL Q4 2024 EPS Cross-Reference ===\n")
    
    period = FiscalPeriod.quarterly(2024, 4)
    
    # Official GAAP
    gaap = await service.get_authoritative(
        entity_id="aapl",
        metric=MetricSpec.eps_gaap_diluted(),
        period=period,
    )
    print(f"SEC (GAAP): ${gaap.value.value_normalized}")
    
    # FactSet normalized
    factset = await service.get_authoritative(
        entity_id="aapl",
        metric=MetricSpec.eps_vendor_normalized(),
        period=period,
        vendor=VendorNamespace.FACTSET,
    )
    print(f"FactSet (Normalized): ${factset.value.value_normalized}")
    
    # Consensus before earnings
    consensus = await service.get_consensus(
        entity_id="aapl",
        metric=MetricSpec.eps_vendor_normalized(),
        period=period,
        as_of=gaap.as_of,  # Get consensus as of earnings date
    )
    print(f"Consensus: ${consensus.value.value_normalized} ({consensus.estimate_info.num_estimates} estimates)")
    
    # Surprise calculation
    surprise_pct = (factset.value.value_normalized - consensus.value.value_normalized) / consensus.value.value_normalized * 100
    print(f"\nSurprise: {surprise_pct:+.1f}% {'BEAT' if surprise_pct > 0 else 'MISS'}")
```

---

## The Canonical Key System

The `canonical_key` is the secret sauce for cross-vendor matching:

```
Metric Canonical Key Format:
{code}:{category}:{basis}:{presentation}:{per_share}:{scope}

Examples:
- eps:per_share:gaap:reported:diluted:total        (SEC GAAP diluted)
- eps:per_share:gaap:reported:basic:total          (SEC GAAP basic)
- eps:per_share:non_gaap:company_adjusted:diluted:total  (Press release adjusted)
- eps:per_share:gaap:vendor_normalized:diluted:total     (FactSet/Bloomberg normalized)

Period Canonical Key Format:
{fiscal_year}:{period_type}:{quarter}:{half}

Examples:
- 2024:quarterly:4:0  (Q4 FY2024)
- 2024:annual:0:0     (FY2024)
- 2025:semi_annual:0:1  (H1 2025)
```

This allows grouping and comparison across vendors:

```python
# "Show me all EPS values with same metric definition"
async for obs in service.query(
    entity_id="aapl",
    metric_canonical_key="eps:per_share:gaap:vendor_normalized:diluted:total",
    period=FiscalPeriod.quarterly(2024, 4),
):
    print(f"{obs.source_key.vendor}: {obs.value}")
```

---

## Summary: EntitySpine's Multi-Vendor Strategy

| Challenge | EntitySpine Solution |
|-----------|---------------------|
| Multiple EPS definitions | `MetricSpec` with orthogonal axes |
| Vendor differences | `SourceKey` with vendor namespace |
| Revisions over time | Supersession chain tracking |
| Duplicates | `observation_key` deduplication |
| Estimates vs Actuals | `ObservationType` enum |
| Which is "right"? | Authority hierarchy queries |
| Time semantics | period vs as_of vs captured_at |
| Analyst metadata | `EstimateInfo` with broker details |

The key insight: **Don't flatten the complexity, model it.**

Instead of `eps_adjusted = 2.18`, you have:
```python
Observation(
    metric=MetricSpec(
        code=EPS,
        basis=NON_GAAP,
        presentation=COMPANY_ADJUSTED,
        per_share=DILUTED,
    ),
    value=2.18,
    source_key=SourceKey(vendor=COMPANY, dataset="press_release"),
    observation_type=ACTUAL,
    as_of=datetime(2024, 1, 30, 21, 30),
)
```

Now you can answer any question about that number.
