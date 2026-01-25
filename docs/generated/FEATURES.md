# FEATURES

**What This Project Can Do**

*Auto-generated from code annotations on 2026-02-02*

---

## General

### FinancialObservationStore

- Append-only storage (immutable observations)
- Partitioned by entity_id and fiscal_year for efficient queries
- Supports full provenance tracking

*From [`FinancialObservationStore`](/app/projects/entityspine/src/entityspine/data/observation_store.py#L235)*

### ParquetEntityStore

- Columnar compression for 5-10x space savings
- Predicate pushdown for fast queries
- Partitioning by source type or entity type
- Metadata tracking for each ingestion

Directory Structure:
    base_path/
        entities.parquet
        securities.parquet
        listings.parquet
        identifiers.parquet
        metadata/
            sources.json
            ingestion_log.json

*From [`ParquetEntityStore`](/app/projects/entityspine/src/entityspine/data/parquet_store.py#L24)*

### SecDataLoader

- Downloads company_tickers.json from SEC
- Caches locally to avoid repeated downloads
- Respects cache expiry (default 24 hours)
- Handles gzip-compressed responses

Args:
    store: EntitySpine store to load data into.
    cache_dir: Directory for cached data files.
    cache_max_age_hours: How long to keep cached data (default 24h).
    user_agent: User-Agent for SEC requests.

Example:
    >>> from entityspine import SqliteStore
    >>> from entityspine.loaders.sec_loader import SecDataLoader
    >>> 
    >>> store = SqliteStore(":memory:")
    >>> store.initialize()
    >>> 
    >>> loader = SecDataLoader(store)
    >>> loader.ensure_loaded()
    >>> 
    >>> print(store.count_entities())  # ~14,000 entities

*From [`SecDataLoader`](/app/projects/entityspine/src/entityspine/loaders/sec_loader.py#L52)*

### AuditManager

- Records all changes with before/after state
- Supports point-in-time queries
- Enables reversion to previous states
- Notifies listeners of changes

*From [`AuditManager`](/app/projects/entityspine/src/entityspine/services/audit.py#L400)*

### GLEIFSource

- Supports CSV and JSON formats
- Handles gzip/zip compression
- Bronze snapshot metadata capture
- Incremental download support (delta files)

Attributes:
    name: Source identifier ("gleif-lei")
    
Example:
    >>> source = GLEIFSource()
    >>> records = await source.fetch()
    >>> print(f"Got {len(records)} LEI records")
    
    # Find NVIDIA
    >>> nvidia = next(r for r in records if 'NVIDIA' in r['legal_name'].upper())
    >>> print(f"NVIDIA LEI: {nvidia['lei']}")

Note:
    The full Golden Copy is ~500MB compressed, ~2GB uncompressed.
    For testing, use a smaller sample file.

*From [`GLEIFSource`](/app/projects/entityspine/src/entityspine/sources/gleif.py#L339)*

### LEIRegistry

- O(1) lookup by LEI
- Search by name
- Filter by country, status
- Get related entities (successor, etc.)

Example:
    >>> registry = LEIRegistry()
    >>> await registry.load_from_source(limit=10000)  # Load sample
    >>>
    >>> nvidia = registry.get("549300S4KLFTLO7GSQ80")
    >>> print(f"NVIDIA: {nvidia.legal_name}")
    >>>
    >>> us_entities = registry.get_by_country("US")
    >>> print(f"US entities: {len(us_entities)}")

*From [`LEIRegistry`](/app/projects/entityspine/src/entityspine/sources/gleif.py#L890)*

### GLEIFMICLEISource

- Automatic download and parsing
- Bronze snapshot storage
- Provenance tracking

Attributes:
    name: Source identifier ("gleif-mic-lei")
    url: Download URL
    
Example:
    >>> source = GLEIFMICLEISource()
    >>> mappings = await source.fetch()
    >>> 
    >>> # Build MIC->LEI lookup
    >>> mic_to_lei = {m['mic']: m['lei'] for m in mappings}
    >>> print(f"NYSE LEI: {mic_to_lei.get('XNYS')}")

*From [`GLEIFMICLEISource`](/app/projects/entityspine/src/entityspine/sources/gleif_mic_lei.py#L128)*

### ISO10383Source

- Automatic retry with exponential backoff
- Content hashing for change detection
- ETag/Last-Modified for conditional requests
- Bronze snapshot metadata capture

Attributes:
    name: Source identifier ("iso10383-mic")
    csv_url: URL for CSV download
    format: Download format (csv, xml)
    
Example:
    >>> source = ISO10383Source()
    >>> records = await source.fetch()
    >>> print(f"Got {len(records)} MIC codes")
    
    # Check for specific MIC
    >>> nyse = next(r for r in records if r['mic'] == 'XNYS')
    >>> print(f"NYSE: {nyse['name']}")

*From [`ISO10383Source`](/app/projects/entityspine/src/entityspine/sources/iso10383.py#L252)*

### MICRegistry

- O(1) lookup by MIC code
- Get all segments for an operating MIC
- Filter by country, status, type
- Get operating MIC hierarchy

Example:
    >>> registry = MICRegistry()
    >>> await registry.load_from_source()
    >>>
    >>> nyse = registry.get("XNYS")
    >>> print(f"NYSE: {nyse.name}")
    >>>
    >>> nasdaq_segments = registry.get_segments("XNAS")
    >>> print(f"NASDAQ has {len(nasdaq_segments)} segments")

*From [`MICRegistry`](/app/projects/entityspine/src/entityspine/sources/iso10383.py#L601)*

### EntitySpineModel

- Immutable by default (frozen=True)
- Strict validation
- JSON-compatible serialization
- Extra fields forbidden

*From [`EntitySpineModel`](/app/projects/entityspine/src/entityspine/adapters/pydantic/base.py#L18)*

## Identifier Management

### IdentifierClaim

- Multi-vendor crosswalks via namespace (SEC, FACTSET, BLOOMBERG)
    - Temporal validity (valid_from/valid_to) separate from capture time
    - Scheme-scope enforcement (CIK→entity, ISIN→security, TICKER→listing)
    - Confidence scoring for conflict resolution
    - Auto-normalization of identifier values
    - Supersession support for identifier changes
    - Sanctions list support (OFAC_SDN, UN_SANCTIONS)

*From [`IdentifierClaim`](/app/projects/entityspine/src/entityspine/domain/claim.py#L26)*

## Domain Models

### Entity

- Immutable (frozen dataclass) for thread safety and hashability
    - NO identifier fields - use IdentifierClaim for CIK, LEI, EIN
    - NO ticker field - tickers belong on Listing (exchange-specific)
    - Redirect support for entity merges (non-destructive resolution)
    - Alias tuple for alternative names (also immutable)
    - Provenance tracking via source_system and source_id
    - Type classification (ORGANIZATION, PERSON, FUND, GOVERNMENT)

*From [`Entity`](/app/projects/entityspine/src/entityspine/domain/entity.py#L27)*

### Listing

- Immutable (frozen dataclass) for thread safety and hashability
    - TICKER IS HERE - normalized to uppercase, validated format
    - Temporal validity via start_date/end_date for point-in-time queries
    - MIC (ISO 10383) for unambiguous exchange identification
    - Primary listing flag for multi-exchange securities
    - Auto-normalization of ticker and MIC on construction
    - Status tracking (ACTIVE, DELISTED, SUSPENDED)

*From [`Listing`](/app/projects/entityspine/src/entityspine/domain/listing.py#L51)*

### Security

- Immutable (frozen dataclass) for thread safety and hashability
    - NO identifier fields - use IdentifierClaim for ISIN, CUSIP, SEDOL, FIGI
    - Entity link (entity_id) is required - every Security has an issuer
    - Type classification (COMMON_STOCK, PREFERRED, BOND, ETF, OPTION)
    - Currency support for primary trading currency
    - Status tracking (ACTIVE, DELISTED, MATURED, SUSPENDED)
    - Provenance via source_system and source_id

*From [`Security`](/app/projects/entityspine/src/entityspine/domain/security.py#L40)*

## Graph Models

### Relationship

- Polymorphic endpoints via NodeRef (any node type)
    - Temporal validity (valid_from/valid_to) for point-in-time queries
    - Evidence pointers (filing_id, section_id, excerpt_hash)
    - Human-readable snippet for quick context
    - Confidence scoring for relationship reliability
    - Subtype field for finer classification
    - Metrics dict for additional quantitative data
    - Immutable (frozen dataclass) for thread safety

*From [`Relationship`](/app/projects/entityspine/src/entityspine/domain/graph.py#L994)*

## Broker-Dealer Model

### BrokerDealer

- **CRD Identification**: FINRA Central Registration Depository number
    - **SEC Registration**: SEC file number tracking (8-XXXXX format)
    - **Clearing Relationships**: Self-clearing vs fully-disclosed
    - **Exchange Memberships**: Via ExchangeMembership model
    - **Business Model**: Retail, institutional, clearing, introducing
    - **Temporal Validity**: valid_from/valid_to for BD lifecycle
    - **Entity Linkage**: FK to Entity for legal identity joins

*From [`BrokerDealer`](/app/projects/entityspine/src/entityspine/domain/markets.py#L584)*

## Clearing Model

### Clearinghouse

- **CCP Types**: Clearinghouses, depositories, and CCPs
    - **SEC Registration**: SEC file number for registered clearing agencies
    - **SIFMU Status**: Systemically Important Financial Market Utility flag
    - **Asset Classes**: What instruments are cleared (equities, options, fixed)
    - **Settlement Cycle**: T+1, T+2, or other settlement timing
    - **Temporal Validity**: valid_from/valid_to for clearinghouse lifecycle
    - **Entity Linkage**: FK to Entity for legal identity joins

*From [`Clearinghouse`](/app/projects/entityspine/src/entityspine/domain/markets.py#L1013)*

## Market Relationships

### ClearingMembership

- **Membership Types**: FULL_CLEARING, CORRESPONDENT, SPONSORED
    - **Asset Class Scope**: What can be cleared under this membership
    - **Temporal Validity**: valid_from/valid_to for membership lifecycle
    - **Entity + BD Links**: Can link to Entity and/or BrokerDealer

*From [`ClearingMembership`](/app/projects/entityspine/src/entityspine/domain/markets.py#L1254)*

### ExchangeMembership

- **MPID Identification**: Market Participant Identifier on exchange
    - **Membership Types**: TRADING_MEMBER, MARKET_MAKER, SPECIALIST
    - **Trading Rights**: Equity, options, market making flags
    - **DMM Status**: Designated Market Maker role (NYSE)
    - **Asset Class Scope**: What can be traded under this membership
    - **Temporal Validity**: valid_from/valid_to for membership lifecycle

*From [`ExchangeMembership`](/app/projects/entityspine/src/entityspine/domain/markets.py#L1394)*

## Financial Observations

### Observation

- MetricSpec for structured metric identification (EPS diluted GAAP)
    - FiscalPeriod for unambiguous period specification
    - ValueWithUnits for normalized + raw value preservation
    - Triple time semantics (period, as_of, captured_at)
    - ProvenanceRef for document-level lineage
    - SourceKey for field-level lineage
    - EstimateInfo for broker/consensus metadata
    - Supersession chain for revision tracking
    - Deterministic observation_key for deduplication
    - Immutable (frozen dataclass) for thread safety

*From [`Observation`](/app/projects/entityspine/src/entityspine/domain/observation.py#L602)*

## Pipeline Execution

### ExecutionContext

- Automatic UUID generation for execution_id
    - Parent-child linking via parent_execution_id
    - Batch grouping via batch_id for related operations
    - Workflow naming for human-readable identification
    - Metadata dict for extensible context (source, params, etc.)
    - Elapsed time tracking via elapsed_seconds property
    - Immutable child() method for safe sub-context creation

*From [`ExecutionContext`](/app/projects/entityspine/src/entityspine/domain/workflow.py#L132)*

## Result Pattern

### Ok

- Immutable (frozen dataclass) for thread safety
    - Generic over T for type-safe value extraction
    - Monadic operations: map, flat_map, and_then
    - Safe unwrapping: unwrap_or, unwrap_or_else
    - Composable with Err via Result[T] union type

*From [`Ok`](/app/projects/entityspine/src/entityspine/domain/workflow.py#L381)*

### Err

- Immutable (frozen dataclass) for thread safety
    - Preserves full exception with traceback
    - map() is no-op (preserves error)
    - map_err() transforms the error
    - or_else() enables recovery attempts
    - unwrap() re-raises the original exception

*From [`Err`](/app/projects/entityspine/src/entityspine/domain/workflow.py#L521)*

## Entity Resolution

### FuzzyMatcher

- Zero dependencies (pure Python implementation)
    - Optional 10x speedup with rapidfuzz
    - Company name normalization (removes Inc, Corp, Ltd, etc.)
    - Configurable similarity weights
    - Configurable minimum threshold
    - Single and batch matching APIs
    - LRU cache for normalization (10K entry cache)
    - Thread-safe (stateless operations)

*From [`FuzzyMatcher`](/app/projects/entityspine/src/entityspine/services/fuzzy.py#L340)*

### EntityResolver

- Zero-config operation (auto-downloads SEC data on first use)
    - Single resolve() method for ALL identifier types
    - Auto-detection of identifier type (CIK, ISIN, ticker, name)
    - Temporal resolution with as_of parameter
    - MIC disambiguation for tickers
    - Fuzzy name matching with configurable threshold
    - Merged entity redirect following
    - Returns ResolutionResult with candidates and confidence
    - Thread-safe and reusable instance

*From [`EntityResolver`](/app/projects/entityspine/src/entityspine/services/resolver.py#L87)*

## Graph Traversal

### GraphService

- Corporate structure traversal (subsidiaries, parent, ultimate parent)
    - People queries (officers, directors, CEO, board members)
    - Path finding between entities (BFS with max depth)
    - Network expansion (N-hop neighborhood)
    - Temporal filtering (as_of for point-in-time queries)
    - Rich result types (OfficerInfo, RelatedEntity, EntityPath, EntityNetwork)
    - Cycle detection to prevent infinite loops
    - Depth limiting for performance control

*From [`GraphService`](/app/projects/entityspine/src/entityspine/services/graph_service.py#L132)*

## Storage Backends

### JsonEntityStore

- Zero external dependencies (stdlib json/urllib)
    - In-memory storage for fast access
    - Optional JSON file persistence
    - SEC company_tickers.json loader (downloads automatically)
    - Full Entity → Security → Listing hierarchy
    - IdentifierClaim support for CIK, ticker, etc.
    - Indexed lookups by CIK, ticker, name
    - Returns DOMAIN dataclasses (not Pydantic/ORM models)

Limitations (Tier 0 Honesty):
    - as_of parameter IGNORED (no temporal data)
    - Exact match search only (no fuzzy)
    - Max recommended: 50,000 entities
    - No concurrent write safety

*From [`JsonEntityStore`](/app/projects/entityspine/src/entityspine/stores/json_store.py#L46)*

### SqliteStore

- Zero external dependencies (stdlib sqlite3)
    - Repository pattern for clean separation of concerns
    - Facade pattern for unified API
    - Full Entity → Security → Listing hierarchy
    - 20+ domain tables with proper foreign keys
    - Indexed lookups (CIK, ticker, entity_id, etc.)
    - LIKE pattern search for names
    - SEC data auto-loader (downloads + caches)
    - Thread-safe read access
    - Returns DOMAIN dataclasses (not ORM models)

Limitations (Tier 1 Honesty):
    - as_of parameter IGNORED (no temporal data)
    - LIKE-based search (not full-text search)
    - Single-writer (SQLite limitation)
    - Max recommended: 500,000 entities

*From [`SqliteStore`](/app/projects/entityspine/src/entityspine/stores/sqlite/storage.py#L77)*


---

*177 features documented across 13 categories*

*Generated by [doc-automation](https://github.com/your-org/py-sec-edgar/tree/main/spine-core/packages/doc-automation)*