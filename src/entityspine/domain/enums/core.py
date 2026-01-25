"""
Core entity, security, and listing enums.

STDLIB ONLY - NO PYDANTIC.
"""

from enum import Enum


class EntityType(str, Enum):
    """
    Type of legal entity.

    Keep types BROAD and stable. Nuance (like "Subsidiary") should be
    modeled via relationships, not more entity types.
    """

    ORGANIZATION = "organization"  # General company/corporation
    PERSON = "person"  # Natural person
    GOVERNMENT = "government"  # Government body/agency
    FUND = "fund"  # Investment fund (mutual, hedge, etc.)
    TRUST = "trust"  # Trust structure
    PARTNERSHIP = "partnership"  # LP, LLP, general partnership
    SPV = "spv"  # Special Purpose Vehicle
    EXCHANGE = "exchange"  # Stock exchange / trading venue
    GEO = "geo"  # Geographic entity (country, state)
    UNKNOWN = "unknown"  # Unknown entity type


class EntityStatus(str, Enum):
    """Lifecycle status of an entity."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    MERGED = "merged"
    PROVISIONAL = "provisional"


class SecurityType(str, Enum):
    """Type of financial security."""

    COMMON_STOCK = "common_stock"
    PREFERRED_STOCK = "preferred_stock"
    ADR = "adr"
    ETF = "etf"
    BOND = "bond"
    WARRANT = "warrant"
    OPTION = "option"
    UNIT = "unit"
    REIT = "reit"
    OTHER = "other"


class SecurityStatus(str, Enum):
    """Lifecycle status of a security."""

    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELISTED = "delisted"
    MATURED = "matured"


class ListingStatus(str, Enum):
    """Lifecycle status of a listing."""

    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELISTED = "delisted"
