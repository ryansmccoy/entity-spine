"""
API schemas for request/response models.

These are Pydantic models specifically for the API layer.
They wrap the domain models from entityspine.adapters.pydantic.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


def _enum_to_str(value: Any) -> str:
    """Convert enum value to string."""
    if hasattr(value, "name"):
        return value.name.lower()
    elif hasattr(value, "value"):
        return str(value.value)
    else:
        return str(value)


# =============================================================================
# Request Models
# =============================================================================


class BatchResolveRequest(BaseModel):
    """Request for batch resolution."""

    queries: list[str] = Field(
        ...,
        description="List of identifiers to resolve (tickers, CIKs, names, etc.)",
        min_length=1,
        max_length=100,
    )
    as_of: date | None = Field(
        None,
        description="Point-in-time date for temporal resolution",
    )


class ConvertRequest(BaseModel):
    """Request for identifier conversion."""

    value: str = Field(..., description="The identifier value to convert")
    from_scheme: str = Field(..., description="Source identifier scheme (cik, ticker, etc.)")
    to_scheme: str = Field(..., description="Target identifier scheme")


# =============================================================================
# Response Models
# =============================================================================


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "healthy"
    database: str = "connected"
    entities_count: int = 0
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class InfoResponse(BaseModel):
    """API information response."""

    name: str = "EntitySpine API"
    version: str = "0.1.0"
    description: str = "Entity Resolution REST API"
    tier: str = "tier_1"
    endpoints: list[str] = []


class EntityResponse(BaseModel):
    """Entity in API responses."""

    entity_id: str
    primary_name: str
    entity_type: str
    status: str
    source_system: str
    source_id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    # Convenience fields (populated if available)
    cik: str | None = None
    ticker: str | None = None

    @classmethod
    def from_domain(cls, entity: Any) -> "EntityResponse":
        """Create from domain Entity."""
        return cls(
            entity_id=entity.entity_id,
            primary_name=entity.primary_name,
            entity_type=_enum_to_str(entity.entity_type),
            status=_enum_to_str(entity.status),
            source_system=entity.source_system,
            source_id=entity.source_id,
            created_at=entity.created_at if hasattr(entity, "created_at") else None,
            updated_at=entity.updated_at if hasattr(entity, "updated_at") else None,
            metadata=entity.metadata if hasattr(entity, "metadata") else {},
            # CIK is often stored in source_id for SEC entities
            cik=entity.source_id if entity.source_system == "sec" else None,
        )


class CandidateResponse(BaseModel):
    """Resolution candidate in API responses."""

    entity_id: str
    score: float
    match_reason: str
    matched_value: str | None = None


class ResolutionResponse(BaseModel):
    """Resolution result in API responses."""

    query: str
    status: str
    entity: EntityResponse | None = None
    confidence: float = 0.0
    match_reason: str | None = None
    tier: str = "tier_1"
    warnings: list[str] = Field(default_factory=list)
    candidates: list[CandidateResponse] = Field(default_factory=list)
    elapsed_ms: float | None = None

    @classmethod
    def from_domain(cls, result: Any, elapsed_ms: float | None = None) -> "ResolutionResponse":
        """Create from domain ResolutionResult."""
        entity = None
        if result.entity:
            entity = EntityResponse.from_domain(result.entity)

        candidates = []
        for c in result.candidates or []:
            candidates.append(
                CandidateResponse(
                    entity_id=c.entity_id,
                    score=c.score,
                    match_reason=_enum_to_str(c.match_reason),
                    matched_value=c.matched_value,
                )
            )

        # Get match_reason from first candidate if available
        match_reason = None
        if result.candidates:
            match_reason = _enum_to_str(result.candidates[0].match_reason)

        return cls(
            query=result.query,
            status=_enum_to_str(result.status),
            entity=entity,
            confidence=result.confidence,
            match_reason=match_reason,
            tier=_enum_to_str(result.tier),
            warnings=result.warnings or [],
            candidates=candidates,
            elapsed_ms=elapsed_ms,
        )


class BatchResolutionResponse(BaseModel):
    """Batch resolution response."""

    results: dict[str, ResolutionResponse]
    total: int
    resolved: int
    not_found: int
    elapsed_ms: float


class SearchResponse(BaseModel):
    """Search results response."""

    query: str
    results: list[EntityResponse]
    total: int
    limit: int
    offset: int
    elapsed_ms: float | None = None


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str
    detail: str | None = None
    status_code: int


# =============================================================================
# Graph Response Models
# =============================================================================


class GraphNodeResponse(BaseModel):
    """Node in a graph response."""

    id: str
    name: str
    type: str
    depth: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class GraphEdgeResponse(BaseModel):
    """Edge in a graph response."""

    source: str
    target: str
    type: str
    strength: float | None = None
    description: str | None = None


class NetworkResponse(BaseModel):
    """Entity network response."""

    center_id: str
    center_name: str | None = None
    nodes: list[GraphNodeResponse]
    edges: list[GraphEdgeResponse]
    node_count: int
    edge_count: int


class SubsidiaryResponse(BaseModel):
    """Subsidiary in response."""

    id: str
    name: str
    type: str
    ownership_percent: float | None = None


class SubsidiariesResponse(BaseModel):
    """Subsidiaries list response."""

    parent_id: str
    subsidiaries: list[SubsidiaryResponse]
    count: int


class OfficerResponse(BaseModel):
    """Officer/director in response."""

    id: str
    name: str
    title: str | None = None
    role_type: str
    is_current: bool = True
    start_date: str | None = None
    end_date: str | None = None


class OfficersResponse(BaseModel):
    """Officers list response."""

    company_id: str
    officers: list[OfficerResponse]
    count: int


class PathStepResponse(BaseModel):
    """Step in a path response."""

    id: str
    name: str
    relationship: str | None = None


class PathResponse(BaseModel):
    """Path between entities response."""

    source: str
    target: str
    found: bool
    path: list[PathStepResponse]
    distance: int
