# Entity Graph App

A standalone 3D Entity Relationship Graph visualization built with React, Three.js, and react-force-graph-3d.

## Features

- **3D Force-Directed Graph**: Interactive visualization of entities and their relationships
- **Semiconductor Ecosystem Data**: 40+ entities including companies, people, funds, and government bodies
- **Dynamic Node Sizing**: Size nodes by market cap, revenue, employees, or connections
- **Search & Filter**: Find entities by name, ticker, or description; filter by type and category
- **Interactive Selection**: Click nodes to see details, relationships, and connected entities
- **Color-Coded Relationships**: Visual distinction between supplies, competes, partners, invests, etc.

## Quick Start

```bash
# Install dependencies
npm install --legacy-peer-deps

# Start development server
npm run dev
```

Open http://localhost:3005 in your browser.

## Integration

To use the EntityGraph component in another React app:

```tsx
import EntityGraph from './EntityGraph';

function App() {
  return (
    <div style={{ width: '100vw', height: '100vh' }}>
      <EntityGraph />
    </div>
  );
}
```

## Dependencies

- React 19
- react-force-graph-3d
- Three.js
- Tailwind CSS
- Lucide React (icons)

## Project Structure

```
entity-graph-app/
├── src/
│   ├── main.tsx        # Entry point
│   ├── App.tsx         # Root component
│   ├── EntityGraph.tsx # Main graph component
│   └── index.css       # Tailwind styles
├── index.html
├── package.json
├── vite.config.ts
├── tailwind.config.js
├── postcss.config.js
└── tsconfig.json
```

## Controls

- **Left-click + drag**: Rotate view
- **Right-click + drag**: Pan
- **Scroll**: Zoom in/out
- **Click node**: Select and view details
- **Click background**: Deselect
