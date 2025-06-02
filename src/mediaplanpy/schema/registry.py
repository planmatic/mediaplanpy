"""
Schema registry module for mediaplanpy.

This module provides a registry for schema versions and utilities
for loading schema definitions from bundled files (backward compatibility wrapper).
"""

import logging
from typing import Dict, Any, List, Optional

from mediaplanpy.exceptions import SchemaError, SchemaRegistryError, SchemaVersionError
from mediaplanpy.schema.manager import SchemaManager

logger = logging.getLogger("mediaplanpy.schema.registry")


class SchemaRegistry:
    """
    Registry for media plan schema versions.

    This class now serves as a backward compatibility wrapper around
    the new SchemaManager, which accesses bundled schema files directly.
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

    def load_versions_info(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Load version information from bundled schema files.

        Args:
            force_refresh: Deprecated. No refresh needed for bundled files.

        Returns:
            Dictionary containing version information.
        """
        if force_refresh:
            logger.debug("force_refresh parameter ignored for bundled schemas")

        try:
            supported_versions = self._schema_manager.get_supported_versions()

            # Determine current version (highest version number)
            current_version = supported_versions[-1] if supported_versions else "v1.0.0"

            return {
                "current": current_version,
                "supported": supported_versions,
                "deprecated": [],  # No deprecated versions for now
                "description": "Schema versions bundled with mediaplanpy SDK"
            }
        except Exception as e:
            logger.error(f"Error loading version info: {e}")
            # Fallback to default
            return {
                "current": "v1.0.0",
                "supported": ["v0.0.0", "v1.0.0"],
                "deprecated": [],
                "description": "Default schema version configuration"
            }

    def get_current_version(self) -> str:
        """
        Get the current (latest) schema version.

        Returns:
            The current schema version string.
        """
        versions_info = self.load_versions_info()
        return versions_info.get("current", "v1.0.0")

    def get_supported_versions(self) -> List[str]:
        """
        Get a list of supported schema versions.

        Returns:
            List of supported schema version strings.
        """
        return self._schema_manager.get_supported_versions()

    def is_version_supported(self, version: str) -> bool:
        """
        Check if a specific schema version is supported.

        Args:
            version: The schema version to check.

        Returns:
            True if the version is supported, False otherwise.
        """
        return version in self.get_supported_versions()

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
            raise SchemaVersionError(
                f"Schema version '{version}' is not supported. "
                f"Supported versions: {', '.join(supported)}"
            )

    def get_schema_path(self, version: str, schema_name: str) -> str:
        """
        Get the repository path for a specific schema.

        Args:
            version: The schema version.
            schema_name: The schema file name.

        Returns:
            The path to the schema (for backward compatibility).

        Note:
            This method is deprecated as schemas are now bundled.
        """
        logger.warning("get_schema_path is deprecated for bundled schemas")
        return f"bundled://schemas/{version}/{schema_name}"

    def get_local_schema_path(self, version: str, schema_name: str) -> str:
        """
        Get the local path for a specific schema.

        Args:
            version: The schema version.
            schema_name: The schema file name.

        Returns:
            The path to the bundled schema file.

        Note:
            This method is deprecated as schemas are now bundled.
        """
        logger.warning("get_local_schema_path is deprecated for bundled schemas")
        return str(self._schema_manager._get_schema_path(version, schema_name))

    def load_schema(self, version: Optional[str] = None,
                   schema_name: str = "mediaplan.schema.json",
                   force_refresh: bool = False) -> Dict[str, Any]:
        """
        Load a specific schema version.

        Args:
            version: The schema version to load. If None, uses the current version.
            schema_name: The schema file name to load.
            force_refresh: Deprecated. No refresh needed for bundled files.

        Returns:
            The schema as a dictionary.

        Raises:
            SchemaRegistryError: If the schema cannot be loaded.
            SchemaVersionError: If the schema version is not supported.
        """
        if force_refresh:
            logger.debug("force_refresh parameter ignored for bundled schemas")

        # Determine version if not specified
        if version is None:
            version = self.get_current_version()

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
            return self._schema_manager.get_schema(schema_type, version)
        except FileNotFoundError as e:
            raise SchemaRegistryError(f"Schema not found: {e}")
        except ValueError as e:
            raise SchemaVersionError(f"Invalid schema request: {e}")
        except Exception as e:
            raise SchemaRegistryError(f"Error loading schema: {e}")

    def load_all_schemas(self, version: Optional[str] = None,
                        force_refresh: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        Load all schemas for a specific version.

        Args:
            version: The schema version to load. If None, uses the current version.
            force_refresh: Deprecated. No refresh needed for bundled files.

        Returns:
            Dictionary mapping schema filenames to schema definitions.

        Raises:
            SchemaRegistryError: If any schema cannot be loaded.
            SchemaVersionError: If the schema version is not supported.
        """
        if force_refresh:
            logger.debug("force_refresh parameter ignored for bundled schemas")

        # Determine version if not specified
        if version is None:
            version = self.get_current_version()

        try:
            schemas = self._schema_manager.get_all_schemas(version)

            # Convert to filename-based mapping for backward compatibility
            filename_schemas = {}
            for schema_type, schema_data in schemas.items():
                filename = f"{schema_type}.schema.json"
                filename_schemas[filename] = schema_data

            return filename_schemas

        except Exception as e:
            raise SchemaRegistryError(f"Error loading schemas for version {version}: {e}")

    # Deprecated properties for backward compatibility
    @property
    def repo_url(self) -> str:
        """Deprecated: Repository URL is no longer used."""
        return "bundled://schemas"

    @property
    def local_cache_dir(self) -> str:
        """Deprecated: Local cache directory is no longer used."""
        return "bundled://cache"