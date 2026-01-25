"""
Unit Tests - Companies API
"""
import pytest
from httpx import AsyncClient


class TestCompaniesAPI:
    """Tests for Companies API endpoints."""
    
    @pytest.mark.asyncio
    async def test_list_companies_empty(self, client: AsyncClient):
        """Test listing companies when database is empty."""
        response = await client.get("/api/v1/companies")
        assert response.status_code == 200
        data = response.json()
        assert data["companies"] == []
        assert data["total"] == 0
    
    @pytest.mark.asyncio
    async def test_list_companies_with_data(self, client: AsyncClient, sample_company):
        """Test listing companies with sample data."""
        response = await client.get("/api/v1/companies")
        assert response.status_code == 200
        data = response.json()
        assert len(data["companies"]) == 1
        assert data["companies"][0]["ticker"] == "TEST"
        assert data["companies"][0]["name"] == "Test Company Inc."
    
    @pytest.mark.asyncio
    async def test_list_companies_filter_sector(self, client: AsyncClient, sample_company):
        """Test filtering companies by sector."""
        # Match
        response = await client.get("/api/v1/companies?sector=Technology")
        assert response.status_code == 200
        data = response.json()
        assert len(data["companies"]) == 1
        
        # No match
        response = await client.get("/api/v1/companies?sector=Healthcare")
        assert response.status_code == 200
        data = response.json()
        assert len(data["companies"]) == 0
    
    @pytest.mark.asyncio
    async def test_get_company_by_id(self, client: AsyncClient, sample_company):
        """Test getting company by ID."""
        response = await client.get(f"/api/v1/companies/{sample_company.company_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "TEST"
        assert data["cik"] == "0001234567"
    
    @pytest.mark.asyncio
    async def test_get_company_not_found(self, client: AsyncClient):
        """Test 404 for non-existent company."""
        from uuid import uuid4
        response = await client.get(f"/api/v1/companies/{uuid4()}")
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_get_company_by_ticker(self, client: AsyncClient, sample_company):
        """Test getting company by ticker symbol."""
        response = await client.get("/api/v1/companies/ticker/TEST")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Company Inc."
    
    @pytest.mark.asyncio
    async def test_get_company_by_cik(self, client: AsyncClient, sample_company):
        """Test getting company by CIK."""
        response = await client.get("/api/v1/companies/cik/0001234567")
        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "TEST"
    
    @pytest.mark.asyncio
    async def test_search_companies(self, client: AsyncClient, sample_company):
        """Test company search."""
        # Search by ticker
        response = await client.get("/api/v1/companies/search?q=TEST")
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) >= 1
        
        # Search by name
        response = await client.get("/api/v1/companies/search?q=Company")
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) >= 1
    
    @pytest.mark.asyncio
    async def test_get_company_metrics(self, client: AsyncClient, sample_company):
        """Test getting company financial metrics."""
        response = await client.get(f"/api/v1/companies/{sample_company.company_id}/metrics")
        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "TEST"
        assert "current_metrics" in data
        assert "market_cap" in data["current_metrics"]
    
    @pytest.mark.asyncio
    async def test_get_company_filings(self, client: AsyncClient, sample_company, sample_filing):
        """Test getting company filings."""
        response = await client.get(f"/api/v1/companies/{sample_company.company_id}/filings")
        assert response.status_code == 200
        data = response.json()
        assert len(data["filings"]) == 1
        assert data["filings"][0]["form_type"] == "10-K"
    
    @pytest.mark.asyncio
    async def test_list_companies_pagination(self, client: AsyncClient, sample_company):
        """Test pagination parameters."""
        response = await client.get("/api/v1/companies?page=1&page_size=10")
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 10
        assert "total_pages" in data
