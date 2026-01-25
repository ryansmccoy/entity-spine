# Changelog

All notable changes to EntitySpine are documented here.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Added
- Enum package split (ADR-007) - 42 enums organized into 10 modules
- Financial observation model v2.2.5 with 8 improvements
- Knowledge graph Event node enhancements (fiscal periods, calendar events)
- Multi-source ingestion support
- Comprehensive ADR documentation

### Changed
- `enums.py` → `enums/` package (backward compatible)

### Deprecated
- `financial_observation.py` (use `observation.py` instead)

---

## [2.3.0] - 2026-01-28

### Added
- **Financial Observations v2.2.5**
  - `MetricSpec` - multi-dimensional metric identity
  - `FiscalPeriod` - proper fiscal calendar handling
  - `ProvenanceRef` - split filing ref from vendor ref
  - `SourceKey` - deduplication key
  - `EstimateInfo` - consensus/broker estimates
  - `ValueWithUnits` - explicit units on values
  - `ObservationSet` - grouped observations with metadata

- **Knowledge Graph Enhancements**
  - Event node: fiscal year/quarter, scheduled_on, report_time, amount
  - Helper properties: `is_calendar_event`, `is_financial_event`
  - Extended relationship types for assets, contracts, products

- **Enum Package Split**
  - 10 focused modules replacing monolithic `enums.py`
  - Full backward compatibility via `__init__.py` re-exports

- **Documentation**
  - 7 Architecture Decision Records (ADRs)
  - Reorganized docs into architecture/, features/, rfcs/, adrs/
  - Session summaries for LLM continuity

### Changed
- Time semantics: explicit `captured_at` vs `valid_from`/`valid_to`
- All timestamps use `utc_now()` helper

---

## [2.2.4] - 2026-01

### Added
- Knowledge graph high-confidence nodes: Asset, Contract, Product, Brand, Event, Case, Geo
- Extended `RelationshipType` for new node types
- `RoleType` expansion for C-suite and board positions

---

## [2.2.3] - 2025-12

### Added
- `IdentifierClaim` as source of truth for identifiers
- `VendorNamespace` for multi-vendor crosswalks
- Scheme-scope enforcement (CIK→entity, ISIN→security, TICKER→listing)
- `captured_at` vs `valid_from`/`valid_to` time semantics

### Changed
- Entity/Security no longer store identifiers directly
- Listing holds ticker (ticker is listing-scoped)

---

## [2.2.0] - 2025-11

### Added
- Stdlib-only domain layer (ADR-001)
- ULID for all IDs (ADR-002)
- Frozen dataclasses (ADR-004)
- `(str, Enum)` pattern (ADR-005)
- Resolution tiers with warnings

---

## [2.0.0] - 2025-10

### Added
- Initial EntitySpine architecture
- Entity, Security, Listing domain models
- Basic resolution system
- JSON and SQLite storage backends
