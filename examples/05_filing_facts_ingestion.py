"""
05_filing_facts_ingestion.py

Ingest SEC filings using the integration module.

This example demonstrates:
- Using the FilingFacts contract
- Automatic entity creation from filing data
- Relationship extraction and storage
"""

from __future__ import annotations

from datetime import date

from entityspine import SqliteStore
from entityspine.integration import (
    FilingEvidence,
    FilingFacts,
    ingest_filing_facts,
)
from entityspine.integration.contracts import (
    ExtractedEntity,
    ExtractedEvent,
    ExtractedIdentifier,
    ExtractedRelationship,
)


def main() -> None:
    """Ingest NVIDIA 10-K filing facts."""
    store = SqliteStore(":memory:")
    store.initialize()

    print("=" * 60)
    print("FILING FACTS INGESTION EXAMPLE")
    print("=" * 60)

    # ========================================
    # BUILD FILING FACTS
    # ========================================
    # In production, this would come from py-sec-edgar parsing

    facts = FilingFacts(
        # Filing metadata
        evidence=FilingEvidence(
            accession_number="0001045810-24-000029",
            form_type="10-K",
            filed_date=date(2024, 2, 21),
            cik="0001045810",
        ),
        # Registrant info (from header)
        registrant_name="NVIDIA Corporation",
        registrant_cik="0001045810",
        registrant_ticker="NVDA",
        registrant_exchange="NASDAQ",
        registrant_sic="3674",
        registrant_state="DE",
        # Extracted entities
        entities=[
            ExtractedEntity(
                name="Jensen Huang",
                entity_type="person",
                role="President and CEO",
            ),
            ExtractedEntity(
                name="Colette Kress",
                entity_type="person",
                role="EVP and CFO",
            ),
            ExtractedEntity(
                name="Taiwan Semiconductor Manufacturing Company",
                entity_type="organization",
            ),
            ExtractedEntity(
                name="Microsoft Corporation",
                entity_type="organization",
            ),
            ExtractedEntity(
                name="Advanced Micro Devices, Inc.",
                entity_type="organization",
            ),
        ],
        # Extracted identifiers
        identifiers=[
            ExtractedIdentifier(
                scheme="lei",
                value="549300S4KLBER65TJQ35",
            ),
            ExtractedIdentifier(
                scheme="cusip",
                value="67066G104",
            ),
        ],
        # Extracted relationships
        relationships=[
            ExtractedRelationship(
                source_name="NVIDIA Corporation",
                target_name="Taiwan Semiconductor Manufacturing Company",
                relationship_type="SUPPLIER",
                evidence_snippet="TSMC manufactures substantially all of our GPUs",
                confidence=0.95,
            ),
            ExtractedRelationship(
                source_name="NVIDIA Corporation",
                target_name="Microsoft Corporation",
                relationship_type="CUSTOMER",
                evidence_snippet="Microsoft Azure is a significant customer",
                confidence=0.90,
            ),
            ExtractedRelationship(
                source_name="NVIDIA Corporation",
                target_name="Advanced Micro Devices, Inc.",
                relationship_type="COMPETITOR",
                evidence_snippet="We compete with AMD in GPU markets",
                confidence=0.95,
            ),
        ],
        # Extracted events
        events=[
            ExtractedEvent(
                title="Fiscal Year 2024 Results",
                event_type="earnings",
                event_date=date(2024, 1, 28),
                description="Record revenue of $60.9 billion, up 126% from prior year",
            ),
            ExtractedEvent(
                title="Stock Split",
                event_type="corporate_action",
                event_date=date(2024, 6, 7),
                description="10-for-1 forward stock split",
            ),
        ],
    )

    print(f"\nFiling: {facts.evidence.form_type} ({facts.evidence.accession_number})")
    print(f"Registrant: {facts.registrant_name} ({facts.registrant_ticker})")
    print(f"Entities extracted: {len(facts.entities or [])}")
    print(f"Identifiers extracted: {len(facts.identifiers or [])}")
    print(f"Relationships extracted: {len(facts.relationships or [])}")
    print(f"Events extracted: {len(facts.events or [])}")

    # ========================================
    # INGEST INTO ENTITYSPINE
    # ========================================
    print("\n" + "-" * 40)
    print("INGESTING...")
    print("-" * 40)

    result = ingest_filing_facts(store, facts)

    print(f"\nIngestion Results:")
    print(f"  Entities created: {result.entities_created}")
    print(f"  Claims created: {result.claims_created}")
    print(f"  Relationships created: {result.relationships_created}")
    print(f"  Events created: {result.events_created}")

    if result.warnings:
        print(f"\nWarnings:")
        for warning in result.warnings:
            print(f"  ⚠️ {warning}")

    if result.errors:
        print(f"\nErrors:")
        for error in result.errors:
            print(f"  ❌ {error}")

    # ========================================
    # VERIFY RESULTS
    # ========================================
    print("\n" + "=" * 60)
    print("VERIFICATION")
    print("=" * 60)

    # Search for the registrant
    print(f"\nSearching for '{facts.registrant_ticker}':")
    results = store.search_entities(facts.registrant_ticker, limit=1)
    if results:
        entity, score = results[0]
        print(f"  Found: {entity.primary_name} (score: {score:.2f})")

        # Get claims
        claims = store.get_claims_for_entity(entity.entity_id)
        print(f"  Identifier claims: {len(claims)}")
        for claim in claims:
            print(f"    {claim.scheme.value}: {claim.value}")

        # Get relationships
        rels = store.get_relationships_for_entity(entity.entity_id)
        print(f"  Relationships: {len(rels)}")
        for rel in rels:
            target = store.get_entity(rel.target_ref.id)
            target_name = target.primary_name if target else "Unknown"
            print(f"    {rel.relationship_type.value} → {target_name}")

    # ========================================
    # STATISTICS
    # ========================================
    print("\n" + "=" * 60)
    print("FINAL STATISTICS")
    print("=" * 60)
    print(f"Total Entities: {store.entity_count()}")
    print(f"Total Claims: {store.claim_count()}")
    print(f"Total Relationships: {store.relationship_count()}")
    print(f"Total Events: {store.event_count()}")


if __name__ == "__main__":
    main()
