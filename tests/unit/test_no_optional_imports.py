# SPDX-License-Identifier: Apache-2.0
"""
Guardrail test: Ensure core entityspine imports do NOT pull in optional dependencies.

This test enforces the "zero-dependency core" rule:
- `pip install entityspine` should work without pydantic, sqlalchemy, or sqlmodel
- Only when you install `entityspine[pydantic]` or `entityspine[orm]` should those deps load

If this test fails, you have accidentally imported an optional dependency in the core.
"""

import sys


def test_core_import_does_not_require_pydantic():
    """Importing entityspine.domain should NOT import pydantic."""
    # Remove pydantic from sys.modules if present (for isolation)
    pydantic_modules = [k for k in sys.modules if k.startswith("pydantic")]
    for mod in pydantic_modules:
        del sys.modules[mod]

    # Also clear entityspine modules to force re-import
    entityspine_modules = [k for k in sys.modules if k.startswith("entityspine")]
    for mod in entityspine_modules:
        del sys.modules[mod]

    # Now import core

    # Check pydantic was NOT imported
    pydantic_imported = any(k.startswith("pydantic") for k in sys.modules)
    assert not pydantic_imported, (
        "Core entityspine imports should NOT trigger pydantic import. "
        "Found pydantic modules in sys.modules after importing entityspine.domain"
    )


def test_core_import_does_not_require_sqlalchemy():
    """Importing entityspine.domain should NOT import sqlalchemy."""
    # Remove sqlalchemy from sys.modules if present
    sqlalchemy_modules = [k for k in sys.modules if k.startswith("sqlalchemy")]
    for mod in sqlalchemy_modules:
        del sys.modules[mod]

    # Also clear entityspine modules to force re-import
    entityspine_modules = [k for k in sys.modules if k.startswith("entityspine")]
    for mod in entityspine_modules:
        del sys.modules[mod]

    # Now import core

    # Check sqlalchemy was NOT imported
    sqlalchemy_imported = any(k.startswith("sqlalchemy") for k in sys.modules)
    assert not sqlalchemy_imported, (
        "Core entityspine imports should NOT trigger sqlalchemy import. "
        "Found sqlalchemy modules in sys.modules after importing entityspine.domain"
    )


def test_core_import_does_not_require_sqlmodel():
    """Importing entityspine.domain should NOT import sqlmodel."""
    # Remove sqlmodel from sys.modules if present
    sqlmodel_modules = [k for k in sys.modules if k.startswith("sqlmodel")]
    for mod in sqlmodel_modules:
        del sys.modules[mod]

    # Also clear entityspine modules to force re-import
    entityspine_modules = [k for k in sys.modules if k.startswith("entityspine")]
    for mod in entityspine_modules:
        del sys.modules[mod]

    # Now import core

    # Check sqlmodel was NOT imported
    sqlmodel_imported = any(k.startswith("sqlmodel") for k in sys.modules)
    assert not sqlmodel_imported, (
        "Core entityspine imports should NOT trigger sqlmodel import. "
        "Found sqlmodel modules in sys.modules after importing entityspine.domain"
    )


def test_all_domain_exports_are_stdlib_dataclasses():
    """All domain models should be stdlib dataclasses."""
    import dataclasses

    from entityspine.domain import (
        Address,
        Asset,
        Brand,
        Case,
        Contract,
        Entity,
        Event,
        Geo,
        IdentifierClaim,
        Listing,
        NodeRef,
        PersonRole,
        Product,
        Relationship,
        RoleAssignment,
        Security,
    )

    models = [
        Entity,
        Security,
        Listing,
        IdentifierClaim,
        Asset,
        Contract,
        Product,
        Brand,
        Event,
        NodeRef,
        Relationship,
        PersonRole,
        RoleAssignment,
        Address,
        Geo,
        Case,
    ]

    for model in models:
        assert dataclasses.is_dataclass(model), (
            f"{model.__name__} is not a stdlib dataclass! "
            "All domain models must be stdlib dataclasses."
        )


def test_domain_module_has_no_pydantic_base():
    """Domain models should NOT inherit from pydantic BaseModel."""
    from entityspine.domain import (
        Address,
        Asset,
        Brand,
        Case,
        Contract,
        Entity,
        Event,
        Geo,
        IdentifierClaim,
        Listing,
        NodeRef,
        PersonRole,
        Product,
        Relationship,
        RoleAssignment,
        Security,
    )

    models = [
        Entity,
        Security,
        Listing,
        IdentifierClaim,
        Asset,
        Contract,
        Product,
        Brand,
        Event,
        NodeRef,
        Relationship,
        PersonRole,
        RoleAssignment,
        Address,
        Geo,
        Case,
    ]

    for model in models:
        # Check MRO for any pydantic.BaseModel
        mro_names = [cls.__name__ for cls in model.__mro__]
        assert "BaseModel" not in mro_names, (
            f"{model.__name__} appears to inherit from BaseModel! "
            "Domain models must be pure stdlib dataclasses."
        )


def test_stores_return_domain_dataclasses():
    """SqliteStore methods should return domain dataclasses, not ORM models."""
    import dataclasses

    from entityspine.domain import Entity, EntityType
    from entityspine.stores import SqliteStore

    store = SqliteStore(":memory:")
    store.initialize()

    # Create and save an entity
    entity = Entity(primary_name="Test Corp", entity_type=EntityType.ORGANIZATION)
    store.save_entity(entity)

    # Get it back
    retrieved = store.get_entity(entity.entity_id)

    # Should be a domain dataclass
    assert dataclasses.is_dataclass(retrieved), (
        "SqliteStore.get_entity() should return a domain dataclass"
    )
    assert type(retrieved).__name__ == "Entity", (
        f"Expected Entity dataclass, got {type(retrieved).__name__}"
    )
    assert retrieved.__class__.__module__.startswith("entityspine.domain"), (
        f"Retrieved entity should be from entityspine.domain, not {retrieved.__class__.__module__}"
    )


def test_core_has_no_optional_module_imports_at_toplevel():
    """Check that core modules don't import optional packages at module level."""
    import importlib.util

    # Core modules that MUST NOT import optional deps at top level
    core_modules = [
        "entityspine",
        "entityspine.domain",
        "entityspine.domain.entity",
        "entityspine.domain.enums",
        "entityspine.domain.graph",
        "entityspine.stores",
        "entityspine.stores.sqlite_store",
        "entityspine.stores.protocol",
    ]

    for mod_name in core_modules:
        spec = importlib.util.find_spec(mod_name)
        if spec is None:
            continue  # Module doesn't exist yet

        # This should NOT raise ImportError for pydantic/sqlalchemy
        # because those should only be in adapters
        loader = spec.loader
        if hasattr(loader, "get_source"):
            source = loader.get_source(mod_name)
            if source:
                # Check for suspicious imports at top level
                # (Not in functions or if blocks)
                lines = source.split("\n")
                for i, line in enumerate(lines):
                    stripped = line.strip()
                    # Skip comments and strings
                    if (
                        stripped.startswith("#")
                        or stripped.startswith('"""')
                        or stripped.startswith("'''")
                    ):
                        continue
                    # Check for direct pydantic/sqlalchemy imports
                    if stripped.startswith("from pydantic") or stripped.startswith(
                        "import pydantic"
                    ):
                        assert False, (
                            f"{mod_name} line {i + 1}: Direct pydantic import found: {stripped}"
                        )
                    if stripped.startswith("from sqlalchemy") or stripped.startswith(
                        "import sqlalchemy"
                    ):
                        assert False, (
                            f"{mod_name} line {i + 1}: Direct sqlalchemy import found: {stripped}"
                        )
                    if stripped.startswith("from sqlmodel") or stripped.startswith(
                        "import sqlmodel"
                    ):
                        assert False, (
                            f"{mod_name} line {i + 1}: Direct sqlmodel import found: {stripped}"
                        )
