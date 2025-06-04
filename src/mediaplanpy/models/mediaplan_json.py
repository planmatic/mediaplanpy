"""
JSON export and import methods for MediaPlan.

This module provides standardized methods for exporting media plans to JSON format
and importing media plans from JSON files.
"""

import os
import json
import logging
from typing import Optional

from mediaplanpy.exceptions import StorageError, SchemaVersionError
from mediaplanpy.workspace import WorkspaceManager

# Configure logging
logger = logging.getLogger("mediaplanpy.models.mediaplan_json")

# Constants for directory structure
EXPORTS_SUBDIR = "exports"
IMPORTS_SUBDIR = "imports"

def export_to_json(self, workspace_manager=None, file_path=None, file_name=None,
                 overwrite=False, **format_options) -> str:
    """
    Export the media plan to JSON format.

    Args:
        workspace_manager: Optional WorkspaceManager for saving to workspace storage.
                          If provided, this takes precedence over file_path.
        file_path: Optional path where to save the file. Required if workspace_manager
                  is not provided.
        file_name: Optional filename. If None, generates based on media plan ID.
        overwrite: Whether to overwrite existing files.
        **format_options: Additional JSON format options (e.g., indent, ensure_ascii).

    Returns:
        The complete path to the exported file.

    Raises:
        ValueError: If neither workspace_manager nor file_path is provided.
        StorageError: If export fails or file exists and overwrite=False.
        WorkspaceInactiveError: If workspace is inactive (warning only).
    """
    # Validate that at least one storage location is provided
    if workspace_manager is None and file_path is None:
        raise ValueError("Either workspace_manager or file_path must be provided")

    # Check workspace status if workspace_manager is provided
    if workspace_manager is not None:
        workspace_manager.check_workspace_active("JSON export", allow_warnings=True)

    # Generate default filename if not provided
    if file_name is None:
        media_plan_id = self.meta.id
        file_name = f"{media_plan_id}.json"

    # Convert model to dictionary
    data = self.to_dict()

    # Determine storage approach based on parameters
    if workspace_manager is not None:
        # Use workspace storage (takes precedence)
        # Make sure workspace is loaded
        if not workspace_manager.is_loaded:
            workspace_manager.load()

        # Get storage backend
        storage_backend = workspace_manager.get_storage_backend()

        # Create exports directory if it doesn't exist
        try:
            if hasattr(storage_backend, 'create_directory'):
                storage_backend.create_directory(EXPORTS_SUBDIR)
        except Exception as e:
            logger.warning(f"Could not create exports directory: {e}")

        # Full path in workspace storage
        full_path = os.path.join(EXPORTS_SUBDIR, file_name)

        # Check if file exists and handle overwrite flag
        if storage_backend.exists(full_path) and not overwrite:
            raise StorageError(
                f"File {full_path} already exists. Set overwrite=True to replace it."
            )

        # Apply format options
        indent = format_options.get("indent", 2)
        ensure_ascii = format_options.get("ensure_ascii", False)

        try:
            # Serialize to JSON
            json_content = json.dumps(data, indent=indent, ensure_ascii=ensure_ascii)

            # Write to storage
            storage_backend.write_file(full_path, json_content)

            logger.info(f"Media plan exported to JSON in workspace storage: {full_path}")
            return full_path
        except Exception as e:
            raise StorageError(f"Failed to export media plan to JSON: {e}")
    else:
        # Use local file system
        # Ensure directory exists
        if not os.path.exists(file_path):
            try:
                os.makedirs(file_path, exist_ok=True)
            except Exception as e:
                raise StorageError(f"Failed to create directory {file_path}: {e}")

        # Full path in local file system
        full_path = os.path.join(file_path, file_name)

        # Check if file exists and handle overwrite flag
        if os.path.exists(full_path) and not overwrite:
            raise StorageError(
                f"File {full_path} already exists. Set overwrite=True to replace it."
            )

        try:
            # Apply format options
            indent = format_options.get("indent", 2)
            ensure_ascii = format_options.get("ensure_ascii", False)

            # Write to file
            with open(full_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=indent, ensure_ascii=ensure_ascii)

            logger.info(f"Media plan exported to JSON at: {full_path}")
            return full_path
        except Exception as e:
            raise StorageError(f"Failed to export media plan to JSON: {e}")


@classmethod
def import_from_json(cls, file_name, workspace_manager=None, file_path=None,
                     **format_options):
    """
    Import a media plan from a JSON file with version handling.

    Args:
        file_name: Name of the file to import.
        workspace_manager: Optional WorkspaceManager for loading from workspace storage.
                          If provided, this takes precedence over file_path.
        file_path: Optional path to the file. Required if workspace_manager
                  is not provided.
        **format_options: Additional format-specific options.

    Returns:
        A new MediaPlan instance.

    Raises:
        ValueError: If neither workspace_manager nor file_path is provided.
        StorageError: If import fails or file doesn't exist.
        WorkspaceInactiveError: If workspace is inactive.
        SchemaVersionError: If schema version is not supported.
    """
    # Validate that at least one storage location is provided
    if workspace_manager is None and file_path is None:
        raise ValueError("Either workspace_manager or file_path must be provided")

    # Check workspace status if workspace_manager is provided
    if workspace_manager is not None:
        workspace_manager.check_workspace_active("JSON import")

    if workspace_manager is not None:
        # Use workspace storage (takes precedence)
        # Make sure workspace is loaded
        if not workspace_manager.is_loaded:
            workspace_manager.load()

        # Get storage backend
        storage_backend = workspace_manager.get_storage_backend()

        # Check imports directory first
        imports_path = os.path.join(IMPORTS_SUBDIR, file_name)

        # Check if file exists in imports directory
        if storage_backend.exists(imports_path):
            full_path = imports_path
        else:
            # Try root directory as fallback
            if not storage_backend.exists(file_name):
                raise StorageError(f"File not found: neither {imports_path} nor {file_name} exists")

            # Use root path
            full_path = file_name
            logger.warning(f"Found file in root directory instead of imports directory")

        try:
            # Read file content
            content = storage_backend.read_file(full_path, binary=False)

            # Parse JSON
            try:
                data = json.loads(content)
            except json.JSONDecodeError as e:
                raise StorageError(f"Failed to parse JSON file: {e}")

            # Create MediaPlan instance with version handling
            # The from_dict method will handle version compatibility
            result = cls.from_dict(data)

            logger.info(f"Media plan imported from JSON in workspace storage: {full_path}")
            return result

        except SchemaVersionError:
            # Re-raise schema version errors with file context
            raise
        except Exception as e:
            if not isinstance(e, StorageError):
                raise StorageError(f"Failed to import media plan from JSON: {e}")
            raise
    else:
        # Use local file system
        # Full path in local file system
        full_path = os.path.join(file_path, file_name)

        # Check if file exists
        if not os.path.exists(full_path):
            raise StorageError(f"File not found: {full_path}")

        try:
            # Read and parse JSON
            with open(full_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Create MediaPlan instance with version handling
            # The from_dict method will handle version compatibility
            result = cls.from_dict(data)

            logger.info(f"Media plan imported from JSON at: {full_path}")
            return result

        except json.JSONDecodeError as e:
            raise StorageError(f"Failed to parse JSON file: {e}")
        except SchemaVersionError:
            # Re-raise schema version errors with file context
            raise
        except Exception as e:
            raise StorageError(f"Failed to import media plan from JSON: {e}")

# Patch methods into MediaPlan class
def patch_mediaplan_json_methods():
    """
    Add the JSON import/export methods to the MediaPlan class.
    """
    from mediaplanpy.models.mediaplan import MediaPlan

    # Add standardized JSON methods
    MediaPlan.export_to_json = export_to_json
    MediaPlan.import_from_json = classmethod(import_from_json)

    logger.debug("Added standardized JSON methods to MediaPlan class")

# Apply patches when this module is imported
patch_mediaplan_json_methods()