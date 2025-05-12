"""
Example usage of the enhanced storage functionality with v1.0.0 schema support.

This script demonstrates how to use the enhanced storage functionality
with automatic file naming based on campaign ID and the v1.0.0 schema.
"""

import os
import logging
from datetime import date
from decimal import Decimal
from pathlib import Path

from mediaplanpy.models import (
    MediaPlan,
    Campaign,
    LineItem,
    Meta
)
from mediaplanpy.workspace import WorkspaceManager
from mediaplanpy.exceptions import StorageError

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mediaplanpy.examples")


def main():
    """Main function for the example."""
    # Create output directory for our example
    output_dir = Path(__file__).parent / "output"
    os.makedirs(output_dir, exist_ok=True)

    # Path for workspace configuration
    workspace_path = output_dir / "storage_example_workspace.json"

    try:
        # First, create a new workspace configuration
        logger.info("Creating a workspace configuration")

        manager = WorkspaceManager()
        config = manager.create_default_workspace(str(workspace_path), overwrite=True)

        # Update the storage configuration to use the output directory
        config['storage']['local']['base_path'] = str(output_dir / "storage")

        # Save the updated configuration
        with open(workspace_path, 'w') as f:
            import json
            json.dump(config, f, indent=2)

        # Load the workspace
        logger.info("Loading workspace")
        manager = WorkspaceManager(str(workspace_path))
        manager.load()

        # Create a media plan to save with v1.0.0 schema
        logger.info("Creating a new media plan with v1.0.0 schema")

        media_plan = MediaPlan.create_new(
            created_by="example@agency.com",
            campaign_name="Fall 2025 Campaign",
            campaign_objective="Increase brand awareness for new product line",
            campaign_start_date="2025-09-01",
            campaign_end_date="2025-11-30",
            campaign_budget=150000,
            comments="Campaign for the fall product launch",
            # v1.0.0 specific fields
            mediaplan_id="mediaplan_fall_2025",
            media_plan_name="Fall 2025 Media Plan",
            # v1.0.0 audience fields
            audience_age_start=18,
            audience_age_end=34,
            audience_gender="Any",
            audience_interests=["fall", "fashion", "lifestyle"],
            # v1.0.0 location fields
            location_type="Country",
            locations=["United States"],
            # Use a custom campaign ID
            campaign_id="fall_2025_campaign"
        )

        # Add line items with v1.0.0 structure
        logger.info("Adding line items with v1.0.0 structure")

        # Social media line item
        media_plan.add_lineitem({
            "id": "li_social_ig_01",
            "name": "Instagram Fall Campaign",  # Required in v1.0.0
            "start_date": "2025-09-01",
            "end_date": "2025-10-15",
            "cost_total": 75000,  # v1.0.0 uses cost_total instead of budget
            "channel": "social",
            "vehicle": "Instagram",  # v1.0.0 uses vehicle instead of platform
            "partner": "Meta",       # v1.0.0 uses partner instead of publisher
            "kpi": "CPM",
            "metric_impressions": 15000000,
            "metric_clicks": 250000
        })

        # Display line item
        media_plan.add_lineitem({
            "id": "li_display_01",
            "name": "Display Ad Campaign",  # Required in v1.0.0
            "start_date": "2025-10-01",
            "end_date": "2025-11-15",
            "cost_total": 50000,  # v1.0.0 uses cost_total instead of budget
            "channel": "display",
            "vehicle": "Google Display Network",
            "partner": "Google",
            "kpi": "CPC",
            "metric_impressions": 10000000,
            "metric_clicks": 200000
        })

        # Video line item
        media_plan.add_lineitem({
            "id": "li_video_01",
            "name": "YouTube Fall Campaign",  # Required in v1.0.0
            "start_date": "2025-10-15",
            "end_date": "2025-11-30",
            "cost_total": 25000,  # v1.0.0 uses cost_total instead of budget
            "channel": "video",
            "vehicle": "YouTube",
            "partner": "Google",
            "kpi": "CPV",
            "metric_impressions": 5000000,
            "metric_views": 1000000
        })

        # Example 1: Save with automatic path generation
        logger.info("Example 1: Saving with automatic path generation")
        saved_path = media_plan.save(manager)
        logger.info(f"Media plan automatically saved to: {saved_path}")
        logger.info(f"The saved path is based on the campaign_id: {media_plan.campaign.id}")

        # Example 2: Load with campaign_id
        logger.info("Example 2: Loading with campaign_id")
        loaded_plan = MediaPlan.load(
            manager,
            campaign_id="fall_2025_campaign"
        )
        logger.info(f"Loaded media plan with ID: {loaded_plan.meta.id}")
        logger.info(f"Loaded plan name: {loaded_plan.meta.name}")
        logger.info(f"Loaded campaign: {loaded_plan.campaign.name}")
        logger.info(f"Number of line items: {len(loaded_plan.lineitems)}")

        # Example 3: Save with automatic path but specify format
        logger.info("Example 3: Saving with automatic path but specifying format")
        saved_path = media_plan.save(
            manager,
            format_name="json",
            indent=4  # Custom JSON formatting option
        )
        logger.info(f"Media plan automatically saved to: {saved_path}")

        # Example 4: Create another media plan with a complex ID
        logger.info("Example 4: Create a media plan with a complex ID")
        complex_plan = MediaPlan.create_new(
            created_by="example@agency.com",
            campaign_name="Special Campaign",
            campaign_objective="Testing complex IDs",
            campaign_start_date="2025-10-01",
            campaign_end_date="2025-10-31",
            campaign_budget=50000,
            # v1.0.0 specific fields
            mediaplan_id="mediaplan_special_2025",
            media_plan_name="Special Campaign 2025",
            # Use an ID with characters that need sanitization
            campaign_id="special/campaign/2025",
            # Add a line item to make it complete
            lineitems=[
                {
                    "id": "li_special_01",
                    "name": "Special Line Item",
                    "start_date": "2025-10-01",
                    "end_date": "2025-10-31",
                    "cost_total": 50000,
                    "channel": "social"
                }
            ]
        )

        # Save it and check that the ID is sanitized in the path
        saved_path = complex_plan.save_to_workspace(manager)
        logger.info(f"Complex ID media plan saved to: {saved_path}")
        logger.info(f"Notice how special/campaign/2025 was sanitized to 'special_campaign_2025'")

        # Example 5: Save to a specific folder
        logger.info("Example 5: Save to a specific folder")
        folder_path = "campaigns/fall_2025/"
        saved_path = media_plan.save(
            manager,
            path=f"{folder_path}{media_plan.campaign.id}.json"
        )
        logger.info(f"Media plan saved to specific folder: {saved_path}")

        # Example 6: List all saved files
        logger.info("Example 6: List all saved files")
        storage_backend = manager.get_storage_backend()
        all_files = storage_backend.list_files("")
        logger.info(f"All saved files ({len(all_files)}):")
        for file_path in all_files:
            file_info = storage_backend.get_file_info(file_path)
            logger.info(f"  - {file_path} (size: {file_info['size']} bytes)")

        # Example 7: Migrate a v0.0.0 plan and save it
        logger.info("Example 7: Migrate a v0.0.0 plan to v1.0.0 and save it")

        # Create a v0.0.0 media plan
        v0_media_plan = {
            "meta": {
                "schema_version": "v0.0.0",
                "created_by": "example@agency.com",
                "created_at": "2025-05-01T12:00:00Z",
                "comments": "Legacy media plan"
            },
            "campaign": {
                "id": "legacy_campaign",
                "name": "Legacy Campaign",
                "objective": "awareness",
                "start_date": "2025-05-01",
                "end_date": "2025-07-31",
                "budget": {
                    "total": 100000,
                    "by_channel": {
                        "social": 60000,
                        "display": 40000
                    }
                },
                "target_audience": {
                    "age_range": "25-45",
                    "location": "United States",
                    "interests": ["technology", "business"]
                }
            },
            "lineitems": [
                {
                    "id": "legacy_li_001",
                    "channel": "social",
                    "platform": "LinkedIn",
                    "publisher": "Microsoft",
                    "start_date": "2025-05-01",
                    "end_date": "2025-06-30",
                    "budget": 60000,
                    "kpi": "CPM"
                },
                {
                    "id": "legacy_li_002",
                    "channel": "display",
                    "platform": "Google Display",
                    "publisher": "Google",
                    "start_date": "2025-06-01",
                    "end_date": "2025-07-31",
                    "budget": 40000,
                    "kpi": "CPC"
                }
            ]
        }

        # Create a MediaPlan object from the v0.0.0 data
        migrated_plan = MediaPlan.from_v0_mediaplan(v0_media_plan)

        # Save the migrated plan
        migrated_path = migrated_plan.save_to_workspace(manager)
        logger.info(f"Migrated media plan saved to: {migrated_path}")
        logger.info(f"Migrated plan ID: {migrated_plan.meta.id}")
        logger.info(f"Migrated plan schema version: {migrated_plan.meta.schema_version}")
        logger.info(f"First line item cost_total: ${migrated_plan.lineitems[0].cost_total:,.2f}")

        # Example 8: Load a media plan by mediaplan_id
        logger.info("Example 8: Load a media plan by mediaplan_id")

        # First, find the file that contains our mediaplan_id
        target_id = migrated_plan.meta.id
        found_file = None

        for file_path in all_files:
            # Read each file and check if it contains our media plan ID
            try:
                with storage_backend.open_file(file_path, 'r') as f:
                    file_content = json.load(f)
                    if file_content.get("meta", {}).get("id") == target_id:
                        found_file = file_path
                        break
            except:
                # Skip files that can't be parsed as JSON
                continue

        if found_file:
            logger.info(f"Found media plan with ID '{target_id}' in file: {found_file}")

            # Load it directly from the file path
            found_plan = MediaPlan.load(manager, path=found_file)
            logger.info(f"Successfully loaded media plan: {found_plan.meta.name or found_plan.campaign.name}")
        else:
            logger.info(f"Could not find a media plan with ID: {target_id}")

        logger.info("Enhanced storage example completed successfully!")

    except StorageError as e:
        logger.error(f"Storage error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")


if __name__ == "__main__":
    main()