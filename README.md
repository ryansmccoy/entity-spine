# EntitySpine

**Zero-Dependency Entity Resolution for SEC EDGAR Data**

From `company_tickers.json` to enterprise-grade Knowledge Graph — without forcing dependencies.

---

## Architecture: Domain is Canonical

```
┌─────────────────────────────────────────────────────────────────┐
│                    entityspine.domain                           │
│                  (stdlib dataclasses only)                      │
│  ┌─────────┐ ┌──────────┐ ┌─────────┐ ┌─────────────────┐      │
│  │ Entity  │ │ Security │ │ Listing │ │IdentifierClaim  │      │
│  └─────────┘ └──────────┘ └─────────┘ └─────────────────┘      │
│  ┌─────────┐ ┌──────────┐ ┌─────────┐ ┌─────────────────┐      │
│  │  Asset  │ │ Contract │ │ Product │ │  Relationship   │      │
│  └─────────┘ └──────────┘ └─────────┘ └─────────────────┘      │
└─────────────────────────────────────────────────────────────────┘
                          ↑ returns domain dataclasses
┌─────────────────────────────────────────────────────────────────┐
│                      entityspine.stores                         │
│  ┌───────────────┐ ┌───────────────┐                           │
│  │  JsonStore    │ │  SqliteStore  │  (Tier 0-1, stdlib)       │
│  └───────────────┘ └───────────────┘                           │
└─────────────────────────────────────────────────────────────────┘
                          ↑ optional extras
┌─────────────────────────────────────────────────────────────────┐
│                    entityspine.adapters                         │
│  ┌─────────────────────┐ ┌─────────────────────┐               │
│  │ pydantic/ wrappers  │ │  orm/ SqlModelStore │               │
│  │ to_domain/from_dom  │ │  returns domain     │               │
│  └─────────────────────┘ └─────────────────────┘               │
│  pip install .[pydantic]  pip install .[orm]                    │
└─────────────────────────────────────────────────────────────────┘
```

**Key Principle**: All business logic lives in `entityspine.domain` as stdlib `@dataclass` classes. Stores and adapters always convert to/from these canonical types.

---

## Quick Start

```bash
# Install (zero dependencies for core)
pip install entityspine

# Verify zero-dep install works
python -c "from entityspine import Entity, SqliteStore; print('OK')"
```

### Load SEC Data + Resolve Ticker

```python
from entityspine.stores import SqliteStore

# Create Tier 1 store (stdlib sqlite3)
store = SqliteStore(":memory:")
store.initialize()

# Load from SEC company_tickers.json
import json
from pathlib import Path

sec_json = json.loads(Path("company_tickers.json").read_text())
store.load_sec_json(sec_json)

# Resolve by ticker
result = store.resolve("AAPL")
print(f"{result.entity.primary_name} (CIK: {result.entity.source_id})")
# Apple Inc. (CIK: 0000320193)

# Search by name
candidates = store.search("Apple")
for c in candidates[:3]:
    print(f"  {c.score:.2f} - {c.entity.primary_name}")
```

### Ingest Filing Facts into Knowledge Graph

```python
from entityspine import (
    Entity, EntityType, EntityStatus,
    Security, SecurityType, SecurityStatus,
    Listing, ListingStatus,
    IdentifierClaim, IdentifierScheme, VendorNamespace, ClaimStatus,
    Relationship, NodeRef, NodeKind, RelationshipType,
)
from entityspine.stores import SqliteStore

store = SqliteStore("./entities.db")
store.initialize()

# Create entity from filing
registrant = Entity(
    primary_name="NVIDIA Corporation",
    entity_type=EntityType.ORGANIZATION,
    status=EntityStatus.ACTIVE,
    jurisdiction="DE",
    source_system="sec-edgar",
    source_id="0001045810",
)
store.save_entity(registrant)

# Attach CIK identifier with evidence
cik_claim = IdentifierClaim(
    entity_id=registrant.entity_id,
    scheme=IdentifierScheme.CIK,
    value="0001045810",
    namespace=VendorNamespace.SEC,
    source_ref="0001045810-24-000029",  # Accession number
    source="sec-edgar",
    confidence=1.0,
    status=ClaimStatus.ACTIVE,
)
store.save_claim(cik_claim)

# Create supplier relationship with evidence
supplier = Entity(
    primary_name="Taiwan Semiconductor Manufacturing",
    entity_type=EntityType.ORGANIZATION,
    source_system="sec-edgar",
)
store.save_entity(supplier)

relationship = Relationship(
    source_ref=NodeRef(NodeKind.ENTITY, registrant.entity_id),
    target_ref=NodeRef(NodeKind.ENTITY, supplier.entity_id),
    relationship_type=RelationshipType.SUPPLIER,
    confidence=0.95,
    evidence_filing_id="0001045810-24-000029",
    evidence_snippet="TSMC manufactures substantially all of our GPUs...",
    source_system="sec-edgar",
)
store.save_relationship(relationship)
```

---

## Storage Tiers

| Tier | Backend | Dependencies | Use Case |
|------|---------|--------------|----------|
| 0 | JSON file | None (stdlib) | Scripts, CLI, testing |
| 1 | SQLite | None (stdlib) | Local dev, small datasets |
| 2 | DuckDB | `[duckdb]` extra | Analytics workloads |
| 3 | PostgreSQL | `[postgres]` extra | Production |

All tiers return **domain dataclasses** — upgrade storage without changing application code.

### Tier Honesty

Resolution operations warn when capabilities are limited:

```python
result = store.resolve("AAPL", as_of="2015-01-01")
if not result.as_of_honored:
    for warning in result.warnings:
        print(f"⚠ {warning}")
# ⚠ as_of parameter ignored: temporal resolution not available at Tier 1
```

---

## Installation

```bash
# Core (Tier 0-1: JSON + SQLite, zero dependencies)
pip install entityspine

# With Pydantic validation wrappers
pip install "entityspine[pydantic]"

# With SQLModel/SQLAlchemy ORM
pip install "entityspine[orm]"

# With DuckDB analytics (Tier 2)
pip install "entityspine[duckdb]"

# With PostgreSQL (Tier 3)
pip install "entityspine[postgres]"

# Full installation
pip install "entityspine[full]"

# Development
pip install "entityspine[dev]"
```

---

## Domain Models

### Core Models

| Model | Purpose | Key Fields |
|-------|---------|------------|
| `Entity` | Legal/organizational identity | `primary_name`, `entity_type`, `jurisdiction` |
| `Security` | Tradeable instrument | `security_type`, `entity_id`, `description` |
| `Listing` | Exchange-specific ticker | `ticker`, `exchange`, `mic`, `security_id` |
| `IdentifierClaim` | Identifier with provenance | `scheme`, `value`, `entity_id/security_id/listing_id` |

### Knowledge Graph Nodes

| Model | Purpose |
|-------|---------|
| `Asset` | Physical/tangible assets |
| `Contract` | Material agreements |
| `Product` | Products/services |
| `Brand` | Brand identities |
| `Event` | Discrete business events |
| `Case` | Legal proceedings |
| `Geo` | Geographic locations |
| `Address` | Physical addresses |
| `RoleAssignment` | Person→Org roles (CEO, CFO, Director) |
| `Relationship` | Generic node→node edges with evidence |

---

## Project Structure

```
entityspine/
├── src/entityspine/
│   ├── domain/              # Canonical stdlib dataclasses
│   │   ├── entity.py        # Entity (no identifiers)
│   │   ├── security.py      # Security
│   │   ├── listing.py       # Listing (ticker here)
│   │   ├── claim.py         # IdentifierClaim
│   │   ├── graph.py         # KG nodes (Asset, Contract, etc.)
│   │   ├── enums.py         # All enumerations
│   │   └── validators.py    # Normalization + validation
│   ├── stores/
│   │   ├── sqlite_store.py  # Tier 1 (stdlib sqlite3)
│   │   ├── json_store.py    # Tier 0 (JSON file)
│   │   └── mappers.py       # Domain ↔ dict conversion
│   ├── adapters/
│   │   ├── pydantic/        # Optional validation wrappers
│   │   └── orm/             # Optional SQLModel layer
│   └── core/                # Utilities (ULID, timestamps)
├── tests/                   # 285 tests, 2 skipped (optional deps)
├── examples/                # End-to-end integration proof
└── docs/                    # Architecture documentation
```

---

## Testing

```bash
# Run all tests
python -m pytest

# Run with coverage
python -m pytest --cov=entityspine --cov-report=html

# Run end-to-end example
python examples/01_end_to_end_sec_filing_to_kg.py
```

---

## Integration with py-sec-edgar / FeedSpine

EntitySpine is designed to be the canonical entity/knowledge-graph layer for SEC filing analysis pipelines:

1. **FeedSpine** extracts filing facts (entities, relationships, events)
2. **EntitySpine** persists and resolves those facts
3. **py-sec-edgar** orchestrates the pipeline

See `docs/FILING_FACTS_SCHEMA.md` for the integration contract.

---

## License

MIT License - see [LICENSE](LICENSE)

---

## Links

- **Repository**: https://github.com/ryansmccoy/entity-spine
- **Documentation**: See `docs/` directory
- **Issues**: https://github.com/ryansmccoy/entity-spine/issues
