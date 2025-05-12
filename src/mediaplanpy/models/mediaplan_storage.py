"""
Integration of MediaPlan models with storage functionality.

This module enhances the MediaPlan model with methods for saving to
and loading from storage backends.
"""

import os
import logging
from typing import Dict, Any, Optional, Union, Type, ClassVar

from mediaplanpy.exceptions import StorageError, FileReadError, FileWriteError
from mediaplanpy.models.mediaplan import MediaPlan
from mediaplanpy.storage import (
    read_mediaplan as storage_read_mediaplan,
    write_mediaplan as storage_write_mediaplan,
    get_format_handler_instance
)
from mediaplanpy.workspace import WorkspaceManager

logger = logging.getLogger("mediaplanpy.models.mediaplan_storage")


# Add storage-related methods to MediaPlan class
def save(self, workspace_manager: WorkspaceManager, path: Optional[str] = None,
                    format_name: Optional[str] = None, **format_options) -> str:
    """
    Save the media plan to a storage location.

    Args:
        workspace_manager: The WorkspaceManager instance.
        path: The path where the media plan should be saved. If None or empty,
              a default path is generated based on the campaign ID.
        format_name: Optional format name to use. If not specified, inferred from path
                    or defaults to "json".
        **format_options: Additional format-specific options.

    Returns:
        The path where the media plan was saved.

    Raises:
        StorageError: If the media plan cannot be saved.
    """
    # Check if workspace is loaded
    if not workspace_manager.is_loaded:
        workspace_manager.load()

    # Get resolved workspace config
    workspace_config = workspace_manager.get_resolved_config()

    # Generate default path if not provided
    if not path:
        # Default format is json if not specified
        default_format = format_name or "json"
        # Get format extension (remove leading dot if present)
        format_handler = get_format_handler_instance(default_format)
        extension = format_handler.get_file_extension()
        if extension.startswith('.'):
            extension = extension[1:]

        # Use campaign ID as filename
        campaign_id = self.campaign.id
        # Sanitize campaign ID for use as a filename
        campaign_id = campaign_id.replace('/', '_').replace('\\', '_')

        # Generate path: campaign_id.extension
        path = f"{campaign_id}.{extension}"

    # Convert model to dictionary
    data = self.to_dict()

    # Write to storage
    storage_write_mediaplan(workspace_config, data, path, format_name, **format_options)

    logger.info(f"Media plan saved to {path}")

    # Return the path where the media plan was saved
    return path


def load(cls, workspace_manager: WorkspaceManager, path: Optional[str] = None,
         campaign_id: Optional[str] = None, format_name: Optional[str] = None) -> 'MediaPlan':
    """
    Load a media plan from a storage location.

    Args:
        workspace_manager: The WorkspaceManager instance.
        path: The path to the media plan file. Required if campaign_id is not provided.
        campaign_id: The campaign ID to load. If provided and path is None, will try to
                    load from a default path based on campaign_id.
        format_name: Optional format name to use. If not specified, inferred from path
                    or defaults to "json".

    Returns:
        A MediaPlan instance.

    Raises:
        StorageError: If the media plan cannot be loaded.
        ValueError: If neither path nor campaign_id is provided.
    """
    # Check if workspace is loaded
    if not workspace_manager.is_loaded:
        workspace_manager.load()

    # Get resolved workspace config
    workspace_config = workspace_manager.get_resolved_config()

    # Generate default path if not provided but campaign_id is
    if not path and campaign_id:
        # Default format is json if not specified
        default_format = format_name or "json"
        # Get format extension
        format_handler = get_format_handler_instance(default_format)
        extension = format_handler.get_file_extension()
        if extension.startswith('.'):
            extension = extension[1:]

        # Sanitize campaign ID for use as a filename
        safe_campaign_id = campaign_id.replace('/', '_').replace('\\', '_')

        # Generate path: campaign_id.extension
        path = f"{safe_campaign_id}.{extension}"

    # Validate we have a path
    if not path:
        raise ValueError("Either path or campaign_id must be provided")

    # Read from storage
    data = storage_read_mediaplan(workspace_config, path, format_name)

    # Create MediaPlan instance from dictionary
    media_plan = cls.from_dict(data)

    logger.info(f"Media plan loaded from {path}")

    return media_plan


# Patch methods into MediaPlan class
MediaPlan.save = classmethod(save)
MediaPlan.load = classmethod(load)