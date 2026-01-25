"""
Base classes and utilities for EntitySpine sources.

STDLIB ONLY - NO PYDANTIC.

This module provides shared infrastructure for all Bronze/Silver/Gold sources:
- Base snapshot creation
- URL download with SSL fallback
- Content hashing
- Flexible date parsing
- Content decoding

All sources should use these utilities to ensure consistency and DRY.
"""

from __future__ import annotations

import hashlib
import logging
import ssl
import urllib.request
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from entityspine.domain.timestamps import utc_now

logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

DEFAULT_USER_AGENT = "EntitySpine/1.0 (Reference Data Fetcher)"
DEFAULT_TIMEOUT = 30


# =============================================================================
# Content Utilities
# =============================================================================


def compute_content_hash(content: bytes) -> str:
    """
    Compute SHA-256 hash of content.
    
    Args:
        content: Raw bytes content.
        
    Returns:
        Hex-encoded SHA-256 hash string.
    """
    return hashlib.sha256(content).hexdigest()


def decode_content(content: bytes, encodings: tuple[str, ...] = ("utf-8", "latin-1")) -> str:
    """
    Decode bytes content with encoding fallback.
    
    Tries encodings in order until one succeeds.
    
    Args:
        content: Raw bytes to decode.
        encodings: Tuple of encodings to try in order.
        
    Returns:
        Decoded string.
        
    Raises:
        UnicodeDecodeError: If all encodings fail.
    """
    for encoding in encodings:
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    # Last encoding without error handling
    return content.decode(encodings[-1])


# =============================================================================
# Date Parsing
# =============================================================================

# Common date formats encountered in reference data
DATE_FORMATS = (
    "%Y-%m-%d",
    "%Y%m%d",
    "%d-%b-%Y",
    "%d/%m/%Y",
    "%m/%d/%Y",
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
)


def parse_date_flexible(value: str, formats: tuple[str, ...] = DATE_FORMATS) -> date | None:
    """
    Parse date string with flexible format detection.
    
    Tries multiple date formats until one succeeds.
    
    Args:
        value: Date string to parse.
        formats: Tuple of strptime formats to try.
        
    Returns:
        Parsed date, or None if parsing fails.
    """
    if not value or not value.strip():
        return None
    
    value = value.strip()
    
    for fmt in formats:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    
    logger.debug(f"Could not parse date: {value}")
    return None


def parse_datetime_flexible(
    value: str,
    formats: tuple[str, ...] = DATE_FORMATS,
) -> datetime | None:
    """
    Parse datetime string with flexible format detection.
    
    Args:
        value: Datetime string to parse.
        formats: Tuple of strptime formats to try.
        
    Returns:
        Parsed datetime, or None if parsing fails.
    """
    if not value or not value.strip():
        return None
    
    value = value.strip()
    
    for fmt in formats:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    
    logger.debug(f"Could not parse datetime: {value}")
    return None


# =============================================================================
# HTTP Download
# =============================================================================


def download_url(
    url: str,
    user_agent: str = DEFAULT_USER_AGENT,
    timeout: int = DEFAULT_TIMEOUT,
    headers: dict[str, str] | None = None,
    ssl_fallback: bool = True,
) -> bytes:
    """
    Download content from URL with optional SSL fallback.
    
    Args:
        url: URL to download from.
        user_agent: User-Agent header value.
        timeout: Request timeout in seconds.
        headers: Additional headers to include.
        ssl_fallback: If True, retry with unverified SSL on certificate errors.
        
    Returns:
        Downloaded content as bytes.
        
    Raises:
        urllib.error.URLError: On network errors (after SSL fallback if enabled).
    """
    request_headers = {"User-Agent": user_agent}
    if headers:
        request_headers.update(headers)
    
    request = urllib.request.Request(url, headers=request_headers)
    
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read()
    except ssl.SSLCertVerificationError:
        if not ssl_fallback:
            raise
        
        logger.warning(
            f"SSL verification failed for {url}, retrying without verification"
        )
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        
        with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
            return response.read()


# =============================================================================
# Snapshot Utilities
# =============================================================================


def generate_snapshot_id(prefix: str, content_hash: str, captured_at: datetime | None = None) -> str:
    """
    Generate a snapshot ID from prefix and content hash.
    
    Format: {prefix}_{YYYYMMDD_HHMMSS}_{hash[:8]}
    
    Args:
        prefix: Source prefix (e.g., "iso10383", "gleif").
        content_hash: SHA-256 hash of content.
        captured_at: Capture timestamp (defaults to now).
        
    Returns:
        Formatted snapshot ID string.
    """
    if captured_at is None:
        captured_at = utc_now()
    
    timestamp_str = captured_at.strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{timestamp_str}_{content_hash[:8]}"


@dataclass(frozen=True, slots=True)
class BaseSnapshot:
    """
    Base class for Bronze layer snapshots.
    
    Provides common fields for all snapshot types.
    Subclasses should add source-specific fields.
    
    Attributes:
        snapshot_id: Unique identifier for this snapshot.
        source_url: URL the data was fetched from.
        content_hash: SHA-256 hash of content.
        content_size: Size in bytes.
        record_count: Number of records in snapshot.
        captured_at: When snapshot was captured.
    """
    snapshot_id: str
    source_url: str
    content_hash: str
    content_size: int
    record_count: int
    captured_at: datetime = field(default_factory=utc_now)


# =============================================================================
# CSV/TSV Utilities
# =============================================================================


def get_csv_field(
    row: dict[str, Any],
    *field_names: str,
    default: str | None = None,
) -> str | None:
    """
    Get field value from CSV row with multiple possible field names.
    
    Useful for handling CSV files with varying column names.
    
    Args:
        row: Dictionary row from csv.DictReader.
        *field_names: Possible field names to check in order.
        default: Default value if no field found.
        
    Returns:
        Field value or default.
    """
    for name in field_names:
        if name in row:
            value = row[name]
            if value is not None:
                return str(value).strip() if value else default
    return default


def normalize_csv_headers(headers: list[str]) -> list[str]:
    """
    Normalize CSV headers to consistent format.
    
    - Strips whitespace
    - Converts to lowercase
    - Replaces spaces/dashes with underscores
    
    Args:
        headers: List of header strings.
        
    Returns:
        Normalized headers.
    """
    normalized = []
    for h in headers:
        h = h.strip().lower()
        h = h.replace(" ", "_").replace("-", "_")
        normalized.append(h)
    return normalized
