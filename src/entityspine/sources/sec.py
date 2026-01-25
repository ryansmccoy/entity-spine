"""
SEC Symbology Source

Fetches company symbology from SEC's company_tickers.json endpoint.

This is the primary source for:
- Company names
- CIK numbers
- Exchange tickers

Example:
    >>> from entityspine.sources import SECTickerSource
    >>>
    >>> source = SECTickerSource()
    >>> records = await source.fetch()
    >>> print(f"Fetched {len(records)} companies")
    >>> print(records[0])
    # {'cik': '0000320193', 'ticker': 'AAPL', 'name': 'Apple Inc.', 'exchange': 'Nasdaq'}
"""

from __future__ import annotations

import json
import logging
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)


class SECTickerSource:
    """SEC company_tickers.json symbology source.

    Fetches company information from the SEC's public company_tickers.json file.
    This file contains ~14,000 public companies with their CIKs and tickers.

    Attributes:
        name: Source identifier ("sec-tickers")
        url: SEC API endpoint URL

    Example:
        >>> source = SECTickerSource()
        >>> records = await source.fetch()
        >>> apple = next(r for r in records if r['ticker'] == 'AAPL')
        >>> print(f"{apple['name']} - CIK: {apple['cik']}")
        Apple Inc. - CIK: 0000320193
    """

    name: str = "sec-tickers"
    url: str = "https://www.sec.gov/files/company_tickers.json"

    def __init__(self, url: str | None = None):
        """Initialize SEC ticker source.

        Args:
            url: Override URL for testing (defaults to SEC endpoint)
        """
        if url:
            self.url = url

    async def fetch(self) -> list[dict[str, Any]]:
        """Fetch company tickers from SEC.

        Returns:
            List of dicts with keys: cik, ticker, name, exchange

        Note:
            Uses urllib.request (stdlib) to maintain zero-dependency core.
            For async HTTP, install httpx: pip install httpx
        """
        logger.info(f"Fetching SEC tickers from {self.url}")

        # Use stdlib urllib for zero-dependency operation
        # Note: Could use httpx if available for true async
        records = await self._fetch_sync()

        logger.info(f"Fetched {len(records)} companies from SEC")
        return records

    async def _fetch_sync(self) -> list[dict[str, Any]]:
        """Synchronous fetch wrapped for async interface."""
        try:
            req = urllib.request.Request(
                self.url,
                headers={"User-Agent": "EntitySpine/1.0 (entity resolution library)"},
            )
            with urllib.request.urlopen(req, timeout=30) as response:
                data = json.loads(response.read().decode("utf-8"))

            return self._transform_records(data)

        except Exception as e:
            logger.error(f"Failed to fetch SEC tickers: {e}")
            raise

    def _transform_records(self, data: dict) -> list[dict[str, Any]]:
        """Transform SEC API response to standard format.

        SEC returns: {"0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}, ...}

        We return: [{"cik": "0000320193", "ticker": "AAPL", "name": "Apple Inc.", "exchange": "..."}, ...]
        """
        records = []

        for item in data.values():
            cik = str(item.get("cik_str", "")).zfill(10)
            ticker = item.get("ticker", "")
            name = item.get("title", "")

            # Determine exchange from ticker patterns
            exchange = self._infer_exchange(ticker)

            records.append(
                {
                    "cik": cik,
                    "ticker": ticker,
                    "name": name,
                    "exchange": exchange,
                }
            )

        return records

    def _infer_exchange(self, ticker: str) -> str:
        """Infer exchange from ticker format.

        This is a heuristic - SEC doesn't provide exchange directly.
        """
        if not ticker:
            return "UNKNOWN"

        # Common patterns
        if len(ticker) <= 4 and ticker.isalpha():
            return "XNAS"  # Most likely NASDAQ or NYSE

        # ADRs typically have longer tickers
        if len(ticker) > 5:
            return "OTC"

        return "US"  # Generic US exchange
