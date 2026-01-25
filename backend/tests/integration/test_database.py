"""
Integration Tests - Database Operations
"""
import pytest
from datetime import date
from decimal import Decimal
from sqlalchemy import select

from app.models.company import Company
from app.models.filing import Filing
from app.models.entity import Entity, Relationship


class TestCompanyDatabase:
    """Integration tests for Company database operations."""
    
    @pytest.mark.asyncio
    async def test_create_company(self, db_session):
        """Test creating a company."""
        company = Company(
            cik="9999999999",
            ticker="INTG",
            name="Integration Test Corp",
            sector="Financials",
            industry="Banks",
            market_cap=Decimal("5000000000"),
            status="active",
        )
        db_session.add(company)
        await db_session.commit()
        
        # Verify
        result = await db_session.execute(
            select(Company).where(Company.ticker == "INTG")
        )
        saved = result.scalar_one()
        assert saved.name == "Integration Test Corp"
        assert saved.market_cap == Decimal("5000000000")
    
    @pytest.mark.asyncio
    async def test_company_unique_cik(self, db_session, sample_company):
        """Test that CIK must be unique."""
        from sqlalchemy.exc import IntegrityError
        
        duplicate = Company(
            cik=sample_company.cik,  # Same CIK
            ticker="DUP",
            name="Duplicate Company",
            status="active",
        )
        db_session.add(duplicate)
        
        with pytest.raises(IntegrityError):
            await db_session.commit()
    
    @pytest.mark.asyncio
    async def test_company_update(self, db_session, sample_company):
        """Test updating company fields."""
        sample_company.market_cap = Decimal("2000000000")
        sample_company.employees = 5000
        await db_session.commit()
        
        # Refresh and verify
        await db_session.refresh(sample_company)
        assert sample_company.market_cap == Decimal("2000000000")
        assert sample_company.employees == 5000


class TestFilingDatabase:
    """Integration tests for Filing database operations."""
    
    @pytest.mark.asyncio
    async def test_create_filing(self, db_session, sample_company):
        """Test creating a filing."""
        filing = Filing(
            company_id=sample_company.company_id,
            accession_number="9999999999-24-000001",
            form_type="8-K",
            filed_at=date(2024, 6, 15),
            sec_url="https://www.sec.gov/test",
            status="captured",
        )
        db_session.add(filing)
        await db_session.commit()
        
        # Verify
        result = await db_session.execute(
            select(Filing).where(Filing.accession_number == "9999999999-24-000001")
        )
        saved = result.scalar_one()
        assert saved.form_type == "8-K"
        assert saved.company_id == sample_company.company_id
    
    @pytest.mark.asyncio
    async def test_filing_company_relationship(self, db_session, sample_filing, sample_company):
        """Test filing-company relationship."""
        # Access company through filing
        result = await db_session.execute(
            select(Filing).where(Filing.filing_id == sample_filing.filing_id)
        )
        filing = result.scalar_one()
        
        # Load company
        await db_session.refresh(filing, ["company"])
        assert filing.company.ticker == "TEST"
    
    @pytest.mark.asyncio
    async def test_filing_cascade_delete(self, db_session, sample_filing, sample_company):
        """Test that deleting company cascades to filings."""
        from sqlalchemy import delete
        
        company_id = sample_company.company_id
        
        # Delete company
        await db_session.delete(sample_company)
        await db_session.commit()
        
        # Verify filing is also deleted
        result = await db_session.execute(
            select(Filing).where(Filing.company_id == company_id)
        )
        filings = result.scalars().all()
        assert len(filings) == 0


class TestEntityDatabase:
    """Integration tests for Entity and Knowledge Graph operations."""
    
    @pytest.mark.asyncio
    async def test_create_entity(self, db_session):
        """Test creating an entity."""
        entity = Entity(
            entity_type="person",
            name="John Smith",
            normalized_name="john smith",
            properties={"title": "CEO"},
        )
        db_session.add(entity)
        await db_session.commit()
        
        # Verify
        result = await db_session.execute(
            select(Entity).where(Entity.name == "John Smith")
        )
        saved = result.scalar_one()
        assert saved.entity_type == "person"
        assert saved.properties["title"] == "CEO"
    
    @pytest.mark.asyncio
    async def test_create_relationship(self, db_session, sample_entity):
        """Test creating a relationship between entities."""
        # Create another entity
        person = Entity(
            entity_type="person",
            name="Jane Doe",
            normalized_name="jane doe",
        )
        db_session.add(person)
        await db_session.commit()
        
        # Create relationship
        relationship = Relationship(
            source_entity_id=person.entity_id,
            target_entity_id=sample_entity.entity_id,
            relationship_type="officer_of",
            is_current=True,
            confidence=Decimal("0.95"),
        )
        db_session.add(relationship)
        await db_session.commit()
        
        # Verify
        result = await db_session.execute(
            select(Relationship).where(Relationship.source_entity_id == person.entity_id)
        )
        saved = result.scalar_one()
        assert saved.relationship_type == "officer_of"
        assert saved.confidence == Decimal("0.95")
    
    @pytest.mark.asyncio
    async def test_entity_link_to_company(self, db_session, sample_company):
        """Test linking entity to company."""
        entity = Entity(
            entity_type="company",
            name=sample_company.name,
            company_id=sample_company.company_id,
            is_verified=True,
        )
        db_session.add(entity)
        await db_session.commit()
        
        # Verify link
        result = await db_session.execute(
            select(Entity).where(Entity.company_id == sample_company.company_id)
        )
        saved = result.scalar_one()
        assert saved.is_verified == True
