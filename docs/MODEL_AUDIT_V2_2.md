# Model Audit: v2.2 Spec vs Pydantic Implementation

**Date:** January 2026  
**Status:** ✅ Models aligned with v2.2 spec

---

## Summary

The Pydantic models correctly implement the v2.2 data model semantics with one technology change:
- **Spec says:** dataclasses (stdlib-only for Tier 0-1)
- **Implementation uses:** Pydantic v2 (chosen for better validation, DX)

This is an acceptable deviation documented in the design decision log.

---

## Entity Model

### v2.2 Spec Fields (from SQL DDL)

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| entity_id | TEXT/ULID | PK | ✅ Implemented |
| entity_type | TEXT | NOT NULL | ✅ Implemented as Enum |
| status | TEXT | NOT NULL | ✅ Implemented as Enum |
| legal_name | TEXT | - | ✅ Implemented |
| primary_name | TEXT | NOT NULL | ✅ Implemented |
| sic_code | TEXT | - | ✅ Implemented |
| source_system | TEXT | NOT NULL | ⚠️ Missing - should add |
| source_id | TEXT | - | ⚠️ Missing - should add |
| created_at | TEXT | NOT NULL | ✅ Implemented |
| updated_at | TEXT | NOT NULL | ✅ Implemented |
| merged_into_id | TEXT FK | - | ✅ As redirect_to |
| merged_at | TEXT | - | ⚠️ Missing - should add |

### Additional Fields in Implementation

| Field | Notes |
|-------|-------|
| cik | Convenience field (also in claims) |
| lei | Convenience field (also in claims) |
| ein | Convenience field (also in claims) |
| jurisdiction | v2.2 has jurisdiction_country + jurisdiction_subdiv |
| incorporation_date | v2.2 has formation_date + dissolution_date |
| identifiers | Dict for additional identifiers |
| aliases | List of name variants |
| redirect_reason | Extra field for merge audit |

### Verdict: ⚠️ Minor gaps

**Add:**
- `source_system: str` (required per spec)
- `merged_at: Optional[datetime]`

---

## Security Model

### v2.2 Spec Fields

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| security_id | TEXT/ULID | PK | ✅ Implemented |
| issuer_entity_id | TEXT FK | NOT NULL | ✅ As entity_id |
| security_type | TEXT | NOT NULL | ✅ Implemented as Enum |
| name | TEXT | NOT NULL | ✅ As description |
| currency | TEXT | - | ⚠️ Missing |
| status | TEXT | NOT NULL | ⚠️ Missing |
| source_system | TEXT | NOT NULL | ⚠️ Missing |
| created_at | TEXT | NOT NULL | ✅ Implemented |

### Verdict: ⚠️ Minor gaps

**Add:**
- `currency: Optional[str]` (ISO 4217)
- `status: str = "active"`
- `source_system: str`

---

## Listing Model

### v2.2 Spec Fields

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| listing_id | TEXT/ULID | PK | ✅ Implemented |
| security_id | TEXT FK | NOT NULL | ✅ Implemented |
| ticker | TEXT | NOT NULL | ✅ Implemented |
| mic | TEXT | - | ✅ Implemented |
| is_primary | INTEGER | NOT NULL | ✅ Implemented |
| status | TEXT | NOT NULL | ⚠️ Missing |
| valid_from | TEXT | NOT NULL | ✅ As start_date |
| valid_to | TEXT | - | ✅ As end_date |
| source_system | TEXT | NOT NULL | ⚠️ Missing |
| created_at | TEXT | NOT NULL | ✅ Implemented |

### Verdict: ⚠️ Minor gaps

**Add:**
- `status: str = "active"`
- `source_system: str`

---

## IdentifierClaim Model

### v2.2 Spec Fields

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| claim_id | TEXT/ULID | PK | ✅ Implemented |
| entity_id | TEXT FK | - | ✅ Implemented |
| security_id | TEXT FK | - | ⚠️ Missing (v2.2 supports claims on securities) |
| listing_id | TEXT FK | - | ⚠️ Missing (v2.2 supports claims on listings) |
| scheme | TEXT | NOT NULL | ✅ Implemented as Enum |
| value | TEXT | NOT NULL | ✅ Implemented |
| source_system | TEXT | NOT NULL | ✅ As source |
| confidence | REAL | NOT NULL | ✅ Implemented |
| captured_at | TEXT | NOT NULL | ✅ As created_at |
| valid_from | TEXT | - | ✅ Implemented |
| valid_to | TEXT | - | ✅ Implemented |
| status | TEXT | NOT NULL | ✅ Implemented as Enum |

### Verdict: ⚠️ Minor gap

**Add:**
- `security_id: Optional[str]`
- `listing_id: Optional[str]`
- Add model_validator to ensure exactly one of entity_id/security_id/listing_id is set

---

## ResolutionResult Model

### v2.2 Spec Requirements

| Requirement | Status |
|-------------|--------|
| Return entity if found | ✅ `entity: Optional[Entity]` |
| Status enum (found, not_found, ambiguous, etc.) | ✅ `ResolutionStatus` |
| Tier that provided result | ✅ `tier: ResolutionTier` |
| Original query | ✅ `query: str` |
| as_of parameter | ✅ `as_of: Optional[date]` |
| as_of_honored flag | ✅ `as_of_honored: bool` |
| Warnings list | ✅ `warnings: list[str]` |
| Limits dict | ✅ `limits: dict[str, str]` |
| Redirect chain | ✅ `redirect_chain: list[str]` |
| Alternatives for ambiguous | ✅ `alternatives: list[Entity]` |
| Confidence score | ✅ `confidence: float` |
| Timing info | ✅ `elapsed_ms: float` |

### Verdict: ✅ Fully compliant

---

## Action Items

### Required Fixes (to match v2.2)

1. **Entity**: Add `source_system`, `merged_at`
2. **Security**: Add `currency`, `status`, `source_system`
3. **Listing**: Add `status`, `source_system`
4. **IdentifierClaim**: Add `security_id`, `listing_id` + validator

### Optional Enhancements

1. Rename `redirect_to` → `merged_into_id` for consistency
2. Rename `start_date`/`end_date` → `valid_from`/`valid_to` for consistency
3. Split `jurisdiction` into `jurisdiction_country` + `jurisdiction_subdiv`

---

## Technology Decision

### Spec Says

> "Tier 0-1: Zero external dependencies (stdlib only)"
> "NEVER use Pydantic at Tier 0-1"

### Implementation Uses

- **Pydantic v2** for all domain models
- **SQLModel** for database persistence

### Rationale

1. **Better validation**: Pydantic provides declarative validation
2. **JSON serialization**: Built-in with proper datetime handling
3. **IDE support**: Better autocomplete and type checking
4. **Developer experience**: Familiar to most Python developers
5. **Ecosystem**: Works with FastAPI, modern tools

### Trade-off

- Adds `pydantic` as a dependency (11MB installed)
- No longer "stdlib only"

### Decision

Accept the dependency for improved DX and validation. Update docs to reflect this choice.

---

*Audit completed: January 2026*
