"""
EntitySpine Python Client

Simple client library for the EntitySpine API.

Usage:
    from entityspine.client import EntitySpineClient
    
    client = EntitySpineClient("http://localhost:8080")
    
    # Simple lookups
    client.ticker("0000320193")  # -> "AAPL"
    client.cik("NVDA")           # -> "0001045810"
    client.name("MSFT")          # -> "Microsoft Corporation"
    
    # Batch lookups
    client.tickers(["0000320193", "0001018724"])  # -> {"0000320193": "AAPL", ...}
    
    # ISIN/LEI
    client.lei_from_isin("US0378331005")  # -> "HWUPKR0MPOU8FGXBT394"
"""

import json
import urllib.request
import urllib.error
from typing import Optional
from dataclasses import dataclass


@dataclass
class EntitySpineClient:
    """
    Client for EntitySpine API.
    
    Args:
        base_url: API base URL (e.g., "http://localhost:8080")
        timeout: Request timeout in seconds
    """
    base_url: str = "http://localhost:8080"
    timeout: int = 30
    
    def _get(self, path: str) -> dict:
        """Make GET request."""
        url = f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"
        request = urllib.request.Request(url)
        request.add_header("Accept", "application/json")
        
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return {"error": "not_found"}
            raise
    
    def _post(self, path: str, data: dict) -> dict:
        """Make POST request."""
        url = f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"
        body = json.dumps(data).encode("utf-8")
        
        request = urllib.request.Request(url, data=body, method="POST")
        request.add_header("Content-Type", "application/json")
        request.add_header("Accept", "application/json")
        
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    
    # =========================================================================
    # Health & Info
    # =========================================================================
    
    def health(self) -> dict:
        """Check API health."""
        return self._get("/health")
    
    def info(self) -> dict:
        """Get API info and statistics."""
        return self._get("/info")
    
    # =========================================================================
    # Single Lookups
    # =========================================================================
    
    def ticker(self, query: str) -> Optional[str]:
        """Get ticker from CIK or name."""
        result = self._get(f"/ticker/{query}")
        return result.get("ticker")
    
    def cik(self, query: str) -> Optional[str]:
        """Get CIK from ticker or name."""
        result = self._get(f"/cik/{query}")
        return result.get("cik")
    
    def name(self, query: str) -> Optional[str]:
        """Get company name from ticker or CIK."""
        result = self._get(f"/name/{query}")
        return result.get("name")
    
    def resolve(self, query: str) -> dict:
        """Resolve identifier and return all info."""
        return self._get(f"/resolve/{query}")
    
    # =========================================================================
    # ISIN/LEI Lookups
    # =========================================================================
    
    def lei_from_isin(self, isin: str) -> Optional[str]:
        """Get LEI from ISIN."""
        result = self._get(f"/lei/{isin}")
        return result.get("lei")
    
    def isins_from_lei(self, lei: str, limit: int = 100) -> list[str]:
        """Get ISINs for an LEI."""
        result = self._get(f"/isins/{lei}?limit={limit}")
        return result.get("isins", [])
    
    def bic_from_lei(self, lei: str) -> Optional[str]:
        """Get BIC from LEI."""
        result = self._get(f"/bic/{lei}")
        return result.get("bic")
    
    # =========================================================================
    # Batch Lookups
    # =========================================================================
    
    def tickers(self, queries: list[str]) -> dict[str, Optional[str]]:
        """Get tickers for multiple identifiers."""
        result = self._post("/batch/tickers", {"queries": queries})
        return result.get("results", {})
    
    def ciks(self, queries: list[str]) -> dict[str, Optional[str]]:
        """Get CIKs for multiple identifiers."""
        result = self._post("/batch/ciks", {"queries": queries})
        return result.get("results", {})
    
    def names(self, queries: list[str]) -> dict[str, Optional[str]]:
        """Get names for multiple identifiers."""
        result = self._post("/batch/names", {"queries": queries})
        return result.get("results", {})


# =============================================================================
# Module-level convenience (uses default localhost)
# =============================================================================

_default_client: EntitySpineClient | None = None


def _get_client() -> EntitySpineClient:
    global _default_client
    if _default_client is None:
        import os
        url = os.environ.get("ENTITYSPINE_API_URL", "http://localhost:8080")
        _default_client = EntitySpineClient(url)
    return _default_client


def ticker(query: str) -> Optional[str]:
    """Get ticker from any identifier (via API)."""
    return _get_client().ticker(query)


def cik(query: str) -> Optional[str]:
    """Get CIK from any identifier (via API)."""
    return _get_client().cik(query)


def name(query: str) -> Optional[str]:
    """Get company name from any identifier (via API)."""
    return _get_client().name(query)


def lei_from_isin(isin: str) -> Optional[str]:
    """Get LEI from ISIN (via API)."""
    return _get_client().lei_from_isin(isin)


if __name__ == "__main__":
    # Quick test
    client = EntitySpineClient()
    print(f"Health: {client.health()}")
    print(f"ticker('0000320193'): {client.ticker('0000320193')}")
    print(f"cik('AAPL'): {client.cik('AAPL')}")
    print(f"resolve('NVDA'): {client.resolve('NVDA')}")
