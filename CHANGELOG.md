# EntitySpine Changelog

All notable changes to EntitySpine will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.3.2] - 2025-01-XX

### Added
- **Integration Module** (`entityspine.integration`) - Clean contract for py-sec-edgar integration:
  - `FilingFacts` - Complete set of facts extracted from SEC filings
  - `FilingEvidence` - Provenance linking facts to source filings
  - `ExtractedEntity` - Entity mentions extracted from filing text
  - `ExtractedIdentifier` - Identifiers extracted from filings
  - `ExtractedRelationship` - Relationships extracted from filing text
  - `ExtractedEvent` - Events extracted from 8-K filings
  - `ingest_filing_facts()` - Main ingestion function
  - `ingest_filing()` - Simplified ingestion for basic metadata
  - Normalizers: `normalize_cik()`, `normalize_ticker()`, `normalize_accession_number()`
- **Integration Tests** - 18 new tests for filing facts ingestion
- **Documentation** - Updated FILING_FACTS_SCHEMA.md with integration module examples

### Changed
- Total test count: 285 → 303 passing (18 new integration tests)
- pyproject.toml author and URLs updated for GitHub release

---

## [0.3.1] - 2025-01-XX

### Fixed
- **CRITICAL: Mapper Field Drift** - Fixed severe field drift in `stores/mappers.py`:
  - `entity_to_row`/`row_to_entity` - Fixed to match domain/entity.py fields
    - Changed: `legal_name` → removed, `incorporated_date` → `incorporation_date`
    - Changed: `merged_into_id` → `redirect_to`/`redirect_reason`/`merged_at`
  - `listing_to_row`/`row_to_listing` - Added missing `currency`, `status`, `source_system`, `source_id`
  - `security_to_row`/`row_to_security` - Removed identifier fields (`cusip`, `isin`, `figi`) 
    per v2.2.3 design (identifiers go in IdentifierClaim)
  - `claim_to_row`/`row_to_claim` - New functions (renamed from broken `identifier_to_row`)
    matching domain/claim.py fields
  - `case_to_row`/`row_to_case` - Fixed to match domain/graph.py Case dataclass

### Added
- **Cluster Mappers** - Added `cluster_to_row`/`row_to_cluster` for EntityCluster
- **ClusterMember Mappers** - Added `cluster_member_to_row`/`row_to_cluster_member` for EntityClusterMember
- **Store Methods for Case/Cluster**:
  - `save_case()`, `get_case()`, `get_cases_by_target()`, `get_cases_by_authority()`, `case_count()`
  - `save_cluster()`, `get_cluster()`, `cluster_count()`
  - `save_cluster_member()`, `get_cluster_members()`, `get_clusters_for_entity()`, `cluster_member_count()`
- **Regression Tests** - Added comprehensive mapper tests:
  - `TestEntityMappers` (4 tests)
  - `TestSecurityMappers` (4 tests)
  - `TestListingMappers` (4 tests)
  - `TestIdentifierClaimMappers` (5 tests including legacy alias check)
  - `TestCaseMappers` (3 tests)
  - `TestClusterMappers` (3 tests)
  - `TestClusterMemberMappers` (3 tests)

### Changed
- Total test count: 276 → 285 passing (9 new mapper regression tests)

### Notes
- SqliteStore was unaffected by mapper drift because it uses direct field access in SQL
- The mappers.py file is used by other stores that may implement the protocol

---

## [0.3.0] - 2025-01-XX

### Added
- **Knowledge Graph Node Types (v2.2.4)**:
  - `Asset` - Physical/tangible assets
  - `Contract` - Legal agreements  
  - `Product` - Products/services
  - `Brand` - Brand identities
  - `Event` - Discrete business events
- **Generic Relationship Model** - `Relationship` with `NodeRef` for polymorphic source/target
- **Full CRUD for KG Nodes** - SqliteStore supports all KG node types
- **Evidence Tracking** - Relationships can link to filing evidence

### Changed
- Refactored to ensure zero core dependencies
- Added `[pydantic]`, `[orm]`, `[duckdb]`, `[postgres]`, `[api]`, `[search]` extras
- Canonical domain models are now pure stdlib dataclasses

---

## [0.2.0] - 2024-XX-XX

### Added
- Initial EntitySpine implementation
- Core domain models: Entity, Security, Listing, IdentifierClaim
- SqliteStore with bootstrap from SEC JSON
- Pydantic adapters with `to_domain()`/`from_domain()`
- ORM adapters with SQLModel

---

## Design Principles

1. **Domain is canonical** - `entityspine.domain.*` contains the ONLY definition of each model
2. **Zero-dependency core** - `pip install entityspine` requires nothing extra
3. **Optional adapters** - Pydantic/ORM gated behind extras
4. **Stores return domain** - All store methods return domain dataclasses, not ORM/Pydantic objects
5. **Evidence-first relationships** - All edges can link to filing evidence
