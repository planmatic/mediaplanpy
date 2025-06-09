"""
Schema migration module for mediaplanpy.

This module provides utilities for migrating media plans
between different schema versions with support for 2-digit versioning.
Updated for SDK v2.0 with v0.0 support completely removed.
"""

import logging
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, List, Optional, Union, Callable

from mediaplanpy.exceptions import SchemaError, SchemaMigrationError, SchemaVersionError
from mediaplanpy.schema.registry import SchemaRegistry

# Import version utils with fallback
try:
    from mediaplanpy.schema.version_utils import (
        normalize_version,
        validate_version_format,
        get_compatibility_type,
        compare_versions
    )
except ImportError:
    logger.warning("Could not import version_utils, using fallback functions")

    def normalize_version(version):
        """Fallback normalize_version function."""
        if version.startswith('v'):
            return '.'.join(version[1:].split('.')[:2])
        return version

    def get_compatibility_type(version):
        """Fallback get_compatibility_type function."""
        return "unknown"

logger = logging.getLogger("mediaplanpy.schema.migration")


class SchemaMigrator:
    """
    Migrator for media plan data between schema versions with 2-digit version support.

    Provides migration paths between different schema versions, supporting both
    legacy 3-digit format (v1.0.0) and new 2-digit format (1.0) inputs/outputs.
    IMPORTANT: v0.0 support completely removed in SDK v2.0.
    """

    def __init__(self, registry: Optional[SchemaRegistry] = None):
        """
        Initialize a SchemaMigrator.

        Args:
            registry: Schema registry to use. If None, creates a new one.
        """
        self.registry = registry or SchemaRegistry()
        self.migration_paths = {}

        # Register built-in migration paths (v0.0 support removed)
        self._register_default_migrations()

    def _register_default_migrations(self):
        """Register the default migration paths using supported 2-digit format."""
        # REMOVED: v0.0 migration paths are no longer supported in SDK v2.0
        # OLD (removed): self.register_migration("0.0", "1.0", self._migrate_00_to_10)
        # OLD (removed): self.register_migration("v0.0.0", "1.0", self._migrate_v000_to_10)
        # OLD (removed): self.register_migration("v0.0.0", "v1.0.0", self._migrate_v000_to_v100)

        # NEW: Add v1.0 → v2.0 migration path
        self.register_migration("1.0", "2.0", self._migrate_10_to_20)

        # Legacy format support for input (but output to supported format)
        # These handle legacy format inputs but migrate to 2-digit format
        self.register_migration("v1.0.0", "2.0", self._migrate_v100_to_20)

        logger.debug("Registered default migration paths for SDK v2.0 (v0.0 support removed)")

    def register_migration(self, from_version: str, to_version: str,
                          migration_func: Callable[[Dict[str, Any]], Dict[str, Any]]):
        """
        Register a migration path between two versions.

        Args:
            from_version: Source schema version (supports both old and new formats).
            to_version: Target schema version (supports both old and new formats).
            migration_func: Function that transforms data from source to target version.
        """
        # Validate that we're not registering v0.0 migrations
        if from_version.startswith("0.") or from_version.startswith("v0."):
            raise SchemaVersionError(
                f"Cannot register migration from v0.0 version '{from_version}'. "
                f"v0.0 support has been removed in SDK v2.0."
            )

        # Only validate target version against registry (source might be legacy format)
        if not self.registry.is_version_supported(to_version):
            # Try normalizing the target version
            try:
                normalized_to = normalize_version(to_version)
                if not self.registry.is_version_supported(normalized_to):
                    logger.warning(f"Target version {to_version} (normalized: {normalized_to}) not supported by registry")
            except Exception:
                logger.warning(f"Target version {to_version} format validation failed")

        key = (from_version, to_version)
        self.migration_paths[key] = migration_func
        logger.debug(f"Registered migration path from {from_version} to {to_version}")

    def migrate(self, media_plan: Dict[str, Any], from_version: str, to_version: str) -> Dict[str, Any]:
        """
        Migrate a media plan from one schema version to another with enhanced 2-digit version support.

        Args:
            media_plan: The media plan data to migrate.
            from_version: Source schema version (supports both old and new formats).
            to_version: Target schema version (supports both old and new formats).

        Returns:
            Migrated media plan data with the target version format.

        Raises:
            SchemaVersionError: If a version is not supported or is v0.0.
            SchemaMigrationError: If no migration path exists or migration fails.
        """
        logger.debug(f"Starting migration from {from_version} to {to_version}")

        # CRITICAL: Reject v0.0 versions immediately
        if from_version.startswith("0.") or from_version.startswith("v0."):
            raise SchemaVersionError(
                f"Schema version '{from_version}' (v0.0.x) is no longer supported in SDK v2.0. "
                f"Please use SDK v1.x to migrate v0.0 plans to v1.0 first, then upgrade to SDK v2.0."
            )

        # Normalize versions for compatibility checking but preserve original formats
        try:
            normalized_from = normalize_version(from_version)
            normalized_to = normalize_version(to_version)
        except Exception as e:
            raise SchemaVersionError(f"Invalid version format in migration: {e}")

        # Check if versions are the same (after normalization)
        if normalized_from == normalized_to:
            logger.debug("No migration needed - versions are equivalent")
            # Still update the version field to match target format
            result = self._update_version_in_data(media_plan, to_version)
            return result

        # Check if target version is supported by registry
        if not self.registry.is_version_supported(to_version):
            # Try with normalized version
            if not self.registry.is_version_supported(normalized_to):
                raise SchemaVersionError(
                    f"Target schema version '{to_version}' (normalized: '{normalized_to}') is not supported"
                )

        # Find migration path
        path = self.find_migration_path(from_version, to_version)
        if not path:
            raise SchemaMigrationError(f"No migration path found from {from_version} to {to_version}")

        logger.info(f"Found migration path: {from_version} -> {' -> '.join(path)}")

        # Apply migrations in sequence
        current_version = from_version
        current_data = media_plan

        for next_version in path:
            # Find the appropriate migration function
            migration_func = self._find_migration_function(current_version, next_version)

            if not migration_func:
                raise SchemaMigrationError(
                    f"Missing migration function from {current_version} to {next_version}"
                )

            try:
                logger.info(f"Migrating from {current_version} to {next_version}")
                current_data = migration_func(current_data)

                # Update the version field in the migrated data
                current_data = self._update_version_in_data(current_data, next_version)

                current_version = next_version

            except Exception as e:
                raise SchemaMigrationError(
                    f"Error during migration from {current_version} to {next_version}: {str(e)}"
                )

        # Final version update to ensure exact target format
        current_data = self._update_version_in_data(current_data, to_version)

        logger.info(f"Migration completed successfully from {from_version} to {to_version}")
        return current_data

    def can_migrate(self, from_version: str, to_version: str) -> bool:
        """
        Check if a direct migration path exists between two versions.

        Supports both exact format matching and normalized version matching.

        Args:
            from_version: Source schema version.
            to_version: Target schema version.

        Returns:
            True if a direct migration path exists, False otherwise.
        """
        # Reject v0.0 versions immediately
        if from_version.startswith("0.") or from_version.startswith("v0."):
            return False

        # First check for exact match
        if (from_version, to_version) in self.migration_paths:
            return True

        # Try normalized versions
        try:
            norm_from = normalize_version(from_version)
            norm_to = normalize_version(to_version)

            # Check all possible format combinations
            format_combinations = [
                (norm_from, norm_to),  # 2-digit to 2-digit
                (f"v{norm_from}.0", f"v{norm_to}.0"),  # 3-digit to 3-digit
                (from_version, norm_to),  # original from to normalized to
                (norm_from, to_version),  # normalized from to original to
            ]

            for from_fmt, to_fmt in format_combinations:
                if (from_fmt, to_fmt) in self.migration_paths:
                    return True

        except Exception as e:
            logger.debug(f"Version normalization failed for migration check {from_version} -> {to_version}: {e}")

        return False

    def find_migration_path(self, from_version: str, to_version: str) -> List[str]:
        """
        Find a path of migrations to get from one version to another.

        This implements breadth-first search to find the shortest migration path,
        considering both old and new version formats.

        Args:
            from_version: Source schema version.
            to_version: Target schema version.

        Returns:
            List of intermediate versions to migrate through, or empty list if no path found.
        """
        # Reject v0.0 versions immediately
        if from_version.startswith("0.") or from_version.startswith("v0."):
            logger.warning(f"Cannot find migration path from unsupported version {from_version}")
            return []

        # If versions are the same (after normalization), no migration needed
        try:
            norm_from = normalize_version(from_version)
            norm_to = normalize_version(to_version)
            if norm_from == norm_to:
                return []
        except Exception:
            # If normalization fails, continue with original versions
            if from_version == to_version:
                return []

        # If direct path exists, use it
        if self.can_migrate(from_version, to_version):
            return [to_version]

        # Build a graph of all possible migration paths (excluding v0.0)
        all_versions = set()
        for from_v, to_v in self.migration_paths.keys():
            # Skip any v0.0 versions in the graph
            if not (from_v.startswith("0.") or from_v.startswith("v0.")):
                all_versions.add(from_v)
            if not (to_v.startswith("0.") or to_v.startswith("v0.")):
                all_versions.add(to_v)

        # BFS to find shortest path
        queue = [(from_version, [])]
        visited = {from_version}

        while queue:
            current, path = queue.pop(0)

            # Check all possible next steps
            for (path_from, path_to), _ in self.migration_paths.items():
                # Skip v0.0 versions
                if path_from.startswith("0.") or path_from.startswith("v0."):
                    continue
                if path_to.startswith("0.") or path_to.startswith("v0."):
                    continue

                # Check if current version matches path_from (with normalization)
                can_use_path = False
                next_version = None

                if current == path_from:
                    can_use_path = True
                    next_version = path_to
                else:
                    # Try with normalization
                    try:
                        if normalize_version(current) == normalize_version(path_from):
                            can_use_path = True
                            next_version = path_to
                    except Exception:
                        continue

                if can_use_path and next_version and next_version not in visited:
                    new_path = path + [next_version]

                    # Check if we've reached the target
                    if next_version == to_version:
                        return new_path

                    # Also check with normalization
                    try:
                        if normalize_version(next_version) == normalize_version(to_version):
                            # Replace the last version with the target format
                            return new_path[:-1] + [to_version]
                    except Exception:
                        pass

                    visited.add(next_version)
                    queue.append((next_version, new_path))

        # No path found
        logger.warning(f"No migration path found from {from_version} to {to_version}")
        return []

    # REMOVED METHODS (no longer needed in SDK v2.0):
    # - _migrate_00_to_10() - v0.0 support completely removed
    # - _migrate_v000_to_10() - v0.0 support completely removed
    # - _migrate_v000_to_v100() - v0.0 support completely removed
    # - _perform_v0_to_v1_migration() - v0.0 support completely removed

    # NEW MIGRATION METHODS FOR SDK v2.0

    def _migrate_10_to_20(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Migrate a media plan from schema 1.0 to 2.0.

        Key changes in v2.0:
        - meta.created_by (optional) → meta.created_by_name (required)
        - All other v2.0 fields are optional, so no migration needed

        Args:
            data: Media plan data in 1.0 format.

        Returns:
            Media plan data in 2.0 format.
        """
        logger.debug("Migrating from 1.0 to 2.0")

        # Create a deep copy to avoid modifying the original
        import copy
        result = copy.deepcopy(data)

        # Update meta section for v2.0 requirements
        if "meta" in result:
            meta = result["meta"]

            # Handle created_by → created_by_name migration
            if "created_by" in meta and "created_by_name" not in meta:
                meta["created_by_name"] = meta["created_by"]
                # Keep the original created_by field for backward compatibility
                # and add created_by_id as None (user can update later)
                meta["created_by_id"] = None
                logger.debug("Migrated created_by to created_by_name")
            elif "created_by_name" not in meta:
                # If neither created_by nor created_by_name exists, set a default
                meta["created_by_name"] = meta.get("created_by", "Unknown User")
                meta["created_by_id"] = None
                logger.debug("Set default created_by_name for missing field")

        # Campaign and LineItem fields: All new v2.0 fields are optional,
        # so no migration is needed - they'll just be None/empty

        # Dictionary field: New and optional in v2.0, so no migration needed

        # Update schema version to 2.0
        result["meta"]["schema_version"] = "2.0"

        logger.debug("Completed 1.0 to 2.0 migration")
        return result

    def _migrate_v100_to_20(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Migrate a media plan from schema v1.0.0 (legacy format) to 2.0 (new format).

        Args:
            data: Media plan data in v1.0.0 format.

        Returns:
            Media plan data in 2.0 format.
        """
        logger.debug("Migrating from v1.0.0 to 2.0 (legacy to new format)")
        # Use the same logic as 1.0 to 2.0 since the schema content is the same
        result = self._migrate_10_to_20(data)
        # Ensure final version is 2.0
        result["meta"]["schema_version"] = "2.0"
        return result

    # UTILITY METHODS

    def _find_migration_function(self, from_version: str, to_version: str) -> Optional[Callable]:
        """
        Find the appropriate migration function for the given version pair.

        Tries exact match first, then normalized versions with different format combinations.

        Args:
            from_version: Source version
            to_version: Target version

        Returns:
            Migration function if found, None otherwise
        """
        # Reject v0.0 versions
        if from_version.startswith("0.") or from_version.startswith("v0."):
            return None

        # Try exact match first
        migration_key = (from_version, to_version)
        if migration_key in self.migration_paths:
            return self.migration_paths[migration_key]

        # Try various format combinations with normalization
        try:
            norm_from = normalize_version(from_version)
            norm_to = normalize_version(to_version)

            # Try different format combinations
            format_combinations = [
                (norm_from, norm_to),  # 2-digit to 2-digit
                (f"v{norm_from}.0", f"v{norm_to}.0"),  # 3-digit to 3-digit
                (f"v{norm_from}.0", norm_to),  # 3-digit to 2-digit
                (norm_from, f"v{norm_to}.0"),  # 2-digit to 3-digit
            ]

            for from_fmt, to_fmt in format_combinations:
                if (from_fmt, to_fmt) in self.migration_paths:
                    return self.migration_paths[(from_fmt, to_fmt)]

        except Exception as e:
            logger.debug(f"Could not find migration function for {from_version} -> {to_version}: {e}")

        return None

    def _update_version_in_data(self, data: Dict[str, Any], target_version: str) -> Dict[str, Any]:
        """
        Update the schema version field in media plan data.

        Args:
            data: Media plan data to update
            target_version: Target version to set

        Returns:
            Updated media plan data
        """
        # Create a copy to avoid modifying the original
        import copy
        result = copy.deepcopy(data)

        # Ensure meta section exists
        if "meta" not in result:
            result["meta"] = {}

        # Update the schema version
        result["meta"]["schema_version"] = target_version

        return result

    def get_supported_migration_paths(self) -> Dict[str, List[str]]:
        """
        Get all supported migration paths (excluding v0.0).

        Returns:
            Dictionary mapping source versions to lists of reachable target versions.
        """
        paths = {}

        # Get all unique versions from migration keys (exclude v0.0)
        all_versions = set()
        for from_v, to_v in self.migration_paths.keys():
            if not (from_v.startswith("0.") or from_v.startswith("v0.")):
                all_versions.add(from_v)
            if not (to_v.startswith("0.") or to_v.startswith("v0.")):
                all_versions.add(to_v)

        # For each version, find all reachable versions
        for version in all_versions:
            reachable = []
            for target in all_versions:
                if version != target and self.find_migration_path(version, target):
                    reachable.append(target)

            if reachable:
                paths[version] = sorted(reachable)

        return paths

    def validate_migration_compatibility(self, from_version: str, to_version: str) -> Dict[str, Any]:
        """
        Validate migration compatibility and provide detailed information.

        Args:
            from_version: Source schema version
            to_version: Target schema version

        Returns:
            Dictionary with compatibility information and recommendations
        """
        result = {
            "compatible": False,
            "migration_path": [],
            "warnings": [],
            "errors": [],
            "recommendations": []
        }

        # Check for v0.0 versions first
        if from_version.startswith("0.") or from_version.startswith("v0."):
            result["errors"].append(
                f"Source version {from_version} (v0.0.x) is not supported in SDK v2.0. "
                f"Please use SDK v1.x to migrate v0.0 plans to v1.0 first."
            )
            result["recommendations"].append("Upgrade using SDK v1.x first, then use SDK v2.0")
            return result

        try:
            # Normalize versions for analysis
            norm_from = normalize_version(from_version)
            norm_to = normalize_version(to_version)

            result["normalized_from"] = norm_from
            result["normalized_to"] = norm_to

            # Check if migration path exists
            path = self.find_migration_path(from_version, to_version)
            if path:
                result["compatible"] = True
                result["migration_path"] = path

                # Analyze migration complexity
                if len(path) == 1:
                    result["migration_type"] = "direct"
                else:
                    result["migration_type"] = "multi_step"
                    result["warnings"].append(f"Migration requires {len(path)} steps")

            else:
                result["errors"].append(f"No migration path found from {from_version} to {to_version}")

            # Check version compatibility types using version_utils
            try:
                from_compat = get_compatibility_type(norm_from)
                to_compat = get_compatibility_type(norm_to)

                if from_compat == "unsupported":
                    result["errors"].append(f"Source version {from_version} is not supported")
                elif from_compat == "deprecated":
                    result["warnings"].append(f"Source version {from_version} is deprecated")

                if to_compat == "unsupported":
                    result["errors"].append(f"Target version {to_version} is not supported")
            except Exception as e:
                result["warnings"].append(f"Could not determine version compatibility: {e}")

            # Add recommendations
            if result["compatible"]:
                if len(path) > 1:
                    result["recommendations"].append("Consider testing migration with sample data first")
                if result["warnings"]:
                    result["recommendations"].append("Review warnings before proceeding")
            else:
                result["recommendations"].append("Check if both versions are supported")
                if not path:
                    result["recommendations"].append("Consider migrating through intermediate versions")

        except Exception as e:
            result["errors"].append(f"Migration compatibility check failed: {str(e)}")

        return result