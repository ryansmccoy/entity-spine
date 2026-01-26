"""
Repository pattern for EntitySpine.

Repositories provide a clean abstraction over database access:
- Encapsulate query logic
- Convert between domain models and database tables
- Enable testing with mock repositories
"""

from entityspine.adapters.orm.repositories.base import BaseRepository
from entityspine.adapters.orm.repositories.entity_repo import EntityRepository
from entityspine.adapters.orm.repositories.security_repo import SecurityRepository
from entityspine.adapters.orm.repositories.listing_repo import ListingRepository
from entityspine.adapters.orm.repositories.claim_repo import ClaimRepository

__all__ = [
    "BaseRepository",
    "EntityRepository",
    "SecurityRepository",
    "ListingRepository",
    "ClaimRepository",
]
