"""
Adapters layer - Optional wrappers and integrations.

This module provides optional adapters that wrap the canonical domain models:

- pydantic/: Pydantic v2 wrappers for validation/serialization ([pydantic] extra)
- orm/: SQLModel/SQLAlchemy ORM tables and repositories ([orm] extra)

DESIGN PRINCIPLE:
Adapters are OPTIONAL. The domain dataclasses (entityspine.domain) are
the canonical source of truth. Adapters convert to/from domain at boundaries.

For storage backends, use entityspine.stores (stdlib-only for Tier 0-1).
"""

# Protocols are stdlib (no optional deps)
from entityspine.adapters.protocol import (
    EntityStoreProtocol,
    SearchProtocol,
    SecurityStoreProtocol,
    StorageLifecycleProtocol,
)

__all__ = [
    # Protocols (stdlib)
    "EntityStoreProtocol",
    "SearchProtocol",
    "SecurityStoreProtocol",
    "StorageLifecycleProtocol",
]

# Note: Pydantic wrappers available at entityspine.adapters.pydantic (requires [pydantic])
# Note: ORM layer available at entityspine.adapters.orm (requires [orm])
