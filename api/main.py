"""
EntitySpine API - Identifier Resolution Service

A simple REST API for ticker/CIK/ISIN/LEI lookups.

Usage:
    uvicorn entityspine.api.main:app --host 0.0.0.0 --port 8080
    
    # Or with Docker
    docker run -p 8080:8080 -v ~/.entityspine:/data entityspine-api

Security:
    Set API_KEY environment variable to require authentication.
    Set RATE_LIMIT_PER_MINUTE to limit requests (default: 60/min).
"""

import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Set DB path from environment
DB_PATH = os.environ.get("ENTITYSPINE_DB_PATH", "/data/entityspine.db")
os.environ["ENTITYSPINE_DB_PATH"] = DB_PATH

from entityspine import (
    ticker, cik, name, tickers, ciks, names,
    lei_from_isin, isins_from_lei, bic_from_lei,
    get_db_path,
)

from api.scheduler import get_scheduler, start_background_refresh
from api.security import verify_api_key, security_middleware, API_KEY


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Start background refresh scheduler
    await start_background_refresh()
    yield
    # Shutdown
    get_scheduler().stop()


app = FastAPI(
    title="EntitySpine API",
    description="Fast identifier resolution: CIK ↔ Ticker ↔ Name ↔ ISIN ↔ LEI",
    version="1.0.0",
    docs_url="/",
    lifespan=lifespan,
)

# Add security middleware (rate limiting, headers)
app.add_middleware(BaseHTTPMiddleware, dispatch=security_middleware)

# Get allowed origins from environment
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Models
# =============================================================================

class TickerResponse(BaseModel):
    query: str
    ticker: Optional[str]


class CikResponse(BaseModel):
    query: str
    cik: Optional[str]


class NameResponse(BaseModel):
    query: str
    name: Optional[str]


class LeiResponse(BaseModel):
    isin: str
    lei: Optional[str]


class IsinsResponse(BaseModel):
    lei: str
    isins: list[str]
    count: int


class BicResponse(BaseModel):
    lei: str
    bic: Optional[str]


class BatchRequest(BaseModel):
    queries: list[str]


class BatchTickerResponse(BaseModel):
    results: dict[str, Optional[str]]


class BatchCikResponse(BaseModel):
    results: dict[str, Optional[str]]


class BatchNameResponse(BaseModel):
    results: dict[str, Optional[str]]


class HealthResponse(BaseModel):
    status: str
    database: str
    database_exists: bool


# =============================================================================
# Health & Info
# =============================================================================

@app.get("/health", response_model=HealthResponse, tags=["System"])
def health_check():
    """Check API health and database status."""
    db_path = get_db_path()
    return HealthResponse(
        status="ok",
        database=db_path,
        database_exists=Path(db_path).exists(),
    )


@app.get("/info", tags=["System"], dependencies=[Depends(verify_api_key)])
def api_info():
    """Get API information and database statistics."""
    import sqlite3
    
    db_path = get_db_path()
    stats = {}
    
    if Path(db_path).exists():
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        for table in ["entities", "securities", "listings", "claims", "isin_mappings", "bic_mappings"]:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                stats[table] = cursor.fetchone()[0]
            except:
                stats[table] = 0
        
        conn.close()
    
    return {
        "version": "1.0.0",
        "database": db_path,
        "statistics": stats,
    }


# =============================================================================
# Single Lookups
# =============================================================================

@app.get("/ticker/{query}", response_model=TickerResponse, tags=["Lookup"], dependencies=[Depends(verify_api_key)])
def get_ticker(query: str):
    """
    Get ticker from CIK, company name, or other identifier.
    
    Examples:
    - /ticker/0000320193 → AAPL
    - /ticker/Apple → AAPL
    """
    result = ticker(query)
    return TickerResponse(query=query, ticker=result)


@app.get("/cik/{query}", response_model=CikResponse, tags=["Lookup"], dependencies=[Depends(verify_api_key)])
def get_cik(query: str):
    """
    Get CIK from ticker or company name.
    
    Examples:
    - /cik/AAPL → 0000320193
    - /cik/Apple → 0000320193
    """
    result = cik(query)
    return CikResponse(query=query, cik=result)


@app.get("/name/{query}", response_model=NameResponse, tags=["Lookup"], dependencies=[Depends(verify_api_key)])
def get_name(query: str):
    """
    Get company name from ticker or CIK.
    
    Examples:
    - /name/AAPL → Apple Inc.
    - /name/0000320193 → Apple Inc.
    """
    result = name(query)
    return NameResponse(query=query, name=result)


# =============================================================================
# ISIN/LEI Lookups
# =============================================================================

@app.get("/lei/{isin}", response_model=LeiResponse, tags=["ISIN/LEI"], dependencies=[Depends(verify_api_key)])
def get_lei_from_isin(isin: str):
    """
    Get LEI from ISIN.
    
    Example: /lei/US0378331005 → HWUPKR0MPOU8FGXBT394
    """
    result = lei_from_isin(isin)
    return LeiResponse(isin=isin, lei=result)


@app.get("/isins/{lei}", response_model=IsinsResponse, tags=["ISIN/LEI"], dependencies=[Depends(verify_api_key)])
def get_isins_from_lei(
    lei: str,
    limit: int = Query(default=100, le=1000, description="Max ISINs to return"),
):
    """
    Get all ISINs for an LEI.
    
    Example: /isins/HWUPKR0MPOU8FGXBT394 → [US0378331005, ...]
    """
    results = isins_from_lei(lei)
    return IsinsResponse(
        lei=lei,
        isins=results[:limit],
        count=len(results),
    )


@app.get("/bic/{lei}", response_model=BicResponse, tags=["ISIN/LEI"], dependencies=[Depends(verify_api_key)])
def get_bic_from_lei(lei: str):
    """
    Get BIC (Bank Identifier Code) from LEI.
    """
    result = bic_from_lei(lei)
    return BicResponse(lei=lei, bic=result)


# =============================================================================
# Batch Lookups
# =============================================================================

@app.post("/batch/tickers", response_model=BatchTickerResponse, tags=["Batch"], dependencies=[Depends(verify_api_key)])
def batch_get_tickers(request: BatchRequest):
    """
    Get tickers for multiple identifiers at once.
    
    Request body: {"queries": ["0000320193", "0001018724", "0001652044"]}
    Response: {"results": {"0000320193": "AAPL", "0001018724": "AMZN", ...}}
    """
    results = {q: ticker(q) for q in request.queries}
    return BatchTickerResponse(results=results)


@app.post("/batch/ciks", response_model=BatchCikResponse, tags=["Batch"], dependencies=[Depends(verify_api_key)])
def batch_get_ciks(request: BatchRequest):
    """
    Get CIKs for multiple tickers at once.
    
    Request body: {"queries": ["AAPL", "AMZN", "GOOGL"]}
    """
    results = {q: cik(q) for q in request.queries}
    return BatchCikResponse(results=results)


@app.post("/batch/names", response_model=BatchNameResponse, tags=["Batch"], dependencies=[Depends(verify_api_key)])
def batch_get_names(request: BatchRequest):
    """
    Get company names for multiple identifiers at once.
    """
    results = {q: name(q) for q in request.queries}
    return BatchNameResponse(results=results)


# =============================================================================
# Convenience Endpoints
# =============================================================================

@app.get("/resolve/{query}", tags=["Lookup"], dependencies=[Depends(verify_api_key)])
def resolve_identifier(query: str):
    """
    Resolve any identifier and return all available info.
    
    Returns ticker, CIK, and name for the given query.
    """
    return {
        "query": query,
        "ticker": ticker(query),
        "cik": cik(query),
        "name": name(query),
    }


# =============================================================================
# Scheduler & Refresh Endpoints
# =============================================================================

@app.get("/scheduler/status", tags=["System"])
def scheduler_status():
    """
    Get scheduler status including last refresh times and next scheduled refresh.
    """
    return get_scheduler().get_status()


@app.post("/refresh/sec", tags=["System"])
def refresh_sec_data(background_tasks: BackgroundTasks):
    """
    Trigger SEC data refresh (runs in background).
    
    Downloads latest company_tickers.json from SEC and updates database.
    """
    scheduler = get_scheduler()
    background_tasks.add_task(scheduler.refresh_sec_data)
    return {
        "status": "started",
        "message": "SEC data refresh started in background",
    }


@app.post("/refresh/all", tags=["System"])
def refresh_all_data(background_tasks: BackgroundTasks):
    """
    Trigger full data refresh (runs in background).
    
    Refreshes SEC and GLEIF data.
    """
    scheduler = get_scheduler()
    background_tasks.add_task(scheduler.refresh_sec_data)
    # GLEIF refresh disabled until download implemented
    # background_tasks.add_task(scheduler.refresh_gleif_data)
    return {
        "status": "started",
        "message": "Data refresh started in background",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
