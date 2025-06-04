"""
Schema migration module for mediaplanpy.

This module provides utilities for migrating media plans
between different schema versions with support for 2-digit versioning.
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
        """Register the default migration paths using supported 2-digit format."""
        # Register migration from 0.0 to 1.0 (supported 2-digit format)
        self.register_migration("0.0", "1.0", self._migrate_00_to_10)

        # Register legacy format support for input (but output to supported format)
        # These handle legacy format inputs but migrate to 2-digit format
        self.register_migration("v0.0.0", "1.0", self._migrate_v000_to_10)
        self.register_migration("v1.0.0", "1.0", self._migrate_v100_to_10)

        # Add the legacy migration for backward compatibility
        self.register_migration("v0.0.0", "v1.0.0", self._migrate_v000_to_v100)

        logger.debug("Registered default migration paths for 2-digit versioning")

    def register_migration(self, from_version: str, to_version: str,
                          migration_func: Callable[[Dict[str, Any]], Dict[str, Any]]):
        """
        Register a migration path between two versions.

        Args:
            from_version: Source schema version (supports both old and new formats).
            to_version: Target schema version (supports both old and new formats).
            migration_func: Function that transforms data from source to target version.
        """
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

    def _validate_migration_versions(self, from_version: str, to_version: str):
        """
        Validate that migration versions are in acceptable formats.

        Args:
            from_version: Source version to validate
            to_version: Target version to validate

        Raises:
            SchemaVersionError: If version format is invalid
        """
        for version, version_type in [(from_version, "source"), (to_version, "target")]:
            # Allow both old format (v1.0.0) and new format (1.0)
            is_old_format = version.startswith('v') and version.count('.') >= 2
            is_new_format = not version.startswith('v') and version.count('.') == 1

            if not (is_old_format or is_new_format):
                # Try to normalize to see if it's valid
                try:
                    normalize_version(version)
                except Exception:
                    raise SchemaVersionError(
                        f"Invalid {version_type} version format: {version}. "
                        f"Expected 'X.Y' (new format) or 'vX.Y.Z' (legacy format)"
                    )

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

        # Build a graph of all possible migration paths
        all_versions = set()
        for from_v, to_v in self.migration_paths.keys():
            all_versions.add(from_v)
            all_versions.add(to_v)

        # BFS to find shortest path
        queue = [(from_version, [])]
        visited = {from_version}

        while queue:
            current, path = queue.pop(0)

            # Check all possible next steps
            for (path_from, path_to), _ in self.migration_paths.items():
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
            SchemaVersionError: If a version is not supported.
            SchemaMigrationError: If no migration path exists or migration fails.
        """
        logger.debug(f"Starting migration from {from_version} to {to_version}")

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

    def _validate_migration_versions(self, from_version: str, to_version: str):
        """
        Validate that migration versions are in acceptable formats.

        Args:
            from_version: Source version to validate
            to_version: Target version to validate

        Raises:
            SchemaVersionError: If version format is invalid
        """
        for version, version_type in [(from_version, "source"), (to_version, "target")]:
            # Allow both old format (v1.0.0) and new format (1.0)
            is_old_format = version.startswith('v') and version.count('.') >= 2
            is_new_format = not version.startswith('v') and version.count('.') == 1

            if not (is_old_format or is_new_format):
                # Try to normalize to see if it's valid
                try:
                    normalize_version(version)
                except Exception:
                    raise SchemaVersionError(
                        f"Invalid {version_type} version format: {version}. "
                        f"Expected 'X.Y' (new format) or 'vX.Y.Z' (legacy format)"
                    )

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
        Get all supported migration paths.

        Returns:
            Dictionary mapping source versions to lists of reachable target versions.
        """
        paths = {}

        # Get all unique versions from migration keys
        all_versions = set()
        for from_v, to_v in self.migration_paths.keys():
            all_versions.add(from_v)
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

            # Check version compatibility types
            from_compat = get_compatibility_type(norm_from)
            to_compat = get_compatibility_type(norm_to)

            if from_compat == "unsupported":
                result["errors"].append(f"Source version {from_version} is not supported")
            elif from_compat == "deprecated":
                result["warnings"].append(f"Source version {from_version} is deprecated")

            if to_compat == "unsupported":
                result["errors"].append(f"Target version {to_version} is not supported")

            # Add recommendations
            if result["compatible"]:
                if len(path) > 1:
                    result["recommendations"].append("Consider testing migration with sample data first")
                if from_compat == "deprecated":
                    result["recommendations"].append("Plan to upgrade from deprecated source version")
            else:
                result["recommendations"].append("Check if both versions are supported")
                if not path:
                    result["recommendations"].append("Consider migrating through intermediate versions")

        except Exception as e:
            result["errors"].append(f"Migration compatibility check failed: {str(e)}")

        return result

    # Migration function implementations

    def _migrate_00_to_10(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Migrate a media plan from schema 0.0 to 1.0 (new 2-digit format).

        Args:
            data: Media plan data in 0.0 format.

        Returns:
            Media plan data in 1.0 format.
        """
        logger.debug("Migrating from 0.0 to 1.0")
        result = self._perform_v0_to_v1_migration(data)
        result["meta"]["schema_version"] = "1.0"
        return result

    def _migrate_v000_to_v100(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Legacy migration method kept for compatibility.
        Migrates from v0.0.0 to v1.0.0 but outputs in 1.0 format for registry compatibility.

        Args:
            data: Media plan data in v0.0.0 format.

        Returns:
            Media plan data in 1.0 format (registry-compatible).
        """
        logger.debug("Legacy migration v0.0.0 to v1.0.0 (redirected to 1.0)")
        return self._migrate_v000_to_10(data)

    def _migrate_v000_to_10(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Migrate a media plan from schema v0.0.0 (legacy) to 1.0 (new format).

        Args:
            data: Media plan data in v0.0.0 format.

        Returns:
            Media plan data in 1.0 format.
        """
        logger.debug("Migrating from v0.0.0 to 1.0 (legacy to new format)")
        result = self._perform_v0_to_v1_migration(data)
        result["meta"]["schema_version"] = "1.0"
        return result

    def _migrate_v100_to_10(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Migrate a media plan from schema v1.0.0 (legacy) to 1.0 (new format).
        This is mainly a version format conversion.

        Args:
            data: Media plan data in v1.0.0 format.

        Returns:
            Media plan data in 1.0 format.
        """
        logger.debug("Migrating from v1.0.0 to 1.0 (format conversion)")
        # This is mainly a version format update since both are v1 schema
        import copy
        result = copy.deepcopy(data)
        result["meta"]["schema_version"] = "1.0"
        return result

    def _perform_v0_to_v1_migration(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform the actual migration logic from v0 to v1 schema structure.

        This is the core migration logic that transforms the data structure,
        shared by all v0->v1 migration variants.

        Args:
            data: Media plan data in v0 format.

        Returns:
            Media plan data in v1 format (without version field update).
        """
        # Create a deep copy to avoid modifying the original
        import copy
        result = copy.deepcopy(data)

        # Update metadata
        if "meta" in result:
            meta = result["meta"]
            # Add id if missing
            if "id" not in meta:
                meta["id"] = f"mediaplan_{uuid.uuid4().hex[:8]}"

            # Add name if missing (use campaign name or create default)
            if "name" not in meta:
                campaign_name = result.get("campaign", {}).get("name", "Unnamed Media Plan")
                meta["name"] = campaign_name

        # Update campaign
        if "campaign" in result:
            campaign = result["campaign"]

            # Transform budget structure from v0 to v1
            if "budget" in campaign:
                budget = campaign.pop("budget")
                campaign["budget_total"] = budget.get("total", 0)

                # Preserve by_channel info in a custom field if available
                if "by_channel" in budget:
                    campaign["dim_custom1"] = f"budget_by_channel:{str(budget['by_channel'])}"

            # Transform target audience from v0 to v1
            if "target_audience" in campaign:
                target_audience = campaign.pop("target_audience")

                # Extract age range
                age_range = target_audience.get("age_range")
                if age_range and "-" in age_range:
                    try:
                        start, end = age_range.split("-")
                        campaign["audience_age_start"] = int(start.strip())
                        campaign["audience_age_end"] = int(end.strip())
                    except (ValueError, TypeError):
                        # In case of parsing error, just set a name
                        campaign["audience_name"] = f"Age {age_range}"

                # Extract location
                location = target_audience.get("location")
                if location:
                    campaign["location_type"] = "Country"  # Assume country as default
                    campaign["locations"] = [location]

                # Extract interests
                interests = target_audience.get("interests")
                if interests:
                    campaign["audience_interests"] = interests

        # Update line items
        if "lineitems" in result:
            for i, lineitem in enumerate(result["lineitems"]):
                # Required fields in v1.0
                # Add name if missing
                if "name" not in lineitem:
                    lineitem["name"] = lineitem.get("id", f"Line Item {i+1}")

                # Change budget to cost_total
                if "budget" in lineitem:
                    lineitem["cost_total"] = lineitem.pop("budget")

                # Map platform to vehicle
                if "platform" in lineitem:
                    lineitem["vehicle"] = lineitem.pop("platform")

                # Map publisher to partner
                if "publisher" in lineitem:
                    lineitem["partner"] = lineitem.pop("publisher")

                # Handle creative_ids as a custom dimension
                if "creative_ids" in lineitem and lineitem["creative_ids"]:
                    creative_ids_str = ",".join(lineitem["creative_ids"])
                    lineitem["dim_custom1"] = f"creative_ids:{creative_ids_str}"
                    del lineitem["creative_ids"]

        logger.debug("Completed v0 to v1 migration logic")
        return result

    def get_supported_migration_paths(self) -> Dict[str, List[str]]:
        """
        Get all supported migration paths.

        Returns:
            Dictionary mapping source versions to lists of reachable target versions.
        """
        paths = {}

        # Get all unique versions from migration keys
        all_versions = set()
        for from_v, to_v in self.migration_paths.keys():
            all_versions.add(from_v)
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