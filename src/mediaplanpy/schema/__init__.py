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

__all__ = [
    # Core classes
    'SchemaManager',
    'SchemaRegistry',
    'SchemaValidator',
    'SchemaMigrator',

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