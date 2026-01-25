"""
Filings API Endpoints
=====================

This module provides REST API endpoints for SEC filing operations.

Endpoints
---------
GET /filings
    List filings with filtering by form type, date, sector, company.
    
GET /filings/feed
    Get filings in Instagram-style feed format for infinite scroll.
    Includes time-ago formatting and engagement metrics.
    
GET /filings/{filing_id}
    Get detailed filing with documents and parsed sections.
    
GET /filings/{filing_id}/sections/{section_type}
    Get specific section content (item_1, item_1a, item_7, etc.).
    
GET /filings/accession/{accession_number}
    Lookup filing by SEC accession number.
    
GET /filings/form-types
    Get list of available form types with filing counts.

Filing Types
------------
Common SEC form types:
- **10-K**: Annual report (fiscal year)
- **10-Q**: Quarterly report
- **8-K**: Current report (material events)
- **DEF 14A**: Proxy statement
- **S-1**: IPO registration
- **4**: Insider transaction

10-K Sections
-------------
Standard sections in annual reports:
- **item_1**: Business description
- **item_1a**: Risk factors
- **item_1b**: Unresolved staff comments
- **item_2**: Properties
- **item_3**: Legal proceedings
- **item_7**: MD&A (Management Discussion & Analysis)
- **item_7a**: Quantitative disclosures about market risk
- **item_8**: Financial statements

Example
-------
.. code-block:: python

    # Get filing feed
    response = await client.get(
        "/api/v1/filings/feed",
        params={"form_types": "10-K,8-K", "sector": "Technology"}
    )
    
    # Each feed item includes:
    # - filing_id, form_type, filed_at
    # - time_ago: "2h ago", "3d ago"
    # - company: {ticker, name, sector}

See Also
--------
- app.models.filing : SQLAlchemy models
- app.schemas.filing : Pydantic schemas
"""
from datetime import date
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.filing import Filing, FilingDocument, FilingSection
from app.models.company import Company
from app.schemas.filing import (
    FilingResponse,
    FilingListResponse,
    FilingDetailResponse,
    FilingFeedItem,
)

router = APIRouter()


@router.get("", response_model=FilingListResponse)
async def list_filings(
    form_type: Optional[str] = Query(None, description="Filter by form type (10-K, 10-Q, 8-K, etc.)"),
    form_types: Optional[str] = Query(None, description="Comma-separated form types"),
    sector: Optional[str] = Query(None, description="Filter by company sector"),
    ticker: Optional[str] = Query(None, description="Filter by company ticker"),
    cik: Optional[str] = Query(None, description="Filter by company CIK"),
    filed_after: Optional[date] = Query(None, description="Filed on or after date"),
    filed_before: Optional[date] = Query(None, description="Filed on or before date"),
    sort_by: str = Query("filed_at", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_session),
):
    """
    List SEC filings with filtering and pagination.
    
    Supports filtering by:
    - Form type (10-K, 10-Q, 8-K, etc.)
    - Company sector
    - Company ticker or CIK
    - Filing date range
    """
    # Build base query with company join
    query = (
        select(Filing, Company)
        .join(Company, Filing.company_id == Company.company_id)
    )
    
    # Apply filters
    if form_type:
        query = query.where(Filing.form_type == form_type)
    if form_types:
        types = [t.strip() for t in form_types.split(",")]
        query = query.where(Filing.form_type.in_(types))
    if sector:
        query = query.where(Company.sector == sector)
    if ticker:
        query = query.where(Company.ticker.ilike(ticker))
    if cik:
        query = query.where(Company.cik == cik)
    if filed_after:
        query = query.where(Filing.filed_at >= filed_after)
    if filed_before:
        query = query.where(Filing.filed_at <= filed_before)
    
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0
    
    # Apply sorting
    sort_column = getattr(Filing, sort_by, Filing.filed_at)
    if sort_order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())
    
    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    
    result = await db.execute(query)
    rows = result.all()
    
    filings = [
        FilingResponse(
            filing_id=str(filing.filing_id),
            accession_number=filing.accession_number,
            form_type=filing.form_type,
            form_description=filing.form_description,
            filed_at=filing.filed_at,
            period_of_report=filing.period_of_report,
            sec_url=filing.sec_url,
            company_id=str(company.company_id),
            company_cik=company.cik,
            company_ticker=company.ticker,
            company_name=company.name,
            company_sector=company.sector,
        )
        for filing, company in rows
    ]
    
    return FilingListResponse(
        filings=filings,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size if total > 0 else 0,
    )


@router.get("/feed", response_model=List[FilingFeedItem])
async def get_filing_feed(
    form_types: str = Query("10-K,10-Q,8-K", description="Comma-separated form types"),
    sector: Optional[str] = Query(None, description="Filter by sector"),
    watchlist_only: bool = Query(False, description="Only watchlist companies"),
    limit: int = Query(50, ge=1, le=100),
    before_id: Optional[UUID] = Query(None, description="Cursor for pagination"),
    db: AsyncSession = Depends(get_session),
):
    """
    Get filing feed (Instagram-style).
    
    Returns recent filings as feed items with company info,
    designed for infinite scroll pagination.
    """
    types = [t.strip() for t in form_types.split(",")]
    
    query = (
        select(Filing, Company)
        .join(Company, Filing.company_id == Company.company_id)
        .where(Filing.form_type.in_(types))
    )
    
    if sector:
        query = query.where(Company.sector == sector)
    
    if before_id:
        # Get the filed_at for cursor
        cursor_query = select(Filing.filed_at).where(Filing.filing_id == before_id)
        cursor_result = await db.execute(cursor_query)
        cursor_date = cursor_result.scalar_one_or_none()
        if cursor_date:
            query = query.where(Filing.filed_at < cursor_date)
    
    query = query.order_by(Filing.filed_at.desc()).limit(limit)
    
    result = await db.execute(query)
    rows = result.all()
    
    feed_items = []
    for filing, company in rows:
        # Calculate time ago
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        filed_datetime = datetime.combine(filing.filed_at, datetime.min.time()).replace(tzinfo=timezone.utc)
        delta = now - filed_datetime
        
        if delta.days > 0:
            time_ago = f"{delta.days}d ago"
        elif delta.seconds >= 3600:
            time_ago = f"{delta.seconds // 3600}h ago"
        else:
            time_ago = f"{delta.seconds // 60}m ago"
        
        feed_items.append(FilingFeedItem(
            filing_id=str(filing.filing_id),
            form_type=filing.form_type,
            filed_at=filing.filed_at,
            time_ago=time_ago,
            period_of_report=filing.period_of_report,
            sec_url=filing.sec_url,
            company=dict(
                company_id=str(company.company_id),
                cik=company.cik,
                ticker=company.ticker,
                name=company.name,
                sector=company.sector,
                market_cap=float(company.market_cap) if company.market_cap else None,
            ),
            # Placeholder for engagement metrics
            views=0,
            bookmarks=0,
            comments=0,
        ))
    
    return feed_items


@router.get("/{filing_id}", response_model=FilingDetailResponse)
async def get_filing(
    filing_id: UUID,
    db: AsyncSession = Depends(get_session),
):
    """
    Get detailed filing information including documents and sections.
    """
    # Get filing with company
    query = (
        select(Filing, Company)
        .join(Company, Filing.company_id == Company.company_id)
        .where(Filing.filing_id == filing_id)
    )
    result = await db.execute(query)
    row = result.one_or_none()
    
    if not row:
        raise HTTPException(status_code=404, detail="Filing not found")
    
    filing, company = row
    
    # Get documents
    docs_query = select(FilingDocument).where(FilingDocument.filing_id == filing_id)
    docs_result = await db.execute(docs_query)
    documents = docs_result.scalars().all()
    
    # Get sections
    sections_query = select(FilingSection).where(FilingSection.filing_id == filing_id)
    sections_result = await db.execute(sections_query)
    sections = sections_result.scalars().all()
    
    return FilingDetailResponse(
        filing_id=str(filing.filing_id),
        accession_number=filing.accession_number,
        form_type=filing.form_type,
        form_description=filing.form_description,
        filed_at=filing.filed_at,
        accepted_at=filing.accepted_at,
        period_of_report=filing.period_of_report,
        fiscal_year=filing.fiscal_year,
        fiscal_quarter=filing.fiscal_quarter,
        sec_url=filing.sec_url,
        filing_index_url=filing.filing_index_url,
        size_bytes=filing.size_bytes,
        status=filing.status,
        is_amended=filing.is_amended,
        company=dict(
            company_id=str(company.company_id),
            cik=company.cik,
            ticker=company.ticker,
            name=company.name,
            sector=company.sector,
            industry=company.industry,
        ),
        documents=[
            dict(
                document_id=str(d.document_id),
                sequence=d.sequence,
                filename=d.filename,
                description=d.description,
                document_type=d.document_type,
                size_bytes=d.size_bytes,
                content_type=d.content_type,
                is_primary=d.is_primary,
                url=d.url,
            )
            for d in documents
        ],
        sections=[
            dict(
                section_id=str(s.section_id),
                section_type=s.section_type,
                section_title=s.section_title,
                word_count=s.word_count,
            )
            for s in sections
        ],
    )


@router.get("/{filing_id}/sections/{section_type}")
async def get_filing_section(
    filing_id: UUID,
    section_type: str,
    db: AsyncSession = Depends(get_session),
):
    """
    Get a specific section from a filing.
    
    Common section types for 10-K:
    - item_1: Business
    - item_1a: Risk Factors
    - item_1b: Unresolved Staff Comments
    - item_2: Properties
    - item_3: Legal Proceedings
    - item_7: MD&A
    - item_7a: Quantitative and Qualitative Disclosures
    - item_8: Financial Statements
    """
    query = select(FilingSection).where(
        FilingSection.filing_id == filing_id,
        FilingSection.section_type == section_type,
    )
    result = await db.execute(query)
    section = result.scalar_one_or_none()
    
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")
    
    return {
        "section_id": str(section.section_id),
        "filing_id": str(filing_id),
        "section_type": section.section_type,
        "section_title": section.section_title,
        "section_number": section.section_number,
        "word_count": section.word_count,
        "content_text": section.content_text,
        "content_html": section.content_html,
    }


@router.get("/accession/{accession_number}")
async def get_filing_by_accession(
    accession_number: str,
    db: AsyncSession = Depends(get_session),
):
    """
    Get filing by accession number.
    """
    # Normalize accession number format
    normalized = accession_number.replace("-", "")
    
    query = select(Filing).where(
        Filing.accession_number.ilike(f"%{accession_number}%")
    )
    result = await db.execute(query)
    filing = result.scalar_one_or_none()
    
    if not filing:
        raise HTTPException(status_code=404, detail="Filing not found")
    
    return {"filing_id": str(filing.filing_id), "redirect": f"/api/v1/filings/{filing.filing_id}"}


@router.get("/form-types")
async def get_form_types(
    db: AsyncSession = Depends(get_session),
):
    """
    Get list of available form types with counts.
    """
    query = (
        select(Filing.form_type, func.count(Filing.filing_id).label("count"))
        .group_by(Filing.form_type)
        .order_by(func.count(Filing.filing_id).desc())
    )
    result = await db.execute(query)
    rows = result.all()
    
    return {
        "form_types": [
            {"form_type": row.form_type, "count": row.count}
            for row in rows
        ]
    }
