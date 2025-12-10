"""
Schema registry module for mediaplanpy.

This module provides a registry for schema versions and utilities
for loading schema definitions from bundled files. Updated for 2-digit versioning.
"""

import logging
from typing import Dict, Any, List, Optional

from mediaplanpy.exceptions import SchemaError, SchemaRegistryError, SchemaVersionError
from mediaplanpy.schema.manager import SchemaManager
from mediaplanpy.schema.version_utils import normalize_version, validate_version_format

logger = logging.getLogger("mediaplanpy.schema.registry")


class SchemaRegistry:
    """
    Registry for media plan schema versions.

    This class serves as a backward compatibility wrapper around
    the new SchemaManager, updated for 2-digit versioning.
    """

    def __init__(self, repo_url: Optional[str] = None, local_cache_dir: Optional[str] = None):
        """
        Initialize a SchemaRegistry.

        Args:
            repo_url: Deprecated. Schema files are now bundled with the SDK.
            local_cache_dir: Deprecated. No caching is needed for bundled files.
        """
        # Log deprecation warnings for old parameters
        if repo_url is not None:
            logger.warning(
                "repo_url parameter is deprecated. Schema files are now bundled with the SDK."
            )
        if local_cache_dir is not None:
            logger.warning(
                "local_cache_dir parameter is deprecated. No caching is needed for bundled files."
            )

        # Use SchemaManager internally
        self._schema_manager = SchemaManager()

    def load_versions_info(self) -> Dict[str, Any]:
        """
        Load version information from bundled schema files.

        Returns:
            Dictionary containing version information in 2-digit format.
        """
        try:
            supported_versions = self._schema_manager.get_supported_versions()

            # Determine current version (highest version number)
            current_version = supported_versions[-1] if supported_versions else "2.0"

            return {
                "current": current_version,
                "supported": supported_versions,
                "deprecated": self._get_deprecated_versions(supported_versions),
                "description": "Schema versions bundled with mediaplanpy SDK (2-digit format)"
            }
        except Exception as e:
            logger.error(f"Error loading version info: {e}")
            # Fallback to default
            return {
                "current": "3.0",
                "supported": ["2.0", "3.0"],
                "deprecated": ["0.0", "1.0"],
                "description": "Default schema version configuration (2-digit format)"
            }

    def _get_deprecated_versions(self, supported_versions: List[str]) -> List[str]:
        """
        Determine which supported versions are deprecated.

        Args:
            supported_versions: List of all supported versions

        Returns:
            List of deprecated version strings
        """
        if not supported_versions:
            return []

        # Import current major version from main module
        try:
            from mediaplanpy import CURRENT_MAJOR
        except ImportError:
            CURRENT_MAJOR = 2

        deprecated = []
        for version in supported_versions:
            try:
                major_version = int(version.split('.')[0])
                if major_version < CURRENT_MAJOR:
                    deprecated.append(version)
            except (ValueError, IndexError):
                continue

        return deprecated

    def get_current_version(self) -> str:
        """
        Get the current (latest) schema version in 2-digit format.

        Returns:
            The current schema version string (e.g., "3.0").
        """
        versions_info = self.load_versions_info()
        return versions_info.get("current", "2.0")

    def get_supported_versions(self) -> List[str]:
        """
        Get a list of supported schema versions in 2-digit format.

        Returns:
            List of supported schema version strings (e.g., ["2.0", "3.0"]).
        """
        return self._schema_manager.get_supported_versions()

    def is_version_supported(self, version: str) -> bool:
        """
        Check if a specific schema version is supported.

        Args:
            version: The schema version to check (supports both old and new formats).

        Returns:
            True if the version is supported, False otherwise.
        """
        try:
            # Normalize version to 2-digit format for comparison
            normalized_version = normalize_version(version)
            return normalized_version in self.get_supported_versions()
        except Exception:
            return False

    def assert_version_supported(self, version: str) -> None:
        """
        Assert that a specific schema version is supported.

        Args:
            version: The schema version to check.

        Raises:
            SchemaVersionError: If the version is not supported.
        """
        if not self.is_version_supported(version):
            supported = self.get_supported_versions()
            try:
                normalized = normalize_version(version)
                raise SchemaVersionError(
                    f"Schema version '{version}' (normalized: '{normalized}') is not supported. "
                    f"Supported versions: {', '.join(supported)}"
                )
            except Exception:
                raise SchemaVersionError(
                    f"Schema version '{version}' is not supported or has invalid format. "
                    f"Supported versions: {', '.join(supported)}"
                )

    def load_schema(self, version: Optional[str] = None,
                    schema_name: str = "mediaplan.schema.json") -> Dict[str, Any]:
        """
        Load a specific schema version with 2-digit version normalization.

        Args:
            version: The schema version to load. If None, uses the current version.
            schema_name: The schema file name to load.

        Returns:
            The schema as a dictionary.

        Raises:
            SchemaRegistryError: If the schema cannot be loaded.
            SchemaVersionError: If the schema version is not supported.
        """
        # Determine version if not specified
        if version is None:
            version = self.get_current_version()

        # Normalize version to 2-digit format
        try:
            normalized_version = normalize_version(version)
        except Exception as e:
            raise SchemaVersionError(f"Invalid version format '{version}': {e}")

        # Log the version being loaded for debugging
        logger.debug(f"Loading schema {schema_name} for version {normalized_version} (original: {version})")

        # Map schema filename to schema type
        schema_type_map = {
            "mediaplan.schema.json": "mediaplan",
            "campaign.schema.json": "campaign",
            "lineitem.schema.json": "lineitem"
        }

        schema_type = schema_type_map.get(schema_name)
        if not schema_type:
            raise SchemaRegistryError(f"Unknown schema file: {schema_name}")

        try:
            return self._schema_manager.get_schema(schema_type, normalized_version)
        except FileNotFoundError as e:
            raise SchemaRegistryError(f"Schema not found: {e}")
        except ValueError as e:
            raise SchemaVersionError(f"Invalid schema request: {e}")
        except Exception as e:
            raise SchemaRegistryError(f"Error loading schema: {e}")

    def load_all_schemas(self, version: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """
        Load all schemas for a specific version with 2-digit version normalization.

        Args:
            version: The schema version to load. If None, uses the current version.

        Returns:
            Dictionary mapping schema filenames to schema definitions.

        Raises:
            SchemaRegistryError: If any schema cannot be loaded.
            SchemaVersionError: If the schema version is not supported.
        """
        # Determine version if not specified
        if version is None:
            version = self.get_current_version()

        # Normalize version to 2-digit format
        try:
            normalized_version = normalize_version(version)
        except Exception as e:
            raise SchemaVersionError(f"Invalid version format '{version}': {e}")

        logger.debug(f"Loading all schemas for version {normalized_version} (original: {version})")

        try:
            schemas = self._schema_manager.get_all_schemas(normalized_version)

            # Convert to filename-based mapping for backward compatibility
            filename_schemas = {}
            for schema_type, schema_data in schemas.items():
                filename = f"{schema_type}.schema.json"
                filename_schemas[filename] = schema_data

            return filename_schemas

        except Exception as e:
            raise SchemaRegistryError(f"Error loading schemas for version {normalized_version}: {e}")

    def is_version_supported(self, version: str) -> bool:
        """
        Check if a specific schema version is supported with version normalization.

        Args:
            version: The schema version to check (supports both old and new formats).

        Returns:
            True if the version is supported, False otherwise.
        """
        try:
            # Normalize version to 2-digit format for comparison
            normalized_version = normalize_version(version)
            supported_versions = self.get_supported_versions()

            logger.debug(f"Checking if version {version} (normalized: {normalized_version}) is in {supported_versions}")

            return normalized_version in supported_versions
        except Exception as e:
            logger.warning(f"Error checking version support for {version}: {e}")
            return False