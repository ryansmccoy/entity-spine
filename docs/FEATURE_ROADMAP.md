# Entity Spine Feature Roadmap

> A comprehensive guide to building a Bloomberg/FactSet-quality financial data platform

**Version:** 1.0  
**Last Updated:** January 27, 2026  
**Status:** Implementation Guide

---

## Table of Contents

1. [Vision Overview](#1-vision-overview)
2. [Feature Tiers](#2-feature-tiers)
3. [Basic Features](#3-basic-features)
4. [Intermediate Features](#4-intermediate-features)
5. [Advanced Features](#5-advanced-features)
6. [Mind-Blowing Features](#6-mind-blowing-features)
7. [Architecture](#7-architecture)
8. [Implementation Phases](#8-implementation-phases)
9. [Testing Strategy](#9-testing-strategy)
10. [File Structure](#10-file-structure)

---

## 1. Vision Overview

### The Goal
Build a **financial intelligence platform** that combines:
- **Instagram-style feeds** for financial news and SEC filings
- **Bloomberg-quality company profiles** with full financial data
- **Knowledge graph exploration** for discovering relationships
- **Universal search** across companies, filings, metrics, and relationships

### Core User Journeys

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         USER JOURNEY MAP                                    │
└─────────────────────────────────────────────────────────────────────────────┘

Discovery Mode:
  Feed → See interesting filing → Click $TSLA → Company Profile → 
  → See competitors → Click relationship → Knowledge Graph → 
  → Discover new company → Add to watchlist

Research Mode:
  Search "EV companies revenue > $1B" → Results table → 
  → Compare financials → Export to Excel → Create alert

Monitoring Mode:
  Dashboard → Watchlist updates → New filing alert → 
  → AI Summary → Quick action → Back to dashboard
```

---

## 2. Feature Tiers

| Tier | Description | Effort | Value |
|------|-------------|--------|-------|
| **Basic** | Core functionality, MVP features | 1-2 weeks each | High |
| **Intermediate** | Enhanced UX, deeper data | 2-4 weeks each | High |
| **Advanced** | Professional-grade tools | 1-2 months each | Medium |
| **Mind-Blowing** | Industry-leading innovation | 2-6 months each | Differentiation |

---

## 3. Basic Features

### 3.1 Company Profile Page

**What:** A dedicated page for each company showing key information.

**User Flow:**
```
Click $TSLA anywhere → /company/tsla → Full company profile
```

**Components:**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│ TESLA, INC.                                           $TSLA │ NASDAQ       │
│ Electric Vehicles & Energy Storage                    ★ Add to Watchlist   │
├─────────────────────────────────────────────────────────────────────────────┤
│ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐       │
│ │ Market Cap   │ │ Revenue      │ │ Employees    │ │ Founded      │       │
│ │ $892.4B      │ │ $96.8B       │ │ 127,855      │ │ 2003         │       │
│ └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘       │
├─────────────────────────────────────────────────────────────────────────────┤
│ [Overview] [Financials] [Filings] [Relationships] [News] [Alerts]          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Company Description                          Quick Facts                   │
│  ─────────────────────                        ───────────                   │
│  Tesla designs, manufactures, and sells       CIK: 0001318605              │
│  electric vehicles, energy storage systems,   SIC: 3711 - Motor Vehicles   │
│  and solar energy generation systems...       Fiscal Year End: December    │
│                                               SEC Filer Status: Large      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Data Sources:**
- SEC EDGAR (CIK, filings, SIC code)
- Entity extraction from filings
- External APIs (optional: Yahoo Finance, Alpha Vantage)

**Implementation:**

```typescript
// Frontend: src/pages/CompanyProfilePage.tsx
interface CompanyProfileProps {
  ticker: string;
}

// API: GET /api/companies/:ticker
interface CompanyProfile {
  cik: string;
  ticker: string;
  name: string;
  description: string;
  sector: string;
  industry: string;
  sicCode: string;
  sicDescription: string;
  marketCap?: number;
  revenue?: number;
  employees?: number;
  founded?: string;
  headquarters?: string;
  website?: string;
  fiscalYearEnd: string;
  filerStatus: string;
}
```

**Database:**
```sql
CREATE TABLE companies (
    company_id UUID PRIMARY KEY,
    cik TEXT UNIQUE NOT NULL,
    ticker TEXT,
    name TEXT NOT NULL,
    description TEXT,
    sector TEXT,
    industry TEXT,
    sic_code TEXT,
    market_cap DECIMAL,
    employees INTEGER,
    founded_year INTEGER,
    headquarters TEXT,
    website TEXT,
    fiscal_year_end TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_companies_ticker ON companies(ticker);
CREATE INDEX idx_companies_sector ON companies(sector);
CREATE INDEX idx_companies_industry ON companies(industry);
```

---

### 3.2 Filing Feed (Instagram-style)

**What:** A scrollable, card-based feed of recent SEC filings with visual previews.

**User Flow:**
```
Open app → See latest filings as cards → Scroll infinitely → 
→ Tap card to expand → See summary → Click to view full filing
```

**Components:**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 📰 Filing Feed                                    [All] [10-K] [8-K] [4]   │
├─────────────────────────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────┐                            │
│ │ 🏢 APPLE INC.                    $AAPL      │  ← Card with company logo  │
│ │ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │                            │
│ │ 10-K Annual Report                          │                            │
│ │ Filed: Jan 27, 2026 • FY 2025               │                            │
│ │                                             │                            │
│ │ 📊 Revenue: $450.2B (+8.3% YoY)             │  ← AI-extracted highlights │
│ │ 💰 Net Income: $98.4B (+12.1% YoY)          │                            │
│ │ 🔮 Guidance: "Expects continued growth..."   │                            │
│ │                                             │                            │
│ │ [View Filing] [💾 Save] [🔔 Alert] [Share]   │                            │
│ └─────────────────────────────────────────────┘                            │
│                                                                             │
│ ┌─────────────────────────────────────────────┐                            │
│ │ 🏢 MICROSOFT CORP               $MSFT       │                            │
│ │ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │                            │
│ │ 8-K Current Report                          │                            │
│ │ Filed: Jan 27, 2026                         │                            │
│ │                                             │                            │
│ │ 📢 "Announces acquisition of..."            │                            │
│ │                                             │                            │
│ └─────────────────────────────────────────────┘                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Implementation:**

```typescript
// Frontend: src/components/FilingFeed.tsx
interface FilingCard {
  filingId: string;
  company: {
    cik: string;
    ticker: string;
    name: string;
    logoUrl?: string;
  };
  formType: string;
  filedAt: string;
  period?: string;
  highlights: string[];
  aiSummary?: string;
  documentUrls: {
    html: string;
    pdf?: string;
  };
}

// Infinite scroll hook
const useFilingFeed = (filters: FilingFilters) => {
  return useInfiniteQuery({
    queryKey: ['filings', filters],
    queryFn: ({ pageParam }) => fetchFilings({ ...filters, cursor: pageParam }),
    getNextPageParam: (lastPage) => lastPage.nextCursor,
  });
};
```

---

### 3.3 Watchlist

**What:** Personal list of companies to monitor.

**User Flow:**
```
Star company → Added to watchlist → See updates on dashboard → 
→ Get alerts for new filings
```

**Components:**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│ ⭐ My Watchlist                              [+ Add Company] [Manage]       │
├─────────────────────────────────────────────────────────────────────────────┤
│ Company          Ticker    Last Filing    Price     Change    Alert        │
│ ─────────────────────────────────────────────────────────────────────────  │
│ Apple Inc.       AAPL      10-K (1d ago)  $198.23   +2.3%    🔔 On        │
│ Tesla Inc.       TSLA      8-K (3d ago)   $245.67   -1.2%    🔔 On        │
│ Microsoft        MSFT      10-Q (5d ago)  $412.89   +0.8%    🔕 Off       │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Database:**
```sql
CREATE TABLE watchlists (
    watchlist_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id),
    name TEXT DEFAULT 'Default',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE watchlist_items (
    watchlist_id UUID REFERENCES watchlists(watchlist_id),
    company_id UUID REFERENCES companies(company_id),
    added_at TIMESTAMPTZ DEFAULT NOW(),
    alert_enabled BOOLEAN DEFAULT true,
    notes TEXT,
    PRIMARY KEY (watchlist_id, company_id)
);
```

---

### 3.4 Simple Search

**What:** Search for companies by name, ticker, or CIK.

**User Flow:**
```
Press / or click search → Type "Tesla" → See results → Click to go to profile
```

**Components:**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 🔍 tesla                                                              ⌘K   │
├─────────────────────────────────────────────────────────────────────────────┤
│ Companies                                                                   │
│ ┌─────────────────────────────────────────────────────────────────────────┐│
│ │ 🏢 TESLA, INC.                                              $TSLA      ││
│ │    Electric Vehicles • CIK: 0001318605                                 ││
│ └─────────────────────────────────────────────────────────────────────────┘│
│ ┌─────────────────────────────────────────────────────────────────────────┐│
│ │ 🏢 TESLA EXPLORATION LTD                                    TSL.V      ││
│ │    Mining • CIK: 0001234567                                            ││
│ └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
│ Filings matching "tesla"                                              [→]  │
│ • Tesla 10-K (Jan 2026)                                                    │
│ • Tesla 8-K Earnings (Oct 2025)                                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### 3.5 Recent Filings Table

**What:** A sortable, filterable table of recent SEC filings.

**Components:**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 📋 Recent Filings                                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│ [Form Type ▼] [Date Range ▼] [Sector ▼] [Size ▼]          🔍 Filter        │
├─────────────────────────────────────────────────────────────────────────────┤
│ Date       │ Company        │ Ticker │ Form  │ Size   │ Links              │
│ ───────────┼────────────────┼────────┼───────┼────────┼─────────────────── │
│ 2026-01-27 │ Apple Inc.     │ AAPL   │ 10-K  │ 12.4MB │ [HTML] [PDF] [XML] │
│ 2026-01-27 │ Microsoft      │ MSFT   │ 8-K   │ 245KB  │ [HTML] [PDF]       │
│ 2026-01-26 │ Nvidia Corp    │ NVDA   │ 10-Q  │ 8.2MB  │ [HTML] [PDF] [XML] │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Intermediate Features

### 4.1 Financial Statements View

**What:** Structured view of income statement, balance sheet, cash flow.

**User Flow:**
```
Company Profile → Financials Tab → Select Statement → View quarterly/annual → Compare periods
```

**Components:**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 📊 TESLA Financial Statements                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│ [Income Statement] [Balance Sheet] [Cash Flow]     [Annual ▼] [Compare]    │
├─────────────────────────────────────────────────────────────────────────────┤
│                              │ FY 2025    │ FY 2024    │ FY 2023    │ YoY % │
│ ─────────────────────────────┼────────────┼────────────┼────────────┼────── │
│ Revenue                      │                                              │
│   Automotive Sales           │ $78,234M   │ $71,462M   │ $65,123M   │ +9.5% │
│   Energy & Storage           │ $12,456M   │ $9,234M    │ $6,789M    │+34.9% │
│   Services & Other           │ $6,123M    │ $5,456M    │ $4,234M    │+12.2% │
│ ─────────────────────────────┼────────────┼────────────┼────────────┼────── │
│ Total Revenue                │ $96,813M   │ $86,152M   │ $76,146M   │+12.4% │
│                              │                                              │
│ Cost of Revenue              │ $72,456M   │ $65,234M   │ $58,123M   │+11.1% │
│ ─────────────────────────────┼────────────┼────────────┼────────────┼────── │
│ Gross Profit                 │ $24,357M   │ $20,918M   │ $18,023M   │+16.4% │
│ Gross Margin                 │ 25.2%      │ 24.3%      │ 23.7%      │       │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Data Source:**
- XBRL parsing from 10-K/10-Q filings
- Standardized GAAP taxonomy mapping

**Database:**
```sql
CREATE TABLE financial_statements (
    statement_id UUID PRIMARY KEY,
    company_id UUID REFERENCES companies(company_id),
    filing_id UUID REFERENCES filings(filing_id),
    statement_type TEXT NOT NULL,  -- 'income', 'balance', 'cashflow'
    period_type TEXT NOT NULL,     -- 'annual', 'quarterly'
    period_end DATE NOT NULL,
    currency TEXT DEFAULT 'USD',
    data JSONB NOT NULL,           -- Structured financial data
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(company_id, statement_type, period_type, period_end)
);

-- Example data structure in JSONB:
-- {
--   "revenue": {"value": 96813000000, "label": "Total Revenue"},
--   "costOfRevenue": {"value": 72456000000, "label": "Cost of Revenue"},
--   "grossProfit": {"value": 24357000000, "label": "Gross Profit"},
--   ...
-- }
```

---

### 4.2 Sector/Industry Explorer

**What:** Browse companies by sector and industry with aggregated metrics.

**User Flow:**
```
Dashboard → Sectors → Technology → Software → See all companies → Sort by metric
```

**Components:**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 🏭 Sector Explorer                                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│ Technology > Software > Application Software                               │
├─────────────────────────────────────────────────────────────────────────────┤
│ Sector Overview                                                            │
│ ┌────────────────┐ ┌────────────────┐ ┌────────────────┐ ┌────────────────┐│
│ │ Companies      │ │ Total Mkt Cap  │ │ Avg P/E        │ │ YTD Return     ││
│ │ 847            │ │ $12.4T         │ │ 28.5x          │ │ +18.7%         ││
│ └────────────────┘ └────────────────┘ └────────────────┘ └────────────────┘│
├─────────────────────────────────────────────────────────────────────────────┤
│ Top Companies by Market Cap                                    [View All →]│
│ ─────────────────────────────────────────────────────────────────────────  │
│ 1. Microsoft     $3.2T    +24.5%     [Profile]                             │
│ 2. Apple         $2.8T    +18.2%     [Profile]                             │
│ 3. Nvidia        $1.8T    +89.3%     [Profile]                             │
│ 4. Alphabet      $1.6T    +12.4%     [Profile]                             │
│ 5. Amazon        $1.5T    +22.1%     [Profile]                             │
├─────────────────────────────────────────────────────────────────────────────┤
│ 📰 Recent Sector News                                                      │
│ • "AI Spending Drives Enterprise Software Growth" - 2h ago                 │
│ • "Cloud Computing Market Reaches $600B" - 5h ago                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Database:**
```sql
CREATE TABLE sectors (
    sector_id UUID PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    parent_sector_id UUID REFERENCES sectors(sector_id)
);

CREATE TABLE industries (
    industry_id UUID PRIMARY KEY,
    sector_id UUID REFERENCES sectors(sector_id),
    name TEXT NOT NULL,
    sic_codes TEXT[],
    description TEXT,
    UNIQUE(sector_id, name)
);

-- Materialized view for sector stats
CREATE MATERIALIZED VIEW sector_stats AS
SELECT 
    s.sector_id,
    s.name as sector_name,
    COUNT(c.company_id) as company_count,
    SUM(c.market_cap) as total_market_cap,
    AVG(c.pe_ratio) as avg_pe_ratio
FROM sectors s
LEFT JOIN companies c ON c.sector = s.name
GROUP BY s.sector_id, s.name;
```

---

### 4.3 Relationship Viewer

**What:** Visual display of company relationships (subsidiaries, officers, investors).

**Components:**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 🔗 TESLA Relationships                                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│ [Subsidiaries] [Officers] [Investors] [Suppliers] [Customers]              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Subsidiaries (12)                                                         │
│  ├── Tesla Motors, Inc. (Delaware)                   100% owned            │
│  ├── Tesla Energy Operations, Inc.                   100% owned            │
│  ├── Tesla Insurance Services, Inc.                  100% owned            │
│  ├── Tesla Shanghai Co., Ltd                         100% owned            │
│  │   └── Gigafactory Shanghai                                              │
│  ├── Tesla Germany GmbH                              100% owned            │
│  │   └── Gigafactory Berlin                                                │
│  └── [Show 6 more...]                                                      │
│                                                                             │
│  Key Officers (8)                                                          │
│  ├── Elon Musk - CEO, Product Architect                                    │
│  ├── Zachary Kirkhorn - CFO                                                │
│  ├── Drew Baglino - SVP, Powertrain and Energy                             │
│  └── [Show 5 more...]                                                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### 4.4 Competitor Analysis

**What:** Side-by-side comparison of company metrics with competitors.

**Components:**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 📊 Competitor Analysis: TESLA vs Peers                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                    │ TSLA      │ F         │ GM        │ RIVN      │ NIO   │
│ ───────────────────┼───────────┼───────────┼───────────┼───────────┼────── │
│ Market Cap         │ $892B     │ $48B      │ $52B      │ $18B      │ $12B  │
│ Revenue (TTM)      │ $96.8B    │ $176.2B   │ $171.8B   │ $4.2B     │ $7.8B │
│ Revenue Growth     │ +12.4%    │ +5.2%     │ +3.8%     │ +167%     │ +34%  │
│ Gross Margin       │ 25.2%     │ 8.4%      │ 9.1%      │ -12.3%    │ 5.4%  │
│ Net Margin         │ 15.4%     │ 3.2%      │ 4.1%      │ -89%      │ -22%  │
│ EV Deliveries (Q)  │ 485K      │ 22K       │ 35K       │ 16K       │ 55K   │
│ P/E Ratio          │ 68x       │ 7x        │ 6x        │ N/A       │ N/A   │
│ ───────────────────┼───────────┼───────────┼───────────┼───────────┼────── │
│                    │ [Profile] │ [Profile] │ [Profile] │ [Profile] │[Prof] │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### 4.5 Filing Diff/Change Detection

**What:** Show what changed between consecutive filings.

**Components:**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 📝 Filing Changes: TESLA 10-K 2025 vs 2024                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│ Summary of Changes                                                         │
│ • 47 sections modified                                                     │
│ • 12 new risk factors added                                                │
│ • 3 risk factors removed                                                   │
│ • Revenue increased 12.4%                                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│ Risk Factors (Item 1A)                                          [Expand]   │
│ ─────────────────────────────────────────────────────────────────────────  │
│ + NEW: "Risks related to artificial intelligence development"              │
│ + NEW: "Cybersecurity threats to vehicle software systems"                 │
│ ~ MODIFIED: "Competition in the electric vehicle market" (see diff)        │
│ - REMOVED: "COVID-19 related supply chain disruptions"                     │
├─────────────────────────────────────────────────────────────────────────────┤
│ [View Full Diff] [Download Comparison Report]                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Advanced Features

### 5.1 Knowledge Graph Explorer

**What:** Interactive 3D visualization of entity relationships across the market.

**User Flow:**
```
Search "Tesla" → See node → Expand relationships → 
→ Discover connected entities → Filter by type → Export subgraph
```

**Components:**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 🕸️ Knowledge Graph                                   [2D] [3D] [VR]        │
├─────────────────────────────────────────────────────────────────────────────┤
│ Filters: [Companies ✓] [People ✓] [Filings] [Relationships ▼]              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│                          ┌─────────┐                                        │
│                    ┌─────┤  TSLA   ├─────┐                                  │
│                    │     └────┬────┘     │                                  │
│              subsidiaryOf    │    competitorOf                              │
│                    │         │         │                                    │
│              ┌─────┴───┐   owns    ┌───┴─────┐                              │
│              │Shanghai │     │     │  RIVN   │                              │
│              │  GF     │     │     └────┬────┘                              │
│              └─────────┘   ┌─┴─┐        │                                   │
│                            │Elon│  investedIn                               │
│                            │Musk│        │                                  │
│                            └─┬─┘   ┌────┴────┐                              │
│                              │     │ Twitter │                              │
│                           ceoOf    └─────────┘                              │
│                              │                                              │
│                        ┌─────┴─────┐                                        │
│                        │  SpaceX   │                                        │
│                        └───────────┘                                        │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│ Selected: TESLA, INC.                                                      │
│ Type: Company │ CIK: 0001318605 │ 156 connections                          │
│ [View Profile] [Expand All] [Focus] [Export]                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Implementation:**

```typescript
// Frontend: src/components/KnowledgeGraph/KnowledgeGraph3D.tsx
import ForceGraph3D from 'react-force-graph-3d';

interface GraphNode {
  id: string;
  label: string;
  type: 'company' | 'person' | 'filing' | 'entity';
  properties: Record<string, any>;
}

interface GraphEdge {
  source: string;
  target: string;
  type: string;
  properties: Record<string, any>;
}

// API: GET /api/graph/neighbors/:entityId
interface GraphNeighborsResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
  totalConnections: number;
}
```

**Database (Graph Structure):**
```sql
CREATE TABLE entities (
    entity_id UUID PRIMARY KEY,
    entity_type TEXT NOT NULL,  -- 'company', 'person', 'location', 'product'
    name TEXT NOT NULL,
    properties JSONB DEFAULT '{}',
    source_filing_id UUID,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE relationships (
    relationship_id UUID PRIMARY KEY,
    source_entity_id UUID REFERENCES entities(entity_id),
    target_entity_id UUID REFERENCES entities(entity_id),
    relationship_type TEXT NOT NULL,  -- 'subsidiary_of', 'officer_of', 'owns', 'competitor'
    properties JSONB DEFAULT '{}',
    confidence DECIMAL(3,2),
    source_filing_id UUID,
    valid_from DATE,
    valid_to DATE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_relationships_source ON relationships(source_entity_id);
CREATE INDEX idx_relationships_target ON relationships(target_entity_id);
CREATE INDEX idx_relationships_type ON relationships(relationship_type);
```

---

### 5.2 Universal Query Platform

**What:** Natural language and structured query interface for finding companies.

**User Flow:**
```
"Show me tech companies with revenue > $10B and P/E < 30" →
→ See results in table → Sort/filter → Export → Create alert
```

**Components:**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 🔍 Universal Query                                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────────────────────────────────┐│
│ │ "tech companies revenue > 10B gross margin > 20% employees > 1000"     ││
│ └─────────────────────────────────────────────────────────────────────────┘│
│ [Natural Language] [Query Builder] [SQL Mode]                   [Search]   │
├─────────────────────────────────────────────────────────────────────────────┤
│ Interpreted Query:                                                         │
│ sector = 'Technology' AND revenue > 10,000,000,000 AND                     │
│ gross_margin > 0.20 AND employees > 1000                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│ Results: 147 companies                         [Export CSV] [Create Alert] │
│ ─────────────────────────────────────────────────────────────────────────  │
│ Company        │ Revenue   │ Gross Margin │ Employees │ P/E   │ Actions   │
│ Apple Inc.     │ $450.2B   │ 43.2%        │ 164,000   │ 28.5x │ [Profile] │
│ Microsoft      │ $245.1B   │ 69.1%        │ 221,000   │ 35.2x │ [Profile] │
│ Alphabet       │ $307.4B   │ 55.4%        │ 186,000   │ 24.8x │ [Profile] │
│ ...                                                                        │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Query Builder UI:**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Query Builder                                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│ ┌───────────────┐ ┌───────────────┐ ┌───────────────┐ ┌───────────────────┐│
│ │ Field         │ │ Operator      │ │ Value         │ │ [AND ▼] [+ Add]  ││
│ │ [Sector    ▼] │ │ [equals    ▼] │ │ [Technology]  │ │                   ││
│ └───────────────┘ └───────────────┘ └───────────────┘ └───────────────────┘│
│ ┌───────────────┐ ┌───────────────┐ ┌───────────────┐ ┌───────────────────┐│
│ │ [Revenue   ▼] │ │ [>        ▼] │ │ [10000000000] │ │ [AND ▼] [+ Add]  ││
│ └───────────────┘ └───────────────┘ └───────────────┘ └───────────────────┘│
│ ┌───────────────┐ ┌───────────────┐ ┌───────────────┐ ┌───────────────────┐│
│ │ [Gross Mrg ▼] │ │ [>         ▼] │ │ [0.20]        │ │ [AND ▼] [× Del]  ││
│ └───────────────┘ └───────────────┘ └───────────────┘ └───────────────────┘│
│                                                                             │
│ [Save Query] [Load Query ▼]                                      [Search]  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### 5.3 Automated Insights Feed

**What:** AI-generated posts about market events, new relationships, anomalies.

**Components:**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 🤖 AI Insights                                              [Customize]    │
├─────────────────────────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────────────────────────────────┐│
│ │ 🔔 NEW RELATIONSHIP DETECTED                           2 hours ago     ││
│ │ ─────────────────────────────────────────────────────────────────────  ││
│ │ Apple Inc. ($AAPL) disclosed a new subsidiary:                         ││
│ │ "Apple Vision Products LLC" incorporated in Delaware                   ││
│ │                                                                         ││
│ │ This is Apple's 3rd new entity in 2026, compared to 1 in same period  ││
│ │ last year. May indicate expansion in AR/VR product development.       ││
│ │                                                                         ││
│ │ Source: 10-K Filing (Jan 27, 2026)                                     ││
│ │ [View Filing] [View Graph] [Dismiss]                                   ││
│ └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐│
│ │ 📊 UNUSUAL METRIC CHANGE                               5 hours ago     ││
│ │ ─────────────────────────────────────────────────────────────────────  ││
│ │ Tesla ($TSLA) R&D spending increased 45% YoY                           ││
│ │                                                                         ││
│ │ This is significantly higher than the industry average of 12%.         ││
│ │ Historical Tesla R&D growth: 2023: +18%, 2024: +22%, 2025: +45%        ││
│ │                                                                         ││
│ │ [View Financials] [Compare Peers] [Set Alert]                          ││
│ └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐│
│ │ 👥 EXECUTIVE MOVEMENT                                  1 day ago       ││
│ │ ─────────────────────────────────────────────────────────────────────  ││
│ │ Sarah Chen joined NVIDIA ($NVDA) as Chief AI Officer                   ││
│ │ Previously: VP of AI Research at Google (2019-2025)                    ││
│ │                                                                         ││
│ │ [View Person Profile] [View Company] [Related News]                    ││
│ └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### 5.4 Custom Dashboards

**What:** Build personalized dashboards with drag-and-drop widgets.

**Components:**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 📊 My EV Industry Dashboard                           [Edit] [Share] [⋮]   │
├─────────────────────────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────┐ ┌─────────────────────────────────────────┐│
│ │ 📈 EV Market Cap Treemap    │ │ 📰 Latest EV Filings                    ││
│ │ ┌────────────────────────┐  │ │ • TSLA 8-K - 2h ago                    ││
│ │ │ TSLA          │ RIVN   │  │ │ • RIVN 10-Q - 1d ago                   ││
│ │ │ ██████████████│ ██     │  │ │ • NIO 6-K - 2d ago                     ││
│ │ │ │ LCID  │ NIO │        │  │ │ • LCID 8-K - 3d ago                    ││
│ │ │ │ ██    │ ███ │        │  │ └─────────────────────────────────────────││
│ │ └────────────────────────┘  │                                           ││
│ └─────────────────────────────┘ ┌─────────────────────────────────────────┐│
│ ┌─────────────────────────────┐ │ 🔔 My EV Alerts                         ││
│ │ 📊 Delivery Comparison      │ │ • TSLA Q4 deliveries expected tomorrow ││
│ │ Q4 2025 Deliveries (000s)   │ │ • NIO earnings call in 3 days         ││
│ │ TSLA ████████████████ 485   │ │ • RIVN Form 4 - insider purchase      ││
│ │ BYD  ███████████████░ 420   │ └─────────────────────────────────────────││
│ │ NIO  ███░░░░░░░░░░░░░  55   │                                           ││
│ │ RIVN ██░░░░░░░░░░░░░░  16   │                                           ││
│ └─────────────────────────────┘                                            ││
└─────────────────────────────────────────────────────────────────────────────┘
```

**Widget Types:**
- Company watchlist
- Metric charts (line, bar, treemap)
- Filing feed (filtered)
- Alert notifications
- Sector heatmap
- Knowledge graph mini-view
- Custom query results
- AI insights stream

---

### 5.5 API Explorer & SDK

**What:** Interactive API documentation with live testing.

**Components:**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 🔧 API Explorer                                                            │
├─────────────────────────────────────────────────────────────────────────────┤
│ Endpoints                    │ GET /api/companies/{ticker}                  │
│ ──────────────               │ ──────────────────────────────────────────── │
│ 📁 Companies                 │ Get detailed company information            │
│   GET /companies             │                                              │
│   GET /companies/{ticker}  ◀ │ Parameters:                                  │
│   GET /companies/{ticker}/   │ ┌─────────────────────────────────────────┐ │
│       filings                │ │ ticker (path)     │ TSLA                │ │
│ 📁 Filings                   │ │ include (query)   │ financials,officers │ │
│   GET /filings               │ └─────────────────────────────────────────┘ │
│   GET /filings/{id}          │                                              │
│ 📁 Search                    │ [Try It]                                     │
│   POST /search/companies     │                                              │
│   POST /search/filings       │ Response:                                    │
│ 📁 Graph                     │ ┌─────────────────────────────────────────┐ │
│   GET /graph/entity/{id}     │ │ {                                       │ │
│   GET /graph/neighbors/{id}  │ │   "cik": "0001318605",                  │ │
│                              │ │   "ticker": "TSLA",                     │ │
│                              │ │   "name": "Tesla, Inc.",                │ │
│                              │ │   "sector": "Consumer Cyclical",        │ │
│                              │ │   ...                                   │ │
│                              │ │ }                                       │ │
│                              │ └─────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Mind-Blowing Features

### 6.1 Real-Time Filing Analysis with AI

**What:** Live analysis as filings are being read, with AI highlighting key changes.

**Components:**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 📄 TESLA 10-K 2025                              🤖 AI Analysis: ON         │
├─────────────────────────────────────────────────────────────────────────────┤
│ ┌───────────────────────────────────────┐ ┌───────────────────────────────┐│
│ │ Filing Content                        │ │ AI Analysis Panel             ││
│ │                                       │ │                               ││
│ │ ITEM 1A. RISK FACTORS                 │ │ 🔴 HIGH IMPORTANCE            ││
│ │                                       │ │ ───────────────────────────── ││
│ │ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ │ │ New Risk Factor Detected:     ││
│ │ Our business may be adversely         │ │                               ││
│ │ affected by geopolitical tensions,    │ │ "Geopolitical tensions and    ││
│ │ particularly related to our           │ │ China exposure"               ││
│ │ operations in China.                  │ │                               ││
│ │ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ │ │ This is NEW in 2025 filing.   ││
│ │                                       │ │ Similar language found in:    ││
│ │ We rely heavily on our Shanghai       │ │ • Apple 10-K (2024)           ││
│ │ Gigafactory, which produced 47% of    │ │ • NVIDIA 10-K (2024)          ││
│ │ our vehicles in 2025...               │ │                               ││
│ │                                       │ │ 📊 China Revenue Exposure:    ││
│ │                                       │ │ TSLA: 22% │ AAPL: 19%        ││
│ │                                       │ │                               ││
│ │                                       │ │ [Deep Dive] [Compare] [Alert] ││
│ └───────────────────────────────────────┘ └───────────────────────────────┘│
├─────────────────────────────────────────────────────────────────────────────┤
│ AI Summary: This 10-K reveals increased China risk awareness, 45% higher   │
│ R&D spending, and first-time disclosure of AI/robotics development costs.  │
│ [Full Summary] [Key Takeaways] [Earnings Call Prep]                        │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### 6.2 Predictive Analytics Dashboard

**What:** ML-powered predictions for earnings, filings, and market events.

**Components:**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 🔮 Predictive Analytics                                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│ Upcoming Events Prediction                                                 │
│ ─────────────────────────────────────────────────────────────────────────  │
│                                                                             │
│ 📅 Expected Filings This Week                           Confidence         │
│ ┌─────────────────────────────────────────────────────────────────────────┐│
│ │ Company     │ Expected Form │ Expected Date │ Confidence │ Based On    ││
│ │ Apple       │ 10-Q          │ Jan 30        │ 95%        │ Historical  ││
│ │ Microsoft   │ 8-K           │ Jan 28        │ 87%        │ Earnings    ││
│ │ Amazon      │ 10-K          │ Feb 2         │ 92%        │ FY Pattern  ││
│ └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
│ 📊 Earnings Surprise Predictions                                           │
│ ┌─────────────────────────────────────────────────────────────────────────┐│
│ │ Company     │ Consensus EPS │ Our Prediction │ Surprise │ Signal       ││
│ │ TSLA       │ $0.85         │ $0.92          │ +8.2%    │ 🟢 Beat      ││
│ │ AAPL       │ $2.12         │ $2.08          │ -1.9%    │ 🟡 In-line   ││
│ │ NVDA       │ $5.45         │ $5.89          │ +8.1%    │ 🟢 Beat      ││
│ └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
│ 🚨 Anomaly Detection                                                       │
│ ┌─────────────────────────────────────────────────────────────────────────┐│
│ │ ⚠️ UNUSUAL: Intel ($INTC) Form 4 activity 340% above 90-day average    ││
│ │    Insider transactions suggest potential corporate action              ││
│ │    [View Details] [Set Alert]                                          ││
│ └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### 6.3 Voice & Chat Interface

**What:** Natural language interaction via voice or chat.

**Components:**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 💬 Entity Spine Assistant                                      [🎤 Voice]  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│ 🧑 "What did Tesla say about AI in their latest 10-K?"                     │
│                                                                             │
│ 🤖 Based on Tesla's 10-K filed January 27, 2026:                           │
│                                                                             │
│    Tesla mentioned AI 47 times, up from 23 in 2024. Key points:            │
│                                                                             │
│    1. **FSD Development**: "Full Self-Driving capability achieved          │
│       Level 4 autonomy in select markets..."                               │
│                                                                             │
│    2. **Optimus Robot**: "We expect Optimus humanoid robots to             │
│       begin limited production in 2027..."                                 │
│                                                                             │
│    3. **AI Compute**: "We invested $3.2B in AI training                    │
│       infrastructure, a 145% increase from 2024..."                        │
│                                                                             │
│    [View Full Section] [Compare to 2024] [Related Filings]                 │
│                                                                             │
│ ─────────────────────────────────────────────────────────────────────────  │
│ 🧑 "Compare that to Ford and GM's AI spending"                             │
│                                                                             │
│ 🤖 Comparing AI-related disclosures:                                       │
│                                                                             │
│    | Company | AI Mentions | AI Capex   | YoY Change |                     │
│    |---------|-------------|------------|------------|                     │
│    | TSLA    | 47          | $3.2B      | +145%      |                     │
│    | F       | 12          | $450M      | +23%       |                     │
│    | GM      | 18          | $680M      | +34%       |                     │
│                                                                             │
│    Tesla's AI investment is 4.7x higher than GM and 7.1x higher            │
│    than Ford, reflecting their focus on autonomy and robotics.             │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────────────────────────────────┐│
│ │ Ask anything about companies, filings, or relationships...             ││
│ └─────────────────────────────────────────────────────────────────────────┘│
│ Suggestions: [Latest 10-K filings] [Insider trading activity] [EV sector] │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### 6.4 AR/VR Data Visualization

**What:** Immersive data exploration in virtual reality.

**Components:**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 🥽 VR Mode: Market Universe                                    [Exit VR]   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│                    ╭────────────────────────────────╮                       │
│                   ╱                                  ╲                      │
│                  ╱    TECHNOLOGY SECTOR               ╲                     │
│                 ╱     $14.2T Market Cap                ╲                    │
│                ╱                                        ╲                   │
│               ╱    ┌─────┐                               ╲                  │
│              │     │AAPL │ ← You are here                 │                 │
│              │     │$3.2T│                                │                 │
│              │     └──┬──┘                                │                 │
│              │        │ competitor                        │                 │
│              │     ┌──┴──┐    ┌─────┐                     │                 │
│              │     │MSFT │────│GOOGL│                     │                 │
│              │     │$3.1T│    │$1.8T│                     │                 │
│              │     └─────┘    └─────┘                     │                 │
│               ╲                                          ╱                  │
│                ╲    [Grab to rotate] [Pinch to zoom]    ╱                   │
│                 ╲                                      ╱                    │
│                  ╲                                    ╱                     │
│                   ╲                                  ╱                      │
│                    ╰────────────────────────────────╯                       │
│                                                                             │
│ Controls: 👆 Point to select │ ✊ Grab to move │ 🤏 Pinch to zoom          │
│ Voice: "Show me Apple's competitors" "Filter by revenue > $100B"           │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### 6.5 Collaborative Research Workspace

**What:** Real-time multiplayer research environment with shared annotations.

**Components:**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 👥 Research Workspace: "Q1 2026 EV Analysis"           5 collaborators     │
├─────────────────────────────────────────────────────────────────────────────┤
│ ┌───────────────────────────────────────┐ ┌───────────────────────────────┐│
│ │ 📄 Document: TSLA 10-K 2025          │ │ 💬 Team Chat                  ││
│ │                                       │ │                               ││
│ │ Revenue increased by 12.4% to        │ │ @Sarah: Look at the margin    ││
│ │ $96.8B, driven by ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓  │ │ compression on page 45        ││
│ │                    ↑                  │ │                               ││
│ │          [Sarah is highlighting]      │ │ @Mike: Added to findings doc  ││
│ │                                       │ │                               ││
│ │ 💬 Sarah: "Key growth driver here"    │ │ @You: Comparing to Ford now   ││
│ │ 📌 Mike: "Compare to Ford 10-K p.23"  │ │                               ││
│ │                                       │ │ Sarah is viewing page 45...   ││
│ │ Gross margin decreased from 25.6%    │ │ Mike is in Document Library   ││
│ │ to 23.8%, primarily due to...        │ │                               ││
│ └───────────────────────────────────────┘ └───────────────────────────────┘│
├─────────────────────────────────────────────────────────────────────────────┤
│ 📋 Shared Findings                                     [+ Add Finding]     │
│ ─────────────────────────────────────────────────────────────────────────  │
│ ☑ TSLA margin compression -1.8pp (Sarah, Jan 27)                          │
│ ☑ RIVN production guidance raised +15% (Mike, Jan 27)                     │
│ ☐ NIO Europe expansion details needed (Assigned: John)                     │
│ ☐ Compare charging network capex across all 4 companies                    │
├─────────────────────────────────────────────────────────────────────────────┤
│ [Generate Report] [Schedule Meeting] [Export to Slides]                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 7. Architecture

### 7.1 System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ENTITY SPINE ARCHITECTURE                         │
└─────────────────────────────────────────────────────────────────────────────┘

                              ┌──────────────────┐
                              │   Web Frontend   │
                              │  (React + Vite)  │
                              └────────┬─────────┘
                                       │
                              ┌────────▼─────────┐
                              │   Mobile Apps    │
                              │ (React Native)   │
                              └────────┬─────────┘
                                       │
┌──────────────────────────────────────┼──────────────────────────────────────┐
│                                      │                                       │
│  ┌───────────────────────────────────▼────────────────────────────────────┐ │
│  │                           API Gateway                                   │ │
│  │                    (FastAPI / Authentication)                           │ │
│  └───────────────────────────────────┬────────────────────────────────────┘ │
│                                      │                                       │
│  ┌───────────────┬───────────────────┼───────────────────┬───────────────┐ │
│  │               │                   │                   │               │ │
│  ▼               ▼                   ▼                   ▼               ▼ │
│ ┌────────┐  ┌─────────┐  ┌──────────────┐  ┌─────────┐  ┌────────────┐    │
│ │Company │  │ Filing  │  │   Search     │  │  Graph  │  │    AI      │    │
│ │Service │  │ Service │  │   Service    │  │ Service │  │  Service   │    │
│ └───┬────┘  └────┬────┘  └──────┬───────┘  └────┬────┘  └─────┬──────┘    │
│     │            │              │               │              │           │
│     └────────────┴──────────────┴───────────────┴──────────────┘           │
│                                 │                                           │
│  ┌──────────────────────────────▼──────────────────────────────────────┐   │
│  │                        Data Layer                                    │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │   │
│  │  │  PostgreSQL  │  │    Redis     │  │ Elasticsearch│               │   │
│  │  │ (Primary DB) │  │   (Cache)    │  │   (Search)   │               │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘               │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      Background Workers                              │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │   │
│  │  │SEC Poller   │  │XBRL Parser  │  │Entity       │  │AI Analyzer  │ │   │
│  │  │             │  │             │  │Extractor    │  │             │ │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 7.2 Click-Through Navigation Map

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         NAVIGATION FLOW MAP                                 │
└─────────────────────────────────────────────────────────────────────────────┘

                            ┌──────────────┐
                            │  Dashboard   │
                            │   /home      │
                            └──────┬───────┘
                                   │
          ┌────────────────────────┼────────────────────────┐
          │                        │                        │
          ▼                        ▼                        ▼
   ┌──────────────┐         ┌──────────────┐         ┌──────────────┐
   │ Filing Feed  │         │   Watchlist  │         │   Sectors    │
   │   /feed      │         │  /watchlist  │         │  /sectors    │
   └──────┬───────┘         └──────┬───────┘         └──────┬───────┘
          │                        │                        │
          │ Click $TICKER          │ Click company          │ Click sector
          │                        │                        │
          ▼                        ▼                        ▼
   ┌──────────────────────────────────────────────────────────────────┐
   │                      Company Profile                              │
   │                     /company/:ticker                              │
   │  ┌─────────┬─────────┬──────────┬──────────────┬───────────────┐ │
   │  │Overview │Financials│ Filings │Relationships │   News        │ │
   │  └────┬────┴────┬────┴────┬─────┴──────┬───────┴───────┬───────┘ │
   └───────┼─────────┼─────────┼────────────┼───────────────┼─────────┘
           │         │         │            │               │
           │         │         │            │               │
           ▼         ▼         ▼            ▼               ▼
    ┌──────────┐ ┌────────┐ ┌──────────┐ ┌────────────┐ ┌──────────┐
    │ Company  │ │Financial│ │ Filing   │ │ Knowledge  │ │ News     │
    │ Summary  │ │Statement│ │ Viewer   │ │   Graph    │ │ Feed     │
    │          │ │  View   │ │          │ │            │ │          │
    └──────────┘ └────────┘ └────┬─────┘ └─────┬──────┘ └──────────┘
                                 │             │
                          Click link     Click entity
                                 │             │
                                 ▼             ▼
                          ┌──────────┐  ┌──────────────┐
                          │ Document │  │ Entity       │
                          │ Viewer   │  │ Profile      │
                          │/filing/id│  │/entity/:id   │
                          └──────────┘  └──────────────┘
```

### 7.3 API Endpoints

```yaml
# Core API Structure
/api/v1:
  # Companies
  /companies:
    GET:    List companies (with search/filter)
    POST:   Create company (admin)
  /companies/{ticker}:
    GET:    Get company profile
    PUT:    Update company (admin)
  /companies/{ticker}/filings:
    GET:    List company filings
  /companies/{ticker}/financials:
    GET:    Get financial statements
  /companies/{ticker}/relationships:
    GET:    Get company relationships
  /companies/{ticker}/competitors:
    GET:    Get competitor companies

  # Filings
  /filings:
    GET:    List filings (with filters)
  /filings/{id}:
    GET:    Get filing details
  /filings/{id}/document:
    GET:    Get filing document
  /filings/{id}/xbrl:
    GET:    Get parsed XBRL data
  /filings/{id}/diff:
    GET:    Get diff with previous filing

  # Search
  /search/companies:
    POST:   Advanced company search
  /search/filings:
    POST:   Full-text filing search
  /search/query:
    POST:   Natural language query

  # Knowledge Graph
  /graph/entities:
    GET:    List entities
  /graph/entities/{id}:
    GET:    Get entity details
  /graph/entities/{id}/neighbors:
    GET:    Get connected entities
  /graph/paths:
    POST:   Find paths between entities
  /graph/subgraph:
    POST:   Extract subgraph

  # User Features
  /watchlists:
    GET:    List user watchlists
    POST:   Create watchlist
  /watchlists/{id}:
    GET:    Get watchlist
    PUT:    Update watchlist
    DELETE: Delete watchlist
  /alerts:
    GET:    List user alerts
    POST:   Create alert

  # AI Features
  /ai/summarize:
    POST:   Summarize document
  /ai/insights:
    GET:    Get AI insights feed
  /ai/chat:
    POST:   Chat with AI assistant
```

---

## 8. Implementation Phases

### Phase 1: Foundation (Weeks 1-4)

**Backend:**
- [ ] Set up FastAPI project structure
- [ ] Implement PostgreSQL schema (companies, filings, entities)
- [ ] Create SEC EDGAR polling service
- [ ] Basic XBRL parser
- [ ] Authentication system

**Frontend:**
- [ ] Set up React + Vite + TypeScript project
- [ ] Implement routing structure
- [ ] Create basic layout components
- [ ] Simple search functionality
- [ ] Company profile page (basic)

**Testing:**
- [ ] Unit tests for data models
- [ ] API endpoint tests
- [ ] Basic Playwright setup

---

### Phase 2: Core Features (Weeks 5-8)

**Backend:**
- [ ] Financial statement extraction
- [ ] Entity extraction pipeline
- [ ] Relationship detection
- [ ] Search indexing (Elasticsearch)
- [ ] Watchlist & alerts system

**Frontend:**
- [ ] Filing feed (Instagram-style)
- [ ] Financial statements view
- [ ] Watchlist management
- [ ] Sector explorer
- [ ] Advanced search UI

**Testing:**
- [ ] Integration tests for ETL pipeline
- [ ] E2E tests for core user flows
- [ ] Performance benchmarks

---

### Phase 3: Advanced Features (Weeks 9-16)

**Backend:**
- [ ] Knowledge graph service
- [ ] Universal query engine
- [ ] AI summarization integration
- [ ] Filing diff detection
- [ ] Competitor analysis engine

**Frontend:**
- [ ] Knowledge graph 3D visualization
- [ ] Query builder UI
- [ ] AI insights feed
- [ ] Filing diff viewer
- [ ] Competitor comparison

**Testing:**
- [ ] Graph traversal tests
- [ ] AI response validation
- [ ] Load testing

---

### Phase 4: Polish & Scale (Weeks 17-24)

**Backend:**
- [ ] Caching optimization
- [ ] API rate limiting
- [ ] Webhook integrations
- [ ] Export functionality
- [ ] Multi-tenancy support

**Frontend:**
- [ ] Custom dashboards
- [ ] Mobile responsive
- [ ] Offline support (PWA)
- [ ] Accessibility audit
- [ ] Performance optimization

**Testing:**
- [ ] Cross-browser testing
- [ ] Mobile testing
- [ ] Security audit
- [ ] Full E2E coverage

---

## 9. Testing Strategy

### 9.1 Testing Pyramid

```
                    ╱╲
                   ╱  ╲
                  ╱ E2E╲         10% - Critical user flows
                 ╱ Tests╲
                ╱────────╲
               ╱Integration╲     20% - API & service tests
              ╱   Tests     ╲
             ╱────────────────╲
            ╱    Unit Tests    ╲  70% - Functions & components
           ╱____________________╲
```

### 9.2 Test Structure

```
entityspine/
├── tests/
│   ├── unit/
│   │   ├── test_models.py
│   │   ├── test_parsers.py
│   │   ├── test_services.py
│   │   └── test_utils.py
│   ├── integration/
│   │   ├── test_api_companies.py
│   │   ├── test_api_filings.py
│   │   ├── test_api_search.py
│   │   ├── test_etl_pipeline.py
│   │   └── test_graph_queries.py
│   └── e2e/
│       ├── playwright.config.ts
│       └── specs/
│           ├── company-profile.spec.ts
│           ├── filing-feed.spec.ts
│           ├── search.spec.ts
│           └── watchlist.spec.ts

frontend/
├── src/
│   └── __tests__/
│       ├── components/
│       │   ├── CompanyCard.test.tsx
│       │   ├── FilingFeed.test.tsx
│       │   └── SearchBar.test.tsx
│       └── hooks/
│           ├── useCompany.test.ts
│           └── useSearch.test.ts
├── tests/
│   └── e2e/
│       ├── playwright.config.ts
│       └── specs/
│           ├── navigation.spec.ts
│           ├── search-flow.spec.ts
│           └── company-profile.spec.ts
```

### 9.3 Playwright E2E Examples

```typescript
// tests/e2e/specs/company-profile.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Company Profile Page', () => {
  test('navigates to company profile from search', async ({ page }) => {
    await page.goto('/');
    
    // Open search
    await page.keyboard.press('Control+k');
    await page.getByPlaceholder('Search companies').fill('Tesla');
    
    // Click first result
    await page.getByRole('option', { name: /Tesla/i }).click();
    
    // Verify navigation
    await expect(page).toHaveURL(/\/company\/tsla/);
    await expect(page.getByRole('heading', { name: /Tesla/i })).toBeVisible();
  });

  test('displays financial statements', async ({ page }) => {
    await page.goto('/company/tsla');
    
    // Click financials tab
    await page.getByRole('tab', { name: 'Financials' }).click();
    
    // Verify data loads
    await expect(page.getByText('Revenue')).toBeVisible();
    await expect(page.getByText(/\$\d+\.\d+[BM]/)).toBeVisible();
  });

  test('adds company to watchlist', async ({ page }) => {
    // Login first
    await page.goto('/login');
    await page.fill('[name="email"]', 'test@example.com');
    await page.fill('[name="password"]', 'password123');
    await page.click('button[type="submit"]');
    
    // Go to company
    await page.goto('/company/tsla');
    
    // Add to watchlist
    await page.getByRole('button', { name: /Add to Watchlist/i }).click();
    
    // Verify added
    await expect(page.getByRole('button', { name: /In Watchlist/i })).toBeVisible();
    
    // Verify in watchlist page
    await page.goto('/watchlist');
    await expect(page.getByText('Tesla')).toBeVisible();
  });
});
```

---

## 10. File Structure

### 10.1 Backend Structure

```
entityspine/
├── README.md
├── pyproject.toml
├── requirements.txt
├── docker-compose.yml
├── Dockerfile
│
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app entry
│   ├── config.py                  # Settings & env vars
│   │
│   ├── api/                       # API routes
│   │   ├── __init__.py
│   │   ├── deps.py                # Dependencies (auth, db)
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── companies.py       # Company endpoints
│   │   │   ├── filings.py         # Filing endpoints
│   │   │   ├── search.py          # Search endpoints
│   │   │   ├── graph.py           # Knowledge graph endpoints
│   │   │   ├── watchlists.py      # Watchlist endpoints
│   │   │   ├── alerts.py          # Alert endpoints
│   │   │   └── ai.py              # AI feature endpoints
│   │   └── router.py              # API router
│   │
│   ├── core/                      # Core functionality
│   │   ├── __init__.py
│   │   ├── security.py            # Auth & JWT
│   │   ├── permissions.py         # RBAC
│   │   └── exceptions.py          # Custom exceptions
│   │
│   ├── db/                        # Database
│   │   ├── __init__.py
│   │   ├── session.py             # DB session
│   │   ├── base.py                # Base model
│   │   └── migrations/            # Alembic migrations
│   │
│   ├── models/                    # SQLAlchemy models
│   │   ├── __init__.py
│   │   ├── company.py
│   │   ├── filing.py
│   │   ├── entity.py
│   │   ├── relationship.py
│   │   ├── financial.py
│   │   ├── user.py
│   │   ├── watchlist.py
│   │   └── alert.py
│   │
│   ├── schemas/                   # Pydantic schemas
│   │   ├── __init__.py
│   │   ├── company.py
│   │   ├── filing.py
│   │   ├── search.py
│   │   ├── graph.py
│   │   └── user.py
│   │
│   ├── services/                  # Business logic
│   │   ├── __init__.py
│   │   ├── company_service.py
│   │   ├── filing_service.py
│   │   ├── search_service.py
│   │   ├── graph_service.py
│   │   ├── financial_service.py
│   │   ├── watchlist_service.py
│   │   └── alert_service.py
│   │
│   └── workers/                   # Background tasks
│       ├── __init__.py
│       ├── sec_poller.py          # SEC EDGAR polling
│       ├── xbrl_parser.py         # XBRL extraction
│       ├── entity_extractor.py    # NER extraction
│       └── ai_analyzer.py         # AI analysis
│
├── tests/
│   ├── conftest.py
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
└── scripts/
    ├── seed_data.py
    ├── run_backfill.py
    └── export_schema.py
```

### 10.2 Frontend Structure

```
frontend/
├── README.md
├── package.json
├── vite.config.ts
├── tsconfig.json
├── tailwind.config.js
├── playwright.config.ts
│
├── public/
│   ├── favicon.ico
│   └── assets/
│
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── index.css
│   │
│   ├── api/                       # API client
│   │   ├── client.ts
│   │   ├── companies.ts
│   │   ├── filings.ts
│   │   ├── search.ts
│   │   ├── graph.ts
│   │   └── types.ts
│   │
│   ├── components/                # Reusable components
│   │   ├── ui/                    # Base UI components
│   │   │   ├── Button.tsx
│   │   │   ├── Card.tsx
│   │   │   ├── Table.tsx
│   │   │   ├── Modal.tsx
│   │   │   └── ...
│   │   │
│   │   ├── layout/                # Layout components
│   │   │   ├── Header.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   ├── Footer.tsx
│   │   │   └── MainLayout.tsx
│   │   │
│   │   ├── company/               # Company-related
│   │   │   ├── CompanyCard.tsx
│   │   │   ├── CompanyHeader.tsx
│   │   │   ├── CompanyMetrics.tsx
│   │   │   ├── CompanyDescription.tsx
│   │   │   └── CompetitorTable.tsx
│   │   │
│   │   ├── filing/                # Filing-related
│   │   │   ├── FilingCard.tsx
│   │   │   ├── FilingFeed.tsx
│   │   │   ├── FilingViewer.tsx
│   │   │   ├── FilingDiff.tsx
│   │   │   └── XBRLTable.tsx
│   │   │
│   │   ├── financial/             # Financial data
│   │   │   ├── IncomeStatement.tsx
│   │   │   ├── BalanceSheet.tsx
│   │   │   ├── CashFlow.tsx
│   │   │   └── MetricChart.tsx
│   │   │
│   │   ├── graph/                 # Knowledge graph
│   │   │   ├── KnowledgeGraph2D.tsx
│   │   │   ├── KnowledgeGraph3D.tsx
│   │   │   ├── GraphControls.tsx
│   │   │   └── EntityNode.tsx
│   │   │
│   │   ├── search/                # Search components
│   │   │   ├── SearchBar.tsx
│   │   │   ├── SearchResults.tsx
│   │   │   ├── QueryBuilder.tsx
│   │   │   └── FilterPanel.tsx
│   │   │
│   │   └── dashboard/             # Dashboard widgets
│   │       ├── WatchlistWidget.tsx
│   │       ├── AlertsWidget.tsx
│   │       ├── InsightsWidget.tsx
│   │       └── SectorHeatmap.tsx
│   │
│   ├── pages/                     # Page components
│   │   ├── HomePage.tsx
│   │   ├── CompanyProfilePage.tsx
│   │   ├── FilingViewerPage.tsx
│   │   ├── SectorExplorerPage.tsx
│   │   ├── KnowledgeGraphPage.tsx
│   │   ├── SearchPage.tsx
│   │   ├── WatchlistPage.tsx
│   │   ├── AlertsPage.tsx
│   │   ├── DashboardPage.tsx
│   │   └── SettingsPage.tsx
│   │
│   ├── hooks/                     # Custom hooks
│   │   ├── useCompany.ts
│   │   ├── useFilings.ts
│   │   ├── useSearch.ts
│   │   ├── useGraph.ts
│   │   ├── useWatchlist.ts
│   │   └── useAlerts.ts
│   │
│   ├── stores/                    # State management
│   │   ├── authStore.ts
│   │   ├── uiStore.ts
│   │   └── watchlistStore.ts
│   │
│   ├── utils/                     # Utilities
│   │   ├── formatters.ts
│   │   ├── validators.ts
│   │   └── constants.ts
│   │
│   └── types/                     # TypeScript types
│       ├── company.ts
│       ├── filing.ts
│       ├── graph.ts
│       └── api.ts
│
├── tests/
│   ├── unit/
│   └── e2e/
│       └── specs/
│
└── .storybook/                    # Component documentation
    └── main.js
```

---

## Summary

This roadmap provides a comprehensive guide to building a professional-grade financial data platform. Key takeaways:

1. **Start Simple**: Basic features provide immediate value
2. **Iterate**: Each phase builds on the previous
3. **Test Everything**: Automated tests ensure quality
4. **Modular Design**: Components are reusable and maintainable
5. **User-Centric**: Every feature maps to a user need

The end result will be a Bloomberg/FactSet-quality platform that makes financial data accessible and actionable for everyone.
