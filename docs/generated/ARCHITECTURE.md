# ARCHITECTURE

**System Design and Structure**

> **Auto-generated from code annotations**  
> **Last Updated**: February 2026  
> **Status**: Living Document

---

## Table of Contents

1. [System Overview](#system-overview)

---

## System Overview

```
```
FeedSpine (SILVER layer) ──► FeedSpineAdapter ──► EntitySpine (Entities)
                                │
                                ├─ Extracts CIK, ticker, name
                                ├─ Checks for existing entity
                                └─ Creates/updates entity
```

Example:
    >>> adapter = FeedSpineAdapter(feedspine, entity_store)
    >>>
    >>> # Sync all SEC entities from FeedSpine
    >>> result = await adapter.sync_sec_entities()
    >>> print(f"Created {result.entities_created} entities")
    >>>
    >>> # Query FeedSpine records with entity resolution
    >>> async for record in adapter.iter_enriched_records("sec-tickers"):
    ...     print(f"{record['ticker']} → {record['entity_name']}")
```

*Source: [`FeedSpineAdapter`](/app/projects/entityspine/src/entityspine/adapters/feedspine_adapter.py#L78)*

```
```
    ┌──────────────────────────────────────────────────────────┐
    │            Claims-Based Identity Resolution              │
    └──────────────────────────────────────────────────────────┘
    
    Query: "Who is CIK 0000320193?"
    
    ┌─────────────────────────┐
    │    IdentifierClaim      │
    │  scheme: CIK            │
    │  value: "0000320193"    │
    │  entity_id: "01HQ..."   │──► Entity: Apple Inc.
    │  namespace: SEC         │
    │  confidence: 1.0        │
    │  valid_from: 1980       │
    │  valid_to: null         │
    └─────────────────────────┘
    
    Multi-Vendor Crosswalk (same entity, different sources):
    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
    │ Claim (SEC)  │  │Claim(FactSet)│  │Claim(Bloom.) │
    │ CIK: 320193  │  │ENTITY:000C7F │  │FIGI:BBG...   │
    │ conf: 1.0    │  │ conf: 0.95   │  │ conf: 0.98   │
    └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
           │                 │                 │
           └────────────┬────┴─────────────────┘
                        ▼
                ┌─────────────┐
                │   Entity    │ Apple Inc.
                └─────────────┘
    
    Scheme-Scope Enforcement:
    ┌─────────────────────────────────────────────┐
    │ CIK, LEI, EIN        → entity_id (required) │
    │ CUSIP, ISIN, SEDOL   → security_id          │
    │ TICKER               → listing_id           │
    └─────────────────────────────────────────────┘
    ```
    Dependencies: None - stdlib only (dataclasses, datetime)
    Storage Tier: T0 (JSON), T1 (SQLite), T2 (DuckDB), T3 (PostgreSQL)
```

*Source: [`IdentifierClaim`](/app/projects/entityspine/src/entityspine/domain/claim.py#L26)*

```
```
    ┌──────────────────────────────────────────────────────────┐
    │                  Entity Relationship Model                │
    └──────────────────────────────────────────────────────────┘
    
                       ┌─────────────┐
                       │   Entity    │◄──── IdentifierClaim (CIK, LEI, EIN)
                       │  (Apple)    │
                       └──────┬──────┘
                              │ issues
                              ▼
                       ┌─────────────┐
                       │  Security   │◄──── IdentifierClaim (CUSIP, ISIN)
                       │(AAPL Stock) │
                       └──────┬──────┘
                              │ listed_on
                              ▼
                       ┌─────────────┐
                       │   Listing   │◄──── IdentifierClaim (TICKER)
                       │(NASDAQ:AAPL)│
                       └─────────────┘
    
    Merged Entity Flow:
    ┌─────────┐        ┌─────────┐
    │Entity A │──────► │Entity B │  (A.redirect_to = B.entity_id)
    │(merged) │        │(active) │
    └─────────┘        └─────────┘
    ```
    Dependencies: None - stdlib only (dataclasses, datetime)
    Storage Tier: T0 (JSON), T1 (SQLite), T2 (DuckDB), T3 (PostgreSQL)
```

*Source: [`Entity`](/app/projects/entityspine/src/entityspine/domain/entity.py#L27)*

```
```
    ┌──────────────────────────────────────────────────────────┐
    │         Generic Relationship with NodeRef Pattern        │
    └──────────────────────────────────────────────────────────┘
    
    ┌─────────────┐                      ┌─────────────┐
    │   NodeRef   │─────Relationship────►│   NodeRef   │
    │  source_ref │  relationship_type   │  target_ref │
    │ kind + id   │  valid_from/to       │ kind + id   │
    └─────────────┘  evidence            └─────────────┘
    
    Example: Apple (entity) → Cupertino HQ (geo)
    ┌─────────────────┐                  ┌─────────────────┐
    │ NodeRef         │                  │ NodeRef         │
    │ kind: ENTITY    │   HEADQUARTER    │ kind: GEO       │
    │ id: "ent_apple" │────────────────► │ id: "geo_cup"   │
    └─────────────────┘                  └─────────────────┘
    
    Evidence Chain:
    ┌────────────────────────────────────────────────────────┐
    │ Relationship                                           │
    │ ├─ source_ref: entity:ent_apple                        │
    │ ├─ target_ref: geo:geo_cupertino                       │
    │ ├─ relationship_type: HEADQUARTER                      │
    │ ├─ valid_from: 1993-01-01                              │
    │ ├─ valid_to: null (current)                            │
    │ ├─ evidence_filing_id: 0001193125-23-272374            │
    │ ├─ evidence_snippet: "principal executive offices..."  │
    │ └─ confidence: 0.95                                    │
    └────────────────────────────────────────────────────────┘
    ```
    Dependencies: None - stdlib only (dataclasses, datetime)
    Storage Tier: T1 (SQLite), T2 (DuckDB), T3 (PostgreSQL)
```

*Source: [`Relationship`](/app/projects/entityspine/src/entityspine/domain/graph.py#L994)*

```
```
    ┌──────────────────────────────────────────────────────────┐
    │        Ticker Resolution: Historical Point-in-Time       │
    └──────────────────────────────────────────────────────────┘
    
    Query: resolve("FB", as_of=2021-06-01)
    
    ┌───────────────┐
    │   Listing     │ ticker="FB", mic="XNAS"
    │ start: 2012   │ start_date=2012-05-18
    │ end: 2022     │ end_date=2022-06-08
    └───────┬───────┘
            │ security_id
            ▼
    ┌───────────────┐
    │   Security    │ "Meta Class A Common Stock"
    └───────┬───────┘
            │ entity_id
            ▼
    ┌───────────────┐
    │    Entity     │ "Meta Platforms, Inc."
    └───────────────┘
    
    Same security, new listing:
    ┌───────────────┐
    │   Listing     │ ticker="META", mic="XNAS"
    │ start: 2022   │ start_date=2022-06-09
    │ end: null     │ end_date=None (active)
    └───────┬───────┘
            │ same security_id
            ▼
    ┌───────────────┐
    │   Security    │ (same as above)
    └───────────────┘
    ```
    Dependencies: None - stdlib only (dataclasses, datetime)
    Storage Tier: T0 (JSON), T1 (SQLite), T2 (DuckDB), T3 (PostgreSQL)
```

*Source: [`Listing`](/app/projects/entityspine/src/entityspine/domain/listing.py#L51)*

```
```
    ┌──────────────────────────────────────────────────────────┐
    │            Broker-Dealer in Market Structure             │
    └──────────────────────────────────────────────────────────┘
    
    Customer Order Flow:
    
    ┌────────────┐     ┌─────────────────┐     ┌──────────────┐
    │  Customer  │────►│  BrokerDealer   │────►│   Exchange   │
    │  (Retail)  │     │  (CRD: 12345)   │     │   (XNYS)     │
    └────────────┘     │                 │     └──────────────┘
                       │  Memberships:   │
                       │  ├─ NYSE (DMM)  │     ┌──────────────┐
                       │  ├─ NASDAQ      │────►│   Exchange   │
                       │  └─ CBOE        │     │   (XNAS)     │
                       └────────┬────────┘     └──────────────┘
                                │
                       Clearing │
                                ▼
                       ┌─────────────────┐
                       │  Clearinghouse  │
                       │    (NSCC)       │
                       └─────────────────┘
    
    Introducing vs Clearing Broker:
    ┌─────────────────┐     ┌─────────────────┐     ┌────────────┐
    │   Introducing   │────►│    Clearing     │────►│Clearinghouse│
    │   BD (front)    │     │    BD (back)    │     │   (DTCC)   │
    │   CRD: 54321    │     │   CRD: 12345    │     │            │
    └─────────────────┘     └─────────────────┘     └────────────┘
    ```
    Dependencies: validators.py (CRD normalization)
    Storage Tier: T0 (JSON), T1 (SQLite), T2 (DuckDB), T3 (PostgreSQL)
```

*Source: [`BrokerDealer`](/app/projects/entityspine/src/entityspine/domain/markets.py#L584)*

```
```
    ┌──────────────────────────────────────────────────────────┐
    │          Clearinghouse in the Settlement Chain           │
    └──────────────────────────────────────────────────────────┘
    
    Trade Execution → Clearing → Settlement
    
    ┌──────────┐  ┌──────────┐     ┌─────────────────┐     ┌──────────────┐
    │  Buyer   │  │  Seller  │     │    Exchange     │     │ Clearinghouse│
    │   BD     │  │   BD     │     │    (XNYS)       │     │   (NSCC)     │
    └────┬─────┘  └────┬─────┘     └────────┬────────┘     └──────┬───────┘
         │             │                    │                      │
         │    Trade Matched                 │                      │
         └─────────────┴────────────────────►                      │
                                            │   Trade Novation     │
                                            └──────────────────────►
                                                                   │
                                                       ┌───────────┴──────────┐
                                                       │      Netting         │
                                                       │  (reduce exposures)  │
                                                       └───────────┬──────────┘
                                                                   │
    ┌────────────────────────────────────────────────────────────────┐
    │                      DTCC Structure                             │
    │  ┌───────────┐    ┌───────────┐    ┌───────────┐              │
    │  │   NSCC    │    │    DTC    │    │   FICC    │              │
    │  │ (equities)│    │(depository)│   │  (fixed)  │              │
    │  └───────────┘    └───────────┘    └───────────┘              │
    └────────────────────────────────────────────────────────────────┘
    ```
    Dependencies: validators.py (SEC file number normalization)
    Storage Tier: T0 (JSON), T1 (SQLite), T2 (DuckDB), T3 (PostgreSQL)
```

*Source: [`Clearinghouse`](/app/projects/entityspine/src/entityspine/domain/markets.py#L1013)*

```
```
    ┌──────────────────────────────────────────────────────────┐
    │           Clearing Membership Graph Relationships        │
    └──────────────────────────────────────────────────────────┘
    
    Direct Clearing Member:
    ┌─────────────────┐                    ┌─────────────────┐
    │   BrokerDealer  │───────────────────►│  Clearinghouse  │
    │   (Goldman)     │ ClearingMembership │     (NSCC)      │
    │   CRD: 361      │    FULL_CLEARING   │                 │
    └─────────────────┘                    └─────────────────┘
    
    Correspondent Clearing (introducing → clearing BD → CCP):
    ┌─────────────────┐     ┌─────────────────┐     ┌──────────────┐
    │   Introducing   │────►│    Clearing     │────►│ Clearinghouse│
    │       BD        │corr.│       BD        │memb.│    (NSCC)    │
    └─────────────────┘     └─────────────────┘     └──────────────┘
    ```
    Dependencies: None (relationship model)
    Storage Tier: T1 (SQLite), T2 (DuckDB), T3 (PostgreSQL)
```

*Source: [`ClearingMembership`](/app/projects/entityspine/src/entityspine/domain/markets.py#L1254)*

```
```
    ┌──────────────────────────────────────────────────────────┐
    │         Exchange Membership - Trading Rights Graph       │
    └──────────────────────────────────────────────────────────┘
    
    ┌─────────────────┐                       ┌──────────────┐
    │   BrokerDealer  │                       │   Exchange   │
    │   (Citadel)     │                       │    (NYSE)    │
    │   CRD: 116797   │                       │   MIC: XNYS  │
    └────────┬────────┘                       └──────┬───────┘
             │                                       │
             │  ExchangeMembership                   │
             │  ┌────────────────────────────────┐   │
             └──┤ MPID: CDRG                     ├───┘
                │ type: TRADING_MEMBER           │
                │ is_designated_market_maker: ✓  │
                │ can_trade_equity: ✓            │
                │ can_trade_options: ✓           │
                │ status: ACTIVE                 │
                │ valid_from: 2004-01-01         │
                └────────────────────────────────┘
    
    Multi-Exchange Membership:
    ┌─────────────────┐     ┌──────────┐     ┌──────────┐
    │   BrokerDealer  │────►│   NYSE   │     │  NASDAQ  │
    │                 │     └──────────┘     └──────────┘
    │   memberships:  │────►│   CBOE   │     │  ARCA    │
    │    - XNYS (DMM) │     └──────────┘     └──────────┘
    │    - XNAS       │────►│   IEX    │
    │    - XCBO       │     └──────────┘
    └─────────────────┘
    ```
    Dependencies: validators.py (MPID normalization)
    Storage Tier: T1 (SQLite), T2 (DuckDB), T3 (PostgreSQL)
```

*Source: [`ExchangeMembership`](/app/projects/entityspine/src/entityspine/domain/markets.py#L1394)*

```
```
    ┌──────────────────────────────────────────────────────────┐
    │              Observation Time Semantics                   │
    └──────────────────────────────────────────────────────────┘
    
    Timeline: ──────────────────────────────────────────────►
              Jan 2025        Feb 2025        Mar 2025
    
    period (what):      ├── Q4 FY2025 ──┤
    
    as_of (when known):         ▲            ▲           ▲
                          guidance      revised     actual
                          2025-01-15   2025-02-01  2025-02-28
    
    captured_at:              ●             ●           ●
                         (ingested)    (ingested)  (ingested)
    
    Supersession Chain:
    ┌─────────────────┐   supersedes   ┌─────────────────┐
    │ Obs (guidance)  │◄──────────────│ Obs (revised)   │
    │ 2025-01-15      │               │ 2025-02-01      │
    │ superseded_by ──┼──────────────►│ supersedes ─────┼──►
    └─────────────────┘               └─────────────────┘
    
    Value Structure:
    ┌────────────────────────────────────────────────────────┐
    │ Observation                                            │
    │ ├─ metric: MetricSpec (EPS, diluted, GAAP, reported)   │
    │ ├─ period: FiscalPeriod (Q4 FY2025)                    │
    │ ├─ value: ValueWithUnits                               │
    │ │     ├─ value_normalized: 6.11 (always base units)   │
    │ │     ├─ value_raw: 6.11                               │
    │ │     └─ unit: "USD/share"                             │
    │ ├─ provenance_ref: ProvenanceRef                       │
    │ │     ├─ kind: SEC_FILING                              │
    │ │     └─ external_id: "0001193125-25-..."              │
    │ └─ source_key: SourceKey                               │
    │       ├─ vendor: SEC                                   │
    │       └─ xbrl_tag: "EarningsPerShareDiluted"           │
    └────────────────────────────────────────────────────────┘
    ```
    Dependencies: None - stdlib only (dataclasses, datetime, decimal)
    Storage Tier: T1 (SQLite), T2 (DuckDB), T3 (PostgreSQL)
```

*Source: [`Observation`](/app/projects/entityspine/src/entityspine/domain/observation.py#L602)*

```
```
    ┌──────────────────────────────────────────────────────────┐
    │               Entity → Security → Listing                 │
    └──────────────────────────────────────────────────────────┘
    
         ┌─────────────┐
         │   Entity    │ Apple Inc.
         │(entity_id)  │
         └──────┬──────┘
                │ 1:N (issues)
       ┌────────┼────────┐
       ▼        ▼        ▼
    ┌──────┐ ┌──────┐ ┌──────┐
    │ Sec  │ │ Sec  │ │ Sec  │ AAPL Common, AAPL Pref, AAPL 3.85% 2046
    └──┬───┘ └──┬───┘ └──────┘
       │        │
       │ 1:N    │ 1:N (listed_on)
       │        │
    ┌──┴──┐  ┌──┴──┐
    │List │  │List │  NASDAQ:AAPL, NYSE:AAPL
    └─────┘  └─────┘
    
    Identifier Claims:
    ┌─────────────┐
    │IdentifierClaim│
    │ ISIN: US0378331005  │──► Security (AAPL Common)
    │ CUSIP: 037833100    │
    │ FIGI: BBG000B9XRY4  │
    └─────────────┘
    ```
    Dependencies: None - stdlib only (dataclasses, datetime)
    Storage Tier: T0 (JSON), T1 (SQLite), T2 (DuckDB), T3 (PostgreSQL)
```

*Source: [`Security`](/app/projects/entityspine/src/entityspine/domain/security.py#L40)*

```
```
    ┌──────────────────────────────────────────────────────────┐
    │               FuzzyMatcher Pipeline                       │
    └──────────────────────────────────────────────────────────┘
    
    "Apple Inc."
          │
          ▼
    ┌─────────────────┐
    │   Normalize     │  → "apple"
    │ - lowercase     │     (remove Inc, Corp, etc.)
    │ - strip suffix  │
    │ - collapse ws   │
    └────────┬────────┘
             │
             ▼
    ┌─────────────────────────────────────────────┐
    │        Compute Similarities                  │
    │                                              │
    │  ┌─────────────┐  ┌─────────────┐  ┌──────┐ │
    │  │Jaro-Winkler │  │ Levenshtein │  │Trigram│ │
    │  │  (40%)      │  │   (30%)     │  │ (30%)│ │
    │  └──────┬──────┘  └──────┬──────┘  └───┬──┘ │
    │         │                │              │    │
    │         └────────┬───────┴──────────────┘    │
    │                  ▼                           │
    │         Weighted Average                     │
    └─────────────────────────────────────────────┘
             │
             ▼
    Score: 0.0 - 1.0
             │
             ▼
    ┌─────────────────┐
    │ Threshold Check │  min_score=0.6
    │ score >= 0.6?   │
    └─────────────────┘
             │
        yes  │  no
             ▼
          Match / None
    ```
    Dependencies: None (stdlib only); Optional: rapidfuzz for 10x speed
    Storage Tier: N/A (stateless service)
```

*Source: [`FuzzyMatcher`](/app/projects/entityspine/src/entityspine/services/fuzzy.py#L340)*

```
```
    ┌──────────────────────────────────────────────────────────┐
    │                  GraphService Traversals                  │
    └──────────────────────────────────────────────────────────┘
    
    get_subsidiaries(parent_id, include_indirect=True)
    
          Parent
            │
    ┌───────┼───────┐
    │ depth=1       │
    ▼               ▼
    Sub A         Sub B
                    │
              ┌─────┼─────┐
              │ depth=2   │
              ▼           ▼
            Sub B1      Sub B2
    
    find_path(source_id, target_id)
    
    Source ──?──> ... ──?──> Target
    
    BFS traversal returns:
    EntityPath {
        source: Entity
        target: Entity
        steps: [PathStep, PathStep, ...]
        total_distance: 3
    }
    
    get_entity_network(center_id, max_depth=2)
    
                  ┌─────────────┐
                  │   Center    │ depth=0
                  └──────┬──────┘
               ┌─────────┼─────────┐
               │         │         │
               ▼         ▼         ▼
          ┌────────┐ ┌────────┐ ┌────────┐
          │ Node A │ │ Node B │ │ Node C │ depth=1
          └───┬────┘ └───┬────┘ └────────┘
              │          │
           ┌──┴──┐    ┌──┴──┐
           ▼     ▼    ▼     ▼
        Node D Node E  ...   depth=2
    ```
    Dependencies: SqliteStore
    Storage Tier: T1 (SQLite) or higher
```

*Source: [`GraphService`](/app/projects/entityspine/src/entityspine/services/graph_service.py#L132)*

```
```
    ┌──────────────────────────────────────────────────────────┐
    │                 EntityResolver Flow                       │
    └──────────────────────────────────────────────────────────┘
    
    resolve("AAPL")
          │
          ▼
    ┌─────────────────┐
    │ Classify Input  │  → IdentifierType.TICKER
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │ Route by Type   │
    │ ├─ CIK: lookup  │
    │ ├─ ISIN: lookup │
    │ ├─ Ticker: list │
    │ └─ Name: fuzzy  │
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │ Store Lookup    │  → SqliteStore / JsonStore
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │ Follow Redirect │  (if merged entity)
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │Build Resolution │  → ResolutionResult
    │    Result       │     ├─ entity
    └─────────────────┘     ├─ confidence
                            ├─ candidates[]
                            └─ match_reason
    ```
    Dependencies: SqliteStore (or JsonStore), FuzzyMatcher
    Storage Tier: Works with T0 (JSON) or T1 (SQLite)
```

*Source: [`EntityResolver`](/app/projects/entityspine/src/entityspine/services/resolver.py#L87)*

```
```
    ┌──────────────────────────────────────────────────────────┐
    │               JsonEntityStore (Tier 0)                    │
    └──────────────────────────────────────────────────────────┘
    
    Memory Storage:
    ┌─────────────────────────────────────────────────────────┐
    │  _entities: dict[entity_id, Entity]                      │
    │  _securities: dict[security_id, Security]                │
    │  _listings: dict[listing_id, Listing]                    │
    │  _claims: dict[claim_id, IdentifierClaim]                │
    └─────────────────────────────────────────────────────────┘
    
    Indexes (for fast lookup):
    ┌─────────────────────────────────────────────────────────┐
    │  _cik_index: dict[cik, set[entity_id]]                   │
    │  _ticker_index: dict[ticker, set[listing_id]]            │
    │  _name_index: dict[lowercase_name, set[entity_id]]       │
    │  _security_by_entity: dict[entity_id, set[security_id]]  │
    │  _listing_by_security: dict[security_id, set[listing_id]]│
    └─────────────────────────────────────────────────────────┘
    
    Persistence (optional):
    ┌────────────────┐        ┌────────────────┐
    │ JsonEntityStore │◄─────►│  entities.json │
    │   (memory)     │  save/ │    (disk)      │
    └────────────────┘  load  └────────────────┘
    
    Data Loading (SEC company_tickers.json):
    
    SEC JSON:
    {"0": {"cik_str": "320193", "ticker": "AAPL", "title": "Apple Inc."}}
          │
          ▼
    ┌─────────────────┐
    │ Entity          │◄── IdentifierClaim (CIK)
    │ Apple Inc.      │
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │ Security        │
    │ AAPL Common     │
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │ Listing         │◄── IdentifierClaim (TICKER)
    │ XNAS:AAPL       │
    └─────────────────┘
    ```
    Dependencies: None - stdlib only (json, urllib)
    Storage Tier: T0 (JSON)
```

*Source: [`JsonEntityStore`](/app/projects/entityspine/src/entityspine/stores/json_store.py#L46)*

```
```
    ┌──────────────────────────────────────────────────────────┐
    │                  SqliteStore (Tier 1)                     │
    │                   Facade Pattern                          │
    └──────────────────────────────────────────────────────────┘
                               │
                ┌──────────────┼──────────────┐
                │              │              │
                ▼              ▼              ▼
    ┌───────────────┐ ┌───────────────┐ ┌───────────────┐
    │EntityRepository│ │SecurityRepo   │ │ListingRepo    │
    │ - save()      │ │ - save()      │ │ - save()      │
    │ - get()       │ │ - get()       │ │ - get()       │
    │ - search()    │ │ - by_entity() │ │ - by_ticker() │
    └───────────────┘ └───────────────┘ └───────────────┘
            │              │              │
            └──────────────┼──────────────┘
                           │
                           ▼
            ┌─────────────────────────────┐
            │   SqliteConnectionManager   │
            │   - connection pool         │
            │   - thread safety           │
            └─────────────────────────────┘
                           │
                           ▼
            ┌─────────────────────────────┐
            │        SQLite DB            │
            │   entities.db               │
            │   - entities table          │
            │   - securities table        │
            │   - listings table          │
            │   - identifier_claims table │
            │   - relationships table     │
            │   - ... (20+ tables)        │
            └─────────────────────────────┘
    
    Repository Structure:
    stores/sqlite/
    ├── __init__.py
    ├── connection.py      # SqliteConnectionManager
    ├── schema.py          # SCHEMA_SQL DDL
    ├── converters.py      # row_to_entity(), etc.
    ├── storage.py         # SqliteStore (this class)
    └── repositories/
        ├── entity.py      # EntityRepository
        ├── security.py    # SecurityRepository
        ├── listing.py     # ListingRepository
        ├── claim.py       # ClaimRepository
        └── ... (10+ repos)
    ```
    Dependencies: None - stdlib sqlite3 only
    Storage Tier: T1 (SQLite)
```

*Source: [`SqliteStore`](/app/projects/entityspine/src/entityspine/stores/sqlite/storage.py#L77)*


---

## BrokerDealer

```
```
    ┌──────────────────────────────────────────────────────────┐
    │            Broker-Dealer in Market Structure             │
    └──────────────────────────────────────────────────────────┘
    
    Customer Order Flow:
    
    ┌────────────┐     ┌─────────────────┐     ┌──────────────┐
    │  Customer  │────►│  BrokerDealer   │────►│   Exchange   │
    │  (Retail)  │     │  (CRD: 12345)   │     │   (XNYS)     │
    └────────────┘     │                 │     └──────────────┘
                       │  Memberships:   │
                       │  ├─ NYSE (DMM)  │     ┌──────────────┐
                       │  ├─ NASDAQ      │────►│   Exchange   │
                       │  └─ CBOE        │     │   (XNAS)     │
                       └────────┬────────┘     └──────────────┘
                                │
                       Clearing │
                                ▼
                       ┌─────────────────┐
                       │  Clearinghouse  │
                       │    (NSCC)       │
                       └─────────────────┘
    
    Introducing vs Clearing Broker:
    ┌─────────────────┐     ┌─────────────────┐     ┌────────────┐
    │   Introducing   │────►│    Clearing     │────►│Clearinghouse│
    │   BD (front)    │     │    BD (back)    │     │   (DTCC)   │
    │   CRD: 54321    │     │   CRD: 12345    │     │            │
    └─────────────────┘     └─────────────────┘     └────────────┘
    ```
    Dependencies: validators.py (CRD normalization)
    Storage Tier: T0 (JSON), T1 (SQLite), T2 (DuckDB), T3 (PostgreSQL)
```

*Source: [`BrokerDealer`](/app/projects/entityspine/src/entityspine/domain/markets.py#L584)*



## Clearinghouse

```
```
    ┌──────────────────────────────────────────────────────────┐
    │          Clearinghouse in the Settlement Chain           │
    └──────────────────────────────────────────────────────────┘
    
    Trade Execution → Clearing → Settlement
    
    ┌──────────┐  ┌──────────┐     ┌─────────────────┐     ┌──────────────┐
    │  Buyer   │  │  Seller  │     │    Exchange     │     │ Clearinghouse│
    │   BD     │  │   BD     │     │    (XNYS)       │     │   (NSCC)     │
    └────┬─────┘  └────┬─────┘     └────────┬────────┘     └──────┬───────┘
         │             │                    │                      │
         │    Trade Matched                 │                      │
         └─────────────┴────────────────────►                      │
                                            │   Trade Novation     │
                                            └──────────────────────►
                                                                   │
                                                       ┌───────────┴──────────┐
                                                       │      Netting         │
                                                       │  (reduce exposures)  │
                                                       └───────────┬──────────┘
                                                                   │
    ┌────────────────────────────────────────────────────────────────┐
    │                      DTCC Structure                             │
    │  ┌───────────┐    ┌───────────┐    ┌───────────┐              │
    │  │   NSCC    │    │    DTC    │    │   FICC    │              │
    │  │ (equities)│    │(depository)│   │  (fixed)  │              │
    │  └───────────┘    └───────────┘    └───────────┘              │
    └────────────────────────────────────────────────────────────────┘
    ```
    Dependencies: validators.py (SEC file number normalization)
    Storage Tier: T0 (JSON), T1 (SQLite), T2 (DuckDB), T3 (PostgreSQL)
```

*Source: [`Clearinghouse`](/app/projects/entityspine/src/entityspine/domain/markets.py#L1013)*



## ClearingMembership

```
```
    ┌──────────────────────────────────────────────────────────┐
    │           Clearing Membership Graph Relationships        │
    └──────────────────────────────────────────────────────────┘
    
    Direct Clearing Member:
    ┌─────────────────┐                    ┌─────────────────┐
    │   BrokerDealer  │───────────────────►│  Clearinghouse  │
    │   (Goldman)     │ ClearingMembership │     (NSCC)      │
    │   CRD: 361      │    FULL_CLEARING   │                 │
    └─────────────────┘                    └─────────────────┘
    
    Correspondent Clearing (introducing → clearing BD → CCP):
    ┌─────────────────┐     ┌─────────────────┐     ┌──────────────┐
    │   Introducing   │────►│    Clearing     │────►│ Clearinghouse│
    │       BD        │corr.│       BD        │memb.│    (NSCC)    │
    └─────────────────┘     └─────────────────┘     └──────────────┘
    ```
    Dependencies: None (relationship model)
    Storage Tier: T1 (SQLite), T2 (DuckDB), T3 (PostgreSQL)
```

*Source: [`ClearingMembership`](/app/projects/entityspine/src/entityspine/domain/markets.py#L1254)*



## Entity

```
```
    ┌──────────────────────────────────────────────────────────┐
    │                  Entity Relationship Model                │
    └──────────────────────────────────────────────────────────┘
    
                       ┌─────────────┐
                       │   Entity    │◄──── IdentifierClaim (CIK, LEI, EIN)
                       │  (Apple)    │
                       └──────┬──────┘
                              │ issues
                              ▼
                       ┌─────────────┐
                       │  Security   │◄──── IdentifierClaim (CUSIP, ISIN)
                       │(AAPL Stock) │
                       └──────┬──────┘
                              │ listed_on
                              ▼
                       ┌─────────────┐
                       │   Listing   │◄──── IdentifierClaim (TICKER)
                       │(NASDAQ:AAPL)│
                       └─────────────┘
    
    Merged Entity Flow:
    ┌─────────┐        ┌─────────┐
    │Entity A │──────► │Entity B │  (A.redirect_to = B.entity_id)
    │(merged) │        │(active) │
    └─────────┘        └─────────┘
    ```
    Dependencies: None - stdlib only (dataclasses, datetime)
    Storage Tier: T0 (JSON), T1 (SQLite), T2 (DuckDB), T3 (PostgreSQL)
```

*Source: [`Entity`](/app/projects/entityspine/src/entityspine/domain/entity.py#L27)*



## EntityResolver

```
```
    ┌──────────────────────────────────────────────────────────┐
    │                 EntityResolver Flow                       │
    └──────────────────────────────────────────────────────────┘
    
    resolve("AAPL")
          │
          ▼
    ┌─────────────────┐
    │ Classify Input  │  → IdentifierType.TICKER
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │ Route by Type   │
    │ ├─ CIK: lookup  │
    │ ├─ ISIN: lookup │
    │ ├─ Ticker: list │
    │ └─ Name: fuzzy  │
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │ Store Lookup    │  → SqliteStore / JsonStore
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │ Follow Redirect │  (if merged entity)
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │Build Resolution │  → ResolutionResult
    │    Result       │     ├─ entity
    └─────────────────┘     ├─ confidence
                            ├─ candidates[]
                            └─ match_reason
    ```
    Dependencies: SqliteStore (or JsonStore), FuzzyMatcher
    Storage Tier: Works with T0 (JSON) or T1 (SQLite)
```

*Source: [`EntityResolver`](/app/projects/entityspine/src/entityspine/services/resolver.py#L87)*



## Err

```
```
    ┌──────────────────────────────────────────────────┐
    │            Error Propagation Flow                │
    └──────────────────────────────────────────────────┘
                            │
    ┌───────────────────────┼───────────────────────┐
    │                       ▼                        │
    │   try_result(risky_op)                        │
    │           │                                    │
    │   ┌───────┴───────┐                           │
    │   │   Success?    │                           │
    │   └───────┬───────┘                           │
    │     yes   │   no                              │
    │     ▼     │   ▼                               │
    │  Ok(val)  │  Err(exc)                         │
    │     │     │   │                               │
    │     │.map(f)  │.map(f) → Err(exc) unchanged   │
    │     ▼         ▼                               │
    │  Ok(f(v))  Err(exc)  ← errors propagate       │
    └──────────────────────────────────────────────┘
    ```
    Dependencies: None - stdlib only (dataclasses, typing)
```

*Source: [`Err`](/app/projects/entityspine/src/entityspine/domain/workflow.py#L521)*



## ExchangeMembership

```
```
    ┌──────────────────────────────────────────────────────────┐
    │         Exchange Membership - Trading Rights Graph       │
    └──────────────────────────────────────────────────────────┘
    
    ┌─────────────────┐                       ┌──────────────┐
    │   BrokerDealer  │                       │   Exchange   │
    │   (Citadel)     │                       │    (NYSE)    │
    │   CRD: 116797   │                       │   MIC: XNYS  │
    └────────┬────────┘                       └──────┬───────┘
             │                                       │
             │  ExchangeMembership                   │
             │  ┌────────────────────────────────┐   │
             └──┤ MPID: CDRG                     ├───┘
                │ type: TRADING_MEMBER           │
                │ is_designated_market_maker: ✓  │
                │ can_trade_equity: ✓            │
                │ can_trade_options: ✓           │
                │ status: ACTIVE                 │
                │ valid_from: 2004-01-01         │
                └────────────────────────────────┘
    
    Multi-Exchange Membership:
    ┌─────────────────┐     ┌──────────┐     ┌──────────┐
    │   BrokerDealer  │────►│   NYSE   │     │  NASDAQ  │
    │                 │     └──────────┘     └──────────┘
    │   memberships:  │────►│   CBOE   │     │  ARCA    │
    │    - XNYS (DMM) │     └──────────┘     └──────────┘
    │    - XNAS       │────►│   IEX    │
    │    - XCBO       │     └──────────┘
    └─────────────────┘
    ```
    Dependencies: validators.py (MPID normalization)
    Storage Tier: T1 (SQLite), T2 (DuckDB), T3 (PostgreSQL)
```

*Source: [`ExchangeMembership`](/app/projects/entityspine/src/entityspine/domain/markets.py#L1394)*



## ExecutionContext

```
```
    ┌─────────────────────────────────────────────────────────┐
    │                 Pipeline Execution Tree                  │
    └─────────────────────────────────────────────────────────┘
    
    Root Context (batch_id: "backfill_2026-01-29")
          │ execution_id: "abc123"
          │
          ├─── Child Context (workflow: "ingest_sec")
          │       │ execution_id: "def456"
          │       │ parent_execution_id: "abc123"
          │       │
          │       ├─── Grandchild (workflow: "parse_10k")
          │       │       execution_id: "ghi789"
          │       │       parent_execution_id: "def456"
          │       │
          │       └─── Grandchild (workflow: "parse_10q")
          │               execution_id: "jkl012"
          │               parent_execution_id: "def456"
          │
          └─── Child Context (workflow: "resolve_entities")
                  execution_id: "mno345"
                  parent_execution_id: "abc123"
    ```
    Dependencies: None - stdlib only (dataclasses, datetime, uuid)
```

*Source: [`ExecutionContext`](/app/projects/entityspine/src/entityspine/domain/workflow.py#L132)*



## FeedSpineAdapter

```
```
FeedSpine (SILVER layer) ──► FeedSpineAdapter ──► EntitySpine (Entities)
                                │
                                ├─ Extracts CIK, ticker, name
                                ├─ Checks for existing entity
                                └─ Creates/updates entity
```

Example:
    >>> adapter = FeedSpineAdapter(feedspine, entity_store)
    >>>
    >>> # Sync all SEC entities from FeedSpine
    >>> result = await adapter.sync_sec_entities()
    >>> print(f"Created {result.entities_created} entities")
    >>>
    >>> # Query FeedSpine records with entity resolution
    >>> async for record in adapter.iter_enriched_records("sec-tickers"):
    ...     print(f"{record['ticker']} → {record['entity_name']}")
```

*Source: [`FeedSpineAdapter`](/app/projects/entityspine/src/entityspine/adapters/feedspine_adapter.py#L78)*



## FuzzyMatcher

```
```
    ┌──────────────────────────────────────────────────────────┐
    │               FuzzyMatcher Pipeline                       │
    └──────────────────────────────────────────────────────────┘
    
    "Apple Inc."
          │
          ▼
    ┌─────────────────┐
    │   Normalize     │  → "apple"
    │ - lowercase     │     (remove Inc, Corp, etc.)
    │ - strip suffix  │
    │ - collapse ws   │
    └────────┬────────┘
             │
             ▼
    ┌─────────────────────────────────────────────┐
    │        Compute Similarities                  │
    │                                              │
    │  ┌─────────────┐  ┌─────────────┐  ┌──────┐ │
    │  │Jaro-Winkler │  │ Levenshtein │  │Trigram│ │
    │  │  (40%)      │  │   (30%)     │  │ (30%)│ │
    │  └──────┬──────┘  └──────┬──────┘  └───┬──┘ │
    │         │                │              │    │
    │         └────────┬───────┴──────────────┘    │
    │                  ▼                           │
    │         Weighted Average                     │
    └─────────────────────────────────────────────┘
             │
             ▼
    Score: 0.0 - 1.0
             │
             ▼
    ┌─────────────────┐
    │ Threshold Check │  min_score=0.6
    │ score >= 0.6?   │
    └─────────────────┘
             │
        yes  │  no
             ▼
          Match / None
    ```
    Dependencies: None (stdlib only); Optional: rapidfuzz for 10x speed
    Storage Tier: N/A (stateless service)
```

*Source: [`FuzzyMatcher`](/app/projects/entityspine/src/entityspine/services/fuzzy.py#L340)*



## GraphService

```
```
    ┌──────────────────────────────────────────────────────────┐
    │                  GraphService Traversals                  │
    └──────────────────────────────────────────────────────────┘
    
    get_subsidiaries(parent_id, include_indirect=True)
    
          Parent
            │
    ┌───────┼───────┐
    │ depth=1       │
    ▼               ▼
    Sub A         Sub B
                    │
              ┌─────┼─────┐
              │ depth=2   │
              ▼           ▼
            Sub B1      Sub B2
    
    find_path(source_id, target_id)
    
    Source ──?──> ... ──?──> Target
    
    BFS traversal returns:
    EntityPath {
        source: Entity
        target: Entity
        steps: [PathStep, PathStep, ...]
        total_distance: 3
    }
    
    get_entity_network(center_id, max_depth=2)
    
                  ┌─────────────┐
                  │   Center    │ depth=0
                  └──────┬──────┘
               ┌─────────┼─────────┐
               │         │         │
               ▼         ▼         ▼
          ┌────────┐ ┌────────┐ ┌────────┐
          │ Node A │ │ Node B │ │ Node C │ depth=1
          └───┬────┘ └───┬────┘ └────────┘
              │          │
           ┌──┴──┐    ┌──┴──┐
           ▼     ▼    ▼     ▼
        Node D Node E  ...   depth=2
    ```
    Dependencies: SqliteStore
    Storage Tier: T1 (SQLite) or higher
```

*Source: [`GraphService`](/app/projects/entityspine/src/entityspine/services/graph_service.py#L132)*



## IdentifierClaim

```
```
    ┌──────────────────────────────────────────────────────────┐
    │            Claims-Based Identity Resolution              │
    └──────────────────────────────────────────────────────────┘
    
    Query: "Who is CIK 0000320193?"
    
    ┌─────────────────────────┐
    │    IdentifierClaim      │
    │  scheme: CIK            │
    │  value: "0000320193"    │
    │  entity_id: "01HQ..."   │──► Entity: Apple Inc.
    │  namespace: SEC         │
    │  confidence: 1.0        │
    │  valid_from: 1980       │
    │  valid_to: null         │
    └─────────────────────────┘
    
    Multi-Vendor Crosswalk (same entity, different sources):
    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
    │ Claim (SEC)  │  │Claim(FactSet)│  │Claim(Bloom.) │
    │ CIK: 320193  │  │ENTITY:000C7F │  │FIGI:BBG...   │
    │ conf: 1.0    │  │ conf: 0.95   │  │ conf: 0.98   │
    └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
           │                 │                 │
           └────────────┬────┴─────────────────┘
                        ▼
                ┌─────────────┐
                │   Entity    │ Apple Inc.
                └─────────────┘
    
    Scheme-Scope Enforcement:
    ┌─────────────────────────────────────────────┐
    │ CIK, LEI, EIN        → entity_id (required) │
    │ CUSIP, ISIN, SEDOL   → security_id          │
    │ TICKER               → listing_id           │
    └─────────────────────────────────────────────┘
    ```
    Dependencies: None - stdlib only (dataclasses, datetime)
    Storage Tier: T0 (JSON), T1 (SQLite), T2 (DuckDB), T3 (PostgreSQL)
```

*Source: [`IdentifierClaim`](/app/projects/entityspine/src/entityspine/domain/claim.py#L26)*



## JsonEntityStore

```
```
    ┌──────────────────────────────────────────────────────────┐
    │               JsonEntityStore (Tier 0)                    │
    └──────────────────────────────────────────────────────────┘
    
    Memory Storage:
    ┌─────────────────────────────────────────────────────────┐
    │  _entities: dict[entity_id, Entity]                      │
    │  _securities: dict[security_id, Security]                │
    │  _listings: dict[listing_id, Listing]                    │
    │  _claims: dict[claim_id, IdentifierClaim]                │
    └─────────────────────────────────────────────────────────┘
    
    Indexes (for fast lookup):
    ┌─────────────────────────────────────────────────────────┐
    │  _cik_index: dict[cik, set[entity_id]]                   │
    │  _ticker_index: dict[ticker, set[listing_id]]            │
    │  _name_index: dict[lowercase_name, set[entity_id]]       │
    │  _security_by_entity: dict[entity_id, set[security_id]]  │
    │  _listing_by_security: dict[security_id, set[listing_id]]│
    └─────────────────────────────────────────────────────────┘
    
    Persistence (optional):
    ┌────────────────┐        ┌────────────────┐
    │ JsonEntityStore │◄─────►│  entities.json │
    │   (memory)     │  save/ │    (disk)      │
    └────────────────┘  load  └────────────────┘
    
    Data Loading (SEC company_tickers.json):
    
    SEC JSON:
    {"0": {"cik_str": "320193", "ticker": "AAPL", "title": "Apple Inc."}}
          │
          ▼
    ┌─────────────────┐
    │ Entity          │◄── IdentifierClaim (CIK)
    │ Apple Inc.      │
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │ Security        │
    │ AAPL Common     │
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │ Listing         │◄── IdentifierClaim (TICKER)
    │ XNAS:AAPL       │
    └─────────────────┘
    ```
    Dependencies: None - stdlib only (json, urllib)
    Storage Tier: T0 (JSON)
```

*Source: [`JsonEntityStore`](/app/projects/entityspine/src/entityspine/stores/json_store.py#L46)*



## Listing

```
```
    ┌──────────────────────────────────────────────────────────┐
    │        Ticker Resolution: Historical Point-in-Time       │
    └──────────────────────────────────────────────────────────┘
    
    Query: resolve("FB", as_of=2021-06-01)
    
    ┌───────────────┐
    │   Listing     │ ticker="FB", mic="XNAS"
    │ start: 2012   │ start_date=2012-05-18
    │ end: 2022     │ end_date=2022-06-08
    └───────┬───────┘
            │ security_id
            ▼
    ┌───────────────┐
    │   Security    │ "Meta Class A Common Stock"
    └───────┬───────┘
            │ entity_id
            ▼
    ┌───────────────┐
    │    Entity     │ "Meta Platforms, Inc."
    └───────────────┘
    
    Same security, new listing:
    ┌───────────────┐
    │   Listing     │ ticker="META", mic="XNAS"
    │ start: 2022   │ start_date=2022-06-09
    │ end: null     │ end_date=None (active)
    └───────┬───────┘
            │ same security_id
            ▼
    ┌───────────────┐
    │   Security    │ (same as above)
    └───────────────┘
    ```
    Dependencies: None - stdlib only (dataclasses, datetime)
    Storage Tier: T0 (JSON), T1 (SQLite), T2 (DuckDB), T3 (PostgreSQL)
```

*Source: [`Listing`](/app/projects/entityspine/src/entityspine/domain/listing.py#L51)*



## Observation

```
```
    ┌──────────────────────────────────────────────────────────┐
    │              Observation Time Semantics                   │
    └──────────────────────────────────────────────────────────┘
    
    Timeline: ──────────────────────────────────────────────►
              Jan 2025        Feb 2025        Mar 2025
    
    period (what):      ├── Q4 FY2025 ──┤
    
    as_of (when known):         ▲            ▲           ▲
                          guidance      revised     actual
                          2025-01-15   2025-02-01  2025-02-28
    
    captured_at:              ●             ●           ●
                         (ingested)    (ingested)  (ingested)
    
    Supersession Chain:
    ┌─────────────────┐   supersedes   ┌─────────────────┐
    │ Obs (guidance)  │◄──────────────│ Obs (revised)   │
    │ 2025-01-15      │               │ 2025-02-01      │
    │ superseded_by ──┼──────────────►│ supersedes ─────┼──►
    └─────────────────┘               └─────────────────┘
    
    Value Structure:
    ┌────────────────────────────────────────────────────────┐
    │ Observation                                            │
    │ ├─ metric: MetricSpec (EPS, diluted, GAAP, reported)   │
    │ ├─ period: FiscalPeriod (Q4 FY2025)                    │
    │ ├─ value: ValueWithUnits                               │
    │ │     ├─ value_normalized: 6.11 (always base units)   │
    │ │     ├─ value_raw: 6.11                               │
    │ │     └─ unit: "USD/share"                             │
    │ ├─ provenance_ref: ProvenanceRef                       │
    │ │     ├─ kind: SEC_FILING                              │
    │ │     └─ external_id: "0001193125-25-..."              │
    │ └─ source_key: SourceKey                               │
    │       ├─ vendor: SEC                                   │
    │       └─ xbrl_tag: "EarningsPerShareDiluted"           │
    └────────────────────────────────────────────────────────┘
    ```
    Dependencies: None - stdlib only (dataclasses, datetime, decimal)
    Storage Tier: T1 (SQLite), T2 (DuckDB), T3 (PostgreSQL)
```

*Source: [`Observation`](/app/projects/entityspine/src/entityspine/domain/observation.py#L602)*



## Ok

```
```
    ┌─────────────────────────────────────────────────┐
    │              Result[T] Type Alias               │
    │         (Ok[T] | Err[T] = Result[T])           │
    └─────────────────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        ▼                         ▼
    ┌───────────┐           ┌───────────┐
    │   Ok[T]   │           │  Err[T]   │
    │  ┌─────┐  │           │  ┌─────┐  │
    │  │value│  │           │  │error│  │
    │  └─────┘  │           │  └─────┘  │
    └───────────┘           └───────────┘
          │                       │
          │ .map(f)               │ .map(f) → self
          ▼                       │
    ┌───────────┐                 │
    │ Ok(f(val))│                 │
    └───────────┘                 │
    ```
    Dependencies: None - stdlib only (dataclasses, typing)
```

*Source: [`Ok`](/app/projects/entityspine/src/entityspine/domain/workflow.py#L381)*



## Relationship

```
```
    ┌──────────────────────────────────────────────────────────┐
    │         Generic Relationship with NodeRef Pattern        │
    └──────────────────────────────────────────────────────────┘
    
    ┌─────────────┐                      ┌─────────────┐
    │   NodeRef   │─────Relationship────►│   NodeRef   │
    │  source_ref │  relationship_type   │  target_ref │
    │ kind + id   │  valid_from/to       │ kind + id   │
    └─────────────┘  evidence            └─────────────┘
    
    Example: Apple (entity) → Cupertino HQ (geo)
    ┌─────────────────┐                  ┌─────────────────┐
    │ NodeRef         │                  │ NodeRef         │
    │ kind: ENTITY    │   HEADQUARTER    │ kind: GEO       │
    │ id: "ent_apple" │────────────────► │ id: "geo_cup"   │
    └─────────────────┘                  └─────────────────┘
    
    Evidence Chain:
    ┌────────────────────────────────────────────────────────┐
    │ Relationship                                           │
    │ ├─ source_ref: entity:ent_apple                        │
    │ ├─ target_ref: geo:geo_cupertino                       │
    │ ├─ relationship_type: HEADQUARTER                      │
    │ ├─ valid_from: 1993-01-01                              │
    │ ├─ valid_to: null (current)                            │
    │ ├─ evidence_filing_id: 0001193125-23-272374            │
    │ ├─ evidence_snippet: "principal executive offices..."  │
    │ └─ confidence: 0.95                                    │
    └────────────────────────────────────────────────────────┘
    ```
    Dependencies: None - stdlib only (dataclasses, datetime)
    Storage Tier: T1 (SQLite), T2 (DuckDB), T3 (PostgreSQL)
```

*Source: [`Relationship`](/app/projects/entityspine/src/entityspine/domain/graph.py#L994)*



## Security

```
```
    ┌──────────────────────────────────────────────────────────┐
    │               Entity → Security → Listing                 │
    └──────────────────────────────────────────────────────────┘
    
         ┌─────────────┐
         │   Entity    │ Apple Inc.
         │(entity_id)  │
         └──────┬──────┘
                │ 1:N (issues)
       ┌────────┼────────┐
       ▼        ▼        ▼
    ┌──────┐ ┌──────┐ ┌──────┐
    │ Sec  │ │ Sec  │ │ Sec  │ AAPL Common, AAPL Pref, AAPL 3.85% 2046
    └──┬───┘ └──┬───┘ └──────┘
       │        │
       │ 1:N    │ 1:N (listed_on)
       │        │
    ┌──┴──┐  ┌──┴──┐
    │List │  │List │  NASDAQ:AAPL, NYSE:AAPL
    └─────┘  └─────┘
    
    Identifier Claims:
    ┌─────────────┐
    │IdentifierClaim│
    │ ISIN: US0378331005  │──► Security (AAPL Common)
    │ CUSIP: 037833100    │
    │ FIGI: BBG000B9XRY4  │
    └─────────────┘
    ```
    Dependencies: None - stdlib only (dataclasses, datetime)
    Storage Tier: T0 (JSON), T1 (SQLite), T2 (DuckDB), T3 (PostgreSQL)
```

*Source: [`Security`](/app/projects/entityspine/src/entityspine/domain/security.py#L40)*



## SqliteStore

```
```
    ┌──────────────────────────────────────────────────────────┐
    │                  SqliteStore (Tier 1)                     │
    │                   Facade Pattern                          │
    └──────────────────────────────────────────────────────────┘
                               │
                ┌──────────────┼──────────────┐
                │              │              │
                ▼              ▼              ▼
    ┌───────────────┐ ┌───────────────┐ ┌───────────────┐
    │EntityRepository│ │SecurityRepo   │ │ListingRepo    │
    │ - save()      │ │ - save()      │ │ - save()      │
    │ - get()       │ │ - get()       │ │ - get()       │
    │ - search()    │ │ - by_entity() │ │ - by_ticker() │
    └───────────────┘ └───────────────┘ └───────────────┘
            │              │              │
            └──────────────┼──────────────┘
                           │
                           ▼
            ┌─────────────────────────────┐
            │   SqliteConnectionManager   │
            │   - connection pool         │
            │   - thread safety           │
            └─────────────────────────────┘
                           │
                           ▼
            ┌─────────────────────────────┐
            │        SQLite DB            │
            │   entities.db               │
            │   - entities table          │
            │   - securities table        │
            │   - listings table          │
            │   - identifier_claims table │
            │   - relationships table     │
            │   - ... (20+ tables)        │
            └─────────────────────────────┘
    
    Repository Structure:
    stores/sqlite/
    ├── __init__.py
    ├── connection.py      # SqliteConnectionManager
    ├── schema.py          # SCHEMA_SQL DDL
    ├── converters.py      # row_to_entity(), etc.
    ├── storage.py         # SqliteStore (this class)
    └── repositories/
        ├── entity.py      # EntityRepository
        ├── security.py    # SecurityRepository
        ├── listing.py     # ListingRepository
        ├── claim.py       # ClaimRepository
        └── ... (10+ repos)
    ```
    Dependencies: None - stdlib sqlite3 only
    Storage Tier: T1 (SQLite)
```

*Source: [`SqliteStore`](/app/projects/entityspine/src/entityspine/stores/sqlite/storage.py#L77)*




---

*19 architectural diagrams from 0 components*

*Generated by [doc-automation](https://github.com/your-org/py-sec-edgar/tree/main/spine-core/packages/doc-automation)*