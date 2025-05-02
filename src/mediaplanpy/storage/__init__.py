"""
Storage module for mediaplanpy.

This module provides functionality for reading and writing media plans
to various storage backends in different formats.
"""

import logging
from typing import Dict, Any, Optional, Type, Union

from mediaplanpy.exceptions import StorageError
from mediaplanpy.storage.base import StorageBackend
from mediaplanpy.storage.local import LocalStorageBackend
from mediaplanpy.storage.formats import (
    FormatHandler,
    get_format_handler_instance,
    JsonFormatHandler
)

logger = logging.getLogger("mediaplanpy.storage")

# Registry of storage backend classes
_storage_backends = {
    'local': LocalStorageBackend
}


def get_storage_backend(workspace_config: Dict[str, Any]) -> StorageBackend:
    """
    Get a storage backend instance based on workspace configuration.

    Args:
        workspace_config: The resolved workspace configuration dictionary.

    Returns:
        A storage backend instance.

    Raises:
        StorageError: If no storage backend is available for the configured mode.
    """
    storage_config = workspace_config.get('storage', {})
    mode = storage_config.get('mode')

    if not mode:
        raise StorageError("No storage mode specified in workspace configuration")

    if mode not in _storage_backends:
        raise StorageError(f"No storage backend available for mode '{mode}'")

    backend_class = _storage_backends[mode]
    return backend_class(workspace_config)


def read_mediaplan(workspace_config: Dict[str, Any], path: str, format_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Read a media plan from storage.

    Args:
        workspace_config: The resolved workspace configuration dictionary.
        path: The path to the media plan file.
        format_name: Optional format name to use. If not specified, inferred from path.

    Returns:
        The media plan data as a dictionary.

    Raises:
        StorageError: If the media plan cannot be read.
    """
    # Get storage backend
    backend = get_storage_backend(workspace_config)

    # Get format handler
    if format_name:
        format_handler = get_format_handler_instance(format_name)
    else:
        format_handler = get_format_handler_instance(path)

    try:
        # Read file content
        with backend.open_file(path, 'r') as f:
            return format_handler.deserialize_from_file(f)
    except Exception as e:
        raise StorageError(f"Failed to read media plan from {path}: {e}")


def write_mediaplan(workspace_config: Dict[str, Any], data: Dict[str, Any], path: str,
                    format_name: Optional[str] = None, **format_options) -> None:
    """
    Write a media plan to storage.

    Args:
        workspace_config: The resolved workspace configuration dictionary.
        data: The media plan data as a dictionary.
        path: The path where the media plan should be written.
        format_name: Optional format name to use. If not specified, inferred from path.
        **format_options: Additional format-specific options.

    Raises:
        StorageError: If the media plan cannot be written.
    """
    # Get storage backend
    backend = get_storage_backend(workspace_config)

    # Get format handler
    if format_name:
        format_handler = get_format_handler_instance(format_name, **format_options)
    else:
        format_handler = get_format_handler_instance(path, **format_options)

    try:
        # Write file content
        with backend.open_file(path, 'w') as f:
            format_handler.serialize_to_file(data, f)
    except Exception as e:
        raise StorageError(f"Failed to write media plan to {path}: {e}")


__all__ = [
    'StorageBackend',
    'LocalStorageBackend',
    'FormatHandler',
    'JsonFormatHandler',
    'get_storage_backend',
    'get_format_handler_instance',
    'read_mediaplan',
    'write_mediaplan'
]