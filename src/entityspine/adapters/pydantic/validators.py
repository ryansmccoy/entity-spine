"""
Identifier validation and normalization for EntitySpine v2.2.3.

This module provides:
- Identifier format normalization (CIK padding, uppercase, etc.)
- Identifier format validation (length, character sets)
- Scheme-scope rules (which schemes apply to which object types)

Decision Log:
- CIK: 10-digit zero-padded (SEC standard)
- LEI: 20 chars uppercase alphanumeric (ISO 17442)
- ISIN: 12 chars uppercase alphanumeric (ISO 6166)
- CUSIP: 9 chars uppercase alphanumeric
- SEDOL: 7 chars uppercase alphanumeric
- FIGI: 12 chars uppercase alphanumeric starting with BBG
- EIN: 9 digits, stored without hyphen
"""

import re
from enum import Enum


class VendorNamespace(str, Enum):
    """
    Vendor/source namespaces for identifier claims.

    This distinguishes WHERE an identifier came from, enabling
    multi-vendor crosswalks (Bloomberg vs FactSet vs Reuters, etc.)
    """

    # Regulatory sources
    SEC = "sec"  # SEC EDGAR
    GLEIF = "gleif"  # Global LEI Foundation

    # Market data vendors
    BLOOMBERG = "bloomberg"  # Bloomberg
    FACTSET = "factset"  # FactSet
    REUTERS = "reuters"  # Refinitiv/Reuters
    OPENFIGI = "openfigi"  # OpenFIGI

    # Exchanges
    EXCHANGE = "exchange"  # Exchange-provided data

    # Internal
    USER = "user"  # User-provided
    INTERNAL = "internal"  # Internal system

    # Other
    OTHER = "other"


class IdentifierScope(str, Enum):
    """
    Which object type an identifier scheme applies to.

    Enforced by IdentifierClaim validators.
    """

    ENTITY = "entity"  # CIK, LEI, EIN, DUNS
    SECURITY = "security"  # ISIN, CUSIP, SEDOL, FIGI
    LISTING = "listing"  # TICKER (exchange-specific)
    ANY = "any"  # INTERNAL, OTHER


# Scheme-to-scope mapping
SCHEME_SCOPES: dict[str, IdentifierScope] = {
    "cik": IdentifierScope.ENTITY,
    "lei": IdentifierScope.ENTITY,
    "ein": IdentifierScope.ENTITY,
    "duns": IdentifierScope.ENTITY,
    "isin": IdentifierScope.SECURITY,
    "cusip": IdentifierScope.SECURITY,
    "sedol": IdentifierScope.SECURITY,
    "figi": IdentifierScope.SECURITY,
    "ticker": IdentifierScope.LISTING,
    "ric": IdentifierScope.LISTING,
    "internal": IdentifierScope.ANY,
    "other": IdentifierScope.ANY,
}


# ============================================================================
# Normalization Functions
# ============================================================================


def normalize_cik(value: str | None) -> str | None:
    """
    Normalize CIK to 10-digit zero-padded format.

    Args:
        value: Raw CIK value (may have leading zeros, spaces)

    Returns:
        10-digit zero-padded CIK or None

    Example:
        >>> normalize_cik("320193")
        '0000320193'
        >>> normalize_cik("0000320193")
        '0000320193'
    """
    if value is None:
        return None
    # Strip whitespace and leading zeros, then pad
    cleaned = value.strip().lstrip("0") or "0"
    return cleaned.zfill(10)


def normalize_lei(value: str | None) -> str | None:
    """
    Normalize LEI to 20-character uppercase format.

    Args:
        value: Raw LEI value

    Returns:
        20-char uppercase LEI or None
    """
    if value is None:
        return None
    return value.strip().upper()


def normalize_isin(value: str | None) -> str | None:
    """
    Normalize ISIN to 12-character uppercase format.

    Args:
        value: Raw ISIN value

    Returns:
        12-char uppercase ISIN or None
    """
    if value is None:
        return None
    return value.strip().upper()


def normalize_cusip(value: str | None) -> str | None:
    """
    Normalize CUSIP to 9-character uppercase format.

    Args:
        value: Raw CUSIP value

    Returns:
        9-char uppercase CUSIP or None
    """
    if value is None:
        return None
    return value.strip().upper()


def normalize_sedol(value: str | None) -> str | None:
    """
    Normalize SEDOL to 7-character uppercase format.

    Args:
        value: Raw SEDOL value

    Returns:
        7-char uppercase SEDOL or None
    """
    if value is None:
        return None
    return value.strip().upper()


def normalize_figi(value: str | None) -> str | None:
    """
    Normalize FIGI to 12-character uppercase format.

    Args:
        value: Raw FIGI value

    Returns:
        12-char uppercase FIGI or None
    """
    if value is None:
        return None
    return value.strip().upper()


def normalize_ein(value: str | None) -> str | None:
    """
    Normalize EIN to 9-digit format (no hyphen).

    Args:
        value: Raw EIN value (may have hyphen: XX-XXXXXXX)

    Returns:
        9-digit EIN or None
    """
    if value is None:
        return None
    # Remove hyphen and whitespace
    return value.strip().replace("-", "")


def normalize_ticker(value: str) -> str:
    """
    Normalize ticker symbol.

    - Uppercase
    - Replace dashes with dots (BRK-B → BRK.B)
    - Strip whitespace

    Args:
        value: Raw ticker value

    Returns:
        Normalized ticker
    """
    return value.strip().upper().replace("-", ".")


def normalize_mic(value: str | None) -> str | None:
    """
    Normalize MIC (Market Identifier Code) to 4-char uppercase.

    Args:
        value: Raw MIC value

    Returns:
        4-char uppercase MIC or None
    """
    if value is None:
        return None
    return value.strip().upper()


# ============================================================================
# Validation Functions
# ============================================================================

# Patterns for validation
_CIK_PATTERN = re.compile(r"^\d{10}$")
_LEI_PATTERN = re.compile(r"^[A-Z0-9]{20}$")
_ISIN_PATTERN = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")
_CUSIP_PATTERN = re.compile(r"^[A-Z0-9]{9}$")
_SEDOL_PATTERN = re.compile(r"^[A-Z0-9]{7}$")
_FIGI_PATTERN = re.compile(r"^BBG[A-Z0-9]{9}$")
_EIN_PATTERN = re.compile(r"^\d{9}$")
_MIC_PATTERN = re.compile(r"^[A-Z]{4}$")
_TICKER_PATTERN = re.compile(r"^[A-Z0-9.]{1,12}$")


def validate_cik(value: str) -> tuple[bool, str]:
    """
    Validate CIK format.

    Args:
        value: Normalized CIK value

    Returns:
        (is_valid, error_message)
    """
    if not _CIK_PATTERN.match(value):
        return False, f"CIK must be exactly 10 digits, got: {value!r}"
    return True, ""


def validate_lei(value: str) -> tuple[bool, str]:
    """
    Validate LEI format (ISO 17442).

    Args:
        value: Normalized LEI value

    Returns:
        (is_valid, error_message)
    """
    if len(value) != 20:
        return False, f"LEI must be exactly 20 characters, got {len(value)}: {value!r}"
    if not _LEI_PATTERN.match(value):
        return False, f"LEI must be uppercase alphanumeric, got: {value!r}"
    return True, ""


def validate_isin(value: str) -> tuple[bool, str]:
    """
    Validate ISIN format (ISO 6166).

    Format: 2-char country + 9-char identifier + 1 check digit

    Args:
        value: Normalized ISIN value

    Returns:
        (is_valid, error_message)
    """
    if len(value) != 12:
        return False, f"ISIN must be exactly 12 characters, got {len(value)}: {value!r}"
    if not _ISIN_PATTERN.match(value):
        return False, f"ISIN format invalid (expected XX + 9 alnum + digit): {value!r}"
    return True, ""


def validate_cusip(value: str) -> tuple[bool, str]:
    """
    Validate CUSIP format.

    Args:
        value: Normalized CUSIP value

    Returns:
        (is_valid, error_message)
    """
    if len(value) != 9:
        return False, f"CUSIP must be exactly 9 characters, got {len(value)}: {value!r}"
    if not _CUSIP_PATTERN.match(value):
        return False, f"CUSIP must be uppercase alphanumeric, got: {value!r}"
    return True, ""


def validate_sedol(value: str) -> tuple[bool, str]:
    """
    Validate SEDOL format.

    Args:
        value: Normalized SEDOL value

    Returns:
        (is_valid, error_message)
    """
    if len(value) != 7:
        return False, f"SEDOL must be exactly 7 characters, got {len(value)}: {value!r}"
    if not _SEDOL_PATTERN.match(value):
        return False, f"SEDOL must be uppercase alphanumeric, got: {value!r}"
    return True, ""


def validate_figi(value: str) -> tuple[bool, str]:
    """
    Validate FIGI format.

    Format: BBG + 9 alphanumeric characters

    Args:
        value: Normalized FIGI value

    Returns:
        (is_valid, error_message)
    """
    if len(value) != 12:
        return False, f"FIGI must be exactly 12 characters, got {len(value)}: {value!r}"
    if not _FIGI_PATTERN.match(value):
        return False, f"FIGI must start with 'BBG' followed by 9 alnum chars, got: {value!r}"
    return True, ""


def validate_ein(value: str) -> tuple[bool, str]:
    """
    Validate EIN format.

    Args:
        value: Normalized EIN value (no hyphen)

    Returns:
        (is_valid, error_message)
    """
    if not _EIN_PATTERN.match(value):
        return False, f"EIN must be exactly 9 digits, got: {value!r}"
    return True, ""


def validate_mic(value: str) -> tuple[bool, str]:
    """
    Validate MIC format (ISO 10383).

    Args:
        value: Normalized MIC value

    Returns:
        (is_valid, error_message)
    """
    if not _MIC_PATTERN.match(value):
        return False, f"MIC must be exactly 4 uppercase letters, got: {value!r}"
    return True, ""


def validate_ticker(value: str) -> tuple[bool, str]:
    """
    Validate ticker format.

    Args:
        value: Normalized ticker value

    Returns:
        (is_valid, error_message)
    """
    if not value:
        return False, "Ticker cannot be empty"
    if not _TICKER_PATTERN.match(value):
        return (
            False,
            f"Ticker must be 1-12 uppercase alphanumeric chars (dots allowed), got: {value!r}",
        )
    return True, ""


# Mapping scheme to validator
SCHEME_VALIDATORS: dict[str, tuple[callable, callable]] = {
    "cik": (normalize_cik, validate_cik),
    "lei": (normalize_lei, validate_lei),
    "ein": (normalize_ein, validate_ein),
    "isin": (normalize_isin, validate_isin),
    "cusip": (normalize_cusip, validate_cusip),
    "sedol": (normalize_sedol, validate_sedol),
    "figi": (normalize_figi, validate_figi),
    "ticker": (normalize_ticker, validate_ticker),
}


def normalize_and_validate(scheme: str, value: str) -> tuple[str, list[str]]:
    """
    Normalize and validate an identifier value for a given scheme.

    Args:
        scheme: Identifier scheme (cik, lei, isin, etc.)
        value: Raw identifier value

    Returns:
        (normalized_value, list_of_errors)

    Example:
        >>> normalize_and_validate("cik", "320193")
        ('0000320193', [])
        >>> normalize_and_validate("lei", "short")
        ('SHORT', ['LEI must be exactly 20 characters, got 5: 'SHORT''])
    """
    errors = []
    scheme_lower = scheme.lower()

    if scheme_lower in SCHEME_VALIDATORS:
        normalizer, validator = SCHEME_VALIDATORS[scheme_lower]
        normalized = normalizer(value)
        if normalized:
            is_valid, error = validator(normalized)
            if not is_valid:
                errors.append(error)
            return normalized, errors

    # No specific validator, just return stripped uppercase
    return value.strip().upper(), errors


def get_scope_for_scheme(scheme: str) -> IdentifierScope:
    """
    Get the expected scope for a given identifier scheme.

    Args:
        scheme: Identifier scheme (cik, lei, isin, etc.)

    Returns:
        IdentifierScope indicating which object type this scheme applies to
    """
    return SCHEME_SCOPES.get(scheme.lower(), IdentifierScope.ANY)


def validate_scheme_scope(
    scheme: str,
    entity_id: str | None,
    security_id: str | None,
    listing_id: str | None,
) -> tuple[bool, str]:
    """
    Validate that a scheme is used with the correct target type.

    Args:
        scheme: Identifier scheme
        entity_id: Entity ID if claim is for entity
        security_id: Security ID if claim is for security
        listing_id: Listing ID if claim is for listing

    Returns:
        (is_valid, error_message)

    Example:
        >>> validate_scheme_scope("cik", "ent123", None, None)
        (True, "")
        >>> validate_scheme_scope("cik", None, "sec123", None)
        (False, "Scheme 'cik' requires entity_id but got security_id")
    """
    scope = get_scope_for_scheme(scheme)

    # Determine actual target
    if entity_id:
        actual = "entity_id"
        actual_scope = IdentifierScope.ENTITY
    elif security_id:
        actual = "security_id"
        actual_scope = IdentifierScope.SECURITY
    elif listing_id:
        actual = "listing_id"
        actual_scope = IdentifierScope.LISTING
    else:
        return False, "No target ID provided"

    # ANY scope allows any target
    if scope == IdentifierScope.ANY:
        return True, ""

    # Check scope match
    if scope != actual_scope:
        expected_id = f"{scope.value}_id"
        return False, f"Scheme '{scheme}' requires {expected_id} but got {actual}"

    return True, ""
