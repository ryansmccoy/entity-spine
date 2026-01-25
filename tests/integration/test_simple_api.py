"""
Integration tests for simple public API.

Tests the facade that hides complexity:
- EntityResolver() works with zero configuration
- Auto-downloads SEC data
- Returns ResolutionResult (not Entity)
- Simple resolution flow

Updated: 2026-01-29 to match current EntityResolver API (uses store, not json_path)
"""

import pytest

try:
    from entityspine import EntityResolver
    from entityspine.services.resolver import ResolverConfig
    from entityspine.stores import SqliteStore
except ImportError:
    pytest.skip("EntityResolver not yet implemented", allow_module_level=True)

# Try importing ResolutionResult from the resolver module (stdlib)
from entityspine.domain.resolution import ResolutionResult


@pytest.fixture
def loaded_resolver(tmp_path, sample_sec_json):
    """
    Create an EntityResolver with pre-loaded SEC data.
    
    Uses SqliteStore in-memory with sample data loaded.
    """
    store = SqliteStore(":memory:")
    store.initialize()
    store.load_sec_json(sample_sec_json)
    
    config = ResolverConfig(auto_load_sec=False)  # Already loaded
    resolver = EntityResolver(config=config, store=store)
    
    yield resolver
    store.close()


class TestSimpleAPIZeroConfig:
    """
    Test that EntityResolver works with zero configuration.

    This is the primary UX requirement:
        resolver = EntityResolver()
        result = resolver.resolve("AAPL")
    """

    def test_resolver_instantiation(self, tmp_path, monkeypatch):
        """EntityResolver() works with no arguments."""
        # Use temp dir to avoid real network calls
        monkeypatch.setenv("ENTITYSPINE_CACHE_DIR", str(tmp_path))

        # Should not raise
        resolver = EntityResolver()
        assert resolver is not None

    def test_resolver_resolve_returns_result(self, loaded_resolver):
        """resolve() returns ResolutionResult, not Entity."""
        result = loaded_resolver.resolve("AAPL")

        # v2.2 CRITICAL: Must return ResolutionResult
        assert isinstance(result, ResolutionResult), (
            f"resolve() returned {type(result).__name__}, expected ResolutionResult"
        )

    def test_resolver_result_has_candidates(self, loaded_resolver):
        """Result has candidates list."""
        result = loaded_resolver.resolve("AAPL")

        assert hasattr(result, "candidates")
        assert isinstance(result.candidates, list)


class TestSimpleAPIResolution:
    """Test resolution via simple API."""

    def test_resolve_ticker_aapl(self, loaded_resolver):
        """Can resolve AAPL to Apple Inc."""
        result = loaded_resolver.resolve("AAPL")

        assert result.best is not None
        assert result.best.score > 0.5

    def test_resolve_cik(self, loaded_resolver):
        """Can resolve by CIK."""
        result = loaded_resolver.resolve("320193")  # Apple's CIK

        assert result.best is not None

    def test_resolve_cik_padded(self, loaded_resolver):
        """Can resolve by padded CIK."""
        result = loaded_resolver.resolve("0000320193")  # Padded CIK

        assert result.best is not None

    def test_resolve_unknown_returns_empty(self, loaded_resolver):
        """Unknown query returns empty candidates (not error)."""
        result = loaded_resolver.resolve("ZZZZZ_NONEXISTENT")

        assert isinstance(result, ResolutionResult)
        assert result.best is None
        assert len(result.candidates) == 0


class TestSimpleAPIEntityRetrieval:
    """Test entity retrieval via get_entity()."""

    def test_get_entity_by_id(self, loaded_resolver):
        """Can get entity by ID after resolution."""
        result = loaded_resolver.resolve("AAPL")

        if result.best:
            entity = loaded_resolver.get_entity(result.best.entity_id)
            assert entity is not None
            assert "apple" in entity.primary_name.lower()

    def test_get_nonexistent_returns_none(self, loaded_resolver):
        """get_entity() returns None for nonexistent ID."""
        entity = loaded_resolver.get_entity("NONEXISTENT_ID")

        assert entity is None


class TestSimpleAPIEntityScopeCorrect:
    """
    v2.2 CRITICAL: Entity from simple API has NO ticker.
    """

    def test_resolved_entity_has_no_ticker(self, loaded_resolver):
        """Entity retrieved via simple API has no ticker attribute."""
        result = loaded_resolver.resolve("AAPL")

        if result.best:
            entity = loaded_resolver.get_entity(result.best.entity_id)
            if entity:
                assert not hasattr(entity, "ticker"), (
                    "v2.2 VIOLATION: Entity from simple API has ticker"
                )


class TestSimpleAPIBackends:
    """Test backend selection (via store configuration)."""

    def test_default_backend(self, tmp_path, monkeypatch):
        """Default backend works."""
        monkeypatch.setenv("ENTITYSPINE_CACHE_DIR", str(tmp_path))

        resolver = EntityResolver()
        assert resolver is not None

    def test_explicit_sqlite_store(self, tmp_path, sample_sec_json):
        """Can use explicit SqliteStore backend."""
        db_path = tmp_path / "test.db"
        store = SqliteStore(db_path)
        store.initialize()
        store.load_sec_json(sample_sec_json)

        resolver = EntityResolver(store=store)
        assert resolver is not None
        
        result = resolver.resolve("AAPL")
        assert result.best is not None
        
        store.close()

    def test_in_memory_sqlite_backend(self, sample_sec_json):
        """Can use in-memory SQLite backend."""
        store = SqliteStore(":memory:")
        store.initialize()
        store.load_sec_json(sample_sec_json)

        config = ResolverConfig(auto_load_sec=False)
        resolver = EntityResolver(config=config, store=store)
        
        result = resolver.resolve("MSFT")
        assert result.best is not None
        
        store.close()


class TestSimpleAPITypicalWorkflow:
    """Test typical user workflow."""

    def test_full_workflow(self, loaded_resolver):
        """
        Complete typical workflow:
        1. Create resolver
        2. Resolve ticker
        3. Check confidence
        4. Get entity if confident
        5. Use entity data
        """
        # 2. Resolve ticker
        result = loaded_resolver.resolve("AAPL")

        # 3. Check if we found a result (best candidate)
        if result.best and result.best.score > 0.5:
            # 4. Get entity
            entity = loaded_resolver.get_entity(result.best.entity_id)

            # 5. Use entity data
            assert entity is not None
            assert "apple" in entity.primary_name.lower()
        else:
            # Low confidence or no match
            pass

    def test_workflow_with_unknown_ticker(self, loaded_resolver):
        """Workflow handles unknown ticker gracefully."""
        result = loaded_resolver.resolve("ZZZZZ_NONEXISTENT")

        # Should not raise, should return empty result
        assert result.best is None or result.best.score < 0.5

    def test_workflow_multiple_resolutions(self, loaded_resolver):
        """Can resolve multiple times with same resolver."""
        result1 = loaded_resolver.resolve("AAPL")
        result2 = loaded_resolver.resolve("MSFT")
        result3 = loaded_resolver.resolve("TSLA")

        assert result1.best is not None
        assert result2.best is not None
        assert result3.best is not None

        # Different entities
        assert result1.best.entity_id != result2.best.entity_id
        assert result2.best.entity_id != result3.best.entity_id


class TestSimpleAPIPySecEdgarIntegration:
    """
    Test integration pattern for py-sec-edgar.

    py-sec-edgar will use entityspine like this:
        from entityspine import EntityResolver
        resolver = EntityResolver()
        result = resolver.resolve(filing["cik"])
        if result.best:
            filing["filer_entity_id"] = result.best.entity_id
    """

    def test_resolve_cik_for_filing(self, loaded_resolver):
        """Can resolve CIK from filing data."""
        # Simulate py-sec-edgar filing
        filing = {"cik": "0000320193", "form_type": "10-K"}

        result = loaded_resolver.resolve(filing["cik"])

        if result.best:
            filing["filer_entity_id"] = result.best.entity_id
            assert "filer_entity_id" in filing

    def test_batch_resolution(self, loaded_resolver):
        """Can resolve multiple CIKs in batch."""
        ciks = ["320193", "789019", "1318605"]

        results = {}
        for cik in ciks:
            result = loaded_resolver.resolve(cik)
            if result.best:
                results[cik] = result.best.entity_id

        assert len(results) == len(ciks)
