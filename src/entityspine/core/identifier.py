"""
Identifier classification utilities for EntitySpine.

Supports detection and normalization of:
- Tickers (including class shares like BRK.B, BRK-B)
- CIKs (SEC Central Index Key)
- ULIDs (EntitySpine internal IDs)
- Scheme:Value pairs (e.g., isin:US0378331005)

CRITICAL: Standard ticker detection (len <= 5 and isalpha) fails for BRK.B.
This module uses regex patterns that support:
- Simple tickers: AAPL, MSFT, IBM
- Class shares: BRK.B, BRK-B, BF.A, BF-A
"""

import re
from enum import Enum
from typing import NamedTuple


class IdentifierType(Enum):
    """Types of identifiers supported by EntitySpine."""

    TICKER = "ticker"  # Stock ticker symbol
    CIK = "cik"  # SEC Central Index Key
    ENTITY_ID = "entity_id"  # ULID internal ID
    SCHEME_VALUE = "scheme_value"  # scheme:value format
    NAME = "name"  # Company name (default)


class ClassificationResult(NamedTuple):
    """Result of identifier classification."""

    identifier_type: IdentifierType
    original: str
    normalized: str
    scheme: str | None = None  # For scheme:value type


# Crockford's Base32 alphabet (used in ULIDs)
ULID_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"

# Ticker pattern: 1-5 letters, optional class suffix (dot or hyphen + single letter)
# Examples: AAPL, BRK.B, BRK-B, BF.A, GOOGL
TICKER_PATTERN = re.compile(
    r"^[A-Z]{1,5}(?:[.-][A-Z])?$",
    re.IGNORECASE,
)

# CIK pattern: 1-10 digits (SEC CIKs are max 10 digits)
CIK_PATTERN = re.compile(r"^\d{1,10}$")

# ULID pattern: exactly 26 Crockford Base32 characters
ULID_PATTERN = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$", re.IGNORECASE)

# Scheme:Value pattern (e.g., isin:US0378331005, lei:HWUPKR0MPOU8FGXBT394)
SCHEME_VALUE_PATTERN = re.compile(r"^([a-z_]+):(.+)$", re.IGNORECASE)


def looks_like_ticker(s: str) -> tuple[bool, str]:
    """
    Detect if string looks like a ticker, normalizing hyphen to dot.

    Args:
        s: String to check.

    Returns:
        Tuple of (is_ticker, normalized_value).
        If not a ticker, returns (False, original_string).

    Examples:
        >>> looks_like_ticker("AAPL")
        (True, 'AAPL')
        >>> looks_like_ticker("BRK-B")
        (True, 'BRK.B')
        >>> looks_like_ticker("BRK.B")
        (True, 'BRK.B')
        >>> looks_like_ticker("0000320193")
        (False, '0000320193')
        >>> looks_like_ticker("Apple Inc.")
        (False, 'Apple Inc.')
    """
    upper = s.upper().strip()

    # Max ticker length is 7 (5 letters + dot + class letter)
    if len(upper) > 7:
        return False, s

    # If all digits, it's a CIK
    if upper.replace(".", "").isdigit():
        return False, s

    # Normalize hyphen to dot for class shares
    normalized = upper.replace("-", ".")

    if TICKER_PATTERN.match(normalized):
        return True, normalized

    return False, s


def looks_like_cik(s: str) -> tuple[bool, str]:
    """
    Detect if string looks like a CIK, normalizing to 10-digit format.

    Args:
        s: String to check.

    Returns:
        Tuple of (is_cik, normalized_value).
        Normalized CIK is zero-padded to 10 digits.

    Examples:
        >>> looks_like_cik("320193")
        (True, '0000320193')
        >>> looks_like_cik("0000320193")
        (True, '0000320193')
        >>> looks_like_cik("AAPL")
        (False, 'AAPL')
    """
    stripped = s.strip()

    if CIK_PATTERN.match(stripped):
        # Zero-pad to 10 digits
        normalized = stripped.zfill(10)
        return True, normalized

    return False, s


def looks_like_ulid(s: str) -> bool:
    """
    Check if string is a valid ULID.

    Args:
        s: String to check.

    Returns:
        True if valid 26-character ULID.

    Examples:
        >>> looks_like_ulid("01ARZ3NDEKTSV4RRFFQ69G5FAV")
        True
        >>> looks_like_ulid("invalid")
        False
    """
    if len(s) != 26:
        return False

    return bool(ULID_PATTERN.match(s))


def parse_scheme_value(s: str) -> tuple[str, str] | None:
    """
    Parse scheme:value identifier format.

    Args:
        s: String to parse.

    Returns:
        Tuple of (scheme, value) if valid, None otherwise.

    Examples:
        >>> parse_scheme_value("isin:US0378331005")
        ('isin', 'US0378331005')
        >>> parse_scheme_value("lei:HWUPKR0MPOU8FGXBT394")
        ('lei', 'HWUPKR0MPOU8FGXBT394')
        >>> parse_scheme_value("AAPL")
        None
    """
    match = SCHEME_VALUE_PATTERN.match(s.strip())
    if match:
        scheme = match.group(1).lower()
        value = match.group(2)
        return scheme, value
    return None


def classify_identifier(s: str) -> ClassificationResult:
    """
    Classify an identifier string and return normalized form.

    Classification priority:
    1. ULID (26-character internal ID)
    2. Scheme:Value (explicit scheme)
    3. CIK (numeric)
    4. Ticker (1-5 letters, optional class)
    5. Name (default fallback)

    Args:
        s: Identifier string to classify.

    Returns:
        ClassificationResult with type, original, normalized, and optional scheme.

    Examples:
        >>> r = classify_identifier("AAPL")
        >>> r.identifier_type
        <IdentifierType.TICKER: 'ticker'>
        >>> r.normalized
        'AAPL'

        >>> r = classify_identifier("BRK-B")
        >>> r.normalized
        'BRK.B'

        >>> r = classify_identifier("320193")
        >>> r.identifier_type
        <IdentifierType.CIK: 'cik'>
        >>> r.normalized
        '0000320193'
    """
    original = s.strip()

    # Check ULID first (26 characters, very specific)
    if looks_like_ulid(original):
        return ClassificationResult(
            identifier_type=IdentifierType.ENTITY_ID,
            original=original,
            normalized=original.upper(),
        )

    # Check scheme:value format
    scheme_value = parse_scheme_value(original)
    if scheme_value:
        scheme, value = scheme_value
        return ClassificationResult(
            identifier_type=IdentifierType.SCHEME_VALUE,
            original=original,
            normalized=f"{scheme}:{value}",
            scheme=scheme,
        )

    # Check CIK (numeric)
    is_cik, cik_normalized = looks_like_cik(original)
    if is_cik:
        return ClassificationResult(
            identifier_type=IdentifierType.CIK,
            original=original,
            normalized=cik_normalized,
        )

    # Check ticker (letters + optional class)
    is_ticker, ticker_normalized = looks_like_ticker(original)
    if is_ticker:
        return ClassificationResult(
            identifier_type=IdentifierType.TICKER,
            original=original,
            normalized=ticker_normalized,
        )

    # Default to name
    return ClassificationResult(
        identifier_type=IdentifierType.NAME,
        original=original,
        normalized=original,
    )
