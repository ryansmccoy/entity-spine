"""
Base Pydantic model configuration for EntitySpine.

All domain models inherit from EntitySpineModel to get consistent:
- Immutability (frozen=True for domain objects)
- Strict validation
- JSON serialization settings
- Consistent field aliases
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_serializer

from entityspine.core.timestamps import utc_now


class EntitySpineModel(BaseModel):
    """
    Base model for all EntitySpine domain objects.

    Features:
    - Immutable by default (frozen=True)
    - Strict validation
    - JSON-compatible serialization
    - Extra fields forbidden
    """

    model_config = ConfigDict(
        frozen=True,  # Immutable
        strict=True,  # Strict type checking
        extra="forbid",  # No extra fields allowed
        validate_default=True,  # Validate defaults
        use_enum_values=True,  # Use enum values in serialization
        ser_json_timedelta="float",  # Serialize timedelta as float seconds
        ser_json_bytes="base64",  # Serialize bytes as base64
    )


class MutableEntitySpineModel(BaseModel):
    """
    Mutable variant for models that need to be modified after creation.

    Use this for:
    - Builder patterns
    - Results that accumulate data
    - Internal state objects
    """

    model_config = ConfigDict(
        frozen=False,  # Mutable
        strict=True,
        extra="forbid",
        validate_default=True,
        use_enum_values=True,
    )


class TimestampedModel(EntitySpineModel):
    """
    Base model with automatic timestamps.

    Adds created_at and updated_at fields with UTC timestamps.
    """

    created_at: datetime = utc_now()
    updated_at: datetime = utc_now()

    @field_serializer("created_at", "updated_at")
    def serialize_datetime(self, value: datetime) -> str:
        """Serialize datetime as ISO 8601 string."""
        return value.isoformat()


class IdentifiedModel(TimestampedModel):
    """
    Base model with ID and timestamps.

    All persistent domain objects should inherit from this.
    """

    pass  # ID field defined in subclasses with specific names


def generate_id() -> str:
    """Generate a new ULID for entity identification."""
    from entityspine.core.ulid import generate_ulid

    return generate_ulid()
