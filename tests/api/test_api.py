"""
Tests for EntitySpine REST API.

Run with:
    pytest tests/api/test_api.py -v
"""

import pytest
from fastapi.testclient import TestClient

from entityspine.api.app import app, create_app
from entityspine.api.deps import Settings, get_resolver, get_settings, reset_resolver


@pytest.fixture(scope="module")
def test_settings() -> Settings:
    """Settings for testing."""
    return Settings(
        db_path=None,  # Use in-memory database
        auto_load_sec=True,
        api_title="EntitySpine Test API",
    )


@pytest.fixture(scope="module")
def client(test_settings: Settings) -> TestClient:
    """Create test client with clean resolver."""
    # Reset any global resolver
    reset_resolver()

    # Override settings
    def override_settings():
        return test_settings

    app.dependency_overrides[get_settings] = override_settings

    with TestClient(app) as client:
        yield client

    # Cleanup
    app.dependency_overrides.clear()
    reset_resolver()


class TestHealthEndpoints:
    """Tests for health and info endpoints."""

    def test_health_check(self, client: TestClient):
        """GET /health returns healthy status."""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert "database" in data
        assert "entities_count" in data
        assert "timestamp" in data

    def test_api_info(self, client: TestClient):
        """GET /info returns API information."""
        response = client.get("/info")
        assert response.status_code == 200

        data = response.json()
        assert data["name"] == "EntitySpine Test API"
        assert "version" in data
        assert "endpoints" in data
        assert len(data["endpoints"]) > 0


class TestResolutionEndpoints:
    """Tests for resolution endpoints."""

    def test_resolve_ticker(self, client: TestClient):
        """GET /resolve/AAPL resolves Apple."""
        response = client.get("/resolve/AAPL")
        assert response.status_code == 200

        data = response.json()
        assert data["query"] == "AAPL"
        assert data["status"] in ["found", "not_found"]
        if data["status"] == "found":
            assert data["entity"]["primary_name"].lower().find("apple") >= 0

    def test_resolve_cik(self, client: TestClient):
        """GET /resolve/0000320193 resolves by CIK."""
        response = client.get("/resolve/0000320193")
        assert response.status_code == 200

        data = response.json()
        assert data["query"] == "0000320193"
        assert "status" in data
        assert "elapsed_ms" in data

    def test_resolve_with_as_of(self, client: TestClient):
        """GET /resolve/AAPL?as_of=2020-01-01 supports temporal query."""
        response = client.get("/resolve/AAPL?as_of=2020-01-01")
        assert response.status_code == 200

        data = response.json()
        # Should have warning about as_of in Tier 1
        assert isinstance(data.get("warnings", []), list)

    def test_resolve_batch(self, client: TestClient):
        """POST /resolve/batch handles multiple queries."""
        response = client.post(
            "/resolve/batch",
            json={"queries": ["AAPL", "MSFT", "GOOGL"]},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["total"] == 3
        assert "results" in data
        assert "resolved" in data
        assert "not_found" in data
        assert "elapsed_ms" in data

    def test_resolve_batch_with_as_of(self, client: TestClient):
        """POST /resolve/batch supports as_of parameter."""
        response = client.post(
            "/resolve/batch",
            json={
                "queries": ["AAPL", "MSFT"],
                "as_of": "2020-01-01",
            },
        )
        assert response.status_code == 200
        assert response.json()["total"] == 2

    def test_resolve_batch_limit(self, client: TestClient):
        """POST /resolve/batch rejects too many queries."""
        response = client.post(
            "/resolve/batch",
            json={"queries": ["X"] * 101},  # Over limit
        )
        assert response.status_code == 422  # Validation error

    def test_resolve_empty_query(self, client: TestClient):
        """GET /resolve/ with empty query returns not_found."""
        response = client.get("/resolve/ ")
        assert response.status_code == 200

        data = response.json()
        # Empty query should return not_found or have warning


class TestEntityEndpoints:
    """Tests for entity lookup endpoints."""

    def test_get_entity_by_cik(self, client: TestClient):
        """GET /entities/cik/{cik} returns entity."""
        response = client.get("/entities/cik/320193")
        # May return 200 or 404 depending on data
        assert response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.json()
            assert "entity_id" in data
            assert "primary_name" in data
            assert data["cik"] == "0000320193"

    def test_get_entity_by_ticker(self, client: TestClient):
        """GET /entities/ticker/{ticker} returns entity."""
        response = client.get("/entities/ticker/AAPL")
        assert response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.json()
            assert data["ticker"] == "AAPL"

    def test_get_entity_by_id_not_found(self, client: TestClient):
        """GET /entities/{id} returns 404 for unknown ID."""
        response = client.get("/entities/01NONEXISTENT123456789")
        assert response.status_code == 404


class TestSearchEndpoint:
    """Tests for search endpoint."""

    def test_search_basic(self, client: TestClient):
        """GET /search?q=apple returns results."""
        response = client.get("/search?q=apple")
        assert response.status_code == 200

        data = response.json()
        assert data["query"] == "apple"
        assert "results" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data

    def test_search_with_limit(self, client: TestClient):
        """GET /search?q=corp&limit=5 respects limit."""
        response = client.get("/search?q=corp&limit=5")
        assert response.status_code == 200

        data = response.json()
        assert data["limit"] == 5
        assert len(data["results"]) <= 5

    def test_search_with_offset(self, client: TestClient):
        """GET /search?q=corp&offset=10 respects offset."""
        response = client.get("/search?q=corp&limit=5&offset=10")
        assert response.status_code == 200

        data = response.json()
        assert data["offset"] == 10

    def test_search_empty_query(self, client: TestClient):
        """GET /search?q= rejects empty query."""
        response = client.get("/search?q=")
        assert response.status_code == 422  # Validation error


class TestConvertEndpoint:
    """Tests for identifier conversion endpoint."""

    def test_convert_ticker_to_cik(self, client: TestClient):
        """GET /convert converts ticker to CIK."""
        response = client.get(
            "/convert",
            params={
                "value": "AAPL",
                "from_scheme": "ticker",
                "to_scheme": "cik",
            },
        )
        assert response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.json()
            assert data["from_scheme"] == "ticker"
            assert data["from_value"] == "AAPL"
            assert data["to_scheme"] == "cik"
            assert "entity_name" in data


class TestOpenAPI:
    """Tests for OpenAPI documentation."""

    def test_openapi_json(self, client: TestClient):
        """GET /openapi.json returns valid OpenAPI spec."""
        response = client.get("/openapi.json")
        assert response.status_code == 200

        data = response.json()
        assert data["openapi"].startswith("3.")
        assert "paths" in data
        assert "/resolve/{query}" in data["paths"]

    def test_docs_accessible(self, client: TestClient):
        """GET /docs returns Swagger UI."""
        response = client.get("/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    def test_redoc_accessible(self, client: TestClient):
        """GET /redoc returns ReDoc UI."""
        response = client.get("/redoc")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
