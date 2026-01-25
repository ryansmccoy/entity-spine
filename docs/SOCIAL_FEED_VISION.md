# EntitySpine Social Feed Vision

## "Instagram for Financial Intelligence"

A social media-inspired experience for exploring SEC filings, knowledge graph discoveries, and financial data - combining the engagement of social feeds with institutional-grade financial intelligence.

---

## Table of Contents

1. [Core Concept](#1-core-concept)
2. [Feature Tiers](#2-feature-tiers)
3. [Page Architecture](#3-page-architecture)
4. [Component Library](#4-component-library)
5. [API Endpoints](#5-api-endpoints)
6. [Database Schema](#6-database-schema)
7. [Implementation Phases](#7-implementation-phases)
8. [Testing Strategy](#8-testing-strategy)
9. [File Structure](#9-file-structure)

---

## 1. Core Concept

### The Problem
Traditional financial terminals present data in dense, overwhelming interfaces. Users miss important events because they can't monitor everything.

### The Solution
Transform financial data into an engaging, scrollable feed experience:
- **Automated Posts**: AI generates posts when new relationships discovered, filings parsed, or significant changes detected
- **Visual Cards**: Each event becomes an Instagram-style card with key metrics, charts, and actions
- **Personalized Feeds**: Follow companies, sectors, or relationship types
- **Discovery**: Explore trending tickers, sectors, and emerging patterns

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    ENTITYSPINE SOCIAL FEED EXPERIENCE                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  📱 FEED VIEW (Instagram-style)                                      │   │
│  │  ═══════════════════════════════════════════════════════════════    │   │
│  │                                                                      │   │
│  │  ┌───────────────────────────────────────────────────────────────┐  │   │
│  │  │  🤖 EntitySpine AI • 2 hours ago                              │  │   │
│  │  │  ─────────────────────────────────────────────────────────────│  │   │
│  │  │  📊 New Relationship Discovered                               │  │   │
│  │  │                                                               │  │   │
│  │  │  $TSLA ──────────────── supplies_to ─────────────── $AAPL    │  │   │
│  │  │                                                               │  │   │
│  │  │  "Tesla has entered a battery supply agreement with Apple    │  │   │
│  │  │   for their upcoming EV project, per 8-K filing..."         │  │   │
│  │  │                                                               │  │   │
│  │  │  ❤️ 234   💬 45   🔖 Save   📤 Share                         │  │   │
│  │  └───────────────────────────────────────────────────────────────┘  │   │
│  │                                                                      │   │
│  │  ┌───────────────────────────────────────────────────────────────┐  │   │
│  │  │  📄 SEC Filing Bot • 4 hours ago                              │  │   │
│  │  │  ─────────────────────────────────────────────────────────────│  │   │
│  │  │  New 10-K Filed: $NVDA                                        │  │   │
│  │  │                                                               │  │   │
│  │  │  ┌─────────────────────────────────────────────────────────┐ │  │   │
│  │  │  │  Revenue: $60.9B (+126% YoY)  │  Net Income: $29.8B    │ │  │   │
│  │  │  │  Gross Margin: 72.7%          │  R&D: $8.7B (+40%)     │ │  │   │
│  │  │  └─────────────────────────────────────────────────────────┘ │  │   │
│  │  │                                                               │  │   │
│  │  │  Key Risk Factors Changed: Supply Chain, China Export...     │  │   │
│  │  │                                                               │  │   │
│  │  │  ❤️ 892   💬 156   🔖 Save   📤 Share   [View Full Filing]   │  │   │
│  │  └───────────────────────────────────────────────────────────────┘  │   │
│  │                                                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Feature Tiers

### 🟢 BASIC TIER (5 Features)

| # | Feature | Description | Click Action |
|---|---------|-------------|--------------|
| 1 | **Filing Feed** | Chronological feed of new SEC filings with summary cards | Click ticker → Company Profile |
| 2 | **Company Profile** | Basic company page with overview, recent filings, key metrics | Click filing → Filing Detail |
| 3 | **Sector Browser** | Grid/table view of all sectors with company counts | Click sector → Sector Detail |
| 4 | **Simple Search** | Search by ticker, company name, CIK | Click result → Company Profile |
| 5 | **Watchlist** | Save companies to personal watchlist | Click company → Company Profile |

### 🟡 INTERMEDIATE TIER (5 Features)

| # | Feature | Description | Click Action |
|---|---------|-------------|--------------|
| 6 | **Personalized Feed** | Algorithm-driven feed based on watchlist & activity | Click card → Relevant detail page |
| 7 | **Relationship Cards** | Visual cards showing entity relationships from knowledge graph | Click relationship → Relationship Explorer |
| 8 | **Financial Statements** | Interactive income statement, balance sheet, cash flow | Click line item → Drill-down modal |
| 9 | **Industry Comparisons** | Side-by-side metrics for companies in same industry | Click competitor → Company Profile |
| 10 | **Saved Searches** | Save and rerun complex queries | Click saved search → Results page |

### 🔴 ADVANCED TIER (5 Features)

| # | Feature | Description | Click Action |
|---|---------|-------------|--------------|
| 11 | **Knowledge Graph Explorer** | 3D visualization of entity relationships | Click node → Entity Detail |
| 12 | **Universal Query Builder** | Natural language + structured query interface | Execute → Results grid |
| 13 | **Revenue Segmentation** | Revenue by customer, geography, product line | Click segment → Segment detail |
| 14 | **Risk Factor Analysis** | AI-summarized risk factors with change detection | Click risk → Historical comparison |
| 15 | **Alert Automation** | Complex conditional alerts (e.g., "notify when revenue drops >10%") | Click alert → Alert configuration |

### 🟣 MINDBLOWING TIER (5 Features)

| # | Feature | Description | Click Action |
|---|---------|-------------|--------------|
| 16 | **AI News Synthesis** | GPT-generated narratives from multiple filings | Click narrative → Source filings |
| 17 | **Predictive Signals** | ML models predicting earnings surprises, M&A likelihood | Click signal → Model explanation |
| 18 | **Supply Chain Mapping** | Full supply chain visualization with disruption alerts | Click supplier → Supplier profile |
| 19 | **Earnings Call Transcripts** | Searchable transcripts with sentiment analysis | Click quote → Audio timestamp |
| 20 | **Portfolio Impact Simulator** | "What-if" scenarios for portfolio exposure | Click scenario → Detailed breakdown |

---

## 3. Page Architecture

### 3.1 Feed Page (`/feed`)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ENTITYSPINE FEED                    🔍 Search    🔔 Alerts    👤 Profile   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────┐  ┌────────────────────────────────────────────────────┐   │
│  │ FILTERS     │  │ MAIN FEED                                          │   │
│  │ ─────────── │  │ ──────────────────────────────────────────────────│   │
│  │             │  │                                                    │   │
│  │ Feed Type:  │  │  ┌────────────────────────────────────────────┐   │   │
│  │ ○ All       │  │  │ 🤖 New Relationship • 2h ago               │   │   │
│  │ ● Filings   │  │  │ $TSLA ← supplies_to → $AAPL               │   │   │
│  │ ○ Relations │  │  │ Battery supply agreement announced...      │   │   │
│  │ ○ Alerts    │  │  │ ❤️ 234  💬 45  🔖  📤                      │   │   │
│  │             │  │  └────────────────────────────────────────────┘   │   │
│  │ Sectors:    │  │                                                    │   │
│  │ ☑ Tech      │  │  ┌────────────────────────────────────────────┐   │   │
│  │ ☑ Finance   │  │  │ 📄 10-K Filed • 4h ago                     │   │   │
│  │ ☐ Healthcare│  │  │ $NVDA - NVIDIA Corporation                 │   │   │
│  │ ☐ Energy    │  │  │ Revenue: $60.9B (+126% YoY)               │   │   │
│  │             │  │  │ [View Filing] [Company Profile]            │   │   │
│  │ Form Types: │  │  └────────────────────────────────────────────┘   │   │
│  │ ☑ 10-K      │  │                                                    │   │
│  │ ☑ 10-Q      │  │  ┌────────────────────────────────────────────┐   │   │
│  │ ☑ 8-K       │  │  │ 🏢 New Company Added • 6h ago              │   │   │
│  │ ☐ DEF 14A   │  │  │ $PLTR - Palantir Technologies              │   │   │
│  │             │  │  │ Sector: Technology | Industry: Software    │   │   │
│  │ Time Range: │  │  │ [Follow] [View Profile]                    │   │   │
│  │ [Today ▼]   │  │  └────────────────────────────────────────────┘   │   │
│  │             │  │                                                    │   │
│  └─────────────┘  │  [Load More...]                                    │   │
│                   └────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Company Profile Page (`/company/:ticker`)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ← Back    $TSLA - Tesla, Inc.                    ⭐ Follow    🔔 Alert     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  COMPANY HEADER                                                      │   │
│  │  ═══════════════════════════════════════════════════════════════    │   │
│  │  Tesla, Inc.                                 Market Cap: $789.2B    │   │
│  │  Technology > Automobiles > Electric Vehicles                        │   │
│  │                                                                      │   │
│  │  CIK: 0001318605 | Founded: 2003 | HQ: Austin, TX | CEO: Elon Musk │   │
│  │                                                                      │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │   │
│  │  │ Price    │ │ P/E      │ │ Revenue  │ │ EPS      │ │ Employees│  │   │
│  │  │ $248.50  │ │ 65.2x    │ │ $96.8B   │ │ $3.81    │ │ 140,473  │  │   │
│  │  │ +2.3%    │ │ vs 25x   │ │ +19% YoY │ │ +12% YoY │ │ +8% YoY  │  │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  [Overview] [Financials] [Filings] [Relationships] [Segments]       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌────────────────────────────────┐  ┌──────────────────────────────────┐  │
│  │  RECENT FILINGS                │  │  ENTITY RELATIONSHIPS            │  │
│  │  ──────────────────────────    │  │  ────────────────────────────    │  │
│  │  📄 10-K  2024-02-15  Annual   │  │                                  │  │
│  │  📄 10-Q  2024-11-01  Q3 2024  │  │      Panasonic                   │  │
│  │  📄 8-K   2024-10-23  Earnings │  │         ↓ supplies_to            │  │
│  │  📄 8-K   2024-10-15  Other    │  │      [$TSLA]                     │  │
│  │                                │  │    ↙    ↓    ↘                   │  │
│  │  [View All Filings →]          │  │ SpaceX  SolarCity  Boring Co    │  │
│  └────────────────────────────────┘  │  (subsidiary) (subsidiary)       │  │
│                                      │                                  │  │
│  ┌────────────────────────────────┐  │  [Explore Full Graph →]          │  │
│  │  REVENUE BY SEGMENT            │  └──────────────────────────────────┘  │
│  │  ──────────────────────────    │                                        │
│  │  Automotive  ████████████ 82%  │  ┌──────────────────────────────────┐  │
│  │  Energy      ████ 12%          │  │  COMPETITORS                     │  │
│  │  Services    ██ 6%             │  │  ────────────────────────────    │  │
│  │                                │  │  $RIVN  Rivian     -$1.2B loss   │  │
│  │  [View Detailed Segments →]    │  │  $LCID  Lucid      -$800M loss   │  │
│  └────────────────────────────────┘  │  $F     Ford EV    +$2.1B profit │  │
│                                      │                                  │  │
│                                      │  [Compare All →]                 │  │
│                                      └──────────────────────────────────┘  │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  INDUSTRY NEWS FEED                                                  │   │
│  │  ═══════════════════════════════════════════════════════════════    │   │
│  │                                                                      │   │
│  │  ┌───────────────────────────────────────────────────────────────┐  │   │
│  │  │ $RIVN filed 8-K: Production guidance reduced by 15%...        │  │   │
│  │  │ 2 hours ago • Impact: Competitor weakness                     │  │   │
│  │  └───────────────────────────────────────────────────────────────┘  │   │
│  │  ┌───────────────────────────────────────────────────────────────┐  │   │
│  │  │ $LCID supply agreement with Panasonic (TSLA's supplier)...    │  │   │
│  │  │ 5 hours ago • Impact: Supplier relationship                   │  │   │
│  │  └───────────────────────────────────────────────────────────────┘  │   │
│  │                                                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.3 Sector Explorer Page (`/sectors`)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  SECTOR EXPLORER                     🔍 Search Sectors    📊 View: [Grid ▼] │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  SECTOR OVERVIEW                                                     │   │
│  │  ═══════════════════════════════════════════════════════════════    │   │
│  │                                                                      │   │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐       │   │
│  │  │ Technology │ │ Healthcare │ │ Financials │ │ Energy     │       │   │
│  │  │ 📊 2,450   │ │ 📊 1,892   │ │ 📊 1,654   │ │ 📊 987     │       │   │
│  │  │ companies  │ │ companies  │ │ companies  │ │ companies  │       │   │
│  │  │            │ │            │ │            │ │            │       │   │
│  │  │ +2.4% MTD  │ │ -0.8% MTD  │ │ +1.2% MTD  │ │ +5.1% MTD  │       │   │
│  │  │            │ │            │ │            │ │            │       │   │
│  │  │ Top: $AAPL │ │ Top: $UNH  │ │ Top: $JPM  │ │ Top: $XOM  │       │   │
│  │  └────────────┘ └────────────┘ └────────────┘ └────────────┘       │   │
│  │                                                                      │   │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐       │   │
│  │  │ Industrials│ │ Consumer   │ │ Real Estate│ │ Materials  │       │   │
│  │  │ 📊 1,234   │ │ 📊 2,100   │ │ 📊 456     │ │ 📊 345     │       │   │
│  │  │ companies  │ │ companies  │ │ companies  │ │ companies  │       │   │
│  │  └────────────┘ └────────────┘ └────────────┘ └────────────┘       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  TECHNOLOGY SECTOR DETAIL (Click to expand)                          │   │
│  │  ═══════════════════════════════════════════════════════════════    │   │
│  │                                                                      │   │
│  │  Industries within Technology:                                       │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │ Industry          │ Companies │ Avg P/E │ YTD Return │ Top  │   │   │
│  │  ├───────────────────┼───────────┼─────────┼────────────┼──────┤   │   │
│  │  │ Semiconductors    │ 234       │ 28.5x   │ +45.2%     │ NVDA │   │   │
│  │  │ Software          │ 890       │ 35.2x   │ +22.1%     │ MSFT │   │   │
│  │  │ Hardware          │ 456       │ 22.1x   │ +18.5%     │ AAPL │   │   │
│  │  │ IT Services       │ 345       │ 18.9x   │ +12.3%     │ IBM  │   │   │
│  │  │ Internet          │ 525       │ 42.3x   │ +28.9%     │ GOOGL│   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  │                                                                      │   │
│  │  [View All 2,450 Technology Companies →]                             │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.4 Universal Query Page (`/query`)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  UNIVERSAL QUERY                                              [Save Query]  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  QUERY BUILDER                                                       │   │
│  │  ═══════════════════════════════════════════════════════════════    │   │
│  │                                                                      │   │
│  │  🗣️ Natural Language:                                               │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │ "Show me technology companies with revenue > $10B and P/E   │   │   │
│  │  │  < 30 that have filed 10-K in the last 30 days"             │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  │                                                                      │   │
│  │  ── OR ── Structured Query:                                         │   │
│  │                                                                      │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │ WHERE                                                        │   │   │
│  │  │   Sector        [= ▼]  [Technology        ▼]    [+ Add]     │   │   │
│  │  │   Revenue       [> ▼]  [$10,000,000,000    ]    [+ Add]     │   │   │
│  │  │   P/E Ratio     [< ▼]  [30                 ]    [+ Add]     │   │   │
│  │  │   Filing Type   [= ▼]  [10-K              ▼]    [+ Add]     │   │   │
│  │  │   Filing Date   [> ▼]  [2024-01-01         ]    [+ Add]     │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  │                                                                      │   │
│  │  [🔍 Execute Query]                                                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  RESULTS (47 companies)                              [Export CSV]   │   │
│  │  ═══════════════════════════════════════════════════════════════    │   │
│  │                                                                      │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │ Ticker │ Company          │ Revenue  │ P/E   │ Filing Date │   │   │
│  │  ├────────┼──────────────────┼──────────┼───────┼─────────────┤   │   │
│  │  │ $AAPL  │ Apple Inc.       │ $383.3B  │ 28.5x │ 2024-11-01  │   │   │
│  │  │ $MSFT  │ Microsoft Corp.  │ $211.9B  │ 29.2x │ 2024-10-30  │   │   │
│  │  │ $GOOGL │ Alphabet Inc.    │ $307.4B  │ 22.1x │ 2024-10-29  │   │   │
│  │  │ $META  │ Meta Platforms   │ $134.9B  │ 24.8x │ 2024-10-25  │   │   │
│  │  │ ...    │ ...              │ ...      │ ...   │ ...         │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  │                                                                      │   │
│  │  [1] [2] [3] [4] [5] ... [10]  |  Showing 1-10 of 47                │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.5 Relationship Explorer Page (`/relationships`)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  RELATIONSHIP EXPLORER                        [2D] [3D]    🔍 Find Path    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────┐  ┌─────────────────────────────────────────────────────┐  │
│  │ FILTERS     │  │ KNOWLEDGE GRAPH VISUALIZATION                       │  │
│  │ ─────────── │  │ ───────────────────────────────────────────────────│  │
│  │             │  │                                                     │  │
│  │ Relationship│  │              ┌─────┐                               │  │
│  │ Types:      │  │         ┌────│$TSLA│────┐                          │  │
│  │ ☑ supplies  │  │         │    └─────┘    │                          │  │
│  │ ☑ subsidiary│  │         │       │       │                          │  │
│  │ ☑ officer   │  │    ┌────┴───┐   │   ┌───┴────┐                     │  │
│  │ ☐ investor  │  │    │Panasonic│   │   │SpaceX  │                     │  │
│  │ ☐ competitor│  │    └────────┘   │   └────────┘                     │  │
│  │             │  │         supplies │ subsidiary                       │  │
│  │ Entity Type:│  │                 │                                   │  │
│  │ ☑ Company   │  │            ┌────┴────┐                             │  │
│  │ ☑ Person    │  │            │Elon Musk│                             │  │
│  │ ☐ Location  │  │            └─────────┘                             │  │
│  │ ☐ Product   │  │               CEO_of                               │  │
│  │             │  │                                                     │  │
│  │ Depth:      │  │  [Zoom +] [Zoom -] [Reset] [Fullscreen]            │  │
│  │ [2 ▼]       │  │                                                     │  │
│  └─────────────┘  └─────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  RELATIONSHIP FEED                                                   │   │
│  │  ═══════════════════════════════════════════════════════════════    │   │
│  │                                                                      │   │
│  │  🔗 $TSLA ←─ supplies_to ─→ Panasonic (battery cells)               │   │
│  │     Source: 10-K 2024 | Confidence: 95% | Since: 2014                │   │
│  │                                                                      │   │
│  │  🔗 $TSLA ←─ subsidiary_of ─→ SpaceX                                 │   │
│  │     Source: 8-K 2022-12-01 | Confidence: 100% | Since: 2002          │   │
│  │                                                                      │   │
│  │  🔗 Elon Musk ←─ CEO_of ─→ $TSLA                                     │   │
│  │     Source: DEF 14A 2024 | Confidence: 100% | Since: 2008            │   │
│  │                                                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Component Library

### Feed Components

```typescript
// FeedCard - Base card for all feed items
interface FeedCardProps {
  type: 'filing' | 'relationship' | 'company' | 'alert' | 'insight';
  timestamp: Date;
  source: string;
  children: React.ReactNode;
  actions?: FeedAction[];
  onLike?: () => void;
  onComment?: () => void;
  onSave?: () => void;
  onShare?: () => void;
}

// FilingCard - SEC filing announcement
interface FilingCardProps {
  ticker: string;
  companyName: string;
  formType: string;
  filedDate: Date;
  summary?: string;
  highlights?: FilingHighlight[];
  onViewFiling: () => void;
  onViewCompany: () => void;
}

// RelationshipCard - New relationship discovered
interface RelationshipCardProps {
  sourceEntity: Entity;
  targetEntity: Entity;
  relationshipType: string;
  confidence: number;
  sourceDocument?: string;
  description?: string;
  onExploreGraph: () => void;
}

// CompanyCard - Company added or updated
interface CompanyCardProps {
  ticker: string;
  companyName: string;
  sector: string;
  industry: string;
  metrics: CompanyMetric[];
  onFollow: () => void;
  onViewProfile: () => void;
}
```

### Company Profile Components

```typescript
// CompanyHeader - Top section of company profile
interface CompanyHeaderProps {
  ticker: string;
  name: string;
  sector: string;
  industry: string;
  marketCap: number;
  price: number;
  priceChange: number;
  cik: string;
  founded?: string;
  headquarters?: string;
  ceo?: string;
  isFollowing: boolean;
  onFollow: () => void;
  onSetAlert: () => void;
}

// MetricCard - Single metric display
interface MetricCardProps {
  label: string;
  value: string | number;
  change?: number;
  changeLabel?: string;
  format?: 'currency' | 'percent' | 'number';
}

// FinancialStatements - Interactive financial tables
interface FinancialStatementsProps {
  companyId: string;
  statementType: 'income' | 'balance' | 'cashflow';
  periods: string[];
  onLineItemClick: (item: LineItem) => void;
}

// FilingList - List of SEC filings
interface FilingListProps {
  filings: Filing[];
  onFilingClick: (filing: Filing) => void;
  showLoadMore?: boolean;
  onLoadMore?: () => void;
}

// RelationshipGraph - Mini graph visualization
interface RelationshipGraphProps {
  centerId: string;
  depth?: number;
  width?: number;
  height?: number;
  onNodeClick: (node: GraphNode) => void;
  onExploreMore: () => void;
}

// CompetitorTable - Side-by-side comparison
interface CompetitorTableProps {
  companies: CompanyComparison[];
  metrics: string[];
  onCompanyClick: (ticker: string) => void;
}

// IndustryNewsFeed - Related news from same industry
interface IndustryNewsFeedProps {
  companyId: string;
  industry: string;
  limit?: number;
  onNewsClick: (news: NewsItem) => void;
}
```

### Sector/Industry Components

```typescript
// SectorCard - Clickable sector overview
interface SectorCardProps {
  name: string;
  companyCount: number;
  monthToDateReturn: number;
  topCompany: { ticker: string; name: string };
  onClick: () => void;
}

// IndustryTable - Tabular view of industries
interface IndustryTableProps {
  industries: Industry[];
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
  onSort: (column: string) => void;
  onIndustryClick: (industry: Industry) => void;
}

// SectorTreemap - Visual hierarchy
interface SectorTreemapProps {
  data: SectorData[];
  metric: 'marketCap' | 'companyCount' | 'return';
  onSectorClick: (sector: string) => void;
}
```

### Query Components

```typescript
// QueryBuilder - Visual query construction
interface QueryBuilderProps {
  onExecute: (query: StructuredQuery) => void;
  savedQueries?: SavedQuery[];
  onSaveQuery: (query: StructuredQuery, name: string) => void;
}

// NaturalLanguageInput - AI-powered query input
interface NaturalLanguageInputProps {
  onQuery: (query: string) => void;
  suggestions?: string[];
  isProcessing?: boolean;
}

// QueryResultsTable - Paginated results
interface QueryResultsTableProps {
  results: QueryResult[];
  columns: ColumnDef[];
  totalCount: number;
  page: number;
  pageSize: number;
  onPageChange: (page: number) => void;
  onRowClick: (row: QueryResult) => void;
  onExport: (format: 'csv' | 'json' | 'xlsx') => void;
}
```

---

## 5. API Endpoints

### Feed API

```yaml
# Feed Endpoints
GET /api/v1/feed
  description: Get personalized feed items
  params:
    - types: filing,relationship,company,alert (comma-separated)
    - sectors: technology,healthcare (comma-separated)
    - form_types: 10-K,10-Q,8-K (comma-separated)
    - since: ISO datetime
    - limit: int (default 20)
    - cursor: string (pagination)
  response:
    items: FeedItem[]
    next_cursor: string
    has_more: boolean

POST /api/v1/feed/items/{id}/like
  description: Like a feed item

POST /api/v1/feed/items/{id}/save
  description: Save a feed item to bookmarks

GET /api/v1/feed/trending
  description: Get trending tickers and topics
  response:
    trending_tickers: Ticker[]
    trending_topics: Topic[]
    hot_filings: Filing[]
```

### Company API

```yaml
# Company Endpoints
GET /api/v1/companies/{ticker}
  description: Get company profile
  response:
    ticker: string
    name: string
    cik: string
    sector: string
    industry: string
    metrics: CompanyMetrics
    recent_filings: Filing[]
    relationships: Relationship[]
    segments: RevenueSegment[]

GET /api/v1/companies/{ticker}/financials
  description: Get financial statements
  params:
    - statement: income|balance|cashflow
    - periods: 4 (number of periods)
    - frequency: annual|quarterly
  response:
    statement_type: string
    periods: Period[]
    line_items: LineItem[]

GET /api/v1/companies/{ticker}/relationships
  description: Get entity relationships
  params:
    - types: supplies_to,subsidiary_of (comma-separated)
    - depth: int (default 1)
  response:
    nodes: GraphNode[]
    edges: GraphEdge[]

GET /api/v1/companies/{ticker}/competitors
  description: Get competitors in same industry
  params:
    - limit: int (default 10)
    - metrics: revenue,pe_ratio,market_cap (comma-separated)
  response:
    competitors: CompanyComparison[]

GET /api/v1/companies/{ticker}/news
  description: Get industry/related news
  params:
    - limit: int (default 20)
    - include_competitors: boolean
    - include_suppliers: boolean
  response:
    news: NewsItem[]
```

### Sector/Industry API

```yaml
# Sector Endpoints
GET /api/v1/sectors
  description: Get all sectors with summary stats
  response:
    sectors: SectorSummary[]

GET /api/v1/sectors/{sector}
  description: Get sector detail with industries
  response:
    name: string
    company_count: int
    industries: Industry[]
    top_companies: Company[]
    performance: SectorPerformance

GET /api/v1/sectors/{sector}/industries/{industry}
  description: Get industry detail with companies
  params:
    - sort_by: market_cap|revenue|pe_ratio
    - sort_order: asc|desc
    - limit: int
    - offset: int
  response:
    name: string
    company_count: int
    companies: Company[]
    metrics: IndustryMetrics
```

### Query API

```yaml
# Query Endpoints
POST /api/v1/query/natural
  description: Execute natural language query
  body:
    query: string
  response:
    parsed_query: StructuredQuery
    results: QueryResult[]
    total_count: int

POST /api/v1/query/structured
  description: Execute structured query
  body:
    filters: Filter[]
    sort_by: string
    sort_order: asc|desc
    limit: int
    offset: int
  response:
    results: QueryResult[]
    total_count: int

GET /api/v1/query/suggestions
  description: Get query suggestions
  params:
    - partial: string (partial query)
  response:
    suggestions: string[]

POST /api/v1/query/save
  description: Save a query
  body:
    name: string
    query: StructuredQuery
    
GET /api/v1/query/saved
  description: Get saved queries
  response:
    queries: SavedQuery[]
```

### Watchlist/Follow API

```yaml
# Follow Endpoints
POST /api/v1/follow/companies/{ticker}
  description: Follow a company

DELETE /api/v1/follow/companies/{ticker}
  description: Unfollow a company

GET /api/v1/follow/companies
  description: Get followed companies
  response:
    companies: FollowedCompany[]

POST /api/v1/follow/sectors/{sector}
  description: Follow a sector

GET /api/v1/follow/feed
  description: Get feed from followed entities only
```

---

## 6. Database Schema

### New Tables for Social Feed

```sql
-- ============================================
-- SOCIAL FEED TABLES
-- ============================================

-- Feed Items (all types of feed content)
CREATE TABLE feed_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Item type and source
    item_type VARCHAR(50) NOT NULL,  -- 'filing', 'relationship', 'company', 'insight', 'alert'
    source_type VARCHAR(50),          -- 'sec_filing', 'knowledge_graph', 'ai_generated', 'user'
    source_id UUID,                   -- Reference to source entity
    
    -- Content
    title TEXT NOT NULL,
    summary TEXT,
    content JSONB,                    -- Type-specific structured content
    
    -- Metadata
    published_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    
    -- Engagement metrics
    like_count INTEGER DEFAULT 0,
    comment_count INTEGER DEFAULT 0,
    save_count INTEGER DEFAULT 0,
    share_count INTEGER DEFAULT 0,
    view_count INTEGER DEFAULT 0,
    
    -- Associations
    tickers TEXT[],                   -- Related tickers
    sectors TEXT[],                   -- Related sectors
    entity_ids UUID[],                -- Related entity IDs
    
    -- Search
    search_vector TSVECTOR,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_feed_items_published ON feed_items(published_at DESC);
CREATE INDEX idx_feed_items_type ON feed_items(item_type);
CREATE INDEX idx_feed_items_tickers ON feed_items USING GIN(tickers);
CREATE INDEX idx_feed_items_sectors ON feed_items USING GIN(sectors);
CREATE INDEX idx_feed_items_search ON feed_items USING GIN(search_vector);

-- User Feed Interactions
CREATE TABLE feed_interactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    feed_item_id UUID NOT NULL REFERENCES feed_items(id),
    
    interaction_type VARCHAR(20) NOT NULL,  -- 'like', 'save', 'share', 'hide', 'report'
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(user_id, feed_item_id, interaction_type)
);

CREATE INDEX idx_feed_interactions_user ON feed_interactions(user_id);
CREATE INDEX idx_feed_interactions_item ON feed_interactions(feed_item_id);

-- Feed Comments
CREATE TABLE feed_comments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    feed_item_id UUID NOT NULL REFERENCES feed_items(id),
    user_id UUID NOT NULL REFERENCES users(id),
    parent_comment_id UUID REFERENCES feed_comments(id),
    
    content TEXT NOT NULL,
    
    like_count INTEGER DEFAULT 0,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_feed_comments_item ON feed_comments(feed_item_id);
CREATE INDEX idx_feed_comments_user ON feed_comments(user_id);

-- User Follows (companies, sectors, users)
CREATE TABLE user_follows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    
    follow_type VARCHAR(20) NOT NULL,  -- 'company', 'sector', 'industry', 'user', 'relationship_type'
    follow_id VARCHAR(100) NOT NULL,   -- ticker, sector name, user_id, etc.
    
    -- Notification preferences for this follow
    notify_filings BOOLEAN DEFAULT TRUE,
    notify_relationships BOOLEAN DEFAULT TRUE,
    notify_price_changes BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(user_id, follow_type, follow_id)
);

CREATE INDEX idx_user_follows_user ON user_follows(user_id);
CREATE INDEX idx_user_follows_type ON user_follows(follow_type, follow_id);

-- Saved Queries
CREATE TABLE saved_queries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    
    name VARCHAR(200) NOT NULL,
    description TEXT,
    
    -- Query definition
    query_type VARCHAR(20) NOT NULL,  -- 'natural', 'structured'
    natural_query TEXT,
    structured_query JSONB,
    
    -- Usage tracking
    run_count INTEGER DEFAULT 0,
    last_run_at TIMESTAMPTZ,
    
    -- Scheduling (optional)
    schedule_cron VARCHAR(100),
    notify_on_new_results BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_saved_queries_user ON saved_queries(user_id);

-- Trending Topics (computed/cached)
CREATE TABLE trending_topics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    topic_type VARCHAR(20) NOT NULL,  -- 'ticker', 'sector', 'keyword', 'relationship'
    topic_value VARCHAR(200) NOT NULL,
    
    -- Trending metrics
    mention_count INTEGER DEFAULT 0,
    engagement_score DECIMAL(10, 2) DEFAULT 0,
    velocity DECIMAL(10, 2) DEFAULT 0,  -- Rate of increase
    
    -- Time window
    window_start TIMESTAMPTZ NOT NULL,
    window_end TIMESTAMPTZ NOT NULL,
    
    rank INTEGER,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_trending_topics_type ON trending_topics(topic_type);
CREATE INDEX idx_trending_topics_window ON trending_topics(window_start, window_end);

-- ============================================
-- COMPANY PROFILE ENHANCEMENTS
-- ============================================

-- Revenue Segments
CREATE TABLE company_segments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id),
    filing_id UUID REFERENCES filings(id),
    
    segment_type VARCHAR(50) NOT NULL,  -- 'product', 'geographic', 'customer'
    segment_name VARCHAR(200) NOT NULL,
    
    -- Financials
    revenue DECIMAL(20, 2),
    revenue_percent DECIMAL(5, 2),
    operating_income DECIMAL(20, 2),
    
    -- Period
    fiscal_year INTEGER NOT NULL,
    fiscal_quarter INTEGER,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_company_segments_company ON company_segments(company_id);
CREATE INDEX idx_company_segments_period ON company_segments(fiscal_year, fiscal_quarter);

-- Company Metrics (cached/computed)
CREATE TABLE company_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id),
    
    metric_name VARCHAR(100) NOT NULL,
    metric_value DECIMAL(20, 4),
    metric_unit VARCHAR(20),
    
    -- Comparison
    previous_value DECIMAL(20, 4),
    change_percent DECIMAL(10, 4),
    
    -- Period
    as_of_date DATE NOT NULL,
    
    -- Source
    source VARCHAR(50),  -- 'calculated', 'sec_filing', 'external'
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(company_id, metric_name, as_of_date)
);

CREATE INDEX idx_company_metrics_company ON company_metrics(company_id);
CREATE INDEX idx_company_metrics_name ON company_metrics(metric_name);

-- Industry Benchmarks
CREATE TABLE industry_benchmarks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    sector VARCHAR(100) NOT NULL,
    industry VARCHAR(100) NOT NULL,
    
    metric_name VARCHAR(100) NOT NULL,
    
    -- Statistics
    median_value DECIMAL(20, 4),
    mean_value DECIMAL(20, 4),
    percentile_25 DECIMAL(20, 4),
    percentile_75 DECIMAL(20, 4),
    min_value DECIMAL(20, 4),
    max_value DECIMAL(20, 4),
    
    company_count INTEGER,
    
    -- Period
    as_of_date DATE NOT NULL,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(sector, industry, metric_name, as_of_date)
);

CREATE INDEX idx_industry_benchmarks_lookup ON industry_benchmarks(sector, industry);
```

### Feed Item Generation Triggers

```sql
-- Auto-generate feed items when new filings are added
CREATE OR REPLACE FUNCTION generate_filing_feed_item()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO feed_items (
        item_type,
        source_type,
        source_id,
        title,
        summary,
        content,
        published_at,
        tickers,
        sectors
    )
    SELECT
        'filing',
        'sec_filing',
        NEW.id,
        c.ticker || ' filed ' || NEW.form_type,
        'New ' || NEW.form_type || ' filing from ' || c.name,
        jsonb_build_object(
            'filing_id', NEW.id,
            'form_type', NEW.form_type,
            'accession_number', NEW.accession_number,
            'company_name', c.name,
            'ticker', c.ticker
        ),
        COALESCE(NEW.filed_date, NOW()),
        ARRAY[c.ticker],
        ARRAY[c.sector]
    FROM companies c
    WHERE c.id = NEW.company_id;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_filing_feed_item
    AFTER INSERT ON filings
    FOR EACH ROW
    EXECUTE FUNCTION generate_filing_feed_item();

-- Auto-generate feed items when new relationships are discovered
CREATE OR REPLACE FUNCTION generate_relationship_feed_item()
RETURNS TRIGGER AS $$
DECLARE
    source_name TEXT;
    target_name TEXT;
BEGIN
    -- Get entity names
    SELECT name INTO source_name FROM entities WHERE id = NEW.source_entity_id;
    SELECT name INTO target_name FROM entities WHERE id = NEW.target_entity_id;
    
    INSERT INTO feed_items (
        item_type,
        source_type,
        source_id,
        title,
        summary,
        content,
        published_at,
        entity_ids
    )
    VALUES (
        'relationship',
        'knowledge_graph',
        NEW.id,
        'New Relationship: ' || source_name || ' → ' || target_name,
        source_name || ' ' || NEW.relationship_type || ' ' || target_name,
        jsonb_build_object(
            'relationship_id', NEW.id,
            'relationship_type', NEW.relationship_type,
            'source_entity_id', NEW.source_entity_id,
            'source_entity_name', source_name,
            'target_entity_id', NEW.target_entity_id,
            'target_entity_name', target_name,
            'confidence', NEW.confidence
        ),
        NOW(),
        ARRAY[NEW.source_entity_id, NEW.target_entity_id]
    );
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_relationship_feed_item
    AFTER INSERT ON relationships
    FOR EACH ROW
    EXECUTE FUNCTION generate_relationship_feed_item();
```

---

## 7. Implementation Phases

### Phase 1: Foundation (Weeks 1-2)
**Goal**: Basic feed and company profile

#### Backend Tasks
- [ ] Create feed_items table and API endpoints
- [ ] Implement filing feed item generation trigger
- [ ] Create company profile API with basic metrics
- [ ] Add sector/industry lookup endpoints

#### Frontend Tasks
- [ ] Create FeedCard component and variants
- [ ] Build Feed page with infinite scroll
- [ ] Create CompanyProfile page with header
- [ ] Implement ticker click navigation

#### Tests
- [ ] Unit: Feed item generation logic
- [ ] Integration: Feed API pagination
- [ ] E2E: Navigate from feed card to company profile

### Phase 2: Engagement (Weeks 3-4)
**Goal**: Social interactions and personalization

#### Backend Tasks
- [ ] Implement like/save/comment APIs
- [ ] Create user_follows table and APIs
- [ ] Build personalized feed algorithm
- [ ] Add trending topics computation

#### Frontend Tasks
- [ ] Add like/save/share buttons to cards
- [ ] Create follow button on company profiles
- [ ] Build "For You" vs "Following" feed tabs
- [ ] Add trending sidebar

#### Tests
- [ ] Unit: Follow/unfollow state management
- [ ] Integration: Personalized feed filtering
- [ ] E2E: Follow company, see in feed

### Phase 3: Discovery (Weeks 5-6)
**Goal**: Sector explorer and search

#### Backend Tasks
- [ ] Create sector/industry aggregation APIs
- [ ] Implement company search with filters
- [ ] Build query builder API
- [ ] Add natural language query processing

#### Frontend Tasks
- [ ] Create SectorExplorer page with cards
- [ ] Build industry drill-down views
- [ ] Create UniversalQuery page
- [ ] Implement QueryBuilder component

#### Tests
- [ ] Unit: Query filter logic
- [ ] Integration: Sector aggregation accuracy
- [ ] E2E: Search → filter → click result → company profile

### Phase 4: Financial Deep Dive (Weeks 7-8)
**Goal**: Financial statements and segments

#### Backend Tasks
- [ ] Parse financial statements from filings
- [ ] Create company_segments table and APIs
- [ ] Build competitor comparison API
- [ ] Implement industry benchmarks

#### Frontend Tasks
- [ ] Create FinancialStatements component
- [ ] Build revenue segment charts
- [ ] Add competitor comparison table
- [ ] Show industry benchmarks on metrics

#### Tests
- [ ] Unit: Financial calculation accuracy
- [ ] Integration: Segment data consistency
- [ ] E2E: View financial statements, compare competitors

### Phase 5: Knowledge Graph (Weeks 9-10)
**Goal**: Relationship visualization

#### Backend Tasks
- [ ] Implement relationship feed generation
- [ ] Create graph traversal API
- [ ] Build relationship search endpoint
- [ ] Add "find path between" algorithm

#### Frontend Tasks
- [ ] Create RelationshipCard component
- [ ] Build 2D/3D graph visualization
- [ ] Add relationship explorer page
- [ ] Implement entity detail sidebar

#### Tests
- [ ] Unit: Graph traversal correctness
- [ ] Integration: Relationship discovery
- [ ] E2E: Click relationship → explore graph → navigate to entity

### Phase 6: Advanced Features (Weeks 11-12)
**Goal**: Saved queries, alerts, AI insights

#### Backend Tasks
- [ ] Implement saved queries with scheduling
- [ ] Create alert automation system
- [ ] Build AI insight generation pipeline
- [ ] Add export functionality

#### Frontend Tasks
- [ ] Create saved query management UI
- [ ] Build alert configuration modal
- [ ] Add AI insight cards to feed
- [ ] Implement export buttons

#### Tests
- [ ] Unit: Alert condition evaluation
- [ ] Integration: Scheduled query execution
- [ ] E2E: Save query → schedule → receive results

---

## 8. Testing Strategy

### 8.1 Backend Tests

```
entityspine/backend/tests/
├── unit/
│   ├── test_feed_generation.py      # Feed item creation logic
│   ├── test_query_parser.py         # Natural language parsing
│   ├── test_financial_calc.py       # Metric calculations
│   ├── test_graph_traversal.py      # Relationship graph algorithms
│   └── test_trending_algorithm.py   # Trending computation
│
├── integration/
│   ├── test_feed_api.py             # Feed endpoint tests
│   ├── test_company_api.py          # Company profile tests
│   ├── test_sector_api.py           # Sector/industry tests
│   ├── test_query_api.py            # Query builder tests
│   ├── test_follow_api.py           # Follow/unfollow tests
│   └── test_interaction_api.py      # Like/save/comment tests
│
└── e2e/
    ├── test_feed_workflow.py        # Full feed user journey
    ├── test_company_workflow.py     # Company profile journey
    └── test_search_workflow.py      # Search to results journey
```

### 8.2 Frontend Tests

```
capture-spine-basic/frontend/tests/
├── unit/
│   ├── components/
│   │   ├── FeedCard.test.tsx
│   │   ├── CompanyHeader.test.tsx
│   │   ├── FinancialTable.test.tsx
│   │   ├── QueryBuilder.test.tsx
│   │   └── RelationshipGraph.test.tsx
│   │
│   └── hooks/
│       ├── useFeed.test.ts
│       ├── useCompany.test.ts
│       ├── useFollow.test.ts
│       └── useQuery.test.ts
│
├── integration/
│   ├── FeedPage.test.tsx
│   ├── CompanyProfilePage.test.tsx
│   ├── SectorExplorerPage.test.tsx
│   └── QueryPage.test.tsx
│
└── e2e/  (Playwright)
    ├── feed.spec.ts
    ├── company-profile.spec.ts
    ├── sector-explorer.spec.ts
    ├── universal-query.spec.ts
    └── relationship-explorer.spec.ts
```

### 8.3 Playwright E2E Tests

```typescript
// e2e/feed.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Feed Page', () => {
  test('should load feed items', async ({ page }) => {
    await page.goto('/feed');
    await expect(page.locator('[data-testid="feed-card"]')).toHaveCount(20);
  });

  test('should filter by form type', async ({ page }) => {
    await page.goto('/feed');
    await page.click('[data-testid="filter-10k"]');
    
    const cards = page.locator('[data-testid="feed-card"]');
    for (const card of await cards.all()) {
      await expect(card).toContainText('10-K');
    }
  });

  test('should navigate to company profile on ticker click', async ({ page }) => {
    await page.goto('/feed');
    await page.click('[data-testid="ticker-link-AAPL"]');
    
    await expect(page).toHaveURL('/company/AAPL');
    await expect(page.locator('[data-testid="company-header"]')).toContainText('Apple');
  });

  test('should like a feed item', async ({ page }) => {
    await page.goto('/feed');
    
    const likeButton = page.locator('[data-testid="like-button"]').first();
    const likeCount = page.locator('[data-testid="like-count"]').first();
    
    const initialCount = parseInt(await likeCount.textContent() || '0');
    await likeButton.click();
    
    await expect(likeCount).toHaveText((initialCount + 1).toString());
  });

  test('should infinite scroll for more items', async ({ page }) => {
    await page.goto('/feed');
    
    const initialCards = await page.locator('[data-testid="feed-card"]').count();
    
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await page.waitForLoadState('networkidle');
    
    const newCards = await page.locator('[data-testid="feed-card"]').count();
    expect(newCards).toBeGreaterThan(initialCards);
  });
});

// e2e/company-profile.spec.ts
test.describe('Company Profile', () => {
  test('should display company overview', async ({ page }) => {
    await page.goto('/company/TSLA');
    
    await expect(page.locator('[data-testid="company-name"]')).toContainText('Tesla');
    await expect(page.locator('[data-testid="company-ticker"]')).toContainText('TSLA');
    await expect(page.locator('[data-testid="company-sector"]')).toBeVisible();
  });

  test('should show financial statements', async ({ page }) => {
    await page.goto('/company/TSLA');
    await page.click('[data-testid="tab-financials"]');
    
    await expect(page.locator('[data-testid="income-statement"]')).toBeVisible();
    await expect(page.locator('[data-testid="revenue-row"]')).toBeVisible();
  });

  test('should navigate to related companies', async ({ page }) => {
    await page.goto('/company/TSLA');
    await page.click('[data-testid="competitor-RIVN"]');
    
    await expect(page).toHaveURL('/company/RIVN');
  });

  test('should follow/unfollow company', async ({ page }) => {
    await page.goto('/company/TSLA');
    
    const followButton = page.locator('[data-testid="follow-button"]');
    await expect(followButton).toHaveText('Follow');
    
    await followButton.click();
    await expect(followButton).toHaveText('Following');
    
    await followButton.click();
    await expect(followButton).toHaveText('Follow');
  });
});

// e2e/universal-query.spec.ts
test.describe('Universal Query', () => {
  test('should execute natural language query', async ({ page }) => {
    await page.goto('/query');
    
    await page.fill('[data-testid="nl-query-input"]', 
      'technology companies with revenue over 10 billion');
    await page.click('[data-testid="execute-query"]');
    
    await expect(page.locator('[data-testid="results-table"]')).toBeVisible();
    await expect(page.locator('[data-testid="result-row"]')).toHaveCount(10);
  });

  test('should build structured query', async ({ page }) => {
    await page.goto('/query');
    await page.click('[data-testid="structured-query-tab"]');
    
    await page.selectOption('[data-testid="filter-field-0"]', 'sector');
    await page.selectOption('[data-testid="filter-op-0"]', '=');
    await page.selectOption('[data-testid="filter-value-0"]', 'Technology');
    
    await page.click('[data-testid="add-filter"]');
    
    await page.selectOption('[data-testid="filter-field-1"]', 'revenue');
    await page.selectOption('[data-testid="filter-op-1"]', '>');
    await page.fill('[data-testid="filter-value-1"]', '10000000000');
    
    await page.click('[data-testid="execute-query"]');
    
    await expect(page.locator('[data-testid="results-count"]')).toContainText('companies');
  });

  test('should save and rerun query', async ({ page }) => {
    await page.goto('/query');
    
    await page.fill('[data-testid="nl-query-input"]', 'tech companies');
    await page.click('[data-testid="execute-query"]');
    
    await page.click('[data-testid="save-query"]');
    await page.fill('[data-testid="query-name-input"]', 'My Tech Query');
    await page.click('[data-testid="confirm-save"]');
    
    await page.goto('/query');
    await page.click('[data-testid="saved-queries-tab"]');
    
    await expect(page.locator('text=My Tech Query')).toBeVisible();
  });
});
```

---

## 9. File Structure

### Backend Structure

```
entityspine/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   │
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── __init__.py
│   │   │       ├── router.py
│   │   │       └── endpoints/
│   │   │           ├── __init__.py
│   │   │           ├── feed.py              # Feed endpoints
│   │   │           ├── companies.py         # Company profile endpoints
│   │   │           ├── sectors.py           # Sector/industry endpoints
│   │   │           ├── query.py             # Universal query endpoints
│   │   │           ├── relationships.py     # Knowledge graph endpoints
│   │   │           ├── follows.py           # Follow/unfollow endpoints
│   │   │           └── interactions.py      # Like/save/comment endpoints
│   │   │
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── feed.py                      # FeedItem, FeedInteraction models
│   │   │   ├── company.py                   # Company, CompanyMetric models
│   │   │   ├── sector.py                    # Sector, Industry models
│   │   │   ├── relationship.py              # Entity, Relationship models
│   │   │   ├── follow.py                    # UserFollow model
│   │   │   └── query.py                     # SavedQuery model
│   │   │
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── feed.py                      # FeedItem schemas
│   │   │   ├── company.py                   # Company schemas
│   │   │   ├── sector.py                    # Sector schemas
│   │   │   ├── relationship.py              # Relationship schemas
│   │   │   └── query.py                     # Query schemas
│   │   │
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── feed_service.py              # Feed generation & retrieval
│   │   │   ├── company_service.py           # Company data aggregation
│   │   │   ├── sector_service.py            # Sector/industry analytics
│   │   │   ├── query_service.py             # Query parsing & execution
│   │   │   ├── graph_service.py             # Knowledge graph traversal
│   │   │   └── trending_service.py          # Trending computation
│   │   │
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   └── logging.py
│   │   │
│   │   └── db/
│   │       ├── __init__.py
│   │       └── session.py
│   │
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   │
│   │   ├── unit/
│   │   │   ├── __init__.py
│   │   │   ├── test_feed_generation.py
│   │   │   ├── test_query_parser.py
│   │   │   ├── test_financial_calc.py
│   │   │   └── test_graph_traversal.py
│   │   │
│   │   ├── integration/
│   │   │   ├── __init__.py
│   │   │   ├── test_feed_api.py
│   │   │   ├── test_company_api.py
│   │   │   ├── test_sector_api.py
│   │   │   └── test_query_api.py
│   │   │
│   │   └── e2e/
│   │       ├── __init__.py
│   │       └── test_workflows.py
│   │
│   ├── alembic/
│   │   └── versions/
│   │       ├── 001_initial_schema.py
│   │       ├── 002_feed_tables.py
│   │       └── 003_social_features.py
│   │
│   └── requirements.txt
│
├── db/
│   └── schema.sql
│
└── docs/
    ├── API_OVERVIEW.md
    ├── SOCIAL_FEED_VISION.md          # This document
    ├── FEED_API.md
    ├── COMPANY_API.md
    └── QUERY_API.md
```

### Frontend Structure

```
capture-spine-basic/frontend/
├── src/
│   ├── App.tsx
│   ├── main.tsx
│   │
│   ├── pages/
│   │   ├── FeedPage.tsx                 # Instagram-style feed
│   │   ├── CompanyProfilePage.tsx       # Bloomberg-style company page
│   │   ├── SectorExplorerPage.tsx       # Sector/industry browser
│   │   ├── UniversalQueryPage.tsx       # Query builder
│   │   ├── RelationshipExplorerPage.tsx # Knowledge graph explorer
│   │   ├── FilingDetailPage.tsx         # Individual filing view
│   │   └── SavedQueriesPage.tsx         # Manage saved queries
│   │
│   ├── components/
│   │   ├── feed/
│   │   │   ├── FeedCard.tsx             # Base feed card
│   │   │   ├── FilingCard.tsx           # SEC filing card
│   │   │   ├── RelationshipCard.tsx     # Relationship discovery card
│   │   │   ├── CompanyCard.tsx          # New company card
│   │   │   ├── InsightCard.tsx          # AI insight card
│   │   │   ├── FeedFilters.tsx          # Filter sidebar
│   │   │   ├── TrendingSidebar.tsx      # Trending tickers/topics
│   │   │   └── FeedActions.tsx          # Like/save/share buttons
│   │   │
│   │   ├── company/
│   │   │   ├── CompanyHeader.tsx        # Company overview header
│   │   │   ├── MetricCard.tsx           # Single metric display
│   │   │   ├── MetricGrid.tsx           # Grid of metrics
│   │   │   ├── FinancialStatements.tsx  # Interactive financials
│   │   │   ├── FilingList.tsx           # Recent filings
│   │   │   ├── RevenueSegments.tsx      # Segment breakdown
│   │   │   ├── CompetitorTable.tsx      # Competitor comparison
│   │   │   ├── RelationshipMini.tsx     # Mini relationship graph
│   │   │   └── IndustryNewsFeed.tsx     # Related news
│   │   │
│   │   ├── sector/
│   │   │   ├── SectorCard.tsx           # Sector overview card
│   │   │   ├── SectorGrid.tsx           # Grid of sectors
│   │   │   ├── IndustryTable.tsx        # Industry list table
│   │   │   ├── SectorTreemap.tsx        # Visual hierarchy
│   │   │   └── CompanyTable.tsx         # Companies in industry
│   │   │
│   │   ├── query/
│   │   │   ├── QueryBuilder.tsx         # Structured query UI
│   │   │   ├── NaturalLanguageInput.tsx # AI query input
│   │   │   ├── FilterRow.tsx            # Single filter row
│   │   │   ├── QueryResults.tsx         # Results table
│   │   │   └── SavedQueryList.tsx       # Saved queries
│   │   │
│   │   ├── graph/
│   │   │   ├── RelationshipGraph2D.tsx  # 2D graph view
│   │   │   ├── RelationshipGraph3D.tsx  # 3D graph view
│   │   │   ├── EntityNode.tsx           # Node component
│   │   │   ├── RelationshipEdge.tsx     # Edge component
│   │   │   └── GraphControls.tsx        # Zoom/pan/filter
│   │   │
│   │   └── common/
│   │       ├── TickerLink.tsx           # Clickable ticker
│   │       ├── FollowButton.tsx         # Follow/unfollow
│   │       ├── AlertButton.tsx          # Set alert
│   │       ├── InfiniteScroll.tsx       # Infinite scroll wrapper
│   │       └── DataTable.tsx            # Reusable table
│   │
│   ├── hooks/
│   │   ├── useFeed.ts                   # Feed data & mutations
│   │   ├── useCompany.ts                # Company profile data
│   │   ├── useSectors.ts                # Sector/industry data
│   │   ├── useQuery.ts                  # Query execution
│   │   ├── useFollow.ts                 # Follow state
│   │   ├── useInteractions.ts           # Like/save/comment
│   │   └── useGraph.ts                  # Graph data
│   │
│   ├── services/
│   │   ├── api.ts                       # Axios instance
│   │   ├── feedService.ts               # Feed API calls
│   │   ├── companyService.ts            # Company API calls
│   │   ├── sectorService.ts             # Sector API calls
│   │   ├── queryService.ts              # Query API calls
│   │   └── graphService.ts              # Graph API calls
│   │
│   ├── types/
│   │   ├── feed.ts                      # Feed types
│   │   ├── company.ts                   # Company types
│   │   ├── sector.ts                    # Sector types
│   │   ├── query.ts                     # Query types
│   │   └── graph.ts                     # Graph types
│   │
│   └── utils/
│       ├── formatters.ts                # Number/date formatting
│       ├── colors.ts                    # Sector/metric colors
│       └── navigation.ts                # Route helpers
│
├── tests/
│   ├── unit/
│   │   ├── components/
│   │   │   ├── FeedCard.test.tsx
│   │   │   ├── CompanyHeader.test.tsx
│   │   │   └── QueryBuilder.test.tsx
│   │   │
│   │   └── hooks/
│   │       ├── useFeed.test.ts
│   │       └── useCompany.test.ts
│   │
│   ├── integration/
│   │   ├── FeedPage.test.tsx
│   │   └── CompanyProfilePage.test.tsx
│   │
│   └── e2e/
│       ├── feed.spec.ts
│       ├── company-profile.spec.ts
│       ├── sector-explorer.spec.ts
│       └── universal-query.spec.ts
│
├── playwright.config.ts
├── vitest.config.ts
└── package.json
```

---

## Summary

This document outlines a comprehensive "Instagram for Financial Intelligence" feature set for EntitySpine, including:

1. **20 Features** across 4 tiers (Basic → Mindblowing)
2. **5 Core Pages**: Feed, Company Profile, Sector Explorer, Universal Query, Relationship Explorer
3. **Complete Component Library** with TypeScript interfaces
4. **Full API Specification** for all endpoints
5. **Database Schema** with triggers for automated feed generation
6. **6-Phase Implementation Plan** (12 weeks)
7. **Comprehensive Testing Strategy** (unit, integration, e2e with Playwright)
8. **Modular File Structure** for both backend and frontend

Each feature follows the click-through navigation pattern:
- **Ticker Click** → Company Profile
- **Sector Click** → Sector Detail → Industry → Company List
- **Relationship Click** → Graph Explorer → Entity Detail
- **Filing Click** → Filing Detail
- **Query Result Click** → Relevant Detail Page
