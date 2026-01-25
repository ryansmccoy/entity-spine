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
    # Entity-scoped
    "cik": IdentifierScope.ENTITY,
    "lei": IdentifierScope.ENTITY,
    "ein": IdentifierScope.ENTITY,
    "duns": IdentifierScope.ENTITY,
    "factset_entity_id": IdentifierScope.ENTITY,
    "factset_person_id": IdentifierScope.ENTITY,

    # Security-scoped
    "isin": IdentifierScope.SECURITY,
    "cusip": IdentifierScope.SECURITY,
    "sedol": IdentifierScope.SECURITY,
    "figi": IdentifierScope.SECURITY,
    "factset_security_id": IdentifierScope.SECURITY,

    # Listing-scoped
    "ticker": IdentifierScope.LISTING,
    "ric": IdentifierScope.LISTING,

    # Sanctions & Compliance (entity-scoped)
    "ofac_sdn": IdentifierScope.ENTITY,
    "ofac_cons": IdentifierScope.ENTITY,
    "bis_entity_list": IdentifierScope.ENTITY,
    "un_sanctions": IdentifierScope.ENTITY,
    "eu_sanctions": IdentifierScope.ENTITY,
    "uk_sanctions": IdentifierScope.ENTITY,
    "pep": IdentifierScope.ENTITY,
    "adverse_media": IdentifierScope.ENTITY,
    "watchlist": IdentifierScope.ENTITY,

    # Flexible
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
_MIC_PATTERN = re.compile(r"^[A-Z0-9]{4}$")  # ISO 10383: 4 alphanumeric
_TICKER_PATTERN = re.compile(r"^[A-Z0-9.]{1,12}$")
# Market infrastructure patterns (v2.3.1)
_CRD_PATTERN = re.compile(r"^\d+$")  # CRD numbers are numeric (variable length)
_MPID_PATTERN = re.compile(r"^[A-Z0-9]{4}$")  # FINRA MPID: 4 alphanumeric
_SEC_FILE_PATTERN = re.compile(r"^\d+-\d+$")  # e.g., "8-12345" or "0-12345"


# =============================================================================
# Validation Functions
# =============================================================================


def validate_cik(value: str, *, original: str | None = None) -> tuple[bool, str]:
    """
    Validate CIK format. Returns (is_valid, error_message).
    
    Args:
        value: Normalized CIK value to validate (10 digits).
        original: Original value before normalization (for better error messages).
    """
    if not _CIK_PATTERN.match(value):
        if original and original != value:
            return False, f"CIK must be exactly 10 digits. Original: {original!r}, normalized: {value!r}"
        return False, f"CIK must be exactly 10 digits, got: {value!r}"
    return True, ""


def validate_lei(value: str, *, original: str | None = None) -> tuple[bool, str]:
    """
    Validate LEI format (ISO 17442).
    
    Args:
        value: Normalized LEI value to validate (20 chars, uppercase alphanumeric).
        original: Original value before normalization (for better error messages).
    """
    if len(value) != 20:
        if original and original != value:
            return False, f"LEI must be exactly 20 characters, got {len(value)}. Original: {original!r}, normalized: {value!r}"
        return False, f"LEI must be exactly 20 characters, got {len(value)}: {value!r}"
    if not _LEI_PATTERN.match(value):
        if original and original != value:
            return False, f"LEI must be uppercase alphanumeric. Original: {original!r}, normalized: {value!r}"
        return False, f"LEI must be uppercase alphanumeric, got: {value!r}"
    return True, ""


def validate_isin(value: str, *, original: str | None = None) -> tuple[bool, str]:
    """
    Validate ISIN format (ISO 6166).
    
    Args:
        value: Normalized ISIN value to validate (12 chars).
        original: Original value before normalization (for better error messages).
    """
    if len(value) != 12:
        if original and original != value:
            return False, f"ISIN must be exactly 12 characters, got {len(value)}. Original: {original!r}, normalized: {value!r}"
        return False, f"ISIN must be exactly 12 characters, got {len(value)}: {value!r}"
    if not _ISIN_PATTERN.match(value):
        if original and original != value:
            return False, f"ISIN format invalid (expected XX + 9 alnum + digit). Original: {original!r}, normalized: {value!r}"
        return False, f"ISIN format invalid (expected XX + 9 alnum + digit): {value!r}"
    return True, ""


def validate_cusip(value: str, *, original: str | None = None) -> tuple[bool, str]:
    """
    Validate CUSIP format.
    
    Args:
        value: Normalized CUSIP value to validate (9 chars, uppercase alphanumeric).
        original: Original value before normalization (for better error messages).
    """
    if len(value) != 9:
        if original and original != value:
            return False, f"CUSIP must be exactly 9 characters, got {len(value)}. Original: {original!r}, normalized: {value!r}"
        return False, f"CUSIP must be exactly 9 characters, got {len(value)}: {value!r}"
    if not _CUSIP_PATTERN.match(value):
        if original and original != value:
            return False, f"CUSIP must be uppercase alphanumeric. Original: {original!r}, normalized: {value!r}"
        return False, f"CUSIP must be uppercase alphanumeric, got: {value!r}"
    return True, ""


def validate_sedol(value: str, *, original: str | None = None) -> tuple[bool, str]:
    """
    Validate SEDOL format.
    
    Args:
        value: Normalized SEDOL value to validate (7 chars, uppercase alphanumeric).
        original: Original value before normalization (for better error messages).
    """
    if len(value) != 7:
        if original and original != value:
            return False, f"SEDOL must be exactly 7 characters, got {len(value)}. Original: {original!r}, normalized: {value!r}"
        return False, f"SEDOL must be exactly 7 characters, got {len(value)}: {value!r}"
    if not _SEDOL_PATTERN.match(value):
        if original and original != value:
            return False, f"SEDOL must be uppercase alphanumeric. Original: {original!r}, normalized: {value!r}"
        return False, f"SEDOL must be uppercase alphanumeric, got: {value!r}"
    return True, ""


def validate_figi(value: str, *, original: str | None = None) -> tuple[bool, str]:
    """
    Validate FIGI format.
    
    Args:
        value: Normalized FIGI value to validate (12 chars, starts with BBG).
        original: Original value before normalization (for better error messages).
    """
    if len(value) != 12:
        if original and original != value:
            return False, f"FIGI must be exactly 12 characters, got {len(value)}. Original: {original!r}, normalized: {value!r}"
        return False, f"FIGI must be exactly 12 characters, got {len(value)}: {value!r}"
    if not _FIGI_PATTERN.match(value):
        if original and original != value:
            return False, f"FIGI must start with 'BBG' followed by 9 alnum chars. Original: {original!r}, normalized: {value!r}"
        return False, f"FIGI must start with 'BBG' followed by 9 alnum chars, got: {value!r}"
    return True, ""


def validate_ein(value: str, *, original: str | None = None) -> tuple[bool, str]:
    """
    Validate EIN format.
    
    Args:
        value: Normalized EIN value to validate (9 digits, no hyphen).
        original: Original value before normalization (for better error messages).
    """
    if not _EIN_PATTERN.match(value):
        if original and original != value:
            return False, f"EIN must be exactly 9 digits. Original: {original!r}, normalized: {value!r}"
        return False, f"EIN must be exactly 9 digits, got: {value!r}"
    return True, ""


def validate_mic(value: str, *, original: str | None = None) -> tuple[bool, str]:
    """
    Validate MIC format (ISO 10383).
    
    Args:
        value: Normalized MIC value to validate (4 chars, uppercase alphanumeric).
        original: Original value before normalization (for better error messages).
    """
    if not _MIC_PATTERN.match(value):
        if original and original != value:
            return False, f"MIC must be exactly 4 alphanumeric characters. Original: {original!r}, normalized: {value!r}"
        return False, f"MIC must be exactly 4 alphanumeric characters, got: {value!r}"
    return True, ""


def validate_ticker(value: str, *, original: str | None = None) -> tuple[bool, str]:
    """
    Validate ticker format.
    
    Args:
        value: Normalized ticker value to validate.
        original: Original value before normalization (for better error messages).
    """
    if not value:
        return False, "Ticker cannot be empty"
    if not _TICKER_PATTERN.match(value):
        if original and original != value:
            return (
                False,
                f"Ticker must be 1-12 uppercase alphanumeric chars (dots allowed). Original: {original!r}, normalized: {value!r}",
            )
        return (
            False,
            f"Ticker must be 1-12 uppercase alphanumeric chars (dots allowed), got: {value!r}",
        )
    return True, ""
    return True, ""


# =============================================================================
# Market Infrastructure Validators (v2.3.1)
# =============================================================================


def normalize_crd(value: str | None) -> str | None:
    """
    Normalize CRD number (FINRA Central Registration Depository).
    
    - Strip whitespace
    - Remove leading zeros (CRD numbers don't require zero-padding)
    
    Example:
        >>> normalize_crd("00361")
        '361'
    """
    if value is None:
        return None
    cleaned = value.strip().lstrip("0") or "0"
    return cleaned


def validate_crd(value: str, *, original: str | None = None) -> tuple[bool, str]:
    """
    Validate CRD number format.
    
    CRD numbers are numeric strings of variable length.
    
    Args:
        value: Normalized CRD value to validate.
        original: Original value before normalization (for better error messages).
    """
    if not value:
        return False, "CRD number cannot be empty"
    if not _CRD_PATTERN.match(value):
        if original and original != value:
            return False, f"CRD must be numeric digits only. Original: {original!r}, normalized: {value!r}"
        return False, f"CRD must be numeric digits only, got: {value!r}"
    return True, ""


def normalize_mpid(value: str | None) -> str | None:
    """
    Normalize Market Participant Identifier (MPID).
    
    - Strip whitespace
    - Uppercase
    
    Example:
        >>> normalize_mpid(" gsco ")
        'GSCO'
    """
    if value is None:
        return None
    return value.strip().upper()


def validate_mpid(value: str, *, original: str | None = None) -> tuple[bool, str]:
    """
    Validate MPID format (FINRA Market Participant Identifier).
    
    MPIDs are 4-character alphanumeric codes assigned by FINRA.
    
    Args:
        value: Normalized MPID value to validate.
        original: Original value before normalization (for better error messages).
    """
    if not value:
        return False, "MPID cannot be empty"
    if not _MPID_PATTERN.match(value):
        if original and original != value:
            return False, f"MPID must be exactly 4 alphanumeric characters. Original: {original!r}, normalized: {value!r}"
        return False, f"MPID must be exactly 4 alphanumeric characters, got: {value!r}"
    return True, ""


def normalize_sec_file_number(value: str | None) -> str | None:
    """
    Normalize SEC file number.
    
    - Strip whitespace
    - Remove leading zeros from the sequence portion
    
    Example:
        >>> normalize_sec_file_number(" 8-00129 ")
        '8-129'
    """
    if value is None:
        return None
    cleaned = value.strip()
    if "-" in cleaned:
        prefix, suffix = cleaned.split("-", 1)
        suffix = suffix.lstrip("0") or "0"
        return f"{prefix}-{suffix}"
    return cleaned


def validate_sec_file_number(value: str, *, original: str | None = None) -> tuple[bool, str]:
    """
    Validate SEC file number format.
    
    Format is typically "prefix-number" (e.g., "8-12345" for BD, "0-12345" for IA).
    
    Args:
        value: Normalized SEC file number to validate.
        original: Original value before normalization (for better error messages).
    """
    if not value:
        return False, "SEC file number cannot be empty"
    if not _SEC_FILE_PATTERN.match(value):
        if original and original != value:
            return False, f"SEC file number must be in format 'X-NNNNN'. Original: {original!r}, normalized: {value!r}"
        return False, f"SEC file number must be in format 'X-NNNNN', got: {value!r}"
    return True, ""


# =============================================================================
# Scheme-to-Validator Mapping
# =============================================================================

# Type alias for validator functions
# Validators accept (value, *, original=None) for better error messages
Normalizer = Callable[[str | None], str | None]
Validator = Callable[[str], tuple[bool, str]]  # For backward compatibility

SCHEME_VALIDATORS: dict[str, tuple[Normalizer, Validator]] = {
    "cik": (normalize_cik, validate_cik),
    "lei": (normalize_lei, validate_lei),
    "ein": (normalize_ein, validate_ein),
    "isin": (normalize_isin, validate_isin),
    "cusip": (normalize_cusip, validate_cusip),
    "sedol": (normalize_sedol, validate_sedol),
    "figi": (normalize_figi, validate_figi),
    "ticker": (lambda v: normalize_ticker(v) if v else None, validate_ticker),
    # Market infrastructure identifiers (v2.3.1)
    "mic": (normalize_mic, validate_mic),
    "crd": (normalize_crd, validate_crd),
    "mpid": (normalize_mpid, validate_mpid),
    "sec_file": (normalize_sec_file_number, validate_sec_file_number),
}


# =============================================================================
# Combined Validation Utilities
# =============================================================================


def normalize_and_validate(
    scheme: str,
    value: str | None,
) -> tuple[str | None, list[str]]:
    """
    Normalize and validate an identifier value by scheme.
    
    This helper uses the new validator signatures that include original values
    in error messages for better debugging.
    
    Args:
        scheme: Identifier scheme (e.g., "cik", "lei", "mic").
        value: Raw identifier value.
        
    Returns:
        Tuple of (normalized_value, list_of_errors).
        
    Example:
        >>> normalize_and_validate("cik", "  320193  ")
        ('0000320193', [])
        >>> normalize_and_validate("cik", "abc")
        ('0000000abc', ["CIK must be exactly 10 digits. Original: 'abc', normalized: '0000000abc'"])
    """
    errors: list[str] = []

    if value is None:
        return None, errors

    scheme_lower = scheme.lower()

    if scheme_lower not in SCHEME_VALIDATORS:
        # No specific validator, just return stripped uppercase
        return value.strip().upper(), errors

    normalizer, validator = SCHEME_VALIDATORS[scheme_lower]
    normalized = normalizer(value)

    if normalized is None:
        return None, errors

    # Call validator with original for better error messages
    is_valid, error = validator(normalized, original=value)
    if not is_valid:
        errors.append(error)

    return normalized, errors


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
