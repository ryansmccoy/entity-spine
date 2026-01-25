"""
Unit Tests - Entities & Knowledge Graph API
"""
import pytest
from httpx import AsyncClient


class TestEntitiesAPI:
    """Tests for Entities API endpoints."""
    
    @pytest.mark.asyncio
    async def test_list_entities_empty(self, client: AsyncClient):
        """Test listing entities when database is empty."""
        response = await client.get("/api/v1/entities")
        assert response.status_code == 200
        data = response.json()
        assert data["entities"] == []
        assert data["total"] == 0
    
    @pytest.mark.asyncio
    async def test_list_entities_with_data(self, client: AsyncClient, sample_entity):
        """Test listing entities with sample data."""
        response = await client.get("/api/v1/entities")
        assert response.status_code == 200
        data = response.json()
        assert len(data["entities"]) == 1
        assert data["entities"][0]["entity_type"] == "company"
    
    @pytest.mark.asyncio
    async def test_list_entities_filter_type(self, client: AsyncClient, sample_entity):
        """Test filtering entities by type."""
        # Match
        response = await client.get("/api/v1/entities?entity_type=company")
        assert response.status_code == 200
        data = response.json()
        assert len(data["entities"]) == 1
        
        # No match
        response = await client.get("/api/v1/entities?entity_type=person")
        assert response.status_code == 200
        data = response.json()
        assert len(data["entities"]) == 0
    
    @pytest.mark.asyncio
    async def test_get_entity_by_id(self, client: AsyncClient, sample_entity):
        """Test getting entity by ID."""
        response = await client.get(f"/api/v1/entities/{sample_entity.entity_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["entity_type"] == "company"
        assert data["is_verified"] == True
    
    @pytest.mark.asyncio
    async def test_get_entity_not_found(self, client: AsyncClient):
        """Test 404 for non-existent entity."""
        from uuid import uuid4
        response = await client.get(f"/api/v1/entities/{uuid4()}")
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_get_entity_types(self, client: AsyncClient, sample_entity):
        """Test getting entity types."""
        response = await client.get("/api/v1/entities/types")
        assert response.status_code == 200
        data = response.json()
        assert "types" in data
        assert any(t["type"] == "company" for t in data["types"])
    
    @pytest.mark.asyncio
    async def test_get_relationship_types(self, client: AsyncClient):
        """Test getting relationship types."""
        response = await client.get("/api/v1/entities/relationship-types")
        assert response.status_code == 200
        data = response.json()
        assert "relationship_types" in data
    
    @pytest.mark.asyncio
    async def test_get_entity_relationships_empty(self, client: AsyncClient, sample_entity):
        """Test getting relationships when none exist."""
        response = await client.get(f"/api/v1/entities/{sample_entity.entity_id}/relationships")
        assert response.status_code == 200
        data = response.json()
        assert data["relationships"] == []
        assert data["count"] == 0
    
    @pytest.mark.asyncio
    async def test_get_entity_mentions_empty(self, client: AsyncClient, sample_entity):
        """Test getting mentions when none exist."""
        response = await client.get(f"/api/v1/entities/{sample_entity.entity_id}/mentions")
        assert response.status_code == 200
        data = response.json()
        assert data["mentions"] == []
        assert data["count"] == 0


class TestKnowledgeGraphAPI:
    """Tests for Knowledge Graph exploration endpoints."""
    
    @pytest.mark.asyncio
    async def test_explore_graph(self, client: AsyncClient, sample_entity):
        """Test graph exploration from starting entity."""
        response = await client.get(f"/api/v1/entities/graph/explore?start_entity_id={sample_entity.entity_id}")
        assert response.status_code == 200
        data = response.json()
        assert "nodes" in data
        assert "edges" in data
        assert data["node_count"] >= 1
    
    @pytest.mark.asyncio
    async def test_explore_graph_with_depth(self, client: AsyncClient, sample_entity):
        """Test graph exploration with custom depth."""
        response = await client.get(f"/api/v1/entities/graph/explore?start_entity_id={sample_entity.entity_id}&depth=3")
        assert response.status_code == 200
        data = response.json()
        assert data["depth"] == 3
    
    @pytest.mark.asyncio
    async def test_find_path_same_entity(self, client: AsyncClient, sample_entity):
        """Test path finding when start and end are same."""
        response = await client.get(
            f"/api/v1/entities/graph/path?from_entity_id={sample_entity.entity_id}&to_entity_id={sample_entity.entity_id}"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["found"] == True
        assert data["length"] == 0
    
    @pytest.mark.asyncio
    async def test_find_path_no_path(self, client: AsyncClient, sample_entity):
        """Test path finding when no path exists."""
        from uuid import uuid4
        response = await client.get(
            f"/api/v1/entities/graph/path?from_entity_id={sample_entity.entity_id}&to_entity_id={uuid4()}"
        )
        assert response.status_code == 200
        data = response.json()
        # Either not found or entity doesn't exist
        assert "found" in data
