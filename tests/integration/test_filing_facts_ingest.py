"""
Tests for EntitySpine integration module.

Tests the FilingFacts contract and ingest functions.
"""

from datetime import date

import pytest

from entityspine.integration import (
    FilingEvidence,
    FilingFacts,
    ingest_filing,
    ingest_filing_facts,
    normalize_cik,
    normalize_ticker,
)
from entityspine.integration.contracts import (
    ExtractedEntity,
    ExtractedEvent,
    ExtractedRelationship,
)
from entityspine.stores import SqliteStore


class TestNormalize:
    """Tests for normalization functions."""

    def test_normalize_cik_pads_to_10_digits(self):
        assert normalize_cik("320193") == "0000320193"
        assert normalize_cik("0000320193") == "0000320193"
        assert normalize_cik("1045810") == "0001045810"

    def test_normalize_cik_handles_whitespace(self):
        assert normalize_cik("  320193  ") == "0000320193"

    def test_normalize_cik_rejects_non_digits(self):
        with pytest.raises(ValueError):
            normalize_cik("abc123")

    def test_normalize_ticker_uppercases(self):
        assert normalize_ticker("aapl") == "AAPL"
        assert normalize_ticker("MSFT") == "MSFT"

    def test_normalize_ticker_handles_dots(self):
        assert normalize_ticker("brk.b") == "BRK.B"
        assert normalize_ticker("BRK.A") == "BRK.A"

    def test_normalize_ticker_strips_whitespace(self):
        assert normalize_ticker("  NVDA  ") == "NVDA"


class TestFilingEvidence:
    """Tests for FilingEvidence contract."""

    def test_filing_evidence_creation(self):
        evidence = FilingEvidence(
            accession_number="0001045810-24-000029",
            form_type="10-K",
            filed_date=date(2024, 2, 21),
            cik="0001045810",
        )
        assert evidence.accession_number == "0001045810-24-000029"
        assert evidence.form_type == "10-K"
        assert evidence.filed_date == date(2024, 2, 21)

    def test_filing_id_property(self):
        evidence = FilingEvidence(
            accession_number="0001045810-24-000029",
            form_type="10-K",
            filed_date=date(2024, 2, 21),
            cik="0001045810",
        )
        assert evidence.filing_id == "000104581024000029"


class TestFilingFacts:
    """Tests for FilingFacts contract."""

    def test_filing_facts_basic_creation(self):
        facts = FilingFacts(
            evidence=FilingEvidence(
                accession_number="0001045810-24-000029",
                form_type="10-K",
                filed_date=date(2024, 2, 21),
                cik="0001045810",
            ),
            registrant_name="NVIDIA Corporation",
            registrant_cik="1045810",
        )
        assert facts.registrant_name == "NVIDIA Corporation"
        # CIK should be normalized to 10 digits
        assert facts.registrant_cik == "0001045810"

    def test_filing_facts_with_ticker(self):
        facts = FilingFacts(
            evidence=FilingEvidence(
                accession_number="0001045810-24-000029",
                form_type="10-K",
                filed_date=date(2024, 2, 21),
                cik="0001045810",
            ),
            registrant_name="NVIDIA Corporation",
            registrant_cik="1045810",
            registrant_ticker="NVDA",
            registrant_exchange="NASDAQ",
        )
        assert facts.registrant_ticker == "NVDA"
        assert facts.registrant_exchange == "NASDAQ"


class TestIngestFilingFacts:
    """Tests for ingest_filing_facts function."""

    @pytest.fixture
    def store(self):
        """Create initialized in-memory store."""
        store = SqliteStore(":memory:")
        store.initialize()
        return store

    def test_ingest_basic_filing(self, store):
        """Test basic filing ingest creates registrant entity."""
        facts = FilingFacts(
            evidence=FilingEvidence(
                accession_number="0001045810-24-000029",
                form_type="10-K",
                filed_date=date(2024, 2, 21),
                cik="0001045810",
            ),
            registrant_name="NVIDIA Corporation",
            registrant_cik="1045810",
        )

        result = ingest_filing_facts(store, facts)

        assert result.entities_created == 1
        assert result.claims_created == 1  # CIK claim
        assert result.registrant_entity_id is not None

        # Verify entity in store
        entity = store.get_entity(result.registrant_entity_id)
        assert entity is not None
        assert entity.primary_name == "NVIDIA Corporation"

    def test_ingest_with_ticker_creates_security_and_listing(self, store):
        """Test filing with ticker creates Security and Listing."""
        facts = FilingFacts(
            evidence=FilingEvidence(
                accession_number="0001045810-24-000029",
                form_type="10-K",
                filed_date=date(2024, 2, 21),
                cik="0001045810",
            ),
            registrant_name="NVIDIA Corporation",
            registrant_cik="1045810",
            registrant_ticker="NVDA",
        )

        result = ingest_filing_facts(store, facts)

        # CIK claim + TICKER claim
        assert result.claims_created == 2

    def test_ingest_with_extracted_entities(self, store):
        """Test filing with extracted entity mentions."""
        facts = FilingFacts(
            evidence=FilingEvidence(
                accession_number="0001045810-24-000029",
                form_type="10-K",
                filed_date=date(2024, 2, 21),
                cik="0001045810",
            ),
            registrant_name="NVIDIA Corporation",
            registrant_cik="1045810",
            entities=[
                ExtractedEntity(
                    name="Taiwan Semiconductor",
                    entity_type="organization",
                    confidence=0.95,
                ),
                ExtractedEntity(
                    name="Microsoft Corporation",
                    entity_type="organization",
                    confidence=0.90,
                ),
            ],
        )

        result = ingest_filing_facts(store, facts)

        # 1 registrant + 2 extracted entities
        assert result.entities_created == 3

    def test_ingest_with_relationships(self, store):
        """Test filing with extracted relationships."""
        facts = FilingFacts(
            evidence=FilingEvidence(
                accession_number="0001045810-24-000029",
                form_type="10-K",
                filed_date=date(2024, 2, 21),
                cik="0001045810",
            ),
            registrant_name="NVIDIA Corporation",
            registrant_cik="1045810",
            entities=[
                ExtractedEntity(
                    name="Taiwan Semiconductor",
                    entity_type="organization",
                ),
            ],
            relationships=[
                ExtractedRelationship(
                    source_name="NVIDIA Corporation",
                    target_name="Taiwan Semiconductor",
                    relationship_type="SUPPLIER",
                    evidence_snippet="TSMC manufactures all of our GPUs",
                    confidence=0.95,
                ),
            ],
        )

        result = ingest_filing_facts(store, facts)

        assert result.relationships_created == 1

    def test_ingest_relationship_warns_on_missing_entity(self, store):
        """Test relationship with unknown entity produces warning."""
        facts = FilingFacts(
            evidence=FilingEvidence(
                accession_number="0001045810-24-000029",
                form_type="10-K",
                filed_date=date(2024, 2, 21),
                cik="0001045810",
            ),
            registrant_name="NVIDIA Corporation",
            registrant_cik="1045810",
            relationships=[
                ExtractedRelationship(
                    source_name="NVIDIA Corporation",
                    target_name="Unknown Company",  # Not in entities list
                    relationship_type="SUPPLIER",
                ),
            ],
        )

        result = ingest_filing_facts(store, facts)

        assert result.relationships_created == 0
        assert len(result.warnings) > 0
        assert "Unknown Company" in result.warnings[0]

    def test_ingest_with_events(self, store):
        """Test filing with extracted events."""
        facts = FilingFacts(
            evidence=FilingEvidence(
                accession_number="0001045810-24-000029",
                form_type="8-K",
                filed_date=date(2024, 2, 21),
                cik="0001045810",
            ),
            registrant_name="NVIDIA Corporation",
            registrant_cik="1045810",
            events=[
                ExtractedEvent(
                    event_type="acquisition",
                    description="Acquisition of AI startup",
                    item_number="2.01",
                    event_date=date(2024, 2, 15),
                ),
            ],
        )

        result = ingest_filing_facts(store, facts)

        assert result.events_created == 1


class TestIngestFiling:
    """Tests for simplified ingest_filing function."""

    @pytest.fixture
    def store(self):
        """Create initialized in-memory store."""
        store = SqliteStore(":memory:")
        store.initialize()
        return store

    def test_ingest_filing_simple(self, store):
        """Test simplified filing ingest."""
        result = ingest_filing(
            store=store,
            accession_number="0000320193-23-000077",
            form_type="10-K",
            filed_date="2023-11-03",
            cik="320193",
            company_name="Apple Inc.",
            ticker="AAPL",
        )

        assert result.entities_created == 1
        assert result.claims_created == 2  # CIK + TICKER

        # Verify via search
        search_results = store.search_entities("AAPL")
        assert len(search_results) > 0
        entity, _score = search_results[0]
        assert entity.primary_name == "Apple Inc."


class TestIntegrationRoundTrip:
    """End-to-end integration tests."""

    @pytest.fixture
    def store(self):
        """Create initialized in-memory store."""
        store = SqliteStore(":memory:")
        store.initialize()
        return store

    def test_full_10k_ingest_and_resolve(self, store):
        """Test full 10-K ingest with resolution."""
        # Simulate what py-sec-edgar would produce
        facts = FilingFacts(
            evidence=FilingEvidence(
                accession_number="0001045810-24-000029",
                form_type="10-K",
                filed_date=date(2024, 2, 21),
                cik="0001045810",
            ),
            registrant_name="NVIDIA Corporation",
            registrant_cik="0001045810",
            registrant_ticker="NVDA",
            registrant_exchange="NASDAQ",
            registrant_sic="3674",
            registrant_state="DE",
            entities=[
                ExtractedEntity(
                    name="Taiwan Semiconductor Manufacturing Company",
                    entity_type="organization",
                ),
                ExtractedEntity(
                    name="Jensen Huang",
                    entity_type="person",
                ),
            ],
            relationships=[
                ExtractedRelationship(
                    source_name="NVIDIA Corporation",
                    target_name="Taiwan Semiconductor Manufacturing Company",
                    relationship_type="SUPPLIER",
                    evidence_snippet="TSMC manufactures substantially all of our GPUs",
                ),
            ],
        )

        # Ingest
        result = ingest_filing_facts(store, facts)

        # Verify counts
        assert result.entities_created == 3  # NVIDIA + TSMC + Jensen
        assert result.claims_created == 2  # CIK + TICKER
        assert result.relationships_created == 1

        # Search by ticker
        search_results = store.search_entities("NVDA")
        assert len(search_results) > 0
        entity, _score = search_results[0]
        assert entity.primary_name == "NVIDIA Corporation"
        assert entity.sic_code == "3674"

        # Search by CIK
        entities = store.get_entities_by_cik("0001045810")
        assert len(entities) > 0
        assert entities[0].primary_name == "NVIDIA Corporation"
