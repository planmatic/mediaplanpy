"""
Media Plan OSC - Python SDK for Media Plans.

A lightweight, open-source Python SDK for interacting with the open data
standard for media plans.
"""

__version__ = '0.1.0'

# Setup package-level logger
import logging

logger = logging.getLogger("mediaplanpy")
logger.setLevel(logging.INFO)

# Import workspace module
from mediaplanpy.workspace import (
    WorkspaceManager,
    WorkspaceError,
    WorkspaceNotFoundError,
    WorkspaceValidationError
)

# Import exceptions
from mediaplanpy.exceptions import (
    MediaPlanError,
    SchemaError,
    ValidationError,
    StorageError,
    FileReadError,
    FileWriteError,
    S3Error,
    DatabaseError
)

# Import the main classes that users will interact with
# These will be implemented in future modules
# from mediaplanpy.models import MediaPlan, Campaign, LineItem
# from mediaplanpy.io import read_mediaplan, write_mediaplan

__all__ = [
    # Workspace
    'WorkspaceManager',
    'WorkspaceError',
    'WorkspaceNotFoundError',
    'WorkspaceValidationError',

    # Exceptions
    'MediaPlanError',
    'SchemaError',
    'ValidationError',
    'StorageError',
    'FileReadError',
    'FileWriteError',
    'S3Error',
    'DatabaseError',

    # Version
    '__version__'
]