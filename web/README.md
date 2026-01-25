# EntitySpine Web - Interactive Knowledge Graph Explorer

A modern React web application for exploring, searching, and visualizing entity relationships in EntitySpine.

## Features

- 🔍 **Entity Search** - Search by name, CIK, ticker, or any identifier
- 🕸️ **Knowledge Graph** - Interactive 2D/3D visualization of entity networks
- 📊 **Dashboard** - Real-time statistics and database metrics
- 💾 **Database Manager** - Load SEC data and manage your database
- 📚 **Integrated Docs** - Direct links to EntitySpine documentation
- 🎨 **Modern UI** - Clean, responsive interface with dark theme

## Quick Start

### Docker (Recommended)

The easiest way to run EntitySpine Web with all services:

```bash
# From the monitoring directory
cd monitoring
docker compose -f docker-compose.monitoring.yml up -d entityspine-api entityspine-docs entityspine-frontend

# Access the services:
# - Frontend: http://localhost:3002
# - API: http://localhost:8000
# - Docs: http://localhost:8001
```

### Local Development

```bash
# Install dependencies
npm install

# Start development server
npm start

# Build for production
npm run build
```

### Environment Variables

Create a `.env` file:

```bash
REACT_APP_API_URL=http://localhost:8000
REACT_APP_DOCS_URL=http://localhost:8001
```

## Architecture

```
entityspine-web/
├── public/              # Static assets
├── src/
│   ├── components/      # Reusable UI components
│   │   └── Layout.tsx   # Main layout with sidebar
│   ├── pages/           # Page components
│   │   ├── Dashboard.tsx         # Dashboard with stats
│   │   ├── Search.tsx            # Entity search
│   │   ├── KnowledgeGraph.tsx    # Graph visualization
│   │   ├── EntityDetails.tsx     # Entity detail view
│   │   ├── DatabaseManager.tsx   # Database management
│   │   └── Documentation.tsx     # Docs integration
│   ├── services/        # API client
│   │   └── api.ts       # EntitySpine API wrapper
│   ├── App.tsx          # Main app component
│   └── index.tsx        # Entry point
├── Dockerfile           # Multi-stage production build
├── nginx.conf           # Nginx configuration
└── package.json         # Dependencies
```

## Pages

### Dashboard (`/`)
- Entity count, identifier count, relationship count
- Identifier schemes breakdown
- Quick action cards

### Search (`/search`)
- Full-text entity search
- Filter by type, jurisdiction
- Confidence score indicators
- Click to view entity details

### Knowledge Graph (`/graph`)
- Interactive 2D force-directed graph
- Node coloring by entity type
- Relationship visualization
- Zoom and pan controls

### Entity Details (`/entity/:id`)
- Entity information
- All identifiers with confidence scores
- Link to knowledge graph view

### Database Manager (`/database`)
- Load SEC data (14K+ companies)
- Database statistics
- Import/export options

### Documentation (`/docs`)
- Quick links to guides
- Embedded documentation
- API reference access

## API Integration

The app integrates with EntitySpine FastAPI backend:

**Endpoints Used:**
- `GET /` - Service info
- `GET /health` - Health check
- `GET /search` - Search entities
- `GET /entities/{id}` - Get entity details
- `GET /entities/{id}/identifiers` - Get identifiers
- `GET /entities/{id}/network` - Get knowledge graph
- `GET /stats` - Database statistics
- `POST /admin/load-sec-data` - Load SEC data

## Development

### Running with Hot Reload

```bash
npm start
```

Runs on `http://localhost:3000` with hot reload enabled.

### Building for Production

```bash
npm run build
```

Creates optimized production build in `build/`.

### Docker Build

```bash
docker build -t entityspine-web .
docker run -p 3002:3000 entityspine-web
```

## Styling

- CSS Variables for theming
- Dark mode by default
- Responsive design (mobile-first)
- Purple gradient accent colors

## Dependencies

**Core:**
- React 18
- TypeScript
- React Router v6

**Visualization:**
- react-force-graph-2d/3d - Graph visualization
- three.js - 3D rendering
- recharts - Charts and metrics

**API:**
- axios - HTTP client

## Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

## License

MIT - See LICENSE file

## Related Projects

- **EntitySpine** - Python entity resolution library
- **EntitySpine API** - FastAPI service
- **EntitySpine Docs** - MkDocs documentation
