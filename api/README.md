# EntitySpine API

**Fast identifier resolution service: CIK ↔ Ticker ↔ Name ↔ ISIN ↔ LEI**

A simple REST API that resolves financial identifiers. Just spin it up and never worry about symbology again.

## Quick Start

### Using Docker (Recommended)

```bash
# Build and run
docker-compose up -d

# Or build manually
docker build -t entityspine-api .
docker run -p 8080:8080 -v ~/.entityspine:/data entityspine-api
```

### Running Locally

```bash
# Install dependencies
pip install fastapi uvicorn

# Set database path
export ENTITYSPINE_DB_PATH=~/.entityspine/entityspine.db

# Run
cd entityspine
PYTHONPATH=src:. uvicorn api.main:app --host 0.0.0.0 --port 8080
```

## API Endpoints

### Single Lookups

| Endpoint | Description | Example |
|----------|-------------|---------|
| `GET /ticker/{query}` | Get ticker from CIK/name | `/ticker/0000320193` → `AAPL` |
| `GET /cik/{query}` | Get CIK from ticker/name | `/cik/NVDA` → `0001045810` |
| `GET /name/{query}` | Get company name | `/name/MSFT` → `MICROSOFT CORP` |
| `GET /resolve/{query}` | Get all info at once | `/resolve/GOOGL` |

### ISIN/LEI Lookups

| Endpoint | Description | Example |
|----------|-------------|---------|
| `GET /lei/{isin}` | Get LEI from ISIN | `/lei/US0378331005` → `HWUPKR0MPOU8FGXBT394` |
| `GET /isins/{lei}` | Get all ISINs for LEI | `/isins/HWUPKR0MPOU8FGXBT394` |
| `GET /bic/{lei}` | Get BIC from LEI | `/bic/{lei}` |

### Batch Lookups

```bash
# POST /batch/tickers
curl -X POST http://localhost:8080/batch/tickers \
  -H "Content-Type: application/json" \
  -d '{"queries": ["0000320193", "0001018724", "0001652044"]}'

# Response:
# {"results": {"0000320193": "AAPL", "0001018724": "AMZN", "0001652044": "GOOGL"}}
```

### System & Scheduler

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Health check |
| `GET /info` | Database statistics |
| `GET /scheduler/status` | Refresh scheduler status |
| `POST /refresh/sec` | Trigger SEC data refresh |
| `POST /refresh/all` | Trigger full data refresh |
| `GET /` | Swagger UI docs |

## Auto-Refresh Scheduler

The API includes a background scheduler that automatically refreshes data:

| Data Source | Refresh Interval | Notes |
|-------------|------------------|-------|
| SEC company_tickers.json | Daily (24h) | ~8,000 companies |
| GLEIF LEI-ISIN | Weekly (168h) | Large file, manual for now |

### Scheduler Configuration

```bash
# Disable auto-refresh (default: enabled)
export ENTITYSPINE_AUTO_REFRESH=false

# Check scheduler status
curl http://localhost:8080/scheduler/status

# Manually trigger refresh
curl -X POST http://localhost:8080/refresh/sec
```

### CLI Refresh

```bash
# Check status
python -m api.scheduler status

# Refresh SEC data
python -m api.scheduler refresh-sec

# Refresh all data
python -m api.scheduler refresh-all
```

### Cron Job Setup

For production, set up a cron job:

```bash
# Add to crontab (daily at 6am)
0 6 * * * cd /app && python -m api.scheduler refresh-sec >> /var/log/entityspine-refresh.log 2>&1
```

## Python Client

```python
from entityspine.api.client import EntitySpineClient

client = EntitySpineClient("http://localhost:8080")

# Single lookups
client.ticker("0000320193")  # "AAPL"
client.cik("NVDA")           # "0001045810"
client.name("MSFT")          # "Microsoft Corporation"

# ISIN/LEI
client.lei_from_isin("US0378331005")  # "HWUPKR0MPOU8FGXBT394"

# Batch (for DataFrames)
client.tickers(["0000320193", "0001018724", "0001652044"])
# {"0000320193": "AAPL", "0001018724": "AMZN", "0001652044": "GOOGL"}
```

Or use environment variable:

```python
import os
os.environ["ENTITYSPINE_API_URL"] = "http://entityspine:8080"

from entityspine.api.client import ticker, cik, name

ticker("0000320193")  # "AAPL"
```

## Database

The API expects an EntitySpine database at `/data/entityspine.db` (in Docker) or `ENTITYSPINE_DB_PATH`.

To populate the database:

```bash
# Load all reference data (SEC + GLEIF)
python scripts/load_all_reference_data.py
```

This loads:
- ~8,000 SEC companies (CIK/ticker/name)
- ~7.8 million ISIN↔LEI mappings
- ~40,000 LEI↔BIC mappings

## Data Sources

| Source | Records | Description |
|--------|---------|-------------|
| SEC company_tickers.json | 8,042 | US public companies |
| GLEIF LEI-ISIN | 7,826,193 | Global ISIN to LEI mappings |
| GLEIF LEI-BIC | 39,461 | Bank identifier codes |

## Deployment

For production:

```yaml
# docker-compose.yml
services:
  entityspine:
    image: entityspine-api:latest
    ports:
      - "8080:8080"
    volumes:
      - /path/to/entityspine.db:/data/entityspine.db:ro
    restart: unless-stopped
```

Or on AWS/EC2:

```bash
# Copy database
scp ~/.entityspine/entityspine.db ec2-user@your-server:/data/

# Run container
docker run -d -p 8080:8080 \
  -v /data/entityspine.db:/data/entityspine.db:ro \
  --name entityspine \
  entityspine-api
```

## License

MIT
