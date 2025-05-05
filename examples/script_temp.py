"""
Integration test script for mediaplanpy with schema v0.0.0 and v1.0.0.
"""

import os
import json
import logging
from pathlib import Path
from datetime import datetime

from mediaplanpy import (
    WorkspaceManager,
    MediaPlan,
    SchemaValidator,
    WorkspaceError,
    ValidationError
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("integration_test")

# Path configurations - UPDATE THESE
WORKSPACE_PATH = r"C:\Users\laure\PycharmProjects\mediaplanpy\examples\fixtures\sample_workspace.json"  # Update this path
MEDIA_PLAN_PATH = r"C:\Temp\example_mediaplan_v0.0.0.json"  # Update this path

def main():
    """Main integration test function."""
    try:
        # Step 1: Open a workspace
        logger.info(f"Opening workspace from: {WORKSPACE_PATH}")
        workspace = WorkspaceManager(WORKSPACE_PATH)
        workspace.load()

        if not workspace.is_loaded:
            logger.error("Failed to load workspace")
            return

        logger.info(f"Workspace loaded: {workspace.config['workspace_name']}")

        # Get storage configuration
        storage_config = workspace.get_storage_config()
        logger.info(f"Storage mode: {storage_config.get('mode', 'unknown')}")

        # Step 2: Validate the media plan file
        logger.info(f"Validating media plan file: {MEDIA_PLAN_PATH}")

        # Create validator
        validator = SchemaValidator()

        # Validate file
        validation_errors = validator.validate_file(MEDIA_PLAN_PATH)
        if validation_errors:
            logger.error("Validation failed:")
            for error in validation_errors:
                logger.error(f"  - {error}")
            return

        logger.info("Media plan validation successful!")

        # Step 3: Convert validated file to v1.0.0 Media Plan
        # First load raw JSON
        with open(MEDIA_PLAN_PATH, 'r') as f:
            v0_data = json.load(f)
        # Then create the v1.0.0 plan directly through migration
        media_plan = MediaPlan.from_v0_mediaplan(v0_data)

        # Display media plan info
        logger.info(f"Campaign name: {media_plan.campaign.name}")
        logger.info(f"Campaign date range: {media_plan.campaign.start_date} to {media_plan.campaign.end_date}")
        logger.info(f"Number of line items: {len(media_plan.lineitems)}")

        # Step 4: Save the v1.0.0 media plan to workspace storage
        logger.info("Saving v1.0.0 media plan to workspace storage")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        v1_filename = f"mediaplan_v1.0.0_{timestamp}.json"
        saved_path = media_plan.save_to_storage(workspace, v1_filename)
        logger.info(f"Saved v1.0.0 media plan to: {saved_path}")

        # Validate migrated plan against v1.0.0 schema
        migrated_errors = media_plan.validate_against_schema()
        if migrated_errors:
            logger.error("Migrated plan validation failed:")
            for error in migrated_errors:
                logger.error(f"  - {error}")
        else:
            logger.info("Migrated plan validation successful!")

        # List stored files
        storage_backend = workspace.get_storage_backend()
        files = storage_backend.list_files("")
        logger.info(f"Files in storage ({len(files)}):")
        for file_path in files:
            file_info = storage_backend.get_file_info(file_path)
            logger.info(f"  - {file_path} ({file_info['size']} bytes)")

        logger.info("Integration test completed successfully!")

    except WorkspaceError as e:
        logger.error(f"Workspace error: {e}")
    except ValidationError as e:
        logger.error(f"Validation error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        import traceback
        logger.error(traceback.format_exc())


if __name__ == "__main__":
    # Create output directory if it doesn't exist
    # os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Run the integration test
    main()