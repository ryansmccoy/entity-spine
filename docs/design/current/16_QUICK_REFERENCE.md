# py-sec-edgar Entity Master v2 Quick Reference

**Migration Guide | ID Mapping | Cheat Sheet**

---

## TL;DR: What Changed?

| Before (v1) | After (v2) |
|-------------|------------|
| Single `entities` table | Entity → Security → Listing hierarchy |
| UUID primary keys | ULID primary keys (26 chars) |
| All identifiers mixed | Scope-enforced identifiers |
| `company_id` foreign key | `entity_id` (Entity Master ULID) |
| Local entity management | Entity Master v2 service |
| Relationships in py-sec-edgar | Relationships pushed to Entity Master |

---

## ID Type Quick Reference

### What py-sec-edgar Uses

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  py-sec-edgar Tables                                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  filings                                                                     │
│  ├── filing_id: UUID (local)                                                │
│  └── filer_entity_id: CHAR(26) → Entity Master entities.entity_id           │
│                                                                              │
│  sigdev_events                                                               │
│  ├── event_id: UUID (local)                                                 │
│  └── issuer_entity_id: CHAR(26) → Entity Master entities.entity_id          │
│                                                                              │
│  entity_mentions                                                             │
│  ├── mention_id: UUID (local)                                               │
│  ├── entity_id: CHAR(26) → Entity Master (entity scope)                     │
│  ├── security_id: CHAR(26) → Entity Master (security scope)                 │
│  └── listing_id: CHAR(26) → Entity Master (listing scope)                   │
│                                                                              │
│  event_entity_links                                                          │
│  ├── link_id: UUID (local)                                                  │
│  ├── entity_id: CHAR(26) → Entity Master (entity scope)                     │
│  ├── security_id: CHAR(26) → Entity Master (security scope)                 │
│  └── listing_id: CHAR(26) → Entity Master (listing scope)                   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Entity Master v2 ID Hierarchy

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Entity Master v2 Hierarchy                                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  entities (ULID: 01HYB7GKPD3MX9VNPBQ2T6XNYW)                                │
│  │   └─ Identifiers: CIK, LEI, EIN, DUNS                                    │
│  │                                                                           │
│  └── securities (ULID: 01HYB7GKPD3MX9VNPBQ2T6XNYM)                          │
│      │   └─ Identifiers: ISIN, CUSIP, SEDOL, Composite FIGI                 │
│      │                                                                       │
│      └── listings (ULID: 01HYB7GKPD3MX9VNPBQ2T6XNYP)                        │
│              └─ Identifiers: Ticker, RIC, Share Class FIGI                  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Identifier Scope Rules

### ⚠️ CRITICAL: Never Cross Scopes

| Identifier | Scope | Table | NEVER attach to |
|------------|-------|-------|-----------------|
| **CIK** | Entity | `entities` | securities, listings |
| **LEI** | Entity | `entities` | securities, listings |
| **EIN** | Entity | `entities` | securities, listings |
| **ISIN** | Security | `securities` | entities, listings |
| **CUSIP** | Security | `securities` | entities, listings |
| **SEDOL** | Security | `securities` | entities, listings |
| **Ticker** | Listing | `listings` | entities, securities |
| **RIC** | Listing | `listings` | entities, securities |

### py-sec-edgar Resolution Examples

```python
# ✅ CORRECT: CIK resolves to entity
result = await resolver.resolve_cik("0000320193")
entity_id = result.entity.entity_id  # Use this

# ✅ CORRECT: Ticker resolves through chain
result = await resolver.resolve_ticker("AAPL")
listing_id = result.entity.listing_id    # Available
security_id = result.entity.security_id  # Available  
entity_id = result.entity.entity_id      # Use this for filer FK

# ✅ CORRECT: CUSIP resolves through chain
result = await resolver.resolve_cusip("037833100")
security_id = result.entity.security_id  # For 13F holdings
entity_id = result.entity.entity_id      # For issuer lookup

# ❌ WRONG: Don't store ticker directly on entity mentions
# The ticker belongs to a LISTING, not the ENTITY
mention.entity_id = result.entity.entity_id  # ✅
mention.ticker = "AAPL"  # ❌ Don't copy - use listing_id instead
```

---

## Common py-sec-edgar Operations

### 1. Ingest Filing (Get entity_id from CIK)

```python
# SEC filing has CIK in header
cik = "0000320193"

# Resolve to Entity Master
result = await entity_resolver.resolve_cik(cik)

# Store filing with entity_id
await db.execute("""
    INSERT INTO filings (filing_id, filer_entity_id, cik, ...)
    VALUES ($1, $2, $3, ...)
""", 
    filing_id,
    result.entity.entity_id,  # ULID from Entity Master
    cik,  # Keep CIK for fast queries
)
```

### 2. Extract Company Mention

```python
# Found "Microsoft Corporation" in text
mention_text = "Microsoft Corporation"

# Resolve by name
result = await entity_resolver.resolve_name(
    name=mention_text,
    min_confidence=0.7,
    create_provisional=True,  # Create if not found
)

if result.success:
    await db.execute("""
        INSERT INTO entity_mentions (
            mention_id, entity_id, mention_text, resolution_status
        ) VALUES ($1, $2, $3, 'resolved')
    """, 
        mention_id,
        result.entity.entity_id,
        mention_text,
    )
```

### 3. Extract Ticker Mention

```python
# Found "(NASDAQ: MSFT)" in text
ticker = "MSFT"

# Resolve ticker → listing → security → entity
result = await entity_resolver.resolve_ticker(ticker, mic="XNAS")

if result.success:
    await db.execute("""
        INSERT INTO entity_mentions (
            mention_id, 
            entity_id, 
            security_id,
            listing_id,
            mention_text,
            resolution_status
        ) VALUES ($1, $2, $3, $4, $5, 'resolved')
    """,
        mention_id,
        result.entity.entity_id,    # Always filled
        result.entity.security_id,  # From ticker chain
        result.entity.listing_id,   # From ticker chain
        f"(NASDAQ: {ticker})",
    )
```

### 4. Extract Customer Concentration + Push Relationship

```python
# Extracted: "Walmart accounted for 15% of revenue"
customer_name = "Walmart"
revenue_pct = 15.0

# Resolve customer
result = await entity_resolver.resolve_name(customer_name)

if result.success:
    # Push relationship to Entity Master
    relationship_id = await entity_resolver.add_relationship(
        source_entity_id=filer_entity_id,  # The filing company
        target_entity_id=result.entity.entity_id,  # Walmart
        relationship_type="SUPPLIES_TO",
        evidence={
            "source_system": "py_sec_edgar",
            "source_id": filing_id,
            "evidence_text": "Walmart accounted for 15% of revenue",
            "confidence": 0.9,
        },
        metrics={"revenue_pct": revenue_pct},
    )
```

### 5. Handle Entity Merge Webhook

```python
@router.post("/webhooks/entity-master")
async def handle_merge(request: Request):
    payload = await request.json()
    
    if payload["event_type"] == "entity.merged":
        old_id = payload["from_entity_id"]
        new_id = payload["to_entity_id"]
        
        # Update ALL entity_id references
        for table in ["filings", "sigdev_events", "entity_mentions", "event_entity_links"]:
            await db.execute(f"""
                UPDATE {table} 
                SET entity_id = $1 
                WHERE entity_id = $2
            """, new_id, old_id)
```

---

## Foreign Key Reference

### py-sec-edgar Tables → Entity Master

| py-sec-edgar Column | Entity Master Table | Entity Master Column |
|---------------------|---------------------|---------------------|
| `filings.filer_entity_id` | `entities` | `entity_id` |
| `sigdev_events.issuer_entity_id` | `entities` | `entity_id` |
| `entity_mentions.entity_id` | `entities` | `entity_id` |
| `entity_mentions.security_id` | `securities` | `security_id` |
| `entity_mentions.listing_id` | `listings` | `listing_id` |
| `event_entity_links.entity_id` | `entities` | `entity_id` |
| `event_entity_links.security_id` | `securities` | `security_id` |
| `event_entity_links.listing_id` | `listings` | `listing_id` |

---

## Resolution Decision Tree

```
                    ┌─────────────────────┐
                    │  What identifier    │
                    │  type do you have?  │
                    └─────────┬───────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
   ┌─────────┐          ┌──────────┐          ┌─────────┐
   │   CIK   │          │  Ticker  │          │  CUSIP  │
   │   LEI   │          │   RIC    │          │  ISIN   │
   │   EIN   │          │          │          │  SEDOL  │
   └────┬────┘          └────┬─────┘          └────┬────┘
        │                    │                     │
        ▼                    ▼                     ▼
   resolve_cik()       resolve_ticker()      resolve_cusip()
        │                    │                     │
        │              ┌─────┴─────┐               │
        │              │           │               │
        │         listing_id  security_id         │
        │              │           │               │
        │              └─────┬─────┘          security_id
        │                    │                     │
        ▼                    ▼                     ▼
   ┌─────────────────────────────────────────────────┐
   │              entity_id (ULID)                   │
   │  Use this for ALL filer/issuer foreign keys    │
   └─────────────────────────────────────────────────┘
```

---

## Configuration

```bash
# Environment variables for Entity Master v2
PY_SEC_EDGAR_ENTITY_MASTER_URL=https://entity-master.example.com
PY_SEC_EDGAR_ENTITY_MASTER_API_KEY=your-api-key
PY_SEC_EDGAR_ENTITY_MASTER_TIMEOUT=10.0
PY_SEC_EDGAR_ENTITY_RESOLVER_ADAPTER=remote  # or "local", "mock"
```

---

## Document Index

| Doc | Purpose |
|-----|---------|
| [14_STORAGE_SCHEMA_V2.md](14_STORAGE_SCHEMA_V2.md) | Full PostgreSQL DDL |
| [15_ENTITY_MASTER_INTEGRATION.md](15_ENTITY_MASTER_INTEGRATION.md) | EntityResolverPort interface |
| [entity_master_v2/01_CANONICAL_DATA_MODEL.md](entity_master_v2/01_CANONICAL_DATA_MODEL.md) | Entity Master schema |
| [entity_master_v2/02_RESOLUTION_AND_MERGE_WORKFLOWS.md](entity_master_v2/02_RESOLUTION_AND_MERGE_WORKFLOWS.md) | Resolution pipeline |

---

*Quick Reference v1.0.0 | 2025-01-25*
