"""
Universal Search API Endpoints
==============================

This module provides REST API endpoints for searching across all content types
in the Entity Spine platform.

Endpoints
---------
GET /search
    Universal search across companies, filings, entities, and sections.
    
GET /search/advanced
    Natural language search with structured filters.
    
GET /search/suggestions
    Get typeahead suggestions as user types.
    
GET /search/trending
    Get trending searches and topics.
    
POST /search/save
    Save a search for later use.

Search Types
------------
The universal search can query:
- **company**: Companies by name, ticker, CIK
- **filing**: Filings by form type, accession number
- **entity**: Entities by name, type
- **section**: Filing sections by content

Response Format
---------------
All search results follow a consistent format:

.. code-block:: json

    {
        "type": "company",
        "id": "uuid",
        "title": "AAPL - Apple Inc.",
        "subtitle": "Technology | Consumer Electronics",
        "data": { /* type-specific fields */ },
        "url": "/companies/{id}"
    }

Advanced Search
---------------
The advanced search supports natural language queries:

.. code-block:: python

    # Natural language query
    response = await client.get(
        "/api/v1/search/advanced",
        params={
            "query": "technology companies mentioning AI in risk factors",
            "filters": '{"sectors": ["Technology"], "form_types": ["10-K"]}'
        }
    )

Typeahead Suggestions
---------------------
Suggestions are returned in priority order:
1. Exact ticker matches
2. Ticker prefix matches
3. Company name matches
4. Form type matches

Example
-------
.. code-block:: python

    # Universal search
    response = await client.get(
        "/api/v1/search",
        params={"q": "artificial intelligence", "types": "company,filing"}
    )
    
    # Get suggestions while typing
    suggestions = await client.get(
        "/api/v1/search/suggestions",
        params={"q": "APP"}
    )
    # Returns: [{"type": "ticker", "value": "AAPL", "label": "AAPL - Apple Inc."}]

See Also
--------
- app.models.company : Company model
- app.models.filing : Filing model
- Elasticsearch documentation for advanced queries
"""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, or_, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.company import Company
from app.models.filing import Filing, FilingSection
from app.models.entity import Entity

router = APIRouter()


@router.get("")
async def universal_search(
    q: str = Query(..., min_length=1, description="Search query"),
    types: Optional[str] = Query(None, description="Comma-separated types: company,filing,entity,section"),
    sector: Optional[str] = Query(None, description="Filter by sector"),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_session),
):
    """
    Universal search across all content types.
    
    Searches companies, filings, entities, and filing sections.
    Results are ranked by relevance.
    """
    type_list = types.split(",") if types else ["company", "filing", "entity"]
    results = []
    
    # Search companies
    if "company" in type_list:
        company_query = select(Company).where(
            Company.status == "active",
            or_(
                Company.search_vector.match(q),
                Company.ticker.ilike(f"{q}%"),
                Company.name.ilike(f"%{q}%"),
                Company.cik.ilike(f"{q}%"),
            )
        )
        if sector:
            company_query = company_query.where(Company.sector == sector)
        
        company_query = company_query.limit(limit)
        company_result = await db.execute(company_query)
        
        for c in company_result.scalars():
            results.append({
                "type": "company",
                "id": str(c.company_id),
                "title": f"{c.ticker or ''} - {c.name}",
                "subtitle": f"{c.sector or ''} | {c.industry or ''}",
                "data": {
                    "company_id": str(c.company_id),
                    "cik": c.cik,
                    "ticker": c.ticker,
                    "name": c.name,
                    "sector": c.sector,
                    "market_cap": float(c.market_cap) if c.market_cap else None,
                },
                "url": f"/companies/{c.company_id}",
            })
    
    # Search filings
    if "filing" in type_list:
        filing_query = (
            select(Filing, Company)
            .join(Company, Filing.company_id == Company.company_id)
            .where(
                or_(
                    Filing.search_vector.match(q),
                    Filing.accession_number.ilike(f"%{q}%"),
                    Filing.form_type.ilike(f"{q}%"),
                )
            )
        )
        if sector:
            filing_query = filing_query.where(Company.sector == sector)
        
        filing_query = filing_query.order_by(Filing.filed_at.desc()).limit(limit)
        filing_result = await db.execute(filing_query)
        
        for filing, company in filing_result.all():
            results.append({
                "type": "filing",
                "id": str(filing.filing_id),
                "title": f"{company.ticker or company.cik} - {filing.form_type}",
                "subtitle": f"Filed {filing.filed_at.isoformat()}",
                "data": {
                    "filing_id": str(filing.filing_id),
                    "accession_number": filing.accession_number,
                    "form_type": filing.form_type,
                    "filed_at": filing.filed_at.isoformat(),
                    "company_ticker": company.ticker,
                    "company_name": company.name,
                },
                "url": f"/filings/{filing.filing_id}",
            })
    
    # Search entities
    if "entity" in type_list:
        entity_query = select(Entity).where(
            or_(
                Entity.search_vector.match(q),
                Entity.name.ilike(f"%{q}%"),
            )
        ).limit(limit)
        
        entity_result = await db.execute(entity_query)
        
        for e in entity_result.scalars():
            results.append({
                "type": "entity",
                "id": str(e.entity_id),
                "title": e.name,
                "subtitle": f"{e.entity_type}",
                "data": {
                    "entity_id": str(e.entity_id),
                    "entity_type": e.entity_type,
                    "name": e.name,
                },
                "url": f"/entities/{e.entity_id}",
            })
    
    # Search filing sections
    if "section" in type_list:
        section_query = (
            select(FilingSection, Filing, Company)
            .join(Filing, FilingSection.filing_id == Filing.filing_id)
            .join(Company, Filing.company_id == Company.company_id)
            .where(FilingSection.search_vector.match(q))
        )
        if sector:
            section_query = section_query.where(Company.sector == sector)
        
        section_query = section_query.limit(limit)
        section_result = await db.execute(section_query)
        
        for section, filing, company in section_result.all():
            # Get snippet from content
            snippet = ""
            if section.content_text:
                # Simple snippet extraction around query term
                lower_content = section.content_text.lower()
                lower_q = q.lower()
                pos = lower_content.find(lower_q)
                if pos >= 0:
                    start = max(0, pos - 100)
                    end = min(len(section.content_text), pos + len(q) + 100)
                    snippet = "..." + section.content_text[start:end] + "..."
            
            results.append({
                "type": "section",
                "id": str(section.section_id),
                "title": f"{company.ticker or company.cik} - {filing.form_type} - {section.section_type}",
                "subtitle": section.section_title or section.section_type,
                "snippet": snippet,
                "data": {
                    "section_id": str(section.section_id),
                    "filing_id": str(filing.filing_id),
                    "section_type": section.section_type,
                    "company_ticker": company.ticker,
                },
                "url": f"/filings/{filing.filing_id}/sections/{section.section_type}",
            })
    
    return {
        "query": q,
        "results": results,
        "count": len(results),
    }


@router.get("/advanced")
async def advanced_search(
    query: str = Query(..., description="Natural language query"),
    filters: Optional[str] = Query(None, description="JSON filter object"),
    db: AsyncSession = Depends(get_session),
):
    """
    Advanced natural language search with structured filters.
    
    Supports queries like:
    - "10-K filings mentioning supply chain risks in technology sector"
    - "Companies with revenue growth over 20%"
    - "CEO changes in healthcare companies 2024"
    
    Filters (JSON):
    {
        "form_types": ["10-K", "10-Q"],
        "sectors": ["Technology"],
        "date_range": {"from": "2024-01-01", "to": "2024-12-31"},
        "market_cap_range": {"min": 1000000000}
    }
    """
    import json
    
    filter_obj = {}
    if filters:
        try:
            filter_obj = json.loads(filters)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid filters JSON")
    
    # TODO: Implement NLP query parsing and advanced search
    # For now, fall back to basic search
    return await universal_search(q=query, types=None, sector=None, limit=50, db=db)


@router.get("/suggestions")
async def search_suggestions(
    q: str = Query(..., min_length=1, description="Partial query"),
    limit: int = Query(10, ge=1, le=20),
    db: AsyncSession = Depends(get_session),
):
    """
    Get search suggestions as user types.
    
    Returns suggestions for:
    - Company tickers
    - Company names
    - Form types
    - Common search phrases
    """
    suggestions = []
    
    # Ticker suggestions
    ticker_query = (
        select(Company.ticker, Company.name)
        .where(
            Company.status == "active",
            Company.ticker.ilike(f"{q}%"),
            Company.ticker.isnot(None),
        )
        .order_by(Company.market_cap.desc().nullslast())
        .limit(5)
    )
    ticker_result = await db.execute(ticker_query)
    for ticker, name in ticker_result.all():
        suggestions.append({
            "type": "ticker",
            "value": ticker,
            "label": f"{ticker} - {name}",
        })
    
    # Company name suggestions
    name_query = (
        select(Company.company_id, Company.ticker, Company.name)
        .where(
            Company.status == "active",
            Company.name.ilike(f"%{q}%"),
        )
        .order_by(Company.market_cap.desc().nullslast())
        .limit(5)
    )
    name_result = await db.execute(name_query)
    for company_id, ticker, name in name_result.all():
        if not any(s["value"] == (ticker or name) for s in suggestions):
            suggestions.append({
                "type": "company",
                "value": name,
                "label": f"{ticker + ' - ' if ticker else ''}{name}",
            })
    
    # Form type suggestions
    form_types = ["10-K", "10-Q", "8-K", "DEF 14A", "S-1", "4", "13F-HR"]
    for ft in form_types:
        if q.upper() in ft:
            suggestions.append({
                "type": "form_type",
                "value": ft,
                "label": f"Form {ft}",
            })
    
    return {
        "query": q,
        "suggestions": suggestions[:limit],
    }


@router.get("/trending")
async def trending_searches(
    period: str = Query("day", description="hour, day, week"),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_session),
):
    """
    Get trending searches and topics.
    """
    # TODO: Implement actual trending based on search history
    # For now, return placeholder trending topics
    
    return {
        "period": period,
        "trending": [
            {"topic": "AI", "category": "keyword", "trend_score": 95},
            {"topic": "NVDA", "category": "ticker", "trend_score": 92},
            {"topic": "Earnings", "category": "event", "trend_score": 88},
            {"topic": "Technology", "category": "sector", "trend_score": 85},
            {"topic": "10-K", "category": "form_type", "trend_score": 80},
        ],
    }


@router.post("/save")
async def save_search(
    name: str = Query(..., description="Search name"),
    query_text: str = Query(..., description="Search query"),
    search_type: str = Query("universal", description="Search type"),
    filters: Optional[str] = Query(None, description="JSON filters"),
    db: AsyncSession = Depends(get_session),
):
    """
    Save a search for later use.
    
    Requires authentication (user_id from token).
    """
    # TODO: Implement saved searches with user authentication
    return {
        "message": "Search saved",
        "search_id": "placeholder",
        "name": name,
    }
