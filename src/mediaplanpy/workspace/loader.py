"""
Workspace configuration loader.

This module provides the WorkspaceManager class for loading, validating,
and managing workspace configurations.
"""

import os
import json
import logging
import pathlib
from typing import Dict, Any, Optional, Union, List

from mediaplanpy.exceptions import (
    WorkspaceError,
    WorkspaceNotFoundError,
    WorkspaceValidationError
)
from mediaplanpy.workspace.validator import validate_workspace, WORKSPACE_SCHEMA

# Configure logging
logger = logging.getLogger("mediaplanpy.workspace.loader")


class WorkspaceManager:
    """
    Manages workspace configuration for the mediaplanpy package.

    The workspace configuration defines storage locations, database connections,
    and other global settings for the package.
    """

    # Default workspace file name
    DEFAULT_FILENAME = "workspace.json"

    # Environment variable that can override the default workspace path
    ENV_VAR_NAME = "MEDIAPLANPY_WORKSPACE_PATH"

    def __init__(self, workspace_path: Optional[str] = None):
        """
        Initialize a WorkspaceManager.

        Args:
            workspace_path: Optional explicit path to workspace.json. If not provided,
                            will look in standard locations.
        """
        self.workspace_path = workspace_path
        self.config = None
        self._resolved_config = None

    @property
    def is_loaded(self) -> bool:
        """Return True if a workspace configuration is loaded."""
        return self.config is not None

    def locate_workspace_file(self) -> str:
        """
        Find the workspace.json file by checking several locations in order.

        Returns:
            Path to the workspace.json file.

        Raises:
            WorkspaceNotFoundError: If no workspace.json can be found.
        """
        search_paths = []

        # 1. Explicitly provided path
        if self.workspace_path:
            search_paths.append(pathlib.Path(self.workspace_path))

        # 2. Path from environment variable
        env_path = os.environ.get(self.ENV_VAR_NAME)
        if env_path:
            search_paths.append(pathlib.Path(env_path))

        # 3. Current working directory
        search_paths.append(pathlib.Path.cwd() / self.DEFAULT_FILENAME)

        # 4. User config directories
        if os.name == 'nt':  # Windows
            user_profile = os.environ.get('USERPROFILE')
            if user_profile:
                search_paths.append(pathlib.Path(user_profile) / '.mediaplanpy' / self.DEFAULT_FILENAME)
        else:  # macOS/Linux
            home = os.environ.get('HOME')
            if home:
                search_paths.append(pathlib.Path(home) / '.config' / 'mediaplanpy' / self.DEFAULT_FILENAME)

        # Check each path
        for path in search_paths:
            if path.exists():
                logger.debug(f"Found workspace configuration at {path}")
                return str(path)

        # If we got here, no workspace file was found
        search_paths_str = "\n  - ".join([str(p) for p in search_paths])
        raise WorkspaceNotFoundError(
            f"No workspace.json file found. Searched the following locations:\n  - {search_paths_str}"
        )

    def load(self, workspace_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Load the workspace configuration.

        Args:
            workspace_path: Optional explicit path to workspace.json.
                           Overrides the path provided at initialization.

        Returns:
            The loaded workspace configuration as a dictionary.

        Raises:
            WorkspaceNotFoundError: If no workspace.json can be found.
            WorkspaceError: If the workspace.json cannot be read or parsed.
        """
        if workspace_path:
            self.workspace_path = workspace_path

        try:
            file_path = self.locate_workspace_file()
            with open(file_path, 'r') as f:
                self.config = json.load(f)
                logger.info(f"Loaded workspace '{self.config.get('workspace_name', 'Unnamed')}' from {file_path}")
                return self.config
        except FileNotFoundError:
            raise WorkspaceNotFoundError(f"Workspace file not found at {self.workspace_path}")
        except json.JSONDecodeError as e:
            raise WorkspaceError(f"Failed to parse workspace.json: {e}")
        except Exception as e:
            raise WorkspaceError(f"Error loading workspace: {e}")

    def validate(self) -> bool:
        """
        Validate the loaded workspace configuration against the schema.

        Returns:
            True if the configuration is valid.

        Raises:
            WorkspaceValidationError: If the configuration fails validation.
            WorkspaceError: If no configuration is loaded.
        """
        if not self.is_loaded:
            raise WorkspaceError("No workspace configuration loaded. Call load() first.")

        errors = validate_workspace(self.config)
        if errors:
            raise WorkspaceValidationError("\n".join(errors))

        return True

    def get_resolved_config(self) -> Dict[str, Any]:
        """
        Get the workspace configuration with all variables resolved.

        Returns:
            A copy of the workspace configuration with placeholder variables resolved.

        Raises:
            WorkspaceError: If no configuration is loaded.
        """
        if not self.is_loaded:
            raise WorkspaceError("No workspace configuration loaded. Call load() first.")

        if self._resolved_config is None:
            self._resolved_config = self._resolve_config_variables(self.config)

        return self._resolved_config

    def _resolve_config_variables(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recursively resolve variables in the configuration.

        Args:
            config: The configuration dictionary to resolve.

        Returns:
            A copy of the configuration with variables resolved.
        """
        # Create a deep copy to avoid modifying the original
        import copy
        resolved = copy.deepcopy(config)

        # Recursively process all string values
        def process_dict(d):
            for key, value in d.items():
                if isinstance(value, dict):
                    process_dict(value)
                elif isinstance(value, list):
                    for i, item in enumerate(value):
                        if isinstance(item, dict):
                            process_dict(item)
                        elif isinstance(item, str):
                            value[i] = self._resolve_path_variables(item)
                elif isinstance(value, str):
                    d[key] = self._resolve_path_variables(value)

        process_dict(resolved)
        return resolved

    def _resolve_path_variables(self, path: str) -> str:
        """
        Resolve placeholder variables in paths.

        Supports:
        - ${user_documents}: User's Documents directory
        - ${user_home}: User's home directory
        - References to other config values with ${config.section.key}

        Args:
            path: The path string to resolve.

        Returns:
            The resolved path.
        """
        # Skip if not a string or has no variables
        if not path or not isinstance(path, str) or '${' not in path:
            return path

        # Resolve built-in variables
        if '${user_documents}' in path:
            if os.name == 'nt':  # Windows
                documents = os.path.join(os.environ.get('USERPROFILE', ''), 'Documents')
            elif os.name == 'posix':  # macOS/Linux
                documents = os.path.join(os.environ.get('HOME', ''), 'Documents')
            else:
                documents = ''
            path = path.replace('${user_documents}', documents)

        if '${user_home}' in path:
            home = os.environ.get('HOME') or os.environ.get('USERPROFILE', '')
            path = path.replace('${user_home}', home)

        # TODO: Implement config reference resolution with ${config.section.key}

        return path

    def create_default_workspace(self, path: str, overwrite: bool = False) -> Dict[str, Any]:
        """
        Create a default workspace.json file.

        Args:
            path: Path where the workspace.json should be created.
            overwrite: Whether to overwrite an existing file.

        Returns:
            The created default configuration.

        Raises:
            WorkspaceError: If the file exists and overwrite is False, or if creation fails.
        """
        default_config = {
            "workspace_name": "Default",
            "environment": "development",
            "storage": {
                "mode": "local",
                "local": {
                    "base_path": "${user_documents}/mediaplanpy",
                    "create_if_missing": True
                }
            },
            "database": {
                "enabled": False
            },
            "google_sheets": {
                "enabled": False
            },
            "logging": {
                "level": "INFO"
            }
        }

        file_path = pathlib.Path(path)

        # Check if parent directory exists, create if not
        if not file_path.parent.exists():
            try:
                file_path.parent.mkdir(parents=True)
            except Exception as e:
                raise WorkspaceError(f"Failed to create directory for workspace.json: {e}")

        # Check if file exists
        if file_path.exists() and not overwrite:
            raise WorkspaceError(f"Workspace file already exists at {path}. Use overwrite=True to replace it.")

        try:
            with open(file_path, 'w') as f:
                json.dump(default_config, f, indent=2)

            logger.info(f"Created default workspace configuration at {path}")
            return default_config
        except Exception as e:
            raise WorkspaceError(f"Failed to create workspace.json: {e}")

    def get_storage_config(self) -> Dict[str, Any]:
        """
        Get the resolved storage configuration section.

        Returns:
            The resolved storage configuration.

        Raises:
            WorkspaceError: If no configuration is loaded.
        """
        resolved = self.get_resolved_config()
        return resolved.get('storage', {})

    def get_database_config(self) -> Dict[str, Any]:
        """
        Get the resolved database configuration section.

        Returns:
            The resolved database configuration.

        Raises:
            WorkspaceError: If no configuration is loaded.
        """
        resolved = self.get_resolved_config()
        return resolved.get('database', {})

    def get_excel_config(self) -> Dict[str, Any]:
        """
        Get the resolved Excel configuration section.

        Returns:
            The resolved Excel configuration.

        Raises:
            WorkspaceError: If no configuration is loaded.
        """
        resolved = self.get_resolved_config()
        return resolved.get('excel', {})

    def get_google_sheets_config(self) -> Dict[str, Any]:
        """
        Get the resolved Google Sheets configuration section.

        Returns:
            The resolved Google Sheets configuration.

        Raises:
            WorkspaceError: If no configuration is loaded.
        """
        resolved = self.get_resolved_config()
        return resolved.get('google_sheets', {})