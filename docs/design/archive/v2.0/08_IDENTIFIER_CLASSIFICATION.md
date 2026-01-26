# EntitySpine Identifier Classification

**Status**: Normative  
**Audience**: Implementers

---

## Table of Contents

1. [Overview](#overview)
2. [Identifier Types](#identifier-types)
3. [Improved Ticker Detection](#improved-ticker-detection)
4. [Classification Logic](#classification-logic)
5. [Testing Requirements](#testing-requirements)
6. [Decision Log](#decision-log)

---

## Overview

EntitySpine must classify input strings to determine:
1. What **type** of identifier was provided
2. How to **route** resolution (CIK lookup vs ticker search vs alias search)
3. What **confidence level** to assign

### The Problem with Naive Detection

```python
# ❌ BROKEN: Misses valid tickers
def _looks_like_ticker(s: str) -> bool:
    return len(s) <= 5 and s.isalpha()

# Fails for:
# - "BRK.B" (dot separator)
# - "BRK-B" (hyphen separator)
# - "META1" (digits)
# - "GOOGL" (5 chars but OK)
# - "123456" (CIK without leading zeros)
```

---

## Identifier Types

### Type Enumeration

```python
from enum import Enum, auto

class IdentifierType(Enum):
    """Classification of identifier input."""
    
    # SEC Central Index Key (always 10 digits, zero-padded)
    CIK = auto()
    
    # Stock ticker (exchange-listed symbol)
    TICKER = auto()
    
    # EntitySpine internal ID (ULID format)
    ENTITY_ID = auto()
    
    # Company name or alias
    NAME = auto()
    
    # Known identifier scheme (ISIN, CUSIP, LEI, etc.)
    SCHEME_VALUE = auto()
    
    # Cannot determine type
    UNKNOWN = auto()
```

### Classification Result

```python
@dataclass(frozen=True, slots=True)
class ClassificationResult:
    """Result of identifier classification."""
    
    identifier_type: IdentifierType
    normalized_value: str  # Cleaned/normalized form
    original_value: str    # As provided by user
    confidence: float      # 0.0-1.0
    scheme: str | None = None  # For SCHEME_VALUE type
```

---

## Improved Ticker Detection

### Ticker Characteristics

Valid tickers can be:
- 1-5 characters (most US exchanges)
- 1-6 characters (some international)
- Contain letters (always)
- Contain digits (sometimes): `META1`, `3M` (hypothetical)
- Contain separators: `.` or `-` for share classes

### Real-World Examples

| Ticker | Company | Notes |
|--------|---------|-------|
| `AAPL` | Apple | Standard 4-letter |
| `A` | Agilent | Single letter |
| `GOOGL` | Alphabet Class A | 5 letters |
| `BRK.A` | Berkshire Class A | Dot separator |
| `BRK.B` | Berkshire Class B | Dot separator |
| `BRK-A` | Berkshire Class A | Hyphen (alternate) |
| `BF.A` | Brown-Forman Class A | Dot separator |
| `BF.B` | Brown-Forman Class B | Dot separator |
| `JPM` | JPMorgan | Standard 3-letter |

### Improved Detection Function

```python
import re
from typing import Tuple

# Ticker pattern:
# - 1-5 base characters (letters, optionally digits)
# - Optional class suffix: .X or -X
TICKER_PATTERN = re.compile(
    r"""
    ^
    [A-Z]{1,5}        # Base: 1-5 letters
    (?:[.-][A-Z])?    # Optional: class suffix (.A, .B, -A, -B)
    $
    """,
    re.VERBOSE | re.IGNORECASE
)

# More permissive pattern for international tickers
TICKER_PATTERN_EXTENDED = re.compile(
    r"""
    ^
    [A-Z0-9]{1,6}     # Base: 1-6 alphanumeric
    (?:[.-][A-Z0-9]{1,2})?  # Optional: class suffix
    $
    """,
    re.VERBOSE | re.IGNORECASE
)


def looks_like_ticker(s: str) -> Tuple[bool, str]:
    """
    Determine if string looks like a stock ticker.
    
    Args:
        s: Input string.
    
    Returns:
        Tuple of (is_ticker, normalized_form).
    
    Examples:
        >>> looks_like_ticker("AAPL")
        (True, "AAPL")
        >>> looks_like_ticker("brk.b")
        (True, "BRK.B")
        >>> looks_like_ticker("BRK-B")
        (True, "BRK.B")  # Normalized to dot
        >>> looks_like_ticker("0000320193")
        (False, "0000320193")
    """
    if not s:
        return False, s
    
    # Normalize case
    upper = s.upper().strip()
    
    # Normalize separator (hyphen → dot)
    normalized = upper.replace("-", ".")
    
    # Quick rejection: too long
    if len(normalized) > 7:
        return False, s
    
    # Quick rejection: all digits (likely CIK)
    if normalized.replace(".", "").isdigit():
        return False, s
    
    # Try standard pattern first
    if TICKER_PATTERN.match(normalized):
        return True, normalized
    
    # Try extended pattern
    if TICKER_PATTERN_EXTENDED.match(normalized):
        return True, normalized
    
    return False, s
```

### Ticker vs CIK Disambiguation

```python
def classify_numeric_string(s: str) -> IdentifierType:
    """
    Classify a numeric string (CIK or possibly ticker).
    
    CIK characteristics:
    - 10 digits (official format)
    - 1-10 digits (unofficial, will be zero-padded)
    - All digits
    """
    # Strip leading zeros for length check
    stripped = s.lstrip("0")
    
    # If 1-10 digits and numeric, it's a CIK
    if stripped.isdigit() and 1 <= len(stripped) <= 10:
        # Zero-pad to 10 digits
        return IdentifierType.CIK
    
    return IdentifierType.UNKNOWN
```

---

## Classification Logic

### Main Classification Function

```python
def classify_identifier(value: str) -> ClassificationResult:
    """
    Classify an identifier string.
    
    Args:
        value: User-provided identifier.
    
    Returns:
        ClassificationResult with type and normalized value.
    """
    original = value
    cleaned = value.strip()
    
    if not cleaned:
        return ClassificationResult(
            identifier_type=IdentifierType.UNKNOWN,
            normalized_value="",
            original_value=original,
            confidence=0.0,
        )
    
    # Check for known scheme prefix (e.g., "isin:US0378331005")
    if ":" in cleaned:
        scheme, scheme_value = cleaned.split(":", 1)
        return ClassificationResult(
            identifier_type=IdentifierType.SCHEME_VALUE,
            normalized_value=scheme_value.upper(),
            original_value=original,
            confidence=0.95,
            scheme=scheme.lower(),
        )
    
    # Check for EntitySpine ULID (26 chars, alphanumeric)
    if _looks_like_ulid(cleaned):
        return ClassificationResult(
            identifier_type=IdentifierType.ENTITY_ID,
            normalized_value=cleaned,
            original_value=original,
            confidence=0.99,
        )
    
    # Check for CIK (numeric, 1-10 digits)
    if cleaned.isdigit() and len(cleaned.lstrip("0")) <= 10:
        # Zero-pad to 10 digits
        normalized_cik = cleaned.lstrip("0").zfill(10)
        return ClassificationResult(
            identifier_type=IdentifierType.CIK,
            normalized_value=normalized_cik,
            original_value=original,
            confidence=0.95,
        )
    
    # Check for ticker
    is_ticker, normalized_ticker = looks_like_ticker(cleaned)
    if is_ticker:
        return ClassificationResult(
            identifier_type=IdentifierType.TICKER,
            normalized_value=normalized_ticker,
            original_value=original,
            confidence=0.7,  # Lower confidence, could be alias
        )
    
    # Assume it's a name/alias
    return ClassificationResult(
        identifier_type=IdentifierType.NAME,
        normalized_value=cleaned,
        original_value=original,
        confidence=0.5,  # Lowest confidence
    )


def _looks_like_ulid(s: str) -> bool:
    """Check if string looks like a ULID."""
    # ULID: 26 characters, Crockford's Base32
    if len(s) != 26:
        return False
    
    # Crockford's Base32 alphabet (excludes I, L, O, U)
    valid_chars = set("0123456789ABCDEFGHJKMNPQRSTVWXYZ")
    return all(c.upper() in valid_chars for c in s)
```

---

## Testing Requirements

### Ticker Detection Tests

```python
class TestTickerDetection:
    """Tests for improved ticker detection."""
    
    @pytest.mark.parametrize("input_value,expected_ticker,expected_normalized", [
        # Standard tickers
        ("AAPL", True, "AAPL"),
        ("aapl", True, "AAPL"),
        ("A", True, "A"),
        ("GOOGL", True, "GOOGL"),
        
        # Class shares with dot
        ("BRK.A", True, "BRK.A"),
        ("BRK.B", True, "BRK.B"),
        ("BF.A", True, "BF.A"),
        ("brk.b", True, "BRK.B"),
        
        # Class shares with hyphen (normalized to dot)
        ("BRK-A", True, "BRK.A"),
        ("BRK-B", True, "BRK.B"),
        ("bf-a", True, "BF.A"),
        
        # Not tickers
        ("0000320193", False, "0000320193"),  # CIK
        ("320193", False, "320193"),          # Short CIK
        ("Apple Inc.", False, "Apple Inc."),  # Name
        ("", False, ""),                       # Empty
    ])
    def test_looks_like_ticker(self, input_value, expected_ticker, expected_normalized):
        is_ticker, normalized = looks_like_ticker(input_value)
        assert is_ticker == expected_ticker
        if expected_ticker:
            assert normalized == expected_normalized
    
    def test_ticker_confidence_lower_than_cik(self):
        """Ticker confidence should be lower than CIK."""
        ticker_result = classify_identifier("AAPL")
        cik_result = classify_identifier("320193")
        
        assert ticker_result.confidence < cik_result.confidence
```

### Classification Integration Tests

```python
class TestClassifyIdentifier:
    """Integration tests for identifier classification."""
    
    def test_cik_zero_padded(self):
        result = classify_identifier("0000320193")
        assert result.identifier_type == IdentifierType.CIK
        assert result.normalized_value == "0000320193"
    
    def test_cik_without_zeros(self):
        result = classify_identifier("320193")
        assert result.identifier_type == IdentifierType.CIK
        assert result.normalized_value == "0000320193"  # Zero-padded
    
    def test_ticker_class_shares(self):
        result = classify_identifier("BRK.B")
        assert result.identifier_type == IdentifierType.TICKER
        assert result.normalized_value == "BRK.B"
    
    def test_scheme_value(self):
        result = classify_identifier("isin:US0378331005")
        assert result.identifier_type == IdentifierType.SCHEME_VALUE
        assert result.scheme == "isin"
        assert result.normalized_value == "US0378331005"
    
    def test_company_name(self):
        result = classify_identifier("Apple Inc.")
        assert result.identifier_type == IdentifierType.NAME
```

---

## Decision Log

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | Support dot and hyphen in tickers | Real-world class shares use both |
| 2 | Normalize hyphen to dot | Consistency in storage |
| 3 | Ticker confidence = 0.7 | Lower than CIK because ambiguous |
| 4 | CIK confidence = 0.95 | High but not 1.0 (edge cases exist) |
| 5 | Name confidence = 0.5 | Lowest, most ambiguous |
| 6 | Zero-pad CIKs to 10 digits | SEC standard format |
| 7 | Case-insensitive comparison | User convenience |
| 8 | Support scheme:value prefix | Explicit identifier specification |

---

*EntitySpine Identifier Classification v2.2.1 | January 2026*
