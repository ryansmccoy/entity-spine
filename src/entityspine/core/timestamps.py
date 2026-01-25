"""
UTC timestamp utilities for EntitySpine.

All timestamps in EntitySpine MUST be timezone-aware UTC.
This module provides helpers to ensure consistency.

NEVER use:
- datetime.now()      → Returns naive datetime
- datetime.utcnow()   → Returns naive datetime (deprecated in 3.12)

ALWAYS use:
- utc_now()           → Timezone-aware UTC datetime
- to_iso8601(dt)      → ISO-8601 string with Z suffix
"""

from datetime import UTC, datetime


def utc_now() -> datetime:
    """
    Get current UTC timestamp (timezone-aware).

    Returns:
        datetime: Current UTC time with tzinfo set to timezone.utc.

    Example:
        >>> ts = utc_now()
        >>> ts.tzinfo is not None
        True
        >>> ts.tzinfo == timezone.utc
        True
    """
    return datetime.now(UTC)


def to_iso8601(dt: datetime) -> str:
    """
    Convert datetime to ISO-8601 string with Z suffix.

    If the datetime is naive (no tzinfo), assumes UTC.

    Args:
        dt: Datetime to convert.

    Returns:
        ISO-8601 formatted string (e.g., "2024-01-15T14:30:00Z").

    Example:
        >>> from datetime import datetime, timezone
        >>> dt = datetime(2024, 1, 15, 14, 30, 0, tzinfo=timezone.utc)
        >>> to_iso8601(dt)
        '2024-01-15T14:30:00Z'
    """
    if dt.tzinfo is None:
        # Assume naive datetime is UTC
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def from_iso8601(s: str) -> datetime:
    """
    Parse ISO-8601 string to timezone-aware UTC datetime.

    Handles both 'Z' suffix and explicit timezone offsets.

    Args:
        s: ISO-8601 formatted string.

    Returns:
        Timezone-aware UTC datetime.

    Example:
        >>> dt = from_iso8601("2024-01-15T14:30:00Z")
        >>> dt.tzinfo is not None
        True
    """
    # Handle Z suffix
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"

    dt = datetime.fromisoformat(s)

    # Ensure UTC
    dt = dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)

    return dt


def ensure_utc(dt: datetime | None) -> datetime | None:
    """
    Ensure datetime is timezone-aware UTC.

    Args:
        dt: Datetime to check/convert, or None.

    Returns:
        Timezone-aware UTC datetime, or None if input was None.

    Raises:
        ValueError: If datetime is naive.
    """
    if dt is None:
        return None

    if dt.tzinfo is None:
        raise ValueError(
            "Naive datetime not allowed. Use utc_now() or provide timezone-aware datetime."
        )

    return dt.astimezone(UTC)
