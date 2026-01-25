"""
EntitySpine Symbology Sources

This module provides pre-built sources for common symbology providers:

- SECTickerSource: SEC company_tickers.json
- GLEIFSource: GLEIF LEI bulk data (coming soon)
- OpenFIGISource: OpenFIGI API (coming soon)

Example:
    >>> from entityspine.sources import SECTickerSource
    >>> from entityspine.services import SymbologyRefreshService
    >>> from entityspine import SqliteStore
    >>>
    >>> store = SqliteStore("entities.db")
    >>> store.initialize()
    >>>
    >>> service = SymbologyRefreshService(store)
    >>> service.add_source(SECTickerSource())
    >>> results = await service.refresh_all()
"""

from entityspine.sources.sec import SECTickerSource

__all__ = [
    "SECTickerSource",
]
