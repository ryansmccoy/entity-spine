"""
EntitySpine Integration Tests: Semiconductor Industry Ecosystem

This test suite demonstrates real-world entity relationship modeling using
the semiconductor industry as an example. It covers:

- Global companies with multiple identifiers (CIK, LEI, ISIN, etc.)
- Complex ownership hierarchies (subsidiaries, holding companies)
- Supply chain relationships (customers, suppliers, foundries)
- Competitive relationships
- Joint ventures and strategic partnerships
- Private company relationships discovered from SEC filings
- Geographic and jurisdictional complexity

The semiconductor industry is ideal because:
1. Global supply chains spanning US, Taiwan, Korea, Japan, Netherlands, China
2. Complex ownership (fabless → foundry → equipment → materials)
3. Well-documented in SEC filings (10-K risk factors, supplier disclosures)
4. Mix of public and private companies
5. Strategic relationships (exclusive manufacturing, licensing, JVs)

Run with: pytest tests/integration/test_semiconductor_ecosystem.py -v
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

import pytest

# EntitySpine imports
from entityspine.domain import (
    Entity,
    EntityType,
    EntityStatus,
    IdentifierClaim,
    IdentifierScheme,
    IdentifierScope,
    create_entity as es_create_entity,
    create_claim,
)
from entityspine.core.ulid import generate_ulid


# =============================================================================
# EXTENDED ENTITY FOR TESTING
# =============================================================================

@dataclass
class TestEntity:
    """
    Extended entity with identifiers for testing purposes.
    
    In production, EntitySpine stores identifiers separately via IdentifierClaim.
    This wrapper makes it easier to work with entities and their identifiers together.
    """
    entity: Entity
    identifiers: list[IdentifierClaim] = field(default_factory=list)
    
    @property
    def entity_id(self) -> str:
        return self.entity.entity_id
    
    @property
    def primary_name(self) -> str:
        return self.entity.primary_name
    
    @property
    def jurisdiction(self) -> str | None:
        return self.entity.jurisdiction
    
    @property
    def entity_type(self) -> EntityType:
        return self.entity.entity_type


# =============================================================================
# RELATIONSHIP TYPES
# =============================================================================

class RelationshipType(str, Enum):
    """Types of relationships between entities."""
    # Ownership
    PARENT = "parent"  # A owns B
    SUBSIDIARY = "subsidiary"  # B is owned by A
    MINORITY_STAKE = "minority_stake"  # A owns <50% of B
    JOINT_VENTURE = "joint_venture"  # A and B jointly own C
    
    # Supply Chain
    CUSTOMER = "customer"  # A buys from B
    SUPPLIER = "supplier"  # A sells to B
    FOUNDRY = "foundry"  # A manufactures chips for B (semiconductor specific)
    FABLESS_CLIENT = "fabless_client"  # B designs, A manufactures
    
    # Strategic
    COMPETITOR = "competitor"  # A and B compete
    PARTNER = "partner"  # A and B have strategic partnership
    LICENSEE = "licensee"  # A licenses IP from B
    LICENSOR = "licensor"  # A licenses IP to B
    
    # Investment
    INVESTOR = "investor"  # A invested in B
    PORTFOLIO_COMPANY = "portfolio_company"  # B received investment from A
    
    # Legal/Regulatory
    SUCCESSOR = "successor"  # A succeeded B (merger, acquisition)
    PREDECESSOR = "predecessor"  # B preceded A
    SPIN_OFF = "spin_off"  # A was spun off from B


@dataclass
class Relationship:
    """A relationship between two entities."""
    id: str
    source_entity_id: str
    target_entity_id: str
    relationship_type: RelationshipType
    
    # Relationship metadata
    ownership_percentage: float | None = None  # For ownership relationships
    start_date: date | None = None
    end_date: date | None = None  # None = still active
    
    # Evidence/provenance
    source: str | None = None  # Where we learned this (SEC filing, news, etc.)
    confidence: float = 1.0  # 0.0 to 1.0
    
    # Additional context
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass 
class EntityGraph:
    """A graph of entities and their relationships."""
    entities: dict[str, TestEntity] = field(default_factory=dict)
    relationships: list[Relationship] = field(default_factory=list)
    
    def add_entity(self, entity: TestEntity) -> None:
        self.entities[entity.entity_id] = entity
    
    def add_relationship(
        self,
        source_id: str,
        target_id: str,
        rel_type: RelationshipType,
        **kwargs
    ) -> Relationship:
        rel = Relationship(
            id=generate_ulid(),
            source_entity_id=source_id,
            target_entity_id=target_id,
            relationship_type=rel_type,
            **kwargs
        )
        self.relationships.append(rel)
        return rel
    
    def get_entity(self, entity_id: str) -> TestEntity | None:
        return self.entities.get(entity_id)
    
    def get_relationships(
        self,
        entity_id: str,
        rel_type: RelationshipType | None = None,
        direction: str = "both"  # "outgoing", "incoming", "both"
    ) -> list[Relationship]:
        """Get relationships involving an entity."""
        results = []
        for rel in self.relationships:
            if rel_type and rel.relationship_type != rel_type:
                continue
            
            if direction in ("outgoing", "both") and rel.source_entity_id == entity_id:
                results.append(rel)
            elif direction in ("incoming", "both") and rel.target_entity_id == entity_id:
                results.append(rel)
        
        return results
    
    def get_supply_chain(self, entity_id: str, depth: int = 2) -> dict:
        """Traverse supply chain relationships."""
        result = {
            "entity": self.entities.get(entity_id),
            "customers": [],
            "suppliers": [],
        }
        
        for rel in self.get_relationships(entity_id, RelationshipType.CUSTOMER, "incoming"):
            customer = self.entities.get(rel.source_entity_id)
            if customer:
                result["customers"].append({
                    "entity": customer,
                    "relationship": rel
                })
        
        for rel in self.get_relationships(entity_id, RelationshipType.SUPPLIER, "incoming"):
            supplier = self.entities.get(rel.source_entity_id)
            if supplier:
                result["suppliers"].append({
                    "entity": supplier,
                    "relationship": rel
                })
        
        return result


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def create_entity(
    name: str,
    entity_type: EntityType = EntityType.ORGANIZATION,
    jurisdiction: str | None = None,
    **identifiers
) -> TestEntity:
    """Create an entity with identifiers.
    
    In EntitySpine v2.2.3, IdentifierClaim scope is determined by which
    target ID is set (entity_id, security_id, or listing_id).
    """
    entity_id = generate_ulid()
    security_id = generate_ulid()  # For security-scoped identifiers
    listing_id = generate_ulid()   # For listing-scoped identifiers
    claims = []
    
    # Map identifier kwargs to claims with appropriate target
    # EntitySpine determines scope by which *_id field is set
    for key, value in identifiers.items():
        if not value:
            continue
            
        if key == "cik":
            claims.append(IdentifierClaim(
                scheme=IdentifierScheme.CIK,
                value=str(value),
                entity_id=entity_id,
            ))
        elif key == "lei":
            claims.append(IdentifierClaim(
                scheme=IdentifierScheme.LEI,
                value=str(value),
                entity_id=entity_id,
            ))
        elif key == "ticker":
            claims.append(IdentifierClaim(
                scheme=IdentifierScheme.TICKER,
                value=str(value),
                listing_id=listing_id,
            ))
        elif key == "isin":
            claims.append(IdentifierClaim(
                scheme=IdentifierScheme.ISIN,
                value=str(value),
                security_id=security_id,
            ))
        elif key == "cusip":
            claims.append(IdentifierClaim(
                scheme=IdentifierScheme.CUSIP,
                value=str(value),
                security_id=security_id,
            ))
        elif key == "figi":
            claims.append(IdentifierClaim(
                scheme=IdentifierScheme.FIGI,
                value=str(value),
                security_id=security_id,
            ))
        elif key == "tax_id":
            claims.append(IdentifierClaim(
                scheme=IdentifierScheme.EIN,
                value=str(value),
                entity_id=entity_id,
            ))
    
    entity = Entity(
        entity_id=entity_id,
        primary_name=name,
        entity_type=entity_type,
        jurisdiction=jurisdiction,
    )
    
    return TestEntity(entity=entity, identifiers=claims)


# =============================================================================
# LEVEL 1: BASIC - Single Company with Identifiers
# =============================================================================

class TestLevel1Basic:
    """
    BASIC: Single entity with multiple identifiers.
    
    Demonstrates:
    - Creating an entity with multiple identifier schemes
    - Different identifier scopes (entity vs security vs listing)
    - Jurisdiction handling
    """
    
    def test_us_public_company_full_identifiers(self):
        """
        NVIDIA Corporation - US public company with complete identifier set.
        
        Real identifiers:
        - CIK: 0001045810
        - LEI: 549300S4KLFTLO7GSQ80
        - Ticker: NVDA (NASDAQ)
        - ISIN: US67066G1040
        - CUSIP: 67066G104
        - FIGI: BBG000BBJQV0
        """
        nvidia = create_entity(
            name="NVIDIA Corporation",
            entity_type=EntityType.ORGANIZATION,
            jurisdiction="US-DE",  # Delaware incorporation
            cik="0001045810",
            lei="549300S4KLFTLO7GSQ80",
            ticker="NVDA",
            isin="US67066G1040",
            cusip="67066G104",
            figi="BBG000BBJQV0",
        )
        
        assert nvidia.primary_name == "NVIDIA Corporation"
        assert nvidia.jurisdiction == "US-DE"
        assert len(nvidia.identifiers) == 6
        
        # Verify we can find by any identifier
        cik_claims = [c for c in nvidia.identifiers if c.scheme == IdentifierScheme.CIK]
        assert len(cik_claims) == 1
        assert cik_claims[0].value == "0001045810"
        
        lei_claims = [c for c in nvidia.identifiers if c.scheme == IdentifierScheme.LEI]
        assert len(lei_claims) == 1
        assert lei_claims[0].value == "549300S4KLFTLO7GSQ80"
    
    def test_foreign_company_multiple_listings(self):
        """
        Taiwan Semiconductor (TSMC) - Foreign company with ADR listing.
        
        TSMC is listed on:
        - Taiwan Stock Exchange (2330.TW)
        - NYSE ADR (TSM)
        
        This tests handling companies with multiple exchange listings.
        """
        # Main Taiwanese entity
        tsmc_tw = create_entity(
            name="Taiwan Semiconductor Manufacturing Company Limited",
            entity_type=EntityType.ORGANIZATION,
            jurisdiction="TW",  # Taiwan
            lei="549300KB6NK5SBD14S87",
            ticker="2330",  # Taiwan listing
        )
        
        # For ADR, we'd typically create a separate listing entity
        # Here we add multiple ticker claims with different listing_ids
        adr_listing_id = generate_ulid()
        tsmc_adr_claim = IdentifierClaim(
            scheme=IdentifierScheme.TICKER,
            value="TSM",
            listing_id=adr_listing_id,  # Different listing for NYSE ADR
        )
        tsmc_tw.identifiers.append(tsmc_adr_claim)
        
        # Also has US SEC filing (foreign private issuer)
        tsmc_cik_claim = IdentifierClaim(
            scheme=IdentifierScheme.CIK,
            value="0001046179",
            entity_id=tsmc_tw.entity_id,
        )
        tsmc_tw.identifiers.append(tsmc_cik_claim)
        
        assert tsmc_tw.jurisdiction == "TW"
        
        # Find all ticker listings
        tickers = [c for c in tsmc_tw.identifiers if c.scheme == IdentifierScheme.TICKER]
        assert len(tickers) == 2
        
        ticker_values = {t.value for t in tickers}
        assert "2330" in ticker_values  # Taiwan
        assert "TSM" in ticker_values  # NYSE ADR
    
    def test_private_company_limited_identifiers(self):
        """
        ARM Holdings - Private company (SoftBank owned) with limited public identifiers.
        
        Private companies typically only have:
        - LEI (if they participate in financial markets)
        - Tax ID (not public)
        - Internal identifiers
        
        Note: ARM went public again in 2023, but this tests the private scenario.
        """
        arm_private = create_entity(
            name="Arm Limited",
            entity_type=EntityType.ORGANIZATION,
            jurisdiction="GB",  # UK company
            lei="9845002986AICDJQLL35",  # LEI is public even for private cos
            # No CIK, no ticker (was private)
        )
        
        assert arm_private.entity_type == EntityType.ORGANIZATION
        assert arm_private.jurisdiction == "GB"
        
        # Only LEI identifier
        assert len(arm_private.identifiers) == 1
        assert arm_private.identifiers[0].scheme == IdentifierScheme.LEI


# =============================================================================
# LEVEL 2: INTERMEDIATE - Parent/Subsidiary Relationships
# =============================================================================

class TestLevel2Intermediate:
    """
    INTERMEDIATE: Ownership hierarchies and corporate structures.
    
    Demonstrates:
    - Parent-subsidiary relationships
    - Ownership percentages
    - Multi-level hierarchies
    - Cross-border ownership
    """
    
    def test_simple_subsidiary_structure(self):
        """
        Intel Corporation subsidiary structure (simplified).
        
        Intel Corporation (parent)
        ├── Intel Americas, Inc.
        ├── Intel International B.V. (Netherlands holding)
        │   └── Intel Technology (China) Co., Ltd.
        └── Mobileye Global Inc. (87% owned after IPO)
        """
        graph = EntityGraph()
        
        # Parent company
        intel = create_entity(
            name="Intel Corporation",
            jurisdiction="US-DE",
            cik="0000050863",
            lei="YNT5USFQLJZLRF8XQ755",
            ticker="INTC",
        )
        graph.add_entity(intel)
        
        # US subsidiary
        intel_americas = create_entity(
            name="Intel Americas, Inc.",
            jurisdiction="US-DE",
            # Private subsidiary - no public identifiers
        )
        graph.add_entity(intel_americas)
        
        # Netherlands holding company
        intel_nl = create_entity(
            name="Intel International B.V.",
            jurisdiction="NL",
            lei="549300I5BE9V5CQZPC49",  # Has LEI for EU operations
        )
        graph.add_entity(intel_nl)
        
        # China subsidiary
        intel_china = create_entity(
            name="Intel Technology (China) Co., Ltd.",
            jurisdiction="CN",
        )
        graph.add_entity(intel_china)
        
        # Mobileye (partially owned after 2022 IPO)
        mobileye = create_entity(
            name="Mobileye Global Inc.",
            jurisdiction="US-DE",
            cik="0001900535",
            ticker="MBLY",
        )
        graph.add_entity(mobileye)
        
        # Define relationships
        graph.add_relationship(
            intel.entity_id, intel_americas.entity_id,
            RelationshipType.PARENT,
            ownership_percentage=100.0,
            source="SEC 10-K Exhibit 21"
        )
        
        graph.add_relationship(
            intel.entity_id, intel_nl.entity_id,
            RelationshipType.PARENT,
            ownership_percentage=100.0,
            source="SEC 10-K Exhibit 21"
        )
        
        graph.add_relationship(
            intel_nl.entity_id, intel_china.entity_id,
            RelationshipType.PARENT,
            ownership_percentage=100.0,
            source="SEC 10-K Exhibit 21",
            metadata={"notes": "Held through Netherlands for tax efficiency"}
        )
        
        graph.add_relationship(
            intel.entity_id, mobileye.entity_id,
            RelationshipType.PARENT,
            ownership_percentage=87.0,  # Post-IPO ownership
            start_date=date(2022, 10, 26),  # IPO date
            source="Mobileye IPO Prospectus"
        )
        
        # Verify structure
        intel_subs = graph.get_relationships(intel.entity_id, RelationshipType.PARENT, "outgoing")
        assert len(intel_subs) == 3  # Americas, NL, Mobileye
        
        # Find the Mobileye relationship to check partial ownership
        mobileye_rel = next(r for r in intel_subs if r.target_entity_id == mobileye.entity_id)
        assert mobileye_rel.ownership_percentage == 87.0
    
    def test_cross_border_holding_structure(self):
        """
        Samsung Electronics complex holding structure.
        
        Samsung Electronics is part of the Samsung Group chaebol:
        
        Samsung C&T (holding company)
        └── Samsung Electronics (via circular ownership)
            ├── Samsung Display Co., Ltd. (84.8%)
            ├── Samsung SDI (19.6% cross-holding)
            ├── Samsung Austin Semiconductor, LLC (US fab)
            └── Harman International (acquired 2017)
        """
        graph = EntityGraph()
        
        # Parent holding
        samsung_ct = create_entity(
            name="Samsung C&T Corporation",
            jurisdiction="KR",
            lei="988400GFRE4IDFPE9E64",
            ticker="028260",  # KRX
        )
        graph.add_entity(samsung_ct)
        
        # Main electronics company
        samsung_elec = create_entity(
            name="Samsung Electronics Co., Ltd.",
            jurisdiction="KR",
            lei="9884007ER46L6N7EI764",
            ticker="005930",  # KRX
        )
        graph.add_entity(samsung_elec)
        
        # Display subsidiary
        samsung_display = create_entity(
            name="Samsung Display Co., Ltd.",
            jurisdiction="KR",
        )
        graph.add_entity(samsung_display)
        
        # US manufacturing subsidiary
        samsung_austin = create_entity(
            name="Samsung Austin Semiconductor, LLC",
            jurisdiction="US-TX",
        )
        graph.add_entity(samsung_austin)
        
        # Acquired US company
        harman = create_entity(
            name="Harman International Industries, Incorporated",
            jurisdiction="US-DE",
            lei="549300CU3B3MTSHW3X23",
            # Was public (HAR) before acquisition
        )
        graph.add_entity(harman)
        
        # Relationships
        graph.add_relationship(
            samsung_ct.entity_id, samsung_elec.entity_id,
            RelationshipType.PARENT,
            ownership_percentage=17.5,  # Complex chaebol structure
            metadata={"notes": "Part of circular cross-holding structure"}
        )
        
        graph.add_relationship(
            samsung_elec.entity_id, samsung_display.entity_id,
            RelationshipType.PARENT,
            ownership_percentage=84.8,
        )
        
        graph.add_relationship(
            samsung_elec.entity_id, samsung_austin.entity_id,
            RelationshipType.PARENT,
            ownership_percentage=100.0,
        )
        
        graph.add_relationship(
            samsung_elec.entity_id, harman.entity_id,
            RelationshipType.PARENT,
            ownership_percentage=100.0,
            start_date=date(2017, 3, 10),  # Acquisition closed
            source="SEC Form 8-K",
            metadata={"acquisition_price_usd": 8_000_000_000}
        )
        
        # Verify complex structure
        samsung_holdings = graph.get_relationships(
            samsung_elec.entity_id, 
            RelationshipType.PARENT, 
            "outgoing"
        )
        assert len(samsung_holdings) == 3
        
        harman_rel = next(r for r in samsung_holdings if r.target_entity_id == harman.entity_id)
        assert harman_rel.metadata.get("acquisition_price_usd") == 8_000_000_000


# =============================================================================
# LEVEL 3: ADVANCED - Supply Chain Relationships
# =============================================================================

class TestLevel3Advanced:
    """
    ADVANCED: Full supply chain modeling with customers, suppliers, and foundries.
    
    Demonstrates:
    - Customer/supplier relationships with revenue significance
    - Foundry/fabless relationships (semiconductor-specific)
    - Multi-tier supply chains
    - Relationship evidence from SEC filings
    """
    
    def test_apple_semiconductor_supply_chain(self):
        """
        Apple's semiconductor supply chain (partial).
        
        Apple (fabless) → TSMC (foundry) → ASML (equipment)
        
        Key relationships from Apple's 10-K:
        - TSMC: Primary foundry for A-series and M-series chips
        - Samsung: Secondary foundry (older nodes)
        - Broadcom: WiFi/Bluetooth chips
        - Qualcomm: Modem chips (transitioning to in-house)
        - ASML: Equipment supplier to foundries
        """
        graph = EntityGraph()
        
        # Apple (the customer/fabless designer)
        apple = create_entity(
            name="Apple Inc.",
            jurisdiction="US-CA",
            cik="0000320193",
            lei="HWUPKR0MPOU8FGXBT394",
            ticker="AAPL",
        )
        graph.add_entity(apple)
        
        # TSMC (primary foundry)
        tsmc = create_entity(
            name="Taiwan Semiconductor Manufacturing Company Limited",
            jurisdiction="TW",
            cik="0001046179",
            lei="549300KB6NK5SBD14S87",
            ticker="TSM",
        )
        graph.add_entity(tsmc)
        
        # Samsung foundry
        samsung = create_entity(
            name="Samsung Electronics Co., Ltd.",
            jurisdiction="KR",
            lei="9884007ER46L6N7EI764",
            ticker="005930",
        )
        graph.add_entity(samsung)
        
        # Broadcom (chip supplier)
        broadcom = create_entity(
            name="Broadcom Inc.",
            jurisdiction="US-DE",
            cik="0001730168",
            lei="549300WV6GIDOZJTV909",
            ticker="AVGO",
        )
        graph.add_entity(broadcom)
        
        # Qualcomm (modem supplier)
        qualcomm = create_entity(
            name="QUALCOMM Incorporated",
            jurisdiction="US-DE",
            cik="0000804328",
            lei="H1J8DDZKZP6H7RWC0H53",
            ticker="QCOM",
        )
        graph.add_entity(qualcomm)
        
        # ASML (equipment supplier to foundries)
        asml = create_entity(
            name="ASML Holding N.V.",
            jurisdiction="NL",
            cik="0000937966",
            lei="724500Y6DUVHQD6OXN27",
            ticker="ASML",
        )
        graph.add_entity(asml)
        
        # Apple → TSMC (foundry relationship)
        graph.add_relationship(
            apple.entity_id, tsmc.entity_id,
            RelationshipType.FABLESS_CLIENT,
            metadata={
                "products": ["A-series SoC", "M-series SoC"],
                "process_nodes": ["3nm", "5nm"],
                "exclusivity": "Leading edge exclusive",
                "revenue_significance": "TSMC's largest customer (~25%)",
            },
            source="TSMC Annual Report 2024",
            confidence=0.95,
        )
        
        # TSMC → Apple (inverse relationship)
        graph.add_relationship(
            tsmc.entity_id, apple.entity_id,
            RelationshipType.FOUNDRY,
            metadata={"relationship": "Primary foundry partner"},
            source="Apple 10-K Supplier Disclosure",
        )
        
        # Apple ← Broadcom (supplier)
        graph.add_relationship(
            broadcom.entity_id, apple.entity_id,
            RelationshipType.SUPPLIER,
            metadata={
                "products": ["WiFi chips", "Bluetooth chips", "Touch controllers"],
                "revenue_significance": "Broadcom: ~20% of revenue from Apple",
                "contract_value_usd": 15_000_000_000,
                "contract_period": "2023-2026",
            },
            source="Broadcom 10-K Customer Concentration",
        )
        
        # Apple ← Qualcomm (supplier)
        graph.add_relationship(
            qualcomm.entity_id, apple.entity_id,
            RelationshipType.SUPPLIER,
            metadata={
                "products": ["5G modems"],
                "end_date_estimate": "2025",  # Apple developing in-house
                "transition_status": "Phasing out",
            },
            source="Qualcomm 10-K, Apple announcement",
        )
        
        # TSMC ← ASML (equipment supplier)
        graph.add_relationship(
            asml.entity_id, tsmc.entity_id,
            RelationshipType.SUPPLIER,
            metadata={
                "products": ["EUV lithography systems", "DUV systems"],
                "equipment_value_per_unit_usd": 150_000_000,
                "strategic_importance": "Critical - only EUV supplier",
            },
            source="ASML Annual Report",
        )
        
        # Samsung also uses ASML
        graph.add_relationship(
            asml.entity_id, samsung.entity_id,
            RelationshipType.SUPPLIER,
            metadata={"products": ["EUV lithography systems"]},
        )
        
        # Verify supply chain
        apple_supply = graph.get_supply_chain(apple.entity_id)
        supplier_rels = graph.get_relationships(
            apple.entity_id, 
            RelationshipType.SUPPLIER, 
            "incoming"
        )
        assert len(supplier_rels) == 2  # Broadcom, Qualcomm
        
        foundry_rels = graph.get_relationships(
            apple.entity_id,
            RelationshipType.FOUNDRY,
            "incoming"
        )
        assert len(foundry_rels) == 1  # TSMC
    
    def test_nvidia_full_supply_chain(self):
        """
        NVIDIA's complete supply chain ecosystem.
        
        Design → Manufacturing → Assembly → Distribution → Customers
        
        NVIDIA (fabless design) 
        → TSMC (foundry - chip manufacturing)
        → ASE/Amkor (OSAT - packaging/assembly)
        → Distribution partners
        → End customers (hyperscalers, enterprises, gamers)
        """
        graph = EntityGraph()
        
        # NVIDIA
        nvidia = create_entity(
            name="NVIDIA Corporation",
            jurisdiction="US-DE",
            cik="0001045810",
            lei="549300S4KLFTLO7GSQ80",
            ticker="NVDA",
        )
        graph.add_entity(nvidia)
        
        # TSMC (foundry)
        tsmc = create_entity(
            name="Taiwan Semiconductor Manufacturing Company Limited",
            jurisdiction="TW",
            cik="0001046179",
            ticker="TSM",
        )
        graph.add_entity(tsmc)
        
        # ASE Technology (OSAT - packaging)
        ase = create_entity(
            name="ASE Technology Holding Co., Ltd.",
            jurisdiction="TW",
            cik="0001132804",
            ticker="ASX",
        )
        graph.add_entity(ase)
        
        # Amkor (OSAT - packaging)
        amkor = create_entity(
            name="Amkor Technology, Inc.",
            jurisdiction="US-AZ",
            cik="0001047127",
            ticker="AMKR",
        )
        graph.add_entity(amkor)
        
        # SK Hynix (HBM memory supplier)
        sk_hynix = create_entity(
            name="SK hynix Inc.",
            jurisdiction="KR",
            lei="549300W69N3YDRW9RH21",
            ticker="000660",
        )
        graph.add_entity(sk_hynix)
        
        # Micron (memory supplier)
        micron = create_entity(
            name="Micron Technology, Inc.",
            jurisdiction="US-DE",
            cik="0000723125",
            ticker="MU",
        )
        graph.add_entity(micron)
        
        # Major customers - Hyperscalers
        microsoft = create_entity(
            name="Microsoft Corporation",
            jurisdiction="US-WA",
            cik="0000789019",
            ticker="MSFT",
        )
        graph.add_entity(microsoft)
        
        meta = create_entity(
            name="Meta Platforms, Inc.",
            jurisdiction="US-DE",
            cik="0001326801",
            ticker="META",
        )
        graph.add_entity(meta)
        
        amazon = create_entity(
            name="Amazon.com, Inc.",
            jurisdiction="US-DE",
            cik="0001018724",
            ticker="AMZN",
        )
        graph.add_entity(amazon)
        
        # Supply chain relationships
        # NVIDIA → TSMC (foundry)
        graph.add_relationship(
            nvidia.entity_id, tsmc.entity_id,
            RelationshipType.FABLESS_CLIENT,
            metadata={
                "products": ["H100", "H200", "B100", "Blackwell"],
                "process_nodes": ["4nm", "3nm"],
                "capacity_allocation": "Priority customer",
            },
            source="NVIDIA 10-K, TSMC earnings calls",
        )
        
        # NVIDIA → ASE (packaging)
        graph.add_relationship(
            nvidia.entity_id, ase.entity_id,
            RelationshipType.CUSTOMER,
            metadata={
                "services": ["CoWoS packaging", "Advanced packaging"],
                "critical": True,
            },
        )
        
        # Memory suppliers → NVIDIA
        graph.add_relationship(
            sk_hynix.entity_id, nvidia.entity_id,
            RelationshipType.SUPPLIER,
            metadata={
                "products": ["HBM3", "HBM3e"],
                "significance": "Exclusive HBM supplier for certain SKUs",
            },
        )
        
        graph.add_relationship(
            micron.entity_id, nvidia.entity_id,
            RelationshipType.SUPPLIER,
            metadata={"products": ["HBM3e"]},
        )
        
        # Customers → NVIDIA
        for customer, metadata in [
            (microsoft, {"products": ["Azure AI", "Copilot infrastructure"]}),
            (meta, {"products": ["AI training", "Inference"]}),
            (amazon, {"products": ["AWS AI instances"]}),
        ]:
            graph.add_relationship(
                customer.entity_id, nvidia.entity_id,
                RelationshipType.CUSTOMER,
                metadata=metadata,
                source="NVIDIA 10-K customer disclosure",
            )
        
        # Verify multi-tier supply chain
        nvidia_suppliers = graph.get_relationships(
            nvidia.entity_id, RelationshipType.SUPPLIER, "incoming"
        )
        assert len(nvidia_suppliers) == 2  # SK Hynix, Micron
        
        nvidia_customers = graph.get_relationships(
            nvidia.entity_id, RelationshipType.CUSTOMER, "incoming"  
        )
        assert len(nvidia_customers) == 3  # Microsoft, Meta, Amazon


# =============================================================================
# LEVEL 4: EXPERT - Competitive Landscape & Strategic Relationships
# =============================================================================

class TestLevel4Expert:
    """
    EXPERT: Complex competitive and strategic relationships.
    
    Demonstrates:
    - Competitor identification with market segment specificity
    - Strategic partnerships and joint ventures
    - IP licensing relationships
    - Coopetition (companies that compete AND cooperate)
    """
    
    def test_semiconductor_competitive_landscape(self):
        """
        Semiconductor industry competitive landscape.
        
        Multiple market segments with different competitive dynamics:
        
        1. Logic (CPU/GPU):
           - Intel vs AMD vs NVIDIA vs Qualcomm
           
        2. Memory:
           - Samsung vs SK Hynix vs Micron
           
        3. Foundry:
           - TSMC vs Samsung vs Intel Foundry vs GlobalFoundries
           
        4. Equipment:
           - ASML (monopoly EUV) vs Applied Materials vs Lam Research vs Tokyo Electron
        """
        graph = EntityGraph()
        
        # === Logic Competitors ===
        intel = create_entity("Intel Corporation", jurisdiction="US-DE", ticker="INTC")
        amd = create_entity("Advanced Micro Devices, Inc.", jurisdiction="US-DE", ticker="AMD")
        nvidia = create_entity("NVIDIA Corporation", jurisdiction="US-DE", ticker="NVDA")
        qualcomm = create_entity("QUALCOMM Incorporated", jurisdiction="US-DE", ticker="QCOM")
        
        for entity in [intel, amd, nvidia, qualcomm]:
            graph.add_entity(entity)
        
        # Intel vs AMD (x86 CPU competition)
        graph.add_relationship(
            intel.entity_id, amd.entity_id,
            RelationshipType.COMPETITOR,
            metadata={
                "market_segment": "x86 CPUs",
                "sub_segments": ["Desktop", "Laptop", "Server"],
                "competitive_intensity": "High",
                "market_share_intel": 0.62,
                "market_share_amd": 0.38,
            },
            source="Mercury Research Q4 2024",
        )
        
        # NVIDIA vs AMD (GPU competition)
        graph.add_relationship(
            nvidia.entity_id, amd.entity_id,
            RelationshipType.COMPETITOR,
            metadata={
                "market_segment": "Discrete GPUs",
                "sub_segments": ["Gaming", "Data Center", "AI Training"],
                "competitive_intensity": "High in gaming, NVIDIA dominant in AI",
            },
        )
        
        # Intel vs NVIDIA (data center AI competition)
        graph.add_relationship(
            intel.entity_id, nvidia.entity_id,
            RelationshipType.COMPETITOR,
            metadata={
                "market_segment": "Data Center AI Accelerators",
                "intel_products": ["Gaudi", "Ponte Vecchio"],
                "nvidia_products": ["H100", "H200"],
                "competitive_status": "NVIDIA dominant",
            },
        )
        
        # === Foundry Competitors ===
        tsmc = create_entity("Taiwan Semiconductor Manufacturing Company Limited", jurisdiction="TW", ticker="TSM")
        samsung = create_entity("Samsung Electronics Co., Ltd.", jurisdiction="KR", ticker="005930")
        intel_foundry = create_entity("Intel Foundry Services", jurisdiction="US-DE")  # Subsidiary
        globalfoundries = create_entity("GlobalFoundries Inc.", jurisdiction="US-NY", ticker="GFS")
        
        for entity in [tsmc, samsung, globalfoundries]:
            graph.add_entity(entity)
        graph.add_entity(intel_foundry)
        
        # Link Intel Foundry to Intel parent
        graph.add_relationship(
            intel.entity_id, intel_foundry.entity_id,
            RelationshipType.PARENT,
            ownership_percentage=100.0,
        )
        
        # Foundry competition
        graph.add_relationship(
            tsmc.entity_id, samsung.entity_id,
            RelationshipType.COMPETITOR,
            metadata={
                "market_segment": "Advanced Node Foundry",
                "nodes": ["3nm", "5nm", "7nm"],
                "tsmc_share": 0.54,
                "samsung_share": 0.17,
            },
        )
        
        graph.add_relationship(
            tsmc.entity_id, intel_foundry.entity_id,
            RelationshipType.COMPETITOR,
            metadata={
                "market_segment": "Foundry Services",
                "status": "Intel entering market",
            },
        )
        
        # === Coopetition Examples ===
        # Intel USES TSMC (competitor) for some chips!
        graph.add_relationship(
            intel.entity_id, tsmc.entity_id,
            RelationshipType.FABLESS_CLIENT,
            metadata={
                "products": ["Meteor Lake tiles", "Arrow Lake tiles"],
                "irony": "Intel (foundry competitor) is TSMC customer",
                "strategy": "Disaggregated chiplet approach",
            },
        )
        
        # Samsung uses ASML (as does competitor TSMC)
        asml = create_entity("ASML Holding N.V.", jurisdiction="NL", ticker="ASML")
        graph.add_entity(asml)
        
        graph.add_relationship(
            asml.entity_id, tsmc.entity_id,
            RelationshipType.SUPPLIER,
            metadata={"products": ["EUV systems"]},
        )
        graph.add_relationship(
            asml.entity_id, samsung.entity_id,
            RelationshipType.SUPPLIER,
            metadata={"products": ["EUV systems"]},
        )
        graph.add_relationship(
            asml.entity_id, intel.entity_id,
            RelationshipType.SUPPLIER,
            metadata={"products": ["EUV systems", "High-NA EUV"]},
        )
        
        # Verify complex competitive relationships
        intel_competitors = graph.get_relationships(
            intel.entity_id, RelationshipType.COMPETITOR
        )
        assert len(intel_competitors) >= 2  # AMD, NVIDIA
        
        # Intel is BOTH a competitor to AND customer of TSMC
        intel_to_tsmc = [
            r for r in graph.relationships 
            if r.source_entity_id == intel.entity_id 
            and r.target_entity_id == tsmc.entity_id
        ]
        rel_types = {r.relationship_type for r in intel_to_tsmc}
        assert RelationshipType.FABLESS_CLIENT in rel_types  # Intel is a TSMC customer
    
    def test_joint_ventures_and_partnerships(self):
        """
        Joint ventures and strategic partnerships in semiconductors.
        
        Examples:
        1. Rapidus (Japan) - JV for advanced chip manufacturing
        2. IMEC - Multi-company R&D consortium
        3. Intel-Tower partnership
        """
        graph = EntityGraph()
        
        # Rapidus JV participants
        rapidus = create_entity(
            name="Rapidus Corporation",
            entity_type=EntityType.ORGANIZATION,
            jurisdiction="JP",
            # No public identifiers yet - private JV
        )
        graph.add_entity(rapidus)
        
        # JV investors
        toyota = create_entity("Toyota Motor Corporation", jurisdiction="JP", ticker="7203")
        sony = create_entity("Sony Group Corporation", jurisdiction="JP", ticker="6758")
        ntt = create_entity("Nippon Telegraph and Telephone Corporation", jurisdiction="JP", ticker="9432")
        
        for entity in [toyota, sony, ntt]:
            graph.add_entity(entity)
            graph.add_relationship(
                entity.entity_id, rapidus.entity_id,
                RelationshipType.JOINT_VENTURE,
                metadata={"purpose": "2nm chip manufacturing in Japan"},
                source="Rapidus announcement 2022",
            )
        
        # IBM technology partnership
        ibm = create_entity("International Business Machines Corporation", jurisdiction="US-NY", ticker="IBM")
        graph.add_entity(ibm)
        
        graph.add_relationship(
            ibm.entity_id, rapidus.entity_id,
            RelationshipType.LICENSOR,
            metadata={
                "technology": "2nm process technology",
                "developed_at": "Albany Nanotech",
            },
        )
        
        # IMEC R&D consortium
        imec = create_entity(
            name="Interuniversity Microelectronics Centre",
            entity_type=EntityType.RESEARCH_INSTITUTE if hasattr(EntityType, 'RESEARCH_INSTITUTE') else EntityType.ORGANIZATION,
            jurisdiction="BE",  # Belgium
        )
        graph.add_entity(imec)
        
        # Major IMEC partners
        asml = create_entity("ASML Holding N.V.", jurisdiction="NL", ticker="ASML")
        tsmc = create_entity("Taiwan Semiconductor Manufacturing Company Limited", jurisdiction="TW", ticker="TSM")
        intel = create_entity("Intel Corporation", jurisdiction="US-DE", ticker="INTC")
        samsung = create_entity("Samsung Electronics Co., Ltd.", jurisdiction="KR", ticker="005930")
        
        for partner in [asml, tsmc, intel, samsung]:
            graph.add_entity(partner)
            graph.add_relationship(
                partner.entity_id, imec.entity_id,
                RelationshipType.PARTNER,
                metadata={
                    "partnership_type": "R&D consortium member",
                    "focus_areas": ["EUV lithography", "Advanced packaging", "New materials"],
                },
            )
        
        # Verify JV structure
        rapidus_investors = graph.get_relationships(
            rapidus.entity_id, RelationshipType.JOINT_VENTURE, "incoming"
        )
        assert len(rapidus_investors) == 3  # Toyota, Sony, NTT
        
        # Verify IMEC partnerships
        imec_partners = graph.get_relationships(
            imec.entity_id, RelationshipType.PARTNER, "incoming"
        )
        assert len(imec_partners) == 4


# =============================================================================
# LEVEL 5: MINDBLOWING - Full Ecosystem with Private Companies
# =============================================================================

class TestLevel5Mindblowing:
    """
    MINDBLOWING: Complete semiconductor ecosystem including private companies,
    investment relationships, and complex ownership structures.
    
    Demonstrates:
    - Private company discovery from SEC filings
    - Venture capital and private equity relationships
    - Complex multi-entity transactions
    - Historical relationship tracking (M&A history)
    - Geographic supply chain mapping
    """
    
    def test_ai_chip_ecosystem_complete(self):
        """
        Complete AI chip ecosystem with public AND private companies.
        
        This models the ENTIRE value chain for AI chips:
        
        1. DESIGN TOOLS (EDA)
           - Synopsys, Cadence (public)
           - Ansys (simulation)
        
        2. IP LICENSING
           - ARM (public again), Rambus, Alphawave
           - PRIVATE: Arteris, Imagination Technologies
        
        3. CHIP DESIGN (Fabless)
           - NVIDIA, AMD, Qualcomm, Apple (public)
           - PRIVATE: Cerebras, Groq, SambaNova, Graphcore (now private)
        
        4. MANUFACTURING (Foundry)
           - TSMC, Samsung, Intel Foundry, GlobalFoundries
        
        5. EQUIPMENT
           - ASML, Applied Materials, Lam Research, KLA
           - PRIVATE: Aixtron suppliers
        
        6. MATERIALS
           - Entegris, Shin-Etsu
           - PRIVATE: Many specialty chemical suppliers
        
        7. PACKAGING (OSAT)
           - ASE, Amkor
        
        8. MEMORY
           - Samsung, SK Hynix, Micron
        
        9. END CUSTOMERS (Hyperscalers)
           - Microsoft, Google, Amazon, Meta
           - PRIVATE: OpenAI, Anthropic
        
        10. INVESTORS
            - SoftBank, Intel Capital, NVIDIA Ventures
            - PRIVATE: Sequoia, a16z, etc.
        """
        graph = EntityGraph()
        
        # === EDA TOOLS ===
        synopsys = create_entity(
            "Synopsys, Inc.", jurisdiction="US-DE",
            cik="0000883241", ticker="SNPS"
        )
        cadence = create_entity(
            "Cadence Design Systems, Inc.", jurisdiction="US-DE",
            cik="0000813672", ticker="CDNS"
        )
        graph.add_entity(synopsys)
        graph.add_entity(cadence)
        
        # === IP LICENSING ===
        arm = create_entity(
            "Arm Holdings plc", jurisdiction="GB",
            cik="0001973239", ticker="ARM"  # Re-IPO 2023
        )
        # Private IP companies
        arteris = create_entity(
            "Arteris, Inc.", 
            entity_type=EntityType.ORGANIZATION,
            jurisdiction="US-CA",
            # Private - no public identifiers
        )
        graph.add_entity(arm)
        graph.add_entity(arteris)
        
        # === AI CHIP STARTUPS (Private) ===
        cerebras = create_entity(
            "Cerebras Systems Inc.",
            entity_type=EntityType.ORGANIZATION,
            jurisdiction="US-CA",
            # Private - raised $4.1B
        )
        groq = create_entity(
            "Groq, Inc.",
            entity_type=EntityType.ORGANIZATION,
            jurisdiction="US-CA",
            # Private - founded by ex-Google TPU team
        )
        sambanova = create_entity(
            "SambaNova Systems, Inc.",
            entity_type=EntityType.ORGANIZATION,
            jurisdiction="US-CA",
            # Private
        )
        for startup in [cerebras, groq, sambanova]:
            graph.add_entity(startup)
        
        # === PUBLIC CHIP COMPANIES ===
        nvidia = create_entity("NVIDIA Corporation", jurisdiction="US-DE", cik="0001045810", ticker="NVDA")
        amd = create_entity("Advanced Micro Devices, Inc.", jurisdiction="US-DE", cik="0000002488", ticker="AMD")
        intel = create_entity("Intel Corporation", jurisdiction="US-DE", cik="0000050863", ticker="INTC")
        qualcomm = create_entity("QUALCOMM Incorporated", jurisdiction="US-DE", cik="0000804328", ticker="QCOM")
        
        for company in [nvidia, amd, intel, qualcomm]:
            graph.add_entity(company)
        
        # === FOUNDRIES ===
        tsmc = create_entity("Taiwan Semiconductor Manufacturing Company Limited", jurisdiction="TW", cik="0001046179", ticker="TSM")
        samsung = create_entity("Samsung Electronics Co., Ltd.", jurisdiction="KR", ticker="005930")
        globalfoundries = create_entity("GlobalFoundries Inc.", jurisdiction="US-NY", cik="0001840706", ticker="GFS")
        
        for foundry in [tsmc, samsung, globalfoundries]:
            graph.add_entity(foundry)
        
        # === EQUIPMENT ===
        asml = create_entity("ASML Holding N.V.", jurisdiction="NL", cik="0000937966", ticker="ASML")
        applied_materials = create_entity("Applied Materials, Inc.", jurisdiction="US-DE", cik="0000006951", ticker="AMAT")
        lam = create_entity("Lam Research Corporation", jurisdiction="US-DE", cik="0000707549", ticker="LRCX")
        kla = create_entity("KLA Corporation", jurisdiction="US-DE", cik="0000319201", ticker="KLAC")
        
        for equip in [asml, applied_materials, lam, kla]:
            graph.add_entity(equip)
        
        # === MEMORY ===
        sk_hynix = create_entity("SK hynix Inc.", jurisdiction="KR", ticker="000660")
        micron = create_entity("Micron Technology, Inc.", jurisdiction="US-DE", cik="0000723125", ticker="MU")
        
        graph.add_entity(sk_hynix)
        graph.add_entity(micron)
        
        # === HYPERSCALERS ===
        microsoft = create_entity("Microsoft Corporation", jurisdiction="US-WA", cik="0000789019", ticker="MSFT")
        google = create_entity("Alphabet Inc.", jurisdiction="US-DE", cik="0001652044", ticker="GOOGL")
        amazon = create_entity("Amazon.com, Inc.", jurisdiction="US-DE", cik="0001018724", ticker="AMZN")
        meta = create_entity("Meta Platforms, Inc.", jurisdiction="US-DE", cik="0001326801", ticker="META")
        
        for hyperscaler in [microsoft, google, amazon, meta]:
            graph.add_entity(hyperscaler)
        
        # === PRIVATE AI COMPANIES ===
        openai = create_entity(
            "OpenAI, Inc.",
            entity_type=EntityType.ORGANIZATION,
            jurisdiction="US-DE",
            # Private - unique capped-profit structure
        )
        anthropic = create_entity(
            "Anthropic, PBC",
            entity_type=EntityType.ORGANIZATION,
            jurisdiction="US-DE",
            # Private - Public Benefit Corporation
        )
        graph.add_entity(openai)
        graph.add_entity(anthropic)
        
        # === INVESTORS ===
        softbank = create_entity(
            "SoftBank Group Corp.",
            jurisdiction="JP",
            ticker="9984"
        )
        sequoia = create_entity(
            "Sequoia Capital Operations, LLC",
            entity_type=EntityType.ORGANIZATION,  # Fund structure
            jurisdiction="US-DE",
        )
        a16z = create_entity(
            "Andreessen Horowitz",
            entity_type=EntityType.ORGANIZATION,
            jurisdiction="US-DE",
        )
        
        for investor in [softbank, sequoia, a16z]:
            graph.add_entity(investor)
        
        # ===========================================
        # RELATIONSHIPS - This is where it gets complex
        # ===========================================
        
        # --- EDA → Chip Designers ---
        for designer in [nvidia, amd, cerebras, groq, sambanova, qualcomm]:
            graph.add_relationship(
                designer.entity_id, synopsys.entity_id,
                RelationshipType.CUSTOMER,
                metadata={"product": "Chip design tools"},
            )
            graph.add_relationship(
                designer.entity_id, cadence.entity_id,
                RelationshipType.CUSTOMER,
                metadata={"product": "Chip design tools"},
            )
        
        # --- IP Licensing ---
        # ARM licenses to everyone
        for licensee in [nvidia, qualcomm, apple := create_entity("Apple Inc.", jurisdiction="US-CA", cik="0000320193", ticker="AAPL")]:
            if not graph.get_entity(licensee.entity_id):
                graph.add_entity(licensee)
            graph.add_relationship(
                arm.entity_id, licensee.entity_id,
                RelationshipType.LICENSOR,
                metadata={"ip": "ARM architecture license"},
            )
        graph.add_entity(apple)
        
        # --- Foundry Relationships ---
        # NVIDIA uses TSMC exclusively
        graph.add_relationship(
            nvidia.entity_id, tsmc.entity_id,
            RelationshipType.FABLESS_CLIENT,
            metadata={
                "exclusivity": "Exclusive for leading edge",
                "nodes": ["4nm", "3nm"],
                "products": ["H100", "H200", "B100"],
            },
        )
        
        # AMD uses TSMC
        graph.add_relationship(
            amd.entity_id, tsmc.entity_id,
            RelationshipType.FABLESS_CLIENT,
            metadata={"nodes": ["5nm", "4nm"], "products": ["MI300", "EPYC"]},
        )
        
        # AI startups - various foundry relationships
        # Cerebras uses TSMC for wafer-scale chips
        graph.add_relationship(
            cerebras.entity_id, tsmc.entity_id,
            RelationshipType.FABLESS_CLIENT,
            metadata={
                "unique": "Wafer-scale integration",
                "chip_size": "46,225 mm²",
                "transistors": "2.6 trillion",
            },
        )
        
        # Groq uses GlobalFoundries
        graph.add_relationship(
            groq.entity_id, globalfoundries.entity_id,
            RelationshipType.FABLESS_CLIENT,
            metadata={"node": "14nm", "product": "LPU"},
        )
        
        # --- Equipment → Foundry ---
        # ASML supplies ALL advanced foundries (monopoly position)
        for foundry in [tsmc, samsung, intel]:
            graph.add_relationship(
                asml.entity_id, foundry.entity_id,
                RelationshipType.SUPPLIER,
                metadata={
                    "products": ["EUV lithography systems"],
                    "strategic_importance": "Critical - sole EUV supplier",
                    "price_per_system_usd": 150_000_000,
                },
            )
        
        # Other equipment suppliers
        for foundry in [tsmc, samsung, globalfoundries, intel]:
            for supplier in [applied_materials, lam, kla]:
                graph.add_relationship(
                    supplier.entity_id, foundry.entity_id,
                    RelationshipType.SUPPLIER,
                    metadata={"products": ["Deposition", "Etch", "Metrology"]},
                )
        
        # --- Memory → AI Chips ---
        # HBM is critical for AI chips
        for memory_supplier in [sk_hynix, micron]:
            graph.add_relationship(
                memory_supplier.entity_id, nvidia.entity_id,
                RelationshipType.SUPPLIER,
                metadata={
                    "products": ["HBM3", "HBM3e"],
                    "critical": True,
                    "supply_constrained": True,
                },
            )
        
        # --- Hyperscaler → AI Chip ---
        for hyperscaler in [microsoft, google, amazon, meta]:
            # All are NVIDIA customers
            graph.add_relationship(
                hyperscaler.entity_id, nvidia.entity_id,
                RelationshipType.CUSTOMER,
                metadata={"products": ["H100", "DGX systems"]},
                source="NVIDIA 10-K customer concentration",
            )
        
        # --- Private AI Company Relationships ---
        # OpenAI uses Microsoft Azure (and NVIDIA chips via Azure)
        graph.add_relationship(
            openai.entity_id, microsoft.entity_id,
            RelationshipType.PARTNER,
            metadata={
                "investment": 13_000_000_000,
                "infrastructure": "Azure exclusive",
                "equity_stake": "49%",
            },
            source="Microsoft 10-K, news reports",
        )
        
        graph.add_relationship(
            microsoft.entity_id, openai.entity_id,
            RelationshipType.INVESTOR,
            metadata={"total_investment_usd": 13_000_000_000},
        )
        
        # Anthropic has multiple investors
        graph.add_relationship(
            google.entity_id, anthropic.entity_id,
            RelationshipType.INVESTOR,
            metadata={"investment_usd": 2_000_000_000},
        )
        graph.add_relationship(
            amazon.entity_id, anthropic.entity_id,
            RelationshipType.INVESTOR,
            metadata={"investment_usd": 4_000_000_000},
        )
        
        # --- VC Investment in AI Chip Startups ---
        for startup in [cerebras, groq, sambanova]:
            graph.add_relationship(
                sequoia.entity_id, startup.entity_id,
                RelationshipType.INVESTOR,
                metadata={"stage": "Growth equity"},
            )
        
        # SoftBank ARM ownership
        graph.add_relationship(
            softbank.entity_id, arm.entity_id,
            RelationshipType.PARENT,
            ownership_percentage=90.0,  # Post-IPO
            metadata={"acquired": "2016", "ipo": "2023"},
        )
        
        # --- Competition ---
        # AI chip competition
        for competitor_pair in [
            (nvidia, amd, "Data center GPUs"),
            (nvidia, intel, "AI accelerators"),
            (nvidia, cerebras, "AI training chips"),
            (nvidia, groq, "AI inference chips"),
            (cerebras, groq, "Custom AI chips"),
            (cerebras, sambanova, "Custom AI chips"),
        ]:
            comp1, comp2, segment = competitor_pair
            graph.add_relationship(
                comp1.entity_id, comp2.entity_id,
                RelationshipType.COMPETITOR,
                metadata={"market_segment": segment},
            )
        
        # Foundry competition
        graph.add_relationship(
            tsmc.entity_id, samsung.entity_id,
            RelationshipType.COMPETITOR,
            metadata={
                "market_segment": "Advanced foundry",
                "tsmc_share": 0.54,
                "samsung_share": 0.17,
            },
        )
        
        # ===========================================
        # VERIFICATION
        # ===========================================
        
        # Total entities
        assert len(graph.entities) >= 25  # Many entities
        
        # Total relationships
        assert len(graph.relationships) >= 40  # Rich relationship graph
        
        # Check NVIDIA's position (should be central)
        nvidia_rels = graph.get_relationships(nvidia.entity_id)
        assert len(nvidia_rels) >= 10  # Many relationships
        
        # Verify private company representation
        private_companies = [
            e for e in graph.entities.values()
            if all(
                c.scheme not in [IdentifierScheme.CIK, IdentifierScheme.TICKER]
                for c in e.identifiers
            ) and e.identifiers  # Has some identifiers but no public ones
        ]
        # Note: Some entities have no identifiers at all (truly private)
        
        # Check investment chains
        anthropic_investors = graph.get_relationships(
            anthropic.entity_id, RelationshipType.INVESTOR, "incoming"
        )
        assert len(anthropic_investors) >= 2  # Google, Amazon
        
        # Print summary for inspection
        print(f"\n{'='*60}")
        print("AI CHIP ECOSYSTEM SUMMARY")
        print(f"{'='*60}")
        print(f"Total Entities: {len(graph.entities)}")
        print(f"Total Relationships: {len(graph.relationships)}")
        print()
        
        # Relationship breakdown
        rel_counts = {}
        for rel in graph.relationships:
            rel_counts[rel.relationship_type] = rel_counts.get(rel.relationship_type, 0) + 1
        
        print("Relationship Types:")
        for rel_type, count in sorted(rel_counts.items(), key=lambda x: -x[1]):
            print(f"  {rel_type.value}: {count}")
    
    def test_private_company_discovery_from_sec_filings(self):
        """
        Discover private companies from SEC filing disclosures.
        
        SEC filings often mention private companies:
        - 10-K risk factors: "We rely on sole-source suppliers..."
        - Exhibit 21: Complete subsidiary lists
        - 8-K: M&A announcements
        - Schedule 14A: Related party transactions
        
        This test demonstrates how to extract and model these relationships.
        """
        graph = EntityGraph()
        
        # Start with a public company
        nvidia = create_entity(
            "NVIDIA Corporation", jurisdiction="US-DE",
            cik="0001045810", ticker="NVDA"
        )
        graph.add_entity(nvidia)
        
        # === Discovered from NVIDIA 10-K Exhibit 21 (Subsidiaries) ===
        # These are REAL subsidiaries from NVIDIA's SEC filings
        
        nvidia_subs = [
            ("NVIDIA Holdings, LLC", "US-DE", 100.0),
            ("NVIDIA International, Inc.", "US-DE", 100.0),
            ("NVIDIA Technology UK Limited", "GB", 100.0),
            ("NVIDIA Semiconductor Co., Ltd.", "TW", 100.0),  # Taiwan entity!
            ("NVIDIA B.V.", "NL", 100.0),  # Netherlands holding
            ("NVIDIA GmbH", "DE", 100.0),  # Germany
            ("NVIDIA France SAS", "FR", 100.0),
            ("NVIDIA Development Pte. Ltd.", "SG", 100.0),  # Singapore
            ("Mellanox Technologies, Ltd.", "IL", 100.0),  # Acquired 2020
        ]
        
        for sub_name, jurisdiction, ownership in nvidia_subs:
            sub = create_entity(sub_name, jurisdiction=jurisdiction)
            graph.add_entity(sub)
            graph.add_relationship(
                nvidia.entity_id, sub.entity_id,
                RelationshipType.PARENT,
                ownership_percentage=ownership,
                source="NVIDIA 10-K FY2024 Exhibit 21",
            )
        
        # === Discovered from 10-K Risk Factors (Suppliers) ===
        # "We depend on sole or limited source suppliers"
        
        # These private companies are mentioned in risk factors
        private_suppliers = [
            {
                "name": "Ampere Computing LLC",
                "jurisdiction": "US-CA",
                "relationship": "Technology licensor",
                "mention": "ARM architecture licensing through Ampere relationship",
                "discoverable_from": "10-K supplier disclosures",
            },
            {
                "name": "Promex Industries, Inc.",  # Real OSAT subcontractor
                "jurisdiction": "US-CA", 
                "relationship": "Assembly subcontractor",
                "mention": "Specialty packaging services",
                "discoverable_from": "Supply chain analysis",
            },
        ]
        
        for supplier_info in private_suppliers:
            supplier = create_entity(
                supplier_info["name"],
                jurisdiction=supplier_info["jurisdiction"],
            )
            graph.add_entity(supplier)
            graph.add_relationship(
                supplier.entity_id, nvidia.entity_id,
                RelationshipType.SUPPLIER,
                metadata={
                    "discovered_from": supplier_info["discoverable_from"],
                    "relationship_type": supplier_info["relationship"],
                },
                source=supplier_info["discoverable_from"],
            )
        
        # === Discovered from 8-K M&A Announcements ===
        # Historical acquisitions reveal private company relationships
        
        acquisitions = [
            {
                "name": "Mellanox Technologies, Ltd.",
                "date": date(2020, 4, 27),
                "price_usd": 6_900_000_000,
                "8k_filing": "8-K April 27, 2020",
                "was_public": True,  # Had CIK before acquisition
            },
            {
                "name": "Cumulus Networks, Inc.",
                "date": date(2020, 5, 4),
                "price_usd": None,  # Undisclosed
                "8k_filing": "8-K May 4, 2020",
                "was_public": False,
            },
            {
                "name": "DeepMap, Inc.",
                "date": date(2021, 6, 10),
                "price_usd": None,
                "8k_filing": "8-K June 10, 2021",
                "was_public": False,
            },
        ]
        
        for acq in acquisitions:
            # Skip if already added as subsidiary
            existing = [e for e in graph.entities.values() if e.primary_name == acq["name"]]
            if existing:
                target = existing[0]
            else:
                target = create_entity(acq["name"])
                graph.add_entity(target)
            
            graph.add_relationship(
                nvidia.entity_id, target.entity_id,
                RelationshipType.SUCCESSOR,  # NVIDIA succeeded the acquired entity
                start_date=acq["date"],
                metadata={
                    "transaction_type": "Acquisition",
                    "price_usd": acq["price_usd"],
                    "source": acq["8k_filing"],
                    "was_public_pre_acquisition": acq["was_public"],
                },
                source=acq["8k_filing"],
            )
        
        # === Discovered from Schedule 14A (Related Parties) ===
        # Board member affiliations can reveal private company relationships
        
        board_affiliations = [
            {
                "person": "Jensen Huang",
                "entity_name": "Stanford University",
                "relationship": "Board of Trustees",
                "relevance": "Academic partnership, recruiting",
            },
            # Directors often sit on private company boards
        ]
        
        # === Summary ===
        subsidiaries = graph.get_relationships(
            nvidia.entity_id, RelationshipType.PARENT, "outgoing"
        )
        assert len(subsidiaries) >= 9  # Many subsidiaries
        
        acquisitions_rels = graph.get_relationships(
            nvidia.entity_id, RelationshipType.SUCCESSOR, "outgoing"
        )
        assert len(acquisitions_rels) >= 2  # At least Mellanox, Cumulus
        
        # Geographic distribution of subsidiaries
        jurisdictions = set()
        for rel in subsidiaries:
            sub = graph.get_entity(rel.target_entity_id)
            if sub and sub.jurisdiction:
                jurisdictions.add(sub.jurisdiction)
        
        print(f"\nNVIDIA Global Footprint: {len(jurisdictions)} jurisdictions")
        print(f"Jurisdictions: {sorted(jurisdictions)}")
        
        assert "US-DE" in jurisdictions
        assert "TW" in jurisdictions  # Taiwan
        assert "NL" in jurisdictions  # Netherlands
        assert "DE" in jurisdictions  # Germany


# =============================================================================
# LLM INTEGRATION FOR DATA POPULATION
# =============================================================================

class TestLLMDataPopulation:
    """
    Demonstrate how to use LLM to populate entity relationships.
    
    This would require API keys for production use.
    """
    
    @pytest.mark.skip(reason="Requires LLM API keys")
    def test_llm_entity_extraction(self):
        """
        Use LLM to extract entities and relationships from SEC filing text.
        
        Prompt engineering for entity extraction:
        1. Provide filing section (e.g., Risk Factors)
        2. Ask LLM to identify entities mentioned
        3. Ask LLM to classify relationship types
        4. Parse structured output
        """
        
        # Example prompt for extracting supplier relationships
        SUPPLIER_EXTRACTION_PROMPT = """
        You are analyzing an SEC 10-K filing to extract supplier relationships.
        
        Given the following text from the Risk Factors section, identify:
        1. Company names mentioned as suppliers
        2. The type of product/service they provide
        3. Whether they are a sole-source or multi-source supplier
        4. The criticality of the relationship (high/medium/low)
        
        Text:
        {filing_text}
        
        Respond in JSON format:
        {{
            "suppliers": [
                {{
                    "name": "Company Name",
                    "product_service": "What they provide",
                    "sole_source": true/false,
                    "criticality": "high/medium/low",
                    "evidence_quote": "Relevant quote from text"
                }}
            ]
        }}
        """
        
        # Example prompt for subsidiary extraction from Exhibit 21
        SUBSIDIARY_EXTRACTION_PROMPT = """
        You are parsing an SEC 10-K Exhibit 21 (Subsidiaries list).
        
        Given the following text, extract each subsidiary with:
        1. Legal name
        2. Jurisdiction of incorporation
        3. Percentage owned (if stated)
        4. Immediate parent (if not the filing company)
        
        Text:
        {exhibit_21_text}
        
        Respond in JSON format:
        {{
            "subsidiaries": [
                {{
                    "name": "Legal Entity Name",
                    "jurisdiction": "Country or State code",
                    "ownership_percentage": 100.0,
                    "immediate_parent": "Parent company name or null"
                }}
            ]
        }}
        """
        
        # Example: Would call LLM API here
        # response = llm.complete(SUPPLIER_EXTRACTION_PROMPT.format(filing_text=text))
        # suppliers = json.loads(response)
        
        pass
    
    def test_entity_relationship_schema_for_llm(self):
        """
        Define JSON schema for LLM to output structured relationship data.
        
        This schema can be used with function calling or structured output modes.
        """
        
        relationship_schema = {
            "type": "object",
            "properties": {
                "source_entity": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "entity_type": {"enum": ["corporation", "fund", "government", "person"]},
                        "jurisdiction": {"type": "string"},
                        "identifiers": {
                            "type": "object",
                            "properties": {
                                "cik": {"type": "string"},
                                "ticker": {"type": "string"},
                                "lei": {"type": "string"},
                            }
                        }
                    },
                    "required": ["name"]
                },
                "target_entity": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "entity_type": {"enum": ["corporation", "fund", "government", "person"]},
                        "jurisdiction": {"type": "string"},
                    },
                    "required": ["name"]
                },
                "relationship": {
                    "type": "object",
                    "properties": {
                        "type": {
                            "enum": [
                                "parent", "subsidiary", "customer", "supplier",
                                "competitor", "partner", "investor", "licensee"
                            ]
                        },
                        "ownership_percentage": {"type": "number"},
                        "start_date": {"type": "string", "format": "date"},
                        "evidence": {"type": "string"},
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    },
                    "required": ["type"]
                }
            },
            "required": ["source_entity", "target_entity", "relationship"]
        }
        
        # This schema can be used with OpenAI function calling, etc.
        assert "source_entity" in relationship_schema["properties"]
        assert "target_entity" in relationship_schema["properties"]
        assert "relationship" in relationship_schema["properties"]


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
