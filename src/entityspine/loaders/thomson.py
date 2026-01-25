"""
Thomson Reuters OpenPermID data loader for EntitySpine.

Loads data from TTL (Turtle) or NTriples files.
Supports:
- Organizations (main entity data)
- Instruments (securities)
- Quotes (listings with tickers)
- Persons (directors/officers - optional)
"""

from __future__ import annotations

import gzip
import logging
import re
from pathlib import Path
from typing import Iterator

from entityspine.domain import (
    Entity,
    EntityStatus,
    EntityType,
    IdentifierClaim,
    IdentifierScheme,
    Listing,
    ListingStatus,
    Security,
    SecurityStatus,
    SecurityType,
    VendorNamespace,
)
from entityspine.loaders.base import DataLoader, LoadStats

logger = logging.getLogger(__name__)


# PermID TTL predicate patterns
PERMID_PATTERNS = {
    "permid": re.compile(r'tr-common:hasPermId\s+"(\d+)"'),
    "name": re.compile(r'vcard:organization-name\s+"([^"]+)"'),
    "hq_address": re.compile(r'mdaas:HeadquartersAddress\s+"([^"]+)"'),
    "domicile": re.compile(r'isDomiciledIn\s+<http://sws\.geonames\.org/(\d+)'),
    "status_active": re.compile(r'hasActivityStatus\s+tr-org:statusActive'),
    "status_inactive": re.compile(r'hasActivityStatus\s+tr-org:statusInactive'),
    "lei": re.compile(r'tr-org:hasLEI\s+"([A-Z0-9]{20})"'),
    "primary_instrument": re.compile(r'tr-fin:hasPrimaryInstrument\s+<https://permid\.org/1-(\d+)>'),
    "website": re.compile(r'vcard:hasURL\s+<([^>]+)>'),
}

INSTRUMENT_PATTERNS = {
    "permid": re.compile(r'tr-common:hasPermId\s+"(\d+)"'),
    "name": re.compile(r'tr-common:hasName\s+"([^"]+)"'),
    "asset_class": re.compile(r'hasAssetClass\s+<https://permid\.org/1-(\d+)>'),
    "issuer": re.compile(r'isIssuedBy\s+<https://permid\.org/1-(\d+)>'),
    "primary_quote": re.compile(r'hasPrimaryQuote\s+<https://permid\.org/1-(\d+)>'),
    "status_active": re.compile(r'instrumentStatusActive'),
    "status_inactive": re.compile(r'instrumentStatusInActive'),
}

QUOTE_PATTERNS = {
    "permid": re.compile(r'tr-common:hasPermId\s+"(\d+)"'),
    "name": re.compile(r'tr-common:hasName\s+"([^"]+)"'),
    "ticker": re.compile(r'hasExchangeTicker\s+"([^"]+)"'),
    "exchange": re.compile(r'hasExchangeCode\s+"([^"]+)"'),
    "mic": re.compile(r'hasMic\s+"([^"]+)"'),
    "ric": re.compile(r'hasRic\s+"([^"]+)"'),
    "instrument": re.compile(r'isQuoteOf\s+<https://permid\.org/1-(\d+)>'),
}

# GeoNames ID to ISO country code mapping (common ones)
GEONAMES_TO_ISO = {
    "6252001": "US",  # United States
    "2635167": "GB",  # United Kingdom
    "6251999": "CA",  # Canada
    "2921044": "DE",  # Germany
    "3017382": "FR",  # France
    "1861060": "JP",  # Japan
    "2077456": "AU",  # Australia
    "1814991": "CN",  # China
    "1269750": "IN",  # India
    "3469034": "BR",  # Brazil
    "2750405": "NL",  # Netherlands
    "2658434": "CH",  # Switzerland
    "3175395": "IT",  # Italy
    "2510769": "ES",  # Spain
    "1835841": "KR",  # South Korea
    "1668284": "TW",  # Taiwan
    "1880251": "SG",  # Singapore
    "1819730": "HK",  # Hong Kong
    "2802361": "BE",  # Belgium
    "2661886": "SE",  # Sweden
}


class ThomsonLoader(DataLoader):
    """
    Load Thomson Reuters OpenPermID data.
    
    Example:
        loader = ThomsonLoader(store)
        stats = loader.load("G:/THOMSON")  # Load all files in directory
        # Or load specific file:
        stats = loader.load("G:/THOMSON/OpenPermID-bulk-organization-20200830_084424.ttl.gz")
    """
    
    def load(
        self,
        source: str | Path,
        limit: int | None = None,
        file_types: list[str] | None = None,
    ) -> LoadStats:
        """
        Load Thomson data from TTL/NTriples files.
        
        Args:
            source: Path to file or directory
            limit: Maximum entities to load (for testing)
            file_types: List of file types to load: ['organization', 'instrument', 'quote']
                       If None, loads organization only
            
        Returns:
            LoadStats with results
        """
        source = Path(source)
        self.stats = LoadStats(source=str(source))
        
        if file_types is None:
            file_types = ["organization"]
        
        logger.info(f"Loading Thomson data from {source}")
        
        if source.is_dir():
            # Load all matching files in directory
            for file_type in file_types:
                pattern = f"*-{file_type}-*.ttl.gz"
                files = sorted(source.glob(pattern))
                if not files:
                    pattern = f"*-{file_type}-*.ntriples.gz"
                    files = sorted(source.glob(pattern))
                
                for f in files:
                    logger.info(f"Loading {file_type} from {f.name}")
                    if file_type == "organization":
                        self._load_organizations(f, limit)
                    elif file_type == "instrument":
                        self._load_instruments(f, limit)
                    elif file_type == "quote":
                        self._load_quotes(f, limit)
        else:
            # Single file
            fname = source.name.lower()
            if "organization" in fname:
                self._load_organizations(source, limit)
            elif "instrument" in fname:
                self._load_instruments(source, limit)
            elif "quote" in fname:
                self._load_quotes(source, limit)
        
        # Flush remaining batches
        self._flush_batches()
        self.store._conn.commit()
        
        self.stats.finish()
        logger.info(f"Completed: {self.stats}")
        
        return self.stats
    
    def _load_organizations(self, path: Path, limit: int | None) -> None:
        """Load organization records from TTL file."""
        for record in self._parse_ttl_records(path, "tr-org:Organization"):
            if limit and self.stats.entities_loaded >= limit:
                break
            
            try:
                entity = self._parse_organization(record)
                if entity:
                    self._add_entity(entity)
                    
                    # Add PermID claim (using INTERNAL scheme since PERMID not defined)
                    permid = PERMID_PATTERNS["permid"].search(record)
                    if permid:
                        claim = IdentifierClaim(
                            entity_id=entity.entity_id,
                            scheme=IdentifierScheme.INTERNAL,
                            value=f"permid:{permid.group(1)}",
                            namespace=VendorNamespace.REUTERS,
                            source="openpermid_bulk",
                        )
                        self._add_claim(claim)
                    
                    # Extract LEI if present
                    lei = PERMID_PATTERNS["lei"].search(record)
                    if lei:
                        lei_claim = IdentifierClaim(
                            entity_id=entity.entity_id,
                            scheme=IdentifierScheme.LEI,
                            value=lei.group(1),
                            namespace=VendorNamespace.REUTERS,
                            source="openpermid_bulk",
                        )
                        self._add_claim(lei_claim)
                        
            except Exception as e:
                self.stats.errors += 1
                if self.stats.errors < 10:
                    logger.warning(f"Error parsing organization: {e}")
            
            if self.stats.entities_loaded > 0 and self.stats.entities_loaded % 100000 == 0:
                self._log_progress("Organizations")
    
    def _load_instruments(self, path: Path, limit: int | None) -> None:
        """Load instrument records as securities."""
        for record in self._parse_ttl_records(path, "tr-fin:Instrument"):
            if limit and self.stats.securities_loaded >= limit:
                break
            
            try:
                security = self._parse_instrument(record)
                if security:
                    self._add_security(security)
            except Exception as e:
                self.stats.errors += 1
                if self.stats.errors < 10:
                    logger.warning(f"Error parsing instrument: {e}")
    
    def _load_quotes(self, path: Path, limit: int | None) -> None:
        """Load quote records as listings."""
        for record in self._parse_ttl_records(path, "tr-fin:Quote"):
            if limit and self.stats.listings_loaded >= limit:
                break
            
            try:
                listing = self._parse_quote(record)
                if listing:
                    self._add_listing(listing)
            except Exception as e:
                self.stats.errors += 1
                if self.stats.errors < 10:
                    logger.warning(f"Error parsing quote: {e}")
    
    def _parse_ttl_records(self, path: Path, record_type: str) -> Iterator[str]:
        """
        Parse TTL file and yield records of the given type.
        
        Records are delimited by blank lines in TTL format.
        """
        opener = gzip.open if path.suffix == ".gz" else open
        
        with opener(path, "rt", encoding="utf-8", errors="replace") as f:
            current_record = []
            in_record = False
            
            for line in f:
                line = line.rstrip()
                
                # Skip prefixes
                if line.startswith("@prefix"):
                    continue
                
                # Record start
                if line.startswith("<https://permid.org/"):
                    if current_record:
                        record_text = "\n".join(current_record)
                        if record_type in record_text:
                            yield record_text
                    current_record = [line]
                    in_record = True
                elif in_record:
                    if line:
                        current_record.append(line)
                    elif line == "" and current_record:
                        # End of record
                        record_text = "\n".join(current_record)
                        if record_type in record_text:
                            yield record_text
                        current_record = []
                        in_record = False
            
            # Last record
            if current_record:
                record_text = "\n".join(current_record)
                if record_type in record_text:
                    yield record_text
    
    def _parse_organization(self, record: str) -> Entity | None:
        """Parse organization record into Entity."""
        permid = PERMID_PATTERNS["permid"].search(record)
        name = PERMID_PATTERNS["name"].search(record)
        
        if not permid or not name:
            return None
        
        permid_value = permid.group(1)
        name_value = name.group(1).strip()
        
        if not name_value:
            return None
        
        # Determine status
        status = EntityStatus.ACTIVE
        if PERMID_PATTERNS["status_inactive"].search(record):
            status = EntityStatus.INACTIVE
        
        # Extract jurisdiction from GeoNames
        jurisdiction = None
        domicile = PERMID_PATTERNS["domicile"].search(record)
        if domicile:
            geonames_id = domicile.group(1)
            jurisdiction = GEONAMES_TO_ISO.get(geonames_id)
        
        return Entity(
            entity_id=f"permid:{permid_value}",
            primary_name=name_value,
            entity_type=EntityType.ORGANIZATION,
            status=status,
            jurisdiction=jurisdiction,
            source_system="openpermid",
            source_id=permid_value,
        )
    
    def _parse_instrument(self, record: str) -> Security | None:
        """Parse instrument record into Security."""
        permid = INSTRUMENT_PATTERNS["permid"].search(record)
        name = INSTRUMENT_PATTERNS["name"].search(record)
        issuer = INSTRUMENT_PATTERNS["issuer"].search(record)
        
        if not permid:
            return None
        
        permid_value = permid.group(1)
        name_value = name.group(1).strip() if name else ""
        
        # Map issuer to entity_id
        entity_id = None
        if issuer:
            entity_id = f"permid:{issuer.group(1)}"
        
        if not entity_id:
            return None
        
        # Determine status
        status = SecurityStatus.ACTIVE
        if INSTRUMENT_PATTERNS["status_inactive"].search(record):
            status = SecurityStatus.INACTIVE
        
        return Security(
            security_id=f"permid:{permid_value}",
            entity_id=entity_id,
            security_type=SecurityType.COMMON_STOCK,  # Default
            status=status,
            description=name_value,
            source_system="openpermid",
        )
    
    def _parse_quote(self, record: str) -> Listing | None:
        """Parse quote record into Listing."""
        permid = QUOTE_PATTERNS["permid"].search(record)
        ticker = QUOTE_PATTERNS["ticker"].search(record)
        exchange = QUOTE_PATTERNS["exchange"].search(record)
        instrument = QUOTE_PATTERNS["instrument"].search(record)
        mic = QUOTE_PATTERNS["mic"].search(record)
        
        if not permid or not ticker or not exchange or not instrument:
            return None
        
        permid_value = permid.group(1)
        ticker_value = ticker.group(1).strip()
        exchange_value = exchange.group(1).strip()
        security_id = f"permid:{instrument.group(1)}"
        mic_value = mic.group(1) if mic else None
        
        return Listing(
            listing_id=f"permid:{permid_value}",
            security_id=security_id,
            ticker=ticker_value,
            exchange=exchange_value,
            mic=mic_value,
            status=ListingStatus.ACTIVE,
            is_primary=False,
            source_system="openpermid",
        )
