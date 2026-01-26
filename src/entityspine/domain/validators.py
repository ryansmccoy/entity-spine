"""
Identifier validation and normalization (stdlib-only).

STDLIB ONLY - NO PYDANTIC.

This module provides:
- Identifier format normalization (CIK padding, uppercase, etc.)
- Identifier format validation (length, character sets)
- Scheme-scope rules (which schemes apply to which object types)

All business validation logic lives here. Pydantic wrappers must call these.
"""

import re
from collections.abc import Callable

from entityspine.domain.enums import IdentifierScope

# =============================================================================
# Scheme-to-Scope Mapping
# =============================================================================

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


# =============================================================================
# Normalization Functions
# =============================================================================


def normalize_cik(value: str | None) -> str | None:
    """
    Normalize CIK to 10-digit zero-padded format.

    Example:
        >>> normalize_cik("320193")
        '0000320193'
    """
    if value is None:
        return None
    cleaned = value.strip().lstrip("0") or "0"
    return cleaned.zfill(10)


def normalize_lei(value: str | None) -> str | None:
    """Normalize LEI to 20-character uppercase format."""
    if value is None:
        return None
    return value.strip().upper()


def normalize_isin(value: str | None) -> str | None:
    """Normalize ISIN to 12-character uppercase format."""
    if value is None:
        return None
    return value.strip().upper()


def normalize_cusip(value: str | None) -> str | None:
    """Normalize CUSIP to 9-character uppercase format."""
    if value is None:
        return None
    return value.strip().upper()


def normalize_sedol(value: str | None) -> str | None:
    """Normalize SEDOL to 7-character uppercase format."""
    if value is None:
        return None
    return value.strip().upper()


def normalize_figi(value: str | None) -> str | None:
    """Normalize FIGI to 12-character uppercase format."""
    if value is None:
        return None
    return value.strip().upper()


def normalize_ein(value: str | None) -> str | None:
    """Normalize EIN to 9-digit format (no hyphen)."""
    if value is None:
        return None
    return value.strip().replace("-", "")


def normalize_ticker(value: str) -> str:
    """
    Normalize ticker symbol.

    - Uppercase
    - Replace dashes with dots (BRK-B → BRK.B)
    """
    return value.strip().upper().replace("-", ".")


def normalize_mic(value: str | None) -> str | None:
    """Normalize MIC to 4-char uppercase."""
    if value is None:
        return None
    return value.strip().upper()


# =============================================================================
# Validation Patterns
# =============================================================================

_CIK_PATTERN = re.compile(r"^\d{10}$")
_LEI_PATTERN = re.compile(r"^[A-Z0-9]{20}$")
_ISIN_PATTERN = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")
_CUSIP_PATTERN = re.compile(r"^[A-Z0-9]{9}$")
_SEDOL_PATTERN = re.compile(r"^[A-Z0-9]{7}$")
_FIGI_PATTERN = re.compile(r"^BBG[A-Z0-9]{9}$")
_EIN_PATTERN = re.compile(r"^\d{9}$")
_MIC_PATTERN = re.compile(r"^[A-Z]{4}$")
_TICKER_PATTERN = re.compile(r"^[A-Z0-9.]{1,12}$")


# =============================================================================
# Validation Functions
# =============================================================================


def validate_cik(value: str) -> tuple[bool, str]:
    """Validate CIK format. Returns (is_valid, error_message)."""
    if not _CIK_PATTERN.match(value):
        return False, f"CIK must be exactly 10 digits, got: {value!r}"
    return True, ""


def validate_lei(value: str) -> tuple[bool, str]:
    """Validate LEI format (ISO 17442)."""
    if len(value) != 20:
        return False, f"LEI must be exactly 20 characters, got {len(value)}: {value!r}"
    if not _LEI_PATTERN.match(value):
        return False, f"LEI must be uppercase alphanumeric, got: {value!r}"
    return True, ""


def validate_isin(value: str) -> tuple[bool, str]:
    """Validate ISIN format (ISO 6166)."""
    if len(value) != 12:
        return False, f"ISIN must be exactly 12 characters, got {len(value)}: {value!r}"
    if not _ISIN_PATTERN.match(value):
        return False, f"ISIN format invalid (expected XX + 9 alnum + digit): {value!r}"
    return True, ""


def validate_cusip(value: str) -> tuple[bool, str]:
    """Validate CUSIP format."""
    if len(value) != 9:
        return False, f"CUSIP must be exactly 9 characters, got {len(value)}: {value!r}"
    if not _CUSIP_PATTERN.match(value):
        return False, f"CUSIP must be uppercase alphanumeric, got: {value!r}"
    return True, ""


def validate_sedol(value: str) -> tuple[bool, str]:
    """Validate SEDOL format."""
    if len(value) != 7:
        return False, f"SEDOL must be exactly 7 characters, got {len(value)}: {value!r}"
    if not _SEDOL_PATTERN.match(value):
        return False, f"SEDOL must be uppercase alphanumeric, got: {value!r}"
    return True, ""


def validate_figi(value: str) -> tuple[bool, str]:
    """Validate FIGI format."""
    if len(value) != 12:
        return False, f"FIGI must be exactly 12 characters, got {len(value)}: {value!r}"
    if not _FIGI_PATTERN.match(value):
        return False, f"FIGI must start with 'BBG' followed by 9 alnum chars, got: {value!r}"
    return True, ""


def validate_ein(value: str) -> tuple[bool, str]:
    """Validate EIN format."""
    if not _EIN_PATTERN.match(value):
        return False, f"EIN must be exactly 9 digits, got: {value!r}"
    return True, ""


def validate_mic(value: str) -> tuple[bool, str]:
    """Validate MIC format (ISO 10383)."""
    if not _MIC_PATTERN.match(value):
        return False, f"MIC must be exactly 4 uppercase letters, got: {value!r}"
    return True, ""


def validate_ticker(value: str) -> tuple[bool, str]:
    """Validate ticker format."""
    if not value:
        return False, "Ticker cannot be empty"
    if not _TICKER_PATTERN.match(value):
        return (
            False,
            f"Ticker must be 1-12 uppercase alphanumeric chars (dots allowed), got: {value!r}",
        )
    return True, ""


# =============================================================================
# Scheme-to-Validator Mapping
# =============================================================================

# Type alias for validator functions
Normalizer = Callable[[str | None], str | None]
Validator = Callable[[str], tuple[bool, str]]

SCHEME_VALIDATORS: dict[str, tuple[Normalizer, Validator]] = {
    "cik": (normalize_cik, validate_cik),
    "lei": (normalize_lei, validate_lei),
    "ein": (normalize_ein, validate_ein),
    "isin": (normalize_isin, validate_isin),
    "cusip": (normalize_cusip, validate_cusip),
    "sedol": (normalize_sedol, validate_sedol),
    "figi": (normalize_figi, validate_figi),
    "ticker": (lambda v: normalize_ticker(v) if v else None, validate_ticker),
}


# =============================================================================
# Combined Validation Utilities
# =============================================================================


def normalize_and_validate(scheme: str, value: str) -> tuple[str, list]:
    """
    Normalize and validate an identifier value for a given scheme.

    Returns:
        (normalized_value, list_of_errors)
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
    """Get the expected scope for a given identifier scheme."""
    return SCHEME_SCOPES.get(scheme.lower(), IdentifierScope.ANY)


def validate_scheme_scope(
    scheme: str,
    entity_id: str | None,
    security_id: str | None,
    listing_id: str | None,
) -> tuple[bool, str]:
    """
    Validate that a scheme is used with the correct target type.

    Returns:
        (is_valid, error_message)
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


def validate_exactly_one_target(
    entity_id: str | None,
    security_id: str | None,
    listing_id: str | None,
) -> tuple[bool, str]:
    """
    Validate that exactly one target ID is set.

    Returns:
        (is_valid, error_message)
    """
    targets = [entity_id, security_id, listing_id]
    non_null = [t for t in targets if t is not None]

    if len(non_null) == 0:
        return False, "Exactly one of entity_id, security_id, or listing_id must be set (got none)"
    if len(non_null) > 1:
        return False, (
            f"Exactly one of entity_id, security_id, or listing_id must be set. "
            f"Got: entity_id={entity_id}, security_id={security_id}, listing_id={listing_id}"
        )
    return True, ""


# =============================================================================
# Person Name Normalization
# =============================================================================


def normalize_person_name(value: str | None) -> str | None:
    """
    Normalize person name for matching.

    - Trim whitespace
    - Collapse multiple spaces to single space
    - Title case for display

    Example:
        >>> normalize_person_name("  john   doe  ")
        'John Doe'
    """
    if value is None:
        return None
    # Trim and collapse whitespace
    cleaned = " ".join(value.split())
    if not cleaned:
        return None
    # Title case for display
    return cleaned.title()


def normalize_person_name_for_search(value: str | None) -> str | None:
    """
    Normalize person name for search/matching.

    - Lowercase
    - Remove punctuation
    - Collapse whitespace

    Example:
        >>> normalize_person_name_for_search("John Q. Doe, Jr.")
        'john q doe jr'
    """
    if value is None:
        return None
    # Lowercase
    cleaned = value.lower()
    # Remove common punctuation (keep only alphanumeric and space)
    cleaned = re.sub(r"[^\w\s]", " ", cleaned)
    # Collapse whitespace
    cleaned = " ".join(cleaned.split())
    return cleaned if cleaned else None


# =============================================================================
# Address Normalization
# =============================================================================


def normalize_country_code(value: str | None) -> str | None:
    """
    Normalize country code to ISO 3166-1 alpha-2 uppercase.

    Example:
        >>> normalize_country_code("us")
        'US'
    """
    if value is None:
        return None
    cleaned = value.strip().upper()
    # Basic validation: must be 2 letters
    if len(cleaned) != 2 or not cleaned.isalpha():
        return cleaned  # Return as-is, let caller validate
    return cleaned


def normalize_region_code(value: str | None) -> str | None:
    """
    Normalize region/state code.

    Example:
        >>> normalize_region_code("ca")
        'CA'
    """
    if value is None:
        return None
    return value.strip().upper()


def normalize_postal_code(value: str | None) -> str | None:
    """
    Normalize postal/ZIP code.

    - Remove extra whitespace
    - Uppercase for countries that use letters

    Example:
        >>> normalize_postal_code(" 94105 ")
        '94105'
    """
    if value is None:
        return None
    cleaned = value.strip().upper()
    return cleaned if cleaned else None


def normalize_address_line(value: str | None) -> str | None:
    """
    Normalize address line for storage.

    - Trim whitespace
    - Collapse multiple spaces

    Example:
        >>> normalize_address_line("  123  Main St  ")
        '123 Main St'
    """
    if value is None:
        return None
    cleaned = " ".join(value.split())
    return cleaned if cleaned else None


def compute_address_hash(
    line1: str | None,
    line2: str | None,
    city: str | None,
    region: str | None,
    postal: str | None,
    country: str = "US",
) -> str:
    """
    Compute a hash for address matching/deduplication.

    Uses normalized, lowercase values for consistent matching.
    Returns a hex string suitable for indexing.
    """
    import hashlib

    # Normalize all parts to lowercase, stripped
    parts = [
        (line1 or "").lower().strip(),
        (line2 or "").lower().strip(),
        (city or "").lower().strip(),
        (region or "").upper().strip(),  # Keep region uppercase (state codes)
        (postal or "").upper().strip(),  # Keep postal uppercase
        (country or "US").upper().strip(),
    ]
    # Join with delimiter and hash
    canonical = "|".join(parts)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:32]


# =============================================================================
# Person Name Validation
# =============================================================================


def validate_person_name(value: str) -> tuple[bool, str]:
    """
    Validate person name.

    - Must not be empty
    - Must contain at least one alphabetic character

    Returns:
        (is_valid, error_message)
    """
    if not value or not value.strip():
        return False, "Person name cannot be empty"
    if not any(c.isalpha() for c in value):
        return False, f"Person name must contain at least one letter: {value!r}"
    return True, ""
