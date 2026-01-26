# py-sec-edgar Storage Schema v2

**Aligned with Entity Master v2 | Entity → Security → Listing Hierarchy**

---

## Executive Summary

This document updates py-sec-edgar's storage schema to integrate with **Entity Master v2**, which introduces the critical separation:

| Object | Scope | py-sec-edgar Uses |
|--------|-------|-------------------|
| **Entity** | Issuer/Organization | Filers, customers, suppliers, competitors |
| **Security** | Financial Instrument | 13F holdings, SEC-registered securities |
| **Listing** | Trading Venue | Ticker lookups, price references |

**Key Changes from v1:**
- Entity resolution now goes through Entity Master v2
- py-sec-edgar stores **references** to Entity Master IDs
- Mentions link to Entity Master's canonical IDs
- Relationships are stored in Entity Master, py-sec-edgar only reads

---

## Architecture: py-sec-edgar + Entity Master v2

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                         py-sec-edgar v4 + ENTITY MASTER v2                               │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                          │
│  ┌───────────────────────────────────────────────────────────────────────────────────┐  │
│  │                              py-sec-edgar (Consumer)                               │  │
│  │                                                                                    │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │  │
│  │  │   FILINGS    │  │   SECTIONS   │  │   SIGDEV     │  │  EXTRACTED   │           │  │
│  │  │   Storage    │  │   Storage    │  │   Events     │  │  Mentions    │           │  │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘           │  │
│  │         │                 │                 │                 │                    │  │
│  │         │   References entity_id, security_id, listing_id     │                    │  │
│  │         └─────────────────┴────────┬────────┴─────────────────┘                    │  │
│  │                                    │                                               │  │
│  └────────────────────────────────────┼───────────────────────────────────────────────┘  │
│                                       │                                                  │
│                                       ▼  EntityResolverPort                              │
│  ┌───────────────────────────────────────────────────────────────────────────────────┐  │
│  │                           Entity Master v2 (Service)                               │  │
│  │                                                                                    │  │
│  │  ┌──────────────┐        ┌──────────────┐        ┌──────────────┐                 │  │
│  │  │   ENTITIES   │ ──1:N──│  SECURITIES  │ ──1:N──│   LISTINGS   │                 │  │
│  │  │  (Issuers)   │        │ (Instruments)│        │  (Venues)    │                 │  │
│  │  └──────┬───────┘        └──────┬───────┘        └──────┬───────┘                 │  │
│  │         │                       │                       │                          │  │
│  │  ┌──────┴───────┐        ┌──────┴───────┐        ┌──────┴───────┐                 │  │
│  │  │ identifiers  │        │ identifiers  │        │ identifiers  │                 │  │
│  │  │ CIK, LEI,    │        │ ISIN, CUSIP, │        │ RIC, BBG_    │                 │  │
│  │  │ EIN, DUNS    │        │ FIGI, SEDOL  │        │ TICKER       │                 │  │
│  │  └──────────────┘        └──────────────┘        └──────────────┘                 │  │
│  │                                                                                    │  │
│  │  ┌──────────────────────────────────────────────────────────────────────────────┐ │  │
│  │  │                         RELATIONSHIPS & MENTIONS                              │ │  │
│  │  │   py-sec-edgar pushes extracted relationships to Entity Master               │ │  │
│  │  │   Entity Master owns the canonical relationship graph                        │ │  │
│  │  └──────────────────────────────────────────────────────────────────────────────┘ │  │
│  │                                                                                    │  │
│  └───────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## py-sec-edgar Schema v2

### Filing Tables (Core Storage)

```sql
-- =============================================================================
-- FILINGS: SEC filing submissions
-- References Entity Master entity_id for the filer
-- =============================================================================
CREATE TABLE filings (
    filing_id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Entity Master reference (ULID from Entity Master v2)
    filer_entity_id         CHAR(26) NOT NULL,  -- References Entity Master entities.entity_id
    
    -- SEC identifiers (kept locally for fast queries)
    cik                     CHAR(10) NOT NULL,  -- Denormalized for performance
    accession_number        VARCHAR(25) UNIQUE NOT NULL,
    
    -- Filing details
    form_type               VARCHAR(20) NOT NULL,
    filed_date              DATE NOT NULL,
    accepted_at             TIMESTAMPTZ,
    period_of_report        DATE,
    
    -- 8-K specific
    items_reported          VARCHAR(10)[],
    
    -- Document info
    primary_document        VARCHAR(255),
    file_number             VARCHAR(25),
    film_number             VARCHAR(25),
    
    -- Status
    is_amendment            BOOLEAN DEFAULT FALSE,
    amendment_type          VARCHAR(20),  -- '/A', '/A-2', etc.
    
    -- Storage
    storage_path            VARCHAR(500),
    content_hash            VARCHAR(64),
    
    -- Timestamps
    created_at              TIMESTAMPTZ DEFAULT NOW(),
    updated_at              TIMESTAMPTZ DEFAULT NOW(),
    last_indexed_at         TIMESTAMPTZ
);

CREATE INDEX idx_filings_entity ON filings(filer_entity_id);
CREATE INDEX idx_filings_cik ON filings(cik);
CREATE INDEX idx_filings_form_date ON filings(form_type, filed_date DESC);
CREATE INDEX idx_filings_date ON filings(filed_date DESC);
CREATE INDEX idx_filings_accession ON filings(accession_number);
```

### Section Tables (Extracted Content)

```sql
-- =============================================================================
-- EXTRACTED_SECTIONS: Parsed sections from filings
-- =============================================================================
CREATE TABLE extracted_sections (
    section_id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filing_id               UUID NOT NULL REFERENCES filings(filing_id),
    
    -- Section identification
    section_type            VARCHAR(50) NOT NULL,  -- 'ITEM_1', 'ITEM_1A', 'EXHIBIT_21', etc.
    section_title           VARCHAR(255),
    item_number             VARCHAR(10),           -- '1', '1A', '7', '1.01', etc.
    
    -- Content
    content_text            TEXT,
    content_html            TEXT,
    
    -- Position in source document
    char_start              INT,
    char_end                INT,
    page_start              INT,
    page_end                INT,
    
    -- Metrics
    word_count              INT,
    sentence_count          INT,
    
    -- Extraction metadata
    extraction_method       VARCHAR(20) NOT NULL,  -- 'regex', 'ml', 'manual'
    extraction_confidence   DECIMAL(3,2),
    extractor_version       VARCHAR(20),
    
    -- Timestamps
    extracted_at            TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT chk_section_type CHECK (section_type IN (
        -- 10-K/10-Q items
        'ITEM_1', 'ITEM_1A', 'ITEM_1B', 'ITEM_1C', 'ITEM_2', 'ITEM_3',
        'ITEM_4', 'ITEM_5', 'ITEM_6', 'ITEM_7', 'ITEM_7A', 'ITEM_8',
        'ITEM_9', 'ITEM_9A', 'ITEM_9B', 'ITEM_10', 'ITEM_11', 'ITEM_12',
        'ITEM_13', 'ITEM_14', 'ITEM_15',
        -- 8-K items
        'ITEM_1_01', 'ITEM_1_02', 'ITEM_1_03', 'ITEM_1_04', 'ITEM_1_05',
        'ITEM_2_01', 'ITEM_2_02', 'ITEM_2_03', 'ITEM_2_04', 'ITEM_2_05', 'ITEM_2_06',
        'ITEM_3_01', 'ITEM_3_02', 'ITEM_3_03',
        'ITEM_4_01', 'ITEM_4_02',
        'ITEM_5_01', 'ITEM_5_02', 'ITEM_5_03', 'ITEM_5_04', 'ITEM_5_05',
        'ITEM_5_06', 'ITEM_5_07', 'ITEM_5_08',
        'ITEM_6_01', 'ITEM_6_02', 'ITEM_6_03', 'ITEM_6_04', 'ITEM_6_05',
        'ITEM_6_06', 'ITEM_6_07', 'ITEM_6_08', 'ITEM_6_09', 'ITEM_6_10',
        'ITEM_7_01', 'ITEM_8_01', 'ITEM_9_01',
        -- DEF 14A sections
        'PROXY_EXECUTIVE_COMP', 'PROXY_DIRECTORS', 'PROXY_OWNERSHIP',
        -- Exhibits
        'EXHIBIT_10', 'EXHIBIT_21', 'EXHIBIT_23', 'EXHIBIT_31', 'EXHIBIT_32',
        'EXHIBIT_99_1', 'EXHIBIT_99_2',
        -- Other
        'FULL_TEXT', 'PREAMBLE', 'SIGNATURES', 'OTHER'
    ))
);

CREATE INDEX idx_sections_filing ON extracted_sections(filing_id);
CREATE INDEX idx_sections_type ON extracted_sections(section_type);
CREATE INDEX idx_sections_item ON extracted_sections(item_number);
```

### Entity Mentions (References Entity Master)

```sql
-- =============================================================================
-- ENTITY_MENTIONS: Where entities are mentioned in filings
-- Entity IDs reference Entity Master v2 canonical IDs
-- =============================================================================
CREATE TABLE entity_mentions (
    mention_id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- What was mentioned (Entity Master v2 references)
    entity_id               CHAR(26),      -- Entity Master entities.entity_id
    security_id             CHAR(26),      -- Entity Master securities.security_id
    listing_id              CHAR(26),      -- Entity Master listings.listing_id
    
    -- Where mentioned
    filing_id               UUID NOT NULL REFERENCES filings(filing_id),
    section_id              UUID REFERENCES extracted_sections(section_id),
    
    -- The mention itself
    mention_text            VARCHAR(500) NOT NULL,
    mention_type            VARCHAR(30) NOT NULL,  -- 'company', 'person', 'ticker', 'product'
    
    -- Position
    char_start              INT,
    char_end                INT,
    sentence_context        TEXT,
    
    -- Resolution metadata
    resolution_status       VARCHAR(20) DEFAULT 'pending',  -- 'resolved', 'pending', 'unresolved', 'manual'
    resolution_confidence   DECIMAL(3,2),
    resolution_method       VARCHAR(30),  -- 'exact', 'fuzzy', 'llm', 'manual'
    
    -- If unresolved, store provisional entity
    provisional_entity_id   CHAR(26),      -- Entity Master provisional entity
    
    -- Timestamps
    mentioned_at            TIMESTAMPTZ,   -- Filing date
    extracted_at            TIMESTAMPTZ DEFAULT NOW(),
    resolved_at             TIMESTAMPTZ,
    
    -- At least one entity reference should be set for resolved mentions
    CONSTRAINT chk_mention_entity CHECK (
        resolution_status != 'resolved' OR (
            entity_id IS NOT NULL OR 
            security_id IS NOT NULL OR 
            listing_id IS NOT NULL
        )
    )
);

CREATE INDEX idx_mentions_entity ON entity_mentions(entity_id) WHERE entity_id IS NOT NULL;
CREATE INDEX idx_mentions_security ON entity_mentions(security_id) WHERE security_id IS NOT NULL;
CREATE INDEX idx_mentions_filing ON entity_mentions(filing_id);
CREATE INDEX idx_mentions_section ON entity_mentions(section_id);
CREATE INDEX idx_mentions_status ON entity_mentions(resolution_status);
CREATE INDEX idx_mentions_text ON entity_mentions(mention_text);
```

### SIGDEV Events (References Entity Master)

```sql
-- =============================================================================
-- SIGDEV_EVENTS: Extracted corporate events
-- Entity references point to Entity Master v2
-- =============================================================================
CREATE TABLE sigdev_events (
    event_id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type              VARCHAR(50) NOT NULL,  -- MGMT_APPOINTMENT, MA_ACQUISITION, etc.
    
    -- Issuer (the filing company)
    issuer_entity_id        CHAR(26) NOT NULL,     -- Entity Master entity_id
    
    -- Source
    filing_id               UUID NOT NULL REFERENCES filings(filing_id),
    section_id              UUID REFERENCES extracted_sections(section_id),
    
    -- Scoring
    confidence              DECIMAL(3,2) NOT NULL,
    significance            DECIMAL(3,2) NOT NULL,
    significance_bin        VARCHAR(10) GENERATED ALWAYS AS (
        CASE 
            WHEN significance >= 0.7 THEN 'HIGH'
            WHEN significance >= 0.4 THEN 'MEDIUM'
            ELSE 'LOW'
        END
    ) STORED,
    
    -- Evidence
    evidence_text           TEXT NOT NULL,
    source_span_start       INT,
    source_span_end         INT,
    
    -- Extraction
    parse_mode              VARCHAR(20) NOT NULL,  -- 'regex', 'ml', 'hybrid'
    rule_name               VARCHAR(100),
    
    -- Event-specific payload
    payload                 JSONB NOT NULL DEFAULT '{}',
    
    -- Timing
    effective_date          DATE,
    announced_date          DATE,
    
    -- Deduplication
    content_hash            VARCHAR(64) NOT NULL,
    cluster_id              UUID,
    is_primary              BOOLEAN DEFAULT TRUE,
    
    -- Timestamps
    detected_at             TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT chk_event_type CHECK (event_type IN (
        -- Governance
        'MGMT_APPOINTMENT', 'MGMT_RESIGNATION', 'MGMT_TERMINATION',
        'BOARD_APPOINTMENT', 'BOARD_RESIGNATION',
        'AUDITOR_CHANGE', 'AUDIT_OPINION',
        -- Financial
        'GUIDANCE_UPDATE', 'NON_GAAP_DISCLOSURE',
        'DEBT_NEW', 'DEBT_AMEND', 'DEBT_COVENANT',
        'EQUITY_ISSUANCE', 'CONVERTIBLE_ISSUANCE',
        'BUYBACK_AUTH', 'BUYBACK_ACTIVITY', 'DIVIDEND_DECLARED',
        'GOING_CONCERN_WARNING', 'RESTATEMENT_NONRELIANCE',
        -- Business
        'MA_ACQUISITION', 'MA_DISPOSAL', 'MA_TERMINATION',
        'SEGMENT_REORG',
        'CUSTOMER_CONCENTRATION', 'SUPPLIER_CONCENTRATION',
        'KPI_DISCLOSURE',
        'LEGAL_PROCEEDING', 'SETTLEMENT',
        'CYBER_INCIDENT', 'SECURITY_POSTURE_UPDATE',
        'SANCTIONS_EXPORT_CONTROL', 'SUBSIDIARY_UPDATE',
        -- Ownership
        'BENEFICIAL_OWNERSHIP_CHANGE', 'INSIDER_TRANSACTION', 'INSTITUTIONAL_POSITION_CHANGE'
    ))
);

CREATE INDEX idx_events_issuer ON sigdev_events(issuer_entity_id);
CREATE INDEX idx_events_type ON sigdev_events(event_type);
CREATE INDEX idx_events_filing ON sigdev_events(filing_id);
CREATE INDEX idx_events_significance ON sigdev_events(significance_bin, detected_at DESC);
CREATE INDEX idx_events_payload ON sigdev_events USING GIN(payload);

-- =============================================================================
-- EVENT_ENTITY_LINKS: Links events to involved entities
-- Uses Entity Master v2 entity/security/listing IDs
-- =============================================================================
CREATE TABLE event_entity_links (
    link_id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id                UUID NOT NULL REFERENCES sigdev_events(event_id) ON DELETE CASCADE,
    
    -- Entity Master v2 references (one should be set)
    entity_id               CHAR(26),
    security_id             CHAR(26),
    listing_id              CHAR(26),
    
    -- Role in the event
    role                    VARCHAR(50) NOT NULL,  -- subject, target, acquirer, customer, supplier, person
    is_primary              BOOLEAN DEFAULT FALSE,
    
    -- Resolution
    resolution_confidence   DECIMAL(3,2),
    
    created_at              TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_event_links_event ON event_entity_links(event_id);
CREATE INDEX idx_event_links_entity ON event_entity_links(entity_id) WHERE entity_id IS NOT NULL;
CREATE INDEX idx_event_links_role ON event_entity_links(role);
```

---

## Relationship Flow: py-sec-edgar → Entity Master v2

py-sec-edgar extracts relationships from filings and pushes them to Entity Master:

```python
"""
Relationship extraction flow with Entity Master v2.
"""
from py_sec_edgar.ports.entity_resolver import EntityResolverPort
from entity_master.api.relationships import RelationshipType, RelationshipEvidence


async def extract_and_store_relationships(
    filing: Filing,
    section: ExtractedSection,
    entity_resolver: EntityResolverPort,
):
    """
    Extract relationships from a filing section and push to Entity Master.
    """
    # 1. Extract customer concentration mentions
    concentrations = extract_customer_concentrations(section.content_text)
    
    for conc in concentrations:
        # 2. Resolve the customer to Entity Master entity
        customer_result = await entity_resolver.resolve(
            query=conc.customer_name,
            scope="entity",
            min_confidence=0.7,
            create_provisional=True,  # Create provisional if not found
        )
        
        if not customer_result.success:
            continue
        
        # 3. Push relationship to Entity Master
        await entity_resolver.add_relationship(
            source_entity_id=filing.filer_entity_id,
            target_entity_id=customer_result.entity.entity_id,
            relationship_type=RelationshipType.SUPPLIES_TO,
            evidence=RelationshipEvidence(
                source_system="py_sec_edgar",
                source_id=str(filing.filing_id),
                source_section=section.section_type,
                evidence_text=conc.evidence_text,
                confidence=conc.confidence,
            ),
            metrics={
                "revenue_pct": conc.revenue_pct,
                "period": conc.fiscal_period,
            },
        )


async def extract_and_store_competitor(
    filing: Filing,
    section: ExtractedSection,
    competitor_name: str,
    segment: str,
    entity_resolver: EntityResolverPort,
):
    """
    Extract competitor relationship and push to Entity Master.
    """
    # Resolve competitor entity
    competitor = await entity_resolver.resolve(
        query=competitor_name,
        scope="entity",
        create_provisional=True,
    )
    
    if competitor.success:
        await entity_resolver.add_relationship(
            source_entity_id=filing.filer_entity_id,
            target_entity_id=competitor.entity.entity_id,
            relationship_type=RelationshipType.COMPETES_WITH,
            evidence=RelationshipEvidence(
                source_system="py_sec_edgar",
                source_id=str(filing.filing_id),
                source_section=section.section_type,
                evidence_text=f"Competition identified in {section.section_type}",
            ),
            metrics={"segment": segment},
            bidirectional=True,  # A competes with B = B competes with A
        )
```

---

## Entity Resolution Integration

### EntityResolverPort Interface

py-sec-edgar uses a port interface to interact with Entity Master v2:

```python
# py_sec_edgar/ports/entity_resolver.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Literal


@dataclass
class ResolvedEntity:
    """Entity resolved via Entity Master v2."""
    # Canonical IDs (ULID from Entity Master)
    entity_id: Optional[str] = None
    security_id: Optional[str] = None
    listing_id: Optional[str] = None
    
    # Basic info
    name: str = ""
    entity_type: str = "UNKNOWN"
    
    # Key identifiers
    cik: Optional[str] = None
    lei: Optional[str] = None
    ticker: Optional[str] = None
    isin: Optional[str] = None
    
    # Resolution metadata
    confidence: float = 1.0
    was_merged: bool = False
    is_provisional: bool = False


@dataclass
class ResolutionResult:
    success: bool
    entity: Optional[ResolvedEntity] = None
    candidates: Optional[list[ResolvedEntity]] = None
    error: Optional[str] = None


class EntityResolverPort(ABC):
    """
    Port interface for Entity Master v2 integration.
    """
    
    @abstractmethod
    async def resolve(
        self,
        query: str,
        scope: Literal["entity", "security", "listing"] = "entity",
        min_confidence: float = 0.7,
        create_provisional: bool = False,
    ) -> ResolutionResult:
        """Resolve any identifier or name to Entity Master canonical record."""
        pass
    
    @abstractmethod
    async def resolve_cik(self, cik: str) -> ResolutionResult:
        """Direct CIK lookup (entity scope)."""
        pass
    
    @abstractmethod
    async def resolve_ticker(
        self, 
        ticker: str, 
        mic: Optional[str] = None,
        as_of_date: Optional[str] = None,
    ) -> ResolutionResult:
        """Ticker lookup (listing scope → security → entity)."""
        pass
    
    @abstractmethod
    async def resolve_isin(self, isin: str) -> ResolutionResult:
        """ISIN lookup (security scope → entity)."""
        pass
    
    @abstractmethod
    async def get_entity(self, entity_id: str) -> Optional[ResolvedEntity]:
        """Get entity by Entity Master entity_id."""
        pass
    
    @abstractmethod
    async def add_relationship(
        self,
        source_entity_id: str,
        target_entity_id: str,
        relationship_type: str,
        evidence: dict,
        metrics: Optional[dict] = None,
        bidirectional: bool = False,
    ) -> str:
        """
        Push extracted relationship to Entity Master.
        Returns relationship_id.
        """
        pass
    
    @abstractmethod
    async def record_mention(
        self,
        entity_id: str,
        filing_id: str,
        section_id: Optional[str],
        mention_text: str,
        context: str,
        confidence: float,
    ) -> str:
        """Record entity mention in Entity Master."""
        pass
```

---

## Views and Queries

### Filing View with Entity Info

```sql
-- Join filings with Entity Master data (requires cross-database query or cache)
CREATE VIEW v_filings_with_entity AS
SELECT 
    f.filing_id,
    f.filer_entity_id,
    f.cik,
    f.accession_number,
    f.form_type,
    f.filed_date,
    f.items_reported,
    -- Entity info would come from Entity Master cache or materialized view
    ec.primary_name AS filer_name,
    ec.ticker AS filer_ticker,
    ec.sic_code AS filer_sic
FROM filings f
LEFT JOIN entity_cache ec ON ec.entity_id = f.filer_entity_id;

-- Entity cache (materialized from Entity Master)
CREATE TABLE entity_cache (
    entity_id               CHAR(26) PRIMARY KEY,
    primary_name            VARCHAR(500),
    legal_name              VARCHAR(500),
    cik                     CHAR(10),
    lei                     CHAR(20),
    ticker                  VARCHAR(20),
    sic_code                CHAR(4),
    entity_type             VARCHAR(30),
    status                  VARCHAR(20),
    last_synced_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_entity_cache_cik ON entity_cache(cik);
CREATE INDEX idx_entity_cache_ticker ON entity_cache(ticker);
```

### SIGDEV Events with Entity Info

```sql
-- Events with resolved entity information
SELECT 
    e.event_id,
    e.event_type,
    e.significance,
    e.confidence,
    e.effective_date,
    e.evidence_text,
    e.payload,
    -- Issuer
    ec.primary_name AS issuer_name,
    ec.ticker AS issuer_ticker,
    -- Target (for M&A events)
    (SELECT ec2.primary_name 
     FROM event_entity_links eel 
     JOIN entity_cache ec2 ON ec2.entity_id = eel.entity_id
     WHERE eel.event_id = e.event_id AND eel.role = 'target'
     LIMIT 1) AS target_name
FROM sigdev_events e
JOIN entity_cache ec ON ec.entity_id = e.issuer_entity_id
WHERE e.significance >= 0.7
ORDER BY e.detected_at DESC;
```

### Customer Concentration Analysis

```sql
-- Find companies with high customer concentration
-- This queries Entity Master relationships
WITH concentrations AS (
    SELECT 
        e.event_id,
        e.issuer_entity_id,
        e.payload->>'customer_name' AS customer_name,
        (e.payload->>'value_pct')::DECIMAL AS revenue_pct,
        eel.entity_id AS customer_entity_id
    FROM sigdev_events e
    LEFT JOIN event_entity_links eel ON (
        eel.event_id = e.event_id 
        AND eel.role = 'customer'
    )
    WHERE e.event_type = 'CUSTOMER_CONCENTRATION'
)
SELECT 
    ec_issuer.primary_name AS company,
    ec_issuer.ticker,
    c.customer_name,
    ec_customer.primary_name AS customer_resolved,
    c.revenue_pct
FROM concentrations c
JOIN entity_cache ec_issuer ON ec_issuer.entity_id = c.issuer_entity_id
LEFT JOIN entity_cache ec_customer ON ec_customer.entity_id = c.customer_entity_id
WHERE c.revenue_pct >= 10
ORDER BY c.revenue_pct DESC;
```

---

## Data Sync with Entity Master

### Webhook Handler

```python
"""
Handle Entity Master webhooks for data sync.
"""
from fastapi import APIRouter, Request
from datetime import datetime

router = APIRouter()


@router.post("/webhooks/entity-master")
async def handle_entity_master_webhook(request: Request):
    """
    Handle Entity Master change notifications.
    
    Events:
    - entity.created
    - entity.updated  
    - entity.merged
    - entity.deactivated
    - relationship.added
    - relationship.removed
    """
    payload = await request.json()
    event_type = payload.get("event_type")
    
    if event_type == "entity.merged":
        # Update all references from old ID to new ID
        old_id = payload["from_entity_id"]
        new_id = payload["to_entity_id"]
        
        await update_entity_references(old_id, new_id)
        await refresh_entity_cache(new_id)
    
    elif event_type == "entity.updated":
        entity_id = payload["entity_id"]
        await refresh_entity_cache(entity_id)
    
    elif event_type == "entity.created":
        entity_id = payload["entity_id"]
        await add_to_entity_cache(entity_id)
    
    return {"status": "ok"}


async def update_entity_references(old_id: str, new_id: str):
    """Update all foreign keys when entity is merged."""
    
    # Update filings
    await db.execute("""
        UPDATE filings SET filer_entity_id = $1 
        WHERE filer_entity_id = $2
    """, new_id, old_id)
    
    # Update events
    await db.execute("""
        UPDATE sigdev_events SET issuer_entity_id = $1 
        WHERE issuer_entity_id = $2
    """, new_id, old_id)
    
    # Update event links
    await db.execute("""
        UPDATE event_entity_links SET entity_id = $1 
        WHERE entity_id = $2
    """, new_id, old_id)
    
    # Update mentions
    await db.execute("""
        UPDATE entity_mentions SET entity_id = $1 
        WHERE entity_id = $2
    """, new_id, old_id)
```

---

## Migration from v1

### Step 1: Add Entity Master ID Columns

```sql
-- Add entity_id columns to existing tables
ALTER TABLE filings ADD COLUMN filer_entity_id CHAR(26);
ALTER TABLE sigdev_events ADD COLUMN issuer_entity_id CHAR(26);
ALTER TABLE entity_mentions ADD COLUMN entity_id CHAR(26);
ALTER TABLE entity_mentions ADD COLUMN security_id CHAR(26);
ALTER TABLE entity_mentions ADD COLUMN listing_id CHAR(26);
```

### Step 2: Resolve Existing CIKs

```python
async def migrate_ciks_to_entity_master():
    """Resolve all existing CIKs to Entity Master entity_ids."""
    
    # Get unique CIKs
    ciks = await db.fetch("SELECT DISTINCT cik FROM filings")
    
    for row in ciks:
        cik = row["cik"]
        
        # Resolve via Entity Master
        result = await entity_resolver.resolve_cik(cik)
        
        if result.success:
            entity_id = result.entity.entity_id
            
            # Update filings
            await db.execute("""
                UPDATE filings SET filer_entity_id = $1 WHERE cik = $2
            """, entity_id, cik)
            
            # Update events
            await db.execute("""
                UPDATE sigdev_events e
                SET issuer_entity_id = $1
                FROM filings f
                WHERE e.filing_id = f.filing_id AND f.cik = $2
            """, entity_id, cik)
```

### Step 3: Add Constraints

```sql
-- After migration, make entity_id required
ALTER TABLE filings ALTER COLUMN filer_entity_id SET NOT NULL;
ALTER TABLE sigdev_events ALTER COLUMN issuer_entity_id SET NOT NULL;
```

---

## Related Documents

| Document | Description |
|----------|-------------|
| [entity_master_v2/01_CANONICAL_DATA_MODEL.md](entity_master_v2/01_CANONICAL_DATA_MODEL.md) | Entity → Security → Listing hierarchy |
| [entity_master_v2/02_RESOLUTION_AND_MERGE_WORKFLOWS.md](entity_master_v2/02_RESOLUTION_AND_MERGE_WORKFLOWS.md) | Identifier detection & merge handling |
| [entity_master_v2/03_VENDOR_CROSSWALK_AND_CONFLICTS.md](entity_master_v2/03_VENDOR_CROSSWALK_AND_CONFLICTS.md) | Vendor ID mapping & conflict resolution |
| [entity_master/13_PYSECEDGAR_PORT.md](entity_master/13_PYSECEDGAR_PORT.md) | EntityResolverPort interface design |
| [12_SIGDEV_EVENT_STORAGE.md](12_SIGDEV_EVENT_STORAGE.md) | Full SIGDEV event taxonomy |

---

*Document version: 2.0.0*
*Last updated: 2025-01-25*
*Aligned with: Entity Master v2*
