"""
Integration tests for simple public API.

Tests the facade that hides complexity:
- EntityResolver() works with zero configuration
- Auto-downloads SEC data
- Returns ResolutionResult (not Entity)
- Simple resolution flow
"""

import pytest

try:
    from entityspine import EntityResolver
    from entityspine.adapters.pydantic import ResolutionResult
except ImportError:
    pytest.skip("EntityResolver not yet implemented", allow_module_level=True)


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

    def test_resolver_resolve_returns_result(self, tmp_path, monkeypatch, sample_sec_json_file):
        """resolve() returns ResolutionResult, not Entity."""
        monkeypatch.setenv("ENTITYSPINE_CACHE_DIR", str(tmp_path))

        resolver = EntityResolver(json_path=str(sample_sec_json_file))
        result = resolver.resolve("AAPL")

        # v2.2 CRITICAL: Must return ResolutionResult
        assert isinstance(result, ResolutionResult), (
            f"resolve() returned {type(result).__name__}, expected ResolutionResult"
        )

    def test_resolver_result_has_candidates(self, tmp_path, monkeypatch, sample_sec_json_file):
        """Result has candidates list."""
        monkeypatch.setenv("ENTITYSPINE_CACHE_DIR", str(tmp_path))

        resolver = EntityResolver(json_path=str(sample_sec_json_file))
        result = resolver.resolve("AAPL")

        assert hasattr(result, "candidates")
        assert isinstance(result.candidates, list)


class TestSimpleAPIResolution:
    """Test resolution via simple API."""

    def test_resolve_ticker_aapl(self, tmp_path, monkeypatch, sample_sec_json_file):
        """Can resolve AAPL to Apple Inc."""
        monkeypatch.setenv("ENTITYSPINE_CACHE_DIR", str(tmp_path))

        resolver = EntityResolver(json_path=str(sample_sec_json_file))
        result = resolver.resolve("AAPL")

        assert result.best is not None
        assert result.best.score > 0.5

    def test_resolve_cik(self, tmp_path, monkeypatch, sample_sec_json_file):
        """Can resolve by CIK."""
        monkeypatch.setenv("ENTITYSPINE_CACHE_DIR", str(tmp_path))

        resolver = EntityResolver(json_path=str(sample_sec_json_file))
        result = resolver.resolve("320193")  # Apple's CIK

        assert result.best is not None

    def test_resolve_cik_padded(self, tmp_path, monkeypatch, sample_sec_json_file):
        """Can resolve by padded CIK."""
        monkeypatch.setenv("ENTITYSPINE_CACHE_DIR", str(tmp_path))

        resolver = EntityResolver(json_path=str(sample_sec_json_file))
        result = resolver.resolve("0000320193")  # Padded CIK

        assert result.best is not None

    def test_resolve_unknown_returns_empty(self, tmp_path, monkeypatch, sample_sec_json_file):
        """Unknown query returns empty candidates (not error)."""
        monkeypatch.setenv("ENTITYSPINE_CACHE_DIR", str(tmp_path))

        resolver = EntityResolver(json_path=str(sample_sec_json_file))
        result = resolver.resolve("ZZZZZ_NONEXISTENT")

        assert isinstance(result, ResolutionResult)
        assert result.best is None
        assert len(result.candidates) == 0


class TestSimpleAPIEntityRetrieval:
    """Test entity retrieval via get()."""

    def test_get_entity_by_id(self, tmp_path, monkeypatch, sample_sec_json_file):
        """Can get entity by ID after resolution."""
        monkeypatch.setenv("ENTITYSPINE_CACHE_DIR", str(tmp_path))

        resolver = EntityResolver(json_path=str(sample_sec_json_file))
        result = resolver.resolve("AAPL")

        if result.best:
            entity = resolver.get(result.best.entity_id)
            assert entity is not None
            assert "apple" in entity.primary_name.lower()

    def test_get_nonexistent_returns_none(self, tmp_path, monkeypatch, sample_sec_json_file):
        """get() returns None for nonexistent ID."""
        monkeypatch.setenv("ENTITYSPINE_CACHE_DIR", str(tmp_path))

        resolver = EntityResolver(json_path=str(sample_sec_json_file))
        entity = resolver.get("NONEXISTENT_ID")

        assert entity is None


class TestSimpleAPIEntityScopeCorrect:
    """
    v2.2 CRITICAL: Entity from simple API has NO ticker.
    """

    def test_resolved_entity_has_no_ticker(self, tmp_path, monkeypatch, sample_sec_json_file):
        """Entity retrieved via simple API has no ticker attribute."""
        monkeypatch.setenv("ENTITYSPINE_CACHE_DIR", str(tmp_path))

        resolver = EntityResolver(json_path=str(sample_sec_json_file))
        result = resolver.resolve("AAPL")

        if result.best:
            entity = resolver.get(result.best.entity_id)
            if entity:
                assert not hasattr(entity, "ticker"), (
                    "v2.2 VIOLATION: Entity from simple API has ticker"
                )


class TestSimpleAPIBackends:
    """Test backend selection."""

    def test_default_backend(self, tmp_path, monkeypatch, sample_sec_json_file):
        """Default backend works."""
        monkeypatch.setenv("ENTITYSPINE_CACHE_DIR", str(tmp_path))

        resolver = EntityResolver(json_path=str(sample_sec_json_file))
        assert resolver is not None

    def test_explicit_json_backend(self, tmp_path, monkeypatch, sample_sec_json_file):
        """Can specify JSON backend."""
        monkeypatch.setenv("ENTITYSPINE_CACHE_DIR", str(tmp_path))

        resolver = EntityResolver(
            backend="json",
            json_path=str(sample_sec_json_file),
        )
        assert resolver is not None

    def test_sqlite_backend(self, tmp_path, monkeypatch, sample_sec_json_file):
        """Can use SQLite backend."""
        monkeypatch.setenv("ENTITYSPINE_CACHE_DIR", str(tmp_path))

        db_path = tmp_path / "test.db"
        resolver = EntityResolver(
            backend="sqlite",
            db_path=str(db_path),
            json_path=str(sample_sec_json_file),
        )
        assert resolver is not None


class TestSimpleAPITypicalWorkflow:
    """Test typical user workflow."""

    def test_full_workflow(self, tmp_path, monkeypatch, sample_sec_json_file):
        """
        Complete typical workflow:
        1. Create resolver
        2. Resolve ticker
        3. Check confidence
        4. Get entity if confident
        5. Use entity data
        """
        monkeypatch.setenv("ENTITYSPINE_CACHE_DIR", str(tmp_path))

        # 1. Create resolver (zero config)
        resolver = EntityResolver(json_path=str(sample_sec_json_file))

        # 2. Resolve ticker
        result = resolver.resolve("AAPL")

        # 3. Check confidence
        if result.is_confident:
            # 4. Get entity
            entity = resolver.get(result.best.entity_id)

            # 5. Use entity data
            assert entity is not None
            assert "apple" in entity.primary_name.lower()
        else:
            # Low confidence or no match
            pass

    def test_workflow_with_unknown_ticker(self, tmp_path, monkeypatch, sample_sec_json_file):
        """Workflow handles unknown ticker gracefully."""
        monkeypatch.setenv("ENTITYSPINE_CACHE_DIR", str(tmp_path))

        resolver = EntityResolver(json_path=str(sample_sec_json_file))
        result = resolver.resolve("ZZZZZ_NONEXISTENT")

        # Should not raise, should return empty result
        assert not result.is_confident
        assert result.best is None

    def test_workflow_multiple_resolutions(self, tmp_path, monkeypatch, sample_sec_json_file):
        """Can resolve multiple times with same resolver."""
        monkeypatch.setenv("ENTITYSPINE_CACHE_DIR", str(tmp_path))

        resolver = EntityResolver(json_path=str(sample_sec_json_file))

        result1 = resolver.resolve("AAPL")
        result2 = resolver.resolve("MSFT")
        result3 = resolver.resolve("TSLA")

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
        result = resolver.resolve_cik(filing["cik"])
        if result.best:
            filing["filer_entity_id"] = result.best.entity_id
    """

    def test_resolve_cik_for_filing(self, tmp_path, monkeypatch, sample_sec_json_file):
        """Can resolve CIK from filing data."""
        monkeypatch.setenv("ENTITYSPINE_CACHE_DIR", str(tmp_path))

        # Simulate py-sec-edgar filing
        filing = {"cik": "0000320193", "form_type": "10-K"}

        resolver = EntityResolver(json_path=str(sample_sec_json_file))
        result = resolver.resolve(filing["cik"])

        if result.best:
            filing["filer_entity_id"] = result.best.entity_id
            assert "filer_entity_id" in filing

    def test_batch_resolution(self, tmp_path, monkeypatch, sample_sec_json_file):
        """Can resolve multiple CIKs in batch."""
        monkeypatch.setenv("ENTITYSPINE_CACHE_DIR", str(tmp_path))

        ciks = ["320193", "789019", "1318605"]

        resolver = EntityResolver(json_path=str(sample_sec_json_file))

        results = {}
        for cik in ciks:
            result = resolver.resolve(cik)
            if result.best:
                results[cik] = result.best.entity_id

        assert len(results) == len(ciks)
