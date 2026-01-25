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
from datetime import datetime, timezone
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
    Structured context for error tracking and debugging.
    
    Provides a standard way to attach metadata to errors for:
    - Log aggregation and searching
    - Alert routing and deduplication
    - Root cause analysis
    - Error correlation across services
    
    Attributes:
        category: Error classification
        severity: Error severity level
        pipeline: Name of the pipeline/process
        workflow: Name of the workflow
        step: Current step/stage
        run_id: Workflow run identifier
        execution_id: Execution context ID
        source_name: Data source name (e.g., "SEC_EDGAR")
        source_type: Data source type (e.g., "API", "FILE")
        url: Request URL if applicable
        http_status: HTTP status code if applicable
        retry_count: Number of retries attempted
        retryable: Whether error is retryable
        metadata: Additional context (open-ended)
        timestamp: When the error occurred
    
    Example:
        >>> ctx = ErrorContext(
        ...     category=ErrorCategory.SOURCE,
        ...     pipeline="ingest_sec_filings",
        ...     source_name="SEC_EDGAR",
        ...     url="https://www.sec.gov/cgi-bin/browse-edgar",
        ...     http_status=503,
        ...     retryable=True,
        ... )
        >>> ctx.to_dict()
        {'category': 'SOURCE', 'pipeline': 'ingest_sec_filings', ...}
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
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
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
    
    def with_retry(self, count: int, after_seconds: int | None = None) -> "ErrorContext":
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
    
    def with_metadata(self, **kwargs: Any) -> "ErrorContext":
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
    Persistent record of an error occurrence.
    
    For storing errors in databases or logs with full context.
    This is the domain model; persistence is handled elsewhere.
    
    Attributes:
        error_id: Unique identifier for this error occurrence
        error_type: Exception class name or error type
        message: Human-readable error message
        context: Structured error context
        stack_trace: Optional stack trace
        caused_by: ID of causing error (for chains)
        resolved: Whether error has been acknowledged/resolved
        resolved_at: When error was resolved
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
    
    def mark_resolved(self) -> "ErrorRecord":
        """Create copy marked as resolved."""
        return ErrorRecord(
            error_id=self.error_id,
            error_type=self.error_type,
            message=self.message,
            context=self.context,
            stack_trace=self.stack_trace,
            caused_by=self.caused_by,
            resolved=True,
            resolved_at=datetime.now(timezone.utc),
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
