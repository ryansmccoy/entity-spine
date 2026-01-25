"""
Base repository with common CRUD operations.

All repositories inherit from this to get standard operations:
- get_by_id
- get_all
- create
- update
- delete
"""

from typing import Generic, TypeVar

from sqlmodel import Session, SQLModel, select

T = TypeVar("T", bound=SQLModel)


class BaseRepository(Generic[T]):
    """
    Base repository providing common CRUD operations.

    Type Parameters:
        T: SQLModel table type.

    Attributes:
        session: Database session.
        model: SQLModel table class.
    """

    def __init__(self, session: Session, model: type[T]):
        """
        Initialize repository.

        Args:
            session: Database session.
            model: SQLModel table class.
        """
        self._session = session
        self._model = model

    @property
    def session(self) -> Session:
        """Get the database session."""
        return self._session

    def get_by_id(self, id_value: str) -> T | None:
        """
        Get record by primary key.

        Args:
            id_value: Primary key value.

        Returns:
            Record or None if not found.
        """
        return self._session.get(self._model, id_value)

    def get_all(self, limit: int = 100, offset: int = 0) -> list[T]:
        """
        Get all records with pagination.

        Args:
            limit: Maximum records to return.
            offset: Number of records to skip.

        Returns:
            List of records.
        """
        statement = select(self._model).offset(offset).limit(limit)
        return list(self._session.exec(statement).all())

    def create(self, obj: T) -> T:
        """
        Create a new record.

        Args:
            obj: Record to create.

        Returns:
            Created record with any auto-generated fields.
        """
        self._session.add(obj)
        self._session.commit()
        self._session.refresh(obj)
        return obj

    def create_many(self, objects: list[T]) -> list[T]:
        """
        Create multiple records.

        Args:
            objects: Records to create.

        Returns:
            Created records.
        """
        for obj in objects:
            self._session.add(obj)
        self._session.commit()
        for obj in objects:
            self._session.refresh(obj)
        return objects

    def update(self, obj: T) -> T:
        """
        Update an existing record.

        Args:
            obj: Record to update.

        Returns:
            Updated record.
        """
        self._session.add(obj)
        self._session.commit()
        self._session.refresh(obj)
        return obj

    def delete(self, obj: T) -> None:
        """
        Delete a record.

        Args:
            obj: Record to delete.
        """
        self._session.delete(obj)
        self._session.commit()

    def delete_by_id(self, id_value: str) -> bool:
        """
        Delete record by primary key.

        Args:
            id_value: Primary key value.

        Returns:
            True if deleted, False if not found.
        """
        obj = self.get_by_id(id_value)
        if obj:
            self.delete(obj)
            return True
        return False

    def count(self) -> int:
        """
        Get total record count.

        Returns:
            Number of records.
        """
        from sqlalchemy import func

        statement = select(func.count()).select_from(self._model)
        return self._session.exec(statement).one()
