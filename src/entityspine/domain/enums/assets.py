"""
Asset, contract, product, and brand enums.

STDLIB ONLY - NO PYDANTIC.
"""

from enum import Enum


class AssetType(str, Enum):
    """
    Type of physical/tangible asset.

    Used in Asset nodes for categorizing physical assets.
    """

    FACILITY = "facility"  # Manufacturing facility, office
    DATA_CENTER = "data_center"  # Data center
    VESSEL = "vessel"  # Ship, boat
    AIRCRAFT = "aircraft"  # Airplane, helicopter
    PLANT = "plant"  # Industrial plant
    PROPERTY = "property"  # Real estate property
    EQUIPMENT = "equipment"  # Major equipment
    VEHICLE = "vehicle"  # Land vehicles
    INVENTORY = "inventory"  # Significant inventory
    INTELLECTUAL_PROPERTY = "ip"  # Patents, trademarks (non-physical)
    OTHER = "other"


class AssetStatus(str, Enum):
    """Lifecycle status of an asset."""

    ACTIVE = "active"  # In operation
    INACTIVE = "inactive"  # Idle/mothballed
    UNDER_CONSTRUCTION = "under_construction"
    DISPOSED = "disposed"  # Sold/decommissioned
    LEASED_OUT = "leased_out"  # Leased to another party
    OTHER = "other"


class ContractType(str, Enum):
    """
    Type of legal contract/agreement.

    Used in Contract nodes for categorizing agreements.
    """

    CREDIT_FACILITY = "credit_facility"  # Loan/credit agreement
    LEASE = "lease"  # Property/equipment lease
    MATERIAL_AGREEMENT = "material_agreement"  # 8-K material contract
    SUPPLY_AGREEMENT = "supply"  # Supply/procurement
    LICENSE = "license"  # License agreement
    EMPLOYMENT = "employment"  # Employment contract
    MERGER_AGREEMENT = "merger"  # M&A agreement
    JOINT_VENTURE = "joint_venture"  # JV agreement
    SERVICE_AGREEMENT = "service"  # Service contract
    DISTRIBUTION = "distribution"  # Distribution agreement
    SETTLEMENT = "settlement"  # Legal settlement
    OTHER = "other"


class ContractStatus(str, Enum):
    """Lifecycle status of a contract."""

    ACTIVE = "active"
    EXPIRED = "expired"
    TERMINATED = "terminated"
    PENDING = "pending"
    UNDER_NEGOTIATION = "negotiation"
    AMENDED = "amended"
    OTHER = "other"


class ProductType(str, Enum):
    """
    Type of product or service.

    Used in Product nodes for categorizing products.
    """

    DRUG = "drug"  # Pharmaceutical drug
    DEVICE = "device"  # Medical device
    SOFTWARE = "software"  # Software product
    SERVICE = "service"  # Service offering
    CONSUMER_GOOD = "consumer_good"  # Consumer product
    INDUSTRIAL_GOOD = "industrial"  # Industrial product
    FINANCIAL_PRODUCT = "financial"  # Financial product (not security)
    FOOD_BEVERAGE = "food_beverage"  # Food & beverage
    VEHICLE = "vehicle"  # Vehicle product
    OTHER = "other"


class ProductStatus(str, Enum):
    """Lifecycle status of a product."""

    ACTIVE = "active"  # On market
    DEVELOPMENT = "development"  # In development
    DISCONTINUED = "discontinued"  # No longer sold
    RECALLED = "recalled"  # Product recall
    PENDING_APPROVAL = "pending"  # Awaiting regulatory approval
    OTHER = "other"
