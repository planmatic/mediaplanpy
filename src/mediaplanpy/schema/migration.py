"""
Schema migration module for mediaplanpy.

This module provides utilities for migrating media plans
between different schema versions.
"""

import logging
import uuid
from datetime import datetime
from decimal import Decimal
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
        # Register migration from v0.0.0 to v1.0.0
        self.register_migration("v0.0.0", "v1.0.0", self._migrate_v000_to_v100)

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

    def _migrate_v000_to_v100(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Migrate a media plan from schema v0.0.0 to v1.0.0.

        Args:
            data: Media plan data in v0.0.0 format.

        Returns:
            Media plan data in v1.0.0 format.
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

            # Transform budget structure
            if "budget" in campaign:
                budget = campaign.pop("budget")
                campaign["budget_total"] = budget.get("total", 0)

                # Keep by_channel info in a custom field if needed
                if "by_channel" in budget:
                    campaign["dim_custom1"] = f"budget_by_channel:{str(budget['by_channel'])}"

            # Transform target audience
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
                # Required fields in v1.0.0
                # Add name if missing
                if "name" not in lineitem:
                    lineitem["name"] = lineitem.get("id", f"Line Item {i+1}")

                # Change budget to cost_total
                if "budget" in lineitem:
                    lineitem["cost_total"] = lineitem.pop("budget")

                # Map optional fields
                if "channel" in lineitem:
                    # Keep as is, already aligned
                    pass

                if "platform" in lineitem:
                    lineitem["vehicle"] = lineitem.pop("platform")

                if "publisher" in lineitem:
                    lineitem["partner"] = lineitem.pop("publisher")

                # Handle creative_ids as a custom dimension
                if "creative_ids" in lineitem and lineitem["creative_ids"]:
                    creative_ids_str = ",".join(lineitem["creative_ids"])
                    lineitem["dim_custom1"] = f"creative_ids:{creative_ids_str}"
                    del lineitem["creative_ids"]

        return result