# Building Corporate Networks

EntitySpine enables you to map relationships between companies, building knowledge graphs of corporate ecosystems. This guide shows you how to model hierarchies, ownership, supply chains, and competitive relationships.

## The Power of Entity Networks

Instead of isolated data points, build connected knowledge:

```
Apple Inc.
  ├─ Subsidiaries: Beats Electronics, Shazam
  ├─ Suppliers: TSMC, Foxconn, LG Display
  ├─ Competitors: Samsung, Google, Microsoft
  └─ Partners: Intel (until 2020), ARM Holdings
```

## Relationship Types

EntitySpine supports any relationship type you need. Common patterns:

### Corporate Structure

```python
from entityspine import Entity, Relationship

# Parent-Subsidiary
alphabet = Entity(primary_name="Alphabet Inc.", ...)
google = Entity(primary_name="Google LLC", ...)

parent_of = Relationship(
    from_entity_id=alphabet.entity_id,
    relationship_type="PARENT_OF",
    to_entity_id=google.entity_id,
    source_system="SEC",
    source="10-K Filing",
    confidence=1.0
)

# The reverse relationship is implicit, but you can model it:
subsidiary_of = Relationship(
    from_entity_id=google.entity_id,
    relationship_type="SUBSIDIARY_OF",
    to_entity_id=alphabet.entity_id,
    source_system="SEC",
    confidence=1.0
)
```

### Supply Chain

```python
# Customer-Supplier relationships
apple = Entity(primary_name="Apple Inc.", ...)
tsmc = Entity(primary_name="Taiwan Semiconductor Manufacturing Co.", ...)

# Apple is a customer of TSMC
customer_of = Relationship(
    from_entity_id=apple.entity_id,
    relationship_type="CUSTOMER_OF",
    to_entity_id=tsmc.entity_id,
    source_system="annual_report",
    source="TSMC 2024 Annual Report",
    confidence=0.95,
    metadata={
        "revenue_percentage": "~25%",  # TSMC gets 25% revenue from Apple
        "product_types": ["A-series chips", "M-series chips"]
    }
)

# TSMC is a supplier to Apple (reverse)
supplier_of = Relationship(
    from_entity_id=tsmc.entity_id,
    relationship_type="SUPPLIER_OF",
    to_entity_id=apple.entity_id,
    source_system="annual_report",
    confidence=0.95
)
```

### Competitive Landscape

```python
# Market competitors
apple = Entity(primary_name="Apple Inc.", ...)
samsung = Entity(primary_name="Samsung Electronics Co.", ...)

competes_with = Relationship(
    from_entity_id=apple.entity_id,
    relationship_type="COMPETES_WITH",
    to_entity_id=samsung.entity_id,
    source_system="market_analysis",
    source="Industry Report 2024",
    confidence=0.90,
    metadata={
        "markets": ["smartphones", "tablets", "wearables"],
        "overlap_percentage": "~70%"
    }
)
```

### Strategic Partnerships

```python
# Joint ventures, partnerships
apple = Entity(primary_name="Apple Inc.", ...)
tsmc = Entity(primary_name="Taiwan Semiconductor Manufacturing Co.", ...)

partnership = Relationship(
    from_entity_id=apple.entity_id,
    relationship_type="PARTNER",
    to_entity_id=tsmc.entity_id,
    source_system="press_release",
    source="Apple-TSMC 3nm Chip Agreement",
    start_date="2023-09-12",
    confidence=0.95,
    metadata={
        "partnership_type": "manufacturing",
        "duration": "multi-year",
        "exclusivity": "partial"
    }
)
```

## Relationship Confidence & Provenance

Always track where relationships come from:

```python
# High confidence - from official filing
official = Relationship(
    from_entity_id=parent.entity_id,
    relationship_type="PARENT_OF",
    to_entity_id=subsidiary.entity_id,
    source_system="SEC",
    source="10-K Filing - Exhibit 21",
    confidence=1.0  # Official SEC filing
)

# Medium confidence - from news article
rumored = Relationship(
    from_entity_id=acquirer.entity_id,
    relationship_type="ACQUISITION_PENDING",
    to_entity_id=target.entity_id,
    source_system="news",
    source="Bloomberg Article 2024-01-15",
    confidence=0.70  # Reported but not confirmed
)

# Lower confidence - from analyst estimate
estimated = Relationship(
    from_entity_id=company.entity_id,
    relationship_type="SUPPLIER_OF",
    to_entity_id=customer.entity_id,
    source_system="analyst_research",
    source="JPM Supply Chain Analysis",
    confidence=0.60  # Analyst estimate
)
```

## Temporal Relationships

Relationships change over time:

```python
from datetime import datetime

# Intel was Apple's chip supplier (past)
past_supplier = Relationship(
    from_entity_id=intel.entity_id,
    relationship_type="SUPPLIER_OF",
    to_entity_id=apple.entity_id,
    start_date=datetime(2006, 1, 1),
    end_date=datetime(2020, 11, 10),  # Apple switched to ARM
    source_system="historical_data",
    confidence=1.0
)

# ARM is now Apple's architecture partner (current)
current_partner = Relationship(
    from_entity_id=arm.entity_id,
    relationship_type="PARTNER",
    to_entity_id=apple.entity_id,
    start_date=datetime(2020, 11, 10),  # M1 chip launch
    source_system="press_release",
    confidence=1.0
)
```

## Building Multi-Level Hierarchies

```python
# Complex corporate structure
berkshire = Entity(primary_name="Berkshire Hathaway Inc.", ...)
geico = Entity(primary_name="GEICO Corporation", ...)
gov_employees = Entity(primary_name="Government Employees Insurance Company", ...)

# Level 1: Berkshire owns GEICO
rel1 = Relationship(
    from_entity_id=berkshire.entity_id,
    relationship_type="OWNS",
    to_entity_id=geico.entity_id,
    ownership_percentage=100.0,
    confidence=1.0
)

# Level 2: GEICO owns Government Employees Insurance Company
rel2 = Relationship(
    from_entity_id=geico.entity_id,
    relationship_type="OWNS",
    to_entity_id=gov_employees.entity_id,
    ownership_percentage=100.0,
    confidence=1.0
)

# You can traverse: Berkshire → GEICO → Gov Employees
```

## Query Patterns

### Find All Subsidiaries

```python
def get_subsidiaries(parent_id: str, store) -> list[Entity]:
    """Get all direct subsidiaries of a parent company."""
    relationships = store.query_relationships(
        from_entity_id=parent_id,
        relationship_type="PARENT_OF"
    )
    return [
        store.get_entity(rel.to_entity_id)
        for rel in relationships
    ]

# Usage
alphabet_subs = get_subsidiaries(alphabet.entity_id, store)
# Returns: [Google, YouTube, Waymo, Verily, etc.]
```

### Find All Suppliers

```python
def get_suppliers(company_id: str, store) -> list[tuple[Entity, float]]:
    """Get all suppliers with confidence scores."""
    relationships = store.query_relationships(
        to_entity_id=company_id,
        relationship_type="SUPPLIER_OF"
    )
    return [
        (store.get_entity(rel.from_entity_id), rel.confidence)
        for rel in relationships
    ]

# Usage
apple_suppliers = get_suppliers(apple.entity_id, store)
# Returns: [(TSMC, 0.95), (Foxconn, 0.90), ...]
```

### Find Competitors in Same Market

```python
def get_competitors(company_id: str, market: str, store) -> list[Entity]:
    """Get competitors in a specific market."""
    relationships = store.query_relationships(
        from_entity_id=company_id,
        relationship_type="COMPETES_WITH"
    )
    
    # Filter by market metadata
    competitors = []
    for rel in relationships:
        if rel.metadata and market in rel.metadata.get("markets", []):
            competitors.append(store.get_entity(rel.to_entity_id))
    
    return competitors

# Usage
smartphone_competitors = get_competitors(
    apple.entity_id,
    market="smartphones",
    store
)
# Returns: [Samsung, Google, Xiaomi, ...]
```

### Build Corporate Tree

```python
def build_corporate_tree(root_id: str, store, depth: int = 5) -> dict:
    """Build full corporate hierarchy tree."""
    entity = store.get_entity(root_id)
    
    tree = {
        "entity": entity,
        "subsidiaries": []
    }
    
    if depth > 0:
        subsidiaries = get_subsidiaries(root_id, store)
        tree["subsidiaries"] = [
            build_corporate_tree(sub.entity_id, store, depth - 1)
            for sub in subsidiaries
        ]
    
    return tree

# Usage
alphabet_tree = build_corporate_tree(alphabet.entity_id, store)
```

## Data Sources for Relationships

### 1. SEC Filings (Free, Authoritative)

**10-K Annual Reports**:
- Item 1 (Business): Subsidiaries, business segments
- Exhibit 21: List of significant subsidiaries

**DEF 14A Proxy Statements**:
- Board of directors connections
- Executive relationships

**8-K Current Reports**:
- Acquisitions, divestitures
- Material agreements

### 2. GLEIF (Free, Global)

**LEI Relationship Data**:
- Parent-subsidiary relationships
- Ultimate parent identification
- Cross-border ownership

```python
# Load GLEIF relationship data
from entityspine import load_gleif_relationships

relationships = load_gleif_relationships("gleif-relationships.csv")
```

### 3. Supply Chain Disclosures

**Annual Reports** (10-K Section: Risk Factors, MD&A):
- Major customers (> 10% revenue)
- Key suppliers
- Geographic concentrations

**Supplier Responsibility Reports**:
- Apple publishes full supplier list annually
- Many tech companies follow similar practices

### 4. News & Press Releases

```python
# Example: Track acquisition from announcement to close
announcement = Relationship(
    from_entity_id=acquirer.entity_id,
    relationship_type="ACQUISITION_ANNOUNCED",
    to_entity_id=target.entity_id,
    start_date=datetime(2024, 1, 15),
    source_system="press_release",
    confidence=0.80
)

closing = Relationship(
    from_entity_id=acquirer.entity_id,
    relationship_type="ACQUIRED",
    to_entity_id=target.entity_id,
    start_date=datetime(2024, 6, 30),
    source_system="SEC_8K",
    confidence=1.0
)
```

## Graph Visualization

Once you've built relationship networks, visualize them:

```python
# Export to Neo4j for graph queries
from entityspine import Neo4jStore

neo4j = Neo4jStore(uri="bolt://localhost:7687")

# All entities become nodes
neo4j.save_entity(apple)
neo4j.save_entity(google)

# All relationships become edges
neo4j.save_relationship(competes_with)

# Query with Cypher:
# MATCH (a:Entity)-[:COMPETES_WITH]->(b:Entity)
# WHERE a.primary_name = 'Apple Inc.'
# RETURN b.primary_name
```

## Best Practices

### 1. Bidirectional Relationships

Model both directions for easier queries:

```python
# Forward
parent_of = Relationship(
    from_entity_id=parent.entity_id,
    relationship_type="PARENT_OF",
    to_entity_id=child.entity_id
)

# Reverse
child_of = Relationship(
    from_entity_id=child.entity_id,
    relationship_type="SUBSIDIARY_OF",
    to_entity_id=parent.entity_id
)
```

### 2. Use Metadata for Context

```python
relationship = Relationship(
    from_entity_id=supplier.entity_id,
    relationship_type="SUPPLIER_OF",
    to_entity_id=customer.entity_id,
    metadata={
        "contract_value": "$500M",
        "contract_duration": "5 years",
        "product_categories": ["semiconductors", "displays"],
        "strategic_importance": "critical",
        "verified_date": "2024-01-15"
    }
)
```

### 3. Track Relationship Changes

```python
# Relationship evolves over time
partnership_started = Relationship(
    relationship_type="PARTNER",
    start_date=datetime(2020, 1, 1),
    end_date=datetime(2023, 12, 31),
    metadata={"partnership_type": "distribution"}
)

acquisition = Relationship(
    relationship_type="ACQUIRED",
    start_date=datetime(2024, 1, 1),
    metadata={"acquisition_price": "$2.5B"}
)
```

## Next Steps

- **[SEC Data Guide](SEC_DATA_GUIDE.md)** - Load company data from SEC
- **[Financial Markets](../guides/MARKET_DATA_ARCHITECTURE.md)** - Extend to securities and markets
- **[API Reference](../api/domain/entity.md)** - Complete entity and relationship API

