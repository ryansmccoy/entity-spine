"""
Tests for Entity domain dataclass.

v2.2.3+ CRITICAL DESIGN:
- Entity must NOT have ticker attribute (belongs on Listing)
- Entity must NOT have exchange attribute (belongs on Listing)
- Entity must NOT have cik/lei/ein fields (use IdentifierClaim)
- Entity can track merge redirects
- All identifiers are tracked via IdentifierClaim for provenance

IMPORTANT: These tests use the CANONICAL domain dataclasses (entityspine.domain),
NOT the optional Pydantic wrappers (entityspine.adapters.pydantic).
"""

import dataclasses

import pytest

from entityspine.domain import Entity, EntityStatus, EntityType


class TestEntityCreation:
    """Test Entity creation and attributes."""

    def test_entity_minimal_creation(self):
        """Entity can be created with minimal required fields."""
        entity = Entity(
            entity_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            primary_name="Apple Inc.",
        )
        assert entity.entity_id == "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        assert entity.primary_name == "Apple Inc."

    def test_entity_with_source_system(self):
        """Entity can have source_system provenance."""
        entity = Entity(
            entity_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            primary_name="Apple Inc.",
            source_system="sec",
            source_id="0000320193",
        )
        assert entity.source_system == "sec"
        assert entity.source_id == "0000320193"

    def test_entity_with_all_fields(self):
        """Entity can be created with all optional fields."""
        entity = Entity(
            entity_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            primary_name="Apple Inc.",
            entity_type=EntityType.ORGANIZATION,
            status=EntityStatus.ACTIVE,
            sic_code="7370",
            jurisdiction="US-DE",
            source_system="sec",
        )
        assert entity.sic_code == "7370"
        assert entity.jurisdiction == "US-DE"
        assert entity.source_system == "sec"

    def test_entity_defaults(self):
        """Entity has correct default values."""
        entity = Entity(
            entity_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            primary_name="Apple Inc.",
        )
        assert entity.entity_type == EntityType.ORGANIZATION
        assert entity.status == EntityStatus.ACTIVE
        assert entity.redirect_to is None
        assert entity.redirect_reason is None
        assert entity.source_system == "unknown"


class TestEntityScopeEnforcement:
    """
    v2.2.3 CRITICAL: Entity must NOT have ticker/exchange or identifier fields.

    These tests enforce the fundamental v2.2.3 design rules:
    - Ticker belongs to Listing, not Entity
    - Identifiers are tracked via IdentifierClaim for provenance
    """

    def test_entity_has_no_ticker_attribute(self):
        """Entity must NOT have ticker attribute."""
        entity = Entity(
            entity_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            primary_name="Apple Inc.",
        )
        assert not hasattr(entity, "ticker"), "v2.2 VIOLATION: Entity has ticker attribute"

    def test_entity_has_no_ticker_field(self):
        """Entity dataclass must NOT have ticker field."""
        field_names = {f.name for f in dataclasses.fields(Entity)}
        assert "ticker" not in field_names, "v2.2 VIOLATION: Entity model has ticker field"

    def test_entity_has_no_exchange_attribute(self):
        """Entity must NOT have exchange attribute."""
        entity = Entity(
            entity_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            primary_name="Apple Inc.",
        )
        assert not hasattr(entity, "exchange"), "v2.2 VIOLATION: Entity has exchange attribute"

    def test_entity_has_no_exchange_field(self):
        """Entity dataclass must NOT have exchange field."""
        field_names = {f.name for f in dataclasses.fields(Entity)}
        assert "exchange" not in field_names, "v2.2 VIOLATION: Entity model has exchange field"

    def test_entity_has_no_cik_field(self):
        """v2.2.3: Entity must NOT have cik field - use IdentifierClaim."""
        field_names = {f.name for f in dataclasses.fields(Entity)}
        assert "cik" not in field_names, (
            "v2.2.3 VIOLATION: Entity model has cik field (use IdentifierClaim)"
        )

    def test_entity_has_no_lei_field(self):
        """v2.2.3: Entity must NOT have lei field - use IdentifierClaim."""
        field_names = {f.name for f in dataclasses.fields(Entity)}
        assert "lei" not in field_names, (
            "v2.2.3 VIOLATION: Entity model has lei field (use IdentifierClaim)"
        )

    def test_entity_has_no_identifiers_dict(self):
        """v2.2.3: Entity must NOT have identifiers dict - use IdentifierClaim."""
        field_names = {f.name for f in dataclasses.fields(Entity)}
        assert "identifiers" not in field_names, (
            "v2.2.3 VIOLATION: Entity model has identifiers dict (use IdentifierClaim)"
        )

    def test_entity_cannot_accept_ticker_kwarg(self):
        """Entity must reject ticker keyword argument."""
        with pytest.raises(TypeError):
            Entity(
                entity_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
                primary_name="Apple Inc.",
                ticker="AAPL",  # This should fail - unexpected kwarg
            )

    def test_entity_cannot_accept_cik_kwarg(self):
        """v2.2.3: Entity must reject cik keyword argument."""
        with pytest.raises(TypeError):
            Entity(
                entity_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
                primary_name="Apple Inc.",
                cik="0000320193",  # This should fail - unexpected kwarg
            )


class TestEntityValidation:
    """Test Entity validation."""

    def test_entity_requires_entity_id(self):
        """Entity must have entity_id."""
        with pytest.raises(ValueError):
            Entity(entity_id="", primary_name="Test")

    def test_entity_requires_primary_name(self):
        """Entity must have primary_name."""
        with pytest.raises(ValueError):
            Entity(entity_id="01ARZ3NDEKTSV4RRFFQ69G5FAV", primary_name="")


class TestEntityMerge:
    """Test Entity merge/redirect support."""

    def test_entity_can_track_merge_target(self):
        """Entity can record what it merged into."""
        entity = Entity(
            entity_id="01OLD3NDEKTSV4RRFFQ69G5FAV",
            primary_name="Old Company",
            redirect_to="01NEW3NDEKTSV4RRFFQ69G5FAV",
            redirect_reason="merged",
            status=EntityStatus.MERGED,
        )
        assert entity.redirect_to == "01NEW3NDEKTSV4RRFFQ69G5FAV"
        assert entity.redirect_reason == "merged"
        assert entity.status == EntityStatus.MERGED

    def test_is_redirect_property(self):
        """Entity has is_redirect property."""
        entity = Entity(
            entity_id="01OLD3NDEKTSV4RRFFQ69G5FAV",
            primary_name="Old Company",
            redirect_to="01NEW3NDEKTSV4RRFFQ69G5FAV",
        )
        assert entity.is_redirect is True

        non_redirect = Entity(
            entity_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            primary_name="Apple Inc.",
        )
        assert non_redirect.is_redirect is False

    def test_merge_into_helper(self):
        """Entity.merge_into creates a merged version."""
        entity = Entity(
            entity_id="01OLD3NDEKTSV4RRFFQ69G5FAV",
            primary_name="Old Company",
        )
        merged = entity.merge_into("01NEW3NDEKTSV4RRFFQ69G5FAV", reason="acquisition")

        assert merged.redirect_to == "01NEW3NDEKTSV4RRFFQ69G5FAV"
        assert merged.redirect_reason == "acquisition"
        assert merged.status == EntityStatus.MERGED
        assert merged.merged_at is not None


class TestEntityType:
    """Test EntityType enum."""

    def test_entity_type_values(self):
        """EntityType has expected values."""
        assert EntityType.ORGANIZATION.value == "organization"
        assert EntityType.PERSON.value == "person"
        assert EntityType.GOVERNMENT.value == "government"

    def test_entity_type_all_values(self):
        """EntityType contains all expected types."""
        expected_types = {"organization", "person", "government", "fund", "spv"}
        actual_types = {t.value for t in EntityType}
        assert expected_types.issubset(actual_types)


class TestEntityStatus:
    """Test EntityStatus enum."""

    def test_entity_status_values(self):
        """EntityStatus has expected values."""
        assert EntityStatus.ACTIVE.value == "active"
        assert EntityStatus.INACTIVE.value == "inactive"
        assert EntityStatus.MERGED.value == "merged"

    def test_entity_status_all_values(self):
        """EntityStatus contains all expected statuses."""
        expected_statuses = {"active", "inactive", "merged", "provisional"}
        actual_statuses = {s.value for s in EntityStatus}
        assert expected_statuses.issubset(actual_statuses)


class TestEntityStringRepresentation:
    """Test Entity string representation."""

    def test_entity_repr(self):
        """Entity has meaningful repr."""
        entity = Entity(
            entity_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            primary_name="Apple Inc.",
        )
        repr_str = repr(entity)
        assert "Entity" in repr_str
        assert "Apple" in repr_str or "01ARZ" in repr_str


class TestEntityAliases:
    """Test Entity alias management."""

    def test_add_alias(self):
        """Entity.add_alias creates entity with new alias."""
        entity = Entity(
            entity_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            primary_name="Apple Inc.",
        )
        updated = entity.add_alias("Apple Computer")

        assert "Apple Computer" in updated.aliases

    def test_add_duplicate_alias_ignored(self):
        """Adding duplicate alias is a no-op."""
        entity = Entity(
            entity_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            primary_name="Apple Inc.",
            aliases=("Apple Computer",),  # Tuple for frozen dataclass
        )
        updated = entity.add_alias("Apple Computer")

        # Should return same object (no change)
        assert updated is entity
