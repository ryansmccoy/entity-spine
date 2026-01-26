# Entity Master v2 - Vendor Crosswalk and Conflict Handling

**Mapping vendor IDs (Bloomberg, FactSet, Refinitiv, S&P) with proper scope enforcement and conflict resolution**

---

## Crosswalk Architecture

### Separation: Identifiers vs Crosswalks

| Table | Purpose | Examples | Ownership |
|-------|---------|----------|-----------|
| `identifiers` | Standard public IDs | CIK, LEI, ISIN, CUSIP, FIGI | Authoritative registries |
| `crosswalks` | Vendor-internal IDs | FactSet Entity ID, PermID, GVKEY | Vendors (proprietary) |

**Why separate?**
- Standard IDs have global uniqueness guarantees; vendor IDs don't
- Different provenance tracking needs
- Different conflict handling strategies
- Crosswalks can have multiple vendor IDs pointing to same canonical record

---

## Vendor ID Scope Matrix

### Entity-Scoped Vendor IDs

| Vendor | ID Type | Format | Notes |
|--------|---------|--------|-------|
| **FactSet** | Entity ID | `000C7F-E` | Suffix `-E` indicates entity |
| **Refinitiv** | PermID Org | Numeric | Organization-level PermID |
| **S&P** | GVKEY | 6-digit | Global Company Key |
| **Bloomberg** | Company ID | Varies | Internal, rarely exposed |
| **D&B** | DUNS | 9-digit | Also a standard ID |

### Security-Scoped Vendor IDs

| Vendor | ID Type | Format | Notes |
|--------|---------|--------|-------|
| **FactSet** | Security ID | `000C7F-S-US` | Suffix `-S-` indicates security |
| **FactSet** | Regional ID | `000C7F-R-US` | Composite of listings |
| **Refinitiv** | PermID Quote | Numeric | Instrument-level PermID |
| **S&P** | GVKEY-IID | `001690-01` | GVKEY + Issue ID |
| **Bloomberg** | BUID | Varies | Bloomberg Unique ID |
| **Bloomberg** | BSID | Varies | Bloomberg Security ID |

### Listing-Scoped Vendor IDs

| Vendor | ID Type | Format | Notes |
|--------|---------|--------|-------|
| **FactSet** | Listing ID | `000C7F-L-NYS-USD` | Full exchange+currency |
| **Bloomberg** | BBID | Varies | Exchange-specific |
| **Refinitiv** | RIC | `AAPL.O` | Symbol + exchange suffix |

---

## Ingestion Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                          VENDOR DATA INGESTION PIPELINE                                  │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                          │
│  VENDOR FILE          PARSE              SCOPE CHECK        CONFLICT CHECK    STORE     │
│  ───────────          ─────              ───────────        ──────────────    ─────     │
│                                                                                          │
│  factset.csv    →   Parse rows     →   Validate scope  →   Check existing  →   Upsert  │
│                     Extract IDs        (entity/sec/lst)    conflicts            crosswalk│
│                     Detect scope       Enforce rules       Log if found                  │
│                                                                                          │
│  CONFLICT DETECTED:                                                                      │
│  ┌─────────────────────────────────────────────────────────────────┐                     │
│  │  If vendor ID already mapped to different canonical:            │                     │
│  │    → Create conflict record                                     │                     │
│  │    → Queue for review                                           │                     │
│  │    → Don't overwrite existing mapping                           │                     │
│  └─────────────────────────────────────────────────────────────────┘                     │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### Ingestion Implementation

```python
from dataclasses import dataclass
from enum import Enum
from typing import Optional, List, Dict
from datetime import date, datetime


class CrosswalkScope(Enum):
    ENTITY = 'entity'
    SECURITY = 'security'
    LISTING = 'listing'


@dataclass
class VendorIdMapping:
    """Represents a parsed vendor ID mapping."""
    vendor: str
    vendor_id_type: str
    vendor_id_value: str
    scope: CrosswalkScope
    
    # Our canonical ID (one of these will be set)
    entity_id: Optional[str] = None
    security_id: Optional[str] = None
    listing_id: Optional[str] = None
    
    # Matching hints (from vendor data)
    hints: Dict = None
    
    # Provenance
    mapping_source: str = 'vendor_file'
    mapping_method: str = 'exact'
    confidence: float = 0.95
    valid_from: Optional[date] = None
    valid_to: Optional[date] = None


class VendorDataLoader:
    """Load and validate vendor data files."""
    
    def __init__(self, db, conflict_handler):
        self.db = db
        self.conflict_handler = conflict_handler
    
    # =========================================================================
    # FactSet Loader
    # =========================================================================
    
    async def load_factset_symbology(self, filepath: str) -> LoadResult:
        """
        Load FactSet symbology file.
        
        FactSet IDs have suffixes indicating scope:
        - `-E` or no suffix: Entity
        - `-S-XX`: Security (with region)
        - `-R-XX`: Regional (composite security)
        - `-L-XXX-XXX`: Listing (exchange + currency)
        """
        stats = LoadStats()
        
        for row in self.read_file(filepath):
            fs_id = row['factset_id']
            
            # Detect scope from suffix
            mapping = self._parse_factset_id(fs_id, row)
            
            if mapping.scope == CrosswalkScope.ENTITY:
                # Try to match to existing entity
                entity_id = await self._resolve_to_entity(mapping.hints)
                if entity_id:
                    mapping.entity_id = entity_id
                else:
                    stats.unmatched += 1
                    continue
            
            elif mapping.scope == CrosswalkScope.SECURITY:
                security_id = await self._resolve_to_security(mapping.hints)
                if security_id:
                    mapping.security_id = security_id
                else:
                    stats.unmatched += 1
                    continue
            
            elif mapping.scope == CrosswalkScope.LISTING:
                listing_id = await self._resolve_to_listing(mapping.hints)
                if listing_id:
                    mapping.listing_id = listing_id
                else:
                    stats.unmatched += 1
                    continue
            
            # Check for conflicts before inserting
            conflict = await self._check_crosswalk_conflict(mapping)
            if conflict:
                await self.conflict_handler.handle(conflict)
                stats.conflicts += 1
                continue
            
            # Insert/update crosswalk
            await self._upsert_crosswalk(mapping)
            stats.loaded += 1
        
        return LoadResult(stats=stats)
    
    def _parse_factset_id(self, fs_id: str, row: dict) -> VendorIdMapping:
        """Parse FactSet ID and determine scope."""
        
        if '-L-' in fs_id:
            scope = CrosswalkScope.LISTING
            vendor_id_type = 'listing_id'
            # Parse exchange and currency from ID
            parts = fs_id.split('-L-')
            exchange_currency = parts[1] if len(parts) > 1 else ''
        
        elif '-S-' in fs_id or '-R-' in fs_id:
            scope = CrosswalkScope.SECURITY
            vendor_id_type = 'security_id' if '-S-' in fs_id else 'regional_id'
        
        elif '-E' in fs_id or fs_id.count('-') == 0:
            scope = CrosswalkScope.ENTITY
            vendor_id_type = 'entity_id'
        
        else:
            scope = CrosswalkScope.ENTITY  # Default assumption
            vendor_id_type = 'unknown'
        
        return VendorIdMapping(
            vendor='factset',
            vendor_id_type=vendor_id_type,
            vendor_id_value=fs_id,
            scope=scope,
            hints={
                'isin': row.get('isin'),
                'cusip': row.get('cusip'),
                'ticker': row.get('ticker'),
                'exchange': row.get('exchange'),
                'name': row.get('name'),
            },
        )
    
    # =========================================================================
    # Bloomberg/OpenFIGI Loader
    # =========================================================================
    
    async def load_openfigi_response(self, responses: List[dict]) -> LoadResult:
        """
        Load OpenFIGI API responses.
        
        CRITICAL: FIGI is SECURITY-scoped, not entity-scoped!
        """
        stats = LoadStats()
        
        for response in responses:
            # FIGI maps to SECURITY
            if response.get('figi'):
                mapping = VendorIdMapping(
                    vendor='openfigi',
                    vendor_id_type='figi',
                    vendor_id_value=response['figi'],
                    scope=CrosswalkScope.SECURITY,
                    mapping_source='api_lookup',
                    hints={
                        'ticker': response.get('ticker'),
                        'exchange': response.get('exchCode'),
                        'name': response.get('name'),
                        'security_type': response.get('securityType'),
                    },
                )
                
                # Resolve to security
                security_id = await self._resolve_to_security(mapping.hints)
                if security_id:
                    mapping.security_id = security_id
                    await self._upsert_crosswalk(mapping)
                    stats.loaded += 1
                else:
                    stats.unmatched += 1
            
            # Composite FIGI also security-scoped
            if response.get('compositeFIGI'):
                mapping = VendorIdMapping(
                    vendor='openfigi',
                    vendor_id_type='composite_figi',
                    vendor_id_value=response['compositeFIGI'],
                    scope=CrosswalkScope.SECURITY,
                    mapping_source='api_lookup',
                )
                # ... similar handling
        
        return LoadResult(stats=stats)
    
    # =========================================================================
    # Refinitiv Loader
    # =========================================================================
    
    async def load_refinitiv_permid(self, filepath: str) -> LoadResult:
        """
        Load Refinitiv PermID data.
        
        PermID types:
        - Organization PermID: Entity-scoped
        - Quote PermID: Security/Listing-scoped
        """
        stats = LoadStats()
        
        for row in self.read_file(filepath):
            permid = row['permid']
            permid_type = row['permid_type']
            
            if permid_type == 'ORGANIZATION':
                mapping = VendorIdMapping(
                    vendor='refinitiv',
                    vendor_id_type='permid_org',
                    vendor_id_value=permid,
                    scope=CrosswalkScope.ENTITY,
                    hints={
                        'lei': row.get('lei'),
                        'name': row.get('organization_name'),
                        'country': row.get('headquarters_country'),
                    },
                )
                
                entity_id = await self._resolve_to_entity(mapping.hints)
                if entity_id:
                    mapping.entity_id = entity_id
                    await self._upsert_crosswalk(mapping)
                    stats.loaded += 1
                else:
                    stats.unmatched += 1
            
            elif permid_type == 'QUOTE':
                mapping = VendorIdMapping(
                    vendor='refinitiv',
                    vendor_id_type='permid_quote',
                    vendor_id_value=permid,
                    scope=CrosswalkScope.SECURITY,  # Can be security or listing
                    hints={
                        'ric': row.get('ric'),
                        'isin': row.get('isin'),
                        'ticker': row.get('ticker'),
                    },
                )
                
                security_id = await self._resolve_to_security(mapping.hints)
                if security_id:
                    mapping.security_id = security_id
                    await self._upsert_crosswalk(mapping)
                    stats.loaded += 1
                else:
                    stats.unmatched += 1
        
        return LoadResult(stats=stats)
    
    # =========================================================================
    # S&P Compustat Loader
    # =========================================================================
    
    async def load_sp_compustat(self, filepath: str) -> LoadResult:
        """
        Load S&P Compustat data.
        
        - GVKEY: Entity-scoped
        - GVKEY + IID: Security-scoped
        """
        stats = LoadStats()
        
        for row in self.read_file(filepath):
            gvkey = row['gvkey'].zfill(6)
            
            # GVKEY alone = Entity
            entity_mapping = VendorIdMapping(
                vendor='sp',
                vendor_id_type='gvkey',
                vendor_id_value=gvkey,
                scope=CrosswalkScope.ENTITY,
                hints={
                    'cik': row.get('cik'),
                    'ticker': row.get('tic'),
                    'name': row.get('conm'),
                    'sic': row.get('sic'),
                },
            )
            
            entity_id = await self._resolve_to_entity(entity_mapping.hints)
            if entity_id:
                entity_mapping.entity_id = entity_id
                await self._upsert_crosswalk(entity_mapping)
                stats.loaded += 1
            
            # GVKEY + IID = Security
            if row.get('iid'):
                iid = row['iid'].zfill(2)
                gvkey_iid = f"{gvkey}-{iid}"
                
                security_mapping = VendorIdMapping(
                    vendor='sp',
                    vendor_id_type='gvkey_iid',
                    vendor_id_value=gvkey_iid,
                    scope=CrosswalkScope.SECURITY,
                    hints={
                        'cusip': row.get('cusip'),
                        'isin': row.get('isin'),
                    },
                )
                
                security_id = await self._resolve_to_security(security_mapping.hints)
                if security_id:
                    security_mapping.security_id = security_id
                    await self._upsert_crosswalk(security_mapping)
                    stats.loaded += 1
        
        return LoadResult(stats=stats)
    
    # =========================================================================
    # Internal Resolution
    # =========================================================================
    
    async def _resolve_to_entity(self, hints: dict) -> Optional[str]:
        """Try to match hints to an existing entity."""
        
        # Priority 1: CIK (authoritative)
        if hints.get('cik'):
            result = await self.db.fetch_one("""
                SELECT entity_id FROM identifiers
                WHERE scheme = 'cik' AND value = :cik
            """, {'cik': hints['cik'].zfill(10)})
            if result:
                return result['entity_id']
        
        # Priority 2: LEI
        if hints.get('lei'):
            result = await self.db.fetch_one("""
                SELECT entity_id FROM identifiers
                WHERE scheme = 'lei' AND value = :lei
            """, {'lei': hints['lei'].upper()})
            if result:
                return result['entity_id']
        
        # Priority 3: Name match
        if hints.get('name'):
            result = await self.db.fetch_one("""
                SELECT entity_id FROM entity_aliases
                WHERE name_normalized = :name
            """, {'name': normalize_company_name(hints['name'])})
            if result:
                return result['entity_id']
        
        return None
    
    async def _resolve_to_security(self, hints: dict) -> Optional[str]:
        """Try to match hints to an existing security."""
        
        # Priority 1: ISIN
        if hints.get('isin'):
            result = await self.db.fetch_one("""
                SELECT security_id FROM identifiers
                WHERE scheme = 'isin' AND value = :isin
            """, {'isin': hints['isin'].upper()})
            if result:
                return result['security_id']
        
        # Priority 2: CUSIP
        if hints.get('cusip'):
            result = await self.db.fetch_one("""
                SELECT security_id FROM identifiers
                WHERE scheme = 'cusip' AND value = :cusip
            """, {'cusip': hints['cusip'].upper()})
            if result:
                return result['security_id']
        
        # Priority 3: Ticker + Exchange → Listing → Security
        if hints.get('ticker') and hints.get('exchange'):
            result = await self.db.fetch_one("""
                SELECT security_id FROM listings
                WHERE ticker = :ticker AND mic = :mic AND status = 'active'
            """, {'ticker': hints['ticker'].upper(), 'mic': hints['exchange'].upper()})
            if result:
                return result['security_id']
        
        return None
    
    async def _resolve_to_listing(self, hints: dict) -> Optional[str]:
        """Try to match hints to an existing listing."""
        
        if hints.get('ticker') and hints.get('exchange'):
            result = await self.db.fetch_one("""
                SELECT listing_id FROM listings
                WHERE ticker = :ticker 
                  AND mic = :mic 
                  AND status = 'active'
            """, {
                'ticker': hints['ticker'].upper(),
                'mic': hints['exchange'].upper(),
            })
            if result:
                return result['listing_id']
        
        return None
    
    async def _check_crosswalk_conflict(
        self, 
        mapping: VendorIdMapping
    ) -> Optional['CrosswalkConflict']:
        """Check if this mapping conflicts with existing data."""
        
        # Check if vendor ID already mapped to different canonical
        existing = await self.db.fetch_one("""
            SELECT crosswalk_id, entity_id, security_id, listing_id
            FROM crosswalks
            WHERE vendor = :vendor
              AND vendor_id_type = :type
              AND vendor_id_value = :value
        """, {
            'vendor': mapping.vendor,
            'type': mapping.vendor_id_type,
            'value': mapping.vendor_id_value,
        })
        
        if not existing:
            return None  # No conflict
        
        # Check if mapped to different canonical
        if mapping.entity_id and existing['entity_id']:
            if mapping.entity_id != existing['entity_id']:
                return CrosswalkConflict(
                    conflict_type='one_to_many',
                    vendor=mapping.vendor,
                    vendor_id_type=mapping.vendor_id_type,
                    vendor_id_value=mapping.vendor_id_value,
                    existing_canonical_id=existing['entity_id'],
                    new_canonical_id=mapping.entity_id,
                    scope='entity',
                )
        
        # Similar checks for security_id and listing_id
        # ...
        
        return None
    
    async def _upsert_crosswalk(self, mapping: VendorIdMapping) -> str:
        """Insert or update crosswalk record."""
        
        crosswalk_id = generate_ulid()
        
        await self.db.execute("""
            INSERT INTO crosswalks (
                crosswalk_id,
                entity_id, security_id, listing_id,
                vendor, vendor_id_type, vendor_id_value,
                mapping_source, mapping_method, confidence,
                valid_from, valid_to,
                first_seen_at, last_seen_at, created_at, updated_at
            ) VALUES (
                :id,
                :entity_id, :security_id, :listing_id,
                :vendor, :type, :value,
                :source, :method, :confidence,
                :valid_from, :valid_to,
                NOW(), NOW(), NOW(), NOW()
            )
            ON CONFLICT (vendor, vendor_id_type, vendor_id_value) DO UPDATE SET
                last_seen_at = NOW(),
                updated_at = NOW(),
                confidence = GREATEST(crosswalks.confidence, EXCLUDED.confidence)
        """, {
            'id': crosswalk_id,
            'entity_id': mapping.entity_id,
            'security_id': mapping.security_id,
            'listing_id': mapping.listing_id,
            'vendor': mapping.vendor,
            'type': mapping.vendor_id_type,
            'value': mapping.vendor_id_value,
            'source': mapping.mapping_source,
            'method': mapping.mapping_method,
            'confidence': mapping.confidence,
            'valid_from': mapping.valid_from,
            'valid_to': mapping.valid_to,
        })
        
        return crosswalk_id
```

---

## Conflict Handling

### Conflict Types

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│  CONFLICT TYPE: ONE-TO-MANY                                                              │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                          │
│  Scenario: One vendor ID maps to multiple canonical records                              │
│                                                                                          │
│    FactSet Entity ID "000C7F-E" →                                                       │
│      Existing: Entity A (Apple Inc)                                                     │
│      New file:  Entity B (Apple Computer Inc)  ← Different entity_id!                   │
│                                                                                          │
│  Cause: Duplicate entities, data error, or corporate action not reflected               │
│  Resolution: Merge entities, or correct the mapping                                      │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────────┐
│  CONFLICT TYPE: MANY-TO-ONE                                                              │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                          │
│  Scenario: Multiple vendor IDs map to same canonical                                     │
│                                                                                          │
│    FactSet "000C7F-E" → Entity A (Apple)                                                │
│    FactSet "001234-E" → Entity A (Apple)  ← Different vendor IDs!                       │
│                                                                                          │
│  Cause: Often legitimate (different ID versions, or vendor's duplicates)                 │
│  Resolution: Usually OK if same vendor_id_type; flag if different types                  │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────────┐
│  CONFLICT TYPE: VENDOR DISAGREE                                                          │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                          │
│  Scenario: Different vendors give different answers for same question                    │
│                                                                                          │
│    Question: "Which entity has ISIN US0378331005?"                                       │
│    FactSet: Entity A (CIK 0000320193)                                                   │
│    Refinitiv: Entity B (CIK 0000320193)  ← Same CIK but different entity_id!            │
│                                                                                          │
│  Cause: Our entities are duplicates of same real company                                 │
│  Resolution: Merge our duplicate entities                                                │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────────┐
│  CONFLICT TYPE: SCOPE MISMATCH                                                           │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                          │
│  Scenario: Vendor ID attached to wrong scope                                             │
│                                                                                          │
│    FIGI "BBG000B9XRY4" attached to Entity (Apple Inc.)                                  │
│    WRONG! FIGI is Security-scoped, not Entity-scoped.                                    │
│                                                                                          │
│  Cause: Misunderstanding of identifier semantics during import                           │
│  Resolution: Move to correct scope (find/create security)                                │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### Conflict Resolution Implementation

```python
@dataclass
class CrosswalkConflict:
    conflict_type: str  # one_to_many, many_to_one, vendor_disagree, scope_mismatch
    vendor: str
    vendor_id_type: str
    vendor_id_value: str
    existing_canonical_id: str
    new_canonical_id: str
    scope: str  # entity, security, listing
    description: Optional[str] = None


class ConflictHandler:
    """Handle crosswalk conflicts."""
    
    def __init__(self, db, merge_service):
        self.db = db
        self.merge_service = merge_service
    
    async def handle(self, conflict: CrosswalkConflict) -> ConflictResolution:
        """Process a conflict and determine resolution."""
        
        # Log the conflict
        conflict_id = await self._create_conflict_record(conflict)
        
        # Attempt automatic resolution
        resolution = await self._try_auto_resolve(conflict)
        
        if resolution.auto_resolved:
            await self._apply_resolution(conflict_id, resolution)
        else:
            await self._queue_for_review(conflict_id, resolution)
        
        return resolution
    
    async def _try_auto_resolve(
        self, 
        conflict: CrosswalkConflict
    ) -> ConflictResolution:
        """Attempt to automatically resolve the conflict."""
        
        if conflict.conflict_type == 'one_to_many':
            return await self._resolve_one_to_many(conflict)
        
        elif conflict.conflict_type == 'many_to_one':
            return await self._resolve_many_to_one(conflict)
        
        elif conflict.conflict_type == 'vendor_disagree':
            return await self._resolve_vendor_disagree(conflict)
        
        elif conflict.conflict_type == 'scope_mismatch':
            return await self._resolve_scope_mismatch(conflict)
        
        return ConflictResolution(auto_resolved=False, reason='unknown_conflict_type')
    
    async def _resolve_one_to_many(
        self, 
        conflict: CrosswalkConflict
    ) -> ConflictResolution:
        """
        Resolve one vendor ID → multiple canonical IDs.
        
        Strategy:
        1. Check if one canonical was merged into another
        2. Check if canonicals are duplicates (same CIK/LEI/ISIN)
        3. If duplicates → auto-merge them
        4. Otherwise → queue for review
        """
        
        existing_id = conflict.existing_canonical_id
        new_id = conflict.new_canonical_id
        
        # Check if one is already merged into the other
        existing_canonical = await get_canonical_entity_id(existing_id)
        new_canonical = await get_canonical_entity_id(new_id)
        
        if existing_canonical == new_canonical:
            # Already resolved via merge chain
            return ConflictResolution(
                auto_resolved=True,
                action='already_merged',
                canonical_id=existing_canonical,
            )
        
        # Check if they're duplicates (same authoritative ID)
        if conflict.scope == 'entity':
            existing_cik = await self._get_identifier(existing_id, 'cik')
            new_cik = await self._get_identifier(new_id, 'cik')
            
            if existing_cik and new_cik and existing_cik == new_cik:
                # Same CIK - they're duplicates, merge them
                merge_id = await self.merge_service.merge_entities(
                    from_entity_id=new_id,
                    to_entity_id=existing_id,
                    merge_type='duplicate',
                    reason=f'Same CIK ({existing_cik}), conflict from {conflict.vendor}',
                )
                
                return ConflictResolution(
                    auto_resolved=True,
                    action='merged',
                    canonical_id=existing_id,
                    merge_id=merge_id,
                )
        
        # Can't auto-resolve
        return ConflictResolution(
            auto_resolved=False,
            reason='different_canonicals_no_common_id',
            candidates=[existing_id, new_id],
        )
    
    async def _resolve_many_to_one(
        self, 
        conflict: CrosswalkConflict
    ) -> ConflictResolution:
        """
        Resolve multiple vendor IDs → one canonical.
        
        This is often OK - vendor may have multiple ID generations or aliases.
        Only flag if the vendor_id_types are the same (suggesting data error).
        """
        
        # Check if same vendor_id_type
        existing_types = await self.db.fetch_all("""
            SELECT DISTINCT vendor_id_type FROM crosswalks
            WHERE vendor = :vendor
              AND (entity_id = :canonical OR security_id = :canonical OR listing_id = :canonical)
        """, {'vendor': conflict.vendor, 'canonical': conflict.existing_canonical_id})
        
        types = [r['vendor_id_type'] for r in existing_types]
        
        if conflict.vendor_id_type in types:
            # Multiple IDs of same type → likely data error
            return ConflictResolution(
                auto_resolved=False,
                reason='duplicate_vendor_id_type',
            )
        
        # Different types → probably OK (add as additional mapping)
        return ConflictResolution(
            auto_resolved=True,
            action='additional_mapping',
            note='Different vendor_id_type, added as additional mapping',
        )
    
    async def _resolve_vendor_disagree(
        self, 
        conflict: CrosswalkConflict
    ) -> ConflictResolution:
        """
        Resolve when different vendors disagree on mapping.
        
        Strategy: Trust the vendor with higher authority for this ID type,
        or the one with more corroborating evidence.
        """
        
        # Define vendor authority ranking per scope
        authority_ranking = {
            'entity': ['sec', 'gleif', 'refinitiv', 'sp', 'factset', 'bloomberg'],
            'security': ['cusip_global', 'openfigi', 'refinitiv', 'factset', 'bloomberg', 'sp'],
            'listing': ['exchange', 'refinitiv', 'factset', 'bloomberg'],
        }
        
        rankings = authority_ranking.get(conflict.scope, [])
        
        existing_vendor = await self._get_mapping_vendor(conflict.existing_canonical_id)
        new_vendor = conflict.vendor
        
        existing_rank = rankings.index(existing_vendor) if existing_vendor in rankings else 999
        new_rank = rankings.index(new_vendor) if new_vendor in rankings else 999
        
        if new_rank < existing_rank:
            # New vendor has higher authority - switch
            return ConflictResolution(
                auto_resolved=True,
                action='switch_to_new',
                canonical_id=conflict.new_canonical_id,
                note=f'{new_vendor} has higher authority than {existing_vendor}',
            )
        
        elif existing_rank < new_rank:
            # Existing vendor has higher authority - keep
            return ConflictResolution(
                auto_resolved=True,
                action='keep_existing',
                canonical_id=conflict.existing_canonical_id,
                note=f'{existing_vendor} has higher authority than {new_vendor}',
            )
        
        # Same rank - queue for review
        return ConflictResolution(
            auto_resolved=False,
            reason='equal_authority_vendors',
        )
    
    async def _resolve_scope_mismatch(
        self, 
        conflict: CrosswalkConflict
    ) -> ConflictResolution:
        """
        Resolve when ID is attached to wrong scope.
        
        Example: FIGI attached to entity, should be on security.
        """
        
        # Determine correct scope from ID type
        id_type_scopes = {
            'figi': 'security',
            'composite_figi': 'security',
            'isin': 'security',
            'cusip': 'security',
            'cik': 'entity',
            'lei': 'entity',
            'ticker': 'listing',
            'ric': 'listing',
        }
        
        correct_scope = id_type_scopes.get(conflict.vendor_id_type)
        
        if not correct_scope:
            return ConflictResolution(
                auto_resolved=False,
                reason='unknown_correct_scope',
            )
        
        if conflict.scope == correct_scope:
            # Not actually a mismatch
            return ConflictResolution(
                auto_resolved=True,
                action='no_action',
                note='Scope is actually correct',
            )
        
        # Find the correct record to attach to
        if correct_scope == 'security' and conflict.scope == 'entity':
            # Need to find a security for this entity
            securities = await self.db.fetch_all("""
                SELECT security_id FROM securities
                WHERE issuer_entity_id = :entity_id AND status = 'active'
            """, {'entity_id': conflict.existing_canonical_id})
            
            if len(securities) == 1:
                # Exactly one security - can auto-fix
                return ConflictResolution(
                    auto_resolved=True,
                    action='move_to_security',
                    canonical_id=securities[0]['security_id'],
                    note='Moved FIGI from entity to its only security',
                )
            
            elif len(securities) == 0:
                # No securities - need to create one
                return ConflictResolution(
                    auto_resolved=False,
                    reason='no_securities_for_entity',
                    action_needed='create_security_then_attach',
                )
            
            else:
                # Multiple securities - can't auto-determine
                return ConflictResolution(
                    auto_resolved=False,
                    reason='multiple_securities',
                    candidates=[s['security_id'] for s in securities],
                )
        
        return ConflictResolution(
            auto_resolved=False,
            reason='complex_scope_mismatch',
        )
    
    async def _create_conflict_record(self, conflict: CrosswalkConflict) -> str:
        """Create a conflict record in the database."""
        
        conflict_id = generate_ulid()
        
        await self.db.execute("""
            INSERT INTO crosswalk_conflicts (
                conflict_id,
                vendor, vendor_id_type, vendor_id_value,
                canonical_id_1, canonical_id_2, canonical_scope,
                conflict_type, description,
                status, detected_at, created_at
            ) VALUES (
                :id,
                :vendor, :type, :value,
                :existing, :new, :scope,
                :conflict_type, :description,
                'open', NOW(), NOW()
            )
        """, {
            'id': conflict_id,
            'vendor': conflict.vendor,
            'type': conflict.vendor_id_type,
            'value': conflict.vendor_id_value,
            'existing': conflict.existing_canonical_id,
            'new': conflict.new_canonical_id,
            'scope': conflict.scope,
            'conflict_type': conflict.conflict_type,
            'description': conflict.description,
        })
        
        return conflict_id
    
    async def _apply_resolution(
        self,
        conflict_id: str,
        resolution: ConflictResolution,
    ) -> None:
        """Apply the resolution to the conflict."""
        
        await self.db.execute("""
            UPDATE crosswalk_conflicts SET
                status = 'resolved',
                resolved_to_id = :resolved_id,
                resolution_method = :method,
                resolution_notes = :notes,
                resolved_at = NOW()
            WHERE conflict_id = :conflict_id
        """, {
            'conflict_id': conflict_id,
            'resolved_id': resolution.canonical_id,
            'method': f'auto:{resolution.action}',
            'notes': resolution.note,
        })
    
    async def _queue_for_review(
        self,
        conflict_id: str,
        resolution: ConflictResolution,
    ) -> None:
        """Queue conflict for manual review."""
        
        await self.db.execute("""
            UPDATE crosswalk_conflicts SET
                status = 'investigating',
                resolution_notes = :notes
            WHERE conflict_id = :conflict_id
        """, {
            'conflict_id': conflict_id,
            'notes': f'Auto-resolution failed: {resolution.reason}',
        })
```

---

## Partial Mappings Strategy

Not all vendor IDs can be resolved immediately. Handle gracefully:

```python
@dataclass
class PartialMapping:
    """A vendor ID without a canonical match yet."""
    vendor: str
    vendor_id_type: str
    vendor_id_value: str
    scope: CrosswalkScope
    hints: dict
    first_seen_at: datetime
    resolution_attempts: int = 0
    last_attempt_at: Optional[datetime] = None


async def store_partial_mapping(mapping: PartialMapping) -> str:
    """Store an unresolved vendor mapping for later resolution."""
    
    partial_id = generate_ulid()
    
    await db.execute("""
        INSERT INTO partial_mappings (
            partial_id, vendor, vendor_id_type, vendor_id_value,
            scope, hints, first_seen_at, resolution_attempts
        ) VALUES (
            :id, :vendor, :type, :value,
            :scope, :hints, NOW(), 0
        )
    """, {
        'id': partial_id,
        'vendor': mapping.vendor,
        'type': mapping.vendor_id_type,
        'value': mapping.vendor_id_value,
        'scope': mapping.scope.value,
        'hints': json.dumps(mapping.hints),
    })
    
    return partial_id


async def retry_partial_mappings(limit: int = 1000) -> RetryResult:
    """
    Periodically retry resolving partial mappings.
    
    Called by scheduled job after new data is loaded.
    """
    
    partials = await db.fetch_all("""
        SELECT * FROM partial_mappings
        WHERE resolution_attempts < 5
          AND (last_attempt_at IS NULL OR last_attempt_at < NOW() - INTERVAL '1 day')
        ORDER BY first_seen_at
        LIMIT :limit
    """, {'limit': limit})
    
    resolved = 0
    failed = 0
    
    for partial in partials:
        hints = json.loads(partial['hints'])
        scope = CrosswalkScope(partial['scope'])
        
        canonical_id = None
        
        if scope == CrosswalkScope.ENTITY:
            canonical_id = await _resolve_to_entity(hints)
        elif scope == CrosswalkScope.SECURITY:
            canonical_id = await _resolve_to_security(hints)
        elif scope == CrosswalkScope.LISTING:
            canonical_id = await _resolve_to_listing(hints)
        
        if canonical_id:
            # Success! Create crosswalk and remove partial
            await _upsert_crosswalk(VendorIdMapping(
                vendor=partial['vendor'],
                vendor_id_type=partial['vendor_id_type'],
                vendor_id_value=partial['vendor_id_value'],
                scope=scope,
                entity_id=canonical_id if scope == CrosswalkScope.ENTITY else None,
                security_id=canonical_id if scope == CrosswalkScope.SECURITY else None,
                listing_id=canonical_id if scope == CrosswalkScope.LISTING else None,
                mapping_source='partial_retry',
            ))
            
            await db.execute(
                "DELETE FROM partial_mappings WHERE partial_id = :id",
                {'id': partial['partial_id']}
            )
            resolved += 1
        
        else:
            # Still unresolved
            await db.execute("""
                UPDATE partial_mappings SET
                    resolution_attempts = resolution_attempts + 1,
                    last_attempt_at = NOW()
                WHERE partial_id = :id
            """, {'id': partial['partial_id']})
            failed += 1
    
    return RetryResult(resolved=resolved, failed=failed)
```

---

## Provenance Tracking

Every crosswalk records where the mapping came from:

```sql
-- Provenance fields in crosswalks table:
-- mapping_source: 'vendor_file', 'api_lookup', 'manual', 'inference', 'merge_transfer'
-- mapping_method: 'exact', 'derived', 'inferred', 'fuzzy'
-- confidence: 0.0-1.0

-- Query: Show all mappings with their provenance
SELECT 
    c.vendor,
    c.vendor_id_type,
    c.vendor_id_value,
    COALESCE(e.primary_name, s.name, l.ticker) AS canonical_name,
    c.mapping_source,
    c.mapping_method,
    c.confidence,
    c.first_seen_at,
    c.last_seen_at
FROM crosswalks c
LEFT JOIN entities e ON e.entity_id = c.entity_id
LEFT JOIN securities s ON s.security_id = c.security_id
LEFT JOIN listings l ON l.listing_id = c.listing_id
WHERE c.vendor = 'factset'
ORDER BY c.confidence DESC, c.last_seen_at DESC;
```

---

## Next Document

→ [04_MENTIONS_PRIVATE_ENTITIES_WORKFLOW.md](04_MENTIONS_PRIVATE_ENTITIES_WORKFLOW.md) - Handling private company mentions
