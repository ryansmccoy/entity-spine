# Prompt: Financial Observation Extensions

> **Feature**: Extend the v2.2.5 observation model with additional capabilities  
> **Priority**: 🟡 P1 (Feature Enhancement)  
> **Estimated Effort**: 2-4 hours per extension

---

## Context

The v2.2.5 observation model (`entityspine/domain/observation.py`) implements the core 8 improvements. This prompt covers potential extensions and enhancements.

## Current State

The observation model has:
- `MetricSpec` - Structured metric specification with orthogonal axes
- `FiscalPeriod` - Fiscal period representation
- `ProvenanceRef` - Document/snapshot provenance
- `SourceKey` - Dataset/field lineage
- `EstimateInfo` - Estimate metadata
- `ValueWithUnits` - Normalized value storage
- `Observation` - Core observation dataclass
- `ObservationSet` - Collection for comparison

## Potential Extensions

### Extension 1: Observation Repository Protocol

Add a protocol for observation storage/retrieval:

```python
# In protocols.py or observation.py

class ObservationStoreProtocol(Protocol):
    """Protocol for observation storage."""
    
    def save(self, observation: Observation) -> None:
        """Save observation (upsert by observation_key)."""
        ...
    
    def get_by_id(self, observation_id: str) -> Observation | None:
        """Get observation by ID."""
        ...
    
    def get_by_key(self, observation_key: str) -> Observation | None:
        """Get observation by deduplication key."""
        ...
    
    def find_for_entity(
        self,
        entity_id: str,
        metric: MetricSpec | None = None,
        period: FiscalPeriod | None = None,
        observation_type: ObservationType | None = None,
    ) -> list[Observation]:
        """Find observations for entity with optional filters."""
        ...
    
    def get_supersession_chain(self, observation_id: str) -> list[Observation]:
        """Get full supersession chain for an observation."""
        ...
```

### Extension 2: Observation Comparison/Delta

Add utilities for comparing observations:

```python
@dataclass(frozen=True, slots=True)
class ObservationDelta:
    """Difference between two observations."""
    
    old_observation: Observation
    new_observation: Observation
    value_change: Decimal
    value_change_percent: Decimal
    is_revision: bool  # Same metric/period, different value
    is_supersession: bool  # Explicit supersession
    
    @classmethod
    def compare(cls, old: Observation, new: Observation) -> "ObservationDelta":
        """Compare two observations."""
        ...
```

### Extension 3: Consensus Calculation

Add consensus calculation from multiple estimates:

```python
@dataclass(frozen=True, slots=True)
class ConsensusResult:
    """Calculated consensus from multiple estimates."""
    
    entity_id: str
    metric: MetricSpec
    period: FiscalPeriod
    
    mean: Decimal
    median: Decimal
    high: Decimal
    low: Decimal
    std_dev: Decimal
    num_estimates: int
    
    estimates: list[Observation]
    calculated_at: datetime = field(default_factory=utc_now)
    
    @classmethod
    def calculate(cls, estimates: list[Observation]) -> "ConsensusResult":
        """Calculate consensus from list of estimate observations."""
        ...
```

### Extension 4: Surprise/Beat Calculation

Add earnings surprise calculation:

```python
@dataclass(frozen=True, slots=True)
class SurpriseResult:
    """Earnings surprise (actual vs estimate)."""
    
    actual: Observation
    estimate: Observation  # or ConsensusResult
    
    surprise_amount: Decimal
    surprise_percent: Decimal
    beat: bool  # actual > estimate
    miss: bool  # actual < estimate
    inline: bool  # within threshold
    
    @classmethod
    def calculate(
        cls,
        actual: Observation,
        estimate: Observation,
        inline_threshold: Decimal = Decimal("0.01"),
    ) -> "SurpriseResult":
        """Calculate surprise."""
        ...
```

### Extension 5: Time Series Builder

Add utilities for building time series:

```python
@dataclass
class ObservationTimeSeries:
    """Time series of observations for a metric."""
    
    entity_id: str
    metric: MetricSpec
    observations: list[Observation]
    
    def get_by_period(self, period: FiscalPeriod) -> Observation | None:
        """Get observation for specific period."""
        ...
    
    def get_quarterly_series(self, years: int = 5) -> list[Observation]:
        """Get last N years of quarterly observations."""
        ...
    
    def get_annual_series(self, years: int = 10) -> list[Observation]:
        """Get last N years of annual observations."""
        ...
    
    def calculate_growth(self, periods: int = 4) -> Decimal | None:
        """Calculate YoY or QoQ growth."""
        ...
```

### Extension 6: XBRL Mapping

Add XBRL tag mapping for SEC filings:

```python
@dataclass(frozen=True, slots=True)
class XBRLMapping:
    """Maps XBRL tags to MetricSpec."""
    
    xbrl_namespace: str
    xbrl_tag: str
    metric: MetricSpec
    priority: int  # For disambiguation
    
    @classmethod
    def from_us_gaap(cls, tag: str) -> "XBRLMapping | None":
        """Look up mapping for us-gaap tag."""
        ...

# Mapping table
XBRL_MAPPINGS: dict[tuple[str, str], MetricSpec] = {
    ("us-gaap", "Revenues"): MetricSpec.revenue(),
    ("us-gaap", "RevenueFromContractWithCustomerExcludingAssessedTax"): MetricSpec.revenue(),
    ("us-gaap", "NetIncomeLoss"): MetricSpec.net_income(),
    ("us-gaap", "EarningsPerShareDiluted"): MetricSpec.eps_gaap_diluted(),
    # ... etc
}
```

## Task Template

For each extension:

1. **Review conventions**: Read `entityspine/docs/ENTITYSPINE_CONVENTIONS.md`
2. **Implement in observation.py**: Or create new file if large enough
3. **Add to exports**: Update `__init__.py`
4. **Write tests**: In `tests/unit/domain/test_observation.py`
5. **Verify**: Run full test suite

## Conventions Checklist

- [ ] `@dataclass(frozen=True, slots=True)`
- [ ] `generate_ulid()` for IDs
- [ ] `utc_now()` for timestamps
- [ ] `str | None` not `Optional[str]`
- [ ] Docstrings with examples
- [ ] `__post_init__` for validation
- [ ] File header: `"""STDLIB ONLY - NO PYDANTIC."""`

## Verification

```bash
cd entityspine
python -m pytest tests/unit/domain/test_observation.py -v --tb=short
python -m pytest tests/unit/ -v --tb=short
```
