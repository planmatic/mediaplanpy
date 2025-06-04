"""
Schema validation module for mediaplanpy.

This module provides utilities for validating media plans
against the appropriate schema.
"""

import json
import logging
from typing import Dict, Any, List, Optional, Union

import jsonschema
from jsonschema import ValidationError as JsonSchemaValidationError
from jsonschema import RefResolver

from mediaplanpy.exceptions import ValidationError, SchemaError, SchemaVersionError, SchemaRegistryError
from mediaplanpy.schema.registry import SchemaRegistry
from mediaplanpy.schema.version_utils import normalize_version, is_backwards_compatible, is_unsupported

logger = logging.getLogger("mediaplanpy.schema.validator")


class SchemaValidator:
    """
    Validator for media plan data.

    Validates media plans against the appropriate schema version.
    """

    def __init__(self, registry: Optional[SchemaRegistry] = None):
        """
        Initialize a SchemaValidator.

        Args:
            registry: Schema registry to use. If None, creates a new one.
        """
        self.registry = registry or SchemaRegistry()

    def validate(self, media_plan: Dict[str, Any], version: Optional[str] = None) -> List[str]:
        """
        Validate a media plan against a schema with version compatibility checking.

        Args:
            media_plan: The media plan data to validate.
            version: The schema version to validate against. If None, uses the version
                     specified in the media plan, or the current version if not specified.

        Returns:
            List of validation error messages, empty if validation succeeds.

        Raises:
            SchemaVersionError: If the specified version is not supported.
            SchemaRegistryError: If the schema cannot be loaded.
        """
        # Determine which version to use
        if version is None:
            # Try to get version from media plan
            version = media_plan.get("meta", {}).get("schema_version")
            if version is None:
                # Fall back to current version
                version = self.registry.get_current_version()
                logger.warning(f"No schema version specified in media plan, using current: {version}")

        # Normalize version to 2-digit format for schema loading
        try:
            normalized_version = normalize_version(version)
        except Exception as e:
            raise SchemaVersionError(f"Invalid version format '{version}': {e}")

        logger.debug(f"Validating media plan against schema version {normalized_version} (original: {version})")

        # Check if normalized version is supported
        if not self.registry.is_version_supported(normalized_version):
            raise SchemaVersionError(
                f"Schema version '{version}' (normalized: '{normalized_version}') is not supported. "
                f"Supported versions: {', '.join(self.registry.get_supported_versions())}"
            )

        # Load the main schema and all related schemas for this version
        try:
            main_schema = self.registry.load_schema(normalized_version, "mediaplan.schema.json")
            all_schemas = self.registry.load_all_schemas(normalized_version)
        except SchemaRegistryError as e:
            raise SchemaRegistryError(f"Failed to load schema for validation: {str(e)}")

        # Create a resolver with bundled schemas
        # Map schema filenames to their URI references for the resolver store
        schema_store = {}
        for filename, schema_content in all_schemas.items():
            # Create URIs that match the $ref patterns used in schemas
            if filename == "mediaplan.schema.json":
                schema_store[filename] = schema_content
            elif filename == "campaign.schema.json":
                schema_store["campaign.schema.json"] = schema_content
            elif filename == "lineitem.schema.json":
                schema_store["lineitem.schema.json"] = schema_content

        # Create resolver with the schema store
        resolver = RefResolver(
            base_uri="",  # Empty base URI since we're using a store
            referrer=main_schema,
            store=schema_store
        )

        # Validate
        errors = []
        try:
            jsonschema.validate(instance=media_plan, schema=main_schema, resolver=resolver)
        except JsonSchemaValidationError as e:
            # Extract useful validation errors
            path = " -> ".join([str(p) for p in e.path]) if e.path else "root"
            errors.append(f"Validation error at {path}: {e.message}")

        # Additional custom validations can go here
        if not errors and "lineitems" in media_plan and "campaign" in media_plan:
            # Check that line items are within campaign dates
            campaign = media_plan["campaign"]
            campaign_start = campaign.get("start_date")
            campaign_end = campaign.get("end_date")

            for i, item in enumerate(media_plan["lineitems"]):
                item_start = item.get("start_date")
                item_end = item.get("end_date")

                if item_start and campaign_start and item_start < campaign_start:
                    errors.append(
                        f"Line item {i} ({item.get('id', 'unnamed')}) starts before campaign: "
                        f"{item_start} < {campaign_start}"
                    )

                if item_end and campaign_end and item_end > campaign_end:
                    errors.append(
                        f"Line item {i} ({item.get('id', 'unnamed')}) ends after campaign: "
                        f"{item_end} > {campaign_end}"
                    )

        logger.debug(f"Validation completed with {len(errors)} errors")
        return errors

    def validate_file(self, file_path: str, version: Optional[str] = None) -> List[str]:
        """
        Validate a media plan JSON file against a schema with version handling.

        Args:
            file_path: Path to the media plan JSON file.
            version: The schema version to validate against. If None, uses the version
                     specified in the media plan, or the current version if not specified.

        Returns:
            List of validation error messages, empty if validation succeeds.

        Raises:
            SchemaVersionError: If the specified version is not supported.
            SchemaRegistryError: If the schema cannot be loaded.
            ValidationError: If the file cannot be read or parsed.
        """
        try:
            with open(file_path, 'r') as f:
                media_plan = json.load(f)

            # Log the file being validated
            file_version = media_plan.get("meta", {}).get("schema_version", "unknown")
            logger.debug(f"Validating file {file_path} with schema version {file_version}")

            return self.validate(media_plan, version)

        except json.JSONDecodeError as e:
            raise ValidationError(f"Invalid JSON in {file_path}: {str(e)}")
        except Exception as e:
            raise ValidationError(f"Error reading file {file_path}: {str(e)}")