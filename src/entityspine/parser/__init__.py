"""EntitySpine Parser Module.

Parsers for SEC filing content:
- Exhibit 21 (Subsidiaries)
- Company information
- Corporate events

Usage:
    from entityspine.parser import Exhibit21Parser
    
    parser = Exhibit21Parser()
    result = parser.parse(html_content, cik, accession, filing_date)
"""

from .exhibit21 import (
    # Models
    Exhibit21Parse,
    # Parser
    Exhibit21Parser,
    HTMLTableParser,
    OwnershipType,
    ParseConfidence,
    SubsidiaryParse,
    TextLineParser,
    clean_entity_name,
    detect_inactive_status,
    # Utilities
    normalize_jurisdiction,
    parse_ownership,
)

__all__ = [
    # Parsers
    "Exhibit21Parser",
    "HTMLTableParser",
    "TextLineParser",

    # Models
    "Exhibit21Parse",
    "SubsidiaryParse",
    "ParseConfidence",
    "OwnershipType",

    # Utilities
    "normalize_jurisdiction",
    "parse_ownership",
    "clean_entity_name",
    "detect_inactive_status",
]
