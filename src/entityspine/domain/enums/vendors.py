"""
Vendor and data source enums.

STDLIB ONLY - NO PYDANTIC.
"""

from enum import Enum


class VendorNamespace(str, Enum):
    """
    Vendor/source namespaces for identifier claims.

    Enables multi-vendor crosswalks (Bloomberg vs FactSet vs Reuters, etc.)
    """

    # Regulatory sources
    SEC = "sec"
    GLEIF = "gleif"

    # Market data vendors
    BLOOMBERG = "bloomberg"
    FACTSET = "factset"
    REUTERS = "reuters"
    OPENFIGI = "openfigi"

    # Exchanges
    EXCHANGE = "exchange"

    # Internal
    USER = "user"
    INTERNAL = "internal"

    # Other
    OTHER = "other"
