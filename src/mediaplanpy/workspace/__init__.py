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

# Import campaign lifecycle module to patch its methods into WorkspaceManager.
# Separate from query.py because query.py is read-only querying and this is
# write/destructive; same patching mechanism.
import mediaplanpy.workspace.campaign_lifecycle

__all__ = [
    'WorkspaceManager',
    'WorkspaceError',
    'WorkspaceNotFoundError',
    'WorkspaceValidationError',
    'validate_workspace',
    'WORKSPACE_SCHEMA'
]