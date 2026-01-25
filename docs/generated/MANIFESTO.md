# MANIFESTO

**Core Principles and Philosophy**

> **Auto-generated from code annotations**  
> **Last Updated**: February 2026  
> **Status**: Living Document

---

## Table of Contents

1. [Core Principles](#core-principles)
1. [General](#general)
1. [Knowledge Graph](#knowledge-graph)
1. [Market Infrastructure](#market-infrastructure)
1. [Data Models](#data-models)
1. [Core Features](#core-features)
1. [Tiered Storage](#tiered-storage)

---

## The Challenge

Financial data comes from many sources, each with their own identifiers.  
The core challenge is: *"Is this the same company across different sources?"*

---

## Core Principles

EntitySpine's claims-based identity model (Principle #2) recognizes that
    identifiers are NOT facts - they are assertions with provenance, confidence,
    and temporal validity. Consider:
    - SEC says Apple's CIK is 0000320193 (confidence: 1.0)
    - FactSet says Apple's entity ID is 000C7F-E (confidence: 0.95)
    - Bloomberg says AAPL's FIGI is BBG000B9XRY4 (confidence: 0.98)
    
    These are all CLAIMS about the same entity from different sources. When
    sources conflict (rare but it happens), confidence scores help resolve.
    Temporal validity (valid_from/valid_to) handles identifier changes:
    - FB ticker valid_to=2022-06-08
    - META ticker valid_from=2022-06-09
    
    Multi-vendor crosswalks are enabled by namespace: the same entity can have
    SEC claims, FactSet claims, and Bloomberg claims, enabling reconciliation.

*Source: [`IdentifierClaim`](/app/projects/entityspine/src/entityspine/domain/claim.py#L26)*

EntitySpine's core insight (Principle #1) is that Entity ≠ Security ≠ Listing.
    Apple Inc. (entity) issues AAPL Common Stock (security) which trades on NASDAQ
    with ticker AAPL (listing). This separation is why identifiers like CIK, LEI,
    and EIN are stored in IdentifierClaim (Principle #2), NOT on Entity. This
    design enables multi-vendor crosswalks: FactSet, Bloomberg, and SEC may all
    have different identifiers for Apple, but they all claim to identify the same
    Entity. Confidence scores track which claims are most reliable.

*Source: [`Entity`](/app/projects/entityspine/src/entityspine/domain/entity.py#L27)*

EntitySpine's critical insight (Principle #1) is that tickers are NOT
    entity identifiers - they are exchange-specific, temporal, and change
    frequently. Consider:
    - FB became META on June 9, 2022 (same company, same security, new ticker)
    - AAPL trades as AAPL on NASDAQ but may have different symbols on foreign
      exchanges
    - Multiple securities can share a ticker (AAPL common vs AAPL warrants)
    - Ticker reuse: TWTR (Twitter 2013-2022) vs TWTR (post-acquisition use)
    
    By putting ticker on Listing with temporal validity (start_date, end_date),
    we can answer questions like "What entity was FB on 2021-01-01?" correctly.
    This is impossible if ticker is stored on Entity.

*Source: [`Listing`](/app/projects/entityspine/src/entityspine/domain/listing.py#L51)*

EntitySpine's three-tier model (Principle #1) separates what is traded
    (Security) from who issued it (Entity) and where it trades (Listing).
    This separation is essential because:
    - Apple Inc. (Entity) has issued multiple securities: common stock,
      corporate bonds, and commercial paper
    - Each Security has different identifiers: common stock has CUSIP
      037833100, bonds have different CUSIPs
    - The same Security (AAPL common) lists on multiple exchanges with
      potentially different tickers
    
    Identifiers like ISIN, CUSIP, SEDOL, and FIGI belong in IdentifierClaim
    (Principle #2), NOT on Security. This enables multi-vendor crosswalks
    and handles the reality that FactSet, Bloomberg, and Refinitiv may all
    have slightly different CUSIP mappings.

*Source: [`Security`](/app/projects/entityspine/src/entityspine/domain/security.py#L40)*

EntitySpine processes data through multi-stage pipelines (Principle #5):
    SEC filing → parse → normalize → resolve → enrich → store. ExecutionContext
    makes this lineage explicit and traceable. When you query "why does Apple
    have two CIKs?", the context links back to which batch, which sub-pipeline,
    and which source file produced each claim. This is critical for debugging
    entity resolution conflicts and for audit compliance.

*Source: [`ExecutionContext`](/app/projects/entityspine/src/entityspine/domain/workflow.py#L132)*

EntitySpine uses the Result[T] pattern (Principle #3) to make success
    and failure explicit in return types. This eliminates the "hidden control
    flow" problem where exceptions can bubble up unexpectedly. Every operation
    that can fail returns Result[T], forcing callers to handle both cases.
    This is especially critical for entity resolution where partial failures
    (e.g., "found entity but missing CUSIP") are common and meaningful.

*Source: [`Ok`](/app/projects/entityspine/src/entityspine/domain/workflow.py#L381)*

EntitySpine uses the Result[T] pattern (Principle #3) because SEC data
    processing involves many partial failures: missing identifiers, stale
    mappings, ambiguous name matches, network timeouts. Rather than throwing
    exceptions that interrupt processing, Err captures failures as values
    that can be logged, aggregated, or retried. This is essential for batch
    pipelines where one bad record shouldn't abort an entire 14,000-company
    load.

*Source: [`Err`](/app/projects/entityspine/src/entityspine/domain/workflow.py#L521)*

## General

The clearing membership graph answers critical operational questions:
    
    - **Trade Settlement**: Can this firm clear trades in this asset class?
    - **Counterparty Risk**: What are the firm's clearing relationships?
    - **Market Access**: Direct clearing vs correspondent clearing?
    - **Regulatory Scope**: Which CCPs does this firm participate in?
    
    This is a temporal relationship: memberships start, may be suspended,
    and can be terminated. Point-in-time queries require checking validity.

*Source: [`ClearingMembership`](/app/projects/entityspine/src/entityspine/domain/markets.py#L1254)*

Trade routing decisions depend on understanding where firms CAN trade:
    
    - **Order Routing**: Which venues can receive orders from this firm?
    - **Market Making**: Which firms are registered MMs on this exchange?
    - **Compliance**: Does the firm have active membership for this trade?
    - **Best Execution**: What venues are available for routing this order?
    
    This relationship is temporal and status-sensitive: a firm can be an
    ACTIVE broker-dealer but have a SUSPENDED membership on a particular
    exchange. Point-in-time queries must check both entity AND membership status.

*Source: [`ExchangeMembership`](/app/projects/entityspine/src/entityspine/domain/markets.py#L1394)*

Entity resolution requires fuzzy name matching because real-world data
    has variations that exact matching misses:
    - "Apple Inc." vs "APPLE INCORPORATED" vs "Apple Computer, Inc."
    - "The Coca-Cola Company" vs "Coca-Cola Co" vs "Coke"
    - "Microsft Corporation" (typo) vs "Microsoft Corporation"
    
    EntitySpine's FuzzyMatcher (Principle #4 - stdlib-only domain) provides
    this capability with ZERO external dependencies by default, while offering
    10x speedup when rapidfuzz is available. The weighted combination of
    algorithms handles different kinds of variations:
    - Jaro-Winkler: Good for typos and similar prefixes
    - Levenshtein: Good for overall character similarity
    - Trigram: Robust to word reordering ("Apple Inc" vs "Inc Apple")

*Source: [`FuzzyMatcher`](/app/projects/entityspine/src/entityspine/services/fuzzy.py#L340)*

## Knowledge Graph

EntitySpine models the world as a knowledge graph where entities
    (companies, people, funds) are connected by typed, temporal, evidence-backed
    relationships. This goes beyond simple "foreign key" links to capture:
    - WHEN the relationship was valid (valid_from/valid_to)
    - WHEN we learned about it (captured_at)
    - WHERE the evidence comes from (filing_id, evidence_snippet)
    - HOW confident we are (confidence score)
    
    The NodeRef pattern enables heterogeneous graph traversal: "Find all
    regulatory cases involving subsidiaries of companies headquartered in
    Delaware" traverses entity→entity (subsidiary), entity→geo (HQ location),
    and entity→case (legal proceeding) relationships.

*Source: [`Relationship`](/app/projects/entityspine/src/entityspine/domain/graph.py#L994)*

EntitySpine is fundamentally a knowledge graph: entities connected by
    typed, temporal, evidence-backed relationships. GraphService makes this
    graph queryable beyond simple foreign key joins:
    - "Get all subsidiaries of Apple (including indirect ones)"
    - "Find the path between two entities in the ownership graph"
    - "Get the 2-hop network around an entity"
    
    This enables compliance use cases (beneficial ownership analysis),
    risk analysis (exposure to sanctioned entities), and due diligence
    (corporate structure verification). The service layer returns rich
    result objects (OfficerInfo, RelatedEntity, EntityPath) rather than
    raw database rows, following EntitySpine's domain-driven design.

*Source: [`GraphService`](/app/projects/entityspine/src/entityspine/services/graph_service.py#L132)*

## Market Infrastructure

Understanding market structure requires modeling WHO can trade WHERE and HOW
    trades are processed. BrokerDealer is the gateway between investors and
    markets:
    
    - **Retail investors** access markets THROUGH broker-dealers
    - **Institutional traders** route orders VIA broker-dealer memberships
    - **Trade execution** flows through exchange memberships (MPID)
    - **Trade settlement** flows through clearing relationships
    
    EntitySpine models this as a graph: Entity (legal identity) → BrokerDealer
    (regulatory registration) → ExchangeMembership (trading rights) → Exchange
    (venue). This enables queries like "which firms can trade options on CBOE?"
    or "trace the clearing chain for this trade."

*Source: [`BrokerDealer`](/app/projects/entityspine/src/entityspine/domain/markets.py#L584)*

Every trade in modern markets flows through clearing and settlement
    infrastructure. Understanding this flow is essential for:
    
    - **Risk Management**: CCPs net exposures and manage collateral
    - **Regulatory Compliance**: SIFMU designation carries systemic importance
    - **Trade Lifecycle**: T+1/T+2 settlement cycles affect operations
    - **Market Access**: Clearing membership determines who can clear
    
    EntitySpine models the clearing chain: BrokerDealer → ClearingMembership →
    Clearinghouse → Settlement. This enables queries like "which firms are
    clearing members of NSCC?" or "trace the settlement flow for this trade."

*Source: [`Clearinghouse`](/app/projects/entityspine/src/entityspine/domain/markets.py#L1013)*

## Data Models

Financial data has three distinct time dimensions that are often conflated:
    1. **period**: What timeframe the number measures (Q4 FY2025 revenue)
    2. **as_of**: When it was known/published (10-K filing date, press release)
    3. **captured_at**: When our system ingested it (for staleness tracking)
    
    EntitySpine separates these because:
    - The same period (Q4 2025) may have multiple observations over time
      (guidance → estimate revisions → preliminary → final → restated)
    - Point-in-time analysis requires knowing what was known WHEN
    - Audit trails require tracking system ingestion separately from publication
    
    The supersession chain (supersedes_id/superseded_by_id) handles revisions
    without destructive updates: the 2024-02-01 Q4 estimate is superseded by
    the 2024-02-15 revised estimate, which is superseded by the 2024-02-28
    actual. All observations remain queryable for analysis.

*Source: [`Observation`](/app/projects/entityspine/src/entityspine/domain/observation.py#L602)*

## Core Features

EntitySpine's killer feature is "resolve anything": given any identifier,
    find the entity. This is harder than it sounds because:
    - Tickers are exchange-specific and change over time (FB→META)
    - CIKs require normalization (320193 vs 0000320193)
    - Names require fuzzy matching ("Apple" vs "Apple Inc." vs "Apple Inc")
    - Historical queries need point-in-time resolution
    
    EntityResolver orchestrates identifier classification, store lookups, fuzzy
    matching, and redirect following into a single API. It embodies Principle #2
    (claims-based identity) by returning confidence scores rather than binary
    match/no-match, and Principle #3 (Result pattern) by returning explicit
    ResolutionResult rather than throwing exceptions.

*Source: [`EntityResolver`](/app/projects/entityspine/src/entityspine/services/resolver.py#L87)*

## Tiered Storage

EntitySpine's tiered storage architecture (Principle #5) provides different
    backends for different scale/complexity needs:
    - T0 (JSON): Simple, fast startup, ~50K entities max
    - T1 (SQLite): Indexed queries, ~500K entities
    - T2 (DuckDB): Analytical queries, millions of entities
    - T3 (PostgreSQL): Production scale, distributed
    
    JsonEntityStore is T0: zero external dependencies (stdlib json module),
    millisecond startup, but limited query capabilities. It's the default
    for development and testing because it requires no database setup.
    
    **TIER CAPABILITY HONESTY**: JsonEntityStore does NOT support temporal
    queries. When as_of is provided, it returns the current value with a
    warning. This is explicit rather than silently ignoring the parameter.

*Source: [`JsonEntityStore`](/app/projects/entityspine/src/entityspine/stores/json_store.py#L46)*

EntitySpine's tiered storage architecture (Principle #5) provides SQLite
    as the T1 backend: more capable than T0 (JSON) but still zero-dependency.
    This is the sweet spot for most use cases:
    - Indexed lookups by CIK, ticker, entity_id
    - LIKE pattern search for partial name matching
    - Proper foreign key constraints
    - Concurrent read access
    - Scales to ~500K entities with good performance
    
    The Facade Pattern orchestrates specialized repositories (EntityRepository,
    SecurityRepository, etc.) for clean separation of concerns while presenting
    a unified 92+ method API for backward compatibility.
    
    **TIER CAPABILITY HONESTY**: Like T0, SQLite does NOT support true temporal
    queries (as_of returns current data with warning). For temporal queries,
    use T2 (DuckDB) or T3 (PostgreSQL with temporal tables).

*Source: [`SqliteStore`](/app/projects/entityspine/src/entityspine/stores/sqlite/storage.py#L77)*


---

*18 principles extracted from 7 sections*

*Generated by [doc-automation](https://github.com/your-org/py-sec-edgar/tree/main/spine-core/packages/doc-automation)*