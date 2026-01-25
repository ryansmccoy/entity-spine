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
    
    Every pipeline execution gets an execution_id. When pipelines call
    sub-pipelines, the parent_execution_id links them. Batch operations
    share a batch_id.
    
    Attributes:
        execution_id: Unique ID for this execution (auto-generated ULID/UUID)
        batch_id: Shared ID for related executions (e.g., a backfill run)
        parent_execution_id: ID of the pipeline that spawned this one
        workflow_name: Name of the workflow being executed
        started_at: When this execution began
        metadata: Additional context (source, parameters, etc.)
    
    Example:
        >>> # Root execution
        >>> ctx = new_execution_context(batch_id="backfill_2026-01-29")
        >>> 
        >>> # Child execution (sub-pipeline)
        >>> child_ctx = ctx.child(workflow_name="normalize")
        >>> assert child_ctx.parent_execution_id == ctx.execution_id
        >>> assert child_ctx.batch_id == ctx.batch_id
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
    
    Part of the Result[T] pattern for explicit success/failure handling.
    Immutable and hashable (if value is hashable).
    
    Example:
        >>> result: Result[int] = Ok(42)
        >>> result.is_ok()
        True
        >>> result.unwrap()
        42
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
    
    Part of the Result[T] pattern for explicit success/failure handling.
    
    Example:
        >>> result: Result[int] = Err(ValueError("invalid input"))
        >>> result.is_err()
        True
        >>> result.unwrap()  # Raises the error
        Traceback (most recent call last):
            ...
        ValueError: invalid input
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
