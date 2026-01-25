# EntitySpine Documentation

> **Version**: 2.3.0  
> **Last Updated**: January 28, 2026

## 📚 Documentation Structure

```
docs/
├── architecture/     # Stable design principles
├── features/         # Feature documentation
├── rfcs/            # Proposals and design docs
├── adrs/            # Architecture Decision Records
├── changelog/       # Version history
├── sessions/        # LLM work session summaries
└── archive/         # Historical documents
```

## 🗂️ Quick Navigation

### Architecture (Stable)
| Document | Description |
|----------|-------------|
| [CONVENTIONS.md](architecture/CONVENTIONS.md) | Coding standards and patterns |
| [MANIFESTO.md](architecture/MANIFESTO.md) | Core philosophy: Entity ≠ Security ≠ Listing |
| [MODEL_ARCHITECTURE.md](architecture/MODEL_ARCHITECTURE.md) | Domain model layer design |
| [UNIFIED_DATA_MODEL.md](architecture/UNIFIED_DATA_MODEL.md) | Complete schema reference |

### Features
| Document | Description |
|----------|-------------|
| [observation-model.md](features/observation-model.md) | Financial observations (v2.2.5) |
| [ingestion.md](features/ingestion.md) | Data ingestion architecture |
| [factset-integration.md](features/factset-integration.md) | FactSet data integration |
| [social-feed.md](features/social-feed.md) | Social feed vision |

### Architecture Decision Records (ADRs)
| ADR | Title |
|-----|-------|
| [001](adrs/001-stdlib-only-domain.md) | Stdlib-only domain layer |
| [002](adrs/002-ulid-over-uuid.md) | ULID over UUID4 |
| [003](adrs/003-identifier-claims.md) | Identifier claims pattern |
| [004](adrs/004-frozen-dataclasses.md) | Frozen dataclasses |
| [005](adrs/005-enum-str-inheritance.md) | Enum str inheritance |
| [006](adrs/006-time-semantics.md) | Time semantics |
| [007](adrs/007-enum-package-split.md) | Enum package split |

### RFCs & Proposals
| Document | Status |
|----------|--------|
| [001-architecture-improvements.md](rfcs/001-architecture-improvements.md) | In Progress |
| [API Proposals](rfcs/) | Various API design options |

### Changelog
| Version | Date | Highlights |
|---------|------|------------|
| [2.3.0](changelog/CHANGELOG.md) | 2026-01-28 | Enum split, observations v2.2.5 |
| [2.2.4](changelog/CHANGELOG.md) | 2026-01 | KG high-confidence nodes |
| [2.2.3](changelog/CHANGELOG.md) | 2025-12 | Identifier claims |

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Applications                             │
│         py-sec-edgar │ FeedSpine │ Custom ETL                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                  entityspine.integration                         │
│          FilingFacts │ ingest_filing_facts() │ normalize        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    entityspine.stores                            │
│          JsonStore (Tier 0) │ SqliteStore (Tier 1)              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    entityspine.domain                            │
│         Entity │ Security │ Listing │ IdentifierClaim           │
│         Person │ Asset │ Contract │ Relationship │ Event        │
└─────────────────────────────────────────────────────────────────┘
```

## 🎯 Core Concepts

### 1. Entity ≠ Security ≠ Listing

EntitySpine maintains clear separation:

- **Entity**: Legal/organizational identity (e.g., "Apple Inc.")
- **Security**: Tradeable instrument (e.g., "Apple Common Stock")
- **Listing**: Exchange-specific ticker (e.g., "AAPL on NASDAQ")

An Entity can have multiple Securities, and each Security can have multiple Listings.

### 2. Claims-Based Identifiers

Instead of storing identifiers as flat fields, EntitySpine uses **claims** with provenance:

```python
# Bad: Flat identifiers with no context
entity.cik = "0000320193"
entity.lei = "HWUPKR..."

# Good: Claims with provenance
IdentifierClaim(
    entity_id=entity.entity_id,
    scheme=IdentifierScheme.CIK,
    value="0000320193",
    namespace=VendorNamespace.SEC,
    source="sec-edgar",
    confidence=1.0,
)
```

### 3. Tiered Storage

| Tier | Backend | Use Case | Temporal Support |
|------|---------|----------|------------------|
| 0 | JSON | Scripts, CLI | ❌ |
| 1 | SQLite | Development | ❌ |
| 2 | DuckDB | Analytics | ⏳ Planned |
| 3 | PostgreSQL | Production | ✅ Full |

### 4. Tier Honesty

Lower tiers explicitly warn when they can't fulfill advanced queries:

```python
result = store.resolve("AAPL", as_of=date(2015, 1, 1))
if not result.as_of_honored:
    print(result.warnings)  # ["as_of requires Tier 2+"]
```

## 📖 Design Documents

The `design/` subdirectory contains detailed design specifications:

| Document | Description |
|----------|-------------|
| `00_UNIFIED_DATA_MODEL_V2_2.md` | Master schema contract |
| `01_RESOLUTION_AND_TEMPORALITY.md` | Resolution algorithms |
| `02_PYSECEDGAR_INTEGRATION_CONTRACT.md` | Integration interface |
| `03_MIGRATION_NOTES.md` | Version migration guide |
| `04_IMPLEMENTATION_BLUEPRINT.md` | Implementation details |

## 📂 Archive

The `archive/` directory contains historical documentation:

- Previous prompt versions (PROMPT_ENTITYSPINE_V2_2_*.md)
- Old Pydantic model specs
- Audit documents

---

## 🔗 Related Resources

- **Repository**: https://github.com/ryansmccoy/entity-spine
- **Examples**: [../examples/](../examples/)
- **Tests**: [../tests/](../tests/)
- **API Reference**: https://entityspine.readthedocs.io (coming soon)
