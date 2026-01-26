# Entity Master - FeedSpine Integration

How FeedSpine powers Entity Master's data ingestion pipeline.

---

## Why FeedSpine?

FeedSpine provides exactly what Entity Master needs:

| Capability | How Entity Master Uses It |
|------------|---------------------------|
| **Deduplication** | Same ticker/CIK won't create duplicates |
| **Sightings** | Track when entities were first/last seen |
| **Change Detection** | Identify new listings, delistings |
| **Medallion Architecture** | Bronze → Silver → Gold entity processing |
| **Storage Agnostic** | Same feeds work with SQLite, DuckDB, Postgres |
| **Scheduling** | Automated daily/weekly/monthly updates |

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                         ENTITY MASTER + FEEDSPINE                             │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  DATA SOURCES                        FEEDSPINE                 ENTITY MASTER │
│  ────────────                        ─────────                 ───────────── │
│                                                                               │
│  ┌─────────────────┐                                                          │
│  │ SEC EDGAR       │──┐                                                       │
│  │ company_tickers │  │     ┌─────────────────────────────┐                   │
│  └─────────────────┘  │     │                             │                   │
│                       │     │  ┌─────────────────────┐    │                   │
│  ┌─────────────────┐  ├────▶│  │   BRONZE LAYER      │    │                   │
│  │ SEC EDGAR       │  │     │  │   (Raw Records)     │    │                   │
│  │ company_tickers │──┤     │  │                     │    │                   │
│  │ _exchange.json  │  │     │  │ • Deduplicated      │    │    ┌───────────┐  │
│  └─────────────────┘  │     │  │ • capture_date      │    │    │           │  │
│                       │     │  │ • natural_key       │    │    │  ENTITY   │  │
│  ┌─────────────────┐  │     │  └─────────┬───────────┘    │    │  MASTER   │  │
│  │ GLEIF           │──┤     │            │                │───▶│  SERVICE  │  │
│  │ Golden Copy     │  │     │            ▼                │    │           │  │
│  └─────────────────┘  │     │  ┌─────────────────────┐    │    │ • resolve │  │
│                       │     │  │   SILVER LAYER      │    │    │ • search  │  │
│  ┌─────────────────┐  │     │  │   (Normalized)      │    │    │ • enrich  │  │
│  │ OpenFIGI        │──┤     │  │                     │    │    │ • graph   │  │
│  │ Bulk Mapping    │  │     │  │ • Schema validated  │    │    │           │  │
│  └─────────────────┘  │     │  │ • Cross-referenced  │    │    └───────────┘  │
│                       │     │  │ • Merged duplicates │    │                   │
│  ┌─────────────────┐  │     │  └─────────┬───────────┘    │                   │
│  │ Your Bloomberg  │──┤     │            │                │                   │
│  │ Files (G:\)     │  │     │            ▼                │                   │
│  └─────────────────┘  │     │  ┌─────────────────────┐    │                   │
│                       │     │  │   GOLD LAYER        │    │                   │
│  ┌─────────────────┐  │     │  │   (Entity Master)   │    │                   │
│  │ Your Thomson    │──┘     │  │                     │    │                   │
│  │ Files (G:\)     │        │  │ • Canonical entities│    │                   │
│  └─────────────────┘        │  │ • All identifiers   │    │                   │
│                             │  │ • Relationships     │    │                   │
│                             │  │ • Change history    │    │                   │
│                             │  └─────────────────────┘    │                   │
│                             │                             │                   │
│                             └─────────────────────────────┘                   │
│                                                                               │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Feed Definitions

### SEC Ticker Feed

```python
# entity_master/feeds/sec_tickers.py

from datetime import UTC, datetime
from feedspine import FeedAdapter, RecordCandidate, Metadata
import httpx


class SECTickersFeed(FeedAdapter):
    """SEC company_tickers_exchange.json feed.
    
    Source: https://www.sec.gov/files/company_tickers_exchange.json
    Updates: Real-time (reflects current SEC database)
    Records: ~10,000 public companies
    """
    
    feed_id = "sec-tickers"
    name = "SEC Company Tickers"
    
    # Schedule: Daily at 6 AM ET (after SEC updates)
    schedule = "0 6 * * *"
    
    async def fetch(self) -> list[RecordCandidate]:
        """Fetch current SEC ticker data."""
        url = "https://www.sec.gov/files/company_tickers_exchange.json"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers={"User-Agent": "EntityMaster/1.0 (contact@example.com)"},
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
        
        # Format: {"fields": ["cik","name","ticker","exchange"], "data": [[...]]}
        records = []
        capture_time = datetime.now(UTC)
        
        for row in data["data"]:
            cik, name, ticker, exchange = row
            cik_padded = str(cik).zfill(10)
            
            # Natural key: CIK (stable, unique)
            natural_key = f"cik:{cik_padded}"
            
            records.append(RecordCandidate(
                natural_key=natural_key,
                published_at=capture_time,
                content={
                    "cik": cik_padded,
                    "name": name,
                    "ticker": ticker,
                    "exchange": exchange,
                    "source": "sec_tickers_exchange",
                },
                metadata=Metadata(
                    source=self.feed_id,
                    tags=["sec", "ticker", "entity"],
                ),
            ))
        
        return records


class SECSubmissionsFeed(FeedAdapter):
    """SEC CIK submissions metadata feed.
    
    Source: https://data.sec.gov/submissions/CIK{cik}.json
    Contains: Detailed company info, filing history, SIC codes
    """
    
    feed_id = "sec-submissions"
    name = "SEC Company Submissions"
    
    # Only run for entities that need enrichment
    schedule = None  # On-demand
    
    async def fetch(self, ciks: list[str]) -> list[RecordCandidate]:
        """Fetch SEC submission data for specific CIKs."""
        records = []
        
        async with httpx.AsyncClient() as client:
            for cik in ciks:
                url = f"https://data.sec.gov/submissions/CIK{cik.zfill(10)}.json"
                
                try:
                    response = await client.get(
                        url,
                        headers={"User-Agent": "EntityMaster/1.0"},
                        timeout=30.0,
                    )
                    response.raise_for_status()
                    data = response.json()
                    
                    records.append(RecordCandidate(
                        natural_key=f"cik:{cik.zfill(10)}",
                        published_at=datetime.now(UTC),
                        content={
                            "cik": cik.zfill(10),
                            "name": data.get("name"),
                            "sic": data.get("sic"),
                            "sic_description": data.get("sicDescription"),
                            "state_of_incorporation": data.get("stateOfIncorporation"),
                            "fiscal_year_end": data.get("fiscalYearEnd"),
                            "ein": data.get("ein"),
                            "tickers": data.get("tickers", []),
                            "exchanges": data.get("exchanges", []),
                            "category": data.get("category"),
                        },
                        metadata=Metadata(source=self.feed_id),
                    ))
                except Exception as e:
                    # Log error but continue
                    pass
        
        return records
```

### GLEIF LEI Feed

```python
# entity_master/feeds/gleif.py

from datetime import UTC, datetime
from pathlib import Path
import json
import zipfile
from feedspine import FeedAdapter, RecordCandidate, Metadata
import httpx


class GLEIFGoldenCopyFeed(FeedAdapter):
    """GLEIF Golden Copy bulk LEI data.
    
    Source: https://goldencopy.gleif.org/
    Updates: 3x daily (we run monthly for bulk)
    Records: ~3.2 million LEIs
    Format: JSON Lines (compressed)
    License: CC0 (public domain)
    """
    
    feed_id = "gleif-lei"
    name = "GLEIF LEI Golden Copy"
    
    # Schedule: Monthly on 1st at midnight
    schedule = "0 0 1 * *"
    
    # Golden copy URLs
    GOLDEN_COPY_URL = "https://goldencopy.gleif.org/api/v2/golden-copies/publishes/latest"
    
    async def fetch(self) -> list[RecordCandidate]:
        """Download and parse GLEIF golden copy."""
        
        # Get latest golden copy metadata
        async with httpx.AsyncClient() as client:
            meta_response = await client.get(self.GOLDEN_COPY_URL)
            meta = meta_response.json()
            
            # Download LEI-CDF file (JSON lines)
            lei_url = meta["data"]["lei2"]["full_file"]["json"]["url"]
            
            # Stream download (file is ~3GB compressed)
            records = []
            async with client.stream("GET", lei_url) as response:
                # Parse JSON lines
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    
                    try:
                        lei_record = json.loads(line)
                        record = self._parse_lei_record(lei_record)
                        if record:
                            records.append(record)
                    except json.JSONDecodeError:
                        continue
        
        return records
    
    def _parse_lei_record(self, lei_data: dict) -> RecordCandidate | None:
        """Parse a single LEI record."""
        lei = lei_data.get("LEI")
        if not lei:
            return None
        
        entity = lei_data.get("Entity", {})
        legal_name = entity.get("LegalName", {}).get("$", "")
        
        return RecordCandidate(
            natural_key=f"lei:{lei}",
            published_at=datetime.now(UTC),
            content={
                "lei": lei,
                "legal_name": legal_name,
                "legal_jurisdiction": entity.get("LegalJurisdiction"),
                "entity_status": entity.get("EntityStatus"),
                "entity_category": entity.get("EntityCategory"),
                "legal_form": entity.get("LegalForm", {}).get("EntityLegalFormCode"),
                "registered_address": entity.get("LegalAddress", {}),
                "headquarters_address": entity.get("HeadquartersAddress", {}),
                "registration_authority": lei_data.get("Registration", {}).get("RegistrationAuthorityID"),
                "initial_registration_date": lei_data.get("Registration", {}).get("InitialRegistrationDate"),
                "last_update_date": lei_data.get("Registration", {}).get("LastUpdateDate"),
            },
            metadata=Metadata(
                source=self.feed_id,
                tags=["gleif", "lei", "entity"],
            ),
        )


class GLEIFMappingFeed(FeedAdapter):
    """GLEIF ISIN-to-LEI mapping feed.
    
    Source: https://www.gleif.org/en/lei-data/lei-mapping/download-isin-to-lei-relationship-files
    Maps: ISIN ↔ LEI
    """
    
    feed_id = "gleif-isin-mapping"
    name = "GLEIF ISIN-to-LEI Mapping"
    
    schedule = "0 0 * * 0"  # Weekly on Sunday
    
    async def fetch(self) -> list[RecordCandidate]:
        """Download ISIN-to-LEI mapping."""
        # Implementation similar to golden copy
        ...
```

### Bloomberg/Thomson File Feed

```python
# entity_master/feeds/local_files.py

from datetime import UTC, datetime
from pathlib import Path
import csv
from feedspine import FeedAdapter, RecordCandidate, Metadata


class BloombergFileFeed(FeedAdapter):
    """Load Bloomberg BSYM files from local directory.
    
    Format: Pipe-delimited (|) CSV
    Source: G:\BLOOMBERG\*.csv (or configured path)
    """
    
    feed_id = "bloomberg-local"
    name = "Bloomberg Local Files"
    
    schedule = None  # Manual trigger only
    
    def __init__(self, directory: str = "G:\\BLOOMBERG"):
        super().__init__()
        self.directory = Path(directory)
    
    async def fetch(self) -> list[RecordCandidate]:
        """Parse all Bloomberg files in directory."""
        records = []
        
        for file_path in self.directory.glob("*.csv"):
            file_records = self._parse_file(file_path)
            records.extend(file_records)
        
        return records
    
    def _parse_file(self, file_path: Path) -> list[RecordCandidate]:
        """Parse a single Bloomberg file."""
        records = []
        
        with open(file_path, "r", encoding="utf-8") as f:
            # Pipe-delimited
            reader = csv.DictReader(f, delimiter="|")
            
            for row in reader:
                # Skip comment lines
                if row.get("NAME", "").startswith("#"):
                    continue
                
                figi = row.get("ID_BB_GLOBAL", "").strip()
                if not figi:
                    continue
                
                records.append(RecordCandidate(
                    natural_key=f"figi:{figi}",
                    published_at=datetime.now(UTC),
                    content={
                        "figi": figi,
                        "name": row.get("NAME", "").strip(),
                        "bb_unique": row.get("ID_BB_UNIQUE", "").strip(),
                        "security_type": row.get("SECURITY_TYP", "").strip(),
                        "market_sector": row.get("MARKET_SECTOR_DES", "").strip(),
                        "composite_figi": row.get("COMPOSITE_ID_BB_GLOBAL", "").strip(),
                        "source_file": file_path.name,
                    },
                    metadata=Metadata(
                        source=self.feed_id,
                        tags=["bloomberg", "figi", "security"],
                    ),
                ))
        
        return records


class ThomsonFileFeed(FeedAdapter):
    """Load Thomson Reuters PermID files from local directory.
    
    Source: G:\THOMSON\*.csv (or configured path)
    """
    
    feed_id = "thomson-local"
    name = "Thomson Local Files"
    
    schedule = None  # Manual trigger only
    
    def __init__(self, directory: str = "G:\\THOMSON"):
        super().__init__()
        self.directory = Path(directory)
    
    async def fetch(self) -> list[RecordCandidate]:
        """Parse all Thomson files in directory."""
        records = []
        
        for file_path in self.directory.glob("*.csv"):
            file_records = self._parse_file(file_path)
            records.extend(file_records)
        
        return records
    
    def _parse_file(self, file_path: Path) -> list[RecordCandidate]:
        """Parse a single Thomson file."""
        records = []
        
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                permid = row.get("PermID", row.get("permid", "")).strip()
                if not permid:
                    continue
                
                records.append(RecordCandidate(
                    natural_key=f"permid:{permid}",
                    published_at=datetime.now(UTC),
                    content={
                        "permid": permid,
                        "name": row.get("LegalName", row.get("Name", "")).strip(),
                        "ticker": row.get("Ticker", "").strip(),
                        "exchange": row.get("Exchange", "").strip(),
                        "isin": row.get("ISIN", "").strip(),
                        "lei": row.get("LEI", "").strip(),
                        "country": row.get("Country", "").strip(),
                        "source_file": file_path.name,
                    },
                    metadata=Metadata(
                        source=self.feed_id,
                        tags=["thomson", "permid", "entity"],
                    ),
                ))
        
        return records
```

---

## Change Detection

FeedSpine's sighting model enables powerful change detection:

```python
# entity_master/changes.py

from datetime import datetime, timedelta
from feedspine import FeedSpine, Query, Layer


class ChangeDetector:
    """Detect entity changes using FeedSpine sightings."""
    
    def __init__(self, feedspine: FeedSpine):
        self.fs = feedspine
    
    async def new_entities_since(self, since: datetime) -> list[dict]:
        """Find entities first seen after a date.
        
        Uses FeedSpine's sighting tracking to identify new records.
        """
        query = Query(
            layer=Layer.BRONZE,
            feed_id="sec-tickers",
            first_seen_after=since,
        )
        
        new_records = []
        async for record in self.fs.query(query):
            new_records.append(record.content)
        
        return new_records
    
    async def missing_entities(self, feed_id: str = "sec-tickers") -> list[dict]:
        """Find entities not seen in the latest capture.
        
        These might be delistings, acquisitions, or data issues.
        """
        # Get latest capture date
        latest = await self.fs.get_latest_capture_date(feed_id)
        
        # Find records not seen in latest
        query = Query(
            layer=Layer.BRONZE,
            feed_id=feed_id,
            last_seen_before=latest,
        )
        
        missing = []
        async for record in self.fs.query(query):
            missing.append(record.content)
        
        return missing
    
    async def changed_tickers(self, since: datetime) -> list[dict]:
        """Find entities whose ticker changed.
        
        Compares historical snapshots to detect ticker symbol changes.
        """
        # Query entity history
        # Implementation depends on how history is stored
        ...
    
    async def generate_change_report(self, since: datetime = None) -> dict:
        """Generate a comprehensive change report.
        
        Returns:
            {
                "new_entities": [...],
                "missing_entities": [...],
                "ticker_changes": [...],
                "name_changes": [...],
                "capture_date": "2024-01-15",
                "since": "2024-01-08",
            }
        """
        if since is None:
            since = datetime.now() - timedelta(days=7)
        
        return {
            "new_entities": await self.new_entities_since(since),
            "missing_entities": await self.missing_entities(),
            "ticker_changes": await self.changed_tickers(since),
            "since": since.isoformat(),
            "generated_at": datetime.now().isoformat(),
        }
```

---

## Medallion Processing

### Bronze → Silver Transformer

```python
# entity_master/transformers/entity_normalizer.py

from feedspine import Enricher, Record


class EntityNormalizerEnricher(Enricher):
    """Transform bronze records to silver layer entities.
    
    Bronze: Raw records from each feed
    Silver: Normalized entity format, cross-referenced
    """
    
    async def enrich(self, record: Record) -> Record:
        """Normalize a bronze record to silver format."""
        content = record.content
        source = record.metadata.source
        
        # Normalize based on source
        if source == "sec-tickers":
            normalized = self._normalize_sec(content)
        elif source == "gleif-lei":
            normalized = self._normalize_gleif(content)
        elif source == "bloomberg-local":
            normalized = self._normalize_bloomberg(content)
        elif source == "thomson-local":
            normalized = self._normalize_thomson(content)
        else:
            normalized = content
        
        # Update record
        record.content = normalized
        record.layer = Layer.SILVER
        
        return record
    
    def _normalize_sec(self, content: dict) -> dict:
        """Normalize SEC ticker data."""
        return {
            "entity_type": "company",
            "primary_name": content["name"],
            "identifiers": [
                {"scheme": "cik", "value": content["cik"]},
                {"scheme": "ticker", "value": content["ticker"], "exchange": content["exchange"]},
            ],
            "jurisdiction": "US",
            "source": "sec",
        }
    
    def _normalize_gleif(self, content: dict) -> dict:
        """Normalize GLEIF LEI data."""
        return {
            "entity_type": "company",
            "primary_name": content["legal_name"],
            "identifiers": [
                {"scheme": "lei", "value": content["lei"]},
            ],
            "jurisdiction": content.get("legal_jurisdiction"),
            "status": content.get("entity_status"),
            "source": "gleif",
        }
    
    def _normalize_bloomberg(self, content: dict) -> dict:
        """Normalize Bloomberg FIGI data."""
        return {
            "entity_type": "security",  # Bloomberg is security-level
            "primary_name": content["name"],
            "identifiers": [
                {"scheme": "figi", "value": content["figi"]},
            ],
            "metadata": {
                "security_type": content.get("security_type"),
                "market_sector": content.get("market_sector"),
            },
            "source": "bloomberg",
        }
```

### Silver → Gold Merger

```python
# entity_master/transformers/entity_merger.py

from feedspine import Record
from entity_master.matching import EntityMatcher


class EntityMerger:
    """Merge silver records into gold layer canonical entities.
    
    Silver: Individual normalized records from each source
    Gold: Canonical entities with all identifiers merged
    """
    
    def __init__(self):
        self.matcher = EntityMatcher()
    
    async def merge_to_gold(self, silver_records: list[Record]) -> list[dict]:
        """Merge multiple silver records into canonical entities.
        
        Process:
        1. Group by potential matches (name similarity, shared identifiers)
        2. Merge identifiers into canonical entity
        3. Resolve conflicts (prefer most authoritative source)
        """
        # Group records by potential matches
        groups = await self.matcher.find_groups(silver_records)
        
        gold_entities = []
        for group in groups:
            # Merge group into single canonical entity
            canonical = self._merge_group(group)
            gold_entities.append(canonical)
        
        return gold_entities
    
    def _merge_group(self, records: list[Record]) -> dict:
        """Merge a group of related records into one entity."""
        # Start with highest-priority source
        priority = {"sec": 1, "gleif": 2, "openfigi": 3, "bloomberg": 4, "thomson": 5}
        
        sorted_records = sorted(
            records,
            key=lambda r: priority.get(r.content.get("source", ""), 99)
        )
        
        # Use first record as base
        canonical = sorted_records[0].content.copy()
        
        # Merge identifiers from all records
        all_identifiers = []
        seen = set()
        
        for record in sorted_records:
            for ident in record.content.get("identifiers", []):
                key = (ident["scheme"], ident["value"])
                if key not in seen:
                    seen.add(key)
                    all_identifiers.append(ident)
        
        canonical["identifiers"] = all_identifiers
        
        # Merge aliases
        all_names = set()
        for record in sorted_records:
            all_names.add(record.content.get("primary_name", ""))
        
        canonical["aliases"] = list(all_names - {canonical["primary_name"]})
        
        return canonical
```

---

## Integration Example

```python
# Complete Entity Master + FeedSpine setup

from feedspine import FeedSpine, DuckDBStorage
from entity_master import EntityMaster
from entity_master.feeds import (
    SECTickersFeed,
    GLEIFGoldenCopyFeed,
    BloombergFileFeed,
)
from entity_master.transformers import EntityNormalizerEnricher


async def main():
    # Initialize FeedSpine with DuckDB storage
    fs_storage = DuckDBStorage("feeds.duckdb")
    
    async with FeedSpine(storage=fs_storage) as fs:
        # Register feeds
        fs.register_feed(SECTickersFeed())
        fs.register_feed(GLEIFGoldenCopyFeed())
        fs.register_feed(BloombergFileFeed("G:\\BLOOMBERG"))
        
        # Register enricher for silver layer transformation
        fs.register_enricher(EntityNormalizerEnricher())
        
        # Collect from all feeds
        result = await fs.collect()
        print(f"Collected: {result.total_count} records")
        print(f"New: {result.new_count}")
        print(f"Updated: {result.updated_count}")
        
        # Initialize Entity Master connected to FeedSpine
        em = EntityMaster(
            tier="intermediate",
            feedspine=fs,
        )
        
        # Sync FeedSpine data to Entity Master gold layer
        await em.sync_from_feedspine()
        
        # Now Entity Master has merged, canonical entities
        entity = em.resolve("AAPL")
        print(f"Entity: {entity.primary_name}")
        print(f"CIK: {entity.cik}")
        print(f"LEI: {entity.lei}")
        print(f"Aliases: {entity.aliases}")
        
        # Detect changes
        changes = await em.changes.since(days=7)
        print(f"New tickers this week: {len(changes['new_entities'])}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

---

## CLI Commands

```bash
# Collect from all feeds
entity-master collect

# Collect from specific feed
entity-master collect --feed sec-tickers

# Show change report
entity-master changes --since 7d

# Import local files
entity-master import bloomberg G:\BLOOMBERG
entity-master import thomson G:\THOMSON

# Sync to Entity Master
entity-master sync

# Show feed status
entity-master feeds status
```

---

## Configuration

```yaml
# entity_master.yaml

feedspine:
  storage:
    type: duckdb
    path: ~/.entity_master/feeds.duckdb
  
  feeds:
    sec-tickers:
      enabled: true
      schedule: "0 6 * * *"  # Daily at 6 AM
    
    gleif-lei:
      enabled: true
      schedule: "0 0 1 * *"  # Monthly on 1st
    
    bloomberg-local:
      enabled: true
      schedule: null  # Manual
      directory: "G:\\BLOOMBERG"
    
    thomson-local:
      enabled: true
      schedule: null  # Manual
      directory: "G:\\THOMSON"
  
  enrichers:
    - entity_normalizer
  
  # How long to keep historical sightings
  retention:
    bronze: 90d
    silver: 365d
    gold: forever
```
