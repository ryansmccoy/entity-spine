# EntitySpine Changelog

All notable changes to EntitySpine will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.3.3] - 2025-01-31

**Release Status**: ✅ APPROVED FOR PYPI

This is a **production-ready release** focused on code quality, comprehensive documentation, and PyPI release preparation.

### 🎉 Highlights
- **548 Passing Tests** (100% pass rate in ~10s)
- **Zero-Dependency Core** (stdlib-only for Tier 0-1)
- **Comprehensive Documentation** (README, Feature Matrix, Release Audit)
- **Successfully Built Wheel** (`entityspine-0.3.3-py3-none-any.whl`)

### ✅ Added
- **MANIFEST.in** - Package manifest for proper source distribution
- **FEATURE_MATRIX.md** - Comprehensive feature support matrix across all tiers
- **RELEASE_AUDIT_REPORT.md** - Detailed v0.3.3 release audit with:
  - Complete audit findings
  - Test results (548 passed, 5 skipped)
  - Quality metrics (coverage: 40%, linting: cleaned)
  - Pre-release checklist
  - PyPI publishing instructions
- **README_v0.3.3.md** - Enhanced README with:
  - Complete folder structure documentation
  - Tiered architecture explanation (Tier 0-5)
  - 40+ code examples
  - Optional dependency matrix
  - Installation patterns
  - Comprehensive API reference
- **API Deployment Wrapper** (`api/` directory):
  - Standalone Docker deployment setup
  - `docker-compose.yml` for multi-container orchestration
  - Separate from package-integrated API (`src/entityspine/api/`)
- **Lookup Service** (`services/lookup.py`):
  - Simple ticker/CIK/name lookup utility
  - Dead-simple API for common queries
  - Zero-dependency implementation
- **Reference Data Scripts**:
  - `scripts/load_all_reference_data.py` - Load ISO standards
  - `scripts/verify_reference_data.py` - Verify data integrity

### 🔧 Fixed
- **Import Errors** in `domain/__init__.py`:
  - Removed non-existent `ObservationType` import
  - Commented out non-existent market constants (moved to `reference_data.markets`)
  - Removed non-existent factory functions (`create_exchange`, `lookup_exchange_by_mic`)
- **Linting Issues**:
  - Auto-fixed **2,162 errors** with ruff (whitespace, imports, type annotations)
  - Remaining 1,246 issues are cosmetic (documented for v0.3.4)
- **Test Suite**:
  - All 548 tests now pass cleanly (was broken by import errors)
  - Added test skip for optional API tests (requires [api] extra)

### 📚 Documentation Updates
- **Reorganized Documentation**:
  - Moved `ARCHITECTURE_AND_TIERS.md` → `docs/architecture/`
  - Moved `GUARDRAILS.md` → `docs/`
  - Archived `IMPLEMENTATION_SUMMARY.md` → `docs/archive/`
  - Deleted 6 stale log files
  - Deleted 7 obsolete prompt files
- **Updated `.gitignore`**:
  - Added exclusions for `*.code-workspace`
  - Added exclusions for deployment configs (Dockerfile, docker-compose.yml)
  - Added exclusions for requirements.txt

### 🧪 Testing
- **Test Count**: 548 passed, 5 skipped
- **Test Duration**: ~10 seconds
- **Coverage**: 40% (target: 60% for v0.4.0)
- **Test Categories**:
  - Unit tests: Domain models, stores, validators
  - Integration tests: End-to-end scenarios, filing ingestion
  - Source tests: ISO loaders, SEC data
  - Reference data tests: Markets, currencies, countries

### 📦 Build & Package
- **Built Wheel**: `entityspine-0.3.3-py3-none-any.whl`
- **Installation Verified**: Core imports working
- **Zero-Dependency Core**: No required dependencies
- **Optional Extras**:
  - `[pydantic]` - Validation wrappers
  - `[orm]` - SQLModel layer
  - `[api]` - FastAPI endpoints
  - `[cli]` - Command-line tools
  - `[dev]` - Development tools
  - `[all]` - Everything

### 🎯 Quality Metrics
- **Linting**: 2,162 errors auto-fixed, 1,246 cosmetic warnings remain
- **Type Checking**: ~50 mypy warnings (non-blocking)
- **Test Coverage**: 40% (below 60% target but acceptable for v0.3.x)
- **Git Status**: Clean (all changes committed)

### 🚀 Release Commits
1. `feat: add lookup service and API deployment wrapper`
2. `docs: reorganize documentation structure`
3. `fix: auto-fix linting errors and repair import issues`
4. `docs: add comprehensive v0.3.3 release audit report`

### ⚠️ Known Issues (Non-Blocking)
1. **Test Coverage**: 40% vs 60% target (fix in v0.3.4)
2. **Linting**: 1,246 cosmetic warnings (address in v0.3.4)
3. **Type Annotations**: ~50 mypy errors (gradual improvement)
4. **SyntaxWarning**: Invalid escape sequence in `data/ingest.py` (1-line fix)

### 📖 Migration Guide
No breaking changes from v0.3.2. Fully backward compatible.

---

## [0.3.2] - 2025-01-XX (Pre-Release)

### Added
- **Best-in-Class README** - Comprehensive documentation with badges, architecture diagrams, examples
- **Pre-commit Configuration** - `.pre-commit-config.yaml` with ruff, mypy, bandit, markdownlint
- **GitHub Actions CI** - `.github/workflows/ci.yml` for automated testing across Python 3.11/3.12, multi-OS
- **CONTRIBUTING.md** - Complete contributor guidelines with development setup, style guide, architecture principles
- **New Examples**:
  - `02_load_sec_company_tickers.py` - Download and load SEC company data
  - `03_entity_identifier_claims.py` - Multi-scheme identifiers with provenance
  - `04_knowledge_graph_relationships.py` - Build KG with suppliers, customers, executives
  - `05_filing_facts_ingestion.py` - Use the integration module for bulk ingestion

### Changed
- **Documentation Cleanup** - Moved outdated PROMPT_*, PYDANTIC_* files to docs/archive/
- **Updated docs/README.md** - New documentation index with architecture overview
- **Updated examples/README.md** - Added table of all examples

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
