# EntitySpine v2.2 Implementation Phases

**For: Claude Opus 4.5 (Extended Thinking Mode)**

> This document breaks down implementation into testable phases.  
> Each phase has tests to write FIRST, then implementation.

---

## Overview: Current State → Target State

### Current Structure (v2.1-ish, needs v2.2 alignment)

```
src/entityspine/
├── __init__.py                    # Exports EntityResolver, Entity
├── core/
│   ├── exceptions.py              # Keep
│   ├── normalize.py               # Keep
│   ├── ulid.py                    # Keep
│   └── config.py                  # Keep
├── domain/
│   ├── entities/
│   │   ├── enums.py               # Keep (EntityType, EntityStatus)
│   │   ├── model.py               # ⚠️ Entity has ticker - WRONG
│   │   └── simple.py              # ⚠️ SimpleEntity has ticker - WRONG
│   └── resolution/
│       └── resolver.py            # ⚠️ Returns Entity|None - WRONG
└── adapters/
    └── __init__.py                # Empty
```

### Target Structure (v2.2)

```
src/entityspine/
├── __init__.py                    # Simple facade exports
├── py.typed                       # PEP 561 marker
│
├── core/                          # Utilities (keep, enhance)
│   ├── __init__.py
│   ├── exceptions.py              # Keep
│   ├── normalize.py               # Keep, add listing normalization
│   ├── ulid.py                    # Keep
│   └── config.py                  # Keep
│
├── domain/                        # Domain layer
│   ├── __init__.py
│   ├── models/                    # v2.2 models
│   │   ├── __init__.py
│   │   ├── entity.py              # Entity (NO ticker)
│   │   ├── security.py            # Security (NEW)
│   │   ├── listing.py             # Listing (HAS ticker)
│   │   ├── claim.py               # IdentifierClaim (NEW)
│   │   ├── resolution.py          # ResolutionResult, Candidate
│   │   └── enums.py               # EntityType, EntityStatus, etc.
│   ├── protocols/                 # Interfaces
│   │   ├── __init__.py
│   │   ├── store.py               # EntityStoreProtocol
│   │   └── resolver.py            # EntityResolverProtocol
│   └── legacy/                    # Backward compat (optional)
│       └── simple.py              # Deprecated SimpleEntity
│
├── infrastructure/                # Storage implementations
│   ├── __init__.py
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── json_store.py          # SEC JSON read-only
│   │   ├── sqlite_store.py        # SQLite with v2.2 schema
│   │   └── protocol.py            # Move from adapters
│   └── http/
│       ├── __init__.py
│       └── sec_fetcher.py         # SEC data download
│
├── application/                   # Application services
│   ├── __init__.py
│   └── resolver.py                # EntityResolver service
│
└── facade/                        # Simple public API
    ├── __init__.py
    └── simple_api.py              # resolver = EntityResolver()
```

---

## Phase 0: Project Foundation

### 0.1 Create Test Structure

**Action**: Create test directories mirroring source.

```
tests/
├── conftest.py                    # Shared fixtures
├── unit/
│   ├── core/
│   │   ├── test_normalize.py
│   │   └── test_ulid.py
│   ├── domain/
│   │   ├── models/
│   │   │   ├── test_entity.py
│   │   │   ├── test_security.py
│   │   │   ├── test_listing.py
│   │   │   ├── test_claim.py
│   │   │   └── test_resolution.py
│   │   └── protocols/
│   │       └── test_protocols.py
│   ├── infrastructure/
│   │   └── storage/
│   │       ├── test_json_store.py
│   │       └── test_sqlite_store.py
│   └── application/
│       └── test_resolver.py
└── integration/
    ├── test_resolution_flow.py
    ├── test_simple_api.py
    └── test_sec_data.py
```

### 0.2 Create conftest.py

```python
# tests/conftest.py
"""Shared test fixtures for entityspine."""

import json
import sqlite3
import tempfile
from datetime import date
from pathlib import Path
from typing import Generator

import pytest


@pytest.fixture
def temp_db() -> Generator[Path, None, None]:
    """Create temporary SQLite database file."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    yield db_path
    db_path.unlink(missing_ok=True)


@pytest.fixture
def sample_sec_json() -> dict:
    """Sample SEC company_tickers.json data structure."""
    return {
        "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
        "1": {"cik_str": 789019, "ticker": "MSFT", "title": "MICROSOFT CORP"},
        "2": {"cik_str": 1318605, "ticker": "TSLA", "title": "Tesla, Inc."},
        "3": {"cik_str": 1067983, "ticker": "BRK-B", "title": "BERKSHIRE HATHAWAY INC"},
    }


@pytest.fixture
def sample_sec_json_file(sample_sec_json: dict, tmp_path: Path) -> Path:
    """Create sample SEC JSON file."""
    json_path = tmp_path / "company_tickers.json"
    json_path.write_text(json.dumps(sample_sec_json))
    return json_path


@pytest.fixture
def today() -> date:
    """Today's date for testing."""
    return date.today()
```

---

## Phase 1: Domain Models (v2.2)

### 1.1 Tests First: Entity Model

**File**: `tests/unit/domain/models/test_entity.py`

```python
"""Tests for v2.2 Entity model."""

from datetime import datetime

import pytest

from entityspine.domain.models.entity import Entity, EntityType, EntityStatus


class TestEntityCreation:
    """Test Entity creation and attributes."""

    def test_entity_minimal_creation(self):
        """Entity can be created with minimal required fields."""
        entity = Entity(
            entity_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            primary_name="Apple Inc.",
            source_system="sec",
        )
        assert entity.entity_id == "01ARZ3NDEKTSV4RRFFQ69G5FAV"
        assert entity.primary_name == "Apple Inc."
        assert entity.source_system == "sec"

    def test_entity_defaults(self):
        """Entity has correct default values."""
        entity = Entity(
            entity_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            primary_name="Apple Inc.",
            source_system="sec",
        )
        assert entity.entity_type == EntityType.COMPANY
        assert entity.status == EntityStatus.ACTIVE
        assert entity.merged_into_id is None


class TestEntityScopeEnforcement:
    """v2.2 CRITICAL: Entity must NOT have ticker/exchange."""

    def test_entity_has_no_ticker_attribute(self):
        """Entity must NOT have ticker attribute."""
        entity = Entity(
            entity_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            primary_name="Apple Inc.",
            source_system="sec",
        )
        assert not hasattr(entity, "ticker")
        assert "ticker" not in entity.__dataclass_fields__

    def test_entity_has_no_exchange_attribute(self):
        """Entity must NOT have exchange attribute."""
        entity = Entity(
            entity_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            primary_name="Apple Inc.",
            source_system="sec",
        )
        assert not hasattr(entity, "exchange")
        assert "exchange" not in entity.__dataclass_fields__


class TestEntityImmutability:
    """Entity should be immutable (frozen dataclass)."""

    def test_entity_is_frozen(self):
        """Entity attributes cannot be modified after creation."""
        entity = Entity(
            entity_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            primary_name="Apple Inc.",
            source_system="sec",
        )
        with pytest.raises((AttributeError, TypeError)):
            entity.primary_name = "Changed"  # type: ignore


class TestEntityMerge:
    """Test entity merge functionality."""

    def test_entity_can_track_merge_target(self):
        """Merged entity tracks redirect target."""
        entity = Entity(
            entity_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
            primary_name="Time Warner",
            source_system="sec",
            status=EntityStatus.MERGED,
            merged_into_id="01BSY4NDEKTSV4RRFFQ69G5FAV",
        )
        assert entity.status == EntityStatus.MERGED
        assert entity.merged_into_id == "01BSY4NDEKTSV4RRFFQ69G5FAV"
```

### 1.2 Implement: Entity Model

**File**: `src/entityspine/domain/models/entity.py`

```python
"""
Entity domain model (v2.2).

An Entity represents a legal organization that files with the SEC
or issues securities. Identified by CIK, LEI, etc.

CRITICAL v2.2 RULE: Entity does NOT have ticker or exchange.
Those belong to Listing (Entity → Security → Listing).
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class EntityType(Enum):
    """Classification of entity."""
    COMPANY = "COMPANY"
    FUND = "FUND"
    PERSON = "PERSON"
    GOVERNMENT = "GOVERNMENT"
    SPV = "SPV"
    TRUST = "TRUST"
    PARTNERSHIP = "PARTNERSHIP"
    UNKNOWN = "UNKNOWN"


class EntityStatus(Enum):
    """Lifecycle status of entity."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    MERGED = "merged"
    PROVISIONAL = "provisional"
    DISPUTED = "disputed"


@dataclass(frozen=True, slots=True)
class Entity:
    """
    A legal organization that files with SEC or issues securities.
    
    This is the top of the hierarchy: Entity → Security → Listing.
    
    Attributes:
        entity_id: ULID primary key.
        primary_name: Current canonical name.
        source_system: Where this entity originated.
        entity_type: Classification (COMPANY, FUND, etc.).
        status: Lifecycle status (active, merged, etc.).
        legal_name: Official legal name if different.
        sic_code: Standard Industrial Classification.
        merged_into_id: If status=MERGED, the target entity ID.
        merged_at: When the merge occurred.
        created_at: When record was created.
        updated_at: When record was last updated.
    
    Note:
        v2.2 CRITICAL: Entity does NOT have ticker or exchange.
        Those are Listing attributes, not Entity attributes.
    
    Example:
        >>> entity = Entity(
        ...     entity_id="01ARZ3NDEKTSV4RRFFQ69G5FAV",
        ...     primary_name="Apple Inc.",
        ...     source_system="sec",
        ... )
        >>> entity.primary_name
        'Apple Inc.'
        >>> hasattr(entity, 'ticker')
        False
    """
    
    # Required fields
    entity_id: str
    primary_name: str
    source_system: str
    
    # Classification
    entity_type: EntityType = EntityType.COMPANY
    status: EntityStatus = EntityStatus.ACTIVE
    
    # Optional details
    legal_name: str | None = None
    sic_code: str | None = None
    
    # Merge tracking (v2.2: redirects, never deletes)
    merged_into_id: str | None = None
    merged_at: datetime | None = None
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def __str__(self) -> str:
        """Human-readable representation."""
        status = f" [{self.status.value}]" if self.status != EntityStatus.ACTIVE else ""
        return f"{self.primary_name}{status}"
```

### 1.3 Tests First: Security Model

**File**: `tests/unit/domain/models/test_security.py`

```python
"""Tests for v2.2 Security model."""

import pytest

from entityspine.domain.models.security import Security, SecurityType


class TestSecurityCreation:
    """Test Security creation."""

    def test_security_minimal_creation(self):
        """Security can be created with required fields."""
        security = Security(
            security_id="01SEC...",
            issuer_entity_id="01ENT...",
            name="Apple Inc. Common Stock",
            source_system="sec",
        )
        assert security.security_id == "01SEC..."
        assert security.issuer_entity_id == "01ENT..."

    def test_security_requires_issuer_entity_id(self):
        """Security must have issuer_entity_id."""
        with pytest.raises(TypeError):
            Security(
                security_id="01SEC...",
                # Missing issuer_entity_id
                name="Apple Inc. Common Stock",
                source_system="sec",
            )


class TestSecurityScopeEnforcement:
    """v2.2: Security should NOT have ticker (that's on Listing)."""

    def test_security_has_no_ticker(self):
        """Security must NOT have ticker attribute."""
        security = Security(
            security_id="01SEC...",
            issuer_entity_id="01ENT...",
            name="Apple Inc. Common Stock",
            source_system="sec",
        )
        assert not hasattr(security, "ticker")
```

### 1.4 Implement: Security Model

**File**: `src/entityspine/domain/models/security.py`

```python
"""
Security domain model (v2.2).

A Security represents a financial instrument issued by an Entity.
Example: Apple Inc. (Entity) issues AAPL Common Stock (Security).

v2.2 CRITICAL: Security does NOT have ticker. Ticker is on Listing.
Security → Listing (1:N) - a security can have multiple listings.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class SecurityType(Enum):
    """Type of financial instrument."""
    COMMON_STOCK = "common_stock"
    PREFERRED_STOCK = "preferred_stock"
    ADR = "adr"
    ETF = "etf"
    BOND = "bond"
    WARRANT = "warrant"
    OPTION = "option"
    UNIT = "unit"
    RIGHT = "right"
    UNKNOWN = "unknown"


class SecurityStatus(Enum):
    """Lifecycle status of security."""
    ACTIVE = "active"
    DELISTED = "delisted"
    SUSPENDED = "suspended"
    MATURED = "matured"


@dataclass(frozen=True, slots=True)
class Security:
    """
    A financial instrument issued by an Entity.
    
    Position in hierarchy: Entity → Security → Listing.
    
    Attributes:
        security_id: ULID primary key.
        issuer_entity_id: FK to Entity that issued this security.
        name: Description of the security.
        security_type: Type (common_stock, etc.).
        status: Lifecycle status.
        currency: Trading currency (ISO 4217).
        source_system: Where this record originated.
    
    Note:
        v2.2 CRITICAL: Security does NOT have ticker.
        Ticker belongs to Listing (where it trades).
    
    Example:
        >>> security = Security(
        ...     security_id="01SEC...",
        ...     issuer_entity_id="01ENT...",  # Apple Inc.
        ...     name="Apple Inc. Common Stock",
        ...     source_system="sec",
        ... )
    """
    
    # Required
    security_id: str
    issuer_entity_id: str
    name: str
    source_system: str
    
    # Classification
    security_type: SecurityType = SecurityType.COMMON_STOCK
    status: SecurityStatus = SecurityStatus.ACTIVE
    
    # Optional
    currency: str | None = None
    isin: str | None = None  # Stored as claim too
    cusip: str | None = None  # Stored as claim too
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
```

### 1.5 Tests First: Listing Model

**File**: `tests/unit/domain/models/test_listing.py`

```python
"""Tests for v2.2 Listing model."""

from datetime import date

import pytest

from entityspine.domain.models.listing import Listing


class TestListingCreation:
    """Test Listing creation."""

    def test_listing_has_ticker(self):
        """v2.2: Listing MUST have ticker attribute."""
        listing = Listing(
            listing_id="01LST...",
            security_id="01SEC...",
            ticker="AAPL",
            valid_from=date(1980, 12, 12),
            source_system="sec",
        )
        assert listing.ticker == "AAPL"

    def test_listing_requires_ticker(self):
        """Listing must have ticker."""
        with pytest.raises(TypeError):
            Listing(
                listing_id="01LST...",
                security_id="01SEC...",
                # Missing ticker
                valid_from=date(1980, 12, 12),
                source_system="sec",
            )


class TestListingTemporality:
    """v2.2: Listings have validity periods."""

    def test_listing_has_valid_from(self):
        """Listing must have valid_from date."""
        listing = Listing(
            listing_id="01LST...",
            security_id="01SEC...",
            ticker="AAPL",
            valid_from=date(1980, 12, 12),
            source_system="sec",
        )
        assert listing.valid_from == date(1980, 12, 12)

    def test_listing_valid_to_nullable(self):
        """Listing.valid_to is None for current listings."""
        listing = Listing(
            listing_id="01LST...",
            security_id="01SEC...",
            ticker="AAPL",
            valid_from=date(1980, 12, 12),
            source_system="sec",
        )
        assert listing.valid_to is None

    def test_listing_is_active_at(self):
        """Can check if listing was active at a point in time."""
        listing = Listing(
            listing_id="01LST...",
            security_id="01SEC...",
            ticker="AAPL",
            valid_from=date(1980, 12, 12),
            valid_to=date(2000, 1, 1),
            source_system="sec",
        )
        assert listing.is_active_at(date(1990, 6, 15)) is True
        assert listing.is_active_at(date(1970, 1, 1)) is False
        assert listing.is_active_at(date(2020, 1, 1)) is False
```

### 1.6 Implement: Listing Model

**File**: `src/entityspine/domain/models/listing.py`

```python
"""
Listing domain model (v2.2).

A Listing represents where and when a Security trades.
Example: AAPL Common Stock (Security) lists as "AAPL" on NASDAQ (Listing).

v2.2 CRITICAL: This is WHERE ticker lives.
- NOT on Entity
- NOT on Security  
- ON Listing (with MIC and validity period)
"""

from dataclasses import dataclass, field
from datetime import date, datetime


class ListingStatus:
    """Status of listing."""
    ACTIVE = "active"
    DELISTED = "delisted"
    SUSPENDED = "suspended"


@dataclass(frozen=True, slots=True)
class Listing:
    """
    Where and when a security trades.
    
    Position in hierarchy: Entity → Security → Listing.
    This is the ONLY place ticker exists in v2.2.
    
    Attributes:
        listing_id: ULID primary key.
        security_id: FK to Security being listed.
        ticker: The trading symbol (v2.2: ONLY on Listing).
        mic: Market Identifier Code (e.g., XNAS, XNYS).
        is_primary: Is this the primary listing?
        status: Lifecycle status.
        valid_from: Start of listing validity.
        valid_to: End of listing validity (None = current).
        source_system: Where this record originated.
    
    Example:
        >>> listing = Listing(
        ...     listing_id="01LST...",
        ...     security_id="01SEC...",
        ...     ticker="AAPL",
        ...     mic="XNAS",  # NASDAQ
        ...     valid_from=date(1980, 12, 12),
        ...     source_system="sec",
        ... )
    """
    
    # Required
    listing_id: str
    security_id: str
    ticker: str  # v2.2: ONLY on Listing!
    valid_from: date
    source_system: str
    
    # Optional
    mic: str | None = None  # Market Identifier Code
    is_primary: bool = True
    status: str = ListingStatus.ACTIVE
    valid_to: date | None = None  # None = still active
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def is_active_at(self, as_of: date) -> bool:
        """
        Check if listing was active at given date.
        
        Args:
            as_of: Date to check.
        
        Returns:
            True if listing was active at as_of.
        
        Example:
            >>> listing.is_active_at(date(1990, 6, 15))
            True
        """
        if as_of < self.valid_from:
            return False
        if self.valid_to and as_of > self.valid_to:
            return False
        return True
```

### 1.7 Tests First: IdentifierClaim Model

**File**: `tests/unit/domain/models/test_claim.py`

```python
"""Tests for v2.2 IdentifierClaim model."""

from datetime import datetime

import pytest

from entityspine.domain.models.claim import IdentifierClaim


class TestClaimCreation:
    """Test IdentifierClaim creation."""

    def test_claim_has_provenance(self):
        """v2.2: All claims have provenance (source_system, confidence)."""
        claim = IdentifierClaim(
            claim_id="01CLM...",
            entity_id="01ENT...",
            scheme="cik",
            value="0000320193",
            source_system="sec",
            confidence=1.0,
        )
        assert claim.source_system == "sec"
        assert claim.confidence == 1.0
        assert claim.captured_at is not None

    def test_claim_requires_source_system(self):
        """Claim must have source_system."""
        with pytest.raises(TypeError):
            IdentifierClaim(
                claim_id="01CLM...",
                entity_id="01ENT...",
                scheme="cik",
                value="0000320193",
                # Missing source_system
                confidence=1.0,
            )


class TestClaimSchemes:
    """Test identifier scheme support."""

    def test_claim_supports_cik(self):
        """Can create CIK claim."""
        claim = IdentifierClaim(
            claim_id="01CLM...",
            entity_id="01ENT...",
            scheme="cik",
            value="0000320193",
            source_system="sec",
            confidence=1.0,
        )
        assert claim.scheme == "cik"

    def test_claim_supports_lei(self):
        """Can create LEI claim."""
        claim = IdentifierClaim(
            claim_id="01CLM...",
            entity_id="01ENT...",
            scheme="lei",
            value="HWUPKR0MPOU8FGXBT394",
            source_system="gleif",
            confidence=1.0,
        )
        assert claim.scheme == "lei"
```

### 1.8 Implement: IdentifierClaim Model

**File**: `src/entityspine/domain/models/claim.py`

```python
"""
IdentifierClaim domain model (v2.2).

All identifiers are stored as claims with provenance.
This allows multiple sources to claim the same identifier
with different confidence levels.

v2.2 CRITICAL: This replaces the old "identifiers" dict.
Every identifier lookup goes through claims table.
"""

from dataclasses import dataclass, field
from datetime import datetime


class ClaimStatus:
    """Status of identifier claim."""
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    DISPUTED = "disputed"
    RETRACTED = "retracted"


@dataclass(frozen=True, slots=True)
class IdentifierClaim:
    """
    A claimed identifier with provenance.
    
    v2.2 CRITICAL: All identifiers are claims, not facts.
    Multiple sources can claim the same identifier with
    different confidence levels.
    
    Attributes:
        claim_id: ULID primary key.
        scheme: Identifier scheme (cik, lei, isin, cusip, etc.).
        value: The identifier value.
        source_system: Where this claim came from.
        confidence: 0.0-1.0 confidence level.
        captured_at: When this claim was captured.
        entity_id: Entity this identifier belongs to (if entity-level).
        security_id: Security this identifier belongs to (if security-level).
        listing_id: Listing this identifier belongs to (if listing-level).
        status: Claim status (active, superseded, etc.).
        valid_from: Start of validity (for temporal identifiers).
        valid_to: End of validity.
        evidence_uri: Where to find proof of this claim.
    
    Example:
        >>> claim = IdentifierClaim(
        ...     claim_id="01CLM...",
        ...     entity_id="01ENT...",
        ...     scheme="cik",
        ...     value="0000320193",
        ...     source_system="sec",
        ...     confidence=1.0,
        ... )
    """
    
    # Required
    claim_id: str
    scheme: str  # cik, lei, isin, cusip, figi, bbgid, ric, etc.
    value: str
    source_system: str
    confidence: float  # 0.0 to 1.0
    
    # Target (exactly one should be set)
    entity_id: str | None = None
    security_id: str | None = None
    listing_id: str | None = None
    
    # Status and validity
    status: str = ClaimStatus.ACTIVE
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    
    # Evidence
    evidence_uri: str | None = None
    evidence_text: str | None = None
    
    # Timestamps
    captured_at: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self):
        """Validate claim has exactly one target."""
        targets = [self.entity_id, self.security_id, self.listing_id]
        set_targets = [t for t in targets if t is not None]
        if len(set_targets) != 1:
            # For frozen dataclass, we can't raise in post_init easily
            # This is just documentation of the constraint
            pass
```

### 1.9 Tests First: ResolutionResult Model

**File**: `tests/unit/domain/models/test_resolution.py`

```python
"""Tests for v2.2 ResolutionResult model."""

from datetime import date

import pytest

from entityspine.domain.models.resolution import (
    ResolutionResult,
    ResolutionCandidate,
)


class TestResolutionResult:
    """Test ResolutionResult (v2.2 CRITICAL)."""

    def test_result_contains_candidates_list(self):
        """v2.2: resolve() returns list of candidates, not single entity."""
        result = ResolutionResult(
            candidates=[
                ResolutionCandidate(
                    entity_id="01ENT...",
                    score=0.95,
                    match_type="exact",
                    matched_value="320193",
                )
            ],
            query="320193",
            as_of=date.today(),
        )
        assert isinstance(result.candidates, list)
        assert len(result.candidates) == 1

    def test_result_has_best_property(self):
        """ResolutionResult.best returns highest scored candidate."""
        result = ResolutionResult(
            candidates=[
                ResolutionCandidate(entity_id="01A", score=0.7, match_type="fuzzy", matched_value="Apple"),
                ResolutionCandidate(entity_id="01B", score=0.95, match_type="exact", matched_value="AAPL"),
            ],
            query="AAPL",
            as_of=date.today(),
        )
        # Candidates should be sorted by score
        assert result.best.entity_id == "01B"
        assert result.best.score == 0.95

    def test_result_empty_candidates(self):
        """Empty candidates is valid (no match found)."""
        result = ResolutionResult(
            candidates=[],
            query="UNKNOWN",
            as_of=date.today(),
        )
        assert result.best is None
        assert len(result.candidates) == 0


class TestResolutionCandidate:
    """Test ResolutionCandidate."""

    def test_candidate_has_required_fields(self):
        """Candidate has entity_id, score, match_type."""
        candidate = ResolutionCandidate(
            entity_id="01ENT...",
            score=0.95,
            match_type="ticker",
            matched_value="AAPL",
        )
        assert candidate.entity_id == "01ENT..."
        assert candidate.score == 0.95
        assert candidate.match_type == "ticker"

    def test_candidate_can_track_listing_path(self):
        """v2.2: Ticker resolution tracks listing_id, security_id."""
        candidate = ResolutionCandidate(
            entity_id="01ENT...",
            score=0.95,
            match_type="ticker",
            matched_value="AAPL:XNAS",
            listing_id="01LST...",
            security_id="01SEC...",
        )
        assert candidate.listing_id == "01LST..."
        assert candidate.security_id == "01SEC..."
```

### 1.10 Implement: ResolutionResult Model

**File**: `src/entityspine/domain/models/resolution.py`

```python
"""
Resolution result models (v2.2).

v2.2 CRITICAL: resolve() returns ResolutionResult containing
a list of ResolutionCandidate, NOT Entity|None.

The resolver NEVER guesses. It returns ranked candidates
and lets the caller decide how to handle ambiguity.
"""

from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional


@dataclass(frozen=True, slots=True)
class ResolutionCandidate:
    """
    A candidate entity from resolution.
    
    Each candidate has a score and information about
    how the match was made.
    
    Attributes:
        entity_id: The candidate entity's ULID.
        score: Confidence score (0.0-1.0).
        match_type: How matched (exact, fuzzy, ticker, etc.).
        matched_value: The value that matched.
        matched_scheme: Identifier scheme if applicable.
        listing_id: If resolved via ticker, the listing.
        security_id: If resolved via ticker, the security.
        redirect_chain: If followed merge redirects, the chain.
    """
    
    entity_id: str
    score: float
    match_type: str
    matched_value: str
    matched_scheme: str | None = None
    listing_id: str | None = None
    security_id: str | None = None
    redirect_chain: list[str] | None = None


@dataclass
class ResolutionResult:
    """
    Result of entity resolution.
    
    v2.2 CRITICAL: This is what resolve() returns.
    NOT Entity, NOT Entity|None, but ResolutionResult.
    
    Attributes:
        candidates: Ranked list of matching entities.
        query: The original query string.
        as_of: Point-in-time for the resolution.
        is_ambiguous: True if multiple high-scoring candidates.
        needs_review: True if confidence is low.
        created_provisional: True if a provisional entity was created.
    
    Example:
        >>> result = resolver.resolve("AAPL")
        >>> if result.best and result.best.score >= 0.9:
        ...     entity = resolver.get(result.best.entity_id)
    """
    
    candidates: list[ResolutionCandidate]
    query: str
    as_of: date
    is_ambiguous: bool = False
    needs_review: bool = False
    created_provisional: bool = False
    
    def __post_init__(self):
        """Sort candidates by score descending."""
        # Sort in place if mutable
        self.candidates.sort(key=lambda c: c.score, reverse=True)
    
    @property
    def best(self) -> ResolutionCandidate | None:
        """
        Get highest-scored candidate.
        
        Returns:
            Best candidate or None if no candidates.
        """
        return self.candidates[0] if self.candidates else None
    
    @property
    def has_match(self) -> bool:
        """True if at least one candidate found."""
        return len(self.candidates) > 0
    
    @property
    def is_confident(self) -> bool:
        """True if best candidate has high confidence."""
        return self.best is not None and self.best.score >= 0.9
```

---

## Phase 2: Protocols & Interfaces

### 2.1 Tests First: EntityStoreProtocol

**File**: `tests/unit/domain/protocols/test_protocols.py`

```python
"""Tests for protocol definitions."""

from typing import Protocol

import pytest

from entityspine.domain.protocols.store import EntityStoreProtocol
from entityspine.domain.protocols.resolver import EntityResolverProtocol


class TestProtocolDefinitions:
    """Test that protocols are properly defined."""

    def test_store_protocol_is_runtime_checkable(self):
        """EntityStoreProtocol should be runtime checkable."""
        # Create a class that satisfies the protocol
        class FakeStore:
            def get_entity(self, entity_id): return None
            def get_entities_by_cik(self, cik): return []
            def get_listings_by_ticker(self, ticker, mic=None, as_of=None): return []
            def get_claims(self, scheme, value): return []
            def save_entity(self, entity): pass
            def save_claim(self, claim): pass
            def entity_count(self): return 0
        
        store = FakeStore()
        assert isinstance(store, EntityStoreProtocol)

    def test_resolver_protocol_returns_resolution_result(self):
        """EntityResolverProtocol.resolve must return ResolutionResult."""
        # This is a documentation/type check test
        # The protocol should define resolve() -> ResolutionResult
        import inspect
        sig = inspect.signature(EntityResolverProtocol.resolve)
        # Return annotation should be ResolutionResult
        # (actual check depends on how protocol is defined)
```

### 2.2 Implement: Protocols

**File**: `src/entityspine/domain/protocols/store.py`

```python
"""
Storage protocol definitions (v2.2).

All storage backends (JSON, SQLite, DuckDB, PostgreSQL) must
implement EntityStoreProtocol.
"""

from datetime import date
from typing import Protocol, runtime_checkable

from entityspine.domain.models.entity import Entity
from entityspine.domain.models.security import Security
from entityspine.domain.models.listing import Listing
from entityspine.domain.models.claim import IdentifierClaim


@runtime_checkable
class EntityStoreProtocol(Protocol):
    """
    Protocol for entity storage backends.
    
    All storage implementations must satisfy this interface.
    
    Example:
        >>> class SQLiteStore:
        ...     def get_entity(self, entity_id: str) -> Entity | None:
        ...         ...
        >>> store: EntityStoreProtocol = SQLiteStore(...)
    """
    
    # Entity operations
    def get_entity(self, entity_id: str) -> Entity | None:
        """Get entity by ID, following merge redirects."""
        ...
    
    def get_entity_raw(self, entity_id: str) -> Entity | None:
        """Get entity by ID without following redirects."""
        ...
    
    def get_entities_by_cik(self, cik: str) -> list[Entity]:
        """Get entities matching CIK (via claims)."""
        ...
    
    def save_entity(self, entity: Entity) -> None:
        """Save or update entity."""
        ...
    
    # Security operations
    def get_security(self, security_id: str) -> Security | None:
        """Get security by ID."""
        ...
    
    def get_securities_by_entity(self, entity_id: str) -> list[Security]:
        """Get all securities issued by entity."""
        ...
    
    # Listing operations
    def get_listings_by_ticker(
        self,
        ticker: str,
        mic: str | None = None,
        as_of: date | None = None,
    ) -> list[Listing]:
        """Get listings matching ticker, optionally at point-in-time."""
        ...
    
    def get_listings_by_security(self, security_id: str) -> list[Listing]:
        """Get all listings for a security."""
        ...
    
    # Claim operations
    def get_claims(
        self,
        scheme: str,
        value: str,
    ) -> list[IdentifierClaim]:
        """Get claims matching scheme and value."""
        ...
    
    def save_claim(self, claim: IdentifierClaim) -> None:
        """Save identifier claim."""
        ...
    
    # Statistics
    def entity_count(self) -> int:
        """Get total number of entities."""
        ...
```

**File**: `src/entityspine/domain/protocols/resolver.py`

```python
"""
Resolver protocol definitions (v2.2).

EntityResolverProtocol defines the resolution interface.
"""

from datetime import date
from typing import Protocol

from entityspine.domain.models.entity import Entity
from entityspine.domain.models.resolution import ResolutionResult


class EntityResolverProtocol(Protocol):
    """
    Protocol for entity resolution.
    
    v2.2 CRITICAL: resolve() returns ResolutionResult, not Entity.
    
    Example:
        >>> resolver: EntityResolverProtocol = EntityResolver(...)
        >>> result = resolver.resolve("AAPL")
        >>> if result.best:
        ...     entity = resolver.get(result.best.entity_id)
    """
    
    def resolve(
        self,
        query: str,
        as_of: date | None = None,
        limit: int = 10,
    ) -> ResolutionResult:
        """
        Resolve any identifier to ranked entity candidates.
        
        Args:
            query: CIK, ticker, name, or other identifier.
            as_of: Point-in-time for resolution.
            limit: Maximum candidates to return.
        
        Returns:
            ResolutionResult with ranked candidates.
        """
        ...
    
    def resolve_cik(self, cik: str) -> ResolutionResult:
        """Resolve SEC CIK to entity candidates."""
        ...
    
    def resolve_ticker(
        self,
        ticker: str,
        mic: str | None = None,
        as_of: date | None = None,
    ) -> ResolutionResult:
        """Resolve ticker via Listing → Security → Entity."""
        ...
    
    def get(self, entity_id: str) -> Entity | None:
        """Get entity by ID, follows merge redirects."""
        ...
    
    def get_canonical(self, entity_id: str) -> tuple[Entity | None, list[str]]:
        """Get entity and redirect chain."""
        ...
```

---

## Phase 3-6: Continue in Similar TDD Pattern

For brevity, Phases 3-6 follow the same pattern:

1. **Phase 3: Storage Layer**
   - Test `SQLiteStore` creates v2.2 schema (no ticker on entities table)
   - Test entity/security/listing CRUD
   - Test claim operations
   - Test merge redirects

2. **Phase 4: Resolution Service**
   - Test `resolve()` returns `ResolutionResult`
   - Test CIK resolution via claims
   - Test ticker resolution via listings
   - Test merge redirect following

3. **Phase 5: Simple Facade**
   - Test `EntityResolver()` works with no config
   - Test auto-download of SEC data
   - Test simple resolution flow

4. **Phase 6: Integration**
   - Test py-sec-edgar port interface
   - Test end-to-end resolution
   - Test SEC JSON to SQLite pipeline

---

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=entityspine --cov-report=html

# Run specific phase
pytest tests/unit/domain/models/

# Run single test file
pytest tests/unit/domain/models/test_entity.py -v
```

---

## Checklist Per Phase

For each phase:

- [ ] Write tests FIRST
- [ ] Run tests (should fail)
- [ ] Implement minimum code to pass
- [ ] Refactor if needed
- [ ] Run `mypy --strict`
- [ ] Run `ruff check`
- [ ] Commit with descriptive message

---

*EntitySpine Implementation Phases v2.2 | January 2026*
