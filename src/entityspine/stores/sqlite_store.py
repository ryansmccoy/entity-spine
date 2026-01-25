"""
Legacy import path for SqliteStore.

DEPRECATED: Import from entityspine.stores.sqlite instead.

This module is maintained for backward compatibility with existing code
that imports SqliteStore from the old path:

    # Old way (still works but deprecated):
    from entityspine.stores.sqlite_store import SqliteStore
    
    # New way (preferred):
    from entityspine.stores.sqlite import SqliteStore
    
    # Or simply:
    from entityspine.stores import SqliteStore

The refactored implementation lives in entityspine/stores/sqlite/ with:
- connection.py: SqliteConnectionManager
- schema.py: Database schema (SCHEMA_SQL)
- converters.py: Row-to-domain converters
- repositories/: Specialized repositories (Entity, Security, Listing, etc.)
- storage.py: SqliteStore facade

This approach maintains zero external dependencies (stdlib sqlite3 only)
while providing clean separation of concerns and following the Repository Pattern.
"""

import warnings

# Import from new location
from entityspine.stores.sqlite import SqliteStore

# Issue deprecation warning when importing from this module
warnings.warn(
    "Importing SqliteStore from 'entityspine.stores.sqlite_store' is deprecated. "
    "Use 'from entityspine.stores.sqlite import SqliteStore' or "
    "'from entityspine.stores import SqliteStore' instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["SqliteStore"]

