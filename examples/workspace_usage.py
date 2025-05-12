"""
Example of workspace usage with schema and storage integration for v1.0.0.

This script demonstrates how to use the workspace functionality to
manage media plans with the v1.0.0 schema.
"""

import os
import json
import logging
from pathlib import Path
from datetime import date
from decimal import Decimal

from mediaplanpy.workspace import WorkspaceManager
from mediaplanpy.models import MediaPlan
from mediaplanpy.exceptions import (
    WorkspaceError,
    SchemaError,
    ValidationError
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mediaplanpy.examples")


def load_existing_workspace():
    """Example function that loads an existing workspace."""
    try:
        # Load a predefined sample workspace
        sample_path = Path(__file__).parent / "fixtures" / "sample_workspace.json"
        workspace = WorkspaceManager(str(sample_path))
        workspace.load()

        logger.info(f"Loaded workspace: {workspace.is_loaded}")

        # Get storage configuration
        storage_config = workspace.get_storage_config()
        logger.info(f"Storage mode: {storage_config.get('mode')}")

        # Get schema settings
        schema_settings = workspace.get_schema_settings()
        logger.info(f"Preferred schema version: {schema_settings.get('preferred_version')}")

        return workspace

    except Exception as e:
        logger.error(f"Error loading workspace: {e}")
        return None


def create_new_workspace(output_dir):
    """Example function that creates a new workspace with v1.0.0 schema settings."""
    try:
        workspace_path = output_dir / "new_workspace.json"

        # Create a new workspace manager
        manager = WorkspaceManager()

        # Create default workspace (now defaults to v1.0.0)
        config = manager.create_default_workspace(str(workspace_path), overwrite=True)

        logger.info(f"Created new workspace: {config['workspace_name']}")
        logger.info(f"Schema version: {config['schema_settings']['preferred_version']}")

        # Load the created workspace
        manager = WorkspaceManager(str(workspace_path))
        manager.load()

        return manager

    except Exception as e:
        logger.error(f"Error creating workspace: {e}")
        return None


def create_v1_media_plan(workspace):
    """Create a v1.0.0 media plan using workspace settings."""
    try:
        # Create a media plan with v1.0.0 schema
        media_plan = MediaPlan.create_new(
            created_by="example@agency.com",
            mediaplan_id="workspace_example_plan",  # v1.0.0 requires this
            media_plan_name="Workspace Example Plan",  # v1.0.0 supports this
            campaign_name="Workspace Campaign",
            campaign_objective="Testing workspace integration",
            campaign_start_date=date(2025, 6, 1),
            campaign_end_date=date(2025, 8, 31),
            campaign_budget=Decimal("100000"),
            # v1.0.0 audience fields
            audience_age_start=25,
            audience_age_end=45,
            audience_gender="Any",
            audience_interests=["technology", "business"],
            # v1.0.0 location fields
            location_type="Country",
            locations=["United States", "Canada"]
        )

        # Add a v1.0.0 compliant line item
        media_plan.add_lineitem({
            "id": "li_workspace_001",
            "name": "Workspace Test Line Item",  # v1.0.0 requires this
            "start_date": date(2025, 6, 1),
            "end_date": date(2025, 7, 31),
            "cost_total": Decimal("50000"),  # v1.0.0 uses cost_total instead of budget
            "channel": "social",
            "vehicle": "LinkedIn",  # v1.0.0 uses vehicle instead of platform
            "partner": "Microsoft",  # v1.0.0 uses partner instead of publisher
            "kpi": "CPM",
            "metric_impressions": 5000000
        })

        logger.info(f"Created media plan with ID: {media_plan.meta.id}")
        logger.info(f"Media plan schema version: {media_plan.meta.schema_version}")

        return media_plan

    except Exception as e:
        logger.error(f"Error creating media plan: {e}")
        return None


def validate_media_plan(workspace, media_plan):
    """Validate a media plan using workspace schema settings."""
    try:
        # Get the preferred schema version from workspace
        schema_settings = workspace.get_schema_settings()
        preferred_version = schema_settings.get("preferred_version")

        logger.info(f"Validating media plan against schema version: {preferred_version}")

        # Validate using workspace schema validator
        errors = workspace.validate_media_plan(media_plan.to_dict())

        if errors:
            logger.error("Validation failed:")
            for error in errors:
                logger.error(f"  - {error}")
            return False
        else:
            logger.info("Validation successful!")
            return True

    except Exception as e:
        logger.error(f"Error validating media plan: {e}")
        return False


def save_and_load_with_workspace(workspace, media_plan, output_dir):
    """Save and load a media plan using workspace storage settings."""
    try:
        # Make sure the storage directory exists
        storage_config = workspace.get_storage_config()
        if storage_config.get("mode") == "local":
            local_config = storage_config.get("local", {})
            base_path = local_config.get("base_path")

            # Override base path for the example
            base_path = output_dir / "workspace_storage"
            os.makedirs(base_path, exist_ok=True)

            # Update the config
            config = workspace.config
            config["storage"]["local"]["base_path"] = str(base_path)

            # Save the updated config
            config_path = output_dir / "updated_workspace.json"
            with open(config_path, "w") as f:
                json.dump(config, f, indent=2)

            # Load the updated workspace
            updated_workspace = WorkspaceManager(str(config_path))
            updated_workspace.load()

            # Save the media plan
            saved_path = media_plan.save_to_storage(updated_workspace)
            logger.info(f"Saved media plan to: {saved_path}")

            # Load the media plan by campaign ID
            loaded_plan = MediaPlan.load(
                updated_workspace,
                campaign_id=media_plan.campaign.id
            )

            logger.info(f"Loaded media plan with ID: {loaded_plan.meta.id}")
            logger.info(f"Loaded media plan with name: {loaded_plan.meta.name}")

            return loaded_plan

    except Exception as e:
        logger.error(f"Error in save/load operations: {e}")
        return None


def demonstrate_migration(workspace, output_dir):
    """Demonstrate migration from v0.0.0 to v1.0.0 using workspace."""
    try:
        # Create a v0.0.0 media plan
        v0_plan = {
            "meta": {
                "schema_version": "v0.0.0",
                "created_by": "legacy@example.com",
                "created_at": "2025-01-01T12:00:00Z"
            },
            "campaign": {
                "id": "legacy_campaign",
                "name": "Legacy Campaign",
                "objective": "awareness",
                "start_date": "2025-01-01",
                "end_date": "2025-06-30",
                "budget": {
                    "total": 75000
                },
                "target_audience": {
                    "age_range": "18-34",
                    "location": "United States"
                }
            },
            "lineitems": [
                {
                    "id": "li_legacy_001",
                    "channel": "social",
                    "platform": "Facebook",
                    "publisher": "Meta",
                    "start_date": "2025-01-01",
                    "end_date": "2025-03-31",
                    "budget": 40000,
                    "kpi": "CPM"
                }
            ]
        }

        # Save v0.0.0 plan to a file for reference
        v0_path = output_dir / "legacy_media_plan.json"
        with open(v0_path, "w") as f:
            json.dump(v0_plan, f, indent=2)

        logger.info(f"Created legacy v0.0.0 media plan and saved to: {v0_path}")

        # Migrate to v1.0.0 using workspace migrator
        migrated_plan = workspace.migrate_media_plan(v0_plan)

        logger.info("Successfully migrated plan from v0.0.0 to v1.0.0")
        logger.info(f"New schema version: {migrated_plan['meta']['schema_version']}")
        logger.info(f"Generated media plan ID: {migrated_plan['meta'].get('id')}")
        logger.info(f"Campaign budget_total: {migrated_plan['campaign']['budget_total']}")

        # Save migrated plan
        migrated_path = output_dir / "migrated_media_plan.json"
        with open(migrated_path, "w") as f:
            json.dump(migrated_plan, f, indent=2)

        logger.info(f"Saved migrated plan to: {migrated_path}")

        # Validate the migrated plan
        validation_result = workspace.validate_media_plan(migrated_plan)
        if not validation_result:
            logger.info("Migrated plan validates successfully against v1.0.0 schema")

        return migrated_plan

    except Exception as e:
        logger.error(f"Error in migration demonstration: {e}")
        return None


def main():
    """Main function for the examples."""
    # Create output directory
    output_dir = Path(__file__).parent / "output" / "workspace_example"
    os.makedirs(output_dir, exist_ok=True)

    # Example 1: Load an existing workspace
    logger.info("Example 1: Loading an existing workspace")
    existing_workspace = load_existing_workspace()

    # Example 2: Create a new workspace
    logger.info("\nExample 2: Creating a new workspace")
    new_workspace = create_new_workspace(output_dir)

    if new_workspace:
        # Example 3: Create a v1.0.0 media plan
        logger.info("\nExample 3: Creating a v1.0.0 media plan")
        media_plan = create_v1_media_plan(new_workspace)

        if media_plan:
            # Example 4: Validate the media plan
            logger.info("\nExample 4: Validating the media plan")
            validate_media_plan(new_workspace, media_plan)

            # Example 5: Save and load with workspace
            logger.info("\nExample 5: Save and load with workspace")
            loaded_plan = save_and_load_with_workspace(new_workspace, media_plan, output_dir)

    # Example 6: Demonstrate migration
    logger.info("\nExample 6: Demonstrate migration from v0.0.0 to v1.0.0")
    if new_workspace:
        migrated_plan = demonstrate_migration(new_workspace, output_dir)

    logger.info("\nWorkspace examples completed successfully!")


if __name__ == "__main__":
    main()