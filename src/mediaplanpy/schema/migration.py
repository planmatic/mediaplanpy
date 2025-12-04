"""
Schema migration module for mediaplanpy.

This module provides utilities for migrating media plans
between different schema versions using 2-digit versioning.

SDK v3.0 supports only v2.0 → v3.0 migration.
v0.0 and v1.0 support completely removed.
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
    Migrator for media plan data between schema versions.

    Provides migration paths for supported schema versions using 2-digit format.
    SDK v3.0 supports only v2.0 → v3.0 migration.

    IMPORTANT: v0.0 and v1.0 support completely removed in SDK v3.0.
    Use SDK v2.x to migrate v1.0 plans to v2.0 first, then upgrade to SDK v3.0.
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
        """Register the default migration paths for SDK v3.0."""
        # REMOVED: v0.0 and v1.0 migration paths are no longer supported in SDK v3.0

        # v2.0 → v3.0 migration path (all format combinations)
        self.register_migration("2.0", "3.0", self._migrate_20_to_30)
        self.register_migration("v2.0", "3.0", self._migrate_20_to_30)
        self.register_migration("v2.0", "v3.0", self._migrate_20_to_30)
        self.register_migration("2.0", "v3.0", self._migrate_20_to_30)

        logger.debug("Registered default migration paths for SDK v3.0 (only v2.0 → v3.0 supported)")

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

    # REMOVED METHODS (no longer supported in SDK v3.0):
    # - _migrate_00_to_10() - v0.0 support removed
    # - _migrate_10_to_20() - v1.0 support removed
    # - _migrate_v100_to_20() - v1.0.0 support removed

    # MIGRATION METHODS FOR SDK v3.0

    def _migrate_20_to_30(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Migrate a media plan from schema v2.0 to v3.0.

        Performs the following required transformations:
        1. Update schema version from 2.0 to 3.0
        2. Migrate campaign audience fields to target_audiences array
        3. Migrate campaign location fields to target_locations array
        4. Rename dictionary.custom_dimensions to lineitem_custom_dimensions

        See MIGRATION_V2_TO_V3.md for complete migration logic.

        Args:
            data: Media plan data in v2.0 format

        Returns:
            Media plan data in v3.0 format
        """
        logger.info("Migrating from v2.0 to v3.0")

        # Make a deep copy to avoid modifying original
        import copy
        result = copy.deepcopy(data)

        # STEP 1: Update schema version
        if "meta" not in result:
            result["meta"] = {}
        result["meta"]["schema_version"] = "3.0"
        logger.debug("Updated schema version to 3.0")

        # STEP 2: Migrate campaign audience fields to target_audiences array
        if "campaign" in result:
            self._migrate_audience_fields_v2_to_v3(result["campaign"])

        # STEP 3: Migrate campaign location fields to target_locations array
        if "campaign" in result:
            self._migrate_location_fields_v2_to_v3(result["campaign"])

        # STEP 4: Rename dictionary.custom_dimensions to lineitem_custom_dimensions
        if "dictionary" in result and "custom_dimensions" in result["dictionary"]:
            result["dictionary"]["lineitem_custom_dimensions"] = result["dictionary"].pop("custom_dimensions")
            logger.debug("Renamed dictionary.custom_dimensions to lineitem_custom_dimensions")

        logger.info("Migration from v2.0 to v3.0 complete")
        return result

    def _migrate_audience_fields_v2_to_v3(self, campaign: Dict[str, Any]) -> None:
        """
        Migrate v2.0 audience fields to v3.0 target_audiences array.

        Transformation:
        - audience_name → target_audiences[0].name
        - audience_age_start → target_audiences[0].demo_age_start
        - audience_age_end → target_audiences[0].demo_age_end
        - audience_gender → target_audiences[0].demo_gender
        - audience_interests (array) → target_audiences[0].interest_attributes (string)

        Name generation rules (if audience_name is missing):
        - Use gender + age range (e.g., "Males 35-55")
        - Fallback to "General Audience"

        Args:
            campaign: Campaign dictionary to modify in-place
        """
        # Extract v2.0 audience fields
        audience_name = campaign.pop("audience_name", None)
        audience_age_start = campaign.pop("audience_age_start", None)
        audience_age_end = campaign.pop("audience_age_end", None)
        audience_gender = campaign.pop("audience_gender", None)
        audience_interests = campaign.pop("audience_interests", None)

        # Only create target_audiences if ANY audience field has data
        if not any([audience_name, audience_age_start, audience_age_end, audience_gender, audience_interests]):
            logger.debug("No audience fields found, skipping target_audiences creation")
            return

        # Generate name if not provided
        if audience_name:
            name = audience_name
        else:
            # Generate from available components
            if audience_gender and audience_gender != "Any":
                prefix = f"{audience_gender}s"  # "Males" or "Females"
            else:
                prefix = "Adults"

            if audience_age_start and audience_age_end:
                name = f"{prefix} {audience_age_start}-{audience_age_end}"
            elif audience_age_start:
                name = f"{prefix} {audience_age_start}+"
            elif audience_age_end:
                name = f"{prefix} up to {audience_age_end}"
            else:
                name = prefix if prefix != "Adults" else "General Audience"

        # Create target_audiences array with single audience object
        audience_obj = {"name": name}

        # Add optional demographic fields
        if audience_age_start is not None:
            audience_obj["demo_age_start"] = audience_age_start
        if audience_age_end is not None:
            audience_obj["demo_age_end"] = audience_age_end
        if audience_gender:
            audience_obj["demo_gender"] = audience_gender

        # Convert audience_interests array to comma-separated string
        if audience_interests:
            if isinstance(audience_interests, list):
                audience_obj["interest_attributes"] = ", ".join(audience_interests)
            else:
                audience_obj["interest_attributes"] = str(audience_interests)

        campaign["target_audiences"] = [audience_obj]
        logger.debug(f"Created target_audiences array with name: {name}")

    def _migrate_location_fields_v2_to_v3(self, campaign: Dict[str, Any]) -> None:
        """
        Migrate v2.0 location fields to v3.0 target_locations array.

        Transformation:
        - location_type → target_locations[0].location_type
        - locations (array) → target_locations[0].location_list (array)
        - Generate descriptive name from locations

        Name generation rules:
        - 1 location: use location name
        - 2 locations: "Location1 and Location2"
        - 3 locations: "Location1, Location2, and Location3"
        - 4+ locations: concatenate with commas, truncate at 50 chars

        Args:
            campaign: Campaign dictionary to modify in-place
        """
        # Extract v2.0 location fields
        location_type = campaign.pop("location_type", None)
        locations = campaign.pop("locations", None)

        # Only create target_locations if locations array has data
        if not locations or len(locations) == 0:
            logger.debug("No locations found, skipping target_locations creation")
            return

        # Generate name from locations
        if len(locations) == 1:
            name = locations[0]
        elif len(locations) == 2:
            name = f"{locations[0]} and {locations[1]}"
        elif len(locations) == 3:
            name = f"{locations[0]}, {locations[1]}, and {locations[2]}"
        else:  # 4+ locations
            # Concatenate all with commas, truncate at 50 chars
            full_name = ", ".join(locations)
            if len(full_name) <= 50:
                name = full_name
            else:
                name = full_name[:47] + "..."  # 47 + 3 = 50 chars total

        # Create target_locations array with single location object
        location_obj = {
            "name": name,
            "location_list": locations
        }

        # Add optional location_type field
        if location_type:
            location_obj["location_type"] = location_type

        campaign["target_locations"] = [location_obj]
        logger.debug(f"Created target_locations array with name: {name}")

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