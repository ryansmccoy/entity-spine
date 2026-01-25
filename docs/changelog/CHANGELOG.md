# Changelog

All notable changes to EntitySpine are documented here.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

---

## [2.3.4] - 2025-02

### Added
- **Full Audit Trail System** - Enterprise-grade provenance and decision tracking
  - `Provenance` - Track data lineage (file, API, manual sources)
  - `SourceRecord` - Preserve raw data snapshots for reproducibility
  - `MergeEvent` / `SplitEvent` - Entity lifecycle event tracking with rollback support
  - `Explanation` - Decision reasoning with human-readable and structured evidence
  - `ResolutionRun` - Batch operation tracking with statistics
  - `DataQualityRule` / `DataQualityResult` - Configurable validation framework

- **New Enums**
  - `DataQualitySeverity` - INFO, WARNING, ERROR, CRITICAL
  - `RunStatus` - PENDING, RUNNING, COMPLETED, FAILED, CANCELLED
  - `DecisionType` - MATCH, REJECT, MERGE, SPLIT, CREATE, UPDATE, MANUAL

- **Factory Functions** for audit trail types
  - `create_file_provenance()` - File-based data sources
  - `create_api_provenance()` - API-based data sources
  - `create_merge_event()` - Entity merge events
  - `create_explanation()` - Decision explanations
  - `create_resolution_run()` - Batch operations
  - `create_quality_rule()` - Data quality rules
  - `create_quality_result()` - Validation results

- **Entity Enhancements**
  - `Entity.merge_into_with_event()` - Merge with audit trail
  - `Claim.provenance_id` / `Claim.explanation_id` - Link to audit records

- **JSON Stores** for all audit trail types (Tier 0 storage)
- **SQLite Schema** - 8 new tables for audit trail persistence

### Changed
- All domain classes follow frozen dataclass pattern with slots
- All new enums use `(str, Enum)` pattern per ADR-005

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
