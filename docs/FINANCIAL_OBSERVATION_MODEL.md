# EntitySpine Architecture & Financial Observation Model

## Table of Contents

1. [EntitySpine Overview](#entityspine-overview)
2. [Core Domain Models](#core-domain-models)
3. [The Identifier Problem](#the-identifier-problem)
4. [Schema Detection & Auto-Loading](#schema-detection--auto-loading)
5. [Financial Observations](#financial-observations)
6. [Complete Architecture Diagram](#complete-architecture-diagram)
7. [Usage Examples](#usage-examples)

---

## EntitySpine Overview

**EntitySpine** is a **multi-source entity resolution system** for financial data. It solves the fundamental problem: *"Is this the same company across FactSet, Bloomberg, SEC, and Reuters?"*

### The Problem

Financial data comes from many sources, each with their own identifiers:

| Source | Identifier | Example (Apple) |
|--------|------------|-----------------|
| SEC EDGAR | CIK | 0000320193 |
| FactSet | FactSet Entity ID | 000C7F-E |
| Bloomberg | BBUID | EQ0010169500001000 |
| Thomson Reuters | PermID | 4295905573 |
| Standard | CUSIP | 037833100 |
| Standard | ISIN | US0378331005 |
| Standard | LEI | HWUPKR0MPOU8FGXBT394 |
| Exchange | Ticker | AAPL (NASDAQ) |

**EntitySpine creates a unified view** by:
1. Creating canonical `Entity`, `Security`, and `Listing` records
2. Linking all identifiers via `IdentifierClaim` with full provenance
3. Tracking which source said what, and when

### Core Design Principles

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     ENTITYSPINE DESIGN PRINCIPLES                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. IMMUTABLE DOMAIN MODELS                                                 │
│     - All models are frozen dataclasses                                     │
│     - Thread-safe by design                                                 │
│     - Updates create new instances                                          │
│                                                                             │
│  2. IDENTIFIERS ARE CLAIMS, NOT PROPERTIES                                  │
│     - Entity has NO cik, lei, ein fields                                    │
│     - Security has NO cusip, isin, sedol fields                             │
│     - All identifiers live in IdentifierClaim with provenance               │
│                                                                             │
│  3. SCHEME-SCOPE ENFORCEMENT                                                │
│     - CIK, LEI, EIN → Entity-scoped                                         │
│     - CUSIP, ISIN, SEDOL, FIGI → Security-scoped                           │
│     - TICKER → Listing-scoped                                               │
│                                                                             │
│  4. MULTI-VENDOR CROSSWALKS                                                 │
│     - VendorNamespace distinguishes sources                                 │
│     - Same identifier from different vendors = different claims             │
│     - Track confidence and validity periods                                 │
│                                                                             │
│  5. FULL PROVENANCE                                                         │
│     - Every value knows where it came from                                  │
│     - captured_at vs valid_from/valid_to time semantics                     │
│     - Source system and source ID tracked                                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Core Domain Models

### Entity → Security → Listing Hierarchy

```
                              ┌─────────────────────────────────────┐
                              │              ENTITY                 │
                              │  (Legal/Organizational Identity)    │
                              ├─────────────────────────────────────┤
                              │  entity_id:      "01HXYZ..."       │
                              │  primary_name:   "Apple Inc."      │
                              │  entity_type:    ORGANIZATION      │
                              │  status:         ACTIVE            │
                              │  jurisdiction:   "US-CA"           │
                              │  sic_code:       "3571"            │
                              └──────────────┬──────────────────────┘
                                             │
                                             │ 1:N (Entity issues Securities)
                                             │
               ┌─────────────────────────────┼─────────────────────────────┐
               │                             │                             │
               ▼                             ▼                             ▼
┌──────────────────────────┐  ┌──────────────────────────┐  ┌──────────────────────────┐
│        SECURITY          │  │        SECURITY          │  │        SECURITY          │
│     (Common Stock)       │  │    (Preferred Stock)     │  │      (Bond)              │
├──────────────────────────┤  ├──────────────────────────┤  ├──────────────────────────┤
│  security_id: "01HAB..." │  │  security_id: "01HCD..." │  │  security_id: "01HEF..." │
│  entity_id:   "01HXYZ.." │  │  entity_id:   "01HXYZ.." │  │  entity_id:   "01HXYZ.." │
│  security_type: COMMON   │  │  security_type: PREF     │  │  security_type: BOND     │
│  currency:    "USD"      │  │  currency:    "USD"      │  │  currency:    "USD"      │
└────────────┬─────────────┘  └──────────────────────────┘  └──────────────────────────┘
             │
             │ 1:N (Security trades on Exchanges)
             │
      ┌──────┴──────┐
      │             │
      ▼             ▼
┌───────────────┐ ┌───────────────┐
│   LISTING     │ │   LISTING     │
│   (NASDAQ)    │ │   (Frankfurt) │
├───────────────┤ ├───────────────┤
│  ticker: AAPL │ │  ticker: APC  │
│  mic:   XNAS  │ │  mic:   XFRA  │
│  is_primary:T │ │  is_primary:F │
└───────────────┘ └───────────────┘
```

### IdentifierClaim - The Source of Truth

**Critical insight**: Identifiers are NOT properties of entities. They are **claims made by sources**.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          IDENTIFIER CLAIM                                   │
│  "Source X says Entity Y has identifier Z during time period T"            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  claim_id:     "01HCLAIM..."        │  Unique ID for this claim            │
│                                                                             │
│  ─── TARGET (exactly one) ───                                               │
│  entity_id:    "01HXYZ..."          │  For CIK, LEI, EIN                   │
│  security_id:  "01HABC..."          │  For CUSIP, ISIN, SEDOL, FIGI        │
│  listing_id:   "01HLIST..."         │  For TICKER                          │
│                                                                             │
│  ─── IDENTIFIER ───                                                         │
│  scheme:       CUSIP                │  Type of identifier                   │
│  value:        "037833100"          │  The normalized value                 │
│                                                                             │
│  ─── PROVENANCE ───                                                         │
│  namespace:    FACTSET              │  Which vendor asserted this          │
│  source:       "ff_security_master" │  Specific dataset                    │
│  source_ref:   "000C7F-E"           │  ID in the source system             │
│  captured_at:  2025-01-15 10:30:00  │  When we captured this               │
│  confidence:   0.95                 │  How confident we are                │
│                                                                             │
│  ─── VALIDITY ───                                                           │
│  valid_from:   2020-01-01           │  When identifier became valid        │
│  valid_to:     None                 │  Still valid                         │
│  status:       ACTIVE               │  Claim status                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Scheme-Scope Rules

Each identifier type has a defined scope:

| Scheme | Scope | Example | Notes |
|--------|-------|---------|-------|
| **CIK** | Entity | 0000320193 | SEC Central Index Key |
| **LEI** | Entity | HWUPKR0MPOU8FGXBT394 | Legal Entity Identifier |
| **EIN** | Entity | 94-2404110 | IRS Employer ID |
| **DUNS** | Entity | 00-136-8083 | Dun & Bradstreet |
| **CUSIP** | Security | 037833100 | Committee on Uniform Security ID |
| **ISIN** | Security | US0378331005 | International Securities ID |
| **SEDOL** | Security | 2046251 | Stock Exchange Daily Official List |
| **FIGI** | Security | BBG000B9XRY4 | Financial Instrument Global ID |
| **TICKER** | Listing | AAPL | Exchange-specific symbol |
| **RIC** | Listing | AAPL.O | Reuters Instrument Code |

---

## The Identifier Problem

### Why This Matters

Consider Apple's common stock across vendors:

```
FACTSET says:
  Entity "Apple Inc." (ID: 000C7F-E) has:
    - CIK: 0000320193
    - CUSIP: 037833100
    - ISIN: US0378331005
    - Ticker: AAPL on NASDAQ

BLOOMBERG says:
  Entity "Apple Inc" (BBUID: EQ0010169500001000) has:
    - CUSIP: 037833100
    - FIGI: BBG000B9XRY4
    - Ticker: AAPL US Equity

SEC EDGAR says:
  Company "APPLE INC" (CIK: 0000320193) filed 10-K on 2024-11-01

REFINITIV says:
  Organization "Apple Inc." (PermID: 4295905573) has:
    - LEI: HWUPKR0MPOU8FGXBT394
    - RIC: AAPL.O
```

### EntitySpine Resolution

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ENTITYSPINE CANONICAL ENTITY                                               │
├─────────────────────────────────────────────────────────────────────────────┤
│  entity_id:    "01H7KCJW2XXXXX"                                            │
│  primary_name: "Apple Inc."                                                 │
│  entity_type:  ORGANIZATION                                                 │
│  jurisdiction: "US-CA"                                                      │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        │                           │                           │
        ▼                           ▼                           ▼
┌───────────────────┐   ┌───────────────────┐   ┌───────────────────┐
│  IDENTIFIER CLAIM │   │  IDENTIFIER CLAIM │   │  IDENTIFIER CLAIM │
│  scheme: CIK      │   │  scheme: LEI      │   │  scheme: CIK      │
│  value: 320193    │   │  value: HWUPKR... │   │  value: 320193    │
│  namespace: SEC   │   │  namespace: GLEIF │   │  namespace: FACTSET│
│  source: EDGAR    │   │  source: LEI-db   │   │  source: ff_sec   │
│  captured: Jan 15 │   │  captured: Jan 16 │   │  captured: Jan 17 │
└───────────────────┘   └───────────────────┘   └───────────────────┘

Same entity, multiple claims, full provenance for each!
```

---

## Schema Detection & Auto-Loading

### The Schema Detector

When you receive a data file, EntitySpine can auto-detect the source:

```python
from entityspine.data.schema_detector import analyze_file, get_loader_suggestion

# Auto-detect file type from column headers
analysis = analyze_file("G:/FACTSET/ff_security_master.csv")

# Result:
# {
#   'vendor': 'factset',
#   'product': 'factset_screening',
#   'data_type': 'security',
#   'confidence': 1.0,
#   'mappings': {
#     'CUSIP Symbol': 'cusip',
#     'ISIN Symbol': 'isin',
#     'Company Name': 'entity_name',
#     ...
#   }
# }
```

### How Detection Works

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SCHEMA DETECTION FLOW                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  INPUT: CSV/TSV File                                                        │
│  ─────────────────                                                          │
│  filename: "ff_security_master_2019-10-14.csv"                             │
│  headers:  [Symbol, Name, CUSIP, FactSet Ind Code, ...]                    │
│                                                                             │
│                              ▼                                              │
│                                                                             │
│  PATTERN MATCHING                                                           │
│  ────────────────                                                           │
│  1. Filename patterns:  "ff_*" → FactSet                                   │
│  2. Column patterns:    "FactSet Ind Code" → FactSet Screening             │
│  3. Prefix patterns:    "FF_SALES" → FactSet Fundamentals                  │
│  4. Required patterns:  "EPS_ACTUAL" + "SALES_ESTIMATE" → Bloomberg EA     │
│                                                                             │
│                              ▼                                              │
│                                                                             │
│  OUTPUT: DetectionResult                                                    │
│  ──────────────────────                                                     │
│  vendor:      FACTSET                                                       │
│  product:     FACTSET_SCREENING                                             │
│  data_type:   SECURITY                                                      │
│  confidence:  0.95                                                          │
│  loader:      iter_factset_csv() + load_factset_batch()                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Vendor Signatures

| Vendor | Filename Patterns | Column Patterns |
|--------|-------------------|-----------------|
| **FactSet** | `ff_*.csv` | `FactSet Industry`, `FDS Ticker`, `Perm. Sec. ID` |
| **Bloomberg** | `BB_*.csv` | `EPS_ACTUAL`, `SALES_ESTIMATE`, `ID_BB_GLOBAL` |
| **Thomson** | `OpenPermID*.ttl` | `tr-org:hasPermId`, `tr-common:hasName` |
| **Compustat** | `compustat*.csv` | `gvkey`, `datadate`, `fyear` |
| **SEC** | `*.txt` | `adsh`, `tag`, `CIK` |

---

## Financial Observations (v2 Architecture)

### The Problem with Simple Models

**Beyond entity resolution**: Once you have canonical entities, you need to track **what financial data** each source reports. But naive models break quickly:

```
PROBLEM: What was Tesla's Q4 2025 EPS?

                     Different answers, all "correct":
┌──────────────────┬────────────────────────────────────────┬─────────┐
│ Source           │ Description                            │ Value   │
├──────────────────┼────────────────────────────────────────┼─────────┤
│ SEC 10-K         │ GAAP, diluted, total operations        │ $0.85   │
│ Press Release    │ Non-GAAP, diluted (ex stock comp)      │ $1.12   │
│ FactSet          │ Vendor-normalized, diluted             │ $1.05   │
│ Bloomberg        │ Vendor-normalized, diluted             │ $1.07   │
│ Analyst estimate │ Non-GAAP (before earnings)             │ $1.08   │
└──────────────────┴────────────────────────────────────────┴─────────┘

A naive model with (metric_code="EPS", variant="non_gaap") can't distinguish:
- Basic vs diluted shares
- GAAP basis vs IFRS basis
- Company adjustments vs vendor normalization
- Total operations vs continuing operations

THIS IS WHY SYSTEMS BREAK.
```

### The v2 Solution: Structured MetricSpec

Replace the ambiguous `(MetricCode, MetricVariant)` pair with orthogonal axes:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          MetricSpec (v2)                                    │
│                                                                             │
│  "EPS (diluted) [vendor-normalized, continuing ops]"                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  code:         MetricCode.EPS           │  WHAT we're measuring            │
│  statement:    StatementType.PER_SHARE  │  Which financial statement       │
│  basis:        AccountingBasis.GAAP     │  Accounting standard             │
│  presentation: Presentation.VENDOR_NORM │  How it's adjusted               │
│  per_share:    PerShareType.DILUTED     │  Share count basis (EPS only)    │
│  scope:        ScopeType.CONTINUING     │  Ops scope (total vs continuing) │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

Each axis is INDEPENDENT - no ambiguity, no conflation.
```

### MetricSpec Axes Explained

| Axis | Values | Description |
|------|--------|-------------|
| **code** | `REVENUE`, `EPS`, `EBITDA`, `NET_INCOME`, `FCF` | Core metric identifier |
| **statement** | `IS` (income), `BS` (balance), `CF` (cash flow), `PS` (per-share) | Which statement |
| **basis** | `GAAP`, `IFRS`, `LOCAL`, `STATUTORY` | Accounting standard |
| **presentation** | `REPORTED`, `COMPANY_ADJ`, `VENDOR_NORM`, `PRO_FORMA` | Adjustment type |
| **per_share** | `BASIC`, `DILUTED`, `WEIGHTED_AVG` | For EPS-like metrics |
| **scope** | `TOTAL`, `CONTINUING`, `DISCONTINUED`, `SEGMENT` | Operations scope |

### Time Semantics: period vs as_of vs captured_at

Three distinct time concepts:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       TIME SEMANTICS                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  period:       What timeframe the number measures                           │
│                "Revenue FOR FY2025"                                         │
│                FiscalPeriod(2025, ANNUAL)                                   │
│                                                                             │
│  as_of:        When it was known (publication/acceptance time)              │
│                "Bloomberg consensus AS OF 2025-01-20"                       │
│                datetime(2025, 1, 20, 16, 30)                                │
│                                                                             │
│  captured_at:  When our system ingested it                                  │
│                "We pulled this data AT 2025-01-21 08:00"                    │
│                datetime(2025, 1, 21, 8, 0)                                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

Why this matters:
- Estimate REVISIONS: same (entity, metric, period), different as_of dates
- Backfill tracking: captured_at shows when data entered your system
- Point-in-time analysis: "What was consensus AS OF Dec 31?"
```

### Provenance: ProvenanceRef + SourceKey

Split the monolithic `DataSource` into two focused objects:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       ProvenanceRef                                         │
│              "Which document/snapshot produced this?"                       │
├─────────────────────────────────────────────────────────────────────────────┤
│  kind:           sec_filing | press_release | vendor_snapshot | broker_note │
│  external_id:    "0001318605-25-000015" (accession number)                  │
│  published_at:   datetime(2025, 2, 15)                                      │
│                                                                             │
│  ─── For SEC filings ───                                                    │
│  accession_number:  "0001318605-25-000015"                                  │
│  form_type:         "10-K"                                                  │
│  filing_date:       date(2025, 2, 15)                                       │
│                                                                             │
│  ─── For vendor snapshots ───                                               │
│  snapshot_date:     date(2025, 2, 16)                                       │
│  snapshot_version:  "2025-02-16T06:00:00Z"                                  │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                        SourceKey                                            │
│              "Which dataset/field within that source?"                      │
├─────────────────────────────────────────────────────────────────────────────┤
│  vendor:         VendorNamespace.FACTSET                                    │
│  dataset:        "ff_fundamentals"                                          │
│  field:          "FF_SALES"                                                 │
│                                                                             │
│  ─── For SEC XBRL ───                                                       │
│  xbrl_namespace: "us-gaap"                                                  │
│  xbrl_tag:       "Revenues"                                                 │
└─────────────────────────────────────────────────────────────────────────────┘

Why split?
- Same document → multiple metrics (one ProvenanceRef, many SourceKeys)
- Same field → multiple snapshots (one SourceKey, many ProvenanceRefs)
- Lineage needs document-level identity
- Crosswalks need field-level identity
```

### Estimate Metadata

Estimates need additional context beyond actuals:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         EstimateInfo                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│  scope:        BROKER | CONSENSUS | COMPANY_GUIDANCE | BUY_SIDE            │
│  estimator:    "Cantor Fitzgerald" | "Bloomberg Consensus"                  │
│                                                                             │
│  ─── For individual analyst ───                                             │
│  analyst_id:   "CF-JSmith-001"                                              │
│  analyst_name: "John Smith"                                                 │
│                                                                             │
│  ─── For consensus ───                                                      │
│  num_estimates:  24                                                         │
│  high_estimate:  $1.15                                                      │
│  low_estimate:   $0.95                                                      │
│                                                                             │
│  ─── For company guidance ───                                               │
│  guidance_type:  "range" | "point"                                          │
│  guidance_low:   $115B                                                      │
│  guidance_high:  $125B                                                      │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Value with Units: Raw + Normalized

Store BOTH to prevent scale confusion:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       ValueWithUnits                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│  value_normalized:  119200000000        │  ALWAYS base units (USD)         │
│  value_raw:         119.2               │  As received                     │
│  unit:              "USD"               │  Unit type                       │
│  scale:             1_000_000_000       │  Raw → Normalized multiplier     │
│  currency:          "USD"               │  ISO 4217 code                   │
└─────────────────────────────────────────────────────────────────────────────┘

Prevents:
- "$119.2B" vs "119,200 (millions)" confusion
- Currency conversion ambiguity
- Scale mismatches in aggregation
```

### Supersession Model (Instead of is_primary)

Don't store "is_primary" - that's subjective. Model supersession explicitly:

```
Timeline:
─────────────────────────────────────────────────────────────────────────────

Jan 29, 2025 │ Press Release       │ Revenue = $119.2B │ obs_id = "pr_001"
             │                     │                   │
Feb 15, 2025 │ SEC 10-K            │ Revenue = $119.2B │ obs_id = "10k_001"
             │                     │                   │ supersedes = "pr_001"
             │                     │                   │
Mar 01, 2025 │ SEC 10-K/A (amended)│ Revenue = $119.5B │ obs_id = "10ka_001"
             │                     │                   │ supersedes = "10k_001"

Query "current value" = find observation where superseded_by IS NULL

"Primary" becomes a VIEW (selection rule), not a stored flag:
- Most recent SEC filing not superseded
- Or most recent vendor snapshot
- Or any actual
```

### Observation Key (Deduplication/Idempotency)

Deterministic key for upsert semantics:

```
observation_key = SHA256(
    entity_id +
    metric.canonical_key +
    period.canonical_key +
    as_of.isoformat() +
    provenance_ref.external_id +
    [estimator + estimate_scope]  # for estimates
)[:32]

Same key = same logical observation
→ Perfect re-run idempotency without overwriting
→ Handles vendor re-deliveries gracefully
```

### Comparability Profiles

Comparability is CONTEXTUAL, not stored on observations:

```python
# Define a profile
PROFILE_EPS_VS_BLOOMBERG = ComparabilityProfile(
    profile_id="eps_vs_bloomberg_consensus",
    metric_spec=MetricSpec.eps_gaap_diluted(),
    acceptable_sources=[VendorNamespace.BLOOMBERG, VendorNamespace.SEC],
    basis_must_match=True,
    presentation_must_match=False,  # Compare reported vs normalized
)

# Check an observation against it
result = check_comparability(observation, PROFILE_EPS_VS_BLOOMBERG)

# Result:
# ComparabilityResult(
#   comparable=True,
#   grade="mostly",
#   reasons=["Presentation mismatch: vendor_norm vs reported"],
#   confidence=0.85,
# )
```

### The Complete v2 Observation Model

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     FinancialObservation (v2)                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ─── IDENTITY ───                                                           │
│  observation_id:      UUID                                                  │
│  observation_key:     SHA256 hash (for deduplication)                       │
│                                                                             │
│  ─── TARGET ───                                                             │
│  entity_id:           Links to Entity                                       │
│  security_id:         Optional link to Security                             │
│                                                                             │
│  ─── WHAT (structured) ───                                                  │
│  metric:              MetricSpec (code + basis + presentation + ...)        │
│                                                                             │
│  ─── WHEN (three timestamps) ───                                            │
│  period:              FiscalPeriod (what it measures)                       │
│  as_of:               datetime (when it was known)                          │
│  captured_at:         datetime (when we ingested)                           │
│                                                                             │
│  ─── TYPE ───                                                               │
│  observation_type:    actual | estimate | guidance | consensus              │
│                                                                             │
│  ─── VALUE (raw + normalized) ───                                           │
│  value:               ValueWithUnits                                        │
│                                                                             │
│  ─── PROVENANCE (split) ───                                                 │
│  provenance_ref:      Which document/snapshot                               │
│  source_key:          Which dataset/field                                   │
│                                                                             │
│  ─── ESTIMATE METADATA ───                                                  │
│  estimate_info:       EstimateInfo (for estimates only)                     │
│                                                                             │
│  ─── SUPERSESSION ───                                                       │
│  supersedes_observation_id:     What this replaces                          │
│  superseded_by_observation_id:  What replaced this                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Complete Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        ENTITYSPINE ARCHITECTURE                            │
└─────────────────────────────────────────────────────────────────────────────┘

                           DATA SOURCES
    ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
    │ FactSet  │  │Bloomberg │  │  SEC     │  │ Thomson  │  │Compustat │
    │  CSV/TSV │  │  DAPI    │  │  EDGAR   │  │  PermID  │  │  WRDS    │
    └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘
         │             │             │             │             │
         └─────────────┴──────┬──────┴─────────────┴─────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       SCHEMA DETECTOR                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  • Auto-detect vendor from filename + column headers                │   │
│  │  • Map vendor columns to EntitySpine fields                         │   │
│  │  • Suggest appropriate loader                                        │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DATA LOADERS                                        │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐               │
│  │ iter_factset_csv│ │iter_bloomberg   │ │ iter_thomson_ttl│  ...         │
│  │ load_factset    │ │load_bloomberg   │ │ load_thomson    │               │
│  └────────┬────────┘ └────────┬────────┘ └────────┬────────┘               │
└───────────┴───────────────────┴───────────────────┴─────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      DOMAIN MODELS (Immutable)                              │
│                                                                             │
│   ┌────────────┐      ┌────────────┐      ┌────────────┐                   │
│   │   Entity   │──1:N─│  Security  │──1:N─│  Listing   │                   │
│   │            │      │            │      │            │                   │
│   │ entity_id  │      │ security_id│      │ listing_id │                   │
│   │ primary_nam│      │ entity_id  │      │ security_id│                   │
│   │ entity_type│      │ sec_type   │      │ ticker     │                   │
│   │ jurisdiction      │ currency   │      │ mic        │                   │
│   └────────────┘      └────────────┘      └────────────┘                   │
│          │                  │                   │                           │
│          └──────────────────┼───────────────────┘                           │
│                             │                                               │
│                             ▼                                               │
│                   ┌──────────────────┐                                      │
│                   │ IdentifierClaim  │  (Links identifiers to targets)     │
│                   │                  │                                      │
│                   │ scheme: CUSIP    │                                      │
│                   │ value: 037833100 │                                      │
│                   │ entity_id: ...   │                                      │
│                   │ namespace: FACTSET                                      │
│                   │ captured_at: ... │                                      │
│                   └──────────────────┘                                      │
│                                                                             │
│                   ┌──────────────────────┐                                  │
│                   │ FinancialObservation │  (Links metrics to entities)    │
│                   │                      │                                  │
│                   │ entity_id: tsla      │                                  │
│                   │ metric: REVENUE      │                                  │
│                   │ period: FY2025       │                                  │
│                   │ value: $119.2B       │                                  │
│                   │ source: SEC_10K      │                                  │
│                   └──────────────────────┘                                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       STORAGE (Parquet)                                     │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐               │
│  │ entities/       │ │ identifiers/    │ │ observations/   │               │
│  │   *.parquet     │ │   *.parquet     │ │   *.parquet     │               │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘               │
└─────────────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        QUERY & ANALYSIS                                     │
│                                                                             │
│  • Resolve entity by any identifier (CIK, CUSIP, ticker, etc.)             │
│  • Get all identifiers for an entity across vendors                         │
│  • Compare financial metrics across sources                                 │
│  • Calculate earnings surprise (actual vs consensus)                        │
│  • Track estimate revisions over time                                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Usage Examples

### 1. Load Entities from FactSet

```python
from entityspine.data.schema_detector import get_loader_suggestion
from entityspine.data.loaders import iter_factset_csv, load_factset_batch

# Auto-detect and load
file_path = "G:/FACTSET/ff_security_master.csv"
suggestion = get_loader_suggestion(file_path)

# Stream in batches (memory efficient)
for batch in iter_factset_csv(file_path, batch_size=10000):
    entities, securities, listings, claims = load_factset_batch(batch)
    
    # Store to Parquet
    store.add_entities(entities)
    store.add_securities(securities)
    store.add_listings(listings)
    store.add_claims(claims)
```

### 2. Create Observations with Full Provenance (v2)

```python
from entityspine.domain.financial_observation_v2 import (
    MetricSpec, FiscalPeriod, Presentation,
    create_factset_observation,
    create_sec_observation,
    create_analyst_estimate,
    create_consensus_estimate,
    create_company_guidance,
)
from decimal import Decimal
from datetime import date

# FactSet revenue (vendor-normalized)
obs1 = create_factset_observation(
    entity_id="tsla-001",
    metric=MetricSpec.revenue(Presentation.VENDOR_NORMALIZED),
    period=FiscalPeriod.annual(2025),
    value=Decimal("119.2"),  # Raw value (billions)
    field_name="FF_SALES",
    dataset="ff_fundamentals",
    scale=1_000_000_000,  # Normalizes to $119.2B
)

# SEC 10-K filing (authoritative, as-reported)
obs2 = create_sec_observation(
    entity_id="tsla-001",
    metric=MetricSpec.revenue(Presentation.REPORTED),
    period=FiscalPeriod.annual(2025),
    value=Decimal("119200000000"),
    form_type="10-K",
    accession_number="0001318605-25-000015",
    filing_date=date(2025, 2, 15),
    xbrl_tag="Revenues",
)

# Analyst estimate (EPS, non-GAAP, diluted)
obs3 = create_analyst_estimate(
    entity_id="tsla-001",
    metric=MetricSpec.eps_non_gaap_diluted(),
    period=FiscalPeriod.quarterly(2025, 4),
    value=Decimal("1.08"),
    analyst_firm="Cantor Fitzgerald",
    estimate_date=date(2025, 1, 10),
)

# Bloomberg consensus
obs4 = create_consensus_estimate(
    entity_id="tsla-001",
    metric=MetricSpec.eps_gaap_diluted(),
    period=FiscalPeriod.quarterly(2025, 4),
    value=Decimal("0.87"),
    provider="Bloomberg",
    as_of_date=date(2025, 1, 25),
    num_estimates=24,
    high=Decimal("1.05"),
    low=Decimal("0.72"),
)

# Company guidance (range)
obs5 = create_company_guidance(
    entity_id="tsla-001",
    metric=MetricSpec.revenue(),
    period=FiscalPeriod.annual(2026),
    low=Decimal("130000000000"),
    high=Decimal("140000000000"),
    guidance_date=date(2025, 1, 29),
)
```

### 3. Track Estimate Revisions Over Time

```python
# Same analyst revising their estimate:

# Jan 10 estimate
est_v1 = create_analyst_estimate(
    entity_id="tsla-001",
    metric=MetricSpec.eps_non_gaap_diluted(),
    period=FiscalPeriod.quarterly(2025, 4),
    value=Decimal("1.08"),
    analyst_firm="Cantor Fitzgerald",
    estimate_date=date(2025, 1, 10),
)

# Jan 20 revision (different as_of → different observation_key)
est_v2 = create_analyst_estimate(
    entity_id="tsla-001",
    metric=MetricSpec.eps_non_gaap_diluted(),
    period=FiscalPeriod.quarterly(2025, 4),
    value=Decimal("1.12"),  # Raised estimate
    analyst_firm="Cantor Fitzgerald",
    estimate_date=date(2025, 1, 20),
)

# Both are stored - you can track the revision history
print(f"V1: {est_v1.observation_key}")
print(f"V2: {est_v2.observation_key}")
# Different keys because as_of differs
```

### 4. Compare Across Sources with Comparability Profiles

```python
from entityspine.domain.financial_observation_v2 import (
    check_comparability,
    ComparabilityProfile,
    PROFILE_EPS_VS_BLOOMBERG_CONSENSUS,
)

# Check if observation is comparable under a profile
result = check_comparability(obs3, PROFILE_EPS_VS_BLOOMBERG_CONSENSUS)

print(f"Comparable: {result.comparable}")
print(f"Grade: {result.grade}")
print(f"Confidence: {result.confidence:.0%}")
print(f"Reasons: {', '.join(result.reasons)}")

# Output:
# Comparable: True
# Grade: mostly
# Confidence: 85%
# Reasons: Presentation mismatch: company_adj vs reported
```

### 5. Model Supersession (10-K supersedes Press Release)

```python
# Press release on earnings day
pr_obs = FinancialObservation(
    observation_id="pr_001",
    entity_id="tsla-001",
    metric=MetricSpec.revenue(),
    period=FiscalPeriod.annual(2025),
    value=ValueWithUnits.from_normalized(Decimal("119200000000"), "USD"),
    provenance_ref=ProvenanceRef.press_release(
        release_date=date(2025, 1, 29),
    ),
)

# 10-K filing supersedes press release
sec_obs = FinancialObservation(
    observation_id="10k_001",
    entity_id="tsla-001",
    metric=MetricSpec.revenue(),
    period=FiscalPeriod.annual(2025),
    value=ValueWithUnits.from_normalized(Decimal("119200000000"), "USD"),
    provenance_ref=ProvenanceRef.sec_filing(
        accession_number="0001318605-25-000015",
        form_type="10-K",
        filing_date=date(2025, 2, 15),
    ),
    supersedes_observation_id="pr_001",  # Explicitly links
)

# Query "current value" = find where superseded_by IS NULL
```

### 6. Handle Unit Conversions Safely

```python
from entityspine.domain.financial_observation_v2 import ValueWithUnits

# FactSet delivers in billions
factset_value = ValueWithUnits.from_raw(
    value_raw=Decimal("119.2"),
    unit="USD",
    scale=1_000_000_000,  # Billions
)
print(f"Normalized: ${factset_value.value_normalized:,.0f}")  # $119,200,000,000
print(f"In billions: ${factset_value.in_billions():.1f}B")   # $119.2B

# Bloomberg delivers in millions
bloomberg_value = ValueWithUnits.from_raw(
    value_raw=Decimal("119200"),
    unit="USD",
    scale=1_000_000,  # Millions
)
print(f"Normalized: ${bloomberg_value.value_normalized:,.0f}")  # $119,200,000,000

# Both normalize to same value - safe to compare!
assert factset_value.value_normalized == bloomberg_value.value_normalized
```

### 7. Entity Resolution

```python
from entityspine.services.resolver import EntityResolver

resolver = EntityResolver(store)

# Find entity by any identifier
entity = resolver.resolve(scheme="CIK", value="0000320193")
# Returns: Entity(primary_name="Apple Inc.", ...)

# Find entity by ticker + exchange
entity = resolver.resolve(scheme="TICKER", value="AAPL", mic="XNAS")

# Get all identifiers for an entity
claims = store.get_claims_for_entity(entity.entity_id)
for claim in claims:
    print(f"{claim.scheme.value}: {claim.value} (from {claim.namespace.value})")
```
```

---

## Summary

**EntitySpine solves three problems:**

1. **Entity Resolution**: Map identifiers across vendors (CIK, CUSIP, PermID, FIGI, etc.)
2. **Data Provenance**: Know exactly where every value came from
3. **Multi-Source Metrics**: Track the same metric from different sources with full context

**v2 Observation Model Improvements:**

| Feature | v1 Problem | v2 Solution |
|---------|------------|-------------|
| **Metric Ambiguity** | `variant="non_gaap"` conflates basis, presentation, share type | Structured `MetricSpec` with orthogonal axes |
| **Time Confusion** | `reported_date` vs `created_at` unclear | Explicit `period`, `as_of`, `captured_at` |
| **Provenance Monolith** | `DataSource` did too much | Split: `ProvenanceRef` + `SourceKey` |
| **Estimate Handling** | Broker and consensus mixed | Explicit `EstimateInfo` with scope |
| **Comparability** | `is_comparable` stored on observation | Contextual `ComparabilityProfile` |
| **Deduplication** | No idempotency | Deterministic `observation_key` |
| **Supersession** | `is_primary` flag (subjective) | Explicit `supersedes_observation_id` |
| **Unit Confusion** | "$119.2B" vs "119,200M" | `ValueWithUnits` with raw + normalized |

**Key architectural decisions:**

- Immutable domain models (thread-safe, auditable)
- Identifiers are claims, not properties (provenance tracking)
- Scheme-scope enforcement (CIK→Entity, CUSIP→Security, TICKER→Listing)
- Multi-vendor namespaces (FactSet, Bloomberg, SEC, etc.)
- Parquet storage (efficient columnar storage for analytics)
- Comparability is contextual, not stored
- Supersession chain instead of "primary" flag
- Both raw and normalized values stored

---

## Migration: v1 → v2

If you're using v1 `financial_observation.py`, here's how to migrate:

```python
# v1 (OLD)
from entityspine.domain.financial_observation import (
    MetricCode, MetricVariant, MetricDefinition,
    create_analyst_estimate,
)
obs = create_analyst_estimate(
    entity_id="tsla",
    metric_code=MetricCode.EPS,
    variant=MetricVariant.NON_GAAP,  # Ambiguous!
    ...
)

# v2 (NEW)
from entityspine.domain.financial_observation_v2 import (
    MetricSpec, create_analyst_estimate,
)
obs = create_analyst_estimate(
    entity_id="tsla",
    metric=MetricSpec.eps_non_gaap_diluted(),  # Explicit: non-gaap + diluted
    ...
)
```

Key mapping:
- `MetricVariant.GAAP` → `MetricSpec(basis=AccountingBasis.GAAP, presentation=Presentation.REPORTED)`
- `MetricVariant.NON_GAAP` → `MetricSpec(presentation=Presentation.COMPANY_ADJUSTED)`
- `MetricVariant.DILUTED` → `MetricSpec(per_share=PerShareType.DILUTED)`
- `MetricVariant.CONTINUING` → `MetricSpec(scope=ScopeType.CONTINUING)`

---

## Next Steps

1. **Migrate Loaders** - Update data loaders to create v2 FinancialObservations
2. **SEC XBRL Parser** - Parse 10-K/10-Q filings with proper MetricSpec
3. **Consensus Builder** - Aggregate broker estimates with EstimateInfo
4. **Surprise Calculator** - Compare actuals vs consensus using ComparabilityProfiles
5. **Revision Tracker** - Build estimate revision history using as_of timestamps
6. **Supersession Chain** - Link amended filings to originals
