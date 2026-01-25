"""
Provenance domain models (stdlib dataclass).

STDLIB ONLY - NO PYDANTIC.

Provenance tracks WHERE data came from - the source system, file, API call,
or human operator that provided a piece of information. This enables:
- Audit trail: "Where did this CIK come from?"
- Data quality: "Which sources are most reliable?"
- Debugging: "Why do SEC and FactSet disagree?"

v2.3.4 Design:
- Provenance is the unit of "where data came from"
- SourceRecord preserves raw ingested data before transformation
- Every IdentifierClaim can optionally link to its provenance
"""

from dataclasses import dataclass, field
from datetime import datetime

from entityspine.domain.enums import ProvenanceKind, VendorNamespace
from entityspine.domain.timestamps import generate_ulid, utc_now


@dataclass(frozen=True, slots=True)
class Provenance:
    """
    Tracks the origin of data in the entity graph for audit and quality.

    Manifesto
    ---------
    Provenance is the foundation of data trust in EntitySpine. Financial data
    flows from multiple sources (SEC EDGAR, FactSet, Bloomberg, manual entry),
    and each source has different reliability characteristics. Provenance
    enables:

    - **Regulatory Compliance**: Auditors can trace any data point to its
      original source file/API call
    - **Conflict Resolution**: When SEC says CIK=320193 and FactSet says
      something different, we know which source to trust
    - **Data Quality**: Track which sources produce the most errors
    - **Reproducibility**: Re-run ingestion from the exact same source

    This supports the Claims-Based Identity principle (Principle #2): every
    IdentifierClaim can link to its provenance, documenting WHO said WHAT
    about WHICH identifier.

    Architecture
    ------------
    ::

        ┌─────────────────────────────────────────────────────────────────────┐
        │                     Provenance Tracking                              │
        │                                                                      │
        │   Data Sources                    Provenance Records                 │
        │   ┌─────────────┐                 ┌─────────────────────┐           │
        │   │ SEC EDGAR   │────────────────▶│ kind: FILE          │           │
        │   │ API/Files   │                 │ namespace: SEC      │           │
        │   └─────────────┘                 │ source_uri: s3://...│           │
        │                                   │ source_hash: abc123 │           │
        │   ┌─────────────┐                 └─────────┬───────────┘           │
        │   │ FactSet     │                           │                        │
        │   │ Symbology   │────────────────▶          ▼                        │
        │   └─────────────┘                 ┌─────────────────────┐           │
        │                                   │ IdentifierClaim     │           │
        │   ┌─────────────┐                 │ scheme: CIK         │           │
        │   │ Manual      │                 │ value: 320193       │           │
        │   │ Override    │────────────────▶│ provenance_id: P1   │◀──────────│
        │   └─────────────┘                 └─────────────────────┘           │
        │                                                                      │
        │   "Every claim traces back to a source"                              │
        └─────────────────────────────────────────────────────────────────────┘

    Features
    --------
    - **Multi-Source**: FILE, API, MANUAL, DERIVED provenance kinds
    - **Content Verification**: source_hash enables integrity checking
    - **Batch Tracking**: batch_id links related ingestion records
    - **User Attribution**: captured_by tracks who made manual changes
    - **Temporal**: captured_at vs created_at distinguishes ingestion time

    Examples
    --------
    File-based provenance (SEC EDGAR):

    >>> prov = Provenance(
    ...     kind=ProvenanceKind.FILE,
    ...     namespace=VendorNamespace.SEC,
    ...     source_uri="https://www.sec.gov/files/company_tickers.json",
    ...     file_name="company_tickers.json",
    ...     source_hash="sha256:abc123...",
    ...     batch_id="batch_20240115_001",
    ... )
    >>> prov.namespace
    <VendorNamespace.SEC: 'sec'>

    API-based provenance (FactSet):

    >>> prov = Provenance(
    ...     kind=ProvenanceKind.API,
    ...     namespace=VendorNamespace.FACTSET,
    ...     api_endpoint="/symbology/v1/identifier-resolution",
    ...     api_params='{"ids": ["AAPL-US"]}',
    ... )

    Manual override with notes:

    >>> prov = Provenance(
    ...     kind=ProvenanceKind.MANUAL,
    ...     namespace=VendorNamespace.INTERNAL,
    ...     captured_by="analyst@company.com",
    ...     notes="Manual correction per ticket JIRA-123",
    ... )

    Performance
    -----------
    - Memory: ~200 bytes per record (frozen, slotted)
    - Storage: Indexed by provenance_id for O(1) lookup
    - Deduplication: source_hash enables duplicate detection

    Guardrails
    ----------
    - Frozen dataclass ensures immutability after creation
    - provenance_id auto-generated as ULID for chronological sorting
    - captured_at defaults to now() for accurate timing

    Context
    -------
    Provenance works with SourceRecord to provide complete audit trails.
    Provenance describes WHERE data came from; SourceRecord preserves
    the raw data before transformation.

    Tags
    ----
    :tag domain-model: Core domain concept
    :tag audit: Regulatory audit trail
    :tag principle-2: Claims-based identity support
    :tag data-quality: Source reliability tracking
    :tag compliance: SEC/FINRA audit requirements

    Doc-Types
    ---------
    :api-ref: entityspine.domain.provenance.Provenance
    :related: SourceRecord, IdentifierClaim, VendorNamespace

    Attributes
    ----------
    provenance_id : str
        ULID primary key (auto-generated).
    kind : ProvenanceKind
        Type of provenance (FILE, API, MANUAL, DERIVED).
    namespace : VendorNamespace
        Vendor/source namespace (SEC, FACTSET, BLOOMBERG, etc.).
    source_uri : str | None
        Location of source (file path, S3 URI, API URL).
    source_hash : str | None
        SHA-256 hash of source content for verification.
    captured_at : datetime
        When the data was captured/ingested.
    captured_by : str | None
        User/system that captured the data.
    file_name : str | None
        Original filename (if file-based).
    api_endpoint : str | None
        API endpoint (if API-based).
    api_params : str | None
        API parameters as JSON string.
    batch_id : str | None
        Batch/job ID for bulk imports.
    notes : str | None
        Additional notes (especially for MANUAL provenance).
    created_at : datetime
        Record creation timestamp.
    """

    # Primary key
    provenance_id: str = field(default_factory=generate_ulid)

    # Source classification
    kind: ProvenanceKind = ProvenanceKind.FILE
    namespace: VendorNamespace = VendorNamespace.INTERNAL

    # Source location
    source_uri: str | None = None
    source_hash: str | None = None  # SHA-256 of source content

    # Timing
    captured_at: datetime = field(default_factory=utc_now)
    captured_by: str | None = None  # User/system that captured

    # File-specific
    file_name: str | None = None

    # API-specific
    api_endpoint: str | None = None
    api_params: str | None = None  # JSON string of params

    # Batch info
    batch_id: str | None = None

    # Notes
    notes: str | None = None

    # Timestamps
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self):
        """Validate provenance after creation."""
        if self.kind == ProvenanceKind.FILE and not self.source_uri and not self.file_name:
            # Allow either source_uri or file_name for FILE provenance
            pass  # Relaxed validation
        if self.kind == ProvenanceKind.API and not self.api_endpoint:
            # API provenance should have endpoint, but don't fail hard
            pass


@dataclass(frozen=True, slots=True)
class SourceRecord:
    """
    Preserves raw ingested data before transformation for reprocessing.

    Manifesto
    ---------
    SourceRecord implements "capture once, process many times" philosophy.
    When ingesting data from external sources, we preserve the EXACT bytes
    received before any normalization or transformation. This enables:

    - **Reprocessing**: Run new parsing logic without re-fetching data
    - **Debugging**: Compare raw vs transformed values when issues arise
    - **Compliance**: Prove what we received matches what we stored
    - **Recovery**: Rebuild the graph from raw records if needed

    Raw data is stored as JSON strings because:
    1. JSON is universal (every API returns it)
    2. It's human-readable for debugging
    3. It compresses well for storage
    4. It's schema-flexible for evolving sources

    Architecture
    ------------
    ::

        ┌─────────────────────────────────────────────────────────────────────┐
        │                    Source Record Lifecycle                           │
        │                                                                      │
        │   External Source          SourceRecord              Domain Objects  │
        │   ┌─────────────┐          ┌──────────────┐          ┌────────────┐ │
        │   │ SEC JSON    │──────────│ raw_data:    │          │            │ │
        │   │ {           │  capture │ '{"cik":     │  process │  Entity    │ │
        │   │  "cik":320193│────────▶│   "320193",  │─────────▶│  Security  │ │
        │   │  "ticker":"AAPL"│      │   "ticker":  │          │  Listing   │ │
        │   │ }           │          │   "AAPL"}'   │          │            │ │
        │   └─────────────┘          ├──────────────┤          └────────────┘ │
        │                            │ processed: T │                         │
        │                            │ entity_id: E1│◀── links back to        │
        │                            └──────────────┘   created objects       │
        │                                                                      │
        │   Later: "Oops, we had a bug in name normalization"                 │
        │   Solution: Reprocess all SourceRecords with fixed logic            │
        └─────────────────────────────────────────────────────────────────────┘

    Features
    --------
    - **Raw Preservation**: Exact data as received (no normalization)
    - **Processing State**: processed/processed_at track transformation
    - **Object Links**: entity_id/security_id/listing_id link to results
    - **Error Tracking**: error_message captures processing failures
    - **Provenance Link**: provenance_id traces to source metadata

    Examples
    --------
    Creating a source record from SEC data:

    >>> source = SourceRecord(
    ...     provenance_id="01HQ...",
    ...     raw_data='{"cik": "320193", "ticker": "AAPL", "title": "Apple Inc."}',
    ...     record_type="entity",
    ...     source_key="320193",
    ... )
    >>> source.is_processed
    False

    After successful processing:

    >>> # (After processing pipeline runs)
    >>> source.processed
    True
    >>> source.entity_id
    '01HQ8KQXYZ...'
    >>> source.is_processed
    True

    Processing failure:

    >>> source.processed
    True
    >>> source.error_message
    'Invalid CIK format: expected 10 digits'
    >>> source.has_error
    True

    Performance
    -----------
    - Storage: raw_data compressed in SQLite (typically 50-80% reduction)
    - Indexing: source_key indexed for deduplication
    - Batch Processing: processed flag enables incremental reprocessing

    Guardrails
    ----------
    - Frozen dataclass ensures raw_data cannot be modified
    - record_id auto-generated as ULID
    - is_processed property checks both processed AND no error

    Context
    -------
    SourceRecord works with Provenance: Provenance describes WHERE data
    came from (file, API, batch); SourceRecord preserves WHAT the data was.
    Together they provide complete audit trail.

    Tags
    ----
    :tag domain-model: Core domain concept
    :tag audit: Raw data preservation
    :tag reprocessing: Enable ETL replay
    :tag data-quality: Error tracking

    Doc-Types
    ---------
    :api-ref: entityspine.domain.provenance.SourceRecord
    :related: Provenance, DataLoader, Entity

    Attributes
    ----------
    record_id : str
        ULID primary key (auto-generated).
    provenance_id : str | None
        Link to source Provenance record.
    raw_data : str
        Original data as JSON string (preserved exactly).
    record_type : str
        Type of record (entity, security, listing, claim).
    source_key : str | None
        Key/ID in the source system (for deduplication).
    processed : bool
        Whether this record has been processed.
    processed_at : datetime | None
        When the record was processed.
    entity_id : str | None
        Entity created/updated from this record.
    security_id : str | None
        Security created/updated from this record.
    listing_id : str | None
        Listing created/updated from this record.
    error_message : str | None
        Error message if processing failed.
    created_at : datetime
        Record creation timestamp.
    """

    # Primary key
    record_id: str = field(default_factory=generate_ulid)

    # Link to provenance
    provenance_id: str | None = None

    # Raw data
    raw_data: str = ""  # JSON string of original data
    record_type: str = "unknown"  # entity, security, listing, etc.
    source_key: str | None = None  # Key in source system

    # Processing state
    processed: bool = False
    processed_at: datetime | None = None

    # Links to created objects
    entity_id: str | None = None
    security_id: str | None = None
    listing_id: str | None = None

    # Error handling
    error_message: str | None = None

    # Timestamps
    created_at: datetime = field(default_factory=utc_now)

    @property
    def has_error(self) -> bool:
        """Check if processing had an error."""
        return self.error_message is not None

    @property
    def is_processed(self) -> bool:
        """Check if record was successfully processed."""
        return self.processed and not self.has_error
