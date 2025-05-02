"""
Example usage of the storage module.

This script demonstrates how to use the storage functionality
to save and load media plans from various storage backends.
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
from mediaplanpy.exceptions import StorageError, FileReadError, FileWriteError
from mediaplanpy.storage import (
    read_mediaplan,
    write_mediaplan,
    get_storage_backend,
    get_format_handler_instance,
    JsonFormatHandler
)

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

        # Create a media plan to save
        logger.info("Creating a new media plan")

        media_plan = MediaPlan.create_new(
            created_by="example@agency.com",
            campaign_name="Summer 2025 Campaign",
            campaign_objective="Increase brand awareness for new product line",
            campaign_start_date="2025-06-01",
            campaign_end_date="2025-08-31",
            campaign_budget=200000,
            comments="Campaign for the summer product launch",
            target_audience={
                "age_range": "18-34",
                "location": "United States",
                "interests": ["summer", "outdoors", "lifestyle"]
            }
        )

        # Add line items
        logger.info("Adding line items")

        # Social media line item
        media_plan.add_lineitem({
            "id": "li_social_fb_01",
            "channel": "social",
            "platform": "Facebook",
            "publisher": "Meta",
            "start_date": "2025-06-01",
            "end_date": "2025-07-15",
            "budget": 80000,
            "kpi": "CPM",
            "creative_ids": ["cr_001", "cr_002"]
        })

        # Display line item
        media_plan.add_lineitem(LineItem(
            id="li_display_gdn_01",
            channel="display",
            platform="Google Display Network",
            publisher="Google",
            start_date=date(2025, 6, 15),
            end_date=date(2025, 8, 15),
            budget=Decimal("120000"),
            kpi="CPC",
            creative_ids=["cr_003", "cr_004", "cr_005"]
        ))

        # Load the workspace
        logger.info("Loading workspace")
        manager = WorkspaceManager(str(workspace_path))
        manager.load()

        # Method 1: Save directly using the media plan's storage method
        logger.info("Method 1: Saving media plan using media_plan.save_to_storage()")

        # Define the path where to save the media plan (relative to the storage base path)
        relative_path = "campaigns/summer_2025/media_plan.json"

        # Save to storage
        media_plan.save_to_storage(manager, relative_path)

        # Method 2: Load directly using the media plan's storage method
        logger.info("Method 2: Loading media plan using MediaPlan.load_from_storage()")

        # Load from storage
        loaded_plan = MediaPlan.load_from_storage(manager, relative_path)

        logger.info(f"Loaded media plan with campaign: {loaded_plan.campaign.name}")
        logger.info(f"Loaded media plan has {len(loaded_plan.lineitems)} line items")

        # Method 3: Using the storage module directly
        logger.info("Method 3: Using the storage module functions directly")

        # Get resolved workspace config
        workspace_config = manager.get_resolved_config()

        # Define a different path for this example
        another_path = "campaigns/summer_2025/media_plan_copy.json"

        # Write directly using the storage module
        write_mediaplan(workspace_config, media_plan.to_dict(), another_path)

        # Read directly using the storage module
        loaded_data = read_mediaplan(workspace_config, another_path)

        logger.info(f"Directly loaded media plan data with campaign: {loaded_data['campaign']['name']}")

        # Method 4: Using the storage backend directly
        logger.info("Method 4: Using the storage backend directly")

        # Get storage backend
        backend = get_storage_backend(workspace_config)

        # Get format handler
        format_handler = get_format_handler_instance("json", indent=4)

        # Define yet another path for this example
        yet_another_path = "campaigns/summer_2025/media_plan_direct.json"

        # Write the file
        serialized_data = format_handler.serialize(media_plan.to_dict())
        backend.write_file(yet_another_path, serialized_data)

        # Read the file
        read_content = backend.read_file(yet_another_path)
        direct_loaded_data = format_handler.deserialize(read_content)

        logger.info(f"Directly loaded media plan data with campaign: {direct_loaded_data['campaign']['name']}")

        # List all saved media plans
        logger.info("Listing all media plans in the campaigns directory")

        all_files = backend.list_files("campaigns", pattern="**/*.json")
        logger.info(f"Found {len(all_files)} media plan files:")
        for file_path in all_files:
            file_info = backend.get_file_info(file_path)
            logger.info(f"  - {file_path} (size: {file_info['size']} bytes, modified: {file_info['modified']})")

        logger.info("Example completed successfully!")

    except StorageError as e:
        logger.error(f"Storage error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")


if __name__ == "__main__":
    main()