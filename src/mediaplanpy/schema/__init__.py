"""
Schema module for mediaplanpy.

This module provides utilities for working with media plan schemas,
including version tracking, validation, and migration. Updated for 2-digit versioning.
"""

import logging

from mediaplanpy.schema.manager import SchemaManager
from mediaplanpy.schema.registry import SchemaRegistry
from mediaplanpy.schema.validator import SchemaValidator
from mediaplanpy.schema.migration import SchemaMigrator
from mediaplanpy.schema import refs as _refs
from mediaplanpy.schema.refs import (
    SchemaRefError,
    contains_external_ref,
    contains_ref,
    resolve_refs,
)
from mediaplanpy.schema import version_utils

logger = logging.getLogger("mediaplanpy.schema")

# Create default instances for easy access
default_registry = SchemaRegistry()
default_validator = SchemaValidator(registry=default_registry)
default_migrator = SchemaMigrator(registry=default_registry)

# Convenience functions that use the default instances
def get_current_version():
    """Get the current schema version in 2-digit format."""
    return default_registry.get_current_version()

def get_supported_versions():
    """Get list of supported schema versions in 2-digit format."""
    return default_registry.get_supported_versions()

def validate(media_plan, version=None):
    """Validate a media plan against a schema version."""
    return default_validator.validate(media_plan, version)

def validate_file(file_path, version=None):
    """Validate a media plan file against a schema version."""
    return default_validator.validate_file(file_path, version)

def migrate(media_plan, from_version, to_version):
    """Migrate a media plan from one schema version to another."""
    return default_migrator.migrate(media_plan, from_version, to_version)

# Version utility functions
def is_backwards_compatible(version):
    """Check if a schema version is backwards compatible with current SDK."""
    return version_utils.is_backwards_compatible(version)

def is_forward_minor(version):
    """Check if a schema version is a forward-compatible minor version."""
    return version_utils.is_forward_minor(version)

def is_unsupported(version):
    """Check if a schema version is unsupported by current SDK."""
    return version_utils.is_unsupported(version)

def get_compatibility_type(version):
    """Get the compatibility type for a schema version."""
    return version_utils.get_compatibility_type(version)

def get_migration_recommendation(version):
    """Get migration recommendation for a schema version."""
    return version_utils.get_migration_recommendation(version)

def normalize_version(version):
    """Normalize a version string to 2-digit format."""
    return version_utils.normalize_version(version)


# ---------------------------------------------------------------------------
# Schema exposure (v3.0.10)
# ---------------------------------------------------------------------------
# These schemas ship with this package, so this package serves them. Three
# consumers need that: planmatic_ask_api re-serves them over HTTP so an agent
# can author a media plan from scratch; scripts and notebooks using the SDK
# directly get the same access without an API; and both get $ref resolution
# (see refs.py) done once, here, rather than each re-encoding this package's
# own definitions/ layout.

def get_schema(schema_type="mediaplan", version=None, resolve_refs=True, inline_local=False):
    """
    Get a schema definition, by default as a single self-contained document.

    Args:
        schema_type: "mediaplan", "campaign", "lineitem" or "dictionary".
        version: Schema version (2-digit, e.g. "3.0"). None uses the current version.
        resolve_refs: Resolve references so the result stands alone -- sibling
            documents inlined, local pointers hoisted into the result's own
            ``$defs``. Pass False for the raw on-disk document, references intact.
        inline_local: Also expand local ``#/$defs/...`` pointers in place, for a
            document with no ``$ref`` at all. Off by default: it triples the
            size of the media plan schema, whose shared custom-field definition
            is used at ~35 sites (see refs.py).

    Returns:
        The schema as a dictionary.

    Raises:
        ValueError: If schema_type or the version format is invalid.
        FileNotFoundError: If no such schema file exists for that version.
        SchemaRefError: If resolve_refs=True and a reference cannot be resolved.

    Unlike SchemaManager.get_schema, which this wraps, ``version`` defaults to
    the current version rather than a pinned "2.0", and refs are resolved by
    default -- an unresolved document is rarely what a caller wants, and never
    what a caller outside this package can use.
    """
    if version is None:
        version = get_current_version()

    schema = SchemaManager.get_schema(schema_type, version)
    if not resolve_refs:
        return schema

    # _refs.resolve_refs, not the bare name: the keyword argument above shadows it.
    return _refs.resolve_refs(schema, get_schema_bundle(version), inline_local=inline_local)


def get_schema_bundle(version=None):
    """
    Get every schema for a version, keyed by filename, with refs left intact.

    Args:
        version: Schema version (2-digit). None uses the current version.

    Returns:
        e.g. ``{"mediaplan.schema.json": {...}, "campaign.schema.json": {...}, ...}``
        -- the shape resolve_refs() consumes as its lookup table.
    """
    if version is None:
        version = get_current_version()
    return default_registry.load_all_schemas(version)


def get_example(schema_type="mediaplan", version=None):
    """
    Get a minimal valid example instance for a schema type.

    Args:
        schema_type: Currently only "mediaplan" is supported.
        version: Schema version (2-digit). None uses the current version.

    Returns:
        A JSON-serializable dict that validates against get_schema(schema_type)
        and imports successfully via MediaPlan.import_from_json.

    Raises:
        ValueError: If no example generator exists for schema_type.

    The example is **generated**, not stored. It is built by MediaPlan.create()
    -- the same code path that constructs a real plan -- so it cannot drift out
    of sync with the schema the way a checked-in fixture silently does. That
    property is the entire reason this function exists rather than a JSON file
    sitting next to the definitions.

    Values are illustrative placeholders; only the structure is meaningful.
    """
    if schema_type != "mediaplan":
        raise ValueError(
            f"No example generator for schema type '{schema_type}'. "
            f"Only 'mediaplan' is supported (campaign and lineitem appear within it)."
        )

    if version is None:
        version = get_current_version()

    # Imported here, not at module scope: mediaplanpy.models imports this
    # module, so a top-level import would be circular.
    from mediaplanpy.models import MediaPlan

    media_plan = MediaPlan.create(
        created_by_name="agent@example.com",
        campaign_name="Example Campaign",
        campaign_start_date="2026-01-01",
        campaign_end_date="2026-03-31",
        campaign_budget_total=100000,
        schema_version=f"v{version}",
        media_plan_name="Example Media Plan",
    )
    media_plan.create_lineitem({
        "name": "Example Line Item",
        "start_date": "2026-01-01",
        "end_date": "2026-03-31",
        "cost_total": 50000,
        "channel": "Social",
    }, validate=False)

    return media_plan.to_dict()

__all__ = [
    # Core classes
    'SchemaManager',
    'SchemaRegistry',
    'SchemaValidator',
    'SchemaMigrator',
    'SchemaRefError',

    # Default instances
    'default_registry',
    'default_validator',
    'default_migrator',

    # Convenience functions
    'get_current_version',
    'get_supported_versions',
    'validate',
    'validate_file',
    'migrate',

    # Schema exposure
    'get_schema',
    'get_schema_bundle',
    'get_example',
    'resolve_refs',
    'contains_ref',
    'contains_external_ref',

    # Version utility functions
    'is_backwards_compatible',
    'is_forward_minor',
    'is_unsupported',
    'get_compatibility_type',
    'get_migration_recommendation',
    'normalize_version',

    # Version utilities module
    'version_utils'
]