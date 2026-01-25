"""
SQLAlchemy Models - Filings
"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional
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
    ForeignKey,
    Index,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Filing(Base):
    """SEC Filing records."""
    
    __tablename__ = "filings"
    
    # Primary Key
    filing_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), 
        primary_key=True, 
        server_default=func.gen_random_uuid()
    )
    company_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("companies.company_id"),
        nullable=False,
        index=True,
    )
    
    # SEC Identifiers
    accession_number: Mapped[str] = mapped_column(String(25), unique=True, nullable=False, index=True)
    file_number: Mapped[Optional[str]] = mapped_column(String(25))
    film_number: Mapped[Optional[str]] = mapped_column(String(25))
    
    # Filing Details
    form_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    form_description: Mapped[Optional[str]] = mapped_column(Text)
    primary_document: Mapped[Optional[str]] = mapped_column(Text)
    primary_doc_description: Mapped[Optional[str]] = mapped_column(Text)
    
    # Dates
    filed_at: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    accepted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    period_of_report: Mapped[Optional[date]] = mapped_column(Date, index=True)
    fiscal_year: Mapped[Optional[int]] = mapped_column(Integer)
    fiscal_quarter: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Size
    size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger)
    
    # URLs
    sec_url: Mapped[Optional[str]] = mapped_column(Text)
    filing_index_url: Mapped[Optional[str]] = mapped_column(Text)
    
    # Status
    status: Mapped[str] = mapped_column(String(20), default="captured", index=True)
    is_amended: Mapped[bool] = mapped_column(Boolean, default=False)
    amends_filing_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True))
    
    # Processing
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    parsed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[Optional[str]] = mapped_column(Text)
    
    # Search
    search_vector: Mapped[Optional[str]] = mapped_column(TSVECTOR)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    company = relationship("Company", back_populates="filings")
    documents = relationship("FilingDocument", back_populates="filing", lazy="dynamic")
    sections = relationship("FilingSection", back_populates="filing", lazy="dynamic")
    
    # Indexes
    __table_args__ = (
        Index("idx_filings_filed_desc", filed_at.desc()),
        Index("idx_filings_search", search_vector, postgresql_using="gin"),
    )
    
    def __repr__(self) -> str:
        return f"<Filing {self.accession_number}: {self.form_type}>"


class FilingDocument(Base):
    """Individual documents within a filing."""
    
    __tablename__ = "filing_documents"
    
    document_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), 
        primary_key=True, 
        server_default=func.gen_random_uuid()
    )
    filing_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("filings.filing_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Document Info
    sequence: Mapped[Optional[int]] = mapped_column(Integer)
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    document_type: Mapped[Optional[str]] = mapped_column(String(50), index=True)
    size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger)
    
    # Content Type
    content_type: Mapped[Optional[str]] = mapped_column(String(100))
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # URLs
    url: Mapped[Optional[str]] = mapped_column(Text)
    
    # Content (for parsed documents)
    content_text: Mapped[Optional[str]] = mapped_column(Text)
    content_html: Mapped[Optional[str]] = mapped_column(Text)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    filing = relationship("Filing", back_populates="documents")


class FilingSection(Base):
    """Parsed sections from filings."""
    
    __tablename__ = "filing_sections"
    
    section_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), 
        primary_key=True, 
        server_default=func.gen_random_uuid()
    )
    filing_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("filings.filing_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True))
    
    # Section Info
    section_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    section_title: Mapped[Optional[str]] = mapped_column(Text)
    section_number: Mapped[Optional[str]] = mapped_column(String(20))
    
    # Content
    content_text: Mapped[Optional[str]] = mapped_column(Text)
    content_html: Mapped[Optional[str]] = mapped_column(Text)
    word_count: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Position
    start_position: Mapped[Optional[int]] = mapped_column(Integer)
    end_position: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Search
    search_vector: Mapped[Optional[str]] = mapped_column(TSVECTOR)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    filing = relationship("Filing", back_populates="sections")
    
    # Indexes
    __table_args__ = (
        Index("idx_filing_sections_search", search_vector, postgresql_using="gin"),
    )


class FilingChange(Base):
    """Track changes between filings."""
    
    __tablename__ = "filing_changes"
    
    change_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), 
        primary_key=True, 
        server_default=func.gen_random_uuid()
    )
    filing_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("filings.filing_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    previous_filing_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True))
    
    # Change Summary
    section_type: Mapped[Optional[str]] = mapped_column(String(50))
    change_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    change_summary: Mapped[Optional[str]] = mapped_column(Text)
    
    # Content
    old_content: Mapped[Optional[str]] = mapped_column(Text)
    new_content: Mapped[Optional[str]] = mapped_column(Text)
    diff_html: Mapped[Optional[str]] = mapped_column(Text)
    
    # Importance
    significance_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(3, 2))
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
