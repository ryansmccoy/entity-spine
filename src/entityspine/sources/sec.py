"""
SEC Symbology Source.

STDLIB ONLY - NO PYDANTIC.

Fetches company symbology from SEC's company_tickers_exchange.json endpoint.

This is the primary source for:
- Company names
- CIK numbers
- Exchange tickers
- Exchange listings (NYSE, Nasdaq, etc.)

Data Source:
- URL: https://www.sec.gov/files/company_tickers_exchange.json
- Format: JSON with fields array and data array
- Records: ~10,000 public companies
- Update: Real-time with SEC filings

Exchange Mapping:
- SEC provides exchange names: "Nasdaq", "NYSE", "Cboe", "NYSE Arca"
- We map these to ISO 10383 MIC codes for standardization

Example:
    >>> from entityspine.sources import SECTickerSource
    >>>
    >>> source = SECTickerSource()
    >>> records = await source.fetch()
    >>> print(f"Fetched {len(records)} companies")
    >>> print(records[0])
    # {'cik': '0001045810', 'ticker': 'NVDA', 'name': 'NVIDIA CORP', 'exchange': 'Nasdaq', 'mic': 'XNAS'}

v1.0.0 Initial implementation.
v2.0.0 Updated to use company_tickers_exchange.json with real exchange data.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import logging
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from entityspine.domain.timestamps import utc_now

logger = logging.getLogger(__name__)


# =============================================================================
# Exchange Name to MIC Mapping
# =============================================================================

# Maps SEC exchange names to ISO 10383 MIC codes
# SEC uses human-readable names; we normalize to standard MICs
SEC_EXCHANGE_TO_MIC: dict[str, str] = {
    # US National Exchanges
    "Nasdaq": "XNAS",
    "NASDAQ": "XNAS",
    "Nasdaq Capital Market": "XNCM",
    "Nasdaq Global Market": "XNMS",
    "Nasdaq Global Select": "XNGS",
    "NYSE": "XNYS",
    "New York Stock Exchange": "XNYS",
    "NYSE American": "XASE",
    "AMEX": "XASE",
    "NYSE Arca": "ARCX",
    "Arca": "ARCX",
    "Cboe": "BATS",
    "Cboe BZX": "BATS",
    "Cboe BYX": "BATY",
    "CBOE": "BATS",
    "IEX": "IEXG",
    "LTSE": "LTSE",

    # OTC Markets
    "OTC": "OTCM",
    "OTC Markets": "OTCM",
    "OTCQX": "OTCQ",
    "OTCQB": "OTCB",
    "Pink": "PINX",
    "OTC Pink": "PINX",

    # Catch-all for unknown
    "": "UNKNOWN",
}


# =============================================================================
# Bronze Layer: Snapshot Metadata
# =============================================================================


@dataclass(frozen=True, slots=True)
class SECTickerSnapshot:
    """
    Bronze layer: Immutable snapshot metadata for SEC ticker data.
    
    Attributes:
        snapshot_id: Unique identifier for this snapshot.
        source_url: URL the data was fetched from.
        content_hash: SHA-256 hash of content.
        record_count: Number of records in snapshot.
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


class SECTickerSource:
    """
    SEC company_tickers_exchange.json symbology source.

    Fetches company information from the SEC's public company_tickers_exchange.json file.
    This file contains ~10,000 public companies with their CIKs, tickers, and exchanges.
    
    Key improvement over company_tickers.json:
    - Includes actual exchange names (NYSE, Nasdaq, etc.)
    - We map these to standard ISO 10383 MIC codes
    
    Attributes:
        name: Source identifier ("sec-tickers")
        url: SEC API endpoint URL

    Example:
        >>> source = SECTickerSource()
        >>> records = await source.fetch()
        >>> apple = next(r for r in records if r['ticker'] == 'AAPL')
        >>> print(f"{apple['name']} - CIK: {apple['cik']} - Exchange: {apple['exchange']} ({apple['mic']})")
        Apple Inc. - CIK: 0000320193 - Exchange: Nasdaq (XNAS)
    """

    name: str = "sec-tickers"
    # Use the exchange-enriched endpoint
    url: str = "https://www.sec.gov/files/company_tickers_exchange.json"
    fallback_url: str = "https://www.sec.gov/files/company_tickers.json"

    def __init__(
        self,
        url: str | None = None,
        use_exchange_data: bool = True,
    ):
        """
        Initialize SEC ticker source.

        Args:
            url: Override URL for testing (defaults to SEC endpoint)
            use_exchange_data: If True, use company_tickers_exchange.json with real exchange data.
                              If False, fall back to company_tickers.json.
        """
        if url:
            self.url = url
        elif not use_exchange_data:
            self.url = self.fallback_url

        self._last_snapshot: SECTickerSnapshot | None = None

    async def fetch(self) -> list[dict[str, Any]]:
        """
        Fetch company tickers from SEC.

        Returns:
            List of dicts with keys: cik, ticker, name, exchange, mic

        Note:
            Uses urllib.request (stdlib) to maintain zero-dependency core.
            For async HTTP, install httpx: pip install httpx
        """
        logger.info(f"Fetching SEC tickers from {self.url}")

        content, records = await self._fetch_sync()

        # Create snapshot metadata
        content_hash = hashlib.sha256(content).hexdigest()
        self._last_snapshot = SECTickerSnapshot(
            snapshot_id=f"sec_{content_hash[:16]}",
            source_url=self.url,
            content_hash=content_hash,
            record_count=len(records),
            captured_at=utc_now(),
        )

        logger.info(f"Fetched {len(records)} companies from SEC")
        return records

    async def _fetch_sync(self) -> tuple[bytes, list[dict[str, Any]]]:
        """Synchronous fetch wrapped for async interface."""
        try:
            req = urllib.request.Request(
                self.url,
                headers={
                    # SEC requires a descriptive User-Agent with contact info
                    "User-Agent": "EntitySpine entity-resolution-library admin@entityspine.io",
                    "Accept": "application/json",
                    "Accept-Encoding": "gzip, deflate",
                    "Host": "www.sec.gov",
                },
            )
            with urllib.request.urlopen(req, timeout=30) as response:
                content = response.read()

                # Handle gzip compression
                if content[:2] == b'\x1f\x8b':
                    content = gzip.decompress(content)

                data = json.loads(content.decode("utf-8"))

            records = self._transform_records(data)
            return content, records

        except Exception as e:
            logger.error(f"Failed to fetch SEC tickers: {e}")
            raise

    def _transform_records(self, data: dict) -> list[dict[str, Any]]:
        """
        Transform SEC API response to standard format.

        company_tickers_exchange.json format:
        {
            "fields": ["cik", "name", "ticker", "exchange"],
            "data": [
                [1045810, "NVIDIA CORP", "NVDA", "Nasdaq"],
                ...
            ]
        }
        
        company_tickers.json format (fallback):
        {
            "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
            ...
        }

        We return: [{"cik": "0001045810", "ticker": "NVDA", "name": "NVIDIA CORP", 
                     "exchange": "Nasdaq", "mic": "XNAS"}, ...]
        """
        records = []

        # Check which format we have
        if "fields" in data and "data" in data:
            # company_tickers_exchange.json format
            fields = data["fields"]
            cik_idx = fields.index("cik") if "cik" in fields else 0
            name_idx = fields.index("name") if "name" in fields else 1
            ticker_idx = fields.index("ticker") if "ticker" in fields else 2
            exchange_idx = fields.index("exchange") if "exchange" in fields else 3

            for row in data["data"]:
                cik = str(row[cik_idx]).zfill(10)
                name = row[name_idx] if len(row) > name_idx else ""
                ticker = row[ticker_idx] if len(row) > ticker_idx else ""
                exchange = row[exchange_idx] if len(row) > exchange_idx else ""

                # Map exchange name to MIC
                mic = self._exchange_to_mic(exchange)

                records.append({
                    "cik": cik,
                    "ticker": ticker,
                    "name": name,
                    "exchange": exchange,
                    "mic": mic,
                })
        else:
            # company_tickers.json format (legacy fallback)
            for item in data.values():
                if not isinstance(item, dict):
                    continue

                cik = str(item.get("cik_str", "")).zfill(10)
                ticker = item.get("ticker", "")
                name = item.get("title", "")

                # No exchange in legacy format - infer from ticker
                exchange = self._infer_exchange(ticker)
                mic = self._exchange_to_mic(exchange)

                records.append({
                    "cik": cik,
                    "ticker": ticker,
                    "name": name,
                    "exchange": exchange,
                    "mic": mic,
                })

        return records

    def _exchange_to_mic(self, exchange: str) -> str:
        """
        Map SEC exchange name to ISO 10383 MIC code.
        
        Args:
            exchange: Exchange name from SEC (e.g., "Nasdaq", "NYSE")
            
        Returns:
            ISO 10383 MIC code (e.g., "XNAS", "XNYS")
        """
        if not exchange:
            return "UNKNOWN"

        # Try exact match first
        if exchange in SEC_EXCHANGE_TO_MIC:
            return SEC_EXCHANGE_TO_MIC[exchange]

        # Try case-insensitive match
        exchange_upper = exchange.upper()
        for name, mic in SEC_EXCHANGE_TO_MIC.items():
            if name.upper() == exchange_upper:
                return mic

        # Try partial match
        exchange_lower = exchange.lower()
        if "nasdaq" in exchange_lower:
            return "XNAS"
        if "nyse" in exchange_lower or "new york" in exchange_lower:
            return "XNYS"
        if "arca" in exchange_lower:
            return "ARCX"
        if "cboe" in exchange_lower or "bats" in exchange_lower:
            return "BATS"
        if "otc" in exchange_lower or "pink" in exchange_lower:
            return "OTCM"

        # Unknown exchange
        logger.warning(f"Unknown SEC exchange: {exchange}")
        return "UNKNOWN"

    def _infer_exchange(self, ticker: str) -> str:
        """
        Infer exchange from ticker format (legacy fallback).
        
        This is a heuristic for when using company_tickers.json
        which doesn't include exchange data.
        """
        if not ticker:
            return "UNKNOWN"

        # Common patterns
        if len(ticker) <= 4 and ticker.isalpha():
            return "Nasdaq"  # Most likely NASDAQ or NYSE

        if len(ticker) == 5 and ticker.endswith("W"):
            return "NYSE"  # Warrants typically NYSE

        if len(ticker) > 5:
            return "OTC"

        return "US"  # Generic US exchange

    @property
    def last_snapshot(self) -> SECTickerSnapshot | None:
        """Get metadata from last fetch."""
        return self._last_snapshot


# =============================================================================
# Convenience Functions
# =============================================================================


def get_mic_for_exchange(exchange_name: str) -> str:
    """
    Get MIC code for an SEC exchange name.
    
    Args:
        exchange_name: Exchange name from SEC data.
        
    Returns:
        ISO 10383 MIC code.
    """
    source = SECTickerSource()
    return source._exchange_to_mic(exchange_name)
