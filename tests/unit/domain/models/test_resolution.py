"""
Tests for v2.2 ResolutionResult domain dataclass.

v2.2 CRITICAL:
- resolve() MUST return ResolutionResult, not Entity|None
- ResolutionResult has entity, status, tier, warnings
- Tier capability honesty: warnings when as_of ignored

IMPORTANT: These tests use the CANONICAL domain dataclasses (entityspine.domain),
NOT the optional Pydantic wrappers (entityspine.adapters.pydantic).
"""

from datetime import date

import pytest

from entityspine.domain import (
    Entity,
    MatchReason,
    ResolutionCandidate,
    ResolutionStatus,
    ResolutionTier,
    ResolutionWarning,
    ambiguous_result,
    found_result,
    not_found_result,
)


@pytest.fixture
def sample_entity():
    """Create a sample entity for testing.

    v2.2.3: Entity no longer has cik field - identifiers tracked via IdentifierClaim.
    """
    return Entity(
        entity_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
        primary_name="Apple Inc.",
        source_system="sec",
        source_id="0000320193",
    )


class TestResolutionResult:
    """Test ResolutionResult creation and attributes."""

    def test_result_has_entity(self, sample_entity):
        """ResolutionResult contains entity when found."""
        result = found_result(
            entity=sample_entity,
            query="AAPL",
            tier=ResolutionTier.TIER_0,
        )
        assert result.entity == sample_entity
        assert result.status == ResolutionStatus.FOUND

    def test_result_has_status(self, sample_entity):
        """ResolutionResult has status field."""
        result = found_result(
            entity=sample_entity,
            query="AAPL",
            tier=ResolutionTier.TIER_0,
        )
        assert result.status == ResolutionStatus.FOUND

    def test_result_has_tier(self, sample_entity):
        """ResolutionResult indicates which tier provided it."""
        result = found_result(
            entity=sample_entity,
            query="AAPL",
            tier=ResolutionTier.TIER_1,
        )
        assert result.tier == ResolutionTier.TIER_1

    def test_result_has_query(self, sample_entity):
        """ResolutionResult records original query."""
        result = found_result(
            entity=sample_entity,
            query="AAPL",
            tier=ResolutionTier.TIER_0,
        )
        assert result.query == "AAPL"

    def test_not_found_result(self):
        """not_found_result creates proper NOT_FOUND result."""
        result = not_found_result(
            query="UNKNOWN",
            tier=ResolutionTier.TIER_0,
        )
        assert result.entity is None
        assert result.status == ResolutionStatus.NOT_FOUND
        assert result.query == "UNKNOWN"


class TestResolutionResultProperties:
    """Test ResolutionResult convenience properties."""

    def test_found_property_true(self, sample_entity):
        """found property returns True when entity exists."""
        result = found_result(
            entity=sample_entity,
            query="AAPL",
            tier=ResolutionTier.TIER_0,
        )
        assert result.found is True

    def test_found_property_false(self):
        """found property returns False when not found."""
        result = not_found_result(
            query="UNKNOWN",
            tier=ResolutionTier.TIER_0,
        )
        assert result.found is False

    def test_has_warnings_property(self, sample_entity):
        """has_warnings property detects warnings."""
        result = found_result(
            entity=sample_entity,
            query="AAPL",
            tier=ResolutionTier.TIER_0,
        )
        assert result.has_warnings is False

        result.add_warning("low_confidence: test")
        assert result.has_warnings is True


class TestTierCapabilityHonesty:
    """
    v2.2 CRITICAL: Tier capability honesty tests.

    When as_of is requested but tier can't honor it,
    the result must warn the caller.
    """

    def test_as_of_honored_when_supported(self, sample_entity):
        """When tier supports temporal, as_of_honored is True."""
        result = found_result(
            entity=sample_entity,
            query="AAPL",
            tier=ResolutionTier.TIER_2,
            as_of=date(2020, 1, 1),
            as_of_honored=True,
        )
        assert result.as_of == date(2020, 1, 1)
        assert result.as_of_honored is True

    def test_as_of_ignored_when_not_supported(self, sample_entity):
        """When tier can't honor as_of, as_of_honored is False."""
        result = found_result(
            entity=sample_entity,
            query="AAPL",
            tier=ResolutionTier.TIER_0,
            as_of=date(2020, 1, 1),
            as_of_honored=False,
        )
        assert result.as_of == date(2020, 1, 1)
        assert result.as_of_honored is False

    def test_warning_when_as_of_ignored(self, sample_entity):
        """Result should have warning when as_of was ignored."""
        result = found_result(
            entity=sample_entity,
            query="AAPL",
            tier=ResolutionTier.TIER_0,
            as_of=date(2020, 1, 1),
            as_of_honored=False,
        )
        result.add_warning("as_of_ignored: Tier 0 store lacks temporal data")
        assert result.has_warnings
        assert any("as_of_ignored" in w for w in result.warnings)


class TestResolutionStatus:
    """Test ResolutionStatus enum."""

    def test_status_values(self):
        """ResolutionStatus has expected values."""
        assert ResolutionStatus.FOUND.value == "found"
        assert ResolutionStatus.NOT_FOUND.value == "not_found"
        assert ResolutionStatus.AMBIGUOUS.value == "ambiguous"
        assert ResolutionStatus.REDIRECTED.value == "redirected"


class TestResolutionTier:
    """Test ResolutionTier enum."""

    def test_tier_values(self):
        """ResolutionTier has expected values."""
        assert ResolutionTier.TIER_0.value == 0
        assert ResolutionTier.TIER_1.value == 1
        assert ResolutionTier.TIER_2.value == 2


class TestResolutionWarning:
    """Test ResolutionWarning constants."""

    def test_warning_constants(self):
        """ResolutionWarning has expected constants."""
        assert ResolutionWarning.AS_OF_IGNORED == "as_of_ignored"
        assert ResolutionWarning.LOW_CONFIDENCE == "low_confidence"
        assert ResolutionWarning.REDIRECT_FOLLOWED == "redirect_followed"


class TestAmbiguousResult:
    """Test ambiguous resolution results."""

    def test_ambiguous_result_has_alternatives(self, sample_entity):
        """Ambiguous result includes alternative candidates."""
        candidate1 = ResolutionCandidate(
            entity_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            score=0.9,
            match_reason=MatchReason.NAME_EXACT,
        )
        candidate2 = ResolutionCandidate(
            entity_id="01XYZ3NDEKTSV4RRFFQ69G5FAV",
            score=0.85,
            match_reason=MatchReason.NAME_FUZZY,
        )
        result = ambiguous_result(
            query="Apple",
            candidates=[candidate1, candidate2],
            tier=ResolutionTier.TIER_0,
        )
        assert result.status == ResolutionStatus.AMBIGUOUS
        assert len(result.candidates) == 2

    def test_ambiguous_result_entity_is_none(self, sample_entity):
        """Ambiguous result has no single entity."""
        candidate1 = ResolutionCandidate(
            entity_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            score=0.9,
            match_reason=MatchReason.NAME_EXACT,
        )
        candidate2 = ResolutionCandidate(
            entity_id="01XYZ3NDEKTSV4RRFFQ69G5FAV",
            score=0.85,
            match_reason=MatchReason.NAME_FUZZY,
        )
        result = ambiguous_result(
            query="Apple",
            candidates=[candidate1, candidate2],
            tier=ResolutionTier.TIER_0,
        )
        assert result.entity is None
        assert result.found is False


class TestResultMetadata:
    """Test result metadata fields."""

    def test_elapsed_ms(self, sample_entity):
        """Result tracks elapsed time."""
        result = found_result(
            entity=sample_entity,
            query="AAPL",
            tier=ResolutionTier.TIER_0,
            elapsed_ms=5.2,
        )
        assert result.elapsed_ms == 5.2

    def test_confidence_score(self, sample_entity):
        """Result can have confidence score."""
        result = found_result(
            entity=sample_entity,
            query="AAPL",
            tier=ResolutionTier.TIER_0,
        )
        result.confidence = 0.95
        assert result.confidence == 0.95

    def test_redirect_chain(self, sample_entity):
        """Result can track redirect chain."""
        result = found_result(
            entity=sample_entity,
            query="OLD_ID",
            tier=ResolutionTier.TIER_0,
        )
        result.redirect_chain = ["OLD_ID", "01ARZ3NDEKTSV4RRFFQ69G5FAV"]
        assert len(result.redirect_chain) == 2
