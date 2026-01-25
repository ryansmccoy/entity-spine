# EntitySpine Features

**Comprehensive feature list organized by capability**

*Updated: February 2026*

---

## Quick Reference

| Category | Features | Status |
|----------|----------|--------|
| Entity Resolution | 8 | ✅ Stable |
| Storage Backends | 4 tiers | ✅ Stable |
| Identifier Validation | 10+ schemes | ✅ Stable |
| Knowledge Graph | 12 node types | ✅ Stable |
| API/CLI | REST + CLI | ✅ Stable |
| Integrations | FeedSpine, SEC | ✅ Stable |

---

## 1. Entity Resolution

### Core Resolution
- **Multi-identifier resolution** - Resolve CIK, ticker, CUSIP, ISIN, LEI, FIGI, SEDOL
- **Confidence scoring** - Each resolution includes confidence (0.0-1.0)
- **Candidate ranking** - Multiple matches ranked by likelihood
- **Resolution tiers** - Exact → Fuzzy → Cross-reference

### Resolution API
```python
from entityspine import EntityManager

manager = EntityManager(storage="sqlite://./entities.db")

# Single resolution
result = manager.resolve("AAPL")
print(result.entity.primary_name)  # Apple Inc.
print(result.confidence)           # 0.98

# Batch resolution
results = manager.resolve_batch(["AAPL", "MSFT", "0000320193"])
```

### Match Reasons
| Reason | Description |
|--------|-------------|
| `TICKER_EXACT` | Exact ticker match |
| `CIK_EXACT` | Exact CIK match |
| `CUSIP_EXACT` | Exact CUSIP match |
| `NAME_FUZZY` | Fuzzy name match |
| `CROSS_REFERENCE` | Via related identifier |

---

## 2. Storage Tiers

### Tier 0: JSON (Zero Dependencies)
```python
manager = EntityManager(storage="json://./data/entities.json")
```
- Pure Python stdlib
- Human-readable files
- Best for: Development, debugging, small datasets

### Tier 1: SQLite (Stdlib Only)
```python
manager = EntityManager(storage="sqlite://./data/entities.db")
```
- Uses `sqlite3` (stdlib)
- ACID transactions
- Best for: Single-user, local applications

### Tier 2: DuckDB (Analytics)
```python
# pip install entityspine[duckdb]
manager = EntityManager(storage="duckdb://./data/entities.duckdb")
```
- Columnar storage
- Fast analytics queries
- Best for: Data analysis, batch processing

### Tier 3: PostgreSQL (Production)
```python
# pip install entityspine[postgres]
manager = EntityManager(storage="postgresql://user:pass@localhost/entities")
```
- Multi-user concurrent access
- Full ACID compliance
- Best for: Production deployments

---

## 3. Domain Models

### Entity (Core)
The legal/organizational identity:
```python
from entityspine import Entity

entity = Entity(
    id="ent_abc123",
    primary_name="Apple Inc.",
    entity_type=EntityType.CORPORATION,
    source_system="sec",
    source_id="0000320193",
    status=EntityStatus.ACTIVE
)
```

### Security
A tradeable instrument issued by an Entity:
```python
from entityspine import Security

security = Security(
    id="sec_xyz789",
    entity_id="ent_abc123",
    name="Apple Inc. Common Stock",
    security_type=SecurityType.COMMON_STOCK,
    cusip="037833100"
)
```

### Listing
An exchange-specific ticker:
```python
from entityspine import Listing

listing = Listing(
    id="lst_001",
    security_id="sec_xyz789",
    ticker="AAPL",
    exchange="NASDAQ",
    mic="XNAS"
)
```

### IdentifierClaim
Every identifier is a claim with provenance:
```python
from entityspine import IdentifierClaim

claim = IdentifierClaim(
    entity_id="ent_abc123",
    scheme=IdentifierScheme.CIK,
    value="0000320193",
    status=ClaimStatus.VERIFIED,
    source="sec_company_tickers",
    confidence=0.99,
    valid_from="2020-01-01"
)
```

---

## 4. Identifier Validation

### Supported Schemes
| Scheme | Validation | Normalization |
|--------|------------|---------------|
| CIK | 10-digit, checksum | Zero-pad |
| CUSIP | 9-char, checksum | Uppercase |
| ISIN | 12-char, checksum | Uppercase |
| LEI | 20-char, checksum | Uppercase |
| FIGI | 12-char, format | Uppercase |
| SEDOL | 7-char, checksum | Uppercase |
| Ticker | Alpha-numeric | Uppercase |
| EIN | 9-digit, format | Formatted |
| MIC | 4-char ISO 10383 | Uppercase |

### Usage
```python
from entityspine import validate_cusip, normalize_cik

# Validation returns bool
validate_cusip("037833100")  # True

# Normalization formats correctly
normalize_cik("320193")  # "0000320193"
```

---

## 5. Knowledge Graph

### Node Types
- **Entity** - Legal organizations
- **Person** - Individuals
- **Security** - Tradeable instruments
- **Listing** - Exchange tickers
- **Address** - Physical locations
- **Event** - Corporate actions
- **Filing** - SEC submissions
- **Role** - Employment/board positions
- **Relationship** - Entity connections
- **Brand** - Product brands
- **Product** - Individual products
- **Contract** - Agreements

### Relationship Types
```python
# Entity → Person (employment)
manager.add_relationship(
    source_id="ent_abc123",
    target_id="per_xyz789",
    relationship_type="employs"
)

# Entity → Entity (subsidiary)
manager.add_relationship(
    source_id="ent_parent",
    target_id="ent_child",
    relationship_type="owns_subsidiary"
)
```

---

## 6. SEC Integration

### Load SEC Data
```python
# Load from company_tickers.json
manager.load_sec_company_tickers()

# Load from company_tickers_exchange.json
manager.load_sec_company_tickers_exchange()

# Load from company_tickers_mf.json (mutual funds)
manager.load_sec_mutual_funds()
```

### SEC-Specific Resolution
```python
# Resolve by CIK
result = manager.resolve_by_cik("0000320193")

# Search by company name
results = manager.search("Apple", entity_type=EntityType.CORPORATION)
```

---

## 7. API & CLI

### REST API (FastAPI)
```bash
# Start server
uvicorn entityspine.api:app --port 8000
```

Endpoints:
- `GET /entities/{id}` - Get entity by ID
- `GET /resolve/{identifier}` - Resolve identifier
- `POST /resolve/batch` - Batch resolution
- `GET /search?q={query}` - Search entities

### CLI
```bash
# Resolve identifier
entityspine resolve AAPL

# Search entities
entityspine search "Apple Inc"

# Load SEC data
entityspine load-sec --source company_tickers

# Export to JSON
entityspine export --format json --output entities.json
```

---

## 8. FeedSpine Integration

### Extracting Entities from Feeds
```python
from entityspine.integration.feedspine import FeedEntityExtractor
from feedspine import FeedItem

extractor = FeedEntityExtractor(manager)

item = FeedItem(
    id="item1",
    title="Apple reports Q4 earnings",
    content="Tim Cook announced...",
    link="https://example.com"
)

# Extract and store entities
entities = extractor.extract_from_item(item)
```

---

## 9. Deduplication

### Entity Clustering
```python
# Find potential duplicates
duplicates = manager.find_duplicates(threshold=0.85)

# Merge entities
manager.merge_entities(
    primary_id="ent_abc123",
    duplicate_id="ent_xyz789",
    strategy="keep_primary"
)
```

### Deduplication Strategies
- `keep_primary` - Keep primary entity attributes
- `keep_most_complete` - Keep entity with most data
- `merge_all` - Combine all attributes

---

## 10. Audit Trail

### Change Tracking
```python
# Get entity history
history = manager.get_history("ent_abc123")

# Get state at specific time
state = manager.get_state_at("ent_abc123", "2025-01-15")

# Revert to previous state
manager.revert("ent_abc123", version=3)
```

---

## Installation

```bash
# Core (stdlib only)
pip install entityspine

# With DuckDB
pip install entityspine[duckdb]

# With PostgreSQL
pip install entityspine[postgres]

# All features
pip install entityspine[all]
```

---

## What's Next

See [TODO.md](TODO.md) for planned features and [CHANGELOG.md](../CHANGELOG.md) for version history.
