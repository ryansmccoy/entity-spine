"""
Asset class metadata registry.

STDLIB ONLY - NO PYDANTIC.

Provides metadata, examples, and relationships for AssetClass enum values.
The enum remains the source of truth; this registry adds descriptive context.

v2.3.2 - Initial version
"""

from dataclasses import dataclass, field
from datetime import datetime

from entityspine.domain.enums.markets import AssetClass
from entityspine.domain.timestamps import utc_now


@dataclass(frozen=True, slots=True)
class AssetClassInfo:
    """
    Metadata for an asset class.
    
    Provides human-readable descriptions, examples, and relationships
    without creating a full domain entity.
    
    Attributes:
        asset_class: The AssetClass enum value.
        name: Human-readable name.
        description: Extended description.
        examples: Example instruments/products.
        parent: Parent asset class (for hierarchy).
        children: Child asset classes.
        typical_venues: Typical venue kinds where this trades.
        iso_cfi_prefix: ISO 10962 CFI code prefix if applicable.
    """
    
    asset_class: AssetClass
    name: str
    description: str
    examples: tuple[str, ...] = ()
    parent: AssetClass | None = None
    children: tuple[AssetClass, ...] = ()
    typical_venues: tuple[str, ...] = ()  # VenueKind values
    iso_cfi_prefix: str | None = None
    captured_at: datetime = field(default_factory=utc_now)


# =============================================================================
# Asset Class Registry
# =============================================================================

ASSET_CLASS_INFO: dict[AssetClass, AssetClassInfo] = {
    AssetClass.EQUITY: AssetClassInfo(
        asset_class=AssetClass.EQUITY,
        name="Equity",
        description="Ownership interests in corporations including common stock, preferred stock, ADRs, and ETFs.",
        examples=("Common Stock", "Preferred Stock", "ADR", "GDR", "ETF", "REIT", "Closed-End Fund"),
        children=(AssetClass.OPTIONS,),  # Equity derivatives
        typical_venues=("stock_exchange", "ecn", "ats", "dark_pool", "otc_market"),
        iso_cfi_prefix="E",
    ),
    
    AssetClass.FIXED_INCOME: AssetClassInfo(
        asset_class=AssetClass.FIXED_INCOME,
        name="Fixed Income",
        description="Debt instruments including government bonds, corporate bonds, municipal bonds, and structured products.",
        examples=(
            "Treasury Bond", "Treasury Note", "Treasury Bill",
            "Corporate Bond", "Municipal Bond", "Agency Bond",
            "MBS", "ABS", "CLO", "CDO",
        ),
        typical_venues=("bond_platform", "rates_venue", "idb", "otc_market"),
        iso_cfi_prefix="D",
    ),
    
    AssetClass.OPTIONS: AssetClassInfo(
        asset_class=AssetClass.OPTIONS,
        name="Options",
        description="Derivative contracts giving the right to buy/sell an underlying at a specified price.",
        examples=(
            "Equity Options", "Index Options", "ETF Options",
            "Flex Options", "LEAPS", "Weekly Options",
        ),
        parent=AssetClass.EQUITY,
        typical_venues=("options_exchange",),
        iso_cfi_prefix="O",
    ),
    
    AssetClass.FUTURES: AssetClassInfo(
        asset_class=AssetClass.FUTURES,
        name="Futures",
        description="Standardized contracts to buy/sell an asset at a future date and price.",
        examples=(
            "E-mini S&P 500", "Crude Oil Futures", "Gold Futures",
            "Treasury Futures", "Currency Futures", "VIX Futures",
        ),
        typical_venues=("futures_exchange", "commodity_exchange"),
        iso_cfi_prefix="F",
    ),
    
    AssetClass.FX: AssetClassInfo(
        asset_class=AssetClass.FX,
        name="Foreign Exchange",
        description="Currency pairs traded in spot, forward, and swap markets.",
        examples=(
            "EUR/USD Spot", "USD/JPY Forward", "GBP/USD Swap",
            "FX Options", "NDF",
        ),
        typical_venues=("fx_ecn", "fx_platform", "idb"),
    ),
    
    AssetClass.COMMODITIES: AssetClassInfo(
        asset_class=AssetClass.COMMODITIES,
        name="Commodities",
        description="Physical goods including energy, metals, and agricultural products.",
        examples=(
            "Crude Oil", "Natural Gas", "Gold", "Silver",
            "Copper", "Corn", "Wheat", "Soybeans", "Coffee",
        ),
        typical_venues=("commodity_exchange", "futures_exchange"),
    ),
    
    AssetClass.CRYPTO: AssetClassInfo(
        asset_class=AssetClass.CRYPTO,
        name="Cryptocurrency",
        description="Digital assets based on blockchain/distributed ledger technology.",
        examples=(
            "Bitcoin", "Ethereum", "Stablecoins",
            "Bitcoin ETF", "Crypto Futures",
        ),
        typical_venues=("crypto_exchange", "digital_asset_platform"),
    ),
    
    AssetClass.STRUCTURED_PRODUCTS: AssetClassInfo(
        asset_class=AssetClass.STRUCTURED_PRODUCTS,
        name="Structured Products",
        description="Pre-packaged investment strategies combining derivatives with other instruments.",
        examples=(
            "Structured Notes", "Principal Protected Notes",
            "Autocallables", "Reverse Convertibles",
        ),
        parent=AssetClass.FIXED_INCOME,
        typical_venues=("otc_market", "idb"),
    ),
    
    AssetClass.MONEY_MARKET: AssetClassInfo(
        asset_class=AssetClass.MONEY_MARKET,
        name="Money Market",
        description="Short-term, highly liquid debt instruments with maturities under one year.",
        examples=(
            "Commercial Paper", "T-Bills", "Repos",
            "Certificates of Deposit", "Bankers Acceptances",
        ),
        typical_venues=("idb", "otc_market"),
        iso_cfi_prefix="D",
    ),
    
    AssetClass.OTHER: AssetClassInfo(
        asset_class=AssetClass.OTHER,
        name="Other",
        description="Asset classes not fitting standard categories.",
        examples=("Insurance-Linked Securities", "Carbon Credits", "Water Rights"),
        typical_venues=(),
    ),
}


# =============================================================================
# Helper Functions
# =============================================================================


def get_asset_class_info(asset_class: AssetClass) -> AssetClassInfo:
    """
    Get metadata for an asset class.
    
    Args:
        asset_class: AssetClass enum value.
        
    Returns:
        AssetClassInfo with metadata.
        
    Raises:
        KeyError: If asset class not in registry.
    """
    return ASSET_CLASS_INFO[asset_class]


def get_asset_class_description(asset_class: AssetClass) -> str:
    """Get the description for an asset class."""
    return ASSET_CLASS_INFO.get(
        asset_class,
        AssetClassInfo(asset_class, asset_class.value, "No description available"),
    ).description


def get_asset_class_examples(asset_class: AssetClass) -> tuple[str, ...]:
    """Get example instruments for an asset class."""
    info = ASSET_CLASS_INFO.get(asset_class)
    return info.examples if info else ()


def get_typical_venues_for_asset_class(asset_class: AssetClass) -> tuple[str, ...]:
    """Get typical venue kinds for an asset class."""
    info = ASSET_CLASS_INFO.get(asset_class)
    return info.typical_venues if info else ()


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "AssetClassInfo",
    "ASSET_CLASS_INFO",
    "get_asset_class_info",
    "get_asset_class_description",
    "get_asset_class_examples",
    "get_typical_venues_for_asset_class",
]
