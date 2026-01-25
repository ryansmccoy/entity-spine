"""
Filing Facts Ingestion Functions

This module provides the ingest functions that convert FilingFacts
contracts into EntitySpine domain objects and persist them.

All functions return domain dataclasses - no foreign types leak out.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from entityspine.domain.claim import IdentifierClaim
from entityspine.domain.entity import Entity
from entityspine.domain.enums import (
    ClaimStatus,
    EntityStatus,
    EntityType,
    EventStatus,
    EventType,
    IdentifierScheme,
    ListingStatus,
    RelationshipType,
    SecurityStatus,
    SecurityType,
    VendorNamespace,
)
from entityspine.domain.graph import Event, NodeKind, NodeRef, Relationship
from entityspine.domain.listing import Listing
from entityspine.domain.security import Security
from entityspine.domain.timestamps import utc_now

from .contracts import (
    ExtractedEntity,
    ExtractedEvent,
    ExtractedIdentifier,
    ExtractedRelationship,
    FilingEvidence,
    FilingFacts,
)
from .normalize import normalize_cik, normalize_ticker

if TYPE_CHECKING:
    from datetime import datetime

    from entityspine.stores.sqlite_store import SqliteStore


# =============================================================================
# Ingest Result
# =============================================================================


@dataclass
class IngestResult:
    """
    Result of a filing facts ingestion operation.

    Provides counts and references for audit/debugging.
    """

    # Filing reference
    accession_number: str
    form_type: str

    # Counts
    entities_created: int = 0
    entities_updated: int = 0
    claims_created: int = 0
    relationships_created: int = 0
    events_created: int = 0

    # Created entity IDs for reference
    registrant_entity_id: str | None = None
    created_entity_ids: list[str] = field(default_factory=list)

    # Warnings (tier honesty, validation issues)
    warnings: list[str] = field(default_factory=list)

    # Timestamp
    ingested_at: datetime = field(default_factory=utc_now)


# =============================================================================
# Entity Type Mapping
# =============================================================================

_ENTITY_TYPE_MAP = {
    "organization": EntityType.ORGANIZATION,
    "org": EntityType.ORGANIZATION,
    "company": EntityType.ORGANIZATION,
    "person": EntityType.PERSON,
    "individual": EntityType.PERSON,
    "fund": EntityType.FUND,
    "government": EntityType.GOVERNMENT,
    "exchange": EntityType.EXCHANGE,
    "unknown": EntityType.UNKNOWN,
}

_RELATIONSHIP_TYPE_MAP = {
    "supplier": RelationshipType.SUPPLIER,
    "supplies": RelationshipType.SUPPLIER,
    "customer": RelationshipType.CUSTOMER,
    "competitor": RelationshipType.COMPETITOR,
    "competes_with": RelationshipType.COMPETITOR,
    "subsidiary": RelationshipType.SUBSIDIARY,
    "parent": RelationshipType.PARENT,
    "partner": RelationshipType.PARTNER,
    "investor": RelationshipType.INVESTOR,
    "investee": RelationshipType.INVESTEE,
    "auditor": RelationshipType.AUDITOR,
    "counsel": RelationshipType.COUNSEL,
    "underwriter": RelationshipType.UNDERWRITER,
    "acquired": RelationshipType.ACQUIRED,
    "other": RelationshipType.OTHER,
}

_EVENT_TYPE_MAP = {
    "acquisition": EventType.MERGER_ACQUISITION,
    "merger": EventType.MERGER_ACQUISITION,
    "m&a": EventType.MERGER_ACQUISITION,
    "contract": EventType.LEGAL,  # Material contract events
    "governance": EventType.MANAGEMENT,
    "mgmt": EventType.MANAGEMENT,
    "management": EventType.MANAGEMENT,
    "security": EventType.CAPITAL,  # Security-related events
    "capital": EventType.CAPITAL,
    "restructure": EventType.RESTRUCTURING,
    "restructuring": EventType.RESTRUCTURING,
    "disclosure": EventType.OTHER,
    "legal": EventType.LEGAL,
    "regulatory": EventType.REGULATORY,
    "bankruptcy": EventType.BANKRUPTCY,
    "other": EventType.OTHER,
}

_IDENTIFIER_SCHEME_MAP = {
    "cik": IdentifierScheme.CIK,
    "ticker": IdentifierScheme.TICKER,
    "cusip": IdentifierScheme.CUSIP,
    "isin": IdentifierScheme.ISIN,
    "lei": IdentifierScheme.LEI,
    "figi": IdentifierScheme.FIGI,
    "sedol": IdentifierScheme.SEDOL,
    "ein": IdentifierScheme.EIN,
}


# =============================================================================
# Main Ingest Functions
# =============================================================================


def ingest_filing_facts(store: SqliteStore, facts: FilingFacts) -> IngestResult:
    """
    Ingest a complete FilingFacts document into EntitySpine.

    This is the primary entry point for py-sec-edgar/FeedSpine integration.

    Steps:
    1. Create/update registrant Entity
    2. Attach CIK identifier claim
    3. Create Security + Listing if ticker provided
    4. Create extracted entities
    5. Create relationships
    6. Create events

    Args:
        store: SqliteStore instance (initialized)
        facts: FilingFacts document from py-sec-edgar

    Returns:
        IngestResult with counts and warnings

    Example:
        >>> from entityspine.stores import SqliteStore
        >>> from entityspine.integration import FilingFacts, FilingEvidence, ingest_filing_facts
        >>>
        >>> store = SqliteStore(":memory:")
        >>> store.initialize()
        >>>
        >>> facts = FilingFacts(
        ...     evidence=FilingEvidence(
        ...         accession_number="0001045810-24-000029",
        ...         form_type="10-K",
        ...         filed_date=date(2024, 2, 21),
        ...         cik="0001045810",
        ...     ),
        ...     registrant_name="NVIDIA Corporation",
        ...     registrant_cik="0001045810",
        ...     registrant_ticker="NVDA",
        ... )
        >>>
        >>> result = ingest_filing_facts(store, facts)
        >>> print(f"Created {result.entities_created} entities")
    """
    result = IngestResult(
        accession_number=facts.evidence.accession_number,
        form_type=facts.evidence.form_type,
    )

    # Track entities by name for relationship linking
    entity_by_name: dict[str, str] = {}  # name -> entity_id

    # 1. Create/update registrant entity
    registrant_entity = _create_registrant_entity(facts)
    store.save_entity(registrant_entity)
    result.registrant_entity_id = registrant_entity.entity_id
    result.entities_created += 1
    entity_by_name[facts.registrant_name.lower()] = registrant_entity.entity_id
    result.created_entity_ids.append(registrant_entity.entity_id)

    # 2. Attach CIK identifier claim
    cik_claim = _create_cik_claim(registrant_entity, facts)
    store.save_claim(cik_claim)
    result.claims_created += 1

    # 3. Create Security + Listing if ticker provided
    if facts.registrant_ticker:
        security, listing = _create_security_and_listing(registrant_entity, facts)
        store.save_security(security)
        store.save_listing(listing)

        # Create TICKER claim
        ticker_claim = IdentifierClaim(
            scheme=IdentifierScheme.TICKER,
            value=normalize_ticker(facts.registrant_ticker),
            listing_id=listing.listing_id,
            namespace=VendorNamespace.SEC,
            source="sec-edgar",
            source_ref=facts.evidence.accession_number,
            confidence=1.0,
            status=ClaimStatus.ACTIVE,
        )
        store.save_claim(ticker_claim)
        result.claims_created += 1

    # 4. Create extracted entities
    for extracted in facts.entities:
        entity = _create_entity_from_extraction(extracted, facts)
        store.save_entity(entity)
        result.entities_created += 1
        entity_by_name[extracted.name.lower()] = entity.entity_id
        result.created_entity_ids.append(entity.entity_id)

    # 5. Create identifiers
    for extracted_id in facts.identifiers:
        entity_id = entity_by_name.get(extracted_id.entity_ref.lower())
        if entity_id:
            claim = _create_claim_from_extraction(extracted_id, entity_id, facts)
            if claim:
                store.save_claim(claim)
                result.claims_created += 1
        else:
            result.warnings.append(
                f"Could not find entity '{extracted_id.entity_ref}' for identifier"
            )

    # 6. Create relationships
    for extracted_rel in facts.relationships:
        source_id = entity_by_name.get(extracted_rel.source_name.lower())
        target_id = entity_by_name.get(extracted_rel.target_name.lower())

        if source_id and target_id:
            relationship = _create_relationship_from_extraction(
                extracted_rel, source_id, target_id, facts
            )
            store.save_relationship(relationship)
            result.relationships_created += 1
        else:
            missing = []
            if not source_id:
                missing.append(f"source '{extracted_rel.source_name}'")
            if not target_id:
                missing.append(f"target '{extracted_rel.target_name}'")
            result.warnings.append(f"Could not link relationship: missing {', '.join(missing)}")

    # 7. Create events
    for extracted_event in facts.events:
        event = _create_event_from_extraction(extracted_event, facts, entity_by_name)
        store.save_event(event)
        result.events_created += 1

    return result


def ingest_filing(
    store: SqliteStore,
    accession_number: str,
    form_type: str,
    filed_date,
    cik: str,
    company_name: str,
    ticker: str | None = None,
    exchange: str | None = None,
    sic_code: str | None = None,
    state_of_incorporation: str | None = None,
) -> IngestResult:
    """
    Simplified ingest for basic filing metadata.

    Use this when you just have filing header info and don't need
    full entity extraction. For richer data, use ingest_filing_facts().

    Args:
        store: SqliteStore instance
        accession_number: SEC accession number
        form_type: Form type (10-K, 10-Q, 8-K)
        filed_date: Filing date
        cik: Central Index Key
        company_name: Company name
        ticker: Stock ticker (optional)
        exchange: Exchange name (optional)
        sic_code: SIC code (optional)
        state_of_incorporation: State (optional)

    Returns:
        IngestResult
    """
    from datetime import date

    # Convert date if needed
    if isinstance(filed_date, str):
        filed_date = date.fromisoformat(filed_date)

    evidence = FilingEvidence(
        accession_number=accession_number,
        form_type=form_type,
        filed_date=filed_date,
        cik=cik,
    )

    facts = FilingFacts(
        evidence=evidence,
        registrant_name=company_name,
        registrant_cik=cik,
        registrant_ticker=ticker,
        registrant_exchange=exchange,
        registrant_sic=sic_code,
        registrant_state=state_of_incorporation,
    )

    return ingest_filing_facts(store, facts)


# =============================================================================
# Helper Functions
# =============================================================================


def _create_registrant_entity(facts: FilingFacts) -> Entity:
    """Create Entity for the filing registrant."""
    return Entity(
        primary_name=facts.registrant_name,
        entity_type=EntityType.ORGANIZATION,
        status=EntityStatus.ACTIVE,
        jurisdiction=facts.registrant_state,
        sic_code=facts.registrant_sic,
        source_system="sec-edgar",
        source_id=normalize_cik(facts.registrant_cik),
    )


def _create_cik_claim(entity: Entity, facts: FilingFacts) -> IdentifierClaim:
    """Create CIK identifier claim."""
    return IdentifierClaim(
        scheme=IdentifierScheme.CIK,
        value=normalize_cik(facts.registrant_cik),
        entity_id=entity.entity_id,
        namespace=VendorNamespace.SEC,
        source="sec-edgar",
        source_ref=facts.evidence.accession_number,
        confidence=1.0,
        status=ClaimStatus.ACTIVE,
    )


def _create_security_and_listing(entity: Entity, facts: FilingFacts) -> tuple[Security, Listing]:
    """Create Security and Listing for ticker."""
    security = Security(
        entity_id=entity.entity_id,
        security_type=SecurityType.COMMON_STOCK,
        status=SecurityStatus.ACTIVE,
        description=f"{facts.registrant_name} Common Stock",
        source_system="sec-edgar",
    )

    listing = Listing(
        security_id=security.security_id,
        ticker=normalize_ticker(facts.registrant_ticker),
        exchange=facts.registrant_exchange or "UNKNOWN",
        mic=None,  # Would need MIC mapping
        status=ListingStatus.ACTIVE,
        source_system="sec-edgar",
    )

    return security, listing


def _create_entity_from_extraction(extracted: ExtractedEntity, facts: FilingFacts) -> Entity:
    """Create Entity from extracted entity mention."""
    entity_type = _ENTITY_TYPE_MAP.get(extracted.entity_type.lower(), EntityType.UNKNOWN)

    return Entity(
        primary_name=extracted.name,
        entity_type=entity_type,
        status=EntityStatus.PROVISIONAL,  # Extracted entities are provisional
        source_system="sec-edgar",
        source_id=f"extracted:{facts.evidence.accession_number}",
    )


def _create_claim_from_extraction(
    extracted: ExtractedIdentifier,
    entity_id: str,
    facts: FilingFacts,
) -> IdentifierClaim | None:
    """Create IdentifierClaim from extracted identifier."""
    scheme = _IDENTIFIER_SCHEME_MAP.get(extracted.scheme.lower())
    if not scheme:
        return None

    return IdentifierClaim(
        scheme=scheme,
        value=extracted.value,
        entity_id=entity_id,
        namespace=VendorNamespace.SEC,
        source="sec-edgar",
        source_ref=facts.evidence.accession_number,
        confidence=extracted.confidence,
        status=ClaimStatus.ACTIVE,
    )


def _create_relationship_from_extraction(
    extracted: ExtractedRelationship,
    source_id: str,
    target_id: str,
    facts: FilingFacts,
) -> Relationship:
    """Create Relationship from extracted relationship."""
    rel_type = _RELATIONSHIP_TYPE_MAP.get(
        extracted.relationship_type.lower(), RelationshipType.OTHER
    )

    return Relationship(
        source_ref=NodeRef(NodeKind.ENTITY, source_id),
        target_ref=NodeRef(NodeKind.ENTITY, target_id),
        relationship_type=rel_type,
        confidence=extracted.confidence,
        evidence_filing_id=facts.evidence.accession_number,
        evidence_snippet=extracted.evidence_snippet,
        source_system="sec-edgar",
    )


def _create_event_from_extraction(
    extracted: ExtractedEvent,
    facts: FilingFacts,
    entity_by_name: dict[str, str],
) -> Event:
    """Create Event from extracted event."""
    event_type = _EVENT_TYPE_MAP.get(extracted.event_type.lower(), EventType.OTHER)

    # Build a title from available data
    title = extracted.description or f"{event_type.value} event"
    if extracted.item_number:
        title = f"8-K Item {extracted.item_number}: {title}"

    return Event(
        event_type=event_type,
        title=title,
        description=extracted.description,
        status=EventStatus.ANNOUNCED,
        occurred_on=extracted.event_date,
        announced_on=facts.evidence.filed_date,
        evidence_filing_id=facts.evidence.accession_number,
        evidence_section_id=extracted.item_number,
        confidence=extracted.confidence,
        source_system="sec-edgar",
    )
