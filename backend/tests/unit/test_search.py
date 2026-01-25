"""
Unit Tests - Search API
"""
import pytest
from httpx import AsyncClient


class TestSearchAPI:
    """Tests for Search API endpoints."""
    
    @pytest.mark.asyncio
    async def test_universal_search_empty(self, client: AsyncClient):
        """Test universal search with no results."""
        response = await client.get("/api/v1/search?q=nonexistent123")
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert data["count"] == 0
    
    @pytest.mark.asyncio
    async def test_universal_search_companies(self, client: AsyncClient, sample_company):
        """Test universal search finds companies."""
        response = await client.get("/api/v1/search?q=TEST")
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) >= 1
        assert any(r["type"] == "company" for r in data["results"])
    
    @pytest.mark.asyncio
    async def test_universal_search_filings(self, client: AsyncClient, sample_filing, sample_company):
        """Test universal search finds filings."""
        response = await client.get("/api/v1/search?q=10-K&types=filing")
        assert response.status_code == 200
        data = response.json()
        # Should find filings
        assert "results" in data
    
    @pytest.mark.asyncio
    async def test_universal_search_type_filter(self, client: AsyncClient, sample_company):
        """Test filtering search by type."""
        response = await client.get("/api/v1/search?q=TEST&types=company")
        assert response.status_code == 200
        data = response.json()
        # All results should be companies
        for result in data["results"]:
            assert result["type"] == "company"
    
    @pytest.mark.asyncio
    async def test_search_suggestions(self, client: AsyncClient, sample_company):
        """Test search suggestions."""
        response = await client.get("/api/v1/search/suggestions?q=TES")
        assert response.status_code == 200
        data = response.json()
        assert "suggestions" in data
        # Should suggest TEST ticker
        assert any(s["value"] == "TEST" for s in data["suggestions"])
    
    @pytest.mark.asyncio
    async def test_search_suggestions_short_query(self, client: AsyncClient):
        """Test suggestions require minimum length."""
        response = await client.get("/api/v1/search/suggestions?q=")
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_trending_searches(self, client: AsyncClient):
        """Test trending searches endpoint."""
        response = await client.get("/api/v1/search/trending")
        assert response.status_code == 200
        data = response.json()
        assert "trending" in data
        assert "period" in data
    
    @pytest.mark.asyncio
    async def test_trending_searches_periods(self, client: AsyncClient):
        """Test different trending periods."""
        for period in ["hour", "day", "week"]:
            response = await client.get(f"/api/v1/search/trending?period={period}")
            assert response.status_code == 200
            data = response.json()
            assert data["period"] == period
    
    @pytest.mark.asyncio
    async def test_advanced_search(self, client: AsyncClient, sample_company):
        """Test advanced natural language search."""
        response = await client.get("/api/v1/search/advanced?query=technology companies")
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
    
    @pytest.mark.asyncio
    async def test_advanced_search_with_filters(self, client: AsyncClient, sample_company):
        """Test advanced search with JSON filters."""
        import json
        filters = json.dumps({"sectors": ["Technology"]})
        response = await client.get(f"/api/v1/search/advanced?query=companies&filters={filters}")
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_save_search(self, client: AsyncClient):
        """Test saving a search."""
        response = await client.post(
            "/api/v1/search/save?name=Tech%20Companies&query_text=technology&search_type=company"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Tech Companies"
