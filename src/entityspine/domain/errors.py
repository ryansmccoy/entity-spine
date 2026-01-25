"""
Structured Error Domain Models.

Provides stdlib-only types for consistent error handling across the ecosystem:
- ErrorCategory enum for classification
- ErrorContext dataclass for structured metadata
- Base error types with retry semantics

These models define error CONCEPTS without exception handling logic.
spine-core imports these and adds exception hierarchy/retry logic.

DESIGN PRINCIPLES:
- Stdlib-only: No third-party dependencies
- Classification: Errors categorized for routing/alerting
- Retryability: Clear semantics for retry decisions
- Context: Structured metadata for debugging

Migration Note:
    These models were extracted from spine-core.errors to provide
    a clean separation between domain types and exception handling.

Example:
    >>> from entityspine.domain import ErrorCategory, ErrorContext
    >>> ctx = ErrorContext(
    ...     pipeline="ingest_sec",
    ...     source_name="SEC_EDGAR",
    ...     url="https://www.sec.gov/cgi-bin/browse-edgar",
    ... )
    >>> ctx.category = ErrorCategory.SOURCE
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

# =============================================================================
# Error Categories
# =============================================================================


class ErrorCategory(str, Enum):
    """
    Standard error categories for classification.
    
    Used by alerting frameworks to route notifications and by retry logic
    to determine if a retry makes sense.
    
    Categories are organized by typical source:
    - Infrastructure: Usually transient, often retryable
    - Data: May or may not be retryable depending on source
    - Configuration: Never retryable (requires code/config change)
    - Application: May need investigation
    
    Example:
        >>> category = ErrorCategory.NETWORK
        >>> category.is_likely_transient()
        True
    """

    # Infrastructure errors (usually transient)
    NETWORK = "NETWORK"           # Connection, timeout, DNS
    DATABASE = "DATABASE"         # Connection pool, query timeout
    STORAGE = "STORAGE"           # Disk, S3, file system
    RATE_LIMIT = "RATE_LIMIT"     # API rate limiting

    # Source/data errors
    SOURCE = "SOURCE"             # Upstream API, file not found
    PARSE = "PARSE"               # Data parsing, format errors
    VALIDATION = "VALIDATION"     # Schema, constraint violations
    ENCODING = "ENCODING"         # Character encoding issues

    # Configuration errors (never retryable)
    CONFIG = "CONFIG"             # Missing config, invalid settings
    AUTH = "AUTH"                 # Authentication, authorization
    PERMISSION = "PERMISSION"     # File/resource access denied

    # Application errors
    PIPELINE = "PIPELINE"         # Pipeline execution failures
    ORCHESTRATION = "ORCHESTRATION"  # Workflow, scheduler errors
    DEPENDENCY = "DEPENDENCY"     # Missing package, version conflict

    # Internal errors
    INTERNAL = "INTERNAL"         # Bugs, unexpected state
    UNKNOWN = "UNKNOWN"           # Uncategorized errors

    def is_likely_transient(self) -> bool:
        """
        True if errors in this category are typically transient.
        
        Transient errors may succeed on retry without any changes.
        """
        return self in (
            ErrorCategory.NETWORK,
            ErrorCategory.DATABASE,
            ErrorCategory.STORAGE,
            ErrorCategory.RATE_LIMIT,
        )

    def is_retryable(self) -> bool:
        """
        True if errors in this category might benefit from retry.
        
        More inclusive than is_likely_transient - includes source errors
        that might recover if the upstream service recovers.
        """
        return self in (
            ErrorCategory.NETWORK,
            ErrorCategory.DATABASE,
            ErrorCategory.STORAGE,
            ErrorCategory.RATE_LIMIT,
            ErrorCategory.SOURCE,
        )

    def requires_investigation(self) -> bool:
        """
        True if errors in this category likely need human investigation.
        
        These errors won't resolve themselves with retries.
        """
        return self in (
            ErrorCategory.CONFIG,
            ErrorCategory.AUTH,
            ErrorCategory.PERMISSION,
            ErrorCategory.INTERNAL,
            ErrorCategory.VALIDATION,
        )


class ErrorSeverity(str, Enum):
    """
    Severity level for error classification.
    
    Used for alerting thresholds and dashboard filtering.
    """

    DEBUG = "DEBUG"       # Detailed debugging info
    INFO = "INFO"         # Informational (expected errors)
    WARNING = "WARNING"   # Concerning but not critical
    ERROR = "ERROR"       # Standard error
    CRITICAL = "CRITICAL" # Requires immediate attention


# =============================================================================
# Error Context
# =============================================================================


@dataclass
class ErrorContext:
    """
    Structured context for error tracking, routing, and debugging.

    Manifesto
    ---------
    ErrorContext brings structure to error handling in EntitySpine. Instead of
    bare exception messages like "Connection failed", we capture rich metadata:

    - **Classification**: ErrorCategory determines routing (NETWORK → retry,
      CONFIG → alert humans, VALIDATION → log and continue)
    - **Execution Context**: Which pipeline, step, run_id was executing
    - **Request Context**: URL, HTTP status for debugging remote calls
    - **Retry Semantics**: Is this retryable? How many retries attempted?

    This enables sophisticated error handling: automatic retries for transient
    errors, immediate alerts for configuration issues, and detailed logs for
    debugging without exposing sensitive data to users.

    Architecture
    ------------
    ::

        ┌─────────────────────────────────────────────────────────────────────┐
        │                     Error Context Flow                               │
        │                                                                      │
        │   Exception Raised              ErrorContext Created                 │
        │   ┌─────────────────┐           ┌─────────────────────────────────┐ │
        │   │ ConnectionError │──────────▶│ category: NETWORK               │ │
        │   │ "timeout"       │           │ pipeline: ingest_sec            │ │
        │   └─────────────────┘           │ source_name: SEC_EDGAR          │ │
        │                                 │ url: https://sec.gov/...        │ │
        │                                 │ http_status: None (timeout)     │ │
        │                                 │ retryable: True (auto-inferred) │ │
        │                                 └─────────────┬───────────────────┘ │
        │                                               │                      │
        │          ┌────────────────────────────────────┴────────────────┐    │
        │          │                                                      │    │
        │          ▼                                                      ▼    │
        │   ┌─────────────────┐                              ┌─────────────┐  │
        │   │ Retry Handler   │                              │ Alert Router│  │
        │   │ if retryable:   │                              │ if CRITICAL:│  │
        │   │   wait & retry  │                              │   PagerDuty │  │
        │   └─────────────────┘                              └─────────────┘  │
        │                                                                      │
        │   ErrorRecord created for persistence:                               │
        │   ┌─────────────────────────────────────────────────────────────┐   │
        │   │ error_id: "err_01HQ8..."                                     │   │
        │   │ error_type: "ConnectionError"                                │   │
        │   │ message: "Connection to SEC timed out after 30s"             │   │
        │   │ context: <ErrorContext above>                                │   │
        │   │ resolved: False                                              │   │
        │   └─────────────────────────────────────────────────────────────┘   │
        └─────────────────────────────────────────────────────────────────────┘

    Features
    --------
    - **Auto-Retry Classification**: retryable inferred from category if not set
    - **Immutable Copies**: with_retry() and with_metadata() return new instances
    - **Serialization**: to_dict() for logging/JSON (omits None values)
    - **Timestamp Tracking**: UTC timestamp for correlation across services

    Examples
    --------
    Creating context for a network error:

    >>> ctx = ErrorContext(
    ...     category=ErrorCategory.NETWORK,
    ...     pipeline="ingest_sec_filings",
    ...     source_name="SEC_EDGAR",
    ...     url="https://www.sec.gov/cgi-bin/browse-edgar",
    ...     http_status=503,
    ... )
    >>> ctx.retryable
    True  # Auto-inferred from NETWORK category

    Creating context for a validation error:

    >>> ctx = ErrorContext(
    ...     category=ErrorCategory.VALIDATION,
    ...     pipeline="parse_10k",
    ...     metadata={"field": "cik", "value": "invalid"},
    ... )
    >>> ctx.retryable
    False  # Validation errors aren't retryable

    Adding retry information:

    >>> ctx2 = ctx.with_retry(count=3, after_seconds=60)
    >>> ctx2.retry_count
    3

    Serializing for logging:

    >>> ctx.to_dict()
    {'category': 'NETWORK', 'pipeline': 'ingest_sec_filings', ...}

    Performance
    -----------
    - Memory: ~500 bytes per context (metadata dict can grow)
    - Immutable copies: New object per modification (safe for async)
    - Serialization: O(n) where n = number of non-None fields

    Guardrails
    ----------
    - retryable auto-inferred in __post_init__ if not explicitly set
    - timestamp defaults to UTC now for accurate timing
    - to_dict() excludes None values for clean logs

    Context
    -------
    ErrorContext is used by spine-core's exception hierarchy for rich error
    handling. The domain model here defines the structure; exception handling
    logic lives in spine-core.

    Tags
    ----
    :tag domain-model: Core domain concept
    :tag error-handling: Structured error management
    :tag observability: Logging and monitoring support
    :tag retry-semantics: Automatic retry classification

    Doc-Types
    ---------
    :api-ref: entityspine.domain.errors.ErrorContext
    :related: ErrorRecord, ErrorCategory, ErrorSeverity

    Attributes
    ----------
    category : ErrorCategory
        Error classification for routing and retry decisions.
    severity : ErrorSeverity
        Error severity level (DEBUG through CRITICAL).
    pipeline : str | None
        Name of the pipeline/process where error occurred.
    workflow : str | None
        Name of the workflow.
    step : str | None
        Current step/stage within pipeline.
    run_id : str | None
        Workflow run identifier for correlation.
    execution_id : str | None
        Execution context ID.
    source_name : str | None
        Data source name (e.g., "SEC_EDGAR", "FACTSET").
    source_type : str | None
        Data source type (e.g., "API", "FILE").
    url : str | None
        Request URL if applicable.
    http_status : int | None
        HTTP status code if applicable.
    retry_count : int
        Number of retries attempted.
    retryable : bool | None
        Whether error is retryable (None = inferred from category).
    retry_after_seconds : int | None
        Suggested wait time before retry.
    metadata : dict[str, Any]
        Additional context (open-ended key-value pairs).
    timestamp : datetime
        When the error occurred (UTC).
    """

    # Classification
    category: ErrorCategory = ErrorCategory.UNKNOWN
    severity: ErrorSeverity = ErrorSeverity.ERROR

    # Execution context
    pipeline: str | None = None
    workflow: str | None = None
    step: str | None = None
    run_id: str | None = None
    execution_id: str | None = None

    # Source context
    source_name: str | None = None
    source_type: str | None = None

    # Request context
    url: str | None = None
    http_status: int | None = None

    # Retry context
    retry_count: int = 0
    retryable: bool | None = None  # None = unknown
    retry_after_seconds: int | None = None

    # Additional metadata
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        """Infer retryable if not explicitly set."""
        if self.retryable is None:
            self.retryable = self.category.is_retryable()

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to dictionary for logging/serialization.
        
        Only includes non-None values.
        """
        result: dict[str, Any] = {
            "category": self.category.value,
            "severity": self.severity.value,
            "timestamp": self.timestamp.isoformat(),
        }

        optional_fields = [
            "pipeline", "workflow", "step", "run_id", "execution_id",
            "source_name", "source_type", "url", "http_status",
            "retry_count", "retryable", "retry_after_seconds",
        ]

        for field_name in optional_fields:
            value = getattr(self, field_name)
            if value is not None and value != 0:
                result[field_name] = value

        if self.metadata:
            result["metadata"] = self.metadata

        return result

    def with_retry(self, count: int, after_seconds: int | None = None) -> ErrorContext:
        """
        Create copy with updated retry information.
        
        Args:
            count: New retry count
            after_seconds: Suggested wait before retry
            
        Returns:
            New ErrorContext with updated retry info
        """
        return ErrorContext(
            category=self.category,
            severity=self.severity,
            pipeline=self.pipeline,
            workflow=self.workflow,
            step=self.step,
            run_id=self.run_id,
            execution_id=self.execution_id,
            source_name=self.source_name,
            source_type=self.source_type,
            url=self.url,
            http_status=self.http_status,
            retry_count=count,
            retryable=self.retryable,
            retry_after_seconds=after_seconds,
            metadata=dict(self.metadata),
            timestamp=self.timestamp,
        )

    def with_metadata(self, **kwargs: Any) -> ErrorContext:
        """
        Create copy with additional metadata.
        
        Args:
            **kwargs: Key-value pairs to add
            
        Returns:
            New ErrorContext with updated metadata
        """
        new_meta = {**self.metadata, **kwargs}
        return ErrorContext(
            category=self.category,
            severity=self.severity,
            pipeline=self.pipeline,
            workflow=self.workflow,
            step=self.step,
            run_id=self.run_id,
            execution_id=self.execution_id,
            source_name=self.source_name,
            source_type=self.source_type,
            url=self.url,
            http_status=self.http_status,
            retry_count=self.retry_count,
            retryable=self.retryable,
            retry_after_seconds=self.retry_after_seconds,
            metadata=new_meta,
            timestamp=self.timestamp,
        )


# =============================================================================
# Error Record (for persistence/tracking)
# =============================================================================


@dataclass
class ErrorRecord:
    """
    Persistent record of an error occurrence for tracking and resolution.

    Manifesto
    ---------
    ErrorRecord is the persistence layer for errors - the domain model that
    gets stored in databases and logs for later analysis. While ErrorContext
    captures the runtime context when an error occurs, ErrorRecord wraps it
    with persistence concerns:

    - **Unique Identity**: error_id for database primary key
    - **Type Information**: error_type preserves exception class name
    - **Stack Trace**: Optional stack trace for debugging
    - **Error Chaining**: caused_by links related errors
    - **Resolution Tracking**: Mark errors as resolved when fixed

    This supports observability: dashboards can show unresolved errors,
    analysts can filter by category, and on-call engineers can mark issues
    as resolved when addressed.

    Architecture
    ------------
    ::

        ┌─────────────────────────────────────────────────────────────────────┐
        │                     Error Record Lifecycle                           │
        │                                                                      │
        │   Runtime Exception           ErrorRecord                            │
        │   ┌─────────────────┐         ┌──────────────────────────────────┐  │
        │   │ Exception       │────────▶│ error_id: "err_01HQ8..."         │  │
        │   │ + ErrorContext  │         │ error_type: "ConnectionError"    │  │
        │   └─────────────────┘         │ message: "Timeout after 30s"     │  │
        │                               │ context: <ErrorContext>          │  │
        │                               │ stack_trace: "..."               │  │
        │                               │ resolved: False                  │  │
        │                               └──────────────┬───────────────────┘  │
        │                                              │                       │
        │                                              ▼  persist              │
        │                               ┌──────────────────────────────────┐  │
        │                               │      Error Database Table        │  │
        │                               │  - Indexed by error_id           │  │
        │                               │  - Filtered by category          │  │
        │                               │  - Dashboard aggregation         │  │
        │                               └──────────────────────────────────┘  │
        │                                              │                       │
        │                                              ▼  later                │
        │                               ┌──────────────────────────────────┐  │
        │                               │ record.mark_resolved()           │  │
        │                               │ → resolved: True                 │  │
        │                               │ → resolved_at: 2024-01-15T...    │  │
        │                               └──────────────────────────────────┘  │
        └─────────────────────────────────────────────────────────────────────┘

    Features
    --------
    - **Full Context**: Embeds ErrorContext for complete error information
    - **Chaining**: caused_by links to originating error (for wrapped exceptions)
    - **Resolution Workflow**: Mark resolved with timestamp
    - **Property Shortcuts**: is_retryable, category for quick access

    Examples
    --------
    Creating an error record:

    >>> record = ErrorRecord(
    ...     error_id="err_01HQ8...",
    ...     error_type="ConnectionError",
    ...     message="Connection to SEC timed out after 30s",
    ...     context=ErrorContext(
    ...         category=ErrorCategory.NETWORK,
    ...         pipeline="ingest_sec",
    ...     ),
    ...     stack_trace="Traceback (most recent call last):\\n...",
    ... )
    >>> record.is_retryable
    True
    >>> record.category
    <ErrorCategory.NETWORK: 'NETWORK'>

    Marking an error as resolved:

    >>> resolved = record.mark_resolved()
    >>> resolved.resolved
    True
    >>> resolved.resolved_at
    datetime.datetime(2024, 1, 15, 10, 30, 0, tzinfo=datetime.timezone.utc)

    Error chaining (wrapped exceptions):

    >>> inner_record = ErrorRecord(
    ...     error_id="err_01HQ7...",
    ...     error_type="SSLError",
    ...     message="Certificate verify failed",
    ... )
    >>> outer_record = ErrorRecord(
    ...     error_id="err_01HQ8...",
    ...     error_type="ConnectionError",
    ...     message="SSL handshake failed",
    ...     caused_by="err_01HQ7...",  # Links to inner error
    ... )

    Performance
    -----------
    - Storage: ~2-5KB per record (stack_trace can be large)
    - Indexing: error_id primary key, category for filtering
    - Resolution: mark_resolved() creates new immutable record

    Guardrails
    ----------
    - error_id should be unique (ULID recommended)
    - mark_resolved() returns new instance (immutability pattern)
    - context defaults to empty ErrorContext if not provided

    Context
    -------
    ErrorRecord is stored by error tracking systems and queried by
    dashboards. The separation from ErrorContext allows runtime code
    to use lightweight context while persistence uses full records.

    Tags
    ----
    :tag domain-model: Core domain concept
    :tag error-handling: Error persistence
    :tag observability: Dashboard and monitoring
    :tag resolution: Error resolution workflow

    Doc-Types
    ---------
    :api-ref: entityspine.domain.errors.ErrorRecord
    :related: ErrorContext, ErrorCategory, ErrorSeverity

    Attributes
    ----------
    error_id : str
        Unique identifier for this error occurrence.
    error_type : str
        Exception class name or error type.
    message : str
        Human-readable error message.
    context : ErrorContext
        Structured error context with full metadata.
    stack_trace : str | None
        Optional stack trace for debugging.
    caused_by : str | None
        error_id of causing error (for exception chaining).
    resolved : bool
        Whether error has been acknowledged/resolved.
    resolved_at : datetime | None
        When error was resolved.
    """

    error_id: str
    error_type: str
    message: str
    context: ErrorContext = field(default_factory=ErrorContext)
    stack_trace: str | None = None
    caused_by: str | None = None  # error_id of causing error
    resolved: bool = False
    resolved_at: datetime | None = None

    @property
    def is_retryable(self) -> bool:
        """True if error context indicates retryability."""
        return self.context.retryable or False

    @property
    def category(self) -> ErrorCategory:
        """Shortcut to context.category."""
        return self.context.category

    def mark_resolved(self) -> ErrorRecord:
        """Create copy marked as resolved."""
        return ErrorRecord(
            error_id=self.error_id,
            error_type=self.error_type,
            message=self.message,
            context=self.context,
            stack_trace=self.stack_trace,
            caused_by=self.caused_by,
            resolved=True,
            resolved_at=datetime.now(UTC),
        )


# =============================================================================
# Helper Functions
# =============================================================================


def create_error_context(
    category: ErrorCategory | str,
    *,
    pipeline: str | None = None,
    source_name: str | None = None,
    url: str | None = None,
    http_status: int | None = None,
    **metadata: Any,
) -> ErrorContext:
    """
    Factory function for creating ErrorContext with common defaults.
    
    Args:
        category: Error category (string or enum)
        pipeline: Pipeline/process name
        source_name: Data source identifier
        url: Request URL if applicable
        http_status: HTTP status if applicable
        **metadata: Additional context
        
    Returns:
        Configured ErrorContext
        
    Example:
        >>> ctx = create_error_context(
        ...     "SOURCE",
        ...     pipeline="ingest_sec",
        ...     url="https://www.sec.gov/...",
        ...     http_status=503,
        ...     filing_type="10-K",
        ... )
    """
    if isinstance(category, str):
        category = ErrorCategory(category)

    return ErrorContext(
        category=category,
        pipeline=pipeline,
        source_name=source_name,
        url=url,
        http_status=http_status,
        metadata=metadata,
    )


def is_retryable_category(category: ErrorCategory | str) -> bool:
    """
    Check if an error category is typically retryable.
    
    Args:
        category: Error category to check
        
    Returns:
        True if category is typically retryable
    """
    if isinstance(category, str):
        category = ErrorCategory(category)
    return category.is_retryable()
