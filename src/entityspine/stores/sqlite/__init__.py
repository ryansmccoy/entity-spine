"""
SQLite storage backend with repository pattern.

This package refactors the monolithic SqliteStore into a clean architecture:
- connection.py: Connection management
- schema.py: Database schema definitions
- converters.py: Row-to-domain conversions
- repositories/: Specialized repositories for each domain (Entity, Security, etc.)
- storage.py: Facade that orchestrates repositories
"""

from .storage import SqliteStore

__all__ = ["SqliteStore"]
