# Entity Master - Quick Start Guide

Get started with Entity Master in 5 minutes.

---

## Installation

```bash
# Basic installation (SQLite)
pip install entity-master

# With DuckDB support
pip install entity-master[duckdb]

# With PostgreSQL + Elasticsearch
pip install entity-master[advanced]

# Full installation (all backends + graph)
pip install entity-master[all]
```

---

## Quick Examples

### Basic Usage (30 seconds)

```python
from entity_master import EntityMaster

# Initialize (uses SQLite by default)
em = EntityMaster()

# Resolve any identifier to an entity
entity = em.resolve("AAPL")
print(f"Name: {entity.primary_name}")
print(f"CIK: {entity.cik}")
print(f"LEI: {entity.lei}")

# Convert between identifiers
cik = em.get_cik("Apple Inc")
ticker = em.get_ticker("0000320193")
```

### Batch Resolution

```python
# Resolve multiple at once
entities = em.resolve_batch(["AAPL", "MSFT", "GOOGL", "AMZN"])

for ticker, entity in entities.items():
    print(f"{ticker}: {entity.primary_name} (CIK: {entity.cik})")
```

### Search

```python
# Fuzzy search
results = em.search("apple", limit=5)
for entity in results:
    print(f"- {entity.primary_name} ({entity.ticker})")

# Autocomplete for UI
suggestions = em.autocomplete("app")
# ["Apple Inc", "Appalachian Power", "Applied Materials", ...]
```

---

## Configuration

### Basic Config File

Create `~/.entity_master/config.yaml`:

```yaml
# Tier selection (basic, intermediate, advanced, full, mindblowing)
tier: basic

# Storage settings
storage:
  type: sqlite
  path: ~/.entity_master/entities.db

# Data sources to load
sources:
  sec_tickers:
    enabled: true
    auto_update: true
    schedule: "0 6 * * *"  # Daily at 6 AM
```

### Environment Variables

```bash
# Override tier
export ENTITY_MASTER_TIER=advanced

# PostgreSQL connection
export ENTITY_MASTER_POSTGRES_DSN=postgresql://localhost/entity_master

# Elasticsearch
export ENTITY_MASTER_ES_HOSTS=http://localhost:9200

# API keys for enrichment
export OPENFIGI_API_KEY=your_key_here
export OPENAI_API_KEY=your_key_here  # For Tier 5 LLM features
```

---

## Data Loading

### Initial Setup (SEC Tickers)

```python
from entity_master import EntityMaster

em = EntityMaster()

# Load SEC tickers (~10,000 companies)
await em.load_sec_tickers()
print(f"Loaded {em.count()} entities")
```

### Add GLEIF Data

```python
# Load GLEIF golden copy (3.2M entities)
# Downloads ~3GB, takes 10-30 minutes first time
await em.load_gleif_golden_copy()
```

### Load Local Files

```python
# Load your Bloomberg files
await em.load_bloomberg_files("G:\\BLOOMBERG")

# Load Thomson files
await em.load_thomson_files("G:\\THOMSON")
```

---

## Integration with py-sec-edgar

### Simple Integration

```python
from py_sec_edgar import SECClient
from py_sec_edgar.core.identity import resolve_cik

# Resolve ticker to CIK, then download
cik = resolve_cik("AAPL")
client = SECClient()
filings = client.get_filings(cik=cik, form_type="10-K")
```

### Enhanced Client

```python
from py_sec_edgar import EnhancedSECClient

# Accepts ticker, name, CIK, or LEI
client = EnhancedSECClient()

# All of these work:
filings = client.get_filings("AAPL")
filings = client.get_filings("Apple Inc")
filings = client.get_filings("0000320193")
filings = client.get_filings("549300Q4RLWG85ULYE86")  # LEI
```

---

## CLI Commands

```bash
# Check status
entity-master status

# Load data
entity-master load sec-tickers
entity-master load gleif --golden-copy
entity-master load file G:\BLOOMBERG\*.csv --format bloomberg

# Resolve identifiers
entity-master resolve AAPL
entity-master resolve "Apple Inc" --format json

# Search
entity-master search "semiconductor" --limit 10

# Enrich entity
entity-master enrich AAPL --sources sec,gleif,openfigi

# Export data
entity-master export --format parquet --output entities.parquet
entity-master export --format csv --output entities.csv
```

---

## Upgrading Tiers

### Basic → Intermediate

```bash
# Export from SQLite
entity-master export --output backup.parquet

# Update config
entity-master config set tier intermediate

# Import to DuckDB
entity-master import backup.parquet
```

### Intermediate → Advanced

```bash
# Start PostgreSQL
docker run -d --name entity-master-postgres \
  -e POSTGRES_DB=entity_master \
  -e POSTGRES_PASSWORD=secret \
  -p 5432:5432 \
  postgres:15

# Start Elasticsearch
docker run -d --name entity-master-es \
  -e "discovery.type=single-node" \
  -p 9200:9200 \
  elasticsearch:8.11.0

# Update config
entity-master config set tier advanced
entity-master config set postgres_dsn postgresql://postgres:secret@localhost/entity_master
entity-master config set elasticsearch_hosts http://localhost:9200

# Migrate data
entity-master migrate --from duckdb --to postgres
```

---

## Docker Quick Start

```yaml
# docker-compose.yml
version: '3.8'

services:
  entity-master:
    image: entity-master:latest
    ports:
      - "8000:8000"
    environment:
      - ENTITY_MASTER_TIER=advanced
      - ENTITY_MASTER_POSTGRES_DSN=postgresql://postgres:secret@postgres/entity_master
      - ENTITY_MASTER_ES_HOSTS=http://elasticsearch:9200
    depends_on:
      - postgres
      - elasticsearch

  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB=entity_master
      - POSTGRES_PASSWORD=secret
    volumes:
      - postgres_data:/var/lib/postgresql/data

  elasticsearch:
    image: elasticsearch:8.11.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
    volumes:
      - es_data:/usr/share/elasticsearch/data

volumes:
  postgres_data:
  es_data:
```

```bash
# Start everything
docker-compose up -d

# Load data
docker-compose exec entity-master entity-master load sec-tickers

# Access API
curl http://localhost:8000/resolve/AAPL
```

---

## Next Steps

1. **[01_TIERED_ARCHITECTURE.md](01_TIERED_ARCHITECTURE.md)** - Understand the tier system
2. **[02_STORAGE_BACKENDS.md](02_STORAGE_BACKENDS.md)** - Storage implementation details
3. **[03_FEEDSPINE_INTEGRATION.md](03_FEEDSPINE_INTEGRATION.md)** - Automated data feeds
4. **[04_API_DESIGN.md](04_API_DESIGN.md)** - Full API reference
5. **[05_ENRICHMENT_PIPELINE.md](05_ENRICHMENT_PIPELINE.md)** - External enrichment
6. **[06_RELATIONSHIP_GRAPH.md](06_RELATIONSHIP_GRAPH.md)** - Knowledge graph features

---

## Common Patterns

### Caching Resolutions

```python
from functools import lru_cache
from entity_master import EntityMaster

em = EntityMaster()

@lru_cache(maxsize=10000)
def cached_resolve(identifier: str):
    return em.resolve(identifier)
```

### Async Usage

```python
import asyncio
from entity_master import AsyncEntityMaster

async def main():
    async with AsyncEntityMaster() as em:
        entities = await asyncio.gather(
            em.resolve("AAPL"),
            em.resolve("MSFT"),
            em.resolve("GOOGL"),
        )
        for entity in entities:
            print(entity.primary_name)

asyncio.run(main())
```

### Error Handling

```python
from entity_master import EntityMaster, EntityNotFound, AmbiguousMatch

em = EntityMaster()

try:
    entity = em.resolve("XYZ")
except EntityNotFound:
    print("Entity not found")
except AmbiguousMatch as e:
    print(f"Multiple matches: {e.candidates}")
```
