"""Custom exceptions for EntitySpine."""


class EntitySpineError(Exception):
    """Base exception for EntitySpine."""

    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class EntityNotFoundError(EntitySpineError):
    """Entity not found."""

    def __init__(self, identifier: str, identifier_type: str = "unknown") -> None:
        super().__init__(
            f"Entity not found: {identifier} (type: {identifier_type})",
            details={"identifier": identifier, "identifier_type": identifier_type},
        )
        self.identifier = identifier
        self.identifier_type = identifier_type


class ResolutionError(EntitySpineError):
    """Error during entity resolution."""

    def __init__(self, query: str, reason: str) -> None:
        super().__init__(
            f"Failed to resolve '{query}': {reason}",
            details={"query": query, "reason": reason},
        )
        self.query = query
        self.reason = reason


class StorageError(EntitySpineError):
    """Storage backend error."""

    def __init__(self, operation: str, reason: str) -> None:
        super().__init__(
            f"Storage error during {operation}: {reason}",
            details={"operation": operation, "reason": reason},
        )
        self.operation = operation
        self.reason = reason


class ConfigurationError(EntitySpineError):
    """Configuration error."""

    pass


class ValidationError(EntitySpineError):
    """Validation error."""

    def __init__(self, field: str, message: str) -> None:
        super().__init__(
            f"Validation error for {field}: {message}",
            details={"field": field, "message": message},
        )
        self.field = field
