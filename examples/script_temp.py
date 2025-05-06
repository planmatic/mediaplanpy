"""
Integration test script for mediaplanpy with schema v0.0.0 and v1.0.0.
"""

import logging
from mediaplanpy import *

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("integration_test")

def export_mediaplan_to_excel():
    """Main integration test function."""

    # Path configurations - UPDATE THESE
    WORKSPACE_PATH = r"C:\Temp\20250506\sample_workspace.json"  # Update this path
    MEDIA_PLAN_PATH = r"C:\Temp\20250506\example_mediaplan_v1.0.0.json"  # Update this path

    try:
        # Step 1: Open workspace
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

        # Step 3: Export Media Plan to Excel
        media_plan = MediaPlan.load_from_storage(workspace, path="example_mediaplan_v1.0.0.json")
        excel_path = media_plan.export_to_excel(workspace_manager=workspace)
        print(f"Exported to: {excel_path}")

        # Step 4: Open Media Plan from Excel
        media_plan = MediaPlan.from_excel(r"C:\Temp\20250506\mp-001_20250506_162205.xlsx")
        media_plan.save_to_storage(workspace)

    except WorkspaceError as e:
        logger.error(f"Workspace error: {e}")
    except ValidationError as e:
        logger.error(f"Validation error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        import traceback
        logger.error(traceback.format_exc())


if __name__ == "__main__":

    # Run the integration test
    export_mediaplan_to_excel()