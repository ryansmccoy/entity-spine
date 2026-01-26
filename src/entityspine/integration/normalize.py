"""
Normalization utilities for SEC identifiers.

These functions standardize identifiers before storage to ensure
consistent deduplication and matching.
"""

from __future__ import annotations

import re


def normalize_cik(cik: str) -> str:
    """
    Normalize a CIK to 10-digit zero-padded format.

    The SEC uses 10-digit CIKs with leading zeros. This function
    ensures consistent formatting regardless of input format.

    Args:
        cik: CIK in any format (with/without leading zeros)

    Returns:
        10-digit zero-padded CIK string

    Examples:
        >>> normalize_cik("320193")
        '0000320193'
        >>> normalize_cik("0000320193")
        '0000320193'
        >>> normalize_cik("  320193  ")
        '0000320193'
    """
    if not cik:
        return ""

    # Strip whitespace and leading zeros, then pad
    cleaned = cik.strip().lstrip("0")
    if not cleaned:
        return "0000000000"

    # Ensure only digits
    if not cleaned.isdigit():
        raise ValueError(f"CIK must contain only digits: {cik!r}")

    return cleaned.zfill(10)


def normalize_ticker(ticker: str) -> str:
    """
    Normalize a ticker symbol to uppercase ASCII.

    Handles common variations like trailing class letters,
    exchange prefixes, and whitespace.

    Args:
        ticker: Ticker symbol in any case/format

    Returns:
        Uppercase normalized ticker

    Examples:
        >>> normalize_ticker("aapl")
        'AAPL'
        >>> normalize_ticker("BRK.B")
        'BRK.B'
        >>> normalize_ticker(" MSFT ")
        'MSFT'
    """
    if not ticker:
        return ""

    # Strip whitespace, uppercase
    normalized = ticker.strip().upper()

    # Remove any non-alphanumeric except dots (for BRK.A, etc.)
    normalized = re.sub(r"[^A-Z0-9.]", "", normalized)

    return normalized


def normalize_accession_number(accession: str) -> str:
    """
    Normalize SEC accession number to standard format.

    Accession numbers have format: XXXXXXXXXX-YY-NNNNNN
    (10-digit filer ID, 2-digit year, 6-digit sequence)

    Args:
        accession: Accession number with or without dashes

    Returns:
        Accession number in standard dash format

    Examples:
        >>> normalize_accession_number("0001045810-24-000029")
        '0001045810-24-000029'
        >>> normalize_accession_number("000104581024000029")
        '0001045810-24-000029'
    """
    if not accession:
        return ""

    # Remove all dashes and whitespace
    digits = re.sub(r"[\s-]", "", accession)

    if len(digits) != 18:
        raise ValueError(f"Accession number must be 18 digits: {accession!r}")

    # Format as XXXXXXXXXX-YY-NNNNNN
    return f"{digits[:10]}-{digits[10:12]}-{digits[12:]}"


def normalize_cusip(cusip: str) -> str:
    """
    Normalize CUSIP to 9-character uppercase format.

    CUSIPs are 9 characters: 6-char issuer, 2-char issue, 1-char check.

    Args:
        cusip: CUSIP identifier

    Returns:
        9-character uppercase CUSIP

    Examples:
        >>> normalize_cusip("67066g104")
        '67066G104'
        >>> normalize_cusip(" 67066G104 ")
        '67066G104'
    """
    if not cusip:
        return ""

    normalized = cusip.strip().upper()

    # Remove any spaces or dashes
    normalized = re.sub(r"[\s-]", "", normalized)

    if len(normalized) != 9:
        raise ValueError(f"CUSIP must be 9 characters: {cusip!r}")

    return normalized


def normalize_isin(isin: str) -> str:
    """
    Normalize ISIN to 12-character uppercase format.

    ISINs are 12 characters: 2-letter country, 9-char identifier, 1 check digit.

    Args:
        isin: ISIN identifier

    Returns:
        12-character uppercase ISIN

    Examples:
        >>> normalize_isin("us0378331005")
        'US0378331005'
    """
    if not isin:
        return ""

    normalized = isin.strip().upper()

    # Remove spaces
    normalized = re.sub(r"\s", "", normalized)

    if len(normalized) != 12:
        raise ValueError(f"ISIN must be 12 characters: {isin!r}")

    if not normalized[:2].isalpha():
        raise ValueError(f"ISIN must start with 2-letter country code: {isin!r}")

    return normalized
