# Entity Spine Backend API - Overview

## Introduction

Entity Spine Backend is a **FastAPI-based REST API** for financial data analysis, SEC filing exploration, and knowledge graph visualization. This document provides a comprehensive overview of the API architecture, endpoints, and usage patterns.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Entity Spine API                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  Companies   │  │   Filings    │  │   Knowledge Graph    │  │
│  │    API       │  │     API      │  │       API            │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
│         │                │                     │                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │   Search     │  │  Watchlists  │  │     Analytics        │  │
│  │    API       │  │     API      │  │       API            │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                     Service Layer                               │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  CompanyService │ FilingService │ EntityService │ etc.  │   │
│  └─────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────┤
│                     Data Access Layer                           │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │    SQLAlchemy Models    │    Pydantic Schemas           │   │
│  └─────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────┤
│                     Database Layer                              │
│  ┌───────────┐  ┌───────────┐  ┌───────────────────────────┐   │
│  │PostgreSQL │  │   Redis   │  │     Elasticsearch         │   │
│  │  (Primary)│  │  (Cache)  │  │      (Search)             │   │
│  └───────────┘  └───────────┘  └───────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Core Concepts

### 1. Companies
Companies are the central entity in Entity Spine. Each company is identified by:
- **CIK** (Central Index Key) - SEC's unique identifier
- **Ticker** - Stock symbol (e.g., AAPL, MSFT)
- **CUSIP/ISIN/LEI** - Other standard identifiers

### 2. Filings
SEC filings associated with companies:
- **10-K** - Annual reports
- **10-Q** - Quarterly reports
- **8-K** - Current reports (material events)
- **DEF 14A** - Proxy statements
- **Form 4** - Insider transactions

### 3. Knowledge Graph
Entities and relationships extracted from filings:
- **Entities**: Companies, People, Locations, Products, Events
- **Relationships**: subsidiary_of, officer_of, investor_in, etc.

### 4. Watchlists
User-created lists for tracking companies and receiving alerts.

---

## API Endpoints

### Base URL
```
http://localhost:8000/api/v1
```

### Authentication
Most endpoints require JWT authentication:
```http
Authorization: Bearer <your-jwt-token>
```

---

## Companies API (`/api/v1/companies`)

### List Companies
```http
GET /api/v1/companies
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `sector` | string | Filter by GICS sector (e.g., "Technology") |
| `industry` | string | Filter by industry |
| `exchange` | string | Filter by exchange (NYSE, NASDAQ) |
| `min_market_cap` | number | Minimum market cap in USD |
| `max_market_cap` | number | Maximum market cap in USD |
| `sort_by` | string | Sort field (market_cap, name, ticker) |
| `sort_order` | string | asc or desc |
| `page` | integer | Page number (default: 1) |
| `page_size` | integer | Items per page (1-100, default: 50) |

**Response:**
```json
{
  "companies": [
    {
      "company_id": "uuid",
      "cik": "0000320193",
      "ticker": "AAPL",
      "name": "Apple Inc.",
      "sector": "Technology",
      "industry": "Consumer Electronics",
      "market_cap": 3000000000000
    }
  ],
  "total": 14000,
  "page": 1,
  "page_size": 50,
  "total_pages": 280
}
```

### Search Companies
```http
GET /api/v1/companies/search?q={query}
```

Full-text search across ticker, name, and CIK.

### Get Company by ID
```http
GET /api/v1/companies/{company_id}
```

### Get Company by Ticker
```http
GET /api/v1/companies/ticker/{ticker}
```

### Get Company by CIK
```http
GET /api/v1/companies/cik/{cik}
```

### Get Company Metrics
```http
GET /api/v1/companies/{company_id}/metrics
```

Returns financial metrics including revenue, margins, ratios.

### Get Company Filings
```http
GET /api/v1/companies/{company_id}/filings
```

### Get Company Relationships
```http
GET /api/v1/companies/{company_id}/relationships
```

---

## Filings API (`/api/v1/filings`)

### List Filings
```http
GET /api/v1/filings
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `form_type` | string | Single form type (10-K, 10-Q, 8-K) |
| `form_types` | string | Comma-separated form types |
| `sector` | string | Filter by company sector |
| `ticker` | string | Filter by company ticker |
| `cik` | string | Filter by company CIK |
| `filed_after` | date | Filed on or after (YYYY-MM-DD) |
| `filed_before` | date | Filed on or before |

### Get Filing Feed (Instagram-style)
```http
GET /api/v1/filings/feed
```

Returns filings formatted for infinite-scroll feed with:
- Time ago formatting ("2h ago", "3d ago")
- Company context
- Engagement metrics (views, bookmarks)

### Get Filing Details
```http
GET /api/v1/filings/{filing_id}
```

Returns full filing with documents and parsed sections.

### Get Filing Section
```http
GET /api/v1/filings/{filing_id}/sections/{section_type}
```

Section types for 10-K:
- `item_1` - Business
- `item_1a` - Risk Factors
- `item_7` - MD&A (Management Discussion)
- `item_8` - Financial Statements

---

## Entities & Knowledge Graph API (`/api/v1/entities`)

### List Entities
```http
GET /api/v1/entities
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `entity_type` | string | company, person, location, product, event |
| `search` | string | Search by name |

### Get Entity Details
```http
GET /api/v1/entities/{entity_id}
```

### Get Entity Relationships
```http
GET /api/v1/entities/{entity_id}/relationships
```

### Explore Knowledge Graph
```http
GET /api/v1/entities/graph/explore
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `start_entity_id` | uuid | Starting entity (required) |
| `depth` | integer | Max traversal depth (1-4, default: 2) |
| `relationship_types` | string | Comma-separated types to include |
| `max_nodes` | integer | Maximum nodes (10-500, default: 100) |

**Response (for 3D visualization):**
```json
{
  "nodes": [
    {"id": "uuid", "type": "company", "name": "Apple Inc.", "depth": 0}
  ],
  "edges": [
    {"id": "uuid", "source": "uuid1", "target": "uuid2", "type": "subsidiary_of"}
  ],
  "node_count": 45,
  "edge_count": 78
}
```

### Find Path Between Entities
```http
GET /api/v1/entities/graph/path?from_entity_id={uuid}&to_entity_id={uuid}
```

---

## Search API (`/api/v1/search`)

### Universal Search
```http
GET /api/v1/search?q={query}
```

Searches across all content types (companies, filings, entities).

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `q` | string | Search query (required) |
| `types` | string | Comma-separated types to search |
| `sector` | string | Filter by sector |
| `limit` | integer | Max results (1-100, default: 20) |

### Search Suggestions
```http
GET /api/v1/search/suggestions?q={partial_query}
```

Returns typeahead suggestions as user types.

### Trending Topics
```http
GET /api/v1/search/trending?period={hour|day|week}
```

---

## Watchlists API (`/api/v1/watchlists`)

### List Watchlists
```http
GET /api/v1/watchlists
```

### Create Watchlist
```http
POST /api/v1/watchlists?name={name}
```

### Add Company to Watchlist
```http
POST /api/v1/watchlists/{watchlist_id}/companies/{company_id}
```

### Remove Company from Watchlist
```http
DELETE /api/v1/watchlists/{watchlist_id}/companies/{company_id}
```

### Get Watchlist Filings
```http
GET /api/v1/watchlists/{watchlist_id}/filings
```

---

## Error Handling

All errors follow a consistent format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

### HTTP Status Codes
| Code | Description |
|------|-------------|
| 200 | Success |
| 400 | Bad Request - Invalid parameters |
| 401 | Unauthorized - Missing/invalid token |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found - Resource doesn't exist |
| 422 | Validation Error - Invalid request body |
| 500 | Internal Server Error |

---

## Rate Limiting

API requests are rate-limited:
- **Anonymous**: 100 requests/minute
- **Authenticated**: 1000 requests/minute
- **SEC EDGAR calls**: 10 requests/second (SEC requirement)

---

## Pagination

List endpoints support cursor-based pagination:

```json
{
  "items": [...],
  "total": 14000,
  "page": 1,
  "page_size": 50,
  "total_pages": 280
}
```

For feed endpoints, use `before_id` cursor:
```http
GET /api/v1/filings/feed?before_id={last_filing_id}
```

---

## WebSocket Endpoints (Planned)

Real-time updates via WebSocket:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/filings');
ws.onmessage = (event) => {
  const filing = JSON.parse(event.data);
  console.log('New filing:', filing);
};
```

---

## SDK Examples

### Python
```python
import httpx

async with httpx.AsyncClient(base_url="http://localhost:8000/api/v1") as client:
    # Search companies
    response = await client.get("/companies/search", params={"q": "Apple"})
    companies = response.json()["results"]
    
    # Get filings feed
    response = await client.get("/filings/feed", params={"form_types": "10-K,8-K"})
    filings = response.json()
```

### TypeScript/JavaScript
```typescript
const API_BASE = 'http://localhost:8000/api/v1';

// Search companies
const response = await fetch(`${API_BASE}/companies/search?q=Apple`);
const { results } = await response.json();

// Get company profile
const company = await fetch(`${API_BASE}/companies/${companyId}`).then(r => r.json());
```

---

## OpenAPI Documentation

Interactive API documentation is available at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/api/v1/openapi.json

---

## See Also

- [FEATURE_ROADMAP.md](../../docs/FEATURE_ROADMAP.md) - Complete feature roadmap
- [IMPLEMENTATION_SUMMARY.md](../../IMPLEMENTATION_SUMMARY.md) - Implementation status
- [Database Schema](../../db/schema.sql) - PostgreSQL schema
