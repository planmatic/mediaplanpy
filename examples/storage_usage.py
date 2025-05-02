"""
Example usage of the enhanced storage functionality.

This script demonstrates how to use the enhanced storage functionality
with automatic file naming based on campaign ID.
"""

import os
import logging
from datetime import date
from decimal import Decimal
from pathlib import Path

from mediaplanpy.models import (
    MediaPlan,
    Campaign,
    Budget,
    TargetAudience,
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

        # Create a media plan to save
        logger.info("Creating a new media plan")

        media_plan = MediaPlan.create_new(
            created_by="example@agency.com",
            campaign_name="Fall 2025 Campaign",
            campaign_objective="Increase brand awareness for new product line",
            campaign_start_date="2025-09-01",
            campaign_end_date="2025-11-30",
            campaign_budget=150000,
            comments="Campaign for the fall product launch",
            # Use a custom campaign ID
            campaign_id="fall_2025_campaign",
            target_audience={
                "age_range": "18-34",
                "location": "United States",
                "interests": ["fall", "fashion", "lifestyle"]
            }
        )

        # Add a line item
        logger.info("Adding a line item")
        media_plan.add_lineitem({
            "id": "li_social_ig_01",
            "channel": "social",
            "platform": "Instagram",
            "publisher": "Meta",
            "start_date": "2025-09-01",
            "end_date": "2025-10-15",
            "budget": 75000,
            "kpi": "CPM",
            "creative_ids": ["cr_001", "cr_002"]
        })

        # Example 1: Save with automatic path generation
        logger.info("Example 1: Saving with automatic path generation")
        saved_path = media_plan.save_to_storage(manager)
        logger.info(f"Media plan automatically saved to: {saved_path}")

        # Example 2: Load with campaign_id
        logger.info("Example 2: Loading with campaign_id")
        loaded_plan = MediaPlan.load_from_storage(
            manager,
            campaign_id="fall_2025_campaign"
        )
        logger.info(f"Loaded media plan with campaign: {loaded_plan.campaign.name}")

        # Example 3: Save with automatic path but specify format
        logger.info("Example 3: Saving with automatic path but specifying format")
        saved_path = media_plan.save_to_storage(
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
            # Use an ID with characters that need sanitization
            campaign_id="special/campaign/2025",
        )

        # Save it and check that the ID is sanitized in the path
        saved_path = complex_plan.save_to_storage(manager)
        logger.info(f"Complex ID media plan saved to: {saved_path}")

        # Example 5: Save to a specific folder
        logger.info("Example 5: Save to a specific folder")
        folder_path = "campaigns/fall_2025/"
        saved_path = media_plan.save_to_storage(
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

        logger.info("Enhanced storage example completed successfully!")

    except StorageError as e:
        logger.error(f"Storage error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")


if __name__ == "__main__":
    main()