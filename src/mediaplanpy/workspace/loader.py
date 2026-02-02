"""
Updated workspace configuration loader with automatic migration of deprecated fields.

This module provides the WorkspaceManager class for loading, validating,
and managing workspace configurations with automatic handling of legacy settings.
"""

import os
import json
import logging
import pathlib
import uuid
from typing import Dict, Any, Optional, Union, List, Tuple
import glob
from datetime import datetime

from mediaplanpy.exceptions import (
    WorkspaceError,
    WorkspaceNotFoundError,
    WorkspaceValidationError
)
from mediaplanpy.workspace.validator import validate_workspace, WORKSPACE_SCHEMA
from mediaplanpy.schema import SchemaRegistry, SchemaValidator, SchemaMigrator

# Configure logging
logger = logging.getLogger("mediaplanpy.workspace.loader")


class WorkspaceInactiveError(WorkspaceError):
    """Exception raised when trying to perform restricted operations on an inactive workspace."""
    pass


class FeatureDisabledError(WorkspaceError):
    """Exception raised when trying to use a disabled feature."""
    pass


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

        # Schema components (initialized when needed)
        self._schema_registry = None
        self._schema_validator = None
        self._schema_migrator = None

    def _migrate_deprecated_fields(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Automatically migrate deprecated fields to new format.

        This method handles the migration from old schema_settings fields to
        new workspace_settings format as described in the versioning strategy.

        Args:
            config: The workspace configuration to migrate.

        Returns:
            Migrated configuration with deprecated fields handled.
        """
        # Create a copy to avoid modifying the original
        import copy
        migrated_config = copy.deepcopy(config)

        # Track if any migration was performed
        migration_performed = False

        # Handle deprecated schema_settings fields
        schema_settings = migrated_config.get('schema_settings', {})

        # Remove deprecated fields if they exist
        deprecated_fields = ['preferred_version', 'auto_migrate']
        for field in deprecated_fields:
            if field in schema_settings:
                removed_value = schema_settings.pop(field)
                migration_performed = True
                logger.info(f"Migrated deprecated field 'schema_settings.{field}' (was: {removed_value})")

        # Ensure workspace_settings exists with proper defaults
        if 'workspace_settings' not in migrated_config:
            migrated_config['workspace_settings'] = {}
            migration_performed = True
            logger.info("Added workspace_settings section")

        workspace_settings = migrated_config['workspace_settings']

        # Set default values for workspace_settings if not present - UPDATED FOR v2.0
        from mediaplanpy import __schema_version__
        current_schema_version = __schema_version__  # This will be "2.0"

        defaults = {
            'schema_version': current_schema_version,  # Now defaults to "2.0"
            'last_upgraded': datetime.now().strftime("%Y-%m-%d"),
            'sdk_version_required': f"{current_schema_version.split('.')[0]}.0.x"  # Now "2.0.x"
        }

        for key, default_value in defaults.items():
            if key not in workspace_settings:
                workspace_settings[key] = default_value
                migration_performed = True
                logger.info(f"Set workspace_settings.{key} to default value: {default_value}")

        # Clean up schema_settings if it's now empty
        if not schema_settings:
            migrated_config.pop('schema_settings', None)
            migration_performed = True
            logger.info("Removed empty schema_settings section")

        if migration_performed:
            logger.info("Workspace configuration automatically migrated to new format")

        return migrated_config

    def _validate_workspace_version_compatibility(self) -> None:
        """
        Validate that the workspace schema version is compatible with the current SDK version.

        This enforces strict version matching: SDK v3.0.x can ONLY load v3.0 workspaces.
        Users must explicitly upgrade v2.0 workspaces or downgrade their SDK.

        Raises:
            WorkspaceError: If workspace version is incompatible with SDK version.
        """
        from mediaplanpy import __schema_version__
        sdk_version = __schema_version__  # e.g., "3.0"

        # Get workspace schema version from config
        workspace_version = self.config.get('workspace_settings', {}).get('schema_version')

        if not workspace_version:
            raise WorkspaceError(
                "Workspace configuration is missing 'workspace_settings.schema_version'. "
                "This workspace may be corrupted or from a very old SDK version."
            )

        # Extract major.minor version (ignore patch if present)
        sdk_major_minor = '.'.join(sdk_version.split('.')[:2])  # "3.0"
        workspace_major_minor = '.'.join(workspace_version.split('.')[:2])  # "2.0" or "3.0"

        # Check for version mismatch
        if workspace_major_minor != sdk_major_minor:
            # Workspace is older than SDK
            if workspace_major_minor < sdk_major_minor:
                raise WorkspaceError(
                    f"❌ WORKSPACE VERSION MISMATCH\n\n"
                    f"Workspace version: {workspace_version}\n"
                    f"SDK version: {sdk_version}\n\n"
                    f"This workspace uses schema v{workspace_version}, but you are running SDK v{sdk_version}.\n"
                    f"SDK v{sdk_major_minor}.x can ONLY load v{sdk_major_minor} workspaces.\n\n"
                    f"To resolve this issue, choose ONE of the following options:\n\n"
                    f"OPTION 1 - Upgrade workspace to v{sdk_major_minor} (RECOMMENDED):\n"
                    f"  1. Create a backup of your workspace files\n"
                    f"  2. Run: workspace_manager.upgrade_workspace(dry_run=True)  # Preview changes\n"
                    f"  3. Run: workspace_manager.upgrade_workspace()  # Perform upgrade\n"
                    f"  Note: Upgrade will create automatic backups before making changes\n\n"
                    f"OPTION 2 - Downgrade SDK to v{workspace_major_minor}.x:\n"
                    f"  pip install mediaplanpy~={workspace_major_minor}.0\n\n"
                    f"For more information, see the migration guide in the documentation."
                )

            # Workspace is newer than SDK
            else:
                raise WorkspaceError(
                    f"❌ WORKSPACE VERSION MISMATCH\n\n"
                    f"Workspace version: {workspace_version}\n"
                    f"SDK version: {sdk_version}\n\n"
                    f"This workspace uses schema v{workspace_version}, which is NEWER than your SDK v{sdk_version}.\n"
                    f"You must upgrade your SDK to work with this workspace.\n\n"
                    f"To resolve this issue:\n\n"
                    f"  pip install --upgrade mediaplanpy~={workspace_major_minor}.0\n\n"
                    f"Alternatively, if you need to stay on SDK v{sdk_major_minor}.x, create a new workspace:\n"
                    f"  workspace_manager.create(workspace_name='My v{sdk_major_minor} Workspace')"
                )

        # Versions match - allow load
        logger.debug(f"Workspace version v{workspace_version} is compatible with SDK v{sdk_version}")

    @property
    def is_loaded(self) -> bool:
        """Return True if a workspace configuration is loaded."""
        return self.config is not None

    @property
    def schema_registry(self) -> SchemaRegistry:
        """
        Get the schema registry for this workspace.

        Returns:
            A SchemaRegistry instance.

        Raises:
            WorkspaceError: If no configuration is loaded.
        """
        if not self.is_loaded:
            raise WorkspaceError("No workspace configuration loaded. Call load() first.")

        if self._schema_registry is None:
            # Initialize schema registry (no parameters needed for bundled schemas)
            self._schema_registry = SchemaRegistry()

        return self._schema_registry

    @property
    def schema_validator(self) -> SchemaValidator:
        """
        Get the schema validator for this workspace.

        Returns:
            A SchemaValidator instance.

        Raises:
            WorkspaceError: If no configuration is loaded.
        """
        if self._schema_validator is None:
            self._schema_validator = SchemaValidator(registry=self.schema_registry)
        return self._schema_validator

    @property
    def schema_migrator(self) -> SchemaMigrator:
        """
        Get the schema migrator for this workspace.

        Returns:
            A SchemaMigrator instance.

        Raises:
            WorkspaceError: If no configuration is loaded.
        """
        if self._schema_migrator is None:
            self._schema_migrator = SchemaMigrator(registry=self.schema_registry)
        return self._schema_migrator

    def check_workspace_active(self, operation: str, allow_warnings: bool = False) -> None:
        """
        Check if the workspace is active for the given operation.

        Args:
            operation: Name of the operation being attempted.
            allow_warnings: If True, show warning for inactive workspace instead of error.

        Raises:
            WorkspaceError: If no configuration is loaded.
            WorkspaceInactiveError: If workspace is inactive and allow_warnings is False.
        """
        if not self.is_loaded:
            raise WorkspaceError("No workspace configuration loaded. Call load() first.")

        workspace_status = self.config.get('workspace_status', 'active')

        if workspace_status == 'inactive':
            message = f"Workspace '{self.config.get('workspace_name', 'Unknown')}' is inactive. Cannot perform operation: {operation}"

            if allow_warnings:
                logger.warning(message)
            else:
                raise WorkspaceInactiveError(message)

    def check_excel_enabled(self, operation: str) -> None:
        """
        Check if Excel functionality is enabled for the given operation.

        Args:
            operation: Name of the Excel operation being attempted.

        Raises:
            WorkspaceError: If no configuration is loaded.
            FeatureDisabledError: If Excel functionality is disabled.
        """
        if not self.is_loaded:
            raise WorkspaceError("No workspace configuration loaded. Call load() first.")

        excel_config = self.config.get('excel', {})
        excel_enabled = excel_config.get('enabled', True)  # Default to True for backward compatibility

        if not excel_enabled:
            raise FeatureDisabledError(
                f"Excel functionality is disabled in workspace '{self.config.get('workspace_name', 'Unknown')}'. "
                f"Cannot perform operation: {operation}"
            )

    def _get_default_workspace_directory(self) -> str:
        """
        Get the default directory for workspace files.

        Returns:
            The platform-specific default directory path.
        """
        if os.name == 'nt':  # Windows
            return os.path.join("C:", os.sep, "mediaplanpy")
        else:  # macOS/Linux
            home = os.environ.get('HOME')
            if home:
                return os.path.join(home, "mediaplanpy")
            else:
                return os.path.join(os.getcwd(), "mediaplanpy")

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

    def create(self, settings_path_name: Optional[str] = None,
               settings_file_name: Optional[str] = None,
               storage_path_name: Optional[str] = None,
               workspace_name: str = "Default",
               overwrite: bool = False,
               **kwargs) -> Tuple[str, str]:
        """
        Create a new workspace configuration.

        Args:
            settings_path_name: Folder where settings file is saved. Default is C:/mediaplanpy
            settings_file_name: Filename for settings. Default is {workspace_id}_settings.json
            storage_path_name: Folder for local storage. Default is C:/mediaplanpy/{workspace_id}
            workspace_name: Name of the workspace
            overwrite: Whether to overwrite an existing file
            **kwargs: Additional configuration options

        Returns:
            tuple: (workspace_id, settings_file_path)

        Raises:
            WorkspaceError: If creation fails
        """
        # Generate a unique workspace ID
        workspace_id = f"workspace_{uuid.uuid4().hex[:8]}"

        # Set default paths
        default_dir = self._get_default_workspace_directory()
        if settings_path_name is None:
            settings_path_name = default_dir

        if settings_file_name is None:
            settings_file_name = f"{workspace_id}_settings.json"

        if storage_path_name is None:
            storage_path_name = os.path.join(default_dir, workspace_id)

        # Create the settings file path
        settings_file_path = os.path.join(settings_path_name, settings_file_name)

        # Check if file exists
        if os.path.exists(settings_file_path) and not overwrite:
            raise WorkspaceError(
                f"Workspace file already exists at {settings_file_path}. Use overwrite=True to replace it.")

        # Load workspace template from JSON file
        from mediaplanpy import __schema_version__
        current_schema_version = __schema_version__

        # Get path to template file
        template_path = os.path.join(
            os.path.dirname(__file__),
            'schemas',
            'workspace.template.json'
        )

        try:
            with open(template_path, 'r') as f:
                template_content = f.read()
        except Exception as e:
            raise WorkspaceError(f"Failed to load workspace template: {e}")

        # Replace placeholders in template
        # Convert Windows backslashes to forward slashes for JSON compatibility
        storage_path_json_safe = storage_path_name.replace('\\', '/')

        template_content = template_content.replace('{{WORKSPACE_ID}}', workspace_id)
        template_content = template_content.replace('{{WORKSPACE_NAME}}', workspace_name)
        template_content = template_content.replace('{{STORAGE_PATH}}', storage_path_json_safe)
        template_content = template_content.replace('{{SCHEMA_VERSION}}', current_schema_version)
        template_content = template_content.replace('{{LAST_UPGRADED}}', datetime.now().strftime("%Y-%m-%d"))
        template_content = template_content.replace('{{SDK_VERSION_REQUIRED}}', f"{current_schema_version.split('.')[0]}.0.x")

        # Parse the template into config dict
        try:
            config = json.loads(template_content)
        except Exception as e:
            raise WorkspaceError(f"Failed to parse workspace template: {e}")

        # Override with any provided config options
        for key, value in kwargs.items():
            if key in config:
                if isinstance(config[key], dict) and isinstance(value, dict):
                    config[key].update(value)
                else:
                    config[key] = value

        # Create settings directory if it doesn't exist
        try:
            os.makedirs(settings_path_name, exist_ok=True)
        except Exception as e:
            raise WorkspaceError(f"Failed to create settings directory: {e}")

        # Write the configuration to file
        try:
            with open(settings_file_path, 'w') as f:
                json.dump(config, f, indent=2)

            logger.info(f"Created workspace '{workspace_name}' with ID '{workspace_id}' at {settings_file_path}")

            # Set the workspace path and config
            self.workspace_path = settings_file_path
            self.config = config
            self._resolved_config = None  # Reset resolved config

            return workspace_id, settings_file_path
        except Exception as e:
            raise WorkspaceError(f"Failed to create workspace: {e}")

    def load(self, workspace_path: Optional[str] = None,
             workspace_id: Optional[str] = None,
             config_dict: Optional[Dict[str, Any]] = None,
             upgrade_mode: bool = False) -> Dict[str, Any]:
        """
        Load a workspace configuration with automatic migration of deprecated fields.

        Args:
            workspace_path: Path to workspace settings file
            workspace_id: Workspace ID to locate settings file
            config_dict: Configuration dictionary to use directly
            upgrade_mode: If True, skip version compatibility check to allow loading
                         workspaces with older schema versions for upgrade purposes

        Returns:
            The loaded workspace configuration

        Raises:
            WorkspaceNotFoundError: If workspace cannot be found
            WorkspaceValidationError: If configuration is invalid
            WorkspaceError: If loading fails
        """
        # Reset resolved config
        self._resolved_config = None

        # Use config_dict if provided
        if config_dict is not None:
            # Migrate deprecated fields before validation
            migrated_config = self._migrate_deprecated_fields(config_dict)

            # Validate the migrated configuration
            errors = validate_workspace(migrated_config, lenient_mode=True)
            if errors:
                raise WorkspaceValidationError("\n".join(errors))

            self.config = migrated_config
            self.workspace_path = None  # No file path
            logger.info(f"Loaded workspace '{self.config.get('workspace_name', 'Unnamed')}' from provided dictionary")

            # Check workspace status and show warning if inactive
            try:
                self.check_workspace_active("load", allow_warnings=True)
            except WorkspaceInactiveError:
                pass  # This won't be raised when allow_warnings=True

            return self.config

        # If workspace_id is provided, locate the settings file
        if workspace_id is not None:
            default_dir = self._get_default_workspace_directory()

            # Check default directory first
            settings_paths = [
                os.path.join(default_dir, f"{workspace_id}_settings.json"),
                os.path.join(default_dir, f"{workspace_id}.json")
            ]

            # Check current directory
            settings_paths.extend([
                os.path.join(os.getcwd(), f"{workspace_id}_settings.json"),
                os.path.join(os.getcwd(), f"{workspace_id}.json")
            ])

            # Check user directories
            if os.name == 'nt':  # Windows
                user_profile = os.environ.get('USERPROFILE')
                if user_profile:
                    settings_paths.extend([
                        os.path.join(user_profile, '.mediaplanpy', f"{workspace_id}_settings.json"),
                        os.path.join(user_profile, '.mediaplanpy', f"{workspace_id}.json")
                    ])
            else:  # macOS/Linux
                home = os.environ.get('HOME')
                if home:
                    settings_paths.extend([
                        os.path.join(home, '.config', 'mediaplanpy', f"{workspace_id}_settings.json"),
                        os.path.join(home, '.config', 'mediaplanpy', f"{workspace_id}.json")
                    ])

            # Check each path
            workspace_path_found = None
            for path in settings_paths:
                if os.path.exists(path):
                    workspace_path_found = path
                    break

            if workspace_path_found is None:
                search_paths_str = "\n  - ".join(settings_paths)
                raise WorkspaceNotFoundError(
                    f"No settings file found for workspace ID '{workspace_id}'. "
                    f"Searched in these locations:\n  - {search_paths_str}"
                )

            # Use the found path
            workspace_path = workspace_path_found

        # If workspace_path provided or found by ID, use it
        if workspace_path:
            self.workspace_path = workspace_path
        else:
            # Fall back to existing logic to locate workspace file
            self.workspace_path = self.locate_workspace_file()

        # Load the configuration from file
        try:
            with open(self.workspace_path, 'r') as f:
                raw_config = json.load(f)

            # Migrate deprecated fields before validation
            self.config = self._migrate_deprecated_fields(raw_config)

            # If migration was performed, save the updated configuration back to file
            if self.config != raw_config:
                try:
                    with open(self.workspace_path, 'w') as f:
                        json.dump(self.config, f, indent=2)
                    logger.info(f"Saved migrated workspace configuration to {self.workspace_path}")
                except Exception as e:
                    logger.warning(f"Could not save migrated configuration: {e}")

            # Validate the migrated configuration with lenient mode
            errors = validate_workspace(self.config, lenient_mode=True)
            if errors:
                raise WorkspaceValidationError("\n".join(errors))

            # NEW v3.0: Validate workspace version compatibility (strict enforcement)
            # Skip version check if in upgrade mode (allows loading older workspaces for upgrade)
            if not upgrade_mode:
                self._validate_workspace_version_compatibility()

            logger.info(f"Loaded workspace '{self.config.get('workspace_name', 'Unnamed')}' from {self.workspace_path}")

            # Check workspace status and show warning if inactive
            try:
                self.check_workspace_active("load", allow_warnings=True)
            except WorkspaceInactiveError:
                pass  # This won't be raised when allow_warnings=True

            return self.config
        except FileNotFoundError:
            raise WorkspaceNotFoundError(f"Workspace file not found at {self.workspace_path}")
        except json.JSONDecodeError as e:
            raise WorkspaceError(f"Failed to parse workspace settings: {e}")
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

        errors = validate_workspace(self.config, lenient_mode=False)
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

        return path

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

    def get_schema_settings(self) -> Dict[str, Any]:
        """
        Get the resolved schema settings configuration section.

        Returns:
            The resolved schema settings configuration.

        Raises:
            WorkspaceError: If no configuration is loaded.
        """
        resolved = self.get_resolved_config()
        return resolved.get('schema_settings', {})

    def validate_media_plan(self, media_plan: Dict[str, Any], version: Optional[str] = None) -> List[str]:
        """
        Validate a media plan against the appropriate schema.

        Args:
            media_plan: The media plan data to validate.
            version: The schema version to validate against. If None, uses the preferred
                     version from workspace settings, or the version in the media plan.

        Returns:
            List of validation error messages, empty if validation succeeds.
        """
        # If no version specified, use preferred version from settings
        if version is None:
            schema_settings = self.get_schema_settings()
            version = schema_settings.get('preferred_version')

        # Validate using the schema validator
        return self.schema_validator.validate(media_plan, version)

    def migrate_media_plan(self, media_plan: Dict[str, Any], to_version: Optional[str] = None) -> Dict[str, Any]:
        """
        Migrate a media plan to a specific schema version.

        Args:
            media_plan: The media plan data to migrate.
            to_version: The target schema version. If None, uses the preferred
                       version from workspace settings.

        Returns:
            The migrated media plan data.
        """
        # If no target version specified, use preferred version from settings
        if to_version is None:
            schema_settings = self.get_schema_settings()
            to_version = schema_settings.get('preferred_version')

        # Get current version from media plan
        from_version = media_plan.get("meta", {}).get("schema_version")
        if not from_version:
            raise WorkspaceError("Media plan does not specify a schema version")

        # Migrate using the schema migrator
        return self.schema_migrator.migrate(media_plan, from_version, to_version)

    def get_storage_backend(self) -> 'StorageBackend':
        """
        Get the storage backend for this workspace.

        Returns:
            A StorageBackend instance.

        Raises:
            WorkspaceError: If no configuration is loaded.
        """
        if not self.is_loaded:
            raise WorkspaceError("No workspace configuration loaded. Call load() first.")

        from mediaplanpy.storage import get_storage_backend
        return get_storage_backend(self.get_resolved_config())

    def get_schema_manager(self) -> 'SchemaManager':
        """
        Get SchemaManager instance for this workspace.

        Returns:
            SchemaManager instance
        """
        from mediaplanpy.schema.manager import SchemaManager
        return SchemaManager()

    # =========================================================================
    # Workspace Upgrade - Delegated to WorkspaceUpgrader
    # =========================================================================

    def upgrade_workspace(self, target_sdk_version: Optional[str] = None, dry_run: bool = False) -> Dict[str, Any]:
        """
        Upgrade workspace from v2.0 to v3.0.

        This method delegates to the WorkspaceUpgrader class which handles:
        1. Pre-upgrade validation (reject v1.0 and below)
        2. Backup creation (JSON, Parquet, Database)
        3. JSON migration with audience/location transformation
        4. Parquet regeneration with v3.0 schema
        5. Database schema upgrade (ALTER TABLE)
        6. Workspace settings update

        Args:
            target_sdk_version: Target SDK version (defaults to current SDK version)
            dry_run: If True, shows what would be upgraded without making changes

        Returns:
            UpgradeResult dictionary with files processed, errors, database changes, backup locations

        Raises:
            WorkspaceError: If no configuration is loaded or upgrade fails
            WorkspaceInactiveError: If workspace is inactive

        Example:
            >>> workspace_manager = WorkspaceManager()
            >>> workspace_manager.load()
            >>> result = workspace_manager.upgrade_workspace(dry_run=True)  # Preview
            >>> result = workspace_manager.upgrade_workspace(dry_run=False)  # Actually upgrade
        """
        from mediaplanpy.workspace.upgrader import WorkspaceUpgrader
        upgrader = WorkspaceUpgrader(self)
        return upgrader.upgrade(target_sdk_version, dry_run)

    def get_workspace_version_info(self) -> Dict[str, Any]:
        """
        Get version information about the current workspace.

        Returns:
            Dictionary with workspace version details

        Raises:
            WorkspaceError: If no configuration is loaded
        """
        if not self.is_loaded:
            raise WorkspaceError("No workspace configuration loaded. Call load() first.")

        from mediaplanpy import __version__, __schema_version__

        # Get workspace settings
        workspace_settings = self.config.get("workspace_settings", {})

        # Get current SDK and schema versions
        current_sdk_version = __version__
        current_schema_version = __schema_version__

        # Get workspace versions
        workspace_schema_version = workspace_settings.get("schema_version")
        workspace_sdk_required = workspace_settings.get("sdk_version_required")
        last_upgraded = workspace_settings.get("last_upgraded")

        # Determine compatibility status
        compatibility_status = "unknown"
        needs_upgrade = False

        if workspace_schema_version:
            from mediaplanpy.schema.version_utils import compare_versions, normalize_version

            try:
                # Normalize versions for comparison
                norm_workspace = normalize_version(workspace_schema_version)
                norm_current = normalize_version(current_schema_version)

                version_comparison = compare_versions(norm_workspace, norm_current)

                if version_comparison == 0:
                    compatibility_status = "current"
                elif version_comparison < 0:
                    compatibility_status = "outdated"
                    needs_upgrade = True
                else:
                    compatibility_status = "newer"

            except Exception:
                compatibility_status = "unknown"
        else:
            compatibility_status = "no_version_info"
            needs_upgrade = True

        return {
            "current_sdk_version": current_sdk_version,
            "current_schema_version": current_schema_version,
            "workspace_schema_version": workspace_schema_version,
            "workspace_sdk_required": workspace_sdk_required,
            "last_upgraded": last_upgraded,
            "compatibility_status": compatibility_status,
            "needs_upgrade": needs_upgrade,
            "workspace_name": self.config.get("workspace_name", "Unknown"),
            "workspace_id": self.config.get("workspace_id", "Unknown")
        }


    def check_workspace_compatibility(self) -> Dict[str, Any]:
        """
        Check compatibility between workspace and current SDK/schema versions.

        Returns:
            Dictionary with compatibility check results

        Raises:
            WorkspaceError: If no configuration is loaded
        """
        if not self.is_loaded:
            raise WorkspaceError("No workspace configuration loaded. Call load() first.")

        version_info = self.get_workspace_version_info()

        # Detailed compatibility analysis
        compatibility_result = {
            "is_compatible": True,
            "warnings": [],
            "errors": [],
            "recommendations": []
        }

        # Check schema version compatibility
        if version_info["workspace_schema_version"]:
            from mediaplanpy.schema.version_utils import get_compatibility_type, get_migration_recommendation

            try:
                compatibility_type = get_compatibility_type(version_info["workspace_schema_version"])

                if compatibility_type == "unsupported":
                    compatibility_result["is_compatible"] = False
                    compatibility_result["errors"].append(
                        f"Workspace schema version {version_info['workspace_schema_version']} is not supported by SDK {version_info['current_sdk_version']}"
                    )

                    recommendation = get_migration_recommendation(version_info["workspace_schema_version"])
                    compatibility_result["recommendations"].append(recommendation.get("message", "Upgrade required"))

                elif compatibility_type == "deprecated":
                    compatibility_result["warnings"].append(
                        f"Workspace schema version {version_info['workspace_schema_version']} is deprecated"
                    )
                    compatibility_result["recommendations"].append("Consider upgrading workspace to current schema version")

                elif compatibility_type == "forward_minor":
                    compatibility_result["warnings"].append(
                        f"Workspace schema version {version_info['workspace_schema_version']} is newer than SDK supports"
                    )
                    compatibility_result["recommendations"].append("Consider upgrading SDK or downgrading workspace")

            except Exception as e:
                compatibility_result["warnings"].append(f"Could not determine schema compatibility: {str(e)}")

        # Check SDK version requirements
        if version_info["workspace_sdk_required"]:
            required_version = version_info["workspace_sdk_required"].replace(".x", ".0")
            current_version = version_info["current_sdk_version"]

            try:
                from mediaplanpy.schema.version_utils import compare_versions
                if compare_versions(current_version, required_version) < 0:
                    compatibility_result["is_compatible"] = False
                    compatibility_result["errors"].append(
                        f"Current SDK version {current_version} is below required version {version_info['workspace_sdk_required']}"
                    )
                    compatibility_result["recommendations"].append(f"Upgrade SDK to version {required_version} or later")
            except Exception:
                compatibility_result["warnings"].append("Could not compare SDK version requirements")

        # Add general recommendations
        if version_info["needs_upgrade"]:
            compatibility_result["recommendations"].append(
                "Run workspace.upgrade_workspace() to upgrade to current versions")

        return compatibility_result
