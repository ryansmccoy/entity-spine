"""
SQLAlchemy Models - Companies
"""
from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Integer,
    Numeric,
    String,
    Text,
    BigInteger,
    Index,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, TSVECTOR, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Company(Base):
    """Company model - Core company information."""
    
    __tablename__ = "companies"
    
    # Primary Key
    company_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), 
        primary_key=True, 
        server_default=func.gen_random_uuid()
    )
    
    # Identifiers
    cik: Mapped[str] = mapped_column(String(10), unique=True, nullable=False, index=True)
    ticker: Mapped[Optional[str]] = mapped_column(String(10), index=True)
    cusip: Mapped[Optional[str]] = mapped_column(String(9))
    isin: Mapped[Optional[str]] = mapped_column(String(12))
    lei: Mapped[Optional[str]] = mapped_column(String(20))
    
    # Basic Info
    name: Mapped[str] = mapped_column(Text, nullable=False)
    legal_name: Mapped[Optional[str]] = mapped_column(Text)
    former_names: Mapped[Optional[List[str]]] = mapped_column(ARRAY(Text))
    description: Mapped[Optional[str]] = mapped_column(Text)
    
    # Classification
    sector: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    industry: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    sub_industry: Mapped[Optional[str]] = mapped_column(String(100))
    sic_code: Mapped[Optional[str]] = mapped_column(String(4))
    sic_description: Mapped[Optional[str]] = mapped_column(Text)
    naics_code: Mapped[Optional[str]] = mapped_column(String(6))
    
    # Location
    headquarters_address: Mapped[Optional[str]] = mapped_column(Text)
    headquarters_city: Mapped[Optional[str]] = mapped_column(String(100))
    headquarters_state: Mapped[Optional[str]] = mapped_column(String(2))
    headquarters_country: Mapped[str] = mapped_column(String(2), default="US")
    mailing_address: Mapped[Optional[str]] = mapped_column(Text)
    
    # Corporate Info
    incorporated_state: Mapped[Optional[str]] = mapped_column(String(2))
    incorporated_country: Mapped[Optional[str]] = mapped_column(String(2))
    fiscal_year_end: Mapped[Optional[str]] = mapped_column(String(20))
    filer_status: Mapped[Optional[str]] = mapped_column(String(50))
    
    # Contact
    website: Mapped[Optional[str]] = mapped_column(Text)
    phone: Mapped[Optional[str]] = mapped_column(String(20))
    ir_website: Mapped[Optional[str]] = mapped_column(Text)
    
    # Market Data (cached)
    market_cap: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))
    enterprise_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))
    shares_outstanding: Mapped[Optional[int]] = mapped_column(BigInteger)
    float_shares: Mapped[Optional[int]] = mapped_column(BigInteger)
    
    # Key Metrics (cached from latest financials)
    revenue_ttm: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))
    net_income_ttm: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))
    gross_margin: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4))
    operating_margin: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4))
    net_margin: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4))
    roe: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4))
    roa: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4))
    pe_ratio: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    ps_ratio: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    pb_ratio: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    
    # Employees
    employees: Mapped[Optional[int]] = mapped_column(Integer)
    employees_date: Mapped[Optional[date]] = mapped_column(Date)
    
    # Status
    status: Mapped[str] = mapped_column(String(20), default="active")
    is_public: Mapped[bool] = mapped_column(Boolean, default=True)
    exchange: Mapped[Optional[str]] = mapped_column(String(20))
    
    # Timestamps
    founded_year: Mapped[Optional[int]] = mapped_column(Integer)
    ipo_date: Mapped[Optional[date]] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_filing_date: Mapped[Optional[date]] = mapped_column(Date)
    
    # Search
    search_vector: Mapped[Optional[str]] = mapped_column(TSVECTOR)
    
    # Relationships
    filings = relationship("Filing", back_populates="company", lazy="dynamic")
    officers = relationship("CompanyOfficer", back_populates="company", lazy="dynamic")
    
    # Indexes
    __table_args__ = (
        Index("idx_companies_market_cap", market_cap.desc().nullslast()),
        Index("idx_companies_name_trgm", name, postgresql_using="gin", postgresql_ops={"name": "gin_trgm_ops"}),
        Index("idx_companies_search", search_vector, postgresql_using="gin"),
    )
    
    def __repr__(self) -> str:
        return f"<Company {self.ticker or self.cik}: {self.name}>"


class CompanyTicker(Base):
    """Historical ticker symbols for companies."""
    
    __tablename__ = "company_tickers"
    
    ticker_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), 
        primary_key=True, 
        server_default=func.gen_random_uuid()
    )
    company_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    ticker: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    exchange: Mapped[Optional[str]] = mapped_column(String(20))
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    valid_from: Mapped[Optional[date]] = mapped_column(Date)
    valid_to: Mapped[Optional[date]] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Sector(Base):
    """GICS sector hierarchy."""
    
    __tablename__ = "sectors"
    
    sector_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), 
        primary_key=True, 
        server_default=func.gen_random_uuid()
    )
    parent_sector_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), index=True)
    code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    level: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
