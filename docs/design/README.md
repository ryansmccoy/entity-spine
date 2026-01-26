# EntitySpine Design Documentation

**Current Version:** v2.2

---

## Quick Links

| Document | Description |
|----------|-------------|
| [00_UNIFIED_DATA_MODEL_V2_2.md](current/00_UNIFIED_DATA_MODEL_V2_2.md) | **Master Contract** - Canonical data model |
| [01_RESOLUTION_AND_TEMPORALITY.md](current/01_RESOLUTION_AND_TEMPORALITY.md) | Resolution algorithms and temporal queries |
| [02_PYSECEDGAR_INTEGRATION_CONTRACT.md](current/02_PYSECEDGAR_INTEGRATION_CONTRACT.md) | py-sec-edgar ↔ entityspine boundary |
| [04_IMPLEMENTATION_BLUEPRINT.md](current/04_IMPLEMENTATION_BLUEPRINT.md) | Implementation guide |

---

## Directory Structure

```
docs/design/
├── README.md                    # This file
├── DESIGN_DOC_REORGANIZATION.md # Reorganization plan & history
│
├── current/                     # v2.2 - AUTHORITATIVE
│   ├── 00_UNIFIED_DATA_MODEL_V2_2.md      # Master contract
│   ├── 01_RESOLUTION_AND_TEMPORALITY.md   # Resolution & temporal
│   ├── 02_PYSECEDGAR_INTEGRATION_CONTRACT.md  # Integration
│   ├── 03_MIGRATION_NOTES.md              # v2.1→v2.2 migration
│   ├── 04_IMPLEMENTATION_BLUEPRINT.md     # Implementation
│   ├── 05_IMPLEMENTATION_PHASES.md        # Phases
│   ├── 05_TIER_CAPABILITIES_AND_LIMITS.md # Tier limits
│   ├── 06_PROTOCOLS_AND_INTERFACES.md     # Protocols
│   ├── 07_SQLITE_OPS_BEST_PRACTICES.md    # SQLite ops
│   └── 16_QUICK_REFERENCE.md              # Quick reference
│
└── archive/                     # HISTORICAL (read-only)
    ├── v2.0/                    # Original detailed designs
    │   ├── 01_CANONICAL_DATA_MODEL.md
    │   ├── 02_RESOLUTION_AND_MERGE_WORKFLOWS.md
    │   └── ...
    └── v2.1/                    # Intermediate version
        └── 00_UNIFIED_DESIGN.md
```

---

## Version History

| Version | Status | Notes |
|---------|--------|-------|
| **v2.2** | **Current** | Unified model, claims-based evidence, vendor mapping fixes |
| v2.1 | Archived | Consolidated from v1 and v2 designs |
| v2.0 | Archived | Original detailed ERD and workflow designs |

---

## Key Principles

1. **Entity ≠ Security ≠ Listing** - Three distinct object types
2. **Identifiers have scope** - CIK→Entity, ISIN→Security, Ticker→Listing
3. **Temporal validity** - `valid_from`/`valid_to` everywhere
4. **Claims-based evidence** - Identifiers backed by claims with provenance

---

## Implementation Technology (Updated January 2026)

The v2.2.2 implementation uses:

| Component | Technology | Notes |
|-----------|------------|-------|
| Domain Models | **Pydantic v2** | `frozen=True`, strict validation |
| Database Tables | **SQLModel** | Pydantic + SQLAlchemy hybrid |
| Package Manager | **uv** | Fast, reproducible builds |
| Repository Pattern | Generic + specific repos | Clean data access layer |

> **Note:** The original v2.2 design specified dataclasses for Tier 0-1. 
> We've modernized to Pydantic/SQLModel for better validation and DX while maintaining the same data model semantics.

---

*Last updated: January 2026*
