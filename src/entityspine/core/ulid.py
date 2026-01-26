"""
ULID (Universally Unique Lexicographically Sortable Identifier) generator.

Zero external dependencies - uses only Python stdlib.
ULIDs are 26 characters, sortable by time, and don't require coordination.

Format: TTTTTTTTTTRRRRRRRRRRRRRRR (26 chars)
- T: Timestamp (10 chars, 48 bits, milliseconds since Unix epoch)
- R: Randomness (16 chars, 80 bits)
"""

import random
import time

# Crockford's Base32 alphabet (excludes I, L, O, U to avoid confusion)
ENCODING = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
ENCODING_LEN = len(ENCODING)  # 32


def generate_ulid() -> str:
    """
    Generate a new ULID.

    Returns:
        26-character ULID string

    Example:
        >>> ulid = generate_ulid()
        >>> len(ulid)
        26
        >>> is_valid_ulid(ulid)
        True
    """
    # Timestamp component (milliseconds since Unix epoch)
    timestamp_ms = int(time.time() * 1000)

    # Encode timestamp (10 characters, most significant first)
    timestamp_chars: list[str] = []
    for _ in range(10):
        timestamp_chars.append(ENCODING[timestamp_ms % ENCODING_LEN])
        timestamp_ms //= ENCODING_LEN
    timestamp_part = "".join(reversed(timestamp_chars))

    # Random component (16 characters)
    random_part = "".join(random.choice(ENCODING) for _ in range(16))

    return timestamp_part + random_part


def ulid_timestamp(ulid: str) -> float:
    """
    Extract Unix timestamp from a ULID.

    Args:
        ulid: 26-character ULID string

    Returns:
        Unix timestamp in seconds (float)

    Raises:
        ValueError: If ULID is invalid
    """
    if not is_valid_ulid(ulid):
        raise ValueError(f"Invalid ULID: {ulid}")

    timestamp_part = ulid[:10].upper()
    timestamp_ms = 0

    for char in timestamp_part:
        idx = ENCODING.index(char)
        timestamp_ms = timestamp_ms * ENCODING_LEN + idx

    return timestamp_ms / 1000.0


def is_valid_ulid(value: str) -> bool:
    """
    Check if a string is a valid ULID.

    Args:
        value: String to validate

    Returns:
        True if valid ULID, False otherwise
    """
    if not isinstance(value, str):
        return False

    if len(value) != 26:
        return False

    return all(c.upper() in ENCODING for c in value)


def ulid_to_uuid(ulid: str) -> str:
    """
    Convert ULID to UUID format (for compatibility).

    Args:
        ulid: 26-character ULID string

    Returns:
        UUID string (36 characters with hyphens)
    """
    if not is_valid_ulid(ulid):
        raise ValueError(f"Invalid ULID: {ulid}")

    # Decode ULID to 128-bit integer
    ulid_upper = ulid.upper()
    value = 0
    for char in ulid_upper:
        value = value * ENCODING_LEN + ENCODING.index(char)

    # Format as UUID
    hex_str = f"{value:032x}"
    return f"{hex_str[:8]}-{hex_str[8:12]}-{hex_str[12:16]}-{hex_str[16:20]}-{hex_str[20:]}"
