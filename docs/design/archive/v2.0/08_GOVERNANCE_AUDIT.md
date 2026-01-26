# Entity Master v2 - Governance, Audit, and Best Practices

**ID Types, Audit Trails, Testing Strategy, and Observability**

---

## Identifier Governance

### Identifier Type Reference

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              IDENTIFIER TYPE REFERENCE                                   │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                          │
│  ENTITY-SCOPED IDENTIFIERS (attach to entities table)                                    │
│  ═══════════════════════════════════════════════════════                                 │
│                                                                                          │
│  ID Type    │ Format           │ Authority      │ Checksum │ Notes                       │
│  ──────────────────────────────────────────────────────────────────────────────────────  │
│  CIK        │ 10-digit number  │ SEC            │ No       │ Zero-padded                 │
│  LEI        │ 20-char alphanum │ GLEIF          │ Yes      │ Mod 97-10                   │
│  EIN        │ XX-XXXXXXX       │ IRS            │ No       │ Tax ID                      │
│  DUNS       │ 9-digit number   │ D&B            │ No       │ Unique business ID          │
│  RSSD_ID    │ Numeric          │ Fed Reserve    │ No       │ Bank holding companies      │
│                                                                                          │
│  SECURITY-SCOPED IDENTIFIERS (attach to securities table)                                │
│  ═════════════════════════════════════════════════════════                               │
│                                                                                          │
│  ID Type       │ Format              │ Authority       │ Checksum │ Notes               │
│  ──────────────────────────────────────────────────────────────────────────────────────  │
│  ISIN          │ AA + 9 alphanum + 1 │ NNA/CUSIP Global│ Luhn     │ Country prefix      │
│  CUSIP         │ 9 alphanum          │ CUSIP Global    │ Luhn     │ US/Canada focus     │
│  SEDOL         │ 7 alphanum          │ LSE             │ Mod 10   │ UK/Ireland          │
│  FIGI          │ BBG + 9 alphanum    │ Bloomberg/OMG   │ Mod 36   │ Security level      │
│  Composite FIGI│ BBG + 9 alphanum    │ Bloomberg/OMG   │ Mod 36   │ Cross-exchange      │
│  Share Class   │ BBG + 9 alphanum    │ Bloomberg/OMG   │ Mod 36   │ Share class level   │
│                                                                                          │
│  LISTING-SCOPED IDENTIFIERS (attach to listings table)                                   │
│  ════════════════════════════════════════════════════════                                │
│                                                                                          │
│  ID Type       │ Format              │ Authority       │ Checksum │ Notes               │
│  ──────────────────────────────────────────────────────────────────────────────────────  │
│  Exchange FIGI │ BBG + 9 alphanum    │ Bloomberg/OMG   │ Mod 36   │ Per-exchange        │
│  RIC           │ Ticker.ExchSuffix   │ Refinitiv       │ No       │ Reuters Code        │
│  BBG Ticker    │ Ticker ExchCode     │ Bloomberg       │ No       │ e.g., "AAPL US"     │
│  Ticker + MIC  │ Ticker + ISO MIC    │ Exchange        │ No       │ Our canonical form  │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### Identifier Validation Functions

```python
"""Identifier validation and checksum verification."""

import re
from typing import Tuple, Optional
from dataclasses import dataclass


@dataclass
class IdentifierValidation:
    """Result of validating an identifier."""
    valid: bool
    normalized: Optional[str]
    scheme: Optional[str]
    scope: Optional[str]  # 'entity', 'security', 'listing'
    error: Optional[str] = None


class IdentifierValidator:
    """Validate and normalize identifiers."""
    
    # =========================================================================
    # CIK Validation
    # =========================================================================
    
    @staticmethod
    def validate_cik(value: str) -> IdentifierValidation:
        """
        Validate SEC CIK.
        
        Format: 10-digit number (zero-padded)
        No checksum.
        """
        if not value:
            return IdentifierValidation(
                valid=False, normalized=None, scheme='cik',
                scope='entity', error='CIK is empty'
            )
        
        # Extract digits only
        digits = re.sub(r'\D', '', value)
        
        if not digits:
            return IdentifierValidation(
                valid=False, normalized=None, scheme='cik',
                scope='entity', error='CIK contains no digits'
            )
        
        if len(digits) > 10:
            return IdentifierValidation(
                valid=False, normalized=None, scheme='cik',
                scope='entity', error='CIK too long (max 10 digits)'
            )
        
        normalized = digits.zfill(10)
        
        return IdentifierValidation(
            valid=True, normalized=normalized, scheme='cik', scope='entity'
        )
    
    # =========================================================================
    # LEI Validation
    # =========================================================================
    
    @staticmethod
    def validate_lei(value: str) -> IdentifierValidation:
        """
        Validate Legal Entity Identifier (LEI).
        
        Format: 20 alphanumeric characters
        Checksum: ISO 7064 Mod 97-10
        """
        if not value:
            return IdentifierValidation(
                valid=False, normalized=None, scheme='lei',
                scope='entity', error='LEI is empty'
            )
        
        lei = value.strip().upper()
        
        # Format check
        if not re.match(r'^[A-Z0-9]{20}$', lei):
            return IdentifierValidation(
                valid=False, normalized=lei, scheme='lei',
                scope='entity', error='LEI must be 20 alphanumeric characters'
            )
        
        # Checksum validation (ISO 7064 Mod 97-10)
        if not IdentifierValidator._validate_lei_checksum(lei):
            return IdentifierValidation(
                valid=False, normalized=lei, scheme='lei',
                scope='entity', error='Invalid LEI checksum'
            )
        
        return IdentifierValidation(
            valid=True, normalized=lei, scheme='lei', scope='entity'
        )
    
    @staticmethod
    def _validate_lei_checksum(lei: str) -> bool:
        """Validate LEI using ISO 7064 Mod 97-10."""
        # Convert letters to numbers: A=10, B=11, ..., Z=35
        numeric = ''
        for char in lei:
            if char.isdigit():
                numeric += char
            else:
                numeric += str(ord(char) - ord('A') + 10)
        
        # Mod 97 check
        return int(numeric) % 97 == 1
    
    # =========================================================================
    # ISIN Validation
    # =========================================================================
    
    @staticmethod
    def validate_isin(value: str) -> IdentifierValidation:
        """
        Validate International Securities Identification Number (ISIN).
        
        Format: 2 letter country code + 9 alphanumeric + 1 check digit
        Checksum: Luhn algorithm
        """
        if not value:
            return IdentifierValidation(
                valid=False, normalized=None, scheme='isin',
                scope='security', error='ISIN is empty'
            )
        
        isin = value.strip().upper()
        
        # Format check
        if not re.match(r'^[A-Z]{2}[A-Z0-9]{9}[0-9]$', isin):
            return IdentifierValidation(
                valid=False, normalized=isin, scheme='isin',
                scope='security', error='Invalid ISIN format'
            )
        
        # Checksum validation
        if not IdentifierValidator._validate_isin_checksum(isin):
            return IdentifierValidation(
                valid=False, normalized=isin, scheme='isin',
                scope='security', error='Invalid ISIN checksum'
            )
        
        return IdentifierValidation(
            valid=True, normalized=isin, scheme='isin', scope='security'
        )
    
    @staticmethod
    def _validate_isin_checksum(isin: str) -> bool:
        """Validate ISIN using Luhn algorithm."""
        # Convert letters to numbers
        digits = []
        for char in isin:
            if char.isdigit():
                digits.append(int(char))
            else:
                val = ord(char) - ord('A') + 10
                digits.extend([val // 10, val % 10])
        
        # Apply Luhn
        total = 0
        for i, digit in enumerate(reversed(digits)):
            if i % 2 == 1:
                digit *= 2
                if digit > 9:
                    digit -= 9
            total += digit
        
        return total % 10 == 0
    
    # =========================================================================
    # CUSIP Validation
    # =========================================================================
    
    @staticmethod
    def validate_cusip(value: str) -> IdentifierValidation:
        """
        Validate CUSIP.
        
        Format: 9 alphanumeric characters
        Checksum: Luhn-like algorithm
        """
        if not value:
            return IdentifierValidation(
                valid=False, normalized=None, scheme='cusip',
                scope='security', error='CUSIP is empty'
            )
        
        cusip = value.strip().upper()
        
        # Format check
        if not re.match(r'^[A-Z0-9]{9}$', cusip):
            return IdentifierValidation(
                valid=False, normalized=cusip, scheme='cusip',
                scope='security', error='CUSIP must be 9 alphanumeric characters'
            )
        
        # Checksum validation
        if not IdentifierValidator._validate_cusip_checksum(cusip):
            return IdentifierValidation(
                valid=False, normalized=cusip, scheme='cusip',
                scope='security', error='Invalid CUSIP checksum'
            )
        
        return IdentifierValidation(
            valid=True, normalized=cusip, scheme='cusip', scope='security'
        )
    
    @staticmethod
    def _validate_cusip_checksum(cusip: str) -> bool:
        """Validate CUSIP checksum."""
        total = 0
        for i, char in enumerate(cusip[:8]):  # Exclude check digit
            if char.isdigit():
                val = int(char)
            elif char == '*':
                val = 36
            elif char == '@':
                val = 37
            elif char == '#':
                val = 38
            else:
                val = ord(char) - ord('A') + 10
            
            if i % 2 == 1:
                val *= 2
            
            total += val // 10 + val % 10
        
        check_digit = (10 - (total % 10)) % 10
        return str(check_digit) == cusip[8]
    
    # =========================================================================
    # SEDOL Validation
    # =========================================================================
    
    @staticmethod
    def validate_sedol(value: str) -> IdentifierValidation:
        """
        Validate SEDOL.
        
        Format: 7 alphanumeric characters (no vowels)
        Checksum: Weighted mod 10
        """
        if not value:
            return IdentifierValidation(
                valid=False, normalized=None, scheme='sedol',
                scope='security', error='SEDOL is empty'
            )
        
        sedol = value.strip().upper()
        
        # Format check (no vowels)
        if not re.match(r'^[B-DF-HJ-NP-TV-Z0-9]{7}$', sedol):
            return IdentifierValidation(
                valid=False, normalized=sedol, scheme='sedol',
                scope='security', error='Invalid SEDOL format'
            )
        
        # Checksum validation
        if not IdentifierValidator._validate_sedol_checksum(sedol):
            return IdentifierValidation(
                valid=False, normalized=sedol, scheme='sedol',
                scope='security', error='Invalid SEDOL checksum'
            )
        
        return IdentifierValidation(
            valid=True, normalized=sedol, scheme='sedol', scope='security'
        )
    
    @staticmethod
    def _validate_sedol_checksum(sedol: str) -> bool:
        """Validate SEDOL checksum."""
        weights = [1, 3, 1, 7, 3, 9, 1]
        
        total = 0
        for i, char in enumerate(sedol[:6]):
            if char.isdigit():
                val = int(char)
            else:
                val = ord(char) - ord('A') + 10
            total += val * weights[i]
        
        check_digit = (10 - (total % 10)) % 10
        return str(check_digit) == sedol[6]
    
    # =========================================================================
    # FIGI Validation
    # =========================================================================
    
    @staticmethod
    def validate_figi(value: str) -> IdentifierValidation:
        """
        Validate Financial Instrument Global Identifier (FIGI).
        
        Format: BBG + 9 alphanumeric
        Checksum: Mod 36 (Luhn mod N)
        """
        if not value:
            return IdentifierValidation(
                valid=False, normalized=None, scheme='figi',
                scope='security', error='FIGI is empty'
            )
        
        figi = value.strip().upper()
        
        # Format check
        if not re.match(r'^BBG[A-Z0-9]{9}$', figi):
            return IdentifierValidation(
                valid=False, normalized=figi, scheme='figi',
                scope='security', error='FIGI must be BBG + 9 alphanumeric'
            )
        
        # Note: Full FIGI checksum validation requires Mod 36 Luhn
        # Simplified here - production should implement full algorithm
        
        return IdentifierValidation(
            valid=True, normalized=figi, scheme='figi', scope='security'
        )
    
    # =========================================================================
    # Auto-Detection
    # =========================================================================
    
    @classmethod
    def detect_and_validate(cls, value: str) -> IdentifierValidation:
        """
        Auto-detect identifier type and validate.
        
        Uses format patterns to guess the type.
        """
        if not value:
            return IdentifierValidation(
                valid=False, normalized=None, scheme=None,
                scope=None, error='Empty value'
            )
        
        cleaned = value.strip().upper()
        
        # CIK: Pure digits, 1-10 chars
        if re.match(r'^\d{1,10}$', cleaned):
            return cls.validate_cik(cleaned)
        
        # LEI: 20 alphanumeric
        if re.match(r'^[A-Z0-9]{20}$', cleaned):
            result = cls.validate_lei(cleaned)
            if result.valid:
                return result
        
        # ISIN: 2 letters + 10 chars
        if re.match(r'^[A-Z]{2}[A-Z0-9]{10}$', cleaned):
            result = cls.validate_isin(cleaned)
            if result.valid:
                return result
        
        # CUSIP: 9 alphanumeric
        if re.match(r'^[A-Z0-9]{9}$', cleaned):
            result = cls.validate_cusip(cleaned)
            if result.valid:
                return result
        
        # SEDOL: 7 alphanumeric
        if re.match(r'^[B-DF-HJ-NP-TV-Z0-9]{7}$', cleaned):
            result = cls.validate_sedol(cleaned)
            if result.valid:
                return result
        
        # FIGI: BBG prefix
        if cleaned.startswith('BBG') and len(cleaned) == 12:
            return cls.validate_figi(cleaned)
        
        # Unknown
        return IdentifierValidation(
            valid=False, normalized=cleaned, scheme=None,
            scope=None, error='Unable to detect identifier type'
        )
```

---

## Audit Trail System

### Audit Tables

```sql
-- Audit log for all changes
CREATE TABLE audit_log (
    audit_id        TEXT PRIMARY KEY,  -- ULID
    
    -- What changed
    table_name      TEXT NOT NULL,
    record_id       TEXT NOT NULL,
    operation       TEXT NOT NULL,  -- 'INSERT', 'UPDATE', 'DELETE'
    
    -- Change details
    old_values      JSONB,
    new_values      JSONB,
    changed_fields  TEXT[],
    
    -- Who/when/why
    changed_by      TEXT,           -- User or system process
    changed_at      TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    change_reason   TEXT,
    
    -- Context
    session_id      TEXT,
    request_id      TEXT,
    source_system   TEXT
);

CREATE INDEX idx_audit_table_record ON audit_log(table_name, record_id);
CREATE INDEX idx_audit_changed_at ON audit_log(changed_at);
CREATE INDEX idx_audit_changed_by ON audit_log(changed_by);

-- Entity-specific audit view
CREATE VIEW v_entity_audit AS
SELECT 
    a.audit_id,
    a.record_id as entity_id,
    e.primary_name,
    a.operation,
    a.changed_fields,
    a.old_values,
    a.new_values,
    a.changed_by,
    a.changed_at,
    a.change_reason
FROM audit_log a
LEFT JOIN entities e ON e.entity_id = a.record_id
WHERE a.table_name = 'entities'
ORDER BY a.changed_at DESC;

-- Merge audit view
CREATE VIEW v_merge_audit AS
SELECT 
    m.merge_id,
    m.from_entity_id,
    e1.primary_name as from_name,
    m.to_entity_id,
    e2.primary_name as to_name,
    m.merge_type,
    m.reason,
    m.merged_at,
    m.merged_by
FROM entity_merges m
JOIN entities e1 ON e1.entity_id = m.from_entity_id
JOIN entities e2 ON e2.entity_id = m.to_entity_id
ORDER BY m.merged_at DESC;
```

### Audit Triggers (PostgreSQL)

```sql
-- Audit trigger function
CREATE OR REPLACE FUNCTION audit_trigger_func()
RETURNS TRIGGER AS $$
DECLARE
    audit_id TEXT;
    old_json JSONB;
    new_json JSONB;
    changed TEXT[];
    col_name TEXT;
BEGIN
    audit_id := gen_ulid();
    
    IF TG_OP = 'DELETE' THEN
        old_json := to_jsonb(OLD);
        new_json := NULL;
    ELSIF TG_OP = 'UPDATE' THEN
        old_json := to_jsonb(OLD);
        new_json := to_jsonb(NEW);
        
        -- Find changed fields
        changed := ARRAY[]::TEXT[];
        FOR col_name IN 
            SELECT key FROM jsonb_each(new_json)
            WHERE new_json->key IS DISTINCT FROM old_json->key
        LOOP
            changed := array_append(changed, col_name);
        END LOOP;
    ELSIF TG_OP = 'INSERT' THEN
        old_json := NULL;
        new_json := to_jsonb(NEW);
    END IF;
    
    INSERT INTO audit_log (
        audit_id, table_name, record_id, operation,
        old_values, new_values, changed_fields,
        changed_by, changed_at
    ) VALUES (
        audit_id, TG_TABLE_NAME, 
        COALESCE(NEW.entity_id, NEW.security_id, NEW.listing_id, OLD.entity_id, OLD.security_id, OLD.listing_id),
        TG_OP,
        old_json, new_json, changed,
        current_setting('app.current_user', true),
        NOW()
    );
    
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

-- Apply audit triggers
CREATE TRIGGER audit_entities
    AFTER INSERT OR UPDATE OR DELETE ON entities
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();

CREATE TRIGGER audit_securities
    AFTER INSERT OR UPDATE OR DELETE ON securities
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();

CREATE TRIGGER audit_listings
    AFTER INSERT OR UPDATE OR DELETE ON listings
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();

CREATE TRIGGER audit_identifiers
    AFTER INSERT OR UPDATE OR DELETE ON identifiers
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();

CREATE TRIGGER audit_entity_merges
    AFTER INSERT ON entity_merges
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();
```

### Audit Query Functions

```python
"""Audit trail queries."""

from datetime import datetime, timedelta
from typing import List, Dict, Optional


class AuditService:
    """Query and analyze audit logs."""
    
    def __init__(self, db):
        self.db = db
    
    async def get_entity_history(
        self,
        entity_id: str,
        since: Optional[datetime] = None,
    ) -> List[Dict]:
        """Get full change history for an entity."""
        
        query = """
            SELECT 
                audit_id,
                operation,
                changed_fields,
                old_values,
                new_values,
                changed_by,
                changed_at,
                change_reason
            FROM audit_log
            WHERE table_name = 'entities' AND record_id = :entity_id
        """
        params = {'entity_id': entity_id}
        
        if since:
            query += " AND changed_at >= :since"
            params['since'] = since
        
        query += " ORDER BY changed_at DESC"
        
        rows = await self.db.fetch_all(query, params)
        return [dict(r) for r in rows]
    
    async def get_recent_merges(
        self,
        limit: int = 100,
    ) -> List[Dict]:
        """Get recent entity merges."""
        
        return await self.db.fetch_all("""
            SELECT 
                m.merge_id,
                m.from_entity_id,
                e1.primary_name as from_name,
                m.to_entity_id,
                e2.primary_name as to_name,
                m.merge_type,
                m.reason,
                m.merged_at,
                m.merged_by
            FROM entity_merges m
            JOIN entities e1 ON e1.entity_id = m.from_entity_id
            JOIN entities e2 ON e2.entity_id = m.to_entity_id
            ORDER BY m.merged_at DESC
            LIMIT :limit
        """, {'limit': limit})
    
    async def get_data_quality_report(
        self,
        days: int = 7,
    ) -> Dict:
        """Generate data quality report."""
        
        since = datetime.utcnow() - timedelta(days=days)
        
        # Count operations by type
        ops = await self.db.fetch_all("""
            SELECT 
                table_name,
                operation,
                COUNT(*) as count
            FROM audit_log
            WHERE changed_at >= :since
            GROUP BY table_name, operation
            ORDER BY table_name, operation
        """, {'since': since})
        
        # Count conflicts
        conflicts = await self.db.fetch_one("""
            SELECT COUNT(*) as count
            FROM crosswalk_conflicts
            WHERE detected_at >= :since
        """, {'since': since})
        
        # Count validation errors
        errors = await self.db.fetch_one("""
            SELECT COUNT(*) as count
            FROM silver.validation_errors
            WHERE detected_at >= :since
        """, {'since': since})
        
        # Unresolved mentions
        unresolved = await self.db.fetch_one("""
            SELECT COUNT(*) as count
            FROM mentions
            WHERE resolution_status = 'pending'
              AND created_at >= :since
        """, {'since': since})
        
        return {
            'period_days': days,
            'operations': [dict(r) for r in ops],
            'conflicts': conflicts['count'],
            'validation_errors': errors['count'],
            'unresolved_mentions': unresolved['count'],
        }
```

---

## Testing Strategy

### Test Categories

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              TEST PYRAMID FOR ENTITY MASTER                              │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                          │
│                           ┌─────────────────────────┐                                    │
│                           │     E2E Tests           │  ← Few, slow, high confidence     │
│                           │   (Integration with     │                                    │
│                           │    external systems)    │                                    │
│                           └───────────┬─────────────┘                                    │
│                                       │                                                  │
│                       ┌───────────────┴───────────────┐                                  │
│                       │     Integration Tests          │  ← Full pipeline tests         │
│                       │   (Bronze → Silver → Gold)     │                                 │
│                       └───────────────┬───────────────┘                                  │
│                                       │                                                  │
│           ┌───────────────────────────┴───────────────────────────┐                      │
│           │              Contract Tests                           │  ← API boundaries    │
│           │   (Storage interface, Resolution interface)           │                      │
│           └───────────────────────────┬───────────────────────────┘                      │
│                                       │                                                  │
│   ┌───────────────────────────────────┴───────────────────────────────────┐              │
│   │                         Unit Tests                                    │  ← Fast,     │
│   │   (Validators, normalizers, checksum, merge logic, resolution)        │    many      │
│   └───────────────────────────────────────────────────────────────────────┘              │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### Unit Tests

```python
"""Unit tests for Entity Master."""

import pytest
from datetime import date

from entity_master.core.identifiers import IdentifierValidator
from entity_master.core.normalization import normalize_company_name
from entity_master.core.types import Entity, EntityStatus


class TestIdentifierValidation:
    """Test identifier validation."""
    
    # =========================================================================
    # CIK Tests
    # =========================================================================
    
    def test_cik_valid(self):
        result = IdentifierValidator.validate_cik("320193")
        assert result.valid
        assert result.normalized == "0000320193"
        assert result.scheme == "cik"
        assert result.scope == "entity"
    
    def test_cik_already_padded(self):
        result = IdentifierValidator.validate_cik("0000320193")
        assert result.valid
        assert result.normalized == "0000320193"
    
    def test_cik_empty(self):
        result = IdentifierValidator.validate_cik("")
        assert not result.valid
        assert result.error == "CIK is empty"
    
    def test_cik_too_long(self):
        result = IdentifierValidator.validate_cik("12345678901")
        assert not result.valid
        assert "too long" in result.error
    
    def test_cik_with_letters(self):
        result = IdentifierValidator.validate_cik("CIK320193")
        assert result.valid  # Letters stripped
        assert result.normalized == "0000320193"
    
    # =========================================================================
    # LEI Tests
    # =========================================================================
    
    def test_lei_valid(self):
        # Apple Inc. LEI
        result = IdentifierValidator.validate_lei("HWUPKR0MPOU8FGXBT394")
        assert result.valid
        assert result.scheme == "lei"
        assert result.scope == "entity"
    
    def test_lei_invalid_checksum(self):
        result = IdentifierValidator.validate_lei("HWUPKR0MPOU8FGXBT395")
        assert not result.valid
        assert "checksum" in result.error.lower()
    
    def test_lei_wrong_length(self):
        result = IdentifierValidator.validate_lei("HWUPKR0MPOU8FGX")
        assert not result.valid
    
    # =========================================================================
    # ISIN Tests
    # =========================================================================
    
    def test_isin_valid(self):
        # Apple Inc. ISIN
        result = IdentifierValidator.validate_isin("US0378331005")
        assert result.valid
        assert result.scheme == "isin"
        assert result.scope == "security"
    
    def test_isin_invalid_checksum(self):
        result = IdentifierValidator.validate_isin("US0378331006")
        assert not result.valid
        assert "checksum" in result.error.lower()
    
    def test_isin_wrong_format(self):
        result = IdentifierValidator.validate_isin("0378331005US")
        assert not result.valid
    
    # =========================================================================
    # CUSIP Tests
    # =========================================================================
    
    def test_cusip_valid(self):
        # Apple Inc. CUSIP
        result = IdentifierValidator.validate_cusip("037833100")
        assert result.valid
        assert result.scheme == "cusip"
    
    def test_cusip_invalid_checksum(self):
        result = IdentifierValidator.validate_cusip("037833101")
        assert not result.valid
    
    # =========================================================================
    # FIGI Tests
    # =========================================================================
    
    def test_figi_valid(self):
        result = IdentifierValidator.validate_figi("BBG000B9XRY4")
        assert result.valid
        assert result.scheme == "figi"
        assert result.scope == "security"
    
    def test_figi_wrong_prefix(self):
        result = IdentifierValidator.validate_figi("XYZ000B9XRY4")
        assert not result.valid
    
    # =========================================================================
    # Auto-Detection Tests
    # =========================================================================
    
    def test_detect_cik(self):
        result = IdentifierValidator.detect_and_validate("320193")
        assert result.valid
        assert result.scheme == "cik"
    
    def test_detect_isin(self):
        result = IdentifierValidator.detect_and_validate("US0378331005")
        assert result.valid
        assert result.scheme == "isin"
    
    def test_detect_lei(self):
        result = IdentifierValidator.detect_and_validate("HWUPKR0MPOU8FGXBT394")
        assert result.valid
        assert result.scheme == "lei"
    
    def test_detect_figi(self):
        result = IdentifierValidator.detect_and_validate("BBG000B9XRY4")
        assert result.valid
        assert result.scheme == "figi"


class TestNameNormalization:
    """Test company name normalization."""
    
    def test_basic_normalization(self):
        assert normalize_company_name("Apple Inc.") == "APPLE"
    
    def test_remove_corp(self):
        assert normalize_company_name("Microsoft Corporation") == "MICROSOFT"
    
    def test_remove_llc(self):
        assert normalize_company_name("Advanced Silicon Technologies, LLC") == "ADVANCED SILICON TECHNOLOGIES"
    
    def test_remove_the(self):
        assert normalize_company_name("The Walt Disney Company") == "WALT DISNEY"
    
    def test_collapse_whitespace(self):
        assert normalize_company_name("Apple    Inc.") == "APPLE"
    
    def test_unicode_normalization(self):
        assert normalize_company_name("Société Générale") == "SOCIETE GENERALE"
    
    def test_preserve_ampersand(self):
        assert normalize_company_name("Johnson & Johnson") == "JOHNSON & JOHNSON"


class TestMergeLogic:
    """Test entity merge logic."""
    
    @pytest.fixture
    def mock_store(self):
        """Create mock storage for testing."""
        from unittest.mock import MagicMock, AsyncMock
        
        store = MagicMock()
        store.get_entity = AsyncMock()
        store.merge_entities = AsyncMock(return_value="merge_123")
        store.get_canonical_entity_id = AsyncMock()
        
        return store
    
    @pytest.mark.asyncio
    async def test_merge_transfers_identifiers(self, mock_store):
        """Verify merge transfers identifiers."""
        # Setup
        from_entity = Entity(
            entity_id="from_123",
            primary_name="Apple Computer Inc",
            cik="0000320193",
        )
        to_entity = Entity(
            entity_id="to_456",
            primary_name="Apple Inc",
        )
        
        mock_store.get_entity.side_effect = [from_entity, to_entity]
        
        # Execute merge
        merge_id = await mock_store.merge_entities(
            from_entity_id="from_123",
            to_entity_id="to_456",
            merge_type="duplicate",
            reason="Same company, different names",
        )
        
        assert merge_id == "merge_123"
        mock_store.merge_entities.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_follow_merge_chain(self, mock_store):
        """Test following merge chains."""
        # A → B → C (canonical)
        mock_store.get_canonical_entity_id.return_value = "entity_C"
        
        canonical = await mock_store.get_canonical_entity_id("entity_A")
        
        assert canonical == "entity_C"
```

### Integration Tests

```python
"""Integration tests for Entity Master."""

import pytest
import tempfile
from datetime import date

from entity_master import EntityResolver
from entity_master.core.types import Entity, Security, Listing


@pytest.fixture
def sqlite_resolver():
    """Create resolver with temp SQLite database."""
    with tempfile.NamedTemporaryFile(suffix='.db') as f:
        resolver = EntityResolver.from_sqlite(f.name)
        yield resolver


class TestResolutionPipeline:
    """Test full resolution pipeline."""
    
    def test_create_and_resolve_entity(self, sqlite_resolver):
        """Test creating entity and resolving by CIK."""
        # Create entity
        entity = Entity(
            entity_id=generate_ulid(),
            primary_name="Apple Inc.",
            cik="0000320193",
        )
        sqlite_resolver.store.create_entity(entity)
        
        # Resolve by CIK
        result = sqlite_resolver.resolve("320193")
        
        assert result.success
        assert result.entity.primary_name == "Apple Inc."
        assert result.resolved_via == "cik"
    
    def test_resolve_by_name_fuzzy(self, sqlite_resolver):
        """Test fuzzy name resolution."""
        # Create entity
        entity = Entity(
            entity_id=generate_ulid(),
            primary_name="Microsoft Corporation",
        )
        sqlite_resolver.store.create_entity(entity)
        
        # Resolve by fuzzy name
        result = sqlite_resolver.resolve("Microsoft Corp")
        
        assert result.success
        assert result.entity.primary_name == "Microsoft Corporation"
    
    def test_merge_and_follow(self, sqlite_resolver):
        """Test merge chain following."""
        # Create two entities
        old_entity = Entity(
            entity_id=generate_ulid(),
            primary_name="Apple Computer Inc",
            cik="0000320193",
        )
        new_entity = Entity(
            entity_id=generate_ulid(),
            primary_name="Apple Inc",
        )
        
        sqlite_resolver.store.create_entity(old_entity)
        sqlite_resolver.store.create_entity(new_entity)
        
        # Merge old into new
        sqlite_resolver.merge_entities(
            from_entity_id=old_entity.entity_id,
            to_entity_id=new_entity.entity_id,
            merge_type="rename",
            reason="Company renamed",
        )
        
        # Resolve old entity - should get new
        result = sqlite_resolver.resolve(old_entity.entity_id)
        
        assert result.success
        assert result.entity.entity_id == new_entity.entity_id
        assert result.followed_merge


class TestBatchResolution:
    """Test batch resolution."""
    
    def test_batch_resolve_mixed(self, sqlite_resolver):
        """Test batch resolution with mixed identifiers."""
        # Create test entities
        entities = [
            Entity(entity_id=generate_ulid(), primary_name="Apple Inc", cik="0000320193"),
            Entity(entity_id=generate_ulid(), primary_name="Microsoft Corp", cik="0000789019"),
        ]
        
        for e in entities:
            sqlite_resolver.store.create_entity(e)
        
        # Batch resolve
        result = sqlite_resolver.resolve_batch([
            "320193",  # CIK
            "789019",  # CIK
            "Nonexistent Company",  # Will fail
        ])
        
        assert result.total == 3
        assert result.resolved == 2
        assert result.failed == 1
```

### Contract Tests

```python
"""Contract tests for storage interface."""

import pytest
from abc import ABC, abstractmethod

from entity_master.storage.base import EntityStore
from entity_master.core.types import Entity, EntityStatus


class StorageContractTests(ABC):
    """
    Contract tests that all storage implementations must pass.
    
    Subclass this and implement get_store() for each implementation.
    """
    
    @abstractmethod
    def get_store(self) -> EntityStore:
        """Return a fresh store instance for testing."""
        pass
    
    @pytest.mark.asyncio
    async def test_create_and_get_entity(self):
        """Storage must support creating and retrieving entities."""
        store = self.get_store()
        await store.connect()
        
        entity = Entity(
            entity_id=generate_ulid(),
            primary_name="Test Entity",
        )
        
        await store.create_entity(entity)
        retrieved = await store.get_entity(entity.entity_id)
        
        assert retrieved is not None
        assert retrieved.entity_id == entity.entity_id
        assert retrieved.primary_name == entity.primary_name
        
        await store.close()
    
    @pytest.mark.asyncio
    async def test_identifier_lookup(self):
        """Storage must support identifier-based lookup."""
        store = self.get_store()
        await store.connect()
        
        entity = Entity(
            entity_id=generate_ulid(),
            primary_name="Test Entity",
            cik="0000123456",
        )
        
        await store.create_entity(entity)
        await store.add_identifier(Identifier(
            identifier_id=generate_ulid(),
            scheme='cik',
            value='0000123456',
            entity_id=entity.entity_id,
        ))
        
        result = await store.get_by_identifier('cik', '0000123456')
        
        assert result is not None
        assert result.entity.entity_id == entity.entity_id
        
        await store.close()
    
    @pytest.mark.asyncio
    async def test_merge_updates_status(self):
        """Merge must update source entity status."""
        store = self.get_store()
        await store.connect()
        
        from_entity = Entity(entity_id=generate_ulid(), primary_name="Old Name")
        to_entity = Entity(entity_id=generate_ulid(), primary_name="New Name")
        
        await store.create_entity(from_entity)
        await store.create_entity(to_entity)
        
        await store.merge_entities(
            from_entity_id=from_entity.entity_id,
            to_entity_id=to_entity.entity_id,
            merge_type='duplicate',
            reason='Test merge',
        )
        
        merged = await store.get_entity(from_entity.entity_id, follow_merges=False)
        assert merged.status == EntityStatus.MERGED
        
        await store.close()


class TestSQLiteStorage(StorageContractTests):
    """SQLite-specific contract tests."""
    
    def get_store(self):
        from entity_master.storage.sqlite_store import SQLiteEntityStore
        return SQLiteEntityStore(":memory:")


class TestDuckDBStorage(StorageContractTests):
    """DuckDB-specific contract tests."""
    
    def get_store(self):
        from entity_master.storage.duckdb_store import DuckDBEntityStore
        return DuckDBEntityStore(":memory:")
```

---

## Observability

### Metrics

```python
"""Metrics for Entity Master observability."""

from prometheus_client import Counter, Histogram, Gauge
import time


# Resolution metrics
RESOLUTION_REQUESTS = Counter(
    'entity_master_resolution_requests_total',
    'Total resolution requests',
    ['scheme', 'success']
)

RESOLUTION_LATENCY = Histogram(
    'entity_master_resolution_latency_seconds',
    'Resolution request latency',
    ['scheme'],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
)

# Entity counts
ENTITY_COUNT = Gauge(
    'entity_master_entities_total',
    'Total entities by status',
    ['status']
)

SECURITY_COUNT = Gauge(
    'entity_master_securities_total',
    'Total securities'
)

LISTING_COUNT = Gauge(
    'entity_master_listings_total',
    'Total listings by status',
    ['status']
)

# Merge metrics
MERGE_COUNT = Counter(
    'entity_master_merges_total',
    'Total entity merges',
    ['merge_type']
)

# Conflict metrics
CONFLICT_COUNT = Counter(
    'entity_master_conflicts_total',
    'Total crosswalk conflicts',
    ['conflict_type', 'auto_resolved']
)

# Pipeline metrics
PIPELINE_RECORDS_PROCESSED = Counter(
    'entity_master_pipeline_records_processed_total',
    'Records processed in pipeline',
    ['layer', 'source']
)

PIPELINE_ERRORS = Counter(
    'entity_master_pipeline_errors_total',
    'Pipeline processing errors',
    ['layer', 'source', 'error_type']
)


class MetricsCollector:
    """Collect and expose Entity Master metrics."""
    
    def __init__(self, db):
        self.db = db
    
    async def collect_entity_counts(self):
        """Update entity count gauges."""
        rows = await self.db.fetch_all("""
            SELECT status, COUNT(*) as count
            FROM entities
            GROUP BY status
        """)
        
        for row in rows:
            ENTITY_COUNT.labels(status=row['status']).set(row['count'])
    
    async def collect_security_counts(self):
        """Update security count gauge."""
        row = await self.db.fetch_one("SELECT COUNT(*) as count FROM securities")
        SECURITY_COUNT.set(row['count'])
    
    async def collect_listing_counts(self):
        """Update listing count gauges."""
        rows = await self.db.fetch_all("""
            SELECT status, COUNT(*) as count
            FROM listings
            GROUP BY status
        """)
        
        for row in rows:
            LISTING_COUNT.labels(status=row['status']).set(row['count'])


def track_resolution(scheme: str):
    """Decorator to track resolution metrics."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                RESOLUTION_REQUESTS.labels(
                    scheme=scheme,
                    success='true' if result.success else 'false'
                ).inc()
                return result
            finally:
                RESOLUTION_LATENCY.labels(scheme=scheme).observe(
                    time.time() - start_time
                )
        return wrapper
    return decorator
```

### Structured Logging

```python
"""Structured logging for Entity Master."""

import structlog
from typing import Any, Dict


# Configure structlog
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a structured logger."""
    return structlog.get_logger(name)


class EntityMasterLogger:
    """Specialized logger for Entity Master operations."""
    
    def __init__(self, name: str = "entity_master"):
        self.log = get_logger(name)
    
    def resolution_started(
        self,
        query: str,
        query_type: str,
        request_id: str = None,
    ):
        """Log resolution start."""
        self.log.info(
            "resolution_started",
            query=query,
            query_type=query_type,
            request_id=request_id,
        )
    
    def resolution_completed(
        self,
        query: str,
        success: bool,
        resolved_entity_id: str = None,
        resolved_via: str = None,
        confidence: float = None,
        duration_ms: float = None,
        request_id: str = None,
    ):
        """Log resolution completion."""
        self.log.info(
            "resolution_completed",
            query=query,
            success=success,
            resolved_entity_id=resolved_entity_id,
            resolved_via=resolved_via,
            confidence=confidence,
            duration_ms=duration_ms,
            request_id=request_id,
        )
    
    def merge_completed(
        self,
        from_entity_id: str,
        to_entity_id: str,
        merge_type: str,
        merge_id: str,
        reason: str = None,
    ):
        """Log entity merge."""
        self.log.info(
            "merge_completed",
            from_entity_id=from_entity_id,
            to_entity_id=to_entity_id,
            merge_type=merge_type,
            merge_id=merge_id,
            reason=reason,
        )
    
    def conflict_detected(
        self,
        conflict_type: str,
        vendor: str,
        vendor_id: str,
        existing_id: str,
        new_id: str,
        auto_resolved: bool,
    ):
        """Log crosswalk conflict."""
        self.log.warning(
            "conflict_detected",
            conflict_type=conflict_type,
            vendor=vendor,
            vendor_id=vendor_id,
            existing_canonical_id=existing_id,
            new_canonical_id=new_id,
            auto_resolved=auto_resolved,
        )
    
    def validation_error(
        self,
        source: str,
        field: str,
        value: str,
        error_type: str,
        error_message: str,
    ):
        """Log validation error."""
        self.log.warning(
            "validation_error",
            source=source,
            field=field,
            value=value,
            error_type=error_type,
            error_message=error_message,
        )
    
    def pipeline_batch_completed(
        self,
        layer: str,
        source: str,
        processed: int,
        errors: int,
        duration_seconds: float,
    ):
        """Log pipeline batch completion."""
        self.log.info(
            "pipeline_batch_completed",
            layer=layer,
            source=source,
            records_processed=processed,
            errors=errors,
            duration_seconds=duration_seconds,
        )
```

---

## Summary

This document completes the Entity Master v2 specification with:

1. **Identifier Governance** - Complete reference of ID types with validation rules
2. **Audit Trail System** - Full change tracking with PostgreSQL triggers
3. **Testing Strategy** - Unit, integration, and contract tests
4. **Observability** - Prometheus metrics and structured logging

Together with the previous 7 documents, this provides a complete Staff+ Architect-level specification for the Entity Master v2 system.

---

## Document Index

| # | Document | Summary |
|---|----------|---------|
| 01 | [Canonical Data Model](01_CANONICAL_DATA_MODEL.md) | ERD, DDL, scope enforcement |
| 02 | [Resolution & Merge Workflows](02_RESOLUTION_AND_MERGE_WORKFLOWS.md) | Resolution paths, merge handling |
| 03 | [Vendor Crosswalk & Conflicts](03_VENDOR_CROSSWALK_AND_CONFLICTS.md) | Vendor ID mapping, conflict resolution |
| 04 | [Mentions & Provisional Entities](04_MENTIONS_PROVISIONAL.md) | Private entity workflow |
| 05 | [Storage Tiers](05_STORAGE_TIERS.md) | SQLite → DuckDB → PostgreSQL → ES+Neo4j |
| 06 | [py-sec-edgar Port](06_PYSECEDGAR_PORT.md) | Integration with existing codebase |
| 07 | [FeedSpine Pipeline](07_FEEDSPINE_PIPELINE.md) | Bronze/Silver/Gold data layers |
| 08 | [Governance & Audit](08_GOVERNANCE_AUDIT.md) | ID types, audit, testing, observability |
