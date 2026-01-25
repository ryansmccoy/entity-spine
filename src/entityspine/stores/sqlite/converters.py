"""
Row-to-domain converters for SQLite store.

This module contains pure functions to convert sqlite3.Row objects to domain dataclasses.
These converters are used by all repositories to ensure consistent domain object creation.

IMPORTANT: Uses only stdlib types. No Pydantic, no SQLAlchemy.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, date, datetime

from entityspine.core.timestamps import from_iso8601, utc_now
from entityspine.domain import (
    Address,
    ClaimStatus,
    Entity,
    EntityStatus,
    EntityType,
    IdentifierClaim,
    IdentifierScheme,
    Listing,
    ListingStatus,
    Security,
    SecurityStatus,
    SecurityType,
    VendorNamespace,
)


def row_to_entity(row: sqlite3.Row) -> Entity:
    """
    Convert database row to Entity domain dataclass.
    
    Args:
        row: sqlite3.Row with entity columns.
        
    Returns:
        Entity domain dataclass.
    """
    return Entity(
        entity_id=row["entity_id"],
        primary_name=row["primary_name"],
        entity_type=EntityType(row["entity_type"]),
        status=EntityStatus(row["status"]),
        source_system=row["source_system"],
        source_id=row["source_id"],
        jurisdiction=row["jurisdiction"],
        sic_code=row["sic_code"],
        redirect_to=row["redirect_to"],
        created_at=from_iso8601(row["created_at"]) if row["created_at"] else utc_now(),
        updated_at=from_iso8601(row["updated_at"]) if row["updated_at"] else utc_now(),
    )


def row_to_security(row: sqlite3.Row) -> Security:
    """
    Convert database row to Security domain dataclass.
    
    Args:
        row: sqlite3.Row with security columns.
        
    Returns:
        Security domain dataclass.
    """
    return Security(
        security_id=row["security_id"],
        entity_id=row["entity_id"],
        security_type=SecurityType(row["security_type"]),
        status=SecurityStatus(row["status"]),
        description=row["description"],
        source_system=row["source_system"],
        created_at=from_iso8601(row["created_at"]) if row["created_at"] else utc_now(),
        updated_at=from_iso8601(row["updated_at"]) if row["updated_at"] else utc_now(),
    )


def row_to_listing(row: sqlite3.Row) -> Listing:
    """
    Convert database row to Listing domain dataclass.
    
    Args:
        row: sqlite3.Row with listing columns.
        
    Returns:
        Listing domain dataclass.
    """
    return Listing(
        listing_id=row["listing_id"],
        security_id=row["security_id"],
        ticker=row["ticker"],
        exchange=row["exchange"],
        mic=row["mic"],
        status=ListingStatus(row["status"]),
        is_primary=bool(row["is_primary"]),
        start_date=date.fromisoformat(row["start_date"]) if row["start_date"] else None,
        end_date=date.fromisoformat(row["end_date"]) if row["end_date"] else None,
        source_system=row["source_system"],
        created_at=from_iso8601(row["created_at"]) if row["created_at"] else utc_now(),
        updated_at=from_iso8601(row["updated_at"]) if row["updated_at"] else utc_now(),
    )


def row_to_claim(row: sqlite3.Row) -> IdentifierClaim:
    """
    Convert database row to IdentifierClaim domain dataclass.
    
    Args:
        row: sqlite3.Row with claim columns.
        
    Returns:
        IdentifierClaim domain dataclass.
    """
    return IdentifierClaim(
        claim_id=row["claim_id"],
        entity_id=row["entity_id"],
        security_id=row["security_id"],
        listing_id=row["listing_id"],
        scheme=IdentifierScheme(row["scheme"]),
        value=row["value"],
        namespace=VendorNamespace(row["namespace"])
        if row["namespace"]
        else VendorNamespace.UNKNOWN,
        status=ClaimStatus(row["status"]),
        confidence=row["confidence"],
        source=row["source"],
        valid_from=date.fromisoformat(row["valid_from"]) if row["valid_from"] else None,
        valid_to=date.fromisoformat(row["valid_to"]) if row["valid_to"] else None,
        captured_at=from_iso8601(row["captured_at"]) if row["captured_at"] else utc_now(),
        created_at=from_iso8601(row["created_at"]) if row["created_at"] else utc_now(),
        updated_at=from_iso8601(row["updated_at"]) if row["updated_at"] else utc_now(),
    )


def row_to_geo(row: sqlite3.Row) -> Geo:
    """
    Convert database row to Geo domain dataclass.
    
    Args:
        row: sqlite3.Row with geo columns.
        
    Returns:
        Geo domain dataclass.
    """
    from entityspine.domain import Geo, GeoType

    return Geo(
        geo_id=row["geo_id"],
        geo_type=GeoType(row["geo_type"]),
        name=row["name"],
        iso_code=row["iso_code"],
        parent_geo_id=row["parent_geo_id"],
    )


def row_to_address(row: sqlite3.Row) -> Address:
    """
    Convert database row to Address domain dataclass.
    
    Args:
        row: sqlite3.Row with address columns.
        
    Returns:
        Address domain dataclass.
    """
    return Address(
        address_id=row["address_id"],
        line1=row["line1"],
        line2=row["line2"],
        city=row["city"],
        region=row["region"],
        postal=row["postal"],
        country=row["country"],
        normalized_hash=row["normalized_hash"],
    )


def row_to_role_assignment(row: sqlite3.Row) -> RoleAssignment:
    """
    Convert database row to RoleAssignment domain dataclass.
    
    Args:
        row: sqlite3.Row with role_assignment columns.
        
    Returns:
        RoleAssignment domain dataclass.
    """
    from entityspine.domain import RoleAssignment, RoleType

    return RoleAssignment(
        role_assignment_id=row["role_assignment_id"],
        person_entity_id=row["person_entity_id"],
        org_entity_id=row["org_entity_id"],
        role_type=RoleType(row["role_type"]),
        title=row["title"],
        start_date=date.fromisoformat(row["start_date"]) if row["start_date"] else None,
        end_date=date.fromisoformat(row["end_date"]) if row["end_date"] else None,
        confidence=row["confidence"],
        captured_at=datetime.fromisoformat(row["captured_at"])
        if row["captured_at"]
        else datetime.now(UTC),
        source_system=row["source_system"] or "unknown",
        source_ref=row["source_ref"],
        filing_id=row["filing_id"],
        section_id=row["section_id"],
        snippet_hash=row["snippet_hash"],
    )


def row_to_relationship(row: sqlite3.Row) -> Relationship:
    """
    Convert database row to Relationship domain dataclass (generic NodeRef pattern).
    
    Args:
        row: sqlite3.Row with relationship columns.
        
    Returns:
        Relationship domain dataclass.
    """
    from entityspine.domain import NodeKind, NodeRef, Relationship, RelationshipType

    return Relationship(
        relationship_id=row["relationship_id"],
        source_ref=NodeRef(
            kind=NodeKind(row["source_kind"]),
            id=row["source_id"],
        ),
        target_ref=NodeRef(
            kind=NodeKind(row["target_kind"]),
            id=row["target_id"],
        ),
        relationship_type=RelationshipType(row["relationship_type"]),
        subtype=row["subtype"],
        valid_from=date.fromisoformat(row["valid_from"]) if row["valid_from"] else None,
        valid_to=date.fromisoformat(row["valid_to"]) if row["valid_to"] else None,
        captured_at=datetime.fromisoformat(row["captured_at"])
        if row["captured_at"]
        else datetime.now(UTC),
        source_system=row["source_system"] or "unknown",
        source_id=row["source_ref"],
        confidence=row["confidence"],
        evidence_filing_id=row["evidence_filing_id"],
        evidence_section_id=row["evidence_section_id"],
        evidence_excerpt_hash=row["evidence_excerpt_hash"],
        evidence_snippet=row["evidence_snippet"],
        metrics=json.loads(row["metrics"]) if row["metrics"] else None,
    )


def row_to_entity_relationship(row: sqlite3.Row) -> EntityRelationship:
    """
    Convert database row to EntityRelationship domain dataclass.
    
    Args:
        row: sqlite3.Row with entity_relationship columns.
        
    Returns:
        EntityRelationship domain dataclass.
    """
    from entityspine.domain.enums import ClaimStatus, RelationshipType
    from entityspine.domain.graph import EntityRelationship

    return EntityRelationship(
        relationship_id=row["relationship_id"],
        from_entity_id=row["from_entity_id"],
        to_entity_id=row["to_entity_id"],
        relationship_type=RelationshipType(row["relationship_type"]),
        valid_from=date.fromisoformat(row["valid_from"]) if row["valid_from"] else None,
        valid_to=date.fromisoformat(row["valid_to"]) if row["valid_to"] else None,
        captured_at=from_iso8601(row["captured_at"]) if row["captured_at"] else utc_now(),
        source_system=row["source_system"] or "unknown",
        source_ref=row["source_ref"],
        confidence=row["confidence"],
        status=ClaimStatus(row["status"]) if row["status"] else ClaimStatus.ACTIVE,
        evidence_text=row["evidence_text"],
        filing_id=row["filing_id"],
        created_at=from_iso8601(row["created_at"]) if row["created_at"] else utc_now(),
        updated_at=from_iso8601(row["updated_at"]) if row["updated_at"] else utc_now(),
    )
