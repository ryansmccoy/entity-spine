"""
Bloomberg data loader for EntitySpine.

Loads Bloomberg reference data from various file formats:
- Common Stock/Equity files (pipe-delimited)
- BBUID (Bloomberg Unique ID) files
- Financial statements

Folder structure expected:
    G:/BLOOMBERG/
        Equity_Common_Stock_20160530/   <- Contains equity data
        bbuid/                          <- Bloomberg UIDs
        INCOME_STATEMENT/
        BALANCE_SHEET/
        CASH_FLOW/
"""

from __future__ import annotations

import csv
import logging
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


# Bloomberg field mappings for equity files
BLOOMBERG_EQUITY_FIELDS = {
    "NAME": "primary_name",
    "ID_BB_GLOBAL": "figi",
    "ID_BB_UNIQUE": "bbuid",
    "ID_BB_SEC_NUM_DES": "ticker",
    "EXCH_CODE": "exchange",
    "FEED_SOURCE": "mic",
    "CNTRY_OF_DOMICILE": "jurisdiction",
    "INDUSTRY_SECTOR": "sector",
    "INDUSTRY_GROUP": "industry_group",
    "INDUSTRY_SUBGROUP": "industry_subgroup",
    "SECURITY_TYP": "security_type",
    "EQY_PRIM_EXCH": "primary_exchange",
    "TICKER": "short_ticker",
}


class BloombergLoader(DataLoader):
    """
    Load Bloomberg reference data.
    
    Example:
        loader = BloombergLoader(store)
        stats = loader.load("G:/BLOOMBERG/Equity_Common_Stock_20160530")
    """
    
    def load(
        self,
        source: str | Path,
        limit: int | None = None,
        create_securities: bool = True,
        create_listings: bool = True,
    ) -> LoadStats:
        """
        Load Bloomberg data from directory or file.
        
        Args:
            source: Path to Bloomberg data directory or file
            limit: Maximum records to load (for testing)
            create_securities: Whether to create security records
            create_listings: Whether to create listing records
            
        Returns:
            LoadStats with results
        """
        source = Path(source)
        self.stats = LoadStats(source=str(source))
        
        logger.info(f"Loading Bloomberg data from {source}")
        
        if source.is_dir():
            # Load all txt files in directory
            files = list(source.glob("*.txt"))
            if not files:
                files = list(source.glob("*.csv"))
            
            for f in files:
                self._load_file(f, limit, create_securities, create_listings)
        else:
            self._load_file(source, limit, create_securities, create_listings)
        
        # Flush remaining batches
        self._flush_batches()
        self.store._conn.commit()
        
        self.stats.finish()
        logger.info(f"Completed: {self.stats}")
        
        return self.stats
    
    def _load_file(
        self,
        path: Path,
        limit: int | None,
        create_securities: bool,
        create_listings: bool,
    ) -> None:
        """Load a single Bloomberg file."""
        logger.info(f"Loading {path.name}")
        
        # Detect delimiter
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            first_line = f.readline()
            delimiter = "|" if "|" in first_line else ","
        
        # Read file
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f, delimiter=delimiter)
            
            for idx, row in enumerate(reader):
                if limit and self.stats.entities_loaded >= limit:
                    break
                
                try:
                    self._process_row(row, create_securities, create_listings)
                except Exception as e:
                    self.stats.errors += 1
                    if self.stats.errors < 10:
                        logger.warning(f"Error processing row {idx}: {e}")
                
                if idx > 0 and idx % 50000 == 0:
                    self._log_progress(f"Processing {path.name}")
    
    def _process_row(
        self,
        row: dict,
        create_securities: bool,
        create_listings: bool,
    ) -> None:
        """Process a single Bloomberg row."""
        # Get entity name
        name = row.get("NAME", "").strip()
        if not name:
            self.stats.entities_skipped += 1
            return
        
        # Get identifiers
        figi = row.get("ID_BB_GLOBAL", "").strip()
        bbuid = row.get("ID_BB_UNIQUE", "").strip()
        ticker = row.get("ID_BB_SEC_NUM_DES", "").strip() or row.get("TICKER", "").strip()
        
        # Need at least one identifier
        if not figi and not bbuid:
            self.stats.entities_skipped += 1
            return
        
        # Determine entity ID (prefer FIGI for global uniqueness)
        if figi:
            entity_id = f"figi:{figi}"
        else:
            entity_id = f"bbuid:{bbuid}"
        
        # Get jurisdiction
        jurisdiction = row.get("CNTRY_OF_DOMICILE", "").strip()
        if jurisdiction and len(jurisdiction) > 2:
            jurisdiction = jurisdiction[:2].upper()
        elif not jurisdiction:
            jurisdiction = None
        
        # Create entity
        entity = Entity(
            entity_id=entity_id,
            primary_name=name,
            entity_type=EntityType.ORGANIZATION,
            status=EntityStatus.ACTIVE,
            jurisdiction=jurisdiction,
            source_system="bloomberg",
            source_id=figi or bbuid,
        )
        
        self._add_entity(entity)
        
        # Create identifier claims (FIGI is security-scoped, so only add to security below)
        # Add BBUID as entity-level identifier
        if bbuid:
            claim = IdentifierClaim(
                entity_id=entity_id,
                scheme=IdentifierScheme.INTERNAL,
                value=bbuid,
                namespace=VendorNamespace.BLOOMBERG,
                source="bloomberg_equity",
            )
            self._add_claim(claim)
        
        # Create security
        if create_securities:
            security_id = f"sec:{figi or bbuid}"
            
            # Determine security type
            sec_type_str = row.get("SECURITY_TYP", "").upper()
            if "PREF" in sec_type_str:
                security_type = SecurityType.PREFERRED_STOCK
            elif "ADR" in sec_type_str or "GDR" in sec_type_str:
                security_type = SecurityType.DEPOSITARY_RECEIPT
            elif "ETF" in sec_type_str or "ETP" in sec_type_str:
                security_type = SecurityType.ETF
            elif "UNIT" in sec_type_str:
                security_type = SecurityType.UNIT
            elif "RIGHT" in sec_type_str:
                security_type = SecurityType.RIGHT
            elif "WARRANT" in sec_type_str:
                security_type = SecurityType.WARRANT
            else:
                security_type = SecurityType.COMMON_STOCK
            
            security = Security(
                security_id=security_id,
                entity_id=entity_id,
                security_type=security_type,
                status=SecurityStatus.ACTIVE,
                description=name,
                source_system="bloomberg",
            )
            
            self._add_security(security)
            
            # Add FIGI claim to security (proper scope)
            if figi:
                sec_claim = IdentifierClaim(
                    security_id=security_id,
                    scheme=IdentifierScheme.FIGI,
                    value=figi,
                    namespace=VendorNamespace.BLOOMBERG,
                    source="bloomberg_equity",
                )
                self._add_claim(sec_claim)
        
        # Create listing
        if create_listings and ticker:
            exchange = row.get("EXCH_CODE", "").strip() or row.get("EQY_PRIM_EXCH", "").strip()
            mic = row.get("FEED_SOURCE", "").strip()
            
            if not exchange:
                exchange = "UNKNOWN"
            
            # MIC must be 4 uppercase letters, otherwise skip it
            if mic and (len(mic) != 4 or not mic.isalpha()):
                mic = None
            elif mic:
                mic = mic.upper()
            
            listing_id = f"lst:{ticker}:{exchange}"
            
            listing = Listing(
                listing_id=listing_id,
                security_id=security_id if create_securities else f"sec:{figi or bbuid}",
                ticker=ticker,
                exchange=exchange,
                mic=mic if mic else None,
                status=ListingStatus.ACTIVE,
                is_primary=True,
                source_system="bloomberg",
            )
            
            self._add_listing(listing)
    
    def load_bbuid(self, source: str | Path, limit: int | None = None) -> LoadStats:
        """
        Load Bloomberg UID mapping file.
        
        Args:
            source: Path to BBUID directory or file
            limit: Maximum records to load
            
        Returns:
            LoadStats with results
        """
        source = Path(source)
        self.stats = LoadStats(source=str(source))
        
        logger.info(f"Loading BBUID data from {source}")
        
        # Load as regular file
        return self.load(source, limit=limit, create_securities=False, create_listings=False)
