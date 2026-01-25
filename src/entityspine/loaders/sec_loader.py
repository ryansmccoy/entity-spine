"""
SEC Data Auto-Loader for EntitySpine.

Provides automatic SEC data loading with caching support.

This module enables lazy-loading of SEC entity data the first time
a query is made, rather than requiring explicit `load_sec_data()` calls.

Usage:
    # In SqliteStore with auto_load_sec enabled:
    store = SqliteStore("entities.db", auto_load_sec=True)
    
    # Data loads automatically on first query
    entities = store.search("APPLE")  # Triggers auto-load
    
    # Or use the helper directly:
    from entityspine.loaders.sec_loader import SecDataLoader
    
    loader = SecDataLoader(store, cache_dir="~/.entityspine/cache")
    loader.ensure_loaded()
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


SEC_COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
DEFAULT_CACHE_DIR = Path.home() / ".entityspine" / "cache"
CACHE_MAX_AGE_HOURS = 24


@runtime_checkable
class SecLoadable(Protocol):
    """Protocol for stores that can load SEC data."""

    def load_sec_json(self, data: dict) -> int:
        """Load SEC JSON data into the store."""
        ...

    def count_entities(self) -> int:
        """Return the count of entities in the store."""
        ...


class SecDataLoader:
    """
    SEC data loader with caching support.
    
    Features:
    - Downloads company_tickers.json from SEC
    - Caches locally to avoid repeated downloads
    - Respects cache expiry (default 24 hours)
    - Handles gzip-compressed responses
    
    Args:
        store: EntitySpine store to load data into.
        cache_dir: Directory for cached data files.
        cache_max_age_hours: How long to keep cached data (default 24h).
        user_agent: User-Agent for SEC requests.
    
    Example:
        >>> from entityspine import SqliteStore
        >>> from entityspine.loaders.sec_loader import SecDataLoader
        >>> 
        >>> store = SqliteStore(":memory:")
        >>> store.initialize()
        >>> 
        >>> loader = SecDataLoader(store)
        >>> loader.ensure_loaded()
        >>> 
        >>> print(store.count_entities())  # ~14,000 entities
    """

    def __init__(
        self,
        store: SecLoadable,
        cache_dir: str | Path | None = None,
        cache_max_age_hours: float = CACHE_MAX_AGE_HOURS,
        user_agent: str = "EntitySpine/0.3.3 (entityspine@example.com)",
    ) -> None:
        self.store = store
        self.cache_dir = Path(cache_dir) if cache_dir else DEFAULT_CACHE_DIR
        self.cache_max_age_hours = cache_max_age_hours
        self.user_agent = user_agent
        self._loaded = False

    @property
    def cache_file(self) -> Path:
        """Path to the cached SEC data file."""
        return self.cache_dir / "company_tickers.json"

    def _is_cache_valid(self) -> bool:
        """Check if cache file exists and is not expired."""
        if not self.cache_file.exists():
            return False
        
        age_seconds = time.time() - self.cache_file.stat().st_mtime
        age_hours = age_seconds / 3600
        
        return age_hours < self.cache_max_age_hours

    def _fetch_from_sec(self) -> dict:
        """Fetch company data directly from SEC."""
        import gzip
        import urllib.request

        headers = {
            "User-Agent": self.user_agent,
            "Accept-Encoding": "gzip, deflate",
            "Host": "www.sec.gov",
        }

        logger.info(f"Downloading SEC data from {SEC_COMPANY_TICKERS_URL}")
        request = urllib.request.Request(SEC_COMPANY_TICKERS_URL, headers=headers)

        with urllib.request.urlopen(request, timeout=30) as response:
            raw_data = response.read()
            # Handle gzip compression
            if response.headers.get("Content-Encoding") == "gzip" or raw_data[:2] == b"\x1f\x8b":
                raw_data = gzip.decompress(raw_data)
            return json.loads(raw_data.decode("utf-8"))

    def _load_from_cache(self) -> dict:
        """Load data from cache file."""
        logger.debug(f"Loading SEC data from cache: {self.cache_file}")
        with open(self.cache_file, encoding="utf-8") as f:
            return json.load(f)

    def _save_to_cache(self, data: dict) -> None:
        """Save data to cache file."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        logger.debug(f"Saving SEC data to cache: {self.cache_file}")
        with open(self.cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f)

    def load(self, force_refresh: bool = False) -> int:
        """
        Load SEC data into the store.
        
        Args:
            force_refresh: If True, fetch fresh data even if cache is valid.
        
        Returns:
            Number of entities loaded.
        """
        # Try cache first
        if not force_refresh and self._is_cache_valid():
            data = self._load_from_cache()
        else:
            data = self._fetch_from_sec()
            self._save_to_cache(data)
        
        count = self.store.load_sec_json(data)
        self._loaded = True
        logger.info(f"Loaded {count} SEC entities")
        return count

    def ensure_loaded(self) -> None:
        """
        Ensure SEC data is loaded, loading if necessary.
        
        This is idempotent - calling multiple times will only load once.
        """
        # Check if store already has data
        try:
            if self.store.count_entities() > 0:
                self._loaded = True
                return
        except Exception:
            pass
        
        if not self._loaded:
            self.load()

    @property
    def is_loaded(self) -> bool:
        """Whether SEC data has been loaded."""
        return self._loaded


class AutoLoadMixin:
    """
    Mixin to add auto-loading behavior to EntitySpine stores.
    
    Add this mixin to a store class to enable automatic SEC data loading
    on first query. The data is loaded lazily (on first access) rather
    than at initialization time.
    
    Example:
        class MyStore(AutoLoadMixin, SqliteStore):
            pass
        
        store = MyStore("entities.db", auto_load_sec=True)
        # Data loads automatically on first query
        entities = store.search("APPLE")
    """

    _auto_load_sec: bool = False
    _sec_loader: SecDataLoader | None = None
    _auto_loaded: bool = False

    def _ensure_auto_loaded(self) -> None:
        """Ensure SEC data is loaded if auto_load_sec is enabled."""
        if self._auto_load_sec and not self._auto_loaded:
            if self._sec_loader is None:
                # type: ignore - mixin assumes store has load_sec_json
                self._sec_loader = SecDataLoader(self)  
            self._sec_loader.ensure_loaded()
            self._auto_loaded = True


def get_sec_cache_status() -> dict:
    """
    Get status of SEC data cache.
    
    Returns:
        Dictionary with cache status information.
    
    Example:
        >>> status = get_sec_cache_status()
        >>> print(status)
        {'exists': True, 'age_hours': 2.5, 'path': '~/.entityspine/cache/company_tickers.json'}
    """
    cache_file = DEFAULT_CACHE_DIR / "company_tickers.json"
    
    if not cache_file.exists():
        return {
            "exists": False,
            "age_hours": None,
            "path": str(cache_file),
            "size_bytes": None,
        }
    
    stat = cache_file.stat()
    age_seconds = time.time() - stat.st_mtime
    
    return {
        "exists": True,
        "age_hours": age_seconds / 3600,
        "path": str(cache_file),
        "size_bytes": stat.st_size,
    }


def clear_sec_cache() -> bool:
    """
    Clear the SEC data cache.
    
    Returns:
        True if cache was cleared, False if no cache existed.
    """
    cache_file = DEFAULT_CACHE_DIR / "company_tickers.json"
    
    if cache_file.exists():
        cache_file.unlink()
        logger.info(f"Cleared SEC cache: {cache_file}")
        return True
    
    return False
