# Entity Master - Overview

**A comprehensive entity and relationship management system for financial data.**

---

## What is Entity Master?

Entity Master is a **standalone service** for managing financial data with proper separation of concerns:

- **Entities**: Companies, funds, people, government bodies (the issuer/organization)
- **Securities**: Financial instruments issued by entities (stocks, bonds, etc.)
- **Listings**: Trading identities (ticker+exchange+currency combinations)
- **Identifiers**: CIK, LEI, ISIN, FIGI, CUSIP, Ticker, PermID, RIC, DUNS
- **Relationships**: Suppliers, customers, competitors, executives, subsidiaries
- **Mentions**: References in filings, news, tweets, research reports
- **Events**: M&A, IPOs, delistings, name changes, bankruptcies

Think of it as a **Security Master on steroids** - not just identifiers, but the full knowledge graph of entity relationships, with proper Entity → Security → Listing hierarchy.

### Entity/Security/Listing Separation

A critical design principle - these are **three distinct concepts**:

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                          CANONICAL HIERARCHY                                         │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│   ENTITY (Issuer)            The legal organization                                 │
│   Alphabet Inc               CIK: 0001652044, LEI: 5493006MHB84DD0ZWV18             │
│       │                                                                              │
│       │  issues                                                                      │
│       ▼                                                                              │
│   SECURITY (Instrument)      What the entity issues                                 │
│   ├── Alphabet Class A       ISIN: US02079K3059, CUSIP: 02079K305                   │
│   └── Alphabet Class C       ISIN: US02079K1079, CUSIP: 02079K107                   │
│       │                                                                              │
│       │  trades as                                                                   │
│       ▼                                                                              │
│   LISTING (Trading Identity) Where/how security trades                              │
│   ├── GOOGL on NASDAQ        Ticker: GOOGL, MIC: XNAS, Currency: USD                │
│   ├── GOOG on NASDAQ         Ticker: GOOG, MIC: XNAS, Currency: USD                 │
│   └── ABEA on Frankfurt      Ticker: ABEA, MIC: XFRA, Currency: EUR                 │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

**Why this matters:**
- **Tickers can be reused** (GM before/after 2009 bankruptcy are different entities)
- **One entity can have multiple securities** (Alphabet has Class A and Class C shares)
- **One security can have multiple listings** (cross-listed on multiple exchanges)
- **Identifiers have scopes** (CIK identifies Entity, ISIN identifies Security, Ticker identifies Listing)

---

## Why Separate from py-sec-edgar?

| Concern | py-sec-edgar | Entity Master |
|---------|--------------|---------------|
| **Purpose** | Download & parse SEC filings | Manage entity knowledge |
| **Data Source** | SEC EDGAR only | SEC + GLEIF + OpenFIGI + news + social |
| **Update Frequency** | Real-time filings | Daily/weekly reference data |
| **Storage** | Filing content | Entity metadata & relationships |
| **Users** | Filing downloaders | Anyone needing entity resolution |

**Benefits of separation:**
1. Entity Master can serve multiple consumers (py-sec-edgar, trading systems, research tools)
2. Independent update cycles (entity data is more stable)
3. Cleaner architecture (separation of concerns)
4. Potential for separate package/deployment

---

## Core Capabilities

### 1. Universal Identifier Resolution

```python
# Any identifier → canonical entity (with proper scope)
entity = entity_master.resolve("AAPL")           # Ticker → Listing → Security → Entity
entity = entity_master.resolve("320193")         # CIK → Entity
entity = entity_master.resolve("HWUPKR0MPOU8FGXBT394")  # LEI → Entity
entity = entity_master.resolve("US0378331005")   # ISIN → Security → Entity

# Explicit scope resolution
security = entity_master.resolve("AAPL", scope="security")
listing = entity_master.resolve("AAPL", scope="listing", mic="XNAS")

# Point-in-time resolution (handles ticker reuse)
entity = entity_master.resolve("GM", as_of_date=date(2008, 1, 1))  # Old GM
entity = entity_master.resolve("GM", as_of_date=date(2015, 1, 1))  # New GM

# All return the same canonical Apple Inc entity
```

### 2. Relationship Queries

```python
# Who supplies to Apple?
suppliers = entity_master.relationships.get_suppliers("AAPL")

# Who are NVIDIA's competitors?
competitors = entity_master.relationships.get_competitors("NVDA")

# What companies did Tim Cook work for?
companies = entity_master.relationships.get_affiliations(person="Tim Cook")

# Show me the supply chain for Tesla
supply_chain = entity_master.graph.get_supply_chain("TSLA", depth=3)
```

### 3. Entity Enrichment

```python
# Enrich entity with external data
entity = entity_master.resolve("AAPL")
await entity_master.enrich(entity, sources=["gleif", "openfigi"])

# Now entity has:
# - LEI from GLEIF
# - FIGI from OpenFIGI
# - SIC code from SEC
# - Exchange info
```

### 4. Change Detection (via FeedSpine)

```python
# What new tickers were added this week?
new_entities = entity_master.changes.since(days=7, change_type="new")

# What companies changed their ticker?
ticker_changes = entity_master.changes.ticker_changes(since="2024-01-01")

# What entities were delisted?
delistings = entity_master.changes.delistings(since="2024-01-01")
```

### 5. Mention Tracking

```python
# Where is Apple mentioned?
mentions = entity_master.mentions.get("AAPL")

# Filter by source
filing_mentions = entity_master.mentions.get("AAPL", source="sec_filings")
news_mentions = entity_master.mentions.get("AAPL", source="news")

# Cross-entity mentions (Apple mentioned in TSMC's filings)
cross_mentions = entity_master.mentions.get(
    entity="AAPL", 
    in_entity="TSMC",
    relationship_type="supplier"
)
```

---

## Architecture Tiers

Entity Master supports **5 tiers** of deployment complexity:

| Tier | Name | Storage | Features | Use Case |
|------|------|---------|----------|----------|
| **1** | Basic | SQLite | Local lookups, manual updates | Personal projects |
| **2** | Intermediate | DuckDB | Analytics, scheduled updates | Small teams |
| **3** | Advanced | PostgreSQL + Elasticsearch | Full-text search, API | Production |
| **4** | Full | + Neo4j | Relationship graphs | Enterprise |
| **5** | Mind-blowing | + LLM + Real-time | AI-powered enrichment | Research |

Each tier builds on the previous - you can start at Tier 1 and scale up.

---

## Integration with py-sec-edgar

py-sec-edgar becomes a **consumer** of Entity Master:

```python
from py_sec_edgar import SEC
from entity_master import EntityMaster

# Initialize Entity Master (separate service)
em = EntityMaster(tier="basic")  # or "intermediate", "advanced", etc.

# py-sec-edgar uses it for resolution
async with SEC(entity_master=em) as sec:
    # Automatic entity resolution
    filings = await sec.filings.get("AAPL")  # Resolved via Entity Master
    
    # Access entity data
    entity = sec.resolve_entity("AAPL")
    print(entity.lei)   # From GLEIF
    print(entity.figi)  # From OpenFIGI
    
    # Get relationships extracted from filings
    suppliers = await sec.get_suppliers("AAPL")
```

---

## Integration with FeedSpine

FeedSpine manages the **data ingestion pipeline**:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          FEEDSPINE PIPELINE                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐                │
│  │ SEC Tickers │     │ GLEIF LEI   │     │ OpenFIGI    │                │
│  │ Feed        │     │ Feed        │     │ Feed        │                │
│  └──────┬──────┘     └──────┬──────┘     └──────┬──────┘                │
│         │                   │                   │                        │
│         └───────────────────┼───────────────────┘                        │
│                             │                                            │
│                             ▼                                            │
│                   ┌─────────────────┐                                    │
│                   │  Bronze Layer   │  Raw ingested data                 │
│                   │  (deduplicated) │  - capture_date tracking           │
│                   └────────┬────────┘  - natural_key dedup               │
│                            │                                             │
│                            ▼                                             │
│                   ┌─────────────────┐                                    │
│                   │  Silver Layer   │  Normalized entities               │
│                   │  (transformed)  │  - schema validation               │
│                   └────────┬────────┘  - cross-reference merge           │
│                            │                                             │
│                            ▼                                             │
│                   ┌─────────────────┐                                    │
│                   │  Gold Layer     │  Entity Master tables              │
│                   │  (enriched)     │  - canonical entities              │
│                   └─────────────────┘  - relationships                   │
│                                        - change history                  │
└─────────────────────────────────────────────────────────────────────────┘
```

### Feed Definitions

```python
# SEC Ticker Feed
class SECTickerFeed(FeedAdapter):
    """Daily SEC company_tickers_exchange.json feed."""
    
    feed_id = "sec-tickers"
    schedule = "0 6 * * *"  # Daily at 6 AM
    
    async def fetch(self) -> list[RecordCandidate]:
        data = await self.http.get("https://www.sec.gov/files/company_tickers_exchange.json")
        return [
            RecordCandidate(
                natural_key=f"cik:{row[0]}",
                published_at=datetime.now(UTC),
                content={
                    "cik": str(row[0]).zfill(10),
                    "name": row[1],
                    "ticker": row[2],
                    "exchange": row[3],
                },
                metadata=Metadata(source="sec-tickers"),
            )
            for row in data["data"]
        ]

# GLEIF LEI Feed (monthly bulk)
class GLEIFGoldenCopyFeed(FeedAdapter):
    """Monthly GLEIF Golden Copy bulk download."""
    
    feed_id = "gleif-lei"
    schedule = "0 0 1 * *"  # Monthly on 1st
    
    async def fetch(self) -> list[RecordCandidate]:
        # Download and parse GLEIF golden copy
        ...
```

### Change Detection

```python
# FeedSpine tracks sightings (when records were seen)
# This enables change detection:

async def detect_new_tickers(since: datetime) -> list[Entity]:
    """Find tickers added since a date."""
    query = Query(
        layer=Layer.BRONZE,
        feed_id="sec-tickers",
        first_seen_after=since,
    )
    new_records = await feedspine.query(query)
    return [record.content for record in new_records]

async def detect_delistings(since: datetime) -> list[Entity]:
    """Find tickers not seen in latest capture."""
    query = Query(
        layer=Layer.BRONZE,
        feed_id="sec-tickers",
        last_seen_before=since,
        not_seen_in_latest=True,
    )
    missing_records = await feedspine.query(query)
    return [record.content for record in missing_records]
```

---

## Entity Types Managed

| Type | Description | Example |
|------|-------------|---------|
| `COMPANY` | Public company | Apple Inc (CIK: 320193) |
| `PRIVATE_COMPANY` | Private company | Stripe Inc |
| `FUND` | Investment fund | Vanguard 500 Index Fund |
| `PERSON` | Individual | Tim Cook |
| `SECURITY` | Tradeable instrument | AAPL common stock |
| `GOVERNMENT` | Government entity | U.S. Treasury |
| `INDEX` | Market index | S&P 500 |
| `EXCHANGE` | Trading venue | NYSE |

---

## Relationship Types Managed

| Relationship | Description | Example |
|--------------|-------------|---------|
| `SUPPLIER_OF` | Supplies goods/services | TSMC → Apple |
| `CUSTOMER_OF` | Buys goods/services | Apple → TSMC |
| `COMPETITOR_OF` | Competes with | Apple ↔ Samsung |
| `SUBSIDIARY_OF` | Owned by | Apple UK → Apple Inc |
| `EXECUTIVE_OF` | Executive role | Tim Cook → Apple |
| `DIRECTOR_OF` | Board member | Al Gore → Apple |
| `INVESTOR_IN` | Holds stake | Berkshire → Apple |
| `ACQUIRED_BY` | M&A target | LinkedIn → Microsoft |
| `PARTNER_WITH` | Strategic partner | Apple ↔ IBM |
| `MENTIONED_IN` | Referenced in filing | NVIDIA → Apple 10-K |

---

## Documents in This Series

### Core Design
- **00_OVERVIEW.md** (this document) - What Entity Master is and why
- [01_TIERED_ARCHITECTURE.md](01_TIERED_ARCHITECTURE.md) - Deployment tier specifications
- [02_DATA_MODEL.md](02_DATA_MODEL.md) - **Canonical Entity/Security/Listing model**
- [03_FEEDSPINE_INTEGRATION.md](03_FEEDSPINE_INTEGRATION.md) - FeedSpine pipeline design
- [04_API_DESIGN.md](04_API_DESIGN.md) - Service API and SDK design

### Capabilities
- [05_ENRICHMENT_PIPELINE.md](05_ENRICHMENT_PIPELINE.md) - GLEIF, OpenFIGI, LLM enrichment
- [06_RELATIONSHIP_GRAPH.md](06_RELATIONSHIP_GRAPH.md) - Graph database and queries
- [07_QUICK_START.md](07_QUICK_START.md) - Getting started guide

### Integration & Extensions
- [08_INTEGRATION_EXTENSIONS.md](08_INTEGRATION_EXTENSIONS.md) - Extended APIs for py-sec-edgar integration
- [09_DESIGN_QUESTIONS.md](09_DESIGN_QUESTIONS.md) - Architecture decisions and open questions

### Canonical Model (New)
- [10_CROSSWALK_STRATEGY.md](10_CROSSWALK_STRATEGY.md) - **Vendor ID mapping** (Bloomberg, FactSet, Refinitiv, S&P, OpenFIGI)
- [11_RESOLUTION_STRATEGY.md](11_RESOLUTION_STRATEGY.md) - **Resolution paths, merge following, identifier ranking**
- [12_STORAGE_TIERS.md](12_STORAGE_TIERS.md) - **Tiered schema implementations** (SQLite → PostgreSQL → +ES+Neo4j)
- [13_PYSECEDGAR_PORT.md](13_PYSECEDGAR_PORT.md) - **EntityResolver Port interface** for py-sec-edgar

### Requirements Input
- [99_PYSECEDGAR_REQUIREMENTS_INPUT.md](99_PYSECEDGAR_REQUIREMENTS_INPUT.md) - Integration requirements from py-sec-edgar perspective

---

## Identifier Scoping

**Critical:** Different identifiers scope to different levels:

| Scope | Identifiers | What They Identify |
|-------|-------------|-------------------|
| **Entity** | CIK, LEI, DUNS, EIN, PermID Entity, FactSet Entity ID, S&P GVKEY | The legal organization |
| **Security** | ISIN, CUSIP, SEDOL, FIGI (Composite), FactSet Security ID | The financial instrument |
| **Listing** | Ticker, RIC, Bloomberg Ticker, Exchange FIGI, FactSet Listing ID | The trading venue identity |

See [02_DATA_MODEL.md](02_DATA_MODEL.md) for detailed identifier rules.

---

## Next Steps

See [09_DESIGN_QUESTIONS.md](09_DESIGN_QUESTIONS.md) for key architecture decisions that need to be made before implementation.
