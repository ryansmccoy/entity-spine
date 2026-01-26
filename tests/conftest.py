"""
Shared test fixtures for entityspine.

This module provides common fixtures used across all test modules.
Uses pytest fixtures for dependency injection.
"""

import json
import tempfile
from collections.abc import Generator
from datetime import date, datetime
from pathlib import Path

import pytest

# =============================================================================
# Temporary Files & Directories
# =============================================================================


@pytest.fixture
def temp_db() -> Generator[Path, None, None]:
    """
    Create temporary SQLite database file.

    Yields:
        Path to temporary database file.

    Example:
        >>> def test_something(temp_db):
        ...     store = SQLiteStore(temp_db)
    """
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    yield db_path
    db_path.unlink(missing_ok=True)


@pytest.fixture
def temp_json(tmp_path: Path) -> Path:
    """
    Create temporary JSON file path.

    Returns:
        Path for temporary JSON file.
    """
    return tmp_path / "company_tickers.json"


# =============================================================================
# Sample SEC Data
# =============================================================================


@pytest.fixture
def sample_sec_json() -> dict:
    """
    Sample SEC company_tickers.json data structure.

    Returns:
        Dict matching SEC JSON format.

    Note:
        This matches the real SEC JSON structure where keys are
        string indices ("0", "1", etc.) and values have cik_str,
        ticker, and title fields.
    """
    return {
        "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
        "1": {"cik_str": 789019, "ticker": "MSFT", "title": "MICROSOFT CORP"},
        "2": {"cik_str": 1318605, "ticker": "TSLA", "title": "Tesla, Inc."},
        "3": {"cik_str": 1067983, "ticker": "BRK-B", "title": "BERKSHIRE HATHAWAY INC"},
        "4": {"cik_str": 1018724, "ticker": "AMZN", "title": "AMAZON COM INC"},
        "5": {"cik_str": 1652044, "ticker": "GOOGL", "title": "Alphabet Inc."},
    }


@pytest.fixture
def sample_sec_json_file(sample_sec_json: dict, tmp_path: Path) -> Path:
    """
    Create sample SEC JSON file on disk.

    Args:
        sample_sec_json: Sample data dict.
        tmp_path: Pytest temporary path.

    Returns:
        Path to created JSON file.
    """
    json_path = tmp_path / "company_tickers.json"
    json_path.write_text(json.dumps(sample_sec_json))
    return json_path


# =============================================================================
# Sample Domain Objects
# =============================================================================


@pytest.fixture
def sample_entity_id() -> str:
    """Sample entity ULID."""
    return "01ARZ3NDEKTSV4RRFFQ69G5FAV"


@pytest.fixture
def sample_security_id() -> str:
    """Sample security ULID."""
    return "01SEC3NDEKTSV4RRFFQ69G5FAV"


@pytest.fixture
def sample_listing_id() -> str:
    """Sample listing ULID."""
    return "01LST3NDEKTSV4RRFFQ69G5FAV"


@pytest.fixture
def sample_claim_id() -> str:
    """Sample claim ULID."""
    return "01CLM3NDEKTSV4RRFFQ69G5FAV"


# =============================================================================
# Date/Time Fixtures
# =============================================================================


@pytest.fixture
def today() -> date:
    """Today's date for testing."""
    return date.today()


@pytest.fixture
def now() -> datetime:
    """Current datetime for testing."""
    return datetime.utcnow()


@pytest.fixture
def historical_date() -> date:
    """A historical date (1990) for temporal tests."""
    return date(1990, 6, 15)


@pytest.fixture
def future_date() -> date:
    """A future date for temporal tests."""
    return date(2030, 12, 31)


# =============================================================================
# Ticker Reuse Test Data
# =============================================================================


@pytest.fixture
def ticker_reuse_data() -> dict:
    """
    Data for testing ticker reuse scenarios.

    AAPL ticker history:
    - Before 1995: Company X (fictional)
    - After 1995: Apple Inc.

    This tests v2.2 point-in-time resolution.
    """
    return {
        "company_x": {
            "entity_id": "01CMPX000000000000000000",
            "name": "Company X (Defunct)",
            "cik": "0000999999",
        },
        "apple": {
            "entity_id": "01AAPL000000000000000000",
            "name": "Apple Inc.",
            "cik": "0000320193",
        },
        "listings": [
            {
                "listing_id": "01LST_X_AAPL",
                "security_id": "01SEC_X",
                "ticker": "AAPL",
                "valid_from": date(1980, 1, 1),
                "valid_to": date(1995, 6, 30),
            },
            {
                "listing_id": "01LST_AAPL_AAPL",
                "security_id": "01SEC_AAPL",
                "ticker": "AAPL",
                "valid_from": date(1995, 7, 1),
                "valid_to": None,
            },
        ],
    }


# =============================================================================
# Merge Test Data
# =============================================================================


@pytest.fixture
def merge_chain_data() -> dict:
    """
    Data for testing merge redirect chains.

    A → B → C (A merged into B, B merged into C)

    Getting A should return C (follow full chain).
    """
    return {
        "entity_a": {
            "entity_id": "01ENTA000000000000000000",
            "name": "Company A (Acquired)",
            "status": "merged",
            "merged_into_id": "01ENTB000000000000000000",
        },
        "entity_b": {
            "entity_id": "01ENTB000000000000000000",
            "name": "Company B (Acquired)",
            "status": "merged",
            "merged_into_id": "01ENTC000000000000000000",
        },
        "entity_c": {
            "entity_id": "01ENTC000000000000000000",
            "name": "Company C (Current)",
            "status": "active",
            "merged_into_id": None,
        },
    }


# =============================================================================
# Assertion Helpers
# =============================================================================


def assert_entity_has_no_ticker(entity) -> None:
    """
    Assert that entity does not have ticker attribute.

    v2.2 CRITICAL: Entity must NOT have ticker.

    Args:
        entity: Entity object to check.

    Raises:
        AssertionError: If entity has ticker attribute.
    """
    assert not hasattr(entity, "ticker"), "v2.2 violation: Entity has ticker attribute"
    # Check Pydantic model_fields
    if hasattr(entity, "model_fields"):
        assert "ticker" not in entity.model_fields, "v2.2 violation: Entity model has ticker field"


def assert_resolution_returns_result(result) -> None:
    """
    Assert that resolution returns ResolutionResult.

    v2.2 CRITICAL: resolve() must return ResolutionResult, not Entity.

    Args:
        result: Result from resolve().

    Raises:
        AssertionError: If result is not ResolutionResult.
    """
    from entityspine.adapters.pydantic import ResolutionResult

    assert isinstance(result, ResolutionResult), (
        f"v2.2 violation: resolve() returned {type(result).__name__}, expected ResolutionResult"
    )
    assert hasattr(result, "alternatives"), (
        "v2.2 violation: ResolutionResult missing alternatives list"
    )
    assert isinstance(result.candidates, list), "v2.2 violation: candidates is not a list"
