"""SQLite connection management with context managers."""

from __future__ import annotations

import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path


class SqliteConnectionManager:
    """
    Manages SQLite database connections with proper resource cleanup.
    
    Provides context managers for database access and handles connection lifecycle.
    Uses sqlite3.Row factory for dict-like row access.
    """

    def __init__(self, db_path: str | Path = ":memory:"):
        """
        Initialize connection manager.

        Args:
            db_path: Path to SQLite database file or ":memory:" for in-memory DB.
        """
        self.db_path = str(db_path)
        self._conn: sqlite3.Connection | None = None

    @contextmanager
    def connection(self) -> Generator[sqlite3.Connection, None, None]:
        """
        Get a database connection with row factory.
        
        Yields:
            sqlite3.Connection configured with Row factory.
            
        Example:
            >>> manager = SqliteConnectionManager("entities.db")
            >>> with manager.connection() as conn:
            ...     cursor = conn.execute("SELECT * FROM entities")
            ...     for row in cursor:
            ...         print(row["entity_id"])
        """
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row
        yield self._conn

    def execute(self, sql: str, params: tuple = (), many: bool = False) -> sqlite3.Cursor:
        """
        Execute SQL and return cursor.
        
        Args:
            sql: SQL statement to execute.
            params: Parameters for SQL statement (tuple for single, list of tuples for many).
            many: If True, use executemany for batch inserts.
            
        Returns:
            Cursor with query results.
            
        Example:
            >>> manager.execute(
            ...     "INSERT INTO entities VALUES (?, ?)",
            ...     ("ent123", "Apple Inc")
            ... )
        """
        with self.connection() as conn:
            cursor = conn.cursor()
            if many:
                cursor.executemany(sql, params)  # type: ignore
            else:
                cursor.execute(sql, params)
            conn.commit()
            return cursor

    def fetchone(self, sql: str, params: tuple = ()) -> sqlite3.Row | None:
        """
        Execute SQL and fetch one row.
        
        Args:
            sql: SQL SELECT statement.
            params: Parameters for SQL statement.
            
        Returns:
            Single row or None if no results.
        """
        cursor = self.execute(sql, params)
        return cursor.fetchone()

    def fetchall(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        """
        Execute SQL and fetch all rows.
        
        Args:
            sql: SQL SELECT statement.
            params: Parameters for SQL statement.
            
        Returns:
            List of rows (may be empty).
        """
        cursor = self.execute(sql, params)
        return cursor.fetchall()

    def close(self) -> None:
        """Close database connection if open."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> SqliteConnectionManager:
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - closes connection."""
        self.close()
