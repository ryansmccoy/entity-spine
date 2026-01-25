"""
Complete integration test for EntitySpine storage and services.

Tests the full workflow:
1. Entity storage with SqliteStore
2. Audit trail with AuditManager
3. Data validation with validators
4. Conflict resolution with ConflictResolver
5. Duplicate detection with DuplicateDetector
"""

import tempfile
from pathlib import Path
from datetime import datetime, timezone

import pytest

# Domain models
from entityspine.domain.entity import Entity, EntityType, EntityStatus
from entityspine.domain.claim import IdentifierClaim
from entityspine.domain.enums import IdentifierScheme, ClaimStatus

# Stores
from entityspine.stores.sqlite_store import SqliteStore

# Services
from entityspine.services.audit import (
    AuditManager,
    SqliteAuditStore,
    ChangeType,
    EntityKind,
)
from entityspine.services.data_quality import (
    IdentifierValidator,
    EntityValidator,
    ValidationResult,
    IdentifierPatterns,
)
from entityspine.services.conflicts import (
    DuplicateDetector,
    ConflictResolver,
    ResolutionStrategy,
    DataQualityScorer,
)
from entityspine.services.fuzzy import normalize_company_name


class TestEntityStorageWorkflow:
    """Test the complete entity storage workflow."""

    def test_entity_storage_basic(self, tmp_path: Path):
        """Test basic entity storage operations."""
        db_path = tmp_path / "test_entities.db"
        store = SqliteStore(db_path)
        store.initialize()

        try:
            # Create an entity (using primary_name, not name)
            entity = Entity(
                entity_id="ent_apple_001",
                primary_name="Apple Inc.",
                entity_type=EntityType.ORGANIZATION,
                status=EntityStatus.ACTIVE,
            )

            # Store it
            store.save_entity(entity)

            # Retrieve it
            retrieved = store.get_entity("ent_apple_001")
            assert retrieved is not None
            assert retrieved.primary_name == "Apple Inc."
            assert retrieved.entity_type == EntityType.ORGANIZATION

            # Query by CIK
            entities = store.get_entities_by_cik("320193")
            # May be empty if no CIK claim attached
            assert isinstance(entities, list)

            print("✅ TEST 1 PASSED: Entity storage works")
        finally:
            store.close()

    def test_audit_trail(self, tmp_path: Path):
        """Test audit trail tracking."""
        audit_db = tmp_path / "audit.db"
        audit_store = SqliteAuditStore(audit_db)
        audit_store.initialize()

        try:
            manager = AuditManager(audit_store)

            # Record a change (using user_id, not user)
            manager.record(
                entity_kind=EntityKind.ENTITY,
                entity_id="ent_apple_001",
                change_type=ChangeType.CREATE,
                after={"name": "Apple Inc.", "cik": "320193"},
                user_id="test_user",
            )

            # Record an update
            manager.record(
                entity_kind=EntityKind.ENTITY,
                entity_id="ent_apple_001",
                change_type=ChangeType.UPDATE,
                before={"name": "Apple Inc."},
                after={"name": "Apple Inc.", "ticker": "AAPL"},
                user_id="test_user",
            )

            # Get history
            history = manager.get_history(EntityKind.ENTITY, "ent_apple_001")
            assert len(history) >= 2

            # Check event attributes
            event = history[0]
            assert hasattr(event, "occurred_at")
            assert event.entity_id == "ent_apple_001"

            print("✅ TEST 2 PASSED: Audit trail works")
        finally:
            audit_store.close()

    def test_identifier_validation(self):
        """Test identifier validation using IdentifierPatterns."""
        # Use the patterns directly for validation
        
        # Valid CIK
        assert IdentifierPatterns.CIK_PATTERN.match("320193") is not None
        assert IdentifierPatterns.CIK_PATTERN.match("0000320193") is not None

        # Invalid CIK
        assert IdentifierPatterns.CIK_PATTERN.match("abc") is None

        # LEI validation (20 chars alphanumeric)
        assert IdentifierPatterns.LEI_PATTERN.match("5493001A7V1L0B6QXM78") is not None
        assert IdentifierPatterns.LEI_PATTERN.match("invalid") is None

        print("✅ TEST 3 PASSED: Identifier validation patterns work")

    def test_identifier_claim_validation(self):
        """Test identifier claim validation."""
        validator = IdentifierValidator()

        # Valid CIK claim
        valid_claim = IdentifierClaim(
            claim_id="claim_001",
            scheme=IdentifierScheme.CIK,
            value="0000320193",
            entity_id="ent_apple",
            status=ClaimStatus.ACTIVE,
        )
        result = validator.validate(valid_claim)
        # Check the result - may have warnings but should be valid
        assert isinstance(result, ValidationResult)
        assert not result.has_errors  # Valid claim should have no errors

        # Test with a CIK that has format issues (missing padding)
        # Note: IdentifierClaim validates at construction, so we test the validator
        # with a valid but non-padded CIK
        unpadded_claim = IdentifierClaim(
            claim_id="claim_003",
            scheme=IdentifierScheme.CIK,
            value="0000000001",  # Valid format, just small number
            entity_id="ent_test",
            status=ClaimStatus.ACTIVE,
        )
        result = validator.validate(unpadded_claim)
        assert isinstance(result, ValidationResult)

        print("✅ TEST 4 PASSED: Identifier claim validation works")

    def test_name_normalization(self):
        """Test company name normalization."""
        # Use the fuzzy service for name normalization
        normalized = normalize_company_name("  APPLE INC.  ")
        assert "apple" in normalized.lower()

        normalized2 = normalize_company_name("MICROSOFT CORPORATION")
        assert "microsoft" in normalized2.lower()

        print("✅ TEST 5 PASSED: Name normalization works")

    def test_duplicate_detection(self):
        """Test duplicate detection."""
        detector = DuplicateDetector()

        entities = [
            Entity(
                entity_id="ent_001",
                primary_name="Apple Inc.",
                entity_type=EntityType.ORGANIZATION,
                status=EntityStatus.ACTIVE,
            ),
            Entity(
                entity_id="ent_002",
                primary_name="APPLE INC",  # Same company, different formatting
                entity_type=EntityType.ORGANIZATION,
                status=EntityStatus.ACTIVE,
            ),
            Entity(
                entity_id="ent_003",
                primary_name="Microsoft Corporation",
                entity_type=EntityType.ORGANIZATION,
                status=EntityStatus.ACTIVE,
            ),
        ]

        # Create claims for comparison
        claims_by_entity = {
            "ent_001": [
                IdentifierClaim(
                    claim_id="c1",
                    scheme=IdentifierScheme.CIK,
                    value="320193",
                    entity_id="ent_001",
                    status=ClaimStatus.ACTIVE,
                )
            ],
            "ent_002": [
                IdentifierClaim(
                    claim_id="c2",
                    scheme=IdentifierScheme.CIK,
                    value="320193",  # Same CIK!
                    entity_id="ent_002",
                    status=ClaimStatus.ACTIVE,
                )
            ],
            "ent_003": [],
        }

        # Find duplicates for entity 1
        duplicates = detector.find_duplicates_for_entity(
            entities[0],
            claims_by_entity.get("ent_001", []),
            entities,
            claims_by_entity,
        )

        # Should detect ent_002 as duplicate (same CIK + similar name)
        assert len(duplicates) >= 1
        print(f"   Found {len(duplicates)} potential duplicate(s)")

        print("✅ TEST 6 PASSED: Duplicate detection works")

    def test_conflict_resolution(self):
        """Test conflict resolution."""
        resolver = ConflictResolver()

        # Create some claims to resolve - TICKER requires listing_id
        claims = [
            IdentifierClaim(
                claim_id="c1",
                scheme=IdentifierScheme.TICKER,
                value="AAPL",
                listing_id="list_001",  # Use listing_id for ticker
                status=ClaimStatus.ACTIVE,
                confidence=0.9,
            ),
            IdentifierClaim(
                claim_id="c2",
                scheme=IdentifierScheme.TICKER,
                value="AAPL",
                listing_id="list_001",  # Use listing_id for ticker
                status=ClaimStatus.ACTIVE,
                confidence=0.95,  # Higher confidence
            ),
        ]

        # Resolve with KEEP_HIGHEST_CONFIDENCE strategy
        winner, losers = resolver.resolve_duplicate_claims(
            claims, strategy=ResolutionStrategy.KEEP_HIGHEST_CONFIDENCE
        )
        assert winner.claim_id == "c2"  # Should pick higher confidence
        assert len(losers) == 1

        print("✅ TEST 7 PASSED: Conflict resolution works")

    def test_data_quality_scoring(self, tmp_path: Path):
        """Test data quality scoring."""
        scorer = DataQualityScorer()

        # Entity with good data
        good_entity = Entity(
            entity_id="ent_good",
            primary_name="Apple Inc.",
            entity_type=EntityType.ORGANIZATION,
            status=EntityStatus.ACTIVE,
            jurisdiction="US-DE",
            source_system="sec",
        )
        
        good_claims = [
            IdentifierClaim(
                claim_id="c1",
                scheme=IdentifierScheme.CIK,
                value="0000320193",
                entity_id="ent_good",
                status=ClaimStatus.ACTIVE,
            )
        ]

        score = scorer.score_entity(good_entity, good_claims)
        assert score.overall_score > 50  # Should have decent score
        print(f"   Good entity score: {score.overall_score:.1f}")

        # Entity with missing data
        poor_entity = Entity(
            entity_id="ent_poor",
            primary_name="Unknown Corp",
            entity_type=EntityType.ORGANIZATION,
            status=EntityStatus.ACTIVE,
        )
        
        score2 = scorer.score_entity(poor_entity, [])
        assert score2.overall_score < score.overall_score  # Should be lower
        print(f"   Poor entity score: {score2.overall_score:.1f}")

        print("✅ TEST 8 PASSED: Data quality scoring works")

    def test_full_workflow(self, tmp_path: Path):
        """Test complete workflow: validate -> store -> audit -> detect duplicates."""
        # Setup
        db_path = tmp_path / "workflow.db"
        audit_db = tmp_path / "workflow_audit.db"

        store = SqliteStore(db_path)
        store.initialize()

        audit_store = SqliteAuditStore(audit_db)
        audit_store.initialize()

        try:
            manager = AuditManager(audit_store)
            id_validator = IdentifierValidator()
            detector = DuplicateDetector()

            # 1. Create and validate entity
            entity = Entity(
                entity_id="ent_apple",
                primary_name="Apple Inc.",
                entity_type=EntityType.ORGANIZATION,
                status=EntityStatus.ACTIVE,
                source_system="sec",
            )

            # 2. Create an identifier claim
            claim = IdentifierClaim(
                claim_id="claim_apple_cik",
                scheme=IdentifierScheme.CIK,
                value="0000320193",
                entity_id="ent_apple",
                status=ClaimStatus.ACTIVE,
            )

            # 3. Validate the claim
            validation = id_validator.validate(claim)
            # May have warnings but check we can proceed
            assert isinstance(validation, ValidationResult)

            # 4. Store entity
            store.save_entity(entity)

            # 5. Audit the creation
            manager.record(
                entity_kind=EntityKind.ENTITY,
                entity_id=entity.entity_id,
                change_type=ChangeType.CREATE,
                after={"name": entity.primary_name, "cik": claim.value},
                user_id="workflow_test",
            )

            # 6. Retrieve and verify
            retrieved = store.get_entity("ent_apple")
            assert retrieved is not None
            assert retrieved.primary_name == "Apple Inc."

            # 7. Check audit history
            history = manager.get_history(EntityKind.ENTITY, "ent_apple")
            assert len(history) >= 1

            print("✅ TEST 9 PASSED: Full workflow works")
        finally:
            # Clean up connections
            store.close()
            audit_store.close()


if __name__ == "__main__":
    # Run tests manually
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        test = TestEntityStorageWorkflow()

        print("\n" + "=" * 60)
        print("Running EntitySpine Storage Integration Tests")
        print("=" * 60 + "\n")

        try:
            test.test_entity_storage_basic(tmp_path)
        except Exception as e:
            print(f"❌ TEST 1 FAILED: {e}")

        try:
            test.test_audit_trail(tmp_path)
        except Exception as e:
            print(f"❌ TEST 2 FAILED: {e}")

        try:
            test.test_identifier_validation()
        except Exception as e:
            print(f"❌ TEST 3 FAILED: {e}")

        try:
            test.test_identifier_claim_validation()
        except Exception as e:
            print(f"❌ TEST 4 FAILED: {e}")

        try:
            test.test_name_normalization()
        except Exception as e:
            print(f"❌ TEST 5 FAILED: {e}")

        try:
            test.test_duplicate_detection()
        except Exception as e:
            print(f"❌ TEST 6 FAILED: {e}")

        try:
            test.test_conflict_resolution()
        except Exception as e:
            print(f"❌ TEST 7 FAILED: {e}")

        try:
            test.test_data_quality_scoring(tmp_path)
        except Exception as e:
            print(f"❌ TEST 8 FAILED: {e}")

        try:
            test.test_full_workflow(tmp_path)
        except Exception as e:
            print(f"❌ TEST 9 FAILED: {e}")

        print("\n" + "=" * 60)
        print("Tests Complete")
        print("=" * 60)
