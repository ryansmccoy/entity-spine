"""
Example 11: Real-World SEC Filing Enrichment

This example demonstrates the complete EntitySpine workflow for enriching
entity data from real SEC filings, including:

1. Parsing 10-K filing headers for company metadata
2. Extracting subsidiaries from Exhibit 21
3. Building a knowledge graph of relationships
4. Full lineage tracking
5. Querying the enriched data

This is the "killer feature" use case - feed in filings, get a complete
entity fabric with all relationships mapped and tracked.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, date, timezone
from pathlib import Path
from typing import Any, Iterator
from collections import defaultdict

# EntitySpine imports
from entityspine import (
    Entity,
    Security,
    Listing,
    IdentifierClaim,
    EntityResolver,
    ResolverConfig,
    create_entity,
    create_security,
    create_listing,
    create_claim,
    SqliteStore,
    EntityType,
    IdentifierScheme,
    ClaimStatus,
)
from entityspine.domain.graph import (
    EntityRelationship,
    RoleAssignment,
    PersonRole,
    RelationshipType,
    RoleType,
)
from entityspine.core.ulid import generate_ulid


print("=" * 80)
print("ENTITYSPINE: REAL-WORLD SEC FILING ENRICHMENT")
print("=" * 80)


# =============================================================================
# PART 1: DATA MODELS FOR SEC FILING PARSING
# =============================================================================

@dataclass
class IngestionSource:
    """Track where data came from."""
    source_type: str           # "sec_filing", "csv", "api"
    source_id: str             # accession_number, file_path
    source_name: str           # Human-readable description
    ingested_at: datetime
    
    # SEC-specific fields
    accession_number: str | None = None
    form_type: str | None = None
    filed_date: date | None = None


@dataclass
class SECFilingHeader:
    """Parsed SEC filing header data."""
    accession_number: str
    form_type: str
    filed_date: date
    
    # Company info
    company_name: str
    cik: str
    ticker: str | None
    sic_code: str | None
    sic_description: str | None
    
    # Location
    state_of_incorporation: str | None
    fiscal_year_end: str | None
    
    # Addresses
    business_address: dict | None
    mailing_address: dict | None
    
    # Former names (temporal history!)
    former_names: list[dict] = field(default_factory=list)


@dataclass
class Subsidiary:
    """A subsidiary extracted from Exhibit 21."""
    name: str
    jurisdiction: str | None
    ownership_pct: float | None
    parent_cik: str
    
    # Lineage
    source_filing: str
    section: str = "Exhibit 21"


@dataclass
class Executive:
    """An executive/officer from filing."""
    name: str
    title: str
    age: int | None
    tenure_start: date | None
    
    company_cik: str
    source_filing: str


# =============================================================================
# PART 2: SIMULATED SEC FILING DATA (Real-world structure)
# =============================================================================

def get_apple_10k_header() -> SECFilingHeader:
    """
    Simulated Apple 10-K header data.
    In production, this would be parsed from actual SGML filing.
    """
    return SECFilingHeader(
        accession_number="0000320193-24-000081",
        form_type="10-K",
        filed_date=date(2024, 11, 1),
        company_name="Apple Inc.",
        cik="0000320193",
        ticker="AAPL",
        sic_code="3571",
        sic_description="ELECTRONIC COMPUTERS",
        state_of_incorporation="CA",
        fiscal_year_end="0928",  # Sept 28
        business_address={
            "street1": "ONE APPLE PARK WAY",
            "city": "CUPERTINO",
            "state": "CA",
            "zip": "95014",
            "country": "US",
        },
        mailing_address={
            "street1": "ONE APPLE PARK WAY",
            "city": "CUPERTINO", 
            "state": "CA",
            "zip": "95014",
            "country": "US",
        },
        former_names=[
            # Apple had name changes historically
            {"name": "APPLE COMPUTER INC", "date": date(2007, 1, 9)},
        ],
    )


def get_apple_subsidiaries() -> list[Subsidiary]:
    """
    Simulated Exhibit 21 data for Apple.
    Real Exhibit 21 lists all significant subsidiaries.
    """
    return [
        Subsidiary(
            name="Apple Sales International",
            jurisdiction="Ireland",
            ownership_pct=100.0,
            parent_cik="0000320193",
            source_filing="0000320193-24-000081",
        ),
        Subsidiary(
            name="Apple Operations International",
            jurisdiction="Ireland",
            ownership_pct=100.0,
            parent_cik="0000320193",
            source_filing="0000320193-24-000081",
        ),
        Subsidiary(
            name="Apple Distribution International Ltd.",
            jurisdiction="Ireland",
            ownership_pct=100.0,
            parent_cik="0000320193",
            source_filing="0000320193-24-000081",
        ),
        Subsidiary(
            name="Braeburn Capital, Inc.",
            jurisdiction="Nevada",
            ownership_pct=100.0,
            parent_cik="0000320193",
            source_filing="0000320193-24-000081",
        ),
        Subsidiary(
            name="Apple Japan, Inc.",
            jurisdiction="Japan",
            ownership_pct=100.0,
            parent_cik="0000320193",
            source_filing="0000320193-24-000081",
        ),
        Subsidiary(
            name="Apple (China) Co., Ltd.",
            jurisdiction="China",
            ownership_pct=100.0,
            parent_cik="0000320193",
            source_filing="0000320193-24-000081",
        ),
    ]


def get_apple_executives() -> list[Executive]:
    """
    Simulated executive data from Item 10 / DEF 14A.
    """
    return [
        Executive(
            name="Timothy D. Cook",
            title="Chief Executive Officer",
            age=64,
            tenure_start=date(2011, 8, 24),
            company_cik="0000320193",
            source_filing="0000320193-24-000081",
        ),
        Executive(
            name="Luca Maestri",
            title="Senior Vice President, Chief Financial Officer",
            age=61,
            tenure_start=date(2014, 5, 1),
            company_cik="0000320193",
            source_filing="0000320193-24-000081",
        ),
        Executive(
            name="Katherine L. Adams",
            title="Senior Vice President, General Counsel",
            age=60,
            tenure_start=date(2017, 4, 1),
            company_cik="0000320193",
            source_filing="0000320193-24-000081",
        ),
        Executive(
            name="Deirdre O'Brien",
            title="Senior Vice President, Retail + People",
            age=57,
            tenure_start=date(2019, 2, 1),
            company_cik="0000320193",
            source_filing="0000320193-24-000081",
        ),
        Executive(
            name="Jeffrey E. Williams",
            title="Chief Operating Officer",
            age=61,
            tenure_start=date(2015, 12, 1),
            company_cik="0000320193",
            source_filing="0000320193-24-000081",
        ),
    ]


def get_supplier_mentions() -> list[dict]:
    """
    Simulated supplier mentions extracted from 10-K text.
    These would come from NER/LLM extraction in production.
    """
    return [
        {
            "name": "Taiwan Semiconductor Manufacturing Company",
            "normalized": "TSMC",
            "relationship_type": "supplier",
            "section": "Item 1A - Risk Factors",
            "context": "We depend on component suppliers, including TSMC...",
            "confidence": 0.95,
            "extraction_method": "pattern",
        },
        {
            "name": "Samsung Electronics",
            "normalized": "Samsung",
            "relationship_type": "supplier",
            "section": "Item 1A - Risk Factors",
            "context": "...key components from Samsung Electronics...",
            "confidence": 0.92,
            "extraction_method": "ner",
        },
        {
            "name": "Foxconn Technology Group",
            "normalized": "Foxconn",
            "relationship_type": "supplier",
            "section": "Item 1 - Business",
            "context": "...manufacturing partners including Foxconn...",
            "confidence": 0.94,
            "extraction_method": "pattern",
        },
        {
            "name": "LG Display",
            "normalized": "LG Display",
            "relationship_type": "supplier",
            "section": "Item 1A - Risk Factors",
            "context": "...display components from suppliers like LG Display...",
            "confidence": 0.88,
            "extraction_method": "ner",
        },
        {
            "name": "Qualcomm",
            "normalized": "Qualcomm",
            "relationship_type": "supplier",
            "section": "Item 1A - Risk Factors",
            "context": "...modem chips from Qualcomm...",
            "confidence": 0.91,
            "extraction_method": "llm",
        },
    ]


# =============================================================================
# PART 3: ENTITY FABRIC - INGESTION AND ENRICHMENT
# =============================================================================

class EntityFabricDemo:
    """
    Demonstrates the EntitySpine Universal Fabric concept.
    
    This class shows how to:
    1. Ingest entity data from SEC filings
    2. Create relationships in the knowledge graph
    3. Track lineage for everything
    4. Query the enriched data
    """
    
    def __init__(self, db_path: str = ":memory:"):
        self.store = SqliteStore(db_path)
        self.store.initialize()
        
        # Lineage tracking (in production, this goes to DB)
        self.lineage_records: list[dict] = []
        
        # Entity index for relationship linking
        self.entity_index: dict[str, Entity] = {}
        
        # Relationship store
        self.relationships: list[EntityRelationship] = []
        self.role_assignments: list[RoleAssignment] = []
    
    def ingest_filing_header(self, header: SECFilingHeader) -> Entity:
        """
        Ingest company data from filing header.
        Creates Entity + Claims with full lineage.
        """
        print(f"\n[INGEST] Filing header: {header.form_type} for {header.company_name}")
        
        source = IngestionSource(
            source_type="sec_filing_header",
            source_id=header.accession_number,
            source_name=f"{header.form_type} for {header.company_name}",
            ingested_at=datetime.now(timezone.utc),
            accession_number=header.accession_number,
            form_type=header.form_type,
            filed_date=header.filed_date,
        )
        
        # Create entity
        entity = create_entity(
            primary_name=header.company_name,
            entity_type=EntityType.ORGANIZATION,
            source_system="sec",
            source_id=header.cik,
        )
        
        # Save entity
        self.store.save_entity(entity)
        self.entity_index[header.cik] = entity
        
        # Create claims for identifiers
        claims_created = []
        
        # CIK claim
        cik_claim = create_claim(
            entity_id=entity.entity_id,
            scheme=IdentifierScheme.CIK,
            value=header.cik,
            source=f"sec:{header.accession_number}",
            confidence=1.0,
        )
        self.store.save_claim(cik_claim)
        claims_created.append(("CIK", header.cik))
        
        # Create a security and listing for ticker (proper Entity->Security->Listing hierarchy)
        if header.ticker:
            # Create security (the tradeable instrument)
            security = create_security(
                entity_id=entity.entity_id,
            )
            self.store.save_security(security)
            
            # Create listing (ticker on exchange)
            listing = create_listing(
                security_id=security.security_id,
                ticker=header.ticker,
                mic="XNAS",  # NASDAQ
            )
            self.store.save_listing(listing)
            claims_created.append(("Ticker", header.ticker))
        
        # Track lineage
        self._record_lineage(
            entity_type="entity",
            record_id=entity.entity_id,
            source=source,
            data_extracted={
                "primary_name": header.company_name,
                "identifiers": claims_created,
                "sic_code": header.sic_code,
                "state": header.state_of_incorporation,
            },
        )
        
        print(f"   Created entity: {entity.entity_id}")
        print(f"   Claims created: {claims_created}")
        
        # Handle former names (temporal data!)
        for former in header.former_names:
            print(f"   Former name: {former['name']} (changed {former['date']})")
            self._record_lineage(
                entity_type="former_name",
                record_id=f"{entity.entity_id}:former:{former['name']}",
                source=source,
                data_extracted={
                    "former_name": former["name"],
                    "date_changed": str(former["date"]),
                },
            )
        
        return entity
    
    def ingest_subsidiaries(
        self,
        parent_entity: Entity,
        subsidiaries: list[Subsidiary],
    ) -> list[Entity]:
        """
        Ingest subsidiaries from Exhibit 21.
        Creates Entity for each + relationship to parent.
        """
        print(f"\n[INGEST] Subsidiaries from Exhibit 21 ({len(subsidiaries)} found)")
        
        created_entities = []
        
        for sub in subsidiaries:
            source = IngestionSource(
                source_type="sec_exhibit_21",
                source_id=sub.source_filing,
                source_name=f"Exhibit 21 - {sub.name}",
                ingested_at=datetime.now(timezone.utc),
                accession_number=sub.source_filing,
                form_type="10-K",
            )
            
            # Create subsidiary entity
            sub_entity = create_entity(
                primary_name=sub.name,
                entity_type=EntityType.ORGANIZATION,
                source_system="sec_exhibit21",
                source_id=f"{sub.source_filing}:{sub.name}",
            )
            
            self.store.save_entity(sub_entity)
            created_entities.append(sub_entity)
            
            # Create SUBSIDIARY relationship
            relationship = EntityRelationship(
                relationship_id=generate_ulid(),
                from_entity_id=sub_entity.entity_id,
                to_entity_id=parent_entity.entity_id,
                relationship_type=RelationshipType.SUBSIDIARY,
                valid_from=date.today(),
                confidence=0.99,
                source_system="sec_exhibit21",
                source_ref=sub.source_filing,
            )
            self.relationships.append(relationship)
            
            # Track lineage
            self._record_lineage(
                entity_type="subsidiary",
                record_id=sub_entity.entity_id,
                source=source,
                data_extracted={
                    "name": sub.name,
                    "jurisdiction": sub.jurisdiction,
                    "ownership_pct": sub.ownership_pct,
                    "parent_entity_id": parent_entity.entity_id,
                },
            )
            
            print(f"   + {sub.name} ({sub.jurisdiction})")
        
        return created_entities
    
    def ingest_executives(
        self,
        company_entity: Entity,
        executives: list[Executive],
    ) -> list[RoleAssignment]:
        """
        Ingest executives as Person entities with RoleAssignments.
        """
        print(f"\n[INGEST] Executives ({len(executives)} found)")
        
        role_assignments = []
        
        for exec in executives:
            source = IngestionSource(
                source_type="sec_item10",
                source_id=exec.source_filing,
                source_name=f"Item 10 - {exec.name}",
                ingested_at=datetime.now(timezone.utc),
                accession_number=exec.source_filing,
            )
            
            # Create person entity
            person_entity = create_entity(
                primary_name=exec.name,
                entity_type=EntityType.PERSON,
                source_system="sec_item10",
                source_id=f"{exec.source_filing}:{exec.name}",
            )
            self.store.save_entity(person_entity)
            
            # Determine role type from title
            role_type = self._classify_role(exec.title)
            
            # Create role assignment
            role = RoleAssignment(
                role_assignment_id=generate_ulid(),
                person_entity_id=person_entity.entity_id,
                org_entity_id=company_entity.entity_id,
                role_type=role_type,
                title=exec.title,
                start_date=exec.tenure_start,
                source_system="sec_item10",
                source_ref=exec.source_filing,
            )
            self.role_assignments.append(role)
            role_assignments.append(role)
            
            # Track lineage
            self._record_lineage(
                entity_type="executive",
                record_id=person_entity.entity_id,
                source=source,
                data_extracted={
                    "name": exec.name,
                    "title": exec.title,
                    "age": exec.age,
                    "tenure_start": str(exec.tenure_start) if exec.tenure_start else None,
                },
            )
            
            print(f"   + {exec.name}: {exec.title}")
        
        return role_assignments
    
    def ingest_supplier_relationships(
        self,
        company_entity: Entity,
        mentions: list[dict],
    ) -> list[EntityRelationship]:
        """
        Create supplier relationships from extracted mentions.
        """
        print(f"\n[INGEST] Supplier relationships ({len(mentions)} mentions)")
        
        relationships = []
        
        for mention in mentions:
            source = IngestionSource(
                source_type="sec_extracted_mention",
                source_id=f"{company_entity.source_id}:{mention['normalized']}",
                source_name=f"Extracted mention: {mention['name']}",
                ingested_at=datetime.now(timezone.utc),
            )
            
            # Create entity for supplier (in production, would resolve to existing)
            supplier_entity = create_entity(
                primary_name=mention["normalized"],
                entity_type=EntityType.ORGANIZATION,
                source_system="extracted",
                source_id=f"mention:{mention['normalized']}",
            )
            self.store.save_entity(supplier_entity)
            
            # Create SUPPLIER relationship
            # Note: Direction is supplier -> company (supplier supplies to company)
            relationship = EntityRelationship(
                relationship_id=generate_ulid(),
                from_entity_id=supplier_entity.entity_id,
                to_entity_id=company_entity.entity_id,
                relationship_type=RelationshipType.SUPPLIER,
                valid_from=date.today(),
                confidence=mention["confidence"],
                source_system="extraction",
                source_ref=mention["section"],
            )
            self.relationships.append(relationship)
            relationships.append(relationship)
            
            # Track lineage with extraction metadata
            self._record_lineage(
                entity_type="supplier_relationship",
                record_id=relationship.relationship_id,
                source=source,
                data_extracted={
                    "supplier_name": mention["name"],
                    "normalized_name": mention["normalized"],
                    "section": mention["section"],
                    "context": mention["context"],
                    "confidence": mention["confidence"],
                    "extraction_method": mention["extraction_method"],
                },
            )
            
            confidence_pct = int(mention["confidence"] * 100)
            print(f"   + {mention['normalized']} supplies to company ({confidence_pct}% conf)")
        
        return relationships
    
    def _classify_role(self, title: str) -> RoleType:
        """Classify executive title to RoleType."""
        title_lower = title.lower()
        if "chief executive" in title_lower or "ceo" in title_lower:
            return RoleType.CEO
        elif "chief financial" in title_lower or "cfo" in title_lower:
            return RoleType.CFO
        elif "chief operating" in title_lower or "coo" in title_lower:
            return RoleType.COO
        elif "general counsel" in title_lower or "chief legal" in title_lower:
            return RoleType.CLO  # Chief Legal Officer
        elif "director" in title_lower:
            return RoleType.DIRECTOR
        else:
            return RoleType.OFFICER
    
    def _record_lineage(
        self,
        entity_type: str,
        record_id: str,
        source: IngestionSource,
        data_extracted: dict,
    ) -> None:
        """Record lineage for audit trail."""
        self.lineage_records.append({
            "lineage_id": generate_ulid(),
            "entity_type": entity_type,
            "record_id": record_id,
            "source_type": source.source_type,
            "source_id": source.source_id,
            "source_name": source.source_name,
            "accession_number": source.accession_number,
            "form_type": source.form_type,
            "filed_date": str(source.filed_date) if source.filed_date else None,
            "ingested_at": source.ingested_at.isoformat(),
            "data_extracted": data_extracted,
        })
    
    # =========================================================================
    # QUERYING
    # =========================================================================
    
    def get_entity_summary(self, cik: str) -> dict:
        """Get complete summary of an entity."""
        entity = self.entity_index.get(cik)
        if not entity:
            return {"error": f"Entity with CIK {cik} not found"}
        
        # Count relationships
        subsidiary_rels = [
            r for r in self.relationships
            if r.to_entity_id == entity.entity_id
            and r.relationship_type == RelationshipType.SUBSIDIARY
        ]
        
        supplier_rels = [
            r for r in self.relationships
            if r.to_entity_id == entity.entity_id
            and r.relationship_type == RelationshipType.SUPPLIER
        ]
        
        roles = [
            r for r in self.role_assignments
            if r.org_entity_id == entity.entity_id
        ]
        
        return {
            "entity_id": entity.entity_id,
            "primary_name": entity.primary_name,
            "cik": cik,
            "subsidiaries_count": len(subsidiary_rels),
            "suppliers_count": len(supplier_rels),
            "executives_count": len(roles),
        }
    
    def get_lineage_for_entity(self, entity_id: str) -> list[dict]:
        """Get all lineage records for an entity."""
        return [
            rec for rec in self.lineage_records
            if rec["record_id"] == entity_id
        ]
    
    def print_lineage_report(self) -> None:
        """Print a summary of all lineage records."""
        print("\n" + "=" * 80)
        print("LINEAGE REPORT")
        print("=" * 80)
        
        # Group by source type
        by_source = defaultdict(list)
        for rec in self.lineage_records:
            by_source[rec["source_type"]].append(rec)
        
        for source_type, records in by_source.items():
            print(f"\nSource: {source_type} ({len(records)} records)")
            for rec in records[:3]:  # Show first 3
                print(f"  - {rec['entity_type']}: {rec['data_extracted'].get('primary_name') or rec['data_extracted'].get('name') or rec['record_id'][:20]}")
            if len(records) > 3:
                print(f"  ... and {len(records) - 3} more")


# =============================================================================
# PART 4: RUN THE DEMO
# =============================================================================

def main():
    print("\n" + "=" * 80)
    print("PART 1: INITIALIZE ENTITY FABRIC")
    print("=" * 80)
    
    fabric = EntityFabricDemo()
    print("Entity Fabric initialized with in-memory SQLite store")
    
    # -------------------------------------------------------------------------
    # Ingest Apple 10-K data
    # -------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("PART 2: INGEST APPLE 10-K FILING DATA")
    print("=" * 80)
    
    # Get simulated filing data
    header = get_apple_10k_header()
    subsidiaries = get_apple_subsidiaries()
    executives = get_apple_executives()
    supplier_mentions = get_supplier_mentions()
    
    # Ingest header (creates main entity)
    apple_entity = fabric.ingest_filing_header(header)
    
    # Ingest subsidiaries
    sub_entities = fabric.ingest_subsidiaries(apple_entity, subsidiaries)
    
    # Ingest executives
    roles = fabric.ingest_executives(apple_entity, executives)
    
    # Ingest supplier relationships
    supplier_rels = fabric.ingest_supplier_relationships(apple_entity, supplier_mentions)
    
    # -------------------------------------------------------------------------
    # Query the enriched data
    # -------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("PART 3: QUERY ENRICHED ENTITY DATA")
    print("=" * 80)
    
    summary = fabric.get_entity_summary("0000320193")
    print(f"\nEntity Summary for Apple Inc.:")
    print(f"  Entity ID: {summary['entity_id']}")
    print(f"  Primary Name: {summary['primary_name']}")
    print(f"  CIK: {summary['cik']}")
    print(f"  Subsidiaries: {summary['subsidiaries_count']}")
    print(f"  Suppliers: {summary['suppliers_count']}")
    print(f"  Executives: {summary['executives_count']}")
    
    # -------------------------------------------------------------------------
    # Show knowledge graph relationships
    # -------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("PART 4: KNOWLEDGE GRAPH RELATIONSHIPS")
    print("=" * 80)
    
    print("\nSubsidiary Relationships:")
    for rel in fabric.relationships:
        if rel.relationship_type == RelationshipType.SUBSIDIARY:
            # Get entity names
            sub_entity = fabric.store.get_entity(rel.from_entity_id)
            if sub_entity:
                print(f"  {sub_entity.primary_name} --[SUBSIDIARY]--> Apple Inc.")
    
    print("\nSupplier Relationships:")
    for rel in fabric.relationships:
        if rel.relationship_type == RelationshipType.SUPPLIER:
            supplier = fabric.store.get_entity(rel.from_entity_id)
            if supplier:
                confidence_pct = int(rel.confidence * 100)
                print(f"  {supplier.primary_name} --[SUPPLIER]--> Apple Inc. ({confidence_pct}%)")
    
    print("\nExecutive Roles:")
    for role in fabric.role_assignments:
        person = fabric.store.get_entity(role.person_entity_id)
        if person:
            print(f"  {person.primary_name}: {role.title}")
    
    # -------------------------------------------------------------------------
    # Show lineage report
    # -------------------------------------------------------------------------
    fabric.print_lineage_report()
    
    # -------------------------------------------------------------------------
    # Demonstrate point-in-time concept
    # -------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("PART 5: LINEAGE ENABLES POINT-IN-TIME QUERIES")
    print("=" * 80)
    
    print("\nExample: Get lineage for Apple entity:")
    apple_lineage = fabric.get_lineage_for_entity(apple_entity.entity_id)
    for rec in apple_lineage:
        print(f"  Source: {rec['source_type']}")
        print(f"  Filing: {rec['accession_number']}")
        print(f"  Ingested: {rec['ingested_at']}")
        print(f"  Data: {json.dumps(rec['data_extracted'], indent=4)}")
    
    print("\n" + "=" * 80)
    print("DEMO COMPLETE")
    print("=" * 80)
    
    print("""
Summary:
--------
This example demonstrated the EntitySpine Universal Fabric concept:

1. INGEST from SEC filings:
   - Filing headers -> Company entity + identifier claims
   - Exhibit 21 -> Subsidiary entities + relationships
   - Item 10 -> Executive entities + role assignments
   - Extracted mentions -> Supplier relationships

2. KNOWLEDGE GRAPH automatically built:
   - Company -[SUBSIDIARY_OF]-> Subsidiaries
   - Suppliers -[SUPPLIES_TO]-> Company
   - Executives -[ROLE]-> Company

3. FULL LINEAGE tracked:
   - Every piece of data has source attribution
   - Accession number, form type, section
   - Extraction method and confidence
   - Timestamps for point-in-time queries

4. QUERYABLE:
   - Get entity summary with counts
   - Traverse relationships
   - Audit trail for any fact

In production, this same pattern scales to:
- Ingest thousands of filings
- Resolve entities across filings (deduplication)
- Track changes over time
- Answer "what did we know when?" questions
""")


if __name__ == "__main__":
    main()
