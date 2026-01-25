"""
Pydantic Schemas - Filings
"""
from datetime import date, datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class FilingResponse(BaseModel):
    """Filing response schema."""
    filing_id: str
    accession_number: str
    form_type: str
    form_description: Optional[str] = None
    filed_at: date
    period_of_report: Optional[date] = None
    sec_url: Optional[str] = None
    
    # Company info
    company_id: str
    company_cik: str
    company_ticker: Optional[str] = None
    company_name: str
    company_sector: Optional[str] = None


class FilingListResponse(BaseModel):
    """Paginated filing list response."""
    filings: List[FilingResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class FilingDocument(BaseModel):
    """Filing document schema."""
    document_id: str
    sequence: Optional[int] = None
    filename: str
    description: Optional[str] = None
    document_type: Optional[str] = None
    size_bytes: Optional[int] = None
    content_type: Optional[str] = None
    is_primary: bool = False
    url: Optional[str] = None


class FilingSection(BaseModel):
    """Filing section schema."""
    section_id: str
    section_type: str
    section_title: Optional[str] = None
    word_count: Optional[int] = None


class FilingDetailResponse(BaseModel):
    """Detailed filing response with documents and sections."""
    filing_id: str
    accession_number: str
    form_type: str
    form_description: Optional[str] = None
    filed_at: date
    accepted_at: Optional[datetime] = None
    period_of_report: Optional[date] = None
    fiscal_year: Optional[int] = None
    fiscal_quarter: Optional[int] = None
    sec_url: Optional[str] = None
    filing_index_url: Optional[str] = None
    size_bytes: Optional[int] = None
    status: str
    is_amended: bool = False
    
    company: Dict[str, Any]
    documents: List[Dict[str, Any]]
    sections: List[Dict[str, Any]]


class FilingFeedItem(BaseModel):
    """Filing feed item for Instagram-style feed."""
    filing_id: str
    form_type: str
    filed_at: date
    time_ago: str
    period_of_report: Optional[date] = None
    sec_url: Optional[str] = None
    
    company: Dict[str, Any]
    
    # Engagement metrics
    views: int = 0
    bookmarks: int = 0
    comments: int = 0


class FilingSectionContent(BaseModel):
    """Filing section with full content."""
    section_id: str
    filing_id: str
    section_type: str
    section_title: Optional[str] = None
    section_number: Optional[str] = None
    word_count: Optional[int] = None
    content_text: Optional[str] = None
    content_html: Optional[str] = None
