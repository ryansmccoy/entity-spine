"""
Integration Contracts

Pure stdlib dataclasses that define the interface between external systems
and EntitySpine. These contracts:

1. Are stdlib @dataclass (no pydantic, no dependencies)
2. Define what external systems provide
3. Map cleanly to EntitySpine domain models

By defining these contracts in EntitySpine, we ensure:
- External systems know exactly what to provide
- EntitySpine controls the canonical structure
- No field drift between systems
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import date, datetime


@dataclass
class FilingEvidence:
    """
    Evidence linking a fact to its source filing.

    This is attached to every entity, claim, relationship, or event
    extracted from a filing to provide provenance.

    Fields:
        accession_number: SEC accession number (e.g., "0001045810-24-000029")
        form_type: SEC form type (10-K, 10-Q, 8-K, etc.)
        filed_date: When the filing was made with SEC
        cik: Central Index Key of the filer
        section_id: Optional section within filing (Item 1, Risk Factors)
        excerpt_snippet: Optional first 200 chars of evidence text
        source_url: Optional URL to the source document
    """

    accession_number: str
    form_type: str
    filed_date: date
    cik: str
    section_id: str | None = None
    excerpt_snippet: str | None = None
    source_url: str | None = None

    @property
    def filing_id(self) -> str:
        """Return accession number as filing ID."""
        return self.accession_number.replace("-", "")


@dataclass
class ExtractedEntity:
    """
    An entity reference extracted from a filing.

    These get converted to EntitySpine Entity domain objects.

    Fields:
        name: Entity name as found in filing
        entity_type: One of: organization, person, product, brand
        mention_context: Optional text surrounding the mention
        confidence: Extraction confidence 0.0-1.0
        metadata: Additional key-value pairs
    """

    name: str
    entity_type: str  # "organization", "person", "product", "brand"
    mention_context: str | None = None
    confidence: float = 1.0
    metadata: dict = field(default_factory=dict)


@dataclass
class ExtractedIdentifier:
    """
    An identifier extracted from a filing.

    These get converted to IdentifierClaim domain objects.

    Fields:
        scheme: Identifier scheme (CIK, TICKER, CUSIP, ISIN, LEI)
        value: The identifier value
        entity_ref: Name of entity this identifier belongs to
        confidence: Extraction confidence 0.0-1.0
        source_section: Where in the filing this was found
    """

    scheme: str  # "CIK", "TICKER", "CUSIP", "ISIN", "LEI"
    value: str
    entity_ref: str  # Name of the entity this belongs to
    confidence: float = 1.0
    source_section: str | None = None


@dataclass
class ExtractedRelationship:
    """
    A relationship extracted from filing text.

    These get converted to Relationship domain objects.

    Fields:
        source_name: Name of source entity
        target_name: Name of target entity
        relationship_type: Type of relationship
        evidence_snippet: Text that supports this relationship
        confidence: Extraction confidence 0.0-1.0
    """

    source_name: str
    target_name: str
    relationship_type: str  # "SUPPLIER", "CUSTOMER", "COMPETITOR", "SUBSIDIARY", "PARTNER"
    evidence_snippet: str | None = None
    confidence: float = 0.8


@dataclass
class ExtractedEvent:
    """
    An event extracted from a filing (typically 8-K).

    These get converted to Event domain objects.

    Fields:
        event_type: Type of event
        event_date: When the event occurred
        description: Event description
        item_number: 8-K item number if applicable
        related_entities: Names of entities involved
        confidence: Extraction confidence 0.0-1.0
    """

    event_type: str  # "ACQUISITION", "CONTRACT", "GOVERNANCE", "SECURITY", etc.
    event_date: date | None = None
    description: str | None = None
    item_number: str | None = None  # "1.01", "2.01", etc.
    related_entities: list[str] = field(default_factory=list)
    confidence: float = 0.8


@dataclass
class FilingFacts:
    """
    Complete set of facts extracted from a single SEC filing.

    This is the primary contract between py-sec-edgar/FeedSpine and EntitySpine.
    External systems populate this dataclass, then call ingest_filing_facts()
    to persist everything to an EntitySpine store.

    Usage:
        ```python
        from entityspine.integration import FilingFacts, FilingEvidence, ingest_filing_facts
        from entityspine.stores import SqliteStore

        # Build the facts from a filing
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
            entities=[
                ExtractedEntity(name="Taiwan Semiconductor", entity_type="organization"),
            ],
            relationships=[
                ExtractedRelationship(
                    source_name="NVIDIA Corporation",
                    target_name="Taiwan Semiconductor",
                    relationship_type="SUPPLIER",
                    evidence_snippet="TSMC manufactures substantially all of our GPUs",
                ),
            ],
        )

        # Ingest into EntitySpine
        store = SqliteStore("./entities.db")
        store.initialize()
        result = ingest_filing_facts(store, facts)
        print(f"Created {result.entities_created} entities")
        ```

    Fields:
        evidence: Filing provenance information
        registrant_name: Filer company name
        registrant_cik: Filer CIK (10-digit padded)
        registrant_ticker: Primary ticker if known
        registrant_exchange: Exchange if known
        registrant_sic: SIC code if known
        registrant_state: State of incorporation if known
        entities: List of extracted entity references
        identifiers: List of extracted identifiers
        relationships: List of extracted relationships
        events: List of extracted events (mainly 8-K)
    """

    evidence: FilingEvidence
    registrant_name: str
    registrant_cik: str

    # Optional registrant details
    registrant_ticker: str | None = None
    registrant_exchange: str | None = None
    registrant_sic: str | None = None
    registrant_state: str | None = None
    registrant_fiscal_year_end: str | None = None

    # Extracted facts
    entities: list[ExtractedEntity] = field(default_factory=list)
    identifiers: list[ExtractedIdentifier] = field(default_factory=list)
    relationships: list[ExtractedRelationship] = field(default_factory=list)
    events: list[ExtractedEvent] = field(default_factory=list)

    # Processing metadata
    extraction_timestamp: datetime | None = None
    extractor_version: str | None = None

    def __post_init__(self):
        """Validate and normalize fields."""
        # Normalize CIK to 10 digits
        if self.registrant_cik:
            self.registrant_cik = self.registrant_cik.lstrip("0").zfill(10)
