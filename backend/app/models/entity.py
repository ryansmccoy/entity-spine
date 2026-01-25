"""
SQLAlchemy Models - Entities & Knowledge Graph
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
    ForeignKey,
    Index,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TSVECTOR, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Entity(Base):
    """Extracted entities from filings for knowledge graph."""
    
    __tablename__ = "entities"
    
    entity_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), 
        primary_key=True, 
        server_default=func.gen_random_uuid()
    )
    
    # Type
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    
    # Identity
    name: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_name: Mapped[Optional[str]] = mapped_column(Text, index=True)
    aliases: Mapped[Optional[List[str]]] = mapped_column(ARRAY(Text))
    
    # Linking
    company_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("companies.company_id"),
        index=True,
    )
    
    # Properties
    properties: Mapped[dict] = mapped_column(JSONB, default={})
    
    # Source
    first_seen_filing_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True))
    
    # Confidence
    confidence: Mapped[Decimal] = mapped_column(Numeric(3, 2), default=1.0)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Search
    search_vector: Mapped[Optional[str]] = mapped_column(TSVECTOR)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    outgoing_relationships = relationship(
        "Relationship",
        foreign_keys="Relationship.source_entity_id",
        back_populates="source_entity",
        lazy="dynamic",
    )
    incoming_relationships = relationship(
        "Relationship",
        foreign_keys="Relationship.target_entity_id",
        back_populates="target_entity",
        lazy="dynamic",
    )
    mentions = relationship("EntityMention", back_populates="entity", lazy="dynamic")
    
    # Indexes
    __table_args__ = (
        Index("idx_entities_name_trgm", name, postgresql_using="gin", postgresql_ops={"name": "gin_trgm_ops"}),
        Index("idx_entities_search", search_vector, postgresql_using="gin"),
    )
    
    def __repr__(self) -> str:
        return f"<Entity {self.entity_type}: {self.name}>"


class Relationship(Base):
    """Relationships between entities in knowledge graph."""
    
    __tablename__ = "relationships"
    
    relationship_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), 
        primary_key=True, 
        server_default=func.gen_random_uuid()
    )
    
    # Entities
    source_entity_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("entities.entity_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_entity_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("entities.entity_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Relationship
    relationship_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    relationship_subtype: Mapped[Optional[str]] = mapped_column(String(50))
    
    # Properties
    properties: Mapped[dict] = mapped_column(JSONB, default={})
    
    # Validity
    valid_from: Mapped[Optional[date]] = mapped_column(Date)
    valid_to: Mapped[Optional[date]] = mapped_column(Date)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Source
    source_filing_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True))
    source_section: Mapped[Optional[str]] = mapped_column(String(50))
    
    # Confidence
    confidence: Mapped[Decimal] = mapped_column(Numeric(3, 2), default=1.0)
    extraction_method: Mapped[Optional[str]] = mapped_column(String(20))
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    source_entity = relationship("Entity", foreign_keys=[source_entity_id], back_populates="outgoing_relationships")
    target_entity = relationship("Entity", foreign_keys=[target_entity_id], back_populates="incoming_relationships")
    
    # Indexes
    __table_args__ = (
        Index("idx_relationships_current", is_current, postgresql_where=is_current),
    )
    
    def __repr__(self) -> str:
        return f"<Relationship {self.relationship_type}: {self.source_entity_id} -> {self.target_entity_id}>"


class EntityMention(Base):
    """Where entities are mentioned in filings."""
    
    __tablename__ = "entity_mentions"
    
    mention_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), 
        primary_key=True, 
        server_default=func.gen_random_uuid()
    )
    entity_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("entities.entity_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    filing_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("filings.filing_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    section_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True))
    
    # Context
    mention_text: Mapped[str] = mapped_column(Text, nullable=False)
    context_text: Mapped[Optional[str]] = mapped_column(Text)
    
    # Position
    start_position: Mapped[Optional[int]] = mapped_column(Integer)
    end_position: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Sentiment
    sentiment_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(3, 2))
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    entity = relationship("Entity", back_populates="mentions")


class RelationshipType(Base):
    """Relationship type definitions."""
    
    __tablename__ = "relationship_types"
    
    type_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), 
        primary_key=True, 
        server_default=func.gen_random_uuid()
    )
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    inverse_name: Mapped[Optional[str]] = mapped_column(String(50))
    source_entity_types: Mapped[Optional[List[str]]] = mapped_column(ARRAY(Text))
    target_entity_types: Mapped[Optional[List[str]]] = mapped_column(ARRAY(Text))
    properties_schema: Mapped[Optional[dict]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
