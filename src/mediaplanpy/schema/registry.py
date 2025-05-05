"""
Schema registry module for mediaplanpy.

This module provides a registry for schema versions and utilities
for loading schema definitions from the repository.
"""

import os
import json
import logging
import requests
import pathlib
from typing import Dict, Any, List, Optional, Set, Union, Tuple

from mediaplanpy.exceptions import SchemaError, SchemaRegistryError, SchemaVersionError

logger = logging.getLogger("mediaplanpy.schema.registry")


class SchemaRegistry:
    """
    Registry for media plan schema versions.

    Provides utilities to load schema definitions from the repository
    and track supported schema versions.
    """

    # Default repository URL for schema definitions
    DEFAULT_REPO_URL = "https://raw.githubusercontent.com/laurent-colard-l5i/mediaplanschema/main/"

    # Schema files to load for each version
    SCHEMA_FILES = ["mediaplan.schema.json", "campaign.schema.json", "lineitem.schema.json"]

    def __init__(self, repo_url: Optional[str] = None, local_cache_dir: Optional[str] = None):
        """
        Initialize a SchemaRegistry.

        Args:
            repo_url: URL of the schema repository. If None, uses the default.
            local_cache_dir: Directory to cache schemas locally. If None, uses a default.
        """
        self.repo_url = repo_url or self.DEFAULT_REPO_URL

        # Set up local cache directory
        if local_cache_dir:
            self.local_cache_dir = pathlib.Path(local_cache_dir)
        else:
            # Default to ~/.mediaplanpy/schemas
            home = pathlib.Path.home()
            self.local_cache_dir = home / ".mediaplanpy" / "schemas"

        # Create cache directory if it doesn't exist
        os.makedirs(self.local_cache_dir, exist_ok=True)

        # Initialize version info and schemas
        self.versions_info = None
        self.schemas = {}

    def load_versions_info(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Load version information from repository or local cache.

        Args:
            force_refresh: If True, force a refresh from the repository.

        Returns:
            Dictionary containing version information.

        Raises:
            SchemaRegistryError: If version information cannot be loaded.
        """
        if self.versions_info is not None and not force_refresh:
            return self.versions_info

        # Try to load from local cache first
        cache_path = self.local_cache_dir / "schema_versions.json"

        try:
            # If we need to refresh or the cache doesn't exist, fetch from repository
            if force_refresh or not cache_path.exists():
                versions_url = f"{self.repo_url}/schemas/schema_versions.json"
                logger.debug(f"Fetching schema versions from {versions_url}")

                response = requests.get(versions_url)
                if response.status_code != 200:
                    raise SchemaRegistryError(f"Failed to fetch schema versions: {response.status_code}")

                versions_data = response.json()

                # Cache the versions data
                with open(cache_path, 'w') as f:
                    json.dump(versions_data, f, indent=2)
            else:
                # Load from cache
                logger.debug(f"Loading schema versions from cache: {cache_path}")
                with open(cache_path, 'r') as f:
                    versions_data = json.load(f)

            # Store and return
            self.versions_info = versions_data
            return versions_data

        except Exception as e:
            # Fallback to default version info if everything fails
            logger.warning(f"Error loading schema versions: {str(e)}. Using default.")
            default_info = {
                "current": "v0.0.0",
                "supported": ["v0.0.0"],
                "deprecated": [],
                "description": "Default schema version configuration"
            }
            self.versions_info = default_info
            return default_info

    def get_current_version(self) -> str:
        """
        Get the current (latest) schema version.

        Returns:
            The current schema version string.
        """
        versions_info = self.load_versions_info()
        return versions_info.get("current", "v0.0.0")

    def get_supported_versions(self) -> List[str]:
        """
        Get a list of supported schema versions.

        Returns:
            List of supported schema version strings.
        """
        versions_info = self.load_versions_info()
        return versions_info.get("supported", ["v0.0.0"])

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
            The full path to the schema in the repository.
        """
        return f"{self.repo_url}/schemas/{version}/{schema_name}"

    def get_local_schema_path(self, version: str, schema_name: str) -> pathlib.Path:
        """
        Get the local cache path for a specific schema.

        Args:
            version: The schema version.
            schema_name: The schema file name.

        Returns:
            Path to the local cached schema file.
        """
        return self.local_cache_dir / version / schema_name

    def load_schema(self, version: Optional[str] = None,
                   schema_name: str = "mediaplan.schema.json",
                   force_refresh: bool = False) -> Dict[str, Any]:
        """
        Load a specific schema version.

        Args:
            version: The schema version to load. If None, uses the current version.
            schema_name: The schema file name to load.
            force_refresh: If True, force a refresh from the repository.

        Returns:
            The schema as a dictionary.

        Raises:
            SchemaRegistryError: If the schema cannot be loaded.
            SchemaVersionError: If the schema version is not supported.
        """
        # Determine version if not specified
        if version is None:
            version = self.get_current_version()

        # Check if version is supported
        self.assert_version_supported(version)

        # Check if we have this schema cached in memory
        cache_key = f"{version}/{schema_name}"
        if cache_key in self.schemas and not force_refresh:
            return self.schemas[cache_key]

        # Create directory for version if it doesn't exist
        version_dir = self.local_cache_dir / version
        os.makedirs(version_dir, exist_ok=True)

        # Get local and remote paths
        local_path = self.get_local_schema_path(version, schema_name)
        remote_url = self.get_schema_path(version, schema_name)

        try:
            # If we need to refresh or the cache doesn't exist, fetch from repository
            if force_refresh or not local_path.exists():
                logger.debug(f"Fetching schema from {remote_url}")

                response = requests.get(remote_url)
                if response.status_code != 200:
                    raise SchemaRegistryError(f"Failed to fetch schema: {response.status_code}")

                schema_data = response.json()

                # Cache the schema data
                with open(local_path, 'w') as f:
                    json.dump(schema_data, f, indent=2)
            else:
                # Load from cache
                logger.debug(f"Loading schema from cache: {local_path}")
                with open(local_path, 'r') as f:
                    schema_data = json.load(f)

            # Store in memory cache and return
            self.schemas[cache_key] = schema_data
            return schema_data

        except SchemaVersionError as e:
            # Re-raise version errors
            raise
        except Exception as e:
            raise SchemaRegistryError(f"Error loading schema {schema_name} (version {version}): {str(e)}")

    def load_all_schemas(self, version: Optional[str] = None,
                        force_refresh: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        Load all schemas for a specific version.

        Args:
            version: The schema version to load. If None, uses the current version.
            force_refresh: If True, force a refresh from the repository.

        Returns:
            Dictionary mapping schema names to schema definitions.

        Raises:
            SchemaRegistryError: If any schema cannot be loaded.
            SchemaVersionError: If the schema version is not supported.
        """
        # Determine version if not specified
        if version is None:
            version = self.get_current_version()

        # Check if version is supported
        self.assert_version_supported(version)

        result = {}
        for schema_name in self.SCHEMA_FILES:
            try:
                schema = self.load_schema(version, schema_name, force_refresh)
                result[schema_name] = schema
            except SchemaRegistryError as e:
                # Re-raise with additional context
                raise SchemaRegistryError(f"Failed to load schema {schema_name}: {str(e)}")

        return result