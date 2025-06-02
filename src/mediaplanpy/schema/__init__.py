"""
Schema module for mediaplanpy.

This module provides utilities for working with media plan schemas,
including version tracking, validation, and migration.
"""

import logging

from mediaplanpy.schema.manager import SchemaManager
from mediaplanpy.schema.registry import SchemaRegistry
from mediaplanpy.schema.validator import SchemaValidator
from mediaplanpy.schema.migration import SchemaMigrator

logger = logging.getLogger("mediaplanpy.schema")

# Create default instances for easy access
default_registry = SchemaRegistry()
default_validator = SchemaValidator(registry=default_registry)
default_migrator = SchemaMigrator(registry=default_registry)

# Convenience functions that use the default instances
def get_current_version():
    """Get the current schema version."""
    return default_registry.get_current_version()

def get_supported_versions():
    """Get list of supported schema versions."""
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

__all__ = [
    'SchemaManager',
    'SchemaRegistry',
    'SchemaValidator',
    'SchemaMigrator',
    'default_registry',
    'default_validator',
    'default_migrator',
    'get_current_version',
    'get_supported_versions',
    'validate',
    'validate_file',
    'migrate'
]