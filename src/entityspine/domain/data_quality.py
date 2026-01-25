"""
Data Quality domain models (stdlib dataclass).

STDLIB ONLY - NO PYDANTIC.

These models implement automated data quality checks:
- DataQualityRule: Definition of a quality check
- DataQualityResult: Outcome of running a rule

This enables:
- Quality gates: "Don't merge if data quality score < 0.8"
- Monitoring: "How many CIKs have multiple names?"
- Alerts: "Flag records needing human review"

v2.3.4 Design:
- Rules are reusable definitions
- Results are immutable records of checks performed
- Results link to entities/claims for actionability
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from entityspine.domain.enums import DataQualitySeverity
from entityspine.domain.timestamps import generate_ulid, utc_now


@dataclass(frozen=True, slots=True)
class DataQualityRule:
    """
    Definition of a data quality check.

    DataQualityRule defines a reusable quality check that can be
    applied to entities, claims, or other records.

    Attributes:
        rule_id: ULID primary key.
        name: Human-readable rule name.
        description: Detailed description of what the rule checks.
        category: Rule category (completeness, consistency, accuracy, etc.).
        severity: Impact level (INFO, WARNING, ERROR, CRITICAL).
        target_type: What this rule applies to (entity, claim, listing, etc.).
        check_expression: Expression/logic for the check (for documentation).
        enabled: Whether the rule is active.
        created_at: Record creation timestamp.
        updated_at: Record update timestamp.

    Examples:
        >>> rule = DataQualityRule(
        ...     name="cik_unique_name",
        ...     description="Each CIK should have exactly one primary name",
        ...     category="consistency",
        ...     severity="WARNING",
        ...     target_type="entity",
        ...     check_expression="COUNT(DISTINCT primary_name) WHERE cik = ? == 1",
        ... )
    """

    # Primary key
    rule_id: str = field(default_factory=generate_ulid)

    # Rule definition
    name: str = ""
    description: str = ""
    category: str = "consistency"  # completeness, consistency, accuracy, timeliness
    severity: DataQualitySeverity = DataQualitySeverity.WARNING

    # Target
    target_type: str = "entity"  # entity, claim, listing, security

    # Check logic (for documentation/reference)
    check_expression: str = ""

    # State
    enabled: bool = True

    # Timestamps
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True, slots=True)
class DataQualityResult:
    """
    Result of running a data quality rule.

    DataQualityResult records the outcome of applying a quality rule
    to a specific record or set of records.

    Attributes:
        result_id: ULID primary key.
        rule_id: Rule that was checked.
        rule_name: Name of the rule (denormalized for convenience).
        passed: Whether the check passed.
        severity: Severity level of the result.
        message: Human-readable result message.
        details: JSON dict with detailed findings.
        entity_id: Entity this result applies to.
        claim_id: Claim this result applies to.
        security_id: Security this result applies to.
        listing_id: Listing this result applies to.
        run_id: ResolutionRun this check was part of.
        checked_at: When the check was performed.
        resolved: Whether this issue was resolved.
        resolved_at: When the issue was resolved.
        resolved_by: Who resolved the issue.
        resolution_notes: Notes on how it was resolved.
        created_at: Record creation timestamp.

    Examples:
        Passing result:

        >>> result = DataQualityResult(
        ...     rule_id="01HQ...",
        ...     rule_name="cik_unique_name",
        ...     passed=True,
        ...     message="CIK 0000320193 has exactly one name",
        ...     entity_id="01HQA...",
        ... )

        Failing result:

        >>> result = DataQualityResult(
        ...     rule_id="01HQ...",
        ...     rule_name="cik_unique_name",
        ...     passed=False,
        ...     severity="WARNING",
        ...     message="CIK 0000320193 has 3 different names",
        ...     details={"names": ["Apple Inc.", "APPLE INC", "Apple Inc"]},
        ...     entity_id="01HQA...",
        ... )
    """

    # Primary key
    result_id: str = field(default_factory=generate_ulid)

    # Rule reference
    rule_id: str = ""
    rule_name: str = ""  # Denormalized for convenience

    # Result
    passed: bool = True
    severity: DataQualitySeverity = DataQualitySeverity.INFO
    message: str = ""

    # Details (stored as frozen dict via field)
    details: dict[str, Any] = field(default_factory=dict)

    # Target references (at least one should be set)
    entity_id: str | None = None
    claim_id: str | None = None
    security_id: str | None = None
    listing_id: str | None = None

    # Run reference
    run_id: str | None = None

    # Timing
    checked_at: datetime = field(default_factory=utc_now)

    # Resolution tracking
    resolved: bool = False
    resolved_at: datetime | None = None
    resolved_by: str | None = None
    resolution_notes: str | None = None

    # Timestamps
    created_at: datetime = field(default_factory=utc_now)

    @property
    def is_failure(self) -> bool:
        """Check if this is a failed check (not passed)."""
        return not self.passed

    @property
    def needs_attention(self) -> bool:
        """Check if this result needs human attention."""
        return (
            not self.passed
            and self.severity
            in (
                DataQualitySeverity.WARNING,
                DataQualitySeverity.ERROR,
                DataQualitySeverity.CRITICAL,
            )
            and not self.resolved
        )
