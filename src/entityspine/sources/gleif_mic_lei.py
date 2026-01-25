"""
GLEIF MIC-to-LEI Relationship Source.

STDLIB ONLY - NO PYDANTIC.

Downloads and manages the GLEIF mapping between MIC codes and LEI identifiers.
This enables linking exchanges (MIC) to their legal entity operators (LEI).

Data Source:
- GLEIF provides a daily-updated file mapping MIC to LEI
- URL: https://www.gleif.org/en/lei-data/lei-mapping/download-mic-to-lei-relationship-files

Use Cases:
- Link Exchange MIC to operator Entity via LEI
- Build "exchange operator entities" in Entity Spine
- Validate MIC<->LEI relationships across vendors
- Enable claims: scheme=MIC linking to scheme=LEI

Example:
    >>> from entityspine.sources import GLEIFMICLEISource
    >>>
    >>> source = GLEIFMICLEISource()
    >>> mappings = await source.fetch()
    >>> print(f"Got {len(mappings)} MIC-LEI mappings")
    >>>
    >>> # Find LEI for NYSE
    >>> nyse = next(m for m in mappings if m['mic'] == 'XNYS')
    >>> print(f"NYSE LEI: {nyse['lei']}")

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
from typing import Any

from entityspine.domain.timestamps import utc_now

logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

# GLEIF MIC-LEI mapping file URL
# Note: GLEIF hosts this at a stable URL, updated daily
GLEIF_MIC_LEI_URL = "https://www.gleif.org/lei-files/lei-lookup-service/mic-to-lei-relationship-file"

# Alternative direct download URL (CSV format)
GLEIF_MIC_LEI_CSV_URL = "https://www.gleif.org/content/4-lei-data/4-lei-mapping/mic-to-lei.csv"


# =============================================================================
# Data Models
# =============================================================================


@dataclass(frozen=True, slots=True)
class MICLEIMapping:
    """
    A mapping between MIC code and LEI.
    
    GLEIF provides this relationship to connect exchange MICs
    to their operating legal entities.
    
    Attributes:
        mic: Market Identifier Code (ISO 10383).
        lei: Legal Entity Identifier (ISO 17442).
        lei_name: Name of the legal entity.
        mic_name: Name of the market (from MIC data).
        relationship_type: Type of relationship (e.g., "OPERATOR").
        valid_from: When relationship became valid.
        valid_to: When relationship ended (None if current).
        source: Source of the mapping.
        captured_at: When we captured this record.
    """
    mic: str
    lei: str
    lei_name: str | None = None
    mic_name: str | None = None
    relationship_type: str = "OPERATOR"
    valid_from: date | None = None
    valid_to: date | None = None
    source: str = "gleif"
    captured_at: datetime = field(default_factory=utc_now)
    
    @property
    def is_current(self) -> bool:
        """Check if mapping is currently valid."""
        if self.valid_to is None:
            return True
        return self.valid_to >= date.today()


@dataclass(frozen=True, slots=True)
class MICLEISnapshot:
    """
    Metadata for a GLEIF MIC-LEI download snapshot.
    
    Attributes:
        snapshot_id: Unique identifier.
        source_url: URL data was fetched from.
        content_hash: SHA-256 of content.
        record_count: Number of mappings.
        captured_at: When snapshot was captured.
    """
    snapshot_id: str
    source_url: str
    content_hash: str
    record_count: int
    captured_at: datetime = field(default_factory=utc_now)


# =============================================================================
# Source Implementation
# =============================================================================


class GLEIFMICLEISource:
    """
    GLEIF MIC-to-LEI relationship file source.
    
    Downloads the GLEIF mapping file that connects exchange MICs
    to their operating legal entity LEIs.
    
    Features:
    - Automatic download and parsing
    - Bronze snapshot storage
    - Provenance tracking
    
    Attributes:
        name: Source identifier ("gleif-mic-lei")
        url: Download URL
        
    Example:
        >>> source = GLEIFMICLEISource()
        >>> mappings = await source.fetch()
        >>> 
        >>> # Build MIC->LEI lookup
        >>> mic_to_lei = {m['mic']: m['lei'] for m in mappings}
        >>> print(f"NYSE LEI: {mic_to_lei.get('XNYS')}")
    """
    
    name: str = "gleif-mic-lei"
    url: str = GLEIF_MIC_LEI_CSV_URL
    
    def __init__(
        self,
        url: str | None = None,
        cache_dir: Path | str | None = None,
    ):
        """
        Initialize GLEIF MIC-LEI source.
        
        Args:
            url: Override URL for testing.
            cache_dir: Directory for storing snapshots.
        """
        if url:
            self.url = url
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self._last_snapshot: MICLEISnapshot | None = None
    
    async def fetch(self) -> list[dict[str, Any]]:
        """
        Fetch MIC-LEI mappings from GLEIF.
        
        Returns:
            List of dicts with mic, lei, and relationship data.
        """
        logger.info(f"Fetching GLEIF MIC-LEI mappings from {self.url}")
        
        content = await self._download()
        records = self._parse_csv(content)
        
        # Create snapshot metadata
        content_hash = hashlib.sha256(content).hexdigest()
        self._last_snapshot = MICLEISnapshot(
            snapshot_id=f"mic_lei_{content_hash[:16]}",
            source_url=self.url,
            content_hash=content_hash,
            record_count=len(records),
            captured_at=utc_now(),
        )
        
        logger.info(f"Parsed {len(records)} MIC-LEI mappings from GLEIF")
        return records
    
    async def fetch_as_records(self) -> list[MICLEIMapping]:
        """
        Fetch and return typed MICLEIMapping objects.
        
        Returns:
            List of MICLEIMapping dataclass instances.
        """
        raw_records = await self.fetch()
        
        return [
            MICLEIMapping(
                mic=r["mic"],
                lei=r["lei"],
                lei_name=r.get("lei_name"),
                mic_name=r.get("mic_name"),
                relationship_type=r.get("relationship_type", "OPERATOR"),
                valid_from=self._parse_date(r.get("valid_from")),
                valid_to=self._parse_date(r.get("valid_to")),
                source="gleif",
                captured_at=utc_now(),
            )
            for r in raw_records
        ]
    
    async def _download(self) -> bytes:
        """Download raw content from GLEIF."""
        try:
            req = urllib.request.Request(
                self.url,
                headers={
                    "User-Agent": "EntitySpine/1.0 (MIC-LEI mapping ingestion)",
                    "Accept": "text/csv, application/csv, */*",
                },
            )
            
            with urllib.request.urlopen(req, timeout=60) as response:
                return response.read()
                
        except Exception as e:
            logger.error(f"Failed to fetch GLEIF MIC-LEI data: {e}")
            raise IOError(f"Failed to fetch GLEIF MIC-LEI data: {e}") from e
    
    def _parse_csv(self, content: bytes) -> list[dict[str, Any]]:
        """Parse GLEIF MIC-LEI CSV content."""
        # Try UTF-8 first
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            text = content.decode("latin-1")
        
        reader = csv.DictReader(io.StringIO(text))
        records = []
        
        for row in reader:
            record = self._normalize_row(row)
            if record and record.get("mic") and record.get("lei"):
                records.append(record)
        
        return records
    
    def _normalize_row(self, row: dict[str, str]) -> dict[str, Any]:
        """Normalize CSV row to standard field names."""
        def get_field(names: list[str]) -> str | None:
            for name in names:
                if name in row:
                    val = row[name].strip() if row[name] else None
                    return val if val else None
                for key in row:
                    if key.upper() == name.upper():
                        val = row[key].strip() if row[key] else None
                        return val if val else None
            return None
        
        return {
            "mic": get_field(["MIC", "MIC_CODE", "MARKET_IDENTIFIER_CODE"]),
            "lei": get_field(["LEI", "LEI_CODE", "LEGAL_ENTITY_IDENTIFIER"]),
            "lei_name": get_field(["LEI_NAME", "ENTITY_NAME", "LEGAL_NAME"]),
            "mic_name": get_field(["MIC_NAME", "MARKET_NAME", "INSTITUTION_NAME"]),
            "relationship_type": get_field(["RELATIONSHIP", "RELATIONSHIP_TYPE", "REL_TYPE"]) or "OPERATOR",
            "valid_from": get_field(["VALID_FROM", "START_DATE", "EFFECTIVE_DATE"]),
            "valid_to": get_field(["VALID_TO", "END_DATE", "EXPIRY_DATE"]),
        }
    
    def _parse_date(self, date_str: str | None) -> date | None:
        """Parse date from various formats."""
        if not date_str:
            return None
        
        formats = ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y%m%d"]
        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt).date()
            except ValueError:
                continue
        return None
    
    @property
    def last_snapshot(self) -> MICLEISnapshot | None:
        """Get metadata from last fetch."""
        return self._last_snapshot


# =============================================================================
# Convenience Functions
# =============================================================================


async def fetch_mic_lei_mappings() -> list[MICLEIMapping]:
    """
    Quick helper to fetch all MIC-LEI mappings.
    
    Returns:
        List of MICLEIMapping from GLEIF.
    """
    source = GLEIFMICLEISource()
    return await source.fetch_as_records()


async def get_lei_for_mic(mic: str) -> str | None:
    """
    Quick helper to get LEI for a MIC code.
    
    Note: Fetches full list each time. For repeated lookups,
    cache the result of fetch_mic_lei_mappings().
    
    Args:
        mic: MIC code to look up.
        
    Returns:
        LEI string or None.
    """
    mappings = await fetch_mic_lei_mappings()
    mic_upper = mic.upper()
    for m in mappings:
        if m.mic.upper() == mic_upper and m.is_current:
            return m.lei
    return None
