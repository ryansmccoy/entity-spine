"""
Identifier scheme and claim enums.

STDLIB ONLY - NO PYDANTIC.
"""

from enum import Enum


class IdentifierScheme(str, Enum):
    """
    Standard identifier schemes.

    Each scheme has an expected scope (entity, security, or listing).
    Includes compliance/sanctions list identifiers for KYC/AML workflows.

    Examples:
        >>> scheme = IdentifierScheme.LEI
        >>> scheme.value
        'lei'

        >>> # Check if scheme is sanctions-related
        >>> IdentifierScheme.OFAC_SDN in [
        ...     IdentifierScheme.OFAC_SDN,
        ...     IdentifierScheme.UN_SANCTIONS,
        ... ]
        True
    """

    # =========================================================================
    # Entity-scoped (legal identity)
    # =========================================================================
    CIK = "cik"  # SEC Central Index Key → entity_id
    LEI = "lei"  # Legal Entity Identifier → entity_id
    EIN = "ein"  # Employer Identification Number → entity_id
    DUNS = "duns"  # D-U-N-S Number → entity_id

    # FactSet Entity identifiers
    FACTSET_ENTITY_ID = "factset_entity_id"  # FactSet Permanent Entity ID
    FACTSET_PERSON_ID = "factset_person_id"  # FactSet Person ID

    # =========================================================================
    # Security-scoped (financial instrument)
    # =========================================================================
    ISIN = "isin"  # International Securities ID Number → security_id
    CUSIP = "cusip"  # CUSIP identifier → security_id
    SEDOL = "sedol"  # SEDOL identifier → security_id
    FIGI = "figi"  # Financial Instrument Global ID → security_id

    # FactSet Security identifiers
    FACTSET_SECURITY_ID = "factset_security_id"  # FactSet Permanent Security ID

    # =========================================================================
    # Listing-scoped (exchange-specific)
    # =========================================================================
    TICKER = "ticker"  # Stock ticker symbol → listing_id
    RIC = "ric"  # Reuters Instrument Code → listing_id

    # =========================================================================
    # Sanctions & Compliance List Identifiers (entity-scoped)
    # =========================================================================
    # US Sanctions
    OFAC_SDN = "ofac_sdn"  # OFAC Specially Designated Nationals list ID
    OFAC_CONS = "ofac_cons"  # OFAC Consolidated Non-SDN List ID
    BIS_ENTITY_LIST = "bis_entity_list"  # Bureau of Industry & Security Entity List

    # International Sanctions
    UN_SANCTIONS = "un_sanctions"  # UN Security Council Sanctions ID
    EU_SANCTIONS = "eu_sanctions"  # EU Consolidated Sanctions List ID
    UK_SANCTIONS = "uk_sanctions"  # UK Sanctions List (OFSI) ID

    # Other Compliance
    PEP = "pep"  # Politically Exposed Person identifier
    ADVERSE_MEDIA = "adverse_media"  # Adverse media reference ID
    WATCHLIST = "watchlist"  # Generic watchlist identifier

    # =========================================================================
    # Flexible scope
    # =========================================================================
    INTERNAL = "internal"  # Internal system ID → any
    OTHER = "other"  # Other identifier type → any


class ClaimStatus(str, Enum):
    """Status of an identifier claim."""

    ACTIVE = "active"
    SUPERSEDED = "superseded"
    REVOKED = "revoked"
    DISPUTED = "disputed"


class SanctionStatus(str, Enum):
    """
    Sanctions screening status for an entity.

    Used to track an entity's status against sanctions lists (OFAC, UN, EU, etc.).
    This enables compliance workflows and risk assessment.

    Examples:
        >>> status = SanctionStatus.DESIGNATED
        >>> status.is_blocked
        True

        >>> # Check if entity requires enhanced due diligence
        >>> SanctionStatus.POTENTIAL_MATCH.requires_review
        True
    """

    # Clear statuses
    CLEAR = "clear"  # No sanctions matches found
    NOT_SCREENED = "not_screened"  # Not yet screened

    # Match statuses
    DESIGNATED = "designated"  # Confirmed on sanctions list
    POTENTIAL_MATCH = "potential_match"  # Possible match, needs review
    FALSE_POSITIVE = "false_positive"  # Reviewed and cleared

    # Historical statuses
    FORMERLY_DESIGNATED = "formerly_designated"  # Previously sanctioned, now delisted
    DELISTED = "delisted"  # Removed from sanctions list

    # Ownership-based statuses
    OWNED_BY_SANCTIONED = "owned_by_sanctioned"  # >50% owned by sanctioned entity
    CONTROLLED_BY_SANCTIONED = "controlled_by_sanctioned"  # Controlled by sanctioned

    @property
    def is_blocked(self) -> bool:
        """Check if this status means entity is blocked for transactions."""
        return self in (
            SanctionStatus.DESIGNATED,
            SanctionStatus.OWNED_BY_SANCTIONED,
            SanctionStatus.CONTROLLED_BY_SANCTIONED,
        )

    @property
    def requires_review(self) -> bool:
        """Check if this status requires manual review."""
        return self in (
            SanctionStatus.POTENTIAL_MATCH,
            SanctionStatus.NOT_SCREENED,
        )


class IdentifierScope(str, Enum):
    """Which object type an identifier scheme applies to."""

    ENTITY = "entity"
    SECURITY = "security"
    LISTING = "listing"
    ANY = "any"
