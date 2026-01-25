# Entity Relationships Dashboard

A comprehensive Bloomberg/FactSet-style entity profile dashboard with 3D relationship graph visualization. This standalone app showcases EntitySpine's entity relationship capabilities.

## Features

### Dashboard View
- **Company Profile**: Complete entity overview with identifiers, financials, and corporate information
- **Key Statistics**: Market cap, revenue, employees, 52-week range, institutional ownership
- **Financial Metrics**: Revenue, net income, assets, debt, and cash positions
- **Industry Classification**: Sector, industry, SIC/NAICS codes
- **Quick Stats Grid**: At-a-glance metrics in a visual grid

### 3D Entity Graph
- **Interactive Force-Directed Graph**: Full 3D visualization using react-force-graph-3d
- **Node Types**: Companies, subsidiaries, persons, funds, government entities
- **Relationship Types**: Ownership, supply chain, competition, investment, regulatory
- **Click-to-Explore**: Click any node to highlight its connections
- **Search & Filter**: Find entities by name, filter by type
- **Camera Controls**: Zoom, pan, reset view
- **Fullscreen Mode**: Expand graph to full screen

### Hierarchy View
- **Bloomberg LAW Style Tree**: Expandable corporate structure tree
- **Expand/Collapse All**: Quick navigation controls
- **Regional Statistics**: Incorporation breakdown by region
- **Industry Tags**: Visual industry classification
- **Relationship Badges**: Color-coded relationship types

## Boeing Ecosystem Example

The app includes a complete Boeing ecosystem with:

**Corporate Structure:**
- Boeing Commercial Airplanes
- Boeing Defense, Space & Security
- Boeing Global Services
- Boeing Capital Corporation
- International subsidiaries

**Supply Chain:**
- GE Aerospace (engines)
- Rolls-Royce Holdings
- Spirit AeroSystems
- Hexcel Corporation
- Honeywell Aerospace

**Customers:**
- Major Airlines (United, Delta, American, Southwest, Emirates, Ryanair)
- US Department of Defense
- NASA

**Competitors:**
- Airbus SE
- Lockheed Martin
- Raytheon (RTX)
- Northrop Grumman
- General Dynamics

**Investors:**
- Vanguard Group
- BlackRock
- State Street

## Getting Started

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build
```

## Tech Stack

- **React 19** + TypeScript
- **Vite** for fast development
- **Tailwind CSS v3** for styling
- **react-force-graph-3d** for 3D graph visualization
- **Three.js** for 3D rendering
- **Lucide React** for icons

## Data Model

The app uses EntitySpine's data model:

```typescript
interface EntityNode {
  id: string;
  name: string;
  type: 'company' | 'subsidiary' | 'person' | 'fund' | 'government';
  category?: string;
  marketCap?: number;
  revenue?: number;
  employees?: number;
  // ... additional fields
}

interface RelationshipLink {
  source: string;
  target: string;
  type: 'owns' | 'supplies' | 'competes' | 'partners' | 'invests' | 'regulates';
  strength?: number;
  ownership?: number;
  description?: string;
}
```

## Screenshots

### Dashboard View
Company profile with quick stats, financials, and mini graph preview.

### 3D Graph View
Interactive force-directed graph showing all entity relationships.

### Hierarchy View
Bloomberg LAW-style expandable corporate structure tree.

## License

MIT
