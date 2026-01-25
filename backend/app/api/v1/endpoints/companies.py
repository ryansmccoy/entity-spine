"""
Companies API Endpoints
=======================

This module provides REST API endpoints for company data operations.

Endpoints
---------
GET /companies
    List companies with filtering, sorting, and pagination.
    
GET /companies/search
    Search companies by name, ticker, or CIK using full-text search.
    
GET /companies/{company_id}
    Get detailed company profile by UUID.
    
GET /companies/ticker/{ticker}
    Get company by stock ticker symbol.
    
GET /companies/cik/{cik}
    Get company by SEC Central Index Key.
    
GET /companies/{company_id}/metrics
    Get financial metrics (revenue, margins, ratios).
    
GET /companies/{company_id}/filings
    Get SEC filings for a specific company.
    
GET /companies/{company_id}/relationships
    Get entity relationships (subsidiaries, officers, etc.).

Data Model
----------
Companies are identified by multiple IDs:
- **company_id**: Internal UUID (primary key)
- **cik**: SEC Central Index Key (unique)
- **ticker**: Stock symbol (may be null for private companies)
- **cusip/isin/lei**: Other standard identifiers

Example
-------
.. code-block:: python

    # Using httpx async client
    async with httpx.AsyncClient() as client:
        # Search for Apple
        response = await client.get(
            "http://localhost:8000/api/v1/companies/search",
            params={"q": "AAPL"}
        )
        companies = response.json()["results"]
        
        # Get company details
        company_id = companies[0]["company_id"]
        detail = await client.get(f"/api/v1/companies/{company_id}")

See Also
--------
- app.models.company : SQLAlchemy models
- app.schemas.company : Pydantic schemas
"""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.company import Company
from app.schemas.company import (
    CompanyResponse,
    CompanyListResponse,
    CompanySearchParams,
    CompanyMetricsResponse,
)

router = APIRouter()


@router.get("", response_model=CompanyListResponse)
async def list_companies(
    sector: Optional[str] = Query(None, description="Filter by sector"),
    industry: Optional[str] = Query(None, description="Filter by industry"),
    exchange: Optional[str] = Query(None, description="Filter by exchange"),
    min_market_cap: Optional[float] = Query(None, description="Minimum market cap"),
    max_market_cap: Optional[float] = Query(None, description="Maximum market cap"),
    sort_by: str = Query("market_cap", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_session),
):
    """
    List companies with filtering and pagination.
    
    - **sector**: Filter by GICS sector
    - **industry**: Filter by industry
    - **exchange**: Filter by stock exchange (NYSE, NASDAQ)
    - **min_market_cap**: Minimum market cap in dollars
    - **max_market_cap**: Maximum market cap in dollars
    - **sort_by**: Field to sort by (market_cap, name, ticker)
    - **sort_order**: Sort direction (asc, desc)
    """
    # Build query
    query = select(Company).where(Company.status == "active")
    
    # Apply filters
    if sector:
        query = query.where(Company.sector == sector)
    if industry:
        query = query.where(Company.industry == industry)
    if exchange:
        query = query.where(Company.exchange == exchange)
    if min_market_cap:
        query = query.where(Company.market_cap >= min_market_cap)
    if max_market_cap:
        query = query.where(Company.market_cap <= max_market_cap)
    
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)
    
    # Apply sorting
    sort_column = getattr(Company, sort_by, Company.market_cap)
    if sort_order == "desc":
        query = query.order_by(sort_column.desc().nullslast())
    else:
        query = query.order_by(sort_column.asc().nullsfirst())
    
    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    
    result = await db.execute(query)
    companies = result.scalars().all()
    
    return CompanyListResponse(
        companies=[CompanyResponse.model_validate(c) for c in companies],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/search")
async def search_companies(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(20, ge=1, le=100, description="Max results"),
    db: AsyncSession = Depends(get_session),
):
    """
    Search companies by name, ticker, or CIK.
    
    Uses full-text search for best matching.
    """
    # Use full-text search with fallback to ILIKE
    query = select(Company).where(
        Company.status == "active",
        (
            Company.search_vector.match(q) |
            Company.ticker.ilike(f"{q}%") |
            Company.name.ilike(f"%{q}%") |
            Company.cik.ilike(f"{q}%")
        )
    ).order_by(
        # Prioritize exact ticker matches
        func.case(
            (Company.ticker.ilike(q), 1),
            (Company.ticker.ilike(f"{q}%"), 2),
            else_=3
        ),
        Company.market_cap.desc().nullslast()
    ).limit(limit)
    
    result = await db.execute(query)
    companies = result.scalars().all()
    
    return {
        "results": [
            {
                "company_id": str(c.company_id),
                "cik": c.cik,
                "ticker": c.ticker,
                "name": c.name,
                "sector": c.sector,
                "industry": c.industry,
                "market_cap": float(c.market_cap) if c.market_cap else None,
            }
            for c in companies
        ],
        "count": len(companies),
    }


@router.get("/{company_id}", response_model=CompanyResponse)
async def get_company(
    company_id: UUID,
    db: AsyncSession = Depends(get_session),
):
    """
    Get detailed company information by ID.
    """
    result = await db.execute(
        select(Company).where(Company.company_id == company_id)
    )
    company = result.scalar_one_or_none()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    return CompanyResponse.model_validate(company)


@router.get("/cik/{cik}", response_model=CompanyResponse)
async def get_company_by_cik(
    cik: str,
    db: AsyncSession = Depends(get_session),
):
    """
    Get company information by CIK.
    """
    # Normalize CIK (remove leading zeros or pad)
    normalized_cik = cik.lstrip("0") or "0"
    
    result = await db.execute(
        select(Company).where(Company.cik == normalized_cik)
    )
    company = result.scalar_one_or_none()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    return CompanyResponse.model_validate(company)


@router.get("/ticker/{ticker}", response_model=CompanyResponse)
async def get_company_by_ticker(
    ticker: str,
    db: AsyncSession = Depends(get_session),
):
    """
    Get company information by stock ticker.
    """
    result = await db.execute(
        select(Company).where(
            Company.ticker.ilike(ticker),
            Company.status == "active",
        )
    )
    company = result.scalar_one_or_none()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    return CompanyResponse.model_validate(company)


@router.get("/{company_id}/metrics", response_model=CompanyMetricsResponse)
async def get_company_metrics(
    company_id: UUID,
    db: AsyncSession = Depends(get_session),
):
    """
    Get financial metrics for a company.
    
    Returns both current metrics and historical time series.
    """
    result = await db.execute(
        select(Company).where(Company.company_id == company_id)
    )
    company = result.scalar_one_or_none()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Build metrics response
    return CompanyMetricsResponse(
        company_id=str(company.company_id),
        ticker=company.ticker,
        name=company.name,
        current_metrics={
            "market_cap": float(company.market_cap) if company.market_cap else None,
            "enterprise_value": float(company.enterprise_value) if company.enterprise_value else None,
            "revenue_ttm": float(company.revenue_ttm) if company.revenue_ttm else None,
            "net_income_ttm": float(company.net_income_ttm) if company.net_income_ttm else None,
            "gross_margin": float(company.gross_margin) if company.gross_margin else None,
            "operating_margin": float(company.operating_margin) if company.operating_margin else None,
            "net_margin": float(company.net_margin) if company.net_margin else None,
            "roe": float(company.roe) if company.roe else None,
            "roa": float(company.roa) if company.roa else None,
            "pe_ratio": float(company.pe_ratio) if company.pe_ratio else None,
            "ps_ratio": float(company.ps_ratio) if company.ps_ratio else None,
            "pb_ratio": float(company.pb_ratio) if company.pb_ratio else None,
        },
        employees=company.employees,
        shares_outstanding=company.shares_outstanding,
    )


@router.get("/{company_id}/filings")
async def get_company_filings(
    company_id: UUID,
    form_type: Optional[str] = Query(None, description="Filter by form type"),
    year: Optional[int] = Query(None, description="Filter by year"),
    limit: int = Query(50, ge=1, le=200, description="Max results"),
    db: AsyncSession = Depends(get_session),
):
    """
    Get filings for a specific company.
    """
    from app.models.filing import Filing
    
    query = select(Filing).where(Filing.company_id == company_id)
    
    if form_type:
        query = query.where(Filing.form_type == form_type)
    if year:
        query = query.where(func.extract("year", Filing.filed_at) == year)
    
    query = query.order_by(Filing.filed_at.desc()).limit(limit)
    
    result = await db.execute(query)
    filings = result.scalars().all()
    
    return {
        "company_id": str(company_id),
        "filings": [
            {
                "filing_id": str(f.filing_id),
                "accession_number": f.accession_number,
                "form_type": f.form_type,
                "filed_at": f.filed_at.isoformat(),
                "period_of_report": f.period_of_report.isoformat() if f.period_of_report else None,
                "sec_url": f.sec_url,
            }
            for f in filings
        ],
        "count": len(filings),
    }


@router.get("/{company_id}/relationships")
async def get_company_relationships(
    company_id: UUID,
    relationship_type: Optional[str] = Query(None, description="Filter by relationship type"),
    db: AsyncSession = Depends(get_session),
):
    """
    Get entity relationships for a company.
    
    Returns subsidiaries, officers, investors, and other related entities.
    """
    from app.models.entity import Entity, Relationship
    
    # First, find the entity for this company
    entity_query = select(Entity).where(Entity.company_id == company_id)
    entity_result = await db.execute(entity_query)
    entity = entity_result.scalar_one_or_none()
    
    if not entity:
        return {"company_id": str(company_id), "relationships": [], "count": 0}
    
    # Get relationships where company is source or target
    rel_query = select(Relationship).where(
        Relationship.is_current == True,
        (Relationship.source_entity_id == entity.entity_id) |
        (Relationship.target_entity_id == entity.entity_id)
    )
    
    if relationship_type:
        rel_query = rel_query.where(Relationship.relationship_type == relationship_type)
    
    rel_result = await db.execute(rel_query)
    relationships = rel_result.scalars().all()
    
    return {
        "company_id": str(company_id),
        "entity_id": str(entity.entity_id),
        "relationships": [
            {
                "relationship_id": str(r.relationship_id),
                "relationship_type": r.relationship_type,
                "source_entity_id": str(r.source_entity_id),
                "target_entity_id": str(r.target_entity_id),
                "direction": "outgoing" if r.source_entity_id == entity.entity_id else "incoming",
                "confidence": float(r.confidence),
            }
            for r in relationships
        ],
        "count": len(relationships),
    }
