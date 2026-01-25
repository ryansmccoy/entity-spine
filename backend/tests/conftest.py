"""
Pytest Configuration & Fixtures
"""
import asyncio
from typing import AsyncGenerator, Generator
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.main import app
from app.db.session import Base, get_session
from app.core.config import settings


# Test database URL
TEST_DATABASE_URL = settings.DATABASE_URL.replace(
    "/entityspine", "/entityspine_test"
)


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_engine():
    """Create test database engine."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    async_session_maker = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session_maker() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test HTTP client with overridden dependencies."""
    
    async def override_get_session():
        yield db_session
    
    app.dependency_overrides[get_session] = override_get_session
    
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client
    
    app.dependency_overrides.clear()


# Sample Data Fixtures

@pytest_asyncio.fixture
async def sample_company(db_session: AsyncSession):
    """Create a sample company for testing."""
    from app.models.company import Company
    
    company = Company(
        cik="0001234567",
        ticker="TEST",
        name="Test Company Inc.",
        sector="Technology",
        industry="Software",
        market_cap=1000000000,
        status="active",
    )
    db_session.add(company)
    await db_session.commit()
    await db_session.refresh(company)
    return company


@pytest_asyncio.fixture
async def sample_filing(db_session: AsyncSession, sample_company):
    """Create a sample filing for testing."""
    from datetime import date
    from app.models.filing import Filing
    
    filing = Filing(
        company_id=sample_company.company_id,
        accession_number="0001234567-24-000001",
        form_type="10-K",
        filed_at=date(2024, 3, 15),
        period_of_report=date(2023, 12, 31),
        sec_url="https://www.sec.gov/Archives/edgar/data/1234567/000123456724000001/test-10k.htm",
        status="captured",
    )
    db_session.add(filing)
    await db_session.commit()
    await db_session.refresh(filing)
    return filing


@pytest_asyncio.fixture
async def sample_entity(db_session: AsyncSession, sample_company):
    """Create a sample entity for testing."""
    from app.models.entity import Entity
    
    entity = Entity(
        entity_type="company",
        name=sample_company.name,
        normalized_name=sample_company.name.lower(),
        company_id=sample_company.company_id,
        is_verified=True,
    )
    db_session.add(entity)
    await db_session.commit()
    await db_session.refresh(entity)
    return entity
