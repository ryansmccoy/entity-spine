"""
Tests for the new audit trail models (v2.3.4).

Tests Provenance, MergeEvent, SplitEvent, Explanation, ResolutionRun,
SourceRecord, DataQualityRule, and DataQualityResult.
"""

import json
from datetime import datetime
from pathlib import Path

import pytest

from entityspine.domain import (
    DataQualityResult,
    DataQualityRule,
    Entity,
    Explanation,
    MergeEvent,
    Provenance,
    ResolutionRun,
    SourceRecord,
    SplitEvent,
)
from entityspine.domain.enums import (
    DataQualitySeverity,
    DecisionType,
    ProvenanceKind,
    RunStatus,
    VendorNamespace,
)


class TestProvenance:
    """Tests for Provenance dataclass."""

    def test_create_file_provenance(self):
        """Test creating a file-based provenance record."""
        prov = Provenance(
            kind=ProvenanceKind.FILE,
            namespace=VendorNamespace.SEC,
            source_uri="https://www.sec.gov/files/company_tickers.json",
            file_name="company_tickers.json",
        )
        
        assert prov.provenance_id is not None
        assert prov.kind == ProvenanceKind.FILE
        assert prov.namespace == VendorNamespace.SEC
        assert prov.file_name == "company_tickers.json"

    def test_create_api_provenance(self):
        """Test creating an API-based provenance record."""
        prov = Provenance(
            kind=ProvenanceKind.API,
            namespace=VendorNamespace.FACTSET,
            api_endpoint="/symbology/v1/identifier-resolution",
            api_params='{"ids": ["AAPL-US"]}',
        )
        
        assert prov.kind == ProvenanceKind.API
        assert prov.api_endpoint == "/symbology/v1/identifier-resolution"

    def test_provenance_is_frozen(self):
        """Test that Provenance is immutable."""
        prov = Provenance(kind=ProvenanceKind.FILE, namespace=VendorNamespace.SEC)
        
        with pytest.raises(AttributeError):
            prov.kind = ProvenanceKind.API


class TestMergeEvent:
    """Tests for MergeEvent dataclass."""

    def test_create_merge_event(self):
        """Test creating a merge event."""
        event = MergeEvent(
            source_entity_id="01HQ8AAAA",
            target_entity_id="01HQ8BBBB",
            reason="same_cik",
            confidence=1.0,
            merged_by="resolution_pipeline",
        )
        
        assert event.event_id is not None
        assert event.source_entity_id == "01HQ8AAAA"
        assert event.target_entity_id == "01HQ8BBBB"
        assert event.reason == "same_cik"
        assert event.reversible is True

    def test_merge_event_validates_different_ids(self):
        """Test that merge event requires different source and target."""
        with pytest.raises(ValueError, match="Cannot merge entity into itself"):
            MergeEvent(
                source_entity_id="01HQ8SAME",
                target_entity_id="01HQ8SAME",
                reason="test",
            )

    def test_merge_event_requires_source(self):
        """Test that merge event requires source_entity_id."""
        with pytest.raises(ValueError, match="source_entity_id is required"):
            MergeEvent(source_entity_id="", target_entity_id="01HQ8BBBB")


class TestSplitEvent:
    """Tests for SplitEvent dataclass."""

    def test_create_split_event(self):
        """Test creating a split event."""
        event = SplitEvent(
            source_entity_id="01HQ8PARENT",
            target_entity_ids=("01HQ8CHILD1", "01HQ8CHILD2"),
            reason="spinoff",
        )
        
        assert event.event_id is not None
        assert event.source_entity_id == "01HQ8PARENT"
        assert len(event.target_entity_ids) == 2

    def test_split_event_converts_list_to_tuple(self):
        """Test that list target_entity_ids is converted to tuple."""
        event = SplitEvent(
            source_entity_id="01HQ8PARENT",
            target_entity_ids=["01HQ8CHILD1", "01HQ8CHILD2"],
            reason="spinoff",
        )
        
        assert isinstance(event.target_entity_ids, tuple)


class TestExplanation:
    """Tests for Explanation dataclass."""

    def test_create_explanation(self):
        """Test creating an explanation record."""
        exp = Explanation(
            decision_type=DecisionType.MATCH,
            summary="Matched on CIK with exact name",
            details="CIK 0000320193 matches exactly.",
            factors={"cik_match": True, "name_score": 1.0},
            confidence=1.0,
        )
        
        assert exp.explanation_id is not None
        assert exp.decision_type == DecisionType.MATCH
        assert exp.factors["cik_match"] is True

    def test_explanation_accepts_string_for_backwards_compat(self):
        """Test that Explanation accepts string decision_type for backwards compatibility."""
        exp = Explanation(decision_type="match", summary="Test")
        assert exp.decision_type == "match"


class TestResolutionRun:
    """Tests for ResolutionRun dataclass."""

    def test_create_resolution_run(self):
        """Test creating a resolution run."""
        run = ResolutionRun(
            input_params={"blocking_keys": ["cik", "name_prefix"]},
            source_record_ids=("rec1", "rec2", "rec3"),
        )
        
        assert run.run_id is not None
        assert run.status == RunStatus.RUNNING
        assert len(run.source_record_ids) == 3

    def test_resolution_run_is_complete(self):
        """Test is_complete property."""
        run = ResolutionRun(status=RunStatus.RUNNING)
        assert not run.is_complete
        
        completed_run = ResolutionRun(status=RunStatus.COMPLETED)
        assert completed_run.is_complete

    def test_resolution_run_is_successful(self):
        """Test is_successful property."""
        run = ResolutionRun(status=RunStatus.FAILED)
        assert not run.is_successful
        
        success_run = ResolutionRun(status=RunStatus.COMPLETED)
        assert success_run.is_successful


class TestSourceRecord:
    """Tests for SourceRecord dataclass."""

    def test_create_source_record(self):
        """Test creating a source record."""
        record = SourceRecord(
            provenance_id="01HQ8PROV",
            raw_data='{"cik": "320193", "ticker": "AAPL"}',
            record_type="entity",
            source_key="0000320193",
        )
        
        assert record.record_id is not None
        assert record.processed is False
        assert record.is_processed is False

    def test_source_record_has_error(self):
        """Test has_error property."""
        ok_record = SourceRecord(raw_data="{}")
        assert not ok_record.has_error
        
        err_record = SourceRecord(raw_data="{}", error_message="Parse failed")
        assert err_record.has_error


class TestDataQualityRule:
    """Tests for DataQualityRule dataclass."""

    def test_create_quality_rule(self):
        """Test creating a data quality rule."""
        rule = DataQualityRule(
            name="cik_unique_name",
            description="Each CIK should have exactly one primary name",
            category="consistency",
            severity=DataQualitySeverity.WARNING,
            target_type="entity",
        )
        
        assert rule.rule_id is not None
        assert rule.name == "cik_unique_name"
        assert rule.enabled is True


class TestDataQualityResult:
    """Tests for DataQualityResult dataclass."""

    def test_create_quality_result(self):
        """Test creating a data quality result."""
        result = DataQualityResult(
            rule_id="01HQ8RULE",
            rule_name="cik_unique_name",
            passed=True,
            message="CIK 0000320193 has exactly one name",
            entity_id="01HQ8ENT",
        )
        
        assert result.result_id is not None
        assert result.passed is True
        assert not result.is_failure

    def test_quality_result_needs_attention(self):
        """Test needs_attention property."""
        passing = DataQualityResult(
            rule_id="rule1",
            passed=True,
        )
        assert not passing.needs_attention
        
        failing = DataQualityResult(
            rule_id="rule1",
            passed=False,
            severity=DataQualitySeverity.WARNING,
        )
        assert failing.needs_attention
        
        resolved = DataQualityResult(
            rule_id="rule1",
            passed=False,
            severity=DataQualitySeverity.WARNING,
            resolved=True,
        )
        assert not resolved.needs_attention


class TestEntityMergeIntoWithEvent:
    """Tests for Entity.merge_into_with_event method."""

    def test_merge_into_with_event(self):
        """Test that merge_into_with_event creates both entity and event."""
        entity = Entity(primary_name="APPLE INC")
        target_id = "01HQ8TARGET"
        
        merged, event = entity.merge_into_with_event(
            target_id,
            reason="same_cik",
            confidence=1.0,
            merged_by="test",
        )
        
        # Check merged entity
        assert merged.redirect_to == target_id
        assert merged.status.value == "merged"
        
        # Check event
        assert event.source_entity_id == entity.entity_id
        assert event.target_entity_id == target_id
        assert event.reason == "same_cik"
        assert event.confidence == 1.0
        assert event.merged_by == "test"
        
        # Check snapshot was created
        assert event.source_snapshot is not None
        snapshot = json.loads(event.source_snapshot)
        assert snapshot["primary_name"] == "APPLE INC"

    def test_original_merge_into_still_works(self):
        """Test that original merge_into method still works."""
        entity = Entity(primary_name="Test Corp")
        merged = entity.merge_into("target_id", "test_reason")
        
        assert merged.redirect_to == "target_id"
        assert merged.redirect_reason == "test_reason"


class TestFactoryFunctions:
    """Tests for audit trail factory functions."""

    def test_create_file_provenance(self):
        """Test create_file_provenance factory."""
        from entityspine.domain import create_file_provenance
        
        prov = create_file_provenance(
            VendorNamespace.SEC,
            "https://www.sec.gov/files/company_tickers.json",
            file_name="company_tickers.json",
        )
        
        assert prov.kind == ProvenanceKind.FILE
        assert prov.namespace == VendorNamespace.SEC
        assert prov.file_name == "company_tickers.json"

    def test_create_api_provenance(self):
        """Test create_api_provenance factory."""
        from entityspine.domain import create_api_provenance
        
        prov = create_api_provenance(
            VendorNamespace.FACTSET,
            "/symbology/v1/identifier-resolution",
            api_params='{"ids": ["AAPL-US"]}',
        )
        
        assert prov.kind == ProvenanceKind.API
        assert prov.namespace == VendorNamespace.FACTSET
        assert prov.api_endpoint == "/symbology/v1/identifier-resolution"

    def test_create_merge_event(self):
        """Test create_merge_event factory."""
        from entityspine.domain import create_merge_event
        
        event = create_merge_event(
            "01HQ8AAA",
            "01HQ8BBB",
            "same_cik",
            confidence=0.95,
            merged_by="test_pipeline",
        )
        
        assert event.source_entity_id == "01HQ8AAA"
        assert event.target_entity_id == "01HQ8BBB"
        assert event.reason == "same_cik"
        assert event.confidence == 0.95

    def test_create_explanation(self):
        """Test create_explanation factory."""
        from entityspine.domain import create_explanation
        
        exp = create_explanation(
            "match",
            "Matched on CIK",
            factors={"cik_match": True},
            confidence=1.0,
        )
        
        assert exp.summary == "Matched on CIK"
        assert exp.factors["cik_match"] is True

    def test_create_resolution_run(self):
        """Test create_resolution_run factory."""
        from entityspine.domain import create_resolution_run
        
        run = create_resolution_run(
            {"blocking_keys": ["cik"]},
            ["rec1", "rec2"],
        )
        
        assert run.status == RunStatus.RUNNING
        assert "cik" in run.input_params["blocking_keys"]
        assert len(run.source_record_ids) == 2

    def test_create_quality_rule(self):
        """Test create_quality_rule factory."""
        from entityspine.domain import create_quality_rule
        
        rule = create_quality_rule(
            "unique_cik",
            "Each CIK should be unique",
            severity=DataQualitySeverity.ERROR,
        )
        
        assert rule.name == "unique_cik"
        assert rule.severity == DataQualitySeverity.ERROR

    def test_create_quality_result(self):
        """Test create_quality_result factory."""
        from entityspine.domain import create_quality_result
        
        result = create_quality_result(
            "rule123",
            "unique_cik",
            passed=True,
            entity_id="ent123",
        )
        
        assert result.passed is True
        assert result.entity_id == "ent123"
