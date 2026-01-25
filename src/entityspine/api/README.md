# EntitySpine REST API

A FastAPI-based REST API for entity resolution.

## Quick Start

```bash
# Install with API dependencies
pip install entityspine[api]

# Run the server
uvicorn entityspine.api.app:app --reload
```

Then visit: http://localhost:8000/docs

## Endpoints

### Health & Info

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check with database status |
| `/info` | GET | API information and available endpoints |

### Resolution

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/resolve/{query}` | GET | Resolve any identifier (ticker, CIK, ISIN, name) |
| `/resolve/batch` | POST | Batch resolution for multiple identifiers |

### Entity Lookup

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/entities/cik/{cik}` | GET | Get entity by SEC CIK |
| `/entities/ticker/{ticker}` | GET | Get entity by ticker symbol |
| `/entities/{entity_id}` | GET | Get entity by internal ID |

### Search

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/search` | GET | Search entities with fuzzy matching |

### Conversion

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/convert` | GET | Convert between identifier schemes |

## Examples

### Resolve a Ticker

```bash
curl http://localhost:8000/resolve/AAPL
```

Response:
```json
{
  "query": "AAPL",
  "status": "found",
  "entity": {
    "entity_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
    "primary_name": "Apple Inc.",
    "entity_type": "company",
    "status": "active",
    "source_system": "sec",
    "source_id": "0000320193"
  },
  "confidence": 1.0,
  "match_reason": "exact_ticker",
  "tier": "tier_1",
  "elapsed_ms": 12.5
}
```

### Batch Resolution

```bash
curl -X POST http://localhost:8000/resolve/batch \
  -H "Content-Type: application/json" \
  -d '{"queries": ["AAPL", "MSFT", "GOOGL"]}'
```

Response:
```json
{
  "results": {
    "AAPL": {"query": "AAPL", "status": "found", ...},
    "MSFT": {"query": "MSFT", "status": "found", ...},
    "GOOGL": {"query": "GOOGL", "status": "found", ...}
  },
  "total": 3,
  "resolved": 3,
  "not_found": 0,
  "elapsed_ms": 35.2
}
```

### Search Entities

```bash
curl "http://localhost:8000/search?q=apple&limit=5"
```

## Configuration

Set environment variables:

```bash
# Database path (default: in-memory)
export ENTITYSPINE_DB_PATH=/path/to/entities.db

# Auto-load SEC data (default: true)
export ENTITYSPINE_AUTO_LOAD_SEC=true

# Fuzzy matching threshold (default: 0.6)
export ENTITYSPINE_MIN_FUZZY_SCORE=0.6

# Max candidates to return (default: 10)
export ENTITYSPINE_MAX_CANDIDATES=10
```

## OpenAPI Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI JSON: http://localhost:8000/openapi.json

## Development

```bash
# Run tests
pytest tests/api/test_api.py -v

# Run with auto-reload
uvicorn entityspine.api.app:app --reload --port 8000
```
