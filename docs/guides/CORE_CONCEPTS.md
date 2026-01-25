# Core Concepts

EntitySpine is built on a few simple, powerful concepts. This guide explains the fundamental building blocks.

## The Entity Model

Everything starts with **entities** - companies, people, organizations, or anything else you need to track.

```python
from entityspine import Entity

apple = Entity(
    primary_name="Apple Inc.",
    entity_type="ORGANIZATION",
    source_system="SEC",
    source_id="0000320193"  # CIK number
)
```

**That's it.** No database required. No dependencies. Just a Python dataclass.

## The Three Core Concepts

### 1. Entities

**What they are**: The "things" you're tracking - companies, people, organizations.

**Why they matter**: Everything connects to entities. They're the nodes in your knowledge graph.

**Key properties**:
- `entity_id`: Unique identifier (auto-generated ULID)
- `primary_name`: The name you primarily use
- `entity_type`: ORGANIZATION, PERSON, or INSTRUMENT
- `source_system`: Where this entity came from (e.g., "SEC", "GLEIF")

```python
# A company
apple = Entity(
    primary_name="Apple Inc.",
    entity_type="ORGANIZATION"
)

# A person
tim_cook = Entity(
    primary_name="Timothy Cook",
    entity_type="PERSON"
)

# A security
aapl_stock = Entity(
    primary_name="AAPL Common Stock",
    entity_type="INSTRUMENT"
)
```

### 2. Identifier Claims

**What they are**: Ways to identify the same entity across different systems.

**Why they matter**: Apple is known as:
- CIK `0000320193` (SEC)
- LEI `HWUPKR0MPOU8FGXBT394` (GLEIF)
- Ticker `AAPL` (NASDAQ)
- CUSIP `037833100` (bond/stock markets)

**How EntitySpine handles this**: Store each identifier as a "claim" with provenance.

```python
from entityspine import IdentifierClaim

# SEC knows Apple as CIK 0000320193
cik_claim = IdentifierClaim(
    entity_id=apple.entity_id,
    scheme="CIK",
    identifier="0000320193",
    source_system="SEC",
    source="company_tickers.json",
    confidence=1.0  # 100% confident - it's official data
)

# GLEIF knows Apple as LEI HWUPKR0MPOU8FGXBT394
lei_claim = IdentifierClaim(
    entity_id=apple.entity_id,
    scheme="LEI",
    identifier="HWUPKR0MPOU8FGXBT394",
    source_system="GLEIF",
    source="GLEIF Golden Copy",
    confidence=1.0
)

# Now you can find Apple by either CIK or LEI
```

**The power**: You always know:
- What the identifier is
- What system it came from
- How confident you are
- When it was valid (temporal support)

### 3. Relationships

**What they are**: Connections between entities.

**Why they matter**: Companies don't exist in isolation. They have:
- Parent companies and subsidiaries
- Suppliers and customers
- Competitors
- Partners

```python
from entityspine import Relationship

# Alphabet owns Google
parent_of = Relationship(
    from_entity_id=alphabet.entity_id,
    relationship_type="PARENT_OF",
    to_entity_id=google.entity_id,
    source_system="SEC",
    confidence=1.0
)

# Apple competes with Samsung
competes_with = Relationship(
    from_entity_id=apple.entity_id,
    relationship_type="COMPETES_WITH",
    to_entity_id=samsung.entity_id,
    source_system="market_analysis",
    confidence=0.85  # Analyst estimate
)
```

**The power**: Build knowledge graphs of entire industries.

## The Philosophy: Claims, Not Facts

EntitySpine doesn't store "facts" - it stores **claims** about entities.

**Why?** Because:
1. Different sources may disagree
2. Data changes over time
3. Some sources are more trustworthy than others

**Example**: Apple's name

```python
# Official SEC name
official_name = IdentifierClaim(
    entity_id=apple.entity_id,
    scheme="NAME",
    identifier="Apple Inc.",
    source_system="SEC",
    confidence=1.0
)

# Common variant
common_name = IdentifierClaim(
    entity_id=apple.entity_id,
    scheme="NAME",
    identifier="Apple",
    source_system="news_articles",
    confidence=0.90
)

# Historical name
old_name = IdentifierClaim(
    entity_id=apple.entity_id,
    scheme="NAME",
    identifier="Apple Computer, Inc.",
    source_system="SEC",
    valid_from=datetime(1977, 1, 3),
    valid_to=datetime(2007, 1, 9),
    confidence=1.0
)
```

All three are valid claims. EntitySpine tracks them all, and you decide which to use.

## Zero Dependencies Philosophy

EntitySpine core has **zero dependencies**.

```python
# This works with just Python stdlib:
from entityspine import Entity, IdentifierClaim, Relationship

apple = Entity(primary_name="Apple Inc.")
claim = IdentifierClaim(
    entity_id=apple.entity_id,
    scheme="CIK",
    identifier="0000320193"
)
relationship = Relationship(
    from_entity_id=parent.entity_id,
    relationship_type="PARENT_OF",
    to_entity_id=child.entity_id
)

# Store in JSON (still zero deps)
from entityspine import JsonStore

store = JsonStore("data/entities")
store.save(apple)
store.save(claim)
```

**Add dependencies only when you need them**:
- SQLite: Built into Python (Tier 1)
- PostgreSQL: `pip install psycopg2` (Tier 3)
- Neo4j: `pip install neo4j` (Tier 5)

## Progression: Start Simple, Grow Complex

EntitySpine is designed to grow with you:

### Level 1: Single Entity

```python
# Just track one company
apple = Entity(primary_name="Apple Inc.")
```

### Level 2: Add Identifiers

```python
# Link to external systems
cik = IdentifierClaim(entity_id=apple.entity_id, scheme="CIK", ...)
lei = IdentifierClaim(entity_id=apple.entity_id, scheme="LEI", ...)
ticker = IdentifierClaim(entity_id=apple.entity_id, scheme="TICKER", ...)
```

### Level 3: Build Networks

```python
# Map relationships
parent_of = Relationship(
    from_entity_id=alphabet.entity_id,
    to_entity_id=google.entity_id,
    relationship_type="PARENT_OF"
)
```

### Level 4: Scale Storage

```python
# Start with JSON
json_store = JsonStore("data")

# Grow to SQLite
sqlite_store = SqliteStore("entities.db")

# Scale to PostgreSQL
postgres_store = PostgresStore("postgresql://...")

# Same API, different backends
```

### Level 5: Add Graph Queries

```python
# Complex graph traversal
neo4j_store = Neo4jStore("bolt://localhost")

# Query with Cypher:
# MATCH (a)-[:SUPPLIER_OF*1..3]->(b)
# WHERE a.name = 'TSMC'
# RETURN b
```

## Common Patterns

### Pattern 1: Load SEC Data

```python
from entityspine import load_sec_data, SqliteStore

# Download 14K+ companies from SEC
entities = load_sec_data()

# Store locally
store = SqliteStore("companies.db")
for entity in entities:
    store.save(entity)
```

### Pattern 2: Cross-Reference Identifiers

```python
# Find entity by any identifier
def find_entity_by_identifier(
    scheme: str,
    identifier: str,
    store
) -> Entity | None:
    claims = store.query_claims(
        scheme=scheme,
        identifier=identifier
    )
    if claims:
        return store.get_entity(claims[0].entity_id)
    return None

# Usage
apple_by_cik = find_entity_by_identifier("CIK", "0000320193", store)
apple_by_ticker = find_entity_by_identifier("TICKER", "AAPL", store)
# Both return the same entity
```

### Pattern 3: Track Provenance

```python
# You can always ask: "Where did this data come from?"
for claim in store.query_claims(entity_id=apple.entity_id):
    print(f"{claim.scheme}:{claim.identifier}")
    print(f"  Source: {claim.source_system}")
    print(f"  From: {claim.source}")
    print(f"  Confidence: {claim.confidence}")
```

Output:
```
CIK:0000320193
  Source: SEC
  From: company_tickers.json
  Confidence: 1.0

LEI:HWUPKR0MPOU8FGXBT394
  Source: GLEIF
  From: GLEIF Golden Copy
  Confidence: 1.0

TICKER:AAPL
  Source: NASDAQ
  From: Symbology Feed
  Confidence: 0.95
```

## Identifier Schemes

EntitySpine supports any identifier scheme. Common ones:

| Scheme | What It Is | Issuer | Coverage |
|--------|------------|--------|----------|
| **CIK** | Central Index Key | SEC | US public companies |
| **LEI** | Legal Entity Identifier | GLEIF | Global companies (2M+) |
| **TICKER** | Stock ticker symbol | Exchanges | Listed securities |
| **CUSIP** | Security identifier | CUSIP Global | US/Canada securities |
| **ISIN** | International security ID | ISO | Global securities |
| **SEDOL** | Stock exchange ID | LSE | UK securities |
| **FIGI** | Financial Instrument ID | Bloomberg | Global securities |
| **PermID** | Permanent identifier | Refinitiv | Global entities |

**You can add your own**:

```python
# Custom internal ID
internal_claim = IdentifierClaim(
    entity_id=entity.entity_id,
    scheme="INTERNAL_CRM_ID",
    identifier="CUST-12345",
    source_system="salesforce",
    confidence=1.0
)
```

## Time Handling

EntitySpine tracks when data is valid:

```python
from datetime import datetime

# Ticker change: FB → META
old_ticker = IdentifierClaim(
    entity_id=meta.entity_id,
    scheme="TICKER",
    identifier="FB",
    valid_from=datetime(2012, 5, 18),
    valid_to=datetime(2022, 6, 9),
    confidence=1.0
)

new_ticker = IdentifierClaim(
    entity_id=meta.entity_id,
    scheme="TICKER",
    identifier="META",
    valid_from=datetime(2022, 6, 9),
    confidence=1.0
)

# Query: "What was Meta's ticker in 2020?"
# Answer: FB

# Query: "What is Meta's ticker today?"
# Answer: META
```

## Next Steps

- **[Working with SEC Data](SEC_DATA_GUIDE.md)** - Load real company data
- **[Building Corporate Networks](CORPORATE_NETWORKS.md)** - Map relationships
- **[Storage Tiers](../architecture/ARCHITECTURE_AND_TIERS.md)** - Scale from JSON to PostgreSQL
- **[API Reference](../api/domain/index.md)** - Complete API documentation

