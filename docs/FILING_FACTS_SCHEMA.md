# Filing Facts Schema (EntitySpine Integration)

This document defines the schema for extracting structured facts from SEC filings and storing them in EntitySpine's Knowledge Graph.

## Overview

When py-sec-edgar processes a filing, it extracts:
1. **Entity References** - Companies, people, products mentioned
2. **Relationships** - Supplier/customer/competitor links
3. **Events** - Material events (acquisitions, bankruptcies, capital raises)
4. **Contracts** - Disclosed material agreements
5. **Identifiers** - CIK, ticker, CUSIP claims with filing evidence

These facts flow into EntitySpine's domain models.

---

## Filing → EntitySpine Mapping

### Source Filing Metadata

Every fact extracted carries provenance:

```python
@dataclass
class FilingEvidence:
    """Evidence linking a fact to its source filing."""
    filing_id: str              # Accession number as ULID-compatible ID
    accession_number: str       # Original SEC accession
    form_type: str              # 10-K, 10-Q, 8-K, etc.
    filed_date: date            # Filing date
    section_id: Optional[str]   # Section within filing (Item 1, Risk Factors)
    excerpt_hash: Optional[str] # SHA256 of the evidence text
    excerpt_snippet: Optional[str]  # First 200 chars of evidence
```

### Entity Extraction

From Item 1 (Business), Risk Factors, Exhibit indexes:

| Filing Source | EntitySpine Model | Example |
|--------------|-------------------|---------|
| Registrant | Entity (organization) | "NVIDIA Corporation" |
| Named customer | Entity (organization) | "Microsoft Corporation" |
| Named supplier | Entity (organization) | "Taiwan Semiconductor" |
| Executive | Entity (person) | "Jensen Huang" |
| Product mention | Product | "A100 GPU" |

### Identifier Claims

From filing header, exhibits, XBRL:

| Filing Source | IdentifierClaim Fields | Example |
|--------------|------------------------|---------|
| Filing header CIK | scheme=CIK, entity_id=... | "0001045810" |
| EDGAR ticker | scheme=TICKER, listing_id=... | "NVDA" |
| Exhibit CUSIP | scheme=CUSIP, security_id=... | "67066G104" |
| XBRL LEI | scheme=LEI, entity_id=... | "549300S4KLBER..." |

### Events

From 8-K filings and Item 9.01:

| Form/Item | EventType | Description |
|-----------|-----------|-------------|
| 8-K Item 1.01 | CONTRACT | Entry into Material Agreement |
| 8-K Item 1.02 | CONTRACT | Termination of Material Agreement |
| 8-K Item 2.01 | ACQUISITION | Completion of Acquisition |
| 8-K Item 2.05 | RESTRUCTURE | Costs, Charges, Exit Activities |
| 8-K Item 3.01 | SECURITY | Notice of Delisting |
| 8-K Item 4.01 | GOVERNANCE | Change in Auditor |
| 8-K Item 5.02 | GOVERNANCE | Director/Officer Changes |
| 8-K Item 7.01 | DISCLOSURE | Regulation FD Disclosure |

### Relationships

From Item 1, Risk Factors, MD&A:

| Relationship | How Detected | Direction |
|--------------|--------------|-----------|
| SUPPLIES | "purchased from", "sourced from" | Target → Source |
| CUSTOMERS | "sold to", "provided services" | Source → Target |
| COMPETES_WITH | "competitive landscape", "principal competitor" | Bidirectional |
| SUBSIDIARY | "wholly-owned subsidiary" | Parent → Child |
| PARTNER | "partnership", "joint venture" | Bidirectional |

---

## Integration Pipeline

### Step 1: Filing Discovery

```python
from py_sec_edgar import SEC

async with SEC() as sec:
    filings = await sec.filings.search(
        tickers=["NVDA"],
        forms=["10-K", "8-K"],
        filed_after="2024-01-01"
    )
```

### Step 2: Content Extraction

```python
for ref in filings:
    # Download and extract sections
    content = await sec.download(ref)
    sections = await sec.extract_sections(content)
    
    # Extract entities using NER or patterns
    entities = extract_entities(sections["item1"])
    relationships = extract_relationships(sections["risk_factors"])
```

### Step 3: EntitySpine Storage

```python
from entityspine import SqliteStore, Entity, EntityType, EntityStatus
from entityspine import IdentifierClaim, IdentifierScheme, VendorNamespace
from entityspine import Relationship, NodeRef, NodeKind, RelationshipType

store = SqliteStore("./entities.db")

# Store the registrant
entity = Entity(
    primary_name="NVIDIA Corporation",
    entity_type=EntityType.ORGANIZATION,
    status=EntityStatus.ACTIVE,
    jurisdiction="US-DE",
    source_system="sec-edgar",
    source_id=ref.cik.value,
)
store.save_entity(entity)

# Attach CIK claim with evidence
cik_claim = IdentifierClaim(
    entity_id=entity.entity_id,
    scheme=IdentifierScheme.CIK,
    value=ref.cik.value,
    namespace=VendorNamespace.SEC,
    source="sec-edgar",
    source_ref=ref.accession_number.value,
    confidence=1.0,
)
store.save_claim(cik_claim)
```

---

## Example: Full Filing Ingest

```python
"""Example: Ingest a 10-K filing into EntitySpine."""

from datetime import date
from entityspine import (
    SqliteStore,
    Entity, EntityType, EntityStatus,
    Security, SecurityType, SecurityStatus,
    Listing, ListingStatus,
    IdentifierClaim, IdentifierScheme, VendorNamespace, ClaimStatus,
    Relationship, NodeRef, NodeKind, RelationshipType,
    Event, EventType, EventStatus,
)

def ingest_10k(store: SqliteStore, filing_data: dict):
    """Ingest facts from a 10-K filing into EntitySpine."""
    
    # 1. Create/update the registrant entity
    registrant = Entity(
        primary_name=filing_data["company_name"],
        entity_type=EntityType.ORGANIZATION,
        status=EntityStatus.ACTIVE,
        jurisdiction=filing_data.get("state_of_incorporation"),
        sic_code=filing_data.get("sic_code"),
        source_system="sec-edgar",
        source_id=filing_data["cik"],
    )
    store.save_entity(registrant)
    
    # 2. Attach CIK identifier claim
    cik_claim = IdentifierClaim(
        entity_id=registrant.entity_id,
        scheme=IdentifierScheme.CIK,
        value=filing_data["cik"],
        namespace=VendorNamespace.SEC,
        source_ref=filing_data["accession_number"],
        source="sec-edgar",
        confidence=1.0,
        status=ClaimStatus.ACTIVE,
    )
    store.save_claim(cik_claim)
    
    # 3. Create common stock security if ticker known
    if filing_data.get("ticker"):
        security = Security(
            entity_id=registrant.entity_id,
            security_type=SecurityType.COMMON_STOCK,
            description=f"Common Stock of {filing_data['company_name']}",
            currency="USD",
            status=SecurityStatus.ACTIVE,
            source_system="sec-edgar",
            source_id=filing_data["cik"],
        )
        store.save_security(security)
        
        # Create primary listing
        listing = Listing(
            security_id=security.security_id,
            ticker=filing_data["ticker"],
            exchange=filing_data.get("exchange", "UNKNOWN"),
            is_primary=True,
            currency="USD",
            status=ListingStatus.ACTIVE,
            source_system="sec-edgar",
        )
        store.save_listing(listing)
        
        # Attach TICKER claim to listing
        ticker_claim = IdentifierClaim(
            listing_id=listing.listing_id,
            scheme=IdentifierScheme.TICKER,
            value=filing_data["ticker"],
            namespace=VendorNamespace.EXCHANGE,
            source_ref=filing_data["accession_number"],
            source="sec-edgar",
            confidence=1.0,
            status=ClaimStatus.ACTIVE,
        )
        store.save_claim(ticker_claim)
    
    # 4. Process extracted relationships
    for rel_data in filing_data.get("relationships", []):
        # Create target entity if needed
        target = Entity(
            primary_name=rel_data["target_name"],
            entity_type=EntityType.ORGANIZATION,
            status=EntityStatus.ACTIVE,
            source_system="sec-edgar",
        )
        store.save_entity(target)
        
        # Create relationship with evidence
        relationship = Relationship(
            source_ref=NodeRef(NodeKind.ENTITY, registrant.entity_id),
            target_ref=NodeRef(NodeKind.ENTITY, target.entity_id),
            relationship_type=RelationshipType(rel_data["type"]),
            confidence=rel_data.get("confidence", 0.8),
            evidence_filing_id=filing_data["accession_number"],
            evidence_snippet=rel_data.get("evidence", ""),
            source_system="sec-edgar",
        )
        store.save_relationship(relationship)
    
    return registrant


# Usage
if __name__ == "__main__":
    store = SqliteStore(":memory:")
    
    # Example filing data (would come from py-sec-edgar extraction)
    filing_data = {
        "cik": "0001045810",
        "ticker": "NVDA",
        "company_name": "NVIDIA Corporation",
        "accession_number": "0001045810-24-000029",
        "state_of_incorporation": "DE",
        "sic_code": "3674",
        "exchange": "NASDAQ",
        "relationships": [
            {
                "target_name": "Taiwan Semiconductor Manufacturing Company",
                "type": "supplier",
                "confidence": 0.95,
                "evidence": "TSMC manufactures substantially all of our GPUs..."
            },
            {
                "target_name": "Microsoft Corporation",
                "type": "customer",
                "confidence": 0.9,
                "evidence": "Microsoft is a significant customer for our datacenter..."
            }
        ]
    }
    
    entity = ingest_10k(store, filing_data)
    print(f"Ingested: {entity.primary_name} ({entity.entity_id})")
    print(f"Entities: {store.entity_count()}")
    print(f"Relationships: {store.relationship_count()}")
```

---

## CLI Integration (Future)

```bash
# Ingest filings into EntitySpine graph
sec kg ingest --tickers NVDA AAPL --forms 10-K --years 2024

# Query the graph
sec kg suppliers NVDA
sec kg customers TSLA
sec kg path NVDA TSMC

# Export for analysis
sec kg export --format parquet --output ./entities/
```

---

## Field Mapping Reference

### Entity Fields

| SEC Source | Entity Field | Notes |
|------------|--------------|-------|
| EDGAR header | primary_name | From `<COMPANY-CONFORMED-NAME>` |
| Filing | entity_type | ORGANIZATION for registrants |
| Header | jurisdiction | `<STATE-OF-INCORPORATION>` |
| Header | sic_code | `<ASSIGNED-SIC>` |
| Header | source_id | CIK value |
| - | source_system | Always "sec-edgar" |

### IdentifierClaim Fields

| SEC Source | Claim Field | Notes |
|------------|-------------|-------|
| Header CIK | scheme=CIK | Zero-padded 10 digits |
| EDGAR ticker | scheme=TICKER | From company_tickers.json |
| Exhibit 99 | scheme=CUSIP | From prospectus/registration |
| XBRL context | scheme=LEI | From dei:LegalEntityIdentifier |
| - | source_ref | Accession number |
| - | captured_at | Filing date |

### Relationship Fields

| Extraction | Relationship Field | Notes |
|------------|-------------------|-------|
| NER output | source_ref/target_ref | NodeRef to entities |
| Pattern match | relationship_type | SUPPLIES, CUSTOMERS, etc. |
| Sentence | evidence_snippet | First 200 chars |
| Context | confidence | 0.0-1.0 from NER model |
| Filing | evidence_filing_id | Accession number |
| Section | evidence_section_id | "item1", "risk_factors" |

---

*Last updated: January 2025 | EntitySpine v0.3.1 | py-sec-edgar integration*

---

## Integration Module (v0.3.1+)

The integration module (`entityspine.integration`) provides a clean contract for py-sec-edgar:

```python
from entityspine.integration import (
    FilingFacts,
    FilingEvidence,
    ingest_filing_facts,
    ingest_filing,
)
from entityspine.integration.contracts import (
    ExtractedEntity,
    ExtractedIdentifier,
    ExtractedRelationship,
    ExtractedEvent,
)
from entityspine.stores import SqliteStore
from datetime import date

# Build facts from a 10-K filing
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
    entities=[
        ExtractedEntity(name="Taiwan Semiconductor", entity_type="organization"),
    ],
    relationships=[
        ExtractedRelationship(
            source_name="NVIDIA Corporation",
            target_name="Taiwan Semiconductor",
            relationship_type="SUPPLIER",
            evidence_snippet="TSMC manufactures all of our GPUs",
        ),
    ],
)

# Ingest into EntitySpine
store = SqliteStore(":memory:")
store.initialize()
result = ingest_filing_facts(store, facts)

print(f"Created {result.entities_created} entities, {result.relationships_created} relationships")
# Created 2 entities, 1 relationships
```

See [src/entityspine/integration/](../src/entityspine/integration/) for the full implementation.
