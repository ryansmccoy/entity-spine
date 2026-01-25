"""
Factory functions for creating domain objects.

STDLIB ONLY - NO PYDANTIC.

These factory functions provide convenient ways to create domain objects
with common configurations and proper validation.
"""

from entityspine.domain.candidate import ResolutionCandidate
from entityspine.domain.claim import IdentifierClaim
from entityspine.domain.data_quality import DataQualityResult, DataQualityRule
from entityspine.domain.entity import Entity
from entityspine.domain.entity_events import MergeEvent
from entityspine.domain.enums import (
    DataQualitySeverity,
    EntityType,
    IdentifierScheme,
    MatchReason,
    ProvenanceKind,
    ResolutionStatus,
    ResolutionTier,
    RunStatus,
    SecurityType,
    VendorNamespace,
)
from entityspine.domain.explanation import Explanation, ResolutionRun
from entityspine.domain.listing import Listing
from entityspine.domain.provenance import Provenance
from entityspine.domain.resolution import ResolutionResult
from entityspine.domain.security import Security

# =============================================================================
# Entity Factories
# =============================================================================


def create_entity(
    primary_name: str,
    entity_id: str | None = None,
    entity_type: EntityType = EntityType.ORGANIZATION,
    source_system: str = "unknown",
    source_id: str | None = None,
    **kwargs,
) -> Entity:
    """
    Create an Entity with common defaults.

    Args:
        primary_name: Legal/trading name
        entity_id: Optional ULID (auto-generated if not provided)
        entity_type: Type of entity
        source_system: Where this record came from
        source_id: ID in the source system
        **kwargs: Additional Entity fields
    """
    params = {
        "primary_name": primary_name,
        "entity_type": entity_type,
        "source_system": source_system,
    }
    if entity_id:
        params["entity_id"] = entity_id
    if source_id:
        params["source_id"] = source_id
    params.update(kwargs)
    return Entity(**params)


# =============================================================================
# Security Factories
# =============================================================================


def create_security(
    entity_id: str,
    security_id: str | None = None,
    security_type: SecurityType = SecurityType.COMMON_STOCK,
    description: str | None = None,
    **kwargs,
) -> Security:
    """
    Create a Security with common defaults.

    Args:
        entity_id: FK to issuing Entity
        security_id: Optional ULID (auto-generated if not provided)
        security_type: Type of security
        description: Human-readable description
        **kwargs: Additional Security fields
    """
    params = {
        "entity_id": entity_id,
        "security_type": security_type,
    }
    if security_id:
        params["security_id"] = security_id
    if description:
        params["description"] = description
    params.update(kwargs)
    return Security(**params)


# =============================================================================
# Listing Factories
# =============================================================================


def create_listing(
    security_id: str,
    ticker: str,
    listing_id: str | None = None,
    exchange: str = "",
    mic: str | None = None,
    is_primary: bool = False,
    **kwargs,
) -> Listing:
    """
    Create a Listing with common defaults.

    Args:
        security_id: FK to Security
        ticker: Ticker symbol
        listing_id: Optional ULID (auto-generated if not provided)
        exchange: Exchange name/code
        mic: Market Identifier Code
        is_primary: Whether this is the primary listing
        **kwargs: Additional Listing fields
    """
    params = {
        "security_id": security_id,
        "ticker": ticker,
        "exchange": exchange,
        "is_primary": is_primary,
    }
    if listing_id:
        params["listing_id"] = listing_id
    if mic:
        params["mic"] = mic
    params.update(kwargs)
    return Listing(**params)


# =============================================================================
# Claim Factories
# =============================================================================


def create_claim(
    scheme: IdentifierScheme,
    value: str,
    entity_id: str | None = None,
    security_id: str | None = None,
    listing_id: str | None = None,
    namespace: VendorNamespace = VendorNamespace.INTERNAL,
    source: str = "unknown",
    confidence: float = 1.0,
    **kwargs,
) -> IdentifierClaim:
    """
    Create an IdentifierClaim with common defaults.

    Args:
        scheme: Identifier scheme
        value: Identifier value (will be normalized)
        entity_id: Entity target (for entity-scoped schemes)
        security_id: Security target (for security-scoped schemes)
        listing_id: Listing target (for listing-scoped schemes)
        namespace: Vendor/source namespace
        source: Human-readable source description
        confidence: Confidence score 0.0-1.0
        **kwargs: Additional IdentifierClaim fields
    """
    params = {
        "scheme": scheme,
        "value": value,
        "namespace": namespace,
        "source": source,
        "confidence": confidence,
    }
    if entity_id:
        params["entity_id"] = entity_id
    if security_id:
        params["security_id"] = security_id
    if listing_id:
        params["listing_id"] = listing_id
    params.update(kwargs)
    return IdentifierClaim(**params)


# =============================================================================
# Candidate Factories
# =============================================================================


def create_candidate(
    score: float,
    match_reason: MatchReason,
    entity_id: str | None = None,
    security_id: str | None = None,
    listing_id: str | None = None,
    matched_scheme: str | None = None,
    matched_value: str | None = None,
    **kwargs,
) -> ResolutionCandidate:
    """
    Create a ResolutionCandidate.

    Args:
        score: Match confidence score 0.0-1.0
        match_reason: Why this candidate matched
        entity_id: Matched entity ID
        security_id: Matched security ID
        listing_id: Matched listing ID
        matched_scheme: Which identifier scheme matched
        matched_value: The actual value that matched
        **kwargs: Additional ResolutionCandidate fields
    """
    params = {
        "score": score,
        "match_reason": match_reason,
    }
    if entity_id:
        params["entity_id"] = entity_id
    if security_id:
        params["security_id"] = security_id
    if listing_id:
        params["listing_id"] = listing_id
    if matched_scheme:
        params["matched_scheme"] = matched_scheme
    if matched_value:
        params["matched_value"] = matched_value
    params.update(kwargs)
    return ResolutionCandidate(**params)


# =============================================================================
# Resolution Result Factories
# =============================================================================


def found_result(
    entity: Entity,
    query: str,
    tier: ResolutionTier,
    elapsed_ms: float = 0.0,
    warnings: list[str] | None = None,
    security: Security | None = None,
    listing: Listing | None = None,
    confidence: float = 1.0,
    match_reason: MatchReason | None = None,
    candidates: list[ResolutionCandidate] | None = None,
    **kwargs,
) -> ResolutionResult:
    """
    Create a successful resolution result.

    Args:
        entity: The resolved entity
        query: Original query string
        tier: Storage tier that provided the result
        elapsed_ms: Time taken in milliseconds
        warnings: Optional list of warnings
        security: Optional resolved security
        listing: Optional resolved listing
        confidence: Confidence score (default 1.0)
        match_reason: Why this entity was matched
        candidates: List of candidates (created automatically if not provided)
        **kwargs: Additional ResolutionResult fields
    """
    # Build candidates list
    if candidates is None:
        candidates = [
            ResolutionCandidate(
                entity_id=entity.entity_id,
                score=confidence,
                match_reason=match_reason or MatchReason.UNKNOWN,
            )
        ]

    return ResolutionResult(
        entity=entity,
        security=security,
        listing=listing,
        status=ResolutionStatus.FOUND,
        tier=tier,
        query=query,
        elapsed_ms=elapsed_ms,
        warnings=warnings or [],
        confidence=confidence,
        candidates=candidates,
        **kwargs,
    )


def not_found_result(
    query: str,
    tier: ResolutionTier,
    elapsed_ms: float = 0.0,
    warnings: list[str] | None = None,
    **kwargs,
) -> ResolutionResult:
    """
    Create a not-found resolution result.

    Args:
        query: Original query string
        tier: Storage tier that performed the resolution
        elapsed_ms: Time taken in milliseconds
        warnings: Optional list of warnings
        **kwargs: Additional ResolutionResult fields
    """
    return ResolutionResult(
        entity=None,
        status=ResolutionStatus.NOT_FOUND,
        tier=tier,
        query=query,
        elapsed_ms=elapsed_ms,
        warnings=warnings or [],
        confidence=0.0,
        **kwargs,
    )


def ambiguous_result(
    query: str,
    tier: ResolutionTier,
    candidates: list[ResolutionCandidate],
    elapsed_ms: float = 0.0,
    warnings: list[str] | None = None,
    **kwargs,
) -> ResolutionResult:
    """
    Create an ambiguous resolution result with multiple candidates.

    Args:
        query: Original query string
        tier: Storage tier that performed the resolution
        candidates: List of potential matches
        elapsed_ms: Time taken in milliseconds
        warnings: Optional list of warnings
        **kwargs: Additional ResolutionResult fields
    """
    warnings_list = warnings or []
    if "ambiguous_match" not in str(warnings_list):
        warnings_list.append("Multiple candidates matched query")

    return ResolutionResult(
        entity=None,
        status=ResolutionStatus.AMBIGUOUS,
        tier=tier,
        query=query,
        candidates=candidates,
        elapsed_ms=elapsed_ms,
        warnings=warnings_list,
        confidence=0.5 if candidates else 0.0,
        **kwargs,
    )


# =============================================================================
# Audit Trail Factories (v2.3.4)
# =============================================================================


def create_file_provenance(
    namespace: VendorNamespace,
    source_uri: str,
    *,
    file_name: str | None = None,
    source_hash: str | None = None,
    batch_id: str | None = None,
    captured_by: str | None = None,
    notes: str | None = None,
) -> Provenance:
    """
    Create a file-based Provenance record.

    Args:
        namespace: Vendor/source namespace (SEC, FACTSET, etc.).
        source_uri: File path or URL of source.
        file_name: Original filename.
        source_hash: SHA-256 hash for verification.
        batch_id: Batch/job ID for bulk imports.
        captured_by: User/system that captured.
        notes: Additional notes.

    Returns:
        Provenance record with kind=FILE.

    Examples:
        >>> prov = create_file_provenance(
        ...     VendorNamespace.SEC,
        ...     "https://www.sec.gov/files/company_tickers.json",
        ...     file_name="company_tickers.json",
        ... )
    """
    return Provenance(
        kind=ProvenanceKind.FILE,
        namespace=namespace,
        source_uri=source_uri,
        file_name=file_name,
        source_hash=source_hash,
        batch_id=batch_id,
        captured_by=captured_by,
        notes=notes,
    )


def create_api_provenance(
    namespace: VendorNamespace,
    api_endpoint: str,
    *,
    api_params: str | None = None,
    batch_id: str | None = None,
    captured_by: str | None = None,
    notes: str | None = None,
) -> Provenance:
    """
    Create an API-based Provenance record.

    Args:
        namespace: Vendor/source namespace (FACTSET, BLOOMBERG, etc.).
        api_endpoint: API endpoint called.
        api_params: JSON string of API parameters.
        batch_id: Batch/job ID for bulk imports.
        captured_by: User/system that captured.
        notes: Additional notes.

    Returns:
        Provenance record with kind=API.

    Examples:
        >>> prov = create_api_provenance(
        ...     VendorNamespace.FACTSET,
        ...     "/symbology/v1/identifier-resolution",
        ...     api_params='{"ids": ["AAPL-US"]}',
        ... )
    """
    return Provenance(
        kind=ProvenanceKind.API,
        namespace=namespace,
        api_endpoint=api_endpoint,
        api_params=api_params,
        batch_id=batch_id,
        captured_by=captured_by,
        notes=notes,
    )


def create_merge_event(
    source_entity_id: str,
    target_entity_id: str,
    reason: str,
    *,
    confidence: float = 1.0,
    merged_by: str | None = None,
    explanation_id: str | None = None,
    run_id: str | None = None,
    source_snapshot: str | None = None,
    notes: str | None = None,
) -> MergeEvent:
    """
    Create a MergeEvent record.

    Args:
        source_entity_id: Entity being merged away.
        target_entity_id: Canonical entity that remains.
        reason: Why the merge happened.
        confidence: Confidence in the decision (0.0-1.0).
        merged_by: User/system that performed merge.
        explanation_id: Link to Explanation record.
        run_id: Link to ResolutionRun if part of batch.
        source_snapshot: JSON snapshot of source entity.
        notes: Additional notes.

    Returns:
        MergeEvent record.

    Examples:
        >>> event = create_merge_event(
        ...     "01HQ8AAA...",
        ...     "01HQ8BBB...",
        ...     "same_cik",
        ...     confidence=1.0,
        ...     merged_by="resolution_pipeline",
        ... )
    """
    return MergeEvent(
        source_entity_id=source_entity_id,
        target_entity_id=target_entity_id,
        reason=reason,
        confidence=confidence,
        merged_by=merged_by,
        explanation_id=explanation_id,
        run_id=run_id,
        source_snapshot=source_snapshot,
        notes=notes,
    )


def create_explanation(
    decision_type: str,
    summary: str,
    *,
    details: str = "",
    factors: dict | None = None,
    confidence: float = 1.0,
    match_scores: dict | None = None,
    rule_hits: tuple[str, ...] | list[str] = (),
) -> Explanation:
    """
    Create an Explanation record.

    Args:
        decision_type: Type of decision (match, reject, merge, split, manual).
        summary: One-line summary.
        details: Detailed explanation text.
        factors: Factors that influenced decision.
        confidence: Confidence in the decision (0.0-1.0).
        match_scores: Individual match scores.
        rule_hits: Rules/heuristics that fired.

    Returns:
        Explanation record.

    Examples:
        >>> exp = create_explanation(
        ...     "match",
        ...     "Matched on CIK with exact name",
        ...     factors={"cik_match": True, "name_score": 1.0},
        ...     confidence=1.0,
        ... )
    """
    return Explanation(
        decision_type=decision_type,
        summary=summary,
        details=details,
        factors=factors or {},
        confidence=confidence,
        match_scores=match_scores or {},
        rule_hits=tuple(rule_hits) if isinstance(rule_hits, list) else rule_hits,
    )


def create_resolution_run(
    input_params: dict | None = None,
    source_record_ids: tuple[str, ...] | list[str] = (),
    *,
    status: RunStatus = RunStatus.RUNNING,
) -> ResolutionRun:
    """
    Create a ResolutionRun record for batch tracking.

    Args:
        input_params: Configuration used for this run.
        source_record_ids: Records to process in this run.
        status: Initial run status.

    Returns:
        ResolutionRun record.

    Examples:
        >>> run = create_resolution_run(
        ...     {"blocking_keys": ["cik", "name_prefix"]},
        ...     ("rec1", "rec2", "rec3"),
        ... )
    """
    return ResolutionRun(
        input_params=input_params or {},
        source_record_ids=tuple(source_record_ids) if isinstance(source_record_ids, list) else source_record_ids,
        status=status,
    )


def create_quality_rule(
    name: str,
    description: str,
    *,
    category: str = "consistency",
    severity: DataQualitySeverity = DataQualitySeverity.WARNING,
    target_type: str = "entity",
    check_expression: str = "",
) -> DataQualityRule:
    """
    Create a DataQualityRule definition.

    Args:
        name: Human-readable rule name.
        description: What the rule checks.
        category: Rule category (completeness, consistency, accuracy, timeliness).
        severity: Impact level (INFO, WARNING, ERROR, CRITICAL).
        target_type: What this rule applies to.
        check_expression: Expression/logic for the check.

    Returns:
        DataQualityRule record.

    Examples:
        >>> rule = create_quality_rule(
        ...     "cik_unique_name",
        ...     "Each CIK should have exactly one primary name",
        ...     severity=DataQualitySeverity.WARNING,
        ... )
    """
    return DataQualityRule(
        name=name,
        description=description,
        category=category,
        severity=severity,
        target_type=target_type,
        check_expression=check_expression,
    )


def create_quality_result(
    rule_id: str,
    rule_name: str,
    passed: bool,
    *,
    message: str = "",
    severity: DataQualitySeverity = DataQualitySeverity.INFO,
    entity_id: str | None = None,
    claim_id: str | None = None,
    run_id: str | None = None,
    details: dict | None = None,
) -> DataQualityResult:
    """
    Create a DataQualityResult record.

    Args:
        rule_id: Rule that was checked.
        rule_name: Name of the rule.
        passed: Whether the check passed.
        message: Human-readable result message.
        severity: Severity level if failed.
        entity_id: Entity this result applies to.
        claim_id: Claim this result applies to.
        run_id: ResolutionRun this check was part of.
        details: Detailed findings.

    Returns:
        DataQualityResult record.

    Examples:
        >>> result = create_quality_result(
        ...     "01HQ8RULE...",
        ...     "cik_unique_name",
        ...     passed=True,
        ...     entity_id="01HQ8ENT...",
        ... )
    """
    return DataQualityResult(
        rule_id=rule_id,
        rule_name=rule_name,
        passed=passed,
        message=message,
        severity=severity,
        entity_id=entity_id,
        claim_id=claim_id,
        run_id=run_id,
        details=details or {},
    )
