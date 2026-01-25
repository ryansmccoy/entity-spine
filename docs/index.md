# EntitySpine

<div class="grid cards" markdown>

- :material-speedometer:{ .lg .middle } **Lightweight & Fast**

    ---

    Zero dependencies for core domain models. Pure Python dataclasses
    that work anywhere.

- :material-link-variant:{ .lg .middle } **Multi-Vendor Crosswalks**

    ---

    Link identifiers across FactSet, Bloomberg, Reuters, and SEC data
    with full provenance tracking.

- :material-database-outline:{ .lg .middle } **Tiered Storage**

    ---

    From JSON files to PostgreSQL - scale from prototypes to production
    with the same domain models.

- :material-graph:{ .lg .middle } **Knowledge Graph Ready**

    ---

    Model corporate hierarchies, ownership, supply chains, and events
    as graph relationships.

</div>

---

**EntitySpine** is a lightweight entity resolution library for financial data.
It provides a clean domain model for representing companies, securities, identifiers,
and their relationships - enabling you to build entity-centric data pipelines.

## Quick Example

```python
from entityspine.domain import Entity, IdentifierClaim, IdentifierScheme
from entityspine.domain.enums import EntityType, VendorNamespace

# Create an entity
apple = Entity(
    primary_name="Apple Inc.",
    entity_type=EntityType.ORGANIZATION,
    jurisdiction="US-DE",
    source_system="sec",
)

# Add identifier claims from multiple vendors
cik_claim = IdentifierClaim(
    scheme=IdentifierScheme.CIK,
    value="0000320193",
    entity_id=apple.entity_id,
    namespace=VendorNamespace.SEC,
    source="company_tickers.json",
)

lei_claim = IdentifierClaim(
    scheme=IdentifierScheme.LEI,
    value="HWUPKR0MPOU8FGXBT394",
    entity_id=apple.entity_id,
    namespace=VendorNamespace.GLEIF,
    source="GLEIF Golden Copy",
)
```

## Key Features

### 🏢 Entity Resolution

Match and deduplicate entities across data sources using identifier crosswalks,
name matching, and configurable resolution strategies.

### 📊 FactSet Integration

First-class support for FactSet Standard Data Feeds including:

- **Symbology**: CUSIP, ISIN, SEDOL, LEI crosswalks
- **Events**: Earnings calendar, dividends, corporate actions
- **People**: Executives, board members, compensation
- **Ownership**: Institutional and insider holdings
- **Supply Chain**: Revere supplier/customer relationships

### 🔗 Knowledge Graph

Model complex relationships between entities:

- Corporate hierarchy (subsidiaries, parent companies)
- Ownership structures (shareholders, beneficial owners)
- Business relationships (suppliers, customers, partners)
- Events and corporate actions

### ⚖️ Compliance Support

Track sanctions and compliance status with built-in support for:

- OFAC SDN List identifiers
- UN/EU/UK sanctions lists
- PEP (Politically Exposed Persons) tracking
- Adverse media references

## Installation

```bash
# Core (zero dependencies)
pip install entityspine

# With FactSet loaders
pip install entityspine[factset]

# With all optional dependencies
pip install entityspine[full]
```

## Storage Tiers

EntitySpine supports multiple storage backends:

| Tier | Backend | Use Case |
|------|---------|----------|
| 0 | JSON files | Development, prototyping |
| 1 | SQLite | Local production, testing |
| 2 | DuckDB | Analytics, large datasets |
| 3 | PostgreSQL | Production, multi-user |

## Next Steps

- [Installation & Quick Start](README.md) - Get started with EntitySpine
- [v0.3.3 Release Notes](DOCUMENTATION_REVIEW.md) - What's new in this release
- [Feature Matrix](FEATURE_MATRIX.md) - Complete feature support overview
- [Tier Architecture](architecture/ARCHITECTURE_AND_TIERS.md) - Understand storage tiers
- [API Reference](api/domain/index.md) - Full API documentation
- [Development Guidelines](GUARDRAILS.md) - Contributing to EntitySpine

## License

MIT License - see [LICENSE](https://github.com/ryansmccoy/entity-spine/blob/main/LICENSE) for details.
