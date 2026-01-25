"""
SQLModel table definitions for EntitySpine.

These tables map directly to the Pydantic domain models but are
designed for database storage using SQLAlchemy under the hood.

Table naming convention:
- Pydantic model: Entity
- SQLModel table: EntityTable
- DB table name: entities
"""

from datetime import date, datetime

from sqlmodel import JSON, Column, Field, Relationship, SQLModel

from entityspine.core.timestamps import utc_now
from entityspine.core.ulid import generate_ulid

# =============================================================================
# Entity Table
# =============================================================================


class EntityTable(SQLModel, table=True):
    """
    Entity database table.

    Maps to: entityspine.models.Entity
    DB table: entities

    Note v2.2.3:
    - cik/lei/ein/identifiers columns kept for backward compat but domain model
      doesn't expose them. Use IdentifierClaim/ClaimTable for identifiers.
    """

    __tablename__ = "entities"

    entity_id: str = Field(default_factory=generate_ulid, primary_key=True)
    primary_name: str = Field(index=True)
    entity_type: str = Field(default="organization")
    status: str = Field(default="active", index=True)

    # Legacy identifier fields (kept for backward compat, use ClaimTable instead)
    cik: str | None = Field(default=None, index=True)
    lei: str | None = Field(default=None, index=True)
    ein: str | None = Field(default=None)

    # Entity details
    jurisdiction: str | None = Field(default=None)
    sic_code: str | None = Field(default=None)
    incorporation_date: date | None = Field(default=None)

    # Record provenance (v2.2.3)
    source_system: str | None = Field(default="unknown")
    source_id: str | None = Field(default=None)

    # Redirect support
    redirect_to: str | None = Field(default=None, foreign_key="entities.entity_id")
    redirect_reason: str | None = Field(default=None)
    merged_at: datetime | None = Field(default=None)

    # JSON fields for flexible data
    identifiers: dict = Field(default_factory=dict, sa_column=Column(JSON))
    aliases: list = Field(default_factory=list, sa_column=Column(JSON))
    metadata_: dict = Field(default_factory=dict, sa_column=Column("metadata", JSON))

    # Timestamps
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    # Relationships
    securities: list["SecurityTable"] = Relationship(back_populates="entity")
    claims: list["ClaimTable"] = Relationship(back_populates="entity")


# =============================================================================
# Security Table
# =============================================================================


class SecurityTable(SQLModel, table=True):
    """
    Security database table.

    Maps to: entityspine.models.Security
    DB table: securities

    v2.2.3: isin/cusip/sedol/figi columns kept for backward compatibility
    but identifiers are now tracked via ClaimTable. Use IdentifierClaim
    as the canonical source of truth.
    """

    __tablename__ = "securities"

    security_id: str = Field(default_factory=generate_ulid, primary_key=True)
    entity_id: str = Field(foreign_key="entities.entity_id", index=True)
    security_type: str = Field(default="common_stock")
    description: str | None = Field(default=None)

    # Legacy identifier columns - kept for backward compatibility
    # v2.2.3: Use IdentifierClaim for identifier tracking
    isin: str | None = Field(default=None, index=True)
    cusip: str | None = Field(default=None, index=True)
    sedol: str | None = Field(default=None)
    figi: str | None = Field(default=None)

    # v2.2.3: Record provenance
    source_system: str | None = Field(default="unknown")
    source_id: str | None = Field(default=None)

    # JSON metadata
    metadata_: dict = Field(default_factory=dict, sa_column=Column("metadata", JSON))

    # Timestamps
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    # Relationships
    entity: EntityTable | None = Relationship(back_populates="securities")
    listings: list["ListingTable"] = Relationship(back_populates="security")


# =============================================================================
# Listing Table (WHERE TICKER LIVES!)
# =============================================================================


class ListingTable(SQLModel, table=True):
    """
    Listing database table.

    CRITICAL: THIS IS WHERE TICKER BELONGS!

    Maps to: entityspine.models.Listing
    DB table: listings
    """

    __tablename__ = "listings"

    listing_id: str = Field(default_factory=generate_ulid, primary_key=True)
    security_id: str = Field(foreign_key="securities.security_id", index=True)
    ticker: str = Field(index=True)  # THIS IS WHERE TICKER LIVES!
    exchange: str = Field(index=True)

    # Exchange identifiers
    mic: str | None = Field(default=None)

    # Validity period
    start_date: date | None = Field(default=None)
    end_date: date | None = Field(default=None)

    # Properties
    is_primary: bool = Field(default=False)
    currency: str | None = Field(default=None)

    # JSON metadata
    metadata_: dict = Field(default_factory=dict, sa_column=Column("metadata", JSON))

    # Timestamps
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    # Relationships
    security: SecurityTable | None = Relationship(back_populates="listings")


# =============================================================================
# Claim Table
# =============================================================================


class ClaimTable(SQLModel, table=True):
    """
    Identifier claim database table.

    Maps to: entityspine.models.IdentifierClaim
    DB table: claims
    """

    __tablename__ = "claims"

    claim_id: str = Field(default_factory=generate_ulid, primary_key=True)
    entity_id: str = Field(foreign_key="entities.entity_id", index=True)
    scheme: str = Field(index=True)
    value: str = Field(index=True)

    # Validity period
    valid_from: date | None = Field(default=None)
    valid_to: date | None = Field(default=None)

    # Provenance
    source: str = Field(default="unknown")
    confidence: float = Field(default=1.0)
    status: str = Field(default="active", index=True)
    notes: str | None = Field(default=None)

    # JSON metadata
    metadata_: dict = Field(default_factory=dict, sa_column=Column("metadata", JSON))

    # Timestamps
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    # Relationships
    entity: EntityTable | None = Relationship(back_populates="claims")
