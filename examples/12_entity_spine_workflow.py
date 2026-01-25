"""Entity Spine Workflow: Complete Entity Management System.

This module demonstrates the full entity workflow:
1. Ingest SEC company_tickers.json (with versions)
2. Track entity changes over time
3. Parse Exhibit 21 for corporate hierarchy
4. Store and query entities with temporal versioning

Run: python entity_spine_workflow.py
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Add source paths
sys.path.insert(0, str(Path(__file__).parent.parent / "py_sec_edgar" / "src"))

from py_sec_edgar.adapters.sec_api import SecSubmissionsAPI, SecFullTextSearch
from py_sec_edgar.services.query_service import QueryService


# =============================================================================
# ENTITY DATA MODELS
# =============================================================================

class EntityType(Enum):
    """Type of entity."""
    PUBLIC_COMPANY = "public_company"
    PRIVATE_COMPANY = "private_company"
    SUBSIDIARY = "subsidiary"


class IdentifierScheme(Enum):
    """Identifier type."""
    CIK = "cik"
    TICKER = "ticker"
    NAME = "name"


class ChangeType(Enum):
    """Type of entity change."""
    ADDED = "added"
    REMOVED = "removed"
    TICKER_CHANGED = "ticker_changed"
    NAME_CHANGED = "name_changed"
    EXCHANGE_CHANGED = "exchange_changed"


@dataclass
class Identifier:
    """An identifier for an entity."""
    scheme: IdentifierScheme
    value: str
    valid_from: date
    valid_to: Optional[date] = None
    source: str = ""
    
    @property
    def is_current(self) -> bool:
        return self.valid_to is None


@dataclass
class EntitySighting:
    """A single observation of an entity from a data source."""
    sighting_id: str
    source: str          # "sec_company_tickers", "sec_exhibit_21", etc.
    source_date: date    # Date of the source data
    seen_at: datetime
    
    # Observed data
    cik: str
    name: str
    ticker: Optional[str] = None
    exchange: Optional[str] = None
    
    # For subsidiaries
    parent_cik: Optional[str] = None
    jurisdiction: Optional[str] = None
    
    # Raw payload
    raw_data: Dict[str, Any] = field(default_factory=dict)
    
    def content_hash(self) -> str:
        """Hash for deduplication."""
        content = f"{self.cik}|{self.name}|{self.ticker}|{self.exchange}"
        return hashlib.md5(content.encode()).hexdigest()[:16]


@dataclass
class EntityVersion:
    """Point-in-time snapshot of an entity."""
    version_id: str
    entity_id: str
    valid_from: date
    valid_to: Optional[date] = None
    
    # State at this version
    name: str = ""
    ticker: Optional[str] = None
    exchange: Optional[str] = None
    entity_type: EntityType = EntityType.PUBLIC_COMPANY
    
    # Identifiers active at this version
    identifiers: List[Identifier] = field(default_factory=list)
    
    # Source tracking
    source_sightings: List[str] = field(default_factory=list)
    
    @property
    def is_current(self) -> bool:
        return self.valid_to is None


@dataclass
class Entity:
    """Canonical entity with version history."""
    entity_id: str
    cik: str
    entity_type: EntityType = EntityType.PUBLIC_COMPANY
    
    # Version history
    versions: List[EntityVersion] = field(default_factory=list)
    
    # All sightings
    sightings: List[EntitySighting] = field(default_factory=list)
    
    # Current state (convenience)
    @property
    def current_version(self) -> Optional[EntityVersion]:
        for v in reversed(self.versions):
            if v.is_current:
                return v
        return self.versions[-1] if self.versions else None
    
    @property
    def name(self) -> str:
        return self.current_version.name if self.current_version else ""
    
    @property
    def ticker(self) -> Optional[str]:
        return self.current_version.ticker if self.current_version else None


@dataclass
class EntityChange:
    """A change detected between entity versions."""
    change_type: ChangeType
    entity_id: str
    cik: str
    name: str
    
    # Change details
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    
    # Temporal
    from_date: date = field(default_factory=date.today)
    to_date: date = field(default_factory=date.today)


# =============================================================================
# ENTITY STORE (In-Memory for Demo)
# =============================================================================

class EntityStore:
    """In-memory entity store with versioning.
    
    This demonstrates the storage pattern before we implement
    the full SQLite/DuckDB backend in EntitySpine.
    """
    
    def __init__(self):
        self.entities: Dict[str, Entity] = {}  # entity_id -> Entity
        self.by_cik: Dict[str, str] = {}       # CIK -> entity_id
        self.by_ticker: Dict[str, str] = {}    # ticker -> entity_id
        self.sightings: List[EntitySighting] = []
        
    def get_or_create_entity(self, cik: str) -> Entity:
        """Get existing entity or create new one."""
        if cik in self.by_cik:
            return self.entities[self.by_cik[cik]]
        
        # Create new entity
        entity_id = f"ENT_{cik}"
        entity = Entity(
            entity_id=entity_id,
            cik=cik,
        )
        self.entities[entity_id] = entity
        self.by_cik[cik] = entity_id
        return entity
    
    def add_sighting(self, sighting: EntitySighting) -> Entity:
        """Add a sighting and update entity."""
        self.sightings.append(sighting)
        
        entity = self.get_or_create_entity(sighting.cik)
        entity.sightings.append(sighting)
        
        # Update ticker index
        if sighting.ticker:
            self.by_ticker[sighting.ticker] = entity.entity_id
        
        return entity
    
    def create_version(
        self,
        entity: Entity,
        sighting: EntitySighting,
        valid_from: date,
    ) -> EntityVersion:
        """Create a new version from a sighting."""
        version_id = f"{entity.entity_id}_v{len(entity.versions) + 1}"
        
        # Close previous version
        if entity.versions:
            entity.versions[-1].valid_to = valid_from
        
        version = EntityVersion(
            version_id=version_id,
            entity_id=entity.entity_id,
            valid_from=valid_from,
            name=sighting.name,
            ticker=sighting.ticker,
            exchange=sighting.exchange,
            source_sightings=[sighting.sighting_id],
        )
        
        entity.versions.append(version)
        return version
    
    def get_by_cik(self, cik: str) -> Optional[Entity]:
        """Lookup by CIK."""
        entity_id = self.by_cik.get(cik)
        return self.entities.get(entity_id) if entity_id else None
    
    def get_by_ticker(self, ticker: str) -> Optional[Entity]:
        """Lookup by ticker."""
        entity_id = self.by_ticker.get(ticker.upper())
        return self.entities.get(entity_id) if entity_id else None
    
    def search(self, query: str, limit: int = 10) -> List[Entity]:
        """Search entities by name or ticker."""
        query_upper = query.upper()
        results = []
        
        for entity in self.entities.values():
            if entity.current_version:
                name = entity.current_version.name.upper()
                ticker = (entity.current_version.ticker or "").upper()
                
                if query_upper in name or query_upper == ticker:
                    results.append(entity)
                    if len(results) >= limit:
                        break
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """Get store statistics."""
        return {
            "total_entities": len(self.entities),
            "total_sightings": len(self.sightings),
            "by_type": self._count_by_type(),
            "with_versions": sum(1 for e in self.entities.values() if len(e.versions) > 1),
        }
    
    def _count_by_type(self) -> Dict[str, int]:
        counts = {}
        for entity in self.entities.values():
            t = entity.entity_type.value
            counts[t] = counts.get(t, 0) + 1
        return counts


# =============================================================================
# SEC DATA INGESTION
# =============================================================================

class SECDataIngester:
    """Ingest SEC company data into EntityStore."""
    
    def __init__(self, store: EntityStore):
        self.store = store
    
    def ingest_company_tickers(
        self,
        data: Dict[str, Any],
        source_date: date,
        source_name: str = "sec_company_tickers",
    ) -> Tuple[int, int, int]:
        """Ingest company_tickers.json data.
        
        Returns: (total, new, updated) counts
        """
        total = 0
        new = 0
        updated = 0
        
        for key, company in data.items():
            total += 1
            cik = str(company.get("cik_str", "")).zfill(10)
            ticker = company.get("ticker", "")
            name = company.get("title", "")
            
            # Create sighting
            sighting = EntitySighting(
                sighting_id=f"{source_name}_{source_date}_{cik}",
                source=source_name,
                source_date=source_date,
                seen_at=datetime.now(),
                cik=cik,
                name=name,
                ticker=ticker,
                raw_data=company,
            )
            
            # Check if entity exists
            existing = self.store.get_by_cik(cik)
            is_new = existing is None
            
            # Add sighting
            entity = self.store.add_sighting(sighting)
            
            # Check if version needed
            needs_version = False
            if is_new:
                needs_version = True
                new += 1
            elif entity.current_version:
                # Check for changes
                cv = entity.current_version
                if cv.name != name or cv.ticker != ticker:
                    needs_version = True
                    updated += 1
            
            if needs_version:
                self.store.create_version(entity, sighting, source_date)
        
        return total, new, updated
    
    def ingest_company_tickers_exchange(
        self,
        data: Dict[str, Any],
        source_date: date,
    ) -> Tuple[int, int, int]:
        """Ingest company_tickers_exchange.json (includes exchange info)."""
        total = 0
        new = 0
        updated = 0
        
        # Format: {"data": [[cik, name, ticker, exchange], ...]}
        rows = data.get("data", [])
        
        for row in rows:
            if len(row) < 4:
                continue
            
            total += 1
            cik = str(row[0]).zfill(10)
            name = row[1]
            ticker = row[2]
            exchange = row[3]
            
            sighting = EntitySighting(
                sighting_id=f"sec_exchange_{source_date}_{cik}_{ticker}",
                source="sec_company_tickers_exchange",
                source_date=source_date,
                seen_at=datetime.now(),
                cik=cik,
                name=name,
                ticker=ticker,
                exchange=exchange,
                raw_data={"cik": cik, "name": name, "ticker": ticker, "exchange": exchange},
            )
            
            existing = self.store.get_by_cik(cik)
            is_new = existing is None
            
            entity = self.store.add_sighting(sighting)
            
            needs_version = False
            if is_new:
                needs_version = True
                new += 1
            elif entity.current_version:
                cv = entity.current_version
                if cv.name != name or cv.ticker != ticker or cv.exchange != exchange:
                    needs_version = True
                    updated += 1
            
            if needs_version:
                self.store.create_version(entity, sighting, source_date)
        
        return total, new, updated


# =============================================================================
# VERSION COMPARISON
# =============================================================================

class VersionComparator:
    """Compare entity versions across time periods."""
    
    def __init__(self, store: EntityStore):
        self.store = store
    
    def compare_ingestions(
        self,
        old_data: Dict[str, Any],
        new_data: Dict[str, Any],
        old_date: date,
        new_date: date,
    ) -> Dict[str, List[EntityChange]]:
        """Compare two company_tickers.json versions."""
        changes = {
            "added": [],
            "removed": [],
            "ticker_changed": [],
            "name_changed": [],
        }
        
        # Build CIK maps
        old_by_cik = {}
        for company in old_data.values():
            cik = str(company.get("cik_str", "")).zfill(10)
            old_by_cik[cik] = company
        
        new_by_cik = {}
        for company in new_data.values():
            cik = str(company.get("cik_str", "")).zfill(10)
            new_by_cik[cik] = company
        
        old_ciks = set(old_by_cik.keys())
        new_ciks = set(new_by_cik.keys())
        
        # Added
        for cik in new_ciks - old_ciks:
            company = new_by_cik[cik]
            changes["added"].append(EntityChange(
                change_type=ChangeType.ADDED,
                entity_id=f"ENT_{cik}",
                cik=cik,
                name=company.get("title", ""),
                new_value=company.get("ticker", ""),
                from_date=old_date,
                to_date=new_date,
            ))
        
        # Removed
        for cik in old_ciks - new_ciks:
            company = old_by_cik[cik]
            changes["removed"].append(EntityChange(
                change_type=ChangeType.REMOVED,
                entity_id=f"ENT_{cik}",
                cik=cik,
                name=company.get("title", ""),
                old_value=company.get("ticker", ""),
                from_date=old_date,
                to_date=new_date,
            ))
        
        # Changed
        for cik in old_ciks & new_ciks:
            old_co = old_by_cik[cik]
            new_co = new_by_cik[cik]
            
            old_ticker = old_co.get("ticker", "")
            new_ticker = new_co.get("ticker", "")
            old_name = old_co.get("title", "")
            new_name = new_co.get("title", "")
            
            if old_ticker != new_ticker:
                changes["ticker_changed"].append(EntityChange(
                    change_type=ChangeType.TICKER_CHANGED,
                    entity_id=f"ENT_{cik}",
                    cik=cik,
                    name=new_name,
                    old_value=old_ticker,
                    new_value=new_ticker,
                    from_date=old_date,
                    to_date=new_date,
                ))
            
            if old_name != new_name:
                changes["name_changed"].append(EntityChange(
                    change_type=ChangeType.NAME_CHANGED,
                    entity_id=f"ENT_{cik}",
                    cik=cik,
                    name=new_name,
                    old_value=old_name,
                    new_value=new_name,
                    from_date=old_date,
                    to_date=new_date,
                ))
        
        return changes


# =============================================================================
# EXHIBIT 21 PARSER
# =============================================================================

@dataclass
class SubsidiaryRecord:
    """A subsidiary from Exhibit 21."""
    name: str
    jurisdiction: Optional[str] = None
    name_normalized: str = ""
    
    def __post_init__(self):
        if not self.name_normalized:
            self.name_normalized = self._normalize(self.name)
    
    @staticmethod
    def _normalize(name: str) -> str:
        """Normalize name for matching."""
        name = name.upper()
        name = re.sub(r'[,\.\(\)]', '', name)
        name = re.sub(r'\s+', ' ', name)
        # Remove common suffixes
        for suffix in [' LLC', ' INC', ' LTD', ' LIMITED', ' CORP', ' CORPORATION', 
                       ' LP', ' LLP', ' SA', ' SRL', ' GMBH', ' BV', ' NV']:
            if name.endswith(suffix):
                name = name[:-len(suffix)]
        return name.strip()


class Exhibit21Parser:
    """Parse Exhibit 21 HTML to extract subsidiaries."""
    
    # Jurisdiction patterns
    JURISDICTION_PATTERNS = [
        (r'\(([A-Z]{2})\)$', 'state'),  # (CA), (DE)
        (r'\(([A-Za-z\s,]+)\)$', 'full'),  # (Delaware), (United Kingdom)
        (r',\s*([A-Z]{2})$', 'state'),  # , CA
        (r',\s*([A-Za-z\s]+)$', 'full'),  # , Delaware
    ]
    
    def parse(self, html_content: str) -> List[SubsidiaryRecord]:
        """Parse HTML to extract subsidiaries."""
        subsidiaries = []
        
        # Try table parsing first
        table_subs = self._parse_tables(html_content)
        if table_subs:
            return table_subs
        
        # Fallback to line-by-line
        return self._parse_lines(html_content)
    
    def _parse_tables(self, html: str) -> List[SubsidiaryRecord]:
        """Parse subsidiaries from HTML tables."""
        from html.parser import HTMLParser
        
        class TableParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.in_table = False
                self.in_cell = False
                self.current_row = []
                self.rows = []
                self.current_text = ""
            
            def handle_starttag(self, tag, attrs):
                if tag == "table":
                    self.in_table = True
                elif tag in ("td", "th") and self.in_table:
                    self.in_cell = True
                    self.current_text = ""
            
            def handle_endtag(self, tag):
                if tag == "table":
                    self.in_table = False
                elif tag in ("td", "th") and self.in_cell:
                    self.current_row.append(self.current_text.strip())
                    self.in_cell = False
                elif tag == "tr" and self.current_row:
                    self.rows.append(self.current_row)
                    self.current_row = []
            
            def handle_data(self, data):
                if self.in_cell:
                    self.current_text += data
        
        parser = TableParser()
        try:
            parser.feed(html)
        except:
            return []
        
        subsidiaries = []
        for row in parser.rows:
            if not row:
                continue
            
            # First cell is usually name
            name = row[0] if row else ""
            jurisdiction = row[1] if len(row) > 1 else None
            
            # Skip headers
            if not name or name.upper() in ['NAME', 'SUBSIDIARY', 'COMPANY', 'ENTITY']:
                continue
            
            # Skip if too short
            if len(name) < 3:
                continue
            
            # Clean up
            name = re.sub(r'<[^>]+>', '', name)
            name = re.sub(r'\s+', ' ', name).strip()
            
            if jurisdiction:
                jurisdiction = re.sub(r'<[^>]+>', '', jurisdiction)
                jurisdiction = re.sub(r'\s+', ' ', jurisdiction).strip()
            
            if name:
                subsidiaries.append(SubsidiaryRecord(
                    name=name,
                    jurisdiction=jurisdiction,
                ))
        
        return subsidiaries
    
    def _parse_lines(self, html: str) -> List[SubsidiaryRecord]:
        """Parse subsidiaries from line-by-line text."""
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '\n', html)
        text = re.sub(r'&nbsp;', ' ', text)
        text = re.sub(r'&amp;', '&', text)
        
        subsidiaries = []
        for line in text.split('\n'):
            line = line.strip()
            if not line or len(line) < 5:
                continue
            
            # Skip obvious headers
            if any(h in line.upper() for h in ['EXHIBIT 21', 'SUBSIDIARIES', 'PAGE', 'LIST OF']):
                continue
            
            # Try to extract jurisdiction
            name = line
            jurisdiction = None
            
            for pattern, _ in self.JURISDICTION_PATTERNS:
                match = re.search(pattern, line)
                if match:
                    jurisdiction = match.group(1)
                    name = line[:match.start()].strip()
                    break
            
            if name and len(name) > 3:
                subsidiaries.append(SubsidiaryRecord(
                    name=name,
                    jurisdiction=jurisdiction,
                ))
        
        return subsidiaries
    
    def compare_years(
        self,
        old_subs: List[SubsidiaryRecord],
        new_subs: List[SubsidiaryRecord],
    ) -> Dict[str, List[SubsidiaryRecord]]:
        """Compare subsidiaries between years."""
        old_names = {s.name_normalized: s for s in old_subs}
        new_names = {s.name_normalized: s for s in new_subs}
        
        old_set = set(old_names.keys())
        new_set = set(new_names.keys())
        
        return {
            "added": [new_names[n] for n in new_set - old_set],
            "removed": [old_names[n] for n in old_set - new_set],
            "unchanged": [new_names[n] for n in old_set & new_set],
        }


# =============================================================================
# WORKFLOW ORCHESTRATOR
# =============================================================================

class EntityWorkflow:
    """Orchestrates the full entity management workflow."""
    
    def __init__(self):
        self.store = EntityStore()
        self.ingester = SECDataIngester(self.store)
        self.comparator = VersionComparator(self.store)
        self.exhibit_parser = Exhibit21Parser()
    
    async def run_full_workflow(self):
        """Run the complete entity workflow demonstration."""
        print("\n" + "=" * 80)
        print("ENTITY SPINE WORKFLOW - Full Entity Management Demonstration")
        print("=" * 80)
        
        # Step 1: Load historical company_tickers.json versions
        await self.step1_ingest_historical_versions()
        
        # Step 2: Compare versions and show changes
        await self.step2_analyze_version_changes()
        
        # Step 3: Load company_tickers_exchange for additional data
        await self.step3_ingest_exchange_data()
        
        # Step 4: Demonstrate entity lookup and versioning
        await self.step4_demonstrate_entity_queries()
        
        # Step 5: Fetch Exhibit 21 for sample companies
        await self.step5_parse_exhibit_21()
        
        # Step 6: Show entity store statistics
        await self.step6_show_statistics()
    
    async def step1_ingest_historical_versions(self):
        """Step 1: Ingest historical company_tickers.json versions."""
        print("\n" + "-" * 80)
        print("STEP 1: Ingest Historical SEC Company Data")
        print("-" * 80)
        
        test_data_dir = Path(__file__).parent / "test_data" / "company_tickers_versions"
        
        # Load versions in chronological order
        versions = [
            ("company_tickers_2019-10-12.json", date(2019, 10, 12)),
            ("company_tickers_2025-07-26.json", date(2025, 7, 26)),
            ("company_tickers_2025-09-13.json", date(2025, 9, 13)),
        ]
        
        for filename, version_date in versions:
            filepath = test_data_dir / filename
            if filepath.exists():
                print(f"\n📥 Loading {filename}...")
                with open(filepath, "r") as f:
                    data = json.load(f)
                
                total, new, updated = self.ingester.ingest_company_tickers(
                    data, version_date, f"sec_company_tickers_{version_date}"
                )
                
                print(f"   Total: {total:,} | New: {new:,} | Updated: {updated:,}")
            else:
                print(f"   ⚠️ File not found: {filename}")
    
    async def step2_analyze_version_changes(self):
        """Step 2: Analyze changes between versions."""
        print("\n" + "-" * 80)
        print("STEP 2: Analyze Entity Changes Over Time")
        print("-" * 80)
        
        test_data_dir = Path(__file__).parent / "test_data" / "company_tickers_versions"
        
        # Load 2019 and 2025 versions for comparison
        old_file = test_data_dir / "company_tickers_2019-10-12.json"
        new_file = test_data_dir / "company_tickers_2025-09-13.json"
        
        if old_file.exists() and new_file.exists():
            with open(old_file) as f:
                old_data = json.load(f)
            with open(new_file) as f:
                new_data = json.load(f)
            
            changes = self.comparator.compare_ingestions(
                old_data, new_data,
                date(2019, 10, 12), date(2025, 9, 13)
            )
            
            print(f"\n📊 Changes from 2019 to 2025:")
            print(f"   • Companies added:    {len(changes['added']):,}")
            print(f"   • Companies removed:  {len(changes['removed']):,}")
            print(f"   • Ticker changes:     {len(changes['ticker_changed']):,}")
            print(f"   • Name changes:       {len(changes['name_changed']):,}")
            
            # Show sample changes
            print("\n📝 Sample Ticker Changes:")
            for change in changes['ticker_changed'][:5]:
                print(f"   [{change.cik}] {change.old_value} → {change.new_value} ({change.name[:40]})")
            
            print("\n📝 Sample Name Changes:")
            for change in changes['name_changed'][:5]:
                print(f"   [{change.cik}] {change.old_value[:30]} → {change.new_value[:30]}")
    
    async def step3_ingest_exchange_data(self):
        """Step 3: Ingest exchange data for richer entity info."""
        print("\n" + "-" * 80)
        print("STEP 3: Enrich with Exchange Data")
        print("-" * 80)
        
        test_data_dir = Path(__file__).parent / "test_data" / "company_tickers_versions"
        exchange_file = test_data_dir / "company_tickers_exchange_2025-09-07.json"
        
        if exchange_file.exists():
            print(f"\n📥 Loading exchange data...")
            with open(exchange_file) as f:
                data = json.load(f)
            
            total, new, updated = self.ingester.ingest_company_tickers_exchange(
                data, date(2025, 9, 7)
            )
            
            print(f"   Total: {total:,} | New: {new:,} | Updated: {updated:,}")
            
            # Show sample entities with exchange
            print("\n📝 Sample Entities with Exchange:")
            count = 0
            for entity in self.store.entities.values():
                if entity.current_version and entity.current_version.exchange:
                    cv = entity.current_version
                    print(f"   [{cv.ticker}] {cv.name[:40]} - {cv.exchange}")
                    count += 1
                    if count >= 5:
                        break
    
    async def step4_demonstrate_entity_queries(self):
        """Step 4: Demonstrate entity lookup and version history."""
        print("\n" + "-" * 80)
        print("STEP 4: Entity Queries and Version History")
        print("-" * 80)
        
        # Query some well-known companies
        test_queries = ["AAPL", "MSFT", "GOOGL", "META", "NVDA"]
        
        print("\n🔍 Looking up well-known companies:")
        for ticker in test_queries:
            entity = self.store.get_by_ticker(ticker)
            if entity:
                cv = entity.current_version
                print(f"\n   {ticker}: {entity.name}")
                print(f"      CIK: {entity.cik}")
                print(f"      Entity ID: {entity.entity_id}")
                print(f"      Versions: {len(entity.versions)}")
                print(f"      Sightings: {len(entity.sightings)}")
                
                if len(entity.versions) > 1:
                    print(f"      Version History:")
                    for v in entity.versions:
                        status = "current" if v.is_current else f"until {v.valid_to}"
                        print(f"         • {v.valid_from}: {v.name[:30]} ({v.ticker}) [{status}]")
            else:
                print(f"\n   {ticker}: Not found")
        
        # Show entities with version changes
        print("\n📊 Entities with Multiple Versions:")
        multi_version = [e for e in self.store.entities.values() if len(e.versions) > 1]
        print(f"   Found {len(multi_version):,} entities with changes over time")
        
        for entity in multi_version[:3]:
            print(f"\n   {entity.cik}: {entity.name}")
            for v in entity.versions:
                status = "→ current" if v.is_current else ""
                print(f"      [{v.valid_from}] {v.ticker}: {v.name[:40]} {status}")
    
    async def step5_parse_exhibit_21(self):
        """Step 5: Parse Exhibit 21 for corporate hierarchy."""
        print("\n" + "-" * 80)
        print("STEP 5: Corporate Hierarchy from Exhibit 21")
        print("-" * 80)
        
        # Use QueryService to fetch Exhibit 21
        async with QueryService() as qs:
            # Get Apple's Exhibit 21 for multiple years
            companies = [
                ("320193", "Apple"),
                ("789019", "Microsoft"),
                ("1652044", "Alphabet"),
            ]
            
            for cik, name in companies:
                print(f"\n🏢 {name} (CIK: {cik})")
                
                try:
                    subs = await qs.submissions.get(cik)
                    ten_ks = subs.filter_by_form(["10-K"])[:3]  # Last 3 years
                    
                    yearly_subs = {}
                    for filing in ten_ks:
                        exhibit_file = await qs.submissions._api.find_exhibit(
                            cik, filing["accession_number"], "EX-21"
                        )
                        
                        if exhibit_file:
                            content = await qs.submissions._api.get_filing_document(
                                cik, filing["accession_number"], exhibit_file
                            )
                            
                            subsidiaries = self.exhibit_parser.parse(content)
                            year = filing["filing_date"][:4]
                            yearly_subs[year] = subsidiaries
                            
                            print(f"   📅 {year}: Found {len(subsidiaries)} subsidiaries")
                    
                    # Compare years if we have multiple
                    if len(yearly_subs) >= 2:
                        years = sorted(yearly_subs.keys())
                        for i in range(len(years) - 1):
                            old_year, new_year = years[i], years[i + 1]
                            changes = self.exhibit_parser.compare_years(
                                yearly_subs[old_year],
                                yearly_subs[new_year]
                            )
                            
                            if changes["added"] or changes["removed"]:
                                print(f"\n   📊 Changes {old_year} → {new_year}:")
                                print(f"      Added: {len(changes['added'])}")
                                print(f"      Removed: {len(changes['removed'])}")
                                
                                if changes["added"][:2]:
                                    print(f"      Sample added: {[s.name[:30] for s in changes['added'][:2]]}")
                                if changes["removed"][:2]:
                                    print(f"      Sample removed: {[s.name[:30] for s in changes['removed'][:2]]}")
                
                except Exception as e:
                    print(f"   ⚠️ Error: {e}")
    
    async def step6_show_statistics(self):
        """Step 6: Show final entity store statistics."""
        print("\n" + "-" * 80)
        print("STEP 6: Entity Store Statistics")
        print("-" * 80)
        
        stats = self.store.get_stats()
        
        print(f"\n📊 Entity Store Summary:")
        print(f"   • Total entities: {stats['total_entities']:,}")
        print(f"   • Total sightings: {stats['total_sightings']:,}")
        print(f"   • Entities with changes: {stats['with_versions']:,}")
        print(f"   • By type: {stats['by_type']}")
        
        # Show sighting sources
        sources = {}
        for sighting in self.store.sightings:
            src = sighting.source.split("_")[0:3]
            src_key = "_".join(src) if src else sighting.source
            sources[src_key] = sources.get(src_key, 0) + 1
        
        print(f"\n📥 Sightings by Source:")
        for source, count in sorted(sources.items(), key=lambda x: -x[1])[:5]:
            print(f"   • {source}: {count:,}")


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

async def main():
    """Run the full workflow."""
    workflow = EntityWorkflow()
    await workflow.run_full_workflow()
    
    print("\n" + "=" * 80)
    print("✅ Entity Spine Workflow Complete!")
    print("=" * 80)
    print("\nNext steps:")
    print("  1. Implement persistent storage (SQLite/DuckDB)")
    print("  2. Add FeedSpine integration for unified sighting management")
    print("  3. Build knowledge graph for subsidiary relationships")
    print("  4. Add change detection triggers")


if __name__ == "__main__":
    asyncio.run(main())
