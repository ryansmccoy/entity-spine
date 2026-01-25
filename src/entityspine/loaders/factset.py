"""
FactSet data loader for EntitySpine.

Loads FactSet fundamentals data from CSV or Parquet files.
Creates entities with financial observations.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Iterator

from entityspine.domain import (
    Entity,
    EntityStatus,
    EntityType,
    IdentifierClaim,
    IdentifierScheme,
    VendorNamespace,
)
from entityspine.loaders.base import DataLoader, LoadStats

if TYPE_CHECKING:
    import pandas as pd

logger = logging.getLogger(__name__)


# FactSet column mappings
FACTSET_ENTITY_COLS = {
    "Identifier": "source_id",
    "Name": "primary_name",
    "Country": "jurisdiction",
    "Company Type": "company_type",
    "Year Founded": "year_founded",
    "Number of Employees": "employees",
    "Primary SIC Industry": "sic_industry",
}

FACTSET_FINANCIAL_COLS = [
    "Revenue", "COGS", "Gross Profit", "EBIT", "EBITDA", "Net Income",
    "Total Assets", "Total Debt", "Market Cap", "Enterprise Value",
    "Free Cash Flow", "Capital Expenditures",
]


class FactSetLoader(DataLoader):
    """
    Load FactSet fundamentals data.
    
    Example:
        loader = FactSetLoader(store)
        stats = loader.load("G:/FACTSET/ff_combined.csv")
        print(stats)
    """
    
    def load(
        self,
        source: str | Path,
        limit: int | None = None,
        create_claims: bool = True,
    ) -> LoadStats:
        """
        Load FactSet data from CSV or Parquet.
        
        Args:
            source: Path to CSV or Parquet file
            limit: Maximum records to load (for testing)
            create_claims: Whether to create identifier claims
            
        Returns:
            LoadStats with results
        """
        source = Path(source)
        self.stats = LoadStats(source=str(source))
        
        logger.info(f"Loading FactSet data from {source}")
        
        try:
            import pandas as pd
        except ImportError:
            raise ImportError("pandas is required for FactSet loader")
        
        # Load data
        if source.suffix == ".parquet":
            df = pd.read_parquet(source)
        else:
            df = pd.read_csv(
                source,
                encoding="utf-8",
                encoding_errors="replace",
                low_memory=False,
            )
        
        if limit:
            df = df.head(limit)
        
        logger.info(f"Loaded {len(df):,} rows from {source.name}")
        
        # Process rows
        for idx, row in df.iterrows():
            try:
                self._process_row(row, create_claims)
            except Exception as e:
                self.stats.errors += 1
                if self.stats.errors < 10:
                    logger.warning(f"Error processing row {idx}: {e}")
            
            # Progress logging
            if self.stats.entities_loaded > 0 and self.stats.entities_loaded % 50000 == 0:
                self._log_progress(f"Processed {self.stats.entities_loaded:,}")
        
        # Flush remaining batches
        self._flush_batches()
        self.store._conn.commit()
        
        self.stats.finish()
        logger.info(f"Completed: {self.stats}")
        
        return self.stats
    
    def _process_row(self, row: "pd.Series", create_claims: bool) -> None:
        """Process a single FactSet row."""
        identifier = str(row.get("Identifier", "")).strip()
        name = str(row.get("Name", "")).strip()
        
        # Skip invalid rows
        if not identifier or not name or identifier == "nan" or name == "nan":
            self.stats.entities_skipped += 1
            return
        
        # Derive entity type
        company_type = str(row.get("Company Type", "")).lower()
        if "fund" in company_type:
            entity_type = EntityType.FUND
        elif "trust" in company_type:
            entity_type = EntityType.TRUST
        elif "partnership" in company_type:
            entity_type = EntityType.PARTNERSHIP
        else:
            entity_type = EntityType.ORGANIZATION
        
        # Extract jurisdiction (first 2 chars of country)
        country = str(row.get("Country", "")).strip()
        jurisdiction = None
        if country and country != "nan":
            if len(country) == 2:
                jurisdiction = country.upper()
            elif len(country) > 2:
                # Map common names
                country_map = {
                    "united states": "US",
                    "united kingdom": "GB",
                    "canada": "CA",
                    "germany": "DE",
                    "france": "FR",
                    "japan": "JP",
                    "australia": "AU",
                    "china": "CN",
                    "india": "IN",
                    "brazil": "BR",
                }
                jurisdiction = country_map.get(country.lower(), country[:2].upper())
        
        # Extract SIC code
        sic = str(row.get("Primary SIC Industry", "")).strip()
        sic_code = None
        if sic and sic != "nan":
            parts = sic.split()
            if parts and parts[0].isdigit():
                sic_code = parts[0]
        
        # Create entity
        entity_id = f"factset:{identifier}"
        entity = Entity(
            entity_id=entity_id,
            primary_name=name,
            entity_type=entity_type,
            status=EntityStatus.ACTIVE,
            jurisdiction=jurisdiction,
            sic_code=sic_code,
            source_system="factset",
            source_id=identifier,
        )
        
        self._add_entity(entity)
        
        # Create identifier claim
        if create_claims:
            claim = IdentifierClaim(
                entity_id=entity_id,
                scheme=IdentifierScheme.INTERNAL,
                value=identifier,
                namespace=VendorNamespace.FACTSET,
                source="factset_fundamentals",
            )
            self._add_claim(claim)
    
    def load_to_parquet(
        self,
        source: str | Path,
        output_dir: str | Path,
    ) -> dict[str, Path]:
        """
        Convert FactSet CSV to logical Parquet files.
        
        Args:
            source: Path to source CSV
            output_dir: Directory to write Parquet files
            
        Returns:
            Dict mapping logical name to output path
        """
        import pandas as pd
        
        source = Path(source)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Converting {source} to Parquet in {output_dir}")
        
        # Read CSV
        df = pd.read_csv(
            source,
            encoding="utf-8",
            encoding_errors="replace",
            low_memory=False,
        )
        df.columns = df.columns.str.strip()
        
        # Column groupings
        groupings = {
            "entities": [
                "Identifier", "Name", "Country", "City", "State/Province",
                "Company Type", "Year Founded", "Number of Employees",
                "Ultimate Parent Name", "Ultimate Parent Type",
            ],
            "identifiers": [
                "Identifier", "Name", "Stock Exchange",
                "Primary SIC Industry", "Primary SIC Industry Group",
                "Primary SIC Major Group", "Primary NAICS Industry",
                "FactSet Industry", "FactSet Sector",
            ],
            "financials": [
                "Identifier", "Name", "Revenue", "COGS", "Gross Profit",
                "EBIT", "EBITDA", "Net Income", "Pretax Income",
                "Total Assets", "Total Current Assets", "Total Current Liabilities",
                "Total Debt", "Long Term Debt", "Short Term Debt",
                "Cash & ST Investments", "Market Cap", "Enterprise Value",
                "Capital Expenditures", "Free Cash Flow", "Net Operating Cash Flow",
            ],
            "ratios": [
                "Identifier", "Name",
                "Gross Income Margin", "EBIT Margin", "EBITDA Margin",
                "Net Income Margin", "Return on Assets", "Return on Equity",
                "Price to Earnings", "Price to Book Value", "Price to Sales",
                "Enterprise Value to EBIT", "Enterprise Value to EBITDA",
            ],
            "metadata": [
                "Identifier", "Name", "Website", "Business Description",
                "Telephone Number", "Fiscal Year End",
            ],
        }
        
        available = set(df.columns)
        outputs = {}
        
        for name, cols in groupings.items():
            valid_cols = [c for c in cols if c in available]
            if not valid_cols:
                continue
            
            subset = df[valid_cols].copy()
            
            # Convert to string to avoid type issues
            for col in subset.columns:
                if subset[col].dtype == "object":
                    subset[col] = subset[col].astype(str).replace("nan", "")
            
            output_path = output_dir / f"{name}.parquet"
            subset.to_parquet(output_path, index=False, compression="snappy")
            outputs[name] = output_path
            
            logger.info(f"  {name}.parquet: {len(valid_cols)} cols, "
                       f"{output_path.stat().st_size / 1024 / 1024:.1f} MB")
        
        # Also save full dataset
        full_path = output_dir / "full.parquet"
        df_str = df.astype(str).replace("nan", "")
        df_str.to_parquet(full_path, index=False, compression="snappy")
        outputs["full"] = full_path
        
        return outputs
