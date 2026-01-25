"""
Domain Object Mappers - Database-Agnostic Conversion Layer (v2.2.4)

This module contains pure Python functions to convert between domain dataclasses
and dictionary/row representations. NO database code here - just mapping logic.

This allows any RDBMS store (SQLite, PostgreSQL, MySQL) to reuse the same
conversion logic without duplication.
"""

import json
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

# =============================================================================
# Entity Mappers (v2.2.4 - aligned with domain/entity.py)
# =============================================================================


def entity_to_row(entity: "Entity") -> dict[str, Any]:
    """Convert Entity dataclass to database row dict."""

    now = datetime.now(UTC).isoformat()
    return {
        "entity_id": entity.entity_id,
        "primary_name": entity.primary_name,
        "entity_type": entity.entity_type.value
        if hasattr(entity.entity_type, "value")
        else entity.entity_type,
        "status": entity.status.value if hasattr(entity.status, "value") else entity.status,
        "jurisdiction": entity.jurisdiction,
        "sic_code": entity.sic_code,
        "incorporation_date": entity.incorporation_date.isoformat()
        if entity.incorporation_date
        else None,
        "source_system": entity.source_system,
        "source_id": entity.source_id,
        "redirect_to": entity.redirect_to,
        "redirect_reason": entity.redirect_reason,
        "merged_at": entity.merged_at.isoformat() if entity.merged_at else None,
        "aliases": json.dumps(list(entity.aliases)) if entity.aliases else None,
        "created_at": now,
        "updated_at": now,
    }


def row_to_entity(row: dict[str, Any]) -> "Entity":
    """Convert database row dict to Entity dataclass."""
    from entityspine.domain import Entity, EntityStatus, EntityType

    return Entity(
        entity_id=row["entity_id"],
        primary_name=row["primary_name"],
        entity_type=EntityType(row["entity_type"])
        if row.get("entity_type")
        else EntityType.ORGANIZATION,
        status=EntityStatus(row["status"]) if row.get("status") else EntityStatus.ACTIVE,
        jurisdiction=row.get("jurisdiction"),
        sic_code=row.get("sic_code"),
        incorporation_date=date.fromisoformat(row["incorporation_date"])
        if row.get("incorporation_date")
        else None,
        source_system=row.get("source_system", "unknown"),
        source_id=row.get("source_id"),
        redirect_to=row.get("redirect_to"),
        redirect_reason=row.get("redirect_reason"),
        merged_at=datetime.fromisoformat(row["merged_at"]) if row.get("merged_at") else None,
        aliases=tuple(json.loads(row["aliases"])) if row.get("aliases") else (),
    )


# =============================================================================
# Listing Mappers (v2.2.4 - aligned with domain/listing.py)
# =============================================================================


def listing_to_row(listing: "Listing") -> dict[str, Any]:
    """Convert Listing dataclass to database row dict."""

    now = datetime.now(UTC).isoformat()
    return {
        "listing_id": listing.listing_id,
        "security_id": listing.security_id,
        "ticker": listing.ticker,
        "exchange": listing.exchange,
        "mic": listing.mic,
        "start_date": listing.start_date.isoformat() if listing.start_date else None,
        "end_date": listing.end_date.isoformat() if listing.end_date else None,
        "is_primary": 1 if listing.is_primary else 0,
        "currency": listing.currency,
        "status": listing.status.value if hasattr(listing.status, "value") else listing.status,
        "source_system": listing.source_system,
        "source_id": listing.source_id,
        "created_at": now,
        "updated_at": now,
    }


def row_to_listing(row: dict[str, Any]) -> "Listing":
    """Convert database row dict to Listing dataclass."""
    from entityspine.domain import Listing, ListingStatus

    return Listing(
        listing_id=row["listing_id"],
        security_id=row["security_id"],
        ticker=row["ticker"],
        exchange=row.get("exchange", ""),
        mic=row.get("mic"),
        start_date=date.fromisoformat(row["start_date"]) if row.get("start_date") else None,
        end_date=date.fromisoformat(row["end_date"]) if row.get("end_date") else None,
        is_primary=bool(row.get("is_primary", False)),
        currency=row.get("currency"),
        status=ListingStatus(row["status"]) if row.get("status") else ListingStatus.ACTIVE,
        source_system=row.get("source_system", "unknown"),
        source_id=row.get("source_id"),
    )


# =============================================================================
# Security Mappers (v2.2.4 - aligned with domain/security.py)
# NO identifier fields - identifiers go in IdentifierClaim
# =============================================================================


def security_to_row(security: "Security") -> dict[str, Any]:
    """Convert Security dataclass to database row dict."""

    now = datetime.now(UTC).isoformat()
    return {
        "security_id": security.security_id,
        "entity_id": security.entity_id,
        "security_type": security.security_type.value
        if hasattr(security.security_type, "value")
        else security.security_type,
        "description": security.description,
        "currency": security.currency,
        "status": security.status.value if hasattr(security.status, "value") else security.status,
        "source_system": security.source_system,
        "source_id": security.source_id,
        "created_at": now,
        "updated_at": now,
    }


def row_to_security(row: dict[str, Any]) -> "Security":
    """Convert database row dict to Security dataclass."""
    from entityspine.domain import Security, SecurityStatus, SecurityType

    return Security(
        security_id=row["security_id"],
        entity_id=row["entity_id"],
        security_type=SecurityType(row["security_type"])
        if row.get("security_type")
        else SecurityType.COMMON_STOCK,
        description=row.get("description"),
        currency=row.get("currency"),
        status=SecurityStatus(row["status"]) if row.get("status") else SecurityStatus.ACTIVE,
        source_system=row.get("source_system", "unknown"),
        source_id=row.get("source_id"),
    )


# =============================================================================
# IdentifierClaim Mappers (v2.2.4 - aligned with domain/claim.py)
# =============================================================================


def claim_to_row(claim: "IdentifierClaim") -> dict[str, Any]:
    """Convert IdentifierClaim dataclass to database row dict."""

    now = datetime.now(UTC).isoformat()
    return {
        "claim_id": claim.claim_id,
        "entity_id": claim.entity_id,
        "security_id": claim.security_id,
        "listing_id": claim.listing_id,
        "scheme": claim.scheme.value if hasattr(claim.scheme, "value") else claim.scheme,
        "value": claim.value,
        "namespace": claim.namespace.value
        if hasattr(claim.namespace, "value")
        else claim.namespace,
        "source_ref": claim.source_ref,
        "captured_at": claim.captured_at.isoformat() if claim.captured_at else now,
        "valid_from": claim.valid_from.isoformat() if claim.valid_from else None,
        "valid_to": claim.valid_to.isoformat() if claim.valid_to else None,
        "source": claim.source,
        "confidence": claim.confidence,
        "status": claim.status.value if hasattr(claim.status, "value") else claim.status,
        "notes": claim.notes,
        "created_at": now,
        "updated_at": now,
    }


def row_to_claim(row: dict[str, Any]) -> "IdentifierClaim":
    """Convert database row dict to IdentifierClaim dataclass."""
    from entityspine.domain import ClaimStatus, IdentifierClaim, IdentifierScheme, VendorNamespace

    return IdentifierClaim(
        claim_id=row["claim_id"],
        entity_id=row.get("entity_id"),
        security_id=row.get("security_id"),
        listing_id=row.get("listing_id"),
        scheme=IdentifierScheme(row["scheme"]),
        value=row["value"],
        namespace=VendorNamespace(row["namespace"])
        if row.get("namespace")
        else VendorNamespace.INTERNAL,
        source_ref=row.get("source_ref"),
        captured_at=datetime.fromisoformat(row["captured_at"])
        if row.get("captured_at")
        else datetime.now(UTC),
        valid_from=date.fromisoformat(row["valid_from"]) if row.get("valid_from") else None,
        valid_to=date.fromisoformat(row["valid_to"]) if row.get("valid_to") else None,
        source=row.get("source", "unknown"),
        confidence=float(row.get("confidence", 1.0)),
        status=ClaimStatus(row["status"]) if row.get("status") else ClaimStatus.ACTIVE,
        notes=row.get("notes"),
    )


# Legacy alias for backward compatibility
identifier_to_row = claim_to_row
row_to_identifier = row_to_claim


# =============================================================================
# Knowledge Graph: Asset Mappers
# =============================================================================


def asset_to_row(asset: "Asset") -> dict[str, Any]:
    """Convert Asset dataclass to database row dict."""

    now = datetime.now(UTC).isoformat()
    return {
        "asset_id": asset.asset_id,
        "asset_type": asset.asset_type.value
        if hasattr(asset.asset_type, "value")
        else asset.asset_type,
        "name": asset.name,
        "description": getattr(asset, "description", None),
        "owner_entity_id": asset.owner_entity_id,
        "operator_entity_id": getattr(asset, "operator_entity_id", None),
        "geo_id": asset.geo_id,
        "address_id": asset.address_id,
        "status": asset.status.value if hasattr(asset.status, "value") else asset.status,
        "source_system": getattr(asset, "source_system", None),
        "source_id": getattr(asset, "source_id", None),
        "captured_at": now,
        "created_at": now,
        "updated_at": now,
    }


def row_to_asset(row: dict[str, Any]) -> "Asset":
    """Convert database row dict to Asset dataclass."""
    from entityspine.domain import Asset, AssetStatus, AssetType

    return Asset(
        asset_id=row["asset_id"],
        asset_type=AssetType(row["asset_type"]),
        name=row["name"],
        owner_entity_id=row["owner_entity_id"],
        geo_id=row.get("geo_id"),
        address_id=row.get("address_id"),
        status=AssetStatus(row["status"]) if row.get("status") else AssetStatus.ACTIVE,
    )


# =============================================================================
# Knowledge Graph: Contract Mappers
# =============================================================================


def contract_to_row(contract: "Contract") -> dict[str, Any]:
    """Convert Contract dataclass to database row dict."""

    now = datetime.now(UTC).isoformat()
    return {
        "contract_id": contract.contract_id,
        "contract_type": contract.contract_type.value
        if hasattr(contract.contract_type, "value")
        else contract.contract_type,
        "title": contract.title,
        "effective_date": contract.effective_date.isoformat() if contract.effective_date else None,
        "termination_date": contract.termination_date.isoformat()
        if contract.termination_date
        else None,
        "status": contract.status.value if hasattr(contract.status, "value") else contract.status,
        "value_usd": float(contract.value_usd) if contract.value_usd else None,
        "source_system": getattr(contract, "source_system", None),
        "source_id": getattr(contract, "source_id", None),
        "filing_id": getattr(contract, "filing_id", None),
        "captured_at": now,
        "created_at": now,
        "updated_at": now,
    }


def row_to_contract(row: dict[str, Any]) -> "Contract":
    """Convert database row dict to Contract dataclass."""
    from entityspine.domain import Contract, ContractStatus, ContractType

    return Contract(
        contract_id=row["contract_id"],
        contract_type=ContractType(row["contract_type"]),
        title=row["title"],
        effective_date=date.fromisoformat(row["effective_date"])
        if row.get("effective_date")
        else None,
        termination_date=date.fromisoformat(row["termination_date"])
        if row.get("termination_date")
        else None,
        value_usd=Decimal(str(row["value_usd"])) if row.get("value_usd") else None,
        status=ContractStatus(row["status"]) if row.get("status") else ContractStatus.ACTIVE,
    )


# =============================================================================
# Knowledge Graph: Product Mappers
# =============================================================================


def product_to_row(product: "Product") -> dict[str, Any]:
    """Convert Product dataclass to database row dict."""

    now = datetime.now(UTC).isoformat()
    return {
        "product_id": product.product_id,
        "product_type": product.product_type.value
        if hasattr(product.product_type, "value")
        else product.product_type,
        "name": product.name,
        "description": getattr(product, "description", None),
        "owner_entity_id": product.owner_entity_id,
        "status": product.status.value if hasattr(product.status, "value") else product.status,
        "source_system": getattr(product, "source_system", None),
        "source_id": getattr(product, "source_id", None),
        "captured_at": now,
        "created_at": now,
        "updated_at": now,
    }


def row_to_product(row: dict[str, Any]) -> "Product":
    """Convert database row dict to Product dataclass."""
    from entityspine.domain import Product, ProductStatus, ProductType

    return Product(
        product_id=row["product_id"],
        product_type=ProductType(row["product_type"]),
        name=row["name"],
        owner_entity_id=row["owner_entity_id"],
        status=ProductStatus(row["status"]) if row.get("status") else ProductStatus.ACTIVE,
    )


# =============================================================================
# Knowledge Graph: Brand Mappers
# =============================================================================


def brand_to_row(brand: "Brand") -> dict[str, Any]:
    """Convert Brand dataclass to database row dict."""

    now = datetime.now(UTC).isoformat()
    return {
        "brand_id": brand.brand_id,
        "name": brand.name,
        "owner_entity_id": brand.owner_entity_id,
        "description": getattr(brand, "description", None),
        "source_system": getattr(brand, "source_system", None),
        "source_id": getattr(brand, "source_id", None),
        "captured_at": now,
        "created_at": now,
        "updated_at": now,
    }


def row_to_brand(row: dict[str, Any]) -> "Brand":
    """Convert database row dict to Brand dataclass."""
    from entityspine.domain import Brand

    return Brand(
        brand_id=row["brand_id"],
        name=row["name"],
        owner_entity_id=row["owner_entity_id"],
    )


# =============================================================================
# Knowledge Graph: Event Mappers
# =============================================================================


def event_to_row(event: "Event") -> dict[str, Any]:
    """Convert Event dataclass to database row dict."""

    now = datetime.now(UTC).isoformat()
    return {
        "event_id": event.event_id,
        "event_type": event.event_type.value
        if hasattr(event.event_type, "value")
        else event.event_type,
        "title": event.title,
        "description": getattr(event, "description", None),
        "status": event.status.value if hasattr(event.status, "value") else event.status,
        "occurred_on": event.occurred_on.isoformat() if event.occurred_on else None,
        "announced_on": event.announced_on.isoformat() if event.announced_on else None,
        "payload": json.dumps(event.payload) if event.payload else None,
        "evidence_filing_id": event.evidence_filing_id,
        "evidence_section_id": getattr(event, "evidence_section_id", None),
        "evidence_snippet": getattr(event, "evidence_snippet", None),
        "confidence": event.confidence,
        "source_system": getattr(event, "source_system", None),
        "source_id": getattr(event, "source_id", None),
        "captured_at": now,
        "created_at": now,
        "updated_at": now,
    }


def row_to_event(row: dict[str, Any]) -> "Event":
    """Convert database row dict to Event dataclass."""
    from entityspine.domain import Event, EventStatus, EventType

    return Event(
        event_id=row["event_id"],
        event_type=EventType(row["event_type"]),
        title=row["title"],
        occurred_on=date.fromisoformat(row["occurred_on"]) if row.get("occurred_on") else None,
        announced_on=date.fromisoformat(row["announced_on"]) if row.get("announced_on") else None,
        status=EventStatus(row["status"]) if row.get("status") else EventStatus.ANNOUNCED,
        payload=json.loads(row["payload"]) if row.get("payload") else None,
        evidence_filing_id=row.get("evidence_filing_id"),
        evidence_section_id=row.get("evidence_section_id"),
        evidence_snippet=row.get("evidence_snippet"),
        confidence=row.get("confidence", 1.0),
    )


# =============================================================================
# Graph Models: Relationship, RoleAssignment, Geo, Case, Address Mappers
# =============================================================================


def relationship_to_row(rel: "Relationship") -> dict[str, Any]:
    """Convert Relationship dataclass to database row dict."""

    now = datetime.now(UTC).isoformat()
    return {
        "relationship_id": rel.relationship_id,
        "relationship_type": rel.relationship_type.value
        if hasattr(rel.relationship_type, "value")
        else rel.relationship_type,
        "source_node_kind": rel.source.kind.value
        if hasattr(rel.source.kind, "value")
        else rel.source.kind,
        "source_node_id": rel.source.id,
        "target_node_kind": rel.target.kind.value
        if hasattr(rel.target.kind, "value")
        else rel.target.kind,
        "target_node_id": rel.target.id,
        "start_date": rel.start_date.isoformat() if rel.start_date else None,
        "end_date": rel.end_date.isoformat() if rel.end_date else None,
        "evidence_filing_id": rel.evidence_filing_id,
        "evidence_section_id": getattr(rel, "evidence_section_id", None),
        "evidence_snippet": getattr(rel, "evidence_snippet", None),
        "confidence": rel.confidence,
        "source_system": getattr(rel, "source_system", None),
        "source_id": getattr(rel, "source_id", None),
        "captured_at": now,
        "created_at": now,
        "updated_at": now,
    }


def row_to_relationship(row: dict[str, Any]) -> "Relationship":
    """Convert database row dict to Relationship dataclass."""
    from entityspine.domain import NodeKind, NodeRef, Relationship, RelationshipType

    return Relationship(
        relationship_id=row["relationship_id"],
        relationship_type=RelationshipType(row["relationship_type"]),
        source=NodeRef(
            kind=NodeKind(row["source_node_kind"]),
            id=row["source_node_id"],
        ),
        target=NodeRef(
            kind=NodeKind(row["target_node_kind"]),
            id=row["target_node_id"],
        ),
        start_date=date.fromisoformat(row["start_date"]) if row.get("start_date") else None,
        end_date=date.fromisoformat(row["end_date"]) if row.get("end_date") else None,
        evidence_filing_id=row.get("evidence_filing_id"),
        evidence_section_id=row.get("evidence_section_id"),
        evidence_snippet=row.get("evidence_snippet"),
        confidence=row.get("confidence", 1.0),
    )


def role_assignment_to_row(role: "RoleAssignment") -> dict[str, Any]:
    """Convert RoleAssignment dataclass to database row dict."""

    now = datetime.now(UTC).isoformat()
    return {
        "role_id": role.role_id,
        "person_entity_id": role.person_entity_id,
        "org_entity_id": role.org_entity_id,
        "role_type": role.role_type.value if hasattr(role.role_type, "value") else role.role_type,
        "title": role.title,
        "start_date": role.start_date.isoformat() if role.start_date else None,
        "end_date": role.end_date.isoformat() if role.end_date else None,
        "evidence_filing_id": getattr(role, "evidence_filing_id", None),
        "source_system": getattr(role, "source_system", None),
        "source_id": getattr(role, "source_id", None),
        "captured_at": now,
        "created_at": now,
        "updated_at": now,
    }


def row_to_role_assignment(row: dict[str, Any]) -> "RoleAssignment":
    """Convert database row dict to RoleAssignment dataclass."""
    from entityspine.domain import RoleAssignment, RoleType

    return RoleAssignment(
        role_id=row["role_id"],
        person_entity_id=row["person_entity_id"],
        org_entity_id=row["org_entity_id"],
        role_type=RoleType(row["role_type"]),
        title=row.get("title"),
        start_date=date.fromisoformat(row["start_date"]) if row.get("start_date") else None,
        end_date=date.fromisoformat(row["end_date"]) if row.get("end_date") else None,
    )


def geo_to_row(geo: "Geo") -> dict[str, Any]:
    """Convert Geo dataclass to database row dict."""

    now = datetime.now(UTC).isoformat()
    return {
        "geo_id": geo.geo_id,
        "geo_type": geo.geo_type.value if hasattr(geo.geo_type, "value") else geo.geo_type,
        "name": geo.name,
        "iso_code": geo.iso_code,
        "parent_geo_id": geo.parent_geo_id,
        "created_at": now,
        "updated_at": now,
    }


def row_to_geo(row: dict[str, Any]) -> "Geo":
    """Convert database row dict to Geo dataclass."""
    from entityspine.domain import Geo, GeoType

    return Geo(
        geo_id=row["geo_id"],
        geo_type=GeoType(row["geo_type"]),
        name=row["name"],
        iso_code=row.get("iso_code"),
        parent_geo_id=row.get("parent_geo_id"),
    )


def address_to_row(addr: "Address") -> dict[str, Any]:
    """Convert Address dataclass to database row dict."""

    now = datetime.now(UTC).isoformat()
    return {
        "address_id": addr.address_id,
        "entity_id": addr.entity_id,
        "address_type": addr.address_type.value
        if hasattr(addr.address_type, "value")
        else addr.address_type,
        "street1": addr.street1,
        "street2": getattr(addr, "street2", None),
        "city": addr.city,
        "state": addr.state,
        "postal_code": addr.postal_code,
        "country_code": addr.country_code,
        "geo_id": getattr(addr, "geo_id", None),
        "source_system": getattr(addr, "source_system", None),
        "source_id": getattr(addr, "source_id", None),
        "captured_at": now,
        "created_at": now,
        "updated_at": now,
    }


def row_to_address(row: dict[str, Any]) -> "Address":
    """Convert database row dict to Address dataclass."""
    from entityspine.domain import Address, AddressType

    return Address(
        address_id=row["address_id"],
        entity_id=row["entity_id"],
        address_type=AddressType(row["address_type"])
        if row.get("address_type")
        else AddressType.BUSINESS,
        street1=row.get("street1"),
        street2=row.get("street2"),
        city=row.get("city"),
        state=row.get("state"),
        postal_code=row.get("postal_code"),
        country_code=row.get("country_code"),
    )


def case_to_row(case: "Case") -> dict[str, Any]:
    """Convert Case dataclass to database row dict."""

    now = datetime.now(UTC).isoformat()
    return {
        "case_id": case.case_id,
        "case_type": case.case_type.value if hasattr(case.case_type, "value") else case.case_type,
        "case_number": case.case_number,
        "title": case.title,
        "status": case.status.value if hasattr(case.status, "value") else case.status,
        "authority_entity_id": case.authority_entity_id,
        "target_entity_id": case.target_entity_id,
        "opened_date": case.opened_date.isoformat() if case.opened_date else None,
        "closed_date": case.closed_date.isoformat() if case.closed_date else None,
        "description": case.description,
        "source_system": case.source_system,
        "source_ref": case.source_ref,
        "filing_id": case.filing_id,
        "captured_at": case.captured_at.isoformat()
        if hasattr(case.captured_at, "isoformat")
        else now,
        "created_at": now,
        "updated_at": now,
    }


def row_to_case(row: dict[str, Any]) -> "Case":
    """Convert database row dict to Case dataclass."""
    from entityspine.domain import Case, CaseStatus, CaseType

    return Case(
        case_id=row["case_id"],
        case_type=CaseType(row["case_type"]),
        case_number=row.get("case_number"),
        title=row["title"],
        status=CaseStatus(row["status"]) if row.get("status") else CaseStatus.UNKNOWN,
        authority_entity_id=row.get("authority_entity_id"),
        target_entity_id=row.get("target_entity_id"),
        opened_date=date.fromisoformat(row["opened_date"]) if row.get("opened_date") else None,
        closed_date=date.fromisoformat(row["closed_date"]) if row.get("closed_date") else None,
        description=row.get("description"),
        source_system=row.get("source_system", "unknown"),
        source_ref=row.get("source_ref"),
        filing_id=row.get("filing_id"),
        captured_at=datetime.fromisoformat(row["captured_at"])
        if row.get("captured_at")
        else datetime.now(UTC),
    )


# =============================================================================
# EntityCluster Mappers (v2.2.4)
# =============================================================================


def cluster_to_row(cluster: "EntityCluster") -> dict[str, Any]:
    """Convert EntityCluster dataclass to database row dict."""

    now = datetime.now(UTC).isoformat()
    return {
        "cluster_id": cluster.cluster_id,
        "reason": cluster.reason,
        "created_at": now,
        "updated_at": now,
    }


def row_to_cluster(row: dict[str, Any]) -> "EntityCluster":
    """Convert database row dict to EntityCluster dataclass."""
    from entityspine.domain import EntityCluster

    return EntityCluster(
        cluster_id=row["cluster_id"],
        reason=row.get("reason"),
        created_at=datetime.fromisoformat(row["created_at"])
        if row.get("created_at")
        else datetime.now(UTC),
        updated_at=datetime.fromisoformat(row["updated_at"])
        if row.get("updated_at")
        else datetime.now(UTC),
    )


# =============================================================================
# EntityClusterMember Mappers (v2.2.4)
# =============================================================================


def cluster_member_to_row(member: "EntityClusterMember") -> dict[str, Any]:
    """Convert EntityClusterMember dataclass to database row dict."""

    now = datetime.now(UTC).isoformat()
    return {
        "cluster_id": member.cluster_id,
        "entity_id": member.entity_id,
        "role": member.role.value if hasattr(member.role, "value") else member.role,
        "confidence": member.confidence,
        "created_at": now,
        "updated_at": now,
    }


def row_to_cluster_member(row: dict[str, Any]) -> "EntityClusterMember":
    """Convert database row dict to EntityClusterMember dataclass."""
    from entityspine.domain import ClusterRole, EntityClusterMember

    return EntityClusterMember(
        cluster_id=row["cluster_id"],
        entity_id=row["entity_id"],
        role=ClusterRole(row["role"]) if row.get("role") else ClusterRole.MEMBER,
        confidence=float(row.get("confidence", 1.0)),
        created_at=datetime.fromisoformat(row["created_at"])
        if row.get("created_at")
        else datetime.now(UTC),
        updated_at=datetime.fromisoformat(row["updated_at"])
        if row.get("updated_at")
        else datetime.now(UTC),
    )
