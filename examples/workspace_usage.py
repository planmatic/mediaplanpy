from mediaplanpy import WorkspaceManager

# Load a workspace
workspace = WorkspaceManager(r"C:\Users\laure\PycharmProjects\mediaplanpy\examples\fixtures\sample_workspace.json")
workspace.load()
print(f"WORKSPACE IS LOADED: {workspace.is_loaded}")

# Get storage configuration
storage_config = workspace.get_storage_config()
print(f"WORKSPACE CONFIG: {str(storage_config)}")

# Use workspace with schema registry / definitions
"""
Example of schema and workspace integration.

This script demonstrates how to use the workspace and schema modules together
to manage media plans.
"""
import os
import json
import logging
from pathlib import Path

from mediaplanpy.workspace import WorkspaceManager
from mediaplanpy.exceptions import (
    WorkspaceError,
    SchemaError,
    ValidationError
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mediaplanpy.examples")


def main():
    """Main function for the example."""
    # Create output directory for our example
    output_dir = Path(__file__).parent / "output"
    os.makedirs(output_dir, exist_ok=True)

    # 1. Create a workspace
    workspace_file = output_dir / "example_workspace.json"
    logger.info(f"Creating workspace at {workspace_file}")

    manager = WorkspaceManager()
    try:
        config = manager.create_default_workspace(str(workspace_file), overwrite=True)
        logger.info(f"Created workspace '{config['workspace_name']}'")

        # Customize schema settings
        config['schema_settings']['preferred_version'] = "v0.0.0"

        # Save changes
        with open(workspace_file, 'w') as f:
            json.dump(config, f, indent=2)

        logger.info(f"Updated schema settings")
    except WorkspaceError as e:
        logger.error(f"Error creating workspace: {e}")
        return

    # 2. Load the workspace
    logger.info(f"Loading workspace from {workspace_file}")
    try:
        manager = WorkspaceManager(str(workspace_file))
        config = manager.load()
        manager.validate()
        logger.info(f"Loaded and validated workspace '{config['workspace_name']}'")
    except (WorkspaceError, SchemaError) as e:
        logger.error(f"Error loading workspace: {e}")
        return

main()