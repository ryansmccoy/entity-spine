"""
Database engine and session management for EntitySpine.

Provides SQLite engine creation with proper configuration:
- PRAGMA foreign_keys = ON (enforce referential integrity)
- PRAGMA journal_mode = WAL (concurrent readers, better performance)
"""

from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine


def _set_sqlite_pragma(dbapi_conn, connection_record):
    """Set SQLite pragmas for better performance and safety."""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.execute("PRAGMA journal_mode = WAL")
    cursor.close()


def create_sqlite_engine(
    db_path: Path | str,
    echo: bool = False,
):
    """
    Create a SQLite engine with proper configuration.

    Args:
        db_path: Path to SQLite database file.
        echo: Whether to echo SQL statements.

    Returns:
        SQLAlchemy engine configured for SQLite.
    """
    if isinstance(db_path, str):
        db_path = Path(db_path)

    # Ensure parent directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Create engine
    engine = create_engine(
        f"sqlite:///{db_path}",
        echo=echo,
        connect_args={"check_same_thread": False},
    )

    # Set pragmas on every connection
    event.listen(engine, "connect", _set_sqlite_pragma)

    return engine


def create_tables(engine) -> None:
    """
    Create all tables in the database.

    Args:
        engine: SQLAlchemy engine.
    """
    SQLModel.metadata.create_all(engine)


@contextmanager
def get_session(engine) -> Generator[Session, None, None]:
    """
    Get a database session with automatic cleanup.

    Usage:
        >>> with get_session(engine) as session:
        ...     session.add(entity)
        ...     session.commit()

    Args:
        engine: SQLAlchemy engine.

    Yields:
        Session for database operations.
    """
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()
