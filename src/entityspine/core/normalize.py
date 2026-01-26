"""
Name and identifier normalization utilities.

Used for consistent matching across different data sources.
"""

import re
import unicodedata

# Corporate suffixes to strip for matching
CORP_SUFFIXES: frozenset[str] = frozenset(
    {
        "inc",
        "inc.",
        "incorporated",
        "corp",
        "corp.",
        "corporation",
        "co",
        "co.",
        "company",
        "ltd",
        "ltd.",
        "limited",
        "llc",
        "l.l.c.",
        "llp",
        "l.l.p.",
        "lp",
        "l.p.",
        "plc",
        "p.l.c.",
        "sa",
        "s.a.",
        "ag",
        "a.g.",
        "nv",
        "n.v.",
        "bv",
        "b.v.",
        "gmbh",
        "g.m.b.h.",
        "ab",
        "oy",
        "oyj",
        "asa",
        "as",
        "se",
        "spa",
        "s.p.a.",
        "srl",
        "s.r.l.",
    }
)

# Noise words to remove
NOISE_WORDS: frozenset[str] = frozenset({"the", "a", "an", "of", "and", "&"})


def normalize_name(name: str) -> str:
    """
    Normalize company name for matching.

    Transformations:
    - Lowercase
    - Remove accents/diacritics
    - Replace & with "and"
    - Remove punctuation except hyphens
    - Remove corporate suffixes
    - Remove noise words
    - Collapse whitespace

    Args:
        name: Company name to normalize

    Returns:
        Normalized name string

    Example:
        >>> normalize_name("Apple Inc.")
        'apple'
        >>> normalize_name("The Procter & Gamble Company")
        'procter gamble'
        >>> normalize_name("Société Générale S.A.")
        'societe generale'
    """
    if not name:
        return ""

    result = name.lower()

    # Remove accents (NFD decomposition + strip combining marks)
    result = unicodedata.normalize("NFD", result)
    result = "".join(c for c in result if unicodedata.category(c) != "Mn")

    # Replace & with "and"
    result = result.replace("&", " and ")

    # Remove punctuation except hyphens and spaces
    result = re.sub(r"[^\w\s-]", " ", result)

    # Split into words
    words = result.split()

    # Remove suffixes and noise words
    words = [w for w in words if w not in CORP_SUFFIXES and w not in NOISE_WORDS]

    # Rejoin and collapse whitespace
    return " ".join(words).strip()


def normalize_cik(cik: str) -> str:
    """
    Normalize CIK to 10-digit zero-padded format.

    Args:
        cik: CIK in any format

    Returns:
        10-digit zero-padded CIK string

    Example:
        >>> normalize_cik("320193")
        '0000320193'
        >>> normalize_cik("0000320193")
        '0000320193'
    """
    # Remove any non-digit characters
    digits = re.sub(r"\D", "", cik)

    # Pad to 10 digits
    return digits.zfill(10)


def normalize_ticker(ticker: str) -> str:
    """
    Normalize ticker symbol to uppercase.

    Args:
        ticker: Ticker symbol

    Returns:
        Uppercase ticker string

    Example:
        >>> normalize_ticker("aapl")
        'AAPL'
        >>> normalize_ticker("BRK.B")
        'BRK.B'
    """
    return ticker.upper().strip()


def normalize_lei(lei: str) -> str | None:
    """
    Normalize and validate LEI (Legal Entity Identifier).

    LEI format: 20 alphanumeric characters
    - Characters 1-4: LOU (Local Operating Unit) prefix
    - Characters 5-18: Entity identifier
    - Characters 19-20: Check digits

    Args:
        lei: LEI to normalize

    Returns:
        Normalized LEI or None if invalid

    Example:
        >>> normalize_lei("5493001KJTIIGC8Y1R12")
        '5493001KJTIIGC8Y1R12'
    """
    # Remove whitespace and uppercase
    cleaned = lei.upper().strip().replace(" ", "").replace("-", "")

    # Must be exactly 20 alphanumeric characters
    if len(cleaned) != 20:
        return None

    if not cleaned.isalnum():
        return None

    return cleaned


def normalize_isin(isin: str) -> str | None:
    """
    Normalize and validate ISIN (International Securities Identification Number).

    ISIN format: 12 characters
    - Characters 1-2: ISO 3166-1 alpha-2 country code
    - Characters 3-11: NSIN (National Securities Identifying Number)
    - Character 12: Check digit

    Args:
        isin: ISIN to normalize

    Returns:
        Normalized ISIN or None if invalid

    Example:
        >>> normalize_isin("US0378331005")
        'US0378331005'
    """
    # Remove whitespace and uppercase
    cleaned = isin.upper().strip().replace(" ", "").replace("-", "")

    # Must be exactly 12 characters
    if len(cleaned) != 12:
        return None

    # First two characters must be letters (country code)
    if not cleaned[:2].isalpha():
        return None

    # Remaining characters must be alphanumeric
    if not cleaned[2:].isalnum():
        return None

    return cleaned


def normalize_cusip(cusip: str) -> str | None:
    """
    Normalize and validate CUSIP.

    CUSIP format: 9 characters
    - Characters 1-6: Issuer code
    - Characters 7-8: Issue number
    - Character 9: Check digit

    Args:
        cusip: CUSIP to normalize

    Returns:
        Normalized CUSIP or None if invalid

    Example:
        >>> normalize_cusip("037833100")
        '037833100'
    """
    # Remove whitespace and uppercase
    cleaned = cusip.upper().strip().replace(" ", "").replace("-", "")

    # Must be exactly 9 characters
    if len(cleaned) != 9:
        return None

    # Must be alphanumeric
    if not cleaned.isalnum():
        return None

    return cleaned
