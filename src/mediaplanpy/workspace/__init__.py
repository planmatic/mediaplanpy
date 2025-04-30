"""
Workspace module for mediaplanpy.

This module provides functionality for managing workspace configurations,
which define storage locations and other global settings.
"""

from mediaplanpy.exceptions import (
    WorkspaceError,
    WorkspaceNotFoundError,
    WorkspaceValidationError
)

from mediaplanpy.workspace.loader import WorkspaceManager
from mediaplanpy.workspace.validator import validate_workspace, WORKSPACE_SCHEMA

__all__ = [
    'WorkspaceManager',
    'WorkspaceError',
    'WorkspaceNotFoundError',
    'WorkspaceValidationError',
    'validate_workspace',
    'WORKSPACE_SCHEMA'
]