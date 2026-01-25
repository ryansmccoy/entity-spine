"""
E2E Tests - Complete User Workflows
"""
import pytest
from httpx import AsyncClient


class TestCompanyResearchWorkflow:
    """
    E2E test for company research workflow.
    
    User journey:
    1. Search for a company
    2. View company profile
    3. Check recent filings
    4. View specific filing
    5. Add to watchlist
    """
    
    @pytest.mark.asyncio
    async def test_research_workflow(self, client: AsyncClient, sample_company, sample_filing):
        """Test complete company research workflow."""
        
        # Step 1: Search for company
        search_response = await client.get("/api/v1/companies/search?q=TEST")
        assert search_response.status_code == 200
        search_data = search_response.json()
        assert len(search_data["results"]) >= 1
        
        company_id = search_data["results"][0]["company_id"]
        
        # Step 2: View company profile
        company_response = await client.get(f"/api/v1/companies/{company_id}")
        assert company_response.status_code == 200
        company_data = company_response.json()
        assert company_data["ticker"] == "TEST"
        
        # Step 3: Check company metrics
        metrics_response = await client.get(f"/api/v1/companies/{company_id}/metrics")
        assert metrics_response.status_code == 200
        metrics_data = metrics_response.json()
        assert "current_metrics" in metrics_data
        
        # Step 4: Get company filings
        filings_response = await client.get(f"/api/v1/companies/{company_id}/filings")
        assert filings_response.status_code == 200
        filings_data = filings_response.json()
        assert len(filings_data["filings"]) >= 1
        
        filing_id = filings_data["filings"][0]["filing_id"]
        
        # Step 5: View specific filing
        filing_response = await client.get(f"/api/v1/filings/{filing_id}")
        assert filing_response.status_code == 200
        filing_data = filing_response.json()
        assert filing_data["form_type"] == "10-K"
        
        # Step 6: Add to watchlist
        watchlist_response = await client.post(
            f"/api/v1/watchlists/default/companies/{company_id}"
        )
        assert watchlist_response.status_code == 200


class TestFilingFeedWorkflow:
    """
    E2E test for filing feed workflow.
    
    User journey:
    1. Load filing feed
    2. Filter by form type
    3. Filter by sector
    4. Click on a filing
    5. View filing details
    """
    
    @pytest.mark.asyncio
    async def test_feed_workflow(self, client: AsyncClient, sample_company, sample_filing):
        """Test complete filing feed workflow."""
        
        # Step 1: Load filing feed
        feed_response = await client.get("/api/v1/filings/feed")
        assert feed_response.status_code == 200
        feed_data = feed_response.json()
        assert len(feed_data) >= 1
        
        # Step 2: Filter by form type
        filtered_response = await client.get("/api/v1/filings/feed?form_types=10-K")
        assert filtered_response.status_code == 200
        filtered_data = filtered_response.json()
        for item in filtered_data:
            assert item["form_type"] == "10-K"
        
        # Step 3: Filter by sector
        sector_response = await client.get("/api/v1/filings/feed?sector=Technology")
        assert sector_response.status_code == 200
        
        # Step 4: Get filing details
        if feed_data:
            filing_id = feed_data[0]["filing_id"]
            detail_response = await client.get(f"/api/v1/filings/{filing_id}")
            assert detail_response.status_code == 200


class TestSearchWorkflow:
    """
    E2E test for search workflow.
    
    User journey:
    1. Start typing search
    2. Get suggestions
    3. Execute search
    4. Filter results
    5. Click on result
    """
    
    @pytest.mark.asyncio
    async def test_search_workflow(self, client: AsyncClient, sample_company, sample_filing):
        """Test complete search workflow."""
        
        # Step 1: Get suggestions while typing
        suggestions_response = await client.get("/api/v1/search/suggestions?q=TES")
        assert suggestions_response.status_code == 200
        suggestions_data = suggestions_response.json()
        assert "suggestions" in suggestions_data
        
        # Step 2: Execute universal search
        search_response = await client.get("/api/v1/search?q=TEST")
        assert search_response.status_code == 200
        search_data = search_response.json()
        
        # Step 3: Filter to companies only
        company_search = await client.get("/api/v1/search?q=TEST&types=company")
        assert company_search.status_code == 200
        company_data = company_search.json()
        for result in company_data["results"]:
            assert result["type"] == "company"
        
        # Step 4: Access search result
        if company_data["results"]:
            result = company_data["results"][0]
            company_id = result["data"]["company_id"]
            
            company_response = await client.get(f"/api/v1/companies/{company_id}")
            assert company_response.status_code == 200


class TestKnowledgeGraphWorkflow:
    """
    E2E test for knowledge graph exploration workflow.
    
    User journey:
    1. Find entity for company
    2. Explore entity relationships
    3. Navigate to related entities
    4. Find path between entities
    """
    
    @pytest.mark.asyncio
    async def test_graph_exploration_workflow(
        self, client: AsyncClient, sample_entity, sample_company
    ):
        """Test complete knowledge graph workflow."""
        
        # Step 1: Get company's entity
        entities_response = await client.get(
            f"/api/v1/entities?entity_type=company&search={sample_company.name}"
        )
        assert entities_response.status_code == 200
        
        # Step 2: Get entity details
        entity_response = await client.get(f"/api/v1/entities/{sample_entity.entity_id}")
        assert entity_response.status_code == 200
        entity_data = entity_response.json()
        assert entity_data["entity_type"] == "company"
        
        # Step 3: Explore graph from entity
        graph_response = await client.get(
            f"/api/v1/entities/graph/explore?start_entity_id={sample_entity.entity_id}&depth=2"
        )
        assert graph_response.status_code == 200
        graph_data = graph_response.json()
        assert "nodes" in graph_data
        assert "edges" in graph_data
        
        # Step 4: Get entity relationships
        rel_response = await client.get(
            f"/api/v1/entities/{sample_entity.entity_id}/relationships"
        )
        assert rel_response.status_code == 200


class TestAPIHealthAndDiscovery:
    """E2E tests for API health and discovery endpoints."""
    
    @pytest.mark.asyncio
    async def test_health_check(self, client: AsyncClient):
        """Test health check endpoint."""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_api_docs_available(self, client: AsyncClient):
        """Test that API documentation is available."""
        # OpenAPI schema
        response = await client.get("/api/v1/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "paths" in data
