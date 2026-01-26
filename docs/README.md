# EntitySpine Documentation

> **Version**: 0.3.3  
> **Last Updated**: 2025-01

## 📚 Documentation Index

| Document | Description |
|----------|-------------|
| [MANIFESTO.md](MANIFESTO.md) | Core design philosophy — Entity ≠ Security ≠ Listing |
| [UNIFIED_DATA_MODEL.md](UNIFIED_DATA_MODEL.md) | Complete schema reference |
| [FILING_FACTS_SCHEMA.md](FILING_FACTS_SCHEMA.md) | Integration contract for py-sec-edgar |
| [MODEL_ARCHITECTURE.md](MODEL_ARCHITECTURE.md) | Domain model layer architecture |
| [MIGRATION.md](MIGRATION.md) | v0.3.0 migration guide |
| [08_MODELS_AND_VALIDATION.md](08_MODELS_AND_VALIDATION.md) | Domain model details and validation |

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
