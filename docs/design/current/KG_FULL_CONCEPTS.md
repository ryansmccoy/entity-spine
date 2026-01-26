# EntitySpine Knowledge Graph Concepts

**Version**: 2.2.3  
**Status**: Normative

This document defines the knowledge graph primitives added in EntitySpine "Full KG" version. These extend the core Entity/Security/Listing hierarchy with richer relationship modeling.

---

## Table of Contents

1. [Overview](#overview)
2. [Node Types](#node-types)
3. [Edge Types](#edge-types)
4. [Tier Capabilities](#tier-capabilities)
5. [Schema Summary](#schema-summary)

---

## Overview

### Design Principles

1. **Entities are Broad**: Keep `EntityType` broad (ORGANIZATION, PERSON, FUND, etc.). Use **relationships** for nuance (not "Subsidiary" entity type).

2. **Evidence-Backed**: All edges carry provenance: `source_system`, `source_ref`, `confidence`, `captured_at`, optional `filing_id`.

3. **Time-Bounded**: Edges have `valid_from`/`valid_to` for truth time, plus `captured_at` for observation time.

4. **Tier Honesty**: Graph features return empty + warnings in lower tiers if data unavailable.

5. **Stdlib-Only Domain**: All models are stdlib `dataclass`, no Pydantic in domain layer.

---

## Node Types

### Core Nodes (Entity/Security/Listing)

These are the existing core hierarchy:

| Node | Purpose | Identifiers |
|------|---------|-------------|
| **Entity** | Legal organization OR person | CIK, LEI, EIN, DUNS |
| **Security** | Financial instrument | ISIN, CUSIP, FIGI, SEDOL |
| **Listing** | Where security trades | Ticker + MIC |

### Extended Nodes (KG Full)

| Node | Purpose | Key Fields |
|------|---------|------------|
| **Geo** | Geographic location | `geo_type`, `name`, `iso_code`, `parent_geo_id` |
| **Address** | Normalized address | `line1`, `city`, `region`, `postal`, `country`, `normalized_hash` |
| **Case** | Legal proceeding | `case_type`, `title`, `status`, `authority_entity_id`, `target_entity_id` |

### EntityType Enum (Expanded)

```python
class EntityType(str, Enum):
    ORGANIZATION = "organization"  # Company/Corporation
    PERSON = "person"              # Natural person
    GOVERNMENT = "government"      # Government body/agency
    FUND = "fund"                  # Investment fund
    TRUST = "trust"                # Trust structure
    PARTNERSHIP = "partnership"    # LP, LLP, GP
    SPV = "spv"                    # Special Purpose Vehicle
    EXCHANGE = "exchange"          # Stock exchange
    GEO = "geo"                    # Geographic entity (optional use)
    UNKNOWN = "unknown"            # Unknown type
```

**Important**: "Subsidiary" is NOT an entity type. Use `RelationshipType.SUBSIDIARY` edge instead.

---

## Edge Types

### NodeRef (Polymorphic Reference)

`NodeRef` enables edges between any node types:

```python
@dataclass(frozen=True, slots=True)
class NodeRef:
    kind: NodeKind  # entity, security, listing, address, geo, case
    id: str         # ULID of the referenced node
```

Usage:
```python
NodeRef.entity("abc123")
NodeRef.geo("xyz789")
```

### Edge Models

#### RoleAssignment (Person → Org)

Represents time-bounded roles:

```python
RoleAssignment(
    person_entity_id="person_ulid",
    org_entity_id="org_ulid",
    role_type=RoleType.CEO,
    title="Chief Executive Officer",
    start_date=date(2020, 1, 1),
    end_date=None,  # Still active
    confidence=0.95,
    filing_id="evidence_filing_id",
)
```

#### EntityRelationship (Entity ↔ Entity)

Corporate structure, business relationships:

```python
EntityRelationship(
    from_entity_id="parent_ulid",
    to_entity_id="subsidiary_ulid",
    relationship_type=RelationshipType.SUBSIDIARY,
    valid_from=date(2018, 3, 15),
    confidence=1.0,
    evidence_text="XYZ Corp acquired ABC Inc...",
)
```

#### Relationship (NodeRef ↔ NodeRef)

Generic edges for cross-type relationships:

```python
Relationship(
    source_ref=NodeRef.entity("company_id"),
    target_ref=NodeRef.geo("location_id"),
    relationship_type=RelationshipType.LOCATED_IN,
    subtype="headquarters",
)
```

#### EntityAddress (Entity → Address)

```python
EntityAddress(
    entity_id="entity_ulid",
    address_id="address_ulid",
    address_type=AddressType.HEADQUARTERS,
    valid_from=date(2015, 1, 1),
)
```

### Relationship Types

```python
class RelationshipType(str, Enum):
    # Corporate structure
    PARENT = "parent"
    SUBSIDIARY = "subsidiary"
    AFFILIATE = "affiliate"
    SUCCESSOR = "successor"
    
    # Business
    CUSTOMER = "customer"
    SUPPLIER = "supplier"
    PARTNER = "partner"
    COMPETITOR = "competitor"
    
    # Financial
    INVESTOR = "investor"
    BENEFICIAL_OWNER_OF = "beneficial_owner_of"
    
    # Employment
    OFFICER_OF = "officer_of"
    DIRECTOR_OF = "director_of"
    EMPLOYED_BY = "employed_by"
    
    # Geographic/Regulatory
    LOCATED_IN = "located_in"
    REGULATED_BY = "regulated_by"
    LISTED_ON = "listed_on"
```

### Role Types

```python
class RoleType(str, Enum):
    # C-Suite
    CEO = "ceo"
    CFO = "cfo"
    COO = "coo"
    
    # Board
    DIRECTOR = "director"
    CHAIR = "chair"
    
    # Officers
    PRESIDENT = "president"
    SECRETARY = "secretary"
    
    # Ownership/Compliance
    BENEFICIAL_OWNER_10PCT = "beneficial_owner_10pct"
    SIGNATORY = "signatory"
    
    # External
    AUDITOR = "auditor"
    COUNSEL = "counsel"
```

---

## Tier Capabilities

| Capability | Tier 0 | Tier 1 | Tier 2 | Tier 3 |
|------------|--------|--------|--------|--------|
| **Person Entities** | ❌ | ✅ Schema | ✅ | ✅ |
| **Role Assignments** | ❌ | ✅ Schema | ✅ | ✅ + temporal |
| **Entity Relationships** | ❌ | ✅ Schema | ✅ | ✅ + temporal |
| **Geo Nodes** | ❌ | ✅ Schema | ✅ | ✅ |
| **Address Matching** | ❌ | ✅ Hash-based | ✅ | ✅ + fuzzy |
| **Cases/Proceedings** | ❌ | ✅ Schema | ✅ | ✅ |
| **Temporal Queries** | ❌ | ⚠️ Best-effort | ⚠️ Best-effort | ✅ Full |

### Tier 1 Behavior

Tier 1 SQLite has the schema for all graph tables, but:
- Data must be manually loaded
- `as_of` queries return current data with warnings
- No full-text search on evidence text

```python
# Tier 1: returns empty if no role data loaded
roles = store.get_roles(person_entity_id)
# Result includes warnings: ["role_data_not_available"]
```

---

## Schema Summary

### SQLite Tables (Tier 1)

```
Core:
  entities         - All entities (orgs, persons, etc.)
  securities       - Financial instruments
  listings         - Exchange listings
  claims           - Identifier claims

Knowledge Graph:
  addresses        - Normalized addresses
  entity_addresses - Entity ↔ Address links
  geos             - Geographic locations
  role_assignments - Person ↔ Org roles
  entity_relationships - Entity ↔ Entity edges
  relationships    - Generic NodeRef edges
  cases            - Legal proceedings
  entity_clusters  - Deduplication clusters
  entity_cluster_members - Cluster membership
```

### Indexes

All graph tables include indexes for:
- Primary lookups (entity_id, person_id, etc.)
- Relationship queries (from/to entity)
- Type filtering (role_type, relationship_type)
- Temporal queries (start_date, end_date)

---

## Usage Examples

### Creating a Person Entity

```python
from entityspine.domain import Entity, EntityType

person = Entity(
    primary_name="John Smith",
    entity_type=EntityType.PERSON,
    source_system="sec_form4",
)
```

### Assigning a Role

```python
from entityspine.domain import RoleAssignment, RoleType

role = RoleAssignment(
    person_entity_id=person.entity_id,
    org_entity_id=company.entity_id,
    role_type=RoleType.CFO,
    start_date=date(2020, 3, 15),
    source_system="sec_filing",
    filing_id="0001234567-20-000123",
)
```

### Creating a Relationship

```python
from entityspine.domain import EntityRelationship, RelationshipType

relationship = EntityRelationship(
    from_entity_id=parent_company.entity_id,
    to_entity_id=subsidiary.entity_id,
    relationship_type=RelationshipType.SUBSIDIARY,
    confidence=1.0,
    evidence_text="ABC Corp acquired XYZ Inc in Q1 2020",
)
```

### Creating a Case

```python
from entityspine.domain import Case, CaseType, CaseStatus

case = Case(
    case_type=CaseType.ENFORCEMENT,
    title="SEC v. Example Corp",
    case_number="24-cv-12345",
    status=CaseStatus.OPEN,
    authority_entity_id=sec_entity_id,
    target_entity_id=company_entity_id,
    opened_date=date(2024, 3, 1),
)
```

---

*EntitySpine KG Full Concepts v2.2.3 | January 2026*
