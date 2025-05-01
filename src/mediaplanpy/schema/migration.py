"""
Schema migration module for mediaplanpy.

This module provides utilities for migrating media plans
between different schema versions.
"""

import logging
from typing import Dict, Any, List, Optional, Union, Callable

from mediaplanpy.exceptions import SchemaError, SchemaMigrationError, SchemaVersionError
from mediaplanpy.schema.registry import SchemaRegistry

logger = logging.getLogger("mediaplanpy.schema.migration")


class SchemaMigrator:
    """
    Migrator for media plan data between schema versions.

    Provides migration paths between different schema versions.
    """

    def __init__(self, registry: Optional[SchemaRegistry] = None):
        """
        Initialize a SchemaMigrator.

        Args:
            registry: Schema registry to use. If None, creates a new one.
        """
        self.registry = registry or SchemaRegistry()
        self.migration_paths = {}

        # Register built-in migration paths
        self._register_default_migrations()

    def _register_default_migrations(self):
        """Register the default migration paths."""
        # No migrations yet, but will be added as new versions are released
        # Example: self.register_migration("v0.9.0", "v1.0.0", self._migrate_v090_to_v100)
        pass

    def register_migration(self, from_version: str, to_version: str,
                          migration_func: Callable[[Dict[str, Any]], Dict[str, Any]]):
        """
        Register a migration path between two versions.

        Args:
            from_version: Source schema version.
            to_version: Target schema version.
            migration_func: Function that transforms data from source to target version.
        """
        # Check that versions are supported
        if not self.registry.is_version_supported(from_version):
            logger.warning(f"Registering migration from unsupported version: {from_version}")

        if not self.registry.is_version_supported(to_version):
            logger.warning(f"Registering migration to unsupported version: {to_version}")

        key = (from_version, to_version)
        self.migration_paths[key] = migration_func
        logger.debug(f"Registered migration path from {from_version} to {to_version}")

    def can_migrate(self, from_version: str, to_version: str) -> bool:
        """
        Check if a direct migration path exists between two versions.

        Args:
            from_version: Source schema version.
            to_version: Target schema version.

        Returns:
            True if a direct migration path exists, False otherwise.
        """
        return (from_version, to_version) in self.migration_paths

    def find_migration_path(self, from_version: str, to_version: str) -> List[str]:
        """
        Find a path of migrations to get from one version to another.

        This implements a simple breadth-first search to find a path between versions.

        Args:
            from_version: Source schema version.
            to_version: Target schema version.

        Returns:
            List of intermediate versions to migrate through, or empty list if no path found.
        """
        # If versions are the same, no migration needed
        if from_version == to_version:
            return []

        # If direct path exists, use it
        if self.can_migrate(from_version, to_version):
            return [to_version]

        # Try to find a path using BFS
        queue = [(from_version, [])]
        visited = {from_version}

        while queue:
            current, path = queue.pop(0)

            # Find all possible next steps
            for key in self.migration_paths:
                if key[0] == current:
                    next_version = key[1]

                    # If this is our target, we found a path
                    if next_version == to_version:
                        return path + [next_version]

                    # Otherwise, add to queue if not visited
                    if next_version not in visited:
                        visited.add(next_version)
                        queue.append((next_version, path + [next_version]))

        # No path found
        return []

    def migrate(self, media_plan: Dict[str, Any], from_version: str, to_version: str) -> Dict[str, Any]:
        """
        Migrate a media plan from one schema version to another.

        Args:
            media_plan: The media plan data to migrate.
            from_version: Source schema version.
            to_version: Target schema version.

        Returns:
            Migrated media plan data.

        Raises:
            SchemaVersionError: If a version is not supported.
            SchemaMigrationError: If no migration path exists or migration fails.
        """
        # Check if versions are supported
        if not self.registry.is_version_supported(from_version):
            raise SchemaVersionError(f"Source schema version '{from_version}' is not supported")

        if not self.registry.is_version_supported(to_version):
            raise SchemaVersionError(f"Target schema version '{to_version}' is not supported")

        # If versions are the same, no migration needed
        if from_version == to_version:
            return media_plan

        # Find migration path
        path = self.find_migration_path(from_version, to_version)
        if not path:
            raise SchemaMigrationError(f"No migration path found from {from_version} to {to_version}")

        # Apply migrations in sequence
        current_version = from_version
        current_data = media_plan

        for next_version in path:
            migration_key = (current_version, next_version)
            migration_func = self.migration_paths.get(migration_key)

            if not migration_func:
                raise SchemaMigrationError(f"Missing migration function from {current_version} to {next_version}")

            try:
                logger.info(f"Migrating from {current_version} to {next_version}")
                current_data = migration_func(current_data)
                current_version = next_version
            except Exception as e:
                raise SchemaMigrationError(
                    f"Error during migration from {current_version} to {next_version}: {str(e)}"
                )

        # Update the schema version in the result
        if "meta" in current_data:
            current_data["meta"]["schema_version"] = to_version

        return current_data

    # Migration functions for specific version transitions
    # These will be added as new schema versions are released

    def _migrate_example(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Example migration function (placeholder).

        Args:
            data: Media plan data to migrate.

        Returns:
            Migrated media plan data.
        """
        # This is just a placeholder for future migrations
        # Clone the data to avoid modifying the original
        result = data.copy()

        # Apply transformations here
        # ...

        return result