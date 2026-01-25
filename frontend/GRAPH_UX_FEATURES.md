# 3D Entity Graph UX Feature Roadmap

Interactive visualization features for exploring financial, supply chain, and industry data across 5 complexity levels.

---

## 🟢 Level 1: Basic (Foundation)

### 1.1 Node Labels & Tooltips
- **Company name** displayed on/near node
- **Hover tooltip** showing: ticker, industry, jurisdiction
- **Relationship type labels** on edges (supplier, customer, competitor)

### 1.2 Color Coding
- Nodes colored by **entity type** (public, private, startup, investor)
- Nodes colored by **industry segment** (foundry, fabless, equipment, memory)
- Edges colored by **relationship type** (red=competitor, green=supplier, blue=customer)

### 1.3 Basic Filtering
- Filter by entity type (show only public companies)
- Filter by relationship type (show only supply chain)
- Search by company name or ticker

### 1.4 Selection & Details Panel
- Click node to select and highlight connections
- Side panel showing entity details (identifiers, metadata)
- List of all relationships for selected entity

### 1.5 Navigation Controls
- Zoom in/out with scroll wheel
- Pan by dragging background
- Rotate by dragging (3D)
- Reset view button

---

## 🟡 Level 2: Intermediate (Data-Driven Visualization)

### 2.1 Dynamic Node Sizing
- **Size by market cap** - larger companies = bigger nodes
- **Size by revenue** - scale by annual revenue
- **Size by employee count** - headcount visualization
- **Size by connection count** - more connected = larger (network centrality)
- Toggle between sizing modes with dropdown

### 2.2 Edge Styling by Metadata
- **Line thickness** = relationship strength/value
- **Line style**: solid (active), dashed (former), dotted (pending)
- **Animated particles** flowing along supply chain direction
- **Arrow direction** showing flow (supplier → customer)

### 2.3 Time-Based Filtering
- Slider to filter relationships by date (show 2020-2024 only)
- Animate graph evolution over time
- Show/hide historical vs current relationships

### 2.4 Grouping & Clustering
- **Group by industry** - cluster semiconductor, software, services
- **Group by geography** - US companies together, Taiwan together
- **Group by corporate family** - subsidiaries near parents
- Expand/collapse groups

### 2.5 Multi-Select & Compare
- Shift+click to select multiple entities
- Compare panel showing side-by-side metrics
- Highlight shared connections between selected entities

---

## 🟠 Level 3: Advanced (Analytics & Intelligence)

### 3.1 Path Finding
- **Find shortest path** between two companies
- **Find all paths** within N hops
- Highlight critical intermediaries (bottleneck analysis)
- "How is Apple connected to ASML?" → shows: Apple → TSMC → ASML

### 3.2 Network Analytics Overlay
- **Centrality scores** - who's most connected/influential?
- **Clustering coefficient** - how tightly knit are subgroups?
- **Betweenness centrality** - who bridges different clusters?
- Color/size nodes by any metric

### 3.3 Risk Propagation Visualization
- Select a node, simulate "what if this company fails?"
- Show cascade effect through supply chain
- Heat map of exposure levels (red = high risk)
- Concentration risk highlighting

### 3.4 Financial Metrics Overlay
- **Revenue heat map** - color by revenue
- **Growth rate** - green (growing) to red (shrinking)
- **P/E ratio** visualization
- **Stock performance** - YTD change as node color intensity

### 3.5 Comparison Mode
- Split screen: compare two time periods
- Diff view: what relationships changed?
- Before/after M&A visualization
- Industry structure evolution

---

## 🔴 Level 4: Expert (Real-Time & Predictive)

### 4.1 Live Data Integration
- **Real-time stock prices** updating node colors
- **Live news feed** - pulse animation when news hits a company
- **SEC filing alerts** - glow effect on new 8-K/10-K
- **Earnings calendar** - countdown badges

### 4.2 Sentiment & NLP Overlay
- **News sentiment** - green aura (positive), red aura (negative)
- **Social media buzz** - particle density around node
- **Analyst rating changes** - arrows up/down
- **Keyword cloud** on hover from recent filings

### 4.3 Scenario Modeling
- "What if TSMC loses 30% capacity?" - model downstream impact
- "What if ARM license cost doubles?" - show affected companies
- Drag sliders to adjust assumptions, see graph react
- Monte Carlo simulation visualization

### 4.4 Custom Metrics & Formulas
- Create calculated fields (Revenue/Employee)
- Custom scoring formulas (weighted risk score)
- User-defined node sizing/coloring rules
- Save and share custom views

### 4.5 Collaborative Features
- **Annotations** - add notes to nodes/edges
- **Shared views** - URL sharing with exact state
- **Team workspaces** - multiple users same graph
- **Version history** - track changes to analysis

---

## 🟣 Level 5: Mindblowing (AI-Powered & Immersive)

### 5.1 Natural Language Queries
- "Show me NVIDIA's top 5 suppliers by revenue"
- "Which companies have the most customer concentration risk?"
- "Find all paths from raw materials to Apple products"
- "Who competes with AMD in data center GPUs?"
- AI generates and executes graph queries

### 5.2 Predictive Relationship Discovery
- ML suggests **likely undisclosed relationships**
- "Companies with similar supply chains to X"
- "Predicted M&A targets based on graph structure"
- Anomaly detection: "This company has unusual supplier concentration"

### 5.3 VR/AR Immersive Mode
- **VR headset support** - walk through your supply chain
- **AR overlay** - point phone at product, see supply chain
- **Gesture controls** - pinch to zoom, swipe to filter
- **Voice commands** - "Zoom to semiconductor cluster"

### 5.4 Generative Insights
- AI-generated **executive summaries** of graph state
- Automatic **risk reports** from graph analysis
- **Narrative generation**: "The chip shortage impact story"
- **Chart generation** from graph data (auto Sankey diagrams)

### 5.5 Digital Twin & Simulation
- Full **supply chain digital twin** with inventory levels
- **Discrete event simulation** - model disruptions
- **Optimization mode** - suggest better supplier diversification
- **What-if time travel** - "Show graph if Intel hadn't sold NAND business"

---

## Implementation Priority Matrix

| Feature | Impact | Effort | Priority |
|---------|--------|--------|----------|
| Dynamic node sizing | High | Low | P0 |
| Metric toggle (revenue/market cap) | High | Low | P0 |
| Edge labels | Medium | Low | P0 |
| Path finding | High | Medium | P1 |
| Time slider | Medium | Medium | P1 |
| Network analytics | High | Medium | P1 |
| Risk propagation | High | High | P2 |
| Live data | Medium | High | P2 |
| NL queries | Very High | Very High | P3 |
| VR mode | Medium | Very High | P4 |

---

## Data Requirements

### For Basic Features
- Entity identifiers (CIK, ticker, LEI)
- Entity metadata (name, type, industry, jurisdiction)
- Relationship type and direction

### For Intermediate Features
- Market cap, revenue, employee count
- Relationship dates (start, end)
- Relationship value/strength metrics

### For Advanced Features
- Historical time series data
- Financial statement data
- News/sentiment feeds

### For Expert/Mindblowing
- Real-time market data feeds
- NLP-processed SEC filings
- ML model endpoints
- WebXR/Three.js VR support

---

## Tech Stack Recommendations

| Feature Level | Frontend | Backend | Data |
|---------------|----------|---------|------|
| Basic | React + Three.js | REST API | PostgreSQL |
| Intermediate | + D3.js | + WebSocket | + TimescaleDB |
| Advanced | + WebGL shaders | + Redis | + Neo4j |
| Expert | + WebRTC | + Kafka | + ClickHouse |
| Mindblowing | + WebXR | + ML endpoints | + Vector DB |
