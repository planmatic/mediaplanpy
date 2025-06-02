"""
Schema manager module for mediaplanpy.

This module provides the SchemaManager class for accessing bundled schema definitions
without requiring network requests or local caching.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

import jsonschema
from jsonschema import ValidationError as JsonSchemaValidationError

logger = logging.getLogger("mediaplanpy.schema.manager")


class SchemaManager:
    """
    Provides basic access to mediaplanschema definitions.

    Accesses schema files bundled with the SDK, eliminating the need for
    network requests or local caching.
    """

    # Valid schema types
    VALID_SCHEMA_TYPES = {"mediaplan", "campaign", "lineitem"}

    # Schema file name mapping
    SCHEMA_FILES = {
        "mediaplan": "mediaplan.schema.json",
        "campaign": "campaign.schema.json",
        "lineitem": "lineitem.schema.json"
    }

    @staticmethod
    def get_schema(schema_type: str, version: str = "v1.0.0") -> Dict[str, Any]:
        """
        Get schema definition for specified type and version.

        Args:
            schema_type: "mediaplan", "campaign", or "lineitem"
            version: Schema version (default: "v1.0.0")

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

        # Validate version format
        if not version or not version.startswith('v'):
            raise ValueError(f"Invalid version format: {version}. Must start with 'v'")

        # Get schema file path
        schema_file = SchemaManager.SCHEMA_FILES[schema_type]
        schema_path = SchemaManager._get_schema_path(version, schema_file)

        # Check if file exists
        if not schema_path.exists():
            raise FileNotFoundError(
                f"Schema file not found: {schema_path}. "
                f"Version {version} may not be supported."
            )

        # Load and return schema
        try:
            with open(schema_path, 'r') as f:
                schema_data = json.load(f)

            logger.debug(f"Loaded schema {schema_type} version {version}")
            return schema_data

        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in schema file {schema_path}: {e}")
        except Exception as e:
            raise FileNotFoundError(f"Error reading schema file {schema_path}: {e}")

    @staticmethod
    def get_all_schemas(version: str = "v1.0.0") -> Dict[str, Dict[str, Any]]:
        """
        Get all schema definitions for specified version.

        Args:
            version: Schema version (default: "v1.0.0")

        Returns:
            Dictionary with schema type as key, schema definition as value
        """
        schemas = {}

        for schema_type in SchemaManager.VALID_SCHEMA_TYPES:
            try:
                schemas[schema_type] = SchemaManager.get_schema(schema_type, version)
            except (FileNotFoundError, ValueError) as e:
                logger.warning(f"Could not load {schema_type} schema for version {version}: {e}")
                # Continue loading other schemas even if one fails

        return schemas

    @staticmethod
    def get_supported_versions() -> List[str]:
        """
        Get list of supported schema versions.

        Returns:
            List of available version strings
        """
        definitions_dir = SchemaManager._get_definitions_dir()

        if not definitions_dir.exists():
            logger.warning(f"Schema definitions directory not found: {definitions_dir}")
            return []

        versions = []
        for item in definitions_dir.iterdir():
            if item.is_dir() and item.name.startswith('v'):
                # Check if this directory contains at least one valid schema file
                has_schemas = any(
                    (item / schema_file).exists()
                    for schema_file in SchemaManager.SCHEMA_FILES.values()
                )
                if has_schemas:
                    versions.append(item.name)

        # Sort versions naturally (v0.0.0, v1.0.0, etc.)
        versions.sort(key=lambda v: [int(x) for x in v[1:].split('.')])

        return versions

    @staticmethod
    def validate_against_schema(data: Dict[str, Any], schema_type: str,
                                version: str = "v1.0.0") -> bool:
        """
        Validate data against specified schema.

        Args:
            data: Data to validate
            schema_type: Schema to validate against
            version: Schema version

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
            version: Schema version (e.g., "v1.0.0")
            schema_file: Schema filename (e.g., "mediaplan.schema.json")

        Returns:
            Path to the schema file
        """
        definitions_dir = SchemaManager._get_definitions_dir()
        return definitions_dir / version / schema_file