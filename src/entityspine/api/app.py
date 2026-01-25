"""
EntitySpine REST API - FastAPI Application

This is the main FastAPI application for EntitySpine.

Usage:
    # Development
    uvicorn entityspine.api.app:app --reload

    # Production
    uvicorn entityspine.api.app:app --host 0.0.0.0 --port 8000

Configuration:
    Set environment variables:
        ENTITYSPINE_DB_PATH=/path/to/entities.db
        ENTITYSPINE_AUTO_LOAD_SEC=true
"""

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from datetime import date
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from entityspine.api.deps import Settings, get_resolver, get_settings
from entityspine.api.schemas import (
    BatchResolveRequest,
    BatchResolutionResponse,
    EntityResponse,
    ErrorResponse,
    HealthResponse,
    InfoResponse,
    ResolutionResponse,
    SearchResponse,
)
from entityspine.services.resolver import EntityResolver


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    # Startup: Initialize resolver (lazy, will load on first request)
    yield
    # Shutdown: Cleanup if needed


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    if settings is None:
        settings = get_settings()

    app = FastAPI(
        title=settings.api_title,
        version=settings.api_version,
        description=settings.api_description,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return app


# Create default app instance
app = create_app()


# =============================================================================
# Health & Info Endpoints
# =============================================================================


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check(
    resolver: Annotated[EntityResolver, Depends(get_resolver)],
) -> HealthResponse:
    """Check API health and database connectivity."""
    try:
        # Try to count entities to verify database connection
        count = 0
        if hasattr(resolver.store, "count_entities"):
            count = resolver.store.count_entities()
        elif hasattr(resolver.store, "_conn"):
            cursor = resolver.store._conn.execute("SELECT COUNT(*) FROM entities")
            count = cursor.fetchone()[0]

        return HealthResponse(
            status="healthy",
            database="connected",
            entities_count=count,
        )
    except Exception as e:
        return HealthResponse(
            status="unhealthy",
            database=f"error: {e}",
            entities_count=0,
        )


@app.get("/info", response_model=InfoResponse, tags=["Health"])
async def api_info(
    resolver: Annotated[EntityResolver, Depends(get_resolver)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> InfoResponse:
    """Get API information and available endpoints."""
    tier_value = resolver.config.tier
    if hasattr(tier_value, "name"):
        tier_str = tier_value.name.lower()
    elif hasattr(tier_value, "value"):
        tier_str = str(tier_value.value)
    else:
        tier_str = str(tier_value)

    return InfoResponse(
        name=settings.api_title,
        version=settings.api_version,
        description=settings.api_description,
        tier=tier_str,
        endpoints=[
            "GET /health",
            "GET /info",
            "GET /resolve/{query}",
            "POST /resolve/batch",
            "GET /entities/cik/{cik}",
            "GET /entities/ticker/{ticker}",
            "GET /entities/{entity_id}",
            "GET /search",
        ],
    )


# =============================================================================
# Resolution Endpoints
# =============================================================================


@app.get(
    "/resolve/{query}",
    response_model=ResolutionResponse,
    responses={404: {"model": ErrorResponse}},
    tags=["Resolution"],
)
async def resolve_identifier(
    query: str,
    resolver: Annotated[EntityResolver, Depends(get_resolver)],
    as_of: Annotated[date | None, Query(description="Point-in-time date")] = None,
    mic: Annotated[str | None, Query(description="Market Identifier Code for ticker disambiguation")] = None,
    scheme_hint: Annotated[str | None, Query(description="Force identifier scheme")] = None,
) -> ResolutionResponse:
    """
    Resolve any identifier to an entity.

    Accepts:
    - Tickers: AAPL, MSFT, GOOGL
    - CIKs: 0000320193, 320193
    - ISINs: US0378331005
    - CUSIPs: 037833100
    - LEIs: HWUPKR0MPOU8FGXBT394
    - Company names: "Apple Inc", "Microsoft"

    Returns the resolved entity with confidence score and metadata.
    """
    start_time = time.perf_counter()

    result = resolver.resolve(
        query,
        as_of=as_of,
        mic=mic,
        scheme_hint=scheme_hint,
    )

    elapsed_ms = (time.perf_counter() - start_time) * 1000

    return ResolutionResponse.from_domain(result, elapsed_ms=elapsed_ms)


@app.post(
    "/resolve/batch",
    response_model=BatchResolutionResponse,
    tags=["Resolution"],
)
async def resolve_batch(
    request: BatchResolveRequest,
    resolver: Annotated[EntityResolver, Depends(get_resolver)],
) -> BatchResolutionResponse:
    """
    Resolve multiple identifiers in a single request.

    More efficient than calling /resolve/{query} repeatedly.
    Limited to 100 queries per request.
    """
    start_time = time.perf_counter()

    results = resolver.resolve_many(
        request.queries,
        as_of=request.as_of,
        continue_on_error=True,
    )

    elapsed_ms = (time.perf_counter() - start_time) * 1000

    # Build response dict
    result_dict = {}
    resolved_count = 0
    not_found_count = 0

    for query, result in zip(request.queries, results):
        response = ResolutionResponse.from_domain(result)
        result_dict[query] = response
        if result.entity:
            resolved_count += 1
        else:
            not_found_count += 1

    return BatchResolutionResponse(
        results=result_dict,
        total=len(request.queries),
        resolved=resolved_count,
        not_found=not_found_count,
        elapsed_ms=elapsed_ms,
    )


# =============================================================================
# Entity Endpoints
# =============================================================================


@app.get(
    "/entities/cik/{cik}",
    response_model=EntityResponse,
    responses={404: {"model": ErrorResponse}},
    tags=["Entities"],
)
async def get_entity_by_cik(
    cik: str,
    resolver: Annotated[EntityResolver, Depends(get_resolver)],
) -> EntityResponse:
    """
    Get entity by SEC CIK (Central Index Key).

    CIK can be provided with or without leading zeros:
    - /entities/cik/0000320193
    - /entities/cik/320193
    """
    result = resolver.resolve(cik, scheme_hint="cik")

    if not result.entity:
        raise HTTPException(
            status_code=404,
            detail=f"Entity not found for CIK: {cik}",
        )

    response = EntityResponse.from_domain(result.entity)
    response.cik = cik.zfill(10)
    return response


@app.get(
    "/entities/ticker/{ticker}",
    response_model=EntityResponse,
    responses={404: {"model": ErrorResponse}},
    tags=["Entities"],
)
async def get_entity_by_ticker(
    ticker: str,
    resolver: Annotated[EntityResolver, Depends(get_resolver)],
    mic: Annotated[str | None, Query(description="Market Identifier Code")] = None,
) -> EntityResponse:
    """
    Get entity by ticker symbol.

    Examples:
    - /entities/ticker/AAPL
    - /entities/ticker/MSFT
    - /entities/ticker/GOOGL?mic=XNAS
    """
    result = resolver.resolve(ticker, mic=mic, scheme_hint="ticker")

    if not result.entity:
        raise HTTPException(
            status_code=404,
            detail=f"Entity not found for ticker: {ticker}",
        )

    response = EntityResponse.from_domain(result.entity)
    response.ticker = ticker.upper()
    return response


@app.get(
    "/entities/{entity_id}",
    response_model=EntityResponse,
    responses={404: {"model": ErrorResponse}},
    tags=["Entities"],
)
async def get_entity_by_id(
    entity_id: str,
    resolver: Annotated[EntityResolver, Depends(get_resolver)],
) -> EntityResponse:
    """
    Get entity by internal entity ID (ULID).

    The entity_id is the internal unique identifier assigned by EntitySpine.
    """
    entity = resolver.store.get_entity(entity_id)

    if not entity:
        raise HTTPException(
            status_code=404,
            detail=f"Entity not found: {entity_id}",
        )

    return EntityResponse.from_domain(entity)


# =============================================================================
# Search Endpoint
# =============================================================================


@app.get(
    "/search",
    response_model=SearchResponse,
    tags=["Search"],
)
async def search_entities(
    resolver: Annotated[EntityResolver, Depends(get_resolver)],
    q: Annotated[str, Query(description="Search query", min_length=1)],
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
    offset: Annotated[int, Query(ge=0)] = 0,
    entity_type: Annotated[str | None, Query(description="Filter by entity type")] = None,
) -> SearchResponse:
    """
    Search entities by name with fuzzy matching.

    Supports partial matches and common variations:
    - /search?q=apple
    - /search?q=micro&limit=5
    """
    start_time = time.perf_counter()

    # Use the resolver's name search capability
    # For now, we do a simple fuzzy search
    result = resolver.resolve(q)

    entities = []
    if result.entity:
        entities.append(EntityResponse.from_domain(result.entity))

    # Add candidates as additional results
    for candidate in result.candidates or []:
        if len(entities) >= limit:
            break
        entity = resolver.store.get_entity(candidate.entity_id)
        if entity:
            entities.append(EntityResponse.from_domain(entity))

    elapsed_ms = (time.perf_counter() - start_time) * 1000

    return SearchResponse(
        query=q,
        results=entities[offset : offset + limit],
        total=len(entities),
        limit=limit,
        offset=offset,
        elapsed_ms=elapsed_ms,
    )


# =============================================================================
# Conversion Endpoint (Tier 2+)
# =============================================================================


@app.get(
    "/convert",
    response_model=dict,
    tags=["Conversion"],
)
async def convert_identifier(
    resolver: Annotated[EntityResolver, Depends(get_resolver)],
    value: Annotated[str, Query(description="Identifier value")],
    from_scheme: Annotated[str, Query(description="Source scheme (cik, ticker, etc.)")],
    to_scheme: Annotated[str, Query(description="Target scheme")],
) -> dict:
    """
    Convert between identifier schemes.

    Examples:
    - /convert?value=AAPL&from_scheme=ticker&to_scheme=cik
    - /convert?value=320193&from_scheme=cik&to_scheme=ticker
    """
    # First resolve the identifier
    result = resolver.resolve(value, scheme_hint=from_scheme)

    if not result.entity:
        raise HTTPException(
            status_code=404,
            detail=f"Could not resolve {from_scheme}: {value}",
        )

    # Get the target identifier
    target_value = None
    entity = result.entity

    if to_scheme.lower() == "cik":
        target_value = entity.source_id if entity.source_system == "sec" else None
    elif to_scheme.lower() == "ticker":
        # Would need to look up listings for the entity
        # For now, return None if not available
        target_value = None
    # Add more schemes as needed

    return {
        "from_scheme": from_scheme,
        "from_value": value,
        "to_scheme": to_scheme,
        "to_value": target_value,
        "entity_id": entity.entity_id,
        "entity_name": entity.primary_name,
    }


# =============================================================================
# Run directly for development
# =============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
