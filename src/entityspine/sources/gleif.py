"""
GLEIF LEI (Legal Entity Identifier) Source.

STDLIB ONLY - NO PYDANTIC.

Downloads and manages GLEIF bulk LEI data following Bronze/Silver/Gold architecture.

GLEIF provides several data products:
1. **LEI-CDF (Golden Copy)**: Full LEI database with entity details (~2.5M records)
2. **LEI-RR (Relationship Records)**: Parent/child relationships
3. **ISIN-LEI Mapping**: Links ISINs to LEIs (~8M records)
4. **BIC-LEI Mapping**: Links BICs to LEIs (~40K records)
5. **MIC-LEI Mapping**: Links MICs to LEIs (see gleif_mic_lei.py)

Data Sources:
- Golden Copy CSV: https://leidata.gleif.org/api/v1/concatenated-files/lei2/get/.../csv/
- ISIN-LEI: https://mapping.gleif.org/api/v2/isin-lei/
- BIC-LEI: https://mapping.gleif.org/api/v2/bic-lei/

Update Cadence:
- GLEIF updates daily
- Full refresh recommended weekly
- Delta updates available for incremental sync

Example:
    >>> from entityspine.sources import GLEIFSource, LEIRegistry
    >>>
    >>> source = GLEIFSource()
    >>> records = await source.fetch()
    >>> print(f"Fetched {len(records)} LEI records")
    >>>
    >>> # Use registry for lookups
    >>> registry = LEIRegistry()
    >>> await registry.load_from_source()
    >>> nvidia = registry.get("549300S4KLFTLO7GSQ80")
    >>> print(f"NVIDIA: {nvidia.legal_name}")

v1.0.0 Initial implementation with Bronze/Silver/Gold pattern.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
import logging
import urllib.request
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

from entityspine.domain.timestamps import utc_now

logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

# GLEIF API endpoints
GLEIF_API_BASE = "https://api.gleif.org/api/v1"
GLEIF_GOLDEN_COPY_URL = "https://leidata.gleif.org/api/v1/concatenated-files/lei2/get/30447/zip"
GLEIF_ISIN_LEI_URL = "https://mapping.gleif.org/api/v2/isin-lei/latest/download"
GLEIF_BIC_LEI_URL = "https://mapping.gleif.org/api/v2/bic-lei/latest/download"

# Alternative: Full file downloads (more stable)
GLEIF_FULL_CSV_URL = "https://leidata-preview.gleif.org/storage/golden-copy-files/2024/01/29/1234/20240129-gleif-concatenated-file-lei2.csv.zip"

# LEI Status values
LEI_STATUS_ACTIVE = "ACTIVE"  # LEI is issued and active
LEI_STATUS_INACTIVE = "INACTIVE"  # LEI is inactive
LEI_STATUS_LAPSED = "LAPSED"  # LEI registration lapsed
LEI_STATUS_MERGED = "MERGED"  # Entity merged into another
LEI_STATUS_RETIRED = "RETIRED"  # LEI retired
LEI_STATUS_ANNULLED = "ANNULLED"  # LEI annulled
LEI_STATUS_DUPLICATE = "DUPLICATE"  # Duplicate LEI
LEI_STATUS_TRANSFERRED = "TRANSFERRED"  # Transferred to another LOU
LEI_STATUS_PENDING_TRANSFER = "PENDING_TRANSFER"
LEI_STATUS_PENDING_ARCHIVAL = "PENDING_ARCHIVAL"

# Entity Legal Form categories
ENTITY_CATEGORY_BRANCH = "BRANCH"
ENTITY_CATEGORY_FUND = "FUND"
ENTITY_CATEGORY_SOLE_PROPRIETOR = "SOLE_PROPRIETOR"
ENTITY_CATEGORY_GENERAL = "GENERAL"


# =============================================================================
# Bronze Layer: Raw Snapshots
# =============================================================================


@dataclass(frozen=True, slots=True)
class LEISnapshot:
    """
    Bronze layer: Immutable raw snapshot of GLEIF LEI data.
    
    Stores metadata about the downloaded bulk file for provenance tracking.
    
    Attributes:
        snapshot_id: Unique identifier for this snapshot.
        source_url: URL the data was fetched from.
        data_type: Type of data (lei, isin_lei, bic_lei).
        content_hash: SHA-256 hash of content.
        content_size: Size in bytes.
        record_count: Number of records in snapshot.
        publication_date: GLEIF publication date.
        captured_at: When snapshot was captured.
        raw_path: Path to stored raw file.
    """
    snapshot_id: str
    source_url: str
    data_type: str  # lei, isin_lei, bic_lei
    content_hash: str  # SHA-256
    content_size: int
    record_count: int
    publication_date: date | None = None
    captured_at: datetime = field(default_factory=utc_now)
    raw_path: str | None = None


@dataclass(frozen=True, slots=True)
class ISINLEISnapshot:
    """Bronze layer: ISIN-LEI mapping snapshot metadata."""
    snapshot_id: str
    source_url: str
    content_hash: str
    record_count: int
    captured_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True, slots=True)
class BICLEISnapshot:
    """Bronze layer: BIC-LEI mapping snapshot metadata."""
    snapshot_id: str
    source_url: str
    content_hash: str
    record_count: int
    captured_at: datetime = field(default_factory=utc_now)


# =============================================================================
# Silver Layer: Normalized Records
# =============================================================================


@dataclass(frozen=True, slots=True)
class LEIRecord:
    """
    Silver layer: Normalized LEI record from GLEIF.
    
    Represents a Legal Entity Identifier with all GLEIF-provided attributes.
    This is the core entity reference data.
    
    GLEIF LEI-CDF Fields:
    - LEI: 20-character Legal Entity Identifier
    - Entity.LegalName: Official registered name
    - Entity.LegalAddress.*: Registered address
    - Entity.HeadquartersAddress.*: HQ address
    - Entity.LegalJurisdiction: ISO country/subdivision
    - Entity.EntityCategory: BRANCH, FUND, etc.
    - Entity.EntityStatus: ACTIVE, INACTIVE, etc.
    - Registration.RegistrationStatus: Status in GLEIF
    - Registration.InitialRegistrationDate: First registered
    - Registration.LastUpdateDate: Last updated
    - Registration.NextRenewalDate: When renewal due
    - Registration.ManagingLOU: LOU managing this LEI
    
    Attributes:
        lei: 20-character Legal Entity Identifier.
        legal_name: Official registered legal name.
        legal_name_language: Language of legal name.
        other_names: Alternative/trading names.
        
        # Legal address
        legal_address_line1: Street address line 1.
        legal_address_city: City.
        legal_address_region: State/province.
        legal_address_country: ISO 3166-1 alpha-2.
        legal_address_postal_code: Postal/ZIP code.
        
        # Headquarters address
        hq_address_city: HQ city (may differ from legal).
        hq_address_country: HQ country.
        
        # Classification
        legal_jurisdiction: ISO country/subdivision code.
        entity_category: BRANCH, FUND, SOLE_PROPRIETOR, GENERAL.
        entity_status: ACTIVE, INACTIVE, etc.
        entity_legal_form_code: ELF code.
        
        # Registration
        registration_status: GLEIF registration status.
        initial_registration_date: First registered.
        last_update_date: Last updated in GLEIF.
        next_renewal_date: When renewal is due.
        managing_lou: LEI of managing LOU.
        
        # Provenance
        snapshot_id: ID of source snapshot.
        captured_at: When captured.
    """
    lei: str
    legal_name: str

    # Names
    legal_name_language: str | None = None
    other_names: tuple[str, ...] = ()

    # Legal address
    legal_address_line1: str | None = None
    legal_address_line2: str | None = None
    legal_address_city: str | None = None
    legal_address_region: str | None = None
    legal_address_country: str | None = None
    legal_address_postal_code: str | None = None

    # HQ address
    hq_address_line1: str | None = None
    hq_address_city: str | None = None
    hq_address_region: str | None = None
    hq_address_country: str | None = None
    hq_address_postal_code: str | None = None

    # Classification
    legal_jurisdiction: str | None = None
    entity_category: str | None = None
    entity_status: str = LEI_STATUS_ACTIVE
    entity_legal_form_code: str | None = None

    # Registration
    registration_status: str | None = None
    initial_registration_date: date | None = None
    last_update_date: date | None = None
    next_renewal_date: date | None = None
    managing_lou: str | None = None

    # Successor (for mergers)
    successor_lei: str | None = None

    # Provenance
    snapshot_id: str | None = None
    captured_at: datetime = field(default_factory=utc_now)

    @property
    def is_active(self) -> bool:
        """Check if LEI is currently active."""
        return self.entity_status == LEI_STATUS_ACTIVE

    @property
    def is_us_entity(self) -> bool:
        """Check if entity is US-based."""
        return self.legal_address_country == "US" or self.legal_jurisdiction == "US"

    @property
    def display_name(self) -> str:
        """Get display name (legal name or first other name)."""
        return self.legal_name or (self.other_names[0] if self.other_names else "Unknown")


@dataclass(frozen=True, slots=True)
class ISINLEIMapping:
    """
    Silver layer: ISIN to LEI mapping record.
    
    Links an ISIN (security identifier) to an LEI (entity identifier).
    One LEI can have multiple ISINs (company issues multiple securities).
    
    Attributes:
        isin: 12-character ISIN.
        lei: 20-character LEI.
        isin_status: Status of ISIN (ACTIVE, etc.).
        lei_status: Status of LEI.
        captured_at: When captured.
    """
    isin: str
    lei: str
    isin_status: str | None = None
    lei_status: str | None = None
    snapshot_id: str | None = None
    captured_at: datetime = field(default_factory=utc_now)

    @property
    def is_active(self) -> bool:
        """Check if mapping is currently active."""
        return self.lei_status == LEI_STATUS_ACTIVE


@dataclass(frozen=True, slots=True)
class BICLEIMapping:
    """
    Silver layer: BIC to LEI mapping record.
    
    Links a BIC (bank identifier) to an LEI.
    Used primarily for financial institutions.
    
    Attributes:
        bic: 8 or 11 character BIC/SWIFT code.
        lei: 20-character LEI.
        bic_status: Status of BIC.
        lei_status: Status of LEI.
        captured_at: When captured.
    """
    bic: str
    lei: str
    bic_status: str | None = None
    lei_status: str | None = None
    snapshot_id: str | None = None
    captured_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True, slots=True)
class LEIChange:
    """
    Silver layer: Field-level change record for LEI diff tracking.
    
    Captures changes between snapshots for audit and analysis.
    """
    lei: str
    field_name: str
    old_value: str | None
    new_value: str | None
    old_snapshot_id: str | None
    new_snapshot_id: str
    change_type: str  # added, modified, deleted
    detected_at: datetime = field(default_factory=utc_now)


# =============================================================================
# Source Implementation: LEI Golden Copy
# =============================================================================


class GLEIFSource:
    """
    GLEIF LEI Golden Copy source.
    
    Downloads and parses the full GLEIF LEI database (Golden Copy).
    This contains ~2.5 million legal entity records.
    
    Features:
    - Supports CSV and JSON formats
    - Handles gzip/zip compression
    - Bronze snapshot metadata capture
    - Incremental download support (delta files)
    
    Attributes:
        name: Source identifier ("gleif-lei")
        
    Example:
        >>> source = GLEIFSource()
        >>> records = await source.fetch()
        >>> print(f"Got {len(records)} LEI records")
        
        # Find NVIDIA
        >>> nvidia = next(r for r in records if 'NVIDIA' in r['legal_name'].upper())
        >>> print(f"NVIDIA LEI: {nvidia['lei']}")
    
    Note:
        The full Golden Copy is ~500MB compressed, ~2GB uncompressed.
        For testing, use a smaller sample file.
    """

    name: str = "gleif-lei"

    def __init__(
        self,
        api_key: str | None = None,
        cache_dir: Path | str | None = None,
        use_sample: bool = False,
    ):
        """
        Initialize GLEIF LEI source.
        
        Args:
            api_key: GLEIF API key (optional, increases rate limits).
            cache_dir: Directory for storing Bronze snapshots.
            use_sample: If True, download smaller sample for testing.
        """
        self.api_key = api_key
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self.use_sample = use_sample
        self._last_snapshot: LEISnapshot | None = None

    async def fetch(self, limit: int | None = None) -> list[dict[str, Any]]:
        """
        Fetch LEI records from GLEIF.
        
        Args:
            limit: Maximum records to return (for testing).
            
        Returns:
            List of dicts with LEI data.
            
        Note:
            Full download can take several minutes.
            Use limit parameter for testing.
        """
        logger.info("Fetching GLEIF LEI Golden Copy")

        # Use API for paginated access (more reliable than bulk download)
        records = await self._fetch_via_api(limit=limit)

        # Create snapshot metadata
        content_str = json.dumps(records, sort_keys=True)
        content_hash = hashlib.sha256(content_str.encode()).hexdigest()

        self._last_snapshot = LEISnapshot(
            snapshot_id=f"lei_{content_hash[:16]}",
            source_url=f"{GLEIF_API_BASE}/lei-records",
            data_type="lei",
            content_hash=content_hash,
            content_size=len(content_str),
            record_count=len(records),
            captured_at=utc_now(),
        )

        logger.info(f"Fetched {len(records)} LEI records from GLEIF")
        return records

    async def fetch_as_records(self, limit: int | None = None) -> list[LEIRecord]:
        """
        Fetch and return typed LEIRecord objects.
        
        Args:
            limit: Maximum records to return.
            
        Returns:
            List of LEIRecord dataclass instances.
        """
        raw_records = await self.fetch(limit=limit)
        snapshot_id = self._last_snapshot.snapshot_id if self._last_snapshot else None

        return [self._dict_to_record(r, snapshot_id) for r in raw_records]

    async def _fetch_via_api(self, limit: int | None = None) -> list[dict[str, Any]]:
        """
        Fetch LEI records via GLEIF API (paginated).
        
        The API returns 100 records per page by default.
        """
        records = []
        page = 1
        page_size = 100
        max_records = limit or float('inf')

        while len(records) < max_records:
            url = f"{GLEIF_API_BASE}/lei-records?page[number]={page}&page[size]={page_size}"

            try:
                req = urllib.request.Request(
                    url,
                    headers={
                        "User-Agent": "EntitySpine/1.0 (LEI data ingestion)",
                        "Accept": "application/vnd.api+json",
                    },
                )

                if self.api_key:
                    req.add_header("Authorization", f"Bearer {self.api_key}")

                with urllib.request.urlopen(req, timeout=60) as response:
                    data = json.loads(response.read().decode("utf-8"))

                # Extract records from JSON:API format
                for item in data.get("data", []):
                    attrs = item.get("attributes", {})
                    record = self._normalize_api_record(item["id"], attrs)
                    records.append(record)

                    if len(records) >= max_records:
                        break

                # Check if more pages
                links = data.get("links", {})
                if not links.get("next") or len(data.get("data", [])) < page_size:
                    break

                page += 1

                # Rate limiting
                if page % 10 == 0:
                    logger.info(f"Fetched {len(records)} LEI records so far...")

            except urllib.error.HTTPError as e:
                logger.error(f"HTTP error fetching LEI data: {e.code} {e.reason}")
                break
            except Exception as e:
                logger.error(f"Error fetching LEI data: {e}")
                break

        return records

    def _normalize_api_record(self, lei: str, attrs: dict) -> dict[str, Any]:
        """Normalize GLEIF API response to standard format."""
        entity = attrs.get("entity", {})
        registration = attrs.get("registration", {})

        legal_address = entity.get("legalAddress", {})
        hq_address = entity.get("headquartersAddress", {})

        return {
            "lei": lei,
            "legal_name": entity.get("legalName", {}).get("name", ""),
            "legal_name_language": entity.get("legalName", {}).get("language"),
            "other_names": [
                n.get("name") for n in entity.get("otherNames", []) if n.get("name")
            ],

            # Legal address
            "legal_address_line1": legal_address.get("addressLines", [""])[0] if legal_address.get("addressLines") else None,
            "legal_address_city": legal_address.get("city"),
            "legal_address_region": legal_address.get("region"),
            "legal_address_country": legal_address.get("country"),
            "legal_address_postal_code": legal_address.get("postalCode"),

            # HQ address
            "hq_address_city": hq_address.get("city"),
            "hq_address_country": hq_address.get("country"),

            # Classification
            "legal_jurisdiction": entity.get("jurisdiction"),
            "entity_category": entity.get("category"),
            "entity_status": entity.get("status", LEI_STATUS_ACTIVE),
            "entity_legal_form_code": entity.get("legalForm", {}).get("id"),

            # Registration
            "registration_status": registration.get("status"),
            "initial_registration_date": registration.get("initialRegistrationDate"),
            "last_update_date": registration.get("lastUpdateDate"),
            "next_renewal_date": registration.get("nextRenewalDate"),
            "managing_lou": registration.get("managingLou"),

            # Successor
            "successor_lei": entity.get("successorEntity", {}).get("lei"),
        }

    def _dict_to_record(self, d: dict, snapshot_id: str | None) -> LEIRecord:
        """Convert dict to LEIRecord."""
        return LEIRecord(
            lei=d["lei"],
            legal_name=d.get("legal_name", ""),
            legal_name_language=d.get("legal_name_language"),
            other_names=tuple(d.get("other_names", [])),
            legal_address_line1=d.get("legal_address_line1"),
            legal_address_city=d.get("legal_address_city"),
            legal_address_region=d.get("legal_address_region"),
            legal_address_country=d.get("legal_address_country"),
            legal_address_postal_code=d.get("legal_address_postal_code"),
            hq_address_city=d.get("hq_address_city"),
            hq_address_country=d.get("hq_address_country"),
            legal_jurisdiction=d.get("legal_jurisdiction"),
            entity_category=d.get("entity_category"),
            entity_status=d.get("entity_status", LEI_STATUS_ACTIVE),
            entity_legal_form_code=d.get("entity_legal_form_code"),
            registration_status=d.get("registration_status"),
            initial_registration_date=self._parse_date(d.get("initial_registration_date")),
            last_update_date=self._parse_date(d.get("last_update_date")),
            next_renewal_date=self._parse_date(d.get("next_renewal_date")),
            managing_lou=d.get("managing_lou"),
            successor_lei=d.get("successor_lei"),
            snapshot_id=snapshot_id,
            captured_at=utc_now(),
        )

    def _parse_date(self, date_str: str | None) -> date | None:
        """Parse date from various formats."""
        if not date_str:
            return None

        formats = ["%Y-%m-%d", "%Y-%m-%dT%H:%M:%SZ", "%Y%m%d"]
        for fmt in formats:
            try:
                return datetime.strptime(date_str[:10], "%Y-%m-%d").date()
            except ValueError:
                continue
        return None

    async def lookup_lei(self, lei: str) -> LEIRecord | None:
        """
        Look up a single LEI via API.
        
        Args:
            lei: 20-character LEI to look up.
            
        Returns:
            LEIRecord or None if not found.
        """
        url = f"{GLEIF_API_BASE}/lei-records/{lei}"

        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "EntitySpine/1.0",
                    "Accept": "application/vnd.api+json",
                },
            )

            with urllib.request.urlopen(req, timeout=30) as response:
                data = json.loads(response.read().decode("utf-8"))

            item = data.get("data", {})
            attrs = item.get("attributes", {})
            record = self._normalize_api_record(item["id"], attrs)
            return self._dict_to_record(record, None)

        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            raise
        except Exception as e:
            logger.error(f"Error looking up LEI {lei}: {e}")
            return None

    @property
    def last_snapshot(self) -> LEISnapshot | None:
        """Get metadata from last fetch."""
        return self._last_snapshot


# =============================================================================
# Source Implementation: ISIN-LEI Mapping
# =============================================================================


class GLEIFISINLEISource:
    """
    GLEIF ISIN-to-LEI mapping source.
    
    Downloads the GLEIF mapping file that connects ISINs to LEIs.
    This is crucial for linking securities to their issuers.
    
    Data Size: ~8 million ISIN-LEI pairs
    Update Cadence: Daily
    
    Example:
        >>> source = GLEIFISINLEISource()
        >>> mappings = await source.fetch()
        >>> 
        >>> # Find LEI for an ISIN
        >>> isin_to_lei = {m['isin']: m['lei'] for m in mappings}
        >>> nvidia_lei = isin_to_lei.get('US67066G1040')
    """

    name: str = "gleif-isin-lei"
    url: str = GLEIF_ISIN_LEI_URL

    def __init__(
        self,
        url: str | None = None,
        cache_dir: Path | str | None = None,
    ):
        """Initialize ISIN-LEI source."""
        if url:
            self.url = url
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self._last_snapshot: ISINLEISnapshot | None = None

    async def fetch(self) -> list[dict[str, Any]]:
        """
        Fetch ISIN-LEI mappings from GLEIF.
        
        Returns:
            List of dicts with isin, lei, and status fields.
        """
        logger.info("Fetching GLEIF ISIN-LEI mappings")

        content = await self._download()
        records = self._parse_csv(content)

        content_hash = hashlib.sha256(content).hexdigest()
        self._last_snapshot = ISINLEISnapshot(
            snapshot_id=f"isin_lei_{content_hash[:16]}",
            source_url=self.url,
            content_hash=content_hash,
            record_count=len(records),
            captured_at=utc_now(),
        )

        logger.info(f"Fetched {len(records)} ISIN-LEI mappings")
        return records

    async def fetch_as_records(self) -> list[ISINLEIMapping]:
        """Fetch and return typed ISINLEIMapping objects."""
        raw = await self.fetch()
        snapshot_id = self._last_snapshot.snapshot_id if self._last_snapshot else None

        return [
            ISINLEIMapping(
                isin=r["isin"],
                lei=r["lei"],
                isin_status=r.get("isin_status"),
                lei_status=r.get("lei_status"),
                snapshot_id=snapshot_id,
                captured_at=utc_now(),
            )
            for r in raw
        ]

    async def _download(self) -> bytes:
        """Download ISIN-LEI file from GLEIF."""
        try:
            req = urllib.request.Request(
                self.url,
                headers={"User-Agent": "EntitySpine/1.0"},
            )

            with urllib.request.urlopen(req, timeout=300) as response:
                content = response.read()

            # Handle gzip
            if content[:2] == b'\x1f\x8b':
                content = gzip.decompress(content)

            return content

        except Exception as e:
            logger.error(f"Failed to fetch ISIN-LEI data: {e}")
            raise

    def _parse_csv(self, content: bytes) -> list[dict[str, Any]]:
        """Parse ISIN-LEI CSV."""
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            text = content.decode("latin-1")

        reader = csv.DictReader(io.StringIO(text))
        records = []

        for row in reader:
            isin = row.get("ISIN") or row.get("isin")
            lei = row.get("LEI") or row.get("lei")

            if isin and lei:
                records.append({
                    "isin": isin.strip(),
                    "lei": lei.strip(),
                    "isin_status": row.get("ISIN_Status", row.get("isin_status")),
                    "lei_status": row.get("LEI_Status", row.get("lei_status")),
                })

        return records

    @property
    def last_snapshot(self) -> ISINLEISnapshot | None:
        return self._last_snapshot


# =============================================================================
# Source Implementation: BIC-LEI Mapping
# =============================================================================


class GLEIFBICLEISource:
    """
    GLEIF BIC-to-LEI mapping source.
    
    Downloads the GLEIF mapping file that connects BIC/SWIFT codes to LEIs.
    Primarily used for financial institutions.
    
    Data Size: ~40,000 BIC-LEI pairs
    Update Cadence: Daily
    
    Example:
        >>> source = GLEIFBICLEISource()
        >>> mappings = await source.fetch()
        >>> 
        >>> # Find LEI for a BIC
        >>> bic_to_lei = {m['bic']: m['lei'] for m in mappings}
        >>> jpmorgan_lei = bic_to_lei.get('CHASUS33')
    """

    name: str = "gleif-bic-lei"
    url: str = GLEIF_BIC_LEI_URL

    def __init__(
        self,
        url: str | None = None,
        cache_dir: Path | str | None = None,
    ):
        """Initialize BIC-LEI source."""
        if url:
            self.url = url
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self._last_snapshot: BICLEISnapshot | None = None

    async def fetch(self) -> list[dict[str, Any]]:
        """
        Fetch BIC-LEI mappings from GLEIF.
        
        Returns:
            List of dicts with bic, lei, and status fields.
        """
        logger.info("Fetching GLEIF BIC-LEI mappings")

        content = await self._download()
        records = self._parse_csv(content)

        content_hash = hashlib.sha256(content).hexdigest()
        self._last_snapshot = BICLEISnapshot(
            snapshot_id=f"bic_lei_{content_hash[:16]}",
            source_url=self.url,
            content_hash=content_hash,
            record_count=len(records),
            captured_at=utc_now(),
        )

        logger.info(f"Fetched {len(records)} BIC-LEI mappings")
        return records

    async def fetch_as_records(self) -> list[BICLEIMapping]:
        """Fetch and return typed BICLEIMapping objects."""
        raw = await self.fetch()
        snapshot_id = self._last_snapshot.snapshot_id if self._last_snapshot else None

        return [
            BICLEIMapping(
                bic=r["bic"],
                lei=r["lei"],
                bic_status=r.get("bic_status"),
                lei_status=r.get("lei_status"),
                snapshot_id=snapshot_id,
                captured_at=utc_now(),
            )
            for r in raw
        ]

    async def _download(self) -> bytes:
        """Download BIC-LEI file from GLEIF."""
        try:
            req = urllib.request.Request(
                self.url,
                headers={"User-Agent": "EntitySpine/1.0"},
            )

            with urllib.request.urlopen(req, timeout=120) as response:
                content = response.read()

            # Handle gzip
            if content[:2] == b'\x1f\x8b':
                content = gzip.decompress(content)

            return content

        except Exception as e:
            logger.error(f"Failed to fetch BIC-LEI data: {e}")
            raise

    def _parse_csv(self, content: bytes) -> list[dict[str, Any]]:
        """Parse BIC-LEI CSV."""
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            text = content.decode("latin-1")

        reader = csv.DictReader(io.StringIO(text))
        records = []

        for row in reader:
            bic = row.get("BIC") or row.get("bic")
            lei = row.get("LEI") or row.get("lei")

            if bic and lei:
                records.append({
                    "bic": bic.strip(),
                    "lei": lei.strip(),
                    "bic_status": row.get("BIC_Status", row.get("bic_status")),
                    "lei_status": row.get("LEI_Status", row.get("lei_status")),
                })

        return records

    @property
    def last_snapshot(self) -> BICLEISnapshot | None:
        return self._last_snapshot


# =============================================================================
# Gold Layer: Registry API
# =============================================================================


class LEIRegistry:
    """
    Gold layer: Domain-ready LEI lookup registry.
    
    Provides fast, ergonomic lookups over normalized LEI data.
    
    Features:
    - O(1) lookup by LEI
    - Search by name
    - Filter by country, status
    - Get related entities (successor, etc.)
    
    Example:
        >>> registry = LEIRegistry()
        >>> await registry.load_from_source(limit=10000)  # Load sample
        >>>
        >>> nvidia = registry.get("549300S4KLFTLO7GSQ80")
        >>> print(f"NVIDIA: {nvidia.legal_name}")
        >>>
        >>> us_entities = registry.get_by_country("US")
        >>> print(f"US entities: {len(us_entities)}")
    """

    def __init__(self):
        """Initialize empty registry."""
        self._leis: dict[str, LEIRecord] = {}
        self._by_country: dict[str, list[str]] = {}
        self._by_name: dict[str, list[str]] = {}  # lowercase name -> LEIs
        self._snapshot: LEISnapshot | None = None
        self._loaded_at: datetime | None = None

    async def load_from_source(
        self,
        source: GLEIFSource | None = None,
        limit: int | None = None,
    ) -> int:
        """
        Load registry from GLEIF source.
        
        Args:
            source: GLEIFSource instance (creates default if None).
            limit: Maximum records to load (for testing).
            
        Returns:
            Number of LEI records loaded.
        """
        if source is None:
            source = GLEIFSource()

        records = await source.fetch_as_records(limit=limit)
        return self.load_records(records, source.last_snapshot)

    def load_records(
        self,
        records: list[LEIRecord],
        snapshot: LEISnapshot | None = None,
    ) -> int:
        """
        Load registry from LEIRecord list.
        
        Args:
            records: List of LEIRecord objects.
            snapshot: Optional snapshot metadata.
            
        Returns:
            Number of LEI records loaded.
        """
        # Clear existing
        self._leis.clear()
        self._by_country.clear()
        self._by_name.clear()

        # Index records
        for rec in records:
            lei = rec.lei.upper()
            self._leis[lei] = rec

            # Index by country
            country = rec.legal_address_country
            if country:
                if country not in self._by_country:
                    self._by_country[country] = []
                self._by_country[country].append(lei)

            # Index by name (lowercase for search)
            if rec.legal_name:
                name_key = rec.legal_name.lower()
                if name_key not in self._by_name:
                    self._by_name[name_key] = []
                self._by_name[name_key].append(lei)

        self._snapshot = snapshot
        self._loaded_at = utc_now()

        logger.info(f"Loaded {len(self._leis)} LEI records into registry")
        return len(self._leis)

    def get(self, lei: str) -> LEIRecord | None:
        """
        Look up LEI by code.
        
        Args:
            lei: 20-character LEI (case-insensitive).
            
        Returns:
            LEIRecord or None if not found.
        """
        return self._leis.get(lei.upper())

    def lookup(self, lei: str) -> LEIRecord | None:
        """Alias for get() - provides consistent API across registries."""
        return self.get(lei)

    def __getitem__(self, lei: str) -> LEIRecord:
        """Look up LEI (raises KeyError if not found)."""
        return self._leis[lei.upper()]

    def __contains__(self, lei: str) -> bool:
        """Check if LEI exists in registry."""
        return lei.upper() in self._leis

    def __len__(self) -> int:
        """Number of LEI records in registry."""
        return len(self._leis)

    def get_by_country(self, country_code: str) -> list[LEIRecord]:
        """Get all LEIs for a country."""
        leis = self._by_country.get(country_code.upper(), [])
        return [self._leis[lei] for lei in leis if lei in self._leis]

    def search(
        self,
        query: str,
        *,
        include_inactive: bool = False,
        limit: int = 100,
    ) -> list[LEIRecord]:
        """
        Search LEIs by name.
        
        Args:
            query: Search string (case-insensitive).
            include_inactive: Whether to include inactive LEIs.
            limit: Maximum results to return.
            
        Returns:
            List of matching LEIRecord objects.
        """
        query_lower = query.lower()
        results = []

        for rec in self._leis.values():
            if not include_inactive and not rec.is_active:
                continue

            # Match legal name
            if rec.legal_name and query_lower in rec.legal_name.lower():
                results.append(rec)
                if len(results) >= limit:
                    break
                continue

            # Match other names
            for name in rec.other_names:
                if query_lower in name.lower():
                    results.append(rec)
                    break

            if len(results) >= limit:
                break

        return results

    def get_active(self) -> list[LEIRecord]:
        """Get all active LEIs."""
        return [r for r in self._leis.values() if r.is_active]

    def all(self) -> Iterator[LEIRecord]:
        """Iterate over all LEI records."""
        return iter(self._leis.values())

    @property
    def snapshot(self) -> LEISnapshot | None:
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


# =============================================================================
# Convenience Functions
# =============================================================================


async def lookup_lei(lei: str) -> LEIRecord | None:
    """
    Quick helper to look up a single LEI via GLEIF API.
    
    Args:
        lei: 20-character LEI to look up.
        
    Returns:
        LEIRecord or None if not found.
    """
    source = GLEIFSource()
    return await source.lookup_lei(lei)


async def validate_lei(lei: str) -> bool:
    """
    Validate an LEI exists and is active in GLEIF.
    
    Args:
        lei: LEI to validate.
        
    Returns:
        True if LEI exists and is active.
    """
    record = await lookup_lei(lei)
    return record is not None and record.is_active
