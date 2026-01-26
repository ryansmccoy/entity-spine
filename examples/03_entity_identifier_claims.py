"""
03_entity_identifier_claims.py

Demonstrate identifier claims with provenance tracking.

This example shows how to:
- Create entities with multiple identifier schemes
- Track provenance (source, confidence, evidence)
- Query by different identifiers
"""

from __future__ import annotations

from datetime import date

from entityspine import (
    Entity,
    EntityStatus,
    EntityType,
    SqliteStore,
)
from entityspine.domain.claim import (
    ClaimStatus,
    IdentifierClaim,
    IdentifierScheme,
    VendorNamespace,
)


def main() -> None:
    """Main example function."""
    # Create store
    store = SqliteStore(":memory:")
    store.initialize()

    print("=" * 60)
    print("IDENTIFIER CLAIMS EXAMPLE")
    print("=" * 60)

    # Create Apple entity
    apple = Entity(
        primary_name="Apple Inc.",
        entity_type=EntityType.ORGANIZATION,
        status=EntityStatus.ACTIVE,
        jurisdiction="CA",
        sic_code="3571",
        source_system="sec-edgar",
        source_id="0000320193",
    )
    store.save_entity(apple)
    print(f"\nCreated entity: {apple.primary_name}")
    print(f"  Entity ID: {apple.entity_id}")

    # Add CIK claim from SEC
    cik_claim = IdentifierClaim(
        entity_id=apple.entity_id,
        scheme=IdentifierScheme.CIK,
        value="0000320193",
        namespace=VendorNamespace.SEC,
        source="sec-edgar",
        source_ref="0000320193-24-000123",  # Accession number
        confidence=1.0,
        status=ClaimStatus.ACTIVE,
        effective_date=date(1980, 12, 12),  # Apple's IPO
    )
    store.save_claim(cik_claim)
    print(f"\nAdded CIK claim: {cik_claim.value}")

    # Add LEI claim from GLEIF
    lei_claim = IdentifierClaim(
        entity_id=apple.entity_id,
        scheme=IdentifierScheme.LEI,
        value="HWUPKR0MPOU8FGXBT394",
        namespace=VendorNamespace.GLEIF,
        source="gleif-api",
        confidence=1.0,
        status=ClaimStatus.ACTIVE,
    )
    store.save_claim(lei_claim)
    print(f"Added LEI claim: {lei_claim.value}")

    # Add EIN claim from IRS
    ein_claim = IdentifierClaim(
        entity_id=apple.entity_id,
        scheme=IdentifierScheme.EIN,
        value="94-2404110",
        namespace=VendorNamespace.IRS,
        source="10-k-filing",
        source_ref="0000320193-23-000077",
        confidence=1.0,
        status=ClaimStatus.ACTIVE,
    )
    store.save_claim(ein_claim)
    print(f"Added EIN claim: {ein_claim.value}")

    # Query claims for entity
    print("\n" + "-" * 40)
    print("CLAIMS FOR APPLE")
    print("-" * 40)

    claims = store.get_claims_for_entity(apple.entity_id)
    for claim in claims:
        print(f"  {claim.scheme.value}: {claim.value}")
        print(f"    Source: {claim.source} ({claim.namespace.value})")
        print(f"    Confidence: {claim.confidence:.0%}")
        if claim.source_ref:
            print(f"    Reference: {claim.source_ref}")
        print()

    # Create another entity with overlapping ticker
    print("=" * 60)
    print("HISTORICAL IDENTIFIER EXAMPLE")
    print("=" * 60)

    # Create historical AT&T (before name change)
    att_old = Entity(
        primary_name="AT&T Inc.",
        entity_type=EntityType.ORGANIZATION,
        status=EntityStatus.MERGED,
        source_system="sec-edgar",
        source_id="0000732717",
    )
    store.save_entity(att_old)

    # Add historical ticker claim (superseded)
    ticker_old = IdentifierClaim(
        entity_id=att_old.entity_id,
        scheme=IdentifierScheme.TICKER,
        value="T",
        namespace=VendorNamespace.NYSE,
        source="nyse-listings",
        confidence=1.0,
        status=ClaimStatus.SUPERSEDED,
        effective_date=date(2005, 11, 18),
        expiry_date=date(2022, 4, 8),  # When T split
    )
    store.save_claim(ticker_old)

    print(f"\nCreated historical entity: {att_old.primary_name}")
    print(f"  Ticker T was active: {ticker_old.effective_date} to {ticker_old.expiry_date}")

    # Statistics
    print("\n" + "=" * 60)
    print("FINAL STATISTICS")
    print("=" * 60)
    print(f"Entities: {store.entity_count()}")
    print(f"Claims: {store.claim_count()}")


if __name__ == "__main__":
    main()
