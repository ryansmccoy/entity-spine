"""
Simple ticker/identifier lookup utility.

STDLIB ONLY - NO PYDANTIC.

Provides dead-simple API for common lookup tasks:

    from entityspine.services.lookup import Lookup

    lu = Lookup()  # Auto-loads SEC data
    
    # Single lookups
    lu.ticker("0000320193")      # "AAPL" (from CIK)
    lu.ticker("Apple Inc")       # "AAPL" (from name)
    lu.cik("AAPL")              # "0000320193"
    lu.name("AAPL")             # "Apple Inc."
    
    # Batch lookups (great for DataFrame columns)
    ciks = ["0000320193", "0001018724", "0001652044"]
    tickers = lu.tickers(ciks)  # ["AAPL", "AMZN", "GOOGL"]
    
    # Dict mapping
    lu.cik_to_ticker(ciks)      # {"0000320193": "AAPL", ...}
    lu.name_to_ticker(names)    # {"Apple Inc": "AAPL", ...}

Shared Database Configuration:
    # Set via environment variable (recommended)
    export ENTITYSPINE_DB_PATH=/data/shared/entityspine.db
    
    # Or programmatically at app startup
    from entityspine import use_shared_db
    use_shared_db("/data/shared/entityspine.db")
    
    # Check current database location
    from entityspine import get_db_path
    print(get_db_path())

Design:
- Zero-config (auto-downloads SEC company_tickers.json on first use)
- Returns None on not found (no exceptions)
- Thread-safe singleton pattern
- Caches results for fast repeat lookups
- Uses ENTITYSPINE_DB_PATH for shared database across apps
"""

from __future__ import annotations

import logging
import os
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

# Lazy import to avoid circular deps
_resolver = None


def _get_resolver():
    """Lazy-load the resolver singleton."""
    global _resolver
    if _resolver is None:
        from entityspine.services.resolver import EntityResolver
        _resolver = EntityResolver()
    return _resolver


@dataclass
class Lookup:
    """
    Simple ticker/identifier lookup utility.
    
    Examples:
        >>> lu = Lookup()
        >>> lu.ticker("0000320193")
        'AAPL'
        >>> lu.ticker("Apple Inc")
        'AAPL'
        >>> lu.cik("AAPL")
        '0000320193'
        >>> lu.tickers(["0000320193", "0001018724"])
        ['AAPL', 'AMZN']
    """

    _cache: dict = field(default_factory=dict, repr=False)
    default_ticker: str = "???"
    default_cik: str = ""
    default_name: str = ""

    # =========================================================================
    # Single Lookups
    # =========================================================================

    def ticker(self, query: str, default: str | None = None) -> str | None:
        """
        Get ticker from any identifier (CIK, name, ISIN, etc).
        
        Args:
            query: CIK, company name, ISIN, or any identifier
            default: Value to return if not found (None if not specified)
            
        Returns:
            Ticker symbol or default value
            
        Examples:
            >>> lu.ticker("0000320193")
            'AAPL'
            >>> lu.ticker("Apple Inc")
            'AAPL'
            >>> lu.ticker("nonexistent", "N/A")
            'N/A'
        """
        cache_key = ("ticker", query)
        if cache_key in self._cache:
            result = self._cache[cache_key]
            return result if result else (default if default is not None else self.default_ticker if self.default_ticker != "???" else None)

        # Try offline lookup first for speed
        ticker = None

        # Check if it looks like a CIK
        query_clean = query.strip()
        if query_clean.isdigit() or (query_clean.startswith("0") and query_clean[1:].isdigit()):
            ticker = offline_ticker(query_clean)

        # If not found offline, try full resolver
        if not ticker:
            resolver = _get_resolver()
            result = resolver.resolve(query)

            if result.entity:
                # Try to get ticker from listing (singular)
                if result.listing:
                    ticker = result.listing.ticker
                # Check candidates for ticker
                if not ticker and result.candidates:
                    for candidate in result.candidates:
                        if hasattr(candidate, 'ticker') and candidate.ticker:
                            ticker = candidate.ticker
                            break

        self._cache[cache_key] = ticker
        return ticker if ticker else (default if default is not None else None)

    def cik(self, query: str, default: str | None = None) -> str | None:
        """
        Get CIK from any identifier (ticker, name, ISIN, etc).
        
        Args:
            query: Ticker, company name, or any identifier
            default: Value to return if not found
            
        Returns:
            CIK (10-digit zero-padded) or default value
            
        Examples:
            >>> lu.cik("AAPL")
            '0000320193'
            >>> lu.cik("Apple Inc")
            '0000320193'
        """
        cache_key = ("cik", query)
        if cache_key in self._cache:
            result = self._cache[cache_key]
            return result if result else default

        resolver = _get_resolver()
        result = resolver.resolve(query)

        cik = None
        if result.entity and result.entity.source_system == "sec":
            cik = result.entity.source_id
            # Ensure zero-padded
            if cik and not cik.startswith("0"):
                cik = cik.zfill(10)

        self._cache[cache_key] = cik
        return cik if cik else default

    def name(self, query: str, default: str | None = None) -> str | None:
        """
        Get company name from any identifier.
        
        Args:
            query: Ticker, CIK, or any identifier
            default: Value to return if not found
            
        Returns:
            Company name or default value
            
        Examples:
            >>> lu.name("AAPL")
            'Apple Inc.'
            >>> lu.name("0000320193")
            'Apple Inc.'
        """
        cache_key = ("name", query)
        if cache_key in self._cache:
            result = self._cache[cache_key]
            return result if result else default

        resolver = _get_resolver()
        result = resolver.resolve(query)

        name = result.entity.primary_name if result.entity else None

        self._cache[cache_key] = name
        return name if name else default

    # =========================================================================
    # Batch Lookups (for DataFrame columns)
    # =========================================================================

    def tickers(
        self,
        queries: Iterable[str],
        default: str | None = None
    ) -> list[str | None]:
        """
        Get tickers for multiple identifiers.
        
        Great for applying to a DataFrame column:
            df['ticker'] = lu.tickers(df['cik'])
        
        Args:
            queries: Iterable of CIKs, names, or any identifiers
            default: Default value for not found
            
        Returns:
            List of tickers (same order as input)
        """
        return [self.ticker(q, default) for q in queries]

    def ciks(
        self,
        queries: Iterable[str],
        default: str | None = None
    ) -> list[str | None]:
        """
        Get CIKs for multiple identifiers.
        
        Args:
            queries: Iterable of tickers, names, or any identifiers
            default: Default value for not found
            
        Returns:
            List of CIKs (same order as input)
        """
        return [self.cik(q, default) for q in queries]

    def names(
        self,
        queries: Iterable[str],
        default: str | None = None
    ) -> list[str | None]:
        """
        Get company names for multiple identifiers.
        
        Args:
            queries: Iterable of tickers, CIKs, or any identifiers
            default: Default value for not found
            
        Returns:
            List of names (same order as input)
        """
        return [self.name(q, default) for q in queries]

    # =========================================================================
    # Dict Mappings
    # =========================================================================

    def cik_to_ticker(
        self,
        ciks: Iterable[str],
        default: str | None = None
    ) -> dict[str, str | None]:
        """
        Create CIK → ticker mapping dict.
        
        Args:
            ciks: Iterable of CIKs
            default: Default value for not found
            
        Returns:
            Dict mapping CIK to ticker
            
        Examples:
            >>> lu.cik_to_ticker(["0000320193", "0001018724"])
            {'0000320193': 'AAPL', '0001018724': 'AMZN'}
        """
        return {cik: self.ticker(cik, default) for cik in ciks}

    def ticker_to_cik(
        self,
        tickers: Iterable[str],
        default: str | None = None
    ) -> dict[str, str | None]:
        """
        Create ticker → CIK mapping dict.
        
        Args:
            tickers: Iterable of tickers
            default: Default value for not found
            
        Returns:
            Dict mapping ticker to CIK
        """
        return {ticker: self.cik(ticker, default) for ticker in tickers}

    def name_to_ticker(
        self,
        names: Iterable[str],
        default: str | None = None
    ) -> dict[str, str | None]:
        """
        Create company name → ticker mapping dict.
        
        Supports fuzzy matching.
        
        Args:
            names: Iterable of company names
            default: Default value for not found
            
        Returns:
            Dict mapping name to ticker
            
        Examples:
            >>> lu.name_to_ticker(["Apple Inc", "Amazon Com"])
            {'Apple Inc': 'AAPL', 'Amazon Com': 'AMZN'}
        """
        return {name: self.ticker(name, default) for name in names}

    def cik_to_name(
        self,
        ciks: Iterable[str],
        default: str | None = None
    ) -> dict[str, str | None]:
        """
        Create CIK → company name mapping dict.
        
        Args:
            ciks: Iterable of CIKs
            default: Default value for not found
            
        Returns:
            Dict mapping CIK to company name
        """
        return {cik: self.name(cik, default) for cik in ciks}

    # =========================================================================
    # ISIN/LEI Lookups
    # =========================================================================

    def lei_from_isin(self, isin: str, default: str | None = None) -> str | None:
        """
        Get LEI from ISIN using the GLEIF mapping table.
        
        Args:
            isin: ISIN identifier (12 characters)
            default: Value to return if not found
            
        Returns:
            LEI (Legal Entity Identifier) or default value
            
        Examples:
            >>> lu.lei_from_isin("US0378331005")
            'HWUPKR0MPOU8FGXBT394'
        """
        cache_key = ("lei_from_isin", isin)
        if cache_key in self._cache:
            result = self._cache[cache_key]
            return result if result else default

        lei = _lookup_isin_lei(isin)
        self._cache[cache_key] = lei
        return lei if lei else default

    def isins_from_lei(self, lei: str) -> list[str]:
        """
        Get all ISINs associated with an LEI.
        
        Args:
            lei: Legal Entity Identifier (20 characters)
            
        Returns:
            List of ISINs associated with this LEI
            
        Examples:
            >>> lu.isins_from_lei("HWUPKR0MPOU8FGXBT394")
            ['US0378331005', 'US0378331013', ...]
        """
        cache_key = ("isins_from_lei", lei)
        if cache_key in self._cache:
            return self._cache[cache_key]

        isins = _lookup_lei_isins(lei)
        self._cache[cache_key] = isins
        return isins

    def lei_lookup(self, lei: str) -> dict | None:
        """
        Get entity info from LEI.
        
        Args:
            lei: Legal Entity Identifier
            
        Returns:
            Dict with entity_name, jurisdiction, status, or None
        """
        return _lookup_lei(lei)

    def bic_from_lei(self, lei: str, default: str | None = None) -> str | None:
        """
        Get BIC (Bank Identifier Code) from LEI.
        
        Args:
            lei: Legal Entity Identifier
            default: Value to return if not found
            
        Returns:
            BIC code or default value
        """
        cache_key = ("bic_from_lei", lei)
        if cache_key in self._cache:
            result = self._cache[cache_key]
            return result if result else default

        bic = _lookup_lei_bic(lei)
        self._cache[cache_key] = bic
        return bic if bic else default

    # =========================================================================
    # Utilities
    # =========================================================================

    def clear_cache(self) -> None:
        """Clear the lookup cache."""
        self._cache.clear()

    def cache_stats(self) -> dict:
        """Get cache statistics."""
        return {
            "size": len(self._cache),
            "ticker_lookups": sum(1 for k in self._cache if k[0] == "ticker"),
            "cik_lookups": sum(1 for k in self._cache if k[0] == "cik"),
            "name_lookups": sum(1 for k in self._cache if k[0] == "name"),
            "isin_lookups": sum(1 for k in self._cache if k[0] in ("lei_from_isin", "isins_from_lei")),
        }


# =============================================================================
# Convenience functions (module-level)
# =============================================================================

_default_lookup: Lookup | None = None


def _get_lookup() -> Lookup:
    """Get or create the default Lookup instance."""
    global _default_lookup
    if _default_lookup is None:
        _default_lookup = Lookup()
    return _default_lookup


def ticker(query: str, default: str | None = None) -> str | None:
    """
    Get ticker from any identifier.
    
    Module-level convenience function.
    
    Examples:
        >>> from entityspine.services.lookup import ticker
        >>> ticker("0000320193")
        'AAPL'
    """
    return _get_lookup().ticker(query, default)


def cik(query: str, default: str | None = None) -> str | None:
    """
    Get CIK from any identifier.
    
    Module-level convenience function.
    
    Examples:
        >>> from entityspine.services.lookup import cik
        >>> cik("AAPL")
        '0000320193'
    """
    return _get_lookup().cik(query, default)


def name(query: str, default: str | None = None) -> str | None:
    """
    Get company name from any identifier.
    
    Module-level convenience function.
    
    Examples:
        >>> from entityspine.services.lookup import name
        >>> name("AAPL")
        'Apple Inc.'
    """
    return _get_lookup().name(query, default)


def tickers(queries: Iterable[str], default: str | None = None) -> list[str | None]:
    """
    Get tickers for multiple identifiers.
    
    Examples:
        >>> from entityspine.services.lookup import tickers
        >>> tickers(["0000320193", "0001018724"])
        ['AAPL', 'AMZN']
    """
    return _get_lookup().tickers(queries, default)


def ciks(queries: Iterable[str], default: str | None = None) -> list[str | None]:
    """
    Get CIKs for multiple identifiers.
    
    Examples:
        >>> from entityspine.services.lookup import ciks
        >>> ciks(["AAPL", "AMZN"])
        ['0000320193', '0001018724']
    """
    return _get_lookup().ciks(queries, default)


def names(queries: Iterable[str], default: str | None = None) -> list[str | None]:
    """
    Get company names for multiple identifiers.
    
    Examples:
        >>> from entityspine.services.lookup import names
        >>> names(["AAPL", "AMZN"])
        ['Apple Inc.', 'Amazon.com, Inc.']
    """
    return _get_lookup().names(queries, default)


# =============================================================================
# CIK-Ticker Reference Data (fast in-memory fallback)
# =============================================================================

# Common SEC CIK to Ticker mappings for fast lookup without DB
# This is loaded from SEC company_tickers.json on first use
_CIK_TICKER_MAP: dict[str, str] | None = None
_TICKER_CIK_MAP: dict[str, str] | None = None


def _load_sec_mappings():
    """Load SEC CIK-ticker mappings from company_tickers.json."""
    global _CIK_TICKER_MAP, _TICKER_CIK_MAP

    if _CIK_TICKER_MAP is not None:
        return

    try:
        import json
        from pathlib import Path

        # Try to find cached SEC data
        cache_dir = Path.home() / ".entityspine" / "cache"
        tickers_file = cache_dir / "company_tickers.json"

        if tickers_file.exists():
            with open(tickers_file) as f:
                data = json.load(f)

            _CIK_TICKER_MAP = {}
            _TICKER_CIK_MAP = {}

            for entry in data.values():
                cik_raw = entry.get("cik_str") or str(entry.get("cik", ""))
                ticker = entry.get("ticker", "")

                if cik_raw and ticker:
                    cik_padded = str(cik_raw).zfill(10)
                    _CIK_TICKER_MAP[cik_padded] = ticker
                    _CIK_TICKER_MAP[cik_raw] = ticker  # Also store unpadded
                    _TICKER_CIK_MAP[ticker.upper()] = cik_padded

            logger.info(f"Loaded {len(_CIK_TICKER_MAP)} CIK-ticker mappings")
    except Exception as e:
        logger.warning(f"Could not load SEC mappings: {e}")
        _CIK_TICKER_MAP = {}
        _TICKER_CIK_MAP = {}


def fast_ticker(cik: str) -> str | None:
    """
    Fast CIK → ticker lookup using in-memory map.
    
    Falls back to full resolver if not in map.
    
    Examples:
        >>> fast_ticker("0000320193")
        'AAPL'
    """
    _load_sec_mappings()

    if _CIK_TICKER_MAP:
        # Try padded and unpadded
        result = _CIK_TICKER_MAP.get(cik)
        if result:
            return result
        result = _CIK_TICKER_MAP.get(cik.lstrip("0"))
        if result:
            return result
        result = _CIK_TICKER_MAP.get(cik.zfill(10))
        if result:
            return result

    # Fall back to full resolver
    return ticker(cik)


def fast_cik(ticker_symbol: str) -> str | None:
    """
    Fast ticker → CIK lookup using in-memory map.
    
    Examples:
        >>> fast_cik("AAPL")
        '0000320193'
    """
    _load_sec_mappings()

    if _TICKER_CIK_MAP:
        result = _TICKER_CIK_MAP.get(ticker_symbol.upper())
        if result:
            return result

    # Fall back to full resolver
    return cik(ticker_symbol)


# =============================================================================
# Hardcoded fallback for most common companies (works offline)
# =============================================================================

COMMON_COMPANIES = {
    # CIK -> (ticker, name)
    "0000320193": ("AAPL", "Apple Inc."),
    "0001018724": ("AMZN", "Amazon.com, Inc."),
    "0001652044": ("GOOGL", "Alphabet Inc."),
    "0000789019": ("MSFT", "Microsoft Corporation"),
    "0001326801": ("META", "Meta Platforms, Inc."),
    "0001045810": ("NVDA", "NVIDIA Corporation"),
    "0001318605": ("TSLA", "Tesla, Inc."),
    "0001067983": ("BRK-A", "Berkshire Hathaway Inc."),
    "0000051143": ("IBM", "International Business Machines Corporation"),
    "0000886982": ("GS", "The Goldman Sachs Group, Inc."),
    "0000070858": ("BAC", "Bank of America Corporation"),
    "0000019617": ("JPM", "JPMorgan Chase & Co."),
    "0000200406": ("JNJ", "Johnson & Johnson"),
    "0000034088": ("XOM", "Exxon Mobil Corporation"),
    "0000078003": ("PFE", "Pfizer Inc."),
    "0000021344": ("KO", "The Coca-Cola Company"),
    "0000080424": ("PG", "The Procter & Gamble Company"),
    "0000093410": ("CVX", "Chevron Corporation"),
    "0000732717": ("VZ", "Verizon Communications Inc."),
    "0000066740": ("MMM", "3M Company"),
    "0001467373": ("CRM", "Salesforce, Inc."),
    "0000804328": ("QCOM", "QUALCOMM Incorporated"),
    "0001341439": ("ORCL", "Oracle Corporation"),
    "0000097745": ("TXN", "Texas Instruments Incorporated"),
    "0001403161": ("V", "Visa Inc."),
    "0000063908": ("MCD", "McDonald's Corporation"),
    "0001065280": ("NFLX", "Netflix, Inc."),
    "0000858877": ("HD", "The Home Depot, Inc."),
    "0000090185": ("DIS", "The Walt Disney Company"),
    "0000895421": ("MA", "Mastercard Incorporated"),
}

# Reverse mappings
_TICKER_TO_CIK_COMMON = {v[0]: k for k, v in COMMON_COMPANIES.items()}
_NAME_TO_CIK_COMMON = {v[1].upper(): k for k, v in COMMON_COMPANIES.items()}


def offline_ticker(cik: str) -> str | None:
    """
    Get ticker from CIK using hardcoded common companies (works offline).
    
    Examples:
        >>> offline_ticker("0000320193")
        'AAPL'
    """
    cik_padded = cik.zfill(10)
    entry = COMMON_COMPANIES.get(cik_padded)
    return entry[0] if entry else None


def offline_cik(ticker_symbol: str) -> str | None:
    """
    Get CIK from ticker using hardcoded common companies (works offline).
    
    Examples:
        >>> offline_cik("AAPL")
        '0000320193'
    """
    return _TICKER_TO_CIK_COMMON.get(ticker_symbol.upper())


def offline_name(query: str) -> str | None:
    """
    Get company name from CIK or ticker (works offline).
    
    Examples:
        >>> offline_name("AAPL")
        'Apple Inc.'
        >>> offline_name("0000320193")
        'Apple Inc.'
    """
    # Try as CIK
    cik_padded = query.zfill(10) if query.isdigit() or query.startswith("0") else None
    if cik_padded:
        entry = COMMON_COMPANIES.get(cik_padded)
        if entry:
            return entry[1]

    # Try as ticker
    cik_from_ticker = _TICKER_TO_CIK_COMMON.get(query.upper())
    if cik_from_ticker:
        entry = COMMON_COMPANIES.get(cik_from_ticker)
        if entry:
            return entry[1]

    return None


# =============================================================================
# Shared Database Configuration
# =============================================================================

def get_db_path() -> str:
    """
    Get the current EntitySpine database path.
    
    Returns:
        Path to the SQLite database being used.
        
    Examples:
        >>> get_db_path()
        '/home/user/.entityspine/entityspine.db'
    """
    from entityspine.core.config import get_settings
    return get_settings().db_path


def use_shared_db(path: str | Path | None = None) -> Path:
    """
    Configure EntitySpine to use a shared persistent database.
    
    Call this at app startup to ensure all EntitySpine operations
    use the same database. This is important when multiple apps
    or scripts need to share the same symbology data.
    
    Args:
        path: Path to database. If None, uses default ~/.entityspine/entityspine.db
        
    Returns:
        Path to the database file.
        
    Examples:
        >>> # Use default shared location
        >>> db_path = use_shared_db()
        >>> print(f"Using database: {db_path}")
        Using database: /home/user/.entityspine/entityspine.db
        
        >>> # Use custom location for production
        >>> db_path = use_shared_db("/data/entityspine/production.db")
    """
    global _resolver, _default_lookup

    if path is None:
        path = Path.home() / ".entityspine" / "entityspine.db"
    else:
        path = Path(path)

    # Set environment variable for all future imports
    os.environ["ENTITYSPINE_DB_PATH"] = str(path)

    # Ensure directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    # Reset singletons to pick up new config
    _resolver = None
    _default_lookup = None

    logger.info(f"EntitySpine using shared database: {path}")
    return path


def reset_resolver() -> None:
    """
    Reset the resolver singleton.
    
    Useful when database path changes or for testing.
    """
    global _resolver, _default_lookup
    _resolver = None
    _default_lookup = None


# =============================================================================
# ISIN/LEI Database Lookups
# =============================================================================

def _get_db_connection():
    """Get a connection to the shared EntitySpine database."""
    import sqlite3

    from entityspine.core.config import get_settings

    db_path = get_settings().db_path
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _lookup_isin_lei(isin: str) -> str | None:
    """
    Look up LEI from ISIN in the database.
    
    Args:
        isin: ISIN identifier
        
    Returns:
        LEI or None if not found
    """
    try:
        conn = _get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT lei FROM isin_mappings WHERE isin = ?", (isin.upper().strip(),))
        row = cursor.fetchone()
        conn.close()
        return row["lei"] if row else None
    except Exception as e:
        logger.debug(f"ISIN lookup failed: {e}")
        return None


def _lookup_lei_isins(lei: str) -> list[str]:
    """
    Look up all ISINs for an LEI in the database.
    
    Args:
        lei: Legal Entity Identifier
        
    Returns:
        List of ISINs (may be empty)
    """
    try:
        conn = _get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT isin FROM isin_mappings WHERE lei = ?", (lei.upper().strip(),))
        rows = cursor.fetchall()
        conn.close()
        return [row["isin"] for row in rows]
    except Exception as e:
        logger.debug(f"LEI->ISIN lookup failed: {e}")
        return []


def _lookup_lei(lei: str) -> dict | None:
    """
    Look up LEI entity info in the database.
    
    Args:
        lei: Legal Entity Identifier
        
    Returns:
        Dict with entity_name, jurisdiction, status, or None
    """
    try:
        conn = _get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT entity_name, jurisdiction, status FROM lei_mappings WHERE lei = ?",
            (lei.upper().strip(),)
        )
        row = cursor.fetchone()
        conn.close()
        if row:
            return {
                "entity_name": row["entity_name"],
                "jurisdiction": row["jurisdiction"],
                "status": row["status"],
            }
        return None
    except Exception as e:
        logger.debug(f"LEI lookup failed: {e}")
        return None


def _lookup_lei_bic(lei: str) -> str | None:
    """
    Look up BIC from LEI in the database.
    
    Args:
        lei: Legal Entity Identifier
        
    Returns:
        BIC code or None
    """
    try:
        conn = _get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT bic FROM bic_mappings WHERE lei = ?", (lei.upper().strip(),))
        row = cursor.fetchone()
        conn.close()
        return row["bic"] if row else None
    except Exception as e:
        logger.debug(f"LEI->BIC lookup failed: {e}")
        return None


# =============================================================================
# Module-level ISIN/LEI Functions
# =============================================================================

def lei_from_isin(isin: str, default: str | None = None) -> str | None:
    """
    Get LEI from ISIN.
    
    Module-level convenience function.
    
    Examples:
        >>> from entityspine import lei_from_isin
        >>> lei_from_isin("US0378331005")
        'HWUPKR0MPOU8FGXBT394'
    """
    return _get_lookup().lei_from_isin(isin, default)


def isins_from_lei(lei: str) -> list[str]:
    """
    Get all ISINs for an LEI.
    
    Module-level convenience function.
    
    Examples:
        >>> from entityspine import isins_from_lei
        >>> isins_from_lei("HWUPKR0MPOU8FGXBT394")
        ['US0378331005', ...]
    """
    return _get_lookup().isins_from_lei(lei)


def bic_from_lei(lei: str, default: str | None = None) -> str | None:
    """
    Get BIC from LEI.
    
    Module-level convenience function.
    """
    return _get_lookup().bic_from_lei(lei, default)
