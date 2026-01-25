# EntitySpine Web - Docker Deployment

The EntitySpine web UI is automatically included in the Spine monitoring stack and is accessible to all containers on the `monitoring-net` network.

## Quick Start

```powershell
# Start everything (from project root)
cd monitoring
./start-entityspine.ps1

# Or manually
docker compose -f monitoring/docker-compose.monitoring.yml up -d
```

## Access Points

Once started, the EntitySpine web UI is available at:
- **Web Interface**: http://localhost:3002
- **API Backend**: http://localhost:8000
- **Documentation**: http://localhost:8001
- **API Docs (Swagger)**: http://localhost:8000/docs

## Container Networking

All EntitySpine services are on the `monitoring-net` Docker network, making them accessible to:
- Other containers in the monitoring stack
- Grafana (for dashboard integration)
- Promtail (for log collection)
- Uptime Kuma (for health checks)
- Any service that joins the `monitoring-net` network

### Accessing from Other Containers

From other containers on the same network, use these internal hostnames:

```yaml
# Example: Another service accessing EntitySpine API
services:
  my-service:
    networks:
      - monitoring-net
    environment:
      - ENTITYSPINE_API=http://spine-entityspine-api:8080
      - ENTITYSPINE_WEB=http://spine-entityspine-web:3000
      - ENTITYSPINE_DOCS=http://spine-entityspine-docs:8000
```

**Internal Container Names:**
- API: `spine-entityspine-api` (port 8080)
- Web: `spine-entityspine-web` (port 3000)
- Docs: `spine-entityspine-docs` (port 8000)

**External (Host) Ports:**
- API: `8000` → internal `8080`
- Web: `3002` → internal `3000`
- Docs: `8001` → internal `8000`

## Development

### Local Development (Hot Reload)

```bash
cd entityspine/web
npm install
npm start  # Runs on http://localhost:3000
```

The dev server will proxy API requests to http://localhost:8000.

### Rebuild Container

```bash
# Rebuild just the frontend
docker compose -f monitoring/docker-compose.monitoring.yml build entityspine-frontend
docker compose -f monitoring/docker-compose.monitoring.yml up -d entityspine-frontend

# Or rebuild everything
docker compose -f monitoring/docker-compose.monitoring.yml up -d --build
```

## Health Checks

The API service includes health checks that the frontend depends on:

```yaml
healthcheck:
  test: ["CMD-SHELL", "curl -f http://localhost:8080/health || exit 1"]
  interval: 30s
  timeout: 10s
  retries: 3
```

The web container will wait for the API to be healthy before starting.

## Logs

```bash
# View all EntitySpine logs
docker compose -f monitoring/docker-compose.monitoring.yml logs -f entityspine-api entityspine-frontend entityspine-docs

# Just the web UI
docker compose -f monitoring/docker-compose.monitoring.yml logs -f entityspine-frontend

# Or use Dozzle at http://localhost:9999
```

## Production Deployment

The web container uses a multi-stage build:
1. **Build stage**: Compiles React app with Node.js
2. **Production stage**: Serves static files with nginx

The nginx configuration includes:
- API proxy at `/api/*` → backend
- Gzip compression
- Browser caching
- SPA fallback routing

See [nginx.conf](nginx.conf) for details.

## Environment Variables

**Frontend (React):**
- `REACT_APP_API_URL` - API base URL (default: http://localhost:8000)
- `REACT_APP_DOCS_URL` - Docs URL (default: http://localhost:8001)

**API:**
- `ENTITYSPINE_DB_PATH` - Database location (default: /data/entities.db)
- `ENTITYSPINE_AUTO_LOAD_SEC` - Auto-load SEC data on startup (default: true)

## Stopping Services

```bash
# Stop but keep data
docker compose -f monitoring/docker-compose.monitoring.yml stop

# Stop and remove containers (data persists in volumes)
docker compose -f monitoring/docker-compose.monitoring.yml down

# Remove everything including data
docker compose -f monitoring/docker-compose.monitoring.yml down -v
```
