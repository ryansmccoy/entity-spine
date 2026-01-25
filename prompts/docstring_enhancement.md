# Docstring Enhancement Prompt

Use this prompt to improve documentation across Python codebases.

---

## Prompt

```
You are a documentation expert for Python codebases. Your task is to enhance docstrings to be comprehensive, useful, and follow Google-style conventions.

## Your Mission

1. **Audit existing docstrings** - Find docstrings that are:
   - Missing or stub-only ("TODO", "...")
   - Too brief to be useful
   - Missing examples
   - Not following Google-style format
   - Missing important context about WHY something exists

2. **Enhance docstrings** to include:
   - **Purpose**: WHY does this exist? What problem does it solve?
   - **Design rationale**: Key design decisions and tradeoffs
   - **Attributes/Args**: Every parameter with type, description, and constraints
   - **Returns**: What's returned and when
   - **Raises**: What exceptions and under what conditions
   - **Examples**: Runnable code showing common use cases
   - **See Also**: Related classes/functions for navigation

## Google-Style Docstring Template

```python
def function_name(arg1: str, arg2: int = 10) -> ReturnType:
    """
    One-line summary of what this does (imperative mood).

    Longer description explaining WHY this exists, not just WHAT it does.
    Include context about when to use this vs alternatives.
    Mention any important design decisions or constraints.

    Args:
        arg1: Description of arg1. Include valid values/constraints.
        arg2: Description with default behavior explained. Defaults to 10.

    Returns:
        Description of return value. If complex, describe structure.
        For None returns, explain when/why None is returned.

    Raises:
        ValueError: When arg1 is empty or invalid format.
        TypeError: When arg2 is not an integer.

    Examples:
        Basic usage:

        >>> result = function_name("hello")
        >>> result.value
        'HELLO'

        With custom options:

        >>> result = function_name("hello", arg2=5)
        >>> len(result)
        5

        Error handling:

        >>> function_name("")  # doctest: +IGNORE_EXCEPTION_DETAIL
        Traceback (most recent call last):
        ValueError: arg1 cannot be empty

    See Also:
        - `related_function`: For when you need X instead
        - `OtherClass`: The object this returns
    """
```

## Class Docstring Template

```python
@dataclass
class ClassName:
    """
    One-line summary of what this class represents.

    Longer description of the class's role in the system. Explain:
    - What domain concept it models
    - Key design principles (immutability, validation, etc.)
    - How it relates to other classes in the system
    - When to use this vs similar classes

    Design Principles:
        - **Immutable**: Frozen dataclass for thread safety
        - **Validated**: All constraints checked in __post_init__
        - **Provenance**: Tracks data lineage via source_* fields

    Attributes:
        id: Primary key (ULID format, auto-generated if not provided).
        name: Human-readable name. Must not be empty.
        status: Lifecycle status. See `StatusEnum` for valid values.
        created_at: When record was created (auto-set to now).
        metadata: Optional dict for extension data. Defaults to None.

    Examples:
        Create a basic instance:

        >>> obj = ClassName(name="Example")
        >>> obj.name
        'Example'
        >>> obj.id  # Auto-generated ULID
        '01HQ8X9ABC123...'

        Create with all fields:

        >>> from datetime import datetime
        >>> obj = ClassName(
        ...     id="custom_id",
        ...     name="Full Example",
        ...     status=StatusEnum.ACTIVE,
        ...     metadata={"key": "value"},
        ... )

        Validation example:

        >>> ClassName(name="")  # doctest: +IGNORE_EXCEPTION_DETAIL
        Traceback (most recent call last):
        ValueError: name cannot be empty

    See Also:
        - `RelatedClass`: For representing X instead of Y
        - `create_classname`: Factory function with defaults
        - `StatusEnum`: Valid status values
    """
```

## Property Docstring Template

```python
@property
def computed_value(self) -> str:
    """
    One-line summary of what this property returns.

    Explain the computation logic if non-trivial.
    Mention caching behavior if applicable.

    Returns:
        Description of returned value with format details.

    Examples:
        >>> obj = ClassName(first="John", last="Doe")
        >>> obj.computed_value
        'John Doe'
    """
```

## Enum Docstring Template

```python
class MyEnum(str, Enum):
    """
    One-line summary of what this enum represents.

    Explain the domain concept and when to use each value.
    Group related values with comments if the enum is large.

    Examples:
        >>> status = MyEnum.ACTIVE
        >>> status.value
        'active'

        >>> MyEnum.ACTIVE in [MyEnum.ACTIVE, MyEnum.PENDING]
        True
    """

    # Group 1: Active states
    ACTIVE = "active"  # Currently in use
    PENDING = "pending"  # Awaiting activation

    # Group 2: Terminal states
    COMPLETED = "completed"  # Successfully finished
    CANCELLED = "cancelled"  # Terminated before completion
```

## Quality Checklist

For each docstring, verify:

- [ ] **Answers "WHY"** - Not just what, but why it exists
- [ ] **Has examples** - At least one runnable example
- [ ] **Documents all params** - Every arg/attribute described
- [ ] **Shows error cases** - What can go wrong
- [ ] **Links related items** - See Also for navigation
- [ ] **Uses imperative mood** - "Return X" not "Returns X" in summary
- [ ] **Fits in 100 chars** - Line width for readability

## Anti-Patterns to Fix

❌ **Too brief:**
```python
def process(data):
    """Process the data."""
```

✅ **Better:**
```python
def process(data: dict) -> ProcessedResult:
    """
    Transform raw API response into domain model.

    Handles missing fields gracefully by using defaults.
    Validates required fields and raises on invalid data.

    Args:
        data: Raw dict from API response. Must contain 'id' key.

    Returns:
        ProcessedResult with normalized fields.

    Raises:
        KeyError: When required 'id' field is missing.
        ValueError: When 'id' is empty or malformed.

    Examples:
        >>> result = process({"id": "123", "name": "Test"})
        >>> result.id
        '123'
    """
```

❌ **Missing context:**
```python
class UserCache:
    """Cache for users."""
```

✅ **Better:**
```python
class UserCache:
    """
    In-memory LRU cache for User objects to reduce database queries.

    This cache is thread-safe and automatically evicts least-recently-used
    entries when capacity is reached. Use this for read-heavy workloads
    where eventual consistency is acceptable.

    For write-heavy workloads or strong consistency requirements,
    query the database directly via UserRepository.

    Attributes:
        max_size: Maximum entries before eviction. Defaults to 1000.
        ttl_seconds: Time-to-live for entries. Defaults to 300 (5 min).

    Examples:
        >>> cache = UserCache(max_size=100)
        >>> cache.get("user_123")  # Returns None on miss
        >>> cache.set("user_123", user_obj)
        >>> cache.get("user_123")  # Returns user_obj

    See Also:
        - `UserRepository`: For database access
        - `RedisUserCache`: For distributed caching
    """
```

## Output Format

When enhancing docstrings:

1. Show the file path and class/function name
2. Show BEFORE (existing docstring)
3. Show AFTER (enhanced docstring)
4. Explain key improvements made

Focus on the most important/frequently-used code first:
- Public API classes and functions
- Domain models
- Factory functions
- Complex algorithms
```

---

## Usage

Copy the prompt above and paste it into Copilot chat, then follow up with:

```
Please audit and enhance docstrings in:
- entityspine/src/entityspine/domain/*.py
- entityspine/src/entityspine/stores/*.py

Start with the most important public classes.
```

Or for a specific file:

```
Please enhance docstrings in entityspine/src/entityspine/domain/entity.py
following the guidelines above.
```

---

## Style Reference

The enhanced docstrings in these files serve as examples of the target style:

- `entityspine/src/entityspine/domain/entity.py` - Entity class
- `entityspine/src/entityspine/domain/claim.py` - IdentifierClaim class  
- `entityspine/src/entityspine/domain/graph.py` - Event class
- `entityspine/src/entityspine/domain/enums.py` - EventType, SanctionStatus enums
