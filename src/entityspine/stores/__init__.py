"""
EntitySpine Stores - Storage backends.

Tier 0-1 stores use ONLY stdlib (zero external dependencies):
- JsonEntityStore: In-memory with JSON file persistence (Tier 0)
- SqliteStore: SQLite using stdlib sqlite3 (Tier 1)

Higher-tier stores require optional dependencies:
- DuckDbStore: Analytics-optimized (Tier 2) - [duckdb] extra
- PostgresStore: Production (Tier 3) - [postgres] extra

ORM-based stores (SqlModelStore) are in entityspine.adapters.orm
and require the [orm] extra.

ALL stores return domain dataclasses (entityspine.domain.*).
"""

from entityspine.stores.json_store import JsonEntityStore
from entityspine.stores.sqlite_store import SqliteStore

__all__ = [
    "JsonEntityStore",
    "SqliteStore",
]

# Optional: SqlModelStore (requires [orm] extra)
# from entityspine.adapters.orm import SqlModelStore
