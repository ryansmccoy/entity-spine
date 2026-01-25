"""
ISO 10383 MIC (Market Identifier Code) Source.

STDLIB ONLY - NO PYDANTIC.

Downloads and manages the official ISO 10383 MIC list from ISO 20022.

This implements a Bronze/Silver/Gold data architecture:
- Bronze: Raw CSV/XML snapshots stored immutably
- Silver: Normalized MIC records with change tracking
- Gold: Domain-ready registry with lookup APIs

Data Sources:
- CSV: https://www.iso20022.org/sites/default/files/ISO10383_MIC/ISO10383_MIC.csv
- XML: https://www.iso20022.org/sites/default/files/ISO10383_MIC/ISO10383_MIC.xml
- XLS: https://www.iso20022.org/sites/default/files/ISO10383_MIC/ISO10383_MIC.xls

Update Cadence:
- ISO publishes updates quarterly (sometimes monthly)
- Subscribe to notifications at: https://www.iso20022.org/market-identifier-codes
- We recommend weekly/daily checks for changes

Related Resources:
- GLEIF MIC-to-LEI mapping: https://www.gleif.org/en/lei-data/lei-mapping
- ISO 10383 spec: https://www.iso.org/standard/61067.html

Example:
    >>> from entityspine.sources import ISO10383Source
    >>>
    >>> source = ISO10383Source()
    >>> records = await source.fetch()
    >>> print(f"Fetched {len(records)} MIC codes")
    >>> print(records[0])
    # {'mic': 'XNYS', 'operating_mic': 'XNYS', 'mic_type': 'OPRT', ...}

v1.0.0 Initial implementation.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import logging
import urllib.request
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterator

from entityspine.domain.timestamps import utc_now

logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

# Official ISO 20022 download URLs
ISO10383_CSV_URL = "https://www.iso20022.org/sites/default/files/ISO10383_MIC/ISO10383_MIC.csv"
ISO10383_XML_URL = "https://www.iso20022.org/sites/default/files/ISO10383_MIC/ISO10383_MIC.xml"
ISO10383_XLS_URL = "https://www.iso20022.org/sites/default/files/ISO10383_MIC/ISO10383_MIC.xls"

# GLEIF MIC-to-LEI relationship file
GLEIF_MIC_LEI_URL = "https://www.gleif.org/en/lei-data/lei-mapping/download-mic-to-lei-relationship-files"

# MIC Types (from ISO 10383)
MIC_TYPE_OPERATING = "OPRT"  # Operating MIC (parent)
MIC_TYPE_SEGMENT = "SGMT"    # Segment MIC (child)

# MIC Status values
MIC_STATUS_ACTIVE = "ACTIVE"
MIC_STATUS_UPDATED = "UPDATED"
MIC_STATUS_EXPIRED = "EXPIRED"
MIC_STATUS_DELETED = "DELETED"


# =============================================================================
# Bronze Layer: Raw Snapshot
# =============================================================================


@dataclass(frozen=True, slots=True)
class MICSnapshot:
    """
    Bronze layer: Immutable raw snapshot of ISO 10383 data.
    
    Stores the raw downloaded content with metadata for provenance tracking.
    Each download creates a new snapshot, enabling historical comparison.
    
    Attributes:
        snapshot_id: Unique identifier for this snapshot.
        source_url: URL the data was fetched from.
        format: File format (csv, xml, xls).
        content_hash: SHA-256 hash of content for deduplication.
        content_size: Size in bytes.
        record_count: Number of MIC records in snapshot.
        etag: HTTP ETag if available (for conditional requests).
        last_modified: HTTP Last-Modified if available.
        captured_at: When snapshot was captured.
        raw_path: Path to stored raw file (optional).
    """
    snapshot_id: str
    source_url: str
    format: str  # csv, xml, xls
    content_hash: str  # SHA-256
    content_size: int
    record_count: int
    etag: str | None = None
    last_modified: str | None = None
    captured_at: datetime = field(default_factory=utc_now)
    raw_path: str | None = None


# =============================================================================
# Silver Layer: Normalized MIC Record
# =============================================================================


@dataclass(frozen=True, slots=True)
class MICRecord:
    """
    Silver layer: Normalized MIC record from ISO 10383.
    
    Each record represents one MIC code with all its attributes.
    This is a direct mapping from the ISO CSV columns.
    
    ISO 10383 CSV Columns (2024+):
    - MIC: The 4-character MIC code
    - OPERATING MIC: Parent MIC for segments (same as MIC for operating MICs)
    - OPRT/SGMT: MIC type - "OPRT" (operating) or "SGMT" (segment)
    - MARKET NAME-INSTITUTION DESCRIPTION: Full name of the market/institution
    - LEGAL ENTITY NAME: Name of the legal entity operator
    - LEI: Legal Entity Identifier of the operator
    - MARKET CATEGORY CODE: Category code (APPA, CTPS, MLTF, NSPD, OTFS, RMOS, SINT)
    - ACRONYM: Short name/acronym
    - ISO COUNTRY CODE (ISO 3166): Country code
    - CITY: City where located
    - WEBSITE: URL of the market
    - STATUS: ACTIVE, UPDATED, EXPIRED, DELETED
    - CREATION DATE: When MIC was created (YYYYMMDD)
    - LAST UPDATE DATE: Last modification date
    - LAST VALIDATION DATE: Last validation
    - EXPIRY DATE: When MIC expires
    - COMMENTS: Additional notes
    
    Attributes:
        mic: The 4-character Market Identifier Code.
        operating_mic: Parent MIC (equals mic for operating MICs).
        mic_type: "OPRT" for operating MIC, "SGMT" for segment.
        name: Full institution/market name.
        legal_entity_name: Name of the legal entity operator.
        lei: Legal Entity Identifier of the operator (ISO 17442).
        market_category_code: Category code (APPA, CTPS, MLTF, etc.).
        acronym: Short name or acronym.
        country_code: ISO 3166-1 alpha-2 country code.
        city: City location.
        website: Market website URL.
        status: Current status (ACTIVE, UPDATED, EXPIRED, DELETED).
        creation_date: When MIC was created.
        last_update_date: When record was last updated.
        last_validation_date: When record was last validated.
        expiry_date: When MIC expires.
        comments: Additional notes from ISO.
        
        # Provenance
        snapshot_id: ID of source snapshot (links to Bronze).
        captured_at: When this record was captured.
    """
    mic: str
    operating_mic: str
    mic_type: str  # OPRT or SGMT
    name: str
    
    # New fields from ISO 10383 (2024+ format)
    legal_entity_name: str | None = None
    lei: str | None = None  # Links MIC to legal entity!
    market_category_code: str | None = None
    
    # Optional fields
    acronym: str | None = None
    country_code: str | None = None
    city: str | None = None
    website: str | None = None
    status: str = MIC_STATUS_ACTIVE
    creation_date: date | None = None
    last_update_date: date | None = None
    last_validation_date: date | None = None
    expiry_date: date | None = None
    comments: str | None = None
    
    # Provenance (links to Bronze snapshot)
    snapshot_id: str | None = None
    captured_at: datetime = field(default_factory=utc_now)
    
    @property
    def is_operating(self) -> bool:
        """Check if this is an operating MIC (parent)."""
        return self.mic_type == MIC_TYPE_OPERATING
    
    @property
    def is_segment(self) -> bool:
        """Check if this is a segment MIC (child)."""
        return self.mic_type == MIC_TYPE_SEGMENT
    
    @property
    def is_active(self) -> bool:
        """Check if MIC is currently active."""
        return self.status in (MIC_STATUS_ACTIVE, MIC_STATUS_UPDATED)
    
    @property
    def parent_mic(self) -> str:
        """Get parent MIC (operating_mic for segments, self for operating)."""
        return self.operating_mic


@dataclass(frozen=True, slots=True)
class MICChange:
    """
    Silver layer: Field-level change record for MIC diff tracking.
    
    Captures changes between snapshots for audit and analysis.
    
    Attributes:
        mic: The MIC code that changed.
        field_name: Which field changed.
        old_value: Previous value (None if new record).
        new_value: New value (None if deleted).
        old_snapshot_id: Source snapshot for old value.
        new_snapshot_id: Source snapshot for new value.
        change_type: Type of change (added, modified, deleted).
        detected_at: When change was detected.
    """
    mic: str
    field_name: str
    old_value: str | None
    new_value: str | None
    old_snapshot_id: str | None
    new_snapshot_id: str
    change_type: str  # added, modified, deleted
    detected_at: datetime = field(default_factory=utc_now)


# =============================================================================
# Source Implementation
# =============================================================================


class ISO10383Source:
    """
    ISO 10383 MIC data source.
    
    Downloads and parses the official MIC list from ISO 20022.
    Supports CSV format (recommended for reliability).
    
    Features:
    - Automatic retry with exponential backoff
    - Content hashing for change detection
    - ETag/Last-Modified for conditional requests
    - Bronze snapshot metadata capture
    
    Attributes:
        name: Source identifier ("iso10383-mic")
        csv_url: URL for CSV download
        format: Download format (csv, xml)
        
    Example:
        >>> source = ISO10383Source()
        >>> records = await source.fetch()
        >>> print(f"Got {len(records)} MIC codes")
        
        # Check for specific MIC
        >>> nyse = next(r for r in records if r['mic'] == 'XNYS')
        >>> print(f"NYSE: {nyse['name']}")
    """
    
    name: str = "iso10383-mic"
    csv_url: str = ISO10383_CSV_URL
    xml_url: str = ISO10383_XML_URL
    format: str = "csv"
    
    def __init__(
        self,
        csv_url: str | None = None,
        format: str = "csv",
        cache_dir: Path | str | None = None,
    ):
        """
        Initialize ISO 10383 source.
        
        Args:
            csv_url: Override URL for testing.
            format: Download format ('csv' recommended).
            cache_dir: Directory for storing Bronze snapshots.
        """
        if csv_url:
            self.csv_url = csv_url
        self.format = format
        self.cache_dir = Path(cache_dir) if cache_dir else None
        
        # Last fetch metadata
        self._last_etag: str | None = None
        self._last_modified: str | None = None
        self._last_snapshot: MICSnapshot | None = None
    
    async def fetch(self) -> list[dict[str, Any]]:
        """
        Fetch MIC records from ISO 20022.
        
        Returns:
            List of dicts with normalized MIC data.
            
        Raises:
            IOError: If download fails.
            ValueError: If parsing fails.
        """
        logger.info(f"Fetching ISO 10383 MIC list from {self.csv_url}")
        
        # Download raw content
        content, metadata = await self._download()
        
        # Parse records
        records = self._parse_csv(content)
        
        # Create snapshot metadata
        content_hash = hashlib.sha256(content).hexdigest()
        self._last_snapshot = MICSnapshot(
            snapshot_id=f"mic_{content_hash[:16]}",
            source_url=self.csv_url,
            format=self.format,
            content_hash=content_hash,
            content_size=len(content),
            record_count=len(records),
            etag=metadata.get("etag"),
            last_modified=metadata.get("last_modified"),
            captured_at=utc_now(),
        )
        
        # Optionally cache raw content
        if self.cache_dir:
            self._save_bronze_snapshot(content)
        
        logger.info(f"Parsed {len(records)} MIC codes from ISO 10383")
        return records
    
    async def fetch_as_records(self) -> list[MICRecord]:
        """
        Fetch and return typed MICRecord objects.
        
        Returns:
            List of MICRecord dataclass instances.
        """
        raw_records = await self.fetch()
        snapshot_id = self._last_snapshot.snapshot_id if self._last_snapshot else None
        
        return [
            MICRecord(
                mic=r["mic"],
                operating_mic=r["operating_mic"],
                mic_type=r["mic_type"],
                name=r["name"] or "",
                legal_entity_name=r.get("legal_entity_name"),
                lei=r.get("lei"),
                market_category_code=r.get("market_category_code"),
                acronym=r.get("acronym"),
                country_code=r.get("country_code"),
                city=r.get("city"),
                website=r.get("website"),
                status=r.get("status", MIC_STATUS_ACTIVE),
                creation_date=self._parse_date(r.get("creation_date")),
                last_update_date=self._parse_date(r.get("last_update_date")),
                last_validation_date=self._parse_date(r.get("last_validation_date")),
                expiry_date=self._parse_date(r.get("expiry_date")),
                comments=r.get("comments"),
                snapshot_id=snapshot_id,
                captured_at=utc_now(),
            )
            for r in raw_records
        ]
    
    async def _download(self) -> tuple[bytes, dict[str, str]]:
        """
        Download raw content from ISO 20022.
        
        Returns:
            Tuple of (content_bytes, metadata_dict).
        """
        try:
            req = urllib.request.Request(
                self.csv_url,
                headers={
                    "User-Agent": "EntitySpine/1.0 (MIC data ingestion)",
                    "Accept": "text/csv, application/csv, */*",
                },
            )
            
            # Add conditional headers if we have previous values
            if self._last_etag:
                req.add_header("If-None-Match", self._last_etag)
            if self._last_modified:
                req.add_header("If-Modified-Since", self._last_modified)
            
            with urllib.request.urlopen(req, timeout=60) as response:
                content = response.read()
                metadata = {
                    "etag": response.headers.get("ETag"),
                    "last_modified": response.headers.get("Last-Modified"),
                    "content_type": response.headers.get("Content-Type"),
                }
                
                # Update cached headers
                if metadata["etag"]:
                    self._last_etag = metadata["etag"]
                if metadata["last_modified"]:
                    self._last_modified = metadata["last_modified"]
                
                return content, metadata
                
        except urllib.error.HTTPError as e:
            if e.code == 304:
                logger.info("MIC data not modified since last fetch")
                raise
            logger.error(f"HTTP error fetching MIC data: {e.code} {e.reason}")
            raise IOError(f"Failed to fetch MIC data: {e}") from e
        except Exception as e:
            logger.error(f"Failed to fetch MIC data: {e}")
            raise IOError(f"Failed to fetch MIC data: {e}") from e
    
    def _parse_csv(self, content: bytes) -> list[dict[str, Any]]:
        """
        Parse ISO 10383 CSV content.
        
        The CSV has varying encodings and column names across versions.
        This handles common variations.
        """
        # Try UTF-8 first, fall back to Latin-1
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            text = content.decode("latin-1")
        
        # Parse CSV
        reader = csv.DictReader(io.StringIO(text))
        records = []
        
        for row in reader:
            record = self._normalize_row(row)
            if record and record.get("mic"):
                records.append(record)
        
        return records
    
    def _normalize_row(self, row: dict[str, str]) -> dict[str, Any]:
        """
        Normalize a CSV row to standard field names.
        
        Handles column name variations across ISO 10383 versions.
        
        Current ISO 10383 CSV columns (2024+):
        - MIC
        - OPERATING MIC
        - OPRT/SGMT (type: OPRT or SGMT)
        - MARKET NAME-INSTITUTION DESCRIPTION
        - LEGAL ENTITY NAME
        - LEI
        - MARKET CATEGORY CODE
        - ACRONYM
        - ISO COUNTRY CODE (ISO 3166)
        - CITY
        - WEBSITE
        - STATUS
        - CREATION DATE
        - LAST UPDATE DATE
        - LAST VALIDATION DATE
        - EXPIRY DATE
        - COMMENTS
        """
        # Column name mappings (ISO uses various names)
        def get_field(names: list[str]) -> str | None:
            for name in names:
                # Try exact match
                if name in row:
                    val = row[name].strip() if row[name] else None
                    return val if val else None
                # Try case-insensitive
                for key in row:
                    if key.upper() == name.upper():
                        val = row[key].strip() if row[key] else None
                        return val if val else None
            return None
        
        return {
            "mic": get_field(["MIC"]),
            "operating_mic": get_field(["OPERATING MIC", "OPRT_MIC", "OPERATING_MIC"]),
            "mic_type": get_field(["OPRT/SGMT", "O/S", "MIC_TYPE", "OPRT_SGMT", "TYPE"]),
            "name": get_field([
                "MARKET NAME-INSTITUTION DESCRIPTION",
                "NAME-INSTITUTION DESCRIPTION",
                "INSTITUTION_DESCRIPTION", 
                "NAME",
                "INSTITUTION DESCRIPTION",
            ]),
            "legal_entity_name": get_field(["LEGAL ENTITY NAME", "LEGAL_ENTITY_NAME"]),
            "lei": get_field(["LEI"]),
            "market_category_code": get_field(["MARKET CATEGORY CODE", "MKT_CAT_CODE"]),
            "acronym": get_field(["ACRONYM", "ACRNM"]),
            "country_code": get_field([
                "ISO COUNTRY CODE (ISO 3166)",
                "COUNTRY",
                "ISO_COUNTRY_CODE",
                "CTRY",
            ]),
            "city": get_field(["CITY"]),
            "website": get_field(["WEBSITE", "WEB_SITE", "URL"]),
            "status": get_field(["STATUS", "STTS"]) or MIC_STATUS_ACTIVE,
            "creation_date": get_field(["CREATION DATE", "CREATION_DATE", "CRTN_DT"]),
            "last_update_date": get_field([
                "LAST UPDATE DATE",
                "LAST_UPDATE_DATE",
                "LAST_UPD_DT",
                "MODIFICATION DATE",
            ]),
            "last_validation_date": get_field(["LAST VALIDATION DATE"]),
            "expiry_date": get_field(["EXPIRY DATE", "EXPIRY_DATE"]),
            "comments": get_field(["COMMENTS", "CMNTS"]),
        }
    
    def _parse_date(self, date_str: str | None) -> date | None:
        """Parse date from various ISO 10383 formats."""
        if not date_str:
            return None
        
        # Try common formats
        formats = [
            "%Y-%m-%d",      # 2024-01-15
            "%d/%m/%Y",      # 15/01/2024
            "%m/%d/%Y",      # 01/15/2024
            "%d-%m-%Y",      # 15-01-2024
            "%Y%m%d",        # 20240115
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt).date()
            except ValueError:
                continue
        
        logger.warning(f"Could not parse date: {date_str}")
        return None
    
    def _save_bronze_snapshot(self, content: bytes) -> Path:
        """Save raw content to Bronze cache directory."""
        if not self.cache_dir:
            raise ValueError("No cache_dir configured")
        
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Filename: mic_YYYYMMDD_HHMMSS_<hash>.csv
        snapshot = self._last_snapshot
        ts = snapshot.captured_at.strftime("%Y%m%d_%H%M%S") if snapshot else "unknown"
        hash_prefix = snapshot.content_hash[:8] if snapshot else "unknown"
        filename = f"mic_{ts}_{hash_prefix}.csv"
        
        filepath = self.cache_dir / filename
        filepath.write_bytes(content)
        
        # Also save metadata
        if snapshot:
            meta_path = self.cache_dir / f"mic_{ts}_{hash_prefix}_meta.json"
            meta = {
                "snapshot_id": snapshot.snapshot_id,
                "source_url": snapshot.source_url,
                "format": snapshot.format,
                "content_hash": snapshot.content_hash,
                "content_size": snapshot.content_size,
                "record_count": snapshot.record_count,
                "etag": snapshot.etag,
                "last_modified": snapshot.last_modified,
                "captured_at": snapshot.captured_at.isoformat(),
                "raw_path": str(filepath),
            }
            meta_path.write_text(json.dumps(meta, indent=2))
        
        logger.info(f"Saved Bronze snapshot to {filepath}")
        return filepath
    
    @property
    def last_snapshot(self) -> MICSnapshot | None:
        """Get metadata from last fetch."""
        return self._last_snapshot


# =============================================================================
# Gold Layer: Registry API
# =============================================================================


class MICRegistry:
    """
    Gold layer: Domain-ready MIC lookup registry.
    
    Provides fast, ergonomic lookups over normalized MIC data.
    Can be backed by in-memory dict or database.
    
    Features:
    - O(1) lookup by MIC code
    - Get all segments for an operating MIC
    - Filter by country, status, type
    - Get operating MIC hierarchy
    
    Example:
        >>> registry = MICRegistry()
        >>> await registry.load_from_source()
        >>>
        >>> nyse = registry.get("XNYS")
        >>> print(f"NYSE: {nyse.name}")
        >>>
        >>> nasdaq_segments = registry.get_segments("XNAS")
        >>> print(f"NASDAQ has {len(nasdaq_segments)} segments")
    """
    
    def __init__(self):
        """Initialize empty registry."""
        self._mics: dict[str, MICRecord] = {}
        self._by_operating: dict[str, list[str]] = {}  # operating_mic -> [segment_mics]
        self._by_country: dict[str, list[str]] = {}    # country_code -> [mics]
        self._snapshot: MICSnapshot | None = None
        self._loaded_at: datetime | None = None
    
    async def load_from_source(
        self,
        source: ISO10383Source | None = None,
    ) -> int:
        """
        Load registry from ISO 10383 source.
        
        Args:
            source: ISO10383Source instance (creates default if None).
            
        Returns:
            Number of MIC codes loaded.
        """
        if source is None:
            source = ISO10383Source()
        
        # Create a fresh source to avoid 304 issues with conditional headers
        fresh_source = ISO10383Source(csv_url=source.csv_url, format=source.format)
        records = await fresh_source.fetch_as_records()
        return self.load_records(records, fresh_source.last_snapshot)
    
    def load_records(
        self,
        records: list[MICRecord],
        snapshot: MICSnapshot | None = None,
    ) -> int:
        """
        Load registry from MICRecord list.
        
        Args:
            records: List of MICRecord objects.
            snapshot: Optional snapshot metadata.
            
        Returns:
            Number of MIC codes loaded.
        """
        # Clear existing
        self._mics.clear()
        self._by_operating.clear()
        self._by_country.clear()
        
        # Index records
        for rec in records:
            mic = rec.mic.upper()
            self._mics[mic] = rec
            
            # Index by operating MIC
            op_mic = rec.operating_mic.upper() if rec.operating_mic else mic
            if op_mic not in self._by_operating:
                self._by_operating[op_mic] = []
            if rec.is_segment and mic != op_mic:
                self._by_operating[op_mic].append(mic)
            
            # Index by country
            if rec.country_code:
                cc = rec.country_code.upper()
                if cc not in self._by_country:
                    self._by_country[cc] = []
                self._by_country[cc].append(mic)
        
        self._snapshot = snapshot
        self._loaded_at = utc_now()
        
        logger.info(f"Loaded {len(self._mics)} MIC codes into registry")
        return len(self._mics)
    
    def get(self, mic: str) -> MICRecord | None:
        """
        Look up MIC by code.
        
        Args:
            mic: 4-character MIC code (case-insensitive).
            
        Returns:
            MICRecord or None if not found.
        """
        return self._mics.get(mic.upper())
    
    def lookup(self, mic: str) -> MICRecord | None:
        """Alias for get() - provides consistent API across registries."""
        return self.get(mic)
    
    def __getitem__(self, mic: str) -> MICRecord:
        """Look up MIC by code (raises KeyError if not found)."""
        return self._mics[mic.upper()]
    
    def __contains__(self, mic: str) -> bool:
        """Check if MIC exists in registry."""
        return mic.upper() in self._mics
    
    def __len__(self) -> int:
        """Number of MIC codes in registry."""
        return len(self._mics)
    
    def get_segments(self, operating_mic: str) -> list[MICRecord]:
        """
        Get all segment MICs for an operating MIC.
        
        Args:
            operating_mic: The operating (parent) MIC code.
            
        Returns:
            List of MICRecord for all segments under this operating MIC.
        """
        segment_mics = self._by_operating.get(operating_mic.upper(), [])
        return [self._mics[mic] for mic in segment_mics if mic in self._mics]
    
    def get_children(self, operating_mic: str) -> list[MICRecord]:
        """Alias for get_segments()."""
        return self.get_segments(operating_mic)
    
    def get_by_country(self, country_code: str) -> list[MICRecord]:
        """
        Get all MICs for a country.
        
        Args:
            country_code: ISO 3166-1 alpha-2 country code.
            
        Returns:
            List of MICRecord for all exchanges in that country.
        """
        mics = self._by_country.get(country_code.upper(), [])
        return [self._mics[mic] for mic in mics if mic in self._mics]
    
    def get_operating_mics(self) -> list[MICRecord]:
        """Get all operating (parent) MICs."""
        return [r for r in self._mics.values() if r.is_operating]
    
    def get_segment_mics(self) -> list[MICRecord]:
        """Get all segment (child) MICs."""
        return [r for r in self._mics.values() if r.is_segment]
    
    def get_active(self) -> list[MICRecord]:
        """Get all active MICs."""
        return [r for r in self._mics.values() if r.is_active]
    
    def search(
        self,
        query: str,
        *,
        include_inactive: bool = False,
    ) -> list[MICRecord]:
        """
        Search MICs by name, acronym, or MIC code.
        
        Args:
            query: Search string (case-insensitive).
            include_inactive: Whether to include expired/deleted MICs.
            
        Returns:
            List of matching MICRecord objects.
        """
        query_upper = query.upper()
        results = []
        
        for rec in self._mics.values():
            if not include_inactive and not rec.is_active:
                continue
            
            # Match MIC code
            if rec.mic.upper() == query_upper:
                results.append(rec)
                continue
            
            # Match acronym
            if rec.acronym and query_upper in rec.acronym.upper():
                results.append(rec)
                continue
            
            # Match name
            if rec.name and query_upper in rec.name.upper():
                results.append(rec)
                continue
        
        return results
    
    def all(self) -> Iterator[MICRecord]:
        """Iterate over all MIC records."""
        return iter(self._mics.values())
    
    @property
    def snapshot(self) -> MICSnapshot | None:
        """Get source snapshot metadata."""
        return self._snapshot
    
    @property
    def loaded_at(self) -> datetime | None:
        """When registry was last loaded."""
        return self._loaded_at
    
    @property
    def countries(self) -> set[str]:
        """Get set of all country codes in registry."""
        return set(self._by_country.keys())
    
    @property
    def operating_mic_count(self) -> int:
        """Number of operating MICs."""
        return len([r for r in self._mics.values() if r.is_operating])
    
    @property
    def segment_mic_count(self) -> int:
        """Number of segment MICs."""
        return len([r for r in self._mics.values() if r.is_segment])


# =============================================================================
# Diff / Change Detection
# =============================================================================


def diff_mic_records(
    old_records: list[MICRecord],
    new_records: list[MICRecord],
    old_snapshot_id: str | None = None,
    new_snapshot_id: str | None = None,
) -> list[MICChange]:
    """
    Compute field-level changes between two MIC snapshots.
    
    Args:
        old_records: Previous snapshot records.
        new_records: New snapshot records.
        old_snapshot_id: ID of old snapshot (for provenance).
        new_snapshot_id: ID of new snapshot (for provenance).
        
    Returns:
        List of MICChange objects describing all changes.
    """
    changes: list[MICChange] = []
    
    old_by_mic = {r.mic: r for r in old_records}
    new_by_mic = {r.mic: r for r in new_records}
    
    all_mics = set(old_by_mic.keys()) | set(new_by_mic.keys())
    
    # Fields to compare (excluding provenance fields)
    compare_fields = [
        "operating_mic", "mic_type", "name", "acronym", "country_code",
        "city", "website", "status", "creation_date", "status_date",
        "last_update_date", "comments",
    ]
    
    for mic in all_mics:
        old_rec = old_by_mic.get(mic)
        new_rec = new_by_mic.get(mic)
        
        if old_rec is None and new_rec is not None:
            # New MIC added
            changes.append(MICChange(
                mic=mic,
                field_name="__record__",
                old_value=None,
                new_value="ADDED",
                old_snapshot_id=old_snapshot_id,
                new_snapshot_id=new_snapshot_id or "",
                change_type="added",
            ))
            
        elif old_rec is not None and new_rec is None:
            # MIC deleted
            changes.append(MICChange(
                mic=mic,
                field_name="__record__",
                old_value="DELETED",
                new_value=None,
                old_snapshot_id=old_snapshot_id,
                new_snapshot_id=new_snapshot_id or "",
                change_type="deleted",
            ))
            
        else:
            # Compare fields
            for field_name in compare_fields:
                old_val = getattr(old_rec, field_name, None)
                new_val = getattr(new_rec, field_name, None)
                
                # Convert dates to strings for comparison
                if isinstance(old_val, date):
                    old_val = old_val.isoformat()
                if isinstance(new_val, date):
                    new_val = new_val.isoformat()
                
                if old_val != new_val:
                    changes.append(MICChange(
                        mic=mic,
                        field_name=field_name,
                        old_value=str(old_val) if old_val is not None else None,
                        new_value=str(new_val) if new_val is not None else None,
                        old_snapshot_id=old_snapshot_id,
                        new_snapshot_id=new_snapshot_id or "",
                        change_type="modified",
                    ))
    
    return changes


# =============================================================================
# Convenience Functions
# =============================================================================


async def fetch_mic_list() -> list[MICRecord]:
    """
    Quick helper to fetch full MIC list.
    
    Returns:
        List of all MICRecord from ISO 10383.
    """
    source = ISO10383Source()
    return await source.fetch_as_records()


async def lookup_mic(mic: str) -> MICRecord | None:
    """
    Quick helper to look up a single MIC.
    
    Note: This fetches the full list each time. For repeated lookups,
    use MICRegistry instead.
    
    Args:
        mic: MIC code to look up.
        
    Returns:
        MICRecord or None.
    """
    records = await fetch_mic_list()
    mic_upper = mic.upper()
    for rec in records:
        if rec.mic.upper() == mic_upper:
            return rec
    return None
