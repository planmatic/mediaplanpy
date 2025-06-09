"""
Schema manager module for mediaplanpy.

This module provides the SchemaManager class for accessing bundled schema definitions
without requiring network requests or local caching. Updated to support 2-digit versioning
and v2.0 dictionary schema.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

import jsonschema
from jsonschema import ValidationError as JsonSchemaValidationError

from mediaplanpy.schema.version_utils import validate_version_format, normalize_version

logger = logging.getLogger("mediaplanpy.schema.manager")


class SchemaManager:
    """
    Provides basic access to mediaplanschema definitions.

    Accesses schema files bundled with the SDK, eliminating the need for
    network requests or local caching. Updated for 2-digit versioning and v2.0 support.
    """

    # Valid schema types - UPDATED to include dictionary for v2.0
    VALID_SCHEMA_TYPES = {"mediaplan", "campaign", "lineitem", "dictionary"}

    # Schema file name mapping - UPDATED to include dictionary
    SCHEMA_FILES = {
        "mediaplan": "mediaplan.schema.json",
        "campaign": "campaign.schema.json",
        "lineitem": "lineitem.schema.json",
        "dictionary": "dictionary.schema.json"  # NEW for v2.0
    }

    @staticmethod
    def get_schema(schema_type: str, version: str = "2.0") -> Dict[str, Any]:
        """
        Get schema definition for specified type and version.

        Args:
            schema_type: "mediaplan", "campaign", "lineitem", or "dictionary"
            version: Schema version in 2-digit format (default: "2.0")

        Returns:
            Dictionary containing the JSON schema definition

        Raises:
            FileNotFoundError: If schema file not found
            ValueError: If schema type or version invalid
        """
        # Validate schema type
        if schema_type not in SchemaManager.VALID_SCHEMA_TYPES:
            raise ValueError(
                f"Invalid schema type: {schema_type}. "
                f"Must be one of: {', '.join(SchemaManager.VALID_SCHEMA_TYPES)}"
            )

        # Validate and normalize version format
        if not validate_version_format(version):
            raise ValueError(f"Invalid version format: {version}. Expected format: 'X.Y'")

        normalized_version = normalize_version(version)

        # For dictionary schema, only available in v2.0+
        if schema_type == "dictionary":
            try:
                major_version = int(normalized_version.split('.')[0])
                if major_version < 2:
                    raise FileNotFoundError(
                        f"Dictionary schema is only available in v2.0+, requested version: {normalized_version}"
                    )
            except (ValueError, IndexError):
                raise ValueError(f"Invalid version format for dictionary schema: {normalized_version}")

        # Get schema file path
        schema_file = SchemaManager.SCHEMA_FILES[schema_type]
        schema_path = SchemaManager._get_schema_path(normalized_version, schema_file)

        # Check if file exists
        if not schema_path.exists():
            # For dictionary schema, provide more helpful error message
            if schema_type == "dictionary":
                raise FileNotFoundError(
                    f"Dictionary schema file not found: {schema_path}. "
                    f"Dictionary schema is only available in v2.0+."
                )
            else:
                raise FileNotFoundError(
                    f"Schema file not found: {schema_path}. "
                    f"Version {normalized_version} may not be supported."
                )

        # Load and return schema
        try:
            with open(schema_path, 'r') as f:
                schema_data = json.load(f)

            logger.debug(f"Loaded schema {schema_type} version {normalized_version}")
            return schema_data

        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in schema file {schema_path}: {e}")
        except Exception as e:
            raise FileNotFoundError(f"Error reading schema file {schema_path}: {e}")

    @staticmethod
    def get_all_schemas(version: str = "2.0") -> Dict[str, Dict[str, Any]]:
        """
        Get all schema definitions for specified version.

        Args:
            version: Schema version in 2-digit format (default: "2.0")

        Returns:
            Dictionary with schema type as key, schema definition as value
        """
        schemas = {}
        normalized_version = normalize_version(version)

        for schema_type in SchemaManager.VALID_SCHEMA_TYPES:
            try:
                # For dictionary schema, only load for v2.0+
                if schema_type == "dictionary":
                    try:
                        major_version = int(normalized_version.split('.')[0])
                        if major_version < 2:
                            logger.debug(f"Skipping dictionary schema for version {normalized_version} (v2.0+ only)")
                            continue
                    except (ValueError, IndexError):
                        logger.warning(f"Could not parse version {normalized_version} for dictionary schema check")
                        continue

                schemas[schema_type] = SchemaManager.get_schema(schema_type, normalized_version)
            except (FileNotFoundError, ValueError) as e:
                logger.warning(f"Could not load {schema_type} schema for version {normalized_version}: {e}")
                # Continue loading other schemas even if one fails

        return schemas

    @staticmethod
    def get_supported_versions() -> List[str]:
        """
        Get list of supported schema versions in 2-digit format.

        Returns:
            List of available version strings (e.g., ["1.0", "2.0"])
        """
        definitions_dir = SchemaManager._get_definitions_dir()

        if not definitions_dir.exists():
            logger.warning(f"Schema definitions directory not found: {definitions_dir}")
            return []

        versions = []
        for item in definitions_dir.iterdir():
            if item.is_dir():
                # Check if this looks like a 2-digit version (X.Y format)
                if SchemaManager._is_valid_version_dir(item.name):
                    # Check if this directory contains at least one valid schema file
                    has_schemas = any(
                        (item / schema_file).exists()
                        for schema_file in SchemaManager.SCHEMA_FILES.values()
                    )
                    if has_schemas:
                        versions.append(item.name)

        # Sort versions by major.minor
        def version_sort_key(v):
            try:
                parts = v.split('.')
                return (int(parts[0]), int(parts[1]))
            except (ValueError, IndexError):
                return (0, 0)

        versions.sort(key=version_sort_key)
        return versions

    @staticmethod
    def _is_valid_version_dir(dirname: str) -> bool:
        """
        Check if directory name looks like a valid 2-digit version.

        Args:
            dirname: Directory name to check

        Returns:
            True if it looks like a valid version directory
        """
        try:
            # Should be in format X.Y where X and Y are integers
            parts = dirname.split('.')
            if len(parts) == 2:
                int(parts[0])  # Check if major version is integer
                int(parts[1])  # Check if minor version is integer
                return True
        except (ValueError, IndexError):
            pass
        return False

    @staticmethod
    def validate_against_schema(data: Dict[str, Any], schema_type: str,
                                version: str = "2.0") -> bool:
        """
        Validate data against specified schema.

        Args:
            data: Data to validate
            schema_type: Schema to validate against
            version: Schema version in 2-digit format

        Returns:
            True if valid, False otherwise
        """
        try:
            schema = SchemaManager.get_schema(schema_type, version)
            jsonschema.validate(instance=data, schema=schema)
            return True
        except (JsonSchemaValidationError, FileNotFoundError, ValueError):
            return False

    @staticmethod
    def _get_definitions_dir() -> Path:
        """
        Get the path to the schema definitions directory.

        Returns:
            Path to the schema/definitions directory
        """
        # Get the directory where this module is located
        current_dir = Path(__file__).parent
        return current_dir / "definitions"

    @staticmethod
    def _get_schema_path(version: str, schema_file: str) -> Path:
        """
        Get the full path to a specific schema file.

        Args:
            version: Schema version in 2-digit format (e.g., "2.0")
            schema_file: Schema filename (e.g., "mediaplan.schema.json")

        Returns:
            Path to the schema file
        """
        definitions_dir = SchemaManager._get_definitions_dir()
        return definitions_dir / version / schema_file