# EntitySpine v2.3.0 Enhancements

This document describes the FactSet-informed enhancements made to EntitySpine
to better support institutional financial data workflows.

## Overview

These enhancements were designed by analyzing FactSet's Standard Data Feeds
and mapping their data models to EntitySpine's domain. The goal is to enable
seamless loading of FactSet data while maintaining EntitySpine's vendor-agnostic
design principles.

## Summary of Changes

| Component | Enhancement | Rationale |
|-----------|-------------|-----------|
| `EventType` enum | +40 new event types | Align with FactSet Events Calendar and SEC 8-K categories |
| `Event` model | Calendar event fields | Support earnings dates, fiscal periods, monetary amounts |
| `IdentifierScheme` enum | +15 new schemes | FactSet IDs, sanctions list identifiers |
| `SanctionStatus` enum | New enum | Track compliance screening status |
| `VendorSignature` patterns | +6 new signatures | Auto-detect FactSet file types |
| FactSet loaders | New module | Specialized loaders for each FactSet feed |
| Docstrings | Enhanced | Google-style with runnable examples |
| mkdocs.yml | New configuration | Modern documentation with mkdocstrings |

---

## 1. Enhanced EventType Enum

### Location
[enums.py](src/entityspine/domain/enums.py#L636)

### New Event Categories

#### Calendar Events (FactSet Events aligned)
```python
# Earnings calendar
EARNINGS_RELEASE = "earnings_release"
EARNINGS_CALL = "earnings_call"
EARNINGS_GUIDANCE = "earnings_guidance"
EARNINGS_REVISION = "earnings_revision"

# Dividend calendar
DIVIDEND_DECLARED = "dividend_declared"
DIVIDEND_EX_DATE = "dividend_ex_date"
DIVIDEND_RECORD = "dividend_record"
DIVIDEND_PAYMENT = "dividend_payment"
SPECIAL_DIVIDEND = "special_dividend"

# Corporate calendar
ANNUAL_MEETING = "annual_meeting"
ANALYST_DAY = "analyst_day"
INVESTOR_CONFERENCE = "investor_conference"
GUIDANCE_UPDATE = "guidance_update"

# Stock events
STOCK_SPLIT = "stock_split"
REVERSE_SPLIT = "reverse_split"
SHARE_BUYBACK = "share_buyback"
```

#### Compliance/Sanctions Events
```python
SANCTION_DESIGNATION = "sanction_designation"
SANCTION_REMOVAL = "sanction_removal"
SANCTION_UPDATE = "sanction_update"
COMPLIANCE_VIOLATION = "compliance_violation"
AUDIT_FINDING = "audit_finding"
```

#### Private Equity Events
```python
FUNDING_ROUND = "funding_round"
IPO = "ipo"
IPO_FILING = "ipo_filing"
DIRECT_LISTING = "direct_listing"
SPAC_MERGER = "spac_merger"
PRIVATE_PLACEMENT = "private_placement"
SECONDARY_OFFERING = "secondary_offering"
LBO = "lbo"
EXIT = "exit"
```

### Rationale
FactSet's Events Calendar provides granular event types that are important for:
- Earnings surprise analysis
- Dividend capture strategies
- Corporate action processing
- M&A deal tracking

---

## 2. Enhanced Event Model

### Location
[graph.py](src/entityspine/domain/graph.py#L1443)

### New Fields

```python
@dataclass(frozen=True, slots=True)
class Event:
    # Core fields (existing)
    event_type: EventType
    title: str
    
    # NEW: Calendar Event Fields (FactSet aligned)
    scheduled_on: date | None = None      # Scheduled date for future events
    effective_date: date | None = None    # When event takes effect (ex-date)
    fiscal_year: int | None = None        # FY for financial events
    fiscal_quarter: int | None = None     # Q1-Q4 for quarterly events
    report_time: str | None = None        # "BMO", "AMC", "DURING"
    currency: str | None = None           # ISO 4217 currency code
    amount: Decimal | None = None         # Dividend amount, deal value
    
    # NEW: Entity References
    entity_id: str | None = None          # Primary entity
    related_entity_ids: tuple = ()        # Other entities (acquirer/target)
```

### New Properties

```python
@property
def is_calendar_event(self) -> bool:
    """Check if this is a scheduled calendar event."""

@property
def is_financial_event(self) -> bool:
    """Check if this event involves monetary values."""

@property
def is_compliance_event(self) -> bool:
    """Check if this is a sanctions/compliance event."""

@property
def fiscal_period_str(self) -> str | None:
    """Get fiscal period as string (e.g., 'Q4 2024')."""
```

### Usage Example

```python
from entityspine.domain.graph import Event
from entityspine.domain.enums import EventType, EventStatus
from datetime import date
from decimal import Decimal

# Earnings release
earnings = Event(
    event_type=EventType.EARNINGS_RELEASE,
    title="Apple Q4 2024 Earnings",
    entity_id="ent_apple",
    fiscal_year=2024,
    fiscal_quarter=4,
    scheduled_on=date(2024, 10, 31),
    report_time="AMC",  # After Market Close
    source_system="factset",
)

# Check if it's a calendar event
assert earnings.is_calendar_event == True
assert earnings.fiscal_period_str == "Q4 2024"
```

---

## 3. Sanctions & Compliance Support

### New IdentifierScheme Values

```python
# FactSet identifiers
FACTSET_ENTITY_ID = "factset_entity_id"
FACTSET_PERSON_ID = "factset_person_id"
FACTSET_SECURITY_ID = "factset_security_id"

# US Sanctions
OFAC_SDN = "ofac_sdn"           # OFAC SDN List
OFAC_CONS = "ofac_cons"         # OFAC Consolidated Non-SDN
BIS_ENTITY_LIST = "bis_entity_list"  # Bureau of Industry & Security

# International Sanctions
UN_SANCTIONS = "un_sanctions"
EU_SANCTIONS = "eu_sanctions"
UK_SANCTIONS = "uk_sanctions"

# Other Compliance
PEP = "pep"                     # Politically Exposed Person
ADVERSE_MEDIA = "adverse_media"
WATCHLIST = "watchlist"
```

### New SanctionStatus Enum

```python
class SanctionStatus(str, Enum):
    """Sanctions screening status for an entity."""
    
    CLEAR = "clear"                         # No matches
    NOT_SCREENED = "not_screened"          # Not yet screened
    DESIGNATED = "designated"               # On sanctions list
    POTENTIAL_MATCH = "potential_match"     # Needs review
    FALSE_POSITIVE = "false_positive"       # Reviewed, cleared
    FORMERLY_DESIGNATED = "formerly_designated"
    DELISTED = "delisted"
    OWNED_BY_SANCTIONED = "owned_by_sanctioned"
    CONTROLLED_BY_SANCTIONED = "controlled_by_sanctioned"
    
    @property
    def is_blocked(self) -> bool:
        """Check if entity is blocked for transactions."""
    
    @property
    def requires_review(self) -> bool:
        """Check if status requires manual review."""
```

### Usage Example

```python
from entityspine.domain import IdentifierClaim, IdentifierScheme
from entityspine.domain.enums import SanctionStatus

# Store OFAC SDN identifier
sanction_claim = IdentifierClaim(
    scheme=IdentifierScheme.OFAC_SDN,
    value="SDN-12345",
    entity_id="ent_sanctioned",
    source="OFAC SDN List 2024-03-01",
    valid_from=date(2024, 3, 1),
)

# Check if entity is blocked
status = SanctionStatus.DESIGNATED
if status.is_blocked:
    print("Entity is blocked for transactions")
```

---

## 4. FactSet File Detection Patterns

### Location
[schema_detector.py](src/entityspine/data/schema_detector.py)

### New VendorSignature Patterns

| Signature | Detects | Column Patterns |
|-----------|---------|-----------------|
| `FACTSET_EDM` (symbology) | Identifier crosswalks | `fsym_id`, `cusip`, `isin`, `sedol` |
| `FACTSET_EDM` (events) | Corporate calendar | `event_type`, `fiscal_year`, `report_time` |
| `FACTSET_EDM` (people) | Executives/board | `person_id`, `job_function`, `job_title` |
| `FACTSET_EDM` (M&A) | Deal data | `deal_id`, `target_name`, `acquirer_name` |
| `FACTSET_SUPPLY_CHAIN` | Revere relationships | `relationship_type`, `revenue_exposure` |
| `FACTSET_ESTIMATES` | Analyst consensus | `eps_est`, `consensus_mean` |

### Usage Example

```python
from entityspine.data.schema_detector import detect_vendor

# Auto-detect FactSet file type
result = detect_vendor("earnings_calendar.csv")
print(f"Vendor: {result.vendor}")      # DataVendor.FACTSET
print(f"Product: {result.product}")    # DataProduct.FACTSET_EDM
print(f"Type: {result.data_type}")     # DataType.CORPORATE_ACTIONS
```

---

## 5. FactSet Loaders Module

### Location
[entityspine/data/factset/](src/entityspine/data/factset/)

### Available Loaders

| Loader | Input | Output |
|--------|-------|--------|
| `FactSetSymbologyLoader` | `sym_coverage.csv` | `IdentifierClaim` |
| `FactSetEventsLoader` | `ca_events.csv` | `Event` |
| `FactSetPeopleLoader` | `ppl_executives.csv` | `PersonRole` |
| `FactSetOwnershipLoader` | `ownership.csv` | `OwnershipPosition` |
| `FactSetMergersLoader` | `ma_deals.csv` | `Event`, `EntityRelationship` |
| `FactSetSupplyChainLoader` | `supply_chain.csv` | `EntityRelationship` |

### Usage Example

```python
from entityspine.data.factset import (
    FactSetSymbologyLoader,
    FactSetEventsLoader,
)

# Load identifier crosswalks
sym_loader = FactSetSymbologyLoader()
for claim in sym_loader.iter_claims("sym_coverage.csv"):
    print(f"{claim.scheme}: {claim.value}")

# Load earnings calendar
events_loader = FactSetEventsLoader()
for event in events_loader.iter_events("earnings_calendar.csv"):
    if event.is_calendar_event:
        print(f"{event.fiscal_period_str}: {event.title}")
```

---

## 6. Enhanced Docstrings

All domain models now have Google-style docstrings with:

- **Detailed descriptions** explaining design rationale
- **Complete attribute documentation**
- **Runnable examples** in doctest format
- **See Also** references to related classes

### Example (Entity class)

```python
@dataclass(frozen=True, slots=True)
class Entity:
    """
    Legal/organizational identity node in the EntitySpine knowledge graph.

    Entity is the central node type representing companies, persons, funds,
    government bodies, and other legal identities. Identifiers (CIK, LEI, etc.)
    are stored separately in IdentifierClaim to support multi-vendor crosswalks
    and temporal validity tracking.

    Examples:
        Create a basic company entity:

        >>> from entityspine.domain import Entity, EntityType
        >>> apple = Entity(
        ...     primary_name="Apple Inc.",
        ...     entity_type=EntityType.ORGANIZATION,
        ...     jurisdiction="US-DE",
        ... )

    See Also:
        - IdentifierClaim: For storing CIK, LEI, CUSIP, etc.
        - Security: For financial instruments issued by entities
    """
```

---

## 7. Documentation Configuration

### Location
[mkdocs.yml](mkdocs.yml)

### Features

- **mkdocs-material** theme with dark mode
- **mkdocstrings** for automatic API docs from docstrings
- **Google-style docstring parsing**
- **Code examples** with syntax highlighting
- **Mermaid diagrams** for architecture docs
- **Full-text search** with suggestions

### Generate Docs

```bash
# Install doc dependencies
pip install entityspine[docs]

# Serve locally
mkdocs serve

# Build for deployment
mkdocs build
```

---

## Migration Notes

These enhancements are **backwards compatible**. Existing code will continue
to work without modification. New fields have default values.

### Breaking Changes

None.

### Deprecations

None.

---

## Future Enhancements

Based on additional FactSet feeds not yet covered:

1. **Economic Indicators** - Macro data for country/region entities
2. **ESG Scores** - ESG ratings as financial observations
3. **Geographic Data** - Enhanced Geo node with economic metadata
4. **Fixed Income** - Bond-specific Security fields
5. **Private Company Data** - Enhanced support for non-public entities

---

## References

- [FactSet Standard Data Feeds](factset-dataset/docs/) - Local documentation
- [FACTSET_INTEGRATION.md](docs/FACTSET_INTEGRATION.md) - Integration mapping
- [EntitySpine README](README.md) - Project overview
