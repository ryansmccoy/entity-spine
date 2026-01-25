"""
EntitySpine Data Loaders - Bulk data ingestion from vendor sources.

Supports:
- FactSet fundamentals CSV/Parquet
- Thomson Reuters OpenPermID (TTL/NTriples)
- Bloomberg reference data
- SEC EDGAR company data (auto-loading)

Usage:
    from entityspine.loaders import FactSetLoader, ThomsonLoader, BloombergLoader
    
    loader = FactSetLoader(store)
    loader.load_from_csv("path/to/ff_combined.csv")
    
    # SEC auto-loading
    from entityspine.loaders import SecDataLoader
    
    loader = SecDataLoader(store)
    loader.ensure_loaded()  # Downloads if needed, uses cache otherwise
"""

from entityspine.loaders.base import DataLoader, LoadStats
from entityspine.loaders.factset import FactSetLoader
from entityspine.loaders.thomson import ThomsonLoader
from entityspine.loaders.bloomberg import BloombergLoader
from entityspine.loaders.sec_loader import (
    AutoLoadMixin,
    SecDataLoader,
    clear_sec_cache,
    get_sec_cache_status,
)

__all__ = [
    "DataLoader",
    "LoadStats",
    "FactSetLoader",
    "ThomsonLoader",
    "BloombergLoader",
    # SEC auto-loading
    "SecDataLoader",
    "AutoLoadMixin",
    "get_sec_cache_status",
    "clear_sec_cache",
]
