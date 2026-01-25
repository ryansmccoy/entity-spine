"""
Unit Tests - Filings API
"""
import pytest
from datetime import date
from httpx import AsyncClient


class TestFilingsAPI:
    """Tests for Filings API endpoints."""
    
    @pytest.mark.asyncio
    async def test_list_filings_empty(self, client: AsyncClient):
        """Test listing filings when database is empty."""
        response = await client.get("/api/v1/filings")
        assert response.status_code == 200
        data = response.json()
        assert data["filings"] == []
        assert data["total"] == 0
    
    @pytest.mark.asyncio
    async def test_list_filings_with_data(self, client: AsyncClient, sample_filing, sample_company):
        """Test listing filings with sample data."""
        response = await client.get("/api/v1/filings")
        assert response.status_code == 200
        data = response.json()
        assert len(data["filings"]) == 1
        assert data["filings"][0]["form_type"] == "10-K"
        assert data["filings"][0]["company_ticker"] == "TEST"
    
    @pytest.mark.asyncio
    async def test_list_filings_filter_form_type(self, client: AsyncClient, sample_filing, sample_company):
        """Test filtering filings by form type."""
        # Match
        response = await client.get("/api/v1/filings?form_type=10-K")
        assert response.status_code == 200
        data = response.json()
        assert len(data["filings"]) == 1
        
        # No match
        response = await client.get("/api/v1/filings?form_type=8-K")
        assert response.status_code == 200
        data = response.json()
        assert len(data["filings"]) == 0
    
    @pytest.mark.asyncio
    async def test_list_filings_filter_multiple_form_types(self, client: AsyncClient, sample_filing, sample_company):
        """Test filtering filings by multiple form types."""
        response = await client.get("/api/v1/filings?form_types=10-K,10-Q,8-K")
        assert response.status_code == 200
        data = response.json()
        assert len(data["filings"]) == 1
    
    @pytest.mark.asyncio
    async def test_list_filings_filter_date_range(self, client: AsyncClient, sample_filing, sample_company):
        """Test filtering filings by date range."""
        # Within range
        response = await client.get("/api/v1/filings?filed_after=2024-01-01&filed_before=2024-12-31")
        assert response.status_code == 200
        data = response.json()
        assert len(data["filings"]) == 1
        
        # Outside range
        response = await client.get("/api/v1/filings?filed_after=2025-01-01")
        assert response.status_code == 200
        data = response.json()
        assert len(data["filings"]) == 0
    
    @pytest.mark.asyncio
    async def test_get_filing_feed(self, client: AsyncClient, sample_filing, sample_company):
        """Test getting filing feed."""
        response = await client.get("/api/v1/filings/feed")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["form_type"] == "10-K"
        assert "time_ago" in data[0]
        assert "company" in data[0]
    
    @pytest.mark.asyncio
    async def test_get_filing_by_id(self, client: AsyncClient, sample_filing, sample_company):
        """Test getting filing by ID."""
        response = await client.get(f"/api/v1/filings/{sample_filing.filing_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["form_type"] == "10-K"
        assert data["accession_number"] == "0001234567-24-000001"
        assert "company" in data
        assert "documents" in data
        assert "sections" in data
    
    @pytest.mark.asyncio
    async def test_get_filing_not_found(self, client: AsyncClient):
        """Test 404 for non-existent filing."""
        from uuid import uuid4
        response = await client.get(f"/api/v1/filings/{uuid4()}")
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_get_form_types(self, client: AsyncClient, sample_filing, sample_company):
        """Test getting available form types."""
        response = await client.get("/api/v1/filings/form-types")
        assert response.status_code == 200
        data = response.json()
        assert "form_types" in data
        assert len(data["form_types"]) >= 1
        assert any(ft["form_type"] == "10-K" for ft in data["form_types"])
    
    @pytest.mark.asyncio
    async def test_list_filings_pagination(self, client: AsyncClient, sample_filing, sample_company):
        """Test pagination parameters."""
        response = await client.get("/api/v1/filings?page=1&page_size=10")
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 10
        assert "total_pages" in data
    
    @pytest.mark.asyncio
    async def test_list_filings_sort_order(self, client: AsyncClient, sample_filing, sample_company):
        """Test sorting filings."""
        response = await client.get("/api/v1/filings?sort_by=filed_at&sort_order=desc")
        assert response.status_code == 200
        data = response.json()
        assert len(data["filings"]) >= 0  # Just verify no error
