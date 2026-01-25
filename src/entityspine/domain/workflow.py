"""
Workflow and Execution Domain Models.

Provides stdlib-only dataclasses for:
- Pipeline execution tracking (ExecutionContext)
- Result[T] pattern for explicit success/failure handling
- Workflow stage and task modeling
- Multi-stage manifest tracking

These models define the WHAT (domain concepts) without the HOW (storage).
spine-core imports these and adds database/persistence logic.

DESIGN PRINCIPLES:
- Stdlib-only: No third-party dependencies
- Domain-focused: Business concepts, not infrastructure
- Composable: Can be used standalone or with spine-core

Migration Note:
    These models were extracted from spine-core to provide a clean
    separation between domain concepts and infrastructure concerns.
    spine-core now imports from entityspine for these types.

Example:
    >>> from entityspine.domain import ExecutionContext, new_execution_context
    >>> ctx = new_execution_context(batch_id="backfill_2026-01-29")
    >>> child = ctx.child()
    >>> assert child.parent_execution_id == ctx.execution_id
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Generic, TypeVar

# =============================================================================
# Type Variables
# =============================================================================

T = TypeVar("T")
U = TypeVar("U")


# =============================================================================
# Workflow Status Enums
# =============================================================================


class WorkflowStatus(str, Enum):
    """
    Status of a workflow execution.
    
    Workflows progress through states:
    PENDING → RUNNING → COMPLETED/FAILED/CANCELLED
    """

    PENDING = "PENDING"           # Not yet started
    RUNNING = "RUNNING"           # Currently executing
    PAUSED = "PAUSED"             # Temporarily halted (resumable)
    COMPLETED = "COMPLETED"       # Successfully finished
    FAILED = "FAILED"             # Finished with error
    CANCELLED = "CANCELLED"       # Manually stopped
    SKIPPED = "SKIPPED"           # Bypassed (dependency not met)


class TaskStatus(str, Enum):
    """
    Status of an individual task within a workflow.
    
    Similar to WorkflowStatus but for atomic units of work.
    """

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    RETRYING = "RETRYING"         # Failed, attempting retry


class StageStatus(str, Enum):
    """
    Status of a workflow stage (group of related tasks).
    
    Used by WorkManifest for multi-stage pipeline tracking.
    """

    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class QualityStatus(str, Enum):
    """
    Result status of a quality check.
    
    Three-level outcome for data validation:
    - PASS: Check succeeded
    - WARN: Check passed with concerns
    - FAIL: Check failed
    """

    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


class QualityCategory(str, Enum):
    """
    Category of quality check for classification.
    
    Used to organize checks and route failures appropriately.
    """

    INTEGRITY = "INTEGRITY"           # Data structure correctness
    COMPLETENESS = "COMPLETENESS"     # Data coverage/availability
    CONSISTENCY = "CONSISTENCY"       # Cross-reference agreement
    BUSINESS_RULE = "BUSINESS_RULE"   # Domain-specific rules
    FRESHNESS = "FRESHNESS"           # Data timeliness


# =============================================================================
# Execution Context
# =============================================================================


@dataclass
class ExecutionContext:
    """
    Context passed through pipeline execution for lineage tracking.
    
    ExecutionContext carries execution metadata through pipeline stages, enabling
    full data lineage from source ingestion to final output. It links parent-child
    executions, batches related runs, and captures timing and metadata.
    
    Manifesto:
        EntitySpine processes data through multi-stage pipelines (Principle #5):
        SEC filing → parse → normalize → resolve → enrich → store. ExecutionContext
        makes this lineage explicit and traceable. When you query "why does Apple
        have two CIKs?", the context links back to which batch, which sub-pipeline,
        and which source file produced each claim. This is critical for debugging
        entity resolution conflicts and for audit compliance.
    
    Architecture:
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
    
    Features:
        - Automatic UUID generation for execution_id
        - Parent-child linking via parent_execution_id
        - Batch grouping via batch_id for related operations
        - Workflow naming for human-readable identification
        - Metadata dict for extensible context (source, params, etc.)
        - Elapsed time tracking via elapsed_seconds property
        - Immutable child() method for safe sub-context creation
    
    Examples:
        >>> # Root execution
        >>> ctx = new_execution_context(batch_id="backfill_2026-01-29")
        >>> ctx.is_root
        True
        
        >>> # Child execution (sub-pipeline)
        >>> child_ctx = ctx.child(workflow_name="normalize")
        >>> child_ctx.parent_execution_id == ctx.execution_id
        True
        >>> child_ctx.batch_id == ctx.batch_id
        True
        
        >>> # With metadata
        >>> ctx = new_execution_context(
        ...     batch_id="daily_load",
        ...     workflow_name="ingest_sec_filings",
        ...     source="SEC_EDGAR",
        ...     filing_types=["10-K", "10-Q"],
        ... )
        >>> ctx.metadata["source"]
        'SEC_EDGAR'
    
    Performance:
        - Construction: O(1), ~100ns (UUID generation dominates)
        - child(): O(1), ~100ns
        - elapsed_seconds: O(1), ~50ns
    
    Guardrails:
        - Do NOT reuse execution_id across different runs
          ✅ Instead: Create new context with new_execution_context()
        - Do NOT modify metadata in place
          ✅ Instead: Use with_metadata() to create new context
    
    Context:
        Problem: Multi-stage pipelines lose track of data provenance, making it
                 impossible to debug "where did this bad data come from?"
        Solution: ExecutionContext creates an explicit execution tree with
                  linkable IDs, propagated metadata, and timing information.
    
    Tags:
        - execution_tracking
        - data_lineage
        - pipeline_orchestration
        - domain_model
        - stdlib_only
    
    Doc-Types:
        - MANIFESTO (section: "Core Principles", priority: 10)
        - FEATURES (section: "Pipeline Execution", priority: 9)
        - API_REFERENCE (section: "Workflow Models", priority: 8)
    
    Attributes:
        execution_id: Unique ID for this execution (auto-generated ULID/UUID)
        batch_id: Shared ID for related executions (e.g., a backfill run)
        parent_execution_id: ID of the pipeline that spawned this one
        workflow_name: Name of the workflow being executed
        started_at: When this execution began
        metadata: Additional context (source, parameters, etc.)
    """

    execution_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    batch_id: str | None = None
    parent_execution_id: str | None = None
    workflow_name: str | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)

    def child(self, workflow_name: str | None = None) -> ExecutionContext:
        """
        Create child context for sub-pipeline.
        
        Inherits batch_id, sets parent_execution_id to this context's id.
        
        Args:
            workflow_name: Optional name for the child workflow
            
        Returns:
            New ExecutionContext linked to this one
        """
        return ExecutionContext(
            batch_id=self.batch_id,
            parent_execution_id=self.execution_id,
            workflow_name=workflow_name,
        )

    def with_batch(self, batch_id: str) -> ExecutionContext:
        """
        Create copy with batch_id set.
        
        Args:
            batch_id: New batch identifier
            
        Returns:
            Copy of this context with updated batch_id
        """
        return ExecutionContext(
            execution_id=self.execution_id,
            batch_id=batch_id,
            parent_execution_id=self.parent_execution_id,
            workflow_name=self.workflow_name,
            started_at=self.started_at,
            metadata=dict(self.metadata),
        )

    def with_metadata(self, **kwargs: Any) -> ExecutionContext:
        """
        Create copy with additional metadata.
        
        Args:
            **kwargs: Key-value pairs to add to metadata
            
        Returns:
            Copy with updated metadata
        """
        new_meta = {**self.metadata, **kwargs}
        return ExecutionContext(
            execution_id=self.execution_id,
            batch_id=self.batch_id,
            parent_execution_id=self.parent_execution_id,
            workflow_name=self.workflow_name,
            started_at=self.started_at,
            metadata=new_meta,
        )

    @property
    def is_root(self) -> bool:
        """True if this is a root execution (no parent)."""
        return self.parent_execution_id is None

    @property
    def elapsed_seconds(self) -> float:
        """Seconds since execution started."""
        return (datetime.now(UTC) - self.started_at).total_seconds()


def new_execution_context(
    batch_id: str | None = None,
    workflow_name: str | None = None,
    **metadata: Any,
) -> ExecutionContext:
    """
    Create new root execution context.
    
    Factory function for creating ExecutionContext with common defaults.
    
    Args:
        batch_id: Optional batch identifier for grouping executions
        workflow_name: Optional workflow name
        **metadata: Additional context metadata
        
    Returns:
        New ExecutionContext ready for use
        
    Example:
        >>> ctx = new_execution_context(
        ...     batch_id="backfill_2026-01-29",
        ...     workflow_name="ingest_sec_filings",
        ...     source="SEC_EDGAR",
        ... )
    """
    return ExecutionContext(
        batch_id=batch_id,
        workflow_name=workflow_name,
        metadata=metadata,
    )


def new_batch_id(prefix: str = "") -> str:
    """
    Generate a new batch ID.
    
    Format: {prefix}_{timestamp}_{short_uuid}
    
    Args:
        prefix: Optional prefix for the batch ID
        
    Returns:
        Unique batch identifier
        
    Example:
        >>> new_batch_id("backfill")
        'backfill_20260129T150022_a1b2c3d4'
        >>> new_batch_id()
        'batch_20260129T150022_e5f6g7h8'
    """
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    short_id = str(uuid.uuid4())[:8]
    return f"{prefix}_{ts}_{short_id}" if prefix else f"batch_{ts}_{short_id}"


# =============================================================================
# Result Pattern
# =============================================================================


@dataclass(frozen=True, slots=True)
class Ok(Generic[T]):
    """
    Successful result containing a value.
    
    Ok is the success variant of the Result[T] pattern, wrapping a value of type T.
    It provides monadic operations (map, flat_map) for composing operations that
    might fail, enabling railway-oriented programming without exceptions.
    
    Manifesto:
        EntitySpine uses the Result[T] pattern (Principle #3) to make success
        and failure explicit in return types. This eliminates the "hidden control
        flow" problem where exceptions can bubble up unexpectedly. Every operation
        that can fail returns Result[T], forcing callers to handle both cases.
        This is especially critical for entity resolution where partial failures
        (e.g., "found entity but missing CUSIP") are common and meaningful.
    
    Architecture:
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
    
    Features:
        - Immutable (frozen dataclass) for thread safety
        - Generic over T for type-safe value extraction
        - Monadic operations: map, flat_map, and_then
        - Safe unwrapping: unwrap_or, unwrap_or_else
        - Composable with Err via Result[T] union type
    
    Examples:
        >>> result: Result[int] = Ok(42)
        >>> result.is_ok()
        True
        >>> result.unwrap()
        42
        
        >>> # Chaining operations
        >>> Ok(10).map(lambda x: x * 2).unwrap()
        20
        
        >>> # Railway-oriented programming
        >>> def parse(s: str) -> Result[int]:
        ...     return Ok(int(s)) if s.isdigit() else Err(ValueError("not a number"))
        >>> def double(x: int) -> Result[int]:
        ...     return Ok(x * 2)
        >>> parse("5").flat_map(double).unwrap()
        10
    
    Performance:
        - Construction: O(1), ~50ns
        - is_ok/is_err: O(1), ~10ns
        - map/flat_map: O(1) + O(f), depends on mapped function
    
    Guardrails:
        - Do NOT catch exceptions to return Ok
          ✅ Instead: Use try_result() helper function
        - Do NOT call unwrap() without checking is_ok()
          ✅ Instead: Use unwrap_or() or pattern match
    
    Context:
        Problem: Exception-based error handling hides control flow and makes
                 partial failures hard to reason about.
        Solution: Explicit Result[T] types force callers to handle both paths,
                  with composable operations for clean error propagation.
    
    Tags:
        - result_pattern
        - domain_model
        - functional_programming
        - error_handling
        - stdlib_only
    
    Doc-Types:
        - MANIFESTO (section: "Core Principles", priority: 10)
        - FEATURES (section: "Result Pattern", priority: 10)
        - API_REFERENCE (section: "Domain Models", priority: 9)
    """

    value: T

    def is_ok(self) -> bool:
        """Return True (this is a success)."""
        return True

    def is_err(self) -> bool:
        """Return False (this is not an error)."""
        return False

    def unwrap(self) -> T:
        """Get the value. Safe for Ok."""
        return self.value

    def unwrap_or(self, default: T) -> T:
        """Get value or default (always returns value for Ok)."""
        return self.value

    def unwrap_or_else(self, f: Callable[[Exception], T]) -> T:
        """Get value or call f with error (always returns value for Ok)."""
        return self.value

    def map(self, f: Callable[[T], U]) -> Result[U]:
        """Transform the value if Ok."""
        return Ok(f(self.value))

    def flat_map(self, f: Callable[[T], Result[U]]) -> Result[U]:
        """Chain to another Result-returning function."""
        return f(self.value)

    def map_err(self, f: Callable[[Exception], Exception]) -> Result[T]:
        """Transform error if Err (no-op for Ok)."""
        return self

    def and_then(self, f: Callable[[T], Result[U]]) -> Result[U]:
        """Alias for flat_map."""
        return self.flat_map(f)

    def or_else(self, f: Callable[[Exception], Result[T]]) -> Result[T]:
        """Return self if Ok, otherwise call f with error."""
        return self


@dataclass(frozen=True, slots=True)
class Err(Generic[T]):
    """
    Failed result containing an error.
    
    Err is the failure variant of the Result[T] pattern, wrapping an Exception.
    It preserves error information while providing the same interface as Ok[T],
    enabling uniform handling of success and failure through monadic operations.
    
    Manifesto:
        EntitySpine uses the Result[T] pattern (Principle #3) because SEC data
        processing involves many partial failures: missing identifiers, stale
        mappings, ambiguous name matches, network timeouts. Rather than throwing
        exceptions that interrupt processing, Err captures failures as values
        that can be logged, aggregated, or retried. This is essential for batch
        pipelines where one bad record shouldn't abort an entire 14,000-company
        load.
    
    Architecture:
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
    
    Features:
        - Immutable (frozen dataclass) for thread safety
        - Preserves full exception with traceback
        - map() is no-op (preserves error)
        - map_err() transforms the error
        - or_else() enables recovery attempts
        - unwrap() re-raises the original exception
    
    Examples:
        >>> result: Result[int] = Err(ValueError("invalid input"))
        >>> result.is_err()
        True
        >>> result.unwrap()  # Raises the error
        Traceback (most recent call last):
            ...
        ValueError: invalid input
        
        >>> # Safe default
        >>> Err(ValueError("bad")).unwrap_or(0)
        0
        
        >>> # Error recovery
        >>> Err(ValueError("bad")).or_else(lambda e: Ok(42)).unwrap()
        42
        
        >>> # Transform error
        >>> def wrap_error(e): return RuntimeError(f"wrapped: {e}")
        >>> Err(ValueError("x")).map_err(wrap_error).error
        RuntimeError('wrapped: x')
    
    Performance:
        - Construction: O(1), ~50ns
        - is_ok/is_err: O(1), ~10ns
        - map (no-op): O(1), ~20ns
        - unwrap (raises): O(1), ~100ns
    
    Guardrails:
        - Do NOT swallow errors silently with unwrap_or
          ✅ Instead: Log or aggregate errors before providing defaults
        - Do NOT create Err with non-Exception types
          ✅ Instead: Wrap strings in ValueError("message")
    
    Context:
        Problem: Exceptions interrupt processing and lose context when caught
                 far from where they occurred.
        Solution: Err wraps exceptions as values, preserving context and
                  enabling error aggregation in batch operations.
    
    Tags:
        - result_pattern
        - domain_model
        - functional_programming
        - error_handling
        - stdlib_only
    
    Doc-Types:
        - MANIFESTO (section: "Core Principles", priority: 10)
        - FEATURES (section: "Result Pattern", priority: 10)
        - API_REFERENCE (section: "Domain Models", priority: 9)
    """

    error: Exception

    def is_ok(self) -> bool:
        """Return False (this is an error)."""
        return False

    def is_err(self) -> bool:
        """Return True (this is an error)."""
        return True

    def unwrap(self) -> T:
        """Raise the error."""
        raise self.error

    def unwrap_or(self, default: T) -> T:
        """Get default (always returns default for Err)."""
        return default

    def unwrap_or_else(self, f: Callable[[Exception], T]) -> T:
        """Call f with the error to produce a value."""
        return f(self.error)

    def map(self, f: Callable[[T], U]) -> Result[U]:
        """No-op for Err (preserves error)."""
        return Err(self.error)

    def flat_map(self, f: Callable[[T], Result[U]]) -> Result[U]:
        """No-op for Err (preserves error)."""
        return Err(self.error)

    def map_err(self, f: Callable[[Exception], Exception]) -> Result[T]:
        """Transform the error."""
        return Err(f(self.error))

    def and_then(self, f: Callable[[T], Result[U]]) -> Result[U]:
        """No-op for Err."""
        return Err(self.error)

    def or_else(self, f: Callable[[Exception], Result[T]]) -> Result[T]:
        """Call f with error to potentially recover."""
        return f(self.error)


# Type alias for Result
Result = Ok[T] | Err[T]


def try_result(f: Callable[[], T], *exception_types: type[Exception]) -> Result[T]:
    """
    Execute a function and wrap in Result.
    
    Catches specified exceptions (or all if none specified) and wraps in Err.
    
    Args:
        f: Function to execute
        *exception_types: Exception types to catch (default: Exception)
        
    Returns:
        Ok(value) on success, Err(exception) on failure
        
    Example:
        >>> def risky() -> int:
        ...     return int("not a number")
        >>> result = try_result(risky, ValueError)
        >>> result.is_err()
        True
    """
    exceptions = exception_types or (Exception,)
    try:
        return Ok(f())
    except exceptions as e:
        return Err(e)


# =============================================================================
# Workflow Task/Stage Models
# =============================================================================


@dataclass
class TaskResult:
    """
    Result of executing a single task.
    
    Captures outcome, metrics, and optional error details.
    
    Attributes:
        task_name: Name/identifier of the task
        status: Final task status
        started_at: When task execution began
        completed_at: When task execution ended
        row_count: Number of records processed (if applicable)
        metrics: Additional task-specific metrics
        error_message: Error details if status is FAILED
        retries: Number of retry attempts
    """

    task_name: str
    status: TaskStatus
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    row_count: int | None = None
    metrics: dict[str, Any] = field(default_factory=dict)
    error_message: str | None = None
    retries: int = 0

    @property
    def duration_seconds(self) -> float | None:
        """Task duration in seconds, or None if not completed."""
        if self.completed_at is None:
            return None
        return (self.completed_at - self.started_at).total_seconds()

    @property
    def is_success(self) -> bool:
        """True if task completed successfully."""
        return self.status == TaskStatus.COMPLETED

    def mark_completed(self, row_count: int | None = None, **metrics: Any) -> TaskResult:
        """Create copy marked as completed with metrics."""
        return TaskResult(
            task_name=self.task_name,
            status=TaskStatus.COMPLETED,
            started_at=self.started_at,
            completed_at=datetime.now(UTC),
            row_count=row_count,
            metrics={**self.metrics, **metrics},
            retries=self.retries,
        )

    def mark_failed(self, error: str | Exception) -> TaskResult:
        """Create copy marked as failed with error."""
        return TaskResult(
            task_name=self.task_name,
            status=TaskStatus.FAILED,
            started_at=self.started_at,
            completed_at=datetime.now(UTC),
            row_count=self.row_count,
            metrics=self.metrics,
            error_message=str(error),
            retries=self.retries,
        )


@dataclass
class StageRecord:
    """
    Record of a workflow stage (used by WorkManifest).
    
    Tracks the state of one stage in a multi-stage workflow.
    This is the domain model; persistence is handled by spine-core.
    
    Attributes:
        stage: Stage name (e.g., "INGESTED", "NORMALIZED")
        stage_rank: Numeric ordering for stage comparison
        status: Current stage status
        row_count: Records processed in this stage
        metrics: Stage-specific metrics
        execution_id: Execution that last updated this stage
        batch_id: Batch this stage belongs to
        updated_at: When stage was last updated
    """

    stage: str
    stage_rank: int
    status: StageStatus = StageStatus.PENDING
    row_count: int | None = None
    metrics: dict[str, Any] = field(default_factory=dict)
    execution_id: str | None = None
    batch_id: str | None = None
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __repr__(self) -> str:
        return f"StageRecord(stage={self.stage!r}, rank={self.stage_rank}, status={self.status.value})"

    @property
    def is_completed(self) -> bool:
        """True if stage is completed."""
        return self.status == StageStatus.COMPLETED


@dataclass
class QualityResult:
    """
    Result of one quality check.
    
    Captures the outcome of a data validation check.
    
    Attributes:
        check_name: Name of the quality check
        category: Type of quality check
        status: PASS, WARN, or FAIL
        message: Human-readable explanation
        actual_value: What was found
        expected_value: What was expected
        checked_at: When the check was performed
    """

    check_name: str
    category: QualityCategory
    status: QualityStatus
    message: str
    actual_value: Any = None
    expected_value: Any = None
    checked_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def is_passing(self) -> bool:
        """True if status is PASS or WARN."""
        return self.status in (QualityStatus.PASS, QualityStatus.WARN)

    @property
    def is_failing(self) -> bool:
        """True if status is FAIL."""
        return self.status == QualityStatus.FAIL


# =============================================================================
# Workflow Definition Models
# =============================================================================


@dataclass
class WorkflowStep:
    """
    Definition of a single step in a workflow.
    
    Describes a unit of work without execution logic.
    
    Attributes:
        name: Step identifier
        description: Human-readable description
        depends_on: Steps that must complete before this one
        timeout_seconds: Maximum execution time
        retries: Number of retry attempts on failure
        metadata: Additional step configuration
    """

    name: str
    description: str = ""
    depends_on: list[str] = field(default_factory=list)
    timeout_seconds: int | None = None
    retries: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowDefinition:
    """
    Definition of a complete workflow.
    
    Describes workflow structure without execution logic.
    
    Attributes:
        name: Workflow identifier
        description: Human-readable description
        steps: Ordered list of workflow steps
        version: Workflow version for tracking changes
        metadata: Additional workflow configuration
    
    Example:
        >>> workflow = WorkflowDefinition(
        ...     name="ingest_sec_filings",
        ...     description="Fetch and process SEC EDGAR filings",
        ...     steps=[
        ...         WorkflowStep("fetch", "Download filings from EDGAR"),
        ...         WorkflowStep("parse", "Extract data from filings", depends_on=["fetch"]),
        ...         WorkflowStep("store", "Save to database", depends_on=["parse"]),
        ...     ],
        ... )
    """

    name: str
    description: str = ""
    steps: list[WorkflowStep] = field(default_factory=list)
    version: str = "1.0.0"
    metadata: dict[str, Any] = field(default_factory=dict)

    def get_step(self, name: str) -> WorkflowStep | None:
        """Get step by name, or None if not found."""
        for step in self.steps:
            if step.name == name:
                return step
        return None

    @property
    def step_names(self) -> list[str]:
        """List of all step names in order."""
        return [s.name for s in self.steps]


@dataclass
class WorkflowRun:
    """
    Record of a workflow execution.
    
    Tracks a single run of a workflow definition.
    
    Attributes:
        workflow_name: Name of the workflow being run
        run_id: Unique identifier for this run
        status: Current workflow status
        context: Execution context for lineage
        started_at: When the run began
        completed_at: When the run finished
        task_results: Results of individual tasks
        error_message: Error if workflow failed
    """

    workflow_name: str
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: WorkflowStatus = WorkflowStatus.PENDING
    context: ExecutionContext | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    task_results: list[TaskResult] = field(default_factory=list)
    error_message: str | None = None

    @property
    def duration_seconds(self) -> float | None:
        """Run duration in seconds, or None if not completed."""
        if self.started_at is None or self.completed_at is None:
            return None
        return (self.completed_at - self.started_at).total_seconds()

    @property
    def is_running(self) -> bool:
        """True if workflow is currently executing."""
        return self.status == WorkflowStatus.RUNNING

    @property
    def is_finished(self) -> bool:
        """True if workflow has reached a terminal state."""
        return self.status in (
            WorkflowStatus.COMPLETED,
            WorkflowStatus.FAILED,
            WorkflowStatus.CANCELLED,
        )

    def get_task_result(self, task_name: str) -> TaskResult | None:
        """Get result for a specific task, or None if not found."""
        for result in self.task_results:
            if result.task_name == task_name:
                return result
        return None
