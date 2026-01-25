# Prompt: Observation Model Consolidation (P3)

> **Feature**: Delete legacy `financial_observation.py`, consolidate to `observation.py`  
> **Priority**: 🟡 P1 (Medium Impact, Low Effort)  
> **Estimated Effort**: 1 hour

---

## Context

EntitySpine currently has TWO observation model files:
- `observation.py` (786 lines) - **NEW v2.2.5** architecture with proper conventions
- `financial_observation.py` (606 lines) - **LEGACY v2.2.4** architecture

This causes confusion about which to use and duplicates maintenance effort.

## Current State

### `observation.py` (v2.2.5 - KEEP)
```python
# Proper EntitySpine conventions
# Uses generate_ulid(), utc_now(), str | None
# Structured MetricSpec with orthogonal axes
# Proper time semantics (period, as_of, captured_at)
# ProvenanceRef + SourceKey split

Classes:
- MetricSpec
- FiscalPeriod
- ProvenanceRef
- SourceKey
- EstimateInfo
- ValueWithUnits
- Observation
- ObservationSet
```

### `financial_observation.py` (v2.2.4 - DELETE)
```python
# Legacy conventions (some violations)
# Has factory functions that may be useful

Classes:
- MetricVariant (enum - now separate enums in enums.py)
- DataSourceType (enum)
- FiscalPeriodType (enum)
- FiscalPeriod (old version)
- DataSource
- MetricDefinition
- FinancialObservation
- ObservationSet (old version)

Factory Functions:
- create_factset_observation()
- create_bloomberg_observation()
- create_sec_observation()
- create_analyst_estimate()
- create_press_release_observation()
```

## Target State

```
entityspine/domain/
├── observation.py           # Single observation model (v2.2.5)
└── (no financial_observation.py)
```

## Requirements

1. **Analyze Factory Functions**: Check if any factory functions from `financial_observation.py` should be migrated to `observation.py` or `factories.py`

2. **Update Imports**: 
   - Remove `financial_observation.py` imports from `__init__.py`
   - Ensure `observation.py` classes are properly exported

3. **Check Usage**: Search codebase for any usage of legacy classes:
   ```python
   # Search for these imports
   from entityspine.domain.financial_observation import ...
   from entityspine.domain import FinancialObservation, DataSource, MetricDefinition
   ```

4. **Delete Legacy File**: Remove `financial_observation.py`

5. **Tests Must Pass**: Run `pytest tests/unit/` - all tests must pass

## Task

1. Search for usages of `financial_observation.py` classes in the codebase
2. Decide which factory functions (if any) to migrate:
   - `create_factset_observation()` → migrate to `observation.py` or `factories.py`
   - `create_bloomberg_observation()` → migrate or delete
   - `create_sec_observation()` → migrate or delete
   - `create_analyst_estimate()` → migrate or delete
   - `create_press_release_observation()` → migrate or delete
3. Update `__init__.py` to remove legacy imports
4. Delete `financial_observation.py`
5. Run tests

## Migration Checklist

- [ ] Search for `from entityspine.domain.financial_observation` imports
- [ ] Search for `FinancialObservation` class usage
- [ ] Search for `DataSource` class usage
- [ ] Search for `MetricDefinition` class usage
- [ ] Search for legacy `FiscalPeriod` usage (distinguish from new one)
- [ ] Migrate useful factory functions if any
- [ ] Update `__init__.py`
- [ ] Delete `financial_observation.py`
- [ ] Run tests

## Factory Function Migration (if needed)

If migrating factories, follow this pattern:

```python
# In observation.py or factories.py

def create_factset_observation(
    entity_id: str,
    metric: MetricSpec,
    period: FiscalPeriod,
    value: Decimal,
    field_name: str,
    snapshot_date: date,
    *,
    security_id: str | None = None,
) -> Observation:
    """Create observation from FactSet data."""
    return Observation(
        entity_id=entity_id,
        metric=metric,
        period=period,
        value=ValueWithUnits.from_normalized(value, "USD"),
        security_id=security_id,
        source_key=SourceKey.factset(field_name),
        provenance_ref=ProvenanceRef.vendor_snapshot(
            vendor=VendorNamespace.FACTSET,
            snapshot_date=snapshot_date,
        ),
    )
```

## Verification

```bash
cd entityspine
python -m pytest tests/unit/ -v --tb=short
# Expected: All tests pass (may be fewer if legacy tests removed)

# Verify new observation imports work
python -c "
from entityspine.domain import (
    Observation, ObservationSet, MetricSpec, FiscalPeriod,
    ProvenanceRef, SourceKey, EstimateInfo, ValueWithUnits,
)
print('All observation imports successful')
"
```
