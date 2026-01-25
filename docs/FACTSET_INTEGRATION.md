# FactSet Data Integration for EntitySpine

## Overview

This document maps FactSet Standard Data Feed content to EntitySpine's entity management needs. EntitySpine handles entity resolution, identifier crosswalks, corporate hierarchy, and knowledge graph construction—all areas where FactSet data provides significant value.

## EntitySpine Core Concepts → FactSet Feeds

| EntitySpine Concept | FactSet Feed | Key Value |
|---------------------|--------------|-----------|
| **Entity** (company/org) | Symbology, Reference Hub | Permanent entity IDs, global coverage |
| **Security** (instrument) | Symbology | Security IDs, ISIN/CUSIP/SEDOL mapping |
| **Listing** (ticker@exchange) | Symbology | Listing IDs, MIC codes, ticker history |
| **IdentifierClaim** | Symbology | Multi-vendor crosswalks, historical IDs |
| **EntityRelationship** | Reference Hub, Supply Chain, Mergers | Parent/subsidiary, M&A succession |
| **PersonRole** | People | Executive/board appointments with dates |
| **OwnershipPosition** | Ownership | Institutional and insider holdings |

---

## High-Value FactSet Feeds for EntitySpine

### 1. Symbology (CRITICAL)

**Why it matters**: EntitySpine's `IdentifierClaim` model is designed for exactly this—claims-based identifier management with vendor namespaces.

**Direct Mappings**:

| FactSet Field | EntitySpine Model | Field |
|---------------|-------------------|-------|
| `FACTSET_ENTITY_ID` | IdentifierClaim | scheme=INTERNAL, namespace=FACTSET |
| `CUSIP` | IdentifierClaim | scheme=CUSIP |
| `SEDOL` | IdentifierClaim | scheme=SEDOL |
| `ISIN` | IdentifierClaim | scheme=ISIN |
| `LEI` | IdentifierClaim | scheme=LEI |
| `CIK` | IdentifierClaim | scheme=CIK |
| `FIGI` | IdentifierClaim | scheme=FIGI |
| `TICKER` | IdentifierClaim | scheme=TICKER, listing_id=... |
| `MIC` | Listing | mic field |

**EntitySpine Integration Code**:
```python
from entityspine.domain import (
    IdentifierClaim, IdentifierScheme, VendorNamespace, ClaimStatus
)

# Load FactSet cross-reference as claims
def create_factset_crossref_claims(factset_row: dict) -> list[IdentifierClaim]:
    """Convert FactSet symbology row to EntitySpine claims."""
    entity_id = factset_row["FACTSET_ENTITY_ID"]
    claims = []
    
    scheme_map = {
        "CUSIP": IdentifierScheme.CUSIP,
        "SEDOL": IdentifierScheme.SEDOL,
        "ISIN": IdentifierScheme.ISIN,
        "LEI": IdentifierScheme.LEI,
        "CIK": IdentifierScheme.CIK,
    }
    
    for field, scheme in scheme_map.items():
        if value := factset_row.get(field):
            claims.append(IdentifierClaim(
                claim_id=f"clm_{scheme.value}_{entity_id}",
                entity_id=entity_id,
                scheme=scheme,
                value=value,
                namespace=VendorNamespace.FACTSET,
                confidence=1.0,
                status=ClaimStatus.ACTIVE,
                source="factset_symbology",
            ))
    
    return claims
```

**Key Benefits**:
- Resolve SEC CIK → FactSet Entity ID → Bloomberg FIGI
- Track identifier changes over time (ticker migrations)
- Handle corporate actions (mergers redirect old IDs)

---

### 2. Reference Hub (HIGH VALUE)

**Why it matters**: Provides entity metadata and corporate hierarchy that EntitySpine's `EntityRelationship` model needs.

**Direct Mappings**:

| FactSet Field | EntitySpine Model | Field/Usage |
|---------------|-------------------|-------------|
| `ENTITY_NAME` | Entity | primary_name |
| `LEGAL_NAME` | Entity | (store as alias claim) |
| `COUNTRY_INC` | Entity | jurisdiction |
| `ENTITY_TYPE` | Entity | entity_type mapping |
| `PARENT_ID` | EntityRelationship | SUBSIDIARY_OF relationship |
| `ULT_PARENT_ID` | EntityRelationship | ULTIMATELY_OWNED_BY relationship |
| `OWNERSHIP_PCT` | EntityRelationship | metadata field |
| `STATUS` | Entity | entity_status |

**Corporate Hierarchy Integration**:
```python
from entityspine.domain import EntityRelationship, RelationshipType

def create_parent_relationship(factset_row: dict) -> EntityRelationship | None:
    """Create parent-subsidiary relationship from Reference Hub."""
    if parent_id := factset_row.get("PARENT_ID"):
        return EntityRelationship(
            relationship_id=generate_ulid(),
            source_entity_id=factset_row["ENTITY_ID"],
            target_entity_id=parent_id,
            relationship_type=RelationshipType.SUBSIDIARY_OF,
            metadata={
                "ownership_pct": factset_row.get("OWNERSHIP_PCT"),
                "effective_date": factset_row.get("EFFECTIVE_DATE"),
            },
            source_system="factset_reference_hub",
        )
    return None
```

---

### 3. Mergers & Acquisitions (HIGH VALUE)

**Why it matters**: EntitySpine's merge/redirect system aligns perfectly with FactSet M&A transaction tracking.

**Key Fields for EntitySpine**:

| FactSet Field | EntitySpine Usage |
|---------------|-------------------|
| `ACQUIRER_ID` | Successor entity |
| `TARGET_ID` | Merged-away entity |
| `EFFECTIVE_DATE` | Redirect valid_from date |
| `DEAL_STATUS` | Only process COMPLETED deals |

**Merge Tracking Integration**:
```python
from entityspine.domain import Entity, EntityStatus

def process_ma_completion(deal: dict, store: SqliteStore):
    """When M&A completes, mark target as merged and create redirect."""
    if deal["DEAL_STATUS"] != "COMPLETED":
        return
    
    target_id = deal["TARGET_ID"]
    acquirer_id = deal["ACQUIRER_ID"]
    
    # 1. Mark target entity as merged
    target = store.get_entity(target_id)
    if target:
        merged_target = Entity(
            entity_id=target.entity_id,
            primary_name=target.primary_name,
            entity_type=target.entity_type,
            status=EntityStatus.MERGED,  # Key status change
            # ... other fields preserved
        )
        store.save_entity(merged_target)
    
    # 2. Create redirect relationship
    store.save_relationship(EntityRelationship(
        relationship_id=generate_ulid(),
        source_entity_id=target_id,
        target_entity_id=acquirer_id,
        relationship_type=RelationshipType.MERGED_INTO,
        valid_from=deal["EFFECTIVE_DATE"],
        source_system="factset_mergers",
    ))
```

**Why This Matters**:
- Old CIKs/tickers remain resolvable forever
- Queries for "Tesla" still work after future acquisition
- Full audit trail of corporate history

---

### 4. People (MODERATE VALUE)

**Why it matters**: EntitySpine's `PersonRole` model tracks executive appointments—FactSet People provides this data.

**Direct Mappings**:

| FactSet Field | EntitySpine Model | Field |
|---------------|-------------------|-------|
| `PERSON_ID` | Entity (type=PERSON) | entity_id |
| `FULL_NAME` | Entity | primary_name |
| `POSITION_TITLE` | PersonRole | title |
| `START_DATE` | PersonRole | valid_from |
| `END_DATE` | PersonRole | valid_to |
| `IS_CURRENT` | PersonRole | (derive from valid_to) |
| `ENTITY_ID` | PersonRole | org_entity_id |

**Executive Tracking Integration**:
```python
from entityspine.domain import PersonRole, RoleType

def create_person_role(factset_row: dict) -> PersonRole:
    """Create PersonRole from FactSet People data."""
    role_type_map = {
        "CEO": RoleType.CEO,
        "CFO": RoleType.CFO,
        "COO": RoleType.COO,
        "CHAIR": RoleType.BOARD_CHAIR,
        "DIR": RoleType.DIRECTOR,
        "DIR_IND": RoleType.INDEPENDENT_DIRECTOR,
    }
    
    return PersonRole(
        role_id=generate_ulid(),
        person_entity_id=f"person_{factset_row['PERSON_ID']}",
        org_entity_id=factset_row["ENTITY_ID"],
        role_type=role_type_map.get(factset_row["POSITION_TYPE"], RoleType.OTHER),
        title=factset_row["POSITION_TITLE"],
        valid_from=parse_date(factset_row["START_DATE"]),
        valid_to=parse_date(factset_row.get("END_DATE")),
        source_system="factset_people",
    )
```

---

### 5. Ownership (MODERATE VALUE)

**Why it matters**: EntitySpine's `OwnershipPosition` model tracks holdings—FactSet Ownership provides institutional and insider data.

**Direct Mappings**:

| FactSet Field | EntitySpine Model | Field |
|---------------|-------------------|-------|
| `INST_ID` | OwnershipPosition | owner_entity_id |
| `SEC_ID` | OwnershipPosition | security_id |
| `SHARES_HELD` | OwnershipPosition | shares |
| `MARKET_VALUE` | OwnershipPosition | market_value |
| `PCT_SHARES_OUT` | OwnershipPosition | percentage |
| `REPORT_DATE` | OwnershipPosition | as_of_date |

---

### 6. Supply Chain (MODERATE VALUE)

**Why it matters**: EntitySpine's generic `Relationship` model can represent supplier/customer relationships.

**Integration**:
```python
from entityspine.domain import EntityRelationship, RelationshipType

def create_supply_chain_relationship(factset_row: dict) -> EntityRelationship:
    """Create supplier/customer relationship."""
    rel_type_map = {
        "SUPPLIER": RelationshipType.SUPPLIER_OF,
        "CUSTOMER": RelationshipType.CUSTOMER_OF,
        "PARTNER": RelationshipType.PARTNER_OF,
    }
    
    return EntityRelationship(
        relationship_id=generate_ulid(),
        source_entity_id=factset_row["ENTITY_ID_SOURCE"],
        target_entity_id=factset_row["ENTITY_ID_TARGET"],
        relationship_type=rel_type_map[factset_row["REL_TYPE"]],
        metadata={
            "revenue_pct": factset_row.get("REVENUE_PCT"),
        },
        source_system="factset_supply_chain",
    )
```

---

### 7. RBICS (LOW-MODERATE VALUE)

**Why it matters**: Industry classification can be stored as entity metadata or claims.

**Integration**:
```python
# Store RBICS as entity metadata or separate claims
entity = Entity(
    entity_id=factset_entity_id,
    primary_name=name,
    metadata={
        "rbics_l2": "Technology",
        "rbics_l4": "Consumer Electronics",
        "rbics_l6": "Smartphones",
    },
    # ...
)
```

---

### 8. Sanctions (SPECIALIZED VALUE)

**Why it matters**: EntitySpine can track sanctioned status via claims or relationships.

**Integration**:
```python
# Track sanctions as claims with temporal validity
sanction_claim = IdentifierClaim(
    claim_id=generate_ulid(),
    entity_id=matched_entity_id,
    scheme=IdentifierScheme.OTHER,
    value=f"OFAC_SDN:{sanction_id}",
    namespace=VendorNamespace.OTHER,
    valid_from=list_date,
    valid_to=removal_date,  # None if still active
    metadata={
        "sanction_type": "ASSET_FREEZE",
        "program": "UKRAINE-EO13662",
    },
    source="factset_sanctions",
)
```

---

## Priority Recommendation

For EntitySpine entity management, load FactSet data in this order:

| Priority | Feed | Why |
|----------|------|-----|
| 1 | **Symbology** | Foundation—identifier crosswalks enable everything else |
| 2 | **Reference Hub** | Entity metadata and corporate hierarchy |
| 3 | **Mergers** | Entity lifecycle tracking (merges, spin-offs) |
| 4 | **People** | Executive/board relationships |
| 5 | **Ownership** | Holdings relationships |
| 6 | **Supply Chain** | Business relationships |
| 7 | **RBICS** | Industry classification |

---

## EntitySpine Enum Alignment

The FactSet documentation reveals entity types that should map to existing EntitySpine enums:

| FactSet Entity Type | EntitySpine EntityType |
|---------------------|------------------------|
| Public Company | `ORGANIZATION` |
| Private Company | `ORGANIZATION` |
| Subsidiary | `ORGANIZATION` (+ SUBSIDIARY_OF relationship) |
| Holding Company | `ORGANIZATION` |
| Government | `GOVERNMENT` |
| Mutual Fund | `FUND` |
| ETF | `FUND` |
| Hedge Fund | `FUND` |
| Pension Fund | `FUND` |
| PE Fund | `FUND` |
| Trust | `TRUST` |
| Joint Venture | `PARTNERSHIP` |
| SPV | `SPV` |
| Exchange | `EXCHANGE` |

---

## Schema Detector Enhancement

The existing `load_factset.py` example could be enhanced to auto-detect more FactSet file types:

```python
# Extend schema_detector.py patterns
FACTSET_PATTERNS = {
    "sym_v1_sym_entity": {
        "vendor": "factset",
        "product": "symbology",
        "loader": "load_symbology_entities",
    },
    "sym_v1_xref_cusip": {
        "vendor": "factset", 
        "product": "symbology_crossref",
        "loader": "load_symbology_crossref",
    },
    "ref_v2_corporate_structure": {
        "vendor": "factset",
        "product": "reference_hub",
        "loader": "load_corporate_hierarchy",
    },
    "ma_v1_deals": {
        "vendor": "factset",
        "product": "mergers",
        "loader": "load_ma_deals",
    },
    "ppl_v1_executives": {
        "vendor": "factset",
        "product": "people",
        "loader": "load_executives",
    },
}
```

---

## Summary

The FactSet documentation reveals that **Symbology** and **Reference Hub** are the most valuable feeds for EntitySpine's core mission of entity resolution and management. They provide:

1. **Permanent identifiers** that survive corporate actions
2. **Multi-vendor crosswalks** (exactly what `IdentifierClaim` is designed for)
3. **Corporate hierarchy** (parent/subsidiary/ultimate parent)
4. **Merge/redirect tracking** (aligns with EntitySpine's merge model)
5. **Historical identifier changes** (ticker migrations, rebranding)

The People, Ownership, and Supply Chain feeds add relationship data that EntitySpine's knowledge graph models (`PersonRole`, `OwnershipPosition`, `EntityRelationship`) can consume.
