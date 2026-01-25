"""
Entities & Knowledge Graph API Endpoints
========================================

This module provides REST API endpoints for knowledge graph operations,
including entity management and relationship traversal.

Endpoints
---------
GET /entities
    List entities with filtering by type and search.
    
GET /entities/types
    Get available entity types with counts.
    
GET /entities/relationship-types
    Get relationship type definitions.
    
GET /entities/{entity_id}
    Get detailed entity information.
    
GET /entities/{entity_id}/relationships
    Get relationships for an entity (incoming and outgoing).
    
GET /entities/{entity_id}/mentions
    Get filing mentions of an entity.
    
GET /entities/graph/explore
    Explore knowledge graph from a starting entity.
    Returns nodes and edges for 3D visualization.
    
GET /entities/graph/path
    Find shortest path between two entities.

Entity Types
------------
Supported entity types:
- **company**: Public/private companies (linked to companies table)
- **person**: Individuals (officers, directors, investors)
- **location**: Geographic locations (headquarters, operations)
- **product**: Products, services, brands
- **event**: Events (mergers, acquisitions, lawsuits)

Relationship Types
------------------
Common relationship types:
- **subsidiary_of**: Company A is subsidiary of Company B
- **officer_of**: Person is an officer of Company
- **director_of**: Person is a director of Company
- **investor_in**: Entity has invested in Company
- **competitor_of**: Companies are competitors
- **supplier_of**: Company A supplies Company B
- **customer_of**: Company A is customer of Company B
- **partner_of**: Companies are partners
- **acquired_by**: Company A was acquired by Company B
- **located_in**: Entity is located in Location

Graph Exploration
-----------------
The explore endpoint performs breadth-first traversal:

.. code-block:: python

    # Explore 2 levels deep from Apple
    response = await client.get(
        "/api/v1/entities/graph/explore",
        params={
            "start_entity_id": apple_entity_id,
            "depth": 2,
            "max_nodes": 100
        }
    )
    
    # Returns format suitable for 3D-force-graph:
    # {
    #   "nodes": [{"id": "...", "type": "company", "name": "Apple"}],
    #   "edges": [{"source": "...", "target": "...", "type": "subsidiary_of"}]
    # }

See Also
--------
- app.models.entity : SQLAlchemy models
- react-force-graph-3d : 3D visualization library
"""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.entity import Entity, Relationship, EntityMention, RelationshipType

router = APIRouter()


@router.get("")
async def list_entities(
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    search: Optional[str] = Query(None, description="Search by name"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_session),
):
    """
    List entities with filtering and pagination.
    
    Entity types:
    - company: Companies (linked to companies table)
    - person: Individuals (officers, directors, etc.)
    - location: Geographic locations
    - product: Products and services
    - event: Events (mergers, acquisitions, etc.)
    """
    query = select(Entity)
    
    if entity_type:
        query = query.where(Entity.entity_type == entity_type)
    if search:
        query = query.where(
            Entity.search_vector.match(search) |
            Entity.name.ilike(f"%{search}%")
        )
    
    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0
    
    # Pagination
    offset = (page - 1) * page_size
    query = query.order_by(Entity.name).offset(offset).limit(page_size)
    
    result = await db.execute(query)
    entities = result.scalars().all()
    
    return {
        "entities": [
            {
                "entity_id": str(e.entity_id),
                "entity_type": e.entity_type,
                "name": e.name,
                "aliases": e.aliases,
                "company_id": str(e.company_id) if e.company_id else None,
                "confidence": float(e.confidence),
                "is_verified": e.is_verified,
            }
            for e in entities
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/types")
async def get_entity_types(
    db: AsyncSession = Depends(get_session),
):
    """
    Get list of entity types with counts.
    """
    query = (
        select(Entity.entity_type, func.count(Entity.entity_id).label("count"))
        .group_by(Entity.entity_type)
        .order_by(func.count(Entity.entity_id).desc())
    )
    result = await db.execute(query)
    rows = result.all()
    
    return {
        "types": [
            {"type": row.entity_type, "count": row.count}
            for row in rows
        ]
    }


@router.get("/relationship-types")
async def get_relationship_types(
    db: AsyncSession = Depends(get_session),
):
    """
    Get list of relationship type definitions.
    """
    query = select(RelationshipType).order_by(RelationshipType.display_name)
    result = await db.execute(query)
    types = result.scalars().all()
    
    return {
        "relationship_types": [
            {
                "name": t.name,
                "display_name": t.display_name,
                "description": t.description,
                "inverse_name": t.inverse_name,
                "source_entity_types": t.source_entity_types,
                "target_entity_types": t.target_entity_types,
            }
            for t in types
        ]
    }


@router.get("/{entity_id}")
async def get_entity(
    entity_id: UUID,
    db: AsyncSession = Depends(get_session),
):
    """
    Get detailed entity information.
    """
    result = await db.execute(
        select(Entity).where(Entity.entity_id == entity_id)
    )
    entity = result.scalar_one_or_none()
    
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    
    return {
        "entity_id": str(entity.entity_id),
        "entity_type": entity.entity_type,
        "name": entity.name,
        "normalized_name": entity.normalized_name,
        "aliases": entity.aliases,
        "company_id": str(entity.company_id) if entity.company_id else None,
        "properties": entity.properties,
        "confidence": float(entity.confidence),
        "is_verified": entity.is_verified,
        "created_at": entity.created_at.isoformat(),
    }


@router.get("/{entity_id}/relationships")
async def get_entity_relationships(
    entity_id: UUID,
    relationship_type: Optional[str] = Query(None),
    direction: Optional[str] = Query(None, description="outgoing, incoming, or both"),
    include_entities: bool = Query(True, description="Include related entity details"),
    db: AsyncSession = Depends(get_session),
):
    """
    Get relationships for an entity.
    
    Returns both outgoing (entity is source) and incoming (entity is target)
    relationships unless direction is specified.
    """
    # Build query based on direction
    conditions = []
    if direction != "incoming":
        conditions.append(Relationship.source_entity_id == entity_id)
    if direction != "outgoing":
        conditions.append(Relationship.target_entity_id == entity_id)
    
    query = select(Relationship).where(
        or_(*conditions),
        Relationship.is_current == True,
    )
    
    if relationship_type:
        query = query.where(Relationship.relationship_type == relationship_type)
    
    result = await db.execute(query)
    relationships = result.scalars().all()
    
    # Optionally load related entities
    related_entity_ids = set()
    for r in relationships:
        related_entity_ids.add(r.source_entity_id)
        related_entity_ids.add(r.target_entity_id)
    related_entity_ids.discard(entity_id)
    
    entities_map = {}
    if include_entities and related_entity_ids:
        entities_query = select(Entity).where(Entity.entity_id.in_(related_entity_ids))
        entities_result = await db.execute(entities_query)
        for e in entities_result.scalars():
            entities_map[str(e.entity_id)] = {
                "entity_id": str(e.entity_id),
                "entity_type": e.entity_type,
                "name": e.name,
            }
    
    return {
        "entity_id": str(entity_id),
        "relationships": [
            {
                "relationship_id": str(r.relationship_id),
                "relationship_type": r.relationship_type,
                "source_entity_id": str(r.source_entity_id),
                "target_entity_id": str(r.target_entity_id),
                "direction": "outgoing" if r.source_entity_id == entity_id else "incoming",
                "valid_from": r.valid_from.isoformat() if r.valid_from else None,
                "valid_to": r.valid_to.isoformat() if r.valid_to else None,
                "confidence": float(r.confidence),
                "properties": r.properties,
                "related_entity": entities_map.get(
                    str(r.target_entity_id if r.source_entity_id == entity_id else r.source_entity_id)
                ),
            }
            for r in relationships
        ],
        "count": len(relationships),
    }


@router.get("/{entity_id}/mentions")
async def get_entity_mentions(
    entity_id: UUID,
    filing_id: Optional[UUID] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_session),
):
    """
    Get mentions of an entity in filings.
    """
    query = select(EntityMention).where(EntityMention.entity_id == entity_id)
    
    if filing_id:
        query = query.where(EntityMention.filing_id == filing_id)
    
    query = query.order_by(EntityMention.created_at.desc()).limit(limit)
    
    result = await db.execute(query)
    mentions = result.scalars().all()
    
    return {
        "entity_id": str(entity_id),
        "mentions": [
            {
                "mention_id": str(m.mention_id),
                "filing_id": str(m.filing_id),
                "section_id": str(m.section_id) if m.section_id else None,
                "mention_text": m.mention_text,
                "context_text": m.context_text,
                "sentiment_score": float(m.sentiment_score) if m.sentiment_score else None,
            }
            for m in mentions
        ],
        "count": len(mentions),
    }


@router.get("/graph/explore")
async def explore_graph(
    start_entity_id: UUID = Query(..., description="Starting entity for exploration"),
    depth: int = Query(2, ge=1, le=4, description="Max relationship depth"),
    relationship_types: Optional[str] = Query(None, description="Comma-separated types to include"),
    max_nodes: int = Query(100, ge=10, le=500, description="Maximum nodes to return"),
    db: AsyncSession = Depends(get_session),
):
    """
    Explore the knowledge graph from a starting entity.
    
    Returns nodes and edges for graph visualization.
    Implements breadth-first traversal with depth limit.
    """
    types_filter = relationship_types.split(",") if relationship_types else None
    
    visited = set()
    nodes = []
    edges = []
    queue = [(start_entity_id, 0)]
    
    while queue and len(nodes) < max_nodes:
        entity_id, current_depth = queue.pop(0)
        
        if entity_id in visited:
            continue
        visited.add(entity_id)
        
        # Get entity
        entity_result = await db.execute(
            select(Entity).where(Entity.entity_id == entity_id)
        )
        entity = entity_result.scalar_one_or_none()
        
        if entity:
            nodes.append({
                "id": str(entity.entity_id),
                "type": entity.entity_type,
                "name": entity.name,
                "company_id": str(entity.company_id) if entity.company_id else None,
                "depth": current_depth,
            })
        
        # Get relationships if within depth
        if current_depth < depth:
            rel_query = select(Relationship).where(
                Relationship.is_current == True,
                or_(
                    Relationship.source_entity_id == entity_id,
                    Relationship.target_entity_id == entity_id,
                )
            )
            
            if types_filter:
                rel_query = rel_query.where(Relationship.relationship_type.in_(types_filter))
            
            rel_result = await db.execute(rel_query)
            relationships = rel_result.scalars().all()
            
            for rel in relationships:
                # Add edge
                edges.append({
                    "id": str(rel.relationship_id),
                    "source": str(rel.source_entity_id),
                    "target": str(rel.target_entity_id),
                    "type": rel.relationship_type,
                    "confidence": float(rel.confidence),
                })
                
                # Queue related entity
                other_entity_id = (
                    rel.target_entity_id 
                    if rel.source_entity_id == entity_id 
                    else rel.source_entity_id
                )
                if other_entity_id not in visited:
                    queue.append((other_entity_id, current_depth + 1))
    
    return {
        "start_entity_id": str(start_entity_id),
        "depth": depth,
        "nodes": nodes,
        "edges": edges,
        "node_count": len(nodes),
        "edge_count": len(edges),
    }


@router.get("/graph/path")
async def find_path(
    from_entity_id: UUID = Query(..., description="Source entity"),
    to_entity_id: UUID = Query(..., description="Target entity"),
    max_depth: int = Query(5, ge=1, le=10, description="Maximum path length"),
    db: AsyncSession = Depends(get_session),
):
    """
    Find shortest path between two entities in the knowledge graph.
    
    Uses bidirectional BFS for efficiency.
    """
    if from_entity_id == to_entity_id:
        return {"path": [], "found": True, "length": 0}
    
    # Simple BFS (can be optimized to bidirectional)
    visited = {from_entity_id: None}
    queue = [(from_entity_id, 0)]
    
    while queue:
        current_id, depth = queue.pop(0)
        
        if depth >= max_depth:
            continue
        
        # Get relationships
        rel_query = select(Relationship).where(
            Relationship.is_current == True,
            or_(
                Relationship.source_entity_id == current_id,
                Relationship.target_entity_id == current_id,
            )
        )
        rel_result = await db.execute(rel_query)
        relationships = rel_result.scalars().all()
        
        for rel in relationships:
            other_id = (
                rel.target_entity_id 
                if rel.source_entity_id == current_id 
                else rel.source_entity_id
            )
            
            if other_id not in visited:
                visited[other_id] = (current_id, rel)
                
                if other_id == to_entity_id:
                    # Reconstruct path
                    path = []
                    node = to_entity_id
                    while visited[node] is not None:
                        prev_node, rel = visited[node]
                        path.append({
                            "from_entity_id": str(prev_node),
                            "to_entity_id": str(node),
                            "relationship_type": rel.relationship_type,
                            "relationship_id": str(rel.relationship_id),
                        })
                        node = prev_node
                    path.reverse()
                    
                    return {
                        "found": True,
                        "length": len(path),
                        "path": path,
                    }
                
                queue.append((other_id, depth + 1))
    
    return {"found": False, "path": [], "length": -1}
