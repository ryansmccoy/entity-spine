# EntitySpine Ingestion Test Scenarios

This document describes complex, real-world test scenarios to validate the ingestion system handles all edge cases correctly.

---

## Test Scenario 1: Multi-Source Entity Resolution

### Setup: Apple Inc from 4 Sources

We have data for Apple Inc from:
1. **Bloomberg** (2016-05-30) - Highest priority
2. **FactSet** (2019-08-01) - Medium priority  
3. **Thomson** (2020-08-30) - Lower priority
4. **SEC EDGAR** (2024-01-01) - Authoritative for CIK

### Test Data

**Bloomberg:**
```
NAME|ID_BB_SEC_NUM_DES|FEED_SOURCE|ID_BB_UNIQUE|SECURITY_TYP|ID_BB_GLOBAL
Apple Inc|AAPL|US|EQ0010169500001000|Common Stock|BBG000B9XRY4
```

**FactSet:**
```
Identifier	Name	Country	State	SIC	Website
AAPL-US	Apple Inc.	United States of America	CA	3571	http://www.apple.com
```

**Thomson TTL:**
```
<https://permid.org/1-4295905573> a tr-org:Organization ;
    tr-org:hasOrganizationName "Apple Inc" ;
    tr-org:isDomiciledIn <http://sws.geonames.org/6252001/> .
```

**SEC EDGAR:**
```
CIK: 0000320193
Conformed Name: APPLE INC
SIC: 3571 - ELECTRONIC COMPUTERS
State: CA
```

### Expected Results

After ingesting all 4 sources (in priority order):

```json
{
  "entity_id": "ent_xxx",
  "primary_name": "Apple Inc",           // From Bloomberg (priority 1)
  "legal_name": "APPLE INC",             // From SEC (authoritative)
  "entity_type": "ORGANIZATION",
  "status": "ACTIVE",
  "jurisdiction": "US",
  "sic_code": "3571",                    // From SEC (authoritative)
  
  "identifiers": [
    {"scheme": "CIK", "value": "0000320193", "source": "sec_edgar"},
    {"scheme": "BBUID", "value": "EQ0010169500001000", "source": "bloomberg"},
    {"scheme": "FIGI", "value": "BBG000B9XRY4", "source": "bloomberg"},
    {"scheme": "PERMID", "value": "4295905573", "source": "thomson"}
  ],
  
  "securities": [{
    "security_type": "COMMON_STOCK",
    "description": "Apple Inc Common Stock",
    "listings": [{
      "mic": "XNAS",
      "ticker": "AAPL",
      "is_primary": true
    }]
  }],
  
  "extended_attributes": {
    "website": "http://www.apple.com",   // From FactSet
    "state": "CA"                        // From FactSet + SEC
  },
  
  "provenance": {
    "sources": ["bloomberg", "factset", "thomson", "sec_edgar"],
    "version_count": 4,
    "last_updated": "2024-01-01"
  }
}
```

### Test Assertions

1. ✅ `primary_name` is "Apple Inc" (Bloomberg, not "APPLE INC" from SEC)
2. ✅ All 4 identifier schemes are present
3. ✅ No duplicate entities created (resolution by name + ticker worked)
4. ✅ Version history shows 4 ingestion events
5. ✅ Each field has provenance tracking

---

## Test Scenario 2: Corporate Merger (Beats → Apple)

### Timeline

- **2006**: Beats Electronics founded
- **2008-2014**: Beats operates independently, has FactSet/Bloomberg data
- **2014-08-01**: Apple acquires Beats for $3B
- **2014-08+**: Beats data should resolve to Apple

### Test Data

**Pre-merger (FactSet 2014-03-01):**
```
Identifier	Name	Country	Entity Type
BEATS-US	Beats Electronics LLC	United States	Private Company
```

**Post-merger news feed (2014-08-01):**
```
{
  "event_type": "MERGER",
  "acquired_entity": "Beats Electronics LLC",
  "acquiring_entity": "Apple Inc",
  "effective_date": "2014-08-01",
  "deal_value_usd": 3000000000
}
```

### Expected State After Processing

**Beats entity:**
```json
{
  "entity_id": "ent_beats_001",
  "primary_name": "Beats Electronics LLC",
  "status": "MERGED_INTO",
  "successor_entity_id": "ent_apple_001",
  "dissolution_date": "2014-08-01",
  
  "merger_info": {
    "merged_into": "ent_apple_001",
    "merged_into_name": "Apple Inc",
    "effective_date": "2014-08-01",
    "deal_type": "acquisition"
  }
}
```

**Apple entity (updated):**
```json
{
  "entity_id": "ent_apple_001",
  "primary_name": "Apple Inc",
  "status": "ACTIVE",
  
  "acquired_entities": [
    {
      "entity_id": "ent_beats_001",
      "name": "Beats Electronics LLC",
      "acquisition_date": "2014-08-01"
    }
  ]
}
```

### Test Assertions

1. ✅ Beats status changed to `MERGED_INTO`
2. ✅ Beats has `successor_entity_id` pointing to Apple
3. ✅ Apple's history shows acquisition
4. ✅ Query for "Beats" returns Apple (with historical note)
5. ✅ Pre-merger Beats data preserved in version history
6. ✅ Post-merger data updates route to Apple

---

## Test Scenario 3: PayPal Spin-off from eBay

### Timeline

- **2002**: eBay acquires PayPal
- **2002-2015**: PayPal is a subsidiary, no separate entity
- **2015-07-20**: PayPal spun off as independent company
- **2015-07+**: PayPal has separate stock (PYPL), entity

### Test Data

**Pre-spinoff (FactSet 2015-06-01):**
```
Identifier	Name	Type	Parent
EBAY-US	eBay Inc	Public	-
```

**Post-spinoff (FactSet 2015-08-01):**
```
Identifier	Name	Type	Parent	Spin_From
EBAY-US	eBay Inc	Public	-	-
PYPL-US	PayPal Holdings Inc	Public	-	EBAY-US
```

**Bloomberg (2015-08-01):**
```
NAME|TICKER|SECURITY_TYP|SPIN_DATE|SPIN_PARENT
PayPal Holdings Inc|PYPL|Common Stock|2015-07-20|EBAY
```

### Expected State After Processing

**New PayPal entity:**
```json
{
  "entity_id": "ent_pypl_001",
  "primary_name": "PayPal Holdings Inc",
  "entity_type": "ORGANIZATION",
  "status": "ACTIVE",
  "formation_date": "2015-07-20",
  
  "spinoff_info": {
    "spun_from_entity_id": "ent_ebay_001",
    "spun_from_name": "eBay Inc",
    "effective_date": "2015-07-20"
  },
  
  "securities": [{
    "security_type": "COMMON_STOCK",
    "listings": [{
      "mic": "XNAS",
      "ticker": "PYPL",
      "listing_date": "2015-07-20"
    }]
  }]
}
```

**eBay entity (updated):**
```json
{
  "entity_id": "ent_ebay_001",
  "primary_name": "eBay Inc",
  "status": "ACTIVE",
  
  "spinoff_history": [{
    "entity_id": "ent_pypl_001",
    "name": "PayPal Holdings Inc",
    "spinoff_date": "2015-07-20"
  }]
}
```

### Test Assertions

1. ✅ New PayPal entity created (not merged with eBay)
2. ✅ PayPal has `formation_date` = spinoff date
3. ✅ PayPal references eBay as parent
4. ✅ eBay's spinoff history includes PayPal
5. ✅ PYPL security/listing properly linked to PayPal entity
6. ✅ Historical queries for "PayPal" before 2015 return nothing (or eBay subsidiary note)

---

## Test Scenario 4: Name Change (RIM → BlackBerry)

### Timeline

- **1984**: Research In Motion founded
- **2013-01-30**: Name changed to BlackBerry Limited
- **Present**: Still operating as BlackBerry

### Test Data

**FactSet 2012:**
```
Identifier	Name	Country
RIM-CA	Research In Motion Limited	Canada
```

**FactSet 2013:**
```
Identifier	Name	Country	Former_Name	Name_Change_Date
BB-CA	BlackBerry Limited	Canada	Research In Motion Limited	2013-01-30
```

**Bloomberg 2024:**
```
NAME|TICKER|ID_BB_UNIQUE
BlackBerry Limited|BB|EQ0019724200001000
```

### Expected State

```json
{
  "entity_id": "ent_bb_001",
  "primary_name": "BlackBerry Limited",       // Current name
  "entity_type": "ORGANIZATION",
  "status": "ACTIVE",
  "jurisdiction": "CA",
  
  "name_history": [
    {
      "name": "BlackBerry Limited",
      "valid_from": "2013-01-30",
      "valid_to": null,
      "is_current": true
    },
    {
      "name": "Research In Motion Limited",
      "valid_from": "1984-03-07",
      "valid_to": "2013-01-30",
      "is_current": false
    }
  ],
  
  "securities": [{
    "listings": [
      {
        "mic": "XTSE",
        "ticker": "BB",          // Current ticker
        "is_primary": true,
        "valid_from": "2013-01-30"
      },
      {
        "mic": "XTSE",
        "ticker": "RIM",         // Historical ticker
        "is_primary": false,
        "valid_from": "1999-01-01",
        "valid_to": "2013-01-30"
      }
    ]
  }]
}
```

### Test Assertions

1. ✅ Single entity (not two entities for RIM and BB)
2. ✅ Current name is "BlackBerry Limited"
3. ✅ Historical name "Research In Motion" preserved
4. ✅ Search for "RIM" returns BlackBerry entity
5. ✅ Search for "Research In Motion" returns BlackBerry entity
6. ✅ Ticker history preserved (RIM → BB)

---

## Test Scenario 5: Duplicate Detection & Resolution

### Problem

Multiple sources provide slightly different names:
- Bloomberg: "Microsoft Corp"
- FactSet: "Microsoft Corporation"  
- Thomson: "MICROSOFT CORPORATION"
- SEC: "MICROSOFT CORP"

### Test Data

**All sources provide MSFT data with different name formats:**

```
Source     | Name                    | Identifier
-----------|-------------------------|----------------
Bloomberg  | Microsoft Corp          | BBUID: EQ001017...
FactSet    | Microsoft Corporation   | Ticker: MSFT-US
Thomson    | MICROSOFT CORPORATION   | PermID: 4295907168
SEC EDGAR  | MICROSOFT CORP          | CIK: 0000789019
```

### Expected Behavior

1. **Matching heuristics applied:**
   - Same ticker (MSFT)
   - Similar names (fuzzy match > 0.9)
   - Same jurisdiction (US)

2. **Single entity created:**
```json
{
  "entity_id": "ent_msft_001",
  "primary_name": "Microsoft Corp",        // From Bloomberg (highest priority)
  "alternate_names": [
    "Microsoft Corporation",
    "MICROSOFT CORPORATION",
    "MICROSOFT CORP"
  ],
  
  "identifiers": [
    {"scheme": "BBUID", "value": "EQ0010174300001000"},
    {"scheme": "PERMID", "value": "4295907168"},
    {"scheme": "CIK", "value": "0000789019"}
  ],
  
  "match_evidence": {
    "matched_by": ["ticker", "name_similarity", "jurisdiction"],
    "confidence": 0.98
  }
}
```

### Test Assertions

1. ✅ Only ONE entity created for Microsoft
2. ✅ All alternate names preserved
3. ✅ All identifiers linked to same entity
4. ✅ Match confidence recorded
5. ✅ No orphan records from any source

---

## Test Scenario 6: Conflicting Data Resolution

### Problem

Sources disagree on data:

```
Field      | Bloomberg (2023) | FactSet (2022) | Resolution
-----------|------------------|----------------|------------------
Name       | Meta Platforms   | Facebook Inc   | Bloomberg (newer + higher priority)
Status     | ACTIVE           | ACTIVE         | Agree
SIC Code   | 7370             | 7374           | Bloomberg (higher priority)
Employees  | 77,805           | 71,970         | Bloomberg (newer data)
```

### Expected Resolution

```json
{
  "entity_id": "ent_meta_001",
  "primary_name": "Meta Platforms Inc",    // Bloomberg wins
  "sic_code": "7370",                      // Bloomberg wins
  
  "field_history": {
    "primary_name": [
      {"value": "Meta Platforms Inc", "source": "bloomberg", "as_of": "2023-01-01"},
      {"value": "Facebook Inc", "source": "factset", "as_of": "2022-01-01"}
    ],
    "sic_code": [
      {"value": "7370", "source": "bloomberg", "as_of": "2023-01-01"},
      {"value": "7374", "source": "factset", "as_of": "2022-01-01"}
    ]
  },
  
  "resolution_log": [
    {
      "field": "primary_name",
      "chosen_value": "Meta Platforms Inc",
      "chosen_source": "bloomberg",
      "reason": "Higher priority source (bloomberg=1 vs factset=2)",
      "rejected_values": [{"value": "Facebook Inc", "source": "factset"}]
    }
  ]
}
```

### Test Assertions

1. ✅ Bloomberg value chosen (higher priority)
2. ✅ FactSet value preserved in history
3. ✅ Resolution reason logged
4. ✅ Both temporal dates preserved
5. ✅ Can query historical state at any point

---

## Test Scenario 7: Data Versioning & Rollback

### Timeline

1. **T1 (2023-01-01)**: Initial Bloomberg load - Company status ACTIVE
2. **T2 (2023-06-01)**: FactSet update - Company status INACTIVE (error!)
3. **T3 (2023-06-02)**: Detect error, rollback to T1 state
4. **T4 (2023-07-01)**: Correct FactSet reload - Status ACTIVE

### Test Operations

```python
# T1: Initial load
ingest(bloomberg_file, as_of="2023-01-01")
# Entity version 1: status=ACTIVE

# T2: Bad data
ingest(factset_file_bad, as_of="2023-06-01")  
# Entity version 2: status=INACTIVE

# T3: Rollback
rollback_entity(entity_id, to_version=1)
# Entity version 3: status=ACTIVE (restored)

# T4: Correct load
ingest(factset_file_corrected, as_of="2023-07-01")
# Entity version 4: status=ACTIVE (confirmed)
```

### Expected Version History

```json
{
  "entity_id": "ent_xxx",
  "current_version": 4,
  
  "versions": [
    {
      "version": 1,
      "status": "ACTIVE",
      "source": "bloomberg",
      "ingested_at": "2023-01-01",
      "change_type": "CREATE"
    },
    {
      "version": 2,
      "status": "INACTIVE",
      "source": "factset",
      "ingested_at": "2023-06-01",
      "change_type": "UPDATE",
      "changed_fields": ["status"]
    },
    {
      "version": 3,
      "status": "ACTIVE",
      "source": "rollback",
      "ingested_at": "2023-06-02",
      "change_type": "ROLLBACK",
      "rollback_from": 2,
      "rollback_to": 1,
      "reason": "Erroneous status in FactSet feed"
    },
    {
      "version": 4,
      "status": "ACTIVE",
      "source": "factset",
      "ingested_at": "2023-07-01",
      "change_type": "UPDATE",
      "note": "Corrected feed"
    }
  ]
}
```

### Test Assertions

1. ✅ Version history preserved (all 4 versions)
2. ✅ Rollback creates new version (not delete)
3. ✅ Rollback reason captured
4. ✅ Can query entity state at any version
5. ✅ Audit trail complete

---

## Test Scenario 8: Extended Attributes Handling

### Test Data

**Bloomberg has custom fields:**
```
NAME|TICKER|MARKET_SECTOR_DES|COMPANY_WEBSITE|EMPLOYEES|INDUSTRY_GROUP
Apple Inc|AAPL|Technology|https://www.apple.com|164000|Computers
```

### Expected Handling

```json
{
  "entity_id": "ent_xxx",
  "primary_name": "Apple Inc",
  
  // Core fields (in schema)
  "securities": [...],
  
  // Extended attributes (dynamic)
  "extended_attributes": [
    {
      "name": "market_sector",
      "value": "Technology",
      "type": "string",
      "source": "bloomberg",
      "source_date": "2023-01-01"
    },
    {
      "name": "website",
      "value": "https://www.apple.com",
      "type": "url",
      "source": "bloomberg",
      "source_date": "2023-01-01"
    },
    {
      "name": "employees",
      "value": 164000,
      "type": "number",
      "source": "bloomberg",
      "source_date": "2023-01-01"
    },
    {
      "name": "industry_group",
      "value": "Computers",
      "type": "string",
      "source": "bloomberg",
      "source_date": "2023-01-01"
    }
  ]
}
```

### Test Assertions

1. ✅ Non-schema fields captured in extended_attributes
2. ✅ Correct type inference (url, number, string)
3. ✅ Source tracking on each attribute
4. ✅ Queryable by attribute name
5. ✅ No schema migration needed for new fields

---

## Running the Test Suite

```bash
# Run all ingestion tests
pytest entityspine/tests/test_ingestion/ -v

# Run specific scenario
pytest entityspine/tests/test_ingestion/test_scenario_merger.py -v

# Run with coverage
pytest entityspine/tests/test_ingestion/ --cov=entityspine.data --cov-report=html
```

---

## Test Data Files Location

```
entityspine/tests/fixtures/ingestion/
├── scenario_1_multi_source/
│   ├── bloomberg_apple.txt
│   ├── factset_apple.csv
│   ├── thomson_apple.ttl
│   └── sec_apple.json
├── scenario_2_merger/
│   ├── beats_pre_merger.csv
│   └── merger_event.json
├── scenario_3_spinoff/
│   ├── ebay_pre_spinoff.csv
│   └── paypal_post_spinoff.csv
├── scenario_4_name_change/
│   ├── rim_2012.csv
│   └── blackberry_2013.csv
├── scenario_5_duplicates/
│   └── microsoft_all_sources.json
├── scenario_6_conflicts/
│   └── meta_conflicting.json
├── scenario_7_versioning/
│   └── versioning_timeline.json
└── scenario_8_extended/
    └── bloomberg_extended_fields.txt
```

---

## Implementation Priority

1. **Phase 1**: Basic multi-source (Scenario 1, 5)
2. **Phase 2**: Version control (Scenario 7)
3. **Phase 3**: Conflict resolution (Scenario 6)
4. **Phase 4**: Corporate actions (Scenario 2, 3, 4)
5. **Phase 5**: Extended attributes (Scenario 8)
