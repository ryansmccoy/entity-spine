"""
ORM layer for EntitySpine (optional).

This module provides SQLModel/SQLAlchemy-based database tables and repositories.
This is an OPTIONAL adapter - requires the [orm] extra.

Installation:
    pip install entityspine[orm]

Use cases:
- Advanced relational queries
- Integration with existing SQLAlchemy apps
- Async database access (PostgreSQL)

CRITICAL DESIGN PRINCIPLE:
ORM models are for persistence mapping only. All ORM operations should
convert rows to/from domain dataclasses at the boundary.

SQLModel = Pydantic + SQLAlchemy, providing:
- Type-safe ORM with validation
- Easy conversion between models and DB rows
- Async support for PostgreSQL (Tier 3)
"""

from entityspine.adapters.orm.engine import (
    create_sqlite_engine,
    create_tables,
    get_session,
)
from entityspine.adapters.orm.sqlmodel_store import SqlModelStore
from entityspine.adapters.orm.tables import (
    ClaimTable,
    EntityTable,
    ListingTable,
    SecurityTable,
)

__all__ = [
    "ClaimTable",
    # Tables
    "EntityTable",
    "ListingTable",
    "SecurityTable",
    # Store
    "SqlModelStore",
    # Engine
    "create_sqlite_engine",
    "create_tables",
    "get_session",
]
