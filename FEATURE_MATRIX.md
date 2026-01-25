# EntitySpine v0.3.3 Feature Matrix

**Status Key**: ✅ Complete | ⏳ In Progress | 📋 Planned | ❌ Not Supported

---

## Core Functionality

| Feature | Status | Tier 0<br>(JSON) | Tier 1<br>(SQLite) | Tier 2<br>(DuckDB) | Tier 3+<br>(Postgres) | Notes |
|---------|--------|----------|-----------|-----------|-------------|-------|
| **Entity Storage** | ✅ | ✅ | ✅ | 📋 | 📋 | Canonical entity records |
| **Security Storage** | ✅ | ✅ | ✅ | 📋 | 📋 | Tradeable instruments |
| **Listing Storage** | ✅ | ✅ | ✅ | 📋 | 📋 | Exchange-specific tickers |
| **Identifier Claims** | ✅ | ✅ | ✅ | 📋 | 📋 | Multi-source identifiers with provenance |
| **Entity Resolution** | ✅ | ✅ | ✅ | 📋 | 📋 | Resolve ticker/CIK/name to entity |
| **Fuzzy Name Matching** | ✅ | ⚠️ | ✅ | 📋 | 📋 | Levenshtein distance, soundex |
| **Search Entities** | ✅ | ⚠️ | ✅ | 📋 | 📋 | Multi-identifier search |
| **Temporal Queries** | ❌ | ❌ | ❌ | 📋 | ✅ | as-of, time-travel queries |
| **Bulk Import** | ✅ | ✅ | ✅ | 📋 | 📋 | Batch loading for performance |
| **Export to JSON** | ✅ | ✅ | ✅ | 📋 | 📋 | Portable data export |

---

## Knowledge Graph

| Feature | Status | Tier 0 | Tier 1 | Tier 2 | Tier 3+ | Notes |
|---------|--------|--------|--------|--------|---------|-------|
| **Person Nodes** | ✅ | ✅ | ✅ | 📋 | 📋 | Executives, directors, beneficial owners |
| **Asset Nodes** | ✅ | ✅ | ✅ | 📋 | 📋 | Real estate, equipment, IP |
| **Contract Nodes** | ✅ | ✅ | ✅ | 📋 | 📋 | Material agreements |
| **Product Nodes** | ✅ | ✅ | ✅ | 📋 | 📋 | Products/services |
| **Brand Nodes** | ✅ | ✅ | ✅ | 📋 | 📋 | Brand identities |
| **Event Nodes** | ✅ | ✅ | ✅ | 📋 | 📋 | Discrete business events |
| **Case Nodes** | ✅ | ✅ | ✅ | 📋 | 📋 | Legal proceedings |
| **Address Nodes** | ✅ | ✅ | ✅ | 📋 | 📋 | Physical locations |
| **Geo Nodes** | ✅ | ✅ | ✅ | 📋 | 📋 | Countries, states, cities |
| **Role Assignments** | ✅ | ✅ | ✅ | 📋 | 📋 | Person→Org roles (CEO, CFO) |
| **Entity Relationships** | ✅ | ✅ | ✅ | 📋 | 📋 | Parent/subsidiary, supplier/customer |
| **Generic Relationships** | ✅ | ✅ | ✅ | 📋 | 📋 | Node→Node edges with evidence |
| **Graph Traversal** | ⏳ | ❌ | ⚠️ | 📋 | ✅ | BFS/DFS, shortest path |
| **Subgraph Extraction** | ⏳ | ❌ | ⚠️ | 📋 | ✅ | Extract connected components |

---

## Market Infrastructure

| Feature | Status | Tier 0 | Tier 1 | Tier 2 | Tier 3+ | Notes |
|---------|--------|--------|--------|--------|---------|-------|
| **Exchange Models** | ✅ | ✅ | ✅ | 📋 | 📋 | NYSE, NASDAQ, etc. |
| **BrokerDealer Models** | ✅ | ✅ | ✅ | 📋 | 📋 | FINRA registered firms |
| **Clearinghouse Models** | ✅ | ✅ | ✅ | 📋 | 📋 | DTCC, OCC, etc. |
| **Market Participant Models** | ✅ | ✅ | ✅ | 📋 | 📋 | Market makers, specialists |
| **Exchange Segments** | ✅ | ✅ | ✅ | 📋 | 📋 | Operating vs. segment MICs |
| **Reference Data Exports** | ✅ | ✅ | ✅ | 📋 | 📋 | ISO 10383 MIC codes, venue mappings |

---

## Data Sources

| Source | Status | Auto-Load | Format | Notes |
|--------|--------|-----------|--------|-------|
| **SEC company_tickers.json** | ✅ | ✅ | JSON | ~14,000 public companies |
| **SEC company_tickers_exchange.json** | ✅ | ✅ | JSON | With exchange/MIC data |
| **GLEIF LEI Data** | ✅ | ⏳ | XML/CSV | Legal Entity Identifiers |
| **ISO 3166 Countries** | ✅ | ✅ | CSV | Country codes |
| **ISO 4217 Currencies** | ✅ | ✅ | XML/CSV | Currency codes |
| **ISO 10383 MIC Codes** | ✅ | ✅ | CSV | Exchange identifiers |
| **GLEIF MIC-LEI Mapping** | ✅ | ⏳ | CSV | Exchange→LEI mapping |
| **Custom CSV Import** | ⏳ | ❌ | CSV | User-provided data |
| **Parquet Import** | ⏳ | ❌ | Parquet | Analytics integration |

---

## Identifier Schemes

| Scheme | Status | Validation | Normalization | Checksum | Notes |
|--------|--------|------------|---------------|----------|-------|
| **CIK** | ✅ | ✅ | ✅ | ❌ | SEC Central Index Key |
| **CUSIP** | ✅ | ✅ | ✅ | ✅ | 9-digit security identifier |
| **ISIN** | ✅ | ✅ | ✅ | ✅ | International security identifier |
| **LEI** | ✅ | ✅ | ✅ | ✅ | Legal Entity Identifier |
| **FIGI** | ✅ | ✅ | ✅ | ✅ | Financial Instrument Global ID |
| **SEDOL** | ✅ | ✅ | ✅ | ✅ | 7-character security identifier |
| **MIC** | ✅ | ✅ | ✅ | ❌ | Market Identifier Code (ISO 10383) |
| **TICKER** | ✅ | ✅ | ✅ | ❌ | Exchange ticker symbol |
| **EIN** | ✅ | ✅ | ✅ | ❌ | Employer Identification Number |
| **PERMID** | ⏳ | ⏳ | ⏳ | ❌ | Refinitiv PermID |
| **BBG_ID** | ⏳ | ⏳ | ⏳ | ❌ | Bloomberg ID |

---

## Integration Points

| Integration | Status | Direction | Protocol | Notes |
|-------------|--------|-----------|----------|-------|
| **py-sec-edgar** | ✅ | Inbound | Python API | Filing facts ingestion |
| **FeedSpine** | ✅ | Bidirectional | Python API | Feed normalization |
| **Pydantic Adapters** | ✅ | Wrapper | Python API | Validation layer |
| **SQLModel ORM** | ✅ | Wrapper | Python API | ORM layer |
| **FastAPI REST** | ✅ | Outbound | HTTP/JSON | Optional API service |
| **CLI Tools** | ✅ | Outbound | Command-line | Data management scripts |
| **Parquet Export** | ⏳ | Outbound | Parquet | Analytics integration |
| **Neo4j Export** | ✅ | Outbound | Cypher | Graph database sync |
| **Elasticsearch Sync** | ✅ | Outbound | REST API | Search index sync |

---

## API Endpoints (Optional [api] Extra)

| Endpoint | Method | Status | Auth | Rate Limit | Notes |
|----------|--------|--------|------|------------|-------|
| `/entities` | GET | ✅ | ❌ | ❌ | Search entities |
| `/entities/{id}` | GET | ✅ | ❌ | ❌ | Get entity by ID |
| `/entities/cik/{cik}` | GET | ✅ | ❌ | ❌ | Get entity by CIK |
| `/entities/ticker/{ticker}` | GET | ✅ | ❌ | ❌ | Get entity by ticker |
| `/entities/{id}/claims` | GET | ✅ | ❌ | ❌ | Get identifier claims |
| `/entities/{id}/relationships` | GET | ✅ | ❌ | ❌ | Get relationships |
| `/resolve` | POST | ✅ | ❌ | ❌ | Resolve identifier |
| `/health` | GET | ✅ | ❌ | ❌ | Health check |
| `/metrics` | GET | ⏳ | ❌ | ❌ | Prometheus metrics |
| `/docs` | GET | ✅ | ❌ | ❌ | OpenAPI documentation |

---

## Validation & Normalization

| Feature | Status | Notes |
|---------|--------|-------|
| **CIK Zero-Padding** | ✅ | Normalize to 10 digits |
| **CUSIP Validation** | ✅ | Mod-10 checksum |
| **ISIN Validation** | ✅ | Mod-10 checksum |
| **LEI Validation** | ✅ | ISO 17442 format + checksum |
| **FIGI Validation** | ✅ | OpenFIGI format |
| **SEDOL Validation** | ✅ | Weighted checksum |
| **Ticker Normalization** | ✅ | Uppercase, trim whitespace |
| **Name Normalization** | ✅ | Remove Corp/Inc suffixes, handle special chars |
| **Fuzzy Name Matching** | ✅ | Levenshtein distance, soundex |
| **Duplicate Detection** | ⏳ | Clustering-based deduplication |

---

## Corporate Actions

| Action Type | Status | Tracking | Historical | Notes |
|-------------|--------|----------|------------|-------|
| **Name Change** | ✅ | ✅ | ⏳ | Track entity name changes |
| **Ticker Change** | ✅ | ✅ | ⏳ | Track ticker symbol changes |
| **Merger** | ✅ | ✅ | ⏳ | Mark merged entities, redirect |
| **Acquisition** | ✅ | ✅ | ⏳ | Parent/subsidiary relationships |
| **Spinoff** | ✅ | ✅ | ⏳ | New entity creation |
| **Delisting** | ✅ | ✅ | ⏳ | Mark listing status inactive |
| **Relisting** | ✅ | ✅ | ⏳ | Reactivate listing |
| **Bankruptcy** | ✅ | ✅ | ⏳ | Mark entity status |

---

## Data Quality

| Feature | Status | Tier 0 | Tier 1 | Tier 2 | Tier 3+ | Notes |
|---------|--------|--------|--------|--------|---------|-------|
| **Duplicate Detection** | ⏳ | ❌ | ⏳ | 📋 | 📋 | Find potential duplicates |
| **Conflict Resolution** | ✅ | ⚠️ | ✅ | 📋 | 📋 | Handle identifier conflicts |
| **Data Auditing** | ✅ | ❌ | ✅ | 📋 | 📋 | Data quality reports |
| **Missing Data Reports** | ✅ | ❌ | ✅ | 📋 | 📋 | Identify incomplete records |
| **Confidence Scoring** | ✅ | ✅ | ✅ | 📋 | 📋 | Track claim confidence |
| **Source Tracking** | ✅ | ✅ | ✅ | 📋 | 📋 | Provenance for all claims |
| **Verification Status** | ✅ | ✅ | ✅ | 📋 | 📋 | Mark claims as verified |

---

## Performance

| Metric | Tier 0<br>(JSON) | Tier 1<br>(SQLite) | Tier 2<br>(DuckDB) | Tier 3+<br>(Postgres) | Notes |
|--------|----------|-----------|-----------|-------------|-------|
| **Max Entities** | ~10K | ~1M | ~100M | Unlimited | Practical limits |
| **Insert Speed** | Slow | Fast | Very Fast | Fast | Bulk operations |
| **Search Speed** | Slow | Fast | Very Fast | Very Fast | Full-text search |
| **Concurrent Writes** | ❌ | ⚠️ | ✅ | ✅ | WAL mode helps SQLite |
| **Concurrent Reads** | ✅ | ✅ | ✅ | ✅ | All tiers support |
| **Index Support** | ❌ | ✅ | ✅ | ✅ | Automatic indexing |

---

## Observability

| Feature | Status | Notes |
|---------|--------|-------|
| **Structured Logging** | ✅ | Python logging module |
| **Metrics (Prometheus)** | ⏳ | Planned for API |
| **Tracing** | ❌ | Not yet implemented |
| **Health Checks** | ✅ | API health endpoint |
| **Performance Profiling** | ⏳ | Development tools |

---

## Testing

| Category | Tests | Coverage | Status |
|----------|-------|----------|--------|
| **Unit Tests** | 340 | 60% | ✅ |
| **Integration Tests** | 150 | 30% | ✅ |
| **Source Tests** | 40 | 70% | ✅ |
| **API Tests** | 18 | 50% | ✅ |
| **Total** | **548** | **40%** | ✅ |

---

## Documentation

| Document | Status | Location | Notes |
|----------|--------|----------|-------|
| **README** | ✅ | README.md | Comprehensive getting started |
| **API Reference** | ⏳ | docs/ | Auto-generated from docstrings |
| **Architecture Guide** | ✅ | docs/architecture/ | Tier system, design patterns |
| **Contributing Guide** | ✅ | CONTRIBUTING.md | Development setup |
| **Changelog** | ✅ | CHANGELOG.md | Version history |
| **Examples** | ✅ | examples/ | Usage examples |
| **Release Audit** | ✅ | RELEASE_AUDIT_REPORT.md | v0.3.3 release audit |
| **Guardrails** | ✅ | docs/GUARDRAILS.md | Code quality standards |

---

## Deployment

| Option | Status | Dependencies | Use Case |
|--------|--------|--------------|----------|
| **pip install** | ✅ | None (core) | Standard installation |
| **Docker Image** | ⏳ | Docker | Containerized deployment |
| **Docker Compose** | ✅ | Docker | Multi-container setup |
| **Kubernetes** | 📋 | K8s | Production orchestration |
| **Serverless** | ❌ | - | Not yet supported |

---

## License & Support

| Item | Details |
|------|---------|
| **License** | MIT |
| **Version** | 0.3.3 |
| **Python Support** | 3.11, 3.12, 3.13 |
| **Stability** | Alpha (pre-1.0) |
| **Breaking Changes** | Possible until v1.0 |
| **Commercial Support** | Not available |
| **Community Support** | GitHub Issues/Discussions |

---

## Legend

- ✅ **Complete**: Fully implemented and tested
- ⏳ **In Progress**: Partially implemented or experimental
- 📋 **Planned**: Roadmapped for future release
- ❌ **Not Supported**: Not currently planned
- ⚠️ **Limited**: Works with restrictions or performance caveats

---

**Last Updated**: January 31, 2025  
**Version**: v0.3.3  
**Status**: Production-ready for Tier 0-1 use cases
