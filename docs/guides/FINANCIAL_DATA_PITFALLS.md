# Financial Data Pitfalls Guide

## A Catalog of Hard Problems in Financial Data

This guide documents the **non-obvious** problems you'll encounter when working with financial data. These aren't bugs—they're fundamental complexities of the domain.

---

## Table of Contents

1. [Point-in-Time (PIT) / Lookahead Bias](#1-point-in-time-pit--lookahead-bias)
2. [Survivorship Bias](#2-survivorship-bias)
3. [Corporate Actions](#3-corporate-actions-splits-spinoffs-mergers)
4. [Fiscal Calendar Misalignment](#4-fiscal-calendar-misalignment)
5. [Currency & Units Chaos](#5-currency--units-chaos)
6. [Identifier Hell](#6-identifier-hell)
7. [Restatements & Corrections](#7-restatements--corrections)
8. [Missing Data vs Zero vs Null](#8-missing-data-vs-zero-vs-null)
9. [Estimate vs Actual Timing](#9-estimate-vs-actual-timing)
10. [Primary Listing Ambiguity](#10-primary-listing-ambiguity)

---

## 1. Point-in-Time (PIT) / Lookahead Bias

### The Problem

**The most insidious bug in financial modeling: using data that wasn't available at the time.**

```
Timeline of AAPL Revenue (billions):
─────────────────────────────────────────────────────────────────────►

              Filing Date        Restatement
                  │                  │
                  ▼                  ▼
Oct 31, 2024   Nov 1, 2024      Feb 15, 2025
     │              │                 │
     ▼              ▼                 ▼
  Q4 ends      $95.2B filed      $94.9B restated

If your backtest on Dec 1, 2024 uses $94.9B... you have lookahead bias!
```

### Real-World Impact

| Model Type | Bias Effect |
|------------|-------------|
| Quant Backtest | Overstated returns (trading on future knowledge) |
| Risk Model | Understated risk (didn't see problems in real-time) |
| Valuation | Wrong multiples (using restated not original) |

### FeedSpine/EntitySpine Solution

**Three timestamp fields, not one:**

```python
@dataclass
class Observation:
    # WHAT timeframe does this measure?
    period: FiscalPeriod           # Q4 FY2024 (Oct-Dec)
    
    # WHEN was this value known to the market?
    as_of: datetime                # Nov 1, 2024 (filing date)
    
    # WHEN did we capture this into our system?
    captured_at: datetime          # Nov 1, 2024 09:15:00 UTC
```

**Point-in-time queries:**

```python
# "What did we KNOW about AAPL Q4 revenue on Dec 1, 2024?"
obs = await storage.query_pit(
    entity_id="aapl",
    metric=MetricSpec.revenue(),
    period=FiscalPeriod.quarterly(2024, 4),
    as_of=datetime(2024, 12, 1),  # Point-in-time constraint
)
# Returns $95.2B (the value known at that time)

# "What's the CURRENT authoritative value?"
obs = await storage.get_authoritative(
    entity_id="aapl",
    metric=MetricSpec.revenue(),
    period=FiscalPeriod.quarterly(2024, 4),
)
# Returns $94.9B (latest restated value)
```

### Implementation: PIT Query

```python
async def query_pit(
    self,
    entity_id: str,
    metric: MetricSpec,
    period: FiscalPeriod,
    as_of: datetime,
) -> Observation | None:
    """
    Get the observation that was known at a specific point in time.
    
    This returns the LATEST observation with as_of <= requested as_of.
    Critical for backtesting without lookahead bias.
    """
    return await self.conn.fetchrow("""
        SELECT * FROM observations
        WHERE entity_id = $1
          AND metric_key = $2
          AND period_key = $3
          AND as_of <= $4
        ORDER BY as_of DESC
        LIMIT 1
    """, entity_id, metric.canonical_key, period.canonical_key, as_of)
```

### The `as_of` Index

```sql
-- BRIN index for time-range queries (small, fast)
CREATE INDEX ix_obs_as_of_brin ON observations USING BRIN (as_of);

-- B-tree for point lookups
CREATE INDEX ix_obs_entity_metric_period_as_of 
ON observations (entity_id, metric_key, period_key, as_of DESC);
```

---

## 2. Survivorship Bias

### The Problem

**Your database only contains companies that still exist.**

```
S&P 500 in 2010:
├── Apple (still exists ✓)
├── Enron (bankrupt, delisted)      ← Missing from most databases!
├── WorldCom (bankrupt, delisted)   ← Missing!
├── Bear Stearns (acquired)         ← Missing!
└── ...

A backtest that only includes survivors overstates returns.
```

### Real-World Impact

- **20-year backtest error**: Can be 2-4% annual return overstatement
- **Sector analysis**: Failed companies in a sector disappear
- **Risk models**: Don't see companies that went bankrupt

### EntitySpine Solution

```python
class EntityStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    MERGED = "merged"
    ACQUIRED = "acquired"
    BANKRUPT = "bankrupt"
    DELISTED = "delisted"

@dataclass
class Entity:
    entity_id: str
    status: EntityStatus
    status_as_of: date
    
    # For merged/acquired
    successor_entity_id: str | None = None
    
    # Historical tracking
    status_history: list[StatusChange] = field(default_factory=list)
```

**Query with deceased entities:**

```python
# Get ALL entities that were in S&P 500 on Jan 1, 2010
# (including those that later failed)
entities = await entity_service.query(
    index="sp500",
    as_of=date(2010, 1, 1),
    include_inactive=True,  # Include bankruptcies, delistings
)
```

---

## 3. Corporate Actions (Splits, Spinoffs, Mergers)

### The Problem

**Historical prices and shares are meaningless without adjustment.**

```
AAPL Stock Splits:
─────────────────────────────────────────────────────────────────────►

2014: 7-for-1 split    2020: 4-for-1 split
        │                       │
        ▼                       ▼
    $700 → $100              $500 → $125

Q: What was AAPL's price on Jan 1, 2010?
A: $30.57 (raw) or $211.99 (split-adjusted)? BOTH are "correct"!
```

### Types of Corporate Actions

| Action | Effect | Complexity |
|--------|--------|------------|
| Stock Split | Share count × N, Price ÷ N | Low |
| Reverse Split | Share count ÷ N, Price × N | Low |
| Spinoff | Parent loses value, new entity created | High |
| Merger | Two entities become one | High |
| Rights Issue | Dilution, price drop | Medium |
| Stock Dividend | Like mini-split | Medium |

### EntitySpine Solution

```python
@dataclass
class CorporateAction:
    action_id: str
    entity_id: str
    action_type: CorporateActionType
    effective_date: date
    announcement_date: date
    
    # For splits
    split_ratio: Decimal | None = None  # 4.0 for 4-for-1
    
    # For spinoffs
    spinoff_entity_id: str | None = None
    spinoff_ratio: Decimal | None = None  # 0.1 = 1 new share per 10 old
    
    # For mergers
    acquirer_entity_id: str | None = None
    cash_component: Decimal | None = None
    stock_ratio: Decimal | None = None

def adjust_for_splits(
    price: Decimal,
    as_of: date,
    target_date: date,
    entity_id: str,
) -> Decimal:
    """Adjust historical price for all splits between dates."""
    splits = get_splits(entity_id, as_of, target_date)
    adjustment_factor = 1.0
    for split in splits:
        adjustment_factor *= split.split_ratio
    return price / Decimal(str(adjustment_factor))
```

---

## 4. Fiscal Calendar Misalignment

### The Problem

**"Q4 2024" means different things for different companies.**

```
Calendar Q4 2024 (Oct-Dec):
─────────────────────────────────────────────────────────────────────►
        Oct 1              Dec 31
           │                  │
           ▼                  ▼
    ┌──────────────────────────┐
    │  Most companies' Q4      │
    └──────────────────────────┘

Apple's Fiscal Year (ends September):
─────────────────────────────────────────────────────────────────────►
        Jul 1              Sep 30
           │                  │
           ▼                  ▼
    ┌──────────────────────────┐
    │  Apple's FY Q4           │  ← Oct-Dec is Apple's Q1!
    └──────────────────────────┘

Walmart's Fiscal Year (ends January):
─────────────────────────────────────────────────────────────────────►
        Nov 1              Jan 31
           │                  │
           ▼                  ▼
    ┌──────────────────────────┐
    │  Walmart's FY Q4         │  ← Calendar Q4 spans Walmart Q3 and Q4!
    └──────────────────────────┘
```

### Real-World Impact

- **Comparing Apple Q4 to Microsoft Q4**: Different 3-month periods!
- **Seasonal analysis**: Retail Q4 (holiday) vs tech Q4 (different months)
- **YoY comparisons**: Must match fiscal periods, not calendar

### EntitySpine Solution

```python
@dataclass(frozen=True, slots=True)
class FiscalPeriod:
    fiscal_year: int
    period_type: PeriodType
    quarter: int | None = None
    fye_month: int = 12          # Fiscal year end month (1-12)
    period_start: date | None = None
    period_end: date | None = None
    
    @classmethod
    def from_calendar_date(
        cls,
        cal_date: date,
        fye_month: int,
    ) -> "FiscalPeriod":
        """Convert calendar date to fiscal period."""
        # If FYE is December, fiscal = calendar
        # If FYE is September (Apple), fiscal year is +1 for Oct-Dec
        if cal_date.month > fye_month:
            fiscal_year = cal_date.year + 1
        else:
            fiscal_year = cal_date.year
        
        # Calculate fiscal quarter
        months_after_fye = (cal_date.month - fye_month - 1) % 12
        quarter = (months_after_fye // 3) + 1
        
        return cls(
            fiscal_year=fiscal_year,
            period_type=PeriodType.QUARTERLY,
            quarter=quarter,
            fye_month=fye_month,
        )
```

**Comparing across fiscal calendars:**

```python
# "Compare Apple and Microsoft Q4 earnings"
# WRONG: This compares different time periods!
apple_q4 = await get_observation(entity="aapl", period="Q4 2024")  # Jul-Sep
msft_q4 = await get_observation(entity="msft", period="Q4 2024")   # Oct-Dec

# RIGHT: Compare same CALENDAR quarter
apple_cal_q4 = await get_observation(
    entity="aapl",
    period=FiscalPeriod.from_calendar_date(date(2024, 12, 1), fye_month=9),
)  # Apple's Q1 FY2025

msft_cal_q4 = await get_observation(
    entity="msft",
    period=FiscalPeriod.from_calendar_date(date(2024, 12, 1), fye_month=6),
)  # Microsoft's Q2 FY2025
```

---

## 5. Currency & Units Chaos

### The Problem

**Is that revenue $119.2B or $119,200M or ¥17.4T?**

```
Same number, different representations:
─────────────────────────────────────────────────────────────────────

SEC Filing:     "Revenue: 119,200" (in millions, USD)
FactSet:        "FF_SALES: 119200000000" (raw USD)
Bloomberg:      "SALES_REV_TURN: 119.2B" (display, USD)
Company IR:     "$119.2 billion"

Toyota (in JPY):
SEC Filing:     "Revenue: 37,154,298" (millions JPY)
Converted:      "$247.7B" at ¥150/$ ... or $283.1B at ¥131/$?
```

### Real-World Impact

- **Aggregation bugs**: Summing millions + billions = disaster
- **Cross-company comparison**: USD vs EUR vs JPY
- **Historical conversion**: Which exchange rate? As-of or current?

### EntitySpine Solution

```python
@dataclass(frozen=True, slots=True)
class ValueWithUnits:
    """
    Stores BOTH raw and normalized values.
    
    value_normalized is ALWAYS base units (USD, not millions).
    """
    value_normalized: Decimal    # Always use this for math
    value_raw: Decimal           # As received from source
    unit: str                    # "USD", "EUR", "USD/share", "%"
    scale: int = 1               # 1, 1000, 1000000
    currency: str | None = None  # ISO 4217
    
    @classmethod
    def from_raw(
        cls,
        raw_value: Decimal,
        scale: int,
        currency: str,
        unit: str | None = None,
    ) -> "ValueWithUnits":
        """Create from raw value with scale."""
        return cls(
            value_normalized=raw_value * scale,
            value_raw=raw_value,
            unit=unit or currency,
            scale=scale,
            currency=currency,
        )

# Example: SEC filing says "119,200" in millions
revenue = ValueWithUnits.from_raw(
    raw_value=Decimal("119200"),
    scale=1_000_000,
    currency="USD",
)
# revenue.value_normalized = 119200000000 (always use this)
# revenue.value_raw = 119200 (what we received)
# revenue.scale = 1000000 (how to interpret raw)
```

---

## 6. Identifier Hell

### The Problem

**There is no universal company identifier.**

```
Apple Inc identifiers:
─────────────────────────────────────────────────────────────────────
CIK:        0000320193      (SEC - US only)
CUSIP:      037833100       (US/Canada securities)
ISIN:       US0378331005    (Global, includes country)
SEDOL:      2046251         (UK/LSE)
Ticker:     AAPL            (Exchange-specific, can be reused!)
LEI:        HWUPKR0MPOU8... (Legal Entity Identifier)
FIGI:       BBG000B9XRY4    (Bloomberg Open FIGI)
FactSet ID: 000C7F-E        (Vendor-specific)
Perm ID:    4295905573      (Refinitiv)

And they change over time:
- Ticker: AT&T was "T" then "T.A" during acquisition
- CUSIP: Changes with restructuring
- CIK: Never changes (good!) but US-only (bad!)
```

### Real-World Impact

- **Duplicate entities**: Same company loaded twice with different IDs
- **Broken links**: Ticker "TWTR" no longer exists
- **Cross-vendor joins**: FactSet ID doesn't match Bloomberg ID

### EntitySpine Solution

```python
@dataclass
class Entity:
    entity_id: str  # Our internal stable ID
    
    identifiers: dict[str, list[IdentifierRecord]]
    # {
    #     "cik": [IdentifierRecord("0000320193", valid_from=..., valid_to=None)],
    #     "cusip": [IdentifierRecord("037833100", ...)],
    #     "ticker": [
    #         IdentifierRecord("AAPL", exchange="NASDAQ", valid_from=1980, valid_to=None),
    #     ],
    # }

@dataclass
class IdentifierRecord:
    value: str
    valid_from: date
    valid_to: date | None  # None = still valid
    exchange: str | None = None  # For tickers
    source: str | None = None    # Who told us this

# Resolution service
async def resolve(
    cik: str | None = None,
    cusip: str | None = None,
    ticker: str | None = None,
    exchange: str | None = None,
    as_of: date | None = None,  # Point-in-time resolution!
) -> Entity:
    """
    Resolve any identifier to our unified entity.
    
    Handles:
    - Multiple identifiers for same entity
    - Historical identifier changes
    - Cross-vendor mapping
    """
```

---

## 7. Restatements & Corrections

### The Problem

**Companies change historical numbers. A lot.**

```
Microsoft Revenue Q2 FY2024 - Revision History:
─────────────────────────────────────────────────────────────────────

Jan 30, 2024 (Earnings):    $62.0B (preliminary)
Feb 2, 2024 (8-K):          $62.0B (confirmed)
Apr 25, 2024 (10-Q):        $61.9B (audited)
Jul 30, 2024 (10-K):        $62.1B (full-year reclass)

Which one is "right"? ALL of them, at different points in time.
```

### Types of Changes

| Type | Frequency | Magnitude | Example |
|------|-----------|-----------|---------|
| Preliminary → Audited | Every quarter | < 1% | Rounding, accruals |
| Restatement | Occasional | 1-5% | Accounting error |
| Reclass | Common | Varies | Segment reorganization |
| Fraud correction | Rare | 10-100% | Enron, WorldCom |

### EntitySpine Solution: Supersession Chain

```python
@dataclass
class Observation:
    observation_id: str
    supersedes_id: str | None = None    # Points to previous version
    superseded_by_id: str | None = None # Points to newer version
    is_authoritative: bool = True       # Latest non-superseded

# Chain example:
obs_1 = Observation(observation_id="001", ...)  # Preliminary
obs_2 = Observation(observation_id="002", supersedes_id="001", ...)  # Audited
obs_3 = Observation(observation_id="003", supersedes_id="002", ...)  # Restated

# Get full history
chain = await storage.get_supersession_chain("003")
# [obs_1, obs_2, obs_3]

# Get authoritative (default)
auth = await storage.get_authoritative(...)  # Returns obs_3

# Get point-in-time (for backtesting)
pit = await storage.query_pit(..., as_of=date(2024, 2, 1))  # Returns obs_1
```

---

## 8. Missing Data vs Zero vs Null

### The Problem

**These three are NOT the same:**

```
Company X Dividend:
─────────────────────────────────────────────────────────────────────

value = None   → We don't know if they pay dividends
value = 0      → They explicitly pay $0.00 dividend
value = NaN    → Calculation error / not applicable

Company Y R&D Expense:
value = None   → Not reported separately
value = 0      → They report $0 R&D (suspicious!)
```

### Real-World Impact

- **Averaging**: Mean of [1, 2, NULL] should be 1.5, not 1.0
- **Screening**: "Find all dividend payers" - does NULL mean non-payer?
- **Imputation**: When to fill forward vs leave missing?

### EntitySpine Solution

```python
class MissingReason(Enum):
    NOT_REPORTED = "not_reported"       # Company doesn't disclose
    NOT_APPLICABLE = "not_applicable"   # Metric doesn't apply (e.g., bank P/E)
    NOT_YET_AVAILABLE = "not_yet"       # Will be reported later
    CALCULATION_ERROR = "calc_error"    # Couldn't compute
    REDACTED = "redacted"               # Intentionally hidden

@dataclass
class ValueWithUnits:
    value_normalized: Decimal | None
    missing_reason: MissingReason | None = None
    
    @property
    def is_missing(self) -> bool:
        return self.value_normalized is None
    
    @property
    def is_zero(self) -> bool:
        return self.value_normalized == Decimal(0)
```

---

## 9. Estimate vs Actual Timing

### The Problem

**Estimates and actuals have a complex timeline relationship.**

```
Apple Q4 2024 EPS Timeline:
─────────────────────────────────────────────────────────────────────►

90 days    60 days    30 days    Earnings   +1 day    +30 days
before     before     before       Day                  
  │          │          │           │          │          │
  ▼          ▼          ▼           ▼          ▼          ▼
$2.10      $2.12      $2.15      $2.18      Actual    Consensus
est        est        est        actual    surprise    updated
                                            +1.4%

Q: What was "the consensus" on earnings day?
A: Depends on exact cutoff time! Morning vs after-hours?
```

### EntitySpine Solution

```python
@dataclass
class EstimateInfo:
    scope: EstimateScope           # BROKER, CONSENSUS, GUIDANCE
    estimator: str                 # "JP Morgan", "IBES Consensus"
    
    # WHEN was this estimate made?
    estimate_date: datetime | None = None
    
    # Consensus metadata
    num_estimates: int | None = None
    high_estimate: Decimal | None = None
    low_estimate: Decimal | None = None
    
    # For rolling consensus
    period_end: date | None = None  # Consensus as of this date

# Query estimates at specific point in time
consensus = await storage.get_consensus(
    entity_id="aapl",
    metric=MetricSpec.eps_vendor_normalized(),
    period=FiscalPeriod.quarterly(2024, 4),
    as_of=datetime(2024, 10, 31, 15, 0),  # Just before earnings
)
```

---

## 10. Primary Listing Ambiguity

### The Problem

**Where is a company "really" listed?**

```
Alibaba (BABA):
─────────────────────────────────────────────────────────────────────
NYSE (ADR):         BABA    - $85.50 (1 ADR = 8 ordinary shares)
Hong Kong:          9988.HK - HK$82.00
Hang Seng (dual):   9988    - HK$82.00

Which price is "correct"? Depends on:
- Your timezone (which market is open?)
- Your currency needs
- Liquidity requirements
- ADR ratio conversions
```

### EntitySpine Solution

```python
@dataclass
class SecurityListing:
    security_id: str
    entity_id: str
    exchange: str
    ticker: str
    
    is_primary: bool                    # Company's home listing
    security_type: SecurityType         # COMMON, ADR, GDR
    
    # For ADRs/GDRs
    underlying_security_id: str | None = None
    ratio: Decimal | None = None        # 1 ADR = 8 shares
    
    # Listing status
    listing_date: date
    delisting_date: date | None = None

# Get primary listing
primary = await security_service.get_primary_listing("alibaba")
# Returns 9988.HK (Hong Kong is "home")

# Get all listings with conversions
listings = await security_service.get_all_listings("alibaba")
for listing in listings:
    price = await get_price(listing.security_id)
    normalized = price / listing.ratio if listing.ratio else price
    print(f"{listing.exchange}: {price} = {normalized} per ordinary share")
```

---

## Summary: How FeedSpine/EntitySpine Help

| Problem | Solution |
|---------|----------|
| **Point-in-Time** | `as_of` timestamp + PIT queries |
| **Survivorship** | `EntityStatus` with history |
| **Corporate Actions** | Adjustment factors, supersession |
| **Fiscal Calendar** | `FiscalPeriod` with `fye_month` |
| **Currency/Units** | `ValueWithUnits` with normalization |
| **Identifiers** | Multi-ID resolution service |
| **Restatements** | Supersession chain |
| **Missing Data** | `MissingReason` enum |
| **Estimate Timing** | `EstimateInfo` with `estimate_date` |
| **Listings** | `SecurityListing` with ratios |

The key insight: **Model the complexity explicitly.** Don't hide it, don't assume it away. Make it queryable.
