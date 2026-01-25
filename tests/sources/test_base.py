"""
Tests for entityspine.sources.base module.

STDLIB ONLY - NO PYDANTIC.
"""

import datetime
from dataclasses import dataclass, field

import pytest

from entityspine.sources.base import (
    BaseSnapshot,
    compute_content_hash,
    decode_content,
    download_url,
    generate_snapshot_id,
    parse_date_flexible,
    parse_datetime_flexible,
    get_csv_field,
    normalize_csv_headers,
    DATE_FORMATS,
)
from entityspine.domain.timestamps import utc_now


class TestComputeContentHash:
    """Tests for compute_content_hash function."""
    
    def test_hash_empty_content(self):
        """Empty content should return valid SHA-256 hash."""
        result = compute_content_hash(b"")
        assert len(result) == 64  # SHA-256 is 64 hex chars
        # Known hash for empty string
        assert result == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    
    def test_hash_simple_content(self):
        """Simple content should hash consistently."""
        content = b"hello world"
        result1 = compute_content_hash(content)
        result2 = compute_content_hash(content)
        assert result1 == result2
        assert len(result1) == 64
    
    def test_hash_different_content(self):
        """Different content should produce different hashes."""
        hash1 = compute_content_hash(b"abc")
        hash2 = compute_content_hash(b"abd")
        assert hash1 != hash2


class TestDecodeContent:
    """Tests for decode_content function."""
    
    def test_decode_utf8(self):
        """UTF-8 content should decode correctly."""
        content = "Hello 世界".encode("utf-8")
        result = decode_content(content)
        assert result == "Hello 世界"
    
    def test_decode_latin1_fallback(self):
        """Latin-1 content should decode with fallback."""
        content = "Café".encode("latin-1")
        # UTF-8 decode will fail, should fall back to latin-1
        result = decode_content(content, encodings=("utf-8", "latin-1"))
        assert "Caf" in result  # May have encoding differences
    
    def test_decode_custom_encodings(self):
        """Custom encoding order should work."""
        content = b"simple ascii"
        result = decode_content(content, encodings=("ascii", "utf-8"))
        assert result == "simple ascii"


class TestParseDateFlexible:
    """Tests for parse_date_flexible function."""
    
    def test_parse_iso_format(self):
        """ISO format YYYY-MM-DD should parse."""
        result = parse_date_flexible("2024-01-15")
        assert result == datetime.date(2024, 1, 15)
    
    def test_parse_compact_format(self):
        """Compact format YYYYMMDD should parse."""
        result = parse_date_flexible("20240115")
        assert result == datetime.date(2024, 1, 15)
    
    def test_parse_european_format(self):
        """European format DD/MM/YYYY should parse."""
        result = parse_date_flexible("15/01/2024")
        assert result == datetime.date(2024, 1, 15)
    
    def test_parse_us_format(self):
        """US format MM/DD/YYYY should parse."""
        result = parse_date_flexible("01/15/2024")
        assert result == datetime.date(2024, 1, 15)
    
    def test_parse_empty_returns_none(self):
        """Empty string should return None."""
        assert parse_date_flexible("") is None
        assert parse_date_flexible("   ") is None
    
    def test_parse_invalid_returns_none(self):
        """Invalid date should return None."""
        assert parse_date_flexible("not-a-date") is None
        assert parse_date_flexible("13/45/2024") is None


class TestParseDatetimeFlexible:
    """Tests for parse_datetime_flexible function."""
    
    def test_parse_iso_datetime(self):
        """ISO datetime with T separator should parse."""
        result = parse_datetime_flexible("2024-01-15T10:30:00")
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15
        assert result.hour == 10
    
    def test_parse_iso_datetime_utc(self):
        """ISO datetime with Z suffix should parse."""
        result = parse_datetime_flexible("2024-01-15T10:30:00Z")
        assert result is not None
        assert result.year == 2024


class TestGenerateSnapshotId:
    """Tests for generate_snapshot_id function."""
    
    def test_basic_id_generation(self):
        """Should generate properly formatted ID."""
        content_hash = "abc123def456"
        captured_at = datetime.datetime(2024, 1, 15, 10, 30, 45)
        
        result = generate_snapshot_id("iso10383", content_hash, captured_at)
        
        assert result == "iso10383_20240115_103045_abc123de"
    
    def test_uses_hash_prefix(self):
        """Should use first 8 chars of hash."""
        result = generate_snapshot_id("test", "abcdefghijklmnop")
        assert "abcdefgh" in result
        assert "ijklmnop" not in result
    
    def test_default_timestamp(self):
        """Should use current time if not specified."""
        result = generate_snapshot_id("test", "abc123")
        assert "test_" in result


class TestBaseSnapshot:
    """Tests for BaseSnapshot dataclass."""
    
    def test_create_snapshot(self):
        """Should create a valid snapshot."""
        snap = BaseSnapshot(
            snapshot_id="test_123",
            source_url="https://example.com",
            content_hash="abc123",
            content_size=1000,
            record_count=50,
        )
        assert snap.snapshot_id == "test_123"
        assert snap.source_url == "https://example.com"
        assert snap.content_hash == "abc123"
        assert snap.content_size == 1000
        assert snap.record_count == 50
    
    def test_snapshot_is_frozen(self):
        """Snapshot should be immutable."""
        snap = BaseSnapshot(
            snapshot_id="test_123",
            source_url="https://example.com",
            content_hash="abc123",
            content_size=1000,
            record_count=50,
        )
        with pytest.raises(Exception):  # FrozenInstanceError
            snap.snapshot_id = "modified"  # type: ignore


class TestGetCsvField:
    """Tests for get_csv_field function."""
    
    def test_get_existing_field(self):
        """Should return field value if exists."""
        row = {"name": "Test", "value": "123"}
        assert get_csv_field(row, "name") == "Test"
    
    def test_get_with_multiple_names(self):
        """Should try multiple field names."""
        row = {"Name": "Test", "value": "123"}
        result = get_csv_field(row, "name", "Name", "NAME")
        assert result == "Test"
    
    def test_get_missing_field(self):
        """Should return None if field missing."""
        row = {"other": "Test"}
        assert get_csv_field(row, "name") is None
    
    def test_get_with_default(self):
        """Should return default if field missing."""
        row = {"other": "Test"}
        assert get_csv_field(row, "name", default="N/A") == "N/A"
    
    def test_strips_whitespace(self):
        """Should strip whitespace from values."""
        row = {"name": "  Test  "}
        assert get_csv_field(row, "name") == "Test"


class TestNormalizeCsvHeaders:
    """Tests for normalize_csv_headers function."""
    
    def test_lowercase(self):
        """Should convert to lowercase."""
        headers = ["NAME", "Value", "TYPE"]
        result = normalize_csv_headers(headers)
        assert result == ["name", "value", "type"]
    
    def test_replace_spaces(self):
        """Should replace spaces with underscores."""
        headers = ["First Name", "Last Name"]
        result = normalize_csv_headers(headers)
        assert result == ["first_name", "last_name"]
    
    def test_replace_dashes(self):
        """Should replace dashes with underscores."""
        headers = ["mic-code", "entity-type"]
        result = normalize_csv_headers(headers)
        assert result == ["mic_code", "entity_type"]
    
    def test_strip_whitespace(self):
        """Should strip leading/trailing whitespace."""
        headers = ["  name  ", " value "]
        result = normalize_csv_headers(headers)
        assert result == ["name", "value"]
