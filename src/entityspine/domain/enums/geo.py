"""
Geographic enums.

STDLIB ONLY - NO PYDANTIC.
"""

from enum import Enum


class GeoType(str, Enum):
    """
    Type of geographic entity.

    Used in Geo for different levels of geographic granularity.
    """

    COUNTRY = "country"  # ISO 3166-1 country
    STATE = "state"  # State/Province (ISO 3166-2)
    CITY = "city"  # City/Municipality
    REGION = "region"  # Other region (county, district)
    CONTINENT = "continent"  # Continent
    OTHER = "other"


class AddressType(str, Enum):
    """
    Type of address.

    Used in Address to categorize physical locations.
    """

    BUSINESS = "business"
    HEADQUARTERS = "headquarters"
    REGISTERED = "registered"
    MAILING = "mailing"
    PHYSICAL = "physical"
    BRANCH = "branch"
    LEGAL = "legal"
    RESIDENTIAL = "residential"
    OTHER = "other"
