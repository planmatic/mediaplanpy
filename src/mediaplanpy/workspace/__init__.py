"""
Workspace module for mediaplanpy.

This module provides functionality for managing workspace configurations,
which define storage locations and other global settings, as well as
querying functionality across media plans.
"""

from mediaplanpy.exceptions import (
    WorkspaceError,
    WorkspaceNotFoundError,
    WorkspaceValidationError
)

from mediaplanpy.workspace.loader import WorkspaceManager
from mediaplanpy.workspace.validator import validate_workspace, WORKSPACE_SCHEMA

# Import query module to patch methods into WorkspaceManager
import mediaplanpy.workspace.query

__all__ = [
    'WorkspaceManager',
    'WorkspaceError',
    'WorkspaceNotFoundError',
    'WorkspaceValidationError',
    'validate_workspace',
    'WORKSPACE_SCHEMA'
]