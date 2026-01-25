"""
Pydantic Schemas - Companies
"""
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class CompanyBase(BaseModel):
    """Base company fields."""
    cik: str
    ticker: Optional[str] = None
    name: str
    sector: Optional[str] = None
    industry: Optional[str] = None


class CompanyResponse(BaseModel):
    """Company response schema."""
    model_config = ConfigDict(from_attributes=True)
    
    company_id: UUID
    
    # Identifiers
    cik: str
    ticker: Optional[str] = None
    cusip: Optional[str] = None
    isin: Optional[str] = None
    lei: Optional[str] = None
    
    # Basic Info
    name: str
    legal_name: Optional[str] = None
    former_names: Optional[List[str]] = None
    description: Optional[str] = None
    
    # Classification
    sector: Optional[str] = None
    industry: Optional[str] = None
    sub_industry: Optional[str] = None
    sic_code: Optional[str] = None
    sic_description: Optional[str] = None
    naics_code: Optional[str] = None
    
    # Location
    headquarters_city: Optional[str] = None
    headquarters_state: Optional[str] = None
    headquarters_country: str = "US"
    
    # Corporate Info
    fiscal_year_end: Optional[str] = None
    filer_status: Optional[str] = None
    
    # Contact
    website: Optional[str] = None
    phone: Optional[str] = None
    ir_website: Optional[str] = None
    
    # Market Data
    market_cap: Optional[Decimal] = None
    enterprise_value: Optional[Decimal] = None
    shares_outstanding: Optional[int] = None
    
    # Key Metrics
    revenue_ttm: Optional[Decimal] = None
    net_income_ttm: Optional[Decimal] = None
    gross_margin: Optional[Decimal] = None
    operating_margin: Optional[Decimal] = None
    net_margin: Optional[Decimal] = None
    pe_ratio: Optional[Decimal] = None
    
    # Employees
    employees: Optional[int] = None
    
    # Status
    status: str = "active"
    is_public: bool = True
    exchange: Optional[str] = None
    
    # Timestamps
    founded_year: Optional[int] = None
    ipo_date: Optional[date] = None
    last_filing_date: Optional[date] = None


class CompanyListResponse(BaseModel):
    """Paginated company list response."""
    companies: List[CompanyResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class CompanySearchParams(BaseModel):
    """Company search parameters."""
    query: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    exchange: Optional[str] = None
    min_market_cap: Optional[float] = None
    max_market_cap: Optional[float] = None


class CompanyMetricsResponse(BaseModel):
    """Company metrics response."""
    company_id: str
    ticker: Optional[str] = None
    name: str
    
    current_metrics: Dict[str, Optional[float]]
    
    employees: Optional[int] = None
    shares_outstanding: Optional[int] = None
    
    # Optional historical time series
    historical_metrics: Optional[List[Dict[str, Any]]] = None


class CompanySearchResult(BaseModel):
    """Simplified company for search results."""
    company_id: str
    cik: str
    ticker: Optional[str] = None
    name: str
    sector: Optional[str] = None
    industry: Optional[str] = None
    market_cap: Optional[float] = None
