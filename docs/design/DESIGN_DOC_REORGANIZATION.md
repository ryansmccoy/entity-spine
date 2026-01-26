# Design Document Reorganization Plan

**Date:** January 2026  
**Status:** Proposed

---

## Current Issue

The `docs/design/` directory has duplicate numbered prefixes (00_, 01_, 02_, etc.) representing **two different documentation series**:

1. **v2.0/2.1 Series** - Original detailed design docs (standalone)
2. **v2.2 Series** - Unified model with companion documents

---

## Proposed Directory Structure

```
docs/design/
├── README.md                              # Index pointing to current docs
├── DESIGN_DOC_REORGANIZATION.md           # This file
│
├── current/                               # v2.2 - AUTHORITATIVE
│   ├── 00_UNIFIED_DATA_MODEL_V2_2.md      # Master contract (source of truth)
│   ├── 01_RESOLUTION_AND_TEMPORALITY.md   # Companion
│   ├── 02_PYSECEDGAR_INTEGRATION_CONTRACT.md  # Companion
│   ├── 03_MIGRATION_NOTES.md              # v2.1→v2.2 migration
│   ├── 04_IMPLEMENTATION_BLUEPRINT.md     # Implementation guide
│   └── 05_IMPLEMENTATION_PHASES.md        # Phased approach
│
└── archive/                               # v2.0/2.1 - HISTORICAL REFERENCE
    ├── v2.0/
    │   ├── 01_CANONICAL_DATA_MODEL.md
    │   ├── 02_RESOLUTION_AND_MERGE_WORKFLOWS.md
    │   ├── 03_VENDOR_CROSSWALK_AND_CONFLICTS.md
    │   ├── 04_MENTIONS_PROVISIONAL.md
    │   └── ...
    └── v2.1/
        └── 00_UNIFIED_DESIGN.md
```

---

## File Classification

### Current (v2.2) - Move to `current/`

| File | Notes |
|------|-------|
| `00_UNIFIED_DATA_MODEL_V2_2.md` | Master contract, supersedes v2.1 |
| `01_RESOLUTION_AND_TEMPORALITY.md` | "Companion to Unified Data Model v2.2" |
| `02_PYSECEDGAR_INTEGRATION_CONTRACT.md` | "Companion to Unified Data Model v2.2" |
| `03_MIGRATION_NOTES.md` | Migration from v2.1 → v2.2 |
| `04_IMPLEMENTATION_BLUEPRINT.md` | "EntitySpine Implementation Blueprint (v2.2)" |
| `05_IMPLEMENTATION_PHASES.md` | "EntitySpine v2.2 Implementation Phases" |
| `05_STORAGE_TIERS.md` | Tier 0-3 details (keep if v2.2 aligned) |
| `06_PROTOCOLS_AND_INTERFACES.md` | Protocol definitions |
| `14_STORAGE_SCHEMA_V2.md` | Storage schema (verify version) |
| `16_QUICK_REFERENCE.md` | Quick reference (keep current) |
| `17_LIGHTWEIGHT_MODULAR_ARCHITECTURE.md` | Architecture overview |

### Archive (v2.0/2.1) - Move to `archive/`

| File | Version | Notes |
|------|---------|-------|
| `00_UNIFIED_DESIGN.md` | v2.1 | "Consolidated from v1 and v2 designs" |
| `01_CANONICAL_DATA_MODEL.md` | v2.0 | Original ERD, predates v2.2 corrections |
| `02_RESOLUTION_AND_MERGE_WORKFLOWS.md` | v2.0 | Older resolution design |
| `03_VENDOR_CROSSWALK_AND_CONFLICTS.md` | v2.0 | Detailed vendor mapping |
| `04_MENTIONS_PROVISIONAL.md` | v2.0 | Provisional entity handling |
| `05_TIER_CAPABILITIES_AND_LIMITS.md` | v2.0? | Verify version |
| `06_PYSECEDGAR_PORT.md` | v2.0? | Port design |
| `07_FEEDSPINE_PIPELINE.md` | v2.0? | FeedSpine integration |
| `07_SQLITE_OPS_BEST_PRACTICES.md` | v2.0 | SQLite practices |
| `08_GOVERNANCE_AUDIT.md` | v2.0? | Audit logging |
| `08_IDENTIFIER_CLASSIFICATION.md` | v2.0 | Identifier schemes |
| `09_FEEDSPINE_INTEGRATION_ANALYSIS.md` | v2.0? | FeedSpine analysis |

### Determine Version (Review needed)

| File | Action |
|------|--------|
| `15_ENTITY_MASTER_INTEGRATION.md` | Check version, classify |
| `18_IMPLEMENTATION_BLUEPRINT.md` | Duplicate of 04? Check |

---

## Migration Commands

```powershell
# Create directories
mkdir docs/design/current
mkdir docs/design/archive/v2.0
mkdir docs/design/archive/v2.1

# Move v2.2 current docs
Move-Item docs/design/00_UNIFIED_DATA_MODEL_V2_2.md docs/design/current/
Move-Item docs/design/01_RESOLUTION_AND_TEMPORALITY.md docs/design/current/
Move-Item docs/design/02_PYSECEDGAR_INTEGRATION_CONTRACT.md docs/design/current/
Move-Item docs/design/03_MIGRATION_NOTES.md docs/design/current/
Move-Item docs/design/04_IMPLEMENTATION_BLUEPRINT.md docs/design/current/
Move-Item docs/design/05_IMPLEMENTATION_PHASES.md docs/design/current/

# Move v2.1 archive docs
Move-Item docs/design/00_UNIFIED_DESIGN.md docs/design/archive/v2.1/

# Move v2.0 archive docs
Move-Item docs/design/01_CANONICAL_DATA_MODEL.md docs/design/archive/v2.0/
Move-Item docs/design/02_RESOLUTION_AND_MERGE_WORKFLOWS.md docs/design/archive/v2.0/
Move-Item docs/design/03_VENDOR_CROSSWALK_AND_CONFLICTS.md docs/design/archive/v2.0/
Move-Item docs/design/04_MENTIONS_PROVISIONAL.md docs/design/archive/v2.0/
```

---

## Benefits

1. **Clear authoritative source** - `current/` contains only v2.2 docs
2. **Historical preservation** - Archive retains valuable design thinking
3. **No duplicate prefixes** - Each directory has unique numbering
4. **Easy navigation** - README at root points to current docs

---

## Decision Needed

Should we:
1. **Execute this reorganization** - Create subdirectories and move files
2. **Keep flat structure** - Just rename files with version suffix (e.g., `_v2.0`)
3. **Delete archives** - Remove older versions entirely (not recommended)

---

*Last updated: January 2026*
