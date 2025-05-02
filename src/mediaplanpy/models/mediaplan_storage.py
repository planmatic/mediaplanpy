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
    write_mediaplan as storage_write_mediaplan
)
from mediaplanpy.workspace import WorkspaceManager

logger = logging.getLogger("mediaplanpy.models.mediaplan_storage")


# Add storage-related methods to MediaPlan class
def save_to_storage(self, workspace_manager: WorkspaceManager, path: str,
                    format_name: Optional[str] = None, **format_options) -> None:
    """
    Save the media plan to a storage location.

    Args:
        workspace_manager: The WorkspaceManager instance.
        path: The path where the media plan should be saved.
        format_name: Optional format name to use. If not specified, inferred from path.
        **format_options: Additional format-specific options.

    Raises:
        StorageError: If the media plan cannot be saved.
    """
    # Check if workspace is loaded
    if not workspace_manager.is_loaded:
        workspace_manager.load()

    # Get resolved workspace config
    workspace_config = workspace_manager.get_resolved_config()

    # Convert model to dictionary
    data = self.to_dict()

    # Write to storage
    storage_write_mediaplan(workspace_config, data, path, format_name, **format_options)

    logger.info(f"Media plan saved to {path}")


def load_from_storage(cls, workspace_manager: WorkspaceManager, path: str,
                      format_name: Optional[str] = None) -> 'MediaPlan':
    """
    Load a media plan from a storage location.

    Args:
        workspace_manager: The WorkspaceManager instance.
        path: The path to the media plan file.
        format_name: Optional format name to use. If not specified, inferred from path.

    Returns:
        A MediaPlan instance.

    Raises:
        StorageError: If the media plan cannot be loaded.
    """
    # Check if workspace is loaded
    if not workspace_manager.is_loaded:
        workspace_manager.load()

    # Get resolved workspace config
    workspace_config = workspace_manager.get_resolved_config()

    # Read from storage
    data = storage_read_mediaplan(workspace_config, path, format_name)

    # Create MediaPlan instance from dictionary
    media_plan = cls.from_dict(data)

    logger.info(f"Media plan loaded from {path}")

    return media_plan


# Patch methods into MediaPlan class
MediaPlan.save_to_storage = save_to_storage
MediaPlan.load_from_storage = classmethod(load_from_storage)