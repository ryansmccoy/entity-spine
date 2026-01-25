"""
Ownership transaction enums.

STDLIB ONLY - NO PYDANTIC.
"""

from enum import Enum


class TransactionCode(str, Enum):
    """
    SEC Form 4 transaction codes.

    Maps to the transaction codes used in SEC ownership filings.
    """

    # Acquisition codes
    P = "P"  # Open market or private purchase
    A = "A"  # Grant, award, or other acquisition
    M = "M"  # Exercise/conversion of derivative security
    C = "C"  # Conversion of derivative security
    X = "X"  # Exercise of in-the-money derivative
    I = "I"  # Discretionary transaction (401k, etc.)
    G = "G"  # Gift
    W = "W"  # Acquisition or disposition by will or laws of descent

    # Disposition codes
    S = "S"  # Open market or private sale
    D = "D"  # Sale back to issuer
    F = "F"  # Payment of exercise price or tax liability by delivering securities
    L = "L"  # Small acquisition (less than $10,000)
    Z = "Z"  # Deposit into or withdrawal from voting trust

    # Other codes
    J = "J"  # Other acquisition or disposition
    K = "K"  # Equity swap or similar
    U = "U"  # Disposition pursuant to tender offer
    H = "H"  # Expiration of short derivative position
    O = "O"  # Exercise of out-of-the-money derivative
    E = "E"  # Expiration of long derivative position
    V = "V"  # Transaction voluntarily reported earlier than required

    OTHER = "other"
