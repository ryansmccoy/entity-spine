"""
EntitySpine Integration Module

This module provides adapters for integrating EntitySpine with external systems:
- py-sec-edgar: SEC filing ingestion
- FeedSpine: Feed record to entity resolution

The integration module:
1. Defines contract schemas (FilingFacts, FeedRecord)
2. Provides ingest functions that convert external data → domain dataclasses
3. Maintains tier honesty (warns when tier limits apply)

All integration functions return domain dataclasses - no foreign types leak out.
"""

from .contracts import FilingEvidence, FilingFacts
from .ingest import ingest_filing, ingest_filing_facts
from .normalize import normalize_cik, normalize_ticker

__all__ = [
    "FilingEvidence",
    # Contracts
    "FilingFacts",
    # Ingest functions
    "ingest_filing",
    "ingest_filing_facts",
    # Normalizers
    "normalize_cik",
    "normalize_ticker",
]
