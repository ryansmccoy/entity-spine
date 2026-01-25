# EntitySpine Documentation

> **Version**: 0.4.0  
> **Last Updated**: January 27, 2026

## 📚 Documentation Index

| Document | Description |
|----------|-------------|
| [MANIFESTO.md](MANIFESTO.md) | Core design philosophy — Entity ≠ Security ≠ Listing |
| [UNIFIED_DATA_MODEL.md](UNIFIED_DATA_MODEL.md) | Complete schema reference |
| [SERVICES_REFERENCE.md](SERVICES_REFERENCE.md) | **NEW** - Audit, Conflicts, Data Quality services |
| [FILING_FACTS_SCHEMA.md](FILING_FACTS_SCHEMA.md) | Integration contract for py-sec-edgar |
| [MODEL_ARCHITECTURE.md](MODEL_ARCHITECTURE.md) | Domain model layer architecture |
| [MIGRATION.md](MIGRATION.md) | v0.3.0 migration guide |
| [08_MODELS_AND_VALIDATION.md](08_MODELS_AND_VALIDATION.md) | Domain model details and validation |

## 🆕 Recent Updates (January 2026)

### Complete Services Inventory

| Service | Module | Lines | Purpose |
|---------|--------|-------|---------|
| **Graph** | `services/graph_service.py` | 812 | Relationship traversal, network analysis |
| **Timeline** | `services/timeline.py` | 549 | Point-in-time queries, entity snapshots |
| **Exhibit 21** | `parser/exhibit21.py` | 918 | Corporate hierarchy parsing |
| **Audit** | `services/audit.py` | — | Change tracking with reversion |
| **Conflicts** | `services/conflicts.py` | — | Duplicate detection & resolution |
| **Data Quality** | `services/data_quality.py` | — | Validation & cleansing |
| **Fuzzy** | `services/fuzzy.py` | — | Name matching & normalization |
| **Clustering** | `services/clustering.py` | — | Entity grouping |
| **Resolver** | `services/resolver.py` | — | Multi-identifier resolution |
| **Symbology** | `services/symbology_refresh.py` | — | Identifier refresh |

See [SERVICES_REFERENCE.md](SERVICES_REFERENCE.md) for full API documentation.

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
